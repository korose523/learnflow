"""数据库连接与会话管理"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

# 延迟初始化，避免导入时就需要数据库驱动
_engine: Optional = None
_AsyncSessionLocal: Optional = None


def _get_engine():
    """延迟创建引擎（首次调用时）"""
    global _engine
    if _engine is None:
        from app.core.config import settings
        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "echo": settings.DEBUG,
        }
        # SQLite + NullPool 不支持 pool_size / max_overflow
        if not settings.DATABASE_URL.startswith("sqlite"):
            engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
            engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
        _engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs,
        )
    return _engine


def _get_sessionmaker():
    """延迟创建 session factory"""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


# 导出 AsyncSessionLocal，供 seed.py 和外部脚本使用
AsyncSessionLocal = _get_sessionmaker()


async def get_db() -> AsyncSession:
    """依赖注入：获取数据库会话"""
    sessionmaker = _get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.error("数据库事务异常，已回滚", exc_info=True)
            raise
        finally:
            await session.close()


async def _ensure_schema_extensions(engine):
    """为【已存在】的表自动补充模型里新增、但数据库尚未包含的列。

    早期开发库（如 learnflow.db）是在 User 模型加入 phone / school_id / class_id
    等列之前创建的。``Base.metadata.create_all`` 只会建【缺失的表】，不会 ALTER
    既有表，于是查询 users 表会报 ``no such column``，连带登录与所有用户相关接口失效。

    这里改为【基于 Base.metadata 自动比对】，不再手工维护列清单：模型演进后无需
    改这里即可自愈。规则：
    - 仅对当前数据库【已存在】的表做扩展（create_all 已负责缺失的整表）；
    - 仅补充【缺失】的列，已存在的列不动；
    - 仅当列声明为非空且当前表为空时才追加 NOT NULL，否则放宽成可空，
      避免既有数据行违反约束导致 ALTER 失败（开发库迁移，生产请用 Alembic）。
    """
    from sqlalchemy import inspect as sa_inspect, text
    try:
        async with engine.begin() as conn:
            def _sync(sync_conn):
                insp = sa_inspect(sync_conn)
                existing_tables = set(insp.get_table_names())
                for table_name, table in Base.metadata.tables.items():
                    if table_name not in existing_tables:
                        continue
                    existing_cols = {c["name"] for c in insp.get_columns(table_name)}
                    row_count = sync_conn.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    ).scalar() or 0
                    for col in table.columns:
                        if col.name in existing_cols:
                            continue
                        # col.type 不含外键约束（FK 属于 Column 的 foreign_keys），
                        # 因此 compile 出来只是纯类型，不会生成 REFERENCES 子句，
                        # 规避了老版本 SQLite 不支持 ALTER ADD COLUMN ... REFERENCES 的问题。
                        col_type = col.type.compile(dialect=engine.dialect)
                        ddl = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                        if (not col.nullable) and row_count == 0:
                            ddl += " NOT NULL"
                        sync_conn.execute(text(ddl))
                        logger.info(
                            f"✅ 已为表 {table_name} 补充列 {col.name} ({col_type})"
                        )
            await conn.run_sync(_sync)
    except Exception as e:  # pragma: no cover
        logger.warning("⚠️ schema 自动扩展跳过（%s），若列已存在可安全忽略", e)


async def init_db():
    """初始化数据库表（带重试逻辑）"""
    from app.core.config import settings
    import logging
    
    logger = logging.getLogger(__name__)
    engine = _get_engine()
    
    # 重试3次
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🔍 尝试连接数据库 (尝试 {attempt + 1}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await _ensure_schema_extensions(engine)
            logger.info("✅ 数据库初始化成功")
            return  # 成功，直接返回
        
        except Exception as e:
            logger.error(f"❌ 数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # 等待后重试
                import asyncio
                wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                logger.info(f"⏳ {wait_time}秒后重试...")
                await asyncio.sleep(wait_time)
            else:
                # 最后一次尝试失败 → 无条件回退到 SQLite
                logger.warning("⚠️ 外部数据库连接失败，自动回退到 SQLite（内存数据库）")
                global _engine, _AsyncSessionLocal
                _engine = create_async_engine(
                    "sqlite+aiosqlite:///./learnflow.db",
                    echo=settings.DEBUG,
                )
                # 重置缓存的 sessionmaker，确保后续使用新的 engine
                _AsyncSessionLocal = async_sessionmaker(
                    _engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
                async with _engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                await _ensure_schema_extensions(_engine)
                logger.info("✅ 已切换到 SQLite 数据库（云环境自动降级）")


async def close_db():
    """关闭数据库连接"""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
