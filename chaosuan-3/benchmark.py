#!/usr/bin/env python3
"""Generate v1 inputs in a temporary directory; keep only auditable JSON evidence."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent
CASES = [(100_000,50,'random'), (2_000_000,50,'random'),
         (2_000_000,50,'blocks'), (2_000_000,1,'random'),
         (2_000_000,100,'blocks')]
IMPLEMENTATIONS = ['baseline_original','baseline_refactored','log_filter']

def run(command):
    result = subprocess.run(list(map(str,command)), capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed: {result.stdout}\n{result.stderr}')
    return result.stdout

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def field(line, name):
    return next(part.split('=',1)[1] for part in line.split() if part.startswith(name+'='))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, default=ROOT/'build')
    parser.add_argument('--samples', type=int, default=7)
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'measurements.json')
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('Run on Linux or WSL 2')
    if args.samples < 5:
        parser.error('At least five samples are required')
    if args.output.exists():
        parser.error('Evidence exists; choose a new --output to preserve original measurements')
    build = args.build.resolve()
    for name in IMPLEMENTATIONS:
        if not (build/name).is_file(): parser.error(f'Missing executable: {name}')
    evidence = {
        'schema':'chaosuan3.measurements.v1',
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'environment':{'uname':platform.uname()._asdict(),'cpu':run(['lscpu']),
                       'memory':run(['free','-b']),'compiler':run(['g++','--version']),
                       'cmake':run(['cmake','--version']), 'python':sys.version,
                       'cpu_affinity':sorted(os.sched_getaffinity(0)), 'threads':1,
                       'compile_commands':json.loads((build/'compile_commands.json').read_text())},
        'timing':'steady_clock around filter only; input generation/loading, buffer allocation, full-field validation and file IO excluded equally; one warmup before each retained sample',
        'sources_sha256':{name:digest(ROOT/name) for name in ['baseline.cpp','main.cpp','serial_filter.cpp','filter.cpp','support.hpp','test_public.py','generate_logs.py','benchmark.py','CMakeLists.txt']},
        'sample_order':'Cyclically rotated executable order each round; order reversed on odd rounds',
        'cases':[]
    }
    with tempfile.TemporaryDirectory(prefix='chaosuan3-benchmark-') as tmp:
        temporary = pathlib.Path(tmp)
        for count, hit, pattern in CASES:
            source = temporary/'input.bin'
            generator_args = ['--count',str(count),'--hit-percent',str(hit),
                              '--pattern',pattern,'--seed','2026','--output',str(source)]
            manifest = json.loads(run([sys.executable, ROOT/'generate_logs.py', *generator_args]))
            assert digest(source) == manifest['sha256']
            case = {'count':count,'requested_hit_percent':hit,'pattern':pattern,'seed':2026,
                    'query':{'begin':1000,'end':2000,'min_latency':100,'flags':3},
                    'manifest':manifest,'runs':[],'summary':{}}
            first_output = None
            for round_index in range(args.samples):
                offset = round_index % len(IMPLEMENTATIONS)
                order = IMPLEMENTATIONS[offset:] + IMPLEMENTATIONS[:offset]
                if round_index % 2: order = order[::-1]
                for name in order:
                    options = ['--input',str(source),'--repeats','1',
                               '--begin','1000','--end','2000','--min-latency','100','--flags','3']
                    destination = temporary/(name+'.bin')
                    if round_index == 0: options += ['--output',str(destination)]
                    start = time.monotonic()
                    stdout = run([build/name,*options])
                    wall = time.monotonic()-start
                    sample = next(line for line in stdout.splitlines() if line.startswith('sample='))
                    assert field(sample,'check') == 'PASS'
                    matched = int(field(sample,'matched'))
                    assert matched == manifest['hitCountActual']
                    item = {'round':round_index,'implementation':name,'core_ms':float(field(sample,'core_ms')),
                            'matched':matched,'process_wall_s':wall,'stdout':stdout}
                    if round_index == 0:
                        # Compare every serialized byte, not just a checksum.
                        data = destination.read_bytes()
                        if first_output is None: first_output = data
                        else: assert data == first_output, 'Full output differs between implementations'
                        item['output_sha256'] = hashlib.sha256(data).hexdigest()
                        destination.unlink()
                    case['runs'].append(item)
            assert digest(source) == manifest['sha256'], 'Input changed'
            for name in IMPLEMENTATIONS:
                values = [r['core_ms'] for r in case['runs'] if r['implementation'] == name]
                case['summary'][name] = {'samples_ms':values,'median_ms':statistics.median(values),
                                         'min_ms':min(values),'max_ms':max(values)}
            base = case['summary']['baseline_original']['median_ms']
            opt = case['summary']['log_filter']['median_ms']
            case['speedup_original_over_optimized'] = base/opt
            evidence['cases'].append(case)
            print(f'N={count} {pattern} hit={hit}% baseline={base:.6f}ms optimized={opt:.6f}ms speedup={base/opt:.3f}x',flush=True)
            first_output = None
            source.unlink()
            pathlib.Path(str(source)+'.json').unlink()
    evidence['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with args.output.open('x',encoding='utf-8') as output:
        json.dump(evidence,output,ensure_ascii=False,indent=2)
        output.write('\n')

if __name__ == '__main__':
    main()
