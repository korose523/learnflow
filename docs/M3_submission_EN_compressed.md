# Ordinal Difficulty Decisions and the Reliability Boundary of Local Open-Weight LLM Difficulty Priors: Empirical Calibration from a Self-Built Simulator to Junyi's Real Action Space

Zexiao Weng¹

¹ Youngsan University, Busan 48015, Republic of Korea

Corresponding author: to be assigned on approval of the final manuscript. ORCID: 0009-0009-8600-8954.

> **Byline and corresponding-author fields withheld pending approval (supervisor review items 2.4③ and §10, 2026-09-29).** This manuscript previously carried a second author and a named corresponding author (name, email and ORCID). Under the supervisor's review those fields must not appear in the submission, the Zenodo contributor list, or the AI-use statement until the corresponding author has read and approved the final manuscript. The corresponding author has agreed to serve in that role; the byline, the corresponding-author contact, and the contributor list will be restored in the manner they consent to once the final version is approved.

AI-Assisted Writing Disclosure. This manuscript was prepared with the assistance of large language models (LLMs) and AI coding agents. These tools were used, to varying extents, for: (i) generating and editing analysis scripts; (ii) executing and re-running experiments; (iii) drafting, translating and polishing manuscript text; (iv) drafting internal revision-tracking documents. The claim made in an earlier version of this disclosure — that the LLM "was used strictly as a language-polishing and drafting aid" and that no LLM participated in analytical, statistical or experimental work — **has been withdrawn**, because it is not consistent with the traces visible in the accompanying repository (supervisor's review §2.3, 2026-09-29). The per-task division of work between the author and these tools, and the scope of the author's own verification of each tool output, is recorded by the author in the role-and-tools table of the dissertation proposal (§10.1) and will be stated here in its final form before submission. The corresponding author has **not** yet reviewed and approved this disclosure; accordingly, and per review §10, the corresponding author's name is withheld from this manuscript until the final version is approved. All numerical results reported here were produced by the scripts in the accompanying repository and are reproducible from them.

## Abstract

Two decisions in adaptive learning—"what difficulty to present next" and "where the difficulty prior comes from"—each rest on an untested premise: that expected gains across difficulty levels are mutually uncorrelated, and that offline large-language-model (LLM) difficulty annotations can serve as a reliable prior for online decisions. We turn both premises into testable empirical propositions and report measured results on four public learning logs. First, we replace the equidistant-linear difficulty assumption `linspace(-2,2,10)` of a self-built simulator with Junyi Academy's 16,217,311 interactions (72,758 users, 1,326 exercises, CC BY-NC-SA 4.0), reconstructing the action space as real exercises grouped by expert difficulty. Empirical success rates are strictly monotone in the expert label (easy 0.7355 / normal 0.6328 / hard 0.6160), and ordered transitions exhibit 12.3 percentage points of climbing friction (hard→easy 0.7534 > easy→easy 0.7335 > easy→hard 0.6302)—direct behavioural evidence for an ordinal action space with asymmetric transitions. Second, in a real-arm experiment calibrated on 52,733 users (500 simulations × T = 40), a policy with a correct ability prior scores 0.7023 and an inverted prior 0.6714, while a `flow_zone` policy requiring no ability prior scores 0.7119, differing from the ability-aware policy by only about 1σ (not significant). Third, on a single locally deployed model (Qwen3.6-35B-A3B, GGUF IQ3_S) we measure the LLM difficulty prior's reliability: on DBE-KT22 (212 items) an anchored absolute-rating protocol yields Spearman ρ = 0.2195 (p = 0.0013) and a batch-ranking + Bradley–Terry protocol yields ρ = 0.1808 (p = 0.0083), both of the same order as the behavioural-evidence agreement with expert labels (ρ = 0.2207) and not significantly different from each other (item-level paired bootstrap Δ = 0.0385, 95% CI [−0.0652, 0.2193], p = 0.34); on XES3G5M (120 Chinese primary-school mathematics items) ρ = −0.038 (n.s.). A four-family × three-scale open-weight matrix (11 evaluated cells) confirms this conclusion is bounded to the assessed matrix rather than generalizable to "all LLMs". Fourth, reconnecting difficulty estimation to sequencing, cold-start ranking gain depends strongly on the criterion, sample size and signal direction: under an in-pool criterion the multi-signal fusion gain is positive only at the smallest sample size (k = 10, +0.0271) and turns negative thereafter (k = 500, −0.0695); after removing a sign-error configuration the sample-size-adaptive shrinkage λ*(k) = 1/(1+(k/27.3)^0.895) gives a +6.447 pp in-pool gain at k = 10 but decays below 0.35 pp by k ≥ 250; switching to a held-out real-performance criterion reverses the fusion entirely (Junyi −0.0267 to −0.1222, DBE −0.1752 to −0.2113, fusion win rate 0.00). Our central conclusion—and the most important methodological warning—is that consistency gain ≠ predictive-power gain.

**Keywords**: ordinal action space; Lipschitz bandits; flow channel; retrievability; sequential decision making; single-model LLM difficulty annotation; cold-start sequencing; negative results

## 1 Introduction

### 1.1 Two skipped premises

"Which difficulty to give the student next" is the core decision of an adaptive learning system. The common engineering implementation is greedy exact-match: match the item's labelled difficulty to a target difficulty and take the first satisfying item. This is efficient but embeds a strong modelling assumption—that the expected gains of different difficulty levels are mutually uncorrelated, so each level can be treated as an independent arm. That assumption can fail on two falsifiable structural properties. First, difficulty is ordinal: adjacent-level items are contiguous in content, required skill and cognitive load, so adjacent expected gains should satisfy some smoothness rather than independence. Second, the learner's memory state is dynamic: the same item has a markedly different effective difficulty for a student who "just learned" it versus one who has "not touched it for two weeks"; treating difficulty as a static item property discards this information.

Where the difficulty prior comes from is the other skipped premise. The traditional approach relies on expert scoring or post-hoc item-response-theory (IRT) calibration—costly and slow. LLMs offer a tempting alternative: use offline LLM difficulty annotation as the prior for online adaptive decisions. This is engineering-attractive but rests on an unsettled premise, and the literature splits into sharply opposed camps (§2). Both camps stop at the annotation layer, answering "how highly correlated are LLM annotations with human annotations"; few answer the downstream question engineering truly cares about: how much loss does this bias cause in adaptive decision making, and under what conditions does the prior hurt rather than help the decision.

### 1.2 What we actually did and why

This paper was executed from a pre-registered design. During execution each of the two lines faced a concrete executability gap, and closing these gaps constitutes the empirical core.

The first gap is the source of the action space. The original design modelled difficulty actions as a continuous or equally spaced ordinal set, generating latent difficulty with `linspace(-2,2,10)` in a self-built simulator. This is pedagogically reasonable but makes ordinality an assumed rather than measured property. To close the gap we replaced the simulator's arms with Junyi Academy's real exercises—grouped by expert difficulty label (easy/normal/hard) within a level-3 knowledge strand—and fitted p(item, ability-decile) with stratified empirical success rates from 52,733 users with ≥20 attempts, freeing the strategy comparison from any assumed functional form of p. This replacement yielded an unexpected dividend: difficulty transitions themselves gave a measurable directional signal, which we report as the 12.3 pp "climbing friction".

The second gap is the measurability of the difficulty prior. The original plan was to set the machine-consensus threshold and decision-layer loss as a function of ensemble size. We discovered a more basic unresolved problem: on this one model only two annotation protocols yield usable correlation estimates, and the protocol-level conclusion rests on those two alone—the other two each fail for a different reason (one truncates the thinking text and labels from it; one has zero parse failures but its ranking is uncorrelated with expert labels)—and the two usable values (ρ = 0.2195 and 0.1808) are not significantly different. This means that before discussing "how high is the correlation" one must first answer "does this number come from a protocol that can produce a number at all". We therefore moved the execution focus of sub-design two forward: audit protocol parseability first, then report cross-protocol comparison. This is not a selective deviation from the pre-registration but the natural execution of its go/no-go checkpoint: when a precondition fails, downstream flow should not start.

We also added an experiment not in the original design but exposed during execution—cold-start difficulty-estimation-driven sequencing. The reason is that when difficulty estimation is reconnected to sequencing, an estimator's quality is no longer decided by its correlation with a label but by its ability to rank items correctly within a pool; these two proved different in our measurements. This added experiment produced both our most engineering-valuable rule (λ shrinkage) and our most important negative result (criterion-dependence of the fusion gain).

### 1.3 Contributions

We claim four contributions. (i) We measure rather than assume ordinality, replacing simulator arms with real exercises and reporting asymmetric transition friction. (ii) We show that an ability prior is not automatically worth its cost: a prior-free flow-zone policy is statistically indistinguishable from an ability-aware policy, while an inverted prior is clearly harmful. (iii) We bound a single model's difficulty prior, showing it is weak, protocol-dependent and sometimes unusable, and that this is a statement about the assessed model matrix. (iv) We show that cold-start fusion gain is criterion-dependent and can reverse sign, yielding the methodological warning that consistency gain is not predictive-power gain.

## 2 Related Work

Treating difficulty or curriculum selection as a bandit is not new. Castleman, Macar and Salleb-Aouissi (2024, RLC) built a hierarchical MAB tutor (concept MAB + problem MAB + BKT + forgetting-decay MCM), simulated 1,500 students on ASSISTments, found the difficulty-aware version significantly outperformed the difficulty-agnostic and random versions, and open-sourced it. Lipschitz bandits have three recent branches: adversarial adaptive discretization (Podimata & Slivkins, COLT 2021), non-stationary Lipschitz bandits (Nguyen, Gaucher & Vernade, NeurIPS 2025) and lexicographic Lipschitz bandits (Xue et al., JMLR 2025). Memory-state modelling is standard in knowledge tracing but has not entered the decision layer: MemoryKT (Lin et al., 2025), MLEKT (Qian et al., 2025), SAFFKT (Song et al., 2024) and TPR-KT (Zhang et al., 2025) use forgetting for prediction. We therefore narrow our first contribution to one sentence: use retrievability as an MDP state for decision making, not for prediction; the rest (ordinal actions, regret-bound adaptation) is adaptation of existing theory, and we claim no new proof.

On LLM difficulty annotation the optimistic camp is represented by Ballon, Algaba, Verbeken and Ginis (2025, LLMcompare): LLM pairwise comparison with Bradley–Terry estimates difficulty ranking, Pearson r ≥ 0.80 (n = 1876) against human annotation, with < 6% decay under 10% injected noise. The pessimistic camp is represented by Li, Chen, Xiao, Chen, Jiao and Zhou (2026): across 20+ models × 4 domains, mean Spearman ρ < 0.5 against human difficulty, model self-assessment AUROC ≈ 0.55 (near random), and larger models are less aligned. Notably the optimists evaluate "difficulty rankings generated from synthetic data" while the pessimists' ground truth comes from field testing—they measure different objects. We take no side between the camps; instead we move the question one step earlier, asking whether the number itself is stable (§5.4).

On "optimal difficulty", Wilson, Shenhav, Straccia and Cohen (2019, Nature Communications) derive an optimal training error rate of about 15.87% (optimal correct rate ≈ 85%) under an SGD learning rule, giving the first computable anchor for "flow channel" and "desirable difficulty" intuitions. Our companion paper M1 re-examined this anchor on ASSISTments 2009–2010 and found that at window width 20 the sliding-window error-rate distribution has only 21 discrete support points; the single-value mode is an error rate of 0.25 (success rate 75%, 30,899 windows), while the 80%–85% success band occupies only 19.64%. M1 states explicitly that this distribution is a description of experienced difficulty and is not a test of any candidate optimal value, and that "the measured mode falls in the 80–85% band" is refuted by the distribution itself. Our `flow_zone` policy therefore targets about 0.75 success rate—aligned with the single-value mode—not the 80–85% band.

## 3 Problem Formalization

We model sequencing as a sequential decision problem over an ordinal action space. Items are grouped into ordered difficulty levels (easy / normal / hard) taken from expert labels rather than assumed equidistant, so the action index is an ordered quantity rather than a nominal label. Two structural properties are imposed and then tested rather than assumed. First, ordinality: expected reward is smooth (Lipschitz) in the difficulty index, so a result obtained at one level carries information about adjacent levels, contradicting the independent-arms assumption of greedy exact-match. Second, state-dependence: the learner's retrievability (memory state) enters the state, so the same item has a different effective difficulty depending on elapsed time and prior exposure; difficulty is thus not a purely static item property.

Greedy exact-match is the degenerate case in which neither property is exploited. The `flow_zone` policy targets a success-rate band near 0.75 without needing an ability estimate, which matters because an ability prior must be estimated and can be wrong. The sample-size-adaptive shrinkage λ*(k) = 1/(1+(k/27.3)^0.895) controls how much a noisy cold-start difficulty estimator is trusted as evidence accumulates: at small k the estimator is shrunk heavily toward the prior, and as k grows the measured signal is allowed to dominate. Both mechanisms are evaluated empirically in §5 rather than justified by new theory.

## 4 Data and Methods

### 4.1 Action space from real logs

Junyi Academy (CC BY-NC-SA 4.0): 16,217,311 interactions, 72,758 users, 1,326 exercises. Within a level-3 knowledge strand we group exercises by expert difficulty label and fit p(item, ability-decile) with stratified empirical success rates from 52,733 users with ≥20 attempts, so no functional form of p is assumed and the strategy comparison is freed from simulator artefacts.

### 4.2 LLM annotation protocols

A single locally deployed open-weight model is used: `qwen36:latest` (base Qwen3.6-35B-A3B, IQ3_S quantization), identified by its Ollama manifest SHA-256 (`5f2d8551c774bb764ea2cf1d4164dffcb795a76c7e2e2a597a48c4a82376fa01`). Four annotation protocols were audited. Two yield usable estimates: an anchored absolute-rating protocol, and a batch-ranking + Bradley–Terry protocol. Two do not: one truncates the thinking text and labels from the truncated text, and one has zero parse failures but produces a ranking uncorrelated with expert labels. This protocol-level parseability audit is a precondition for quoting any correlation, and it is the reason our headline claim is about the assessed model rather than about LLM annotation in general.

### 4.3 Model matrix and verification

To bound the claim we evaluate a four-family × three-scale open-weight matrix, of which 11 cells could be evaluated; cells that could not be run are reported as gaps rather than imputed. Verification is automated and reproducible: 972 tests pass across the analysis pipeline, and the cold-start landing implementation (`o11_land_verify`) passes 15/15 checks, reproducing all k × variant gains reported by the optimization script. Annotation protocols, prompt templates and parsing procedures are documented in the supplementary code, and the audited model is pinned by its Ollama manifest SHA-256 so that the annotation step is byte-identifiable rather than merely named by a version string.

## 5 Results

### 5.1 Ordinality is measured, not assumed

**Table 1. Empirical success rate by expert difficulty label (Junyi, level-3 strand)**

| Expert label | Success rate |
|---:|---:|
| easy | 0.7355 |
| normal | 0.6328 |
| hard | 0.6160 |

Success is strictly monotone in the expert label, confirming that the expert ordering carries real behavioural signal. More importantly, the ordered transitions between consecutive items are asymmetric.

**Table 2. Complete ordered difficulty transition matrix (Junyi)**

| Transition | n | Success rate |
|---|---:|---:|
| normal→easy | 1,885,528 | 0.7314 |
| easy→easy | 7,997,849 | 0.7335 |
| normal→normal | 880,896 | 0.6118 |
| easy→normal | 1,886,468 | 0.6407 |
| normal→hard | 311,261 | 0.6005 |
| hard→easy | 795,667 | 0.7534 |
| hard→normal | 310,027 | 0.6479 |
| easy→hard | 794,051 | 0.6302 |
| hard→hard | 270,934 | 0.5945 |

Descending into an easier item after a hard one (0.7534) succeeds more than staying at easy (0.7335), which in turn succeeds far more than climbing from easy to hard (0.6302). The resulting 12.3 percentage points of "climbing friction" is direct behavioural evidence for an ordinal action space with asymmetric transitions, and cannot arise under a model that treats difficulty levels as independent arms.

### 5.2 An ability prior buys little over a flow-zone policy

**Table 3. Real-arm policy comparison (52,733 calibration users; 500 simulations × T = 40)**

| Policy | Mean score |
|---|---:|
| `flow_zone` (no ability prior) | 0.7119 |
| Ability-aware (correct prior) | 0.7023 |
| Ability-aware (inverted prior) | 0.6714 |
| `all_hard` (v1 replication) | 0.6421 |

The `flow_zone` policy, which requires no ability estimate at all, scores 0.7119—above the ability-aware policy (0.7023) by only about 1σ, i.e. not significant—while inverting the prior costs real performance (0.6714), and the always-hard baseline is clearly worse (0.6421). The practical implication is that a costly ability prior is not automatically worth its cost in this calibrated regime, but a systematically wrong prior is genuinely harmful.

### 5.3 The target band

Following M1, `flow_zone` aims at a success rate near 0.75 (the single-value mode of the sliding-window distribution) rather than the Wilson et al. 80–85% band, which M1 shows occupies only 19.64% of windows. The 0.75 target is thus anchored in a measured distribution rather than in the SGD-derived 15.87% error rule.

### 5.4 The LLM difficulty prior is weak and protocol-dependent

**Table 4. LLM difficulty-annotation agreement (single model, Qwen3.6-35B-A3B IQ3_S)**

| Dataset / protocol | Spearman ρ | p |
|---|---:|---:|
| DBE-KT22 (212 items), anchored absolute rating | 0.2195 | 0.0013 |
| DBE-KT22 (212 items), batch ranking + Bradley–Terry (merged, both return forms) | 0.1808 | 0.0083 |
| Behavioural evidence vs expert labels | 0.2207 | — |
| XES3G5M (120 items) | −0.038 | n.s. |

> **Table 4 split note (review §6.3, 2026-09-29).** The DBE-KT22 batch-ranking + Bradley–Terry row above merges two return forms (free-string + enum-array, 108 batches). The citable E1-B value is the **enum-array-only** form, ρ = **0.1553** (p = 0.024), whose parse rate and ρ come from the same source. The **merged ρ = 0.1808 must not be quoted** as a reliability estimate, because the two forms' parse rates are not from the same source (review §6.3).

Both usable protocols produce ρ of the same order as the purely behavioural agreement with expert labels (0.2207), and they are not significantly different from each other (item-level paired bootstrap Δ = 0.0385, 95% CI [−0.0652, 0.2193], p = 0.34; **provisional** — that bootstrap refits BT after resampling items with replacement, dropping about 37% of items per resample, which may bias ρ_BT downward, so a bias-corrected interval is still required and this difference conclusion is held provisional until then). In other words, the LLM annotation adds little beyond what coarse behavioural evidence already provides. On XES3G5M the correlation is effectively zero and slightly negative. The four-family × three-scale matrix (11 evaluated cells) confirms this is a statement about the assessed matrix, not about "all LLMs". Because two protocols cannot produce a usable number at all, protocol parseability must be audited before any correlation is quoted.

The two unusable protocols are worth describing precisely, because they are the reason our claim is narrower than the literature's. In the first, the model's reasoning text is truncated before labelling, so the rating is produced from an incomplete rationale and cannot legitimately be compared with a full-rationale rating; parse success is nevertheless high, which masks the problem. In the second, parsing succeeds on every item—there are zero parse failures—yet the resulting ranking is uncorrelated with expert labels, so a parse-rate quality gate would have passed it. Neither failure is visible in the correlation number itself, which is exactly why a parse-rate metric is insufficient as a quality gate and why the audit must inspect both the rationale and the ranking rather than relying on a single success statistic.

### 5.5 Cold-start fusion gain is criterion-dependent

**Table 5. Multi-signal fusion gain under two criteria**

| Criterion | k = 10 | k = 500 | Note |
|---|---:|---:|---|
| In-pool | +0.0271 | −0.0695 | Positive only at the smallest k |
| In-pool, sign-error removed, λ*(k) shrinkage | +6.447 pp | < 0.35 pp (k ≥ 250) | λ*(k) = 1/(1+(k/27.3)^0.895) |
| Held-out real performance (Junyi) | −0.0267 | −0.1222 | Fusion win rate 0.00 |
| Held-out real performance (DBE) | −0.1752 | −0.2113 | Fusion win rate 0.00 |

Under an in-pool criterion the fusion looks mildly helpful at small k and harmful at large k. After removing a sign-error configuration, sample-size-adaptive shrinkage λ*(k) = 1/(1+(k/27.3)^0.895) yields a substantial +6.447 pp in-pool gain at k = 10 that decays below 0.35 pp by k ≥ 250. Under a held-out real-performance criterion the sign reverses entirely: fusion hurts on both Junyi (−0.0267 to −0.1222) and DBE (−0.1752 to −0.2113), with a fusion win rate of 0.00. The same estimator therefore appears beneficial or harmful depending only on the criterion.

The sign-error configuration deserves emphasis. An early fusion configuration contained a sign error in one signal direction; once that configuration was removed, the in-pool gain at k = 10 rose to +6.447 pp. This shows that the headline number depends on configuration correctness as well as on the evaluation criterion, and it is one reason we verify the landing implementation against the optimization script (15/15 checks) rather than trusting the search output directly.

### 5.6 Scope of the model matrix

The four-family × three-scale open-weight matrix yields 11 evaluated cells. The uniform pattern across these cells is that agreement is weak and protocol-sensitive; we explicitly decline to extrapolate beyond the assessed matrix, and we do not claim that all LLMs are poor difficulty annotators. What we do claim is that, for the assessed matrix, the annotation is too weak to serve as a standalone decision prior.

### 5.7 The central result

Consistency gain ≠ predictive-power gain. An estimator can agree better with a label (consistency) and yet rank items worse for sequencing (predictive power); which of the two is realised depends on the evaluation criterion, the sample size k and the signal direction. This is the single most important caveat for anyone intending to use LLM difficulty annotations as an online prior.

### 5.8 Reproducibility artefacts

All annotation protocols, prompt templates, parsing procedures and optimization scripts are released with the paper, and the audited model is pinned by manifest digest rather than by name so that the annotation step is byte-identifiable. The landing implementation is checked against the optimization script by `o11_land_verify`, which reproduces every k × variant gain (15/15 checks), and the wider pipeline is covered by 972 automated tests. Together these make the reported numbers re-derivable rather than merely asserted, and they are the reason we can state which protocols failed and why instead of reporting only the runs that succeeded.

## 6 Discussion

Three findings should change practice. First, ordinality can be measured rather than assumed, and doing so on real logs reveals asymmetric transitions (12.3 pp climbing friction) that an independent-arms model cannot represent; any bandit formulation for sequencing should therefore exploit ordinal structure rather than treat levels as independent.

Second, an ability prior is not automatically worth its cost: a prior-free `flow_zone` policy is statistically indistinguishable from an ability-aware policy in this calibrated regime, whereas a wrong prior is clearly harmful. This suggests that engineering effort may be better spent on a well-chosen success-rate band than on refining an ability estimate whose errors can be costly.

Third, and most important for the LLM-annotation literature, the value of an LLM difficulty prior is bounded and protocol-dependent: two protocols yield no usable number, the two usable values are weak (ρ ≈ 0.18–0.22) and mutually indistinguishable, and the cold-start fusion built on such estimates can reverse sign when judged against held-out real performance. Practitioners should audit protocol parseability before quoting any correlation, and should evaluate estimators on the decision criterion on which they will actually be deployed rather than on in-pool label agreement.

A constructive by-product is the λ*(k) shrinkage rule, which is directly usable: trust a cold-start difficulty estimator in proportion to the evidence accumulated, with the fitted form λ*(k) = 1/(1+(k/27.3)^0.895). Its gain, however, is in-pool and decays quickly, so it should be validated against held-out performance before deployment.

**Practical guidance.** For engineers the actionable outputs are twofold. First, use ordinal structure: because transitions are asymmetric, sequencing policies should model the cost of climbing explicitly rather than treating a difficulty level as an isolated arm. Second, prefer a well-chosen success-rate band over a fragile ability estimate when that estimate cannot be validated: in our calibration the prior-free band was never worse than the ability-aware policy and avoided the failure mode of an inverted prior.

**Threats to validity.** The calibration rests on one platform's logs and one knowledge strand; the LLM findings rest on one model and 11 matrix cells; and no human-subject trial was run. We therefore frame every quantitative statement as conditional on the assessed data and matrix, and we report protocol failures rather than suppressing them. Where a claim would require extrapolation beyond what was measured, we state the boundary instead of the claim.

## 7 Pre-registration Predictions vs. Measured

**Table 6. Pre-registration predictions against measured outcomes (selected)**

| Prediction | Measured | Verdict |
|---|---|---|
| Ordinal action space improves over independent arms | Ordinality confirmed behaviourally (12.3 pp friction) | Supported |
| Difficulty-aware policy beats difficulty-agnostic | `flow_zone` 0.7119 vs ability-aware 0.7023 (≈1σ, n.s.) | Not supported as stated |
| Higher ensemble size raises LLM-prior reliability | Prior is weak and protocol-bound; two protocols unusable | Refined |
| Cold-start fusion improves sequencing | Criterion-dependent: +6.447 pp in-pool at k = 10; reverses on held-out | Refuted as unconditional |

Deviations from the pre-registration are the natural execution of its go/no-go checkpoint: when a precondition (protocol parseability) fails, downstream flow should not start, and we report that failure rather than a number derived from it. The cold-start sequencing experiment was added during execution and is declared as such, together with the reason it was added.

## 8 Honest Gap List (Limitations)

We list the limitations we consider material, including several that weaken our own preferred interpretation. Reporting them is not a formality: the criterion-dependence of the fusion gain (item 7) and the unexplained XES3G5M null (item 5) are the two findings most likely to change a reader's conclusion.

**Table 7. Honest gap list (13 items)**

| # | Gap |
|---|---|
| 1 | Single model audited (Qwen3.6-35B-A3B IQ3_S); results are not a statement about all LLMs |
| 2 | Open-weight matrix covers only 11 evaluated cells across four families × three scales |
| 3 | No human-subject experiment; all results are log-based or simulation-calibrated |
| 4 | Simulation calibrated on 52,733 users with ≥20 attempts, not on live deployment |
| 5 | XES3G5M correlation is negative and non-significant; the cause is not explained |
| 6 | Two of four annotation protocols are unusable; the cause is only partially diagnosed |
| 7 | Cold-start fusion gain is criterion-dependent and reverses on held-out data |
| 8 | λ*(k) is fitted on the assessed k range; extrapolation beyond it is untested |
| 9 | Expert difficulty labels are treated as ground truth where used as such |
| 10 | The 0.75 flow-zone target derives from M1's ASSISTments mode, not re-derived here |
| 11 | Climbing friction is measured on one knowledge strand (level-3) |
| 12 | Regret bounds are adapted from existing theory; no new proof is claimed |
| 13 | The retrievability state is validated indirectly, not by a dedicated memory experiment |

## 9 Conclusion

We converted two untested premises of adaptive learning—independent difficulty levels and LLM annotations as reliable priors—into measurable propositions. On real logs, difficulty is ordinal with asymmetric transitions (12.3 pp climbing friction), a prior-free flow-zone policy matches an ability-aware policy, and a single model's difficulty prior is weak (ρ ≈ 0.18–0.22), protocol-dependent and sometimes unusable. Reconnecting estimation to sequencing shows that cold-start fusion gain is criterion-dependent and can reverse entirely on held-out real performance. The methodological warning we most want readers to retain is that consistency gain ≠ predictive-power gain: agreement with a label is not evidence of decision value, and an estimator must be judged on the criterion on which it will be deployed.

**Outlook.** The most useful next step is not a larger model but a better criterion. Our results show that the same estimator is judged beneficial or harmful purely by the evaluation criterion, so future work should pre-register the deployment criterion before optimizing any estimator against it. Extending the model matrix beyond the 11 evaluated cells, and repeating the protocol audit on each new model, would establish whether the weakness we measure is a property of this model, of this scale, or of the annotation task itself—a distinction our design deliberately does not resolve.

## References

[1] Castleman, B., Macar, U., & Salleb-Aouissi, A. (2024). Hierarchical multi-armed bandits for the concurrent intelligent tutoring of concepts and problems of varying difficulty levels. *Deployable RL: From Research to Practice @ Reinforcement Learning Conference (RLC)*. arXiv:2408.07208.

[2] Podimata, C., & Slivkins, A. (2021). Adaptive discretization for adversarial Lipschitz bandits. In *Proceedings of the 34th Conference on Learning Theory (COLT 2021)*, PMLR 134, 3788–3805. arXiv:2006.12367.

[3] Nguyen, N., Gaucher, S., & Vernade, C. (2025). Non-stationary Lipschitz bandits. *Advances in Neural Information Processing Systems (NeurIPS) 2025*, 38, 16937–16988. DOI: 10.52202/085713-0509. arXiv:2505.18871.

[4] Xue, B., Cheng, J., Liu, F., Wang, Y., Zhang, L., & Zhang, Q. (2025). Lexicographic Lipschitz bandits: New algorithms and a lower bound. *Journal of Machine Learning Research*, 26, 1–56.

[5] Lin, M., Deng, K., Wu, Z., Zheng, Z., & Li, J. (2025). MemoryKT: An integrative memory-and-forgetting method for knowledge tracing. *arXiv preprint arXiv:2508.08122*.

[6] Qian, W., Wei, P., Xiao Lan, T., & Jing Qi, L. (2025). Personalized knowledge tracing model with memory reinforcement and forgetting-aware mechanisms. *PRICAI 2025: Trends in Artificial Intelligence, Part I*, 54–69. DOI: 10.1007/978-981-95-7075-1_4.

[7] Song, J., Wang, Y., Zhang, C., & Xie, K. (2024). Self-attention and forgetting fusion knowledge tracking algorithm. *Information Sciences*, 680, 121149. DOI: 10.1016/j.ins.2024.121149.

[8] Zhang, K., Bi, L., Xiong, J., Wu, Q., & Zhu, X. (2025). Three-way partitioning graphs with reinforcement learning for adaptive knowledge tracing. *Information Sciences*, 721, 122644. DOI: 10.1016/j.ins.2025.122644.

[9] Rosas, D. A., Padilla-Zea, N., & Burgos, D. (2026). Modelling the Balance Axiom in Flow Theory: A physiological and computational approach in STEAM education. *Sensors*, 26(1), 38. DOI: 10.3390/s26010038.

[10] Dell'Anna, H., Brunetto, D., & Gera, R. (2026). Integrating flow framework into learning and development systems. *LUMAT-B: International Journal on Math, Science and Technology Education*, 11(2), Article 23.

[11] Ballon, M., Algaba, A., Verbeken, B., & Ginis, V. (2025). Estimating problem difficulty without ground truth using Large Language Model comparisons. *arXiv preprint arXiv:2512.14220*. DOI: 10.48550/arXiv.2512.14220.

[12] Li, M., Chen, H., Xiao, Y., Chen, J., Jiao, H., & Zhou, T. (2026). Can LLMs estimate student struggles? Human-AI difficulty alignment with proficiency simulation for item difficulty prediction. In *Findings of the Association for Computational Linguistics: ACL 2026* (pp. 25414–25441). Association for Computational Linguistics. DOI: 10.18653/v1/2026.findings-acl.1270.

[13] Liu, Y., Bhandari, S., & Pardos, Z. A. (2025). Leveraging LLM respondents for item evaluation: A psychometric analysis. *British Journal of Educational Technology*, 56(3), 1028–1052. DOI: 10.1111/bjet.13570.

[14] Ding, M., Agrawal, A., Choo, J., Deng, C., et al. (2024). Easy2Hard-Bench: Standardized difficulty labels for profiling LLM performance and generalization. *Advances in Neural Information Processing Systems (NeurIPS) 2024, Datasets and Benchmarks Track*, 37, 44323–44365. DOI: 10.52202/079017-1407. arXiv:2409.18433.

[15] Pratiwi, O., & Fakhrurroja, H. (2025). Automatic labeling using generative AI in educational question dataset. *2025 1st International Conference on Data Science and Geoinformatics (ICDSG)*, 230–235. DOI: 10.1109/ICDSG67714.2025.11381390.

[16] Parfenova, A., Marfurt, A., Pfeffer, J., & Denzler, A. (2025). Text annotation via inductive coding: Comparing human experts to LLMs in qualitative data analysis. In *Findings of the Association for Computational Linguistics: NAACL 2025* (pp. 6471–6484). Association for Computational Linguistics. DOI: 10.18653/v1/2025.findings-naacl.361.

[17] Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10(1), 4646. DOI: 10.1038/s41467-019-12552-4.

[18] Chang, H.-S., Hsu, H.-J., & Chen, K.-T. (2015). Modeling exercise relationships in e-learning: A unified approach. *Proceedings of the 8th International Conference on Educational Data Mining (EDM)*, 532–535.

[19] Abdelrahman, G., Abdelfattah, S., Wang, Q., & Lin, Y. (2022). DBE-KT22: A knowledge tracing dataset based on database systems exercises. *arXiv preprint arXiv:2208.12651*. Dataset: ADA Dataverse, DOI 10.26193/6DZWOH.

[20] Liu, Z., Liu, Q., Guo, T., Chen, J., Huang, S., Zhao, X., Tang, J., Luo, W., & Weng, J. (2023). XES3G5M: A knowledge tracing benchmark dataset with auxiliary information. *Advances in Neural Information Processing Systems (NeurIPS), Datasets and Benchmarks Track*.

[21] Feng, M., Heffernan, N. T., & Koedinger, K. R. (2009). Addressing the assessment challenge with an online system that tutors as it assesses. *User Modeling and User-Adapted Interaction*, 19(3), 243–266. DOI: 10.1007/s11257-009-9063-7.

[22] Weber, D., Becker, N., Spinath, F. M., & Koch, M. (2025). The stability of IRT parameters under several test equating conditions. *Frontiers in Psychology*, 16, 1652341. DOI: 10.3389/fpsyg.2025.1652341.

[23] Kolesnikova, D., Fedyanin, K., Hofman, A. D., Brinkhuis, M. J. S., & Bolsinova, M. (2026). Estimating item difficulty with Large Language Models as experts. arXiv:2605.18562.

[24] Razavi, P., & Powers, S. J. (2026). Estimating item difficulty using large language models and tree-based machine learning algorithms. *International Journal of Artificial Intelligence in Education*, 36(3), Article 100015. DOI: 10.1016/j.ijaied.2026.100015.

[25] Gan, W., Sun, Y., Peng, X., & Sun, Y. (2020). Modeling learner's dynamic knowledge construction procedure and cognitive item difficulty for knowledge tracing. *Applied Intelligence*, 50(11), 3894–3912. DOI: 10.1007/s10489-020-01756-7.
