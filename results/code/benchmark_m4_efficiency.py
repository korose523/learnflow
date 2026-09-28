# -*- coding: utf-8 -*-
"""M4 逐题（per-item）路径的效率基准：量化"秩矩阵外提"的加速比。

背景
----
`difficulty_m4.py` 的 `estimate_m4_difficulty` 在部分可观测（coverage）下走**逐题 β**
路径：原本 `m4_beta(zstd, qi)` 每次调用都在内部对全部 m 列重排一遍
（`ranks(c) for c in zstd`）。但 zstd 的秩对**所有题目相同**（item-invariant），于是
n 道题被重复排序了 n 次——纯 Python 下排序是主导成本。

本基准独立复刻逐题组合的数学（`ranks`/`pearson`/`standardize`/`solve` 与生产模块同口径），
对比两种实现：
  OLD：秩在逐题循环内重算（= 优化前行为）；
  NEW：秩在循环外算一次后透传（= 优化后行为，第 3.5 节）。
两者数值结果逐位相同（已由 `tests/test_difficulty_m4.py::TestEfficiencyRefactor` 锁死）。

用法
----
    python results/code/benchmark_m4_efficiency.py
"""
import math
import time

M = 7  # 信号列数（与 M4_DEFAULT_SIGNALS 同量级）


# ───────────────────────────── 复刻的底层数学（与生产模块同口径） ─────────────────────────────
def ranks(v):
    n = len(v)
    order = sorted(range(n), key=v.__getitem__)
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        pivot = v[order[i]]
        while j + 1 < n and v[order[j + 1]] == pivot:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            r[order[t]] = avg
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    if n < 2:
        return 0.0
    ma = sum(a) / n
    mb = sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0.0 or vb <= 0.0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def standardize(cols):
    n = len(cols[0])
    out = []
    for c in cols:
        m = sum(c) / n
        v = sum((x - m) ** 2 for x in c) / n
        s = math.sqrt(v) if v > 0 else 1.0
        out.append([(x - m) / s for x in c])
    return out


def solve(A, b):
    m = len(A)
    M_ = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(m):
        piv = max(range(c, m), key=lambda r: abs(M_[r][c]))
        if abs(M_[piv][c]) < 1e-12:
            return None
        M_[c], M_[piv] = M_[piv], M_[c]
        pv = M_[c][c]
        for r in range(c + 1, m):
            f = M_[r][c] / pv
            if f:
                for t in range(c, m + 1):
                    M_[r][t] -= f * M_[c][t]
    x = [0.0] * m
    for r in range(m - 1, -1, -1):
        acc = M_[r][m]
        for t in range(r + 1, m):
            acc -= M_[r][t] * x[t]
        x[r] = acc / M_[r][r]
    return x


def rank_covariance(R, ridge=1e-3):
    m = len(R)
    V = [[0.0] * m for _ in range(m)]
    for i in range(m):
        V[i][i] = 1.0 + ridge
        for j in range(i + 1, m):
            v = pearson(R[i], R[j])
            V[i][j] = v
            V[j][i] = v
    return V


def beta_from_q_old(Zstd, q, ridge=1e-3):
    """优化前：秩在每次调用内重算。"""
    R = [ranks(c) for c in Zstd]
    V = rank_covariance(R, ridge)
    return solve(V, list(q))


def beta_from_q_new(Zstd, q, R, ridge=1e-3):
    """优化后：秩由调用方传入（循环外已算好）。"""
    V = rank_covariance(R, ridge)
    return solve(V, list(q))


# ───────────────────────────── 数据生成（确定性 LCG，零第三方依赖） ─────────────────────────────
def make_signals(n, seed=12345):
    st = seed
    def rnd():
        nonlocal st
        st = (st * 1103515245 + 12345) % 2147483648
        return st / 2147483648.0
    cols = []
    for _ in range(M):
        cols.append([rnd() for _ in range(n)])
    return cols


def per_item_path(cols, rho, coverage, kind):
    n = len(cols[0])
    Zstd = standardize(cols)
    sgn = [1.0] * M
    rows = [[0.0] * n for _ in range(M)]
    if kind == "old":
        for i in range(n):
            qi = []
            for j in range(M):
                rho_j = rho[j]
                if coverage is not None:
                    rho_j = coverage_reliability(rho[j], coverage[i])
                qi.append(sgn[j] * math.sqrt(max(0.0, min(0.999999, rho_j))))
            bi = beta_from_q_old(Zstd, qi)
            for j in range(M):
                rows[j][i] = (bi[j] if bi else 0.0) * Zstd[j][i]
    else:
        R = [ranks(c) for c in Zstd]  # 循环外算一次
        for i in range(n):
            qi = []
            for j in range(M):
                rho_j = rho[j]
                if coverage is not None:
                    rho_j = coverage_reliability(rho[j], coverage[i])
                qi.append(sgn[j] * math.sqrt(max(0.0, min(0.999999, rho_j))))
            bi = beta_from_q_new(Zstd, qi, R)
            for j in range(M):
                rows[j][i] = (bi[j] if bi else 0.0) * Zstd[j][i]
    return list(map(sum, zip(*rows)))


def coverage_reliability(rho_unit, n_obs):
    n = max(1, int(n_obs))
    rho = max(0.0, min(0.999999, float(rho_unit)))
    return n * rho / (1.0 + (n - 1) * rho)


def _time(fn, repeats=5):
    # 一次预热 + 取中位数
    fn()
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    samples.sort()
    return samples[len(samples) // 2]


def main():
    ns = [100, 200, 400, 800]
    rho = [0.9, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
    print(f"{'n':>6} | {'OLD(ms)':>9} | {'NEW(ms)':>9} | {'speedup':>8}")
    print("-" * 42)
    for n in ns:
        cols = make_signals(n)
        cov = [1 + (i % 9) for i in range(n)]  # 每题有效观测数（部分可观测）
        old_t = _time(lambda: per_item_path(cols, rho, cov, "old"))
        new_t = _time(lambda: per_item_path(cols, rho, cov, "new"))
        sp = old_t / new_t if new_t > 0 else float("inf")
        print(f"{n:>6} | {old_t*1000:>9.2f} | {new_t*1000:>9.2f} | {sp:>7.2f}x")
    print("-" * 42)
    print("说明：OLD=秩在逐题循环内重算（优化前）；NEW=秩循环外算一次后透传（优化后）。")
    print("数值结果两者逐位相同（已由 TestEfficiencyRefactor 锁死）；本表仅量化时间收益。")


if __name__ == "__main__":
    main()
