"""研究知情同意的判定与标记（博士论文伦理合规）

背景
----
项目面向 K12 未成年人，正在开展博士论文研究。答题采数路径
（/submit-answer、/attempt、编排器）曾经全程不校验任何知情同意，导致未取得
同意的被试数据照样进入研究数据集。若论文 Ethics 章节声明「已取得知情同意」，
而实际未做判定，则属不实声明，审稿人一查即为硬伤。

本模块采用**标记式（不阻断）**方案：
  - ❌ 不阻断学习：即使未取得同意，学生照样答题，事件照样写入。
    任何调用方都**不得**据此返回 403 / 拒绝提交 / 拦截流程。
  - ✅ 打标记：每个研究事件携带 ``research_consented``，标明「本次数据是否
    取得有效研究同意」，供后续分析时过滤。
  - ✅ 未成年人（minor）的研究同意**必须由家长授权**：学生本人授权一律无效。

判定规则（reason 码表）
-----------------------
``resolve_research_consent`` 返回 ``ResearchConsentStatus``，其中 ``reason``
为机器可读原因码，供审计脚本与离线分析使用：

  - ``"no_record"``                 查不到任何 DATA_RESEARCH 同意记录
                                    → consented=None（「没问过」，未知）
  - ``"revoked"``                   最新一条记录已被撤销（revoked_at 非空）
                                    → consented=None（视为无效）
  - ``"guardian_granted"``          未成年人，且由家长（PARENT 角色）授权
                                    → consented=True
  - ``"minor_without_guardian_consent"``
                                    未成年人，但授权不满足家长授权要求
                                    （学生自授 / granted_by 为空 / 授权人非 PARENT）
                                    → consented=False
  - ``"self_granted"``              成年人，本人授权（granted_by 为空或本人）
                                    → consented=True
  - ``"granted_by_other"``          成年人，由他人（非本人）授权
                                    → consented=True（成年人无监护人强制要求）
  - ``"error"``                     判定过程异常（db 失败 / user 为 None 等）
                                    → consented=None（容错，绝不冒泡）

语义要点
--------
  - ``consented=None`` 与 ``consented=False`` 必须严格区分：
    ``None`` 表示「未知 / 未判定 / 没问过 / 已撤销」，``False`` 表示「明确未取得
    有效同意」。二者在伦理审查中的处理方式不同（前者需进一步追溯，后者应直接
    排除），不得混用。
  - 已撤销的记录必须视为无效（排除），且以 ``"revoked"`` 区别于「从未记录」。
  - 任何异常都返回 ``None + error`` 并记 warning，**绝不能让同意判定失败导致
    答题提交 500**——这是本项目的既定契约（标记式方案的前提）。
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select

from app.models.consent import ConsentRecord, ConsentType
from app.models.user import User, UserRole
from app.services.anti_addiction import infer_age_band, to_age_group
from app.services.anti_addiction_compliance import MinorProtectionEngine

logger = logging.getLogger(__name__)


@dataclass
class ResearchConsentStatus:
    """单次研究事件的知情同意判定结果。

    Attributes:
        consented: True / False / None(未知)。``None`` 与 ``False`` 语义不同，
            分析时必须区分（见模块 docstring）。
        reason: 机器可读原因码（见模块 docstring 的 reason 码表）。
        granted_by: 实际授权人 user_id（可能为 None）。
    """

    consented: Optional[bool]
    reason: str
    granted_by: Optional[str] = None


def judge_research_consent(
    record: Optional[ConsentRecord],
    is_minor: bool,
    granted_by_user: Optional[User] = None,
) -> ResearchConsentStatus:
    """同步纯函数：给定同意记录 + 是否未成年，判定研究同意状态（不查 db）。

    该函数不访问数据库，仅做逻辑判定，便于单测覆盖所有规则分支而无需构造 db。
    异步版 ``resolve_research_consent`` 内部调用它。

    Args:
        record: 被试最新的 DATA_RESEARCH 同意记录；为 None 表示查不到记录。
        is_minor: 被试是否未成年（由调用方用
            ``MinorProtectionEngine.is_minor(to_age_group(infer_age_band(user)))`` 得出）。
        granted_by_user: ``record.granted_by`` 对应的授权人 User 对象（用于校验
            其 ``role == PARENT``）。为 None 表示未查到授权人（此时无法确认家长身份）。

    Returns:
        ResearchConsentStatus，语义与 reason 码表见模块 docstring。
    """
    # 1) 查不到任何记录 → 未知（「没问过」）
    if record is None:
        return ResearchConsentStatus(consented=None, reason="no_record", granted_by=None)

    # 2) 已撤销 → 视为无效（区别于「从未记录」）
    if record.revoked_at is not None:
        return ResearchConsentStatus(consented=None, reason="revoked", granted_by=None)

    subject_id = record.user_id

    # 3) 成年人：本人授权即可；他人授权也接受（无监护人强制要求）
    if not is_minor:
        if granted_by_user is not None and granted_by_user.id != subject_id:
            return ResearchConsentStatus(
                consented=True,
                reason="granted_by_other",
                granted_by=str(record.granted_by),
            )
        return ResearchConsentStatus(
            consented=True,
            reason="self_granted",
            granted_by=str(record.granted_by) if record.granted_by else None,
        )

    # 4) 未成年人：必须由家长授权，否则一律无效
    granted_by = record.granted_by
    guardian_valid = (
        granted_by is not None
        and granted_by_user is not None
        # 授权人 ≠ 被试本人（排除学生自授）
        and granted_by_user.id != subject_id
        # 授权人必须是家长角色
        and granted_by_user.role == UserRole.PARENT
    )
    if guardian_valid:
        return ResearchConsentStatus(
            consented=True, reason="guardian_granted", granted_by=str(granted_by)
        )
    return ResearchConsentStatus(
        consented=False,
        reason="minor_without_guardian_consent",
        granted_by=str(granted_by) if granted_by else None,
    )


async def resolve_research_consent(
    db,
    user: Optional[User],
) -> ResearchConsentStatus:
    """异步判定被试的研究知情同意状态（标记式，永不阻断）。

    查 ``ConsentRecord``（user_id == user.id、consent_type == DATA_RESEARCH），
    取 ``consented_at`` 最新的一条；若最新记录已撤销则视为无效。未成年判定复用
    既有 ``infer_age_band`` / ``to_age_group`` / ``MinorProtectionEngine.is_minor``。
    最终委托纯函数 ``judge_research_consent`` 做规则判定。

    容错契约：任何异常（db 失败、user 为 None、age_band 无法推断等）均返回
    ``consented=None + reason="error"`` 并记 warning，**绝不冒泡**——
    同意判定失败绝不允许导致答题提交 500。

    Args:
        db: AsyncSession；为 None 时直接返回 error（兼容离线 / 回放路径）。
        user: 被试 User 对象；为 None 时直接返回 error。

    Returns:
        ResearchConsentStatus。
    """
    try:
        if db is None or user is None:
            logger.warning("研究同意判定跳过：db 或 user 为 None，按未知处理")
            return ResearchConsentStatus(consented=None, reason="error", granted_by=None)

        # 取被试最新的 DATA_RESEARCH 同意记录（含已撤销，撤销判定交给纯函数）
        result = await db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user.id)
            .where(ConsentRecord.consent_type == ConsentType.DATA_RESEARCH)
            .order_by(ConsentRecord.consented_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()

        # 未成年判定（复用既有实现）
        age_group = to_age_group(infer_age_band(user))
        is_minor = bool(MinorProtectionEngine.is_minor(age_group))

        # 解析授权人对象，用于校验 PARENT 角色
        granted_by_user: Optional[User] = None
        if record is not None and record.granted_by is not None:
            res = await db.execute(
                select(User).where(User.id == record.granted_by).limit(1)
            )
            granted_by_user = res.scalar_one_or_none()

        return judge_research_consent(record, is_minor, granted_by_user)
    except Exception as exc:  # 容错：绝不冒泡
        logger.warning("研究同意判定异常（按未知处理，不阻断提交）：%s", exc)
        return ResearchConsentStatus(consented=None, reason="error", granted_by=None)
