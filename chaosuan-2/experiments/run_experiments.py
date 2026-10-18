#!/usr/bin/env python3
"""Reproducible single-core paired benchmark; no root privileges required."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('machine')
parser.add_argument('--phase', choices=['setup', 'pilot', 'full'], default='full')
args = parser.parse_args()
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'experiments' / 'results' / args.machine
BUILD = ROOT / 'experiments' / 'build'
OUT.mkdir(parents=True, exist_ok=True)
BUILD.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', LC_ALL='C')
CPU = min(os.sched_getaffinity(0))
FLAGS = ['-std=c++17', '-O3', '-march=x86-64-v3', '-mtune=generic',
         '-ffp-contract=off', '-g']

def execute(command, log=None, timeout=1800):
    proc = subprocess.run(command, cwd=ROOT, env=ENV, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if log:
        (OUT / log).write_text('$ ' + ' '.join(map(str, command)) + '\n' + proc.stdout)
    return proc

def setup():
    commands = {
        'date': ['date', '--iso-8601=seconds'], 'uname': ['uname', '-a'],
        'lscpu': ['lscpu'], 'lscpu_json': ['lscpu', '-J'],
        'memory': ['free', '-b'], 'compiler': ['g++', '--version'],
        'load': ['uptime'], 'perf_permission': ['cat', '/proc/sys/kernel/perf_event_paranoid'],
        'virtualization': ['systemd-detect-virt'],
    }
    info = {'cpu_affinity': CPU, 'flags': FLAGS, 'machine': args.machine,
            'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                              for name in ['common.hpp', 'gemm.cpp', 'stencil.cpp']}}
    for name, command in commands.items():
        p = execute(command, 'env_' + name + '.txt')
        info[name] = {'returncode': p.returncode, 'output': p.stdout}
    info['cache'] = []
    for index in sorted(pathlib.Path('/sys/devices/system/cpu/cpu0/cache').glob('index*')):
        info['cache'].append({name: (index/name).read_text().strip()
                              for name in ['level', 'type', 'size', 'coherency_line_size',
                                           'ways_of_associativity', 'number_of_sets', 'shared_cpu_list']})
    info['cpufreq'] = {}
    for name in ['scaling_governor', 'scaling_min_freq', 'scaling_max_freq', 'scaling_cur_freq']:
        path = pathlib.Path('/sys/devices/system/cpu') / f'cpu{CPU}' / 'cpufreq' / name
        if path.exists(): info['cpufreq'][name] = path.read_text().strip()
    (OUT/'environment.json').write_text(json.dumps(info, indent=2))
    for kernel in ['stencil', 'gemm']:
        command = ['g++', *FLAGS, '-fopt-info-vec-all=' + str(OUT/(kernel+'_vectorization.txt')),
                   kernel+'.cpp', '-o', str(BUILD/kernel)]
        p = execute(command, kernel+'_build.txt')
        if p.returncode: raise RuntimeError(p.stdout)
        p = execute(['objdump', '-d', '-C', str(BUILD/kernel)], kernel+'_disassembly.txt')
    print(f'{args.machine}: environment captured and both kernels compiled; CPU={CPU}', flush=True)

def bench(case, kernel, params, round_no, repeats):
    command = ['taskset', '-c', str(CPU), str(BUILD/kernel), *map(str, params), str(repeats)]
    label = f'{case}_round{round_no}'
    p = execute(command, label+'.txt')
    if p.returncode or 'check=FAIL' in p.stdout:
        raise RuntimeError(f'{label}: benchmark or correctness failed\n{p.stdout}')
    samples = [float(line.split('compute_ms=')[1]) for line in p.stdout.splitlines()
               if line.startswith('sample=')]
    checks = [line for line in p.stdout.splitlines() if line.startswith('check=')]
    if len(samples) != repeats or len(checks) != repeats+1 or not all('check=PASS' in x for x in checks):
        raise RuntimeError(f'{label}: incomplete output')
    errors = [float(line.split('max_abs_error=')[1].split()[0]) for line in checks]
    item = {'case': case, 'kernel': kernel, 'params': params, 'round': round_no,
            'command': command, 'samples_ms': samples, 'checks': len(checks),
            'max_abs_error': max(errors), 'correctness': 'PASS',
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'log': label+'.txt'}
    with (OUT/'runs.jsonl').open('a') as f: f.write(json.dumps(item)+'\n')
    print(f'{args.machine}: {label} PASS median={statistics.median(samples):.6g} ms', flush=True)

if args.phase == 'setup':
    setup()
elif args.phase == 'pilot':
    bench('pilot_stencil_row', 'stencil', [512, 512, 20, 'row'], 0, 3)
    bench('pilot_stencil_column', 'stencil', [512, 512, 20, 'column'], 0, 3)
    bench('pilot_gemm_naive', 'gemm', [128, 'naive', 64], 0, 3)
    bench('pilot_gemm_blocked', 'gemm', [128, 'blocked', 64], 0, 3)
else:
    # Three rounds, each containing three measured samples. Reverse AB in round 1
    # to reduce a systematic run-order bias; one warmup precedes every invocation.
    for size, dim in [('small', 512), ('large', 4096)]:
        for round_no in range(3):
            order = ['column', 'row'] if round_no == 1 else ['row', 'column']
            for impl in order:
                bench(f'stencil_{size}_{impl}', 'stencil', [dim, dim, 20, impl], round_no, 3)
    for size, n in [('small', 128), ('large', 1024)]:
        for round_no in range(3):
            order = ['blocked', 'naive'] if round_no == 1 else ['naive', 'blocked']
            for impl in order:
                bench(f'gemm_{size}_{impl}', 'gemm', [n, impl, 64], round_no, 3)
    for size, n in [('small', 128), ('large', 1024)]:
        for tile in [16, 32, 128, 256]:
            # tile=64 uses the paired baseline above (nine samples).
            bench(f'gemm_{size}_tile{tile}', 'gemm', [n, 'blocked', tile], 0, 5)
    # Edge tiles, tile>N, rectangular stencils, odd/even ping-pong semantics.
    for n, tile in [(1, 1), (31, 16), (65, 32), (31, 64)]:
        for impl in ['naive', 'blocked']:
            bench(f'edge_gemm_n{n}_t{tile}_{impl}', 'gemm', [n, impl, tile], 0, 1)
    for h, w, steps in [(3, 3, 1), (7, 11, 3), (7, 11, 4)]:
        for impl in ['row', 'column']:
            bench(f'edge_stencil_{h}x{w}_s{steps}_{impl}', 'stencil', [h, w, steps, impl], 0, 1)
    execute(['uptime'], 'env_load_after.txt')
    execute(['free', '-b'], 'env_memory_after.txt')
    print(f'{args.machine}: all paired, tile-scan and edge cases complete', flush=True)
