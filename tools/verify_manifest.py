#!/usr/bin/env python3
"""Verify the transferred patch/core digests recorded in integration/manifest.json."""
# SPDX-License-Identifier: MIT
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'integration/manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['integrity']:
        path = (ROOT / entry['path']).resolve()
        if ROOT not in path.parents:
            raise ValueError('Manifest path outside repository')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry['sha256']:
            raise ValueError(f'Integrity mismatch: {entry["path"]}')
    print(f'PASS: {len(manifest["integrity"])} source/patch digests')


if __name__ == '__main__':
    main()
