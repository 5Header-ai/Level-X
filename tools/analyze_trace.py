#!/usr/bin/env python3
"""Summarize Level X metadata with the matching QEMU simpletrace reader."""
# SPDX-License-Identifier: MIT
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import sys


def load_reader(inferno):
    scripts = inferno.resolve() / 'scripts'
    if not (scripts / 'simpletrace.py').is_file():
        raise ValueError('Inferno scripts/simpletrace.py is required')
    sys.path.insert(0, str(scripts))
    return importlib.import_module('simpletrace')


def analyzer_type(simpletrace):
    class Summary(simpletrace.Analyzer2):
        def __init__(self):
            self.counts = Counter()
            self.mmio = Counter()
            self.scanouts = Counter()
            self.dropped = 0
            self.unbucketed = 0

        def add_bucket(self, buckets, key):
            # Fixed upper bound on aggregation memory, independent of trace size.
            if key in buckets or len(buckets) < 4096:
                buckets[key] += 1
            else:
                self.unbucketed += 1

        def mmio_event(self, kind, addr, value, size):
            self.counts[kind] += 1
            # The model subtracts this shadow offset once; retain raw address too.
            normalized = addr - 0x200000 if addr >= 0x200000 else addr
            self.add_bucket(self.mmio, (kind, addr, normalized, size))

        def levelx_adp_mmio_read(self, addr, value, size, **kwargs):
            self.mmio_event('read', addr, value, size)

        def levelx_adp_mmio_write(self, addr, value, size, **kwargs):
            self.mmio_event('write', addr, value, size)

        def levelx_adp_scanout(self, pipe, iova, width, height, stride, status, **kwargs):
            self.counts['checked_scanout'] += 1
            self.counts['accepted' if status == 0 else 'rejected'] += 1
            self.add_bucket(self.scanouts, (pipe, width, height, stride, status))

        def catchall(self, *args, event, **kwargs):
            if event.name == 'Dropped_Event':
                self.dropped += args[0]
            else:
                self.counts['other'] += 1

        def result(self):
            relevant = sum(self.counts[k] for k in ('read', 'write', 'checked_scanout'))
            status = 'PARSED' if relevant else 'NO_LEVELX_EVENTS'
            if self.dropped:
                status = 'INCOMPLETE'
            return {
                'schema_version': 1, 'status': status,
                'scope': 'DisplayPipe metadata only; not GPU/Metal functionality or frame completion',
                'counts': dict(self.counts), 'dropped_events': self.dropped,
                'aggregation_overflow_events': self.unbucketed,
                'mmio': [dict(operation=k[0], raw_offset=hex(k[1]),
                              model_offset=hex(k[2]), size=k[3], count=v)
                         for k, v in sorted(self.mmio.items())],
                'checked_scanouts': [dict(pipe=k[0], width=k[1], height=k[2],
                                         stride=k[3], status_code=k[4], count=v)
                                    for k, v in sorted(self.scanouts.items())],
            }
    return Summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inferno', type=Path, required=True,
                        help='trusted source checkout used to build the traced QEMU')
    parser.add_argument('--events', type=Path, required=True, help='matching build trace-events-all')
    parser.add_argument('--trace', type=Path, required=True, help='binary simple backend trace')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        reader = load_reader(args.inferno)
        summary = analyzer_type(reader)()
        reader.process(str(args.events), str(args.trace), summary)
        result = summary.result()
    except Exception as error:
        # A parser failure never produces a success report or partial summary.
        print(f'Trace analysis failed: {error}', file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['status'])
    return 0 if result['status'] == 'PARSED' else 2


if __name__ == '__main__':
    sys.exit(main())
