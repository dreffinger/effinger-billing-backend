# PLAIN ENGLISH (board inbox file for the 1:39 AM ET 11/23 columns run, six-hourly slot, fired 06:39Z): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-23T0640Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/23"
SRC = "1:39 AM ET 11/23 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/23: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/23: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 00:55Z except the routines' own files and non-billing letter drafts); Claimocity feed 35 objects, 0 new (newest 20261122); Working Denials queue 0; board drops 0; Pam Gmail nothing in 2 days. ERA Center 0 checks $0.00 -> 0 checks $0.00 (engine pass 06:45-06:54Z, 0 errors). Columns 0/3/31/1 -> 0/3/0/1: 29 Unbilled prior-payor visits (31 rows) released; inspector holds v19461189 / v19461966 / v19462192 for you; AET12 hold."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
