"""验证脚本：LEARNFLOW_STATE_BACKEND=json 时，游戏化状态是否真的能跨"进程重启"存活。

目的：不依赖 tests/ 下任何既有测试（包括 worker 写的），独立证明
「90 天纵向研究数据不会因进程重启而丢失」这一核心主张。

模拟进程重启的方式：清空 sys.modules 里 app.* 的模块缓存后重新导入，
迫使所有容器重新走 default_state_store() 从磁盘读回。
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

# 关键：必须在导入任何 app.service 之前设置，因为容器在类体求值（导入期）就建好了
STATE_DIR = os.path.join(tempfile.mkdtemp(prefix="lf_smoke_"), "state")
os.environ["LEARNFLOW_STATE_BACKEND"] = "json"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 把落库目录重定向到临时目录，避免污染 artifacts/state
import app.services.state_store as ss  # noqa: E402

ss._state_dir = lambda: STATE_DIR

from app.services.team_competition_engine import (  # noqa: E402
    TeamLeagueEngine,
    TeamManagementEngine,
)

failures = []


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "OK  " if cond else "FAIL"
    print(f"[{status}] {label}" + (f"  -> {detail}" if detail else ""))
    if not cond:
        failures.append(label)


def restart_process():
    """模拟进程重启：丢弃所有 app.* 模块缓存，重新导入。"""
    for name in [m for m in list(sys.modules) if m == "app" or m.startswith("app.")]:
        del sys.modules[name]
    # 重新导入后 _state_dir 需要再次打补丁（模块被重新执行）
    import app.services.state_store as ss2

    ss2._state_dir = lambda: STATE_DIR
    from app.services.team_competition_engine import TeamManagementEngine as T2

    return T2


print("=" * 72)
print("独立冒烟：json 后端下的状态持久化")
print(f"落盘目录: {STATE_DIR}")
print("=" * 72)

# ── 会话 1：写入数据 ──────────────────────────────────────────
team = TeamManagementEngine.create_team("冒烟战队", "SMK", "captain_1", "math")
print(f"\n[会话1] 创建战队 id={team.id}, 队长 captain_1")

# 触发就地修改：record_team_contribution 修改 team.total_xp / subject_scores /
# member.contribution_xp —— 这正是原来会静默丢失的地方
TeamLeagueEngine.record_team_contribution(team.id, "captain_1", "math", 100)
TeamLeagueEngine.record_team_contribution(team.id, "captain_1", "math", 50)

before = TeamManagementEngine.TEAMS.get(team.id)
print(f"[会话1] 两次贡献后 total_xp={before.total_xp}")
check("写入后内存中 total_xp == 150", before.total_xp == 150, f"实际 {before.total_xp}")

# 邀请新成员（join_team 就地 append members）
# 注意签名顺序是 join_team(team_id, user_id, name)
res = TeamManagementEngine.join_team(team.id, "member_2", "小明")
check("join_team 返回成功", res.get("success") is True, f"实际 {res}")
after_join = TeamManagementEngine.TEAMS.get(team.id)
print(f"[会话1] 加入成员后 members 数 = {len(after_join.members)}")
check("会话1 中 members 已变为 2", len(after_join.members) == 2,
      f"实际 {len(after_join.members)}")

# ── 模拟进程重启 ──────────────────────────────────────────────
print("\n--- 模拟进程重启（清空模块缓存，从磁盘读回）---")
T2 = restart_process()
reloaded = T2.TEAMS.get(team.id)

check("重启后战队仍在", reloaded is not None)
check("重启后 total_xp 仍为 150（就地修改已落盘）",
      reloaded is not None and reloaded.total_xp == 150,
      f"实际 {getattr(reloaded, 'total_xp', None)}")
check("重启后 members 数仍为 2（join_team 的 append 已落盘）",
      reloaded is not None and len(reloaded.members) == 2,
      f"实际 {len(reloaded.members) if reloaded else None}")

# 类型还原：members 元素必须是 TeamMember 实例而非 dict（此前是崩溃缺口）
# 注意：模拟重启会重新导入模块，TeamMember 类对象已换新，isinstance 会失效，
# 故此处比类名 —— 判据是「不能退化成 dict」。
if reloaded and reloaded.members:
    m0 = reloaded.members[0]
    check("members 元素还原为 TeamMember 实例（不是 dict）",
          type(m0).__name__ == "TeamMember", f"实际类型 {type(m0).__name__}")
    check("members 元素可访问 .user_id",
          hasattr(m0, "user_id"), f"实际属性 {list(vars(m0).keys())[:4] if hasattr(m0, '__dict__') else type(m0)}")
    joined = getattr(m0, "joined_at", None)
    from datetime import datetime

    check("TeamMember.joined_at 还原为 datetime（不是字符串）",
          isinstance(joined, datetime), f"实际类型 {type(joined).__name__}")

check("subject_scores 正确还原",
      reloaded is not None and reloaded.subject_scores.get("math") == 150,
      f"实际 {getattr(reloaded, 'subject_scores', None)}")

# ── 退出成员（leave_team 就地重排 members）──────────────────
T2.leave_team("member_2")
T3 = restart_process()
after_leave = T3.TEAMS.get(team.id)
check("重启后退出仍生效（members 回到 1）",
      after_leave is not None and len(after_leave.members) == 1,
      f"实际 {len(after_leave.members) if after_leave else None}")

print("\n" + "=" * 72)
if failures:
    print(f"结果：{len(failures)} 项失败 -> {failures}")
else:
    print("结果：全部通过 —— json 后端下状态可跨进程重启存活，就地修改已落盘")
print("=" * 72)

shutil.rmtree(os.path.dirname(STATE_DIR), ignore_errors=True)
sys.exit(1 if failures else 0)
