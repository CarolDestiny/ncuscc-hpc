# NCUSCC 超算学习与实验

三个 C/C++ 工作区的源码、实验材料及合并考核报告。

**阅读入口：[合并报告](docs/report.md) · [PDF](docs/report.pdf) · [详细数据与复现](docs/data-index.md)**

| 目录 | 内容 | 说明 |
| --- | --- | --- |
| [chaosuan-1](chaosuan-1/) | CPU 负载与 Linux procfs 指标采集 | [使用说明](chaosuan-1/README.md) |
| [chaosuan-2](chaosuan-2/) | Stencil / GEMM、访问顺序与分块实验 | [使用说明](chaosuan-2/README.md)、[详细报告](chaosuan-2/ai_result.md) |
| [chaosuan-3](chaosuan-3/) | 稳定日志筛选及位图分块优化 | [使用说明](chaosuan-3/README.md)、[详细报告](chaosuan-3/REPORT.md) |
| [docs](docs/) | 合并报告、数据索引、验证记录和来源 | [验证结果](docs/verification.md) |
| [scripts](scripts/) | 完整正确性复验入口 | [verify.py](scripts/verify.py) |

## 统一构建

需要 Linux / WSL 2、CMake、G++（C++17）和 Python 3。

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
ctest --test-dir build --output-on-failure
```

可执行文件位于 `build/chaosuan-1/`、`build/chaosuan-2/`、`build/chaosuan-3/`。第二题也可单独用 CMake 构建。根目录 CTest 运行第三题现存的 3 组测试；第一题原 CMake 引用的两项脚本缺失，统一入口明确提示并关闭这两项注册，不将其计为通过。

完整复验（第一题联动、第二题参数与边界、第三题公开/API/回归及 ASan/UBSan）使用：

```bash
python3 scripts/verify.py
```

该脚本在临时目录构建，将命令与输出保存为新的 `docs/verification-*.json`，不覆盖历史测量。

## 数据与报告

报告正文只保留工具、方法和主要成果，逐次样本、环境、编译参数及硬件计数通过[数据索引](docs/data-index.md)引用。感想来自作者最新修改的 Markdown；技术、实验和报告中的 AI 使用已在正文说明。

第二题历史证据由原交付备份恢复，第三题保留原始测量与测试输出。核心算法、历史数据和原始文件哈希保持原状。第一题缺失的测试和未执行的正式平台验收均已注明，具体见[整理来源](docs/provenance.md)。
