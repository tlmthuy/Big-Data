"""Convert measured TV1 timings into the TV2 E2 telemetry contract."""
import argparse
import json
import math
from pathlib import Path

from fit_weekly_workflow import digest


def seconds(value, field):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f'Invalid measured timing: {field}')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('timings', 'first-seen-manifest', 'source-log', 'output'):
        parser.add_argument(f'--{flag}', type=Path, required=True)
    args = parser.parse_args()
    timing = json.loads(args.timings.read_text())
    first = json.loads(args.first_seen_manifest.read_text())
    if timing.get('status') != 'measured' or type(timing['n_events']) is not int or timing['n_events'] <= 0:
        raise ValueError('Expected measured timings with a positive integer event count')
    for field in ('read_seconds', 'preprocessing_seconds'):
        seconds(timing[field], field)
    lookup = Path(timing['first_seen_artifact']).resolve(strict=True)
    if digest(lookup) != timing['first_seen_sha256'] or timing['first_seen_sha256'] != first['output_sha256']:
        raise ValueError('First-seen artifact does not match the timing and monthly manifest')
    log = args.source_log.resolve(strict=True)
    if not log.is_file() or log.stat().st_size == 0:
        raise ValueError('Expected a nonempty preprocessing source log')
    metrics = dict(timing, first_seen_artifact=str(lookup), source_log=str(log),
                   first_seen_seconds=seconds(first['shared_build_seconds'], 'first_seen_seconds'))
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
