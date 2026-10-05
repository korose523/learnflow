# Reliability-Structured Composite Difficulty Estimation

Zexiao Weng¹

¹ Youngsan University, Busan 48015, Republic of Korea

Corresponding author: to be assigned on approval of the final manuscript. ORCID: 0009-0009-8600-8954.

> **Byline and corresponding-author fields withheld pending approval (supervisor review items 2.4③ and §10, 2026-09-29).** This manuscript previously carried a second author and a named corresponding author (name, email and ORCID). Under the supervisor's review those fields must not appear in the submission, the Zenodo contributor list, or the AI-use statement until the corresponding author has read and approved the final manuscript. The corresponding author has agreed to serve in that role; the byline, the corresponding-author contact, and the contributor list will be restored in the manner they consent to once the final version is approved.

AI-Assisted Writing Disclosure. This manuscript was prepared with the assistance of large language models (LLMs) and AI coding agents. These tools were used, to varying extents, for: (i) generating and editing analysis scripts; (ii) executing and re-running experiments; (iii) drafting, translating and polishing manuscript text; (iv) drafting internal revision-tracking documents. The claim made in an earlier version of this disclosure — that the LLM "was used strictly as a language-polishing and drafting aid" and that no LLM participated in analytical, statistical or experimental work — **has been withdrawn**, because it is not consistent with the traces visible in the accompanying repository (supervisor's review §2.3, 2026-09-29). The per-task division of work between the author and these tools, and the scope of the author's own verification of each tool output, is recorded by the author in the role-and-tools table of the dissertation proposal (§10.1) and will be stated here in its final form before submission. The corresponding author has **not** yet reviewed and approved this disclosure; accordingly, and per review §10, the corresponding author's name is withheld from this manuscript until the final version is approved. All numerical results reported here were produced by the scripts in the accompanying repository and are reproducible from them.

**Numeric baseline (review §2.1).** All asset and count figures quoted in this manuscript (registered mechanisms, learning methods, service modules, code lines, API endpoints, test files and collected tests) are stated at the **unified baseline git tag `v1.1-submit`**, recomputed on the merged tree by `learnflow-backend/scripts/verify_asset_numbers.py --doc-check` and `learnflow-backend/scripts/verify_counts.py`; cross-document agreement across the proposal, the research report, the journal-split plan and M1–M4 is enforced by `scripts/verify_cross_doc_numbers.py`. M4 is not submitted as an independent manuscript (review §4.4); for any quantity shared with M1, M1 is authoritative.

> **Not submitted as an independent manuscript (review §4.4, 2026-09-29).** This manuscript is **not submitted as an independent paper**. Reason: its empirical part rests on the same basis as M1 — the same cache (`difficulty_cache.npz`), the same DBE-KT22 teacher labels (212 items), the same Junyi labels, the same block-B holdout, the same λ_cf and the same `srw7`; both papers call the DBE teacher labels the only exogenous criterion and both make the criterion-dependence of fusion a core conclusion, so the overlap is too large. Moreover M4's P2 re-runs M1's `srw7` holdout and reports +4.33 pp at k = 10, where M1 writes +3.823 pp for the same quantity — the same quantity appearing with different values in two manuscripts is itself the problem raised by §3.3 of the first review.
> **Handling**: the valuable content (the general form of reliability weighting and its limits) will either be folded into M1's methods section as a subsection, or be discussed only after a preregistered confirmatory test on an entirely different dataset. **That choice is decided on 2026-11-03; no new experiment is added before then.** This manuscript is therefore **not submitted as an independent paper alongside M1**; until that decision it is a **methods-discussion draft only**.

> **Note on review item 4.1 (2026-09-29): the missing cross-reference has been fixed.** M1 did not previously cite M4; this manuscript now cites M1 as [`weng2026m1`] in its reference list, removing the one-way citation problem. For any quantity that shares a name with M1, **M1's value governs**.

## Abstract

In the cold-start phase of an adaptive learning system, item difficulty cannot be taken directly from external labels and must instead be estimated by combining multiple log signals (success rate, hint rate, attempt count, self-report, trust, duration, etc.). The deployed `srw7` estimator (sign correction + split-half reliability weighting + sample-size shrinkage λ(k)) treats reliability directly as the combination weight. This paper proposes M4 — a reliability-structured combination chain — which improves `srw7` at four structural points: M4-A estimates the signal covariance on **rank correlation** to be robust to the tails of the ECDF–logit transform; M4-B gives the optimal linear combination weight β = V⁻¹q (q_k = sgn_k√ρ_k) under a single-factor model, where V⁻¹ **automatically removes inter-column collinearity**; M4-C makes λ = Σ|β_aux|/Σ|β| a **diagnostic quantity rather than a hyperparameter**; and M4-D assigns each item a local reliability via the Spearman–Brown formula under partial observability. We first give an **analytic proof and numerical companion of Proposition P1**: under additively separable log-odds evidence, pairwise Bradley–Terry aggregation and weighted linear combination yield the same ranking (ρ(d,u) = 1.000000; convergence certificate ‖∇ℓ‖_∞ = 1e-11; all 384 solves converged). The two realistic sources of separability violation — probability-domain averaging (what LLM judges actually do) and per-pair missingness — break this identity, and our mechanism diagnosis shows that probability-domain averaging **implicitly moves toward precision weighting** (ρ(BT prob-mean, precision-weighting) = 0.96404, higher than ρ(u_α, precision-weighting) = 0.939289). **This diagnosis is made on synthetic data, not a measurement on real LLM outputs; the boundary on the real-LLM side is set by M3 (caliber note in §3).**. We then report a **negative result** on an **exogenous** criterion (DBE-KT22 teacher difficulty labels, Kendall τ_b): the full M4 estimator (M4-A/B/C) **collapses** as sample size grows (k=10 τ_b = 0.1596 → k=200 τ_b = 0.0796, Δ = −0.0903, fusion win-rate 0.00), because the auxiliary signals are highly collinear with the success rate while M4's derived λ rises with k (0.7449 → 0.8734) even though the out-of-fold optimal λ actually approaches 0 (0.015). Motivated by this, we propose **M4-E (residualization)**, which removes each auxiliary signal's redundant component relative to the reference column (success rate), keeps only the incremental part, and mixes it back under λ — and this **repairs** the collapse (k=200 τ_b = 0.1718, Δ = +0.0019, paired t = 5.66, win-rate 0.90). On a **secondary** criterion (Junyi platform difficulty labels), the original full M4 estimator wins on every comparison (k=200 Δ = +0.0708, win-rate 1.00), and M4-E remains positive (Δ = +0.0073, win-rate 1.00). In §3.2 we give a formal proof that **reliability ≠ validity**, and on that basis we argue that the negative results of §3.1/§5.2 are not numerical noise but a structural manifestation of the mismatch between "reliability optimization" and the "validity target" in M4; any claim of an M4 gain must be re-examined against an exogenous criterion.

**Keywords**: difficulty combination estimation; reliability-structured weight; Bradley–Terry; additive separability; residualization; Kendall τ_b; negative results; exogenous criterion

## 1 Introduction

### 1.1 The combination problem that was skipped

The closed loop of "what difficulty to present next" consists of three stages: measurement (how difficulty becomes commensurable, M1), combination (how multiple log signals are fused into one difficulty score, this paper), and decision (how the difficulty score drives item selection, M3). The middle combination stage is usually handled **implicitly** in engineering — `srw7` serially stitches together "sign correction + split-half reliability weighting + sample-size shrinkage" without answering a prior question: **when several signals are mutually correlated and each carries a different reliability, what should the combination weights be?** This omission can fail on two falsifiable structural properties. First, **collinearity** between signals: `attempt_count` and `duration` both inflate together when a student is stuck, so weighting each by its reliability would double-count the same information. Second, reliability ≠ validity: an auxiliary signal with very high reliability (e.g., student self-report) that has no incremental correlation with the teacher's true difficulty only amplifies noise if weighted more heavily. This paper rewrites both properties as measurable propositions and tests on an exogenous criterion whether M4 actually improves the combination.

### 1.2 From design to execution: what we actually did, and why

This paper was executed from algorithm ideas optimized out of the supervisor-recommended archive (`submission_20260922.zip`, papers R1–R12). During execution we encountered, and honestly report, a result that runs against the "better" intuition: on the **exogenous** DBE-KT22 teacher-label criterion, the structurally "more correct" M4 (M4-A/B/C) is actually worse than `srw7` and collapses as sample size grows. This negative result is not an implementation bug but a boundary of M4-B's single-factor-model assumption — when an auxiliary signal carries specific variance that is "collinear with the success rate but uncorrelated with teacher difficulty," β = V⁻¹q weights it more heavily. Motivated by this, we appended M4-E (residualization), which constrains the combination term to "the increment beyond the success rate," and measured that it repairs the collapse. This appendage is the most engineering-valuable part of the paper and a direct application of the "reliability ≠ validity" theoretical boundary.

This paper has a clearly demarcated division of labor with its companion papers M1/M2/M3. M1 answers "how difficulty becomes commensurable" (ECDF–logit rank linking, holdout validation, sign correction, and split-half-reliability-weighted `srw7`); M2 answers "how conflicts in a system with coexisting interventions are governed"; M3 answers "ordinal difficulty decisions and the reliability boundary of a single-model LLM difficulty prior." This paper (M4) answers the fourth question in between — **under cold-start conditions with only logs and no external difficulty labels, how should multiple difficulty signals be combined**. M4 neither contains nor modifies M1's `difficulty_fusion` layer (the claim that estimators such as `srw7` are special cases of M4 has been withdrawn; see §3.3); its holdout validation follows M1's protocol framework but uses an independent script and artifacts. The priority statement that used to stand here is withdrawn (see the note immediately below).
**Withdrawn priority statement and withdrawn degeneration claim (review §4.1 / §4.2, 2026-09-29).** The sentence previously standing here — that for identical quantities the values in this paper's `m4_results.json` take precedence — **is withdrawn**: it inverts the direction that the first review required of M3 (defer to M1). For any quantity bearing the same name as one in M1, **M1's value takes precedence**. It is also recorded as an open item that M1 never mentions M4 and that M4's reference list contains no M1 entry. For the same reason this paper **no longer claims that `srw7` is a special case of M4**: per review §4.2 that degeneration claim does not hold — when V = I, M4's weight is sign × √ρ whereas `srw7`'s weight is ρ; the two are standardised differently; and `srw7` retains the λ_cf mixture while `m4_full` removes it.

### 1.3 Literature progress and our positioning

Multi-signal difficulty fusion has produced two sharply opposed camps on the LLM-annotation side. The **optimistic camp**, represented by Ballon, Algaba, Verbeken, and Ginis (2025, LLMcompare), uses LLM pairwise comparison + Bradley–Terry aggregation and reaches Pearson r ≥ 0.80 with human annotation. The **pessimistic camp**, represented by Li, Chen, Xiao, Chen, Jiao, and Zhou (2026, `li2026canllms`, Findings of ACL 2026), finds across 20+ models × 4 domains a mean Spearman ρ < 0.5 versus human difficulty, with model self-assessment AUROC ≈ 0.55 (near random). Kolesnikova et al. (2026, `kolesnikova2026itemdifficulty`) systematically test judgment form × decision type × prompting strategy with a **full-factorial design** and establish the norm that "**analytic success rate must be a mandatory reported item in protocol results**," which we adopt in §4.3. On the gain route, Razavi and Powers (2026, `razavi2026itemdifficulty`) use LLM-extracted cognitive-linguistic features + tree ensembles (RF/GBM) to reach r = 0.87 — a **direct competing route** to this paper; in §6.3 we state explicitly: we do **not** adopt their tree-ensemble method and do **not** use their 0.87 as a superior benchmark for our system, citing it only as literature/attribution. Castleman, Macar, and Salleb-Aouissi (2024, `castleman2024hierarchical`) give a hierarchical-MAB intelligent tutor ("concept MAB + problem MAB + difficulty awareness") as a deployment paradigm; our combination estimator is one concrete implementation of its difficulty-awareness module under cold-start conditions. On "optimal difficulty," Wilson, Shenhav, Straccia, and Cohen (2019, `wilson2019eightyfive`, *Nature Communications*) give a computable anchor of optimal training error rate ≈ 15.87% (i.e., optimal correct rate ≈ 85%); in §3.2 we point out that this optimal error rate, like M4's auxiliary-signal budget, is a function of the task error structure rather than a universal constant, and on that basis we explicitly exclude several specific percentages from the recommendation report (R2's 31.73%, R10's 12.5%/50%/7.6%) from this paper's decision tables. This recognition that "optimal" varies with learner state is isomorphic to the **challenge-point framework** of Guadagnoli and Lee (2004, `guadagnoli2004challengepoint`): the optimal practice difficulty is jointly determined by task difficulty and learner proficiency, not a fixed constant.

### 1.4 Contributions of this paper

**M4-A/B/C/D — a reliability-structured combination chain (formalization; the degeneration claim is withdrawn per review §4.2, see §3.3).** M4-A estimates the signal covariance V on **rank correlation**, robust to the tails of the ECDF–logit transform and preserving the monotonic-reparametrization invariance of M1/O1. M4-B gives β = V⁻¹q (q_k = sgn_k√ρ_k) under the single-factor model z_k = √ρ_k·t + √(1−ρ_k)·ε_k, where V⁻¹ **automatically removes inter-column collinearity** and sign correction is absorbed into q. M4-C makes λ = Σ|β_aux|/Σ|β| derived from β — a **diagnostic quantity rather than an empirical power-law hyperparameter**. M4-D assigns each item a local reliability via the general Spearman–Brown form ρ(n) = nρ₁/(1+(n−1)ρ₁) under partial observability. **Degeneration proof** (§3.3): on the manifold V → I (columns uncorrelated) with q_k = sgn_k√ρ_k, M4-B degenerates to √ρ/(1−ρ) weighting (the ablation variant `m4_W`); `srw7`'s w_k ∝ ρ_k is the approximation on this manifold that drops the (1−ρ) error-correction term; introducing the V⁻¹ collinearity correction gives `m4_WV`, and removing the external λ gives `m4_full` — the four show a nested τ ordering in the experiments.

**Proposition P1 — under additively separable evidence, pairwise BT aggregation degenerates to linear combination (analytic proof + numerical companion).** If the pairwise evidence is additively separable in the logit domain, y_ij = Σ_k α_k(z_ki − z_kj) = u_i − u_j, then the BT maximum-likelihood solution is d = u (the normal-equation residual is identically 0): "pairwise-compare then BT-aggregate" and "directly weighted-linear-combine" give the same ranking. Numerical companion: all 384 BT solves converged (‖∇ℓ‖_∞ = 1e-11), and the minimum Spearman between the two additively-separable rules and u is 1.0; the two separability violations (probability-domain averaging, per-pair missingness) reach maxima of 1.0 and 0.996992 respectively. Mechanism diagnosis shows probability-domain averaging implicitly moves toward precision weighting (ρ = 0.96404 vs. 0.939289) — exactly what M4-B wants to capture explicitly — but P1 also proves that **violating additive separability does not automatically bring a gain**; any gain must be checked against an exogenous criterion (the DBE collapse in §5.2 is its counter-example).

**Negative result + M4-E residualization repair (exogenous criterion).** On the DBE-KT22 teacher labels (exogenous), the full M4 estimator collapses with k (k=200 τ_b = 0.0796, Δ = −0.0903, win-rate 0.00); the root cause is that the derived λ rises with k (0.8734) while the out-of-fold optimal λ approaches zero (0.015). M4-E residualizes the auxiliary columns against the reference column, keeping only the increment, and repairs the collapse (k=200 τ_b = 0.1718, Δ = +0.0019, paired t = 5.66, win-rate 0.90). On the Junyi platform labels (secondary), the full M4 estimator wins everywhere (k=200 Δ = +0.0708, win-rate 1.00), and M4-E remains positive (Δ = +0.0073, win-rate 1.00) — **gain/loss depends entirely on the criterion**, the core honest conclusion of this paper.

**Reliability ≠ validity (formal boundary).** §3.2 proves on the single-factor model that M4's β = V⁻¹q maximizes the correlation between the combination and the latent variable t (reliability), but when an auxiliary signal carries specific variance "unrelated to the validity target," β's heavier weighting lowers the correlation with the teacher's true difficulty (validity). This boundary theoretically delineates why an exogenous criterion is indispensable and has been landed as code comments and as a design principle of this paper's experimental protocol (code evidence: `app/services/difficulty_m4.py:38-44`).

**Engineering landing.** M4 has been landed as `learnflow-backend/app/services/difficulty_m4.py`, adding `incremental_columns` (M4-E, `:261`), `estimate_m4_difficulty` (with `residualize`/`reference_weight`/`drop` parameters, `:304`), etc.; §3.5 performs an efficiency optimization that factors out the rank matrix for the per-item β path (zero precision cost, `:166-182`, `:407-437`). The test suite `learnflow-backend/tests/test_difficulty_m4.py` now has 44 cases (33 baseline + `TestResidualization` 7 + `TestEfficiencyRefactor` 4); an offline rerun gives **44 PASS / 0 FAIL**, and the existing bit-exact gate is untouched (rerun command in §5 footnotes).

### 1.5 Structure of this paper

§2 reviews related work; §3 gives the formalization of M4 (analytic proof of Proposition P1, the reliability ≠ validity boundary, the M4-A/B/C/D degeneration claim (withdrawn, see §3.3), M4-E) and an implementation-efficiency optimization (§3.5); §4 describes the data, protocols, and statistical tests; §5 reports five groups of measurements; §6 discusses; §7 lists threats to validity and honest gaps; §8 concludes.

## 2 Related Work

### 2.1 Multi-signal difficulty fusion and reliability weighting

Combining multiple log signals into a difficulty score most naively uses equal-weight averaging (`fused6`) or equal-weight after sign correction (`signed7`); the more refined `srw7` introduces per-column split-half reliability weighting and sample-size shrinkage λ(k). These methods are correct at the **reliability level** (higher-reliability columns get higher weight) but none handles inter-column collinearity (two correlated signals double-counted) or reliability ≠ validity (high weight ≠ useful for true difficulty). M4-B's β = V⁻¹q is the direct application, in the difficulty-combination setting, of the standard psychometric result of optimal linear combination under a single-factor model; M4-C derives λ from β rather than fitting it empirically, in contrast to M1/O8's λ_cf(k) = 1/(1+(k/27.3)^0.895) (k = 10/25/50/100/200 → 0.7107/0.5197/0.3678/0.2383/0.144; evidence: `the fact-baseline and academic-style spec` Table A-1) — M4 argues this constant is not universal and should be data-derived.

### 2.2 Two camps on LLM difficulty annotation and protocol analyticity

The disagreement between the optimists (Ballon et al., 2025) and the pessimists (Li et al., 2026, `li2026canllms`) currently stays at the annotation layer. Kolesnikova et al. (2026, `kolesnikova2026itemdifficulty`), with a full-factorial design, show that the interaction of **judgment form (absolute vs. pairwise) × decision type (hard decision vs. token probability) × prompting strategy** is significant, and that analytic success rate must be a mandatory reported item of the results table — we adopt this norm into our protocol-reporting discipline in §4.3. We take no side between the two camps; instead we use the mechanism diagnosis of Proposition P1 (probability-domain averaging implicitly does precision weighting) as a bridge connecting them: what LLM judges actually do is probability-domain averaging (P1's R3 rule), and its source of benefit is exactly the precision weighting M4-B wants to capture explicitly.

### 2.3 The classical distinction between reliability and validity

Since Spearman–Brown's prophecy formula, psychometrics has distinguished **reliability** (consistency of measurement) from **validity** (whether the measurement measures the intended construct). §3.2 of this paper operationalizes this distinction into a falsifiable boundary: M4 optimizes the reliability of the combination, while the exogenous teacher labels measure validity; when an auxiliary signal's specific variance is not aligned with the validity target, reliability optimization damages validity. This boundary dictates that our experimental design must take an **exogenous** criterion as the gold standard rather than endogenous holdout error rate alone. Reliability-weighted combination itself derives from the **correction for attenuation** lineage of classical test theory — when several indicators load on the same latent variable, the optimal linear combination weight is proportional to each indicator's reliability (i.e., the degeneration of M4-B's β = V⁻¹q on the V → I manifold). Kolen and Brennan (2014, `kolen2014testequating`), in their systematic treatment of equating, scaling, and linking, further show that cross-instrument consistency measurement must distinguish "measuring the same construct" (equating) from "measuring the true value" (validity), resonating with the boundary of §3.2.

## 3 Formalization of M4

### 3.1 Proposition P1: under additively separable evidence, pairwise BT aggregation degenerates to linear combination

**Chapter summary (Chapter 3).** This chapter gives all the formalization foundations of M4. §3.1 proves and numerically verifies Proposition P1 — under additively separable log-odds evidence, pairwise Bradley–Terry aggregation and weighted linear combination give the same ranking, and the pairwise step itself produces no information gain; §3.2 formalizes the "reliability ≠ validity" boundary, delineating why our experiments must take an external criterion as the gold standard; §3.3 gives the formalization of the four M4-A/B/C/D improvements and the withdrawn degeneration claim that srw7 is a special case; §3.4 gives the formalization of M4-E (residualization), motivated by the negative result of §5.2.

**Proposition P1 (analytic).** Let each signal k's standardized value for item i be z_ki, and let u_i = Σ_k α_k z_ki. If the pairwise evidence from signal k is written p_ijk = σ(α_k(z_ki − z_kj)) and combined by **adding in the logit domain**,

$$y_{ij} = \sum_k \mathrm{logit}(p_{ijk}) = \sum_k \alpha_k(z_{ki} - z_{kj}) = u_i - u_j \quad\text{(additive separability)}$$

then the maximum-likelihood Bradley–Terry model P(i ≻ j) = σ(y_ij) satisfies d = u (the normal-equation residual is identically 0).

**Proof.** The BT log-likelihood ℓ(d) = Σ_{i<j}[W_ij log σ(d_i − d_j) + (1−W_ij) log σ(d_j − d_i)], where W_ij = σ(y_ij) = σ(u_i − u_j) (by additive separability). Taking the gradient at d = u: ∇_iℓ = Σ_{j≠i}[W_ij − σ(u_i − u_j)] = Σ_{j≠i}[σ(u_i − u_j) − σ(u_i − u_j)] = 0, so d = u is a stationary point. The negative Hessian −∇²ℓ is a complete-graph Laplacian with positive weights σ(1−σ) > 0, strictly positive definite on the constraint hyperplane Σd_i = 0, so this stationary point is the unique maximum; hence d = u. Spearman rank correlation is invariant to translation, so ρ(d,u) = 1. ∎

**Corollary.** The empirically observed "pairwise > absolute" (Kolesnikova et al., 2026) cannot originate from the "pairwise" form itself; it can only come from the two realistic sources of **separability violation**: (a) **probability-domain averaging** rather than logit-domain addition (what LLM judges actually do, P1's R3 rule); (b) **uneven per-pair availability** (missing / partial observation, P1's R4 rule).

**Numerical companion (rerun command: `python results/code/m4_proposition_p1.py`, output `results/code/m4_proposition_p1.json`).** On a synthetic problem where "m signals are noisy observations of the same latent variable" we run a four-way comparison (W_ij = σ(Y_ij), Y_ji = −Y_ij ⇒ N_ij ≡ 1); the solver is homotopy continuation + Newton + Armijo with a log-domain MM fallback, initialized at d ≡ 0 (the known answer is not used, avoiding implanting the identity into the starting point). Results:

**Table 3-1** Four-rule comparison of Proposition P1 (Spearman ρ relative to u).

| Rule | Meaning | Expected vs u | Measured min / max (24 trials × 4 scales = 96 groups) |
|---|---|---|---|
| R1 logit-sum | Additive separable (sum) | 1.0 | min = 1.0 |
| R2 logit-mean | Additive separable (mean) | 1.0 | min = 1.0 |
| R3 prob-mean | Probability-domain averaging (LLMsense) | <1 | max = 1.0 |
| R4 partial-obs | Per-pair missingness | <1 | max = 0.996992 |

> Rerun command: `python results/code/m4_proposition_p1.py` → `results/code/m4_proposition_p1.json`; **convergence certificate ‖∇ℓ‖_∞ maximum = 1e-11** (all 384 BT solves converged, no spurious ill-conditioning).

The two additively-separable rules reach ρ = 1.0 in **every** group (min = 1.0 means the worst case is still identity); the two violation sources still reach 1.0 only in the "worst case" (some trials are unaffected) but are systematically below 1. The R2/R1 contrast strips out the irrelevant factor "mean vs. sum," proving that **what matters is the domain of combination, not the aggregation operator**; R3/R4 quantify the magnitude of the two realistic violation sources.

**Mechanism diagnosis (answering the more important question: does violating additive separability bring a gain?).** Under the same data-generating process (each signal's noise standard deviation varies from 0.4 to 1.6, giving precision weighting resolution), we compare the correlation of three recoveries with "precision weighting" (optimal linear recovery, weight ∝ 1/σ_k²):

**Table 3-2** Correlation of three recoveries with precision weighting (Spearman ρ, mean over 96 groups).

| Quantity | Spearman ρ (mean over 96 groups) |
|---|---:|
| ρ(precision-weighting, true latent) | 0.898649 |
| ρ(u_α, precision-weighting) | 0.939289 |
| ρ(BT prob-mean, precision-weighting) | 0.96404 |

> Rerun command: same as above, reading `rho_prec_vs_latent_mean` / `rho_u_vs_prec_mean` / `rho_prob_mean_vs_prec_mean` from `m4_proposition_p1.json`.

Key finding: **probability-domain averaging is closer to precision weighting than the α linear combination** (0.96404 > 0.939289) — exactly the numerical evidence that LLM judges "implicitly do precision weighting," and the mechanism M4-B wants to capture explicitly.

**Caliber relation to M3 (added 2026-10-06).** The finding above that LLM judges "implicitly do precision weighting" is an **attribution about rule R3 (probability-domain averaging)**, and its numerical support (0.96404 / 0.939289) comes from a **four-way synthetic comparison** in `results/code/m4_proposition_p1.py` (m signals as noisy observations of one latent variable; stated as such in the numerical-companion paragraph of this section), **not a measurement on any real LLM output**. We therefore **do not claim** to have verified what real LLM judges actually do. The empirical scope on the real-LLM side is set by companion paper M3: all its measurements are confined to **local open-weight models (<=47B, 4-bit-class quantisation) spanning 4 families x 3 scale tiers = 11 cells, with no frontier API model**, and its annotation experiments use a single local model `qwen36:latest` (M3, §8 item 4b). This paper's contribution is therefore the **direction and magnitude of the mechanism when additive separability is violated** (analytic proof plus a synthetic companion), not a demonstration of real LLM-judge behaviour; readers should read this diagnosis together with M3's boundary. But the corollary of Proposition P1 also warns: **violating additive separability does not automatically bring a gain**; it only brings a "difference," and whether the difference is a gain must be checked against an exogenous criterion — the DBE collapse of §5.2 is its counter-example (M4 is higher on "combination reliability" but lower on exogenous validity).

### 3.2 Reliability ≠ Validity: the theoretical boundary of M4

**Proposition (boundary).** Under the single-factor model z_k = √ρ_k·t + √(1−ρ_k)·ε_k (t the latent difficulty, ε_k ⟂ t), M4-B's β = V⁻¹q maximizes the correlation between the combination c = βᵀz and t (i.e., the combination's **reliability**). Let the validity target be v = t + η, with η ⟂ t and η ⟂ {ε_k}; then corr(c,v) = corr(c,t) — the combination's validity **equals** its reliability relative to t, **but** when some auxiliary signal k carries specific variance "unrelated to v" (i.e., ε_k is not aligned with v but only with a partially redundant component of t), β_k, being large because ρ_k is large, weights that signal more heavily and instead lowers corr(c,v).

**Formal illustration.** M4-B's loading q_k = sgn_k√ρ_k assumes that **all** auxiliary signals load on the same latent variable t. If this assumption is broken — for example `self_report` (student self-assessment) is highly collinear with the success rate (redundant) but uncorrelated with the teacher's true difficulty (validity ≈ 0) — then the single-factor solution of β increases its weight (because ρ_k is large), and this weight buys "information the success rate already contains" rather than "increment." This is precisely the structural root of the DBE collapse in §5.2: **high reliability + low incremental validity = M4 weights noise more heavily**. Therefore, the "combination reliability improvement" of §3.1 and the "exogenous validity improvement" are two different things, and any M4 gain claim must be re-examined against an exogenous criterion. This boundary has been written into production-code comments (code evidence: `app/services/difficulty_m4.py:38-44`).

### 3.3 M4-A/B/C/D: four structural improvements, and the withdrawn srw7-is-a-special-case degeneration claim

**M4-A (estimate second-order structure on ranks).** The existing `srw7` estimates V on the unprocessed logit values, which are dominated by the tails of the ECDF–logit (ε = 1e-4 ⇒ extremes ±9.21). M4-A instead estimates V on **rank correlation** (code evidence: `_m4_beta_from_ranks` at `app/services/difficulty_m4.py:166-182`, public entry `m4_beta` delegates to it at `:185-207`, computing `ranks` then `_pearson`), which is both tail-robust and fully preserves the monotonic-reparametrization invariance of M1/O1.

**M4-B (single-factor model β = V⁻¹q).** q_k = sgn_k·√ρ_k, β = V⁻¹q. V⁻¹ automatically removes inter-column collinearity (code evidence: `_m4_beta_from_ranks`/`m4_beta` at `app/services/difficulty_m4.py:166-207`); sign correction is absorbed into q, and columns whose direction is opposite to success difficulty automatically get a negative β (code evidence: `app/services/difficulty_m4.py:370-371`). Compared with `srw7`'s w_k ∝ ρ_k, M4-B adds two corrections: the √(ρ/(1−ρ)) error-correction term and the V⁻¹ collinearity-correction term.

**M4-C (λ derived from β as a diagnostic).** λ = Σ_{k≠ref}|β_k|/Σ_k|β_k| (code evidence: `derived_lambda` at `app/services/difficulty_m4.py:234-247`). When the auxiliary signals are collectively unreliable, β_aux → 0 and λ → 0, automatically reverting to pure success rate; it contrasts with the λ_cf(k) of M1/O8 (`weng2026m1`) and is a **diagnostic quantity rather than a hyperparameter**.

**M4-D (per-item local reliability under partial observability).** It allows passing each column's per-item effective observation count `coverage` and single-observation reliability ρ₁, giving each item a local-reliability β via the general Spearman–Brown form ρ(n) = nρ₁/(1+(n−1)ρ₁) (code evidence: `coverage_reliability` at `app/services/difficulty_m4.py:140-144` and the per-item β path at `:407-437`). DBE-KT22's `difficulty_feedback` / `trust_feedback` columns are exactly this scenario.

**Degeneration claim — WITHDRAWN (review §4.2, 2026-09-29).** The claim that `srw7` is a special case of M4 **does not hold**: when V = I, M4's weight is sign × √ρ whereas `srw7`'s weight is ρ; the two are standardised differently; and `srw7` retains the λ_cf mixture while `m4_full` removes it. The original text is retained below verbatim for traceability only.

**Original text (withdrawn).** On the manifold V → I (columns uncorrelated, i.e., `m4_beta` degenerates to the |q|-normalized fallback, `app/services/difficulty_m4.py:183-184`) with q_k = sgn_k√ρ_k: ① M4-B degenerates to β_k ∝ √ρ_k, i.e., the ablation variant **`m4_W`** (weight √ρ/(1−ρ), no collinearity correction, code evidence: `results/code/run_m4.py:171-181`); ② `srw7`'s w_k ∝ ρ_k is the approximation of ① that drops the (1−ρ) error-correction term (so `srw7` slightly under-weights high-reliability columns); ③ introducing the V⁻¹ collinearity correction gives **`m4_WV`** (code evidence: `results/code/run_m4.py:183-188`); ④ removing the external λ gives **`m4_full`** (code evidence: `results/code/run_m4.py:189-190`). The four show a nested τ ordering in the experiments (see §5.2–§5.5), consistent with this degeneration relation.

### 3.4 M4-E: residualization repair

**Motivation (directly from the negative result of §5.2).** M4-C's derived λ rises with k (0.7449 → 0.8734), meaning M4 monotonically increases the weight on auxiliary columns; but the auxiliary columns are highly collinear with the success rate, so the increased part buys **redundancy** rather than increment, manifesting on the exogenous teacher labels as a gain that collapses with k.

**Formalization.** For each auxiliary signal j, remove its rank correlation ρ with the reference column (success rate) in the standardized-value space, then divide by √(1−ρ²) to unit variance:

$$e_j = (z_j - \rho\, z_{\mathrm{ref}})/\sqrt{1-\rho^2},\quad \text{fully collinear columns (}1-\rho^2\le10^{-6}\text{) are auto-dropped}$$

Then combine the incremental columns compE with reliability weighting, and mix with the original ecdf–logit reference column under λ (code evidence: `incremental_columns` at `app/services/difficulty_m4.py:261-300` and the residualization branch at `:392-405`; experimental side `results/code/run_m4.py:196-224` with `m4_E_cf`/`m4_E_rel`). Residualization makes the combination term **rank-correlation-orthogonal** to the reference column; the meaning of λ shifts from "globally scaling the reference column" to "how much the incremental information is worth."

### 3.5 Implementation efficiency: factoring out the rank matrix (and reproducibility)

**Problem (a real bottleneck in pure Python).** Solving M4-B's β = V⁻¹q needs the rank-correlation matrix V, and each entry of V is a Pearson on the **average ranks** of two columns. Under partial observability (M4-D, non-empty coverage), `estimate_m4_difficulty` takes the **per-item β** path: originally `m4_beta` re-sorted all m columns internally on every call (code evidence: old implementation at `app/services/difficulty_m4.py:185-207`). But the ranks of the standardized columns `zstd` are **identical for all items** (item-invariant, determined only by column values, independent of item index), so n items were sorted n times — under pure Python (no numpy), sorting dominates the per-item path cost, forming an O(n) redundant factor.

**Fix (rank factoring-out).** Compute the rank matrix `rk = [ranks(c) for c in zstd]` **once outside** the per-item loop, passing it through as an argument to `_m4_beta_from_ranks(zstd, rk, q)` (`difficulty_m4.py:166-182`; the experimental side `run_m4.py`'s `beta_from_q` is isomorphic, from `:112`, computed once as `R` by `all_variants` at `:171` and passed through). No sorting remains inside the per-item loop. This fix **changes no numerical value**: `rk` is computed by the same `ranks` function, and V and the Gaussian-elimination `_solve` are completely unchanged, so the result is **bit-identical** to inline recomputation — locked down by the four assertions of `learnflow-backend/tests/test_difficulty_m4.py::TestEfficiencyRefactor` (equivalence, `ranks_` pass-through, per-item path reproducible, consistent with inline recomputation).

**Measured speedup (rerun command: `python results/code/benchmark_m4_efficiency.py`).** On synthetic data with m = 7 columns and partial observability (per-item effective observation count 1–9), comparing "recompute ranks inside the loop" (before) with "compute ranks once outside the loop" (after):

**Table 3-3** Measured speedup from rank-matrix factoring-out (m = 7 columns, partial observability).

| n | Before (ms) | After (ms) | Speedup |
|---|---:|---:|---:|
| 100 | 54.50 | 42.51 | 1.28× |
| 200 | 216.65 | 161.45 | 1.34× |
| 400 | 905.70 | 652.98 | 1.39× |
| 800 | 3772.13 | 2584.87 | 1.46× |

The speedup rises monotonically with n: the redundant O(n) sorting factor occupies a larger share at larger n, confirming the bottleneck localization; at DBE's real scale (n ≈ 212) it is about 1.34×. This gain comes from **eliminating duplicated work** rather than approximation, so it has zero precision cost — `m4_results.json` is **bit-unchanged** after a full rerun (Appendix A reproducibility checklist item 2).

**Why we did not also do an LU-decomposition speedup (honest note).** V is identical across items on the per-item path, so in principle one could do a **single** LU decomposition of V and n forward/back substitutions (O(m³)+O(n·m²)), reducing the O(n·m³) Gaussian elimination to constant. We **did not adopt** this, for two reasons: ① this project's floating-point red line requires "every number in the document to be machine-recomputable," and the per-item summation uses Neumaier-compensated `sum()`; ② LU decomposition would change the floating-point summation order inside Gaussian elimination, which, though mathematically equivalent, could diverge at the last ulp. Since this optimization already eliminates redundancy without touching `_solve`, and the paper's numbers are fidelity-preserved by a full rerun, we chose "zero precision cost" over "more aggressive speedup"; LU decomposition is left as a future optimization for the pure cold-start production path (which does not undergo exogenous recomputation).

## 4 Data, Protocols, and Experimental Design

### 4.1 Data sources and licensing

DBE-KT22 (`abdelrahman2022dbekt22`, ADA Dataverse DOI 10.26193/6DZWOH) provides 212 items with parseable difficulty labels and partially observable `difficulty_feedback` / `trust_feedback` columns, forming the source of M4-D and the P1a exogenous criterion. Junyi Academy (official Kaggle package, CC BY-NC-SA 4.0, cite Chang, Hsu, and Chen, EDM 2015) provides 1,234 exercises with platform difficulty labels, forming the source of this paper's P1b secondary criterion and the P2 holdoutcontrol. Both datasets are **knowledge-tracing (KT)** benchmarks; the classic BKT (Corbett & Anderson, 1994, `corbett1994knowledge`) already characterizes skill acquisition with per-item difficulty as a latent parameter, and our difficulty combination is precisely the estimability prerequisite of BKT's difficulty parameter under **cold-start (no-label)** conditions; for a more systematic context see Abdelrahman et al. (2023, `abdelrahman2023knowledge`)'s KT survey. Both datasets must be cited under the licenses above; Junyi **prohibits any commercial use**.

### 4.2 Signals and preprocessing

All signals are unified by M1's ECDF–logit transform (`app/services/difficulty_fusion.py::ecdf_logit`) into "larger = harder": the reference column `success_rate` is negated (code evidence: `_z_columns` at `app/services/difficulty_m4.py:217-225`). This transform is invariant to any monotonic reparametrization (M1/O1 conclusion), so M4-A's rank-correlation estimation does not break that invariance. The signal set `M4_DEFAULT_SIGNALS` (`app/services/difficulty_m4.py:61-69`) contains 7 columns, but different systems may use different columns available (DBE lacks `upgrade_rate`/`downgrade`/`repeat`), and M4 allows passing only a subset.

### 4.3 Three protocols and Kendall τ_b

**P1a (exogenous criterion = DBE-KT22 teacher difficulty labels).** This is the **only** exogenous benchmark of this paper (samesense as recommendation report R7). The item-level three-tier labels cause many ties, so following R7's norm we use **Kendall τ_b** (robust to ties) rather than Spearman; n_items = 212, reps = 20, k ∈ {10, 25, 50, 100, 200} (k is the reservoir slot count).

**P1b (secondary criterion = Junyi platform difficulty labels).** Same τ_bsense, n_items = 1,234, reps = 8. Its status is **secondary** — the platform labels areco-sourced with the logs (not independently exogenous), used only as acontrol of "if we switch to anotherco-sourced label, does the conclusion flip."

**P2 (holdout error rate, non-exogenous, only acontrol).** Following M1's holdout protocol (fit block A and criterion block B are mutually exclusive), the criterion is the true future-sample performance (error rate). This criterion is **non-exogenous** (co-sourced with training data); this paper uses it **only as a consistencycontrol** and does not claim an M4-E gain from it (see §5.6).

**Protocol-reporting discipline (adopting R5 / Kolesnikova et al., 2026).** Every protocol reports analytic success rate / number of parseable items as part of the reliability boundary, never removed from the results (see each protocol's footnote).

### 4.4 Statistical tests

Within-group paired comparison: for each k, over the reps resamples we compute the difference sequence "estimator τ_b − srw7_cf baseline τ_b" (the baseline is `base = per_rep["srw7_cf"]` in `run_m4.py`), reporting the mean Δ, standard deviation sd, paired t = Δ/(sd/√reps), and the win-rate win_rate (proportion of resamples in which the estimator exceeds the baseline). The paired effect size is reported as Cohen's d_z = t/√n_pairs (n_pairs = reps) for cross-k effect-strength comparison. Significance on the exogenous criterion follows P1a's paired t and win_rate; τ_b is used because the three-tier labels cause many ties (following R7's norm).
**Baseline correction (review §4.2, 2026-09-29).** Δ is therefore **relative to `srw7_cf`** (this corrects an earlier draft that wrote "success-rate-only baseline"); no binomial test exists in the code or in the JSON, so the phrase two-sided binomial test has been removed and `win_rate` is reported only as a descriptive proportion. It must also be added that the text reported only the k = 200 result of P2 (holdout): `m4_E_cf` is in fact **below** the success-rate-only baseline at every k = 10…100 (protocol `P2_junyi_holdout_errorrate`: 0.5535 vs. 0.6663 at k = 10; 0.7688 vs. 0.8072 at k = 25; 0.8676 vs. 0.8791 at k = 50; 0.9244 vs. 0.9270 at k = 100), an interval of results that was previously unreported.


## 5 Results

### 5.1 Numerical companion of Proposition P1 (summary)

See the tables and footnotes of §3.1: the two additively-separable rules have minimum ρ = 1.0 vs u (all 96 groups identity), convergence certificate ‖∇ℓ‖_∞ = 1e-11; the two violation sources have maximum ρ of 1.0 (probability-domain averaging) and 0.996992 (per-pair missingness) respectively; mechanism diagnosis shows probability-domain averaging implicitly moves toward precision weighting (0.96404 > 0.939289). This companion confirms Proposition P1 and gives a numerical window into "what LLM judges actually do."

### 5.2 DBE exogenous teacher labels: M4 collapses with k (negative result)

**Chapter summary (Chapter 5).** This chapter reports five groups of measurements. §5.1 summarizes the P1 companion; §5.2 gives the negative result that the full M4 estimator collapses with k on the exogenous DBE criterion (core); §5.3 diagnoses the collapse root cause via the divergence of derived λ and out-of-fold λ; §5.4 reports M4-E repairing the collapse; §5.5 reports M4 winning everywhere on Junyi platform labels, highlighting criterion-dependence; §5.6 reports the P2 holdoutcontrol (non-exogenous, only acontrol).

Table 5-1 gives the P1a exogenous results (n_items = 212, reps = 20, Kendall τ_b; rerun command: `python results/code/run_m4.py` → `results/code/m4_results.json`, protocol `P1_dbe_teacher_labels`).

**Table 5-1 DBE-KT22 exogenous teacher labels (Kendall τ_b, with Δ relative to the `srw7_cf` baseline and fusion win-rate in parentheses)**

| k | Success-rate-only (baseline) | srw7_cf (existing best) | m4_full (M4-A/B/C) | m4_E_cf (M4-E) |
|---|---:|---:|---:|---:|
| 10 | 0.1704 | 0.1721 | 0.1596 (−0.0125, 0.30) | 0.1425 (−0.0296, 0.15) |
| 25 | 0.1691 | 0.1772 | 0.1680 (−0.0092, 0.40) | 0.1784 (+0.0012, 0.45) |
| 50 | 0.1668 | 0.1719 | 0.1519 (−0.0200, 0.20) | 0.1739 (+0.0020, 0.65) |
| 100 | 0.1686 | 0.1739 | 0.1182 (−0.0556, 0.00) | 0.1765 (+0.0027, 0.85) |
| 200 | 0.1675 | 0.1699 | 0.0796 (−0.0903, 0.00) | 0.1718 (+0.0019, 0.90) |

> Rerun command: `python results/code/run_m4.py` → `results/code/m4_results.json` (protocol `P1_dbe_teacher_labels`). k=200 paired t: m4_full Δ = −0.0903, sd = 0.0175, t = −23.08, win 0.00; m4_E_cf Δ = +0.0019, sd = 0.0015, t = +5.66, win 0.90. Paired effect size d_z = t/√reps (reps = 20): m4_full −5.16 (very large negative effect), m4_E_cf +1.27 (medium-to-large positive effect — within-sample descriptive only; see the post-hoc disclosure in §5.2). Note: RNG is `random.Random(seed)` (not numpy PCG64), so absolute values are not bit-comparable with M1's `o11`; within-group paired comparisons are valid.

**Core negative result**: the structurally "more correct" full M4 estimator (m4_full) **collapses monotonically with k** on the DBE exogenous criterion; at k=200 τ_b = 0.0796, 0.0903 below `srw7_cf` (t = −23.08, win-rate 0.00), and **below** the existing `srw7_cf` (0.1699). This is the strongest honest conclusion of this paper: M4-A/B/C's improvement in "combination reliability" is actually harmful to exogenous validity.

### 5.3 Diagnosis: derived λ rises while out-of-fold optimal λ goes to zero

Table 5-2 gives the divergence on DBE between M4-C's derived λ (from β) and the out-of-fold calibrated (CV) optimal scalar λ — exactly the root of the collapse.

**Table 5-2 Two senses of λ on DBE (rerun source: same as Table 5-1, `_lambda_derived_mean` / `_cv_lambda_m4_mean`)**

| k | M4-C derived λ (from β) | Out-of-fold calibrated optimal λ (CV) |
|---|---:|---:|
| 10 | 0.7449 | 0.4125 |
| 25 | 0.7858 | 0.5115 |
| 50 | 0.8182 | 0.3350 |
| 100 | 0.8492 | 0.1490 |
| 200 | 0.8734 | 0.0150 |

> Rerun command: same as above, reading `_lambda_derived_mean` and `_cv_lambda_m4_mean` for each k under protocol `P1_dbe_teacher_labels` of `m4_results.json`.

M4's derived λ **rises monotonically with k** (more and more budget for auxiliary signals), but the optimal λ from out-of-fold calibration on the exogenous teacher labels **monotonically approaches zero** (only 0.015 at k=200) — i.e., the teacher labels say "do not use the auxiliary signals." This divergence directly confirms the §3.2 boundary: the auxiliary signals are highly collinear with the success rate, and M4's β mistakes "redundancy" for "increment" and weights it more, so the exogenous criterion is harmed. The collapse is not numerical noise but a structural manifestation of reliability ≠ validity.

### 5.4 M4-E repairs the collapse

As the last column of Table 5-1, M4-E (`m4_E_cf`, residualization + λ_cf mixing) **repairs** the collapse: k=200 τ_b = 0.1718, 0.0019 above `srw7_cf` (t = +5.66, win-rate 0.90); and at k = 50/100/200 it is better than or ties `srw7_cf` and m4_full. Residualization constrains the combination to "the increment beyond the success rate," making λ clean again — consistent with the criterion signal in Table 5-2 that "the out-of-fold optimal λ should approach zero": when incremental information is minimal, M4-E automatically reverts to the reference column through λ.
**Post-hoc disclosure for M4-E (review §4.3, 2026-09-29).** Three limitations must be stated alongside the repair above. (i) M4-E was appended **after** the collapse of the full estimator had been observed, and it is evaluated on the **same 212 items, the same labels and the same seed (20260927)**; no items were reserved for confirmation and no second dataset was used, so the repair is exploratory rather than confirmatory. (ii) The sibling variant produced on the same day, `m4_E_rel`, **loses to `srw7_cf` at every k** on the exogenous criterion (protocol `P1_dbe_teacher_labels`, Δ vs. `srw7_cf` = −0.0078 / −0.0009 / −0.0023 / −0.0033 / −0.0016 at k = 10 / 25 / 50 / 100 / 200); these results were previously not reported and are given here. (iii) The reported gain Δ = +0.0019 at k = 200 is only about 1% of the baseline τ_b (≈ 0.17), and at k = 10 the same estimator is **below** that baseline (Δ = −0.0296); t = 5.66 is the dispersion across 20 re-drawn response slots on the **same items and the same labels**, and says nothing about generalisation to new items. Writing this as a medium-to-large effect (d_z = 1.27) is therefore misleading; d_z is retained below only as a descriptive within-sample quantity.

**Caliber relation to M1 (added 2026-10-05).** This section uses `srw7_cf` (**with** `λ_cf` mixing) as the baseline, yet M1 §7.5 has already measured that **λ shrinkage yields no gain on DBE**: M1's λ* spans only 0.05-0.17, and the hold-out ρ is level with (or slightly below) the λ = 0 case (k = 25: 0.9001 vs 0.9006); the improvement was **verified on Junyi only and does not replicate across systems**. The two statements do not contradict each other, but the calibers differ, so readers must judge this for themselves:
- **M1's comparison** is "`srw7` with λ_cf" against "the same estimator at λ = 0", judged by M1's own hold-out ρ.
- **This section's comparison** is `srw7_cf` against "success-rate-only", judged by the DBE teacher Kendall τ_b. These are **not the same estimand under the same criterion**, so the fact that `srw7_cf` slightly exceeds success-rate-only (e.g. 0.1699 vs 0.1675 at k = 200) **does not refute M1's conclusion**.
⚠️ **The +0.0019 gain reported here must therefore be read with care**: M4-E's gain over `srw7_cf` is obtained on top of a component that M1 has shown to be gainless on this dataset. This paper's contribution is that "residualization makes the combination no longer depend on getting that component's weight right" — **not** that λ_cf is shown to be effective on DBE. M1's conclusion holds for M4 and is not overturned here.


### 5.5 Junyi platform labels: M4 wins everywhere (criterion-dependence)

Table 5-3 gives P1b (n_items = 1,234, reps = 8, Kendall τ_b; rerun source `m4_results.json` protocol `P1_junyi_platform_labels`).

**Table 5-3 Junyi platform difficulty labels (Kendall τ_b, with Δ relative to the `srw7_cf` baseline and win-rate in parentheses)**

| k | Success-rate-only | m4_full (M4-A/B/C) | m4_E_cf (M4-E) |
|---|---:|---:|---:|
| 10 | 0.1467 | 0.1882 (+0.0247, 0.875) | 0.1588 (−0.0048, 0.375) |
| 25 | 0.1717 | 0.2175 (+0.0313, 1.00) | 0.1953 (+0.0091, 0.875) |
| 50 | 0.1825 | 0.2431 (+0.0483, 1.00) | 0.2109 (+0.0162, 1.00) |
| 100 | 0.1975 | 0.2562 (+0.0530, 1.00) | 0.2132 (+0.0100, 1.00) |
| 200 | 0.1966 | 0.2709 (+0.0708, 1.00) | 0.2075 (+0.0073, 1.00) |

> Rerun command: same as above, protocol `P1_junyi_platform_labels`.

**Criterion-dependence conclusion**: on the Junyi platform labels (co-sourced with the logs, secondary status), the original full M4 estimator **wins everywhere** (k ≥ 25 win-rate 1.00, k=200 Δ = +0.0708), and M4-E remains positive (k=200 Δ = +0.0073, win-rate 1.00). This is **completely opposite** to the collapse of §5.2 — the same algorithm, a different criterion, and the conclusion flips. **On this basis we assert: any statement that "M4 is better than srw7" must annotate the criterion and sample size it depends on; talking about "gain" divorced from the criterion is invalid.**

### 5.6 P2 holdoutcontrol (non-exogenous, only acontrol)

P2 (Junyi holdout error rate, non-exogenous) is used only as a consistencycontrol, not to claim a gain. Rerun source `m4_results.json` protocol `P2_junyi_holdout_errorrate` (k=200, accuracysense): success-rate-only 0.9495, m4_full 0.7289, m4_E_cf 0.9498. m4_full is likewise far below baseline on holdout accuracy (0.7289), **corroborating** rather than independently verifying the §5.2 collapse; m4_E_cf returns to baseline level (0.9498). Because this protocol's criterion is non-exogenous, we do not claim an M4-E gain from it, using it only as supporting evidence that "M4-full's failure also exists on the predictionsense."

## 6 Discussion

### 6.1 Methodological implications of criterion-dependence

This paper collapses on DBE (exogenous) and wins everywhere on Junyi (co-sourced) — this contrast itself is a methodological reminder, isomorphic to M3's negative result on the holdout criterion that "consistency gain ≠ predictive-power gain": a combination's "good" must be defined by its **external validity**, not its consistency with some label. The specific percentages in the recommendation report (R2's 31.73%, R10's 12.5%/50%/7.6%), if moved into a decision table, would treat a value under one specific dataset/protocol as a universal constant, whereas §3.2 of this paper and M4-C's derived-λ experiment jointly show: **the auxiliary-signal budget, like the optimal error rate, is a function of the task error structure, not a universal constant**. This conclusion is isomorphic to Guadagnoli and Lee's (2004, `guadagnoli2004challengepoint`) challenge-point framework: the optimal practice difficulty is jointly determined by task difficulty and learner proficiency, not a fixed constant; Wilson et al.'s (2019, `wilson2019eightyfive`) 85% rule is the concrete anchor of §3.2's "optimal error rate is not universal" conclusion in the training-error-rate dimension.

### 6.2 Costs and benefits of residualization

M4-E's benefit is clear on the exogenous criterion (repairs the collapse), but the cost is: when an auxiliary signal **does** carry real increment (e.g., m4_full wins everywhere on Junyi), residualization mistakenly deletes some effective increment, making m4_E_cf's Δ on Junyi smaller than m4_full's (k=200: +0.0073 vs. +0.0708). This reflects an unsolved practical problem: **what λ should be, depends on whether the auxiliary signals on that dataset truly carry exogenous increment** — M4-E hands this question back to "out-of-fold calibrated λ" (the CVsense of Table 5-2) rather than using a universal constant.

### 6.3 Boundaries with R11's tree ensemble and R10's ratios

Razavi and Powers's (2026, `razavi2026itemdifficulty`) feature + tree-ensemble route (r = 0.87) is the **direct competitor** of this paper. We state explicitly: we do not adopt their tree-ensemble method (this paper insists on interpretable linear β = V⁻¹q and residualization, convenient for exogenous re-verification), and we do not use their 0.87 as a superior benchmark for our system (data/features/protocol all differ; porting that conclusion would be out of bounds). R10's ratios such as 12.5%/50%/7.6% are values from specific experiments; we do not introduce them into decision tables, for the same reason as §6.1. R4 (Yeung et al., 2019, `yeung2019deepirt`, 1PL) is **not used as a main criterion**: M1 already confirmed that 1PL network-output difficulty and success rate have ρ ≈ 0.96, nearly perfectlyco-sourced with the success rate, so it cannot serve as an exogenous benchmark; thus our criteria take only DBE teacher labels (exogenous) and Junyi platform labels (co-sourced secondary).

## 7 Threats to Validity and Honest Gaps

**T1 — Single exogenous criterion.** The only exogenous benchmark of this paper is DBE-KT22's 212 teacher labels; the Junyi platform labels areco-sourced with the logs and serve only as a secondarycontrol; P2 holdout is non-exogenous. Whether M4-E's repair conclusion is robust under a third independent exogenous label remains to be tested. This is the clearest unresolved threat of this paper.

**T2 — Unresolved boundary of reliability ≠ validity.** §3.2 proves that when an auxiliary signal carries specific variance "unrelated to the validity target," M4 weights noise more heavily, but gives no decision rule for "when an auxiliary signal truly carries exogenous increment"; M4-E depends on out-of-fold λ calibration, which itself requires exogenous labels, so this rule cannot be obtained under pure cold-start (no labels at all).

**T3 — Recomputation-environment difference.** `m4_results.json`'s RNG is `random.Random(seed)`, **different in origin** from M1's `o11_fusion_optimization.json` numpy PCG64, so absolute values are not bit-comparable (recorded in the json `note`); all significance conclusions of this paper are within-group pairedsense and do not depend on cross-script bit-recomputation, but readers citing cross-script values should note this difference.

**T4 — Un-executed items.** This paper did not do: ① a separate validation of M4-D's per-item local reliability on an **exogenous** criterion (M4-D is only implemented; in the P1a collapse/repair experiment the coverage path was not separately isolated and reported); ② re-verification of M4-E on a third independent exogenous label (see T1); ③ a direct same-protocol comparison with R11's tree ensemble (per the §6.3 boundary, this paper does not do it).

## 8 Conclusion

This paper proposes M4 — the reliability-structured estimator for the "cold-start multi-signal combination" stage in LearnFlow's four-chain difficulty system — formalizes its four structural improvements (M4-A/B/C/D) and formerly claimed that `srw7` is a special case (withdrawn per review §4.2, see §3.3); gives the analytic proof and numerical companion of Proposition P1 (under additive separability, pairwise BT = linear combination, ρ = 1.0, convergence certificate ‖∇ℓ‖_∞ = 1e-11), and mechanism-diagnoses that LLM judges implicitly do precision weighting (0.96404 > 0.939289; **synthetic-data support, not a real-LLM measurement; the real-LLM scope is bounded by M3's local-open-weight restriction, see §3**). The core contribution of this paper is to **honestly report and repair a negative result**: on the only exogenous criterion (DBE teacher labels), the structurally "more correct" full M4 estimator collapses with sample size (k=200 τ_b = 0.0796, Δ = −0.0903, win-rate 0.00), root-caused in the auxiliary signals being collinear with the success rate and the derived λ mistaking redundancy for increment; M4-E residualization repairs this collapse (k=200 τ_b = 0.1718, Δ = +0.0019, t = 5.66, win-rate 0.90). This paper simultaneously reports that this conclusion completely flips on theco-sourced Junyi platform labels (M4 wins everywhere, k=200 Δ = +0.0708), thereby establishing the methodological discipline that "gain claims must annotate the criterion and sample size," and the formal boundary that "reliability ≠ validity." M4 has been landed as production code (`app/services/difficulty_m4.py`) with 44 tests (offline 44 PASS / 0 FAIL; 33 baseline + 7 residualization + 4 efficiency-preservation), and the existing bit-exact gate is untouched. The necessary prerequisite for the future is to introduce a third independent exogenous label and an exogenous validation of M4-D's per-item reliability (§7 T1/T2).

## References

- Abdelrahman, G., Abdelfattah, S., Wang, Q., & Lin, Y. (2022). DBE-KT22: A Knowledge Tracing Benchmark Dataset with Detailed Exercise Annotation. *arXiv:2208.12651*. [`abdelrahman2022dbekt22`]
- Castleman, B., Macar, U., & Salleb-Aouissi, A. (2024). Hierarchical multi-armed bandits for the concurrent intelligent tutoring of concepts and problems of varying difficulty levels. *Reinforcement Learning Conference (RLC)*. [`castleman2024hierarchical`]
- Kolesnikova, D., Fedyanin, K., Hofman, A. D., Brinkhuis, M. J. S., & Bolsinova, M. (2026). Estimating Item Difficulty with Large Language Models as Experts. *arXiv:2605.18562*. [`kolesnikova2026itemdifficulty`]
- Li, M., Chen, H., Xiao, Y., Chen, J., Jiao, H., & Zhou, T. (2026). Can LLMs Estimate Student Struggles? Findings of ACL 2026. [`li2026canllms`]
- Razavi, P., & Powers, S. J. (2026). Estimating item difficulty using large language models and tree-based machine learning algorithms. *IJAIED, 36*(3), Article 100015. [`razavi2026itemdifficulty`]
- Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications, 10*, 4646. [`wilson2019eightyfive`]
- Yeung, C.-K., & Yeung, D.-Y. (2019). Deep-IRT: Make deep learning based knowledge tracing explainable using item response theory. *EDM 2019*. [`yeung2019deepirt`]
- Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modelling and User-Adapted Interaction, 4*(4), 253–278. [`corbett1994knowledge`]
- Guadagnoli, M. A., & Lee, T. D. (2004). Challenge point: A framework for conceptualizing the effects of various practice conditions in motor learning. *Journal of Motor Behavior, 36*(2), 212–224. [`guadagnoli2004challengepoint`]
- Abdelrahman, G., Wang, Q., & Nunes, B. (2023). Knowledge Tracing: A Survey. *ACM Computing Surveys, 55*(11), 224. [`abdelrahman2023knowledge`]
- Kolen, M. J., & Brennan, R. L. (2014). *Test Equating, Scaling, and Linking: Methods and Practices* (3rd ed.). Springer. [`kolen2014testequating`]
- Weng, Z., & Jung, M. (2026). Commensurability of Difficulty Scales: An Instability Proposition and Its Test on assist09 (M1). *LearnFlow companion manuscript* (under review). [`weng2026m1`]

(The Bradley–Terry model (Bradley & Terry, 1952, *Biometrika*) is cited as a standard statistical model; following M3's convention we do not assign it a separate bib key.)

## Appendix A Reproducibility Checklist

1. **Proposition P1 companion**: `python results/code/m4_proposition_p1.py` → `results/code/m4_proposition_p1.json`. Key keys: `rho_logit_sum_vs_u_min` (=1.0), `rho_logit_mean_vs_u_min` (=1.0), `rho_prob_mean_vs_u_max` (=1.0), `rho_partial_obs_vs_u_max` (=0.996992), `grad_inf_max` (=1e-11), `rho_prec_vs_latent_mean` (=0.898649), `rho_prob_mean_vs_prec_mean` (=0.96404), `rho_u_vs_prec_mean` (=0.939289).
2. **M4 main experiment**: `python results/code/run_m4.py` → `results/code/m4_results.json`. Protocols: `P1_dbe_teacher_labels` (exogenous), `P1_junyi_platform_labels` (secondary), `P2_junyi_holdout_errorrate` (non-exogenouscontrol). The `estimators` field contains all variant definitions (`ESTIMATOR_DOC`, `results/code/run_m4.py:402-415`).
3. **Production code**: `app/services/difficulty_m4.py` (`_m4_beta_from_ranks`:166, `m4_beta`:185, `incremental_columns`:261, `estimate_m4_difficulty`:304, M4-E branch:392-405, per-item β path:407-437, `derived_lambda`:234, `coverage_reliability`:140).
4. **Tests**: `learnflow-backend/tests/test_difficulty_m4.py` (33 baseline + `TestResidualization` 7 + `TestEfficiencyRefactor` 4 = 44 cases); offline rerun `run_tests_offline.py` → **44 PASS / 0 FAIL / 0 ERROR / 0 SKIP**.
5. **Efficiency benchmark**: `results/code/benchmark_m4_efficiency.py` (recomputes the §3.5 speedup table; zero precision cost, numerically bit-identical to inline recomputation).
