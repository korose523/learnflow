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


def test_skilltree_repo_format_accepts_engine_view():
    """回归: SkillTreeEngine.get_skill_tree 的引擎视图结构不再崩溃。

    历史缺陷 —— get_skill_tree 返回
    {"meta_level": int, ..., "categories": {cat: [{id, level, times_used, ...}]}},
    而旧版 _skilltree_repo_format 把它当扁平结构遍历, 首个键 "meta_level" 的值为
    int, 触发 AttributeError。凡 db 非 None 的提交路径必崩, 而既有单测只覆盖扁平
    入参故未暴露。本测试冻结两种形状的双重契约。
    """
    from app.services.meta_learning_skilltree import SkillTreeEngine

    uid = "skilltree_engine_view_u"
    SkillTreeEngine.PLAYER_SKILLS.delete(uid)
    try:
        SkillTreeEngine.init_player_skills(uid)
        tree = SkillTreeEngine.get_skill_tree(uid)

        # 引擎视图结构的顶层键不是 skill_id, 这是缺陷的根源
        assert "categories" in tree
        assert isinstance(tree["meta_level"], int)

        payload = _skilltree_repo_format(tree)

        assert payload, "引擎视图结构应被展平为非空映射"
        assert "meta_level" not in payload, "元数据键不得混入技能条目"
        # 16 个技能树节点 (与 count_verification 的 skill_tree_nodes 一致)
        assert len(payload) == 16
        for skill_id, data in payload.items():
            assert set(data) == {"proficiency", "level", "total_uses"}
            assert isinstance(data["level"], int)
            assert isinstance(data["total_uses"], int)
            assert 0.0 <= data["proficiency"] <= 1.0
        assert payload["active_recall"] == {
            "proficiency": 0.1, "level": 1, "total_uses": 0}
    finally:
        SkillTreeEngine.PLAYER_SKILLS.delete(uid)


def test_skilltree_repo_format_edge_cases():
    """空输入 / 空 categories / 非字典值均不得抛异常"""
    assert _skilltree_repo_format({}) == {}
    assert _skilltree_repo_format({"categories": {}}) == {}
    assert _skilltree_repo_format({"categories": {"memory": []}}) == {}
    # 非字典条目与缺失 id 的条目应被跳过而非崩溃
    assert _skilltree_repo_format({"categories": {"memory": [None, {"level": 2}]}}) == {}
    # 扁平结构中的非字典值同样跳过 (防御历史形状污染)
    assert _skilltree_repo_format({"junk": 3}) == {}
