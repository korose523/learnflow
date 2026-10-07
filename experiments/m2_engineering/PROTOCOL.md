# M2 engineering evaluation specification

This specification is fixed before the first execution of the new benchmark.
It is not registered with an external registry. Source and specification hashes
are saved with each result. The evaluation unit is a constructed source/manifest
case, not a student, session, or independent software project.

Primary questions: (1) do structural contract checks return the declared diagnostic
for an injected defect? (2) do symbol and literal-site checks add coverage beyond
contract-only validation? (3) which unsupported Python constructs require an
unknown result rather than a false statement of reachability?

The case generator fixes expected codes independently of the audit execution.
Cases include seven removed contract fields, invalid types/values, duplicate IDs,
missing file/symbol, root escape, unregistered literals, four equivalent supported
constructor forms, and five unsupported or non-executed forms. Baselines are
module ablations (contract only, reference only, producer only), not externally
implemented competing products. They are evaluated on the same cases.

Report exact expected-diagnostic recall, unexpected diagnostics, and per-family
results. Do not interpret perfect conformance on designer-authored cases as
real-project precision/recall. No significance test on case permutations or timing
repetitions. Measure a 100/500/1000-declaration manifest three times with the same
source file; median wall time and peak Python allocation describe this machine,
not statistical superiority or repository-scale complexity.

Real-source audit is separate: extract the literal registry from the frozen
audit-m2-20260911 revision and current services tree without importing app code.
Keep stage separate from a complete trigger, priority separate from complete
precedence, and ledger directions separate from implementation schema. The new
tool must not recreate the historical semantic producer count as if literal AST
sites were interchangeable. No runtime conflict rates or learning effects.

Public external repositories and independent expert review are not included in
this execution. Their absence limits the paper's cross-project claims. A separate
case study and a frozen external evaluation set are required before making those
claims.
