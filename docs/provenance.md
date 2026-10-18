# 来源与整理范围

整理日期：2026-10-18（Asia/Shanghai）。

- 三个目录来自 WSL Ubuntu 的 `/home/destiny/project/chaosuan-{1,2,3}`。复制到新汇总仓库；原工作区保持原状。
- 排除第一题原有 `build/` 中的二进制、CMake 缓存和运行输出。保留学习笔记、报告、原始实验材料与验证记录。
- 第二题工作区缺少 `ai_result.md` 引用的 `experiments/`，从原交付备份 `ai_experiment_evidence.zip` 恢复。恢复前核对了 common.hpp、gemm.cpp、stencil.cpp、ai_result.md、tools.md 与工作区逐字节相同。
- 第一题 CMake 所引用的两个测试脚本未找到；不伪造原测试。源码与原 CMake 保持不变。
- 新增根 README、两题使用说明、报告准备提纲和统一复验脚本；不改动原算法。
- `source-manifest.json` 记录整理时源文件及恢复材料的 SHA256，可检查快照来源。历史测量不因上传而变成本次测量。
- 合并报告中的感想来自作者最新修改的桌面 Markdown，保持正文原话；技术摘要按已有证据整理，逐次数据通过 GitHub 固定归档链接引用。
- 本次新增根目录和第二题 CMake 入口，统一构建三个项目；不修改原算法、第一/三题原 CMake 或历史数据。原始快照的 316 项哈希仍可核对。
- 更新 README 和报告入口，PDF 与 Markdown 同步；不改动作者单独保存的感想和技术报告原稿。
