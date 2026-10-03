# -*- coding: utf-8 -*-
"""G 任务：重生成 10-20 正式提交包所需的 docx。

背景：
  1. 计划书 md 在 2026-09-23 修改过 §4.5（第二阶段被试计划表）与 §7.1（期刊口径核验后更正），
     而现 docx 生成于 09-22 19:20 —— 不同步重生成则提交的将是**不含这些更正的旧版**。
  2. 审阅表 6 要求 10-20 提交「docx 3 份」= 计划书 v1.1(韩) + 报告更正版(韩) + 因果侧识别策略文档；
     后者此前只有 md，无 docx —— 本脚本补生成。

复用 _build_tools/_md_to_docx.py 的 build_docx（含 core_properties.author，满足审阅 §2.5）。
注：python-docx 只装在系统 Python 3.11，须用该解释器运行。
"""
import os
import sys

BUILD_TOOLS = r"E:\learnflow\tools\docx_build"   # 2026-10-03: 构建工具迁出 docs/
sys.path.insert(0, BUILD_TOOLS)

from _md_to_docx import build_docx  # noqa: E402

JOBS = [
    # (md 源, docx 目标, 语言)
    (r"E:\learnflow\docs\LearnFlow_研究总档.md",
     r"E:\learnflow\docs\研究计划_韩文版.docx", "kr"),
    (r"E:\learnflow\docs\LearnFlow_研究总档.md",
     r"E:\learnflow\docs\研究计划_中文版.docx", "zh"),
    (r"E:\learnflow\docs\LearnFlow_研究总档.md",
     r"E:\learnflow\docs\研究报告_韩文版.docx", "kr"),
    (r"E:\learnflow\docs\LearnFlow_研究总档.md",
     r"E:\learnflow\docs\研究报告_中文版.docx", "zh"),
    # 审阅表 6 第三份：因果侧识别策略文档（未接触结果变量状态）
    (r"E:\learnflow\docs\因果侧识别策略.md",
     r"E:\learnflow\docs\因果侧识别策略.docx", "zh"),
]

LOG_PATH = r"E:\learnflow\results\g_build\build_log.txt"


def main():
    log = []
    ok = 0
    for src, dst, lang in JOBS:
        if not os.path.exists(src):
            log.append("ERR missing source: %s" % src)
            continue
        before_mtime = os.path.getmtime(src)
        try:
            n_p, n_t = build_docx(src, dst, lang)
            after_mtime = os.path.getmtime(dst)
            size = os.path.getsize(dst)
            log.append("OK  %s -> %s (段落=%d, 表格=%d, 字节=%d)" % (
                os.path.basename(src), os.path.basename(dst), n_p, n_t, size))
            log.append("    源 mtime=%.0f  产物 mtime=%.0f  产物>=源: %s" % (
                before_mtime, after_mtime, "是" if after_mtime >= before_mtime else "否(异常)"))
            ok += 1
        except Exception as e:
            log.append("ERR %s : %r" % (os.path.basename(src), e))

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("\n".join(log))
    print("\n完成 %d / %d" % (ok, len(JOBS)))


if __name__ == "__main__":
    main()
