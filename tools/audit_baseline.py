#!/usr/bin/env python3
"""Reproduce the baseline source map from Git objects, not a moving worktree."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = 'cc4302a99167abec69b714cfd00c38caece7e7de'
FILES = ['VERSION','LICENSE','hw/arm/apple-silicon/t8030.c',
    'hw/display/apple_displaypipe_v4.c','include/hw/display/apple_displaypipe_v4.h',
    'hw/arm/apple-silicon/dart.c','include/hw/arm/apple-silicon/dart.h',
    'hw/display/apple_scaler.c','hw/display/apple_displaypipe_v2.c',
    'hw/display/meson.build','hw/arm/apple-silicon/meson.build',
    'hw/arm/Kconfig','include/system/dma.h','ui/icons/CKBrandingNotice.md']

def audit(root):
    result = {'upstream': 'https://github.com/ChefKissInc/Inferno', 'sha': BASE,
              'scope': 'source implementation, not physical A13 hardware specification', 'files': {}}
    for path in FILES:
        data = subprocess.check_output(['git','-C',str(root),'show',BASE+':'+path])
        entry = {'sha256': hashlib.sha256(data).hexdigest()}
        if path.endswith('.c'):
            registers = []
            for i, line in enumerate(data.decode().splitlines(), 1):
                match = re.search(r'REG(32|64)\((\w+),\s*(0x[0-9a-fA-F]+)\)', line)
                if match:
                    registers.append({'name': match[2], 'offset': match[3],
                                      'width': int(match[1]), 'line': i})
            entry['registers'] = registers
        result['files'][path] = entry
    files = subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',BASE],text=True).splitlines()
    result['qtest_files'] = [p for p in files if 'qtest' in p.lower()]
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inferno', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.inferno)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f"Pinned baseline: {result['sha']}; {len(result['files'])} file hashes; qtest files: {len(result['qtest_files'])}")

if __name__ == '__main__': main()
