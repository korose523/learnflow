"""自陈测量聚合服务 —— 把自陈作答换算为 LAI 输入并报告测量覆盖度

职责
----
LAI 的五个维度中，``control``（25%）与 ``function``（10%）**无法从 ``Attempt``
行为日志中观测**；``cognition`` 亦有一个子指标（时间感知偏差）无法观测。此前这些
输入被硬编码为 0，等于「恒定健康」，使索引结构性偏向「不成瘾」。

本模块是**唯一**的聚合点：读取 ``SelfReportResponse`` 最新一次作答，换算为 LAI
输入键，并据「哪些输入有真实来源」推导出 ``measured_dimensions`` —— 供
``LearningAddictionIndex.assess`` 使用，以及供 API 对外披露覆盖度。

与 ``instrument_catalog`` 的关系
--------------------------------
「哪份量表喂哪个输入」由 ``InstrumentSpec.lai_input`` 定义，本模块**不重复维护**
映射表，避免两处口径漂移。

诚实性契约
----------
* 无自陈数据时，**不返回任何默认值** —— 未覆盖的输入不出现在结果里，其所属维度
  不会被谎报为「已测」。
* 过旧的自陈数据（超过 ``MAX_AGE_DAYS``）视为失效，防止用几个月前的一次作答
  永久支撑当前结论。
* 行为日志侧输入（时长/夜间比例/提示依赖等）只要存在作答记录即视为可得，
  但它们只是**代理指标**，此事实在 ``coverage`` 中以 ``proxy_dimensions`` 披露。
"""
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select

from app.models.instrument import SelfReportResponse
from app.services import instrument_catalog
from app.services.learning_addiction_index import LearningAddictionIndex

logger = logging.getLogger(__name__)

#: 自陈作答的有效期（天）。超过则视为失效，不得支撑当前评分。
MAX_AGE_DAYS = 28

#: 各 LAI 维度的输入来源分解。
#: ``self_report`` 非空的维度，必须有新鲜自陈作答才算「已测」。
DIMENSION_INPUTS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "time": {
        "log": ("daily_minutes", "session_minutes", "night_ratio"),
        "self_report": (),
    },
    "motivation": {
        "log": ("intrinsic_motivation_ratio", "external_reward_dependency"),
        "self_report": (),
    },
    "control": {
        "log": (),
        "self_report": ("planned_stop_failures",),
    },
    "cognition": {
        "log": ("content_attention_ratio",),
        "self_report": ("time_perception_bias",),
    },
    "function": {
        "log": ("sleep_impact", "social_impact"),
        "self_report": ("sleep_impact", "social_impact"),
    },
}

#: 仅由行为日志代理支撑的维度 —— 其取值是代理指标而非直接观测。
PROXY_DIMENSIONS: Tuple[str, ...] = ("time", "motivation")


def _self_report_inputs() -> Dict[str, str]:
    """lai_input → instrument_code，直接取自量表目录（单一事实来源）。"""
    return {spec.lai_input: spec.code for spec in instrument_catalog.all_instruments()}


async def latest_self_report_inputs(
    db, user_id: str, max_age_days: int = MAX_AGE_DAYS
) -> Dict[str, dict]:
    """取该用户每个 LAI 输入键**最新且未过期**的自陈取值。

    Returns:
        ``{lai_input: {"value": float, "instrument_code": str,
        "submitted_at": iso8601, "raw_total": int, "normalized": float}}``；
        无有效作答的输入键**不会出现在结果中**（不填默认值）。
    """
    if db is None or not user_id:
        return {}

    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    codes = list(_self_report_inputs())
    if not codes:
        return {}

    try:
        result = await db.execute(
            select(SelfReportResponse)
            .where(SelfReportResponse.user_id == user_id)
            .where(SelfReportResponse.submitted_at >= cutoff)
            .order_by(SelfReportResponse.submitted_at.desc())
        )
        rows = list(result.scalars().all())
    except Exception as exc:  # pragma: no cover - 防御性：聚合失败不得炸掉评分
        logger.warning("自陈聚合查询失败，按「无自陈数据」处理：%s", exc)
        return {}

    out: Dict[str, dict] = {}
    for row in rows:
        # rows 已按时间倒序，每个 lai_input 首次出现即为最新
        if row.lai_input in out:
            continue
        out[row.lai_input] = {
            "value": float(row.lai_value),
            "instrument_code": row.instrument_code,
            "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
            "raw_total": int(row.raw_total),
            "normalized": float(row.normalized),
        }
    return out


def _dimension_measured(dim: str, covered_inputs: Set[str]) -> bool:
    """某维度是否已由新鲜自陈作答支撑（看它的 self_report 必需输入是否齐备）。"""
    required = set(DIMENSION_INPUTS[dim]["self_report"])
    if not required:
        # 无自陈要求的维度（time / motivation）由行为日志代理支撑
        return True
    return required.issubset(covered_inputs)


async def measured_dimensions(
    db, user_id: str, max_age_days: int = MAX_AGE_DAYS
) -> Set[str]:
    """返回当前由真实测量支撑的 LAI 维度集合。

    这是传给 ``LearningAddictionIndex.assess(measured_dimensions=...)`` 的值。
    """
    covered = set((await latest_self_report_inputs(db, user_id, max_age_days)).keys())
    return {d for d in DIMENSION_INPUTS if _dimension_measured(d, covered)}


async def coverage_report(
    db, user_id: str, max_age_days: int = MAX_AGE_DAYS
) -> dict:
    """测量覆盖度报告 —— 用于对外披露「这个 LAI 分数基于多少测量」。

    Returns:
        含 ``measured`` / ``unmeasured`` / ``complete`` / ``weight_basis`` /
        ``proxy_dimensions`` / ``self_report_inputs`` / ``missing_instruments``
        的 dict；``missing_instruments`` 列出补测后即可提升覆盖度的量表。
    """
    inputs = await latest_self_report_inputs(db, user_id, max_age_days)
    covered = set(inputs)
    measured = {d for d in DIMENSION_INPUTS if _dimension_measured(d, covered)}
    all_dims = set(DIMENSION_INPUTS)

    # 归因：某维度未测时，列出缺失的输入键及其对应量表
    input_to_code = _self_report_inputs()
    missing_inputs: List[str] = []
    missing_instruments: List[dict] = []
    seen_codes: Set[str] = set()
    for dim in sorted(all_dims - measured):
        for key in DIMENSION_INPUTS[dim]["self_report"]:
            if key not in covered:
                missing_inputs.append(key)
                code = input_to_code.get(key)
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    spec = instrument_catalog.get_instrument(code)
                    missing_instruments.append(
                        {
                            "code": code,
                            "name_zh": spec.name_zh if spec else code,
                            "lai_input": key,
                            "dimension": dim,
                            "item_count": spec.item_count if spec else None,
                        }
                    )

    # 权重取自 LAI 引擎本身（单一事实来源），不在此重复字面量
    weights = LearningAddictionIndex.WEIGHTS
    weight_basis = sum(weights[d] for d in measured)

    return {
        "measured": sorted(measured),
        "unmeasured": sorted(all_dims - measured),
        "complete": measured == all_dims,
        "weight_basis": round(weight_basis, 4),
        # 代理维度：由行为日志推导，非直接观测 —— 阅读结论时必须知晓
        "proxy_dimensions": [d for d in PROXY_DIMENSIONS if d in measured],
        "self_report_inputs": {
            k: {"value": v["value"], "instrument_code": v["instrument_code"],
                "submitted_at": v["submitted_at"]}
            for k, v in sorted(inputs.items())
        },
        "missing_inputs": missing_inputs,
        "missing_instruments": missing_instruments,
        "max_age_days": max_age_days,
    }


async def lai_inputs_from_self_report(
    db, user_id: str, max_age_days: int = MAX_AGE_DAYS
) -> Dict[str, object]:
    """仅返回可直接覆盖到 LAI 入参的自陈值（``{lai_input: value}``）。

    与 ``LearningAddictionIndex.assess`` 的入参名一一对应，供调用方直接 ``**`` 合并。
    """
    inputs = await latest_self_report_inputs(db, user_id, max_age_days)
    return {k: v["value"] for k, v in inputs.items()}
