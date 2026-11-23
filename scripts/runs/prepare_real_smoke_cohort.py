"""Prepare a deterministic, provenance-recorded real-data validation cohort."""

import argparse
import hashlib
import json
from pathlib import Path

from evaluation.data import Catalog, audit_sessions, read_sessions
from evaluation.run_popularity import fingerprint, sha256


def select_rows(table, count, seed, day, split):
    import pyarrow as pa

    if "user_session" not in table.column_names or "product_id-list" not in table.column_names:
        raise ValueError("Source partition lacks required session sequence columns")
    session_ids = table["user_session"].to_pylist()
    if any(value is None for value in session_ids):
        raise ValueError("Source partition contains null session IDs")
    normalized = [str(value) for value in session_ids]
    if len(set(normalized)) != len(normalized):
        raise ValueError("Source partition contains duplicate session IDs")
    ranked = sorted(range(len(normalized)), key=lambda i: (
        hashlib.sha256(f"real-smoke-cohort-v1|{seed}|{day}|{split}|{normalized[i]}".encode()).hexdigest(),
        normalized[i]))
    if count < 1 or count > len(ranked):
        raise ValueError(f"Requested {count} {split} sessions, source has {len(ranked)}")
    indices = ranked[:count]
    selected = table.take(pa.array(indices, type=pa.int64()))
    return selected, [session_ids[i] for i in indices]


def prepare(sessions, catalog_path, schema_path, split_manifest_path, output,
            workflow_manifest_path, train_day=1, eval_day=2, train_count=256, eval_count=64, seed=42):
    import pyarrow.parquet as pq

    sessions, catalog_path = Path(sessions), Path(catalog_path)
    schema_path, split_manifest_path, workflow_manifest_path, output = map(
        Path, (schema_path, split_manifest_path, workflow_manifest_path, output))
    if output.exists():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    if eval_day != train_day + 1:
        raise ValueError("Smoke must use validation day t+1 after train day t")
    catalog = Catalog.load(catalog_path)
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    workflow_manifest = json.loads(workflow_manifest_path.read_text(encoding="utf-8"))
    if split_manifest.get("no_overlap_and_complete_coverage") is not True:
        raise ValueError("Official split manifest does not attest complete, disjoint membership")
    workflow_dir = workflow_manifest_path.parent
    mapping_path = workflow_dir / "product_mapping.parquet"
    workflow_root = workflow_dir.parent
    expected_catalog = split_manifest["catalog_sha256"]
    expected_schema = split_manifest["schema_sha256"]
    checksums = workflow_manifest["checksums"]
    if (sha256(catalog_path) != expected_catalog or sha256(schema_path) != expected_schema
            or sha256(catalog_path) != checksums["catalog.json"]
            or sha256(schema_path) != checksums["processed_nvt/schema.pbtxt"]
            or sha256(mapping_path) != checksums["product_mapping.parquet"]):
        raise ValueError("Schema/mapping/catalog checksum differs from same-run workflow/split manifests")
    workflow_input_hash = workflow_manifest["input_sha256"]
    split_input_hash = split_manifest["input_hashes"].get("part_0.parquet")
    if (sha256(workflow_root / "week.parquet") != workflow_input_hash
            or sha256(workflow_dir / "processed_nvt/part_0.parquet") != split_input_hash):
        raise ValueError("Workflow weekly input or split sequence checksum differs from its same-run manifest")
    if workflow_manifest.get("technical_ids") != {
            key: int(value) for key, value in json.loads(catalog_path.read_text(encoding="utf-8"))["technical_ids"].items()
            if key in {"padding", "null", "oov"}}:
        raise ValueError("Catalog technical IDs differ from the fitted workflow")
    if workflow_manifest.get("product_vocabulary_size") != len(catalog.products):
        raise ValueError("Catalog cardinality differs from fitted workflow vocabulary")

    full_counts = audit_sessions(sessions, catalog)
    split_counts = {(r["day_index"], r["split"]): r["n_sessions"] for r in full_counts}
    distinct_counts = {(r["day_index"], r["split"]): r["n_items"] for r in full_counts}
    interaction_counts = {}
    for row in read_sessions(sessions):
        key = (row["day_index"], row["split"])
        interaction_counts[key] = interaction_counts.get(key, 0) + len(catalog.sequence(row["product_ids"]))
    for row in split_manifest["counts"]:
        key = (row["day_index"], {"valid": "validation"}.get(row["split"], row["split"]))
        if (split_counts.get(key, 0) != row["sessions"]
                or distinct_counts.get(key, 0) != row["distinct_items"]
                or interaction_counts.get(key, 0) != row["item_interactions"]):
            raise ValueError(f"Source counts for {key} differ from split manifest: "
                             f"actual={(split_counts.get(key, 0), distinct_counts.get(key, 0), interaction_counts.get(key, 0))}, "
                             f"expected={(row['sessions'], row['distinct_items'], row['item_interactions'])}")
        source_file = sessions / row["path"]
        if sha256(source_file) != row["sha256"]:
            raise ValueError(f"Partition checksum mismatch: {source_file}")

    train_path = sessions / str(train_day) / "train.parquet"
    eval_path = sessions / str(eval_day) / "valid.parquet"
    train_table, train_ids = select_rows(pq.read_table(train_path), train_count, seed, train_day, "train")
    eval_table, eval_ids = select_rows(pq.read_table(eval_path), eval_count, seed, eval_day, "validation")
    train_sequences = train_table["product_id-list"].to_pylist()
    eval_sequences = eval_table["product_id-list"].to_pylist()
    for sequence in train_sequences + eval_sequences:
        catalog.sequence(sequence)
    if set(map(str, train_ids)) & set(map(str, eval_ids)):
        raise ValueError("Train and validation cohort session IDs overlap")

    output.mkdir(parents=True)
    for day, name, table in [(train_day, "train", train_table), (eval_day, "valid", eval_table)]:
        target = output / "sessions" / str(day) / f"{name}.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, target, compression="snappy")
    cohort = {
        "cohort_version": 1,
        "selection_rule": "ascending SHA-256(real-smoke-cohort-v1|seed|day_index|split|user_session), deterministic tie by session ID",
        "seed": seed,
        "source_split_manifest": fingerprint(split_manifest_path),
        "source_workflow_manifest": fingerprint(workflow_manifest_path),
        "workflow_week_input_sha256": workflow_input_hash,
        "split_sequence_input_sha256": split_input_hash,
        "source_sessions": fingerprint(sessions),
        "catalog": fingerprint(catalog_path),
        "schema": fingerprint(schema_path),
        "train": {"day_index": train_day, "split": "train", "n_sessions": len(train_ids),
                  "session_ids": train_ids, "source_partition": str(train_path),
                  "source_sha256": sha256(train_path), "cohort_sha256": sha256(output / "sessions" / str(train_day) / "train.parquet")},
        "validation": {"day_index": eval_day, "split": "validation", "n_sessions": len(eval_ids),
                       "session_ids": eval_ids, "source_partition": str(eval_path),
                       "source_sha256": sha256(eval_path), "cohort_sha256": sha256(output / "sessions" / str(eval_day) / "valid.parquet")},
        "test_partition_used": False,
        "audit": {"full_source_partition_counts": full_counts,
                  "technical_ids": sorted(catalog.technical_ids),
                  "real_catalog_items": len(catalog.products),
                  "catalog_id_min": min(catalog.products), "catalog_id_max": max(catalog.products),
                  "schema_sha256": expected_schema},
    }
    (output / "cohort.json").write_text(json.dumps(cohort, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return cohort


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--workflow-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-day", type=int, default=1)
    parser.add_argument("--eval-day", type=int, default=2)
    parser.add_argument("--train-count", type=int, default=256)
    parser.add_argument("--eval-count", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.sessions, args.catalog, args.schema, args.split_manifest,
                                 args.output, args.workflow_manifest, args.train_day, args.eval_day,
                                 args.train_count, args.eval_count, args.seed), indent=2))
    except (ValueError, KeyError, OSError, ImportError) as error:
        parser.exit(1, f"Cohort preparation failed: {error}\n")


if __name__ == "__main__":
    main()
