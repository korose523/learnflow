#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""M2 静态审计的时点锚点核验（零依赖，只读）。

背景（审阅意见 6.3）：
    M2 是一篇静态审计稿件，其全部证据是代码锚点（`file:line` + 断言行内容）。
    但被审计仓库在审计之后继续前进，工作树已不等于审计时点，于是"审计时点
    不可复现"对审计型论文是致命的。

本脚本的做法：
    1. 用 `git tag audit-m2-20260911` 把审计基线树封存（tag 指向
       commit 8a328430d36860043f3bf80e8e0bf2a82edd2ecd，2026-09-11）；
    2. 用 `git show <tag>:<path>` 从**封存树**（而非当前工作树）读出每一处
       锚点的上下文行，逐条断言 M2 稿件中被引用的命题；
    3. 把结果落盘为 `results/m2/m2_anchor_verification.json`。

断言清单（全部来自 M2 正文，全部可在封存树上复核）：
    A1  全仓库 `Effect(` 构造点恰好 2 处
    A2  LF-M44 在 deep_addiction_engine.py:296 构造 Effect，且 user_visible=True
        / health_critical=False
    A3  LF-M52 在 learning_orchestrator.py:986 构造 Effect，且 user_visible=False
        / health_critical=True
    A4  mechanism_arbitrator.py 的 _DIRECTION 表登记 12 个机制（9 approach
        + 3 withdraw），故类型 I 静态潜在对 = 9 x 3 = 27
    A5  方向消解的比较范围只在 user_visible 的效果之间（含 LF-M52 则违反）
    A6  健康一票否决层存在（第 1 层）

用法：
    python results/m2/verify_m2_anchors.py            # 人读输出
    python results/m2/verify_m2_anchors.py --quiet    # 仅一行结论
退出码：0 = 全部通过；1 = 有断言失败；2 = 环境不满足（无 git / 无 tag）。
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

TAG = "audit-m2-20260911"
BASELINE_COMMIT = "8a328430d36860043f3bf80e8e0bf2a82edd2ecd"

SRC = "learnflow-backend/app/services"
PATHS = {
    "engine": f"{SRC}/deep_addiction_engine.py",
    "orchestrator": f"{SRC}/learning_orchestrator.py",
    "arbitrator": f"{SRC}/mechanism_arbitrator.py",
}

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_JSON = os.path.join(REPO_ROOT, "results", "m2", "m2_anchor_verification.json")


def _git(*args: str) -> str:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git %s 失败：%s"
            % (" ".join(args), proc.stderr.decode("utf-8", "replace").strip())
        )
    return proc.stdout.decode("utf-8", "replace")


def _show(tag: str, path: str) -> list[str]:
    """取出封存树中被审计文件的全部行（1-based，索引 0 对应第 1 行）。"""
    return _git("show", f"{tag}:{path}").split("\n")


def _resolve_tag() -> str:
    tags = _git("tag", "-l", TAG).strip()
    if tags != TAG:
        raise RuntimeError(
            f"未找到审计时点 tag {TAG}；请先运行："
            f"git tag -a {TAG} {BASELINE_COMMIT} -m '...'"
        )
    return TAG


def _scan_effect_producers(files: dict[str, list[str]]) -> list[dict]:
    """A1/A2/A3：找出全部 `Effect(` 构造点及其机制 ID 与两个布尔属性。"""
    hits: list[dict] = []
    for key, lines in files.items():
        for idx, line in enumerate(lines, start=1):
            if "Effect(" not in line or line.lstrip().startswith("#"):
                continue
            # 构造点与属性字段可能相隔最多约 15 行（payload 多行），窗口取 20 行。
            window = "\n".join(lines[idx - 1 : idx + 20])
            mech = re.search(r'mechanism_id\s*=\s*"([^"]+)"', window)
            vis = re.search(r"user_visible\s*=\s*(True|False)", window)
            crit = re.search(r"health_critical\s*=\s*(True|False)", window)
            hits.append(
                {
                    "file": key,
                    "line": idx,
                    "mechanism_id": mech.group(1) if mech else None,
                    "user_visible": (vis.group(1) == "True") if vis else None,
                    "health_critical": (crit.group(1) == "True") if crit else None,
                    "line_text": line.strip(),
                }
            )
    return hits


def _parse_direction_table(arb_lines: list[str]) -> dict[str, str]:
    """A4：解析 _DIRECTION 字典的键值对。"""
    table: dict[str, str] = {}
    inside = False
    for line in arb_lines:
        if "_DIRECTION" in line and "{" in line:
            inside = True
            continue
        if inside:
            if "}" in line:
                break
            for mid, direction in re.findall(r'"(LF-M\d+)"\s*:\s*"(\w+)"', line):
                table[mid] = direction
    return table


def _find_compare_scope(arb_lines: list[str]) -> dict:
    """A5：找到方向消解的比较范围（是否用 user_visible 过滤）。"""
    joined = "\n".join(arb_lines)
    m = re.search(
        r"user_visible[^\n]{0,120}", joined
    )
    return {"found_user_visible_filter": bool(m), "snippet": m.group(0) if m else None}


def _find_health_override(arb_lines: list[str]) -> dict:
    """A6：找到第 1 层健康一票否决（health_critical 相关分支）。"""
    joined = "\n".join(arb_lines)
    m = re.search(r"health_critical[^\n]{0,120}", joined)
    return {"found_health_override": bool(m), "snippet": m.group(0) if m else None}


def main() -> int:
    quiet = "--quiet" in sys.argv

    try:
        tag = _resolve_tag()
        files = {key: _show(tag, path) for key, path in PATHS.items()}
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"verify_m2_anchors: 环境不满足 — {exc}")
        return 2

    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    producers = _scan_effect_producers(files)
    check(
        "A1 全仓库 Effect( 构造点恰为 2 处",
        len(producers) == 2,
        f"实际 {len(producers)} 处："
        + ", ".join(f"{p['file']}.py:{p['line']}({p['mechanism_id']})" for p in producers),
    )

    m44 = next((p for p in producers if p["mechanism_id"] == "LF-M44"), None)
    check(
        "A2 LF-M44 在 deep_addiction_engine.py:296 构造 Effect（visible=True / health=False）",
        bool(m44)
        and m44["file"] == "engine"
        and m44["line"] == 296
        and m44["user_visible"] is True
        and m44["health_critical"] is False,
        repr(m44),
    )

    m52 = next((p for p in producers if p["mechanism_id"] == "LF-M52"), None)
    check(
        "A3 LF-M52 在 learning_orchestrator.py:986 构造 Effect（visible=False / health=True）",
        bool(m52)
        and m52["file"] == "orchestrator"
        and m52["line"] == 986
        and m52["user_visible"] is False
        and m52["health_critical"] is True,
        repr(m52),
    )

    direction = _parse_direction_table(files["arbitrator"])
    n_app = sum(1 for v in direction.values() if v == "approach")
    n_wd = sum(1 for v in direction.values() if v == "withdraw")
    check(
        "A4 _DIRECTION 登记 12 个机制（9 approach + 3 withdraw），静态潜在对 = 27",
        len(direction) == 12 and n_app == 9 and n_wd == 3 and n_app * n_wd == 27,
        f"total={len(direction)} approach={n_app} withdraw={n_wd} pairs={n_app * n_wd}",
    )
    check(
        "A4b LF-M44 在方向表中为 approach、LF-M52 为 withdraw",
        direction.get("LF-M44") == "approach" and direction.get("LF-M52") == "withdraw",
        f"LF-M44={direction.get('LF-M44')}, LF-M52={direction.get('LF-M52')}",
    )

    scope = _find_compare_scope(files["arbitrator"])
    check(
        "A5 方向消解的比较范围以 user_visible 过滤（故 LF-M52 从不进入方向比较）",
        scope["found_user_visible_filter"],
        scope["snippet"] or "未找到 user_visible 过滤",
    )

    health = _find_health_override(files["arbitrator"])
    check(
        "A6 第 1 层健康一票否决存在（health_critical 分支）",
        health["found_health_override"],
        health["snippet"] or "未找到 health_critical 分支",
    )

    failed = [c for c in checks if not c["ok"]]
    payload = {
        "generated_by": "results/m2/verify_m2_anchors.py",
        "audit_tag": tag,
        "baseline_commit": BASELINE_COMMIT,
        "anchor_source": "git show <tag>:<path>（封存树，非当前工作树）",
        "checked": len(checks),
        "failed": len(failed),
        "verdict": "verified" if not failed else "FAILED",
        "checks": checks,
        "effect_producers": producers,
        "direction_table": direction,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with io.open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    if quiet:
        print(
            f"verify_m2_anchors: {payload['verdict']} "
            f"(tag={tag}, checked={len(checks)}, failed={len(failed)})"
        )
    else:
        for c in checks:
            print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['check']}")
            print(f"         {c['detail']}")
        print(
            f"verify_m2_anchors: {payload['verdict']} "
            f"(tag={tag}, checked={len(checks)}, failed={len(failed)})"
        )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
