#!/usr/bin/env python3
# PLAIN ENGLISH (Tier-2 fixes: UHC / Florida Blue / FCC / Medicaid unpaid claims whose payer the 9/23 sweep + Stedi proved wrong)
# Decides: Nothing - executes the per-patient plan from medfirst_20260923.json + the Stedi second pass: original-Medicare patients whose
#          visits were billed to Medicaid / FCC / a dead UHC or FB plan get the Medicare plan (added when missing) first and a freq-1
#          rebill to Medicare; visits billed to a dead plan while an Advantage / Simply plan was active are re-pointed to that plan;
#          an uninsured patient's balance goes to the patient (WOBAD after a statement cycle, William's 9/12 rule).
# Rules it uses: frequency 1 before every rebill; full-visit echo; DOS on/before the date of death only (deceased guard inside amd);
#          never a visit with a Medicare payment on it; register every step; resume-safe (skips visits already rebilled -> 204).
# Never touches: payments/write-offs; patient (died 8/25, FB secondaries pending); patient/patient/patient/patient (Medicare id unknown -> William).
# ---
"""Usage: python3 medfirst_act2_0923.py [--dry] [--only PID]"""
import amd, elig_amd, add_ins, ins_update, move_to_ins, freq1_visit, txh, payreasons, resave
import json, sys, time, datetime, os, re
DRY = "--dry" in sys.argv; ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
SCANS = "/home/claude/scans"; REG = os.path.join(SCANS, "medfirst_act2_0923_register.json")
reg = json.load(open(REG)) if os.path.exists(REG) else []
CAR = json.load(open("carriers.json"))
S = json.load(open(os.path.join(SCANS, "medfirst_stedi_cache.json")))
def cms(pid): return next(v for k, v in S.items() if k.startswith(pid + "|"))
def log(pid, what, res):
    reg.append({"pid": pid, "what": what, "result": str(res)[:220], "at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "dry": DRY}); json.dump(reg, open(REG, "w"), indent=1)
    print("  ", pid, what, "->", str(res)[:150], flush=True)
def plans(pid):
    pa, pl = elig_amd.plans(pid)
    return pa, [{"id": p.get("id"), "code": CAR.get(p.get("carrier"), ["?"])[0], "car": p.get("carrier"), "seq": p.get("sequence"), "end": p.get("enddate"), "begin": p.get("begindate"), "sub": p.get("subscribernum", "")} for p in pl]
def cids_of(pid, vid):
    ch = payreasons.visit_state(pid, vid, txh.fetch_visit(pid, vid)); return [str(c["cid"]) for c in ch], ch
DONE_VIDS = {(r["pid"], r["what"].split(" ")[1]) for r in reg if r["what"].startswith("rebill ") and "-> 204" in r["result"] and not r.get("dry")}
def rebill(pid, vid, order, seq):
    if (pid, vid) in DONE_VIDS: return print("   skip (already rebilled)", pid, vid)
    cids, ch = cids_of(pid, vid)
    if not cids: return log(pid, "rebill %s" % vid, "no live charges")
    if any(p["carrier"] == "FLO02" and p["void"] != "1" and (p["amount"] > 0 or p["reasons"]) for c in ch for p in c["pays"]): return log(pid, "rebill %s" % vid, "SKIP - Medicare already adjudicated this visit")
    if vid.startswith("194542") and vid <= "19454251": return log(pid, "rebill %s" % vid, "SKIP - re-created Medicaid-only visit (9/10 profile swap)")
    if DRY: return log(pid, "rebill %s seq %s order %s" % (vid, seq, order), "DRY %s" % [(c["cpt"], c["dos"], c["insbalance"], c["patbalance"], c["carrier"]) for c in ch])
    r1 = freq1_visit.run(vid, cids[0], int(seq)); time.sleep(0.6)
    r2 = move_to_ins.move(cids[0], order, rebill_seq=int(seq)); time.sleep(0.6)
    log(pid, "rebill %s seq %s order %s" % (vid, seq, order), "%s | %s" % (r1, r2))
def add_plan(pid, carrier, member, begin):
    if DRY: log(pid, "add plan %s %s… begin %s" % (carrier, member[:3], begin), "DRY"); return "insDRY", "9"
    insid, seq = add_ins.add(pid, carrier, member, begin); log(pid, "add plan %s %s… begin %s" % (carrier, member[:3], begin), (insid, seq)); return insid, str(seq)
def end_plan(pid, insid, enddate):
    if DRY: return log(pid, "end-date %s %s" % (insid, enddate), "DRY")
    log(pid, "end-date %s %s" % (insid, enddate), ins_update.update(pid, insid, enddate=enddate))
def set_order(pid, insid, order):
    if DRY: return log(pid, "chart order %s via %s" % (order, insid), "DRY")
    log(pid, "chart order %s via %s" % (order, insid), ins_update.update(pid, insid, sequence=order))
def ensure_plan(pid, code, carrier, member, begin, allow_ended=False):
    pa, pl = plans(pid)
    p = next((p for p in pl if p["code"] == code and (not p["end"] or allow_ended)), None)
    if p and (not member or p["sub"].upper() == member.upper()): return p["id"], p["seq"]
    if p and member and p["sub"].upper() != member.upper():
        if DRY: log(pid, "fix member id on %s" % p["id"], "DRY")
        else: log(pid, "fix member id on %s" % p["id"], ins_update.update(pid, p["id"], subscribernum=member))
        return p["id"], p["seq"]
    return add_plan(pid, carrier, member, begin)
def first_then(first_seq, others): return ",".join([first_seq] + [s for s in others if s != first_seq])
def active_seqs(pid, exclude=(), include=()):
    pa, pl = plans(pid); return [p["seq"] for p in pl if (not p["end"] or p["id"] in include) and p["id"] not in exclude]
def run(pid): return (ONLY is None) or (ONLY == pid)
def disc_member(pid, dos, payer_prefix):
    j = json.load(open("patient_db/%s/stedi_disc_%s.json" % (pid, dos)))
    return sorted({it["subscriber"]["memberId"] for it in j["items"] if (it.get("payer") or {}).get("name", "").upper().startswith(payer_prefix)})[0]
def partb_begin(pid):
    b = (cms(pid).get("partB") or "").split("-")[0]; return "%s/%s/%s" % (b[4:6], b[6:8], b[:4]) if len(b) == 8 else None
def move_to_pat(cid):
    """Insurance balance -> patient, ONLY on charges with no payments (a resave with insportion=0 unapplies insurance payments - 9/23 lesson)."""
    vis, pat, allc = resave.visit_charges(cid)
    if any(c.find("payment") is not None for c in allc): return "REFUSED - visit carries payments"
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
                a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved += ib
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    if moved == 0: return "nothing to move"
    if DRY: return "DRY move %.2f to patient" % moved
    va = dict(vis.attrib); va["force"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    return "FAULT " + re.sub(r"\s+", " ", r[:200]) if "Fault" in r else "moved %.2f to patient" % moved

amd.login_cached()
ROWS = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(SCANS, "medfirst_20260923.jsonl"))}
def rebill_vids(pid): return [vid for vid, a in ROWS[pid]["plan"] if a == "REBILL_TO_MEDICARE"]

# --- ORIGINAL MEDICARE: Medicare first, freq-1 rebill of the visits the sweep marked REBILL_TO_MEDICARE ---------------------------
# NOT here (9/23 finding): the 1/27/2026 CCM visits carry Medicare's $0 deductible adjudication (PR1) - the balance is the QMB/Medicaid
# secondary's, never a Medicare rebill; and the 194542xx January-February visits are the 9/10 Garland-G->Effinger RE-CREATED Medicaid-only
# visits (digest 2026-09-20T0910Z) - their Medicare claim lives on the original visit, so a Medicare rebill would be a duplicate.
MED = ["17476042", "46692", "17470802", "21885", "17473661", "17477529", "23617", "25541"]
for pid in MED:
    if not run(pid): continue
    c = cms(pid); pa, pl = plans(pid)
    ended_med = next((p for p in pl if p["code"] == "FLO02" and p["end"]), None); active_med = next((p for p in pl if p["code"] == "FLO02" and not p["end"]), None)
    if active_med: insid, seq = active_med["id"], active_med["seq"]
    elif ended_med: insid, seq = ended_med["id"], ended_med["seq"]          # patient: FLO02 ended 2/9/2026, the visits are January 2026 - still Medicare's
    else: insid, seq = add_plan(pid, "car6085", c["mbi"], partb_begin(pid))
    order = first_then(seq, active_seqs(pid, include=(insid,))) if not DRY else seq
    set_order(pid, insid, order)
    for vid in rebill_vids(pid): rebill(pid, vid, order, seq)
if run("21593"):   # patient Judeth - original Medicare, died [DOB]; 8 UHC visits 8/11-8/18 (UNI20 + WellCare both inactive)
    c = cms("21593"); insid, seq = add_plan("21593", "car6085", c["mbi"], partb_begin("21593"))
    order = first_then(seq, active_seqs("21593", include=(insid,))) if not DRY else seq; set_order("21593", insid, order)
    for vid in [v["vid"] for v in ROWS["21593"]["visits"] if v["dos"] <= "2026-08-18"]: rebill("21593", vid, order, seq)

# --- Advantage / Simply plan proven for the DOS: re-point ----------------------------------------------------------------------
if run("17469645"):   # patient - UHC of Florida HMO (UNI20 seq 3 active); one visit went to Medicaid
    pa, pl = plans("17469645"); uni = next(p for p in pl if p["code"] == "UNI20" and not p["end"])
    order = first_then(uni["seq"], active_seqs("17469645")) if not DRY else uni["seq"]; set_order("17469645", uni["id"], order)
    for vid in [v["vid"] for v in ROWS["17469645"]["visits"] if v["carrier"] == "MCAD"]: rebill("17469645", vid, order, uni["seq"])
if run("24853"):      # patient - Humana MA PPO (Emphesys) active, HUM01 seq 1; 13 visits went to a dead UHC plan
    pa, pl = plans("24853"); hum = next(p for p in pl if p["code"] == "HUM01" and not p["end"]); uni = next(p for p in pl if p["code"] == "UNI20" and not p["end"])
    end_plan("24853", uni["id"], "12/31/2025")
    order = first_then(hum["seq"], active_seqs("24853", exclude=(uni["id"],))) if not DRY else hum["seq"]; set_order("24853", hum["id"], order)
    for vid in [v["vid"] for v in ROWS["24853"]["visits"] if v["carrier"] == "UNI20"]: rebill("24853", vid, order, hum["seq"])
if run("17472741"):   # patient William - UHC of Florida HMO (UNI20 seq 5 active); one visit went to FCC
    pa, pl = plans("17472741"); uni = next(p for p in pl if p["code"] == "UNI20" and not p["end"])
    order = first_then(uni["seq"], active_seqs("17472741")) if not DRY else uni["seq"]; set_order("17472741", uni["id"], order)
    for vid in [v["vid"] for v in ROWS["17472741"]["visits"] if v["carrier"] == "FLO99"]: rebill("17472741", vid, order, uni["seq"])
if run("17474231"):   # patient - Simply MMA since 2/2025 (discovery); straight Medicaid rejected 6 visits
    mid = disc_member("17474231", "20260801", "SIMPLY"); insid, seq = ensure_plan("17474231", "SIM01", "car42019", mid, "02/01/2025")
    order = first_then(seq, active_seqs("17474231", include=(insid,))) if not DRY else seq; set_order("17474231", insid, order)
    for vid in [v["vid"] for v in ROWS["17474231"]["visits"]]: rebill("17474231", vid, order, seq)
if run("17473689"):   # patient Jr - UHC Dual Complete 1/1/2025-12/31/2025 (discovery); 2 visits 10-11/2025 went to a dead UNI20 plan
    mid = disc_member("17473689", "20251105", "UNITED"); pa, pl = plans("17473689"); uni = next(p for p in pl if p["code"] == "UNI20" and not p["end"])
    insid, seq = ensure_plan("17473689", "UHCMA", "car302853", mid, "01/01/2025", allow_ended=True)
    if insid != "insDRY": end_plan("17473689", insid, "12/31/2025")
    end_plan("17473689", uni["id"], "12/31/2025")
    order = first_then(seq, active_seqs("17473689", exclude=(uni["id"],), include=(insid,))) if not DRY else seq; set_order("17473689", insid, order)
    for vid in [v["vid"] for v in ROWS["17473689"]["visits"]]: rebill("17473689", vid, order, seq)
if run("17474713"):   # patient Kerry (b. 1996) - FB inactive, discovery found nothing -> uninsured: balance to the patient
    pa, pl = plans("17474713"); fb = next(p for p in pl if p["code"] == "BCBS" and not p["end"]); end_plan("17474713", fb["id"], "07/31/2026")
    for v in ROWS["17474713"]["visits"]:
        cids, ch = cids_of("17474713", v["vid"]); log("17474713", "uninsured -> patient %s" % v["vid"], move_to_pat(cids[0]))
print("register", REG, len(reg), "entries")
