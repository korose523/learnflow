# -*- coding: utf-8 -*-
"""提交前暂存区审计： 试运行 → 统计文件数/总体积/最大文件，并扫描风险路径。

用法（在仓库根执行）：
    python scripts/audit_staged.py

风险路径命中不意味着一定不能提交，但必须人工确认后再提交
（本仓库历史上有 13 GB data/ 与 49 MB 第三方浅克隆误入的前科）。
"""
import os
import re
import subprocess

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = subprocess.run(["git", "add", "-An"], capture_output=True, text=True,
                     encoding="utf-8", errors="replace").stdout

paths = []
for line in out.splitlines():
    m = re.match(r"^add '(.+)'$", line.strip())
    if m:
        paths.append(m.group(1).replace("\\", "/"))

print("would-add files:", len(paths))

total = 0
missing = 0
rows = []
for p in paths:
    try:
        s = os.path.getsize(p)
    except OSError:
        missing += 1
        continue
    total += s
    rows.append((s, p))

rows.sort(reverse=True)
print("total bytes: %d  (%.2f MB)" % (total, total / 2**20))
print("missing (unreadable):", missing)
print("\nlargest 15:")
for s, p in rows[:15]:
    print("  %10.2f MB  %s" % (s / 2**20, p))

RISK = ["data/", ".venv/", "node_modules/", "__pycache__/", ".pytest_tmp/",
        "round2_results_hygiene/", "external/", ".ollama/", "ollama_models/"]
print("\nrisk-pattern hits:")
for pat in RISK:
    hits = [p for p in paths if pat.strip("/") in p.split("/")]
    if hits:
        sz = sum(os.path.getsize(p) for p in hits if os.path.exists(p))
        print("  %-28s %5d files  %8.2f MB   e.g. %s" % (pat, len(hits), sz / 2**20, hits[0][:90]))
