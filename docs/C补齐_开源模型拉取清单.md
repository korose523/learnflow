# C 补齐 · 本地 Ollama 开源权重模型拉取清单

> 目的：为 M3 稿 §8 ④b（审阅 §5.1）「投稿前须补齐 ≥3 模型族 × ≥3 规模标注矩阵」提供**可在本机 `ollama pull` 拿到**的开放权重模型清单，作为 `results/m3/m3_model_scale_matrix.csv` 其余 15 个 `NOT_EVALUATED` 单元格的候选来源。
> 关联只读文件：`docs/M3_模型族规模标注矩阵方案.md`（§2 族分类法 / §3 规模分层法）、`results/m3/verify_m3_matrix.py`、`results/m3/m3_model_scale_matrix.csv`、`results/m3/cloud_model_catalog.json`。
> 本文档**只新建、不改动任何既有文件**。
>
> 数据来源：**Ollama 官方模型库页面**（`https://ollama.com/library/<model>` 及 `/tags`）逐页核实，检索日期 2026-09-23。所有体积/标签均取自库页显示值；查不到的字段一律标「未核实」，不编造。

---

## §0 状态与结论摘要

**一句话结论**：云端托管端点路线不可行（两条硬证据见 §1），**唯一可行路线 = 本地 Ollama + 开放权重模型**；本清单给出可满足 ④b「≥3 族 × ≥3 档」的拉取方案——**最小方案 9 个模型 / 约 86 GB**（3 族 × 3 档），**完整方案 16 个模型 / 约 1005 GB**（4 族 × 4 档，其中 S4 档建议列为可选）。

- **族分类（§2，4 族）**：F1 Qwen（Alibaba）｜F2 Llama（Meta）｜F3 Mistral·Mixtral（Mistral AI）｜F4 DeepSeek（DeepSeek-AI）。
- **规模分层（§3，4 档）**：S1 `<7B`｜S2 `7–30B`｜S3 `30–70B`｜S4 `>70B`（MoE 按**总参数**归档）。
- **关键可行性确认**：④b 的审计锚点模型 `qwen36`（Qwen3.6-35B-A3B）对应 Ollama 官方库页 **`qwen3.6:35b`（23 GB，S3）**——该页确实存在（见 §6 缺口：A3B/IQ3_S 细节未核实）。
- **关键风险**：审计锚点用 **IQ3_S** 量化，而 Ollama 官方库对上述模型**只提供 `q4_K_M`（默认）/`q8_0`/`fp16` 等 K-quant**，**不含 IQ3_S**；IQ3_S 仅见于**第三方社区命名空间**（见 §4）。

---

## §1 排除依据：云端托管端点路线不可行（两条硬证据）

> 本节复述并指向既有证据产物 `results/m3/cloud_model_catalog.json`（`cloud.llm.models.list()` 只读快照，30 个模型），**不重复论证**，仅供清单自洽。

1. **平台公开模型目录里，Qwen / Llama / Mistral 三族一个都没有，且不公开任何参数量。**
   `cloud_model_catalog.json.preset_family_availability` 显示：`F1_Qwen` (probe `qwen`/`qwq`) → 0 命中；`F2_Llama` (probe `llama`/`meta-llama`) → 0 命中；`F3_Mistral` (probe `mistral`/`ministral`/`mixtral`/`magistral`/`codestral`) → 0 命中；只有 `F4_DeepSeek` 有 4 个命中。同文件 `parameter_count_disclosure` 记录 `n_enabled_models_with_explicit_param_count = 0`——**目录不公开参数量**，无法据目录填 S1–S4 档。

2. **该平台 SDK 的 `response_format` 只支持 `'json_object' | 'text'`，无 `json_schema` enum 约束解码**，无法复现已审计协议（E1-A 的 schema enum 约束解码）。证据同目录（`docs/M3_模型族规模标注矩阵方案.md` §5 补记亦记录该试点对本方案不构成补齐）。

**结论**：要同时满足「**开放权重 + 参数量公开可查 + 支持 `format` 语法约束解码**」，唯一路线为**本地 Ollama + 开源权重**。

---

## §2 推荐清单（族 / 档 / pull tag / 参数 / MoE / 量化 / 体积 / 依据 URL）

> 说明：体积为库页显示值（十进制 GB，Ollama 库页口径）。「默认量化」中，凡库页 `/tags` 明确列出 `-q4_K_M` 即标注确认，否则按 Ollama 惯例标 **Q4_K_M（惯例，未逐页确认）**。`参数` 为**总参数**（MoE 另记激活参数）。族归属依据 = **基座实验室 / 架构 lineage**。
> 「档」按 §3：S1 `<7B`、S2 `7–30B`、S3 `30–70B`、S4 `>70B`。

### F1 · Qwen 系（基座：Alibaba / Qwen 团队；lineage：Qwen3 dense + Qwen3 MoE）
依据 URL：https://ollama.com/library/qwen3 ｜ https://ollama.com/library/qwen2.5 ｜ https://ollama.com/library/qwen3.6

| 档 | pull tag | 总参数 | MoE（激活） | 默认量化 | 体积 | 备注 |
|---|---|---|---|---|---|---|
| S1 | `qwen3:0.6b` | 0.6B | dense | Q4_K_M（`/tags` 见 `-q4_K_M`） | 0.52 GB | 最小 |
| S1 | `qwen3:1.7b` | 1.7B | dense | Q4_K_M（`/tags` 见） | 1.4 GB | 建议 S1 代表 |
| S1 | `qwen3:4b` | 4B | dense | Q4_K_M | 2.5 GB | |
| S2 | `qwen3:8b` | 8B | dense | Q4_K_M（默认=`:latest`） | 5.2 GB | 建议 S2 代表 |
| S2 | `qwen3:14b` | 14B | dense | Q4_K_M（`/tags` 见） | 9.3 GB | |
| S2/S3⚠ | `qwen3:30b`（=`30b-a3b`） | 30B | **MoE（A3B）** | Q4_K_M | 19 GB | ⚠ 30B 落在 S2/S3 边界，建议避用 |
| S3 | `qwen3:32b` | 32B | dense | Q4_K_M（`/tags` 见） | 20 GB | 建议 S3 代表 |
| S3 | `qwen3.6:35b` | 35B | MoE（A3B，**未核实**） | **未核实**（库页仅列 tag，未标量化） | 23 GB | **④b 审计锚点族**（现 `qwen36` 落此档） |
| S2 | `qwen3.6:27b` | 27B | MoE（**未核实**） | 未核实 | 18 GB | |
| S4 | `qwen3:235b`（=`235b-a22b`） | 235B | **MoE（A22B）** | Q4_K_M | 142 GB | S4 巨模型 |
| S4 | `qwen2.5:72b` | 72B | dense | Q4_K_M（未逐页确认） | 47 GB | **S4 低成本替代** |

### F2 · Llama 系（基座：Meta；lineage：Llama 3.2 / 3.1 / 3.3 同家族 dense）
依据 URL：https://ollama.com/library/llama3.2 ｜ https://ollama.com/library/llama3.1 ｜ https://ollama.com/library/llama3.3

| 档 | pull tag | 总参数 | MoE | 默认量化 | 体积 | 备注 |
|---|---|---|---|---|---|---|
| S1 | `llama3.2:1b` | 1B | dense | Q4_K_M | 1.3 GB | 建议 S1 代表 |
| S1 | `llama3.2:3b` | 3B | dense | Q4_K_M（默认=`:latest`） | 2.0 GB | |
| S2 | `llama3.1:8b` | 8B | dense | Q4_K_M（默认=`:latest`） | 4.9 GB | 建议 S2 代表（Llama 无 3.2-8B） |
| S3 | `llama3.1:70b` | 70B | dense | Q4_K_M（未逐页确认） | 43 GB | S3 唯一选择（无 30–70B dense 中间档） |
| S3 | `llama3.3:70b` | 70B | dense | Q4_K_M（未逐页确认） | 43 GB | 与 3.1-70b 二选一 |
| S4 | `llama3.1:405b` | 405B | dense | Q4_K_M（未逐页确认） | 243 GB | S4 巨模型 |

> ⚠ **F2 无 30–70B 之间的模型**（Llama 3.2 只到 3B，Llama 3.3 起步 70B），故 F2×S3 只能取 70B（43 GB）。这是本清单中**不可回避的最大单体**。

### F3 · Mistral / Mixtral 系（基座：Mistral AI；lineage：Mistral dense + Mixtral MoE）
依据 URL：https://ollama.com/library/mistral ｜ https://ollama.com/library/ministral-3 ｜ https://ollama.com/library/mistral-nemo ｜ https://ollama.com/library/mistral-small ｜ https://ollama.com/library/mixtral

| 档 | pull tag | 总参数 | MoE（激活） | 默认量化 | 体积 | 备注 |
|---|---|---|---|---|---|---|
| S1 | `ministral-3:3b` | 3B | dense | Q4_K_M（未逐页确认） | 3.0 GB | ⚠ 需 **Ollama 0.13.1（pre-release）**；视觉模型 |
| S2 | `mistral:7b` | 7B | dense | Q4_K_M（默认=`:latest`） | 4.4 GB | 建议 S2 代表 |
| S2 | `mistral-nemo:12b` | 12B | dense | Q4_K_M（未逐页确认） | 7.1 GB | |
| S2 | `mistral-small:24b` | 24B | dense | Q4_K_M（默认=`:latest`） | 14 GB | |
| S3 | `mixtral:8x7b` | 46.7B | **MoE（约 13B 激活，近似）** | Q4_K_M（默认=`:latest`；某 tag 记 28 GB） | 26 GB | 建议 S3 代表 |
| S4 | `mixtral:8x22b` | 141B | **MoE（39B 激活）** | Q4_K_M（未逐页确认） | 80 GB | S4 巨模型 |

### F4 · DeepSeek 系（基座实验室：DeepSeek-AI）
依据 URL：https://ollama.com/library/deepseek-r1 ｜ https://ollama.com/library/deepseek-v2 ｜ https://ollama.com/library/deepseek-v3

> ⚠ **lineage 重要提醒**：`deepseek-r1` 的 S1–S3 尺寸档**并非 DeepSeek 自研架构**，而是**蒸馏自 Qwen2.5 / Llama3.1 / Llama3.3 的 dense 学生模型**（证据：HF `deepseek-ai/DeepSeek-R1-Distill-*` 模型卡，2025-01）：`R1-Distill-Qwen-1.5B/7B`（基座 Qwen2.5-Math）、`R1-Distill-Qwen-14B/32B`（基座 Qwen2.5）、`R1-Distill-Llama-8B`（基座 Llama-3.1-8B）、`R1-Distill-Llama-70B`（基座 Llama-3.3-70B）。**只有 671B（`deepseek-r1`/`deepseek-v3`）是 DeepSeek-V3 原生 MoE 架构**。若 F4 用小档 R1-Distill，则 F4 与 F1/F2 的 lineage 将重叠，削弱「族间差异 = 架构-训练侧」的论证力（§7 会展开）。

| 档 | pull tag | 总参数 | MoE（激活） | 默认量化 | 体积 | 依据 / lineage caveat |
|---|---|---|---|---|---|---|
| S1 | `deepseek-r1:1.5b` | 1.5B | dense | Q4_K_M（未逐页确认） | 1.1 GB | 基座 Qwen2.5-Math（**非 DeepSeek 架构**） |
| S2 | `deepseek-r1:7b` | 7B | dense | Q4_K_M（未逐页确认） | 4.7 GB | 基座 Qwen2.5-Math |
| S2 | `deepseek-r1:8b` | 8B | dense | Q4_K_M（默认=`:latest`） | 5.2 GB | 基座 **存疑**（Ollama readme 记 Qwen3-8B；HF 表记 Llama-3.1-8B） |
| S2 | `deepseek-r1:14b` | 14B | dense | Q4_K_M（未逐页确认） | 9.0 GB | 基座 Qwen2.5 |
| S3 | `deepseek-r1:32b` | 32B | dense | Q4_K_M（未逐页确认） | 20 GB | 基座 Qwen2.5 |
| S3 | `deepseek-r1:70b` | 70B | dense | Q4_K_M（未逐页确认） | 43 GB | 基座 Llama-3.3-70B |
| S2 | `deepseek-v2:16b` | 16B | **MoE** | Q4_K_M（未逐页确认） | 8.9 GB | **DeepSeek 原生 MoE**（S2 更纯的替代） |
| S4 | `deepseek-v2:236b` | 236B | **MoE** | Q4_K_M（未逐页确认） | 133 GB | DeepSeek 原生 MoE（**S4 低成本替代**） |
| S4 | `deepseek-r1:671b` | 671B | **MoE（37B 激活）** | Q4_K_M（未逐页确认） | 404 GB | DeepSeek-V3 原生 |
| S4 | `deepseek-v3:671b` | 671B | **MoE（37B 激活）** | Q4_K_M（未逐页确认） | 404 GB | DeepSeek-V3 原生 |

---

## §3 两套体积方案

> 体积按库页值直接相加（十进制 GB）。每族内部取**最小可满足档**的模型，以压总体积。

### 方案 A ·「最小满足 ≥3 族 × ≥3 档」= 3 族 × 3 档 = **9 个模型 / ≈ 86.3 GB**

选 **F1 + F3 + F4**（剔除 F2，因 F2 的 S3 只能是 70B=43 GB，最不划算）：

| 族 | S1 | S2 | S3 | 小计 |
|---|---|---|---|---|
| F1 Qwen | `qwen3:1.7b` 1.4 | `qwen3:8b` 5.2 | `qwen3:32b` 20.0 | **26.6** |
| F3 Mistral | `ministral-3:3b` 3.0 | `mistral:7b` 4.4 | `mixtral:8x7b` 26.0 | **33.4** |
| F4 DeepSeek | `deepseek-r1:1.5b` 1.1 | `deepseek-r1:8b` 5.2 | `deepseek-r1:32b` 20.0 | **26.3** |
| | | | **合计** | **≈ 86.3 GB** |

- 若 S1 改 `qwen3:0.6b`（0.52 GB）→ ≈ **85.4 GB**。
- 满足审阅「≥3 族 × ≥3 档」硬要求；**不含任何 70B+ 巨模型**（最大单体为 `mixtral:8x7b` 26 GB）。

### 方案 B ·「推荐 4 族 × 3 档」= **12 个模型 / ≈ 135.5 GB**

在方案 A 基础上加 F2：

| 族 | S1 | S2 | S3 | 小计 |
|---|---|---|---|---|
| F2 Llama | `llama3.2:1b` 1.3 | `llama3.1:8b` 4.9 | `llama3.1:70b` 43.0 | **49.2** |
| **合计** | | | | **≈ 135.5 GB** |

- 覆盖 §2 预设的**全部 4 族**（比审阅「≥3 族」更充分）；代价是引入 43 GB 的 `llama3.1:70b`。

### 方案 C ·「完整 4 族 × 4 档」= **16 个模型 / ≈ 1005 GB**（S4 建议可选）

在方案 B 基础上补 S4：

| S4 单元 | tag | 体积 |
|---|---|---|
| F1 S4 | `qwen3:235b` | 142 |
| F2 S4 | `llama3.1:405b` | 243 |
| F3 S4 | `mixtral:8x22b` | 80 |
| F4 S4 | `deepseek-r1:671b` | 404 |
| **S4 小计** | | **869** |
| **总计（含 B）** | | **≈ 1004.5 GB** |

- **S4 低成本变体**（若必须要 S4）：F1 用 `qwen2.5:72b`(47) 替 235b、F4 用 `deepseek-v2:236b`(133) 替 671b → S4 小计 ≈ 503 GB，总计 **≈ 638.5 GB**（F2 的 405b 无更廉价替代）。
- **建议**：S4 档属「体积过大」，标为**可选**；如 ④b 只需「≥3 族 × ≥3 档」，**方案 A/B 即可**，无需触碰 70B+。

---

## §4 量化一致性取舍（**不替作者决定**，仅列清权衡）

**事实基础**：
- 现有唯一 `EVALUATED` 单元格（F1×S3，`qwen36`）的量化是 **IQ3_S**（见 `M3_模型族规模标注矩阵方案.md` §1/§5）。
- 本清单所涉模型的 **Ollama 官方库页 `/tags`** 提供的量化档为：**`q4_K_M`（默认）/ `q8_0` / `fp16`**，部分（如 `llama3.2`）还提供 `q2_K…q6_K` 系列 K-quant；**均未见 IQ3_S**（逐页核实：`qwen3`、`llama3.2`、`mixtral` 等）。
- IQ3_S 在 Ollama 上**仅见于第三方社区命名空间**（如 `krith/qwen2.5-7b-instruct:IQ3_S`、`krith/llama-3.3-70b-instruct:IQ3_S`、`mannix/smallthinker:iq3_s`），**非官方库**，且**不保证每个模型都有对应 GGUF**。

**由此产生的两条可选路线（作者定夺）**：

| 路线 | 做法 | 优点 | 代价 / 风险 |
|---|---|---|---|
| **(a) 统一到官方默认量化**（`q4_K_M`，或统一 `q8_0`） | 全部用 `ollama pull` 官方 tag | 完全可复现（纯官方库）；族/档之间**量化一致**；无需第三方源 | **与审计锚点 `qwen36`（IQ3_S）不一致**——锚点单元格与其余单元格存在量化错配，可能引入混淆 |
| **(b) 统一到 `IQ3_S`** | 用第三方社区 GGUF 或 `ollama create --quantize iq3_s` 从源权重自建 | 与审计锚点量化一致，矩阵内部同质 | **非纯 `ollama pull`**（需第三方源/自建，可用性不保证）；增加工程与校验成本；有供应链/许可不确定性 |

**我的判断（供参考，非决定）**：
1. **可比性 > 与单一锚点字面一致**。跨族/跨档的难度标注，若各族量化不同，会把「量化噪声」混入「族 × 档」效应——这也是审阅强调「同一套已通过审计的协议」的同一逻辑。**无论选哪条，矩阵内部必须量化统一**。
2. 若坚持「锚点单元格不动」，则需接受「锚点 = IQ3_S、其余 = 统一 X」的**非完全同质**并**显式声明**，或在补跑时把 `qwen36` 也**重跑为统一量化**（推荐后者以彻底消除错配，但会改动既有 EVALUATED 数值，须作者确认）。
3. 另：**MoE 按总参数归档**（§3）已定，但注意 MoE 与 dense 的**量化后体积/精度退化曲线不同**（如 IQ3_S 对 MoE 更敏感），同量化不等于同退化——可在 `reliability_verdict` 里如实记录。

> 以上**不改变** `m3_model_scale_matrix.csv` 的 schema（§4：EVALUATED 带 `spearman_rho` + 配对 bootstrap 95% CI，NOT_EVALUATED 数值留空）。

---

## §5 执行步骤

### 5.1 拉取命令（示例：方案 B「4 族 × 3 档」）

```bash
# F1 Qwen
ollama pull qwen3:1.7b
ollama pull qwen3:8b
ollama pull qwen3:32b

# F2 Llama
ollama pull llama3.2:1b
ollama pull llama3.1:8b
ollama pull llama3.1:70b

# F3 Mistral
ollama pull ministral-3:3b        # 需 Ollama >= 0.13.1（pre-release）
ollama pull mistral:7b
ollama pull mixtral:8x7b

# F4 DeepSeek
ollama pull deepseek-r1:1.5b
ollama pull deepseek-r1:8b
ollama pull deepseek-r1:32b
```

> 若要求统一量化，在 tag 后追加量化后缀（官方支持的档），例如 `ollama pull qwen3:8b-q8_0`、`ollama pull qwen3:32b-q8_0`。**注意 IQ3_S 无官方 tag**，见 §4。

### 5.2 校验与评估（命令占位）

```bash
# 1) 确认已拉取模型
ollama list

# 2) 矩阵结构门禁（骨架校验，纯标准库）
python results/m3/verify_m3_matrix.py

# 3) 本机多模型标注评估（local driver；脚本由本地驱动任务产出，路径为约定占位）
python results/m3/local_matrix_e1ab.py \
  --models qwen3:1.7b,qwen3:8b,qwen3:32b,llama3.2:1b,llama3.1:8b,llama3.1:70b,ministral-3:3b,mistral:7b,mixtral:8x7b,deepseek-r1:1.5b,deepseek-r1:8b,deepseek-r1:32b \
  --datasets DBE-KT22,XES3G5M \
  --protocol E1-A,E1-B

# 4) 补全 m3_model_scale_matrix.csv 后再次门禁
python results/m3/verify_m3_matrix.py --matrix results/m3/m3_model_scale_matrix.csv
```

> ⚠ `results/m3/local_matrix_e1ab.py` 在本文档撰写时**尚不存在**（属本地驱动任务交付物），此处仅为**约定路径占位**，不得据此认为脚本已就绪。

---

## §6 诚实缺口与已用检索式

### 6.1 未核实字段清单（一律不编造）

| 项 | 状态 |
|---|---|
| `qwen3.6:27b` / `qwen3.6:35b` 是否 **A3B（MoE）** | **未核实**（库页仅显示 `27b`/`35b` tag 与体积，未标 MoE/激活参数） |
| `qwen3.6` 系列的**默认量化 / 是否提供 IQ3_S** | **未核实**（库页未列量化档；仅知 `35b`=23 GB） |
| `qwen36`（审计锚点）是否等价于 `qwen3.6:35b` 且确为 IQ3_S | **未核实**（M3 方案文记 A3B+IQ3_S，但库页无法证实） |
| `deepseek-r1:8b` 的基座到底是 **Qwen3-8B 还是 Llama-3.1-8B** | **来源冲突**（Ollama readme 记 Qwen3；HF 模型卡表记 Llama-3.1），未判定 |
| `mixtral:8x7b` 默认量化 | 惯例判为 **Q4_K_M**（体积 26 GB 与参数 46.7B 吻合，另见某 tag 记 28 GB），**库页 /tags 未完整渲染确认** |
| `mixtral:8x7b` 激活参数「约 13B」 | **近似值**，取自二手来源，非官方库页 |
| 多个模型的默认量化（标「未逐页确认」者） | 按 Ollama 惯例 **Q4_K_M**，未逐页从 `/tags` 证实 |
| `ministral-3` 可用性 | 需 **Ollama ≥ 0.13.1（pre-release）**，本机版本未在本任务核实 |

### 6.2 已用检索式（WebSearch / WebFetch）

- WebFetch `https://ollama.com/library/qwen3`、`/qwen3/tags`、`/qwen2.5`、`/qwen3.6`
- WebFetch `https://ollama.com/library/llama3.2`、`/llama3.2/tags`、`/llama3.1`、`/llama3.1/tags`、`/llama3.3`
- WebFetch `https://ollama.com/library/mistral`、`/ministral-3`、`/mistral-nemo`、`/mistral-small`、`/mixtral`、`/mixtral/tags`
- WebFetch `https://ollama.com/library/deepseek-r1`、`/deepseek-r1/tags`、`/deepseek-v2`、`/deepseek-v3`
- WebFetch `https://ollama.com/library/gemma3`（旁证他族，未纳入本清单）
- WebSearch `ollama library IQ3_S quantization tag available`
- WebSearch `ollama mixtral 8x7b quantization default q4_K_M size`
- WebSearch `DeepSeek-R1-Distill base model Qwen2.5 Llama3 lineage 1.5b 7b 8b 14b 32b 70b`

### 6.3 来源池（供主理人并入全局来源池）

1. [Ollama · qwen3 模型库页](https://ollama.com/library/qwen3) — Qwen3 dense+MoE，tags 0.6b–235b，含 q4_K_M/q8_0/fp16 量化档
2. [Ollama · qwen3 tags](https://ollama.com/library/qwen3/tags) — 量化档清单（未见 IQ3_S）
3. [Ollama · qwen3.6 模型库页](https://ollama.com/library/qwen3.6) — 审计锚点族；tags 27b(18GB)/35b(23GB)/mlx
4. [Ollama · qwen2.5 模型库页](https://ollama.com/library/qwen2.5) — 0.5b–72b（S4 低成本替代 72b=47GB）
5. [Ollama · llama3.2 模型库页](https://ollama.com/library/llama3.2) — 1b/3b（S1）
6. [Ollama · llama3.1 模型库页](https://ollama.com/library/llama3.1) — 8b/70b/405b
7. [Ollama · llama3.3 模型库页](https://ollama.com/library/llama3.3) — 70b
8. [Ollama · mistral 模型库页](https://ollama.com/library/mistral) — 7b v0.3
9. [Ollama · ministral-3 模型库页](https://ollama.com/library/ministral-3) — 3b/8b/14b（S1，需 pre-release）
10. [Ollama · mistral-nemo 模型库页](https://ollama.com/library/mistral-nemo) — 12b
11. [Ollama · mistral-small 模型库页](https://ollama.com/library/mistral-small) — 22b/24b
12. [Ollama · mixtral 模型库页](https://ollama.com/library/mixtral) — 8x7b(46.7B)/8x22b(141B)
13. [Ollama · deepseek-r1 模型库页](https://ollama.com/library/deepseek-r1) — 1.5b–671b，含蒸馏 lineage 说明
14. [Ollama · deepseek-v2 模型库页](https://ollama.com/library/deepseek-v2) — 16b/236b（原生 MoE）
15. [Ollama · deepseek-v3 模型库页](https://ollama.com/library/deepseek-v3) — 671b（原生 MoE，37B 激活）
16. [HF · DeepSeek-R1-Distill-Qwen-14B 模型卡提交](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/commit/c79f47acaf303faabb7133b4b7b76f24231f2c8d) — R1-Distill 六款基座对照表（lineage 证据）
17. [AI Wiki · DeepSeek-R1-Distill](https://aiwiki.ai/wiki/deepseek_r1_distill) — 蒸馏基座与参数规模对照
18. [Ollama 社区 · krith/qwen2.5-7b-instruct:IQ3_S](https://ollama.com/krith/qwen2.5-7b-instruct:IQ3_S) — IQ3_S 仅见于第三方命名空间（量化一致性证据）
19. [Ollama 社区 · krith/llama-3.3-70b-instruct:IQ3_S](https://ollama.com/krith/llama-3.3-70b-instruct:IQ3_S) — 同上
20. [ComputingForGeeks · Ollama Models Cheat Sheet](https://computingforgeeks.com/ollama-models-cheat-sheet/) — Ollama 默认量化=Q4_K_M 的旁证

---

## §7 与 ④b 的对应关系（逐条）

| ④b / 方案要求 | 本清单是否补齐 | 说明 |
|---|---|---|
| **≥3 模型族** | ✅ 满足（提供 **4 族**：F1 Qwen / F2 Llama / F3 Mistral / F4 DeepSeek） | 族按基座实验室/lineage 划分，与 §2 分类法一致 |
| **≥3 参数规模档** | ✅ 满足（提供 S1/S2/S3，且给出 S4 可选） | 每族给出 ≥3 个不同档的可拉取模型 |
| **参数量公开可查** | ✅ 满足 | 各 tag 参数量取自库页/模型卡 |
| **同一批题目（DBE-212/XES-120）** | ⛔ **本清单不补齐** | 需本地驱动脚本按同批题目跑；清单只保证模型可得 |
| **同一套已通过审计的协议（E1-A/E1-B）** | ⛔ **本清单不补齐** | 需 `local_matrix_e1ab.py`（占位）复现协议；Ollama 支持 `format` 语法约束解码是本地路线的可行性前提 |
| **EVALUATED 单元格带 `spearman_rho` + bootstrap 95% CI** | ⛔ **本清单不补齐** | 需真实评估后回填；清单不产生任何 ρ/CI |
| **量化与审计锚点（IQ3_S）一致** | ⚠ **部分** | 官方库无 IQ3_S（§4）；须作者决断统一量化路线 |
| **F4 lineage 纯度** | ⚠ **风险** | R1-Distill 小档实为 Qwen/Llama 系（§2 F4 注）；若要求「族间差异=架构侧」，F4 建议改用 `deepseek-v2:16b`/`deepseek-v3:671b` 原生 MoE |
| **不修改既有文件** | ✅ 满足 | 本文档为唯一新建文件；方案稿 / 稿件 / CSV 均只读 |

> **净结论**：本清单**解决了 ④b 的「模型可得性」前置**（开放权重、参数量公开、可由 `ollama pull` 获取、支持约束解码），但**不构成 ④b 的完成**——同批题目重跑、同协议复现、ρ+CI 实算，仍须本地驱动任务在本文档列出的模型上执行。在矩阵补全前，M3 稿 §8 ④b / ⑥「不宣称跨模型 LLM 边界」硬约束**仍然成立**。

---

*本文档由课题研究员谭溯源（c-openweight-list）产出，仅新建，未改动任何既有文件。所有体积/标签均经 Ollama 官方库页核实，未核实项已在 §6 显式标注。*
