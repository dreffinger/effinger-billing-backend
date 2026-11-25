# PLAIN ENGLISH (Capital Health Plan member numbers William pasted on three board cards tonight, 11/25/2026 - and a chart with no plan)
# Decides: nothing. William's HCA facesheet pastes (02:33-02:39 UTC) carry the CHP (Capital Health Plan, CAP07 = car41826) member
#   number for three feed charts that Medicare's record names as CHP Medicare Advantage members (H5938):
#   card-17478470    MEMBER-ID-REDACTED effective 11/17/2026 (chart has NO plan; visits v19461860 11/17 99223+99497, v19461854 11/18 99233 never billed)
#   card-17478452 MEMBER-ID-REDACTED effective 11/01/2026 (chart has Medicare only; v19461642 11/16 99223, v19461630 11/17 99232 sent to Medicare)
#   card-17478455    MEMBER-ID-REDACTED effective 11/09/2026 (chart has Medicare only; seven visits 11/16-11/22 sent to Medicare / unbilled)
# Does, per chart: (1) add the CAP07 plan with the member number and the sheet's effective date - NO group number (William's standing
#   rule) - unless a CAP07 plan with that number is already on the chart; (2) AMD's free 271 on the new plan (elig_amd.run_plan) and
#   print its answer; (3) the deceased guard; (4) per visit `freq1_visit.reroute(vid, cid, "<CHP seq>", <CHP seq>)` = the visit's
#   insurance order set to the CHP plan by a no-rebill full-visit echo, then ONE frequency-1 reset + ONE chargerebill (the standing
#   one-rebill-per-visit rule); (5) the patient default order: CHP first (ins_update sequence=) where the chart holds a Medicare plan too
#   (Medicare stays on the chart - Medicare's own record names the MA plan as the payer, nothing is end-dated by this helper).
# --dry = reads and prints only. Register registers/board_plans_2026-11-25T0435Z[_dry].json (chart / visit / plan ids, no names).
# Never touches: other charts, payments, write-offs, charges' codes. Usage: python3 board_plans_1125.py [--live] [--only <pid>]
import amd, add_ins, ins_update, elig_amd, freq1_visit, re, json, sys, time
LIVE = "--live" in sys.argv; S = "2026-11-25T0435Z"
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
CAP07 = "car41826"
CHARTS = [
    ("card-17478470", "17478470", "MEMBER-ID-REDACTED", "11/17/2026", [("19461860", "23374889"), ("19461854", "23374883")]),
    ("card-17478452", "17478452", "MEMBER-ID-REDACTED", "11/01/2026", [("19461642", "23374563"), ("19461630", "23374549")]),
    ("card-17478455", "17478455", "MEMBER-ID-REDACTED", "11/09/2026", [("19461640", "23374561"), ("19461968", "23374995"), ("19461853", "23374882"), ("19461990", "23375019"), ("19462060", "23375074"), ("19462187", "23375232"), ("19462331", "23375396")]),
]
amd.login_cached()
def plans(pid):
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', t)
    return [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', t)], (m.group(1) if m else "")
reg = []
for card, pid, member, eff, visits in CHARTS:
    if ONLY and pid != ONLY: continue
    row = {"card": card, "pid": pid, "effective": eff, "steps": [], "visits": {}}
    pl, order = plans(pid)
    have = [p for p in pl if p.get("carrier") == CAP07 and p.get("subscribernum") == member and not p.get("enddate")]
    print("=== %s pat%s plans=%s insorder=%s chp-already=%s" % (card, pid, [(p.get("id"), p.get("carrier"), p.get("sequence")) for p in pl], order, bool(have)))
    if have:
        insid, seq = have[0]["id"], have[0]["sequence"]; row["steps"].append(["CAP07 plan already on the chart", insid, seq])
    elif not LIVE:
        insid, seq = None, str(len(pl) + 1); row["steps"].append(["DRY would add CAP07 plan", member[-4:], eff, "seq", seq])
    else:
        insid, seq = add_ins.add(pid, CAP07, member, eff); row["steps"].append(["add CAP07", insid, seq]); print("  add CAP07 ->", insid, seq)
        if not insid or not str(insid).startswith("ins"): print("  ADD FAILED - stop this chart"); reg.append(row); continue
    if insid:
        try:
            s = elig_amd.run_plan(pid, insid, force=True); line = elig_amd.one_line(s) if not isinstance(s, str) else s
        except Exception as e: line = "271 error %s" % e
        row["steps"].append(["AMD 271", str(line)[:300]]); print("  271:", str(line)[:300])
    # the deceased guard runs inside amd.rebill_charge (dod_guard=True) on every rebill below
    # patient default order: CHP first (chart with Medicare too)
    if LIVE and len(pl) >= 1 and not have:
        others = [p.get("sequence") for p in pl if not p.get("enddate")]
        want = ",".join([seq] + [o for o in others if o != seq])
        try: res = ins_update.update(pid, insid, sequence=want); row["steps"].append(["patient order", want, str(res)[:160]]); print("  patient order", want, "->", str(res)[:160])
        except Exception as e: row["steps"].append(["patient order error", str(e)[:120]])
    for vid, cid in visits:
        r = freq1_visit.reroute(vid, cid, seq, seq, dry=not LIVE)
        row["visits"][vid] = str(r)[:240]; print("  v%s -> %s" % (vid, str(r)[:200])); time.sleep(0.4)
    reg.append(row)
json.dump(reg, open("registers/board_plans_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
