# -*- coding: utf-8 -*-
"""在本地记录中检索 Zenodo API token。

安全约定：
  - **不把 token 明文打印到输出**（仅打印掩码与前若干字符的指纹）；
  - 找到后把 token 写入**仓库外**的临时文件（os tempdir），供后续脚本读取，
    避免 token 进入仓库、日志或任何交付物；
  - 本脚本不发起任何网络请求。
"""
import os
import re
import tempfile

# 注意：不扫 ~/.workbuddy 全树（plugins/marketplaces 缓存极大，会超时），
# 只取其中的 MEMORY.md 单文件。
ROOTS = [
    r"E:\learnflow",
    r"C:\Users\mac\WorkBuddy\2026-09-22-18-14-08\.workbuddy",
]

# 额外单文件（不走 os.walk）
EXTRA_FILES = [
    os.path.expanduser(r"~\.workbuddy\MEMORY.md"),
]

SKIP_DIRS = {".venv", ".venv_new", "node_modules", "data", "data_backup", ".git",
             "__pycache__", "external", ".pytest_cache", ".pytest_tmp", "build",
             "dist", "plugins", "marketplaces", "cache", "binaries", "logs"}

TEXT_EXT = {".md", ".txt", ".json", ".py", ".env", ".cfg", ".ini",
            ".yaml", ".yml", ".sh", ".ps1", ".log", ".cff", ".bak"}

# token 赋值形态：ZENODO_TOKEN=xxx / zenodo_token: "xxx"
P_ASSIGN = re.compile(
    r'(?i)\bzenodo[ _\-]?token\b\s*[=:]\s*["\']?([A-Za-z0-9_\-\.]{16,})["\']?')
# 行内含 zenodo 且出现长串（裸 token）
P_INLINE = re.compile(
    r'(?i)(zenodo[^A-Za-z0-9]{0,40})([A-Za-z0-9_\-]{32,})')

OUT = os.path.join(tempfile.gettempdir(), "lf_zenodo_token.txt")


def mask(t):
    if len(t) <= 8:
        return "*" * len(t)
    return t[:4] + "*" * 10 + t[-2:]


def main():
    hits = []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in TEXT_EXT:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                for m in P_ASSIGN.finditer(content):
                    hits.append((p, m.group(1), "assign"))
                for m in P_INLINE.finditer(content):
                    tok = m.group(2)
                    # 排除明显的 DOI / URL / 哈希噪声
                    if tok.lower().startswith("10.") or "/" in tok:
                        continue
                    hits.append((p, tok, "inline"))

    # 扫描额外单文件
    for p in EXTRA_FILES:
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        for m in P_ASSIGN.finditer(content):
            hits.append((p, m.group(1), "assign"))
        for m in P_INLINE.finditer(content):
            tok = m.group(2)
            if tok.lower().startswith("10.") or "/" in tok:
                continue
            hits.append((p, tok, "inline"))

    if not hits:
        print("NOT_FOUND: 未在扫描范围内发现 Zenodo token。")
        return 1

    # 去重（按 token 值）
    seen = {}
    for p, tok, kind in hits:
        seen.setdefault(tok, []).append((p, kind))

    print("FOUND %d 个候选 token：" % len(seen))
    best = None
    for tok, locs in seen.items():
        print("  - 掩码=%s  长度=%d  出现处=%d" % (mask(tok), len(tok), len(locs)))
        for p, kind in locs[:3]:
            print("      %s  [%s]" % (p, kind))
        # 优先取 "assign" 形态（显式命名），其次较长者
        score = (100 if any(k == "assign" for _, k in locs) else 0) + len(tok)
        if best is None or score > best[0]:
            best = (score, tok)

    token = best[1]
    try:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(token)
        print("\n已将 token 写入仓库外临时文件（不打印明文）: %s" % OUT)
        print("指纹(掩码): %s" % mask(token))
    except Exception as e:
        print("写入临时文件失败: %r" % e)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
