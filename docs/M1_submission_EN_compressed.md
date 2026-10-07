# Commensurability of Difficulty Scales: Fusion Instability and Criterion-Bounded Evaluation

Zexiao Weng¹

¹ Youngsan University, Busan 48015, Republic of Korea

Sole and corresponding author: Zexiao Weng (wengzexiao). ORCID: 0009-0009-8600-8954.

## Abstract

Adaptive learning systems combine several signals called difficulty, although their scales and evaluation criteria differ. We quantify the instability of linear min-max fusion under monotone reparameterisation and examine how the apparent benefit of fusion changes with the criterion. In synthetic experiments, nonlinear monotone transforms produce mean L1 effective-weight drift of 0.1276 and rank reversals in 36.4% of source-transform cells. On assist09, the real-data drift is 0.5357 under min-max fusion and 0.0001 under quantile linking. Rank invariance under shared quantile calibration is an identity; the empirical contribution is the size of the instability under linear fusion. Two criterion comparisons bound the estimator claim. On DBE-KT22, equal-weight five-signal fusion has higher observed teacher-label agreement than the success-rate baseline (Spearman 0.2918 versus 0.2204), but the paired difference interval includes zero (−0.0184 to 0.1627). On Junyi, using an independent B-half IRT item parameter as criterion and estimating both predictors on A-half responses, success rate agrees more closely than seven-signal fusion (0.9541 versus 0.8923). These are different datasets and signal sets, so the contrast establishes criterion-bounded performance rather than an isolated causal effect of changing the criterion. On assist09, 49.3% of 286,150 practice windows have error rates between 0.15 and 0.35; 2,000 student-level bootstrap samples yield the 95% modal set {0.25, 0.20}. This describes experienced difficulty and does not identify an optimal practice error rate. The results support two engineering requirements: specify the linking scale and state the independent criterion before interpreting a fusion gain.

**Keywords**: difficulty commensurability; measurement invariance; quantile linking; criterion dependence; educational measurement

## 1 Introduction

### 1.1 A skipped question

No adaptive learning system can avoid "what difficulty should the next item have." The standard engineering practice is to normalise several quantities called "difficulty" or "ability"—the mastery probability of knowledge tracing, the memory difficulty of spaced repetition, the ability estimate of competitive rating, the window success rate—into [0,1] and then add them up with weights. This is convenient, but it silently assumes a property that is rarely tested: that these quantities are **commensurable**, i.e. that they live on one common scale on which addition and weighting are meaningful operations. We reformulate "commensurability" as a falsifiable measurement proposition rather than a design vocabulary, and we ask how large the violation is in practice.

### 1.2 Why this is not a technical detail

A few decimal points of weight drift might look negligible, but it determines the system's interpretability and tunability. If the weight vector "0.45 / 0.35 / 0.20" becomes a different vector once the knowledge-tracing side is changed from one monotone parameterisation to another, then the weights no longer mean anything a practitioner can set, audit, or tune: they are artefacts of an arbitrary choice of scale. This is the practical stake of the proposition.

### 1.3 Contributions

We quantify instability under monotone reparameterisation, compare fusion against two independently defined criteria, and describe experienced difficulty without identifying an optimal target. The mathematical invariance of shared rank linking is a construction property; the empirical contribution is the measured discrepancy under linear fusion and the limits of interpreting estimator agreement.

## 2 Related Work

Deep knowledge tracing predicts response correctness; its output is not an item difficulty parameter independent of learner ability. Treating it as such can confound difficulty with ability. Test equating addresses the comparability of different test forms and provides a measurement-theoretic context (Weber, Becker, Spinath & Koch, 2026). Easy2Hard-Bench (Ding et al., 2024) uses IRT and Glicko-2 in different benchmark domains to provide difficulty labels for LLM evaluation. Wilson et al. (2019) derive an optimal error rate of 15.87% for a specified binary-classification learning model. That result is not evidence that the same rate optimizes a human mathematics tutor. Off-policy estimation provides a separate framework for causal evaluation; it does not turn the descriptive analyses reported here into randomized evidence.

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

Let S = Σ_k w_k z_k, with fixed nonnegative nominal weights satisfying Σ_k w_k = 1, and nondegenerate score variance Var(S) > 0. We define the effective contribution as

π_k = w_k Cov(z_k, S) / Var(S).

Hence Σ_k π_k = 1, because Σ_k w_k Cov(z_k, S) = Cov(S, S). With covariance matrix Σ, the vector is π = w ⊙ (Σw) / (wᵀΣw). This is a covariance-based variance allocation, not a causal contribution or a partial derivative. A component can be negative when sources oppose one another; the vector need not lie in the probability simplex. Equality π = w requires (Σw)_k = wᵀΣw for every component with nonzero nominal weight. For orthogonal columns of equal variance, π_k = w_k² / Σ_j w_j², which equals w only for equal nonzero weights. Equal marginal scales alone therefore do not make effective and nominal weights equal.

Metric A applies columnwise min-max normalization, z_k = (x_k − min x_k)/(max x_k − min x_k), on the same evaluation sample. Positive affine reparameterizations leave this mapping unchanged. Nonlinear increasing transformations need not do so and can change its covariance allocation.

Metric B uses a fixed common calibration sample and maps each observation through p = (#{x_cal ≤ x} + 0.5)/(n_cal + 1), followed by logit(p). If a strictly increasing transformation is applied both to the evaluation values and the corresponding calibration values, all comparisons x_cal ≤ x are preserved. Thus mapped values, S, and π are exactly unchanged. The same calibration sample, tie rule and source orientation are essential. Strictly decreasing transformations require an explicit orientation reversal and are not covered directly.

### 3.3 Proposition C1

**Proposition C1 (bounded invariance statement).** Min-max fusion is invariant to positive affine transformations, but is not generally invariant to nonlinear strictly increasing reparameterization. Under the shared calibration conditions stated above, quantile-logit fusion and its covariance-based effective contributions are invariant to strictly increasing reparameterization. This does not imply π = w. The rank-invariance part follows from preservation of order comparisons; the empirical question is the size and direction of instability under linear normalization. Independent calibration samples introduce estimation variability rather than violating the shared-sample identity.

## 4 Synthetic Validation

We test C1 in an environment with known truth structure: common latent ability θ ∼ N(0,1), n = 500 with an independent calibration sample n_cal = 500, the four sources being monotone functions of θ with source-specific noise (X₁ mastery σ(1.1θ + 0.2 + 0.30ε₁); X₂ memory difficulty exp(0.7θ + 0.3 + 0.25ε₂); X₃ competitive rating 1200 + 250θ + 40ε₃; X₄ window success rate σ(0.9θ − 0.1 + 0.30ε₄)).

**Table 2. Baseline effective weights and Metric A drift (synthetic)**

| Quantity | Linear [0,1] | Quantile logit |
|---|---|---|
| π₁ (nominal 0.400) | **0.532 ± 0.026** | 0.403 ± 0.006 |
| π₂ (0.300) / π₃ (0.200) / π₄ (0.100) | 0.171 / 0.179 / 0.119 | 0.299 / 0.201 / 0.097 |
| L1 drift, affine (9 transforms) | **0.000000** | — |
| L1 drift, nonlinear monotone (7) | **0.127620** (SD 0.019553) | — |
| Mean rank reversal / proportion with reversal | 0.513 / **0.364** | Not aggregated for shared-calibration clipped transforms |
| Spearman vs. baseline weight | 0.8646 | — |

For the four-source experiment, the largest shared-calibration component deviation under the implemented transform library is 0.002726, arising from `logit_minmax`. This function clips evaluation-range endpoints and calibration values outside that range, creating new ties; it is not globally strictly increasing and therefore falls outside the exact invariance proposition. The corresponding three-source maximum is 0.002901. Under independent calibration the mean L1 drift is 0.0160 for affine and 0.0159 for nonlinear transformations. Those empirical deviations must not be represented as an exact-zero result for the complete implementation library. One recorded counterexample applies `logit_minmax` (increasing within its unclipped range) to X₁ mastery: baseline π⁽⁰⁾ = [0.5429, 0.1514, 0.1831, 0.1226] (per-source ranks [1,3,2,4]) becomes π⁽ᵍ⁾ = [0.1983, 0.2840, 0.3110, 0.2068] (per-source ranks [4,2,1,3]), L1 = 0.6893 with 3 of the 6 source-pair orderings reversed and Spearman −0.20, while the quantile-logit metric gives |Δπ| = 0.000 with no reversal. Per source, the most severe transforms are: X₁ mastery under `logit_minmax` (L1 0.674, 95% interval [0.641, 0.709], mean reversal 2.835) and under `log` (0.193, [0.116, 0.325]); X₂ memory difficulty under `probit_std` (0.368, [0.274, 0.487]) and `exp_scaled` (0.286, [0.163, 0.343]); and X₃ competitive rating under `logit_minmax` (0.274, [0.248, 0.298]). The pattern is that sources already living on a bounded probability scale suffer most under logit-type reparameterisation—precisely the transform a practitioner reaches for when a signal "looks like a probability"—which makes this failure mode a live engineering hazard rather than a contrived edge case.

Two boundaries must be stated: this is entirely synthetic data, and the four sources sharing a single latent variable is a deliberately correlated environment for commensurability—even so, linear fusion fails.

## 5 Real-Data Test I: Metric Repair and Two Negative Results

### 5.1 Data

**Table 3. Datasets, scale, and licence obligations**

| Dataset | Scale | Use | Licence |
|---|---|---|---|
| assist09 (revised) | 346,860 rows × 31 cols | three-source correlation, O1 drift, sliding-window distribution | cite Feng et al. (2009) |
| DBE-KT22 | 161,953 responses; 212 items; 1,264 students | O2 estimator, O4/O4b fusion | arXiv:2208.12651; DOI 10.26193/6DZWOH |
| XES3G5M | 4,806 items (≥100 responses) | O3 negative result | NeurIPS 2023; MIT |
| Junyi Academy | 16,217,311 rows; 72,758 users; 1,326 exercises | O5, O6, O7/O8 | CC-BY-NC-SA-4.0 (**commercial use prohibited**) |

Junyi sample counts are analysis-specific. The library description reports 1,326 exercises; the A1 student-half criterion analysis includes 1,274 items with at least 500 B-half responses. Historical O5 and O10 summaries use additional screening rules and are not substituted for the current A1 analysis count.

### 5.2 Real sources are weakly negatively correlated

On assist09's 994 items (≥50 responses), the three realistically available difficulty sources are pairwise **weakly negatively** correlated—a configuration impossible in the synthetic experiment: IRT difficulty ~ median first-attempt time ρ = −0.250; IRT difficulty ~ mean attempt count ρ = −0.134; first-attempt time ~ mean attempt count ρ = −0.302.

### 5.3 O1: metric repair on real data

**Table 4. O1: effective-weight drift under the two metrics (assist09, 994 items)**

| Fusion metric | L1 mean | Rank reversal |
|---|---:|---|
| A: min-max linear (status quo) | **0.5357** | significant |
| B: empirical CDF → logit | **0.0001** | **0** |

### 5.4 O2 and O3: two negative results

A historical exploratory cache, using a different DBE transaction filter, reports success-rate agreement 0.2207 and joint 1PL agreement 0.2300. Those values are not paired with the current all-transaction A2 comparison in §6. The historical analysis is kept in the supplementary record and does not establish an estimator improvement. XES3G5M provides a separate exploratory test of knowledge-component hierarchy as a difficulty proxy; its near-zero result does not explain the mechanism of failure.

## 6 Fusion performance across criterion-specific settings

### 6.1 External teacher labels on DBE-KT22

A2 and O4 use the same five-signal builder. All transactions are eligible; feedback is averaged over rows carrying a value; durations satisfy 0 ≤ d < 3,600 seconds; average ranks map through (rank − 0.5)/n to logit. Signals are oriented toward greater difficulty before equal-weight fusion. Teacher difficulty labels have three ordered levels and are used for evaluation rather than as one of the five predictors.

**Table 5. Canonical DBE-KT22 evaluation against teacher labels, 212 items**

| Estimator | Spearman correlation |
|---|---:|
| Success-rate baseline | 0.2204 |
| Equal-weight five-signal fusion | 0.2918 |
| Optimised weights evaluated on the fitting sample | 0.5367 |
| Five-fold evaluation of optimised weights, mean | 0.4862 |

The observed equal-weight difference is 0.0714. A paired item bootstrap with 2,000 resamples and seed 20261007 gives a 95% percentile interval [−0.0184, 0.1627] for fusion minus success-rate correlation. The interval includes zero, so a teacher-label advantage is not established. Relative percentage gains are not used to imply significance. The optimised fitting-sample value is reported separately from cross-validation and is not an out-of-sample estimate. Each individual signal gives correlation 0.2204 for inverse success, −0.1176 for hints, 0.0453 for difficulty feedback, 0.2603 for inverse trust and 0.2434 for duration. Weak and oppositely directed components make the definition of the signal set material to the interpretation.

### 6.2 Independent IRT criterion on Junyi

A1 splits students by the fixed O10 student rule. Both success-rate and seven-signal fusion estimates use A-half responses; IRT-1PL item parameters are fitted from B-half responses. There are 1,274 eligible items, 32,563 B-half respondents and 1,845,035 responses used for IRT fitting, with at least 500 B-half responses per item.

**Table 6. Junyi A-half estimators against B-half IRT item parameters**

| Estimator | Spearman correlation with B-half item parameter |
|---|---:|
| A-half inverse success rate | 0.9541 |
| A-half equal-weight seven-signal fusion | 0.8923 |

The observed success-rate estimator is closer to the IRT criterion. Paired item bootstrap gives fusion-minus-success difference −0.0617, with 95% percentile interval [−0.0730, −0.0520] (2,000 resamples, seed 20261007). Estimating both predictors on A prevents either one from sharing the criterion's B-half sampling noise. The two predictors themselves correlate at 0.9404 within A. The intervals condition on the fitted criterion and predictors and do not refit IRT or resample learners. The criterion uses 25 EM iterations and a cap of the first 1,500 stored B-half responses per item, with 1,845,035 retained responses from 32,563 students. Formal convergence, item-fit and cap/order sensitivity are not established; these are limitations of treating the fitted 1PL parameter as a criterion, not evidence of its measurement validity.

**Figure 1. Paired criterion-specific correlation differences.** Points show fusion-minus-success Spearman differences; bars are conditional 95% percentile intervals from 2,000 item resamples. The DBE interval includes zero. Junyi and DBE use different datasets and signal definitions; the display is not a controlled criterion-switch experiment.

[Figure 1 about here]

### 6.3 What the contrast establishes

The point-estimate ordering differs across settings, but the DBE teacher-label advantage is not confirmed by its paired interval. On the independent Junyi IRT criterion, fusion has lower correlation within the stated conditional bootstrap analysis. Agreement with expert labels therefore cannot be presented as a general estimator superiority claim. Because these comparisons also differ in dataset, signal availability and criterion construction, they do not isolate the effect of changing only the criterion. The success-rate criterion is structurally close to an estimator based on success rate; this is an expected advantage that must be stated when interpreting that comparison.

Older O6–O12 cache analyses exclude hidden DBE transactions and use a different rank-link convention. They are preserved as historical exploratory material in the supplementary working record, not combined with the canonical all-transaction baseline above. A common-definition rerun is required before using them to extend the present estimator claim.

## 7 Experienced difficulty on assist09

Responses are ordered within student and windows contain 20 responses. Exact integer error counts define 21 support points, avoiding floating-point histogram boundary artifacts. There are 286,150 windows from 2,314 contributing students out of 4,217 students in the input. Mean error rate is 0.3511 and median is 0.30.

**Table 7. Distribution shape and student-level uncertainty**

| Quantity | Value |
|---|---:|
| Windows at error rates 0.15–0.35 | 141,064 (49.3%) |
| Gap between two most frequent support points | 838 windows (0.29%) |
| Modal support point | 0.25 |
| Minimum cumulative 95% bootstrap modal set | {0.25, 0.20} |
| Bootstrap frequency of 0.25 and 0.20 | 0.9410 and 0.0595 |
| Success-rate band 80–85%, inclusive endpoints | 19.64% |
| Success-rate band 75–80%, inclusive endpoints | 21.30% |
| Success-rate band 70–75%, inclusive endpoints | 20.76% |

The entire analysis output was regenerated from the assist09 CSV, using 2,000 student-level resamples and seed 20260922. Bootstrap modal frequencies and support-point table entries are produced by the same execution. These frequencies concern which support point becomes an argmax after resampling, not confidence in the optimal practice target. The broad near-flat region, and the small gap between its two leading values, are the relevant descriptive findings. Windows overlap within student and the distribution is jointly determined by learner ability and item allocation.

The first causal-analysis implementation did not pass its positive-control standard and differed from its frozen protocol; its output is not interpreted. Causal analysis proceeds as a separate study.

## 8 Discussion

The instability comparison answers a measurement question: a numerical fusion weight can change its effective contribution when one input is monotonically reparameterised. Shared quantile linking removes the ranking component of that instability by construction, but it does not establish that the input signals measure one construct, nor that equal numerical weights are scientifically optimal. The real-data test of C1 is limited to assist09; the additional datasets serve different questions.

The criterion comparisons answer an evaluation question. Under teacher labels, additional behavioural signals have higher observed agreement but an uncertain difference; under a held-out IRT item parameter, success rate is closer. This pattern requires stating what difficulty means operationally before selecting an estimator. It is not evidence that either criterion measures learning gain. Teacher ratings, response-derived parameters and later learning outcomes are distinct targets.

The experienced-error distribution answers a descriptive question. Its concentration over 0.15–0.35 and its two-point modal set do not justify converting the mode into a practice target. A learning-gain claim requires independent outcomes after random assignment of practice conditions. The current study contains no such experiment.

## 9 Limitations and conclusion

The C1 real-data test uses one corpus, and the shared-latent-variable simulation does not establish cross-domain validity. A1 and A2 have different datasets and signal sets; A2 uses one teacher-label source without inter-rater evidence. The canonical all-transaction analysis and historical hidden-transaction-excluded cache are different specifications. Reliability weighting and cold-start holdout findings remain in historical exploratory material pending a common-definition rerun. No human experiment identifies an optimal practice target.

Within these boundaries, linear fusion instability is measurable and can be reduced by rank linking; estimator comparisons are bounded by their dataset, signal definitions and declared criterion; and experienced difficulty is not an optimum. These conclusions require separate measurement and learning-outcome evaluations.

## Data, code and study scope

This study collects no new participant data. It uses publicly released educational datasets for secondary computational analysis. Dataset access and redistribution follow the original providers’ terms. Analysis artifacts, script names, input hashes and software versions are documented in the accompanying reproducibility guide; a final immutable public code release and venue-specific availability statement remain to be prepared. No new participant ethics approval number or exemption determination is asserted. The paper evaluates measurement behavior and does not estimate a causal effect on learning.

## AI assistance disclosure

The author reports using WorkBuddy and Codex, and identifies ChatGPT, DeepSeek and Hy4 as tools/models used during project and manuscript preparation. Codex assisted with code repair, stored-data analysis, reference checking and manuscript revision in this revision. Exact model versions, dates, and the mapping between tools and individual tasks remain to be documented. The author retains responsibility for the manuscript and must personally verify the final text, calculations, citations and code before submission. This disclosure does not assert that that final personal review has already occurred.

## References

[1] Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10(1), 4646. DOI: 10.1038/s41467-019-12552-4.

[2] Baillifard, A., Belardi, A., & Martarelli, C. S. (2025). Engagement beyond success rate: Evidence from an adaptive learning system. In The Envisioning Report for Empowering Universities (9th ed., pp.56–59). European Association of Distance Teaching Universities. https://doi.org/10.5281/zenodo.15908735

[3] Guadagnoli, M. A., & Lee, T. D. (2004). Challenge point: A framework for conceptualizing the effects of various practice conditions in motor learning. *Journal of Motor Behavior*, 36(2), 212–224. DOI: 10.3200/JMBR.36.2.212-224.

[4] Hodges, N. J., & Lohse, K. R. (2022). An extended challenge-based framework for practice design in sports coaching. *Journal of Sports Sciences*, 40(7), 754–768. DOI: 10.1080/02640414.2021.2015917.

[5] Weber, D., Becker, N., Spinath, F. M., & Koch, M. (2026). The stability of IRT parameters under several test equating conditions. Frontiers in Psychology, 16, 1652341. https://doi.org/10.3389/fpsyg.2025.1652341

[6] Deng, J. (2025). Linking errors introduced by rapid guessing responses when employing multigroup concurrent IRT scaling. *Large-scale Assessments in Education*, 13, 28. DOI: 10.1186/s40536-025-00265-8.

[7] Liu, Z., Guo, T., Liang, Q., Hou, M., Zhan, B., Tang, J., Luo, W., & Weng, J. (2025). Deep learning based knowledge tracing: A review, a tool and empirical studies. *IEEE Transactions on Knowledge and Data Engineering*, 37(8), 4512–4536. DOI: 10.1109/TKDE.2025.3552759.

[8] Ding, M., Deng, C., Choo, J., Wu, Z., Agrawal, A., Schwarzschild, A., Zhou, T., Goldstein, T., Langford, J., Anandkumar, A., & Huang, F. (2024). Easy2Hard-Bench: Standardized difficulty labels for profiling LLM performance and generalization. Advances in Neural Information Processing Systems, 37. https://doi.org/10.52202/079017-1407

[9] Dudík, M., Langford, J., & Li, L. (2011). Doubly robust policy evaluation and learning. *Proceedings of the 28th International Conference on Machine Learning (ICML)*.

[10] Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., & Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. *The Econometrics Journal*, 21(1), C1–C68. DOI: 10.1111/ectj.12097.

[11] VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in observational research: Introducing the E-value. *Annals of Internal Medicine*, 167(4), 268–274. DOI: 10.7326/M16-2607.

[12] Feng, M., Heffernan, N. T., & Koedinger, K. R. (2009). Addressing the assessment challenge with an online system that tutors as it assesses. User Modeling and User-Adapted Interaction, 19(3), 243–266. https://doi.org/10.1007/s11257-009-9063-7

[13] Abdelrahman, G., Abdelfattah, S., Wang, Q., & Lin, Y. (2022). DBE-KT22: A knowledge tracing dataset based on online student evaluation. arXiv:2208.12651. https://arxiv.org/abs/2208.12651v1

[14] Liu, Z., Liu, Q., Guo, T., Chen, J., Huang, S., Zhao, X., Tang, J., Luo, W., & Weng, J. (2023). XES3G5M: A knowledge tracing benchmark dataset with auxiliary information. Advances in Neural Information Processing Systems, 36, 32958–32970. https://doi.org/10.52202/075280-1429

[15] Chang, H.-S., Hsu, H.-J., & Chen, K.-T. (2015). Modeling exercise relationships in e-learning: A unified approach. In Proceedings of the 8th International Conference on Educational Data Mining (pp. 532–535). International Educational Data Mining Society. https://www.educationaldatamining.org/EDM2015/uploads/papers/paper_47.pdf

[16] Kolen, M. J., & Brennan, R. L. (2014). Test equating, scaling, and linking: Methods and practices (3rd ed.). Springer. https://doi.org/10.1007/978-1-4939-0317-7

[17] Platt, J. C. (2000). Probabilities for SV machines. In A. J. Smola, P. L. Bartlett, B. Schölkopf, & D. Schuurmans (Eds.), Advances in large-margin classifiers (pp. 61–74). MIT Press. https://doi.org/10.7551/mitpress/1113.003.0008

[18] Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. In Proceedings of the 34th International Conference on Machine Learning (Proceedings of Machine Learning Research, Vol. 70, pp. 1321–1330). https://proceedings.mlr.press/v70/guo17a.html

[19] Efron, B., & Tibshirani, R. J. (1993). An introduction to the bootstrap. Chapman & Hall.

[20] Cohen, J. (1968). Weighted kappa: Nominal scale agreement with provision for scaled disagreement or partial credit. Psychological Bulletin, 70(4), 213–220. https://doi.org/10.1037/h0026256

[21] Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. Journal of the Royal Statistical Society: Series B (Methodological), 57(1), 289–300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x

[22] Al-Fawakhiri, N., Kayani, S., & McDougle, S. D. (2023). Evidence of an optimal error rate for motor skill learning [Preprint]. bioRxiv. https://doi.org/10.1101/2023.07.19.549705

[23] Yeung, C.-K. (2019). Deep-IRT: Make deep learning based knowledge tracing explainable using item response theory. In Proceedings of the 12th International Conference on Educational Data Mining (pp. 683–686). International Educational Data Mining Society. https://educationaldatamining.org/edm2019/proceedings/
