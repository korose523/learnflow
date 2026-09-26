"""
R11 实证检验：结构化特征工程 + 树集成 能否比 LearnFlow 当前 LLM 直接/排序评级
更好地预测题目难度。

对比基线 (M3 直接评级):
  - DBE (E1A): LLM 直接评级 vs 专家难度, Spearman rho = 0.2195
  - XES (E2X): LLM 直接评级 vs 实证难度四分位, Spearman rho = -0.038

诚实约束:
  - 不声称复现 R11 (Razavi & Powers 2026) 的 r=.87 (数据/特征不同)。
  - 仅报告「在 LearnFlow 自有数据上，结构化特征是否把 rho 提升到高于直接评级基线」。

数据可用性:
  - DBE 题目文本 + 专家难度 (Questions.csv) + LLM 评级 (llm_labeling_v2.jsonl E1A) 均可用。
  - XES 题目文本 (metadata/questions.json) + 实证四分位 (llm_labeling_v2.jsonl E2X) + LLM 评级 均可用。

方法:
  - 逐题构造结构化特征 (词法/可读性/结构/选项数/KC 数) + LLM 评级作为特征。
  - 目标变量 = 专家难度标签 (DBE: Questions.csv difficulty; XES: emp_quartile)。
  - 模型: scikit-learn RandomForestRegressor / GradientBoostingRegressor。
  - 评估: 5-fold CV 袋外预测 -> Spearman rho + RMSE; bootstrap 95% CI (seed=42, B=2000)。
"""
import json, csv, re, os, sys
from collections import defaultdict
import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_predict, KFold
from sklearn.metrics import mean_squared_error

SEED = 42
BASE = "E:/learnflow"
CODE = os.path.join(BASE, "results/code")
DATA = os.path.join(BASE, "data")
DBE_CSV = os.path.join(DATA, "dbe_kt22/csv")
XES = os.path.join(DATA, "xes3g5m/XES3G5M")

np.random.seed(SEED)

# ----------------------------------------------------------------------------
# 1. 载入 LLM 标注记录
# ----------------------------------------------------------------------------
dbe_rows = {}   # key -> {expert, llm}
xes_rows = {}   # key -> {emp_quartile, llm}
with open(os.path.join(CODE, "llm_labeling_v2.jsonl"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        c = r.get("cond")
        if c == "E1A":
            dbe_rows[r["key"]] = {"expert": r.get("expert"), "llm": r.get("llm")}
        elif c == "E2X":
            xes_rows[r["key"]] = {"emp_quartile": r.get("emp_quartile"), "llm": r.get("llm")}

# ----------------------------------------------------------------------------
# 2. DBE 特征构造
# ----------------------------------------------------------------------------
def read_csv_dict(path, key_col, val_cols):
    out = defaultdict(dict)
    with open(path, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            k = row[key_col]
            for vc in val_cols:
                out[k][vc] = row.get(vc)
    return out

# Questions.csv: id,question_rich_text,question_title,explanation,hint_text,question_text,difficulty
dbe_q = {}
with open(os.path.join(DBE_CSV, "Questions.csv"), encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f):
        dbe_q[row["id"]] = row

# choices per question
dbe_choices = defaultdict(lambda: [0, 0])  # question_id -> [n_choices, n_correct]
with open(os.path.join(DBE_CSV, "Question_Choices.csv"), encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f):
        qid = row.get("question_id")
        if qid is None:
            continue
        dbe_choices[qid][0] += 1
        if str(row.get("is_correct", "")).strip().lower() in ("true", "1", "yes"):
            dbe_choices[qid][1] += 1

# KC per question (generic: first col=question, second col=KC)
dbe_kc = defaultdict(int)
with open(os.path.join(DBE_CSV, "Question_KC_Relationships.csv"), encoding="utf-8", errors="replace") as f:
    rdr = csv.reader(f)
    header = next(rdr)
    for row in rdr:
        if len(row) >= 2 and row[0]:
            dbe_kc[row[0]] += 1

def clean_text(t):
    return re.sub(r"<[^>]+>", " ", t or "")

def dbe_features(qid):
    q = dbe_q.get(qid, {})
    rich = q.get("question_rich_text") or ""
    plain = q.get("question_text") or ""
    text = (plain + " " + rich)
    cln = clean_text(text)
    char_len = len(text)
    cjk = len(re.findall(r"[一-鿿]", cln))
    tokens = re.findall(r"[A-Za-z]+", cln)
    word_count = len(tokens) + cjk
    n_img = text.count("<img")
    n_tags = len(re.findall(r"<[a-zA-Z]", text))
    digits = sum(ch.isdigit() for ch in text)
    num_density = digits / max(char_len, 1)
    has_latex = ("latex.codecogs" in text) or ("<img" in text)
    has_code = ("<code" in text.lower()) or ("<pre" in text.lower())
    nc, ncor = dbe_choices.get(qid, [0, 0])
    n_kc = dbe_kc.get(qid, 0)
    f_struct = [char_len, word_count, n_img, n_tags, num_density,
                int(has_latex), int(has_code), nc, ncor, n_kc]
    return f_struct, q

# ----------------------------------------------------------------------------
# 3. XES 特征构造
# ----------------------------------------------------------------------------
with open(os.path.join(XES, "metadata/questions.json"), encoding="utf-8", errors="replace") as f:
    xes_q = json.load(f)

def xes_features(qid):
    m = xes_q.get(qid, {})
    content = m.get("content") or ""
    analysis = m.get("analysis") or ""
    text = content + " " + analysis
    cln = clean_text(text)
    char_len = len(text)
    cjk = len(re.findall(r"[一-鿿]", cln))
    tokens = re.findall(r"[A-Za-z]+", cln)
    word_count = len(tokens) + cjk
    n_math = text.count("$$") + text.count("\\(") + text.count("\\[")
    opts = m.get("options") or {}
    n_options = len(opts) if isinstance(opts, dict) else (len(opts) if opts else 0)
    digits = sum(ch.isdigit() for ch in text)
    num_density = digits / max(char_len, 1)
    f_struct = [char_len, word_count, n_math, n_options, num_density]
    return f_struct, m

# ----------------------------------------------------------------------------
# 4. 组装数据集 (保证与基线同口径: 同时具备 目标 + LLM 评级 的题)
# ----------------------------------------------------------------------------
def build_dataset(rows, target_key, feat_fn, has_llm_feature):
    X_struct, X_all, y, llm, keys = [], [], [], [], []
    for qid, rec in rows.items():
        tgt = rec.get(target_key)
        if tgt is None:
            continue
        ll = rec.get("llm")
        if ll is None:
            continue
        fs, _ = feat_fn(qid)
        if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in fs):
            continue
        X_struct.append(fs)
        X_all.append(fs + [float(ll)])
        y.append(float(tgt))
        llm.append(float(ll))
        keys.append(qid)
    X_struct = np.array(X_struct, dtype=float)
    X_all = np.array(X_all, dtype=float)
    y = np.array(y, dtype=float)
    llm = np.array(llm, dtype=float)
    if not has_llm_feature:
        return X_struct, y, llm, keys
    return X_all, y, llm, keys

# ----------------------------------------------------------------------------
# 5. 评估
# ----------------------------------------------------------------------------
FEAT_NAMES_STRUCT = {
    "DBE": ["char_len", "word_count", "n_img", "n_tags", "num_density",
            "has_latex", "has_code", "n_choices", "n_correct_choices", "n_kc"],
    "XES": ["char_len", "word_count", "n_math", "n_options", "num_density"],
}

def evaluate(X, y, model_factory, n_splits=5, b=2000):
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    model = model_factory()
    oof = cross_val_predict(model, X, y, cv=kf, n_jobs=-1)
    rho, pval = stats.spearmanr(oof, y)
    rmse = float(np.sqrt(mean_squared_error(y, oof)))
    # bootstrap CI for rho (resample paired oof/y)
    rng = np.random.default_rng(SEED)
    idx = np.arange(len(y))
    rhos = np.empty(b)
    for i in range(b):
        s = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[s])) < 2 or len(np.unique(oof[s])) < 2:
            rhos[i] = np.nan
            continue
        r, _ = stats.spearmanr(oof[s], y[s])
        rhos[i] = r if np.isfinite(r) else np.nan
    rhos = rhos[~np.isnan(rhos)]
    ci = [float(np.percentile(rhos, 2.5)), float(np.percentile(rhos, 97.5))]
    return {"rho": float(rho), "pvalue": float(pval), "rmse": rmse,
            "ci95": ci, "n": int(len(y))}

def baseline_ci(y, llm, b=2000):
    rho, pval = stats.spearmanr(llm, y)
    rng = np.random.default_rng(SEED)
    idx = np.arange(len(y))
    rhos = np.empty(b)
    for i in range(b):
        s = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[s])) < 2 or len(np.unique(llm[s])) < 2:
            rhos[i] = np.nan
            continue
        r, _ = stats.spearmanr(llm[s], y[s])
        rhos[i] = r if np.isfinite(r) else np.nan
    rhos = rhos[~np.isnan(rhos)]
    ci = [float(np.percentile(rhos, 2.5)), float(np.percentile(rhos, 97.5))]
    return {"rho": float(rho), "pvalue": float(pval),
            "rmse": float(np.sqrt(mean_squared_error(y, llm))), "ci95": ci, "n": int(len(y))}

rf_factory = lambda: RandomForestRegressor(n_estimators=400, random_state=SEED,
                                           oob_score=True, n_jobs=-1)
gb_factory = lambda: GradientBoostingRegressor(random_state=SEED)

# ----------------------------------------------------------------------------
# 6. 运行
# ----------------------------------------------------------------------------
results = {
    "protocol": "R11 empirical test: structured feature engineering + tree ensemble vs LLM direct rating",
    "seed": SEED,
    "baseline_direct_rating": {"DBE_E1A": 0.2195, "XES_E2X": -0.0379},
    "data_availability": {
        "DBE": "Questions.csv (text+expert difficulty) + E1A LLM rating available",
        "XES": "metadata/questions.json (text) + E2X emp_quartile + LLM rating available",
    },
    "datasets": {},
}

for name, rows, tkey, feat_fn in [
    ("DBE", dbe_rows, "expert", dbe_features),
    ("XES", xes_rows, "emp_quartile", xes_features),
]:
    Xs, y, llm, keys = build_dataset(rows, tkey, feat_fn, has_llm_feature=False)
    Xa, y2, llm2, keys2 = build_dataset(rows, tkey, feat_fn, has_llm_feature=True)
    assert len(y) == len(y2)
    base = baseline_ci(y, llm)
    # structured-only (no LLM feature)
    rf_struct = evaluate(Xs, y, rf_factory)
    gb_struct = evaluate(Xs, y, gb_factory)
    # structured + LLM rating as feature (R11-style: LLM output feeds tree)
    rf_all = evaluate(Xa, y, rf_factory)
    gb_all = evaluate(Xa, y, gb_factory)
    results["datasets"][name] = {
        "n": int(len(y)),
        "feature_names_struct": FEAT_NAMES_STRUCT[name],
        "feature_names_with_llm": FEAT_NAMES_STRUCT[name] + ["llm_rating"],
        "target": tkey,
        "baseline_direct_rating": base,
        "tree_struct_only": {
            "RandomForest": rf_struct,
            "GradientBoosting": gb_struct,
        },
        "tree_struct_plus_llm": {
            "RandomForest": rf_all,
            "GradientBoosting": gb_all,
        },
        "primary_model": "RandomForest",
    }
    print(f"[{name}] n={len(y)} baseline rho={base['rho']:.4f} CI={base['ci95']}")
    print(f"   RF struct-only  rho={rf_struct['rho']:.4f} CI={rf_struct['ci95']} rmse={rf_struct['rmse']:.4f}")
    print(f"   RF +llm        rho={rf_all['rho']:.4f} CI={rf_all['ci95']} rmse={rf_all['rmse']:.4f}")
    print(f"   GB struct-only  rho={gb_struct['rho']:.4f} CI={gb_struct['ci95']}")
    print(f"   GB +llm        rho={gb_all['rho']:.4f} CI={gb_all['ci95']}")

with open(os.path.join(BASE, "results/m3/r11_tree/r11_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nWROTE r11_results.json")
