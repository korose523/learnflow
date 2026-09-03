"""决策审计落库助手（未成年人保护硬约束）

所有难度 / 奖励 / 风险决策必须写入 audit_logs。
"""
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AuditLog, AuditKind


async def write_audit(
    db: AsyncSession,
    kind: AuditKind,
    user_id: Optional[str] = None,
    input_json: Optional[dict] = None,
    output_json: Optional[dict] = None,
    subject: Optional[str] = None,
    age_band: Optional[str] = None,
) -> None:
    """写入一条审计记录（best-effort，失败仅记录日志不阻断主流程）"""
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
    except Exception as e:  # pragma: no cover
        import logging
        logging.getLogger(__name__).warning("审计写入失败：%s", e)
