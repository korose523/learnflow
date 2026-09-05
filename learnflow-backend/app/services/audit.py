"""决策审计落库助手（未成年人保护硬约束）

所有难度 / 奖励 / 风险决策必须写入 audit_logs。

审计完整性是可测量的
--------------------
本模块原先是**静默的 best-effort**：写入失败只打一条 warning 日志，主流程
继续。这在两个层面构成缺陷：

1. 模块文档声明「**必须**写入」且属「未成年人保护硬约束」，实现却是尽力而为，
   文档与实现自相矛盾；
2. **没有任何失败计数**。审计轨迹可以静默缺失任意多条，而事后无从察觉——
   对本项目的论文用途是致命的：audit_logs 是实验的证据链，若无法证明其
   完整性，就无法据此做任何主张。

因此此处保留 best-effort 语义（审计失败不应阻断学习主流程——学生不该因为
日志故障而无法提交答案），但把**完整性变成可测量的量**：

* ``write_audit`` 返回 ``bool``，调用方可按需检查；
* 维护进程内计数器，``get_audit_stats()`` 可随时读取；
* ``strict=True`` 时失败直接抛出，供研究批次（要求审计零丢失）使用。

这样论文中可如实引用形如「审计写入成功率 100.00%（N=12,345）」的可复算
指标，而非含糊地声称「所有决策均已记录」。

注意：计数器是**进程内**的，多 worker 部署时需各自采集后汇总。
"""
from datetime import datetime, UTC
from typing import Optional
import logging
import threading

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AuditLog, AuditKind

logger = logging.getLogger(__name__)

# ── 审计完整性计数器（进程内） ──────────────────────────────
# 仅做简单的 dict 增减，不涉及 await，用 threading.Lock 即可。
_AUDIT_STATS = {
    "attempted": 0,
    "succeeded": 0,
    "failed": 0,
}
_AUDIT_LAST_ERROR: Optional[str] = None
_STATS_LOCK = threading.Lock()


def get_audit_stats() -> dict:
    """返回审计写入完整性统计（供可复现性报告引用）。

    Returns:
        {
            "attempted": int,   # 尝试写入总数
            "succeeded": int,   # 成功数
            "failed": int,      # 失败数
            "success_rate": float | None,  # 成功率，attempted=0 时为 None
            "last_error": str | None,      # 最近一次失败原因
        }
    """
    with _STATS_LOCK:
        attempted = _AUDIT_STATS["attempted"]
        succeeded = _AUDIT_STATS["succeeded"]
        failed = _AUDIT_STATS["failed"]
        last_error = _AUDIT_LAST_ERROR
    return {
        "attempted": attempted,
        "succeeded": succeeded,
        "failed": failed,
        "success_rate": (succeeded / attempted) if attempted else None,
        "last_error": last_error,
    }


def reset_audit_stats() -> None:
    """清零计数器（每个实验批次开始时调用，便于分批统计）。"""
    global _AUDIT_LAST_ERROR
    with _STATS_LOCK:
        _AUDIT_STATS.update({"attempted": 0, "succeeded": 0, "failed": 0})
        _AUDIT_LAST_ERROR = None


def _record(succeeded: bool, error: Optional[str] = None) -> None:
    global _AUDIT_LAST_ERROR
    with _STATS_LOCK:
        _AUDIT_STATS["attempted"] += 1
        if succeeded:
            _AUDIT_STATS["succeeded"] += 1
        else:
            _AUDIT_STATS["failed"] += 1
            _AUDIT_LAST_ERROR = error


async def write_audit(
    db: AsyncSession,
    kind: AuditKind,
    user_id: Optional[str] = None,
    input_json: Optional[dict] = None,
    output_json: Optional[dict] = None,
    subject: Optional[str] = None,
    age_band: Optional[str] = None,
    *,
    strict: bool = False,
) -> bool:
    """写入一条审计记录。

    默认 best-effort：失败仅记录日志与计数器，不阻断主流程（学生不应因日志
    故障而无法提交答案）。``strict=True`` 时失败直接抛出，供要求审计零丢失的
    研究批次使用。

    Args:
        strict: True 时写入失败抛出原异常，而非返回 False。

    Returns:
        True 表示写入成功；False 表示失败（仅 strict=False 时可能返回）。

    Raises:
        Exception: strict=True 且写入失败时，抛出底层异常。
    """
    try:
        log = AuditLog(
            user_id=user_id,
            kind=kind,
            input_json=input_json or {},
            output_json=output_json or {},
            subject=subject,
            age_band=age_band,
        )
        db.add(log)
        await db.flush()
    except Exception as e:
        _record(False, f"{type(e).__name__}: {e}")
        logger.warning("审计写入失败：%s", e)
        if strict:
            raise
        return False

    _record(True)
    return True
