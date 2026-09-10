"""研究知情同意审计报告（可重复执行）

用途
----
对 ``learning_events`` 表做研究知情同意标记的合规审计，输出：
  - 按 ``research_consented``（True / False / None）分组的事件数与去重被试数；
  - 其中未成年人的各状态被试数（伦理审查最关心的数字）；
  - 学生自授（未成年人未取得家长授权）的被试数；
  - 结论行：明确写出「有多少被试的数据**不应**纳入研究数据集」。

设计
----
- 标记式（不阻断）方案下，本脚本只做**只读**统计，绝不修改任何数据。
- 无数据库时自动回退到 SQLite（见 app/core/config.py）；连不上库时打印
  友好提示并退出，不抛栈。
- 可重复执行，适合 CI / 定期巡检。

用法
----
    python scripts/audit_research_consent.py
"""
import asyncio
import sys
from pathlib import Path

# 允许以 `python scripts/audit_research_consent.py` 直接运行：
# 把后端根目录加入 sys.path，使 `app` 包可导入。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import inspect as sa_inspect

from app.core.config import settings
from app.models.user import User
from app.models.progression import LearningEvent
from app.services.anti_addiction import infer_age_band, to_age_group
from app.services.anti_addiction_compliance import MinorProtectionEngine
from app.services.research_consent import resolve_research_consent


def _is_minor(user: User) -> bool:
    """被试是否未成年（复用既有实现）。"""
    if user is None:
        return False
    age_group = to_age_group(infer_age_band(user))
    return bool(MinorProtectionEngine.is_minor(age_group))


async def main() -> None:
    # ── 连接兜底 ───────────────────────────────────────────
    try:
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # 连不上库：友好提示并退出
        print("⚠️ 无法连接数据库：%s" % exc)
        print("   请检查 DATABASE_URL 配置或数据库是否已启动。")
        print("   当前 DATABASE_URL = %s" % settings.DATABASE_URL)
        return

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as db:
        # ── 表 / 列存在性兜底 ───────────────────────────────
        # 老开发库可能早于 learning_events 表或 research_consented 列创建
        # （create_all 不 ALTER 既有表，_ensure_schema_extensions 仅补可空列）。
        # 缺表或缺列时打印友好提示并退出，不抛栈。
        try:
            def _sync_inspect(sync_conn):
                insp = sa_inspect(sync_conn)
                tbls = insp.get_table_names()
                cols = {c["name"] for c in insp.get_columns("learning_events")} \
                    if "learning_events" in tbls else set()
                return tbls, cols

            async with engine.connect() as conn:
                tables, cols = await conn.run_sync(_sync_inspect)
            if "learning_events" not in tables:
                print("⚠️ 研究事件表 learning_events 不存在于当前数据库。")
                print("   可能是早期开发库（create_all 不会 ALTER 既有库）。")
                print("   请先执行数据库初始化（app.core.database.init_db）后再审计。")
                return
            if "research_consented" not in cols:
                print("⚠️ learning_events 缺少 research_consented 列。")
                print("   请先执行数据库初始化 / schema 扩展后再审计。")
                return
        except Exception as exc:
            print("⚠️ 读取数据库结构失败：%s" % exc)
            return

        # 加载全部用户，用于未成年判定
        users = {u.id: u for u in (await db.execute(select(User))).scalars().all()}

        # 1) 按 research_consented 分组的事件数 + 去重被试数
        grp = await db.execute(
            select(
                LearningEvent.research_consented,
                func.count(),
                func.count(func.distinct(LearningEvent.user_id)),
            ).group_by(LearningEvent.research_consented)
        )
        groups: dict = {}
        for val, ev_count, subj_count in grp:
            key = val if val in (True, False) else None
            groups[key] = (ev_count, subj_count)

        # 2) 去重被试集合，按 research_consented 归类（Python 端去重，
        #    避免 SQLite 对 func.distinct 作为独立列表达式不支持）
        subj_rows = await db.execute(
            select(LearningEvent.research_consented, LearningEvent.user_id)
        )
        subjects_by_val: dict = {True: set(), False: set(), None: set()}
        for val, uid in subj_rows:
            key = val if val in (True, False) else None
            subjects_by_val.setdefault(key, set()).add(uid)

        # 3) 各状态中的未成年被试数
        minor_by_val = {True: set(), False: set(), None: set()}
        for val, uids in subjects_by_val.items():
            key = val if val in (True, False) else None
            for uid in uids:
                if _is_minor(users.get(uid)):
                    minor_by_val[key].add(uid)

        # 4) 学生自授（minor_without_guardian_consent）的被试数
        all_minor_uids = set()
        for s in subjects_by_val.values():
            for uid in s:
                if _is_minor(users.get(uid)):
                    all_minor_uids.add(uid)
        self_granted_minors = set()
        for uid in all_minor_uids:
            st = await resolve_research_consent(db, users.get(uid))
            if st.reason == "minor_without_guardian_consent":
                self_granted_minors.add(uid)

    # ── 输出报告 ───────────────────────────────────────────
    ev_t = groups.get(True, (0, 0))[0]
    ev_f = groups.get(False, (0, 0))[0]
    ev_n = groups.get(None, (0, 0))[0]
    subj_t = groups.get(True, (0, 0))[1]
    subj_f = groups.get(False, (0, 0))[1]
    subj_n = groups.get(None, (0, 0))[1]

    print("=" * 64)
    print("研究知情同意审计报告  (research_consented)")
    print("=" * 64)
    print("说明：True=已同意  False=明确未取得有效同意  None=未知/未判定/已撤销")
    print("-" * 64)
    print("【事件数 / 去重被试数】")
    print("  True : 事件 %8d | 被试 %6d" % (ev_t, subj_t))
    print("  False: 事件 %8d | 被试 %6d" % (ev_f, subj_f))
    print("  None : 事件 %8d | 被试 %6d" % (ev_n, subj_n))
    print("-" * 64)
    print("【其中未成年人被试数（伦理审查重点）】")
    print("  True : %6d" % len(minor_by_val.get(True, set())))
    print("  False: %6d" % len(minor_by_val.get(False, set())))
    print("  None : %6d" % len(minor_by_val.get(None, set())))
    print("-" * 64)
    print("【学生自授（未成年人未取得家长授权）：被试 %d 人】" % len(self_granted_minors))
    if self_granted_minors:
        print("  被试ID: " + ", ".join(sorted(self_granted_minors)))
    print("=" * 64)

    # 结论：明确不应纳入 = research_consented == False 的被试；
    # 未知(None)需进一步追溯，不能直接纳入。
    excluded = subj_f
    unknown = subj_n
    print("结论：")
    print("  ● 明确不应纳入研究数据集的被试：%d 人（research_consented = False）" % excluded)
    print("  ● 未知/未判定/已撤销、需进一步追溯的被试：%d 人（research_consented = None）" % unknown)
    print("    分析时必须显式过滤为 research_consented IS TRUE，以上两类不得纳入。")
    if self_granted_minors:
        print("  ★ 其中未成年人自授 %d 人，若论文声称已取得家长知情同意则属不实声明，"
              "须立即整改。" % len(self_granted_minors))
    print("=" * 64)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
