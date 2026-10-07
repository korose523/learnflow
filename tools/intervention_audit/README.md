# Intervention implementation audit

Version 0.1.0 is a read-only research prototype. It validates a JSON intervention
contract and links declarations to Python symbol and literal construction evidence.
It never imports inspected code or writes to the application/database.

Requires Python 3.11 or later; no runtime third-party dependencies.

```sh
uv venv .audit-venv --python 3.11
uv pip install --python .audit-venv/bin/python ./tools/intervention_audit
.audit-venv/bin/intervention-audit manifest.json --source-root source/ --output audit.json
```

For a local source checkout without installation:

```sh
PYTHONPATH=tools/intervention_audit/src python -m intervention_audit.cli manifest.json --source-root source/ --output audit.json
python experiments/m2_engineering/run_benchmark.py
python experiments/m2_engineering/audit_learnflow.py
```

A complete toy example is included under `examples/demo`. It has no participant
data and is not used as a real-system case or a new research result:

```sh
intervention-audit tools/intervention_audit/examples/demo/manifest.json --source-root tools/intervention_audit/examples/demo --output /tmp/demo-audit.json
```

The expected report has one declaration, one supported literal site and no findings.
CLI success means the report was generated, not that the inspected system is safe.

The manifest contains a `mechanisms` array. Each record has `id`, `impl_ref`,
`expects_effect` and the contract fields `trigger`, `target_construct`, `direction`,
`channel`, `cost`, `side_effect`, `precedence`. Missing/unknown fields are reported,
not filled by guessing. Empty side-effect lists mean an explicit declaration,
not proof that a mechanism is harmless. Triggers and constructs are descriptive
strings, not verified psychological or executable predicates.

References use root-relative `file.py:Class.method`. Line-only references remain
unverified. Explicit imports of `Effect` from a module ending in
`mechanism_registry`, with optional aliases, are supported. A supported literal
construction site is not proof that a function can execute or the effect was
presented. Alias rebinding is conservatively treated as unsupported. Dynamic
factories, star imports, reflection and interprocedural ID propagation are outside
scope. Parse failures are retained. Never treat absence of a finding as safety
certification or absence of a construction site as proof of absence of an effect.

The supplied benchmark is a constructed conformance benchmark, not an independent
measurement of real-project defect-detection precision. The real case study is
LearnFlow. A separate fixed-commit external gamification-engine check covers source
references only; it does not validate an external intervention registry or runtime.
No student logs are required.

Licensing: no new repository-wide license has been asserted. External publication
of this package requires the author's confirmed license and release decision.
