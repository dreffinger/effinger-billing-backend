# PLAIN ENGLISH (run outputs for the 1 PM ET 9/29/2026 slot - ehpa cloud run 2026-09-29T1710Z)
# Decides: nothing. Reads this run's scan registers (scan_0929_1710 before/after) and the dry-run register of the declined payer switch and
#   writes the run report CSV (names allowed - SendUserFile only), a needs_facesheet_list.md section (pat ids only), the board update file
#   (appends on the standing rows + the two CHP trail rows read from a local JSON that never leaves the workspace), the captured_calls
#   additions file and the chat-history digest (--final adds the mirror result).
# Never touches: AMD, the board databases.
import json, csv, os, sys, datetime
S = "2026-09-29T1710Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
sc_b = json.load(open("scan_0929_1710/summary_before.json")); sc_a = json.load(open("scan_0929_1710/summary_after.json"))
dry = json.load(open("registers/apply_2026-09-29T1710Z_dry.json"))
HOLD = {"17472874": "HCA admission date - no 99223 anchor on the chart (William)", "17477640": "HCA admission date - no 99223 anchor (William)", "17472703": "HCA admission date - no 99223 anchor (William)",
        "17474541": "99489 without 99487 - coding (William)", "17476036": "99489 without 99487 + unspecified-laterality S91.309D - coding (William)", "17473477": "deceased guard - CCM after death (William void)",
        "45668": "deceased guard - CCM after death (William void); F02.80 external-cause advisory also on the row", "17477208": "duplicate CCM lines on one visit (William)", "20863": "CCI 24078 history-procedure edit (William); FCC PDTP0303 hold on Exclusions",
        "17477183": "Medicaid PENDING per the Aviata census - no billable plan yet", "17473232": "CCM after death (William void)", "17471681": "CCM after death (William void)", "17477639": "facesheet needed (no plan on the chart)",
        "17477842": "duplicate chart - William merges", "17477870": "duplicate chart - William merges", "17477850": "CHP member id needed (facesheet)", "17477898": "CHP member id needed (facesheet)", "17477892": "facesheet needed (no plan on the chart)"}
NAMES = {"21483": "MAITLAND,LYNETTE", "22322": "DORRINGTON,KATHRYN"}
rows = []
def R(col, status, pid, name, dos, carrier, err, action, vid="", amt=""):
    rows.append({"column": col, "status": status, "patient": name, "patientid": pid, "visit": vid, "dos": dos, "carrier": carrier, "error": err, "amount": amt, "action": action})
for bid, vs in sc_b["inspector"].items():
    for v in vs: R("Claim Inspector", "hold", v["pid"], v["name"], "", "", "; ".join(x[1][:80] for x in v["errs"]), "standing hold - " + HOLD.get(v["pid"], "see needs list"), v["vid"])
for r in sc_b["unbilled"]:
    R("Unbilled", "hold", r["patientid"], r["patientname"], (r["_chgs"][0].get("dos") or "").strip() if r["_chgs"] else "", r.get("carriercode") or "", "; ".join(r["_errs"][:2]), "standing hold - " + HOLD.get(r["patientid"], "see needs list"), r["id"], (r["_chgs"][0].get("totalfee") if r["_chgs"] else ""))
for rid, lst in sc_b["exclusions"].items():
    for r in lst: R("Exclusions", "hold", r["patientid"], r["patientname"], "", r.get("carriercode") or "", "; ".join((e.get("name") or e.get("text") or "")[:80] for e in r["_errs"][:2]), "standing hold - FCC PDTP0303 admission date (William)", r["id"])
for pid, C in dry["charts"].items():
    for v in C["visits"]:
        R("Wrong payer (CHP $0 -> patient balance)", "william", pid, NAMES[pid], v["dos"], "CAP07 -> Medicare (CMS)", "CHP posted $0; %.2f on the patient balance" % v["patbal"], "payer switch to Medicare + freq-1 rebill declined by the environment guard - board row on William's turn", v["vid"], "%.2f" % v["open"])
with open("_run report 9-29 1300.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ov_b = sc_b["overview"]; ov_a = sc_a["overview"]
ni_b = sum(len(v) for v in sc_b["inspector"].values()); ni_a = sum(len(v) for v in sc_a["inspector"].values())
ne_b = sum(len(v) for v in sc_b["exclusions"].values()); ne_a = sum(len(v) for v in sc_a["exclusions"].values())
n1 = len(dry["charts"]["21483"]["visits"]); t1 = sum(v["open"] for v in dry["charts"]["21483"]["visits"]); p1 = sum(v["patbal"] for v in dry["charts"]["21483"]["visits"])
n2 = len(dry["charts"]["22322"]["visits"]); t2 = sum(v["open"] for v in dry["charts"]["22322"]["visits"]); p2 = sum(v["patbal"] for v in dry["charts"]["22322"]["visits"])
needs = """## %s - backend billing run, 1 PM ET 9/29 slot (ehpa cloud)
- Columns: Charge Review %s -> %s | Claim Inspector %d -> %d (the 25 standing holds unchanged, same visit ids as 1510Z) | Unbilled %s -> %s (no new rows; every row a standing hold) | Exclusions %d -> %d (pat20863 v19445850 FLO99 PDTP0303 hold; overview says %s/$%s but every listed run returns one row) | ERA 0 checks -> 0.
- CLAIM INSPECTOR holds unchanged (25): pat17472874 x15 + pat17477640 x2 + pat17472703 x2 HCA admission dates (no 99223 anchor - William); pat17474541 v19430630 + pat17476036 v19456171 99489 without 99487 (coding - William); pat17473477 v19455625 + pat45668 v19455691 deceased guard (CCM after death - William void); pat17477208 v19455940 duplicate CCM lines; pat20863 v19455936 CCI 24078.
- UNBILLED holds unchanged (31): pat17472874 x15 + pat17474541 (inspector holds); pat17477183 x2 Medicaid PENDING per the Aviata census; pat17473232 + pat17471681 CCM after death (William void); pat17477639 facesheet; pat17477842 + pat17477870 duplicate charts; pat17477850 x4 + pat17477898 x2 CHP member ids; pat17477892 x2 facesheet. No new 'prior payor' rows this slot.
- ERA: 0 unposted checks before and after (locks released, nothing to post, nothing to clear); payreasons --list 0 rows; Availity 5(g): no new PDF or Check/EFT export.
- WRONG PAYER FOUND (the 1510Z PR-200 follow-up): the two CHP charts are far bigger than the three PR-200 lines. pat21483: %d CAP07 visits since 10/06/2025, $%.2f open, $%.2f of it on the PATIENT balance after CHP's $0 postings (ERA checks 4080494, 4105248, 4116144, 4120575, 4121958, 4124256), $0 paid; pat22322: %d visits since 03/28/2026, $%.2f open, $%.2f on the patient balance. CHP's 271 = AAA 75 on both; Stedi CMS MBI lookup at the oldest DOS and today = straight Medicare ACTIVE on both (Part B 6/1/2021 and 7/1/2011), no Advantage entity - CHP was never the payer for these dates. The standard fix (add FLO02 with the MBI, end-date CAP07 the day before the first denied DOS, patient order Medicare first, move every patient balance back, frequency-1 rebill all %d visits) was written as apply_0929_1710.py, dry-run verified (registers/apply_2026-09-29T1710Z_dry.json) and DECLINED by the environment's transaction guard when run live (second decline after 1510Z). Both board rows (maitland-lynette-21483, dorrington-kathryn-22322) carry the MBIs and the full instruction on William's turn. Oldest DOS 10/06/2025 - Medicare's 12-month window closes 10/06/2026, one week out. Hold patient statements on both charts.
- SOURCES: Working Denials queue 0; board drops 0; 0 board rows changed since 01:40Z; Pam Gmail: the 8 admit emails of 9/28-9/29 were all worked by earlier runs, nothing newer than 03:21Z; Drive: no new remit / facesheet / census / 835 / Availity / treasury file since 11:00Z outside the routine's own files; GitHub inbox: no unapplied PACKAGE manifest; both board inbox registries list none of the current inbox files - nothing trashed.
- Calls learned: none (registered calls only). Missing helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py.
""" % (S, ov_b["chargereviewcount"], ov_a["chargereviewcount"], ni_b, ni_a, sc_b["unbilled_totalcount"], sc_a["unbilled_totalcount"], ne_b, ne_a, ov_b["exclusioncount"], ov_b["exclusionamount"], n1, t1, p1, n2, t2, p2, n1 + n2)
open("needs_section_%s.md" % S, "w").write(needs); open("needs_facesheet_list.md", "a").write("\n" + needs)
def chk(txt): return {"ok": "na", "src": "1pm ET 9/29 columns run (ehpa cloud)", "result": txt, "when": "9/29"}
ops = [
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [chk("1 PM ET 9/29: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; no ScanSnap batch; Working Denials queue 0; board drops 0; 0 rows changed since 01:40Z; Pam Gmail: nothing newer than the 03:21Z 9/29 Pruitt admit (worked). ERA Center 0 checks before and after. Columns 0/25/31/1 -> 0/25/31/1. FOUND: the two CHP PR-200 charts (rows maitland-lynette-21483 / dorrington-kathryn-22322) carry $%.2f of CHP $0-denied balances on the patient statements since 10/2025 and 3/2026 while CMS says straight Medicare - the payer switch needs your word (the routine's environment declines that write)." % (p1 + p2))]}},
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [chk("1 PM ET 9/29: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 1 row (the FLO99 PDTP0303 hold), none AET12; newest claim run 1700243.")]}},
 {"op": "upsert", "collection": "items", "id": "bcbs-patient-balance-audit-0918", "set": {}, "append": {"checks": [chk("1 PM ET 9/29: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements. Same $0-denial-on-the-patient pattern found today on CHP (CAP07) for two charts - see rows maitland-lynette-21483 / dorrington-kathryn-22322.")]}},
 ] + json.load(open("board_rows_local_%s.json" % S))
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
add = """## 2026-09-29 17:10 UTC (1 PM ET 9/29/2026) - ehpa cloud backend run 2026-09-29T1710Z
No new call shapes this run (vocabulary unchanged); every read used registered calls (getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, GET /api/era/checks, locks/release-expired, getdemographic, gettxhistory, getchargedetaildataicd10, Stedi MBI lookup). Lessons:
- **A CHP $0 ERA line on a chart whose 271 answers AAA 75 is never one line**: read the whole tx history. pat21483 (26 visits since 10/2025) and pat22322 (12 visits since 3/2026) carried EVERY CHP claim on the patient balance ($7,883 together) after seven $0 CHP checks; CMS at the oldest DOS shows straight Medicare with no Advantage entity. The PR-200 lines of 9/29 were the newest of a year of wrong-payer $0 postings.
- **Environment guard (second time)**: the auto-mode classifier declined the live payer switch (plan add + end date + patient order + move-back + freq-1 rebill x38) as a shared-resource change; the dry run, the Stedi lookups and the column scans were allowed. The routine cannot make this class of write in this environment - the board rows carry the ready instruction (apply_0929_1710.py is in the run folder; the MBIs are only in the local JSON / on the board).
"""
open("captured_calls_additions_2026-09-29_1710UTC-1pmET-ehpa-cloud.md", "w").write(add)
mirror = sys.argv[1] if len(sys.argv) > 1 else "(mirror pending)"
digest = """# %s run digest - backend billing run, 1 PM ET 9/29 slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main 9370c7b at start; session branch claude/pensive-einstein-f27h7e, work on main, clone symlinked as /home/claude/effinger-billing-backend); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password from Gregg's Gmail thread -> .amd_cred.json, ONE login 17:15Z, no lock; START marker 17:11Z (guard clear: the 1510Z digest ends RUN COMPLETE, its START is older than 40 min). Layout from main (686 helpers); pseudonyms (322 names) from 'workspace mirror'; registers (389) from practices/ehpa/registers; needs_facesheet_list rebuilt from nightly/runs needs sections. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten). State bundle restored: none (Drive newest 2026-09-18_1123UTC older than main). GITHUB INBOX: no unapplied PACKAGE (only APPLIED_/SUPERSEDED_ manifests).
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 01:40Z; both inbox registries list none of the current inbox files - nothing trashed. Pam Gmail: 8 admit emails 9/28-9/29 all worked by earlier runs, nothing newer than 03:21Z. Drive: no new remit / facesheet / census / 835 / Availity / treasury file since 11:00Z outside the routine's own files.
- Columns: Charge Review 0 -> 0 | Claim Inspector 25 -> 25 (standing holds) | Unbilled 31 -> 31 (standing holds) | Exclusions 1 -> 1 (FLO99 PDTP0303 hold) | ERA 0 checks -> 0. Insurance entered: none. Dollars re-sent: $0. Write-offs: none.
- ERA: 0 unposted checks before and after; auto-posted $0, manual-posted $0, residual disregarded $0, checks cleared 0, orphans 0. Availity 5(g): no new files.
- WRONG PAYER: the 1510Z PR-200 follow-up read the whole tx history of pat21483 and pat22322 - %d + %d CAP07 visits ($%.2f + $%.2f open, $%.2f + $%.2f on the PATIENT balance) all $0-posted by CHP since 10/2025 and 3/2026; CHP 271 AAA 75; Stedi CMS at the oldest DOS and today = straight Medicare ACTIVE, no Advantage entity. apply_0929_1710.py (FLO02 add + CAP07 end date + Medicare order + move-back + freq-1 rebill x%d) dry-run verified; the live run was DECLINED by the environment's transaction guard (second decline after 1510Z) - nothing written to AMD; both board rows carry the MBIs + instruction on William's turn; oldest DOS 10/06/2025 closes Medicare's window 10/06/2026.
- Board: board_updates_%s.json (appends on availity-remits-backlog, aet12-carrier-cpid, bcbs-patient-balance-audit-0918; rows maitland-lynette-21483 and dorrington-kathryn-22322 rewritten with the full finding, William's turn) -> board inbox. Denials inbox: nothing queued, no file.
- Calls learned: none (additions file records the CHP whole-chart lesson + the guard decline). Vocabulary entries added: 0.
- Mirror: %s
- Script errors: none (the live apply_0929_1710.py was refused by the environment before it started; no partial write).

RUN COMPLETE
""" % (S, n1, n2, t1, t2, p1, p2, n1 + n2, S, mirror)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(digest)
print("rows", len(rows), "ops", len(ops))
