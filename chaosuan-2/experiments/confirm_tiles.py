#!/usr/bin/env python3
import pathlib
import sys
sys.argv = [sys.argv[0], sys.argv[1], '--phase', 'setup']
source = pathlib.Path(__file__).with_name('run_experiments.py').read_text()
namespace = {'__file__': str(pathlib.Path(__file__).with_name('run_experiments.py'))}
exec(source.split("if args.phase == 'setup':")[0], namespace)
bench = namespace['bench']
for round_no in range(3):
    for tile in ([128,64] if round_no == 1 else [64,128]):
        bench(f'confirm_gemm_large_tile{tile}', 'gemm', [1024,'blocked',tile],round_no,3)
