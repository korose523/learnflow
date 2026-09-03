"""内存态容器 → StateStore 迁移的回归测试

治理文档 §4.2 列出 11 个进程内内存容器。`BOX_STATES` 已在参考迁移中改造完成，
本文件覆盖其余 9 个容器：确认它们不再是裸 dict，而是 `StateStore` 实例，
并验证 set/get/delete/keys 四个接口的往返语义与改造前的 dict 行为一致。

同时验证「一行切换后端」——把容器换成 `JSONFileStateStore` 后数据真正落盘，
新进程（新 store 实例）能读回，为后续切 PostgreSQL/Redis 提供依据。
"""
from datetime import datetime, UTC

import pytest

from app.services.state_store import (
    StateStore,
    MemoryStateStore,
    JSONFileStateStore,
)


# ─── 被迁移的 9 个容器（引擎类, 属性名） ────────────────────

def _all_containers():
    from app.services.gamification_service import PeakEndEngine, ZeigarnikEngine
    from app.services.team_competition_engine import (
        TeamManagementEngine, TeamMatchEngine,
    )
    from app.services.habit_addiction_engine import SelfRegulationEngine
    from app.services.learning_methods_engine import MemoryPalaceEngine
    from app.services.duolingo_addiction_engine import FriendQuestEngine
    from app.services.meta_learning_skilltree import SkillTreeEngine

    return [
        (PeakEndEngine, "_active_sessions"),
        (ZeigarnikEngine, "_unfinished"),
        (TeamManagementEngine, "TEAMS"),
        (TeamManagementEngine, "PLAYER_TEAMS"),
        (TeamMatchEngine, "MATCHES"),
        (SelfRegulationEngine, "GOALS"),
        (MemoryPalaceEngine, "PALACES"),
        (FriendQuestEngine, "ACTIVE_QUESTS"),
        (SkillTreeEngine, "PLAYER_SKILLS"),
    ]


def _representative_values():
    """每个容器一个贴合真实用法的代表值（含 dataclass 实例）"""
    from app.services.gamification_service import SessionMemory, UnfinishedTask
    from app.services.team_competition_engine import Team, TeamMember, TeamMatch
    from app.services.habit_addiction_engine import SelfRegulationGoal
    from app.services.learning_methods_engine import MemoryPalace
    from app.services.duolingo_addiction_engine import FriendQuest
    from app.services.meta_learning_skilltree import LearningSkill, SkillCategory

    now = datetime.now(UTC)
    return {
        "_active_sessions": SessionMemory(session_start=now, total_attempts=3),
        "_unfinished": UnfinishedTask(task_id="mig_t1", topic="分数运算",
                                       difficulty=5, started_at=now),
        "TEAMS": Team(id="mig_team", name="迁移队", tag="MIG", captain_id="mig_u1",
                       members=[TeamMember(user_id="mig_u1", name="队长",
                                            role="captain")]),
        "PLAYER_TEAMS": "mig_team",
        "MATCHES": TeamMatch(id="mig_m1", team_a_id="mig_a", team_b_id="mig_b",
                              subject="数学"),
        "GOALS": [SelfRegulationGoal(id="mig_g1", user_id="mig_u1",
                                      description="每天 20 题", target_value=20,
                                      unit="题")],
        "PALACES": MemoryPalace(user_id="mig_u1", name="我的卧室"),
        "ACTIVE_QUESTS": FriendQuest(id="mig_fq1", participants=["mig_u1", "mig_u2"],
                                      goal_xp=100, start_date="", end_date=""),
        "PLAYER_SKILLS": {
            "active_recall": LearningSkill(
                skill_id="active_recall", name="主动回忆",
                category=SkillCategory.MEMORY, icon="🧠"),
        },
    }


CONTAINER_IDS = [f"{e.__name__}.{a}" for e, a in _all_containers()]


class TestContainersAreStateStores:
    """9 个容器不再是裸 dict"""

    @pytest.mark.parametrize("engine,attr",
                             _all_containers(), ids=CONTAINER_IDS)
    def test_container_is_state_store(self, engine, attr):
        store = getattr(engine, attr)
        assert isinstance(store, StateStore), f"{engine.__name__}.{attr} 仍不是 StateStore"
        assert not isinstance(store, dict), f"{engine.__name__}.{attr} 仍是裸 dict"

    @pytest.mark.parametrize("engine,attr",
                             _all_containers(), ids=CONTAINER_IDS)
    def test_container_backend_is_memory(self, engine, attr):
        """当前 9 个容器均持有可就地修改的 dataclass, 故显式使用内存后端"""
        assert isinstance(getattr(engine, attr), MemoryStateStore)

    def test_reference_migration_still_intact(self):
        """参考迁移 BOX_STATES 未被破坏"""
        from app.services.gamification_service import GamificationService
        assert isinstance(GamificationService.BOX_STATES, StateStore)


class TestRoundTrip:
    """set/get/delete/keys 往返语义"""

    @pytest.mark.parametrize("engine,attr",
                             _all_containers(), ids=CONTAINER_IDS)
    def test_set_get_delete_keys(self, engine, attr):
        store = getattr(engine, attr)
        value = _representative_values()[attr]
        key = f"__mig_probe_{attr}__"

        assert store.get(key) is None
        assert key not in store.keys()

        store.set(key, value)
        assert store.get(key) is value          # 引用语义：就地修改仍可见
        assert key in store.keys()

        store.delete(key)
        assert store.get(key) is None
        assert key not in store.keys()
        store.delete(key)                        # 重复删除静默忽略


class TestBehaviorPreserved:
    """迁移后业务流程行为不变（抽样覆盖读写删三类路径）"""

    def test_peak_end_session_lifecycle(self):
        from app.services.gamification_service import PeakEndEngine
        PeakEndEngine.start_session("mig_pe")
        PeakEndEngine.record_answer("mig_pe", True, "分数", 8, 5)
        summary = PeakEndEngine.end_session("mig_pe")
        assert summary["has_session"] is True
        assert summary["total_attempts"] == 1
        # end_session 应已删除该 key
        assert PeakEndEngine._active_sessions.get("mig_pe") is None
        assert PeakEndEngine.end_session("mig_pe") == {"has_session": False}

    def test_zeigarnik_save_and_clear(self):
        from app.services.gamification_service import ZeigarnikEngine
        ZeigarnikEngine.save_unfinished("mig_zg", "mig_task", "几何", 4)
        assert ZeigarnikEngine.get_reminder("mig_zg")["topic"] == "几何"
        ZeigarnikEngine.clear_unfinished("mig_zg", "mig_task")
        assert ZeigarnikEngine.get_reminder("mig_zg") is None

    def test_team_create_join_leave(self):
        from app.services.team_competition_engine import TeamManagementEngine
        team = TeamManagementEngine.create_team("迁移测试队", "MGT",
                                                 "mig_cap", "队长")
        assert TeamManagementEngine.PLAYER_TEAMS.get("mig_cap") == team.id
        assert TeamManagementEngine.TEAMS.get(team.id) is team

        # 重复加入应被拒（原 `user_id in PLAYER_TEAMS` 语义）
        assert TeamManagementEngine.join_team(team.id, "mig_cap", "队长")["success"] is False

        joined = TeamManagementEngine.join_team(team.id, "mig_mem", "队员")
        assert joined["success"] is True
        assert TeamManagementEngine.leave_team("mig_mem")["success"] is True
        assert TeamManagementEngine.PLAYER_TEAMS.get("mig_mem") is None

        # 队长离队后战队成员归零 → 战队被删除
        assert TeamManagementEngine.leave_team("mig_cap")["success"] is True
        assert TeamManagementEngine.TEAMS.get(team.id) is None

    def test_team_leaderboard_iterates_store(self):
        from app.services.team_competition_engine import (
            TeamManagementEngine, TeamLeagueEngine,
        )
        t = TeamManagementEngine.create_team("榜单队", "LBD", "mig_lb", "C")
        TeamLeagueEngine.record_team_contribution(t.id, "mig_lb", "地理", 777)
        board = TeamLeagueEngine.get_subject_leaderboard("地理")
        assert board["rankings"][0]["score"] == 777
        assert any(r["team_name"] == "榜单队"
                   for r in TeamLeagueEngine.get_global_leaderboard()["rankings"])
        TeamManagementEngine.leave_team("mig_lb")

    def test_match_id_uses_store_length(self):
        from app.services.team_competition_engine import (
            TeamManagementEngine, TeamMatchEngine,
        )
        a = TeamManagementEngine.create_team("对抗A", "MA", "mig_ma", "C")
        b = TeamManagementEngine.create_team("对抗B", "MB", "mig_mb", "C")
        before = len(TeamMatchEngine.MATCHES.keys())
        created = TeamMatchEngine.create_match(a.id, b.id, "化学")
        assert created["success"] is True
        assert len(TeamMatchEngine.MATCHES.keys()) == before + 1
        assert TeamMatchEngine.contribute_to_match(
            created["match_id"], a.id, "mig_ma", 30)["score_a"] == 30
        assert TeamMatchEngine.get_match_status(created["match_id"])["subject"] == "化学"
        TeamManagementEngine.leave_team("mig_ma")
        TeamManagementEngine.leave_team("mig_mb")

    def test_goals_append_semantics(self):
        """原 setdefault(user_id, []).append(goal) 的累积语义"""
        from app.services.habit_addiction_engine import SelfRegulationEngine
        SelfRegulationEngine.GOALS.delete("mig_goal_u")
        SelfRegulationEngine.set_goal("mig_goal_u", "g1", "每天20题", 20, "题")
        SelfRegulationEngine.set_goal("mig_goal_u", "g2", "每天30分钟", 30, "分钟")
        assert len(SelfRegulationEngine.GOALS.get("mig_goal_u")) == 2
        progress = SelfRegulationEngine.monitor_progress("mig_goal_u", "g2", 15)
        assert progress["progress_pct"] == 50.0
        # 未知用户走 `get(user_id) or []` 分支
        assert SelfRegulationEngine.monitor_progress("mig_absent", "g1", 1) == {
            "error": "目标不存在"}
        SelfRegulationEngine.GOALS.delete("mig_goal_u")

    def test_palace_place_and_recall(self):
        from app.services.learning_methods_engine import MemoryPalaceEngine
        MemoryPalaceEngine.PALACES.delete("mig_palace_u")
        placed = MemoryPalaceEngine.place_knowledge("mig_palace_u", "勾股定理", "直角三角形")
        assert placed["placed"] is True
        recall = MemoryPalaceEngine.recall_walkthrough("mig_palace_u")
        assert recall["has_palace"] is True
        assert recall["total_knowledge_stored"] == 1
        MemoryPalaceEngine.PALACES.delete("mig_palace_u")

    def test_friend_quest_contribution(self):
        from app.services.duolingo_addiction_engine import FriendQuestEngine
        quest = FriendQuestEngine.create_quest("mig_q1", "mig_q2")
        assert FriendQuestEngine.ACTIVE_QUESTS.get(quest.id) is quest
        result = FriendQuestEngine.contribute_xp(quest.id, "mig_q1", quest.goal_xp)
        assert result["completed"] is True
        FriendQuestEngine.ACTIVE_QUESTS.delete(quest.id)

    def test_skill_tree_cache_and_persistence_path(self):
        """PLAYER_SKILLS 为引擎内缓存；get_skill_tree / use_skill 路径不受影响"""
        from app.services.meta_learning_skilltree import SkillTreeEngine
        SkillTreeEngine.PLAYER_SKILLS.delete("mig_skill_u")
        skills = SkillTreeEngine.init_player_skills("mig_skill_u")
        assert SkillTreeEngine.PLAYER_SKILLS.get("mig_skill_u") is skills
        used = SkillTreeEngine.use_skill("mig_skill_u", "active_recall")
        assert used["used"] is True and used["xp_gained"] > 0
        tree = SkillTreeEngine.get_skill_tree("mig_skill_u")
        assert "categories" in tree and "meta_level" in tree
        # 缓存缺失时自愈重建（get_skill_tree 的 init 分支）
        SkillTreeEngine.PLAYER_SKILLS.delete("mig_skill_u")
        assert "categories" in SkillTreeEngine.get_skill_tree("mig_skill_u")
        SkillTreeEngine.PLAYER_SKILLS.delete("mig_skill_u")

    def test_skill_cache_feeds_persistence_payload(self):
        """PLAYER_SKILLS 缓存仍能喂给 save_skill_tree 所需的扁平结构"""
        from app.services.learning_orchestrator import _skilltree_repo_format
        from app.services.meta_learning_skilltree import SkillTreeEngine

        SkillTreeEngine.PLAYER_SKILLS.delete("mig_repo_u")
        skills = SkillTreeEngine.init_player_skills("mig_repo_u")
        cached = SkillTreeEngine.PLAYER_SKILLS.get("mig_repo_u")
        assert cached is skills, "缓存应返回同一对象, 保证就地升级可见"

        payload = _skilltree_repo_format(
            {sid: {"level": s.level, "times_used": s.times_used}
             for sid, s in cached.items()})
        assert payload["active_recall"] == {
            "proficiency": 0.1, "level": 1, "total_uses": 0}
        SkillTreeEngine.PLAYER_SKILLS.delete("mig_repo_u")


class TestBackendSwap:
    """一行切换后端：JSONFileStateStore 真正落盘并可跨实例读回"""

    def test_json_file_store_round_trip(self, tmp_path):
        path = str(tmp_path / "state" / "probe.json")
        store = JSONFileStateStore(path)
        store.set("k1", {"n": 1, "zh": "中文"})
        store.set("k2", "v2")
        assert sorted(store.keys()) == ["k1", "k2"]

        reopened = JSONFileStateStore(path)          # 模拟进程重启
        assert reopened.get("k1") == {"n": 1, "zh": "中文"}
        assert reopened.get("k2") == "v2"

        reopened.delete("k1")
        assert JSONFileStateStore(path).get("k1") is None
        reopened.close()

    def test_player_teams_can_swap_to_json_backend(self, tmp_path):
        """PLAYER_TEAMS 的值是 str，可无损切到文件后端（演示落库开关）"""
        from app.services.team_competition_engine import TeamManagementEngine

        path = str(tmp_path / "state" / "PLAYER_TEAMS.json")
        original = TeamManagementEngine.PLAYER_TEAMS
        TeamManagementEngine.PLAYER_TEAMS = JSONFileStateStore(path)
        try:
            team = TeamManagementEngine.create_team("落库队", "PST", "mig_js", "C")
            assert JSONFileStateStore(path).get("mig_js") == team.id
            TeamManagementEngine.leave_team("mig_js")
            assert JSONFileStateStore(path).get("mig_js") is None
        finally:
            TeamManagementEngine.PLAYER_TEAMS = original
        assert TeamManagementEngine.PLAYER_TEAMS is original
