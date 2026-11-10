#!/usr/bin/env python3
"""One-off (11/10/2026, privacy review P2): take ZIP code, city, marital status and any raw 'deceased' value out of the chart-facts documents
already written, and store a birth year of 1936 or earlier as 1936 with birth_year_capped = 1. Local files only; the loader then puts the
changed documents into the database in place of the old ones.   Usage: coarsen_chartfacts.py [--dry]"""
import json, glob, os, sys
S = os.path.dirname(os.path.abspath(__file__)); dry = "--dry" in sys.argv; OLDEST = 1936
n = changed = capped = 0; dropped = {}
for f in sorted(glob.glob(os.path.join(S, "docs_chartfacts", "s*", "chartfacts", "*.json"))):
    d = json.load(open(f)); p = d.get("patient") or {}; before = json.dumps(p, sort_keys=True); n += 1
    for k in ("zip", "city", "maritalstatus", "deceased"):
        if k in p: del p[k]; dropped[k] = dropped.get(k, 0) + 1
    by = str(p.get("birth_year") or "")
    if by.isdigit():
        if int(by) <= OLDEST: p["birth_year"] = str(OLDEST); p["birth_year_capped"] = "1"; capped += 1
        else: p.setdefault("birth_year_capped", "0")
    elif "birth_year_capped" not in p: p["birth_year_capped"] = "0"
    if json.dumps(p, sort_keys=True) != before:
        changed += 1
        if not dry:
            d["patient"] = p; tmp = f + ".tmp"; json.dump(d, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, f)
print("%s%d chart-facts files read, %d changed; values taken out: %s; birth years stored as %d or earlier: %d" % ("DRY: " if dry else "", n, changed, dropped, OLDEST, capped))
