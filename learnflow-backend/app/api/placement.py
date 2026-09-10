"""入学水平测试 (自适应 CAT) API (LF-Placement)

把已实现的水平测试引擎 ``app.services.placement_test_engine`` 暴露为 HTTP 接口,
消除「引擎已实现但无运行时入口」的死代码:

- ``POST /api/v1/placement/start``   开始测试, 返回 session_id 与首题
- ``POST /api/v1/placement/answer`` 提交答案, 自适应出下题或收敛出结果

================================================================================
⚠️ 会话存储说明（对论文很重要，请勿假装它是分布式）
--------------------------------------------------------------------------------
引擎本身是**无状态 classmethod**, 通过 ``PlacementState`` 对象在每次调用间传递;
它本身没有任何会话/存储层。本模块在 **进程内** 用一个字典 ``_SESSIONS`` 保存
``session_id -> PlacementState``, 并用一把 ``threading.Lock`` 保护并发读写。

这是 **单进程 / 单 worker 仅** 的简易方案:
- 多 worker (例如多 uvicorn 进程 / 容器横向扩展) 时, 会话只存在于某一个 worker 内,
  其它 worker 会因查不到 session_id 而返回 404;
- 进程重启会丢失所有进行中的会话;
- 没有持久化, 也没有跨节点共享。

生产部署若要支持多 worker, 必须把 ``_SESSIONS`` 换成 **Redis** 或一张 **数据库表**
(序列化 PlacementState), 并把 TTL 清理交给 Redis 的 TTL / 定时任务。这里刻意保留
为最小可运行实现, 并明确标注其局限, 而不是伪装成生产级分布式会话。
================================================================================
"""
import threading
import time
import uuid
from datetime import datetime, UTC
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.models.user import User
from app.services.placement_test_engine import (
    AdaptivePlacementEngine,
    PlacementState,
)

router = APIRouter(prefix="/api/v1/placement", tags=["入学水平测试"])

# ── 进程内会话存储（单 worker 仅） ──────────────────────
_SESSIONS: Dict[str, Dict] = {}          # session_id -> {"state": PlacementState, "created_at": float}
_LOCK = threading.Lock()
_TTL_SECONDS = 30 * 60                    # 30 分钟过期


def _purge_expired() -> None:
    """在持锁状态下清理超过 TTL 的会话（惰性清理, 仅在 /start 时触发）。"""
    now = time.monotonic()
    expired = [
        sid for sid, entry in _SESSIONS.items()
        if now - entry["created_at"] > _TTL_SECONDS
    ]
    for sid in expired:
        _SESSIONS.pop(sid, None)


# ── 请求体 ───────────────────────────────────────────────
class AnswerRequest(BaseModel):
    session_id: str
    is_correct: bool


# ── 路由 ────────────────────────────────────────────────
@router.post("/start")
async def start_test(
    user: User = Depends(get_current_user),
) -> dict:
    """开始一次自适应水平测试。

    返回 session_id（后续 /answer 凭此定位会话）、引擎的 start 负载, 以及首题。
    """
    with _LOCK:
        _purge_expired()
        session_id = uuid.uuid4().hex
        # 注意: 引擎的 start_test 只返回「开始说明」dict, 并不持有/返回状态对象,
        # 状态必须由本模块自行构造并保存。
        state = PlacementState(
            user_id=user.id,
            test_started_at=datetime.now(UTC),
            phase="testing",
        )
        _SESSIONS[session_id] = {"state": state, "created_at": time.monotonic()}

    start_payload = AdaptivePlacementEngine.start_test(user.id)
    first_question = AdaptivePlacementEngine.get_next_question(state)
    return {
        "session_id": session_id,
        "started": start_payload,
        "question": first_question,
    }


@router.post("/answer")
async def submit_answer(
    body: AnswerRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """提交一道题的答案。

    - session_id 未知或已过期 → HTTP 404
    - 收敛 → 返回 {"converged": True, "result": ...}
    - 未收敛 → 返回 {"converged": False, "question": 下一题}
    """
    with _LOCK:
        entry = _SESSIONS.get(body.session_id)
        if entry is None:
            raise HTTPException(
                status_code=404,
                detail="会话不存在或已过期，请重新发起 /api/v1/placement/start",
            )
        state = entry["state"]

    submit_result = AdaptivePlacementEngine.submit_answer(state, body.is_correct)

    if AdaptivePlacementEngine._check_convergence(state):
        with _LOCK:
            _SESSIONS.pop(body.session_id, None)
        return {
            "converged": True,
            "result": AdaptivePlacementEngine.generate_result(state),
        }

    return {
        "converged": False,
        "answered": submit_result,
        "question": AdaptivePlacementEngine.get_next_question(state),
    }
