"""Build isolated E1/E3 real-data cohort smoke configs, never official runs."""

import argparse
import hashlib
import json
from pathlib import Path


def version(path, label):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"{label}:sha256:{digest}"


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def prepare(manifest_path, data_root, cohort, environment_snapshot, output,
            e4_csv=None, e4_parquet=None):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    first_seen_manifest = json.loads((Path(manifest_path).parent / "monthly_first_seen.json").read_text(encoding="utf-8"))
    if manifest["dataset_decision"]["status"] != "selected_for_official_experiments":
        raise ValueError("The selected cuDF E2 handoff is not marked official")
    pinned_first_seen = "5923002be2c73b90d7cf4261967b416a8684d1d9d884a64da1c3d9d15baba8a7"
    if first_seen_manifest.get("output_sha256") != pinned_first_seen:
        raise ValueError("Monthly first-seen manifest checksum is not the pinned shared artifact")
    data_root, cohort = Path(data_root), Path(cohort)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    subsets = {}
    for entry in manifest["runs"]:
        subset = str(entry["subset"])
        root = data_root / subset
        workflow = root / "workflow/manifest.json"
        split = root / "splits/manifest.json"
        catalog = root / "workflow/catalog.json"
        schema = root / "workflow/processed_nvt/schema.pbtxt"
        telemetry = root / "pipeline_metrics.json"
        paths = [workflow, split, catalog, schema, telemetry]
        if not all(path.is_file() for path in paths):
            raise ValueError(f"Incomplete selected TV1 artifacts for subset {subset}")
        workflow_info = json.loads(workflow.read_text(encoding="utf-8"))
        split_info = json.loads(split.read_text(encoding="utf-8"))
        telemetry_info = json.loads(telemetry.read_text(encoding="utf-8"))
        source_log = Path(telemetry_info["source_log"])
        first_seen = Path(telemetry_info["first_seen_artifact"])
        expected_preprocessing = sum(telemetry_info.get(key, -1) for key in
                                     ("prepare_seconds", "workflow_seconds", "split_seconds"))
        if (split_info.get("no_overlap_and_complete_coverage") is not True
                or workflow_info.get("notebook_commit") != "f0ca2b5343dd1e40b5d2422b942f014b224f5c20"
                or telemetry_info.get("status") != "measured"
                or telemetry_info.get("input_sha256") != entry["input_sha256"]
                or telemetry_info.get("n_events") != entry["n_events"]
                or split_info.get("input_sessions") != entry["sequence_count"]
                or workflow_info.get("product_vocabulary_size") != entry["vocabulary_size"]
                or telemetry_info.get("first_seen_sha256") != pinned_first_seen
                or telemetry_info.get("first_seen_seconds") != first_seen_manifest["shared_build_seconds"]
                or abs(telemetry_info.get("preprocessing_seconds", -1) - expected_preprocessing) > 1e-6
                or not source_log.is_file() or source_log.stat().st_size == 0
                or not first_seen.is_file()
                or digest(first_seen) != telemetry_info["first_seen_sha256"]):
            raise ValueError(f"Lineage/split/telemetry mismatch for subset {subset}")
        day_indices = [row["day_index"] for row in split_info["counts"]]
        subsets[subset] = {
            "sessions": str(cohort if subset == "10" else root / "splits"),
            "schema": str(schema), "catalog": str(catalog),
            "preprocessing_manifest": str(split),
            "workflow_version": version(workflow, "tv1-cuDF-workflow"),
            "mapping_version": workflow_info["checksums"]["product_mapping.parquet"],
            "catalog_version": workflow_info["checksums"]["catalog.json"],
            "accepted_by_tv2": True,
            "final_day": 2 if subset == "10" else max(day_indices),
            "pipeline_metrics": str(telemetry),
        }
    if bool(e4_csv) != bool(e4_parquet):
        raise ValueError("Provide both E4 CSV and Parquet paths, or neither")
    if e4_csv and (not Path(e4_csv).is_file() or not Path(e4_parquet).is_file()):
        raise ValueError("Both E4 pair files must exist before building the smoke site")
    preprocessing_argv = ["python", "pipeline/preprocess_weekly.py", "--input", "{input_path}",
                          "--input-format", "{input_format}", "--output-dir", "{output_dir}",
                          "--subset", "10", "--first-seen",
                          "/workspace/data/clean/monthly_first_seen/product_first_seen.parquet"]
    site = {"data_kind": "real", "device": "cuda", "configuration_frozen": False,
            "environment_snapshot": str(environment_snapshot), "subsets": subsets,
            "e4": {"csv": str(e4_csv) if e4_csv else None,
                  "parquet": str(e4_parquet) if e4_parquet else None,
                  "preprocessing_argv": preprocessing_argv if e4_csv else None}}
    runs = []
    for run_id, experiment, model, batch_size in [
            ("real-smoke-popularity-cohort-v1", "E1", "popularity", None),
            ("real-smoke-gru-cohort-v1", "E1", "gru", 256),
            ("real-smoke-xlnet-cohort-v1", "E1", "xlnet", 256),
            ("real-smoke-gru-cohort-v1-b32", "E3", "gru", 32),
            ("real-smoke-gru-cohort-v1-b128", "E3", "gru", 128)]:
        runs.append({"run_id": run_id, "experiment": experiment, "kind": "model",
                     "model": model, "subset": "10", "batch_size": batch_size,
                     "split": "validation", "input_format": "session Parquet",
                     "seed": 1, "epochs": 3, "sequence_length": 20,
                     "resource_config": {"device": "cuda", "change_only": "train_batch_size" if experiment == "E3" else None},
                     "train_partitions": "1", "eval_partition": "2",
                     "purpose": "real_data_smoke_cohort_v1"})
    if e4_csv:
        for format_name in ("csv", "parquet"):
            runs.append({"run_id": f"real-smoke-e4-cohort-v1-{format_name}",
                         "experiment": "E4", "kind": "io", "model": None, "subset": "10",
                         "batch_size": None, "split": None, "input_format": format_name,
                         "seed": 1, "epochs": 1, "sequence_length": 20,
                         "resource_config": {"device": "cuda", "change_only": None},
                         "train_partitions": None, "eval_partition": None,
                         "purpose": "real_data_smoke_cohort_v1"})
    (output / "site.json").write_text(json.dumps(site, indent=2) + "\n", encoding="utf-8")
    (output / "matrix.json").write_text(json.dumps({"schema_version": 1, "runs": runs}, indent=2) + "\n", encoding="utf-8")
    return {"site": str(output / "site.json"), "matrix": str(output / "matrix.json"),
            "subset_bindings": len(subsets), "runs": [run["run_id"] for run in runs]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--environment-snapshot", type=Path, required=True)
    parser.add_argument("--e4-csv", type=Path)
    parser.add_argument("--e4-parquet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.manifest, args.data_root, args.cohort,
                                 args.environment_snapshot, args.output,
                                 args.e4_csv, args.e4_parquet), indent=2))
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"Smoke config preparation failed: {error}\n")


if __name__ == "__main__":
    main()
