import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/intervention_audit/src"))
from intervention_audit.core import audit, source_evidence


def test_scanning_never_executes_inspected_code(tmp_path):
    sentinel = tmp_path / "executed.txt"
    (tmp_path / "danger.py").write_text(f'raise RuntimeError("must never execute")\nopen({str(sentinel)!r}, "w").write("bad")\n')
    result = source_evidence(tmp_path)
    assert "danger.py" in result["files"]
    assert not sentinel.exists()


def test_unreachable_literal_is_not_runtime_evidence(tmp_path):
    (tmp_path / "engine.py").write_text('from app.services.mechanism_registry import Effect\ndef make():\n    if False:\n        return Effect(mechanism_id="M1")\n')
    result = source_evidence(tmp_path)
    assert result["sites"][0]["evidence"] == "literal_construction_site_not_runtime_exposure"
    assert "reachable" not in result["sites"][0]


def test_shadowed_and_dynamic_calls_are_not_certified(tmp_path):
    (tmp_path / "engine.py").write_text('from app.services.mechanism_registry import Effect\ndef make(Effect):\n    return Effect(mechanism_id="M1")\n')
    assert source_evidence(tmp_path)["sites"] == []
    (tmp_path / "engine.py").write_text('from app.services.mechanism_registry import Effect\ndef make():\n    return Effect(mechanism_id=lookup())\n')
    result = source_evidence(tmp_path)
    assert result["sites"] == [] and len(result["unknown_calls"]) == 1


def test_source_parse_failure_is_not_silent(tmp_path):
    (tmp_path / "bad.py").write_text("def not valid")
    result = audit({"mechanisms": []}, tmp_path)
    assert len(result["source_evidence"]["parse_errors"]) == 1


def test_module_cli_installed_entry_contract(tmp_path):
    import os
    (tmp_path / "manifest.json").write_text(json.dumps({"mechanisms": []}))
    env = {**os.environ, "PYTHONPATH": str(ROOT / "tools/intervention_audit/src")}
    proc = subprocess.run([sys.executable, "-m", "intervention_audit.cli", str(tmp_path / "manifest.json"),
                           "--source-root", str(tmp_path), "--output", str(tmp_path / "audit.json")], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads((tmp_path / "audit.json").read_text())["scope"] == "structural_contract_and_literal_python_evidence"
