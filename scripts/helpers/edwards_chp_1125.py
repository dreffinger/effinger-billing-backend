#!/usr/bin/env python3
# PLAIN ENGLISH (chart 17478414 - the Brynwood 11/08/2026 admit whose chart the feed created on 11/22; card edgerton-micah-admit-1108)
# Decides: nothing. The card (from Pam's 11/9 admission record) names Capital Health Plan (HMO) policy [member id] for this patient and
#   says: when the chart exists, add CHP car41826 with that policy (no group), AMD 271, visit insorder, release. The chart exists now
#   (17478414, Medicare plan only); Medicare's own record names CAPITAL HEALTH PLAN as the primary (this run's feed cascade HOLD on the
#   reprocessed 11/09 visit). Cascade rule (a): add the MA plan, point the visits at it, ONE frequency-1 claim each:
#   v19462412 (11/09/2026 99306+99497, never billed) and v19462163 (11/19/2026 99309, sent to Medicare 11/22) -> freq1_visit.reroute.
# Never touches: other charts, the Medicare plan (stays on the chart), payments. Usage: python3 edgerton_chp_1125.py [--live]
import amd, add_ins, ins_update, elig_amd, freq1_visit, json, re, sys, time, os
LIVE = "--live" in sys.argv; S = "2026-11-25T0634Z"; PID = "17478414"; CAP07 = "car41826"
BOARD = "/tmp/claude-0/-home-claude-effinger-billing-backend/54dad968-8e54-5d62-b91f-c8705cdd698d/scratchpad/board_0634/items/edgerton-micah-admit-1108.json"
o = json.load(open(BOARD)); x = o.get("data", o); m = re.search(r"policy\s+([A-Z]{3}\d{8})", x.get("need") or "", re.I); policy = m.group(1) if m else ""
amd.login_cached(); out = {"pid": PID, "live": LIVE, "steps": [], "visits": {}}
print("policy", "found" if policy else "NOT FOUND on the card")
raw, plans, order = ins_update._plans(PID); pl = list(plans.values())
have = [p for p in pl if p.get("carrier") == CAP07 and not p.get("enddate")]
if have: insid, seq = have[0]["id"], have[0]["sequence"]; out["steps"].append(["CAP07 already on the chart", insid, seq])
elif not LIVE or not policy: insid, seq = None, str(len(pl) + 1); out["steps"].append(["DRY would add CAP07", policy[-4:], "11/08/2026"])
else:
    insid, seq = add_ins.add(PID, CAP07, policy, "11/08/2026"); out["steps"].append(["add CAP07", insid, seq]); print("add CAP07 ->", insid, seq)
if insid and LIVE:
    s = elig_amd.run_plan(PID, insid, force=True); out["steps"].append(["AMD 271", elig_amd.one_line(s)[:300]]); print("271:", elig_amd.one_line(s)[:300])
    others = [p.get("sequence") for p in pl if not p.get("enddate") and p.get("sequence") != seq]
    want = ",".join([str(seq)] + others); res = ins_update.update(PID, insid, sequence=want); out["steps"].append(["patient order", want, str(res)[:120]]); print("patient order", want, "->", str(res)[:120])
for vid, cid in (("19462412", "23375502"), ("19462163", "23375207")):
    r = freq1_visit.reroute(vid, cid, str(seq), seq, dry=not LIVE); out["visits"][vid] = str(r)[:240]; print("v%s -> %s" % (vid, str(r)[:220])); time.sleep(0.4)
json.dump(out, open("registers/edgerton_chp_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
