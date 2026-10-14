#!/usr/bin/env python3
"""Integration with real upstream simpletrace, using synthetic binary records."""
# SPDX-License-Identifier: MIT
import argparse
import io
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_trace import analyzer_type, load_reader

DEFINITIONS = '''levelx_adp_mmio_read(uint64_t addr, uint64_t value, unsigned size) ""
levelx_adp_mmio_write(uint64_t addr, uint64_t value, unsigned size) ""
levelx_adp_scanout(unsigned pipe, uint64_t iova, unsigned width, unsigned height, unsigned stride, int status) ""
unrelated(uint64_t value) ""
'''


def fixture(records):
    # Writer for our own synthetic fixtures; decoding remains upstream's job.
    out = bytearray(struct.pack('=QQQ', 0xffffffffffffffff, 0xf2b177cb0aa429b4, 4))
    for i, line in enumerate(DEFINITIONS.splitlines()):
        name = line.split('(')[0].encode()
        out.extend(struct.pack('=QQL', 0, i, len(name)) + name)
    for i, args in records:
        payload = struct.pack('=' + 'Q' * len(args), *args)
        out.extend(struct.pack('=QQQII', 1, i, 1000, 24 + len(payload), 10) + payload)
    return bytes(out)


class TraceTests(unittest.TestCase):
    def parse(self, data):
        definitions = io.StringIO(DEFINITIONS)
        definitions.name = '<synthetic-levelx-events>'
        analyzer = analyzer_type(READER)()
        READER.process(definitions, io.BytesIO(data), analyzer)
        return analyzer.result()

    def test_observed_metadata(self):
        result = self.parse(fixture([
            (0, (0x46020, 0x70045, 4)), (1, (0x24602c, 1 << 12, 4)),
            (2, (0, 0xff0, 8, 8, 32, 0)), (2, (1, 0x1000, 8, 8, 32, 5)),
            (3, (123,)),
        ]))
        self.assertEqual(result['status'], 'PARSED')
        self.assertEqual(result['counts'], {'read': 1, 'write': 1,
                         'checked_scanout': 2, 'accepted': 1, 'rejected': 1, 'other': 1})
        self.assertEqual(result['mmio'][1]['model_offset'], '0x4602c')
        self.assertEqual(result['mmio'][1]['raw_offset'], '0x24602c')

    def test_dropped_is_incomplete(self):
        result = self.parse(fixture([(0xfffffffffffffffe, (9,)), (0, (1, 2, 4))]))
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(result['dropped_events'], 9)

    def test_unrelated_is_not_evidence(self):
        self.assertEqual(self.parse(fixture([(3, (1,))]))['status'], 'NO_LEVELX_EVENTS')

    def test_invalid_header_and_partial_payload(self):
        with self.assertRaises(ValueError):
            self.parse(bytes(24))
        with self.assertRaises(struct.error):
            self.parse(fixture([(0, (1, 2, 4))])[:-1])

    def test_bucket_memory_bound_preserves_totals(self):
        records = [(0, (i * 4, 0, 4)) for i in range(4100)]
        result = self.parse(fixture(records))
        self.assertEqual(result['counts']['read'], 4100)
        self.assertEqual(len(result['mmio']), 4096)
        self.assertEqual(result['aggregation_overflow_events'], 4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('inferno', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    READER = load_reader(args.inferno)
    run = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TraceTests))
    report = {'status': 'PASS' if run.wasSuccessful() else 'FAIL', 'tests': run.testsRun,
              'failures': len(run.failures), 'errors': len(run.errors),
              'scope': 'synthetic binary traces parsed by real Inferno simpletrace; no guest execution'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    sys.exit(0 if run.wasSuccessful() else 1)
