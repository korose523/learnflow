**Subject:** Submission of a theory/method paper — "Commensurability of Difficulty Scales: An Instability Proposition and Its Test on assist09" (with honest negative results)

**To the Editor-in-Chief of IEEE Transactions on Learning Technologies,**

> **收件期刊说明（2026-10-03 填实）**：按研究计划书 §7.1 的期刊表，M1 的**第一顺位**为
> *IEEE Transactions on Learning Technologies*（TLT），备选 *International Journal of
> Artificial Intelligence in Education*（IJAIED）与 *Journal of Educational Data Mining*（JEDM）。
> 定稿投哪一刊时，只需替换上方刊名并删去本说明块；**三刊均在投稿前合规声明的适用范围内**
> （TLT→Acknowledgment；IJAIED→Methods；JEDM→致谢或相关章节）。

We submit the enclosed manuscript for consideration as a Regular/Research Article. It is a theory/method paper in educational measurement: we recast the neglected question of "whether difficulty can be placed on a single commensurable scale" as a falsifiable metrological proposition, and test it on synthetic data and four public learning-log corpora.

**Methodological contribution.** We show that linear [0,1] fusion of difficulty sources drifts under monotone reparameterization, while a quantile→logit commensurability metric is strictly invariant; on assist09 (994 items) the real drift falls from 0.5357 to 0.0001. We further locate a concrete directional error in fusion configuration (a negatively-signed signal assigned a positive weight) and propose a sample-size-adaptive shrinkage, both verified to improve small-sample rank stability without claiming predictive-power gains.

**Honest negative results (reported, not concealed).** In the spirit of preregistration-executable-verifiable research, we explicitly report what did *not* work or was *not* performed, and treat this as a contribution rather than a weakness:
1. The causal side was executed under a frozen identification strategy (2026-09-24), but it **did not pass the preregistered positive-control criterion and its implementation differs from the frozen protocol document; its results are therefore not interpretable**, and the causal side has been removed from this manuscript and transferred to a separate paper. We consequently retain **no dose–response reading** and make **no point estimate, confidence interval, or test against 15.87%** for the optimal error rate.
2. Of seven preregistered hypotheses, **H2 was only partially tested and H3 and H7 were not executed** (source sets differed from the preregistration; ECE/Brier not computed). We do not rewrite these as supported.
3. The `srw7` fusion optimizer and direction-error correction (O8/O11/O12) were verified **only on Junyi**, not cross-system replicated (no corresponding validation on DBE).

These boundaries delineate the scope of the method rather than invalidate its engineering contribution, which (invariance + criterion-dependence of fusion gains) replicates across more than two systems. We believe this candid handling of negative/null results and preregistration gaps aligns with your journal's emphasis on methodological rigor and reproducibility.

**Fit & compliance.** The work fits the method/theory remit of TLT/IJAIED/JEDM; all three accept methodological papers without requiring every preregistered hypothesis to be supported. We will conform to the relevant length guidance (TLT ≤10 double-column pages; IJAIED 5000–7000 words; JEDM concise) upon final English typesetting, and will complete a word/page count check before submission.

**Data & code availability.** All numbers are produced by scripts under `results/code/`. The tested system is archived on Zenodo; the manuscript body cites the artifact by repository rather than by DOI, for the following reason. **The currently registered Zenodo record is v0.1.0, whose record title is "学习成瘾测量工具" (a learning-addiction measurement tool) — a topic unrelated to this manuscript.** The corrected v0.2.0 metadata, which retitles the record to the difficulty-measurement line of work, is prepared but **not yet published**; the DOI to be quoted is therefore the one minted on publication of v0.2.0. We prefer to supply the repository link now and insert the definitive DOI at submission, rather than direct a reviewer to a record whose title does not match the manuscript. Data/code availability and the generative-AI use disclosure will follow the targeted journal's current policy (IEEE Acknowledgment / Springer Methods / JEDM "Declaration of Generative AI Software tools" section).

We confirm the manuscript is original and not under consideration elsewhere.

> **⚠ Approval statement and byline withheld (review item 2.4③ and §10, 2026-09-29).** This letter previously carried the corresponding author's name (MinPo Jung) directly beneath the "all authors approve submission" statement. **That approval statement and the byline have now been removed**: the corresponding author has agreed to serve as such, but at their request, **the approval statement in this submission letter, the Zenodo contributor list, and the AI-use statement must not carry their name until they have read and approved the final manuscript**. Once the final version is approved, it will be restored in the manner they consent to.

Sincerely,
Zexiao Weng
(corresponding-author byline to be inserted after the final manuscript is approved)
