#!/usr/bin/env python3
# PLAIN ENGLISH (Florida Blue-on-a-Medicare-retiree order fix, chart 17473245, 1 PM ET 10/21/2026 run 2026-10-21T1710Z).
# Florida Blue check 1053245 answered PR-22 / MA04 ($0, 'other payer is primary - send the primary's adjudication') a SECOND time on
#   three Medicare-paid charges (v19452629 99487 + 99489 and v19452861 99309, 8/2026) and AMD transferred the whole remainder to the
#   PATIENT balance ($142.72 + $74.05 + $74.64 = $291.41) - the standing 9/23 lesson: the chart carries Florida Blue (BlueOptions
#   Standard PPO retiree plan, seq 1) AHEAD of Medicare (seq 2), so every claim goes to Florida Blue as a primary and bounces, and
#   Medicare's CO-45 / CO-253 contractual (check 819979797-era 819814877, 9/19/2026) was never written off.
# Decides (William's 9/23 flow, applied by the routine since): (1) chart default order Medicare first (ins_update sequence "2,1");
#   (2) move every patient balance back to insurance (move_to_ins.move, no rebill); (3) write off Medicare's contractual WOINS with
#   the Medicare check number (manual_post pay 0.0 - a processed check cannot be re-posted ERA-linked), leaving only the PR-2
#   coinsurance ($16.14 + $8.92 + $16.93) on insurance; (4) ONE frequency-1 re-route per visit to Florida Blue as the SECONDARY
#   (freq1_visit.reroute order "2,1", seq 1 - Medicare's adjudication rides on the posted payment reasons). Deceased guard inside
#   amd.rebill_charge. --dry prints the plan. Register registers/fb_secondary_fix_<stamp>.json. Never a write-off of a PR amount.
# Usage: python3 fb_secondary_fix_1021_1710.py [--dry]
import json, sys, time, os, amd, ins_update, move_to_ins, manual_post, freq1_visit
S = "2026-10-21T1710Z"; dry = "--dry" in sys.argv; PID = "17473245"; MEDICARE_INS = "ins9519180"; MCHK = "819814877"
WO = {"23362978": 126.58, "23362979": 65.13, "23363234": 57.71}            # CO-45 + CO-253 from Medicare's 9/19/2026 remit, never adjusted
VISITS = {"19452629": "23362978", "19452861": "23363234"}
amd.login_cached(); log = {"stamp": S, "pid": PID, "steps": []}
def step(name, res): print(name, "->", res); log["steps"].append({"step": name, "result": str(res)[:300]})
if dry: step("chart order", "DRY ins_update.update(%s, %s, sequence='2,1')" % (PID, MEDICARE_INS))
else: step("chart order", ins_update.update(PID, MEDICARE_INS, sequence="2,1")); time.sleep(0.6)
for cid, wo in WO.items():
    step("move back %s" % cid, move_to_ins.move(cid, None, dry=dry, rebill=False)); time.sleep(0.6)
    step("WOINS %s %.2f" % (cid, wo), manual_post.post(cid, "FLO02", 0.0, wo, "WOINS", checknumber=MCHK, note="Medicare contractual never adjusted - FB PR-22 move-back run %s" % S, dry=dry)); time.sleep(0.6)
for vid, cid in VISITS.items():
    step("reroute v%s" % vid, freq1_visit.reroute(vid, cid, "2,1", 1, dry=dry)); time.sleep(0.6)
os.makedirs("registers", exist_ok=True); json.dump(log, open("registers/fb_secondary_fix_%s%s.json" % (S, "_dry" if dry else ""), "w"), indent=1)
