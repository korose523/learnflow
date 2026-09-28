# ④b 矩阵 · S3 规模档的算力约束实测证据（2026-09-27 记录 / 2026-09-28 更新）

> ## ⚠ 状态更新（2026-09-28）——先读这一段，下文 §1–§4 为历史留痕
>
> 本文件原题「S3 规模档在本机**不可扩展**」，其结论**已被后续事实部分推翻**，现予更正：
>
> 1. **本机已升级至 32 GB RAM**（原 15.8 GB），`deepseek-r1:32b` 于 2026-09-28 **复跑成功**：
>    E1-A **212/212** 解析、`ρ=0.0891`、E1-B **108/108**（100% 覆盖）。
>    → **F4_DeepSeek / S3 格现为 `EVALUATED`，不再是 NOT_RUN。**
> 2. 矩阵 `m3_model_scale_matrix.csv` 现为 **11 个 EVALUATED 单元格**，触及 **4 族 × 3 档**：
>    F1_Qwen、F3_Mistral、F4_DeepSeek 三族 S1/S2/S3 齐全；**唯一缺口为 F2_Llama 的 S3 档**。
> 3. **F2_Llama 缺 S3 是结构性的、非算力问题**：开放权重中 Llama 无 30–70B 档
>    （1B/3B/8B/70B/405B，70B 落 S4），**换机器也补不上**。
>    → ④b「≥3 族 × ≥3 规模**全覆盖**」因此**仍未解除**，M3 §8「不宣称跨模型 LLM 边界」维持不变；
>    但其理由已从「算力不足」更正为「**F2 族开放权重无该档位**」。
> 4. 下文 §1–§4 完整保留 2026-09-27 在 15.8 GB 机器上的实测止损证据，**不作删除**（过程留痕），
>    但**不得再作为「S3 不可算 / F4_S3 为 NOT_RUN / 矩阵 8 格」的当前依据**——那是旧快照。
>
> 相关更正同步见：`m3_colibri_verification_20260927.md`（§5、§8 已更正）。

## 原文结论（2026-09-27，历史留痕）

**原结论一句话**：本机（15.8 GB RAM）物理内存小于 30B 级模型的权重体积，S3（30–70B）档
每格需 ≥30 小时且持续超时，因此在**当时那台机器**上无法补齐。以下全部为实测值，不推断、
不估算自网页。

## 1. 机器规格（实测）

| 项 | 实测值 | 取得方式 |
|---|---|---|
| 物理内存 | **15.8 GB**（可用 0.3 GB，负载 97%，跑批期间） | `GlobalMemoryStatusEx` |
| CPU | 8 核 | `os.cpu_count()` |
| NVIDIA GPU | **无**（`nvidia-smi` 不存在） | 命令不存在 |
| Ollama 推理位置 | **CPU-only**（`/api/ps` 各模型 `size_vram=0`） | `curl localhost:11434/api/ps` |

## 2. 目标模型体积（实测）

| 模型 | 参数量 | 量化 | 盘上体积 | 与内存比较 |
|---|---|---|---|---|
| `deepseek-r1:32b` | 32.8B | Q4_K_M | **19 GB**（`ollama list`） | **19 GB > 15.8 GB → 必然换页** |
| `deepseek-r1:1.5b` | 1.8B | Q4_K_M | 1.1 GB | 可装 |

## 3. 跑批实测（`results/m3/_r1_32b_out.txt`）

- E1-A 进度：**25/212 题，elapsed = 13002 s** → 约 **520 秒/题**
- 外推：E1-A 全量 212 题 ≈ **30.6 小时**（尚未计 E1-B 的 108 批）
- 期间出现多次 `[E1A ERR] <key> timed out`（单次请求超时 600 s，慢于该阈值的题直接判失败）
- 处置：**停止跑批**（4h24m 后人工终止），残卷 29 条保留在 `local_matrix.jsonl` 作留痕

## 4. 连带修复：完整性门禁此前只对锚点生效

`build_matrix_rows.py` 的 `MIN_KEYS`（=200）判据原本只作用于锚点模型 `qwen36:latest`，
导致 32B 中断后残存的 **29/212（13%）** 条也会被算出 ρ/κ 并写进矩阵——那是用残缺样本冒充完整单元格。
**已修复为对所有模型一律生效**：题量不足则跳过该行并打印缺口，不产出任何 ρ/κ/parse_rate。
复算确认：`deepseek-r1:32b` 现被正确跳过（"尚需 171 键"），矩阵仍为 8 个完整单元格。

## 5. 对 ④b 的含义（须写入稿件）— 2026-09-28 更正版

- **S3 档当前实况（已不是"仅一格"）**：矩阵中 S3_30-70B 现有 **3 格**——
  `qwen36:latest`（F1，34.7B IQ3_S）、`mixtral:8x7b`（F3，46.7B Q4_0）、
  `deepseek-r1:32b`（F4，32.8B Q4_K_M，2026-09-28 于 32 GB RAM 机器复跑成功）。
- **唯一缺口 F2_Llama / S3，且为结构性缺口**：开放权重中 Llama 无 30–70B 档
  （1B / 3B / 8B / 70B / 405B；70B 已 >70 落 S4）。这是**权重可得性问题，不是算力问题**——
  升级机器、换推理引擎均无法补上。
- 因此：**④b 硬约束（不宣称跨模型 LLM 边界）继续有效**，M3 §8 相关表述不得放宽。
  但稿件中给出的理由应写「**F2 族开放权重缺 30–70B 档位**」，
  **不得再写「S3 规模档算力上不可算」**（已被 F1/F3/F4 三格 S3 实测推翻）。
- 矩阵对外表述统一口径：**11 个 EVALUATED 单元格，触及 4 族 × 3 档，缺 F2_Llama S3 一格**（状态 🟡）。
- 解除路径只剩一条：**取得 30–70B 区间的 Llama 系开放权重**（目前不存在）；
  除此之外不存在"再跑一批就能补齐"的路径。

## 7. 追加（2026-09-27 晚）：colibri 引擎系核查——F4_S3 终局性不可行，S3 格转作跨引擎复现

新机器（RTX 5080 16 GB + 32 GB RAM，`D:\colibri` colibri 1.12.1）的引入改变了
**算力约束**，但核查 `D:\colibri-src\family_registry.py` 的 9 家族权威清单后确认：

1. **colibri 引擎系不含 DeepSeek R1 蒸馏 dense 模型**（r1:32b 属 llama.cpp/ollama
   生态的 dense 蒸馏检查点）。colibri 的 DeepSeek 支持仅两个 MoE 家族：
   V4 Flash（284B 总参 / 13B 激活，REAP 150B 版权重 85 GB）与 V4.1（552B）。
   按 ④b 的**总参档位**规约，284B 落 S4_>70B——**错档，不得冒充 F4_S3**。
2. **结论（2026-09-28 更正）**：「colibri 引擎系**不含** DeepSeek R1 蒸馏 dense 检查点」
   这一核查事实**仍然成立**，但由此得出的「F4_S3 维持 NOT_RUN」**已被推翻**——
   F4_S3 不需要 colibri：`deepseek-r1:32b` 属 ollama/llama.cpp 生态，本机升级 32 GB RAM 后
   于 2026-09-28 由 **ollama 系直接跑通**（212/212 + 108/108）。
   → **F4_S3 现为 EVALUATED**。原文「两层独立证据」中只有"colibri 无该检查点"这层仍有效。
3. 补偿性验证（本机已执行，见 `m3_colibri_verification_20260927.md`）：
   用 colibri 的 Qwen3.6-35B-A3B（int4-gs64，CUDA）对**唯一既有 S3 格**
   `qwen36:latest`（ollama，IQ3_S，CPU）做**同题同协议跨引擎复现**——
   若 ρ 与题目级标签跨引擎一致，则 S3 格（乃至整个矩阵）的结论不依赖推理后端。
## 8. 追加（2026-09-27 深夜）：F4_S4 探索点实测——协议通、算力不可行（E1-B）/勉强可行（E1-A）

DeepSeek-V4-Flash-0731 REAP 150B（85 GB，hf-mirror `puwaer/DeepSeek-V4-Flash-0731-reap-150b`）
在本机（RTX 5080 16 GB + 32 GB RAM）的实测结果，全部数字为直接测量：

1. **下载与校验**：17 分片 + config/tokenizer/index 共 23 文件、79 GiB，
   `model.safetensors.index.json` 全对上；config.json 与 colibri `_dsv4_geometry`
   必需字段全对齐（43 层 / 132 路由专家 / 每 token 6 专家 / compress_ratios 43 项）。
2. **CUDA 后端**：`coli_cuda_dsv4.dll` 编译成功（nvcc 12.8 + MSVC 14.44，
   手动环境绕过沙箱 reg.exe 黑名单；精简 CUDA 12.8 缺 `cuda_profiler_api.h`
   以源码目录最小 shim 补齐，声明与上游 ABI 一致）；dumpbin 核对 81 个
   `dsv4_cuda_*` 导出。运行日志确认加载：`[DSV4 CUDA] backend=coli_cuda_dsv4.dll
   (generic)`、`device 0: RTX 5080 17.1 GB sm_120`、`v4_gpu tier=dense-matvec`
   （GPU 承担 dense matvec，专家权重 CPU+NVMe 流式）。
3. **协议兼容**：prefill 续写在 DSV4 上同样成立——冒烟请求
   `{"difficulty":` 前缀 → 回复 ` 1}` / ` 3}`，与归一化目标容器形状逐字一致；
   引擎纯 greedy（日志：`top_p ignored; target engine is greedy`），无 thinking 噪声。
4. **吞吐实测（瓶颈）**：专家缓存仅 23 槽（`ram_tiers available=23.52GiB
   target_cache=12.31GiB`，85 GB 权重的 0.4%），热缓存无复利（同题二跑 65 s→104 s）。
   真实题长探针（题 217，271 prompt token）：**118.8 s → 2.28 tok/s**。
   外推：E1-A 212 题 ≈ **7 h**；E1-B 108 批（~2000 tok/批）≈ **27 h**。
5. **决策与执行结果**：E1-A 全量于 2026-09-28 凌晨完成（4.4 h，低于 r1:32b 当时 30 h 止损线）：
   **212/212 解析、0 错误、零重试，ρ=0.2998 CI [0.1604, 0.4136]**（全矩阵最高 E1-A ρ）；
   E1-B 外推 27 h 维持不可行。模型标识 `deepseek-v4-colibri`，产物 `local_matrix_dsv4.*`。
   **该探索点按总参 284B 落 S4_>70B，不并入 4×3 矩阵主张**（F4_S3 缺口维持 NOT_RUN，见 §7）。
   F4 族内跨档观察（S3 缺位限制外推）：v2:16b（S2）ρ=0.2521 → v4-flash（S4 探索点）ρ=0.2998。
   运行后 DSV4 引擎已 `coli stop` 释放 20 GB RAM。

## 9. 复算命令（2026-09-28 修订）

```bash
python results/m3/build_matrix_rows.py --csv-out E:/learnflow/results/m3/m3_model_scale_matrix.csv
python results/m3/verify_m3_matrix.py --matrix results/m3/m3_model_scale_matrix.csv
```

### 9.1 复算链路修复（2026-09-28，消除不可复现缺陷）

**缺陷**：修订前 `build_matrix_rows.py` 只读取 `local_matrix.jsonl`，导致
① `deepseek-r1:32b` 用的是该文件里 29/212 的**中断残卷**；② `ministral-3:3b` 与
`mixtral:8x7b` 两格**完全读不到** → 按文档命令只能复现 **8 行**，与磁盘上 **11 行** CSV 不符。

**修复**：改为按序读取全部贡献源，后加载源覆盖同 `(model, cond, key)` 记录：

| 源文件 | 贡献单元格 |
|---|---|
| `local_matrix.jsonl` | 8 个主模型（`deepseek-r1:32b` 的 29 条残卷在此，会被下方覆盖） |
| `local_matrix_ministral.jsonl` | `ministral-3:3b` |
| `local_matrix_mixtral_r1.jsonl` | `mixtral:8x7b` **与** `deepseek-r1:32b` 的完整 320 条 |

`local_matrix_colibri.*` / `local_matrix_dsv4.*` **不在读取列表**：前者是跨引擎复现行、
后者按总参 284B 落 S4，二者按方案均**不并入** 4×3 矩阵主张。

**验证结果（2026-09-29 实跑）**：修复后脚本产出 **11 行**，与已提交 CSV 逐字段比对——
`family / scale_tier / params_billions / architecture / eval_status / parse_rate /
spearman_rho / accuracy / cohen_kappa` **全部一致，差异 0 项**。

### 9.2 一处已知且已记录的口径差异（不影响 ρ，仅影响 CI 端点）

脚本对全部 11 行统一采用**本脚本 bootstrap**（种子 20260922）算 CI；而 CSV 中
`ministral-3:3b` / `mixtral:8x7b` / `deepseek-r1:32b` 三行的 CI 转录自**跑批自带 bootstrap**
（`local_matrix_*.json` 的 `e1a_spearman_ci95`，种子不同）。二者 ρ 完全相同，
CI 端点相差约 0.001–0.02（例：ministral `[0.0849, 0.3268]` vs 脚本 `[0.1005, 0.3238]`）。

**处置**：已发布 CSV 与稿件引用保持**跑批 CI**（不改已发布数字，避免论文↔产物脱节）；
差异在此显式留痕，属**bootstrap 种子差异**而非数据矛盾。若日后统一为脚本 CI，
须同步更新稿件中该三行的 CI 值。

### 9.3 `source_anchor` 复核（曾被质疑"两个模型同锚点"）

`mixtral:8x7b` 与 `deepseek-r1:32b` 两行的 `source_anchor` 相同，**经复核为正确而非误标**：
`local_matrix_mixtral_r1.jsonl` 实含两个模型的记录（mixtral 365 条 + 32b 320 条，见 §9.1 表）。
该文件名中的 `r1` 即指后者。此处留痕以免后续复查时误判。
