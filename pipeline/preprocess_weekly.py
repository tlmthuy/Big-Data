"""Run the same weekly preprocessing for equivalent raw CSV and Parquet."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from fit_weekly_workflow import digest

COLUMNS = ['event_time', 'event_type', 'product_id', 'category_id',
           'category_code', 'brand', 'price', 'user_id', 'user_session']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--input-format', required=True, choices=['csv', 'parquet'])
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--first-seen', type=Path, required=True)
    p.add_argument('--subset', type=int, required=True, choices=[10, 25, 50, 100])
    args = p.parse_args()

    import cudf
    import cupy
    import pyarrow as pa
    import pyarrow.csv as arrow_csv
    import pyarrow.parquet as pq

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    timings = {}
    tick = time.perf_counter()
    schema = pa.schema([(name, pa.string()) for name in COLUMNS])
    if args.input_format == 'csv':
        raw = arrow_csv.read_csv(args.input, convert_options=arrow_csv.ConvertOptions(
            column_types=schema, strings_can_be_null=False))
    else:
        raw = pq.read_table(args.input)
    timings['read_seconds'] = time.perf_counter() - tick
    if not raw.schema.equals(schema, check_metadata=False):
        raise ValueError('Expected nine ordered raw string columns')
    tick = time.perf_counter()
    frame = cudf.DataFrame.from_arrow(raw)
    del raw
    n_events = len(frame)
    frame = frame.replace('', None)
    timestamps = cudf.to_datetime(frame.pop('event_time').str.replace(' UTC', '', regex=False),
                                  format='%Y-%m-%d %H:%M:%S', errors='raise')
    frame['event_time_ts'] = timestamps.astype('datetime64[s]').astype('int64')
    if (frame.event_time_ts.isna().any() or not frame.event_time_ts.between(1569888000, 1570492799).all()
            or not frame.event_type.isin(['view', 'cart', 'purchase']).all()):
        raise ValueError('Input must contain eligible events from the first UTC week')
    for col in ('product_id', 'user_id', 'category_id'):
        frame[col] = frame[col].astype('int64')
    frame['price'] = frame['price'].astype('float64')
    frame = frame.dropna(subset=['user_session'])
    eligible_events = len(frame)
    frame = frame.sort_values(['user_session', 'event_time_ts'])
    repeated = ((frame.user_session == frame.user_session.shift(1))
                & (frame.product_id == frame.product_id.shift(1))).fillna(False)
    frame = frame[~repeated]
    mapping = frame[['user_session']].drop_duplicates().sort_values('user_session').reset_index(drop=True)
    mapping['session_id'] = mapping.index.astype('int64') + 1
    mapping.to_parquet(output / 'session_mapping.parquet', index=False)
    frame = frame.merge(mapping, on='user_session').drop(columns=['user_session']).rename(columns={'session_id': 'user_session'})
    lookup = cudf.read_parquet(args.first_seen)
    lookup['product_id'] = lookup.product_id.astype('int64')
    if not lookup.product_id.is_unique:
        raise ValueError('Shared first-seen product IDs must be unique')
    frame = frame.merge(lookup, on='product_id', how='left')
    if frame.prod_first_event_time_ts.isna().any() or (frame.prod_first_event_time_ts > frame.event_time_ts).any():
        raise ValueError('Invalid first-seen join')
    weekly_events = len(frame)
    products = int(frame.product_id.nunique())
    stage = output / 'week.parquet'
    frame.to_parquet(stage, index=False)
    (output / 'manifest.json').write_text(json.dumps({'outputs': [dict(
        percent=args.subset, path=stage.name, sha256=digest(stage),
        events=weekly_events, products=products)]})+'\n')
    del frame, mapping, lookup
    cupy.cuda.runtime.deviceSynchronize()
    timings['prepare_seconds'] = time.perf_counter() - tick

    for label, script, flags in (
        ('workflow_seconds', 'fit_weekly_workflow.py',
         ['--inputs', str(output), '--subset', str(args.subset)]),
        ('split_seconds', 'split_weekly_sequences.py', ['--workflow', str(output / 'workflow')]),
    ):
        tick = time.perf_counter()
        folder = 'workflow' if label == 'workflow_seconds' else 'splits'
        subprocess.run([sys.executable, str(Path(__file__).with_name(script)), *flags,
                        '--output-dir', str(output / folder)], check=True)
        timings[label] = time.perf_counter() - tick

    (output / 'timings.json').write_text(json.dumps(dict(
        status='measured', n_events=n_events, eligible_events=eligible_events,
        events_after_repeat_removal=weekly_events, input_format=args.input_format,
        input_sha256=digest(args.input), first_seen_artifact=str(args.first_seen.resolve()),
        first_seen_sha256=digest(args.first_seen),
        preprocessing_seconds=sum(v for k,v in timings.items() if k != 'read_seconds'),
        **timings), indent=2)+'\n')


if __name__ == '__main__':
    main()
