**Subject:** Submission of a theory/method paper — "Commensurability of Difficulty Scales: An Instability Proposition and Its Test on assist09" (with honest negative results)

**To the Editor-in-Chief of [IEEE TLT / IJAIED / JEDM],**

We submit the enclosed manuscript for consideration as a Regular/Research Article. It is a theory/method paper in educational measurement: we recast the neglected question of "whether difficulty can be placed on a single commensurable scale" as a falsifiable metrological proposition, and test it on synthetic data and four public learning-log corpora.

**Methodological contribution.** We show that linear [0,1] fusion of difficulty sources drifts under monotone reparameterization, while a quantile→logit commensurability metric is strictly invariant; on assist09 (994 items) the real drift falls from 0.5357 to 0.0001. We further locate a concrete directional error in fusion configuration (a negatively-signed signal assigned a positive weight) and propose a sample-size-adaptive shrinkage, both verified to improve small-sample rank stability without claiming predictive-power gains.

**Honest negative results (reported, not concealed).** In the spirit of preregistration-executable-verifiable research, we explicitly report what did *not* work or was *not* performed, and treat this as a contribution rather than a weakness:
1. The causal side was executed under a frozen identification strategy (2026-09-24): we detected **no preregistered internal optimum**, and a Junyi time-reversed negative control was significant, downgrading all dose–response readings to associational evidence. We therefore make **no point estimate, confidence interval, or test against 15.87%** for the optimal error rate.
2. Of seven preregistered hypotheses, **H2 was only partially tested and H3 and H7 were not executed** (source sets differed from the preregistration; ECE/Brier not computed). We do not rewrite these as supported.
3. The `srw7` fusion optimizer and direction-error correction (O8/O11/O12) were verified **only on Junyi**, not cross-system replicated (no corresponding validation on DBE).

These boundaries delineate the scope of the method rather than invalidate its engineering contribution, which (invariance + criterion-dependence of fusion gains) replicates across more than two systems. We believe this candid handling of negative/null results and preregistration gaps aligns with your journal's emphasis on methodological rigor and reproducibility.

**Fit & compliance.** The work fits the method/theory remit of TLT/IJAIED/JEDM; all three accept methodological papers without requiring every preregistered hypothesis to be supported. We will conform to the relevant length guidance (TLT ≤10 double-column pages; IJAIED 5000–7000 words; JEDM concise) upon final English typesetting, and will complete a word/page count check before submission.

**Data & code availability.** All numbers are produced by scripts under `results/code/`; the tested system is archived on Zenodo (DOI 10.5281/zenodo.22719229). Data/code availability and the generative-AI use disclosure will follow the targeted journal's current policy (IEEE Acknowledgment / Springer Methods / JEDM "Declaration of Generative AI Software tools" section).

We confirm the manuscript is original and not under consideration elsewhere.

> **⚠ 批准语句与署名暂缓（审阅意见 2.4 ③ 与 §10，2026-09-29）。** 本信此前在"all authors approve submission"下方并列署有通讯作者（MinPo Jung）的姓名。**该批准语句与署名现已移除**：通讯作者已同意担任本稿通讯作者，但按其要求，**投稿信的批准语句、Zenodo 贡献者名单与 AI 使用声明，在其读完最终稿并批准之前，不得出现其姓名**。待最终稿获批后，再按其同意的方式补入。

Sincerely,
Zexiao Weng
（通讯作者署名待最终稿获批后补入）
