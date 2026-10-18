# 第三关：稳定日志筛选

在 Linux / WSL 2 下使用 C++17 编译。读取 log-filter.v1 输入，按查询筛选，保留输入顺序、重复项和每条记录的全部字段。实现采用单线程 64 条位图分块，无第三方库、无 GPU、无全局状态。

## 构建与测试

需要 CMake >= 3.16、支持 C++17 的 GCC / Clang、Python >= 3.10。`requirements.txt` 无第三方 Python 依赖。所有命令从项目根目录执行：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
ctest --test-dir build --output-on-failure
```

默认生成 `build/log_filter`（优化版）、`build/baseline_original`（保留的原始程序）、`build/baseline_refactored`（只抽取接口的串行版本）和 `build/test_api`。编译选项为 `-std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic`，不依赖 `-march=native`、AVX2 或 OpenMP。CMake Release 与目标设置中的重复 `-O3` 等价；完整实际命令保存在 `measurements.json`。

不使用 CMake 时，优化主程序的等价编译命令为：

```bash
g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic main.cpp filter.cpp -o log_filter
```

## 使用

```bash
# 进程内生成数据，预热一次，然后测量七次；每次逐字段验证。
./build/log_filter --count 1000000 --hit-percent 50 --pattern random --seed 2026 --repeats 7

# 平台同版本 Python 生成器；不需要提交任何数据集。
python3 generate_logs.py --count 100000 --hit-percent 50 --pattern random --seed 2026 --output /tmp/logs.bin
./build/log_filter --input /tmp/logs.bin --output /tmp/selected.bin --repeats 7
```

输入模式不能混用 `--count/--seed/--hit-percent/--pattern/--export-input`。默认查询为 `[1000,2000)`、`latency_us >= 100`、`(flags & 3) == 3`；可用 `--begin/--end/--min-latency/--flags` 修改，`begin == end` 合法且结果为空，`begin > end` 拒绝。全部数值参数为无符号十进制。输出文件必须尚不存在，不覆盖输入、硬链接或软链接。默认 `--max-records 10000000`；可显式修改。

`--output` 只写最后一次已验证的结果；`--export-input` 保存进程内生成的输入。生成、加载、分配、参考结果、验证和文件输出均在核心计时之外；核心计时包括全部筛选计算与命中记录写入。原始版和优化版保持相同边界。

## 接口和文件格式

`filter.hpp` 声明：

```cpp
std::size_t filter_records(const Record* input, std::size_t count,
                           Record* output, const Query& query);
```

输入输出不重叠，output 容量至少 count；count=0 时两指针可为空；查询由调用方验证；返回条数，输出前缀有效。仅链接 `filter.cpp` 即可从自己的 C++ 驱动调用该接口；不要同时链接 `serial_filter.cpp`，两者提供同一接口的不同实现。

二进制为显式小端，不直接保存 C++ 结构体布局：24 字节文件头依次是 8 字节 `NCULOG01`、u32 版本 1、u32 记录宽度 24、u64 条数。每条记录为 u64 timestamp、u32 source_id、u32 latency_us、u32 payload_bytes、u32 flags，总计 24 字节。文件总长必须严格为 `24 + 24*N`。文件格式与生成器保持原样。

## 复现验证和性能

```bash
# 编译、原始/重构公开测试、全部新测试，以及 ASan/UBSan 验证。
python3 verify.py --build build --output validation-rerun.json

# 五组数据，每组每种实现至少七个样本；生成数据在临时目录自动清理。
python3 benchmark.py --build build --samples 7 --output measurements-rerun.json
```

脚本拒绝覆盖已有证据文件。默认发布包中已包含本次的 `validation.json` 与 `measurements.json`。后者记录生成参数、输入 SHA256、原始 stdout、逐次核心耗时、进程总耗时、运行顺序、编译选项与机器信息；每个保留样本之前均有一次预热。首次运行还会逐字节比较三种实现的全部序列化输出；所有样本的 C++ 驱动都会逐字段比较完整参考输出。

`test_public.py`、`baseline.cpp`、`support.hpp`、`generate_logs.py` 原样保留。`test_api.cpp` 包含 1057 个直接接口用例；`test_regression.py` 包含分块边界、完整字段、重复项、Python/C++ 生成器一致性与输出链接保护测试。

## 正式平台提交

提交单根目录 `chaosuan-3/` 的 `.tar.gz`，上限 32 MiB。根目录含源码、CMakeLists.txt、requirements.txt、公开/新增测试、报告及原始测量。无需数据集。压缩包中没有构建产物、软链接、隐藏测试或绝对路径条目。

本次仅执行 WSL 2 本地验证；正式正确性与排名由平台 Linux runner / 发布的 checker 判定。收到的文件与截图未提供完整 checker 命令或镜像标签，因此没有声称已通过正式平台。CPU 本地实现不需要 GPU。
