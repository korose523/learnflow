# -*- coding: utf-8 -*-
"""
LearnFlow 参考文献 [VERIFY] 批量核验脚本
- DOI 条目 -> Crossref REST API
- arXiv 条目 -> arXiv API (批量)
- 缺 DOI 但可检索条目 -> Crossref query.bibliographic 标题检索
输出：人类可读摘要 + JSON 报告 (crossref_report.json)
"""
import urllib.request, urllib.parse, json, re, sys, os, html
from xml.etree import ElementTree as ET

OUT = os.path.dirname(os.path.abspath(__file__))
UA = "learnflow-verify/1.0 (mailto:learnflow@example.com)"

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

def crossref_by_doi(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        d = json.loads(get(url))["message"]
    except Exception as e:
        return {"error": str(e)}
    authors = []
    for a in d.get("author", []):
        g = a.get("given", "")
        f = a.get("family", "")
        authors.append((f + (", " + g if g else "")).strip())
    yr = ""
    for k in ("published-print", "published-online", "published", "issued"):
        if k in d and d[k].get("date-parts"):
            yr = d[k]["date-parts"][0][0]
            break
    return {
        "doi": d.get("DOI"),
        "title": d.get("title", [""])[0],
        "container": d.get("container-title", [""])[0],
        "volume": d.get("volume", ""),
        "issue": d.get("issue", ""),
        "page": d.get("page", ""),
        "year": str(yr),
        "publisher": d.get("publisher", ""),
        "authors": authors,
        "type": d.get("type", ""),
    }

def crossref_title_search(title, rows=5):
    url = "https://api.crossref.org/works?query.bibliographic=" + urllib.parse.quote(title) + "&rows=" + str(rows)
    try:
        items = json.loads(get(url))["message"]["items"]
    except Exception as e:
        return [{"error": str(e)}]
    out = []
    for d in items:
        authors = []
        for a in d.get("author", []):
            g = a.get("given", ""); f = a.get("family", "")
            authors.append((f + (", " + g if g else "")).strip())
        yr = ""
        for k in ("published-print", "published", "issued"):
            if k in d and d[k].get("date-parts"):
                yr = d[k]["date-parts"][0][0]; break
        out.append({
            "score": round(d.get("score", 0), 1),
            "doi": d.get("DOI"),
            "title": d.get("title", [""])[0],
            "container": d.get("container-title", [""])[0],
            "volume": d.get("volume", ""), "issue": d.get("issue", ""),
            "page": d.get("page", ""), "year": str(yr),
            "authors": authors[:6],
        })
    return out

def arxiv_batch(ids):
    url = "http://export.arxiv.org/api/query?id_list=" + ",".join(ids)
    data = get(url)
    ns = {"a": "http://www.w3.org/2005/Atom",
          "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(data)
    out = {}
    for e in root.findall("a:entry", ns):
        aid = e.find("a:id", ns).text.strip()
        # normalize id to bare arxiv id
        m = re.search(r"abs/([^v]+)(v\d+)?", aid)
        bare = m.group(1) if m else aid
        title = " ".join(e.find("a:title", ns).text.split())
        authors = [a.find("a:name", ns).text for a in e.findall("a:author", ns)]
        published = e.find("a:published", ns).text
        updated = e.find("a:updated", ns).text
        jref = e.find("arxiv:journal_ref", ns)
        doi = e.find("arxiv:doi", ns)
        primary = e.find("arxiv:primary_category", ns)
        out[bare] = {
            "url": aid, "title": title, "authors": authors,
            "published": published, "updated": updated,
            "journal_ref": jref.text if jref is not None else "",
            "doi": doi.text if doi is not None else "",
            "primary_category": primary.get("term") if primary is not None else "",
        }
    return out

# ----------------------------------------------------------------------------
# 1) DOI 条目（含已核验待回填与待补）
DOI_ENTRIES = {
    "liu2025pykt": "10.1109/TKDE.2025.3552759",
    "choudhary2025blockchain": "10.1007/s11042-024-20303-x",
    "razzaq2026blockchain": "10.1049/sfw2/5556408",
    "jusic2025microcredential": "10.21125/edulearn.2025.1342",
    "lieberoth2015shallow": "10.1177/1555412014559978",
    "falconcode2022": "10.1145/3545945.3569822",
    "hamari2014doesgamification": "10.1109/HICSS.2014.377",
    "rafferty2016pomdp": "10.1111/cogs.12290",
    "nafchi2025digitalfatigue": "10.2478/acc-2025-0010",
}

# 2) 缺 DOI 但可标题检索的条目
TITLE_SEARCH = {
    "guadagnoli2004challengepoint": "Challenge point: A framework for conceptualizing the effects of various practice conditions in motor learning",
    "hodges2022extendedchallenge": "An extended challenge-based framework for practice design in sports coaching",
    "feng2009assistments": "Addressing the assessment challenge with an online system that tutors as it assesses",
    "zhang2021theoryintegration": "Theory integration for lifestyle behavior change in the digital age: An adaptive decision-making framework",
}

# 3) arXiv 条目
ARXIV_IDS = {
    "raihan2025llmcsed": "2410.16349",
    "kcgenkt2025": "2502.18632",
    "kone2024banditpareto": "2311.03992",
    "kone2025constrainedpareto": "2506.08127",
    "kim2025morlportfolios": "2502.09724",
    "ballon2025estimating": "2512.14220",
    "li2025canllms": "2512.18880",
    "parfenova2025textannotation": "2512.00046",
}

report = {"doi": {}, "title_search": {}, "arxiv": {}}

print("=" * 80)
print("CROSSREF — DOI 直查")
print("=" * 80)
for key, doi in DOI_ENTRIES.items():
    r = crossref_by_doi(doi)
    report["doi"][key] = r
    print(f"\n[{key}]  {doi}")
    if "error" in r:
        print("  ERROR:", r["error"]); continue
    print("  标题:", r["title"])
    print("  载体:", r["container"], "|", r["publisher"])
    print("  卷/期/页:", r["volume"], "/", r["issue"], "/", r["page"], "| 年:", r["year"])
    print("  作者:", "; ".join(r["authors"]))

print("\n" + "=" * 80)
print("CROSSREF — 标题检索（补 DOI）")
print("=" * 80)
for key, title in TITLE_SEARCH.items():
    cands = crossref_title_search(title, rows=5)
    report["title_search"][key] = cands
    print(f"\n[{key}]  {title[:70]}...")
    for c in cands[:3]:
        if "error" in c:
            print("  ERR", c["error"]); continue
        print(f"  score={c['score']} | {c['year']} | {c['container']} | {c['volume']}/{c['issue']}/{c['page']} | DOI={c['doi']}")
        print("     ", c["title"][:80])

print("\n" + "=" * 80)
print("arXiv API — 批量")
print("=" * 80)
ax = arxiv_batch(list(ARXIV_IDS.values()))
for key, aid in ARXIV_IDS.items():
    r = ax.get(aid, {})
    report["arxiv"][key] = r
    print(f"\n[{key}]  arXiv:{aid}")
    if not r:
        print("  NOT FOUND"); continue
    print("  标题:", r["title"][:80])
    print("  作者:", "; ".join(r["authors"]))
    print("  发布:", r["published"], "| 更新:", r["updated"], "| 类别:", r["primary_category"])
    print("  journal_ref:", r["journal_ref"] or "(无，未正式发表/预印本)")
    print("  doi:", r["doi"] or "(无)")

with open(os.path.join(OUT, "crossref_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("\n\n报告已写:", os.path.join(OUT, "crossref_report.json"))
