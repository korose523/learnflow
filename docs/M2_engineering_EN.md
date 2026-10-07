# Auditing Intervention Declarations Against Implementation Evidence

Zexiao Weng

## Abstract

Software that combines motivational, protective and instructional interventions needs to distinguish declared mechanisms from implementation evidence. A registry entry does not establish that an intervention produces a candidate, reaches arbitration or is presented to a user. This paper describes a read-only audit prototype that combines a seven-field intervention contract, source-symbol references and Python literal construction evidence. The tool preserves unresolved evidence rather than converting missing information into default completeness. Evaluation uses a constructed conformance benchmark and a versioned case study of LearnFlow. Across 31 predefined cases, the complete configuration returned all 26 expected diagnostics without additional diagnostics; contract-only checking returned 16. These results establish conformance to the supplied cases, not real-project defect-detection accuracy. In the frozen LearnFlow registry, 54 declarations had no explicit seven-field intervention contract, and the source scan identified two supported literal construction sites. These observations do not establish runtime reachability or intervention effectiveness. The prototype provides reproducible structural evidence for implementation review, with generalization restricted by its supported Python syntax and single-project evaluation.

Keywords: software audit; intervention systems; implementation evidence; static analysis; reproducibility

## 1 Introduction

Applications often combine multiple mechanisms: prompts, rewards, reminders and protective constraints may be described in design documents, registered in metadata and implemented across different services. These representations answer different questions. A design ledger records intent; a source registry makes a mechanism enumerable; a constructor supplies a potential intervention object. Actual exposure requires execution and delivery evidence. Treating these layers as interchangeable makes it difficult to determine what an application can meaningfully evaluate.

The practical problem is traceability between declarations and implementation evidence. An intervention description may omit its direction or delivery channel. An implementation reference may consist of a line number that moves after an edit. A source file may contain a candidate constructor inside an uncalled function. A literal object count therefore cannot serve as a count of user exposures. An audit should identify what is directly supported and retain uncertainty about what remains unresolved.

This work describes a prototype that checks intervention contracts and links them to inspectable source evidence. It does not infer psychological constructs from function names, establish execution paths or evaluate student outcomes. Its contribution is an explicit evidence model, an installable implementation and a reproducible conformance evaluation. The approach combines existing structural validation and syntax inspection techniques; no new general static-analysis algorithm or priority over existing analyzers is claimed.

The evaluation addresses three questions. RQ1 asks whether predefined contract and reference defects receive their specified diagnostics. RQ2 asks what coverage source-reference and construction checks add to contract-only validation. RQ3 asks what the tool can report about a versioned application without interpreting syntax as runtime behavior. LearnFlow is used as an internal case selected because its registry and implementation history are available. It is not a representative sample of educational platforms.

## 2 Related work and positioning

JSON Schema separates structural validation of data from the truth of the represented claims [1]. The present contract checks similarly validate field presence and selected types; an explicit side-effect list does not establish that an intervention is harmless. The implementation uses direct checks rather than a full JSON Schema engine. Python's abstract syntax tree interface supports inspection of declarations and call syntax without executing source code [2]. This is the foundation of the source adapter.

Semgrep offers configurable source-pattern rules [3], while CodeQL provides queries over code databases [4]. These tools cover substantially broader analysis tasks than the present prototype. They are relevant implementation alternatives, not evaluated competitors. A seven-field intervention rule pack could potentially be implemented in those ecosystems. The current work tests the behavior of its own minimal implementation and does not claim superior accuracy, scalability or expressiveness.

The evaluation follows a bounded engineering case-study rationale: selection, evidence and interpretive limits are made explicit, as recommended in software-engineering case-study guidance [5]. A single system can reveal a traceability problem but does not establish its prevalence across systems. Constructed cases exercise specified behavior, and the case study demonstrates application to real source. Neither substitutes for independent validation on a frozen external defect corpus.

## 3 Evidence model

An intervention declaration contains a stable identifier and a seven-field contract I=〈trigger, target_construct, direction, channel, cost, side_effect, precedence〉. Trigger, construct and channel are nonempty descriptive strings. Direction belongs to approach, withdraw or neutral. Cost is finite and nonnegative; precedence is a finite numeric value. Side effects are an explicit list of nonempty descriptions, with an empty list allowed. These checks establish syntactic completeness, not adequacy of the intervention's semantics.

Implementation evidence is represented separately. A symbol reference uses a root-relative Python file and qualified class or function name. A constructor record includes the file, line and literal mechanism identifier. A declaration may state that it expects an effect, but absence of a recognized constructor is classified as unknown evidence rather than proof of nonimplementation. Parse errors are retained in the report.

Four levels of evidence remain distinct: declaration, supported source construction, runtime arbitration and delivery, and outcome evaluation. The prototype covers the first two. It does not collect runtime traces or provide the latter two levels. A lifecycle stage is not automatically converted into a complete trigger predicate, and a local object's priority is not automatically treated as registry-wide precedence coverage.

Diagnostic severity distinguishes directly established structural inconsistencies from unresolved evidence. Invalid field values, duplicate identifiers, absent referenced files and absent supported symbols are structural errors within the scanned scope. Line-only references and missing literal production evidence remain unknown. A file-only reference lacks the symbol detail required by the adapter; it is not labelled proof that the implementation is missing.

## 4 Implementation

The package exposes a command-line interface and a Python audit function. Input consists of a JSON manifest and a source directory. Output includes findings, supported construction sites, unresolved calls, parse failures, source hashes and the declared analysis limits. Source files are parsed and are never imported, so application initialization and database code are not executed during inspection. Root-escaping references are rejected, and file symlinks escaping the source directory are not read.

The Python adapter recognizes explicit imports of Effect from modules ending in mechanism_registry, including import aliases and qualified calls through an explicitly aliased module. It requires a literal string mechanism_id. Dynamic identifiers, star imports, reflective factories and interprocedural propagation are unsupported. Rebinding a recognized alias causes conservative rejection of that evidence. Symbol collection supports module-level definitions and nested class/function definitions; it is not a complete name-resolution implementation.

The adapter deliberately records literal calls in dead branches. This demonstrates a boundary: a supported construction site proves only that the syntax exists. The output names this evidence level explicitly. A caller must not interpret a clean report as execution coverage, safety certification or confirmation of learning benefit.

The LearnFlow adapter extracts the literal registry using ast.literal_eval without importing application code. It analyzes the frozen audit revision and the current services tree separately. It does not insert inferred intervention fields or replace the historical maturity labels. Thus the original internal audit and the new structural scan can be compared without silently changing their definitions.

## 5 Evaluation design

The benchmark specification and expected diagnostics were written before the first execution of this new benchmark. It is locally specified and has not been registered externally. The result records specification, case and tool hashes. The benchmark unit is a constructed manifest/source case. Variants of the same template are not treated as independent projects or population observations.

There are 31 cases: 15 field-presence or value cases, one duplicate-identity case, three reference cases, two producer cases, four valid constructor controls and six boundary cases. Twenty-six diagnostics are specified across these cases. Expected outputs are fixed by the case definitions rather than derived from the tool's observed outputs. Nevertheless, both the tool and cases were created within the same development effort, making the benchmark a conformance exercise with limited independence.

The complete configuration is compared with contract-only, reference-only and producer-only module ablations. Identity validation remains enabled in every configuration. The comparison measures which checks contribute to coverage of the predefined requirements; it is not a comparison against independent competing analyzers. No precision or recall estimate for naturally occurring software defects is inferred.

For a small performance check, manifests with 100, 500 and 1,000 declarations are audited against one source file. Each identical workload is run three times with Python allocation tracking enabled. Median wall time and peak tracked allocation are reported. They describe this machine and workload, include local filesystem overhead, and are not independent samples for hypothesis testing.

The case study analyzes the source revision resolved from audit-m2-20260911 and the current services tree. Version and source hashes bound the reports. Historical maturity and direction-ledger counts are interpreted only according to the existing internal audit. No new user sessions, independent annotator study or learning experiment is performed.

A separately specified exploratory stage checks source-reference portability using the public ActiDoo gamification-engine [6], fixed at commit b82a900f2f4a43cea463853e36d6f8237c7f255e. Three valid model-class references and four deliberately perturbed reference controls are evaluated without intervention-contract or producer checking. The selected classes are source-model objects, not an intervention census. This stage was specified after the constructed benchmark and before its own execution; it is not included in the original 31 cases.

## 6 Results

Table 1. Constructed conformance results. Expected diagnostics include unknown outcomes; identity checking is shared by all configurations.

| Configuration | Expected diagnostics returned | Unexpected diagnostics |
|---|---|---|
| full | 26/26 | 0 |
| contract_only | 16/26 | 0 |
| reference_only | 5/26 | 0 |
| producer_only | 7/26 | 0 |

Table 2. One-file workload on Python 3.11.16. Three repetitions per workload with allocation tracking enabled.

| Declarations | Median seconds | Median tracked Python allocation bytes |
|---|---|---|
| 100 | 0.1020 | 15862 |
| 500 | 0.5002 | 42724 |
| 1000 | 0.9609 | 42724 |


The complete configuration returned all 26 expected diagnostics, with no additional diagnostics on the supplied cases. Contract-only checking returned 16, reference-only checking five, and producer-only checking seven. These counts include identity validation shared by the configurations. The source checks therefore supplied evidence absent from the contract-only ablation within this specification. The result does not demonstrate superiority over JSON Schema, Semgrep or CodeQL implementations of equivalent rules.

All four supported constructor controls produced recognized sites. Dynamic and unsupported forms remained outside recognized literal evidence. The dead-code case produced a site, as designed, without any claim that it would execute. This boundary case is consequential: reporting the site's existence is correct, whereas interpreting it as runtime exposure would be incorrect.

The frozen registry contained 54 declarations, with historical maturity counts of nine complete, 37 partial and eight placeholders. The new structural adapter found 378 absent contract fields, corresponding to seven explicit contract fields for each declaration. This differs from the historical diagnosis of four missing schema components: the new result concerns explicit fields in the literal registry, while the historical analysis also considered stage metadata, direction ledgers and runtime properties. It must not be reported as 378 independent defects or evidence that the historical count was wrong.

The source adapter identified two supported literal construction sites, associated with LF-M44 and LF-M52. In this case their identities agree with the historical producer inventory, but the new scanner does not reproduce the stronger semantic or runtime interpretation of that inventory. Forty references used unverified single or multiple line numbers, and three were file-only references. The current tree retained the same registry counts and site identities, with changed line locations. Unchanged maturity labels do not prove that all implementation behavior remained unchanged.

On the fixed external source file, the unchanged reference adapter resolved the Achievement, Reward and AchievementTriggerStep classes and returned the expected diagnoses for missing symbol, missing file, root escape and line-only controls. All seven checks matched their specified outputs. This supports bounded source-reference inspection on an unrelated codebase; it does not establish intervention-contract coverage, runtime compatibility or naturally occurring defect accuracy for that platform. Its original MIT license and source hashes are retained.

## 7 Discussion and limitations

The main engineering value is an inspectable distinction between what a registry declares and what a source scan supports. A report can direct implementation review to missing metadata, unresolved references and literal production sites while making its own limits visible. It can be used before instrumenting runtime exposure, but it cannot replace that instrumentation.

The constructed evaluation supports conformance to a small set of specified rules. Its cases were authored alongside the tool and therefore cannot establish independent defect-detection performance. The complete intervention-contract evaluation contains one internally developed application, with two revisions rather than two independent systems. The external source-reference check is narrower and does not establish cross-project usefulness of the complete method.

The analyzer does not prove reachability, arbitral correctness or semantic consistency of constructs. Supporting more imports or factories would require both implementation work and new evaluation cases. A future external corpus should contain adjudicated defects and benign examples selected independently of the tool's rules, and should report adaptation costs and failure modes. This would change the scope of the contribution rather than merely increase a test count.

The performance workloads contain one source file and do not characterize large repositories. The prototype has not undergone independent installation review, adoption measurement or production deployment. These limitations restrict claims of usability and impact. They do not invalidate the reported behavior on the supplied cases.

## 8 Conclusion

The prototype combines intervention contract checking, symbol-reference inspection and literal construction evidence in a reproducible read-only audit. It meets the predefined conformance cases and exposes missing registry metadata in a versioned LearnFlow case study. Its conclusions concern implementation evidence within the scanned scope. Runtime reachability, user exposure and intervention effects require additional evidence, while external-case evaluation is needed before claiming general usefulness across applications.

## Data and software availability

The local replication package contains the Python package, benchmark specification, generated cases, individual diagnostics, versioned source hashes and case-study adapters. The package has no third-party runtime dependencies and requires Python 3.11 or later. Public release URL, persistent archive identifier and author-confirmed software license have not yet been assigned. They must be supplied before a submission requiring public software access. No participant data are included or required by this evaluation.

## AI assistance disclosure

The author reports using WorkBuddy and Codex and identifies ChatGPT, DeepSeek and Hy4 among the tools or models used. Codex assisted with code, tests, source inspection, analysis and manuscript drafting. Exact versions and task attribution remain to be confirmed in the final disclosure. The author is responsible for reviewing and validating the final materials; this draft does not assert that complete personal review has already occurred.

## References

[1] JSON Schema. JSON Schema Validation: A Vocabulary for Structural Validation of JSON. Draft 2020-12. https://json-schema.org/draft/2020-12/json-schema-validation

[2] Python Software Foundation. ast — Abstract syntax trees. Python documentation. https://docs.python.org/3/library/ast.html

[3] Semgrep. Write rules. Official documentation. https://docs.semgrep.dev/writing-rules/overview

[4] CodeQL. About CodeQL queries. Official documentation. https://codeql.github.com/docs/writing-codeql-queries/about-codeql-queries/

[5] Runeson, P., & Höst, M. (2009). Guidelines for conducting and reporting case study research in software engineering. Empirical Software Engineering, 14, 131–164. https://doi.org/10.1007/s10664-008-9102-8

[6] ActiDoo. Gamification-engine. Source code, commit b82a900f2f4a43cea463853e36d6f8237c7f255e, MIT license. https://github.com/ActiDoo/gamification-engine/tree/b82a900f2f4a43cea463853e36d6f8237c7f255e
