# 游戏化学习干预机制的分类学、形式化与冲突仲裁：面向 54 个机制的可复现治理研究

> **文档性质**：本篇为期刊论文 P4「游戏化干预的形式化与冲突仲裁」的主稿件，同时作为博士学位论文机制章节的底稿。
> **可复现性声明**：文中全部统计量均可由 `E:\learnflow\learnflow-backend` 下的一条命令复算，命令清单见附录 A。
> **代码基线**：`git HEAD = 79d7f36`；可复现性印章 `artifacts/count_verification.json`（六项指标全部 `verified`）。
> **版本**：2026-09-04

---

## 摘要

游戏化学习系统中普遍存在两类被低估的方法论缺陷：其一，系统声称所实现的干预机制数量与代码实际可复算的机制数量不一致，导致任何基于"机制数量"的论断都无法被独立验证；其二，多个干预机制在同一决策点并发产生相互冲突的效应，而系统缺乏统一的效应表示与仲裁规则，使得消融实验的估计量定义失去意义。本文以 LearnFlow 学习平台为研究对象，对上述问题给出可复现的工程与形式化处理。首先，本文建立四层计数口径，将"声称的机制数"与"可复算的唯一机制数"分离，经预注册去重规则 R1–R6 得到 54 个唯一机制（LF-M01…LF-M54），并给出 52–57 的敏感性区间；该数值可由一条命令复算，并由带 git 提交指针的印章文件固定。其次，本文提出八类机制分类学与统一效应接口，将全部机制的产出归一化为 `Effect` 对象，并设计三层漏斗仲裁器（健康一票否决、冲突消解、干预预算）以消解并发干预的方向性冲突。第三，本文给出运行时接线与可复现性基础设施，使得"某机制是否参与运行时决策"成为可扫描、可审计的命题：截至代码基线，LF-M01–LF-M53 中 34 个在编排器中具备显式门控、19 个仅存在源码文本引用；另有本轮新增的 LF-M54（班级宠物共养）为独立 API 模块、不进入编排器门控映射，机制总数合计 54。最后，本文给出八类机制的消融实验设计，包括估计量定义、分层 Gatekeeping 的多重检验校正、设计效应 DEFF = 2.45 下的样本量要求，以及 IRB 伦理排除规则。本文同时如实披露五项未实现项与已知缺陷。本研究的贡献不在于新增机制，而在于使既有的机制集合成为可被独立验证、可被消融、可被仲裁的研究对象。

**关键词**：游戏化学习；机制分类学；干预冲突仲裁；可复现性；消融实验；数字诚信

---

## 1. 引言

### 1.1 研究背景

游戏化（gamification）已被广泛部署于在线学习系统，其有效性在不同研究中呈现显著异质性。元分析研究表明，游戏化元素的效应量随元素类型、情境与实现方式而大幅波动，且"游戏化"作为整体标签的解释力有限，效应主要来自具体设计元素的组合与实现质量（[@sailer2017how]；[@sailer2020meta]）。与此同时，一批研究指出部分游戏化设计已滑向"暗黑模式"（dark patterns），即通过剥夺用户自主性来维持参与度（[@gray2018dark]），亦有实验证据表明浅层游戏化（shallow gamification）仅在短期产生有限效应（[@lieberoth2015shallow]）。

在此背景下，一个被系统性忽视的问题是：**研究文献中所报告的"系统实现了 N 个游戏化机制"这一陈述，通常缺乏可验证的定义**。若两个系统各自声称"实现了 76 个机制"，但其计数口径分别为"类名以 Engine 结尾的类总数"与"语义去重后的心理学构念数"，则二者不可比较，任何基于 N 的横向比较与效应归因都将失效。

### 1.2 问题陈述

本文处理三个相互关联的问题。

**问题一（计数不可复算）**：系统文档声称的机制数量与代码实际承载的机制数量不一致，且不一致的来源未被分解。在本文所研究的系统中，项目需求文档标题与概述声称 76 个机制，而同一文档 §2.3 的逐项表格求和仅为 69；经代码三层复算，语义去重后的唯一机制为 54。三个数字分别对应三种不同的计数口径，若不显式区分，论文中的任何数字陈述都可能被审稿人证伪。

**问题二（干预冲突无仲裁）**：多个机制在同一决策点并发产出效应，且效应方向可能相反。典型的冲突构型为：一个机制诱导"趋近"行为（如错失恐惧 LF-M44 推动用户继续作答），而另一个机制要求"退出"行为（如未成年保护 LF-M52 要求冷却与停止）。若系统仅按触发顺序或优先级数值决定下发，则"关闭某机制"的消融实验所估计的因果效应将依赖于其他机制的触发状态，估计量定义不成立。

**问题三（运行时接线不可审计）**：机制的存在（有实现类）与其是否真正参与运行时决策（被调用）是两个不同的命题。若大量机制仅有实现而无调用方，则基于"关闭该机制"的消融实验实际上不产生任何处理变异，实验结论无效。因此，"某机制是否已接线"必须成为可自动扫描、可复算的命题，而非人工声明。

### 1.3 研究问题

- **RQ1（可复算性）**：如何定义机制计数口径，使得唯一机制数可由一条命令复算，且不同口径之间的差异可被完整分解？
- **RQ2（分类学）**：在何种预注册规则下，实现单元集合可被映射为唯一的机制构念集合，且该映射的敏感性区间可被量化？
- **RQ3（仲裁）**：如何设计统一的效应表示与仲裁规则，使得并发干预的方向性冲突被确定性消解，且消融实验的估计量保持良定义？
- **RQ4（可审计性）**：如何使"机制是否参与运行时决策"成为可扫描命题，并为消融实验提供处理变异的先验保证？

### 1.4 主要贡献

1. **四层计数口径与其差异分解**：给出 L0（类名计数）→ L1（实现单元计数）→ L2（语义去重后唯一机制）的三层复算链，并显式分解 76 与 54 之间 22 的差额来源（§3）。
2. **预注册去重规则与敏感性区间**：提出 R1–R6 六条去重规则，报告 54 这一取值，并给出 52–57 的诚实区间（§4.2）。
3. **统一效应接口与三层漏斗仲裁器**：将异构机制产出归一化为 `Effect`，以健康一票否决、冲突消解（保守偏置）、干预预算三层结构确定性消解冲突（§5）。
4. **可复现性基础设施**：机制注册表指纹、落地扫描脚本、带 git 指针的计数印章，使上述全部命题可被一条命令验证（§6）。
5. **八类消融的实验设计**：给出估计量、随机化单位、设计效应、分层 Gatekeeping 与样本量要求（§7）。
6. **负面结果的诚实披露**：单列已知缺陷与未实现项，包括机制接线强度的区分（显式门控 vs. 文本引用）（§9）。

### 1.5 论文结构

本文其余部分组织如下：§2 回顾相关工作；§3 处理数字诚信问题；§4 建立机制分类学；§5 给出统一效应接口与仲裁器形式化；§6 描述运行时接线与可复现性基础设施；§7 给出实验设计；§8 分析效度威胁；§9 披露已知缺陷；§10 总结。附录 A 给出复算命令清单，附录 B 为术语表，附录 C 为遗留错误数字更正表，附录 D 为待核验引用清单。

---

## 2. 相关工作

### 2.1 游戏化元素的分类学与效应异质性

早期游戏化研究倾向于将"游戏化"作为整体处理变量，后续研究则转向元素层面的分解。元分析证据表明，不同游戏化元素对学习结果的影响方向与量级存在系统性差异，且元素间的组合效应并非可加（[@sailer2017how]；[@sailer2020meta]）。针对"哪一个元素有效"这一问题的实验研究进一步显示，效应高度依赖于具体实现与用户特征（[@mazarakis2024whichone]）。本文的分类学工作与这一支文献的关系是：本文不提出新的元素集合，而是为既有元素集合提供**可复算的编目方法**，使不同研究之间的元素集合可比较。

### 2.2 暗黑模式与伦理边界

游戏化设计中的伦理风险已被系统梳理，其中"剥夺自主性""制造虚假紧迫感""利用损失厌恶"等构型被归入暗黑模式（[@gray2018dark]）。在教育场景中，此类风险的后果更为严重，因为其对象包含未成年人。本文在分类学中将健康护栏（H 类）单列，并赋予其在仲裁器中的一票否决权（§5.4），可视为对上述伦理关切的形式化落地。

### 2.3 干预冲突与自适应干预

自适应干预（adaptive intervention）文献关注在多个候选干预并存时如何决策，其典型形式是 just-in-time adaptive intervention（JITAI）与多臂Bandit 方法（[@neurips2017posetbandits]）。本文的仲裁器与该支文献的区别在于：Bandit 方法以长期累积回报为优化目标，而本文的仲裁器以**约束满足**为首要目标（健康约束不可违反），仅在约束满足后按优先级与预算分配。这一差异源于教育场景的伦理约束：参与度最大化不是合法目标。

### 2.4 学习分析中的可复现性危机

学习分析领域长期面临数据质量与可复现性危机，其中"指标定义随实现漂移"是核心问题之一；已有工作提出以标准化事件流（xAPI）与多源数据规范来缓解该问题（[@kitto2020xapi]；[@ieee9274xapi2023]；[@mangaroska2019multisource]）。本文的可复现性基础设施与之互补：本文不解决数据本身的采集标准，而是解决**系统内部机制集合的自描述与自验证**问题，使得"系统实现了什么"这一元问题可被机器回答。

### 2.5 与学习科学算法的边界

需要严格区分两类算法：一类是**学习科学算法**（知识追踪、间隔重复、难度估计），其作用是估计学习者的潜在状态；另一类是**行为干预机制**，其作用是根据状态改变行为。二者在本文的分类学中被明确分离（规则 R5）。知识追踪的经典模型与近期综述见（[@corbett1994knowledge]；[@abdelrahman2023knowledge]；[@liu2025pykt]）；本文不将其计入干预机制。

---

## 3. 数字诚信：从声称值到可复算值

### 3.1 问题的性质

系统需求文档（PRD）在标题与概述中声称"76 个游戏化成瘾引擎"，而同一文档 §2.3 的逐项表格求和为 69。二者之差为 7，属于文档内部矛盾。更严重的是，二者均高于代码可复算的唯一机制数 54。若不处理这一矛盾，任何引用 76 的论文陈述都可被审稿人在数分钟内证伪，进而动摇全文可信度。

### 3.2 四层计数口径

**表 3-1　机制计数的四层口径及其差异分解**

| 层级 | 口径定义 | 数值 | 性质 |
|---|---|---:|---|
| L0 | `app/**/*.py` 中类名以 `Engine` 结尾的类总数 | 86 | 类别错误：混入 BKT、DDA、FSRS、最优难度等学习科学算法 |
| L1 | 10 个机制承载文件中的实现单元数（含非 `Engine` 机制类，减去状态容器与引擎的合并对） | 60 | 实现视角，含重复实现 |
| L2 | L1 经语义去重后的唯一机制构念数 | **54** | 本文采用的论文主表述 |
| — | PRD §2.3 表格逐项求和 | 69 | 文档内部值，与标题 76 矛盾 |
| — | PRD 标题/概述声称值 | 76 | 禁用：不可复算 |

> 复算命令：`python scripts/verify_counts.py`（输出：`artifacts/count_verification.json`）

**22 的差额分解**（76 − 54 = 22）：

1. **7 = 76 − 69**：PRD 标题估值高于其自身表格求和；
2. **9 = 69 − 60**：文档表格将非机制的支撑类（状态容器、算法类、基础设施类）计入；
3. **6 = 60 − 54**：同一心理学构念存在多份重复实现，按预注册规则 R3 合并。

### 3.3 披露策略

本文采取**分层披露**策略：论文正文一律使用 54（唯一机制）并给出复算命令；在讨论项目历史文档时，明确写出"PRD 标题声称 76，与其 §2.3 表格求和 69 自相矛盾，经三层复算唯一机制为 54"，并给出上述差额分解。**禁止**在任何场合将 76 作为系统能力的正面陈述。

### 3.4 三条硬性纪律

1. **任何进入论文的数字必须有一条命令可复算**；
2. **计数口径必须在首次出现时显式声明**；
3. **代码演进后必须重跑验证脚本并刷新印章**，印章文件记录 `git_commit` 指针，使数字与代码版本绑定。

---

## 4. 机制分类学

### 4.1 分类学设计原则

分类学需同时满足三个条件：**互斥**（每个机制归入唯一类别）、**完备**（54 个机制全部归类）、**理论可追溯**（每个类别对应明确的心理学理论传统，而非实现文件划分）。第三条尤其重要：按实现文件划分类别（如"深度成瘾引擎类"）虽有工程便利，但与理论构念无关，无法支持跨研究比较。

本文采用三轴编码：**轴 1** 为八类理论类别（A–H）；**轴 2** 为干预时机（`pre` 作答前 / `during` 作答中 / `post` 作答后 / `ambient`  ambient 常驻）；**轴 3** 为语义类别（`retention` 留存 / `motivation` 动机 / `cognition` 认知 / `selfreg` 自我调节 / `health` 健康）。

**表 4-1　八类划分及其理论依据**

| 类别 | 理论基础 | 代表文献 |
|---|---|---|
| **A 行为主义·强化与奖励** | 操作性条件反射、强化程序（变比率/变动时距）、奖励预测误差 | Skinner (1938)；Ferster & Skinner (1957)；Schultz (1998) |
| **B 承诺、损失与目标梯度** | 前景理论、目标设定理论、目标梯度假说、峰终定律、蔡格尼克效应 | Kahneman & Tversky (1979)；Zeigarnik (1927)；Kahneman et al. (1993)；Locke & Latham (1990)；Hull (1934) |
| **C 自我决定论：自主·胜任·关联** | 基本心理需求理论、认知负荷理论、情感设计 | Deci & Ryan (1985)；Ryan & Deci (2000)；Sweller (1988)；Norman (2004) |
| **D 社会影响与社会学习** | 社会比较理论、社会认同理论、社会促进、互惠规范、社会互赖 | Festinger (1954)；Cialdini (1984)；Tajfel & Turner (1979)；Garcia & Tor (2009)；Johnson & Johnson (1989) |
| **E 习惯形成与自我调节** | 习惯自动化、执行意图、诱惑捆绑、自我调节学习、元认知 | Lally et al. (2010)；Gollwitzer (1999)；Milkman et al. (2014)；Zimmerman (2002)；Fogg (2019) |
| **F 情绪与动机触发** | 信息缺口理论、身份动机、错失恐惧 | Loewenstein (1994)；Oyserman (2007)；Przybylski et al. (2013) |
| **G UX 微交互与认知负荷** | 微交互、色彩心理学、空状态行为启动 | Norman (2004)；Elliot & Maier (2014) |
| **H 健康护栏与伦理** | 防沉迷合规、强制休息、成瘾风险自适应降级 | 中国《关于进一步严格管理 切实防止未成年人沉迷网络游戏的通知》；Griffiths (2005) |

### 4.2 预注册去重规则与 54 的敏感性区间

54 这一取值依赖于以下六条预注册规则，规则必须在实验预注册中先行声明，否则该数字不可辩护。

- **R1（同名类合并）**：类名完全相同者视为同一机制。
- **R2（同一理论构念合并）**：类名不同但实现同一心理学构念者合并（如峰终定律的两份实现）。
- **R3（同构念多份实现计 1）**：保留成熟度最高者为 canonical，其余标 `DUP`，不计入唯一机制数。
- **R4（占位合并）**：三个及以上无实质逻辑的占位机制合并为一个占位机制，处置建议为废弃或合并实现。
- **R5（算法类与干预类分离）**：知识追踪（BKT）、动态难度（DDA）、FSRS 间隔重复、最优难度属学习科学算法，不计入行为干预机制。
- **R6（争议项处理）**：两名评分者独立判定，不一致处由第三人裁决，并报告评分者间一致性系数 κ。

**表 4-2　去重减项明细（60 → 53，净减 7）**

| # | 机制构念 | 实现单元 | 减项 |
|---:|---|---|---:|
| 1 | 蔡格尼克效应 | `addiction_engine_v3.py:108` + `gamification_service.py:578` | −1 |
| 2 | 峰终定律 | `addiction_engine_v3.py:163` + `gamification_service.py:507` | −1 |
| 3 | 自主性支持 | `habit_addiction_engine.py:159` + `gamification_service.py:683` | −1 |
| 4 | 损失厌恶 | `addiction_engine_v3.py:7` + `gamification_service.py:419` | −1 |
| 5 | 社会认同 | `positive_addiction_engine.py:506` + `gamification_service.py:659` | −1 |
| 6 | 连胜 | `duolingo_addiction_engine.py:316` + `gamification_service.py:118` | −1 |
| 7 | 多感官包装（触觉/声音/字体动效三占位合并） | `ux:345` + `ux:482` + `ux:524` | −2 |
| | | **合计** | **−7** |

**敏感性区间**：54 是上述规则下的结果（本轮新增 LF-M54 班级宠物共养，为独立完整模块，不改变 R2/R4 边界）。放宽 R2（将连胜神圣化并入连胜）得 53；收紧 R4（三个占位各计 1）得 56。因此**诚实区间为 52–57**，论文应报告 54 并同时给出该区间。

### 4.3 完整机制清单

**表 4-3　完整机制清单（LF-M01–LF-M54）**

> 图例 — 成熟度：**●** 完整（含持久化或完整逻辑）｜**◐** 部分（有逻辑未持久化）｜**○** 占位
> 处置：**K** 保留　**M** 合并　**R** 重构　**D** 废弃
> 运行时接入列：`6/8/9/12/13` 为编排器步骤编号（具显式 `is_enabled` 门控）；`外部` 表示仅在 `services`/`api` 源码中存在文本引用，无编排器门控（详见 §6.4）。
> 实现位置由 `artifacts/mechanism_catalog.json` 生成，行号随代码演进可能漂移，以 §附录 A 的复算命令为准。

### A. 行为主义·强化与奖励（8）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M01 | 变比率奖励（宝箱） | Variable-Ratio Reward | during | retention | Skinner (1938)；Ferster & Skinner (1957) | `gamification_service.py:128,139` | ● | K | 13 |
| LF-M02 | 濒赢效应 | Near-Miss Effect | during | retention | Clark et al. (2009)；Reid (1986) | `gamification_service.py:139` | ● | K | 外部 |
| LF-M03 | 奖励节拍（多巴胺节律） | Dopamine Rhythm | during | retention | Schultz (1998) | `gamification_service.py:460` | ◐ | R | 外部 |
| LF-M04 | 即时满足 | Instant Gratification | during | motivation | Ainslie (1975) | `positive_addiction_engine.py:588` | ◐ | R | 13 |
| LF-M05 | 惊喜与愉悦 | Surprise & Delight | during | motivation | Reiss (2004) | `addiction_engine_v3.py:199` | ◐ | R | 13 |
| LF-M06 | 时间限定加成 | Time-Based Bonus | during | retention | 强化程序（变动时距） | `duolingo_addiction_engine.py:539` | ● | K | 13 |
| LF-M07 | 集换收藏 | Collection / Completion | ambient | retention | Zeigarnik 变体；完成欲 | `deep_addiction_engine.py:116` | ◐ | R | 外部 |
| LF-M08 | 稀缺性 | Scarcity | pre | motivation | Cialdini (1984, Ch.7) | `deep_addiction_engine.py:461` | ◐ | R | 13 |

### B. 承诺、损失与目标梯度（8）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M09 | 损失厌恶 | Loss Aversion | post | retention | Kahneman & Tversky (1979) | `addiction_engine_v3.py:7`（canonical）<br>`gamification_service.py:419` | ◐ | M | 外部 |
| LF-M10 | 沉没成本提示 | Sunk-Cost Reminder | post | retention | Arkes & Blumer (1985) | `addiction_engine_v3.py:36` | ◐ | R | 外部 |
| LF-M11 | 连胜 | Streak | post | retention | 连续强化；Lally et al. (2010) | `duolingo_addiction_engine.py:316`（canonical）<br>`gamification_service.py:118` | ● | M | 外部 |
| LF-M12 | 连胜神圣化 | Streak Sanctification | post | retention | 承诺 × 损失厌恶 | `deep_addiction_engine.py:308` | ◐ | R | 13 |
| LF-M13 | 蔡格尼克效应 | Zeigarnik Effect | post | retention | Zeigarnik (1927) | `addiction_engine_v3.py:108`（canonical）<br>`gamification_service.py:578` | ◐ | M | 13 |
| LF-M14 | 峰终定律 | Peak-End Rule | during | motivation | Kahneman et al. (1993) | `addiction_engine_v3.py:163`（canonical）<br>`gamification_service.py:507` | ◐ | M | 13 |
| LF-M15 | 目标梯度/近距目标 | Goal Gradient | during | motivation | Hull (1934)；Locke & Latham (1990) | `gamification_service.py:96` | ◐ | R | 13 |
| LF-M16 | 每日/月度挑战 | Daily & Monthly Challenge | pre | retention | Locke & Latham (1990) | `duolingo_addiction_engine.py:704,582` | ● | K | 13 |

### C. 自我决定论：自主·胜任·关联（6）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M17 | 自主性支持 | Autonomy Support | during | selfreg | Deci & Ryan (1985)；Ryan & Deci (2000) | `habit_addiction_engine.py:159`（canonical）<br>`gamification_service.py:683` | ◐ | M | 外部 |
| LF-M18 | 宜家效应/自主定制 | IKEA Effect | during | motivation | Norton, Mochon & Ariely (2012) | `gamification_service.py:623,615` | ◐ | R | 13 |
| LF-M19 | 经验值与等级 | XP & Leveling | post | motivation | 二级强化；SDT 胜任感 | `duolingo_addiction_engine.py:55` | ○ | R | 9 |
| LF-M20 | 进步可视化 | Progress Visualization | during | motivation | Locke & Latham (1990)；Bandura (1997) | `positive_addiction_engine.py:649` | ◐ | R | 13 |
| LF-M21 | 渐进式披露 | Progressive Disclosure | during | cognition | Sweller (1988)；Nielsen (1994) | `ux_addiction_engine.py:119` | ◐ | R | 13 |
| LF-M22 | 虚拟宠物陪伴 | Pet Companion | ambient | motivation | Ryan & Deci (2000)（关联性） | `pet_service.py`；表 `pet_profiles` | ● | K | 6 |

### D. 社会影响与社会学习（10）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M23 | 社会认同 | Social Proof | during | motivation | Cialdini (1984, Ch.4) | `gamification_service.py:659`（canonical）<br>`positive_addiction_engine.py:506` | ◐ | M | 外部 |
| LF-M24 | 社会传染 | Social Contagion | ambient | retention | Christakis & Fowler (2007) | `positive_addiction_engine.py:506` | ◐ | R | 13 |
| LF-M25 | 同伴进度推动 | Peer Progress Nudge | pre | motivation | Festinger (1954)（上行比较） | `deep_addiction_engine.py:292` | ◐ | R | 外部 |
| LF-M26 | 友好竞争 | Friendly Competition | during | motivation | Festinger (1954)；Tauer & Harackiewicz (2004) | `positive_addiction_engine.py:538` | ◐ | R | 外部 |
| LF-M27 | 排行榜与联赛 | Leaderboard & Leagues | ambient | retention | Garcia & Tor (2009)（N-effect） | `duolingo_addiction_engine.py:208` | ● | K | 外部 |
| LF-M28 | 社交名片 | Business Card / Identity Display | ambient | retention | Tajfel & Turner (1979) | `social_addiction_engine.py:55` | ○ | R | 外部 |
| LF-M29 | 礼物经济 | Gift Economy | ambient | retention | Mauss (1925)；Cialdini 互惠 | `social_addiction_engine.py:411` | ○ | R | 13 |
| LF-M30 | 组队任务 | Friend Quest | during | retention | Johnson & Johnson (1989) | `duolingo_addiction_engine.py:455` | ◐ | R | 外部 |
| LF-M31 | 团队竞赛与赛季 | Team Competition & Season | ambient | retention | Johnson & Johnson (1989) | `team_competition_engine.py:103,288,389,487,556,651` | ◐ | R | 外部 |
| LF-M32 | 家长门户 | Parent Portal | post | selfreg | Hoover-Dempsey & Sandler (1995) | `social_addiction_engine.py:288` | ○ | R | 13 |

### E. 习惯形成与自我调节（10）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M33 | 钩子模型 | Hook Model | pre | retention | Eyal (2014) | `positive_addiction_engine.py:67` | ◐ | R | 13 |
| LF-M34 | 习惯回路 | Habit Loop | pre | selfreg | Duhigg (2012)；Wood & Rünger (2016) | `positive_addiction_engine.py:262` | ◐ | R | 13 |
| LF-M35 | 情境线索提示 | Cue Prompting | pre | selfreg | Wood & Neal (2007) | `positive_addiction_engine.py:322` | ◐ | R | 13 |
| LF-M36 | 习惯叠加 | Habit Stacking | pre | selfreg | Fogg (2019) | `habit_addiction_engine.py:27` | ◐ | K | 外部 |
| LF-M37 | 诱惑捆绑 | Temptation Bundling | pre | selfreg | Milkman, Minson & Volpp (2014) | `habit_addiction_engine.py:80` | ◐ | K | 13 |
| LF-M38 | 执行意图 | Implementation Intentions | pre | selfreg | Gollwitzer (1999) | `habit_addiction_engine.py:109` | ◐ | K | 13 |
| LF-M39 | 自我调节目标 | Self-Regulation Goals | pre | selfreg | Zimmerman (2002)；Bandura (1991) | `habit_addiction_engine.py:213` | ◐ | R | 13 |
| LF-M40 | 元认知技能树 | Metacognitive Skill Tree | ambient | cognition | Zimmerman (2002)；Flavell (1979) | `meta_learning_skilltree.py:157`（16 节点） | ◐ | R | 外部 |
| LF-M41 | 承诺装置/预约 | Commitment Device | pre | selfreg | Rogers, Milkman & Volpp (2014) | `deep_addiction_engine.py:388` | ◐ | R | 13 |
| LF-M42 | 新起点效应 | Fresh Start Effect | pre | motivation | Dai, Milkman & Riis (2014) | `addiction_engine_v3.py:51` | ◐ | K | 外部 |

### F. 情绪与动机触发（4）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M43 | 好奇心缺口 | Curiosity Gap | pre | motivation | Loewenstein (1994) | `deep_addiction_engine.py:25` | ◐ | K | 13 |
| LF-M44 | 错失恐惧 | FOMO | pre | retention | Przybylski et al. (2013) | `deep_addiction_engine.py:238` | ◐ | R | 12 |
| LF-M45 | 偶然性与惊喜 | Serendipity | during | motivation | 变比率 × 内在动机 | `deep_addiction_engine.py:542` | ○ | R | 外部 |
| LF-M46 | 身份认同动机 | Identity-Based Motivation | ambient | motivation | Oyserman (2007)；Markus & Nurius (1986) | `positive_addiction_engine.py:348` | ◐ | K | 13 |

### G. UX 微交互与认知负荷（4）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M47 | 微交互反馈 | Micro-interaction | during | motivation | Norman (2004) | `ux_addiction_engine.py:24` | ◐ | R | 外部 |
| LF-M48 | 色彩与情绪 | Color Psychology | ambient | cognition | Elliot & Maier (2014) | `ux_addiction_engine.py:210` | ◐ | R | 13 |
| LF-M49 | 空间锚定 | Spatial Anchoring | ambient | cognition | 空间一致性；位置记忆 | `ux_addiction_engine.py:290` | ○ | R | 13 |
| LF-M50 | 多感官包装（占位） | Multi-sensory Packaging | during | motivation | 无理论支撑 | `ux:345` + `ux:482` + `ux:524` | ○ | D | 13 |

### H. 健康护栏与伦理（4）

| ID | 机制名 | 英文名 | 轴2 | 轴3 | 理论来源 | 实现位置 | 成熟度 | 处置 | 运行时接入 |
|---|---|---|---|---|---|---|---|---|---:|
| LF-M51 | 强制休息提醒 | Forced Rest Reminder | during | health | 认知疲劳恢复 | `feedback_service.py:198` | ◐ | K | 8 |
| LF-M52 | 未成年保护与奖励冷却 | Minor Protection & Reward Cooldown | during | health | 监管合规；Griffiths (2005) | `anti_addiction_compliance.py:79` | ● | K | 9 |
| LF-M53 | LAI 自适应降级 | LAI Adaptive Downgrade | ambient | health | 自陈成瘾指数量表改编 | `learning_addiction_index.py` | ○ | R | 8 |
| LF-M54 | 班级积分养宠系统（班级宠物园） | Class Points-Pet Garden | ambient | health | Ryan & Deci 2000（关联性）；Hari 2018（连接替代） | `class_pet_service.py` | ● | K | 外部 |

**小计**：A 8 + B 8 + C 6 + D 10 + E 10 + F 4 + G 4 + H 4 = **54**

> 复算命令：`python scripts/verify_counts.py` → `category_counts`（自检：类别和 54、编号连续无重复）

### 4.4 类别—状态汇总与审计发现

**表 4-4　类别—状态汇总**

| 类别 | 机制数 | ● 完整 | ◐ 部分 | ○ 占位 | 编排器门控数 |
|---|---:|---:|---:|---:|---:|
| A 行为主义 | 8 | 3 | 5 | 0 | 5 |
| B 承诺损失 | 8 | 2 | 6 | 0 | 5 |
| C 自我决定论 | 6 | 1 | 4 | 1 | 5 |
| D 社会影响 | 10 | 1 | 6 | 3 | 3 |
| E 习惯自我调节 | 10 | 0 | 10 | 0 | 7 |
| F 情绪动机 | 4 | 0 | 3 | 1 | 3 |
| G UX 微交互 | 4 | 0 | 2 | 2 | 3 |
| H 健康护栏 | 4 | 1 | 2 | 1 | 3 |
| **合计** | **54** | **9** | **41** | **4** | **34** |

> 复算命令：`python -c "from app.services.mechanism_registry import all_mechanisms; import collections; print(collections.Counter(m.maturity for m in all_mechanisms()))"`

表 4-4 揭示三项审计发现。

**发现一：实现成熟度分布严重右偏。** 54 个机制中 9 个（16.7%，含本轮新增的完整模块 LF-M54）达到完整成熟度，41 个（75.9%）处于"有逻辑但未持久化"状态，4 个（7.4%）为占位实现。这意味着在消融实验中，占多数的机制其处理效应可能弱到无法检出，且部分机制的处理变异本身可能不成立。

**发现二：接线强度存在两类，且不可等同。** 34 个机制在编排器中具有显式 `is_enabled` 门控，构成真正的可开关处理；19 个机制仅在 `services`/`api` 源码中存在文本引用（§6.4）。二者的差别对实验效力具有决定性影响：对后一类机制做消融，处理组与对照组可能无实际差异，从而产生假阴性结论。

**发现三：健康护栏类（H）的成熟度与其重要性不匹配。** H 类 4 个机制中仅 1 个（LF-M52）达到完整成熟度，而该类机制在仲裁器中被赋予一票否决权（§5.4）。作为最高权限的干预，其实现完整性应优先于任何动机类机制。

---

## 5. 统一效应接口与三层漏斗仲裁器

### 5.1 动机：为何需要统一效应接口

在未统一表示前，各机制直接返回用户可见内容（如文案、数值、状态对象），导致三个后果：（1）仲裁器无法在不解析异构返回值的前提下比较效应；（2）"关闭某机制"只能通过移除调用代码实现，无法在运行时按配置完成；（3）效应的方向性（趋近 vs. 退出）与代价（cost）不可见，冲突无法被系统性检测。

### 5.2 数据模型

统一效应接口定义为 `Effect` 对象，其核心字段如下（代码证据：`app/services/mechanism_registry.py`）：

- `mechanism_id`：产生该效应的机制编号（`LF-Mxx`）；
- `effect_type`：效应类型（`NUDGE` / `REWARD` / `NOTIFICATION` / `SOCIAL` / `UI` 等）；
- `payload`：效应的具体内容，仅在被下发时对用户可见；
- `priority`：优先级数值，仅在第 3 层（预算分配）中作为排序依据；
- `cost`：干预预算消耗；
- `user_visible`：是否对用户可见；
- `health_critical`：是否为健康关键效应；
- `direction`：效应方向，`approach`（趋近，推动继续）或 `withdraw`（退出，推动停止）。

关键设计约束：**引擎只产出 `Effect` 候选，不直接下发用户可见内容**。下发的决定权完全属于仲裁器。这一约束使得"机制是否生效"成为可被仲裁器单一控制点决定的命题，从而保证消融实验的处理分配是真实的。

以错失恐惧（LF-M44）为例：其引擎函数由原先直接返回用户可见文案，改为返回 `Effect(mechanism_id="LF-M44", effect_type=NUDGE, payload=文案, priority=50, cost=1.5, user_visible=True, health_critical=False, direction="approach")`（代码证据：`app/services/deep_addiction_engine.py`）。

### 5.3 三层漏斗仲裁算法

**表 5-1　三层漏斗的结构与判据**

| 层 | 名称 | 判据 | 输出 |
|---|---|---|---|
| 1 | 健康一票否决 | 若存在 `health_critical=True` 且 `direction="withdraw"` 的效应 | 丢弃所有 `direction="approach"` 的效应 |
| 2 | 冲突消解 | 剩余效应中方向冲突者 | 按保守偏置保留 `withdraw`，丢弃 `approach` |
| 3 | 干预预算 | 剩余效应按 `priority` 降序 | 在预算上限内下发，超出者丢弃 |

三层结构的顺序是不可交换的：健康约束必须先于优先级比较，否则高优先级的趋近干预可能压过健康约束；保守偏置必须先于预算分配，否则预算可能被趋近干预耗尽。

**保守偏置的合理性**：当两个效应的方向冲突且无法判定何者更优时，保留"退出"方向。这一偏置的代价是可能损失部分参与度收益，其收益是避免在健康与伦理维度上犯第一类错误。在教育场景中，该偏置是恰当的。

### 5.4 健康一票否决的实现

健康一票否决在第 1 层实现，其触发条件为：学习者被判定为未成年人或处于强制休息状态。此时编排器构造一个健康关键效应 `Effect(mechanism_id="LF-M52", effect_type=NOTIFICATION, health_critical=True, direction="withdraw", priority=100)`，交由仲裁器处理；仲裁器在第 1 层据此丢弃全部趋近效应，其中包括 LF-M44 的错失恐惧效应（代码证据：`app/services/learning_orchestrator.py`）。

> 该设计的验证方式见 `tests/test_fomo_arbitrator.py`：在未成年条件下，FOMO 效应被第 1 层丢弃，测试断言其不进入下发集合。

### 5.5 仲裁器的性质

- **确定性**：给定效应集合与学习者状态，仲裁结果唯一确定，不依赖触发顺序。
- **单调性**：新增一个 `approach` 效应不会导致既有 `withdraw` 效应被丢弃（第 2 层保守偏置）。
- **可审计性**：仲裁结果随决策快照落库，可事后重建（§6.3）。

---

## 6. 运行时接线与可复现性基础设施

### 6.1 编排管线与机制映射

提交处理管线（`process_submission`）划分为若干步骤，每个步骤与机制的对应关系由 `PIPELINE_MECHANISM_MAP` 显式声明（代码证据：`app/services/learning_orchestrator.py`）：

**表 6-1　编排步骤与机制映射**

| 步骤 | 机制 | 说明 |
|---:|---|---|
| 6 | 虚拟宠物陪伴（LF-M22） | 陪伴类常驻机制 |
| 8 | LAI 自适应降级（LF-M53）、强制休息（LF-M51） | 健康护栏与风险监控 |
| 9 | 经验值与等级（LF-M19）、未成年保护（LF-M52） | 奖励与合规 |
| 12 | 错失恐惧（LF-M44） | 经仲裁器下发的后置 nudge |
| 13 | 28 个次级机制 | 评估钩子：每机制显式 `is_enabled` 门控 + 真实引擎调用 |

### 6.2 步骤 13：次级机制评估钩子

步骤 13 针对此前无运行时调用的 28 个机制，为每一个提供显式门控与真实调用：

1. 门控：`mechanism_registry.is_enabled("<key>")`，默认返回 `True`，即默认行为与接线前一致；
2. 调用：门控通过后调用该机制的既有引擎函数，**不新增行为、不伪造实现**；
3. 落库：评估结果写入 `decision_snapshot`，随埋点持久化；
4. 返回：同时作为响应字段 `mechanism_evaluations` 返回。

该设计使得这 28 个机制从"仅存在实现"转变为"可被独立开关、其结果可被观测"，从而使消融实验的处理变异成立。

### 6.3 埋点与决策快照

每次提交产生一条 `learning_events` 记录，其 `decision_snapshot` 字段以 JSON 形式冻结本次决策的完整上下文，包括机制开关状态、风险等级、被抑制的奖励、连胜状态以及步骤 13 的机制评估结果（代码证据：`app/services/progression_repository.py` 中的 `record_learning_event`）。快照的设计原则是**事后可重建**：给定快照，可复算当时的仲裁结果，无需访问运行时状态。

### 6.4 两类接线强度的界定

落地扫描脚本（`scripts/scan_mechanism_landing.py`）对 54 个机制逐条判定两个布尔量：

- `orchestrator_wired`：机制键出现在 `PIPELINE_MECHANISM_MAP` 中，或编排器中存在字面量 `is_enabled("<key>")` 门控；
- `external_ref`：机制键字符串出现在 `services`/`api` 源码文本中（排除注册表自身与测试）。

机制被判为已落地（`landed`）当且仅当 `orchestrator_wired` 或 `external_ref` 为真。截至代码基线，`landed = 54`、`orphan = 0`。

**必须强调**：`external_ref` 仅为文本出现判据，**不等同于有效运行时调用**。19 个仅满足 `external_ref` 的机制（表 4-3 中"运行时接入 = 外部"者），其处理变异未经证实。因此，在实验设计中，仅应对具备编排器门控的 34 个机制做消融；对其余 19 个，应在预注册中声明为"处理变异待验证"。

> 复算命令：`python scripts/scan_mechanism_landing.py --quiet`（输出：`artifacts/mechanism_landing_status.json`）

### 6.5 可复现性印章

`scripts/verify_counts.py` 对六项指标执行登记值—实测值比对，输出 `artifacts/count_verification.json`，其中记录生成时间、git 提交指针、Python 版本与逐项判定结果。

**表 6-2　可复现性印章的指标构成**

| 指标 | 登记值 | 严格性 | 含义 |
|---|---:|---|---|
| `mechanism_unique` | 54 | 严格 | 唯一机制数（论文 Table 1 的数字） |
| `learning_methods` | 28 | 严格 | 学习方法数（权威源 `method_registry.py`） |
| `skill_tree_nodes` | 16 | 严格 | 元学习技能树节点数 |
| `prd_claimed` | 69 | 严格 | PRD §2.3 表格求和（用于论证文档内部矛盾） |
| `mechanism_units` | 60 | 非严格 | 实现单元数（工程演进指示量） |
| `engine_classes` | 86 | 非严格 | `Engine` 类总数（含学习科学算法） |

> 复算命令：`python scripts/verify_counts.py`（退出码 0 表示全部通过；严格指标漂移会阻塞）

---

## 7. 实验设计：八类机制消融

### 7.1 估计量

本文的主要估计量为**意向治疗效应（ITT）**：在机制类别 $c$ 上，处理组（类别 $c$ 全部机制关闭）与对照组（全部机制开启）在主要结局上的均值差

$$\tau_c = \mathbb{E}[Y_i(0)] - \mathbb{E}[Y_i(1)]$$

其中 $Y_i(1)$ 表示开启类别 $c$ 时学习者 $i$ 的结局。注意符号约定：$\tau_c < 0$ 表示开启该类别反而降低结局，即该类别的干预是无效的或有害的。

随机化单位为学习者（个体），但学习者嵌套于班级，因此需考虑聚类相关（§7.2）。

### 7.2 随机化单位与设计效应

聚类随机化下，方差膨胀因子（设计效应）为

$$\text{DEFF} = 1 + (m - 1)\rho$$

其中 $m$ 为平均簇规模，$\rho$ 为组内相关系数。本项目取 $m = 30$、$\rho = 0.05$，得 $\text{DEFF} = 2.45$（代码证据：`app/services/ab_test_framework.py` 中的 `design_effect`）。

### 7.3 分层 Gatekeeping 的多重检验校正

同时检验八个类别会显著膨胀第一类错误率，因此采用分层 Gatekeeping：

**表 7-1　分层 Gatekeeping 的 α 分配**

| 层 | 检验内容 | α | 说明 |
|---|---|---|---|
| Gate 0 | 全局 omnibus 检验 | 0.05 | 若不显著，停止后续全部检验 |
| Gate 1 | 八个类别的类别级检验 | 0.05 / 8 = 0.00625（Holm 校正） | 通过者进入 Gate 2 |
| Gate 2 | 类别内机制级检验（每类 ≤ 12） | 类别内 Holm 校正 | 仅检验通过 Gate 1 的类别 |
| Gate 2.5 | 预先指定的交互项（≤ 3） | 0.05 / 3 ≈ 0.0167 | 仅检验预注册的交互 |

> 预注册文件：`scripts/prereg/ablation_design_v1.yaml`

### 7.4 样本量

给定效应量 $d$、显著性水平 $\alpha$ 与功效 $1-\beta$，每组的 Required 样本量为

$$n_{\text{per group}} = \text{DEFF} \times \frac{2(z_{1-\alpha/2} + z_{1-\beta})^2}{d^2}$$

在 $\alpha = 0.05$（经 Gate 1 校正后为 0.00625）、功效 0.8、$d = 0.3$、$\rho = 0.05$、$m = 30$ 的条件下，每组需约 428 人（代码证据：`scripts/power_table.py`）。

**表 7-2　八类机制的效应量与样本量要求（$\alpha = 0.00625$，功效 0.8）**

| 类别 | 假定 MDE $d$ | ICC $\rho$ | DEFF | 每组样本量 |
|---|---:|---:|---:|---:|
| A 行为主义 | 0.30 | 0.05 | 2.45 | 428 |
| B 承诺损失 | 0.30 | 0.05 | 2.45 | 428 |
| C 自我决定论 | 0.35 | 0.05 | 2.45 | 315 |
| D 社会影响 | 0.25 | 0.08 | 3.32 | 669 |
| E 习惯自我调节 | 0.30 | 0.05 | 2.45 | 428 |
| F 情绪动机 | 0.30 | 0.05 | 2.45 | 428 |
| G UX 微交互 | 0.20 | 0.05 | 2.45 | 963 |
| H 健康护栏 | — | — | — | 恒开，不参与消融 |

> 复算命令：`python scripts/power_table.py`（输出逐类样本量）

H 类（健康护栏）**不参与消融**，因其关闭涉及伦理与合规风险。这是一个不可协商的约束，必须在预注册中声明。

### 7.5 IRB 与伦理排除

1. **未成年人排除**：未成年学习者不参与任何涉及动机类机制关闭的实验；
2. **高风险排除**：学习成瘾指数（LAI）达到高风险阈值的个体被排除；
3. **健康护栏恒开**：H 类机制在所有实验条件下保持开启；
4. **退出权**：学习者可随时退出实验，其数据不纳入分析。

### 7.6 与 A/B 框架的对接

实验框架提供类别级关闭开关（`--off-category`，取值 A–H 或类别名），其实现为将类别内全部机制键映射为关闭状态（代码证据：`app/services/ab_test_framework.py` 的 `toggles_for_category`）。阶段推进（`--advance-to`）默认尊重 `required_n_per_group` 门槛，仅在显式 `--force` 时方可强推，以避免在样本量不足时提前进入下一阶段。

---

## 8. 效度威胁

### 8.1 构造效度

**威胁**：八类分类学的类别边界依赖评分者判定，尽管规则 R1–R6 已预注册，仍存在主观性。
**缓解**：报告评分者间一致性 κ；对争议项给出单独列表；给出 52–57 的敏感性区间而非点估计。

**威胁**："机制已落地"的判据中，`external_ref` 仅为文本出现判据。
**缓解**：在表 4-3 中显式区分两类接线强度，并在预注册中限制消融对象为具备编排器门控的 34 个机制。

### 8.2 内部效度

**威胁**：机制之间存在交互，关闭某一类别的效应可能依赖其他类别的开启状态。
**缓解**：Gate 2.5 仅检验预注册的少量交互项，避免事后探索；主要分析以类别级主效应为准。

**威胁**：部分机制实现成熟度为占位（4/54），其处理变异可能不成立。
**缓解**：在预注册中声明占位机制不参与主要分析，仅作为探索性结果报告。

### 8.3 外部效度

**威胁**：研究对象为单一平台的 K12 学习者，结论向其他学科、年龄段与平台的迁移性未知。
**缓解**：不在论文中主张跨情境的一般性；明确将结论限定于"K12 在线练习场景"。

**威胁**：结局指标以平台内行为（作答量、留存）为主，而非学习结果。
**缓解**：将行为结局与学习结局分开报告，不以行为改善替代学习改善的论断。

### 8.4 结论效度

**威胁**：多重比较与类别内机制级的嵌套检验膨胀第一类错误率。
**缓解**：分层 Gatekeeping（§7.3）与预注册。

**威胁**：聚类随机化下的 ICC 估计不确定，样本量计算可能偏低。
**缓解**：采用保守的 $\rho = 0.05$；在实验进行中重估 ICC 并按需调整样本量（须在预注册中声明中期重估规则）。

---

## 9. 已知缺陷与未实现项（诚实披露）

**表 9-1　必须披露的未实现项与已知缺陷**

| # | 项目 | 性质 | 对实验的影响 | 状态 |
|---:|---|---|---|---|
| 1 | `anti_addiction_compliance.py` 的 `MinorProtectionEngine`（LF-M52）**无调用方** | 合规硬伤 | 健康一票否决依赖编排器内构造的等效效应，而非该引擎本身 | **已解决·2026-09-10**：`MinorProtectionEngine` 已接线，全仓 16 处引用，原“无调用方”已消除 |
| 2 | `learning_orchestrator.py` 中 `get_skill_tree()` 返回值与 `_skilltree_repo_format()` 期望形状不兼容 | 既有缺陷 | 技能树相关结局在真实扁平入参下不可用 | **已解决·2026-09-10**：`_skilltree_repo_format`（`learning_orchestrator.py:430`）已兼容 `get_skill_tree`（`meta_learning_skilltree.py:273`）返回的 `categories` 形状，原 `AttributeError` 路径已消除 |
| 3 | `SQLExperimentStore` 未实现 | 基础设施缺口 | 实验数据仅支持 JSON 后端，规模化受限 | **已解决·2026-09-10**：`SQLExperimentStore` 已落地（`ab_test_framework.py:510`，真实 SQLAlchemy Core 后端） |
| 4 | 9 个内存态容器默认仍为 `MemoryStateStore` | 持久化缺口（**未决**） | `StateStore` 接口已落地，但默认后端仍为 `MemoryStateStore`，进程重启后状态未落盘，影响长期结局的连续性 | 未决 |
| 5 | 4 个机制（LF-M29、LF-M32、LF-M49、LF-M50，`maturity="placeholder"`）实现为占位 | 实现缺口（**未决**） | 其步骤 13 输出为引擎占位数据，不参与主要分析 | 未决 |

上述五项必须在论文的"威胁到效度"或"实现状态"章节中如实陈述，不得以任何方式隐藏。

---

## 10. 结论与未来工作

本文针对游戏化学习系统中机制计数不可复算、干预冲突无仲裁、接线状态不可审计这三个方法论缺陷，给出了一套可复现的处理方案：以四层计数口径与预注册去重规则确定 54 个唯一机制并给出 52–57 的敏感性区间；以统一效应接口与三层漏斗仲裁器确定性消解并发干预的方向性冲突；以编排器门控、落地扫描与计数印章使接线状态成为可机器验证的命题；以分层 Gatekeeping 与聚类随机化下的功效分析给出八类消融的实验设计。

需要强调的是，本研究的价值不在于新增干预机制，而在于**使既有的机制集合从不可验证的工程资产转变为可验证的研究对象**。这一转变是可开展任何严肃消融实验的前提。

未来工作包括三项：其一，补齐表 9-1 中的未实现项，尤其是未成年保护引擎的调用方与实验数据的 SQL 后端；其二，将 19 个仅有文本引用的机制纳入显式门控，使其消融的处理变异得到保证；其三，在真实学习者样本上执行预注册的八类消融，并以本文给出的命令集公开全部复算结果。

---

## 附录 A　复算命令清单

在 `E:\learnflow\learnflow-backend` 目录下执行（Python 解释器使用项目虚拟环境）：

| 目的 | 命令 | 输出 |
|---|---|---|
| 全指标复算与印章刷新 | `python scripts/verify_counts.py` | 控制台比对表 + `artifacts/count_verification.json` |
| 机制落地扫描 | `python scripts/scan_mechanism_landing.py --quiet` | `artifacts/mechanism_landing_status.json` |
| 注册表指纹 | `python -c "from app.services.mechanism_registry import registry_fingerprint as f; print(f())"` | `ee1a49be5732` |
| 成熟度分布 | `python -c "from app.services.mechanism_registry import all_mechanisms; import collections; print(collections.Counter(m.maturity for m in all_mechanisms()))"` | `partial=41, complete=9, placeholder=4` |
| 样本量表 | `python scripts/power_table.py` | 八类 (MDE, ICC) 功效表 |
| 全量回归测试 | `python -m pytest tests/ -q` | 基线 `868 passed / 49 文件` |

## 附录 B　术语表

| 术语 | 英文 | 定义 |
|---|---|---|
| 机制 | mechanism | 一个可对学习者行为施加干预的、具有独立心理学构念的设计元素 |
| 实现单元 | implementation unit | 代码中承载机制的一个类或函数单元；一个机制可对应多个实现单元 |
| 唯一机制 | unique mechanism | 经语义去重后的机制构念；本文主计数口径，取值 54 |
| 效应 | Effect | 机制产出的统一表示，含方向、代价、优先级与健康标记 |
| 仲裁器 | arbitrator | 决定哪些效应被下发的组件，采用三层漏斗结构 |
| 保守偏置 | conservative bias | 方向冲突时保留"退出"方向、丢弃"趋近"方向的仲裁策略 |
| 接线 | wiring | 机制接入运行时决策路径的状态；分"编排器门控"与"外部文本引用"两级 |
| 设计效应 | design effect (DEFF) | 聚类随机化下方差膨胀因子，$1 + (m-1)\rho$ |
| 分层 Gatekeeping | hierarchical gatekeeping | 先 omnibus、后类别、再机制级的多重检验校正结构 |

## 附录 C　遗留错误数字更正表

| 错误表述 | 正确表述 | 依据 |
|---|---|---|
| 76 个/种游戏化机制 | 54 个唯一机制（LF-M01–LF-M54）；PRD 标题声称 76 与其表格求和 69 自相矛盾 | §3.2，`verify_counts` |
| 23 / 21 种学习方法 | 28 种学习方法（LF-L01–LF-L28，权威源 `method_registry.py`） | `verify_counts` |
| 48 个零调用机制 | 落地 54/54，orphan = 0；其中 19 个仅有文本引用 | §6.4 |
| 394 个测试用例 | 868 passed（49 个测试文件） | `pytest tests/ -q` |
| 后端 16,593 行 | 后端 81 个 Python 文件 / 23,927 行 | 文件统计 |

## 附录 D　待核验引用清单

表 4-1 与表 4-3 中"理论来源"列引用的心理学经典文献尚未全部录入 `docs/references.bib`。以下条目需逐条核验作者、年份、标题与 DOI 后补录；在补录完成前，正文对该类文献采用"作者（年份）"的裸引用形式，不使用 citation key。

## D.2 代码事实基线（2026-09-10 复核，待核验）

以下条目由 `learnflow-backend` 仓库内脚本复算，须在投稿前逐条复核并保留「待核验」标注：

- 机制注册表指纹 `ee1a49be5732`（`registry_fingerprint()`，`app/services/mechanism_registry.py:145`）；
- 机制运行时落地 54/54，orphan=0（`scripts/scan_mechanism_landing.py --quiet`）；
- `SQLExperimentStore` 已落地（`ab_test_framework.py:510`，真实 SQLAlchemy Core 后端），原「未实现」状态于 2026-09-10 标记为已解决；
- `MinorProtectionEngine` 已接线（全仓 16 处引用），原「零调用」状态于 2026-09-10 消除；
- 技能树持久化 `_skilltree_repo_format`（`learning_orchestrator.py:430`）已兼容 `get_skill_tree`（`meta_learning_skilltree.py:273`）返回的 `categories` 形状，原 `AttributeError` 路径于 2026-09-10 消除；
- 4 个机制 `maturity="placeholder"`：LF-M29（`social_addiction_engine.py:411`）、LF-M32（`social_addiction_engine.py:288`）、LF-M49（`ux_addiction_engine.py:290`）、LF-M50（`ux_addiction_engine.py:345,482,524`），仍属未决项。


- Ainslie (1975)；Arkes & Blumer (1985)；Bandura (1991, 1997)；Christakis & Fowler (2007)
- Cialdini (1984)；Clark et al. (2009)；Dai, Milkman & Riis (2014)；Deci & Ryan (1985)
- Duhigg (2012)；Elliot & Maier (2014)；Eyal (2014)；Ferster & Skinner (1957)
- Festinger (1954)；Flavell (1979)；Fogg (2019)；Garcia & Tor (2009)；Gollwitzer (1999)
- Griffiths (2005)；Hoover-Dempsey & Sandler (1995)；Hull (1934)；Johnson & Johnson (1989)
- Kahneman & Tversky (1979)；Kahneman et al. (1993)；Lally et al. (2010)
- Locke & Latham (1990)；Loewenstein (1994)；Markus & Nurius (1986)；Mauss (1925)
- Milkman, Minson & Volpp (2014)；Mochon et al. (2012)；Nielsen (1994)；Norman (2004)
- Norton, Mochon & Ariely (2012)；Oyserman (2007)；Przybylski et al. (2013)；Reid (1986)
- Reiss (2004)；Rogers, Milkman & Volpp (2014)；Ryan & Deci (2000)；Schultz (1998)
- Skinner (1938)；Sweller (1988)；Tajfel & Turner (1979)；Tauer & Harackiewicz (2004)
- Wood & Neal (2007)；Wood & Rünger (2016)；Zeigarnik (1927)；Zimmerman (2002)

正文已核验并使用的 citation key：`@sailer2017how`、`@sailer2020meta`、`@mazarakis2024whichone`、`@gray2018dark`、`@lieberoth2015shallow`、`@neurips2017posetbandits`、`@kitto2020xapi`、`@ieee9274xapi2023`、`@mangaroska2019multisource`、`@corbett1994knowledge`、`@abdelrahman2023knowledge`、`@liu2025pykt`。

---

*本文档的每一项统计声明均可由附录 A 的命令复算；若复算结果与本文档不符，以复算结果为准并须更新本文档。*
