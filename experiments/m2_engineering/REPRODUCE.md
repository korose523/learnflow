# Reproduce M2 engineering evaluation

Requires Python 3.11 or later, with no runtime third-party packages. Run from the
repository root using an isolated environment.

```sh
uv venv .audit-venv --python 3.11
uv pip install --python .audit-venv/bin/python -e tools/intervention_audit
.audit-venv/bin/python experiments/m2_engineering/run_benchmark.py
.audit-venv/bin/python experiments/m2_engineering/audit_learnflow.py
.audit-venv/bin/python experiments/m2_engineering/check_external_adapter.py
```

The historical adapter requires the audit-m2-20260911 Git revision. A partial source
snapshot without repository history cannot regenerate that step; use the original
repository or inspect the supplied result with its source hashes.

The external check uses fixed-commit source and the original MIT license under
results/m2/engineering/external/gengine. SOURCE.json records official URLs and
SHA256. It never imports or starts that application.

Outputs are under results/m2/engineering. The main benchmark is 31 designer-authored
conformance cases, not independent natural-defect accuracy. Module ablations are
not competing implementations. External reference checks are a separately
specified stage and do not validate an intervention registry.

Source hashes and deterministic diagnostic counts should reproduce. Wall time and
allocation depend on machine, Python version and filesystem. No database,
participant records, model calls or paid service is used.
