"""Read-only, exact raw CSV audit. Run with Python and duckdb installed."""
import argparse
import csv
import hashlib
import json
import resource
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

COLUMNS = ['event_time', 'event_type', 'product_id', 'category_id',
           'category_code', 'brand', 'price', 'user_id', 'user_session']


def peak_rss_bytes(system):
    """Normalize the native ru_maxrss unit on supported systems."""
    unit_bytes = {"Darwin": 1, "Linux": 1024}
    if system not in unit_bytes:
        raise NotImplementedError(f"Unknown ru_maxrss unit on {system}")
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit_bytes[system]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', type=Path, default=Path('data/raw_audit.csv'))
    p.add_argument('--memory-limit', default='1GB')
    args = p.parse_args()
    start = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    src = args.input.resolve()
    before = src.stat()
    with src.open(newline='', encoding='utf-8-sig') as f:
        if next(csv.reader(f)) != COLUMNS:
            raise ValueError('Unexpected CSV header')
    con = duckdb.connect()
    con.execute('SET memory_limit = ?', [args.memory_limit])
    con.execute('SET threads = 2')
    tmp = Path('tmp/raw_audit_spill').resolve()
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute('SET temp_directory = ?', [str(tmp)])
    # Strict CSV reader: no skipped malformed records; identifiers remain strings.
    escaped = str(src).replace("'", "''")
    con.execute(f"""CREATE VIEW raw AS SELECT *,
        try_strptime(event_time, '%Y-%m-%d %H:%M:%S UTC') AS ts
        FROM read_csv('{escaped}', header=true, all_varchar=true,
        delim=',', quote='"', escape='"', nullstr='', strict_mode=true)""")
    rows = []
    counts = {}
    def emit(scope, metric, column='', value='', count=None, denominator=None, ratio=None):
        rows.append(dict(scope=scope, metric=metric, column=column, value=value,
                         count=count, denominator=denominator, ratio=ratio))
    for scope, where in [('raw_month', 'true'), ('raw_week', "ts >= TIMESTAMP '2019-10-01' AND ts < TIMESTAMP '2019-10-08'")]:
        print(f'Auditing {scope}', flush=True)
        n, bad, lo, hi = con.execute(f'SELECT count(*), count(*) FILTER (WHERE ts IS NULL), min(ts), max(ts) FROM raw WHERE {where}').fetchone()
        counts[scope] = n
        emit(scope, 'row_count', count=n)
        emit(scope, 'invalid_timestamp_count', 'event_time', count=bad, denominator=n)
        emit(scope, 'min_timestamp_utc', 'event_time', str(lo))
        emit(scope, 'max_timestamp_utc', 'event_time', str(hi))
        for col in COLUMNS:
            unique, missing = con.execute(f'SELECT count(DISTINCT "{col}"), count(*) FILTER (WHERE "{col}" IS NULL) FROM raw WHERE {where}').fetchone()
            emit(scope, 'distinct_count', col, count=unique)
            emit(scope, 'missing_count', col, count=missing, denominator=n, ratio=missing/n if n else None)
            assert 0 <= missing <= n and unique <= n - missing
            print(f'  {col}: distinct={unique}, missing={missing}', flush=True)
        events = con.execute(f'SELECT event_type, count(*) FROM raw WHERE {where} GROUP BY event_type ORDER BY event_type').fetchall()
        assert sum(v for _, v in events) == n
        for event, amount in events:
            emit(scope, 'event_type_count', 'event_type', event if event is not None else '<MISSING>', amount, n, amount/n if n else None)
        days = con.execute(f'SELECT CAST(ts AS DATE), count(*) FROM raw WHERE {where} GROUP BY 1 ORDER BY 1').fetchall()
        assert sum(v for _, v in days) == n
        for day, amount in days:
            emit(scope, 'daily_event_count', 'event_time', str(day) if day else '<INVALID>', amount)
    assert counts['raw_week'] <= counts['raw_month']
    print('Computing input SHA-256', flush=True)
    sha = hashlib.sha256()
    with src.open('rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''):
            sha.update(chunk)
    after = src.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Input changed during audit'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['scope','metric','column','value','count','denominator','ratio'])
        w.writeheader()
        w.writerows(rows)
    system = platform.system()
    manifest = dict(input_path=str(src), input_bytes=before.st_size,
                    input_sha256=sha.hexdigest(), output_path=str(args.output.resolve()),
                    started_at_utc=started, completed_at_utc=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=time.perf_counter()-start,
                    peak_process_rss_bytes=peak_rss_bytes(system),
                    peak_rss_platform=platform.platform(), peak_rss_system=system,
                    duckdb_version=duckdb.__version__,
                    memory_limit=args.memory_limit, threads=2,
                    git_commit=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    missing_rule='CSV empty fields only; distinct excludes NULL; no trimming or imputation',
                    raw_month='All rows, before cleaning/deduplication/sampling',
                    raw_week='UTC [2019-10-01, 2019-10-08), before cleaning/deduplication/sampling',
                    checks='PASS: event/day totals, distinct/missing bounds, week <= month, input unchanged')
    out = Path('data/manifests/raw_audit_manifest.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(f'PASS: {args.output}; {counts}', flush=True)


if __name__ == '__main__':
    main()
