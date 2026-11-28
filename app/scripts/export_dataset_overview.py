"""Export the TV1 dataset overview. Run from the team checkout."""
import argparse
import csv
from datetime import date
import json
import re
from pathlib import Path

from team_repo import team_commit

TEAM_ROOT = Path(__file__).resolve().parents[2] / "Big-Data"
AUDIT = TEAM_ROOT / "data/raw_audit.csv"
VERIFIED = TEAM_ROOT / "data/manifests/e2_preprocessing_verified.json"
SAMPLING = VERIFIED.with_name("session_sampling_manifest.json")
CLEANUP = VERIFIED.with_name("timestamp_session_cleanup.json")
DICTIONARY = TEAM_ROOT / "docs/data_dictionary.md"
PROTOCOL = TEAM_ROOT / "docs/modeling/model_protocol.md"
SUBSETS = (10, 25, 50, 100)
TABLES = TEAM_ROOT / "reports/tables/tv2-20261124"
SUPPLEMENTARY_FILES = (
    "sampling_population.csv", "subset_distribution.csv", "event_mix_before_after.csv",
    "preprocessing_retention.csv", "split_population.csv",
)


def team_path(path):
    """Path relative to the team repo root, so exports never carry a local home directory."""
    return Path(path).resolve().relative_to(TEAM_ROOT.resolve()).as_posix()


FIELDS = ("n_events", "events_after_repeat_removal", "sequence_count", "vocabulary_size")
PROFILE_FIELDS = ("distinct", "missing", "event_types", "session_length_histogram")


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
        "source": team_path(AUDIT),
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
            "source": team_path(SAMPLING),
        },
        "cleanup_reference": {
            **{key: cleanup.get(key) for key in ("engine", "timestamp_parse_failures", "consecutive_repeat_rows_removed")},
            "source": team_path(CLEANUP),
        },
        "raw_schema": {"columns": int(columns[1]) if columns else None, "source": team_path(DICTIONARY)},
        "evaluation_protocol": {
            "split_ratio": split[1] if split else None, "seed": int(seed[1]) if seed else None,
            "top_k": int(top_k[1]) if top_k else None, "source": team_path(PROTOCOL),
        },
    }


def read_table(name):
    path = TABLES / name
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = []
        for row in csv.DictReader(file):
            converted = {}
            for key, value in row.items():
                if value == "":
                    converted[key] = None
                else:
                    try:
                        converted[key] = int(value)
                    except ValueError:
                        try:
                            converted[key] = float(value)
                        except ValueError:
                            converted[key] = value
            rows.append(converted)
    return rows


def export(raw_only=False):
    supplementary = {} if raw_only else {Path(name).stem: read_table(name) for name in SUPPLEMENTARY_FILES}
    population_by_subset = {int(row["subset_session_threshold_pct"]): row for row in supplementary.get("sampling_population", [])}
    distribution_by_subset = {int(row["subset"]): row for row in supplementary.get("subset_distribution", [])}
    retention_by_subset = {int(row["subset"]): row for row in supplementary.get("preprocessing_retention", [])}
    split_by_subset = {int(row["subset"]): row for row in supplementary.get("split_population", [])}
    distribution_keys = ("length_TV_vs_100", "event_TV_vs_100")
    for subset, row in distribution_by_subset.items():
        if any(not isinstance(row.get(key), (int, float)) for key in distribution_keys):
            raise ValueError(f"subset_distribution.csv: subset {subset} is missing a TV distance")
    for subset, row in split_by_subset.items():
        if not isinstance(row.get("last_partition_D"), int):
            raise ValueError(f"split_population.csv: subset {subset} is missing last_partition_D")
    index = {}
    if not raw_only:
        records = json.loads(VERIFIED.read_text(encoding="utf-8"))["runs"]
        index = {int(row["subset"]): row for row in records}
        if len(records) != len(index) or set(index) != set(SUBSETS):
            raise ValueError(f"{VERIFIED}: expected one record per cuDF subset")
    commit = team_commit(TEAM_ROOT)
    if not commit:
        raise ValueError("Cannot identify the team commit")
    return {
        **data_context(),
        "schema": "tv4-dataset-overview/v1",
        "team_commit": commit,
        "generated_at": date.today().isoformat(),
        "data_kind": "real" if supplementary else "unconfirmed",
        "source_confirmed_by": "TV2 package tv2-20261124 supplementary tables" if supplementary else None,
        "source_package": "tv2-20261124" if supplementary else None,
        "raw_month": raw_audit(),
        "subsets": [
            {"subset": subset, "scope": "first week of 2019-10, cuDF weekly cleanup",
             **{key: index[subset][key] if subset in index else None for key in FIELDS},
             **{key: index[subset]["profile"].get(key) if subset in index else None for key in PROFILE_FIELDS},
             **population_by_subset.get(subset, {}),
             **distribution_by_subset.get(subset, {}),
             **retention_by_subset.get(subset, {}),
             **split_by_subset.get(subset, {}),
             "source": team_path(VERIFIED) if subset in index else None}
            for subset in SUBSETS
        ],
        "supplementary_sources": {name: team_path(TABLES / (name + ".csv")) for name in supplementary},
        "event_mix_before_after": supplementary.get("event_mix_before_after", []),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-only", action="store_true", help="Export the raw audit when verified manifests are unavailable")
    args = parser.parse_args()
    try:
        content = json.dumps(export(args.raw_only), ensure_ascii=False, indent=2) + "\n"
        if len(content.encode("utf-8")) >= 200_000:
            raise ValueError("Dataset overview must be under 200 KB")
        args.output.write_text(content, encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Dataset overview export failed: {error}\n")


if __name__ == "__main__":
    main()
