"""新手引导 / 情境帮助 / 功能发现 API (LF-Onboarding)

把已实现的引导引擎 ``app.services.onboarding_engine`` 暴露为 HTTP 接口,
消除「引擎已实现但无运行时入口」的死代码:

- ``GET  /api/v1/onboarding/steps``    某角色的完整引导流程 (OnboardingEngine.get_onboarding)
- ``GET  /api/v1/onboarding/current``  当前应进行的步骤 (OnboardingEngine.get_current_step)
- ``POST /api/v1/onboarding/complete`` 完成一步并领取奖励 (OnboardingEngine.complete_step)
- ``POST /api/v1/onboarding/skip``     跳过引导 (OnboardingEngine.skip_onboarding)
- ``GET  /api/v1/onboarding/help``     情境帮助 (ContextualHelpEngine.get_help_for_trigger)
- ``GET  /api/v1/onboarding/features`` 新功能发现 (FeatureDiscoveryEngine.check_new_features)
- ``PUT  /api/v1/onboarding/profile``  引导向导采集的学习档案真实落库（年级/学科/监护人同意）

**两类语义必须区分**：``steps``/``current``/``complete``/``skip`` 暴露的是
**产品导览引擎**（无状态：``complete_step`` 只按 STEP_REWARDS 查表返回奖励
dict，**不写任何数据库**）；而 ``profile`` 才是**引导向导**（grade → subjects
→ consent）的真实持久化端点。不要把前者当作后者使用，否则前端会以为数据已
落库而实际什么也没存。

所有引擎方法均为返回普通 dict/list 的 classmethod, 已可直接 JSON 序列化,
本模块只做参数解析与错误映射, 不复制任何引擎逻辑。
"""
from datetime import UTC, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.onboarding_engine import (
    OnboardingEngine,
    ContextualHelpEngine,
    FeatureDiscoveryEngine,
)

router = APIRouter(prefix="/api/v1/onboarding", tags=["新手引导"])


# ── 请求体 ───────────────────────────────────────────────
class CompleteStepRequest(BaseModel):
    role: str
    step_id: str


class SkipRequest(BaseModel):
    role: str


class ProfileRequest(BaseModel):
    """引导向导采集的学习档案。所有字段可选，只更新显式提供的字段。"""
    grade: Optional[str] = None
    subjects: Optional[List[str]] = None
    consent_name: Optional[str] = None
    consent_agreed: bool = False


def _parse_completed(raw: str) -> List[str]:
    """把逗号分隔的 completed 解析为列表; 空 / 省略 → []。"""
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def _parse_help_context(raw: Optional[str]) -> Optional[dict]:
    """把 ``key=value,key2=value2`` 解析为 dict。

    - 为 None → 返回 None (引擎会忽略 context)
    - 任一片段缺少 ``=`` → 视为格式错误, 返回 sentinel 标记由调用方转 400
    """
    if raw is None:
        return None
    result: dict = {}
    for pair in raw.split(","):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise HTTPException(
                status_code=400,
                detail="context 格式错误：应为逗号分隔的 key=value 对，例如 feature_name=技能树,benefit=提升效率",
            )
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


# ── 路由 ────────────────────────────────────────────────
@router.get("/steps")
async def get_steps(
    role: str = Query("student", description="角色：student / teacher / parent"),
    user: User = Depends(get_current_user),
) -> dict:
    """获取某角色的完整引导流程（步骤列表 + 预计总时长）。"""
    return OnboardingEngine.get_onboarding(role)


@router.get("/current")
async def get_current(
    role: str = Query("student", description="角色：student / teacher / parent"),
    completed: str = Query("", description="已完成步骤 step_id，逗号分隔，可省略"),
    user: User = Depends(get_current_user),
) -> dict:
    """获取当前应进行的步骤；全部完成则返回 has_next=False。"""
    completed_steps = _parse_completed(completed)
    return OnboardingEngine.get_current_step(role, completed_steps)


@router.post("/complete")
async def complete_step(
    body: CompleteStepRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """完成一个引导步骤，返回 XP 奖励 / 徽章 / 解锁信息。"""
    return OnboardingEngine.complete_step(body.role, body.step_id)


@router.post("/skip")
async def skip_onboarding(
    body: SkipRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """跳过引导流程。"""
    return OnboardingEngine.skip_onboarding(body.role)


@router.get("/help")
async def get_help(
    trigger: Optional[str] = Query(None, description="触发点标识，如 first_error / idle_30s"),
    context: Optional[str] = Query(
        None,
        description="可选上下文，逗号分隔 key=value，用于模板替换（如 feature_name=技能树）",
    ),
    user: User = Depends(get_current_user),
) -> dict:
    """获取情境帮助。

    - 缺少 trigger 或 trigger 未知 → 引擎返回 None → HTTP 404
    - context 格式错误（缺 ``=``）→ HTTP 400
    """
    if trigger is None or trigger == "":
        raise HTTPException(status_code=404, detail="缺少情境帮助触发点（trigger）")

    parsed_context = _parse_help_context(context)  # 可能抛 400
    help_info = ContextualHelpEngine.get_help_for_trigger(trigger, parsed_context)
    if help_info is None:
        raise HTTPException(status_code=404, detail=f"未找到触发点「{trigger}」的情境帮助")
    return help_info


@router.get("/features")
async def check_features(
    role: str = Query("student", description="角色：student / teacher / parent"),
    sessions_completed: int = Query(0, ge=0, description="已完成的学习会话数（>=0）"),
    user: User = Depends(get_current_user),
) -> List[dict]:
    """检查当前会话数下是否有新功能可解锁（按解锁进度表精确匹配）。"""
    return FeatureDiscoveryEngine.check_new_features(role, sessions_completed)


@router.put("/profile")
async def save_profile(
    body: ProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """持久化引导向导（grade → subjects → consent）采集的学习档案。

    与上面的产品导览端点语义不同：``POST /complete`` 只做无状态奖励查询，
    **不写库**；本端点是向导数据的唯一真实落库路径。

    - 仅更新显式提供的字段（``None`` 表示「不改动」
    - ``consent_agreed=True`` 时写入监护人同意记录（姓名 + 时间戳）
    - 写库依赖 ``get_db`` 的自动 commit（与项目内其他写端点一致）
    - **必须从本请求的 ``db`` 会话重新加载用户**：``get_current_user`` 注入的
      ``user`` 来自另一个会话（甚至是脱离会话的实例），直接改它再 ``flush()``
      不会落库。这与 ``parent.py`` 写端点的做法一致。
    """
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.grade is not None:
        db_user.grade = body.grade
    if body.subjects is not None:
        # 整体重新赋值而非原地 append：JSON 列的原地改不会被 SQLAlchemy 追踪
        db_user.subjects = list(body.subjects)
    if body.consent_agreed:
        consents = dict(db_user.consents or {})
        consents["parental_consent"] = True
        consents["parental_consent_name"] = body.consent_name
        consents["parental_consent_at"] = datetime.now(UTC).isoformat()
        db_user.consents = consents

    await db.flush()

    return {
        "grade": db_user.grade,
        "subjects": db_user.subjects or [],
        "consents": db_user.consents or {},
    }
