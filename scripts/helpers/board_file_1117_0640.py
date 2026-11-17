# PLAIN ENGLISH (board inbox file for the 1:39 AM ET 11/17 six-hourly columns run, fired 06:39Z 11/17): ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops through board_ops.clean_file
#   (no `updated`, no status change): the standing watch rows aet12-carrier-cpid and availity-remits-backlog with this run's numbers.
# Usage: cd /home/claude/unbilled && python3 board_file_1117_0640.py -> outbox/board_updates_2026-11-17T0640Z.json
import json, datetime
from board_ops import clean_file
STAMP = "2026-11-17T0640Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/17"
SRC = "1:39 AM ET 11/17 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
ops = [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/17: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]}},
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/17: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 00:55Z except the routines' own files and a 9/1 progress note); Claimocity feed 29 objects, 0 new (newest 20261116); Working Denials queue 0; board drops 0; no William note since the last run; Pam Gmail: nothing in 2 days. ERA Center 0 checks $0.00 -> 0 checks $0.00 (engine pass 06:43-06:51Z, 0 errors). Columns 0/1/0/1 -> 0/1/0/1 (inspector chart 17478413 O24.419 hold; AET12 hold)."}]}},
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]))
