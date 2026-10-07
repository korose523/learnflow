"""Extract real declarations without importing application code."""
import ast
import collections
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/intervention_audit/src"))
from intervention_audit.core import audit


def registry(text):
    tree = ast.parse(text)
    for n in tree.body:
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == "_SPECS_DATA":
            return ast.literal_eval(n.value)
    raise ValueError("Literal _SPECS_DATA registry not found")


def run(root, label):
    rows = registry((root / "mechanism_registry.py").read_text())
    # No translation of stage to trigger, priority to precedence, or direction ledger to schema.
    manifest = {"mechanisms": [{"id": r["id"], "impl_ref": r["impl_ref"], "expects_effect": False} for r in rows]}
    result = audit(manifest, root)
    result["case"] = label
    result["registry_summary"] = {"count": len(rows), "maturity": dict(collections.Counter(r["maturity"] for r in rows))}
    result["finding_counts"] = dict(collections.Counter(f["code"] for f in result["findings"]))
    result["adapter_note"] = "Seven intervention contract fields absent from literal registry; runtime Effect fields and separate ledgers do not establish per-declaration contract coverage."
    return result


def main():
    out = ROOT / "results/m2/engineering"; out.mkdir(parents=True, exist_ok=True)
    prefix = "learnflow-backend/app/services/"
    revision = subprocess.check_output(["git", "rev-parse", "audit-m2-20260911^{commit}"], cwd=ROOT, text=True).strip()
    files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", revision, prefix], cwd=ROOT, text=True).splitlines()
    with tempfile.TemporaryDirectory() as td:
        source = Path(td)
        for rel in files:
            if not rel.endswith(".py"): continue
            p = source / rel[len(prefix):]; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(subprocess.check_output(["git", "show", f"{revision}:{rel}"], cwd=ROOT))
        frozen = run(source, "audit-m2-20260911")
        frozen["git_revision"] = revision
        (out / "learnflow_frozen_audit.json").write_text(json.dumps(frozen, ensure_ascii=False, indent=2))
    current = run(ROOT / prefix, "current_working_services_tree")
    (out / "learnflow_current_audit.json").write_text(json.dumps(current, ensure_ascii=False, indent=2))
    for label, data in [("frozen", frozen), ("current", current)]:
        print(label, data["registry_summary"], data["finding_counts"], "literal sites", data["source_evidence"]["sites"])


if __name__ == "__main__":
    main()
