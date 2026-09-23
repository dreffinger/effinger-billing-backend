#!/usr/bin/env python3
# PLAIN ENGLISH (Paper-EOB wrong-insurance denials: fix the chart to what Stedi/CMS/AMD-271 proved, then rebill)
# Decides: Nothing - executes the per-patient plan decided from the 9/23 lookups (medfirst_20260923.json + the Stedi BCBSF / UHC /
#          Medicaid / discovery answers in patient_db/): add the Medicare plan (MBI) and bill Medicare first; end-date the Florida
#          Blue plan the day before the first denied DOS; add the AARP/UHC supplement discovery found and bill it the Medicare
#          coinsurance; move a Medicare coinsurance with no supplement left, or an uninsured primary balance, to the patient.
# Rules it uses: frequency 1 before every rebill; full-visit echo (void trap); one login; register every step; never a payment or write-off.
# Never touches: patient (BlueMedicare payer setup is William's), patient (already paid by Humana), patient (no balance).
# ---
"""Usage: python3 cascade_act_0923.py [--dry] [--only PID]"""
import amd, elig_amd, resave, add_ins, ins_update, move_to_ins, freq1_visit, txh, payreasons
import json, sys, time, re, datetime, os
DRY = "--dry" in sys.argv; ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
SCANS = "/home/claude/scans"; REG = os.path.join(SCANS, "cascade_act_0923_register.json")
reg = json.load(open(REG)) if os.path.exists(REG) else []
CAR = json.load(open("carriers.json"))
def log(pid, what, res):
    reg.append({"pid": pid, "what": what, "result": str(res)[:220], "at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "dry": DRY}); json.dump(reg, open(REG, "w"), indent=1)
    print("  ", pid, what, "->", str(res)[:160], flush=True)

def move_to_pat(cid):
    """Reverse of move_to_ins.move: the visit's insurance balance becomes patient responsibility (full-visit echo)."""
    vis, pat, allc = resave.visit_charges(cid)
    if not any(c.get("id") == "charge" + cid for c in allc): return "charge not live on visit"
    chg = ""; moved = 0.0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        if c.get("void") != "1":
            ib = float(c.get("insbalance") or 0)
            if ib > 0:
                a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
                a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"
                moved += ib
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    if moved == 0: return "nothing to move"
    if DRY: return "DRY move %.2f to patient" % moved
    va = dict(vis.attrib); va["force"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    time.sleep(0.8); x2 = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x2)
    return "moved %.2f to patient -> %s" % (moved, dict(re.findall(r'(insbalance|patbalance)="([^"]*)"', m.group(0))))

def plans(pid):
    pa, pl = elig_amd.plans(pid)
    return pa, [{"id": p.get("id"), "code": CAR.get(p.get("carrier"), ["?"])[0], "seq": p.get("sequence"), "end": p.get("enddate"), "begin": p.get("begindate"), "sub": p.get("subscribernum", "")} for p in pl]

def cids_of(pid, vid):
    ch = payreasons.visit_state(pid, vid, txh.fetch_visit(pid, vid)); return [str(c["cid"]) for c in ch], ch

def rebill(pid, vid, order, seq):
    cids, ch = cids_of(pid, vid)
    if not cids: return log(pid, "rebill %s" % vid, "no live charges")
    if DRY: return log(pid, "rebill %s seq %s order %s" % (vid, seq, order), "DRY %s" % [(c["cpt"], c["insbalance"], c["patbalance"], c["carrier"]) for c in ch])
    r1 = freq1_visit.run(vid, cids[0], int(seq)); time.sleep(0.6)
    r2 = move_to_ins.move(cids[0], order, rebill_seq=int(seq)); time.sleep(0.6)
    log(pid, "rebill %s seq %s order %s" % (vid, seq, order), "%s | %s" % (r1, r2))

def add_plan(pid, carrier, member, begin):
    if DRY: return log(pid, "add plan %s %s… begin %s" % (carrier, member[:3], begin), "DRY"), ("insDRY", "9")
    insid, seq = add_ins.add(pid, carrier, member, begin); log(pid, "add plan %s %s… begin %s" % (carrier, member[:3], begin), (insid, seq)); return None, (insid, seq)

def end_plan(pid, insid, enddate):
    if DRY: return log(pid, "end-date %s %s" % (insid, enddate), "DRY")
    log(pid, "end-date %s %s" % (insid, enddate), ins_update.update(pid, insid, enddate=enddate))

def set_order(pid, insid, order):
    if DRY: return log(pid, "chart order %s via %s" % (order, insid), "DRY")
    log(pid, "chart order %s via %s" % (order, insid), ins_update.update(pid, insid, sequence=order))

def med_first(pid, mbi, partb_start, wrong_ins, wrong_end, visits):
    """Add FLO02 when missing, order Medicare first, end-date the wrong primary, freq-1 rebill the visits to Medicare."""
    pa, pl = plans(pid)
    med = next((p for p in pl if p["code"] == "FLO02" and not p["end"]), None)
    if not med:
        b = partb_start; begin = "%s/%s/%s" % (b[4:6], b[6:8], b[:4]) if b else None
        _, (insid, seq) = add_plan(pid, "car6085", mbi, begin); med = {"id": insid, "seq": str(seq)}
    if wrong_ins: end_plan(pid, wrong_ins, wrong_end)
    pa, pl = plans(pid) if not DRY else (pa, pl)
    active = [p["seq"] for p in pl if not p["end"] and p["id"] != wrong_ins] + ([med["seq"]] if DRY and med["id"] == "insDRY" else [])
    order = ",".join([med["seq"]] + [s for s in active if s != med["seq"]])
    set_order(pid, med["id"], order)
    for vid in visits: rebill(pid, vid, order, med["seq"])

def run(pid): return (ONLY is None) or (ONLY == pid)

amd.login_cached()
S = json.load(open(os.path.join(SCANS, "medfirst_stedi_cache.json")))
def cms(pid): return next(v for k, v in S.items() if k.startswith(pid + "|"))

# A. patient 17476503 - original Medicare since 12/2018 (Stedi), FB inactive 7/9/2026, discovery: CMS only -> Medicare primary
if run("17476503"):
    c = cms("17476503"); med_first("17476503", c["mbi"], c["partB"].split("-")[0], "ins9517779", "07/08/2026", ["19447742", "19448599", "19448747", "19450200"])

# B. patient 17476544 - Medicare paid 9 visits, FB (secondary) inactive 6/9/2026, discovery: WellCare PDP only -> no supplement: coinsurance to patient; 1 visit (6/25) never billed to Medicare -> rebill
if run("17476544"):
    pa, pl = plans("17476544"); med = next(p for p in pl if p["code"] == "FLO02")
    end_plan("17476544", "ins9517809", "06/08/2026")
    set_order("17476544", med["id"], med["seq"])
    rebill("17476544", "19446208", med["seq"], med["seq"])
    for vid in ["19449337", "19449924", "19450272", "19445164", "19445134", "19445429", "19447339", "19446731", "19445833"]:
        cids, ch = cids_of("17476544", vid)
        if any(c["insbalance"] > 0 for c in ch): log("17476544", "coinsurance to patient %s" % vid, move_to_pat(cids[0]))
        else: log("17476544", "coinsurance to patient %s" % vid, "no insurance balance")

# C. patient 17475362 - original Medicare (Stedi), DOD 5/19/2026; visit 4/29/2026 (before death) denied PR22 by FB, $198 on patient -> Medicare
if run("17475362"):
    c = cms("17475362"); med_first("17475362", c["mbi"], c["partB"].split("-")[0], "ins%s" % next(p["id"] for p in plans("17475362")[1] if p["code"] == "BCBS").replace("ins", ""), "04/28/2026", ["19440504"])

# D. patient 17472124 - Medicare paid; FB id not found (ERR 75) since 6/8/2026; discovery: UHC/AARP 9-digit id -> AARP supplement (AAR01) as secondary
if run("17472124"):
    j = json.load(open("patient_db/17472124/stedi_disc_20260720.json")); mid = sorted({it["subscriber"]["memberId"] for it in j["items"] if (it.get("payer") or {}).get("name", "").startswith("UNITED")})[0]
    pa, pl = plans("17472124"); med = next(p for p in pl if p["code"] == "FLO02")
    _, (insid, seq) = add_plan("17472124", "car6600", mid, "01/01/2026")
    end_plan("17472124", "ins9511472", "06/07/2026")
    order = "%s,%s" % (med["seq"], seq); set_order("17472124", med["id"], order)
    for vid in ["19448899", "19449437", "19445180", "19446287"]: rebill("17472124", vid, order, seq)

# E. patient 17470713 - Medicare paid; FB inactive; discovery: UHC/AARP 9-digit id -> AARP supplement; coinsurance sits on the patient -> move back + bill AARP
if run("17470713"):
    j = json.load(open("patient_db/17470713/stedi_disc_20260703.json")); mid = sorted({it["subscriber"]["memberId"] for it in j["items"] if (it.get("payer") or {}).get("name", "").startswith("UNITED")})[0]
    pa, pl = plans("17470713"); med = next(p for p in pl if p["code"] == "FLO02")
    _, (insid, seq) = add_plan("17470713", "car6600", mid, "01/01/2026")
    end_plan("17470713", "ins9509722", "06/24/2026")
    order = "%s,%s" % (med["seq"], seq); set_order("17470713", med["id"], order)
    for vid in ["19447326", "19446185"]: rebill("17470713", vid, order, seq)

# F. patient 17477059 - FB inactive on the DOS, only family-planning Medicaid, no Medicare -> uninsured: balance to patient (WOBAD after one statement cycle - William's 9/12 rule)
if run("17477059"):
    end_plan("17477059", "ins9518491", "07/08/2026")
    for vid in ["19447677", "19447678", "19447727", "19447879", "19448232"]:
        cids, ch = cids_of("17477059", vid); log("17477059", "uninsured -> patient %s" % vid, move_to_pat(cids[0]))
print("register", REG, len(reg), "entries")
