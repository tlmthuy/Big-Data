"""Create a small raw CSV/Parquet pair retaining every event of sampled sessions."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from benchmark.format_io import COLUMNS, content_fingerprint, prepare_pair
from evaluation.run_popularity import sha256


def prepare(source, output, expected_source_sha256, expected_source_events, session_count=4096, seed=42):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    if not source.is_file():
        raise ValueError(f"Raw source CSV not found: {source}")
    source_hash = sha256(source)
    if source_hash != expected_source_sha256:
        raise ValueError("Raw source CSV checksum differs from selected official E2 input")
    event_counts = Counter()
    total_rows = 0
    with source.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError("Raw source must use the canonical nine-field header")
        for row in reader:
            total_rows += 1
            session = row.get("user_session")
            if session:
                event_counts[session] += 1
    if total_rows != expected_source_events:
        raise ValueError("Raw source row count differs from selected official E2 input")
    if session_count < 1 or session_count > len(event_counts):
        raise ValueError(f"Requested {session_count} sessions, source has {len(event_counts)}")
    selected = sorted(event_counts, key=lambda sid: (
        hashlib.sha256(f"real-smoke-e4-v1|{seed}|{sid}".encode()).hexdigest(), sid))[:session_count]
    selected_set = set(selected)
    output.mkdir(parents=True)
    csv_path, parquet_path = output / "raw.csv", output / "raw.parquet"
    written_counts = Counter()
    with source.open("r", newline="", encoding="utf-8") as src, \
            csv_path.open("w", newline="", encoding="utf-8") as dest:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dest, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            session = row.get("user_session")
            if session in selected_set:
                writer.writerow(row)
                written_counts[session] += 1
    if written_counts != Counter({sid: event_counts[sid] for sid in selected}):
        raise ValueError("Sampled raw CSV did not preserve every event for each selected session")
    converted = prepare_pair(csv_path, parquet_path)
    csv_fingerprint = content_fingerprint(csv_path, "csv")
    parquet_fingerprint = content_fingerprint(parquet_path, "parquet")
    if converted != sum(written_counts.values()) or csv_fingerprint != parquet_fingerprint:
        raise ValueError("CSV/Parquet pair content or full-session event count mismatch")
    result = {
        "scope": "E4 real-data preprocessing smoke pair; not an E4 benchmark result",
        "selection_rule": "ascending SHA-256(real-smoke-e4-v1|seed|user_session), tie by session ID",
        "seed": seed,
        "requested_sessions": session_count,
        "selected_sessions": len(selected),
        "session_ids": selected,
        "events_by_session": dict(sorted(written_counts.items())),
        "n_events": converted,
        "source": {"path": str(source), "sha256": source_hash, "bytes": source.stat().st_size,
                   "n_events": total_rows, "selected_e2_input": True},
        "csv": {"path": str(csv_path), "sha256": sha256(csv_path), "bytes": csv_path.stat().st_size},
        "parquet": {"path": str(parquet_path), "sha256": sha256(parquet_path), "bytes": parquet_path.stat().st_size},
        "fingerprint": csv_fingerprint,
        "all_events_preserved_for_selected_sessions": True,
    }
    (output / "pair.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--session-count", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        selected = next(run for run in manifest["runs"] if str(run["subset"]) == "10")
        print(json.dumps(prepare(args.source, args.output, selected["input_sha256"],
                                 selected["n_events"], args.session_count, args.seed), indent=2))
    except (ValueError, OSError, ImportError) as error:
        parser.exit(1, f"E4 smoke-pair preparation failed: {error}\n")


if __name__ == "__main__":
    main()
