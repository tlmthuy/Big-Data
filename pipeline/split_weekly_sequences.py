"""Apply the pinned NVIDIA GPU split to fitted Notebook 02 sequences."""
import argparse
import importlib.util
import json
import time
from pathlib import Path

from fit_weekly_workflow import digest

SOURCE = 'transformers4rec/utils/data_utils.py'
SPLITS = ('train', 'valid', 'test')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)

    import cupy
    import cudf
    import numpy as np
    import nvtabular as nvt
    import pandas as pd
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    vendor = Path(__file__).resolve().parents[1] / 'docs/vendor/nvidia-transformers4rec'
    pin = json.loads((vendor / 'manifest.json').read_text())
    source = vendor / 'upstream' / SOURCE
    if digest(source) != pin['files'][SOURCE]:
        raise ValueError('Pinned split source checksum mismatch')
    spec = importlib.util.spec_from_file_location('nvidia_split_source', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fit = json.loads((args.workflow / 'manifest.json').read_text())
    catalog_path = args.workflow / 'catalog.json'
    schema_path = args.workflow / 'processed_nvt/schema.pbtxt'
    if (digest(catalog_path) != fit['checksums']['catalog.json']
            or digest(schema_path) != fit['checksums']['processed_nvt/schema.pbtxt']):
        raise ValueError('Workflow catalog or schema checksum mismatch')
    catalog = json.loads(catalog_path.read_text())
    padding = catalog['technical_ids']['padding']
    known = {item['encoded_id'] for item in catalog['items']}
    seq_dir = args.workflow / 'processed_nvt'
    paths = sorted(seq_dir.glob('*.parquet'))
    expected = pq.read_table(paths, columns=['user_session', 'day_index']).to_pandas()
    if expected.empty or expected.isna().any().any() or not expected.user_session.is_unique:
        raise ValueError('Sequence input requires unique sessions and valid day_index')

    start = time.perf_counter()
    module.save_time_based_splits(
        data=nvt.Dataset([str(p) for p in paths]), output_dir=str(args.output_dir),
        partition_col='day_index', timestamp_col='user_session',
        val_size=0.1, test_size=0.1, cpu=False, overwrite=False,
    )
    split_seconds = time.perf_counter() - start

    counts, memberships, seen = [], [], set()
    days = sorted(map(int, expected.day_index.unique()))
    expected_by_day = {int(day): set(group.user_session) for day, group in expected.groupby('day_index')}
    for day in days:
        for split in SPLITS:
            path = args.output_dir / str(day) / f'{split}.parquet'
            table = pq.read_table(path, columns=['user_session', 'product_id-list'])
            sessions = table['user_session'].to_pylist()
            current = set(sessions)
            if (len(current) != len(sessions) or seen & current
                    or not current <= expected_by_day[day]):
                raise ValueError(f'Invalid membership in {day}/{split}')
            seen.update(current)
            flat = pc.list_flatten(table['product_id-list'])
            values = flat.combine_chunks().to_numpy(zero_copy_only=False)
            items = values[values != padding]
            if flat.null_count or not set(np.unique(items)) <= known:
                raise ValueError(f'Invalid product IDs in {day}/{split}')
            counts.append(dict(day_index=day, split=split, sessions=len(sessions),
                               distinct_items=int(len(np.unique(items))), item_interactions=int(len(items)),
                               path=str(path.relative_to(args.output_dir)), sha256=digest(path)))
            memberships.append(pd.DataFrame(dict(user_session=sessions, day_index=day, split=split)))
    if seen != set(expected.user_session):
        raise ValueError('Split membership does not cover all input sessions')
    membership_path = args.output_dir / 'membership.parquet'
    pq.write_table(pa.Table.from_pandas(pd.concat(memberships, ignore_index=True),
                                      preserve_index=False), membership_path)
    report = dict(subset=fit['subset'], input_hashes={p.name: digest(p) for p in paths},
                  notebook_commit=pin['commit'], seed=1, engine='NVIDIA GPU',
                  cudf=cudf.__version__, cupy=cupy.__version__, nvtabular=nvt.__version__,
                  requested_ratios=dict(train=0.8, valid=0.1, test=0.1),
                  partition_col='day_index', sort_col='user_session',
                  input_sessions=len(expected), membership=membership_path.name,
                  membership_sha256=digest(membership_path), catalog_sha256=digest(catalog_path),
                  schema_sha256=digest(schema_path), split_seconds=split_seconds,
                  no_overlap_and_complete_coverage=True,
                  daily_pairs=[dict(train=t, validation=t+1) for t in days if t+1 in days],
                  counts=counts)
    (args.output_dir / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"PASS {fit['subset']}%: {len(expected)} sessions, {len(days)} partitions", flush=True)


if __name__ == '__main__':
    main()
