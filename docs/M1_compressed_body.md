## Abstract

Adaptive learning systems must answer "what difficulty should the next item have?" every day, yet the prior question—whether difficulty is a quantity that can be placed on one common scale—is systematically skipped. We reformulate that question as a falsifiable measurement proposition and report three results. **First, we quantify the magnitude of the instability proposition (C1) on real systems.** The invariance side of the proposition is an identity, not a discovery (for strictly increasing g, #{g(x_cal) ≤ g(x)} = #{x_cal ≤ x}, so effective weights under the quantile metric are pointwise invariant); our contribution is to quantify how large the discrepancy becomes when that identity is violated. If difficulty sources are each normalised to [0,1] and then linearly combined, the effective weights defined by marginal contribution equal neither the nominal weights (π₁ = 0.532 ± 0.026 against nominal w₁ = 0.40 in simulation) nor themselves under a monotone reparameterisation of any single source: drift is exactly zero under affine transforms but averages L1 = 0.1276 (SD 0.0196) under nonlinear monotone transforms, with rank reversals in 36.4% of (source, transform) cells and complete sign reversal in the strongest counterexample (Spearman −0.20, L1 = 0.6893). An empirical-CDF-to-logit quantile metric gives exactly zero drift under shared calibration, 0.016 linking sampling noise under independent calibration, and zero reversals. On real data (assist09, 994 items), linear min-max fusion drifts by L1 = 0.5357 with substantial reversals, while the quantile metric reduces this to 0.0001 with reversals eliminated. **Second, the gain from multi-signal fusion is real under an expert-label criterion but reverses under a holdout criterion.** Five-signal fusion on DBE-KT22 raises agreement with expert labels from ρ = 0.2207 (raw correct rate) to 0.2899 (equal-weight) and 0.5240 ± 0.1069 (cross-validated optimised weights); on Junyi (1,234 exercises, no-feedback regime) seven-signal fusion raises ρ from 0.2610 to 0.3629 equal-weight and 0.4023 ± 0.0480 optimised. Yet once the criterion switches to real performance on held-out samples, the fusion loses at every sample size (Junyi −0.0267 to −0.1222, DBE −0.1752 to −0.2113, win rate 0.00). We trace part of this to a directional error, and show that sign correction plus reliability weighting (`srw7`) with sample-size-adaptive shrinkage λ*(k) recovers a deployable but rapidly decaying gain (+4.283 pp student-level at k = 10, +0.102 pp at k = 200). **Qualification (review §3.2 ③): when the criterion quantity is success rate, the success-rate estimator's dominance at large samples is design-expected; fusion's role is rank stabilisation at small samples.** **Third, we give descriptive evidence on the optimal error rate.** On assist09 the sliding-window error-rate distribution (W = 20, n = 286,150 windows) has only 21 discrete support points, mean 0.3511, median 0.30, and a single-value mode at error rate 0.25 (success 75%, 30,899 windows); the 80–85% success band occupies only 19.64%. Together with the fact that the 80–85% success band occupies only 19.64% of windows, this locates where the system actually operates. It is a distribution of **experienced difficulty** — the joint product of how ASSISTments allocates items and how capable its students are — **not a test of the optimal error rate**; about whether the 85% rule holds for real learners, this paper can say nothing. The preregistered causal analysis that would have borne on that question has been removed from this paper (§8.2).

**Keywords**: difficulty commensurability; measurement invariance; quantile linking; multi-signal fusion; holdout validation; optimal error rate; negative results

## 1 Introduction

### 1.1 A skipped question

No adaptive learning system can avoid "what difficulty should the next item have." The standard engineering practice is to normalise several quantities called "difficulty" or "ability"—the mastery probability of knowledge tracing, the memory difficulty of spaced repetition, the ability estimate of competitive rating, the window success rate—into [0,1] and then add them up with weights. This is convenient, but it silently assumes a property that is rarely tested: that these quantities are **commensurable**, i.e. that they live on one common scale on which addition and weighting are meaningful operations. We reformulate "commensurability" as a falsifiable measurement proposition rather than a design vocabulary, and we ask how large the violation is in practice.

### 1.2 Why this is not a technical detail

A few decimal points of weight drift might look negligible, but it determines the system's interpretability and tunability. If the weight vector "0.45 / 0.35 / 0.20" becomes a different vector once the knowledge-tracing side is changed from one monotone parameterisation to another, then the weights no longer mean anything a practitioner can set, audit, or tune: they are artefacts of an arbitrary choice of scale. This is the practical stake of the proposition.

### 1.3 Contributions

We make four contributions. (i) We turn "difficulty commensurability" from a design vocabulary into a computable, falsifiable proposition (C1) and quantify the violation; the invariance half of C1 is an analytic identity, and our contribution is the magnitude of the discrepancy when that identity is broken. (ii) We show the violation is repairable: switching the fusion metric from linear min-max to an empirical-CDF-to-logit quantile linking removes the drift entirely (0.5357 → 0.0001 on real data). (iii) We show that the apparent gain of multi-signal fusion is criterion-dependent and can reverse completely under holdout validation, and we isolate both a directional error and a deployable correction (`srw7` with λ*(k) shrinkage). (iv) We report the descriptive distribution of experienced difficulty on assist09 and state explicitly that it is not a test of any candidate optimal value; about the 85% rule this paper makes no claim. To prevent readers from inferring contributions from the title, we also state four explicit non-claims up front (§1.4 of the full paper).

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
| Mode bootstrap 95% set (200 resamples by student; review §3.3 requires ≥ 2,000 — rerun pending the assist09 source data) | **{0.25}** (95.5% of resamples; Monte Carlo standard error ≈ 1.5 percentage points) |
| Window share, success 80–90% | 26.40% |
| Window share, success 80–85% | **19.64%** (k = 3, 4) |
| Window share, success 77–83% | 10.51% |

**Table 8. Robustness of the mode across filter calibers**

| Caliber | Windows (students) | Mean | Mode | Success rate at mode |
|---|---:|---:|---|---:|
| Full | 286,150 (2,314 / 4,217) | 0.3511 | k = 5 | 75% |
| Topic items only | 216,993 (2,112 / 4,217) | 0.3334 | k = 4 | 80% |
| No-help items | 231,125 (2,021 / 4,106) | 0.2183 | k = 3 | 85% |

Two readings are conservative and important. A large number of learning windows sit in the "overly difficult" region: the mean error rate 0.3511 is far above any version of an optimal value and the median 0.30 (success 70%) likewise; only 26.40% of windows fall in success 80–90% and 19.64% in 80–85%. And the mode is **not** in the 80–85% band: the single most frequent value is 75% success, and its bootstrap set is {0.25} in 95.5% of resamples. This is a distribution of **experienced difficulty**, not a test of any candidate optimal value: about whether the 85% rule or the 80.7% value holds for real learners, this paper can say nothing. What the distribution does refute is a narrower *descriptive* claim — that the mode falls in the 80–85% success band — since the single most frequent value is 0.25 (75% success), and only 19.64% of windows fall in that band.
**The mode is not the optimum, and the RQ2 decision rule is abolished (review §3.3, 2026-09-29).** The most common speed on a motorway is 100 km/h, which does not show that 100 km/h is the most fuel-efficient — only that people drive that way; likewise this distribution is the distribution of **experienced difficulty** jointly produced by the item-allocation policy and student ability. The first two ranks differ by only **838 windows (0.29% of the total)** and the five support points spanning error rates 0.15–0.35 carry **49.3%** of all windows almost flatly, so the reported object of this section is the **shape** of the distribution, not the position of the mode. The former RQ2 falsification conditions (deviation of the mode from [0.15, 0.20]; exclusion of 0.1587 and 0.193 from the confidence set) **are abolished**: the support points are only multiples of 0.05, so 0.1587 and 0.193 could never have entered the set — the rule tests the discreteness of the support grid, not the optimal error rate. Per review §3.3 the bootstrap must be raised to **≥ 2,000** resamples; `BOOT` in `results/code/m1_real_data.py` has been set to 2000 accordingly, but the rerun needs the original assist09 data (`data/assist09_corrected.csv`), which is absent from this working copy, so the 2,000-resample result is pending and the 200-resample figures above are a record only, not a basis for conclusions (Monte Carlo standard error ≈ 1.5 percentage points, just above the 95% threshold). Wilson et al.'s optimal error rate under Cauchy noise happens also to be 0.25; **this paper claims nothing from that coincidence.**


### 8.2 The causal side — removed from this paper

The preregistered AIPW/DR dose–response analysis was executed on 2026-09-24. **It did not pass the preregistered positive-control criterion, and its implementation differs from the frozen protocol document in four places; its results are therefore not interpretable, and this paper makes no confirmatory reading of them.** Accordingly the causal side (the corresponding sections and hypotheses H4 and H5) has been **removed from this paper** and transferred to a separate fourth paper, listed as row 4 of the research-plan §7.1 table. A second version of the identification strategy must be committed and tagged before any re-execution; until then this paper makes no causal claim about the optimal error rate.

**Table 9. Status of the seven preregistered hypotheses**

| Hypothesis | Status |
|---|---|
| H1 Linear fusion unstable under monotone reparameterisation | **Tested and holds** (§4 synthetic, §5.3 real) |
| H2 Unified scale improves calibration quality | **Partial**: ECE/Brier/target-hit rate not computed; criterion changed to expert-label consistency |
| H3 Stable ordering of four-source calibration error | **Not executed** (real source set differs; ECE not computed) |
| H4 Optimal error rate significantly above 15.87% | **Removed from this paper** — transferred to the fourth paper (§8.2) |
| H5 Dose–response curve non-monotone | **Removed from this paper** — transferred to the fourth paper (§8.2) |
| H6 Effect-decay ordering of the five premises | **Partial** — exploratory strata unestimable (each n < 3000) |
| H7 Optimal-interval heterogeneity by ability | **Not executed** |
| Additional: knowledge tree is not difficulty order | **Completed** (negative result, §5.4) |

## 9 Discussion

Three conclusions follow. **First, commensurability is an engineering property that can be repaired, not a philosophical stance**; the synthetic path (L1 0.1276 → 0, 36.4% reversal → 0%) and the real-data path (0.5357 → 0.0001) agree. **Second, an estimator's apparent quality depends entirely on the criterion**; agreement with expert labels is not evidence of decision value, and the same fusion that gains under the label criterion loses under held-out real performance. **Third, the deployable rule is conditional**: switch the metric to quantile logit unconditionally, then decide whether to enable multi-signal fusion by sample size, and before enabling it run a direct holdout validation. Part of these conclusions has landed in the studied system's code layer.

**One practical recommendation.** Synthesising the metric repair, the directional-error fix, the sample-size decay and the `srw7` optimisation, our recommendation for a difficulty-fusion module is one sentence: **first switch the metric to quantile logit (unconditional), then decide whether to enable multi-signal fusion by sample size (conditional), and before enabling it run a direct holdout validation.** The first step is free and removes the instability entirely; the second and third are necessary because the fusion gain is real but criterion-dependent and vanishes as evidence accumulates.

**Landed code changes.** Part of these conclusions has landed in the studied system's code layer in three places: the quantile-logit metric switch, the removal of the directionally wrong upgrade-rate signal, and the sample-size-adaptive shrinkage rule—the first two covered by regression tests and the third by an external verification script. We report this as evidence that the conclusions are actionable at the engineering level, not as evidence of their external validity.

## 10 Honest Gap Inventory

1. **Causal side removed from this paper (review §2.2, 2026-09-29)**: the preregistered AIPW/DR dose–response analysis was executed on 2026-09-24, but it did not pass the positive-control criterion and its implementation differs from the frozen protocol document; its results are not interpretable and this paper makes no confirmatory reading of them. The causal side has been transferred to the fourth paper (see §8.2).
2. **Uneven preregistration fulfilment**: H3 and H7 not executed; H2's criterion changed (ECE/Brier/85% target-hit rate not computed); H6 only partially executed (exploratory strata each n < 3000, unestimable).
3. **Gain decays with sample size**: under `srw7` the student-level gain is +0.335 pp at k = 100 and +0.102 pp at k = 200, i.e. negligible for mature item banks.
4. **Synthetic boundary**: four sources sharing one latent variable is the most favourable case for commensurability, so the synthetic failure is a lower bound on severity.
5. **Source-set mismatch**: the real-data source set differs from the preregistered four sources.
6. **Licence constraint**: Junyi is CC-BY-NC-SA-4.0, commercial use prohibited.

## 11 Conclusions

We rewrote the question "can difficulty be measured on one common scale," which engineering practice had skipped, into a falsifiable measurement proposition, and answered it on synthetic data and four public learning-log corpora. **The caliber must be stated first: the real-data test of the proposition and the fusion gains are bounded to the assessed datasets, calibers, and criteria.** Within that caliber, three results stand: linear fusion of normalised difficulty sources is unstable and the instability is repairable by quantile linking (0.5357 → 0.0001); multi-signal fusion gains under an expert-label criterion but reverses under holdout validation, with a deployable but rapidly decaying correction in `srw7` plus λ*(k); and the descriptive error-rate distribution is a distribution of experienced difficulty rather than a test of the optimal error rate — about the 85% rule this paper can say nothing. The single most transferable warning is that a consistency gain is not a predictive-power gain.
