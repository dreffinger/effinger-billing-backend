# PLAIN ENGLISH (board update file, columns run 2026-11-24T1844Z). Writes outbox/board_updates_<stamp>.json via board_ops.clean_file. No AMD call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-24T1844Z"; NOW = "2026-11-24T19:10:00Z"; WHEN = "11/24"
SRC = "1:39 PM ET 11/24 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks=None, notes=None):
    a = {}
    if checks: a["checks"] = checks
    if notes: a["notes"] = notes
    return {"op": "upsert", "collection": "items", "id": i, "append": a}
ops = [
 app("aet12-carrier-cpid", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/24: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]),
 app("availity-remits-backlog", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/24: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders nothing new after 12:40Z); Claimocity feed 36 objects, 20261124 re-listed - all 26 visits already in AMD, 0 entered; retry-dx: 2 visits still wait on S82.843D; feed order sweep 0 saved, 7 not saved (standing); Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail nothing in 2 days. ERA Center 1 check $3,235.37 -> 0: Capital Health Plan 4132551 (ERA 1053632) - 30 visits posted $3,235.37 by the Post button, CO-45 audit: every contractual already written off; 1 denial line (chart F1028-11 v19459256 10/22/2026 99309 $141, CO-97/M15 bundled) recorded for the denial handling; check dismissed. Columns 0/5/0/1 -> 0/5/0/1 (inspector holds v19461189 Pattern 28158, v19461966 / v19462318 / v19462335 Pattern 692, v19462192 Pattern 4531 on your cards; AET12 hold)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]))
