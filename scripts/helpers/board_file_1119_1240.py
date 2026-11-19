# PLAIN ENGLISH (board update file, columns run 2026-11-19T1240Z). Writes outbox/board_updates_<stamp>.json via board_ops.clean_file. No AMD call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-19T1240Z"; NOW = "2026-11-19T13:05:00Z"; WHEN = "11/19"
SRC = "7:39 AM ET 11/19 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/19: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/19: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 09:35Z except a chat report); Claimocity feed 32 objects, 0 new (newest 20261119, ingested by the 0756Z button run); retry-dx: 1 visit still waits on S82.843D; feed order sweep 20261119T124334Z: 0 saved, 7 not saved (standing checks for William); Working Denials queue 0; board drops 0; no card changed since 08:20Z (the 0755Z chat answered the night's notes); Pam Gmail: the 11/19 Centre Pointe thread only (worked 0640Z). ERA Center 0 checks $0.00 -> 0 checks $0.00 (engine pass 12:44-12:53Z, 0 errors). Columns 0/1/0/1 -> 0/1/0/1 (inspector chart 17478413 O24.419 hold; AET12 hold)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
