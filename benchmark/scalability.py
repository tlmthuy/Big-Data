"""E5 consumes successful E2 logs; never trains another model."""

import argparse
import csv
import json
import math
from pathlib import Path

from evaluation.timing import INFERENCE_PROTOCOL


def summarize(root):
    rows = []
    common_first_seen = None
    reference_run = None
    for path in sorted(Path(root).glob("*/run.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        meta = run.get("metadata", {})
        config = meta.get("run", {})
        if config.get("experiment") != "E2" or run.get("status") != "passed":
            continue
        if meta.get("data_kind") == "toy" or meta.get("purpose") == "toy_smoke":
            continue
        metrics_path = path.parent / "artifacts" / "metrics.json"
        model = json.loads(metrics_path.read_text(encoding="utf-8"))
        if model.get("inference_timing_protocol") != INFERENCE_PROTOCOL:
            raise ValueError("E2 inference timing protocol missing/obsolete; rerun instead of mixing old timings")
        effective = model["training_config"]
        for key in ["model", "batch_size", "epochs", "seed"]:
            if effective[key] != config[key]:
                raise ValueError(f"E2 matrix and effective training config disagree: {key}")
        if model["config"].get("checkpoint"):
            raise ValueError("E2 must measure fresh training, not checkpoint replay")
        expected_days = list(range(1, model["eval_day"]))
        if model["train_days"] != expected_days or model["eval_split"] != config["split"]:
            raise ValueError("E2 did not use daily train 1..D-1 / final evaluation D")
        if max(r["day_index"] for r in model["split_counts"]) != model["eval_day"]:
            raise ValueError("E2 final evaluation is not the last available partition")
        signature = (json.dumps(effective, sort_keys=True),
                     json.dumps(model["source_sha256"], sort_keys=True),
                     model["config"]["eval_batch_size"], model["config"]["device"],
                     config["sequence_length"], config["split"],
                     json.dumps(meta["environment"], sort_keys=True))
        if reference_run is None:
            reference_run = signature
        elif signature != reference_run:
            raise ValueError("E2 effective model/config/code/environment changed between subsets")
        data = meta["pipeline_metrics"]
        n = data["n_events"]
        values = [data["read_seconds"], data["preprocessing_seconds"], data["first_seen_seconds"],
                  model["train_with_input_scan_seconds"], model["inference_seconds"]]
        if type(n) is not int or n <= 0 or any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("E2 timings/counts must be finite, nonnegative and measured")
        first_seen = (data["first_seen_artifact"], data["first_seen_seconds"])
        if common_first_seen is None:
            common_first_seen = first_seen
        elif common_first_seen != first_seen:
            raise ValueError("E2 subsets must identify the same measured first-seen artifact/cost")
        stages = {"raw_read": values[0], "preprocessing_excluding_raw_read_and_first_seen": values[1],
                     "train_including_sequence_io": values[3], "final_evaluation_including_io": values[4]}
        total = sum(stages.values())
        rows.append({"run_id": config["run_id"], "subset": config["subset"], "n_events": n,
                     "trained_partition_count": len(model["train_days"]), "eval_day": model["eval_day"],
                     **stages, "composed_seconds_excluding_first_seen": total,
                     "seconds_per_million_events": total * 1_000_000 / n,
                     "bottleneck": max(stages, key=stages.get),
                     "first_seen_seconds_shared": values[2],
                     "composed_seconds_with_first_seen": total + values[2],
                     "process_wall_seconds": run["elapsed_seconds"],
                     "peak_model_process_tree_rss_bytes": run["peak_process_tree_rss_bytes"],
                     "source_log": str(path)})
    if not rows:
        raise ValueError("No successful E2 logs with model metrics and pipeline timings")
    subsets = [r["subset"] for r in rows]
    if len(subsets) != len(set(subsets)):
        raise ValueError("Multiple successful runs for a subset; select one log set explicitly")
    return sorted(rows, key=lambda r: int(r["subset"]))


def write_outputs(rows, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "scalability.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    # Standalone SVG; x is actual events, not the nominal session sampling rate.
    xs = [r["n_events"] for r in rows]
    ys = [r["composed_seconds_excluding_first_seen"] for r in rows]
    points = [(70 + 650 * x / max(xs), 335 - 275 * y / max(max(ys), 1e-9)) for x, y in zip(xs, ys)]
    dots = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    labels = "".join(f'<text x="{x:.2f}" y="{y-10:.2f}" font-size="12">{r["subset"]}% sessions</text>'
                     for (x, y), r in zip(points, rows))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="420" viewBox="0 0 820 420">
<rect width="820" height="420" fill="white"/><g font-family="sans-serif" fill="#172554">
<text x="70" y="25">E5 — composed measured stages; shared first-seen excluded</text>
<path d="M70 55V335H745" fill="none" stroke="#475569"/>
<polyline points="{dots}" fill="none" stroke="#2563eb" stroke-width="3"/>{labels}
<text x="270" y="390">Weekly events (0 to {max(xs):,})</text>
<text x="10" y="50">Seconds</text><text x="15" y="70">{max(ys):.2f}</text><text x="40" y="335">0</text>
</g></svg>'''
    (output / "scalability.svg").write_text(svg, encoding="utf-8")
    complete = {r["subset"] for r in rows} == {"10", "25", "50", "100"}
    (output / "summary.json").write_text(json.dumps({"status": "complete" if complete else "partial",
        "rows": rows, "limitations": ["Composed stage timings are not one observed end-to-end process wall time.",
        "Train includes sequence reads; standalone raw read is a different earlier stage.",
        "Final inference is compute/ranking only; validation, audit, checksum and serialization excluded.",
        "First-seen shared cost is reported separately; do not sum it four times.",
        "One run per subset; no variance or confidence interval measured."]}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--logs", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    write_outputs(summarize(a.logs), a.output)
