"""Constructed conformance benchmark; no application import or database writes."""
import copy
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/intervention_audit/src"))
from intervention_audit.core import FIELDS, audit

SOURCE = 'from app.services.mechanism_registry import Effect\ndef make():\n    return Effect(mechanism_id="M1")\n'
BASE = {"id": "M1", "trigger": "after_response", "target_construct": "engagement",
        "direction": "approach", "channel": "banner", "cost": 1.0,
        "side_effect": [], "precedence": 10, "impl_ref": "engine.py:make", "expects_effect": True}


def cases():
    rows = []
    def add(name, item=None, source=SOURCE, expected=(), family="contract", extra=()):
        rows.append({"name": name, "family": family,
                     "manifest": {"mechanisms": [copy.deepcopy(BASE if item is None else item), *extra]},
                     "source": source, "expected": [list(x) for x in expected]})
    for f in FIELDS:
        item = copy.deepcopy(BASE); del item[f]
        add("missing_" + f, item, expected=[("MISSING_FIELD", "M1", f)])
    for f, v in [("trigger", ""), ("target_construct", []), ("channel", 3),
                 ("direction", "push"), ("cost", -1), ("cost", True),
                 ("precedence", "high"), ("side_effect", "none")]:
        item = {**BASE, f: v}
        add("invalid_" + f + "_" + str(v), item, expected=[("INVALID_FIELD", "M1", f)])
    add("duplicate", extra=[copy.deepcopy(BASE)], expected=[("DUPLICATE_ID", "M1", None)], family="identity")
    for name, ref, code in [("missing_file", "absent.py:make", "MISSING_SOURCE"),
                             ("missing_symbol", "engine.py:absent", "MISSING_SYMBOL"),
                             ("root_escape", "../engine.py:make", "INVALID_REFERENCE")]:
        add(name, {**BASE, "impl_ref": ref}, expected=[(code, "M1", None)], family="reference")
    add("unregistered", source=SOURCE + '\ndef other():\n    return Effect(mechanism_id="M2")\n',
        expected=[("UNREGISTERED_PRODUCER", "M2", None)], family="producer")
    add("absent_literal", source="def make():\n    return None\n",
        expected=[("NO_LITERAL_PRODUCER", "M1", None)], family="producer")
    # Known-equivalent forms are fixed positive controls, not independent projects.
    add("clean_direct", family="clean")
    add("clean_alias", source=SOURCE.replace("import Effect", "import Effect as Candidate").replace("return Effect", "return Candidate"), family="clean")
    add("clean_module", source='import app.services.mechanism_registry as registry\ndef make():\n    return registry.Effect(mechanism_id="M1")\n', family="clean")
    add("clean_nested", {**BASE, "impl_ref": "engine.py:Engine.make"},
        source='from app.services.mechanism_registry import Effect\nclass Engine:\n    def make(self):\n        return Effect(mechanism_id="M1")\n', family="clean")
    add("dynamic_id", source=SOURCE.replace('mechanism_id="M1"', 'mechanism_id=identifier'),
        expected=[("NO_LITERAL_PRODUCER", "M1", None)], family="boundary")
    add("star_import", source=SOURCE.replace("import Effect", "import *"),
        expected=[("NO_LITERAL_PRODUCER", "M1", None)], family="boundary")
    add("comment_only", source='def make():\n    # Effect(mechanism_id="M1")\n    return None\n',
        expected=[("NO_LITERAL_PRODUCER", "M1", None)], family="boundary")
    add("unrelated_class", source='class Effect:\n    pass\ndef make():\n    return Effect(mechanism_id="M1")\n',
        expected=[("NO_LITERAL_PRODUCER", "M1", None)], family="boundary")
    add("line_reference", {**BASE, "impl_ref": "engine.py:2"},
        expected=[("LINE_REFERENCE_UNVERIFIED", "M1", None)], family="boundary")
    # Dead code deliberately still contains a literal: the tool makes no reachability claim.
    add("dead_code_literal", source=SOURCE.replace('return Effect', 'if False:\n        return Effect'), family="boundary")
    return rows


def expected_hit(expected, findings):
    return any(f["code"] == expected[0] and f["mechanism_id"] == expected[1]
               and (expected[2] is None or f["detail"] == expected[2]) for f in findings)


def main():
    rows = cases()
    out = ROOT / "results/m2/engineering"; out.mkdir(parents=True, exist_ok=True)
    configs = {"full": {}, "contract_only": {"references": False, "producers": False},
               "reference_only": {"contracts": False, "producers": False},
               "producer_only": {"contracts": False, "references": False}}
    result = {"scope": "constructed_conformance_not_independent_real_defect_accuracy",
              "case_count": len(rows), "cases": [], "configurations": {}, "performance": [],
              "python": platform.python_version(), "platform": platform.platform(),
              "protocol_sha256": hashlib.sha256((Path(__file__).parent / "PROTOCOL.md").read_bytes()).hexdigest(),
              "tool_sha256": hashlib.sha256((ROOT / "tools/intervention_audit/src/intervention_audit/core.py").read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory() as td:
        source = Path(td)
        for config, flags in configs.items():
            detected = total = unexpected = 0
            family = {}
            for row in rows:
                (source / "engine.py").write_text(row["source"])
                findings = audit(row["manifest"], source, **flags)["findings"]
                hits = sum(expected_hit(x, findings) for x in row["expected"])
                extras = sum(not any(expected_hit(x, [f]) for x in row["expected"]) for f in findings)
                detected += hits; total += len(row["expected"]); unexpected += extras
                fam = family.setdefault(row["family"], {"expected": 0, "detected": 0, "unexpected": 0})
                fam["expected"] += len(row["expected"]); fam["detected"] += hits; fam["unexpected"] += extras
                if config == "full":
                    result["cases"].append({**row, "findings": findings, "matched": hits, "unexpected": extras})
            result["configurations"][config] = {"expected": total, "detected": detected,
                "expected_diagnostic_recall": detected / total, "unexpected": unexpected, "by_family": family}
        (source / "engine.py").write_text(SOURCE)
        for n in (100, 500, 1000):
            declarations = [{**BASE, "id": "M" + str(i), "expects_effect": False} for i in range(n)]
            times, peaks = [], []
            for _ in range(3):
                tracemalloc.start(); start = time.perf_counter()
                audit({"mechanisms": declarations}, source)
                times.append(time.perf_counter() - start); peaks.append(tracemalloc.get_traced_memory()[1]); tracemalloc.stop()
            result["performance"].append({"declarations": n, "repetitions": 3,
                "median_seconds": statistics.median(times), "median_peak_python_bytes": statistics.median(peaks),
                "source_files": 1, "note": "same workload repetitions, not independent research samples"})
    (out / "benchmark_cases.json").write_text(json.dumps(rows, indent=2) + "\n")
    result["cases_sha256"] = hashlib.sha256((out / "benchmark_cases.json").read_bytes()).hexdigest()
    (out / "benchmark_results.json").write_text(json.dumps(result, indent=2) + "\n")
    full = result["configurations"]["full"]
    if full["detected"] != full["expected"] or full["unexpected"]:
        raise SystemExit("Conformance mismatch: inspect saved individual diagnostics")
    print(json.dumps({"cases": len(rows), "configurations": result["configurations"], "performance": result["performance"]}, indent=2))


if __name__ == "__main__":
    main()
