# PLAIN ENGLISH (11am ET 9/29/2026 run 2026-09-29T1510Z): the move_to_ins resave of v19455647 (pat22322, CCM 99487+99489 9/20/2026, moved
#   back from the patient balance after CHP's PR-200) re-inspected the visit and raised Pattern 35790 (add-on 99489 reported with 99487 that
#   has a review edit) = the add-on advisory the standing prompt bypasses. Re-list the batch, bypass with the FRESH error id, re-list.
# Never touches: codes, dx, balances, other visits.
import amd, re, time, xml.etree.ElementTree as ET
amd.login_cached(); BID = "127783"; TARGET = "19455647"
def listbatch(bid): return amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
def parse(t):
    return [(v.get("id"), v.get("patientid"), [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:160]) for e in v.iter("error")]) for v in ET.fromstring(t).iter("visit")]
rows = parse(listbatch(BID)); print("before:", [(v, p, [(i, t[:60]) for i, t in e]) for v, p, e in rows if v == TARGET])
for vid, pid, errs in rows:
    if vid != TARGET: continue
    ids = [i for i, t in errs if "Pattern 35790" in t]
    if not ids: print("no 35790 on", vid); continue
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
    print("bypass", vid, ids, "->", "Fault" not in r, re.sub(r"\s+", " ", r)[:160])
time.sleep(2); rows2 = parse(listbatch(BID)); print("after: visits in batch", len(rows2), "target still listed:", [v for v, p, e in rows2 if v == TARGET])
