#!/usr/bin/env python3
"""Check a built binary's registration/help surfaces, without an iOS fixture."""
# SPDX-License-Identifier: MIT
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('qemu', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    executable = args.qemu.resolve()
    cases = [
        ('version', ['--version'], ['QEMU']),
        ('machine_type', ['-machine', 'help'], ['t8030']),
        ('checked_scanout_property', ['-device', 'apple-display-pipe-v4,help'],
         ['levelx-checked-scanout', 'on/off (default: off)']),
        ('trace_events', ['-trace', 'help'],
         ['levelx_adp_mmio_read', 'levelx_adp_mmio_write', 'levelx_adp_scanout']),
    ]
    results = []
    for name, flags, expected in cases:
        result = subprocess.run([str(executable), *flags], capture_output=True, text=True, timeout=30)
        text = result.stdout + result.stderr
        ok = result.returncode == 0 and all(s in text for s in expected)
        results.append({'name': name, 'args': flags, 'status': 'PASS' if ok else 'FAIL',
                        'exit': result.returncode, 'matched_lines':
                        [line for line in text.splitlines() if any(s in line for s in expected)],
                        'output_sha256': hashlib.sha256(text.encode()).hexdigest()})
    ok = all(r['status'] == 'PASS' for r in results)
    report = {'status': 'PASS' if ok else 'FAIL', 'checks': results,
              'binary_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
              'scope': 'CLI registration only; device realization/MMIO/DART/IRQ/iOS/Metal NOT RUN'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
