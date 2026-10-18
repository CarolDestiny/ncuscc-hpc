# 第二题：stencil 与 GEMM

- `thinking.txt`：原工作区保留的个人代码阅读笔记。
- `ai_result.md`：既有实验报告，包含历史计时、物理机缓存/PMU 分析和限制。
- `experiments/`：从原交付备份恢复的脚本及历史原始结果。
- `tools.md`：工具使用说明，以及 whole-process 与 kernel 计时的区别。

可通过仓库根目录统一构建，也可在本目录执行 `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j2`。

基本编译与正确性复验（不等同于历史性能实验的编译配置）：

```bash
mkdir -p build
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic stencil.cpp -o build/stencil
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic gemm.cpp -o build/gemm
./build/stencil 64 64 4 row 2
./build/stencil 64 64 4 column 2
./build/gemm 31 naive 16 2
./build/gemm 31 blocked 16 2
```

历史性能实验的完整编译配置、成对顺序和规模见 `ai_result.md`。原始测量和当前基本复验应分开引用，不以 WSL 虚拟缓存信息代替物理机缓存证据。
