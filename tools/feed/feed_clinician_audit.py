#!/usr/bin/env python3
# PLAIN ENGLISH (feed visits entered under a different clinician than their feed message names - 11/10/2026)
# Decides: nothing. Reads the registers the feed runs mirror to main - practices/ehpa/registers/feed_recon_<stamp>.json (every feed
#   message with ITS OWN clinician, field "prov") and feed_import_<stamp>.json (the profile each visit was entered under, field "prof") -
#   and lists the visits where the two differ. Until 11/10/2026 the import kept one clinician per feed patient per batch (the last message
#   read), so a resident's CCM message and the nurse practitioner's visit messages in one batch all went in under one clinician.
# Prints counts and one line per visit: batch, chart number, visit id, date of service, codes, the feed's clinician, the clinician entered.
#   No name, date of birth or member id is read or printed. Never touches AdvancedMD: whether a listed visit has since been corrected,
#   billed or paid is read in AdvancedMD (or the practice database's amd tables), and correcting one is William's decision.
# Usage: python3 tools/feed/feed_clinician_audit.py [--registers practices/ehpa/registers] [--csv out.csv]
import os, sys, re, json, glob, csv, collections
a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a else default
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGS = opt("--registers", os.path.join(ROOT, "practices", "ehpa", "registers"))
PROF = {"prof13": "physician", "prof15": "nurse practitioner"}             # the two rendering profiles of the practice
# the labels claimocity_recon.clin() writes for the practice's two clinicians (a third label is listed as 'other' and counts as a difference)
LABELS = {"Dr. Effinger (DO)": "physician", "Pamela G. (ARNP)": "nurse practitioner", "Pamela G.": "nurse practitioner"}
def feed_clinician(label):
    return LABELS.get(str(label or "").strip(), "other: " + str(label or ""))
entered = {}
for rf in sorted(glob.glob(os.path.join(REGS, "feed_import_*.json"))):
    if rf.endswith("_decisions.json"): continue
    try: reg = json.load(open(rf))
    except Exception: continue
    for r in reg.get("created", []):
        if r.get("visit"): entered[r["visit"]] = r
rows = []; seen = set(); matched = 0
for rf in sorted(glob.glob(os.path.join(REGS, "feed_recon_*.json"))):
    try: j = json.load(open(rf))
    except Exception: continue
    for r in j.get("rows", []):
        v = r.get("v")
        if not v or v not in entered or v in seen: continue
        seen.add(v); matched += 1
        feed = feed_clinician(r.get("prov")); ent = PROF.get(entered[v].get("prof"), str(entered[v].get("prof")))
        if feed != ent:
            rows.append({"batch": j.get("stamp"), "chart": r.get("p"), "visit": v, "date of service": r.get("d"), "codes": "+".join(r.get("c") or []),
                         "feed message says": feed, "entered under": ent, "charges": " ".join(entered[v].get("charges") or [])})
print("feed visits entered: %d, matched to their feed message: %d, entered under a different clinician: %d" % (len(entered), matched, len(rows)))
print("by direction:", dict(collections.Counter((r["feed message says"], r["entered under"]) for r in rows)))
print("by batch:", dict(collections.Counter(r["batch"] for r in rows)))
try:
    for r in sorted(rows, key=lambda r: (str(r["batch"]), str(r["chart"]), str(r["date of service"]))):
        print("  %s | %s | %s | %s | %s | feed: %s | entered under: %s" % (r["batch"], r["chart"], r["visit"], r["date of service"], r["codes"], r["feed message says"], r["entered under"]))
except BrokenPipeError: pass                                               # piped into head
out = opt("--csv")
if out and rows:
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("written:", out)
