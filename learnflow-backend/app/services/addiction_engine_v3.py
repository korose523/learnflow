"""新增游戏化成瘾引擎：损失厌恶、新起点效应、蔡格尼克效应、峰终定律、惊喜彩蛋"""
import random
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, Optional


class LossAversionEngine:
    """损失厌恶 + 沉没成本引擎

    原理：人们对损失的敏感度是收益的2倍。已投入的学习时间/连胜/进度产生沉没成本，
    中断意味着"损失"，驱使用户保持连续学习。

    功能：
    - 连胜保护盾：积累到一定天数可获得1天保护
    - 进度可视化：显示"已学习X天，中断将损失Y XP"
    - 回撤警告：显示即将失去的奖励
    """

    @staticmethod
    def get_streak_shield(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取连胜保护状态"""
        streak = user_data.get("streak", 0)
        shields = max(0, streak // 7)  # 每7天给1个保护盾
        return {
            "streak": streak,
            "shields_available": shields,
            "loss_if_broken": {
                "streak_days": streak,
                "xp_loss": streak * 10,
                "message": f"如果今天不学习，你将失去 {streak} 天连胜和 {streak * 10} XP!"
            },
            "next_shield_in_days": max(0, 7 - (streak % 7)),
        }

    @staticmethod
    def get_sunk_cost_reminder(total_minutes: float, total_days: int) -> Dict[str, Any]:
        """沉没成本提醒"""
        return {
            "total_time_invested": {
                "minutes": round(total_minutes, 1),
                "hours": round(total_minutes / 60, 1),
                "days": total_days,
            },
            "message": f"你已经投入了 {round(total_minutes/60, 1)} 小时学习，坚持就是胜利！",
            "milestone": {
                "next": f"距离下一个里程碑还有 {max(0, 10 - (total_days % 10))} 天",
            }
        }


class FreshStartEngine:
    """新起点效应引擎

    原理：人们在时间地标（周一、月初、新学期）时更有动力改变行为。
    利用"重新开始"心理推动学习。

    功能：
    - 每周一/每月1日重置小目标
    - "新的一周，新的开始"激励
    - 周期总结与展望
    """

    FRESH_START_LANDMARKS = {
        "monday": {"label": "周一新起点", "message": "新的一周开始！本周目标：完成20道题"},
        "month_start": {"label": "月初新起点", "message": "新的一个月！月度挑战已重置"},
        "quarter_start": {"label": "季度新起点", "message": "新季度新挑战！排行榜已刷新"},
    }

    @staticmethod
    def check_fresh_start(today: Optional[datetime] = None) -> Dict[str, Any]:
        """检查今天是否是新起点日"""
        dt = today or datetime.now(UTC)
        triggers = []
        
        # 周一检测（weekday(): 周一=0）
        if dt.weekday() == 0:
            triggers.append(FreshStartEngine.FRESH_START_LANDMARKS["monday"])
        
        # 月初检测
        if dt.day == 1:
            triggers.append(FreshStartEngine.FRESH_START_LANDMARKS["month_start"])
        
        # 季度初检测
        if dt.day == 1 and dt.month in (1, 4, 7, 10):
            triggers.append(FreshStartEngine.FRESH_START_LANDMARKS["quarter_start"])

        return {
            "is_fresh_start": len(triggers) > 0,
            "triggers": triggers,
            "bonus_xp": len(triggers) * 25,
            "message": triggers[0]["message"] if triggers else "继续加油！",
        }

    @staticmethod
    def get_weekly_reset(weekly_goals: Dict[str, int]) -> Dict[str, Any]:
        """获取每周重置信息"""
        return {
            "last_week": weekly_goals,
            "this_week_goals": {
                "tasks_target": 20,
                "streak_keep": True,
                "bonus_available": True,
            },
            "message": "本周目标已重置！完成20题可获得额外奖励",
        }


class ZeigarnikEngine:
    """蔡格尼克效应引擎

    原理：未完成的任务比已完成的任务更容易被记住。
    利用这种心理张力驱动用户回来完成学习。

    功能：
    - 未完成题目提醒
    - 半途而废的课程章节
    - "还有X题未完成"提示
    """

    @staticmethod
    def get_incomplete_reminder(incomplete_tasks: list, incomplete_chapters: list) -> Dict[str, Any]:
        """获取未完成任务提醒"""
        return {
            "incomplete_tasks_count": len(incomplete_tasks),
            "incomplete_chapters_count": len(incomplete_chapters),
            "urgent_task": incomplete_tasks[0] if incomplete_tasks else None,
            "message": (
                f"你还有 {len(incomplete_tasks)} 道未完成的题目和 {len(incomplete_chapters)} 个进行中的章节，"
                f"完成它们可以获得认知闭合的满足感！"
            ) if incomplete_tasks else "所有任务已完成！太棒了！",
            "closure_bonus": len(incomplete_tasks) * 5,  # 完成所有未完成任务的额外奖励
        }

    @staticmethod
    def get_progress_bar(completed: int, total: int) -> Dict[str, Any]:
        """获取进度条信息（利用接近完成的张力）"""
        if total == 0:
            return {"percentage": 0, "message": "开始你的第一条学习吧！"}
        
        pct = round(completed / total * 100, 1)
        remaining = total - completed
        
        if pct >= 80:
            message = f"只剩 {remaining} 题就完成了！再加把劲！💪"
            bonus = remaining * 3
        elif pct >= 50:
            message = f"已完成一半！还有 {remaining} 题"
            bonus = 0
        else:
            message = f"已完成 {pct}%，继续加油！"
            bonus = 0
        
        return {
            "percentage": pct,
            "completed": completed,
            "total": total,
            "remaining": remaining,
            "message": message,
            "completion_bonus": bonus,
        }


class PeakEndRuleEngine:
    """峰终定律引擎

    原理：人们对体验的评价主要取决于体验峰值和结束时的感受。
    在学习中，确保每次会话的高峰时刻和结尾都有积极体验。

    功能：
    - 学习结束时给予特别正面的反馈
    - 记录学习高峰时刻（最快答题、最高连对等）
    - 会话总结突出亮点
    """

    @staticmethod
    def generate_session_end_summary(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成会话结束总结（突出峰终体验）"""
        best_speed = session_data.get("fastest_answer_seconds", 0)
        best_streak = session_data.get("max_correct_streak", 0)
        
        highlights = []
        if best_speed > 0 and best_speed < 30:
            highlights.append(f"最快答题仅用 {best_speed} 秒！闪电般的速度⚡")
        if best_streak >= 5:
            highlights.append(f"最高连续答对 {best_streak} 题！势不可挡🔥")
        
        return {
            "peak_moments": highlights,
            "end_message": random.choice([
                "今天的学习非常出色！带着成就感结束吧🌟",
                "你的大脑正在形成新的神经连接！明天见🧠",
                "每一次学习都在让你变得更强大！💪",
            ]),
            "total_xp_earned": session_data.get("xp_earned", 0),
            "peak_xp_bonus": len(highlights) * 10,
        }


class SurpriseDelightEngine:
    """惊喜彩蛋引擎

    原理：不可预测的奖励比可预测的奖励更能激活多巴胺系统。

    功能：
    - 随机彩蛋奖励（1/20概率触发）
    - 学习里程碑惊喜
    - 隐藏成就解锁
    """

    HIDDEN_ACHIEVEMENTS = [
        {"id": "night_owl", "name": "夜猫子", "desc": "在22点后完成学习", "xp": 100},
        {"id": "early_bird", "name": "早起的鸟儿", "desc": "在6点前开始学习", "xp": 100},
        {"id": "perfect_10", "name": "十全十美", "desc": "连续答对10题", "xp": 200},
        {"id": "speed_demon", "name": "闪电侠", "desc": "10秒内答对一题", "xp": 150},
        {"id": "comeback", "name": "王者归来", "desc": "答错后连续答对5题", "xp": 120},
    ]

    @staticmethod
    def roll_surprise() -> Dict[str, Any]:
        """随机触发惊喜（1/20概率）"""
        triggered = random.random() < 0.05  # 5% 概率
        if not triggered:
            return {"triggered": False}
        
        surprise = random.choice([
            {"type": "double_xp", "message": "🎉 双倍 XP！本次学习获得双倍经验！", "multiplier": 2},
            {"type": "bonus_xp", "message": "🌟 彩蛋！获得 50 额外 XP！", "bonus_xp": 50},
            {"type": "free_shield", "message": "🛡️ 幸运！获得1个连胜保护盾！", "free_shield": 1},
            {"type": "pet_treat", "message": "🍖 你的宠物获得一份零食！心情+20", "pet_mood_boost": 20},
        ])
        return {"triggered": True, **surprise}

    @staticmethod
    def check_achievements(user_stats: Dict[str, Any]) -> list:
        """检查隐藏成就"""
        unlocked = []
        hour = datetime.now(UTC).hour
        
        for ach in SurpriseDelightEngine.HIDDEN_ACHIEVEMENTS:
            if ach["id"] == "night_owl" and hour >= 22:
                unlocked.append(ach)
            elif ach["id"] == "early_bird" and hour <= 6:
                unlocked.append(ach)
            elif ach["id"] == "perfect_10" and user_stats.get("current_streak", 0) >= 10:
                unlocked.append(ach)
            elif ach["id"] == "speed_demon" and user_stats.get("fastest_answer", 999) <= 10:
                unlocked.append(ach)
        
        return unlocked
