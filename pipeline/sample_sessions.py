"""Select nested raw-session lists by a version-independent SHA-256 rule."""
import argparse
import csv
import hashlib
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from raw_audit import COLUMNS

PERCENTAGES = (10, 25, 50, 100)


def score(session, seed):
    payload = f'{seed}:{session}'.encode('utf-8')
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big')


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir', type=Path, default=Path('data/subset/session_ids'))
    parser.add_argument('--manifest', type=Path, default=Path('data/manifests/session_sampling_manifest.json'))
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    source = args.input.resolve()
    before = source.stat()
    with source.open(encoding='utf-8-sig', newline='') as f:
        if next(csv.reader(f)) != COLUMNS:
            raise ValueError('Unexpected CSV schema')
    paths = {p: args.output_dir / f'sessions_{p:03d}.csv' for p in PERCENTAGES}
    if args.manifest.exists() or any(p.exists() for p in paths.values()):
        raise FileExistsError('Output already exists; use a new output directory and manifest')
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute('SET threads=2')
    temp = Path('tmp/session_sampling_spill').resolve()
    temp.mkdir(parents=True, exist_ok=True)
    con.execute('SET temp_directory=?', [str(temp)])
    escaped = str(source).replace("'", "''")
    con.execute(f"""CREATE TEMP TABLE candidates AS
        SELECT DISTINCT user_session FROM read_csv('{escaped}',
        header=true, all_varchar=true, delim=',', quote='"', escape='"',
        nullstr='', strict_mode=true)
        WHERE user_session IS NOT NULL AND event_type IN ('view','cart','purchase')
        AND try_strptime(event_time, '%Y-%m-%d %H:%M:%S UTC') >= TIMESTAMP '2019-10-01'
        AND try_strptime(event_time, '%Y-%m-%d %H:%M:%S UTC') < TIMESTAMP '2019-10-08'
    """)
    population = con.execute('SELECT count(*) FROM candidates').fetchone()[0]
    if not population:
        raise ValueError('No eligible sessions')
    print(f'Eligible raw-week sessions: {population}', flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts = {p: 0 for p in PERCENTAGES}
    thresholds = {p: (p * 2**64) // 100 for p in PERCENTAGES}
    handles = {}
    try:
        for p, path in paths.items():
            handles[p] = path.open('w', encoding='utf-8', newline='')
        writers = {p: csv.writer(f, lineterminator='\n') for p, f in handles.items()}
        for w in writers.values():
            w.writerow(['user_session'])
        cursor = con.execute('SELECT user_session FROM candidates ORDER BY user_session')
        while batch := cursor.fetchmany(10000):
            for (session,) in batch:
                value = score(session, args.seed)
                for p in PERCENTAGES:
                    if value < thresholds[p]:
                        writers[p].writerow([session])
                        counts[p] += 1
    finally:
        for f in handles.values():
            f.close()
    assert counts[100] == population
    # Verify every output independently against rule, uniqueness and nesting.
    previous = set()
    outputs = []
    for p, path in paths.items():
        current = set()
        with path.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                session = row['user_session']
                assert session and session not in current
                assert score(session, args.seed) < thresholds[p]
                current.add(session)
        assert len(current) == counts[p] and previous.issubset(current)
        previous = current
        outputs.append(dict(percent=p, session_count=counts[p],
                            actual_session_ratio=counts[p]/population,
                            threshold_integer=thresholds[p], path=str(path.resolve()),
                            bytes=path.stat().st_size, sha256=checksum(path)))
        print(f'{p}%: {counts[p]} sessions', flush=True)
    input_hash = checksum(source)
    after = source.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    manifest = dict(started_at_utc=started, completed_at_utc=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=time.perf_counter()-start, seed=args.seed,
                    seed_purpose='session sampling; independent of NVIDIA GPU split seed 1',
                    input_path=str(source), input_bytes=before.st_size, input_sha256=input_hash,
                    population_sessions=population,
                    scope='UTC [2019-10-01, 2019-10-08); non-null original user_session; view/cart/purchase',
                    hash_rule='UTF-8(str(seed) + colon + original user_session); SHA-256; first 8 digest bytes as unsigned big-endian integer h; select h < floor(percent * 2^64 / 100)',
                    percentages_are='Expected fractions of sessions, not exact quotas or event ratios',
                    preprocessing='Raw membership only; no deduplication, minimum-length filtering, truncation, mapping or split performed. Same membership may be reused after NVIDIA preprocessing; do not rehash encoded IDs.',
                    event_retention='Next step: join selected original session IDs and retain all their eligible events within the week; no row sampling. No event subset exported in this run.',
                    outputs=outputs, checks='PASS: unique non-null IDs, hash rule, nested 10 <= 25 <= 50 <= 100, 100% equals population, input unchanged',
                    duckdb_version=duckdb.__version__, python_version=platform.python_version(),
                    git_base_commit=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                    script_sha256=checksum(Path(__file__)))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(f'PASS: {args.manifest}', flush=True)


if __name__ == '__main__':
    main()
