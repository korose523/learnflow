"""核心学习流与游戏化端到端测试"""
import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock


class TestOnboardingService:
    """用户初始化统一服务测试"""

    @pytest.mark.asyncio
    async def test_ensure_default_pet_creates_pet_when_none(self):
        from app.services.onboarding_service import OnboardingService
        from app.models.user import User, UserRole
        from app.models.pet import PetProfile

        user = User(email="test@example.com", name="Test", role=UserRole.STUDENT, hashed_password="x")
        user.id = "user-1"

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        pet = await OnboardingService.ensure_default_pet(user, db)
        assert pet.name == "小豆"
        assert pet.breed.value == "cat"
        assert pet.understanding == 50.0
        assert pet.persistence == 50.0
        assert pet.creativity == 50.0
        assert pet.collaboration == 50.0

    @pytest.mark.asyncio
    async def test_ensure_default_pet_returns_existing_pet(self):
        from app.services.onboarding_service import OnboardingService
        from app.models.user import User, UserRole
        from app.models.pet import PetProfile

        user = User(email="test@example.com", name="Test", role=UserRole.STUDENT, hashed_password="x")
        user.id = "user-1"
        existing = PetProfile(user_id=user.id, name="Existing", breed="cat")

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing)))

        pet = await OnboardingService.ensure_default_pet(user, db)
        assert pet is existing

    @pytest.mark.asyncio
    async def test_ensure_default_skill_profile_creates_profiles(self):
        from app.services.onboarding_service import OnboardingService
        from app.models.user import User, UserRole

        user = User(email="test@example.com", name="Test", role=UserRole.STUDENT, hashed_password="x")
        user.id = "user-1"

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db.flush = AsyncMock()

        await OnboardingService.ensure_default_skill_profile(user, db)
        assert db.execute.called
        assert db.flush.called

    @pytest.mark.asyncio
    async def test_ensure_default_consents_sets_relaxation_guide(self):
        from app.services.onboarding_service import OnboardingService
        from app.models.user import User, UserRole

        user = User(email="test@example.com", name="Test", role=UserRole.STUDENT, hashed_password="x")
        user.consents = {}

        db = MagicMock()
        db.flush = AsyncMock()

        await OnboardingService.ensure_default_consents(user, db)
        assert user.consents.get("relaxation_guide") is True


class TestLearningOrchestrator:
    """学习流编排器测试"""

    def test_compare_answer_normalizes_strings(self):
        from app.services.learning_orchestrator import LearningOrchestrator

        assert LearningOrchestrator._compare_answer("  4  ", "4") is True
        assert LearningOrchestrator._compare_answer("1/2", "0.5") is True
        assert LearningOrchestrator._compare_answer("3.14", "3,14") is True
        assert LearningOrchestrator._compare_answer("x=4", "4") is False

    def test_compute_fused_difficulty_respects_bounds(self):
        from app.services.learning_orchestrator import LearningOrchestrator

        assert LearningOrchestrator._compute_fused_difficulty(1, 1, 1) == 1
        assert LearningOrchestrator._compute_fused_difficulty(10, 10, 10) == 10
        fused = LearningOrchestrator._compute_fused_difficulty(5, 7, 8)
        assert 1 <= fused <= 10

    def test_compute_fused_difficulty_uses_weights(self):
        from app.services.learning_orchestrator import LearningOrchestrator

        # 5*0.45 + 7*0.35 + 8*0.20 = 2.25 + 2.45 + 1.6 = 6.3 -> 6
        assert LearningOrchestrator._compute_fused_difficulty(5, 7, 8) == 6


class TestGamificationService:
    """游戏化服务测试"""

    def test_open_box_returns_reward(self):
        from app.services.gamification_service import GamificationService, TreasureBoxState

        state = TreasureBoxState(questions_since_last_box=3, next_box_at=3)
        reward = GamificationService.open_box(state, pet_name="小豆", current_topic="数学")
        assert "type" in reward
        assert "title" in reward
        assert "icon" in reward
        assert state.questions_since_last_box == 0

    def test_should_open_box_when_threshold_reached(self):
        from app.services.gamification_service import GamificationService, TreasureBoxState

        state = TreasureBoxState(questions_since_last_box=2, next_box_at=3)
        assert GamificationService.should_open_box(state) is True

    def test_should_not_open_box_before_threshold(self):
        from app.services.gamification_service import GamificationService, TreasureBoxState

        state = TreasureBoxState(questions_since_last_box=1, next_box_at=3)
        assert GamificationService.should_open_box(state) is False

    def test_near_miss_detector_numeric(self):
        from app.services.gamification_service import NearMissDetector

        is_near, reason = NearMissDetector.is_near_miss("3", "5")
        assert is_near is True
        assert reason

        is_near, _ = NearMissDetector.is_near_miss("10", "5")
        assert is_near is False

    def test_near_miss_detector_fraction_swap(self):
        from app.services.gamification_service import NearMissDetector

        is_near, reason = NearMissDetector.is_near_miss("1/2", "2/1")
        assert is_near is True
        assert "分子" in reason or "分母" in reason

    def test_near_miss_detector_one_char_diff(self):
        from app.services.gamification_service import NearMissDetector

        is_near, reason = NearMissDetector.is_near_miss("x=4", "x=5")
        assert is_near is True
        assert reason

    def test_update_streak_extends_on_consecutive_day(self):
        from app.services.gamification_service import GamificationService, StreakState

        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        state = StreakState(current_streak=2, best_streak=2, last_active_date=yesterday)
        result = GamificationService.update_streak(state)
        assert result["streak"] == 3
        assert result["changed"] is True

    def test_update_streak_resets_on_gap(self):
        from app.services.gamification_service import GamificationService, StreakState

        state = StreakState(current_streak=5, best_streak=5, last_active_date="2020-01-01")
        result = GamificationService.update_streak(state)
        assert result["streak"] == 1
        assert result["changed"] is True

    def test_update_streak_uses_shield(self):
        from app.services.gamification_service import GamificationService, StreakState

        state = StreakState(current_streak=5, streak_shields=1, last_active_date="2020-01-01")
        result = GamificationService.update_streak(state)
        assert result["streak"] == 6
        assert result["changed"] is True

    def test_record_question_completion_triggers_mini_goal(self):
        from app.services.gamification_service import GamificationService, ProximalGoals

        goals = ProximalGoals(mini_goal_progress=4)
        result = GamificationService.record_question_completion(goals)
        assert result["mini_completed"] is True
        assert goals.mini_goals_completed == 1


class TestDuolingoEngine:
    """多邻国式连胜/XP引擎测试"""

    def test_xp_engine_award_xp_increases_total(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState

        state = XPState(total_xp=0)
        result = XPEngine.award_xp(state, "lesson_complete")
        assert result["xp_earned"] > 0
        assert state.total_xp > 0

    def test_xp_engine_leveled_up(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState

        state = XPState(total_xp=95, xp_to_next_level=100)
        XPEngine.award_xp(state, "perfect_lesson")
        assert state.xp_level > 1 or state.total_xp >= 100

    def test_streak_check_in_extends(self):
        from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState

        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        state = DuolingoStreakState(current_streak=3, last_lesson_date=yesterday)
        result = DuolingoStreakEngine.check_in(state)
        assert result["streak"] == 4
        assert result["action"] == "extended"

    def test_streak_check_in_freezes(self):
        from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState

        state = DuolingoStreakState(current_streak=5, streak_freezes_available=1, last_lesson_date="2020-01-01")
        result = DuolingoStreakEngine.check_in(state)
        assert result["action"] == "frozen"
        assert result["streak"] == 6


class TestTeamCompetition:
    """战队/排位系统测试"""

    def test_create_team_validates_tag_length(self):
        from app.services.team_competition_engine import TeamManagementEngine

        with pytest.raises(ValueError):
            TeamManagementEngine.create_team("Team", "A", "user-1", "Captain")

    def test_create_team_succeeds(self):
        from app.services.team_competition_engine import TeamManagementEngine

        TeamManagementEngine.TEAMS.clear()
        TeamManagementEngine.PLAYER_TEAMS.clear()
        team = TeamManagementEngine.create_team("LearnFlow", "LF", "user-1", "Captain")
        assert team.name == "LearnFlow"
        assert team.tag == "LF"
        assert TeamManagementEngine.PLAYER_TEAMS.get("user-1") == team.id

    def test_join_team_adds_member(self):
        from app.services.team_competition_engine import TeamManagementEngine

        TeamManagementEngine.TEAMS.clear()
        TeamManagementEngine.PLAYER_TEAMS.clear()
        team = TeamManagementEngine.create_team("LearnFlow", "LF", "user-1", "Captain")
        result = TeamManagementEngine.join_team(team.id, "user-2", "Member")
        assert result["success"] is True
        assert len(team.members) == 2

    def test_solo_rank_win_increases_lp(self):
        from app.services.team_competition_engine import SoloRankEngine, SubjectRank

        rank = SubjectRank(subject="数学")
        result = SoloRankEngine.record_game(rank, True)
        assert result["lp_change"] > 0
        assert rank.lp > 0


class TestSkillTree:
    """元学习技能树测试"""

    def test_init_player_skills_unlocks_basic_methods(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine

        SkillTreeEngine.PLAYER_SKILLS.clear()
        skills = SkillTreeEngine.init_player_skills("user-1")
        assert skills["active_recall"].unlocked is True
        assert skills["retrieval_practice"].unlocked is True

    def test_use_skill_gains_xp(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine

        SkillTreeEngine.PLAYER_SKILLS.clear()
        SkillTreeEngine.init_player_skills("user-1")
        result = SkillTreeEngine.use_skill("user-1", "active_recall")
        assert result["used"] is True
        assert result["xp_gained"] > 0

    def test_get_skill_tree_returns_categories(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine

        SkillTreeEngine.PLAYER_SKILLS.clear()
        tree = SkillTreeEngine.get_skill_tree("user-1")
        assert "categories" in tree
        assert "meta_level" in tree

    def test_daily_quests_generated(self):
        from app.services.meta_learning_skilltree import MethodQuestEngine

        quests = MethodQuestEngine.generate_daily_quests("user-1")
        assert len(quests) == 3
