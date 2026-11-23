# PLAIN ENGLISH (board inbox file for the 1:39 PM ET 11/23 columns run, six-hourly slot, fired 18:39Z): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-23T1840Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/23"
SRC = "1:39 PM ET 11/23 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/23: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/23: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 12:56Z except the routines' own files); Claimocity feed 35 objects, 0 new (newest 20261122); Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail nothing in 2 days. ERA Center 1 check $10.21 -> 0 checks $0.00 (Medicaid FFS crossover 153082494 / ERA 1053625: chart 17475222 v19455294 posted $10.21 by the Post button - CO-45 audit left that one line for review, patient balance 9.71 on a Sunshine dual; 35 $0 denial lines recorded for the denial handling - 21 CO16/N290 rendering-id, 7 CO208/N286 referring-id, 6 CO256/CO170 managed-care/provider-type, 3 CO22/N598 COB). Columns 0/3/0/1 -> 0/3/0/1 (inspector holds v19461189 / v19461966 / v19462192 on your cards; AET12 hold)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
