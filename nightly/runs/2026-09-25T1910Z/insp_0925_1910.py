# PLAIN ENGLISH (Claim Inspector pass, 3pm ET 9/25/2026 run 2026-09-25T1910Z): one NEW row - batch 127789 v19456117 pat17472641,
#   a hospital visit from the Claimocity feed raising only "Hospitalization From Date in the Extra Info tab is empty".
# Decides: (1) DECEASED GUARD on the visit; (2) admission date = the most recent 99223 on/before the DOS within 45 days on the chart
#   (gettxhistory; if the visit itself is the 99223 the admission = its DOS); no anchor -> HOLD, never guess; (3) updextrainsinfo
#   hospitalizationfrom ONLY (never hospitalizationto) per charge code; (4) full-visit resave (resave.visit_charges echo, the void trap)
#   with onhcfa=1 so the claim is CMS-1500; (5) re-list the batch and bypass only advisory patterns with FRESH ids.
# Never touches: payments, write-offs, diagnoses, insurance plans, the standing-hold visits (pat17472874 x15, pat17474541, deceased-guard
#   and CCI / duplicate-CCM holds), anything outside batch 127789.
"""Usage: python3 insp_0925_1910.py [--dry]"""
import amd, resave, era_post, deceased_guard, txh, re, time, json, sys, datetime
DRY = "--dry" in sys.argv
STAMP = "2026-09-25T1910Z"; BID = "127789"; TARGET = "19456117"
ADV = ("Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261", "Pattern 4531")
amd.login_cached(); batch = era_post.batch()
out = {"stamp": STAMP, "dry": DRY, "steps": []}
def L(m): print(m, flush=True); out["steps"].append(m)
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
def listbatch(bid): return amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
def parse(t):
    import xml.etree.ElementTree as ET
    rows = []
    for v in ET.fromstring(t).iter("visit"):
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:160]) for e in v.iter("error")]
        rows.append((v.get("id"), v.get("patientid"), v.get("claimstatus"), errs, [(c.get("id"), c.get("proccode")) for c in v.iter("charge")]))
    return rows
def admit_for(pid, dos):
    best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or c.get("proccode") != "99223" or not c.get("dos"): continue
        cd = d(c.get("dos"))
        if cd <= dos and (dos - cd).days <= 45 and (best is None or cd > best): best = cd
    return best
def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid if not str(vid).startswith("vst") else vid, "nocookie": "1"}, ext))
def full_resave(cid, over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid)
    ok = "Fault" not in r
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if not ok else "saved live=%d/%d onhcfa=%s charges=%s" % (len(c2), len(allc), v2.get("onhcfa"), [(x.get("id"), x.get("proccode"), x.get("modcodes")) for x in c2])
rows = parse(listbatch(BID)); L("batch %s before: %s" % (BID, rows))
for vid, pid, status, errs, chgs in rows:
    if vid != TARGET: L("v%s pat%s not the target - left alone" % (vid, pid)); continue
    cid0 = chgs[0][0].replace("charge", "")
    vis, pat, allc = resave.visit_charges(cid0)
    dos = d(allc[0].get("begindate") or vis.get("date"))
    L("v%s pat%s DOS %s charges=%s facility=%s onhcfa=%s insorder=%s refplan=%s" % (vid, pid, dos, [(c.get("id"), c.get("proccode"), c.get("modcodes"), c.get("diagcodes", "")[:60]) for c in allc], vis.get("facility"), vis.get("onhcfa"), vis.get("insorder"), vis.get("refplan")))
    g = deceased_guard.check(pid, dos.strftime("%m/%d/%Y")) if hasattr(deceased_guard, "check") else None
    L("deceased guard: %s" % (g,))
    if g and ((g.get("hold") if isinstance(g, dict) else (g[0] if isinstance(g, tuple) else g is True))):
        L("HELD by the deceased guard"); continue
    codes = []
    for c in allc:
        dx = resave.detail(c.get("id").replace("charge", "")); m = re.search(r'<proccode id="%s"[^>]*code="([^"]+)"' % c.get("proccode"), dx)
        codes.append(m.group(1) if m else c.get("proccode"))
    L("CPTs: %s" % codes)
    admit = dos if "99223" in codes else admit_for(pid, dos)
    if not admit: L("HOLD: no 99223 anchor within 45 days on the chart - admission date needs William"); continue
    admit_s = admit.strftime("%m/%d/%Y"); L("admission anchor: %s" % admit_s)
    if DRY: L("DRY - would write hospitalizationfrom %s on %s and resave onhcfa=1" % (admit_s, codes)); continue
    for code in codes:
        r = set_date(vid, code, admit_s); L("updextrainsinfo %s %s -> %s" % (code, admit_s, ("Fault" not in r, re.sub(r"\s+", " ", r[:160]))))
    ok, msg = full_resave(cid0, {"onhcfa": "1"}); L("resave onhcfa=1 -> %s %s" % (ok, msg))
    det = resave.detail(cid0); m = re.search(r'<extins [^>]*>', det); L("extins readback: %s" % (m.group(0)[:300] if m else "none"))
if not DRY:
    time.sleep(3); rows2 = parse(listbatch(BID)); L("batch %s after: %s" % (BID, rows2))
    for vid, pid, status, errs, chgs in rows2:
        if vid != TARGET: continue
        ids = [e for e, t in errs if any(a in t for a in ADV)]
        if ids:
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
            L("bypass advisories %s -> %s" % (ids, "Fault" not in r))
            time.sleep(2); L("batch %s final: %s" % (BID, parse(listbatch(BID))))
json.dump(out, open("insp_0925_1910%s.json" % ("_dry" if DRY else ""), "w"), indent=1)
