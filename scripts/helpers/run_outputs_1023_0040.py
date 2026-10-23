#!/usr/bin/env python3
# PLAIN ENGLISH (report pieces of the 9 PM ET 10/22/2026 backend billing run, stamp 2026-10-23T0040Z, fired 00:39Z 10/23): LOCAL ONLY, no AMD call.
# Decides: nothing. Reads this run's scan folder (scan_2026-10-23T0045Z: before / after summaries + the raw XML) and the
#   registers the engine pass wrote, and writes the report pieces the prompt asks for: the run report CSV (names allowed -
#   it goes to William by SendUserFile), the needs_facesheet_list.md section (chart ids only), the board update file for the
#   'board inbox' (real board row ids, plus one new row for tonight's Pam card photo), the captured_calls additions file
#   (0 new shapes this run) and the run digest. Never touches AMD, never prints a member id outside the board file (which
#   lives only in William's Drive inbox).
# Usage: python3 run_outputs_1023_0040.py
import json, re, csv, os, datetime
STAMP = "2026-10-23T0040Z"; SLOT = "9 PM ET 10/22 (fired 00:39Z 10/23)"; SCAN = "scan_2026-10-23T0045Z"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
os.makedirs("outbox", exist_ok=True); os.makedirs("chat_history", exist_ok=True)
# tonight's admit identifiers (names, the card's member id) live ONLY in inbox/pam/admits_1023.json (workspace, never mirrored)
P = json.load(open("inbox/pam/admits_1023.json"))
CARD = P["card"]

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
        act = ("standing hold - chart has zero insurance plans; HCA Florida Capital facesheet (admit 10/12/2026) on William's turn; "
               "no new facesheet, Pam email or board note since the 1840Z run")
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
add("ERA", "clear", "", "", "", "", "ERA Center 0 checks / $0.00 unposted before and after (era_list 00:48Z / 00:48Z); era_post --all-unposted 0 lines; era_clear 0 dismissed / 0 held; "
    "nothing to upload; Availity / Treasury: no new PDF or Check/EFT export; 1053220 (Medicare takeback pair) stays dismissed outside the routine for William's decision")
add("Sweep", "info", "", "", "UNI20,BCBS", "", "UNI20/BCBS pre-5/1 pass 158 (--min-age 175 --max 60 --skip-answered): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent")
add("Admits", "info", P["new"], "", "Florida Blue BlueOptions PPO (card)", "", "NEW Pam email 10/22 23:57Z ('Independent - lives in own apt', two card photos): Florida Blue BlueOptions PPO card, member %s, plan %s, print date %s (group on the card is never entered); no DOB, facility or admit date on the email; lookuppatient %s = no AMD chart yet - nothing to bill, watched (board row %s); the first run that finds the chart adds BCBS car6062 with that member id (no group) and runs AMD's 271" % (CARD["member"], CARD["plan"], CARD["printed"], P["new_pattern"], P["new_row"]))
add("Admits", "info", P["brynwood_1019"], "10/19/2026", "Medicare A (sheet)", "", "Brynwood admit 10/19 (Pam 10/22 15:00Z): lookuppatient %s still no AMD chart (00:5xZ 10/23) - watched, row %s" % (P["brynwood_pattern"], P["brynwood_row"]))
add("Admits", "info", "", "", "", "", P["recheck_text"])

csv_path = "_run report 10-22 2100ET.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "chart", "visit", "dos", "carrier", "error", "amount", "action"])
    w.writeheader(); w.writerows(rows)

section = f"""
## {STAMP} - backend billing run, {SLOT} slot (ehpa cloud, repo attached) - 00:39-01:1xZ
- Bootstrap: repo ATTACHED (origin/main edb3d90 at start; main checked out, /home/claude/effinger-billing-backend symlinked to the session clone); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (credential file written by nightly_bootstrap.sh); layout 1226 helper files + OCR tools; pseudonyms.json (410 names, Drive 10/21 17:55Z) in both secrets folders; deceased_cache.json (Drive 10/21 21:56Z, 38 dated / 76 merged) merged into the workspace cache. State bundle: Drive 'workspace mirror' newest is 2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). Missing optional helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py, github_sync.py. Guard: no START younger than 40 min (1840Z run has its RUN COMPLETE digest; the 2325Z GitHub slot #144 is not a routine run); START 00:42Z, lock written and deleted at the end. ONE login 00:46Z (engine pass), reused by every later helper; no lock, no 429. Prompt fired as the v7 text at 00:39Z (the 9 PM ET slot, ~90 min late); the v12 text + v13 insert on main applied. Learned from others: SHARED_LESSONS lines newer than the 1840Z run: none; 0 applied.
- Sources: Insurance Refresh Board rows on Claude's turn read (first page of 200, standing rows, no new William note), drops 0; Working Denials queue 0; approvals_pending.json on main: 93 items, all done. Drive: nothing new in the facesheet folders, 'bht Optum era downloads', 'treasury payments', the Claimocity drop or 'board inbox' since the 1840Z run (only that run's own files). Pam Gmail (2d): ONE new thread 23:57Z 10/22 - two HEIC photos of a Florida Blue BlueOptions PPO card ('Independent - lives in own apt'); lookuppatient: no AMD chart (listed, not created; card data on the new board row); the 10/19-10/20 admits re-checked: two still without an AMD chart (BAK*/DIC*), one a namesake chart, one the existing readmit chart 17474046; Brynwood 10/19 admit (BRO*) still without a chart. Both drive_sync registries list no current inbox file as applied - nothing trashed.
- Engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, plainly in the foreground, 00:46-00:49Z, report reports/button/2026-10-23T0045Z.json): Columns 0/0/6/29 -> 0/0/6/29; ERA 0 -> 0; packages: none approved. The GitHub Billing Button slot #144 (23:24-23:30Z 10/22) ran before this run; the next slot (01:17Z cron) was not overlapped by the engine pass.
- Columns (columns_scan before 00:46Z -> after 00:47Z): Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 6 ($1,263) -> 6 ($1,263) | Exclusions 29 -> 29 (overview 30 / $5,018 lags the list).
- UNBILLED 6 -> 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (two visits each, $421 each, admit 10/12/2026) - standing hold on William's turn (HCA facesheets); unbilled_repair / payreasons found nothing to repair.
- EXCLUSIONS 29 -> 29: chart 17470713's 25 AARP rows (run 1700302, $3,610), chart 17471204's three AET07 rows (run 1700311, $783), the AET12 chart-24750 row (run 1700294, $315) - standing holds, nothing rebilled; excl_dup_complete / excl_crossover_complete found nothing to complete.
- ERA (step 5): (a) nothing to upload; (b) GET /api/era/checks 0 checks / $0.00 before and after; (c) era_post --all-unposted 0 lines; (d) nothing to post by hand; (e) era_clear 0 dismissed / 0 held; (f) no new call shapes; (g) Availity / Treasury: no new PDF or Check/EFT export. Auto-posted $0, manual-posted 0 lines, residuals $0, checks cleared 0, still open 0. 1053220 (Medicare 820007360, the takeback pair on chart 17474741 v19455454) stays dismissed outside the routine - William's decision.
- UNI20/BCBS pre-5/1 pass 158 (claim_status_sweep.py --min-age 175 --max 60 --carriers UNI20,BCBS --skip-answered, read-only 277): 17 asked - 16 PENDING at payer chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310); 0 candidates, 0 sent, 0 written off.
- Writes this run (AdvancedMD): none by this container beyond the engine pass, which wrote nothing (0 bypasses, 0 repairs, 0 completions, 0 posts). Dollars re-sent $0.00. Write-offs none. Approvals applied 0 / submitted 0 / waiting 0. Permission-classifier refusals: none. Script errors: none (ImageMagick cannot decode iPhone HEIC - pillow-heif in a throwaway venv converted the two card photos; the system Pillow was restored afterwards).
- Board update file: board_updates_{STAMP}.json (append ops on the standing rows, real ids, + 1 new row for tonight's Pam card photos) -> 'board inbox'. No denials_updates file (queue empty).
- Waiting on William (unchanged + 1): takeback decision chart 17474741 v19455454 (ERA 1053220); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); the 2026 VA referral / authorization for chart 17478013's 10/5/2026 admission (8 visits, $1,430); chart 17471204's three Aetna claims ($783); AARP member number chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); chart 17474290 CO-97 ($310); chart 17473501 $122.29 coinsurance payer; chart 48449 default order (Part A only). NEW (nothing to do yet): Pam's 10/22 card photos (HIC*) - no AMD chart, no DOB / facility on the email; the row carries the card data for the first run that finds the chart.
- Calls learned: 0 new shapes; vocabulary entries added: 0. Helpers this run: run_outputs_1023_0040.py (local report pieces only), admit_lookup_1023_0040.py (read-only re-stamp of the 10/22 helper).
"""
open("needs_facesheet_list.md", "a").write(section)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(section)

SRC = "9pm ET 10/22 columns run (ehpa cloud) - run " + STAMP
def chk(ok, text): return {"ok": ok, "result": text, "src": SRC, "when": "10/22"}
ops = []
def up(rid, ok, text, notes=None):
    op = {"op": "upsert", "collection": "items", "id": rid, "append": {"checks": [chk(ok, text)]}}
    if notes: op["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(op)
up("availity-remits-backlog", "na", "9 PM ET 10/22 (run 00:39-01:1xZ 10/23): no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 10/21); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: one new thread 23:57Z (Florida Blue card photos, no AMD chart yet - row hic[member id]), the 10/19-10/20 admits unchanged (three still without a chart). ERA Center 0 checks before and after (engine pass 00:46-00:49Z, Post button $0.00). Columns 0/0/6/29 -> 0/0/6/29 - every row a standing hold, no AMD write this slot. UNI20/BCBS pre-5/1 pass 158: 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 ($310), 0 sent.")
up("aet12-carrier-cpid", "na", "9 PM ET 10/22: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")
for rid, pid, vis in (("maddern-digby-[first]-17478059", "17478059", "v19457778 / v19457794"), ("[name]-17478063", "17478063", "v19457783 / v19457797"), ("edgerton-jocelyn-17478064", "17478064", "v19457784 / v19457791")):
    up(rid, "human", "9 PM ET 10/22: chart %s still has zero insurance plans (Unbilled 'Insurance order is missing' before and after the 00:46Z engine pass); no new HCA / TMH / PCC facesheet, Pam email or board note - the two visits (%s, $421) stay in Unbilled on your turn." % (pid, vis))
up("poulter-ellery-gwen-denials", "human", "9 PM ET 10/22: the 25 AARP Medigap secondary rejections of claim run 1700302 ($3,610) stay on the exclusion list - AARP member number still needed (chart carries AAR01 seq 4 since 1/1/2026 with no usable id).")
up("tolliver-tracy", "human", "9 PM ET 10/22: the three Aetna AET07 rejections of claim run 1700311 (v19431511 / v19435174 / v19435175, $783) stay on the exclusion list, held for your subscriber-relationship answer / the Feb 2026 HCA facesheet.")
up("[name]-17478013", "human", "9 PM ET 10/22: nothing new - the 2026 VA referral / authorization number for the 10/5/2026 HCA admission is still needed before the 8 visits ($1,430) are re-sent (the facesheet pasted 10/15 carries the 10/2025 auth VA0048867957, not a 2026 one).")
up(P["brynwood_row"], "na", "9 PM ET 10/22: lookuppatient %s at 00:5xZ 10/23 - still no AMD chart for the Brynwood 10/19 admit; nothing to bill, watching." % P["brynwood_pattern"])
ops.append({"op": "upsert", "collection": "items", "id": P["new_row"], "set": {
    "patient": P["new"], "dob": "", "facility": "home / independent living ('Independent - lives in own apt', Pam 10/22)",
    "amdid": "", "mbi": "", "amount": 0, "status": "claude",
    "inscarrier": "BCBS Florida Blue BlueOptions PPO (card)", "insid": CARD["member"],
    "insplans": "card: Florida Blue BlueOptions PPO member %s, plan %s, printed %s (group on the card never entered); no Medicare / Medicaid on the email" % (CARD["member"], CARD["plan"], CARD["printed"]),
    "need": "None yet - watching. Pam's email 10/22 23:57Z ('Independent - lives in own apt') carried two photos of a Florida Blue BlueOptions PPO card (member %s, plan %s, print date %s) and nothing else - no DOB, no facility, no admit date. lookuppatient %s at 00:5xZ 10/23 = no AMD chart yet (not created by the routine, per the 10/14 rule). The first run that finds the chart adds BCBS car6062 %s (no group), runs AMD's 271 on it and orders the visits; nothing for you unless the 271 says the plan is not in force." % (CARD["member"], CARD["plan"], CARD["printed"], P["new_pattern"], CARD["member"]),
    "why": "Pam email 10/22/2026 23:57Z (insurance card photos, 'Independent - lives in own apt') - no AMD chart yet, listed per the 10/14 rule",
    "created": NOW, "updated": NOW},
    "append": {"notes": [{"who": "Claude", "text": "Created by the 9 PM ET 10/22 run from Pam's card photos (IMG_3633 / IMG_3634, HEIC). Card only: Florida Blue BlueOptions PPO, member %s, plan %s, printed %s. No chart, no DOB, no facility - nothing to do until the chart appears." % (CARD["member"], CARD["plan"], CARD["printed"]), "at": NOW}]}})
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
json.dump(board, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

add_md = f"""# captured_calls additions - {STAMP} (9 PM ET 10/22/2026 slot, fired 00:39Z 10/23, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after inside the engine pass 00:46-00:49Z);
GET /api/era/checks (era_list.py before/after, 0 checks); posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0);
Stedi 276/277 (claim_status_sweep.py pass 158, 17 asked); lookuppatient (admit_lookup_1023_0040.py, seven name patterns incl. tonight's
Pam card photos). No AdvancedMD write by this container. Vocabulary entries added: 0.
Lesson (not a call): a Pam admit sent as iPhone HEIC photos - ImageMagick's heic delegate refuses the HEVC codec in this container;
`python3 -m venv /tmp/heifenv && /tmp/heifenv/bin/pip install pillow pillow-heif` and a 6-line convert (register_heif_opener, exif_transpose,
save JPEG) reads them; never `pip install pillow-heif` into the main interpreter (it replaced the workspace Pillow and broke `from PIL import Image`
until `pip install --ignore-installed pillow==10.2.0`).
"""
open("outbox/captured_calls_additions_2026-10-23_0040UTC-9pmET-ehpa-cloud.md", "w").write(add_md)
print("rows", len(rows), "csv", csv_path, "ops", len(ops))
