# PLAIN ENGLISH (1am ET 9/22/2026 run 2026-09-22T0510Z): the 9/22 chat session's referral-plan repoint resaved old PAID hospital visits
#   and their Extra-Info admission date came back empty, so they sit in the Claim Inspector. The inspector scripts never resave a paid
#   visit (standing rule since 9/7), so this pass writes ONLY the admission date back (updextrainsinfo hospitalizationfrom, never
#   hospitalizationto) where the chart proves it: the stay's own 99223 or the most recent 99223 within 45 days (full gettxhistory).
# Never touches: charges, payments, insurance, hospitalizationto; no resave.
import amd, resave, txh, re, json, sys, time, datetime
DRY = "--dry" in sys.argv
amd.login_cached()
scan = json.load(open("scan_0912/summary_after.json"))
visits = [v for b in scan["inspector"].values() for v in b if any("Hospitalization From" in e[1] for e in v["errs"])]
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
hist = {}
def history(pid):
    if pid not in hist:
        rows = []
        for c in txh.fetch("pat" + pid).iter("charge"):
            if c.get("void") == "1" or not c.get("dos"): continue
            rows.append((d(c.get("dos")), c.get("proccode"), c.get("visit"), c.get("id")))
        hist[pid] = rows; time.sleep(0.3)
    return hist[pid]
out = []
seen = set()
for v in visits:
    vid, pid = v["vid"], v["pid"]
    if vid in seen: continue
    seen.add(vid)
    vis, pat, allc = resave.visit_charges(v["chgs"][0][0])
    ex = vis.find("extins"); hf = ex.get("hospitalizationfrom") if ex is not None else None
    dos = d(allc[0].get("begindate") or vis.get("date"))
    cpts = sorted({(re.search(r'<proccode id="%s"[^>]*?\bcode="([^"]*)"' % c.get("proccode"), resave.detail(c.get("id").replace("charge", ""))) or [None, c.get("proccode")])[1] for c in allc})
    if hf: out.append((vid, pid, "already has hospitalizationfrom %s" % hf)); print(vid, pid, "already", hf); continue
    if "99223" in cpts: adm, why = dos, "own 99223"
    else:
        a = [x for x, p, vv, c in history(pid) if p == "99223" and x <= dos and (dos - x).days <= 45]
        adm, why = (max(a), "most recent 99223 within 45d") if a else (None, "no 99223 anchor within 45 days")
    if not adm: out.append((vid, pid, "HOLD: " + why)); print(vid, pid, str(dos), cpts, "HOLD", why); continue
    if DRY: out.append((vid, pid, "DRY would set %s (%s) on %s" % (adm, why, cpts))); print(vid, pid, str(dos), cpts, "DRY", adm, why); continue
    res = []
    for code in cpts:
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
            '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, adm.strftime("%m/%d/%Y"))))
        res.append((code, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:120]))); time.sleep(0.3)
    v2, p2, c2 = resave.visit_charges(v["chgs"][0][0]); ex2 = v2.find("extins")
    out.append((vid, pid, "set %s (%s) %s -> readback %s" % (adm, why, res, ex2.get("hospitalizationfrom") if ex2 is not None else None)))
    print(vid, pid, str(dos), cpts, "SET", adm, why, res, "readback", ex2.get("hospitalizationfrom") if ex2 is not None else None)
json.dump(out, open("registers/insp_dateonly_2026-09-22T0510Z%s.json" % ("_dry" if DRY else ""), "w"), indent=1)
