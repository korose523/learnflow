"""学习成瘾化指数（Learning Addiction Index, LAI）

基于论文第十章系统优化清单第6项：建立'学习成瘾化指数'仪表盘，
将RRMS风险评分升级为综合性的LAI，作为系统自适应调节的核心输入。

LAI 五维度测量框架（论文第十一章11.1节）：
1. 时间投入维度 (30%) - 每日学习时长、单次会话时长、夜间学习比例
2. 动机结构维度 (25%) - 内外在动机比例、外在奖励依赖度、停止后情绪反应
3. 行为控制维度 (25%) - 能否按计划停止、反复减少失败、隐瞒使用时间
4. 认知维度 (10%) - 内容关注度vs社交关注度、时间感知偏差、身份内部化
5. 功能影响维度 (10%) - 睡眠、运动、社交、其他学业影响

LAI 评分：0-100，越高越健康（0=深度成瘾，100=完全健康）
风险等级：L1(80-100 正常) / L2(50-79 关注) / L3(20-49 深度) / L4(0-19 病理)
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import IntEnum
from typing import Optional
from collections import deque


class LAIRiskTier(IntEnum):
    """LAI 风险等级（对应论文 RRMS 四层模型）"""
    L1_NORMAL = 1       # 80-100 正常动机层
    L2_WATCH = 2        # 50-79 投入关注层
    L3_DEEP = 3         # 20-49 深度成瘾层
    L4_PATHOLOGICAL = 4  # 0-19 病理成瘾层


@dataclass
class LAIDimensionScore:
    """单维度评分"""
    dimension: str
    raw_score: float       # 0-1 原始分
    weighted_score: float  # 加权后分值
    sub_indicators: dict   # 子指标明细
    risk_flag: bool = False  # 是否触发风险标记


@dataclass
class LAIAssessment:
    """LAI 综合评估结果"""
    overall_score: float                      # 0-100
    risk_tier: LAIRiskTier
    dimensions: dict                          # {dimension_name: LAIDimensionScore}
    recommendations: list = field(default_factory=list)
    should_reduce_gamification: bool = False   # 是否应降低游戏化强度
    should_notify_guardian: bool = False        # 是否应通知家长
    should_force_break: bool = False            # 是否应强制休息
    autonomy_support_boost: bool = False        # 是否应增强自主性支持
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "risk_tier": self.risk_tier.name,
            "risk_tier_value": int(self.risk_tier),
            "dimensions": {
                name: {
                    "raw_score": round(d.raw_score, 3),
                    "weighted_score": round(d.weighted_score, 1),
                    "sub_indicators": d.sub_indicators,
                    "risk_flag": d.risk_flag,
                }
                for name, d in self.dimensions.items()
            },
            "recommendations": self.recommendations,
            "should_reduce_gamification": self.should_reduce_gamification,
            "should_notify_guardian": self.should_notify_guardian,
            "should_force_break": self.should_force_break,
            "autonomy_support_boost": self.autonomy_support_boost,
            "timestamp": self.timestamp.isoformat(),
        }


class LearningAddictionIndex:
    """学习成瘾化指数计算引擎

    将五维度测量框架转化为可操作的评分系统。
    分数越高越健康（0=成瘾，100=健康）。
    """

    # 维度权重（论文第十一章11.1节）
    WEIGHTS = {
        "time": 0.30,       # 时间投入维度
        "motivation": 0.25,  # 动机结构维度
        "control": 0.25,     # 行为控制维度
        "cognition": 0.10,   # 认知维度
        "function": 0.10,    # 功能影响维度
    }

    # 动态阈值基线（根据年龄/学段调整）
    DEFAULT_THRESHOLDS = {
        "daily_minutes_yellow": 90,    # 日学习时长关注阈值
        "daily_minutes_red": 150,      # 日学习时长红线
        "session_minutes_yellow": 45,
        "session_minutes_red": 75,
        "night_ratio_yellow": 0.10,
        "night_ratio_red": 0.20,
        "content_attention_ratio_yellow": 0.60,  # 内容页停留占比
        "leaderboard_view_limit": 10,             # 排行榜日查看次数
        "planned_stop_failure_limit": 2,          # 计划停止失败次数/周
    }

    @classmethod
    def assess(
        cls,
        daily_minutes: float = 0.0,
        session_minutes: float = 0.0,
        night_ratio: float = 0.0,
        content_attention_ratio: float = 1.0,
        leaderboard_views: int = 0,
        planned_stop_failures: int = 0,
        intrinsic_motivation_ratio: float = 0.7,
        external_reward_dependency: float = 0.3,
        time_perception_bias: float = 0.0,
        sleep_impact: float = 0.0,
        social_impact: float = 0.0,
        age_group: str = "secondary",  # primary/secondary/senior
        thresholds: Optional[dict] = None,
    ) -> LAIAssessment:
        """计算 LAI 综合指数

        Args:
            daily_minutes: 当日学习总时长（分钟）
            session_minutes: 平均单次会话时长（分钟）
            night_ratio: 夜间学习占比 (0-1)
            content_attention_ratio: 学习内容页停留时间占比 (0-1)
            leaderboard_views: 当日排行榜查看次数
            planned_stop_failures: 本周计划停止失败次数
            intrinsic_motivation_ratio: 内在动机占比 (0-1)
            external_reward_dependency: 外在奖励依赖度 (0-1)
            time_perception_bias: 时间感知偏差 (0-1，0=无偏差)
            sleep_impact: 睡眠影响程度 (0-1，0=无影响)
            social_impact: 社交影响程度 (0-1，0=无影响)
            age_group: 年龄段 (primary=小学/secondary=初中/senior=高中)
            thresholds: 自定义阈值覆盖

        Returns:
            LAIAssessment: 综合评估结果
        """
        t = {**cls.DEFAULT_THRESHOLDS}
        if thresholds:
            t.update(thresholds)

        # 按年龄调整阈值
        if age_group == "primary":
            t["daily_minutes_yellow"] = 60
            t["daily_minutes_red"] = 90
        elif age_group == "senior":
            t["daily_minutes_yellow"] = 120
            t["daily_minutes_red"] = 180

        # ── 维度1: 时间投入 (30%) ──
        time_score, time_subs = cls._score_time_dimension(
            daily_minutes, session_minutes, night_ratio, t
        )

        # ── 维度2: 动机结构 (25%) ──
        motiv_score, motiv_subs = cls._score_motivation_dimension(
            intrinsic_motivation_ratio, external_reward_dependency
        )

        # ── 维度3: 行为控制 (25%) ──
        control_score, control_subs = cls._score_control_dimension(
            planned_stop_failures, t
        )

        # ── 维度4: 认知 (10%) ──
        cogn_score, cogn_subs = cls._score_cognition_dimension(
            content_attention_ratio, leaderboard_views, time_perception_bias, t
        )

        # ── 维度5: 功能影响 (10%) ──
        func_score, func_subs = cls._score_function_dimension(
            sleep_impact, social_impact
        )

        # 综合评分（0-100，越高越健康）
        dimensions = {
            "time": LAIDimensionScore("time", time_score, time_score * 100 * cls.WEIGHTS["time"], time_subs, time_score < 0.4),
            "motivation": LAIDimensionScore("motivation", motiv_score, motiv_score * 100 * cls.WEIGHTS["motivation"], motiv_subs, motiv_score < 0.4),
            "control": LAIDimensionScore("control", control_score, control_score * 100 * cls.WEIGHTS["control"], control_subs, control_score < 0.4),
            "cognition": LAIDimensionScore("cognition", cogn_score, cogn_score * 100 * cls.WEIGHTS["cognition"], cogn_subs, cogn_score < 0.4),
            "function": LAIDimensionScore("function", func_score, func_score * 100 * cls.WEIGHTS["function"], func_subs, func_score < 0.4),
        }

        weighted_sum = sum(d.weighted_score for d in dimensions.values())
        overall = weighted_sum  # 已经是 0-100 范围

        # 确定风险等级
        if overall >= 80:
            tier = LAIRiskTier.L1_NORMAL
        elif overall >= 50:
            tier = LAIRiskTier.L2_WATCH
        elif overall >= 20:
            tier = LAIRiskTier.L3_DEEP
        else:
            tier = LAIRiskTier.L4_PATHOLOGICAL

        # 生成建议和干预标志
        recommendations = cls._generate_recommendations(dimensions, tier, age_group)
        should_reduce = tier >= LAIRiskTier.L2_WATCH and (dimensions["time"].risk_flag or dimensions["motivation"].risk_flag)
        should_notify = tier >= LAIRiskTier.L3_DEEP
        should_break = dimensions["time"].risk_flag and session_minutes > t["session_minutes_red"]
        autonomy_boost = tier >= LAIRiskTier.L2_WATCH  # 联动自主性支持引擎

        return LAIAssessment(
            overall_score=overall,
            risk_tier=tier,
            dimensions=dimensions,
            recommendations=recommendations,
            should_reduce_gamification=should_reduce,
            should_notify_guardian=should_notify,
            should_force_break=should_break,
            autonomy_support_boost=autonomy_boost,
        )

    @staticmethod
    def _score_time_dimension(daily_min, session_min, night_ratio, t):
        """时间维度评分：越高越健康"""
        subs = {}
        # 日学习时长（超过红线=0分，在yellow以下=1分，线性插值）
        if daily_min <= t["daily_minutes_yellow"]:
            daily_score = 1.0
        elif daily_min >= t["daily_minutes_red"]:
            daily_score = 0.0
        else:
            daily_score = 1.0 - (daily_min - t["daily_minutes_yellow"]) / (t["daily_minutes_red"] - t["daily_minutes_yellow"])
        subs["daily_minutes"] = {"value": daily_min, "score": round(daily_score, 3)}

        # 单次会话时长
        if session_min <= t["session_minutes_yellow"]:
            session_score = 1.0
        elif session_min >= t["session_minutes_red"]:
            session_score = 0.0
        else:
            session_score = 1.0 - (session_min - t["session_minutes_yellow"]) / (t["session_minutes_red"] - t["session_minutes_yellow"])
        subs["session_minutes"] = {"value": session_min, "score": round(session_score, 3)}

        # 夜间占比
        if night_ratio <= t["night_ratio_yellow"]:
            night_score = 1.0
        elif night_ratio >= t["night_ratio_red"]:
            night_score = 0.0
        else:
            night_score = 1.0 - (night_ratio - t["night_ratio_yellow"]) / (t["night_ratio_red"] - t["night_ratio_yellow"])
        subs["night_ratio"] = {"value": night_ratio, "score": round(night_score, 3)}

        avg = (daily_score + session_score + night_score) / 3
        return avg, subs

    @staticmethod
    def _score_motivation_dimension(intrinsic_ratio, external_dep):
        """动机结构评分：内在动机占比越高越健康"""
        subs = {}
        # 内在动机占比（>0.7=1分，<0.3=0分）
        motiv_score = max(0, min(1, (intrinsic_ratio - 0.3) / 0.4))
        subs["intrinsic_ratio"] = {"value": intrinsic_ratio, "score": round(motiv_score, 3)}

        # 外在奖励依赖度（越低越健康）
        dep_score = 1.0 - external_dep
        subs["external_dependency"] = {"value": external_dep, "score": round(dep_score, 3)}

        avg = (motiv_score + dep_score) / 2
        return avg, subs

    @staticmethod
    def _score_control_dimension(planned_stop_failures, t):
        """行为控制维度：计划停止失败次数越少越健康"""
        subs = {}
        limit = t["planned_stop_failure_limit"]
        if planned_stop_failures == 0:
            control_score = 1.0
        elif planned_stop_failures >= limit * 2:
            control_score = 0.0
        else:
            control_score = 1.0 - planned_stop_failures / (limit * 2)
        subs["planned_stop_failures"] = {"value": planned_stop_failures, "score": round(control_score, 3)}
        return control_score, subs

    @staticmethod
    def _score_cognition_dimension(content_ratio, leaderboard_views, time_bias, t):
        """认知维度"""
        subs = {}
        # 内容关注度
        content_score = max(0, min(1, (content_ratio - 0.3) / 0.4))
        subs["content_attention"] = {"value": content_ratio, "score": round(content_score, 3)}

        # 排行榜查看频率
        lb_limit = t["leaderboard_view_limit"]
        if leaderboard_views <= lb_limit / 2:
            lb_score = 1.0
        elif leaderboard_views >= lb_limit * 2:
            lb_score = 0.0
        else:
            lb_score = 1.0 - (leaderboard_views - lb_limit / 2) / (lb_limit * 1.5)
        subs["leaderboard_views"] = {"value": leaderboard_views, "score": round(lb_score, 3)}

        # 时间感知偏差
        bias_score = 1.0 - time_bias
        subs["time_perception_bias"] = {"value": time_bias, "score": round(bias_score, 3)}

        avg = (content_score + lb_score + bias_score) / 3
        return avg, subs

    @staticmethod
    def _score_function_dimension(sleep_impact, social_impact):
        """功能影响维度：影响越小越健康"""
        subs = {}
        sleep_score = 1.0 - sleep_impact
        social_score = 1.0 - social_impact
        subs["sleep_impact"] = {"value": sleep_impact, "score": round(sleep_score, 3)}
        subs["social_impact"] = {"value": social_impact, "score": round(social_score, 3)}
        avg = (sleep_score + social_score) / 2
        return avg, subs

    @staticmethod
    def _generate_recommendations(dimensions, tier, age_group):
        """根据评估结果生成行为建议"""
        recs = []

        if dimensions["time"].risk_flag:
            recs.append("建议将每日学习时间控制在合理范围内，设置定时休息提醒")
        if dimensions["motivation"].risk_flag:
            recs.append("外在奖励依赖度偏高，建议尝试探索性学习任务，重新发现学习的内在乐趣")
        if dimensions["control"].risk_flag:
            recs.append("计划停止学习时遇到困难，建议使用系统的'强制休息'功能，或与家长约定学习时段")
        if dimensions["cognition"].risk_flag:
            recs.append("对排行榜和社交功能的关注度偏高，建议开启'专注模式'，暂时隐藏排行榜")
        if dimensions["function"].risk_flag:
            recs.append("学习已影响到睡眠或社交，建议立即调整学习节奏，必要时联系学校心理老师")

        if tier == LAIRiskTier.L1_NORMAL:
            recs.insert(0, "当前学习模式健康，继续保持！")
        elif tier == LAIRiskTier.L2_WATCH:
            recs.insert(0, "学习投入略有偏高，建议关注以下维度")
        elif tier == LAIRiskTier.L3_DEEP:
            recs.insert(0, "检测到深度成瘾风险，系统将自动降低游戏化强度并通知家长")
        elif tier == LAIRiskTier.L4_PATHOLOGICAL:
            recs.insert(0, "检测到病理性成瘾风险，建议立即暂停使用并寻求专业心理评估")

        return recs


# 全局单例
lai_engine = LearningAddictionIndex()
