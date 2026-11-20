# PLAIN ENGLISH (board inbox file for the 7:39 PM ET 11/19 columns run, evening slot, fired 00:40Z 11/20): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD.
#   Ops: the two standing watch rows (append), GREEN (Detego carrier not in AMD), CAMERON (Humana inactive tonight),
#   and one new card for the Humana M76 answers on chart 44953 (twinned with that chart's two earlier cards).
# Usage: cd /home/claude/unbilled && python3 board_file_1120_0040.py -> outbox/board_updates_2026-11-20T0040Z.json
import json, datetime, os
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-20T0040Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/19"
SRC = "7:39 PM ET 11/19 columns run (ehpa cloud, evening slot) - run %s" % STAMP
def app(i, checks=None, notes=None):
    a = {}
    if checks: a["checks"] = checks
    if notes: a["notes"] = notes
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": a}
ops = [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/19: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/19: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders: nothing new after 18:45Z); Claimocity feed 32 objects, 0 new (newest 20261119); retry-dx: 1 visit still waits on S82.843D; feed order sweep 0 checks bought, 0 saved, 7 not saved (standing); Working Denials queue 0; board drops 0; no card changed since 08:20Z; Pam Gmail: the 11/19 Collins thread only (worked 0640Z). ERA Center 3 checks $1,411.53 -> 0: Medicare 820211313 ($1,245.27) and Humana 206864106261118 ($166.26) posted by the Post button (+1 fallback line chart 23969 v19460189 99497 $68.11 + WOINS 47.52), Humana NO-PAY 202611170006642 dismissed; denial lines recorded: Humana M76 x3 chart 44953 (new card), PI197 chart 4350 v19461148, OA23 CCM v19459014. Columns 0/1/0/1 -> 0/1/0/1 (standing holds)."}]),
 app("[name]-17478200",
   checks=[{"ok": "no", "src": "AMD lookupcarrier %DETEGO% / %DET% (this run)", "when": WHEN, "result": "no Detego Health carrier in AdvancedMD (0 carriers)"},
           {"ok": "human", "src": "William", "when": WHEN, "result": "add the Detego Health carrier in Master Files (PO BOX 211609 SAINT PAUL MN 55121, 866-278-1074); then the next run adds policy [member id] (begin 10/07/2026, no group) and sends v19459188 + v19459194 ($421)"}],
   notes=[{"who": "Claude", "at": NOW, "text": "Thanks for the facesheet. The payer on it, Detego Health (500K limited benefit plan), is not a carrier in AdvancedMD yet - I looked it up tonight and there is none. Add it in Master Files and the next run puts policy [member id] on the chart and sends both HCA visits ($421)."}]),
 app("[name]-17478332",
   checks=[{"ok": "no", "src": "AMD eligibility (free 271) - elig_amd --all (this run)", "when": WHEN, "result": "seq 2 HUM01 H04462923 INACTIVE; seq 1 FLO02 (MBI on file) ACTIVE naming OT/PR H5434-025 BLUE CROSS AND BLUE SHIELD OF FLORIDA"}],
   notes=[{"who": "Claude", "at": NOW, "text": "The Humana MCR HMO number from the sheet (H04462923) was added, but Humana answers INACTIVE tonight and Medicare's own record names a Florida Blue Medicare Advantage plan (H5434-025) as her payer - the sheet looks older than her current plan. The Florida Blue card (member number) is still what the 11/03 visit ($433) needs."}]),
]
items = [{"id": "orwell-padraig-44953", "amdid": "44953", "status": "done"}, {"id": "orwell-padraig-denials", "amdid": "44953", "status": "claude"}]
row = {"id": "orwell-padraig-44953-m76-1112", "amdid": "44953", "patient": "ORWELL,PADRAIG", 
       "facility": "HCA Florida Capital Hospital (99233 11/12, 11/13, 11/14/2026)", "amount": 480,
       "status": "william", "inscarrier": "HUM01 Humana", "insid": "[member id]",
       "need": "WILLIAM: Humana answered three new HCA visits $0 with CO-16 + M76 (missing/invalid diagnosis) on NO-PAY remit 202611170006642 - v19461125 11/12, v19461250 11/13, v19461227 11/14/2026, 99233 $160 each ($480). The primary-diagnosis cascade finds nothing to fix (J06.9 leads, then F31.9, F32.A, G47.00, I10, F41.9, K21.9 - all acceptable). This chart is the one whose Humana claims you wrote off 9/19 and 9/21 as 'not contract payable' (Humana 277: processed per contract $0). Say 'write off' to treat these three the same way, or name a diagnosis change (e.g. the condition actually treated first) and the next run resaves and re-sends them.",
       "why": "ERA 1053578 (Humana NO-PAY 202611170006642, 11/17/2026): 3 denial-only lines CO16/M76 on chart 44953",
       "checks": [{"ok": "na", "src": "dx_primary_fix.py 44953 --visits 19461125,19461250,19461227 --dry (this run)", "when": WHEN, "result": "primary dx already acceptable on all 3 visits - nothing to fix"},
                  {"ok": "human", "src": "William", "when": WHEN, "result": "write off (contract $0, as 9/21) or a diagnosis change - $480"}],
       "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 7:39 PM ET 11/19 evening run from Humana's 11/17 no-pay remit. Not rebilled and not written off - your call."}]}
ops += plan_new_row(items, row, now=NOW)
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
