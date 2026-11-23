# PLAIN ENGLISH (7:39 PM ET 11/22 evening columns run 2026-11-23T0040Z): writes the Insurance Refresh Board inbox file -
# two append-only checks on standing cards (AET12 hold, Availity inputs). No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-23T0040Z"; AT = "2026-11-23T01:05:00Z"; WHEN = "11/22"
SRC = "7:39 PM ET 11/22 columns run (ehpa cloud, evening slot) - run " + STAMP
ops = [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [
   {"ok": "na", "result": "7:39 PM ET 11/22: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row).", "src": SRC, "when": WHEN}]}},
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [
   {"ok": "na", "result": "7:39 PM ET 11/22: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 18:56Z except this run's START); Claimocity feed 35 objects, 0 new (newest 20261122); Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail nothing in 2 days. ERA Center 0 checks $0.00 -> 0 checks $0.00 (engine pass 00:43-00:52Z, 0 errors). Columns 0/3/0/1 -> 0/3/0/1 (inspector holds v19461189 / v19461966 / v19462192; AET12 hold). 'current face sheets needed' email sent (17 charts, $7,740.43).", "src": SRC, "when": WHEN}]}},
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run " + STAMP, "created": AT, "ops": ops})
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1); print("wrote", p, len(doc["ops"]), "ops")
