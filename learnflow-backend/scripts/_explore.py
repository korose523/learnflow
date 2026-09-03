"""临时探查脚本：摸清各口径的真实计数规则（用完即删）。"""
import ast
import pathlib
import re
import collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "app"

# 1) *Engine 类
engines = []
for p in sorted(APP.rglob("*.py")):
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("PARSE FAIL", p, e)
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Engine"):
            engines.append((str(p.relative_to(ROOT)), node.name, node.lineno))
print("L0 *Engine classes:", len(engines))
byname = collections.Counter(n for _, n, _ in engines)
print("  duplicate names:", {k: v for k, v in byname.items() if v > 1})
print("  unique names:", len(byname))
byfile = collections.Counter(f for f, _, _ in engines)
for f, c in byfile.most_common():
    print(f"   {c:3d}  {f}")

# 2) method 字符串取值
KEYFILES = [
    "app/services/learning_methods_engine.py",
    "app/services/learning_methods_engine_v3.py",
    "app/services/advanced_methods_engine.py",
    "app/services/meta_learning_skilltree.py",
]
for rel in KEYFILES:
    p = ROOT / rel
    if not p.exists():
        print("MISSING", rel)
        continue
    tree = ast.parse(p.read_text(encoding="utf-8"))
    vals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "method" and isinstance(v, ast.Constant):
                    vals.append((v.value, node.lineno))
    print(f"\n--- {rel}: {len(vals)} 'method' literals")
    uniq = []
    for v, ln in vals:
        mark = ""
        if v not in uniq:
            uniq.append(v)
        else:
            mark = " (dup)"
        print(f"   L{ln:<5} {v!r}{mark}")
    print("   unique:", len(uniq))

# 3) METHOD_TIPS
p = ROOT / "app/services/learning_methods_engine.py"
tree = ast.parse(p.read_text(encoding="utf-8"))
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "METHOD_TIPS":
                items = node.value.elts
                print("\nMETHOD_TIPS len:", len(items))
                keys = [e for it in items if isinstance(it, ast.Dict)
                        for k, v in zip(it.keys, it.values)
                        if isinstance(k, ast.Constant) and k.value == "method"
                        for e in [v.value] if isinstance(v, ast.Constant)]
                print("  method keys:", len(keys), "unique:", len(set(keys)))
                print("  ", sorted(set(keys)))

# 4) SKILL_DEFINITIONS
p = ROOT / "app/services/meta_learning_skilltree.py"
tree = ast.parse(p.read_text(encoding="utf-8"))
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "SKILL_DEFINITIONS":
                print("\nSKILL_DEFINITIONS len:", len(node.value.elts))
                sid = []
                for it in node.value.elts:
                    if isinstance(it, ast.Call):
                        for kw in it.keywords:
                            if kw.arg == "skill_id" and isinstance(kw.value, ast.Constant):
                                sid.append(kw.value.value)
                print("  skill_ids:", len(sid), "unique:", len(set(sid)))
                print("  ", sid)
