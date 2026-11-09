#!/usr/bin/env python3
# PLAIN ENGLISH (board inbox file for the 1:39 AM ET 11/9 columns run, 06:39Z): builds board_updates_2026-11-09T0639Z.json through
#   board_ops.clean_file - append-only checks/notes on the standing rows, and the answer on the chart-17478346 row (insurance and
#   DOB from William's HCA facesheet drop; nothing for him). No `updated` in any set; no status/need/why change on a row William
#   answered since this run read the board. Reads the engine report for the column counts. Writes nothing to AMD or the board.
import json, sys, datetime
sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-09T0639Z"; NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/9"
SRC = "1:39am ET 11/9 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
eng = json.load(open("/home/claude/effinger-billing-backend/reports/button/%s-engine.json" % STAMP))
c = eng["summary"]["columns"]; era = eng["summary"]["era"]
cols = "Columns 0/4/3/14 -> 0/2/0/1 (engine pass, then by hand: chart-17478346 admission dates, three MSP rows re-pointed to UHC Dual Complete, 13 Florida Blue PREF0283 crossover secondaries completed)"
eraline = "ERA Center %s checks $%.2f -> %s checks $%.2f" % (era["before"]["checks"], era["before"]["unposted"], era["after"]["checks"], era["after"]["unposted"])
ops = []
def chk(rid, result, ok="na"):
    ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": WHEN}]}})
chk("aet12-carrier-cpid", "1:39 AM ET 11/9: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged.")
chk("availity-remits-backlog", "1:39 AM ET 11/9: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide after 01:05Z only your HCA facesheet drop frobel.pdf 05:43Z, a Barclay 11/5 progress note and a WorldStrides form in the PCC folder - no remit); no new 835 or Claimocity file (gcs 21 objects, 0 new, newest 20261108); Working Denials queue 0; board drops 0; Pam Gmail: the 11/8 Huntley Jr thread only (worked). %s (engine pass). %s. The facesheet insured chart 17478346 (see its row); every other row a standing hold." % (eraline, cols))
chk("hunter-edwin-jr-admit-1104", "1:39 AM ET 11/9: lookuppatient HUNTLEY,[first]% still returns only the 1971 namesake (pat45499) - the 03/17/1943 admit has no AMD chart yet; nothing to bill.")
chk("hawksworth-davin-admit-1107", "1:39 AM ET 11/9: lookuppatient HAWKSWORTH,[first]% still returns only the 1961 namesake (pat17476928) - the 08/31/1944 admit has no AMD chart yet; nothing to bill.")
ops.append({"op": "upsert", "collection": "items", "id": "frobel-delwyn-17478346", "set": {
    "dob": "[DOB]", "inscarrier": "AET07 Aetna Medicare Advantage (SEHBP Educators Medicare Plan, PPO)", "insid": "[member id]",
    "insplans": "1st AET07 Aetna Medicare Advantage 101319122800 (begin 10/01/2026, no group number); AMD 271 ACTIVE 1/1-12/31/2026",
    "need": "None - insured and released from your HCA facesheet (frobel.pdf, 05:43Z 11/9): primary AETNA MCR = Aetna Medicare Advantage, SEHBP Educators Medicare Plan (State of New Jersey retiree PPO), policy [member id] effective 10/01/2026, hospital auth 261005656301 (the value before the slash; written on the chart's referral plan), DOB [DOB] (the feed had entered 1929 - corrected). AET07 plan added (no group number), patient order Aetna alone, both HCA visits (99223 11/6 v19460523, 99232 11/7 v19460531) resaved full-echo with insorder 1 + onhcfa=1, AMD 271 ACTIVE (plan 1/1-12/31/2026, PR), released from Unbilled - they leave on the next claim run. Admission date 11/06/2026 is written by the inspector pass.",
    "status": "claude"},
    "append": {"notes": [{"who": "Claude", "text": "Your facesheet did it: Aetna Medicare Advantage (NJ SEHBP Educators plan) from 10/1/2026, DOB corrected to 1949, both hospital visits insured and released - nothing more needed from you.", "at": NOW}],
               "checks": [{"ok": "ok", "src": "HCA facesheet (Drive bht hca facesheets, frobel.pdf, OCR) - run %s" % STAMP, "result": "AETNA MCR policy [member id] eff 10/01/26, group State of New Jersey (not entered), auth 261005656301/27447, DOB [DOB] age 77, financial class MANAGED CARE MEDICARE", "when": WHEN},
                          {"ok": "ok", "src": "AMD action: patient_patch dob [DOB]; add_ins car6047 -> ins9521193 seq 1; ins_update sequence 1; full-visit resave x2 (insorder 1, preauth, onhcfa=1); hideunbillablevisits x2", "result": "DOB read back [DOB]; plan added; visits 19460523 / 19460531 saved 1/1 live charges each, auth on rplan18462709; released", "when": WHEN},
                          {"ok": "ok", "src": "AMD eligibility (free 271) - AET07 ins9521193", "result": "ACTIVE - Aetna Inc, SEHBP Educators Medicare Plan, PR, benefit 20260101-20261231, no AAA", "when": WHEN}]}})

chk("waldron-marthe-17477267", "1:39 AM ET 11/9: as this row foresaw, the 13 Medigap secondaries re-sent 11/8 bounced at the clearinghouse on claim run 1700365 - CH FH PREF0283 MISSING PAYER DOC CONTROL NUM (the Medicare ICN the Medigap loop wants). Completed under the crossover-wait rule, not re-sent (Medicare paid every line 9/11 and 10/2, checks 819766146 / 819900020); the $809.20 coinsurance stays open on BCBS seq 2 for Medicare's Medigap crossover. If Florida Blue never answers it is your call (estate statement or write-off) - nothing to do now.")
chk("[name]-25558", "1:39 AM ET 11/9: the 11/4/2026 99309 from the 11/8 feed (v19460510, $141) came in Medicare first ('1,4' - Unbilled 'MSP code required'); Medicare's 271 again names Care Improvement Plus / UHC Dual Complete and the UHCMA plan answers ACTIVE, so the visit order is now UHCMA alone (4) and the chart's default order 2,3,1,4 (Magellan AAA 72, WellCare INACTIVE first) is now 4. Released - goes to UHC Dual Complete on the next claim run.", ok="ok")
sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
from board_ops import plan_new_row
items = json.load(open("board_items_inline.json")) if False else []
new = {"id": "[name]-21020", "patient": "[name]", "dob": "[DOB]", "facility": "SNF (99309 11/4/2026 + 10/5/2026, fac32)", "amdid": "21020", "mbi": "",
       "inscarrier": "UHCMA UnitedHealthcare Dual Complete SNP (Full Medicaid)", "insid": "[member id]",
       "insplans": "1st FLO02 Medicare [MBI] (MA member - not billed) · 2nd STA03 Staywell (INACTIVE) · 3rd UHCMA UnitedHealthcare Dual Complete 123135253 (ACTIVE) · 4th UNI20 123142401 (ACTIVE, same Dual Complete SNP); chart order 3,4",
       "need": "None - fixed. Two 99309 visits from the 11/8 Claimocity file (11/4/2026 v19460514, 10/5/2026 v19460515, $141 each) came in Medicare first with UHC Dual Complete behind it and sat in Unbilled ('MSP code required'). Medicare's own 271 names Care Improvement Plus South Central (H1889 = UnitedHealthcare Dual Complete) as her Advantage plan and the chart's UHCMA plan answers ACTIVE, so each visit's order is now the UHCMA plan (3) and both were released - they go to UHC Dual Complete on the next claim run. Chart default order 3,4 unchanged.",
       "why": "Unbilled 11/9: 'When billing Medicare as the non-primary carrier, the MSP Code is required' on two feed visits of an MA member", "status": "claude", "amount": 282,
       "notes": [{"who": "Claude", "text": "Created by the 1:39 AM ET 11/9 run - fixed from the chart's own eligibility, nothing for you.", "at": NOW}],
       "checks": [{"ok": "ok", "src": "AMD eligibility (free 271) - elig_amd --all, run %s" % STAMP, "result": "FLO02 ACTIVE but other payer PR H1889 CARE IMPROVEMENT PLUS SOUTH CENTRAL (UHC Dual Complete); STA03 INACTIVE; UHCMA 123135253 ACTIVE; UNI20 123142401 ACTIVE (FL UHC Dual Complete SNP Full Medicaid)", "when": WHEN},
                  {"ok": "ok", "src": "AMD action: resave.set_insorder x2 (full-visit echo) + hideunbillablevisits", "result": "v19460514 / v19460515 insorder 1,3 -> 3, 1 live charge each; released", "when": WHEN}]}
ops.extend(plan_new_row(items, new, same_item=False, now=NOW))

doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
json.dump(doc, open("board_updates_%s.json" % STAMP, "w"), indent=1)
print("board_updates_%s.json: %d ops" % (STAMP, len(doc["ops"])))
