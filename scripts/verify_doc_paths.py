#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_doc_paths.py —— 「死引用门禁」：校验版本控制内文件对 docs/ 下目标的引用是否真实存在。

背景（2026-10-02）：本轮暴露了一类无门禁可拦的错误——脚本/文档里指向一个**已不存在**的
路径（例如某个内部工作文档被撤出公开仓库后，别处仍写着 `docs/<name>.md` 的引用）。
既有的两个跨文档门禁只核对**数字**口径，对「路径是否指向真实文件」完全无感。

本门禁扫描 `git ls-files` 中的 `*.py` / `*.sh` / `*.mjs` / `*.md`，抽取形如
`docs/**.md` 与 `docs/**.docx` 的路径字面量，逐个 `os.path.isfile` 校验；
**任一不存在即 exit 1**，并打印 `文件:行号 → 被引路径`。

设计取舍：
  * 用**通用版**而非「19 个被撤文件黑名单版」——把内部文档名写进脚本等于把它们留在公开仓库；
    通用版还能顺带拦住未来任何新增的死引用。
  * 只抽取 `docs/` 目标；对 `results/` 等非 docs 目标的引用不抽取、不校验
    （含 `docs/` 内反向引用 `results/` 的情形）。
  * 不区分引用是出自 `docs/` 还是 `results/`——两侧都查，才算真门禁。
  * 一个 `docs/x.md` 字面量按两种解释试解：相对**仓库根**（代码注释里的常见写法）与
    相对**引用文件所在目录**（markdown 链接的常见写法），任一命中即视为有效。
  * 省略号简写（如 `docs/...机制治理方案.md`）不是真实路径，跳过。
  * 本文件自身（`scripts/verify_doc_paths.py`）不参与扫描：其 docstring 中的
    `docs/x.md`、`docs/research_tooling.md` 是说明性示例而非真实引用，若纳入扫描
    会永久自我 FAIL。这是唯一的自我豁免，且只豁免本文件一个文件。

排除项（理由见下）：
  * `output/`          —— 构建产物中间件，可重建，且已在 .gitignore（提交时 git rm --cached）；
  * `.venv/`、`venv/`、`.venv_new/` —— 第三方/虚拟环境，非本项目产物；
  * `node_modules/`    —— 第三方依赖；
  * `data/`、`data_backup/` —— 上游数据集，已 gitignore，非本项目产物；
  * 已 gitignore / 未跟踪的路径 —— `git ls-files` 天然排除。

用法（仓库根目录执行，纯标准库）：
    python scripts/verify_doc_paths.py
    python scripts/verify_doc_paths.py --root /path/to/repo
退出码：0 = 所有 docs/ 引用均指向真实文件；1 = 存在死引用。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from typing import List, Tuple

_EXTS = (".py", ".sh", ".mjs", ".md")

# 只扫描这些前缀之外的文件（见模块 docstring 的「排除项」）
_SKIP_PREFIXES = (
    "output/",
    ".venv/", ".venv_new/", "venv/",
    "node_modules/",
    "data/", "data_backup/",
)

# 本文件自身：docstring 里的 docs/ 路径是说明性示例，不是真实引用（见 docstring「排除项」）。
_SELF_RELPATH = "scripts/verify_doc_paths.py"

# 抽取 `docs/<...>.md|.docx`。字符类限于：字母/数字/下划线/连字符/点/斜杠/汉字。
# 负向后顾 (?<![/\w]) 避免误匹配 URL 或更长路径中的 `.../docs/x.md`（只认独立出现的 docs/ 引用）。
DOC_REF_RE = re.compile(r"(?<![/\w])docs/[A-Za-z0-9_\-./\u4e00-\u9fff]+\.(?:md|docx)")


def _resolves(root: str, rel_file: str, ref: str) -> bool:
    """ref 是否存在：分别按「相对仓库根」与「相对引用文件所在目录」两种解释试解。

    同一段 `docs/x.md` 在代码注释里通常指仓库根，在 markdown 链接里通常指同目录
    （如 learnflow-backend/README.md 里的 `docs/research_tooling.md` 实指
    learnflow-backend/docs/research_tooling.md），任一解释命中即视为有效。
    """
    bases = (root, os.path.join(root, os.path.dirname(rel_file)))
    return any(os.path.isfile(os.path.normpath(os.path.join(b, ref))) for b in bases)


def _repo_root(explicit: str | None) -> str:
    if explicit:
        return os.path.abspath(explicit)
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8", "replace").strip() or os.getcwd()
    except (OSError, subprocess.CalledProcessError):
        # 退化：脚本位于 <root>/scripts/ 下
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tracked_files(root: str) -> List[str]:
    """返回版本控制内的候选文件（相对 root 的正斜杠路径）。"""
    try:
        raw = subprocess.check_output(
            ["git", "-C", root, "ls-files", "-z"], stderr=subprocess.DEVNULL)
        files = [p for p in raw.decode("utf-8", "replace").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        files = []
    out: List[str] = []
    for f in files:
        if not f.endswith(_EXTS):
            continue
        if f.startswith(_SKIP_PREFIXES):
            continue
        out.append(f)
    return out


def scan(root: str) -> Tuple[List[Tuple[str, int, str]], int]:
    """返回 (死引用列表[(文件,行号,路径)], 扫描文件数)。"""
    bad: List[Tuple[str, int, str]] = []
    files = _tracked_files(root)
    for rel in files:
        if rel == _SELF_RELPATH:
            continue  # 自身 docstring 含说明性示例路径，豁免（见 docstring）
        abspath = os.path.join(root, rel)
        try:
            with open(abspath, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue  # 二进制或不可读，跳过
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in DOC_REF_RE.finditer(line):
                ref = m.group(0)
                if "..." in ref:
                    continue  # 省略号简写（如 docs/...机制治理方案.md）不是真实路径
                if "git show" in line:
                    # `git show <rev>:path` 指向 git 历史而非工作树：被引文件可能
                    # 已不在工作树（如已删除文档的 v1 恢复命令），属历史引用，豁免。
                    continue
                if not _resolves(root, rel, ref):
                    bad.append((rel, lineno, ref))
    return bad, len(files)


def main() -> int:
    ap = argparse.ArgumentParser(description="死引用门禁：docs/ 路径引用存在性校验")
    ap.add_argument("--root", help="仓库根目录（缺省用 git rev-parse --show-toplevel）")
    args = ap.parse_args()

    root = _repo_root(args.root)
    bad, n_files = scan(root)

    print(f"扫描 {n_files} 个版本控制内文件（*.py/*.sh/*.mjs/*.md）……")
    if bad:
        print(f"[FAIL] 发现 {len(bad)} 处指向不存在 docs/ 目标的死引用：")
        for rel, lineno, ref in bad:
            print(f"  {rel}:{lineno} → {ref}")
        print("结论: FAIL   退出码 1")
        return 1
    print("结论: PASS   退出码 0（所有 docs/ 引用均指向真实文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
