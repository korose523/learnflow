"""AI 教师助手引擎 — 智能学生分析与建议

功能:
1. 学习进度全景视图 — 班级+个人掌握度热力图
2. 智能难度调节 — 一键调整单个/批量学生难度
3. AI 学习分析 — 自动识别需要关注的学生
4. 干预建议生成 — 具体可操作的教学建议
5. 预警通知 — 自动生成教师可读的学生状态报告

设计原则:
  教师不是数据的消费者，而是教学决策的制定者。
  AI 提供建议，教师保留最终决定权。
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class StudentAnalysisReport:
    """单个学生的AI分析报告"""
    student_id: str
    student_name: str
    grade: str

    # 能力概览
    overall_mastery: float          # 0-1
    mastery_trend: str              # improving/stable/declining
    strongest_skill: str
    weakest_skill: str

    # 行为分析
    current_streak: int
    weekly_attempts: int
    avg_difficulty: float
    skip_ratio: float
    help_others_count: int

    # 风险标记
    risk_level: str                 # green/yellow/red
    risk_reasons: List[str]
    needs_attention: bool

    # 成瘾引擎数据
    engagement_score: float         # 0-1, 综合参与度
    addiction_stage: str            # exploring/forming/hooked/automated
    hook_loops_completed: int
    identity_labels: List[str]

    # AI 建议
    recommended_action: str
    suggested_difficulty: int
    suggested_difficulty_reason: str
    personalized_tip: str


@dataclass
class ClassAnalysisReport:
    """班级分析报告"""
    total_students: int
    active_students: int
    avg_mastery: float
    mastery_distribution: Dict[str, int]  # mastered/proficient/developing/beginner/novice

    # 班级动态
    most_improving_student: Optional[str]
    most_concerning_student: Optional[str]
    most_engaged_student: Optional[str]

    # 知识点热力
    topic_heatmap: List[dict]       # [{topic, avg_mastery, difficulty_coverage}]
    difficulty_distribution: Dict[int, int]  # {difficulty: count}

    # 时间分析
    most_active_hour: str
    weekend_vs_weekday_ratio: float

    # AI 教学建议
    class_wide_suggestions: List[str]
    group_suggestions: List[dict]   # [{group: "struggling_with_X", students: [...], action: ...}]


# module-level helper
def max_risk(a: str, b: str) -> str:
    order = {"green": 0, "yellow": 1, "red": 2}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def _count_consecutive_fails(results: List[bool]) -> int:
    """统计连续失败次数（从最新结果开始）"""
    count = 0
    for r in reversed(results):
        if not r:
            count += 1
        else:
            break
    return count


class TeacherAIAssistant:
    """AI 教师助手

    基于所有现有引擎的综合分析。
    """

    # ─── 1. 学生个体分析 ──────────────────────

    @classmethod
    def analyze_student(cls, student: dict, stats: dict,
                         bkt_state: dict = None) -> StudentAnalysisReport:
        """生成单个学生的 AI 分析报告"""
        from app.services.knowledge_tracing import BKTEngine

        # 能力分析
        overall_mastery = stats.get("avg_mastery", 0.5)
        trend = cls._detect_trend(stats.get("recent_accuracy", []))
        stats["recent_trend"] = trend  # 注入趋势，供后续风险评估使用

        # 最强/最弱技能
        skill_scores = stats.get("skill_scores", {})
        if skill_scores:
            strongest = max(skill_scores, key=skill_scores.get)
            weakest = min(skill_scores, key=skill_scores.get)
        else:
            strongest = "暂无数据"
            weakest = "暂无数据"

        # 风险标记
        risk, risk_reasons = cls._assess_risk(stats)
        needs_attention = risk in ("yellow", "red")

        # 成瘾数据
        engagement = cls._calculate_engagement(stats)
        addiction_stage = cls._assess_addiction_stage(stats)

        # 身份标签
        identities = stats.get("identity_labels", [])
        if not identities:
            identities = ["初学者"]

        # AI 建议
        action, difficulty, diff_reason, tip = cls._generate_recommendation(
            overall_mastery, trend, risk, stats)

        return StudentAnalysisReport(
            student_id=student.get("id", ""),
            student_name=student.get("name", ""),
            grade=student.get("grade", ""),
            overall_mastery=overall_mastery,
            mastery_trend=trend,
            strongest_skill=strongest,
            weakest_skill=weakest,
            current_streak=stats.get("current_streak", 0),
            weekly_attempts=stats.get("weekly_attempts", 0),
            avg_difficulty=stats.get("avg_difficulty", 5),
            skip_ratio=stats.get("skip_ratio", 0),
            help_others_count=stats.get("help_others", 0),
            risk_level=risk,
            risk_reasons=risk_reasons,
            needs_attention=needs_attention,
            engagement_score=engagement,
            addiction_stage=addiction_stage,
            hook_loops_completed=stats.get("hook_loops", 0),
            identity_labels=identities,
            recommended_action=action,
            suggested_difficulty=difficulty,
            suggested_difficulty_reason=diff_reason,
            personalized_tip=tip,
        )

    # ─── 2. 班级全景分析 ──────────────────────

    @classmethod
    def analyze_classroom(cls, students: List[dict],
                           class_stats: dict) -> ClassAnalysisReport:
        """生成班级 AI 分析报告"""
        topics = class_stats.get("topic_mastery", {})
        topic_heatmap = [
            {"topic": t, "avg_mastery": round(m, 2),
             "difficulty_coverage": class_stats.get("topic_difficulty", {}).get(t, [])}
            for t, m in topics.items()
        ]

        # 分布统计
        distribution = {"mastered": 0, "proficient": 0, "developing": 0, "beginner": 0, "novice": 0}
        for s in students:
            m = s.get("overall_mastery", 0.5)
            if m >= 0.85: distribution["mastered"] += 1
            elif m >= 0.65: distribution["proficient"] += 1
            elif m >= 0.40: distribution["developing"] += 1
            elif m >= 0.20: distribution["beginner"] += 1
            else: distribution["novice"] += 1

        # 建议
        class_suggestions = cls._generate_class_suggestions(distribution, topic_heatmap)
        group_suggestions = cls._generate_group_suggestions(students, topic_heatmap)

        # 极端值
        if students:
            most_improving = max(students, key=lambda s: s.get("trend_score", 0))
            most_concerning = min(students, key=lambda s: s.get("overall_mastery", 1))
            most_engaged = max(students, key=lambda s: s.get("hook_loops", 0))
        else:
            most_improving = most_concerning = most_engaged = None

        return ClassAnalysisReport(
            total_students=class_stats.get("total_students", 0),
            active_students=class_stats.get("active_today", 0),
            avg_mastery=class_stats.get("class_avg_mastery", 0.5),
            mastery_distribution=distribution,
            most_improving_student=most_improving.get("name") if most_improving else None,
            most_concerning_student=most_concerning.get("name") if most_concerning else None,
            most_engaged_student=most_engaged.get("name") if most_engaged else None,
            topic_heatmap=topic_heatmap,
            difficulty_distribution=class_stats.get("difficulty_distribution", {}),
            most_active_hour=class_stats.get("most_active_hour", "19:00"),
            weekend_vs_weekday_ratio=class_stats.get("weekend_ratio", 0.3),
            class_wide_suggestions=class_suggestions,
            group_suggestions=group_suggestions,
        )

    # ─── 3. 智能难度调节 ──────────────────────

    @classmethod
    def suggest_difficulty_adjustment(cls, student_id: str,
                                       current_difficulty: int,
                                       bkt_mastery: float,
                                       recent_accuracy: float) -> dict:
        """建议难度调整

        Returns:
            {suggested_difficulty, reason, confidence, teacher_can_override}
        """
        # BKT 驱动的难度建议
        if bkt_mastery > 0.85 and recent_accuracy > 0.85:
            new_diff = min(10, current_difficulty + 2)
            reason = f"BKT掌握度 {bkt_mastery:.0%}，最近正确率{recent_accuracy:.0%}——太简单了"
            confidence = 0.9
        elif bkt_mastery > 0.7 and recent_accuracy > 0.8:
            new_diff = min(10, current_difficulty + 1)
            reason = f"掌握度良好，可以适度挑战"
            confidence = 0.7
        elif bkt_mastery < 0.3 or recent_accuracy < 0.4:
            new_diff = max(1, current_difficulty - 2)
            reason = f"BKT掌握度 {bkt_mastery:.0%}，最近正确率 {recent_accuracy:.0%}——需要巩固基础"
            confidence = 0.85
        elif bkt_mastery < 0.5 and recent_accuracy < 0.5:
            new_diff = max(1, current_difficulty - 1)
            reason = "掌握度偏低，降低难度让学生重建信心"
            confidence = 0.6
        else:
            new_diff = current_difficulty
            reason = "当前难度适中，维持心流状态"
            confidence = 0.5

        return {
            "student_id": student_id,
            "current_difficulty": current_difficulty,
            "suggested_difficulty": new_diff,
            "reason": reason,
            "confidence": confidence,
            "teacher_can_override": True,
            "auto_apply": confidence > 0.8,
        }

    @classmethod
    def batch_adjust_difficulty(cls, students: List[dict]) -> List[dict]:
        """批量难度建议 — 一键调整全班"""
        suggestions = []
        for s in students:
            suggestion = cls.suggest_difficulty_adjustment(
                s.get("id", ""),
                s.get("current_difficulty", 5),
                s.get("bkt_mastery", 0.5),
                s.get("recent_accuracy", 0.5),
            )
            suggestions.append(suggestion)
        return suggestions

    # ─── 辅助方法 ──────────────────────────

    @staticmethod
    def _count_consecutive_fails(results: List[bool]) -> int:
        """调用顶层函数统计连续失败次数"""
        return _count_consecutive_fails(results)

    @staticmethod
    def _detect_trend(recent_accuracy: List[float]) -> str:
        if not recent_accuracy or len(recent_accuracy) < 2:
            return "stable"
        # 简单线性趋势
        x = list(range(len(recent_accuracy)))
        n = len(x)
        if n < 2:
            return "stable"
        slope = (n * sum(i * a for i, a in zip(x, recent_accuracy)) -
                 sum(x) * sum(recent_accuracy)) / max(n * sum(i*i for i in x) - sum(x)**2, 1)
        if slope > 0.02: return "improving"
        elif slope < -0.02: return "declining"
        return "stable"

    @staticmethod
    def _assess_risk(stats: dict) -> Tuple[str, List[str]]:
        reasons = []
        risk = "green"

        # 按严重程度从高到低检查
        if stats.get("consecutive_failures", 0) >= 5:
            reasons.append("连续错误超过5题")
            risk = "red"

        if stats.get("recent_trend") == "declining":
            reasons.append("近期掌握度下降")
            risk = "red" if risk != "red" else "red"

        if stats.get("skip_ratio", 0) > 0.4:
            reasons.append("跳过率偏高")
            risk = max_risk(risk, "yellow")

        if stats.get("weekly_attempts", 100) < 5:
            reasons.append("本周做题数偏低")
            risk = max_risk(risk, "yellow")

        if stats.get("avg_difficulty", 5) < 3 and stats.get("total_attempts", 0) > 20:
            reasons.append("持续选择低难度，可能回避挑战")
            risk = max_risk(risk, "yellow")

        if stats.get("hook_loops", 0) == 0 and stats.get("total_attempts", 0) > 50:
            reasons.append("参与度下降（Hook循环不活跃）")
            risk = max_risk(risk, "yellow")

        return risk, reasons

    @staticmethod
    def _calculate_engagement(stats: dict) -> float:
        score = 0.0
        if stats.get("current_streak", 0) >= 7: score += 0.3
        elif stats.get("current_streak", 0) >= 3: score += 0.15
        if stats.get("weekly_attempts", 0) >= 30: score += 0.25
        elif stats.get("weekly_attempts", 0) >= 10: score += 0.1
        if stats.get("hook_loops", 0) >= 20: score += 0.25
        elif stats.get("hook_loops", 0) >= 5: score += 0.1
        if stats.get("help_others", 0) > 0: score += 0.1
        if stats.get("identity_count", 0) >= 3: score += 0.1
        return min(1.0, score)

    @staticmethod
    def _assess_addiction_stage(stats: dict) -> str:
        loops = stats.get("hook_loops", 0)
        streak = stats.get("current_streak", 0)
        if streak >= 30 and loops >= 100: return "automated"
        elif streak >= 7 and loops >= 30: return "hooked"
        elif streak >= 3 and loops >= 5: return "forming"
        return "exploring"

    @staticmethod
    def _generate_recommendation(mastery, trend, risk, stats) -> Tuple[str, int, str, str]:
        suggested_diff = max(1, min(10, int(mastery * 10) + 1))

        if risk == "red":
            action = "intervention"
            suggested_diff = max(1, suggested_diff - 2)
            reason = "学生需要紧急教学干预，建议降低难度并安排一对一辅导"
            tip = "与该学生进行一次简短的交流，了解学习困难的具体原因。"
        elif risk == "yellow":
            action = "monitor"
            reason = "学生需要更多关注，建议保持当前难度但增加鼓励"
            tip = "下次上课时给该学生一个正向反馈，认可ta的努力。"
        elif trend == "improving":
            action = "challenge"
            suggested_diff = min(10, suggested_diff + 1)
            reason = "学生正在进步，可以适当增加挑战"
            tip = "推荐一道挑战题给该学生，并在完成后公开表扬。"
        else:
            action = "maintain"
            reason = "维持当前心流状态"
            tip = "该学生状态稳定，保持关注即可。"

        return action, suggested_diff, reason, tip

    @staticmethod
    def _generate_class_suggestions(distribution: dict,
                                     heatmap: List[dict]) -> List[str]:
        suggestions = []
        weak_pct = (distribution.get("beginner", 0) + distribution.get("novice", 0))
        total = sum(distribution.values()) or 1
        if weak_pct / total > 0.3:
            suggestions.append("班级有>30%学生基础薄弱，建议安排基础巩固课。")
        if distribution.get("mastered", 0) / total > 0.5:
            suggestions.append("班级超过半数学生掌握良好，可以考虑引入拓展内容。")

        # 知识点薄弱环节
        weak_topics = [h for h in heatmap if h["avg_mastery"] < 0.4]
        if weak_topics:
            names = ", ".join(h["topic"] for h in weak_topics[:3])
            suggestions.append(f"知识点薄弱: {names}。建议安排专题复习。")

        if not suggestions:
            suggestions = ["班级整体状态良好，继续保持当前节奏。"]

        return suggestions

    @staticmethod
    def _generate_group_suggestions(students: List[dict],
                                     heatmap: List[dict]) -> List[dict]:
        """生成分组建议"""
        groups = []

        # 按掌握度分组
        struggling = [s for s in students if s.get("overall_mastery", 0.5) < 0.4]
        advanced = [s for s in students if s.get("overall_mastery", 0.5) > 0.8]
        disengaged = [s for s in students if s.get("hook_loops", 0) < 3 and s.get("total_attempts", 0) > 20]

        if struggling:
            groups.append({
                "group": "struggling",
                "label": "需要更多支持",
                "student_count": len(struggling),
                "student_names": [s.get("name", "") for s in struggling[:5]],
                "action": "建议为这些学生安排基础巩固课或一对一辅导。",
                "suggested_difficulty_adjustment": -2,
            })

        if advanced:
            groups.append({
                "group": "advanced",
                "label": "学有余力",
                "student_count": len(advanced),
                "student_names": [s.get("name", "") for s in advanced[:5]],
                "action": "建议为这些学生提供拓展挑战题。",
                "suggested_difficulty_adjustment": +2,
            })

        if disengaged:
            groups.append({
                "group": "disengaged",
                "label": "参与度偏低",
                "student_count": len(disengaged),
                "student_names": [s.get("name", "") for s in disengaged[:5]],
                "action": "建议与这些学生交流，了解学习兴趣和困难。",
                "suggested_difficulty_adjustment": -1,
            })

        return groups
