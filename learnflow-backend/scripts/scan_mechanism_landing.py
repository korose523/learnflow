#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_mechanism_landing.py —— LearnFlow 机制落地审计矩阵（可复算）
=============================================================================

数字诚信声明（重要）
-----------------------------------------------------------------------------
本项目的游戏化机制经审计为 **53** 个唯一机制（LF-M01..LF-M53），来源是
``app/services/mechanism_registry.py`` 的单一事实源，并由
``scripts/verify_counts.py`` 的 AST 复算交叉校验（mechanism_unique=53）。

历史上曾有「76 种游戏化机制」的宣称，该数字在任何口径下都不成立，已被
verify_counts.py 证伪并拒绝引用。**「76」是禁止引用的遗留错误数字，本脚本
绝不以任何形式引用它。** 53 是经过审计、可被一条命令复算的唯一机制数。

为什么需要这个脚本
-----------------------------------------------------------------------------
mechanism_registry 枚举了 53 个机制，但研究发现其中 39 个虽有引擎逻辑、却
**零外部运行时调用方**（orphan）。本脚本把「机制落地状态」从口头声明变为
**一条命令可复算的审计矩阵**：对每个机制判断它是否真正接入运行时（有外部
引用，或被编排器流程接线/门控），并写入 ``artifacts/mechanism_landing_status.json``。

我们**不伪造**实现：orphan 机制被如实记录为 "logic present, not
orchestrator-wired"，其落地状态 = 引擎/文档可达、运行时不可达。这样论文的
「机制落地」主张是诚实、可审计、可复算的。

运行
-----------------------------------------------------------------------------
    python scripts/scan_mechanism_landing.py          # 扫描 + 写 JSON + 打印摘要
    python scripts/scan_mechanism_landing.py --quiet  # 仅打印一行摘要

设计约束
-----------------------------------------------------------------------------
* 扫描逻辑只用标准库（ast / json / pathlib / subprocess），零第三方依赖。
* 注册表规格通过 ``from app.services.mechanism_registry import all_mechanisms``
  程序化读取（单一事实源），不重复硬编码任何机制清单。
* 可复算：同一 commit 下重复运行结果一致（仅时间戳/commit 变化）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 路径
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent                 # E:\learnflow\learnflow-backend
PROJECT_ROOT = BACKEND_ROOT.parent               # E:\learnflow
APP_DIR = BACKEND_ROOT / "app"
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
ORCH_PATH = APP_DIR / "services" / "learning_orchestrator.py"
REGISTRY_PATH = APP_DIR / "services" / "mechanism_registry.py"

# 允许以 `python scripts/scan_mechanism_landing.py` 直接运行（脚本目录不在后端根，
# 需把后端根加入 sys.path 才能 `import app`）。pytest 运行时后端根已在 path 上，无副作用。
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _git_commit() -> str:
    """取当前 commit hash；不在 git 仓库 / git 不可用时返回 "unknown"，绝不崩溃。"""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 扫描辅助
# ─────────────────────────────────────────────────────────────────────────────

def _impl_ref_file_exists(impl_ref: str, app_dir: Path) -> bool:
    """impl_ref 中 ':' 之前的文件名在后端下是否存在。"""
    fname = impl_ref.split(":", 1)[0].strip()
    if not fname:
        return False
    candidate = app_dir / "services" / fname
    if candidate.is_file():
        return True
    # 兜底：在 app/ 下递归查找同名文件
    for p in app_dir.rglob(fname):
        if p.is_file():
            return True
    return False


def _collect_source_texts(app_dir: Path) -> List[Tuple[str, str]]:
    """读取 app/services/*.py 与 app/api/*.py 的源码文本（一次读取，供多机制复用）。"""
    out: List[Tuple[str, str]] = []
    for pat in ("services/*.py", "api/*.py"):
        for f in sorted(app_dir.glob(pat)):
            if f.name == "mechanism_registry.py":
                continue
            if "tests" in f.parts:
                continue
            try:
                out.append((f.name, f.read_text(encoding="utf-8")))
            except (UnicodeDecodeError, OSError):
                continue
    return out


def _scan_external_ref(key: str, impl_ref: str, file_texts: List[Tuple[str, str]]) -> bool:
    """检索 key（及 impl_ref 中可能的符号）是否出现在 services/api 源码中。

    复现「orphan 发现」：机制 key 若只在 mechanism_registry 内部出现、而在
    运行时代码（services / api，排除注册表自身与 tests）中无引用，则判定为
    无外部运行时调用方。
    """
    needles = [key]
    sym = impl_ref.split(":", 1)[0].strip()
    # 机制的 impl_ref 是 file.py:line，符号即文件名，跳过；
    # 仅当符号不是 .py 文件时才作为独立检索词。
    if sym and not sym.endswith(".py"):
        needles.append(sym)
    needles = list(dict.fromkeys(needles))

    for _fname, text in file_texts:
        if any(n in text for n in needles):
            return True
    return False


def _orchestrator_wired(key: str, orch_text: str, wired_keys: set) -> bool:
    """机制是否由编排器流程接线/门控：在 PIPELINE_MECHANISM_MAP 值中，或存在
    ``is_enabled("<key>")`` 字面调用。"""
    if key in wired_keys:
        return True
    return f'is_enabled("{key}")' in orch_text


# ─────────────────────────────────────────────────────────────────────────────
# 核心：构建落地矩阵
# ─────────────────────────────────────────────────────────────────────────────

def build_landing_rows(backend_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """枚举全部 53 个机制，计算每项的运行时落地状态。

    返回行列表，字段与 artifacts/mechanism_landing_status.json 的 rows 一致。
    """
    backend_root = Path(backend_root) if backend_root else BACKEND_ROOT
    app_dir = backend_root / "app"

    # 程序化读取注册表规格（单一事实源）
    from app.services.mechanism_registry import all_mechanisms
    from app.services.learning_orchestrator import PIPELINE_MECHANISM_MAP

    wired_keys: set = set()
    for keys in PIPELINE_MECHANISM_MAP.values():
        wired_keys.update(keys)

    orch_text = ORCH_PATH.read_text(encoding="utf-8") if ORCH_PATH.is_file() else ""
    file_texts = _collect_source_texts(app_dir)

    rows: List[Dict[str, Any]] = []
    for spec in all_mechanisms():
        ext = _scan_external_ref(spec.key, spec.impl_ref, file_texts)
        orch_wired = _orchestrator_wired(spec.key, orch_text, wired_keys)
        landed = bool(ext or orch_wired)
        rows.append({
            "id": spec.id,
            "key": spec.key,
            "name_zh": spec.name_zh,
            "category": spec.category,
            "disposition": spec.disposition,
            "maturity": spec.maturity,
            "impl_ref": spec.impl_ref,
            "impl_ref_file_exists": _impl_ref_file_exists(spec.impl_ref, app_dir),
            "external_ref": ext,
            "orchestrator_wired": orch_wired,
            "landed": landed,
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="LearnFlow 机制落地审计矩阵扫描")
    ap.add_argument("--quiet", action="store_true", help="仅打印一行摘要")
    args = ap.parse_args(argv)

    rows = build_landing_rows(BACKEND_ROOT)
    landed_n = sum(1 for r in rows if r["landed"])
    orphan_n = len(rows) - landed_n

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "total": len(rows),
        "landed": landed_n,
        "orphan": orphan_n,
        "rows": rows,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS_DIR / "mechanism_landing_status.json"
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.quiet:
        print(
            f"mechanism_landing: landed={landed_n}/53 orphan={orphan_n} "
            f"(engine_classes/mechanism_units unaffected)"
        )
    else:
        print("=" * 78)
        print("LearnFlow 机制落地审计矩阵")
        print("=" * 78)
        print(f"git HEAD : {payload['git_commit']}")
        print(f"total    : {len(rows)}")
        print(f"landed   : {landed_n}  (运行时可达：有外部引用 或被编排器接线/门控)")
        print(f"orphan   : {orphan_n}  (仅引擎/文档可达，运行时不可达)")
        print("-" * 78)
        for r in rows:
            flag = "OK " if r["landed"] else "ORPH"
            print(
                f"  {flag} {r['id']} {r['key']:<28} "
                f"ext={int(r['external_ref'])} wired={int(r['orchestrator_wired'])} "
                f"maturity={r['maturity']}"
            )
        print("-" * 78)
        print(f"  JSON 输出 : {out}")
        print("=" * 78)

    return 0


if __name__ == "__main__":
    try:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):
                pass
        sys.exit(main())
    except Exception:  # noqa: BLE001 —— 顶层兜底
        import traceback
        traceback.print_exc()
        sys.exit(2)
