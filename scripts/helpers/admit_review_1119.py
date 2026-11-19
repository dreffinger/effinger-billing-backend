# PLAIN ENGLISH (Admission-date review of the held feed stays, 11/19/2026) - READ ONLY.
# Decides: Nothing. Lists every live hospital charge of the given charts with its date, code, building, admission date on the
#          visit, insurance order (attribute and list), bill date and payments, so the standing rule can be applied:
#          admission date = the most recent 99223 on or before the visit (William 11/19: a discharge to inpatient rehab starts
#          a new admission, so a later 99223 inside what looks like one stay is valid).
import amd, txh, resave, sys, json, re, datetime
amd.login_cached(); out = {}
def d8(s):
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", s or ""); return "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else ""
for pid in sys.argv[1:]:
    rows = []
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        rows.append(a)
    rows.sort(key=lambda a: d8(a.get("dos")))
    adm = [d8(a.get("dos")) for a in rows if a.get("proccode") in ("99221", "99222", "99223", "99304", "99305", "99306")]
    seen = set(); print("\n== pat%s" % pid); out[pid] = []
    for a in rows:
        v = a.get("visit")
        if v in seen: continue
        seen.add(v)
        vis, pat, allc = resave.visit_charges(a.get("id"))
        admit = resave.admit_of(vis); lst = resave.order_list(vis)
        want = max([x for x in adm if x <= d8(a.get("dos"))] or [""])
        rec = {"vid": v, "cid": a.get("id"), "dos": a.get("dos"), "cpt": [x.get("proccode") for x in rows if x.get("visit") == v], "fac": a.get("faccode"), "prov": a.get("provcode"),
               "admit": admit, "rule_admit": want, "insorder": vis.get("insorder"), "list": lst, "billdate": a.get("billdate"), "insbal": a.get("insbal"), "paid": a.get("paid")}
        out[pid].append(rec); print("  ", rec)
json.dump(out, open("admit_review_1119.json", "w"), indent=0)
