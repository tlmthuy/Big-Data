"""Export the TV1 dataset overview. Run from the team checkout."""
import argparse
import csv
from datetime import date
import json
import re
from pathlib import Path

from export_run_results import team_commit

AUDIT = Path("data/raw_audit.csv")
VERIFIED = Path("data/manifests/e2_preprocessing_verified.json")
SMOKE = VERIFIED.with_name("e4_preprocessing_smoke.json")
SAMPLING = VERIFIED.with_name("session_sampling_manifest.json")
CLEANUP = VERIFIED.with_name("timestamp_session_cleanup.json")
DICTIONARY = Path("docs/data_dictionary.md")
PROTOCOL = Path("docs/modeling/model_protocol.md")
SUBSETS = (10, 25, 50, 100)
FIELDS = ("n_events", "events_after_repeat_removal", "sequence_count", "vocabulary_size")
PROFILE_FIELDS = ("distinct", "missing", "event_types", "session_length_histogram")
TIMINGS = (
    "preprocessing_seconds", "read_seconds", "prepare_seconds", "workflow_seconds", "split_seconds",
    "input_format", "input_bytes",
)


def raw_audit():
    with AUDIT.open(newline="", encoding="utf-8-sig") as file:
        rows = {(r["metric"], r["column"]): r for r in csv.DictReader(file) if r["scope"] == "raw_month"}
    return {
        "row_count": int(rows["row_count", ""]["count"]),
        "min_timestamp_utc": rows["min_timestamp_utc", "event_time"]["value"],
        "max_timestamp_utc": rows["max_timestamp_utc", "event_time"]["value"],
        "missing": {column: int(rows["missing_count", column]["count"]) for column in ("brand", "category_code")},
        "invalid_timestamps": int(rows["invalid_timestamp_count", "event_time"]["count"]),
        "distinct": {column: int(rows["distinct_count", column]["count"]) for column in ("event_type", "category_code", "brand")},
        "source": str(AUDIT),
    }


def data_context():
    sampling = json.loads(SAMPLING.read_text(encoding="utf-8"))
    cleanup = json.loads(CLEANUP.read_text(encoding="utf-8"))
    columns = re.search(r"(\d+) cột", DICTIONARY.read_text(encoding="utf-8"))
    protocol = PROTOCOL.read_text(encoding="utf-8")
    split = re.search(r"khoảng (\d+/\d+/\d+)", protocol)
    seed = re.search(r'GPU dùng seed `(\d+)`', protocol)
    top_k = re.search(r"K = (\d+)", protocol)
    return {
        "sampling": {
            **{key: sampling.get(key) for key in ("scope", "seed", "input_bytes", "population_sessions", "hash_rule", "event_retention", "checks")},
            "outputs": [{key: row.get(key) for key in ("percent", "session_count", "actual_session_ratio")} for row in sampling["outputs"]],
            "source": str(SAMPLING),
        },
        "cleanup_reference": {
            **{key: cleanup.get(key) for key in ("engine", "timestamp_parse_failures", "consecutive_repeat_rows_removed")},
            "source": str(CLEANUP),
        },
        "raw_schema": {"columns": int(columns[1]) if columns else None, "source": str(DICTIONARY)},
        "evaluation_protocol": {
            "split_ratio": split[1] if split else None, "seed": int(seed[1]) if seed else None,
            "top_k": int(top_k[1]) if top_k else None, "source": str(PROTOCOL),
        },
    }


def export(raw_only, show_measurements):
    index = {}
    smoke = None
    if not raw_only:
        records = json.loads(VERIFIED.read_text(encoding="utf-8"))["runs"]
        index = {int(row["subset"]): row for row in records}
        if len(records) != len(index) or set(index) != set(SUBSETS):
            raise ValueError(f"{VERIFIED}: expected one record per cuDF subset")
        smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
        if not isinstance(smoke["smoke_scope"], str):
            raise ValueError(f"{SMOKE}: expected smoke_scope text")
        formats = {row["input_format"]: row for row in smoke["runs"]}
        if len(smoke["runs"]) != 2 or formats.keys() != {"csv", "parquet"}:
            raise ValueError(f"{SMOKE}: expected one CSV and one Parquet smoke run")
        smoke = {
            "smoke_scope": smoke["smoke_scope"],
            "formats": [
                {"format": name, "input_bytes": row["input_bytes"], "bytes": row["input_bytes"],
                 "read_seconds": row.get("read_seconds"), "preprocessing_seconds": row.get("preprocessing_seconds")}
                for name, row in formats.items()
            ],
            "source": str(SMOKE),
            **{key: smoke.get(key) for key in ("input_rows_identical_in_order", "split_membership_identical")},
        }
    commit = team_commit(Path.cwd())
    if not commit:
        raise ValueError("Cannot identify the team commit")
    shared_first_seen = {row.get("first_seen_seconds") for row in index.values()}
    if len(shared_first_seen) > 1:
        raise ValueError(f"{VERIFIED}: expected one shared monthly first-seen cost")
    return {
        **data_context(),
        "schema": "tv4-dataset-overview/v1",
        "team_commit": commit,
        "generated_at": date.today().isoformat(),
        "data_kind": "unconfirmed",
        "confirmed_by_tv1": False,
        "raw_month": raw_audit(),
        "subsets": [
            {"subset": subset, "scope": "first week of 2019-10, cuDF weekly cleanup",
             **{key: index[subset][key] if subset in index else None for key in FIELDS},
             **{key: index[subset]["profile"].get(key) if subset in index else None for key in PROFILE_FIELDS},
             "source": str(VERIFIED) if subset in index else None}
            for subset in SUBSETS
        ],
        "pipeline_measurements": {
            "status": "unconfirmed", "show": show_measurements,
            "e2_source": str(VERIFIED) if index else None,
            "first_seen_seconds": next(iter(shared_first_seen), None),
            "e2": [{"subset": subset, **{key: row.get(key) for key in TIMINGS}} for subset, row in index.items()],
            "e4_smoke": [] if smoke is None else [smoke],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-only", action="store_true", help="Export the raw audit when verified manifests are unavailable")
    parser.add_argument("--show-pipeline-measurements", action="store_true")
    args = parser.parse_args()
    try:
        content = json.dumps(export(args.raw_only, args.show_pipeline_measurements), ensure_ascii=False, indent=2) + "\n"
        if len(content.encode("utf-8")) >= 200_000:
            raise ValueError("Dataset overview must be under 200 KB")
        args.output.write_text(content, encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Dataset overview export failed: {error}\n")


if __name__ == "__main__":
    main()
