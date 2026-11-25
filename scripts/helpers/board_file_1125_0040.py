# PLAIN ENGLISH (board update file, columns run 2026-11-25T0040Z). Writes outbox/board_updates_<stamp>.json via board_ops.clean_file. No AMD call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-25T0040Z"; NOW = "2026-11-25T01:15:00Z"; WHEN = "11/24"
SRC = "7:39 PM ET 11/24 columns run (ehpa cloud, evening slot) - run %s" % STAMP
def app(i, checks=None):
    return {"op": "upsert", "collection": "items", "id": i, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/24: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/24: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders nothing new after 19:05Z); Claimocity feed 36 objects, 20261124 re-listed - all 26 visits already in AMD, 0 entered; retry-dx: 2 visits still wait on S82.843D; feed order sweep 0 saved, 7 not saved (standing); Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail nothing in 2 days. ERA Center 3 checks $206.67 -> 0: Ambetter 0935804550 (ERA 1053635) - 2 visits posted $206.67 by the Post button (chart 4812 v19461481 99309 $97.67, chart F261109-04 v19461447 99233 $109.00), CO-45 audit 0 lines; WellCare $0 X320073604 (ERA 1053636) - 10 CO-109 wrong-payer + 2 CO-16/M56 lines on charts 1059 and 4563 recorded for the denial handling / cascade; VA CCN $0 3681230165 (ERA 1053634) - 1 CO-288 line chart 4389 recorded; both dismissed. Columns 0/5/0/1 -> 0/5/0/1 (inspector holds on your cards; AET12 hold). 'current face sheets needed' email sent (18 charts, $8,343.43 - unchanged)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]))
