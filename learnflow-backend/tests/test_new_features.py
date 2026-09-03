"""新功能测试套件: BKT引擎 + 游戏化服务 + 成瘾防护增强 + 近战效应 + 多巴胺节律"""
import pytest
from datetime import datetime, UTC, timedelta


# ─── BKT 知识追踪引擎 ──────────────────────────────

class TestBKTEngine:
    def test_initial_state(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        # get_or_create_skill 使用引擎默认参数创建
        skill = engine.get_or_create_skill(state, "math")
        assert skill.p_mastery == engine.DEFAULT_PARAMS["p_learn0"]
        assert skill.total_attempts == 0

    def test_update_correct_increases_mastery(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        skill = engine.update(state, "math", True)
        assert skill.p_mastery > 0.35
        assert skill.total_attempts == 1
        assert skill.correct_attempts == 1

    def test_update_incorrect_decreases_mastery(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        skill = engine.update(state, "math", False)
        assert skill.p_mastery < 0.35
        assert skill.total_attempts == 1
        assert skill.correct_attempts == 0

    def test_repeated_correct_converges(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        for _ in range(30):
            engine.update(state, "math", True)
        skill = state.skills["math"]
        # 大量正确后掌握概率应接近1
        assert skill.p_mastery > 0.85

    def test_batch_update(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        engine.batch_update(state, [("math", True), ("science", False), ("math", True)])
        assert state.skills["math"].total_attempts == 2
        assert state.skills["science"].total_attempts == 1

    def test_recommend_difficulty_range(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        skill = engine.get_or_create_skill(state, "math")
        d = engine.recommend_difficulty(skill)
        assert 1 <= d <= 10

    def test_recommend_difficulty_scales_with_mastery(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")

        # 低掌握 → 低难度
        skill_low = engine.get_or_create_skill(state, "low")
        skill_low.p_mastery = 0.1
        assert engine.recommend_difficulty(skill_low) <= 4

        # 高掌握 → 高难度
        skill_high = engine.get_or_create_skill(state, "high")
        skill_high.p_mastery = 0.9
        assert engine.recommend_difficulty(skill_high) >= 7

    def test_skill_report(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        engine.update(state, "math", True)
        engine.update(state, "science", False)
        report = engine.get_skill_report(state)
        assert report["total_skills"] == 2
        assert len(report["skills"]) == 2
        assert 0 <= report["average_mastery"] <= 1

    def test_mastery_level_labels(self):
        from app.services.knowledge_tracing import BKTEngine
        assert BKTEngine._mastery_level(0.9) == "mastered"
        assert BKTEngine._mastery_level(0.7) == "proficient"
        assert BKTEngine._mastery_level(0.5) == "developing"
        assert BKTEngine._mastery_level(0.3) == "beginner"
        assert BKTEngine._mastery_level(0.1) == "novice"

    def test_parameter_adaptation(self):
        from app.services.knowledge_tracing import BKTEngine, KnowledgeState
        engine = BKTEngine()
        state = KnowledgeState(user_id="test_user")
        # 模拟高正确率场景
        for _ in range(15):
            engine.update(state, "math", True)
        skill = state.skills["math"]
        old_transit = skill.p_transit
        engine.adapt_parameters(skill)
        # 参数应该被调整
        assert skill.p_transit != old_transit


# ─── 近战效应检测 ──────────────────────────────────

class TestNearMissDetection:
    def test_exact_match(self):
        from app.services.gamification_service import NearMissDetector
        is_nm, reason = NearMissDetector.is_near_miss("4", "4")
        assert not is_nm

    def test_numeric_near_miss(self):
        from app.services.gamification_service import NearMissDetector
        is_nm, reason = NearMissDetector.is_near_miss("3", "4")
        assert is_nm
        assert "差1" in reason

    def test_numeric_far_away(self):
        from app.services.gamification_service import NearMissDetector
        is_nm, reason = NearMissDetector.is_near_miss("1", "10")
        assert not is_nm

    def test_single_char_diff(self):
        from app.services.gamification_service import NearMissDetector
        is_nm, reason = NearMissDetector.is_near_miss("abc", "abd")
        assert is_nm
        assert "一个字符" in reason

    def test_no_match(self):
        from app.services.gamification_service import NearMissDetector
        is_nm, reason = NearMissDetector.is_near_miss("apple", "orange")
        assert not is_nm


# ─── 游戏化激励 — 宝箱 ──────────────────────────────

class TestTreasureBox:
    def test_initial_state(self):
        from app.services.gamification_service import TreasureBoxState
        state = TreasureBoxState()
        assert state.questions_since_last_box == 0
        assert state.next_box_at == 3

    def test_not_yet_due(self):
        from app.services.gamification_service import GamificationService, TreasureBoxState
        state = TreasureBoxState()
        for _ in range(2):
            assert not GamificationService.should_open_box(state)

    def test_box_triggers(self):
        from app.services.gamification_service import GamificationService, TreasureBoxState
        state = TreasureBoxState()
        for _ in range(2):
            GamificationService.should_open_box(state)
        assert GamificationService.should_open_box(state)

    def test_open_box_resets(self):
        from app.services.gamification_service import GamificationService, TreasureBoxState
        state = TreasureBoxState()
        GamificationService.should_open_box(state)
        GamificationService.should_open_box(state)
        GamificationService.should_open_box(state)
        result = GamificationService.open_box(state, pet_name="小豆", current_topic="分数运算")
        assert "type" in result
        assert "title" in result
        assert state.questions_since_last_box == 0
        assert state.total_boxes_opened == 1
        assert 3 <= state.next_box_at <= 10


# ─── 游戏化激励 — 目标梯度 & 渐近目标 ──────────────

class TestProximalGoals:
    def test_initial_goals(self):
        from app.services.gamification_service import ProximalGoals
        goals = ProximalGoals()
        assert goals.daily_target == 10
        assert goals.weekly_target == 50

    def test_record_question(self):
        from app.services.gamification_service import GamificationService, ProximalGoals
        goals = ProximalGoals()
        result = GamificationService.record_question_completion(goals)
        assert goals.current_streak == 1
        assert goals.daily_completed == 1
        assert goals.mini_goal_progress == 1

    def test_mini_goal_completion(self):
        from app.services.gamification_service import GamificationService, ProximalGoals
        goals = ProximalGoals()
        for _ in range(5):
            GamificationService.record_question_completion(goals)
        assert goals.mini_goals_completed == 1
        assert goals.mini_goal_progress == 0

    def test_goal_progress_pulse(self):
        from app.services.gamification_service import GamificationService, ProximalGoals
        goals = ProximalGoals()
        for _ in range(8):
            GamificationService.record_question_completion(goals)
        progress = GamificationService.get_goal_progress(goals)
        assert progress["daily"]["pct"] == 80
        assert progress["pulse_daily"] == True


# ─── 游戏化激励 — 禀赋效应 ──────────────────────────

class TestEndowedProgress:
    def test_endowed_progress_monday(self):
        from app.services.gamification_service import GamificationService, ProximalGoals
        goals = ProximalGoals()
        result = GamificationService.get_endowed_progress(goals)
        # 如果今天是周一，会赠送2题；否则不赠送
        assert "gifted" in result
        assert "weekly_completed" in result


# ─── 游戏化激励 — 损失厌恶 ──────────────────────────

class TestLossAversion:
    def test_streak_update_first_time(self):
        from app.services.gamification_service import GamificationService, StreakState
        streak = StreakState()
        result = GamificationService.update_streak(streak)
        assert result["streak"] == 1
        assert result["changed"] == True

    def test_nudge_at_high_streak(self):
        from app.services.gamification_service import GamificationService, StreakState
        streak = StreakState(current_streak=3, best_streak=3)
        nudge = GamificationService.get_loss_aversion_nudge(streak)
        assert nudge is not None
        assert "3" in nudge

    def test_nudge_at_low_streak(self):
        from app.services.gamification_service import GamificationService, StreakState
        streak = StreakState(current_streak=1, best_streak=1)
        nudge = GamificationService.get_loss_aversion_nudge(streak)
        assert nudge is None


# ─── 多巴胺节律 ─────────────────────────────────────

class TestDopamineRhythm:
    def test_correct_rhythm(self):
        from app.services.gamification_service import DopamineRhythm
        rhythm = DopamineRhythm.for_correct("分数运算", "小豆", 0)
        assert "sparkle" in rhythm.phase_1
        assert "小豆" in rhythm.phase_2
        assert "分数运算" in rhythm.phase_3

    def test_near_miss_rhythm(self):
        from app.services.gamification_service import DopamineRhythm
        rhythm = DopamineRhythm.for_incorrect("分数运算", "小豆", True)
        assert "near_miss" in rhythm.phase_1
        assert "差一点" in rhythm.phase_2

    def test_incorrect_rhythm(self):
        from app.services.gamification_service import DopamineRhythm
        rhythm = DopamineRhythm.for_incorrect("分数运算", "小豆", False)
        assert "gentle" in rhythm.phase_1
        assert "小豆" in rhythm.phase_2


# ─── 成瘾防护增强 — 三级防护 ────────────────────────

class TestEnhancedRiskMonitor:
    def test_normal_usage(self):
        from app.services.risk_monitor import RiskMonitor, RiskLevel, UsageSnapshot
        # 使用白天时间避免 is_night_time 影响
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        snapshots = [
            UsageSnapshot(user_id="u1", date=day_time, total_minutes=60, total_attempts=20, correct_attempts=15)
        ]
        result = RiskMonitor.assess(snapshots)
        assert result.level == RiskLevel.NORMAL
        assert result.zone == "green"

    def test_daily_usage_red(self):
        from app.services.risk_monitor import RiskMonitor, RiskLevel, UsageSnapshot
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        snapshots = [UsageSnapshot(user_id="u1", date=day_time, total_minutes=250)]
        result = RiskMonitor.assess(snapshots)
        assert result.level == RiskLevel.INTERVENTION
        assert result.should_force_rest

    def test_consecutive_failure_intervention(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot
        snapshots = [UsageSnapshot(user_id="u1", date=datetime.now(UTC), consecutive_failures=6)]
        result = RiskMonitor.assess(snapshots)
        assert result.should_reduce_difficulty

    def test_repeated_skill_switch(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot
        snapshots = [UsageSnapshot(user_id="u1", date=datetime.now(UTC),
                                    repeated_skill_attempts={"math": 22})]
        result = RiskMonitor.assess(snapshots)
        assert result.should_switch_topic

    def test_consecutive_usage_red(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_consecutive_usage(100)
        assert result["should_force_rest"]
        assert result["zone"] == "red"

    def test_consecutive_usage_yellow(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_consecutive_usage(70)
        assert not result["should_force_rest"]
        assert result["zone"] == "yellow"

    def test_consecutive_usage_green(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_consecutive_usage(30)
        assert not result["should_force_rest"]
        assert result["zone"] == "green"

    def test_repeated_skill_check(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_repeated_skill({"math": 25})
        assert result["should_switch"]
        assert result["most_repeated"] == "math"

    def test_repeated_skill_ok(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_repeated_skill({"math": 10})
        assert not result["should_switch"]

    def test_consecutive_failure_alert(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_consecutive_failure(6)
        assert result["should_intervene"]
        assert result["should_reduce_difficulty"]

    def test_consecutive_failure_ok(self):
        from app.services.risk_monitor import RiskMonitor
        result = RiskMonitor.check_consecutive_failure(3)
        assert not result["should_intervene"]

    def test_is_night_time(self):
        from app.services.risk_monitor import RiskMonitor
        night = datetime(2026, 6, 20, 23, 0, tzinfo=UTC)
        day = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        assert RiskMonitor.is_night_time(night)
        assert not RiskMonitor.is_night_time(day)


# ─── 近战效应反馈 ──────────────────────────────────

class TestNearMissFeedback:
    def test_near_miss_feedback_structure(self):
        from app.services.feedback_service import FeedbackService
        result = FeedbackService.generate_near_miss_feedback("差1个单位", "分数运算", "小豆")
        assert result["type"] == "near_miss"
        assert "近在咫尺" in result["feedback_text"] or "差1" in result["feedback_text"]
        assert result["pet_reaction"] == "CURIOUS"
        assert len(result["recovery_options"]) >= 1

    def test_dopamine_rhythm_correct(self):
        from app.services.feedback_service import FeedbackService
        rhythm = FeedbackService.generate_dopamine_rhythm(True, False, "分数运算", "小豆", 0)
        assert rhythm["phase_1"]["animation"] == "sparkle"
        assert rhythm["phase_2"]["pet_animation"] in ["happy_dance", "smile"]

    def test_dopamine_rhythm_near_miss(self):
        from app.services.feedback_service import FeedbackService
        rhythm = FeedbackService.generate_dopamine_rhythm(False, True, "分数运算", "小豆", 0)
        assert rhythm["phase_1"]["animation"] == "near_miss_pulse"

    def test_dopamine_rhythm_incorrect(self):
        from app.services.feedback_service import FeedbackService
        rhythm = FeedbackService.generate_dopamine_rhythm(False, False, "分数运算", "小豆", 0)
        assert rhythm["phase_1"]["animation"] == "gentle_shake"
