"""Verify pre-split Notebook 02 sequences against the original weekly events."""
import argparse
import json
from pathlib import Path

from fit_weekly_workflow import digest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(run, workspace):
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq

    subset = run['subset']
    evidence = run['sequence_verification']
    root = workspace / 'data/clean/workflows' / str(subset)
    source = workspace / 'data/clean/workflow_inputs' / Path(run['input_path']).name
    sequence = root / evidence['path']
    mapping_path = root / 'product_mapping.parquet'
    for path, expected in (
        (source, run['input_sha256']),
        (sequence, evidence['sha256']),
        (mapping_path, run['checksums']['product_mapping.parquet']),
    ):
        require(digest(path) == expected, f'{subset}%: checksum mismatch for {path}')

    events = pd.read_parquet(source, columns=['user_session', 'event_time_ts', 'product_id'])
    require(len(events) == run['input_events'], f'{subset}%: unexpected input event count')
    counts = events.groupby('user_session').size()
    eligible = counts[counts >= 2].to_dict()
    tied = set(events.loc[events.duplicated(['user_session', 'event_time_ts'], keep=False), 'user_session'])
    suffix = (events[~events.user_session.isin(tied)]
              .sort_values(['user_session', 'event_time_ts']).groupby('user_session').tail(20))
    mapping = pd.read_parquet(mapping_path)
    require(mapping.product_id.is_unique and mapping.encoded_id.is_unique,
            f'{subset}%: product mapping is not one-to-one')
    suffix = suffix.assign(encoded_id=suffix.product_id.map(mapping.set_index('product_id').encoded_id))
    require(suffix.encoded_id.notna().all(), f'{subset}%: missing product mapping')
    expected = suffix.groupby('user_session').encoded_id.agg(list)
    known = set(mapping.encoded_id)
    padding = run['technical_ids']['padding']

    file = pq.ParquetFile(sequence)
    list_cols = [name for name in file.schema_arrow.names if name.endswith('-list')]
    require('product_id-list' in list_cols, f'{subset}%: missing product list')
    observed = set()
    exact = 0
    for batch in file.iter_batches(columns=['user_session', 'product_id-count', *list_cols]):
        for row in batch.to_pylist():
            session = row['user_session']
            label = f'{subset}% session {session}'
            count = row['product_id-count']
            require(session not in observed and session in eligible and eligible[session] == count,
                    f'{label}: duplicate, ineligible or incorrect interaction count')
            observed.add(session)
            length = min(count, 20)
            require(all(row[c] is not None and len(row[c]) == 20 for c in list_cols),
                    f'{label}: feature lists have inconsistent lengths')
            ids = row['product_id-list']
            require(all(x in known for x in ids[:length]) and all(x == padding for x in ids[length:]),
                    f'{label}: invalid item or right padding')
            if session not in tied:
                require(np.array_equal(ids[:length], expected.loc[session]),
                        f'{label}: product order or final-20 slice mismatch')
                exact += 1
    require(observed == set(eligible) and len(observed) == run['sequence_count'],
            f'{subset}%: session membership mismatch')
    ties = len(observed) - exact
    require(exact == evidence['exact_suffix_sessions_without_timestamp_ties']
            and ties == evidence['sessions_with_timestamp_ties'],
            f'{subset}%: exact-order or tie counts differ from manifest')
    print(f"PASS subset={subset} sequences={len(observed)} exact_suffix_without_ties={exact} "
          f"with_ties={ties} list_columns={len(list_cols)} sha256={evidence['sha256']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    runs = json.loads(args.manifest.read_text())['runs']
    require([r['subset'] for r in runs] == [10, 25, 50, 100], 'Expected four ordered subsets')
    for run in runs:
        verify(run, args.workspace)


if __name__ == '__main__':
    main()
