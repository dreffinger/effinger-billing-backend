# PLAIN ENGLISH (board inbox file for the 7:39 AM ET 11/23 columns run, six-hourly slot, fired 12:39Z): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-23T1240Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/23"
SRC = "7:39 AM ET 11/23 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/23: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/23: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 07:00Z except the routines' own files); Claimocity feed 35 objects, 0 new (newest 20261122); Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail nothing in 2 days. ERA Center 1 check $83.13 -> 0 checks $0.00 (Humana 207389160261122: chart 17477972 v19461286 posted $83.13 by the Post button, CO-45 76.87 already written off). Columns 0/3/0/1 -> 0/3/0/1 (inspector holds v19461189 / v19461966 / v19462192 on your cards; AET12 hold)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
