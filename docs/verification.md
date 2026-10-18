# 本次复验结果

复验日期：2026-10-18（Asia/Shanghai）。这次只重新检查正确性，没有重跑历史性能或物理机 PMU 测量。

- 源快照 SHA256：316 个文件核对通过。
- 第一题：Release 构建、两个帮助入口、真实负载与采集联动、JSONL schema 和目标 PID 检查通过。原 CMake 引用的两个测试脚本缺失，未宣称其通过。
- 第二题：stencil row/column 各 3 组尺寸；GEMM naive/blocked 各 4 组尺寸与 tile；另有 2 组错误参数退出码检查，全部通过。
- 第三题：原始和重构基线各 7 项公开测试；优化版 3 组 CTest；1057 个 API 用例；ASan/UBSan API 与 CLI 测试通过。完整命令和输出保存在下面的 JSON 中。

原始记录：[本次复验证据](verification-20261018T020039Z.json)。

正式平台 checker 与排行榜没有在本次运行，不能将本地结果称为正式验收成绩。
