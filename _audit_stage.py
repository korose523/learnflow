# -*- coding: utf-8 -*-
"""git add -An 试运行结果的体积/风险审计（提交前必查）。"""
import os
import re
import subprocess

os.chdir("E:/learnflow")
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
