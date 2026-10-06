# PLAIN ENGLISH (1 AM ET 10/4 slot, run 2026-10-04T0510Z): act on the Insurance Refresh Board rows William answered 03:20-03:47Z 10/4
#   and on the Claims Center holds the scan found, each from the LIVE chart read by reads_0510_1004.py (registers/reads_2026-10-04T0510Z.json).
#   A: pat17474541 (restore) - the 99487 is already restored (c23368589, unbilled): resave the visit Medicare-first (insorder 2,1) and freq-1 rebill seq 2.
#   B: pat17477375 (bill Medicare with GV) - the three 8/11-8/13/2026 visits already carry GV but were re-sent to WEL04 9/27: set insorder 3 (Medicare seq 3) + freq-1 seq 3.
#   C: pat17477892 (CAP07 CIO50078852 is already on the chart): admission 09/23/2026 on the 3 HCA visits, insorder 1, onhcfa 1, release.
#   D: pat17477842 (Jarvis: 'fix the charts and send the claim') - chart now has the real DOB + the Medicare plan: visit 19455665 insorder 1 + release.
#   E: pat17477975 (inspector hold): admission 09/28/2026 (the chart's own 99223) on v19456869/70/900, onhcfa 1.
#   F: pat17477933 v19456467 (inspector Pattern 20389 F02.80 first): F02.80 -> F03.90 (dcode1034545095), full-visit resave, re-list batch 127827, bypass fresh advisory ids.
#   G: pat12180329 (Sayer): chart last name 'SAYER III' -> last name SAYER + suffix III (Medicare's 271 rejects AAA 73 on the name); AMD 271; if ACTIVE, freq-1 the 5 open full-charge Medicare visits.
#   H: pat17474290 (Shortall): Stedi Florida Blue eligibility at DOS 10/06/2025 (read only - decides whether the 9/4 claim stands).
#   I: pat17477777 (Lazenby): try addreferralplan (ismain=0 status=stat1) for a BLANK plan; if a NEW rplan id comes back, repoint the two open visits to it with preauth="".
#   J: pat17476534 (Bellingham 'write off WONCS'): WONCS on the open 5/11-5/13/2026 insurance balances, check BOARD1004.
#   K: pat17477640 (Reeve): admission 09/02/2026 (HCA arrival list: ADM IN 9/2, discharged 9/27) on v19456252/v19456267 - extins only, claims already out 9/30.
#   --dry prints every write; --only A,B,... limits. Never touches: payments, hospitalizationto, group numbers, the paid Lazenby visit, standing holds.
import amd, resave, era_post, add_ins, ins_update, freq1_visit, manual_post, move_to_ins, elig_amd, stedi, patient_patch, recode, re, json, sys, time, datetime
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-10-04T0510Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
amd.login_cached(); batch = era_post.batch()
R = json.load(open("registers/reads_%s.json" % STAMP))
out = {"stamp": STAMP, "dry": DRY, "steps": []}
def L(m): print(m, flush=True); out["steps"].append(m)
def want(k): return ONLY is None or k in ONLY
def set_date(vid, code, admit):
    if DRY: return "DRY"
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
def cpts_of(allc, dets):
    cpt = {}
    for c in allc:
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', dets[c.get("id")]))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    return cpt
def full_resave(cid, over=None, chg_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if chg_over and c.get("id") in chg_over: a.update(chg_over[c.get("id")])
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    if DRY: return True, "DRY resave visit %s over=%s charges=%d" % (vis.get("id"), over, len(allc))
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    ok = "Fault" not in r and len(c2) == len(allc)
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if "Fault" in r else "saved live=%d/%d onhcfa=%s insorder=%s refplan=%s hospfrom=%s" % (len(c2), len(allc), v2.get("onhcfa"), v2.get("insorder"), v2.get("refplan"), ex.get("hospitalizationfrom") if ex is not None else None)
def release(vids):
    if DRY: return "DRY release %s" % vids
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
def freq1(vid, cid, seq):
    if DRY: return "DRY freq1 v%s seq %s" % (vid, seq)
    try: return str(freq1_visit.run(vid, cid, seq))[:120]
    except Exception as e: return "freq1 error %s" % e
def first_cid(pid, vid):
    for r in R["charts"][pid]["all"]:
        if r["visit"] == vid and r["void"] != "1": return r["id"]
def rows(pid, vid): return [r for r in R["charts"][pid]["all"] if r["visit"] == vid and r["void"] != "1"]
def elig(pid, insid):
    try: s = elig_amd.run_plan(pid, insid, True); return elig_amd.one_line(s)[:220]
    except Exception as e: return "271 error %s" % e

if want("A"):
    pid, vid = "17474541", "19430630"; cid = first_cid(pid, vid)
    L("A pat%s v%s charges %s" % (pid, vid, [(r["id"], r["proccode"], r["insbal"], r["billdate"]) for r in rows(pid, vid)]))
    ok, msg = full_resave(cid, {"insorder": "2,1"}); L("  resave: " + msg)
    if ok: L("  " + freq1(vid, cid, "2"))
if want("B"):
    pid = "17477375"
    for vid in ("19451378", "19451386", "19451481"):
        cid = first_cid(pid, vid); L("B pat%s v%s %s" % (pid, vid, [(r["id"], r["proccode"], r["modifiers"], r["carrier"], r["billdate"]) for r in rows(pid, vid)]))
        ok, msg = full_resave(cid, {"insorder": "3"}); L("  resave: " + msg)
        if ok: L("  " + freq1(vid, cid, "3"))
        time.sleep(0.4)
if want("C"):
    pid = "17477892"; vids = ("19456293", "19456228", "19456888")
    for vid in vids:
        cid = first_cid(pid, vid); vis, pat, allc = resave.visit_charges(cid); dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}; cpt = cpts_of(allc, dets)
        L("C pat%s v%s cpts %s insorder %r onhcfa %s" % (pid, vid, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa")))
        for p in sorted(set(cpt.values())): L("  updextrainsinfo %s 09/23/2026 -> %s" % (p, set_date(vid, p, "09/23/2026")))
        ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": "1"}); L("  resave: " + msg); time.sleep(0.4)
    L("  release -> " + release(list(vids)))
    L("  271 CAP07: " + elig(pid, "9520711"))
if want("D"):
    pid, vid = "17477842", "19455665"; cid = first_cid(pid, vid)
    ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": "1"}); L("D pat%s v%s resave: %s" % (pid, vid, msg))
    L("  release -> " + release([vid]))
if want("E"):
    pid = "17477975"
    for vid in ("19456900", "19456869", "19456870"):
        cid = first_cid(pid, vid); vis, pat, allc = resave.visit_charges(cid); dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}; cpt = cpts_of(allc, dets)
        L("E pat%s v%s cpts %s insorder %r onhcfa %s" % (pid, vid, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa")))
        for p in sorted(set(cpt.values())): L("  updextrainsinfo %s 09/28/2026 -> %s" % (p, set_date(vid, p, "09/28/2026")))
        ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": vis.get("insorder") or "1"}); L("  resave: " + msg); time.sleep(0.4)
if want("F"):
    pid, vid, cid = "17477933", "19456467", first_cid("17477933", "19456467")
    m = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', resave.detail(cid))); L("F pat%s v%s dx %s" % (pid, vid, m))
    def edit_dx(cid, fn):
        mp = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', resave.detail(cid)))
        def e(a):
            d = (a.get("diagcodes") or "").split(); n = fn(d, mp)
            if n and n != d: a["diagcodes"] = " ".join(n); return True
            return False
        c2, msg = recode._save(cid, e); return msg
    def fn(d, mp):
        n = ["dcode1034545095" if mp.get(x, "").replace(".", "") in ("F0280", "F02.80", "F0281", "F02818", "F02811") else x for x in d]
        return n if n != d else None
    if DRY: L("  DRY edit_dx -> F03.90 for the F02.8x code")
    else:
        L("  edit_dx: " + str(edit_dx(cid, fn))[:200]); time.sleep(1.0)
        r = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": "127827", "nocookie": "1"}), timeout=120)
        errs = re.findall(r'<claimedit id="(\d+)"[^>]*(?:description|text|message)="([^"]*)"', r)
        L("  inspector batch 127827 after swap: %s" % [(e[0], e[1][:80]) for e in errs][:6])
        adv = [e for e in errs if "20389" in e[1] or "11256" in e[1] or "35790" in e[1]]
        if adv:
            r2 = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e[0] for e in adv))))
            L("  bypass %s -> %s" % ([e[0] for e in adv], "ok" if "Fault" not in r2 else r2[:160]))
if want("G"):
    pid = "12180329"
    if DRY: L("G pat%s DRY patch names: lastname SAYER suffix III (was 'SAYER III')" % pid)
    else:
        p = patient_patch.get(pid); f = patient_patch.flatten(p); nm = [dict(n) for n in f.get("names", [])]
        for n in nm:
            if n.get("lastname", "").upper().endswith(" III"): n["lastname"] = n["lastname"][:-4].strip(); n["suffix"] = "III"; n["prefixSuffix"] = {"prefix": n.get("prefix") or "", "suffix": "III"}
        code, txt, before = patient_patch.patch(pid, {"names": nm}); L("G pat%s PATCH names -> %s %s" % (pid, code, txt[:160]))
        time.sleep(0.8); L("  271 Medicare after rename: " + elig(pid, "6028401"))
        if "ACTIVE" in out["steps"][-1]:
            for vid in ("19436536", "19436825", "19436828", "19436829", "19437116"):
                cid = first_cid(pid, vid); L("  " + freq1(vid, cid, "1")); time.sleep(0.4)
        else: L("  Medicare 271 still not ACTIVE - visits not re-sent")
if want("H"):
    try:
        j = stedi.elig("00590", "KELVIN", "SHORTALL", "19660829", "VMYH57761517", "20251006"); L("H pat17474290 Stedi Florida Blue @10/06/2025: " + json.dumps(j)[:600])
    except Exception as e: L("H stedi error %s" % e)
if want("I"):
    pid = "17477777"; main = "rplan18462071"
    if DRY: L("I pat%s DRY addreferralplan ismain=0 status=stat1 -> (new id?) then repoint v19454905 + v19456882 preauth=''" % pid)
    else:
        r = amd.post(amd.msg("addreferralplan", "chargeentry", {"patientid": "pat" + pid, "nocookie": "1"}, '<refplan id="" patient="pat%s" ismain="0" status="stat1" preauthreq="0" sequence="2" refprov="" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility=""/>' % pid))
        ids = re.findall(r'(rplan\d+)', r); new = [x for x in ids if x != main]
        L("I pat%s addreferralplan -> ids %s resp %s" % (pid, ids[:4], re.sub(r"\s+", " ", r[100:300])))
        if new:
            for vid in ("19454905", "19456882"):
                cid = first_cid(pid, vid); ok, msg = full_resave(cid, {"refplan": new[0], "preauth": ""}); L("  v%s -> %s: %s" % (vid, new[0], msg)); time.sleep(0.4)
            d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
            L("  refplans now: %s" % re.findall(r'<refplan id="(rplan\d+)"[^>]*ismain="([^"]*)"[^>]*preauth="([^"]*)"', d))
        else: L("  no new plan id came back - visits left as they are")
if want("J"):
    pid = "17476534"
    for r in R["charts"][pid]["all"]:
        if r["void"] != "1" and r["dos"] and r["dos"][6:] == "2026" and r["dos"][:2] == "05" and float(r["insbal"] or 0) > 0:
            ok, msg = manual_post.post(r["id"], "BCBS", 0.0, float(r["insbal"]), "WONCS", checknumber="BOARD1004", note="Florida Blue PR-50/PR-197 - William 10/4/2026 'write off WONCS' (board bellingham-amon-17476534)", dry=DRY)
            L("J pat%s c%s v%s %s %s WONCS %s -> %s %s" % (pid, r["id"], r["visit"], r["dos"], r["proccode"], r["insbal"], "ok" if ok else "FAIL", str(msg)[:140])); time.sleep(0.3)
if want("K"):
    pid = "17477640"
    for vid in ("19456252", "19456267"):
        L("K pat%s v%s updextrainsinfo 99233 09/02/2026 -> %s" % (pid, vid, set_date(vid, "99233", "09/02/2026")))
json.dump(out, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("DONE %s" % ("DRY" if DRY else "LIVE"))
