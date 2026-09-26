#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate the 4-system / 33-item A4 blind coding questionnaire (single HTML file).

Input : results/m2/a4_items_all.csv   (system,item_id,commit,source_anchor,desc_zh)
Output: results/m2/a4_coder_survey_v2.html

Design constraints (these are what make the resulting kappa defensible):
  1. BLIND - the page never contains any coder's previous codes; switching the
     coder selector swaps to a separate localStorage namespace, so coderA cannot
     see coderB's answers and vice versa.
  2. CLOSED SET - every question is a radio group drawn from CODEBOOK v2 (§3.1):
     construct 6 / direction 3 (ordered) / channel 13.
  3. EVIDENCE ONLY - each item shows the pinned commit, the file:line anchor and
     a source-derived functional description. No target label is shown.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "a4_items_all.csv")
OUT = os.path.join(ROOT, "a4_coder_survey_v2.html")

NODE = r"C:/Users/mac/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"

# items where a-priori ambiguity was flagged during the coderA mapping review
FLAGGED = {
    "LUDI_5": ["construct"],
    "LUXP_11": ["construct", "channel"],
}

HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A4 外部系统机制编码问卷 v2 · 4 系统 / 33 实例</title>
<style>
  :root{
    --bg:#f7f8fa; --card:#fff; --text:#1f2328; --muted:#5b6570;
    --line:#e3e6ea; --accent:#2563eb; --accent-soft:#eff4ff;
    --ok:#16a34a; --warn:#d97706; --warn-soft:#fff7ed;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
       font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;}
  .wrap{max-width:980px;margin:0 auto;padding:28px 18px 80px}
  h1{font-size:22px;margin:0 0 6px}
  .sub{color:var(--muted);font-size:13px}
  .banner{background:var(--accent-soft);border:1px solid #c7d7fe;border-radius:10px;
          padding:12px 14px;font-size:13px;margin:16px 0;color:#1e3a8a}
  .flag{background:var(--warn-soft);border:1px solid #fed7aa;border-radius:8px;
        padding:8px 11px;font-size:12.5px;margin:8px 0 0;color:#9a3412}
  .panel{background:var(--card);border:1px solid var(--line);border-radius:12px;
         padding:16px 18px;margin-bottom:14px}
  .bar{position:sticky;top:0;z-index:5;background:var(--card);
       border:1px solid var(--line);border-radius:12px;padding:12px 16px;
       margin-bottom:16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  .bar .grow{flex:1;min-width:220px}
  select,input[type=text]{padding:7px 10px;border:1px solid var(--line);border-radius:8px;
                         font-size:14px;background:#fff}
  button{background:var(--accent);color:#fff;border:0;border-radius:8px;
         padding:9px 16px;font-size:14px;cursor:pointer}
  button.ghost{background:#fff;color:var(--accent);border:1px solid var(--accent)}
  .chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:5px 12px;
        font-size:13px;cursor:pointer}
  .chip.on{border-color:var(--accent);background:var(--accent-soft);color:#1e3a8a}
  .item{border-top:1px solid var(--line);padding:16px 0}
  .item:first-child{border-top:0;padding-top:0}
  .hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:6px}
  .id{font-weight:700;font-size:15px}
  .sys{font-size:12px;color:#fff;background:#334155;border-radius:999px;padding:2px 9px}
  .sha{font:12px ui-monospace,Menlo,Consolas,monospace;color:var(--muted)}
  .anchor{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
          color:var(--muted);word-break:break-all}
  .desc{background:#fafbfc;border-left:3px solid var(--accent);border-radius:0 8px 8px 0;
        padding:10px 12px;margin:10px 0 12px;font-size:13.5px;white-space:pre-wrap}
  .q{margin:12px 0 4px;font-weight:600;font-size:14px}
  .opts{display:flex;flex-wrap:wrap;gap:8px}
  label.opt{display:flex;align-items:flex-start;gap:7px;border:1px solid var(--line);
            border-radius:8px;padding:7px 11px;cursor:pointer;background:#fff;font-size:13px;
            max-width:100%}
  label.opt:hover{border-color:var(--accent)}
  label.opt input{accent-color:var(--accent);margin:2px 0 0}
  label.opt.on{border-color:var(--accent);background:var(--accent-soft)}
  .code{font:12px ui-monospace,Menlo,Consolas,monospace;color:var(--muted)}
  textarea{width:100%;font:12px ui-monospace,Menlo,Consolas,monospace;
           border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:8px}
  textarea.big{height:190px}
  .stat{font-size:13px;color:var(--muted)}
  .done{color:var(--ok);font-weight:600}
  .note-in{width:100%;height:44px;font:13px inherit;border:1px solid var(--line);
           border-radius:8px;padding:7px 9px;margin-top:8px}
  .sysbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
</style>
</head>
<body>
<div class="wrap">
  <h1>A4 外部系统机制编码问卷 v2</h1>
  <div class="sub">M2 论文 · 跨系统复现双编码 · __N__ 个机制实例 / __NSYS__ 个外部系统 · 闭集 CODEBOOK v2（§3.1）</div>

  <div class="banner">
    <b>编码须知</b><br>
    1. 每题给出该代码点的<b>锚点（pinned commit + file:line）</b>与<b>源码级功能描述</b>。请只依据这些信息独立判断，
       <b>不得查看或打听另一名编码者的答案</b>；切换「编码者」会切到独立的本机存档，看不到对方数据。<br>
    2. 三问均为<b>闭集单选</b>：target_construct（6 类）· direction（3 类，有序 withdraw &lt; neutral &lt; approach）· channel（13 类）。<br>
    3. 边界裁决（§3.1）：含学习者自身成就/进展反馈 → ACHIEVEMENT；纯促活无成就反馈 → ENGAGEMENT；
       相对位置/名次/分组 → SOCIAL；个性化外观或自主选择 → IDENTITY_AUTONOMY；计时/节奏/限时 → TEMPORAL；
       防作弊/限流/规则 → COMPLIANCE。<br>
    4. 若某代码点在<b>默认配置下不生效</b>或需开关开启才构建，请在备注中说明，并按<b>默认状态</b>编码。<br>
    5. 全部作答后点「生成 CSV」。答案自动存本机浏览器，可中断续填。
  </div>

  <div class="bar">
    <div class="grow">
      <div>编码者：
        <select id="coder">
          <option value="coderA">coderA</option>
          <option value="coderB">coderB</option>
        </select>
        <span class="code" id="ns"></span>
      </div>
      <div class="stat" id="stat">已作答 0 / __N__</div>
    </div>
    <button class="ghost" id="clear">清空本编码者答卷</button>
    <button id="gen">生成 CSV</button>
  </div>

  <div class="sysbar" id="sysbar"></div>
  <div class="panel" id="items"></div>

  <div class="panel" id="out" style="display:none">
    <b>生成的 CSV（可直接复制，或点下方下载）</b>
    <textarea class="big" id="csv" readonly></textarea>
    <div style="margin-top:10px;display:flex;gap:10px">
      <button id="dl">下载 CSV</button>
      <button class="ghost" id="copy">复制到剪贴板</button>
    </div>
  </div>
</div>

<script>
const SYSTEMS = __SYSTEMS__;
const CONSTRUCT = [
  ["IDENTITY_AUTONOMY","身份/自主","自我表达、个性化、自主感"],
  ["ACHIEVEMENT","成就/表现","成就、精通、等级、分数、XP、进度等『自身进展/表现反馈』"],
  ["SOCIAL","社交比较/分层","排行榜、名次、相对位置、分组/层级/地位分化"],
  ["ENGAGEMENT","参与度","参与/活跃；不含自身成就反馈的促活"],
  ["TEMPORAL","时长/节奏","计时、节奏控制、惩罚性限时"],
  ["COMPLIANCE","合规","防作弊、限速、规则引擎、安全/合规护栏"]
];
const DIRECTION = [
  ["withdraw","推开/限制","休息、保护、负向限制（强制休息、扣分、拦截）"],
  ["neutral","中性","既不促学也不限制（纯展示、纯配置）"],
  ["approach","拉回/促学","加时、增益、正向促学"]
];
const CHANNEL = [
  ["VISUAL_CUSTOMIZATION","头像/个性化"],["BADGE","徽章"],["PROGRESS_BAR","进度条"],
  ["LEADERBOARD","排行榜/名次"],["SCORE_PANEL","分数/数值面板"],["TIMER","计时器"],
  ["CHEATGUARD","防作弊拦截"],["GROUPING","分组"],["LEVEL_INFO","等级/经验信息"],
  ["NOTIFICATION","通知/横幅"],["RATE_LIMIT","限流窗口"],
  ["RULE_ENGINE","规则引擎"],["XP_STATE","经验状态"]
];
const ITEMS = __ITEMS__;
const FLAGGED = __FLAGGED__;

let answers = {};
let notes = {};
const coderSel = document.getElementById("coder");
const key = () => "a4_survey_v2_" + coderSel.value;
const keyN = () => "a4_survey_v2_" + coderSel.value + "_notes";

function load() {
  answers = JSON.parse(localStorage.getItem(key()) || "{}");
  notes = JSON.parse(localStorage.getItem(keyN()) || "{}");
}
function save() {
  localStorage.setItem(key(), JSON.stringify(answers));
  localStorage.setItem(keyN(), JSON.stringify(notes));
}

function opts(name, list) {
  return list.map(function (row) {
    const code = row[0], label = row[1], hint = row[2];
    return '<label class="opt"><input type="radio" name="' + name + '" value="' + code + '">' +
      '<span><b>' + label + '</b> <span class="code">' + code + '</span>' +
      (hint ? '<br><span class="code">' + hint + '</span>' : '') + '</span></label>';
  }).join("");
}

function flagHtml(id) {
  const f = FLAGGED[id];
  if (!f) return "";
  const zh = f.map(function (x) { return x === "construct" ? "target_construct" : x; }).join(" / ");
  return '<div class="flag">⚠ 事先标注的歧义项（' + zh + '）：请在下方备注写明你的裁定依据。</div>';
}

let filter = "ALL";

function render() {
  const list = ITEMS.filter(function (it) { return filter === "ALL" || it.system === filter; });
  document.getElementById("items").innerHTML = list.map(function (it) {
    return '<div class="item" data-item="' + it.item_id + '">' +
      '<div class="hd"><span class="id">' + it.item_id + '</span>' +
      '<span class="sys">' + it.system + '</span>' +
      '<span class="sha">' + it.commit.slice(0, 7) + '</span>' +
      '<span class="anchor">' + it.anchor + '</span></div>' +
      '<div class="desc">' + it.desc + '</div>' + flagHtml(it.item_id) +
      '<div class="q">Q1 · target_construct（该代码点意图触发的行为科学构念）</div>' +
      '<div class="opts">' + opts(it.item_id + "__c", CONSTRUCT) + '</div>' +
      '<div class="q">Q2 · direction（干预的语义方向，有序 withdraw &lt; neutral &lt; approach）</div>' +
      '<div class="opts">' + opts(it.item_id + "__d", DIRECTION) + '</div>' +
      '<div class="q">Q3 · channel（干预落地的载体/通道）</div>' +
      '<div class="opts">' + opts(it.item_id + "__h", CHANNEL) + '</div>' +
      '<input class="note-in" type="text" data-note="' + it.item_id + '" placeholder="备注（可选；歧义项请写裁定依据）" value="' +
        (notes[it.item_id] || "").replace(/"/g, "&quot;") + '">' +
      '</div>';
  }).join("");

  document.querySelectorAll("input[type=radio]").forEach(function (r) {
    if (answers[r.name] === r.value) { r.checked = true; r.closest("label").classList.add("on"); }
    r.addEventListener("change", function () {
      answers[r.name] = r.value;
      document.querySelectorAll('input[name="' + r.name + '"]').forEach(function (x) {
        x.closest("label").classList.remove("on");
      });
      r.closest("label").classList.add("on");
      save();
      stat();
    });
  });
  document.querySelectorAll("input[data-note]").forEach(function (t) {
    t.addEventListener("input", function () {
      notes[t.getAttribute("data-note")] = t.value;
      save();
    });
  });
  stat();
}

function answeredCount() {
  return ITEMS.filter(function (it) {
    return answers[it.item_id + "__c"] && answers[it.item_id + "__d"] && answers[it.item_id + "__h"];
  }).length;
}
function stat() {
  const n = answeredCount();
  const el = document.getElementById("stat");
  el.innerHTML = '已作答 <b class="' + (n === ITEMS.length ? "done" : "") + '">' + n + ' / ' +
    ITEMS.length + '</b>' + (n === ITEMS.length ? " ✓ 全部完成，可生成 CSV" : "（每题需三问全答）");
}

function renderSysbar() {
  document.getElementById("sysbar").innerHTML =
    ['ALL'].concat(SYSTEMS).map(function (s) {
      const label = s === "ALL" ? "全部（" + ITEMS.length + "）" :
        s + "（" + ITEMS.filter(function (i) { return i.system === s; }).length + "）";
      return '<span class="chip' + (filter === s ? " on" : "") + '" data-sys="' + s + '">' + label + '</span>';
    }).join("");
  document.querySelectorAll(".chip[data-sys]").forEach(function (c) {
    c.addEventListener("click", function () {
      filter = c.getAttribute("data-sys");
      renderSysbar();
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

function esc(v) {
  v = String(v == null ? "" : v);
  return /[",\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}

function buildCsv() {
  const coder = coderSel.value;
  const rows = [["system", "item_id", "commit", "target_construct", "direction", "channel",
                 "coder", "source_anchor", "note"]];
  ITEMS.forEach(function (it) {
    rows.push([it.system, it.item_id, it.commit, answers[it.item_id + "__c"] || "",
               answers[it.item_id + "__d"] || "", answers[it.item_id + "__h"] || "",
               coder, it.anchor, notes[it.item_id] || ""]);
  });
  return rows.map(function (r) { return r.map(esc).join(","); }).join("\\n");
}

document.getElementById("gen").addEventListener("click", function () {
  const n = answeredCount();
  if (n < ITEMS.length) {
    if (!confirm("尚有 " + (ITEMS.length - n) + " 题未答完。仍要生成（未答项留空）？")) return;
  }
  document.getElementById("csv").value = buildCsv();
  document.getElementById("out").style.display = "block";
  document.getElementById("out").scrollIntoView({ behavior: "smooth" });
});
document.getElementById("dl").addEventListener("click", function () {
  const blob = new Blob(["\\ufeff" + buildCsv()], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "a4_" + coderSel.value + "_survey_v2.csv";
  a.click();
  URL.revokeObjectURL(a.href);
});
document.getElementById("copy").addEventListener("click", async function () {
  await navigator.clipboard.writeText(buildCsv());
  alert("CSV 已复制到剪贴板");
});
document.getElementById("clear").addEventListener("click", function () {
  if (!confirm("清空『" + coderSel.value + "』本机已保存的答卷？")) return;
  localStorage.removeItem(key());
  localStorage.removeItem(keyN());
  load();
  render();
});
coderSel.addEventListener("change", function () {
  load();
  document.getElementById("ns").textContent = "存档键：" + key();
  render();
  stat();
});

load();
document.getElementById("ns").textContent = "存档键：" + key();
renderSysbar();
render();
</script>
</body>
</html>
"""


def main() -> int:
    rows = list(csv.DictReader(io.open(SRC, encoding="utf-8-sig")))
    if not rows:
        print("empty item universe")
        return 1

    systems: list[str] = []
    for r in rows:
        if r["system"] not in systems:
            systems.append(r["system"])

    items = [
        {
            "item_id": r["item_id"],
            "system": r["system"],
            "commit": r["commit"],
            "anchor": r["source_anchor"],
            "desc": r["desc_zh"],
        }
        for r in rows
    ]
    for it in items:
        for k, v in it.items():
            if '"' in v:
                raise RuntimeError("ASCII quote in %s.%s" % (it["item_id"], k))
            if "\n" in v:
                raise RuntimeError("newline in %s.%s" % (it["item_id"], k))

    html = HTML_HEAD
    html = html.replace("__N__", str(len(items)))
    html = html.replace("__NSYS__", str(len(systems)))
    html = html.replace("__SYSTEMS__", json.dumps(systems, ensure_ascii=False))
    html = html.replace("__ITEMS__", json.dumps(items, ensure_ascii=False, indent=1))
    html = html.replace("__FLAGGED__", json.dumps(FLAGGED, ensure_ascii=False))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)

    # syntax-check the embedded JS
    start = html.index("<script>") + len("<script>")
    end = html.index("</script>")
    js = html[start:end]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(js)
        tmp = tf.name
    try:
        subprocess.run([NODE, "--check", tmp], check=True)
    finally:
        os.unlink(tmp)

    print("wrote %s" % OUT)
    print("items=%d systems=%d %s" % (len(items), len(systems), systems))
    print("per-system:", {s: sum(1 for i in items if i["system"] == s) for s in systems})
    print("node --check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
