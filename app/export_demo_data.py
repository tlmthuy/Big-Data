"""Convert a TV2 Popularity toy run to the React demo's JSON format."""

import argparse
import json
from pathlib import Path

from evaluation.data import Catalog, encoded_id
from evaluation.ranking import K
from evaluation.run_popularity import sha256


def export(run_dir, catalog_path, output):
    metadata = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    if (metadata["model"], metadata["subset"], metadata["K"]) != ("Popularity", "toy", K):
        raise ValueError("The current demo expects a Popularity toy run with K=20")
    if sha256(catalog_path) != metadata["artifacts"]["catalog"]["sha256"]:
        raise ValueError("Catalog checksum does not match the run")

    catalog = Catalog.load(catalog_path)
    sessions = []
    seen_sessions = set()
    with (run_dir / "predictions.jsonl").open(encoding="utf-8") as predictions:
        for line in predictions:
            if not line.strip():
                continue
            row = json.loads(line)
            session_id = row["user_session"]
            if not isinstance(session_id, str) or not session_id.strip() or session_id in seen_sessions:
                raise ValueError("Expected a unique nonempty toy session ID")
            seen_sessions.add(session_id)

            sequence = row["prefix"] + [row["target"]]
            if catalog.sequence(sequence) != sequence:
                raise ValueError(f"{session_id}: prefix and target must contain only real IDs")

            ranked = [encoded_id(item) for item in row["top20"]]
            if len(set(ranked)) != len(ranked) or len(ranked) > K:
                raise ValueError(f"{session_id}: expected at most {K} unique recommendations")
            if any(item not in catalog.products for item in ranked):
                raise ValueError(f"{session_id}: recommendation is outside the real-item catalog")
            original_ids = [catalog.products[item] for item in ranked]
            if row["product_ids"] != original_ids:
                raise ValueError(f"{session_id}: ranked product IDs disagree with the catalog")

            sessions.append({
                "user_session": session_id,
                "prefix": [catalog.products[item] for item in row["prefix"]],
                "target": catalog.products[row["target"]],
                "top20": original_ids,
            })

    if not sessions or len(sessions) != metadata["n_sessions"]:
        raise ValueError("Prediction session count does not match the run")

    demo = {
        "model": metadata["model"],
        "subset": metadata["subset"],
        "split": metadata["eval_split"],
        "catalog": list(catalog.products.values()),
        "sessions": sessions,
    }
    output.write_text(json.dumps(demo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(sessions)} sessions and {len(demo['catalog'])} catalog items to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        export(args.run_dir, args.catalog, args.output)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Export failed: {error}\n")


if __name__ == "__main__":
    main()
