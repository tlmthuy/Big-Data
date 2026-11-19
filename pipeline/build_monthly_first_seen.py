"""Build one product first-seen lookup shared by the four weekly subsets."""
import argparse
import json
import time
from pathlib import Path

import duckdb

from export_raw_subsets import sql_path
from sample_sessions import checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cleanup-report', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    source_report = json.loads(args.cleanup_report.read_text())
    source = Path(source_report['output_path'])
    if source_report['status'] != 'passed' or checksum(source) != source_report['output_sha256']:
        raise ValueError('Cleanup input does not match a successful cleanup report')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    artifact = args.output_dir / 'product_first_seen.parquet'
    start = time.perf_counter()
    with duckdb.connect() as db:
        db.execute('CREATE TEMP VIEW events AS SELECT * FROM read_parquet(' + sql_path(source) + ')')
        db.execute('''CREATE TEMP TABLE first_seen AS
            SELECT product_id, min(event_time_ts) AS prod_first_event_time_ts
            FROM events GROUP BY product_id''')
        db.execute(f'COPY first_seen TO {sql_path(artifact)} (FORMAT PARQUET, COMPRESSION ZSTD)')
        shared_seconds = time.perf_counter() - start
        event_count = db.execute('SELECT count(*) FROM events').fetchone()[0]
        count, distinct_count, invalid, first, last = db.execute('''
            SELECT count(*), count(DISTINCT product_id),
                   count(*) FILTER (WHERE product_id IS NULL OR prod_first_event_time_ts IS NULL),
                   min(prod_first_event_time_ts), max(prod_first_event_time_ts)
            FROM read_parquet(?)
        ''', [str(artifact)]).fetchone()
        if event_count != source_report['rows_after_cleanup'] or count != distinct_count or invalid:
            raise ValueError('First-seen artifact failed row-count or key validation')
        if first != source_report['min_event_time_ts'] or not first <= last <= source_report['max_event_time_ts']:
            raise ValueError('First-seen timestamps do not match the monthly bounds')
    report = dict(
        input_path=str(source.resolve()), input_sha256=source_report['output_sha256'],
        cleanup_report=str(args.cleanup_report), upstream_engine=source_report['engine'],
        output_path=str(artifact.resolve()), output_sha256=checksum(artifact),
        input_events=event_count, product_count=count, invalid_lookup_rows=invalid,
        min_first_seen_ts=first, max_first_seen_ts=last, timestamp_unit='unix_seconds_utc',
        shared_for_subset_percentages=[10, 25, 50, 100], shared_build_seconds=shared_seconds,
        timing_scope='Monthly Parquet scan, group-by minimum and Parquet write; excludes upstream cleanup, verification and checksums',
        engine='DuckDB CPU', engine_version=duckdb.__version__,
    )
    summary = json.dumps(report, indent=2) + '\n'
    (args.output_dir / 'report.json').write_text(summary)
    print(summary)


if __name__ == '__main__':
    main()
