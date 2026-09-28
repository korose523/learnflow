# 目标期刊 AI 使用披露政策对照表（投稿前合规）

> 生成时间：2026-09-22（续会话 8 · I 任务）
> **2026-09-29 复核**：`docs/` 下现已出版**四篇**完整稿（`M1_难度可公度性与最优错误率_完整稿.md`、`M2_多干预并存学习系统的冲突结构审计_完整稿.md`、`M3_有序难度决策与大模型先验边界_完整稿.md`、`M4_信度结构化组合难度估计_完整稿.md`），本表相应扩展至四篇；M4 的目标期刊依据其文首「目标期刊」段。
> 政策核验日期：2026-09-22（各出版方/学会官网最新版，URL 见各条）
> 用途：为 M1 / M2 / M3 / **M4** 四篇投稿锁定**目标期刊**的 AI 使用披露要求；投稿前须再次复核官网最新版（出版方 AI 政策更新频繁）
> 关联：待办 §3-I；M3 稿 L15「投稿前 AIGC 合规提示」；M3 稿 L633「作者与角色」要求「在致谢/方法中列表说明工具使用（含本文所用的 LLM 标注流水线）」
> 纪律：本表仅据**官方政策原文**整理，未虚构任何披露要求；政策若有更新以官网为准。

---

## 0. 目标期刊清单（英文 Scopus 第一顺位 · 毕业口径）

四篇完整稿的并集（毕业口径 = 英文 Scopus 收录刊）：

| 期刊 | 出版方 / 学会 | 归属稿 | 政策依据 |
|---|---|---|---|
| *IEEE Transactions on Learning Technologies* (TLT) | IEEE | M1、M3、**M4** | IEEE Editorial Style Manual + IEEE PSPB《Principles of Ethical Use of AI in Publishing》 |
| *International Journal of Artificial Intelligence in Education* (IJAIED) | Springer | M1、M3、**M4** | Springer Nature 投稿指南（LLM 披露政策） |
| *Journal of Educational Data Mining* (JEDM) | Int. Educational Data Mining Society (IEDMS) | M1 | JEDM《Publication Ethics and Malpractice Statement》（遵循 ACM 政策） |
| *Journal of Systems and Software* (JSS) | Elsevier | M2 | Elsevier《Generative AI policies for journals》 |
| *Empirical Software Engineering* (EMSE) | Springer | M2 | Springer Nature 投稿指南（LLM 披露政策） |
| *Information and Software Technology* (IST) | Elsevier | M2 | Elsevier《Generative AI policies for journals》 |

> **M4 的归属依据**（2026-09-29）：`M4_信度结构化组合难度估计_完整稿.md` 文首「目标期刊」段原文为「拟投 *IEEE Transactions on Learning Technologies* 或 *International Journal of Artificial Intelligence in Education*；备选中文学术期刊（不作毕业口径）同 M3」。故 M4 落在已覆盖的 IEEE 与 Springer 两家政策内，**不引入新的出版方**。
> 第二顺位（**不作毕业口径**，仅英文第一顺位被拒且时间不可接受时启用）：
> - M1：《开放教育研究》（CSSCI/北大核心，免版面费与审稿费）、《数据分析与知识发现》（CSSCI/EI）
> - 中文刊 AI 政策须在各自投稿时单独核查，本表不预先覆盖（低优先，见 §5）。

---

## 1. 四家出版方 / 学会 AI 政策逐条（官方原文要点）

### 1.1 IEEE（覆盖 TLT）

**来源**：IEEE Editorial Style Manual（http://ieeeauthorcenter.ieee.org/wp-content/uploads/IEEE_Style_Manual.pdf）；IEEE PSPB Operations Manual §5–6《Principles of Ethical Use of Artificial Intelligence in Publishing》。核验 2026-09-22。

- **披露位置**：**Acknowledgment 段**（置于文末、References 之前；标题拼写单数 `ACKNOWLEDGMENT`，无 "e"）。
- **必备要素**（官方原文）：
  1. 指明所用 **AI 系统名称**；
  2. 指明使用了 AI 生成内容的**具体章节**；
  3. 附**简要说明**：AI 系统在何种**层级（level）**上被用于生成该内容。
- **覆盖范围**：文本、图（figures）、图像（images）、代码（code）均属须披露范围。
- **编辑 / 语法增强**：「使用 AI 进行编辑与语法增强是常见做法，原则上不在上述政策意图之内；此情形下披露为**推荐（recommended）而非强制**」。
- **图注**：AI 生成的图须在图注标明 `Graphic(s) created using AI-generation`，图像署名见 Acknowledgment。
- **AI 署名**：**禁止**。 authorship 须满足 IEEE 三准则（显著智力贡献 + 起草/修订 + 批准终版），AI 无法满足。
- **审稿人约束**：**禁用 AI 起草 / 生成评审意见**（在审稿件属保密文件，审稿人被选中凭其专业判断而非外包判断）。

### 1.2 Springer Nature（覆盖 IJAIED、EMSE）

**来源**：Springer 各刊投稿指南（如 springer.com/journal/11633、/44154 的 Submission guidelines「Large Language Models」段）。核验 2026-09-22。

- **披露位置**：**Methods 段**（若无 Methods 段，置于「合适的替代部分」）。
- **必备要素**：记录 LLM（如 ChatGPT）或其他 AI 工具的使用。
- **「AI assisted copy editing」豁免**：用于**可读性、风格、语法/拼写/标点/语气**的 AI 辅助改写**无需声明**；定义明确为「对人类生成文本的可读性与风格改进，不含生成式编辑工作或自主内容创作」。
- **生成式 AI 图像**：须遵守 Springer 生成式 AI 图像政策（默认**禁止**用生成式 AI 制造/篡改科学图像）。
- **AI 署名**：**禁止**（LLM 不满足 authorship 标准，署名即承担无法适用于 AI 的责任）。
- **责任**：所有情形下须有**人类对终版文本负责**，且作者同意编辑反映其原意。
- **审稿人约束**：投稿指南未统一授权审稿人用 AI；各刊依 COPE/具体政策，谨慎起见默认不将 AI 用于评审判断。

### 1.3 Elsevier（覆盖 JSS、IST）

**来源**：Elsevier《Generative AI policies for journals》（https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals）。核验 2026-09-22。

- **披露位置**：**独立 AI 声明段**，提交时即纳入稿件，将出现在发表物中；段标题 `Declaration of generative AI and AI-assisted technologies in the manuscript preparation process`，置于 **References 之前**。
- **必备要素（官方模板）**：
  > During the preparation of this work, the author(s) used **[NAME OF TOOL / SERVICE]** in order to **[REASON]**. After using this tool/service, the author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the published article.
  - 须记录：**工具名**、**用途（purpose）**、**监督程度（extent of oversight）**。
- **基础校对豁免**：基本语法/拼写/标点检查**无需声明**；但当 AI 对**句子结构或文本组织做实质性改动**时须披露。
- **研究过程中的 AI**（非写作过程）：须在 **Methods 段**详述，不归入上述声明。
- **生成式 AI 图像**：**禁止**（须确保 AI 生成图像的准确与原创并适当署名）。
- **AI 署名**：**禁止**（不得列为作者或引用为作者）。
- **人类监督**：AI 工具须始终在人类监督下使用，作者对所写内容负责并须核实 AI 输出（含文献，AI 生成参考文献可能错误/虚构）。
- **审稿人约束**：编辑/审稿人**不得**将未发表稿件上传至生成式 AI 工具（保密）；可用于改进评审报告结构/语言的辅助角色（依具体刊政策）。

### 1.4 JEDM（IEDMS 学会刊）

**来源**：JEDM / IEDMS《Publication Ethics and Malpractice Statement》（https://educationaldatamining.org/?p=482/）。核验 2026-09-22。

- **政策定位**：「**Consistent with ACM policy**，generative AI may not be an author and any use of generative AI must be fully disclosed in the work, either in the **acknowledgements section or in the relevant section** of the paper.」
- **披露位置**：**Acknowledgements 段** 或 **论文相关章节**（二选一，依使用场景）。
  - ⚠️ **关键纠偏**：前序会话曾记为「参考文献前独立『Declaration of Generative AI Software tools』段（改编自 Elsevier）」——**与官方原文不符**。JEDM 实际遵循 ACM 政策，披露位置为**致谢段或相关章节**，并非 Elsevier 式独立声明段。本表以官方原文为准。
- **AI 署名**：**禁止**（遵循 ACM authorship 准则，须满足实质贡献 + 参与撰写 + 对内容完整性负责三准则）。
- **审稿人约束**：EDM 评审指南明确「LLM 仅可用于拼写/语法检查，其余一切生成式 AI 使用在评审中**禁止**」（保密 + AI 非同行 + 系统性错误风险）。
- **数据开放**：鼓励 OSF/Zenodo 公开数据、预注册；与本项目 Zenodo v0.2.0 上传（待办 E）一致。

---

## 2. 目标期刊 × 政策 对照总表（核心）

| 期刊 | 出版方 | 披露位置 | 必备披露要素 | AI 署名 | AI 生成图像 | 语法/校对豁免 | 审稿人约束 |
|---|---|---|---|---|---|---|---|
| **TLT** | IEEE | Acknowledgment 段（文末、Refs 前） | AI 系统名 + 具体章节 + 使用层级说明；图注标 AI 生成 | **禁止** | 须声明（图注 + 致谢） | 编辑/语法增强：推荐披露非强制 | **禁用** AI 起草评审 |
| **IJAIED** | Springer | Methods 段（或替代段） | LLM/AI 工具使用记录 | **禁止** | **禁止**（生成式 AI 图像） | copy-editing 类：免声明 | 默认不用于评审判断 |
| **JEDM** | IEDMS(ACM) | Acknowledgements 段 **或** 相关章节 | 生成式 AI 使用 fully disclosed | **禁止** | 须声明（按 ACM） | 依 ACM：合理辅助可披露 | **仅**拼写/语法可用，余禁止 |
| **JSS** | Elsevier | 独立段「Declaration of generative AI…」（Refs 前） | 工具名 + 用途 + 监督程度（官方模板） | **禁止** | **禁止** | 基础语法/拼写/标点：免声明；实质结构改动须披露 | **禁用**上传未发表稿至 AI |
| **EMSE** | Springer | Methods 段（或替代段） | LLM/AI 工具使用记录 | **禁止** | **禁止**（生成式 AI 图像） | copy-editing 类：免声明 | 默认不用于评审判断 |
| **IST** | Elsevier | 独立段「Declaration of generative AI…」（Refs 前） | 工具名 + 用途 + 监督程度（官方模板） | **禁止** | **禁止** | 基础语法/拼写/标点：免声明；实质结构改动须披露 | **禁用**上传未发表稿至 AI |

> 共同点（四家一致强约束）：① **AI / LLM 不得列为作者或共同作者**，也不得作为作者引用；② 人类须对终版内容负全责；③ 在审稿件不得交由 AI 处理（保密）。

---

## 3. 本课题实际 AI 使用盘点与披露建议

> 以下为**须在披露声明中覆盖的 AI 使用面**，具体工具名与章节由作者按真实情况填实（不得虚构）。

| 使用面 | 项目内依据 | 建议披露位置（依目标刊） |
|---|---|---|
| **LLM 标注 / 标注流水线**（如 M3 ≥3 模型族 × ≥3 规模标注矩阵、E1-A/E1-B 题目级标注） | M3 稿 L633「含本文所用的 LLM 标注流水线」；M3 §8 标注矩阵方案 | 写法类：IEEE/JEDM→Acknowledgments；Springer→Methods；Elsevier→独立声明段 |
| **LLM 辅助写作 / 语言润色**（若用于草稿组织、可读性、语法） | M3 稿 L15「如明示禁止 AI 辅助写作，须由人类作者主导改写」 | 同上；若仅基础语法/拼写，IEEE/Elsevier 可豁免声明（Springer copy-editing 豁免、JEDM 依 ACM） |
| **AI 生成图像 / 图表**（若有） | — | 四家均须声明；Springer/Elsevier **禁止生成式 AI 图像**，须改用真实图表 |

**强提示（M3 稿 L15）**：若目标刊明示禁止 AI 辅助写作，须由**人类作者主导改写**后再投；披露声明不替代「人类主导」的实质要求。

### 3.1 中文撰写 → 英文翻译流程的披露处理（2026-09-23 新增）

**项目既定流程**：**四篇**稿件以**中文**撰写（便于作者本人阅读与逐句核校），投稿前译为**英文**。该流程已写入研究计划 v1.1 §10.5（中/韩两版）。

**三条必须说清的边界**：

1. **作者须核实 AI 输出并对内容负全责。** 中文底稿须**由人类作者撰写**、译稿须经作者逐句核校后再提交；四家均要求作者对内容承担全部责任，且**禁止**盲目复制粘贴 AI 输出。翻译不构成对「人类主导」这一实质要求的替代。
2. **翻译属须披露的 AI 使用（超出校对豁免）。**
   - Elsevier：基础语法/拼写/标点免声明，但对**句子结构或文本组织做实质性改动**须披露 → 翻译**须披露**。
   - Springer：「AI assisted copy editing」豁免明确**排除**「生成式编辑工作与自主内容创作」→ 翻译**不属豁免**。
   - IEEE：编辑/语法增强属「推荐披露非强制」，但 AI 生成**内容**（含翻译产出）须在 Acknowledgment 披露。
   - JEDM（ACM 式）：生成式 AI 使用须 fully disclosed（致谢或相关章节）。
3. **若目标刊明示禁止 AI 辅助写作，须由人类作者主导改写**，不得以翻译规避。

**译后披露语句建议**（在既有模板的 `[REASON]` 中显式写出翻译）：
> ... used [TOOL] in order to **translate the manuscript from Chinese (authored by the authors) into English and improve language readability**. ... the author(s) reviewed and edited the translated content sentence by sentence and take(s) full responsibility ...

---

## 4. 可直接套用的披露语句模板（中英）

> `[...]` 为须作者填实的占位；多工具/多章节按实列举。投稿前复核官网模板最新措辞。

### 4.1 IEEE（TLT）— Acknowledgment 段

```
# ACKNOWLEDGMENT
The authors used [NAME OF AI SYSTEM, e.g., an LLM-based labeling pipeline] to
support [SPECIFIC SECTIONS, e.g., the item-difficulty annotation in Section 8]
at the level of [LEVEL, e.g., generating candidate difficulty labels that were
reviewed and finalized by the authors]. The use of AI for editing and grammar
enhancement is outside the intent of this policy and is noted here as recommended.
```
图注：`Fig. X was created using [TOOL].`

### 4.2 Springer（IJAIED / EMSE）— Methods 段

```
The use of an LLM (large language model) is documented here: [TOOL NAME] was used
to [PURPOSE, e.g., support the item-difficulty annotation pipeline in Section X],
with all outputs reviewed and edited by the authors, who take full responsibility
for the content. AI-assisted copy editing for readability and grammar is exempt
from declaration per Springer Nature policy.
```

### 4.3 Elsevier（JSS / IST）— 独立声明段（Refs 前）

```
Declaration of generative AI and AI-assisted technologies in the manuscript preparation process
During the preparation of this work, the author(s) used [NAME OF TOOL / SERVICE]
in order to [REASON, e.g., support the item-difficulty labeling pipeline and improve
language readability]. After using this tool/service, the author(s) reviewed and edited
the content as needed and take(s) full responsibility for the content of the published article.
```

### 4.4 JEDM（IEDMS / ACM 式）— Acknowledgements 或相关章节

```
Acknowledgements (or relevant section):
The authors disclose the use of generative AI: [TOOL NAME] was used to [PURPOSE]
in [SECTION]. All AI-generated content was reviewed and edited by the authors, who
take full responsibility for the work. Generative AI was not listed as an author.
```

---

## 5. 强约束与风险提示

1. **AI 不可署名（四家一致）**：LLM / 生成式 AI 不得列为作者、共同作者，亦不得作为参考文献中的作者引用。署名即承担责任，AI 无法满足。
2. **政策频繁更新**：Elsevier 页标注「will update these policies as practices… evolve」；IEEE/Springer/JEDM 亦可能调整。投稿前须复核官网最新版，**以官网为准**。
3. **禁止盲目复制粘贴 AI 输出**：Elsevier、JEDM 均明确反对未经审查照搬 AI 产出；须「reviewed and edited… take full responsibility」。
4. **参考文献真实性**：AI 生成的参考文献可能错误/虚构（Elsevier 明示）；须逐条核对——与已闭环的 F 任务（30 条 `[VERIFY]` 批）精神一致。
5. **中文第二顺位刊**：仅英文第一顺位被拒且时间不可接受时启用，其 AI 政策须各自单独核查，本表不预覆盖。
6. **M3 合规提示须落实**：M3 稿 L15/L633 已埋 AIGC 合规与工具披露要求，本表为其提供可执行的刊别对照与模板，投出前须逐刊填实。

---

## 6. 下一步

- 本表已闭环待办 §3-I（🟡→🟢）：覆盖 6 个英文 Scopus 第一顺位刊 + 4 家政策官方原文 + 对照总表 + 可套用模板。
- 待作者动作：① 按真实 AI 使用面填实各刊披露声明模板；② 投稿前复核官网政策最新版；③ 若目标刊禁止 AI 辅助写作，须人类作者主导改写（M3 L15）。
- 仍待推进的投稿前项：E Zenodo v0.2.0 上传、G 正式提交(10-20)、D IRB 被试计划表(12-01)、H 语言确认；实验类 A1/A2/A4/C 仍待外部/人工。
