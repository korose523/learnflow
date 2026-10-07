import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/intervention_audit/src"))
from intervention_audit.core import audit


def main():
    source = ROOT / "results/m2/engineering/external/gengine"
    rel = "gengine/app/model.py"
    cases = [("Achievement", rel + ":Achievement", None),
             ("Reward", rel + ":Reward", None),
             ("AchievementTriggerStep", rel + ":AchievementTriggerStep", None),
             ("missing_symbol", rel + ":NonexistentAuditControl", "MISSING_SYMBOL"),
             ("missing_file", "absent.py:Achievement", "MISSING_SOURCE"),
             ("escape", "../outside.py:Achievement", "INVALID_REFERENCE"),
             ("line_only", rel + ":1243", "LINE_REFERENCE_UNVERIFIED")]
    records = []
    for name, ref, expected in cases:
        data = audit({"mechanisms": [{"id": name, "impl_ref": ref}]}, source, contracts=False, producers=False)
        codes = [r["code"] for r in data["findings"]]
        wanted = [] if expected is None else [expected]
        records.append({"name": name, "reference": ref, "expected": wanted, "actual": codes,
                        "matched": codes == wanted, "findings": data["findings"]})
        if data["source_evidence"]["parse_errors"]:
            raise ValueError(data["source_evidence"]["parse_errors"])
    report = {"scope": "external_source_reference_adapter_only", "cases": records,
              "source": json.loads((source / "SOURCE.json").read_text()),
              "protocol_sha256": hashlib.sha256((Path(__file__).parent / "EXTERNAL_PROTOCOL.md").read_bytes()).hexdigest(),
              "tool_sha256": hashlib.sha256((ROOT / "tools/intervention_audit/src/intervention_audit/core.py").read_bytes()).hexdigest(),
              "matched": sum(r["matched"] for r in records), "total": len(records),
              "limits": ["selected classes are not intervention census", "no intervention contract or runtime checks", "not independent adoption or defect accuracy"]}
    (source.parent / "external_adapter_results.json").write_text(json.dumps(report, indent=2))
    assert report["matched"] == report["total"]
    print(f"External adapter reference checks: {report['matched']}/{report['total']}; commit {report['source']['commit']}")


if __name__ == "__main__":
    main()
