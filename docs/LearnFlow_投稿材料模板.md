# LearnFlow 投稿材料模板（按目标期刊的强制要求）

> 用途：把各目标 venue 的**强制前置材料**做成可直接套用的模板，避免因缺声明、
> 超字数等非学术原因被 desk reject。
>
> 适用范围：P1–P5 核心论文 + P7 软件论文。venue 选择见
> `docs/LearnFlow_期刊论文拆分方案.md`。
>
> ⚠️ **时效性**：期刊要求会变。本模板基于投稿前的一次核查，**投稿前必须复核**
> 目标期刊的最新 Guide for Authors。凡本文件与期刊官网冲突，以期刊官网为准。

---

## 〇、本研究的特殊披露义务（先读）

本项目是 **AI 辅助研究**，且研究对象是**未成年人**。这两点使以下声明**不可省略**：

| 声明 | 为什么本项目必须写 |
|---|---|
| **生成式 AI 使用声明** | 研究过程使用了 AI 辅助（代码生成、文献梳理）。Elsevier / Springer / IEEE 均已要求披露生成式 AI 的使用范围。**隐瞒的后果远大于披露** |
| **伦理与知情同意** | 面向 K12 未成年人；若涉及真实被试，须有伦理审查批号 |
| **数据可用性** | 研究数据含未成年人心理自陈数据，**不能公开原始数据**，须说明受控获取方式 |
| **测量效度局限** | 自陈量表为本项目自编、未经信效度检验（见 `LearnFlow_成瘾化研究_测量框架.md` §3.2） |

---

## 一、通用声明模板（可直接复制）

### 1.1 Declaration of Competing Interest / Competing Interests

> **适用**：Elsevier 全系（Information Sciences / IPM / Applied Soft Computing）、
> Springer 全系（KAIS / UMUAI / EAIT）、IEEE 全系

```
Declaration of Competing Interest

The authors declare that they have no known competing financial interests or
personal relationships that could have appeared to influence the work reported
in this paper.
```

若确有利益关系，须如实列出。**不得**留空或写「None」了事——Elsevier 的
Declaration of Competing Interest 是**逐稿强制**的独立声明项。

### 1.2 Data Availability Statement

> **适用**：Elsevier 全系（强制）、Springer 全系（强制）、IEEE（鼓励）

本项目**不能**使用「Data available on request」这种含糊表述——审稿人对该措辞的
容忍度正在快速下降。适用版本：

```
Data Availability Statement

The source code of the LearnFlow platform, together with all reproducibility
scripts (mechanism counting, asset-number verification, mechanism landing scan)
and the machine-generated verification artifacts they produce, is openly
available at https://github.com/korose523/learnflow under the MIT licence.
An archived, citable snapshot is deposited on Zenodo (DOI: <TO_BE_INSERTED>).

The empirical datasets used in this study are publicly available:
<LIST PUBLIC DATASETS WITH CITATIONS>.

Raw participant-level data CANNOT be shared. The platform collects
self-reported psychological and behavioural data from minors (sleep, social
and self-control items). Distribution is restricted by the ethics approval
and by data-minimisation obligations; access may be granted to researchers
who obtain an independent ethics approval, via a controlled request to the
corresponding author.
```

**投稿前必须做的两件事**：
1. 把 `<TO_BE_INSERTED>` 换成真实 Zenodo DOI（见 §四）；
2. 把 `<LIST PUBLIC DATASETS ...>` 换成真实数据集与引文；**若本研究未使用任何公开数据集，
   必须删掉该句而不是留占位符**。

### 1.3 CRediT Authorship Contribution Statement

> **适用**：Elsevier 全系（**强制**）

单作者版本：

```
CRediT Authorship Contribution Statement

<AUTHOR NAME>: Conceptualization, Methodology, Software, Validation,
Formal analysis, Investigation, Data curation, Writing – original draft,
Writing – review & editing, Visualization, Project administration.
```

多作者时必须逐人列出，且**每个作者至少承担一项**。CRediT 术语须使用官方 14 项
标准词（Conceptualization / Methodology / Software / Validation / Formal analysis /
Investigation / Resources / Data curation / Writing – original draft /
Writing – review & editing / Visualization / Supervision / Project administration /
Funding acquisition）。

### 1.4 Ethics Approval and Informed Consent

```
Ethics Approval and Informed Consent

This study involved human participants who are minors (K12 students).
The study protocol was approved by <INSTITUTION> Institutional Review Board
(approval no. <IRB_NUMBER>, date <YYYY-MM-DD>).

Informed consent was obtained from the legal guardians of all participating
minors; assent was additionally obtained from the participants themselves.
The self-report instrument module records research-consent status per
submission; for minor participants, consent granted by any party other than
a registered guardian account is treated as invalid by the platform's
consent-resolution logic.

No participant-level data are publicly released (see Data Availability
Statement).
```

⚠️ **若尚未取得伦理批件**：不要伪造批号。此时应改为「本研究使用**仿真被试**
（in-silico simulation，seed 与配置见 artifact）与公开数据集，未采集真实人类被试数据」，
并**删除**上述知情同意段落。用仿真数据本身是合法的，伪造批件不是。

### 1.5 Generative AI Usage Disclosure

```
Generative AI Usage Disclosure

The authors used generative AI tools to assist with <SPECIFIC SCOPE: e.g.
code scaffolding, refactoring suggestions, and literature organisation>.
The AI tools were not used to generate research hypotheses, to fabricate
data, or to produce results. All AI-assisted output was reviewed, verified
and, where necessary, corrected by the authors, who take full responsibility
for the entire content of this manuscript.

To support auditability, all headline numerical claims in this manuscript are
recomputed from source by scripts contained in the published artifact; the
corresponding verification command and its machine-readable output are
identified for every reported count.
```

这一点是本项目的**相对优势**：大多数被质疑「AI 生成」的稿件无法自证，
而本 artifact 的数字可被机器复算。**不要**把这句话写成泛泛的免责声明。

---

## 二、分出版商要求的差异对照

| 项目 | Elsevier（Information Sciences / IPM / ASOC） | Springer（KAIS / UMUAI / EAIT） | IEEE（TLT / TKDE / THMS） | ACM（TOCHI / TOIS） |
|---|---|---|---|---|
| **摘要字数** | **≤200 词**（Information Sciences） | 通常 ≤250 词 | **150–250 词**（TLT） | 通常 ≤250 词 |
| **Highlights** | **必填：3–5 条，每条 ≤85 字符（含空格）** | 不要求 | 不要求 | 不要求 |
| **Graphical Abstract** | 可选（部分刊推荐） | 可选 | 不要求 | 可选 |
| **Index Terms / Keywords** | 关键词 4–6 个 | 关键词 4–6 个 | **Index Terms 3–6 个**（IEEE 系强制，用 IEEE Thesaurus 术语） | CCS Concepts |
| **Competing Interest** | **强制** | **强制** | 强制 | 强制 |
| **Data Availability** | **强制** | **强制**（Springer 全刊） | 鼓励 | ACM 有独立政策 |
| **CRediT** | **强制** | 鼓励 | 不要求 | 不要求 |
| **生成式 AI 声明** | **强制**（在 Methods 或独立声明） | **强制** | **强制** | **强制** |
| **模板** | `elsarticle` | Springer Nature LaTeX | `IEEEtran`（双栏） | `acmart` |
| **评审方式** | 单盲（Information Sciences） | 单盲/双盲视刊 | 单盲 | 双盲（TOCHI） |
| **重投前核对** | Guide for Authors | Submission guidelines | Author Center | acmart 说明 |

---

## 三、Highlights 模板（Elsevier 专用，3–5 条 × ≤85 字符）

> **硬约束**：每条**含空格不超过 85 个字符**。超长会在投稿系统被拒或自动截断。
> 中文字符不计入该限制（Highlights 须以英文提交）。下列字符数需在投稿前用工具复核。

```
Highlights

• Five-dimension learning-addiction index with explicit measurement coverage.
• Self-report instruments cover the 35% of index weight logs cannot observe.
• Unmeasured dimensions are excluded from weighting, never scored as healthy.
• Every headline count is machine-recomputable from the released artifact.
• Dual-source design separates what learners do from how they experience it.
```

**自检**（投稿前逐条跑）：

```bash
python - <<'PY'
lines = [
 "Five-dimension learning-addiction index with explicit measurement coverage.",
 "Self-report instruments cover the 35% of index weight logs cannot observe.",
 "Unmeasured dimensions are excluded from weighting, never scored as healthy.",
 "Every headline count is machine-recomputable from the released artifact.",
 "Dual-source design separates what learners do from how they experience it.",
]
assert 3 <= len(lines) <= 5, f"条数须 3–5，当前 {len(lines)}"
for s in lines:
    assert len(s) <= 85, f"超长 {len(s)}: {s}"
print(f"OK: {len(lines)} 条，最长 {max(len(s) for s in lines)} 字符")
PY
```

**按主题替换的备选条目**（按论文分别选用，勿超出总条数上限）：

| 论文 | 建议 Highlights（已控制在 ≤85 字符） |
|---|---|
| P1 难度量纲 | `A common scale makes heterogeneous difficulty measures comparable.` |
| P2 85% 规则 | `The 85% success-rate rule is re-tested for external validity.` |
| P3 有序动作 Bandit | `Ordered-action bandits formalise the flow channel as a constraint.` |
| P4 干预冲突 | `Conflicting gamification interventions are arbitrated, not merged.` |
| P5 LLM 标注 | `Reliability boundaries of LLM-based difficulty annotation are mapped.` |

---

## 四、Index Terms 模板（IEEE 专用）

> **要求**：3–6 个，须取自 **IEEE Thesaurus** 的受控词表（自由词会被要求修改），
> 按字母序排列。

```
Index Terms—Adaptive learning, educational data mining, gamification,
human factors, psychological measurement, user modelling
```

（6 项，字母序，均为 IEEE Thesaurus 常用受控词。）

---

## 五、摘要字数自检（各刊口径不同，必须逐刊核对）

```bash
# 把摘要存成 abstract.txt（英文，纯文本）后运行
python - <<'PY'
import io, re
text = io.open('abstract.txt', encoding='utf-8').read().strip()
words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-\.]*", text))
print(f"词数 = {words}")
for venue, limit in [("Information Sciences", 200), ("IPM", 200),
                     ("IEEE TLT (min)", 150), ("IEEE TLT (max)", 250),
                     ("Springer KAIS", 250), ("UMUAI", 250)]:
    ok = "OK " if words <= limit else "超出"
    print(f"  [{ok}] {venue}: 上限 {limit}")
PY
```

> **注意**：Information Sciences 的 200 词上限比 Springer 的 250 更紧。
> 若一篇稿子同时投两个刊，**以更紧的口径写作**，避免改投时重写摘要。

---

## 六、投稿前检查清单

### 每篇论文都适用

- [ ] 摘要词数符合目标刊上限（§五）
- [ ] 关键词 / Index Terms 数量与词表合规（§二、§四）
- [ ] Declaration of Competing Interest 已写（§1.1）
- [ ] Data Availability Statement 已写，且**无 `on request` 含糊表述**（§1.2）
- [ ] 生成式 AI 使用声明已写，且**具体到使用范围**（§1.5）
- [ ] 所有头部数字与 artifact 的复算结果一致：
      `python scripts/verify_asset_numbers.py --doc-check` 退出码为 0
- [ ] 机制计数一律 **54**，无 76 / 69 / 60 / 53 的当前态表述
- [ ] 测量局限已逐条声明（自编量表未验证、社会赞许性偏差、代理指标、未测维度）
- [ ] 引用的每个 BibTeX key 都在 `docs/references.bib` 中存在

### Elsevier 额外

- [ ] Highlights 3–5 条，每条 ≤85 字符（§三自检脚本通过）
- [ ] CRediT 声明逐作者列出（§1.3）
- [ ] 使用 `elsarticle` 模板

### Springer 额外

- [ ] Competing Interests 与 Data Availability 均在**独立章节**（Springer 全刊强制）
- [ ] 使用 Springer Nature LaTeX 模板

### IEEE 额外

- [ ] Index Terms 3–6 个，取自 IEEE Thesaurus（§四）
- [ ] 参考文献格式严格符合 IEEE 样式（格式不合可能被行政退稿）
- [ ] 双栏 `IEEEtran` 模板；TLT 常规论文不超过页数上限
- [ ] **所有作者持 ORCID**（IEEE 全系要求）

### 涉及人类被试的额外

- [ ] 伦理审查批号已填（**未取得则改为仿真数据的表述，不得伪造**）
- [ ] 监护人知情同意与参与者本人同意均已说明（§1.4）

### 软件论文（P7）额外

- [ ] 仓库具备 `LICENSE`（MIT，已就位）、根 `README.md`、`CONTRIBUTING.md`、`CITATION.cff`
- [ ] Zenodo 归档已获得 DOI，并回填至 §1.2
- [ ] `CITATION.cff` 的作者信息已填为真实署名（非占位）

---

## 七、投稿顺序建议（与论文组合方案一致）

| 序 | 论文 | 目标 | 前置依赖 |
|---|---|---|---|
| 1 | P2 85% 规则外部效度 | KAIS | 无需额外前置；本文数字门禁通过即可投 |
| 2 | P4 干预冲突仲裁 | UMUAI | 需先有 P1 的难度量纲定义 |
| 3 | P1 难度量纲可公度性 | KAIS | — |
| 4 | P3 有序动作 Bandit | Information Sciences（可先投会议版） | — |
| 5 | P5 LLM 标注边界 | IEEE TLT | IEEE 需 **ORCID** |
| — | P7 系统 artifact | Zenodo DOI 先行；JOSS 待公开开发史满 6 个月 | 见论文组合方案 §P7 |
| — | P6 区块链 | **建议终止** | — |

> **JOSS 资格提醒**（已核实）：JOSS 的预筛门槛要求仓库有 **6 个月以上**的公开开发史、
> 有 release/tag、且非「单人无社区参与」。本仓库此前为单作者、提交高度集中在数日内，
> **当前不满足**，故 P7 的第一步是 Zenodo 归档（免费 DOI），而非直接投 JOSS。
