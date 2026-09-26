import re, os

BIB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "references.bib"))
with open(BIB, encoding="utf-8") as f:
    text = f.read()

entries = {}
pat = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)
for m in pat.finditer(text):
    key = m.group(2).strip()
    start = m.end()
    depth = 1; i = start
    while i < len(text) and depth > 0:
        c = text[i]
        if c == '{': depth += 1
        elif c == '}': depth -= 1
        i += 1
    entries[key] = text[m.start():i]

for t in ["neurips2017posetbandits","sensors2026flowbalance","reymond2024bestarm","chang2015junyi","dellanna2025","mazarakis2024whichone","preprints2025dlktreview","baillifard2025engagement"]:
    print("\n================ %s ================" % t)
    print(entries.get(t, ">>> MISSING <<<"))
