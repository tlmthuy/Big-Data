"""Build public/run-results.json (contract Part B, sections B2-B7).

Run from the root of a tlmthuy/Big-Data clone:

    python3 ../tv4-demo-web/scripts/export_run_results.py \
      --matrix configs/experiments.json \
      --collector-dir metrics/tv2-config-collector-smoke \
      --output ../tv4-demo-web/public/run-results.json

Records produced:
- one record per planned run in the experiment matrix ("Dự kiến"). Its "Thực tế"
  side stays null until a delivered run with the same run_id is passed in with
  --collector-dir (a real TV2 package) and the run's data_kind is "real";
- one record per collector run found under --collector-dir. Toy runs keep
  data_kind "toy" and point to the matrix run they rehearse via matrix_run_id.

Nothing is computed here. Values are copied from the artifacts with their unit and
scope. Unknown or undelivered values are null. Applicability is decided by the UI.
"""

import argparse
from datetime import date
import json
import subprocess
from pathlib import Path

PLANNED_KEYS = ["train_batch_size", "eval_batch_size", "epochs", "sequence_length", "seed",
                "learning_rate", "subset", "split", "train_partitions", "eval_partition",
                "input_format", "device", "change_only", "artifact_versions"]
ENV_KEYS = ["gpu", "cuda", "driver", "python", "torch", "cpu_model", "cpu_cores", "ram_bytes", "os"]
SCOPE_EVAL = "full_evaluation_wall_v1"


def metric(value, unit, scope):
    return {"value": value, "unit": unit, "scope": scope}


def planned_from(entry):
    """Matrix entry (or the collector's copy of it) -> planned block."""
    neural = entry.get("model") in {"gru", "xlnet"}
    return {
        "train_batch_size": entry.get("batch_size"),
        # The matrix has no eval batch field; the runner passes --eval-batch-size 32 to neural runs.
        "eval_batch_size": 32 if neural else None,
        "epochs": entry.get("epochs"),
        "sequence_length": entry.get("sequence_length"),
        "seed": entry.get("seed"),
        "learning_rate": None,
        "subset": entry.get("subset"),
        "split": entry.get("split"),
        "train_partitions": entry.get("train_partitions"),
        "eval_partition": entry.get("eval_partition"),
        "input_format": entry.get("input_format"),
        "device": (entry.get("resource_config") or {}).get("device"),
        "change_only": (entry.get("resource_config") or {}).get("change_only"),
        "artifact_versions": entry.get("artifact_versions"),
    }


def empty_metrics(kind):
    if kind == "io":
        return {
            "bytes": metric(None, "bytes", "Input file size"),
            "read_seconds": metric(None, "s", "Full streamed decode, excluding pair verification"),
            "peak_read_process_rss_bytes": metric(None, "bytes", "RSS sampled at batch boundaries"),
            "preprocessing_elapsed_seconds": metric(None, "s", "TV1 preprocessing command including its input read"),
            "elapsed_seconds": metric(None, "s", "Whole launched command (collector)"),
            "peak_process_tree_rss_bytes": metric(None, "bytes", "Sampled parent+child RSS; shared pages may be counted twice"),
        }
    return {
        "Recall@20": metric(None, "ratio", None),
        "NDCG@20": metric(None, "ratio", None),
        "train_with_input_scan_seconds": metric(None, "s", "Training stages including input scan"),
        "inference_seconds": metric(None, "s", SCOPE_EVAL),
        "inference_ms_per_session": metric(None, "ms/session", SCOPE_EVAL + " (includes I/O)"),
        "inference_sessions_per_second": metric(None, "sessions/s", SCOPE_EVAL + " (includes I/O)"),
        "elapsed_seconds": metric(None, "s", "Whole launched command (collector)"),
        "peak_process_tree_rss_bytes": metric(None, "bytes", "Sampled parent+child RSS; shared pages may be counted twice"),
        "peak_cuda_reserved_bytes": metric(None, "bytes", "Peak PyTorch CUDA allocator reservation"),
        "cost": metric(None, None, None),
    }


def base_record(entry, run_id):
    kind = entry.get("kind", "model")
    return {
        "experiment": entry["experiment"],
        "run_id": run_id,
        "matrix_run_id": entry["run_id"],
        "kind": kind,
        "model": entry.get("model"),
        "status": None,
        "data_kind": None,
        "exclusion_note": None,
        "planned": planned_from(entry),
        "actual": {key: None for key in PLANNED_KEYS if key != "change_only"},
        "environment": {key: None for key in ENV_KEYS},
        "metrics": empty_metrics(kind),
        "sources": {"matrix": "configs/experiments.json", "runner": "scripts/runs/run_experiments.py",
                    "run": None, "metrics": None, "environment": None},
    }


def fill_from_collector(record, run_dir, team_root):
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    meta = run.get("metadata", {})
    rel = run_dir.resolve().relative_to(team_root).as_posix()
    record["status"] = run.get("status")
    record["data_kind"] = meta.get("data_kind")
    if run.get("status") == "failed":
        record["exclusion_note"] = f"Collector status failed (exit code {run.get('exit_code')})"
    record["sources"]["run"] = f"{rel}/run.json"
    record["metrics"]["elapsed_seconds"]["value"] = run.get("elapsed_seconds")
    record["metrics"]["peak_process_tree_rss_bytes"]["value"] = run.get("peak_process_tree_rss_bytes")

    metrics_path = run_dir / "artifacts" / "metrics.json"
    if not metrics_path.is_file():
        return record
    m = json.loads(metrics_path.read_text(encoding="utf-8"))
    if m.get("run_id") != record["run_id"]:
        raise ValueError(f"{run_dir}: metrics run_id {m.get('run_id')} != collector {record['run_id']}")
    record["sources"]["metrics"] = f"{rel}/artifacts/metrics.json"
    cfg = m.get("config", {})
    neural = m.get("model") in {"gru", "xlnet"}
    record["actual"].update({
        "train_batch_size": cfg.get("batch_size") if neural else None,
        "eval_batch_size": cfg.get("eval_batch_size") if neural else None,
        "epochs": cfg.get("epochs") if neural else None,
        "sequence_length": None,  # not recorded in metrics.json (contract B3, NEED TV2)
        "seed": cfg.get("seed") if neural else None,
        "learning_rate": cfg.get("learning_rate") if neural else None,
        "subset": m.get("subset"),
        "split": m.get("eval_split"),
        "train_partitions": m.get("train_days"),
        "eval_partition": m.get("eval_day"),
        "input_format": None,
        "device": m.get("device"),
        "artifact_versions": meta.get("versions"),
    })
    scope = f"{m.get('n_sessions')} session(s), split {m.get('eval_split')}, partition {m.get('eval_day')}"
    record["metrics"]["Recall@20"].update(value=m.get("Recall@20"), scope=scope)
    record["metrics"]["NDCG@20"].update(value=m.get("NDCG@20"), scope=scope)
    for key in ["train_with_input_scan_seconds", "inference_seconds", "inference_ms_per_session",
                "inference_sessions_per_second", "peak_cuda_reserved_bytes"]:
        record["metrics"][key]["value"] = m.get(key)
    if m.get("inference_timing_protocol") not in (None, SCOPE_EVAL):
        raise ValueError(f"{run_dir}: unexpected timing protocol {m.get('inference_timing_protocol')}")
    record["environment"].update({
        "gpu": m.get("gpu"), "cuda": m.get("cuda"), "python": m.get("python"),
        "torch": (m.get("packages") or {}).get("torch"),
        "platform": m.get("platform"),
    })
    record["sources"]["environment"] = (
        f"{rel}/artifacts/metrics.json (gpu/cuda/python/packages); full snapshot "
        f"{(meta.get('environment') or {}).get('sha256', '')[:12]} not committed"
    )
    return record


def team_commit(root):
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


BASELINE_FIELDS = (
    "gpu", "vram", "cpu_model", "cpu_cores", "ram", "os", "kernel", "driver",
    "cuda_driver", "cuda_toolkit", "python", "torch", "transformers4rec",
)


def environment_baseline(root, commit):
    readme = Path("environment/README.md")
    inspect = Path("environment/logs/04-docker-image-inspect.json")
    heading = "## Bản ghi runtime chính thức"
    text = (root / readme).read_text(encoding="utf-8")
    if heading not in text:
        raise ValueError(f"{readme}: missing runtime table heading")
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) != 2:
            raise ValueError(f"{readme}: expected a two-column runtime table")
        label, value = columns
        rows[label.strip("`").casefold().replace(" ", "_")] = value.strip("`")
    missing = set(BASELINE_FIELDS) - rows.keys()
    if missing:
        raise ValueError(f"{readme}: missing runtime table fields {', '.join(sorted(missing))}")
    digests = json.loads((root / inspect).read_text(encoding="utf-8"))[0]["RepoDigests"]
    if len(digests) != 1:
        raise ValueError(f"{inspect}: expected one unambiguous image digest")
    return {
        **{key: rows[key] for key in BASELINE_FIELDS},
        "merlin_image_digest": digests[0],
        "source": {"files": [str(readme), str(inspect)], "team_commit": commit},
        "scope": "VM runtime verified 21/11, not tied to a specific run",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--collector-dir", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--without-vm-baseline", action="store_true", help="Export when the verified TV3 inputs are unavailable")
    parser.add_argument("--team-commit", help="Source revision when exporting from a Git archive")
    args = parser.parse_args()
    team_root = Path.cwd().resolve()
    commit = args.team_commit or team_commit(team_root)
    try:
        matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
        entries = {entry["run_id"]: entry for entry in matrix["runs"]}
        records = {run_id: base_record(entry, run_id) for run_id, entry in entries.items()}
        by_output = {entry["output_path"]: run_id for run_id, entry in entries.items()}

        for collector_dir in args.collector_dir:
            for run_dir in sorted(p.parent for p in collector_dir.glob("*/run.json")):
                run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
                planned = run["metadata"]["run"]
                run_id = planned["run_id"]
                matrix_id = by_output.get(planned.get("output_path"))
                if matrix_id is None:
                    raise ValueError(f"{run_dir}: no matrix run with output_path {planned.get('output_path')}")
                if run_id == matrix_id and run["metadata"].get("data_kind") == "real":
                    record = records[matrix_id]  # delivered official run fills the matrix record
                else:
                    record = base_record(dict(planned, run_id=matrix_id), run_id)
                    records[run_id] = record
                fill_from_collector(record, run_dir, team_root)

        payload = {
            "schema": "tv4-run-results/v1",
            "package_id": None,
            "confirmed_by_tv2": False,
            "team_commit": commit,
            "generated_at": date.today().isoformat(),
            "data_kind": "unconfirmed",
            "environment_baseline": None if args.without_vm_baseline else environment_baseline(team_root, commit),
            "matrix_decisions": matrix.get("decisions"),
            "runs": list(records.values()),
        }
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        toy = sum(r["data_kind"] == "toy" for r in records.values())
        print(f"Wrote {len(records)} records ({len(entries)} planned, {toy} toy) to {args.output}")
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Export failed: {error}\n")


if __name__ == "__main__":
    main()
