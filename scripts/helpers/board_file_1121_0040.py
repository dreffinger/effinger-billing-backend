# PLAIN ENGLISH (board inbox file for the 7:39 PM ET 11/20 columns run, evening slot, fired 00:39Z 11/21): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
# Usage: cd /home/claude/unbilled && python3 board_file_1121_0040.py -> outbox/board_updates_2026-11-21T0040Z.json
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-21T0040Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/20"
SRC = "7:39 PM ET 11/20 columns run (ehpa cloud, evening slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/20: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/20: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 18:30Z except the routines' own files); Claimocity feed 33 objects, 0 new (newest 20261120); retry-dx: 1 visit still waits on S82.843D; feed order sweep 7 visits / 5 charts empty order (standing); Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail: one new Centre Pointe admit 22:39Z 11/20 (chart 17477851 - Medicare + Florida Medicaid already on the chart, order 2,3, both ACTIVE on AMD 271; nothing to change). ERA Center 2 checks $3,082.64 -> 0 (WellCare/Sunshine 1008884527 $170.92 and Capital Health Plan 4132044 $2,911.72 posted by the Post button; 3 CHP lines on charts 17478343 / 17469476 posted ERA-linked by the fallback $304.87 + WOINS $279.13). Columns 0/2/0/1 -> 0/2/0/1 (inspector charts 17478413 O24.419 / 17478350 Pattern 692 holds; AET12 hold). 'current face sheets needed' email sent (19 charts, $8,584)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
