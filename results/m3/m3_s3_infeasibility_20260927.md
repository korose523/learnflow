# ④b 矩阵 · S3 规模档在本机不可扩展的实测证据（2026-09-27）

结论一句话：**本机物理内存小于 30B 级模型的权重体积，S3（30–70B）档每格需 ≥30 小时且持续超时，
因此 ④b 的「≥3 族 × ≥3 规模全覆盖」无法在本机补齐。** 以下全部为实测值，不推断、不估算自网页。

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

## 5. 对 ④b 的含义（须写入稿件）

- 现有 S3 单元格**仅 `qwen36:latest`（34.7B，IQ3_S）一格**，属 F1_Qwen；
  该模型之所以能跑通，是因为 IQ3_S 量化后体积**小于**本次的 19 GB Q4_K_M。
- F2_Llama 在开放权重中**无 30–70B 档**（只有 8B / 70.6B，后者落 S4）；
  F3_Mistral 无 <7B 档；F4_DeepSeek 的 S3 档在本机不可算（本文件证据）。
- 因此：**④b 硬约束（不宣称跨模型 LLM 边界）继续有效**，M3 §8 相关表述不得放宽。
- 解除路径只有两条：① 换用显存/内存充足的机器（≥64 GB RAM 或 ≥24 GB VRAM）跑满矩阵；
  ② 改用可获取的低比特 30–70B 权重（如 Q2_K/IQ 系列，体积需 < 15 GB）。

## 7. 追加（2026-09-27 晚）：colibri 引擎系核查——F4_S3 终局性不可行，S3 格转作跨引擎复现

新机器（RTX 5080 16 GB + 32 GB RAM，`D:\colibri` colibri 1.12.1）的引入改变了
**算力约束**，但核查 `D:\colibri-src\family_registry.py` 的 9 家族权威清单后确认：

1. **colibri 引擎系不含 DeepSeek R1 蒸馏 dense 模型**（r1:32b 属 llama.cpp/ollama
   生态的 dense 蒸馏检查点）。colibri 的 DeepSeek 支持仅两个 MoE 家族：
   V4 Flash（284B 总参 / 13B 激活，REAP 150B 版权重 85 GB）与 V4.1（552B）。
   按 ④b 的**总参档位**规约，284B 落 S4_>70B——**错档，不得冒充 F4_S3**。
2. 结论：F4_DeepSeek S3 格维持 **NOT_RUN**，且理由从「本机算力不足」升级为
   「**第二推理引擎系（colibri）亦无可比检查点**」——两层独立证据。
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

## 6. 复算命令

```bash
python results/m3/build_matrix_rows.py --csv-out E:/learnflow/results/m3/m3_model_scale_matrix.csv
python results/m3/verify_m3_matrix.py --matrix results/m3/m3_model_scale_matrix.csv
```
