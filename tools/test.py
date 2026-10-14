#!/usr/bin/env python3
"""Build and execute the actual C module. No third-party Python dependencies."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def msvc_env(build):
    env = os.environ.copy()
    if shutil.which('cl', path=env.get('PATH')):
        return env
    vswhere = Path(env.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    install = subprocess.check_output([str(vswhere), '-latest', '-products', '*',
        '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
        '-property', 'installationPath'], text=True).strip()
    if not install:
        raise RuntimeError('MSVC C toolchain not found')
    bat = build / 'msvc-env.cmd'
    vcvars = Path(install) / 'VC/Auxiliary/Build/vcvars64.bat'
    bat.write_text('@echo off\nset VSCMD_VER=\ncall "' + str(vcvars) + '" >nul\nif errorlevel 1 exit /b 1\nset\n')
    result = subprocess.check_output(['cmd', '/d', '/c', str(bat)], text=True)
    imported = set()
    for line in result.splitlines():
        key, sep, value = line.partition('=')
        if (sep and key.upper() in ('PATH', 'INCLUDE', 'LIB', 'LIBPATH')
                and key.upper() not in imported):
            env[key.upper()] = value
            imported.add(key.upper())
    return env

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cc', default='cl' if os.name == 'nt' else 'cc')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    exe = build / ('test_scanout.exe' if os.name == 'nt' else 'test_scanout')
    env = msvc_env(build) if args.cc == 'cl' else os.environ.copy()
    sources = [str(ROOT / 'src/levelx_scanout.c'), str(ROOT / 'tests/unit/test_scanout.c')]
    if args.cc == 'cl':
        flags = ['/nologo','/std:c11','/W4','/WX','/Od','/Zi', '/I'+str(ROOT/'include')]
        flags += ['/fsanitize=address'] if args.sanitize else ['/RTC1']
        compiler = shutil.which('cl', path=env.get('PATH'))
        if not compiler:
            raise RuntimeError('MSVC environment did not provide cl.exe')
        command = [compiler] + flags + sources + ['/Fe:'+str(exe)]
    else:
        flags = ['-std=c11','-Wall','-Wextra','-Werror','-Wconversion','-g','-O1','-I',str(ROOT/'include')]
        if args.sanitize:
            flags += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        command = [args.cc] + flags + sources + ['-o',str(exe)]
    compilation = subprocess.run(command, env=env, cwd=build, text=True, capture_output=True)
    print(compilation.stdout + compilation.stderr)
    execution = None
    if compilation.returncode == 0:
        execution = subprocess.run([str(exe)], env=env, cwd=build, text=True,
                                   capture_output=True, timeout=60)
        print(execution.stdout + execution.stderr)
    ok = compilation.returncode == 0 and execution is not None and execution.returncode == 0
    result = {'status': 'PASS' if ok else 'FAIL',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'compiler': args.cc, 'sanitizers_requested': args.sanitize,
        'command': command, 'build_exit': compilation.returncode,
        'build_output': compilation.stdout + compilation.stderr,
        'run_exit': execution.returncode if execution else None,
        'run_output': execution.stdout + execution.stderr if execution else 'NOT RUN',
        'scope': 'standalone C scanout module; not Inferno, DART hardware, or Metal'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
