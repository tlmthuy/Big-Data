"""Verify a toy GPU checkpoint: last labels, target hiding and batch independence."""

import argparse
import json
from pathlib import Path

from evaluation.data import Catalog
from evaluation.run_neural import save_json, tensor_batch
from models.session_models import build_model


def verify(model_name, run_path):
    import torch

    run_path = Path(run_path)
    metrics = json.loads((run_path / "metrics.json").read_text(encoding="utf-8"))
    if metrics["subset"] != "toy" or metrics["model"] != model_name:
        raise ValueError("Only use this verifier on the matching toy smoke run")
    if not torch.cuda.is_available():
        raise ValueError("GPU verification requires CUDA")
    config = metrics["config"]
    catalog = Catalog.load(config["catalog"])
    items = sorted(catalog.products)
    if len(items) < 4:
        raise ValueError("The counterfactual toy check requires at least four real items")
    device = torch.device("cuda")
    model = build_model(model_name, config["schema"], catalog).to(device)
    checkpoint = torch.load(run_path / "checkpoint.pt", map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    first = ("same-prefix-a", items[:3])
    changed_target = ("same-prefix-b", [items[0], items[1], items[3]])
    unrelated = ("other-session", [items[3], items[2], items[0]])
    with torch.no_grad():
        paired = model(tensor_batch([first, changed_target], catalog.padding_id, device), testing=True)
        if paired["labels"].cpu().tolist() != [items[2], items[3]]:
            raise ValueError("Runtime labels are not the final non-padding items")
        if not torch.allclose(paired["predictions"][0], paired["predictions"][1], atol=1e-5, rtol=1e-5):
            raise ValueError("Changing the target while preserving the prefix changed prediction scores")
        alone = model(tensor_batch([first], catalog.padding_id, device), testing=True)["predictions"][0]
        with_other = model(tensor_batch([first, unrelated], catalog.padding_id, device), testing=True)["predictions"][0]
        if not torch.allclose(alone, with_other, atol=1e-5, rtol=1e-5):
            raise ValueError("An unrelated batch session changed prediction scores")
    result = {"status": "passed", "model": model_name, "scope": "synthetic GPU smoke only",
              "gpu": torch.cuda.get_device_name(), "last_item_labels": "passed",
              "target_hidden": "passed", "batch_independence": "passed",
              "counterfactual_max_score_diff": (paired["predictions"][0] - paired["predictions"][1]).abs().max().item(),
              "batch_max_score_diff": (alone - with_other).abs().max().item(),
              "original_run_id": metrics["run_id"], "evaluated_sessions": metrics["n_sessions"]}
    save_json(run_path / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["gru", "xlnet"], required=True)
    parser.add_argument("--run-path", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.model, args.run_path), indent=2))
