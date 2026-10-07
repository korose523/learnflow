# ④b 矩阵 · colibri 跨引擎验证：F1_Qwen S3 格复现 + F4 终局核查（2026-09-27）

> ## ⚠ 状态更新（2026-09-28）——先读这一段
>
> 本文件原结论含「**F4_S3 维持 NOT_RUN**」与「**8 格矩阵原样**」两处表述，**均已过期**，现更正：
>
> 1. **F4_DeepSeek / S3 已 EVALUATED**：`deepseek-r1:32b` 由 **ollama 系**在本机升级 32 GB RAM 后
>    于 2026-09-28 跑通（E1-A 212/212、ρ=0.0891、E1-B 108/108）。本文件 §5 关于
>    「colibri 引擎系无 DeepSeek R1 蒸馏 dense 检查点」的**核查事实仍成立**，
>    但由此推出的「F4_S3 = NOT_RUN」**已被推翻**（F4_S3 本就不依赖 colibri）。
> 2. **矩阵现为 11 个 EVALUATED 单元格**（触及 4 族 × 3 档），不是 8 格；
>    唯一缺口为 **F2_Llama 的 S3 档**（开放权重无 30–70B，属结构性问题）。
>    colibri 行与 dsv4 行仍**未并入**主矩阵，此点不变。
> 3. **数字勘误**：§4.1 / §4.2 中 colibri E1-B ρ 原记 `0.2816`，与产物
>    `cross_engine_compare.json` 的 `0.2793` 不符，已按产物更正（差 0.0023）。
>
> 相关更正同步见：`m3_s3_infeasibility_20260927.md` 篇首状态更新。

结论一句话（原文）：**同基座 Qwen3.6-35B-A3B 换推理栈（ollama IQ3_S/CPU → colibri int4-gs64/CUDA）
后，S3 格结论完全复现——ρ 0.1744→0.1897（CI 几乎重叠）、两两方向一致率 99.5%、BT 分数
相关 0.76；DeepSeek V4 Flash（S4_>70B）作为超档探索点已启动全量标注。**
（原文此处另写「F4_S3 维持 NOT_RUN」，见上方更正。）全部数字由脚本从产物算出，未经手工转录。

## 1. 背景与任务

`m3_s3_infeasibility_20260927.md` 记录了旧机器（15.8 GB RAM、无 GPU）上
`deepseek-r1:32b` 的 F4_S3 缺口。本机（RTX 5080 16 GB + 32 GB RAM）引入 colibri 1.12.1
推理引擎后，本轮回答三个问题：

1. 唯一既有 S3 格 `qwen36:latest` 的结论**是否依赖推理后端**（跨引擎复现性）；
2. colibri 引擎系**能否补 F4_S3**（终局核查）；
3. colibri 独有的 DeepSeek V4 引擎能否给出 **F4 超档参考点**（S4 探索，不并入 4×3 主张）。

## 2. 数据链修复（前置条件，本机原缺题库）

本机仓库不含 `data/`（旧机器专有）。题面文本从 HuggingFace 镜像
`Unggi/dbe-kt22_raw_data`（ADA Dataverse DOI 10.26193/6DZWOH 的镜像，本机网络不可达
ADA 域名）恢复至 `data/dbe_kt22/csv/Questions.csv`，并做**三重完整性校验**
（`results/m3/verify_dbe_questions.py`，输出 `verify_dbe_questions_out.txt`）：

- [1] 212 行 ID 集合与 `difficulty_cache.npz` 的 `D_keep` 完全一致：PASS
- [2] `difficulty` 列与 `D_y` 逐 ID 一致：PASS
- [3] 与 `local_matrix.jsonl` 中 **9 个模型** E1A 记录自带的 expert 字段逐 ID 一致：PASS
- 文本非空 212/212

## 3. 传输层适配（协议零改动）

适配器 `results/m3/local_matrix_colibri.py` 经 importlib **直接复用**
`local_matrix_e1ab.py` 的提示词/schema/统计函数对象（单一事实来源），只替换传输层：

| 项 | ollama 侧（旧机器） | colibri 侧（本机） |
|---|---|---|
| API | `:11434/api/generate` + `format=schema` 约束解码 | `:8000/v1/chat/completions` |
| 输出约束 | 语法强制（输出恰为 schema 容器） | **prefill 续写等效约束**（见下） |
| 量化 | IQ3_S（34.7B 总参） | int4-gs64（同基座 35B） |
| 硬件 | CPU-only | CUDA sm_120（coli_cuda.dll） |

**prefill 续写的等效性论证**：colibri qwen36 引擎子进程不支持 grammar payload
（`capabilities.grammar_payload=False`，`response_format` 一律 HTTP 400，实测），
但网关支持尾随 assistant 续写（`resolve_generation_prompt` 默认开启，
`openai_server.py:2503-2523`；qwen 渲染分支 `:1444-1453` 以预闭合 `<think></think>`
+ 前缀文本渲染开放回合）。把 schema 容器前缀（如 `{"difficulty":`）作为 assistant
前缀，greedy 续写标签的条件分布 P(label | prompt, 前缀) 与 ollama 约束解码**同条件**
（被语法强制生成的容器 token 不改变标签条件分布）。`stop=["\n"]` 与容器归一化
（`_normalize_prefill_completion`：E1-A 取前缀后首个数字串、E1-B 截首个 `]` 补 `}`）
把自由解码的多余输出恢复为约束解码本会产出的精确容器形状；标签 token 逐字保留。

**引擎稳定性问题（诚实记录）**：qwen36 引擎在部分长 prefill 批量请求上确定性
HTTP 500（同批重试 2-3 次仍失败，跨进程重启复现），致 E1-B 最终覆盖 81/108=75.0%
（< 90% 门线）。失败模式：空响应 11 批（500）、模型自造短/嵌套数组 16 批
（greedy 确定性输出）、其他 1 批。E1-B 的 ρ 按 `build_matrix_rows.py` 规约**不得与
满批单元格并列比较**（门禁 JSON：`protocol_usability_colibri.json`）。

## 4. 结果（全部数字来自产物 JSON，脚本算出）

### 4.1 colibri 侧单元格（`local_matrix_colibri.json`）

| 条件 | 数值 |
|---|---|
| E1-A 解析 | **212/212（100%）**，无重试 |
| E1-A ρ(listwise) | **0.1897**，95% CI [0.0580, 0.3024]（配对 bootstrap，同审计种子）——**CI 不含零** |
| E1-A ρ(none_as_zero) | 0.1897（与 listwise 同，因无解析失败） |
| E1-A accuracy / κ | 0.4528 / 0.0867（加权 κ=0.1201）；分布 1:26.4% 2:57.1% 3:16.5%（熵 0.838，非塌缩） |
| E1-B 覆盖 | **81/108（75.0%）**（引擎 500 确定性失败 27 批，见 §3） |
| E1-B ρ | **0.2793**，95% CI [0.1071, 0.3750]（覆盖率门线未达，不并列比较）<br>*（2026-09-28 勘误：原记 0.2816 / CI[0.1145, 0.3727]，与产物 `cross_engine_compare.json` 的 0.2793 / [0.1071, 0.375] 不符，已按产物更正）* |

### 4.2 跨引擎复现性（`cross_engine_compare.json`，脚本 `compare_cross_engine.py`）

| 指标 | 数值 | 解读 |
|---|---|---|
| ρ vs 专家（ollama） | 0.1744，CI [0.0573, 0.2925] | 原 S3 格（JSONL 直算） |
| ρ vs 专家（colibri） | 0.1897，CI [0.0580, 0.3024] | 复现值，**两 CI 几乎重叠** |
| 引擎间标签一致率 | 65.1%（138/212 对角） | 分歧集中于相邻档（1↔2），1↔3 仅 6 题 |
| 引擎间 Cohen's κ | 0.3772 | 3 级主观任务的典型跨引擎一致度 |
| 引擎间 Spearman | 0.528 | 秩信号跨引擎保持 |
| **E1-B 方向一致率** | **791/795 = 99.5%**（仅 4 对矛盾） | 两两约束层面几乎完全复现 |
| BT 分数 Spearman | 0.7612 | 排序聚合高度一致 |
| E1-B ρ vs 专家 | ollama 0.2660 vs colibri **0.2793** | 两种栈同向、幅度一致 |

**判定：F1_Qwen S3 格的矩阵结论（小而显著的正对齐、幅度 ~0.17-0.19）不依赖推理
后端**——换引擎、换量化、换解码通道、换硬件，ρ 复现、排序几乎逐对复现。

### 4.3 协议可用性门禁（`_colibri_matrix_gate.py` → `protocol_usability_colibri.json`）

- E1-A：**usable**（解析 100% ≥ 90%；归一化熵 0.838 ≥ 0.50；众数占比 57.1% ≤ 80%）
- E1-B：**unusable-coverage**（75% < 90%）→ ρ(E1-B) 不得与满批单元格并列比较；
  E1-A 判定不受影响。

### 4.4 矩阵行（`local_matrix_colibri_rows.csv`，dump-matrix 生成）

```
qwen3.6-colibri,Qwen,S3_30-70B,35,MoE,EVALUATED,DBE-KT22,
E1-A(schema enum+锚定)/E1-B(枚举数组+BT),1.0,0.1897,0.4528,0.0867,...
```

该行作为 S3 格的**跨引擎复现行**（稳健性附录），**不改变主矩阵结构**。
*（2026-09-28 更正：主矩阵现为 **11 格**，原写「8 格」为旧快照；colibri 行与 dsv4 行
仍独立成文件，未并入主矩阵，此点不变。）*

## 5. F4_DeepSeek S3：两套引擎系的终局核查

1. ollama 系：`deepseek-r1:32b`（32.8B dense Q4_K_M = 19 GB）> 15.8 GB RAM → 不可行
   （`m3_s3_infeasibility_20260927.md` §1-3）。
2. colibri 系（本轮核查 `family_registry.py` 9 家族清单）：**不含 DeepSeek R1 蒸馏
   dense 检查点**；DeepSeek 支持仅 V4 Flash（284B/13B MoE）与 V4.1（552B），
   按总参档位均 > 70B，落 S4——错档不可比。
3. **结论（2026-09-28 更正）**：colibri 系无该检查点的事实成立，但「F4_S3 NOT_RUN」**已推翻**——
   F4_S3 由 ollama 系在 32 GB RAM 机器上完成（`deepseek-r1:32b`，2026-09-28），
   **F4_S3 现为 EVALUATED**。当前矩阵的**唯一缺口是 F2_Llama / S3**
   （开放权重无 30–70B 档，结构性不可补）。

## 6. DeepSeek V4 Flash（S4_>70B）探索点：已启动

- 权重：`puwaer/DeepSeek-V4-Flash-0731-reap-150b`（REAP 150B 版，85 GB，17 分片，
  hf-mirror 44.5 min 下完，`model.safetensors.index.json` 校验 17/17 文件齐全）→
  `D:\colibri\models\dsv4-reap150b\`。
- CUDA 后端：`coli_cuda_dsv4.dll`（generic sm_80+）已按 Makefile `cuda-dsv4-dll` 配方
  构建成功（nvcc 12.8 + MSVC 14.44.35207，`-ccbin` 显式指定绕开注册表发现；
  构建脚本 `D:\colibri-src\c\build_dsv4_cuda.bat`，产物已部署 `D:\colibri\app\`，
  运行时依赖 `cublasLt64_12.dll` 一并部署）。
- 冒烟（`_smoke` 产物已清理，证据见运行日志）：E1-A 3/3 + 温态探针 3/3，
  **全部输出干净 `{"difficulty": N}` 容器**，prefill 续写在 v4 引擎同样成立。
- 实测吞吐：温态 **58-144 s/题**（NVMe 专家流式为瓶颈）→ E1-A 全量约 5-6 h、
  加 E1-B 共 13-18 h。
- **E1-A 全量已完成（2026-09-28 凌晨 01:49，4.4 h）**：**212/212 解析、0 错误、零重试**，
  **ρ(listwise)=0.2998，95% CI [0.1604, 0.4136]**（配对 bootstrap 同审计种子）——CI 远离零，
  为全矩阵最高的 E1-A ρ。E1-B 未跑（外推 27 h，记不可行）。产物：`local_matrix_dsv4.{jsonl,json}`
  与 `local_matrix_dsv4_rows.csv`（EVALUATED 行）。
- **F4 族内跨档观察（2026-09-28 更正：S3 已补齐，原文"随规模上升"不成立）**：
  F4 三档现为 `deepseek-v2:16b`（S2）ρ=**0.2521**（CI 不含零·显著）→
  `deepseek-r1:32b`（S3）ρ=**0.0891**（CI [-0.0367, 0.1698] **含零·不显著**，且严重等级塌缩：
  众数占比 98.1%、归一化熵 0.085 → E1-A 判 unusable）→
  `deepseek-v4-flash`（S4 探索点）ρ=**0.2998**（CI 不含零·显著）。
  → **族内并非单调随规模上升**：S3 反而是三档中最弱且不显著的一档。
- **因此不得作"规模越大越对齐"的主张**。三点额外限定必须同时写明：
  (a) 三档是**三个不同的模型线**（DeepSeek-V2 / R1-Distill-Qwen / V4-Flash），
      族内跨档对比**混杂了架构差异**，不是纯粹的规模效应；
  (b) S3 的 `deepseek-r1:32b` 为 Qwen2 蒸馏骨架，与 F1_Qwen 共享主干，族间独立性受限；
  (c) S4 点为超档探索参考，**按总参 284B 落 S4**，不并入 4×3 矩阵主张、不冒充 F4_S3。

## 7. 产物与复算命令

| 产物 | 说明 |
|---|---|
| `data/dbe_kt22/csv/Questions.csv` | 题库（三重校验 PASS，`verify_dbe_questions_out.txt`） |
| `results/m3/local_matrix_colibri.py` | 传输层适配器（协议/统计零改动） |
| `results/m3/local_matrix_colibri.jsonl/.json` | colibri qwen3.6 标注记录 + 汇总 |
| `results/m3/local_matrix_colibri_rows.csv` | 矩阵复现行（EVALUATED） |
| `results/m3/protocol_usability_colibri.json` | 三重门禁判定 |
| `results/m3/compare_cross_engine.py` → `cross_engine_compare.json` | 跨引擎对比（全部数字） |
| `results/m3/_colibri_matrix_gate.py` | 门禁猴补丁 runner（builder 零改动） |
| `results/m3/_colibri_full_run.log` / `_colibri_resume_pass2.log` | 运行日志（含 500 明细） |

```bash
# 完整复算链
python results/m3/verify_dbe_questions.py
python results/m3/local_matrix_colibri.py --selftest
python results/m3/compare_cross_engine.py
python results/m3/local_matrix_colibri.py --dump-matrix --out results/m3/local_matrix_colibri
python results/m3/_colibri_matrix_gate.py
```

## 8. 纪律声明

- 缺失/失败测量一律如实记录（E1-B 27 批失败逐批留痕于 JSONL，含 retry 标记）；
- 未修改任何审计参考实现（`llm_labeling_v2.py`/`o13_llm_protocol_audit.py`/
  `local_matrix_e1ab.py`/`build_matrix_rows.py` 均经 importlib 复用，零改动）；
- 未改动 `m3_model_scale_matrix.csv`（本轮 colibri 验证未并入主矩阵；该文件现为 **11 格**，
  原「8 格原样」为旧快照表述，已更正）；colibri 行独立成文件；
- 所有 ρ/CI/κ 由脚本从 JSONL 产物直算，未经手工转录。
