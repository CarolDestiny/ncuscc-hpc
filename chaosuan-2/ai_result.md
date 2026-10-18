# ai_result：stencil 与 GEMM 成对实验报告

实验日期：2026-10-12（北京时间）。本报告由 AI 协助执行真实实验并整理，基于 `thinking.txt`，原始三个源码文件未修改。更新：按用户要求，缓存与 PMU 分析只使用物理机；WSL 保留正确性和计时实验。

**结果：两台机器所有正确性检查通过；stencil 应使用 row，GEMM 应使用 blocked。大 GEMM 的 tile=128 在补充成对复测中比 64 快约 7%，但 WSL 存在波动，参数结论只适用于本次规模和编译配置。**

## 1. 环境与方法

| 项目 | WSL 虚拟机 | Ubuntu 物理机 |
| --- | --- | --- |
| CPU | i9-14900HX，暴露 2 vCPU | i5-8250U，4 核 / 8 线程 |
| 内存 / swap | 3.83 GiB / 4 GiB | 约 7.0 GiB / 4 GiB |
| 系统 | WSL2 / Microsoft Hyper-V，Linux 6.18.33.2 | Linux 7.0.0-31-generic，systemd-detect-virt=none |
| 每核 L1d / L2 | 不用于缓存分析 | 32 KiB / 256 KiB |
| 共享 L3 / 缓存行 | 不用于缓存分析 | 6 MiB / 64 B |
| GCC | 15.2.0-16ubuntu1 | 15.2.0-16ubuntu1 |
| 执行配置 | 单线程，taskset 绑定 CPU 0 | 单线程，taskset 绑定 CPU 0；powersave，动态频率 |
| perf 硬件事件 | 本次不进行缓存/PMU分析 | sudo 后可用；普通用户 perf_event_paranoid=4 |

两边统一编译：`g++ -std=c++17 -O3 -march=x86-64-v3 -mtune=generic -ffp-contract=off -g`。不使用 fast-math；固定输入 seed=2026。源码 SHA-256 一致，详见两边 `environment.json`。WSL 来宾信息不能确定宿主实际调度到的 P/E 核；本报告不据此作物理缓存结论。

主实验每个实现 **3 轮 × 3 次 = 9 个计时样本**；每次程序启动先完成 1 次不计入统计的预热。每轮成对运行，顺序为 AB / BA / AB：stencil A=row、B=column，GEMM A=naive、B=blocked（tile=64）。配对控制了输入、规模、编译配置及运行轮次，并未声称具有统计显著性。

| 数据集 | 小数据集 | 大数据集 |
| --- | --- | --- |
| stencil | 512×512，20 steps；工作双缓冲 2 MiB | 4096×4096，20 steps；工作双缓冲 128 MiB |
| GEMM | N=128；A+B+C=192 KiB | N=1024；A+B+C=12 MiB |

stencil 另有 input 与 FP64 ref/tmp，总数组占用约 7 / 448 MiB；GEMM 另有 FP64 reference 与 scratch。只计 kernel：stencil 包括全部时间步与 swap；blocked 包括 packing、scratch 清零与 copy-out。分配、初始化、FP64 reference、每次恢复输入和校验不计时。恢复输入与校验会影响缓存，因此是预热后的重复工作负载，不是冷缓存实验。

统计：`mean=Σt/n`；中位数按排序取中间值；**总体标准差** `σ=sqrt(Σ(t-mean)²/n)`，分母不是 n−1。下面吞吐均用中位数，GB 使用 10⁹ B：

- stencil：`U=(H−2)(W−2)×steps`，`F=6U`，`Q_eff=8U B`；GFLOP/s=`F/(t_ms×10⁶)`，有效 GB/s=`Q_eff/(t_ms×10⁶)`。8 B/update 是理想空间复用的有用字节模型，包含一次 FP32 读和一次写。
- GEMM：`F=2N³`；统一用 `Q_min=12N² B`（A、B 各读一次，C 写一次）的**最低有用字节模型**计算有效 GB/s。它不是 naive/blocked 的实际访存量，也不是硬件 DRAM 带宽。

## 2. 成对实验数据

### stencil

| 机器 | 规模 | 实现 | 正确性 | 平均 ms | 中位数 ms | 总体 σ ms | GFLOP/s | 有效 GB/s（8 B/update） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WSL | 小 | row | PASS | 1.09081 | 0.671513 | 1.16804 | 46.4801 | 61.9735 |
| WSL | 小 | column | PASS | 16.2408 | 15.9935 | 0.844101 | 1.95154 | 2.60206 |
| WSL | 大 | row | PASS | 117.642 | 118.556 | 4.71314 | 16.965 | 22.62 |
| WSL | 大 | column | PASS | 6884.62 | 6989.21 | 178.987 | 0.287772 | 0.383696 |
| 物理机 | 小 | row | PASS | 1.33984 | 1.33807 | 0.0133475 | 23.3261 | 31.1015 |
| 物理机 | 小 | column | PASS | 27.7792 | 27.8108 | 0.856184 | 1.1223 | 1.4964 |
| 物理机 | 大 | row | PASS | 266.462 | 266.522 | 0.457741 | 7.54647 | 10.062 |
| 物理机 | 大 | column | PASS | 11539.2 | 11612.3 | 118.262 | 0.173204 | 0.230939 |

### GEMM（blocked tile=64）

| 机器 | 规模 | 实现 | 正确性 | 平均 ms | 中位数 ms | 总体 σ ms | GFLOP/s | 有效 GB/s（Q_min） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WSL | 小 | naive | PASS | 0.834737 | 0.791575 | 0.127573 | 5.29868 | 0.248376 |
| WSL | 小 | blocked | PASS | 0.113005 | 0.107038 | 0.00723125 | 39.1852 | 1.83681 |
| WSL | 大 | naive | PASS | 2216.67 | 2215.95 | 19.8486 | 0.969103 | 0.00567834 |
| WSL | 大 | blocked | PASS | 63.0038 | 63.1274 | 1.37829 | 34.0182 | 0.199326 |
| 物理机 | 小 | naive | PASS | 2.04999 | 2.04739 | 0.0203734 | 2.04861 | 0.0960286 |
| 物理机 | 小 | blocked | PASS | 0.247215 | 0.249198 | 0.00290412 | 16.8312 | 0.788963 |
| 物理机 | 大 | naive | PASS | 3123.55 | 3194.03 | 351.135 | 0.672343 | 0.00393951 |
| 物理机 | 大 | blocked | PASS | 119.478 | 119.525 | 0.209791 | 17.9668 | 0.105274 |

| 机器 | 规模 | row 相对 column 加速 | blocked 相对 naive 加速 |
| --- | --- | --- | --- |
| WSL | 小 | 23.82× | 7.40× |
| WSL | 大 | 58.95× | 35.10× |
| 物理机 | 小 | 20.78× | 8.22× |
| 物理机 | 大 | 43.57× | 26.72× |

WSL 小 stencil row 的全部样本为 `[0.837615, 0.766169, 4.3877, 0.609207, 0.646298, 0.580375, 0.631967, 0.671513, 0.686453] ms`，其中 4.3877 ms 拉高平均与 σ，**未删异常值**。物理机大 naive GEMM 三轮中位数为 2669.60 / 3194.03 / 3446.49 ms，存在漂移；调度、频率、温度等原因未被单独验证。使用中位数可减轻异常影响，不能消除系统干扰。不同 CPU 的 WSL/物理机比较也不能被解释为“虚拟化开销”。原目录旧测试缺少编译配置，未混入本次统计。

## 3. 正确性

原程序每次预热及正式运行都对全部 FP32 输出进行独立 FP64 reference 比较：`isfinite(got) && |got−ref| ≤ 1e−5+1e−4×|ref|`，checksum 只作辅助。stencil 还要求边界严格为零。原计时与验证批次中，两台机器各 236 次逐元素检查全部 PASS（主实验、tile 扫描、补充复测、关闭向量化对照、预跑及边界用例合计），共 472 次。

| 工作负载 | 小数据集最大绝对误差 | 大数据集最大绝对误差 |
| --- | --- | --- |
| stencil（两实现、两机器一致） | 1.29584e−7 | 1.56184e−7 |
| GEMM（两实现、两机器及 tile 扫描一致） | 2.54014e−5 | 5.77060e−4 |

GEMM 大矩阵的绝对误差超过 1e−5 并不意味着失败，因为逐元素检查还包含相对容差。额外验证：GEMM N=1、31/tile=16、65/tile=32、31/tile=64（非整 tile 与 tile>N）；stencil 3×3/1 step、7×11/3 与 4 steps（矩形及奇偶时间步），均 PASS。

## 4. 物理机硬件缓存、SIMD 与瓶颈证据

**只在 i5-8250U 物理机上分析缓存。** 普通用户运行 perf 被 perf_event_paranoid=4 拒绝；使用 sudo 后已成功采集真实 PMU 事件，不需要修改 sysctl。工具包括 `perf stat`、`lscpu`/sysfs、GCC 向量化报告、`objdump` 和物理机 Cachegrind；WSL 缓存模拟已从报告及交付证据包中撤下。

硬件采样使用相同 kernel、规模、seed、编译选项和单线程 CPU 0。辅助 driver 包含原始 kernel，先预热一次、恢复输入，再通过 perf `--control fd` 的 enable/disable 与 ack 把 PMU 计数限制在 kernel 区域；排除初始化、FP64 reference、恢复输入、checksum 与打印。事件使用 `:u` 只计用户态；区域边界有少量控制指令。每个实现重复 3 次并按 AB/BA/AB 排序；与独立的计时成绩分开。全部 48 次采集事件运行比例为 100%，没有复用缩放。

为避免 NMI watchdog 占用计数器后的硬件槽位不足，分两组采集：① cycles、instructions、mem_load_retired.l1_hit/l1_miss/fb_hit；② cycles、instructions、mem_load_retired.l3_hit/l3_miss。曾尝试同时加入 L2 事件导致 not counted，已减少事件数并完整重采，未将不可用计数填零。事件定义来自该机 `perf list --details mem_load_retired`，不是泛化 cache-misses 别名。

下面 cycles、instructions 与 miss 数为 3 次采集的**算术平均计数**，IPC=`Σinstructions/Σcycles`（第一组）。L1 事件命中占比=`Σl1_hit/(Σl1_hit+Σl1_miss)`；L3 事件命中占比=`Σl3_hit/(Σl3_hit+Σl3_miss)`，为相应退休 load 事件的限定口径。FB hit 单独列出，未归入 L1 hit；这些比例不是所有读写操作的总命中率，L3 占比也不是全体 load 的命中率。

| 规模 | 实现 | cycles (百万) | instructions (百万) | IPC | L1事件命中占比 | L1 miss (百万) | FB hit (百万) | L3事件命中占比 | L3 miss (百万) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stencil 512 | row | 4.5705 | 8.0708 | 1.766 | 95.64% | 0.1348 | 0.4261 | 99.52% | 0.0001 |
| stencil 512 | column | 92.2445 | 67.7612 | 0.735 | 10.29% | 1.8737 | 23.9217 | 100.00% | 0.0000 |
| stencil 4096 | row | 825.9533 | 468.2746 | 0.567 | 69.43% | 25.1217 | 129.4749 | 54.86% | 0.9912 |
| stencil 4096 | column | 13562.0714 | 4358.8960 | 0.321 | 32.58% | 146.9368 | 1458.1152 | 8.83% | 105.0522 |
| gemm 128 | naive | 6.8687 | 9.0965 | 1.324 | 18.83% | 2.1184 | 0.0290 | 99.69% | 0.0000 |
| gemm 128 | blocked | 0.8327 | 2.4890 | 2.989 | 98.80% | 0.0084 | 0.0109 | 99.57% | 0.0000 |
| gemm 1024 | naive | 7540.4645 | 4574.9598 | 0.607 | 20.27% | 1060.1746 | 13.4760 | 94.58% | 55.9160 |
| gemm 1024 | blocked | 405.3087 | 1266.4680 | 3.125 | 99.10% | 3.2136 | 4.0454 | 91.60% | 0.0988 |

实测对照：大 stencil column 的 L3 miss 平均约 1.0505 亿，row 约 99.12 万，前者约 106 倍，IPC 为 0.321/0.567；大 GEMM naive 的 L1 miss 约 10.6017 亿，blocked 约 321.36 万（约 330 倍），IPC 为 0.607/3.125。小 stencil column 的 L3 事件命中占比接近 100% 仍明显较慢，说明 LLC 能命中也可能存在 L1 局部性和访问延迟限制。

注意：大 GEMM naive 的 L3 事件命中占比 94.58% 反而高于 blocked 的 91.60%，但 naive 的 L3 miss 约 5591.60 万，blocked 约 9.88 万；分块大幅减少了需要访问下层缓存的总 load。因此不能按单个层级的命中百分比给实现排序。

此 driver 未在同一运行中重复 FP64 校验；原 kernel 已在第 3 节逐元素通过校验，48 次硬件采样的 checksum 也与对应原程序一致。checksum 仅是辅助证据。不同计数组是独立运行，不能直接拼成精确的完整缓存流量分解。计数对象是退休 load 指令，不包括所有 store、RFO、硬件预取和写回；不能用 miss×64 或有效 GB/s 代替实测 DRAM 字节。

物理机 Cachegrind 3.26.0 仅作补充，模拟 D1=32 KiB/8-way、LL=6 MiB/12-way，缓存行 64 B；以 client request 只采 kernel，初始模拟状态与 PMU 的预热状态不同。它不模拟独立 L2、硬件预取、TLB、真实延迟和共享竞争，辅助规模也不同，不能将其 miss 次数除以主实验 compute_ms。

| 物理机模拟工作负载 | 顺序 | D1 misses（读+写） | LL data misses（读+写） |
| --- | --- | --- | --- |
| stencil 512²×2 steps | column/row | 1,107,741/65,425 | 32,781/32,778 |
| stencil 2048²×2 steps | column/row | 17,800,221/1,060,353 | 17,800,221/1,048,081 |
| gemm 128，tile=64 | naive/blocked | 2,131,723/15,774 | 3,085/3,731 |
| gemm 512，tile=64 | naive/blocked | 134,789,134/836,735 | 49,167/49,941 |

SIMD 证据也仅采用物理机：GCC 报告 `stencil.cpp:25` 的 row 循环使用 32/16 B 向量，column 跨步路径受 strided load 限制；`gemm.cpp:44` 的 blocked 连续 j 循环使用 32/16 B 向量；naive 归约循环存在部分 16 B 向量化，不能称为“完全无 SIMD”。关闭向量化后仍通过校验；小数据集各 5 次的中位数为：

| 物理机小数据集 | 顺序 | 允许向量化 ms | 关闭向量化 ms | 加速比变化 |
| --- | --- | --- | --- | --- |
| stencil | column/row | 27.8108/1.33807 | 26.867/5.6596 | 20.78× → 4.75× |
| gemm | naive/blocked | 2.04739/0.249198 | 2.22682/1.04208 | 8.22× → 2.14× |

该编译对照还影响指令组织，不能据速度差计算 SIMD 的精确贡献百分比。缓存模拟的 SIMD/标量访问粒度也不同，不宜把模拟失效率直接当成源代码 load 的命中率。

瓶颈判断使用上述物理机硬件事件、缓存模拟与编译证据交叉验证。WSL 只据计时报告版本优劣，不据其虚拟缓存信息判定实际缓存行为。

| 对象 | 瓶颈判断 | 结论边界 |
| --- | --- | --- |
| stencil column | 跨行访存导致局部性差、缓存行利用率低，并且缺少连续 SIMD；对照硬件退休 load 事件与辅助模拟缓存失效 | TLB、预取和内存控制器流量未单独采集 |
| stencil row | 小集受益于缓存和 SIMD；物理机大双缓冲达 128 MiB，有效带宽降至 10.06 GB/s，低算术强度 0.75 FLOP/B，符合流式访存限制特征 | 退休 load 命中率高也不证明无内存瓶颈；未测 STREAM，不能声称 DRAM 带宽饱和 |
| GEMM naive | B 跨列、cache set 冲突风险与 k 归约依赖限制吞吐；N=1024 跨步 4096 B；辅助 N=512 模拟 D1 miss 约为 blocked 的 161 倍 | 低 IPC 与缓存失效是组合证据，不能单凭其中一个指标判定 DRAM 饱和 |
| GEMM blocked | 连续 j、分块复用及 SIMD 降低访问与指令成本；剩余开销含 packing、scratch 清零、输出写回及计算 | 未对各阶段单独计时，不能定量指定唯一剩余瓶颈 |

blocked 输入块流量模型在 N 可整除 T、scratch 保留于目标缓存时约为 `Q_tile=8N³/T+4N² B`，算术强度趋近 `T/4 FLOP/B`；实际流量受重复打包、写分配及 scratch 访存影响。stencil 的 5 个源代码读取也不等于 5 次 DRAM 读取。

## 5. tile 扫描与优化决策

| 机器 | 规模 | T=16 ms | T=32 ms | T=64 ms | T=128 ms | T=256 ms |
| --- | --- | --- | --- | --- | --- | --- |
| WSL | N=128 | 0.230356 | 0.163482 | 0.107038 | 0.118674 | 0.123637 |
| WSL | N=1024 | 121.167 | 90.7943 | 63.1274 | 63.6244 | 70.4135 |
| 物理机 | N=128 | 0.60028 | 0.352411 | 0.249198 | 0.210647 | 0.248856 |
| 物理机 | N=1024 | 340.23 | 180.638 | 119.525 | 111.572 | 122.141 |

扫描中 T=64 引用主实验的 9 样本，其他 T 各 5 样本；不混合重复批次。三个 scratch 合计 `12T² B`：T=16/32/64/128/256 分别约 3/12/48/192/768 KiB。只据物理机实际缓存判断：T=64 的三个 scratch 合计超过其 L1d；T=128 在其 L2 可容纳，T=256 超过其 L2。容量说明取舍，不能保证实际驻留。

大 GEMM 对 T=64/128 再做 3 轮×3次、顺序 64→128 / 128→64 / 64→128 的独立复测：

| 机器 | tile | 正确性 | 平均 ms | 中位数 ms | 总体 σ ms | GFLOP/s | 有效 GB/s（Q_min） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WSL | 64 | PASS | 61.2914 | 61.9263 | 2.53481 | 34.6781 | 0.203192 |
| WSL | 128 | PASS | 58.4185 | 57.7726 | 2.02646 | 37.1713 | 0.217801 |
| 物理机 | 64 | PASS | 120.523 | 119.721 | 1.40658 | 17.9374 | 0.105102 |
| 物理机 | 128 | PASS | 112.032 | 112.153 | 0.620095 | 19.1478 | 0.112194 |

- WSL：128 相对 64 为 1.072×，中位时间减少 6.71%。
- 物理机：128 相对 64 为 1.067×，中位时间减少 6.32%。

决策：**stencil 优先 row；GEMM 优先 blocked，小 N=128 时 WSL 选 64、物理机可选 128；大 N=1024 暂选 128。** 物理机复测三轮均为 128 更快，WSL 三轮中两轮更快，故 WSL 的参数收益应视为待跨会话复验的小幅收益。禁止单凭“块越大复用越好”选择 256。N=128、tile=256 会清零大量未使用的 scratch，且 N 小时打包开销更显著。

后续优先级：① 已验证的遍历/分块/SIMD配置；② 在保持校验下减少 GEMM 对相同 A/B 块的重复 packing，尝试寄存器 microkernel 或成熟 BLAS；③ 如扩大 stencil 规模，再测试空间/时间分块及多线程，保持每个时间步只读旧网格、双缓冲与零边界。后两项是后续实验建议，本次没有实现或宣称收益；多线程应同时测加速比与带宽，不直接按核心数外推。

对 `thinking.txt` 的补充：stencil 是加权平滑/扩散而非锐化；最外层 `run` 重复次数由 repeats 控制，steps 是每次计时内的时间步；blocked 的 scratch 分配不在计时内，但 packing/清零/copy-out 在计时内。

## 6. 原始证据与复现

项目位置：WSL `/home/destiny/project/chaosuan-2`；物理机隔离实验目录 `/home/user/project/chaosuan-2-ai-20261012`。物理机日志已同步回 WSL。原始样本、命令、环境、向量化报告和缓存剖析均保存在：

- `experiments/results/{wsl,physical}/runs.jsonl` 及同目录每次运行 `.txt`：所有实测样本、正确性结果、命令和 UTC 时间。
- `experiments/results/summary.json`、`summary.csv`：按同配置汇总，保留总体标准差、样本、每轮中位数与最大误差；JSON 是完整统计证据。
- `experiments/results/{wsl,physical}/environment.json`：两机环境；缓存、向量化和反汇编工具证据仅使用 `experiments/results/physical/`。
- `experiments/results/physical/hardware_perf.json`、`hardware_summary.json`、`hardware_*.perf.csv`、`hardware_*.txt`、`hardware_event_definitions.txt`：物理机真实 PMU 原始计数、事件口径和区域控制命令；另有物理机 `cache_*.cg`、`cache_summary.json` 作为模拟补充。
- `ai_experiment_evidence.zip`：可离线解压查看的源码、实验脚本、报告和上述证据；不含 SSH 凭据、下载工具包或编译二进制。

复现主要实验（会追加 runs.jsonl；重跑时先把原 results 目录改名保存，避免把不同会话合并）：

```bash
cd /home/destiny/project/chaosuan-2
python3 experiments/run_experiments.py wsl --phase setup
python3 experiments/run_experiments.py wsl --phase full
python3 experiments/confirm_tiles.py wsl
python3 experiments/analyze.py .
```

缓存分析仅在物理机复现：在 `/home/user/project/chaosuan-2-ai-20261012` 中运行 `python3 experiments/profile_experiments.py physical` 获取模拟/编译证据，再运行 `sudo python3 experiments/hardware_perf.py` 获取真实 PMU 证据。Valgrind 3.26.0 可通过 `apt-get download valgrind`、`dpkg-deb -x ... experiments/tools/local` 本地解包；计时脚本不依赖它。PMU 脚本重写本批次计数日志，计时脚本追加 runs.jsonl，重跑前应保存旧结果。无需在报告或脚本中保存登录密码。
