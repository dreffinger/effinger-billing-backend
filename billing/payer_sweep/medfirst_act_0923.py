#!/usr/bin/env python3
# PLAIN ENGLISH (Medicare-first / right-payer fixes for the unpaid-list patients the 9/23 sweep + Stedi verified)
# Decides: Nothing - executes the per-patient plan proved by medfirst_sweep + the Stedi second pass (CMS MBI lookup, payer eligibility on
#          the DOS, insurance discovery): add the Medicare plan and bill Medicare first for original-Medicare patients whose claims sat at
#          a supplement / TRICARE For Life / commercial secondary; add the Advantage plan discovery found and re-point the visits; end-date
#          the dead plan the day before the first denied DOS. Frequency 1 before every rebill, full-visit echo, register every step.
# Never touches: payments/write-offs, VA claims, patient (Railroad Medicare enrollment), patient (hospice + GV), patient (MBI unknown).
# ---
"""Usage: python3 medfirst_act_0923.py [--dry] [--only PID]"""
import amd, elig_amd, add_ins, ins_update, move_to_ins, freq1_visit, txh, payreasons
import json, sys, time, datetime, os
DRY = "--dry" in sys.argv; ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
SCANS = "/home/claude/scans"; REG = os.path.join(SCANS, "medfirst_act_0923_register.json")
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
    if DRY: return log(pid, "rebill %s seq %s order %s" % (vid, seq, order), "DRY %s" % [(c["cpt"], c["insbalance"], c["patbalance"], c["carrier"]) for c in ch])
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
def ensure_plan(pid, code, carrier, member, begin):
    """Return (insid, seq) of an ACTIVE plan for carrier code, adding it when missing (member id must match when present)."""
    pa, pl = plans(pid)
    p = next((p for p in pl if p["code"] == code and not p["end"]), None)
    if p and (not member or p["sub"].upper() == member.upper()): return p["id"], p["seq"]
    if p and member and p["sub"].upper() != member.upper():
        if DRY: log(pid, "fix member id on %s" % p["id"], "DRY")
        else: log(pid, "fix member id on %s" % p["id"], ins_update.update(pid, p["id"], subscribernum=member))
        return p["id"], p["seq"]
    return add_plan(pid, carrier, member, begin)
def first_then(pid, first_seq, others):
    return ",".join([first_seq] + [s for s in others if s != first_seq])
def active_seqs(pid, exclude=()):
    pa, pl = plans(pid); return [p["seq"] for p in pl if not p["end"] and p["id"] not in exclude]
def run(pid): return (ONLY is None) or (ONLY == pid)
def disc_member(pid, dos, payer_prefix):
    j = json.load(open("patient_db/%s/stedi_disc_%s.json" % (pid, dos)))
    return sorted({it["subscriber"]["memberId"] for it in j["items"] if (it.get("payer") or {}).get("name", "").upper().startswith(payer_prefix)})[0]
def partb_begin(pid):
    b = (cms(pid).get("partB") or "").split("-")[0]; return "%s/%s/%s" % (b[4:6], b[6:8], b[:4]) if len(b) == 8 else None

amd.login_cached()
# --- ORIGINAL MEDICARE never billed: add/keep FLO02, Medicare first, freq-1 rebill ---------------------------------------
MED = {  # pid: (visits)  - all DOS within 365 days, no Medicare payment on the visit, last bill went to the other payer
    "17475365": ["19431396", "19433866", "19437307", "19442527", "19448360", "19448725", "19452649"],   # patient - TRICARE For Life; DOD 8/27/2026 after every DOS
    "17474541": ["19422202", "19423559", "19430630", "19442285", "19450201", "19452591"],               # patient - Philadelphia American (Medigap) billed as primary
    "17477774": ["19454901", "19454914", "19454943", "19455048", "19455119", "19455206", "19455455"],   # patient - UMR billed as primary, FLO02 on chart seq 2
    "17477773": ["19454900", "19454915", "19454944"],                                                   # patient - Cigna billed as primary, FLO02 seq 2
    "17476869": ["19452593"],                                                                           # patient - Humana (Medicaid) billed as primary, FLO02 seq 2
}
for pid, vids in MED.items():
    if not run(pid): continue
    c = cms(pid); insid, seq = ensure_plan(pid, "FLO02", "car6085", c["mbi"], partb_begin(pid))
    order = first_then(pid, seq, active_seqs(pid)) if not DRY else seq
    set_order(pid, insid, order)
    for vid in vids: rebill(pid, vid, order, seq)

# --- Advantage / commercial plan discovery found: add it, end the dead plan, re-point the visits ------------------------------
if run("17472228"):   # patient - AARP Medicare Advantage HMO-POS (UHC 87726) since 7/1/2026; WellCare inactive
    mid = json.load(open("patient_db/17472228/stedi_uhc_20260813.json"))["subscriber"]["memberId"]
    pa, pl = plans("17472228"); wel = next(p for p in pl if p["code"] == "WEL04")
    insid, seq = ensure_plan("17472228", "UNI20", "car6404", mid, "07/01/2026"); end_plan("17472228", wel["id"], "06/30/2026")
    order = first_then("17472228", seq, active_seqs("17472228", exclude=(wel["id"],))) if not DRY else seq; set_order("17472228", insid, order)
    for vid in ["19451572", "19451582"]: rebill("17472228", vid, order, seq)
if run("17472874"):   # patient - AARP Medicare Advantage LPPO (UNI20 plan already on chart, seq 3); WellCare inactive
    pa, pl = plans("17472874"); wel = next(p for p in pl if p["code"] == "WEL04"); uni = next(p for p in pl if p["code"] == "UNI20" and not p["end"])
    end_plan("17472874", wel["id"], "12/31/2025")
    order = first_then("17472874", uni["seq"], active_seqs("17472874", exclude=(wel["id"],))) if not DRY else uni["seq"]; set_order("17472874", uni["id"], order)
    for vid in ["19438061", "19438903", "19438993", "19439271"]: rebill("17472874", vid, order, uni["seq"])
if run("17471110"):   # patient - UHC Dual Complete HMO-POS 1/1/2026-8/31/2026 (and 9/1-12/31); WellCare ended 2005
    mid = disc_member("17471110", "20260420", "UNITED"); pa, pl = plans("17471110"); wel = next(p for p in pl if p["code"] == "WEL04")
    insid, seq = ensure_plan("17471110", "UHCMA", "car302853", mid, "01/01/2026"); end_plan("17471110", wel["id"], "12/31/2025")
    order = first_then("17471110", seq, active_seqs("17471110", exclude=(wel["id"],))) if not DRY else seq; set_order("17471110", insid, order)
    for vid in ["19439003", "19439004", "19439005", "19439232", "19439267", "19439704", "19439786", "19439813", "19439881", "19439923", "19440248", "19440263", "19440406"]: rebill("17471110", vid, order, seq)
if run("48163"):      # patient - UHC Dual Complete HMO-POS 1/1/2026-12/31/2026; WellCare inactive
    mid = disc_member("48163", "20260801", "UNITED"); pa, pl = plans("48163"); dead = [p for p in pl if p["code"] in ("WEL04", "WEL07") and not p["end"]]
    insid, seq = ensure_plan("48163", "UHCMA", "car302853", mid, "01/01/2026")
    for p in dead: end_plan("48163", p["id"], "12/31/2025")
    order = first_then("48163", seq, active_seqs("48163", exclude=tuple(p["id"] for p in dead))) if not DRY else seq; set_order("48163", insid, order)
    rebill("48163", "19433127", order, seq)
if run("17477409"):   # patient - Florida Blue BlueOptions Standard PPO since 7/1/2026; patient rejected
    mid = json.load(open("patient_db/17477409/stedi_disc_20260901.json"))["items"][0]["subscriber"]["memberId"]
    pa, pl = plans("17477409"); lan = next(p for p in pl if p["code"] == "LAN")
    insid, seq = ensure_plan("17477409", "BCBS", "car6062", mid, "07/01/2026"); end_plan("17477409", lan["id"], "06/30/2026")
    order = first_then("17477409", seq, active_seqs("17477409", exclude=(lan["id"],))) if not DRY else seq; set_order("17477409", insid, order)
    for vid in ["19451457", "19451462"]: rebill("17477409", vid, order, seq)
print("register", REG, len(reg), "entries")
