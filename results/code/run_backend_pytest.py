# -*- coding: utf-8 -*-
"""红线段验证：跑后端全量 pytest，确认 collected 数仍为 934。

用子进程调用（避免 pytest 的 capture 管理器吞掉输出），
并显式设置 PYTEST_DEBUG_TEMPROOT（目录必须预先存在，否则 tmp_path 夹具大批报 WinError 3）。
"""
import os
import re
import subprocess

BACKEND = r"E:\learnflow\learnflow-backend"
PY = os.path.join(BACKEND, ".venv", "Scripts", "python.exe")
TMPROOT = r"E:\learnflow\results\code\.pytest_tmp"
REPORT = r"E:\learnflow\results\code\pytest_out.txt"

os.makedirs(TMPROOT, exist_ok=True)

env = dict(os.environ)
env["PYTEST_DEBUG_TEMPROOT"] = TMPROOT
env["CODEBUDDY_SAFE_DELETE_ENABLED"] = "0"
env["PYTHONPATH"] = BACKEND
env["NO_PROXY"] = "localhost,127.0.0.1"
env["no_proxy"] = "localhost,127.0.0.1"

out = []


def run(args, label):
    p = subprocess.run([PY, "-m", "pytest"] + args, cwd=BACKEND, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (p.stdout or "").strip().splitlines()
    out.append("=== %s rc=%s ===" % (label, p.returncode))
    out.extend(tail[-25:])
    if p.returncode != 0 and p.stderr:
        out.append("--- stderr ---")
        out.extend((p.stderr or "").strip().splitlines()[-25:])
    return p


# 1) 收集阶段：produce 权威 collected 数
pc = run(["--collect-only", "-q", "-p", "no:cacheprovider"], "collect-only")
m = re.search(r"(\d+)\s+tests?\s+collected", pc.stdout or "")
collected = int(m.group(1)) if m else None
if collected is None:
    n = sum(1 for ln in (pc.stdout or "").splitlines() if "::" in ln)
    collected = n or None
out.append("COLLECTED=%s" % collected)

# 2) 执行阶段
pr = run(["-q", "-p", "no:cacheprovider"], "run")

out.append("COLLECT_RC=%s" % pc.returncode)
out.append("RUN_RC=%s" % pr.returncode)

open(REPORT, "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
