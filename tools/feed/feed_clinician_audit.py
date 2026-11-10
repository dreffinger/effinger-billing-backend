#!/usr/bin/env python3
# PLAIN ENGLISH (feed visits entered under a different clinician than their feed message names - 11/10/2026)
# Decides: nothing. Reads the registers the feed runs mirror to main - practices/ehpa/registers/feed_recon_<stamp>.json (every feed
#   message with ITS OWN clinician, field "prov") and feed_import_<stamp>.json (the profile each visit was entered under, field "prof") -
#   and lists the visits where the two differ. Until 11/10/2026 the import kept one clinician per feed patient per batch (the last message
#   read), so a resident's CCM message and the nurse practitioner's visit messages in one batch all went in under one clinician.
# Prints counts and one line per visit: batch, chart number, visit id, date of service, codes, the feed's clinician, the clinician entered.
#   No name, date of birth or member id is read or printed. Never touches AdvancedMD: whether a listed visit has since been corrected,
#   billed or paid is read in AdvancedMD (or the practice database's amd tables), and correcting one is William's decision.
# Second part (11/10/2026 review): the same fault also put visits in the patient's last-read BUILDING. The registers do not keep each
#   message's own building, so this part can only list what the registers show: visits whose code family does not fit the kind of
#   building they were entered in (a nursing code at the hospital or an assisted-living facility, a hospital code outside the hospital,
#   a home code in a nursing building or the hospital, care management at the hospital), and how many charts have visits entered both at
#   the hospital location with a nursing code and in a nursing building (the feed inspector step moves a nursing code at the hospital
#   location to the HCA REHAB unit afterwards - its own register says which; this list is the import's entry, not the final state).
# Usage: python3 tools/feed/feed_clinician_audit.py [--registers practices/ehpa/registers] [--csv out.csv] [--buildings-csv out2.csv]
import os, sys, re, json, glob, csv, collections
a = sys.argv[1:]
def opt(name, default=None):
    if name not in a: return default
    if a.index(name) + 1 >= len(a) or a[a.index(name) + 1].startswith("--"): sys.exit("%s needs a file or folder name after it" % name)
    return a[a.index(name) + 1]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGS = opt("--registers", os.path.join(ROOT, "practices", "ehpa", "registers"))
if not os.path.isdir(REGS): sys.exit("registers folder not found: %s" % REGS)
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
_nc = sorted(v for v in entered if v not in seen)
if _nc: print("not compared (no feed message found for the visit): %d - %s" % (len(_nc), " ".join(_nc[:40])))
print("by direction:", dict(collections.Counter((r["feed message says"], r["entered under"]) for r in rows)))
print("by batch:", dict(collections.Counter(r["batch"] for r in rows)))
try:
    for r in sorted(rows, key=lambda r: (str(r["batch"]), str(r["chart"]), str(r["date of service"]))):
        print("  %s | %s | %s | %s | %s | feed: %s | entered under: %s" % (r["batch"], r["chart"], r["visit"], r["date of service"], r["codes"], r["feed message says"], r["entered under"]))
except BrokenPipeError: pass                                               # piped into head
# ---- buildings: code family against the kind of building the visit was entered in ------------------------------------------------------
KIND = {"fac29": "hospital", "fac67": "hospital rehab unit", "fac34": "nursing", "fac32": "nursing", "fac33": "nursing", "fac58": "nursing", "fac1350": "nursing",
        "fac37": "home / ALF", "fac55": "home / ALF", "fac53": "home / ALF", "fac54": "home / ALF", "fac38": "home / ALF", "fac65": "home / ALF", "fac57": "home / ALF"}
NURSING = set("99304 99305 99306 99307 99308 99309 99310 99315 99316".split()); HOSPITAL = set("99221 99222 99223 99231 99232 99233 99234 99235 99236 99238 99239".split())
HOME = set("99341 99342 99344 99345 99347 99348 99349 99350".split()); CCMC = {"99487", "99489"}
def misfit(codes, kind):
    c = set(codes or ())
    if kind == "hospital": return "nursing code at the hospital" if c & NURSING else "home code at the hospital" if c & HOME else "care management at the hospital" if c & CCMC else ""
    if kind == "nursing": return "hospital code in a nursing building" if c & HOSPITAL else "home code in a nursing building" if c & HOME else ""
    if kind == "home / ALF": return "nursing code at an assisted-living facility" if c & NURSING else "hospital code at an assisted-living facility" if c & HOSPITAL else ""
    if kind == "hospital rehab unit": return ""
    return "building not in the facility table" if (c & (NURSING | HOSPITAL | HOME | CCMC)) else ""
brows = []; by_chart = collections.defaultdict(set)
for v, r in sorted(entered.items()):
    kind = KIND.get(r.get("fac") or "", "unknown"); by_chart[r.get("pid")].add(kind)
    why = misfit(r.get("cpts"), kind)
    if why: brows.append({"chart": r.get("pid"), "visit": v, "date of service": r.get("dos"), "codes": "+".join(r.get("cpts") or []), "entered in": r.get("fac") or "(none)", "kind of building": kind, "does not fit": why})
both = sorted(p for p, ks in by_chart.items() if "nursing" in ks and any(b["chart"] == p and b["does not fit"] == "nursing code at the hospital" for b in brows))
print("buildings (as the import entered them; the registers do not keep each message's own building): %d visit(s) whose codes do not fit the building" % len(brows))
print("by kind:", dict(collections.Counter(b["does not fit"] for b in brows)))
print("charts with a nursing code entered at the hospital AND visits entered in a nursing building: %d" % len(both))
try:
    for b in brows: print("  %s | %s | %s | %s | entered in %s (%s) | %s" % (b["chart"], b["visit"], b["date of service"], b["codes"], b["entered in"], b["kind of building"], b["does not fit"]))
except BrokenPipeError: pass
bout = opt("--buildings-csv")
if bout and brows:
    with open(bout, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(brows[0].keys())); w.writeheader(); w.writerows(brows)
    print("written:", bout)
out = opt("--csv")
if out and rows:
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("written:", out)
