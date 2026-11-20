# PLAIN ENGLISH (board inbox file for the 7:39 AM ET 11/20 columns run, fired 12:40Z): ONE board_updates_<stamp>.json for William's
#   Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Ops: the two standing watch rows (append), one more
#   Humana M76 line on the chart-44953 M76 card, the 11/20 feed visit held on chart 17478455 (CHP card), and a new card for the
#   Pattern 692 inspector hold on chart 17478350 (twinned with that chart's done card).
# Usage: cd /home/claude/unbilled && python3 board_file_1120_1240.py -> outbox/board_updates_2026-11-20T1240Z.json
import json, datetime, os
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-20T1240Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/20"
SRC = "7:39 AM ET 11/20 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks=None, notes=None):
    a = {}
    if checks: a["checks"] = checks
    if notes: a["notes"] = notes
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": a}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/20: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/20: no new Availity PDF / Check-EFT export / 835 / facesheet; Claimocity feed 33 objects, 1 new (20261120): 36 visits / $6,760 entered, 1 new chart (F261120-01, Medicare from discovery), 2 cascade holds (charts 17478455 CHP, 12182947 Sunshine - standing cards), 1 inspector hold (chart 17478350 Pattern 692); retry-dx: 1 visit still waits on S82.843D; feed order sweep 0 bought / 0 saved / 7 standing; Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z. ERA Center 3 checks $508.81 -> 0: Humana 206996996261119 $508.81 posted by the Post button (6 visits, CO-45 already off), Humana NO-PAY 202611180006174 (OA-23 x3 chart 20379, cascade) and 202611180006175 (M76 chart 44953 v19461280) dismissed. Columns 0/2/0/1 -> 0/2/0/1 (standing holds + the new 692 hold)."}]),
 app("orwell-padraig-44953-m76-1112",
   checks=[{"ok": "no", "src": "Humana NO-PAY 202611180006175 (ERA 1053593, 11/18)", "when": WHEN, "result": "v19461280 11/15/2026 99233 $160 CO-16 + M76, $0 paid"},
           {"ok": "na", "src": "dx_primary_fix.py 44953 --visits 19461280 --dry (this run)", "when": WHEN, "result": "primary dx J06.9 already acceptable - nothing to fix"}],
   notes=[{"who": "Claude", "at": NOW, "text": "One more of the same: Humana's 11/18 no-pay remit answered the 11/15 visit (v19461280, 99233, $160) CO-16/M76 too. Same diagnosis list, nothing for the cascade to fix. Your 'write off' or diagnosis-change answer above now covers four visits, $640. Not rebilled, not written off."}]),
 app("[name]-17478455",
   checks=[{"ok": "no", "src": "Claimocity feed 20261120 cascade (claimocity_verify)", "when": WHEN, "result": "CMS names CAPITAL HEALTH PLAN (CAP07) as the MA payer; no CAP07 plan on the chart - the new feed visit is held in the report only"}],
   notes=[{"who": "Claude", "at": NOW, "text": "Today's feed brought another HCA visit for this chart; it waits on the same thing - the CHP member number (card or facesheet)."}]),
]
items = [{"id": "dorrance-seton-17478350", "amdid": "17478350", "status": "done"}]
row = {"id": "dorrance-seton-17478350-692-1114", "amdid": "17478350", "patient": "DORRANCE,SETON",
       "facility": "HCA Florida Capital Hospital (99223 11/14/2026)", "amount": 310, "status": "william",
       "need": "WILLIAM: the Claim Inspector holds today's feed visit v19461966 (11/14/2026, 99223, $310) on Pattern 692 - 'Initial hospital care code 99223' because the chart already carries a 99223 from the 11/06/2026 admission (v19460540). The feed gives this visit an admission date of 11/14/2026, so it may be a readmission. Say 'subsequent' and the next run changes the line to 99233 and releases it, 'readmit' if this was a new admission (then it stays 99223 and the run writes the new admission date), or 'void' if it is a duplicate.",
       "why": "Claimocity feed 20261120 import - inspector Pattern 692 on v19461966",
       "checks": [{"ok": "human", "src": "Claim Inspector Pattern 692 (claimocity_inspector, this run)", "when": WHEN, "result": "HELD: second 99223 on the chart (11/06 admission already billed 99223)"}],
       "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 7:39 AM ET 11/20 run. The routine never bypasses a coding edit without your word."}]}
ops += plan_new_row(items, row, now=NOW)
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
