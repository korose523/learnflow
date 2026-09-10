"""验证「伦理审计器本身是有效的」—— 它必须既能放行合规代码, 也能抓到违规。

一个只会打印 [OK] 的审计器比没有审计器更危险: 它会给审稿人虚假的安全感。
故本文件从两个方向钉死它的有效性:

* **无假阴性**: 真的引入时长类指标时, 必须 FAIL (不是永远通过);
* **无假阳性**: docstring/注释里写「禁止使用时长」不构成违规。
  这是修复过的真实缺陷 —— 旧版审计做纯文本匹配, 把 compute_reward docstring
  中的禁用清单当成实际使用, 导致审计恒定失败且结论完全相反。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "audit_intervention_reward.py"
)


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_intervention_reward", _SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def audit():
    return _load_audit_module()


def test_audit_passes_on_real_implementation(audit):
    """对当前真实实现, 审计必须通过 (基线)。"""
    assert audit.audit_reward_source() is True


def test_no_false_negative_catches_real_duration_metric(audit):
    """★ 无假阴性: 函数体真的引用 usage_duration 时, 扫描器必须抓到。"""
    def bad_reward(s):
        usage_duration = getattr(s, "usage_duration", 0)  # 违规: 时长类指标
        return 1.0 if usage_duration > 60 else 0.0

    idents = audit._referenced_identifiers(bad_reward)
    hit = {t for i in idents for t in audit._FORBIDDEN_IN_REWARD if t in i}
    assert "usage_duration" in hit, "审计器抓不到真实的时长指标 = 形同虚设"


def test_no_false_negative_catches_dataclass_field(audit):
    """★ 无假阴性: 在信号结构上开后门 (加 duration 字段) 也要被抓到。"""
    from dataclasses import dataclass

    @dataclass
    class BadSignals:
        mastery_after: float = 0.0
        session_duration: float = 0.0  # 违规: 为时长指标留位置

    idents = audit._referenced_identifiers(BadSignals)
    hit = {t for i in idents for t in audit._FORBIDDEN_IN_REWARD if t in i}
    assert "duration" in hit


@pytest.mark.parametrize("word", ["时长", "活跃", "连胜", "留存", "粘性"])
def test_no_false_positive_on_docstring(audit, word):
    """★ 无假阳性: docstring 里声明「禁止…」不应被判为违规。

    旧版审计正是栽在这里 —— 中文禁用词只会出现在注释/docstring 中,
    文本匹配于是把「禁止声明」当成了「实际使用」。
    """
    def good_reward(s):
        """本函数禁止使用使用时长、活跃天数与连胜长度等指标。"""
        delta = s.mastery_after - s.mastery_before
        return 0.6 * delta

    idents = audit._referenced_identifiers(good_reward)
    hit = {t for i in idents for t in audit._FORBIDDEN_IN_REWARD if t in i}
    assert hit == set(), f"合规函数被误判: {hit} (docstring 含「{word}」不应触发)"


def test_comment_mention_is_not_violation(audit):
    """注释中提及禁用词同样不构成违规。"""
    def good_reward_2(s):
        # 注意: 这里绝不能引入 stickiness / retention 之类指标
        return 0.4 * (s.risk_before - s.risk_after)

    idents = audit._referenced_identifiers(good_reward_2)
    hit = {t for i in idents for t in audit._FORBIDDEN_IN_REWARD if t in i}
    assert hit == set()


def test_reward_weights_declare_forbidden_features(audit):
    """奖励权重自述里必须显式声明禁用特征, 供论文与审计引用。"""
    w = audit.describe_reward_weights()
    assert w["allowed_features"] == ["mastery_gain", "risk_drop"]
    for feat in ("usage_duration", "streak_length", "active_days", "answer_count"):
        assert feat in w["forbidden_features"]
    # 权重之和应为 1 (两个目标已配齐, 无隐藏第三项)
    assert w["w_mastery"] + w["w_health"] == pytest.approx(1.0)
