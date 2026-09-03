"""Redis 缓存封装（能力估计 + 看板聚合 + 热读）

设计要点（Spec P0）：
- 必需优雅降级：redis 连不上时退化为内存 dict，保证无 Redis 也能开发/跑测试
- get/set_json 通用方法
- cache_ability / get_ability：能力估计缓存
- cache_dashboard / get_dashboard：学生看板聚合缓存
- cache_hot / get_hot（含 cache_hot_tasks 别名）：热读缓存
- TTL 5–15 分钟
"""
import json
import logging
import asyncio
from typing import Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# TTL 配置（秒）
ABILITY_TTL = 600        # 10 分钟
DASHBOARD_TTL = 300      # 5 分钟
HOT_TTL = 900            # 15 分钟

# 模块级单例
_redis = None
_redis_initialized = False
_memory: dict = {}
_memory_expiry: dict = {}


def _now_ts() -> float:
    import time
    return time.time()


async def _get_redis():
    """懒加载 Redis 客户端；连接失败时返回 None 并退化为内存模式"""
    global _redis, _redis_initialized
    if _redis_initialized:
        return _redis
    _redis_initialized = True
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        # 用短超时探测连通性，连不上直接降级
        await asyncio.wait_for(client.ping(), timeout=1.5)
        _redis = client
        logger.info("✅ Redis 缓存已连接：%s", settings.REDIS_URL)
    except Exception as e:
        _redis = None
        logger.warning("⚠️ Redis 不可用，缓存降级为内存模式：%s", e)
    return _redis


async def _memory_get(key: str) -> Optional[Any]:
    if key in _memory:
        exp = _memory_expiry.get(key)
        if exp is None or exp > _now_ts():
            return _memory[key]
        _memory.pop(key, None)
        _memory_expiry.pop(key, None)
    return None


async def _memory_set(key: str, value: Any, ttl: int) -> None:
    _memory[key] = value
    _memory_expiry[key] = _now_ts() + ttl


async def get_json(key: str) -> Optional[Any]:
    """读取 JSON 缓存值，未命中返回 None"""
    try:
        r = await _get_redis()
        if r is not None:
            raw = await asyncio.wait_for(r.get(key), timeout=1.0)
            return json.loads(raw) if raw is not None else None
    except Exception as e:
        logger.debug("Redis get_json 失败，回退内存：%s", e)
    return await _memory_get(key)


async def set_json(key: str, value: Any, ttl: int = DASHBOARD_TTL) -> None:
    """写入 JSON 缓存值（带 TTL）"""
    payload = json.dumps(value, ensure_ascii=False, default=str)
    try:
        r = await _get_redis()
        if r is not None:
            await asyncio.wait_for(r.set(key, payload, ex=ttl), timeout=1.0)
            return
    except Exception as e:
        logger.debug("Redis set_json 失败，回退内存：%s", e)
    await _memory_set(key, value, ttl)


async def delete(key: str) -> None:
    """失效单个键"""
    _memory.pop(key, None)
    _memory_expiry.pop(key, None)
    try:
        r = await _get_redis()
        if r is not None:
            await asyncio.wait_for(r.delete(key), timeout=1.0)
    except Exception:
        pass


# ─── 能力估计缓存 ─────────────────────────────────

def _ability_key(user_id: str) -> str:
    return f"ability:{user_id}"


async def cache_ability(user_id: str, theta: float, sigma: float, ttl: int = ABILITY_TTL) -> None:
    await set_json(_ability_key(user_id), {"theta": theta, "sigma": sigma}, ttl)


async def get_ability(user_id: str) -> Optional[tuple]:
    """返回 (theta, sigma) 或 None"""
    data = await get_json(_ability_key(user_id))
    if data and "theta" in data and "sigma" in data:
        return float(data["theta"]), float(data["sigma"])
    return None


async def invalidate_ability(user_id: str) -> None:
    await delete(_ability_key(user_id))


# ─── 看板聚合缓存 ─────────────────────────────────

def _dashboard_key(user_id: str) -> str:
    return f"dashboard:{user_id}"


async def cache_dashboard(user_id: str, payload: dict, ttl: int = DASHBOARD_TTL) -> None:
    await set_json(_dashboard_key(user_id), payload, ttl)


async def get_dashboard(user_id: str) -> Optional[dict]:
    return await get_json(_dashboard_key(user_id))


async def invalidate_dashboard(user_id: str) -> None:
    await delete(_dashboard_key(user_id))


# ─── 热读缓存（如热题列表） ───────────────────────

def _hot_key(name: str) -> str:
    return f"hot:{name}"


async def cache_hot(name: str, payload: Any, ttl: int = HOT_TTL) -> None:
    await set_json(_hot_key(name), payload, ttl)


async def get_hot(name: str) -> Optional[Any]:
    return await get_json(_hot_key(name))


# 兼容 Spec 命名的别名
cache_hot_tasks = cache_hot
get_hot_tasks = get_hot


async def invalidate_user(user_id: str) -> None:
    """失效某用户相关的所有缓存键（提交作答/布置作业/完成作业完成时调用）"""
    await invalidate_ability(user_id)
    await invalidate_dashboard(user_id)
