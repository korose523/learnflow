import re, os

DOCS = r"E:/learnflow/docs"
BIB = os.path.join(DOCS, "references.bib")

bib_text = open(BIB, encoding="utf-8").read()

# --- parse bib entries + preceding comment block per key ---
entry_pat = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)
entries = list(entry_pat.finditer(bib_text))
key_comments = {}
prev_end = 0
for m in entries:
    key = m.group(2).strip()
    key_comments[key] = bib_text[prev_end:m.start()]
    prev_end = m.end()

tag_pat = re.compile(r'M([123])\s*\[(\d+)\]')
m_tags = {1: {}, 2: {}, 3: {}}
for key, block in key_comments.items():
    for tm in tag_pat.finditer(block):
        man = int(tm.group(1)); num = int(tm.group(2))
        m_tags[man][num] = key

def parse_manuscript(fname):
    text = open(os.path.join(DOCS, fname), encoding="utf-8").read()
    lines = text.splitlines()
    ref_start = None
    for i, l in enumerate(lines):
        if re.match(r'^#+\s*参考文献', l.strip()) or l.strip() == '参考文献':
            ref_start = i; break
    if ref_start is None:
        for i, l in enumerate(lines):
            if re.match(r'^#+\s*References', l.strip()):
                ref_start = i; break
    body = "\n".join(lines[:ref_start]) if ref_start is not None else text
    refsec = "\n".join(lines[ref_start:]) if ref_start is not None else ""
    listed = [int(x) for x in re.findall(r'^\[\s*(\d+)\s*\]', refsec, re.MULTILINE)]
    cites = set()
    for cm in re.finditer(r'\[(\d+)(?:[,\-]\d+)*\]', body):
        cites.add(int(cm.group(1)))
    return listed, cites

print("bib entry count:", len(entries))
print("M1/M2/M3 bib-tagged numbers:",
      {m: (len(m_tags[m]), max(m_tags[m]) if m_tags[m] else 0) for m in (1, 2, 3)})
print("=" * 60)

for man, fname in [(1, "M1_难度可公度性与最优错误率_完整稿.md"),
                   (2, "M2_多干预并存学习系统的冲突结构审计_完整稿.md"),
                   (3, "M3_有序难度决策与大模型先验边界_完整稿.md")]:
    listed, cites = parse_manuscript(fname)
    bib_nums = set(m_tags[man].keys())
    listed_set = set(listed)
    seq = listed == list(range(1, len(listed) + 1))
    missing_in_bib = sorted(listed_set - bib_nums)
    missing_in_ms = sorted(bib_nums - listed_set)
    dangling = sorted(cites - listed_set)
    print(f"=== M{man} ({fname}) ===")
    print(f"  references-section: count={len(listed)} max={max(listed) if listed else 0} sequential={seq}")
    print(f"  bib-tagged:         count={len(bib_nums)} max={max(bib_nums) if bib_nums else 0}")
    print(f"  listed-but-no-bib-entry : {missing_in_bib}")
    print(f"  bib-but-not-listed      : {missing_in_ms}")
    print(f"  body-citation dangling   : {dangling}")
    if not (missing_in_bib or missing_in_ms or dangling or not seq):
        print("  >> CLEAN")
    print("-" * 60)
