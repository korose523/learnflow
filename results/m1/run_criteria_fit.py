# -*- coding: utf-8 -*-
"""M1 · A1/A2 两类追加判据 — 真实数据拟合：**独立交叉校验实现**（纯标准库 + csv）。

⚠️ 本脚本**不是规范产物来源**。规范产物 `m1_criteria_results.json` 由 `run_a1a2_fit.py` 产出
（每题 B 半 IRT 响应上限 1500、15 节点 quadrature）；本脚本是**独立第二实现**
（上限 4000、21 节点 quadrature、概率域 E-step），输出到 `m1_criteria_results_xcheck.json`，
用于交叉校验两套实现是否给出相容估计（cap/nodes 不同，数值不要求逐位相等）。
历史：本脚本曾因 M-step 在 25 次牛顿内迭代中复用迭代初查表（stale 梯度）而发散（mean|b|≈37、
ρ 变负），已于 2026-09-23 修正为「每步用当前 b_j 实时重算 sigmoid」，并加合成数据回归验证
（`_validate_fit_scaled.py`：ρ(true_b, b_rec)=0.9714、|b−b_true|=0.0916，与骨架 `fit_irt_1pl` 数值一致）。

依赖：
  - 复用 `verify_m1_criteria.py` 的 `spearman_rho` / `weighted_kappa`（同一份数学，审稿人 clone 即跑）。
  - IRT-1PL 估计量与骨架 `fit_irt_1pl` 数学严格一致（Rasch, 斜率=1, θ~N(0,1), 21 节点高斯 quadrature,
    MML-EM）；此处为在 1620 万行 Junyi 规模下可运行，仅做实现效率优化（逐迭代预计算
    P(correct|θ,b)/P(incorrect) 查表供 E-step 复用 + 概率域 posterior 归一化 + 牛顿 M-step
    实时重算 sigmoid(θ−b)），不改变估计量本身。验证：`_validate_fit_scaled.py` 合成数据
    ρ(true_b, b_rec)>0.95、|b_rec−b_true|均值<0.30，与 `fit_irt_1pl` 数值一致。

A1（能力校正判据，Junyi）：
  - 按 crc32(uuid) 奇偶把学生切 A/B 半（O10 学生级留出）。
  - 判据块 B：每题 B 半作答数 ≥ 500 的题（口径）拟合 IRT-1PL 难度 b_j。
  - 行为判据（融合）：在 A 半上计算 O5 七信号（等权符号校正融合，ECDF→logit），作留出比较。
  - 行为判据（仅成功率）：B 半失败率 logit 变换。
  - spearman_fusion  = Spearman(b_j, 融合_A)；spearman_success = Spearman(b_j, 仅成功率_B)。

A2（外生判据，DBE-KT22）：
  - 212 题，专家难度标签 1/2/3（Questions.difficulty）作外生判据。
  - O4 五信号等权符号校正融合（成功率反向 / 提示率 / 自报难度 / 信任反向 / 时长）。
  - spearman_fusion  = Spearman(融合, 专家标签)；spearman_success = Spearman(成功率反向, 专家标签)。
  - 加权 κ：DBE 仅单专家标注，无法算编码者间 κ；改为「专家标签 vs 行为难度三分位参照编码」的
    线性加权 κ（1<2<3 有序），如实标注。

输出：results/m1/m1_criteria_results.json（含 a1 / a2 双块；每块含 spearman_fusion / spearman_success）。
"""
from __future__ import annotations

import array
import csv
import json
import math
import os
import sys
import zlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_m1_criteria as V  # spearman_rho, weighted_kappa

# ─────────────────────────────────────────────────────────────────────────────
# 通用数学
# ─────────────────────────────────────────────────────────────────────────────
def _logit(p: float) -> float:
    p = min(max(p, 1e-9), 1.0 - 1e-9)
    return math.log(p / (1.0 - p))


def _bit(s: str) -> int:
    """Junyi/DBE 布尔列以 'True'/'False'/'' 存储。"""
    return 1 if s.strip().lower() in ("true", "1") else 0


def _num(s):
    try:
        return float(s)
    except (ValueError, AttributeError):
        return 0.0


def _ecdf_logit(values):
    """对一组数值做 ECDF→logit 变换（正方向保持；返回与 values 同序的向量）。"""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    out = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rank = (i + j) / 2.0 + 1.0
            p = rank / n
            out[order[k]] = _logit(p)
        i = j + 1
    return out


def _equal_weight_signed_fusion(signal_vectors, signs):
    """signal_vectors: 各信号原始值列表（每条长度 K）；signs: +1/-1 方向。
    逐信号 ECDF→logit（负向信号先取反），等权求和。返回长度 K 的融合向量。"""
    K = len(signal_vectors[0])
    fused = [0.0] * K
    for vec, sgn in zip(signal_vectors, signs):
        v = [-x if sgn < 0 else x for x in vec]
        t = _ecdf_logit(v)
        for i in range(K):
            fused[i] += t[i]
    return fused


# ─────────────────────────────────────────────────────────────────────────────
# IRT-1PL（Rasch）MML + 高斯 quadrature EM —— 规模优化版
#   P(correct|θ,b)=logistic(θ-b)，θ~N(0,1)，n_nodes 节点 quadrature。
#   与 verify_m1_criteria.fit_irt_1pl 同估计量、同收敛性；仅实现效率不同：
#     · E-step：逐迭代预计算 P(correct|θ_q,b_j) 与 P(incorrect|θ_q,b_j) 查表（只依赖 b_j、θ_q，
#       与 person 无关），避免 per-(person,item) 重复算 sigmoid；posterior 在概率域归一化，
#       不再用 log1p(exp(±x))（b_j 漂移时易上溢退化）。
#     · M-step：牛顿求 b_j 时**实时重算** sigmoid(θ_q−b_j)（用当前 b_j），与 fit_irt_1pl 严格一致；
#       不复用迭代初查表（旧版 stale 梯度是发散根因）。
# ─────────────────────────────────────────────────────────────────────────────
def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def fit_irt_1pl_scaled(responses_p, responses_j, responses_c,
                       n_persons, n_items,
                       n_iter=60, n_nodes=21,
                       lo=-5.0, hi=5.0):
    theta = [lo + (hi - lo) * i / (n_nodes - 1) for i in range(n_nodes)]
    raw = [math.exp(-0.5 * t * t) for t in theta]
    sw = sum(raw)
    w = [r / sw for r in raw]

    by_person = defaultdict(list)
    for p, j, c in zip(responses_p, responses_j, responses_c):
        by_person[p].append((j, c))

    b = [0.0] * n_items
    for it in range(n_iter):
        # E-step 查表：P(correct) 与 P(incorrect)，逐迭代按当前 b_j 重算一次
        pc = [[0.0] * n_nodes for _ in range(n_items)]
        pi = [[0.0] * n_nodes for _ in range(n_items)]
        for j in range(n_items):
            bj = b[j]
            Pc = pc[j]
            Pi = pi[j]
            for q in range(n_nodes):
                pj = _sigmoid(theta[q] - bj)
                Pc[q] = pj
                Pi[q] = 1.0 - pj

        # E-step：逐 person 算后验 r[p][q]（概率域，与 fit_irt_1pl 同级）
        R = [[0.0] * n_nodes for _ in range(n_items)]   # Σ_p r[p][q]，覆盖所有响应
        S = [0.0] * n_items                            # Σ_p Σ_q r[p][q]·x_pj（期望正确数）
        for p in range(n_persons):
            items = by_person.get(p)
            if not items:
                continue
            like = list(w)
            for (j, c) in items:
                tbl = pc[j] if c == 1 else pi[j]
                Lk = like
                Tbl = tbl
                for q in range(n_nodes):
                    Lk[q] *= Tbl[q]
            tot = sum(like)
            rp = list(w) if tot <= 0 else [lk / tot for lk in like]
            sr = sum(rp)
            for (j, c) in items:
                Rj = R[j]
                for q in range(n_nodes):
                    Rj[q] += rp[q]
                if c == 1:
                    S[j] += sr

        # M-step：逐题牛顿求 b_j，实时重算 sigmoid(θ_q−b_j)
        max_delta = 0.0
        for j in range(n_items):
            Rj = R[j]
            Sj = S[j]
            bj = b[j]
            for _ in range(25):
                fval = 0.0
                dfval = 0.0
                for q in range(n_nodes):
                    pr = _sigmoid(theta[q] - bj)
                    fval += Rj[q] * pr
                    dfval += Rj[q] * pr * (1.0 - pr)
                fval -= Sj
                dfval = -dfval
                if abs(dfval) < 1e-12:
                    break
                step = fval / dfval
                if step > 2.0:
                    step = 2.0
                elif step < -2.0:
                    step = -2.0
                bj -= step
                if abs(step) < 1e-6:
                    break
                max_delta = max(max_delta, abs(step))
            b[j] = bj
        if max_delta < 1e-4 and it > 5:
            break
    return b


# ─────────────────────────────────────────────────────────────────────────────
# A1：Junyi 能力校正判据
# ─────────────────────────────────────────────────────────────────────────────
def run_a1():
    log_path = "E:/learnflow/data/junyi/Log_Problem.csv"
    MIN_B_RESP = 500
    MAX_PER_ITEM_STORE = 4000  # 每题 B 半至多存 4000 条用于 IRT（远 >500，b_j 已收敛；控内存/耗时）

    # A 半聚合（融合信号）：aggA[ucid] = [n, corr, hint, sec, att, up, down, rep_sum]
    aggA = defaultdict(lambda: [0, 0, 0, 0.0, 0.0, 0, 0, 0.0])
    # B 半聚合：aggB[ucid] = [n, corr]
    aggB = defaultdict(lambda: [0, 0])

    uid_to_idx = {}
    ucid_to_idx = {}
    p_arr = array.array('i')
    j_arr = array.array('i')
    c_arr = array.array('i')
    stored_per_item = defaultdict(int)

    total_rows = 0
    b_rows = 0
    print(f"[A1] 流式读取 {log_path} ...", flush=True)
    with open(log_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        ix_uuid = header.index("uuid")
        ix_ucid = header.index("ucid")
        ix_rep = header.index("exercise_problem_repeat_session")
        ix_corr = header.index("is_correct")
        ix_hint = header.index("is_hint_used")
        ix_sec = header.index("total_sec_taken")
        ix_att = header.index("total_attempt_cnt")
        ix_up = header.index("is_upgrade")
        ix_down = header.index("is_downgrade")

        for row in reader:
            total_rows += 1
            if total_rows % 2000000 == 0:
                print(f"    ...已处理 {total_rows} 行，B 半响应 {b_rows}", flush=True)
            uuid = row[ix_uuid]
            ucid = row[ix_ucid]
            half = zlib.crc32(uuid.encode("utf-8")) & 1
            corr = _bit(row[ix_corr])
            if half == 1:
                a = aggB[ucid]
                a[0] += 1
                a[1] += corr
                if stored_per_item[ucid] < MAX_PER_ITEM_STORE:
                    ui = uid_to_idx.setdefault(uuid, len(uid_to_idx))
                    ci = ucid_to_idx.setdefault(ucid, len(ucid_to_idx))
                    p_arr.append(ui); j_arr.append(ci); c_arr.append(corr)
                    stored_per_item[ucid] += 1
                    b_rows += 1
            else:
                a = aggA[ucid]
                a[0] += 1
                a[1] += corr
                a[2] += _bit(row[ix_hint])
                a[3] += _num(row[ix_sec])
                a[4] += _num(row[ix_att])
                a[5] += _bit(row[ix_up])
                a[6] += _bit(row[ix_down])
                a[7] += _num(row[ix_rep])

    print(f"[A1] 完成流式读取：{total_rows} 行；B 半记录响应 {b_rows} 条", flush=True)

    qual_ucid = [u for u, a in aggB.items() if a[0] >= MIN_B_RESP]
    print(f"[A1] B 半 ≥{MIN_B_RESP} 作答的题数 = {len(qual_ucid)}", flush=True)

    new_cidx = {u: i for i, u in enumerate(qual_ucid)}
    cidx_to_ucid = {v: k for k, v in ucid_to_idx.items()}
    new_pidx = {}
    fp2 = array.array('i'); fj2 = array.array('i'); fc2 = array.array('i')
    for p, j, c in zip(p_arr, j_arr, c_arr):
        ucid = cidx_to_ucid[j]
        if ucid not in new_cidx:
            continue
        ni = new_cidx[ucid]
        np_ = new_pidx.setdefault(p, len(new_pidx))
        fp2.append(np_); fj2.append(ni); fc2.append(c)

    K = len(qual_ucid)
    M = len(new_pidx)
    n_resp_used = len(fp2)
    print(f"[A1] 合格题 K={K}，参与 person M={M}，用于 IRT 的响应数={n_resp_used}", flush=True)

    print("[A1] 拟合 IRT-1PL (Rasch MML-EM) ...", flush=True)
    b = fit_irt_1pl_scaled(fp2, fj2, fc2, M, K, n_iter=60, n_nodes=21)
    print("[A1] IRT 拟合完成。", flush=True)

    mean_abs_b = sum(abs(x) for x in b) / K

    success_diff_B = []
    for u in qual_ucid:
        n, corr = aggB[u]
        fail = (n - corr + 0.5) / (n + 1.0)
        success_diff_B.append(_logit(fail))  # 越高越难

    sig_success = []; sig_hint = []; sig_dur = []; sig_att = []
    sig_up = []; sig_down = []; sig_rep = []
    for u in qual_ucid:
        a = aggA.get(u)
        if a is None or a[0] == 0:
            sig_success.append(0.0); sig_hint.append(0.0); sig_dur.append(0.0)
            sig_att.append(0.0); sig_up.append(0.0); sig_down.append(0.0)
            sig_rep.append(0.0)
            continue
        n, corr, hint, sec, att, up, down, rep = a
        sig_success.append(1.0 - corr / n)
        sig_hint.append(hint / n)
        sig_dur.append(sec / n)
        sig_att.append(att / n)
        sig_up.append(up / n)
        sig_down.append(down / n)
        sig_rep.append(rep / n)
    fusion_A = _equal_weight_signed_fusion(
        [sig_success, sig_hint, sig_dur, sig_att, sig_up, sig_down, sig_rep],
        [+1, +1, +1, +1, -1, +1, +1])

    rho_fusion = V.spearman_rho(b, fusion_A)
    rho_success = V.spearman_rho(b, success_diff_B)

    print(f"[A1] Spearman(b_j, 融合_A)       = {rho_fusion:.4f}", flush=True)
    print(f"[A1] Spearman(b_j, 仅成功率_B)   = {rho_success:.4f}", flush=True)
    print(f"[A1] mean|b_j| = {mean_abs_b:.4f}", flush=True)

    return {
        "experiment": "A1",
        "dataset": "Junyi",
        "split_protocol": "O10 学生级留出：crc32(uuid) 奇偶切 A/B 半；融合信号仅 A 内、IRT 仅 B 内",
        "n_items": K,
        "n_persons_b_half": M,
        "n_responses_used_for_irt": n_resp_used,
        "min_b_half_responses": MIN_B_RESP,
        "mean_abs_b": mean_abs_b,
        "spearman_fusion": rho_fusion,
        "spearman_success": rho_success,
        "note": ("融合=A 半 O5 七信号等权符号校正融合(ECDF→logit)；仅成功率=B 半失败率 logit；"
                 "IRT b_j 与仅成功率同源于 B 半（不独立，计划已声明）；"
                 "每题 B 半 IRT 响应上限 %d（远>%d）。" % (MAX_PER_ITEM_STORE, MIN_B_RESP)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# A2：DBE-KT22 外生判据
# ─────────────────────────────────────────────────────────────────────────────
def run_a2():
    zip_path = "E:/learnflow/data/dbe_kt22/2_DBE_KT22_datafiles_100102_csv.zip"
    import zipfile
    from datetime import datetime

    q_diff = {}
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Questions.csv") as f:
            text = f.read().decode("utf-8")
    reader = csv.reader(text.splitlines())
    hq = next(reader)
    ix_id = hq.index("id")
    ix_diff = hq.index("difficulty")
    for row in reader:
        if not row:
            continue
        qid = row[ix_id].strip()
        dv = row[ix_diff].strip()
        try:
            q_diff[qid] = int(float(dv))
        except ValueError:
            continue
    print(f"[A2] 读取专家标签题数 = {len(q_diff)}", flush=True)

    agg = defaultdict(lambda: [0, 0, 0, 0.0, 0.0, 0.0, 0.0])  # n, corr, hint, selfrep, trust, dur, ndur
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Transaction.csv") as f:
            text = f.read().decode("utf-8")
    reader = csv.reader(text.splitlines())
    ht = next(reader)
    ix_qid = ht.index("question_id")
    ix_ans = ht.index("answer_state")
    ix_hint = ht.index("hint_used")
    ix_self = ht.index("difficulty_feedback")
    ix_trust = ht.index("trust_feedback")
    ix_st = ht.index("start_time")
    ix_et = ht.index("end_time")

    n_tx = 0
    for row in reader:
        if not row:
            continue
        qid = row[ix_qid].strip()
        if qid not in q_diff:
            continue
        n_tx += 1
        a = agg[qid]
        a[0] += 1
        a[1] += 1 if row[ix_ans].strip().lower() == "true" else 0
        a[2] += 1 if row[ix_hint].strip().lower() == "true" else 0
        a[3] += _num(row[ix_self])
        a[4] += _num(row[ix_trust])
        try:
            st = datetime.strptime(row[ix_st].strip()[:23], "%Y-%m-%d %H:%M:%S.%f")
            et = datetime.strptime(row[ix_et].strip()[:23], "%Y-%m-%d %H:%M:%S.%f")
            d = (et - st).total_seconds()
            if d > 0:
                a[5] += d
                a[6] += 1
        except Exception:
            pass

    print(f"[A2] 已处理交易 {n_tx} 条（限专家标注题）", flush=True)

    qids = [q for q in q_diff if q in agg and agg[q][0] > 0]
    K = len(qids)
    print(f"[A2] 同时含专家标签与交易的题数 = {K}", flush=True)

    expert = []
    sig_success = []; sig_hint = []; sig_self = []; sig_trust = []; sig_dur = []
    for q in qids:
        n, corr, hint, selfrep, trust, dur, ndur = agg[q]
        expert.append(q_diff[q])
        sig_success.append(1.0 - corr / n)
        sig_hint.append(hint / n)
        sig_self.append(selfrep / n)
        sig_trust.append(trust / n)
        sig_dur.append((dur / ndur) if ndur > 0 else 0.0)

    fusion = _equal_weight_signed_fusion(
        [sig_success, sig_hint, sig_self, sig_trust, sig_dur],
        [+1, +1, +1, -1, +1])

    rho_fusion = V.spearman_rho(fusion, expert)
    rho_success = V.spearman_rho(sig_success, expert)

    order = ["1", "2", "3"]
    tert = sorted(fusion)
    def _tercile(x):
        if x <= tert[len(tert) // 3]:
            return "1"
        if x <= tert[2 * len(tert) // 3]:
            return "2"
        return "3"
    ref_coding = [_tercile(x) for x in fusion]
    expert_str = [str(e) for e in expert]
    kappa = V.weighted_kappa(expert_str, ref_coding, order)

    print(f"[A2] Spearman(融合, 专家标签)        = {rho_fusion:.4f}", flush=True)
    print(f"[A2] Spearman(仅成功率, 专家标签)    = {rho_success:.4f}", flush=True)
    print(f"[A2] 加权 κ(专家标签 vs 行为三分位)  = {kappa:.4f}", flush=True)

    return {
        "experiment": "A2",
        "dataset": "DBE-KT22",
        "split_protocol": "题级 A/B 蓄水池留出（等权融合无参数，全样本评估，与 O4 一致）",
        "n_items": K,
        "n_transactions": n_tx,
        "weighted_kappa_expert_vs_reference": kappa,
        "spearman_fusion": rho_fusion,
        "spearman_success": rho_success,
        "note": ("DBE 仅单专家难度标注(Questions.difficulty)，无法算编码者间κ；"
                 "κ 为专家标签 vs 行为难度(融合)三分位参照编码的线性加权κ(1<2<3)。"
                 "Spearman 基于全 212 题（等权融合无泄漏风险）。"),
    }


def main():
    out_path = os.path.join(HERE, "m1_criteria_results_xcheck.json")
    a1 = run_a1()
    a2 = run_a2()
    result = {"a1": a1, "a2": a2}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已写出 {out_path}", flush=True)


if __name__ == "__main__":
    main()
