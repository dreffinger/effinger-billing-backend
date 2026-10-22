#!/usr/bin/env python3
# PLAIN ENGLISH (report pieces of the 9 AM ET 10/22/2026 backend billing run, stamp 2026-10-22T1240Z): LOCAL ONLY, no AMD call.
# Decides: nothing. Reads this run's scan folder (scan_2026-10-22T1251Z: before / after summaries + the raw XML) and the
#   registers the engine pass wrote, and writes the four report pieces the prompt asks for: the run report CSV (names allowed -
#   it goes to William by SendUserFile), the needs_facesheet_list.md section (chart ids only), the board update file for the
#   'board inbox' (real board row ids, taken from the 0640Z file the board applied), and the captured_calls additions file
#   (0 new shapes this run). Never touches AMD, never prints a member id.
# Usage: python3 run_outputs_1022_1240.py
import json, re, csv, os, datetime
STAMP = "2026-10-22T1240Z"; SLOT = "9 AM ET 10/22"; SCAN = "scan_2026-10-22T1251Z"
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

after = json.load(open(SCAN + "/summary_after.json"))
unb_before = visits(open(SCAN + "/unbilled_before.xml").read())
unb_after = visits(open(SCAN + "/unbilled_after.xml").read())
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
        act = ("standing hold - chart has zero insurance plans (live getdemographic this run, plan_check_1022_1240.py); HCA Florida Capital "
               "facesheet (admit 10/12/2026) on William's turn; no new facesheet, Pam email or board note since the 0640Z run")
        add("Unbilled", "remaining", v.get("patientname", ""), c.get("dos", "").strip(), v.get("carriername", "").strip() or "(none)",
            err, act, visit=v["id"], chart=v.get("patientid", ""), amount="%.2f" % amt)
    else:
        add("Unbilled", "cleared", v.get("patientname", ""), c.get("dos", "").strip(), v.get("carriername", "").strip(),
            err, "cleared by the engine pass", visit=v["id"], chart=v.get("patientid", ""), amount="%.2f" % amt)

HOLD = {"1700302": "standing hold - 25 AARP Medigap secondary rejections; AARP member number still needed from William",
        "1700311": "standing hold - Aetna AET07 rejections held for William's subscriber-relationship answer / the Feb 2026 HCA facesheet",
        "1700294": "standing hold - AET12 carrier master still sends the TIN as payer id (board row aet12-carrier-cpid); not rebilled"}
for run, lst in after.get("exclusions", {}).items():
    for v in lst or []:
        c = v["_chgs"][0] if v.get("_chgs") else {}
        err = "; ".join(e.get("name", "") for e in v.get("_errs", []))
        amt = sum(float(x.get("totalfee", 0) or 0) for x in v.get("_chgs", []))
        add("Exclusions", "remaining", v.get("patientname", ""), c.get("dos", "").strip(), v.get("carriercodeshort") or v.get("carriercode", ""),
            err, HOLD.get(run, "standing hold") + " (claim run %s)" % run, visit=v.get("id", ""), chart=v.get("patientid", ""), amount="%.2f" % amt)

add("Charge Review", "clear", "", "", "", "", "0 charges before and after")
add("Claim Inspector", "clear", "", "", "", "", "0 batches before and after")
add("ERA", "clear", "", "", "", "", "ERA Center 0 checks / $0.00 unposted before and after (era_list 12:54Z); era_post --all-unposted 0 lines; era_clear 0 dismissed / 0 held; "
    "nothing to upload; Availity / Treasury: no new PDF or Check/EFT export; 1053220 (Medicare takeback pair) stays dismissed outside the routine for William's decision")
add("Sweep", "info", "", "", "UNI20,BCBS", "", "UNI20/BCBS pre-5/1 pass 156 (--min-age 174 --max 60 --skip-answered): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent")
add("Admits", "info", "", "", "", "", "Pam 10/20 admits re-checked with lookuppatient: BAKER / DUNWOODY still no AMD chart; SMYTHE namesake chart 25746 (not her); ORME readmit = existing chart 17474046")

csv_path = "_run report 10-22 1240.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "chart", "visit", "dos", "carrier", "error", "amount", "action"])
    w.writeheader(); w.writerows(rows)

# --- needs_facesheet_list.md section (chart ids only) ---
section = f"""
## {STAMP} - backend billing run, {SLOT} slot (ehpa cloud, repo attached) - 12:40-13:4xZ
- Bootstrap: repo ATTACHED (origin/main 5c00300 at start; main checked out, symlinked); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no credential file); layout 1220 helper files + OCR tools; v12 precondition (seven repo helpers over the workspace, four greps, tf_writeoff_watch.json on main) pass; pseudonyms.json (410 names, Drive 10/21 17:55Z) in both secrets folders; deceased_cache.json (Drive 10/21 21:56Z, 38 dated) merged into the workspace cache (repo copy left scrubbed). State bundle: Drive 'workspace mirror' newest is 2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). Missing optional helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py, github_sync.py. Guard: no START younger than 40 min (0640Z run has its RUN COMPLETE digest 07:06Z); START 12:47Z, lock written and deleted at the end. ONE login 12:51Z (engine pass), reused by every later helper; no lock, no 429. Prompt fired as the v7 text; the v12 text + v13 insert on main applied. Learned from others: git log 36h = this routine, the Billing Button slots (0527Z/0544Z/0734Z/0929Z/1126Z) and the nightly cascade; SHARED_LESSONS lines newer than the 0640Z run: none; 0 applied. Note: the 5 AM and 7 AM ET slots of this routine did not fire (no 0910Z / 1110Z START or digest on Drive); the GitHub slots #136-#138 covered the columns and ERA Center in between (all 0/0/6/29, ERA $66.36 -> 0 at 1126Z).
- Sources: Insurance Refresh Board 0 rows updated after 07:00Z 10/22, drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved / 0 waiting; approvals_pending.json on main: 93 items, none waiting or approved. Drive: nothing new in the facesheet folders, 'bht Optum era downloads', 'treasury payments', the Claimocity drop or 'board inbox' since the 0640Z run (Drive-wide modifiedTime > 07:10Z: only the morning money report, the weekly metrics files and the VIX desk files). Pam Gmail (2d): the three 10/20 admit threads only - lookuppatient this run: two still without an AMD chart, one a namesake, one the existing readmit chart 17474046. Both drive_sync registries list no current inbox file as applied - nothing trashed.
- Engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, plainly in the foreground, 12:51-12:55Z, report reports/button/2026-10-22T1251Z.json): Columns 0/0/6/29 -> 0/0/6/29; ERA 0 -> 0; packages: none approved. The GitHub Billing Button slot #138 (11:26-11:32Z) ran before this run; slot #139 (13:17Z cron) was not overlapped by the engine pass.
- Columns (columns_scan before 12:51Z -> after 12:54Z): Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 6 ($1,263) -> 6 ($1,263) | Exclusions 29 -> 29 (overview 30 / $5,018 lags the list).
- UNBILLED 6 -> 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (two visits each, $421 each, admit 10/12/2026) - plan_check_1022_1240.py: 0 plans on each (live getdemographic), chart 17470713 4 plans, chart 17478013 1 plan (VA) - standing hold on William's turn; unbilled_repair / payreasons found nothing to repair.
- EXCLUSIONS 29 -> 29: chart 17470713's 25 AARP rows (run 1700302), chart 17471204's three AET07 rows (run 1700311, $783), the AET12 chart-24750 row (run 1700294) - standing holds, nothing rebilled; excl_dup_complete / excl_crossover_complete found nothing to complete.
- ERA (step 5): (a) nothing to upload; (b) GET /api/era/checks 0 checks / $0.00 before and after; (c) era_post --all-unposted 0 lines; (d) nothing to post by hand; (e) era_clear 0 dismissed / 0 held; (f) no new call shapes; (g) Availity / Treasury: no new PDF or Check/EFT export. Auto-posted $0, manual-posted 0 lines, residuals $0, checks cleared 0, still open 0. 1053220 (Medicare 820007360, the takeback pair on chart 17474741 v19455454) stays dismissed outside the routine - William's decision.
- UNI20/BCBS pre-5/1 pass 156 (claim_status_sweep.py --min-age 174 --max 60 --carriers UNI20,BCBS --skip-answered, read-only 277): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent, 0 written off.
- Writes this run (AdvancedMD): none by this container beyond the engine pass, which wrote nothing (0 bypasses, 0 repairs, 0 completions, 0 posts). Dollars re-sent $0.00. Write-offs none. Approvals applied 0 / submitted 0 / waiting 0. Permission-classifier refusals: none. Script errors: none.
- Board update file: board_updates_{STAMP}.json (9 append ops on the standing rows, real ids) -> 'board inbox'. No denials_updates file (queue empty).
- Waiting on William (unchanged): takeback decision chart 17474741 v19455454 (ERA 1053220); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); the 2026 VA referral / authorization for chart 17478013's 10/5/2026 admission (8 visits, $1,430); chart 17471204's three Aetna claims ($783); AARP member number chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); chart 17474290 CO-97 ($310); chart 17473501 $122.29 coinsurance payer; chart 48449 default order (Part A only - retiree plan first for good?).
- Calls learned: 0 new shapes; vocabulary entries added: 0. Helpers this run: run_outputs_1022_1240.py (local report pieces only), plan_check_1022_1240.py and admit_lookup_1022_1240.py (read-only re-stamps of the 10/21-10/22 helpers).
"""
open("needs_facesheet_list.md", "a").write(section)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(section)

# --- board update file (real board row ids, as the 0640Z file the board applied used them) ---
SRC = "9am ET 10/22 columns run (ehpa cloud) - run " + STAMP
def chk(ok, text): return {"ok": ok, "result": text, "src": SRC, "when": "10/22"}
ops = []
def up(rid, ok, text, notes=None):
    op = {"op": "upsert", "collection": "items", "id": rid, "append": {"checks": [chk(ok, text)]}}
    if notes: op["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(op)
up("availity-remits-backlog", "na", "9 AM ET 10/22: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing new after 07:10Z outside the routines' own files); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: the three 10/20 admit threads only (two still without an AMD chart). ERA Center 0 checks before and after (engine pass 12:51-12:55Z, Post button $0.00). Columns 0/0/6/29 -> 0/0/6/29 - every row a standing hold, no AMD write this slot. UNI20/BCBS pre-5/1 pass 156: 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310), 0 sent.")
up("aet12-carrier-cpid", "na", "9 AM ET 10/22: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")
for rid, pid, vis in (("madison-digby-[first]-17478059", "17478059", "v19457778 / v19457794"), ("[name]-17478063", "17478063", "v19457783 / v19457797"), ("edgerton-jocelyn-17478064", "17478064", "v19457784 / v19457791")):
    up(rid, "human", "9 AM ET 10/22: chart %s still has zero insurance plans (live getdemographic 13:0xZ); no new HCA / TMH / PCC facesheet, Pam email or board note - the two visits (%s, $421) stay in Unbilled on your turn." % (pid, vis))
up("poulter-ellery-gwen-denials", "human", "9 AM ET 10/22: the 25 AARP Medigap secondary rejections of claim run 1700302 stay on the exclusion list - AARP member number still needed (chart carries AAR01 seq 4 since 1/1/2026 with no usable id).")
up("tully-tracy", "human", "9 AM ET 10/22: the three Aetna AET07 rejections of claim run 1700311 (v19431511 / v19435174 / v19435175, $783) stay on the exclusion list, held for your subscriber-relationship answer / the Feb 2026 HCA facesheet.")
up("[name]-17478013", "human", "9 AM ET 10/22: nothing new - the 2026 VA referral / authorization number for the 10/5/2026 HCA admission is still needed before the 8 visits ($1,430) are re-sent (chart still carries the VA plan alone).")
up("[name]-17474741", "human", "9 AM ET 10/22: ERA check 1053220 (Medicare 820007360, the takeback pair on v19455454) still dismissed outside the routine, both lines unposted on the visit - your decision stands.")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
json.dump(board, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

# --- captured_calls additions (0 new shapes) ---
add_md = f"""# captured_calls additions - {STAMP} (9 AM ET 10/22/2026, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after inside the engine pass 12:51-12:55Z);
GET /api/era/checks (era_list.py before/after, 0 checks); posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0);
Stedi 276/277 (claim_status_sweep.py pass 156, 17 asked); getdemographic (plan_check_1022_1240.py charts 17478059 / 17478063 / 17478064 /
17470713 / 17478013); lookuppatient (admit_lookup_1022_1240.py, five name patterns). No AdvancedMD write by this container.
Vocabulary entries added: 0.
"""
open("outbox/captured_calls_additions_2026-10-22_1240UTC-9amET-ehpa-cloud.md", "w").write(add_md)
print("rows", len(rows), "csv", csv_path, "ops", len(ops))
