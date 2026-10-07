# Offline Evaluation of Difficulty Priors for Adaptive Sequencing: Public Learning Logs, Simulation and Local Open-Weight Models

Zexiao Weng¹

¹ Youngsan University, Busan 48015, Republic of Korea

Sole and corresponding author: Zexiao Weng (wengzexiao). ORCID: 0009-0009-8600-8954.

## Abstract

Adaptive sequencing depends on an ordered difficulty action space and an estimate of item difficulty. We examine these components separately using public learning logs, simulation and stored ratings from local open-weight models. Junyi's observed success rates are ordered by teacher difficulty label (easy 0.7355, normal 0.6328, hard 0.6160); ordered transitions show a 12.3 percentage-point difference between hard-to-easy and easy-to-hard transitions. These observational patterns motivate an ordinal action space but do not identify a causal effect of difficulty transitions. In a real-arm-calibrated simulator, the paired deterministic replay scores 0.7128 for the ability-threshold policy, 0.6871 for its inverted mapping and 0.7286 for a target-band policy; always-easy scores 0.7674. These are simulator outcomes, not measured human learning gains. On DBE-KT22, a detailed local-model protocol audit gives Spearman 0.2195 for anchored absolute ratings and 0.1553 for Bradley–Terry scores from valid enumerated-array batches. Across the eight models in the original stored-rating file, ordinal AUC ranges from 0.4846 to 0.6169 when teacher-label ties are excluded and model-rating ties receive half credit. A separate 11-cell matrix is regenerated from three stored record files using a common 2,000-resample item bootstrap. Results are limited to the evaluated local models, quantisations, protocols and item banks. Neither a descriptive practice-error mode nor simulator performance establishes an optimal human practice target. Independent learning outcomes and broader model evaluation are required before using these priors as a validated sequencing component.

**Keywords**: ordinal difficulty; adaptive sequencing; local open-weight models; difficulty priors; simulation; protocol evaluation

## 1 Introduction

### 1.1 Two skipped premises

Adaptive sequencing requires a choice of item difficulty and a model of how that choice relates to learner state. Teacher difficulty categories provide an ordered label space, but an ordering of observed success rates does not establish smooth expected learning gains or statistical dependence between bandit arms. Difficulty labels, response probabilities and learning gains are distinct quantities. We therefore use public logs to describe the observed action space and a calibrated simulator to examine policy behavior under explicit assumptions. These are offline evaluations rather than tests of improved human learning.

Where the difficulty prior comes from is the other skipped premise. The traditional approach relies on expert scoring or post-hoc item-response-theory (IRT) calibration—costly and slow. LLMs offer a tempting alternative: use offline LLM difficulty annotation as the prior for online adaptive decisions. This is engineering-attractive but rests on an unsettled premise, and the literature splits into sharply opposed camps (§2). Both camps stop at the annotation layer, answering "how highly correlated are LLM annotations with human annotations"; few answer the downstream question engineering truly cares about: how much loss does this bias cause in adaptive decision making, and under what conditions does the prior hurt rather than help the decision.

### 1.2 What we actually did and why

An archived design document guided the original analyses. We distinguish its planned comparisons from analyses added during execution; an archived document alone is not evidence of public, prospective registration of every analysis. The current paper reports offline results and retrospective protocol audits.

The first gap is the source of the action space. The original design modelled difficulty actions as a continuous or equally spaced ordinal set, generating latent difficulty with `linspace(-2,2,10)` in a self-built simulator. This is pedagogically reasonable but makes ordinality an assumed rather than measured property. To close the gap we replaced the simulator's arms with Junyi Academy's real exercises—grouped by expert difficulty label (easy/normal/hard) within a level-3 knowledge strand—and fitted p(item, ability-decile) with stratified empirical success rates from 52,733 users with ≥20 attempts, reducing dependence on an assumed parametric form of p while retaining the simulator’s other structural assumptions. This replacement yielded an unexpected dividend: observed transitions differed directionally by 12.3 percentage points, which we describe without identifying a transition cost or causal friction.

The second gap is the evaluation of a difficulty prior. We audit output protocols on one local model and separately examine a multi-model matrix. Failed implementations and mixed return formats are kept distinct from valid protocol-specific estimates; parsing success alone does not show that an estimate measures the intended construct.

Exploratory cold-start analyses were added during execution. Their configurations and evaluation criteria are not sufficiently matched to isolate a criterion-only effect; they are described in the supplementary record and are not the central evidence of the present paper.

### 1.3 Contributions

We contribute an offline evaluation of three components. First, public Junyi logs describe success rates across ordered teacher labels and transition groups. Second, simulation compares policies under a documented empirical calibration, without inferring human learning effects. Third, stored local-model ratings are audited for valid protocols, ordinal agreement, ties and uncertainty. Cold-start fusion analyses are exploratory comparisons across different configurations and criteria; they are not a controlled test that changes only one evaluation criterion.

## 2 Related Work

Treating difficulty or curriculum selection as a bandit is not new. Castleman, Macar and Salleb-Aouissi (2024) simulated three groups of 500 learners using BKT calibrated with transformed ASSISTments data and reported higher simulated mastery for a difficulty-aware hierarchical tutor; their system already incorporates memory decay in decision-making. Lipschitz bandits include adversarial adaptive discretization (Podimata & Slivkins, 2021), non-stationary algorithms (Nguyen, Gaucher & Vernade, 2025), and lexicographic algorithms (Xue et al., 2025). MemoryKT (Lin et al., 2025), MLEKT (Qian et al., 2026), SAFFKT (Song et al., 2024), and TPR-KT (Zhang et al., 2025) model memory or forgetting in knowledge tracing. Accordingly, our architectural proposal specifies a retrievability state and ordinal difficulty actions within LearnFlow; it is not a claim that memory has never informed tutoring decisions. The regret-bound discussion adapts existing theory and supplies no new proof.

Results on LLM difficulty annotation depend on datasets, protocols and validation criteria. Ballon, Algaba, Verbeken and Ginis (2025) evaluate pairwise comparisons and Bradley–Terry estimates across JEE, CMCQRD and Omni-Math using available human labels and performance measures, reporting Pearson r ≥ 0.80 (n = 1,876) and less than 6% deterioration under 10% injected noise. Their synthetic tier-separation demonstration is a subset, not the sole evaluation dataset. Li et al. (2026) report an overall mean Spearman correlation of 0.28 across 21 models and four domains (Table 1) and mean self-assessment AUROC of 0.56 (Table 5); increasing model size does not reliably improve alignment. These studies evaluate different settings. Our analysis examines the stability and criterion agreement of the stored annotation outputs in §5.4, without claiming a universal failure of LLM difficulty estimation.

On optimal difficulty, Wilson et al. (2019) derive a target under a specific gradient-descent binary-classification learner. The observed practice-error distribution in assist09 instead describes experienced difficulty: 49.3% of windows lie at error rates 0.15–0.35, with a 95% bootstrap modal set {0.25, 0.20}. The simulator's 0.75 target is a chosen policy setting, not a validated optimum or a test of that theoretical rule.

## 3 Problem Formalization

We consider a sequential decision problem whose candidate item labels are ordered easy, normal and hard. An ordinal index provides an ordering, not a calibrated distance or a verified Lipschitz condition. A memory or retrievability state is an architectural proposal; the analyses here do not directly validate its contribution to learning. Independent-arm policies can also represent unequal rewards at different labels, so observed transition differences cannot rule them out.

The `flow_zone` simulator policy targets a chosen success-rate band near 0.75. Its comparison with an ability-aware policy is conditional on the simulator calibration, update rules and reward. The fitted shrinkage expression λ*(k) = 1/(1+(k/27.3)^0.895) belongs to an exploratory cold-start configuration and has no validated deployment guarantee. Neither expression is an optimal human practice rule.

## 4 Data and Methods

### 4.1 Action space from real logs

Junyi Academy (CC BY-NC-SA 4.0): 16,217,311 interactions, 72,758 users, 1,326 exercises. Within a level-3 knowledge strand we group exercises by expert difficulty label and fit p(item, ability-decile) with stratified empirical success rates from 52,733 users with ≥20 attempts, reducing dependence on a parametric response curve while retaining fixed-probability simulator assumptions.

### 4.2 LLM annotation protocols

The protocol audit uses local `qwen36:latest`, identified by the stored manifest, while the model matrix is a separate set of 11 local open-weight cells. Absolute item ratings and enumerated-array batch rankings are evaluated separately. In the batch protocol, 47 of 60 enumerated-array batches parse successfully; the 48 free-string batches are a different return format and are not merged into the primary capability estimate. No new model call is used in the stored-data recalculation.

### 4.3 Model matrix and verification

The stored matrix has 11 evaluated cells across four nominal families and three parameter-size tiers; unexecuted cells are not imputed. Recalculation uses the saved records, explicit merge precedence, parsing checks and item-level resampling. The detailed protocol run is identified by stored model metadata; model names and metadata do not by themselves prove byte-identical inference on a different runtime. Engineering verification is reported in the reproducibility record, separately from scientific validity.

## 5 Results

### 5.1 Observed response rates across ordered labels

**Table 1. Empirical success rate by expert difficulty label (Junyi, level-3 strand)**

| Expert label | Success rate |
|---:|---:|
| easy | 0.7355 |
| normal | 0.6328 |
| hard | 0.6160 |

Observed success rates decrease across the three teacher labels. This describes label agreement with responses in the analyzed logs. Transition-group rates are reported separately below without a causal interpretation.

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

Hard-to-easy transitions have success rate 0.7534, compared with 0.6302 for easy-to-hard transitions, a difference of 12.32 percentage points. The destination difficulty changes between these groups. Selection, learner ability and prior history are not controlled, so the comparison does not identify a transition cost, reject independent-arm models or verify a Lipschitz reward condition.

### 5.2 A deterministic paired response-success replay

**Table 3. Paired simulator replay with 500 scenarios and 40 responses per scenario**

| Policy | Mean response success | Conditional 95% percentile interval |
|---|---:|---|
| `flow_zone` | 0.7286 | [0.7164, 0.7411] |
| `ability_correct` | 0.7127 | [0.7001, 0.7258] |
| `ability_inverted` | 0.6871 | [0.6709, 0.7046] |
| `all_easy` | 0.7674 | [0.7536, 0.7815] |
| `all_hard` | 0.6508 | [0.6335, 0.6692] |
| `random` | 0.7022 | [0.6870, 0.7175] |

This new deterministic replay uses seed 20261007, sorted eligible item pools, equal sampling across ability deciles, and common initial decile/strand and random uniforms across policies. It is separate from the archived v2 simulator summaries. Each response is sampled from a fixed decile-specific empirical probability clipped to [0.05, 0.98]. The score is the fraction of simulated correct responses; neither latent ability nor memory improves during the sequence. It is therefore a response-success simulation, not a learning model.

The target-band policy exceeds the ability-threshold policy by 0.0159, with an exploratory paired scenario interval [0.0112, 0.0206]. It is below the always-easy policy by 0.0388, with interval [−0.0444, −0.0336]. Maximizing correctness favors easy items, illustrating why response success alone is insufficient as a learning objective. These 2,000-resample intervals condition on the calibration archive, do not include student-calibration uncertainty, and are not multiplicity-adjusted tests of human policy effects.

### 5.3 The target band

The target-band policy uses success rate near 0.75 as an explicit simulator setting. It is not a rule inferred to maximise learning from the assist09 mode. The observed distribution is generated jointly by item allocation and learner ability and cannot determine an optimal target. A causal claim about the effect of those targets on learning would require separate outcome evidence and is outside this offline paper.

### 5.4 Protocol-specific difficulty agreement

**Table 4. Local protocol audit on DBE-KT22**

| Protocol | Sample | Spearman ρ |
|---|---|---:|
| Anchored absolute rating | 212 items | 0.2195 |
| Enumerated-array ranking plus Bradley–Terry | 47 valid of 60 batches | 0.1553 |
| Free-string ranking, diagnostic only | 48 batches | 0.0478 |

Mixed-return-format estimates are retained only in diagnostic outputs and do not enter the primary interpretation. The paired item bootstrap uses 2,000 resamples, seed 20260922, and refits Bradley–Terry on each resample of valid enumerated-array constraints. The absolute-minus-ranking difference is 0.0642, with percentile 95% interval [−0.0759, 0.2464] and bias-corrected interval [−0.1068, 0.2042]. Both include zero; this does not establish equivalence. The BC correction has no acceleration term and does not remove possible graph-resampling design bias. Similar marginal correlations do not establish that model ratings add little incremental value beyond behavioural evidence: that claim requires a joint predictive comparison. The XES3G5M protocol gives a negative correlation near zero and does not establish the reason for the difference between item banks.

### 5.4.1 Ordinal metrics with explicit tie handling

Ordinal AUC compares only pairs with different teacher labels. A correctly ordered pair scores one, a model-rating tie scores 0.5, and a reversed pair scores zero. Kendall τ_b removes joint ties from the counts of pairs tied on only one variable. A hand-calculated example and random tied samples are checked against SciPy's standard τ_b. All metrics are invariant to reversing the input record order. Top-k Jaccard is omitted because three-level ratings do not identify a unique top-k set under ties.

**Table 4a. Recalculated original eight-model rating file**

| Model | Items | Spearman | Kendall τ_b | Ordinal AUC |
|---|---:|---:|---:|---:|
| qwen36:latest | 212 | 0.1744 | 0.1593 | 0.5745 |
| qwen3:1.7b | 212 | 0.1072 | 0.1022 | 0.5125 |
| llama3.2:1b | 212 | -0.0337 | -0.0328 | 0.4846 |
| llama3.1:8b | 212 | 0.2430 | 0.2230 | 0.6088 |
| qwen3:8b | 212 | 0.0849 | 0.0810 | 0.5364 |
| mistral:7b | 212 | 0.2085 | 0.1974 | 0.5798 |
| deepseek-v2:16b | 212 | 0.2521 | 0.2265 | 0.6169 |
| deepseek-r1:1.5b | 212 | -0.0088 | -0.0082 | 0.4970 |

The AUC range is 0.4846–0.6169. Two models are below the chance-order level of 0.5, while a collapsed constant prediction would score exactly 0.5. This is weak ordering evidence in these local-model configurations; it cannot establish the performance of larger API models. The protocol-audit run and matrix run of the anchor model are separate executions and their correlations are not interchangeable.

### 5.5 Exploratory cold-start material

Earlier cold-start analyses use different signal directions, shrinkage settings, samples and outcomes. They are retained in `M3_exploratory_coldstart_SI.md` with their unresolved configuration boundaries. They do not establish that an unchanged estimator reverses value solely because an evaluation criterion changes, and they do not link the stored LLM ratings causally to a sequencing loss. No headline deployment-value claim is based on those exploratory summaries.

### 5.6 Scope and uncertainty of the model matrix

The 11-cell matrix reads `local_matrix.jsonl`, `local_matrix_ministral.jsonl` and `local_matrix_mixtral_r1.jsonl`. Complete later records replace interrupted earlier records for the same model, condition and item. E1-A correlations and confidence intervals use the same paired-item percentile bootstrap with 2,000 resamples and seed 20260922 for every cell. Model-family and architecture metadata come from the stored metadata sources rather than manual CSV edits. Parsing, output collapse and batch coverage are reported independently of correlation.

No tested scale trend or family advantage is claimed without paired comparisons and correction for the comparison family. Quantisation and model lineage vary across cells. Cloud pilot results may indicate a boundary of the evaluated local models, rather than a general inability of LLMs to judge difficulty; the pilot is not pooled with the controlled matrix. Three independent repeat runs and the planned API models have not been executed.

### 5.7 What the offline evidence establishes

The stored ratings show limited teacher-label agreement in the evaluated configurations. That agreement is an annotation criterion, not measured decision value. The exploratory cold-start comparisons motivate separately evaluating an estimator against a deployment-relevant outcome; they do not establish that the observed LLM ratings caused the simulated fusion losses, or that one unchanged estimator reverses sign solely because the criterion changes.

### 5.8 Reproducibility artefacts

Annotation protocols, prompt templates, parsing procedures and optimisation scripts are stored in the accompanying project, and the audited model is pinned by manifest digest rather than by name so that the annotation step is byte-identifiable. The landing implementation is checked against the optimization script by `o11_land_verify`, which reproduces every k × variant gain (15/15 checks), and the wider pipeline is covered by automated engineering tests. These artifacts support recomputation of the retained model metrics and the new simulator replay. The archive does not establish byte-identical model generation on different runtimes or complete reproducibility of every historical exploratory summary.

## 6 Discussion

Observed success rates decrease across Junyi’s ordered teacher labels, and transition groups differ by 12.3 percentage points. These descriptions support using an ordered label vocabulary for this item bank. They do not establish reward smoothness, causal transition effects or superiority over independent-arm policies.

The calibrated simulator reports a slightly higher mean for the target-band policy than for the ability-threshold policy, with a conditional paired interval. The always-easy policy has still higher response success. These comparisons do not show learning effectiveness or justify an optimal target. The inverted-prior result illustrates sensitivity to a deliberately misspecified prior within the simulator; it is not a measured harm to students.

The local-model findings are protocol-specific. The detailed audit produces correlations of 0.1553 and 0.2195 from valid protocol subsets, with uncertainty and coverage limits. The model matrix includes parsing and collapse diagnostics. These results do not establish the reliability of all LLMs, a monotonic scale effect, or human learning outcomes. Independent repeat runs and additional held-out item banks would strengthen external validity while remaining compatible with an offline study.

For practical use, separate protocol validity, item-label agreement and decision outcomes. A high parsing rate does not validate difficulty, and agreement with teacher labels does not validate a sequencing policy. The fitted shrinkage rule and 0.75 simulator target remain exploratory specifications whose value depends on the selected evaluation outcome.

## 7 Archived Design Predictions and Evidence Boundaries

**Table 6. Pre-registration predictions against measured outcomes (selected)**

| Prediction | Measured | Verdict |
|---|---|---|
| Ordinal action space improves over independent arms | Ordered descriptive rates and 12.3 pp transition-group difference | Comparative policy claim not established |
| Difficulty-aware policy beats difficulty-agnostic | Paired replay is conditional on fixed probabilities; always-easy has the highest correctness mean | Not supported as stated |
| Higher ensemble size raises LLM-prior reliability | Prior is weak and protocol-bound; two protocols unusable | Refined |
| Cold-start fusion improves sequencing | Earlier analyses differ in configuration and criterion; matched claim not established | Refuted as unconditional |

Deviations from the pre-registration are the natural execution of its go/no-go checkpoint: when a precondition (protocol parseability) fails, downstream flow should not start, and we report that failure rather than a number derived from it. The cold-start sequencing experiment was added during execution and is declared as such, together with the reason it was added.

## 8 Limitations

We list the limitations we consider material, including several that weaken our own preferred interpretation. Reporting them is not a formality: the configuration ambiguity of cold-start summaries (item 7) and the unexplained XES3G5M null (item 5) are the two findings most likely to change a reader's conclusion.

**Table 7. Material limitations**

| # | Gap |
|---|---|
| 1 | Detailed protocol audit on one local model and a separate 11-cell matrix; neither represents all LLMs |
| 2 | Open-weight matrix covers only 11 evaluated cells across four families × three scales |
| 3 | No human-subject experiment; all results are log-based or simulation-calibrated |
| 4 | Simulation calibrated on 52,733 users with ≥20 attempts, not on live deployment |
| 5 | XES3G5M correlation is negative and near zero; the cause is not explained |
| 6 | Two of four annotation protocols are unusable; the cause is only partially diagnosed |
| 7 | Cold-start analyses change both configuration and criterion, precluding a criterion-only inference |
| 8 | λ*(k) is fitted on the assessed k range; extrapolation beyond it is untested |
| 9 | Expert difficulty labels are treated as ground truth where used as such |
| 10 | The 0.75 flow-zone target is a chosen simulator setting, not an optimum |
| 11 | Transition-group differences are descriptive and confounded by destination difficulty and selection |
| 12 | Regret bounds are adapted from existing theory; no new proof is claimed |
| 13 | The contribution of the proposed retrievability state is not directly validated |

## 9 Conclusion

Public logs describe an ordered difficulty-label space; calibrated simulation illustrates the sensitivity of policy behavior to priors; and stored local-model outputs show limited, protocol-dependent agreement with teacher difficulty labels. These findings are conditional on the evaluated banks, models, quantizations and implementations. No new human data were collected, and the paper does not establish learning improvements, an optimal practice rate, or a causal effect of difficulty transitions. The main methodological implication is to distinguish parsing success, annotation agreement and deployment outcomes when evaluating a difficulty prior.

Future offline work can repeat model protocols, compare paired model differences, evaluate separate held-out item banks and assess calibration sensitivity. New human studies are a possible later direction, not a prerequisite claimed by this paper for its descriptive and computational findings.

## Data, code and study scope

No new participants were recruited. The study uses released educational logs, stored model outputs and computational simulation. XES3G5M provides a separate public K12 bank for offline item inspection; preparing that bank is not a new annotation experiment. No new human research approval number or exemption determination is asserted. Dataset permissions, processing choices, input hashes and regeneration commands accompany the reproducibility materials. A final immutable public release and journal-specific availability statement have not yet been registered.

## AI assistance disclosure

The author reports using WorkBuddy and Codex, and identifies ChatGPT, DeepSeek and Hy4 as tools/models used during project and manuscript preparation. Codex assisted with code repair, stored-data analysis, reference checking and manuscript revision in this revision. Exact model versions, dates, and the mapping between tools and individual tasks remain to be documented. The author retains responsibility for the manuscript and must personally verify the final text, calculations, citations and code before submission. This disclosure does not assert that that final personal review has already occurred.

## References

[1] Castleman, B., Macar, U., & Salleb-Aouissi, A. (2024). Hierarchical multi-armed bandits for the concurrent intelligent tutoring of concepts and problems of varying difficulty levels. *Deployable RL: From Research to Practice @ Reinforcement Learning Conference (RLC)*. arXiv:2408.07208.

[2] Podimata, C., & Slivkins, A. (2021). Adaptive discretization for adversarial Lipschitz bandits. In *Proceedings of the 34th Conference on Learning Theory (COLT 2021)*, PMLR 134, 3788–3805. arXiv:2006.12367.

[3] Nguyen, N., Gaucher, S., & Vernade, C. (2025). Non-stationary Lipschitz bandits. *Advances in Neural Information Processing Systems (NeurIPS) 2025*, 38, 16937–16988. DOI: 10.52202/085713-0509. arXiv:2505.18871.

[4] Xue, B., Cheng, J., Liu, F., Wang, Y., Zhang, L., & Zhang, Q. (2025). Lexicographic Lipschitz bandits: New algorithms and a lower bound. *Journal of Machine Learning Research*, 26(223), 1–56.

[5] Lin, M., Deng, K., Wu, Z., Zheng, Z., & Li, J. (2025). MemoryKT: An integrative memory-and-forgetting method for knowledge tracing. *arXiv preprint arXiv:2508.08122*.

[6] Qian, W., Wei, P., Lan, T. X., & Qi, L. J. (2026). Personalized knowledge tracing model with memory reinforcement and forgetting-aware mechanisms. *PRICAI 2025: Trends in Artificial Intelligence, Part I*, Lecture Notes in Computer Science, 16451, 54–69. DOI: 10.1007/978-981-95-7075-1_4.

[7] Song, J., Wang, Y., Zhang, C., & Xie, K. (2024). Self-attention and forgetting fusion knowledge tracking algorithm. *Information Sciences*, 680, 121149. DOI: 10.1016/j.ins.2024.121149.

[8] Zhang, K., Bi, L., Xiong, J., Wu, Q., & Zhu, X. (2025). Three-way partitioning graphs with reinforcement learning for adaptive knowledge tracing. *Information Sciences*, 721, 122644. DOI: 10.1016/j.ins.2025.122644.

[9] Rosas, D. A., Padilla-Zea, N., & Burgos, D. (2026). Modelling the Balance Axiom in Flow Theory: A physiological and computational approach in STEAM education. *Sensors*, 26(1), 38. DOI: 10.3390/s26010038.

[10] Dell'Anna, H., Brunetto, D., & Gera, R. (2026). Integrating flow framework into learning and development systems. *LUMAT-B: International Journal on Math, Science and Technology Education*, 11(2), Article 23.

[11] Ballon, M., Algaba, A., Verbeken, B., & Ginis, V. (2025). Estimating problem difficulty without ground truth using Large Language Model comparisons. *arXiv preprint arXiv:2512.14220*. DOI: 10.48550/arXiv.2512.14220.

[12] Li, M., Chen, H., Xiao, Y., Chen, J., Jiao, H., & Zhou, T. (2026). Can LLMs estimate student struggles? Human-AI difficulty alignment with proficiency simulation for item difficulty prediction. In *Findings of the Association for Computational Linguistics: ACL 2026* (pp. 25414–25441). Association for Computational Linguistics. DOI: 10.18653/v1/2026.findings-acl.1270.

[13] Liu, Y., Bhandari, S., & Pardos, Z. A. (2025). Leveraging LLM respondents for item evaluation: A psychometric analysis. *British Journal of Educational Technology*, 56(3), 1028–1052. DOI: 10.1111/bjet.13570.

[14] Ding, M., Deng, C., Choo, J., Wu, Z., Agrawal, A., Schwarzschild, A., Zhou, T., Goldstein, T., Langford, J., Anandkumar, A., & Huang, F. (2024). Easy2Hard-Bench: Standardized difficulty labels for profiling LLM performance and generalization. Advances in Neural Information Processing Systems, 37. https://doi.org/10.52202/079017-1407

[15] Pratiwi, O., & Fakhrurroja, H. (2025). Automatic labeling using generative AI in educational question dataset. *2025 1st International Conference on Data Science and Geoinformatics (ICDSG)*, 230–235. DOI: 10.1109/ICDSG67714.2025.11381390.

[16] Parfenova, A., Marfurt, A., Pfeffer, J., & Denzler, A. (2025). Text annotation via inductive coding: Comparing human experts to LLMs in qualitative data analysis. In *Findings of the Association for Computational Linguistics: NAACL 2025* (pp. 6471–6484). Association for Computational Linguistics. DOI: 10.18653/v1/2025.findings-naacl.361.

[17] Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications*, 10(1), 4646. DOI: 10.1038/s41467-019-12552-4.

[18] Chang, H.-S., Hsu, H.-J., & Chen, K.-T. (2015). Modeling exercise relationships in e-learning: A unified approach. In Proceedings of the 8th International Conference on Educational Data Mining (pp. 532–535). International Educational Data Mining Society. https://www.educationaldatamining.org/EDM2015/uploads/papers/paper_47.pdf

[19] Abdelrahman, G., Abdelfattah, S., Wang, Q., & Lin, Y. (2022). DBE-KT22: A knowledge tracing dataset based on online student evaluation. arXiv:2208.12651. https://arxiv.org/abs/2208.12651v1

[20] Liu, Z., Liu, Q., Guo, T., Chen, J., Huang, S., Zhao, X., Tang, J., Luo, W., & Weng, J. (2023). XES3G5M: A knowledge tracing benchmark dataset with auxiliary information. Advances in Neural Information Processing Systems, 36, 32958–32970. https://doi.org/10.52202/075280-1429

[21] Feng, M., Heffernan, N. T., & Koedinger, K. R. (2009). Addressing the assessment challenge with an online system that tutors as it assesses. User Modeling and User-Adapted Interaction, 19(3), 243–266. https://doi.org/10.1007/s11257-009-9063-7

[22] Weber, D., Becker, N., Spinath, F. M., & Koch, M. (2026). The stability of IRT parameters under several test equating conditions. Frontiers in Psychology, 16, 1652341. https://doi.org/10.3389/fpsyg.2025.1652341

[23] Kolesnikova, D., Fedyanin, K., Hofman, A. D., Brinkhuis, M. J. S., & Bolsinova, M. (2026). Estimating item difficulty with Large Language Models as experts. arXiv:2605.18562.

[24] Razavi, P., & Powers, S. J. (2026). Estimating item difficulty using large language models and tree-based machine learning algorithms. *International Journal of Artificial Intelligence in Education*, 36(3), Article 100015. DOI: 10.1016/j.ijaied.2026.100015.

[25] Gan, W., Sun, Y., Peng, X., & Sun, Y. (2020). Modeling learner's dynamic knowledge construction procedure and cognitive item difficulty for knowledge tracing. *Applied Intelligence*, 50(11), 3894–3912. DOI: 10.1007/s10489-020-01756-7.
