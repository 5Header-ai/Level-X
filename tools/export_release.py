#!/usr/bin/env python3
"""Export clean tracked sources and a verified full-history bundle; no binaries."""
# SPDX-License-Identifier: MIT
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *map(str, args)], cwd=cwd, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Export outside the source repository')
    if git('status', '--porcelain').strip():
        raise ValueError('Commit or review all source changes before export')
    if git('branch', '--show-current').decode().strip() != 'feature/levelx-gpu':
        raise ValueError('Export the feature/levelx-gpu branch')
    head = git('rev-parse', 'HEAD').decode().strip()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='levelx-export-') as tmp:
        temporary = Path(tmp)
        archive = temporary / 'levelx-iphone-gpu-engine-source.zip'
        bundle = temporary / 'levelx-iphone-gpu-engine.bundle'
        git('archive', '--format=zip', '--prefix=levelx-iphone-gpu-engine/', '-o', archive, 'HEAD')
        git('bundle', 'create', bundle, '--all')
        git('bundle', 'verify', bundle)
        refs = git('bundle', 'list-heads', bundle).decode().splitlines()
        restored = temporary / 'restored'
        git('-c', 'core.autocrlf=false', 'clone', bundle, restored)
        restored_head = git('rev-parse', 'refs/heads/feature/levelx-gpu', cwd=restored).decode().strip()
        if restored_head != head:
            raise RuntimeError('Restored bundle does not match exported feature HEAD')
        git('fsck', '--full', cwd=restored)
        files = {}
        for artifact in (archive, bundle):
            contents = artifact.read_bytes()
            files[artifact.name] = {'sha256': hashlib.sha256(contents).hexdigest(), 'bytes': len(contents)}
            # Publish only after verification. These names belong to this exporter.
            (output / artifact.name).write_bytes(contents)
    metadata = {
        'schema_version': 1, 'release': '0.1.0-preliminary', 'head': head,
        'branch': 'feature/levelx-gpu', 'bundle_restore': 'PASS',
        'bundle_verification': 'PASS', 'bundle_refs': refs,
        'upstream_base': 'cc4302a99167abec69b714cfd00c38caece7e7de',
        'files': files, 'scope': 'independent source repository and its history; no full A13 GPU/Metal claim',
    }
    (output / 'levelx-release.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8', newline='\n')
    (output / 'SHA256SUMS.txt').write_text(''.join(f"{v['sha256']}  {k}\n" for k, v in files.items()), encoding='utf-8', newline='\n')
    print(f'Exported {head}; bundle verified and restored; source archive contains tracked files only')


if __name__ == '__main__':
    main()
