"""LAI 学习成瘾化指数 和 A/B 测试框架 单元测试"""
import pytest
from app.services.learning_addiction_index import (
    LearningAddictionIndex, lai_engine, LAIRiskTier,
)
from app.services.ab_test_framework import (
    ABTestFramework, ab_test_framework, ExperimentPhase,
)


class TestLearningAddictionIndex:
    """LAI 学习成瘾化指数测试"""

    def test_healthy_student_l1(self):
        """健康学习者应为 L1 正常层"""
        assessment = lai_engine.assess(
            daily_minutes=40,
            session_minutes=25,
            night_ratio=0.0,
            content_attention_ratio=0.9,
            leaderboard_views=2,
            planned_stop_failures=0,
            intrinsic_motivation_ratio=0.8,
            external_reward_dependency=0.2,
            time_perception_bias=0.0,
            sleep_impact=0.0,
            social_impact=0.0,
        )
        assert assessment.overall_score >= 80
        assert assessment.risk_tier == LAIRiskTier.L1_NORMAL
        assert not assessment.should_reduce_gamification
        assert not assessment.should_notify_guardian

    def test_overuse_student_l2(self):
        """过度使用学习者应为 L2 关注层"""
        assessment = lai_engine.assess(
            daily_minutes=120,
            session_minutes=50,
            night_ratio=0.12,
            content_attention_ratio=0.7,
            leaderboard_views=8,
            planned_stop_failures=1,
            intrinsic_motivation_ratio=0.5,
            external_reward_dependency=0.5,
        )
        assert 50 <= assessment.overall_score < 80
        assert assessment.risk_tier == LAIRiskTier.L2_WATCH
        assert assessment.autonomy_support_boost  # 应触发自主性支持增强

    def test_addicted_student_l3(self):
        """成瘾学习者应为 L3 深度层"""
        assessment = lai_engine.assess(
            daily_minutes=155,
            session_minutes=65,
            night_ratio=0.18,
            content_attention_ratio=0.45,
            leaderboard_views=14,
            planned_stop_failures=3,
            intrinsic_motivation_ratio=0.35,
            external_reward_dependency=0.65,
            time_perception_bias=0.35,
            sleep_impact=0.25,
            social_impact=0.20,
        )
        assert 20 <= assessment.overall_score < 50, f"Score {assessment.overall_score} not in L3 range"
        assert assessment.risk_tier == LAIRiskTier.L3_DEEP
        assert assessment.should_reduce_gamification
        assert assessment.should_notify_guardian

    def test_pathological_student_l4(self):
        """病理性成瘾应为 L4"""
        assessment = lai_engine.assess(
            daily_minutes=300,
            session_minutes=120,
            night_ratio=0.4,
            content_attention_ratio=0.2,
            leaderboard_views=25,
            planned_stop_failures=8,
            intrinsic_motivation_ratio=0.1,
            external_reward_dependency=0.9,
            time_perception_bias=0.6,
            sleep_impact=0.7,
            social_impact=0.6,
        )
        assert assessment.overall_score < 20
        assert assessment.risk_tier == LAIRiskTier.L4_PATHOLOGICAL

    def test_primary_school_lower_thresholds(self):
        """小学生阈值应更低（更严格）"""
        # 90分钟对初中生正常，对小学生可能偏高
        primary = lai_engine.assess(daily_minutes=90, age_group="primary")
        secondary = lai_engine.assess(daily_minutes=90, age_group="secondary")
        assert primary.dimensions["time"].raw_score < secondary.dimensions["time"].raw_score

    def test_to_dict_serializable(self):
        """评估结果应可序列化为dict"""
        assessment = lai_engine.assess(daily_minutes=45)
        d = assessment.to_dict()
        assert "overall_score" in d
        assert "risk_tier" in d
        assert "dimensions" in d
        assert "recommendations" in d


class TestABTestFramework:
    """A/B 测试框架测试"""

    def test_create_experiment_shadow_mode(self):
        """新实验应为影子模式"""
        exp = ab_test_framework.create_experiment(
            name="测试变比率奖励概率",
            description="测试15% vs 25%触发概率",
            parameter_name="variable_ratio_probability",
            control_value="0.25",
            treatment_value="0.15",
        )
        assert exp.phase == ExperimentPhase.SHADOW
        assert exp.traffic_percentage == 0.0

    def test_shadow_mode_all_control(self):
        """影子模式下所有用户使用默认值"""
        exp = ab_test_framework.create_experiment(
            name="影子测试",
            description="测试",
            parameter_name="test_param",
            control_value="A",
            treatment_value="B",
        )
        val = ab_test_framework.get_parameter_value(exp.id, "user1", "default")
        assert val == "default"  # 影子模式返回默认值

    def test_advance_to_canary(self):
        """推进到小流量阶段"""
        exp = ab_test_framework.create_experiment(
            name="推进测试",
            description="测试阶段推进",
            parameter_name="param",
            control_value="0",
            treatment_value="1",
        )
        ab_test_framework.advance_phase(exp.id)
        assert exp.phase == ExperimentPhase.CANARY
        assert exp.traffic_percentage == 0.05

    def test_deterministic_assignment(self):
        """同一用户始终分到同一组"""
        exp = ab_test_framework.create_experiment(
            name="确定性分配测试",
            description="测试",
            parameter_name="p",
            control_value="c",
            treatment_value="t",
        )
        ab_test_framework.advance_phase(exp.id)  # canary
        ab_test_framework.advance_phase(exp.id)  # ramping
        ab_test_framework.advance_phase(exp.id)  # full

        group1 = ab_test_framework.assign_user(exp.id, "user123")
        group2 = ab_test_framework.assign_user(exp.id, "user123")
        assert group1 == group2  # 确定性

    def test_safety_stop_triggered(self):
        """健康一票否决：风险评分超阈值应触发安全停止"""
        exp = ab_test_framework.create_experiment(
            name="安全停止测试",
            description="测试健康一票否决",
            parameter_name="p",
            control_value="0",
            treatment_value="1",
        )
        # force=True 跳过样本量检查，快速推进到 full
        ab_test_framework.advance_phase(exp.id, force=True)  # canary
        ab_test_framework.advance_phase(exp.id, force=True)  # ramping
        ab_test_framework.advance_phase(exp.id, force=True)  # full

        # 模拟12个treatment用户的高风险评分
        for i in range(12):
            ab_test_framework.record_result(exp.id, f"u{i}", {
                "risk_score": 75,  # 超过安全阈值70
                "lai_score": 25,
            })

        assert exp.phase == ExperimentPhase.STOPPED
        assert exp.safety_stop_triggered
        assert "安全阈值" in exp.safety_stop_reason

    def test_experiment_summary(self):
        """实验摘要统计"""
        exp = ab_test_framework.create_experiment(
            name="摘要测试",
            description="测试",
            parameter_name="p",
            control_value="0",
            treatment_value="1",
        )
        ab_test_framework.advance_phase(exp.id, force=True)  # canary (5%)
        ab_test_framework.advance_phase(exp.id, force=True)  # ramping (25%)

        # 记录100个用户结果，确保有足够的 control 和 treatment
        for i in range(100):
            ab_test_framework.record_result(exp.id, f"user_{i}", {"exam_score": 70 + i % 10})

        summary = ab_test_framework.get_experiment_summary(exp.id)
        assert "control_count" in summary
        assert "treatment_count" in summary
        # 确保两组都有样本
        assert summary["control_count"] > 0
        assert summary["treatment_count"] > 0
        assert "metric_comparisons" in summary
        assert "exam_score" in summary["metric_comparisons"]


class TestLaiDashboardAggregation:
    """/lai/dashboard 的数据驱动聚合（从 Attempt 日志派生 LAI 输入）"""

    def _fake_db(self, attempts):
        class _Scalars:
            def __init__(self, rows): self.rows = rows
            def all(self): return self.rows
        class _Result:
            def __init__(self, rows): self.rows = rows
            def scalars(self): return _Scalars(self.rows)
        class _DB:
            async def execute(self, *a, **k): return _Result(attempts)
        return _DB()

    def _attempt(self, hour, time_spent, is_correct, hints_used):
        from datetime import datetime, UTC
        from types import SimpleNamespace
        return SimpleNamespace(
            created_at=datetime(2026, 1, 1, hour, 0, 0, tzinfo=UTC),
            time_spent=time_spent, is_correct=is_correct, hints_used=hints_used,
        )

    @pytest.mark.asyncio
    async def test_empty_log_falls_back_to_healthy_defaults(self):
        from app.api import gamification as g
        inputs = await g._aggregate_lai_inputs("u1", self._fake_db([]))
        assert inputs["night_ratio"] == 0.0
        assert inputs["daily_minutes"] == 20
        a = lai_engine.assess(**inputs)
        assert a.risk_tier == LAIRiskTier.L1_NORMAL

    @pytest.mark.asyncio
    async def test_night_heavy_log_drives_higher_risk(self):
        from app.api import gamification as g
        # 7 天、每天 30 题，全部凌晨 2 点、低正确率、高提示依赖 → 高夜比例 + 低专注
        attempts = [self._attempt(2, 600, False, 3) for _ in range(210)]
        inputs = await g._aggregate_lai_inputs("u2", self._fake_db(attempts))
        assert inputs["night_ratio"] > 0.9
        assert inputs["content_attention_ratio"] < 0.5
        a = lai_engine.assess(**inputs)
        assert a.risk_tier.value >= LAIRiskTier.L2_WATCH.value

    @pytest.mark.asyncio
    async def test_healthy_log_stays_l1(self):
        from app.api import gamification as g
        # 白天、正确率高、提示少 → 健康
        attempts = [self._attempt(15, 120, True, 0) for _ in range(70)]
        inputs = await g._aggregate_lai_inputs("u3", self._fake_db(attempts))
        assert inputs["night_ratio"] == 0.0
        a = lai_engine.assess(**inputs)
        assert a.risk_tier == LAIRiskTier.L1_NORMAL
