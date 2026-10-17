# PLAIN ENGLISH (insurance cascade + re-route, chart 23177, 7 AM ET 10/17/2026 run 2026-10-17T1110Z)
# Decides: nothing new - RULE C (William 10/14 'run stedi and add correct insurance and submit the claims') and the 10/16 CO-109/N418
#   lesson. Medicare's $0 remit 350087718 (ERA 1053200) answered CO-109 / N418 (not this payer - misrouted) on the chart's eight
#   10/25/2025-01/27/2026 claims (99487+99489 CCM, 99309, 99308; $1,666) sent to Medicare 10/14. Lookups this run (patient_db/23177/):
#   AMD 271 today = straight Medicare ACTIVE (QMB) + Medicaid ACTIVE (Humana SMMC LTC/MMA); Stedi CMS 271 at DOS 11/15/2025 = PRIMARY
#   PAYER 'CARE IMPROVEMENT PLUS SOUTH CENTRAL' (UHC Medicare Advantage PPO) coordination of benefits 10/01/2022-01/31/2026; Stedi
#   discovery = UNITEDHEALTHCARE member [member id] plan 2025; Stedi UHC 87726 with that id = ACTIVE 'FL UNITEDHEALTHCARE DUAL COMPLETE
#   LPPO FULL H1889' at 11/15/2025 and at 01/27/2026 (plan 01/01-01/31/2026). So UHC Dual Complete was the payer on every one of the
#   eight dates and original Medicare only from 02/01/2026 - exactly the chart-46692 pattern (UNI20 car6404, frequency 1, 10/16).
# Does (--live): add UNI20 car6404 member [member id] begin 10/01/2022 (no group), end-date it 01/31/2026 (ins_update puts the patient
#   order back - verified), then for each of the 8 visits ONE freq1_visit.reroute(vid, cid, "<new seq>") = visit insorder by the
#   no-rebill full-visit echo + ONE frequency-1 reset + ONE chargerebill to the UHC sequence. Medicare stays seq 1 on the chart
#   (ACTIVE today - the 2026 visits after 1/31 bill Medicare); patient default order 1,2 untouched.
# Never touches: payments, write-offs, diagnosis or procedure codes, the Medicare or Medicaid plans, any other visit.
#   python3 cascade_23177_1110.py          # dry      python3 cascade_23177_1110.py --live   # register registers/cascade_23177_2026-10-17T1110Z.json
import amd, add_ins, ins_update, freq1_visit, json, sys, re, time
LIVE = "--live" in sys.argv; S = "2026-10-17T1110Z"; PID = "23177"
VISITS = [("19421130", "23369639"), ("19423401", "23369643"), ("19423726", "23369645"), ("19425356", "23369649"), ("19426995", "23369651"), ("19427137", "23369653"), ("19430015", "23369657"), ("19430853", "23369659")]
amd.login_cached()
def plans():
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + PID, "nocookie": "1"}), timeout=60)
    ps = [dict(re.findall(r'(\w+)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*>', d)]
    io = re.search(r'insorder="([^"]*)"', d)
    return ps, (io.group(1) if io else None)
reg = {"stamp": S, "live": LIVE, "pid": PID, "steps": []}
ps, order = plans(); print("plans before:", [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate")) for p in ps], "insorder", order)
reg["before"] = {"plans": [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate")) for p in ps], "insorder": order}
have = [p for p in ps if p.get("carrier") == "car6404"]
if have:
    seq = have[0]["sequence"]; insid = have[0]["id"]; print("UNI20 plan already on the chart:", insid, "seq", seq)
elif not LIVE:
    seq = str(len(ps) + 1); print("DRY add UNI20 car6404 124171897 begin 10/01/2022 -> seq", seq, "then enddate 01/31/2026, then order", order, "re-asserted")
else:
    r = add_ins.add(PID, "car6404", "124171897", "10/01/2022", "1", "CC"); print("add_ins ->", str(r)[:200]); reg["steps"].append({"add_ins": str(r)[:300]}); time.sleep(0.8)
    ps, order2 = plans(); have = [p for p in ps if p.get("carrier") == "car6404"]
    if not have: print("ABORT - plan not on the chart after add"); json.dump(reg, open("registers/cascade_23177_%s.json" % S, "w"), indent=1); sys.exit(1)
    seq = have[0]["sequence"]; insid = have[0]["id"]
    r2 = ins_update.update(PID, insid, enddate="01/31/2026"); print("enddate ->", str(r2)[:200]); reg["steps"].append({"enddate": str(r2)[:300]}); time.sleep(0.8)
    ps, order3 = plans(); print("insorder after enddate:", order3)
    if (order3 or "") != (order or ""):
        r3 = ins_update.update(PID, [p for p in ps if p.get("carrier") == "car6085"][0]["id"], sequence=order or "1,2"); print("order restore ->", str(r3)[:200]); reg["steps"].append({"order_restore": str(r3)[:300]}); time.sleep(0.8)
        ps, order4 = plans(); print("insorder now:", order4); reg["steps"].append({"insorder_after": order4})
        if (order4 or "") != (order or ""): print("WARNING patient insorder is %r, wanted %r - report" % (order4, order))
reg["uhc_seq"] = seq
for vid, cid in VISITS:
    if LIVE:
        res = freq1_visit.reroute(vid, cid, str(seq), int(seq)); time.sleep(0.8)
    else:
        res = freq1_visit.reroute(vid, cid, str(seq), int(seq), dry=True)
    print(vid, cid, "->", str(res)[:200]); reg["steps"].append({"vid": vid, "cid": cid, "result": str(res)[:300]})
json.dump(reg, open("registers/cascade_23177_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
print("saved registers/cascade_23177_%s%s.json" % (S, "" if LIVE else "_dry"))
