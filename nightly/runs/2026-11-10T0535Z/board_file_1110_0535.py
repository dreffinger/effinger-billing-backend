#!/usr/bin/env python3
# PLAIN ENGLISH (board inbox file for the 12:35 AM ET 11/10 nightly cascade, 05:35Z): builds board_updates_2026-11-10T0535Z.json
#   through board_ops.clean_file - append-only checks / api / note on the ONE chart the pre-claim check flagged tonight (the
#   existing card on that chart, same work item -> no new row). No `updated` in any set; no status / need / why change.
#   Writes nothing to AMD or the board; the page applies the file when William opens it.
import json, sys, datetime
sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-10T0535Z"; NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/10"
SRC = "12:35am ET 11/10 nightly cascade (ehpa cloud) - run %s" % STAMP
ops = []
ops.append({"op": "upsert", "collection": "items", "id": "marsh-[name]-17473090",
    "set": {"lastdos": "11/07/2026"},
    "append": {
        "checks": [
            {"ok": "no", "src": "Stedi MBI lookup (precheck, DOS 11/07/2026, cached from the 11/2 lookup) - run %s" % STAMP,
             "result": "ADVANTAGE PLAN on DOS: HEALTH CARE SERVICE CORPORATION, coordination of benefits since 01/01/2024 - the 11/7/2026 hospital visit 99233 ($160, v19459907) had come in from the feed against Medicare FLO02 again (billed 11/09)", "when": WHEN},
            {"ok": "ok", "src": "AMD getdemographic (chart plans) - run %s" % STAMP,
             "result": "seq 1 car6062 BCBS (HCSC 65 Plus Medicare Advantage PPO), seq 2 car6085 FLO02 Medicare - both open; no plan add needed", "when": WHEN},
            {"ok": "ok", "src": "dx_primary_fix --dry visit 19459907", "result": "primary dx R55 acceptable on 99233 - no change", "when": WHEN},
            {"ok": "ok", "src": "AMD action: freq1_visit reroute 19459907 / charge 23372516, order 1 (MA plan alone per the 11/5 lesson), seq 1",
             "result": "visit insorder 2,1 -> 1 (1 live charge echoed), frequency 1, chargerebill to BCBS seq 1 -> 204; no payment on the visit", "when": WHEN}],
        "api": [{"at": NOW, "src": "Stedi API - MBI lookup MBILUNOSSN (precheck cache, DOS 20261107)",
                 "text": "[name]  DOB [DOB]  state FL  DOS 20261107\nmbi: [MBI]  partA: 20100601  partB: 20100601  death: none\nADVANTAGE PLAN on DOS: HEALTH CARE SERVICE CORPORATION  (coordinationOfBenefits 20240101)\n[cached answer from the 11/2 lookup - no new Stedi charge tonight]"}],
        "notes": [{"who": "Claude", "at": NOW,
                   "text": "11/10 nightly: one more hospital visit (11/7 99233, $160) arrived from the feed pointed at Medicare; Medicare's record still names HCSC Blue Cross Medicare Advantage as her plan since 1/1/2024, so the visit now sits at the BCBS plan alone (order 1) as an original claim, like the 10/30-11/6 visits before it. Nothing for you here."}]}})
doc = clean_file({"schema": "irb-board-updates/1", "source": "nightly cascade %s" % STAMP, "created": NOW, "ops": ops})
json.dump(doc, open("board_updates_%s.json" % STAMP, "w"), indent=1)
print("board_updates_%s.json: %d ops" % (STAMP, len(doc["ops"])))
