"""DataclassJSONStateStore 与 default_state_store 工厂的测试。

覆盖：dataclass 往返、跨实例持久化、Enum/datetime/set/tuple 往返、
value_type 未给返回 dict、数据损坏容错、工厂三态、原子写无 .tmp 残留。
所有用例使用 ``tmp_path``，不污染仓库。
"""
from __future__ import annotations

import enum
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pytest

from app.services.state_store import (
    DataclassJSONStateStore,
    MemoryStateStore,
    default_state_store,
)


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"


@dataclass
class Player:
    """只有 JSON 原生字段 —— 用于「原样读回」精确相等。"""

    uid: str
    level: int
    hp: float
    active: bool
    nick: str = ""


@dataclass
class Rich:
    """含 Enum / datetime / set / tuple / list / dict 字段。"""

    color: Color
    when: datetime
    tags: set
    coords: tuple
    items: list
    meta: dict


WHEN = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ─── 1. dataclass 写入后能原样读回（字段值全部相等） ───────────────
def test_dataclass_roundtrip_exact(tmp_path):
    p = tmp_path / "exact.json"
    s = DataclassJSONStateStore(str(p), value_type=Player)
    original = Player(uid="u1", level=7, hp=3.5, active=True, nick="豆")
    s.set("k", original)

    got = s.get("k")
    assert isinstance(got, Player)
    assert got.uid == "u1"
    assert got.level == 7
    assert got.hp == 3.5
    assert got.active is True
    assert got.nick == "豆"


def test_get_missing_key_returns_none(tmp_path):
    p = tmp_path / "miss.json"
    s = DataclassJSONStateStore(str(p), value_type=Player)
    assert s.get("nope") is None


# ─── 2. 跨实例持久化（“真落库”判据） ─────────────────────────────
def test_cross_instance_persistence(tmp_path):
    p = tmp_path / "persist.json"
    s1 = DataclassJSONStateStore(str(p), value_type=Player)
    s1.set("k", Player(uid="u2", level=9, hp=1.0, active=False))
    s1.close()

    # 用同一路径 new 一个新 store，应当读回之前写的值
    s2 = DataclassJSONStateStore(str(p), value_type=Player)
    got = s2.get("k")
    assert isinstance(got, Player)
    assert got.uid == "u2"
    assert got.level == 9
    assert got.active is False


# ─── 3. Enum / datetime / set / tuple 字段的往返 ──────────────────
def test_rich_field_roundtrip(tmp_path):
    p = tmp_path / "rich.json"
    s = DataclassJSONStateStore(str(p), value_type=Rich)
    original = Rich(
        color=Color.RED,
        when=WHEN,
        tags={"x", "y"},
        coords=(1, 2, 3),
        items=[1, 2],
        meta={"a": 1},
    )
    s.set("k", original)

    got = s.get("k")
    assert isinstance(got, Rich)
    # 类型感知还原：_from_jsonable 按字段注解把 JSON 原生值还原回原类型。
    # 这对研究数据是必要的——时间戳若停留在字符串，下游比较/排序/聚合会静默出错；
    # Enum 若停留在裸 value，``is`` 比较与 ``.value`` 访问都会失败。
    assert got.color is Color.RED           # Enum：value → 成员
    assert got.when == WHEN                 # datetime：ISO 字符串 → datetime
    assert got.tags == {"x", "y"}           # set：list → set
    assert got.coords == (1, 2, 3)          # tuple：list → tuple
    assert got.items == [1, 2]
    assert got.meta == {"a": 1}

    # 因此读回值与原对象完全相等（dataclass 的 __eq__ 逐字段比较）
    assert got == original


# ─── 4. value_type 未给时 get 返回 dict ───────────────────────────
def test_no_value_type_returns_dict(tmp_path):
    p = tmp_path / "nodict.json"
    s = DataclassJSONStateStore(str(p))  # 未给 value_type
    s.set("k", Player(uid="u3", level=2, hp=9.0, active=True))

    got = s.get("k")
    assert isinstance(got, dict)
    assert got["uid"] == "u3"
    assert got["level"] == 2


# ─── 5. 数据损坏时不崩溃，回退到空或原始值 ───────────────────────
def test_corrupt_json_file_does_not_crash(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text("{ this is not valid json ", encoding="utf-8")

    # 构造时 _load 捕获 JSONDecodeError → 视为空，不应抛异常
    s = DataclassJSONStateStore(str(p), value_type=Player)
    assert s.get("k") is None


def test_incompatible_shape_falls_back_to_dict(tmp_path):
    p = tmp_path / "incompat.json"
    # 合法的 JSON，但字段与 Player 不匹配
    p.write_text('{"k": {"foo": "bar"}}', encoding="utf-8")

    s = DataclassJSONStateStore(str(p), value_type=Player)
    got = s.get("k")
    # 重建失败 → 回退返回原始 dict，不抛异常
    assert got == {"foo": "bar"}
    assert isinstance(got, dict)


# ─── 6. default_state_store 三态 ─────────────────────────────────
@pytest.fixture
def backend_state_dir():
    """返回 default_state_store 在 json 模式下会写入的 artifacts/state 目录，便于清理。"""
    from app.services import state_store as st

    root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(st.__file__)))
    )
    return os.path.join(root, "artifacts", "state")


def test_factory_memory(monkeypatch):
    monkeypatch.setenv("LEARNFLOW_STATE_BACKEND", "memory")
    s = default_state_store("any_name")
    assert isinstance(s, MemoryStateStore)


def test_factory_json(monkeypatch, backend_state_dir):
    monkeypatch.setenv("LEARNFLOW_STATE_BACKEND", "json")
    name = "test_factory_json_unique"
    s = default_state_store(name, value_type=Player)
    assert isinstance(s, DataclassJSONStateStore)
    assert s._path.endswith(os.path.join("artifacts", "state", name + ".json"))

    # 清理：只删我们这次可能留下的文件/空目录，绝不碰既有文件
    try:
        if os.path.exists(s._path):
            os.remove(s._path)
        if os.path.isdir(backend_state_dir) and not os.listdir(backend_state_dir):
            os.rmdir(backend_state_dir)
    except OSError:
        pass


def test_factory_unknown_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("LEARNFLOW_STATE_BACKEND", "totally_bogus")
    s = default_state_store("any_name")
    assert isinstance(s, MemoryStateStore)


def test_factory_default_is_memory_when_unset(monkeypatch):
    monkeypatch.delenv("LEARNFLOW_STATE_BACKEND", raising=False)
    s = default_state_store("any_name")
    assert isinstance(s, MemoryStateStore)


# ─── 7. 原子写：写入后不留 .tmp 残留 ─────────────────────────────
def test_atomic_write_leaves_no_tmp(tmp_path):
    p = tmp_path / "atomic.json"
    s = DataclassJSONStateStore(str(p), value_type=Player)
    s.set("k", Player(uid="u4", level=1, hp=1.0, active=True))
    s.close()

    files = os.listdir(str(tmp_path))
    assert "atomic.json" in files
    assert not any(f.endswith(".tmp") for f in files)


# ─── 8. mutate()：就地修改问题的官方解法 ─────────────────────────
# 背景：内存后端 get() 返回对象本身，调用方就地改即生效；
# 文件后端必须显式 set() 才刷盘。mutate() 把「读—改—写」收敛成一个
# 原子操作，让两种后端的语义一致，消除静默丢数据的风险。


def test_mutate_writes_back_without_explicit_set(tmp_path):
    """调用方在 mutate 回调里就地改对象，不调用 set，改动也必须落盘。"""
    p = tmp_path / "mutate.json"
    s = DataclassJSONStateStore(str(p), value_type=Player)
    s.set("u1", Player(uid="u1", level=1, hp=100.0, active=True))

    def _level_up(cur):
        # 刻意「就地修改并返回」，模拟既有容器的调用习惯
        cur.level += 1
        return cur

    s.mutate("u1", _level_up)
    s.close()

    # 重新打开一个 store：level 必须是 2，而不是 1
    s2 = DataclassJSONStateStore(str(p), value_type=Player)
    assert s2.get("u1").level == 2


def test_mutate_on_missing_key_receives_none(tmp_path):
    """key 不存在时，回调收到 None，可自行决定初始值。"""
    s = DataclassJSONStateStore(str(tmp_path / "m2.json"), value_type=Player)

    def _create(cur):
        assert cur is None
        return Player(uid="new", level=1, hp=100.0, active=True)

    got = s.mutate("nobody", _create)
    assert got.uid == "new"
    assert "nobody" in s.keys()


def test_mutate_returning_none_deletes_key(tmp_path):
    """回调返回 None 等价于删除该条目。"""
    s = DataclassJSONStateStore(str(tmp_path / "m3.json"), value_type=Player)
    s.set("gone", Player(uid="gone", level=9, hp=1.0, active=True))
    assert "gone" in s.keys()

    s.mutate("gone", lambda cur: None)
    assert "gone" not in s.keys()
    assert s.get("gone") is None


def test_mutate_returns_updated_value(tmp_path):
    """返回值是写回后的新值，方便调用方链式使用。"""
    s = DataclassJSONStateStore(str(tmp_path / "m4.json"), value_type=Player)
    s.set("u", Player(uid="u", level=3, hp=50.0, active=True))
    got = s.mutate("u", lambda cur: Player(uid=cur.uid, level=cur.level + 2, hp=cur.hp, active=cur.active))
    assert got.level == 5
    assert s.get("u").level == 5


def test_mutate_inherited_by_memory_store():
    """mutate 定义在 ABC 上，内存后端同样可用，保证两种后端可互换。"""
    s = MemoryStateStore()
    s.set("k", Player(uid="k", level=1, hp=1.0, active=True))
    s.mutate("k", lambda cur: Player(uid=cur.uid, level=cur.level + 1, hp=cur.hp, active=cur.active))
    assert s.get("k").level == 2


# ─── 9. 泛型容器还原（本次修复的反序列化缺口） ─────────────────────
# 背景：_from_jsonable 此前只按字段注解还原 Enum/datetime/嵌套 dataclass/set/tuple，
# 不处理泛型容器。这会让 List[SomeDataclass] / Optional[datetime] / Dict[str, X] /
# 顶层 List[X] 等值读回后停留在 JSON 原生结构，下游访问属性直接 AttributeError——
# 正是把 6 个游戏化状态容器切到可落盘后端时会触发的线上崩溃。下面逐项覆盖。

# 复用既有 Color/Player/Rich 之外的专用 dataclass，避免与上面语义耦合。
@dataclass
class TeamMember:
    user_id: str
    score: int


@dataclass
class Team:
    name: str
    members: List[TeamMember]          # List[X]
    subject_scores: Dict[str, int]     # Dict[K, V]（V 为 JSON 原生，侥幸可用）
    captain: Optional[TeamMember] = None  # Optional[X]


@dataclass
class PeerBoard:
    peers: Dict[str, TeamMember]       # Dict[str, X]


@dataclass
class SelfRegulationGoal:
    id: str
    deadline: Optional[datetime] = None  # Optional[datetime]


@dataclass
class GoalList:
    goals: List[SelfRegulationGoal]                 # 普通 List[X]
    maybe_goals: Optional[List[SelfRegulationGoal]] = None  # Optional[List[X]]
    grouped: Dict[str, List[SelfRegulationGoal]] = None      # Dict[str, List[X]]


@dataclass
class Bare:
    """字段注解为裸 list / dict（get_args 为空）。"""
    items: list
    mapping: dict


def test_list_dataclass_field_roundtrip(tmp_path):
    """List[SomeDataclass] 字段：读回后元素是 dataclass 实例而非 dict。"""
    p = tmp_path / "team.json"
    s = DataclassJSONStateStore(str(p), value_type=Team)
    team = Team(
        name="A",
        members=[TeamMember("u1", 10), TeamMember("u2", 20)],
        subject_scores={"math": 5},
    )
    s.set("t", team)

    got = s.get("t")
    assert isinstance(got, Team)
    # 关键判据：能访问 .user_id 且 isinstance 为 TeamMember（不是 dict）
    assert isinstance(got.members[0], TeamMember)
    assert got.members[0].user_id == "u1"
    assert got.members[0].score == 10
    assert got.members[1].user_id == "u2"
    # subject_scores 的 V 是 int，原样保留
    assert got.subject_scores == {"math": 5}


def test_optional_datetime_field(tmp_path):
    """Optional[datetime] 字段：有值读回是 datetime；None 读回仍是 None。"""
    p = tmp_path / "goal.json"
    s = DataclassJSONStateStore(str(p), value_type=SelfRegulationGoal)
    s.set("g1", SelfRegulationGoal(id="g1", deadline=WHEN))
    s.set("g2", SelfRegulationGoal(id="g2", deadline=None))

    got1 = s.get("g1")
    got2 = s.get("g2")
    assert isinstance(got1.deadline, datetime)   # 不是 str
    assert got1.deadline == WHEN
    assert got2.deadline is None                 # None 原样返回


def test_optional_dataclass_field(tmp_path):
    """Optional[X]（X 为 dataclass）：有值还原为实例，None 原样返回。"""
    p = tmp_path / "captain.json"
    s = DataclassJSONStateStore(str(p), value_type=Team)
    s.set("t1", Team(name="A", members=[], subject_scores={}, captain=TeamMember("cap", 99)))
    s.set("t2", Team(name="B", members=[], subject_scores={}, captain=None))

    assert isinstance(s.get("t1").captain, TeamMember)
    assert s.get("t1").captain.user_id == "cap"
    assert s.get("t2").captain is None


def test_dict_dataclass_value(tmp_path):
    """Dict[str, SomeDataclass]：value 被还原为实例（key 保持字符串）。"""
    p = tmp_path / "peer.json"
    s = DataclassJSONStateStore(str(p), value_type=PeerBoard)
    s.set("b", PeerBoard(peers={"u1": TeamMember("u1", 99)}))

    got = s.get("b")
    assert isinstance(got, PeerBoard)
    assert isinstance(got.peers["u1"], TeamMember)   # value 已还原
    assert got.peers["u1"].score == 99
    assert "u1" in got.peers                          # key 未被改写


def test_nested_generic_combos(tmp_path):
    """嵌套组合：Optional[List[X]]、Dict[str, List[X]] 层层还原。"""
    p = tmp_path / "gl.json"
    s = DataclassJSONStateStore(str(p), value_type=GoalList)
    gl = GoalList(
        goals=[SelfRegulationGoal("a"), SelfRegulationGoal("b", deadline=WHEN)],
        maybe_goals=[SelfRegulationGoal("c")],
        grouped={"cat": [SelfRegulationGoal("d")]},
    )
    s.set("gl", gl)

    got = s.get("gl")
    assert isinstance(got, GoalList)
    # Optional[List[X]]：整体先剥 Optional，再逐元素还原
    assert isinstance(got.maybe_goals, list)
    assert isinstance(got.maybe_goals[0], SelfRegulationGoal)
    assert got.maybe_goals[0].id == "c"
    # Dict[str, List[X]]：value 是 list，list 元素再还原
    assert isinstance(got.grouped["cat"][0], SelfRegulationGoal)
    assert got.grouped["cat"][0].id == "d"
    # 普通 List[X] 也正常
    assert isinstance(got.goals[1], SelfRegulationGoal)
    assert got.goals[1].deadline == WHEN


def test_top_level_list_value_type(tmp_path):
    """顶层 value_type 本身就是 List[X]（GOALS 容器的真实形态）。

    此前 _from_jsonable 在 raw 不是 dict 时直接短路返回，导致 List[X] 永远拿不到
    还原。这里用 List[SelfRegulationGoal] 构造 store，读回元素必须是实例。
    """
    p = tmp_path / "goals.json"
    s = DataclassJSONStateStore(str(p), value_type=List[SelfRegulationGoal])
    goals = [SelfRegulationGoal("g1"), SelfRegulationGoal("g2", deadline=WHEN)]
    s.set("GOALS", goals)

    got = s.get("GOALS")
    assert isinstance(got, list)
    assert len(got) == 2
    # 关键判据：元素是 SelfRegulationGoal 实例而非 dict
    assert all(isinstance(g, SelfRegulationGoal) for g in got)
    assert got[0].id == "g1"
    assert got[1].deadline == WHEN


def test_generic_fault_tolerance_shape_mismatch(tmp_path):
    """容错：泛型位置存入不符合形状的数据时不抛异常，原样返回。"""
    p = tmp_path / "ft.json"
    s = DataclassJSONStateStore(str(p), value_type=Team)
    # members 字段注解是 List[TeamMember]，这里故意塞一个 int
    s.set("t", {"name": "X", "members": 5, "subject_scores": {"math": 1}})

    got = s.get("t")
    # List[X] 分支：value=5 不是 list → 原样返回，绝不让调用方崩溃
    assert isinstance(got, Team)
    assert got.members == 5


def test_bare_list_dict_hint_no_crash(tmp_path):
    """裸 list / dict 注解（get_args 为空）不炸，元素原样返回。"""
    p = tmp_path / "bare.json"
    s = DataclassJSONStateStore(str(p), value_type=Bare)
    s.set("b", Bare(items=[1, {"x": 2}], mapping={"k": {"y": 3}}))

    got = s.get("b")
    assert isinstance(got, Bare)
    assert got.items == [1, {"x": 2}]       # 裸 list：不强行当 dataclass 还原
    assert got.mapping == {"k": {"y": 3}}   # 裸 dict：不强行还原 value
