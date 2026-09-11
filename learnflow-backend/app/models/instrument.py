"""自陈测量作答记录模型

用途
----
存放自陈量表（见 ``app/services/instrument_catalog.py``）的一次施测结果，
供 LAI 的「行为控制 / 功能影响 / 时间感知偏差」维度取值。

⚠️ 数据敏感性与边界（重要）
---------------------------
本表存放的是**未成年人自陈的心理与行为数据**（睡眠、社交、自控感受），
属于受试者研究原始数据，敏感度高于普通业务数据：

* 受伦理与**数据最小化**约束：仅采集量表所需字段，不额外记录设备/位置等标识；
* **不得**随代码仓库或公开 artifact 一起归档（与 ``artifacts/state/``、
  ``artifacts/experiments.json`` 同级处置）；
* 导出与使用须在 ``ConsentType.DATA_RESEARCH`` 同意范围内；
* 检索与导出应通过受控端点，不得提供无条件全表导出。

计分结果同时冗余存入本表（``raw_total`` / ``normalized``），目的是**冻结当时的计分口径**：
``catalog_fingerprint`` 记录作答时所用量表目录版本，使日后题项或计分规则变更时，
历史数据仍可复现其原始分数，而不会被新规则追溯改写。
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Float, JSON, Index,
)

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class SelfReportResponse(Base):
    """一次自陈量表施测的作答与计分结果。"""

    __tablename__ = "self_report_responses"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    #: 量表 code，对应 instrument_catalog 中的 InstrumentSpec.code
    instrument_code = Column(String(64), nullable=False, index=True)

    #: 与题项同序的作答值列表（likert: 1..5；count: 0..7）
    answers = Column(JSON, nullable=False)

    #: 计分结果（冗余存储以冻结当时口径）
    raw_total = Column(Integer, nullable=False)
    normalized = Column(Float, nullable=False)

    #: 该结果映射到的 LAI 输入键与其值（便于聚合时免于重算）
    lai_input = Column(String(64), nullable=False)
    lai_value = Column(Float, nullable=False)

    #: 作答时的量表目录指纹 —— 可复现性锚点
    catalog_fingerprint = Column(String(32), nullable=True)

    #: 施测情境（如 session / weekly_checkin），供研究分析分层
    context = Column(JSON, default=dict)

    submitted_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    __table_args__ = (
        # 聚合查询主路径：按用户 + 量表取最近一次
        Index("ix_srr_user_instrument_time", "user_id", "instrument_code", "submitted_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "instrument_code": self.instrument_code,
            "answers": self.answers,
            "raw_total": self.raw_total,
            "normalized": self.normalized,
            "lai_input": self.lai_input,
            "lai_value": self.lai_value,
            "catalog_fingerprint": self.catalog_fingerprint,
            "context": self.context or {},
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }
