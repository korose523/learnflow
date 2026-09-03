"""学习方法注册表测试 — 可复现性与数字诚信

覆盖目标:
1. 注册表是全量 23 个方法的单一事实源 (ID 连续无缺口、key 唯一)
2. 每条 ``impl_ref`` 都指向**真实存在**的代码位置 (importlib 动态导入校验)
3. 23 个方法全部可被 ``render()`` 统一调度, 且输出必然锚定当前知识点
4. 每日挑战可复现 —— 同一天 100 次调用必须是同一个方法
"""
import json
from datetime import date, datetime

import pytest

from app.services import method_registry


# ────────────────────────────────────────────────────────────
# 工具: 独立解析 impl_ref (不复用 registry 的 resolver, 避免自证)
# ────────────────────────────────────────────────────────────

_MODULE_BY_SHORT_NAME = {
    "learning_methods_engine.py": "app.services.learning_methods_engine",
    "advanced_methods_engine.py": "app.services.advanced_methods_engine",
    "learning_methods_engine_v3.py": "app.services.learning_methods_engine_v3",
}


def _resolve(impl_ref: str):
    """把 ``module.py:Sym.attr[0]`` 解析成真实对象, 解析不到就 raise"""
    import importlib
    import re

    m = re.match(r"^(?P<module>[\w.]+\.py):(?P<path>.+)$", impl_ref)
    assert m, f"impl_ref 格式非法: {impl_ref!r}"

    short = m.group("module")
    assert short in _MODULE_BY_SHORT_NAME, f"未登记的模块: {short!r}"
    module = importlib.import_module(_MODULE_BY_SHORT_NAME[short])

    obj = None
    for token in re.finditer(r"(?P<name>[A-Za-z_]\w*)|\[(?P<index>-?\d+)\]", m.group("path")):
        if obj is None:
            assert token.group("name"), f"impl_ref 必须以符号名开头: {impl_ref!r}"
            obj = getattr(module, token.group("name"))
        elif token.group("name"):
            obj = getattr(obj, token.group("name"))
        else:
            obj = obj[int(token.group("index"))]
    assert obj is not None, f"impl_ref 未解析出符号: {impl_ref!r}"
    return obj


def _frozen_datetime_cls(day: date):
    """构造一个 now() 恒返回 ``day`` 的 datetime 子类, 用于冻结"今天" """
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: D102
            return cls(day.year, day.month, day.day, tzinfo=tz)
    return _FrozenDatetime


# ────────────────────────────────────────────────────────────
# 1. 注册表完整性
# ────────────────────────────────────────────────────────────

class TestRegistryIntegrity:
    def test_count_is_23(self, registry):
        assert registry.count() == 23

    def test_keys_unique_and_snake_case(self, registry):
        all_keys = registry.keys()
        assert len(all_keys) == 23
        assert len(set(all_keys)) == 23, "method key 存在重复"
        for key in all_keys:
            assert key == key.lower() and key.replace("_", "").isalnum(), f"非 snake_case: {key}"

    def test_ids_contiguous_no_gap(self, registry):
        ids = registry.ids()
        assert len(set(ids)) == 23, "方法 ID 存在重复"
        assert ids == [f"LF-L{i:02d}" for i in range(1, 24)], f"ID 有缺口或错位: {ids}"

    def test_all_specs_have_required_fields(self, registry):
        required = ("id", "key", "name_zh", "category", "evidence_ref",
                    "impl_ref", "delivery", "difficulty")
        for spec in registry.all_methods():
            for fname in required:
                value = getattr(spec, fname, None)
                assert value not in (None, "", ()), f"{spec.key} 缺字段: {fname}"
            assert spec.category in registry.CATEGORIES
            assert spec.difficulty in registry.DIFFICULTIES
            assert set(spec.delivery) <= set(registry.DELIVERIES)
            assert spec.evidence_ref.strip(), f"{spec.key} 的 evidence_ref 为空"
            assert spec.variants, f"{spec.key} 没有任何变体"

    def test_catalog_rows_shape(self, registry):
        rows = registry.catalog_rows()
        assert len(rows) == 23
        for row in rows:
            assert set(row) == {
                "id", "key", "name_zh", "category", "evidence_ref", "impl_ref",
            }
            assert row["id"].startswith("LF-L")

    def test_category_and_delivery_queries(self, registry):
        buckets = [registry.by_category(c) for c in registry.CATEGORIES]
        assert sum(len(b) for b in buckets) == 23, "分类未覆盖全部方法"
        for spec in registry.all_methods():
            assert spec in registry.by_category(spec.category)
            for delivery in spec.delivery:
                assert spec in registry.by_delivery(delivery)

    def test_mind_mapping_is_registered(self, registry):
        """历史上唯一永远调度不到的方法 —— 必须在注册表里"""
        spec = registry.get("mind_mapping")
        assert spec.id == "LF-L23"
        assert spec.key in registry.keys()


# ────────────────────────────────────────────────────────────
# 2. impl_ref 真实性 (importlib 动态导入, 非字符串检查)
# ────────────────────────────────────────────────────────────

class TestImplRefResolves:
    @pytest.mark.parametrize("spec", [
        pytest.param(s, id=s.id) for s in __import__(
            "app.services.method_registry", fromlist=["SPECS"]
        ).SPECS
    ])
    def test_impl_ref_points_to_real_symbol(self, spec):
        obj = _resolve(spec.impl_ref)
        assert obj is not None
        if isinstance(obj, dict):
            # tip 条目: 必须真是该方法的文案, 而不只是"下标存在"
            assert obj["method"] == spec.key, (
                f"{spec.id} 的 impl_ref 指向了别的方法: {obj['method']}"
            )
            assert obj["difficulty"] == spec.difficulty
        else:
            assert callable(obj), f"{spec.id} 的 impl_ref 应指向可调用对象"

    def test_variant_refs_resolve(self, registry):
        for spec in registry.all_methods():
            for variant in spec.variants:
                assert _resolve(variant.impl_ref) is not None

    def test_memory_palace_has_two_variants(self, registry):
        spec = registry.get("memory_palace")
        assert [v.difficulty for v in spec.variants] == ["advanced", "beginner"]

    def test_bad_impl_ref_raises(self, registry):
        with pytest.raises(ValueError):
            registry.resolve_impl_ref("not_a_real_ref")
        with pytest.raises(ValueError):
            registry.resolve_impl_ref("learning_methods_engine.py:METHOD_TIPS[999]")


# ────────────────────────────────────────────────────────────
# 3. 调度层 render()
# ────────────────────────────────────────────────────────────

class TestRender:
    @pytest.mark.parametrize("key", sorted(
        s.key for s in __import__(
            "app.services.method_registry", fromlist=["SPECS"]
        ).SPECS
    ))
    def test_render_all_methods(self, registry, key):
        result = registry.render(key, "分数运算", sub_topics=["通分", "约分"])
        assert isinstance(result, dict)
        assert result["method_id"] == registry.get(key).id
        assert result["method_key"] == key
        assert result["topic"] == "分数运算"

    def test_render_grounds_topic(self, registry):
        """知识点必须出现在输出里 —— 不允许被静默丢弃"""
        for key in registry.keys():
            result = registry.render(key, "分数运算")
            blob = json.dumps(result, ensure_ascii=False)
            assert "分数运算" in blob, (
                f"{key} 的输出没有锚定知识点: {result}"
            )

    def test_render_topic_grounding_even_without_placeholder(self, registry):
        """pomodoro 是唯一 detail/action 无 {concept} 占位符的 tip"""
        result = registry.render("pomodoro", "二次函数")
        assert "二次函数" in result["detail"]
        assert "二次函数" in result["action"]

    def test_render_mind_mapping(self, registry):
        result = registry.render("mind_mapping", "代数", sub_topics=["方程", "因式分解"])
        assert result["method_id"] == "LF-L23"
        assert result["nodes"][0]["label"] == "代数"
        assert len(result["nodes"]) == 3

    def test_render_variant_selection(self, registry):
        advanced = registry.render("memory_palace", "几何")
        beginner = registry.render("memory_palace", "几何", difficulty="beginner")
        assert advanced["difficulty"] == "advanced"
        assert beginner["difficulty"] == "beginner"
        assert advanced["title"] != beginner["title"]

    def test_render_unknown_key_raises(self, registry):
        with pytest.raises(KeyError):
            registry.render("no_such_method", "代数")

    def test_render_respects_kill_switch(self, registry):
        key = registry.keys()[0]
        registry.set_enabled(key, False)
        try:
            with pytest.raises(registry.MethodDisabledError):
                registry.render(key, "代数")
            assert registry.is_enabled(key) is False
            assert key in registry.disabled_keys()
            assert len(registry.enabled_methods()) == 22
        finally:
            registry.set_enabled(key, True)
        assert registry.is_enabled(key) is True


# ────────────────────────────────────────────────────────────
# 4. 每日挑战可复现性 (回归测试)
# ────────────────────────────────────────────────────────────

class TestDailyChallengeReproducibility:
    def test_same_day_100_calls_same_method(self, registry):
        """历史 bug: 对 set→list 的结果取模, 同一天不同进程结果不同"""
        from app.services.learning_methods_engine import LearningMethodEngine

        seen = {
            LearningMethodEngine.get_daily_method_challenge("u1")["method"]
            for _ in range(100)
        }
        assert len(seen) == 1, f"同一天返回了多个方法: {seen}"

    def test_deterministic_under_frozen_date(self, registry, monkeypatch):
        from app.services import learning_methods_engine as engine

        monkeypatch.setattr(engine, "datetime", _frozen_datetime_cls(date(2026, 3, 15)))
        expected_key = registry.keys()[date(2026, 3, 15).toordinal() % 23]

        results = {
            engine.LearningMethodEngine.get_daily_method_challenge("u1")["method"]
            for _ in range(100)
        }
        assert results == {expected_key}

    def test_full_pool_reachable_within_23_days(self, registry, monkeypatch):
        """23 天周期内 23 个方法都要轮到 —— 证明思维导图进得来"""
        from app.services import learning_methods_engine as engine

        seen = set()
        for offset in range(23):
            day = date(2026, 1, 1).fromordinal(date(2026, 1, 1).toordinal() + offset)
            monkeypatch.setattr(engine, "datetime", _frozen_datetime_cls(day))
            seen.add(engine.LearningMethodEngine.get_daily_method_challenge("u1")["method"])

        assert seen == set(registry.keys()), f"有方法永远轮不到: {set(registry.keys()) - seen}"
        assert "mind_mapping" in seen

    def test_challenge_field_signature_unchanged(self, registry):
        from app.services.learning_methods_engine import LearningMethodEngine

        challenge = LearningMethodEngine.get_daily_method_challenge("u1")
        for field_name in ("challenge_type", "method", "title", "description",
                           "how_to", "try_it", "science", "xp_reward", "message"):
            assert field_name in challenge, f"每日挑战丢了字段: {field_name}"
        assert challenge["challenge_type"] == "learning_method"
        assert challenge["xp_reward"] == 10
        assert challenge["science"]
        assert challenge["method_id"].startswith("LF-L")


# ────────────────────────────────────────────────────────────
# 5. 查询语义 & 向后兼容
# ────────────────────────────────────────────────────────────

class TestLookupSemantics:
    def test_get_missing_key_raises(self, registry):
        with pytest.raises(KeyError):
            registry.get("不存在的key")
        with pytest.raises(KeyError):
            registry.get("no_such_method")
        with pytest.raises(KeyError):
            registry.get_by_id("LF-L99")

    def test_get_by_id(self, registry):
        assert registry.get_by_id("LF-L23").key == "mind_mapping"

    def test_invalid_query_raises(self, registry):
        with pytest.raises(ValueError):
            registry.by_category("not_a_category")
        with pytest.raises(ValueError):
            registry.by_delivery("not_a_delivery")

    def test_method_tips_still_appendable(self, registry):
        """advanced_methods_engine 依赖 METHOD_TIPS 可被 append"""
        from app.services.learning_methods_engine import METHOD_TIPS

        assert isinstance(METHOD_TIPS, list)
        assert len(METHOD_TIPS) == 23, "METHOD_TIPS 应含 16 条 A + 7 条 B"
        tip_methods = {t["method"] for t in METHOD_TIPS}
        for key in registry.keys():
            if key == "mind_mapping":
                continue
            assert key in tip_methods, f"{key} 在 METHOD_TIPS 里找不到"

    def test_engine_render_tip_unknown_key_raises(self):
        from app.services.learning_methods_engine import LearningMethodEngine

        with pytest.raises(KeyError):
            LearningMethodEngine.render_tip("no_such_method", "代数")

    def test_existing_engine_entrypoints_still_work(self):
        """返回字段签名不得变化"""
        from app.services.learning_methods_engine import LearningMethodEngine

        tip = LearningMethodEngine.get_loading_tip("分数运算")
        assert {"method", "icon", "title", "short", "detail", "action",
                "scene", "duration_ms"} <= set(tip)
        assert "分数运算" in tip["detail"]

        post = LearningMethodEngine.get_post_question_tip("几何", False)
        assert post["scene"] == "post_question"
        assert post["trigger"] == "incorrect"
        assert "几何" in post["detail"]
