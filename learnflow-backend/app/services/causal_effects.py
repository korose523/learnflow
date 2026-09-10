"""DML 双机器学习因果效应估计（纯 Python, 双阶段残差回归）。

用于从 ``LearningEvent.decision_snapshot`` 复现数据估计
「某机制是否下发 → LAI 变化量」的**平均因果效应 (ATE)**,
这是系统论文最强的可复现卖点 (对照 CHI/UIST 因果评估范式)。
"""
from __future__ import annotations

from typing import Dict, List

from app.services._ml_utils import add_bias, dot, ols, std


def _residuals(X: List[List[float]], y: List[float], l2: float) -> List[float]:
    w = ols(X, y, l2=l2)
    Xb = add_bias(X)
    pred = [dot(row, w) for row in Xb]
    return [yi - pi for yi, pi in zip(y, pred)]


def dml_ate(
    treatment: List[float],
    outcome: List[float],
    covariates: List[List[float]],
    l2: float = 1e-3,
) -> Dict[str, float]:
    """估计处理对结局的平均因果效应 (ATE)。

    Args:
        treatment: 0/1 或因变量 (是否下发某机制 / 机制剂量)
        outcome:   连续结局 (如 LAI 变化量)
        covariates: 混淆变量矩阵 (用户基线特征等)
    返回: {ate, se, n}
    """
    if len(treatment) < 4 or len({round(t, 6) for t in treatment}) < 2:
        return {"ate": 0.0, "se": float("nan"), "n": len(treatment)}
    rt = _residuals(covariates, treatment, l2)
    ro = _residuals(covariates, outcome, l2)
    w = ols([[r] for r in rt], ro, l2=l2)
    ate = w[0]
    n = len(ro)
    sst = sum(r * r for r in rt)
    se = (std(ro) / (sst / n) ** 0.5) if sst > 0 else float("nan")
    return {"ate": ate, "se": se, "n": n}


def estimate_mechanism_effect(rows: List[Dict]) -> Dict[str, float]:
    """rows: [{treatment:0/1, outcome:float, covariates:[...]}] -> ATE。"""
    tr = [float(r["treatment"]) for r in rows]
    ou = [float(r["outcome"]) for r in rows]
    cov = [list(r["covariates"]) for r in rows]
    return dml_ate(tr, ou, cov)
