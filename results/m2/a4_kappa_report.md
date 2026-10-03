# M2 A4 双编码 —— 内部工作留痕（**不作为结果接受**；更新：2026-09-27）
> **定位更正（审阅意见 §5.1 与 §5.4，2026-09-29）。** 审阅判定路线 A 的 A2·A3·A4 产出**不作为结果接受**，M2 已于 2026-09-29 转为**路线 B**（保留审计时点 tag `audit-m2-20260911` 封存的内部静态审计与七元组四字段未实现的诊断 → 学位论文治理章 + 短经验报告，撤下 *JSS* / *EMSE* / *IST*）。因此：① **本方案不再作为投稿前置条件执行**；② 本文件保留为"路线 A 若重启时应如何做"的历史设计文档；③ 路线 A 重启的前置条件是——具备真实机制逻辑的效果生产者，且**在编码之前登记两名人类编码者的盲编流程**，届时须先向导师说明编码者是谁。在此之前，**各投稿稿件**任何位置均不报告 Cohen κ 数值，也不宣称双编码（本文件作为内部留痕仍照录数值供复核，数值不作为结果，亦不得援引为信度证据）。


> **状态：闭集口径 κ = 0.778 / 0.595 / 0.935，两字段达"良好"；但 A4 仍 UNCHECKED。**
> 本文件为内部工作报告，非投稿稿 §6 终稿。两项限制使 κ **暂不可写入 §6**：
> ① coderA 侧闭集映射为 AI 提议、**coderA 本人尚未复核**；② A4 系统数仅 2、要求 ≥4。
> （M2 稿 §6 自设红线" A4 完成前不报告任何 κ 值"；清单第 19 项规则"完成并报告 κ 后方可勾销"。）
>
> **κ 值的处置（审阅意见 §5.1，2026-09-29）。** 本表 κ 值 **0.778 / 0.595 / 0.935** 属内部工作留痕，**不写入任何稿件的正文或表格**；A4 不再作为投稿前置条件执行。M2 各稿件的裁定口径为：**全篇未报告任何 κ 数值，不宣称双重编码**（详见 M2 稿件 §6）。

## 1. κ 口径说明（闭集口径，coderA vs coderB 问卷，17 项；**内部留痕数值，不作为结果报告**）

| 字段 | κ | 判定 |
|---|---|---|
| target_construct | **0.778** | **良好 (≥0.61)** |
| direction | 0.595 | 可接受 (0.41–0.60) |
| channel | **0.935** | **良好 (≥0.61)** |

- 数据源：`a4_coderA_closed.csv`（coderA 侧闭集映射，**提议版待 coderA 确认**）
  vs `a4_coderB_survey.csv`（coderB 问卷产出，闭集码）。
- **无多值单元格**（全部单值），故下界=主估=上界，κ 为确定值而非区间。
- **coderA 侧闭集映射为 AI 按 CODEBOOK 提议、coderA 本人尚未复核**（见上文限制 ①）；**本文件此前所写「两侧均为人类编码」与该事实相矛盾，该说法已撤回（审阅意见 §2.3，2026-09-29）。** 现状是：coderB 侧为人类编码，coderA 侧尚未完成人类复核，故本文件**不构成双编码证据**，也不得据此宣称已测得评分者间信度。脚本只做对齐 + 数学。
- 复算：
  `python results/m2/a4_kappa_v2.py --coder-a results/m2/a4_coderA_closed.csv --coder-b results/m2/a4_coderB_survey.csv`
- **三字段全一致项：11/17**。

### 三代对比（同一批 17 个实例）

| 字段 | v1（旧中文·多值） | v2（旧中文·单值） | **v3 闭集（问卷）** |
|---|---|---|---|
| target_construct | 0.346 不足 | 0.549 可接受 | **0.778 良好** |
| direction | 0.577 可接受 | 0.642 良好 | 0.595 可接受 |
| channel | 0.572 可接受 | 0.452 可接受 | **0.935 良好** |

> 结论：闭集化主要收益在 `target_construct`（+0.229）与 `channel`（+0.483），
> 印证二者此前的低值**源于标签集不闭集/近义异名，而非真实判断冲突**。
> `direction` 微降（0.642→0.595）是真实分歧变化，非缺陷。

### 残余分歧 6 处（须仲裁，κ 应如实保留）

| item | 字段 | coderA(提议) | coderB | 性质 |
|---|---|---|---|---|
| LUDI_2 | construct | ACHIEVEMENT | ENGAGEMENT | 徽章=成就 vs 促活，边界争议 |
| LUDI_5 | construct | ACHIEVEMENT | ENGAGEMENT | ⚠️ coderA 复核表已标注此歧义 |
| LUDI_6 | direction | withdraw | approach | 扣分计时器=惩罚 vs 激励 |
| LUXP_3 | direction | approach | neutral | 分组是否构成"促学" |
| LUXP_10 | direction | approach | neutral | 规则引擎是否构成"促学" |
| LUXP_11 | construct | ENGAGEMENT | ACHIEVEMENT | ⚠️ 已标注歧义（与 §3.1.4 读法冲突） |
| LUXP_11 | channel | SCORE_PANEL | XP_STATE | ⚠️ 已标注歧义（「数值」多义） |

> ⚠️ **不得为使 κ 上升而反向修改 coderA 映射去迎合 coderB**（循环论证、虚增信度）。
> 上表 3 处本就在 coderA 复核表中**事先标注**为歧义项，应由 coderA **独立**按 CODEBOOK 裁定。

## 2. 缺口状态（决定能否写 §6 / 勾销 19）

### ① 闭集 CODEBOOK 采纳 —— ✅ 已解决（v3 问卷）
coderB 经 `a4_coderB_survey.html` 问卷产出**闭集码**（ACHIEVEMENT / SOCIAL / BADGE…），
v2 的"旧中文词表"问题不复存在；κ 现按闭集口径计算（见 §1）。

### ② channel 近义异名 —— ✅ 已解决（0.452 → 0.935）
改用 §3.1.2 闭集 13 类后，原 7 处同义异名全部归同，`channel` κ 由 0.452 升至 **0.935**。

### ③ channel 多值格 —— ✅ 已解决（无多值残留）
问卷为单选，产出数据**无任何多值单元格**，`LUXP_5`/`LUXP_8` 的多值问题消失，
κ 由"区间估计"变为**确定值**。

### ④ 独立性（v2 有瑕疵，v3 问卷已根治）

- v2 的成因：coderB 按"选项词"填写，而选项词来源表 §3.1.4 **并列展示了 coderA 的逐条原标签**
  → 存在"经选项词间接暴露 A 标签"的通道，κ 有被抬高之虞（用户已确认盲编初衷）。
- **v3 问卷（全三字段）仅提供源码锚点 + 真实功能描述 + 闭集码，不展示 coderA 任何编码值**，
  coderB 侧独立性已确保；v2 的 κ 降为过程值。
- 残留待办：**coderA 侧的闭集映射仍为 LLM（AI）的提议**，须 coderA 本人独立复核（见 §4 步 5）。
  在此之前，本报告 κ 只能作为**内部进度值**，不得写入投稿稿。

### ⑤ A4 系统数未达 ≥4（与 κ 无关的独立缺口）
当前仍仅 **2 个系统**（Ludilearn + Level Up XP）双编码，A4 要求 ≥4；
Habitica / Khan Academy 仍为候选、待 clone 复核。此项不闭环，第 19 项不可勾销。

## 3. 已更正的历史错误

- **LevelUpXP "404 / 不可复现" 系误检**：查的是已失效的 `danbetcher/moodle-levelup`。
  真实源 `FMCorz/moodle-block_xp`（commit `65541fdc`，Release v20.0），
  **11 个 LUXP 锚点全部 HTTP 200 核验通过** → coderB 判定具备可复现锚点。
- **v1 coderB 曾为 GBK 编码**、含 12+6 个多值格；v2 已归一化 UTF-8 且仅剩 2 个多值格。
- **原 CODEBOOK（§3）已废止**：`target_construct` 用英文且把 channel 词混入 construct 列，
  与中文实务脱节，是 v1 `target_construct` κ=0.346 的结构性根因；以 §3.1 闭集版为准。

## 4. 下一步（κ 已达标，剩余两项）

| 步 | 动作 | 状态 |
|---|---|---|
| 1 | coderB 确认盲编 | ✅ 已确认 |
| 2 | 生成问卷（17 题 × 3 闭集问，不展示 A 值）+ coderA 闭集复核表 | ✅ 已生成 |
| 3 | coderB 完成问卷并导出 `a4_coderB_survey.csv` | ✅ **已完成** |
| 4 | 闭集口径 κ 复算 | ✅ **已完成**：0.778 / 0.595 / 0.935（见 §1） |
| 5 | **coderA 独立复核 `a4_coderA_closed_review.csv`** 并裁定 3 处歧义 | ⏳ **待 coderA**（当前 κ 中 coderA 侧仍为 AI 提议值） |
| 6 | 补 ≥2 个可公开获取、非同源外部系统并双编码（达 A4 的 ≥4 系统） | ⏳ **唯一硬缺口** |
| 7 | 写入 M2 §6 双编码 κ 表 → 勾销清单第 19 项 | ⏳（须 5、6 完成） |

> **关键限定**：当前 κ 的 coderA 侧为 **LLM 按 CODEBOOK 提议的映射**，尚未经 coderA 本人确认。
> 在 coderA 复核前，该 κ 只能作为**内部进度值**，不得写入投稿稿 §6。

## 5. 复算命令

```bash
# 闭集口径（当前权威）
python results/m2/a4_kappa_v2.py \
  --coder-a results/m2/a4_coderA_closed.csv \
  --coder-b results/m2/a4_coderB_survey.csv

# 旧中文词表口径（v2，历史对照）
python results/m2/a4_kappa_v2.py --coder-b results/m2/a4_coderB_v2.csv
```

> 数据文件：`a4_coderA.csv`(原始) · `a4_coderA_closed_review.csv`(复核表) ·
> `a4_coderA_closed.csv`(提议闭集版) · `a4_coderB.csv`(v1) · `a4_coderB_v2.csv`(v2) ·
> **`a4_coderB_survey.csv`(v3 问卷产出，当前权威)** · `a4_coderB_survey.html`(问卷) / 本报告。
