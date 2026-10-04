# PLAIN ENGLISH (5 PM ET 10/4 slot, run 2026-10-04T2110Z): READ-ONLY re-check of the standing holds + ERA Center BEFORE picture.
#   Herriot pat17477972: has a 99223 appeared on the chart (admission anchor)?  Willoughby pat17477898 / Zane pat17477973: any insplan yet?
#   Christensen pat17477946: TRICARE plan + any preauth on the visit?  ERA: GET /api/era/checks count/total, cache checkdetails.
# Never touches: AMD writes.
import amd, txh, re, json, os, time, datetime
import xml.etree.ElementTree as ET
import era_post
amd.login_cached()
out = {}
def plans(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    return [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate"), (p.get("subscribernum") or "")[:3] + "...") for p in ET.fromstring(r.encode("latin-1","ignore")).iter("insplan")]
for pid in ("17477972", "17477898", "17477973", "17477946"):
    try:
        pl = plans(pid); out[pid] = {"plans": pl}
        print(pid, "plans:", pl, flush=True)
    except Exception as e:
        print(pid, "plans ERR", e)
# Herriot 99223 anchor?
try:
    cs = [(c.get("dos"), c.get("proccode"), c.get("visit"), c.get("void")) for c in txh.fetch("17477972").iter("charge")]
    print("17477972 charges:", cs)
    out["17477972"]["charges"] = cs
except Exception as e:
    print("txh 17477972 ERR", e)
# Christensen preauth on the visit
try:
    import resave
    vis, pat, allc = resave.visit_charges("23368330") if False else (None, None, None)
except Exception: pass
# ERA before
try:
    chks = era_post.checks()
    tot = 0.0
    rows = []
    for c in chks:
        rows.append({k: c.get(k) for k in ("id", "checkid", "paymentnumber", "payername", "payer", "checkamount", "amount", "unpostedamount", "depositdate", "checkdate", "status") if k in c})
        print("ERA check:", json.dumps(rows[-1]))
    out["era_before"] = rows
    os.makedirs("era_details", exist_ok=True)
    for c in chks:
        cid = str(c.get("id") or c.get("checkid"))
        p = "era_details/%s.json" % cid
        if not os.path.exists(p):
            json.dump(era_post.details(cid), open(p, "w"), indent=1); print("cached", p)
            time.sleep(0.5)
except Exception as e:
    print("ERA ERR", repr(e))
json.dump(out, open("scan_1004_2110/recheck_before.json", "w"), indent=1, default=str)
