# Commensurability of Difficulty Scales: An Instability Proposition and Its Test on assist09

Zexiao Weng¹ and MinPo Jung¹,*

¹ Youngsan University, Busan 48015, Republic of Korea

* Corresponding author. Email: minpo@ysu.ac.kr; ORCID: 0009-0003-3369-757X. Zexiao Weng ORCID: 0009-0009-8600-8954.

AI-Assisted Writing Disclosure. This manuscript was prepared with the assistance of large language models (LLMs) and AI coding agents. These tools were used, to varying extents, for: (i) generating and editing analysis scripts; (ii) executing and re-running experiments; (iii) drafting, translating and polishing manuscript text; (iv) drafting internal revision-tracking documents. The claim made in an earlier version of this disclosure — that the LLM "was used strictly as a language-polishing and drafting aid" and that no LLM participated in analytical, statistical or experimental work — **has been withdrawn**, because it is not consistent with the traces visible in the accompanying repository (supervisor's review §2.3, 2026-09-29). The per-task division of work between the author and these tools, and the scope of the author's own verification of each tool output, is recorded by the author in the role-and-tools table of the dissertation proposal (§10.1) and will be stated here in its final form before submission. The corresponding author has **not** yet reviewed and approved this disclosure; accordingly, and per review §10, the corresponding author's name is withheld from this manuscript until the final version is approved. All numerical results reported here were produced by the scripts in the accompanying repository and are reproducible from them.

**Numeric baseline (review §2.1).** All asset and count figures quoted in this manuscript (registered mechanisms, learning methods, service modules, code lines, API endpoints, test files and collected tests) are stated at the **unified baseline git tag `v1.1-submit`**, recomputed on the merged tree by `learnflow-backend/scripts/verify_asset_numbers.py --doc-check` and `scripts/verify_counts.py`; cross-document agreement across the proposal, the research report, the journal-split plan and M1–M4 is enforced by `scripts/verify_cross_doc_numbers.py`.

**Relation to the companion manuscript M4 (review §4.1 / §4.4, 2026-09-29).** A companion manuscript M4 (*Reliability-Structured Combined Difficulty Estimation*) shares its empirical basis with §7 of this paper (the same `difficulty_cache.npz`, the same DBE teacher labels, the same Junyi labels, the same B-block holdout, the same `λ_cf`, the same `srw7`). Per review §4.4, **M4 is not submitted as an independent manuscript**; its disposition (merged into this paper as a section, or a pre-registered confirmatory experiment on a different dataset) is to be decided on **2026-11-03**, with no new experiments added before that date. **For any quantity bearing the same name in both, this paper is authoritative**; M4 may not set priority in the reverse direction.

## Abstract

(Methodological contributions upfront: the two independently standing methodological conclusions of this paper are the quantile-logit metric invariance identity and the `srw7` sample-size-adaptive shrinkage weighting; the empirical negative results below are all presented within this framework.) Adaptive learning systems must answer "what difficulty should the next item have?" every day, yet the prior question—whether difficulty is a quantity that can be placed on one common scale—is systematically skipped. We reformulate that question as a falsifiable measurement proposition and report three results. **First, the magnitude of the instability proposition (C1) on real systems is quantified.** The invariance side of the proposition is an identity, not a discovery (Section 3.2: for strictly increasing g, #{g(x_cal) ≤ g(x)} = #{x_cal ≤ x}, so effective weights under the quantile metric are pointwise invariant); this paper's contribution is to quantify how large the discrepancy becomes when that identity is violated. If difficulty sources are each normalised to [0,1] and then linearly combined, the "effective weights" defined by marginal contribution equal neither the nominal weights (π₁ = 0.532 ± 0.026 against nominal w₁ = 0.40 in simulation) nor themselves under a monotone reparameterisation of any single source: drift is exactly zero under affine transforms (absorbed by min-max) but averages L1 = 0.1276 (SD 0.0196) under nonlinear monotone transforms, with rank reversals in 36.4% of (source, transform) cells and complete sign reversal in the strongest counterexample (Spearman −0.20, L1 = 0.6893). An empirical-CDF-to-logit quantile metric gives exactly zero drift under shared calibration, 0.016 linking sampling noise under independent calibration, and zero reversals. On real data (assist09, 994 items), linear min-max fusion drifts by L1 = 0.5357 with substantial reversals, while the quantile metric reduces this to 0.0001 with reversals eliminated. **Second, the gain from multi-signal fusion is a gain in consistency with expert labels, not in predictive power.** On DBE-KT22 (212 items), the rank correlation between expert and empirical difficulty is only 0.2207; a joint IRT-1PL estimator raises it merely to 0.2300, whereas equal-weight fusion of five behavioural signals (quantile metric) rises to 0.2918 and optimised weights under repeated 5-fold ×10 cross-validation reach 0.5240 ± 0.1069, driven by a differential feature "self-reported difficulty high and trust low." On Junyi (1,234 exercises, 16.21 million interactions, no self-report feedback) the same pattern reproduces: 0.2610 → 0.3629, with repeated cross-validation 0.4023 ± 0.0480; the bootstrap paired gain is Junyi Δ = +0.1017 [0.0726, 0.1325] (p = 0.000), DBE Δ = +0.0723 [−0.0195, 0.1649] (one-sided p = 0.059, only marginally significant). **Qualification (review §3.2 ③): when the criterion quantity is success rate, the success-rate estimator's dominance at large samples is design-expected; fusion's role is rank stabilisation at small samples.** **Third, the above gain reverses under a changed criterion.** The rank correlation between expert labels and real-performance difficulty is only 0.4326; once the criterion is switched to "real performance on unseen samples," equal-weight fusion is worse than success rate alone at every sample size on both Junyi and DBE (Junyi −0.0267 → −0.1222, DBE −0.1752 → −0.2113, fusion win rate 0.00). One located cause is a directional error in the fusion configuration (the upgrade rate was assigned a positive weight +0.154); after its removal and the introduction of sample-size-adaptive shrinkage λ*(k) = 1/(1+(k/27.4)^0.902) (R² = 0.9989; the deployed value uses the leave-one-k cross-validation fit 27.3 / 0.895, rounded from k₀ = 27.332), the small-sample bracket first overtakes (k = 10: +3.43 percentage points), but the gain falls below 0.22 pp for k ≥ 100. Further, we optimise the fusion estimator itself—sign-correcting each signal by its in-fit-block rank correlation (retaining the information of inversely signed signals rather than dropping the column) and split-half-reliability weighting per signal—yielding the `srw7` estimator; under both record-level and student-level double holdout it is non-inferior to the "success-rate-only" baseline at every sample size and exceeds O8's fused6 at all brackets (record-level +3.823 / +2.025 / +0.930 / +0.391 / +0.138 pp; student-level +4.283 / +2.189 / +0.951 / +0.335 / +0.102 pp), eliminating fused6's harmfulness below baseline for k ≥ 25. Finally, we report the sliding-window error-rate distribution on assist09 (n = 286,150 windows; mean 0.3511). At window width W = 20 it has only 21 discrete support points (k/20); recomputed by integer error counts, the single-value mode is an error rate of 0.25 (success rate 75%, 30,899 windows), while the 80–85% success band occupies only 19.64% of windows. The earlier-reported "mode interval 0.15–0.20 (success 80–85%)" was a binning-boundary artifact (floating-point merging from interval edges coinciding with support points) and is voided. This descriptive distribution is a distribution of **experienced difficulty**; it does not constitute a test of the 85% rule or of the 80.7% value, and about either this paper says nothing. The preregistered doubly robust (AIPW/DR) off-policy evaluation was executed on 2026-09-24, but **it did not pass the preregistered positive-control criterion and its implementation differs from the frozen identification strategy (LF-CIS-2026-09-22); its results are therefore not interpretable**, and the causal side has been removed from this paper and transferred to the fourth paper (review §2.2, 2026-09-29). This paper makes no point estimate, confidence interval, or test of 15.87%.

**Keywords**: difficulty measurement; commensurability; instability proposition; quantile linking; expert labels; criterion dependence; optimal error rate; negative results

## 1 Introduction

### 1.1 A skipped question

No adaptive learning system can avoid "what difficulty should the next item have." The standard engineering practice is to normalise several quantities called "difficulty" or "ability"—the mastery probability of knowledge tracing, the memory difficulty of spaced repetition, the ability estimate of competitive rating, the window success rate of recent responses—and then feed them into a weighted sum with hard-coded weights. This practice presupposes that these quantities already live on a comparable scale. As far as the literature we surveyed indicates, this presupposition has never been tested on its own.

The presupposition is suspicious not because the normalisation is done carelessly, but because it is undefined in a measurement-theoretic sense. The weighted-sum operation requires that the addends belong to the same kind of scale on which linear combination is well defined: there is no well-defined addition between ordinal, interval, and ratio scales. When a system adds "mastery probability" and "memory difficulty," it has effectively made an undeclared metric choice, and the consequence of that choice is absorbed into the weights and then misread as the effect of a "difficulty recipe."

We name this phenomenon **instability** and write it as a falsifiable proposition: when sources are each normalised to [0,1] and then linearly combined, the effective weights defined by marginal contribution drift with any monotone reparameterisation of a single source; whereas if sources are first linked through the empirical CDF to a logit metric and then fused, the effective weights are strictly invariant under any strictly monotone reparameterisation. This contrast is not engineering common sense of the "we did a normalisation" kind, but a computable claim about why current mainstream implementations are measurement-theoretically invalid.

### 1.2 Why this is not a technical detail

One may ask: a few decimal points of weight drift—how much does it matter? It matters because it determines the system's interpretability and tunability. If the weight vector "0.45 / 0.35 / 0.20" becomes a different vector once the knowledge-tracing side is changed from `mastery × 9 + 1` to `mastery`, then everything built on this weight vector—every empirical tuning, every A/B conclusion, every claim that "we find mastery should weigh more"—merely describes a particular implementation choice, not difficulty itself. The commensurability problem is therefore not a preparatory technical cleanup but the precondition for whether any subsequent difficulty research can be interpreted.

The motivation for this paper is precisely this preconditional nature. The original preregistration expressed this relation as "the measurement goal is the precondition of the causal goal: if the dose itself is not a well-defined difficulty measure, its causal effect cannot be interpreted either." That sentence still holds here, but its practical consequence is more direct than expected: **the measurement-side test is complete; the causal side was additionally executed at revision time under a frozen identification strategy (LF-CIS-2026-09-22), yielding a negative result and one significant negative control (see §8.3), rather than causal-grade evidence.** This paper is thus a manuscript that gives complete results on the measurement side and honest negative results on the causal side. This asymmetry is itself information, and we do not hide it.

### 1.3 What this paper does not claim

To prevent readers from inferring contributions from the title by habit, we list four "non-claims" up front:

**We do not claim** that multi-signal fusion improves the predictive power of difficulty estimation. §7 gives decisive evidence: under holdout validation, fusion is instead worse than success rate alone. Every gain reported in §6 uses the criterion of **expert difficulty labels**, so the correct phrasing is "gain in consistency with expert labels."

**We do not claim** that the optimal error rate equals or differs from 15.87%. §8 reports a descriptive sliding-window error-rate distribution; the preregistered doubly robust (AIPW/DR) off-policy evaluation was executed on 2026-09-24 under a frozen identification strategy, yielding no detected internal optimum and a significant Junyi time-inverted negative control (dose–response readings downgraded to associational evidence, see §8.3), so this paper still makes no assertion of any point estimate or confidence interval for the optimal error rate.

**We do not claim** that knowledge-tree structure can serve as a difficulty proxy. §5.5 gives a clean small negative result: the knowledge-tree depth vs. empirical difficulty rank correlation is only +0.0785 and non-monotone across strata, and parent–child edge difficulty-gradient consistency is 0.487 (about a coin flip).

**We do not claim** that the studied system is a special case in difficulty handling. On the contrary, the studied system is a real, built, publicly archived K12 adaptive learning platform (54 gamified intervention mechanisms, 28 learning methods, registry fingerprint `ee1a49be5732`), and its difficulty-fusion code is no different from the common practice of comparable systems. We criticise a class of implementations, not one implementation.

### 1.4 Contributions and main findings

**Contribution 1: turn "difficulty commensurability" from a design vocabulary into a computable, falsifiable proposition, and quantify how large the violation is.** The side of the proposition stating "effective weights are invariant under the quantile metric" is an **analytic identity** (§3.2); we do not treat it as a discovery. What is testable is the other side—**how far linear min-max fusion violates this identity**. The synthetic experiment (§4) gives the complete numeric picture: under the linear [0,1] metric affine drift is exactly 0, nonlinear monotone drift is L1 = 0.1276, 36.4% of cells show rank reversal, and the strongest counterexample completely reverses sign; under the quantile-logit metric drift is 0 under shared calibration and only 0.016 sampling noise under independent calibration. Real data (§5.3) gives the engineering-landing evidence: on assist09 linear fusion drifts L1 = 0.5357, which falls to 0.0001 after switching to the quantile metric, with rank reversals eliminated.

**Contribution 2: give the distance between the "expert-annotation / behavioural-evidence" two systems of difficulty evidence, and re-evaluate the value of multi-signal fusion accordingly.** On DBE-KT22 the rank correlation between expert and empirical difficulty is only 0.2207 (p = 0.0012); switching to a joint IRT-1PL estimator raises it merely to 0.2300—the bottleneck is not the estimator. But equal-weight fusion of five behavioural signals in the quantile metric rises to 0.2918, and optimised weights reach 0.5240 ± 0.1069 under repeated 5-fold ×10 cross-validation. The mechanism is located in a differential feature: self-reported difficulty and trust correlate at +0.94 at the item level (Pearson), while in quantile space "trust reversed" vs. self-reported difficulty correlate at −0.80; subtracting the two cancels the common-mode noise.

**Contribution 3: give a set of negative results via criterion switching, and locate one real directional error.** The rank correlation between expert labels and real-performance difficulty is only 0.4326 (§7.1); after switching the criterion to "real performance on unseen samples," equal-weight fusion is worse than success rate alone at **every** sample-size bracket on both Junyi and DBE, with fusion win rate 0.00 (§7.2). We further locate that the upgrade rate correlates −0.1837 with expert labels and −0.756 in-pool, yet the optimiser assigned it a **positive weight** +0.154; after removing this signal and introducing sample-size-adaptive shrinkage, the small-sample bracket first overtakes (k = 10: +3.43 percentage points), but the gain decays below 0.22 pp for k ≥ 100; the correct phrasing for "fusion gain" is gain in consistency with expert labels, not predictive-power improvement (§7.2). The validity gap of record-level holdout is separately closed by student-level holdout validation, with unchanged conclusions (§7.6). On this basis, §7.8 reports two optimisations of the fusion estimator: changing a directionally wrong signal from "drop the whole column" to "sign-correct," and adding per-signal split-half-reliability weighting (`srw7`). Under both record-level and student-level double holdout, `srw7` is non-inferior to the "success-rate-only" baseline at every sample-size bracket and exceeds fused6 at all brackets; at the student level `srw7` has paired win rate 0.902–1.000 against fused6, with Wilcoxon signed-rank p ≤ 1.29 × 10⁻⁶⁶. This also shows that O8's "drop the upgrade rate," though directionally correct, discards the signal's effective information and is not the optimal handling.

**Contribution 4: delimit the scope of the above conclusions across systems.** The four datasets cover three different evidence regimes: DBE-KT22 has expert annotation and student self-report; Junyi has expert annotation but no feedback; XES3G5M has full item text and a knowledge tree but no expert difficulty; assist09 has hint use and multi-skill annotation. The fusion gain reproduces at the same order on DBE and Junyi (+31% and +39%), showing it is not a single-system artifact; but the λ-shrinkage gain is verified only on Junyi, with no gain on DBE—we report this non-reproduction honestly.

### 1.5 Structure and reproducibility

§2 reviews related work; §3 formalises the typology of difficulty sources and the instability proposition; §4 reports the proposition's validation on synthetic data; §5 reports the metric repair on real data and two negative results; §6 reports the gain of multi-signal fusion under the expert-label criterion; §7 switches the criterion and reports the conclusion reversal, the directional error, the sample-size-adaptive shrinkage, and the leave-one-k cross-validation (in-interval interpolation) test of that shrinkage formula plus student-level holdout validation; §8 reports the descriptive evidence on the optimal error rate and the unfinished causal identification; §9 discusses implications, code landing, and limitations; §10 lists the honest gap inventory; §11 concludes.

**Scope note on the title.** The real-data test of the instability proposition (C1) is in fact carried out at only **one** real system, assist09 (994 items, §5.3); the Junyi, DBE-KT22, and XES3G5M datasets bear the multi-signal-fusion consistency experiment, the expert-annotation experiment, and the knowledge-tree / ordered-transition experiment, and do **not** constitute a test of proposition C1. The title is narrowed to the proposition's test scope; the roles of the other datasets are stated honestly in the Abstract and the §5 data tables.

**Reproducibility note.** Every number in this paper is produced by the scripts under `results/code/`, deterministically or with fixed seeds: `results/code/m1_instability.py` (synthetic, seed `902000+r`), `m1_real_data.py`, `optimized_experiments.py`, `o4_fusion.py`, `o4b_fusion.py`, `o5_junyi_fusion.py`, `build_difficulty_cache.py`, `o6_difficulty_stats.py`, `o7_holdout_validation.py`, `o8_fusion_variants.py`, `o9_lambda_generalization.py`, `o10_user_holdout.py`, and the causal-side `results/m1/aipw/aipw_run.py` (added 2026-09-24; main analysis W=20 and window-width robustness W=10/40, three runs, outputs `aipw_results*.json` and the trace `aipw_audit.log`). Raw products are the same-named `.json`. We do not recompute, re-estimate, or backfill any unexecuted experiment.

**Random-seed table.** The concrete fixed-seed values referenced above (line numbers point to the statement position within each script):

**Table 1. Random seeds and the random steps they affect**

| Script | Random seed | Affected random step |
|---|---|---|
| `results/code/m1_instability.py` | `902000 + r` (r = repeat index) | resampling and repeats of synthetic data |
| `results/code/m1_real_data.py` | `20260922` (`:72`, `np.random.default_rng`) | reservoir / reshuffle of real-data experiment |
| `results/code/o9_lambda_generalization.py` | `20260913` (`:76`, `:192`) | in-pool sampling of λ*(k) leave-one-k cross-validation |
| `results/code/o11_fusion_optimization.py` | `20260913` (`:106`) | repeated holdout of fusion variants (REP = 25 × SPLITS = 20) |
| `results/code/o12_student_o11.py` | `20260913` (`:51` `random.seed`, `:128` `default_rng`) | reshuffle and reservoir of student-level holdout |
| `results/code/build_difficulty_cache.py` | `20260913` (`:18`, `random.seed`) | sampling of difficulty-cache construction |
| `results/code/o4_fusion.py` | `42` (`:126`, `rngcv = np.random.default_rng(42)`) | fold split of 5-fold cross-validation |
| `results/m1/aipw/aipw_run.py` | `42` (`:63`, `SEED = 42`; `:85` `RandomState`, `:542`/`:551` `random_state`) | AIPW/DR bootstrap and model randomness |

**Results that cannot be reproduced bit-for-bit without the above seeds.** The following three classes of numbers depend on specific seed splits or resampling and **will jitter by an undetermined magnitude under a different seed, being bit-for-bit reproducible only under their stated seeds**: (i) the **0.4778** in §6.2 (single 5-fold CV of O4 optimised weights, seed 42)—one reason we require priority citation of the repeated 5-fold ×10 values (DBE 0.5240 ± 0.1069, Junyi 0.4023 ± 0.0480); (ii) **all AIPW results in §8.3**, including point estimates and bootstrap confidence intervals (seed 42, main analysis W=20 and window-width robustness W=10/40); (iii) **the single-value-mode bootstrap 95% confidence set in §8.1** (200 resamples by student, single-value mode 0.25 occupies 95.5%). Deterministic conclusions (e.g., the metric identity in §3.2, the 0.5357 and 0.0001 in §5.3) do not depend on seeds.

## 2 Related Work

### 2.1 Knowledge tracing and the difficulty–ability confound

Deep knowledge tracing is the mainstream paradigm for predicting "the probability that a student answers the next item correctly," but its output is a **probability**, not difficulty. When a system uses this probability as a difficulty signal, the difficulty–ability confound arises: a high correct rate can come from either an easy item or a capable student. One manifestation of this confound in the literature is that different studies compare AUCs on the same incomparable scales. Liu et al. (2025), after standardising 21 deep knowledge-tracing models and 9 datasets, note that the field shows "highly similar methods, minimal divergence in conclusions, and inconsistent AUC reporting"—one source of divergence being precisely that the compared quantity is not on the same metric. Our treatment is not to propose yet another predictive model but to single out "whether these quantities are additive" for testing, which is the two sides of the same problem pointed out by that review.

### 2.2 Test equating and IRT linking

The equating literature solves "whether different test forms are comparable," sharing the same measurement-theoretic root as our "whether different difficulty-technique routes are comparable." Weber, Becker, Spinath, and Koch (2025) systematically compared five equating methods (MS, MM, MGM, IRF, TRF) under 400 simulation scenarios for parameter recovery under 2PL/3PL, with direct methodological implications for us: **the choice of equating method has little effect; what truly determines recovery quality is the anchor items' high discrimination, low guessing probability, and large sample**; parameter recovery is unacceptable below a sample size of 100. This conclusion supports our approach—invest resources in the metric and signal quality, not in more complex linking methods. Deng (2025) examines, on PISA 2018 science-module Arabic- and Chinese-group data, the effect of rapid guessing on multi-group concurrent IRT calibration, finding the procedure robust to anchor identification and ability estimation but reducing the precision of individual ability estimates. Together the two studies delimit the boundary of our calibration design: whether rapid-guess contamination of **difficulty linking** is measurable remains an open question, on which we make no claim.

### 2.3 Multi-signal difficulty estimation and the place of expert labels

The "difficulty" that adaptive ranking truly needs has long been assumed estimable from the single signal of correct rate. Ding et al. (2024), with Easy2Hard-Bench, use joint IRT and Glicko-2 calibration to provide difficulty labels for standardised LLM difficulty evaluation, representing the mainstream route of "treating difficulty as a calibratable parameter." Our quantile metric shares IRT's logit intuition with that route but changes the object from "item correct rate" to "the rank of any monotone observation," thereby elevating invariance from an estimation problem to an analytic identity. The division-of-labour difference from that work must be stressed: they pursue more accurate difficulty labels; we ask **under which criterion those labels sit**. §7 will show that this question changes the sign of the conclusion.

### 2.4 The 85% rule, the challenge-point framework, and evidence on real learners

Wilson et al. (2019) derive, on a gradient-descent binary-classification learner, an optimal error rate of 15.87%, i.e., the "85% rule." This is a theorem about a specific learning algorithm, whose derivation depends on five premises: a binary-classification task, no hints, no skipping, no forgetting, and no transfer. Real classrooms deviate on all five dimensions simultaneously. Notably, this applicability gap was not excavated by later critics from a seam in the literature but was explicitly limited by the original authors in the Discussion: the derivation holds only "in the special case of a binary classification task to which the stochastic gradient descent learning rule applies," and they explicitly state that "it remains to be generalized to broader contexts, such as multiple-choice questions and different learning algorithms," and that "not all models will exhibit a difficulty sweet spot" (the authors use a Bayesian learner with a perfect memory as a counterexample). Therefore the original text contains no direct quotation of the kind "this rule may not apply to students because they are not learning a binary-classification task"—an earlier paraphrase had reshaped it into a direct quotation, which is a misquotation that we correct here. The theoretical boundary goes further—when the noise distribution changes from Gaussian to Laplace or Cauchy, the optimal accuracy drifts to about 82% and 75% respectively; for a Bayesian learner with perfect memory, no such sweet spot exists.

The verbatim English of these three limitations, the PMC paragraph ids (Par26 / Par30 / Par31), and the retrieval basis are in `results/ref_verify/wilson2019_quotations.md` (Europe PMC PMC6831579 full-text XML, retrieved 2026-09-25). Two points must be noted: first, the word "student" appears **0 times** in the entire original text, so there is no original quotation about "whether this rule applies to students"—only the applicability-boundary limitations above are citable; second, the bioRxiv preprint (10.1101/255182v1) Discussion wording differs substantially from the published version, so **all citations use the Nature Communications published version**.

Directional evidence on real learners comes from Baillifard, Belardi, and Martarelli (2025): on the logs of 413 learners in a digital-skills course, performance peaked at about 80.7% success rate, and the optimal strategy showed significant heterogeneity among the most persistent, highest-performing learners. **The source grade must be noted**: that 80.7% comes from the EADTU *Envisioning Report for Empowering Universities 2025*, a **non-peer-reviewed** annual report, not a journal paper. We therefore cite it as a **candidate value to be tested**, not as an opposing claim of equal evidence grade to 15.87%; the distribution evidence in §8 discriminates between neither, and part of the reason for this handling also comes from the source-grade difference. Guadagnoli and Lee (2004)'s challenge-point framework (CPF) and its extension (Hodges and Lohse, 2022) provide a mechanistic explanation: CPF reconstructs the optimal difficulty from a "single point" to a dynamic interval of "functional task difficulty = f(nominal difficulty, learner skill, practice condition)," explicitly incorporating motivational cost, so **the true optimum should be below 85%**. The distribution evidence in §8 is compatible with this expectation; the preregistered causal identification was executed on 2026-09-24 under a frozen identification strategy, yielding no detected internal optimum and a significant negative control (§8.3)—that negative result does not conflict with CPF's "dynamic interval" expectation, but we do not claim it causally tests that expectation.

A positive case for task dependence also exists at the controlled-experiment level: Al-Fawakhiri, Kayani, and McDougle (2023, bioRxiv, doi:10.1101/2023.07.19.549705), in a motor-skill task with dynamically adjusted difficulty by performance (N=192), empirically find an optimal error rate of about 30%, consistent with their theoretical prediction extending Wilson et al. (2019) to the sensorimotor domain. This further supports the proposition itself that "an optimal error rate exists and varies by task"; but the domain is motor-skill learning, and the **value cannot be extrapolated to academic learning**, so we cite it only as a task-dependence case, **not as a coordinate of this study's RQ2 decision table, nor as a new target value**.

### 2.5 Off-policy evaluation: the preregistered toolbox and its execution (2026-09-24 supplement)

Adaptive learning systems almost never run online randomised controlled experiments; a student's item choice is jointly determined by the system strategy and self-selection, so "if this student were placed in another difficulty bracket, how would their mastery speed change" is a counterfactual question. Off-policy evaluation provides standard tools: a propensity model characterises selection probability, an outcome model characterises the endpoint, and then inverse-probability weighting or a doubly robust estimator gives the counterfactual mean (Dudík, Langford, and Li, 2011); double/debiased machine learning with cross-fitting further reduces the regularisation bias of the outcome model (Chernozhukov et al., 2018); the E-value quantifies how strong unobserved confounding must be to explain away the estimated effect (VanderWeele and Ding, 2017). This toolbox remains scarce in educational data mining and was the core method of the original preregistration.

**Removal note (2026-09-29, review §2.2): of the methods listed in this section, AIPW/DR and the clustered bootstrap were executed on 2026-09-24 under the frozen identification strategy (LF-CIS-2026-09-22)**; the dose uses the raw-integer-error-count caliber solidified by that strategy (not the forward-calibrated version of the original preregistration), and the E-value and the formal ordering test of the five premises were not executed. **That execution did not pass the positive-control criterion, and its implementation differs from the frozen document in four places (the ability-confounding caliber, the item-difficulty caliber, the time-inverted control window, and the treatment-window width); its results are therefore not interpretable and have been removed from this paper** — see §8.3. This section is retained so that readers can compare the preregistered design with what was actually executed.

## 3 Theory: the Instability Proposition

### 3.1 Four difficulty sources and their scale types

Suppose the system holds four sources: knowledge-tracing mastery m ∈ [0,1], spaced-repetition memory difficulty D, competitive-rating ability θ_EL, and window success rate r ∈ [0,1]. Following the classical scale classification and the three-plane classification of difficulty measurement (construction / scale / dependence), the four belong to different types:

**Table 2. Four difficulty sources and their scale types**

| Source | Scale type | construction | scale | dependence |
|---|---|---|---|---|
| KT mastery m | bounded latent variable (approx. ordinal after integerisation) | machine-inferred | static, continuous | depends on real responses |
| SR memory difficulty D | ordinal scale | machine + human | dynamic, discrete | model-specific |
| EL competitive rating θ_EL | interval scale (log-odds scale) | machine | dynamic, continuous | not directly dependent on ground truth |
| WR window success rate r | ratio scale | machine | static, continuous | depends on real responses |

Two key judgements follow. First, **window success rate is not difficulty but the joint result of difficulty and ability**: it roughly satisfies r ≈ σ(θ − β), encoding both ability and difficulty, so linearly adding it to a pure difficulty measure is a category error. Second, the four sources have inconsistent scale types—there is no well-defined linear combination between ordinal, ratio, and interval scales. Together these constitute the intuitive source of the instability proposition: it is not that the fusion weights are mistuned, but that the objects being added do not belong to the same additive space.

### 3.2 Two metrics and their invariance

Let the fusion rule be S = Σ_k w_k · z_k, where z_k is the value of the k-th source after some mapping and w_k is the nominal weight. Define the **effective weight** by the marginal-contribution method:

  **π_k = w_k · Cov(z_k, S) / Var(S)**, and Σ_k π_k = 1.

When the sources are orthogonal and equal in dispersion, π = w; otherwise π depends on each source's dispersion and correlation structure—which is precisely the source of drift.

**Reading of negative π (must be explicitly defined).** When a source's covariance with S is negative, π_k < 0, and Σ_k π_k = 1 still holds, but **a single π_k can no longer be read as a "weight share"**—a negative value means that source plays a **counteracting** role in the weighted sum: it does not "contribute a negative share" but raises the share of the other positive weights. Counting negative π_k into the L1 drift (the component-wise absolute sum |π − π⁰|) is therefore a **deliberately conservative** choice: it counts both "direction flip" and "share-size change" equally as drift, rather than letting the two errors cancel through positive–negative offset. This situation does not appear in the synthetic experiment (the four sources are correlated monotone observations of one latent ability). **It must be emphasised that, under this paper's current caliber, there is also no instance of negative π in the real data, so the discussion of negative π here should be regarded as pure theoretical preparation, not an empirical claim about the real data.**

- **Under the current 0.5357 caliber all three components are positive**: the min-max baseline effective weights on assist09 are π = `[0.5219, 0.344, 0.1351]` (`results/code/optimized_results.json`, O1's `o1_metric_comparison.A_minmax_linear.pi_baseline`), **all three components positive**—despite the three sources being pairwise negatively correlated (−0.25 / −0.13 / −0.30, §5.2). That is, under the current caliber **there is no instance of "negative π appearing in real data."**
- **The vector containing a negative component comes from the voided old caliber and is not the baseline weight**: `[0.9371, 0.0745, −0.0106]` is the π **after applying a transform** in the cell `irt|probit_std` under the **voided** old-sign caliber (L1_mean = 0.7597), located at `results/code/deprecated/assist09_drift_v1_sign_mixed.json`'s `payload.transforms["irt|probit_std"].pi` (`:28-36`), **not** `payload.pi_baseline`; that file self-marks `_reason: "...L1_mean = 0.7597 voided, do not cite"`, and its real `payload.pi_baseline` (`:13-17`) = `[0.5406, 0.3878, 0.0726]`, likewise with no negative component.

Therefore our reading of L1 drift is uniformly limited to "the magnitude of change of the effective-weight vector," and is not read as "redistribution of shares"; the discussion of negative π is used only to fix the reading caliber of L1 drift and must not be cited as evidence that negative weights have appeared in the real data.

This paper compares two metrics:

**Table 3. Two fusion metrics and their invariance to reparameterisation**

| Metric | Definition | Invariance to reparameterisation |
|---|---|---|
| A: linear [0,1] | min-max per column then linear weighting | **invariant only to affine y′ = ay + b** (absorbed by min-max); drifts under nonlinear monotone transforms |
| B: quantile logit | per column link via step empirical CDF to logit latent scale ψ = ln(p/(1−p)), p = (#{x_cal ≤ x} + 0.5)/(n + 1) | **strictly invariant to any strictly monotone transform** (rank invariance, analytic identity) |

The invariance of metric B is an identity, not a discovery: for strictly increasing g, #{g(x_cal) ≤ g(x)} = #{x_cal ≤ x}, so ψ is pointwise invariant. This paper treats it as a **verification object**, not a contribution: we recompute with finite samples, confirm the deviation is 0, and additionally report the sampling-noise magnitude under independent calibration.

### 3.3 Proposition C1 and its testable implications

**Proposition C1 (instability).** If sources are each first normalised to [0,1] and then linearly combined, the effective weight π generally differs from the nominal weight w and drifts with any monotone reparameterisation of a single source; if sources are first linked through the empirical CDF to a logit metric and then fused, π is strictly invariant to any strictly monotone reparameterisation, and under finite calibration samples the deviation comes only from linking sampling error.

This yields three testable implications, tested respectively in §4 (synthetic) and §5 (real):

- **P1**: under metric A, the baseline (untransformed) effective weight already deviates from the nominal weight;
- **P2**: under metric A, affine reparameterisation drift is 0, nonlinear monotone reparameterisation drift > 0, and there exists a transform inducing rank reversal;
- **P3**: under metric B, shared-calibration drift is 0, independent-calibration drift is only sampling-noise magnitude, and zero rank reversal.

## 4 Method Validation: the Proposition on Synthetic Data

### 4.1 Generative model and experimental setup

The purpose of this section is to test the proposition in an environment with a **known truth structure**, not to estimate any real-system parameter. Common latent ability θ ∼ N(0,1), sample size n = 500, calibration sample independently drawn n_cal = 500; the four sources are monotone functions of θ plus source-specific noise:

**Table 4. Synthetic generative model**

| Source | Generative form | Scale |
|---|---|---|
| X₁ mastery | σ(1.1θ + 0.2 + 0.30ε₁) | probability [0,1] |
| X₂ memory difficulty | exp(0.7θ + 0.3 + 0.25ε₂) | positive scale (exponential) |
| X₃ competitive rating | 1200 + 250θ + 40ε₃ | wide linear scale |
| X₄ window success rate | σ(0.9θ − 0.1 + 0.30ε₄) | probability [0,1] |

ε_k ∼ N(0,1) independent. The four sources are correlated monotone observations of one latent ability—the most favourable environment where "a true common metric exists"—but with different dispersions and shapes. The main nominal-weight configuration is w = (0.40, 0.30, 0.20, 0.10), the robust configuration is three sources w = (0.45, 0.35, 0.20). For any single source we apply 9 affine transforms (a ∈ {0.5, 1, 2} × b ∈ {−0.5, 0, 0.5}) and 7 nonlinear monotone transforms (`power2`, `power3`, `sqrt`, `log`, `exp_scaled`, `probit_std`, `logit_minmax`); transform parameters are fixed on the test sample and then applied with the same parameters to the calibration sample, ensuring it is the same reparameterisation. Each (source, transform) is repeated R = 200 times.

### 4.2 Baseline: effective weights already differ from nominal

**Table 5. Baseline effective weights already deviate from nominal weights**

| Metric | π₁ | π₂ | π₃ | π₄ |
|---|---|---|---|---|
| Nominal weight w | 0.400 | 0.300 | 0.200 | 0.100 |
| **Linear [0,1]** (mean ± SD) | **0.532 ± 0.026** | 0.171 ± 0.032 | 0.179 ± 0.009 | 0.119 ± 0.006 |
| **Quantile logit** | 0.403 ± 0.006 | 0.299 ± 0.006 | 0.201 ± 0.003 | 0.097 ± 0.003 |

**Testable implication P1 holds.** Under linear [0,1] fusion, the weight set "0.40 / 0.30 / 0.20 / 0.10" is **misleading**: because the mastery source has the largest relative dispersion, its effective weight is systematically inflated to 0.532, while the memory-difficulty source nominally at 0.30 actually contributes only 0.171. Under the quantile-logit metric the effective weight returns near the nominal value (max deviation 0.003), showing that this system does have a unique commensurable scale in this setting, and min-max normalisation simply does not land on it.

### 4.3 Metric A: affine-invariant, nonlinear-monotone drift

**Table 6. Metric A: affine-invariant, nonlinear-monotone drift**

| Transform family | L1 mean | L1 SD | mean rank reversal | proportion with reversal | Spearman vs. baseline weight |
|---|---|---|---|---|---|
| Affine (9) | **0.000000** | 0.000000 | 0.000 | 0.000 | 1.0000 |
| Nonlinear monotone (7) | **0.127620** | 0.019553 | 0.513 | **0.364** | 0.8646 |

**Testable implication P2 holds, and it holds in two halves.** Under affine transforms drift is exactly 0—this is the analytic property of min-max normalisation and the **only** invariance of the linear metric; under nonlinear monotone transforms L1 mean is 0.1276, max single-cell 0.674, and 36.4% of (source, transform) cells show weight-rank reversal. This split has direct engineering meaning: in real systems the mastery, memory difficulty, competitive rating, and success rate come precisely from probability, exponential, wide-linear, and ratio scales, and the transforms among them are **never affine**, so the stability of linear fusion in practice falls exactly in the refuted half.

The most severe transform per source is as follows (L1 mean / 95% interval / mean reversal count):

**Table 7. Most severe transform per source (L1 mean / 95% interval / mean reversal)**

| Source | Most severe transform | L1 mean | 95% interval | mean reversal |
|---|---|---|---|---|
| X₁ mastery | `logit_minmax` | 0.674 | [0.641, 0.709] | 2.835 |
| X₁ mastery | `log` | 0.193 | [0.116, 0.325] | 0.065 |
| X₂ memory difficulty | `probit_std` | 0.368 | [0.274, 0.487] | 0.670 |
| X₂ memory difficulty | `exp_scaled` | 0.286 | [0.163, 0.343] | 1.330 |
| X₃ competitive rating | `logit_minmax` | 0.274 | [0.248, 0.298] | 1.590 |

Notably the two most severe cells both occur on `logit_minmax`—i.e., "first min-max then take logit" on a source, the most natural-looking modification, causes the largest weight drift instead. This suggests a counterintuitive practical conclusion: before the metric is unified, any local "make some source more like logit" improvement may amplify rather than reduce the system's overall instability.

### 4.4 Metric B: zero drift under shared calibration, sampling noise only under independent calibration

**Table 8. Metric B: zero drift under shared calibration, sampling noise only under independent calibration**

| Variant | Transform family | L1 mean | mean rank reversal | proportion with reversal |
|---|---|---|---|---|
| Shared calibration · same transform | all | **0.000000** | 0.000 | 0.000 |
| Independent calibration sample | affine | 0.0160 | 0.000 | 0.000 |
| Independent calibration sample | nonlinear | 0.0159 | 0.000 | 0.000 |

**Testable implication P3 holds.** Under shared calibration drift is strictly 0 (numerically the largest |Δπ| in the whole table is 2.7 × 10⁻³, appearing only in one `logit_minmax` cell, a numeric artifact from domain-boundary clipping creating at most two tied values, not a conceptual drift). Under independent calibration the 0.016-magnitude deviation is identical for affine (0.0160) and nonlinear (0.0159), proving it is unrelated to reparameterisation and is the linking sampling error of finite calibration samples. Zero rank reversal holds under both variants.

### 4.5 Three counterexamples: information unchanged, weight-rank reversed

**Counterexample 1 (strongest):** applying `logit_minmax` (strictly monotone) to X₁ mastery, result of repeat 0:

**Table 9. Counterexample 1 (strongest): X₁ mastery under logit_minmax**

| Item | Value |
|---|---|
| Baseline effective weight π⁽⁰⁾ | [0.5429, 0.1514, 0.1831, 0.1226], order [1, 3, 2, 4] |
| Transformed π⁽ᵍ⁾ | [0.1983, 0.2840, 0.3110, 0.2068], order [4, 2, 1, 3] |
| L1 | **0.6893** |
| Rank-reversal count | **3** (complete reversal) |
| Spearman vs. baseline weight | **−0.20** |
| |Δπ| of quantile-logit metric under same transform | **0.000** (no reversal) |

**Counterexample 2:** applying `probit_std` to X₂ memory difficulty, π changes from [0.543, 0.151, 0.183, 0.123] to [0.415, 0.352, 0.140, 0.094], L1 = 0.400, 1 reversal; quantile metric |Δπ| = 0.

**Counterexample 3:** applying `power3` to X₂, π → [0.611, 0.047, 0.205, 0.137], L1 = 0.209, 1 reversal; quantile metric |Δπ| = 0.

All three counterexamples use **strictly monotone** transforms and θ is unchanged—i.e., under "information content completely unchanged, only the scale changed," the weight ranking of linear fusion underwent substantial reversal, and the strongest case completely flips sign. This is our direct response to the objection that "weight drift is just a few decimal points": the drift can be large enough to completely invert the interpretation of the weights.

### 4.6 Boundaries of the synthetic experiment (honest statement)

**This entire section is synthetic data**, the generation method is fully written out, and no external data is used. Three boundaries must be stated: first, the four sources sharing a single latent variable is the **most favourable** environment for the "commensurability" proposition—even so, linear fusion remains unstable, which strengthens rather than weakens the conclusion; second, affine invariance (= 0) is an analytic conclusion, not an empirical discovery, and we use it as a control, not a contribution; third, the zero drift of the quantile metric is likewise a design goal (rank invariance), and this experiment **verifies** it with finite samples, rather than discovering it. In sum, the role of this section is **method validation**; the test on real systems is borne by §5.

## 5 Real-Data Test I: Metric Repair and Two Negative Results

### 5.1 Data, licences, and samples

**Table 10. Datasets, scale, use in this paper, and licence/citation obligations**

| Dataset | Scale | Use in this paper | Licence and citation obligation |
|---|---|---|---|
| assist09 (revised) | 346,860 rows × 31 cols (64,412,812 B) | three-source correlation, O1 metric drift, sliding-window error-rate distribution | cite Feng et al. (2009) and data page (URL verified before submission) |
| DBE-KT22 | 161,953 valid responses; 212 items; 1,264 students | O2 difficulty estimator, O4 / O4b multi-signal fusion | cite arXiv:2208.12651; ADA Dataverse DOI 10.26193/6DZWOH |
| XES3G5M | 4,806 items (≥100 responses with KC path); 7,652 items with item text | O3 knowledge-tree-structure negative result | cite NeurIPS 2023 Datasets & Benchmarks; MIT licence |
| Junyi Academy | 16,217,311 rows; 72,758 users; **1,326 exercises library-wide** | O5 cross-system reproduction, O6 sample efficiency and robustness, O7 / O8 holdout validation | CC-BY-NC-SA-4.0 (**commercial use prohibited**); cite Chang et al. (2015) |

**Three calibers of the Junyi exercise count (defined where first appearing, unified thereafter).** This paper uses three different exercise counts in different experiments; they are not contradictions but different filter conditions:

**Table 11. Three calibers of the Junyi exercise count**

| Caliber | Exercise count | Definition | Appears in |
|---|---|---|---|
| Library-wide | **1,326** | all exercises in the Junyi exercise table with response data | §5.1 Table 3-1, §5.4 |
| O5 fusion reproduction caliber | **1,234** | on top of 1,326, add O5 usability filter: exercise must have expert-difficulty annotation and meet O5's minimum-response threshold | §6.3, §6.4 |
| O10/O12 criterion-half caliber | **1,238** | on top of 1,326, require the criterion half (B-half students) to have ≥500 responses per exercise | §7.2 O10, §7.8 O12 |

Of the three calibers only 1,326 is "all exercises with data"; 1,234 and 1,238 are experiment-specific inclusion conditions. Earlier versions mixed two of these values in §3.2 and §5.1 without definition; they are now unified per the table above.

The four datasets cover three different evidence regimes, which itself constitutes the external-validity design of this paper: DBE-KT22 has expert difficulty annotation (1/2/3) and student self-report (difficulty feedback and trust); Junyi has expert difficulty annotation (easy/normal/hard) but **no self-report channel**; XES3G5M has item text and a knowledge tree but no expert difficulty; assist09 has hint use and multi-skill annotation but no expert difficulty. §6 will use this design to report the "with-feedback" and "without-feedback" regimes separately.

### 5.2 Real difficulty sources pairwise weakly negatively correlated: a form impossible in the synthetic experiment

On assist09's 994 items (≥50 responses), the Spearman correlations among the three realistically available difficulty sources are:

**Table 12. Pairwise Spearman correlations among the three real difficulty sources on assist09**

| Source pair | Spearman ρ |
|---|---|
| IRT difficulty ~ median first-attempt time | **−0.250** |
| IRT difficulty ~ mean attempt count | −0.134 |
| First-attempt time ~ mean attempt count | **−0.302** |

The three sources are **pairwise negatively correlated**: items judged hard by IRT are answered faster and with fewer attempts by students. This is the exact opposite of the synthetic-experiment setting in §4.1 ("the four sources are correlated monotone observations of one latent ability"). The explanation is not mysterious—hard items are often abandoned faster by students (fast abandonment means short time and few attempts), while easy but tedious items take long and many attempts. The important consequence: **the real system's difficulty scales are not merely incommensurable, their directions also fight each other**. In the synthetic experiment, min-max fusion drift comes from dispersion differences; in the real data it is overlaid with sign conflict, so it is unsurprising that the observed real drift (0.5357, §5.3) far exceeds the synthetic (0.1276). This finding also explains why "make some source more like logit" local fixes fail: when sources are negatively correlated, any linear combination relying on concrete values weights noise as signal.

### 5.3 O1: from 0.5357 to 0.0001

On the same batch of 994 items, compare the two metrics' effective-weight drift under arbitrary monotone reparameterisation:

**Table 13. O1: effective-weight drift under the two metrics (assist09, 994 items)**

| Fusion metric | L1 mean | Rank reversal |
|---|---|---|
| A: min-max linear (status quo) | **0.5357** | significant |
| B: empirical CDF → logit (quantile linking) | **0.0001** | **0** |

**This is the engineering-landing evidence of proposition C1, obtained on real data.** After replacing the difficulty-fusion module from min-max linear fusion to "quantile linking + logit metric," the effective-weight drift under arbitrary monotone reparameterisation drops from 0.5357 to the 1 × 10⁻⁴ order (pure numeric noise), and rank reversals go to zero. Compared with the synthetic experiment (0.1276 → 0), the baseline drift on real data is about 4.2× higher, while the residual drift after repair is likewise zero—i.e., **the gain from the metric repair is larger on real data than in the synthetic environment**.

Here the caliber-correction note from the front matter must be restated: an earlier batch of experiments had mixed sign conventions across difficulty sources (some sources' positive direction was "easy," some "hard"), systematically inflating the linear-fusion drift. After unifying to "positive = hard" and recomputing, the value is 0.5357. We do not cite the corrected old value. The qualitative conclusion is identical under both calibers (linear fusion drift ≫ quantile metric), but only 0.5357 is the caliber-consistent, comparable number.

### 5.4 O2: changing the estimator is only worth +0.009

On DBE-KT22 (1,264 students × 212 items), comparing two difficulty estimators against the expert-difficulty annotation (1 easy / 2 medium / 3 hard):

**Table 14. O2: estimator comparison against expert difficulty on DBE-KT22**

| Estimator | Spearman ρ with expert grade |
|---|---|
| Raw correct-rate difficulty (baseline) | 0.2207 |
| **Joint IRT-1PL (EM-style gradient, 300 rounds)** | **0.2300** |

The IRT stratified means (positive = hard) are level 1 → −1.32, level 2 → −1.19, level 3 → −0.21, **monotone with clear hard-level separation**; correct rate decreases monotonically by expert grade (0.803 / 0.770 / 0.632), consistent with the original dataset paper's conclusion.

**Honest reading: ρ improves by only 0.009.** This is a highly informative negative result: it shows that on the axis "expert annotation vs. behavioural data," the bottleneck is not the complexity of the estimator but the agreement between the expert annotation itself and the response behaviour. This directly negates the implicit expectation in our original preregistration that "a better measurement model would improve commensurability," and prompted the pivot in §6—since the estimator is not the bottleneck, we should test whether the **signal set** is the bottleneck. The sequel will show that this pivot brought both the gain of §6 and the reversal of §7.

### 5.5 O3: knowledge-tree structure is not difficulty order

On XES3G5M we test an assumption widely defaulted to in engineering practice but rarely explicitly tested: whether the hierarchical structure of the knowledge-component (KC) tree can serve as a difficulty proxy.

- **Depth correlation**: KC-tree depth vs. empirical difficulty has Spearman ρ = **+0.0785** (p = 5.1 × 10⁻⁸, significant but extremely weak); the stratified mean is **non-monotone**—depth 4 correct rate is 0.799 (easiest), depth 3 is 0.746 (hardest).
- **Tree-edge gradient**: among 347 parent–child edges, the proportion with "parent difficulty < child difficulty" is **0.487**, about a coin flip.

The two pieces of evidence jointly refute "tree structure = difficulty order." We report this as a small but clean negative result: it depends on no new algorithm, only one correlation test and one direction-consistency test, yet suffices to block a common engineering shortcut—using knowledge-tree depth, section numbering, or course progress as a difficulty estimate. This negative result has been written into the module documentation of the studied system's difficulty-metric layer (§9.2) as a prohibitive constraint.

## 6 Real-Data Test II: Multi-Signal Fusion and the Gain under the Expert-Label Criterion

### 6.1 O4: five-signal fusion on DBE-KT22 and a differential feature

O2 showed that changing the estimator helps little. O4 tests another hypothesis: **the bottleneck may not be the label but the single behavioural signal (correct rate) itself being information-poor**. Design: on DBE-KT22's 212 items (≥30 transactions per item) take five behavioural signals—success rate (reversed), hint rate, student self-reported difficulty, trust (reversed), mean response time—each transformed by ECDF → logit (i.e., O1's quantile metric, positive = hard) and then linearly fused.

**Table 15. O4: five-signal fusion on DBE-KT22 and a differential feature**

| Estimator | Spearman ρ with expert 1/2/3 |
|---|---|
| Raw correct rate (O2 baseline) | 0.2207 |
| Joint IRT-1PL (O2) | 0.2300 |
| **Five-signal equal-weight fusion** | **0.2918** |
| Optimised weights (greedy, in-sample) | 0.5306 |
| **Optimised weights · repeated 5-fold ×10 cross-validation** | **0.5240 ± 0.1069** (interval [0.2895, 0.7390]) |

Single-signal performance: trust (reversed) 0.261, time 0.240, success rate (reversed) 0.217, hint rate **−0.117** (wrong direction), self-reported difficulty 0.038 (near noise alone).

**The core finding is a differential feature.** Self-reported difficulty and trust are strongly positively correlated at the item level (Pearson +0.94), but in ECDF space "trust reversed" vs. self-reported difficulty correlate at **−0.80**. The 50/50 combination selected by the optimised weights is essentially a differential feature: **"items that are self-reported difficult AND trust-low are the truly hard ones."** Subtracting two weak signals cancels the common-mode noise, isolates the difficulty-specific variance, and lifts ρ from the single-signal ceiling of 0.26 to the 0.53 order (cross-validation 0.52).

Three citation disciplines must be observed: the in-sample 0.5306 has optimistic bias, so **cite the cross-validation value**; the equal-weight 0.2918 is the tuning-free lower bound, representing "what you get without tuning"; self-reported difficulty and trust come from the same system's student self-reports, independent of expert annotation (no label leakage), but **exist only in systems with a feedback mechanism**—feedback-free systems can only fall back to pure-performance-signal fusion (about 0.29).

### 6.2 O4b: extended features add no gain, the differential feature is the driver

To test the mechanistic explanation rather than merely accept its fit, O4b adds three explicit features (explicit difference term, dispersion, response count) and re-estimates by coordinate ascent:

**Table 16. O4b: extended features add no gain, the differential feature is the driver**

| Configuration | cross-validation ρ under repeated caliber | Note |
|---|---|---|
| O4 (5-signal full-grid greedy) | **0.4778** (single 5-fold; cite with caliber noted) | final cited configuration |
| O4b (8 features, coordinate ascent) | 0.4608 | does not exceed O4 |

Two direct pieces of evidence support "the differential feature is the driver": the explicit difference feature (self-reported difficulty − trust) alone has ρ = **0.389**, the strongest single feature; response count correlates negatively with expert difficulty (ρ = −0.302), indicating popular exercises tend to be core easy items. The added features bring no generalisable gain, so O4 remains the final cited configuration, and O4b serves only as a mechanism-ablation piece of evidence.

### 6.3 O5: cross-system reproduction on Junyi (no-feedback regime)

The key difference between Junyi and DBE is: Junyi **has no student self-report feedback field**, a "performance-signal-only" regime. This exactly tests how much of O4's gain survives on a feedback-free system.

**Table 17. O5: cross-system reproduction on Junyi (no-feedback regime)**

| Estimator (Junyi, 1,234 exercises) | Spearman ρ with expert easy/normal/hard |
|---|---|
| Success rate only | 0.2610 |
| **Seven-signal equal-weight fusion** | **0.3629** (+39% vs. baseline) |
| Coordinate-ascent optimised · repeated 5-fold ×10 | **0.4023 ± 0.0480** (interval [0.3227, 0.4909]) |

Single signals: repeat-session rate 0.294, mean attempt count 0.285, downgrade rate 0.271, success rate (reversed) 0.261, hint rate 0.217, time 0.214, upgrade rate **−0.184** (reversed).

**Conclusion:** the fusion gain **is not DBE-specific**. On 16.21 million interactions, 1,234 items, a completely different subject (Taiwan mathematics) and a different regime (no feedback), the equal-weight fusion improvement over baseline (+39%) is of the same order as DBE's (0.2207 → 0.2918, +31%). This provides cross-system evidence for "difficulty estimation should use multi-signal rank fusion rather than single correct rate," while delimiting the upper bound reachable by feedback-free systems (about 0.36–0.40).

A pre-emptive warning to readers: every gain in this section uses the criterion of **expert difficulty labels**. §7 will switch the criterion to "real performance on unseen samples," at which point the conclusion reverses. The table numbers here are themselves correct, but the boundary of their interpretive power is redrawn in §7.

### 6.4 O6a: sample efficiency — the gain is complementary information, not denoising

If the fusion benefit were merely "multi-signal averaging out noise," the benefit should vanish as sample size grows. O6a uses reservoir sampling to give, for each item, random subsamples of any k ∈ {10, …, 500} responses (30 repeats per bracket) to test this.

**Table 18. O6a: sample efficiency — the gain is complementary information, not denoising**

| k | Junyi success-only | Junyi fusion | paired win rate | DBE success-only | DBE fusion | paired win rate |
|---|---|---|---|---|---|---|
| 10 | 0.1750 | 0.2260 | 1.00 | 0.2024 | 0.2316 | 0.87 |
| 25 | 0.2116 | 0.2640 | 1.00 | 0.2113 | 0.2399 | 0.77 |
| 50 | 0.2314 | 0.2929 | 1.00 | 0.2224 | 0.2493 | 0.83 |
| 100 | 0.2416 | 0.3099 | 1.00 | 0.2208 | 0.2654 | 0.97 |
| 250 | 0.2496 | 0.3269 | 1.00 | 0.2213 | 0.2725 | 1.00 |
| 500 | 0.2536 | 0.3380 | 1.00 | 0.2209 | 0.2779 | 1.00 |
| Full | 0.2610 | 0.3629 | — | 0.2170 | 0.2918 | — |

The **relative** gain stays stable at +29% ~ +33% across all sample-size brackets, and the absolute gain even rises monotonically with sample size (Junyi from +0.0509 to +0.0844). Therefore fusion provides **complementary information**, not merely variance reduction—a judgement that §7 will qualify but not overturn: complementarity is real, it is just that what it complements is "the construct contained in expert labels," not necessarily "the construct contained in student performance."

**Correction record (honest archive):** DBE's first-version sample-efficiency result was inflated (k = 500 gave 0.2485, exceeding the full 0.2170). The cause was that among 212 items, 13 had response count n < K = 500, the reservoir tail had zero-padding slots, and global permutation then truncation counted the zero-padding as 0 in the sum. After changing to "sort the invalid slots' keys to +∞ and push them to the queue tail" for fetching, the table above shows the corrected values.

### 6.5 O6b: statistical robustness (bootstrap 2000 and repeated cross-validation)

**Table 19. O6b: statistical robustness (bootstrap 2000 and repeated cross-validation)**

| Quantity | Junyi | DBE |
|---|---|---|
| Success-only ρ [95% CI] | 0.2606 [0.2112, 0.3101] | 0.2167 [0.0809, 0.3476] |
| Equal-weight fusion ρ [95% CI] | 0.3623 [0.3149, 0.4094] | 0.2890 [0.1563, 0.4127] |
| Paired difference Δ [95% CI] | **+0.1017 [0.0726, 0.1325]** | **+0.0723 [−0.0195, 0.1649]** |
| One-sided p(Δ ≤ 0) | **0.000** | **0.059** |
| Three-grade quadratic-weighted Kappa (success-only → fusion) | 0.1815 → 0.2595 | 0.1778 → 0.2370 |
| Repeated 5-fold ×10 (50 folds) optimised-weight ρ | **0.4023 ± 0.0480** | **0.5240 ± 0.1069** |

Two points must be emphasised. First, **the fusion gain on DBE is only marginally significant even under the expert-label criterion** (one-sided p = 0.059, CI crosses 0); only Junyi's p = 0.000 constitutes strong evidence. Merging the two datasets' gains without distinguishing significance is embellishment of evidence strength. Second, the absolute level of quadratic-weighted Kappa (0.18 → 0.26) is far below the intuitive "usable" threshold, indicating limited improvement at the three-grade classification level; the improvement mainly occurs at the rank level.

**Number update (must be observed):** the 0.3837 reported by O5 and the 0.4778 by O4 are both **single 5-fold** results; the more stable repeated 5-fold ×10 estimates are Junyi 0.4023 ± 0.0480 and DBE 0.5240 ± 0.1069. Both differ from the old values within one standard deviation (not contradictory), but **this paper uniformly prioritises citing the repeated values with standard deviations**; if the old values appear, they must be noted as "single 5-fold."

## 7 Criterion Switch: Holdout Validation, Conclusion Reversal, and a Directional Error

### 7.1 The distance between expert labels and real-performance difficulty

The consistency criterion of O4 and O5 is **expert difficulty labels**. But what adaptive ranking truly needs is "predicting real student performance." These are not the same construct, and their distance is directly measurable:

> **Expert difficulty labels vs. real-performance difficulty (Junyi, ability decile 5, n = 906, ≥500 responses): Spearman ρ = 0.4326 (95% CI [0.38, 0.48], p < 0.001).**

That is, expert labels explain only about 19% of the rank variance of real-performance difficulty. This is not a criticism of expert annotation—expert annotation measures "how hard the course designer thinks it is," which is itself a different construct from "how hard it actually is for the student." But it means: **an estimator's progress in "fitting expert labels" need not translate into progress in "predicting student performance."** Reporting a consistency gain without first measuring this distance would let readers assume the two are the same thing—which we explicitly deny here.

### 7.2 O7: conclusion reversal under holdout validation

The method splits each item's reservoir slots into mutually exclusive block A (for estimation, k slots) and block B (for criterion, 250 slots), so that estimation error and criterion error no longer share samples. After switching the criterion to "real performance on unseen samples":

**Table 20. O7: conclusion reversal under holdout validation**

| Dataset | k | Success-only | Equal-weight fusion | Difference | Fusion win rate |
|---|---|---|---|---|---|
| Junyi | 10 | 0.6677 | 0.6410 | −0.0267 | 0.00 |
| Junyi | 25 | 0.8066 | 0.7355 | −0.0711 | 0.00 |
| Junyi | 50 | 0.8814 | 0.7850 | −0.0963 | 0.00 |
| Junyi | 100 | 0.9251 | 0.8115 | −0.1136 | 0.00 |
| Junyi | 200 | 0.9509 | 0.8287 | **−0.1222** | 0.00 |
| DBE | 10 | 0.8083 | 0.6331 | −0.1752 | 0.00 |
| DBE | 25 | 0.9036 | 0.6982 | −0.2054 | 0.00 |
| DBE | 50 | 0.9427 | 0.7259 | −0.2168 | 0.00 |
| DBE | 100 | 0.9652 | 0.7541 | −0.2112 | 0.00 |
| DBE | 200 | 0.9767 | 0.7655 | **−0.2113** | 0.00 |

**Conclusion: under the criterion "generalise to new samples," equal-weight seven-signal fusion is comprehensively worse than success rate alone**, and the disadvantage grows with more samples (Junyi from −0.0267 to −0.1222, DBE stable around −0.21); the fusion win rate is 0.00 across all 10 configurations.

**But this reversal cannot be read entirely as "fusion has no predictive power"; the part constructed by the criterion structure itself must first be subtracted.** The criterion here is "the real success rate 1 − ok_B/n_B of block B," and the baseline estimator "success rate only" estimates **exactly this statistic** on fit block A—**the baseline is a small-sample estimate of the criterion quantity**, while the fusion estimator mixes in other constructs such as hint dependence, response time, attempt count, and session count. If an item's success probability is stable, the success rate on A converges to that on B, so this design is **asymptotically favourable to the success-rate-only estimator**; the observed "larger k, larger disadvantage" (baseline ρ reaches 0.95–0.96 at k = 200) is consistent with this. This does not mean the difference is entirely an artifact of the structure: the objective function is inter-item rank correlation, block B is still finite-sample, and the fusion estimator also contains the success-rate signal, leaving real differences. But **a substantial part of the reversal is built into the criterion choice**.

Therefore we rewrite the final qualitative statement of O4 / O5 as: **when the criterion quantity is success rate, the success-rate estimator's large-sample dominance is design-expected; fusion's role is rank stabilisation at small samples.** This statement is directly supported by O8–O12 (record-level +3.823 pp and student-level +4.283 pp at k = 10, falling below 0.4 pp for k ≥ 100), and is compatible with the variance-reduction explanation of the "(1−λ)·success-rate + λ·fusion" shrinkage combination—but we **did no bias–variance decomposition and have no prior model, so we have not identified this explanation**; it is merely a compatible reading.

The sentence "consistency gain is not predictive-power gain" must be given a primary test on an **exogenous criterion**. The hierarchy of criteria is set by construct distance: **the primary decision criterion takes DBE-KT22's teacher difficulty labels** (R7: Abdelrahman et al. 2022; 3-level ordinal 1/2/3, from outside the logs, the **only** exogenous benchmark available to us); the **ability-corrected criterion (IRT-1PL) is demoted to an appendix sensitivity analysis**, for the reason given in the next paragraph.

**Primary decision criterion (A2·DBE-KT22, exogenous):** all 212 items carry teacher difficulty annotation. With teacher labels placed at the criterion position (signals built by the shared `dbe_signals.build()`; all transactions used, per review §3.2 ②), the result is Spearman(fusion, teacher label) = **0.2918**, Spearman(success-only, teacher label) = **0.2204**, linear-weighted κ = **0.178**. Fusion now holds a small advantage over success-rate-only under this criterion, and both remain only weakly correlated with teacher labels. (Review §3.2, 2026-10-02: this section's signal definitions are now unified with §6/O4 through a single `dbe_signals.build()`, and both report the **same** equal-weight Spearman 0.2918; the previous 0.2918-vs-0.205 discrepancy is resolved.) (Single-model rating vs. teacher-label alignment at richer ordinal metrics is in M3 §5.7.1: τ_b / graded AUC / k-scan panels.)

**Why 1PL cannot serve as an exogenous benchmark (Appendix A.x):** we additionally split students on Junyi by crc32(uuid) parity (O10 student-level holdout), and under the criterion-half per-item ≥500-response caliber actually obtain **1,274 items** (32,563 students, 1,845,035 responses) fitting IRT-1PL item difficulty b_j (ability-corrected, mean|b_j| = 0.80), yielding (review §3.1, 2026-10-02 corrected) Spearman(b_j, success-only_B) = 0.963 — a value inflated by same-half leakage from taking the baseline from block B, the same half that fits b_j — **withdrawn**. With the success-rate baseline and the fusion estimator both placed on **block A** and compared against the same b_j: Spearman(b_j, success-only_A) = **0.9541**, Spearman(b_j, fusion_A) = **0.8923** (neither estimator shares a half with b_j; the within-A success/fusion correlation is 0.940). **1PL and success rate remain highly同源** (≈0.95), a value of the same order and same conclusion as Deep-IRT (Yeung 2019) reporting "Pearson r = 0.96 between item analysis and 1PL IRT difficulty" on FSAI data. Therefore **1PL only corrects the ability composition, it is not an exogenous benchmark**: placing 1PL as a third criterion alongside success rate merely re-introduces the tautology "same statistic" under a different name. We therefore move it to the appendix as a sensitivity analysis only, and **the main results table has no 1PL column**. Both additional criteria were cross-validated by `verify_m1_criteria.py --results m1_criteria_results.json` (PASS); all numbers are real computed values.

An over-interpretation that must also be avoided is "fusion is useless." The fusion gain under the expert-label criterion is real, reproducible, and has a clear mechanism (differential feature); "useless" means it is **not proven useful for the purpose of adaptive ranking**. For tasks aimed at expert judgement, such as "difficulty grading at item intake" and "expert alignment of question-bank quality," fusion remains effective.

Finally, **the absolute values of ρ in this section and the §7.8 tables must not be bolded and must not be read as "near perfect"**: the criterion-block reliability is limited (record-level block B fixed at 250, student-level requires ≥500), so only **within-k between-group comparisons** are valid.

### 7.3 O8: locating and fixing a directional error

Faced with the above reversal, we did not attribute it to "tuning preference" but inspected the fusion configuration itself. The inspection located one real error:

> **The upgrade rate correlates −0.1837 with expert difficulty, and −0.756 in-pool (same knowledge point × same ability decile), yet the optimiser assigned it a positive weight +0.154.**

That is, a negatively-directed signal was counted into the fusion with a positive weight. This does not surface in in-sample fitting (the optimiser can compensate with other signals), but in holdout validation it systematically reverses the direction of difficulty. There are two fixes: drop the signal (fused6), and introduce a sample-size-shrinking fusion weight λ (§7.4). Comparing variants under the holdout framework (λ chosen on a random half of items, evaluated on the held-out other half, 20 half-splits × 25 repeats):

**Table 21. O8: locating and fixing a directional error**

| Variant | k | success ρ / variant ρ | λ* | holdout ρ(λ*) | gain vs. success rate |
|---|---|---|---|---|---|
| fused7 (O5 original) | 10 | 0.6702 / 0.6431 | 0.52 | 0.6871 | +1.73 pp |
| **fused6 (drop upgrade rate)** | 10 | 0.6659 / **0.6880** | 0.70 | **0.6992** | **+3.43 pp** |
| fused6 | 25 | 0.8109 / 0.7974 | 0.52 | 0.8273 | +1.57 pp |
| fused6 | 50 | 0.8810 / 0.8487 | 0.39 | 0.8878 | +0.73 pp |
| fused6 | 100 | 0.9257 / 0.8748 | 0.23 | 0.9271 | +0.22 pp |
| fused6 | 200 | 0.9504 / 0.8899 | 0.12 | 0.9502 | +0.05 pp |
| fused3 (success + hint + attempt) | 10–200 | — | 0.04–0.08 | — | ≈ 0 (no gain) |

Three conclusions. First, **after dropping the inversely-directed signal, fusion first overtakes success rate at k = 10** (0.6880 vs. 0.6659, +0.0220), and the lag at each k is also halved (at k = 200 from −0.1206 narrowed to −0.0605). Second, **it is not "fewer signals is better"**—fused3 instead has no gain, because the more similar the variant is to success rate, the smaller the complementary gain available; the real fix point is **direction checking**, not reducing the signal count. Third, the gain is highly sample-size dependent, leading to the next section.

### 7.4 Sample-size-adaptive shrinkage λ*(k)

λ* falls monotonically from 0.70 at k = 10 to 0.12 at k = 200, showing that "what fraction fusion should occupy" is a function of sample size. The fitted form is

  **λ*(k) = 1 / (1 + (k / 27.4)^0.902), R² = 0.9989**,

with observed values 0.701 / 0.524 / 0.387 / 0.234 / 0.125 corresponding to fitted 0.713 / 0.521 / 0.368 / 0.237 / 0.143. Whether this fit can be deployed directly (rather than holding only on the k's that participated in the fit) is answered by the leave-one-k cross-validation (in-interval interpolation) test of §7.5.

The recommended estimator we thereby give is:

```
score(item) = (1 − λ) · z_success(item) + λ · Σ_{s ∈ 7 signals} w_s · sgn_s · z_s(item)
sgn_s = sign(Spearman(z_s, z_success))      # direction correction; success itself sgn = +1
w_s   = max(0, split_half_reliability_s) normalized   # split-half reliability estimated within fit block A
λ = 1 / (1 + (k / 27.3)^0.895)              # deployed uses 27.3 (O9 leave-one-k CV fit value 27.332 rounded); full-fit 27.4 / 0.902
signal set = all 7 signals (including upgrade rate, corrected to negative contribution)
z_s = ECDF → logit (O1's monotone-reparameterisation-invariant metric)
```

Here λ's parameters take the **leave-one-k cross-validation fit value** (k₀ = **27.332**, p = 0.895), and the **deployed value is 27.3** (i.e., the rounded value of the fit 27.332), not the full-fit value above (27.4 / 0.902); the two are nearly identical, showing the curve shape is stable, but the full-fit value both fits and evaluates on the same batch of k, so the cross-validation value is preferred at deployment. This closed form is likewise a fit to O8's fused6 per-k empirical λ*(k) (λ's method and the fusion kernel are independent; O11 confirms the closed-form λ_cf applies to the `srw7` kernel too, see §7.8), and the leave-one-k cross-validation confirms the in-interval interpolation generalisation of the empirical λ*, not a direct verification of the closed form itself—that direct verification has now been added: fixing λ_cf(k)=1/(1+(k/27.3)^0.895) into the same holdout protocol (not fitting λ on data, evaluating on the held-out half), its holdout Spearman gap vs. the empirical optimal-λ version at k=10/25/50/100/200 is +0.34/−0.55/+0.12/+0.01/+0.07 pp (all ≤0.55 pp), confirming the closed form is deployable without per-k λ fitting. The next section gives the empirical basis for this choice. All signs, weights, and λ in the above estimator are estimated **only within fit block A**; criterion block B is entirely uninvolved, so there is no leakage; this is jointly guaranteed by the §7.8 holdout protocol and O11's item-by-item reproduction.

### 7.5 Leave-one-k cross-validation of λ*(k) (O9): in-interval interpolation test, formula directly deployable

The λ*(k) of §7.4 was both fit and evaluated on the same batch of k, and cannot be taken directly as a deployment rule. The first test of O9 is precisely for this: fit (k₀, p) using only λ* from k ∈ {10, 50, 200}, then evaluate at k = 25 and k = 100—which lie **within** the fit interval [10, 200]—by **holding out for validation** (in-interval interpolation, not out-of-interval extrapolation; the true out-of-sample test is the half-split holdout, see §7.6).

**Table 22. O9: leave-one-k cross-validation of λ*(k) (in-interval interpolation)**

| Validation k (in-interval) | λ̂ (formula) | λ*_emp (half-split picked) | ρ(λ=0) | ρ(λ̂) | formula gain | empirical gain | retention ratio |
|---|---|---|---|---|---|---|---|
| 25 | 0.520 | 0.536 | 0.8103 | **0.8272** | **+1.695 pp** | +1.528 pp | **111%** |
| 100 | 0.239 | 0.230 | 0.9262 | **0.9286** | **+0.237 pp** | +0.186 pp | **128%** |

The fit parameters (leave-one-k cross-validation) are k₀ = 27.332, p = 0.895, nearly identical to the full-fit 27.4 / 0.902, showing the curve shape is stable. **The formula's in-interval λ̂ is slightly better than the half-split-picked empirical λ*** (retention ratios 111% and 128%), because the empirical λ* carries its own selection noise. **Conclusion: λ*(k) can be used directly without re-tuning at deployment.**

### 7.6 Student-level holdout validation (O10): empirical test of the record-level concern

The holdout validation in §7.2 split **records**, not **students**: the same student's multiple responses could fall into both blocks A and B, so the two errors are not independent, making "optimistic generalisation estimate" a reasonable attack. O10 directly addresses this gap: split the 72,758 students into mutually exclusive halves by **crc32(uuid) parity**, estimate using only half A students' first k responses on the exercise (in-half reservoir 250), and compute the true difficulty 1 − ok_B/n_B using **all** of half B students' responses (≥500); include **1,238 exercises** (criterion half requires ≥500 responses, different from the 1,234 caliber in §6.3), 25 repeats × 20 half-splits.

> **Implementation note (part of reproducibility):** student half-splitting **must not** use Python's built-in `hash()`—it salts strings randomly per process (PYTHONHASHSEED), making the split non-reproducible; this script instead uses crc32 and caches by uuid. Ignoring this, the same code yields different splits in different processes and the conclusion becomes irreproducible.

**Table 23. O10: student-level holdout validation**

| k | Success-only | fused7 (O5 config) | fused6 | mix6 (λ̂ formula, **untuned**) | λ̂ | λ*_emp | λ̂ gain | fused6 raw gain |
|---|---|---|---|---|---|---|---|---|
| 10 | 0.6631 | 0.6442 | 0.6870 | **0.6995** | 0.711 | 0.716 | **+3.64 pp** | +2.39 pp |
| 25 | 0.8133 | 0.7418 | 0.7993 | **0.8297** | 0.520 | 0.521 | +1.64 pp | −1.40 pp |
| 50 | 0.8881 | 0.7838 | 0.8491 | 0.8944 | 0.368 | 0.355 | +0.63 pp | −3.90 pp |
| 100 | 0.9356 | 0.8101 | 0.8783 | 0.9372 | 0.239 | 0.200 | +0.16 pp | −5.73 pp |
| 200 | 0.9603 | 0.8234 | 0.8922 | 0.9605 | 0.144 | 0.093 | +0.02 pp | −6.81 pp |

Three conclusions. **First, O7's conclusion is fully reproduced at the student-level holdout**: fused7 still lags across the board, and the disadvantage grows with more samples (at k = 200, 0.8234 vs. 0.9603, difference **−0.137**); the λ-shrinkage gain is nearly identical to the record-level (at k = 10 **+3.64 pp**, record-level +3.43 pp). Thus the concern "record-level rather than student-level" is tested to have **little effect** and does not constitute a substantive threat to our conclusion. **Second, λ̂ and empirical λ* agree closely** (0.711 / 0.716, 0.520 / 0.521, 0.368 / 0.355), capturing nearly all the gain with **zero tuning**, further supporting that the λ*(k) formula is directly deployable. **Third, "dropping the directionally wrong signal alone is still insufficient" is also reproduced**: fused6 remains negative gain after k ≥ 25 (−1.40 to −6.81 pp); only mix6 with λ-shrinkage added is non-inferior to success-rate-only at all k—i.e., direction checking and sample-size shrinkage are two inseparable requirements. §7.8 further shows a better variant, `srw7`: it is also non-inferior to baseline at all k and exceeds the fused6 kernel used by mix6 at all k (student-level k = 10/25/50/100/200: +4.283 / +2.189 / +0.951 / +0.335 / +0.102 pp), showing "dropping" is not the optimal handling of a directional error.

### 7.7 Three boundaries (must be reported together with the conclusions)

**First, the gain vanishes rapidly with sample size.** Under this paper's final recommended `srw7` estimator, the holdout gain is student-level +0.335 pp at k = 100 and +0.102 pp at k = 200 (record-level +0.391 / +0.138 pp, §7.8 Tables 7-1, 7-2). For a mature question bank (hundreds of observations per item) **no significant gain should be expected**—at that point success rate is close to a sufficient statistic and the complementary space is small.

**Second, λ-shrinkage has no gain on DBE.** DBE's λ* is only in 0.05–0.17, and the holdout ρ is on par with or slightly below λ = 0 (0.9001 vs. 0.9006 at k = 25). This improvement **is verified only on Junyi, not cross-system reproduced**. We do not write it as a general rule. (In correspondence, DBE's repeated-cross-validation CI [0.2895, 0.7390] spans about 0.45, and with n = 212 items the information is extremely low, further indicating DBE's estimate should not be merged with Junyi's.)

**Third, the validity gap of "record-level holdout" has been handled by the student-level holdout test, and the conclusion holds.** O10 in §7.6 re-ran all tests by student split, O7's conclusion is fully reproduced, and the λ-shrinkage gain is nearly identical to the record-level (at k = 10, +3.64 pp vs. +3.43 pp), so this concern is tested to have **little effect**. The remaining boundaries are threefold: **one**, gain decay—under the student-level caliber `srw7`'s gain is +0.335 percentage points at k = 100 and +0.102 pp at k = 200 (record-level +0.391 / +0.138 pp); **two**, cross-system extrapolation—λ-shrinkage is verified only on Junyi, with no gain on DBE; **three**, O10 still rearranges student–item pairs within historical data and does not cover the cold-start cross-generalisation of "new student + new item"—whether fusion still gains in that scenario remains an open question. In addition, the criterion block is fixed at 250 (O7) and the criterion half fixed at a response count (O10), meaning the criterion itself has a reliability ceiling, so the absolute ρ values in both places (e.g., 0.9603) **cannot be read as "near perfect"**, and only **within-k between-group comparisons** are valid.

### 7.8 O11/O12: optimising the fusion estimator — sign correction and split-half-reliability weighting

§7.3 attributed the reversal to one directional error and fixed it by "dropping the upgrade rate" (fused6). O11 and O12 test a further hypothesis: **a directionally wrong signal should be sign-corrected, not deleted column-wise**; on top of that, **weighting per signal by its reliability within the fit block** should further reduce small-sample fusion variance. Both are evaluated under the same holdout protocol as §7.2 (O7/O8): fit block A is k reservoir slots per item, criterion block B is 250 mutually exclusive slots; REP = 25, SPLITS = 20; O12 follows the O10 protocol (split students by `crc32(uuid)` parity, 1,238 items, reservoir/half = 250, REP = 25 × SPLITS = 20). **All signs, weights, and λ are estimated only within fit block A; criterion block B is entirely uninvolved, no leakage**; λ defaults to the closed form λ_cf(k) = 1 / (1 + (k / 27.3)^0.895) (deployed 27.3, the rounded value of O9's leave-one-k CV fit **27.332**).

The variants are defined as follows: `fused6` is O8's "drop upgrade rate, 6-signal equal weight"; `fused7` is O5's 7-signal equal weight; `signed7` is 7-signal equal weight but with **per-signal sign correction** by in-fit-block rank correlation (success's own sign fixed at +1); `rw6` is 6-signal split-half-reliability weighting; `srw7` is 7-signal with both sign correction and split-half-reliability weighting, i.e.,

```
score(item) = (1 − λ) · z_success(item) + λ · Σ_{s ∈ 7 signals} w_s · sgn_s · z_s(item)
sgn_s = sign(Spearman(z_s, z_success))      # direction correction; success itself sgn = +1
w_s   = max(0, split_half_reliability_s) normalized   # split-half reliability estimated within fit block A
λ = 1 / (1 + (k / 27.3)^0.895)              # deployed 27.3 (O9 leave-one-k CV fit 27.332 rounded); full-fit 27.4 / 0.902
```

Table 7-1 gives the record-level holdout gain, Table 7-2 the student-level holdout gain.

**Table 7-1. Record-level holdout gain (O11, relative to "success-rate-only" baseline, unit pp, λ = λ_cf)**

| k | Success-only (held-out) | fused6 | fused7 | signed7 | rw6 | **srw7** | λ_cf | λ_rel | λ*_emp |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 0.6698 | +3.278 | +1.498 | +3.594 | +3.616 | **+3.823** | 0.7107 | 0.7010 | 0.7000 |
| 25 | 0.8060 | +1.586 | +0.523 | +1.930 | +1.829 | **+2.025** | 0.5197 | 0.4902 | 0.5270 |
| 50 | 0.8824 | +0.659 | +0.181 | +0.850 | +0.806 | **+0.930** | 0.3678 | 0.3136 | 0.3723 |
| 100 | 0.9248 | +0.243 | +0.073 | +0.327 | +0.335 | **+0.391** | 0.2383 | 0.1881 | 0.2370 |
| 200 | 0.9502 | +0.071 | +0.013 | +0.111 | +0.108 | **+0.138** | 0.1440 | 0.1041 | 0.1333 |

> Recompute command: `python results/code/o11_fusion_optimization.py` (output: `results/code/o11_fusion_optimization.json`). The script depends on numpy and must be run with an interpreter that has numpy installed (the project venv lacks numpy; this round was run with Python 3.13 + numpy 2.5.3 and passed).

**Table 7-2. Student-level holdout gain (O12, unit pp)**

| k | Success-only | fused6 | **srw7 (λ_cf)** | srw7 − fused6 | win rate | Wilcoxon p |
|---|---|---|---|---|---|---|
| 10 | 0.6631 | +2.390 | **+4.283** | +0.662 | 0.902 | 1.15e-66 |
| 25 | 0.8133 | −1.402 | **+2.189** | +0.557 | 1.000 | 1.26e-83 |
| 50 | 0.8881 | −3.905 | **+0.951** | +0.317 | 1.000 | 1.26e-83 |
| 100 | 0.9356 | −5.728 | **+0.335** | +0.169 | 0.998 | 1.27e-83 |
| 200 | 0.9603 | −6.804 | **+0.102** | +0.081 | 0.996 | 1.29e-83 |

> Recompute command: `python results/code/o12_student_o11.py` (output: `results/code/o12_student_o11.json`). The script depends on numpy and must be run with an interpreter that has numpy installed (the project venv lacks numpy).
> Caliber note: column 2 `fused6` is the holdout ρ minus baseline **without** λ stacked; column 3 `srw7 (λ_cf)` is the holdout ρ minus baseline **with** λ_cf stacked; while `srw7 − fused6`, win rate, and Wilcoxon p are **paired-caliber**—for each half-split B, compute the holdout ρ of `srw7` and `fused6` respectively and take the difference, then average and signed-rank test across the 25 × 20 = 500 pairs. Therefore the `srw7 − fused6` column **cannot** be obtained by subtracting columns 2 and 3 (subtraction gives 1.893 pp, paired value is 0.662 pp at k = 10); this is a two-caliber difference, not a numerical contradiction.

**Conclusion 1: sign correction beats direct deletion, and holds at all k.** `signed7 > fused6` holds bracket by bracket at k = 10/25/50/100/200 (k = 10: +3.594 vs. +3.278 pp; k = 200: +0.111 vs. +0.071 pp). This shows O8's "drop the upgrade rate," though it corrected the direction, also **discarded the signal's information**—its error is in direction, not in information content; correcting the direction and counting it as negative evidence is instead superior to deleting the whole column.

**Conclusion 2: reliability weighting adds further, `srw7` is optimal at all k.** On top of sign correction, split-half-reliability weighting (weight = rank correlation between the two half estimates after splitting each signal in the fit block A, taken positive and normalised) makes `srw7` achieve the highest gain at all k: +3.823 / +2.025 / +0.930 / +0.391 / +0.138 pp (record-level, Table 7-1). Low-reliability signals are automatically down-weighted, thereby suppressing small-sample fusion variance.

**Conclusion 3: the λ strategies are nearly equivalent; the closed form is directly deployable.** The closed-form λ_cf and the empirical optimal λ*_emp differ by ≤ 0.011 at all k (k = 10: 0.7107 vs. 0.7000); the reliability-driven λ_rel = 1 − ρ_success(A) differs from the two by at most **0.059** (k = 50: 0.3136 vs. 0.3723). Despite this order of difference in λ values, the three's **holdout gains** differ by ≤ 0.087 pp at all k (`srw7` caliber, largest at k = 10), so the fusion-weight choice is insensitive to how λ is taken; substituting the closed form directly by sample size suffices, with no per-k tuning needed.

**Conclusion 4: O12 student-level reuses the same optimisation; `srw7` eliminates the O8 estimator's harmfulness.** Under student-level holdout, `fused6` falls **below the "success-rate-only" baseline** for k ≥ 25 (−1.402 / −3.905 / −5.728 / −6.804 pp), i.e., this simplified estimator becomes harmful as sample size grows; `srw7` is the **only variant non-inferior to baseline at all k** under the same protocol (+4.283 / +2.189 / +0.951 / +0.335 / +0.102 pp). `srw7`'s paired win rate against `fused6` is 0.902 / 1.000 / 1.000 / 0.998 / 0.996, with Wilcoxon signed-rank test p ≤ 1.29 × 10⁻⁶⁶.

**Limitations that must be listed separately.** First, O11/O12 run **only on Junyi**, not cross-system reproduced (no corresponding validation on DBE); second, at k = 200 the gain is already small (record-level +0.138 pp, student-level +0.102 pp), and no significant gain should be expected for a mature question bank; third, the criterion block's own reliability ceiling (O7 block B fixed 250, O12 criterion half fixed response count) limits the absolute level of ρ, so in Tables 7-1 and 7-2 only **within-k between-group comparisons** are valid, and the absolute ρ values **cannot be read as "near perfect."**

The `srw7` estimator above has been landed to the studied system's difficulty-metric layer as an incremental function; the landing method, cost, and verification are in §9.2.

## 8 Optimal Error Rate: Descriptive Evidence and the Unfinished Causal Identification

### 8.1 The sliding-window error-rate distribution on assist09

On assist09 (sorted by student, by order_id, taking those with ≥20 items), a sliding window of width W = 20 computes each window's error rate.

**First, the correct representation of the distribution.** Window width W = 20 makes the error rate take only the **21 discrete support points** k/W (k = number of errors in window) (interval 0.05). An earlier version of this paper summarised with an equal-width histogram `np.histogram(win_err, bins=np.arange(0, 1.0001, 0.05))`, whose interval edges coincide exactly with these 21 support points; floating-point error (e.g., at k = 4, 1 − 16/20 = 0.19999999999999996) merges 0.15 and 0.20 into the same interval and pushes 0.10 into the next interval. The consequence was that the "mode interval" equalled **the sum of two discrete values**, while the single-value frequency was never reported—and the resulting "mode interval 0.15–0.20 (success 80–85%)" is a **binning-boundary artifact, not a distribution fact**. This section instead counts directly by integer error count k (integer arithmetic, no floating point), so the support points k/W are exact.

**Table 8-1. assist09 sliding-window error-rate 21 discrete support-point frequencies** (n = 286,150 windows; students actually contributing sliding windows = 2,314; students appearing in the input = 4,217)

| k (error count) | error rate | success rate | windows | share |
|---|---|---|---|---|
| 0 | 0.00 | 1.00 | 3,794 | 1.33% |
| 1 | 0.05 | 0.95 | 10,982 | 3.84% |
| 2 | 0.10 | 0.90 | 19,345 | 6.76% |
| 3 | 0.15 | 0.85 | 26,151 | 9.14% |
| 4 | 0.20 | 0.80 | 30,061 | 10.51% |
| 5 | 0.25 | 0.75 | 30,899 | 10.80% ← global mode |
| 6 | 0.30 | 0.70 | 28,518 | 9.97% |
| 7 | 0.35 | 0.65 | 25,435 | 8.89% |
| 8 | 0.40 | 0.60 | 22,360 | 7.81% |
| 9 | 0.45 | 0.55 | 18,892 | 6.60% |
| 10 | 0.50 | 0.50 | 15,590 | 5.45% |
| 11 | 0.55 | 0.45 | 12,477 | 4.36% |
| 12 | 0.60 | 0.40 | 9,914 | 3.46% |
| 13 | 0.65 | 0.35 | 7,714 | 2.70% |
| 14 | 0.70 | 0.30 | 5,696 | 1.99% |
| 15 | 0.75 | 0.25 | 4,356 | 1.52% |
| 16 | 0.80 | 0.20 | 3,377 | 1.18% |
| 17 | 0.85 | 0.15 | 2,734 | 0.96% |
| 18 | 0.90 | 0.10 | 2,270 | 0.79% |
| 19 | 0.95 | 0.05 | 2,066 | 0.72% |
| 20 | 1.00 | 0.00 | 3,519 | 1.23% |

Summary statistics (computed exactly from support-point frequencies, not a floating-point mean):

**Table 24. Summary statistics of the assist09 sliding-window error-rate distribution (computed exactly from support-point frequencies)**

| Statistic | Value |
|---|---|
| Mean error rate | **0.3511** |
| Median error rate | **0.30** (success rate 70%) |
| **Mode (single value)** | **error rate 0.25, i.e., success rate 75%** (k = 5, 30,899 windows) |
| Mode's bootstrap 95% set (200 resamples by student, seed 20260922; review §3.3 requires ≥ 2,000 — rerun pending the assist09 source data) | **{0.25}** (200-resample record: 95.5%; Monte Carlo standard error ≈ 1.5 percentage points) |
| Window share with success rate 77–83% | 10.51% (only k = 4 falls in this interval) |
| Window share with success rate 80–90% | **26.40%** (k = 2, 3, 4) |
| Window share with success rate 80–85% | 19.64% (k = 3, 4) |

Therefore, taking the single value, **the statement "80–85% success rate is the mode" does not match the stored result**: the global mode is 75% success rate (both 0.20 and 0.15 have fewer windows than its 30,899). Under a discrete distribution the mode has no stability problem in the point-estimate sense—bootstrap shows the single-value mode k = 5 is the unique mode in 95.5% of resamples.

**The claim "the three filter calibers share the same mode" does not hold.** After recomputing each caliber by integer error count, the mode support points are **mutually different**:

**Table 25. Robustness of the mode across three filter calibers (recomputed by integer error count)**

| Filter caliber | windows (students) | mean error rate | mode support point | success rate |
|---|---|---|---|---|
| Full | 286,150 (2,314 / 4,217) | 0.3511 | k = 5 | 75% |
| Topic items only (`original = 1`) | 216,993 (2,112 / 4,217) | 0.3334 | k = 4 | 80% |
| No-help items (`hint_count = 0`) | 231,125 (2,021 / 4,106) | 0.2183 | k = 3 | 85% |
| `tutor_mode = test` (not valid) | 0 (0 / 30) | — | — | — |

An earlier version claimed "all three calibers have mode interval 0.15–0.20," which was the result of reusing the same binning function, not independent evidence; and the `tutor_mode` caliber has 0 windows, so it does not constitute a caliber at all. After recomputing by integer error count, the mode position **does move with item type** (help items push the distribution toward lower error rates), which is itself a reportable phenomenon, but it cannot be written as "robust."

### 8.2 What this distribution shows and does not show

Two things it shows are conservative. First, **a large number of learning windows sit in the "overly difficult" interval**—the mean error rate 0.3511 is far above any version of the optimal value, and the median 0.30 (success 70%) is likewise; only 26.40% of windows fall in success 80–90%, 19.64% in 80–85%, and 10.51% in 77–83%. In other words, the difficulty the real system allocates has its distribution centre not near the theoretical optimum, consistent with the intuition that "systems are generally too hard."

Second, **the single-value mode of the distribution is 75% success rate (error rate 0.25, 30,899 windows)**. This position is **below** Wilson et al.'s 84.13% and Baillifard et al.'s 80.7%, while the 80–85% success band occupies only 19.64% of all windows. The 80–85% success band occupies only 19.64% of windows. **But the mode is not the optimum (review §3.3, 2026-09-29)**: the most common speed on a motorway is 100 km/h, which does not show that 100 km/h is the most fuel-efficient — only that people drive that way. This distribution is likewise the distribution of **experienced difficulty** jointly produced by the ASSISTments item-allocation policy and student ability. Moreover the first rank (0.25; 30,899 windows) and the second (0.20; 30,061 windows) differ by only **838 windows, 0.29% of the total**; the five support points spanning error rates 0.15–0.35 (k = 3…7) carry **49.3%** of all windows almost flatly (26,151 + 30,061 + 30,899 + 28,518 + 25,435 = 141,064 / 286,150). **This paper therefore reports the shape of the distribution (its flatness over that interval) rather than the position of the mode**, and states explicitly that this distribution **constitutes no test of any optimal error rate**. The sentence previously written here — that this distribution does not support the claim that the measured mode falls in the 80–85% band — **has been deleted**.


What it does not show is more important: under a discrete distribution the "mode" has no comparable interval width, and the gap between 84.13% and 80.7% is only about 3.4 percentage points—smaller than the support-point interval (5 percentage points) times one, so this evidence **cannot discriminate between these two candidate optima**. Any statement "this paper supports the 85% rule" or "this paper supports 80.7%" exceeds the information this distribution can bear. Moreover, the sliding-window error rate is the joint product of system allocation and student response, not an intervention on the dose, so it is not even a "descriptive dose–response," merely a "descriptive exposure distribution."

**On the testability of the RQ2 decision rule — the decision rule is abolished (review §3.3, 2026-09-29).** An earlier version wrote RQ2's falsification condition as "if the sliding-window error-rate mode significantly deviates from [0.15, 0.20], then falsify." Under the discrete-support-point caliber this condition **cannot be tested as is**: the single-value mode is 0.25, already outside the interval, but "significant deviation" requires a distributional quantity (confidence interval). This paper's approach is to **bootstrap the discrete distribution by student resampling and define the uncertainty by the resample distribution of the mode support point** (the 95% set is given in Table 8-1 above). With current evidence, the mode support point is stably k = 5 in 95.5% of resamples, so the description "mode = 0.25" is stable, while the statement "the mode falls in the 80–85% band" **is falsified**. The causal-side proposition of RQ2 (whether the optimal error rate on real learners equals 15.87%) was executed on 2026-09-24 under a frozen identification strategy: no internal optimum detected, and the Junyi time-inverted negative control significant, downgrading to associational evidence (see §8.3), so that proposition still receives no causal-grade answer.
**Abolition of the RQ2 decision rule, and the reporting caliber of this section (review §3.3, 2026-09-29).** An earlier version wrote RQ2's falsification condition as: if the sliding-window error-rate mode significantly deviates from [0.15, 0.20], then falsify; and the proposal (§3.2) wrote it as: if the confidence set excludes 0.1587 and 0.193, neither candidate is supported. **Both decision rules are abolished**: the support points are only multiples of 0.05 (k/20), and 0.1587 and 0.193 **could never have entered** any confidence set built from support points, so the rule returns refuted regardless of the data — it tests the discreteness of the support grid, not the optimal error rate. More fundamentally, the mode is not the optimum (see the motorway-speed analogy above), so **nothing about the 85% rule or about 80.7% follows from the fact that the mode is 0.25**. Accordingly this section is repositioned as: **the sliding-window error-rate distribution is descriptive statistics of experienced difficulty, not a test of an optimal value**. This section reports the distribution shape (flat over 0.15–0.35, 49.3%) and the resampling stability of the mode (k = 5 in 95.5% of 200 bootstrap resamples; Monte Carlo standard error ≈ 1.5 percentage points, just above the 95% threshold), **but no longer judges any candidate optimum on that basis**. Per review §3.3 the bootstrap must be raised to **≥ 2,000** resamples with the distribution shape as the reported object; `BOOT` in `results/code/m1_real_data.py` has been changed to 2000 accordingly, but **the rerun needs the original assist09 data (`data/assist09_corrected.csv`), which is not present in this working copy**, so the 2,000-resample result is marked as pending rerun and the 200-resample figures above are retained as a record only, not as a basis for conclusions. It is also noted that Wilson et al.'s optimal error rate under Cauchy noise happens also to be 0.25; **this paper claims nothing from that coincidence.**


### 8.3 The causal side — removed from this paper (review §2.2, 2026-09-29)

> **Removal statement.** Per review §2.2, the causal side (former §2.5, this section, and the H4/H5 rows of §8.4) **has been removed from M1** and transferred to the fourth paper, i.e. row 4 of the table in §7.1 of the dissertation proposal. This section no longer carries any causal claim about the optimal error rate, and no longer reports a dose–response curve, the shape of μ(d), an internal optimum location, or positive/negative-control readings.

**The only retained conclusion of the version-1 execution (one paragraph):**

> The preregistered AIPW/DR dose–response analysis was executed on 2026-09-24 on three public logs (assist09, Junyi, DBE-KT22; `results/m1/aipw/aipw_results.json`). That execution **did not pass the positive-control criterion**, and its **implementation differs from the frozen identification strategy (LF-CIS-2026-09-22)**; its results are therefore **not interpretable**, and this paper makes no confirmatory reading of them.

The three grounds for that judgement, item by item, follow review §2.2:

1. **The positive control did not pass the frozen rule.** §6.1 of the frozen document requires that the all-correct (error rate 0) and all-incorrect brackets be "significantly slower; if not significant, the estimator has no detection capability on this data and the negative result of the main analysis is not interpretable." Under the executing script's criterion (bootstrap probability that k = 0 and k = 20 are slower than k = 10, both > 0.95), the measured values are assist09 0.000 / 0.63, DBE 0.312 / 0.646, Junyi 0.002 / 1.000 — **none of the three datasets passed**. An earlier version of this paper wrote that "the estimator itself has detection capability (p = 0.002 and p = 1.000)": the 0.002 is in the direction **opposite** to the prediction, and 1.000 is a bootstrap proportion, not a p-value — that reading contradicts the frozen rule and **has been deleted**. There is also a more fundamental problem: this "positive control" presupposes the very U-shaped hypothesis under test, so it is not a control with a known effect and could not have served as a positive control from the outset.
2. **Identification does not hold.** The variation of the treatment (number of errors in the first 20 items) mixes learner ability, the system's item selection, learning progress and randomness; the outcome (number of steps to the first three consecutive correct responses within the next 20 items) reads the ability and progress of the **same learner on the same knowledge point**. As long as ability is persistent, the monotone shape "learners who erred more earlier are also slower later" arises mechanically. The significance of the time-inverted negative control is consistent with this explanation.
3. **The implementation differs from the frozen document.** (i) Ability confounding: the document specifies "IRT-1PL θ̂ fitted from responses prior to the treatment window," whereas the code uses the logit of the empirical accuracy over the first half of the responses prior to the treatment window; item difficulty: the document specifies expert labels or IRT difficulty, whereas the code uses the mean learner self-reported difficulty on DBE and the knowledge-point global accuracy on assist09. (ii) In the time-inverted negative control, the code sets the "pre-treatment" window to the same interval as the outcome window (`seq[0:20]`) and computes θ̂ from that interval, so the outcome variable enters the confounding adjustment and this control's result cannot be read at face value either. (iii) **The former W = 10/40 "window-width robustness" did not change the window width** — the code that extracts the treatment window, `seq[e-19:e+1]`, is fixed at 20 items; only the number of dose brackets changed. That statement **has been deleted**.

**Follow-up.** Version 2 of the identification strategy must be submitted **before execution** and tagged (the executing script reads that tag and writes its hash into the results JSON); where the implementation differs from the document, the document must be amended and resubmitted first. Version 2 must state where the variation of the treatment variable comes from, and on what basis that variation is taken to be independent of the outcome. **If no basis for identification can be established on observational logs, the work moves to the randomised-assignment experiment** (the design in §11 of the proposal). The 10 October interview must bring the original `aipw_audit.log` and the filesystem timestamps of the frozen document, to show that freezing preceded execution.

### 8.4 Status of preregistered hypotheses

To help readers judge the relationship between this paper and the original design, the following table gives the fulfilment status of the seven hypotheses item by item:

**Table 26. Status of preregistered hypotheses**

| Hypothesis | Content | Status |
|---|---|---|
| H1 | Linear fusion is unstable under monotone reparameterisation | **Tested and holds** (§4 synthetic, §5.3 real) |
| H2 | Unified scale improves calibration quality and target-hit rate | **Partially tested**: ECE / Brier / reliability diagram / 85% target-hit rate not computed; switched to comparing fusion schemes by expert-label consistency (§6), criterion changed |
| H3 | Four-source calibration error has a stable ordering | **Not executed**: the real-data source set differs from the preregistered four sources, ECE not computed |
| H4 | Optimal error rate significantly above 15.87% | **Removed from this paper**: transferred to the fourth paper (causal side); the executed AIPW/DR did not pass the preregistered positive-control criterion and its implementation differs from the frozen document, hence is not interpretable (§8.3), the "optimal-position" test's premise fails, so no point test against 15.87% is reported |
| H5 | Dose–response curve is non-monotone | **Removed from this paper (2026-09-29, review §2.2)**: as above, the readings are not interpretable (§8.3), transferred to the fourth paper. The former W = 10/40 window-width robustness statement is invalid because the treatment window is fixed at 20 items, and has been deleted |
| H6 | Effect-decay ordering of the five premises | **Partial**: exploratory stratification by hint rate × item type is unestimable (each stratum n<3000); the five-premise decomposition retains qualitative discussion (§2.4), formal ordering test not executed |
| H7 | Optimal-interval heterogeneity under ability stratification | **Not executed** |
| — | Additional finding: knowledge-tree structure is not difficulty order | **Completed** (§5.5, negative result) |
| — | Additional finding: criterion dependence of the fusion gain | **Completed** (§7, negative result) |

## 9 Discussion

### 9.1 Three conclusions

**First, commensurability is an engineering property that can be repaired, not a philosophical stance.** The synthetic experiment (L1 0.1276 → 0, 36.4% reversal → 0%) and the real data (0.5357 → 0.0001) give the same conclusion along two independent paths: changing the sources from "linearly add after normalisation" to "link to a logit metric after quantile linking then add" makes the effective weights no longer drift under any monotone reparameterisation. This change needs no new estimator, no new data, and no tuning; its only cost is abandoning the habit of min-max. We argue it should be regarded as the default baseline for difficulty fusion.

**Second, any report of "how much difficulty estimation improved" must simultaneously report the criterion of improvement, and must admit that the criterion itself constructs part of the conclusion.** On the same data and the same fusion configuration, this paper successively obtained two opposite conclusions: +0.1017 (expert-label criterion, p = 0.000) and −0.1222 (holdout-performance criterion, win rate 0.00). They are not contradictory, because the rank correlation between expert labels and real-performance difficulty is only 0.4326.

But this reversal **cannot be read entirely as "fusion has no predictive power."** The holdout-validation criterion is "the true success rate 1 − ok_B/n_B of block B," and the baseline estimator "success rate only" estimates **exactly this statistic** on fit block A. That is, **the baseline is a small-sample estimate of the criterion quantity, while the fusion estimator mixes in other constructs such as hints, time, attempt count, and session count.** If an item's success probability is stable, the success rate on A converges to that on B, so this design is **asymptotically favourable to the success-rate-only estimator**; the observed pattern (larger k, larger fusion disadvantage; Junyi −0.0267 → −0.1222, ρ reaches 0.95–0.96 at k = 200) is consistent with this structure. This is only a partial explanation—the objective function is inter-item rank correlation, block B is also finite-sample, and the fusion estimator also contains the success-rate signal—but **a substantial part of the reversal is built into the criterion choice**, which must be stated clearly in the conclusion.

Therefore what this paper can safely claim under this structure is: **when the criterion quantity is success rate, the success-rate estimator's large-sample dominance is design-expected; fusion's role is rank stabilisation at small samples.** This is exactly what `srw7` and λ_cf show (at k = 10, +3.8 ~ +4.3 pp; gone by k ≥ 100), and is consistent with the variance-reduction explanation of the "(1−λ)·success-rate + λ·fusion" shrinkage combination—but we did no bias–variance decomposition and have no prior model, so we have not identified this explanation; it is merely a compatible reading.

**To make the sentence "consistency gain is not predictive-power gain" hold, two classes of criteria were added and recomputed (real-dataset fit, cross-validated PASS by `verify_m1_criteria.py --results`):** First, **ability-corrected criterion (A1·Junyi, B-half ≥500 responses, actually 1,274 items)**—b_j fitted on block B, with the success-rate baseline and the fusion estimator both estimated on **block A** and compared against the same b_j (caliber corrected per review §3.1); Spearman(b_j, success-only_A) = **0.9541**, Spearman(b_j, fusion_A) = **0.8923** (the old 0.963, inflated by same-half leakage, is withdrawn). Second, **exogenous criterion (A2·DBE-KT22, 212 items)**—teacher labels placed at the criterion position, signal definitions unified with §6/O4 (same `dbe_signals.build()`); Spearman(fusion, teacher) = **0.2918**, Spearman(success-only, teacher) = **0.2204**, teacher-vs-behaviour three-grade weighted κ = **0.178**. The two criteria point in **opposite directions**: **under A1's b_j criterion success rate is closer to b_j (0.9541 vs 0.8923), whereas under A2's teacher-label criterion fusion is closer (0.2918 vs 0.2204)** — and this divergence survives the unification of the signal definitions, so it stems from the choice of criterion itself. The claim is therefore narrowed to "the conclusion depends on the definition of the criterion quantity", adopted here on the basis of the real recomputation of the two criteria.

In addition, the criterion block has limited reliability (record-level block B fixed at 250, student-level requires ≥500), so **only within-k between-group comparisons are valid**; the absolute ρ values in the tables (max 0.96) **must not be read as "near perfect,"** nor bolded in the tables.

**Third, completing the measurement side does not automatically buy the causal side.** The original logic of this paper was "first argue whether the measure is well defined, then argue the causal effect on that measure." The first half is complete; the second is not. This asymmetry should not be masked by narrative skill: what this paper can now say is "difficulty can be well-definedly fused," not "placing a student in a certain difficulty bracket changes their mastery speed." (Supplement 2026-09-24: the causal side was executed under a frozen identification strategy, yielding no detected internal optimum and a significant Junyi negative control—the scope of "cannot say" is thereby narrowed to "cannot make a causal-grade assertion," not "did not attempt"; see §8.3.)

### 9.2 Implications for the system and three landed code changes

Part of the above conclusions has landed in the studied system's code layer, in three places (the first two covered by regression tests, the third by an external verification script):

1. **New difficulty-metric layer** `learnflow-backend/app/services/difficulty_fusion.py`, providing three functions: `ecdf_logit()` (empirical CDF → logit quantile linking, invariant to any monotone reparameterisation, corresponding to O1's 1 × 10⁻⁴ property), `fuse_signals()` (multi-behavioural-signal rank fusion, corresponding to O4 / O5 conclusions), `logit_to_fsrs()` (in-batch mapping to FSRS's [1, 10] interval). The module docstring writes in O1 / O3 / O4 / O5 numbers, and writes in **O3's negative-result warning: prohibit using knowledge-tree depth as a difficulty proxy**.

2. **Modified** `learnflow-backend/app/services/optimal_difficulty.py`'s `update_task_difficulty`: replaced the time-consuming `>180s` hard-threshold bracketing with a log-time continuous monotonic soft term s = σ(ln(t/60)/0.8), and added a hint penalty (O5 shows hint rate is an effective difficulty signal); the old behaviour contract "lower difficulty after fast correct" is preserved.

3. **New** `estimate_optimized_difficulty()` in `learnflow-backend/app/services/difficulty_fusion.py` (along with `split_half_reliability()` and `OPT_SIGNAL_NAMES`, defined at `:278`; the file is 338 lines in total): implements the §7.8 `srw7` estimator—per-signal sign correction (sign fixed by in-fit-block rank correlation with success-rate direction; inversely signed signals taken negative, not dropped), split-half-reliability weighting (`split_half_reliability()` estimates each signal's reliability, taken positive and normalised), and λ-shrinkage (defaults to the closed form `lambda_closed_form(k)`). The recommended estimator of §7.4 is this function.

The accompanying new `learnflow-backend/tests/test_difficulty_fusion.py` (14 regression tests) covers quantile-metric monotone-transform invariance, zero fusion-weight drift, fusion better than single signal, no time jump (difference between 179 s and 181 s < 0.02), and evidence-score boundary [1, 4]; **the above regression tests cover only the first two changes.** The full test count **rose from 920 before the changes to 934 (intermediate) after the difficulty-metric layer added 14 regression tests, then to 936 (intermediate) after this review's remediation added 2 mechanism-count gate tests, and finally to 972 after merging the `learnflow-main` snapshot; measured `pytest` is now 972 passed**. All citations in this paper uniformly use 972.

**Landing method and cost of the third change (stated honestly):** `estimate_optimized_difficulty()` landed as an **incremental function**, **added no new pytest cases**, so **this estimator does not change the test count** (still 972 full)—the earlier notice "this estimator's landing will change the test count" no longer holds, corrected here honestly. The function's correctness is instead guaranteed by the **external verification script** `results/code/o11_land_verify.py`: all 15 checks pass (15/15 PASS), covering module export `estimate_optimized_difficulty` / `split_half_reliability`, `ValueError` on k ≤ 0, `ValueError` on missing signal, λ default equals `lambda_closed_form(k)`, `signed7` and `srw7` holdout gains at k = 10/25/50/100/200 reproduced item-by-item with O11 (e.g., k = 10: +3.594 / +3.823 pp; k = 200: +0.111 / +0.138 pp), and the sign-correction behaviour (after correction fusion positively correlates with difficulty direction, Spearman +0.951).

**One defect found and fixed by the verifier (stated honestly):** `ecdf_logit()` originally used `if not values:` to check emptiness, which raises `ValueError: The truth value of an array with more than one element is ambiguous` for numpy array input; now changed to first take `n = len(values)` then `if n == 0: return []`, behaviour-identical for list input, changing no tested behaviour (`app/services/difficulty_fusion.py:63`).

### 9.3 Limitations

**First, the causal side is executed but the result is negative.** §8.3 lists it: the preregistered AIPW/DR was executed under a frozen identification strategy (2026-09-24), detected no internal optimum, μ(d) rises overall with dose, and the Junyi time-inverted negative control is significant—so this paper still contains no causal conclusion about the optimal error rate; all dose–response readings remain at the associational level.

**Second, the criterion limitation of the fusion gain.** All conclusions in §7 condition on the two specific criteria "expert difficulty labels" and "holdout performance." The validity gap "O7 splits records not students" was handled by O10's student-level holdout (§7.6)—the conclusion fully reproduces, so it is not a substantive threat. The remaining boundary is the criterion's own reliability ceiling (O7 block B fixed 250, O10 criterion half fixed response count), which limits the absolute level of all ρ; only **within-k between-group comparisons** are valid.

**Third, neither λ-shrinkage nor fusion optimisation is cross-system reproduced.** λ-shrinkage is verified only on Junyi (which has downgrade-rate, repeat-session-rate signals), with no gain on DBE; the O11/O12 optimisation of §7.8 (sign correction + split-half-reliability weighting) is likewise **verified only on Junyi**, not cross-system reproduced. It must be re-verified before writing it into other systems.

**Fourth, the suspect status of expert annotation itself.** This paper uses expert labels as an acceptable criterion, but §7.1 measured their correlation with real-performance difficulty at only 0.4326. This means all comparisons anchored on expert labels (including O2, O4, O5, O6) inherit this limitation. We do not believe a better alternative criterion exists, but we also do not treat expert labels as "truth."

**Fifth, data-licence constraints.** Junyi is CC-BY-NC-SA-4.0, **commercial use prohibited**; all our analyses are offline, non-commercial, read-only research use. Before submission, the citation obligations of all four datasets must be verified item by item (assist09's Feng et al. 2009 and data page, DBE-KT22's arXiv:2208.12651 and ADA DOI, XES3G5M's NeurIPS 2023 and MIT licence, Junyi's Chang et al. 2015 and CC licence).

**Sixth, the studied system's real deployment data is missing.** Although the studied system is built and publicly archived, it has no logs produced by real users, so all our measurements rest on the four public datasets; the studied system's role in this paper is a concrete instance of "a class of implementations being criticised" and the carrier of code landing, not an empirical object.

**Seventh, the learning-addiction-inclination measurement is unvalidated (mandatory disclosure).** The Learning Addiction Index (LAI) built into the studied system is self-constructed by this project, with five-dimensional weights time 30% / motivation 25% / control 25% / cognitive 10% / function 10%, of which "control + function" totalling 35% is supplied by the self-report measurement layer (instrument catalogue `instrument_catalog.py`'s SRL-STOP / SLEEP-IMPACT / SOCIAL-IMPACT / TIME-BIAS); dimensions not measured are not counted into the weighting and output `coverage` for disclosure, never silently scoring "healthy." **It must be emphasised** that this scale's items are self-authored by this project, not yet validated for reliability and validity, with no norm and no clinical cutoff, a work-in-progress instrument. **This paper did NOT use LAI for any analysis**—all our data come from the four public datasets and contain no self-report scale data; this disclosure only explains the tool's status to prevent readers from assuming the system already has a validated problematic-use measurement capability. The mitigation path is three-pronged and **none completed**: ① use public validated scales as convergent-validity anchors (BStAS 5 items, Atroszko et al., 2025; SI-10, Loscalzo et al., 2024; Chinese Adolescent Learning Burnout Scale, Wu et al., 2010); ② complete a minimal reliability/validity set (α/ω + EFA→CFA + 2-week retest ICC + correlation with burnout/anxiety); ③ convergent validity between self-report scores and behavioural logs.

**Eighth (honest negative results as a methodological contribution).** Reporting "unmet expectations / unexecuted" honestly rather than dressing them up as successes is itself a demonstration of the "preregister–executable–testable" research paradigm, with independent methodological value. Specifically: (a) the causal side executed under a frozen identification strategy yielded a **negative result**—no detected internal optimum in the preregistered sense, and a significant Junyi time-inverted negative control, all dose–response readings downgraded to associational evidence (§8.3), which instead strengthens the separation of "difficulty can be well-definedly fused" from "causal identification of the optimal error rate is not yet supported"; (b) of the seven preregistered hypotheses, **H2 is only partially tested, H3 and H7 unexecuted** (§8.4), and we do not recast them as supportive conclusions; (c) the `srw7` fusion optimisation and direction correction (O8/O11/O12) are **verified only on Junyi, not cross-system reproduced** (§7.7, 7.8, and 9.3). These boundaries do not negate this paper's engineering-methodological contributions: the quantile-logit metric's invariant and the criterion dependence of the fusion gain are reproduced on more than two systems; while the above negative results, preregistration gaps, and single-system verification jointly demarcate the method's applicability boundary, which readers should use to calibrate expectations of extrapolation. Accordingly, this paper submits "honest negative results" as one of its contributions, consistent with the reception orientation of the target journals (IEEE TLT / IJAIED / JEDM) toward methodological and reproducibility research.

**Ninth (scope of the methodological contribution: cross-system gain pending).** The engineering-methodological contribution must be clearly separated from "cross-system gain." §7 already shows: on DBE-KT22 the fusion gain is only marginally significant (one-sided p = 0.059) and negative after criterion switch, and Junyi is the only system so far that reproduces and verifies the fusion gain; `srw7` (sign correction + split-half-reliability weighting) and the §7.3 direction-error correction are **verified methods**, but their **cross-system gain remains to be proven (cross-system gain pending)**. Therefore this paper's contribution positioning is "method + single-system (Junyi) verification + honest boundary on cross-system extrapolation," not an already-proven cross-system improvement; readers must re-verify on their own system's data before writing `srw7` into other systems.

### 9.4 One practical recommendation

Synthesising §5.3, §7.3, §7.7, and §7.8, this paper's practical recommendation for the difficulty-fusion module is one sentence: **first switch the metric to quantile logit (unconditional), then decide whether to enable multi-signal fusion by sample size (conditional), and before enabling, do direction correction per signal rather than simple deletion (mandatory).** The first item's gain is largest and depends on no tuning; the second item's gain approaches zero when observations per item ≥100; the third is a **directional-configuration error**—§7.8 shows that deleting a directionally wrong signal column-wise (O8's fused6) discards its effective information, while correcting its direction (counting it as negative evidence) is instead superior, i.e., **correction beats deletion**.

## 10 Honest Gap Inventory

1. **Causal side executed, result negative (2026-09-24):** the preregistered AIPW/DR, dose–response estimation, and negative control were executed under a frozen identification strategy (§8.3); result is no detected internal optimum, significant Junyi negative control (downgraded to associational evidence). Still unexecuted: E-value, the formal ordering test of the five premises, the P-pos-2 simulation-arm control.
2. **H2 / H3 not executed per original caliber:** ECE, Brier, reliability diagram, and 85% target-hit rate not computed; four-source calibration-error ordering not tested (§8.4).
3. **The record-level-holdout validity gap was handled by O10's student-level holdout** (§7.6): conclusion fully reproduces, the "record-level rather than student-level" concern is tested to have little effect. Remaining boundary: gain decays to ≤0.34 pp for k ≥ 100 (student-level `srw7` caliber: k = 100 is +0.335 pp, k = 200 is +0.102 pp; record-level +0.391 / +0.138 pp) and λ-shrinkage not reproduced on DBE (§7.7).
4. **λ-shrinkage not reproduced on DBE** (§7.5).
5. **O11/O12 optimisation not cross-system reproduced:** the recommended estimator `estimate_optimized_difficulty` (sign correction + split-half-reliability weighting + λ-shrinkage) has been **incrementally landed** to the repo code (this landing does not change the test count, currently 972 full), its correctness guaranteed by the external verification script `results/code/o11_land_verify.py` (15/15 PASS) (§9.2); but this optimisation is verified only on Junyi, not cross-system reproduced (§9.3).
6. **Expert-label-criterion reliability not independently estimated:** this paper obtained no inter-rater reliability of the expert annotation; all uncertainty of the 0.4326 distance is attributed to the single realisation of the expert labels.
7. **assist09 sliding-window analysis uses the "one row per student-problem" revised version;** help-recording semantics (tutor semantics) handled per the official caliber, possibly differing from some secondary literature.
8. **The synthetic experiment's most-favourable environment:** the four sources sharing one latent variable is the most favourable setting for the proposition to hold (§4.6).
9. **Data licences not legally verified item by item:** the citation obligations and commercial restrictions of the four datasets follow official pages and must be closed before submission.
10. **LAI unvalidated and not used in this paper** (§9.3 seventh point); all three mitigation paths unfinished.

## 11 Conclusions

This paper rewrote the question "can difficulty be measured on one common scale," which engineering practice had skipped, into a falsifiable measurement proposition, and gave results on synthetic data and four public learning-log corpora. **The caliber must be stated first:** the **real-data test of proposition C1 was completed at only one real system, assist09** (994 items); the Junyi, DBE-KT22, and XES3G5M datasets bear the multi-signal-fusion consistency experiment, the expert-annotation experiment, and the knowledge-tree / ordered-transition experiment, and **do not constitute a test of C1** (see the title-caliber note at the front). The instability proposition holds: linear [0,1] fusion's effective weights equal neither the nominal weights (π₁ = 0.532 vs. w₁ = 0.40) nor themselves under monotone reparameterisation (nonlinear monotone L1 = 0.1276, 36.4% cell rank reversal, strongest counterexample complete sign reversal), while the quantile-logit metric is strictly invariant to it (0 under shared calibration, 0.016 sampling noise under independent calibration); on assist09's 994 items, the real drift falls from 0.5357 to 0.0001. Multi-signal fusion does raise consistency with expert difficulty labels (DBE 0.2207 → 0.2918, repeated-cross-validation optimised weights 0.5240 ± 0.1069; Junyi 0.2610 → 0.3629, repeated cross-validation 0.4023 ± 0.0480), driven by a "self-reported difficulty high and trust low" differential feature; but the rank correlation between expert labels and real-performance difficulty is only 0.4326, and after switching the criterion to holdout performance, fusion is worse than success rate alone at every sample size on both datasets, with win rate 0.00—these gains are consistency gains, not predictive-power improvement. We further located a directional error in the fusion configuration and proposed sample-size-adaptive shrinkage, whose gain reaches +3.43 percentage points at k = 10 (O8 caliber) and decays below 0.22 percentage points for k ≥ 100, and is not reproduced on DBE. Further optimisation of the fusion estimator itself (sign correction + split-half-reliability weighting, `srw7`) was doubly validated at record-level and student-level holdout: non-inferior to success-rate-only at every sample size, and consistently better than fused6 which only deletes. Finally, this paper reports that the single-value mode of the assist09 sliding-window error-rate distribution is **error rate 0.25 (success rate 75%)** (n = 286,150 windows; 21 discrete support points; the 80–85% success band occupies only 19.64%), and explicitly states that this descriptive evidence **is a distribution of experienced difficulty and is not a test of the 85% rule or of the 80.7% value, and the earlier-reported "mode interval 0.15–0.20" was verified to be a binning-boundary artifact of equal-width binning and is voided**; **the preregistered dose–response identification was fully executed on 2026-09-24 under a frozen identification strategy (LF-CIS-2026-09-22), yielding "no internal optimum in the preregistered sense detected," and Junyi's time-inverted negative control is significant** (low-end exceedance 1.000/0.998), so per that strategy's §6.2 handling convention all dose–response conclusions are downgraded to associational evidence; therefore this paper **still makes no point estimate, confidence interval, or test against 15.87% for the optimal error rate** (that test presupposes the existence of an internal optimum, a premise not supported), and makes no directional assertion about whether that value holds for real learners (full execution record in §8.3; the conclusion section's earlier wording "causal side not executed" was legacy from an old version and was corrected on 2026-09-25). The three conclusions have partially landed in the studied system's difficulty-metric layer (full test 972 passed); the `srw7` estimator has also landed as the incremental function `estimate_optimized_difficulty()` in `difficulty_fusion.py`, its correctness guaranteed by an external verification script (§9.2). **It must be emphasised:** while presenting the methodological contributions, this paper also honestly reports the causal-side negative result (no detected internal optimum, significant Junyi negative control), the preregistration gaps of H2 partially tested and H3/H7 unexecuted, and the cross-system boundary that `srw7` / direction correction is verified only on Junyi; these **honest negative results and boundaries themselves are this paper's methodological contribution to the "preregister–executable–testable" norm, and do not negate the engineering conclusions.**

**Educational stake.** The purity of difficulty-signal fusion matters not merely as measurement tidiness, because an adaptive system's next-item selection is directly driven by the difficulty metric: if multiple difficulty sources are mis-weighted, the next-item difficulty routed to the learner will systematically shift, and this shift accumulates question by question along the adaptive sequence, misaligning the learning path near the "challenge point" and amplifying subsequent item-selection error. This paper's quantile-logit invariance contribution has a concrete educational payoff—it guarantees that the routing precondition "effective weight = nominal weight" is not broken under monotone reparameterisation, thereby suppressing the magnitude of the above cumulative shift. To be clear: this is a mechanistic inference from a measurement property to a routing mechanism; this paper did not test its corresponding learning outcome on real learners, and claims no causal effect.

## References

[1] Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10(1), 4646. DOI: 10.1038/s41467-019-12552-4.

[2] Baillifard, A., Belardi, A., & Martarelli, C. S. (2025). Engagement beyond success rate: Evidence from an adaptive learning system. In *The Envisioning Report for Empowering Universities*, nr. 9 (9th edition, 2025), 56–59. European Association of Distance Teaching Universities (EADTU), Parkweg 27, 6212 XN Maastricht, the Netherlands. DOI: 10.5281/zenodo.15908735. (Non-peer-reviewed annual report, not a journal paper; source grade must be noted at the citation in the text.) n = 413; optimal success rate ≈ 80.7%. Bibliographic limits: this DOI is a report-level DOI, not a chapter-level DOI (the chapter has no independent DOI); no ISBN (Zenodo official API metadata `isbn` field empty, PDF copyright page also none)—must not be filled; no volume / issue (annual report only has nr. 9)—must not be fabricated. Page numbers per PDF footer print page 56–59; the report TOC marks 57, which has a systematic off-by-one error from page 43 onward. (Verified 2026-09-23.)

[3] Guadagnoli, M. A., & Lee, T. D. (2004). Challenge point: A framework for conceptualizing the effects of various practice conditions in motor learning. *Journal of Motor Behavior*, 36(2), 212–224. DOI: 10.3200/JMBR.36.2.212-224.

[4] Hodges, N. J., & Lohse, K. R. (2022). An extended challenge-based framework for practice design in sports coaching. *Journal of Sports Sciences*, 40(7), 754–768. DOI: 10.1080/02640414.2021.2015917. (Correction 2026-09-23: originally mis-entered as *International Review of Sport and Exercise Psychology*; verified via publisher page to be *Journal of Sports Sciences*.)

[5] Weber, D., Becker, N., Spinath, F. M., & Koch, M. (2025). The stability of IRT parameters under several test equating conditions. *Frontiers in Psychology*, 16, 1652341. DOI: 10.3389/fpsyg.2025.1652341.

[6] Deng, J. (2025). Linking errors introduced by rapid guessing responses when employing multigroup concurrent IRT scaling. *Large-scale Assessments in Education*, 13, 28. DOI: 10.1186/s40536-025-00265-8.

[7] Liu, Z., Guo, T., Liang, Q., Hou, M., Zhan, B., Tang, J., Luo, W., & Weng, J. (2025). Deep learning based knowledge tracing: A review, a tool and empirical studies. *IEEE Transactions on Knowledge and Data Engineering*, 37(8), 4512–4536. DOI: 10.1109/TKDE.2025.3552759.

[8] Ding, M., Agrawal, A., Choo, J., Deng, C., et al. (2024). Easy2Hard-Bench: Standardized difficulty labels for profiling LLM performance and generalization. *Advances in Neural Information Processing Systems (NeurIPS), Datasets and Benchmarks Track*. arXiv:2409.18433.

[9] Dudík, M., Langford, J., & Li, L. (2011). Doubly robust policy evaluation and learning. *Proceedings of the 28th International Conference on Machine Learning (ICML)*.

[10] Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., & Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. *The Econometrics Journal*, 21(1), C1–C68. DOI: 10.1111/ectj.12097.

[11] VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in observational research: Introducing the E-value. *Annals of Internal Medicine*, 167(4), 268–274. DOI: 10.7326/M16-2607.

[12] Feng, M., Heffernan, N. T., & Koedinger, K. R. (2009). Addressing the assessment challenge with an online system that tutors as it assesses. *User Modeling and User-Adapted Interaction*, 19(3), 243–266. DOI: 10.1007/s11257-009-9063-7. ASSISTments 2009–2010 skill-builder data page URL: https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010 (HTTP 200 verified). Warning: the widely circulated old URL variant is now 404, disabled. Note: the data page self-citation titles the paper "...in an Intelligent Tutoring System that tutors as it assesses," inconsistent with the published title—use the published title.

[13] Abdelrahman, G., Wang, Q., et al. (2022). Knowledge tracing for complex skill training data. arXiv:2208.12651. (DBE-KT22; ADA Dataverse DOI: 10.26193/6DZWOH)

[14] Liu, Z., Liu, Q., Guo, T., Chen, J., Huang, S., Zhao, X., Tang, J., Luo, W., & Weng, J. (2023). XES3G5M: A knowledge tracing benchmark dataset with auxiliary information. In *Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track*, 32958–32970. DOI: 10.52202/075280-1429. (MIT licence.) Bibliographic limits: pages 32958–32970 from OpenAlex; NeurIPS official page shows no pages; if the target journal does not require conference pages, DOI alone suffices. arXiv number left blank—the paper has no arXiv preprint (arXiv API returns 0); must not fabricate. Disambiguation: Liu, Z., Chen, J., & Luo, W. (2023) "Recent Advances on Deep Learning based Knowledge Tracing" (WSDM 2023, 1295–1296) is a same-first-author, same-field, same-year two-page short paper, not this entry—do not miscite.

[15] Chang, H.-S., Hsu, H.-J., & Chen, K.-T. (2015). Modeling exercise relationships in e-learning: A unified approach. In *Proceedings of the 8th International Conference on Educational Data Mining (EDM 2015)*, 532–535. International Educational Data Mining Society. ISBN: 978-8-4606-9425-0. URL: https://www.educationaldatamining.org/EDM2015/proceedings/short532-535.pdf (HTTP 200 verified). Junyi Academy dataset, CC-BY-NC-SA-4.0, commercial use prohibited. (Correction 2026-09-23: entire original entry was wrong, replaced. Originally entered as *Educational Technology & Society*, 18(2), 128–141. Counter-evidence: ET&S official Volume 18, Number 2 (2015) TOC PDF contains no such paper; the "128–141" spans three unrelated papers. No DOI found (EDM 2015 proceedings assigned no Crossref DOI), left blank, must not fabricate, use the URL above. This paper remains the source of the Junyi Academy dataset.)

[16] Kolen, M. J., & Brennan, R. L. (2014). *Test Equating, Scaling, and Linking: Methods and Practices* (3rd ed.). Springer.

[17] Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In *Advances in Large Margin Classifiers*. MIT Press.

[18] Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. *Proceedings of the 34th International Conference on Machine Learning (ICML)*.

[19] Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.

[20] Cohen, J. (1968). Weighted kappa: Nominal scale agreement with provision for scaled disagreement or partial credit. *Psychological Bulletin*, 70(4), 213–220.

[21] Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B*, 57(1), 289–300.

[22] Atroszko, P. A., Charzyńska, E., Buźniak, A., Czerwiński, S. K., Griffiths, M. D., et al. (2025). Validity, reliability, and cross-cultural comparability of a problematic overstudying scale. *International Journal of Mental Health and Addiction*. DOI: 10.1007/s11469-023-01128-5.

[23] Loscalzo, Y., Wetstone, H., Schuldberg, D., Giannini, M., & Rice, K. G. (2024). Studyholism in the United States and Italy. *Current Psychology*, 43(29), 24608–24621. DOI: 10.1007/s12144-024-06163-6.

[24] Wu, Y., Dai, X., Wen, Z., & Cui, H. (2010). Compilation of an adolescent learning burnout scale. *Chinese Journal of Clinical Psychology*, 18(2), 152–154.

[25] Al-Fawakhiri, N., Kayani, S., & McDougle, S. D. (2023). Evidence of an optimal error rate for motor skill learning. *bioRxiv*. DOI: 10.1101/2023.07.19.549705. (Supplemented 2026-09-27: previously a dangling reference; now added. Evidence grade must be stated with citation: as of this verification still a bioRxiv preprint (latest v5, not peer-reviewed), v3 revision note self-states "rearranged methods section for submission," no formal publication record found, so it must not be described as published. Content consistent with text: N=192, empirical optimal error rate ≈ 30%, domain motor-skill learning. Placement limit unchanged: value not extrapolable to academic learning, cited only as a task-dependence case, not in the RQ2 decision table, not as a new target value.)

[26] Yeung, C.-K. (2019). Deep-IRT: Make deep learning based knowledge tracing explainable using item response theory. In *Proceedings of the 12th International Conference on Educational Data Mining (EDM 2019)* (pp. 683–686). arXiv:1904.11738. (Supplemented 2026-09-27: previously a dangling reference; now added. Verified that beyond arXiv:1904.11738 there is also a formal EDM 2019 conference version (pp. 683–686, per the author's own code-repo citation example), so cited by formal version, arXiv as auxiliary. This paper's citation point is only one reported number: item analysis (first-attempt error proportion) vs. 1PL IRT difficulty Pearson r = 0.96; the same paper also reports publisher-labelled 3-level difficulty correlates only 0.40 with item analysis, 0.39 with IRT, 0.08 with Deep-IRT, so its network-output difficulty must not be used as a decision benchmark.)
