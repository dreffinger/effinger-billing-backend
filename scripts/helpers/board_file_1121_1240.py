# PLAIN ENGLISH (board inbox file for the 7:39 AM ET 11/21 columns run, six-hourly slot, fired 12:39Z): ONE board_updates_<stamp>.json
#   for William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. One new card (chart 17475970 11/5 HCA stay
#   billed to Medicare Part A-only, VA CCN auth needed, twinned with lowry-fenwick) + append-only checks on the two standing watch rows.
# Usage: cd /home/claude/unbilled && python3 board_file_1121_1240.py -> outbox/board_updates_2026-11-21T1240Z.json
# (identifiers removed from this copy after the run for the PHI gate - the uploaded file carried dob and MBI)
import json, datetime, os
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-21T1240Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/21"
SRC = "7:39 AM ET 11/21 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks):
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": {"checks": checks}}
items = [{"id": "lowry-fenwick", "amdid": "17475970", "twins": []}]
row = {"id": "lowry-fenwick-17475970-stay-1105", "amdid": "17475970", "patient": "LOWRY,FENWICK", "dob": "",
 "facility": "HCA FLORIDA CAPITAL HOSPITAL (feed fac29, admitted 11/05/2026)", "amount": 1600,
 "status": "william",
 "need": "WILLIAM: VA CCN authorization needed for the 11/05/2026 HCA admission (about $1,600 so far). The Claimocity feed entered this stay's 99233s (v19461085 11/9, v19461064 11/10, v19461041 11/11, v19461136 11/12, v19461269 11/13, v19461242 11/14, v19461295 11/15, v19461449 11/16, v19461629 11/17, v19461858 11/18) with the chart's order 2 = Medicare. Medicare answered the 11/15 claim PR-27 'coverage terminated' (check 350239508, $0) and AMD's own 271 shows why: Medicare is Part A only (no Part B) - physician visits are not Medicare's. His payer is VA CCN (seq 1,, 271 ACTIVE), which rejects any claim without a 12-byte VA auth for the stay (NPV087, the 8/10 and 9/4 stays). Send the VA authorization for the 11/5 stay (HSRM / Optum VA CCN 877-881-7618, or the HCA facesheet if it prints one) and the next run writes it on a referral plan, moves all the stay's visits to VA CCN and re-sends them as originals. Nothing is changed until then (the visits stay on insurance balance, not on the patient).",
 "why": "Medicare $0 remit 350239508 (ERA 1053612, 11/21): PR-27 on v19461295 11/15/2026 99233; AMD 271 Medicare = Part A only since 05/2010, no Part B; the feed sets the stay's visits to Medicare (chart order 2)",
 "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 7:39 AM ET 11/21 run. The feed keeps sending this hospital stay to Medicare, but his Medicare is hospital-only (Part A) - his doctor visits belong to VA CCN, which needs the stay's authorization number. I need that number; everything else is ready."}],
 "checks": [{"ok": "no", "src": "Medicare ERA 1053612 (check 350239508)", "result": "v19461295 11/15/2026 99233 $160: PR27 coverage terminated, MA01, $0", "when": WHEN},
            {"ok": "ok", "src": "AMD eligibility (free 271) - elig_amd --all", "result": "seq 1 VACCN ACTIVE; seq 2 FLO02 ACTIVE Part A 20100501, NO Part B", "when": WHEN},
            {"ok": "human", "src": "William", "result": "VA CCN 12-byte authorization for the 11/05/2026 HCA admission", "when": WHEN}]}
ops = plan_new_row(items, row, same_item=False, now=NOW)
ops += [
 app("aet12-carrier-cpid", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/21: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/21: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders: nothing new after 06:57Z except the 0640Z run's own files); Claimocity feed 34 objects, 1 new (20261121): 84 visits / $13,146 entered on 69 charts, 54 released, 3 held (chart 17477183 no plan); retry-dx: 1 visit still waits on S82.843D; Working Denials queue 0; board drops 0; no card changed since 11/19 08:16Z; Pam Gmail: nothing new. ERA Center 2 checks $322.74 -> 0 (Medicare 820230394: four visits posted $322.74 by the Post button, CO-45 audit 0 lines; Medicare $0 350239508 dismissed - chart 4524 CCM CO-151/CO-234 to the denial handling, chart 17475970 PR-27 -> new card). Columns 0/4/0/1 -> 0/2/0/1: chart 17478349 two UMR source-of-payment advisories bypassed by error id; inspector charts 17478413 / 17478350 holds; AET12 hold."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [(o["op"], o["id"]) for o in doc["ops"]])
