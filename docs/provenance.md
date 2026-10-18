# 来源与整理范围

整理日期：2026-10-18（Asia/Shanghai）。

- 三个目录来自 WSL Ubuntu 的 `/home/destiny/project/chaosuan-{1,2,3}`。复制到新汇总仓库；原工作区保持原状。
- 排除第一题原有 `build/` 中的二进制、CMake 缓存和运行输出。保留学习笔记、报告、原始实验材料与验证记录。
- 第二题工作区缺少 `ai_result.md` 引用的 `experiments/`，从原交付备份 `ai_experiment_evidence.zip` 恢复。恢复前核对了 common.hpp、gemm.cpp、stencil.cpp、ai_result.md、tools.md 与工作区逐字节相同。
- 第一题 CMake 所引用的两个测试脚本未找到；不伪造原测试。源码与原 CMake 保持不变。
- 新增根 README、两题使用说明、报告准备提纲和统一复验脚本；不改动原算法。
- `source-manifest.json` 记录整理时源文件及恢复材料的 SHA256，可检查快照来源。历史测量不因上传而变成本次测量。
- 感想报告仅提供本人填写提示；不代写作者的个人经历。
