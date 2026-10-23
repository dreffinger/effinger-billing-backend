#!/usr/bin/env python3
# PLAIN ENGLISH (report pieces of the 3 AM ET 10/22/2026 backend billing run, stamp 2026-10-22T0640Z): LOCAL ONLY, no AMD call.
# Decides: nothing. Reads this run's scan folder (scan_2026-10-22T0650Z: before / after / after2 summaries + the raw XML) and
#   writes the four report pieces the prompt asks for: the run report CSV (names allowed - it goes to William by SendUserFile),
#   the needs_facesheet_list.md section (chart ids only), the board update file for the 'board inbox' (real board row ids),
#   and the captured_calls additions file (0 new shapes this run). Never touches AMD, never prints a member id.
# Usage: python3 run_outputs_1022_0640.py
import json, re, csv, os, datetime
STAMP = "2026-10-22T0640Z"; SLOT = "3 AM ET 10/22"; SCAN = "scan_2026-10-22T0650Z"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
os.makedirs("outbox", exist_ok=True); os.makedirs("chat_history", exist_ok=True)

def attrs(tag):
    return dict(re.findall(r'(\w+)="([^"]*)"', tag))

def visits(xml):
    out = []
    for m in re.finditer(r'<visit (.*?)>(.*?)</visit>', xml, re.S):
        v = attrs("<visit " + m.group(1) + ">"); body = m.group(2)
        v["_errs"] = [attrs(e) for e in re.findall(r'<error [^>]*>', body)]
        v["_chgs"] = [attrs(c) for c in re.findall(r'<charge [^>]*>', body)]
        out.append(v)
    return out

before = json.load(open(SCAN + "/summary_before.json"))
after2 = json.load(open(SCAN + "/summary_after2.json"))
unb_before = visits(open(SCAN + "/unbilled_before.xml").read())
unb_after = visits(open(SCAN + "/unbilled_after2.xml").read()) if os.path.exists(SCAN + "/unbilled_after2.xml") else visits(open(SCAN + "/unbilled_after.xml").read())
after_ids = {v["id"] for v in unb_after}

rows = []
def add(col, state, patient, dos, carrier, err, action, visit="", chart="", amount=""):
    rows.append({"column": col, "state": state, "patient": patient, "chart": chart, "visit": visit, "dos": dos,
                 "carrier": carrier, "error": err, "amount": amount, "action": action})

for v in unb_before:
    c = v["_chgs"][0] if v["_chgs"] else {}
    err = "; ".join(e.get("name", "") for e in v["_errs"])
    amt = sum(float(x.get("totalfee", 0) or 0) for x in v["_chgs"])
    if v["id"] in after_ids:
        act = ("standing hold - chart has zero insurance plans (live getdemographic this run); HCA Florida Capital facesheet "
               "(admit 10/12/2026) on William's turn; no new facesheet, Pam email or board note")
        add("Unbilled", "remaining", v.get("patientname", ""), c.get("dos", "").strip(), v.get("carriername", "").strip() or "(none)",
            err, act, visit=v["id"], chart=v.get("patientid", ""), amount="%.2f" % amt)
    else:
        act = ("cleared - visit_order_release.py 48449 23368913 --order 2 --release --live: visit insorder 2,1 -> 2 (Florida Blue "
               "alone; the chart's Medicare plan is Part A only, Medicare answered $0 PR-27 on 10/20, so there is no Medicare "
               "secondary claim to build and no MSP code to invent), onhcfa 1, hideunbillablevisits success=1; the Florida Blue "
               "original of 10/21 stands, nothing re-sent")
        add("Unbilled", "cleared", v.get("patientname", ""), c.get("dos", "").strip(), v.get("carriername", "").strip(),
            err, act, visit=v["id"], chart=v.get("patientid", ""), amount="%.2f" % amt)

HOLD = {"1700302": "standing hold - 25 AARP Medigap secondary rejections; AARP member number still needed from William",
        "1700311": "standing hold - Aetna AET07 rejections held for William's subscriber-relationship answer / the Feb 2026 HCA facesheet",
        "1700294": "standing hold - AET12 carrier master still sends the TIN as payer id (board row aet12-carrier-cpid); not rebilled"}
for run, lst in after2.get("exclusions", {}).items():
    for v in lst or []:
        c = v["_chgs"][0] if v.get("_chgs") else {}
        err = "; ".join(e.get("name", "") for e in v.get("_errs", []))
        amt = sum(float(x.get("totalfee", 0) or 0) for x in v.get("_chgs", []))
        add("Exclusions", "remaining", v.get("patientname", ""), c.get("dos", "").strip(), v.get("carriercodeshort") or v.get("carriercode", ""),
            err, HOLD.get(run, "standing hold") + " (claim run %s)" % run, visit=v.get("id", ""), chart=v.get("patientid", ""), amount="%.2f" % amt)

add("Charge Review", "clear", "", "", "", "", "0 charges before and after")
add("Claim Inspector", "clear", "", "", "", "", "0 batches before and after")
add("ERA", "clear", "", "", "", "", "ERA Center 0 checks / $0.00 unposted before and after; era_post --all-unposted 0 lines; era_clear 0 dismissed / 0 held; "
    "nothing to upload; Availity / Treasury: no new PDF or Check/EFT export (VALLANCE_JUDETH_08042026.pdf in 'billing agent project files' is an 8/4/2026 progress note, not a remit)")
add("Sweep", "info", "", "", "UNI20,BCBS", "", "UNI20/BCBS pre-5/1 pass 155 (--min-age 159 --max 60 --skip-answered): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent")

csv_path = "_run report 10-22 0640.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "chart", "visit", "dos", "carrier", "error", "amount", "action"])
    w.writeheader(); w.writerows(rows)

# --- needs_facesheet_list.md section (chart ids only) ---
section = f"""
## {STAMP} - backend billing run, {SLOT} slot (ehpa cloud, repo attached) - 06:39-07:10Z
- Bootstrap: repo ATTACHED (origin/main ad7542e at start; main checked out, symlinked); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no credential file); layout 1219 helper files + OCR tools; v12 precondition (seven repo helpers over the workspace, four greps, tf_writeoff_watch.json on main) pass; pseudonyms.json (410 names, Drive 10/21 17:55Z) in both secrets folders; deceased_cache.json (Drive 10/21 21:56Z, 76 dated) merged into both caches. State bundle: Drive 'workspace mirror' newest is 2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). Missing optional helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py, github_sync.py. Guard: no START younger than 40 min (0110Z run has its RUN COMPLETE digest); START 06:50Z, lock written and deleted at the end. ONE login 06:50Z (engine pass), reused by every later helper; no lock, no 429. Learned from others: git log 36h = this routine, the Billing Button slots (0134Z/0331Z/0527Z/0544Z) and the nightly cascade; SHARED_LESSONS lines newer than the 0110Z run: none; 0 applied.
- Sources: Insurance Refresh Board 0 rows updated after 00:30Z 10/22, drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved / 0 waiting; approvals_pending.json on main: no waiting/approved item covers chart 48449. Drive: nothing new in the facesheet folders, 'bht Optum era downloads', 'treasury payments', the Claimocity drop or 'board inbox' since the 0110Z run except VALLANCE_JUDETH_08042026.pdf (05:44Z, 'billing agent project files') = an 8/4/2026 progress note, not a remit - nothing to post. Pam Gmail (2d): the three 10/20 admit threads, all already worked. Both drive_sync registries list no current inbox file as applied - nothing trashed.
- Engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, plainly in the foreground, 06:50-06:54Z, report reports/button/2026-10-22T0650Z.json): Columns 0/0/7/29 -> 0/0/7/29; ERA 0 -> 0; packages: none approved. The GitHub Billing Button slots before this run: 0527Z columns (Unbilled 40 -> 7), 0544Z cascade; the next slot (07:17Z) was not overlapped.
- Columns (columns_scan before 06:50Z -> after2 07:0xZ): Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 7 ($1,563) -> 6 ($1,263) | Exclusions 29 -> 29 (overview 30 / $5,018 lags the list).
- UNBILLED 7 -> 6: NEW row chart 48449 v19457091 (99349 10/01/2026, $300, Florida Blue) 'When billing Medicare as the non-primary carrier, the MSP Code on the Insurance Tab is required' - the 0510Z 10/21 run had set the visit order 2,1 (Florida Blue first, Medicare second) after Medicare's $0 PR-27; the chart's Medicare plan (seq 1, since 2007) is Part A only (AMD 271 10/21), so no Medicare secondary claim can pay and no MSP code applies -> visit_order_release.py 48449 23368913 --order 2 --release (dry, then --live): insorder 2,1 -> 2, onhcfa 1, released (success=1); the Florida Blue original sent 10/21 stands, nothing re-sent. The chart DEFAULT order is still Medicare first (left alone; the 10/21 WATCH line still asks a chat session to confirm with William whether a Part-A-only chart flips to the retiree plan for good). The six other rows = the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (two visits each, $421 each, admit 10/12/2026) - live plan count unchanged, standing hold on William's turn.
- EXCLUSIONS 29 -> 29: chart 17470713's 25 AARP rows (run 1700302), chart 17471204's three AET07 rows (run 1700311, $783), the AET12 chart-24750 row (run 1700294) - standing holds, nothing rebilled; excl_dup_complete / excl_crossover_complete found nothing to complete.
- ERA (step 5): (a) nothing to upload; (b) GET /api/era/checks 0 checks / $0.00 before and after; (c) era_post --all-unposted 0 lines; (d) nothing to post by hand; (e) era_clear 0 dismissed / 0 held; (f) no new call shapes; (g) Availity / Treasury: no new PDF or Check/EFT export. Auto-posted $0, manual-posted 0 lines, residuals $0, checks cleared 0, still open 0.
- UNI20/BCBS pre-5/1 pass 155 (claim_status_sweep.py --min-age 159 --max 60 --carriers UNI20,BCBS --skip-answered, read-only 277): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent, 0 written off.
- Writes this run (AdvancedMD): ONE full-visit resave (v19457091 insorder 2, onhcfa 1) + ONE hideunbillablevisits. Dollars re-sent $0.00. Write-offs none. Approvals applied 0 / submitted 0 / waiting 0. Permission-classifier refusals: none. Script errors: none.
- Board update file: board_updates_{STAMP}.json (10 append ops on the standing rows + rowley-corinne-48449) -> 'board inbox'. No denials_updates file (queue empty).
- Waiting on William (unchanged): takeback decision chart 17474741 v19455454 (ERA 1053220); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); the 2026 VA referral / authorization for chart 17478013's 10/5/2026 admission (8 visits, $1,430); chart 17471204's three Aetna claims ($783); AARP member number chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); chart 17474290 CO-97 ($310); chart 17473501 $122.29 coinsurance payer; chart 48449 default order (Part A only - retiree plan first for good?).
- Calls learned: 0 new shapes; vocabulary entries added: 0. Helpers this run: run_outputs_1022_0640.py (local report pieces only).
"""
open("needs_facesheet_list.md", "a").write(section)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(section)

# --- board update file (board row ids as the 0110Z run used them) ---
SRC = "%s columns run (ehpa cloud) - run %s" % (SLOT.replace(" 10/22", "").lower().replace("am", "am ET 10/22"), STAMP)
SRC = "3am ET 10/22 columns run (ehpa cloud) - run " + STAMP
def chk(ok, text): return {"ok": ok, "result": text, "src": SRC, "when": "10/22"}
ops = []
def up(rid, ok, text, notes=None):
    op = {"op": "upsert", "collection": "items", "id": rid, "append": {"checks": [chk(ok, text)]}}
    if notes: op["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(op)
up("availity-remits-backlog", "na", "3 AM ET 10/22: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (the only new Drive file, an 8/4/2026 progress note in 'billing agent project files', is not a remit); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: the three 10/20 admit threads, all worked. ERA Center 0 checks before and after (engine pass 06:50-06:54Z, Post button $0.00). Columns 0/0/7/29 -> 0/0/6/29: the new MSP-code row on chart 48449 released (visit order Florida Blue alone); every other row a standing hold. UNI20/BCBS pre-5/1 pass 155: 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310), 0 sent.")
up("aet12-carrier-cpid", "na", "3 AM ET 10/22: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")
for rid, pid, vis in (("maddern-digby-[first]-17478059", "17478059", "v19457778 / v19457794"), ("[name]-17478063", "17478063", "v19457783 / v19457797"), ("edgerton-jocelyn-17478064", "17478064", "v19457784 / v19457791")):
    up(rid, "human", "3 AM ET 10/22: chart %s still has zero insurance plans (Unbilled list unchanged at 07:0xZ); no new HCA / TMH / PCC facesheet, Pam email or board note - the two visits (%s, $421) stay in Unbilled on your turn." % (pid, vis))
up("poulter-ellery-gwen-denials", "human", "3 AM ET 10/22: the 25 AARP Medigap secondary rejections of claim run 1700302 stay on the exclusion list - AARP member number still needed.")
up("tolliver-tracy", "human", "3 AM ET 10/22: the three Aetna AET07 rejections of claim run 1700311 (v19431511 / v19435174 / v19435175, $783) stay on the exclusion list, held for your subscriber-relationship answer / the Feb 2026 HCA facesheet.")
up("[name]-17478013", "human", "3 AM ET 10/22: nothing new - the 2026 VA referral / authorization number for the 10/5/2026 HCA admission is still needed before the 8 visits ($1,430) are re-sent.")
up("[name]-17474741", "human", "3 AM ET 10/22: ERA check 1053220 (Medicare 820007360, the takeback pair on v19455454) still dismissed outside the routine, both lines unposted on the visit - your decision stands.")
up("rowley-corinne-48449", "ok", "3 AM ET 10/22: v19457091 (99349 10/1/2026, $300) surfaced in Unbilled with 'When billing Medicare as the non-primary carrier, the MSP Code on the Insurance Tab is required' after the 10/21 re-route (Florida Blue first, Medicare second). Medicare is Part A only on this chart (AMD 271 10/21) and answered $0 PR-27 on 10/20, so there is no Medicare secondary claim to build: visit order set to Florida Blue alone (insorder 2, onhcfa 1) and released; the Florida Blue original of 10/21 stands. The chart DEFAULT order is still Medicare first - say whether a Part-A-only chart should carry the retiree plan first for good.",
   notes="Visit 19457091 released from Unbilled (Florida Blue alone - Medicare Part A only cannot pay a 99349). Your call: flip the chart default order to Florida Blue first?")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
json.dump(board, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

# --- captured_calls additions (0 new shapes) ---
add_md = f"""# captured_calls additions - {STAMP} (3 AM ET 10/22/2026, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after/after2); GET /api/era/checks (era_list.py);
posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0); Stedi 276/277 (claim_status_sweep.py pass 155, 17 asked);
getdemographic (plan_check_1022_0110.py chart 48449); gettxhistory (txh.py chart 48449); updvisitwithcharges full-visit echo with insorder="2"
onhcfa="1" + hideunbillablevisits (visit_order_release.py 48449 anchor charge 23368913 --order 2 --release --live: insorder 2,1 -> 2, success=1).
Vocabulary entries added: 0.
"""
open("outbox/captured_calls_additions_2026-10-22_0640UTC-3amET-ehpa-cloud.md", "w").write(add_md)
print("rows", len(rows), "csv", csv_path, "ops", len(ops))
