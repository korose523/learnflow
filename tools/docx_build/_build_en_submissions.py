# -*- coding: utf-8 -*-
"""从 docs/ 下已修订的英文稿确定性重建 output/ 中的投稿 docx（原地替换）。

背景（2026-10-04）
------------------
output/20260928-* 下的 8 份 docx 构建于 2026-09-28，**早于 09-29 第二次审阅**，
因此既不含本轮任何整改，也仍写着已被取代的 95.5%（现为 2,000 次重抽样下的
94.1% / 5.95%，95% 集 {0.25, 0.20}）。10-20 要交的就是这批 docx，故须重建。

与 09-28 那次的差别
--------------------
09-28 走的是「md → md2academic HTML → 插件 html_to_docx」三段链；本脚本改用项目内
自带的确定性转换器 `_md_to_docx.py`（docs/ 下 4 份中韩交付件即由它生成），
好处是：不依赖插件缓存与外部 venv，任何机器装上 python-docx 都能一键重建，
且结果可复算。代价是不再经过学术版式 HTML 中间层，排版比 09-28 那版朴素。

源稿件已内嵌作者块与 AI 使用披露（grep 已核验），故无需外部注入。

用法（仓库根目录）：
    python tools/docx_build/_build_en_submissions.py
    python tools/docx_build/_build_en_submissions.py --check   # 只校验不写盘
"""
from __future__ import annotations

import argparse
import importlib.util as ilu
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DOCS = os.path.join(REPO, "docs")


def _load_converter():
    spec = ilu.spec_from_file_location(
        "_md_to_docx", os.path.join(HERE, "_md_to_docx.py"))
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# (源 md 相对 docs/, 输出 docx 相对 output/, 语言)
JOBS = [
    ("M1_submission_EN.md", "en",
     "20260928-en-submissions/M1/stage3/M1_难度可公度性与最优错误率_EN_终稿.docx"),
    ("M1_submission_EN_compressed.md", "en",
     "20260928-en-submissions/M1c/stage3/M1_难度可公度性与最优错误率_压缩投稿版_EN_终稿.docx"),
    ("M2_submission_EN.md", "en",
     "20260928-en-submissions/M2/stage3/M2_多干预并存学习系统的冲突结构审计_EN_终稿.docx"),
    ("M2_submission_EN_compressed.md", "en",
     "20260928-en-submissions/M2c/stage3/M2_多干预并存学习系统的冲突结构审计_压缩投稿版_EN_终稿.docx"),
    ("M3_submission_EN_compressed.md", "en",
     "20260928-en-submissions/M3c/stage3/M3_有序难度决策与大模型先验边界_压缩投稿版_EN_终稿.docx"),
    ("M4_submission_EN.md", "en",
     "20260928-en-submissions/M4/stage3/M4_信度结构化组合难度估计_EN_终稿.docx"),
    ("M3_submission_EN.md", "en",
     "20260928-m3-final-docx/stage3/M3_有序难度决策与大模型先验边界_EN_终稿.docx"),
    ("M3_有序难度决策与大模型先验边界_完整稿.md", "zh",
     "20260928-m3-final-docx/stage3/M3_有序难度决策与大模型先验边界_终稿.docx"),
]

# 重建后必须出现的新值 / 必须消失的旧值（M1 系稿件）
_MUST_HAVE = ("94.1",)
_MUST_NOT_HAVE = ("rerun pending",)


def main() -> int:
    ap = argparse.ArgumentParser(description="重建 output/ 投稿 docx")
    ap.add_argument("--check", action="store_true", help="只校验源与目标，不写盘")
    args = ap.parse_args()

    conv = _load_converter()
    rc = 0
    for src_md, lang, out_rel in JOBS:
        sp = os.path.join(DOCS, src_md)
        dp = os.path.join(REPO, "output", out_rel)
        if not os.path.isfile(sp):
            print("ERR 源缺失: %s" % src_md)
            rc = 1
            continue
        if args.check:
            print("CHECK %-46s -> %s (%s)" % (src_md, out_rel, lang))
            continue
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        np_, nt_ = conv.build_docx(sp, dp, lang)
        size = os.path.getsize(dp)
        print("OK   %-46s -> %s  段落=%d 表格=%d  %d B"
              % (src_md, os.path.basename(out_rel), np_, nt_, size))
    return rc


if __name__ == "__main__":
    sys.exit(main())
