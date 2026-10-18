# 第一题：Linux 负载与指标采集

`src/workload.cpp` 创建可配置 CPU 负载；`src/collector.cpp` 对目标进程定时采集；`src/linux_procfs.*` 读取 Linux procfs；`src/metrics_schema.hpp` 提供 `hpc-metrics.v1` 和 JSON 输出工具。

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build build -j2
./build/workload --help
./build/collector --help
```

示例（输出路径必须尚不存在）：

```bash
./build/workload --threads 1 --duration 3s --pid-file /tmp/ncuscc-workload.pid &
./build/collector --pid-file /tmp/ncuscc-workload.pid --interval 200ms --duration 1s --output /tmp/ncuscc-metrics.jsonl
wait
```

现存目录缺少 CMake 引用的两个 Python 测试脚本，因此构建显式设置 `BUILD_TESTING=OFF`。仓库根目录的验证脚本另行检查程序联动与 JSONL 可解析性，不宣称恢复或通过了这两个原测试。
