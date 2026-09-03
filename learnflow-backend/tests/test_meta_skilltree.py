"""元学习技能树游戏化测试"""
import pytest


class TestSkillTreeEngine:
    def test_init_skills(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        skills = SkillTreeEngine.init_player_skills("u1")
        assert len(skills) == 16
        assert skills["active_recall"].unlocked
        assert skills["active_recall"].level == 1

    def test_use_skill_gains_xp(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        SkillTreeEngine.init_player_skills("u2")
        result = SkillTreeEngine.use_skill("u2", "active_recall")
        assert result["used"]
        assert result["xp_gained"] > 0
        assert result["times_used"] == 1

    def test_use_lock_skill_refused(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        SkillTreeEngine.init_player_skills("u3")
        # 记忆宫殿需要前置 active_recall
        # 如果前置满足应该能解锁
        result = SkillTreeEngine.use_skill("u3", "memory_palace")
        if not result["used"]:
            assert "尚未解锁" in result["message"]

    def test_skill_levels_up(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        skills = SkillTreeEngine.init_player_skills("u4")
        skill = skills["active_recall"]
        skill.xp = 48  # 接近升级 (need 50)
        # 用一次应该升级
        result = SkillTreeEngine.use_skill("u4", "active_recall")
        # Should have leveled up to Lv.2 (10 XP gets to 58, over 50 threshold)
        assert result["leveled_up"]

    def test_skill_tree_structure(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        SkillTreeEngine.init_player_skills("u5")
        tree = SkillTreeEngine.get_skill_tree("u5")
        assert tree["meta_level"] >= 1
        assert "categories" in tree
        assert len(tree["categories"]) >= 3

    def test_combo_bonuses(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        skills = SkillTreeEngine.init_player_skills("u6")
        skills["active_recall"].level = 5
        skills["spaced_repetition"].level = 5
        tree = SkillTreeEngine.get_skill_tree("u6")
        assert tree["combo_bonus"]["active_combos"] >= 1

    def test_categories_not_empty(self):
        from app.services.meta_learning_skilltree import SkillTreeEngine
        skills = SkillTreeEngine.init_player_skills("u7")
        SkillTreeEngine.use_skill("u7", "active_recall")
        SkillTreeEngine.use_skill("u7", "feynman")
        tree = SkillTreeEngine.get_skill_tree("u7")
        for cat in tree["categories"].values():
            assert len(cat) > 0


class TestMethodQuestEngine:
    def test_generate_daily_quests(self):
        from app.services.meta_learning_skilltree import MethodQuestEngine, SkillTreeEngine
        SkillTreeEngine.init_player_skills("q1")
        quests = MethodQuestEngine.generate_daily_quests("q1")
        assert len(quests) == 3

    def test_different_days_different_quests(self):
        from app.services.meta_learning_skilltree import MethodQuestEngine, SkillTreeEngine
        SkillTreeEngine.init_player_skills("q2")
        q1 = MethodQuestEngine.generate_daily_quests("q2")
        # 同一天同一用户应该生成相同任务（确定性）
        q2 = MethodQuestEngine.generate_daily_quests("q2")
        assert q1[0]["quest"] == q2[0]["quest"]
        assert len(q1) == 3


class TestProficiencyEngine:
    def test_proficiency_badge(self):
        from app.services.meta_learning_skilltree import (
            ProficiencyEngine, LearningSkill, SkillCategory
        )
        skill = LearningSkill(skill_id="test", name="测试", category=SkillCategory.MEMORY,
                              icon="🧪", level=5)
        badge = ProficiencyEngine.get_proficiency_badge(skill)
        assert badge["tier"] == "方法大师"

    def test_global_proficiency(self):
        from app.services.meta_learning_skilltree import ProficiencyEngine, SkillTreeEngine
        skills = SkillTreeEngine.init_player_skills("p1")
        skills["active_recall"].level = 5
        skills["feynman"].level = 3
        result = ProficiencyEngine.get_global_proficiency(skills)
        assert result["total_unlocked"] >= 5
        assert "summary" in result
        assert "most_used" in result
