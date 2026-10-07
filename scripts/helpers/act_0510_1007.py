# PLAIN ENGLISH (1 AM ET 10/7 slot, run 2026-10-07T0510Z - ehpa cloud copy)
# Decides: nothing new - applies the standing rules to this run's Unbilled and Exclusion rows:
#  A: pat17476358 v19457078 (HCA 99233 10/4/2026, $160) held 'Insurance order is missing on visit'. Chart (AMD 271 this run):
#     UNI20 ended 5/1/2026, FLO02 seq 2 ACTIVE (Part A/B 8/1/2024, FL QMB), SUN01 seq 3 ACTIVE and pointing at Medicare primary.
#     Admission = the most recent 99223 on/before the DOS within 45 days on that chart (gettxhistory; the 10/4 run wrote 10/01/2026
#     on the 10/1-10/2 visits of the same stay); updextrainsinfo hospitalizationfrom ONLY (never hospitalizationto); full-visit resave
#     (resave.visit_charges echo, every active charge kept) with insorder "2,3" (Medicare, then Sunshine - the order the 10/4 run gave
#     v19456840 / v19456831) and onhcfa=1; then release (hideunbillablevisits hide=-1). No 99223 anchor within 45 days = HOLD, reported.
#  B: claim run 1700276 - 3 Florida Blue Medigap secondaries (claim letter H: v19431100 pat17475338 1/27/2026 99223; v19436591 +
#     v19436827 pat12180329 3/24 + 3/28/2026) rejected CH FH PREF0283 MISSING PAYER DOC CONTROL NUM. Standing rule (9/20/2026,
#     applied 10/5 on pat17477260): a Medigap secondary already at frequency 1 is COMPLETED (hideexclusions) and left to the
#     Medicare crossover - AMD holds no payer ICN to send frequency 7. Guard: the live chart must show Medicare's non-void payment on
#     the charge (the primary adjudicated); a charge with no Medicare payment is HELD and reported instead.
#  --dry (default) prints every planned write and sends nothing; --live sends them. Register registers/act_2026-10-07T0510Z[_dry].json.
#  Never touches: payments, write-offs, hospitalizationto, insurance plans, group numbers, rebills, the standing holds
#  (pat20863 inspector CCI 24078 reopening; pat17473087 UNI20 'Medicare is primary' on run 1700266 - William's MBI).
#  Copied from act_1910_1006.py (admission-date + resave functions) and act_1005_0510.py (hideexclusions shape).
import amd, resave, txh, payreasons, re, json, sys, time, datetime
DRY = "--live" not in sys.argv
ONLY = sys.argv[sys.argv.index("--only") + 1].upper() if "--only" in sys.argv else "AB"   # approval cards run one section: --only A / --only B
STAMP = "2026-10-07T0510Z"
amd.login_cached()
out = {"stamp": STAMP, "dry": DRY, "steps": [], "hold": [], "done": []}
def L(m): print(m, flush=True); out["steps"].append(m)

def admit_for(pid, dos):
    d = datetime.datetime.strptime(dos, "%m/%d/%Y").date(); best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or not (c.get("proccode") or "").startswith("99223") or not c.get("dos"): continue
        cd = datetime.datetime.strptime(c.get("dos").strip(), "%m/%d/%Y").date()
        if cd <= d and (d - cd).days <= 45 and (best is None or cd > best): best = cd
    return best.strftime("%m/%d/%Y") if best else None
def set_date(vid, code, admit):
    if DRY: return "DRY"
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
def cpts_of(allc):
    cpt = {}
    for c in allc:
        x = resave.detail(c.get("id").replace("charge", ""))
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    return cpt
def full_resave(cid, over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    if DRY: return True, "DRY resave visit %s over=%s charges=%d" % (vis.get("id"), over, len(allc))
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    ok = "Fault" not in r and len(c2) == len(allc)
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if "Fault" in r else "saved live=%d/%d onhcfa=%s insorder=%s hospfrom=%s" % (len(c2), len(allc), v2.get("onhcfa"), v2.get("insorder"), ex.get("hospitalizationfrom") if ex is not None else None)
def release(vid):
    if DRY: return "DRY release %s" % vid
    ok, msg = payreasons.release_visit(vid); return "ok" if ok else msg
def hide_excl(runid, pairs):
    if DRY: return "DRY hideexclusions %s %s" % (runid, pairs)
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": str(runid), "hide": "-1", "nocookie": "1"},
                 "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in pairs)))
    return re.sub(r"\s+", " ", r)[:160]

# ---------------- A. Unbilled 'Insurance order is missing' ----------------
A_ROWS = [("17476358", "19457078", "23368899", "2,3")] if "A" in ONLY else []
for pid, vid, cid, order in A_ROWS:
    try:
        vis, pat, allc = resave.visit_charges(cid); cpt = cpts_of(allc)
        dos = (allc[0].get("begindate") or vis.get("date") or "").strip()
        ex = vis.find("extins"); have = ex.get("hospitalizationfrom") if ex is not None else None
        own223 = any(str(v).startswith("99223") for v in cpt.values())
        admit = dos if own223 else admit_for(pid, dos)
        L("A pat%s v%s dos %s cpts %s insorder %r onhcfa %s hospfrom-now %r -> admission %s, insorder %s" % (pid, vid, dos, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa"), have, admit, order))
        if not dos or not admit:
            L("  HOLD: %s" % ("no DOS read" if not dos else "no 99223 within 45 days of %s - admission date unknown (William)" % dos))
            out["hold"].append({"pid": pid, "vid": vid, "dos": dos, "why": "no DOS" if not dos else "no 99223 anchor within 45 days"}); continue
        for p in sorted(set(cpt.values())): L("  updextrainsinfo %s %s -> %s" % (p, admit, set_date(vid, p, admit)))
        ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": order}); L("  resave: " + msg)
        if ok:
            if not DRY:
                v2, p2, c2 = resave.visit_charges(cid)
                if v2.get("insorder") != order: L("  insorder readback %r != %s - NOT released" % (v2.get("insorder"), order)); out["hold"].append({"pid": pid, "vid": vid, "why": "insorder readback mismatch"}); continue
            L("  release: " + release(vid))
            out["done"].append({"pid": pid, "vid": vid, "dos": dos, "cpts": sorted(set(cpt.values())), "action": "admission %s, insorder %s, onhcfa=1, released" % (admit, order)})
    except Exception as ex:
        L("A EXC pat%s v%s %s" % (pid, vid, repr(ex)[:200])); out["hold"].append({"pid": pid, "vid": vid, "why": "exception " + repr(ex)[:120]})

# ---------------- B. Exclusions run 1700276 - PREF0283 Florida Blue Medigap secondaries ----------------
B_RUN = "1700276"
B_ROWS = [("17475338", "19431100", "19431100H", "23337644"), ("12180329", "19436591", "19436591H", "23343643"), ("12180329", "19436827", "19436827H", "23343875")] if "B" in ONLY else []
pairs = []
for pid, vid, claim, cid in B_ROWS:
    try:
        st = payreasons.visit_state(pid, vid, txh.fetch_visit(pid, vid))
        ch = [c for c in st if c["cid"] == cid]
        medpays = [p for c in ch for p in c["pays"] if p["void"] != "1" and p["amount"] > 0 and "FLO" in (p["carrier"] or "").upper()]
        anypays = [p for c in ch for p in c["pays"] if p["void"] != "1" and p["amount"] > 0]
        L("B pat%s v%s %s charge %s: live carrier %s insbal %s patbal %s paid %s medicare-pays %d other-pays %d" % (pid, vid, claim, cid,
          [c["carrier"] for c in ch], [c["insbalance"] for c in ch], [c["patbalance"] for c in ch], [c["paid"] for c in ch], len(medpays), len(anypays) - len(medpays)))
        if ch and medpays: pairs.append((vid, claim)); out["done"].append({"pid": pid, "vid": vid, "claim": claim, "action": "PREF0283 completed - crossover-wait rule (Medicare paid %s)" % medpays[0]["amount"]})
        else:
            L("  HOLD: no non-void Medicare payment on the charge - not completed"); out["hold"].append({"pid": pid, "vid": vid, "claim": claim, "why": "no Medicare payment on the charge"})
    except Exception as ex:
        L("B EXC pat%s v%s %s" % (pid, vid, repr(ex)[:200])); out["hold"].append({"pid": pid, "vid": vid, "why": "exception " + repr(ex)[:120]})
if pairs: L("B hideexclusions %s: %s" % (B_RUN, hide_excl(B_RUN, pairs)))
json.dump(out, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("SUMMARY done %d hold %d (dry=%s)" % (len(out["done"]), len(out["hold"]), DRY))
