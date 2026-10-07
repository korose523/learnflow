from __future__ import annotations

import ast
import hashlib
import math
import re
from pathlib import Path

FIELDS = ("trigger", "target_construct", "direction", "channel", "cost", "side_effect", "precedence")
TEXT_FIELDS = ("trigger", "target_construct", "channel")


def source_evidence(root: Path) -> dict:
    """Parse local files without importing them; resolve explicit Effect imports only.

    No call graph, runtime reachability, dynamic import or interprocedural analysis.
    Attribute calls require an import alias bound to mechanism_registry.
    """
    root = root.resolve()
    files, sites, unknown, symbols, errors = {}, [], [], {}, []
    for path in sorted(root.rglob("*.py")):
        if any(p in {".git", ".venv", "node_modules", "__pycache__"} for p in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        if not path.resolve().is_relative_to(root):
            errors.append({"path": rel, "error": "symlink escapes source root; not read"})
            continue
        raw = path.read_bytes()
        files[rel] = hashlib.sha256(raw).hexdigest()
        try:
            tree = ast.parse(raw, filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append({"path": rel, "error": str(exc)})
            continue
        # Import binding is intentionally module-local and conservative.
        names, modules = set(), set()
        for n in tree.body:
            if isinstance(n, ast.ImportFrom) and n.module and n.module.endswith("mechanism_registry"):
                names.update(a.asname or a.name for a in n.names if a.name == "Effect")
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.endswith("mechanism_registry") and a.asname:
                        modules.add(a.asname)
        # Rebinding prevents accepting a shadowed constructor as known evidence.
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                names.discard(n.id)
                modules.discard(n.id)
            if isinstance(n, ast.arg):
                names.discard(n.arg)
                modules.discard(n.arg)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.discard(n.name)
                modules.discard(n.name)

        def collect(nodes, prefix=""):
            for n in nodes:
                if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = prefix + n.name
                    symbols.setdefault(rel, {})[key] = n.lineno
                    collect(n.body, key + ".")
        collect(tree.body)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            known = (isinstance(n.func, ast.Name) and n.func.id in names) or (
                isinstance(n.func, ast.Attribute) and n.func.attr == "Effect"
                and isinstance(n.func.value, ast.Name) and n.func.value.id in modules)
            if not known:
                continue
            kw = {x.arg: x.value for x in n.keywords}
            v = kw.get("mechanism_id")
            rec = {"path": rel, "line": n.lineno}
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                sites.append({**rec, "mechanism_id": v.value,
                              "evidence": "literal_construction_site_not_runtime_exposure"})
            else:
                unknown.append({**rec, "reason": "nonliteral_or_missing_mechanism_id"})
    return {"files": files, "sites": sites, "unknown_calls": unknown,
            "symbols": symbols, "parse_errors": errors}


def audit(manifest: dict, root: Path, *, contracts=True, references=True, producers=True) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if not root.is_dir():
        raise ValueError("source root must be an existing directory")
    evidence = source_evidence(root)
    findings = []
    def add(code, ident, detail, severity="error"):
        findings.append({"code": code, "mechanism_id": ident, "detail": detail, "severity": severity})
    items = manifest.get("mechanisms", [])
    if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
        raise ValueError("mechanisms must be a list of objects")
    seen = set()
    for item in items:
        ident = item.get("id")
        if not isinstance(ident, str) or not ident.strip():
            add("INVALID_ID", str(ident), "Nonempty string ID required")
            continue
        if ident in seen:
            add("DUPLICATE_ID", ident, "ID occurs more than once")
        seen.add(ident)
        if contracts:
            for field in FIELDS:
                if field not in item or item[field] is None:
                    add("MISSING_FIELD", ident, field)
            for field in TEXT_FIELDS:
                if field in item and item[field] is not None and (
                    not isinstance(item[field], str) or not item[field].strip()):
                    add("INVALID_FIELD", ident, field)
            if "direction" in item and item["direction"] is not None and item["direction"] not in ("approach", "withdraw", "neutral"):
                add("INVALID_FIELD", ident, "direction")
            for field in ("cost", "precedence"):
                if field in item and item[field] is not None:
                    v = item[field]
                    valid = type(v) in (int, float) and math.isfinite(v)
                    if field == "cost": valid = valid and v >= 0
                    if not valid: add("INVALID_FIELD", ident, field)
            if "side_effect" in item and item["side_effect"] is not None:
                v = item["side_effect"]
                if not isinstance(v, list) or any(not isinstance(s, str) or not s.strip() for s in v):
                    add("INVALID_FIELD", ident, "side_effect")
        if references:
            ref = item.get("impl_ref")
            if not isinstance(ref, str) or ":" not in ref:
                add("UNRESOLVED_REFERENCE", ident, "Expected relative file.py:QualifiedSymbol", "unknown")
            else:
                rel, symbol = ref.rsplit(":", 1)
                p = (root / rel).resolve()
                if not p.is_relative_to(root.resolve()):
                    add("INVALID_REFERENCE", ident, "Reference escapes source root")
                elif rel not in evidence["files"]:
                    add("MISSING_SOURCE", ident, rel)
                elif re.fullmatch(r"\d+(,\d+)*", symbol):
                    add("LINE_REFERENCE_UNVERIFIED", ident, ref, "unknown")
                elif not re.fullmatch(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*", symbol):
                    add("UNRESOLVED_REFERENCE", ident, ref, "unknown")
                elif symbol not in evidence["symbols"].get(rel, {}):
                    add("MISSING_SYMBOL", ident, ref)
        if producers and item.get("expects_effect") is True:
            if not any(s["mechanism_id"] == ident for s in evidence["sites"]):
                add("NO_LITERAL_PRODUCER", ident, "No supported literal site in scanned scope; absence is not proof of nonimplementation", "unknown")
    if producers:
        for site in evidence["sites"]:
            if site["mechanism_id"] not in seen:
                add("UNREGISTERED_PRODUCER", site["mechanism_id"], f"{site['path']}:{site['line']}")
    return {"version": "0.1.0", "scope": "structural_contract_and_literal_python_evidence",
            "mechanisms": len(items), "findings": findings, "source_evidence": evidence,
            "limits": ["not a reachability or semantic verifier", "no runtime exposure or learning-effect inference",
                       "line-only references remain unknown", "factories, star imports and dynamic imports are not resolved"]}
