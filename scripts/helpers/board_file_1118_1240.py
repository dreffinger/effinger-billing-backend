# PLAIN ENGLISH (board inbox file for the 7:39 AM ET 11/18 columns run, fired 12:40Z): ONE board_updates_<stamp>.json for William's Drive
#   'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops on the two standing watch rows.
# Usage: cd /home/claude/unbilled && python3 board_file_1118_1240.py -> outbox/board_updates_2026-11-18T1240Z.json
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-18T1240Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/18"
SRC = "7:39 AM ET 11/18 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/18: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/18: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 06:55Z outside the routines' own files); Claimocity feed 31 objects, 1 new (20261118): 32 visits / $6,139 entered, 4 new charts (insured from Stedi discovery: FLO02 x2, BCBS x2), 2 standing cascade holds (charts 17472491, 12182947); retry-dx: 1 visit still waits on S82.843D; feed order sweep unchanged, 0 checks bought, 0 saved; Working Denials queue 0; board drops 0; no William note since the last run; Pam Gmail nothing in 2 days. ERA Center 3 checks $2,568.83 -> 0 (Medicare 820201800 posted $2,568.83 by the Post button, CO-45 audit 0 lines; two $0 checks dismissed - 12 Medicare CO-109 wrong-payer lines on charts F261113-02 / 3339 / 3516 / 4129, 2 CO-22 lines chart 430, 1 WellCare secondary chart 4563 left to the denial handling / nightly cascade). Columns 0/1/0/1 -> 0/1/0/1 (standing holds)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
