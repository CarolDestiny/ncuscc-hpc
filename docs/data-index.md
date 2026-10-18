# 详细数据与复现索引

[合并报告](report.md)保留工具、方法和主要成果；本页提供完整数据和命令。历史性能数据与本地正确性复验分别记录。

## 第一题：负载与采集

- [源码与构建说明](../chaosuan-1/README.md)
- [联动采样、环境及全部命令输出](verification-20261018T020039Z.json)：查看 `stage1_smoke.rows` 和 `commands`。
- 原 CMake 引用的两项 Python 测试未保留，本地只完成基本联动检查。

## 第二题：Stencil 与 GEMM

实验日期：2026-10-12。分别保存 WSL 和 i5-8250U 物理机结果，缓存与硬件计数证据只采用物理机。

- [完整报告：环境、参数、计时范围、结果及限制](../chaosuan-2/ai_result.md)
- [汇总 CSV](../chaosuan-2/experiments/results/summary.csv) / [完整统计 JSON](../chaosuan-2/experiments/results/summary.json)
- [WSL 逐次样本与命令](../chaosuan-2/experiments/results/wsl/runs.jsonl) / [环境](../chaosuan-2/experiments/results/wsl/environment.json)
- [物理机逐次样本与命令](../chaosuan-2/experiments/results/physical/runs.jsonl) / [环境](../chaosuan-2/experiments/results/physical/environment.json)
- [物理机硬件计数](../chaosuan-2/experiments/results/physical/hardware_perf.json) / [事件口径](../chaosuan-2/experiments/results/physical/hardware_event_definitions.txt)
- [实验、分析与剖析脚本](../chaosuan-2/experiments/)

独立编译和小规模正确性检查：

```bash
cmake -S chaosuan-2 -B build-stage2 -DCMAKE_BUILD_TYPE=Release
cmake --build build-stage2 -j2
./build-stage2/stencil 64 64 4 row 2
./build-stage2/stencil 64 64 4 column 2
./build-stage2/gemm 31 naive 16 2
./build-stage2/gemm 31 blocked 16 2
```

历史性能实验采用报告中的完整编译参数与重复方案。重新测量应使用独立结果目录，保留原批次。WSL 与物理机 CPU 不同，不能将两机耗时差解释为虚拟化开销。

## 第三题：稳定日志筛选

实验日期：2026-10-15，WSL 本地计时。

- [完整报告：实现、样本、收益和退化](../chaosuan-3/REPORT.md)
- [逐次测量、输入哈希、原始 stdout 和环境](../chaosuan-3/measurements.json)
- [原始验证命令与输出](../chaosuan-3/validation.json)
- [本地复验结果汇总](verification.md)及其中的完整记录，包含重新运行的公开/API/回归与 ASan/UBSan 结果。
- [基准脚本](../chaosuan-3/benchmark.py) / [验证脚本](../chaosuan-3/verify.py)

复现时使用新的输出文件名，脚本拒绝覆盖旧记录：

```bash
python3 chaosuan-3/verify.py --build build-stage3 --output validation-new.json
python3 chaosuan-3/benchmark.py --build build-stage3 --samples 7 --output measurements-new.json
```

混合命中约加速 1.68–2.68 倍，全命中耗时增加约 8.35%。所有速度比针对计算核心，不代替端到端性能或正式平台成绩。

## 整个仓库

新增统一入口已完成干净构建和复验，见[完整构建与测试记录](build-verification-20261018T024135Z.json)。

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
ctest --test-dir build --output-on-failure
python3 scripts/verify.py
```

统一构建后的程序位于 `build/chaosuan-{1,2,3}/`。完整复验脚本额外检查第一题联动和第二题的正常/错误参数。原始快照哈希见 [source-manifest.json](source-manifest.json)，来源见 [provenance.md](provenance.md)。
