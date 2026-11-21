"""Stage unsplit weekly event tables for the Notebook 02 workflow."""
import argparse
import json
from pathlib import Path

import duckdb

from export_raw_subsets import read_csv, sql_path
from sample_sessions import checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cleanup', type=Path, default=Path('data/manifests/timestamp_session_cleanup.json'))
    parser.add_argument('--first-seen', type=Path, default=Path('data/manifests/monthly_first_seen.json'))
    parser.add_argument('--sampling', type=Path, default=Path('data/manifests/session_sampling_manifest.json'))
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    clean, first, sampling = [json.loads(p.read_text()) for p in (args.cleanup, args.first_seen, args.sampling)]
    events, lookup = [Path(m['output_path']) for m in (clean, first)]
    if (checksum(events) != clean['output_sha256'] or checksum(lookup) != first['output_sha256']
            or clean['output_sha256'] != first['input_sha256']
            or clean['input_sha256'] != sampling['input_sha256']):
        raise ValueError('Input provenance/checksum mismatch')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    results = []
    with duckdb.connect() as db:
        db.execute(f"""CREATE TEMP TABLE week AS SELECT e.*, f.prod_first_event_time_ts
            FROM read_parquet({sql_path(events)}) e
            LEFT JOIN read_parquet({sql_path(lookup)}) f USING(product_id)
            WHERE event_time_ts >= 1569888000 AND event_time_ts < 1570492800
              AND event_type IN ('view', 'cart', 'purchase')""")
        if db.execute('SELECT count(*) FROM week WHERE prod_first_event_time_ts IS NULL OR prod_first_event_time_ts > event_time_ts').fetchone()[0]:
            raise ValueError('Invalid first-seen join')
        mapping = args.output_dir / 'session_mapping.parquet'
        db.execute(f"""CREATE TEMP TABLE session_mapping AS
            SELECT user_session, row_number() OVER (ORDER BY user_session) AS session_id
            FROM (SELECT DISTINCT user_session FROM week)""")
        db.execute(f'COPY session_mapping TO {sql_path(mapping)} (FORMAT PARQUET)')
        for entry in sampling['outputs']:
            percent = entry['percent']
            ids = Path(entry['path'])
            if checksum(ids) != entry['sha256']:
                raise ValueError(f'Membership checksum mismatch for {percent}%')
            dest = args.output_dir / f'week_{percent:03d}.parquet'
            db.execute(f"""COPY (SELECT w.* EXCLUDE (user_session, product_id, category_id, user_id, price),
                    m.session_id AS user_session, w.product_id::BIGINT AS product_id,
                    w.category_id::BIGINT AS category_id, w.user_id::BIGINT AS user_id,
                    w.price::DOUBLE AS price
                FROM week w JOIN session_mapping m USING(user_session)
                SEMI JOIN {read_csv(ids)} s ON w.user_session = s.user_session)
                TO {sql_path(dest)} (FORMAT PARQUET)""")
            counts = db.execute('SELECT count(*), count(DISTINCT user_session), count(DISTINCT product_id) FROM read_parquet(?)', [str(dest)]).fetchone()
            results.append(dict(percent=percent, path=dest.name, sha256=checksum(dest),
                                events=counts[0], sessions=counts[1], products=counts[2]))
            print(results[-1], flush=True)
    (args.output_dir / 'manifest.json').write_text(json.dumps(dict(
        cleanup_sha256=clean['output_sha256'], first_seen_sha256=first['output_sha256'],
        sampling_manifest_sha256=checksum(args.sampling), session_mapping_sha256=checksum(mapping),
        outputs=results), indent=2) + '\n')


if __name__ == '__main__':
    main()
