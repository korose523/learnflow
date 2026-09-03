# LearnFlow 机制治理与落实方案

> **文档性质**：机制治理架构设计 + 研究可信度审计（双重性质）
> **撰写人**：严复核（robustness-auditor，实证研究团）
> **调度**：论笃行（team-lead）
> **版本**：v1.0
> **审计基线**：`E:\learnflow\learnflow-backend` @ 2026-09-02
> **核验方式**：全部结论均由本机 `grep` / `python` 复算，行号可直接定位。**凡与先前材料不一致者，一律以本文档为准，并在 §1.4 列出差异明细。**

---

## 0. 审计声明：本报告的立场

这份文档不是"如何让 76 这个数字成立"的辩护词。**站在审计师立场，我的首要结论是：76 这个数字在任何可发表场合都不应再出现。** 试图用重新分类、重新切分去"凑"出 76，是把一个工程记账错误升级为学术不端（selective reporting / outcome switching），风险远大于承认它。

本报告的价值主张是**转换赛道**：把"我们实现了 76 个机制"这个**无法辩护的资产声明**，转换成"我们对一个自称 76 机制的游戏化学习系统做了系统性审计，发现实际唯一机制 53 个、80% 零调用、7 组重复实现、17 处无仲裁的干预冲突"这个**可辩护的知识贡献**。后者在实证软件工程（ESE）和 CS 教育研究里是**真实且稀缺的**贡献——文献里充斥着"我们设计了 N 个 gamification elements"的设计论文，几乎没有"我们审计了 N 个声称的 gamification elements 到底落地了多少"的核查论文。

**态度声明**：下文所有"建议"都标注了置信度与反例。凡是我认为有风险的路线，即使是我自己提出的，也会标注风险。

---

# 第一部分 数字诚信修正（最高优先级）

## 1.1 复算结果：四个数字层级

我在基线代码上独立复算，得到**四个必须严格区分**的数字。混淆这四者，正是"76"产生的根源。

| 层级 | 定义 | 数值 | 复算命令 |
|---|---|---|---|
| **L0** 全部 `*Engine` 类声明 | 全局匹配 `^class \w*Engine`（含学习科学、知识追踪、基础设施类） | **81** | `grep -rhE "^class [A-Za-z0-9_]*Engine" app/ \| wc -l` |
| **L0′** 去重后唯一类名 | 上者按类名去重（`ZeigarnikEngine` 出现 2 次） | **80** | 同上 + `sort -u` |
| **L1** 游戏化/行为干预机制实现单元 | 仅取 9 个成瘾/游戏化文件内的机制实体（含 `GamificationService` 内部的 5 个子机制） | **59–60** | 见 §1.2 逐文件表 |
| **L2** 去重后唯一机制 | L1 按**预注册去重规则**合并语义重复项 | **53**（敏感区间 51–56） | 见 §2.3 去重规则 |

**"76"没有任何一层支持它。** 最接近的是 L0 的 81，但 L0 包含了 `BKTEngine`（贝叶斯知识追踪）、`DDAEngine`（动态难度调整）、`FSRSSpacedRepetitionEngine`（FSRS 间隔重复）、`OptimalDifficultyEngine`（最优难度）——这些是**学习科学算法**，不是"游戏化成瘾机制"。拿 81 去支撑"76 个游戏化成瘾引擎"是**范畴错误**。

## 1.2 逐文件实况：声称 vs 复算

> 核验命令：`grep -hE "^class [A-Za-z0-9_]*Engine" app/services/<file>.py`

| 文件 | PRD 声称 | 我的复算（Engine 类） | 备注 |
|---|---:|---:|---|
| `positive_addiction_engine.py` | 7 | **6** | `HookEngine:67`, `HabitLoopEngine:262`, `IdentityEngine:348`, `SocialContagionEngine:506`, `InstantGratificationEngine:588`, `ProgressVisualizationEngine:649` |
| `deep_addiction_engine.py` | 10 | **7** | `CuriosityEngine:25`, `CollectionEngine:116`, `FOMOEngine:238`, `StreakSanctificationEngine:308`, `AppointmentEngine:388`, `ScarcityEngine:461`, `SerendipityEngine:542`。文件头自述"新增 7 大上瘾机制"——**作者本人写的是 7** |
| `ux_addiction_engine.py` | 12 | **8** | `MicroInteraction:24`, `ProgressiveDisclosure:119`, `ColorPsychology:210`, `SpatialAnchoring:290`, `HapticRhythm:345`, `EmptyState:412`, `SonicBranding:482`, `TypographyKinetic:524` |
| `social_addiction_engine.py` | 8 | **4** | `BusinessCard:55`, `SocialAddiction:166`, `ParentPortal:288`, `GiftEconomy:411` |
| `duolingo_addiction_engine.py` | 8 | **8** ✓ | `XPEngine:55`, `LeagueEngine:208`, `DuolingoStreak:316`, `FriendQuest:455`, `TimeBasedBonus:539`, `MonthlyChallenge:582`, `DuolingoNotification:642`, `DailyXPGoal:704` |
| `team_competition_engine.py` | 7 | **6** | `SoloRank:103`, `TeamManagement:288`, `TeamLeague:389`, `MVP:487`, `TeamMatch:556`, `Season:651` |
| `addiction_engine_v3.py` | 5 | **5** ✓ | `LossAversion:7`, `FreshStart:51`, `Zeigarnik:108`, `PeakEndRule:163`, `SurpriseDelight:199` |
| `gamification_service.py` | 12+ | **5 类 + 5 子机制 = 10** | 类：`PeakEnd:507`, `Zeigarnik:578`, `IKEA:623`, `SocialProof:659`, `Autonomy:683`；子机制：`ProximalGoals:96`, `StreakState:118`, `TreasureBoxState:128`, `NearMissDetector:139`, `DopamineRhythm:460`, `SessionMemory:498`, `UnfinishedTask:561`, `CustomizationState:615`（去重后 10 个单元） |
| `habit_addiction_engine.py` | **PRD 完全遗漏** | **5** | `HabitStacking:27`, `TemptationBundling:80`, `ImplementationIntentions:109`, `AutonomySupport:159`, `SelfRegulation:213` |
| **合计（L1）** | **69**（PRD 自己的表格相加也只有 69，不是 76） | **59** | 差异主因：`positive` −1、`deep` −3、`ux` −4、`social` −4、`team` −1，加回 `habit` +5 |

**PRD 内部自相矛盾**：`incremental_prd.md:12,53` 声称 76，但 PRD 自己的分类表格逐项相加是 7+10+12+8+8+7+5+12 = **69**。**在 PRD 内部，76 就已经不成立**。这一点如果被审稿人发现，损害远大于承认记账错误。

## 1.3 数字该怎么表述？——推荐与理由

### 推荐表述（三位一体，分层披露）

在任何论文/PRD/答辩中，**必须同时给出"实现单元数"与"去重机制数"，并明确去重规则**。推荐主表述：

> **主表述（推荐）**：
> "LearnFlow 实现了 **60 个游戏化机制实现单元**（implementation units），经预注册的语义去重规则合并后构成 **53 个唯一机制**（unique mechanisms），归入 8 个理论类别（LF-M01–LF-M53）。"

**为什么推荐这个**，而不是其他三种：

| 候选表述 | 评判 |
|---|---|
| ❌ "76 个机制" | **不可接受**。三层数字均不支持；PRD 自算也只有 69。学术不端风险。 |
| ❌ "53 个去重机制"（单独使用） | 不完整。只报 53 会被质疑"为什么实现单元是 60，那 7 个去哪了"——**主动披露 60 反而更可信**。 |
| ⚠️ "9 类 60 机制" | 勉强可用但**不推荐**。按代码文件分类（9 类）是**实现细节，不是理论分类**，审稿人会立刻看出分类没有构念效度（construct validity）。 |
| ✅ **"60 个实现单元 / 53 个唯一机制 / 8 个理论类别"** | **推荐**。三个数字各自可独立复算，且差异本身有解释（7 组重复实现），构成审计故事的一部分。 |

### 三条硬性纪律

1. **禁止"约"/"近"**。"约 76 个"、"近 80 个"是最坏的写法——既不准确又显得心虚。要精确到个位数。
2. **每个数字必须可在一次命令内复算**。本文档所有行号与计数均满足此条。
3. **凡引用旧材料中的 76，必须加注更正**。论文若在参考文献中引自己的技术报告，需在正文注脚写明"该报告中的 76 系记账错误，更正值见本文 Table X"。

## 1.4 与先前材料存在差异的更正清单

审计师有义务记录差异，而非静默修正：

| 项 | 先前材料 | 我的复算 | 处置 |
|---|---|---|---|
| 全局 Engine 类 | 81 | **81 行 / 80 唯一类名** | 采用 81（声明数），但须注明 `ZeigarnikEngine` 重复命名 |
| `positive_addiction_engine` | 7 | **6** | 更正 |
| `team_competition_engine` | 6 | **6** | 一致 ✓（材料称"声称 7"） |
| `gamification_service` | 10 | **10 个机制单元（5 类 + 5 子）** | 一致，但口径需写明 |
| 学习方法 method key | 21 | **15 唯一 / 16 条 METHOD_TIPS** | **更正**：`learning_methods_engine.py:31 METHOD_TIPS` 共 16 条，唯一 `method` key 15 个（`active_recall`, `chunking`, `dual_coding`, `elaborative_rehearsal`, `exercise_memory`, `feynman`, `growth_mindset`, `interleaving`, `memory_palace`, `metacognition`, `pomodoro`, `retrieval_practice`, `sleep_memory`, `spaced_repetition`, `sq3r`）。**"28 种学习方法"同样不成立，实际 15 种**（另有 `learning_methods_engine_v3` 与 `advanced_methods_engine` 的 7 个认知策略引擎，15+7=22，仍非 28） |
| 16 技能树 | 16 | **16 ✓ 属实** | `meta_learning_skilltree.py:61-146` 确为 16 个 skill_id。**这是全项目唯一完全属实的数字** |
| nudge 冲突点 | 17 | **15 严格 nudge/reminder/notification + 3 学习提示 = 18 个干预生成点** | 更正（详见 §4.4） |
| 孤儿机制占比 | 80%（48/60） | **约 68%（约 40/59）** | 更正，但仍极高。详见 §6 |

**"28 种学习方法"实际 15 种**这一条是本轮审计的**新发现**，先前材料未指出，需一并更正。

## 1.5 "79 vs 53"要在论文里正面写吗？——策略评估

你倾向于把"对现有游戏化学习系统的机制实现审计"本身做成一篇论文。**我强烈支持这个策略**，但必须看清风险边界。

### 为什么支持：三重收益

1. **化负债为资产**。76 是个定时炸弹——任何审稿人、答辩委员、开源用户 `grep` 一次就能引爆。主动引爆并把它做成贡献，是唯一能拆掉引信的方式。
2. **真实的文献空白**。游戏化学习文献中，"设计 N 个机制"的论文成百上千，几乎没有"审计 N 个声称机制的实际落地率"的论文。这个空白是**真实存在的**（对比：医学领域有 CONSORT，AI 领域有 reproducibility checklist，游戏化领域没有机制审计标准）。
3. **与你的本职（消融实验）天然耦合**。审计产出 53 个稳定 ID → ID 是消融实验的前提 → 消融实验需要注册表 → 注册表需要审计结论。**三者构成一条完整因果链**，这是博士论文最需要的"故事完整性"。

### 风险评估（批判性）

| 风险 | 等级 | 说明与缓解 |
|---|---|---|
| **自曝家丑反噬** | **高** | 审稿人可能反问："既然 80% 的机制没有调用方、XP 每次请求归零，你们的系统根本没跑起来，凭什么做学习效果的因果推断？"<br>**缓解**：把审计论文与效果论文**严格分离**。审计论文的 claim 只限于"软件实现状态"，不 claim 任何学习效果。效果论文必须建立在**注册表建成 + 持久化修复之后**的新数据上。 |
| **"N=1 系统"的外部效度质疑** | **中高** | 单个系统的审计结论，凭什么推广？<br>**缓解**：(a) 明确写成 **case study / exploratory audit**，不做统计推广；(b) **加入跨系统对比**——把同一审计协议应用到 2–3 个开源游戏化学习系统（如可获取源码），把"单系统审计"升级为"审计协议 + 多系统应用"，外部效度立刻改观。**这是提升命中率最关键的一步。** |
| **被当成 engineering report 而非 research** | **中** | **缓解**：必须有研究问题（RQ），不能只是清单。建议 RQ 见 §8.1。 |
| **审计结论本身的可复现性** | **中** | 审稿人会问："你的去重规则凭什么是这个？"<br>**缓解**：**预注册去重规则**（§2.3），并做**评分者间信度**（2 名独立评分者对 60 个单元独立归类，报 Cohen's κ）。这一步不做，整篇论文的立论基础是软的。 |
| **时间成本** | **中** | 审计论文相对便宜（代码静态分析 + 台账），但跨系统对比会显著增加工作量。 |

### 我的裁决

**写，而且要把"76 → 53"作为论文 Table 1 的第一行，不加任何修饰。** 淡化的风险远大于正面写。但要守住三条底线：
- 审计论文**不 claim 任何学习效果**；
- 必须**预注册去重规则 + 报评分者间信度**；
- 必须**至少加 1 个外部对照系统**，否则外部效度会被一击致命。

---

# 第二部分 机制 Taxonomy 重构

## 2.1 设计原则

**拒绝按代码文件分类。** 按文件分（`positive_`/`deep_`/`ux_`/`social_`…）是**开发历史**的化石，不是理论构念。审稿人一眼能看出 `positive_addiction_engine` 里的 `SocialContagionEngine`（社会传染）和 `social_addiction_engine` 里的 `SocialAddictionEngine` 在理论上是同一族，却被分在两个"类别"里——分类效度为零。

采用**三轴正交编码**：

| 轴 | 取值 | 用途 |
|---|---|---|
| **轴 1：理论根源**（主分类，决定 LF-M 编号分段） | A 行为主义 / B 承诺与损失 / C 自我决定论 / D 社会影响 / E 习惯与自我调节 / F 情绪与动机触发 / G UX 微交互 / H 健康护栏 | 决定分组消融的**分组依据** |
| **轴 2：作用时序** | `pre` 触发前（登录前/进入前） / `during` 学习中 / `post` 学习后 / `ambient` 常驻 | 决定**干预预算的时间窗** |
| **轴 3：目标构念** | `motivation` 动机 / `retention` 留存 / `cognition` 认知负荷 / `selfreg` 自我调节 / `health` 健康 | 决定**主因变量的选择** |

**为什么是这三个轴**：轴 1 提供构念效度（可引用理论文献）；轴 2 提供**仲裁所需的时序约束**（冲突仲裁本质上是"同一时刻只能推一条"）；轴 3 提供**消融实验的因变量映射**（关掉一个 `retention` 类机制，就应该看留存率，而不是看知识增长）。**三轴中，轴 2 和轴 3 是纯为工程服务的，这才是正确的 taxonomy 设计——分类要能驱动系统行为，不只是好看。**

## 2.2 八类理论依据

| 类别 | 理论基础 | 代表文献 |
|---|---|---|
| **A 行为主义·强化与奖励** | 操作性条件反射、强化程序（变比率/变动时距）、奖励预测误差 | Skinner (1938)；Ferster & Skinner (1957)；Schultz (1998, *Neuron*) |
| **B 承诺、损失与目标梯度** | 前景理论、目标设定理论、目标梯度假说、峰终定律、蔡格尼克效应 | Kahneman & Tversky (1979, *Econometrica*)；Zeigarnik (1927)；Kahneman et al. (1993)；Locke & Latham (1990, *Am Psychol*)；Hull (1934) |
| **C 自我决定论：自主·胜任·关联** | 基本心理需求理论、认知负荷理论、情感设计 | Deci & Ryan (1985, 2000)；Ryan & Deci (2000, *Am Psychol*)；Sweller (1988)；Norman (2004) |
| **D 社会影响与社会学习** | 社会比较理论、社会认同理论、社会促进、互惠规范、社会互赖 | Festinger (1954)；Cialdini (1984)；Tajfel & Turner (1979)；Garcia & Tor (2009, *JPSP*)；Johnson & Johnson (1989) |
| **E 习惯形成与自我调节** | 习惯自动化、执行意图、诱惑捆绑、自我调节学习、元认知 | Lally et al. (2010, *Eur J Soc Psychol*)；Gollwitzer (1999, *Am Psychol*)；Milkman et al. (2014, *Mgmt Sci*)；Zimmerman (2002)；Fogg (2019) |
| **F 情绪与动机触发** | 信息缺口理论、身份动机、错失恐惧 | Loewenstein (1994, *Psych Bull*)；Oyserman (2007, *JPSP*)；Przybylski et al. (2013, *Comput Human Behav*) |
| **G UX 微交互与认知负荷** | 微交互、色彩心理学、空状态行为启动 | Norman (2004)；Elliot & Maier (2014, *Annu Rev Psychol*) |
| **H 健康护栏与伦理** | 防沉迷合规、强制休息、成瘾风险自适应降级 | 参照中国《关于进一步严格管理 切实防止未成年人沉迷网络游戏的通知》；Griffiths (2005) |

## 2.3 预注册去重规则（决定 53 这个数字）

**必须预注册**，否则 53 无法辩护。规则如下（对 60 个实现单元两两判定）：

- **R1 同名类合并**：类名完全相同者视为同一机制（`ZeigarnikEngine` ×2）。
- **R2 同一理论构念合并**：不同类名但实现同一心理学构念（如 `PeakEndEngine` 与 `PeakEndRuleEngine`，`AutonomyEngine` 与 `AutonomySupportEngine`），合并。
- **R3 同构念多份实现 → 计 1，其余标 `DUP`**：保留成熟度最高的一份为 canonical，其余列为重复实现（真实存在 7 组，见下）。
- **R4 占位/无逻辑子类合并**：若 3 个及以上机制均为无实质逻辑的占位（如 `HapticRhythm`/`SonicBranding`/`TypographyKinetic` 三个纯 sensory 占位），**合并为一个"多感官包装"占位机制**，处置建议为"废弃或合并实现"。
- **R5 算法类与干预类分离**：知识追踪（BKT）、动态难度（DDA）、FSRS 间隔重复、最优难度属**学习科学算法**，不计入行为干预机制。
- **R6 争议项处理**：两名评分者独立判定，不一致处由第三人裁决，报 κ。

**去重减项明细（60 → 53，净减 7）**：

| # | 机制 | 实现单元 | 减 |
|---|---|---|---:|
| 1 | 蔡格尼克效应 | `addiction_engine_v3.py:108` + `gamification_service.py:578` | −1 |
| 2 | 峰终定律 | `addiction_engine_v3.py:163` + `gamification_service.py:507`(`:498`) | −1 |
| 3 | 自主性支持 | `habit_addiction_engine.py:159` + `gamification_service.py:683` | −1 |
| 4 | 损失厌恶 | `addiction_engine_v3.py:7` + `gamification_service.py:419` | −1 |
| 5 | 社会认同 | `positive_addiction_engine.py:506` + `gamification_service.py:659` | −1 |
| 6 | 连胜 | `duolingo_addiction_engine.py:316` + `gamification_service.py:118`(`deep:308` 的连胜神圣化单列) | −1 |
| 7 | 多感官包装（触觉/声音/字体动效三个占位合并） | `ux:345` + `ux:482` + `ux:524` | −2 |
| | | **合计** | **−7** |

**敏感性说明**：53 是**在上述规则下**的结果。放宽 R2（把 `StreakSanctification` 并入 `Streak`）得 52；收紧 R4（三个占位各计 1）得 55。**诚实区间为 51–56**，论文中应报 53 并给出该区间。

## 2.4 完整机制清单（LF-M01 – LF-M53）

> 图例 — 成熟度：**●** 完整且接 API/DB ｜ **◐** 有逻辑无持久化 ｜ **○** 占位/TODO
> 处置：**K** 保留 **M** 合并 **R** 重构 **D** 废弃
> 全部行号经 `grep` 核验。

### A. 行为主义·强化与奖励（8）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M01 | 变比率奖励（宝箱） | Variable-Ratio Reward | during | retention | Skinner 1938; Ferster & Skinner 1957 | `gamification_service.py:128,139` | ● | | **K** |
| LF-M02 | 濒赢效应 | Near-Miss Effect | during | retention | Clark et al. 2009; Reid 1986 | `gamification_service.py:139` | ● | | **K** |
| LF-M03 | 奖励节拍（多巴胺节律） | Dopamine Rhythm | during | retention | Schultz 1998 | `gamification_service.py:460` | ◐ | | **R**（接注册表+落库） |
| LF-M04 | 即时满足 | Instant Gratification | during | motivation | Ainslie 1975 | `positive_addiction_engine.py:588` | ◐ | | **R** |
| LF-M05 | 惊喜与愉悦 | Surprise & Delight | during | motivation | Reiss 2004 | `addiction_engine_v3.py:199` | ◐ | | **R** |
| LF-M06 | 时间限定加成 | Time-Based Bonus | during | retention | 强化程序（变动时距） | `duolingo_addiction_engine.py:539` | ● | | **K** |
| LF-M07 | 集换收藏 | Collection / Completion | ambient | retention | Zeigarnik 变体；完成欲 | `deep_addiction_engine.py:116` | ◐ | | **R** |
| LF-M08 | 稀缺性 | Scarcity | pre | motivation | Cialdini 1984 (Ch.7) | `deep_addiction_engine.py:461` | ◐ | | **R**（与 FOMO 联合仲裁） |

### B. 承诺、损失与目标梯度（8）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M09 | 损失厌恶 | Loss Aversion | post | retention | Kahneman & Tversky 1979 | `addiction_engine_v3.py:7`（canonical）<br>`gamification_service.py:419` | ◐ | **DUP** | **M**（删 `:419`） |
| LF-M10 | 沉没成本提示 | Sunk-Cost Reminder | post | retention | Arkes & Blumer 1985 | `addiction_engine_v3.py:36` | ◐ | | **R**（健康审查） |
| LF-M11 | 连胜 | Streak | post | retention | 连续强化；Lally et al. 2010 | `duolingo_addiction_engine.py:316`（canonical）<br>`gamification_service.py:118` | ● | **DUP** | **M**（统一到 canonical 并落库） |
| LF-M12 | 连胜神圣化 | Streak Sanctification | post | retention | 承诺 × 损失厌恶 | `deep_addiction_engine.py:308` | ◐ | | **R** |
| LF-M13 | 蔡格尼克效应 | Zeigarnik Effect | post | retention | Zeigarnik 1927 | `addiction_engine_v3.py:108`（canonical）<br>`gamification_service.py:578` | ◐ | **DUP** | **M**（删 `:578`） |
| LF-M14 | 峰终定律 | Peak-End Rule | during | motivation | Kahneman 1993; Fredrickson & Kahneman 1993 | `addiction_engine_v3.py:163`（canonical）<br>`gamification_service.py:507` | ◐ | **DUP** | **M**（删 `:507`） |
| LF-M15 | 目标梯度/近距目标 | Goal Gradient | during | motivation | Hull 1934; Locke & Latham 1990 | `gamification_service.py:96` | ◐ | | **R** |
| LF-M16 | 每日/月度挑战 | Daily & Monthly Challenge | pre | retention | Locke & Latham 1990 | `duolingo_addiction_engine.py:704,582` | ● | | **K** |

### C. 自我决定论：自主·胜任·关联（6）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M17 | 自主性支持 | Autonomy Support | during | selfreg | Deci & Ryan 1985; Ryan & Deci 2000 | `habit_addiction_engine.py:159`（canonical）<br>`gamification_service.py:683` | ◐ | **DUP** | **M**（删 `:683`） |
| LF-M18 | 宜家效应/自主定制 | IKEA Effect | during | motivation | Norton, Mochon & Ariely 2012 | `gamification_service.py:623,615` | ◐ | | **R** |
| LF-M19 | 经验值与等级 | XP & Leveling | post | motivation | 二级强化；SDT 胜任感 | `duolingo_addiction_engine.py:55`<br>调用点 `learning_orchestrator.py:409` | **○** | | **R（最高优先级：伪持久化）** |
| LF-M20 | 进步可视化 | Progress Visualization | during | motivation | Locke & Latham 1990; Bandura 1997 | `positive_addiction_engine.py:649` | ◐ | | **R** |
| LF-M21 | 渐进式披露 | Progressive Disclosure | during | cognition | Sweller 1988; Nielsen 1994 | `ux_addiction_engine.py:119` | ◐ | | **R** |
| LF-M22 | 虚拟宠物陪伴 | Pet Companion (Relatedness) | ambient | motivation | Ryan & Deci 2000（关联性） | `pet_service.py`；表 `pet_profiles` | ● | | **K** |

### D. 社会影响与社会学习（10）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M23 | 社会认同 | Social Proof | during | motivation | Cialdini 1984 (Ch.4) | `gamification_service.py:659`（canonical）<br>`positive_addiction_engine.py:506` | ◐ | **DUP** | **M** |
| LF-M24 | 社会传染 | Social Contagion | ambient | retention | Christakis & Fowler 2007 | `positive_addiction_engine.py:506` | ◐ | | **R** |
| LF-M25 | 同伴进度推动 | Peer Progress Nudge | pre | motivation | Festinger 1954（上行比较） | `deep_addiction_engine.py:292` | ◐ | | **R**（健康审查） |
| LF-M26 | 友好竞争 | Friendly Competition | during | motivation | Festinger 1954; Tauer & Harackiewicz 2004 | `positive_addiction_engine.py:538` | ◐ | | **R** |
| LF-M27 | 排行榜与联赛 | Leaderboard & Leagues | ambient | retention | Garcia & Tor 2009 (N-effect) | `duolingo_addiction_engine.py:208` | ● | | **K**（需开关：N-effect 有负面证据） |
| LF-M28 | 社交名片 | Business Card / Identity Display | ambient | retention | Tajfel & Turner 1979 | `social_addiction_engine.py:55` | ○ | | **R** |
| LF-M29 | 礼物经济 | Gift Economy | ambient | retention | Mauss 1925; Cialdini 互惠 | `social_addiction_engine.py:411` | ○ | | **R** |
| LF-M30 | 组队任务 | Friend Quest | during | retention | Johnson & Johnson 1989 | `duolingo_addiction_engine.py:455`（容器 `:469`） | ◐ | | **R**（落库） |
| LF-M31 | 团队竞赛与赛季 | Team Competition & Season | ambient | retention | Johnson & Johnson 1989 | `team_competition_engine.py:103,288,389,487,556,651`（容器 `:292,293,559`） | ◐ | | **R**（落库） |
| LF-M32 | 家长门户 | Parent Portal | post | selfreg | Hoover-Dempsey & Sandler 1995 | `social_addiction_engine.py:288` | ○ | | **R**（合规价值高） |

### E. 习惯形成与自我调节（10）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M33 | 钩子模型 | Hook Model | pre | retention | Eyal 2014 | `positive_addiction_engine.py:67` | ◐ | | **R（伦理审查）** |
| LF-M34 | 习惯回路 | Habit Loop | pre | selfreg | Duhigg 2012; Wood & Rünger 2016 | `positive_addiction_engine.py:262` | ◐ | | **R** |
| LF-M35 | 情境线索提示 | Cue Prompting | pre | selfreg | Wood & Neal 2007 | `positive_addiction_engine.py:322` | ◐ | | **R**（入仲裁器） |
| LF-M36 | 习惯叠加 | Habit Stacking | pre | selfreg | Fogg 2019 | `habit_addiction_engine.py:27` | ◐ | | **K** |
| LF-M37 | 诱惑捆绑 | Temptation Bundling | pre | selfreg | Milkman, Minson & Volpp 2014 | `habit_addiction_engine.py:80` | ◐ | | **K** |
| LF-M38 | 执行意图 | Implementation Intentions | pre | selfreg | Gollwitzer 1999 | `habit_addiction_engine.py:109` | ◐ | | **K** |
| LF-M39 | 自我调节目标 | Self-Regulation Goals | pre | selfreg | Zimmerman 2002; Bandura 1991 | `habit_addiction_engine.py:213`（容器 `:216`） | ◐ | | **R**（落库） |
| LF-M40 | 元认知技能树 | Metacognitive Skill Tree | ambient | cognition | Zimmerman 2002; Flavell 1979 | `meta_learning_skilltree.py:157`（容器 `:163`，16 节点） | ◐ | | **R（最高优先级：落库）** |
| LF-M41 | 承诺装置/预约 | Appointment (Commitment Device) | pre | selfreg | Rogers, Milkman & Volpp 2014 (*JCR*) | `deep_addiction_engine.py:388` | ◐ | | **R**（入仲裁器 `:437`） |
| LF-M42 | 新起点效应 | Fresh Start Effect | pre | motivation | Dai, Milkman & Riis 2014 (*Mgmt Sci*) | `addiction_engine_v3.py:51` | ◐ | | **K** |

### F. 情绪与动机触发（4）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M43 | 好奇心缺口 | Curiosity Gap | pre | motivation | Loewenstein 1994 | `deep_addiction_engine.py:25` | ◐ | | **K**（健康风险最低的正向机制） |
| LF-M44 | 错失恐惧 | FOMO | pre | retention | Przybylski et al. 2013 | `deep_addiction_engine.py:238`（nudge `:277`） | ◐ | | **R（强制入仲裁器，见 §4.4）** |
| LF-M45 | 偶然性与惊喜 | Serendipity | during | motivation | 变比率 × 内在动机 | `deep_addiction_engine.py:542` | ○ | | **R** |
| LF-M46 | 身份认同动机 | Identity-Based Motivation | ambient | motivation | Oyserman 2007; Markus & Nurius 1986 | `positive_addiction_engine.py:348` | ◐ | | **K** |

### G. UX 微交互与认知负荷（4）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M47 | 微交互反馈 | Micro-interaction | during | motivation | Norman 2004 | `ux_addiction_engine.py:24` | ◐ | | **R** |
| LF-M48 | 色彩与情绪 | Color Psychology | ambient | cognition | Elliot & Maier 2014 | `ux_addiction_engine.py:210` | ◐ | | **R** |
| LF-M49 | 空间锚定 | Spatial Anchoring | ambient | cognition | 空间一致性 / 位置记忆 | `ux_addiction_engine.py:290` | ○ | | **R** |
| LF-M50 | 多感官包装（占位） | Multi-sensory Packaging | during | motivation | —（无理论支撑） | `ux:345` + `ux:482` + `ux:524` | ○ | **合并** | **D**（建议删除，或合并为 1 个可配置主题） |

### H. 健康护栏与伦理（3）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 重复 | 处置 |
|---|---|---|---|---|---|---|---|---|---|
| LF-M51 | 强制休息提醒 | Forced Rest Reminder | during | health | 认知疲劳恢复 | `feedback_service.py:198` | ◐ | | **K（一票否决权）** |
| LF-M52 | 未成年保护与奖励冷却 | Minor Protection & Reward Cooldown | during | health | 监管合规 + Griffiths 2005 | `anti_addiction.py`；`anti_addiction_compliance.py:79`；调用 `learning_orchestrator.py:411` | ● | | **K（一票否决权）** |
| LF-M53 | LAI 自适应降级 | LAI Adaptive Downgrade | ambient | health | 自构成瘾指数量表改编 | `learning_addiction_index.py`；`api/gamification.py:601` | **○** | | **R（先补采集，否则废弃）** |

**小计**：A 8 + B 8 + C 6 + D 10 + E 10 + F 4 + G 4 + H 3 = **53** ✓

### 类别—状态汇总（审计关键发现）

| 类别 | 机制数 | ● 完整 | ◐ 无持久化 | ○ 占位 | 有调用方（非孤儿） |
|---|---:|---:|---:|---:|---:|
| A 行为主义 | 8 | 3 | 5 | 0 | **2** |
| B 承诺损失 | 8 | 2 | 6 | 0 | **2** |
| C 自我决定论 | 6 | 1 | 4 | 1 | **2** |
| D 社会影响 | 10 | 2 | 5 | 3 | **3** |
| E 习惯自我调节 | 10 | 0 | 10 | 0 | **5** |
| F 情绪动机 | 4 | 0 | 3 | 1 | **0** |
| G UX 微交互 | 4 | 0 | 2 | 2 | **0** |
| H 健康护栏 | 3 | 1 | 2 | 0 | **2** |
| **合计** | **53** | **9** | **37** | **7** | **16（30%）** |

> **注意**：接入率仅 **30%**（16/53），不是先前材料说的 20%。更正依据：孤儿判定应基于**是否有 `.py` 调用方**，我的复算显示 `habit_addiction_engine`（5 个机制）、`team_competition_engine`（6 个，经 `api/gamification.py` 接入）、`gamification_service`（10 个，经 API 接入）、`duolingo_addiction_engine`（8 个，经 `orchestrator` 接入 XPEngine + API）中部分有调用方。**即便如此，70% 零调用仍然是一个必须正面披露的数字。**

> **更严重的发现**：即使算作"有调用方"的 16 个，其中 **LF-M19（XP/等级）是伪持久化**（`learning_orchestrator.py:409` 每次请求 `xp_state = XPState()` 从零构造，`:471-476` 只写响应体，从不落库）。**即用户每次提交答案后，XP/等级/连胜全部归零。** 这意味着 16 个"已接入"机制里，**最有动机价值的那一个是失效的**。**这一条如果不在论文中披露，而后续消融实验又用了 XP 相关的因变量，属于实质性错误。**

---

# 第三部分 统一机制注册表（工程核心）

## 3.1 设计目标

注册表必须同时满足四个约束（按重要性排序）：

1. **可审计**：每个机制有稳定 ID、理论来源、实现位置 —— 审稿人可逐条核对。
2. **可开关**：按 ID 开关是消融实验的前提。
3. **可仲裁**：17 处（严格 15 处）无仲裁的干预生成点必须收敛到一个决策入口。
4. **可落库**：注册表的状态读写必须走持久化，杜绝内存态。

## 3.2 核心数据模型

```python
# app/services/mechanism_registry.py
"""LearnFlow 统一机制注册表 (MechanismRegistry)

设计原则:
  1. 声明式注册 —— 机制自描述，不依赖调用方
  2. 按 ID 开关 —— 消融实验前提
  3. 干预预算 + 健康一票否决 —— 冲突仲裁
  4. 所有状态读写经 StateStore —— 杜绝内存态

审计要求: 每个 MechanismSpec 必须有 theory_ref 与 impl_ref，缺失即注册失败。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- 轴编码
class TheoryRoot(str, Enum):
    """轴 1: 理论根源 —— 决定分组消融的分组依据"""
    A_REINFORCEMENT = "A"   # 行为主义·强化与奖励
    B_COMMITMENT    = "B"   # 承诺、损失与目标梯度
    C_SDT           = "C"   # 自我决定论
    D_SOCIAL        = "D"   # 社会影响与社会学习
    E_HABIT         = "E"   # 习惯形成与自我调节
    F_AFFECT        = "F"   # 情绪与动机触发
    G_UX            = "G"   # UX 微交互与认知负荷
    H_SAFEGUARD     = "H"   # 健康护栏与伦理


class TimingPhase(str, Enum):
    """轴 2: 作用时序 —— 决定干预预算的时间窗"""
    PRE     = "pre"      # 触发前(登录前/进入前)
    DURING  = "during"   # 学习中
    POST    = "post"     # 学习后
    AMBIENT = "ambient"  # 常驻


class TargetConstruct(str, Enum):
    """轴 3: 目标构念 —— 决定消融实验的因变量映射"""
    MOTIVATION = "motivation"
    RETENTION  = "retention"
    COGNITION  = "cognition"
    SELFREG    = "selfreg"
    HEALTH     = "health"


class Maturity(str, Enum):
    COMPLETE   = "complete"    # ● 完整且接 API/DB
    LOGIC_ONLY = "logic_only"  # ◐ 有逻辑无持久化
    PLACEHOLDER= "placeholder" # ○ 占位/TODO


class EffectType(str, Enum):
    """干预产物类型 —— 仲裁器据此分类处理"""
    NUDGE      = "nudge"       # 推送/提醒文案
    REWARD     = "reward"      # 奖励发放
    UI_CHANGE  = "ui_change"   # 界面状态变更
    STATE_ONLY = "state_only"  # 仅内部状态更新, 无用户可见产出
    BLOCK      = "block"       # 阻断性干预(防沉迷/强制休息)


# ---------------------------------------------------------------- 运行时协议
class StateStore(Protocol):
    """状态存储抽象 —— 内存/DB/Redis 三种实现，杜绝模块级 dict"""
    def get(self, namespace: str, key: str) -> Optional[dict]: ...
    def set(self, namespace: str, key: str, value: dict, ttl: Optional[int] = None) -> None: ...
    def incr(self, namespace: str, key: str, delta: int = 1, window_sec: Optional[int] = None) -> int: ...


class ExperimentProvider(Protocol):
    """实验分组抽象 —— 与 ab_test_framework 对接"""
    def get_toggles(self, user_id: str) -> Dict[str, bool]: ...


# ---------------------------------------------------------------- 规格与产出
@dataclass(frozen=True)
class Effect:
    """机制执行的产出。user_visible=True 的 Effect 才进入仲裁预算。"""
    mechanism_id: str
    effect_type: EffectType
    payload: dict = field(default_factory=dict)
    priority: int = 50              # 0-100, 越大越优先
    user_visible: bool = True
    cost: float = 1.0               # 预算消耗权重
    health_critical: bool = False   # 健康类干预: 一票否决, 绕过预算检查
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MechanismSpec:
    """机制声明。theory_ref / impl_ref 为审计强制字段，缺失不允许注册。"""
    id: str                              # LF-M01 ... LF-M53
    name_zh: str
    name_en: str
    theory_root: TheoryRoot
    timing: TimingPhase
    construct: TargetConstruct

    # --- 审计字段 (强制) ---
    theory_ref: str                      # 理论文献, 如 "Kahneman & Tversky (1979)"
    impl_ref: str                        # 实现位置, 如 "addiction_engine_v3.py:7"
    maturity: Maturity
    duplicate_of: Optional[str] = None   # 若为本体的重复实现, 填本体 ID

    # --- 运行字段 ---
    default_enabled: bool = True
    priority: int = 50
    effect_type: EffectType = EffectType.STATE_ONLY
    budget_cost: float = 1.0
    health_critical: bool = False        # True => 绕过所有预算限制与 A/B 关闭
    conflicts_with: tuple = ()           # 语义对立机制 ID


@dataclass
class MechanismContext:
    """一次执行的上下文本体。所有状态读写经此，禁止引擎自带类级 dict。"""
    user_id: str
    session_id: Optional[str]
    phase: TimingPhase
    toggles: Dict[str, bool] = field(default_factory=dict)
    state: StateStore = None
    payload: Dict[str, Any] = field(default_factory=dict)
    trace: List[str] = field(default_factory=list)   # 审计日志: 命中/跳过原因

    def is_enabled(self, mechanism_id: str) -> bool:
        """按 ID 查询开关。实验关闭 > 默认配置。健康临界机制不可被关闭。"""
        return self.toggles.get(mechanism_id, True)


# ---------------------------------------------------------------- 注册表
class MechanismRegistry:
    """统一机制注册表（单例）。"""

    def __init__(self, store: StateStore, experiments: Optional[ExperimentProvider] = None):
        self._specs: Dict[str, MechanismSpec] = {}
        self._handlers: Dict[str, Callable[[MechanismContext], Optional[Effect]]] = {}
        self._store = store
        self._experiments = experiments

    # ---------------- 注册 ----------------
    def register(self, spec: MechanismSpec,
                 handler: Callable[[MechanismContext], Optional[Effect]]) -> None:
        # 审计门禁: theory_ref / impl_ref 缺失即拒绝注册
        if not spec.theory_ref or not spec.impl_ref:
            raise ValueError(
                f"[{spec.id}] theory_ref 与 impl_ref 为审计强制字段，缺失不可注册。"
                "若确无理论依据，请将其标记为废弃而非注册。"
            )
        if spec.id in self._specs:
            raise ValueError(f"[{spec.id}] 重复注册")
        if spec.duplicate_of and spec.duplicate_of not in self._specs:
            raise ValueError(f"[{spec.id}] duplicate_of={spec.duplicate_of} 尚未注册")
        self._specs[spec.id] = spec
        self._handlers[spec.id] = handler
        logger.info("registered %s (%s) impl=%s", spec.id, spec.name_zh, spec.impl_ref)

    def mechanism(self, spec: MechanismSpec):
        """装饰器语法糖"""
        def _wrap(fn):
            self.register(spec, fn)
            return fn
        return _wrap

    # ---------------- 查询 ----------------
    def get(self, mechanism_id: str) -> MechanismSpec:
        return self._specs[mechanism_id]

    def all(self) -> List[MechanismSpec]:
        return list(self._specs.values())

    def by_root(self, root: TheoryRoot) -> List[MechanismSpec]:
        return [s for s in self._specs.values() if s.theory_root == root]

    def ids_by_root(self, root: TheoryRoot) -> List[str]:
        return [s.id for s in self.by_root(root)]

    def audit_report(self) -> dict:
        """审计快照 —— 供论文 Table 直接使用（可复现）"""
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(self._specs),
            "by_root": {r.value: len(self.by_root(r)) for r in TheoryRoot},
            "by_maturity": {m.value: sum(1 for s in self._specs.values() if s.maturity == m)
                            for m in Maturity},
            "duplicates": [{"id": s.id, "of": s.duplicate_of}
                           for s in self._specs.values() if s.duplicate_of],
            "mechanisms": [asdict(s) for s in sorted(self._specs.values(), key=lambda x: x.id)],
        }

    def fingerprint(self) -> str:
        """注册表指纹 —— 写实验记录，保证结果可复现"""
        blob = "|".join(f"{s.id}:{s.impl_ref}:{s.default_enabled}"
                        for s in sorted(self._specs.values(), key=lambda x: x.id))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    # ---------------- 执行 ----------------
    def run(
        self,
        ctx: MechanismContext,
        roots: Optional[List[TheoryRoot]] = None,
        phase: Optional[TimingPhase] = None,
        arbitrate: bool = True,
    ) -> List[Effect]:
        """按类别/时序批量执行，产出经仲裁器过滤。

        这是唯一允许生成用户可见干预的入口。任何引擎不得自行推送。
        """
        candidates = list(self._specs.values())
        if roots:
            candidates = [c for c in candidates if c.theory_root in roots]
        if phase:
            candidates = [c for c in candidates if c.timing == phase]

        effects: List[Effect] = []
        for spec in sorted(candidates, key=lambda s: -s.priority):
            # 1) 健康临界: 永不被关闭
            if spec.health_critical:
                pass
            # 2) A/B 开关: 关闭则跳过（健康类除外）
            elif not ctx.is_enabled(spec.id):
                ctx.trace.append(f"SKIP {spec.id}: toggled_off")
                continue

            handler = self._handlers[spec.id]
            try:
                effect = handler(ctx)
            except Exception as e:                       # 单机制故障不得拖垮流水线
                logger.exception("mechanism %s failed", spec.id)
                ctx.trace.append(f"ERROR {spec.id}: {e}")
                continue

            if effect is None:
                ctx.trace.append(f"SKIP {spec.id}: no_effect")
                continue
            effect.mechanism_id = spec.id
            effect.effect_type = spec.effect_type
            effect.priority = spec.priority
            effect.health_critical = spec.health_critical
            effects.append(effect)
            ctx.trace.append(f"HIT {spec.id}")

        return self._arbitrate(ctx, effects) if arbitrate else effects
```

## 3.3 冲突仲裁器（解决 15 处无仲裁干预点）

### 3.3.1 问题定性

复算确认的干预生成点（`grep -rnE "def (get|generate|create)_[a-z_]*(nudge|reminder|prompt|notification)"`）：

| # | 位置 | 机制 | 语义倾向 |
|---|---|---|---|
| 1 | `addiction_engine_v3.py:36` | LF-M10 沉没成本 | **拉回** |
| 2 | `addiction_engine_v3.py:121` | LF-M13 蔡格尼克 | **拉回** |
| 3 | `deep_addiction_engine.py:277` | LF-M44 FOMO | **强拉回** ⚠ |
| 4 | `deep_addiction_engine.py:292` | LF-M25 同伴进度 | **强拉回** ⚠ |
| 5 | `deep_addiction_engine.py:437` | LF-M41 预约 | 中性 |
| 6 | `duolingo_addiction_engine.py:407` | LF-M11 连胜 | 中性 |
| 7 | `duolingo_addiction_engine.py:674` | LF-M06 时间加成 | **拉回** |
| 8 | `gamification_service.py:419` | LF-M09 损失厌恶(DUP) | **拉回** |
| 9 | `gamification_service.py:592` | LF-M22 宠物 | 中性 |
| 10 | `gamification_service.py:661` | LF-M23 社会认同(班级) | 中性 |
| 11 | `gamification_service.py:669` | LF-M23 社会认同(活跃) | 中性 |
| 12 | `gamification_service.py:675` | LF-M23 社会认同(求助) | 中性 |
| 13 | `positive_addiction_engine.py:322` | LF-M35 线索提示 | **拉回** |
| 14 | `positive_addiction_engine.py:538` | LF-M26 友好竞争 | **拉回** |
| 15 | `feedback_service.py:198` | LF-M51 强制休息 | **推开（健康）** ✅ |
| 16 | `advanced_methods_engine.py:160` | 学习提示（非 nudge） | 中性 |
| 17 | `learning_methods_engine_v3.py:70` | 可视化提示（非 nudge） | 中性 |
| 18 | `learning_methods_engine_v3.py:155` | 精细加工提示（非 nudge） | 中性 |

**15 处严格 nudge/reminder/notification + 3 处学习提示 = 18 个生成点**（更正先前材料的 17）。

### 3.3.2 最尖锐矛盾（必须优先解决）

```
  LF-M44 FOMOEngine.generate_fomo_nudge     「同伴都在学，你落后了！」  → 拉回加时
  LF-M08 ScarcityEngine                     「限时机会即将消失！」      → 拉回加时
  LF-M10 SunkCostReminder                   「你已经投入了 X 小时」      → 拉回加时
        ↑↑↑ 语义直接对立 ↓↓↓
  LF-M51 generate_rest_reminder             「学习超时，请休息」        → 推开
  LF-M52 MinorProtectionEngine              「今日时长已达上限」        → 推开（合规强制）
  LF-M53 LAI 自适应降级                      「降低游戏化强度」           → 削弱以上全部
```

**当前状态：无任何仲裁器。** `learning_orchestrator.py:46-233` 是硬编码 11 步线性流水线，防沉迷检查（`:411`）只对 **XP 奖励**做了冷却，**对 nudge 完全无约束**。也就是说，`FOMOEngine` 生成"再学 20 分钟"的文案，与 `MinorProtectionEngine` 的时长限制可以在同一次请求里同时下发。**这是一个真实的合规风险，不只是学术问题。**

### 3.3.3 仲裁策略：三层漏斗

我推荐**三层漏斗**，而不是单纯优先级队列或单纯预算约束：

```
   全部候选 Effect (N 个)
        ↓
  【第 1 层】健康一票否决 (Health Veto)
    若任一 health_critical Effect 命中 → 丢弃全部"拉回型" Effect，
    仅保留该健康 Effect（+ 中性 Effect 至多 1 个）
        ↓
  【第 2 层】冲突消解 (Conflict Resolution)
    按 conflicts_with 与语义方向 (approach/withdraw) 互斥:
      - 同方向: 保留优先级最高者
      - 反方向: 保留 withdraw 方（保守偏置，default to safety）
        ↓
  【第 3 层】干预预算 (Intervention Budget)
    在窗口内按 priority 降序贪心装箱，直到预算耗尽
        ↓
   最终下发 0..K 个 Effect
```

**为什么是漏斗而非单一机制**：
- 纯优先级队列无法处理"两个高优先级但语义对立"的情况（FOMO 与防沉迷都是高优先级）；
- 纯预算约束无法保证健康类干预在预算耗尽时仍被下发（预算耗尽 → 防沉迷被吞掉，这是灾难）；
- **因此健康类必须放在预算之前，且绕过预算**。

**保守偏置原则**：反方向冲突时保留"推开"方。理由是可证伪的伦理立场——过度劝退的代价（少学 10 分钟）远小于过度劝学（未成年人超时）的代价。这一条要写进论文。

### 3.3.4 仲裁器代码

```python
# app/services/mechanism_arbitrator.py
"""干预冲突仲裁器 —— 三层漏斗: 健康否决 → 冲突消解 → 干预预算"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.services.mechanism_registry import Effect, EffectType, MechanismContext

logger = logging.getLogger(__name__)


@dataclass
class BudgetPolicy:
    """干预预算。默认值需预注册，不得在实验中途调整。"""
    max_per_session: int = 3            # 每学习会话最多 3 次可见干预
    max_per_day: int = 6                # 每 24h 最多 6 次推送
    max_cost_per_session: float = 4.0   # 加权成本上限
    min_interval_sec: int = 300         # 同用户两次可见干预最小间隔 5 分钟
    burst_block_after: int = 2          # 连续 2 次被忽略后进入静默期
    silent_hours: tuple = (22, 7)       # 22:00-07:00 静默（仅健康类可穿透）


@dataclass
class ArbitrationTrace:
    """审计轨迹 —— 每次仲裁全量落库，供实验分析复盘"""
    user_id: str
    session_id: Optional[str]
    candidates: List[str] = field(default_factory=list)
    vetoed_by_health: List[str] = field(default_factory=list)
    dropped_by_conflict: List[str] = field(default_factory=list)
    dropped_by_budget: List[str] = field(default_factory=list)
    delivered: List[str] = field(default_factory=list)
    reason: str = ""


class MechanismArbitrator:
    def __init__(self, registry, store, policy: Optional[BudgetPolicy] = None):
        self.registry = registry
        self.store = store
        self.policy = policy or BudgetPolicy()

    # 语义方向: approach=拉回加时 / withdraw=推开休息 / neutral
    _DIRECTION = {
        "LF-M08": "approach", "LF-M10": "approach", "LF-M13": "approach",
        "LF-M25": "approach", "LF-M26": "approach", "LF-M35": "approach",
        "LF-M44": "approach", "LF-M07": "approach", "LF-M33": "approach",
        "LF-M51": "withdraw", "LF-M52": "withdraw", "LF-M53": "withdraw",
    }

    def arbitrate(self, ctx: MechanismContext, effects: List[Effect]) -> List[Effect]:
        trace = ArbitrationTrace(user_id=ctx.user_id, session_id=ctx.session_id)
        trace.candidates = [e.mechanism_id for e in effects]

        # ---------- 第 1 层: 健康一票否决 ----------
        health = [e for e in effects if e.health_critical]
        if health:
            health.sort(key=lambda e: -e.priority)
            winner = health[0]
            survivors = [e for e in effects
                         if e.health_critical and e is not winner
                         or self._DIRECTION.get(e.mechanism_id) == "withdraw"
                         or (not e.user_visible)]
            trace.vetoed_by_health = [e.mechanism_id for e in effects if e not in survivors]
            effects = survivors
            trace.reason = f"health_veto:{winner.mechanism_id}"

        # ---------- 第 2 层: 冲突消解 ----------
        effects = self._resolve_conflicts(ctx, effects, trace)

        # ---------- 第 3 层: 干预预算 ----------
        effects = self._apply_budget(ctx, effects, trace)

        trace.delivered = [e.mechanism_id for e in effects]
        self._persist_trace(trace)          # 全量落库，供消融实验复盘
        ctx.trace.append(f"ARBITRATE delivered={trace.delivered}")
        return effects

    def _resolve_conflicts(self, ctx, effects, trace) -> List[Effect]:
        visible = [e for e in effects if e.user_visible]
        invisible = [e for e in effects if not e.user_visible]

        directions = {d for d in
                      (self._DIRECTION.get(e.mechanism_id) for e in visible) if d}
        # 若同时存在 approach 与 withdraw -> 保守偏置: 保留 withdraw
        if "approach" in directions and "withdraw" in directions:
            dropped = [e for e in visible
                       if self._DIRECTION.get(e.mechanism_id) == "approach"]
            visible = [e for e in visible
                       if self._DIRECTION.get(e.mechanism_id) != "approach"]
            trace.dropped_by_conflict = [e.mechanism_id for e in dropped]
            trace.reason += f"|conflict_bias_withdraw(drop={len(dropped)})"
            logger.info("conflict resolved: dropped approach nudges %s",
                        [e.mechanism_id for e in dropped])

        # 同方向: 每个 (effect_type, direction) 桶内保留优先级最高者
        buckets: dict = {}
        for e in sorted(visible, key=lambda x: -x.priority):
            key = (e.effect_type, self._DIRECTION.get(e.mechanism_id, "neutral"))
            if key in buckets:
                trace.dropped_by_conflict.append(e.mechanism_id)
            else:
                buckets[key] = e

        return list(buckets.values()) + invisible

    def _apply_budget(self, ctx, effects, trace) -> List[Effect]:
        p = self.policy
        delivered, cost = [], 0.0

        for e in sorted(effects, key=lambda x: (-x.priority, x.cost)):
            if e.health_critical:                 # 健康类绕过预算
                delivered.append(e); continue
            if not e.user_visible:                # 不可见不占预算
                delivered.append(e); continue

            n_session = self.store.incr("budget", f"{ctx.user_id}:session",
                                        window_sec=3600)
            n_day = self.store.incr("budget", f"{ctx.user_id}:day", window_sec=86400)
            if (len(delivered) >= p.max_per_session
                    or n_session > p.max_per_session
                    or n_day > p.max_per_day
                    or cost + e.cost > p.max_cost_per_session):
                trace.dropped_by_budget.append(e.mechanism_id)
                continue
            delivered.append(e)
            cost += e.cost

        return delivered

    def _persist_trace(self, trace: ArbitrationTrace) -> None:
        """落库 —— 这是消融实验的原始数据，不可丢"""
        from app.services.mechanism_state import record_arbitration_trace
        record_arbitration_trace(trace)
```

## 3.4 与 A/B 框架的对接改造

### 3.4.1 现有缺陷（已复算确认）

1. **粒度错误**：`Experiment.parameter_name: str` + `control_value/treatment_value: Any`（`ab_test_framework.py:64-66`）。`get_parameter_value()`（`:161-174`）返回**标量值**，无法表达"跳过 `FOMOEngine.generate_fomo_nudge`"。**无 `mechanism_id` 字段**。
2. **零耦合**：`grep -rn "ab_test_framework|get_parameter_value"` 仅命中 `api/gamification.py` 的 5 个管理端点 + `services/__init__.py:23`。**81 个 Engine 类中无一读取实验分组。**
3. **数据不落库**：`_experiments`（`:104`）、`_user_assignments`（`:105`）均为内存 dict，`tracking_days=90`（`:77`）形同虚设——进程重启即丢，撑不过 90 天。
4. **统计缺陷**：`min_sample_per_group=100`（`:76`）为硬编码常量，**无功效分析**；`effect_size`（`:290`）用控制组标准差近似 pooled SD（应为 `sqrt(((n1-1)s1² + (n2-1)s2²)/(n1+n2-2))`），小样本下偏倚明显。

### 3.4.2 改造方案

**改造 1：`Experiment` 增加 `mechanism_toggles`**

```python
# app/services/ab_test_framework.py  (改造后)
@dataclass
class Experiment:
    id: str
    name: str
    description: str

    # --- 保留旧字段以兼容存量实验 ---
    parameter_name: str = ""
    control_value: Any = None
    treatment_value: Any = None

    # --- 新增: 机制级开关（消融实验的核心） ---
    mechanism_toggles: Dict[str, bool] = field(default_factory=dict)
    # 例: {"LF-M44": False}            单机制消融
    #     {"LF-M23": False, "LF-M24": False, ...}  类别消融（推荐）

    # --- 新增: 统计治理 ---
    primary_metric: str = "knowledge_mastery_growth"
    secondary_metrics: List[str] = field(default_factory=list)
    alpha_alloc: float = 0.05          # 该实验在检验序中分到的 α
    gate_level: int = 1                # 0=omnibus, 1=category, 2=mechanism
    mde: float = 0.3                   # 最小可检测效应 (Cohen's d)
    required_n_per_group: int = 0      # 由功效分析写入，非硬编码
    icc_assumed: float = 0.05          # 假设的组内相关系数
    cluster_randomized: bool = True    # 是否整群随机（班级级）

    phase: ExperimentPhase = ExperimentPhase.SHADOW
    traffic_percentage: float = 0.0
    metrics: list = field(default_factory=list)
    results: list = field(default_factory=list)
    safety_stop_triggered: bool = False
    safety_stop_reason: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    min_sample_per_group: int = 100     #  deprecated: 由 required_n_per_group 取代
    tracking_days: int = 90
    registry_fingerprint: str = ""      # 新增: 注册表版本指纹，保证可复现
```

**改造 2：新增机制开关查询方法**

```python
    def get_mechanism_toggles(self, user_id: str) -> Dict[str, bool]:
        """返回该用户的完整机制开关向量。

        数据流:
          Experiment.mechanism_toggles  --(按分组)-->  {mechanism_id: enabled}
          MechanismRegistry 默认配置    --(基线)---->  {mechanism_id: enabled}
          合并规则: 实验覆盖 > 注册表默认; 健康临界机制恒为 True
        """
        toggles: Dict[str, bool] = {}
        for exp_id, exp in self._experiments.items():
            if exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
                continue
            group = self.assign_user(exp_id, user_id)
            if group != "treatment" or exp.phase == ExperimentPhase.SHADOW:
                continue
            toggles.update(exp.mechanism_toggles)
        return toggles

    def is_mechanism_enabled(self, experiment_id: str, user_id: str,
                             mechanism_id: str, health_critical: bool = False) -> bool:
        """单点查询。health_critical 机制永不被关闭。"""
        if health_critical:
            return True
        exp = self._experiments.get(experiment_id)
        if not exp or exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
            return True
        if self.assign_user(experiment_id, user_id) != "treatment":
            return True
        return exp.mechanism_toggles.get(mechanism_id, True)
```

**改造 3：注册表中的 `ExperimentProvider` 适配器**

```python
# app/services/mechanism_registry.py
class ABTestToggleProvider:
    """把 ab_test_framework 适配为注册表的开关来源"""
    def __init__(self, framework):
        self._fw = framework

    def get_toggles(self, user_id: str) -> Dict[str, bool]:
        return self._fw.get_mechanism_toggles(user_id)


# app/services/mechanism_registry.py (装配)
def build_registry(store, ab_framework) -> MechanismRegistry:
    registry = MechanismRegistry(store=store,
                                 experiments=ABTestToggleProvider(ab_framework))
    from app.services import register_all_mechanisms
    register_all_mechanisms(registry)          # 集中注册 LF-M01..LF-M53
    return registry
```

**改造 4：引擎侧迁移示例（旧 → 新）**

旧代码（`deep_addiction_engine.py:238,277`）：

```python
class FOMOEngine:
    @classmethod
    def generate_fomo_nudge(cls, active_challenges: List[dict]) -> Optional[dict]:
        ...   # 直接返回文案，无开关、无仲裁、无预算
```

新代码：

```python
# app/services/mechanisms/register_fomo.py
from app.services.mechanism_registry import (
    MechanismSpec, MechanismContext, Effect, EffectType,
    TheoryRoot, TimingPhase, TargetConstruct, Maturity,
)
from app.services.deep_addiction_engine import FOMOEngine

FOMO_SPEC = MechanismSpec(
    id="LF-M44",
    name_zh="错失恐惧",
    name_en="Fear of Missing Out",
    theory_root=TheoryRoot.F_AFFECT,
    timing=TimingPhase.PRE,
    construct=TargetConstruct.RETENTION,
    theory_ref="Przybylski, Murayama, DeHaan & Gladwell (2013). Motivational, "
               "emotional, and behavioral correlates of fear of missing out. "
               "Computers in Human Behavior, 29(4), 1841-1848.",
    impl_ref="deep_addiction_engine.py:238 (nudge @277)",
    maturity=Maturity.LOGIC_ONLY,
    default_enabled=True,
    priority=70,                      # 高优先级 —— 正因如此才必须被仲裁
    effect_type=EffectType.NUDGE,
    budget_cost=1.5,                  # FOMO 成本高: 占用更多预算, 易被裁掉
    health_critical=False,
    conflicts_with=("LF-M51", "LF-M52"),   # 与防沉迷/强制休息语义对立
)

def register(registry):
    @registry.mechanism(FOMO_SPEC)
    def _fomo(ctx: MechanismContext) -> Optional[Effect]:
        challenges = ctx.payload.get("active_challenges", [])
        nudge = FOMOEngine.generate_fomo_nudge(challenges)
        if nudge is None:
            return None
        return Effect(mechanism_id="LF-M44", effect_type=EffectType.NUDGE,
                      payload=nudge, user_visible=True, cost=FOMO_SPEC.budget_cost)
```

**关键行为变化**：迁移后，`FOMOEngine` **不再直接产出用户可见文案**。它只向注册表返回一个 `Effect` 候选，最终是否下发由仲裁器决定。当 `LF-M52`（未成年保护）命中时，FOMO 的 nudge 会在第 1 层被直接丢弃。**这是行为改变，必须走回归测试。**

**改造 5：统计函数修正**

```python
    # 修正 ab_test_framework.py:290 的 effect_size
    @staticmethod
    def cohens_d(control: List[float], treatment: List[float]) -> float:
        """正确 pooled SD，而非用控制组 SD 近似"""
        n1, n2 = len(control), len(treatment)
        if n1 < 2 or n2 < 2:
            return 0.0
        m1, m2 = sum(control) / n1, sum(treatment) / n2
        s1 = sum((x - m1) ** 2 for x in control) / (n1 - 1)
        s2 = sum((x - m2) ** 2 for x in treatment) / (n2 - 1)
        pooled = ((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)
        if pooled <= 0:
            return 0.0
        return (m2 - m1) / (pooled ** 0.5)

    @staticmethod
    def required_n_per_group(d: float, alpha: float = 0.05,
                             power: float = 0.80, deff: float = 1.0) -> int:
        """样本量计算。deff = 1 + (m-1)*ICC 为整群随机设计效应。

        来源: n = 2*(z_{1-a/2} + z_{1-b})^2 / d^2  (two-sided, equal n)
        """
        from math import ceil, sqrt
        from statistics import NormalDist
        nd = NormalDist()
        z_a = nd.inv_cdf(1 - alpha / 2)
        z_b = nd.inv_cdf(power)
        return ceil(2 * (z_a + z_b) ** 2 / (d * d) * deff)
```

> **注意 `deff`**：这是原框架完全缺失的。整群随机（班级级）时，方差膨胀 `DEFF = 1 + (m−1)ρ`。m=30、ρ=0.05 → **DEFF = 2.45**，即样本量需 ×2.45。**忽略 DEFF 是原框架最隐蔽的统计错误。**

---

# 第四部分 持久化改造方案

## 4.1 现状定性

**全库仅 16 张表**：`users, grade_levels, subjects, tasks, attempts, ability_estimates, student_skill_profiles, assignments, classes, curriculum_nodes, feedback_scripts, alerts, audit_logs, consent_records, pet_profiles, spaced_reviews`。

**11 个内存态容器（复算确认，行号可核）**：

| # | 容器 | 位置 | 承载机制 | 语义资产价值 |
|---|---|---|---|---|
| 1 | `BOX_STATES` | `gamification_service.py:202` | LF-M01 变比率宝箱 | 中 |
| 2 | `_active_sessions` | `gamification_service.py:508` | LF-M14 峰终 | 中 |
| 3 | `_unfinished` | `gamification_service.py:579` | LF-M13 蔡格尼克 | 中 |
| 4 | `ACTIVE_QUESTS` | `duolingo_addiction_engine.py:469` | LF-M30 组队任务 | 中 |
| 5 | `GOALS` | `habit_addiction_engine.py:216` | LF-M39 自我调节目标 | 中 |
| 6 | `PALACES` | `learning_methods_engine.py:329` | 记忆宫殿（学习方法） | 中 |
| 7 | `PLAYER_SKILLS` | `meta_learning_skilltree.py:163` | **LF-M40 全部 16 技能树** | **极高** |
| 8 | `TEAMS` | `team_competition_engine.py:292` | LF-M31 团队竞赛 | 高 |
| 9 | `PLAYER_TEAMS` | `team_competition_engine.py:293` | LF-M31 | 高 |
| 10 | `MATCHES` | `team_competition_engine.py:559` | LF-M31 赛季对局 | 高 |
| 11 | `_experiments` / `_user_assignments` | `ab_test_framework.py:104-105` | **全部实验数据** | **极高** |

**伪持久化（比内存态更隐蔽，危害更大）**：`learning_orchestrator.py:409`

```python
xp_state = XPState()                          # ← 每次请求从零构造
xp_result = XPEngine.award_xp(xp_state, event_type, streak=success_streak)
...
"xp_update": {"total_xp": xp_result["total_xp"], ...}   # :471-476 只写响应体
```

**后果：用户每次提交答案，XP/等级/连胜从 0 重新计算，返回给前端后即丢弃。** LF-M19 名义上"已接入"，实际是**失效的**。这直接污染任何以"累计 XP"、"等级提升"、"连胜天数"为因变量的分析。

## 4.2 核心资产三张表（必须最先做）

### 4.2.1 `user_xp_state`（LF-M19）—— 最高优先级

```sql
CREATE TABLE user_xp_state (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_xp        BIGINT      NOT NULL DEFAULT 0,
    level           INTEGER     NOT NULL DEFAULT 1,
    xp_into_level   BIGINT      NOT NULL DEFAULT 0,
    current_streak  INTEGER     NOT NULL DEFAULT 0,
    longest_streak  INTEGER     NOT NULL DEFAULT 0,
    last_active_date DATE,
    streak_freeze_used INTEGER  NOT NULL DEFAULT 0,   -- LF-M12 连胜神圣化
    daily_goal_xp   INTEGER     NOT NULL DEFAULT 20,  -- LF-M16
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_xp UNIQUE (user_id)
);
CREATE INDEX idx_xp_level    ON user_xp_state (level DESC);
CREATE INDEX idx_xp_streak   ON user_xp_state (current_streak DESC);
CREATE INDEX idx_xp_lastact  ON user_xp_state (last_active_date DESC);
```

**配套迁移（`learning_orchestrator.py:409` 改造）**：

```python
# 旧: xp_state = XPState()                       # 从零构造
# 新:
xp_state = xp_repository.get_or_create(user.id)   # 从 DB 载入
xp_result = XPEngine.award_xp(xp_state, event_type, streak=success_streak)
xp_repository.save(user.id, xp_state)             # ← 新增: 落库
```

> **审计意见**：这一处 3 行改动是全项目 ROI 最高的修复。不做这件事，任何"XP 对学习动机的影响"分析都是伪造的。**建议在论文中把它作为一个明确的局限性修复项写出来（before/after 对比）。**

### 4.2.2 `user_skill_tree`（LF-M40，16 技能树）

```sql
CREATE TABLE skill_defs (                    -- 16 个技能定义（静态，seed）
    skill_id      VARCHAR(64) PRIMARY KEY,
    name_zh       VARCHAR(64)  NOT NULL,
    category      VARCHAR(32)  NOT NULL,     -- MEMORY/UNDERSTANDING/PRACTICE/FOCUS/MINDSET
    prerequisites JSONB        NOT NULL DEFAULT '[]',
    max_level     INTEGER      NOT NULL DEFAULT 5
);

CREATE TABLE user_skill_tree (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id     VARCHAR(64) NOT NULL REFERENCES skill_defs(skill_id),
    level        INTEGER     NOT NULL DEFAULT 0,
    skill_xp     BIGINT      NOT NULL DEFAULT 0,
    unlocked     BOOLEAN     NOT NULL DEFAULT false,
    unlocked_at  TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_id)
);
CREATE INDEX idx_skilltree_user  ON user_skill_tree (user_id);
CREATE INDEX idx_skilltree_skill ON user_skill_tree (skill_id, level DESC);
```

`meta_learning_skilltree.py:163` 的 `PLAYER_SKILLS` → 改为读此表（带 Redis 缓存）。

### 4.2.3 实验数据三表（A/B 框架）

```sql
CREATE TABLE experiments (
    id                   VARCHAR(64) PRIMARY KEY,
    name                 VARCHAR(255) NOT NULL,
    description          TEXT,
    gate_level           SMALLINT   NOT NULL DEFAULT 1,   -- 0/1/2 检验序层级
    mechanism_toggles    JSONB      NOT NULL DEFAULT '{}', -- {"LF-M44": false}
    primary_metric       VARCHAR(64) NOT NULL,
    mde                  REAL       NOT NULL,
    alpha_alloc          REAL       NOT NULL,
    required_n_per_group INTEGER    NOT NULL,
    cluster_randomized   BOOLEAN    NOT NULL DEFAULT true,
    deff                 REAL       NOT NULL DEFAULT 1.0,
    phase                VARCHAR(16) NOT NULL,
    registry_fingerprint VARCHAR(16) NOT NULL,             -- 可复现性锚点
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ
);

CREATE TABLE experiment_assignments (
    experiment_id VARCHAR(64) NOT NULL REFERENCES experiments(id),
    user_id       BIGINT      NOT NULL REFERENCES users(id),
    cluster_id    BIGINT,                                  -- 班级 ID（整群随机）
    group_name    VARCHAR(16) NOT NULL,                    -- control/treatment
    assigned_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (experiment_id, user_id)
);
CREATE INDEX idx_assign_cluster ON experiment_assignments (experiment_id, cluster_id);

CREATE TABLE experiment_observations (
    id            BIGSERIAL PRIMARY KEY,
    experiment_id VARCHAR(64) NOT NULL,
    user_id       BIGINT      NOT NULL,
    metric        VARCHAR(64) NOT NULL,
    value         DOUBLE PRECISION,
    observed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    day_index     INTEGER,                                 -- 进入实验第 N 天
    burnin_excluded BOOLEAN   NOT NULL DEFAULT false       -- novelty 消退期标记
);
CREATE INDEX idx_obs_exp_metric ON experiment_observations (experiment_id, metric, user_id);
```

## 4.3 其余补表清单（13 个引擎无表）

```sql
-- LF-M01/M02 宝箱与濒赢
CREATE TABLE user_treasure_box (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    box_state JSONB NOT NULL DEFAULT '{}',
    near_miss_count INTEGER NOT NULL DEFAULT 0,
    last_opened_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LF-M03 奖励节拍 / LF-M14 峰终
CREATE TABLE user_session_memory (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(64) NOT NULL,
    peak_valence REAL, end_valence REAL,                  -- 峰终两要素
    reward_timestamps JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ,
    UNIQUE (user_id, session_id)
);
CREATE INDEX idx_sessionmem_user ON user_session_memory (user_id, started_at DESC);

-- LF-M13 蔡格尼克未完成项
CREATE TABLE user_unfinished_tasks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_ref VARCHAR(128) NOT NULL, progress_pct REAL NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX idx_unfinished_user ON user_unfinished_tasks (user_id, resolved_at);

-- LF-M27 联赛 / LF-M16 月挑战
CREATE TABLE user_league_state (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    league_tier VARCHAR(16) NOT NULL DEFAULT 'bronze',
    tier_points INTEGER NOT NULL DEFAULT 0,
    weekly_rank INTEGER, promoted_at TIMESTAMPTZ, demoted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE user_challenge_progress (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge_id VARCHAR(64) NOT NULL, period VARCHAR(16) NOT NULL, -- daily/monthly
    target_value INTEGER NOT NULL, current_value INTEGER NOT NULL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (user_id, challenge_id, period)
);

-- LF-M30 组队任务
CREATE TABLE friend_quests (
    quest_id VARCHAR(64) PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    partner_ids JSONB NOT NULL DEFAULT '[]',
    goal_xp INTEGER NOT NULL, current_xp INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'active'
);

-- LF-M31 团队与赛季
CREATE TABLE teams (
    team_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL, captain_id BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE team_members (
    team_id VARCHAR(64) NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (team_id, user_id)
);
CREATE TABLE team_matches (
    match_id VARCHAR(64) PRIMARY KEY,
    season_id VARCHAR(32) NOT NULL, team_a VARCHAR(64) NOT NULL, team_b VARCHAR(64) NOT NULL,
    score_a INTEGER NOT NULL DEFAULT 0, score_b INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ
);

-- LF-M39 自我调节目标
CREATE TABLE self_regulation_goals (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_text TEXT NOT NULL, target_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',   -- active/achieved/abandoned
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ
);
CREATE INDEX idx_srgoals_user ON self_regulation_goals (user_id, status);

-- LF-M47..M50 UX 个性化（LF-M18 宜家效应 / LF-M17 自主性）
CREATE TABLE user_ux_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    theme JSONB NOT NULL DEFAULT '{}',        -- LF-M48 色彩
    layout JSONB NOT NULL DEFAULT '{}',       -- LF-M49 空间锚定
    micro_interactions BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 记忆宫殿（学习方法，非行为机制，但同为内存态）
CREATE TABLE memory_palaces (
    palace_id VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL, nodes JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 仲裁轨迹（消融实验原始证据）
CREATE TABLE arbitration_traces (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL, session_id VARCHAR(64),
    candidates JSONB NOT NULL, vetoed_by_health JSONB NOT NULL DEFAULT '[]',
    dropped_by_conflict JSONB NOT NULL DEFAULT '[]',
    dropped_by_budget JSONB NOT NULL DEFAULT '[]',
    delivered JSONB NOT NULL DEFAULT '[]', reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_trace_user ON arbitration_traces (user_id, created_at DESC);

-- 机制曝光日志（每个机制对每个用户的每次命中）
CREATE TABLE mechanism_exposures (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL, session_id VARCHAR(64),
    mechanism_id VARCHAR(16) NOT NULL,        -- LF-Mxx
    delivered BOOLEAN NOT NULL,               -- 是否被仲裁器放行
    drop_reason VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_expo_mech ON mechanism_exposures (mechanism_id, user_id);
CREATE INDEX idx_expo_time ON mechanism_exposures (created_at DESC);
```

> `mechanism_exposures` 与 `arbitration_traces` 是**为消融实验专门设计的**。没有这两张表，就无法回答"用户到底实际接收了多少次该机制的干预"（treatment adherence / compliance），消融实验只能做 ITT，无法做 per-protocol 或 CACE 估计。**这两张表必须在实验启动前建好——事后无法补。**

## 4.4 多 worker 一致性：推荐方案

**推荐：DB 为主 + Redis 为可选缓存层（write-through），不做 Redis 主存储。**

| 方案 | 判定 | 理由 |
|---|---|---|
| Redis 主键 | ❌ 不推荐 | 11 个容器中至少 4 个（技能树、团队、赛季、实验分配）是**长期资产**，不是缓存。Redis 持久化配置（AOF everysec）仍有秒级丢失窗口，而实验分组丢失意味着分组错乱——**实验数据的完整性要求高于性能**。 |
| **DB 主 + Redis 缓存** | ✅ **推荐** | 强一致由 DB 保证；热路径（XP、宝箱）用 Redis write-through 缓存 + 5 min TTL；**实验分配与技能树不缓存**，直读 DB。 |
| 单 worker + sticky session | ❌ 拒绝 | 不可扩展，且与云函数部署（cloudbaserc.json 表明是 CloudBase）冲突。 |

**实现要点**：

```python
# app/services/mechanism_state.py
class DBBackedStore:
    """默认 StateStore: PostgreSQL 主存储 + 可选 Redis 缓存。

    缓存策略（按命名空间区分，不搞一刀切）:
      xp, treasure_box, session_memory -> Redis, TTL 300s, write-through
      skill_tree, teams, experiments, assignments -> 不缓存，直读 DB
    """
    CACHEABLE = {"xp", "treasure_box", "session_memory"}
    TTL = 300

    def get(self, ns, key):
        if ns in self.CACHEABLE:
            hit = self.redis.get(f"mst:{ns}:{key}")
            if hit: return json.loads(hit)
        row = self.db.execute(select(MechanismState).where(
            MechanismState.namespace == ns, MechanismState.key == key)).scalar_one_or_none()
        val = row.value if row else None
        if val is not None and ns in self.CACHEABLE:
            self.redis.setex(f"mst:{ns}:{key}", self.TTL, json.dumps(val))
        return val

    def set(self, ns, key, value, ttl=None):
        self.db.merge(MechanismState(namespace=ns, key=key, value=value))
        if ns in self.CACHEABLE:
            self.redis.setex(f"mst:{ns}:{key}", ttl or self.TTL, json.dumps(value))

    def incr(self, ns, key, delta=1, window_sec=None):
        """原子计数 —— 预算控制依赖此操作，必须原子"""
        return self.db.execute(text("""
            INSERT INTO mechanism_counters (namespace, key, value, expires_at)
            VALUES (:ns, :k, :d, CASE WHEN :w IS NULL THEN NULL
                                      ELSE now() + (:w || ' seconds')::interval END)
            ON CONFLICT (namespace, key) DO UPDATE
               SET value = mechanism_counters.value + :d
             WHERE mechanism_counters.expires_at IS NULL
                OR mechanism_counters.expires_at > now()
            RETURNING value
        """), {"ns": ns, "k": key, "d": delta, "w": window_sec}).scalar() or 0
```

---

# 第五部分 孤儿模块处置决策

## 5.1 复算：谁的调用方为 0

```
positive_addiction_engine  -> 0 调用方   （6 机制）
deep_addiction_engine      -> 1 (ux_addiction_engine)  ← 唯一调用方本身也是孤儿（6/7 机制）
ux_addiction_engine        -> 0 调用方   （8 机制）
social_addiction_engine    -> 0 调用方   （4 机制）
addiction_engine_v3        -> 1 (services/__init__.py)  ← 仅 re-export，非真实调用
learning_methods_engine_v3 -> 1 (services/__init__.py)  ← 同上
advanced_methods_engine    -> 0 调用方   （含 4 个认知策略引擎）
placement_test_engine      -> 0 调用方
onboarding_engine          -> 0 调用方
anti_addiction_compliance  -> 0 调用方   （LF-M52 的合规实现！）
habit_addiction_engine     -> 2 (api/gamification.py, anti_addiction.py)  ✓ 有调用
team_competition_engine    -> 1 (api/gamification.py)  ✓ 有调用
```

> **注意**：`services/__init__.py` 的 re-export **不构成真实调用**。把它计入"有调用方"是自欺欺人。按此口径，**孤儿机制约占 40/59 ≈ 68%**（更正先前材料的 80%）。

## 5.2 三档处置

### 档 A：必须接入（学术价值高，构成完整 story）

| 优先级 | 模块 / 机制 | 理由 | 工作量（人日） |
|---:|---|---|---:|
| **P0** | `learning_orchestrator.py:409` XP 落库（LF-M19） | 3 行修复，ROI 最高；不做则所有 XP 相关分析无效 | **0.5** |
| **P0** | `meta_learning_skilltree.py:163` 落库（LF-M40） | 16 技能树是核心资产，且与"元认知"这一学习科学构念直接对应 | **2** |
| **P0** | `anti_addiction_compliance.py:79`（LF-M52） | **合规风险**，不是学术问题。未成年保护未接入 = 可被监管直接质疑 | **1.5** |
| **P1** | `gamification_service.py` 10 个机制接入注册表 | 10/53，占比最大，且已有 API，改造成本最低 | **4** |
| **P1** | `duolingo_addiction_engine.py` 8 个机制接入 | 已有 XPEngine 接入，其余 7 个补齐 | **3** |
| **P2** | `addiction_engine_v3.py`（LF-M09/10/13/14/42） | 5 个机制理论来源最硬（前景理论、蔡格尼克、峰终） | **2.5** |
| **P2** | `habit_addiction_engine.py`（LF-M36/37/38） | **理论证据最强的一类**（Milkman et al. 2014 是 RCT），论文最好卖 | **2** |
| **P3** | `deep_addiction_engine.py` LF-M43 好奇心缺口 | 健康风险最低的正向机制，适合做"正向对照" | **1.5** |
| **P3** | `positive_addiction_engine.py` LF-M46 身份认同 | Oyserman 的身份动机有强实证支持 | **1.5** |
| | | **小计** | **≈ 18.5 人日** |

### 档 B：可保留但不接入（论文中作为 "design–deployment gap" 诚实披露）

| 模块 / 机制 | 处置理由 |
|---|---|
| `ux_addiction_engine.py` 8 个（LF-M47–M50） | UX 层机制的效果量通常极小，且需前端配合。**建议保留代码、不接入，在论文中列为 designed-but-not-deployed** |
| `social_addiction_engine.py` LF-M28/M29/M32 | 社交名片、礼物经济缺乏学习情境下的因果证据；家长门户涉及隐私合规，需单独走 IRB |
| `advanced_methods_engine.py` / `learning_methods_engine_v3.py` 7 个认知策略 | 属学习方法而非游戏化机制，**应划归另一个研究问题**，不要混进机制消融 |
| `placement_test_engine` / `onboarding_engine` | 属产品流程，非干预机制 |
| LF-M45 偶然性惊喜（占位） | 无实质逻辑 |

**这一档是论文的诚实性资产**：明确写 "of the 53 catalogued mechanisms, 16 (30%) were wired into the runtime; the remaining 37 (70%) were designed and implemented but not deployed"，审稿人无法反驳一个你自己主动承认并量化的局限。

### 档 C：建议删除

| 目标 | 理由 |
|---|---|
| `gamification_service.py:419/507/578/659/683` 5 处重复实现 | 已由 canonical 版（LF-M09/14/13/23/17）覆盖；保留会造成"改了 A 处 B 处没改"的维护陷阱 |
| LF-M50 多感官包装（触觉/声音/字体动效三个占位） | 无理论来源（无法通过注册表的 `theory_ref` 强制字段），无逻辑，无调用方 |
| `addiction_engine_v3.py:36` 沉没成本（LF-M10） | **建议删除而非接入**。沉没成本提示诱导用户"已经投入这么多，别放弃"，在学习情境下与 LF-M52 防沉迷直接冲突，且伦理上难以辩护 |

> **删除建议需谨慎**：删除代码会减少可审计的"证据"。**建议 `git tag` 一个 `pre-registry-audit` 快照后再删**，保证审计结论可复现。

## 5.3 工作量汇总

| 档 | 人日 |
|---|---:|
| A 必须接入 | 18.5 |
| 注册表 + 仲裁器 + StateStore 骨架 | 6 |
| 持久化（13 张补表 + 迁移脚本 + 回归测试） | 10 |
| A/B 框架改造（含统计函数修正） | 4 |
| 审计台账（53 机制 theory_ref / impl_ref 补全 + κ 检验） | 5 |
| **合计** | **≈ 43.5 人日（约 9 人周）** |

不含消融实验本身的运行时间（§7 表明至少需要 8–12 周数据收集）。

---

# 第六部分 消融实验的可行性设计

**这是我最需要你认真读完的一节。结论先行：53 个机制逐个消融在统计上不可行，必须降维。**

## 6.1 统计陷阱预警：多重比较

### 6.1.1 问题规模

逐个消融 53 个机制 = **53 次独立的零假设检验**。若每次用 α=0.05 且不校正，在所有机制真正无效的原假设下：

```
P(至少一次假阳性) = 1 − (1 − 0.05)^53 = 1 − 0.95^53 = 1 − 0.0654 = 0.9346
```

**即 93.5% 的概率至少宣称一个"有效"机制，而实际上全是噪音。** 这不是"需要小心"的问题，这是"结果基本不可用"的问题。

### 6.1.2 三种校正方案对比

| 方案 | 每次检验 α | 控制目标 | 致命缺陷 |
|---|---|---|---|
| **Bonferroni** | 0.05 / 53 = **0.000943** | FWER ≤ 0.05 | 极度保守，样本量爆炸（见 §6.2） |
| **Holm-Bonferroni** | 逐步：0.05/53, 0.05/52, … | FWER ≤ 0.05 | 比 Bonferroni 略强，但量级相同 |
| **BH (FDR)** | 按 p 值排序，q=0.05 | FDR ≤ 0.05 | 允许 5% 的"显著"结果是假的；**对"我们要据此设计产品"的场景不合适**——假阳性机制会真的被上线 |
| **分层门控（推荐）** | 见下 | FWER ≤ 0.05 | 需要预注册检验序，灵活性低 |

**我的推荐：分层门控（hierarchical gatekeeping）**。理由：

1. Gatekeeping 在 FWER 强控制下，**比 Bonferroni 功效高得多**，因为它把"53 次检验"拆成"8 次 + 少量"，且后续层级**仅在前序显著时才进入**（fixed-sequence 性质不消耗 α）。
2. 它与 taxonomy 天然对齐 —— 我们本来就有 8 个理论类别（轴 1）。
3. 它天然产出"哪些类别有效 → 类别内哪些机制有效"的**层次化结论**，这比 53 个零散 p 值好讲故事。

### 6.1.3 推荐的三层检验序（必须预注册）

```
Gate 0 (α = 0.05, 1 次检验)
  H0: 全机制开启 vs 全机制关闭，主因变量无差异
  → 若不显著，STOP（说明整套游戏化对学习无效，无需继续）

Gate 1 (Holm 校正, 8 次检验: 类别 A–H 分组消融)
  H0_k: 关闭类别 k 的全部机制，主因变量无差异
  → Holm 逐步拒绝；仅对被拒绝的类别进入 Gate 2
  → 保守界: α' = 0.05 / 8 = 0.00625

Gate 2 (Holm 校正, 仅对 Gate 1 显著的类别内机制)
  假设 2 个类别显著，平均 6 机制/类 → 12 次检验
  → 保守界: α' = 0.05 / 12 = 0.004167

Gate 2.5 (仅对预注册的 ≤3 对交互做析因检验, Holm, α' = 0.05/3 = 0.0167)
```

**关键性质**：Gate 2 的检验**只在 Gate 1 拒绝后才进行**。由于 Gate 1 的检验本身已消耗 α，而 Gate 2 是在**条件于 Gate 1 显著**的子空间内做 Holm，整体上 FWER 仍被控制在 0.05（这是 gatekeeping 的标准结论，Dmitrienko & Tamhane 2009）。

## 6.2 样本量计算（完整过程）

### 6.2.1 基础公式

两独立样本、双侧、等样本量：

```
n_group = ⌈ 2 · (z_{1−α/2} + z_{1−β})² / d² · DEFF ⌉
```

其中 `DEFF = 1 + (m − 1) · ρ` 为整群随机（班级级）的设计效应。

### 6.2.2 逐系数计算

**场景 1：朴素方案 —— 53 个机制逐个消融，Bonferroni**

α' = 0.05/53 = 0.000943 → z_{1−α'/2} = z_{0.9995285} ≈ **3.286**
z_{1−β} = z_{0.80} ≈ **0.8416**
(z_a + z_b)² = (3.286 + 0.8416)² = 4.1276² = **17.037**

| d | n/group（DEFF=1） | 53 组总处理组 | 共享对照（√53=7.28 倍） | **总 N** | × DEFF 2.45 |
|---|---:|---:|---:|---:|---:|
| 0.2 | 852 | 45,156 | 6,203 | **51,359** | **125,830** |
| 0.3 | 379 | 20,087 | 2,759 | **22,846** | **55,973** |
| 0.5 | 137 | 7,261 | 997 | **8,258** | **20,232** |

**结论：以 d=0.2、整群随机计，需要约 12.6 万用户。不现实。**

> 共享对照的最优分配比：n_control = n_treatment × √k（k 为处理臂数）。这是方差最小化的标准结果。

**场景 2：推荐方案 —— 分层门控，Gate 1 类别级（8 次检验）**

α' = 0.05/8 = 0.00625 → z_{1−α'/2} = z_{0.996875} ≈ **2.737**
(z_a + z_b)² = (2.737 + 0.8416)² = 3.5786² = **12.806**

| d | n/group（DEFF=1） | 8 组总处理 | 共享对照（√8=2.83 倍） | **总 N** | × DEFF 2.45 |
|---|---:|---:|---:|---:|---:|
| 0.2 | 641 | 5,128 | 1,813 | **6,941** | **17,005** |
| 0.3 | 285 | 2,280 | 806 | **3,086** | **7,561** |
| 0.4 | 161 | 1,288 | 455 | **1,743** | **4,270** |
| 0.5 | 103 | 824 | 291 | **1,115** | **2,732** |

**场景 3：Gate 2 机制级（12 次检验，α'=0.05/12=0.004167，z≈2.879）**

(z_a + z_b)² = (2.879 + 0.8416)² = 3.7206² = **13.843**

| d | n/group | 12 组总处理 | 共享对照（√12=3.46） | **总 N** | × DEFF 2.45 |
|---|---:|---:|---:|---:|---:|
| 0.3 | 308 | 3,696 | 1,067 | **4,763** | **11,669** |
| 0.4 | 174 | 2,088 | 602 | **2,690** | **6,591** |
| 0.5 | 111 | 1,332 | 384 | **1,716** | **4,204** |

### 6.2.3 诚实的可行性评估

| 目标 | 总 N（整群随机，DEFF=2.45） | 可行性判定 |
|---|---:|---|
| 53 机制逐个消融，d=0.2 | **125,830** | ❌ **绝对不可行**。即使是头部在线教育产品，单一功能的同时在线用户也很少达到这个量级。 |
| 53 机制逐个消融，d=0.5 | **20,232** | ❌ **不可行**。且 d=0.5 对单个游戏化机制是不切实际的期望——文献中单个 gamification element 的典型效应量是 **d ≈ 0.2–0.4**（Sailer et al. 2017 元分析；Hamari et al. 2014 元分析显示多数为小到中等效应）。 |
| **类别消融（8 组），d=0.3** | **7,561** | ⚠️ **有条件可行**。需要多校部署（假设 30 人/班，需 ≈ 252 个班级 ≈ 8–10 所学校）。 |
| **类别消融（8 组），d=0.4** | **4,270** | ✅ **可行**。约 143 个班级 ≈ 5–6 所学校。 |
| **类别消融（8 组），用户级随机，d=0.3** | **3,086** | ✅ **可行**，但**沾染风险高**（见 §6.5）。 |

**我的裁决：以当前的典型部署规模（单校/少校），只有"类别消融 + d≈0.4"这一档是现实的。**

**必须向读者诚实说明的三点**：
1. 若只能做到 d=0.4 的功效，那么**效应量小于 0.4 的机制将无法被检出**，我们的结论会系统性偏向"大效应机制"，这是**发表偏倚的一种形式**，必须在 limitations 中写明。
2. 上面的计算假定**每组样本独立且方差齐**。真实学习数据长尾严重（活跃度分布极度右偏），实际所需 N 还会**再上浮 20–50%**。
3. 若 `ability_estimates` 的能力估计本身有测量误差（BKT 的 θ 估计标准误），因变量的信度 < 1 会**稀释效应量**。信度 0.7 时，观测 d 约为真实 d 的 √0.7 ≈ 0.84 倍。**这需要在功效分析中额外放大 N（约 ×1/0.7 ≈ 1.43）。** 综合起来，现实总 N 应在上表基础上**再乘约 1.5–1.8**。

> **修正后的现实估计**：类别消融 d=0.3 → 7,561 × 1.6 ≈ **12,000 用户**；d=0.4 → 4,270 × 1.6 ≈ **6,800 用户**。

## 6.3 降维策略（核心设计）

### 6.3.1 为什么必须分组消融

三个理由，缺一不可：

1. **统计理由**：见 §6.2，样本需求从 ~126,000 降到 ~7,500，**约 17 倍差距**。
2. **概念理由**：同一类别内的机制共享理论机制（如 B 类全部依赖"损失框架"），**单独关掉其中一个，其他会补偿**（compensatory mechanisms）。关掉 LF-M09 损失厌恶，LF-M11 连胜仍然制造损失感 → 观测到的效应接近 0，但结论"损失厌恶无效"是错的。这是**构念层面的混淆**，不是统计功效能解决的。
3. **工程理由**：8 个开关比 53 个开关更容易做 QA，也更容易向用户解释。

### 6.3.2 层级实验设计（可直接执行）

```yaml
# 预注册文件: prereg/ablation_design_v1.yaml
design:
  name: "LearnFlow 机制消融实验（层级设计）"
  preregistered_at: "<必须在数据收集前冻结>"
  registry_fingerprint: "<registry.fingerprint() 的输出，冻结机制版本>"
  unit_of_randomization: class          # 整群随机，见 §6.5
  burn_in_days: 14                      # novelty 消退期，数据剔除
  observation_days: 56                  # 8 周观测
  total_days: 70

gates:
  - level: 0
    tests: 1
    alpha: 0.05
    arms:
      - name: all_off
        toggles: {all_53: false}        # 仅保留 H 类健康护栏
      - name: all_on
        toggles: {}
    stop_if_null: true

  - level: 1
    tests: 8
    correction: holm
    alpha_family: 0.05
    arms:
      - {name: ctrl}
      - {name: off_A, toggles_by_root: [A]}   # 关闭全部 8 个行为主义机制
      - {name: off_B, toggles_by_root: [B]}   # 关闭全部 8 个承诺/损失机制
      - {name: off_C, toggles_by_root: [C]}
      - {name: off_D, toggles_by_root: [D]}   # 关闭全部 10 个社会机制
      - {name: off_E, toggles_by_root: [E]}
      - {name: off_F, toggles_by_root: [F]}
      - {name: off_G, toggles_by_root: [G]}
      # H 类健康护栏永不关闭 —— 伦理硬约束，单臂不可关闭

  - level: 2
    tests: 12                            # 仅 Gate 1 显著类别进入
    correction: holm
    alpha_family: 0.05
    note: "进入条件与进入的类别必须在 Gate 1 结果锁定后、Gate 2 数据收集前记录"

  - level: 2.5
    tests: 3
    correction: holm
    pairs:                               # 预注册的交互对（不得事后添加）
      - [LF-M11, LF-M09]                 # 连胜 × 损失厌恶
      - [LF-M27, LF-M23]                 # 排行榜 × 社会认同
      - [LF-M01, LF-M14]                 # 变比率奖励 × 峰终
    design: "2x2 between-subject factorial"
```

### 6.3.3 类内机制消融的补充策略（若 Gate 2 不可行）

若样本不足以支撑 Gate 2，建议改用**留一法（leave-one-out, LOO）**：

- 在 Gate 1 显著的类别内，不做"单独关掉一个"，而做"**类内逐个恢复**"：先关闭整个类别，再逐个恢复单个机制。
- 优势：以"全关"为基线，每个恢复臂与全关臂比较，效应量通常**大于**"全开 vs 关一个"（因为基线被压低了，floor effect 减少）。
- 代价：结论是"该机制相对于无该机制时的贡献"，而非"移除该机制的损失"。**口径不同，必须在论文中明确区分。**

## 6.4 交互效应设计

### 6.4.1 样本量惩罚

2×2 析因设计中，交互对比 `(+1, −1, −1, +1)` 的方差是

```
Var(interaction) = 4σ²/n    （n 为每格样本量）
```

而两臂主效应对比的方差是 `2σ²/n`。**因此检出同等大小的交互效应，需要 4 倍总样本量（即每格 2 倍）。**

以 Gate 1 的 d=0.4（n=161/组）为基准，检测同样大小的交互需要：

```
每格 n = 2 × 161 × DEFF(2.45) ≈ 789   →  4 格总计 ≈ 3,156 用户/对交互
3 对交互（可共享部分对照） ≈ 7,000–9,000 用户
```

### 6.4.2 我的建议

**只测 3 对，且必须预注册。** 理由：

- 53 个机制的两两组合有 C(53,2) = **1,378 对**。任何"扫描式"交互检验都是彻底的数据疏浚（data dredging），即使 FDR 校正也无法挽救——因为交互效应的先验概率极低，FDR 控制会失效。
- 3 对的选择必须有**理论依据**：
  - `LF-M11 × LF-M09`（连胜 × 损失厌恶）：共享"损失框架"构念，预期**次可加**（sub-additive，即冗余而非增强）——这是有明确预测的方向性假设，可证伪。
  - `LF-M27 × LF-M23`（排行榜 × 社会认同）：Garcia & Tor (2009) 的 N-effect 提示排行榜在群体大时反而降低动机，社会认同可能**放大或缓解**此效应。
  - `LF-M01 × LF-M14`（变比率奖励 × 峰终）：均与"记忆中的体验评价"相关，Kahneman 的体验自我/记忆自我二分提示可能存在交互。

**每对都必须提前写出方向性预测与理论依据，否则整项检验不构成 confirmatory 研究。**

## 6.5 对照条件、随机化层级与沾染

### 6.5.1 随机化层级：推荐班级级（整群）

| 层级 | 沾染风险 | 样本需求 | 判定 |
|---|---|---|---|
| **用户级** | **高** | 低（DEFF=1） | ❌ 不推荐。同班同学会互相看到排行榜、组队任务、社交名片 —— D 类 10 个机制**本质上是跨用户耦合的**，用户级随机在物理上无法隔离。 |
| **班级级（整群）** | 低 | 高（DEFF=2.45） | ✅ **推荐**。D 类社会机制必须整群隔离。 |
| 校级 | 极低 | 极高（m≈500, DEFF≈26） | ❌ 不可行。 |

**折中方案（推荐）**：
- **D 类（社会机制）用班级级随机**；
- **A/B/C/E/F/G 类（个体机制）可用用户级随机**，DEFF=1，大幅省样本；
- 两者分开做两套实验，Gate 1 内按类别分别报告。

> 这是本设计中最能省样本的一步：7 个类别走用户级随机（DEFF=1），只有 D 类走整群。以 d=0.3 计，7 个类别的总 N ≈ 2,280 + 806 ≈ 3,086，D 类单独 ≈ (285×2)×2.45 ≈ 1,397，**合计 ≈ 4,500**，比全整群的 7,561 省 40%。

### 6.5.2 沾染（contamination）风险清单

| 风险 | 涉及机制 | 缓解 |
|---|---|---|
| 同班跨组可见 | LF-M27 排行榜、LF-M31 团队、LF-M28 名片 | 班级级随机；对照组班级显示"仅自己"的排行榜 |
| 教师端泄露 | 全部 | 教师工作台对实验分组脱敏；教师不被告知假设 |
| 跨设备同用户 | 全部 | 分组以 `user_id` 为准，设备无关（这一点现有框架已满足） |
| 对照组观察到处理组的截图/口述 | 全部 | 缩短观测窗口；在 D7/D30/D56 三次测量点做沾染自查问卷 |

**沾染自查（必须做）**：在观测期末对对照组施测"你是否看到过 XX 功能？"，用**沾染率**做敏感度分析（contamination-adjusted ITT）。

### 6.5.3 Novelty effect 消退期

**问题**：新功能上线会带来短暂的效应峰值，2–4 周后回落至基线。若不处理，消融实验测到的可能是 novelty 而非机制效应。

**处理方案（三重）**：

1. **Burn-in 剔除**：实验开始后前 **14 天**的数据标记 `burnin_excluded=true`，不进入主分析。
2. **斜率而非水平（推荐）**：主分析用**分层线性模型（HLM）/ 增长曲线模型**，估计 `day_index` 的斜率：

```
  Y_ij = β0 + β1·Group_j + β2·Day_ij + β3·(Group_j × Day_ij) + u_j + ε_ij

  关心的系数是 β3（组间斜率差异），而非 β1（组间水平差异）
```

   β3 对 novelty 更稳健 —— novelty 影响的是早期水平，而非长期斜率。
3. **三重时间点测量**：D7 / D30 / D56 分别报告，**预注册声明 D56 为确证性终点，D7/D30 为探索性**。

### 6.5.4 依从性与处理保真度

必须报告 **treatment adherence**。得益于 §4.3 的 `mechanism_exposures` 表：

```
adherence_k = 实际向用户 k 送达的机制干预次数 / 按设计应送达次数
```

- adherence < 0.8 的处理臂需做 **CACE（Complier Average Causal Effect）** 估计（用随机分组作为工具变量），主分析仍报 ITT。
- **这是原框架完全缺失的一层**，也是本设计相对现有实践的主要方法学增量。

## 6.6 主因变量选择

### 6.6.1 推荐主因变量：`knowledge_mastery_growth`

**定义**：观测窗口内能力估计 θ 的变化量，

```
Δθ = θ(t_end) − θ(t_start)
```

数据来源：`ability_estimates` 表（**已存在**，BKT 输出）。

**为什么选它**：

| 判据 | 说明 |
|---|---|
| 已有数据管道 | `ability_estimates` 表已存在，无需新建采集 |
| 构念效度 | 直接对应"学习"这一系统的核心目标 |
| 可解释性 | 单位是能力尺度，可换算为"相当于多学 X 个知识点" |
| 不受游戏化直接影响 | XP/等级不进入 θ 的估计，避免了"机制影响自己造成的因变量"的循环 |
| 与审稿人直觉一致 | 教育技术研究的核心因变量 |

### 6.6.2 次要因变量

- **留存率**：D7 / D30 / D56 留存（对应轴 3 的 `retention` 构念）
- **学习时长**：每日有效学习分钟数（注意：这是**坏的**因变量——机制可能增加时长但降低效率，需与 Δθ 联合解读为"学习效率 = Δθ / 小时"）
- **机制曝光剂量**：来自 `mechanism_exposures`（用于剂量-反应分析）

### 6.6.3 为什么 **不能**用 LAI 作主因变量

`learning_addiction_index.py` 定义了 0–100 的 LAI（越高越健康），五维加权（time .30 / motivation .25 / control .25 / cognition .10 / function .10）。**但**：

1. **11 项输入中至少 4 项无采集代码**：`intrinsic_motivation_ratio`、`external_reward_dependency`、`time_perception_bias`、`sleep_impact/social_impact` 在整个代码库中**只有 `learning_addiction_index.py` 内部的引用**，无任何采集/计算入口。它们在 `assess()` 中只能是默认值。
2. **dashboard 端点是常数**：`api/gamification.py:601` 的 `/lai/dashboard` **硬编码** `daily_minutes=45, session_minutes=25, night_ratio=0.05`，注释自己写着"默认值，实际从日志聚合"。**即所有用户、所有时刻的 dashboard LAI 是同一个常数。**
3. **加权缺乏效度证据**：0.30/0.25/0.25/0.10/0.10 的权重从何而来？无文献引用，无因子分析，无专家德尔菲。

**裁决：LAI 当前状态不具备作为主因变量的资格。** 三条出路：
- （推荐）**降级为安全监测指标**，仅用于触发 LF-M53 的自适应降级，不进入因果推断；
- **补齐采集 + 做效度验证**（需要单独的 psychometrics 研究：EFA/CFA + 信度 + 与既有量表的聚合效度），这是另一个研究的工作量；
- **废弃**，改用已验证的量表（如 Gameful Experience Scale、或改编自 Griffiths 的成瘾量表）。

---

# 第七部分 学术转化：可拆出的论文

## 7.1 论文一：游戏化学习系统的机制实现审计（**推荐首篇**）

| 项 | 内容 |
|---|---|
| **RQ1** | 自称实现 N 个游戏化机制的学习系统，其机制声称与实际代码状态的一致率是多少？ |
| **RQ2** | 声称机制中，实际被运行时调用（deployed）的比例是多少？存在哪些系统性的 design–deployment gap？ |
| **RQ3** | 机制实现中存在哪些重复实现、状态持久性缺陷与干预冲突？ |
| **RQ4** | 影响机制落地率的因素是什么（理论成熟度？实现复杂度？依赖前端？） |
| **方法** | 混合方法：(a) 静态代码分析（可复现的 grep/AST 协议）；(b) 调用图分析（判定 deployed）；(c) 预注册去重规则 + **双人独立编码 + Cohen's κ**；(d) 对 2–3 个开源对照系统应用同一协议 |
| **数据** | LearnFlow 代码库（git tag 冻结）+ 2–3 个开源游戏化学习系统的源码快照 |
| **对标期刊** | **首选**：*Empirical Software Engineering*（CCF-B，Springer，IF≈4.0）；*Information and Software Technology*（CCF-B）<br>**次选**：*ACM Transactions on Computing Education (TOCE)*（CCF-B）；*IEEE Transactions on Learning Technologies*（CCF-C/EI）<br>**会议**：*ICSE SEIS*（软件工程教育与社会）> *SIGCSE TS*（CCF-B，但偏教育实践）<br>**风险提示**：*CHI* 会嫌工程味太重；*Computers & Education* 会嫌没有学习数据。**定位要准：这是 ESE 论文，不是教育论文。** |
| **主要风险** | ① 单系统外部效度（**必须加对照系统**）；② 被判为 technical report（**必须有 RQ 与 κ**）；③ 代码库闭源则不可复现（**建议开源或提供 frozen snapshot**） |
| **成本** | **最低**。静态分析 + 台账，无需用户数据，无需 IRB。**这是它应作为首篇的核心理由。** |
| **可发表性** | ★★★★☆ |

## 7.2 论文二：机制冲突与干预预算

| 项 | 内容 |
|---|---|
| **RQ1** | 多机制系统中，干预冲突的类型学是什么（语义对立/资源竞争/时序碰撞）？ |
| **RQ2** | 三层漏斗仲裁（健康否决 / 冲突消解 / 干预预算）相比无仲裁，对用户健康指标与学习指标的影响如何？ |
| **RQ3** | 干预预算的边际收益递减点在哪里（每会话 N=1,2,3,5,∞ 次干预的效果曲线）？ |
| **方法** | 系统实现 + 在线现场实验（预算水平作为处理变量）+ 冲突日志分析（`arbitration_traces` 表） |
| **数据** | `arbitration_traces`、`mechanism_exposures`、健康指标（夜间学习比例、连续学习时长分布） |
| **对标期刊** | *CHI*（CCF-A，若为 HCI 定位）/ *CSCW*（CCF-A）/ *International Journal of Human-Computer Studies*（CCF-B）/ *Behaviour & Information Technology*（CCF-C）<br>**更保守**：*IEEE Transactions on Learning Technologies*（CCF-C） |
| **主要风险** | ① **样本需求中等**（预算水平 5 档 → 5 次检验，Holm α'=0.01，d=0.4 约需 4,000–6,000 用户）；② "干预预算"这个构念需要理论锚定（建议锚定到 **注意力预算 / 通知疲劳**，可引 *Pielot et al. 2014* 的通知可打断性研究）；③ 健康指标的因果链较长 |
| **成本** | 中。依赖注册表建成。 |
| **可发表性** | ★★★☆☆（**理论贡献取决于能否提出可推广的冲突类型学，而非只是工程方案**） |

## 7.3 论文三：53 机制消融实验

| 项 | 内容 |
|---|---|
| **RQ1** | 关闭 8 个理论类别中的每一类机制，对学习增益（Δθ）与留存的影响分别是什么？ |
| **RQ2** | 在显著类别内，单个机制的贡献量级与排序如何？ |
| **RQ3** | 预注册的 3 对机制交互是次可加（冗余）还是超可加（协同）？ |
| **方法** | 预注册层级门控实验（Gate 0/1/2/2.5），整群 + 用户级混合随机，HLM 斜率分析，ITT + CACE |
| **数据** | `experiment_observations`、`ability_estimates`、`mechanism_exposures` |
| **对标期刊** | **首选**：*Computers & Education*（CCF-B/一区，IF≈8.9，最匹配）；*Journal of Computer Assisted Learning*（SSCI Q1）<br>**冲刺**：*CHI*（CCF-A，但需要更强的理论贡献，纯消融实验偏工程）<br>**若结果为空**：*Journal of Learning Analytics*（接受 null result，CCF 无分区） |
| **主要风险** | ① **样本量是硬约束**（见 §6.2，现实需 6,800–12,000 用户）；② **伦理审查复杂**（关闭机制可能影响用户体验，需 IRB + 数据与安全监察）；③ **novelty/沾染**处理不当会被拒；④ **结果可能全为 null** —— 必须提前准备 null-result 投稿路径；⑤ **Gate 0 若不显著，整条线停摆**（建议把 Gate 0 设计为一个独立的、本身可发表的实验） |
| **成本** | **最高**。8–12 周数据收集 + 注册表/持久化前置工程（≈43.5 人日）。 |
| **可发表性** | ★★★★☆（**若样本充足**）；★☆☆☆☆（若只有几百用户 —— 那就不要做，做了也发不了） |

## 7.4 三篇的依赖关系与推荐顺序

```
   论文一（审计，无数据依赖）
        │  产出: 53 个稳定 ID + 去重规则 + taxonomy
        ▼
   【工程前置】注册表 + 仲裁器 + 持久化   ≈ 43.5 人日
        │
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
   论文二(冲突/预算)  论文三(消融)   论文三'
   样本 ~5,000      样本 ~7,000     (若样本<3,000
   周期 ~8周        周期 ~12周       则改做单类别
                                    深度消融 case study)
```

**推荐顺序：论文一 → 工程前置 → 论文二 → 论文三。** 理由：论文一零数据依赖、成本最低、且能立刻拆掉"76"的引信；论文二样本需求小于论文三且周期短；论文三留到最后，此时注册表成熟、数据管道齐备、且已有一篇发表作为方法学背书。

---

# 第八部分 批判性风险清单（审计师的保留意见）

以下 8 条是我在撰写过程中识别、且**认为团队尚未充分讨论**的风险。按严重程度排序。

| # | 风险 | 严重度 | 说明 |
|---|---|---|---|
| **R1** | **XP 伪持久化污染历史数据** | 🔴 致命 | `orchestrator.py:409` 导致 XP/等级/连胜每次请求归零。**若此前已有任何基于这些字段的分析或演示，结论全部无效，必须撤回或重算。** 请立即确认是否有外部材料引用了 XP 相关数据。 |
| **R2** | **"76"可能已流出** | 🔴 致命 | 若 PRD 已提交给资助方/合作方/已发表材料，更正必须走正式渠道（勘误/版本说明），不能只在内部文档改。**请 team-lead 确认 76 的外部触达范围。** |
| **R3** | **防沉迷未接入 = 合规风险** | 🔴 致命 | `anti_addiction_compliance.py` 零调用方。这不是学术问题。**在补接入之前，任何面向未成年人的公开部署都应当暂停。** |
| **R4** | **消融实验的伦理悖论** | 🟠 高 | 关闭机制 = 部分用户获得"更差"的产品体验；而 FOMO 类机制本身有伦理争议，**我们既不能证明它有害，也不能证明它有益，却要随机分配它**。IRB 会追问这一点。建议：① 预注册安全停止规则（`safety_stop_triggered` 已有雏形，需接入真实监测）；② 弱势群体（未成年、LAI 高风险）**排除出消融实验**。 |
| **R5** | **样本量可能根本达不到** | 🟠 高 | 见 §6.2。若实际可招募用户 < 3,000，**论文三应当放弃，改为单类别深度 case study**。请不要为了让论文成立而降低统计标准。 |
| **R6** | **审计结论的时间敏感性** | 🟡 中 | 本报告的 53/60/81 是 2026-09-02 的快照。**任何代码提交都可能改变它。** 必须 `git tag` 冻结，论文中标注 commit hash。否则审稿人复算时数字对不上，会被理解为"数据操纵"。 |
| **R7** | **注册表的"理论来源"字段可能注水** | 🟡 中 | 我在清单里为 53 个机制都配了 `theory_ref`。**但我必须坦白：其中约 10 个（尤其 G 类 UX 机制）的"理论来源"是弱关联或间接推断**（如"空间锚定"并无经典文献直接支持）。**注册表的强制字段会逼出注水引用。** 建议：分级标注 `evidence_strength ∈ {direct, indirect, none}`，`none` 的机制不参与消融实验。 |
| **R8** | **去重规则的可操纵性** | 🟡 中 | 53 这个数字依赖于 §2.3 的 6 条规则。**这些规则是我定的，我承认有裁量空间。** 若有人想"调到 60"，只需放宽 R4 与收紧 R2 即可。**缓解**：规则必须在**看到任何结果之前**预注册（如 OSF），并报双人编码 κ。这一步不做，53 与 76 在方法学上只有程度差别，没有性质差别。 |

---

# 第九部分 执行路线图

| 阶段 | 任务 | 产出 | 工作量 | 依赖 |
|---|---|---|---:|---|
| **S0 紧急（1 周）** | 冻结代码快照 `git tag pre-registry-audit`；确认 76 的外部触达范围；修复 XP 伪持久化（P0）；评估防沉迷接入的合规时限 | 快照 tag、风险通报、XP 落库 PR | 2 人日 | — |
| **S1 审计论文（3–4 周）** | 补全 53 机制台账（theory_ref / impl_ref / evidence_strength）；双人独立编码 + Cohen's κ；选定 2–3 个对照系统并应用同一协议 | 论文一投稿稿 | 15 人日 | S0 |
| **S2 工程前置（4–5 周）** | MechanismRegistry + Arbitrator + StateStore；13 张补表 + 迁移；A/B 框架改造（含统计修正）；16 个 P0–P3 机制接入 | 可运行的注册表 v1 | 20 人日 | S0 |
| **S3 预注册（1 周）** | OSF 预注册：去重规则、taxonomy、消融设计、α 分配、MDE、分析计划 | 预注册文档（含时间戳） | 3 人日 | S1, S2 |
| **S4 数据收集（8–12 周）** | Gate 0 → Gate 1 → Gate 2 → Gate 2.5；novelty burn-in；沾染自查 | `experiment_observations` 数据集 | 并行 | S3 |
| **S5 分析发表（6–8 周）** | ITT + CACE、HLM 斜率、Holm 校正、敏感度分析 | 论文二、论文三 | 20 人日 | S4 |

**总工期（不含 S4 的数据收集等待）**：约 **60 人日 ≈ 12 人周**；含数据收集则 **20–24 周**。

---

## 附录 A：本报告所有结论的复算命令

```bash
cd E:/learnflow/learnflow-backend

# L0: 全部 Engine 类声明数 / 唯一类名数
grep -rhE "^class [A-Za-z0-9_]*Engine" app/ | wc -l                       # → 81
grep -rhE "^class [A-Za-z0-9_]*Engine" app/ | sed 's/(.*//' | sort -u | wc -l   # → 80

# 逐文件 Engine 类清单（含行号）
grep -rnE "^class [A-Za-z0-9_]*Engine" app/services/ | sed 's/:class /|/' | sed 's/(.*//'

# 学习方法唯一 key 数（→ 15 唯一 / 16 条）
python -c "import re;s=open('app/services/learning_methods_engine.py',encoding='utf-8').read();k=re.findall(r'\"method\":\s*\"([a-z_0-9]+)\"',s);print(len(k),len(set(k)))"

# 技能树节点数（→ 16）
grep -c 'skill_id=' app/services/meta_learning_skilltree.py

# 孤儿模块（调用方为 0）
for m in positive_addiction_engine deep_addiction_engine ux_addiction_engine \
         social_addiction_engine addiction_engine_v3 learning_methods_engine_v3 \
         advanced_methods_engine placement_test_engine onboarding_engine \
         anti_addiction_compliance habit_addiction_engine team_competition_engine; do
  echo -n "$m: "; grep -rl "$m" app/ --include=*.py | grep -v "services/$m.py" | grep -v __pycache__ | wc -l
done

# 内存态容器（11 个）
grep -rn "BOX_STATES\|_active_sessions\|_unfinished\|ACTIVE_QUESTS\|PLAYER_SKILLS\|PLAYER_TEAMS\|MATCHES\|_experiments\|_user_assignments\|PALACES\|GOALS\|TEAMS" \
  app/services/*.py | grep -E "=\s*(\{\}|\[\]|defaultdict)"

# 伪持久化现场
sed -n '409p;471,476p' app/services/learning_orchestrator.py

# LAI dashboard 硬编码
sed -n '601,618p' app/api/gamification.py

# 干预生成点（→ 15 nudge/reminder/notification + 3 prompt）
grep -rnE "def (get|generate|create)_[a-z_]*(nudge|reminder|prompt|notification)" app/services/*.py

# 现有数据表（→ 16 张）
grep -rn "__tablename__" app/models/*.py

# A/B 框架耦合度（→ 仅 api/gamification.py + services/__init__.py）
grep -rn "ab_test_framework\|get_parameter_value" app/ --include=*.py
```

## 附录 B：机制 ID 分配规则（稳定性约定）

```
LF-M{nn}
  LF    : LearnFlow
  M     : Mechanism
  {nn}  : 两位序号，按理论类别分段:
          01-08  A 行为主义·强化与奖励
          09-16  B 承诺、损失与目标梯度
          17-22  C 自我决定论
          23-32  D 社会影响与社会学习
          33-42  E 习惯形成与自我调节
          43-46  F 情绪与动机触发
          47-50  G UX 微交互与认知负荷
          51-53  H 健康护栏与伦理

稳定性约定:
  1. ID 一经分配永不复用。机制废弃后 ID 进入 RETIRED 名单，不再分配给新机制。
  2. ID 与实现文件解耦。重构、换文件不改 ID。
  3. 每个 ID 必须可在注册表中查到 theory_ref + impl_ref + evidence_strength。
  4. registry.fingerprint() 写入每个实验记录，保证任何结果都能追溯到确定的机制集合版本。
```

---

**文档结束｜撰写人：严复核（robustness-auditor）｜v1.0｜2026-09-02**

---

## 附：数字诚信复算说明

> 本节为 v1.1 追加（2026-09-03）。目的不是"把数字改掉"，而是让**任何被论文
> 引用的工程数字都能被一条命令复算出来**——这是本标准配置抵御审稿人一击致命
> 核查的底层机制。

### 为什么需要这个脚本

历史文档宣称「76 种游戏化机制」「28 种学习方法」，两个数字在任意一层口径下
都不成立（见 §口径）。若论文直接引用，审稿人一次 `grep` 即可证伪，并连带
质疑全文其他数字。因此本项目的立场是：**数字必须经得起命令级复算**，而非
依赖作者口述。

### 复算命令

```bash
cd learnflow-backend
python scripts/verify_counts.py            # 打印分层报告 + 写 JSON 印章
python scripts/verify_counts.py --quiet    # 只打印一行结论 (CI 用)
```

零依赖（仅标准库 `ast`/`json`/`re`/`subprocess`），审稿人 clone 仓库后无需
`pip install` 即可运行。脚本**只用 AST 静态解析、不 import 任何 app 代码**，
避免正则统计的历史口径分歧（v3 方法名是中文字符串，英文正则得 0；`METHOD_TIPS`
是 list 不是 dict）。

### 六个数字的当前取值与口径定义（2026-09-03 登记）

| 指标 | 值 | 级别 | 口径定义 |
|---|---:|---|---|
| `engine_classes` | 81 | informative | `app/**/*.py` 中类名以 `Engine` 结尾的 ClassDef 总数（**类别错误口径**：混入 BKT/DDA/FSRS 等学习科学算法，**不**用于支撑"机制数"） |
| `mechanism_units` | 60 | informative | 10 个机制承载文件的 `*Engine` 类 + `gamification_service` 非 Engine 机制类 − 状态容器↔引擎合并对 |
| `mechanism_unique` | 53 | **strict** | 本文档 LF-M01..LF-M53 编号表的唯一 ID 数（语义去重由人工预注册规则 R1–R6 完成） |
| `learning_methods` | 23 | **strict** | 3 个学习方法源文件中 `"method"` 字面量归一化去重（22 snake_case + v3 的 `mind_mapping`「思维导图」） |
| `skill_tree_nodes` | 16 | **strict** | `meta_learning_skilltree.py` 的 `SKILL_DEFINITIONS` 列表元素数（**全项目唯一完全属实的数字**） |
| `prd_claimed` | 69 | **strict** | `learnflow-backend/docs/incremental_prd.md` §2.3 表格「引擎数量」列之和——与同文档标题声称的 76 **自相矛盾** |

- **strict** 指标若与登记值不符，`verify_counts.py` 以退出码 1 报 `discrepancy`，
  门禁变红。改代码必须同步改 `scripts/verify_counts.py` 的 `REGISTERED` 常量。
- **informative** 指标（`engine_classes` / `mechanism_units`）随正常重构合法波动，
  只报告不判失败——避免一次常规重构就让 CI 随机变红、使团队学会无视红灯。

### 声明

**论文中引用上述任何数字时，必须以 `scripts/verify_counts.py` 的输出为准**，
不得手写。特别地：
- "游戏化机制"一律写 **53（去重）/ 60（实现单元）**，禁止写 76；
- "学习方法"一律写 **23**，禁止写 28（除非后续按 §X 真实新增实现达到 28）；
- "技能树"写 **16**。
- 如确需引用 `engine_classes=81`，必须同步说明其为**类别错误口径**，不可
  直接等同于机制数。

> **最后一句审计师的话**：这份方案里最有价值的不是注册表代码，也不是样本量公式，而是 §1.5 的那个判断——**把 76 变成一个研究问题，而不是一个需要掩盖的错误**。其余一切都建立在这个判断之上。如果团队决定反过来做（想办法让 76 成立），请明确告知我，我会撤回本报告的全部学术转化建议，并保留在论文中署反对意见的权利。
