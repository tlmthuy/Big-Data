"""Generate synthetic inputs for adapter and Chrome performance checks."""
import hashlib
import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "fixtures/large"


def write(path, data):
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def main():
    run = OUTPUT / "run"
    run.mkdir(parents=True, exist_ok=True)
    products = range(3, 63_398 + 3)
    catalog = OUTPUT / "catalog.json"
    write(catalog, {
        "subset": "toy",
        "technical_ids": {"padding": 0, "null": 1, "oov": 2, "mask": 100_000},
        "items": [{"encoded_id": item, "product_id": f"p{item}"} for item in products],
    })
    predictions = []
    for index in range(30):
        ranking = list(range(3 + index, 23 + index))
        predictions.append({
            "user_session": f"synthetic-{index}", "prefix": [3],
            "target": ranking[index % len(ranking)], "top20": ranking,
            "product_ids": [f"p{item}" for item in ranking],
        })
    write(run / "metrics.json", {
        "K": 20, "model": "Popularity", "subset": "toy", "eval_split": "validation", "eval_day": 2,
        "run_id": "synthetic-large", "n_sessions": len(predictions),
        "artifacts": {"catalog": {"sha256": hashlib.sha256(catalog.read_bytes()).hexdigest()}},
    })
    (run / "predictions.jsonl").write_text("".join(json.dumps(row) + "\n" for row in predictions), encoding="utf-8")


if __name__ == "__main__":
    main()
