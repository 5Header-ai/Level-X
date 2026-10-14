#!/usr/bin/env python3
"""Verify exported patch series in a new temporary clone of the exact baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = 'cc4302a99167abec69b714cfd00c38caece7e7de'
ALLOWED = {'hw/display/apple_displaypipe_v4.c','hw/display/meson.build',
           'hw/display/trace-events','hw/display/levelx_scanout.c','hw/display/levelx_scanout.h'}

def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args], stderr=subprocess.STDOUT)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inferno', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    patches = sorted((ROOT/'patches/inferno').glob('*.patch'))
    if len(patches) != 2:
        raise RuntimeError('Expected the documented two-patch series')
    log = []
    with tempfile.TemporaryDirectory(prefix='levelx-patch-') as tmp:
        checkout = Path(tmp)/'inferno'
        subprocess.run(['git','-c','core.autocrlf=false','clone','--no-checkout','--shared',
                        str(args.inferno.resolve()),str(checkout)], check=True, capture_output=True)
        git(checkout,'config','core.autocrlf','false')
        git(checkout,'checkout','--detach',BASE)
        for patch in patches:
            git(checkout,'apply','--check','--index',str(patch))
            git(checkout,'-c','user.name=Level X Transfer Check',
                '-c','user.email=levelx-check@localhost','am',str(patch))
            log.append({'patch': patch.name, 'sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
                        'status': 'PASS'})
        changed = set(git(checkout,'diff','--name-only',BASE,'HEAD').decode().splitlines())
        if changed != ALLOWED: raise RuntimeError(f'Unexpected changed files: {changed}')
        c = (checkout/'hw/display/levelx_scanout.c').read_bytes()
        h = (checkout/'hw/display/levelx_scanout.h').read_bytes()
        if c != b'#include "qemu/osdep.h"\n' + (ROOT/'src/levelx_scanout.c').read_bytes():
            raise RuntimeError('Transferred C source differs from tested source')
        if h != (ROOT/'include/levelx_scanout.h').read_bytes():
            raise RuntimeError('Transferred header differs from tested header')
        git(checkout,'diff','--check',BASE,'HEAD')
        # Verify rollback, in the throwaway clone only, newest patch first.
        for patch in reversed(patches):
            git(checkout,'apply','--reverse','--check',str(patch))
            git(checkout,'apply','--reverse',str(patch))
        if git(checkout,'diff',BASE,'--','hw/display/apple_displaypipe_v4.c',
               'hw/display/meson.build','hw/display/trace-events'):
            raise RuntimeError('Rollback did not restore baseline files')
        if (checkout/'hw/display/levelx_scanout.c').exists():
            raise RuntimeError('Rollback left the added implementation')
    result = {'status':'PASS','baseline':BASE,'patches':log,
              'changed_files':sorted(changed),'source_identity':'PASS','rollback':'PASS',
              'qemu_build':'NOT RUN','qtest':'NOT RUN','ios':'NOT RUN'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: patch application, exact C source identity, scope, whitespace and rollback')

if __name__ == '__main__': main()
