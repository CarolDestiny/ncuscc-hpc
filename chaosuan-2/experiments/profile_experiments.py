#!/usr/bin/env python3
"""Separate profiling and scalar controls from performance scores."""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.argv = [sys.argv[0], sys.argv[1], '--phase', 'setup']
# Import helpers without executing run_experiments.py's phase dispatch.
source = pathlib.Path(__file__).with_name('run_experiments.py').read_text()
namespace = {'__file__': str(pathlib.Path(__file__).with_name('run_experiments.py'))}
exec(source.split("if args.phase == 'setup':")[0], namespace)
if namespace['args'].machine != 'physical':
    raise SystemExit('Cache/compiler profiling is restricted to the physical machine; WSL is timing-only.')
ROOT, OUT, BUILD, ENV, CPU, FLAGS = [namespace[x] for x in ['ROOT','OUT','BUILD','ENV','CPU','FLAGS']]
execute, bench = namespace['execute'], namespace['bench']
TOOLS = ROOT/'experiments/tools/local'
VAL = TOOLS/'usr/bin/valgrind'
ENV['VALGRIND_LIB'] = str(TOOLS/'usr/libexec/valgrind')
ENV['LD_LIBRARY_PATH'] = str(TOOLS/'usr/lib/x86_64-linux-gnu')
perf = shutil.which('perf') or str(TOOLS/'usr/bin/perf')
for name, command in {
    'perf_version': [perf, '--version'],
    'perf_stat': [perf, 'stat', '-e', 'cycles,instructions,cache-references,cache-misses',
                  '--', 'taskset','-c',str(CPU),str(BUILD/'stencil'),'512','512','2','row','1'],
    'perf_software': [perf,'stat','-e','task-clock','--','true'],
    'valgrind_version': [str(VAL),'--version'],
}.items():
    p = execute(command, name+'.txt')
    print(f'{namespace["args"].machine}: {name} returncode={p.returncode}', flush=True)

for kernel in ['stencil', 'gemm']:
    scalar = BUILD/(kernel+'_scalar')
    p = execute(['g++', *FLAGS, '-fno-tree-vectorize', '-fno-tree-slp-vectorize',
                 kernel+'.cpp', '-o', str(scalar)], kernel+'_scalar_build.txt')
    if p.returncode: raise RuntimeError(p.stdout)
    for impl in (['row', 'column'] if kernel == 'stencil' else ['naive', 'blocked']):
        params = [512, 512, 20, impl] if kernel=='stencil' else [128, impl, 64]
        case = 'scalar_'+kernel+'_'+impl
        existing = [json.loads(x)['case'] for x in (OUT/'runs.jsonl').read_text().splitlines()]
        if case not in existing:
            bench(case, kernel+'_scalar', params, 0, 5)

p = execute(['g++', *FLAGS, '-I'+str(TOOLS/'usr/include'),
             'experiments/cache_driver.cpp', '-o', str(BUILD/'cache_driver')], 'cache_driver_build.txt')
if p.returncode: raise RuntimeError(p.stdout)
info = json.loads((OUT/'environment.json').read_text())
def cache_spec(kind, level):
    item = next(x for x in info['cache'] if x['type']==kind and x['level']==str(level))
    size = item['size']
    size_bytes = int(size[:-1])*1024 if size.endswith('K') else int(size)
    return ','.join([str(size_bytes), item['ways_of_associativity'], item['coherency_line_size']])
ll_spec = cache_spec('Unified',3)
cache_flags = ['--I1='+cache_spec('Instruction',1), '--D1='+cache_spec('Data',1),
               '--LL='+ll_spec]
profiles = []
for kernel, sizes, implementations, param in [
    ('stencil',[512,2048],['row','column'],2),
    ('gemm',[128,512],['naive','blocked'],64),
]:
    for n in sizes:
        for impl in implementations:
            label = f'cache_{kernel}_{n}_{impl}'
            command = ['taskset','-c',str(CPU),str(VAL),'--tool=cachegrind',
                       '--cache-sim=yes','--branch-sim=no','--instr-at-start=no', *cache_flags,
                       '--cachegrind-out-file='+str(OUT/(label+'.cg')),
                       str(BUILD/'cache_driver'),kernel,str(n),impl,str(param)]
            p = execute(command, label+'.txt')
            if p.returncode: raise RuntimeError(p.stdout)
            lines = (OUT/(label+'.cg')).read_text().splitlines()
            events = next(x for x in lines if x.startswith('events:')).split()[1:]
            summary = next(x for x in lines if x.startswith('summary:')).split()[1:]
            counts = dict(zip(events, map(int, summary)))
            profiles.append({'kernel':kernel,'n':n,'impl':impl,'param':param,
                             'cache_flags':cache_flags,'counts':counts,'log':label+'.txt'})
            print(f'{info["machine"]}: {label} simulated D1_misses={counts["D1mr"]+counts["D1mw"]}', flush=True)
            (OUT/'cache_summary.json').write_text(json.dumps(profiles,indent=2))
print(f'{info["machine"]}: profiling and scalar controls complete', flush=True)
