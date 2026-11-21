# PLAIN ENGLISH (board inbox file for the 1:39 AM ET 11/21 columns run, six-hourly slot, fired 06:39Z): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
# Usage: cd /home/claude/unbilled && python3 board_file_1121_0040.py -> outbox/board_updates_2026-11-21T0640Z.json
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-21T0640Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/21"
SRC = "1:39 AM ET 11/21 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/21: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 2 runs -> 1 row after this run fixed chart 17478224 on run 1700396)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/21: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders: nothing new after 00:55Z except the nightly cascade's own files); Claimocity feed 33 objects, 0 new (newest 20261120); retry-dx: nothing to retry; Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail: nothing new (Barclay 22:39Z already worked). ERA Center 0 checks $0.00 -> 0 checks $0.00 (engine pass 06:43-06:52Z, 0 errors). Columns 0/2/31/2 -> 0/2/0/1: 31 Unbilled prior-payor rows released; new exclusion on your claim run 1700396 (chart 17478224 v19459239 Medicare CCM $315, PNM10500 subscriber middle name '(RITA)') fixed - middle name RITA, re-sent frequency 1, completed; inspector charts 17478413 / 17478350 holds; AET12 hold."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
