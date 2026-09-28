# -*- coding: utf-8 -*-
"""M4：信度结构化 composition 难度估计器 —— 零依赖实现与严谨留出对比。

为什么写这个包
--------------
本环境没有 numpy / scipy，但 results/code/difficulty_cache.npz 里已经缓存了
Junyi（M=1234 题 × 7 字段 × K=500 蓄水池槽位）与 DBE-KT22（M=212 题 × 5 字段
× K=500）。.npz 是 zip + .npy，可以用标准库直接读；于是**不必安装任何第三方包**
就能在真实数据上复 flavor 出 O8/O11 的留出协议，并把 M4 与既有估计器放在同一
共和协议下比较。

与本 Os={fused6, signed7, srw7} 的关系
--------------------------------------
既有估计器不是被替换，而是被**包含**：
    fused6  = 等权 + 别除 upgrade_rate            （M4-C 退化为固定 λ 时的一部分）
    signed7 = 符号校正 + 等权                      （M4-A + M4-B 退化为等权）
    srw7    = 符号校正 + 逐列信度 w_k ∝ ρ_k        （M4-B 忽略列间共线时的特例）
M4 在此之上引入四个可独立剥离的模块，见 `run_m4.py` 的消融表。

唯有红线（与本项目其余部分一致）
--------------------------------
* 判定量不得与拟合量同统计量。故主判据一律为 **外生标签**（DBE 教师难度 `D_y`、
  Junyi 平台难度 `J_y`）；既有 O7/O11 的"留出错误率"判据只作为 **同场对照**，
  不承载任何"哪个更难"的因果/准确性主张。
* 所有符号、信度、权重、**以及λ** 一律只在拟合块 A 内估计；B 块与外生标签只用于评价。
"""
import array
import ast
import json
import math
import random
import struct
import zipfile
from pathlib import Path

# ---------------------------------------------------------------- 数据加载
_TC = {"<f4": "f", "<f8": "d", "<i4": "i", "<i8": "q", "|i1": "b",
       "|u1": "B", "<i2": "h"}


def load_cache(npz_path):
    """读 results/code/difficulty_cache.npz，返回 {name: (shape, array)}。

    纯标准库实现：.npz = zip，.npy = 128 字节级头部 + 裸数组（本项目缓存一律
    little-endian、C order，本机为 Windows x86-64 亦为 little-endian，故无需字节交换）。
    """
    zf = zipfile.ZipFile(npz_path)
    out = {}
    for info in zf.infolist():
        name = info.filename
        if not name.endswith(".npy"):
            continue
        blob = zf.read(name)
        assert blob[:6] == b"\x93NUMPY", name
        hlen = int.from_bytes(blob[8:10], "little")
        head = blob[10:10 + hlen].decode("latin1").strip()
        d = ast.literal_eval(head)
        shape, descr = d["shape"], d["descr"]
        if d.get("fortran_order"):
            raise ValueError(f"{name}: Fortran order 未支持")
        if descr.startswith("|U") or descr.startswith("<U"):
            continue                      # 字符串列（J_keep / D_keep 的 id）本脚本不需要
        tc = _TC.get(descr)
        if tc is None:
            raise ValueError(f"{name}: 未知 dtype {descr}")
        payload = blob[10 + hlen:]
        a = array.array(tc)
        a.frombytes(payload)
        # 尾部可能有 padding，按 shape 截断
        n = 1
        for s in shape:
            n *= s
        if len(a) != n:
            a = a[:n]
        out[name[:-4]] = (shape, a)
    zf.close()
    return out


# ---------------------------------------------------------------- 秩与相关
def rank_average(v):
    """平均秩（1..n），并列取均值。与 scipy.stats.rankdata(method='average') 一致。"""
    n = len(v)
    order = sorted(range(n), key=v.__getitem__)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        pivot = v[order[i]]
        while j + 1 < n and v[order[j + 1]] == pivot:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


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


def spearman(a, b):
    """Spearman ρ = 平均秩上的 Pearson。"""
    return pearson(rank_average(a), rank_average(b))


def kendall_tau_b(a, b):
    """Kendall τ_b（对并列一致的操作 Knox —— 适合 3 级教师标签这样的重并列数据）。

    τ_b = (C - D) / sqrt((C+D+T_a) * (C+D+T_b))
    """
    n = len(a)
    if n < 2:
        return 0.0
    concord = discord = 0
    ta = tb = 0
    for i in range(n - 1):
        ai, bi = a[i], b[i]
        for j in range(i + 1, n):
            aj, bj = a[j], b[j]
            da = (aj > ai) - (aj < ai)
            db = (bj > bi) - (bj < bi)
            if da == 0 and db == 0:
                continue
            if da == 0:
                ta += 1
                continue
            if db == 0:
                tb += 1
                continue
            if da * db > 0:
                concord += 1
            else:
                discord += 1
    num = concord - discord
    den = math.sqrt((concord + discord + ta) * (concord + discord + tb))
    return num / den if den > 0 else 0.0


EPS = 1e-4


def ecdf_logit(v):
    """经验 CDF → logit（与生产模块的同名函数逐值一致）。"""
    n = len(v)
    if n == 0:
        return []
    r = rank_average(v)
    out = []
    for x in r:
        q = (x - 0.5) / n
        p = EPS if q < EPS else (1.0 - EPS if q > 1.0 - EPS else q)
        out.append(math.log(p / (1.0 - p)))
    return out


def standardize(cols):
    """逐列去均值除标准差（M4-B 的前置：潜变量模型要求单位方差的指示列）。"""
    n = len(cols[0])
    out = []
    for c in cols:
        m = sum(c) / n
        v = sum((x - m) ** 2 for x in c) / n
        s = math.sqrt(v) if v > 0 else 1.0
        out.append([(x - m) / s for x in c])
    return out


# ---------------------------------------------------------------- 线性代数
def solve(A, b):
    """高斯消元（部分选主元）解 A x = b。m ≤ 7，暴力可靠即可。"""
    m = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(m):
        piv = max(range(c, m), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return None                      # 奇异 → 调用方退化处理
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        for r in range(c + 1, m):
            f = M[r][c] / pv
            if f:
                for k in range(c, m + 1):
                    M[r][k] -= f * M[c][k]
    x = [0.0] * m
    for r in range(m - 1, -1, -1):
        acc = M[r][m]
        for k in range(r + 1, m):
            acc -= M[r][k] * x[k]
        x[r] = acc / M[r][r]
    return x


# ---------------------------------------------------------------- M4 核心
def spearman_brown(r_half):
    """Spearman–Brown：把"半长样本"折半信度换算为"全长样本"信度。
    ρ_full = 2r / (1 + r)（r ≤ 0 时按 0 处理，与 srw7 的 max(0, ·) 口径一致）。"""
    r = max(0.0, min(0.999999, float(r_half)))
    return 2.0 * r / (1.0 + r)


def item_reliability_from_coverage(rho_unit, n_obs):
    """由"单位观测信度"与每题实际观测数给出该题的折半式信度（M4-D）。

    Spearman–Brown 的一般形式：ρ(n) = n·ρ₁ / (1 + (n−1)·ρ₁)。
    这样即便同一列内部，观测数多的题也自动获得更高的本地权重。
    """
    n = max(1, int(n_obs))
    return n * rho_unit / (1.0 + (n - 1) * rho_unit)


def unit_unreliability_from_half(r_half, half_n):
    """由半长样本的信度 r_half 反解单次观测信度 ρ₁，用于对不同题量做外推。

    ρ(h) = h ρ₁ / (1+(h−1)ρ₁)  ⇒  ρ₁ = r / (h − (h−1) r)
    """
    r = max(0.0, min(0.999999, float(r_half)))
    h = max(1.0, float(half_n))
    den = h - (h - 1.0) * r
    return r / den if den > 0 else 0.0


def m4_weights(Z, rel_full, per_item_rel=None, item_idx=None, ridge=1e-3):
    """M4-B：信度结构化、共线校正的组合权重 β = V^{-1} q。

    Args:
        Z: 已标准化的列列表 [[...] × m]，长度 n。
        rel_full: 每列的（全长）信度 ρ_k ∈ [0,1)。
        per_item_rel: 可选，长度 m 的"每题本地信度"列表；给出则用它代替全局 ρ_k
                      构造 q（M4-D 的行级变体：对每个题单独求解一次 7×7）。
        ridge: V 的对角阻尼，防止因并列/常量列导致的病态。

    Returns:
        β 列表（未归一；量纲与 q 一致）。奇异时退化为 q / Σq。
    """
    m = len(Z)
    n = len(Z[0])
    # V：秩相关矩阵（M4-A：在秩上估二阶结构 → 对 logit 尾部的极值不敏感，
    # 且完整保留 M1/O1 的"单调重参数化不变性"）
    R = [rank_average(c) for c in Z]
    V = [[0.0] * m for _ in range(m)]
    for i in range(m):
        V[i][i] = 1.0 + ridge
        for j in range(i + 1, m):
            v = pearson(R[i], R[j])
            V[i][j] = V[j][i] = v
    q = [math.sqrt(max(0.0, min(0.999999, rel_full[k]))) for k in range(m)]
    beta = solve(V, q)
    if beta is None:
        s = sum(q)
        beta = [x / s for x in q] if s > 0 else [1.0 / m] * m
    return beta


def lambda_from_beta(beta, ref=0):
    """M4-C：λ 不再由 k 的经验幂律给出，而是由组合权重直接导出。

    λ = Σ_{k≠ref} |β_k| / Σ_k |β_k|
    当辅助信号全部不可信时 β_aux → 0 ⇒ λ → 0（自动退回纯成功率），
    无需重拟合 λ_cf(k) 的两个常数（27.3, 0.895），也避免了 O9 观察到的
    "λ 只由 k 驱动 → 跨数据集无收益"。
    """
    absb = [abs(x) for x in beta]
    tot = sum(absb)
    if tot <= 0:
        return 0.0
    return (tot - absb[ref]) / tot


# ---------------------------------------------------------------- 快速 Kendall τ_b
def _merge_count_inv(seq):
    """归并排序数逆序对（含并列处理见调用方），返回逆序数。"""
    n = len(seq)
    if n < 2:
        return 0
    buf = [0] * n
    inv = 0
    width = 1
    src = list(seq)
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                if src[i] <= src[j]:
                    buf[k] = src[i]; i += 1
                else:
                    buf[k] = src[j]; j += 1
                    inv += mid - i
                k += 1
            while i < mid:
                buf[k] = src[i]; i += 1; k += 1
            while j < hi:
                buf[k] = src[j]; j += 1; k += 1
        src, buf = buf[:n], src
        width *= 2
    return inv


def kendall_tau_b_fast(a, b):
    """Kendall τ_b，O(n log n)：按 a 稳定排序后在 b 上归并数逆序对。

    记号：N = n(n−1)/2；ta / tb 为**全部**并列对数（含双并列），t 为双并列对数。
      C + D = N − ta − tb + t
    分母须用"仅在其中一条上并列"的对数，故要把双并列从 ta、tb 里扣掉一次：
      τ_b = (C − D) / sqrt((C + D + tb − t) · (C + D + ta − t))
                        = (C − D) / sqrt((N − ta) · (N − tb))
    """
    n = len(a)
    if n < 2:
        return 0.0
    N = n * (n - 1) // 2
    order = sorted(range(n), key=lambda i: (a[i], b[i]))
    aa = [a[i] for i in order]
    bb = [b[i] for i in order]
    D = _merge_count_inv(bb)
    ta = tb = t = 0

    def ties(vals):
        s = 0
        i = 0
        while i < len(vals):
            j = i
            while j + 1 < len(vals) and vals[j + 1] == vals[i]:
                j += 1
            m = j - i + 1
            if m > 1:
                s += m * (m - 1) // 2
            i = j + 1
        return s

    ta = ties(aa)                       # aa 已排序 ⇒ 可直接数相邻相等
    tb = ties(sorted(b))                # ⚠ 必须另行排序：bb 是按 (a,b) 排的，b 值本身不相邻
    key = sorted(zip(a, b))             # 双并列对数（两条都不并列的对）
    t = 0
    i = 0
    while i < n:
        j = i
        while j + 1 < n and key[j + 1] == key[i]:
            j += 1
        m = j - i + 1
        if m > 1:
            t += m * (m - 1) // 2
        i = j + 1
    CD = N - ta - tb + t          # C + D（双并列对被 ta、tb 各扣一次，须加回一次）
    num = CD - 2 * D              # C − D
    den = math.sqrt(max(0.0, N - ta) * max(0.0, N - tb))
    return num / den if den > 0 else 0.0
