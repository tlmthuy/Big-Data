"""Export raw weekly events by existing session membership; no sequence cleaning."""
import argparse
import csv
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from raw_audit import COLUMNS
from sample_sessions import checksum


def sql_path(path):
    return "'" + str(path.resolve()).replace("'", "''") + "'"


def read_csv(path):
    return f'''read_csv({sql_path(path)}, header=true, all_varchar=true,
        delim=',', quote='"', escape='"', nullstr='', strict_mode=true)'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sampling-manifest', type=Path, default=Path('data/manifests/session_sampling_manifest.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/subset/raw_week'))
    parser.add_argument('--manifest', type=Path, default=Path('data/manifests/raw_subset_manifest.json'))
    parser.add_argument('--counts', type=Path, default=Path('data/manifests/raw_subset_counts.csv'))
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    begin = time.perf_counter()
    sampling = json.loads(args.sampling_manifest.read_text())
    source = Path(sampling['input_path'])
    before = source.stat()
    outputs = {o['percent']: args.output_dir / f'raw_week_{o["percent"]:03d}.csv' for o in sampling['outputs']}
    destinations = [args.manifest, args.counts, *outputs.values()]
    if len({p.resolve() for p in destinations}) != len(destinations):
        raise ValueError('Manifest, counts and subset paths must be distinct')
    for path in destinations:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'Output already exists: {path}')
    print('Checking input/session-list checksums', flush=True)
    assert checksum(source) == sampling['input_sha256']
    for o in sampling['outputs']:
        assert checksum(Path(o['path'])) == o['sha256']
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute('SET threads=2')
    temp = Path('tmp/raw_subset_export').resolve()
    temp.mkdir(parents=True, exist_ok=True)
    con.execute('SET temp_directory=?', [str(temp)])
    print('Loading eligible raw weekly events without deduplication', flush=True)
    con.execute(f'''CREATE TEMP TABLE week AS SELECT * FROM {read_csv(source)}
        WHERE user_session IS NOT NULL AND event_type IN ('view','cart','purchase')
        AND try_strptime(event_time, '%Y-%m-%d %H:%M:%S UTC') >= TIMESTAMP '2019-10-01'
        AND try_strptime(event_time, '%Y-%m-%d %H:%M:%S UTC') < TIMESTAMP '2019-10-08' ''')
    columns = ', '.join(f'w."{c}"' for c in COLUMNS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for o in sampling['outputs']:
        p = o['percent']
        path = outputs[p]
        con.execute(f'CREATE OR REPLACE TEMP TABLE ids AS SELECT user_session FROM {read_csv(Path(o["path"]))}')
        n, distinct_ids = con.execute('SELECT count(*), count(DISTINCT user_session) FROM ids').fetchone()
        assert n == distinct_ids == o['session_count']
        con.execute(f'CREATE OR REPLACE TEMP VIEW selected AS SELECT {columns} FROM week w SEMI JOIN ids USING(user_session)')
        print(f'Exporting {p}% raw subset', flush=True)
        con.execute(f'COPY (SELECT * FROM selected) TO {sql_path(path)} (FORMAT CSV, HEADER true)')
        with path.open(encoding='utf-8', newline='') as f:
            assert next(csv.reader(f)) == COLUMNS
        con.execute(f'CREATE OR REPLACE TEMP VIEW exported AS SELECT * FROM {read_csv(path)}')
        expected = con.execute('SELECT count(*), count(DISTINCT user_session), count(DISTINCT user_id), count(DISTINCT product_id) FROM selected').fetchone()
        actual = con.execute('SELECT count(*), count(DISTINCT user_session), count(DISTINCT user_id), count(DISTINCT product_id) FROM exported').fetchone()
        assert actual == expected and actual[1] == o['session_count']
        # Exact per-session event multiplicities, including one-event sessions.
        mismatch = con.execute('''WITH a AS (SELECT user_session, count(*) n FROM selected GROUP BY 1),
            b AS (SELECT user_session, count(*) n FROM exported GROUP BY 1)
            SELECT count(*) FROM a FULL JOIN b USING(user_session) WHERE a.n IS DISTINCT FROM b.n''').fetchone()[0]
        assert mismatch == 0
        invalid = con.execute('''SELECT count(*) FROM exported e ANTI JOIN ids USING(user_session)''').fetchone()[0]
        assert invalid == 0
        summaries.append(dict(percent=p, event_count=actual[0], session_count=actual[1],
                              user_count=actual[2], item_count=actual[3],
                              session_list_path=o['path'], session_list_sha256=o['sha256'],
                              threshold_integer=o['threshold_integer'], output_path=str(path.resolve()),
                              output_bytes=path.stat().st_size, output_sha256=checksum(path),
                              checks='PASS: schema; exported/source counts; exact per-session event multiplicities; all selected sessions present; no unselected sessions'))
        print(f'PASS {p}%: events/session/user/item = {actual}', flush=True)
    after = source.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    total = next(o['event_count'] for o in summaries if o['percent'] == 100)
    for o in summaries:
        o['actual_event_ratio'] = o['event_count'] / total
    manifest = dict(counts_path=str(args.counts.resolve()), input_path=str(source.resolve()), input_bytes=before.st_size,
                    input_sha256=sampling['input_sha256'], sampling_seed=sampling['seed'],
                    hash_rule=sampling['hash_rule'], scope=sampling['scope'],
                    sampling_manifest_path=str(args.sampling_manifest.resolve()),
                    sampling_manifest_sha256=checksum(args.sampling_manifest),
                    time_start_inclusive_utc='2019-10-01T00:00:00Z', time_end_exclusive_utc='2019-10-08T00:00:00Z',
                    retention='All raw events of selected sessions within scope, including consecutive repeats and one-event sessions; preserve nine field values; not a cleaned sequence. CSV serialization may differ from input.',
                    exclusions='Only outside-week events, missing user_session and event types outside view/cart/purchase',
                    sort_policy='No event sorting/tie-break introduced; raw row order is not a sequence-order guarantee',
                    outputs=summaries, started_at_utc=started,
                    completed_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-begin,
                    duckdb_version=duckdb.__version__, python_version=platform.python_version(),
                    git_base_commit=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                    script_sha256=checksum(Path(__file__)), input_unchanged=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.counts.parent.mkdir(parents=True, exist_ok=True)
    with args.counts.open('x', encoding='utf-8', newline='') as f:
        fields = ['percent','event_count','session_count','user_count','item_count','actual_event_ratio']
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(summaries)
    with args.manifest.open('x', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')
    con.close()
    print(f'PASS: {args.manifest}', flush=True)


if __name__ == '__main__':
    main()
