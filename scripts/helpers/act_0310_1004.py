# PLAIN ENGLISH (11 PM ET 10/3 slot, run 2026-10-04T0310Z): act on the Insurance Refresh Board rows William answered 02:28-03:19Z 10/4,
#   each from the LIVE chart read by reads_0310_1004.py (registers/reads_2026-10-04T0310Z.json). Every step is named by the row id.
#   A: pat17476868-17476868 - admission 09/30/2026 (HCA facesheet pat17476868.pdf: arrival 09/30/26, discharged 10/02/26) on v19456834/35/36, resave onhcfa=1.
#   B: pat17477850-17477850 - CAP07 plan CIO60196937 (no group) added, admission 09/21/2026 on the 4 HCA visits, insorder 1, released from Unbilled.
#   C: pat17477549-17477549 - Medicare member id -> the TMH id; AMD 271; freq-1 rebill the two open Medicare visits.
#   D: pat17471977-17471977 - BCBS (out-of-state Blue under car6062) VGD731W22044 begin 11/19/2025, UNI20 end-dated 11/18/2025, the 2 HCA visits moved off the patient balance to seq 2 and freq-1 rebilled.
#   E: write-offs William named: awv-pr119-0922 (WONCS G0439 x2), pat17474613 (WOLATE v19422927), pat17468923 (WONCS v19442292), fcc-co26-pat24039 (WOCAID2ND the CO-26 residual).
#   F: voids William named: pat23159 v19456297 (duplicate admission), pat45668 v19455691 (CCM after death).
#   G: pat17474611 - the 6 Nov-2025 HCA visits set to UNI20 seq 1 and freq-1 rebilled (William: send to United; untimely answer -> write off).
#   H: pat17477183 - no insurance after 8/31: the 3 open visits moved to the patient balance and released from Unbilled (WOBAD after the statement cycle, the 9/12 rule).
#   I: pat17475906 - read chart pat17475906 plans (the BlueOptions id William wants tried).
#   Dry run first (--dry): every write is printed, nothing sent. Never touches: payments already posted, hospitalizationto, group numbers, standing holds.
import amd, resave, era_post, add_ins, ins_update, freq1_visit, manual_post, move_to_ins, void_tx, elig_amd, stedi, re, json, sys, time, datetime
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-10-04T0310Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
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
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if "Fault" in r else "saved live=%d/%d onhcfa=%s insorder=%s hospfrom=%s" % (len(c2), len(allc), v2.get("onhcfa"), v2.get("insorder"), ex.get("hospitalizationfrom") if ex is not None else None)
def release(vids):
    if DRY: return "DRY release %s" % vids
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
def wo(cid, carrier, amt, code, note):
    ok, msg = manual_post.post(cid, carrier, 0.0, amt, code, checknumber="BOARD1004", note=note, dry=DRY)
    return "%s %s" % ("ok" if ok else "FAIL", msg)
def first_cid(pid, vid):
    for r in R["charts"][pid]["all"]:
        if r["visit"] == vid and r["void"] != "1": return r["id"]
def elig(pid, insid):
    try: s = elig_amd.run_plan(pid, insid, True); return elig_amd.one_line(s)[:200]
    except Exception as e: return "271 error %s" % e

# ---------------- A. pat17476868 admission 09/30/2026 ----------------
if want("pat17476868"):
    for vid in ("19456834", "19456835", "19456836"):
        cid = first_cid("17476868", vid)
        vis, pat, allc = resave.visit_charges(cid); dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}; cpt = cpts_of(allc, dets)
        L("pat17476868 v%s cpts %s insorder %s onhcfa %s" % (vid, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa")))
        for p in sorted(set(cpt.values())): L("  updextrainsinfo %s 09/30/2026 -> %s" % (p, set_date(vid, p, "09/30/2026")))
        ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": vis.get("insorder") or "2,1"}); L("  resave: " + msg); time.sleep(0.4)

# ---------------- B. pat17477850 CAP07 plan + admission + release ----------------
if want("pat17477850"):
    pid = "17477850"; plans = R["charts"][pid]["demo"]["plans"]
    have = [p for p in plans if p["carrier"] == "car41826"]
    if have: insid, seq = have[0]["id"], have[0]["sequence"]; L("pat17477850 CAP07 already on chart %s seq %s" % (insid, seq))
    elif DRY: insid, seq = "DRY", "1"; L("pat17477850 DRY add_ins CAP07 car41826 CIO60196937 begin 02/01/2026")
    else:
        insid, seq = add_ins.add(pid, "car41826", "CIO60196937", "02/01/2026"); L("pat17477850 add_ins CAP07 -> %s seq %s" % (insid, seq))
    if insid and insid != "DRY" and str(insid).startswith("ins"):
        L("  AMD 271 CAP07: " + elig(pid, insid.replace("ins", "")))
    try:
        j = stedi.elig("95112", R["charts"][pid]["demo"]["name"].split(",")[1].split()[0], R["charts"][pid]["demo"]["name"].split(",")[0], "19810826", "CIO60196937", "20260921")
        st = [b.get("name") for b in (j.get("benefitsInformation") or []) if b.get("serviceTypeCodes") and "30" in b.get("serviceTypeCodes")][:3]
        L("  Stedi CHP 95112 @9/21/2026: %s errors %s plan %s" % (st, j.get("errors"), (j.get("planInformation") or {}).get("groupDescription") or (j.get("planDateInformation") or {})))
    except Exception as e: L("  Stedi CHP error %s" % e)
    if insid and (insid == "DRY" or str(insid).startswith("ins")):
        rel = []
        for vid in ("19455898", "19455868", "19456282", "19456281"):
            cid = first_cid(pid, vid); vis, pat, allc = resave.visit_charges(cid); dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}; cpt = cpts_of(allc, dets)
            for p in sorted(set(cpt.values())): L("  v%s updextrainsinfo %s 09/21/2026 -> %s" % (vid, p, set_date(vid, p, "09/21/2026")))
            chg_over = {}
            for c in allc:
                if cpt[c.get("id")] == "99497" and "mcode7" not in (c.get("modcodes") or "").split(): chg_over[c.get("id")] = {"modcodes": ("mcode7 " + (c.get("modcodes") or "")).strip()}
            ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": str(seq)}, chg_over); L("  v%s resave: %s" % (vid, msg))
            if ok: rel.append(vid)
            time.sleep(0.4)
        L("  release %s -> %s" % (rel, release(rel) if rel else "none"))

# ---------------- C. pat17477549 new Medicare id ----------------
if want("pat17477549"):
    pid = "17477549"; NEW = json.load(open("secrets/run_inputs_2026-10-04T0310Z.json"))["pat17477549_new_medicare_id"]  # the TMH member id lives in secrets/ (PHI), never in this file
    plan = [p for p in R["charts"][pid]["demo"]["plans"] if p["carrier"] == "car6085"][0]
    if plan["subscribernum"] == NEW: L("pat17477549 Medicare id already %s" % NEW)
    elif DRY: L("pat17477549 DRY ins_update %s subscribernum %s -> %s" % (plan["id"], plan["subscribernum"], NEW))
    else: L("pat17477549 ins_update %s subscribernum -> %s: %s" % (plan["id"], NEW, ins_update.update(pid, plan["id"], subscribernum=NEW)))
    L("  AMD 271 Medicare: " + elig(pid, plan["id"].replace("ins", "")))
    for vid in ("19455707", "19452973"):
        cid = first_cid(pid, vid)
        L("  v%s freq1 seq 1 -> %s" % (vid, "DRY" if DRY else freq1_visit.run(vid, cid, 1))); time.sleep(0.4)

# ---------------- D. pat17471977 BCBS Georgia (out-of-state Blue -> car6062) ----------------
if want("pat17471977"):
    pid = "17471977"; plans = R["charts"][pid]["demo"]["plans"]
    have = [p for p in plans if p["carrier"] == "car6062"]
    if have: insid, seq = have[0]["id"], have[0]["sequence"]; L("pat17471977 BCBS already on chart %s seq %s" % (insid, seq))
    elif DRY: insid, seq = "DRY", "2"; L("pat17471977 DRY add_ins BCBS car6062 VGD731W22044 begin 11/19/2025; end-date UNI20 ins9511288 11/18/2025")
    else:
        insid, seq = add_ins.add(pid, "car6062", "VGD731W22044", "11/19/2025"); L("pat17471977 add_ins BCBS -> %s seq %s" % (insid, seq))
        L("  end-date UNI20 ins9511288 11/18/2025: %s" % (ins_update.update(pid, "ins9511288", enddate="11/18/2025"),))
    if insid and insid != "DRY" and str(insid).startswith("ins"): L("  AMD 271 BCBS: " + elig(pid, insid.replace("ins", "")))
    if insid and (insid == "DRY" or str(insid).startswith("ins")):
        for vid in ("19424212", "19424211"):
            cid = first_cid(pid, vid)
            if DRY: L("  v%s DRY move_to_ins seq %s + freq1" % (vid, seq)); continue
            L("  v%s move_to_ins seq %s: %s" % (vid, seq, move_to_ins.move(cid, str(seq))))
            L("  v%s freq1 seq %s -> %s" % (vid, seq, freq1_visit.run(vid, cid, seq))); time.sleep(0.4)

# ---------------- E. write-offs ----------------
if want("wo"):
    # awv-pr119: pat23617 v19448516 G0439 $204 on insurance (MCAD last billed; Medicare's PR-119)
    L("awv pat23617 c23357819 WONCS 204.00: " + wo("23357819", "FLO02", 204.00, "WONCS", "Medicare PR-119 AWV frequency - William 10/4 write off WONCS"))
    # awv-pr119: pat21885 v19448510 G0439 $204 sits on the PATIENT balance -> back to insurance, then WONCS
    if DRY: L("awv pat21885 c23357813 DRY move_to_ins then WONCS 204.00")
    else:
        L("awv pat21885 c23357813 move_to_ins: " + str(move_to_ins.move("23357813"))); time.sleep(0.5)
        L("awv pat21885 c23357813 WONCS 204.00: " + wo("23357813", "FLO02", 204.00, "WONCS", "Medicare PR-119 AWV frequency - William 10/4 write off WONCS"))
    # pat17474613 v19422927 11/6/2025 99306+99497 -> WOLATE (untimely to United)
    for cid, amt in (("23328277", 256.00), ("23328278", 133.00)):
        L("pat17474613 c%s WOLATE %.2f: %s" % (cid, amt, wo(cid, "UNI20", amt, "WOLATE", "Nov-2025 UHC MA claim past timely filing - William 10/4 write off untimely")))
    # pat17468923 v19442292 CCM during hospice -> WONCS
    for cid, amt in (("23350301", 206.00), ("23350302", 109.00)):
        L("pat17468923 c%s WONCS %.2f: %s" % (cid, amt, wo(cid, "FLO02", amt, "WONCS", "CCM during hospice election CO-B9 - William 10/4: CCM billed to hospice patients does not pay, write off")))
    # pat24039 FCC CO-26 residual v19453504 9/1/2026 99233 $21.80 -> WOCAID2ND
    L("pat24039 c23364201 WOCAID2ND 21.80: " + wo("23364201", "FLO99", 21.80, "WOCAID2ND", "FCC CO-26 N650 on the Medicare coinsurance residual - William 10/4 write off WOCAID2ND"))

# ---------------- F. voids ----------------
if want("void"):
    for pid, vid, cids in (("23159", "19456297", ("23367922", "23367923")), ("45668", "19455691", ("23367068", "23367069"))):
        for cid in cids:
            ch, wos, pays = void_tx.charge_state(cid)
            live_pays = [p for p in pays if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
            if live_pays: L("void pat%s v%s c%s HAS PAYMENTS %s - not voided" % (pid, vid, cid, live_pays)); continue
            L("void pat%s v%s c%s %s fee %s -> %s" % (pid, vid, cid, ch.get("proccode"), ch.get("fee"), "DRY" if DRY else void_tx.void_charge(pid, cid))); time.sleep(0.4)

# ---------------- G. pat17474611 Nov-2025 visits to UHC ----------------
if want("pat17474611"):
    pid = "17474611"
    for vid in ("19422924", "19422902", "19422901", "19422900", "19423060", "19423203"):
        cid = first_cid(pid, vid); vis, pat, allc = resave.visit_charges(cid)
        L("pat17474611 v%s insorder %s -> 1: %s" % (vid, vis.get("insorder"), full_resave(cid, {"insorder": "1"})[1]))
        L("  freq1 seq 1 -> %s" % ("DRY" if DRY else freq1_visit.run(vid, cid, 1))); time.sleep(0.4)

# ---------------- H. pat17477183 -> patient balance, release ----------------
if want("pat17477183"):
    pid = "17477183"; rel = []
    for vid in ("19455471", "19455759", "19456663"):
        cid = first_cid(pid, vid); vis, pat, allc = resave.visit_charges(cid); chg = ""; moved = 0.0
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            ib = float(c.get("insbalance") or 0)
            if ib > 0:
                a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
                a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved += ib
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        if DRY: L("pat17477183 v%s DRY move %.2f to patient + release" % (vid, moved)); rel.append(vid); continue
        va = dict(vis.attrib); va["force"] = "1"
        r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
        time.sleep(0.8); x2 = resave.detail(cid); st = re.findall(r'id="charge\d+"[^>]*?insbalance="([^"]*)" patbalance="([^"]*)"', x2)
        L("pat17477183 v%s moved %.2f to patient -> %s %s" % (vid, moved, "FAULT " + re.sub(r"\s+", " ", r[:160]) if "Fault" in r else "ok", st)); rel.append(vid)
    L("pat17477183 release %s -> %s" % (rel, release(rel)))

# ---------------- I. pat17475906 chart read ----------------
if want("pat17475906"):
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17475906", "nocookie": "1"}), timeout=120)
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    L("pat17475906 pat17475906 plans: %s" % [(p.get("id"), p.get("sequence"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate")) for p in plans])
    out["moriarty_plans"] = plans
json.dump(out, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("DONE %s" % ("DRY" if DRY else "LIVE"))
