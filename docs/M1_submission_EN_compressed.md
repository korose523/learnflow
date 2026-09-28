# Difficulty Commensurability and the Optimal Error Rate

Zexiao Weng¹ and MinPo Jung¹,*

¹ Youngsan University, Busan 48015, Republic of Korea

* Corresponding author. Email: minpo@ysu.ac.kr; ORCID: 0009-0003-3369-757X. Zexiao Weng ORCID: 0009-0009-8600-8954.

AI-Assisted Writing Disclosure. This manuscript was prepared with the assistance of a large language model (LLM) used strictly as a language-polishing and drafting aid. No LLM authored scientific content or made any analytical, statistical, or experimental decision; all results, claims, and numerical values were produced by the authors' own experiments, simulations, and scripts. The LLM was not used to generate data, analyses, or conclusions.

## Abstract

Adaptive learning systems must answer "what difficulty should the next item have?" every day, yet the prior question—whether difficulty is a quantity that can be placed on one common scale—is systematically skipped. We reformulate that question as a falsifiable measurement proposition and report three results. **First, we quantify the magnitude of the instability proposition (C1) on real systems.** The invariance side of the proposition is an identity, not a discovery (for strictly increasing g, #{g(x_cal) ≤ g(x)} = #{x_cal ≤ x}, so effective weights under the quantile metric are pointwise invariant); our contribution is to quantify how large the discrepancy becomes when that identity is violated. If difficulty sources are each normalised to [0,1] and then linearly combined, the effective weights defined by marginal contribution equal neither the nominal weights (π₁ = 0.532 ± 0.026 against nominal w₁ = 0.40 in simulation) nor themselves under a monotone reparameterisation of any single source: drift is exactly zero under affine transforms but averages L1 = 0.1276 (SD 0.0196) under nonlinear monotone transforms, with rank reversals in 36.4% of (source, transform) cells and complete sign reversal in the strongest counterexample (Spearman −0.20, L1 = 0.6893). An empirical-CDF-to-logit quantile metric gives exactly zero drift under shared calibration, 0.016 linking sampling noise under independent calibration, and zero reversals. On real data (assist09, 994 items), linear min-max fusion drifts by L1 = 0.5357 with substantial reversals, while the quantile metric reduces this to 0.0001 with reversals eliminated. **Second, the gain from multi-signal fusion is real under an expert-label criterion but reverses under a holdout criterion.** Five-signal fusion on DBE-KT22 raises agreement with expert labels from ρ = 0.2207 (raw correct rate) to 0.2899 (equal-weight) and 0.5240 ± 0.1069 (cross-validated optimised weights); on Junyi (1,234 exercises, no-feedback regime) seven-signal fusion raises ρ from 0.2610 to 0.3629 equal-weight and 0.4023 ± 0.0480 optimised. Yet once the criterion switches to real performance on held-out samples, the fusion loses at every sample size (Junyi −0.0267 to −0.1222, DBE −0.1752 to −0.2113, win rate 0.00). We trace part of this to a directional error, and show that sign correction plus reliability weighting (`srw7`) with sample-size-adaptive shrinkage λ*(k) recovers a deployable but rapidly decaying gain (+4.283 pp student-level at k = 10, +0.102 pp at k = 200). **Third, we give descriptive evidence on the optimal error rate.** On assist09 the sliding-window error-rate distribution (W = 20, n = 286,150 windows) has only 21 discrete support points, mean 0.3511, median 0.30, and a single-value mode at error rate 0.25 (success 75%, 30,899 windows); the 80–85% success band occupies only 19.64%. Together with a preregistered AIPW/DR analysis that detects no internal optimum, this supports neither the 15.87% rule nor the claim that the measured mode falls in the 80–85% band.

**Keywords**: difficulty commensurability; measurement invariance; quantile linking; multi-signal fusion; holdout validation; optimal error rate; negative results

## 1 Introduction

### 1.1 A skipped question

No adaptive learning system can avoid "what difficulty should the next item have." The standard engineering practice is to normalise several quantities called "difficulty" or "ability"—the mastery probability of knowledge tracing, the memory difficulty of spaced repetition, the ability estimate of competitive rating, the window success rate—into [0,1] and then add them up with weights. This is convenient, but it silently assumes a property that is rarely tested: that these quantities are **commensurable**, i.e. that they live on one common scale on which addition and weighting are meaningful operations. We reformulate "commensurability" as a falsifiable measurement proposition rather than a design vocabulary, and we ask how large the violation is in practice.

### 1.2 Why this is not a technical detail

A few decimal points of weight drift might look negligible, but it determines the system's interpretability and tunability. If the weight vector "0.45 / 0.35 / 0.20" becomes a different vector once the knowledge-tracing side is changed from one monotone parameterisation to another, then the weights no longer mean anything a practitioner can set, audit, or tune: they are artefacts of an arbitrary choice of scale. This is the practical stake of the proposition.

### 1.3 Contributions

We make four contributions. (i) We turn "difficulty commensurability" from a design vocabulary into a computable, falsifiable proposition (C1) and quantify the violation; the invariance half of C1 is an analytic identity, and our contribution is the magnitude of the discrepancy when that identity is broken. (ii) We show the violation is repairable: switching the fusion metric from linear min-max to an empirical-CDF-to-logit quantile linking removes the drift entirely (0.5357 → 0.0001 on real data). (iii) We show that the apparent gain of multi-signal fusion is criterion-dependent and can reverse completely under holdout validation, and we isolate both a directional error and a deployable correction (`srw7` with λ*(k) shrinkage). (iv) We provide descriptive evidence on the optimal error rate that supports neither the 15.87% rule nor the 80–85% band claim. To prevent readers from inferring contributions from the title, we also state four explicit non-claims up front (§1.4 of the full paper).

## 2 Related Work

Deep knowledge tracing is the mainstream paradigm for predicting the probability that a student answers the next item correctly, but its output is a **probability**, not difficulty; using it as a difficulty signal creates the difficulty–ability confound. The test-equating literature solves the analogous question of whether different test forms are comparable and shares our measurement-theoretic root (Weber, Becker, Spinath & Koch, 2025 compare five equating methods). On difficulty estimation, Easy2Hard-Bench (Ding et al., 2024) uses joint IRT and Glicko-2 calibration to provide labels for standardised LLM difficulty evaluation, representing the mainstream position that difficulty is estimable from behavioural signals. On the optimal error rate, Wilson et al. (2019) derive 15.87% on a gradient-descent binary-classification learner—a theorem about a specific algorithm whose derivation depends on five premises (binary classification, no hints, no skipping, no forgetting, and a fixed learning rule). Because adaptive systems almost never run online randomised experiments, we also draw on off-policy evaluation (AIPW/DR) for the causal side.

## 3 Theory: the Instability Proposition

### 3.1 Four difficulty sources and their scale types

**Table 1. Four difficulty sources and their scale types**

| Source | Scale type | Construction | Dependence |
|---|---|---|---|
| KT mastery m | bounded latent variable (approx. ordinal after integerisation) | machine-inferred | depends on real responses |
| SR memory difficulty D | ordinal scale | machine + human | model-specific |
| EL competitive rating θ_EL | interval scale (log-odds) | machine | not directly dependent on ground truth |
| WR window success rate r | ratio scale | machine | depends on real responses |

### 3.2 Two metrics and their invariance

Let the fusion rule be S = Σ_k w_k · z_k, where z_k is the k-th source after mapping and w_k the nominal weight, and define the **effective weight** π by marginal contribution. Metric A (linear [0,1]) applies min-max per column and is invariant **only** to affine transforms, which min-max absorbs. Metric B (quantile logit) links each column through the step empirical CDF to a logit latent scale, ψ = ln(p/(1−p)) with p = (#{x_cal ≤ x} + 0.5)/(n + 1), and is invariant to **any** strictly monotone transform by rank invariance.

### 3.3 Proposition C1

**Proposition C1 (instability).** If sources are each first normalised to [0,1] and then linearly combined, the effective weight π generally differs from the nominal weight w and drifts with any monotone reparameterisation of a single source; if sources are first linked through the empirical CDF to a logit scale, the effective weights are invariant and equal the nominal weights. The invariance half is an **analytic identity**, not an empirical discovery; the empirical content is the size of the violation under metric A.

## 4 Synthetic Validation

We test C1 in an environment with known truth structure: common latent ability θ ∼ N(0,1), n = 500 with an independent calibration sample n_cal = 500, the four sources being monotone functions of θ (X₁ mastery σ(1.1θ + 0.2 + 0.30ε₁); X₂ memory difficulty exp(0.7θ + 0.3 + 0.25ε₂); X₃ competitive rating 1200 + 250θ + 40ε₃; X₄ window success rate σ(0.9θ − 0.1 + 0.30ε₄)).

**Table 2. Baseline effective weights and Metric A drift (synthetic)**

| Quantity | Linear [0,1] | Quantile logit |
|---|---|---|
| π₁ (nominal 0.400) | **0.532 ± 0.026** | 0.403 ± 0.006 |
| π₂ (0.300) / π₃ (0.200) / π₄ (0.100) | 0.171 / 0.179 / 0.119 | 0.299 / 0.201 / 0.097 |
| L1 drift, affine (9 transforms) | **0.000000** | — |
| L1 drift, nonlinear monotone (7) | **0.127620** (SD 0.019553) | — |
| Mean rank reversal / proportion with reversal | 0.513 / **0.364** | 0.000 / 0.000 |
| Spearman vs. baseline weight | 0.8646 | — |

Metric B gives exactly zero drift under shared calibration and only linking sampling noise under independent calibration (0.0160 affine, 0.0159 nonlinear), with zero reversals. The strongest counterexample applies `logit_minmax` (strictly monotone) to X₁ mastery: baseline π⁽⁰⁾ = [0.5429, 0.1514, 0.1831, 0.1226] (order [1,3,2,4]) becomes π⁽ᵍ⁾ = [0.1983, 0.2840, 0.3110, 0.2068] (order [4,2,1,3]), L1 = 0.6893 with 3 rank reversals (complete reversal) and Spearman −0.20, while the quantile-logit metric gives |Δπ| = 0.000 with no reversal. Per source, the most severe transforms are: X₁ mastery under `logit_minmax` (L1 0.674, 95% interval [0.641, 0.709], mean reversal 2.835) and under `log` (0.193, [0.116, 0.325]); X₂ memory difficulty under `probit_std` (0.368, [0.274, 0.487]) and `exp_scaled` (0.286, [0.163, 0.343]); and X₃ competitive rating under `logit_minmax` (0.274, [0.248, 0.298]). The pattern is that sources already living on a bounded probability scale suffer most under logit-type reparameterisation—precisely the transform a practitioner reaches for when a signal "looks like a probability"—which makes this failure mode a live engineering hazard rather than a contrived edge case.

Two boundaries must be stated: this is entirely synthetic data, and the four sources sharing a single latent variable is the **most favourable** environment for commensurability—even so, linear fusion fails.

## 5 Real-Data Test I: Metric Repair and Two Negative Results

### 5.1 Data

**Table 3. Datasets, scale, and licence obligations**

| Dataset | Scale | Use | Licence |
|---|---|---|---|
| assist09 (revised) | 346,860 rows × 31 cols | three-source correlation, O1 drift, sliding-window distribution | cite Feng et al. (2009) |
| DBE-KT22 | 161,953 responses; 212 items; 1,264 students | O2 estimator, O4/O4b fusion | arXiv:2208.12651; DOI 10.26193/6DZWOH |
| XES3G5M | 4,806 items (≥100 responses) | O3 negative result | NeurIPS 2023; MIT |
| Junyi Academy | 16,217,311 rows; 72,758 users; 1,326 exercises | O5, O6, O7/O8 | CC-BY-NC-SA-4.0 (**commercial use prohibited**) |

Three calibers of the Junyi exercise count are used in this paper and must be distinguished, because mixing them is a common source of non-reproducibility: **1,326** library-wide exercises (all exercises in the Junyi exercise table with response data); **1,234** in the O5 fusion-reproduction caliber (adding the requirement that an exercise carry an expert-difficulty annotation and meet O5's minimum-response threshold); and **1,238** in the O10/O12 criterion-half caliber (requiring the B-half students to have ≥500 responses per exercise).

### 5.2 Real sources are weakly negatively correlated

On assist09's 994 items (≥50 responses), the three realistically available difficulty sources are pairwise **weakly negatively** correlated—a configuration impossible in the synthetic experiment: IRT difficulty ~ median first-attempt time ρ = −0.250; IRT difficulty ~ mean attempt count ρ = −0.134; first-attempt time ~ mean attempt count ρ = −0.302.

### 5.3 O1: metric repair on real data

**Table 4. O1: effective-weight drift under the two metrics (assist09, 994 items)**

| Fusion metric | L1 mean | Rank reversal |
|---|---:|---|
| A: min-max linear (status quo) | **0.5357** | significant |
| B: empirical CDF → logit | **0.0001** | **0** |

### 5.4 O2 and O3: two negative results

On DBE-KT22, replacing the raw correct-rate difficulty estimator with a joint IRT-1PL estimator (EM-style gradient, 300 rounds) moves agreement with expert grades only from ρ = 0.2207 to 0.2300: **changing the estimator is worth +0.009**. On XES3G5M we test the widely defaulted engineering assumption that the knowledge-component tree's hierarchical structure can serve as a difficulty proxy; it cannot, and we report this as a negative result (O3).

## 6 Real-Data Test II: Multi-Signal Fusion under the Expert-Label Criterion

Since changing the estimator helps little, O4 tests a different hypothesis: the bottleneck may be the single behavioural signal itself being information-poor.

**Table 5. O4/O5: multi-signal fusion gain under the expert-label criterion**

| Configuration | DBE-KT22 (212 items) | Junyi (1,234 exercises, no feedback) |
|---|---|---|
| Raw correct rate / success rate only | 0.2207 | 0.2610 |
| Joint IRT-1PL | 0.2300 | — |
| Equal-weight fusion (5 signals / 7 signals) | **0.2899** | **0.3629** (+39%) |
| Optimised weights, repeated 5-fold ×10 | **0.5240 ± 0.1069** [0.2895, 0.7390] | **0.4023 ± 0.0480** [0.3227, 0.4909] |

O4b adds three explicit features (difference term, dispersion, response count) and re-estimates by coordinate ascent: 0.4608 against O4's 0.4778, i.e. extended features add no gain and the differential feature is the driver. O6a subsamples k ∈ {10,…,500} responses per item (30 repeats) and shows the fusion gain **grows** with sample size rather than vanishing (Junyi paired win rate 1.00 at every k), so the gain is complementary information, not denoising. O6b (bootstrap 2000) confirms statistical robustness: Junyi Δ = +0.1017 [0.0726, 0.1325], one-sided p = 0.000; DBE Δ = +0.0723 [−0.0195, 0.1649], p = 0.059; three-grade quadratic-weighted Kappa improves from 0.1815 to 0.2595 (Junyi) and 0.1778 to 0.2370 (DBE).

**Table 6. O6a: sample efficiency — the fusion gain grows with k, so it is complementary information rather than denoising**

| k | Junyi success-only | Junyi fusion | paired win rate | DBE success-only | DBE fusion |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.1750 | 0.2260 | 1.00 | 0.2024 | 0.2316 |
| 50 | 0.2314 | 0.2929 | 1.00 | 0.2224 | 0.2493 |
| 100 | 0.2416 | 0.3099 | 1.00 | 0.2208 | 0.2654 |
| 500 | 0.2536 | 0.3380 | 1.00 | 0.2209 | 0.2779 |
| Full | 0.2610 | 0.3629 | — | 0.2170 | 0.2899 |

If the fusion benefit were merely multi-signal averaging of noise, it should shrink as sample size grows; instead it widens, and the paired win rate is 1.00 at every k on Junyi. This is the strongest available evidence that the added signals carry complementary information about difficulty rather than merely reducing variance.

## 7 Criterion Switch: Reversal, Correction, and a Deployable Rule

### 7.1 O7: the conclusion reverses

The consistency criterion above is **expert labels**, but what adaptive ranking needs is predicting real student performance. Splitting each item's responses into mutually exclusive block A (estimation, k slots) and block B (criterion, 250 slots) so that the two errors no longer share samples:

**Table 6. O7: conclusion reversal under holdout validation**

| Dataset | k = 10 | k = 200 | Fusion win rate |
|---|---|---|---|
| Junyi success-only → fusion | 0.6677 → 0.6410 (−0.0267) | 0.9509 → 0.8287 (**−0.1222**) | 0.00 |
| DBE success-only → fusion | 0.8083 → 0.6331 (−0.1752) | — | 0.00 |

The fusion loses at every sample size and on both datasets. We did not attribute this to tuning preference but inspected the configuration, and located one real directional error.

### 7.2 O8: locating and fixing a directional error

Dropping the upgrade-rate signal (`fused6`) reverses the sign: at k = 10 the variant ρ rises to 0.6880 with λ* = 0.70 and holdout ρ(λ*) = 0.6992, a **+3.43 pp** gain against the original fused7's +1.73 pp, whereas a three-signal variant shows essentially zero gain. λ* falls monotonically from 0.70 at k = 10 to 0.12 at k = 200, showing that how much fusion should contribute is a function of sample size.

### 7.3 O9 and O10: is λ*(k) deployable?

O9 fits (k₀, p) using only λ* from k ∈ {10, 50, 200} and evaluates at k = 25 and 100, which lie **within** the fit interval: at k = 25, λ̂ = 0.520 against an empirically half-split-picked 0.536, giving ρ 0.8103 → 0.8272 (+1.695 pp formula, +1.528 pp empirical, retention 111%); at k = 100, λ̂ = 0.239 against 0.230, +0.237 pp formula and +0.186 pp empirical (retention 128%). O10 addresses a sharper attack—that §7.2 split **records**, not students, so the errors are not independent—by splitting the 72,758 students instead: at k = 10 the λ̂-formula mixture (untuned) reaches 0.6995 against success-only 0.6631 (**+3.64 pp**) with λ̂ = 0.711 versus λ*_emp = 0.716, and at k = 25 λ̂ = 0.520 versus 0.521. The formula therefore survives an independent, untuned, student-level test.

### 7.4 O11/O12: `srw7` and the size of the surviving gain

A directionally wrong signal should be sign-corrected, not deleted, and each signal should be weighted by its reliability within the split-half. The resulting `srw7` estimator gives record-level gains of +3.823 pp at k = 10 down to +0.138 pp at k = 200, and student-level gains of **+4.283 pp at k = 10** (win rate 0.902, Wilcoxon p = 1.15e-66), +2.189 pp at k = 25, +0.951 pp at k = 50, +0.335 pp at k = 100, and **+0.102 pp at k = 200** (win rate 0.996). Three boundaries must be reported with these conclusions: the gain vanishes rapidly with sample size (student-level +0.335 pp at k = 100, +0.102 pp at k = 200), so for a mature question bank with hundreds of observations per item the fusion is not worth its complexity; the result is bounded to the assessed datasets and calibers; and the criterion change, not the estimator, is what reversed the conclusion.

**Table 8. O11/O12: `srw7` holdout gain (pp) relative to the success-rate-only baseline**

| k | Record-level `srw7` | Student-level `srw7` | Student-level win rate |
|---:|---:|---:|---:|
| 10 | +3.823 | **+4.283** | 0.902 |
| 25 | +2.025 | +2.189 | 1.000 |
| 50 | +0.930 | +0.951 | 1.000 |
| 100 | +0.391 | +0.335 | 0.998 |
| 200 | +0.138 | **+0.102** | 0.996 |

`fused6`—the delete-the-column fix—goes **negative** at student level for k ≥ 25 (−1.402 pp at k = 25, −6.804 pp at k = 200), whereas `srw7`—the sign-correct-and-weight-by-reliability fix—stays positive throughout. The contrast is the practical payload of §7: how one handles a directionally wrong signal determines whether the fusion helps or hurts.

## 8 The Optimal Error Rate: Descriptive Evidence and the Causal Side

### 8.1 Descriptive distribution

On assist09 (sorted by student and order_id, students with ≥20 items) a sliding window of W = 20 gives n = 286,150 windows.

**Table 7. assist09 sliding-window error-rate distribution (W = 20, n = 286,150)**

| Statistic | Value |
|---|---|
| Support points | **21 discrete** values |
| Mean error rate | **0.3511** |
| Median error rate | 0.30 (success 70%) |
| **Mode (single value)** | **error rate 0.25 — success rate 75%** (k = 5, 30,899 windows) |
| Mode bootstrap 95% set (200 resamples by student) | **{0.25}** (95.5% of resamples) |
| Window share, success 80–90% | 26.40% |
| Window share, success 80–85% | **19.64%** (k = 3, 4) |
| Window share, success 77–83% | 10.51% |

**Table 8. Robustness of the mode across filter calibers**

| Caliber | Windows (students) | Mean | Mode | Success rate at mode |
|---|---:|---:|---|---:|
| Full | 286,150 (2,314 / 4,217) | 0.3511 | k = 5 | 75% |
| Topic items only | 216,993 (2,112 / 4,217) | 0.3334 | k = 4 | 80% |
| No-help items | 231,125 (2,021 / 4,106) | 0.2183 | k = 3 | 85% |

Two readings are conservative and important. A large number of learning windows sit in the "overly difficult" region: the mean error rate 0.3511 is far above any version of an optimal value and the median 0.30 (success 70%) likewise; only 26.40% of windows fall in success 80–90% and 19.64% in 80–85%. And the mode is **not** in the 80–85% band: the single most frequent value is 75% success, and its bootstrap set is {0.25} in 95.5% of resamples. This descriptive distribution supports neither the 15.87% error rule nor the claim that "the measured mode falls in the 80–85% band"; the latter is refuted by the distribution itself.

### 8.2 The causal side

The preregistered causal design (dose construction, endpoint definition, AIPW/DR estimation, non-monotonicity test, robustness procedures) was executed on three public logs under a "freeze first, then touch the endpoint" identification strategy. It detected **no internal optimum**, μ(d) rises overall with dose, and the Junyi time-inverted negative control is significant, so all causal readings are downgraded to associational evidence. Of the seven preregistered hypotheses, H1 (linear fusion unstable under monotone reparameterisation) is tested and holds; H2 is partially tested with the criterion changed; H3 and H7 are not executed; H4 is executed but its premise is not supported; H5 (U-shaped dose response) is executed and not supported; H6 is partial.

**Table 9. Status of the seven preregistered hypotheses**

| Hypothesis | Status |
|---|---|
| H1 Linear fusion unstable under monotone reparameterisation | **Tested and holds** (§4 synthetic, §5.3 real) |
| H2 Unified scale improves calibration quality | **Partial**: ECE/Brier/target-hit rate not computed; criterion changed to expert-label consistency |
| H3 Stable ordering of four-source calibration error | **Not executed** (real source set differs; ECE not computed) |
| H4 Optimal error rate significantly above 15.87% | **Executed, premise not supported** — no internal optimum detected |
| H5 Dose–response curve non-monotone | **Executed, not supported** — μ(d) rises with dose; downgraded to associational |
| H6 Effect-decay ordering of the five premises | **Partial** — exploratory strata unestimable (each n < 3000) |
| H7 Optimal-interval heterogeneity by ability | **Not executed** |
| Additional: knowledge tree is not difficulty order | **Completed** (negative result, §5.4) |

## 9 Discussion

Three conclusions follow. **First, commensurability is an engineering property that can be repaired, not a philosophical stance**; the synthetic path (L1 0.1276 → 0, 36.4% reversal → 0%) and the real-data path (0.5357 → 0.0001) agree. **Second, an estimator's apparent quality depends entirely on the criterion**; agreement with expert labels is not evidence of decision value, and the same fusion that gains under the label criterion loses under held-out real performance. **Third, the deployable rule is conditional**: switch the metric to quantile logit unconditionally, then decide whether to enable multi-signal fusion by sample size, and before enabling it run a direct holdout validation. Part of these conclusions has landed in the studied system's code layer.

**One practical recommendation.** Synthesising the metric repair, the directional-error fix, the sample-size decay and the `srw7` optimisation, our recommendation for a difficulty-fusion module is one sentence: **first switch the metric to quantile logit (unconditional), then decide whether to enable multi-signal fusion by sample size (conditional), and before enabling it run a direct holdout validation.** The first step is free and removes the instability entirely; the second and third are necessary because the fusion gain is real but criterion-dependent and vanishes as evidence accumulates.

**Landed code changes.** Part of these conclusions has landed in the studied system's code layer in three places: the quantile-logit metric switch, the removal of the directionally wrong upgrade-rate signal, and the sample-size-adaptive shrinkage rule—the first two covered by regression tests and the third by an external verification script. We report this as evidence that the conclusions are actionable at the engineering level, not as evidence of their external validity.

## 10 Honest Gap Inventory

1. **Causal side executed, result negative**: AIPW/DR, dose–response and negative control were run under a frozen identification strategy; no internal optimum was detected and the Junyi negative control is significant, so the causal claims are downgraded to associational.
2. **Uneven preregistration fulfilment**: H3 and H7 not executed; H2's criterion changed (ECE/Brier/85% target-hit rate not computed); H6 only partially executed (exploratory strata each n < 3000, unestimable).
3. **Gain decays with sample size**: under `srw7` the student-level gain is +0.335 pp at k = 100 and +0.102 pp at k = 200, i.e. negligible for mature item banks.
4. **Synthetic boundary**: four sources sharing one latent variable is the most favourable case for commensurability, so the synthetic failure is a lower bound on severity.
5. **Source-set mismatch**: the real-data source set differs from the preregistered four sources.
6. **Licence constraint**: Junyi is CC-BY-NC-SA-4.0, commercial use prohibited.

## 11 Conclusions

We rewrote the question "can difficulty be measured on one common scale," which engineering practice had skipped, into a falsifiable measurement proposition, and answered it on synthetic data and four public learning-log corpora. **The caliber must be stated first: the real-data test of the proposition and the fusion gains are bounded to the assessed datasets, calibers, and criteria.** Within that caliber, three results stand: linear fusion of normalised difficulty sources is unstable and the instability is repairable by quantile linking (0.5357 → 0.0001); multi-signal fusion gains under an expert-label criterion but reverses under holdout validation, with a deployable but rapidly decaying correction in `srw7` plus λ*(k); and the descriptive error-rate distribution supports neither the 15.87% rule nor the 80–85% band claim. The single most transferable warning is that a consistency gain is not a predictive-power gain.

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
