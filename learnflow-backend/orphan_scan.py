"""临时诊断：从 API 入口出发，分析 app/services 模块的可达性。

判据不是"有没有人 import"，而是"从一次真实 HTTP 请求能否走到"。
桶文件 services/__init__.py 的 re-export 不计入可达（导入≠调用）。
"""
import ast
import pathlib
from collections import defaultdict, deque

root = pathlib.Path(".")
svc_dir = root / "app" / "services"


def module_name(path: pathlib.Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def parse_imports(path: pathlib.Path):
    """返回该文件 import 的所有模块末段名（不含相对导入的 '.'）。"""
    out = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module.split(".")[-1])
            # `from app.services import anti_addiction` 的被导入名也要计入
            for a in node.names:
                out.add(a.name.split(".")[-1])
        elif isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name.split(".")[-1])
    return out


# 1. 建立 末段名 -> 文件 的索引
by_stem = defaultdict(list)
for f in (root / "app").rglob("*.py"):
    by_stem[f.stem].append(f)

# 2. 入口：API 路由 + main
entries = list((root / "app" / "api").rglob("*.py")) + list((root / "app" / "routers").rglob("*.py"))
main_py = root / "app" / "main.py"
if main_py.exists():
    entries.append(main_py)
entries = [e for e in entries if e.name != "__init__.py"]

# 3. BFS，把 services/__init__.py 视为不可传递的桶
BARRELS = {"__init__"}

seen = set()
queue = deque()
for e in entries:
    seen.add(e.resolve())
    queue.append(e)

while queue:
    cur = queue.popleft()
    for stem in parse_imports(cur):
        if stem in BARRELS:
            continue
        for tgt in by_stem.get(stem, []):
            if tgt.resolve() not in seen:
                seen.add(tgt.resolve())
                queue.append(tgt)

svc_files = sorted(f for f in svc_dir.glob("*.py") if f.name != "__init__.py")
reachable = [f for f in svc_files if f.resolve() in seen]
unreachable = [f for f in svc_files if f.resolve() not in seen]

print(f"API 入口文件数        : {len(entries)}")
print(f"服务模块总数          : {len(svc_files)}")
print(f"从 API 可达的服务模块 : {len(reachable)}")
print(f"不可达(机制未落地)    : {len(unreachable)}")
print(f"不可达率              : {len(unreachable) / len(svc_files) * 100:.1f}%")
print()
print("【不可达模块 — 这些机制没有接进任何 HTTP 请求路径】")
for f in unreachable:
    print(f"  - {f.stem}")
