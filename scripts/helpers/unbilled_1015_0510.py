# PLAIN ENGLISH (Unbilled column work of the 2026-10-15T0510Z run - 'Insurance order is missing' + MSP-code rows)
# Decides: Nothing on its own - each section is one chart whose coverage this run established by the cascade (AMD free 271,
#   Stedi Medicare lookup with the chart SSN, insurance discovery) or by the facesheet William pasted on the board.
#   --dry (default) plans, --live writes, --only A,B,... runs the named sections. Register registers/unbilled_1015_0510_<dry|live>.json.
# Sections:
#   A chart 17478013 (8 HCA visits 10/05-10/12/2026): William's HCA facesheet 10/15 03:41Z = Optum VA CCN, member = the VA ICN,
#     authorization VA0048867957 (VA + 10 digits, the value before the slash). Add VACCN car42025 (no group), admission 10/05/2026
#     (the 99223's own DOS) by updextrainsinfo hospitalizationfrom ONLY, full-visit resave with insorder 1, onhcfa 1, preauth on
#     the chart's referral plan, then release from Unbilled.
#   B chart 24197 (5 SNF visits 12/10-12/14/2025, Bill Insurance = No): William's HCA facesheet 10/15 03:48Z = CAPITAL HEALTH MCR
#     (Medicare Advantage) policy [member id]; CMS record says CHP HMO Medicare Risk since 05/01/2021. Add CAP07 car41826
#     (begin 05/01/2021, no group), rule B resave billins=1 finclasscode MC + insorder <chp seq>, ONE freq-1 rebill, release.
#     The BC FEDERAL EMP secondary on the sheet belongs to another subscriber - not added (report).
#   C chart 17478060 and D chart 17478062 (HCA 10/12 99223 + 10/13 99232): Stedi MBILU with the chart SSN = straight Medicare
#     (Part A/B active, stand-alone Part D only, no Advantage entity). Add FLO02 car6085 with the MBI (begin 1 year back), admission
#     10/12/2026, insorder 1, onhcfa 1, release.
#   E chart 17478058 (HCA 10/12 + 10/13, age 66, Medicare lookup ERR 72): insurance discovery = AARP MEDICARE ADVANTAGE FROM UHC
#     (LPPO) member found, plan since 02/01/2026 -> UNI20 car6404 (the AARP MA carrier), admission 10/12/2026, insorder 1, release.
#   F chart 17471019 (HCA 10/12 99223 + 10/13 99232, 'MSP code required'): AMD 271 - Florida Blue BlueOptions Standard PPO (employer
#     group) ACTIVE primary, Medicare ACTIVE secondary; age 70 with an employer group plan = MSP 12 (working aged). Write mspcode 12
#     on the Medicare plan (updateinsurance wrapped shape), admission 10/12/2026, onhcfa 1, release.
#   G chart 17477183 (HCA 10/12 99223+99497, 10/13 99233): Sunshine ended 08/31/2026 (271: SSI Non Dual MMA inactive), Florida
#     Medicaid 77027 INACTIVE at the DOS, discovery 0 coverages, no facesheet - William's standing plan on the row (10/4): patient
#     responsibility, statement cycle, then the no-pay write-off. Move the three charges to the patient balance and release.
# Rules it uses: no group numbers; one rebill per visit; hospitalizationfrom only, never hospitalizationto; VA auth = the number
#   before the slash; address placeholder untouched (charts carry a street in line 2 - reported, not changed).
# Never touches: payments, write-offs, other visits.
import amd, resave, add_ins, ins_update, freq1_visit, payreasons, json, sys, re, time, datetime
LIVE = "--live" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else set("ABCDEFG")
STAMP = "2026-10-15T0510Z"
amd.login_cached()
REG = {"stamp": STAMP, "live": LIVE, "sections": {}}
def save(): json.dump(REG, open("registers/unbilled_1015_0510_%s.json" % ("live" if LIVE else "dry"), "w"), indent=1, default=str)
def S(sec, *m):
    line = " ".join(str(x) for x in m); print(sec, line); REG["sections"].setdefault(sec, []).append(line); save()
def num(s): return re.sub(r"\D", "", str(s or ""))
def chart_visits(pid, vids):
    """first live charge id per visit (gettxhistory visitid=)"""
    import txh
    out = {}
    for vid in vids:
        root = txh.fetch_visit(pid, vid)
        cs = [c for c in root.iter("charge") if c.get("void") != "1" and c.get("visit") == str(vid)]
        out[vid] = [(num(c.get("id")), c.get("proccode"), c.get("dos"), c.get("insbal"), c.get("patbal")) for c in cs]
    return out
def hosp_from(vid, cpts, admit):
    for code in sorted(set(cpts)):
        if not LIVE: continue
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
            '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
        if "Fault" in r: return "FAULT extins %s: %s" % (code, re.sub(r"\s+", " ", r[:160]))
        time.sleep(0.4)
    return "hospitalizationfrom %s on %s" % (admit, sorted(set(cpts)))
def full_resave(cid, visit_over=None, charge_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        a.update(charge_over or {})
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(visit_over or {})
    if not LIVE: return True, "DRY resave %s charges=%d visit_over=%s charge_over=%s" % (vis.get("id"), len(allc), visit_over, charge_over)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                 "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return False, "resave FAULT %s: %s" % (vis.get("id"), re.sub(r"\s+", " ", r[:300]))
    time.sleep(0.8)
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    ok = len(c2) == len(allc)
    return ok, "resave %s live %d/%d insorder=%s onhcfa=%s preauth=%s hospfrom=%s" % (vis.get("id"), len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), v2.get("preauth"), ex.get("hospitalizationfrom") if ex is not None else None)
def release(vids):
    if not LIVE: return "DRY release %s" % list(vids)
    out = []
    for v in vids:
        ok, msg = payreasons.release_visit(v); out.append((v, "released" if ok else "FAIL " + msg[:80])); time.sleep(0.3)
    return out
def mbi_of(pid):
    j = json.load(open("patient_db/%s/[name]_[DOB].json" % pid)); return (j.get("subscriber") or {}).get("memberId")
def add_plan(sec, pid, car, member, begin, coverage="1", finclass="CC"):
    if not LIVE: S(sec, "DRY add_ins", pid, car, "member ****%s" % str(member)[-4:], begin, coverage, finclass); return None, "99"
    insid, seq = add_ins.add(pid, car, member, begin, coverage, finclass); S(sec, "add_ins ->", insid, seq); return insid, seq
def bill_hospital(sec, pid, visits, order, admit, extra_visit=None):
    """visits: {vid: [(cid, cpt, dos, ...)]}; writes admission date, resave insorder+onhcfa (+extra), releases."""
    done = []
    for vid, chs in visits.items():
        cpts = [c[1] for c in chs]
        S(sec, "v%s" % vid, cpts, "->", hosp_from(vid, cpts, admit) if LIVE else "DRY hospitalizationfrom %s" % admit)
        over = {"insorder": order, "onhcfa": "1"}; over.update(extra_visit or {})
        ok, msg = full_resave(chs[0][0], over); S(sec, "v%s" % vid, msg[:220])
        if ok: done.append(vid)
        time.sleep(0.3)
    S(sec, "release ->", release(done))

# ---- A  Cowling 17478013: VACCN + auth
if "A" in ONLY:
    try:
        pid = "17478013"; vids = ["19457321", "19457281", "19457280", "19457476", "19457471", "19457529", "19457519", "19457647"]
        plans = ins_update._plans(pid)[1]
        have = [p for p, a in plans.items() if a.get("carrier") == "car42025"]
        if have: S("A", "VACCN already on the chart", have); seq = plans[have[0]].get("sequence")
        else:
            insid, seq = add_plan("A", pid, "car42025", "[ICN]", "10/15/2025", "1", "CC")
        if LIVE:
            okp, mp = ins_update.update(pid, "ins%s" % num(insid) if not have else have[0], sequence=str(seq)); S("A", "patient order", seq, "->", okp, mp[:160])
        vis = chart_visits(pid, vids)
        bill_hospital("A", pid, vis, str(seq), "10/05/2026", {"preauth": "VA0048867957", "refplan": "rplan18462365"})
    except Exception as e: S("A", "ERROR", str(e)[:300])

# ---- B  Meyer 24197: CHP + rule B
if "B" in ONLY:
    try:
        pid = "24197"
        import txh
        root = txh.fetch(pid)
        rows = [(num(c.get("id")), c.get("visit"), c.get("proccode"), c.get("dos"), c.get("insbal"), c.get("patbal"), c.get("billins")) for c in root.iter("charge") if c.get("void") != "1" and (c.get("dos") or "").endswith("/2025") and (c.get("dos") or "").startswith("12/")]
        S("B", "12/2025 charges", rows)
        plans = ins_update._plans(pid)[1]
        have = [p for p, a in plans.items() if a.get("carrier") == "car41826"]
        if have: seq = plans[have[0]].get("sequence"); S("B", "CAP07 already on the chart", have, seq)
        else: insid, seq = add_plan("B", pid, "car41826", "CIO60089196", "05/01/2021", "1", "MC")
        if LIVE:
            okp, mp = ins_update.update(pid, "ins%s" % num(insid) if not have else have[0], sequence=str(seq)); S("B", "patient order", seq, "->", okp, mp[:160])
        byvisit = {}
        for cid, vid, cpt, dos, ib, pb, bi in rows: byvisit.setdefault(vid, []).append((cid, cpt, dos, ib, pb))
        for vid, chs in byvisit.items():
            ok, msg = full_resave(chs[0][0], {"insorder": str(seq)}, {"billins": "1", "finclasscode": "MC"}); S("B", "v%s" % vid, msg[:200])
            if ok and LIVE:
                res = freq1_visit.run(vid, chs[0][0], seq); S("B", "v%s freq1 ->" % vid, res[:160])
            time.sleep(0.3)
        S("B", "release ->", release(list(byvisit)))
    except Exception as e: S("B", "ERROR", str(e)[:300])

# ---- C / D  straight Medicare charts
for sec, pid, vids in (("C", "17478060", ["19457796", "19457779"]), ("D", "17478062", ["19457795", "19457782"])):
    if sec in ONLY:
        try:
            plans = ins_update._plans(pid)[1]
            have = [p for p, a in plans.items() if a.get("carrier") == "car6085"]
            if have: seq = plans[have[0]].get("sequence"); S(sec, "FLO02 already on the chart", have, seq)
            else: insid, seq = add_plan(sec, pid, "car6085", mbi_of(pid), "10/12/2025", "1", "MC")
            if LIVE:
                okp, mp = ins_update.update(pid, "ins%s" % num(insid) if not have else have[0], sequence=str(seq)); S(sec, "patient order", seq, "->", okp, mp[:160])
            bill_hospital(sec, pid, chart_visits(pid, vids), str(seq), "10/12/2026")
        except Exception as e: S(sec, "ERROR", str(e)[:300])

# ---- E  17478058: AARP MA from UHC -> UNI20
if "E" in ONLY:
    try:
        pid = "17478058"; vids = ["19457789", "19457775"]
        j = json.load(open("patient_db/%s/[name]_[DOB].json" % pid))
        member = next(((it.get("subscriber") or {}).get("memberId") for it in j.get("items", []) if "UNITED" in ((it.get("payer") or {}).get("name") or "").upper()), None)
        plans = ins_update._plans(pid)[1]
        have = [p for p, a in plans.items() if a.get("carrier") == "car6404"]
        if have: seq = plans[have[0]].get("sequence"); S("E", "UNI20 already on the chart", have, seq)
        else: insid, seq = add_plan("E", pid, "car6404", member, "02/01/2026", "1", "MC")
        if LIVE:
            okp, mp = ins_update.update(pid, "ins%s" % num(insid) if not have else have[0], sequence=str(seq)); S("E", "patient order", seq, "->", okp, mp[:160])
        bill_hospital("E", pid, chart_visits(pid, vids), str(seq), "10/12/2026")
    except Exception as e: S("E", "ERROR", str(e)[:300])

# ---- F  17471019: MSP code 12 on the Medicare plan, admission, release
if "F" in ONLY:
    try:
        pid = "17471019"; vids = ["19457792", "19457781"]
        if LIVE:
            ok, msg = ins_update.update(pid, "ins9510095", mspcode="12"); S("F", "mspcode 12 on ins9510095 ->", ok, msg[:200])
            r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat17471019", "nocookie": "1"}))
            S("F", "readback mspcode:", re.findall(r'<insplan id="ins9510095"[^>]*mspcode="([^"]*)"', r), "insorder", re.findall(r'<patient [^>]*insorder="([^"]*)"', r)[:1])
        else: S("F", "DRY ins_update mspcode=12 on ins9510095 (Medicare seq 2)")
        bill_hospital("F", pid, chart_visits(pid, vids), "1,2", "10/12/2026")
    except Exception as e: S("F", "ERROR", str(e)[:300])

# ---- G  17477183: patient responsibility + release
if "G" in ONLY:
    try:
        pid = "17477183"; vids = ["19457790", "19457788"]
        for vid in vids:
            vis, pat, allc = resave.visit_charges(num(chart_visits(pid, [vid])[vid][0][0])); chg = ""; moved = 0.0
            for c in allc:
                a = {"id": c.get("id")}
                for f in resave.CHG_FIELDS:
                    if c.get(f) is not None: a[f] = c.get(f)
                ib = float(c.get("insbalance") or 0)
                if ib > 0:
                    a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
                    a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved += ib
                chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
            va = dict(vis.attrib); va["force"] = "1"
            if not LIVE: S("G", "v%s DRY move %.2f to patient" % (vid, moved)); continue
            r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
            S("G", "v%s moved %.2f to patient ->" % (vid, moved), "FAULT " + re.sub(r"\s+", " ", r[:160]) if "Fault" in r else "ok"); time.sleep(0.8)
        S("G", "release ->", release(vids))
    except Exception as e: S("G", "ERROR", str(e)[:300])
save(); print("DONE", "live" if LIVE else "dry")
