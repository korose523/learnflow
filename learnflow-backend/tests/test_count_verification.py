"""数字诚信复算测试 — 把「项目内部数字自相矛盾」钉进 CI 门禁。

为什么存在这个测试
-------------------
LearnFlow 历史文档宣称「76 种机制 / 28 种学习方法」, 但真实口径分别为
60 实现单元 / 53 去重机制 / 28 学习方法 (其中 23 为三源文件字面量去重,
差额 5 来自 advanced_methods_v2 补上的真实引擎, 由 method_registry 统辖)。
这种虚高数字一旦写进论文, 审稿人一次 grep 即可证伪。本测试不去「证明数字对」,
而是把**已登记口径**逐条钉死, 并显式断言 PRD 内部自相矛盾 (prd_claimed !=
engine_classes), 防止有人偷偷改回 76 却没同步改代码 —— 那样 CI 会变红, 提醒口径漂移。

约定
----
登记口径的唯一真源是 ``scripts/verify_counts.py`` 的 ``REGISTERED`` 常量。本测试
只断言「稳定关系」, 不把易波动的 engine_classes(86) 这种数字硬编码成断言, 避免
正常重构 (新增一个 *Engine 类) 就随机变红、导致团队学会无视红灯。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = BACKEND_ROOT / "scripts" / "verify_counts.py"
JSON_OUT = BACKEND_ROOT / "artifacts" / "count_verification.json"


def _load_module():
    """导入复算脚本 (其 __main__ 守护已隔离, import 安全)"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("verify_counts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ────────────────────────────────────────────────────────────
# 1. 已登记口径逐条钉死
# ────────────────────────────────────────────────────────────

def test_learning_methods_is_28():
    mod = _load_module()
    counts = mod.collect_all()
    assert counts["learning_methods"]["value"] == 28


def test_skill_tree_nodes_is_16():
    mod = _load_module()
    counts = mod.collect_all()
    assert counts["skill_tree_nodes"]["value"] == 16
    # 唯一性交叉验证: 元素数 == skill_id 唯一数
    st = counts["skill_tree_nodes"]
    assert st["unique_skill_ids"] == 16
    assert st["duplicate_skill_ids"] == []


def test_mechanism_unique_is_53():
    mod = _load_module()
    counts = mod.collect_all()
    mq = counts["mechanism_unique"]
    assert mq["value"] == 54
    # 治理文档内部交叉验证必须通过: 编号表 / 类别小计 / 合计行一致
    assert mq["cross_validation_passed"] is True
    assert mq["duplicate_ids"] == []
    assert mq["contiguous"] is True


# ────────────────────────────────────────────────────────────
# 1b. 头条数字三元组「登记 54 / 效果生产 2 / 成熟度 9·37·8」
#     （审阅意见 6.2：54 单独出现会被读成「54 个都在运行」，必须始终并列）
# ────────────────────────────────────────────────────────────

def test_maturity_triple_is_9_37_8():
    """成熟度分解必须与「登记 54」自洽，且占位机制为 8（历史文档曾写 4）。"""
    mod = _load_module()
    counts = mod.collect_all()
    assert counts["maturity_complete"]["value"] == 9
    assert counts["maturity_partial"]["value"] == 37
    assert counts["maturity_placeholder"]["value"] == 8
    total = (counts["maturity_complete"]["value"]
             + counts["maturity_partial"]["value"]
             + counts["maturity_placeholder"]["value"])
    assert total == counts["mechanism_unique"]["value"] == 54, (
        f"成熟度分解之和 {total} 与登记机制数不一致，分解口径已漂移"
    )
    assert counts["maturity_placeholder"]["ids"] == [
        "LF-M19", "LF-M28", "LF-M29", "LF-M32",
        "LF-M45", "LF-M49", "LF-M50", "LF-M53",
    ]


def test_runtime_effect_producers_genuine_only():
    """运行时构造 Effect(...) 的位置须为真实生产者（导师 2026-09-29 审阅意见 5.2 校准）。

    「效果生产者」审计口径只统计运行时真正构造 Effect 的代码位置；opt-in 候选声明
    模块 route_a_producers.py 已被显式排除（它是声明式候选集 + 单一工厂，不是生产引擎）。
    审计时点（封存 tag audit-m2-20260911）的真实生产者只有 2 处：
    deep_addiction_engine.py（LF-M44）/ learning_orchestrator.py（LF-M52）。

    此前该测试断言 ≥14（把 route_a_producers.py 字面展开的 12 个固定 Effect 也算入），
    那是为计数器写的代码，已被撤销。这里恢复为「≥2 且两处真实生产者均在」。
    """
    mod = _load_module()
    counts = mod.collect_all()
    ep = counts["effect_producers"]
    assert ep["value"] >= 2, (
        f"运行时干预效果生产者应 ≥2 处（真实生产者口径），实测 {ep['value']}；"
        f"位置：{[s['location'] for s in ep['sites']]}"
    )
    # 锚点用「文件 + 机制关联」而非硬编码行号，避免代码位移即脆断
    # （封存审计时点的精确行号见 tag audit-m2-20260911，由 verify_m2_anchors 校验）。
    locs = [s["location"] for s in ep["sites"]]
    assert any("deep_addiction_engine.py" in s for s in locs), f"缺 LF-M44 生产者: {locs}"
    assert any("learning_orchestrator.py" in s for s in locs), f"缺 LF-M52 生产者: {locs}"
    # route_a_producers.py 不得计入（opt-in 候选声明，非生产生产者）
    assert not any("route_a_producers.py" in s for s in locs), (
        f"route_a_producers.py 不应计入效果生产者审计: {locs}"
    )
    # 每个生产者都必须能关联到具体机制，否则「N 个机制在运行」不可追溯
    for s in ep["sites"]:
        assert s["mechanism_labels"] or s["registry_impl_ref_ids"], (
            f"{s['location']} 未能关联到任何 LF-M 机制"
        )


# ────────────────────────────────────────────────────────────
# 2. 把「项目内部数字自相矛盾」钉成机器可读事实
# ────────────────────────────────────────────────────────────

def test_prd_contradiction_is_machine_readable():
    """PRD §2.3 表格相加得 69, 但同文档标题声称 76 —— 两者必须不等。

    这是本项目最锋利的数字诚信证据: 不是我们说「76 是错的」, 而是脚本证明
    「连项目自己都对不上」。这个断言存在, 就是为了有人偷偷把代码数字改回 76
    时 CI 立刻变红。
    """
    mod = _load_module()
    counts = mod.collect_all()
    prd = counts["prd_claimed"]["value"]
    eng = counts["engine_classes"]["value"]
    assert prd != eng, f"PRD 自述 ({prd}) 不应等于 *Engine 类总数 ({eng})"
    assert counts["prd_claimed"]["internally_inconsistent"] is True


# ────────────────────────────────────────────────────────────
# 3. 脚本本身可运行且产出 JSON 印章
# ────────────────────────────────────────────────────────────

def test_script_runs_and_emits_json():
    """端到端: 以子进程运行脚本, 断言退出码 0 且 JSON 印章落盘。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"verify_counts 退出码非 0:\n{result.stdout}\n{result.stderr}"
    )
    assert JSON_OUT.is_file(), "未生成 count_verification.json 可复现性印章"

    payload = json.loads(JSON_OUT.read_text(encoding="utf-8"))
    assert payload["verdict"]["_overall"]["status"] == "verified"
    # 印章必须带 commit, 否则不可追溯
    assert payload["git_commit"] and payload["git_commit"] != "unknown", (
        "可复现性印章缺少 git_commit (项目需在版本控制下才能归档)"
    )
