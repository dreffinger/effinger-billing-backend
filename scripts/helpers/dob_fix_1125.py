# PLAIN ENGLISH (a birth date William gave on the board, 11/25/2026 - kept only if Medicare agrees)
# Decides: whether the birth date William typed is the one Medicare holds - by AdvancedMD's free check answering ACTIVE once it is on
#   the chart. Card card-17473160: Medicare said the chart's birth date ([DOB]) does not match its record;
#   William answered "6/5/27" (04:36 UTC) = [DOB]. Writes it (patient_patch.patch dob=[DOB], the captured demographics PATCH),
#   runs AMD's 271 on the Medicare plan; ACTIVE -> keep and re-send the unpaid Medicare visit(s) named (ONE frequency-1 rebill each, the
#   deceased guard inside); anything else -> put [DOB] back and say so.
# Never touches: other fields, other charts, paid visits. Usage: python3 dob_fix_1125.py [--live]
import amd, patient_patch, elig_amd, freq1_visit, json, sys
LIVE = "--live" in sys.argv; PID, INS, NEW, OLD = "17473160", "ins9512735", "[DOB]", "[DOB]"
VISITS = [("19442323", "23350355")]   # 02/28/2026 99487+99489, Medicare answered $0 (check 349483589) - the card's one visit, $315
amd.login_cached(); out = {"pid": PID, "new": NEW, "live": LIVE}
before = patient_patch.get(PID); print("dob before:", before.get("dob"))
if not LIVE: print("DRY - would patch dob", NEW, ", check 271, keep on ACTIVE and re-send", VISITS); sys.exit()
code, txt, _ = patient_patch.patch(PID, {"dob": NEW}); out["patch"] = [code, str(txt)[:120]]; print("PATCH", code, str(txt)[:120])
print("dob after:", patient_patch.get(PID).get("dob"))
s = elig_amd.run_plan(PID, INS, force=True); out["271"] = elig_amd.one_line(s)[:220]; print("271:", out["271"])
if s.get("status") == "ACTIVE":
    out["outcome"] = "kept - Medicare ACTIVE"; out["visits"] = {}
    for vid, cid in VISITS:
        r = freq1_visit.run(vid, cid, 1); out["visits"][vid] = r; print("  v%s %s" % (vid, r))
else:
    code2, txt2, _ = patient_patch.patch(PID, {"dob": OLD}); out["outcome"] = "restored %s - Medicare %s" % (OLD, s.get("status")); print("restored", code2, str(txt2)[:100])
print("OUTCOME:", out["outcome"]); json.dump(out, open("registers/dob_fix_2026-11-25T0435Z.json", "w"), indent=1)
