"""游戏化机制注册表测试 — 53 个机制 (LF-M01..LF-M53) 的单一事实源完整性

覆盖目标:
1. 注册表是全量 53 个机制的单一事实源 (ID 连续无缺口、key 唯一、snake_case)
2. 每个机制都有必填治理字段 (theory_ref / impl_ref / stage / category / disposition)
3. 可按 stage / category / disposition 查询, 且各维度切分之和 == 53
4. 可按 ID 开关 (消融实验), kill switch 生效
5. 与治理文档 §2.4 清单表的 LF-M 编号双向一致 (交叉验证)
"""
import re
from pathlib import Path

import pytest

from app.services import mechanism_registry as reg


DOC_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "LearnFlow_机制治理与落实方案.md"


@pytest.fixture
def registry():
    """注册表本身即单一事实源, 测试直接引用该模块"""
    return reg


# ────────────────────────────────────────────────────────────
# 1. 注册表完整性
# ────────────────────────────────────────────────────────────

class TestRegistryIntegrity:
    def test_count_is_53(self, registry):
        assert registry.count() == 53

    def test_keys_unique_and_snake_case(self, registry):
        all_keys = registry.keys()
        assert len(all_keys) == 53
        assert len(set(all_keys)) == 53, "mechanism key 存在重复"
        for key in all_keys:
            assert key == key.lower() and key.replace("_", "").isalnum(), f"非 snake_case: {key}"

    def test_ids_contiguous_no_gap(self, registry):
        ids = registry.ids()
        assert len(set(ids)) == 53, "机制 ID 存在重复"
        assert ids == [f"LF-M{i:02d}" for i in range(1, 54)], f"ID 有缺口或错位: {ids}"

    def test_all_specs_have_required_fields(self, registry):
        required = ("id", "key", "name_zh", "name_en", "stage", "category",
                    "theory_ref", "impl_ref", "disposition", "maturity")
        for spec in registry.all_mechanisms():
            for fname in required:
                value = getattr(spec, fname, None)
                assert value not in (None, "", ()), f"{spec.key} 缺字段: {fname}"
            assert spec.stage in registry.STAGES
            assert spec.category in registry.CATEGORIES
            assert spec.disposition in registry.DISPOSITIONS
            assert spec.maturity in registry.MATURITY
            assert spec.theory_ref.strip(), f"{spec.key} 的 theory_ref 为空"
            assert spec.impl_ref.strip(), f"{spec.key} 的 impl_ref 为空"

    def test_catalog_rows_shape(self, registry):
        rows = registry.catalog_rows()
        assert len(rows) == 53
        for row in rows:
            assert set(row) == {
                "id", "key", "name_zh", "name_en", "stage", "category",
                "theory_ref", "impl_ref", "disposition", "maturity", "notes",
            }
            assert row["id"].startswith("LF-M")


# ────────────────────────────────────────────────────────────
# 2. 多维切分（各维度之和必须等于 53）
# ────────────────────────────────────────────────────────────

class TestDimensionSlices:
    def test_stage_slices_cover_all(self, registry):
        buckets = [registry.by_stage(s) for s in registry.STAGES]
        assert sum(len(b) for b in buckets) == 53, "stage 切分未覆盖全部机制"
        for spec in registry.all_mechanisms():
            assert spec in registry.by_stage(spec.stage)

    def test_category_slices_cover_all(self, registry):
        buckets = [registry.by_category(c) for c in registry.CATEGORIES]
        assert sum(len(b) for b in buckets) == 53, "category 切分未覆盖全部机制"
        for spec in registry.all_mechanisms():
            assert spec in registry.by_category(spec.category)

    def test_disposition_slices_cover_all(self, registry):
        buckets = [registry.by_disposition(d) for d in registry.DISPOSITIONS]
        assert sum(len(b) for b in buckets) == 53, "disposition 切分未覆盖全部机制"
        for spec in registry.all_mechanisms():
            assert spec in registry.by_disposition(spec.disposition)


# ────────────────────────────────────────────────────────────
# 3. 查询语义 & 向后兼容
# ────────────────────────────────────────────────────────────

class TestLookupSemantics:
    def test_get_and_get_by_id(self, registry):
        assert registry.get("streak").id == "LF-M11"
        assert registry.get_by_id("LF-M53").key == "lai_downgrade"
        # 健康护栏三个都有一票否决权, 单独可定位
        for mid in ("LF-M51", "LF-M52", "LF-M53"):
            assert registry.get_by_id(mid).category == "health"

    def test_get_missing_raises(self, registry):
        with pytest.raises(KeyError):
            registry.get("不存在的key")
        with pytest.raises(KeyError):
            registry.get_by_id("LF-M99")


class TestOrchestratorWiring:
    def test_pipeline_mechanism_map_references_real_mechanisms(self, registry):
        """orchestrator 的 11 步流水线接线必须引用真实存在的机制 ID。

        导入 learning_orchestrator 即触发其构造期校验; 这里再显式断言,
        使「流水线是注册表驱动的」这一不变量可测。
        """
        from app.services.learning_orchestrator import PIPELINE_MECHANISM_MAP

        assert PIPELINE_MECHANISM_MAP, "PIPELINE_MECHANISM_MAP 不应为空"
        for step, keys in PIPELINE_MECHANISM_MAP.items():
            for k in keys:
                assert registry.get(k).id.startswith("LF-M"), (
                    f"orchestrator step {step} 引用了未注册机制 {k!r}"
                )



# ────────────────────────────────────────────────────────────
# 4. 开关 (消融实验)
# ────────────────────────────────────────────────────────────

class TestToggle:
    def test_kill_switch(self, registry):
        key = registry.keys()[0]
        registry.set_enabled(key, False)
        try:
            assert registry.is_enabled(key) is False
            assert key in registry.disabled_keys()
            assert len(registry.enabled_mechanisms()) == 52
        finally:
            registry.set_enabled(key, True)
        assert registry.is_enabled(key) is True

    def test_set_enabled_unknown_key_raises(self, registry):
        with pytest.raises(KeyError):
            registry.set_enabled("no_such_mechanism", False)


# ────────────────────────────────────────────────────────────
# 5. 与治理文档双向交叉验证
# ────────────────────────────────────────────────────────────

class TestDocCrossValidation:
    def test_registry_ids_match_governance_doc(self, registry):
        """注册表的 53 个 ID 必须与 docs/...机制治理方案.md §2.4 清单表完全一致。

        这是对「单一事实源」的强约束: 有人改了代码没改文档 (或反之),
        这个测试立刻变红。
        """
        assert DOC_PATH.is_file(), f"治理文档缺失: {DOC_PATH}"
        text = DOC_PATH.read_text(encoding="utf-8")
        # 只匹配清单表行首的 `| LF-Mxx |` (避免误匹配正文里其它 LF-M 提及)
        doc_ids = re.findall(r"^\|\s*(LF-M\d{2})\s*\|", text, flags=re.MULTILINE)
        # 去重后排序
        doc_ids = sorted(set(doc_ids))
        assert doc_ids == registry.ids(), (
            f"注册表 ID 与治理文档不一致:\n"
            f"  文档: {doc_ids}\n"
            f"  注册表: {registry.ids()}"
        )
