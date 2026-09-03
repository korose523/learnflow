"""state_store 与 BOX_STATES 迁移 / 技能树格式转换的测试"""
import pytest

from app.services.state_store import (
    StateStore,
    MemoryStateStore,
    JSONFileStateStore,
)
from app.services import gamification_service
from app.services.gamification_service import GamificationService
from app.services.learning_orchestrator import _skilltree_repo_format


def test_memory_state_store_crud():
    store: StateStore = MemoryStateStore()
    assert store.get("missing") is None
    assert store.keys() == []

    store.set("a", 1)
    store.set("b", {"x": 2})
    assert store.get("a") == 1
    assert store.get("b") == {"x": 2}
    assert set(store.keys()) == {"a", "b"}

    store.delete("a")
    assert store.get("a") is None
    assert store.keys() == ["b"]

    store.close()  # 无副作用, 不应抛错


def test_json_file_state_store_roundtrip(tmp_path):
    path = str(tmp_path / "state.json")
    store = JSONFileStateStore(path)
    store.set("user:1", {"level": 3, "xp": 42})
    store.set("user:2", [1, 2, 3])
    store.set("name", "小明")
    store.close()

    # 重新打开一个实例, 验证真正落库 (磁盘读取)
    reopened = JSONFileStateStore(path)
    assert reopened.get("user:1") == {"level": 3, "xp": 42}
    assert reopened.get("user:2") == [1, 2, 3]
    assert reopened.get("name") == "小明"
    assert set(reopened.keys()) == {"user:1", "user:2", "name"}
    reopened.close()


def test_box_states_uses_store():
    # BOX_STATES 已迁移为 StateStore 后端
    assert isinstance(GamificationService.BOX_STATES, StateStore)
    assert isinstance(GamificationService.BOX_STATES, MemoryStateStore)

    uid = "state_store_test_user"
    # 访问器: 首次访问创建默认状态 (set)
    s1 = GamificationService.get_box_state_for_user(uid)
    s1.questions_since_last_box = 2
    # 再次访问应返回同一对象 (get), 状态在内存中保持一致
    s2 = GamificationService.get_box_state_for_user(uid)
    assert s2 is s1
    assert s2.questions_since_last_box == 2
    # 容器记录了该 user key
    assert uid in GamificationService.BOX_STATES.keys()


def test_skilltree_repo_format():
    assert _skilltree_repo_format(
        {"active_recall": {"level": 5, "times_used": 12}}
    ) == {"active_recall": {"proficiency": 0.5, "level": 5, "total_uses": 12}}
