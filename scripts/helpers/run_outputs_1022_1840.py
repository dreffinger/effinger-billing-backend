#!/usr/bin/env python3
# PLAIN ENGLISH (report pieces of the 2:40 PM ET 10/22/2026 backend billing run, stamp 2026-10-22T1840Z): LOCAL ONLY, no AMD call.
# Decides: nothing. Reads this run's scan folder (scan_2026-10-22T1847Z: before / after summaries + the raw XML) and the
#   registers the engine pass wrote, and writes the report pieces the prompt asks for: the run report CSV (names allowed -
#   it goes to William by SendUserFile), the needs_facesheet_list.md section (chart ids only), the board update file for the
#   'board inbox' (real board row ids, taken from the 1240Z file the board applied, plus one new row for today's Pam admit),
#   the captured_calls additions file (0 new shapes this run) and the run digest. Never touches AMD, never prints a member id
#   outside the board file (which lives only in William's Drive inbox).
# Usage: python3 run_outputs_1022_1840.py
import json, re, csv, os, datetime
STAMP = "2026-10-22T1840Z"; SLOT = "2:40 PM ET 10/22"; SCAN = "scan_2026-10-22T1847Z"
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
        act = ("standing hold - chart has zero insurance plans (live getdemographic this run, plan_check_1022_1840.py); HCA Florida Capital "
               "facesheet (admit 10/12/2026) on William's turn; no new facesheet, Pam email or board note since the 1240Z run")
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
add("ERA", "clear", "", "", "", "", "ERA Center 0 checks / $0.00 unposted before and after (era_list 18:50Z / 18:51Z); era_post --all-unposted 0 lines; era_clear 0 dismissed / 0 held; "
    "nothing to upload; Availity / Treasury: no new PDF or Check/EFT export; 1053220 (Medicare takeback pair) stays dismissed outside the routine for William's decision")
add("Sweep", "info", "", "", "UNI20,BCBS", "", "UNI20/BCBS pre-5/1 pass 157 (--min-age 174 --max 60 --skip-answered): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent")
add("Admits", "info", "[name]", "10/19/2026", "Medicare A (sheet)", "", "NEW Pam admit email 10/22 15:00Z (NA Brynwood, admitted 10/19/2026 from Capital Regional): Medicare A primary with the MBI on the sheet, 'Medicare A coinsurance from private' (secondary carrier not named), Medicaid number on the sheet; lookuppatient [name]% = no AMD chart yet - the Claimocity feed creates it; nothing to bill yet, watched (board row brown-lisa-admit-1019)")
add("Admits", "info", "", "", "", "", "Pam 10/20 admits re-checked with lookuppatient: BAKER / DUNWOODY still no AMD chart; SMYTHE namesake chart 25746 (not her); ORME readmit = existing chart 17474046")

csv_path = "_run report 10-22 1840.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "chart", "visit", "dos", "carrier", "error", "amount", "action"])
    w.writeheader(); w.writerows(rows)

# --- needs_facesheet_list.md section (chart ids only) ---
section = f"""
## {STAMP} - backend billing run, {SLOT} slot (ehpa cloud, repo attached) - 18:40-19:0xZ
- Bootstrap: repo ATTACHED (origin/main b659daa at start; main checked out, symlinked); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no credential file); layout 1223 helper files + OCR tools; v12 precondition (seven repo helpers over the workspace, four greps, tf_writeoff_watch.json on main) pass; pseudonyms.json (410 names, Drive 10/21 17:55Z) in both secrets folders; deceased_cache.json (Drive 10/21 21:56Z, 38 dated) merged into the workspace cache (repo copy left scrubbed). State bundle: Drive 'workspace mirror' newest is 2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). Missing optional helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py, github_sync.py. Guard: no START younger than 40 min (1240Z run has its RUN COMPLETE digest); START 18:47Z, lock written and deleted at the end. ONE login 18:47Z (engine pass), reused by every later helper; no lock, no 429. Prompt fired as the v7 text at 18:39Z (an off-schedule firing - the 11 AM and 1 PM ET slots left no START or digest on Drive; the GitHub slots #139-#141 at 13:29Z / 15:28Z / 17:24Z covered the columns and ERA Center in between, all 0/0/6/29, ERA 0); the v12 text + v13 insert on main applied. Learned from others: git log 36h = this routine, the Billing Button slots and the nightly cascade; SHARED_LESSONS lines newer than the 1240Z run: none; 0 applied.
- Sources: Insurance Refresh Board rows on Claude's turn read (first page, standing rows, no new William note), drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved / 0 waiting; approvals_pending.json on main: 93 items, none waiting or approved. Drive: nothing new in the facesheet folders, 'bht Optum era downloads', 'treasury payments', the Claimocity drop or 'board inbox' since the 1240Z run. Pam Gmail (2d): ONE new admit thread 15:00Z 10/22 (NA Brynwood, admitted 10/19/2026) - facesheet read from the attachment: Medicare A primary, a private Medicare-A-coinsurance plan (carrier not named), Medicaid number on the sheet; lookuppatient: no AMD chart yet (listed, not created); the three 10/20 threads re-checked: two still without an AMD chart, one a namesake, one the existing readmit chart 17474046. Both drive_sync registries list no current inbox file as applied - nothing trashed.
- Engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, plainly in the foreground, 18:47-18:51Z, report reports/button/2026-10-22T1847Z.json): Columns 0/0/6/29 -> 0/0/6/29; ERA 0 -> 0; packages: none approved. The GitHub Billing Button slot #141 (17:24-17:31Z) ran before this run; the next slot (19:17Z cron) was not overlapped by the engine pass.
- Columns (columns_scan before 18:47Z -> after 18:49Z): Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 6 ($1,263) -> 6 ($1,263) | Exclusions 29 -> 29 (overview 30 / $5,018 lags the list).
- UNBILLED 6 -> 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (two visits each, $421 each, admit 10/12/2026) - plan_check_1022_1840.py: 0 plans on each (live getdemographic), chart 17470713 4 plans, chart 17478013 1 plan (VA) - standing hold on William's turn; unbilled_repair / payreasons found nothing to repair.
- EXCLUSIONS 29 -> 29: chart 17470713's 25 AARP rows (run 1700302, $3,610), chart 17471204's three AET07 rows (run 1700311, $783), the AET12 chart-24750 row (run 1700294, $315) - standing holds, nothing rebilled; excl_dup_complete / excl_crossover_complete found nothing to complete.
- ERA (step 5): (a) nothing to upload; (b) GET /api/era/checks 0 checks / $0.00 before and after; (c) era_post --all-unposted 0 lines; (d) nothing to post by hand; (e) era_clear 0 dismissed / 0 held; (f) no new call shapes; (g) Availity / Treasury: no new PDF or Check/EFT export. Auto-posted $0, manual-posted 0 lines, residuals $0, checks cleared 0, still open 0. 1053220 (Medicare 820007360, the takeback pair on chart 17474741 v19455454) stays dismissed outside the routine - William's decision.
- UNI20/BCBS pre-5/1 pass 157 (claim_status_sweep.py --min-age 174 --max 60 --carriers UNI20,BCBS --skip-answered, read-only 277): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent, 0 written off.
- Writes this run (AdvancedMD): none by this container beyond the engine pass, which wrote nothing (0 bypasses, 0 repairs, 0 completions, 0 posts). Dollars re-sent $0.00. Write-offs none. Approvals applied 0 / submitted 0 / waiting 0. Permission-classifier refusals: none. Script errors: none.
- Board update file: board_updates_{STAMP}.json (9 append ops on the standing rows, real ids, + 1 new row for today's Pam admit) -> 'board inbox'. No denials_updates file (queue empty).
- Waiting on William (unchanged): takeback decision chart 17474741 v19455454 (ERA 1053220); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); the 2026 VA referral / authorization for chart 17478013's 10/5/2026 admission (8 visits, $1,430); chart 17471204's three Aetna claims ($783); AARP member number chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); chart 17474290 CO-97 ($310); chart 17473501 $122.29 coinsurance payer; chart 48449 default order (Part A only - retiree plan first for good?).
- Calls learned: 0 new shapes; vocabulary entries added: 0. Helpers this run: run_outputs_1022_1840.py (local report pieces only), plan_check_1022_1840.py and admit_lookup_1022_1840.py (read-only re-stamps of the 10/22 helpers).
"""
open("needs_facesheet_list.md", "a").write(section)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(section)

# --- board update file (real board row ids, as the 1240Z file the board applied used them) ---
SRC = "2:40pm ET 10/22 columns run (ehpa cloud) - run " + STAMP
def chk(ok, text): return {"ok": ok, "result": text, "src": SRC, "when": "10/22"}
ops = []
def up(rid, ok, text, notes=None):
    op = {"op": "upsert", "collection": "items", "id": rid, "append": {"checks": [chk(ok, text)]}}
    if notes: op["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(op)
up("availity-remits-backlog", "na", "2:40 PM ET 10/22: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 10/21); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: one new Brynwood admit 15:00Z (no AMD chart yet - row brown-lisa-admit-1019), the 10/20 admits unchanged (two still without a chart). ERA Center 0 checks before and after (engine pass 18:47-18:51Z, Post button $0.00). Columns 0/0/6/29 -> 0/0/6/29 - every row a standing hold, no AMD write this slot. UNI20/BCBS pre-5/1 pass 157: 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310), 0 sent.")
up("aet12-carrier-cpid", "na", "2:40 PM ET 10/22: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")
for rid, pid, vis in (("madison-digby-[first]-17478059", "17478059", "v19457778 / v19457794"), ("[name]-17478063", "17478063", "v19457783 / v19457797"), ("edgerton-jocelyn-17478064", "17478064", "v19457784 / v19457791")):
    up(rid, "human", "2:40 PM ET 10/22: chart %s still has zero insurance plans (live getdemographic 18:5xZ); no new HCA / TMH / PCC facesheet, Pam email or board note - the two visits (%s, $421) stay in Unbilled on your turn." % (pid, vis))
up("poulter-ellery-gwen-denials", "human", "2:40 PM ET 10/22: the 25 AARP Medigap secondary rejections of claim run 1700302 ($3,610) stay on the exclusion list - AARP member number still needed (chart carries AAR01 seq 4 since 1/1/2026 with no usable id).")
up("tully-tracy", "human", "2:40 PM ET 10/22: the three Aetna AET07 rejections of claim run 1700311 (v19431511 / v19435174 / v19435175, $783) stay on the exclusion list, held for your subscriber-relationship answer / the Feb 2026 HCA facesheet.")
up("[name]-17478013", "human", "2:40 PM ET 10/22: nothing new - the 2026 VA referral / authorization number for the 10/5/2026 HCA admission is still needed before the 8 visits ($1,430) are re-sent (chart still carries the VA plan alone).")
up("[name]-17474741", "human", "2:40 PM ET 10/22: ERA check 1053220 (Medicare 820007360, the takeback pair on v19455454) still dismissed outside the routine, both lines unposted on the visit - your decision stands.")
# today's Pam admit: the identifiers (name, DOB, MBI, Medicaid id) live ONLY in inbox/pam/brown_admit_1019.json (workspace, never mirrored)
P = json.load(open("inbox/pam/brown_admit_1019.json"))
ops.append({"op": "upsert", "collection": "items", "id": "brown-lisa-admit-1019", "set": {
    "patient": P["patient"], "dob": P["dob"], "facility": "Brynwood Health and Rehabilitation Center (admitted 10/19/2026 from Capital Regional)",
    "amdid": "", "mbi": P["mbi"], "amount": 0, "status": "claude",
    "inscarrier": "Medicare A (facesheet)", "insid": P["mbi"],
    "insplans": "facesheet: Medicare A primary %s; 'Medicare A coinsurance from private' (secondary, carrier not named); Medicaid # %s" % (P["mbi"], P["medicaid"]),
    "need": "None yet - watching. Pam's NA facesheet (email 10/22 15:00Z, IMG_9758): Brynwood admit 10/19/2026 from Capital Regional; Medicare (HIC) %s primary, a private Medicare-A-coinsurance plan whose carrier the sheet does not name, Medicaid # %s (Medicare A coinsurance 'from private' + a Medicaid number = check the SMMC plan with the 271). No AMD chart yet (lookuppatient %s 18:5xZ 10/22) - the Claimocity / visit feed creates it; the first run that finds the chart adds FLO02 with this MBI (no group), runs AMD's 271 + the Medicaid 271 for the SMMC plan, and asks you only for the private secondary's name if the 271 does not name it." % (P["mbi"], P["medicaid"], P["pattern"]),
    "why": "Pam admit email 10/22/2026 15:00Z (NA Brynwood) - no AMD chart yet, listed per the 10/14 rule (never turned into a chart by the routine)",
    "created": NOW, "updated": NOW},
    "append": {"notes": [{"who": "Claude", "text": "Created by the 2:40 PM ET 10/22 run from Pam's admit email. Facesheet dx: I69.354, I48.0, E03.9, F10.230, I10, E78.5. Nothing for you unless the 271 cannot name the private secondary.", "at": NOW}]}})
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
json.dump(board, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

# --- captured_calls additions (0 new shapes) ---
add_md = f"""# captured_calls additions - {STAMP} (2:40 PM ET 10/22/2026, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after inside the engine pass 18:47-18:51Z);
GET /api/era/checks (era_list.py before/after, 0 checks); posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0);
Stedi 276/277 (claim_status_sweep.py pass 157, 17 asked); getdemographic (plan_check_1022_1840.py charts 17478059 / 17478063 / 17478064 /
17470713 / 17478013); lookuppatient (admit_lookup_1022_1840.py, six name patterns incl. today's Pam admit). No AdvancedMD write by this container.
Vocabulary entries added: 0.
"""
open("outbox/captured_calls_additions_2026-10-22_1840UTC-240pmET-ehpa-cloud.md", "w").write(add_md)
print("rows", len(rows), "csv", csv_path, "ops", len(ops))
