"""Resolve TV2 experiment configs with TV3 paths; plan first, execute explicitly."""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from benchmark.collect import run_command
from evaluation.run_neural import save_json
from evaluation.run_popularity import fingerprint


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_path(value, label):
    if not value or not Path(value).exists():
        raise ValueError(f"Bind existing {label} in site config")
    return Path(value)


def resolve(run, site, output):
    if run["sequence_length"] != 20 or run["epochs"] < 1 or run["seed"] < 0:
        raise ValueError("Invalid fixed sequence length, epoch or seed in experiment config")
    subset = site["subsets"][run["subset"]]
    versions = {key: subset.get(key) for key in ["workflow_version", "mapping_version", "catalog_version"]}
    if not all(versions.values()):
        raise ValueError("Bind actual workflow/mapping/catalog versions from TV1")
    if run["split"] == "test" and not site.get("configuration_frozen"):
        raise ValueError("Freeze model configurations before final test")
    common = ["--run-id", run["run_id"], "--output", str(output / "artifacts")]
    artifacts = {}
    if run["kind"] == "io":
        pair = site["e4"]
        for name in ["csv", "parquet"]:
            artifacts[name] = fingerprint(require_path(pair.get(name), f"E4 {name}"))
        if not pair.get("preprocessing_argv"):
            raise ValueError("Bind the shared TV1 E4 preprocessing_argv")
        argv = [sys.executable, "-m", "benchmark.format_io", "--csv", pair["csv"],
                "--parquet", pair["parquet"], "--format", run["input_format"],
                "--preprocess-argv", json.dumps(pair["preprocessing_argv"]), *common]
    else:
        if type(subset.get("final_day")) is not int or subset["final_day"] < 2:
            raise ValueError("Bind the actual final_day >= 2 from TV1 membership")
        for name in ["sessions", "schema", "catalog", "preprocessing_manifest"]:
            artifacts[name] = fingerprint(require_path(subset.get(name), name))
        if not Path(subset["sessions"]).is_dir():
            raise ValueError("Official model matrix expects the TV1 session Parquet directory")
        # data completeness/acceptance cannot be inferred from filenames alone.
        if not subset.get("accepted_by_tv2"):
            raise ValueError("TV2 must accept TV1 data before experiment execution")
        if run["model"] == "popularity":
            argv = [sys.executable, "-m", "evaluation.run_popularity", "--sessions", subset["sessions"],
                    "--catalog", subset["catalog"], "--train-through", str(subset["final_day"] - 1),
                    "--eval-split", run["split"], "--subset", run["subset"], *common]
        else:
            argv = [sys.executable, "-m", "evaluation.run_neural", "--model", run["model"],
                    "--data", subset["sessions"], "--schema", subset["schema"],
                    "--catalog", subset["catalog"], "--train-through", str(subset["final_day"] - 1),
                    "--split", run["split"], "--subset", run["subset"],
                    "--batch-size", str(run["batch_size"]), "--eval-batch-size", "32",
                    "--epochs", str(run["epochs"]), "--seed", str(run["seed"]), "--device", site["device"], *common]
            if run["split"] == "test":
                if not site.get("configuration_frozen"):
                    raise ValueError("Freeze model configurations before final test")
                argv += ["--config-frozen"]
    return argv, {"versions": versions, "artifacts": artifacts}


def execute(run, site, root, site_path):
    output = root / run["run_id"]
    if run["kind"] != "io" and site.get("device") != "cuda":
        raise ValueError("Official E1-E3 model runs require the selected GPU runtime")
    snapshot = require_path(site.get("environment_snapshot"), "environment snapshot")
    argv, inputs = resolve(run, site, output)
    preprocessing = None
    if run["experiment"] == "E2":
        path = require_path(site["subsets"][run["subset"]].get("pipeline_metrics"), "measured TV1 pipeline metrics")
        preprocessing = load(path)
        for field in ["n_events", "read_seconds", "preprocessing_seconds", "first_seen_seconds", "first_seen_artifact", "source_log"]:
            if field not in preprocessing:
                raise ValueError(f"pipeline_metrics missing {field}")
        if preprocessing.get("status") != "measured":
            raise ValueError("pipeline_metrics must be measured, not the example template")
        if type(preprocessing["n_events"]) is not int or preprocessing["n_events"] <= 0:
            raise ValueError("pipeline_metrics requires an actual positive event count")
        for field in ["read_seconds", "preprocessing_seconds", "first_seen_seconds"]:
            value = preprocessing[field]
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid measured timing: {field}")
        inputs["pipeline_source_log"] = fingerprint(require_path(preprocessing["source_log"], "pipeline source log"))
        inputs["first_seen_artifact"] = fingerprint(require_path(preprocessing["first_seen_artifact"], "first-seen artifact"))
        inputs["pipeline_metrics"] = fingerprint(path)
    metadata = {"run": run, **inputs, "site_config": fingerprint(site_path),
                "environment": fingerprint(snapshot), "pipeline_metrics": preprocessing,
                "pipeline_timing_scope": "TV1 measured stages reused; model process timed fresh",
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()}
    return run_command(argv, output, metadata)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--matrix", type=Path, default=Path("configs/experiments.json"))
    p.add_argument("--site", type=Path)
    select = p.add_mutually_exclusive_group(required=True)
    select.add_argument("--run-id")
    select.add_argument("--experiment", choices=["E1", "E2", "E3", "E4"])
    p.add_argument("--output-root", type=Path, default=Path("metrics/raw"))
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    runs = [r for r in load(args.matrix)["runs"] if
            r["run_id"] == args.run_id or r["experiment"] == args.experiment]
    if not runs:
        p.error("No matching runs")
    if not args.execute:
        print(json.dumps({"status": "plan_only", "runs": runs,
                          "note": "Bind TV1 paths/versions and GPU environment via --site before --execute"}, indent=2))
        return
    if not args.site:
        p.error("--execute requires --site")
    site = load(args.site)
    failed = []
    for run in runs:
        record = execute(run, site, args.output_root, args.site)
        print(json.dumps({"run_id": run["run_id"], "status": record["status"]}))
        if record["status"] != "passed":
            failed.append(run["run_id"])
    if failed:
        raise SystemExit("Failed runs: " + ", ".join(failed))


if __name__ == "__main__":
    main()
