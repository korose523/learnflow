"""审计脚本: 证明 AI 行为管控链路的优化目标里**没有**时长类成瘾化指标。

用途 (向审稿人 / 伦理审查证明):
  1. 打印当前奖励权重 (describe_reward_weights);
  2. 打印已学习的 Q 表规模 (各风险档下机制分布);
  3. 静态扫描 compute_reward 源码, 断言其**不引用**任何时长 / 活跃度 / 答题量 /
     连胜类指标 —— 即优化目标只依赖「学习成效」与「健康风险」。

用法:
    python scripts/audit_intervention_reward.py
    python scripts/audit_intervention_reward.py --q-path path/to/bandit.json   # 载入已训练 Q 表
"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

# 让脚本在 backend 根目录直接运行即可 import app
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.intervention_reward import (  # noqa: E402
    compute_reward, describe_reward_weights,
)
from app.services.learning_orchestrator import _FOMO_ARBITRATOR  # noqa: E402
from app.services.rl_arbitrator import MIN_OBS_FOR_DECISION  # noqa: E402


# 在奖励信号链路的**可执行逻辑**中不得出现的成瘾化指标标识符 (代码级红线)。
#
# 只列英文标识符 —— 代码里的变量/属性名不可能是中文, 中文词只会出现在注释与
# docstring 中。把中文词列进扫描项是此前假阳性的根源: compute_reward 的 docstring
# 里写着「禁止包含使用时长 / 活跃天数 / 连胜长度」, 文本匹配于是把**禁止声明**
# 误判成**实际使用**, 导致审计恒定失败。
_FORBIDDEN_IN_REWARD = (
    "time_spent", "duration", "stay_time", "active_days", "login_freq",
    "answer_count", "drill", "streak_length", "consecutive_days",
    "retention", "engagement", "stickiness", "usage_duration",
)


def _referenced_identifiers(obj) -> set:
    """用 AST 提取函数/类中真实引用的标识符, 天然排除 docstring 与注释。

    AST 不含注释; docstring 虽是节点但为字符串常量, 显式剔除。这样扫描到的是
    **代码真正引用的东西**, 而不是「文档里提到了什么」。
    """
    import ast

    import textwrap

    # dedent: inspect.getsource 对嵌套定义的函数/类会带上外层缩进, 直接 parse 会
    # IndentationError (测试里就地定义的小函数正是这种情况)。
    tree = ast.parse(textwrap.dedent(inspect.getsource(obj)))
    body = list(tree.body[0].body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]  # 剔除 docstring

    idents = set()
    for n in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(n, ast.Name):
            idents.add(n.id)
        elif isinstance(n, ast.Attribute):
            idents.add(n.attr)
        elif isinstance(n, ast.arg):
            idents.add(n.arg)
    return {i.lower() for i in idents}


def audit_reward_source() -> bool:
    """扫描奖励信号链路 (compute_reward + InterventionSignals), 确认不含成瘾化指标。

    两个对象都要扫: 光看公式不够 —— 若在 ``InterventionSignals`` 上加一个
    ``usage_duration`` 字段, 哪怕 compute_reward 暂未引用, 也已经是「为时长指标开后门」。
    """
    from app.services.intervention_reward import InterventionSignals

    leaked: dict = {}
    for name, obj in (("compute_reward", compute_reward),
                      ("InterventionSignals", InterventionSignals)):
        idents = _referenced_identifiers(obj)
        hit = sorted({tok for i in idents
                      for tok in _FORBIDDEN_IN_REWARD if tok in i})
        if hit:
            leaked[name] = hit

    if leaked:
        print(f"[FAIL] 奖励信号链路引用了成瘾化指标: {leaked}")
        return False
    print("[OK]   奖励信号链路未引用任何时长/活跃度/答题量/连胜类指标")
    print("       (AST 扫描: docstring/注释中的禁用声明不计入, 避免假阳性)")
    return True


def report_q_table(q_path: str | None = None) -> dict:
    """返回 Q 表规模与各风险档机制分布。"""
    rl = _FOMO_ARBITRATOR.rl_arbitrator
    if q_path is not None:
        from app.services.rl_arbitrator import BanditPolicy
        bandit = BanditPolicy.load(q_path)
    elif rl is not None:
        bandit = rl.bandit
    else:
        bandit = None

    if bandit is None:
        return {"injected": False, "tiers": 0, "arms": 0, "updates": 0,
                "distribution": {}}

    Q = bandit.Q
    counts = bandit.counts
    tiers = list(Q.keys())
    total_arms = sum(len(arms) for arms in Q.values())
    total_updates = sum(
        sum(c.values()) for c in counts.values()
    )
    distribution = {
        tier: {arm: counts.get(tier, {}).get(arm, 0) for arm in arms}
        for tier, arms in Q.items()
    }
    # 「已训练」不等于「已接管决策」。后者要求该风险档下某 arm 观测次数达到
    # MIN_OBS_FOR_DECISION, 是保守放行门槛 —— 审计需同时报告两者, 以便审稿人确认
    # 系统没有在未学够时就把机制选择权交给 RL。
    ready_tiers = [t for t in tiers if bandit.ready(t)]
    return {
        "injected": True,
        "trained": bandit.trained(),
        "tiers": len(tiers),
        "arms": total_arms,
        "updates": total_updates,
        "distribution": distribution,
        "ready_tiers": ready_tiers,
        "min_obs_for_decision": MIN_OBS_FOR_DECISION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="干预奖励函数伦理审计")
    parser.add_argument("--q-path", default=None,
                        help="已训练 bandit Q 表 json 路径 (可选)")
    args = parser.parse_args()

    print("=" * 60)
    print("AI 行为管控链路 · 干预奖励函数审计")
    print("=" * 60)

    weights = describe_reward_weights()
    print("\n[奖励权重]")
    print(f"  w_mastery (掌握度增益) = {weights['w_mastery']}")
    print(f"  w_health  (风险下降)   = {weights['w_health']}")
    print(f"  裁剪区间                = [{weights['clip_min']}, {weights['clip_max']}]")
    print(f"  阻断硬惩罚              = {weights['blocked_penalty']}")
    print(f"  禁止进入奖励的特征      = {weights['forbidden_features']}")
    print(f"  允许进入奖励的特征      = {weights['allowed_features']}")

    print("\n[Q 表规模 / 风险档机制分布]")
    q = report_q_table(args.q_path)
    print(f"  RL 已注入      = {q['injected']}")
    print(f"  已训练         = {q.get('trained')}")
    print(f"  风险档数       = {q['tiers']}")
    print(f"  机制-档对数    = {q['arms']}")
    print(f"  累计观测次数   = {q['updates']}")
    # 保守放行: 仅达到门槛的风险档才由 RL 接管决策
    print(f"  RL 已接管档位  = {q.get('ready_tiers') or '（无, 仍由规则层决策）'}")
    print(f"  接管门槛(观测) = {q.get('min_obs_for_decision')}")
    for tier, dist in q["distribution"].items():
        print(f"    {tier}: " + ", ".join(f"{a}={n}" for a, n in dist.items()))

    print("\n[伦理扫描]")
    ok = audit_reward_source()

    print("\n" + "=" * 60)
    if ok:
        print("审计通过: 优化目标仅含「学习成效 + 健康风险」, 无时长类成瘾化指标。")
        return 0
    print("审计失败: 奖励函数混入了成瘾化指标, 需修正。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
