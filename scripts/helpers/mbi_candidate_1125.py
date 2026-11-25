# PLAIN ENGLISH (test ONE candidate Medicare number on a chart, the medicare_number_fix way, 11/25/2026)
# Decides: whether a candidate Medicare number is right - ONLY by AdvancedMD's free check answering ACTIVE once it is on the chart.
#   Chart 17474021: the number on the chart (= the number on William's 11/25 facesheet paste) is REJECTED 72 by Medicare; Medicare's
#   look-up by name / birth date / SSN finds nothing (75); the secondary's own 271 (BCBS, ACTIVE) lists a Medicare-shaped id for the
#   patient among its other payers. This helper writes that id on the Medicare plan (ins_update, wrapped updateinsurance; the
#   insurance order is re-read and put back), runs AMD's free 271, and KEEPS it only on ACTIVE - otherwise the old number goes back.
# Never touches: visits, balances, other plans. Usage: python3 mbi_candidate_1125.py <pid> <insid> <candidate> [--live]
#   Register registers/mbi_candidate_2026-11-25T0435Z.json (chart / plan ids and the outcome; the numbers masked to their last 4).
import amd, ins_update, elig_amd, re, json, sys
a = [x for x in sys.argv[1:] if not x.startswith("--")]; PID, INS, CAND = a[0], a[1], a[2]; LIVE = "--live" in sys.argv
amd.login_cached()
t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
p = {d.get("id"): d for d in [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', t)]}
old = p.get(INS, {}).get("subscribernum", "")
m = lambda s: "*" * max(0, len(s) - 4) + s[-4:]
out = {"pid": PID, "insid": INS, "old": m(old), "candidate": m(CAND), "live": LIVE}
print("pat%s %s old %s candidate %s" % (PID, INS, m(old), m(CAND)))
if not LIVE: print("DRY - would write the candidate, check, keep on ACTIVE else restore"); sys.exit()
r1 = ins_update.update(PID, INS, subscribernum=CAND); out["write"] = str(r1)[:160]; print("write:", str(r1)[:160])
s = elig_amd.run_plan(PID, INS, force=True); status = s.get("status"); out["271"] = elig_amd.one_line(s)[:200]; print("271:", out["271"])
if status == "ACTIVE": out["outcome"] = "kept - Medicare ACTIVE"
else:
    r2 = ins_update.update(PID, INS, subscribernum=old); out["restore"] = str(r2)[:160]; out["outcome"] = "restored - %s" % status; print("restored:", str(r2)[:160])
print("OUTCOME:", out["outcome"])
f = "registers/mbi_candidate_2026-11-25T0435Z.json"
try: reg = json.load(open(f))
except Exception: reg = []
reg.append(out); json.dump(reg, open(f, "w"), indent=1)
