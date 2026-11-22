# PLAIN ENGLISH (board inbox file for the 7:39 PM ET 11/21 columns run, evening slot, fired 00:39Z 11/22): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
# Usage: cd /home/claude/unbilled && python3 board_file_1122_0039.py -> outbox/board_updates_2026-11-22T0039Z.json
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-22T0039Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/21"
SRC = "7:39 PM ET 11/21 columns run (ehpa cloud, evening slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/21: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/21: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 18:40Z except an unrelated MEC letter); Claimocity feed 34 objects, 0 new (newest 20261121); retry-dx 1 visit waits on S82.843D; feed order sweep 7 standing, 0 bought, 0 saved; Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail: the 11/20 threads only. ERA Center 2 checks $746.10 -> 0 (Humana 207259647261121 $438.35 + 207259646261121 $307.75 posted by the Post button; CO-45 already corrected; one OA-23 $0 CCM secondary line on chart 2596 v19459284 to the denial handling). Columns 0/2/0/1 -> 0/2/0/1 (standing holds). 'current face sheets needed' email sent (19 charts, unchanged)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
