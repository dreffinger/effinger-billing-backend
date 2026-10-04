# PLAIN ENGLISH (run report builder, 10/4/2026 5 AM ET slot = 0910Z, ehpa cloud)
# Decides: nothing. Reads this run's scan summaries + the ERA Center read and writes the run report CSV, the
# needs_facesheet_list.md section, the board update file, the additions file and the digest. Never touches AMD.
import json, csv, datetime, os
STAMP="2026-10-04T0910Z"; SLOT="5 AM ET 10/4"; NOW=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
b=json.load(open("scan_%s/summary_before.json"%STAMP)); a=json.load(open("scan_%s/summary_after.json"%STAMP))
def cnt(s): o=s["overview"]; return "%s/%s/%s/%s"%(o["chargereviewcount"],o["claiminspectorcount"],o["unbillablecount"],o["exclusioncount"])
HOLD={"17472874":"HOLD - William: April 2026 admission date for the Thackeray stay (no 99223 anchor in the 45-day window); 15 visits",
      "17477972":"HOLD - William: admission date (no 99223 on the chart); 4 visits (row herring)",
      "20863":"HOLD - William: coding choice 99233 vs 99306 same day (CCI Pattern 24078)",
      "17477898":"HOLD - William: CHP member id (row will)","17477973":"HOLD - William: CHP member id (row zane)",
      "17477946":"HOLD - William: TRICARE referral/auth number from the admission facesheet (row christensen)"}
rows=[]
for bid,vs in a["inspector"].items():
    for v in vs:
        dos=""; 
        for u in a["unbilled"]:
            if u["id"]==v["vid"] and u.get("_chgs"): dos=u["_chgs"][0].get("dos","").strip()
        rows.append(["Claim Inspector","remaining",v["name"],dos,"",v["errs"][0][1][:90] if v["errs"] else "",HOLD.get(v["pid"],"hold")])
for u in a["unbilled"]:
    dos=(u["_chgs"][0].get("dos","").strip() if u.get("_chgs") else "")
    rows.append(["Unbilled","remaining",u["patientname"],dos,u.get("carriercode",""),"; ".join(u["_errs"]),HOLD.get(u["patientid"],"hold")])
rows.append(["ERA","remaining","(check 1052906 Florida Blue, 17 claim lines)","","FLO BLUE","unposted $104.19 - OA-23 takeback pair pat17476868 + pat17475906","HOLD - William's takeback decision (no takeback posting rule)"])
with open("_run report 10-04 0910.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["column","status","patient","dos","carrier","error","action"]); w.writerows(rows)
    w.writerow(["Charge Review","summary","0 -> 0","","","",""]); w.writerow(["Claim Inspector","summary","20 -> 20","","","","all standing holds"])
    w.writerow(["Unbilled","summary","21 -> 21","","","","all standing holds"]); w.writerow(["Exclusions","summary","0 -> 0","","","","newest claim run 1700250"])
    w.writerow(["ERA","summary","1 check $104.19 -> 1 check $104.19","","","","auto-posted $0, manual-posted $0, residuals $0, cleared 0"])
sec="""
## %s - %s backend billing run (ehpa cloud): columns %s -> %s; ERA 1 check $104.19 -> 1 check $104.19 (held); no AMD writes
- Bootstrap: repo ATTACHED (origin/main d1d0ff9 at start; main checked out and symlinked as /home/claude/effinger-billing-backend; layout 785 helper files); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no file); no login lock; guard clear (the 0710Z START has its RUN COMPLETE digest; no START younger than 40 min); START marker 09:13Z; lock written. State bundle on Drive (9/18) older than main - not unpacked (patient_db / era_details start empty, 1052906 re-cached from the Center). secrets/pseudonyms.json (379 names, Drive 05:47Z copy) restored to both secrets/. Missing optional helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py, working_denials.py, github_sync.py.
- GITHUB INBOX: no unapplied PACKAGE_*.manifest.json in Drive 'github mirror' (10/4 and both 9/23 packages read APPLIED_). Nothing to apply.
- APPROVALS: register showed A-2026-10-04T0510Z-A1 / -A2 still 'waiting' although the 0710Z run verified every item live (done by the 02:00-06:00Z chat session) - both closed 'done' in registers/approvals_pending.json this run with that note. Gmail: no new APPROVED/NO reply after the 03:08Z 'APPROVED A-2026-10-03T2110Z-A1' (already consumed by the 0510Z run). No refusals this run (no writes attempted).
- ONE AMD login 09:16Z. Reads only: scan before/after (columns_scan.py), GET /api/era/checks + checkdetails 1052906. WRITES: none - every row on every column is a standing hold on William's turn, nothing new arrived.
- Charge Review 0 -> 0 | Claim Inspector 20 -> 20 (pat17472874 x15 'Hospitalization From Date empty' - April admission date, William; pat17477972 x4 same hold, no 99223 on the chart - William; pat20863 CCI Pattern 24078 99233 vs 99306 same day - William's coding choice) | Unbilled 21 -> 21 (pat17472874 x15 behind the inspector + WEL04 'DOS outside coverage effective dates' on 11 of them; pat17477898 x2 + pat17477973 x3 'Insurance order is missing' - CHP member ids; pat17477946 'Insurance order is missing' - TRICARE auth) | Exclusions 0 -> 0 (newest claim run 1700250; 89 runs).
- ERA (step 5): (a) no new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' or 'treasury payments' (nothing modified there since 10/2); locks not released (nothing to post). (b) before = 1 check / $104.19 unposted: 1052906 Florida Blue (17 claim lines, the OA-23 takeback pair on pat17476868 + pat17475906) - HELD for William's takeback decision (no takeback posting rule); checkdetails re-cached era_details/1052906.json. (c)/(d) nothing postable. (e) nothing to clear; after = 1 check / $104.19. (f) no new call shapes. (g) Availity / Treasury: nothing new.
- Sources: Working Denials queue 0; board drops 0; board rows changed after 06:00Z: 0; facesheet folders (hca / tmh / PCC / Claimocity / the 10/4 chat folder): nothing after addison.pdf x2 (02:33Z) and IMG_8921.jpeg (03:06Z), both worked by the 0310Z/0510Z runs and the chat; Pam Gmail (2d): nothing newer than the 10/2 BUTTERMERE re-send. 9/30 admits THORNEY / TRENT / HARLOW / WILBOURNE still without an AMD chart.
- Board update file: board_updates_%s.json (1 op: slot check on availity-remits-backlog). Denials queue empty (no file). Board inbox: none of the 5 current files is in the page's applied map - nothing trashed. Write-offs: none. Dollars re-sent: $0. Auto-posted $0. Manual-posted $0. Residuals $0. Checks cleared 0.
- Waiting on William (unchanged): the 1052906 takeback decision ($104.19); Thackeray April admission date (15 visits); Herriot admission date (4 visits); Hatherley 99233/99306 coding; CHP member ids (Willoughby, Zane); Christensen TRICARE auth; Lazenby + duplicate-chart merge: one HAR capture each; Carmody new MBI; Levin StudentResources carrier; AARP supplement numbers (Hodgson, Poulter-Ellery); paper-EOB 22 held lines; MacAllister UHC F2; Rustin CHAMPVA paper; Whitlow trust invoice; Medicaid FFS 460-line re-render (dedicated session).
""" % (STAMP, SLOT, cnt(b), cnt(a), STAMP)
open("needs_facesheet_list.md","a").write(sec); open("needs_facesheet_list_section_%s.md"%STAMP,"w").write(sec)
add="""# captured_calls additions - 2026-10-04 09:10 UTC (5 AM ET 10/4) backend billing run, ehpa cloud

No new call shapes this run. Behaviours recorded:
- Read-only run: columns 0/20/21/0 -> 0/20/21/0 and ERA Center 1 check ($104.19, 1052906 held) unchanged since the 0710Z run; no AMD write was needed, so nothing was attempted and nothing was refused.
- registers/approvals_pending.json still carried A-2026-10-04T0510Z-A1 / -A2 as 'waiting' although the 0710Z digest recorded them closed - the 0710Z register write did not reach main; closed 'done' this run (approval_request.py done <id> --note ...). Lesson: run `approval_request.py pending` after `done` and commit the register in the same mirror commit.
- GitHub inbox: the Drive 'github mirror' listing by `title contains 'manifest'` is the quick check - every manifest read APPLIED_/SUPERSEDED_, so nothing to apply.
"""
open("captured_calls_additions_2026-10-04_0910UTC-5amET-ehpa-cloud.md","w").write(add)
bu={"schema":"irb-board-updates/1","source":"backend billing run %s"%STAMP,"created":NOW,"ops":[{"op":"upsert","collection":"items","id":"availity-remits-backlog","set":{},
  "append":{"checks":[{"ok":"na","src":"5am ET 10/4 columns run (ehpa cloud) - run %s"%STAMP,"when":"10/4",
  "result":"5 AM ET 10/4: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 10/2); no new 835, facesheet or Claimocity file after the 02:33-03:06Z chat drops (worked); Working Denials queue 0; board drops 0; 0 rows changed since 06:00Z; Pam Gmail: nothing newer than the 10/2 BUTTERMERE re-send. ERA Center 1 check $104.19 before and after (1052906 Florida Blue takeback pair, held for you). Columns 0/20/21/0 -> 0/20/21/0 - every row a standing hold, no AMD writes this slot."}]}}]}
json.dump(bu,open("board_updates_%s.json"%STAMP,"w"),indent=1)
print(cnt(b),"->",cnt(a), len(rows),"report rows")
