#!/usr/bin/env python3
# PLAIN ENGLISH (board inbox file for the 1:39 AM ET 11/12 columns run, fired 06:40Z): writes ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db, no approval). Decides nothing in AMD. Ops are APPEND-ONLY:
#   (1) the Westminster Oaks admit row (chart 17478318): Pam's second photo of 03:03Z 11/12 is the same PCC Clinical Resident Profile
#       the 18:39Z 11/11 run already acted on (CHP plan added, six HCA visits re-pointed and sent 11/11) - a live read this run confirms;
#   (2) the standing watch rows (availity-remits-backlog, aet12-carrier-cpid) get this run's column / ERA numbers.
#   No set carries status / need / why / updated (William 11/2/2026). Row ids with a name live in secrets/run_0640_ids.json (PHI gate).
# Usage: cd /home/claude/unbilled && python3 board_file_1112_0640.py -> outbox/board_updates_2026-11-12T0640Z.json
import json, os, datetime, sys
from board_ops import clean_file
ids = json.load(open("secrets/run_0640_ids.json"))
STAMP = "2026-11-12T0640Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/12"
SRC = "1:39am ET 11/12 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
summary = json.load(open("outbox/run_summary_0640.json")) if os.path.exists("outbox/run_summary_0640.json") else {}
cols = summary.get("cols", "columns: see the run digest"); era = summary.get("era", "ERA Center: see the run digest")
ops = []
ops.append({"op": "update", "collection": "items", "id": ids["grantham_row"], "set": {},
            "append": {"checks": [{"ok": "ok", "src": SRC + " - Pam Gmail 03:03Z 11/12 (second photo on the same thread) + AMD getdemographic / gettxhistory live read",
                                   "when": WHEN,
                                   "result": "the second photo is the same PCC Clinical Resident Profile (Westminster Oaks, admitted 11/10/2026 from Capital Regional, Primary Payer Capital Health Plan, policy on the sheet, Medicare HIC listed) the 1:39 PM ET 11/11 run acted on; live chart: CHP plan seq 2 (begin 10/01/2018, no group) is the patient's default order, the Cigna dental plan ended 11/02/2026, all six HCA visits 11/03-11/08/2026 ($865) carry CAP07 with bill date 11/11/2026, no payment yet - nothing more to do until CHP answers"}],
                       "notes": [{"who": "Claude", "at": NOW, "text": "Pam sent the same Westminster Oaks admission sheet again at 10:03 PM ET 11/11 - already acted on 1:39 PM: CHP is on the chart and the six hospital claims went to CHP as originals on 11/11. Nothing needed from you unless CHP rejects them."}]}})
for rid in ("availity-remits-backlog", "aet12-carrier-cpid"):
    txt = ("%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 11/11 18:00Z outside the routines' own files); no new 835 or facesheet file; Claimocity feed 24 objects, 0 new (newest 20261111); Working Denials queue 0; board drops 0; 0 Claude-turn rows changed since 00:30Z; Pam Gmail: the 11/11 Westminster Oaks thread only (second photo = the same sheet, already acted on). %s. %s." % ("1:39 AM ET 11/12", era, cols)) if rid == "availity-remits-backlog" else \
          ("1:39 AM ET 11/12: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged.")
    ops.append({"op": "update", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN, "result": txt}]}})
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
clean_file(doc)
os.makedirs("outbox", exist_ok=True)
out = "outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(out, "w"), indent=1)
print("wrote", out, len(ops), "ops")
