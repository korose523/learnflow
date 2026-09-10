"""LLM 干预生成 + 暗黑模式护栏。

用 LLM 生成**个性化、非操控性**的干预话术, 并强制一道护栏:
任何含有论文 §9 所列「暗黑模式」关键词 (连胜/排名/限时/负罪感/攀比/付费复活…)
的输出都会被替换为安全模板。这把「AI 辅助伦理护栏」做成可审计的工程事实,
直接支撑论文关于「合规/反暗黑模式」的贡献点。
"""
from __future__ import annotations

import re
from typing import Dict, List

from app.services.ollama_client import get_ollama

# 暗黑模式关键词 (论文 §9 对照的多邻国暗黑模式清单); 命中即视为不安全
_FORBIDDEN = [
    "连胜", "streak", "排行榜", "排名", "限时", "倒计时", "错过", "再不",
    "别人", "同学都", "落后", "红心", "心脏", "复活", "抓紧", "赶紧",
    "fomo", "fear", "断签", "惩罚", "就差", "最后", "仅剩",
]
_FORBIDDEN_RE = re.compile("|".join(re.escape(w) for w in _FORBIDDEN), re.IGNORECASE)

_SYSTEM = ("你是学习陪伴助手。只生成温和、非操控、尊重自主性的鼓励语。"
           "绝对不要使用连胜/排名/限时/负罪感/攀比/付费复活等暗黑模式话术。")

_SAFE_TEMPLATE = "你今天已经很努力了，记得按时休息。学习是为了更好的自己，慢慢来也可以。"


def generate_intervention(user_state: Dict, risk: float) -> Dict:
    """user_state: {name, level, ...}; risk: 0-1 成瘾风险。
    返回 {message, safe, mechanism_id, tone}。
    """
    ollama = get_ollama()
    name = user_state.get("name", "同学")
    mood = "low" if risk >= 0.5 else "ok"
    prompt = (f"给{name}一句简短(≤30字)的学习鼓励语, 当前状态: "
              f"{'需要减负休息' if mood == 'low' else '状态不错'}。只输出这句话。")
    try:
        text = ollama.generate(prompt, system=_SYSTEM)
    except Exception:
        text = _SAFE_TEMPLATE
    safe = not _FORBIDDEN_RE.search(text or "")
    if not safe:
        text = _SAFE_TEMPLATE
        safe = True
    # 高风险的回退到「健康推开」类机制 (LF-M51/52/53 为 withdraw)
    mechanism_id = "LF-M53" if risk >= 0.5 else "LF-M51"
    return {"message": text, "safe": safe, "mechanism_id": mechanism_id,
            "tone": "rest" if risk >= 0.5 else "encourage"}


def personalize_intervention_message(
    user_state: Dict, risk: float, rule_message: str
) -> str:
    """用 LLM 生成个性化干预话术; LLM 不可用时回退到既有规则话术。

    这是 ``llm_intervention.py`` 真正接入主流程的入口 (此前零调用方 -> 死代码)。
    设计要点 (与任务「保留规则兜底」一致):

    * ollama 未启动 / 超时被 :func:`get_ollama` 判定为不可用 (返回 ``MockOllama``,
      ``available()`` 为 ``False``) -> **直接回退** ``rule_message``, 绝不把一条
      通用安全模板悄悄替换掉本就有意义、针对具体机制的规则文案, 保证用户始终能看到反馈。
    * ollama 可用但返回含暗黑模式关键词 -> :func:`generate_intervention` 内部护栏会
      替换为 ``_SAFE_TEMPLATE`` (这是有意的合规行为, 与「可用性兜底」是两回事)。
    * 任何异常 -> 回退 ``rule_message``, 不拖垮调用方。
    """
    try:
        ollama = get_ollama()
    except Exception:
        return rule_message
    if not ollama.available():
        return rule_message
    try:
        out = generate_intervention(user_state, risk)
    except Exception:
        return rule_message
    msg = out.get("message") if isinstance(out, dict) else None
    if not msg:
        return rule_message
    return msg

