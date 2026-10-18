#!/usr/bin/env python3
"""Physical-machine PMU sampling with explicitly enabled kernel regions."""
import json
import os
import pathlib
import subprocess

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'experiments/results/physical'
BUILD=ROOT/'experiments/build'
TOOLS=ROOT/'experiments/tools/local'
FLAGS=['-std=c++17','-O3','-march=x86-64-v3','-mtune=generic','-ffp-contract=off','-g']
subprocess.run(['g++',*FLAGS,'-I'+str(TOOLS/'usr/include'),
                'experiments/cache_driver.cpp','-o',str(BUILD/'perf_driver')],cwd=ROOT,check=True)
env=dict(os.environ,LC_ALL='C',OMP_NUM_THREADS='1')
catalog=subprocess.run(['perf','list','--details','mem_load_retired'],text=True,capture_output=True)
(OUT/'hardware_event_definitions.txt').write_text(catalog.stdout+catalog.stderr)
groups={
 'l1':['cycles:u','instructions:u','mem_load_retired.l1_hit:u','mem_load_retired.l1_miss:u','mem_load_retired.fb_hit:u'],
 'll':['cycles:u','instructions:u','mem_load_retired.l3_hit:u','mem_load_retired.l3_miss:u'],
}
records=[]
for kernel,sizes,implementations,param in [
 ('stencil',[512,4096],['row','column'],20),
 ('gemm',[128,1024],['naive','blocked'],64),
]:
    for n in sizes:
        for trial in range(3):
            order=list(reversed(implementations)) if trial==1 else implementations
            for impl in order:
                for group,events in groups.items():
                    cr,cw=os.pipe(); ar,aw=os.pipe()
                    child_env=dict(env,BENCH_PERF_CONTROL_FD=str(cw),BENCH_PERF_ACK_FD=str(ar))
                    label=f'hardware_{kernel}_{n}_{impl}_{group}_trial{trial}'
                    stat=OUT/(label+'.perf.csv')
                    command=['perf','stat','-D','-1','--control',f'fd:{cr},{aw}',
                             '-x',';','-o',str(stat),'-e','{'+','.join(events)+'}',
                             '--','taskset','-c','0',str(BUILD/'perf_driver'),
                             kernel,str(n),impl,str(param)]
                    try:
                        proc=subprocess.run(command,env=child_env,cwd=ROOT,text=True,
                            capture_output=True,pass_fds=(cr,cw,ar,aw),timeout=180)
                    finally:
                        for fd in (cr,cw,ar,aw): os.close(fd)
                    (OUT/(label+'.txt')).write_text('$ '+' '.join(command)+'\n'+proc.stdout+proc.stderr)
                    if proc.returncode: raise RuntimeError(proc.stderr+stat.read_text())
                    counts={}; running={}
                    for line in stat.read_text().splitlines():
                        if not line or line.startswith('#'): continue
                        fields=line.split(';')
                        if len(fields)<5: continue
                        name=fields[2].strip()
                        if name not in events: continue
                        try: value=float(fields[0].strip())
                        except ValueError: raise RuntimeError('Unavailable event: '+line)
                        counts[name]=value
                        running[name]=float(fields[4].strip().rstrip('%'))
                    if set(counts)!=set(events): raise RuntimeError('Missing counters: '+stat.read_text())
                    if min(running.values())<99.0: raise RuntimeError('Counter multiplexing: '+stat.read_text())
                    records.append(dict(kernel=kernel,n=n,impl=impl,param=param,trial=trial,
                                        group=group,counts=counts,running_percent=running,
                                        checksum=proc.stdout.strip(),log=label+'.perf.csv'))
                    (OUT/'hardware_perf.json').write_text(json.dumps(records,indent=2))
                print(f'physical PMU: {kernel} {n} {impl} trial{trial} recorded (user kernel ROI)',flush=True)
print('Physical hardware sampling complete',flush=True)
