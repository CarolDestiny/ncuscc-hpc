# NCUSCC 超算学习与实验

本仓库汇总三个 WSL 工作区的源码、学习笔记与可核对的实验材料，供最终技术报告引用。

| 目录 | 内容 | 阅读入口 |
| --- | --- | --- |
| [chaosuan-1](chaosuan-1/) | Linux CPU 负载程序、procfs 指标采集与 JSONL 输出 | [构建与现状](chaosuan-1/README.md) |
| [chaosuan-2](chaosuan-2/) | 五点 stencil、矩阵乘法、访问顺序与分块实验 | [实验报告](chaosuan-2/ai_result.md)、[个人分析](chaosuan-2/thinking.txt) |
| [chaosuan-3](chaosuan-3/) | 稳定日志筛选、64 条位图分块优化与回归验证 | [使用说明](chaosuan-3/README.md)、[实验报告](chaosuan-3/REPORT.md) |

## 构建和验证

需要 Linux / WSL 2、CMake、G++（C++17）和 Python 3。仓库不附带编译器、构建缓存或生成的数据集。

```bash
python3 scripts/verify.py
```

脚本在临时目录构建：第一题执行负载与采集联动检查；第二题测试两种 stencil 和两种 GEMM 实现及边界；第三题调用原有验证脚本，检查公开测试、回归测试和 ASan/UBSan。它不重跑历史性能测量或物理机 PMU 采样。

第一题的原 CMake 引用了未保留的 `tests/integration_test.py` 和 `tests/lifecycle_test.py`。当前复验关闭这两项注册，并明确区分新增的基本联动检查与缺失的原测试；原源码和 CMake 不作修改。

## 实验材料与结果口径

第二题的 `experiments/` 从原交付备份 `ai_experiment_evidence.zip` 恢复；恢复前逐字节核对了归档中的源码、报告和工具说明与工作区一致。该目录包含 WSL/物理机样本、环境、分析脚本和物理机 PMU 证据。历史性能结果不等于本次重新测得的成绩。

第三题保留 `measurements.json`、`validation.json` 与原始文件哈希。历史混合命中场景约有 1.68–2.68 倍核心加速，全命中场景约退化 8.35%；报告保留了收益、退化与环境限制。WSL 本地验证不代表正式平台验收或排名。

本次复验：[结果与完整命令](docs/verification.md)。

## 最终报告准备

- [报告要求和素材索引](docs/report-plan.md)
- [技术报告提纲](docs/technical-report.md)
- [感想报告待本人填写](docs/reflections.md)
- [仓库整理来源与范围](docs/provenance.md)

技术报告可以基于代码、命令和实验材料整理。感想报告需要作者提供真实经历、问题和思考，目前仅保留提示，不代写个人体验。部分既有分析、实现、测试和文档使用了 AI 辅助，具体过程应在最终报告中如实说明。
