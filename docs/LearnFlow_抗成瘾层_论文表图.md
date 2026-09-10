# 抗成瘾层评估：研究方法、表 2 与图 2

> 本章节为 LearnFlow「学习成瘾化研究」论文的**系统贡献（System Contribution）**支撑材料，
> 以可复现的计算式评估（in-silico ablation）验证抗成瘾层（LF-M54 班级宠物 + LAI 风险自适应降权仲裁器）
> 的设计方向与机制有效性。产物对应 `E:/learnflow/artifacts/evaluation/` 下的全量结果与三张 SVG 图表。

---

## § 方法　研究方法（抗成瘾层计算式评估）

为回应"论文需要可复现的实证/准实证证据"这一要求，我们对抗成瘾层的两块设计——
**(1) LF-M54 班级宠物（真实连接替代，Hari C1）** 与 **(2) 机制仲裁器「LAI 风险自适应降权」**——
进行了**计算式评估（in-silico ablation）**。该评估**非田野实验（non-field experiment）**，
而是系统型论文（对标 CHI / UIST 系统贡献类文章的 ablation 范式）的**机制验证证据**：
其目的是证明引擎设计在给定输入下"按预期方向移动指标"，而非估计真实世界因果效应。

**设计与队列。** 我们构造一个合成学生队列 **N = 600**（K-12 学段），
固定随机种子 **`seed = 20260906`**，保证完全可复现。每名学生在五维 LAI 基底
（时间 / 动机 / 控制 / 认知 / 功能）上叠加四个文献补位参数
（`connection_quality`、`variable_ratio_exposure`、`incentive_sensitization`、`hook_internal_trigger_dependency`）。
核心指标为 **LAI（Learning Addiction Index，0–100，分值越高表示学习健康度越高）**。

**配对反事实三条件（同一队列在三种配置下评估，消除个体差异）。**

- **C0 基线（Baseline）**：纯参与最大化，不开启任何抗成瘾层（仲裁器 `lai_risk = None`）。
- **C1 班级宠物（Class Pet）**：仅开启真实连接替代——将 `connection_quality` 抬升到班级宠物回灌值
  （班级凝聚力 cohesion = 78 → `connection_quality = 0.771`，越过 LAI 0.7 缓冲阈值），经 Hari C1「连接替代」路径缓冲动机与功能维度。
- **C2 全抗成瘾层（Full Anti-Addiction）**：C1 之上，再启用仲裁器按个体 LAI 风险对
  高成瘾化且拉回型（approach）的 nudge 进行自适应降权，衰减可变比率、激励敏化与 Hook 暴露。

**仲裁器消融（Arbitrator Ablation）。** 固定 5 个候选 Effect
（LF-M44 FOMO、LF-M33 Hook、LF-M08 稀缺性、LF-M07 集换、LF-M35 情境线索），
对比 `lai_risk = None`（默认，行为与旧版一致）与 `lai_risk = 0.70` 下的下发差异，
以隔离"风险自适应降权"层本身的运作（消融中放松干预预算，排除预算约束干扰）。

**声明。** 本评估为**计算式 / 设计验证（computational / design validation）**，
作为系统贡献章节的机制验证证据；真实田野因果效应须在后续与学校合作的
RCT / 队列研究中补齐。所有产物（含预分析计划 `pap.json` 与种子）已落盘，可逐行复现。

---

## 表 2　抗成瘾层主结果（in-silico ablation, N = 600, seed = 20260906）

| 场景 | 平均 LAI | 中位 LAI | LAI 标准差 | L3+L4 人数 | % 应降游戏化 | % 应通知家长 |
|---|---:|---:|---:|---:|---:|---:|
| C0 基线（无抗成瘾层） | 63.17 | 63.52 | 11.12 | 70 | 54.5% | 11.7% |
| C1 班级宠物 | 63.60 | 63.98 | 11.13 | 67 | 52.5% | 11.2% |
| C2 全抗成瘾层 | 64.78 | 65.00 | 10.70 | 53 | 47.5% | 8.8% |
| **边际提升（C2−C0 / C1−C0）** | **+1.61 / +0.43** | **+1.48 / +0.46** | **−0.42 / +0.01** | **−17 / −3** | **−7.0pp / −2.0pp** | **−2.9pp / −0.5pp** |

**表注（Caption）。** 各场景基于同一 N = 600 合成队列（固定种子 20260906）配对反事实评估；
LAI 为 0–100 连续指数，**分值越高表示学习健康度越高**。"L3+L4 人数"为 LAI 风险等级
L3_DEEP（深度沉迷）与 L4_PATHOLOGICAL（病理性）之和；该队列中无 L4 个案（各场景 L4 = 0）。
"边际提升"行报告 C2 与 C1 相对 C0 基线的差值：平均 LAI 提升 +1.61 / +0.43 个 log 点；
L3+L4 高危人数下降 17 / 3 人；应降游戏化占比下降 7.0 / 2.0 个百分点；应通知家长占比下降 2.9 / 0.5 个百分点。
班级宠物回灌连接质量 `connection_quality = 0.771`（cohesion = 78.0，active_ratio = 0.75）。
**高危亚组救援率**：C0 下处于 L3/L4 的 70 名学生中，**17 名（24.3%）** 在 C2 下脱离高危（→ L1/L2）。
**仲裁器降权**：`lai_risk = None` 下发全部 5 个候选，升至高成瘾风险时仅下发 3 个，
丢弃成瘾风险最高的 **LF-M44 FOMO（权重 0.9）** 与 **LF-M33 Hook（权重 0.7）**，保留低风险 3 个。
*声明：计算式 / 设计验证，非田野实验；用于系统贡献的机制验证。*

---

## 图 2　抗成瘾层评估可视化（Figure 2）

> 三张矢量图（SVG）位于以下路径，可直接嵌入 LaTeX（`\includegraphics`）或 Word（插入图片）：
> - 图 2a：`E:/learnflow/artifacts/evaluation/figures/lai_by_scenario.svg`
> - 图 2b：`E:/learnflow/artifacts/evaluation/figures/risk_distribution.svg`
> - 图 2c：`E:/learnflow/artifacts/evaluation/figures/arbitrator_cooling.svg`

![图 2a 各场景平均 LAI](E:/learnflow/artifacts/evaluation/figures/lai_by_scenario.svg)
![图 2b 各场景 LAI 风险等级分布](E:/learnflow/artifacts/evaluation/figures/risk_distribution.svg)
![图 2c 仲裁器 LAI 风险自适应降权对比](E:/learnflow/artifacts/evaluation/figures/arbitrator_cooling.svg)

### 图 2a　各场景平均 LAI 柱状图（Caption）

横向对比 C0 / C1 / C2 三场景的**平均 LAI**。指标越高代表学习健康度越高；
柱高呈现 **C0（63.17）< C1（63.60）< C2（64.78）的单调上升趋势**，
表明抗成瘾层（班级宠物 → 叠加仲裁器降权）逐级、累加地将队列整体推向更健康的 LAI 区间。
边际增益 C2−C0 = +1.61 个 log 点，数值虽小但方向与设计预期完全一致，
且在同一配对队列下排除了个体差异混杂。

### 图 2b　各场景 LAI 风险等级（L1–L4）堆叠分布（Caption）

按 LAI 风险四等级（L1 正常 / L2 观察 / L3 深度沉迷 / L4 病理性）对每场景 600 人做堆叠分布。
三场景均无 L4 个案；关键信号在于 **L3+L4 高危占比随抗成瘾层开启而单调下降**
（C0 = 70 人 → C1 = 67 人 → C2 = 53 人），其中 C2 下高危人数较 C0 减少 17 人（降幅约 24.3% 的高危亚组被"救援"脱离），
直观支撑表 2 中"全抗成瘾层显著降低深度沉迷规模"的结论。

### 图 2c　仲裁器「LAI 风险自适应降权」对比（Caption）

展示机制仲裁器在不同 LAI 风险设定下的候选 nudge 下发情况。
`lai_risk = None`（默认）时下发全部 **5 个**候选 Effect；
当 LAI 风险升至高（high）时仅下发 **3 个**，**丢弃成瘾风险最高的 LF-M44 FOMO（权重 0.9）与 LF-M33 Hook（权重 0.7）**，
保留低风险的 LF-M08 / LF-M07 / LF-M35。
该图直接证明"风险自适应降权"层按 `_ADDICTION_RISK` 权重正确运作——
在高成瘾风险语境下，系统主动牺牲高成瘾化拉回型 nudge 的触达，以保守偏置保护学习者。

---

## 表 3　AI 实时分析层：风险识别性能（in-silico, N = 600, seed = 20260906）

| 模型 | AUROC | Accuracy | 说明 |
|---|---:|---:|---|
| 规则基线 (夜间比例阈值) | 0.498 | — | 纯启发式上界 |
| **ML 时序风险模型** | **0.966** | 0.852 | 本层主模型（14 维滚动窗口特征 + 在线隐状态 MLP）|

**表注（Caption）。** 各模型基于同一 N = 600 合成脱敏队列（固定种子 20260906）评估；
真实数据可经 `scripts/train_eval_ai_layer.py --data` 替换复现。ML 时序风险模型 AUROC 达 0.966，
远超规则基线 0.498（ΔAUROC = +0.468），证明数据驱动模型显著优于单特征启发式；
早期预警召回率 @ 阈值 0.5 = 98.0%，即高危学习行为中被正确标红的比例。
*声明：计算式 / 设计验证，非田野实验；proxy 标签来自植入的「成瘾签名」，用于证明管线可学习。*

---

## 图 3　AI 实时分析层 ROC 曲线（Figure 3）

> 矢量图（SVG）位于以下路径，可直接嵌入 LaTeX（`\includegraphics`）或 Word（插入图片）：
> `E:/learnflow/learnflow-backend/artifacts/ai_layer/figures/roc_curve.svg`

![图 3 AI 实时分析层 ROC 曲线](E:/learnflow/learnflow-backend/artifacts/ai_layer/figures/roc_curve.svg)

### 图 3　ROC 曲线（Caption）

曲线下面积 AUROC = 0.966，远超规则基线 0.498（ΔAUROC = +0.468）。ROC 在假正率可控区间内高位上扬，
表明 ML 时序风险模型对高危学习行为（夜间高发、提示依赖、浅层思考、强度过载等「成瘾签名」）具有强区分力，
与表 3 互证。该模型构成 AI 实时分析层「感知」端：特征管线（滚动窗口 14 维）→ TemporalRiskModel →
RL 仲裁器 / LLM 干预 → 实时分析 API，与 §2 抗成瘾层（LF-M54 班级宠物 + 仲裁器 LAI 风险自适应降权）
共同形成「实时识别 + 自适应干预」双层架构（详见《AI 实时分析层设计与评估》）。

---

## 结论　（Concluding Statement）

上述计算式评估一致表明：抗成瘾层在保持可复现性的前提下，
使队列平均 LAI 单调提升、L3+L4 高危规模显著收缩（救援率 24.3%），
并令仲裁器在高风险语境下精准丢弃 LF-M44 FOMO 与 LF-M33 Hook。
这为论文"**保守偏置 / 风险自适应**"的伦理立场提供了可量化、可复现的机制验证证据，
并构成系统贡献章节中"抗成瘾设计按预期运作"的核心支撑。

此外，AI 实时分析层以 0.966 AUROC 的实时风险识别与 98.0% 的早期预警召回，为抗成瘾层
（保守偏置 / 风险自适应降权）提供前置的「何时介入」感知能力；二者构成可复现、可审计的
学习健康防护体系。
