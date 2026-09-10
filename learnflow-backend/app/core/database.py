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
    """为已存在的表补充新增的可空列（create_all 不会 ALTER 既有表，兼容开发库升级）"""
    from sqlalchemy import inspect as sa_inspect, text
    # (表名, [(列名, 类型)])
    extensions = {
        "tasks": [("curriculum_node_id", "VARCHAR(36)")],
        "student_skill_profiles": [("curriculum_node_id", "VARCHAR(36)")],
        # 研究知情同意标记：新增列必须在此注册，否则已存在的开发库不会 ALTER 出该列，
        # 功能会静默失效（不报错，只是没有这一列）。
        "learning_events": [("research_consented", "BOOLEAN")],
    }
    try:
        async with engine.begin() as conn:
            def _sync(sync_conn):
                insp = sa_inspect(sync_conn)
                for table, cols in extensions.items():
                    if not insp.has_table(table):
                        continue
                    existing = {c["name"] for c in insp.get_columns(table)}
                    for col_name, col_type in cols:
                        if col_name not in existing:
                            sync_conn.execute(
                                text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                            )
                            logger.info(f"✅ 已为表 {table} 补充列 {col_name}")
            await conn.run_sync(_sync)
    except Exception as e:  # pragma: no cover
        logger.warning("⚠️ schema 扩展跳过（%s），若列已存在可忽略", e)


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
