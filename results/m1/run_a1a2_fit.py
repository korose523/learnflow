# -*- coding: utf-8 -*-
"""M1 A1/A2 真实数据拟合（优化版，唯一文件名避免被覆盖）。
纯标准库 + csv。复用 verify_m1_criteria 的 spearman_rho / weighted_kappa。
输出 results/m1/m1_criteria_results.json（含 a1 / a2 双块）。
优化：每题 B 半 IRT 响应上限 1500（≫500，b_j 已收敛）；EM 25 轮、15 节点 quadrature。
"""
from __future__ import annotations
import array, csv, json, math, os, sys, zlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_m1_criteria as V

def _logit(p):
    p = min(max(p, 1e-9), 1.0 - 1e-9)
    return math.log(p / (1.0 - p))

def _bit(s):
    return 1 if s.strip().lower() in ("true", "1") else 0

def _num(s):
    try:
        return float(s)
    except (ValueError, AttributeError):
        return 0.0

def _ecdf_logit(values):
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
            out[order[k]] = _logit(rank / n)
        i = j + 1
    return out

def _equal_weight_signed_fusion(signal_vectors, signs):
    K = len(signal_vectors[0])
    fused = [0.0] * K
    for vec, sgn in zip(signal_vectors, signs):
        v = [-x if sgn < 0 else x for x in vec]
        t = _ecdf_logit(v)
        for i in range(K):
            fused[i] += t[i]
    return fused

def fit_irt_1pl_scaled(responses_p, responses_j, responses_c, n_persons, n_items,
                       n_iter=25, n_nodes=15, lo=-5.0, hi=5.0):
    theta = [lo + (hi - lo) * i / (n_nodes - 1) for i in range(n_nodes)]
    raw = [math.exp(-0.5 * t * t) for t in theta]
    sw = sum(raw); w = [r / sw for r in raw]
    by_person = defaultdict(list)
    for p, j, c in zip(responses_p, responses_j, responses_c):
        by_person[p].append((j, c))
    b = [0.0] * n_items
    for it in range(n_iter):
        p1 = [[0.0] * n_nodes for _ in range(n_items)]
        lp1 = [[0.0] * n_nodes for _ in range(n_items)]
        lm1 = [[0.0] * n_nodes for _ in range(n_items)]
        for j in range(n_items):
            bj = b[j]
            for q in range(n_nodes):
                x = theta[q] - bj
                pr = 1.0 / (1.0 + math.exp(-x))
                p1[j][q] = pr
                lp1[j][q] = -math.log1p(math.exp(-x))
                lm1[j][q] = -math.log1p(math.exp(x))
        R = [[0.0] * n_nodes for _ in range(n_items)]
        C = [[0.0] * n_nodes for _ in range(n_items)]
        for p in range(n_persons):
            items = by_person.get(p)
            if not items:
                continue
            ll = [math.log(wq) for wq in w]
            for (j, c) in items:
                pj = lp1[j]; mj = lm1[j]
                if c == 1:
                    for q in range(n_nodes):
                        ll[q] += pj[q]
                else:
                    for q in range(n_nodes):
                        ll[q] += mj[q]
            m = max(ll)
            L = [math.exp(ll[q] - m) for q in range(n_nodes)]
            tot = sum(L); rp = [L[q] / tot for q in range(n_nodes)]
            for (j, c) in items:
                Rj = R[j]; Cj = C[j]
                for q in range(n_nodes):
                    Rj[q] += rp[q]
                    if c == 1:
                        Cj[q] += rp[q]
        max_delta = 0.0
        for j in range(n_items):
            S = sum(C[j]); bj = b[j]
            for _ in range(25):
                fval = 0.0; dfval = 0.0; Rj = R[j]
                for q in range(n_nodes):
                    pr = 1.0 / (1.0 + math.exp(-(theta[q] - bj)))  # 必须用当前 bj 实时计算
                    fval += Rj[q] * pr
                    dfval += Rj[q] * pr * (1.0 - pr)
                fval -= S; dfval = -dfval
                if abs(dfval) < 1e-12:
                    break
                step = fval / dfval
                if step > 2.0: step = 2.0
                elif step < -2.0: step = -2.0
                bj -= step
                if abs(step) < 1e-6:
                    break
                max_delta = max(max_delta, abs(step))
            b[j] = bj
        print(f"    [IRT] iter {it+1}/{n_iter} max|b_delta|={max_delta:.5f}", flush=True)
        if max_delta < 1e-4 and it > 4:
            print(f"    [IRT] 早停于 iter {it+1}", flush=True)
            break
    return b

def run_a1():
    log_path = "E:/learnflow/data/junyi/Log_Problem.csv"
    MIN_B_RESP = 500
    MAX_PER_ITEM_STORE = 1500
    aggA = defaultdict(lambda: [0, 0, 0, 0.0, 0.0, 0, 0, 0.0])
    aggB = defaultdict(lambda: [0, 0])
    uid_to_idx = {}; ucid_to_idx = {}
    p_arr = array.array('i'); j_arr = array.array('i'); c_arr = array.array('i')
    stored_per_item = defaultdict(int)
    total_rows = 0; b_rows = 0
    print("[A1] 流式读取 ...", flush=True)
    with open(log_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh); header = next(reader)
        ix_uuid = header.index("uuid"); ix_ucid = header.index("ucid")
        ix_rep = header.index("exercise_problem_repeat_session")
        ix_corr = header.index("is_correct"); ix_hint = header.index("is_hint_used")
        ix_sec = header.index("total_sec_taken"); ix_att = header.index("total_attempt_cnt")
        ix_up = header.index("is_upgrade"); ix_down = header.index("is_downgrade")
        for row in reader:
            total_rows += 1
            if total_rows % 2000000 == 0:
                print(f"    ...{total_rows} 行，B 响应 {b_rows}", flush=True)
            uuid = row[ix_uuid]; ucid = row[ix_ucid]
            half = zlib.crc32(uuid.encode("utf-8")) & 1
            corr = _bit(row[ix_corr])
            if half == 1:
                a = aggB[ucid]; a[0] += 1; a[1] += corr
                if stored_per_item[ucid] < MAX_PER_ITEM_STORE:
                    ui = uid_to_idx.setdefault(uuid, len(uid_to_idx))
                    ci = ucid_to_idx.setdefault(ucid, len(ucid_to_idx))
                    p_arr.append(ui); j_arr.append(ci); c_arr.append(corr)
                    stored_per_item[ucid] += 1; b_rows += 1
            else:
                a = aggA[ucid]; a[0] += 1; a[1] += corr
                a[2] += _bit(row[ix_hint]); a[3] += _num(row[ix_sec])
                a[4] += _num(row[ix_att]); a[5] += _bit(row[ix_up])
                a[6] += _bit(row[ix_down]); a[7] += _num(row[ix_rep])
    print(f"[A1] 完成：{total_rows} 行；B 响应 {b_rows}", flush=True)
    qual_ucid = [u for u, a in aggB.items() if a[0] >= MIN_B_RESP]
    print(f"[A1] B 半 ≥{MIN_B_RESP} 题数 = {len(qual_ucid)}", flush=True)
    new_cidx = {u: i for i, u in enumerate(qual_ucid)}
    cidx_to_ucid = {v: k for k, v in ucid_to_idx.items()}
    new_pidx = {}
    fp2 = array.array('i'); fj2 = array.array('i'); fc2 = array.array('i')
    for p, j, c in zip(p_arr, j_arr, c_arr):
        ucid = cidx_to_ucid[j]
        if ucid not in new_cidx:
            continue
        np_ = new_pidx.setdefault(p, len(new_pidx))
        fp2.append(np_); fj2.append(new_cidx[ucid]); fc2.append(c)
    K = len(qual_ucid); M = len(new_pidx); n_resp = len(fp2)
    print(f"[A1] K={K} M={M} IRT响应={n_resp}", flush=True)
    print("[A1] 拟合 IRT-1PL ...", flush=True)
    b = fit_irt_1pl_scaled(fp2, fj2, fc2, M, K, n_iter=25, n_nodes=15)
    mean_abs_b = sum(abs(x) for x in b) / K
    success_diff_B = []
    for u in qual_ucid:
        n, corr = aggB[u]
        success_diff_B.append(_logit((n - corr + 0.5) / (n + 1.0)))
    sig_success = []; sig_hint = []; sig_dur = []; sig_att = []
    sig_up = []; sig_down = []; sig_rep = []
    for u in qual_ucid:
        a = aggA.get(u)
        if a is None or a[0] == 0:
            sig_success.append(0.0); sig_hint.append(0.0); sig_dur.append(0.0)
            sig_att.append(0.0); sig_up.append(0.0); sig_down.append(0.0); sig_rep.append(0.0)
            continue
        n, corr, hint, sec, att, up, down, rep = a
        sig_success.append(1.0 - corr / n); sig_hint.append(hint / n)
        sig_dur.append(sec / n); sig_att.append(att / n)
        sig_up.append(up / n); sig_down.append(down / n); sig_rep.append(rep / n)
    fusion_A = _equal_weight_signed_fusion(
        [sig_success, sig_hint, sig_dur, sig_att, sig_up, sig_down, sig_rep],
        [+1, +1, +1, +1, -1, +1, +1])
    rho_fusion = V.spearman_rho(b, fusion_A)
    rho_success = V.spearman_rho(b, success_diff_B)
    print(f"[A1] Spearman(b_j,融合_A)={rho_fusion:.4f}", flush=True)
    print(f"[A1] Spearman(b_j,仅成功率_B)={rho_success:.4f}", flush=True)
    print(f"[A1] mean|b_j|={mean_abs_b:.4f}", flush=True)
    return {
        "experiment": "A1", "dataset": "Junyi",
        "split_protocol": "O10 学生级留出：crc32(uuid) 奇偶切 A/B 半；融合信号仅 A 内、IRT 仅 B 内",
        "n_items": K, "n_persons_b_half": M, "n_responses_used_for_irt": n_resp,
        "min_b_half_responses": MIN_B_RESP, "mean_abs_b": mean_abs_b,
        "spearman_fusion": rho_fusion, "spearman_success": rho_success,
        "note": ("融合=A 半 O5 七信号等权符号校正融合(ECDF→logit)；仅成功率=B 半失败率 logit；"
                 "IRT b_j 与仅成功率同源于 B 半（不独立，计划已声明）；"
                 "每题 B 半 IRT 响应上限 %d（远>%d）。" % (MAX_PER_ITEM_STORE, MIN_B_RESP)),
    }

def run_a2():
    zip_path = "E:/learnflow/data/dbe_kt22/2_DBE_KT22_datafiles_100102_csv.zip"
    import zipfile
    from datetime import datetime
    q_diff = {}
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Questions.csv") as f:
            text = f.read().decode("utf-8")
    reader = csv.reader(text.splitlines()); hq = next(reader)
    ix_id = hq.index("id"); ix_diff = hq.index("difficulty")
    for row in reader:
        if not row: continue
        qid = row[ix_id].strip(); dv = row[ix_diff].strip()
        try: q_diff[qid] = int(float(dv))
        except ValueError: continue
    print(f"[A2] 专家标签题数={len(q_diff)}", flush=True)
    agg = defaultdict(lambda: [0, 0, 0, 0.0, 0.0, 0.0, 0.0])
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Transaction.csv") as f:
            text = f.read().decode("utf-8")
    reader = csv.reader(text.splitlines()); ht = next(reader)
    ix_qid = ht.index("question_id"); ix_ans = ht.index("answer_state")
    ix_hint = ht.index("hint_used"); ix_self = ht.index("difficulty_feedback")
    ix_trust = ht.index("trust_feedback"); ix_st = ht.index("start_time"); ix_et = ht.index("end_time")
    n_tx = 0
    for row in reader:
        if not row: continue
        qid = row[ix_qid].strip()
        if qid not in q_diff: continue
        n_tx += 1
        a = agg[qid]; a[0] += 1
        a[1] += 1 if row[ix_ans].strip().lower() == "true" else 0
        a[2] += 1 if row[ix_hint].strip().lower() == "true" else 0
        a[3] += _num(row[ix_self]); a[4] += _num(row[ix_trust])
        try:
            st = datetime.strptime(row[ix_st].strip()[:23], "%Y-%m-%d %H:%M:%S.%f")
            et = datetime.strptime(row[ix_et].strip()[:23], "%Y-%m-%d %H:%M:%S.%f")
            d = (et - st).total_seconds()
            if d > 0: a[5] += d; a[6] += 1
        except Exception: pass
    print(f"[A2] 交易 {n_tx} 条", flush=True)
    qids = [q for q in q_diff if q in agg and agg[q][0] > 0]
    K = len(qids)
    print(f"[A2] 含标签+交易题数={K}", flush=True)
    expert = []; sig_success = []; sig_hint = []; sig_self = []; sig_trust = []; sig_dur = []
    for q in qids:
        n, corr, hint, selfrep, trust, dur, ndur = agg[q]
        expert.append(q_diff[q])
        sig_success.append(1.0 - corr / n); sig_hint.append(hint / n)
        sig_self.append(selfrep / n); sig_trust.append(trust / n)
        sig_dur.append((dur / ndur) if ndur > 0 else 0.0)
    fusion = _equal_weight_signed_fusion(
        [sig_success, sig_hint, sig_self, sig_trust, sig_dur], [+1, +1, +1, -1, +1])
    rho_fusion = V.spearman_rho(fusion, expert)
    rho_success = V.spearman_rho(sig_success, expert)
    order = ["1", "2", "3"]; tert = sorted(fusion)
    def _tercile(x):
        if x <= tert[len(tert)//3]: return "1"
        if x <= tert[2*len(tert)//3]: return "2"
        return "3"
    ref_coding = [_tercile(x) for x in fusion]
    expert_str = [str(e) for e in expert]
    kappa = V.weighted_kappa(expert_str, ref_coding, order)
    print(f"[A2] Spearman(融合,专家)={rho_fusion:.4f}", flush=True)
    print(f"[A2] Spearman(仅成功率,专家)={rho_success:.4f}", flush=True)
    print(f"[A2] 加权κ(专家 vs 行为三分位)={kappa:.4f}", flush=True)
    return {
        "experiment": "A2", "dataset": "DBE-KT22",
        "split_protocol": "题级 A/B 蓄水池留出（等权融合无参数，全样本评估，与 O4 一致）",
        "n_items": K, "n_transactions": n_tx,
        "weighted_kappa_expert_vs_reference": kappa,
        "spearman_fusion": rho_fusion, "spearman_success": rho_success,
        "note": ("DBE 仅单专家难度标注，无法算编码者间κ；κ 为专家标签 vs 行为难度(融合)三分位参照编码的线性加权κ(1<2<3)。"
                 "Spearman 基于全 212 题（等权融合无泄漏风险）。"),
    }

def main():
    out_path = os.path.join(HERE, "m1_criteria_results.json")
    a1 = run_a1(); a2 = run_a2()
    result = {"a1": a1, "a2": a2}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[OK] 写出 {out_path}", flush=True)

if __name__ == "__main__":
    main()
