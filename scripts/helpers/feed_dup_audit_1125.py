#!/usr/bin/env python3
# PLAIN ENGLISH (READ-ONLY audit of the charts the Claimocity feed made since 10/28/2026: which of them duplicate a chart the patient
#   already had - William 11/25/2026: 'correct every one that comes to the correct date of birth and insurance ... figure out how to do this
#   for other charts that have the same mistake where we know the correct dob but claimocity sends the wrong one or the 01011900 default date')
# Decides: nothing in AdvancedMD - it changes NOTHING. For each feed-made chart F: getdemographic (name, birth date, plans' member numbers),
#   lookuppatient 'LAST,FIR%' (first three letters of the first name), and for every OTHER chart O under that name its birth date and member
#   numbers. F is a LIKELY DUPLICATE of O when (1) the birth dates are the same; (2) they differ by a slip (one digit, two neighbouring digits
#   swapped, month and day swapped, one day apart); (3) F carries 01/01/1900 or no date and every same-name chart with a real date carries ONE
#   date; (4) a member number of F equals one of O (letters and digits only, a leading three-letter prefix dropped, 8+ characters). Two
#   charts whose Social Security numbers both exist and differ are two people - never a duplicate.
# Writes registers/feed_duplicate_audit_<stamp>.json: chart ids, which test fired, each chart's live charge count and open balance - no names,
#   no dates. Prints one line per likely duplicate for the card (both chart ids, which holds the older history, the test, visits and dollars on F)
#   and lists the feed charts that still carry 01/01/1900 / no birth date and those with NO plan and an open balance.
# Never touches: AMD writes, the patient map. Usage: python3 feed_dup_audit_1125.py <chart id>[,<chart id>...] [--stamp S]
import amd, txh, json, re, sys, os, datetime, itertools
STAMP = sys.argv[sys.argv.index("--stamp") + 1] if "--stamp" in sys.argv else "2026-11-25T0721Z"
IDS = [x for x in sys.argv[1].split(",") if x]
amd.login_cached()
def demo(pid):
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    m = re.search(r'<patient [^>]*>', t)
    if not m: return None
    pa = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', t)]
    return {"name": pa.get("name") or "", "dob": pa.get("dob") or "", "ssn": pa.get("ssn") or "", "members": [p.get("subscribernum") or "" for p in plans], "plans": len(plans)}
def lookup(last, first3):
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": "%s,%s%%" % (last, first3), "nocookie": "1"}), timeout=120)
    return [re.sub(r"\D", "", x) for x in re.findall(r'<patient id="([^"]*)"', r)]
def norm_member(s):
    s = re.sub(r"[^A-Za-z0-9]", "", s or "").upper()
    if len(s) >= 11 and s[:3].isalpha(): s = s[3:]
    return s if len(s) >= 8 else ""
def digits(d): return re.sub(r"\D", "", d or "")
def slip(a, b):
    """birth dates as mm/dd/yyyy strings: equal; one digit off; two neighbouring digits swapped; month/day swapped; one day apart."""
    da, db = digits(a), digits(b)
    if not da or not db or len(da) != 8 or len(db) != 8: return None
    if da == db: return "same birth date"
    if sum(x != y for x, y in zip(da, db)) == 1: return "one digit differs"
    if any(da[:i] + da[i + 1] + da[i] + da[i + 2:] == db for i in range(7)): return "two neighbouring digits swapped"
    if a[:2] == b[3:5] and a[3:5] == b[:2] and a[6:] == b[6:]: return "month and day swapped"
    try:
        x = datetime.datetime.strptime(a, "%m/%d/%Y"); y = datetime.datetime.strptime(b, "%m/%d/%Y")
        if abs((x - y).days) == 1: return "one day apart"
    except Exception: pass
    return None
def balance(pid):
    root = txh.fetch(pid); n = 0; bal = 0.0; first = None
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        n += 1; bal += float(c.get("insbal") or 0) + float(c.get("patbal") or 0)
        d = c.get("dos"); k = d[-4:] + d[:5]
        if first is None or k < first: first = k
    return n, round(bal, 2), first
out = {"stamp": STAMP, "audited": len(IDS), "duplicates": [], "placeholder_dob": [], "no_plan_open": [], "errors": []}
for F in IDS:
    try:
        f = demo(F)
        if not f: out["errors"].append(F); continue
        last, _, first = f["name"].partition(",")
        placeholder = (not f["dob"]) or f["dob"].startswith("01/01/1900")
        nF, balF, firstF = balance(F)
        if placeholder: out["placeholder_dob"].append({"F": F, "charges": nF, "open": balF})
        if f["plans"] == 0 and balF > 0: out["no_plan_open"].append({"F": F, "charges": nF, "open": balF})
        others = [o for o in lookup(last.strip(), first.strip()[:3]) if o != F]
        real_dates = set()
        cands = []
        for O in others:
            o = demo(O)
            if not o: continue
            if o["dob"] and not o["dob"].startswith("01/01/1900"): real_dates.add(o["dob"])
            cands.append((O, o))
        for O, o in cands:
            if f["ssn"] and o["ssn"] and f["ssn"] != o["ssn"]: continue
            test = None
            s = slip(f["dob"], o["dob"]) if not placeholder else None
            if s: test = s
            elif placeholder and len(real_dates) == 1 and o["dob"] in real_dates: test = "placeholder birth date, one real date on the same name"
            else:
                mf = {norm_member(x) for x in f["members"]} - {""}; mo = {norm_member(x) for x in o["members"]} - {""}
                if mf & mo: test = "same member number"
            if test:
                nO, balO, firstO = balance(O)
                out["duplicates"].append({"F": F, "O": O, "test": test, "F_charges": nF, "F_open": balF, "O_charges": nO, "O_open": balO,
                                          "older_history": O if (firstO or "9") < (firstF or "9") else F})
                print("LIKELY DUPLICATE: feed chart %s ~ chart %s (%s) - older history on %s; F holds %d charge(s), $%.2f open" % (F, O, test, out["duplicates"][-1]["older_history"], nF, balF), flush=True)
    except Exception as e:
        out["errors"].append("%s: %s" % (F, str(e)[:120])); print("ERR", F, str(e)[:120], flush=True)
print("audited %d charts: %d likely duplicate(s), %d with a placeholder / no birth date, %d with no plan and an open balance, %d error(s)" % (len(IDS), len(out["duplicates"]), len(out["placeholder_dob"]), len(out["no_plan_open"]), len(out["errors"])))
json.dump(out, open("registers/feed_duplicate_audit_%s.json" % STAMP, "w"), indent=1)
print("register: registers/feed_duplicate_audit_%s.json" % STAMP)
