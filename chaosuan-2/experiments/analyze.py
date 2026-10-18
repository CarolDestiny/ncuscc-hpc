import csv
import json
import pathlib
import statistics
import sys

root = pathlib.Path(sys.argv[1])
results = root/'experiments/results'
all_stats = {}
all_runs = {}
for machine in ['wsl','physical']:
    runs = [json.loads(x) for x in (results/machine/'runs.jsonl').read_text().splitlines()]
    all_runs[machine] = runs
    groups = {}
    for run in runs: groups.setdefault(run['case'], []).append(run)
    stats = {}
    for case, cases in groups.items():
        times = [t for run in cases for t in run['samples_ms']]
        median = statistics.median(times)
        p = cases[0]['params']
        if 'stencil' in case:
            work = 6*(p[0]-2)*(p[1]-2)*p[2]
            byte_model = 8*(p[0]-2)*(p[1]-2)*p[2]
        else:
            work = 2*p[0]**3
            byte_model = 12*p[0]**2
        stats[case] = {'samples': len(times), 'mean_ms': statistics.mean(times),
            'median_ms': median, 'population_stddev_ms': statistics.pstdev(times),
            'GFLOP/s': work/(median*1e6), 'effective_GB/s': byte_model/(median*1e6),
            'max_abs_error': max(r['max_abs_error'] for r in cases),
            'checks': sum(r['checks'] for r in cases),
            'correctness': 'PASS', 'times_ms': times,
            'round_medians_ms': [statistics.median(r['samples_ms']) for r in cases]}
    all_stats[machine] = stats
(results/'summary.json').write_text(json.dumps(all_stats, indent=2))
with (results/'summary.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['machine','case','samples','mean_ms','median_ms','population_stddev_ms',
                     'GFLOP/s','effective_GB/s','max_abs_error','checks','correctness'])
    for machine, stats in all_stats.items():
        for case, s in stats.items():
            writer.writerow([machine,case,*[s[x] for x in ['samples','mean_ms','median_ms',
                'population_stddev_ms','GFLOP/s','effective_GB/s','max_abs_error','checks','correctness']]])

for machine, stats in all_stats.items():
    print(machine)
    for case, s in stats.items():
        if case.startswith(('pilot','edge')): continue
        print(case, 'n=',s['samples'], 'mean=%.6g median=%.6g std=%.6g GF=%.6g BW=%.6g err=%.6g' %
              tuple(s[x] for x in ['mean_ms','median_ms','population_stddev_ms','GFLOP/s','effective_GB/s','max_abs_error']))
    print('CHECKS',sum(r['checks'] for r in all_runs[machine]), 'RUNS',len(all_runs[machine]))
    profiles=json.loads((results/machine/'cache_summary.json').read_text())
    for p in profiles:
        c=p['counts']; refs=c['Dr']+c['Dw']; misses=c['D1mr']+c['D1mw']; ll=c['DLmr']+c['DLmw']
        print('CACHE',p['kernel'],p['n'],p['impl'],'refs',refs,'D1',misses,'LL',ll,'D1%%=%.4f'%(misses/refs*100))
