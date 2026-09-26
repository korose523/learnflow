import re, os

BIB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "references.bib"))
with open(BIB, encoding="utf-8") as f:
    lines = f.readlines()

# find lines (outside @entries) that contain braces; show comment lines with braces
print("--- comment/non-entry lines containing { or } ---")
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if s.startswith('%') and ('{' in ln or '}' in ln):
        print(i, repr(ln.rstrip()))

# per-entry balance
text = "".join(lines)
pat = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)
bad = []
for m in pat.finditer(text):
    key = m.group(2).strip()
    start = m.start(); depth = 1; j = m.end()
    while j < len(text) and depth > 0:
        c = text[j]
        if c == '{': depth += 1
        elif c == '}': depth -= 1
        j += 1
    body = text[m.start():j]
    d = body.count('{') - body.count('}')
    if d != 0:
        bad.append((key, d))
print("\n--- entries with non-zero brace diff ---")
for k, d in bad:
    print(k, d)
if not bad:
    print("(none — all entries balanced)")

# Also check the file head region (before first @entry) for braces
first = pat.search(text)
print("\nhead region braces:", text[:first.start()].count('{'), "open /", text[:first.start()].count('}'), "close")
