
> **Submission positioning withdrawn (review §5.4, 2026-09-29).** This manuscript is **no longer established as a journal paper**, and the two target journals *Journal of Systems and Software* and *Empirical Software Engineering* (plus the fallback *Information and Software Technology*) are **withdrawn**.
>
> **Handled along Route B of §6.2 of the first review**: the parts of this manuscript that remain valid — **the internal static audit sealed at the audit-time tag (`audit-m2-20260911`)**, and **the diagnosis that four fields of the seven-tuple are unimplemented** — are reorganised into **a dissertation governance chapter + a short experience report** (workshop or short paper, 8–10 pages). Route A's A2·A3·A4 outputs **are not accepted as results** (see §8.2); Route A is not to be revisited until effect producers carrying real mechanism logic are ready **and** the blinded procedure of two human coders has been registered before coding begins, at which point the coders' identities must be reported to the supervisor first.

## Abstract

When a learning system registers dozens of behavioural intervention mechanisms at once, the intuitive expectation is that they will collide at run time, cancel each other out, and therefore require arbitration and budget governance. This paper tests that intuition head-on, and the results run against it — but the accounting must come first: the platform audited here has **54 registered** semantically de-duplicated gamified intervention mechanisms (LF-M01…LF-M54, registry fingerprint `ee1a49be5732`), of which **only 2 construct an intervention effect** (LF-M44 / LF-M52; sealed baseline tag `audit-m2-20260911`; under A2 the current HEAD carries **16** AST sites / **14** mechanism opt-ins, off by default), with maturity **complete 9 · partial 37 · placeholder 8**. These three figures must always be reported together, because "on the register" and "able to produce a run-time effect" are not the same thing. We report four measured findings. First, mapped onto the intervention seven-tuple defined here, **42 of 54 (77.8%) cannot be assigned a direction field**, and four fields (`target_construct`, `channel`, `side_effect`, `precedence`) **do not exist anywhere in our own code**; this triggers the threshold we set in advance (> 20%). **We explicitly classify this as a diagnosis of implementation completeness, not as a discovery triggered by a falsification condition**: designer and audited party are the same party, so the figure measures how much of the schema we wrote down has been implemented, not a general property of the world. Second, of the three conflict types, type I has 27 static latent pairs (all from the 9 × 3 direction table) and 2 document-anchored same-construct pairs, yet only **one pair is detectable at run time** (LF-M44 vs LF-M52), and it is dissolved at the "health override" layer rather than at the "direction cancellation" layer we designed — the latter is **dead code** under the current set of intervention-effect producers. Third, type II (renamed **budget contention**) has **0 run-time contention pairs**, because the secondary mechanisms write only evaluation records, construct no intervention effect, never enter the arbitrator, and consume no budget. For the second and third findings the material **cannot distinguish "conflicts are rare" from "there simply is no run time in which conflicts could occur"** (real user logs are 0), so we assert only one independently provable engineering proposition: **the existence of an arbitration layer does not entail the reachability of an arbitration path**. Fourth, cross-system replication (Ludilearn, 6 mechanisms; Level Up XP, 11) shows that under the strict caliber **both external systems coded in this paper exhibit 0 type-I conflicts**; they avoid conflict *by construction* — mutually exclusive activation, rate windows — rather than resolving it. The main-line conclusion is a negative result, and it is **descriptive**: conflict is exposed only by the multi-intervention-coexistence architecture, and the external systems we examined evade conflict through structural design. Our cross-system sample is n = 2, single-coded, with no inter-rater reliability, so this must **not** be generalized to "most similar systems." We also report the failures of the audit method itself (insufficient schema coverage, ledger initially unimplemented, external coding without reliability, audit-time asset metrics not reproducible from a commit and therefore sealed by tag) and derive design requirements from the audit. (This paper proceeds along Route A: A1 / A2 / A3 implemented; A4 pending.)

**Keywords**: gamified intervention; conflict audit; empirical software audit; intervention registry; budget contention; negative results

## Author's Declarations

**First, this paper is "an internal static audit and its limits," not a general finding about similar systems.** Three inferences **exceed our material and must not be written**: (1) Do not call the 77.8% unclassifiable proportion a "discovery triggered by a falsification condition" — its cause is that four fields of the seven-tuple we ourselves designed do not exist in our own code, i.e. a diagnosis of implementation completeness; (2) Do not infer "multi-intervention systems rarely conflict" from "1 run-time conflict pair, 0 budget-contention pairs" — we have no real user logs (limitation ⑧); (3) Do not infer "most similar systems avoid conflict by structural design" from 2 external systems (both Moodle/PHP plug-ins, single coder, no reliability).

**Second, wherever a mechanism scale appears, the three figures must be stated together**: registered **54** / effect-producing **2** (sealed tag `audit-m2-20260911`; under A2 HEAD carries 16 AST sites / 14 opt-ins, off by default) / maturity **complete 9 · partial 37 · placeholder 8**. A bare "54" reads a registration scale as a capability scale.

**Third, all numbers are taken only from script products under `results/m2/`, and all code anchors from the sealed tree `audit-m2-20260911`.** The audited repository has moved on (current HEAD far past `8a328430`); asset line-count metrics have drifted, which affects no audit conclusion. Code-anchor evidence (registry, direction table, effect-producer locations) is sealed by tag and verified item by item (7/7 PASS).

**Fourth, this paper does not claim a verified method.** The contribution is the audit itself, not a method.

## 1 Introduction

### 1.1 An engineering fact and an unnamed problem

Gamified learning systems have evolved over fifteen years from the "badge–points–leaderboard" trio to "adaptive gamification," whose core claim is that different users prefer different game elements and the system should select elements dynamically from the user profile. Adaptive gamification thus answers "who gets which element." What it does not answer is the question this paper poses: when dozens of intervention mechanisms are registered simultaneously, do they collide at run time, cancel each other out, and therefore require arbitration and budget governance? That intuition circulates widely in design documents, but it had not been formalized as an auditable criterion, nor checked against code.

### 1.2 The audited object and the three-part accounting

The audited object is a real, deployed, publicly released K12 adaptive learning platform. Its salient feature is scale, but the scale must be given under the **three-part accounting**: a unified mechanism registry **registers 54** semantically de-duplicated gamified intervention mechanisms (LF-M01…LF-M54, contiguous numbering, fingerprint `ee1a49be5732`); of these **only 2 construct an intervention effect** (LF-M44 @ `deep_addiction_engine.py:296`, LF-M52 @ `learning_orchestrator.py:986`; sealed tag `audit-m2-20260911`); maturity is **complete 9 · partial 37 · placeholder 8**. Under Route A's A2 the current HEAD carries **16** AST construction sites / **14** mechanism opt-ins, off by default. Section 4 further exposes an earlier inflation from 76 to 54; a bare "54" would itself become a second layer of inflation. Reporting all three figures together is this paper's self-defence against an inflated narrative.

### 1.3 Contributions and main findings

This paper is a **static audit + cross-system replication**. It proposes no new detection algorithm and claims no mechanism is effective for learning. Four contributions, each with a measured number: (i) the intervention seven-tuple and a conflict criterion whose unclassifiable proportion was measured at 77.8%, triggering the pre-set > 20% threshold and yielding the conclusion that schema granularity does not match implementation granularity — qualified as a **diagnosis of implementation completeness**; (ii) measured convergence of three conflict types (27 static → 1 run-time; 0; 7/8 letters) plus the dead-code finding; (iii) a cross-system replication (E2) on two external systems, direction reversed; (iv) three design requirements derived from the audit, and a ledger downgraded from "evaluated contribution" to "design requirement."

### 1.4 Structure and reproducibility

§2 reviews related work; §3 gives the formalization and conflict detection; §4 the mechanism census, taxonomy conflict and numeric drift; §5 the ledger as design requirement with A3 synthetic-session distributions; §6 cross-system replication; §7 predictions versus measurements; §8 discussion; §9 the twelve honest gaps; §10 conclusion. All numbers come from `results/m2/`; code anchors are sealed at tag `audit-m2-20260911`.

## 2 Related Work

Four threads are relevant, and in each the gap is the same: interaction among simultaneously present mechanisms is not the unit of analysis. **Adaptive gamification and user typologies.** Sailer et al. (2017) propose the HEXAD typology (achievers, free spirits, socializers, philanthropists, players, disruptors); a later meta-analysis (Sailer et al., 2020) tests type–element correspondence. This thread answers "who gets what element," not what happens when several interventions are active together. **Behavioural-change science and JITAIs.** Hsu et al. (2024), in a 62-study scoping review, note that most JITAIs rely on self-report adaptation with insufficient transparency and heterogeneous validity; the theoretical integration of behaviour change acknowledges that when several techniques target the same construct their combination need not be additive, but stops at acknowledging it. **Multi-objective identification and budget-constrained online learning.** Pareto-set identification for multi-objective bandits (Kone et al., 2024; 2025) gives algorithms and information-theoretic lower bounds under fixed budget / fixed confidence, the latter handling linear feasibility constraints; MORL policy composition (Kim et al., 2025) covers generalized p-mean preferences. This literature is mature on *allocation*, but presupposes that competing arms actually reach the allocator — precisely the presupposition this audit falsifies (§3.4). **Gamification effect baselines and the dark side.** Dai et al. (2025) (182 effect sizes / 37 RCTs, d = 0.566) and Slamet and Meng (2025) (collaborative learning, d ≈ 0.875) establish the average gamification effect, but their comparison unit is "packaged gamification vs. no gamification," which exposes exactly the gap in single-mechanism identification and inter-mechanism interaction that this paper addresses.

## 3 Audit Object and Method: Formalization of Intervention and Conflict Detection

### 3.1 The intervention seven-tuple and the pre-fixed criterion

This paper defines the intervention unit as a seven-tuple **I = ⟨tr, c, δ, ch, b, se, pr⟩**: tr is the trigger condition (a predicate on a decision snapshot); c ∈ C the acted-upon construct, with C = {engagement, persistence, self-efficacy, social connection, online time, health compliance}; δ ∈ {+1, −1} the action direction (promote / suppress); ch the presentation channel; b the intervention-budget consumption; se the known side effects; pr the compliance priority (integer, larger = higher). C is derived from three theories — the gamification-mechanism taxonomy (MDA and game-element classification), self-determination theory (autonomy / competence / relatedness), and the behaviour-change-technique taxonomy (Fogg behaviour model, COM-B's capability / opportunity / motivation). δ inherits the promote/suppress semantics of behaviour-change techniques; pr is set by compliance requirements (minor protection), not engineering preference.

**The criterion was fixed before the audit ran**, to prevent "being unclassifiable is itself a discovery" from becoming self-exemption: below 5% unclassifiable, the construct set already covers enough and "schema granularity is inappropriate" does not hold; above 20%, the schema's granularity itself needs re-design.

### 3.2 Mapping coverage: measured 77.8%, a diagnosis of implementation completeness

**Field availability.** Of the seven fields, only `trigger` (implemented as `stage`) is fully available across all 54 mechanisms (54/54), and `direction` is available on 12 (12/54). The other four — `target_construct`, `channel`, `side_effect`, `precedence` — **do not exist in the code**: neither the registry nor the orchestrator defines them, so any value can only be reverse-inferred from document semantics by the analyst, not read from the implementation.

**Unclassifiable proportion.** Under the caliber "can a `direction` field be assigned," unclassifiable mechanisms number **42/54 = 77.78%**; the ID list is in `4_unclassifiable.no_direction_ids` of `results/m2/m2_conflict_analysis.json`.

**Qualitative classification.** The measured value far exceeds the pre-set > 20% threshold, so the conclusion is **not** "schema coverage is acceptable" but: **the granularity of this seven-tuple does not match the implementation's** — a formalization that lists acted-upon construct, presentation channel, side effect and compliance priority as required fields, when four of them do not exist at all, describes a design intention rather than an auditable system. This conclusion is self-negating and we do not soften it. **But self-negation is not a discovery.** The cause is that four fields of the schema we ourselves designed are not implemented in our own code — designer and audited party are the same party, so the number measures "how much of the written schema has landed." A "falsification condition" presupposes a falsifiable proposition about the external world; what is falsified here is only the internal-consistency hypothesis that the schema we wrote and the implementation we wrote match each other. We therefore **withdraw** the earlier phrasing "triggers this paper's self-set falsification condition" and adopt "self-set threshold triggered," with the qualitative classification **diagnosis of implementation completeness**.

**A contrasting caliber that must also be reported.** Asking instead for the proportion that "cannot be placed into the governance document's A–H eight categories" yields **0%**: all 54 entries carry an A–H classification. The two numbers measure different things — "has an affiliation" versus "field-level availability." We adopt the latter, because only it answers "can the system be automatically audited."

### 3.3 Detection of three conflict types

**Type I · effect-direction conflict.** Condition: c_i = c_j ∧ δ_i = −δ_j ∧ tr_i ∧ tr_j can be simultaneously true. Three sources are cross-checked: the direction table of `mechanism_arbitrator.py`, the budget policy, and the real intervention-effect producers in `learning_orchestrator.py`.

*Direction-table coverage*: `_DIRECTION` registers only **12/54** mechanisms (`mechanism_arbitrator.py:102-107`) — approach 9 (`LF-M07, M08, M10, M13, M25, M26, M33, M35, M44`), withdraw 3 (`LF-M51, M52, M53`) — so static latent pairs (upper bound) are 9 × 3 = **27**. *Document-anchored same-construct pairs*: on the construct "online time," 2 substantive pairs — LF-M44 (fear of missing out, approach) ↔ LF-M51 (forced rest, withdraw), and LF-M44 ↔ LF-M52 (minor protection, withdraw). *Actually detectable at run time*: **1 pair** (LF-M44 vs LF-M52), because the whole repository constructs an intervention effect in only two places.

**Table 1. The two run-time intervention-effect producers**

| Mechanism | Construction site | Run-time attributes |
|---|---|---|
| LF-M44 | `deep_addiction_engine.py:296` | `user_visible=True, health_critical=False, cost=1.5, priority=50` |
| LF-M52 | `learning_orchestrator.py:986` | `user_visible=False, health_critical=True, cost=0.0, priority=100` |

The gap between the static 27 and the run-time 1 is the most important measured fact of this type: registering opposed directions does not mean they will meet at run time.

**Type II · budget contention.** The original name "channel contention" does not match the implementation — there is no measure of channel load; what exists is `BudgetPolicy` (`mechanism_arbitrator.py:44-53`) with `max_per_session = 3`, `max_per_day = 6`, `max_cost_per_session = 4.0`, `min_interval_sec = 300`. We therefore **rename type II "budget contention."** Measured: run-time contention pairs = **0**. The only non-health candidate visible at run time is LF-M44 alone; LF-M52 bypasses the budget because `health_critical=True` (`mechanism_arbitrator.py:380-382`). The structural cause: the 28 secondary mechanisms at step 13 produce only **evaluation records** (written to `decision_snapshot["mechanism_evaluations"]`, `learning_orchestrator.py:1105`), constructing no intervention effect, entering no arbitrator, consuming no budget. Hence the judgement **non-zero ≠ detectable**: even with 3 suppress-direction mechanisms registered and session/daily caps prescribed, budget contention has **no detectable carrier** while the producer set keeps them out of the arbitrator. We propose that distinguishing conflict-in-design from conflict-detectable become a routine reporting item, since conflating them systematically overestimates governance needs.

**Type III · schema-classification conflict.** This examines information-modelling-level conflict: the same mechanism inconsistently affiliated under two classification systems — the governance document's eight letters A–H versus the registry `CATEGORIES`'s five values (retention / motivation / selfreg / cognition / health). Measured: **7 of 8 letters span ≥ 2 code-side categories**, H (health guardrail and ethics) being the only single mapping.

**Table 2. Governance letters and the code-side categories they fall into**

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

The two taxonomies are **not refinements of one another**: A in the governance document and `retention` in the registry is not a naming difference but a real classification conflict at the information-modelling level.

### 3.4 The layer-2 direction cancellation is dead code

The system designs two dissolution layers: **layer 1** health override (`mechanism_arbitrator.py:157-170`) and **layer 2** direction cancellation, which compares directions only among interventions with `user_visible = True` (`mechanism_arbitrator.py:344-349`). Of the only two effect producers, LF-M44 is `user_visible=True, health_critical=False` and LF-M52 is `user_visible=False, health_critical=True`. Therefore LF-M52 **never enters the direction comparison** and layer 2 **is not triggered**; their semantic opposition is actually dissolved by the **layer-1 health override**, which discards all approach-direction interventions. **The structural opposition this system implements is the semantics of "health veto," not "direction cancellation"; layer 2 is dead code under the current set of effect producers.** This judgement depends on no subjective coding — only two `Effect` construction points and one comparison scope — and any reader can re-check it with two `grep`s. It is this audit's "hardest" engineering finding: one layer of an apparently complete two-layer arbitration architecture has never been reached. It is **not** an accusation that the system is defective; it is a reminder that **the existence of an arbitration layer does not entail the reachability of an arbitration path**.

### 3.5 Audit conclusion on the compliance-preemption property S1

> **Property S1 (compliance preemption).** If at state s an active compliance constraint k exists, then any intervention i with pr_i < pr_k must be silent at s, i.e. x_i(s) = 0; conversely x_k(s) is unaffected by any lower-priority intervention.

Verdict: "**satisfied at the implementation level, but in a way stronger and cruder than the statement**." LF-M52 is registered `health_critical=True`, `priority=100`; the health-veto layer unconditionally passes it and discards all approach-direction interventions, which is effectively equivalent to S1. But the system does not express the constraint as machine-checkable temporal logic and leaves no checkable arbitration trace, so S1 is currently **a system contract implied by the implementation but neither expressed nor verified by the system itself**. Because layer 2 is dead code and no trace is persisted, S1 can neither be effectively refuted nor has independent verification evidence; we therefore downgrade S1 from "evaluated methodological contribution" to "design requirement derived from the audit."

## 4 Mechanism Census, Taxonomy Conflict, and Numeric Drift

### 4.1 Two taxonomies that cannot corroborate each other

A fact extremely easy to miswrite must be clarified first: the governance document organizes mechanisms into A–H **eight categories**; the code-side registry's `CATEGORIES` constant has only **five** values. No place classifies mechanisms by A–H in code — the eight categories can only be parsed from Markdown. Both distributions sum to 54, **but they cannot corroborate each other** (the A–H taxonomy is a governance-document artefact and must not be attributed to the code-side registry).

**Table 3. Governance document's eight categories and mechanism counts**

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

### 4.2 Landing-strength stratification

**Table 4. Landing-strength stratification of 54 mechanisms**

| Stratum | Measured | Caliber basis |
|---|---:|---|
| `landed` (implementation reference reachable, or wired/gated via orchestrator) | **54** | `scan_mechanism_landing.py:177` |
| `orphan` | **0** | — |
| Entered `PIPELINE_MECHANISM_MAP` step mapping | **34** | step 6(1)+8(2)+9(2)+12(1)+13(28) |
| Source-code-text reference only (not in step mapping) | **20** | 54 − 34 |
| Of which `is_enabled("<key>")` independently gated and truly called | **31** | 31 literals in `learning_orchestrator.py` |
| 3 health guardrails exempt from gating by design | 3 | `lai_downgrade` / `forced_rest` / `minor_protection` |

All 54 are "landed" in the weak sense and none is orphaned, yet far fewer truly participate in arbitration — the quantitative form of the §3.3.2 gap.

### 4.3 Four-dimension mechanism census

**Table 5. Four-dimension mechanism census**

| Dimension | Distribution |
|---|---|
| stage (trigger stage) | during 20 / pre 14 / ambient 13 / post 7 |
| maturity | complete 9 / partial 37 / placeholder 8 |
| disposition | R 32 / K 15 / M 6 / D 1 |
| direction | unassigned 42 / approach 9 / withdraw 3 |

### 4.4 Numeric drift

**Table 6. Asset and counting metrics: registration baseline vs. measured**

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

These values drifted relative to the registration baseline and, after Route A, relative to the audit time as well; per limitation ⑪ they **are not part of the audit conclusions** and only illustrate that drift exists between the registration baseline and implementation status.

## 5 Design Requirements Derived from the Audit: An Auditable Intervention Ledger

### 5.1 Ledger schema and implementation status

The auditable intervention ledger was originally listed as an "evaluated contribution"; the audit **downgrades it to a design requirement derived from the audit**. Before Route A the repository had no ledger implementation: no `budget_consumed` field, no `preempted_by` field, no ledger module, and `ArbitrationTrace` existed only in memory or within a single call (`mechanism_arbitrator.py:57-69`), not persisted. **Route A A1 (2026-09-22) landed it**: `ArbitrationTrace` gained `budget_consumed` / `preempted_by` / `arbitration_decision`, filled by `MechanismArbitrator.arbitrate`; a new `app/services/arbitration_ledger.py` provides `LedgerTraceSink` (synchronous SQLite append-only, opt-in via `LEARN2_LEDGER_ENABLED=1`). **Important boundary**: A1 adds observability only and does **not change the number of effect producers** (still 2 at that point), so run-time conflicts still could not occur and the three checks yielded 0 rows. The proposed schema (per record: `mechanism_id`, `intervention_instance_id`, `session_id`, `decision_snapshot`, `budget_consumed`, `arbitration_decision`, `preempted_by`, `timestamp`) can thus be given as implemented-but-unexercised; the existing `learning_events` table already freezes `decision_snapshot` and can serve as the persistence access point.

### 5.2 Three classes of consistency checks and the A3 distribution

**Table 7. Three ledger violation types and checks**

| Violation type | Definition | Planned check | This-round status |
|---|---|---|---|
| Budget overspend | Σ `budget_consumed` within a session > B | aggregate and compare by session | **Implemented and runnable; A3 synthetic sessions have produced a distribution** |
| Executed although preempted | `preempted_by` non-empty but `arbitration_decision = executed` | record-level assertion | **Implemented and runnable; measured violation rate = 0 (safety invariant holds)** |
| Decision with no record | intervention effect appears but no corresponding ledger record | reconcile event stream with ledger | **Implemented and runnable; the ledger is the record source, always 0** |

A3 (2026-09-22) drives the real `MechanismArbitrator` (with `MemoryBudgetStore` + in-memory trace sink) over **10,000 sessions × 40 steps** (400,000 steps) with the Route A ≥ 14-producer set, using "only the 2 existing producers" as the reference baseline (`results/m2/a3_synthetic_sessions.json`).

**Table 8. Run-time conflict distribution: before vs. after Route A producer expansion**

| Metric | Before (2-producer baseline) | After (≥14 producers, opt-in) |
|---|---:|---:|
| Run-time conflict frequency (note: this field also counts same-direction same-type de-duplication, so it is not purely direction opposition) | 0.000 | 0.633 (**not accepted as a result**) |
| Contention rate (step ratio discarded by health-veto or conflict-resolution layer) | 0.299 | 0.971 |
| Budget-exhaustion rate (session ratio with ≥1 step discarded by budget) | 0.433 | 1.000 |
| Preemption-violation rate (step ratio with `preempted_by ∩ delivered ≠ ∅`) | 0.000 | 0.000 |

**This distribution is not accepted as a result (review §5.3 and §5.4, 2026-09-29).** The figures in the table above are retained as a record only, for four reasons: (i) the script `a3_synthetic_sessions.py` states in its own header that it does not modify production code and directly constructs `MechanismArbitrator`, i.e. it does **not** run through the real orchestrator, and it has no learner model; (ii) the conflict-frequency field `dropped_by_conflict` also counts **same-type / same-direction de-duplication**, so 0.633 mixes in discards that are not direction opposition, which makes the earlier label Layer-2 direction-opposition discard ratio inaccurate; (iii) the metric definitions were **changed three times after the results were seen** (the first version pinned conflict frequency at 100% and the activation method was then changed; after preemption violations appeared the definition was changed to `preempted_by ∩ delivered`; after budget exhaustion stayed at 0 the definition was changed), and A3 had **no prediction written down in advance**; (iv) the A1 ledger database has **0 rows**, A3 never used the ledger, and there is no record of it running end-to-end on the real path.

**Former key interpretation (no longer used; retained for the record only)**: before the change conflict frequency = 0, consistent with the §3 audit conclusion on the natural 2-producer system; after the change it is 0.633, which **makes the previously indistinguishable dichotomy quantifiably distinguishable** once ≥ 14 producers are enabled (Δ = 0.633). The preemption-violation rate of 0 under both modes validates the safety invariant "a preempted mechanism never enters the delivery set." These are **counterfactual (opt-in, not deployed)** distributions characterizing how the same arbitrator would behave under the Route A producer set; they **do not alter** the chapter-3 conclusion on the natural system, whose measured carrier remains the 2 producers at the sealed tag. The only runnable substitutes unrelated to the ledger are table-creation portability (SQLite 13/13 statements succeed, 6/6 tables built) and state persistence (9/9 PASS); `impl_ref` integrity is 54/54 OK.

### 5.3 Replacing a distributed ledger with Merkle anchoring

As a **design argument rather than a measured conclusion**: the ledger's tamper-resistance requirement can be met by a Merkle tree plus periodic public anchoring, at roughly two orders of magnitude lower cost and complexity than a distributed ledger and without institutional authorization. Merkle anchoring remains not-yet-implemented, but A1 has already delivered append-only persistence, so anchoring is an optional enhancement on top of it.

## 6 Cross-System Replication (E2)

### 6.1 Objects and coding method

**System A · Ludilearn**: `https://github.com/DigiDago/moodle-format_ludilearn`, commit `eb69582fb4def6e4cbb26c2146ceb90435951c53`, GPL-3.0, PHP; part of the LudiMoodle+ project (French ANR e-FRAN / France 2030) and **explicitly sold on "adaptive gamification"** with a Hexad-profile adaptation algorithm. **System B · Level Up XP**: a Moodle plug-in. Coding is file-by-file, each coding carrying a `file:line` anchor, single coder, **no inter-rater reliability** (limitation ③); the relaxed upper bound is always reported alongside to expose criterion sensitivity.

**Table 9. Ludilearn conflict detection (6 mechanisms)**

| Conflict type | Detected | Note |
|---|---:|---|
| Type I (strict: same target and opposite direction) | **0** | `score` etc. are approach; `timer` is withdraw (timeout penalty, `timer.php:46`, `DEFAULT_PENALTIES=20`), but targets differ (engagement/performance vs. time/rhythm) |
| Type I (relaxed upper bound: any approach × withdraw) | 5 | holds only when target matching is ignored |
| Type II (budget contention) | no budget concept | 4 mechanisms (badge/progress/ranking/score) write the same user state, but there is no rate cap |
| Type III (objective conflict) | **0** | no compliance/health-guardrail mechanism |

**Table 10. Level Up XP conflict detection (11 mechanisms)**

| Conflict type | Detected | Note |
|---|---:|---|
| Type I (strict) | **0** | no same-target opposite-direction pair |
| Type I (relaxed upper bound) | 18 | 2 withdraw (`rule_limits`, `cheatguard`) × 9 approach |
| Type II (budget contention) | **exists, with explicit cap** | 5 mechanisms (xp_points/levels/leaderboard/rank/badge) write the same user state; `classes/local/ruletype/limit_spec.php` provides **H/D/W/M four-tier rate windows** plus a `timesallowed` cap |
| Type III (objective conflict) | **1** | `cheatguard` (compliance, anti-cheat interception) against all approach mechanisms |

**Table 11. Cross-system comparison of conflict structure**

| | This system | Ludilearn | Level Up XP |
|---|---|---|---|
| Mechanism count | **Registered 54 / effect-producing 2** (sealed tag `audit-m2-20260911`; under A2 HEAD carries **16** AST sites / **14** opt-ins, off by default) **/ maturity 9·37·8** | 6 | 11 |
| Type I (strict) | 1 (and dissolved by health veto) | 0 | 0 |
| Type I (relaxed upper bound) | 27 (static latent pairs) | 5 | 18 |
| Type II | 0 (no carrier) | no budget concept | explicit rate cap exists |
| Type III | 7/8 letters span categories | 0 | 1 |
| Conflict-handling method | layered arbitration (layer 1 reached, layer 2 dead code) | mutually exclusive activation, impossible by construction | rate windows, capped in advance |

### 6.2 Cross-system conclusion: conflict is structurally avoided, not resolved

Under the strict caliber both external systems have **0** type-I conflicts, but for different reasons. Ludilearn's conflict is **non-existent by construction**: `attribution_game_element()` first deletes other elements' attributions under the same section before assignment (`classes/local/gamification/manager.php:126-1xx`), so two elements never co-activate. Level Up XP does not forbid co-activation but **caps it in advance** through H/D/W/M rate windows and `timesallowed`; its single type-III conflict is `cheatguard` against all approach mechanisms. Neither system resolves conflict at run time — both make it unreachable by design. Compared with this system's layered arbitration (layer 1 reached, layer 2 dead code), the conclusion is: **conflict is structurally avoided, not resolved.** This is an n = 2 description of two homologous Moodle/PHP plug-ins, not a distribution; we therefore always write "**the 2 external systems coded in this paper**," never "most similar systems."

## 7 Prediction-versus-Measurement Comparison

**Table 12. Predictions fixed before the audit versus measured results**

| No. | Prediction before audit | Measured | Verdict |
|---|---|---|---|
| P1 | After mapping 54 mechanisms to the seven-tuple, **10–20%** expected unclassifiable; >20% means schema granularity must be re-designed | **77.8% (42/54)**; four fields **do not exist in our own code** | **Prediction overturned → self-set threshold triggered**; conclusion: schema granularity does not match implementation granularity. **Qualitative correction**: a **diagnosis of implementation completeness** (designer and audited party are the same), not a general discovery; the "falsification-condition triggered" phrasing is withdrawn |
| P2 | Three conflict types universal in this system; type I contains at least "FOMO × minor protection × rest reminder" | Type I run-time **only 1 pair** (M44–M52); type II **0 pairs**; type III 7/8 letters spanning categories | **Prediction overturned** (conflicts not universal) |
| P3 | Cross-system replication upgrades the single-point observation into a class finding: external systems would also show non-zero conflict | Ludilearn type I/III both **0**; Level Up XP type I **0**, type III **1** | **Prediction overturned** (direction reversed: conflicts rare) |
| P4 | Compliance-preemption property S1 expressible in temporal logic and **model-checkable** on the orchestrator state machine | S1 satisfied at the implementation level but **not expressed by the system itself**, no arbitration trace persisted, so neither effectively refutable nor independently verified | **Not tested** (downgraded to design requirement) |
| P5 | Ledger three violations reliably detectable (detection rate > 0.95, false-positive rate < 0.05) | Originally **could not execute**: `budget_consumed`/`preempted_by`/ledger had zero matches; after A1/A3 the checks are runnable and A3 produced a distribution, but real run-time logs are still absent | **Not tested** (original hypothesis deleted; partially remedied by Route A) |

Three predictions (P1–P3) were overturned, all in directions **opposite** to the pre-audit expectation. P1 is the one that triggered our self-set > 20% threshold, but its qualitative classification is a diagnosis of implementation completeness, so its "overturning" constrains our method, not the world.

## 8 Discussion

### 8.1 Self-assessment: "taxonomy or method"?

The original design prepared three conditions to cross the verdict "this is merely a taxonomy": machine-checkability of S1, the applicability precondition of the allocation model's regret analysis, and cross-project replication E2. Measured: S1 is implied by the implementation but not expressed (§3.5); the allocation model's precondition has no real carrier because the **run-time contention count is 0** (§3.3); and E2 is completed but reversed in direction (§6.2). Therefore **this paper does not claim to have proposed a verified method**; the contribution is the audit itself — clarifying a problem assumed to exist but never checked into "in this system and two external systems it almost never occurs, and the reason is structural avoidance." In empirical software engineering this is of no small value: it replaces a widely circulating design intuition ("more mechanisms, more conflict, more need for arbitration and budget") with an empirical fact anchored in code, and gives the condition under which that intuition holds — two or more intervention-effect producers competing at the same decision point.

### 8.2 Route A / Route B
**Decision (review §5.4, 2026-09-29): Route B.** Route A's A1/A2/A3 are implemented, but **Route A's A2·A3·A4 outputs are not accepted as results**; this paper therefore proceeds along Route B — the internal static audit sealed at tag `audit-m2-20260911` and the diagnosis that four fields of the seven-tuple are unimplemented are reorganised into a dissertation governance chapter + a short experience report, **and no journal submission is made**. Route A is not revisited until effect producers carrying real mechanism logic are ready and the blinded procedure of two human coders has been registered before coding begins, at which point the coders' identities must be reported to the supervisor first.


The reviewer's judgement: the existing material supports a limited internal static audit but **not** an empirical-software-engineering journal paper, so a route had to be chosen rather than patched. **Route A (empirical strengthening)**: A1 ledger landing (implemented 2026-09-22); A2 raising effect producers from 2 to ≥ 14 (implemented 2026-09-22; `route_a_producers.py`, `verify_counts` AST sites 2 → **16**, 14 distinct mechanisms, off by default via `LEARN2_A2_PRODUCERS=1`, not affecting the 936 existing tests); A3 synthetic sessions (implemented 2026-09-22, §5.2); A4 external ≥ 4 systems + two coders + Cohen's κ (**still pending**, plan and CODEBOOK ready, `a4_coderA.csv` / `a4_coderB_template.csv`). *Cost*: A2 changes the audited system itself — the audit object becomes "the system modified to pass the audit" — so the 2 pre-modification and ≥ 14 post-modification producers must be reported **side by side**, not substituted. **Route B (reduce)**: split into thesis chapter 4 (governance chain) + a short experience report (8–10 pages), which is a suitable vehicle for "we audited our own system by our own schema and found three fields unimplemented and one arbitration layer never reached"; its core value ("first count the `Effect` construction points, then talk about arbitration") has been absorbed into A2. **Decision (2026-09-22): Route A first**; Route B's form is a milestone output. The common precondition of both routes: the three-part caliber must always appear together.

### 8.3 Teaching and practical implications

Three implications, all directly actionable. First, **count the producers first, then talk about arbitration**: before claiming a system has conflict governance, `grep` the number of intervention-effect construction points; if only one producer exists at the same decision point, the "conflict" retrieved exists only in document semantics. Second, **include taxonomy alignment in design review**: if the governance document's classification and the run-time registry's classification are not a refinement relationship (we measured 7/8 governance letters spanning ≥ 2 registry categories), any statistic relying on a single encoding will be distorted. Third, **make constraints expressible by the system itself**: the health veto is currently a contract implied by the implementation but uncheckable by the system; writing it as a machine-checkable assertion and persisting the arbitration trace is the necessary step from "design convention" to "verifiable system property."

## 9 Honest Gap List (Limitations)

Twelve gaps, listed without merging or weakening. **①** MySQL table creation not measured (no `sqlglot`, no MySQL server); only SQLite results may be written: 13/13 statements succeed, 6/6 tables built (PASS). **②** Cross-system sample small and homologous: only 2 external systems, both Moodle/PHP. **③** External coding is single coding with **no inter-rater reliability** computed; neither external system has a `target_construct` dictionary, so strict type I depends heavily on the coding criterion — hence the relaxed upper bounds (5 and 18) are always reported. The A4 scaffold (`a4_coderA.csv`, `a4_coderB_template.csv`) is prepared and a pipeline sanity self-check returns κ = 1.000, but **that only proves the pipeline is usable, not real reliability**; real κ remains PENDING and this paper reports no reliability number. **④** No human-subjects experiment: no intervention-load perception, harassment, or usability results. **⑤** No claim that any mechanism is effective for learning; statements are limited to implementation-level wiring, direction, and budget attributes. **⑥** Ledger implemented and A3 has produced a distribution, but **real run-time logs are still lacking**, so run-time-log statistics are 0 rows; Merkle anchoring remains an unimplemented design argument. **⑦** Learning-addiction measurement unvalidated: the Learning Addiction Index (time 30% / motivation 25% / control 25% / cognitive 10% / function 10%) is **self-authored, with no reliability/validity validation, no norms, no clinical cut-off**; no clinical or diagnostic inference may be drawn. **⑧** Static audit cannot replace run-time observation: the studied system has no real-user logs, so real conflict frequency and budget-consumption distributions are unanswerable. **⑨** Taxonomy completeness not proven — a common limitation of formalization work. **⑩ (topmost)** **The material cannot distinguish "conflicts are rare" from "no run time in which conflict can occur"**: only 2 effect producers and 0 real user logs make "type-II run-time contention = 0" and the alternative explanation indistinguishable; all generalized formulations of the form "multi-intervention systems rarely conflict" are therefore **withdrawn**, and the conclusion narrowed to a descriptive one. **⑪** Audit-time asset metrics not reproducible by commit (partially remedied): code-anchor evidence is sealed at tag `audit-m2-20260911` and verified 7/7 PASS by `results/m2/verify_m2_anchors.py`; asset-metric values remain unrecoverable and are declared **not part of the audit conclusions**. **⑫** Route A selected; A1/A2/A3 implemented, A4 pending.

## 10 Conclusion

This paper rewrites a widely assumed design intuition — "a system running dozens of intervention mechanisms simultaneously must inevitably experience intervention conflict and therefore needs arbitration and budget governance" — into a checkable empirical proposition, and gives measured evidence against it. **Headline caliber, three-part and none dispensable: registered 54 / effect-producing 2** (sealed tag `audit-m2-20260911`; under A2 HEAD carries 16 AST sites / 14 opt-ins, off by default) **/ maturity complete 9 · partial 37 · placeholder 8.** Under this caliber, the three core numbers are: unclassifiable proportion **77.8% (42/54)** — a **diagnosis of implementation completeness**, not a discovery; type-I conflict converging from 27 static latent pairs to **1** run-time pair, handled by the layer-1 health veto rather than the layer-2 direction cancellation, the latter being **dead code**; and type-II budget contention's run-time count of **0**, because secondary mechanisms write only evaluation records and enter no arbitrator. Cross-system replication shows both external systems coded here have 0 strict type-I conflicts, avoiding conflict **by construction**.

The main-line conclusion is a negative result and is **descriptive**: the multi-intervention-coexistence architecture is the scarce condition that exposes intervention conflict, not a universal predicament of this class of systems — but our material cannot distinguish "conflicts are rare" from "there is simply no run time in which conflict can occur." Hence the single independently provable engineering proposition: **the existence of an arbitration layer does not entail the reachability of an arbitration path**. Three actionable design requirements follow: count intervention-effect producers before talking about arbitration; include the alignment of the two taxonomies in design review; make compliance constraints assertions checkable by the system itself and persist the arbitration trace. Route A continues: A1 ledger implemented, A2 producers 2 → 16 construction points, A3 synthetic sessions (conflict frequency 0.633 after vs. 0.000 before), A4 (≥ 4 systems, two coders, Cohen's κ) still to be executed.
