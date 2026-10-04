> ⚠️ **本快照已被取代（2026-09-29 审阅 2.2 节）。** 本文件是 2026-09-28 生成的投稿用事实清单快照，**生成于第二次审阅之前**。其中因果侧的"未检出内部最优 / Junyi 时间倒置阴性对照显著 / 全部剂量—反应读数降级为关联性证据"等读数**已被撤回**：当前口径为"已于 2026-09-24 执行，但未通过预注册的阳性对照标准、且实现与冻结文档不一致，故其结果不可解释"，因果侧已从 M1 拆出并转入第四篇论文。**当前口径请以 `docs/M1_submission_EN.md` 与 `docs/M1_submission_EN_compressed.md` 为准**，本文件仅作历史留档，勿直接用于投稿。
## Abstract

(Methodological contributions upfront: the two independently standing methodological conclusions of this paper are the quantile-logit metric invariance identity and the `srw7` sample-size-adaptive shrinkage weighting; the empirical negative results below are all presented within this framework.) Adaptive learning systems must answer "what difficulty should the next item have?" every day, yet the prior question—whether difficulty is a quantity that can be placed on one common scale—is systematically skipped. We reformulate that question as a falsifiable measurement proposition and report three results. **First, the magnitude of the instability proposition (C1) on real systems is quantified.** The invariance side of the proposition is an identity, not a discovery (Section 3.2: for strictly increasing g, #{g(x_cal) ≤ g(x)} = #{x_cal ≤ x}, so effective weights under the quantile metric are pointwise invariant); this paper's contribution is to quantify how large the discrepancy becomes when that identity is violated. If difficulty sources are each normalised to [0,1] and then linearly combined, the "effective weights" defined by marginal contribution equal neither the nominal weights (π₁ = 0.532 ± 0.026 against nominal w₁ = 0.40 in simulation) nor themselves under a monotone reparameterisation of any single source: drift is exactly zero under affine transforms (absorbed by min-max) but averages L1 = 0.1276 (SD 0.0196) under nonlinear monotone transforms, with rank reversals in 36.4% of (source, transform) cells and complete sign reversal in the strongest counterexample (Spearman −0.20, L1 = 0.6893). An empirical-CDF-to-logit quantile metric gives exactly zero drift under shared calibration, 0.016 linking sampling noise under independent calibration, and zero reversals. On real data (assist09, 994 items), linear min-max fusion drifts by L1 = 0.5357 with substantial reversals, while the quantile metric reduces this to 0.0001 with reversals eliminated. **Second, the gain from multi-signal fusion is a gain in consistency with expert labels, not in predictive power.** On DBE-KT22 (212 items), the rank correlation between expert and empirical difficulty is only 0.2207; a joint IRT-1PL estimator raises it merely to 0.2300, whereas equal-weight fusion of five behavioural signals (quantile metric) rises to 0.2899 and optimised weights under repeated 5-fold ×1

HEAD # Difficulty Commensurability and the Optimal Error Rate
  LEAD: Zexiao Weng¹ and MinPo Jung¹,*

HEAD ## Abstract
  LEAD: (Methodological contributions upfront: the two independently standing methodological conclusions of this paper are the quantile-logit metric invariance identity and the `srw7` sample-size-adaptive shrinkage weighting; the empirical negative results below are all presented within this framework.) Ada

HEAD ### 1.1 A skipped question
  LEAD: No adaptive learning system can avoid "what difficulty should the next item have." The standard engineering practice is to normalise several quantities called "difficulty" or "ability"—the mastery probability of knowledge tracing, the memory difficulty of spaced repetition, the ability estimate of c

HEAD ### 1.2 Why this is not a technical detail
  LEAD: One may ask: a few decimal points of weight drift—how much does it matter? It matters because it determines the system's interpretability and tunability. If the weight vector "0.45 / 0.35 / 0.20" becomes a different vector once the knowledge-tracing side is changed from `mastery × 9 + 1` to `mastery

HEAD ### 1.3 What this paper does not claim
  LEAD: To prevent readers from inferring contributions from the title by habit, we list four "non-claims" up front:

HEAD ### 1.4 Contributions and main findings
  LEAD: **Contribution 1: turn "difficulty commensurability" from a design vocabulary into a computable, falsifiable proposition, and quantify how large the violation is.** The side of the proposition stating "effective weights are invariant under the quantile metric" is an **analytic identity** (§3.2); we 

HEAD ### 1.5 Structure and reproducibility
  LEAD: §2 reviews related work; §3 formalises the typology of difficulty sources and the instability proposition; §4 reports the proposition's validation on synthetic data; §5 reports the metric repair on real data and two negative results; §6 reports the gain of multi-signal fusion under the expert-label 

CAP **Table 1. Random seeds and the random steps they affect**

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

HEAD ### 2.1 Knowledge tracing and the difficulty–ability confound
  LEAD: Deep knowledge tracing is the mainstream paradigm for predicting "the probability that a student answers the next item correctly," but its output is a **probability**, not difficulty. When a system uses this probability as a difficulty signal, the difficulty–ability confound arises: a high correct r

HEAD ### 2.2 Test equating and IRT linking
  LEAD: The equating literature solves "whether different test forms are comparable," sharing the same measurement-theoretic root as our "whether different difficulty-technique routes are comparable." Weber, Becker, Spinath, and Koch (2025) systematically compared five equating methods (MS, MM, MGM, IRF, TR

HEAD ### 2.3 Multi-signal difficulty estimation and the place of expert labels
  LEAD: The "difficulty" that adaptive ranking truly needs has long been assumed estimable from the single signal of correct rate. Ding et al. (2024), with Easy2Hard-Bench, use joint IRT and Glicko-2 calibration to provide difficulty labels for standardised LLM difficulty evaluation, representing the mainst

HEAD ### 2.4 The 85% rule, the challenge-point framework, and evidence on real learners
  LEAD: Wilson et al. (2019) derive, on a gradient-descent binary-classification learner, an optimal error rate of 15.87%, i.e., the "85% rule." This is a theorem about a specific learning algorithm, whose derivation depends on five premises: a binary-classification task, no hints, no skipping, no forgettin

HEAD ### 2.5 Off-policy evaluation: the preregistered toolbox and its execution (2026-09-24 supplement)
  LEAD: Adaptive learning systems almost never run online randomised controlled experiments; a student's item choice is jointly determined by the system strategy and self-selection, so "if this student were placed in another difficulty bracket, how would their mastery speed change" is a counterfactual quest

HEAD ### 3.1 Four difficulty sources and their scale types
  LEAD: Suppose the system holds four sources: knowledge-tracing mastery m ∈ [0,1], spaced-repetition memory difficulty D, competitive-rating ability θ_EL, and window success rate r ∈ [0,1]. Following the classical scale classification and the three-plane classification of difficulty measurement (constructi

CAP **Table 2. Four difficulty sources and their scale types**

| Source | Scale type | construction | scale | dependence |
|---|---|---|---|---|
| KT mastery m | bounded latent variable (approx. ordinal after integerisation) | machine-inferred | static, continuous | depends on real responses |
| SR memory difficulty D | ordinal scale | machine + human | dynamic, discrete | model-specific |
| EL competitive rating θ_EL | interval scale (log-odds scale) | machine | dynamic, continuous | not directly dependent on ground truth |
| WR window success rate r | ratio scale | machine | static, continuous | depends on real responses |

HEAD ### 3.2 Two metrics and their invariance
  LEAD: Let the fusion rule be S = Σ_k w_k · z_k, where z_k is the value of the k-th source after some mapping and w_k is the nominal weight. Define the **effective weight** by the marginal-contribution method:

CAP **Table 3. Two fusion metrics and their invariance to reparameterisation**

| Metric | Definition | Invariance to reparameterisation |
|---|---|---|
| A: linear [0,1] | min-max per column then linear weighting | **invariant only to affine y′ = ay + b** (absorbed by min-max); drifts under nonlinear monotone transforms |
| B: quantile logit | per column link via step empirical CDF to logit latent scale ψ = ln(p/(1−p)), p = (#{x_cal ≤ x} + 0.5)/(n + 1) | **strictly invariant to any strictly monotone transform** (rank invariance, analytic identity) |

HEAD ### 3.3 Proposition C1 and its testable implications
  LEAD: **Proposition C1 (instability).** If sources are each first normalised to [0,1] and then linearly combined, the effective weight π generally differs from the nominal weight w and drifts with any monotone reparameterisation of a single source; if sources are first linked through the empirical CDF to 

HEAD ### 4.1 Generative model and experimental setup
  LEAD: The purpose of this section is to test the proposition in an environment with a **known truth structure**, not to estimate any real-system parameter. Common latent ability θ ∼ N(0,1), sample size n = 500, calibration sample independently drawn n_cal = 500; the four sources are monotone functions of 

CAP **Table 4. Synthetic generative model**

| Source | Generative form | Scale |
|---|---|---|
| X₁ mastery | σ(1.1θ + 0.2 + 0.30ε₁) | probability [0,1] |
| X₂ memory difficulty | exp(0.7θ + 0.3 + 0.25ε₂) | positive scale (exponential) |
| X₃ competitive rating | 1200 + 250θ + 40ε₃ | wide linear scale |
| X₄ window success rate | σ(0.9θ − 0.1 + 0.30ε₄) | probability [0,1] |

HEAD ### 4.2 Baseline: effective weights already differ from nominal
  LEAD: **Table 5. Baseline effective weights already deviate from nominal weights**

| Metric | π₁ | π₂ | π₃ | π₄ |
|---|---|---|---|---|
| Nominal weight w | 0.400 | 0.300 | 0.200 | 0.100 |
| **Linear [0,1]** (mean ± SD) | **0.532 ± 0.026** | 0.171 ± 0.032 | 0.179 ± 0.009 | 0.119 ± 0.006 |
| **Quantile logit** | 0.403 ± 0.006 | 0.299 ± 0.006 | 0.201 ± 0.003 | 0.097 ± 0.003 |

HEAD ### 4.3 Metric A: affine-invariant, nonlinear-monotone drift
  LEAD: **Table 6. Metric A: affine-invariant, nonlinear-monotone drift**

| Transform family | L1 mean | L1 SD | mean rank reversal | proportion with reversal | Spearman vs. baseline weight |
|---|---|---|---|---|---|
| Affine (9) | **0.000000** | 0.000000 | 0.000 | 0.000 | 1.0000 |
| Nonlinear monotone (7) | **0.127620** | 0.019553 | 0.513 | **0.364** | 0.8646 |

CAP **Table 7. Most severe transform per source (L1 mean / 95% interval / mean reversal)**

| Source | Most severe transform | L1 mean | 95% interval | mean reversal |
|---|---|---|---|---|
| X₁ mastery | `logit_minmax` | 0.674 | [0.641, 0.709] | 2.835 |
| X₁ mastery | `log` | 0.193 | [0.116, 0.325] | 0.065 |
| X₂ memory difficulty | `probit_std` | 0.368 | [0.274, 0.487] | 0.670 |
| X₂ memory difficulty | `exp_scaled` | 0.286 | [0.163, 0.343] | 1.330 |
| X₃ competitive rating | `logit_minmax` | 0.274 | [0.248, 0.298] | 1.590 |

HEAD ### 4.4 Metric B: zero drift under shared calibration, sampling noise only under independent calibration
  LEAD: **Table 8. Metric B: zero drift under shared calibration, sampling noise only under independent calibration**

| Variant | Transform family | L1 mean | mean rank reversal | proportion with reversal |
|---|---|---|---|---|
| Shared calibration · same transform | all | **0.000000** | 0.000 | 0.000 |
| Independent calibration sample | affine | 0.0160 | 0.000 | 0.000 |
| Independent calibration sample | nonlinear | 0.0159 | 0.000 | 0.000 |

HEAD ### 4.5 Three counterexamples: information unchanged, weight-rank reversed
  LEAD: **Counterexample 1 (strongest):** applying `logit_minmax` (strictly monotone) to X₁ mastery, result of repeat 0:

CAP **Table 9. Counterexample 1 (strongest): X₁ mastery under logit_minmax**

| Item | Value |
|---|---|
| Baseline effective weight π⁽⁰⁾ | [0.5429, 0.1514, 0.1831, 0.1226], order [1, 3, 2, 4] |
| Transformed π⁽ᵍ⁾ | [0.1983, 0.2840, 0.3110, 0.2068], order [4, 2, 1, 3] |
| L1 | **0.6893** |
| Rank-reversal count | **3** (complete reversal) |
| Spearman vs. baseline weight | **−0.20** |
| |Δπ| of quantile-logit metric under same transform | **0.000** (no reversal) |

HEAD ### 4.6 Boundaries of the synthetic experiment (honest statement)
  LEAD: **This entire section is synthetic data**, the generation method is fully written out, and no external data is used. Three boundaries must be stated: first, the four sources sharing a single latent variable is the **most favourable** environment for the "commensurability" proposition—even so, linear

HEAD ### 5.1 Data, licences, and samples
  LEAD: **Table 10. Datasets, scale, use in this paper, and licence/citation obligations**

| Dataset | Scale | Use in this paper | Licence and citation obligation |
|---|---|---|---|
| assist09 (revised) | 346,860 rows × 31 cols (64,412,812 B) | three-source correlation, O1 metric drift, sliding-window error-rate distribution | cite Feng et al. (2009) and data page (URL verified before submission) |
| DBE-KT22 | 161,953 valid responses; 212 items; 1,264 students | O2 difficulty estimator, O4 / O4b multi-signal fusion | cite arXiv:2208.12651; ADA Dataverse DOI 10.26193/6DZWOH |
| XES3G5M | 4,806 items (≥100 responses with KC path); 7,652 items with item text | O3 knowledge-tree-structure negative result | cite NeurIPS 2023 Datasets & Benchmarks; MIT licence |
| Junyi Academy | 16,217,311 rows; 72,758 users; **1,326 exercises library-wide** | O5 cross-system reproduction, O6 sample efficiency and robustness, O7 / O8 holdout validation | CC-BY-NC-SA-4.0 (**commercial use prohibited**); cite Chang et al. (2015) |

CAP **Table 11. Three calibers of the Junyi exercise count**

| Caliber | Exercise count | Definition | Appears in |
|---|---|---|---|
| Library-wide | **1,326** | all exercises in the Junyi exercise table with response data | §5.1 Table 3-1, §5.4 |
| O5 fusion reproduction caliber | **1,234** | on top of 1,326, add O5 usability filter: exercise must have expert-difficulty annotation and meet O5's minimum-response threshold | §6.3, §6.4 |
| O10/O12 criterion-half caliber | **1,238** | on top of 1,326, require the criterion half (B-half students) to have ≥500 responses per exercise | §7.2 O10, §7.8 O12 |

HEAD ### 5.2 Real difficulty sources pairwise weakly negatively correlated: a form impossible in the synthetic experiment
  LEAD: On assist09's 994 items (≥50 responses), the Spearman correlations among the three realistically available difficulty sources are:

CAP **Table 12. Pairwise Spearman correlations among the three real difficulty sources on assist09**

| Source pair | Spearman ρ |
|---|---|
| IRT difficulty ~ median first-attempt time | **−0.250** |
| IRT difficulty ~ mean attempt count | −0.134 |
| First-attempt time ~ mean attempt count | **−0.302** |

HEAD ### 5.3 O1: from 0.5357 to 0.0001
  LEAD: On the same batch of 994 items, compare the two metrics' effective-weight drift under arbitrary monotone reparameterisation:

CAP **Table 13. O1: effective-weight drift under the two metrics (assist09, 994 items)**

| Fusion metric | L1 mean | Rank reversal |
|---|---|---|
| A: min-max linear (status quo) | **0.5357** | significant |
| B: empirical CDF → logit (quantile linking) | **0.0001** | **0** |

HEAD ### 5.4 O2: changing the estimator is only worth +0.009
  LEAD: On DBE-KT22 (1,264 students × 212 items), comparing two difficulty estimators against the expert-difficulty annotation (1 easy / 2 medium / 3 hard):

CAP **Table 14. O2: estimator comparison against expert difficulty on DBE-KT22**

| Estimator | Spearman ρ with expert grade |
|---|---|
| Raw correct-rate difficulty (baseline) | 0.2207 |
| **Joint IRT-1PL (EM-style gradient, 300 rounds)** | **0.2300** |

HEAD ### 5.5 O3: knowledge-tree structure is not difficulty order
  LEAD: On XES3G5M we test an assumption widely defaulted to in engineering practice but rarely explicitly tested: whether the hierarchical structure of the knowledge-component (KC) tree can serve as a difficulty proxy.

HEAD ### 6.1 O4: five-signal fusion on DBE-KT22 and a differential feature
  LEAD: O2 showed that changing the estimator helps little. O4 tests another hypothesis: **the bottleneck may not be the label but the single behavioural signal (correct rate) itself being information-poor**. Design: on DBE-KT22's 212 items (≥30 transactions per item) take five behavioural signals—success r

CAP **Table 15. O4: five-signal fusion on DBE-KT22 and a differential feature**

| Estimator | Spearman ρ with expert 1/2/3 |
|---|---|
| Raw correct rate (O2 baseline) | 0.2207 |
| Joint IRT-1PL (O2) | 0.2300 |
| **Five-signal equal-weight fusion** | **0.2899** |
| Optimised weights (greedy, in-sample) | 0.5306 |
| **Optimised weights · repeated 5-fold ×10 cross-validation** | **0.5240 ± 0.1069** (interval [0.2895, 0.7390]) |

HEAD ### 6.2 O4b: extended features add no gain, the differential feature is the driver
  LEAD: To test the mechanistic explanation rather than merely accept its fit, O4b adds three explicit features (explicit difference term, dispersion, response count) and re-estimates by coordinate ascent:

CAP **Table 16. O4b: extended features add no gain, the differential feature is the driver**

| Configuration | cross-validation ρ under repeated caliber | Note |
|---|---|---|
| O4 (5-signal full-grid greedy) | **0.4778** (single 5-fold; cite with caliber noted) | final cited configuration |
| O4b (8 features, coordinate ascent) | 0.4608 | does not exceed O4 |

HEAD ### 6.3 O5: cross-system reproduction on Junyi (no-feedback regime)
  LEAD: The key difference between Junyi and DBE is: Junyi **has no student self-report feedback field**, a "performance-signal-only" regime. This exactly tests how much of O4's gain survives on a feedback-free system.

CAP **Table 17. O5: cross-system reproduction on Junyi (no-feedback regime)**

| Estimator (Junyi, 1,234 exercises) | Spearman ρ with expert easy/normal/hard |
|---|---|
| Success rate only | 0.2610 |
| **Seven-signal equal-weight fusion** | **0.3629** (+39% vs. baseline) |
| Coordinate-ascent optimised · repeated 5-fold ×10 | **0.4023 ± 0.0480** (interval [0.3227, 0.4909]) |

HEAD ### 6.4 O6a: sample efficiency — the gain is complementary information, not denoising
  LEAD: If the fusion benefit were merely "multi-signal averaging out noise," the benefit should vanish as sample size grows. O6a uses reservoir sampling to give, for each item, random subsamples of any k ∈ {10, …, 500} responses (30 repeats per bracket) to test this.

CAP **Table 18. O6a: sample efficiency — the gain is complementary information, not denoising**

| k | Junyi success-only | Junyi fusion | paired win rate | DBE success-only | DBE fusion | paired win rate |
|---|---|---|---|---|---|---|
| 10 | 0.1750 | 0.2260 | 1.00 | 0.2024 | 0.2316 | 0.87 |
| 25 | 0.2116 | 0.2640 | 1.00 | 0.2113 | 0.2399 | 0.77 |
| 50 | 0.2314 | 0.2929 | 1.00 | 0.2224 | 0.2493 | 0.83 |
| 100 | 0.2416 | 0.3099 | 1.00 | 0.2208 | 0.2654 | 0.97 |
| 250 | 0.2496 | 0.3269 | 1.00 | 0.2213 | 0.2725 | 1.00 |
| 500 | 0.2536 | 0.3380 | 1.00 | 0.2209 | 0.2779 | 1.00 |
| Full | 0.2610 | 0.3629 | — | 0.2170 | 0.2899 | — |

HEAD ### 6.5 O6b: statistical robustness (bootstrap 2000 and repeated cross-validation)
  LEAD: **Table 19. O6b: statistical robustness (bootstrap 2000 and repeated cross-validation)**

| Quantity | Junyi | DBE |
|---|---|---|
| Success-only ρ [95% CI] | 0.2606 [0.2112, 0.3101] | 0.2167 [0.0809, 0.3476] |
| Equal-weight fusion ρ [95% CI] | 0.3623 [0.3149, 0.4094] | 0.2890 [0.1563, 0.4127] |
| Paired difference Δ [95% CI] | **+0.1017 [0.0726, 0.1325]** | **+0.0723 [−0.0195, 0.1649]** |
| One-sided p(Δ ≤ 0) | **0.000** | **0.059** |
| Three-grade quadratic-weighted Kappa (success-only → fusion) | 0.1815 → 0.2595 | 0.1778 → 0.2370 |
| Repeated 5-fold ×10 (50 folds) optimised-weight ρ | **0.4023 ± 0.0480** | **0.5240 ± 0.1069** |

HEAD ### 7.1 The distance between expert labels and real-performance difficulty
  LEAD: The consistency criterion of O4 and O5 is **expert difficulty labels**. But what adaptive ranking truly needs is "predicting real student performance." These are not the same construct, and their distance is directly measurable:

HEAD ### 7.2 O7: conclusion reversal under holdout validation
  LEAD: The method splits each item's reservoir slots into mutually exclusive block A (for estimation, k slots) and block B (for criterion, 250 slots), so that estimation error and criterion error no longer share samples. After switching the criterion to "real performance on unseen samples":

CAP **Table 20. O7: conclusion reversal under holdout validation**

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

HEAD ### 7.3 O8: locating and fixing a directional error
  LEAD: Faced with the above reversal, we did not attribute it to "tuning preference" but inspected the fusion configuration itself. The inspection located one real error:

CAP **Table 21. O8: locating and fixing a directional error**

| Variant | k | success ρ / variant ρ | λ* | holdout ρ(λ*) | gain vs. success rate |
|---|---|---|---|---|---|
| fused7 (O5 original) | 10 | 0.6702 / 0.6431 | 0.52 | 0.6871 | +1.73 pp |
| **fused6 (drop upgrade rate)** | 10 | 0.6659 / **0.6880** | 0.70 | **0.6992** | **+3.43 pp** |
| fused6 | 25 | 0.8109 / 0.7974 | 0.52 | 0.8273 | +1.57 pp |
| fused6 | 50 | 0.8810 / 0.8487 | 0.39 | 0.8878 | +0.73 pp |
| fused6 | 100 | 0.9257 / 0.8748 | 0.23 | 0.9271 | +0.22 pp |
| fused6 | 200 | 0.9504 / 0.8899 | 0.12 | 0.9502 | +0.05 pp |
| fused3 (success + hint + attempt) | 10–200 | — | 0.04–0.08 | — | ≈ 0 (no gain) |

HEAD ### 7.4 Sample-size-adaptive shrinkage λ*(k)
  LEAD: λ* falls monotonically from 0.70 at k = 10 to 0.12 at k = 200, showing that "what fraction fusion should occupy" is a function of sample size. The fitted form is

HEAD ### 7.5 Leave-one-k cross-validation of λ*(k) (O9): in-interval interpolation test, formula directly deployable
  LEAD: The λ*(k) of §7.4 was both fit and evaluated on the same batch of k, and cannot be taken directly as a deployment rule. The first test of O9 is precisely for this: fit (k₀, p) using only λ* from k ∈ {10, 50, 200}, then evaluate at k = 25 and k = 100—which lie **within** the fit interval [10, 200]—by

CAP **Table 22. O9: leave-one-k cross-validation of λ*(k) (in-interval interpolation)**

| Validation k (in-interval) | λ̂ (formula) | λ*_emp (half-split picked) | ρ(λ=0) | ρ(λ̂) | formula gain | empirical gain | retention ratio |
|---|---|---|---|---|---|---|---|
| 25 | 0.520 | 0.536 | 0.8103 | **0.8272** | **+1.695 pp** | +1.528 pp | **111%** |
| 100 | 0.239 | 0.230 | 0.9262 | **0.9286** | **+0.237 pp** | +0.186 pp | **128%** |

HEAD ### 7.6 Student-level holdout validation (O10): empirical test of the record-level concern
  LEAD: The holdout validation in §7.2 split **records**, not **students**: the same student's multiple responses could fall into both blocks A and B, so the two errors are not independent, making "optimistic generalisation estimate" a reasonable attack. O10 directly addresses this gap: split the 72,758 stu

CAP **Table 23. O10: student-level holdout validation**

| k | Success-only | fused7 (O5 config) | fused6 | mix6 (λ̂ formula, **untuned**) | λ̂ | λ*_emp | λ̂ gain | fused6 raw gain |
|---|---|---|---|---|---|---|---|---|
| 10 | 0.6631 | 0.6442 | 0.6870 | **0.6995** | 0.711 | 0.716 | **+3.64 pp** | +2.39 pp |
| 25 | 0.8133 | 0.7418 | 0.7993 | **0.8297** | 0.520 | 0.521 | +1.64 pp | −1.40 pp |
| 50 | 0.8881 | 0.7838 | 0.8491 | 0.8944 | 0.368 | 0.355 | +0.63 pp | −3.90 pp |
| 100 | 0.9356 | 0.8101 | 0.8783 | 0.9372 | 0.239 | 0.200 | +0.16 pp | −5.73 pp |
| 200 | 0.9603 | 0.8234 | 0.8922 | 0.9605 | 0.144 | 0.093 | +0.02 pp | −6.81 pp |

HEAD ### 7.7 Three boundaries (must be reported together with the conclusions)
  LEAD: **First, the gain vanishes rapidly with sample size.** Under this paper's final recommended `srw7` estimator, the holdout gain is student-level +0.335 pp at k = 100 and +0.102 pp at k = 200 (record-level +0.391 / +0.138 pp, §7.8 Tables 7-1, 7-2). For a mature question bank (hundreds of observations 

HEAD ### 7.8 O11/O12: optimising the fusion estimator — sign correction and split-half-reliability weighting
  LEAD: §7.3 attributed the reversal to one directional error and fixed it by "dropping the upgrade rate" (fused6). O11 and O12 test a further hypothesis: **a directionally wrong signal should be sign-corrected, not deleted column-wise**; on top of that, **weighting per signal by its reliability within the 

CAP **Table 7-1. Record-level holdout gain (O11, relative to "success-rate-only" baseline, unit pp, λ = λ_cf)**

| k | Success-only (held-out) | fused6 | fused7 | signed7 | rw6 | **srw7** | λ_cf | λ_rel | λ*_emp |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 0.6698 | +3.278 | +1.498 | +3.594 | +3.616 | **+3.823** | 0.7107 | 0.7010 | 0.7000 |
| 25 | 0.8060 | +1.586 | +0.523 | +1.930 | +1.829 | **+2.025** | 0.5197 | 0.4902 | 0.5270 |
| 50 | 0.8824 | +0.659 | +0.181 | +0.850 | +0.806 | **+0.930** | 0.3678 | 0.3136 | 0.3723 |
| 100 | 0.9248 | +0.243 | +0.073 | +0.327 | +0.335 | **+0.391** | 0.2383 | 0.1881 | 0.2370 |
| 200 | 0.9502 | +0.071 | +0.013 | +0.111 | +0.108 | **+0.138** | 0.1440 | 0.1041 | 0.1333 |

CAP **Table 7-2. Student-level holdout gain (O12, unit pp)**

| k | Success-only | fused6 | **srw7 (λ_cf)** | srw7 − fused6 | win rate | Wilcoxon p |
|---|---|---|---|---|---|---|
| 10 | 0.6631 | +2.390 | **+4.283** | +0.662 | 0.902 | 1.15e-66 |
| 25 | 0.8133 | −1.402 | **+2.189** | +0.557 | 1.000 | 1.26e-83 |
| 50 | 0.8881 | −3.905 | **+0.951** | +0.317 | 1.000 | 1.26e-83 |
| 100 | 0.9356 | −5.728 | **+0.335** | +0.169 | 0.998 | 1.27e-83 |
| 200 | 0.9603 | −6.804 | **+0.102** | +0.081 | 0.996 | 1.29e-83 |

HEAD ### 8.1 The sliding-window error-rate distribution on assist09
  LEAD: On assist09 (sorted by student, by order_id, taking those with ≥20 items), a sliding window of width W = 20 computes each window's error rate.

CAP **Table 8-1. assist09 sliding-window error-rate 21 discrete support-point frequencies** (n = 286,150 windows; students actually contributing

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

CAP **Table 24. Summary statistics of the assist09 sliding-window error-rate distribution (computed exactly from support-point frequencies)**

| Statistic | Value |
|---|---|
| Mean error rate | **0.3511** |
| Median error rate | **0.30** (success rate 70%) |
| **Mode (single value)** | **error rate 0.25, i.e., success rate 75%** (k = 5, 30,899 windows) |
| Mode's bootstrap 95% set (**2,000** resamples by student, seed 20260922; rerun on assist09 source data 2026-10-04 per review §3.3) | **{0.25, 0.20}** — k = 5 in **94.1%**, k = 4 in **5.95%**; k = 5 alone falls below 95%, so the mode is **not unique at the 95% threshold** (Monte Carlo SE ≈ 0.5 pp; superseded 200-resample record: {0.25} at 95.5%, SE ≈ 1.5 pp) |
| Window share with success rate 77–83% | 10.51% (only k = 4 falls in this interval) |
| Window share with success rate 80–90% | **26.40%** (k = 2, 3, 4) |
| Window share with success rate 80–85% | 19.64% (k = 3, 4) |

CAP **Table 25. Robustness of the mode across three filter calibers (recomputed by integer error count)**

| Filter caliber | windows (students) | mean error rate | mode support point | success rate |
|---|---|---|---|---|
| Full | 286,150 (2,314 / 4,217) | 0.3511 | k = 5 | 75% |
| Topic items only (`original = 1`) | 216,993 (2,112 / 4,217) | 0.3334 | k = 4 | 80% |
| No-help items (`hint_count = 0`) | 231,125 (2,021 / 4,106) | 0.2183 | k = 3 | 85% |
| `tutor_mode = test` (not valid) | 0 (0 / 30) | — | — | — |

HEAD ### 8.2 What this distribution shows and does not show
  LEAD: Two things it shows are conservative. First, **a large number of learning windows sit in the "overly difficult" interval**—the mean error rate 0.3511 is far above any version of the optimal value, and the median 0.30 (success 70%) is likewise; only 26.40% of windows fall in success 80–90%, 19.64% in

HEAD ### 8.3 Execution of the causal side: preregistered AIPW/DR executed under a frozen identification strategy (2026-09-24 supplement)
  LEAD: The causal-side design of the original preregistration (dose construction, endpoint definition, AIPW/DR estimation, non-monotonicity test, supporting robustness procedures) was executed on three public logs under the identification strategy of "freeze first, then touch the endpoint" (LF-CIS-2026-09-

HEAD ### 8.4 Status of preregistered hypotheses
  LEAD: To help readers judge the relationship between this paper and the original design, the following table gives the fulfilment status of the seven hypotheses item by item:

CAP **Table 26. Status of preregistered hypotheses**

| Hypothesis | Content | Status |
|---|---|---|
| H1 | Linear fusion is unstable under monotone reparameterisation | **Tested and holds** (§4 synthetic, §5.3 real) |
| H2 | Unified scale improves calibration quality and target-hit rate | **Partially tested**: ECE / Brier / reliability diagram / 85% target-hit rate not computed; switched to comparing fusion schemes by expert-label consistency (§6), criterion changed |
| H3 | Four-source calibration error has a stable ordering | **Not executed**: the real-data source set differs from the preregistered four sources, ECE not computed |
| H4 | Optimal error rate significantly above 15.87% | **Executed (2026-09-24), premise not supported**: preregistered AIPW/DR detected no internal optimum (§8.3), the "optimal-position" test's premise fails, so no point test against 15.87% is reported |
| H5 | Dose–response curve is non-monotone | **Executed (2026-09-24), U-shape not supported**: μ(d) rises overall with dose (more prior errors, slower mastery); Junyi time-inverted negative control significant, all readings downgraded to associational evidence (§8.3) |
| H6 | Effect-decay ordering of the five premises | **Partial**: exploratory stratification by hint rate × item type is unestimable (each stratum n<3000); the five-premise decomposition retains qualitative discussion (§2.4), formal ordering test not executed |
| H7 | Optimal-interval heterogeneity under ability stratification | **Not executed** |
| — | Additional finding: knowledge-tree structure is not difficulty order | **Completed** (§5.5, negative result) |

HEAD ### 9.1 Three conclusions
  LEAD: **First, commensurability is an engineering property that can be repaired, not a philosophical stance.** The synthetic experiment (L1 0.1276 → 0, 36.4% reversal → 0%) and the real data (0.5357 → 0.0001) give the same conclusion along two independent paths: changing the sources from "linearly add aft

HEAD ### 9.2 Implications for the system and three landed code changes
  LEAD: Part of the above conclusions has landed in the studied system's code layer, in three places (the first two covered by regression tests, the third by an external verification script):

HEAD ### 9.3 Limitations
  LEAD: **First, the causal side is executed but the result is negative.** §8.3 lists it: the preregistered AIPW/DR was executed under a frozen identification strategy (2026-09-24), detected no internal optimum, μ(d) rises overall with dose, and the Junyi time-inverted negative control is significant—so thi

HEAD ### 9.4 One practical recommendation
  LEAD: Synthesising §5.3, §7.3, §7.7, and §7.8, this paper's practical recommendation for the difficulty-fusion module is one sentence: **first switch the metric to quantile logit (unconditional), then decide whether to enable multi-signal fusion by sample size (conditional), and before enabling, do direct

HEAD ## 10 Honest Gap Inventory
  LEAD: 1. **Causal side executed, result negative (2026-09-24):** the preregistered AIPW/DR, dose–response estimation, and negative control were executed under a frozen identification strategy (§8.3); result is no detected internal optimum, significant Junyi negative control (downgraded to associational ev

HEAD ## 11 Conclusions
  LEAD: This paper rewrote the question "can difficulty be measured on one common scale," which engineering practice had skipped, into a falsifiable measurement proposition, and gave results on synthetic data and four public learning-log corpora. **The caliber must be stated first:** the **real-data test of

HEAD ## References
  LEAD: [1] Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10(1), 4646. DOI: 10.1038/s41467-019-12552-4.