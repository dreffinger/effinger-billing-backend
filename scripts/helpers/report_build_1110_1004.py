# PLAIN ENGLISH (run report builder, 10/4/2026 7 AM ET slot = 1110Z, ehpa cloud)
# Decides: nothing. Writes this run's ERA register entries, the run report CSV, the needs_facesheet_list.md section, the board
# update file and the captured-calls additions file from the scan summaries + the act log. Never touches AMD.
import json, csv, datetime, os
STAMP="2026-10-04T1110Z"; SLOT="7 AM ET 10/4"; NOW=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); ISO=NOW
b=json.load(open("scan_%s/summary_before.json"%STAMP)); a=json.load(open("scan_%s/summary_after.json"%STAMP))
def cnt(s): o=s["overview"]; return "%s/%s/%s/%s"%(o["chargereviewcount"],o["claiminspectorcount"],o["unbillablecount"],o["exclusioncount"])
# --- 1. ERA register
reg=json.load(open("registers/era_manual_register.json"))
have={(str(r.get("checkid")),str(r.get("visitid")),str(r.get("chargedetailid"))) for r in reg}
lines=[("19454281","23365353","99233","wocaid2nd 21.80"),("19454311","23365384","99233","wocaid2nd 21.80"),("19454438","23365526","99233","wocaid2nd 21.80"),("19454458","23365546","99233","wocaid2nd 21.80"),
       ("19456182","23367806","99308","cob-rerouted Medicare seq 4 freq1 204"),("19456209","23367833","99309","cob-rerouted Medicare seq 1 freq1 204"),
       ("19454394","23365482","99309","denial-held M56 cluster"),("19454409","23365497","99309","denial-held M56 cluster"),("19454393","23365481","99309","denial-held M56 cluster"),("19454414","23365502","99309","denial-held M56 cluster"),("19456313","23367947","99309","denial-held M56 cluster (primary)"),
       ("19455292","23366503","99306","denial-william CO-222/N640 frequency"),("19455291","23366500","99316","already-settled CO-18 $0"),("19448638","23357944","99223","already-settled CO-18 $0")]
for vid,cid,cpt,out in lines:
    if ("1052960",vid,cid) in have: continue
    reg.append({"checkid":"1052960","checknumber":"X319720720","visitid":vid,"chargedetailid":cid,"cpt":cpt,"outcome":out,"pay":0.0,"when":STAMP})
json.dump(reg,open("registers/era_manual_register.json","w"),indent=0)
# --- 2. report CSV
HOLD={"17472874":"HOLD - William: April 2026 admission date for the Thackeray stay (no 99223 anchor in the 45-day window); 15 visits",
      "17477972":"HOLD - William: admission date (no 99223 on the chart); 4 visits (row herring)",
      "20863":"HOLD - William: coding choice 99233 vs 99306 same day (CCI Pattern 24078)",
      "17477898":"HOLD - William: CHP member id (row will)","17477973":"HOLD - William: CHP member id (row zane)",
      "17477946":"HOLD - William: TRICARE referral/auth number from the admission facesheet (row christensen)"}
rows=[]
for bid,vs in a["inspector"].items():
    for v in vs:
        dos=""
        for u in a["unbilled"]:
            if u["id"]==v["vid"] and u.get("_chgs"): dos=u["_chgs"][0].get("dos","").strip()
        rows.append(["Claim Inspector","remaining",v["name"],dos,"",v["errs"][0][1][:90] if v["errs"] else "",HOLD.get(v["pid"],"hold")])
for u in a["unbilled"]:
    dos=(u["_chgs"][0].get("dos","").strip() if u.get("_chgs") else "")
    rows.append(["Unbilled","remaining",u["patientname"],dos,u.get("carriercode",""),"; ".join(u["_errs"]),HOLD.get(u["patientid"],"hold")])
era=[["ERA","cleared","check 1052960 SUNSHINE HEALTH X319720720 ($0 denial remit, 14 lines)","","SUN01","dismissed after every line was handled","see lines below"],
 ["ERA","written off","WINSLOW JR,ERWIN v19454311 99233","09/09/2026","SUN01","$0 OA-23/CO-45 on the Medicaid-MMA secondary (Medicare paid 138.20)","WOCAID2ND $21.80 check X319720720"],
 ["ERA","written off","WINSLOW JR,ERWIN v19454281 99233","09/10/2026","SUN01","same","WOCAID2ND $21.80"],
 ["ERA","written off","WINSLOW JR,ERWIN v19454458 99233","09/11/2026","SUN01","same","WOCAID2ND $21.80"],
 ["ERA","written off","WINSLOW JR,ERWIN v19454438 99233","09/12/2026","SUN01","same","WOCAID2ND $21.80"],
 ["ERA","re-routed","[name] v19456182 99308 $107","09/21/2026","SUN01 -> FLO02","CO-22 other payer primary; AMD 271 Medicare ACTIVE, Sunshine names Medicare A/B","patient order 4,5; visit insorder 4,5; freq-1 rebill seq 4 -> 204"],
 ["ERA","re-routed","PEARCE,KARINA v19456209 99309 $141","09/24/2026","SUN01 -> FLO02","CO-22 other payer primary; AMD 271 Medicare ACTIVE (QMB)","patient order 1,2; visit insorder 1,2; freq-1 rebill seq 1 -> 204"],
 ["ERA","held","WALCOTT,LENOX v19455292 99306 $256","07/13/2026","SUN01","CO-222 / N640 frequency exceeded (99497 CO-96 N448 already WONCS)","WILLIAM: appeal with the H&P / medical-necessity letter, or write off (row walcott-lenox-denials)"],
 ["ERA","held","M56 cluster: ROSSITER v19454394 $16.93, RAUGHLEY v19454409 $16.93, SAYER v19454393 $16.93, HEULER v19454414 $16.93, DALLOWAY v19456313 $141 (primary)","09/02-09/24/2026","SUN01","CO-16 / M56 missing payer identifier","held on row centene-m56-denials-0920 (SUN01 carrier payer id - William)"],
 ["ERA","settled","JACOBSEN,NORCOTT v19455291 99316 / WALCOTT,LENOX v19448638 99223","06/23 + 07/16/2026","SUN01","CO-18 duplicate, charges already at $0","nothing to do"],
 ["ERA","remaining","(check 1052906 Florida Blue, 17 claim lines)","","FLO BLUE","unposted $104.19 - OA-23 takeback pair pat17476868 + pat17475906","HOLD - William's takeback decision (no takeback posting rule)"]]
with open("_run report 10-04 1110.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["column","status","patient","dos","carrier","error","action"]); w.writerows(rows+era)
    w.writerow(["Charge Review","summary","0 -> 0","","","",""]); w.writerow(["Claim Inspector","summary","20 -> 20","","","","all standing holds"])
    w.writerow(["Unbilled","summary","21 -> 21","","","","all standing holds"]); w.writerow(["Exclusions","summary","0 -> 0","","","","newest claim run 1700250"])
    w.writerow(["ERA","summary","2 checks $104.19 unposted -> 1 check $104.19","","","","auto-posted $0, manual-posted $0, write-offs WOCAID2ND $87.20 (4 lines), 2 visits re-routed to Medicare ($248), residuals $0, cleared 1 (1052960)"])
# --- 3. needs section
sec="""
## %s - %s backend billing run (ehpa cloud): columns %s -> %s; ERA 2 checks $104.19 unposted -> 1 check $104.19 (1052906 held); new Sunshine $0 remit 1052960 worked and dismissed
- Bootstrap: repo attached (main 4eedf54), net AMD_OK / STEDI_CRED_OK, AMD_PSW env credential, no login lock, guard clear, START 11:12Z. State bundle on Drive (9/18) older than main - not unpacked. pseudonyms.json 05:47Z copy (379 names). Missing optional helpers: era_details_pull.py, columns_inspector2_0908.py, working_denials.py, github_sync.py. GitHub inbox: no unapplied package. Approvals pending: none; Gmail: no new APPROVED/NO reply; Working Denials queue 0; board drops 0; board rows changed after 08:00Z: 0.
- Sources: facesheet folders nothing after IMG_8921.jpeg (03:06Z, worked 0310Z/0510Z); 'bht Optum era downloads' / 'treasury payments' nothing new; Pam Gmail nothing newer than the 10/2 BUTTERMERE re-send.
- Charge Review 0 -> 0 | Claim Inspector 20 -> 20 (pat17472874 x15 + pat17477972 x4 'Hospitalization From Date empty' - admission dates, William; pat20863 CCI 24078 - coding choice, William) | Unbilled 21 -> 21 (pat17472874 x15 behind the inspector; pat17477898 x2 + pat17477973 x3 'Insurance order is missing' - CHP member ids; pat17477946 TRICARE auth) | Exclusions 0 -> 0 (newest claim run 1700250).
- ERA (step 5): (a) nothing new to upload; (b) before = 2 checks: 1052906 Florida Blue $104.19 unposted (takeback pair, HELD for William) + NEW 1052960 SUNSHINE HEALTH X319720720 (received 03:50Z, $0 denial remit, 14 claim lines, deposit date 10/05/2026) - details cached era_details/1052960.json; (c) nothing postable (no money line anywhere in the Center) - era_post --all-unposted not run; (d) the 14 lines of 1052960 worked from the live charts: 4 x OA-23/CO-45 $0 on pat17472546 99233 9/9-9/12 (Medicare paid 138.20 each, Sunshine is the Medicaid-MMA secondary) -> WOCAID2ND $21.80 x4 = $87.20 (pay 0, check X319720720, pay24658275-78); 2 x CO-22 'other payer primary' on visits billed to Sunshine FIRST although Medicare is ACTIVE on the chart (AMD 271 this run) -> pat17472429 v19456182 99308 $107: patient order 4,5, visit insorder 4,5, freq-1 rebill seq 4 (204); pat20670 v19456209 99309 $141: patient order 1,2, visit insorder 1,2, freq-1 rebill seq 1 (204) - the freq1 helper's own rebill answered 500 before the insorder was set, move_to_ins's rebill after it answered 204 (same pattern as 9/23); 5 x CO-16/M56 (pat20729 v19454394, pat17473346 v19454409, pat17472286 v19454393, pat17471131 v19454414 - $16.93 coinsurance residuals - and pat17469541 v19456313 99309 9/24 $141 PRIMARY) -> held on the centene-m56 board row (SUN01 carrier payer id, William); 1 x CO-222/N640 frequency-exceeded on pat17471755 v19455292 99306 7/13 $256 (its 99497 CO-96/N448 was already WONCS) -> William's decision on the walker row; 2 x CO-18 duplicate (pat17469007 v19455291, pat17471755 v19448638) already at $0. (e) 1052960 dismissed (issuccess true); GET /api/era/checks after = [1052906]. (f) no new call shapes. (g) Availity / Treasury: nothing new.
- Writes this run (all accepted, none refused): 4 addpayments (WOCAID2ND), 2 updateinsurance (patient order), 2 updextrainsinfo freq-1 + 2 updvisitwithcharges (insorder) + 2 chargerebill (204), 1 ERA dismiss. Dollars re-sent: $248 (2 visits to Medicare). Write-offs: $87.20 WOCAID2ND. Auto-posted $0. Manual-posted $0. Residuals $0. Checks cleared 1.
- Board update file: board_updates_%s.json (7 ops). Denials queue empty (no file). Board inbox: none of the current inbox files is in the page's applied map - nothing trashed.
- Waiting on William (unchanged + 1): the 1052906 takeback decision ($104.19); the pat17471755 99306 7/13 CO-222 frequency denial (appeal or write off); Thackeray April admission date (15 visits); Herriot admission date (4 visits); Hatherley 99233/99306 coding; CHP member ids (Willoughby, Zane); Christensen TRICARE auth; SUN01 carrier payer id (M56 cluster, now 18 lines); Lazenby + duplicate-chart merge HAR captures; Carmody new MBI; Levin StudentResources carrier; AARP supplement numbers (Hodgson, Poulter-Ellery); paper-EOB 22 held lines; MacAllister UHC F2 decision; Rustin CHAMPVA paper; Whitlow trust invoice; Medicaid FFS 460-line re-render.
""" % (STAMP, SLOT, cnt(b), cnt(a), STAMP)
open("needs_facesheet_list.md","a").write(sec); open("needs_facesheet_list_section_%s.md"%STAMP,"w").write(sec)
# --- 4. board update file
SRC="%s columns run (ehpa cloud) - run %s"%(SLOT,STAMP); WHEN="10/4"
def chk(ok,res): return {"ok":ok,"src":SRC,"result":res,"when":WHEN}
def note(t): return {"who":"Claude","text":t,"at":ISO}
ops=[
 {"op":"upsert","collection":"items","id":"winslow-jr-erwin","append":{"checks":[chk("ok","Sunshine (Medicaid MMA secondary) answered $0 OA-23/CO-45 on the four 9/9-9/12/2026 99233s (ERA 1052960, trace X319720720) after Medicare paid 138.20 each - the 21.80 coinsurance residuals written off WOCAID2ND (4 x $21.80 = $87.20), balances $0, nothing on the patient.")]}},
 {"op":"upsert","collection":"items","id":"vaughan-sheree","append":{"checks":[chk("ok","Sunshine answered CO-22 'other payer primary' on the 9/21/2026 99308 ($107, v19456182) - it had gone to Sunshine FIRST because the chart's default order was Sunshine alone (seq 5). AMD 271: Medicare ins9519143 ACTIVE (A/B since 2007), Sunshine ACTIVE as the secondary naming Medicare. Patient order set 4,5 (Medicare, Sunshine), visit insorder 4,5, freq-1 rebilled to Medicare seq 4 (204).")],"notes":[note("9/21 visit re-routed Medicare first; the chart default order now bills Medicare before Sunshine on its own.")]}},
 {"op":"upsert","collection":"items","id":"pearce-karina-20670","append":{"checks":[chk("ok","Sunshine answered CO-22 'other payer primary' on the 9/24/2026 99309 ($141, v19456209, ERA 1052960) - the chart's default order was Sunshine alone (seq 2) although Medicare ins6406 is ACTIVE (QMB; AMD 271 this run). Patient order set 1,2 (Medicare, Sunshine), visit insorder 1,2, freq-1 rebilled to Medicare seq 1 (204). Sunshine follows as the crossover.")],"notes":[note("The 9/24 visit went to Sunshine first by mistake of chart order - sent to Medicare tonight; nothing needed from you.")]}},
 {"op":"upsert","collection":"items","id":"walcott-lenox-denials","set":{"status":"william","need":"WILLIAM: Sunshine adjudicated the 7/13/2026 99306 ($256, v19455292) on remit X319720720 (10/4): CO-222 / N640 'exceeds the number/frequency approved or allowed within the time period' - a frequency denial, not coverage (the 99497 on the same visit was CO-96/N448 and is already written off WONCS). Say 'appeal' (needs the H&P / a medical-necessity note showing why a second initial NF visit in the period was warranted - or whether it should have been a 99309 subsequent visit, in which case say 'recode 99309' and the run rebills it frequency 7 with Sunshine's claim number) or 'write off' (WONCS). Nothing re-sent."},"append":{"checks":[chk("human","7/13/2026 99306 $256 denied CO-222/N640 frequency exceeded (ERA 1052960) - appeal, recode 99309, or write off?")],"notes":[note("Sunshine's answer to the 7/13 99306 is in: frequency exceeded (CO-222/N640). Your call - appeal with records, recode to 99309 and resend as a corrected claim, or write off.")]}},
 {"op":"upsert","collection":"items","id":"centene-m56-denials-0920","append":{"checks":[chk("no","Sunshine remit X319720720 (ERA 1052960, 10/4) answered FIVE more CO-16/M56 lines: four Medicare-coinsurance residuals billed to the Sunshine secondary - pat20729 v19454394 99309 9/3 $16.93, pat17473346 v19454409 99309 9/2 $16.93, pat17472286 v19454393 99309 9/3 $16.93, pat17471131 v19454414 99309 9/2 $16.93 (that one last billed to CHP) - and one PRIMARY Sunshine claim, pat17469541 v19456313 99309 9/24/2026 $141. Cluster now 18 lines / ~$1,112. Held - same SUN01 carrier payer-id question; nothing re-sent or written off.")],"notes":[note("Five more M56 lines on the 10/4 Sunshine remit, one of them a primary claim - the SUN01 carrier record's payer id is still the blocker.")]}},
 {"op":"upsert","collection":"items","id":"dalloway-fred-denials","append":{"checks":[chk("no","Sunshine answered CO-16/M56 'missing/invalid payer identifier' on the 9/24/2026 99309 ($141, v19456313, ERA 1052960) - a PRIMARY Sunshine claim, chart plan SUN01 7933384234 ACTIVE on AMD's 271. Held with the centene-m56-denials-0920 cluster (SUN01 carrier payer id - William); nothing re-sent.")]}},
 {"op":"upsert","collection":"items","id":"availity-remits-backlog","append":{"checks":[chk("na","7 AM ET 10/4: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified since 10/2); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; 0 rows changed since 08:00Z; Pam Gmail: nothing newer than the 10/2 23:11Z BUTTERMERE re-send. ERA Center 2 checks $104.19 -> 1 check $104.19: new Sunshine $0 remit 1052960 (14 lines) worked - 4 WOCAID2ND, 2 CO-22 visits re-routed Medicare first, 5 M56 lines to the cluster, 1 CO-222 line to William - and dismissed; 1052906 held. Columns 0/20/21/0 -> 0/20/21/0.")]}},
]
json.dump({"schema":"irb-board-updates/1","source":"backend billing run %s"%STAMP,"created":ISO,"ops":ops},open("board_updates_%s.json"%STAMP,"w"),indent=1)
# --- 5. additions file
add="""# captured_calls additions - 2026-10-04 1110 UTC (7 AM ET 10/4 backend billing run, ehpa cloud)

No new AMD or Stedi call shapes this run. Calls exercised (all already in the registry): login_cached (one login), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimrunstatus/getclaimexclusioncharges, getdemographic, gettxhistory, checkEligibility (free 271, 6 plans on 3 charts), GET /api/era/checks, GET /api/era/checkdetails, addpayments (manual_post pay 0 + WOCAID2ND, 4 lines), updateinsurance (patient order via sequence=, 2 charts), updextrainsinfo freq 1 + updvisitwithcharges insorder + POST /api/claim/chargerebill (2 visits), POST /api/era/checks/dismiss (1052960).

Observations (not new shapes):
- ERA check 1052960 (SUNSHINE HEALTH, trace X319720720, deposit date 10/05/2026 - a day in the FUTURE at run time) arrived in the Center 03:50Z 10/4 as a pure $0 denial remit: paymentamount 0 on every line, systemcarriercode mapped to FLO02 (6085) although the ERA carrier is Sunshine; line carrierid 6194 on 12 lines, 6085 on 1, 41826 on 1 - the carrier id on an ERA line is the carrier the claim was last billed to, not the remitting payer.
- addpayments with pay 0.00 + WOCAID2ND and a future-dated depositdate (10/05/2026) was accepted (success=1, paymentid 10165648-51); the write-off shows on the charge as a PE payment of 0.00 carrying the trace number.
- freq1_visit.run's chargerebill answers HTTP 500 while the visit insorder does not yet contain the target sequence; move_to_ins.move(cid, order, rebill_seq=N) right after it (sets insorder, rebills) answers 204 - the 9/23 pattern, confirmed on pat17472429 / pat20670. Order of operations for a CO-22 re-route: updateinsurance sequence=<order> (patient default) -> freq1_visit.run (extins freq 1) -> move_to_ins.move(cid, order, rebill_seq=first).
- Dismissing a $0 denial check whose every line is handled: POST /api/era/checks/dismiss body "1052960" -> {"issuccess":true,"id":1052960,"actionname":1}; the check left GET /api/era/checks at once.
"""
open("captured_calls_additions_2026-10-04_1110UTC-7amET-ehpa-cloud.md","w").write(add)
print("built: register +%d, csv rows %d, board ops %d"%(len(lines),len(rows)+len(era),len(ops)))
