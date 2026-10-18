#!/usr/bin/env python3
"""Build, run preserved/new tests, and check API + CLI under ASan/UBSan on Linux."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, default=ROOT/'build')
    parser.add_argument('--output',type=pathlib.Path,default=ROOT/'validation.json')
    args = parser.parse_args()
    if not sys.platform.startswith('linux'): parser.error('Linux / WSL 2 required')
    if args.output.exists(): parser.error('Use a new --output to preserve existing evidence')
    build = args.build.resolve()
    results = []
    def run(command):
        command = list(map(str,command))
        process = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=180)
        results.append({'command':command,'returncode':process.returncode,
                        'stdout':process.stdout,'stderr':process.stderr})
        print(process.stdout,end='')
        print(process.stderr,end='',file=sys.stderr)
        if process.returncode:
            raise RuntimeError(f'Failed: {command[0]}')
    try:
        run(['cmake','-S','.', '-B',build,'-DCMAKE_BUILD_TYPE=Release'])
        run(['cmake','--build',build,'-j2'])
        for name in ['baseline_original','baseline_refactored']:
            run([sys.executable,'test_public.py',build/name])
        run(['ctest','--test-dir',build,'--output-on-failure'])
        flags = ['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer']
        run([*flags,'test_api.cpp','filter.cpp','-o',build/'test_api_sanitized'])
        run([build/'test_api_sanitized'])
        run([*flags,'main.cpp','filter.cpp','-o',build/'log_filter_sanitized'])
        run([sys.executable,'test_public.py',build/'log_filter_sanitized'])
        run([sys.executable,'test_regression.py',build/'log_filter_sanitized'])
    finally:
        sources = {file.name:hashlib.sha256(file.read_bytes()).hexdigest()
                   for file in sorted(ROOT.iterdir())
                   if file.suffix in ['.cpp','.hpp','.py'] or file.name in ['CMakeLists.txt','requirements.txt']}
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump({'results':results,'sources_sha256':sources},stream,ensure_ascii=False,indent=2)
            stream.write('\n')

if __name__ == '__main__':
    main()
