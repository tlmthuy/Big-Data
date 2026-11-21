"""Convert delivered TV2 prediction runs into public/demo-data.json (contract Part A).

Run from the root of a tlmthuy/Big-Data clone so `evaluation` is importable:

    PYTHONPATH=. python3 ../tv4-demo-web/scripts/export_demo_data.py \
      --run metrics/tv2-toy-day1=evaluation/tests/fixtures/catalog.json \
      --run metrics/tv2-config-collector-smoke/smoke-e1-popularity-010=evaluation/tests/fixtures/catalog.json \
      --output ../tv4-demo-web/public/demo-data.json

Each --run is RUN_DIR=CATALOG. RUN_DIR holds metrics.json and predictions.jsonl
directly, or under artifacts/ (collector layout, with run.json beside it).

Rules applied (see AGENTS.md):
- IDs are mapped to original product IDs with the run's own catalog, verified by SHA-256.
- Recommendation order is the artifact order; `rank` is the 1-based position.
- `score` is always null: TV2 has not exported per-item scores yet.
- Nothing is recomputed. Metrics are not copied here; they belong to run-results.json.
"""

import argparse
import csv
from datetime import date
import hashlib
import json
import subprocess
from pathlib import Path

from evaluation.data import Catalog, encoded_id

K = 20
CSV_RUN_FIELDS = ("run_id", "model", "subset", "split", "data_kind", "catalog_sha256")
CSV_FIELDS = (*CSV_RUN_FIELDS, "user_session", "prefix", "target", "target_rank", "rank", "product_id", "score")
PREDICTION_KEYS = {"user_session", "prefix", "target", "top20", "product_ids"}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def catalog_match(catalog_path, recorded_sha, *, allow_toy_line_endings):
    """Return 'exact' or 'line-endings-only'; raise if the content differs.

    Runs executed on a Windows checkout record the SHA-256 of the CRLF file.
    The JSON content is identical, so we accept it but record the fact.
    """
    catalog_request = f"Ask TV2 for catalog.json with SHA-256 {recorded_sha} from the same run"
    try:
        raw = catalog_path.read_bytes()
    except FileNotFoundError as error:
        raise ValueError(catalog_request) from error
    if sha256_bytes(raw) == recorded_sha:
        return "exact"
    variants = {raw.replace(b"\r\n", b"\n"), raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")}
    if allow_toy_line_endings and any(sha256_bytes(v) == recorded_sha for v in variants):
        return "line-endings-only"
    raise ValueError(catalog_request)


def locate(run_dir):
    for artifact_dir in (run_dir, run_dir / "artifacts"):
        if (artifact_dir / "metrics.json").is_file():
            run_json = run_dir / "run.json"
            collector = json.loads(run_json.read_text(encoding="utf-8")) if run_json.is_file() else None
            return artifact_dir, collector
    raise ValueError(f"{run_dir}: no metrics.json found")


def recorded_checksum(sources, *keys):
    for source in sources:
        artifacts = source.get("artifacts") or {}
        for key in keys:
            artifact = artifacts.get(key)
            checksum = source.get(f"{key}_sha256") or (artifact.get("sha256") if isinstance(artifact, dict) else None)
            if checksum:
                return checksum
    return None


def data_kind(metadata, collector):
    if collector is not None:
        return collector.get("metadata", {}).get("data_kind")
    # Runs without a collector record: only the explicit toy subset label is trusted.
    return "toy" if metadata.get("subset") == "toy" else None


def export_run(run_dir, catalog_path, allow_missing_total=False):
    artifact_dir, collector = locate(run_dir)
    metrics_path = artifact_dir / "metrics.json"
    metrics_bytes = metrics_path.read_bytes()
    metadata = json.loads(metrics_bytes)
    collector_metadata = (collector or {}).get("metadata") or {}
    sources = (metadata, collector_metadata, collector or {})
    if metadata.get("K") != K:
        raise ValueError(f"{run_dir}: expected K={K}, found {metadata.get('K')}")
    recorded_sha = metadata["artifacts"]["catalog"]["sha256"]
    kind = data_kind(metadata, collector)
    match = catalog_match(catalog_path, recorded_sha, allow_toy_line_endings=kind == "toy")
    catalog = Catalog.load(catalog_path)

    sessions, seen = [], set()
    for line in (artifact_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if set(row) != PREDICTION_KEYS:
            raise ValueError(f"{run_dir}: unexpected prediction keys {sorted(row)}")
        session_id = row["user_session"]
        if not isinstance(session_id, str) or not session_id.strip() or session_id in seen:
            raise ValueError(f"{run_dir}: expected unique nonempty session IDs")
        seen.add(session_id)

        sequence = row["prefix"] + [row["target"]]
        if catalog.sequence(sequence) != sequence:
            raise ValueError(f"{session_id}: prefix and target must contain only real IDs")
        ranked = [encoded_id(item) for item in row["top20"]]
        if len(set(ranked)) != len(ranked) or len(ranked) > K:
            raise ValueError(f"{session_id}: expected at most {K} unique recommendations")
        if any(item not in catalog.products for item in ranked):
            raise ValueError(f"{session_id}: recommendation outside the real-item catalog")
        original = [catalog.products[item] for item in ranked]
        if row["product_ids"] != original:
            raise ValueError(f"{session_id}: product_ids disagree with the catalog")

        target = catalog.products[row["target"]]
        sessions.append({
            "user_session": session_id,
            "prefix": [catalog.products[item] for item in row["prefix"]],
            "target": target,
            "top20": original,
            "target_rank": original.index(target) + 1 if target in original else None,
            "recommendations": [
                {"rank": index + 1, "product_id": product, "score": None}
                for index, product in enumerate(original)
            ],
        })

    total = metadata.get("n_sessions") if allow_missing_total else metadata["n_sessions"]
    if not sessions or (total is not None and len(sessions) != total):
        raise ValueError(f"{run_dir}: prediction count does not match n_sessions")

    return {
        "model": metadata["model"],
        "subset": metadata["subset"],
        "split": metadata["eval_split"],
        "run_id": metadata["run_id"],
        "data_kind": kind,
        "catalog_sha256": recorded_sha,
        "catalog": list(catalog.products.values()),
        "sessions": sessions,
        "provenance": {
            "run_dir": run_dir.as_posix(),
            "metrics_path": metrics_path.as_posix(),
            "metrics_sha256": sha256_bytes(metrics_bytes),
            "mapping_sha256": recorded_checksum(sources, "mapping", "id_mapping"),
            "vocabulary_sha256": recorded_checksum(sources, "vocabulary", "vocab"),
            "eval_day": metadata.get("eval_day"),
            "experiment": (collector or {}).get("metadata", {}).get("run", {}).get("experiment"),
            "catalog_path": catalog_path.as_posix(),
            "catalog_match": match,
            "score_available": False,
        },
    }


def sample_runs(runs, limit, seed):
    groups = {}
    for run in runs:
        key = (run["subset"], run["split"], run["provenance"]["eval_day"])
        groups.setdefault(key, []).append(run)
    for key, group in groups.items():
        by_id = [{row["user_session"]: row for row in run["sessions"]} for run in group]
        if any(index.keys() != by_id[0].keys() for index in by_id):
            raise ValueError(f"{key}: sampling requires identical session membership across runs")
        selected = sorted(by_id[0], key=lambda session: sha256_bytes(f"{seed}:{session}".encode("utf-8")))[:limit]
        for run, index in zip(group, by_id):
            artifact_dir, _ = locate(Path(run["provenance"]["run_dir"]))
            metrics = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
            run["sessions"] = [index[session] for session in selected]
            run["provenance"]["sample"] = {
                "rule": "sha256(seed:user_session)",
                "seed": seed,
                "n_selected": len(selected),
                "n_total": metrics.get("n_sessions"),
            }


def write_sample_csv(path, runs):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(CSV_FIELDS)
        for run in runs:
            run_values = tuple(run[key] for key in CSV_RUN_FIELDS)
            for session in run["sessions"]:
                session_values = (session["user_session"], " > ".join(session["prefix"]), session["target"], session["target_rank"])
                for recommendation in session["recommendations"]:
                    writer.writerow((*run_values, *session_values, recommendation["rank"], recommendation["product_id"], recommendation["score"]))


def team_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="append", required=True, metavar="RUN_DIR=CATALOG")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stamp", action="store_true", help="Include export date and file-level data kind")
    parser.add_argument("--sample", type=int, metavar="N")
    parser.add_argument("--sample-seed", type=int, default=0, metavar="S")
    parser.add_argument("--team-commit", help="Source revision when exporting from a Git archive")
    args = parser.parse_args()
    if args.sample is not None and args.sample <= 0:
        parser.error("--sample must be positive")
    try:
        runs = []
        for spec in args.run:
            run_dir, sep, catalog = spec.partition("=")
            if not sep:
                raise ValueError(f"--run needs RUN_DIR=CATALOG, got {spec!r}")
            runs.append(export_run(Path(run_dir), Path(catalog), allow_missing_total=args.sample is not None))
        if len({run["run_id"] for run in runs}) != len(runs):
            raise ValueError("Duplicate run_id")
        if args.sample is not None:
            sample_runs(runs, args.sample, args.sample_seed)
        payload = {"schema": "tv4-demo-data/v2", "team_commit": args.team_commit or team_commit(), "runs": runs}
        if args.stamp or args.sample is not None:
            kinds = {run["data_kind"] for run in runs}
            payload.update(generated_at=date.today().isoformat(),
                           data_kind=next(iter(kinds)) if kinds in ({"toy"}, {"real"}) else "unconfirmed")
        csv_path = args.output.with_name("sample-predictions.csv")
        if args.output == csv_path:
            raise ValueError("--output must be a JSON path distinct from sample-predictions.csv")
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_sample_csv(csv_path, runs)
        for run in runs:
            print(f"{run['run_id']}: {run['model']}, {len(run['sessions'])} sessions, "
                  f"data_kind={run['data_kind']}, catalog {run['provenance']['catalog_match']}")
        print(f"Wrote {args.output} and {csv_path}")
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Export failed: {error}\n")


if __name__ == "__main__":
    main()
