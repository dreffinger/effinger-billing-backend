# PLAIN ENGLISH (board update file, columns run 2026-11-24T1241Z). Writes outbox/board_updates_<stamp>.json via board_ops.clean_file. No AMD call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-24T1241Z"; NOW = "2026-11-24T13:10:00Z"; WHEN = "11/24"
SRC = "7:41 AM ET 11/24 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks=None, notes=None):
    a = {}
    if checks: a["checks"] = checks
    if notes: a["notes"] = notes
    return {"op": "upsert", "collection": "items", "id": i, "append": a}
ops = [
 app("[name]-17478452", checks=[{"ok": "no", "src": "Medicare $0 remit check 350245820 (ERA 1053629, 11/24)", "when": WHEN,
   "result": "Medicare denied v19461642 11/16 99223 and v19461630 11/17 99232 with MA01 + N418 (misrouted - another payer) - confirms the Capital Health Plan Advantage plan; still needs the CHP member number to add CAP07 and re-send"}]),
 app("aet12-carrier-cpid", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:41 AM ET 11/24: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:41 AM ET 11/24: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders nothing new after 07:00Z); Claimocity feed 36 objects, 1 new (20261124): 26 visits / $5,292 entered, 0 new charts, 2 standing cascade holds (charts 17478455 CHP, 12182947 Sunshine); retry-dx: 2 visits still wait on S82.843D; feed insurance intake: 11 already on chart, 1 LTC-only; Working Denials queue 0; board drops 0; Pam Gmail nothing in 2 days. ERA Center 1 check $0.00 -> 0 (Medicare $0 remit 1053629: 14 MA01/N418 wrong-payer denial lines recorded for the cascade, dismissed). Columns 0/6/0/1 -> 0/5/0/1 (chart 17478349 UMR source-of-payment advisory bypassed; inspector holds for William: v19461189 Pattern 28158, v19461966 / v19462318 / v19462335 Pattern 692 initial-hospital-care, v19462192 Pattern 4531; AET12 hold)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]))
