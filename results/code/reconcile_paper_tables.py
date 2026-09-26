# -*- coding: utf-8 -*-
"""论文表格 <-> 实验 JSON 逐值对账（可复用于每一轮定稿）。

对账范围（v2，2026-09-22 审阅整改后）：
    M1 表 7-1  <-  results/code/o11_fusion_optimization.json
    M1 表 7-2  <-  results/code/o12_student_o11.json
    M1 O10 表  <-  results/code/o10_user_holdout.json
    M3 去重边界 <- 纯文本检查（见 run_dedup）

**为什么 v2 去掉了 M3 侧的表值对账**：审阅意见 §3.3 / §5.3 判定 M1 第 7.8 节与
M3 第 5.5~5.6 节是同一批结果（同一 JSON 产出），两篇同时投稿构成重复发表风险。
整改办法是"冷启动估计器（O7~O12、λ_cf、srw7、落地描述）只保留在 M1 一处，
M3 改为一段交叉引用并删除全部相关表格"。因此 M3 侧不再持有这些表，
本脚本改为**检查去重是否真的执行到位**（M3 不得再出现上述表格标题）。

用法：
    python results/code/reconcile_paper_tables.py            # 全部四组
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

# M3 在去重后不得再作为"表格标题"出现的编号（表 8~表 12 已移交 M1）
M3_FORBIDDEN_TABLE_CAPTIONS = ["表 8", "表 9", "表 10", "表 11", "表 12"]
# M3 必须保留的交叉引用标记（指向 M1 的对应节）
M3_REQUIRED_XREF = ["M1", "7.2", "7.8"]

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
    print("O11 记录级  ->  M1 表 7-1（M3 侧已按审阅 §3.3 拆分删除）")
    print("=" * 92)
    d = load("o11_fusion_optimization.json")
    VAR = ["fused6", "fused7", "signed7", "rw6", "srw7"]
    for doc, cap in ((M1, "表 7-1"),):
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
    print("O12 学生级  ->  M1 表 7-2（M3 侧已按审阅 §3.3 拆分删除）")
    print("=" * 92)
    d = load("o12_student_o11.json")
    for doc, cap in ((M1, "表 7-2"),):
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
    print("O10 学生级  ->  M1 O10 表（M3 侧已按审阅 §3.3 拆分删除）")
    print("=" * 92)
    d = load("o10_user_holdout.json")["results"]

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
    if not rows:
        FAIL.append("M1 O10 表: 未找到锚定行 «| 10 | 0.6631 | 0.6442 | 0.6870 |»")
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


# ---------------------------------------------------------------- M3 去重边界
def run_dedup():
    """审阅 §3.3 / §5.3：冷启动估计器结果只保留在 M1 一处。

    检查两件事：
      (a) M3 不得再把"表 8 ~ 表 12"作为**表格标题**出现（它们已移交 M1）；
      (b) M3 必须保留指向 M1 的交叉引用（含 M1、7.2、7.8）。
    """
    print("=" * 92)
    print("M3 去重边界  <-  M1 保留 O7~O12 全部表格，M3 仅保留交叉引用")
    print("=" * 92)
    t = read(os.path.join(DOCS, M3))
    lines = t.splitlines()

    bad = []
    for ln in lines:
        s = ln.strip()
        for cap in M3_FORBIDDEN_TABLE_CAPTIONS:
            # 只把"**表 N ..."形式的**表格标题**判为违规；
            # 去重说明段落中的文字提及（如"表 9–12 已删除"）不算违规。
            if s.startswith("**" + cap):
                bad.append(s[:60])
    if bad:
        for b in bad:
            FAIL.append(f"M3 仍保留已移交 M1 的表格标题: {b}")
    print(f"  已移交 M1 的表格标题（表 8~表 12）在 M3 中残留: {len(bad)} 处")

    missing = [k for k in M3_REQUIRED_XREF if k not in t]
    if missing:
        FAIL.append(f"M3 缺少指向 M1 的交叉引用标记: {', '.join(missing)}")
    print(f"  M3 -> M1 交叉引用标记缺失: {len(missing)} 处")

    # 附表编号连续性：M3 现存表格标题应为 表 1 ~ 表 N，且 N <= 7
    caps = sorted({int(m.group(1)) for m in re.finditer(r"^\*\*表 (\d+)", t, re.M)})
    print(f"  M3 现存表格标题编号: {caps if caps else '（无）'}")
    if caps and caps[-1] > 7:
        FAIL.append(f"M3 表格编号超出预期的 表 1~表 7（实测最大 = 表 {caps[-1]}）")


groups = set(a.lower() for a in sys.argv[1:]) or {"o11", "o12", "o10", "dedup"}
if "o11" in groups:
    run_o11()
if "o12" in groups:
    run_o12()
if "o10" in groups:
    run_o10()
if "dedup" in groups:
    run_dedup()

print()
print("=" * 92)
if FAIL:
    print(f"FAILURES ({len(FAIL)})")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("ALL PASS —— 论文表格与实验 JSON 逐值一致，且 M3 去重边界成立")
