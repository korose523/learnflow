import re, os

BIB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "references.bib"))
with open(BIB, encoding="utf-8") as f:
    text = f.read()

# brace balance check (whole file, ignoring brace chars inside field values is same as full balance)
def balance(s):
    d = 0
    for c in s:
        if c == '{': d += 1
        elif c == '}': d -= 1
    return d
print("GLOBAL BRACE BALANCE:", balance(text))

# parse entries
entries = {}
pat = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)
for m in pat.finditer(text):
    key = m.group(2).strip()
    start = m.start(); depth = 1; i = m.end()
    while i < len(text) and depth > 0:
        c = text[i]
        if c == '{': depth += 1
        elif c == '}': depth -= 1
        i += 1
    entries[key] = text[m.start():i]

keys = ["liu2025pykt","choudhary2025blockchain","razzaq2026blockchain","jusic2025microcredential",
"lieberoth2015shallow","falconcode2022","hamari2014doesgamification","rafferty2016pomdp","nafchi2025digitalfatigue",
"guadagnoli2004challengepoint","hodges2022extendedchallenge","feng2009assistments","zhang2021theoryintegration",
"raihan2025llmcsed","kcgenkt2025","kone2024banditpareto","kone2025constrainedpareto","kim2025morlportfolios",
"ballon2025estimating","li2025canllms","parfenova2025textannotation",
"neurips2017posetbandits","sensors2026flowbalance","reymond2024bestarm","chang2015junyi","dellanna2025",
"mazarakis2024whichone","preprints2025dlktreview","hepp2018originstamp","baillifard2025engagement"]

remaining_verify = 0
for k in keys:
    b = entries.get(k, "")
    nm = re.search(r'note\s*=\s*\{(.*?)\}', b, re.DOTALL)
    note = nm.group(1) if nm else "(no note)"
    has_verify = "VERIFY" in note
    if has_verify: remaining_verify += 1
    status = "OK" if not has_verify else "STILL VERIFY"
    print(f"[{status}] {k}: " + note[:70].replace('\n',' '))

print("\nTARGET ENTRIES STILL CARRYING VERIFY:", remaining_verify)

# count total VERIFY occurrences remaining in file (other pending entries)
print("TOTAL 'VERIFY' occurrences in file:", text.count("VERIFY"))
print("TOTAL entries:", len(entries))
