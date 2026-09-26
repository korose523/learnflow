#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the machine-readable A4 coding item universe.

Input:
  - results/m2/a4_coderB_survey.html   (17 Ludilearn / Level Up XP items, embedded JS ITEMS)
  - results/m2/_src_snippets/habitica_items.csv   (8 HABI_* items)
  - results/m2/_src_snippets/anki_items.csv       (8 ANKI_* items)

Output:
  - results/m2/_src_snippets/ludilearn_luxp_items.csv  (17 rows)
  - results/m2/a4_items_all.csv                        (33 rows)  <- authoritative item universe

All outputs: UTF-8 without BOM, LF newlines, 5 columns:
  system,item_id,commit,source_anchor,desc_zh

No field may contain an ASCII double quote (use 「」 instead) and no field may
contain a newline -- both would break downstream CSV parsing.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SNIP = os.path.join(ROOT, "_src_snippets")

COMMIT = {
    "Ludilearn": "eb69582fb4def6e4cbb26c2146ceb90435951c53",
    "Level Up XP": "65541fdc9c77511a906353f6660e195eeaa51893",
    "Habitica": "bce89c627c756d72e6b2403a91e8ac2cf7116e4d",
    "Anki": "1f7c8d7c4c402da06ab10b8f5d0acca6d5abf748",
}

SYSTEM_ORDER = ["Ludilearn", "Level Up XP", "Habitica", "Anki"]
HEADER = ["system", "item_id", "commit", "source_anchor", "desc_zh"]


def extract_items_from_html(path: str) -> list[dict]:
    """Pull the embedded JS `const ITEMS = [...]` array out of the survey HTML."""
    text = io.open(path, encoding="utf-8").read()
    start = text.index("const ITEMS")
    start = text.index("[", start)
    # walk brackets so nested arrays / strings are handled
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    else:
        raise RuntimeError("unbalanced ITEMS array")
    raw = text[start:end]
    data = json.loads(raw)  # JS array-of-arrays with double quotes is valid JSON
    rows = []
    for item_id, system, anchor, desc in data:
        rows.append(
            {
                "system": system,
                "item_id": item_id,
                "commit": COMMIT[system],
                "source_anchor": anchor,
                "desc_zh": desc,
            }
        )
    return rows


def read_csv_rows(path: str) -> list[dict]:
    """Read a 5-column item CSV.

    External editors on this machine tend to re-save CSVs with a UTF-8 BOM,
    which silently turns the first header into '\\ufeffsystem'. We therefore
    read with utf-8-sig and, if a BOM was present, rewrite the file once
    without it so downstream consumers stay simple.
    """
    with io.open(path, "rb") as fh:
        head = fh.read(3)
    if head == b"\xef\xbb\xbf":
        print("  note: stripping BOM from %s" % os.path.basename(path))
        body = io.open(path, encoding="utf-8-sig").read()
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
    rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
    out = []
    for idx, r in enumerate(rows, start=2):
        extra = [k for k in r if k is None]
        if extra:
            # a stray comma inside a field silently forks extra columns into the
            # None key -- always fatal for downstream merging
            raise RuntimeError(
                "%s line %d: stray comma split the row into extra columns: %r"
                % (os.path.basename(path), idx, extra)
            )
        missing = [k for k in HEADER if k not in r]
        if missing:
            raise RuntimeError("%s line %d: missing columns %s" % (path, idx, missing))
        out.append(
            {
                "system": r["system"].strip(),
                "item_id": r["item_id"].strip(),
                "commit": r["commit"].strip(),
                "source_anchor": r["source_anchor"].strip(),
                "desc_zh": r["desc_zh"].strip(),
            }
        )
    return out


def validate(rows: list[dict], label: str, expect: int | None = None) -> None:
    ids = [r["item_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError("%s: duplicate item_id" % label)
    for r in rows:
        for k in HEADER:
            if not r[k]:
                raise RuntimeError("%s: empty %s in %s" % (label, k, r["item_id"]))
            if '"' in r[k]:
                raise RuntimeError('%s: ASCII quote in %s of %s' % (label, k, r["item_id"]))
            if "\n" in r[k] or "\r" in r[k]:
                raise RuntimeError("%s: newline in %s of %s" % (label, k, r["item_id"]))
        if r["system"] not in COMMIT:
            raise RuntimeError("%s: unknown system %s" % (label, r["system"]))
    if expect is not None and len(rows) != expect:
        raise RuntimeError("%s: expected %d rows, got %d" % (label, expect, len(rows)))


def write_csv(path: str, rows: list[dict]) -> None:
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with io.open(path, "rb") as fh:
        if fh.read(3) == b"\xef\xbb\xbf":
            raise RuntimeError("wrote BOM -- aborting")


def main() -> int:
    base = extract_items_from_html(os.path.join(ROOT, "a4_coderB_survey.html"))
    validate(base, "ludilearn/luxp", expect=17)
    write_csv(os.path.join(SNIP, "ludilearn_luxp_items.csv"), base)
    print("ludilearn_luxp_items.csv: %d rows" % len(base))

    extra = []
    for fn, n in (("habitica_items.csv", 8), ("anki_items.csv", 8)):
        p = os.path.join(SNIP, fn)
        if not os.path.exists(p):
            print("MISSING: %s" % p)
            continue
        rows = read_csv_rows(p)
        validate(rows, fn, expect=n)
        extra.extend(rows)
        print("%s: %d rows" % (fn, len(rows)))

    all_rows = base + extra
    all_rows.sort(key=lambda r: (SYSTEM_ORDER.index(r["system"]), r["item_id"]))
    validate(all_rows, "all")
    out = os.path.join(ROOT, "a4_items_all.csv")
    write_csv(out, all_rows)

    by_sys: dict[str, int] = {}
    for r in all_rows:
        by_sys[r["system"]] = by_sys.get(r["system"], 0) + 1
    print("a4_items_all.csv: %d rows %s" % (len(all_rows), by_sys))
    print("systems=%d" % len(by_sys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
