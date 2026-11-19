"""CPU validation of Notebook 01 timestamp and consecutive-item cleanup."""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from event_timestamp import create_parsed_events
from export_raw_subsets import sql_path
from raw_audit import peak_rss_bytes
from sample_sessions import checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    report_path = output / 'report.json'
    parquet = output / 'events_clean.parquet'
    with duckdb.connect() as db:
        db.execute("SET memory_limit='2GB'")
        db.execute('SET threads=2')
        db.execute('SET temp_directory=?', [str((output / 'spill').resolve())])
        create_parsed_events(db, args.input)
        rows, invalid, missing, first, last = db.execute("""
            SELECT count(*), count(*) FILTER (WHERE event_time_ts IS NULL),
                   count(*) FILTER (WHERE user_session IS NULL),
                   min(event_time_ts), max(event_time_ts)
            FROM parsed
        """).fetchone()
        report = dict(input_path=str(args.input.resolve()), output_path=str(parquet.resolve()),
                      started_at_utc=started_at, timezone='UTC', timestamp_unit='unix_seconds',
                      rows_before_timestamp=rows, rows_after_timestamp=rows,
                      timestamp_parse_failures=invalid, min_event_time_ts=first,
                      max_event_time_ts=last, null_session_rows=missing,
                      engine='DuckDB CPU', engine_version=duckdb.__version__,
                      platform=platform.platform(),
                      repeat_rule='Within original user_session, order only by event_time_ts and drop a row when the preceding product_id matches. Timestamp ties follow this runtime.')
        print(json.dumps(report), flush=True)
        if invalid:
            report['status'] = 'failed_timestamp_parse'
            report_path.write_text(json.dumps(report, indent=2) + '\n')
            raise ValueError(f'{invalid} timestamps failed parsing. See {report_path}')
        db.execute(f"""COPY (
            SELECT * EXCLUDE (previous_product) FROM (
                SELECT *, lag(product_id) OVER (
                    PARTITION BY user_session ORDER BY event_time_ts
                ) AS previous_product
                FROM parsed WHERE user_session IS NOT NULL
            ) WHERE NOT coalesce(product_id = previous_product, false)
        ) TO {sql_path(parquet)} (FORMAT PARQUET, COMPRESSION ZSTD)""")
        clean, bad_output = db.execute(f"""
            SELECT count(*), count(*) FILTER (WHERE user_session IS NULL OR event_time_ts IS NULL)
            FROM read_parquet({sql_path(parquet)})
        """).fetchone()
        if bad_output or clean > rows - missing:
            raise ValueError('Parquet validation failed')
        report.update(rows_before_session_cleanup=rows, rows_after_null_session_filter=rows - missing,
                      consecutive_repeat_rows_removed=rows - missing - clean, rows_after_cleanup=clean,
                      input_sha256=checksum(args.input), output_sha256=checksum(parquet),
                      peak_process_rss_bytes=peak_rss_bytes(platform.system()),
                      elapsed_seconds=time.perf_counter() - start, status='passed')
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
