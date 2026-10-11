# PLAIN ENGLISH (new chart 17478031 is on a UnitedHealthcare DUAL COMPLETE HMO-POS Medicare Advantage plan - run 2026-10-11T0510Z)
# Decides: nothing new - the standing dual-eligible routing (10/5/2026): a Medicare Advantage plan found by eligibility is billed FIRST,
#   straight Medicare stays on the chart unbilled. AMD's 271 on the Medicare plan added this run named 'HN H2509 UNITEDHEALTHCARE OF
#   FLORIDA' and Stedi UHC 87726 answered Active Coverage 'FL UNITEDHEALTHCARE DUAL COMPLETE HMOPOS', plan 5/1/2026-12/31/2026, with the
#   member id (patient_db/17478031/stedi_87726_20261007.json - read at run time, never printed). So: add the UHCMA plan (carrier from
#   carriers.json, member id, begin 05/01/2026, no group), AMD free 271 on it, patient order = the MA plan alone (Medicare unbilled;
#   the Florida Medicaid plan waits for the Medicaid id - QMB), and the three HCA visits released this run get their visit order set to
#   the MA plan by the no-rebill full-visit echo (resave.set_insorder) - they have not been billed yet, so no rebill is needed.
# Never touches: payments, group numbers, hospitalizationto, the Medicare plan's dates, any other chart.
#   python3 uhc_ma_fix_1011.py          # dry
#   python3 uhc_ma_fix_1011.py --live   # register registers/uhc_ma_fix_2026-10-11T0510Z.json
import amd, add_ins, elig_amd, ins_update, resave, json, sys, time
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"; PID = "17478031"
VISITS = [("19457492", "23369400"), ("19457459", "23369365"), ("19457455", "23369361")]
CAR = json.load(open("carriers.json")); car = CAR.get("UHCMA")
e = json.load(open("patient_db/%s/stedi_87726_20261007.json" % PID)); member = e.get("subscriber", {}).get("memberId")
reg = {"stamp": S, "live": LIVE, "pid": PID, "carrier": car, "steps": []}
def L(m): print(m, flush=True); reg["steps"].append(m)
if not car or not member:
    L("STOP - UHCMA carrier (%s) or member id (%s) missing" % (car, bool(member))); json.dump(reg, open("registers/uhc_ma_fix_%s.json" % S, "w"), indent=1); sys.exit(1)
amd.login_cached()
if not LIVE:
    L("DRY: add UHCMA %s begin 05/01/2026 CC; 271; patient order <seq>; set_insorder <seq> on %s" % (car, [v for v, c in VISITS]))
else:
    insid, seq = add_ins.add(PID, car, member, "05/01/2026", "1", "CC"); L("add_ins UHCMA -> %s seq %s" % (insid, seq))
    if not insid or not str(seq).isdigit(): L("STOP - plan not added"); json.dump(reg, open("registers/uhc_ma_fix_%s.json" % S, "w"), indent=1); sys.exit(1)
    time.sleep(0.8)
    try:
        r = elig_amd.run_plan(PID, insid); L("271: %s" % (elig_amd.one_line(r) if isinstance(r, dict) else str(r))[:300])
    except Exception as ex: L("271 ERR %s" % str(ex)[:200])
    ok, msg = ins_update.update(PID, insid, sequence=str(seq)); L("patient order %s: ok=%s %s" % (seq, ok, str(msg)[:200]))
    for vid, cid in VISITS:
        time.sleep(0.5); ok, msg = resave.set_insorder(cid, str(seq)); L("v%s set_insorder %s: ok=%s %s" % (vid, seq, ok, str(msg)[:200]))
json.dump(reg, open("registers/uhc_ma_fix_%s.json" % S, "w"), indent=1)
print("saved registers/uhc_ma_fix_%s.json" % S)
