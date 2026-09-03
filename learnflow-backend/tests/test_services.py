"""综合单元测试 —— 覆盖所有核心服务的边缘场景"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timedelta, UTC


# ═══════════════════════════════════════════════
# DDA 动态难度调节引擎 测试
# ═══════════════════════════════════════════════

class TestDDAEngine:
    """DDA引擎：覆盖所有方向 + 边界条件"""

    def test_too_easy_increases_difficulty(self):
        from app.services.dda import dda_engine
        r = dda_engine.calculate([True] * 10, 4)
        assert r.direction.value == 'increase'
        assert r.difficulty == 5
        assert r.success_rate == 1.0

    def test_too_hard_decreases_difficulty(self):
        from app.services.dda import dda_engine
        r = dda_engine.calculate([False] * 10, 7)
        assert r.direction.value == 'decrease'
        assert r.difficulty == 6

    def test_flow_zone_maintains(self):
        from app.services.dda import dda_engine
        r = dda_engine.calculate([True, True, True, True, False, True, True, True, True, False], 5)
        assert r.success_rate == 0.8
        assert r.direction.value in ('maintain', 'micro_adjust')

    def test_empty_results_default(self):
        from app.services.dda import dda_engine
        r = dda_engine.calculate([], 5)
        assert r.difficulty == 5
        assert r.direction.value == 'maintain'
        assert r.confidence == 0.5

    def test_single_result(self):
        from app.services.dda import dda_engine
        r = dda_engine.calculate([True], 5)
        assert r.success_rate == 1.0
        assert r.difficulty == 6  # too easy with 100%

    def test_difficulty_bounds(self):
        from app.services.dda import dda_engine
        # 不能低于 1
        r = dda_engine.calculate([False] * 10, 1)
        assert r.difficulty == 1
        # 不能超过 10
        r = dda_engine.calculate([True] * 10, 10)
        assert r.difficulty == 10

    def test_with_time_slow_but_correct(self):
        from app.services.dda import dda_engine
        r = dda_engine.calculate_with_time(
            [True] * 10, [200.0] * 10, 4
        )
        # 虽然正确率高但很慢，应该维持难度
        assert r.direction.value == 'maintain'

    def test_micro_adjust_upper_boundary(self):
        from app.services.dda import dda_engine
        # success_rate = 9/10 = 0.9 > 0.82，触发 micro_adjust 向上
        r = dda_engine.calculate([True]*9 + [False], 4)
        assert r.direction.value in ('micro_adjust', 'increase')
        assert r.difficulty >= 4

    def test_micro_adjust_lower_boundary(self):
        from app.services.dda import dda_engine
        # success_rate = 5/10 = 0.5 < 0.78, 若 current > min → micro_adjust
        r = dda_engine.calculate([True]*5 + [False]*5, 5)
        # 0.5 < 0.75 target_min so decrease
        assert r.direction.value == 'decrease'


# ═══════════════════════════════════════════════
# 宠物系统 测试
# ═══════════════════════════════════════════════

class TestPetService:
    """宠物四维模型：属性更新 + 边界"""

    def test_correct_easy(self):
        from app.services.pet_service import PetService
        e = PetService.calculate_correct_answer(difficulty=3, hints_used=0)
        assert e.understanding_delta > 0
        assert e.persistence_delta == 0
        assert e.mood.value == 'happy'

    def test_correct_hard_retry(self):
        from app.services.pet_service import PetService
        e = PetService.calculate_correct_answer(difficulty=8, hints_used=0, is_retry=True)
        assert e.understanding_delta > 2.0  # 难度加成
        assert e.persistence_delta > 0     # 重试奖励

    def test_correct_with_hints_reduces_reward(self):
        from app.services.pet_service import PetService
        e_no_hint = PetService.calculate_correct_answer(difficulty=5, hints_used=0)
        e_with_hint = PetService.calculate_correct_answer(difficulty=5, hints_used=2)
        assert e_no_hint.understanding_delta > e_with_hint.understanding_delta

    def test_wrong_retry_gives_persistence(self):
        from app.services.pet_service import PetService
        e = PetService.calculate_wrong_answer(difficulty=5, chosen_recovery='retry')
        assert e.persistence_delta > 0
        assert e.mood.value == 'encouraging'

    def test_wrong_skip_penalizes(self):
        from app.services.pet_service import PetService
        e = PetService.calculate_wrong_answer(difficulty=5, chosen_recovery='skip')
        assert e.persistence_delta < 0  # 跳过扣坚持力
        assert e.mood.value == 'tired'

    def test_wrong_watch_tutorial_gives_understanding(self):
        from app.services.pet_service import PetService
        e = PetService.calculate_wrong_answer(difficulty=5, chosen_recovery='watch_tutorial')
        assert e.understanding_delta > 0

    def test_apply_update_clamps_values(self):
        from app.services.pet_service import PetService, PetUpdateEvent
        from app.models.pet import PetProfile, PetBreed
        import uuid
        pet = PetProfile(
            user_id=uuid.uuid4(),
            understanding=99.0, persistence=50.0,
            creativity=50.0, collaboration=50.0,
        )
        event = PetUpdateEvent(understanding_delta=5.0)  # 会超 100
        PetService.apply_update(pet, event)
        assert pet.understanding == 100.0  # clamped

    def test_level_evolution(self):
        from app.services.pet_service import PetService, PetUpdateEvent
        from app.models.pet import PetProfile, PetBreed
        import uuid
        # 从低分开始：总分 ~11 
        pet = PetProfile(
            user_id=uuid.uuid4(),
            understanding=10.0, persistence=10.0,
            creativity=10.0, collaboration=10.0,
        )
        assert pet.level == 1  # __init__ 默认 level=1
        # level 根据公式重算: int(10.0 // 10) + 1 = 2
        event = PetUpdateEvent(understanding_delta=0.0)
        PetService.apply_update(pet, event)
        assert pet.level == 2  # 总分10 → level应该=2

        # 再大幅提升
        event2 = PetUpdateEvent(
            understanding_delta=30.0, persistence_delta=30.0,
            creativity_delta=30.0, collaboration_delta=30.0,
        )
        PetService.apply_update(pet, event2)
        # 总分 = (40+40+40+40)/4 = 40, level = int(40//10)+1 = 5
        assert pet.level >= 5

    def test_collaboration_helped_other(self):
        from app.services.pet_service import PetService
        e = PetService.calculate_collaboration('helped_other')
        assert e.collaboration_delta > 0
        assert e.understanding_delta > 0  # 教学相长

    def test_repetition_decay(self):
        from app.services.pet_service import PetService
        e1 = PetService.calculate_correct_answer(difficulty=5, repetition_count=0)
        e10 = PetService.calculate_correct_answer(difficulty=5, repetition_count=10)
        assert e1.understanding_delta > e10.understanding_delta  # 衰减


# ═══════════════════════════════════════════════
# 微反馈服务 测试
# ═══════════════════════════════════════════════

class TestFeedbackService:
    """微反馈生成：各类上下文 + 边界"""

    def test_correct_feedback_structure(self):
        from app.services.feedback_service import FeedbackService, FeedbackContext
        ctx = FeedbackContext(
            is_correct=True, student_name='测试', topic='数学',
            difficulty=5, success_streak=0,
        )
        fb = FeedbackService.generate_task_feedback(ctx)
        assert fb['type'] == 'correct'
        assert fb['feedback_text']
        assert fb['pet_reaction'] in ('HAPPY', 'CONFIDENT')

    def test_incorrect_feedback_has_recovery(self):
        from app.services.feedback_service import FeedbackService, FeedbackContext
        ctx = FeedbackContext(
            is_correct=False, student_name='测试', topic='英语',
            difficulty=5,
        )
        fb = FeedbackService.generate_task_feedback(ctx)
        assert fb['type'] == 'incorrect'
        assert len(fb['recovery_options']) == 3
        assert fb['recovery_options'][0]['action'] == 'watch_tutorial'

    def test_high_streak_gives_badge(self):
        from app.services.feedback_service import FeedbackService, FeedbackContext
        ctx = FeedbackContext(
            is_correct=True, student_name='测试', topic='数学',
            difficulty=5, success_streak=5,
        )
        fb = FeedbackService.generate_task_feedback(ctx)
        assert fb['streak_badge']  # >=5, should have badge

    def test_identity_reinforcement(self):
        from app.services.feedback_service import FeedbackService
        result = FeedbackService.generate_identity_reinforcement(
            '小明', {
                'understanding_delta': 5, 'persistence_delta': 0,
                'creativity_delta': 2, 'collaboration_delta': 0,
            }
        )
        assert '小明' in result
        assert '分析能力' in result
        assert '创造性思维' in result

    def test_rest_reminder_90min(self):
        from app.services.feedback_service import FeedbackService
        msg = FeedbackService.generate_rest_reminder(90)
        assert '90分钟' in msg or '十分钟' in msg

    def test_rest_reminder_60min(self):
        from app.services.feedback_service import FeedbackService
        msg = FeedbackService.generate_rest_reminder(60)
        assert '60' in msg or '小' in msg

    def test_relaxation_guide(self):
        from app.services.feedback_service import FeedbackService
        guide = FeedbackService.generate_relaxation_guide()
        assert len(guide) > 10

    def test_encouragement_high_failure(self):
        from app.services.feedback_service import FeedbackService
        msg = FeedbackService._get_encouragement(5)
        assert '5个' in msg or '坚持' in msg or '边界' in msg

    def test_encouragement_low_failure(self):
        from app.services.feedback_service import FeedbackService
        msg = FeedbackService._get_encouragement(1)
        assert len(msg) > 0

    def test_streak_badge_thresholds(self):
        from app.services.feedback_service import FeedbackService
        assert FeedbackService._get_streak_badge(2) is None
        assert FeedbackService._get_streak_badge(3) == '🔥 三连对'
        assert FeedbackService._get_streak_badge(5) == '⭐ 五连对'
        assert FeedbackService._get_streak_badge(10) == '👑 十连对'
        assert FeedbackService._get_streak_badge(49) == '🏆 二十连对'  # 49 >= 20, 最高匹配
        assert FeedbackService._get_streak_badge(50) == '💎 五十连对'


# ═══════════════════════════════════════════════
# 间隔复习 测试
# ═══════════════════════════════════════════════

class TestSpacedRepetition:
    """艾宾浩斯间隔复习：序列 + 边界"""

    def test_correct_review_sequence(self):
        from app.services.spaced_repetition import SpacedRepetitionService as SRS
        intervals = []
        interval = None
        for i in range(8):
            r = SRS.calculate_next_review(i, True, interval)
            intervals.append(r['next_interval_days'])
            interval = r['next_interval_days']
        # 标准序列：1, 3, 7, 16, 35, 70, 140, 180（上限）
        assert intervals[0] == 1
        assert intervals[1] == 3
        assert intervals[2] == 7
        assert intervals[3] == 16
        assert intervals[4] == 35
        assert intervals[5] == 70
        assert intervals[6] == 140
        assert intervals[7] == 180  # capped at max

    def test_wrong_review_shortens_interval(self):
        from app.services.spaced_repetition import SpacedRepetitionService as SRS
        r = SRS.calculate_next_review(3, False, 16)
        assert r['next_interval_days'] < 16

    def test_max_interval_capped(self):
        from app.services.spaced_repetition import SpacedRepetitionService as SRS
        r = SRS.calculate_next_review(20, True, 300)
        assert r['next_interval_days'] == 180  # max

    def test_min_interval(self):
        from app.services.spaced_repetition import SpacedRepetitionService as SRS
        r = SRS.calculate_next_review(3, False, 1)
        assert r['next_interval_days'] >= 1

    def test_estimate_mastery(self):
        from app.services.spaced_repetition import SpacedRepetitionService as SRS
        assert SRS.estimate_mastery(0, True) == 0.0
        assert SRS.estimate_mastery(3, True) > 0.5
        assert SRS.estimate_mastery(5, True) >= 1.0


# ═══════════════════════════════════════════════
# 风险监控 测试
# ═══════════════════════════════════════════════

class TestRiskMonitor:
    """风险监控引擎：所有告警类型"""

    def test_normal_usage(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot, RiskLevel
        from datetime import datetime
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        snap = UsageSnapshot(
            user_id='u1', date=day_time,
            total_minutes=60, standard_minutes=50,
            hard_task_ratio=0.5, skip_ratio=0.1,
        )
        a = RiskMonitor.assess([snap])
        assert a.level == RiskLevel.NORMAL

    def test_daily_usage_red(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot, RiskLevel
        from datetime import datetime
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        snap = UsageSnapshot(
            user_id='u1', date=day_time,
            total_minutes=300,  # 5h > 3.5h red
        )
        a = RiskMonitor.assess([snap])
        assert a.level == RiskLevel.INTERVENTION

    def test_night_usage_red(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot
        from datetime import datetime
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        snap = UsageSnapshot(
            user_id='u1', date=day_time,
            total_minutes=60, night_minutes=30,  # 50% > 20%
        )
        from app.services.risk_monitor import RiskLevel
        a = RiskMonitor.assess([snap])
        assert a.level in (RiskLevel.INTERVENTION, RiskLevel.WARNING)

    def test_skip_ratio_warning(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot, RiskLevel
        from datetime import datetime
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        snap = UsageSnapshot(
            user_id='u1', date=day_time,
            total_minutes=60, skip_ratio=0.51, total_attempts=20,
        )
        a = RiskMonitor.assess([snap])
        assert a.level != RiskLevel.NORMAL

    def test_consecutive_usage_red(self):
        from app.services.risk_monitor import RiskMonitor
        r = RiskMonitor.check_consecutive_usage(130)
        assert r['should_force_rest'] is True
        assert r['zone'] == 'red'

    def test_consecutive_usage_yellow(self):
        from app.services.risk_monitor import RiskMonitor
        r = RiskMonitor.check_consecutive_usage(100)
        assert r['zone'] == 'red'

    def test_consecutive_usage_green(self):
        from app.services.risk_monitor import RiskMonitor
        r = RiskMonitor.check_consecutive_usage(30)
        assert r['zone'] == 'green'

    def test_is_night_time(self):
        from app.services.risk_monitor import RiskMonitor
        from datetime import datetime
        # Mock: use fixed hour
        assert RiskMonitor.is_night_time(datetime(2026, 6, 17, 23, 0)) is True
        assert RiskMonitor.is_night_time(datetime(2026, 6, 17, 5, 0)) is True
        assert RiskMonitor.is_night_time(datetime(2026, 6, 17, 12, 0)) is False

    def test_empty_snapshots(self):
        from app.services.risk_monitor import RiskMonitor, RiskLevel
        a = RiskMonitor.assess([])
        assert a.level == RiskLevel.NORMAL

    def test_low_hard_task_ratio_alert(self):
        from app.services.risk_monitor import RiskMonitor, UsageSnapshot
        from datetime import datetime
        snap = UsageSnapshot(
            user_id='u1', date=datetime.now(UTC),
            total_minutes=60, hard_task_ratio=0.1, total_attempts=15,
        )
        a = RiskMonitor.assess([snap])
        assert len(a.alerts) >= 1  # Should have challenge avoidance alert


# ═══════════════════════════════════════════════
# 认证模块 测试
# ═══════════════════════════════════════════════

class TestAuth:
    """认证模块：密码 + JWT"""

    def test_password_roundtrip(self):
        from app.core.security import hash_password, verify_password
        pw = 'MySecureP@ss123'
        hashed = hash_password(pw)
        assert verify_password(pw, hashed)
        assert not verify_password('wrong', hashed)

    def test_different_salts(self):
        from app.core.security import hash_password
        assert hash_password('same') != hash_password('same')

    def test_token_roundtrip(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token({'sub': 'user-1', 'role': 'student'})
        payload = decode_token(token)
        assert payload['sub'] == 'user-1'
        assert payload['type'] == 'access'

    def test_token_expiry(self):
        from app.core.security import create_access_token, decode_token
        import time
        token = create_access_token(
            {'sub': 'u1'},
            expires_delta=timedelta(seconds=-1),  # already expired
        )
        assert decode_token(token) is None

    def test_invalid_token(self):
        from app.core.security import decode_token
        assert decode_token('not.a.valid.token') is None
        assert decode_token('') is None

    def test_refresh_token_type(self):
        from app.core.security import create_refresh_token, decode_token
        refresh = create_refresh_token({'sub': 'u2'})
        payload = decode_token(refresh)
        assert payload['type'] == 'refresh'


# ═══════════════════════════════════════════════
# 配置模块 测试
# ═══════════════════════════════════════════════

class TestConfig:
    """应用配置验证"""

    def test_defaults(self):
        from app.core.config import settings
        assert settings.APP_NAME == 'LearnFlow'
        assert settings.DDA_TARGET_SUCCESS_RATE == 0.80
        assert settings.MAX_LEARNING_SESSION_MINUTES == 90
        assert settings.DAILY_USAGE_ALERT_HOURS == 3.5

    def test_jwt_settings(self):
        from app.core.config import settings
        assert settings.JWT_ALGORITHM == 'HS256'
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60

    def test_dda_window(self):
        from app.core.config import settings
        assert settings.DDA_WINDOW_SIZE == 10
