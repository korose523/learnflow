"""A/B 测试与持续优化框架

基于论文第九章9.5节：A/B测试与持续优化框架
- 最小可干预单元：每次实验只改变一个参数
- 分层随机化：按年级、学科、学习风格分层
- 伦理优先：安全停止规则
- 长期追踪：30天、90天效果追踪
- 健康一票否决：牺牲健康安全的方案拒绝上线

实验流程：影子模式 → 小流量(1-5%) → 全量上线（经伦理委员会审查）
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional, Any
from collections import defaultdict
import random
import hashlib


class ExperimentPhase(str, Enum):
    """实验阶段"""
    SHADOW = "shadow"        # 影子模式：计算但不执行
    CANARY = "canary"        # 小流量：1-5%用户
    RAMPING = "ramping"      # 逐步放量
    FULL = "full"            # 全量上线
    STOPPED = "stopped"      # 已停止（安全规则触发）
    COMPLETED = "completed"  # 已完成


class MetricCategory(str, Enum):
    """指标类别（论文'学习效果-动机质量-健康安全'三维）"""
    LEARNING = "learning"      # 学习效果
    MOTIVATION = "motivation"  # 动机质量
    HEALTH = "health"          # 健康安全


@dataclass
class ExperimentMetric:
    """实验指标定义"""
    name: str
    category: MetricCategory
    target_direction: str  # "increase" or "decrease"
    safety_threshold: Optional[float] = None  # 健康安全阈值（超过则停止实验）
    current_value: float = 0.0


@dataclass
class ExperimentResult:
    """实验结果记录"""
    experiment_id: str
    user_id: str
    group: str  # "control" or "treatment"
    metrics: dict  # {metric_name: value}
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Experiment:
    """A/B 测试实验定义"""
    id: str
    name: str
    description: str
    parameter_name: str        # 被测试的参数名（最小可干预单元）
    control_value: Any         # 对照组参数值
    treatment_value: Any       # 实验组参数值
    phase: ExperimentPhase = ExperimentPhase.SHADOW
    traffic_percentage: float = 0.0  # 实验流量占比
    metrics: list = field(default_factory=list)  # [ExperimentMetric]
    results: list = field(default_factory=list)  # [ExperimentResult]
    safety_stop_triggered: bool = False
    safety_stop_reason: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    min_sample_per_group: int = 100  # 每组最小样本量
    tracking_days: int = 90  # 长期追踪天数

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameter_name": self.parameter_name,
            "control_value": str(self.control_value),
            "treatment_value": str(self.treatment_value),
            "phase": self.phase.value,
            "traffic_percentage": self.traffic_percentage,
            "safety_stop_triggered": self.safety_stop_triggered,
            "safety_stop_reason": self.safety_stop_reason,
            "total_results": len(self.results),
            "created_at": self.created_at.isoformat(),
        }


class ABTestFramework:
    """A/B 测试框架

    管理 LearnFlow 所有游戏化引擎参数的 A/B 测试生命周期。
    遵循'健康一票否决'原则：任何牺牲健康安全的方案拒绝上线。
    """

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._user_assignments: dict[str, dict[str, str]] = defaultdict(dict)  # {user_id: {experiment_id: group}}

    def create_experiment(
        self,
        name: str,
        description: str,
        parameter_name: str,
        control_value: Any,
        treatment_value: Any,
        metrics: Optional[list] = None,
    ) -> Experiment:
        """创建新实验（初始为影子模式）"""
        exp_id = self._generate_id(name)
        exp = Experiment(
            id=exp_id,
            name=name,
            description=description,
            parameter_name=parameter_name,
            control_value=control_value,
            treatment_value=treatment_value,
            metrics=metrics or self._default_metrics(),
        )
        self._experiments[exp_id] = exp
        return exp

    def assign_user(self, experiment_id: str, user_id: str, strata: Optional[dict] = None) -> str:
        """将用户分配到对照组或实验组

        使用基于 user_id 的确定性哈希，确保同一用户始终分到同一组。
        支持分层随机化（strata 参数用于后续分层分析）。
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return "control"

        # 已分配则返回已有分组
        if experiment_id in self._user_assignments.get(user_id, {}):
            return self._user_assignments[user_id][experiment_id]

        # 影子模式：所有用户都是对照组（不执行新策略）
        if exp.phase == ExperimentPhase.SHADOW:
            group = "control"
        else:
            # 确定性哈希分配
            hash_input = f"{experiment_id}:{user_id}"
            hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            bucket = (hash_val % 100) / 100.0

            if bucket < exp.traffic_percentage:
                group = "treatment"
            else:
                group = "control"

        self._user_assignments[user_id][experiment_id] = group
        return group

    def get_parameter_value(self, experiment_id: str, user_id: str, default_value: Any) -> Any:
        """获取用户应使用的参数值（核心方法）

        在影子模式下，所有用户使用 default_value；
        在小流量/全量阶段，实验组用户使用 treatment_value。
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
            return default_value

        group = self.assign_user(experiment_id, user_id)
        if group == "treatment" and exp.phase != ExperimentPhase.SHADOW:
            return exp.treatment_value
        return exp.control_value if exp.phase != ExperimentPhase.SHADOW else default_value

    def record_result(self, experiment_id: str, user_id: str, metrics: dict):
        """记录实验结果"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return

        group = self.assign_user(experiment_id, user_id)
        result = ExperimentResult(
            experiment_id=experiment_id,
            user_id=user_id,
            group=group,
            metrics=metrics,
        )
        exp.results.append(result)

        # 检查安全停止规则
        self._check_safety_rules(exp)

    def _check_safety_rules(self, exp: Experiment):
        """检查安全停止规则——健康一票否决"""
        if exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
            return

        # 检查健康安全指标
        treatment_health = [r.metrics for r in exp.results if r.group == "treatment"]
        if len(treatment_health) < 10:  # 样本不足时不检查
            return

        # 计算实验组的健康指标均值
        health_metrics = ["risk_score", "anxiety_score", "depression_score", "addiction_index"]
        for metric_name in health_metrics:
            values = [m.get(metric_name) for m in treatment_health if m.get(metric_name) is not None]
            if not values:
                continue
            avg = sum(values) / len(values)

            # 如果健康指标恶化超过阈值，触发安全停止
            if metric_name == "risk_score" and avg > 70:  # LAI风险评分>70（即健康分<30）
                self._trigger_safety_stop(exp, f"实验组风险评分均值 {avg:.1f} 超过安全阈值 70")
                return
            if metric_name == "addiction_index" and avg > 0.6:  # 成瘾指数>0.6
                self._trigger_safety_stop(exp, f"实验组成瘾指数均值 {avg:.2f} 超过安全阈值 0.6")
                return

    def _trigger_safety_stop(self, exp: Experiment, reason: str):
        """触发安全停止"""
        exp.phase = ExperimentPhase.STOPPED
        exp.safety_stop_triggered = True
        exp.safety_stop_reason = reason
        exp.completed_at = datetime.now(UTC)

    def advance_phase(self, experiment_id: str, force: bool = False) -> ExperimentPhase:
        """推进实验阶段：shadow → canary → ramping → full

        Args:
            experiment_id: 实验ID
            force: 是否强制推进（跳过样本量检查，用于测试或管理员强制操作）
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return ExperimentPhase.STOPPED

        if exp.phase == ExperimentPhase.SHADOW:
            exp.phase = ExperimentPhase.CANARY
            exp.traffic_percentage = 0.05  # 5%
            exp.started_at = datetime.now(UTC)
        elif exp.phase == ExperimentPhase.CANARY:
            # 检查是否有足够样本（可强制跳过）
            treatment_count = sum(1 for r in exp.results if r.group == "treatment")
            if not force and treatment_count < exp.min_sample_per_group:
                return exp.phase  # 样本不足，暂不推进
            exp.phase = ExperimentPhase.RAMPING
            exp.traffic_percentage = 0.25  # 25%
        elif exp.phase == ExperimentPhase.RAMPING:
            exp.phase = ExperimentPhase.FULL
            exp.traffic_percentage = 1.0  # 100%
        elif exp.phase == ExperimentPhase.FULL:
            exp.phase = ExperimentPhase.COMPLETED
            exp.completed_at = datetime.now(UTC)

        return exp.phase

    def get_experiment_summary(self, experiment_id: str) -> dict:
        """获取实验摘要统计"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}

        control_results = [r for r in exp.results if r.group == "control"]
        treatment_results = [r for r in exp.results if r.group == "treatment"]

        summary = {
            "experiment": exp.to_dict(),
            "control_count": len(control_results),
            "treatment_count": len(treatment_results),
            "metric_comparisons": {},
        }

        # 计算各指标的组间差异
        all_metric_names = set()
        for r in exp.results:
            all_metric_names.update(r.metrics.keys())

        for metric_name in all_metric_names:
            control_vals = [r.metrics[metric_name] for r in control_results if metric_name in r.metrics and r.metrics[metric_name] is not None]
            treatment_vals = [r.metrics[metric_name] for r in treatment_results if metric_name in r.metrics and r.metrics[metric_name] is not None]

            if not control_vals or not treatment_vals:
                continue

            control_mean = sum(control_vals) / len(control_vals)
            treatment_mean = sum(treatment_vals) / len(treatment_vals)

            # 简单效应量（Cohen's d 的简化版）
            pooled_std = (sum((v - control_mean) ** 2 for v in control_vals) / len(control_vals)) ** 0.5
            effect_size = (treatment_mean - control_mean) / pooled_std if pooled_std > 0 else 0

            summary["metric_comparisons"][metric_name] = {
                "control_mean": round(control_mean, 4),
                "treatment_mean": round(treatment_mean, 4),
                "difference": round(treatment_mean - control_mean, 4),
                "effect_size": round(effect_size, 3),
                "favor_treatment": treatment_mean > control_mean,
            }

        # 健康一票否决判定
        health_metrics = ["risk_score", "addiction_index", "anxiety_score"]
        health_ok = True
        for hm in health_metrics:
            if hm in summary["metric_comparisons"]:
                comp = summary["metric_comparisons"][hm]
                # 健康指标：treatment不应比control更差
                if comp["favor_treatment"] and hm in ("risk_score", "addiction_index", "anxiety_score"):
                    health_ok = False

        summary["health_veto"] = not health_ok
        summary["recommendation"] = "reject" if not health_ok else ("approve" if all(v.get("favor_treatment", False) for k, v in summary["metric_comparisons"].items() if k not in health_metrics) else "inconclusive")

        return summary

    def list_experiments(self) -> list:
        """列出所有实验"""
        return [exp.to_dict() for exp in self._experiments.values()]

    def _default_metrics(self) -> list:
        """默认指标集（三维指标体系）"""
        return [
            ExperimentMetric("knowledge_mastery_growth", MetricCategory.LEARNING, "increase"),
            ExperimentMetric("exam_score", MetricCategory.LEARNING, "increase"),
            ExperimentMetric("intrinsic_motivation_ratio", MetricCategory.MOTIVATION, "increase"),
            ExperimentMetric("flow_frequency", MetricCategory.MOTIVATION, "increase"),
            ExperimentMetric("autonomy_score", MetricCategory.MOTIVATION, "increase"),
            ExperimentMetric("lai_score", MetricCategory.HEALTH, "increase", safety_threshold=50.0),
            ExperimentMetric("risk_score", MetricCategory.HEALTH, "decrease", safety_threshold=70.0),
            ExperimentMetric("drop_rate", MetricCategory.HEALTH, "decrease", safety_threshold=0.15),
        ]

    @staticmethod
    def _generate_id(name: str) -> str:
        """根据名称生成确定性ID"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"exp_{timestamp}_{name_hash}"


# 全局单例
ab_test_framework = ABTestFramework()
