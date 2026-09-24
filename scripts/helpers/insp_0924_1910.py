# PLAIN ENGLISH (inspector, 3pm ET 9/24/2026 run 2026-09-24T1910Z)
# Decides: nothing new. Re-lists inspector batch 127787, bypasses the Pattern 4531 advisory (99223 in POS 31 - a
#   provider-specialty/POS advisory in the standing BYPASSABLE set of insp_work_0911.py) on the one new visit with its
#   FRESH error id, then re-lists to confirm. Every other row is a standing hold (admission dates, deceased guard, CCI, dup CCM, 15775).
# Never touches: charges, diagnoses, insurance.
import amd, re, json, time
import xml.etree.ElementTree as ET
amd.login_cached()
def listbatch(bid): return amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
def parse(t):
    out = []
    for v in ET.fromstring(t).iter("visit"):
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:160]) for e in v.iter("error")]
        out.append((v.get("id"), v.get("patientid"), errs))
    return out
def bypass(vid, ids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"},
        '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
    return r
BID = "127787"; TARGET = "19456050"
rows = parse(listbatch(BID))
print("batch", BID, "before:", rows)
for vid, pid, errs in rows:
    if vid != TARGET: continue
    ids = [e for e, t in errs if "Pattern 4531" in t]
    if not ids: print("no 4531 error on", vid); continue
    r = bypass(vid, ids); print("bypass", vid, ids, "->", "Fault" not in r, r[:200])
time.sleep(2)
rows2 = parse(listbatch(BID))
print("batch", BID, "after:", rows2)
json.dump({"before": rows, "after": rows2}, open("insp_0924_1910.json", "w"), indent=1)
