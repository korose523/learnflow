# -*- coding: utf-8 -*-
"""
aipw_run.py — LearnFlow M1 因果侧升级：离策略剂量—反应 AIPW/DR 估计
======================================================================

冻结方案（唯一权威规格）: E:/learnflow/docs/LearnFlow_研究总档.md  (编号 LF-CIS-2026-09-22)
目标论文:                E:/learnflow/docs/M1_难度可公度性与最优错误率_完整稿.md §8

本脚本严格按冻结方案执行：
  * 处理变量 d = k/20, k = 结局窗之前最近 W=20 条同知识点作答的错误条数（整数 0..20）。
    处理窗与结局窗严格互斥，间隔 >=1 条其他作答。纳入条件：该学习者在该知识点累计
    作答 >= 20 条且处理窗无缺失。
  * 结局 Y1(主) = 结局窗（处理窗之后前 20 条）内“首次连续 3 题全对”所需步数（越高越慢），
    截断为窗长上限（生存式处理）。Y2(次) = 结局窗末 5 题正确率。
    稳健性变换：主分析用 Y1 的“题内秩变换”；另报 log(1+T) 与原始步数。
  * 个体单位 = 学习者 x 知识点；标准误按学习者聚类。
  * 混杂变量（冻结，事后不增删）：前测能力 θ̂(处理窗前作答)、题目难度代理、知识点哈希桶+
    技能数、处理窗前累计作答、会话结构、提示使用率(同时作 X 与分层)、呈现顺序。
  * 主估计量 AIPW/DR：对每档 d 估计 mu(d)=E[Y|do(d)]，m̂=结局回归(RF,交叉拟合)，
    ê=广义倾向得分(21 档离散,多分类 RF,交叉拟合)。
  * 对照估计量：IPW-only / 回归-only / 同 k 档最近邻匹配。
  * 推断：学习者聚类 bootstrap(>=500)，逐点 95% CI；BH 控 FDR(q=0.05)，同时报未校正。
  * 主检验：H-c1(方向/内部最优) H-c2(位置 0.1587/0.193) H-c3(外推/分层)。
  * 阳性对照 P-pos-1(错误率0 vs 1 应慢于中段)；阴性对照 P-neg-2(时间倒置窗应无显著效应)。
  * 诚实铁律：阴性结果写“未检出剂量—反应”，绝不写“证明不存在”；阴性对照显著须如实
    报告并把主结论降级为“关联性证据”；不做未声明亚组分析。

运行环境（Windows, E:/ 路径）：
  * venv: C:/Users/mac/.workbuddy/binaries/python/envs/default/Scripts/python.exe
  * 需 numpy + scikit-learn（已装 1.9.1）。
  * 可复现：所有分桶/分半使用 zlib.crc32（非内置 hash）；bootstrap/RNG 固定 SEED。

输出（E:/learnflow/results/m1/aipw/）：
  * aipw_results.json — 结构化结果
  * aipw_audit.log   — §9 留痕（append-only）：冻结文档 SHA256+mtime(未提交状态)、
                       各输入文件 SHA256、脚本 SHA256、首跑日志(运行时间/脚本哈希/
                       输入哈希/输出哈希)。

用法：
  python aipw_run.py                 # 全量三数据集
  python aipw_run.py --dataset assist09
  python aipw_run.py --debug         # 小样本/少 bootstrap/少树，仅 assist09+小 junyi 快速验证
"""

import os, sys, json, csv, math, hashlib, argparse, time, random
from collections import defaultdict
from zlib import crc32

import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

# ----------------------------------------------------------------------------
# 全局配置（全部对应冻结方案）
# ----------------------------------------------------------------------------
W             = 20      # 处理窗宽（条）
GAP_MIN       = 1       # 处理窗与结局窗最小间隔（条）
OUT_W         = 20      # 结局窗宽（条）
K_MAX         = 20      # 错误条数上界 -> 21 档
N_DOSES       = K_MAX + 1
MIN_UNIT_ANS  = W + GAP_MIN + OUT_W          # 构成一个窗对所需最少作答 = 41
FOLDS         = 5       # 交叉拟合折数（按学习者聚类分折）
BOOT          = 500     # 聚类 bootstrap 次数
SEED          = 42
EPS_E         = 0.01    # 倾向得分下界（防除零/极端权重）
WT_CAP        = 10.0    # 权重截断（稳健性 AIPW_trunc）
N_SAMPLE_JUNYI = 150000 # Junyi 合格单元抽样目标（报告实际 N 与抽样方式）
SESSION_GAP_S = 1800.0  # 会话间隔阈值（秒）：>30 分钟视为跨会话（仅有时间戳数据）

RF_NEST       = 120
RF_MIN_LEAF   = 2

# 路径
DOC_PATH   = "E:/learnflow/docs/LearnFlow_研究总档.md"
OUT_DIR    = "E:/learnflow/results/m1/aipw"
JSON_PATH  = os.path.join(OUT_DIR, "aipw_results.json")
AUDIT_PATH = os.path.join(OUT_DIR, "aipw_audit.log")

ASSIST_CSV = "E:/learnflow/data/assist09_corrected.csv"
DBE_TXN    = "E:/learnflow/data/dbe_kt22/csv/Transaction.csv"
DBE_QKC    = "E:/learnflow/data/dbe_kt22/csv/Question_KC_Relationships.csv"
DBE_KC     = "E:/learnflow/data/dbe_kt22/csv/KCs.csv"
JUNYI_LOG  = "E:/learnflow/data/junyi/Log_Problem.csv"
JUNYI_INFO = "E:/learnflow/data/junyi/Info_Content.csv"

rng = np.random.RandomState(SEED)


# ----------------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------------
def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def ckey(s):
    """确定性 64 位整数键，避免内置 hash 的不可复现性。"""
    return (crc32(s.encode("utf-8")) & 0xFFFFFFFF)


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1.0 - p))


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def open_csv(path, enc_first=("utf-8", "cp1252", "latin-1")):
    """探测编码后打开。注意：UnicodeDecodeError 发生在迭代时而非 open() 时，
    故必须读二进制样本来探测，不能只 try open()。utf-8 失败即回退 latin-1
    （latin-1 对任意字节流都可解码，保证迭代不再抛错；文本字段仅用于分层标签）。"""
    with open(path, "rb") as f:
        sample = f.read(1 << 20)
    try:
        sample.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        enc = "latin-1"
    # errors="replace" 兜底：坏字节可能位于 1MB 探测样本之外（assist09 实测即如此，
    # 0x80 出现在远端）；仅影响文本分层标签（显示为 U+FFFD），数值/布尔字段全 ASCII 不受影响。
    return open(path, "r", encoding=enc, newline="", errors="replace")


def rank_within(values):
    """组内序数秩（1..n），保持大小顺序，用于题内秩变换。"""
    v = np.asarray(values, dtype=float)
    order = v.argsort()
    ranks = np.empty(len(v), dtype=float)
    ranks[order] = np.arange(1, len(v) + 1)
    return ranks


def ts_ymdh_to_epoch(y, mo, d, h, mi, s):
    """(年,月,日,时,分,秒) -> epoch 秒；days_from_civil 纯算术实现，单调且跨分钟边界正确。"""
    yy = y - (1 if mo <= 2 else 0)
    era = yy // 400
    yoe = yy - era * 400
    doy = (153 * (mo + (-3 if mo > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    return days * 86400 + h * 3600 + mi * 60 + s


# ----------------------------------------------------------------------------
# 数据加载：返回 list[unit]，每个 unit 是一个 dict：
#   { 'learner': str, 'kc': str, 'seq': list[(correct, tsec, hint_feat, diff_feat, pos, item_type)], ... }
# 其中 seq 已按时间/次序排序；后续统一抽取窗对。
# ----------------------------------------------------------------------------

def load_assist09():
    """assist09：无时间戳。按 (user_id, skill_id) 为单位；次序用 opportunity 再按行序。"""
    units = defaultdict(list)  # key -> list of (correct, hint_rate, answer_type, position, opp)
    order = defaultdict(int)
    with open_csv(ASSIST_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            uid = row.get("user_id", "")
            kc = row.get("skill_id", "")
            if uid == "" or kc == "":
                continue
            c = row.get("correct", "").strip()
            if c not in ("0", "1"):
                c = None
            else:
                c = int(c)
            hc = safe_float(row.get("hint_count", "0"), 0.0)
            ht = safe_float(row.get("hint_total", "0"), 0.0)
            hr = (hc / ht) if ht > 0 else 0.0
            at = row.get("answer_type", "").strip()
            try:
                opp = int(row.get("opportunity", "0"))
            except Exception:
                opp = 0
            units[(uid, kc)].append((c, hr, at, opp, order[(uid, kc)]))
            order[(uid, kc)] += 1
    out = []
    for (uid, kc), seq in units.items():
        seq.sort(key=lambda t: (t[3], t[4]))  # opportunity 升序，再按行序
        out.append({"learner": uid, "kc": kc, "seq": [t[:3] for t in seq],
                    "has_ts": False, "item_type_raw": [t[2] for t in seq]})
    return out


def load_dbe():
    # 先建 question_id -> [kc_id,...]
    q2kcs = defaultdict(list)
    with open_csv(DBE_QKC) as f:
        r = csv.DictReader(f)
        for row in r:
            q = (row.get("question_id") or "").strip()
            k = (row.get("knowledgecomponent_id") or "").strip()
            if q and k:
                q2kcs[q].append(k)
    units = defaultdict(list)  # (student_id, kc) -> list
    order = defaultdict(int)
    from datetime import datetime
    def parse_ts(s):
        s = (s or "").strip()
        if not s:
            return None
        s2 = s.replace("Z", "").replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(s2[:19], fmt).timestamp()
            except Exception:
                continue
        return None
    with open_csv(DBE_TXN) as f:
        r = csv.DictReader(f)
        for row in r:
            sid = (row.get("student_id") or "").strip()
            qid = (row.get("question_id") or "").strip()
            if sid == "":
                continue
            kcs = q2kcs.get(qid)
            if not kcs:
                continue
            st = row.get("answer_state", "").strip().lower()
            c = 1 if st in ("true", "1", "t") else (0 if st in ("false", "0", "f") else None)
            hu = row.get("hint_used", "").strip().lower()
            hint = 1.0 if hu in ("true", "1", "t") else 0.0
            dfb = safe_float(row.get("difficulty_feedback", ""), np.nan)
            ts = parse_ts(row.get("start_time", ""))
            for kc in kcs:
                units[(sid, kc)].append((c, hint, dfb, ts, order[(sid, kc)]))
                order[(sid, kc)] += 1
    out = []
    for (sid, kc), seq in units.items():
        seq.sort(key=lambda t: (t[3] if t[3] is not None else 0, t[4]))
        out.append({"learner": sid, "kc": kc,
                    "seq": [(t[0], t[1], t[2]) for t in seq],  # (correct, hint, diff_fb)
                    "has_ts": any(t[3] is not None for t in seq),
                    "ts": [t[3] for t in seq]})
    return out


def load_junyi(sample_target=N_SAMPLE_JUNYI):
    """Junyi：2.8GB，必须流式两遍。第一遍计数 (uuid,ucid) 合格单元；第二遍收集合格单元序列。"""
    # ucid -> (difficulty, level3_id)
    info = {}
    with open_csv(JUNYI_INFO) as f:
        r = csv.DictReader(f)
        for row in r:
            u = (row.get("ucid") or "").strip()
            if not u:
                continue
            diff = row.get("difficulty", "").strip()
            l3 = row.get("level3_id", "").strip()
            info[u] = (diff, l3)

    # 第一遍：计数（内存安全：uint64 数组 + np.unique，避免千万级 dict）
    from array import array
    keys1 = array("Q")
    rows1 = 0
    with open_csv(JUNYI_LOG) as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            rows1 += 1
            if len(row) < 9:
                continue
            uuid = row[1].strip()
            ucid = row[2].strip()
            if not uuid or not ucid:
                continue
            keys1.append((ckey(uuid) << 32) | ckey(ucid))
    uniq, cnts = np.unique(np.frombuffer(keys1, dtype=np.uint64), return_counts=True)
    del keys1
    elig_arr = uniq[cnts >= MIN_UNIT_ANS]
    eligible = set(elig_arr.tolist())
    print(f"[junyi] pass1 done: rows={rows1}, pairs={len(uniq)}, eligible(>= {MIN_UNIT_ANS} 条)={len(eligible)}", flush=True)
    del uniq, cnts, elig_arr

    # 第二遍：收集合格单元
    store = {}
    rows2 = 0
    with open_csv(JUNYI_LOG) as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            rows2 += 1
            if len(row) < 9:
                continue
            uuid = row[1].strip()
            ucid = row[2].strip()
            if not uuid or not ucid:
                continue
            key = (ckey(uuid) << 32) ^ ckey(ucid)
            if key not in eligible:
                continue
            # 时间：YYYYMMDDHHMMSS -> epoch 秒（纯算术，跨分钟边界仍单调）
            s = row[0]
            try:
                ts = ts_ymdh_to_epoch(int(s[0:4]), int(s[5:7]), int(s[8:10]),
                                      int(s[11:13]), int(s[14:16]), int(s[17:19]))
            except Exception:
                ts = 0
            c = 1 if row[6].strip().lower() in ("true", "1", "t") else 0
            hint = 1.0 if row[10].strip().lower() in ("true", "1", "t") else 0.0
            try:
                att = int(row[8])
            except Exception:
                att = 1
            rec = store.get(key)
            if rec is None:
                rec = {"uuid": uuid, "ucid": ucid, "ts": [], "cor": [], "att": [], "hint": []}
                store[key] = rec
            rec["ts"].append(ts)
            rec["cor"].append(c)
            rec["att"].append(att)
            rec["hint"].append(hint)
    del eligible

    # 组装 unit 列表（每单元选一个确定性窗对，见 extract_window）
    out = []
    for rec in store.values():
        n = len(rec["ts"])
        seq = list(zip(rec["cor"], rec["hint"], [np.nan] * n))  # (correct, hint, diff=NA)
        ts = rec["ts"]
        # 用 (ts, att, idx) 排序
        order_idx = sorted(range(n), key=lambda i: (ts[i], rec["att"][i], i))
        seq_sorted = [seq[i] for i in order_idx]
        ts_sorted = [ts[i] for i in order_idx]
        diff, l3 = info.get(rec["ucid"], ("", ""))
        out.append({"learner": rec["uuid"], "kc": rec["ucid"],
                    "seq": seq_sorted, "has_ts": True, "ts": ts_sorted,
                    "item_type_raw": [l3] * n, "diff_raw": diff})
    return out


# ----------------------------------------------------------------------------
# 窗对抽取 + 特征/结局构造（统一于三数据集）
# ----------------------------------------------------------------------------
def build_observations(units, dataset_name, diff_map=None, global_kc_acc=None, reverse=False):
    """
    对每个 unit 抽取一个确定性窗对（处理窗 + 间隔 + 结局窗），构造：
      D(int 0..20 错误条数), Y_raw(步数), Y_log, 以及特征向量 X, 分层字段。
    返回 obs 列表 + 元数据（kc 数、是否有时戳、提示可用、难度可用）。
    """
    obs = []
    kc_to_units = defaultdict(list)
    for u in units:
        seq = u["seq"]
        n = len(seq)
        if n < MIN_UNIT_ANS:
            continue
        # 确定性选窗（按 unit 串的 crc32）
        uid_str = f"{u['learner']}|{u['kc']}"
        if reverse:
            # 时间倒置阴性对照：结局取最早 20 条，处理取其后 20 条（处理发生在结局之后）
            if n < 40:
                continue
            ok = all(seq[j][0] is not None for j in range(0, 40))
            if not ok:
                continue
            e = 39
            treat = seq[20:40]
            outcome = seq[0:20]
            pre = seq[0:20]   # 负对照中“处理前”即等于结局窗（仅用于机械填充管线）
        else:
            valid_es = []
            for e0 in range(W - 1, n - OUT_W - GAP_MIN):  # e+1 间隔, e+2..e+21 结局窗
                # 处理窗 [e0-19, e0], 间隔 e0+1, 结局窗 [e0+2, e0+21]
                if e0 + OUT_W + 1 > n - 1:
                    continue
                ok = True
                for j in range(e0 - 19, e0 + 1):
                    if seq[j][0] is None:
                        ok = False; break
                if ok:
                    for j in range(e0 + 2, e0 + OUT_W + 2):
                        if seq[j][0] is None:
                            ok = False; break
                if ok:
                    valid_es.append(e0)
            if not valid_es:
                continue
            e = valid_es[ckey(uid_str) % len(valid_es)]
            treat = seq[e - 19: e + 1]
            outcome = seq[e + 2: e + OUT_W + 2]
            pre = seq[0: e - 19]

        k = sum(1 for (cc, _, _) in treat if cc == 0)   # 错误条数
        D = k  # 0..20

        # 结局 Y1：首次连续3题全对所需步数；否则 = 窗长（删失）
        T = OUT_W
        for j in range(0, OUT_W - 2):
            if outcome[j][0] == 1 and outcome[j + 1][0] == 1 and outcome[j + 2][0] == 1:
                T = j + 3
                break
        Y_raw = float(T)
        # Y2 末5题正确率
        last5 = outcome[-5:]
        Y2 = float(sum(1 for (cc, _, _) in last5 if cc == 1)) / 5.0

        # ---- 混杂特征 ----
        # 1) 前测能力 θ̂：处理窗前作答的（crc32 分半避免与结局同源）经验 logit 正确率
        if len(pre) >= 5:
            half = [(i, x) for i, x in enumerate(pre) if x[0] is not None
                    and (ckey(uid_str + ":" + str(i)) & 1) == (ckey(uid_str) & 1)]
            if len(half) >= 3:
                s = sum(1 for (_, x) in half if x[0] == 1)
                theta = logit((s + 0.5) / (len(half) + 1.0))
            else:
                s = sum(1 for x in pre if x[0] == 1)
                theta = logit((s + 0.5) / (len(pre) + 1.0))
        elif len(pre) > 0:
            s = sum(1 for x in pre if x[0] == 1)
            theta = logit((s + 0.5) / (len(pre) + 1.0))
        else:
            theta = 0.0  # 退回全局均值（缺预治疗史）；下游标准化会吸收

        # 2) 题目难度代理
        if dataset_name == "assist09":
            diff = global_kc_acc.get(u["kc"], 0.5) if global_kc_acc else 0.5
        elif dataset_name == "dbe":
            # difficulty_feedback 在处理窗前作答的均值
            pre_d = [x[2] for x in pre if x[2] == x[2]]  # 非 nan
            diff = float(np.nanmean(pre_d)) if pre_d else 3.0
        else:  # junyi
            d = u.get("diff_raw", "")
            diff = safe_float(d, np.nan)
            if not (diff == diff):  # nan
                diff = 0.5
        # 3) 知识点哈希桶
        kc_bucket = ckey(u["kc"]) % 50
        # 4) 技能数（单技能=1；本实现单位即单 KC，恒为 1；多技能维度由 item_type 承载）
        skill_count = 1
        # 5) 处理窗前累计作答条数（log1p）
        cum_before = math.log1p(max(0, e - 19))
        # 6) 会话结构
        session_gap_bucket = -1.0
        cross_session = 0.0
        if u.get("has_ts") and "ts" in u:
            ts = u["ts"]
            # 处理窗首条前一条（e-20）与处理窗首条（e-19）的间隔
            t_prev = ts[e - 20] if (e - 20) >= 0 else ts[e - 19]
            t_first = ts[e - 19]
            gap = abs(t_first - t_prev)
            if gap > SESSION_GAP_S:
                session_gap_bucket = 3.0
                cross_session = 1.0
            elif gap > 300.0:
                session_gap_bucket = 2.0
            elif gap > 60.0:
                session_gap_bucket = 1.0
            else:
                session_gap_bucket = 0.0
            # 处理窗内是否跨会话
            for j in range(e - 19, e):
                if abs(ts[j + 1] - ts[j]) > SESSION_GAP_S:
                    cross_session = 1.0
                    break
        # 7) 提示使用率（处理窗内；三数据集均有提示字段：assist09=hint_count/hint_total，
        #    dbe=hint_used，junyi=is_hint_used(Log_Problem.csv 第 10 列)）
        hint_avail = True
        hrs = [x[1] for x in treat]
        hint_rate = float(np.mean(hrs)) if hrs else 0.0
        # 8) 呈现顺序（处理窗在 KC 序列中的相对位置）
        pres_order = (e - 19) / max(1, n - 1)

        X = [theta, diff, float(kc_bucket), float(skill_count), cum_before,
             session_gap_bucket, cross_session, hint_rate, pres_order]

        # 分层字段
        item_type = None
        if dataset_name == "assist09":
            item_type = outcome[0][2] if False else (u["item_type_raw"][e] if e < len(u["item_type_raw"]) else "")
        elif dataset_name == "junyi":
            item_type = u["item_type_raw"][0] if u["item_type_raw"] else ""
        else:
            item_type = ""

        obs.append({
            "learner": u["learner"], "kc": u["kc"],
            "D": D, "Y_raw": Y_raw, "Y2": Y2,
            "X": X, "hint_rate": hint_rate, "hint_avail": hint_avail,
            "item_type": str(item_type), "session_avail": u.get("has_ts", False),
        })
        kc_to_units[u["kc"]].append(len(obs) - 1)

    # 题内秩变换（主分析 Y）
    for kc, idxs in kc_to_units.items():
        if len(idxs) < 2:
            for i in idxs:
                obs[i]["Y_rank"] = obs[i]["Y_raw"]
            continue
        vals = np.array([obs[i]["Y_raw"] for i in idxs])
        rk = rank_within(vals)
        for r, i in zip(rk, idxs):
            obs[i]["Y_rank"] = float(r)

    meta = {
        "n_units_raw": len(units),
        "n_obs": len(obs),
        "hint_available": True,
        "session_available": any(o["session_avail"] for o in obs),
    }
    return obs, meta


# ----------------------------------------------------------------------------
# AIPW/DR 交叉拟合
# ----------------------------------------------------------------------------
def cross_fit(X, Y, D, learner_ids):
    """
    X: (n, p) 标准化特征
    Y: (n,) 结局
    D: (n,) 整数剂量 0..20
    返回 m_hat (n,21), e_hat (n,21)（已 clip 到 [EPS,1]）
    交叉拟合按学习者聚类分折。
    """
    n = X.shape[0]
    # 按学习者分折
    uniq_lr = sorted(set(learner_ids))
    fold_of_lr = {lr: i % FOLDS for i, lr in enumerate(uniq_lr)}
    fold = np.array([fold_of_lr[l] for l in learner_ids])

    m_hat = np.zeros((n, N_DOSES))
    e_hat = np.zeros((n, N_DOSES))

    dose_grid = np.arange(N_DOSES)
    for fd in range(FOLDS):
        tr = np.where(fold != fd)[0]
        te = np.where(fold == fd)[0]
        if len(tr) == 0 or len(te) == 0:
            continue
        # ---- 结局回归 m̂(d,X) ----
        mdl = RandomForestRegressor(n_estimators=RF_NEST, min_samples_leaf=RF_MIN_LEAF,
                                    n_jobs=-1, random_state=SEED)
        Xtr = np.hstack([X[tr], D[tr].reshape(-1, 1)])
        mdl.fit(Xtr, Y[tr])
        Xte_grid = np.hstack([np.repeat(X[te], N_DOSES, axis=0),
                              np.tile(dose_grid, len(te)).reshape(-1, 1)])
        pred = mdl.predict(Xte_grid).reshape(len(te), N_DOSES)
        m_hat[te] = pred
        # ---- 广义倾向得分 ê(d|X) ----
        clf = RandomForestClassifier(n_estimators=RF_NEST, min_samples_leaf=RF_MIN_LEAF,
                                     n_jobs=-1, random_state=SEED)
        clf.fit(X[tr], D[tr])
        # 对齐到 0..20 全 21 类
        full = np.zeros((len(te), N_DOSES))
        present = {int(c): i for i, c in enumerate(clf.classes_)}
        proba = clf.predict_proba(X[te])
        for c, idx in present.items():
            if 0 <= c < N_DOSES:
                full[:, c] = proba[:, idx]
        e_hat[te] = full

    e_hat = np.clip(e_hat, EPS_E, 1.0)
    return m_hat, e_hat


def compute_psi(X, Y, D, learner_ids, Y_variant="Y_rank"):
    """计算四种估计量的逐单位贡献（用于 bootstrap 与权重截断）。"""
    m_hat, e_hat = cross_fit(X, Y, D, learner_ids)
    Dcol = D.reshape(-1, 1)
    onehot = (Dcol == np.arange(N_DOSES).reshape(1, -1)).astype(float)  # (n,21)
    # AIPW
    psi_aipw = onehot * (Y.reshape(-1, 1) - m_hat) / e_hat + m_hat
    # AIPW 权重截断
    w = onehot / e_hat
    w_clip = np.minimum(w, WT_CAP)
    psi_aipw_trunc = w_clip * (Y.reshape(-1, 1) - m_hat) + m_hat
    # 回归-only
    psi_reg = m_hat.copy()
    # IPW Hajek 用 w（存 w 供 bootstrap 比率计算）
    return {"m_hat": m_hat, "e_hat": e_hat, "onehot": onehot, "w": w,
            "psi_aipw": psi_aipw, "psi_aipw_trunc": psi_aipw_trunc, "psi_reg": psi_reg}


def estimate_from_psi(P, learner_ids, Y, D, n, boot=True):
    """由 psi 计算点估计 + 聚类 bootstrap 95% CI。返回 dict of {est_name: {d: {point,lo,hi}}}。"""
    res = {}
    # ---- AIPW ----
    mu_aipw = P["psi_aipw"].mean(axis=0)
    # ---- AIPW trunc ----
    mu_aipw_t = P["psi_aipw_trunc"].mean(axis=0)
    # ---- regression ----
    mu_reg = P["psi_reg"].mean(axis=0)
    # ---- IPW (Hajek) ----
    w = P["w"]
    num = (w * Y.reshape(-1, 1)).sum(axis=0)
    den = w.sum(axis=0)
    mu_ipw = num / np.where(den > 0, den, np.nan)
    # ---- matching (同 k 档最近邻, 参考剂量=众数) ----
    mu_match, _ = matching_estimator(X_global, Y, D)

    if not boot:
        return {"aipw": mu_aipw, "aipw_trunc": mu_aipw_t, "reg": mu_reg,
                "ipw": mu_ipw, "match": mu_match}

    # 聚类 bootstrap
    lr_to_idx = defaultdict(list)
    for i, l in enumerate(learner_ids):
        lr_to_idx[l].append(i)
    lrs = list(lr_to_idx.keys())
    B = BOOT
    boot_aipw = np.empty((B, N_DOSES))
    boot_aipw_t = np.empty((B, N_DOSES))
    boot_reg = np.empty((B, N_DOSES))
    boot_ipw = np.empty((B, N_DOSES))
    boot_match = np.empty((B, N_DOSES))

    # 预存匹配 NN 索引（基于标准化 X）
    nn_idx, ref_mask, ref_units = _matching_prep()

    for b in range(B):
        samp = rng.choice(lrs, size=len(lrs), replace=True)
        sel = np.concatenate([lr_to_idx[l] for l in samp])
        # AIPW
        boot_aipw[b] = P["psi_aipw"][sel].mean(axis=0)
        boot_aipw_t[b] = P["psi_aipw_trunc"][sel].mean(axis=0)
        boot_reg[b] = P["psi_reg"][sel].mean(axis=0)
        # IPW Hajek
        wb = w[sel]
        numb = (wb * Y[sel].reshape(-1, 1)).sum(axis=0)
        denb = wb.sum(axis=0)
        boot_ipw[b] = numb / np.where(denb > 0, denb, np.nan)
        # matching
        boot_match[b] = _matching_boot(Y, D, sel, nn_idx, ref_mask, ref_units)

    def ci(arr):
        lo = np.nanpercentile(arr, 2.5, axis=0)
        hi = np.nanpercentile(arr, 97.5, axis=0)
        return lo, hi

    out = {}
    for name, point, boots in [("aipw", mu_aipw, boot_aipw),
                               ("aipw_trunc", mu_aipw_t, boot_aipw_t),
                               ("reg", mu_reg, boot_reg),
                               ("ipw", mu_ipw, boot_ipw),
                               ("match", mu_match, boot_match)]:
        lo, hi = ci(boots)
        out[name] = {"point": point, "lo": lo, "hi": hi, "boot": boots}
    return out


# ---- 匹配估计量（对照）----
X_global = None  # 在 run_dataset 中设置
D_global = None
_match_nn = None

def _matching_prep():
    global _match_nn
    from sklearn.neighbors import NearestNeighbors
    ref_dose = int(np.bincount(D_global).argmax())
    ref_mask = (D_global == ref_dose)
    if ref_mask.sum() == 0:
        ref_dose = 0
        ref_mask = (D_global == ref_dose)
    # 参考单元集合
    ref_X = X_global[ref_mask]
    nn = NearestNeighbors(n_neighbors=1).fit(ref_X)
    # 每个非参考单元的最近邻（在参考单元中）
    others = ~ref_mask
    if others.sum() == 0:
        _match_nn = (ref_dose, None, ref_mask, np.where(ref_mask)[0])
        return None, ref_mask, np.where(ref_mask)[0]
    _, idx = nn.kneighbors(X_global[others])
    nn_idx = np.full(X_global.shape[0], -1, dtype=int)
    nn_idx[others] = np.where(ref_mask)[0][idx.flatten()]
    _match_nn = (ref_dose, nn_idx, ref_mask, np.where(ref_mask)[0])
    return nn_idx, ref_mask, np.where(ref_mask)[0]


def matching_estimator(X, Y, D):
    ref_dose, nn_idx, ref_mask, ref_units = _match_nn if _match_nn is not None else _matching_prep()
    ref_mean = Y[ref_units].mean() if len(ref_units) else 0.0
    mu = np.full(N_DOSES, np.nan)
    for d in range(N_DOSES):
        mask = (D == d)
        if mask.sum() == 0:
            continue
        if d == ref_dose or nn_idx is None:
            mu[d] = ref_mean  # 参考剂量档按构造差分为 0
            continue
        diff = Y[mask] - Y[nn_idx[mask]]
        mu[d] = ref_mean + diff.mean()
    return mu, ref_dose


def _matching_boot(Y, D, sel, nn_idx, ref_mask, ref_units):
    inter = np.intersect1d(sel, ref_units)
    ref_mean = Y[inter].mean() if len(inter) else np.nan
    mu = np.full(N_DOSES, np.nan)
    if not len(inter):
        return mu
    ref_dose = int(np.bincount(D[ref_units]).argmax()) if len(ref_units) else -1
    for d in range(N_DOSES):
        mask = (D[sel] == d)
        if mask.sum() == 0:
            continue
        local_idx = sel[mask]
        if d == ref_dose or nn_idx is None:
            mu[d] = ref_mean  # 参考剂量档按构造差分为 0
            continue
        diff = Y[local_idx] - Y[nn_idx[local_idx]]
        mu[d] = ref_mean + diff.mean()
    return mu


# ----------------------------------------------------------------------------
# 假设检验
# ----------------------------------------------------------------------------
def test_hc1_hc2(mu_boot, mu_point):
    """H-c1 方向(内部最优); H-c2 位置(85%目标 0.1587 / 先行研究 0.193 对应的 k 档)。"""
    interior = list(range(1, N_DOSES - 1))
    # H-c2 目标档集随 W 缩放：0.1587*W 与 0.193*W 的整数档（W=20 -> {3,4}）
    star_set = sorted({int(0.1587 * W), int(round(0.193 * W))})
    # d* 点估计
    d_star = int(np.nanargmin(mu_point[interior])) + 1
    # bootstrap: 每复制内部极小点 + 是否低于两端点
    below0 = 0
    below20 = 0
    star_in_set = 0
    B = mu_boot.shape[0]
    star_list = []
    for b in range(B):
        row = mu_boot[b]
        if np.any(np.isnan(row)):
            continue
        sb = int(np.nanargmin(row[interior])) + 1
        star_list.append(sb)
        if row[sb] < row[0]:
            below0 += 1
        if row[sb] < row[N_DOSES - 1]:
            below20 += 1
        if sb in star_set:
            star_in_set += 1
    # 仅统计非全 nan 的复制
    valid = sum(1 for s in star_list)
    frac_below0 = below0 / max(1, valid)
    frac_below20 = below20 / max(1, valid)
    frac_set = star_in_set / max(1, valid)
    star_arr = np.array(star_list)
    star_lo = int(np.percentile(star_arr, 2.5)) if valid else None
    star_hi = int(np.percentile(star_arr, 97.5)) if valid else None
    hc1_supported = (frac_below0 >= 0.95) and (frac_below20 >= 0.95)
    # H-c2: d* 落在 85% 规则 / 先行研究对应档附近
    hc2_supported = frac_set >= 0.95
    return {
        "d_star_k": d_star,
        "d_star_dose": d_star / float(W),
        "d_star_boot_lo": star_lo, "d_star_boot_hi": star_hi,
        "frac_below_endpoint0": frac_below0,
        "frac_below_endpoint20": frac_below20,
        "hc1_internal_optimum_supported": hc1_supported,
        "hc2_star_in_target_set_supported": hc2_supported,
        "hc2_target_k_set": star_set,
        "frac_star_in_target_set": frac_set,
        "note": ("H-c1 支持需内部极小点低于两端点(各>=95% bootstrap 复制); "
                 f"H-c2 支持需 d* 落在目标档 {star_set} (剂量≈0.1587/0.193) 且>=95% 复制。"),
    }


def bh_adjust(pvals):
    """Benjamini-Hochberg, q=0.05。输入 list of (key, p)。返回 dict key->(p_raw, p_adj, sig)。"""
    items = [(k, p) for k, p in pvals if p == p and p is not None]
    m = len(items)
    if m == 0:
        return {}
    order = sorted(range(m), key=lambda i: items[i][1])
    adj = [0.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), 1):
        val = min(prev, items[i][1] * m / (m - rank + 1))
        adj[m - rank] = val
        prev = val
    out = {}
    for (k, p), a in zip(items, adj):
        out[k] = {"p_raw": p, "p_bh": min(1.0, a), "sig_q05": (min(1.0, a) < 0.05)}
    return out


def test_nonmonotonic_bh(mu_boot, mu_point):
    """对每档内部剂量 d 与两端点比较，BH 校正。返回显著低于两端的剂量。"""
    B = mu_boot.shape[0]
    p_low0, p_low20 = {}, {}
    for d in range(1, N_DOSES - 1):
        cnt0 = 0; cnt20 = 0; cnt = 0
        for b in range(B):
            a = mu_boot[b]
            if np.any(np.isnan(a)):
                continue
            cnt += 1
            if a[d] < a[0]:
                cnt0 += 1
            if a[d] < a[N_DOSES - 1]:
                cnt20 += 1
        p_low0[d] = 1 - cnt0 / max(1, cnt)
        p_low20[d] = 1 - cnt20 / max(1, cnt)
    pvals = []
    for d in range(1, N_DOSES - 1):
        pvals.append((f"d{d}_vs0", p_low0[d]))
        pvals.append((f"d{d}_vs20", p_low20[d]))
    adj = bh_adjust(pvals)
    sig_doses = sorted({int(k.split("_")[0][1:]) for k, v in adj.items() if v["sig_q05"]})
    return {"bh_adjusted": adj, "significant_interior_doses_below_both_endpoints": sig_doses}


def hc3_strata(obs, dataset_name, strat_keys):
    """H-c3：在分层子集上重估 d*（探索性，点估计）。为控制运行时，仅取样本量最大的前 3 个合格分层。"""
    out = {}
    sizes = {skey: sum(1 for o in obs if o.get("stratum") == skey) for skey in strat_keys}
    kept = [k for k, v in sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0])) if v >= 3000][:3]
    for skey in strat_keys:
        if skey not in kept:
            out[skey] = {"n": sizes[skey],
                         "skipped": ("仅取最大 3 个分层（运行时控制）" if sizes[skey] >= 3000 else "n<3000")}
            continue
        sub = [o for o in obs if o.get("stratum") == skey]
        try:
            res = quick_aipw(sub)
            out[skey] = {"n": len(sub), "d_star_k": int(np.nanargmin(res["aipw"])),
                         "mu_aipw": [float(x) for x in res["aipw"]]}
        except Exception as e:
            out[skey] = {"n": len(sub), "error": str(e)}
    out["_note"] = "分层为探索性（未预注册），仅报告点估计；每数据集只取最大 3 个合格分层。"
    return out


def quick_aipw(obs_subset):
    """轻量 AIPW（点估计）供 H-c3 分层使用。"""
    global X_global, D_global, _match_nn
    X, Y, D, lr = assemble(obs_subset, "Y_rank")
    save_X, save_D, save_match = X_global, D_global, _match_nn
    X_global, D_global = X, D
    _matching_prep()
    P = compute_psi(X, Y, D, lr, "Y_rank")
    est = estimate_from_psi(P, lr, Y, D, len(D), boot=False)
    X_global, D_global, _match_nn = save_X, save_D, save_match
    return est


# ----------------------------------------------------------------------------
# 组装矩阵
# ----------------------------------------------------------------------------
def assemble(obs, y_key):
    X = np.array([o["X"] for o in obs], dtype=float)
    # 标准化特征
    mu = X.mean(axis=0); sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Xs = (X - mu) / sd
    if y_key == "Y_rank":
        Y = np.array([o["Y_rank"] for o in obs], dtype=float)
    elif y_key == "Y_log":
        Y = np.array([math.log1p(o["Y_raw"]) for o in obs], dtype=float)
    else:
        Y = np.array([o["Y_raw"] for o in obs], dtype=float)
    D = np.array([o["D"] for o in obs], dtype=int)
    lr = [o["learner"] for o in obs]
    return Xs, Y, D, lr


def run_dataset(obs, dataset_name, rev_obs=None, do_neg2=True):
    global X_global, D_global, _match_nn
    n = len(obs)
    dose_counts = {d: int(sum(1 for o in obs if o["D"] == d)) for d in range(N_DOSES)}

    # 主分析（题内秩变换 Y_rank）
    X, Y, D, lr = assemble(obs, "Y_rank")
    X_global, D_global = X, D
    _matching_prep()
    P = compute_psi(X, Y, D, lr, "Y_rank")
    est = estimate_from_psi(P, lr, Y, D, n, boot=True)
    boot_aipw = est["aipw"]["boot"]

    hc1 = test_hc1_hc2(boot_aipw, est["aipw"]["point"])
    nonmono = test_nonmonotonic_bh(boot_aipw, est["aipw"]["point"])

    # 稳健性变换：log(1+T)、原始步数（点估计；不另做 bootstrap 以控制运行时，CI 以主分析为基准）
    est_log, est_raw = {}, {}
    for yk, store in (("Y_log", est_log), ("Y_raw", est_raw)):
        Xr, Yr, Dr, lrr = assemble(obs, yk)
        X_global, D_global = Xr, Dr
        _matching_prep()
        Pr = compute_psi(Xr, Yr, Dr, lrr, yk)
        store_est = estimate_from_psi(Pr, lrr, Yr, Dr, len(Dr), boot=False)
        # boot=False 时返回裸数组（非 dict），直接取 aipw 曲线
        store["aipw"] = [float(x) for x in np.asarray(store_est["aipw"], dtype=float)]
    X_global, D_global = X, D  # 还原主分析全局态

    # 对照估计量一致性：取点估计曲线
    ctrl = {}
    for name in ("aipw", "aipw_trunc", "reg", "ipw", "match"):
        ctrl[name] = {
            "point": [float(x) for x in est[name]["point"]],
            "lo": [float(x) for x in est[name]["lo"]],
            "hi": [float(x) for x in est[name]["hi"]],
        }

    # P-pos-1：剂量 0 与 W 应慢于中段（mu 更高）。使用主 AIPW 曲线 + bootstrap 概率
    mu = est["aipw"]["point"]
    mid = W // 2
    kmax = W
    pos1 = {
        "mu_at_k0": float(mu[0]), "mu_at_kmid": float(mu[mid]), "mu_at_kmax": float(mu[kmax]),
        "diff_k0_minus_kmid": float(mu[0] - mu[mid]),
        "diff_kmax_minus_kmid": float(mu[kmax] - mu[mid]),
        "p_k0_slower_than_kmid": float(np.mean(boot_aipw[:, 0] > boot_aipw[:, mid])),
        "p_kmax_slower_than_kmid": float(np.mean(boot_aipw[:, kmax] > boot_aipw[:, mid])),
        "expectation": "k=0 与 k=W 的 μ 应显著高于中段（更慢→更高步数秩）；两 bootstrap 概率应 >0.95，否则估计量在该数据上无检出能力，主结论降级",
        "naive_mean_T_k0": float(np.mean([o["Y_raw"] for o in obs if o["D"] == 0])) if any(o["D"] == 0 for o in obs) else None,
        "naive_mean_T_kmid": float(np.mean([o["Y_raw"] for o in obs if o["D"] == mid])) if any(o["D"] == mid for o in obs) else None,
        "naive_mean_T_kmax": float(np.mean([o["Y_raw"] for o in obs if o["D"] == kmax])) if any(o["D"] == kmax for o in obs) else None,
    }

    # P-neg-2：时间倒置窗（结局取最早 20，处理取其后 20）。若显著内部最优则说明有时间趋势混杂。
    neg2 = None
    if do_neg2 and rev_obs is not None:
        if len(rev_obs) >= MIN_UNIT_ANS * 2:
            Xr, Yr, Dr, lrr = assemble(rev_obs, "Y_rank")
            X_global, D_global = Xr, Dr
            _matching_prep()
            Pr = compute_psi(Xr, Yr, Dr, lrr, "Y_rank")
            estr = estimate_from_psi(Pr, lrr, Yr, Dr, len(Dr), boot=True)
            hc1r = test_hc1_hc2(estr["aipw"]["boot"], estr["aipw"]["point"])
            neg2 = {
                "n_reversed": len(rev_obs),
                "mu_aipw_reversed": [float(x) for x in estr["aipw"]["point"]],
                "hc1_internal_optimum_supported": hc1r["hc1_internal_optimum_supported"],
                "d_star_k_reversed": hc1r["d_star_k"],
                "frac_below_endpoint0_reversed": hc1r["frac_below_endpoint0"],
                "frac_below_endpoint20_reversed": hc1r["frac_below_endpoint20"],
                "interpretation": ("若倒置窗出现显著内部最优，说明存在时间趋势混杂，主结论须降级为关联性证据；"
                                   "期望为不显著。注意：倒置窗的能力特征 θ 机械取自结局窗本身（最早 20 条之前"
                                   "无更早数据），该对照只用于探测时间趋势混杂的方向性，判读从保守。"),
            }
            X_global, D_global = X, D

    # H-c3 分层（探索性）
    strata_defs = build_strata(obs, dataset_name)
    for o, sk in zip(obs, strata_defs):
        o["stratum"] = sk
    hc3 = hc3_strata(obs, dataset_name, sorted(set(strata_defs)))

    return {
        "n_obs": n,
        "dose_counts": dose_counts,
        "primary_y": "rank_within_item",
        "mu_curves": ctrl,
        "robustness": {
            "log1pT_aipw_point": est_log["aipw"],
            "rawT_aipw_point": est_raw["aipw"],
        },
        "hc1": hc1,
        "hc2": {"star_in_target_set_supported": hc1["hc2_star_in_target_set_supported"],
                "hc2_target_k_set": hc1["hc2_target_k_set"],
                "frac_star_in_target_set": hc1["frac_star_in_target_set"],
                "d_star_dose": hc1["d_star_dose"]},
        "nonmonotonic_bh": nonmono,
        "controls": {"pos1": pos1, "neg2": neg2,
                     "pos2_note": "P-pos-2（随机化处理的模拟臂对照）本次未执行：本运行只覆盖公开日志离策略路线，模拟臂对照如实留空，不作声称。",
                     "neg1_note": "P-neg-1（机制无关结局）不可构造：三套日志中不存在与学习机制无关、且与处理同期的界面类结局变量，如实声明。"},
        "hc3_exploratory": hc3,
    }


def build_strata(obs, dataset_name):
    """返回与 obs 等长的 stratum 标签列表（探索性；明确标注未预注册亚组）。"""
    labels = []
    for o in obs:
        if o["hint_avail"]:
            hb = "hint_high" if o["hint_rate"] >= 0.5 else "hint_low"
        else:
            hb = "hint_na"
        it = (o["item_type"] or "na")[:24]
        labels.append(f"{hb}|it={it}")
    # 仅保留计数足够多的 stratum（下游 hc3_strata 会再过滤）
    return labels


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="all", choices=["all", "assist09", "dbe", "junyi"])
    ap.add_argument("--window", type=int, default=20, choices=[10, 20, 40],
                    help="窗宽稳健性（冻结方案 §11.2：主分析 W=20，稳健性须报告 W=10/40）")
    ap.add_argument("--debug", action="store_true",
                    help="小样本/少 bootstrap/少树，仅 assist09 + 小 junyi 快速验证")
    args = ap.parse_args()

    global BOOT, RF_NEST, N_SAMPLE_JUNYI, W, K_MAX, N_DOSES, MIN_UNIT_ANS, JSON_PATH
    if args.debug:
        BOOT = 30
        RF_NEST = 20
        N_SAMPLE_JUNYI = 3000
    if args.window != 20:
        W = args.window
        K_MAX = W
        N_DOSES = W + 1
        MIN_UNIT_ANS = W + GAP_MIN + OUT_W
        JSON_PATH = os.path.join(OUT_DIR, f"aipw_results_w{W}.json")
        print(f"[config] robustness window W={W} -> doses 0..{W}, "
              f"MIN_UNIT_ANS={MIN_UNIT_ANS}, out={JSON_PATH}", flush=True)

    datasets_to_run = (["assist09", "dbe", "junyi"] if args.dataset == "all"
                       else [args.dataset])

    results = {"meta": {
        "frozen_doc": DOC_PATH,
        "scheme_id": "LF-CIS-2026-09-22",
        "config": {"W": W, "OUT_W": OUT_W, "N_DOSES": N_DOSES, "FOLDS": FOLDS,
                   "BOOT": BOOT, "SEED": SEED, "EPS_E": EPS_E, "WT_CAP": WT_CAP,
                   "N_SAMPLE_JUNYI": N_SAMPLE_JUNYI},
        "python": sys.version.split()[0],
    }}
    all_obs = {}

    # ---- assist09 ----
    if "assist09" in datasets_to_run:
        print("[assist09] loading...", flush=True)
        units = load_assist09()
        # 全局 KC 正确率（难度代理）
        kc_acc = defaultdict(lambda: [0, 0])
        for u in units:
            for (c, *_rest) in u["seq"]:
                if c is not None:
                    kc_acc[u["kc"]][0] += (1 if c == 1 else 0)
                    kc_acc[u["kc"]][1] += 1
        gka = {k: (v[0] / v[1]) for k, v in kc_acc.items()}
        obs, meta = build_observations(units, "assist09", global_kc_acc=gka)
        rev_obs, _ = build_observations(units, "assist09", global_kc_acc=gka, reverse=True)
        # 抽样（若有需要；assist09 一般不大，用全部）
        all_obs["assist09"] = (obs, meta, rev_obs)

    # ---- dbe ----
    if "dbe" in datasets_to_run:
        print("[dbe] loading...", flush=True)
        units = load_dbe()
        obs, meta = build_observations(units, "dbe")
        rev_obs, _ = build_observations(units, "dbe", reverse=True)
        all_obs["dbe"] = (obs, meta, rev_obs)

    # ---- junyi ----
    if "junyi" in datasets_to_run:
        print("[junyi] streaming (2-pass)...", flush=True)
        units = load_junyi(N_SAMPLE_JUNYI)
        # 抽样到目标
        if len(units) > N_SAMPLE_JUNYI:
            units.sort(key=lambda u: ckey(f"{u['learner']}|{u['kc']}"))
            units = units[:N_SAMPLE_JUNYI]
        obs, meta = build_observations(units, "junyi")
        rev_obs, _ = build_observations(units, "junyi", reverse=True)
        all_obs["junyi"] = (obs, meta, rev_obs)

    # 运行
    out_datasets = {}
    for name, pack in all_obs.items():
        obs, meta = pack[0], pack[1]
        rev_obs = pack[2] if len(pack) > 2 else None
        print(f"[{name}] running AIPW on {meta['n_obs']} obs...", flush=True)
        t1 = time.time()
        res = run_dataset(obs, name, rev_obs=rev_obs, do_neg2=True)
        res["meta"] = meta
        res["sampling"] = (f"全部合格单元(n={meta['n_obs']})" if name != "junyi"
                           else f"Junyi 合格单元抽样至 N_SAMPLE={N_SAMPLE_JUNYI}（按 ckey 确定性截断）")
        out_datasets[name] = res
        print(f"[{name}] done in {time.time()-t1:.1f}s  d*_k={res['hc1']['d_star_k']}  "
              f"hc1={res['hc1']['hc1_internal_optimum_supported']} "
              f"hc2={res['hc1']['hc2_star_in_target_set_supported']}", flush=True)

    results["datasets"] = out_datasets
    results["meta"]["runtime_sec"] = round(time.time() - t0, 1)

    # 写 JSON
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("[write] aipw_results.json written", flush=True)

    # ---- 审计留痕（append-only）----
    write_audit(results)


def write_audit(results):
    doc_sha = sha256_file(DOC_PATH)
    doc_mtime = os.path.getmtime(DOC_PATH)
    import datetime
    doc_mtime_str = datetime.datetime.fromtimestamp(doc_mtime).isoformat()

    inputs = {
        "assist09": ASSIST_CSV,
        "dbe_txn": DBE_TXN,
        "dbe_qkc": DBE_QKC,
        "dbe_kc": DBE_KC,
        "junyi_log": JUNYI_LOG,
        "junyi_info": JUNYI_INFO,
    }
    input_shas = {k: sha256_file(p) for k, p in inputs.items()}

    script_sha = sha256_file(os.path.abspath(__file__))
    out_sha = sha256_file(JSON_PATH)

    lines = []
    lines.append("=" * 72)
    lines.append(f"AIPW/DR 留痕日志  @ {datetime.datetime.now().isoformat()}")
    lines.append("=" * 72)
    lines.append("【冻结方案文档】 (LF-CIS-2026-09-22)")
    lines.append(f"  path        : {DOC_PATH}")
    lines.append(f"  sha256      : {doc_sha}")
    lines.append(f"  mtime       : {doc_mtime_str}  (冻结日期标注 2026-09-22)")
    lines.append("  repo_status : 本仓库当前未提交(git 不可用)；以文档内容哈希+日期作为冻结证据，")
    lines.append("               确立‘先冻结、后接触结局’的可核验性（文档 §9 要求）。")
    lines.append("【输入数据文件 SHA256】")
    for k, v in input_shas.items():
        lines.append(f"  {k:12s}: {v}  ({inputs[k]})")
    lines.append("【脚本 SHA256】（先写脚本、哈希，再运行；本次运行即以该文件为准）")
    lines.append(f"  {os.path.abspath(__file__)}")
    lines.append(f"  sha256      : {script_sha}")
    lines.append("【首跑日志】")
    lines.append(f"  runtime_sec : {results['meta'].get('runtime_sec')}")
    lines.append(f"  script_sha  : {script_sha}")
    lines.append("  input_shas  : " + json.dumps(input_shas))
    lines.append(f"  output_json : {JSON_PATH}")
    lines.append(f"  output_sha  : {out_sha}")
    lines.append(f"  datasets    : {list(results.get('datasets', {}).keys())}")
    lines.append("")
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("[audit] aipw_audit.log appended", flush=True)


if __name__ == "__main__":
    main()
