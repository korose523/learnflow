# -*- coding: utf-8 -*-
"""论文表格 <-> 实验 JSON 逐值对账（可复用于每一轮定稿）。

对账范围：
    M1 表 7-1  / M3 表 11  <-  results/code/o11_fusion_optimization.json
    M1 表 7-2  / M3 表 12  <-  results/code/o12_student_o11.json
    M1 O10 表  / M3 表 10  <-  results/code/o10_user_holdout.json

用法：
    python results/code/reconcile_paper_tables.py            # 全部三组
    python results/code/reconcile_paper_tables.py o11 o12    # 只跑指定组

不依赖 numpy。任一处 doc != json 即以退出码 1 失败并逐项打印差异。
"""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(BASE, "docs")
CODE = os.path.join(BASE, "results", "code")
KS = [10, 25, 50, 100, 200]

M1 = "M1_难度可公度性与最优错误率_完整稿.md"
M3 = "M3_有序难度决策与大模型先验边界_完整稿.md"

FAIL = []


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def load(n):
    with io.open(os.path.join(CODE, n), encoding="utf-8") as f:
        return json.load(f)


def num(s):
    s = s.replace("*", "").replace("\u2212", "-").replace(",", "").strip()
    return float(re.sub(r"\s*pp$", "", s))


def rows_of(doc, caption):
    """第一个 caption 以 caption 开头的 markdown 管道表的数值行。"""
    lines = read(os.path.join(DOCS, doc)).splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("**" + caption):
            rows, started = [], 0
            for j in range(i + 1, min(i + 40, len(lines))):
                s = lines[j].strip()
                if not s.startswith("|"):
                    if rows:
                        break
                    continue
                cells = [c.strip() for c in s.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    started = 1
                    continue
                if started and re.match(r"^\**\d+\**$", cells[0]):
                    rows.append(cells)
            return rows
    FAIL.append(f"{doc}: 未找到表标题「{caption}」")
    return []


def chk(tag, doc_val, json_val, tol=5e-4):
    if abs(doc_val - json_val) > tol:
        FAIL.append(f"{tag}: doc={doc_val} json={json_val} diff={json_val - doc_val:+.6f}")


# ---------------------------------------------------------------- O11
def run_o11():
    print("=" * 92)
    print("O11 记录级  ->  M1 表 7-1  &  M3 表 11")
    print("=" * 92)
    d = load("o11_fusion_optimization.json")
    VAR = ["fused6", "fused7", "signed7", "rw6", "srw7"]
    for doc, cap in ((M1, "表 7-1"), (M3, "表 11")):
        for row in rows_of(doc, cap):
            k = int(row[0].replace("*", ""))
            r = d["results"][str(k)]
            chk(f"{cap} k={k} 仅成功率", num(row[1]), r["success_heldout"])
            for idx, v in enumerate(VAR, start=2):
                chk(f"{cap} k={k} {v}", num(row[idx]),
                    r["variants"][v]["cf"]["gain_vs_success_pp"])
            for idx, key in ((7, "lambda_cf_mean"), (8, "lambda_rel_mean"),
                             (9, "lambda_star_emp_mean")):
                chk(f"{cap} k={k} {key}", num(row[idx]), r[key])
        print(f"  {cap}: {len(rows_of(doc, cap))} 行已对账")


# ---------------------------------------------------------------- O12
def run_o12():
    print("=" * 92)
    print("O12 学生级  ->  M1 表 7-2  &  M3 表 12")
    print("=" * 92)
    d = load("o12_student_o11.json")
    for doc, cap in ((M1, "表 7-2"), (M3, "表 12")):
        for row in rows_of(doc, cap):
            k = int(row[0].replace("*", ""))
            r = d["results"][str(k)]
            chk(f"{cap} k={k} 仅成功率", num(row[1]), r["success"])
            chk(f"{cap} k={k} fused6", num(row[2]), r["gain_fused6_pp"])
            chk(f"{cap} k={k} srw7", num(row[3]), r["gain_srw7_cf_pp"])
            chk(f"{cap} k={k} 配对差", num(row[4]), r["srw7_minus_fused6_pp"])
            chk(f"{cap} k={k} 胜率", num(row[5]), r["win_rate"], tol=1e-9)
            if abs(float(row[6].replace("*", "")) - r["wilcoxon_p"]) / r["wilcoxon_p"] > 0.02:
                FAIL.append(f"{cap} k={k} wilcoxon doc={row[6]} json={r['wilcoxon_p']:.2e}")
        print(f"  {cap}: {len(rows_of(doc, cap))} 行已对账")


# ---------------------------------------------------------------- O10
def run_o10():
    print("=" * 92)
    print("O10 学生级  ->  M1 O10 表  &  M3 表 10")
    print("=" * 92)
    d = load("o10_user_holdout.json")["results"]
    # M3 表 10：k | success | fused7 | fused6 | mix6 | srw7 | lam_hat | lam_emp | ...
    for row in rows_of(M3, "表 10"):
        k = int(row[0].replace("*", ""))
        r = d[str(k)]
        chk(f"M3 表 10 k={k} success", num(row[1]), r["success"])
        chk(f"M3 表 10 k={k} fused7", num(row[2]), r["fused7"])
        chk(f"M3 表 10 k={k} fused6", num(row[3]), r["fused6"])
        chk(f"M3 表 10 k={k} mix6", num(row[4]), r["mix6_hat"])
        chk(f"M3 表 10 k={k} λ̂", num(row[6]), r["lambda_hat"])
        chk(f"M3 表 10 k={k} λ*_emp", num(row[7]), r["lambda_emp_mean"])
    print(f"  M3 表 10: {len(rows_of(M3, '表 10'))} 行已对账")

    # M1 的 O10 表：k | success | fused7 | fused6 | mix6 | λ̂ | λ*_emp | ...
    lines = read(os.path.join(DOCS, M1)).splitlines()
    rows = []
    for i, ln in enumerate(lines):
        if ln.strip().startswith("| 10 | 0.6631 | 0.6442 | 0.6870 |"):
            for j in range(i, i + 6):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                if re.match(r"^\**\d+\**$", cells[0]):
                    rows.append(cells)
            break
    for row in rows:
        k = int(row[0].replace("*", ""))
        r = d[str(k)]
        chk(f"M1-O10 k={k} success", num(row[1]), r["success"])
        chk(f"M1-O10 k={k} fused7", num(row[2]), r["fused7"])
        chk(f"M1-O10 k={k} fused6", num(row[3]), r["fused6"])
        chk(f"M1-O10 k={k} mix6", num(row[4]), r["mix6_hat"])
        chk(f"M1-O10 k={k} λ̂", num(row[5]), r["lambda_hat"])
        chk(f"M1-O10 k={k} λ*_emp", num(row[6]), r["lambda_emp_mean"])
    print(f"  M1 O10 表: {len(rows)} 行已对账")


groups = set(a.lower() for a in sys.argv[1:]) or {"o11", "o12", "o10"}
if "o11" in groups:
    run_o11()
if "o12" in groups:
    run_o12()
if "o10" in groups:
    run_o10()

print()
print("=" * 92)
if FAIL:
    print(f"FAILURES ({len(FAIL)})")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("ALL PASS —— 论文表格与实验 JSON 逐值一致")
