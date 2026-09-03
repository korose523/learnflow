"""间隔复习服务 (Spaced Repetition)

基于艾宾浩斯遗忘曲线的简化实现。
- 答对：延长复习间隔（×2.5）
- 答错：缩短复习间隔（÷2）
- 最小间隔：1天，最大间隔：180天
"""
import math
from datetime import datetime, timedelta, UTC
from typing import Optional


class SpacedRepetitionService:
    """间隔复习算法

    标准间隔序列（天）：1, 3, 7, 16, 35, 70, 140, 280
    """

    BASE_INTERVALS = [1, 3, 7, 16, 35, 70, 140, 280]

    @classmethod
    def calculate_next_review(
        cls,
        review_number: int,
        was_correct: bool,
        current_interval: Optional[float] = None,
    ) -> dict:
        """计算下次复习时间和间隔

        Args:
            review_number: 当前是第几次复习 (从0开始)
            was_correct: 本次复习是否答对
            current_interval: 当前间隔天数（如果有的话）

        Returns:
            dict: {
                "next_review_date": datetime,
                "next_interval_days": float,
                "review_number": int,
            }
        """
        if was_correct:
            # 答对 → 用标准间隔或 ×2.5
            if review_number < len(cls.BASE_INTERVALS):
                next_interval = cls.BASE_INTERVALS[review_number]
            else:
                next_interval = current_interval * 2.5 if current_interval else 180
        else:
            # 答错 → 回退到较短间隔
            if current_interval and current_interval > 1:
                next_interval = max(1, current_interval / 2)
            else:
                next_interval = 1
            # 复习编号回退（但不低于1）
            review_number = max(0, review_number - 1)

        next_interval = min(180, max(1, next_interval))
        next_review_date = datetime.now(UTC) + timedelta(days=next_interval)
        next_review_number = review_number + 1 if was_correct else max(1, review_number)

        return {
            "next_review_date": next_review_date,
            "next_interval_days": next_interval,
            "next_review_number": next_review_number,
        }

    @classmethod
    def get_due_reviews(cls, reviews: list, now: Optional[datetime] = None) -> list:
        """获取所有到期需要复习的项目"""
        if now is None:
            now = datetime.now(UTC)
        # SQLite 存储的是 naive datetime，统一去掉时区信息再比较
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        return [
            r for r in reviews
            if r.scheduled_date and r.scheduled_date <= now and not r.completed_date
        ]

    @classmethod
    def estimate_mastery(cls, review_number: int, was_correct: bool) -> float:
        """估算掌握度 (0-1)

        基于复习次数和最近正确性
        """
        if review_number == 0:
            return 0.0
        base = min(1.0, review_number / 5)  # 5次复习 = 基本掌握
        if was_correct:
            base = min(1.0, base + 0.15)
        else:
            base = max(0.0, base - 0.1)
        return base
