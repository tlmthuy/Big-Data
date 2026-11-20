"""Run from repo root: python -m evaluation.run_popularity --help."""

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

from evaluation.timing import evaluation_timing

from evaluation.data import Catalog, audit_sessions, read_sessions
from evaluation.ranking import K, RankingMetrics
from models.popularity import Popularity


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(path):
    path = Path(path)
    if path.is_file():
        return {"path": str(path), "sha256": sha256(path)}
    if not path.is_dir():
        raise ValueError(f"Artifact path does not exist: {path}")
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise ValueError(f"Artifact directory is empty: {path}")
    return {"path": str(path), "files": [
        {"path": str(p.relative_to(path)), "sha256": sha256(p)}
        for p in files]}


def run(args):
    if args.train_through < 1:
        raise ValueError("train-through must be >= 1")
    catalog = Catalog.load(args.catalog)
    split_counts = audit_sessions(args.sessions, catalog)
    eval_day = args.train_through + 1
    final_day = max(row["day_index"] for row in split_counts)
    if args.eval_split == "test" and eval_day != final_day:
        raise ValueError("Final test requires train-through = final day_index - 1")
    selected = next((r for r in split_counts if r["day_index"] == eval_day
                     and r["split"] == args.eval_split), None)
    if not selected or not selected["n_sessions"]:
        raise ValueError("No sessions in requested next-partition evaluation split")
    args.output.mkdir(parents=True, exist_ok=False)
    model = Popularity(catalog)
    start = time.perf_counter()
    for day in range(1, args.train_through + 1):
        model.update_partition(day, (row for row in read_sessions(args.sessions)
                                    if row["split"] == "train" and row["day_index"] == day))
    train_seconds = time.perf_counter() - start
    evaluation_started = time.perf_counter()
    start = time.perf_counter()
    predictions = model.recommend()
    rank_seconds = time.perf_counter() - start
    metrics = RankingMetrics()
    with (args.output / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in read_sessions(args.sessions, day=eval_day, split=args.eval_split):
            sequence = catalog.sequence(row["product_ids"])
            metrics.update(sequence[-1], predictions)
            handle.write(json.dumps({"user_session": row["user_session"],
                                     "prefix": sequence[:-1], "target": sequence[-1],
                                     "top20": predictions,
                                     "product_ids": [catalog.products[i] for i in predictions]}) + "\n")
    summary = metrics.compute()
    timing = evaluation_timing(evaluation_started, summary["n_sessions"], rank_seconds,
                               "one cached shared catalog ranking; not comparable to neural compute")
    result = {"run_id": args.run_id, "model": "Popularity", "subset": args.subset,
              "K": K, "train_days": sorted(model.trained_days), "eval_day": eval_day,
              "eval_split": args.eval_split, **summary, **timing,
              "train_with_input_scan_seconds": train_seconds,
              "ranking_once_seconds": rank_seconds,
              "output_path": str(args.output.resolve()), "python": platform.python_version(),
              "platform": platform.platform(),
              "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "source_sha256": {str(path): sha256(path) for path in [
                  Path("evaluation/data.py"), Path("evaluation/ranking.py"),
                  Path("evaluation/run_popularity.py"), Path("models/popularity.py"),
                  Path("evaluation/timing.py")]},
              "config": vars(args) | {"sessions": str(args.sessions), "catalog": str(args.catalog),
                                      "output": str(args.output)},
              "artifacts": {"sessions": fingerprint(args.sessions),
                            "catalog": fingerprint(args.catalog)},
              "split_counts": split_counts}
    (args.output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (args.output / "popularity.json").write_text(json.dumps({
        "train_days": sorted(model.trained_days),
        "counts": dict(sorted(model.counts.items())), "top20": predictions}, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--train-through", required=True, type=int)
    parser.add_argument("--eval-split", choices=["validation", "test"], default="validation")
    parser.add_argument("--subset", required=True, choices=["toy", "10", "25", "50", "100"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), indent=2))
    except (ValueError, KeyError, OSError, ImportError) as error:
        parser.exit(1, f"Run failed: {error}\n")


if __name__ == "__main__":
    main()
