"""Additional independent black-box tests; usage: python3 test_regression.py EXE."""
import hashlib
import json
import pathlib
import random
import struct
import subprocess
import sys
import tempfile
import unittest

EXE = str(pathlib.Path(sys.argv.pop(1)).resolve())
ROOT = pathlib.Path(__file__).resolve().parent
HEADER, RECORD = struct.Struct('<8sIIQ'), struct.Struct('<QIIII')

class Regression(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='chaosuan3-regression-')
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)

    def run_ok(self, *args):
        result = subprocess.run([EXE, *map(str,args)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_full_records_at_mask_boundaries(self):
        rng = random.Random(9321)
        for n in [63,64,65,127,128,129,4097,16385]:
            for mode in ['all','none','alternating','duplicates','random']:
                rows = []
                for i in range(n):
                    hit = mode in ['all','duplicates'] or (mode == 'alternating' and i % 2 == 0) or (mode == 'random' and rng.randrange(2))
                    rows.append((1500 if hit else 2000, rng.getrandbits(32), 100, rng.getrandbits(32), 3))
                if mode == 'duplicates': rows = [(1500,17,100,0xffffffff,3)] * n
                src, dst = self.root/'input.bin', self.root/'output.bin'
                data = HEADER.pack(b'NCULOG01',1,24,n) + b''.join(RECORD.pack(*r) for r in rows)
                src.write_bytes(data)
                dst.unlink(missing_ok=True)
                self.run_ok('--input',src,'--output',dst,'--repeats',1)
                expected = [r for r in rows if 1000 <= r[0] < 2000 and r[2] >= 100 and r[4] & 3 == 3]
                expected_bytes = HEADER.pack(b'NCULOG01',1,24,len(expected)) + b''.join(RECORD.pack(*r) for r in expected)
                self.assertEqual(dst.read_bytes(), expected_bytes, (n,mode))
                self.assertEqual(src.read_bytes(), data)

    def test_python_generator_v1_parity(self):
        for pattern, rate, seed in [('random',50,2026),('random',1,0xffffffff),('blocks',90,17)]:
            stem = f'{pattern}-{rate}'
            source, exported = self.root/(stem+'.bin'), self.root/(stem+'-cpp.bin')
            command = [sys.executable, str(ROOT/'generate_logs.py'),'--count','10001',
                       '--hit-percent',str(rate),'--pattern',pattern,'--seed',str(seed),'--output',str(source)]
            generated = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(generated.returncode,0,generated.stderr)
            manifest = json.loads(generated.stdout)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),manifest['sha256'])
            self.run_ok('--count',10001,'--hit-percent',rate,'--pattern',pattern,'--seed',seed,
                        '--export-input',exported,'--repeats',1)
            self.assertEqual(source.read_bytes(),exported.read_bytes())
            self.run_ok('--input',source,'--repeats',1)

    def test_linked_output_not_overwritten(self):
        source = self.root/'input.bin'
        data = HEADER.pack(b'NCULOG01',1,24,1) + RECORD.pack(1000,1,100,1,3)
        source.write_bytes(data)
        hard, symbolic = self.root/'hard.bin', self.root/'symbolic.bin'
        hard.hardlink_to(source)
        symbolic.symlink_to(source)
        for output in [hard,symbolic]:
            result = subprocess.run([EXE,'--input',str(source),'--output',str(output),'--repeats','1'],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,2)
            self.assertEqual(source.read_bytes(),data)

if __name__ == '__main__':
    unittest.main()
