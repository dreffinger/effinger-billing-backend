# PLAIN ENGLISH (board inbox file for the 7:39 AM ET 11/17 six-hourly columns run, fired 12:39Z 11/17): ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD.
#   - NEW card garland-g-mercy-[first]-17478434 (William's turn): the Claimocity feed created duplicate chart F261117-01 because Claimocity
#     still sends her old DOB <feed DOB> (the chart was corrected to <chart DOB> on 9/21); twinned with garland-g-mercy-denials (board_ops).
#   - append-only checks on the standing watch rows aet12-carrier-cpid and availity-remits-backlog.
# Usage: cd /home/claude/unbilled && python3 board_file_1117_1239.py -> outbox/board_updates_2026-11-17T1239Z.json
import json, datetime, os
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-17T1239Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/17"
SRC = "7:39 AM ET 11/17 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
items = [{"id": "garland-g-mercy-denials", "amdid": "17471238", "status": "done"}]   # inline board read: the only card on these charts
row = {"id": "garland-g-mercy-[first]-17478434", "patient": "GARLAND-G,MERCY", "facility": "Centre Pointe Health & Rehab",
       "amdid": "17471238", "mbi": "", "amount": 0, "status": "william",
       "need": ("YOUR CALL (UI): the Claimocity feed created a DUPLICATE chart for her this morning - chart F261117-01 (pat17478434) - because "
                "Claimocity still sends her old birth date <feed DOB>; her real chart 17471238 was corrected to <chart DOB> on 9/21 from your facesheet. "
                "No charge and no insurance were put on the duplicate (its only visit was skipped). Please (1) inactivate / merge chart F261117-01 in AMD and "
                "(2) correct her DOB in Claimocity so the feed stops sending 11/19. The feed's patient map now points her Claimocity id at chart 17471238, so later "
                "visits land on the right chart. ALSO: her 11/09/2026 nursing visit (99309 + G0439 annual wellness visit, Pamela G.) was NOT entered - the feed "
                "import does not know G0439 yet (no fee/pcode in claimocity_import.py); add G0439 to the import tables (or say 'enter the 99309 alone') and the "
                "retry step enters it."),
       "why": "Claimocity feed 2026-11-17 (file 20261117): name matched two same-name charts with DOB <chart DOB>, feed DOB <feed DOB> -> new chart created",
       "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 7:39 AM ET 11/17 run. Duplicate chart from the feed's stale DOB - merge/inactivate it; the map is already fixed."}],
       "checks": [{"ok": "no", "src": "claimocity_resolve (feed DOB [DOB] vs charts 17471238 / 17471333 at 19341129)", "result": "MISSING -> claimocity_newcharts created pat17478434 F261117-01 (no IN1, no plan)", "when": WHEN},
                  {"ok": "ok", "src": "registers/claimocity_patient_map.json (this run)", "result": "Claimocity id 65d64419... repointed pat17478434 -> pat17471238", "when": WHEN},
                  {"ok": "no", "src": "claimocity_import (feed_recon_20261117T1239Z)", "result": "11/09/2026 G0439 + 99309 not entered: unknown CPT G0439", "when": WHEN}]}
ops = plan_new_row(items, row, now=NOW)
ops += [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/17: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]}},
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 AM ET 11/17: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 06:55Z except the routines' own files); Claimocity feed 30 objects, 1 new (20261117): 60 visits / $9,898 entered, 2 new charts (one a duplicate - card garland-g-mercy-[first]-17478434), 1 cascade hold (chart 17472491, standing), 1 visit skipped (unknown CPT G0439); Working Denials queue 0; board drops 0; no William note since the last run; Pam Gmail: nothing in 2 days. ERA Center 2 checks $146.78 -> 0: Medicare 00149732354 (1053544) - Post button $45.20, then 5 secondary OA-23 lines ($101.58, charts 17477557 x4 / 17477974) moved back from the patient balance and posted ERA-linked; Medicare $0 check 350213184 (1053545) recorded + dismissed. Columns 0/1/0/1 -> 0/1/0/1 (inspector chart 17478413 O24.419 hold; AET12 hold)."}]}},
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
