"""LF-M52 未成年保护接编排器的回归测试

治理审计发现的历史缺陷：

    机制注册表把 LF-M52「未成年保护」的 impl_ref 指向
    ``anti_addiction_compliance.py:79``（即 ``MinorProtectionEngine``），
    但生产代码中该引擎**零调用方**。编排器只使用了 ``anti_addiction`` 的
    粗粒度规则（学段布尔值 + 25 分钟会话重置），导致：

      (a) 注册表宣称 LF-M52 已落地，其声明的实现却从未运行 —— 可被一行 grep 证伪；
      (b) 运行中的实现缺少「每日时长上限」与「夜间禁用」两项合规硬要求。

    修复后：``anti_addiction.minor_protection_decision`` 成为唯一对外门面，
    内部委托 ``MinorProtectionEngine``；编排器步骤 8b 调用该门面，并把结论
    用于奖励抑制与 FOMO 仲裁的健康一票否决。

本文件冻结上述契约，防止回退。三条主线：

* 注册表的 impl_ref 必须指向**真实可达**的引擎（不是死字符串）
* 门面必须真的调用该引擎（不是同名空壳）
* 夜间禁用只对未成年生效（成年人不得被越权阻断）
"""
import re
from datetime import datetime, UTC
from pathlib import Path

import pytest

from app.services.anti_addiction import (
    minor_protection_decision,
    to_age_group,
)
from app.services.anti_addiction_compliance import (
    AgeGroup,
    MinorProtectionEngine,
    SessionStatus,
    UsageQuota,
)
from app.services.mechanism_registry import all_mechanisms

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ORCHESTRATOR = BACKEND_ROOT / "app" / "services" / "learning_orchestrator.py"

# 固定时刻，避免测试在真实夜间运行时产生环境依赖（flaky）。
#
# 关键：下列常量是 **UTC** 时刻，需按 night_timezone_offset=8 换算才是北京时间。
#   DAY   = UTC 2026-09-04 02:00  →  北京时间 10:00（白天）
#   NIGHT = UTC 2026-09-04 14:30  →  北京时间 22:30（夜间）
DAY = datetime(2026, 9, 4, 2, 0, tzinfo=UTC)
NIGHT = datetime(2026, 9, 4, 14, 30, tzinfo=UTC)


def _spec(mech_id: str):
    return next(m for m in all_mechanisms() if m.id == mech_id)


class TestRegistryImplRefReachable:
    """注册表声明的实现位置必须指向一个真实存在且可被解析的符号"""

    def test_lf52_impl_ref_points_to_minor_protection_engine(self):
        """LF-M52 的 impl_ref 必须能解析到 MinorProtectionEngine 这一符号。

        历史教训：impl_ref 原为行号形式 ``anti_addiction_compliance.py:79``。
        在该文件上方插入代码（时区偏移配置等）后，行号静默漂移到无关内容，
        而注册表与 scan 脚本都不校验行号 —— 审稿人按图索骥会看到错误代码。
        现改为**符号级引用** ``file.py:MinorProtectionEngine``，抗漂移。
        """
        spec = _spec("LF-M52")
        assert spec.key == "minor_protection"

        m = re.match(r"^(?P<fname>[A-Za-z_]+\.py):(?P<sym>[A-Za-z_]\w*)$", spec.impl_ref)
        assert m, (
            f"impl_ref 应为符号级形式 'file.py:Symbol'，实际: {spec.impl_ref!r}"
        )

        path = BACKEND_ROOT / "app" / "services" / m.group("fname")
        assert path.exists(), f"impl_ref 指向的文件不存在: {path}"

        symbol = m.group("sym")
        src = path.read_text(encoding="utf-8")
        assert re.search(rf"^class {symbol}\b", src, re.M), (
            f"文件 {path.name} 中未找到类定义 {symbol}"
        )
        # 该符号必须与注册表声明的实现一致
        assert symbol == "MinorProtectionEngine"

    def test_lf52_impl_ref_survives_source_edits(self):
        """行号会漂移，符号引用不会 —— 冻结这一性质"""
        spec = _spec("LF-M52")
        assert ":" in spec.impl_ref
        anchor = spec.impl_ref.split(":", 1)[1]
        assert not anchor.isdigit(), (
            f"impl_ref 锚点不应是裸行号（会随源码编辑漂移）: {spec.impl_ref!r}"
        )

    def test_lf52_is_not_a_dead_string(self):
        """反例守卫：引擎必须可被真实导入并调用（而非仅存在于文档字符串）"""
        verdict = MinorProtectionEngine.check_session(
            UsageQuota(user_id="probe", age_group=AgeGroup.PRE_TEEN),
            None,
            DAY,
        )
        assert "status" in verdict and "should_block" in verdict


class TestFacadeDelegatesToRegisteredEngine:
    """门面必须真的把校验委托给注册表声明的那个引擎"""

    def test_facade_invokes_check_session(self, monkeypatch):
        seen = []
        original = MinorProtectionEngine.check_session.__func__

        def spy(cls, quota, config=None, current_time=None):
            seen.append(quota)
            return original(cls, quota, config, current_time)

        monkeypatch.setattr(MinorProtectionEngine, "check_session", classmethod(spy))

        minor_protection_decision("u1", "小学", daily_minutes=5.0, now=DAY)

        assert len(seen) == 1, "门面应恰好调用一次引擎校验"
        assert seen[0].user_id == "u1"
        assert seen[0].age_group == AgeGroup.PRE_TEEN

    def test_orchestrator_calls_the_facade(self):
        """编排器源码必须调用该门面（防止接线被后续重构悄悄移除）"""
        src = ORCHESTRATOR.read_text(encoding="utf-8")
        assert "anti_addiction.minor_protection_decision" in src, (
            "编排器未调用 minor_protection_decision 门面 —— LF-M52 接线已回退"
        )
        # 结论必须进入决策快照（埋点/论文归因依赖）
        assert 'decision_snapshot["minor_protection"]' in src


class TestGradeBandToAgeGroup:
    def test_mapping(self):
        assert to_age_group("小学") == AgeGroup.PRE_TEEN
        assert to_age_group("初中") == AgeGroup.TEEN
        assert to_age_group("高中") == AgeGroup.LATE_TEEN

    def test_unknown_band_defaults_to_adult(self):
        """未知学段按成人处理：宁可漏限，不可误限成年用户"""
        assert to_age_group("其他") == AgeGroup.ADULT
        assert to_age_group("") == AgeGroup.ADULT
        assert to_age_group("幼儿园") == AgeGroup.ADULT


class TestNightBlockIsMinorOnly:
    """回归：夜间禁用曾对包括成年人在内的所有人生效（越权阻断）"""

    def test_minor_blocked_at_night(self):
        d = minor_protection_decision("u1", "小学", daily_minutes=5.0, now=NIGHT)
        assert d["should_block"] is True
        assert d["status"] == SessionStatus.NIGHT_BLOCKED.value
        assert d["night_time"] is True
        assert d["message"], "阻断时应给出面向用户的解释文案"

    def test_adult_not_blocked_at_night(self):
        """这是被修复的缺陷：成年人夜间学习不应被阻断"""
        d = minor_protection_decision("u9", "其他", daily_minutes=5.0, now=NIGHT)
        assert d["should_block"] is False
        assert d["status"] == SessionStatus.ACTIVE.value
        # 仍保留夜间标记，可供上层做温和提示
        assert d["night_time"] is True
        assert d["is_minor"] is False


class TestNightWindowUsesLocalTime:
    """回归：夜间时段曾按 UTC 小时判定，对中国用户（UTC+8）政策整体错位 8 小时。

    缺陷时的实际效果：阻断北京时间 06:00–14:00（上午/中午的正常学习时段），
    却在真正的深夜 22:00–06:00 放行 —— 与《未成年人网络保护条例》意图相反。
    """

    @pytest.mark.parametrize("utc_dt,beijing_hhmm,expect_night", [
        (datetime(2026, 9, 4, 2, 0, tzinfo=UTC), "10:00", False),    # 上午
        (datetime(2026, 9, 4, 5, 0, tzinfo=UTC), "13:00", False),    # 中午
        (datetime(2026, 9, 4, 13, 59, tzinfo=UTC), "21:59", False),  # 傍晚边界前
        (datetime(2026, 9, 4, 14, 1, tzinfo=UTC), "22:01", True),    # 深夜边界后
        (datetime(2026, 9, 3, 18, 0, tzinfo=UTC), "02:00", True),    # 凌晨
        (datetime(2026, 9, 3, 21, 59, tzinfo=UTC), "05:59", True),   # 凌晨边界前
        (datetime(2026, 9, 3, 22, 1, tzinfo=UTC), "06:01", False),   # 清晨边界后
    ])
    def test_boundaries_in_beijing_time(
        self, utc_dt, beijing_hhmm, expect_night,
    ):
        d = minor_protection_decision("u", "小学", daily_minutes=1.0, now=utc_dt)
        assert d["night_time"] is expect_night, (
            f"北京时间 {beijing_hhmm} 的夜间判定错误 "
            f"(UTC {utc_dt.hour:02d}:{utc_dt.minute:02d})"
        )

    def test_offset_is_configurable(self):
        """偏移可调：UTC+0 时，UTC 22:30 即应判为夜间"""
        from app.services.anti_addiction_compliance import MinorProtectionConfig
        utc_late = datetime(2026, 9, 4, 22, 30, tzinfo=UTC)
        cfg = MinorProtectionConfig(night_timezone_offset=0)
        assert MinorProtectionEngine._is_night_time(cfg, utc_late) is True
        # 同一时刻按北京时区（+8）换算为次日 06:30，已不在夜间
        cfg_bj = MinorProtectionConfig(night_timezone_offset=8)
        assert MinorProtectionEngine._is_night_time(cfg_bj, utc_late) is False


class TestLimitsByAgeGroup:
    @pytest.mark.parametrize("band,group", [
        ("小学", AgeGroup.PRE_TEEN),
        ("初中", AgeGroup.TEEN),
        ("高中", AgeGroup.LATE_TEEN),
    ])
    def test_limits_are_age_differentiated(self, band, group):
        d = minor_protection_decision("u", band, daily_minutes=1.0, now=DAY)
        assert d["age_group"] == group.value
        assert d["daily_limit"] == MinorProtectionEngine.get_daily_limit(group)
        assert d["consecutive_limit"] == MinorProtectionEngine.get_consecutive_limit(group)

    def test_consecutive_limit_triggers_rest(self):
        """连续学习超过该年龄段上限 → 要求强制休息"""
        group = AgeGroup.PRE_TEEN
        limit = MinorProtectionEngine.get_consecutive_limit(group)
        d = minor_protection_decision(
            "u", "小学", daily_minutes=float(limit + 1),
            consecutive_minutes=float(limit + 1), now=DAY,
        )
        assert d["should_block"] is True
        assert d["status"] == SessionStatus.REST_REQUIRED.value
        assert d["rest_minutes"] == MinorProtectionEngine.get_rest_duration(group)


class TestDecisionContract:
    """门面返回值的字段契约（响应体、埋点快照、FOMO 仲裁均依赖）"""

    REQUIRED = {
        "age_band", "age_group", "is_minor", "status", "should_block",
        "message", "rest_minutes", "daily_limit", "consecutive_limit",
        "daily_minutes_used", "consecutive_minutes_used",
        "night_time", "daily_remaining",
    }

    def test_all_fields_present(self):
        d = minor_protection_decision("u1", "小学", daily_minutes=5.0, now=DAY)
        missing = self.REQUIRED - set(d)
        assert not missing, f"决策字段缺失: {sorted(missing)}"

    def test_types_are_json_serialisable(self):
        """决策快照会随埋点 JSON 落库，字段必须是可序列化的标量"""
        import json
        d = minor_protection_decision("u1", "小学", daily_minutes=5.0, now=DAY)
        json.dumps(d)  # 不可序列化则抛出
        assert isinstance(d["should_block"], bool)
        assert isinstance(d["is_minor"], bool)
        assert isinstance(d["rest_minutes"], int)

    def test_consecutive_falls_back_to_daily(self):
        """未显式传入连续时长时以当日累计兜底（已知局限，行为须稳定）"""
        d = minor_protection_decision("u1", "小学", daily_minutes=12.0, now=DAY)
        assert d["consecutive_minutes_used"] == 12.0
        assert d["daily_minutes_used"] == 12.0


class TestProcessSubmissionIntegration:
    """端到端：process_submission 必须真的执行 LF-M52 合规校验"""

    async def test_response_carries_minor_protection_verdict(self):
        """（同时覆盖技能树 P0 修复：此处**不再**对 get_skill_tree 打桩）

        历史说明：本集成测试原先需要把 SkillTreeEngine.get_skill_tree 打桩成
        `lambda uid: {}`，因为真实返回值与 _skilltree_repo_format 形状不兼容，
        凡 db 非 None 的提交路径必抛 AttributeError。该缺陷已修复，故此处改用
        真实调用 —— 这也是对修复本身的端到端验证。
        """
        from unittest.mock import AsyncMock, patch
        from sqlalchemy.ext.asyncio import (
            AsyncSession, async_sessionmaker, create_async_engine)
        from sqlalchemy.pool import StaticPool

        from app.core.database import Base
        import app.models  # noqa: F401  (注册全部表)
        from app.models.user import User, UserRole
        from app.models.task import Task
        from app.services.learning_orchestrator import LearningOrchestrator

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            # learning_events 复合主键 SQLite 建表不兼容 (既有已知问题), 排除并以桩替换
            tables = [t for t in Base.metadata.sorted_tables
                      if t.name != "learning_events"]
            await conn.run_sync(lambda s: Base.metadata.create_all(s, tables=tables))

        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            db.add(User(
                id="lf-mp-minor", email="lf_mp_minor@example.com", name="Minor",
                role=UserRole.STUDENT, hashed_password="x", grade="五年级",
            ))
            db.add(Task(
                id="lf-mp-task", content="2+3=?", topic="math",
                difficulty=3, correct_answer="5", explanation="两数相加",
            ))
            await db.commit()
            user = await db.get(User, "lf-mp-minor")
            task = await db.get(Task, "lf-mp-task")

            # 固定两处非确定性来源，使断言稳定：
            #   1) 时钟 —— 非夜间路径（夜间分支已由 TestNightWindowUsesLocalTime
            #      用显式时刻覆盖，此处不重复）
            #   2) 变比率随机 —— 未成年强奖励按 15%~25% 概率触发，若不固定则
            #      xp_earned 会在 0 与正值之间随机翻转（flaky）。固定为 0.05
            #      使其必然落在触发概率内，从而验证「未阻断时正常发奖」。
            with patch(
                "app.services.learning_orchestrator.record_learning_event",
                new=AsyncMock(),
            ), patch.object(
                MinorProtectionEngine, "_is_night_time",
                classmethod(lambda cls, cfg, t=None: False),
            ), patch(
                "app.services.learning_orchestrator.random.random",
                new=lambda: 0.05,
            ):
                resp = await LearningOrchestrator.process_submission(
                    user, task, {"answer": "5", "hints_used": 0}, db)

            mp = resp["minor_protection"]
            assert mp["age_band"] == "小学"
            assert mp["age_group"] == AgeGroup.PRE_TEEN.value
            assert mp["is_minor"] is True
            assert "should_block" in mp and "status" in mp
            assert mp["should_block"] is False, "非夜间且用量极低，不应阻断"
            # 五年级 → PRE_TEEN，每日上限 60 分钟
            assert mp["daily_limit"] == 60
            assert mp["consecutive_limit"] == 30

            # 技能树 P0 修复的端到端验证：真实路径未抛异常且主流程完好
            assert resp["is_correct"] is True
            assert resp["xp_update"]["xp_earned"] > 0

        await engine.dispose()
