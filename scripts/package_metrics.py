"""Issue and verify one CSV/JSON metrics release for TV4 and TV5."""

import csv
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path("metrics/releases/tv2-20261124")
TABLES = Path("reports/tables/tv2-20261124")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def typed(value):
    if value == "":
        return None
    try:
        result = json.loads(value)
    except ValueError:
        return value
    return result if isinstance(result, (int, float, bool)) else value


def csv_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [{k: typed(v) for k, v in r.items()} for r in csv.DictReader(handle)]


def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    receipts = {"TV4": None, "TV5": None}
    if (ROOT / "manifest.json").exists():
        receipts.update(load(ROOT / "manifest.json").get("recipient_acknowledgements", {}))
    tables, configs, registry = {}, {}, []
    for experiment in ("E1", "E2", "E3", "E4", "E5"):
        source = TABLES / (experiment + ".csv")
        shutil.copyfile(source, ROOT / source.name)
        rows = csv_rows(source)
        tables[experiment] = rows
        for row in rows:
            run_id = row["run_id"]
            if experiment in ("E1", "E2", "E3"):
                model, run = load(row["source_metrics"]), load(row["source_run"])
                configs[run_id] = {
                    "effective_config": model["config"], "training_config": model.get("training_config"),
                    "command_argv": run["argv"], "run_metadata": run["metadata"],
                    "artifacts": model["artifacts"], "split_counts": model["split_counts"],
                    "source_sha256": model["source_sha256"], "git_commit": model["git_commit"],
                    "runtime": {k: model.get(k) for k in ("python", "packages", "device", "gpu", "cuda")},
                    "warmup": run.get("warm_up_policy"), "cache": run.get("cache_policy"),
                    "source_run": row["source_run"], "source_metrics": row["source_metrics"]}
                status = run["status"]
            elif experiment == "E4":
                measured = load(row["source_metrics"])
                directory = Path(row["source_metrics"]).parent
                configs[run_id] = {"preprocessing_argv": measured["preprocessing"]["argv"],
                    "verification": measured["verification"], "cache": measured["cache_policy"],
                    "read_scope": measured["read_scope"], "schema_policy": measured["schema_policy"],
                    "workflow_manifest": load(directory / "preprocessed/workflow/manifest.json"),
                    "split_manifest": load(directory / "preprocessed/splits/manifest.json"),
                    "timings": load(directory / "preprocessed/timings.json"),
                    "source_metrics": row["source_metrics"]}
                status = measured["status"]
            else:
                status = "derived_from_verified_E2"
            registry.append({"experiment": experiment, "run_id": run_id, "status": status,
                             "source": row.get("source_metrics", row.get("source_log"))})
    save(ROOT / "metrics.json", {"schema_version": 1, "owner": "TV2", "data_kind": "real",
                                 "tables": tables, "E5_aggregation_only": True})
    save(ROOT / "configs.json", configs)
    save(ROOT / "run_registry.json", {"scope": "selected official runs; not full failed-attempt inventory",
         "excluded": {"e4-010-csv": "smoke pair, superseded by full E4", "e4-010-parquet": "smoke pair, superseded by full E4"},
         "runs": registry})
    save(ROOT / "data_dictionary.json", {
        "accuracy_units": "Recall@20/NDCG@20 fractions [0,1], single target per valid session",
        "time_units": "seconds unless named ms_per_session",
        "memory_units": "bytes; missing is null, not measured zero",
        "inference_protocol": "full_evaluation_wall_v1; complete evaluation including I/O and metrics",
        "train_seconds_including_sequence_io": "training only, excludes daily validation",
        "process_wall_seconds": "whole model process; not added to component timings",
        "sampled_rss_bytes_descriptive_only": "may double-count shared pages/miss short peaks; no cross-config RAM conclusion",
        "sampled_gpu_process_bytes": "sampled process GPU memory, not CUDA allocated/reserved or total GPU used",
        "sampled_gpu_status": "observed_legacy_flag from observation_available=true; unavailable -> null bytes",
        "raw_week_users": "before product deduplication: raw_subset_counts.csv",
        "cleaned_week_users": "after cuDF product deduplication: selected E2 profile",
        "E2_accuracy": "different eval/catalog across subsets; not isolated train-size gain",
        "E3_accuracy": "validation; do not compare directly with E1/E2 test",
        "E4_preprocessing_wall": "includes its own read; do not add standalone read",
        "E5_composed": "raw read + preprocess excluding raw read/first-seen + train with sequence I/O + final eval; not observed E2E wall",
        "first_seen_shared": "add once per complete scenario; separate shared build cost"})
    groups = {
        "package": sorted(p for p in ROOT.iterdir() if p.is_file() and p.name != "manifest.json"),
        "runtime": [Path(p) for p in ["environment/README.md", "environment/logs/02-import-test.log",
                     "environment/logs/04-docker-image-inspect.json", "environment/pip_freeze_baseline.txt"]],
        "analysis": [TABLES / "analysis.md", TABLES / "instructor_feedback_analysis.md",
                     Path("reports/figures/tv2-20261124/scalability/scalability.svg")],
        "evidence": [Path("metrics/tv2-analysis-20261124") / p for p in
                     ["source_manifest.json", "prediction_checks.json", "analysis_validation.json", "supplement_validation.json"]]}
    save(ROOT / "manifest.json", {"package_id": "tv2-20261124", "owner": "TV2", "recipients": ["TV4", "TV5"],
        "status": "TV4_checked_TV5_pending" if receipts["TV4"] and not receipts["TV5"] else "TV2_verified_available_for_recipient_review",
        "recipient_acknowledgements": receipts,
        "receipt_rule": "Do not infer human acceptance from AI review or publication",
        "checksum_rule": "CRLF normalized to LF; raw source_manifest uses exact archived bytes",
        "files_sha256": {group: {p.as_posix(): digest(p) for p in paths} for group, paths in groups.items()},
        "reproduce_argv": ["python", "-m", "scripts.analyze_results"],
        "use_rule": "TV4/TV5 use the same TV2 package; additional numbers/changes require TV2 confirmation",
        "limits": ["single run/seed", "sampled RSS descriptive", "E2 changing eval/catalog", "E4 warm cache", "pre-split workflow fit"]})


def verify():
    for paths in load(ROOT / "manifest.json")["files_sha256"].values():
        for path, expected in paths.items():
            if digest(path) != expected:
                raise ValueError(f"Package checksum mismatch: {path}")
    tables = load(ROOT / "metrics.json")["tables"]
    for experiment, rows in tables.items():
        if csv_rows(ROOT / (experiment + ".csv")) != rows:
            raise ValueError(f"CSV/JSON differ: {experiment}")
    return {"status": "passed", "tables": len(tables), "configs": len(load(ROOT / "configs.json")),
            "recipient_acceptance": "not_inferred"}


if __name__ == "__main__":
    build()
    print(json.dumps(verify(), indent=2))
