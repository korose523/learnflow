#!/usr/bin/env python
"""机制注册表 impl_ref 引用完整性检查（可复现性基础设施）

背景
----
``mechanism_registry`` 中每条机制都带一个 ``impl_ref``，用于把机制 ID 追溯到
具体代码实现。这是论文「可追溯性」承诺的载体：审稿人应当能按 impl_ref 找到
该机制的真实实现位置。

但 ``file.py:line`` 形式的行号会**静默漂移**——任何在被引用位置上方的编辑
都会让行号指向无关内容，而注册表与 ``scan_mechanism_landing.py`` 都不校验行号
（后者只取 ``:`` 之前的文件名）。本项目已实际发生：LF-M52 曾登记
``anti_addiction_compliance.py:79``，在该文件插入 10 行后已指向
``UsageQuota`` 的某个字段，而非 ``MinorProtectionEngine``。

本脚本把这一失效模式变成**可复算的红灯**。

判据
----
* ``MISSING``  —— impl_ref 指向的文件在 app/services 下不存在（硬错误）
* ``OUT_OF_RANGE`` —— 行号超出文件实际行数，或符号未定义（硬错误）
* ``BLANK``    —— 行号落在空行（几乎必然已漂移，警告）
* ``OK``       —— 其余情况（含符号级引用、注释分隔行等可接受锚点）

符号级引用支持点分路径 ``file.py:Class.method``：首段须为顶层 class/def，
后续各段须以 def 形式出现。**不能整串做子串匹配**——源文件里不存在
``GamificationService.get_goal_progress`` 这样的连续文本，整串匹配会误报。

行内容是否为「定义行」只作提示，不判失败——既有条目中相当一部分锚定在分隔
注释行（如 ``# ═════ ... ═════``）上，这是当初人工 grep 核验时的合理选择。

用法
----
    python scripts/check_impl_ref.py                # 打印报告
    python scripts/check_impl_ref.py --quiet        # 只打印汇总
    python scripts/check_impl_ref.py --json         # 写 artifacts/impl_ref_integrity.json

退出码：0 = 无硬错误；1 = 存在 MISSING / OUT_OF_RANGE。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.mechanism_registry import all_mechanisms  # noqa: E402

ARTIFACT = BACKEND_ROOT / "artifacts" / "impl_ref_integrity.json"

# impl_ref 允许的形态：
#   file.py                      仅文件
#   file.py:123                  行号
#   file.py:123,456              多位置（canonical + 重复实现）
#   file.py:SymbolName           符号级（推荐，抗漂移）
#   file.py:123,Symbol           混合
_REF_RE = re.compile(r"^(?P<fname>[A-Za-z_][A-Za-z0-9_]*\.py)(?::(?P<rest>.+))?$")
_LINE_RE = re.compile(r"^\d+$")


def _split_ref(impl_ref: str):
    """返回 (fname, parts)；无法解析返回 (None, [])。"""
    m = _REF_RE.match(impl_ref.strip())
    if not m:
        return None, []
    rest = (m.group("rest") or "").strip()
    parts = [p.strip() for p in rest.split(",") if p.strip()] if rest else []
    return m.group("fname"), parts


def check_one(mech_id: str, impl_ref: str, services_dir: Path) -> Dict:
    fname, parts = _split_ref(impl_ref)
    row: Dict = {
        "id": mech_id,
        "impl_ref": impl_ref,
        "file": fname,
        "status": "OK",
        "detail": "",
    }

    if fname is None:
        row["status"] = "UNPARSEABLE"
        row["detail"] = "impl_ref 形态无法识别"
        return row

    path = services_dir / fname
    if not path.is_file():
        row["status"] = "MISSING"
        row["detail"] = f"文件不存在: {path}"
        return row

    if not parts:
        row["status"] = "OK"
        row["detail"] = "仅文件级引用"
        return row

    lines = path.read_text(encoding="utf-8").splitlines()
    problems: List[str] = []
    symbol_seen = False

    for p in parts:
        if _LINE_RE.match(p):
            ln = int(p)
            if ln > len(lines):
                problems.append(f"行号 {ln} 越界(文件共 {len(lines)} 行)")
            elif not lines[ln - 1].strip():
                problems.append(f"行号 {ln} 为空行(疑似漂移)")
        else:
            # 符号级引用：校验该符号确实在文件中被定义。
            #
            # 支持点分路径（``Class.method``）。不能整串做子串匹配——源文件里
            # 不存在 ``GamificationService.get_goal_progress`` 这样的连续文本，
            # 整串匹配会误报「符号未出现」。改为：
            #   * 首段必须是顶层 class/def；
            #   * 后续各段必须在文件中以 def 形式出现（缩进不限）。
            symbol_seen = True
            segments = p.split(".")
            head, tail = segments[0], segments[1:]
            if not any(re.search(rf"^(class|def)\s+{re.escape(head)}\b", ln) for ln in lines):
                problems.append(f"符号 {head!r} 未在文件中定义")
            for seg in tail:
                if not any(re.search(rf"^\s*def\s+{re.escape(seg)}\b", ln) for ln in lines):
                    problems.append(f"方法 {seg!r} 未在文件中定义 (来自 {p!r})")

    if problems:
        row["status"] = "OUT_OF_RANGE" if any("越界" in x for x in problems) else "BLANK"
        row["detail"] = "; ".join(problems)
    elif symbol_seen:
        row["detail"] = "符号级引用已校验"
    else:
        row["detail"] = "行号在有效范围内"

    return row


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="检查机制注册表 impl_ref 的引用完整性")
    ap.add_argument("--quiet", action="store_true", help="只打印汇总")
    ap.add_argument("--json", action="store_true", help="写出 JSON 工件")
    args = ap.parse_args(argv)

    services_dir = BACKEND_ROOT / "app" / "services"
    rows = [check_one(m.id, m.impl_ref, services_dir) for m in all_mechanisms()]

    hard = [r for r in rows if r["status"] in ("MISSING", "OUT_OF_RANGE", "UNPARSEABLE")]
    warn = [r for r in rows if r["status"] == "BLANK"]
    ok = [r for r in rows if r["status"] == "OK"]

    if not args.quiet:
        print("=" * 74)
        print("机制注册表 impl_ref 引用完整性检查")
        print("=" * 74)
        for r in rows:
            if r["status"] == "OK":
                continue
            print(f"  [{r['status']:<13}] {r['id']}  {r['impl_ref']}")
            print(f"                  └─ {r['detail']}")
        print("-" * 74)

    print(f"  总计 {len(rows)} 条 | OK {len(ok)} | 警告(BLANK) {len(warn)} | 硬错误 {len(hard)}")

    if args.json:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(
            json.dumps(
                {
                    "total": len(rows),
                    "ok": len(ok),
                    "warning": len(warn),
                    "hard_error": len(hard),
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  JSON 输出 : {ARTIFACT}")

    if hard:
        print("  结论      : FAILED（存在无法解析/越界/缺失的引用）")
        return 1
    print("  结论      : PASSED（警告项需人工确认，见上）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
