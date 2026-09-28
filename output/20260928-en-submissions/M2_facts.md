## Abstract

When a learning system registers dozens of behavioural intervention mechanisms at once, the intuitive expectation is that they will collide at run time, cancel each other out, and therefore require arbitration and budget governance. This paper tests that intuition head-on, and the results run against it — but the accounting must come first: the platform audited here has **54 registered** semantically de-duplicated gamified intervention mechanisms (LF-M01…LF-M54, registry fingerprint `ee1a49be5732`), of which **only 2 construct an intervention effect** (LF-M44 / LF-M52; sealed baseline tag `audit-m2-20260911`; under A2 the current HEAD carries **16** AST sites / **14** mechanism opt-ins, off by default), with maturity **complete 9 · partial 37 · placeholder 8**. These three figures must always be reported together, because "on the register" and "able to produce a run-time effect" are not the same thing, and every conclusion below is governed by the latter two. We report four measured findings. First, when mechanisms are mapped onto the intervention seven-tuple defined here, **42 of 54 (77.8%) cannot be assigned a direction field**, and four fields (`target_construct`, `channel`, `side_effect`, `precedence`) **do not exist anywhere in our own code**; this triggers the falsification threshold we set in advance (> 20%), and the conclusion is that the schema's granularity does not match the implementation's. **We explicitly classify this as a diagnosis of implementation completeness, not as a "discovery triggered by a falsification condition"**: designer and audited party are the same party, so the figure measures how much of the schema we wrote down has been implemented, not a general property of the world. Second, of the three conflict types, type I has 27 static latent pairs (all from the 9 × 3 direction table) and 2 document-anchored same-construct pairs, yet only **one pair is detectable at run time** (LF-M44 vs LF-M52), and it is dissolved at the "health override" layer rather than at the "direction cancellation" layer we designed — the latter is **dead code** under the current set of intervention-effect producers. Third, type II (renamed **budget contention**) has **0 run-time contention pairs**, its structural cause being that the secondary mechanisms write only evaluation records, construct no intervention effect, never enter the arbitrator,

HEAD # Conflict-Structure Audit of Multi-Intervention Coexisting Learning Systems
  LEAD: Zexiao Weng¹ and MinPo Jung¹,*

HEAD ## Abstract
  LEAD: When a learning system registers dozens of behavioural intervention mechanisms at once, the intuitive expectation is that they will collide at run time, cancel each other out, and therefore require arbitration and budget governance. This paper tests that intuition head-on, and the results run against it — but the accounting must

HEAD ## Author's Declarations
  LEAD: **First, this paper is "an internal static audit and its limits," not a general finding about similar systems.** The strongest claim this paper can make is the following: on the one code snapshot of the one system audited here, the static structure of its intervention conflicts is as reported, while the visibility of run-time co

HEAD ## 1 Introduction
  LEAD: **Chapter summary.** This chapter explains the origin of the problem. Research on adaptive gamification has long used "packaged gamification vs. no gamification" as its comparison unit and has failed to answer what happens when multiple intervention mechanisms are simultaneously present. This chapter identifies three internal co

HEAD ### 1.1 An engineering fact and an unnamed problem
  LEAD: Gamified learning systems have evolved over the past fifteen years from the "badge–points–leaderboard" trio to "adaptive gamification." The core claim of the latter is that different users prefer different game elements, so the system should dynamically select elements based on the user profile. Echoing this, a large body of res

HEAD ### 1.2 The audited object's pre-existing contradictions
  LEAD: The object of this audit is a real, deployed, and publicly released K12 adaptive learning platform. Its salient feature is scale, but it must be given under the **three-part accounting**: a unified mechanism registry **registers 54** semantically de-duplicated gamified intervention mechanisms (numbered LF-M01…LF-M54, contiguous 

HEAD ### 1.3 Contributions and main findings
  LEAD: This paper is a **static audit + cross-system replication**; it proposes no new detection algorithm and claims no mechanism is effective for learning. The contributions fall into four items, each supported by measured numbers.

HEAD ### 1.4 Structure and reproducibility
  LEAD: §2 reviews related work; §3 gives the intervention formalization criteria and the measured detection of three conflict types, and reports the dead-code finding and the audit conclusion on the compliance-preemption property S1; §4 reports the mechanism census, the relationship between the two taxonomies, and numeric drift; §5 dow

HEAD ### 1.5 Chapter summary
  LEAD: 1. Research problem: the interaction among mechanisms in a multi-intervention-coexistence system had not been named head-on, nor formalized as an auditable criterion. 2. Audited object: a K12 adaptive learning platform, **registering 54** semantically de-duplicated gamified intervention mechanisms (LF-M01…LF-M54, contiguous, fin

HEAD ## 2 Related Work
  LEAD: **Chapter summary.** This chapter reviews four related-work threads: adaptive gamification and user typologies, behavioural-change science and JITAIs, multi-objective identification and budget-constrained online learning, and gamification effect baselines and dark-side evidence. The focus is not the review itself but the structu

HEAD ### 2.1 Adaptive gamification and user typologies
  LEAD: The dominant paradigm of adaptive gamification is built on user typologies. Sailer et al. (2017) propose the HEXAD typology, dividing users into achievers, free spirits, socializers, philanthropists, players, and disruptors; a later meta-analysis (Sailer et al., 2020) tests the correspondence between type and element preference.

HEAD ### 2.2 Behavioural-change science and JITAI
  LEAD: The JITAI literature offers another thread: interventions should be delivered just in time at "vulnerable moments." Hsu et al. (2024), in a 62-study scoping review, note that most JITAIs rely on self-report adaptation, with insufficient transparency and heterogeneous validity. The theoretical integration of behaviour change in t

HEAD ### 2.3 Multi-objective identification and budget-constrained online learning
  LEAD: Pareto-set identification for multi-objective bandits (Kone et al., 2024; 2025) gives algorithms and information-theoretic lower bounds under fixed budget / fixed confidence, the latter further handling linear feasibility constraints; MORL policy composition (Kim et al., 2025) covers generalized p-mean preferences with α-approxi

HEAD ### 2.4 Gamification effect baselines and the dark side
  LEAD: The meta-analysis of Dai et al. (2025) (182 effect sizes / 37 RCTs, d = 0.566) and Slamet and Meng (2025) on collaborative learning (d ≈ 0.875) establish the average gamification effect, but their comparison unit is "packaged vs. no gamification," exactly exposing the gap in single-mechanism identification and inter-mechanism in

HEAD ### 2.5 Chapter summary
  LEAD: 1. The user-typology thread answers "who gets what element," not the interaction when multiple interventions are simultaneously present. 2. The JITAI literature and the theoretical-integration work on behaviour change have acknowledged that, when multiple intervention techniques target the same construct, their combination is no

HEAD ## 3 Audit Object and Method: Formalization of Intervention and Conflict Detection
  LEAD: **Chapter summary.** This chapter gives the paper's two core tools — the intervention seven-tuple ⟨trigger, target_construct, direction, channel, cost, side_effect, precedence⟩ and the type-I criterion based on directional opposition — and reports the measured detection of three conflict types: the unclassifiable proportion is 4

HEAD ### 3.1 The intervention seven-tuple and this paper's audit criterion
  LEAD: This paper defines the intervention unit as a seven-tuple

HEAD ### 3.2 Mapping coverage and the unclassifiable proportion: measured 77.8%, triggering the self-set threshold (**a diagnosis of implementation completeness**)
  LEAD: The audit maps the 54 mechanisms field by field onto the seven-tuple; the measured results are as follows.

HEAD ### 3.3 Detection of three conflict types
  LEAD: #### 3.3.1 Type I · effect-direction conflict

CAP **Table 1. The two run-time intervention-effect producers**

| Mechanism | Construction site | Run-time attributes |
|---|---|---|
| LF-M44 | `deep_addiction_engine.py:296` | `user_visible=True, health_critical=False, cost=1.5, priority=50` |
| LF-M52 | `learning_orchestrator.py:986` | `user_visible=False, health_critical=True, cost=0.0, priority=100` |

CAP **Table 2. Governance letters and the code-side categories they fall into**

| Governance letter | Code-side categories fallen into |
|---|---|
| A | motivation, retention |
| B | motivation, retention |
| C | cognition, motivation, selfreg |
| D | motivation, retention, selfreg |
| E | cognition, motivation, retention, selfreg |
| F | motivation, retention |
| G | cognition, motivation |
| H | health (the only single mapping) |

HEAD ### 3.4 A directly provable finding: the layer-2 direction cancellation is dead code under the current set of intervention-effect producers
  LEAD: Combining the results of type I and type II yields a software-engineering fact, previously unrecorded and directly provable.

HEAD ### 3.5 Audit conclusion on the compliance-preemption property S1
  LEAD: The original design formalized "compliance priority" as a machine-checkable system property S1:

HEAD ### 3.6 Chapter summary
  LEAD: 1. Of the seven-tuple, only `trigger` (implemented as `stage`, 54/54 available) and `direction` (12/54 available) exist in the implementation; the four fields `target_construct`, `channel`, `side_effect`, `precedence` do not exist in code; the unclassifiable proportion is **42/54 = 77.8%**, triggering this paper's self-set > 20%

HEAD ## 4 Mechanism Census, Taxonomy Conflict, and Numeric Drift
  LEAD: **Chapter summary.** This chapter reports the mechanism census and the counting caliber. The governance document organizes 54 mechanisms into A–H eight categories, while the code-side registry `CATEGORIES` has only five values; both distributions sum to 54 but cannot corroborate each other. The chapter also gives the landing-str

HEAD ### 4.1 Two taxonomies: the governance document's 8 categories and the code-side's 5 categories
  LEAD: **A fact extremely easy to miswrite must first be clarified**: the governance document organizes mechanisms into A–H **eight categories**. The code-side registry's `CATEGORIES` constant has only **five** values. The audit found no place that classifies mechanisms by A–H; the eight categories can only be parsed from the Markdown 

CAP **Table 3. Governance document's eight categories and mechanism counts**

| Category | Title | Mechanism count |
|---|---|---:|
| A | Behaviourism · reinforcement and reward | 8 |
| B | Commitment, loss, and goal gradient | 8 |
| C | Self-determination theory: autonomy · competence · relatedness | 6 |
| D | Social influence and social learning | 10 |
| E | Habit formation and self-regulation | 10 |
| F | Emotion and motivation triggers | 4 |
| G | UX micro-interaction and cognitive load | 4 |
| H | Health guardrail and ethics | 4 |

HEAD ### 4.2 Landing-strength stratification
  LEAD: The audit stratifies the 54 mechanisms by landing strength, with the results below (caliber per `scan_mechanism_landing.py:177` and `learning_orchestrator.PIPELINE_MECHANISM_MAP`):

CAP **Table 4. Landing-strength stratification of 54 mechanisms**

| Stratum | Measured | Caliber basis |
|---|---:|---|
| `landed` (implementation reference reachable, or wired/gated via orchestrator) | **54** | `scan_mechanism_landing.py:177` |
| `orphan` | **0** | — |
| Entered `PIPELINE_MECHANISM_MAP` step mapping | **34** | step 6(1)+8(2)+9(2)+12(1)+13(28) |
| Source-code-text reference only (not in step mapping) | **20** | 54 − 34 |
| Of which `is_enabled("<key>")` independently gated and truly called | **31** | 31 literals in `learning_orchestrator.py` |
| 3 health guardrails exempt from gating by design | 3 | `lai_downgrade` / `forced_rest` / `minor_protection` |

HEAD ### 4.3 Mechanism census (Table 5 material)
  LEAD: The audit performs an item-by-item census of the 54 mechanisms; the four-dimension distribution is as follows.

CAP **Table 5. Four-dimension mechanism census**

| Dimension | Distribution |
|---|---|
| stage (trigger stage) | during 20 / pre 14 / ambient 13 / post 7 |
| maturity | complete 9 / partial 37 / placeholder 8 |
| disposition | R 32 / K 15 / M 6 / D 1 |
| direction | unassigned 42 / approach 9 / withdraw 3 |

HEAD ### 4.4 Numeric drift and the PRD self-contradiction
  LEAD: The audit recomputed asset and counting metrics; the results show reproducible drift relative to the registration baseline.

CAP **Table 6. Asset and counting metrics: registration baseline vs. measured**

| Metric | Registration baseline | Measured | Verdict |
|---|---:|---:|---|
| `python_loc` | 25,389 | **26,107** | drift +718 |
| `source_files` | 87 | **90** | drift +3 |
| `service_modules` | 54 | **57** | drift +3 |
| `api_files` | 13 | 13 | consistent |
| `api_routes_defined` | — | 104 | — |
| `api_routes_reachable` | 104 | 104 | consistent (unreachable = 0) |
| `test_files` | 53 | **54** | drift +1 |
| `test_functions` | 826 | **842** | drift +16 |

HEAD ### 4.5 Chapter summary
  LEAD: 1. The A–H eight categories are the **governance-document taxonomy** and must not be attributed to the code-side registry; the code-side `CATEGORIES` has only the five values retention / motivation / selfreg / cognition / health, both distributions sum to 54 but cannot corroborate each other. 2. Landing-strength stratification: 

HEAD ## 5 Design Requirements Derived from the Audit: An Auditable Intervention Ledger
  LEAD: **Chapter summary.** This chapter downgrades the auditable intervention ledger from an "evaluated contribution" to a "design requirement derived from the audit." The audit confirms the repository has no ledger implementation: no `budget_consumed` field, no `preempted_by` field, no ledger module, and `ArbitrationTrace` is not per

HEAD ### 5.1 Ledger schema and current implementation status
  LEAD: At the original design stage, the auditable intervention ledger was listed as an "evaluated contribution"; after the audit this paper **downgrades it to a design requirement derived from the audit**, because it is not currently implemented. The reason is as follows.

HEAD ### 5.2 Three classes of consistency checks: the algorithm is executable and A3 synthetic sessions have produced a distribution
  LEAD: The original design defined three ledger violation types and their check algorithms:

CAP **Table 7. Three ledger violation types and checks**

| Violation type | Definition | Planned check | This-round status |
|---|---|---|---|
| Budget overspend | Σ `budget_consumed` within a session > B | aggregate and compare by session | **Implemented and runnable; A3 synthetic sessions have produced a distribution** |
| Executed although preempted | `preempted_by` non-empty but `arbitration_decision = executed` | record-level assertion | **Implemented and runnable; measured violation rate = 0 (safety invariant holds)** |
| Decision with no record | intervention effect appears but no corresponding ledger record | reconcile event stream with ledger | **Implemented and runnable; the ledger is the record source, always 0** |

CAP **Table 8. Run-time conflict distribution: before vs. after Route A producer expansion**

| Metric | Before (2-producer baseline) | After (≥14 producers, opt-in) |
|---|---:|---:|
| Run-time conflict frequency (Layer-2 direction-opposition discard ratio) | 0.000 | 0.633 |
| Contention rate (step ratio discarded by either health-veto or conflict-resolution layer) | 0.299 | 0.971 |
| Budget-exhaustion rate (session ratio with at least one step discarded by budget) | 0.433 | 1.000 |
| Preemption-violation rate (step ratio with `preempted_by ∩ delivered ≠ ∅`) | 0.000 | 0.000 |

HEAD ### 5.3 Replacing a distributed ledger with Merkle anchoring (design argument)
  LEAD: As a design argument rather than a measured conclusion: the ledger's tamper-resistance requirement can be met by a Merkle tree plus periodic public anchoring, whose cost and complexity are about two orders of magnitude lower than a distributed ledger, and which requires no institutional authorization or legal recognition. This p

HEAD ### 5.4 Chapter summary
  LEAD: 1. The repository has no intervention-ledger implementation, so all content in this chapter is a **design specification**, not a measured result. 2. The three consistency checks (budget overspend, executed although preempted, decision with no record) **are executable, and A3 synthetic sessions (10,000 sessions × 40 steps) first 

HEAD ## 6 Cross-System Replication (E2)
  LEAD: **Chapter summary.** This chapter reports cross-system replication (E2). File-by-file coding of Ludilearn (6 mechanisms) and Level Up XP (11 mechanisms) shows: under the strict caliber, both external systems have 0 type-I conflicts. Ludilearn makes conflict non-existent by construction through mutually exclusive activation; Leve

HEAD ### 6.1 Audit objects and coding method
  LEAD: - **System A · Ludilearn**: `https://github.com/DigiDago/moodle-format_ludilearn`, commit `eb69582fb4def6e4cbb26c2146ceb90435951c53`, GPL-3.0, PHP. This system is also part of the LudiMoodle+ project (French ANR e-FRAN / France 2030) and **explicitly sells itself on "adaptive gamification,"** with a Hexad-profile adaptation algo

HEAD ### 6.2 Ludilearn: type I and type III both 0, conflict non-existent by construction
  LEAD: **Table 9. Ludilearn conflict detection**

| Conflict type | Detected | Note |
|---|---:|---|
| Type I (strict: same target and opposite direction) | **0** | `score` etc. are approach; `timer` is withdraw (timeout penalty, `timer.php:46`'s `DEFAULT_PENALTIES=20`), but targets differ (engagement/performance vs. time/rhythm) |
| Type I (relaxed upper bound: any approach × withdraw) | 5 | holds only when target matching is ignored |
| Type II (budget contention) | no budget concept | 4 mechanisms (badge/progress/ranking/score) write the same user state, but the system has no rate cap |
| Type III (objective conflict) | **0** | no compliance/health-guardrail mechanism |

HEAD ### 6.3 Level Up XP: type III = 1, rate windows isomorphic to budget governance
  LEAD: **Table 10. Level Up XP conflict detection**

| Conflict type | Detected | Note |
|---|---:|---|
| Type I (strict) | **0** | no same-target opposite-direction pair |
| Type I (relaxed upper bound) | 18 | 2 withdraw (`rule_limits`, `cheatguard`) × 9 approach |
| Type II (budget contention) | **exists, with explicit cap** | 5 mechanisms (xp_points/levels/leaderboard/rank/badge) write the same user state; `classes/local/ruletype/limit_spec.php` provides **H/D/W/M four-tier rate windows** plus a `timesallowed` cap |
| Type III (objective conflict) | **1** | `cheatguard` (compliance, anti-cheat interception) against all approach mechanisms |

HEAD ### 6.4 Cross-system conclusion: conflict is structurally avoided, not resolved
  LEAD: Placing the two systems side by side with this system yields this paper's most important comparative conclusion:

CAP **Table 11. Cross-system comparison of conflict structure**

| | This system | Ludilearn | Level Up XP |
|---|---|---|---|
| Mechanism count | **Registered 54 / effect-producing 2** (sealed baseline tag `audit-m2-20260911`; under A2 the current HEAD carries **16** AST sites / **14** mechanism opt-ins, off by default) **/ maturity 9·37·8** | 6 | 11 |
| Type I (strict) | 1 (and dissolved by health veto) | 0 | 0 |
| Type I (relaxed upper bound) | 27 (static latent pairs) | 5 | 18 |
| Type II | 0 (nocarrier) | no budget concept | explicit rate cap exists |
| Type III | 7/8 letters span categories | 0 | 1 |
| Conflict-handling method | layered arbitration (layer 1 reached, layer 2 dead code) | mutually exclusive activation, impossible by construction | rate windows, capped in advance |

HEAD ### 6.5 Chapter summary
  LEAD: 1. Under the strict caliber, both external systems have **0** type-I conflicts (Ludilearn 0, Level Up XP 0). 2. Ludilearn's conflict is **non-existent by construction**: `attribution_game_element()` first deletes other elements' attributions under the same section before assignment (`classes/local/gamification/manager.php:126-14

HEAD ## 7 Prediction-versus-Measurement Comparison
  LEAD: **Chapter summary.** This chapter presents side by side the five predictions fixed before the audit and the measured results. P1 (expected unclassifiable proportion 10–20%) is overturned by the measured 77.8% and triggers the falsification condition; P2 (three conflict types universal) is overturned; P3 (cross-system replication

CAP **Table 12. Predictions fixed before the audit versus measured results**

| No. | Prediction before audit | Measured | Verdict |
|---|---|---|---|
| P1 | After mapping 54 mechanisms to the seven-tuple, **10–20% were expected to be unclassifiable due to semantic ambiguity**; criterion: > 20% means schema granularity must be re-designed | **77.8% (42/54)**, four fields **do not exist in our own code** | **Prediction overturned → triggered self-set threshold**; conclusion: schema granularity does not match implementation granularity. **Qualitative correction (reviewer §6.1)**: this is a **diagnosis of implementation completeness** (designer and audited party are the same), **not** a general discovery about the external world; the original "falsification-condition triggered" phrasing is withdrawn to "self-set threshold triggered" |
| P2 | Three conflict types universal in this system; type I contains at least the structural case "FOMO × minor protection × rest reminder" | Type I run-time **only 1 pair** (M44–M52); type II **0 pairs**; type III is 7/8 letters spanning categories | **Prediction overturned** (conflicts not universal) |
| P3 | Cross-system replication would upgrade the single-point observation into a class finding: the two external systems would also detect non-zero conflict | Ludilearn type I/III both **0**; Level Up XP type I **0**, type III **1** | **Prediction overturned** (direction reversed: conflicts rare) |
| P4 | Compliance-preemption property S1 expressible in temporal logic and **model-checkable** on the orchestrator state machine | S1 satisfied at the implementation level but **not expressed by the system itself**, no arbitration trace persisted, so neither effectively refutable nor with independent verification evidence | **Not tested** (downgraded to design requirement) |
| P5 | Ledger three violations reliably detectable (expected detection rate > 0.95, false-positive rate < 0.05) | **Cannot execute**: `budget_consumed`/`preempted_by`/ledger have zero matches in the repository | **Not tested** (original hypothesis deleted) |

HEAD ### 7.1 Chapter summary
  LEAD: 1. Three predictions (P1–P3) were overturned, all in directions opposite to the pre-audit expectation; among them P1 directly triggered this paper's self-set > 20% threshold, but the qualitative classification of that result is a **diagnosis of implementation completeness** (designer and audited party are the same), so its "over

HEAD ## 8 Discussion
  LEAD: **Chapter summary.** This chapter discusses this paper's positioning and practical implications. The audit conclusion forces this paper to downgrade its own positioning once: S1 is implied by the implementation but not expressed by the system itself, the allocation model has no realcarrier because the run-time contention count i

HEAD ### 8.1 Self-assessment: "taxonomy or method"?
  LEAD: The audit conclusion forces this paper to honestly downgrade its own positioning once. The original design prepared three conditions to cross the verdict "this is merely a taxonomy": the machine-checkability of S1, the applicability precondition of the allocation model's regret analysis, and the cross-project replication E2. The

HEAD ### 8.2 This paper's current form and the choice between Route A / Route B
  LEAD: The reviewer's judgement is clear: **this paper's existing material is sufficient to support a limited internal static audit, but insufficient to support an empirical-software-engineering journal paper**; the question "what can other system designers learn from this audit" currently has a weak answer ("register mechanisms but pr

HEAD ### 8.3 Teaching and practical implications
  LEAD: For designers of adaptive learning systems, this paper's implications are three, all directly actionable. First, **count the producers first, then talk about arbitration**: before claiming a system has conflict governance, first `grep` the number of intervention-effect construction points; if there is only one producer at the sa

HEAD ### 8.4 Chapter summary
  LEAD: 1. This paper **does not claim** to have proposed a verified method; the contribution is the audit itself, i.e., clarifying a problem assumed to exist but never checked into "in the system audited here and 2 external systems it almost never occurs." 2. The design intuition ("more mechanisms, more conflict, more need for arbitrat

HEAD ## 9 Honest Gap List (Limitations)
  LEAD: **Chapter summary.** This chapter lists this paper's limitations and honest gaps item by item, without merging or weakening. The **twelve** gaps come from four aspects: environment and sample (MySQL not measured, cross-system sample only 2 and homologous, external coding no reliability, no real-person experiment), the audited sy

HEAD ### 9.1 Chapter summary
  LEAD: 1. Of the twelve limitations ①–⑫, ②③ come from sample and method, ①⑥⑧ from implementation and environment gaps, **⑩⑪ from the hard limits of material and reproducibility (topmost)**, and ④⑤⑦⑨⑫ from this paper's self-limitations and unfinished work. 2. The three most affecting generalizability: cross-system sample small and homol

HEAD ## 10 Conclusion
  LEAD: **Chapter summary.** This chapter summarizes the whole paper. The headline caliber is the three-part "registered 54 / effect-producing 2 / maturity 9·37·8." The three core numbers of the audit are: unclassifiable proportion 77.8% (**qualitatively a diagnosis of implementation completeness**, not a discovery); type-I conflict con

HEAD ### 10.1 Chapter summary
  LEAD: 1. **Headline caliber (three-part, none dispensable)**: registered **54** / effect-producing **2** (sealed baseline tag `audit-m2-20260911`; under A2 the current HEAD carries **16** AST sites / **14** mechanism opt-ins, off by default) / maturity **complete 9 · partial 37 · placeholder 8**. 2. The main-line conclusion is a negat

HEAD ## References
  LEAD: [1] Hsu, T.-C. C., Whelan, P., Gandrup, J., Armitage, C. J., Cordingley, L., & McBeth, J. (2024). Personalized interventions for behaviour change: A scoping review of just-in-time adaptive interventions. *British Journal of Health Psychology*, 30, e12766. DOI: 10.1111/bjhp.12766.