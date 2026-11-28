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
- Nothing is recomputed. Experiment metrics belong to public/official-results.json.
"""

import argparse
import csv
import csv
from datetime import date
import hashlib
import json
import tempfile
from pathlib import Path
from pathlib import PurePosixPath

from evaluation.data import Catalog, encoded_id
from team_repo import team_commit

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
    predictions_path = artifact_dir / "predictions.jsonl"
    predictions_bytes = predictions_path.read_bytes()
    for line in predictions_bytes.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if set(row) != PREDICTION_KEYS:
            raise ValueError(f"{run_dir}: unexpected prediction keys {sorted(row)}")
        session_id = row["user_session"]
        if isinstance(session_id, bool) or not isinstance(session_id, (str, int)) or not str(session_id).strip():
            raise ValueError(f"{run_dir}: expected unique nonempty session IDs")
        session_id = str(session_id)
        if session_id in seen:
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
            "predictions_sha256": sha256_bytes(predictions_bytes),
            "catalog_sha256": recorded_sha,
            "catalog_size": len(catalog.products),
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
                "rule": "SHA-256 of \"<seed>:<user_session>\", ascending; first N",
                "seed": seed,
                "n_selected": len(selected),
                "n_total": metrics.get("n_sessions"),
            }


def subset_catalogs(runs):
    for run in runs:
        full_catalog = run["catalog"]
        full_size = len(full_catalog)
        used = {item for session in run["sessions"]
                for item in (*session["prefix"], session["target"], *session["top20"])}
        run["catalog"] = [item for item in full_catalog if item in used]
        run["catalog_size"] = full_size
        run["provenance"]["catalog_size"] = full_size


def real_e1_runs(bundle, metrics_path, configs_path, checks_path, split_population_path):
    """Prepare checksum-verified delivered E1 artifacts in the adapter's normal input shape."""
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    configs = json.loads(configs_path.read_text(encoding="utf-8"))
    checks = {row["run_id"]: row for row in json.loads(checks_path.read_text(encoding="utf-8"))}
    table = {row["run_id"]: row for row in metrics["tables"]["E1"]}
    catalog_path = bundle / "catalog.json"
    catalog_bytes = catalog_path.read_bytes()
    catalog_sha = sha256_bytes(catalog_bytes)
    verified_catalog_hashes = {
        configs[run]["run_metadata"]["versions"]["catalog_version"]
        for run in ("e1-popularity-010", "e1-gru-010", "e1-xlnet-010")
    }
    if verified_catalog_hashes != {catalog_sha}:
        raise ValueError("Real catalog SHA-256 does not match the official configs")
    with split_population_path.open(newline="", encoding="utf-8-sig") as file:
        partition = next((int(row["last_partition_D"]) for row in csv.DictReader(file) if int(row["subset"]) == 10), None)
    if partition is None:
        raise ValueError("split_population.csv has no subset 10 last_partition_D")
    prepared = []
    for run_id in ("e1-popularity-010", "e1-gru-010", "e1-xlnet-010"):
        prediction_path = bundle / f"{run_id}.predictions.jsonl"
        raw = prediction_path.read_bytes()
        checksum = sha256_bytes(raw)
        expected = checks[run_id]["predictions_sha256"]
        if checksum != expected or sha256_bytes(raw.replace(b"\r\n", b"\n")) != expected:
            raise ValueError(f"{run_id}: predictions SHA-256 does not match prediction_checks.json")
        row = table[run_id]
        if row["n_sessions"] != checks[run_id]["sessions"]:
            raise ValueError(f"{run_id}: metrics session count differs from prediction_checks.json")
        prepared.append((run_id, prediction_path, row, checksum))
    session_sets = []
    catalog = Catalog.load(catalog_path)
    for run_id, path, row, _ in prepared:
        seen = set()
        count = 0
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                item = json.loads(line)
                if set(item) != PREDICTION_KEYS:
                    raise ValueError(f"{run_id}: prediction keys do not match the contract")
                if [catalog.products[i] for i in item["top20"]] != item["product_ids"]:
                    raise ValueError(f"{run_id}/{item['user_session']}: top20/product_ids mismatch")
                if item["user_session"] in seen:
                    raise ValueError(f"{run_id}: duplicate user_session")
                seen.add(item["user_session"])
                count += 1
        if count != row["n_sessions"]:
            raise ValueError(f"{run_id}: expected {row['n_sessions']} JSONL rows, found {count}")
        session_sets.append(seen)
    if not (session_sets[0] == session_sets[1] == session_sets[2]):
        raise ValueError("E1 prediction files do not have identical user_session sets")

    temporary = tempfile.TemporaryDirectory(prefix="tv4-real-e1-")
    root = Path(temporary.name)
    runs = []
    for run_id, prediction_path, row, checksum in prepared:
        run_dir = root / run_id
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True)
        (run_dir / "run.json").write_text(json.dumps({"metadata": {"data_kind": "real"}}), encoding="utf-8")
        metadata = {"K": 20, "model": row["model"], "subset": row["subset"],
                    "eval_split": row["split"], "run_id": run_id, "n_sessions": row["n_sessions"],
                    "eval_day": partition, "artifacts": {"catalog": {"sha256": catalog_sha}}}
        (artifacts / "metrics.json").write_text(json.dumps(metadata), encoding="utf-8")
        (artifacts / "predictions.jsonl").write_bytes(prediction_path.read_bytes())
        run = export_run(run_dir, catalog_path)
        run["provenance"]["predictions_sha256"] = checksum
        run["provenance"]["catalog_sha256"] = catalog_sha
        run["provenance"]["n_total"] = row["n_sessions"]
        runs.append(run)
    return temporary, runs


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


def public_product_lookup_path(value):
    if value is None:
        return None
    clean_value = value.strip()
    path = PurePosixPath(clean_value)
    if (
        not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or any(char in clean_value for char in "\\?#")
        or path.suffix.lower() != ".json"
    ):
        raise ValueError("--product-lookup must be a relative JSON path within public/")
    return path.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="append", metavar="RUN_DIR=CATALOG")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stamp", action="store_true", help="Include export date and file-level data kind")
    parser.add_argument("--sample", type=int, metavar="N")
    parser.add_argument("--sample-seed", type=int, default=0, metavar="S")
    parser.add_argument("--team-commit", help="Source revision when exporting from a Git archive")
    parser.add_argument("--product-lookup", type=public_product_lookup_path, metavar="PUBLIC_PATH",
                        help="Optional relative JSON path for the public product lookup")
    parser.add_argument("--real-e1-bundle", type=Path, help="Verified delivered real E1 bundle directory")
    parser.add_argument("--metrics", type=Path, help="Official metrics.json for real E1 export")
    parser.add_argument("--configs", type=Path, help="Official configs.json for real E1 export")
    parser.add_argument("--prediction-checks", type=Path, help="Official prediction_checks.json")
    parser.add_argument("--split-population", type=Path, help="TV2 split_population.csv for test partition D")
    args = parser.parse_args()
    if args.sample is not None and args.sample <= 0:
        parser.error("--sample must be positive")
    try:
        temporary = None
        if args.real_e1_bundle:
            if args.run or not (args.metrics and args.configs and args.prediction_checks and args.split_population):
                raise ValueError("--real-e1-bundle requires --metrics, --configs, --prediction-checks, --split-population and no --run")
            temporary, runs = real_e1_runs(args.real_e1_bundle, args.metrics, args.configs, args.prediction_checks, args.split_population)
        else:
            if not args.run:
                raise ValueError("provide --run or --real-e1-bundle")
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
        subset_catalogs(runs)
        if args.real_e1_bundle:
            for run in runs:
                run_id = run["run_id"]
                provenance = run["provenance"]
                run["provenance"] = {
                    "predictions_path": (args.real_e1_bundle / f"{run_id}.predictions.jsonl").as_posix(),
                    "predictions_sha256": provenance["predictions_sha256"],
                    "catalog_path": (args.real_e1_bundle / "catalog.json").as_posix(),
                    "catalog_sha256": run["catalog_sha256"],
                    "catalog_size": run["catalog_size"],
                    "catalog_match": "exact",
                    "eval_day": provenance["eval_day"],
                    "score_available": False,
                    "n_total": provenance["n_total"],
                    "sample": provenance["sample"],
                }
        payload = {
            "schema": "tv4-demo-data/v2",
            "team_commit": args.team_commit or team_commit(),
            "provenance": {"product_lookup": args.product_lookup},
            "runs": runs,
        }
        if args.stamp or args.sample is not None:
            kinds = {run["data_kind"] for run in runs}
            payload.update(generated_at=date.today().isoformat(),
                           data_kind=next(iter(kinds)) if kinds in ({"toy"}, {"real"}) else "unconfirmed")
        csv_path = args.output.with_name("sample-predictions.csv")
        if args.output == csv_path:
            raise ValueError("--output must be a JSON path distinct from sample-predictions.csv")
        write_sample_csv(csv_path, runs)
        # Keep contract top20; recommendations is the UI adapter's expanded duplicate.
        for run in runs:
            for session in run["sessions"]:
                session.pop("recommendations", None)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for run in runs:
            print(f"{run['run_id']}: {run['model']}, {len(run['sessions'])} sessions, "
                  f"data_kind={run['data_kind']}, catalog {run['provenance']['catalog_match']}")
        print(f"Wrote {args.output} and {csv_path}")
        if temporary is not None:
            temporary.cleanup()
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Export failed: {error}\n")


if __name__ == "__main__":
    main()
