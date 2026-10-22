# PLAIN ENGLISH (run outputs for the 7 PM ET 10/17/2026 slot - ehpa cloud run 2026-10-17T2310Z)
# Decides: nothing. Reads this run's column scans (scan_2310/summary_before|after.json), the pass-132 sweep register and the
# precheck log, then writes the run report CSV, the needs_facesheet_list.md section (+ a copy for Drive), the board_updates
# inbox file (append-only checks, never set on status/need), the captured_calls additions file and the chat-history digest.
# Never touches: AMD, the board database.
import csv, json, datetime, collections
S = "2026-10-17T2310Z"; SRC = "7pm ET 10/17 columns run (ehpa cloud) - run %s" % S; W = "10/17"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
b = json.load(open("scan_2310/summary_before.json")); a = json.load(open("scan_2310/summary_after.json"))
def cnt(s):
    ex = s.get("exclusions", {}); nex = sum(len(v) for v in ex.values()) if isinstance(ex, dict) else len(ex)
    ins = s.get("inspector", {}); nin = sum(len(v) for v in ins.values()) if isinstance(ins, dict) else len(ins)
    return len(s.get("chargereview", [])), nin, len(s.get("unbilled", [])), nex
cb, ca = cnt(b), cnt(a); cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb + ca)
sw = json.load(open("registers/uni20_bcbs_pre0501_sweep_%s.json" % S))
byact = collections.Counter(r["action"].split(" - ")[0] for r in sw); asked = len(sw); askamt = sum(r["balance"] for r in sw)
NAMES = {"17478059": "[name]", "17478063": "[name]", "17478064": "EDGERTON,JOCELYN R", "17470713": "[name]", "24750": "chart 24750"}
VIS = {"19457778": ("17478059", "99223 10/12/2026"), "19457794": ("17478059", "99232 10/13/2026"), "19457783": ("17478063", "99223 10/12/2026"), "19457797": ("17478063", "99232 10/13/2026"), "19457784": ("17478064", "99223 10/12/2026"), "19457791": ("17478064", "99232 10/13/2026")}
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear", action="0 visits before and after")
add("claim inspector", "clear", action="0 batches before and after")
for r in a.get("unbilled", []):
    pid = str(r.get("patientid") or ""); vid = str(r.get("id") or "")
    add("unbilled", "remaining", NAMES.get(pid, "chart " + pid), VIS.get(vid, ("", ""))[1], "(no plan on chart - live getdemographic 23:2xZ: 0 insplans)", "; ".join(r.get("_errs") or []) or "Insurance order is missing on visit", "held - cascade exhausted 10/15, HCA Florida Capital facesheet (admit 10/12/2026) on William's turn; listed in tonight's 'current face sheets needed' email", visit=vid, amt="")
add("exclusions", "remaining", NAMES["17470713"], "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP Medicare Supplement member number from her card needed (William's turn); not rebilled", amt="")
add("exclusions", "remaining", NAMES["24750"], "", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 (v19455937)", "held - carrier master (board row aet12-carrier-cpid); not rebilled", visit="19455937")
add("era", "clear", action="ERA Center 0 checks $0.00 before and after; nothing uploaded, posted or cleared; Availity: no new PDF / Check-EFT export; Treasury: nothing new")
add("precheck (7pm)", "clear", action="precheck.py --days 3 --max 120: checked 0 patient/payer pairs (0 new lookups); 0 flagged")
for r in sw:
    add("uni20/bcbs pre-5/1 pass 132", "sweep", r.get("patient", ""), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit=str(r.get("visitid")), amt=r.get("balance"))
add("pam admits", "waiting", "[name] (Tapestry NA 10/15, re-sent 10/17); [name] (Brynwood NA 10/15); BEARDSLEY,[first] (Brynwood NA 10/15)", action="lookuppatient 23:2xZ: still no AMD chart for any of the three - nothing to attach to; waiting on the Claimocity feed (never create a chart from an email)")
with open("_run report 10-17 2310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
sec = """## %s - backend billing run, 7 PM ET 10/17/2026 slot (ehpa cloud) - 23:10-23:4xZ

Bootstrap: repo ATTACHED (origin/main 2fe4784 at start; session branch claude/pensive-einstein-npqxa4 = main; symlinked as /home/claude/effinger-billing-backend; layout 1098 helper files); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password from Gregg's thread into .amd_cred.json (chmod 600) + AMD_PSW environment credential present; ONE login 23:21Z, no lock, no 429. Guard: 2110Z START has its RUN COMPLETE digest (21:37Z), no newer START; own START uploaded 23:13Z, lock written. State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main. pseudonyms.json (406 names, Drive 10/8) in both secrets/; deceased_cache.json (Drive 10/16) merged (76 dated entries). Missing required helpers: none.

Sources: Insurance Refresh Board (read_db only): 0 rows changed since 19:00Z; drops 0; Working Denials queue 0; both drive_sync registries list no current inbox file - nothing trashed. Drive (recent-files list): nothing new in any watched folder after the 2110Z run's own files. Pam Gmail (2 days): the 10/17 16:18Z Aviata readmit (chart 17472553, worked 1710Z) and the 10/17 00:29Z Tapestry new admit; lookuppatient 23:2xZ: FLINTHAM (Tapestry 10/15), JENNER and BEARDSLEY (Brynwood 10/15) still have no AMD chart.

Columns (columns_scan before 23:21Z -> after 23:3xZ) %s (overview 27 / $4,235 lags the list):
- CHARGE REVIEW 0. CLAIM INSPECTOR 0 batches.
- UNBILLED 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 - v19457778 / v19457794, v19457783 / v19457797, v19457784 / v19457791 (99223 10/12 + 99232 10/13/2026, $421 each, $1,263) 'Insurance order is missing' - live getdemographic 23:2xZ: still 0 insplans on all three; cascade exhausted 10/15 (two are Capital Health Plan MA by Medicare's COB record, CHP answers 'subscriber not found' without the member id; one has no medical payer on file); no HCA / TMH / PCC facesheet, Pam email or board drop since; rows on William's turn unchanged; in tonight's face sheets email.
- EXCLUSIONS 26: 25 AARP Medigap secondary rows of chart 17470713 on claim run 1700302 (subscriber id not found - the AARP supplement member number from her card is the only fix, William's turn) + 1 AET12 PREF0288 chart 24750 v19455937 (carrier master hold). Nothing rebilled, nothing completed.
- Dollars re-sent $0. Rebills 0. Write-offs none. No AdvancedMD write this slot.

ERA (step 5): (a) nothing to upload (no new 835); (b) GET /api/era/checks = 0 checks / $0.00 before and after (era_post --all-unposted --dry); (c)-(e) nothing to post or clear. (g) Availity: no new PDF or Check/EFT export; Treasury nothing new.
7 PM extras: (a) precheck.py --days 3 --max 120 -> checked 0 patient/payer pairs (0 new lookups); 0 flagged. UNI20/BCBS pre-5/1 pass 132 (claim_status_sweep.py --min-age 169 --max 60 --carriers UNI20,BCBS --skip-answered <116 sweep registers, comma-joined>): 586 answered visits skipped, %d asked ($%.2f): %s - 16 PENDING chart 17472874 ($2,563; 15 'accepted for processing' + the 03/04/2026 visit 'adjudicated, awaiting payment cycle') + 1 UNKNOWN chart 17475632 v19433791 ($310, empty status), 0 candidates, 0 sent, 0 written off; register registers/uni20_bcbs_pre0501_sweep_%s.json. (c) 'current face sheets needed' email sent to dreffinger@gmail.com (charts 17478059 / 17478063 / 17478064 facesheets; chart 17470713 AARP member number). (d) run report CSV also in Drive 'bht hca facesheets'.

Waiting on William: HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); AARP Medicare Supplement member number for chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); three 10/15 Pam admits without an AMD chart; the standing items of earlier digests unchanged.
Script errors: none. Calls learned: 0 new shapes (0 vocabulary entries).
""" % (S, cols, asked, askamt, dict(byact), S)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt: {"checks": [{"ok": "na", "result": txt, "src": SRC, "when": W}]}
hold = "7 PM ET 10/17: chart still has 0 insurance plans (live getdemographic 23:2xZ; Unbilled list 23:21Z and 23:3xZ); no HCA / TMH / PCC facesheet, Pam email or board drop since the 10/15 cascade; the two HCA visits (99223 10/12 + 99232 10/13/2026, $421) stay in Unbilled 'Insurance order is missing' - your facesheet (HCA Florida Capital, admit 10/12/2026) is still the only source; listed in tonight's 'current face sheets needed' email."
ops = [{"op": "update", "collection": "items", "id": i, "append": chk(hold)} for i in ("madison-digby-[first]-17478059", "[name]-17478063", "edgerton-jocelyn-17478064")]
ops.append({"op": "update", "collection": "items", "id": "poulter-ellery-gwen-denials", "append": chk("7 PM ET 10/17: the 25 AARP Medigap secondary rejections of claim run 1700302 stay on the exclusion list; held, not rebilled - the AARP Medicare Supplement member number from her card is still the only fix; in tonight's face sheets email.")})
ops.append({"op": "update", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("7 PM ET 10/17: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937) stays on the list, not rebilled; carrier master still unchanged.")})
ops.append({"op": "update", "collection": "items", "id": "availity-remits-backlog", "append": chk("7 PM ET 10/17: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive recent-files list: nothing after the 2110Z run's own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; 0 rows changed since 19:00Z; Pam Gmail: nothing newer than the 16:18Z Aviata readmit (worked 1710Z); FLINTHAM / JENNER / BEARDSLEY (10/15 admits) still have no AMD chart. ERA Center 0 checks before and after. Columns %s - every row a standing hold; no AMD write this slot. Precheck --days 3: 0 pairs, 0 flagged. UNI20/BCBS pre-5/1 pass 132: 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632, 0 sent. 'current face sheets needed' email sent." % cols)})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
open("captured_calls_additions_2026-10-17_2310UTC-7pmET-ehpa-cloud.md", "w").write("""# captured_calls additions - backend billing run %s (7 PM ET 10/17/2026, ehpa cloud)

No new call shapes this run. Calls used, all already in the registry: login (one attempt), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus + getclaimexclusioncharges (clearinghouse=1 payer=1; columns_scan.py before/after), getdemographic x3 (live insplan re-check of the zero-plan charts), lookuppatient x3 (admit_lookup_1017_2310.py), GET /api/era/checks (0 checks; era_post.py --all-unposted --dry), precheck.py --days 3 (0 pairs), massrebillsearch + Stedi 276/277 claim status x17 (claim_status_sweep.py pass 132, --skip-answered with the comma-joined sweep registers). No AdvancedMD write.
""" % S)
dig = """# %s run digest - backend billing run, 7 PM ET 10/17/2026 (ehpa cloud, repo attached)

## Bootstrap
- Repo attached: main 2fe4784 at start (session branch claude/pensive-einstein-npqxa4 identical; main checked out; /home/claude/effinger-billing-backend symlinked to the session clone). Network: AMD OK, Stedi proxy credential OK (STEDI_CRED_OK, no key file), GitHub attached. AMD password: Gregg's thread -> .amd_cred.json (chmod 600); AMD_PSW environment credential also present. One login 23:21Z, no lock, no 429.
- State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main (1098 helper files laid out). pseudonyms.json (406 names, Drive 10/8 copy) in both secrets/. deceased_cache.json (Drive 10/16) merged into the workspace cache (76 dated entries; the repo copy kept scrubbed). Missing required helpers: none.
- Guard: 2110Z START has its RUN COMPLETE digest (21:37Z); no newer START; own START uploaded 23:13Z, lock written, deleted at the end.

## Sources read
- Insurance Refresh Board (read_db only): 0 rows changed since 19:00Z; drops 0. Working Denials queue 0. Both drive_sync registries: no current inbox file in the applied maps - nothing trashed.
- Drive (recent-files list): nothing new in any watched folder after the 2110Z run's own files. Pam Gmail (2 days): the 16:18Z Aviata readmit (chart 17472553, worked 1710Z) and the 10/17 00:29Z Tapestry new admit; lookuppatient 23:2xZ: the three 10/15 admits (Tapestry x1, Brynwood x2) still have no AMD chart (registers/admit_lookup_%s.json).

## Columns (list calls) %s
- Charge Review 0. Claim Inspector 0 batches.
- Unbilled 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (live getdemographic 23:2xZ: still 0 insplans; William's turn, HCA Florida Capital facesheets admit 10/12/2026, $1,263; checks appended through the board inbox; in tonight's face sheets email).
- Exclusions 26 (overview 27 / $4,235 lags): the 25 AARP rows of chart 17470713 on run 1700302 (member number on William's turn) and the AET12 chart-24750 PREF0288 hold - unchanged, nothing rebilled.
- Dollars re-sent $0. Rebills 0. Write-offs none. No AdvancedMD write this slot.

## ERA Center - 0 checks $0.00 before -> 0 checks $0.00 after
- Nothing uploaded (no new 835), nothing posted, nothing cleared. Availity 5(g): no new PDF or Check/EFT export; Treasury nothing new. Calls learned: none (0 vocabulary entries).

## 7 PM extras
- precheck.py --days 3 --max 120: checked 0 patient/payer pairs (0 new lookups); 0 flagged.
- UNI20/BCBS pre-5/1 pass 132 (--min-age 169 --max 60 --carriers UNI20,BCBS --skip-answered = 116 sweep registers comma-joined): 586 answered visits skipped, %d asked ($%.2f): 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632 v19433791 ($310); 0 candidates, 0 sent, 0 written off. Register practices/ehpa/registers/uni20_bcbs_pre0501_sweep_%s.json on main.
- 'current face sheets needed' email sent to dreffinger@gmail.com (3 HCA facesheets + the AARP member number). Run report CSV also in Drive 'bht hca facesheets'.

## Script errors
- None.

## Waiting on William
- HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263).
- AARP Medicare Supplement member number for chart 17470713 (25 secondary claims on run 1700302).
- AET12 carrier master (chart 24750); three 10/15 Pam admits without an AMD chart; the standing items of earlier digests unchanged.

## Mirror
- GitHub: MIRROR_GITHUB
- Postman: unchanged (no new call shapes; docs/postman_effinger_amd.json / api_vocabulary.json unchanged - not re-uploaded). The Drive registry copy is carried by captured_calls_additions_2026-10-17_2310UTC-7pmET-ehpa-cloud.md -> 'billing agent project files'.
- Drive: needs_facesheet_list_section_%s.md -> 'workspace mirror'; board_updates_%s.json (6 ops, all appends) -> 'board inbox'; no denials_updates (queue empty); this digest -> 'chat history'; run report CSV delivered with SendUserFile and to 'bht hca facesheets'.
- State bundle: skipped with the standing justification (Drive bundle 2026-09-18 superseded by main; patient_db/ and era_details/ empty this run; the registers that changed are on main; the connector's typed-text transport cannot carry the parts byte-exact). Deceased cache unchanged - not re-uploaded.

## SHARED LESSONS
- 2026-10-17T23:40Z | backend billing run | WATCH | columns %s, ERA Center 0 checks, precheck 0 flags, UNI20/BCBS pre-5/1 pass 132: 16 PENDING chart 17472874 + 1 UNKNOWN chart 17475632, 0 sent; no AMD write | nightly/runs/%s

RUN COMPLETE
""" % (S, S, cols, asked, askamt, S, S, S, cols, S)
import os; os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(dig)
print(cols, "| sweep", asked, dict(byact))
