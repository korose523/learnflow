# -*- coding: utf-8 -*-
"""把报告中 Junyi 规模的近似值替换为权威精确值（中韩两版同步）。"""
import io

EDITS = [
    # (文件, 旧串, 新串)
    (
        r"E:\learnflow\docs\研究计划与报告\研究报告_中文版.md",
        "在 Junyi（1,234 练习、16,210,000 余条交互、无自陈反馈）上同向复现：",
        "在 Junyi（1,234 练习、1,621 万条交互、无自陈反馈）上同向复现：",
    ),
    (
        r"E:\learnflow\docs\研究计划与报告\研究报告_韩文版.md",
        "Junyi(1,234개 연습, 16,210,000여 건 상호작용, 자기보고 피드백 없음)에서 동일 방향으로 재현된다.",
        "Junyi(1,234개 연습, 약 1,621만 건 상호작용, 자기보고 피드백 없음)에서 동일 방향으로 재현된다.",
    ),
    (
        r"E:\learnflow\docs\研究计划与报告\研究报告_中文版.md",
        "把动作空间重建为\"同一知识 strand 内按专家难度分组的真实练习\"。专家难度标签的经验成功率严格单调：",
        "把动作空间重建为\"同一知识 strand 内按专家难度分组的真实练习\"。Junyi 的完整规模为 "
        "**16,217,311 条交互 / 72,758 名用户 / 1,326 个练习**，动作空间的重建使用其中的专家标注子集。"
        "专家难度标签的经验成功率严格单调：",
    ),
    (
        r"E:\learnflow\docs\研究计划与报告\研究报告_韩文版.md",
        "동일 지식 strand 내에서 전문가 난이도로 그룹화한 실제 연습\"으로 재구축하였다. 전문가 난이도 라벨의 경험적 성공률은 엄격히 단조이다.",
        "동일 지식 strand 내에서 전문가 난이도로 그룹화한 실제 연습\"으로 재구축하였다. "
        "Junyi의 전체 규모는 **16,217,311건 상호작용 / 72,758명 사용자 / 1,326개 연습**이며, "
        "행동 공간 재구축에는 그중 전문가 라벨이 있는 부분집합을 사용하였다. "
        "전문가 난이도 라벨의 경험적 성공률은 엄격히 단조이다.",
    ),
]

for path, old, new in EDITS:
    s = io.open(path, "r", encoding="utf-8", newline="").read()
    c = s.count(old)
    assert c == 1, "anchor count=%d in %s :: %s" % (c, path, old[:50])
    s2 = s.replace(old, new, 1)
    assert s2 != s
    io.open(path, "w", encoding="utf-8", newline="").write(s2)
    print("PATCHED  %s" % path.split("\\")[-1])

print()
for p in (r"E:\learnflow\docs\研究计划与报告\研究报告_中文版.md",
          r"E:\learnflow\docs\研究计划与报告\研究报告_韩文版.md"):
    t = io.open(p, "r", encoding="utf-8").read()
    print("%s : 16,217,311=%s  72,758=%s  1,326=%s  16,210,000=%s" % (
        p.split("\\")[-1],
        "16,217,311" in t, "72,758" in t, "1,326" in t, "16,210,000" in t))
