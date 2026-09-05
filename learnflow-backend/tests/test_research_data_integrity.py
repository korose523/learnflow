"""研究数据完整性回归测试

本项目要从 K12 产品转型为博士论文研究平台，代码产出的每个值都可能成为论文
中的观测。因此"静默失效"比"崩溃"更危险——崩溃会被立刻发现，静默失效会让
错误数据看起来完全正常。

本文件冻结三处已修复的静默失效：

* 审计写入失败无计数  → audit_logs 是证据链，完整性必须可测量
* 学习方法提示兜底无标记 → 兜底值与真实推荐同形，会系统性污染实验变量
* next-task 异常一律 404 → 编程错误与"无匹配题目"不可区分
"""
import pytest

from app.models.analytics import AuditKind
from app.services.audit import (
    get_audit_stats,
    reset_audit_stats,
    write_audit,
)
from app.services.feedback_service import FeedbackService


class _FailingSession:
    """模拟写入失败的数据库会话。"""

    def __init__(self, exc=None):
        self._exc = exc or RuntimeError("simulated DB failure")
        self.added = []

    def add(self, _obj):
        self.added.append(_obj)

    async def flush(self):
        raise self._exc


class _OkSession:
    def __init__(self):
        self.added = []

    def add(self, _obj):
        self.added.append(_obj)

    async def flush(self):
        return None


class TestAuditCompleteness:
    """审计完整性必须可测量——否则无法在论文中声称 audit_logs 完整"""

    def setup_method(self):
        reset_audit_stats()

    def teardown_method(self):
        reset_audit_stats()

    async def test_success_is_counted(self):
        db = _OkSession()
        assert await write_audit(db, AuditKind.RISK, user_id="u1") is True
        stats = get_audit_stats()
        assert stats["attempted"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["last_error"] is None

    async def test_failure_is_counted_not_silent(self):
        """缺陷回归：原实现吞掉异常且不计数，丢失的审计无从察觉"""
        db = _FailingSession()
        assert await write_audit(db, AuditKind.REWARD, user_id="u1") is False

        stats = get_audit_stats()
        assert stats["attempted"] == 1
        assert stats["succeeded"] == 0
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.0
        assert "simulated DB failure" in (stats["last_error"] or "")

    async def test_strict_mode_raises(self):
        """研究批次要求审计零丢失时，失败必须抛出而非静默返回"""
        with pytest.raises(RuntimeError, match="simulated DB failure"):
            await write_audit(
                _FailingSession(), AuditKind.RISK, user_id="u1", strict=True
            )
        assert get_audit_stats()["failed"] == 1

    async def test_success_rate_is_computable(self):
        """论文可引用形如「审计写入成功率」的可复算指标"""
        for _ in range(3):
            await write_audit(_OkSession(), AuditKind.RISK)
        await write_audit(_FailingSession(), AuditKind.RISK)

        stats = get_audit_stats()
        assert stats["attempted"] == 4
        assert stats["succeeded"] == 3
        assert stats["failed"] == 1
        assert stats["success_rate"] == pytest.approx(0.75)

    def test_reset_for_each_batch(self):
        get_audit_stats()  # 确保结构可读
        reset_audit_stats()
        stats = get_audit_stats()
        assert stats["attempted"] == 0
        assert stats["success_rate"] is None, "空样本时成功率应为 None 而非 0"


class TestLearningMethodTipFallbackIsMarked:
    """学习方法提示的兜底值必须可识别——它是核心实验变量"""

    def test_normal_path_is_not_marked_as_fallback(self):
        tip = FeedbackService._get_learning_method_tip("math", True)
        assert tip["fallback"] is False
        assert tip["method"], "正常路径应返回真实方法键"

    def test_fallback_is_marked(self, monkeypatch):
        """缺陷回归：兜底值原与真实输出同形，会静默污染 method 分布"""
        def boom(*_args, **_kwargs):
            raise RuntimeError("engine exploded")

        monkeypatch.setattr(
            "app.services.feedback_service.LearningMethodEngine.get_post_question_tip",
            staticmethod(boom),
        )

        tip = FeedbackService._get_learning_method_tip("math", True)
        assert tip["fallback"] is True, "兜底值必须带 fallback 标记以便过滤"
        assert tip["method"] == "retrieval_practice"
        # 字段集与正常路径对齐，避免下游因缺键而行为不一致
        assert set(tip) == {"method", "title", "icon", "short", "action", "fallback"}
