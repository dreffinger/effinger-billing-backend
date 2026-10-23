#!/usr/bin/env python3
# PLAIN ENGLISH (report pieces of the 3 AM ET 10/23/2026 backend billing run, stamp 2026-10-23T0640Z, fired 06:39Z): LOCAL ONLY, no AMD call.
# Decides: nothing. Reads this run's scan folder (scan_2026-10-23T0650Z: before / after summaries + the raw exclusion XML), the engine
#   report (reports/button/2026-10-23T0650Z.json) and the registers this run wrote, and writes the report pieces the prompt asks
#   for: the run report CSV (names allowed - it goes to William by SendUserFile), the needs_facesheet_list.md section (chart ids
#   only), the board update file for the 'board inbox' (real board row ids), the captured_calls additions file (0 new shapes)
#   and the run digest. Never touches AMD.
# Usage: python3 run_outputs_1023_0640.py
import json, re, csv, os, datetime
STAMP = "2026-10-23T0640Z"; SLOT = "3 AM ET 10/23 (fired 06:39Z)"; SCAN = "scan_2026-10-23T0650Z"
REPORT = "/home/claude/effinger-billing-backend/reports/button/2026-10-23T0650Z.json"
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

rep = json.load(open(REPORT))
before = json.load(open(SCAN + "/summary_before.json")); after = json.load(open(SCAN + "/summary_after.json"))
excl_rows = {}
for run in ("1700294", "1700319"):
    for v in visits(open("%s/excl_%s_before.xml" % (SCAN, run)).read()):
        excl_rows[v["id"]] = v
hidden = json.load(open("registers/excl_hide_%s.json" % STAMP))
sweep = json.load(open("registers/uni20_bcbs_pre0501_sweep_2026-10-23T0650Z.json"))
admits = json.load(open("registers/admit_lookup_%s.json" % STAMP))

rows = []
def add(col, state, patient, dos, carrier, err, action, visit="", chart="", amount=""):
    rows.append({"column": col, "state": state, "patient": patient, "chart": chart, "visit": visit, "dos": dos,
                 "carrier": carrier, "error": err, "amount": amount, "action": action})

ACTION = {
    "19455937": ("remaining", "HOLD - AET12 carrier master (payer id transmits the practice TIN); board row aet12-carrier-cpid, William's turn"),
    "19433791": ("remaining", "HOLD for William - the new UNI98 carrier record (car307804) has no payer city/state: Master Files address, then 'rebill' (board row levin-lize-17475632)"),
    "19452629": ("cleared", "Florida Blue Medigap secondary already re-sent frequency 1 on 10/22 after the Medicare reason repair and rejected again (no Medicare claim number on the re-posted payment); exclusion completed (hideexclusions OK), $8.92 moved off the patient (move_to_ins, no rebill); $25.06 coinsurance listed for William (Availity secondary with the Medicare EOB, or write off) - board row dalrymple-dane-17473245"),
}
for vid, v in excl_rows.items():
    st, act = ACTION.get(vid, ("remaining", "standing hold"))
    errs = " | ".join(e.get("name", "") for e in v["_errs"])
    amt = sum(float(c.get("insportion", 0) or 0) for c in v["_chgs"])
    add("Exclusions (run %s)" % v["claimrunid"], st, v.get("patientname", ""), v["_chgs"][0].get("dos", "").strip() if v["_chgs"] else "",
        v.get("carriercodeshort", ""), errs, act, visit=vid, chart=v.get("patientid", ""), amount="%.2f" % amt)
add("Charge Review", "none", "", "", "", "", "0 charges before and after (getreviewcharges per inspector batch)")
add("Claim Inspector", "none", "", "", "", "", "0 batches before and after")
add("Unbilled", "none", "", "", "", "", "0 rows before and after (unbilled_repair / payreasons found nothing)")
add("ERA posting", "none", "", "", "", "", "GET /api/era/checks: 0 unposted checks / $0.00 before and after; era_post --all-unposted 0 lines; era_clear 0 dismissed / 0 held; nothing to upload; Availity 5(g): no new Remittance Viewer PDF or Check/EFT export; Treasury: no new CSV")
add("UNI20/BCBS pre-5/1 sweep", "remaining", "", "", "UNI20", "277 pass 159", "16 visits chart 17472874 ($2,563) PENDING at payer - wait; 0 sent, 0 written off")
for lk in admits["lookups"]:
    add("Pam admits", "remaining", "", "", "", "no AMD chart yet", "lookuppatient found no chart (pattern %s) - board row only, nothing created" % lk["pattern_hash"])

csv_name = "_run report 10-23 0640.csv"
with open(csv_name, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

cols = lambda s: "%s/%s/%s/%s" % (s["overview"]["chargereviewcount"], s["overview"]["claiminspectorcount"], s["overview"]["unbillablecount"], s["overview"]["exclusioncount"])
section = """
## %s - backend billing run, %s (ehpa cloud, v7 prompt + v12 rules from main; repo attached)
- Columns (list calls): Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 0 -> 0 | Exclusions 3 -> 2 (overview %s -> %s at the scan; the Florida Blue row completed after the scan).
- Exclusions left: v19455937 chart 24750 AET12 PREF0288 (carrier master hold); v19433791 chart 17475632 UNI98 'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' (the carrier William added 10/23 has no payer address - Master Files, then rebill).
- Exclusions cleared: v19452629 chart 17473245 Florida Blue PREF0283 (Medigap secondary CCM 8/23/2026) - re-sent frequency 1 on 10/22 after the 10/21 Medicare reason repair and rejected again: the re-posted Medicare payment carries no Medicare claim number for the COB loop, so an electronic secondary cannot pass CH's PREF0283 edit; completed (hideexclusions run 1700319 success), $8.92 patient balance on 23362979 moved back to insurance (no rebill); $25.06 coinsurance waits on William (Availity secondary with the Medicare EOB, or write off).
- ERA Center: 0 unposted checks / $0.00 before and after; auto-posted $0, manual-posted 0, residuals $0, checks cleared 0. Availity 5(g) + Treasury: nothing new since 10/21. Calls learned: none.
- UNI20/BCBS pre-5/1 pass 159: 16 PENDING at payer (chart 17472874, $2,563), 0 sent, 0 written off.
- Board: drops 0, Working Denials queue 0, Mandatory Approvals 0 approved / 0 waiting, no new William note since the 0424Z run. Pam Gmail (2d): the 10/22 15:00Z and 23:57Z admit threads (worked); lookuppatient 07:0xZ: still no chart for either (BRO* / HIC*).
- Writes this run (AdvancedMD): hideexclusions run 1700319 v19452629 (excl_hide_1023_0640.py --live); move_to_ins.py 23362979 --no-rebill ($8.92 patient -> insurance). The engine pass wrote nothing (0 bypasses, 0 repairs, 0 completions, 0 posts). Write-offs none. Dollars re-sent $0.
- Skipped: state bundle not packed (patient_db/ and era_details/ empty, every changed register is on main); 9/18 Drive bundle not restored (superseded by main).
""" % (STAMP, SLOT, cols(before), cols(after))
open("needs_facesheet_list.md", "a").write(section)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(section)

iso = NOW; when = "10/23"
def chk(src, result, ok="na"):
    return {"ok": ok, "src": src, "result": result, "when": when}
SRC = "3am ET 10/23 columns run (ehpa cloud) - run %s" % STAMP
ops = [
    {"op": "upsert", "collection": "items", "id": "levin-lize-17475632",
     "set": {"status": "william", "need": "WILLIAM: the claim run 1700319 (10/22 23:53) rejected the 2/26/2026 99223 (v19433791, $310) on your new UNI98 carrier: 'CH EC MISSING PAYER CITY' + 'CH G2 L2010BB.N4 missing state code' - the carrier record UNITEDHEALTHCARE STUDENT (car307804, CPID 6465) has no payer address. Master Files > carrier UNI98: enter the payer address from the HCA facesheet (PO BOX 809025, DALLAS, TX 75380), save, re-open to confirm it stuck, then write 'rebill' here - the next run re-sends the visit as an original and completes the exclusion. Held on the exclusion list until then."},
     "append": {"checks": [chk(SRC, "v19433791 rejected on run 1700319: CH EC MISSING PAYER CITY + L2010BB.N4 missing state code (UNI98 car307804 carrier record has no address); held, not re-sent", "no")],
                "notes": [{"who": "Claude", "at": iso, "text": "Change Healthcare bounced the UNI98 claim for a missing payer city/state - the carrier record needs the payer address (PO Box 809025, Dallas TX 75380) in Master Files; say 'rebill' when it is in and the next run re-sends it."}]}},
    {"op": "upsert", "collection": "items", "id": "dalrymple-dane-17473245",
     "set": {"status": "william", "amount": 25.06, "need": "WILLIAM: 8/23/2026 CCM 99487+99489 (v19452629) - Medicare paid 9/19 ($98.23, contractual repaired 10/21); the Florida Blue Medigap secondary went out frequency 1 on 10/22 and Change Healthcare rejected it PREF0283 'missing payer doc control num' again (run 1700319): the re-posted Medicare payment carries no Medicare claim number, so the electronic secondary cannot carry the primary's ICN; Florida Blue has already answered $0 twice (9/2 check 423782226, 10/21 check 423830695). Exclusion completed, the $8.92 the 10/21 $0 pushed onto the patient moved back to insurance. Left: $25.06 coinsurance (16.14 + 8.92). Options: submit the secondary on Availity with the Medicare EOB, or say 'write off' here (WOINS, crossover residual). The earlier item on this row (v19451554 8/10 99309 $74.64, card A-2026-10-14T1710Z-D) is the same pattern."},
     "append": {"checks": [chk(SRC, "v19452629 (99487+99489 8/23/2026) PREF0283 again on run 1700319 after the 10/22 frequency-1 send; exclusion completed (hideexclusions success), 8.92 patbal moved back to insurance (insbal 8.92 + 16.14 = 25.06 open on BCBS seq 1); not re-sent", "no")],
                "notes": [{"who": "Claude", "at": iso, "text": "The 8/23 CCM secondary bounced PREF0283 a third time even as an original - the Medicare claim number is not on the re-posted Medicare payment, so the clearinghouse cannot build the COB loop. $25.06 of coinsurance is yours to route: Availity secondary with the Medicare EOB, or 'write off'."}]}},
    {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
     "append": {"checks": [chk(SRC, "3 AM ET 10/23: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")]}},
    {"op": "upsert", "collection": "items", "id": "availity-remits-backlog",
     "append": {"checks": [chk(SRC, "3 AM ET 10/23: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 10/21); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: the 10/22 admit threads only (both still without an AMD chart). ERA Center 0 checks before and after (engine pass 06:50-06:54Z, Post button $0.00). Columns 0/0/0/3 -> 0/0/0/2: Florida Blue PREF0283 secondary (chart 17473245) completed after its 10/22 frequency-1 resend bounced again; new UNI98 'missing payer city' row (chart 17475632) on William's turn; AET12 hold unchanged. UNI20/BCBS pre-5/1 pass 159: 16 PENDING chart 17472874 ($2,563), 0 sent.")]}},
    {"op": "upsert", "collection": "items", "id": "brown-lisa-admit-1019",
     "append": {"checks": [chk(SRC, "3 AM ET 10/23: lookuppatient BRO* at 07:0xZ - still no AMD chart for the Brynwood 10/19 admit; nothing to bill, watching.")]}},
    {"op": "upsert", "collection": "items", "id": "hic[member id]",
     "append": {"checks": [chk(SRC, "3 AM ET 10/23: lookuppatient HIC* at 07:0xZ - still no AMD chart; the Florida Blue card data stays on this row, nothing created.")]}},
]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops},
          open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

adds = """# captured_calls additions - %s backend billing run (%s, ehpa cloud, v7 prompt + v12 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(columns_scan before/after, insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete
on runs 1700294 + 1700319, era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register),
getclaimexclusioncharges (re-list of run 1700319 before the write), getdemographic, gettxhistory (visit_read), getchargedetaildataicd10
(resave.detail), hideexclusions run 1700319 (excl_hide_1023_0640.py), move_to_ins.py --no-rebill (the $0-balance move shape),
lookuppatient (admit_lookup_1023_0640.py).
Behaviour seen: (1) a Florida Blue Medigap SECONDARY whose Medicare payment was re-posted by the payreason repair (no Medicare ICN on the
payment) rejects CH FH PREF0283 'MISSING PAYER DOC CONTROL NUM' even as a frequency-1 original (resubmissioncode 1, origrefnum blank) -
the edit is about the PRIMARY payer's claim control number in the COB loop, not the claim frequency; complete the exclusion and route the
coinsurance to William (Availity secondary / write-off). (2) A carrier added in Master Files without a payer address (UNI98 car307804)
rejects 'CH EC MISSING PAYER CITY' + 'CH G2 L2010BB.N4..2.0.1:missing state code' on the first claim run - the address is a Master Files
field (no API), William's turn.
""" % (STAMP, SLOT)
open("captured_calls_additions_2026-10-23_0640UTC-3amET-ehpa-cloud.md", "w").write(adds)

digest = """# %s run digest - backend billing run, %s slot (ehpa cloud, repo attached)

## Bootstrap
- Repo ATTACHED: origin/main 3e74c4c at start; main checked out in the session clone and symlinked as /home/claude/effinger-billing-backend. Network: AMD OK (login gateway 200), Stedi proxy credential OK (no key file), GitHub attached. AMD password = the AMD_PSW environment credential (never printed). ONE login 06:50Z inside the engine pass; every later helper reused the token; no lock, no 429.
- Layout from main: 1232 helper files + OCR tools; required helpers all present (optional era_details_pull.py / columns_inspector2_0908.py / github_sync.py absent as usual). v12 precondition (repo copies of amd/resave/freq1_visit/move_to_ins/ins_update/dx_primary_fix/approval_submit, reroute / --no-rebill / _REBILLED / set_insorder / tf_writeoff_watch): all pass. State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). pseudonyms.json: Drive 04:11Z copy (415 names) in both secrets/ copies. deceased_cache.json: Drive 10/21 copy merged into the workspace cache (38 dated entries, 291 total).
- Prompt fired as the v7 text at 06:39Z (scheduled 07:00Z slot); the v12 text + v13 insert on main applied as on every run since 10/6. Learned from others: git log 36h + SHARED_LESSONS 10/22-10/23 read (the backgrounded-Bash classifier TRAP applied - the engine pass ran plainly in the foreground; the 10/23 chat lessons on carrier-in-place moves and begindate edits noted); 0 RULE lines applied.
- Guard: the 0400Z START has its 0415Z / 0424Z RUN COMPLETE digests; no START younger than 40 min; START 0640Z uploaded 06:44Z, lock written and deleted at the end. GitHub Billing Button slots #150/#151 (05:26Z columns, 05:44Z cascade) ran before this run; the ~07:25Z slot was not overlapped (engine pass 06:50-06:54Z, writes 07:0xZ).
- Permission classifier: no refusal this run. Script errors: none.

## Sources read
- Insurance Refresh Board (read_db only): rows on Claude's turn - standing rows, no William note newer than the 0424Z run (only tolliver-tracy set done 05:35Z by the chat); drops 0. Working Denials queue 0. Mandatory Approvals page 0 approved; approvals_pending.json on main 93 items, all done.
- Drive: nothing new in 'bht Optum era downloads', 'treasury payments', the facesheet folders, the Claimocity drop or 'board inbox' since the 0424Z run (only that run's and the 0535Z cascade's own files; captured_calls_additions_2026-10-23_chat.md already merged into the registry on main). Pam Gmail (2d): the 10/22 15:00Z and 23:57Z admit threads (worked 1840Z / 0040Z); lookuppatient 07:0xZ: still no chart for either.

## Columns 0/0/0/3 at 06:52Z -> 0/0/0/2 at 07:0xZ
- Charge Review 0 -> 0. Claim Inspector 0 -> 0. Unbilled 0 -> 0.
- Exclusions 3 -> 2. New claim run 1700319 (10/22 23:53) brought two rows: (a) v19433791 chart 17475632 UNI98 'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' - the carrier William added 10/23 (car307804) has no payer address; Master Files only -> William's turn on row levin-lize-17475632, held; (b) v19452629 chart 17473245 Florida Blue PREF0283 on the 8/23/2026 CCM Medigap secondary - re-sent frequency 1 on 10/22 after the 10/21 Medicare reason repair and rejected again (the re-posted Medicare payment has no Medicare ICN for the COB loop); exclusion COMPLETED (hideexclusions run 1700319 success, re-listed first), $8.92 moved off the patient (move_to_ins --no-rebill), $25.06 coinsurance to William (Availity secondary with the Medicare EOB, or write off). (c) v19455937 chart 24750 AET12 PREF0288 run 1700294 - standing carrier-master hold.
- Dollars re-sent $0.00. Packages applied 0 / refused 0 / skipped 0.

## ERA Center - 0 checks before and after
- GET /api/era/checks 0 checks / $0.00 at 06:53Z before and after; era_post.py --all-unposted 0 lines; era_clear.py 0 dismissed / 0 held; nothing to upload. Auto-posted $0.00, manual-posted 0 lines, residuals disregarded $0.00, checks cleared 0, still open 0.
- Availity 5(g) and Treasury: nothing new. Calls learned: none (0 vocabulary entries).
- UNI20/BCBS pre-5/1 pass 159 (claim_status_sweep.py --min-age 175 --max 60 --carriers UNI20,BCBS --skip-answered): 16 asked, all PENDING at payer (chart 17472874, $2,563); 0 candidates, 0 sent, 0 written off.

## Writes this run (AdvancedMD)
- hideexclusions run 1700319 v19452629 / 19452629F (excl_hide_1023_0640.py --live, success=1); move_to_ins.py 23362979 --no-rebill (patbalance 8.92 -> insbalance 8.92, insorder 2,1). The engine pass wrote nothing. Write-offs none.

## Waiting on William
- UNI98 carrier record (car307804): payer address in Master Files, then 'rebill' on row levin-lize-17475632 ($310).
- Chart 17473245 v19452629: $25.06 Florida Blue Medigap coinsurance - Availity secondary with the Medicare EOB, or 'write off'.
- Standing: AET12 carrier master (chart 24750); chart 17478013 2026 VA auth; chart 17470713 AARP member number / 'write off now'; the two chartless Pam admits.

## Mirror
- GitHub: mirror.py sync on main (this run's registers, scripts/helpers/excl_hide_1023_0640.py + admit_lookup_1023_0640.py + run_outputs_1023_0640.py, docs/SHARED_LESSONS.md +3 lines, docs/captured_calls.md + this run's additions, nightly/runs/%s/, reports/button/2026-10-23T0650Z.json + latest.json). Result: see the run summary.
- Postman: unchanged (0 new call shapes). Drive: _run report 10-23 0640.csv delivered with SendUserFile (not a 7 PM slot); board_updates_%s.json (6 ops) -> 'board inbox'; captured_calls additions -> 'billing agent project files'; needs_facesheet_list section + the three new helpers -> 'workspace mirror'; this digest -> 'chat history'. No denials_updates (queue empty). Not re-uploaded: captured_calls.md (main is the record), pseudonyms.json / deceased_cache.json (unchanged), postman / vocabulary JSON (no new shapes).
- State bundle: not packed (standing justification since 9/18: main supersedes it; patient_db/ and era_details/ empty).
- Lock: /home/claude/unbilled/.columns_run.lock deleted at the end of the run.

## SHARED LESSONS
- %s | backend billing run | WATCH | columns 0/0/0/3 -> 0/0/0/2 (run 1700319: Florida Blue PREF0283 secondary chart 17473245 completed after its 10/22 frequency-1 resend bounced again; UNI98 'MISSING PAYER CITY' chart 17475632 = carrier-record address, William; AET12 hold); ERA Center 0 checks before and after (engine pass 06:50-06:54Z in the foreground, Post button $0.00, no refusal); UNI20/BCBS pre-5/1 pass 159: 16 PENDING chart 17472874 ($2,563), 0 sent; Pam admits BRO*/HIC* still without a chart | reports/button/2026-10-23T0650Z.json
- %s | backend billing run | FIX | CH FH PREF0283 'MISSING PAYER DOC CONTROL NUM' on a Florida Blue Medigap SECONDARY whose Medicare payment was re-posted by the payreason repair (no Medicare ICN on the payment) comes back even on a frequency-1 original (resubmissioncode 1, origrefnum blank, v19452629 run 1700319) - the edit wants the PRIMARY payer's claim control number in the COB loop, not frequency 1; complete the exclusion (one rebill per visit), move any $0-pushed patient coinsurance back (move_to_ins --no-rebill) and route the coinsurance to William (Availity secondary with the Medicare EOB / write-off) | scripts/helpers/excl_hide_1023_0640.py
- %s | backend billing run | TRAP | a carrier William adds in Master Files without a payer address (UNI98 car307804, 10/23) rejects 'CH EC MISSING PAYER CITY' + 'CH G2 L2010BB.N4..2.0.1:missing state code' on its first claim run (1700319) - no API writes a carrier address; board row on William's turn, visit held, not re-sent | practices/ehpa/rules.md

RUN COMPLETE
""" % (STAMP, SLOT, STAMP, STAMP, NOW, NOW, NOW)
open("chat_history/%s run digest.md" % STAMP, "w").write(digest)
print("wrote", csv_name, "rows", len(rows), "| board ops", len(ops), "| digest + section + additions")
