# Historical exploratory cache analyses

These are archival analyses, not results under the canonical all-transaction DBE definition. The cache excludes hidden transactions; it must not be pooled or paired with the all-transaction success baseline. Re-estimation and the decision on incorporating reliability weighting remain pending.

## 6 Real-Data Test II: Multi-Signal Fusion under the Expert-Label Criterion

Since changing the estimator helps little, O4 tests a different hypothesis: the bottleneck may be the single behavioural signal itself being information-poor.

**Table 5. O4/O5: multi-signal fusion gain under the expert-label criterion**

| Configuration | DBE-KT22 (212 items) | Junyi (1,234 exercises, no feedback) |
|---|---|---|
| Raw correct rate / success rate only | 0.2207 | 0.2610 |
| Joint IRT-1PL | 0.2300 | — |
| Equal-weight fusion (5 signals / 7 signals) | **0.2918** | **0.3629** (+39%) |
| Optimised weights, repeated 5-fold ×10 | **0.5240 ± 0.1069** [0.2895, 0.7390] | **0.4023 ± 0.0480** [0.3227, 0.4909] |

O4b adds three explicit features (difference term, dispersion, response count) and re-estimates by coordinate ascent: 0.4608 against O4's 0.4778, i.e. extended features add no gain and the differential feature is the driver. O6a subsamples k ∈ {10,…,500} responses per item (30 repeats) and shows the fusion gain **grows** with sample size rather than vanishing (Junyi paired win rate 1.00 at every k), so the gain is complementary information, not denoising. O6b (bootstrap 2000) confirms statistical robustness: Junyi Δ = +0.1017 [0.0726, 0.1325], one-sided p = 0.000; DBE Δ = +0.0723 [−0.0195, 0.1649], p = 0.059; three-grade quadratic-weighted Kappa improves from 0.1815 to 0.2595 (Junyi) and 0.1778 to 0.2370 (DBE).

**Table 6. O6a: sample efficiency — the fusion gain grows with k, so it is complementary information rather than denoising**

| k | Junyi success-only | Junyi fusion | paired win rate | DBE success-only | DBE fusion |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.1750 | 0.2260 | 1.00 | 0.2024 | 0.2316 |
| 50 | 0.2314 | 0.2929 | 1.00 | 0.2224 | 0.2493 |
| 100 | 0.2416 | 0.3099 | 1.00 | 0.2208 | 0.2654 |
| 500 | 0.2536 | 0.3380 | 1.00 | 0.2209 | 0.2779 |
| Full | 0.2610 | 0.3629 | — | 0.2170 | 0.2918 |

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
| Mode bootstrap 95% set (**2,000** resamples by student, seed 20260922; rerun on the assist09 source data on 2026-10-04 per review §3.3) | **{0.25, 0.20}** — k = 5 in **94.1%** and k = 4 in **5.95%** of resamples; k = 5 alone falls below 95%, so **the mode is not unique at the 95% threshold** (Monte Carlo standard error ≈ 0.5 pp; superseded 200-resample record: {0.25} at 95.5%, SE ≈ 1.5 pp) |
| Window share, success 80–90% | 26.40% |
| Window share, success 80–85% | **19.64%** (k = 3, 4) |
| Window share, success 77–83% | 10.51% |

**Table 8. Robustness of the mode across filter calibers**

| Caliber | Windows (students) | Mean | Mode | Success rate at mode |
|---|---:|---:|---|---:|
| Full | 286,150 (2,314 / 4,217) | 0.3511 | k = 5 | 75% |
| Topic items only | 216,993 (2,112 / 4,217) | 0.3334 | k = 4 | 80% |
| No-help items | 231,125 (2,021 / 4,106) | 0.2183 | k = 3 | 85% |

Two readings are conservative and important. A large number of learning windows sit in the "overly difficult" region: the mean error rate 0.3511 is far above any version of an optimal value and the median 0.30 (success 70%) likewise; only 26.40% of windows fall in success 80–90% and 19.64% in 80–85%. And the mode is **not** in the 80–85% band: the single most frequent value is 75% success, and with 2,000 student-level resamples its 95% set is {0.25, 0.20} (k = 5 at 94.1%, k = 4 at 5.95%) — 0.25 is the modal support point but it is **not unique at the 95% threshold**. This is a distribution of **experienced difficulty**, not a test of any candidate optimal value: about whether the 85% rule or the 80.7% value holds for real learners, this paper can say nothing. What the distribution does refute is a narrower *descriptive* claim — that the mode falls in the 80–85% success band — since the single most frequent value is 0.25 (75% success), and only 19.64% of windows fall in that band.
**The mode is not the optimum, and the RQ2 decision rule is abolished (review §3.3, 2026-09-29).** The most common speed on a motorway is 100 km/h, which does not show that 100 km/h is the most fuel-efficient — only that people drive that way; likewise this distribution is the distribution of **experienced difficulty** jointly produced by the item-allocation policy and student ability. The first two ranks differ by only **838 windows (0.29% of the total)** and the five support points spanning error rates 0.15–0.35 carry **49.3%** of all windows almost flatly, so the reported object of this section is the **shape** of the distribution, not the position of the mode. The former RQ2 falsification conditions (deviation of the mode from [0.15, 0.20]; exclusion of 0.1587 and 0.193 from the confidence set) **are abolished**: the support points are only multiples of 0.05, so 0.1587 and 0.193 could never have entered the set — the rule tests the discreteness of the support grid, not the optimal error rate. Per review §3.3 the bootstrap has been raised to **2,000** resamples (`BOOT` = 2000 in `results/code/m1_real_data.py`; rerun on the assist09 source data on 2026-10-04, seed 20260922): k = 5 now occupies 94.1% and k = 4 5.95%, giving a 95% set of **{0.25, 0.20}** with Monte Carlo standard error ≈ 0.5 percentage points. The increase **removed uniqueness at the 95% threshold** — the 200-resample record put k = 5 at 95.5% (SE ≈ 1.5 pp), just above the line; 2,000 resamples put it at 94.1%, below it — which is why the reported object here is the shape of the distribution (49.3% near-flat over 0.15–0.35; 838 windows, 0.29%, between the top two ranks) rather than the position of the mode. Wilson et al.'s optimal error rate under Cauchy noise happens also to be 0.25; **this paper claims nothing from that coincidence.**


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

