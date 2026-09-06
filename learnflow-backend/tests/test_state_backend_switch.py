"""游戏化状态容器 → 可插拔后端切换的回归测试（价值证明）

本文件证明：把 11 个容器接上 ``default_state_store`` 后，一旦把某个容器切到
JSON 文件后端（``LEARNFLOW_STATE_BACKEND=json`` 的落库形态），此前「内存后端
get 返回对象本身、就地修改自动可见」的依赖不再成立 —— 必须显式 ``set`` 回写，
否则改动会**静默丢失**（进程重启即截断纵向序列）。

覆盖：
1. 端到端持久化：真实业务方法写入 → 用同一路径重开 store → 数据还在（模拟进程重启）；
2. 7 处（另加 4 处额外发现的）就地修改点，调用业务方法 → 重开 store → 改动仍在；
3. 类型还原：嵌套 ``List[dataclass]``（TEAMS.members → TeamMember）、
   ``datetime``（SelfRegulationGoal.deadline）正确还原而非退化成 dict / str；
4. GOALS 顶层 ``List[...]``：重开后元素是 ``SelfRegulationGoal`` 实例且 ``g.id`` 可访问；
5. 默认后端仍是内存：不设环境变量时 ``default_state_store`` 返回 ``MemoryStateStore``。

临时目录用 ``tmp_path``，绝不写入 ``artifacts/state/``。每个用例用 try/finally 还原容器。
"""
from contextlib import contextmanager
from datetime import datetime

import pytest

from app.services.state_store import (
    DataclassJSONStateStore,
    MemoryStateStore,
    default_state_store,
)

from app.services.gamification_service import (
    GamificationService,
    PeakEndEngine,
    ZeigarnikEngine,
    TreasureBoxState,
    SessionMemory,
    UnfinishedTask,
)
from app.services.duolingo_addiction_engine import FriendQuestEngine, FriendQuest
from app.services.habit_addiction_engine import SelfRegulationEngine, SelfRegulationGoal
from app.services.learning_methods_engine import MemoryPalaceEngine, MemoryPalace
from app.services.team_competition_engine import (
    TeamManagementEngine,
    TeamLeagueEngine,
    TeamMatchEngine,
    Team,
    TeamMember,
    TeamMatch,
)


@contextmanager
def swapped_store(engine_cls, attr, store):
    """把容器的类属性临时替换为给定 store，结束后还原（try/finally 保证还原）。"""
    original = getattr(engine_cls, attr)
    setattr(engine_cls, attr, store)
    try:
        yield store
    finally:
        setattr(engine_cls, attr, original)


def reopen(path, value_type):
    """用同一路径重开一个 store，模拟进程重启后读回落盘数据。"""
    return DataclassJSONStateStore(path=str(path), value_type=value_type)


# ─── 1. 端到端持久化（模拟进程重启） ──────────────────────────────

def test_e2e_team_persists_across_restart(tmp_path):
    """真实业务方法 create_team 写入 → 重开 store → 数据还在。"""
    store = DataclassJSONStateStore(str(tmp_path / "teams.json"), value_type=Team)
    with swapped_store(TeamManagementEngine, "TEAMS", store):
        team = TeamManagementEngine.create_team("战队A", "AAA", "cap1", "队长")
        tid = team.id

    reopened = reopen(tmp_path / "teams.json", Team)
    assert reopened.get(tid) is not None
    assert reopened.get(tid).name == "战队A"
    assert isinstance(reopened.get(tid).captain_id, str)


# ─── 2. 7 处就地修改点（用户列出） + 4 处额外发现，逐处验证落盘 ──

def test_active_quests_contribute_xp_persists(tmp_path):
    store = DataclassJSONStateStore(str(tmp_path / "active_quests.json"), value_type=FriendQuest)
    with swapped_store(FriendQuestEngine, "ACTIVE_QUESTS", store):
        q = FriendQuestEngine.create_quest("u1", "u2")
        FriendQuestEngine.contribute_xp(q.id, "u1", 100)
        FriendQuestEngine.contribute_xp(q.id, "u2", 50)

    rq = reopen(tmp_path / "active_quests.json", FriendQuest).get(q.id)
    assert rq.current_xp == 150
    assert rq.contribution["u1"] == 100
    assert rq.contribution["u2"] == 50


def test_active_sessions_record_answer_persists(tmp_path):
    store = DataclassJSONStateStore(str(tmp_path / "_active_sessions.json"), value_type=SessionMemory)
    with swapped_store(PeakEndEngine, "_active_sessions", store):
        PeakEndEngine.start_session("u1")
        PeakEndEngine.record_answer("u1", True, "数学", 8, 5)
        PeakEndEngine.record_answer("u1", False, "数学", 8, 5)

    rs = reopen(tmp_path / "_active_sessions.json", SessionMemory).get("u1")
    assert rs.total_attempts == 2
    assert rs.total_correct == 1
    assert isinstance(rs.session_start, datetime)


def test_unfinished_get_reminder_persists(tmp_path):
    store = DataclassJSONStateStore(str(tmp_path / "_unfinished.json"), value_type=UnfinishedTask)
    with swapped_store(ZeigarnikEngine, "_unfinished", store):
        ZeigarnikEngine.save_unfinished("u1", "t1", "数学", 5)
        ZeigarnikEngine.get_reminder("u1")

    rs = reopen(tmp_path / "_unfinished.json", UnfinishedTask).get("u1")
    assert rs.reminder_count == 1
    assert isinstance(rs.last_reminded_at, datetime)


def test_goals_monitor_progress_persists(tmp_path):
    store = DataclassJSONStateStore(
        str(tmp_path / "goals.json"), value_type=list[SelfRegulationGoal]
    )
    with swapped_store(SelfRegulationEngine, "GOALS", store):
        SelfRegulationEngine.set_goal("u1", "g1", "每天 20 题", 20, "题")
        SelfRegulationEngine.monitor_progress("u1", "g1", 10)

    rs = reopen(tmp_path / "goals.json", list[SelfRegulationGoal]).get("u1")
    assert isinstance(rs, list)
    g = rs[0]
    assert isinstance(g, SelfRegulationGoal)
    assert g.id == "g1"
    assert g.progress == 0.5


def test_palaces_place_knowledge_persists(tmp_path):
    store = DataclassJSONStateStore(str(tmp_path / "palaces.json"), value_type=MemoryPalace)
    with swapped_store(MemoryPalaceEngine, "PALACES", store):
        MemoryPalaceEngine.create_palace("u1", 0)
        MemoryPalaceEngine.place_knowledge("u1", "勾股定理", "直角三角形")

    rs = reopen(tmp_path / "palaces.json", MemoryPalace).get("u1")
    assert rs.total_items == 1
    assert rs.locations[0]["item"] == "勾股定理"


def test_teams_record_team_contribution_persists(tmp_path):
    store = DataclassJSONStateStore(str(tmp_path / "teams.json"), value_type=Team)
    with swapped_store(TeamManagementEngine, "TEAMS", store):
        team = TeamManagementEngine.create_team("战队A", "AAA", "rcap", "队长")
        TeamManagementEngine.join_team(team.id, "rm1", "小明")
        TeamLeagueEngine.record_team_contribution(team.id, "rm1", "数学", 50)

    rs = reopen(tmp_path / "teams.json", Team).get(team.id)
    assert rs.total_xp == 50
    assert rs.subject_scores["数学"] == 50
    assert len(rs.members) == 2
    m1 = next(m for m in rs.members if m.user_id == "rm1")
    assert m1.contribution_xp == 50


def test_matches_contribute_to_match_persists(tmp_path):
    store = DataclassJSONStateStore(str(tmp_path / "matches.json"), value_type=TeamMatch)
    with swapped_store(TeamMatchEngine, "MATCHES", store):
        ta = TeamManagementEngine.create_team("A", "AAA", "ca", "队长A")
        tb = TeamManagementEngine.create_team("B", "BBB", "cb", "队长B")
        m = TeamMatchEngine.create_match(ta.id, tb.id, "数学")
        TeamMatchEngine.contribute_to_match(m["match_id"], ta.id, "u1", 30)

    rs = reopen(tmp_path / "matches.json", TeamMatch).get(m["match_id"])
    assert rs.score_a == 30
    assert rs.participants_a["u1"] == 30


# ─── 额外发现的就地修改点（用户未列出，但同属静默丢失，一并修掉验证） ──

def test_box_states_open_box_persists(tmp_path):
    """BOX_STATES: open_box 就地改 state，open_box_for_user 已补 set 回写。"""
    store = DataclassJSONStateStore(str(tmp_path / "box_states.json"), value_type=TreasureBoxState)
    with swapped_store(GamificationService, "BOX_STATES", store):
        GamificationService.get_box_state_for_user("u1")
        GamificationService.open_box_for_user("u1", current_topic="数学")

    rs = reopen(tmp_path / "box_states.json", TreasureBoxState).get("u1")
    assert rs.total_boxes_opened == 1
    assert rs.questions_since_last_box == 0


def test_goals_set_goal_append_persists(tmp_path):
    """GOALS: set_goal 先 set 空 list 再 append，append 若未回写则丢目标。"""
    store = DataclassJSONStateStore(
        str(tmp_path / "goals2.json"), value_type=list[SelfRegulationGoal]
    )
    with swapped_store(SelfRegulationEngine, "GOALS", store):
        SelfRegulationEngine.set_goal("u1", "g1", "目标一", 20, "题")
        SelfRegulationEngine.set_goal("u1", "g2", "目标二", 30, "题")

    rs = reopen(tmp_path / "goals2.json", list[SelfRegulationGoal]).get("u1")
    assert isinstance(rs, list)
    assert len(rs) == 2
    assert {g.id for g in rs} == {"g1", "g2"}


def test_teams_join_team_persists(tmp_path):
    """TEAMS: join_team append 成员后必须 set，否则成员丢失。"""
    store = DataclassJSONStateStore(str(tmp_path / "teams_join.json"), value_type=Team)
    with swapped_store(TeamManagementEngine, "TEAMS", store):
        team = TeamManagementEngine.create_team("战队A", "AAA", "jcap", "队长")
        TeamManagementEngine.join_team(team.id, "jm1", "小明")

    rs = reopen(tmp_path / "teams_join.json", Team).get(team.id)
    assert any(m.user_id == "jm1" for m in rs.members)


def test_teams_leave_team_persists(tmp_path):
    """TEAMS: leave_team 重排 members 后必须 set，否则成员未真正退出。"""
    store = DataclassJSONStateStore(str(tmp_path / "teams_leave.json"), value_type=Team)
    with swapped_store(TeamManagementEngine, "TEAMS", store):
        team = TeamManagementEngine.create_team("战队A", "AAA", "lcap", "队长")
        TeamManagementEngine.join_team(team.id, "lm1", "小明")
        TeamManagementEngine.leave_team("lm1")

    rs = reopen(tmp_path / "teams_leave.json", Team).get(team.id)
    assert all(m.user_id != "lm1" for m in rs.members)


# ─── 3. 类型还原正确（嵌套 dataclass / datetime） ────────────────

def test_teams_members_restored_as_dataclass_instances(tmp_path):
    """嵌套 List[dataclass] 还原为 TeamMember 实例，而非 dict（此前是崩溃缺口）。"""
    store = DataclassJSONStateStore(str(tmp_path / "teams_type.json"), value_type=Team)
    with swapped_store(TeamManagementEngine, "TEAMS", store):
        team = TeamManagementEngine.create_team("战队A", "AAA", "cap1", "队长")
        TeamManagementEngine.join_team(team.id, "m1", "小明")

    rs = reopen(tmp_path / "teams_type.json", Team).get(team.id)
    assert all(isinstance(m, TeamMember) for m in rs.members)
    # 可访问 dataclass 属性而非走 dict 下标
    assert rs.members[0].user_id == "cap1"


def test_goals_deadline_restored_as_datetime(tmp_path):
    """SelfRegulationGoal.deadline 重开后是 datetime 实例，而非字符串。"""
    store = DataclassJSONStateStore(
        str(tmp_path / "goals_type.json"), value_type=list[SelfRegulationGoal]
    )
    with swapped_store(SelfRegulationEngine, "GOALS", store):
        SelfRegulationEngine.set_goal("u1", "g1", "目标", 20, "题", deadline_days=7)

    rs = reopen(tmp_path / "goals_type.json", list[SelfRegulationGoal]).get("u1")
    assert isinstance(rs[0].deadline, datetime)


# ─── 4. GOALS 顶层 list 实例 ─────────────────────────────────────

def test_goals_top_level_list_is_dataclass_list(tmp_path):
    store = DataclassJSONStateStore(
        str(tmp_path / "goals_list.json"), value_type=list[SelfRegulationGoal]
    )
    with swapped_store(SelfRegulationEngine, "GOALS", store):
        SelfRegulationEngine.set_goal("u1", "g1", "目标", 20, "题")

    rs = reopen(tmp_path / "goals_list.json", list[SelfRegulationGoal]).get("u1")
    assert isinstance(rs, list)
    assert all(isinstance(g, SelfRegulationGoal) for g in rs)
    assert rs[0].id == "g1"


# ─── 5. 默认后端仍是内存（保证既有测试行为不变） ──────────────────

def test_default_backend_is_memory(monkeypatch):
    monkeypatch.delenv("LEARNFLOW_STATE_BACKEND", raising=False)
    store = default_state_store("whatever", value_type=FriendQuest)
    assert isinstance(store, MemoryStateStore)
