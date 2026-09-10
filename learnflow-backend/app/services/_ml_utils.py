"""纯 Python 数值工具（无 numpy 依赖）—— AI 实时分析层的基础数学库。

提供矩阵运算 / 激活函数 / 最小二乘 / logistic 梯度 / AUROC 等,
全部用标准库实现, 保证在受限环境(本机无 numpy)也能训练与推断。
"""
from __future__ import annotations

import bisect
import math
from typing import List, Sequence, Tuple

Vector = List[float]
Matrix = List[Vector]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    s = 0.0
    for x, y in zip(a, b):
        s += x * y
    return s


def matvec(M: Matrix, v: Vector) -> Vector:
    return [dot(row, v) for row in M]


def transpose(M: Matrix) -> Matrix:
    if not M:
        return []
    return [[M[r][c] for r in range(len(M))] for c in range(len(M[0]))]


def matmul(A: Matrix, B: Matrix) -> Matrix:
    Bt = transpose(B)
    return [[dot(A[i], Bt[j]) for j in range(len(Bt))] for i in range(len(A))]


def add_bias(X: Matrix) -> Matrix:
    """末尾追加一列 1（截距）。"""
    return [row + [1.0] for row in X]


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def tanh(x: float) -> float:
    if x < -20:
        return -1.0
    if x > 20:
        return 1.0
    e = math.exp(2 * x)
    return (e - 1.0) / (e + 1.0)


def clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _inv(M: Matrix) -> Matrix:
    """Gauss-Jordan 求逆（方阵, 近奇异时加扰动）。"""
    n = len(M)
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(M)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        A[col], A[piv] = A[piv], A[col]
        d = A[col][col]
        if abs(d) < 1e-12:
            d = 1e-12
        A[col] = [v / d for v in A[col]]
        for r in range(n):
            if r != col:
                f = A[r][col]
                if f != 0.0:
                    A[r] = [A[r][k] - f * A[col][k] for k in range(2 * n)]
    return [row[n:] for row in A]


def ols(X: Matrix, y: Vector, l2: float = 0.0) -> Vector:
    """普通最小二乘 (normal equations), 带可选 L2。返回系数 w (截距在末位)。"""
    Xb = add_bias(X)
    Xt = transpose(Xb)
    XtX = matmul(Xt, Xb)
    if l2:
        for i in range(len(XtX)):
            XtX[i][i] += l2
    Xty = matvec(Xt, y)
    try:
        inv = _inv(XtX)
    except Exception:
        inv = [[0.0] * len(XtX) for _ in range(len(XtX))]
    return matvec(inv, Xty)


def auc(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    """AUROC (rank 法, 含 MidRank 处理并列)。"""
    n = len(y_true)
    if n == 0:
        return 0.5
    pos = [s for t, s in zip(y_true, y_score) if t == 1]
    neg = sorted(s for t, s in zip(y_true, y_score) if t == 0)
    if not pos or not neg:
        return 0.5

    def rank_count(s: float) -> float:
        lt = bisect.bisect_left(neg, s)
        le = bisect.bisect_right(neg, s)
        return lt + 0.5 * (le - lt)

    s = sum(rank_count(p) for p in pos)
    return s / (len(pos) * len(neg))


def accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    if not y_true:
        return 0.0
    return sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(y_true)


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def std(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
