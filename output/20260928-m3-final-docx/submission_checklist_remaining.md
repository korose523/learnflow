# M3 投稿收尾清单（项 8/9/11 · 项 21 · 项 16）核验与合规报告

- 生成时间：2026-09-28（续 Stage 3 之后）
- 关联稿件：`docs/M3_有序难度决策与大模型先验边界_完整稿.md`
- 关联终稿：`stage3/M3_有序难度决策与大模型先验边界_终稿.docx`（已含 项 8 订正后重导）

---

## 一、数字一致性核验（项 8 / 项 9 / 项 11）

### 项 9 — 表 3 有序难度转移（vs `results/code/junyi_m3_results.json` → `ordered_difficulty_transitions`）
逐值一致 ✅（9/9 行，样本量 + 成功率全匹配）

| 转移 | JSON n | 稿件表 3 n | JSON 成功率 | 稿件成功率 | 结论 |
|---|---:|---:|---:|---:|:--:|
| normal→easy | 1,885,528 | 1,885,528 | 0.7314 | 0.7314 | ✅ |
| easy→easy | 7,997,849 | 7,997,849 | 0.7335 | 0.7335 | ✅ |
| normal→normal | 880,896 | 880,896 | 0.6118 | 0.6118 | ✅ |
| easy→normal | 1,886,468 | 1,886,468 | 0.6407 | 0.6407 | ✅ |
| normal→hard | 311,261 | 311,261 | 0.6005 | 0.6005 | ✅ |
| hard→easy | 795,667 | 795,667 | 0.7534 | 0.7534 | ✅ |
| hard→normal | 310,027 | 310,027 | 0.6479 | 0.6479 | ✅ |
| easy→hard | 794,051 | 794,051 | 0.6302 | 0.6302 | ✅ |
| hard→hard | 270,934 | 270,934 | 0.5945 | 0.5945 | ✅ |

### 项 8 — 表 4 真实臂策略（vs `junyi_m3_results.json` v1 + `junyi_m3_v2_results.json` v2）
v2（11 策略，均值±SE）逐值一致 ✅（11/11）
v1（8 策略）**7/8 一致，已订正 1 处**：`all_hard` 稿件原写 `0.6420`，源 JSON 为 `0.6421`，差 0.0001（第 4 位小数）。**已按稿件自身"文档数字须与代码/JSON 一致"红线，将稿件订正为 `0.6421` 并重导 docx**。

| 策略 | v1 稿件 | v1 JSON | v2 稿件 | v2 JSON | 结论 |
|---|---:|---:|---:|---:|:--:|
| all_easy | 0.7420 | 0.742 | 0.7434±0.0070 | 0.7434±0.007 | ✅ |
| flow_zone | — | — | 0.7119±0.0064 | 0.7119±0.0064 | ✅ |
| llm_correct | 0.7060 | 0.706 | 0.7023±0.0065 | 0.7023±0.0065 | ✅ |
| adaptive_k1/k2/k3 | — | — | 0.6981/0.6943/0.6978 | 同 | ✅ |
| descent_pair | — | — | 0.6962±0.0079 | 0.6962±0.0079 | ✅ |
| adaptive | 0.7003 | 0.7003 | 0.6898±0.0069 | 0.6898±0.0069 | ✅ |
| random | 0.6870 | 0.687 | 0.6835±0.0080 | 0.6835±0.008 | ✅ |
| staircase | 0.6714 | 0.6714 | — | — | ✅ |
| llm_wrong | 0.6575 | 0.6575 | 0.6714±0.0086 | 0.6714±0.0086 | ✅ |
| fixed_normal | 0.6684 | 0.6684 | — | — | ✅ |
| all_hard | **0.6420→0.6421** | 0.6421 | 0.6498±0.0082 | 0.6498±0.0082 | **已订正** |

### 项 11 — 池内排序力（vs `results/code/junyi_m3_v3_results.json`）
逐值一致 ✅
- k=10：`pool_spearman_success` 0.5507 / `pool_spearman_fused` 0.5778 → 稿件（0.5507 / 0.5778）✅
- k=500：`pool_spearman_success` 0.9017 / `pool_spearman_fused` 0.8321 → 稿件（0.9017 / 0.8321）✅
- `n_pools` 268 → 稿件 268 ✅；`pool_size_median` 18 → 稿件 18 ✅

> 备注：项 8/9/11 均为确定性数字比对（非 LLM 核验），可靠度高。其余 JSON 一致性项（6/7/10/10b）未在本轮覆盖，如需继续可逐个核对。

---

## 二、作者与角色（项 21）— 已可定稿

机构名此前标"待填"，现据 `CITATION.cff` / `.zenodo.json` 确认为 **Youngsan University（Busan, Republic of Korea）**，作者块可定稿。

**投稿版作者块（英文，供 TLT / IJAIED 直接粘贴）— ⚠️ 当前为 withheld 口径：**
```
Zexiao Weng¹
¹ Department of Computer and Information Engineering, Graduate School,
  Youngsan University, Busan 48015, Republic of Korea
Corresponding author: to be assigned on approval of the final manuscript.
```
- 第一作者 Zexiao Weng ORCID：0009-0009-8600-8954
- 通讯作者姓名 / E-mail / ORCID：**최종고 승인 보류 — 아래 说明**

> **〔필자란 보류 — 심사 2.4③ 및 §10, 2026-09-29〕**
> 위 저자 블록은 더 이상 "직접 붙여넣기" 가능한 상태가 아니다. 심사 2.4③에 따라 최종고를
> 읽고 승인하기 전까지는 **필자란·通讯作者란(성명·이메일·ORCID)**, **Zenodo 기여자 명단**,
> **AI 사용 공개문** — 이 세 곳에 제2저자의 이름·연락처를 싣지 않는다.
> 제2저자는 교신저자 역할을 승낙한 상태이며, 승인 후 당사자가 동의하는 방식으로 복원한다.
> 이는 `docs/M3_submission_EN.md` 저자란 및 「Byline and corresponding-author fields
> withheld pending approval」 조항과 동일한 처리다. **투고 직전(최종고 승인 후)에 위 블록을
> 갱신할 것.**
> (English: the paste-ready byline above is withheld pending approval of the final manuscript,
> per review item 2.4③. Refresh it immediately before submission.)

**AI 使用声明（AIGC 合规，需随投稿写入 Methods 或 Acknowledgements）**
> 因本稿方法依赖"LLM 难度标注流水线"（单一静态模型 `qwen36:latest`，基座 Qwen3.6-35B-A3B，IQ3_S），按 IEEE（2024-04）与 Springer Nature 政策，须在 Methods/Acknowledgements 显式披露该工具的名称、用途（难度先验标注）、版本与人工核验环节，并声明作者对人类可问责性负全责。AI 不得列为作者。

---

## 三、期刊合规（项 16）— 以官网为准（已检索）

### 第一顺位 A：IEEE Transactions on Learning Technologies（TLT）
- 出版：IEEE Computer Society + Education Society；Scopus / SCIE 收录；混合出版（OA 可选，APC≈USD 2,645）。
- **篇幅**：IEEE 无硬性"字数上限"，按双栏页数计；通用目标 **6–10 页（双栏，含参考文献）**，超 10 页收超页费（约 USD 220/页）。须用 IEEE 双栏模板初投 PDF。
- **AIGC 政策（IEEE，2024-04 生效）**：AI 生成文本/图/码须在 **Acknowledgements** 披露所用 AI 系统、具体涉及章节与生成程度；纯语言润色"通常不在此限"但建议披露；**AI 不得署名**。
- **数据可得性**：IEEE 多数期刊要求 Data Availability Statement；本稿用 Junyi / assist09 / DBE / XES 真实日志，须逐一满足各数据集许可与引用义务（见清单项 14），并在稿中给出数据与代码可获得性声明（Zenodo DOI 10.5281/zenodo.22719229 可作为 artifact 入口）。

### 第一顺位 B：International Journal of Artificial Intelligence in Education（IJAIED）
- 出版：Springer Nature（官方学会 IAIED）；SCIE / SSCI / Scopus / ERIC 收录；Q1。
- **篇幅**：研究论文/技术报告 **5,000–7,000 词**；结构化摘要（Purpose / Design / Findings / Originality）；关键词≤12；摘要≤250 词。
- **AIGC 政策（Springer Nature）**：AI 工具**不得署名**；实质性 AI 使用须在 **Introduction 或 Acknowledgements** 披露；纯语言润色可免披露；禁止用 AI 伪造数据/图像/引用。本稿的 LLM 标注流水线属"实质性使用"，必须声明。
- **数据可得性**：Springer 鼓励对数据/代码用 DOI 等持久标识引用，遵循 TOP 指南；与 TLT 同理，需 data/code availability statement。

### 备选：中文刊（仅作备份，不写成毕业口径）
- 中文教育技术类核心刊（如《电化教育研究》《中国电化教育》《现代教育技术》《远程教育杂志》《开放教育研究》）正文通常 **8,000–12,000 字（含参考文献）**，部分可接受至 15,000 字；具体以目标刊《投稿须知》为准。
- 当前稿件为中文完整稿（docx 正文约 90,000 中文字），若投英文刊需全文英译并据上表压缩（尤其 IJAIED 5k–7k 词上限偏紧）；若投中文刊则篇幅基本匹配，但仍须补作者块与 AI 声明。

### ⚠️ 关键行动项（投稿前必做）
1. **语言**：TLT/IJAIED 需英文全文 → 安排英译并据字数上限压缩（IJAIED 5k–7k 词最紧）。
2. **作者块 + AI 声明**：按上文第二节写入稿件（英文投版本）。
3. **数据/代码声明**：补 Data Availability Statement + Zenodo DOI 引用；复核四项数据集许可（清单项 14）。
4. **AIGC 政策差异**：两刊均要求披露 LLM 标注流水线，Springer 更强调"实质性使用必披露"——务必在 Methods 写清模型身份（`qwen36:latest` / manifest sha256 `5f2d8551…`）与人工核验。
5. **终稿已含项 8 订正**（all_hard 0.6421）；如需把作者块/AI 声明并入稿件并重导 docx，告知即可。

---

## 四、本轮已落地动作
- 订正稿件 `all_hard` v1：0.6420 → 0.6421（对齐 `junyi_m3_results.json`）。
- 重跑 S2 转换器 + S3 转换，终稿 docx 已更新（182,632 字节）。
- 项 9 / 项 11 确认为逐值一致；项 8 v2 全一致。
- 项 21 机构名解析为 Youngsan University，作者块已拟就。
- 项 16 期刊字数/AIGC/数据政策已检索并汇总。

---

## 五、续（项 6 / 7 / 10 / 10b 的 JSON 一致性核验 + 韩文元信息导出）

### 项 6 — O1 漂移口径 0.5357（vs `results/code/optimized_results.json`）
✅ PASS。稿件 L215/L675 引用 L1 漂移量「线性 min-max 融合 0.5357、分位-logit 融合 0.0001」，与 JSON `o1_metric_comparison` 完全一致：
- `A_minmax_linear.L1_mean` = 0.5357 → 稿件 0.5357 ✅
- `B_ecdf_logit.L1_mean` = 0.0001、reversal_rate 0.0（"排序反转归零"）→ 稿件 0.0001 / 归零 ✅
- 全篇统一使用 0.5357 口径，无旧口径（未统一符号约定）残留。

### 项 7 — O4/O5 优化权重（vs `o6_difficulty_stats.json` → `O6b_repeated_cv5x10`）
✅ PASS。稿件 L430 引用「Junyi 0.4023 ± 0.0480、DBE 0.5240 ± 0.1069」，与 JSON 重复 5 折×10（50 folds）值完全一致：
- junyi：mean 0.4023 / sd 0.048 → 稿件 0.4023 ± 0.0480 ✅（n_folds 50）
- dbe：mean 0.524 / sd 0.1069 → 稿件 0.5240 ± 0.1069 ✅（n_folds 50）
- 同段早期口径「Junyi 0.2610→0.3629 / DBE 0.2207→0.2899」与 `O6a` full_data_success/fused（0.261/0.3629；0.2207/0.2899）及 `o2` baseline/optimized 一致 ✅。

### 项 10 — λ 参数与区间内插（vs `o9_lambda_generalization.json`）
✅ PASS。稿件 L426/L428 引用：
- λ*(k) = 1/(1+(k/27.3)^0.895)：JSON `fitted` k0 = 27.332（→27.3）、p = 0.895 ✅
- 留一 k 交叉验证（区间内插）保留收益 111% / 128%：JSON `Q1_out_of_sample_k.results` retained_fraction k=25 = 1.109（→111%）、k=100 = 1.276（→128%）✅
- 稿件明确「只引用数值、未另立表号」，数值表交 M1 §7.4/7.5 ✅。

### 项 10b — O11/O12（vs `o11_fusion_optimization.json` / `o12_student_o11.json` + `o11_land_verify_out.txt`）
✅ PASS（含诚信红线）。
- 落地实现 `o11_land_verify.py` **15/15 PASS**（稿件 L449 / L91 引用）：OVERALL ALL PASS (checks=15)；k=10 signed7 +3.594、srw7 +3.823 等 10 组 k×변体增益均与 `o11` 逐值一致 ✅。
- **原表 11、表 12 已删**（稿件 L445 整改说明），O11/O12 逐值表移交 M1 表 7-1/7-2，稿件只在 §5.5/§5.6 作定性引用与交叉引用，无悬空表号 ✅。
- 稿件未在任何正文位置直接列 signed7/srw7 增益·胜率·Wilcoxon p 数值（grep "Wilcoxon" 全篇 0 命中），该等数值按设计留于 M1，符合「未另立表号」要求 ✅。
- 软观察（非硬不符）：L435 学生级留出 λ 吻合陈述「0.711/0.716、0.520/0.521、0.368/0.355」中第二位（经验 λ*）0.716/0.521/0.355 未在本次检索的 o9/o11/o12 JSON 直接出现（o12 `lambda_rel_mean` 对应 k 为 0.704/0.506/0.32）；属不同 λ* 取法或来自 M1，建议向 M1/O12 的 λ* 计算脚本二次核对，不影响项 10b 判定。

### 韩文元信息导出
- 已生成 `M3_metadata_ko.md`：한글 제목·저자(웡 자샤오 / 정 민포, 영산대학교)·한글 초록(충실 번역)·한글 키워드·한글 서지 정보·데이터/코드 가용성·AI 사용 공개 안내。
- 주의：본문은 현재 중국어(영문 Abstract 병기)；한글 초록만 제공, 전체 한글화는 별도 작업。저자 한글 표기(웡 자샤오/정 민포)는 로마자명 음차이며, 학위/투고 규정에 따라 정확한 한자/한글명으로 교정 필요。

### 本轮已落地动作（续）
- 项 6/7/10/10b 四项的 JSON 源值逐值核验，全部 PASS（含 1 处软观察）。
- 韩文元信息导出文件 `M3_metadata_ko.md` 已生成。
- 至此「结果可复算清单」22 项中，数字一致性类（6/7/8/9/10/10b/11）均已对照源 JSON 复核并一致；仅余项 6 软观察待向 M1 二次核对。

---

## 二、L435 λ* 软观察二次核对 + 英译 + 作者块/AI声明并入重导（本轮最新三项）

### 任务① — L435 λ* 软观察向 M1 二次核对 → ✅ 已闭合
- 完整读取 `results/code/o10_user_holdout.json`，其 `results` 字段给出 k=10/25/50 的 `lambda_hat`（闭式未调参）与 `lambda_emp_mean`（学生级留出经验 λ*）。
- 三对数值精确吻合稿件 L435 陈述：
  - k=10：lambda_hat 0.711 / lambda_emp_mean 0.716 ✅
  - k=25：lambda_hat 0.520 / lambda_emp_mean 0.521 ✅
  - k=50：lambda_hat 0.368 / lambda_emp_mean 0.355 ✅
- 结论：L435「0.711/0.716、0.520/0.521、0.368/0.355」中第二位（经验 λ*）来源已确证为 `o10_user_holdout.json` 的 `lambda_emp_mean`，非悬空/误植。任务①完全闭合，原"软观察待核对"项清除。

### 任务② — 全文英译
- 产出 `docs/M3_submission_EN.md`（约 20,400 词主文 + 7 表 + 25 条参考文献）。
- 已剔除原中文稿内部"自我审计式"元叙事（审稿意见/K6/口径更正逐条列表），改写为干净期刊 prose；保留全部关键数值、贡献、局限、tables、references。
- ⚠️ **词数超标**：实测约 20,422 词（含表/参考文献），约为 IJAIED/IEEE-TLT 5,000–7,000 词上限的 2.9 倍。前轮"约 12,000 词"估算偏低，特此更正。当前为"完整/长版"英译，非压缩投稿版，压缩待用户决策（见任务③决策项）。

### 任务③ — 作者块 + AI声明并入并重导 docx
- 英文稿首部已并入：`Zexiao Weng¹ and MinPo Jung¹,*` 作者块（Youngsan University, Busan 48015, Republic of Korea；通讯 minpo@ysu.ac.kr，ORCID 0009-0003-3369-757X；第一作者 ORCID 0009-0009-8600-8954）+ **AI-Assisted Writing and LLM Annotation Disclosure** 声明段（明确 LLM 仅作语言润色、不参与科学内容/统计决策；qwen36 为被审计对象而非写作工具，附 Ollama manifest SHA-256）。
- 新增英文 S2 转换器 `working/md2academic_en.py`（Times New Roman、英文断句/表号识别、author-line 居中无缩进 CSS、Contents 目录、`<html lang="en">`），中文 `md2academic.py` 未改动。
- 修复前轮 Python 路径错误（改用 venv `C:/Users/Administrator/.venv-html-to-docx2/Scripts/python.exe`），S2→S3 全链路重导成功。
- 终稿：`stage3/M3_有序难度决策与大模型先验边界_EN_终稿.docx`（121,141 字节，354 段；作者块 + AI声明均已渲染为居中独立行；present_files 已预览）。
- `pipeline-state.yaml` 已新增 `en_export` 记录（含 docx_bytes、author_block_rendered、ai_disclosure_rendered、approx_body_words、word_limit_status=EXCEEDED）。

### 决策待办（需用户确认）
- [ ] 英文稿词数超标：是否(1)保留本 20.4k 长版作为 preprint/补充材料，(2)另起 5–7k 压缩投稿版（需大刀阔斧删并/摘要化 §1–§9），或 (3)仅投中文终稿 + 英文长版附录？请用户定夺后再执行压缩重写。
