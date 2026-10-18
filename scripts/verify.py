#!/usr/bin/env python3
"""Rebuild the three snapshots on Linux; preserve historical measurements."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    if sys.platform != "linux":
        raise SystemExit("Run inside Linux / WSL 2")
    records = []
    report = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "platform": platform.platform(), "commands": records,
              "scope": "Fresh correctness checks; no historical performance or PMU remeasurement",
              "stage1_missing_tests": ["tests/integration_test.py", "tests/lifecycle_test.py"],
              "passed": False}
    def run(args, cwd=ROOT, expected=0):
        args = list(map(str, args))
        print("RUN", " ".join(args), flush=True)
        p = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=240)
        records.append({"command": args, "cwd": str(cwd), "returncode": p.returncode,
                        "expected_returncode": expected, "stdout": p.stdout, "stderr": p.stderr})
        if p.returncode != expected:
            print(p.stdout); print(p.stderr, file=sys.stderr)
            raise RuntimeError("Unexpected return code: " + str(p.returncode))
        return p
    try:
        manifest = json.loads((ROOT / "docs/source-manifest.json").read_text())
        for name, expected_hash in manifest["files_sha256"].items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            if actual != expected_hash:
                raise RuntimeError("Snapshot hash mismatch: " + name)
        report["snapshot_files_checked"] = len(manifest["files_sha256"])
        run(["g++", "--version"])
        run(["cmake", "--version"])
        with tempfile.TemporaryDirectory(prefix="ncuscc-verify-") as tmp:
            tmp = pathlib.Path(tmp)
            b1, b2, b3 = tmp / "stage1", tmp / "stage2", tmp / "stage3"
            run(["cmake", "-S", ROOT / "chaosuan-1", "-B", b1,
                 "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=OFF"])
            run(["cmake", "--build", b1, "-j2"])
            run([b1 / "workload", "--help"])
            run([b1 / "collector", "--help"])
            output = tmp / "metrics.jsonl"
            workload = subprocess.Popen([str(b1 / "workload"), "--threads", "1",
                                         "--duration", "3s"], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
            try:
                run([b1 / "collector", "--pid", workload.pid, "--interval", "200ms",
                     "--duration", "1s", "--output", output])
                rows = [json.loads(line) for line in output.read_text().splitlines()]
                assert all(row["schema"] == "hpc-metrics.v1" for row in rows)
                samples = [r for r in rows if r.get("event") == "sample"]
                assert samples and all(r["target"]["pid"] == workload.pid for r in samples)
                stdout, stderr = workload.communicate(timeout=10)
                assert workload.returncode == 0, stderr
                report["stage1_smoke"] = {"samples": len(samples), "rows": rows,
                                          "workload_stdout": stdout, "workload_stderr": stderr}
            finally:
                if workload.poll() is None:
                    workload.terminate()
                    workload.communicate(timeout=10)
            b2.mkdir()
            for name in ["stencil", "gemm"]:
                run(["g++", "-std=c++17", "-O3", "-Wall", "-Wextra", "-Wpedantic",
                     ROOT / "chaosuan-2" / (name + ".cpp"), "-o", b2 / name])
            for h, w, steps in [(3, 3, 1), (7, 11, 4), (64, 64, 4)]:
                for impl in ["row", "column"]:
                    run([b2 / "stencil", h, w, steps, impl, 2])
            for n, tile in [(1, 16), (31, 16), (31, 64), (128, 64)]:
                for impl in ["naive", "blocked"]:
                    run([b2 / "gemm", n, impl, tile, 2])
            run([b2 / "stencil", 2, 3, 1, "row", 1], expected=2)
            run([b2 / "gemm", 31, "unknown", 16, 1], expected=2)
            run([sys.executable, ROOT / "chaosuan-3/verify.py", "--build", b3,
                 "--output", tmp / "stage3-validation.json"])
            report["stage3_validation"] = json.loads((tmp / "stage3-validation.json").read_text())
        report["passed"] = True
    finally:
        report["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = ROOT / "docs" / ("verification-" + stamp + ".json")
        with target.open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("Evidence:", target, flush=True)
    print("ALL CHECKS PASSED", flush=True)

if __name__ == "__main__":
    main()
