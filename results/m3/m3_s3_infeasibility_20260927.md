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

## 6. 复算命令

```bash
python results/m3/build_matrix_rows.py --csv-out E:/learnflow/results/m3/m3_model_scale_matrix.csv
python results/m3/verify_m3_matrix.py --matrix results/m3/m3_model_scale_matrix.csv
```
