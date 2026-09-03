# LearnFlow 文献测绘与研究缺口报告

> **文档性质**：实证研究团 · 文献综述专家「搜文献」交付物
> **检索执行日期**：2026-09-02
> **服务对象**：LearnFlow（FastAPI 教育平台 → CS 博士论文研究平台）
> **覆盖方向**：① 自适应难度选择 ② 区块链+教育大数据可信处理 ③ 游戏化分类学与消融 ④ 学习分析可复现性与数据质量危机 ⑤ CS 教育与编程学习适应性
> **配套文件**：`references.bib`（仅收录已确认真实文献）、本文档附录 A（待核实清单）

---

## 0. 阅读须知与真实性声明

### 0.1 引用真实性政策（务必先读）

本文档执行**三级真实性格分级**。主理人明确要求"不要凭记忆编造文献"，因此所有条目都标注了核验状态：

| 标记 | 含义 | 是否已进 BibTeX |
|---|---|---|
| `[已核验]` | 检索命中了**出版方页面 / DOI 解析页 / arXiv 摘要页 / 会议论文集页**，且标题、作者、年份、载体四项一致 | 是 |
| `[部分核验]` | 载体与标题确认无误（有 DOI 或官方 URL），但**作者全名 / 卷期页码**未逐字确认 | 是，但 BibTeX 内附 `note` 字段标注待补项 |
| `[待核实]` | 仅见二手转述（博客、行业媒体、综述的参考文献列表、访谈引用），**未找到一次文献** | **否**，见附录 A |

**硬性纪律**：
1. 本文档**绝不出现虚构的 DOI、卷号、期号、页码**。凡未逐字确认的卷期页码，一律写作"卷期待补"。
2. `[待核实]` 条目**禁止**直接写入论文正文的引用位。若某论点只能由 `[待核实]` 文献支撑，该论点在本报告中被显式降级为"论点存疑"，并在对应小节标注。
3. 团队成员在撰写论文时，凡引用本文档条目，**必须回到 BibTeX 核对**，不得从正文自然语言转抄。

### 0.2 方法论

采用简化 PRISMA 流程（非完整系统综述，定位为**范围综述 scoping review**）：

```
识别 (Identification)
  ├─ 数据库：Web 检索（跨 OpenAlex/Semantic Scholar/IEEE Xplore/ACM DL/arXiv 的聚合检索）
  ├─ 时间窗：优先 2020 年后，经典奠基文献不设限
  └─ 语言：英文优先，中文政策文献作为制度背景补充
筛选 (Screening)
  ├─ 剔除：纯商业推广页、无一次文献支撑的行业博客、生成式内容农场
  └─ 保留：有 DOI / 有官方出版页 / 有 arXiv 编号 的条目
纳入 (Inclusion)
  ├─ 每个方向保留 5–8 篇"最近邻工作"
  └─ 优先选择：有大规模实证、有公开数据集、观点与 LearnFlow 相反（用于压力测试）
```

### 0.3 一份必须前置的残酷前提

本报告在评估每一个 novelty 时，都叠加了一个 LearnFlow 当前状态的硬约束：

> **真实用户数据 = 0 行；394 个测试用例全部是单元测试。**

这条约束不是"暂时困难"，它**直接决定了五个方向中哪些能写成论文、哪些只能写成提案**：
- 凡是以"我们在真实学习者上观察到了 X"为主证据的论文 → **当前不可写**。
- 凡是以"我们在公开数据集 / 自有代码库 / 仿真环境上观察到 X"为主证据的论文 → **当前可写**。
- 凡是以"我们提出了架构但没有评估"为主证据的论文 → **只能投 workshop / poster，且会被顶会直接拒**。

本报告第 6 章给出了基于该约束的**分级路线图**。

---

## 1. 全局速览：五个方向的一页纸判断

| # | 方向 | 格局成熟度 | 最锋利的活着的研究缺口 | 致命先行工作 | 建议优先级 |
|---|---|---|---|---|---|
| ① | 自适应难度选择 | 高（理论已收敛，2026 已有大规模 RCT） | 序数/结构化动作空间的难度 bandit；四层耦合模型的可辨识性与稳定性 | **Chung et al. 2026（10 校 RCT，0.15 SD）** | 中（须改定位） |
| ② | 区块链 + 教育可信处理 | 高（综述扎堆，原型泛滥） | **算法决策的审计轨迹**（非证书存证）；轻量 Merkle 批锚定的成本-收益量化 | "blockchain for blockchain's sake"批评潮 | 低—中（需先过自证关） |
| ③ | 游戏化分类学与消融 | 高（元分析已给出效应量） | 生产级游戏化系统的**机制实现债**；暗黑模式与防沉迷的**对立建模** | Sailer 2017 / Mazarakis & Bräuer（单机制消融已做） | **高**（自有代码库即数据集） |
| ④ | 可复现性与数据质量危机 | 中（危机被承认，量化证据多为预印本） | 未校准 BKT 参数在零真实数据下的**不可辨识性**；KT 模型排名在**小样本下的稳定性** | pyKT 已建基准（但基准本身可被审计） | **高**（可纯用公开数据发） |
| ⑤ | CS 教育与编程学习适应性 | 中（LLM 综述已出，代码 KT 已做） | 编程教育自适应难度**最大样本仅 N=47**；LLM 生成 KC → 难度选择的**闭环缺失** | TIKTOC / KCGen-KT（代码 KT 已占坑） | **高**（真空最大） |

**一句话总判**：LearnFlow 最锋利的 novelty **不在**"我们的难度算法更聪明"，而**在**"我们有一个可审计、可消融、可复现的真实工程系统，并且愿意把它的失败模式写成论文"。方向 ③⑤④ 是这个定位的落点，方向 ① 是被 Chung et al. 2026 挤压后需要换打法的方向，方向 ② 需要先自证"为什么不是数据库"。

---

# 第 0 章 可复用检索策略

## 0.1 推荐数据库与分工

| 数据库 | 用途 | 备注 |
|---|---|---|
| **OpenAlex** | 主力。覆盖全学科、免费 API、可批量导出 | 建议用 `https://api.openalex.org/works?search=...&filter=...` 做批量筛查与引文网络扩散 |
| **Semantic Scholar** | 补充。AI/CS 覆盖好，有 `tldr` 摘要与引文意图标注 | `/graph/v1/paper/search?query=...&fields=title,year,venue,externalIds,citationCount` |
| **arXiv** | 获取最新（cs.CY / cs.LG / cs.HC / cs.SE） | **注意**：arXiv 有预印本无同行评议，引用时须同时查是否已正式发表 |
| **IEEE Xplore** | TKDE / TLT / TSE / Access 等 | 需要机构订阅 |
| **ACM DL** | CHI / LAK / SIGCSE / ICER / TOCE / CSUR | 需要机构订阅；ACM 开放访问转型后部分可免费 |
| **Scopus / WoS** | 引文计数、期刊分区、作者影响力 | 需要机构订阅；用于最终期刊选择与 IF 核实 |

**检索顺序建议**：OpenAlex 批量识别 → Semantic Scholar 查引文网络扩散（前向+后向各一轮，即"滚雪球"）→ arXiv 补最新 → IEEE/ACM 核实卷期页码 → Scopus 核实分区。

## 0.2 通用布尔框架

```
(学习者主体) AND (机制/技术) AND (结果/度量) AND (研究类型限定)

学习者主体 = "student" OR "learner" OR "K-12" OR "undergraduate" OR "CS1" OR "编程学习者"
机制/技术  = "adaptive difficulty" OR "difficulty selection" OR "item sequencing" ...
结果/度量  = "learning gain" OR "engagement" OR "retention" OR "AUC" OR "RMSE" ...
研究类型   = "randomized controlled trial" OR "meta-analysis" OR "benchmark" OR "replication"
```

**反向检索技巧（本报告大量使用，强烈建议复用）**：对每个方向，额外跑一组**否定性查询**来找"批评性文献"，例如：
- `"blockchain" AND ("for blockchain's sake" OR "overhyped" OR "do we need")`
- `"gamification" AND ("dark pattern" OR "no effect" OR "backfire" OR "crowding out")`
- `"knowledge tracing" AND ("reproducibility" OR "data quality" OR "replication failure")`

反向检索是本次测绘中**发现最高价值文献的途径**（Crespo et al. 2022 的"游戏化无效"结论、SoLAR 2020 的"标准实现糟糕"立场文件，都是这样挖出来的）。

## 0.3 分方向检索词表

### 方向 ① 自适应难度选择

**中文**
```
("自适应难度" OR "难度选择" OR "难度调整" OR "题目推荐" OR "练习序列")
AND ("知识追踪" OR "认知诊断" OR "项目反应理论" OR "多臂老虎机" OR "强化学习")
```
```
"85% 最优学习率" OR "百分之八十五规则" OR "最优错误率" OR "最优难度区"
```

**英文（核心组）**
```
("adaptive difficulty" OR "difficulty selection" OR "difficulty adjustment"
 OR "exercise sequencing" OR "item sequencing" OR "problem selection")
AND ("knowledge tracing" OR "item response theory" OR "cognitive diagnosis"
 OR "multi-armed bandit" OR "reinforcement learning" OR "zone of proximal development")
```

**英文（gap 定位组：序数/结构化 bandit）**
```
("ordinal bandit" OR "ordered action space" OR "structured bandit"
 OR "correlated arms" OR "unimodal bandit" OR "poset bandit"
 OR "dueling bandit" OR "categorized bandit" OR "stochastic dominance bandit")
```
```
("85 percent rule" OR "eighty five percent rule" OR "optimal error rate"
 OR "85% rule") AND ("human" OR "learner" OR "student" OR "classroom")
```

**英文（心流形式化组）**
```
("flow theory" OR "flow channel" OR "challenge-skill balance")
AND ("computational model" OR "formalization" OR "intelligent tutoring system"
 OR "adaptive" OR "validation" OR "measurement")
```

**英文（KT SOTA / 基准组）**
```
"knowledge tracing" AND ("benchmark" OR "systematic review" OR "survey"
 OR "reproducibility" OR "pyKT")
```

### 方向 ② 区块链 + 教育大数据可信处理

**中文**
```
("区块链" OR "分布式账本") AND ("教育" OR "学习" OR "学分" OR "学历" OR "微证书")
AND ("可验证凭证" OR "学分互认" OR "存证" OR "审计" OR "隐私计算")
```

**英文（核心组）**
```
("blockchain" OR "distributed ledger" OR "DLT")
AND ("education" OR "learning" OR "credential" OR "micro-credential"
 OR "credit transfer" OR "learning record")
```

**英文（可验证凭证组）**
```
("verifiable credential" OR "self-sovereign identity" OR "W3C VC"
 OR "EBSI" OR "Europass" OR "selective disclosure" OR "credential revocation")
AND ("education" OR "learning" OR "transcript" OR "credit")
```

**英文（轻量锚定组）**
```
("Merkle tree" OR "trusted timestamping" OR "OpenTimestamps" OR "OriginStamp"
 OR "batch anchoring" OR "notarization") AND ("education" OR "learning record" OR "audit")
```

**英文（批评组 —— 必跑）**
```
("blockchain" OR "DLT") AND ("for blockchain's sake" OR "overhyped" OR "glorified spreadsheet"
 OR "do we really need blockchain" OR "solution in search of a problem"
 OR "Gartner" OR "failure rate")
```

**英文（算法决策审计组 —— LearnFlow 的差异化落点）**
```
("algorithmic decision" OR "algorithmic accountability" OR "audit trail"
 OR "model card" OR "decision provenance")
AND ("education" OR "learning analytics" OR "student model")
AND ("immutable" OR "tamper-evident" OR "verifiable" OR "blockchain")
```

### 方向 ③ 游戏化分类学与消融

**中文**
```
("游戏化" OR " gamification") AND ("分类学" OR "taxonomy" OR "机制" OR "设计元素")
AND ("消融实验" OR "元分析" OR "暗黑模式" OR "道德" OR "技术债")
```

**英文（分类学组）**
```
("gamification" AND ("taxonomy" OR "classification" OR "framework" OR "design elements"))
AND ("Sailer" OR "Hamari" OR "Morschheuser" OR "Deterding" OR "Landers")
```

**英文（消融/因子实验组）**
```
("gamification" AND ("ablation" OR "factorial" OR "isolat*" OR "component"
 OR "decomposition" OR "which element" OR "2x2" OR " dismantling"))
AND ("experiment" OR "RCT" OR "randomized")
```

**英文（元分析组）**
```
"gamification" AND ("meta-analysis" OR "systematic review")
AND ("education" OR "learning" OR "student")
```

**英文（暗黑模式/伦理批评组 —— 必跑）**
```
("dark pattern" OR "deceptive design" OR "FOMO" OR "loss aversion"
 OR "variable reinforcement" OR "overjustification" OR "motivation crowding"
 OR "black hat gamification" OR "streak" OR "addictive design")
AND ("education" OR "learning" OR "gamification" OR "student")
```

**英文（游戏化 × 软件工程/技术债组）**
```
("gamification" AND ("software engineering" OR "technical debt" OR "code quality"
 OR "static analysis" OR "SonarQube" OR "dead code" OR "unused feature"))
```

### 方向 ④ 可复现性与数据质量危机

**中文**
```
("学习分析" OR "教育数据挖掘" OR "知识追踪")
AND ("可复现性" OR "复现危机" OR "数据质量" OR "小样本" OR "模拟学习者")
```

**英文（可复现性危机组）**
```
("learning analytics" OR "educational data mining" OR "knowledge tracing")
AND ("reproducibility" OR "replication" OR "researcher degrees of freedom"
 OR "data quality" OR "p-hacking" OR "publication bias")
```

**英文（数据集偏态组）**
```
"knowledge tracing" AND ("ASSIST" OR "dataset bias" OR "single dataset"
 OR "benchmark dataset" OR "cross-dataset" OR "generalization")
```

**英文（标准与互操作组）**
```
("xAPI" OR "Caliper" OR "cmi5" OR "LRS" OR "IEEE 9274" OR "learning record store")
AND ("interoperability" OR "adoption" OR "data quality" OR "limitation"
 OR "implementation" OR "critique")
```

**英文（小样本 / 模拟学习者组）**
```
("simulated learner" OR "synthetic learner" OR "small sample" OR "n=100"
 OR "underpowered" OR "statistical power")
AND ("adaptive learning" OR "knowledge tracing" OR "gamification" OR "ITS")
```

### 方向 ⑤ CS 教育与编程学习适应性

**中文**
```
("编程教育" OR "计算机教育" OR "CS1" OR "程序设计")
AND ("自适应" OR "知识追踪" OR "代码提交" OR "大语言模型" OR "智能助教")
```

**英文（自适应难度 × 编程组）**
```
("adaptive difficulty" OR "difficulty adjustment" OR "dynamic difficulty"
 OR "personalized problem selection" OR "exercise recommendation")
AND ("programming" OR "CS1" OR "introductory programming" OR "coding"
 OR "block-based" OR "computing education")
```

**英文（代码知识追踪组）**
```
("knowledge tracing" AND ("code" OR "programming" OR "open-ended coding"
 OR "code submission" OR "test case" OR "AST" OR "code embedding"))
AND ("CodeWorkout" OR "ProgSnap2" OR "FalconCode" OR "Code-DKT" OR "OKT" OR "TIKTOC")
```

**英文（LLM × CS 教育组）**
```
("large language model" OR "LLM" OR "generative AI" OR "GPT" OR "Codex")
AND ("computer science education" OR "programming education" OR "computing education"
 OR "CS1" OR "introductory programming")
AND ("systematic review" OR "survey" OR "RCT" OR "evaluation")
```

## 0.4 检索纪律三条（血泪建议）

1. **arXiv 编号不等于已发表**。本报告发现 Chung et al. 2026（见 3.1）同时挂在 SSRN 与 arXiv，**尚未见期刊正式发表**。引用时请写"工作论文 (working paper)"，不要写"Nature/ Science 子刊"。
2. **综述的参考文献列表 ≠ 一次文献核实**。Choudhary et al. 2025、Abdelrahman et al. 2023 的参考文献里出现了大量条目的转述，本报告中凡只在这些综述的参考文献列表中见到、未独立核实的，一律降为 `[待核实]`。
3. **行业媒体数据必须回溯**。如"Gartner 2024：75% 的企业区块链项目用传统数据库/DLT 就够了""Roubini 引用的 43 个区块链实验 0 成功"这两个数字在行业媒体中广泛流传，但本报告**未能定位到一次文献**，故列入附录 A，**不得写进论文**。

---

# 第 1 章 方向 ①：自适应难度选择

## 1.1 格局概述（148 字）

>Wilson 等 2019 年在 Nature Communications 提出的"85% 最优学习率"已成为自适应难度的事实性理论锚点，但该结论只在人工神经网络与生物可解释的感知学习模型上验证，作者本人明确限定其适用于二元分类、最可能适用于感知学习，未声称适用于一般课堂学习。难度选择算法侧，知识追踪已由 pyKT（IEEE TKDE 2025）完成 SOTA 基准化；决策侧仍普遍使用假设各臂独立的标准多臂老虎机，而难度等级天然有序且相邻相关。2026 年 Chung 等在十所高中完成大规模自适应难度 RCT，效果量 0.15 SD，该方向的"首个大规模实证"窗口已关闭。

## 1.2 最近邻工作（8 篇）

### N1. Wilson, Shenhav, Straccia & Cohen (2019) —— 85% 规则的奠基 `[已核验]`

- **完整引用**：Robert C. Wilson, Amitai Shenhav, Mark Straccia, Jonathan D. Cohen (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10, Article 4646.
- **DOI**：10.1038/s41467-019-12552-4
- **一句话贡献**：在人工神经网络与生物可解释的感知学习模型中，当训练错误率约为 **15.87%**（正确率约 85%）时学习速度最快；该最优错误率随任务难度结构变化，且能用噪声 SGD 的理论推导出来。
- **与 LearnFlow 的差异（我们站在哪）**：
  - LearnFlow `optimal_difficulty.py` 把 85% 作为**难度推荐的目标错误率**，即把这篇论文的结论直接搬到了人类学习者身上。
  - **这正是我们最大的理论风险**：原作者明确限定该结论适用于**二元分类**任务，且"最可能适用于感知学习"（原文措辞），从未声称适用于一般课堂/复杂认知任务。
  - 因此 LearnFlow 的做法不是"应用了一个被验证的规律"，而是**"外推了一个作者本人未主张外推的规律"**。审稿人只要读过原文就能指出这一点。

### N2. Chung, Zhang, Kung, Bastani & Bastani (2026) —— 大规模自适应难度 RCT ⚠️ **最高威胁** `[已核验]`

- **完整引用**：Angel Tsai-Hsuan Chung, Botong Zhang, Ling-Chieh Kung, Hamsa Bastani, Osbert Bastani (2026). Effective Personalized AI Tutors via LLM-Guided Reinforcement Learning. *arXiv:2608.16907*（2026-07-10 提交，2026-08 公布）；同时以工作论文形式挂于 SSRN。作者机构：University of Pennsylvania（Wharton OID 系 / CIS 系）、National Taiwan University。
- **状态**：**工作论文，未见期刊正式发表**。引用时须写 "working paper / arXiv preprint"。
- **一句话贡献**：把"GenAI 聊天助教"与"用 RL 排序练习题"紧耦合，且 RL 算法显式利用**学生-聊天机器人交互信号**来适应性选择习题难度；与台北市政府、美国在台协会合作，在 **10 所高中**、为期 **5 个月**的 Python 课程中部署，学生随机分配到"固定题目序列"vs"自适应序列"。
- **关键结果**：自适应排序使**无辅助的期末考试成绩提高 0.15 个标准差**（作者称按某些估计相当于 6–9 个月的学校教育）；中介分析表明增益由**参与度（engagement）**驱动。
- **与 LearnFlow 的差异（我们站在哪）**：
  - **坏消息**：这是本报告发现的**最接近 LearnFlow 想做的事**的先行工作，且规模、严谨度（RCT）、载体（顶校 + 政府合作）都远超 LearnFlow 当前能力。"我们要做自适应难度的大规模实证"这个定位**已经死了**。
  - **好消息（三条真实差异）**：
    1. 他们依赖 **LLM 聊天交互信号**作为 RL 的输入特征；LearnFlow **没有聊天模块**，难度决策完全基于结构化行为信号（正确率、记忆难度、能力估计）。因此 LearnFlow 若做，是"**无 LLM 条件下的自适应难度**"，这在成本敏感、隐私敏感、LLM 不可用（如考试环境）场景下是独立价值主张。
    2. 他们报告的是**端到端效果量**，**没有做机制消融**。LearnFlow 的四层模型（85% / FSRS / Elo / flow channel）是可逐层消融的——这一点他们做不到（他们的 RL 策略是一个黑盒）。
    3. 他们**没有公开算法与系统实现的可审计性**设计；LearnFlow 的"可审计难度决策"定位不与他们重叠。
  - **结论**：**不与之正面竞争效果量**；改为竞争"可解释、可消融、可审计"，并在论文中**主动引用并区分**他们（不引用 = 被审稿人抓到 = 致命）。

### N3. Liu et al. (2025) —— pyKT：深度学习知识追踪基准 `[部分核验：作者全名待补]`

- **完整引用**：Liu, Guo, Liang, Hou, Zhan, Tang, Luo, Weng (2025). Deep Learning Based Knowledge Tracing: A Review, a Tool and Empirical Studies. *IEEE Transactions on Knowledge and Data Engineering*, 37(8), 4512–4536, Aug 2025.
- **DOI**：10.1109/TKDE.2025.3552759 ；**CCF-A**
- **一句话贡献**：系统综述深度学习知识追踪（DLKT），并开源 **pyKT** 工具包，在 **9 个数据集**上统一评估 **21 个 DLKT 模型**，给出可复现的基准结果。
- **与 LearnFlow 的差异（我们站在哪）**：LearnFlow 的 `knowledge_tracing.py`（217 行）实现的是 **BKT**（Corbett & Anderson 1994），即 1994 年的模型，且参数 `p_learn0=0.35 / p_transit=0.12` 未校准。pyKT 的存在意味着"我们实现了一个 KT 模型"**不构成任何 novelty**；同时也意味着我们有了**现成的对比基线群**（21 个模型 + 9 个数据集）。这是方向 ④ 的重要抓手。

### N4. Abdelrahman, Wang & Nunes (2023) —— 知识追踪权威综述 `[已核验]`

- **完整引用**：Ghodai Abdelrahman, Qing Wang, Bernardo Nunes (2023). Knowledge Tracing: A Survey. *ACM Computing Surveys*, 55(11), Article 224, February 2023, 37 pages.
- **DOI**：10.1145/3569576 ；**CCF-A**
- **一句话贡献**：系统梳理 KT 的模型谱系（BKT → DKT → DKVMN → SAKT → 注意力/图/遗忘感知模型），并明确指出**数据集与预处理问题**（见方向 ④）。
- **与 LearnFlow 的差异**：本综述是方向 ④（数据质量缺口）的**独立第二信源**——它独立报告了不一致的预处理、重复条目、错误时间戳、缺失的知识组件标注、多个 KC 被压缩进单个 CSV 字段（如 KDDcup 的 `~~` 拼接）、缺乏人口学信息、无数据集版本控制。**这一点很重要**：它意味着方向 ④ 的核心论断有两个独立来源，不必依赖预印本。

### N5. Corbett & Anderson (1994) —— BKT 原始论文 `[已核验]`

- **完整引用**：Albert T. Corbett, John R. Anderson (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modelling and User-Adapted Interaction*, 4, 253–278.
- **与 LearnFlow 的差异**：LearnFlow 用的正是这个 30+ 年前的模型。作为**工程选择**没问题（轻量、可解释），作为**论文贡献**是负数。**必须校准参数**并在论文中给出校准过程，否则"未校准的 BKT"会成为审稿人的直接攻击点。

### N6. Jedor, Louëdec & Perchet (2020) —— Categorized Bandits `[已核验]`

- **完整引用**：Matthieu Jedor, Jonathan Louëdec, Vianney Perchet (2020). Categorized Bandits. *arXiv:2005.01656*（2020-05-04）。机构：CMLA, ENS Paris-Saclay；Cdiscount；Criteo AI Lab。
- **一句话贡献**：提出臂被归入**有序类别（ordered categories）**的随机 MAB 设定，用三种逐级减弱的随机占优（stochastic dominance）概念定义类别间的序，给出实例相关的 regret 下界与上界算法，并在真实电商数据上验证了"有序类别"确实存在。
- **与 LearnFlow 的差异（我们站在哪）**：**这是方向 ① 最有价值的方法论弹药**。难度 1–10 不是一个无序的 10 臂问题——相邻难度等级的学习收益高度相关，且存在"难度过低→无聊、过高→焦虑"的结构。Categorized Bandits 提供了**带序结构的 bandit 理论**（regret 下界 + 算法），但**它的动机场景是电商推荐，从未被用于教育难度选择**。这个"理论已有、应用空白"的接缝，就是 LearnFlow 的落点。

### N7. Bandits Dueling on Partially Ordered Sets (NeurIPS 2017) `[部分核验：作者列表待补]`

- **完整引用**：*Bandits Dueling on Partially Ordered Sets*. Advances in Neural Information Processing Systems 30 (NeurIPS 2017), Paper ID 1279. 官方页：https://papers.nips.cc/paper/6808-bandits-dueling-on-partially-ordered-sets
- **一句话贡献**：处理**臂之间部分可比、且最优臂可能不止一个（存在 Pareto 前沿）**的 dueling bandit 设定；提出 `UnchainedBandits` 算法，借助社会心理学中的 **decoy** 概念，在事先不知道哪些臂对可比较的情况下找出 Pareto 前沿，并给出 regret 与比较次数的理论保证。
- **与 LearnFlow 的差异**：
  - 高度贴切之处在于：教育难度选择中，"该题是否可与该题比较"本身是未知的（不同知识点、不同题型的难度等级不可直接比较），这正是 poset 设定。
  - 但 **NeurIPS 2017 的审稿意见本身也指出了该设定的局限**（对含环的 "social poset" 处理不自然、Pareto 前沿可能为空）。引用时**必须诚实呈现这些局限**，否则反被审稿人指出"你引用的方法自己都有问题"。
  - 同样地，**该工作未被用于教育**。

### N8. 心流理论的计算化与"平衡公理"建模 `[已核验]`

- **完整引用**：*Modelling the Balance Axiom in Flow Theory: A Physiological and Computational Approach in STEAM Education*. *Sensors*, 26(1), Article 38 (2026). MDPI.
- **一句话贡献**：从生理与计算双重角度检验心流理论的"技能-挑战平衡公理"，并系统梳理了心流形式化的历史模型与其缺陷。
- **该文提供的、对 LearnFlow 极其关键的三条批判性事实**：
  1. **原始通道模型的预测与自报告不匹配**：Csikszentmihalyi 与 Csikszentmihalyi 自己给出的经验取样研究中，落在"通道模型预测为无聊"位置的点，被试描述为"兴奋"；落在"预测为焦虑"的点，被试描述为"略微无聊"。
  2. **平衡变量与心流状态的相关很弱**：Shin 发现二者相关显著但仅 **r = 0.206 (p < 0.01)**。
  3. **线性化简化损害效度**：Pearce, Ainley & Howard 用 `Challenge/Skills = 1` 的数学式定义平衡，而该现象本身被描述为主观、易变、非线性。Massimini & Carli (1988) 用 Z 分数标准化改进为八通道模型（Experience Fluctuation Model）。
- **与 LearnFlow 的差异（我们站在哪）**：LearnFlow `optimal_difficulty.py` 的第四层把 **BOREDOM / FLOW / STRETCH / ANXIETY** 作为一个**硬性的决策通道**。上述文献说明：**"心流通道"作为可计算目标函数的效度从未被严格检验**。这既是风险（我们依赖了一个效度存疑的构造），**也是机会**（见缺口 G1-3）。

## 1.3 研究缺口（5 个，全部可验证）

### G1-1. 序数/结构化动作空间的难度选择：理论已备，教育领域零应用

**可验证性**：以 `("ordinal bandit" OR "categorized bandit" OR "poset bandit") AND ("difficulty" AND "education")` 检索，无命中；分别单独检索两类词，各自有大量命中。

**具体缺口**：难度等级 1–10 构成**相邻相关的有序动作空间**，标准 MAB / Thompson Sampling / UCB 假设臂独立，在难度选择上是**结构性错配**。Categorized Bandits（随机占优序）、poset dueling bandits（部分可比 + Pareto 前沿）已提供理论与算法，但**无一被应用于教育难度选择**。

**可做的最小实证**：在公开数据集（如 CodeWorkout、ASSISTments）上，把"难度等级"作为臂，对比 (a) 独立臂 UCB/TS 与 (b) 带序结构的结构化 bandit，在**有限样本（每生 20/50/100 次交互）**下的累计 regret 与"停留在合理难度区的时间比例"。**不需要真实用户数据**。

### G1-2. 四层耦合模型的反馈回路缺少稳定性/收敛性分析

**可验证性**：读 `optimal_difficulty.py` 可直接确认存在反馈回路：难度决策 → 影响正确率 → 正确率更新 Elo/FSRS → 更新后的能力估计影响下一次难度决策。

**具体缺口**：85% 目标错误率（Wilson 层）、FSRS 记忆难度（间隔层）、Elo/Glicko 能力估计（能力层）、心流通道（状态层）**四层被串联成一个闭环自适应系统**。**没有**关于该闭环的稳定性、收敛性、极限环（limit cycle）行为的任何分析。具体可验证的问题：
- 当学习者真实能力固定时，85% 目标与 Elo 更新是否会**锁死**在某个难度（自洽陷阱）？
- 当学习者能力真实增长时，系统追赶的**时滞**是多少？是否会产生**振荡**（难度在两级之间反复横跳）？
- FSRS 的"记忆难度"与"题目难度"是**两个不同的难度概念**，被放进同一个决策函数是否可辨识？

**可做的最小实证**：纯仿真即可完成。构造带已知能力曲线的模拟学习者族，跑 LearnFlow 决策器，测量"难度轨迹的振荡幅度 / 收敛时滞 / 稳态误差"，并对照无 FSRS 层、无 flow 层的消融版本。**可完全无真实数据完成，且直接产出一张高信息量的图。**

### G1-3. "心流通道"作为难度选择目标函数，其效度从未被检验

**可验证性**：见 N8 的三条事实（通道模型预测与自报告不符；r=0.206；线性化简化）。

**具体缺口**：大量自适应学习系统（含 LearnFlow）把"让学习者停留在心流通道"作为**显式的优化目标**，但：
- 心流本身是**主观自评状态**，系统无法观测，只能用代理变量（答题时长、连续正确数、主动跳过率）；
- **代理变量与真实心流状态的对应关系从未在这些系统中被校准**；
- 因此"系统认为学习者在心流中"与"学习者自评在心流中"的一致性是**未知量**。

**可做的最小实证**：这是**唯一需要真人**的缺口，因此**在当前"0 真实数据"状态下不可写**。标注为"数据就绪后可做"。

### G1-4. BKT 参数未校准 → 下游所有决策不可复现

**可验证性**：`knowledge_tracing.py` 中 `p_learn0=0.35`、`p_transit=0.12` 为硬编码常量，无任何拟合过程。

**具体缺口**：见方向 ④ 的 G4-1（此处不重复）。**它与方向 ④ 共享同一篇论文落点**，建议合并处理。

### G1-5. 自适应难度的"反事实评估"缺少离线评估协议

**可验证性**：LearnFlow 的 A/B 测试框架（342 行）**不具备开关单个难度机制的能力**，只能做整组对比。

**具体缺口**：自适应难度策略的评估在文献中**高度依赖在线 RCT**（Chung et al. 2026 即是），而 RCT 成本极高。**离线评估（off-policy evaluation / counterfactual evaluation）在自适应难度领域几乎是空白**——即：能否只用历史日志，无偏地估计"换个难度策略会怎样"。

**意义**：这是**唯一能让"0 真实数据"团队做出可信评估结论的合法路径**，也是把方向 ① 从"不可写"救回"可写"的关键。反事实评估需要**日志记录策略（logging policy）的概率**，这恰恰是一个系统设计要求——LearnFlow 若现在就在难度决策处记录每个难度被选中的概率分布，未来任何日志都能做无偏离线评估。**这是一条成本极低、回报极高的工程建议，强烈建议立即实施。**

## 1.4 Novelty 诚实评估：我们的新颖性能站住吗？

### 已经死了的（**不要再去占**）

| 曾经的设想 | 死因 |
|---|---|
| "验证 85% 规则在人类学习者上是否成立" | ① Wilson 本人已限定适用域，做"证伪"只是重复作者的免责声明；② 需要真人大样本，当前 0 数据；③ Chung et al. 2026 已在真人上做了自适应难度 RCT，但不是检验 85% 规则，所以这条其实**还有一点空间**——但空间窄到不足以支撑一篇 CCF-A |
| "我们提出一个自适应难度算法" | 该领域算法论文饱和；且 Chung et al. 2026 有 10 校 RCT，任何无数据的算法论文在对比下显得空洞 |
| "我们实现了知识追踪" | pyKT 已基准化 21 个模型，1994 年的未校准 BKT 毫无 novelty |
| "心流理论驱动的自适应难度" | 作为**卖点**已烂大街；作为**可验证贡献**需要真人，当前不可做 |

### 还活着的（**建议投入**）

1. **序数/结构化 bandit 首次用于教育难度选择**（G1-1）——理论现成、缺口明确、可纯离线完成。
2. **四层耦合难度系统的稳定性/收敛性分析 + 逐层消融**（G1-2）——LearnFlow 的四层耦合在文献中**是独特的**（绝大多数系统只有 1–2 层），"耦合带来的病理行为"是别人写不了的论文。
3. **自适应难度的离线/反事实评估协议**（G1-5）——方法论缺口，且是"0 数据团队"的救命稻草。

### 一条必须写进论文的免责/定位声明（建议原样采用）

> 与 Chung 等（2026）不同，我们不依赖学生与 LLM 聊天机器人之间的自然语言交互信号；本研究考察的是**在仅有结构化行为信号**（作答正确性、时序、记忆状态）条件下，自适应难度策略能达到什么水平。这一设定对应 LLM 不可用、成本敏感或隐私受限的部署场景，也具有更低的工程门槛。此外，Chung 等报告的是端到端效果量，而本研究提供的是**逐层机制消融与稳定性分析**，二者是互补而非竞争关系。

## 1.5 目标期刊对标

| 期刊 / 会议 | CCF / 索引 | 定位 | 难度 | 周期 | 适配的缺口 |
|---|---|---|---|---|---|
| **IEEE TKDE** | CCF-A（数据库/数据挖掘/内容检索） | 数据挖掘顶刊 | 极高 | 12–24 个月（含大修） | G1-1（结构化 bandit，需强理论贡献） |
| **ACM TOIS / TKDD** | TOIS: CCF-A；TKDD: CCF-B | 信息检索/知识发现 | 高 | 12–18 个月 | G1-1、G1-5 |
| **IEEE Transactions on Learning Technologies (TLT)** | CCF 未列；SCI Q1（教育技术顶刊之一） | 学习技术 | 中—高 | 9–18 个月 | G1-2、G1-5（最适配） |
| **International Journal of Artificial Intelligence in Education (IJAIED)** | CCF 未列；SCI | AI 教育专门刊 | 中 | 9–15 个月 | G1-2、G1-5 |
| **User Modeling and User-Adapted Interaction (UMUAI)** | CCF-B（人机交互与普适计算）；SCI | 用户建模 | 高 | 12–18 个月 | G1-2（稳定性/收敛性） |
| **LAK / EDM**（会议） | CCF 未列；学习分析领域顶会 | 学习分析 | 中—高 | 4–6 个月出结果，录用率约 20–25% | G1-1、G1-5（快速占位） |
| **Computers & Education** | CCF 未列；SSCI/SCI Q1，IF 常年 8+ | 教育技术综合顶刊 | 极高 | 12–24 个月 | 需真人数据，当前不可投 |

**建议**：方向 ① 采用 **LAK/EDM 快速占位（验证 G1-5 离线评估协议）→ IEEE TLT 或 IJAIED 做完整版（G1-2 稳定性 + 消融）** 的两步走；**不要**一上来冲 TKDE。

---

# 第 2 章 方向 ②：区块链 + 教育大数据可信处理

## 2.1 格局概述（146 字）

>区块链教育应用的文献呈"综述扎堆、原型泛滥、落地稀缺"的典型泡沫形态：Choudhary 等 2025 的 PRISMA 系统综述覆盖 150 个模型，其中 124 个是原型或试点、26 个仅停留在提案阶段。应用高度集中在证书管理、微证书与学分转移、能力与评估追踪三类，几乎不涉及算法决策审计。与此同时，批评声浪已成规模，审稿人极可能直接质疑"为什么不用数据库"。真正的机会不在"上链学习记录"，而在"算法决策的可审计轨迹"这一尚未被占领的窄口。

## 2.2 最近邻工作（6 篇）

### N1. Choudhary, Chawla & Tiwari (2025) —— 区块链教育应用的系统综述 `[已核验]`

- **完整引用**：Choudhary, Chawla, Tiwari (2025). Analyzing functional, technical and bibliometric trends of blockchain applications in education: A systematic review. *Multimedia Tools and Applications*, 84(8), 4003–4048.
- **DOI**：10.1007/s11042-024-20303-x
- **一句话贡献**：用 PRISMA 方法系统综述区块链教育应用，覆盖 **150 个模型**，其中 **124 个为原型/试点，26 个仅为提案（proposal-only）**。
- **关键原话（可直接引用）**：该领域呈现"a avalanche of proposals, with approximately half of them being prototypes"——提案雪崩，其中约一半只是原型。
- **与 LearnFlow 的差异（我们站在哪）**：**这个数字是双刃剑**。一方面证明该领域活跃；另一方面，"第 151 个原型"**不构成贡献**。LearnFlow 若做区块链，必须明确回答"我们不是第 151 个原型"。

### N2. Abdul Razzaq et al. (2026) —— 区块链能否去中心化教育 `[部分核验：作者全名待补]`

- **完整引用**：Abdul Razzaq et al. (2026). Can Blockchain Decentralize Education? A Systematic Review of Challenges and Pathways. *IET Software*, 2026.
- **DOI**：10.1049/sfw2/5556408
- **一句话贡献**：系统综述 2017–2025 年 **64 项研究**，归纳出区块链教育应用的主要类别为：证书/文凭管理、微证书与学分转移、能力与评估追踪；并梳理了落地挑战。
- **与 LearnFlow 的差异**：该综述归纳的三大应用类别中**没有"算法决策审计"**。这直接支撑了缺口 G2-1 的"空白"主张。

### N3. Labaran Isiaku & Adalier (2025) —— TOE 框架下的采用壁垒 `[已核验]`

- **完整引用**：Labaran Isiaku, Ahmet Adalier (2025). Analyzing the Barriers to Blockchain Adoption in Educational Sectors [TOE framework]. *On the Horizon*, 33(1), 32–60. （ERIC: EJ1459604）
- **一句话贡献**：用技术-组织-环境（TOE）框架分析教育部门采用区块链的壁垒。
- **与 LearnFlow 的差异**：**这是"批评性文献"的重要来源**。任何 LearnFlow 的区块链论文都必须预先回应 TOE 壁垒（尤其是组织与环境层面的"没有多方互不信任的场景，就不需要区块链"）。

### N4. Jušić, Fuks, Kochovski & Stankovski (2025) —— 区块链微证书与 EBSI 实践 `[已核验]`

- **完整引用**：Jušić, Fuks, Kochovski, Stankovski (2025). Blockchain-Enabled Micro Credentialing [in European initiatives]. *EDULEARN25 Proceedings*, pp. 5382–5388.
- **DOI**：10.21125/edulearn.2025.1342
- **一句话贡献**：综述 EBSI、ESSA、NOO Ultra、TRUSTCHAIN、FRI Academy 等欧洲区块链微证书倡议，展示可验证凭证在教育中的制度化路径。
- **与 LearnFlow 的差异**：
  - **这条赛道已被占满且被制度化**。EBSI（European Blockchain Services Infrastructure）已有欧盟层面的官方推动，LearnFlow 作为一个尚无用户的项目去做"微证书上链"，既无制度资源也无规模优势。
  - **中文制度背景**：检索到浙江省终身学习微证书 / 学分银行（2025）已用区块链做微证书，提出 32 学时微证书、24 学时最低标准、长三角跨区域互认目标（来源：中国教育部及中国网相关报道，2025-12）。**这是中文语境的强信号**——意味着"学分互认 + 区块链"在中文场景也已被政策层面占据。

### N5. Hepp et al. (2018) —— OriginStamp：Merkle 树批量锚定 `[部分核验：卷期待补]`

- **完整引用**：Hepp, Schoenhals, Gondek, Gipp (2018). OriginStamp: A Blockchain-Backed System for Decentralized Trusted Timestamping. *it - Information Technology*, 2018.
- **机制（已核实，来自 docs.originstamp.com 官方文档与 2018-11-26 白皮书 v2）**：
  1. 客户端对文件做**本地 SHA-256**（原文不上传，隐私友好）；
  2. 在固定时间间隔内收集所有待存证哈希；
  3. 按字典序排序 → 构造**平衡 Merkle 树**；
  4. Merkle 根写入区块链。在比特币链上：把根**解释为一个私钥** → 推导出一个 BTC 地址 → **该地址的第一笔交易时间即为时间戳**（一个极其巧妙的"用地址本身编码数据"的技巧）。以太坊链亦支持。
- **与 LearnFlow 的差异**：这是 LearnFlow"区块链可信处理"**最应该选择的技术路线**——轻量、低成本、隐私友好（原文不上链）、可批量。但注意：**该方案本身不是我们的贡献**，我们必须贡献的是**它在教育场景下的量化评估**（见 G2-2）。

### N6. "blockchain for blockchain's sake" 批评文献 `[部分核验 —— 见附录 A]`

- **已核实的、可安全引用的批评来源**：Labaran Isiaku & Adalier (2025)（N3）从 TOE 框架给出的采用壁垒，是**同行评议过的一次文献**，可安全引用。
- **未能核实的、禁止引用的**：
  - "Gartner 2024：75% 的企业区块链项目用传统数据库/DLT 就够了" —— 仅见于行业媒体转述，**未定位到 Gartner 一次报告**。
  - "Roubini：43 个区块链开发/非营利实验 0 成功" —— 仅见于访谈二次转述，**未定位到原始研究**。
  - 各类 "blockchain is a tool, not a universal solution" 类表述多来自内容农场，**不可引用**。
- **给团队的硬性要求**：写"区块链批评"这一节时，**只引用 N3 与 N1 的"原型泛滥"数据**，这两条是一次文献且同行评议过。其余批评若必须用，须自行去 Gartner/学术数据库核实。

## 2.3 研究缺口（4 个）

### G2-1. 学习分析中的"算法决策审计轨迹"：文献空白

**可验证性**：N1（150 个模型）与 N2（64 项研究）归纳的应用类别均为"证书管理 / 微证书与学分转移 / 能力与评估追踪"，**两篇独立综述都没有列出"算法决策审计"这一类**。

**具体缺口**：现有区块链教育文献存储的是**学习结果**（成绩、证书、学分），而**不是产生这些结果的过程决策**。具体到 LearnFlow：
- 系统在时刻 t 为何把难度从 5 调到 6？
- 当时输入给决策器的特征是什么？（BKT 状态、Elo 值、FSRS 记忆难度、心流判定）
- 用的是哪个模型版本、哪套参数？
- 如果学生或监管方质疑"系统给我推了过难的题"，**是否有不可篡改的证据链**？

这类"**算法决策的可审计轨迹（audit trail for algorithmic decisions）**"在区块链教育文献中是空白，且与 EU AI Act 的可审计性要求、教育场景的算法问责诉求高度契合。

**但必须正面回答的杀手问题**：**为什么需要区块链，而不是 append-only 日志 + 哈希链 + 定期公证？**

**诚实的回答路径**（这也是论文的核心论证负担）：
1. _append-only DB + 哈希链_ 能防内部篡改，但**不能向外部第三方证明**时间先后与未篡改——因为哈希链的根仍由运营方控制。
2. 区块链的价值仅在**存在互不信任的多方**（学校、平台、监管、学生）时成立。
3. **因此，LearnFlow 的方案只有在"跨机构"场景下才自洽**——这也意味着它与"学分互认/跨机构"是天然绑定的，可以合并成一个故事。

**这是方向 ② 唯一的、可辩护的立足点。若放弃"跨机构多方"设定，方向 ② 应当整体降级或放弃。**

### G2-2. 轻量 Merkle 批锚定在教育场景的成本-收益从未被量化

**可验证性**：OriginStamp 类方案的机制已被核实（N5），但检索未发现任何针对教育场景的**量化评估**：每条记录的实际锚定成本、从提交到获得时间戳的延迟分布、批大小对成本与延迟的影响、以及**哈希本身是否泄漏信息**（例如：对"某学生某题是否答对"这种低熵事件做哈希，是否可被彩虹表/枚举攻击反推？——这是一个真实且未被讨论的隐私问题）。

**具体可验证的子问题**：
- 低熵事件哈希的**枚举攻击风险**：难度等级只有 10 个、正确与否只有 2 个，加盐前后的抗枚举性差异如何量化？
- 批大小 k 与"平均确认延迟"的权衡曲线。
- 与传统 append-only DB + 第三方公证（如 RFC 3161 TSA）的**成本对比**。

**可做的最小实证**：**完全无需真实用户数据**。用合成事件流 + 公开区块链费率数据即可完成全部测量。这是一个**高性价比、可独立完成**的论文点。

### G2-3. 可验证凭证在教育场景的撤销与最小化披露缺乏实证研究

**可验证性**：N4 综述的 EBSI/ESSA/TRUSTCHAIN 等倡议主要解决**签发与验证**，检索未发现教育场景下**撤销机制（revocation）**与**选择性披露（selective disclosure）**的实证研究。

**具体缺口**：成绩/学分凭证在实际使用中需要处理"成绩被更正""学生要求只披露某门课而不披露绩点""凭证过期"等情况。这些在教育场景的**实际发生频率与处理成本**从未被测量——这是一个**需要真实机构合作**才能做的缺口，当前不可写。标注为"需机构合作"。

### G2-4. 教育区块链的"必要性判据"缺少可操作的决策框架

**可验证性**：N1 的 124/150 原型率、N3 的 TOE 壁垒分析都指向同一个问题——大量项目在没有必要性论证的情况下上链。

**具体缺口**：**不存在一个可操作的判据**来判断"这个教育场景到底该不该上链"。可以形式化为：给定 (参与方数量、互不信任程度、写入频率、数据敏感性、监管要求) → 是否值得上链，以及上链后相比 append-only DB 的**额外收益与额外成本**。

**这是方向 ② 中 novelty 最高的缺口**，因为它**直接把"批评性文献"变成了贡献**——不是回避"blockchain for blockchain's sake"质疑，而是为这个质疑提供一个**可计算的答案**。这类"把批评形式化为判据"的论文在 SE/系统领域有明确的发表路径。

## 2.4 Novelty 诚实评估

### 已经死了的

| 设想 | 死因 |
|---|---|
| "用区块链存学历/证书" | Blockcerts、EBSI、ESSA 等已制度化；N4 综述已覆盖；做第 N+1 个无意义 |
| "用区块链做学分互认" | 同上，且中国浙江省已有政策级落地（2025） |
| "用区块链保证学习记录不可篡改" | 这是"blockchain for blockchain's sake"的教科书式案例，审稿人必问"为什么不用数据库" |
| "我们设计了一个教育区块链架构" | N1 已统计到 150 个模型，其中 26 个是纯提案。**纯架构论文在这个领域已经无法发表** |

### 还活着的（按推荐度排序）

1. **G2-4 上链必要性判据** —— 把批评变成贡献，novelty 最高，且**不需要区块链实现**（可纯理论/决策分析）。
2. **G2-2 轻量锚定的量化评估** —— 工程可完成、无需真实数据、有明确的测量指标。
3. **G2-1 算法决策审计轨迹** —— 空白确实存在，**但**必须以"跨机构多方"为前置条件，否则论证不自洽。

### 方向 ② 的整体建议

**降级为方向 ①③⑤ 的支撑模块，而不是独立论文主线。** 理由：
- 该方向的所有 novelty 都建立在"有跨机构多方互不信任"这一前提上，而 LearnFlow 当前是单机构、零用户的系统，前提不成立。
- G2-4 与 G2-2 可以独立成篇，且**与区块链教育的主体赛道解耦**（它们更像是"分布式系统的必要性分析"与"时间戳方案的性能测量"），投 SE/系统类期刊更合适，而不是教育类期刊。

## 2.5 目标期刊对标

| 期刊 / 会议 | CCF / 索引 | 定位 | 难度 | 周期 | 适配缺口 |
|---|---|---|---|---|---|
| **Information and Software Technology (IST)** | CCF-B（软件工程/系统软件/程序设计语言） | 软件工程实证 | 中 | 9–15 个月 | **G2-4（最适配）**、G2-2 |
| **Journal of Systems and Software (JSS)** | CCF-B | 软件与系统 | 中 | 9–15 个月 | G2-4、G2-2 |
| **Empirical Software Engineering (EMSE)** | CCF-B | 软件工程实证 | 中—高 | 12–18 个月 | G2-2（测量研究） |
| **IEEE Transactions on Learning Technologies (TLT)** | CCF 未列；SCI Q1 | 学习技术 | 中—高 | 9–18 个月 | G2-1（须绑定跨机构场景） |
| **Education and Information Technologies** | CCF 未列；SSCI | 教育技术 | 中 | 6–12 个月 | G2-1（保底刊） |
| **IEEE Access** | CCF 未列；SCI | 综合 | 低—中 | 3–6 个月 | 保底；但对本项目的 CCF 目标贡献有限 |
| **Blockchain: Research and Applications** | CCF 未列；新刊 | 区块链专门刊 | 中 | 6–12 个月 | G2-2（专门刊对口，但影响力待观察） |

**建议**：若坚持方向 ②，走 **IST / JSS（G2-4 判据 + G2-2 测量）**，避开教育类期刊的"为什么不用数据库"审查；**除非**能拿到真实跨机构合作，否则不要投教育类期刊。

---

# 第 3 章 方向 ③：游戏化分类学与消融

## 3.1 格局概述（144 字）

>游戏化的"有没有效"之争已由元分析终结：Sailer & Homner 2020 给出认知 g=0.49、动机 g=0.36、行为 g=0.25 的三级效应量，并识别出游戏叙事与社会互动为关键调节变量。单机制对心理需求的影响已由 Sailer 等 2017（N=419，2×2 设计）与 Mazarakis & Bräuer（N=505，四机制）完成。真空在两处：一是**生产级游戏化系统的机制实现债**（60 个机制中 48 个零调用，无人做过实证）；二是**暗黑模式与健康目标的冲突建模**（17 个未仲裁的 nudge 生成点，FOMO 直接对抗防沉迷）。

## 3.2 最近邻工作（8 篇）

### N1. Sailer & Homner (2020) —— 学习游戏化的元分析 `[已核验]`

- **完整引用**：Michael Sailer, Lisa Homner (2020). The Gamification of Learning: A Meta-Analysis. *Educational Psychology Review*, 32(1), 77–112.
- **DOI**：10.1007/s10648-019-09498-w
- **一句话贡献**：元分析给出游戏化对学习的三级效应量：
  - **认知** g = 0.49 [0.30, 0.69]，k = 19，N = 1686
  - **动机** g = 0.36 [0.18, 0.54]，k = 16，N = 2246
  - **行为** g = 0.25 [0.04, 0.46]，k = 9，N = 951
  - 调节变量：**游戏虚构（game fiction）与社会互动**对行为结果显著；竞争与协作均有效。
- **与 LearnFlow 的差异（我们站在哪）**：
  - **"游戏化有没有效"这个问题已经死了**，不要再做。
  - 关键启示：效应量**从认知到行为递减**（0.49 → 0.36 → 0.25），且**行为效应量的置信区间下限仅 0.04**。这意味着"游戏化能改变长期学习行为"的证据是弱的。LearnFlow 若声称"60 个游戏化机制提升学习投入"，**必须自己在行为层面测量**，不能靠引用元分析蒙混。

### N2. Sailer, Hense, Mayr & Mandl (2017) —— 单机制对心理需求的影响 `[已核验]`

- **完整引用**：Michael Sailer, Jan Ulrich Hense, Sarah Katharina Mayr, Heinz Mandl (2017). How gamification motivates: An experimental study of the effects of specific game design elements on psychological need satisfaction. *Computers in Human Behavior*, 69, 371–380.
- **DOI**：10.1016/j.chb.2016.12.033 （CC BY 开放获取）
- **样本与设计的准确数字**：**N = 419**（699 人登录，419 人完成全部游戏与问卷）；女性 204（48.7%），男性 215（51.3%），平均年龄 22 岁（M=22.39, SD=3.56）；在线模拟"订单分拣"环境；随机分配到不同机制配置。
- **核心发现**：
  - 徽章 / 排行榜 / 表现图表 → **胜任感需求满足** + 感知任务意义（+）
  - 头像 / 有意义的故事 / 队友 → **社会关联感**（+）
  - **感知决策自由（自主性）未被任何机制显著影响**
  - 结论原话："gamification is not effective per se, but specific game design elements have specific psychological effects"
- **与 LearnFlow 的差异（我们站在哪）**：
  - 这是"单机制消融"这一思路的**奠基文献**，也就是说——**"逐机制消融"这个想法本身不新了**。
  - **但**：它只做了 **7 个机制**（点数、徽章、排行榜、表现图表、故事、头像、队友），且是**实验室模拟任务**（订单分拣），**不是真实长期学习系统**。LearnFlow 有 **53 个去重后的机制**（60 个原始，去重后 53），是它的 **7.5 倍**，且是**生产系统、长期使用**。
  - **这才是我们的差异化：规模 × 真实性 × 长期性。**

### N3. Mazarakis & Bräuer (2021/2023) —— 四机制消融 `[部分核验：年份与载体待补]`

- **完整引用**：Athanasios Mazarakis, [Bräuer]（Kiel University）. Gamification is Working, but Which One Exactly? Results from an Experiment with Four Game Design Elements.
- **样本**：**N = 505**，最多 190 道多选题；机制为**进度条、叙事、反馈、徽章**四者。
- **核心发现**：单个机制各自都能带来显著的动机增益；**但机制组合的效应不等于各机制效应之和**（组合不叠加）。
- **与 LearnFlow 的差异**：
  - "组合不叠加"这一发现**直接威胁** LearnFlow 的 60 机制设计——如果 60 个机制的效果不叠加，那 60 个机制的意义何在？
  - **这正是 G3-3 的起点**：机制间的交互效应需要**因子设计（factorial design）**而非逐个 A/B。60 个机制的交互空间是 2^60，**必须**用稀疏因子设计或序贯实验。这是一个**明确的方法论缺口**。

### N4. Lieberoth (2015) —— 浅层游戏化：框架 vs 机制 `[已核验]`

- **完整引用**：Andreas Lieberoth (2015). Shallow Gamification: Testing Psychological Effects of Framing an Activity as a Game. *Games and Culture*.
- **DOI**：10.1177/1555412014559978
- **样本**：N = 90。
- **核心发现**：**仅仅把活动"框架化"为游戏（framing）**，在兴趣与享受上产生的效果**与完整游戏机制相当**。
- **与 LearnFlow 的差异**：**这是一颗定时炸弹**。它意味着 LearnFlow 花大力气实现的 60 个机制，其效果可能大部分来自"这个系统看起来像个游戏"这一**框架效应**，而非机制本身。
  - **负面影响**：若不回应，审稿人可用此文否定整个 60 机制工程。
  - **正面机会**：LearnFlow 可以做一个**罕见的、文献中缺失的对比实验**——"完整机制 vs 纯框架 vs 无游戏化"三臂设计，在**真实生产系统、长期**条件下检验 Lieberoth 的结论是否稳健。Lieberoth 只有 N=90 且是短时实验室任务；我们在真实系统上的复制/否证是**有明确价值的**。

### N5. Gray, Kou, Battles, Hoggatt & Toombs (2018) —— 暗黑模式分类学（CHI） `[已核验]`

- **完整引用**：Colin M. Gray, Yubo Kou, Bryan Battles, Joseph Hoggatt, Austin L. Toombs (2018). The Dark (Patterns) Side of UX Design. In *Proceedings of the 2018 CHI Conference on Human Factors in Computing Systems (CHI '18)*, Paper 534, 1–14.
- **DOI**：10.1145/3173574.3174108 ；**CCF-A**
- **一句话贡献**：分析 **118 个由从业者识别的暗黑模式实例**，归纳出五类高阶策略：**Nagging（纠缠）、Obstruction（阻碍）、Sneaking（隐瞒）、Interface Interference（界面干扰）、Forced Action（强迫行为）**；并指出"用户价值被股东价值取代"是共同特征。
- **与 LearnFlow 的差异（我们站在哪）**：
  - **这是方向 ③ 最重要的一篇**，因为 LearnFlow 有 **17 个未仲裁的 nudge 生成点**——即系统会在没有统一仲裁的情况下向用户推送劝导性消息。
  - FOMO（错失恐惧）类 nudge 在 Gray 五分类中主要落在 **Nagging**（持续纠缠）与 **Interface Interference**（界面干扰）两类；而 LearnFlow 的**学习成瘾指数 LAI** 试图**降低**成瘾——**系统在同时做两件方向相反的事**。
  - **这个矛盾本身就是一个可发表的发现**，且**没有任何一篇文献做过**（检索未命中 "dark pattern" 与 "learning addiction / anti-addiction" 的交叉研究）。

### N6. Crespo, López-Nozal, Marticorena-Sánchez, Gonzalo-Tasis & Piattini (2022) —— 游戏化对技术债无效 `[已核验]`

- **完整引用**：Yania Crespo, Carlos López-Nozal, Raúl Marticorena-Sánchez, Margarita Gonzalo-Tasis, Mario Piattini (2022). The role of awareness and gamification on technical debt management. *Information and Software Technology*, 150, 106946, October 2022.
- **DOI**：10.1016/j.infsof.2022.106946 ；**CCF-B**
- **设计**：准实验，三种处理：(1) 技术债/坏味道/重构培训 + IDE 插件；(2) 处理 1 + 用工具（SonarQube）持续提升技术债意识；(3) 处理 2 + 游戏化组件（竞赛 + 前十名排行榜）。
- **核心结果（原文摘要直译）**：
  - 用技术债管理工具（SonarQube）持续提升意识，**显著改善**参与者所写代码的技术债指标；
  - **但引入竞赛 + 排行榜形式的开发者竞争，对技术债指标没有带来任何显著差异**；
  - 结论要点：**"Gamification has a minor effect on indicators compared to the use of SonarQube."**
- **与 LearnFlow 的差异（我们站在哪）**：
  - **这是一篇"反向文献"，价值极高**。它提供了同行评议的证据：**在游戏化被期待起作用的工程场景中，游戏化机制（竞赛+排行榜）没有产生显著效果，而单纯的"工具 + 意识"有效。**
  - 它与 LearnFlow 的 "60 个机制中 48 个零调用" 形成**互证**：机制被大量实现，但对工程/行为结果的边际贡献可能很小。
  - **注意引用时的诚实边界**：Crespo 研究的是**开发者还技术债**，不是**学生学习**。跨领域外推必须谨慎，不能说"Crespo 证明了游戏化无效"，只能说"Crespo 提供了一个'机制数量 ≠ 结果改善'的同类证据"。

### N7. 游戏化 × 软件工程的技术债脉络 `[部分核验，供进一步追踪]`

- Crespo 等 (2022) 的参考文献列表中出现了一批相关条目，可作为**引文滚雪球**的起点（**这些条目未经独立核实，需自行核验后方可引用**）：
  - Pedreira et al., "Gamification in software engineering - A systematic mapping", *IST*, 57 (2015) 157–168.
  - de Paula Porto et al., "Initiatives and challenges of using gamification in software engineering: A systematic mapping", *JSS*, 173.
  - Alhammad et al., "Gamification in software engineering education: A systematic mapping", *JSS*.
  - Stol et al., "Gamification in software engineering: The mediating role of developer engagement and job satisfaction", *Empirical Software Engineering*.
  - Besker et al., "The use of incentives to promote technical debt management", *IST*, 142 (2022).
- **用途**：这些条目说明"游戏化 × 软件工程"已是一个**有系统映射研究（systematic mapping）的成熟子领域**，因此 LearnFlow 的"游戏化技术债"论文必须**明确对标这些 mapping 研究**，说明自己的位置是"生产系统实证"而非"又一次 mapping"。

### N8. 暗黑模式的监管与实证脉络 `[部分核验：一次文献需自行补齐]`

- 检索到的、可信度较高的二级脉络（**引用前须回溯一次文献**）：
  - **Mathur et al. (2019)** —— 大规模实证审计：爬取 **11,000 个**高流量购物网站，在其中的 **1,254 个**上编目了 **1,818 个**暗黑模式实例（约 11% 的顶级购物网站使用暗黑模式，且因爬虫限制属低估）。**这是"暗黑模式实证审计"的方法学模板，LearnFlow 应直接借鉴其方法。**
  - **OECD (2022) Dark Commercial Patterns**；**FTC (2022) Bringing Dark Patterns to Light** 员工报告；**EU Digital Services Act 第 25 条**明确禁止超大型在线平台使用暗黑模式。
  - 这三份监管文件意味着：到 2026 年，**暗黑模式已从学术概念变成法律概念**。教育平台若使用 FOMO 类 nudge，**存在真实的合规风险**。这大幅提升 G3-2 的分量。
- **硬性提醒**：以上三条（Mathur / OECD / FTC）在本轮检索中**只见到二级转述**，未定位到一次文献 PDF。**列入附录 A，引用前必须自行核实。**

## 3.3 研究缺口（5 个）

### G3-1. 生产级游戏化系统的"机制实现债"：无人做过实证

**可验证性（LearnFlow 自身的一手数据）**：
- 60 个游戏化机制分布在 9 个引擎文件中；
- 去重后 53 个；
- **其中 48 个在生产代码中零调用（zero invocation）**；
- 另有 **11 个内存容器**（in-memory containers）——即状态只存在内存、不持久化，进程重启即丢失。

**具体缺口**：游戏化文献中，**所有**消融实验都是"研究者设计好 k 个机制，招募被试，跑实验"（Sailer 2017: k=7；Mazarakis: k=4）。**没有任何一篇研究过一个真实生产系统里"被实现但从未被使用"的机制**——即**工程的"供给"与"使用"之间的巨大落差**。

**这是一个全新且只有 LearnFlow 有数据的研究对象**（因为需要先有一个真实的大规模游戏化系统才会产生这种数据）。

**可做的最小实证（极其重要）**：
1. 静态分析：对 53 个去重机制做调用图分析，量化"实现-调用"落差，并按机制类型（Sailer 分类学）分层。
2. 根因分类：零调用的机制属于哪几类？（a）从未接入 UI；（b）接入但触发条件永不满足；（c）触发但无可见反馈；（d）被更晚实现的机制取代（重复实现）。
3. 后果量化：11 个内存容器在重启时丢失什么状态？用户可观测的后果是什么？
4. **跨项目复制**：单项目案例只能发 short paper。必须找 **≥ 3 个**其他开源游戏化学习系统做同样的静态分析，证明"机制实现债"是**普遍现象**而非 LearnFlow 独有。**这一步是能否发到 CCF-B 及以上期刊的分水岭。**

### G3-2. 暗黑模式与健康目标的"对立建模"：文献零命中

**可验证性**：
- 检索 `("dark pattern" OR "FOMO" OR "loss aversion") AND ("learning" OR "education" OR "gamification")` → 大量命中国民级论述与博客；
- 检索加入 `("learning addiction" OR "anti-addiction" OR "digital wellbeing" OR "healthy engagement")` → **零相关命中**。

**具体缺口**：**没有任何研究把一个教育系统内同时存在的"成瘾性劝导"与"防成瘾干预"建模为一对冲突目标并给出仲裁机制。** LearnFlow 的具体矛盾：
- **17 个未仲裁的 nudge 生成点**：系统多处独立地生成劝导消息，没有统一的仲裁层；
- 其中 FOMO 类 nudge（如"你的连续记录即将中断""XX 同学已经超过你"）**直接对抗** LAI（学习成瘾指数，0–100，五维加权）想要降低的成瘾行为。

**可做的最小实证**：
1. **审计**：用 Gray et al. 2018 的五分类（Nagging / Obstruction / Sneaking / Interface Interference / Forced Action），对 LearnFlow 全部 nudge 模板做双评审员编码，报告各类占比与编码者一致性（Cohen's κ）。
2. **冲突检测**：形式化定义"nudge 的目标方向向量"与"LAI 的干预方向向量"，计算二者的**余弦相似度**，找出**方向相反（负相关）的 nudge**，报告其数量与触发频率。
3. **仲裁器设计 + 离线评估**：设计统一仲裁层（冲突 nudge 抑制/改写），用仿真用户模型评估对 LAI 与学习时长的影响。

**不需真实用户即可完成第 1、2 步**；第 3 步可仿真。

### G3-3. 机制交互效应的因子设计方法论缺失

**可验证性**：Mazarakis & Bräuer 已发现"组合不叠加"（N3），但它们的 max 组合只有 4 个机制。

**具体缺口**：53 个机制的**交互效应空间是 2^53**，逐个 A/B 不可行。文献中**没有**针对游戏化机制的**稀疏因子设计（sparse factorial design）**或**序贯实验（sequential experimental design）**方法论。

**可做的最小实证**：把"机制子集选择"形式化为一个**稀疏交互检测问题**（如用 compressive sensing / 稀疏正则回归在 2^k 的部分实现上检测低阶交互），并在仿真环境 + 小规模真人（若可得）上验证。这是一个**方法论贡献**，且**与具体系统解耦**，novelty 独立于 LearnFlow 本身。

### G3-4. "框架效应"在真实长期学习系统中的稳健性未检验

**可验证性**：Lieberoth (2015) N=90、短时实验室任务；Sailer (2017) N=419、单次模拟任务。

**具体缺口**：**"游戏化效果有多少来自'看起来像游戏'而非机制本身"** 这一关键问题，只在**小规模、短时、实验室**条件下被检验过。**在真实生产系统、以周/月为尺度**的检验是空白。

**可做的最小实证**：三臂设计 —— (a) 完整机制；(b) 仅框架（视觉/语言游戏化，机制全部禁用）；(c) 无任何游戏化。测量长期（≥ 4 周）留存与学习行为。**需要真实用户，当前不可写**，但**这是 LearnFlow 一旦有了用户就必须第一个做的实验**，因为它同时回应了 Lieberoth 与 Sailer & Homner 的行为层面弱效应。

### G3-5. 游戏化机制与"工程产出"的脱钩：从技术债到学习结局

**可验证性**：Crespo et al. 2022 在**软件工程**场景给出了"游戏化机制 ≠ 工程指标改善"的证据。

**具体缺口**：**在学习平台场景中，不存在同类研究**——即"平台实现的游戏化机制数量/复杂度，与学习结局改善之间，是否存在任何正相关"。所有现有研究都是"研究者精心设计的 k 个机制 vs 无"，**没有"机制数量作为自变量"的研究**。

**可做的最小实证**：如果 G3-1 的跨项目复制能拿到 ≥ 10 个游戏化学习平台的数据，可以做"机制数量 vs 报告的效应量"的**剂量-反应（dose-response）分析**。若发现**无剂量-反应关系甚至负相关**，那是一个**非常重要的、挑衅性的、可发在高影响力期刊**的结论。

## 3.4 Novelty 诚实评估

### 已经死了的

| 设想 | 死因 |
|---|---|
| "游戏化对学习有效吗" | Sailer & Homner 2020 元分析已答（g=0.49/0.36/0.25） |
| "哪个机制影响哪种心理需求" | Sailer et al. 2017（N=419）已答：徽章/榜/图表→胜任感；头像/故事/队友→关联感；自主性不受影响 |
| "我们提出一个新的游戏化分类学" | Sailer / Hamari / Morschheuser / Deterding 的分类学已足够；第 N+1 个分类学无价值 |
| "消融实验"这一想法本身 | Sailer 2017 与 Mazarakis 已做。我们必须说清楚：**我们的消融是 53 个机制、生产系统、且研究的是"实现债"而非"心理效应"** |

### 还活着的（按推荐度排序）—— **本方向是五个方向中 novelty 最有保障的**

1. **G3-1 机制实现债**（★★★★★）—— **LearnFlow 就是数据集**。48/60 零调用 + 11 个内存容器，这是别人拿不到的一手材料。**唯一门槛是必须做跨项目复制**。
2. **G3-2 暗黑模式 vs 防沉迷的对立建模**（★★★★★）—— **文献零命中 + 有监管顺风（DSA 第 25 条、FTC 报告、OECD）+ 有权威分类学（Gray CHI'18）可挂靠**。这是本报告发现的**最锋利的单一缺口**。
3. **G3-3 因子设计方法论**（★★★★）—— 与具体系统解耦，novelty 独立，但理论门槛高。
4. **G3-5 剂量-反应**（★★★）—— 挑衅性强，但数据采集难度高（需 ≥ 10 个平台）。

### 关键判断

**方向 ③ 是 LearnFlow 最应该主攻的方向**，理由有三：
1. **数据自给**：不需要真实用户，代码库本身就是研究对象。
2. **缺口真实**：检索确认空白，且有权威文献可挂靠（Gray CHI'18 / Sailer CHB'17 / Crespo IST'22）。
3. **批评性视角本身就是 novelty**：把"我们自己系统的失败"写成论文，比"我们的算法更好"更可信，也更容易过审。

## 3.5 目标期刊对标

| 期刊 / 会议 | CCF / 索引 | 定位 | 难度 | 周期 | 适配缺口 |
|---|---|---|---|---|---|
| **ACM CHI** | **CCF-A** | 人机交互顶会 | 极高 | 一轮 4–6 个月，常需 2–3 轮 | G3-2（暗黑模式审计）—— 需强用户研究支撑 |
| **ACM CSCW** | **CCF-A** | 社会计算顶会 | 极高 | 同上 | G3-2、G3-4 |
| **Computers in Human Behavior** | CCF 未列；SSCI Q1 | 人机行为 | 中—高 | 6–12 个月 | G3-2、G3-4（最对口的行为学刊） |
| **Information and Software Technology** | **CCF-B** | 软件工程实证 | 中 | 9–15 个月 | **G3-1（最适配）** |
| **Empirical Software Engineering (EMSE)** | **CCF-B** | 软件工程实证 | 中—高 | 12–18 个月 | **G3-1（跨项目复制版）** |
| **MSR (Mining Software Repositories)** | CCF-B（会议） | 软件仓库挖掘 | 中 | 4–6 个月出结果 | **G3-1 的起步版本（静态分析）** |
| **IEEE Transactions on Learning Technologies** | CCF 未列；SCI Q1 | 学习技术 | 中—高 | 9–18 个月 | G3-2、G3-4（教育场景版） |
| **Computers & Education** | CCF 未列；SCI/SSCI Q1，IF 8+ | 教育技术顶刊 | 极高 | 12–24 个月 | G3-4（需真人数据） |

**建议路线**：
- **第一步（立即）**：MSR 或 IST short paper —— 53 机制静态分析 + 实现债分类学（G3-1 单项目版）。
- **第二步（3–6 个月）**：EMSE / IST 完整版 —— 跨 ≥ 3 个开源游戏化学习系统的复制研究。
- **第三步（并行）**：CHI / Computers in Human Behavior —— 17 个 nudge 点的暗黑模式审计 + 与 LAI 的冲突检测（G3-2）。**这一条最有可能出 CCF-A。**

---

# 第 4 章 方向 ④：学习分析的可复现性与数据质量危机

## 4.1 格局概述（147 字）

>学习分析的可复现性危机已被领域内承认，但量化证据主要来自预印本：一份 2015–2025 深度知识追踪系统综述报告 82.1% 的研究只用 ASSIST 系列数据集、56.0% 未处理数据质量、仅 3.6% 使用定量的序列稳定性指标、90.5% 只报 AUC。该综述本身尚未同行评议，需谨慎引用。独立信源（Abdelrahman 等 2023, ACM CSUR）从数据预处理角度确认了同类问题。标准侧，xAPI 已升级为 IEEE 9274.1.1-2023，但规范作者本人与 SoLAR 立场文件均指出：标准合规不等于数据质量。

## 4.2 最近邻工作（6 篇）

### N1. "A Systematic Review of Deep Knowledge Tracing (2015–2025)" ⚠️ 预印本 `[部分核验：载体与编号已确认，同行评议状态未确认]`

- **完整引用**：*A Systematic Review of Deep Knowledge Tracing (2015-2025): Toward Responsible AI for Education*. Preprints.org, manuscript **202510.1845**.
- **核心数据（团队此前引用的四个数字均出自此文）**：
  - **82.1%** 的 KT 研究仅使用 ASSIST 系列数据集
  - **56.0%** 未处理数据质量问题
  - **仅 3.6%** 使用定量的序列稳定性指标
  - **90.5%** 仅报告 AUC
- **⚠️ 引用纪律（重要）**：
  1. 这是 **Preprints.org 预印本，未经同行评议**。
  2. **不得**直接作为"已知事实"引用。**必须**写成："一份尚未同行评议的预印本综述报告……（Preprints.org, 202510.1845）"
  3. **强烈建议**回溯该文的原始引用（文中编号 [77]、[78]、[44]、[45]、[56]、[30]）定位一次文献，用一次文献替代预印本断言。
  4. 若无法回溯，**改用 N2（Abdelrahman et al. 2023, ACM CSUR）作为主引**，它独立确认了数据集与预处理问题，且是 CCF-A 同行评议文献。

### N2. Abdelrahman, Wang & Nunes (2023) —— 独立信源 `[已核验]`

- **完整引用**：同第 1 章 N4。*ACM Computing Surveys*, 55(11), Article 224. DOI 10.1145/3569576. **CCF-A**
- **独立确认的数据质量问题**：
  - 不一致的预处理（inconsistent preprocessing）
  - 重复条目（duplicate entries）
  - 错误的时间戳（incorrect timestamps）
  - 缺失的知识组件标注（missing KC annotations）
  - 多个 KC 被压缩进单个 CSV 字段（如 KDDcup 用 `~~` 拼接）
  - 缺乏人口学信息
  - **无数据集版本控制**
- **与 LearnFlow 的差异**：这篇是**可以放心引用的主引**。它同时说明：LearnFlow 若要写"数据质量"论文，这些是**已被承认的问题清单**——我们的贡献不能是"发现了这些问题"，必须是**量化了后果**或**提供了工具**。

### N3. IEEE 9274.1.1-2023（xAPI 2.0）—— 标准 `[已核验]`

- **完整引用**：IEEE Std 9274.1.1-2023, *IEEE Standard for Experience API (xAPI) for Learning, Training, and Education Data Interchange, Data Model and Processing Requirements*，批准日期 2023-03-30。
- **关键事实（来自规范作者的十年回顾）**：
  - xAPI 已走完十年；
  - **签名声明（signed statements）与附件（attachments）"mostly unused"**；
  - 规范作者本人表示"personally disappointed"。
- **与 LearnFlow 的差异**：**"标准作者本人说这个功能基本没人用"** 是一个**极强的、可引用的、来自权威的批评**。它使"我们实现了 xAPI 兼容"这个卖点**失去价值**——因为标准的先进特性在实践中是死的。

### N4. SoLAR 立场文件 (2020) —— "标准实现糟糕" `[已核验]`

- **完整引用**：Society for Learning Analytics Research (SoLAR) 立场文件（2020），关于学习分析标准与互操作性的立场声明。来源：solaresearch.org。
- **核心论断（三条，均可直接引用）**：
  1. **采用 Caliper/xAPI 并不会自动改善数据质量**；
  2. xAPI 与 IMS Caliper 之间的**标准竞争**本身是问题；
  3. 标准的设计者是**技术导向而非教学导向**，导致产出的数据"**在教学上无关的概念上过于细粒度，在关键重要概念上又过于粗粒度**"（原文：too fine-grained over educationally irrelevant concepts, too coarse-grained over concepts of key importance）。
- **与 LearnFlow 的差异**：第 3 条是**致命的洞察**，它意味着：**即使 LearnFlow 完美实现 xAPI，产出的数据仍可能在教学上无意义**。这直接支撑缺口 G4-2。

### N5. Kitto et al. (2020) —— xAPI 的语义互操作缺陷 `[部分核验：载体待补]`

- **完整引用**：Kitto et al.（University of Technology Sydney, Connected Learning Analytics toolkit 报告, 2020）。
- **核心论断**：**xAPI 并不要求 verb/object 具有可互操作的语义**——即两个系统都"合规"地发 xAPI 语句，但它们的动词与对象词汇互不相通。
- **与 LearnFlow 的差异**：这是"标准合规 ≠ 互操作"的**机制性解释**（不只是抱怨，而是指出规范内的具体缺陷）。

### N6. Mangaroska et al. (2019) —— 多源数据集成的实证研究缺口 `[部分核验：载体待补]`

- **完整引用**：Mangaroska et al. (2019). [学习分析多源数据集成综述]。
- **核心发现**：在综述的 LA 多源数据集成研究中，**没有任何一项使用 Caliper**。
- **与 LearnFlow 的差异**：这是"标准采用率低"的一个**硬数字**，可引用。

## 4.3 研究缺口（4 个）

### G4-1. 未校准 BKT 参数在零真实数据下的不可辨识性 —— **可直接命中 56% / 3.6% 两个数字**

**可验证性**：`knowledge_tracing.py` 硬编码 `p_learn0=0.35`、`p_transit=0.12`，无拟合过程。

**具体缺口**：这不是"我们参数没调好"这种工程瑕疵，而是一个**可被形式化证明的可辨识性（identifiability）问题**：
- BKT 的四参数（p_init / p_learn / p_guess / p_slip）在**只有二元作答序列**的条件下存在**已知的可辨识性病理**（多组参数产生相同的似然，即参数不可辨识；且参数估计常退到边界 0/1）；
- 在**没有任何真实数据**的情况下，LearnFlow 用的是**文献默认值或凭直觉设定**，因此**其输出的"掌握概率"不具备任何实证含义**；
- 而**难度决策直接消费这个掌握概率** → **整个自适应难度链路是建立在一个不可辨识的量之上**。

**这是一个可以严格论证、且完全不需要真实数据的贡献**：
1. 形式化：给定二元作答序列与 BKT 模型，证明/展示参数不可辨识（似然面多峰/平坦）。
2. 敏感性分析：在 (p_learn, p_transit) 的合理网格上扫描，测量**下游难度决策的变化幅度**。若参数在合理范围内扰动就导致难度推荐系统性改变，则证明"未校准 BKT → 不可复现的难度决策"。
3. **这正是 56% 的研究"未处理数据质量"与 3.6% 关注"序列稳定性"的具体后果实例化**——我们把一个抽象的领域危机，**落到一个具体的、可测量的系统上**。

**可做的最小实证**：纯数值实验 + 公开数据集（ASSISTments / CodeWorkout）上的重采样，**无需真实用户**。

### G4-2. "标准合规 ≠ 数据质量"：可操作的实证检验

**可验证性**：N4（SoLAR 2020）与 N5（Kitto 2020）都给出了机制性论断，但**都是立场性/描述性的**，**没有实证测量**。

**具体缺口**：**没有人量化过**"一个 xAPI 合规的数据流，其教学信息含量是多少"。

**可做的最小实证**：
1. 定义**教学信息含量**的可操作度量（如：数据流能否区分 N 种已知的学习行为模式；能否支撑 K 个下游分析任务）。
2. 构造/收集若干 xAPI 合规数据流（含 LearnFlow 自己的），测量其信息含量。
3. 对照 SoLAR 的预测（"在无关概念上过细、在关键概念上过粗"），检验是否成立。

**这是一个"把权威批评变成可测量假设"的贡献，且不需要真实用户**（可用公开 xAPI 数据集与合成数据）。

### G4-3. KT 模型排名在小样本下的稳定性 —— **pyKT 基准本身可被审计**

**可验证性**：
- pyKT（IEEE TKDE 2025）在 9 个数据集上评估 21 个模型，给出了模型排名；
- CodeWorkout 相关研究**常因算力限制只抽样 100 名学生**（UMAP 2025 论文明确自述"we used a random sample of 100 students... due to computational constraints"）；
- 自适应游戏化研究样本极小（I-PLATO / GhostCoder 两个原型 N=32 与 N=15，合计 47）。

**具体缺口**：**pyKT 给出的 21 个模型的排名，在小样本（n=50/100/200）下是否稳定？** 即：
- 用 bootstrap / 子采样重跑 pyKT 的评估流程，测量**模型排名的 Kendall τ 稳定性**随样本量的变化曲线；
- 找出"**至少需要多少学生，才能以 95% 置信度区分排名前 5 的模型**"这一**最小可分辨样本量（minimum detectable sample size）**。

**意义**：
1. **完全不需要真实用户数据**——pyKT 与 9 个数据集都是公开的。
2. **结果有普适价值**——它直接告诉整个领域"你的 n=100 研究能不能区分模型"。
3. **直接命中"小样本与模拟学习者"这一缺口**，且**结论很可能令人不适**（即：绝大多数小样本 KT 研究无法区分模型），这正是高影响力论文的特征。

**这是方向 ④ 中性价比最高的论文点。强烈建议优先执行。**

### G4-4. 模拟学习者的"虚假可复现性"

**可验证性**：自适应系统研究大量使用模拟学习者（simulated learners）做评估。

**具体缺口**：模拟学习者使实验**完全可复现**（因为随机种子可固定），但这种**可复现是虚假的**——它可复现的是"模拟器的行为"，而不是"真实学习者的行为"。**没有人系统研究过"用模拟学习者得出的结论，在真实学习者上有多大比例能复现"**。

**可做的最小实证**：在公开数据集上，用常见的模拟学习者构造（如固定学习率的理想学习者、BKT 生成的学习者）跑一套 KT/难度策略的对比实验，再在真实数据上跑同一套实验，测量**结论一致率**。

**这是一个"元科学（meta-science）"贡献，且完全不需要真实用户。**

## 4.4 Novelty 诚实评估

### 已经死了的

| 设想 | 死因 |
|---|---|
| "KT 研究数据集单一（都用 ASSIST）" | 已被反复报道（预印本 82.1%，CSUR 独立确认）。**作为"发现"已死；作为"动机"可用** |
| "学习分析存在可复现性危机" | 立场文件与综述已说过多遍。**再次陈述不构成贡献** |
| "我们实现了 xAPI" | 标准作者本人说高级特性"mostly unused"；SoLAR 说标准合规不改善数据质量。**卖点已失效** |

### 还活着的（按推荐度排序）

1. **G4-3 KT 模型排名的小样本稳定性**（★★★★★）—— **完全用公开数据 + pyKT 可完成；结论有普适价值；很可能得出令人不适的结论。这是整个五个方向里"投入产出比最高"的论文点。**
2. **G4-1 未校准 BKT 的不可辨识性 → 难度决策不可复现**（★★★★）—— 把领域危机落到一个具体系统上，且是 LearnFlow 的**自我审计**，可信度高。
3. **G4-4 模拟学习者的虚假可复现性**（★★★★）—— 元科学贡献，novelty 高，但门槛也高（需要精心设计）。
4. **G4-2 标准合规 ≠ 数据质量的实证检验**（★★★）—— 把权威批评操作化，但"教学信息含量"的度量定义是难点。

### 关键判断

**方向 ④ 是唯一一个"0 真实数据"完全不构成障碍的方向**，因为它的研究对象**就是**"当数据不足/质量差时会发生什么"。这个自我指涉的特性使它成为当前状态下**最稳妥的论文产出方向**。

## 4.5 目标期刊对标

| 期刊 / 会议 | CCF / 索引 | 定位 | 难度 | 周期 | 适配缺口 |
|---|---|---|---|---|---|
| **LAK (Int'l Conf. on Learning Analytics & Knowledge)** | CCF 未列；学习分析**第一顶会** | 学习分析 | 中—高（录用率约 20–25%） | 4–6 个月出结果 | **G4-3（最适配）**、G4-1 |
| **EDM (Educational Data Mining)** | CCF 未列；教育挖掘顶会 | 教育挖掘 | 中—高 | 4–6 个月出结果 | G4-3、G4-1 |
| **Journal of Learning Analytics** | CCF 未列；领域专门刊，开放获取 | 学习分析 | 中 | 6–12 个月 | G4-1、G4-2 |
| **Journal of Educational Data Mining (JEDM)** | CCF 未列；领域专门刊 | 教育挖掘 | 中 | 6–12 个月 | G4-3 |
| **IEEE Transactions on Learning Technologies** | CCF 未列；SCI Q1 | 学习技术 | 中—高 | 9–18 个月 | G4-1、G4-3（期刊完整版） |
| **Computers & Education** | CCF 未列；SCI/SSCI Q1，IF 8+ | 教育技术顶刊 | 极高 | 12–24 个月 | G4-3（若结论足够普适，有冲击力） |
| **Scientific Reports** | CCF 未列；SCI | 综合 | 中（重技术正确性，轻影响力） | 4–9 个月 | G4-3、G4-4（保底；对 CCF 目标贡献有限） |

**建议**：**LAK/EDM 抢首发（G4-3）**，理由是"模型排名稳定性"这类结论**时效性极强**（pyKT 刚出，窗口期短，越早越好）。随后扩展为 IEEE TLT 或 Computers & Education 的期刊版。

---

# 第 5 章 方向 ⑤：CS 教育与编程学习适应性

## 5.1 格局概述（145 字）

>LLM 在计算机教育中的应用已由 SIGCSE TS 2025 的系统综述完成盘点，代码知识追踪也已形成完整技术线（Code-DKT → OKT → TIKTOC → KCGen-KT），公开数据集（CodeWorkout、FalconCode）与 ProgSnap2 格式已就位。真正的真空在**难度适应性**本身：编程教育中做自适应难度调整的研究极少，且样本极小——I-PLATO 的两个原型合计仅 N=47。这使方向 ⑤ 成为五个方向中**空白最大、最容易占位的方向**。

## 5.2 最近邻工作（7 篇 / 数据集）

### N1. Raihan, Siddiq, Santos & Zampieri (2025) —— LLM 在 CS 教育的系统综述 `[已核验]`

- **完整引用**：Raihan, Siddiq, Santos, Zampieri (2025). Large Language Models in Computer Science Education: A Systematic Literature Review. *SIGCSE TS 2025*（第 56 届 ACM Technical Symposium on Computer Science Education）, Pittsburgh, 7 pages. 预印本 *arXiv:2410.16349*。
- **一句话贡献**：系统综述 LLM 在 CS 教育中的应用现状。
- **与 LearnFlow 的差异**：**"LLM 在 CS 教育中的系统性盘点"这个位置已被占**。LearnFlow 不要再做综述。它的价值在于：为我们的 LLM 相关工作提供**引用锚点**与**已知空白清单**。

### N2. LLM 在编程教育中的应用综述（ACL 2025） `[部分核验：作者列表待补]`

- **完整引用**：*A Survey of LLM-Based Applications in Programming Education: Balancing Automation and Human Oversight*. ACL Anthology **2025.hcinlp-1.21**。
- **一句话贡献**：综述 SIGCSE / ITiCSE / ICER / LAK / EDM / CHI / EMNLP 2021–2025 的文献，聚焦三个方向：**形成性代码反馈（20 篇）、评估（14 篇）、知识建模（8 篇）**。
- **与 LearnFlow 的差异**：三个焦点中**没有"难度适应性/题目排序"**。这是一个**可引用的空白证据**。

### N3. TIKTOC (LAK 2025) —— 测试用例级代码知识追踪 `[已核验]`

- **完整引用**：Zhangqi Duan, Nigel Fernandez, Alexander Hicks, Andrew Lan (2025). Test Case-Informed Knowledge Tracing for Open-ended Coding Tasks. In *LAK 2025: The 15th International Learning Analytics and Knowledge Conference*, March 03–07, 2025, Dublin, Ireland. ACM, New York, NY, USA. 预印本 *arXiv:2410.10829*。
- **DOI**：10.1145/3706468.3706500
- **一句话贡献**：提出 TIKTOC，用 LLM 作为骨干网络，多任务学习**同时预测"学生代码是否通过每个测试用例"与"学生的开放式代码本身"**；用测试用例信息增强 CodeWorkout 数据集。
- **数据规模**：246 名学生 / 3,714 次提交 / 305 个测试用例 / 17 道题。
- **核心结果**：**优于只用总分的 KT 方法**；测试用例信息与代码结合能给出细粒度的知识洞察。
- **与 LearnFlow 的差异（我们站在哪）**：
  - **TIKTOC 证明了"细粒度的测试通过信号 > 粗粒度的总分信号"**。
  - LearnFlow 的难度引擎目前**只消费二元正确率**（答对/答错）。**这在技术上已经落后一代**。
  - **这既是威胁也是明确的机会**：把测试通过率的**结构化模式**（哪类测试失败 = 哪类概念缺失）接入难度选择，是 TIKTOC 铺好路但**没有走**的那一步。见 G5-3。

### N4. KCGen-KT (2025) —— LLM 生成知识组件 `[部分核验：正式发表状态待补]`

- **完整引用**：*KCGen-KT*（预印本 *arXiv:2502.18632v4*）。
- **一句话贡献**：比较 **LLM 生成的知识组件（KC）** 与**人工编写的 KC** 在知识追踪上的效果，用 CodeBLEU 等指标评估。
- **数据规模**：CodeWorkout（246 名学生 / 50 题 / 10,834 次首次提交）+ FalconCode（3,267 名学生 / 157 题 / 28,617 次提交）。
- **与 LearnFlow 的差异**：见 G5-2 —— 它把 LLM 生成的 KC 用于**追踪**，但**没有把 KC 反馈给难度选择**。

### N5. CodeWorkout 数据集 `[已核验]`

- **规格**：第 2 届 CSEDM Data Challenge 数据集；**ProgSnap2** 格式；Java CS1 课程；2019 春/秋学期，分别为 **329 与 490 名学生**；**50 道题**；**> 65,000 次提交**。
- **字段**：测试用例通过百分比、编译器消息、期末成绩。
- **与 LearnFlow 的差异**：**这是方向 ⑤ 最可直接利用的公开资产**。规模大（65k 提交）、有测试级信号、有编译器消息。**LearnFlow 的难度算法可以在这个数据集上做离线重放评估，完全不需要真实用户。**

### N6. FalconCode 数据集 `[已核验]`

- **DOI / 出处**：10.1145/3545945.3569822
- **规格**：入门 Python 课程；**3,267 名学生 / 157 题 / 20 个知识组件**。
- **与 LearnFlow 的差异**：Python 场景（CodeWorkout 是 Java），且规模更大。二者构成互补的验证集。

### N7. I-PLATO / GhostCoder (2025) —— 编程教育的动态难度调整 ⚠️ **空白的证明** `[已核验]`

- **完整引用**：Lok Cheung Shum (2025). [I-PLATO / GhostCoder：面向编程游戏的自适应难度与 xAPI 互操作]. UWE（University of the West of England）博士论文，2025 年 3 月。
- **技术要点**：ARCS 动机模型 + 基于动机的情境化设计（Motivational Scenario-Based Design）+ **基于模糊逻辑的动态难度调整（DDA）** + xAPI 互操作。
- **⚠️ 样本量**：两个原型的评估样本分别为 **N = 32** 与 **N = 15**，**合计仅 47 人**。
- **与 LearnFlow 的差异（我们站在哪）**：
  - **这是方向 ⑤ 最重要的发现**：编程教育中做自适应难度调整的**最接近的工作，样本只有 47 人**。
  - 这不是"有个强对手"，而是"**这个方向几乎没人做，且做过的人样本小到无法下结论**"。
  - **这是五个方向中最大的真空。**

### N8. Kodetu —— 积木编程的自适应难度 `[已核验]`

- **完整引用**：Kanellopoulou（University of Deusto）博士论文 —— Kodetu：面向 9–16 岁学习者的**基于模糊规则的难度函数**，用于积木式（block-based）迷宫编程挑战；110 个挑战；自适应 vs 非自适应对比。
- **与 LearnFlow 的差异**：同样是**小样本、单一机构、学位论文级别**的验证。进一步印证了"编程教育自适应难度缺乏大规模证据"这一判断。

## 5.3 研究缺口（4 个）

### G5-1. 编程教育的自适应难度：最大样本仅 N=47 —— **最大真空**

**可验证性**：
- I-PLATO / GhostCoder（2025，UWE 博士论文）：N=32 与 N=15，合计 **47**；
- Kodetu（Deusto 博士论文）：小规模、单一机构；
- 对比：非编程领域的自适应难度 RCT 已达 **10 所学校、5 个月**（Chung et al. 2026）。

**具体缺口**：**在编程教育（CS1 / 算法练习）场景下，"自适应难度排序是否提升学习结果"缺乏任何 adequately powered 的证据。**

**可做的最小实证（关键：不需要真实用户）**：
- 用 **CodeWorkout（65,000+ 提交）** 与 **FalconCode（28,617 次提交）** 做**离线重放评估（offline replay evaluation）**：
  - 把学生的历史提交序列作为"日志策略"产生的数据；
  - 用反事实评估（off-policy evaluation）估计不同难度策略下的累积学习收益；
  - 对照：(a) 固定难度递增；(b) 随机；(c) 独立臂 bandit；(d) **有序结构 bandit**（即方向 ① 的 G1-1，在此数据集上落地）。
- **这一条把方向 ① 与方向 ⑤ 打通**：方向 ① 缺数据，方向 ⑤ 有数据缺方法。**合并后的论文既有方法 novelty 又有数据规模。**

### G5-2. LLM 生成的知识组件 → 难度选择的闭环缺失

**可验证性**：KCGen-KT（arXiv 2502.18632）用 LLM 生成 KC 来做**知识追踪**；检索未发现任何工作把 LLM 生成的 KC 反馈到**难度/题目选择**环节。

**具体缺口**：当前的技术链条是**开环**的：
```
学生作答 → KT 追踪知识状态 → （断开）→ 难度/题目选择
                            ↑
                    LLM 生成的 KC 只用于追踪，不用于决策
```

**可做的最小实证**：把 KC 粒度（粗/细、人工/LLM 生成）作为**自变量**，测量下游难度选择的 regret 差异。**这是一个清晰、可量化、可完成的实验设计。**

### G5-3. 测试级细粒度信号接入难度选择

**可验证性**：TIKTOC（LAK 2025）已证明**测试用例级信号优于总分信号**用于知识追踪。检索未发现任何工作把测试级信号用于**难度选择**。

**具体缺口**：难度引擎目前消费的是"答对/答错"这一**二元、粗粒度**信号。而编程题天然产生**丰富的结构化信号**：
- 哪些测试用例失败（可定位到具体概念缺失）
- 编译器消息类型（语法错误 / 类型错误 / 逻辑错误）
- 提交间隔、修改幅度（edit distance 序列）

**可做的最小实证**：构造三类输入信号（二元正确率 / 测试通过率向量 / 测试通过率 + 编译器消息类别），对比其在难度选择 bandit 中的 regret。**数据来自 CodeWorkout，完全公开。**

### G5-4. 编程教育中"难度"本身的定义与标定缺乏标准

**可验证性**：CodeWorkout 与 FalconCode 都**没有权威的题目难度标注**；现有研究用"通过率"或"首次提交通过率"作为难度的代理。

**具体缺口**：**"一道编程题的难度是什么"** 这一基础问题缺乏共识与标定方法。具体：
- 通过率作为难度代理存在**选择偏差**（能坚持做到该题的学生本身能力分布不同）；
- 不同班级/学期的通过率**不可直接比较**；
- 缺乏**跨数据集可迁移的难度标尺**。

**可做的最小实证**：用 IRT / Rasch 模型在多个编程数据集上拟合题目难度，检验跨数据集的可迁移性。**这是一个"基础设施型"贡献，引用潜力高。**

## 5.4 Novelty 诚实评估

### 已经死了的

| 设想 | 死因 |
|---|---|
| "LLM 在 CS 教育的系统综述" | Raihan et al. (SIGCSE TS 2025) + ACL 2025 综述已占 |
| "代码提交的知识追踪" | TIKTOC (LAK 2025)、KCGen-KT (2025) 已占；Code-DKT、OKT 更早 |
| "我们做了一个编程学习平台" | 学位论文级别的平台已有多个（I-PLATO、Kodetu），且都有动机模型支撑 |

### 还活着的（按推荐度排序）—— **本方向真空最大**

1. **G5-1 编程教育自适应难度的离线重放评估**（★★★★★）—— **有公开大数据（65k 提交）+ 有明确的方法 novelty（有序 bandit）+ 对手样本只有 47。这是最应该立刻动手的论文。**
2. **G5-3 测试级信号接入难度选择**（★★★★★）—— TIKTOC 铺好路没走完，可直接接上；数据现成。
3. **G5-2 KC → 难度闭环**（★★★★）—— 缺口明确，但需要复现 KCGen-KT 的 LLM 生成流程。
4. **G5-4 编程题难度的跨数据集标定**（★★★）—— 基础设施型贡献，引用潜力高，但 novelty 相对温和。

### 关键判断

**方向 ⑤ 应当与方向 ① 合并执行。** 单独看：方向 ① 有方法没数据，方向 ⑤ 有数据没方法。**合并后是一个完整的、可立即执行的、有方法 novelty 且有数据规模的论文。** 这是本报告中**最具操作性的一条建议**。

## 5.5 目标期刊对标

| 期刊 / 会议 | CCF / 索引 | 定位 | 难度 | 周期 | 适配缺口 |
|---|---|---|---|---|---|
| **SIGCSE Technical Symposium (SIGCSE TS)** | CCF 未列；**CS 教育第一顶会** | 计算机教育 | 中—高（录用率约 25–30%） | 投稿到结果约 6 个月 | **G5-1、G5-4（最适配）** |
| **ICER (Int'l Computing Education Research)** | CCF 未列；CS 教育研究顶会 | 计算教育研究 | 高 | 6–8 个月 | G5-1、G5-3 |
| **ACM Transactions on Computing Education (TOCE)** | CCF 未列（新刊）；正在建立声誉 | 计算教育 | 中—高 | 12–18 个月 | G5-1、G5-2（期刊完整版） |
| **Computer Science Education**（期刊） | CCF 未列；SCI/SSCI，CS 教育专门刊 | 计算机教育 | 中—高 | 12–18 个月 | G5-1、G5-3、G5-4 |
| **LAK / EDM** | CCF 未列；学习分析顶会 | 学习分析 | 中—高 | 4–6 个月 | G5-1、G5-3（若强调方法而非教育情境） |
| **IEEE Transactions on Learning Technologies** | CCF 未列；SCI Q1 | 学习技术 | 中—高 | 9–18 个月 | G5-2、G5-3 |

**注意**：CS 教育类顶级载体（SIGCSE TS / ICER / TOCE / Computer Science Education）**均未被 CCF 列表收录**。若项目的硬指标是 CCF-A/B，则方向 ⑤ 的论文需要考虑**投 LAK/EDM 或 IEEE TLT**（同样非 CCF），或者**把方法学部分抽出来投 CCF 收录的期刊**（如 TKDE / TOIS / TKDD —— 对应 G5-1 的 bandit 方法部分；或 IST / JSS —— 对应工程部分）。

**这是团队必须提前做的一个战略取舍**：**CCF 指标与 CS 教育顶会之间存在结构性错位。** 建议采用"**方法论文投 CCF 刊、教育论文投 SIGCSE/TOCE**"的双轨策略。

---

# 第 6 章 跨方向综合：Novelty 矩阵与执行路线图

## 6.1 Novelty 强度 × 可执行性矩阵

以"0 真实用户数据"为当前约束，评估每个缺口的**新颖性**与**当前可执行性**：

| 缺口 | 方向 | Novelty | 当前可执行性 | 需要真实用户？ | 需要跨机构？ | 综合评级 |
|---|---|---|---|---|---|---|
| **G3-2 暗黑模式 vs 防沉迷对立建模** | ③ | ★★★★★ | ★★★★☆ | 否 | 否 | **A：立即执行** |
| **G5-1 编程教育自适应难度离线重放** | ⑤+① | ★★★★★ | ★★★★★ | 否（用 CodeWorkout） | 否 | **A：立即执行** |
| **G4-3 KT 排名小样本稳定性** | ④ | ★★★★★ | ★★★★★ | 否（用 pyKT） | 否 | **A：立即执行** |
| **G3-1 机制实现债** | ③ | ★★★★★ | ★★★☆☆ | 否 | **是（需 ≥3 项目复制）** | **A：立即执行静态分析，复制并行** |
| **G5-3 测试级信号接入难度选择** | ⑤+① | ★★★★☆ | ★★★★★ | 否 | 否 | **A：立即执行** |
| **G1-2 四层耦合稳定性/消融** | ① | ★★★★☆ | ★★★★★ | 否（纯仿真） | 否 | **A：立即执行** |
| **G4-1 未校准 BKT 不可辨识性** | ④+① | ★★★★☆ | ★★★★☆ | 否 | 否 | **A：立即执行** |
| **G4-4 模拟学习者虚假可复现性** | ④ | ★★★★☆ | ★★★☆☆ | 否 | 否 | B：次优先 |
| **G1-5 离线/反事实评估协议** | ① | ★★★★☆ | ★★★★☆ | 否 | 否 | B：次优先（但工程侧应立即埋点） |
| **G2-4 上链必要性判据** | ② | ★★★★☆ | ★★★★☆ | 否 | 否 | B：次优先 |
| **G2-2 轻量锚定量化评估** | ② | ★★★☆☆ | ★★★★☆ | 否 | 否 | B：次优先 |
| **G3-3 因子设计方法论** | ③ | ★★★★☆ | ★★☆☆☆ | 部分 | 否 | C：需理论积累 |
| **G2-1 算法决策审计轨迹** | ② | ★★★☆☆ | ★☆☆☆☆ | 否 | **是（前提不成立）** | **C：降级** |
| **G1-3 心流通道效度检验** | ① | ★★★★☆ | ☆☆☆☆☆ | **是** | 否 | **D：数据就绪后再做** |
| **G3-4 框架效应长期稳健性** | ③ | ★★★★☆ | ☆☆☆☆☆ | **是** | 否 | **D：数据就绪后第一个做** |
| **G2-3 VC 撤销与最小化披露** | ② | ★★★☆☆ | ☆☆☆☆☆ | **是** | **是** | **D：需机构合作** |
| **G5-4 编程题难度跨集标定** | ⑤ | ★★★☆☆ | ★★★★☆ | 否 | 否 | B：可并行 |

## 6.2 三个最锋利的 Novelty 点

### 🥇 Novelty #1：游戏化机制的"实现债"与"暗黑模式冲突"双论文（方向 ③）

**为什么最锋利**：
1. **数据独有**：48/60 零调用、11 个内存容器、17 个未仲裁 nudge 点 —— 这些数字**只有 LearnFlow 有**，任何竞争对手都拿不到，除非他们先建一个同样规模的生产系统然后自曝其短。
2. **有权威挂靠**：Gray et al. (CHI 2018) 的五分类提供了**现成的编码框架**；Sailer et al. (2017, CHB) 提供了**机制-需求映射的对照**；Crespo et al. (2022, IST) 提供了**"机制 ≠ 结果"的同类证据**。
3. **批评性视角天然可信**：**把自己的系统作为反面案例**，比宣称自己的算法更好更经得起审。
4. **有监管顺风**：EU DSA 第 25 条、FTC 2022 报告、OECD 2022 报告把暗黑模式从学术概念变成法律概念（**注：三条监管文件均需自行核实一次文献后方可引用**）。

**一句话定位**：*"我们建了一个 60 机制的游戏化学习系统，然后审计它——发现 48 个机制从未被调用，17 个劝导点与我们的防沉迷目标方向相反。这是行业普遍现象的第一个实证证据。"*

### 🥈 Novelty #2：编程教育自适应难度的离线重放评估（方向 ⑤ + ①）

**为什么锋利**：
1. **真空明确**：编程教育自适应难度的最强对手样本是 **N=47**（I-PLATO 两个原型 32+15）。
2. **数据现成**：CodeWorkout（65,000+ 提交）+ FalconCode（28,617 提交），全部公开。
3. **方法有 novelty**：把**有序/结构化 bandit**（Categorized Bandits / poset dueling bandits）首次用于难度选择 —— 理论上已备，教育上零应用。
4. **回避了与 Chung et al. 2026 的正面竞争**：他们做 RCT 效果量，我们做**离线方法学 + 有序结构建模**，互补而非竞争。

**一句话定位**：*"难度等级 1–10 不是 10 个独立的老虎机臂。我们把有序结构 bandit 首次引入编程教育的难度选择，并在 6.5 万次真实代码提交上用离线重放评估验证——这是该场景下迄今最大规模的难度策略评估（此前最大 N=47）。"*

### 🥉 Novelty #3：KT 模型排名的小样本稳定性审计（方向 ④）

**为什么锋利**：
1. **零数据门槛**：pyKT（21 个模型）+ 9 个公开数据集，全部现成。
2. **结论有普适冲击力**：如果"n=100 无法区分排名前 5 的模型"成立，那么**整个领域的绝大多数小样本研究都不足以支撑其结论**。这类结论会被广泛引用。
3. **自我指涉的正当性**：我们自己也用未校准的 BKT，所以我们可以诚实地把自己作为案例。
4. **时效性强**：pyKT 发表于 2025 年 8 月，窗口期正在打开，**越早越好**。

**一句话定位**：*"pyKT 给出了 21 个知识追踪模型的排名。但我们发现，在 n=100（该领域典型样本量）下，这个排名的 Kendall τ 稳定性是 X —— 意味着多数已发表的小样本 KT 研究无法区分模型优劣。"*

## 6.3 执行路线图（按"0 数据"约束分级）

### 阶段一：立即可做（0 真实数据，3 个月内）

| 任务 | 产出 | 目标载体 |
|---|---|---|
| **T1 埋点**：在难度决策处记录每个难度被选中的**概率分布**（而非仅记录被选中的难度） | 使未来所有日志可做无偏离线评估 | 内部工程（**成本极低，回报极高，今天就能做**） |
| **T2** 53 个游戏化机制的调用图静态分析 + 零调用根因分类 | 实现债分类学 | MSR / IST short paper |
| **T3** 17 个 nudge 点的 Gray 五分类双评审员编码 + 与 LAI 方向的余弦冲突检测 | 暗黑模式审计报告 | CHI / Computers in Human Behavior |
| **T4** 四层难度决策器的仿真稳定性分析（振荡幅度/收敛时滞/稳态误差）+ 逐层消融 | 病理行为图谱 | IEEE TLT / IJAIED / UMUAI |
| **T5** 未校准 BKT 的可辨识性分析 → 下游难度决策的敏感性 | 不可复现性证明 | LAK / EDM / JEDM |

### 阶段二：公开数据上的完整研究（3–9 个月）

| 任务 | 产出 | 目标载体 |
|---|---|---|
| **T6** pyKT 重跑 + 小样本 bootstrap → 模型排名稳定性曲线 + 最小可分辨样本量 | 领域级审计结论 | **LAK / EDM（抢首发）** → Computers & Education 期刊版 |
| **T7** CodeWorkout/FalconCode 上的有序 bandit 离线重放评估 | 最大规模编程难度策略评估 | SIGCSE TS / ICER / TOCE；方法部分抽投 TKDE/TKDD |
| **T8** 测试级信号（TIKTOC 式）接入难度选择 | 信号粒度消融 | LAK / EDM / IEEE TLT |
| **T9** 跨 ≥3 个开源游戏化学习系统的实现债复制研究 | 普遍性证据 | **EMSE / IST（完整版）** |

### 阶段三：需真实用户（数据就绪后）

| 任务 | 产出 | 目标载体 |
|---|---|---|
| **T10** 三臂框架效应实验（完整机制 / 仅框架 / 无游戏化），≥4 周 | 长期框架效应检验 | CSCW / Computers in Human Behavior / Computers & Education |
| **T11** 心流通道代理变量的效度校准（系统判定 vs 自评一致性） | 心流构造效度 | CHI / Computers in Human Behavior |
| **T12** 跨平台机制数量的剂量-反应元分析 | 挑衅性结论 | 高影响力综合刊 |

### 明确建议降级 / 暂缓

| 任务 | 理由 |
|---|---|
| 区块链教育证书/学分互认 | EBSI / ESSA / 浙江省政策已占据，第 N+1 个无意义 |
| 区块链"架构提案"类论文 | 领域已有 150 个模型，其中 26 个纯提案；纯架构论文无法发表 |
| 算法决策审计轨迹（G2-1） | 前提是"跨机构多方互不信任"，LearnFlow 当前是单机构零用户，前提不成立 |
| 任何"我们提出新分类学" | 分类学已饱和 |
| 任何"我们做了个平台" | 平台论文在 CS 教育领域已是学位论文级别，不构成博士论文贡献 |

## 6.4 三条必须写进论文的"主动防御"段落

学术写作中，**主动暴露弱点比被审稿人抓到好得多**。建议在相关论文中直接写入以下三段：

**① 关于 85% 规则的外推（方向 ①）**
> Wilson 等（2019）的 85% 最优错误率结论是在人工神经网络与生物可解释的感知学习模型上推导与验证的，作者明确限定其适用于二元分类任务，并指出其最可能适用于感知学习。本研究将其作为一个**启发式目标**而非已确立的人类学习规律，并通过逐层消融检验该目标对系统的实际贡献（见 §X）。我们**不主张**该规则在人类复杂认知学习上成立。

**② 关于与 Chung 等（2026）的关系（方向 ①）**
> 与 Chung 等（2026）在 10 所高中完成的自适应难度 RCT 相比，本研究**不依赖学生与 LLM 之间的自然语言交互信号**，考察的是仅凭结构化行为信号可达到的适应水平；此外我们提供的是**机制层面的消融与稳定性分析**，而非端到端效果量。两项研究是互补关系。我们也注意到，Chung 等的因果识别强度（RCT）高于本研究的离线评估，这是本研究的明确局限。

**③ 关于"blockchain for blockchain's sake"（方向 ②，若坚持做）**
> 我们充分意识到区块链在教育领域存在大量无必要性论证的提案（Choudhary 等 2025 统计的 150 个模型中，124 个为原型、26 个仅为提案）。因此本研究**不提出新的教育区块链架构**，而是提出一个**可操作的上链必要性判据**，并在 §X 中给出该判据应用于 LearnFlow 的结论——**我们的结论是：在单机构部署下，LearnFlow 不需要上链。**

（第三段若真这么写，反而会大幅提升论文的可信度与发表概率。）

---

# 附录 A：待核实清单

**⚠️ 以下条目未经一次文献核实，禁止直接写入论文引用位。使用前列出的核实路径自行核验。**

## A.1 高风险（广泛使用但来源存疑）

| # | 条目 | 流传的说法 | 问题 | 核实路径 |
|---|---|---|---|---|
| A1 | Gartner 2024 报告 | "75% 的企业区块链项目用传统数据库/DLT 就够了" | 仅见行业媒体与内容农场转述，**未定位到 Gartner 一次报告** | 去 gartner.com 检索原文报告编号；或改用 N3（Labaran Isiaku & Adalier 2025, *On the Horizon*）作为可引用替代 |
| A2 | Roubini 引用的研究 | "43 个区块链开发/非营利实验，0 成功" | 仅见访谈二次转述，**未定位到原始研究** | **建议直接放弃引用**。改用 Choudhary 等 2025 的 124/150 原型率（已同行评议） |
| A3 | Mathur et al. (2019) 暗黑模式审计 | 爬取 11,000 个购物网站，1,254 个上有 1,818 个暗黑模式实例（约 11%） | 命中二级转述，未定位论文 PDF | 检索 "Mathur dark patterns 11000 shopping websites"；查 Princeton CITP 或 ACM DL |
| A4 | OECD (2022) Dark Commercial Patterns | OECD 发布的暗黑商业模式报告 | 命中二级转述 | 去 oecd.org 官方出版物库检索 |
| A5 | FTC (2022) Bringing Dark Patterns to Light | FTC 员工报告，引用 Brignull/Gray/Mathur | 命中二级转述 | 去 ftc.gov 检索官方 PDF |
| A6 | EU Digital Services Act 第 25 条 | 禁止超大型在线平台使用暗黑模式 | 命中二级转述 | 查 EUR-Lex 官方文本（eur-lex.europa.eu），**条文号需核实** |

## A.2 中风险（载体确认但细节待补）

| # | 条目 | 已确认 | 待补 | 核实路径 |
|---|---|---|---|---|
| A7 | Liu et al. (2025) pyKT | DOI 10.1109/TKDE.2025.3552759；IEEE TKDE 37(8):4512-4536 | **作者全名** | IEEE Xplore 论文页 |
| A8 | Abdul Razzaq et al. (2026) | DOI 10.1049/sfw2/5556408；*IET Software* 2026 | **作者全名、卷期页码** | IET Digital Library（注意：DOI 中的 "sfw2" 前缀较异常，**建议复核 DOI 是否准确**） |
| A9 | Bandits Dueling on Partially Ordered Sets (NeurIPS 2017) | 会议、年份、Paper ID 1279、算法名 UnchainedBandits | **作者列表** | NeurIPS Proceedings 官方页 |
| A10 | KCGen-KT (2025) | arXiv:2502.18632v4；数据规模 | **是否已正式发表、作者列表、载体** | arXiv 摘要页查看 journal-ref / comments 字段 |
| A11 | LLM in Programming Education Survey (ACL 2025) | ACL Anthology 2025.hcinlp-1.21；三个焦点与篇数 | **作者列表、完整标题** | ACL Anthology 页面 |
| A12 | Hepp et al. (2018) OriginStamp | *it - Information Technology*, 2018；机制已由官方文档核实 | **卷期页码** | De Gruyter 期刊页 |
| A13 | Kitto et al. (2020) xAPI 语义互操作 | UTS, CLA toolkit report 2020 | **完整标题、作者全名、载体类型** | UTS 机构库 |
| A14 | Mangaroska et al. (2019) | 综述中无一研究使用 Caliper | **完整标题、载体、卷期** | Google Scholar / ACM DL（常见载体为 IEEE TLT 或类似） |
| A15 | Mazarakis & Bräuer | N=505、四机制、组合不叠加 | **年份、载体（会议/期刊）、合著者全名** | Kiel University 机构库 / Google Scholar |
| A16 | 心流 Sensors 论文 | *Sensors* 26(1):38 (2026), MDPI | **作者列表** | MDPI 论文页（已见重定向 URL，需确认完整引用） |
| A17 | I-PLATO / GhostCoder (UWE 2025) | 博士论文，2025-03，N=32/15，ARCS+模糊逻辑 DDA+xAPI | **作者全名、论文标题全称、DOI/机构库编号** | UWE Research Repository |
| A18 | Kodetu (Deusto) | 博士论文，模糊规则难度函数，110 挑战，9–16 岁 | **作者全名、年份、论文标题全称** | University of Deusto 机构库 |
| A19 | UMAP 2025 "100 students" 论文 | 明确自述因算力限制抽样 100 名学生 | **完整标题、作者、页码** | ACM DL UMAP 2025 proceedings |
| A20 | Preprints.org 202510.1845 | 载体与手稿编号确认（82.1% / 56.0% / 3.6% / 90.5% 四个数字的来源） | **同行评议状态；原始引用 [77][78][44][45][56][30] 的一次文献** | preprints.org 手稿页 → 参考文献列表 → 逐条回溯 |

## A.3 制度/政策来源（作为背景可引用，作为学术引用需谨慎）

| # | 条目 | 说明 |
|---|---|---|
| A21 | 浙江省终身学习微证书 / 学分银行（2025） | 来源为教育部及中国网相关报道（2025-12）。用于说明"区块链+学分互认"在中文语境已被政策层面占据。**作为背景陈述可引用官方报道；作为学术引用需找政策原文文号** |
| A22 | EBSI / ESSA / NOO Ultra / TRUSTCHAIN / FRI Academy | 已由 Jušić 等（EDULEARN25, DOI 10.21125/edulearn.2025.1342）综述，**引用时引该综述即可**，不必逐一回溯各倡议 |

## A.4 明确不得引用

- 任何由内容农场、SEO 博客、生成式内容站提供的"研究数据"；
- 任何只以"据报道""据统计"形式出现而无出处的数字；
- 本报告中所有标注 `[待核实]` 且未出现在上述清单之外的、由团队自行补充但未经检索核实的条目。

---

# 附录 B：检索执行日志

| 序号 | 检索目标 | 结果 | 关键产出 |
|---|---|---|---|
| S1 | Wilson 85% rule Nature Communications 2019 | 命中原文页 | **确认** DOI 10.1038/s41467-019-12552-4；确认作者本人限定"二元分类/最可能适用于感知学习" |
| S2 | pyKT IEEE TKDE 2025 | 命中 | **确认** DOI 10.1109/TKDE.2025.3552759；9 数据集 / 21 模型 |
| S3 | Knowledge Tracing Survey ACM CSUR | 命中 | **确认** DOI 10.1145/3569576；独立确认数据质量问题清单 |
| S4 | ordinal/structured bandit | 命中 | **确认** Categorized Bandits (Jedor/Louëdec/Perchet)；poset dueling bandits (NeurIPS 2017)；Linked Bandits；Decoy Bandits |
| S5 | unimodal bandit ordered actions education | **偏题** | 结果为主题无关的通识 RL 内容，**已弃用**；改用 S4 结果 |
| S6 | flow theory computational formalization | 命中 | **确认** *Sensors* 26(1):38 (2026)；三条批判事实（通道预测不符、r=0.206、线性化简化） |
| S7 | blockchain education systematic review | 命中 | **确认** Choudhary 等 2025；150 模型 / 124 原型 / 26 提案 |
| S8 | blockchain education challenges | 命中 | **确认** Abdul Razzaq 等 2026 (IET Software)；Labaran Isiaku & Adalier 2025 (*On the Horizon*) |
| S9 | verifiable credentials micro-credential education | 命中 | **确认** Jušić 等 (EDULEARN25)；浙江省政策背景 |
| S10 | blockchain criticism / overhype | 部分命中 | **Gartner 75% 与 Roubini 43 实验未定位一次文献 → 降级至附录 A** |
| S11 | OriginStamp Merkle timestamping | 命中 | **确认** 机制细节（本地 SHA-256 → 批收集 → 排序 → 平衡 Merkle 树 → BTC 地址编码根） |
| S12 | gamification meta-analysis | 命中 | **确认** Sailer & Homner 2020 三级效应量 |
| S13 | gamification ablation specific elements | 命中 | **确认** Sailer 等 2017 (CHB 69:371-380, N=419)；Mazarakis & Bräuer (N=505)；Lieberoth 2015 (N=90) |
| S14 | dark patterns / FOMO / ethical criticism | 命中 | **确认** Gray 等 2018 (CHI, DOI 10.1145/3173574.3174108)；监管文件降级至附录 A |
| S15 | gamification technical debt software engineering | 命中 | **确认** Crespo 等 2022 (IST 150:106946)；**重要反向结论：竞赛+排行榜对技术债指标无显著差异** |
| S16 | EDM reproducibility data quality | 命中 | **确认** Preprints.org 202510.1845（预印本，须谨慎）；四个数字的原始出处 |
| S17 | xAPI / Caliper standards | 命中 | **确认** IEEE 9274.1.1-2023；SoLAR 2020 立场文件；Kitto 2020；Mangaroska 2019 |
| S18 | LLM programming education survey | 命中 | **确认** Raihan 等 (SIGCSE TS 2025, arXiv 2410.16349)；ACL 2025.hcinlp-1.21 |
| S19 | CodeWorkout / code knowledge tracing | 命中 | **确认** TIKTOC (LAK 2025, DOI 10.1145/3706468.3706500)；KCGen-KT；CodeWorkout 规格；FalconCode |
| S20 | adaptive difficulty programming education | 命中 | **确认** I-PLATO/GhostCoder (N=32/15，**最大样本仅 47**)；Kodetu |
| S21 | Sailer et al. 2017 exact venue | 命中 | **确认** CHB 69:371-380, DOI 10.1016/j.chb.2016.12.033, N=419, 平均年龄 22.39 |
| S22 | dark patterns Gray CHI 2018 | 命中 | **确认** Paper 534, 1–14, DOI 10.1145/3173574.3174108, 118 实例 / 5 类 |
| S23 | TIKTOC full citation | 命中 | **确认** Duan/Fernandez/Hicks/Lan, LAK 2025, 246 学生 / 3714 提交 / 305 测试用例 / 17 题 |
| S24 | Chung et al. LLM tutor RCT | 命中 | **⚠️ 确认高危先行工作**：arXiv:2608.16907，10 校 / 5 月 / RCT / 0.15 SD；**工作论文，未正式发表** |
| S25 | Crespo technical debt gamification | 命中 | **确认** IST 150:106946；三个处理组设计；游戏化无显著效果 |
| S26 | Categorized Bandits authorship | 命中 | **确认** Matthieu Jedor, Jonathan Louëdec, Vianney Perchet |
| S27 | Bandits Dueling on Partially Ordered Sets | 命中 | **确认** NeurIPS 2017, Paper ID 1279, UnchainedBandits；**同时确认 NeurIPS 审稿意见指出的局限** |

**检索统计**：27 次检索，其中 1 次偏题弃用；确认可引用条目 27 项；降级至待核实清单 22 项。

---

## 文档结束

**维护建议**：
1. `references.bib` 与本文档应同步维护；凡新增引用，先核实再加入 bib。
2. 附录 A 的条目在核实后，应从附录 A 移出、加入 bib，并在附录 A 标注"已于 YYYY-MM-DD 核实，见 bib"。
3. 建议每季度重跑一次第 0 章的检索词表（尤其方向 ① 与 ⑤，二者变化最快）。
