"""E4: identical raw event values/string schema in CSV and Snappy Parquet.

Pair verification is outside the timed read stage. Full preprocessing is a
single TV1 argv template bound to the two formats, never a substitute CPU ETL.
"""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq
import psutil

from benchmark.collect import run_command
from evaluation.run_neural import save_json

COLUMNS = ["event_time", "event_type", "product_id", "category_id", "category_code",
           "brand", "price", "user_id", "user_session"]
SCHEMA = pa.schema([(name, pa.string()) for name in COLUMNS])


def read_batches(path, format_name):
    if format_name == "csv":
        reader = csv.open_csv(path, convert_options=csv.ConvertOptions(
            column_types={name: pa.string() for name in COLUMNS}, strings_can_be_null=False))
        if reader.schema != SCHEMA:
            raise ValueError("CSV must contain the nine raw fields in canonical order")
        yield from reader
    else:
        reader = pq.ParquetFile(path)
        if not reader.schema_arrow.equals(SCHEMA, check_metadata=False):
            raise ValueError("E4 Parquet must use the same nine string columns as CSV")
        yield from reader.iter_batches(batch_size=65536)


def prepare_pair(csv_path, parquet_path):
    parquet_path = Path(parquet_path)
    if parquet_path.exists():
        raise ValueError("Pair output already exists")
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with pq.ParquetWriter(parquet_path, SCHEMA, compression="snappy") as writer:
        for batch in read_batches(csv_path, "csv"):
            writer.write_batch(batch)
            count += batch.num_rows
    return count


def content_fingerprint(path, format_name):
    # Order-independent probabilistic fingerprint preserves duplicate multiplicity.
    count, total, squares = 0, 0, 0
    modulo = 1 << 256
    for batch in read_batches(path, format_name):
        for row in batch.to_pylist():
            raw = json.dumps([row[c] for c in COLUMNS], ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
            value = int.from_bytes(hashlib.sha256(raw).digest(), "big")
            total = (total + value) % modulo
            squares = (squares + value * value) % modulo
            count += 1
    return {"n_events": count, "sum_sha256_mod_2_256": str(total),
            "sum_squared_sha256_mod_2_256": str(squares)}


def benchmark(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    left = content_fingerprint(args.csv, "csv")
    right = content_fingerprint(args.parquet, "parquet")
    if left != right or not left["n_events"]:
        raise ValueError("CSV/Parquet content fingerprints differ or input is empty")
    path = args.csv if args.format == "csv" else args.parquet
    tick = time.perf_counter()
    process = psutil.Process()
    peak_read_rss = process.memory_info().rss
    count = 0
    for batch in read_batches(path, args.format):
        count += batch.num_rows
        peak_read_rss = max(peak_read_rss, process.memory_info().rss)
    seconds = time.perf_counter() - tick
    if count != left["n_events"]:
        raise ValueError("Input changed after verification")
    template = json.loads(args.preprocess_argv) if args.preprocess_argv else None
    if not template and not args.read_only:
        raise ValueError("Official E4 requires the same TV1 preprocessing argv for both formats")
    preprocessing = None
    if template:
        if not isinstance(template, list) or not all(isinstance(v, str) for v in template):
            raise ValueError("preprocess-argv must encode an argv list")
        if not any("{input_path}" in v for v in template):
            raise ValueError("Preprocessing template must bind {input_path}")
        if not any("{input_format}" in v for v in template):
            raise ValueError("Preprocessing template must bind {input_format}")
        if not any("{output_dir}" in v for v in template):
            raise ValueError("Preprocessing template must bind a fresh {output_dir}")
        values = {"input_path": str(path), "input_format": args.format,
                  "output_dir": str(output / "preprocessed")}
        command = []
        for value in template:
            for name, replacement in values.items():
                value = value.replace("{" + name + "}", replacement)
            command.append(value)
        preprocessing = run_command(command, output / "preprocessing", {"scope": "TV1 preprocessing command; includes its input read"})
        if preprocessing["status"] == "passed" and (
                not (output / "preprocessed").is_dir() or not any((output / "preprocessed").iterdir())):
            preprocessing["status"] = "failed"
            preprocessing["error"] = "TV1 command did not produce artifacts in {output_dir}"
    result = {"run_id": args.run_id, "experiment": "E4", "format": args.format,
              "input": str(path), "bytes": path.stat().st_size, "read_seconds": seconds,
              "peak_read_process_rss_bytes": peak_read_rss,
              "read_rss_scope": "sampled at batch boundaries, includes existing reader/cache allocations",
              "n_events": count, "verification": left,
              "verification_method": "nine string fields, multiplicity-sensitive multiset fingerprint (probabilistic)",
              "cache_policy": "OS cache warm after pair verification; no privileged cache drop",
              "schema_policy": "all nine fields strings; isolates format, excludes dtype conversion",
              "read_scope": "streaming full decode, all rows consumed; excludes pair verification",
              "preprocessing": preprocessing,
              "status": "read_only_diagnostic" if args.read_only else (
                  "passed" if preprocessing["status"] == "passed" else "failed")}
    save_json(output / "metrics.json", result)
    if result["status"] == "failed":
        raise ValueError("TV1 preprocessing failed; preserve raw logs")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--parquet", required=True, type=Path)
    p.add_argument("--prepare-pair", action="store_true")
    p.add_argument("--format", choices=["csv", "parquet"])
    p.add_argument("--preprocess-argv")
    p.add_argument("--read-only", action="store_true")
    p.add_argument("--output", type=Path)
    p.add_argument("--run-id")
    args = p.parse_args()
    if args.prepare_pair:
        print(json.dumps({"conversion_rows": prepare_pair(args.csv, args.parquet),
                          "note": "one-time conversion outside E4 read/preprocessing timing"}))
    else:
        if not args.format or not args.output or not args.run_id:
            p.error("benchmark requires --format, --output and --run-id")
        print(json.dumps(benchmark(args), indent=2))


if __name__ == "__main__":
    main()
