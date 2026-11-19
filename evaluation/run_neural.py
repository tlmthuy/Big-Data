"""Daily GRU/XLNet training, last-item evaluation and common real-item Top-20.

Architecture/masking source: models/session_models.py (Apache-2.0).
The streaming PyArrow/JSONL loop replaces the notebook Trainer, retaining
AdamW state and weights, resetting linear LR decay at each daily partition.
"""

import argparse
import importlib.metadata
import json
import math
import platform
import random
import subprocess
import time
import traceback
from pathlib import Path

from evaluation.data import Catalog, audit_sessions, read_sessions
from evaluation.ranking import K, RankingMetrics
from evaluation.run_popularity import fingerprint, sha256
from models.session_models import DEFAULTS, FEATURE, SOURCE_COMMIT, build_model


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def batches(path, catalog, day, split, size):
    batch = []
    for row in read_sessions(path, day=day, split=split):
        batch.append((row["user_session"], catalog.sequence(row["product_ids"])))
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def tensor_batch(rows, padding, device):
    import torch

    return {FEATURE: torch.tensor([seq + [padding] * (20 - len(seq))
                                   for _, seq in rows], dtype=torch.long, device=device)}


def rank_catalog(scores, catalog):
    import torch

    ids = torch.tensor(sorted(catalog.products), device=scores.device)
    if scores.ndim != 2 or ids[-1] >= scores.shape[1]:
        raise ValueError("Runtime prediction tensor is not [batch, fitted vocabulary]")
    real_scores = scores[:, ids]
    if not torch.isfinite(real_scores).all():
        raise ValueError("Non-finite scores on real catalog items")
    # Stable sort on ascending IDs defines deterministic ties without changing scores.
    order = torch.argsort(real_scores, dim=-1, descending=True, stable=True)[:, :K]
    return ids[order].detach().cpu().tolist()


def sync(device):
    if device.type == "cuda":
        import torch
        torch.cuda.synchronize(device)


def evaluate(model, args, catalog, day, split, device, output):
    import torch

    model.eval()
    metrics = RankingMetrics()
    compute_seconds = 0.0
    started = time.perf_counter()
    with Path(output).open("w", encoding="utf-8") as handle, torch.no_grad():
        for rows in batches(args.data, catalog, day, split, args.eval_batch_size):
            inputs = tensor_batch(rows, catalog.padding_id, device)
            sync(device)
            tick = time.perf_counter()
            # Full sequences: the library masks/generates the last target once.
            result = model(inputs, training=False, testing=True)
            expected = [seq[-1] for _, seq in rows]
            if result["labels"].detach().cpu().tolist() != expected:
                raise ValueError("Runtime labels disagree with last non-padding targets")
            if result["predictions"].shape[0] != len(rows):
                raise ValueError("Runtime must return exactly one prediction row per session")
            rankings = rank_catalog(result["predictions"], catalog)
            sync(device)
            compute_seconds += time.perf_counter() - tick
            for (session, seq), top20 in zip(rows, rankings):
                metrics.update(seq[-1], top20)
                handle.write(json.dumps({"user_session": session, "prefix": seq[:-1],
                                         "target": seq[-1], "top20": top20,
                                         "product_ids": [catalog.products[i] for i in top20]}) + "\n")
    return {"day_index": day, "split": split, **metrics.compute(),
            "inference_seconds": compute_seconds,
            "evaluation_with_io_seconds": time.perf_counter() - started}


def train_day(model, optimizer, args, catalog, day, n_sessions, device):
    import torch

    steps = math.ceil(n_sessions / args.batch_size) * args.epochs
    # Same optimizer/weights across days; a new schedule, as notebook reset_lr_scheduler.
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda step: max(0.0, 1.0 - step / steps))
    model.train()
    sync(device)
    started = time.perf_counter()
    updates = 0
    loss_sum = 0.0
    for _ in range(args.epochs):
        for rows in batches(args.data, catalog, day, "train", args.batch_size):
            optimizer.zero_grad(set_to_none=True)
            result = model(tensor_batch(rows, catalog.padding_id, device), training=True)
            loss = result["loss"]
            if not torch.isfinite(loss):
                raise ValueError("Non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            loss_sum += loss.detach().item()
            updates += 1
            del result, loss
    sync(device)
    if updates != steps:
        raise ValueError("Train membership changed after audit")
    return {"day_index": day, "n_sessions": n_sessions, "updates": updates,
            "mean_step_loss": loss_sum / updates,
            "train_with_input_scan_seconds": time.perf_counter() - started}


def preflight(args):
    for key in ["batch_size", "eval_batch_size", "epochs"]:
        if getattr(args, key) < 1:
            raise ValueError(f"{key} must be positive")
    if args.seed < 0:
        raise ValueError("seed must be non-negative")
    if args.learning_rate is None:
        args.learning_rate = DEFAULTS[args.model]["learning_rate"]
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        raise ValueError("learning-rate must be positive and finite")
    if not args.schema.is_file():
        raise ValueError("Provide the fitted schema JSON or pbtxt from TV1")
    catalog = Catalog.load(args.catalog)
    if catalog.padding_id != 0:
        raise ValueError("Pinned NVIDIA masking uses padding 0; verify runtime/catalog before training")
    counts = audit_sessions(args.data, catalog)
    final_day = max(row["day_index"] for row in counts)
    if args.train_through is None:
        args.train_through = final_day - 1
    if not 1 <= args.train_through < final_day:
        raise ValueError("train-through must be in 1..D-1")
    if args.split == "test" and (args.train_through != final_day - 1 or not args.config_frozen):
        raise ValueError("Final test requires train-through D-1 and --config-frozen")
    membership = {(r["day_index"], r["split"]): r["n_sessions"] for r in counts}
    for day in range(1, args.train_through + 1):
        if not membership.get((day, "train")):
            raise ValueError(f"Empty train partition {day}")
        if not membership.get((day + 1, "validation")):
            raise ValueError(f"Empty validation partition {day + 1}")
    if not membership.get((args.train_through + 1, args.split)):
        raise ValueError("Requested final evaluation partition is empty")
    return catalog, counts


def run(args):
    catalog, counts = preflight(args)
    artifacts = {"sessions": fingerprint(args.data), "catalog": fingerprint(args.catalog),
                 "schema": fingerprint(args.schema)}
    if args.check_inputs:
        return {"status": "input_contract_checked_only", "counts": counts,
                "train_through": args.train_through, "artifacts": artifacts}
    if args.output.exists():
        raise ValueError("Output must be a new directory")
    args.output.mkdir(parents=True)
    try:
        return execute(args, catalog, counts, artifacts)
    except Exception:
        save_json(args.output / "failure.json", {"run_id": args.run_id,
                  "model": args.model, "traceback": traceback.format_exc(),
                  "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}})
        raise


def execute(args, catalog, counts, artifacts):
    import torch
    import numpy as np

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA unavailable; use the verified TV3 GPU runtime")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    model = build_model(args.model, args.schema, catalog).to(device)
    training_config = {key: getattr(args, key) for key in
                       ["model", "batch_size", "epochs", "seed", "learning_rate"]}
    training_source_sha256 = {p: sha256(p) for p in
                              ["models/session_models.py", "evaluation/run_neural.py", "evaluation/data.py"]}
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate,
                                 betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    history = []
    trained_days = []
    if args.checkpoint:
        state = torch.load(args.checkpoint, map_location=device, weights_only=False)
        expected = list(range(1, args.train_through + 1))
        if state["trained_days"] != expected or state["artifacts"] != artifacts:
            raise ValueError("Checkpoint membership/schema/catalog mismatch")
        if state["model"] != args.model:
            raise ValueError("Checkpoint model mismatch")
        if state["training_config"] != training_config:
            raise ValueError("Checkpoint originating training configuration mismatch")
        if state["training_source_sha256"] != training_source_sha256:
            raise ValueError("Checkpoint training code differs from this checkout")
        model.load_state_dict(state["state_dict"])
        trained_days = state["trained_days"]
    else:
        for day in range(1, args.train_through + 1):
            n_sessions = next(r["n_sessions"] for r in counts
                              if r["day_index"] == day and r["split"] == "train")
            train = train_day(model, optimizer, args, catalog, day, n_sessions, device)
            validation = evaluate(model, args, catalog, day + 1, "validation", device,
                                  args.output / f"validation-day{day+1}.jsonl")
            trained_days.append(day)
            history.append({"train": train, "validation": validation})
        torch.save({"state_dict": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "trained_days": trained_days, "artifacts": artifacts,
                    "training_config": training_config, "training_source_sha256": training_source_sha256,
                    "model": args.model}, args.output / "checkpoint.pt")
    final = evaluate(model, args, catalog, args.train_through + 1, args.split, device,
                     args.output / "predictions.jsonl")
    packages = {}
    for name in ["torch", "transformers", "transformers4rec", "merlin-core", "pyarrow"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    result = {"run_id": args.run_id, "model": args.model, "subset": args.subset,
              "K": K, "train_days": trained_days, "eval_day": final["day_index"],
              "eval_split": args.split, "final": final, "history": history,
              **{key: final[key] for key in ["n_sessions", "Recall@20", "NDCG@20", "recall_sum", "ndcg_sum"]},
              "train_with_input_scan_seconds": sum(r["train"]["train_with_input_scan_seconds"] for r in history),
              "inference_seconds": final["inference_seconds"],
              "inference_scope": "testing forward (mask/labels/loss) plus real-catalog ranking and IDs transfer; excludes input packing and file IO",
              "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else None,
              "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(device) if device.type == "cuda" else None,
              "parameter_bytes": sum(p.numel() * p.element_size() for p in model.parameters()),
              "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
              "artifacts": artifacts, "split_counts": counts,
              "training_config": training_config, "training_source_sha256": training_source_sha256,
              "source_commit": SOURCE_COMMIT, "loader": "fixed-order streaming PyArrow/JSONL; no shuffle",
              "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "source_sha256": {p: sha256(p) for p in ["models/session_models.py", "evaluation/run_neural.py", "evaluation/data.py", "evaluation/ranking.py"]},
              "python": platform.python_version(), "packages": packages,
              "device": str(device), "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
              "cuda": torch.version.cuda}
    save_json(args.output / "metrics.json", result)
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=DEFAULTS, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--schema", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--split", choices=["validation", "test"], default="validation")
    p.add_argument("--train-through", type=int)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--eval-batch-size", type=int, default=32)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--learning-rate", type=float)
    p.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    p.add_argument("--subset", choices=["toy", "10", "25", "50", "100"], required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--config-frozen", action="store_true")
    p.add_argument("--check-inputs", action="store_true")
    p.add_argument("--checkpoint", type=Path, help="Trusted project checkpoint; evaluation only")
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    try:
        print(json.dumps(run(args), indent=2))
    except (ValueError, OSError, ImportError, RuntimeError) as error:
        raise SystemExit(f"Neural run failed: {error}") from error
