"""自陈测量 API：量表目录、施测提交、结果查询与测量覆盖度

⚠️ 机制编号说明：本模块是**测量基础设施**，不是游戏化行为干预机制，因此
**不登记**进 ``mechanism_registry``（保持权威计数 54 个机制不变）。
它的干预侧对应物是既有的 LF-M53（LAI 自适应降级）——本模块只负责把
「降级决策所依赖的输入」变成真实测量所得，不自行实施干预。

为什么需要这个模块
------------------
LAI 五维框架中 ``control``(25%) 与 ``function``(10%) 无法从 ``Attempt`` 行为日志
观测，``cognition`` 亦有一个子指标不能观测。此前这些输入被硬编码为 0，使索引
结构性偏向「不成瘾」。本模块提供**自陈侧采集入口**，与行为日志组成双源测量：

- ``GET  /instruments``               量表目录（含题项；可按维度过滤）
- ``GET  /instruments/catalog``       目录元信息 + 指纹（可复现性引用）
- ``GET  /instruments/me/responses``  我本人的作答历史
- ``GET  /instruments/me/coverage``   我的 LAI 测量覆盖度（哪些维度已实测）
- ``POST /instruments/{code}/responses``  提交一次施测（服务端计分后落库）
- ``GET  /instruments/{code}``        单份量表题项

计分与映射全部委托 ``instrument_catalog``，覆盖度推导委托
``self_report_service``；本模块只做参数解析、鉴权与错误映射，不复制任何计分逻辑。

数据边界与伦理
--------------
存放的是**未成年人自陈的心理/行为数据**（睡眠、社交、自控感受）：

* 仅本人可读写自己的作答（``user_id`` 强制取自当前登录用户，不接受请求体传入）；
* 提交时解析研究知情同意状态并**标记**在记录上（``context["research_consent"]``）——
  采集属产品功能，同意状态用于研究分析时的样本筛除，依既有设计**不阻断**提交；
* 不提供无条件全表导出；导出须在 ``ConsentType.DATA_RESEARCH`` 范围内另行受控进行。

⚠️ 量表题项为本项目自编，**尚未经独立信效度检验**（见 ``instrument_catalog`` 的
诚实声明）。任何引用本测量结果的材料必须声明该局限。
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.instrument import SelfReportResponse
from app.models.user import User
from app.services import instrument_catalog
from app.services.learning_addiction_index import LearningAddictionIndex
from app.services.research_consent import resolve_research_consent
from app.services.self_report_service import (
    MAX_AGE_DAYS,
    coverage_report,
    lai_inputs_from_self_report,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/instruments", tags=["自陈测量"])


# ── 请求体 ────────────────────────────────────────────────

class SubmitInstrumentRequest(BaseModel):
    """一次施测的作答。"""

    answers: List[int] = Field(
        ...,
        description="与题项**同序**的作答值；Likert 题 1..5，计数题 0..7",
    )
    context: Optional[dict] = Field(
        None,
        description='施测情境（可选），如 {"phase": "weekly_checkin"}，仅供研究分层',
    )


# ── 目录类端点（静态前缀必须先于 /{code} 声明，避免被当作 code 匹配）──

@router.get("/catalog")
async def get_catalog(
    dimension: Optional[str] = Query(
        None, description="按 LAI 维度过滤：time/motivation/control/cognition/function"
    ),
    user: User = Depends(get_current_user),
) -> dict:
    """量表目录元信息与指纹。

    ``fingerprint`` 随题项或计分规则变更而变化，可用于论文中锚定测量版本。
    """
    specs = instrument_catalog.all_instruments()
    if dimension:
        specs = instrument_catalog.instruments_for_dimension(dimension)
        if not specs:
            raise HTTPException(
                status_code=400,
                detail=f"未知维度 {dimension!r}；合法取值为 "
                       f"{sorted(LearningAddictionIndex.WEIGHTS)}",
            )
    return {
        "fingerprint": instrument_catalog.catalog_fingerprint(),
        "count": len(specs),
        "instruments": [s.to_dict() for s in specs],
        "provenance_notice": (
            "题项为本项目自编（purpose-built），未经独立信效度检验；"
            "引用其结果的研究材料必须声明该局限。"
        ),
    }


@router.get("")
async def list_instruments(
    dimension: Optional[str] = Query(None, description="按 LAI 维度过滤"),
    user: User = Depends(get_current_user),
) -> dict:
    """列出量表（含题项），可按 LAI 维度过滤。"""
    specs = (
        instrument_catalog.instruments_for_dimension(dimension)
        if dimension
        else instrument_catalog.all_instruments()
    )
    if dimension and not specs:
        raise HTTPException(status_code=400, detail=f"未知维度 {dimension!r}")
    return {
        "count": len(specs),
        "instruments": [s.to_dict() for s in specs],
    }


@router.get("/me/responses")
async def my_responses(
    code: Optional[str] = Query(None, description="只看某份量表"),
    limit: int = Query(20, ge=1, le=200, description="返回条数上限"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """我本人的作答历史（按时间倒序）。

    仅返回当前登录用户的记录 —— ``user_id`` 强制取自登录态，不接受外部传入。
    """
    stmt = (
        select(SelfReportResponse)
        .where(SelfReportResponse.user_id == user.id)
        .order_by(SelfReportResponse.submitted_at.desc())
        .limit(limit)
    )
    if code:
        stmt = stmt.where(SelfReportResponse.instrument_code == code)
    rows = list((await db.execute(stmt)).scalars().all())
    return {"count": len(rows), "responses": [r.to_dict() for r in rows]}


@router.get("/me/coverage")
async def my_coverage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """我的 LAI 测量覆盖度 —— 明确「当前 LAI 分数基于多少测量」。

    回答三个问题：哪些维度已由真实测量支撑、缺哪些量表、以及已测维度占的权重比重。
    未测维度**不会**被谎报为健康。
    """
    report = await coverage_report(db, user.id)
    report["lai_inputs"] = await lai_inputs_from_self_report(db, user.id)
    report["hint"] = (
        "coverage.complete=false 时，LAI 综合分只基于 weight_basis 部分的权重，"
        "引用该分数必须同时披露未测维度。"
    )
    return report


# ── 单份量表与提交 ─────────────────────────────────────────

@router.get("/{code}")
async def get_instrument(
    code: str,
    user: User = Depends(get_current_user),
) -> dict:
    """取单份量表的题项与计分说明。"""
    spec = instrument_catalog.get_instrument(code)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"未知量表 {code!r}")
    return {
        **spec.to_dict(),
        "scoring_method": instrument_catalog.scoring_method(code),
        "max_total": spec.max_total,
    }


@router.post("/{code}/responses")
async def submit_response(
    code: str,
    body: SubmitInstrumentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """提交一次施测：服务端计分后落库，并返回更新后的测量覆盖度。

    计分口径由 ``instrument_catalog.score`` 决定（Likert 反向题按 ``6-value`` 处理
    并归一化到 [0,1]；计数题取和）。作答数量或取值不符 → 400；未知量表 → 404。
    """
    spec = instrument_catalog.get_instrument(code)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"未知量表 {code!r}")

    try:
        scored = instrument_catalog.score(code, body.answers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:  # pragma: no cover - get_instrument 已先行拦截
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # 研究知情同意：标记式判定，任何异常都不阻断提交（与既有设计一致）
    consent = await resolve_research_consent(db, user)
    context = dict(body.context or {})
    context["research_consent"] = {
        "consented": consent.consented,
        "reason": consent.reason,
        "granted_by": consent.granted_by,
    }

    record = SelfReportResponse(
        user_id=user.id,
        instrument_code=code,
        answers=list(body.answers),
        raw_total=scored["raw_total"],
        normalized=scored["normalized"],
        lai_input=scored["lai_input"],
        lai_value=scored["lai_value"],
        catalog_fingerprint=instrument_catalog.catalog_fingerprint(),
        context=context,
    )
    db.add(record)
    # 写库依赖 get_db 的自动 commit（与项目内其他写端点一致）
    await db.flush()

    # 提交后立即回算覆盖度，使前端能即时显示「还差哪份量表」
    report = await coverage_report(db, user.id)

    return {
        "saved": True,
        "response": record.to_dict(),
        "lai_input": scored["lai_input"],
        "lai_value": scored["lai_value"],
        "coverage": {
            "measured": report["measured"],
            "unmeasured": report["unmeasured"],
            "complete": report["complete"],
            "weight_basis": report["weight_basis"],
            "missing_instruments": report["missing_instruments"],
        },
    }
