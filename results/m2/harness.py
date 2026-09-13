#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 实证复算 harness —— 只读运行 E:/learnflow 的脚本，全部输出重定向到 results/m2/。

为什么需要它
------------
仓库的 ``learnflow-backend/artifacts/`` 是 **git 跟踪** 目录（.gitignore 第 74 行
明确说明「刻意不忽略」）。直接运行 ``scan_mechanism_landing.py`` / ``verify_counts.py`` /
``verify_asset_numbers.py`` 会覆写这些被跟踪的 JSON，从而修改仓库。

本 harness 以 importlib 加载脚本模块后，把模块级输出路径常量重定向到 results/m2/，
再调用其 ``main()``。这样跑的是**脚本本体的真实逻辑**，但不写仓库。

用法：
    python results/m2/harness.py <task>
    task ∈ {fingerprint, landing, counts, assets, assets_pytest, implref}
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
import json
import os
import sys
from pathlib import Path

REPO_BACKEND = Path(r"E:\learnflow\learnflow-backend")
SCRIPTS = REPO_BACKEND / "scripts"
OUT = Path(r"E:/learnflow\results\m2")

sys.path.insert(0, str(REPO_BACKEND))
OUT.mkdir(parents=True, exist_ok=True)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_capture(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a, **kw)
    return rc, buf.getvalue()


def cmd_fingerprint():
    from app.services.mechanism_registry import (
        registry_fingerprint, count, ids, keys, CATEGORIES, by_category, STAGES,
    )
    from collections import Counter
    data = {
        "count": count(),
        "fingerprint": registry_fingerprint(),
        "id_first": ids()[0],
        "id_last": ids()[-1],
        "id_contiguous": ids() == [f"LF-M{i:02d}" for i in range(1, count() + 1)],
        "registry_CATEGORIES": list(CATEGORIES),
        "registry_STAGES": list(STAGES),
        "registry_category_counts": {c: len(by_category(c)) for c in CATEGORIES},
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))
    (OUT / "fingerprint.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_landing():
    mod = load("lf_scan_landing", SCRIPTS / "scan_mechanism_landing.py")
    mod.ARTIFACTS_DIR = OUT
    rc, txt = run_capture(mod.main, [])
    (OUT / "scan_mechanism_landing.stdout.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"[harness] rc={rc}")


def cmd_counts():
    mod = load("lf_verify_counts", SCRIPTS / "verify_counts.py")
    mod.ARTIFACTS_DIR = OUT
    mod.JSON_OUT = OUT / "count_verification.json"
    rc, txt = run_capture(mod.main, [])
    (OUT / "verify_counts.stdout.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"[harness] rc={rc}")


def cmd_assets():
    mod = load("lf_verify_assets", SCRIPTS / "verify_asset_numbers.py")
    mod.ARTIFACTS_DIR = OUT
    mod.JSON_OUT = OUT / "asset_numbers.json"
    rc, txt = run_capture(mod.main, [])
    (OUT / "verify_asset_numbers.stdout.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"[harness] rc={rc}")


def cmd_assets_pytest():
    mod = load("lf_verify_assets2", SCRIPTS / "verify_asset_numbers.py")
    mod.ARTIFACTS_DIR = OUT
    mod.JSON_OUT = OUT / "asset_numbers_with_pytest.json"
    rc, txt = run_capture(mod.main, ["--with-pytest"])
    (OUT / "verify_asset_numbers_with_pytest.stdout.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"[harness] rc={rc}")


def cmd_implref():
    mod = load("lf_check_implref", SCRIPTS / "check_impl_ref.py")
    mod.ARTIFACT = OUT / "impl_ref_integrity.json"
    rc, txt = run_capture(mod.main, ["--json"])
    (OUT / "check_impl_ref.stdout.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"[harness] rc={rc}")


TASKS = {
    "fingerprint": cmd_fingerprint,
    "landing": cmd_landing,
    "counts": cmd_counts,
    "assets": cmd_assets,
    "assets_pytest": cmd_assets_pytest,
    "implref": cmd_implref,
}

if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    t = sys.argv[1]
    TASKS[t]()
