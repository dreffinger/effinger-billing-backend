# PLAIN ENGLISH (dual chart 17472124 per William's PCC admission record pasted 10/11/2026 03:34Z: primary payer Florida Community
#   Care (Medicaid MMA), Medicare B third, "Medicare B coinsurance from Medicaid" via FCC - so the Medicare coinsurance the chart
#   has been sending to a guessed AARP supplement (rejected 'subscriber not found' 10/4) belongs to FCC.)
# Decides: (1) add the FCC plan (FLO99 car42008, Medicaid id from the facesheet, begin 01/01/2026, finclass MD, no group number) with
#   add_ins.add; (2) AMD's free 271 on it (elig_amd.run_plan); (3) end-date the guessed AARP plan ins9520542 on its own begin date
#   (ins_update.update enddate); (4) patient order Medicare first, FCC second (ins_update.update sequence, verified); (5) the four
#   Medicare-paid visits whose coinsurance sits at AAR01 get ONE re-route each (freq1_visit.reroute vid cid "2,<fcc seq>" <fcc seq>)
#   = visit order Medicare / FCC + one frequency-1 secondary claim to FCC. Dry mode only reads and prints the plan.
# Never touches: payments, write-offs, the Medicare plan, the ended Florida Blue plan, any other chart.
#   python3 dual_fcc_1011.py          # dry
#   python3 dual_fcc_1011.py --live   # register registers/dual_fcc_2026-10-11T0510Z.json
import amd, add_ins, ins_update, elig_amd, freq1_visit, json, sys, time, re
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"; PID = "17472124"
FCC = "car42008"; AARP_INS = "ins9520542"; MED_SEQ = "2"
VISITS = [("19445180", "23353988"), ("19446287", "23355335"), ("19448899", "23358403"), ("19449437", "23359067")]
cfg = json.load(open("secrets/dual_fcc_1011_cfg.json"))   # {"medicaid_id": "..."} - the facesheet id stays in secrets/
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "pid": PID, "steps": []}
def L(m): print(m, flush=True); reg["steps"].append(m)
if not LIVE:
    L("DRY: add FLO99 %s begin 01/01/2026 MD; 271 on it; end-date %s 01/01/2026; patient order %s,<new>; reroute %s to 2,<new> seq <new>" % (FCC, AARP_INS, MED_SEQ, [v for v, c in VISITS]))
else:
    insid, seq = add_ins.add(PID, FCC, cfg["medicaid_id"], "01/01/2026", "1", "MD")
    L("add_ins -> %s seq %s" % (insid, seq))
    if not insid or not str(seq).isdigit():
        L("STOP - plan not added"); json.dump(reg, open("registers/dual_fcc_%s.json" % S, "w"), indent=1); sys.exit(1)
    time.sleep(0.8)
    try:
        e = elig_amd.run_plan(PID, insid); L("271 on %s: %s" % (insid, (elig_amd.one_line(e) if isinstance(e, dict) else str(e))[:300]))
    except Exception as ex:
        L("271 on %s: ERR %s" % (insid, str(ex)[:200]))
    ok, msg = ins_update.update(PID, AARP_INS, enddate="01/01/2026"); L("end-date %s: ok=%s %s" % (AARP_INS, ok, str(msg)[:200]))
    time.sleep(0.5)
    ok, msg = ins_update.update(PID, insid, sequence="%s,%s" % (MED_SEQ, seq)); L("patient order %s,%s: ok=%s %s" % (MED_SEQ, seq, ok, str(msg)[:200]))
    for vid, cid in VISITS:
        time.sleep(0.6)
        L("reroute v%s c%s -> %s,%s seq %s: %s" % (vid, cid, MED_SEQ, seq, seq, freq1_visit.reroute(vid, cid, "%s,%s" % (MED_SEQ, seq), seq)))
json.dump(reg, open("registers/dual_fcc_%s.json" % S, "w"), indent=1)
print("saved registers/dual_fcc_%s.json" % S)
