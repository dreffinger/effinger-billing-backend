#!/usr/bin/env python3
# PLAIN ENGLISH (ehpa Practice Database - the datasets a billing page carries INSIDE its HTML).
# Several boards have no database of their own: the Outstanding Claims report, the Money Ledger, the Working Denials triage, the
#   Treasury Payments page and the Button embed their dataset in the page itself, as <script type="application/json"> blocks or as
#   `const D = {...};` literals that the Button run rebuilds from the repo. The practice database sync copies those too: the routine
#   saves the page (Artifact read, path index.html, out_dir ...) and this script pulls every embedded JSON block out of the saved
#   file into <out>/snapshot_1.json, snapshot_2.json ... - the `embedded` collection artifact_copy.py then packs with the rest.
# Only valid JSON is kept (a JS literal with functions or unquoted keys is reported and skipped). Nothing is fetched here; nothing
#   leaves the workspace. Usage: python3 tools/db/artifact_embedded.py <saved page.html> <out dir>   (exit 0 even when nothing found)
import os, sys, re, json

if len(sys.argv) < 3: sys.exit("usage: artifact_embedded.py <page.html> <out dir>")
src, out = sys.argv[1], sys.argv[2]
html = open(src, encoding="utf-8", errors="replace").read()
found, skipped = [], []

def literal_end(s, i):
    """index just past the JSON-ish literal starting at s[i] ('{' or '['), honouring strings and escapes; None if unbalanced"""
    depth = 0; j = i; n = len(s); instr = None
    while j < n:
        c = s[j]
        if instr:
            if c == "\\": j += 2; continue
            if c == instr: instr = None
        elif c in "\"'": instr = c
        elif c in "{[": depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0: return j + 1
        j += 1
    return None

# 1 <script type="application/json" ...>...</script>
for m in re.finditer(r'<script[^>]*type\s*=\s*["\']application/(?:ld\+)?json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
    ident = re.search(r'id\s*=\s*["\']([^"\']+)', m.group(0)[:300]); ident = ident.group(1) if ident else "script"
    try: found.append(("script/json:" + ident, json.loads(m.group(1).strip())))
    except Exception as e: skipped.append("script/json:%s - %s" % (ident, str(e)[:80]))

# 2 const/let/var NAME = {...}; or [...];  (only literals that are valid JSON and at least 200 bytes - the page's data, not its code)
for m in re.finditer(r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?=[\[{])', html):
    i = m.end(); j = literal_end(html, i)
    if j is None or j - i < 200: continue
    lit = html[i:j]
    try: found.append(("const:" + m.group(1), json.loads(lit)))
    except Exception as e:
        if len(lit) >= 2048: skipped.append("const:%s (%d bytes) - a JS literal, not JSON" % (m.group(1), len(lit)))   # code tables; the small ones are not worth a line

os.makedirs(out, exist_ok=True)
for k, (label, obj) in enumerate(found, 1):
    body = obj if isinstance(obj, dict) else {"items": obj}
    body = dict(body); body["_embedded_from"] = label
    json.dump(body, open(os.path.join(out, "snapshot_%d.json" % k), "w"), separators=(",", ":"))
print("embedded %s: %d block(s) kept [%s]%s" % (os.path.basename(os.path.dirname(src)) or src, len(found), ", ".join(l for l, _ in found),
      ("; skipped " + "; ".join(skipped)) if skipped else ""))
