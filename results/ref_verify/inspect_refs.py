import re, json, os

BIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "references.bib")
BIB = os.path.abspath(BIB)

with open(BIB, encoding="utf-8") as f:
    text = f.read()

# Parse entries: @type{key, ... } with brace matching
entries = {}
pos = 0
pat = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)
for m in pat.finditer(text):
    etype = m.group(1)
    key = m.group(2).strip()
    start = m.end()  # after "{key,"
    # find matching closing brace
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    body = text[m.start():i]  # full entry including @type{...}
    entries[key] = body

print("TOTAL ENTRIES:", len(entries))

targets = [
    "liu2025pykt","choudhary2025blockchain","razzaq2026blockchain","jusic2025microcredential",
    "lieberoth2015shallow","falconcode2022","hamari2014doesgamification","rafferty2016pomdp","nafchi2025digitalfatigue",
    "guadagnoli2004challengepoint","hodges2022extendedchallenge","feng2009assistments","zhang2021theoryintegration",
    "raihan2025llmcsed","kcgenkt2025","kone2024banditpareto","kone2025constrainedpareto","kim2025morlportfolios",
    "ballon2025estimating","li2025canllms","parfenova2025textannotation",
    "audiffren2017bandits","rosas2026flow","reymond2024utility","chang2015modeling","dellanna2025flow",
    "mazarakis2024gamification","hepp2018originstamp","krivich2025dkt","baillifard2025engagement",
]

for t in targets:
    if t in entries:
        body = entries[t]
        # extract note
        nm = re.search(r'note\s*=\s*\{(.*?)\}', body, re.DOTALL)
        note = nm.group(1) if nm else "(no note field)"
        print("\n==== %s ====" % t)
        print("KEY FOUND. note:", note[:400])
    else:
        print("\n==== %s ====  >>> NOT FOUND IN BIB <<<" % t)

# Also list all keys containing these substrings to help debug mismatches
print("\n\n--- KEY INDEX (all keys) ---")
for k in sorted(entries.keys()):
    print(k)
