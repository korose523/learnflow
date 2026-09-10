# LearnFlow AI 实时分析层：设计与评估

> 配套工程：`learnflow-backend/app/services/{_ml_utils,feature_store,ml_risk_model,rl_arbitrator,ollama_client,llm_intervention,causal_effects}.py`
> + `app/api/analytics.py` + `scripts/train_eval_ai_layer.py`
> 评估产物：`artifacts/ai_layer/{result.json, tables/main_results.md, figures/roc_curve.svg}`

本文档把《AI 在学习成瘾研究中的应用》工程类论文所需的「AI 实时分析层」从
架构、模块、数据到评估结果完整定稿，可直接作为论文 §系统/§方法/§评估 的底稿。

---

## 1. 动机与定位

既有 LearnFlow 是一整套**规则 / 心理学启发式引擎**
（`positive_addiction_engine`、`learning_addiction_index`、`mechanism_arbitrator`
以及 `duolingo_`/`habit_`/`social_`/`ux_addiction_engine` 等），全部为
**硬编码启发式，没有可训练、可在线推断、可评估的 ML 模型**。

本层补齐这一缺口：在保留全部规则引擎作为 **baseline + 安全兜底** 的前提下，
叠加一个**数据驱动、可在线学习、可复现评估**的 AI 实时分析层，实现三件事：

1. **实时成瘾风险预测**：从行为事件流序列建模，实时预测 LAI 风险轨迹；
2. **自适应干预策略**（RL）：在线学习「什么状态下发什么机制 → 健康度最高、成瘾最低」；
3. **LLM 辅助的伦理护栏**：自动生成非操控性干预话术，并强制对照「暗黑模式」做合规审计。

---

## 2. 系统架构

```
LearningEvent 流 (只增不改, decision_snapshot 可复现)
        │
        ▼
┌─────────────────────────────────────────────┐
│  FeatureStore (滚动窗口聚合)                  │
│  → 14 维规范特征向量 (FEATURE_KEYS)            │
└─────────────────────────────────────────────┘
        │
        ├──────────────┐
        ▼              ▼
┌──────────────┐  ┌──────────────────────────┐
│TemporalRisk  │  │ LLM 信号提取              │
│Model (MLP)   │  │ (ollama_client + 护栏)    │
│→ 实时风险概率 │  └──────────────────────────┘
└──────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  RLArbitrator (contextual bandit)             │
│  在规则 MechanismArbitrator 之上做送达决策    │
│  未训练 → 回退规则 (保守偏置不变)             │
└─────────────────────────────────────────────┘
        │
        ▼
   机制库 (各 addiction_engine / LF-M01..54)
        │
        ▼
  实时反馈 + 预警 + 因果评估 (DML)
```

---

## 3. 模块设计（可复现锚点）

| 模块 | 文件 | 关键技术 | 论文对应 |
|---|---|---|---|
| 数值基础 | `_ml_utils.py` | 纯 Python 矩阵/OLS/AUROC（无 numpy） | 方法 §实现 |
| 特征摄入 | `feature_store.py` | 滚动窗口聚合 → 14 维向量 | 方法 §特征 |
| 风险模型 | `ml_risk_model.py` | 1 隐藏层 MLP + logistic，在线隐藏态 | 方法 §风险模型 |
| 干预策略 | `rl_arbitrator.py` + `mechanism_arbitrator.py` | contextual bandit (ε-greedy + TD)，已接入仲裁器在线决策闭环（LAI 改善作奖励） | 方法 §RL仲裁 / §在线闭环 |
| LLM 护栏 | `llm_intervention.py` + `ollama_client.py` | Ollama/模板回退 + 暗黑模式正则 | 方法 §伦理护栏 |
| 因果评估 | `causal_effects.py` | DML 双机器学习 ATE | 方法 §因果 |
| 实时 API | `api/analytics.py` | ingest/risk/class/early-warning | 系统 §接口 |

**特征向量（FEATURE_KEYS，14 维，全部归一 [0,1]）**：
正确率、提示依赖率、跳过率、连续错、思考时长、夜间比例、近 10 分钟强度、
事件间隔变异性（可变比率暴露代理）、平均难度、沉浸/心流区占比、会话切换率、
距上次事件间隔、窗口时长、参与强度。

**时序建模说明（诚实披露）**：纯 Python 下完整 BPTT 代价过高，故采用
「滚动窗口聚合承载时序动态 + 在线隐藏态平滑」的工程折中——特征本身编码了
近期行为趋势，模型以特征为输入即可感知成瘾进度，且**完全可复现、无外部依赖**。

### 在线决策闭环（RL × 规则仲裁器）

`RLArbitrator` 现已接入 `MechanismArbitrator.arbitrate` 的在线决策闭环，形成
「感知（AI 风险模型）→ 决策（RL 选机制）→ 反馈（LAI 改善作奖励）」的学习回路：

- **接入点**：`MechanismArbitrator.__init__` 新增可选 `rl_arbitrator` 参数；在 `arbitrate`
  的「LAI 风险自适应降权（层 1.5）」之后、「冲突消解（层 2）」之前，若 bandit 已训练，
  调用 `select_mechanism(ctx, effects, risk_tier)` 在当前风险档下从候选 approach 机制中
  由 bandit 选一个收益最高的，**丢弃其余 approach 机制**（withdraw / neutral 不受影响）。
  风险档由 `lai_risk` 经 `_risk_tier()` 离散化为 t0–t3，与 `TemporalRiskModel.risk_tier`
  阈值对齐，使规则层与 RL 层共享同一风险桶。
- **奖励信号**：新增 `report_lai_feedback(user_id, lai_before, lai_after, session_id)`，
  奖励 = `(lai_after − lai_before) / 100`（LAI 0–100，越高越健康，故 LAI 改善为正收益），
  记入「决策时刻为该 (用户, 会话) 选中的 approach 机制」对应的 (风险档, 机制) 状态-动作对，
  即 `rl.observe(risk_tier, chosen_id, reward)`。
- **安全兜底（向后兼容）**：bandit 未训练 → RL 层完全跳过，规则仲裁行为与旧版一致；
  RL 选中的机制若被后续冲突层（approach vs withdraw 保守偏置）丢弃，则不记反馈目标；
  反馈仅在该机制确实下发时才回灌，且未注入 RL 仲裁器时 `report_lai_feedback` 安全返回 `None`。

> **诚实披露**：bandit 以「LAI 改善」这一近端代理奖励学习，是长期成瘾化降低的近似信号；
> 奖励对齐（reward alignment）仍需在与学校合作的 RCT / 队列研究中检验。在线学习默认关闭，
> 仅在已训练且显式注入 `rl_arbitrator` 时启用。

---

## 4. 公开数据集与代理标签策略

检索确认：**目前没有「学习行为日志 + 成瘾标签」的大规模公开配对集**。
本项目采用三层代理标签策略（论文 §数据）：

1. **自监督 proxy 标签**：用本项目 LAI 引擎对 `learning_events` 打伪标签，
   预训练风险模型（已内置 `scripts/train_eval_ai_layer.py --sample` 证明管线可学习）；
2. **少量真人标注微调**：用 IGD / 手机成瘾量表对 K12 用户做小样本标注；
3. **无监督异常检测**：对行为流做孤立森林 / AutoEncoder 识别沉迷模式。

**候选公开数据集（按契合度）**：

| 数据集 | 规模 | 许可 | 用途 |
|---|---|---|---|
| EdNet (Riiid) | 78万生/1.31亿次 | CC BY-NC | 行为序列预训练主力 |
| Eedi / NeurIPS2020 | 500万+次 | 注册 | 时序学习投入建模 |
| KDD Cup 2015 / ASSISTments | 94万/32万次 | 学术申请 | 作答-时间戳序列 |
| Junyi Academy | 786万次 | 学术申请 | K12 数学层级日志 |
| OULAD | 3.26万生 | CC BY 4.0 | 分布外验证 |
| IGD 学生 (Zenodo 15068893) | 989生 | CC BY 4.0 | 游戏时长+IGD 自评（标签代理） |
| 手机成瘾 (Kaggle) | 1.36万用户 | 开放 | 使用时长+成瘾标签 |

脚本已内置 `load_event_csv()` 适配器，真实 CSV 到手后填入字段映射即可切换
`--data`（无需改模型代码）。

---

## 5. 评估结果（in-silico）

运行 `python scripts/train_eval_ai_layer.py --sample --out artifacts/ai_layer`，
N=600 合成脱敏样本（植入「成瘾签名」，proxy 标签）：

| 模型 | AUROC | Accuracy | 说明 |
|---|---|---|---|
| 规则基线（夜间比例阈值） | 0.498 | — | 纯启发式上界（近随机，因标签由多特征耦合驱动） |
| **ML 时序风险模型** | **0.966** | **0.852** | 本层主模型 |

- **早期预警召回率 @阈值 0.5 = 98.0%**（高危用户中被正确标红比例）；
- **ΔAUROC(ML − 规则) = +0.468** —— 量化证明数据驱动模型显著优于单特征规则；
- ROC 曲线见 `figures/roc_curve.svg`（可嵌入论文图 3）。

DML 因果评估（`causal_effects.py`）在合成「处理→结局」数据上可复现恢复
植入的 ATE=2.5（±0.5），为后续「机制→LAI 因果效应」的论文强卖点提供可复现方法。

> **声明**：以上为计算式 / 设计验证，非田野实验；proxy 标签来自植入的成瘾签名，
> 用于证明管线具备学习能力。真实大效应需与学校合作的 RCT / 队列研究补齐。

---

## 6. 与论文结构的映射

| 论文章节 | 本层供给 |
|---|---|
| §引言：参与 vs 成瘾两难 | `llm_intervention.py` 的暗黑模式护栏（对照多邻国暗黑模式） |
| §系统 | 第 2 节架构图 |
| §方法 | 第 3 节模块表 + 第 4 节数据集与代理标签 |
| §评估 | 第 5 节（表 3 = `tables/main_results.md`；图 3 = ROC） |
| §讨论/局限 | 第 5 节声明 + 第 4 节代理标签局限 |

---

## 7. 运行与复现

```bash
# 训练/评估 AI 层 (合成样本)
PYTHONPATH=".venv/Lib/site-packages;." \
  .venv_new/Scripts/python.exe scripts/train_eval_ai_layer.py \
  --sample --out artifacts/ai_layer

# 单元测试
PYTHONPATH=".venv/Lib/site-packages;." .venv_new/Scripts/python.exe \
  -m pytest tests/test_ai_layer.py -q
```

依赖：纯标准库 + 现有 FastAPI/SQLAlchemy 栈；**无需 numpy / torch / sklearn**，
在受限环境（本机无 numpy）亦可训练与推断。
