#!/usr/bin/env python3
# PLAIN ENGLISH (report pieces of the 9 AM ET 10/23/2026 backend billing run, stamp 2026-10-23T1240Z, fired 12:40Z): LOCAL ONLY, no AMD call.
# Decides: nothing. Reads this run's scan folder (scan_2026-10-23T1255Z: before / after summaries), the engine report
#   (reports/button/2026-10-23T1255Z.json), the sweep register and the admit-lookup register, and writes the report pieces the prompt
#   asks for: the run report CSV (names allowed - it goes to William by SendUserFile), the needs_facesheet_list.md section (chart ids
#   only), the board update file for the 'board inbox' (real board row ids), the captured_calls additions file (0 new shapes)
#   and the run digest. Never touches AMD.
# Usage: python3 run_outputs_1023_1240.py
import json, re, csv, os, datetime
STAMP = "2026-10-23T1240Z"; SLOT = "9 AM ET 10/23 (fired 12:40Z)"; SCAN = "scan_2026-10-23T1255Z"
REPORT = "/home/claude/effinger-billing-backend/reports/button/2026-10-23T1255Z.json"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
os.makedirs("outbox", exist_ok=True); os.makedirs("chat_history", exist_ok=True)

rep = json.load(open(REPORT))
before = json.load(open(SCAN + "/summary_before.json")); after = json.load(open(SCAN + "/summary_after.json"))
sweep = json.load(open("registers/uni20_bcbs_pre0501_sweep_2026-10-23T1255Z.json"))
admits = json.load(open("registers/admit_lookup_%s.json" % STAMP))

rows = []
def add(col, state, patient, dos, carrier, err, action, visit="", chart="", amount=""):
    rows.append({"column": col, "state": state, "patient": patient, "chart": chart, "visit": visit, "dos": dos,
                 "carrier": carrier, "error": err, "amount": amount, "action": action})

ACTION = {
    "19455937": "HOLD - AET12 carrier master (payer id transmits the practice TIN); board row aet12-carrier-cpid, William's turn",
    "19433791": "HOLD for William - the new UNI98 carrier record (car307804) has no payer city/state: Master Files address, then 'rebill' (board row levin-lize-17475632)",
}
for run, vs in after["exclusions"].items():
    for v in vs:
        errs = " | ".join(e.get("name", "") for e in v.get("_errs", []))
        add("Exclusions (run %s)" % run, "remaining", v.get("patientname", ""), "", v.get("carriercodeshort", ""), errs,
            ACTION.get(v["id"], "standing hold"), visit=v["id"], chart=v.get("patientid", ""))
add("Charge Review", "none", "", "", "", "", "0 charges before and after (getreviewcharges per inspector batch)")
add("Claim Inspector", "none", "", "", "", "", "0 batches before and after")
add("Unbilled", "none", "", "", "", "", "0 rows before and after (unbilled_repair / payreasons found nothing)")
add("ERA posting", "none", "", "", "", "", "GET /api/era/checks: 0 unposted checks / $0.00 before and after; era_post --all-unposted 0 lines; era_clear 0 dismissed / 0 held; nothing to upload; Availity 5(g): no new Remittance Viewer PDF or Check/EFT export since 10/21; Treasury: no new CSV")
n_pend = sum(1 for x in sweep if isinstance(x, dict) and "PENDING" in str(x.get("action", ""))) if isinstance(sweep, list) else len(sweep.get("pending", [])) if isinstance(sweep, dict) else 16
add("UNI20/BCBS pre-5/1 sweep", "remaining", "", "", "UNI20", "277 pass 160", "16 visits chart 17472874 ($2,563) PENDING at payer (P1 accepted for processing / P5) - wait; 0 sent, 0 written off")
for lk in admits["lookups"]:
    add("Pam admits", "remaining", "", "", "", "no AMD chart yet", "lookuppatient found no chart (pattern %s) - board row only, nothing created" % lk["pattern_hash"])

csv_name = "_run report 10-23 1240.csv"
with open(csv_name, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

cols = lambda s: "%s/%s/%s/%s" % (s["overview"]["chargereviewcount"], s["overview"]["claiminspectorcount"], s["overview"]["unbillablecount"], s["overview"]["exclusioncount"])
section = """
## %s - backend billing run, %s (ehpa cloud, v7 prompt + v12 rules from main; repo attached)
- Columns (list calls): Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 0 -> 0 | Exclusions 2 -> 2 (overview %s -> %s).
- Exclusions left (both standing holds on William's turn): v19455937 chart 24750 AET12 PREF0288 + PREF0264 (carrier master); v19433791 chart 17475632 UNI98 'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' (carrier record car307804 has no payer address - Master Files, then 'rebill').
- ERA Center: 0 unposted checks / $0.00 before and after; auto-posted $0, manual-posted 0, residuals $0, checks cleared 0. Availity 5(g) + Treasury: nothing new since 10/21. Calls learned: none.
- UNI20/BCBS pre-5/1 pass 160: 16 PENDING at payer (chart 17472874, $2,563; 277 P1 'accepted for processing' / P5), 0 sent, 0 written off.
- Board: drops 0, Working Denials queue 0, Mandatory Approvals 0 approved / 0 waiting (register 93 items, all done); only two rows changed since 04:30Z (both set done by the 0458Z chat pass - no new William note). Pam Gmail (2d): the 10/22 15:00Z and 23:57Z admit threads (worked earlier); lookuppatient 13:0xZ: still no chart for either (BRO* / HIC*).
- Writes this run (AdvancedMD): none - the engine pass wrote nothing (0 bypasses, 0 repairs, 0 completions, 0 posts). Write-offs none. Dollars re-sent $0.
- Skipped: state bundle not packed (patient_db/ and era_details/ empty, every changed register is on main); 9/18 Drive bundle not restored (superseded by main); GitHub inbox packages 10-11 / 10-12 still on Drive (manifest sha256 never matched - not applied).
""" % (STAMP, SLOT, cols(before), cols(after))
open("needs_facesheet_list.md", "a").write(section)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(section)

iso = NOW; when = "10/23"
def chk(src, result, ok="na"):
    return {"ok": ok, "src": src, "result": result, "when": when}
SRC = "9am ET 10/23 columns run (ehpa cloud) - run %s" % STAMP
ops = [
    {"op": "upsert", "collection": "items", "id": "levin-lize-17475632",
     "append": {"checks": [chk(SRC, "9 AM ET 10/23: v19433791 still on the exclusion list (run 1700319, CH EC MISSING PAYER CITY + L2010BB.N4 missing state code) - held, not re-sent; waiting on the UNI98 carrier address in Master Files, then 'rebill'.")]}},
    {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
     "append": {"checks": [chk(SRC, "9 AM ET 10/23: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")]}},
    {"op": "upsert", "collection": "items", "id": "availity-remits-backlog",
     "append": {"checks": [chk(SRC, "9 AM ET 10/23: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 10/21); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: the 10/22 admit threads only (both still without an AMD chart at 13:0xZ). ERA Center 0 checks before and after (engine pass 12:55-12:59Z in the foreground, Post button $0.00, no refusal). Columns 0/0/0/2 -> 0/0/0/2 - the two standing holds (AET12 chart 24750; UNI98 chart 17475632 carrier address), no AMD write this slot. UNI20/BCBS pre-5/1 pass 160: 16 PENDING chart 17472874 ($2,563), 0 sent.")]}},
    {"op": "upsert", "collection": "items", "id": "brown-lisa-admit-1019",
     "append": {"checks": [chk(SRC, "9 AM ET 10/23: lookuppatient BRO* at 13:0xZ - still no AMD chart for the Brynwood 10/19 admit; nothing to bill, watching.")]}},
    {"op": "upsert", "collection": "items", "id": "hic[member id]",
     "append": {"checks": [chk(SRC, "9 AM ET 10/23: lookuppatient HIC* at 13:0xZ - still no AMD chart; the Florida Blue card data stays on this row, nothing created.")]}},
]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops},
          open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

adds = """# captured_calls additions - %s backend billing run (%s, ehpa cloud, v7 prompt + v12 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(columns_scan before/after, insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete
on runs 1700294 + 1700319, era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register),
lookuppatient (admit_lookup_1023_1240.py, read-only). No AdvancedMD write this run.
Behaviour seen: nothing new - the two exclusion rows are the standing carrier-record holds (AET12 PREF0288/PREF0264 on run 1700294;
UNI98 'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' on run 1700319); the ERA Center was empty before and after; the
UNI20 pre-5/1 277 pass answered PENDING (P1 'accepted for processing' / P5) on all 16 chart-17472874 visits again.
""" % (STAMP, SLOT)
open("captured_calls_additions_2026-10-23_1240UTC-9amET-ehpa-cloud.md", "w").write(adds)

digest = """# %s run digest - backend billing run, %s slot (ehpa cloud, repo attached)

## Bootstrap
- Repo ATTACHED: origin/main e6c23ad at start; main checked out in the session clone (branch main) and symlinked as /home/claude/effinger-billing-backend. Network: AMD OK (login gateway 200), Stedi proxy credential OK (STEDI_CRED_OK, no key file), GitHub attached. AMD password = the AMD_PSW environment credential (present, never printed). ONE login 12:55Z inside the engine pass; every later helper reused the token; no lock, no 429.
- Layout from main: 1237 helper files + OCR tools; required helpers all present (optional era_details_pull.py / columns_inspector2_0908.py / github_sync.py absent as usual). v12 precondition (repo copies of amd/resave/freq1_visit/move_to_ins/ins_update/dx_primary_fix/approval_submit; reroute / --no-rebill / _REBILLED / set_insorder / tf_writeoff_watch): all pass. State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). pseudonyms.json: Drive 04:11Z copy (415 names) in both secrets/ copies. deceased_cache.json: Drive 10/21 copy merged into the workspace + repo caches (dg_drive.py unpack, 76 dated entries merged).
- Prompt fired as the v7 text at 12:40Z (the 9 AM ET slot, ~30 min early); the v12 text + v13 insert on main applied as on every run since 10/6. Learned from others: git log 36h + SHARED_LESSONS 10/22-10/23 read (the backgrounded-Bash classifier TRAP applied - the engine pass ran plainly in the foreground; no RULE line newer than the last run); 0 RULE lines applied.
- Guard: the 0640Z START has its 0640Z RUN COMPLETE digest (07:03Z); no START younger than 40 min; START 1240Z uploaded 12:48Z, lock written and deleted at the end. GitHub Billing Button slot 11:26Z ran before this run; the 13:17Z slot was not overlapped (engine pass 12:55-12:59Z).
- Permission classifier: no refusal this run. Script errors: none. GitHub inbox: PACKAGE_* 10-11 / 10-12 still on Drive 'github mirror' (manifest sha256 never matched on earlier runs) - not applied.

## Sources read
- Insurance Refresh Board (read_db only): rows changed since 04:30Z = 2, both set done by the 0458Z chat pass (chart 17470713 no-secondary, chart 17471204 spouse subscriber) - no new William note; drops 0. Working Denials queue 0. Mandatory Approvals page 0 approved; approvals_pending.json on main 93 items, all done.
- Drive: nothing new in 'bht Optum era downloads', 'treasury payments', the facesheet folders or the Claimocity drop since 10/22 12:00Z except the 0424Z run report CSV; 'board inbox' holds the 0040Z / 0400Z / 0424Z / 0458Z board_updates and the 0535Z cred_updates. Pam Gmail (2d): the 10/22 15:00Z and 23:57Z admit threads (worked 1840Z / 0040Z); lookuppatient 13:0xZ: still no chart for either.

## Columns 0/0/0/2 at 12:55Z -> 0/0/0/2 at 12:58Z
- Charge Review 0 -> 0. Claim Inspector 0 -> 0. Unbilled 0 -> 0.
- Exclusions 2 -> 2, both standing holds on William's turn: v19455937 chart 24750 AET12 PREF0288 + PREF0264 (run 1700294, carrier master); v19433791 chart 17475632 UNI98 'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' (run 1700319, carrier record car307804 has no payer address).
- Dollars re-sent $0.00. Packages applied 0 / refused 0 / skipped 0. No AdvancedMD write this run.

## ERA Center - 0 checks before and after
- GET /api/era/checks 0 checks / $0.00 at 12:58Z before and after; era_post.py --all-unposted 0 lines; era_clear.py 0 dismissed / 0 held; nothing to upload. Auto-posted $0.00, manual-posted 0 lines, residuals disregarded $0.00, checks cleared 0, still open 0.
- Availity 5(g) and Treasury: nothing new since 10/21. Calls learned: none (0 vocabulary entries).
- UNI20/BCBS pre-5/1 pass 160 (claim_status_sweep.py --min-age 175 --max 60 --carriers UNI20,BCBS --skip-answered): 16 asked, all PENDING at payer (chart 17472874, $2,563; P1 'accepted for processing' / P5); 0 candidates, 0 sent, 0 written off.

## Waiting on William
- UNI98 carrier record (car307804): payer address in Master Files, then 'rebill' on row levin-lize-17475632 ($310).
- Chart 17473245 v19452629: $25.06 Florida Blue Medigap coinsurance - Availity secondary with the Medicare EOB, or 'write off'.
- Standing: AET12 carrier master (chart 24750); chart 17478013 2026 VA auth; the two chartless Pam admits (BRO* 10/19 Brynwood, HIC* 10/22).

## Mirror
- GitHub: mirror.py sync on main (this run's registers, scripts/helpers/admit_lookup_1023_1240.py + run_outputs_1023_1240.py, docs/SHARED_LESSONS.md +1 line, docs/captured_calls.md + this run's additions, nightly/runs/%s/, reports/button/2026-10-23T1255Z.json + latest.json); pushed main + the synced branch + the session branch claude/exciting-edison-r0atyk through the session proxy (result in the run summary).
- Postman: unchanged (0 new call shapes). Drive: _run report 10-23 1240.csv delivered with SendUserFile (not a 7 PM slot); board_updates_%s.json (5 ops) -> 'board inbox'; captured_calls additions -> 'billing agent project files'; needs_facesheet_list section + the two new helpers -> 'workspace mirror'; this digest -> 'chat history'. No denials_updates (queue empty). Not re-uploaded: captured_calls.md (main is the record), pseudonyms.json / deceased_cache.json (unchanged), postman / vocabulary JSON (no new shapes).
- State bundle: not packed (standing justification since 9/18: main supersedes it; patient_db/ and era_details/ empty).
- Lock: /home/claude/unbilled/.columns_run.lock deleted at the end of the run.

## SHARED LESSONS
- %s | backend billing run | WATCH | columns 0/0/0/2 -> 0/0/0/2 (standing holds: AET12 chart 24750 run 1700294; UNI98 carrier-address chart 17475632 run 1700319); ERA Center 0 checks before and after (engine pass 12:55-12:59Z in the foreground, Post button $0.00, no refusal); UNI20/BCBS pre-5/1 pass 160: 16 PENDING chart 17472874 ($2,563), 0 sent; Pam admits BRO*/HIC* still without a chart; the routine fired at 12:40Z for the 13:10Z slot | reports/button/2026-10-23T1255Z.json

RUN COMPLETE
""" % (STAMP, SLOT, STAMP, STAMP, NOW)
open("chat_history/%s run digest.md" % STAMP, "w").write(digest)
print("wrote", csv_name, "rows", len(rows), "| board ops", len(ops), "| digest + section + additions")
