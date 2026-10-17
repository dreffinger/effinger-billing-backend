# PLAIN ENGLISH (run outputs for the 5 PM ET 10/17/2026 slot - ehpa cloud run 2026-10-17T2110Z)
# Decides: nothing. Reads this run's column scans (scan_2026-10-17T2110Z/summary_before|after.json) and the pass-131
# sweep register, then writes the run report CSV, the needs_facesheet_list.md section (+ a copy for Drive), the
# board_updates inbox file (append-only checks, never set on status/need), the captured_calls additions file and the
# chat-history digest. Never touches: AMD, the board database.
import csv, json, datetime, collections
S = "2026-10-17T2110Z"; SRC = "5pm ET 10/17 columns run (ehpa cloud) - run %s" % S; W = "10/17"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
b = json.load(open("scan_%s/summary_before.json" % S)); a = json.load(open("scan_%s/summary_after.json" % S))
def cnt(s):
    ex = s.get("exclusions", {}); nex = sum(len(v) for v in ex.values()) if isinstance(ex, dict) else len(ex)
    ins = s.get("inspector", {}); nin = sum(len(v) for v in ins.values()) if isinstance(ins, dict) else len(ins)
    return len(s.get("chargereview", [])), nin, len(s.get("unbilled", [])), nex
cb, ca = cnt(b), cnt(a); cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb + ca)
sw = json.load(open("registers/uni20_bcbs_pre0501_sweep_%s.json" % S))
byact = collections.Counter(r["action"].split(" - ")[0] for r in sw); asked = len(sw); askamt = sum(r["balance"] for r in sw)
NAMES = {"17478059": "[name]", "17478063": "[name]", "17478064": "EDGERTON,JOCELYN R", "17470713": "[name]", "24750": "chart 24750"}
# ---- run report CSV
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear", action="0 visits before and after")
add("claim inspector", "clear", action="0 batches before and after")
for r in a.get("unbilled", []):
    pid = str(r.get("patientid") or r.get("patient") or ""); vid = str(r.get("visitid") or r.get("id") or "")
    add("unbilled", "remaining", NAMES.get(pid, "chart " + pid), r.get("dos") or r.get("dateofservice") or "", "(no plan on chart)", "; ".join(r.get("errors") or r.get("reasons") or []) or "Insurance order is missing on visit", "held - cascade exhausted 10/15, HCA Florida Capital facesheet (admit 10/12/2026) on William's turn", visit=vid, amt=r.get("balance") or r.get("amount") or "")
add("exclusions", "remaining", NAMES["17470713"], "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP Medicare Supplement member number from her card needed (William's turn); not rebilled", amt="")
add("exclusions", "remaining", NAMES["24750"], "", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 (v19455937)", "held - carrier master (board row aet12-carrier-cpid); not rebilled", visit="19455937")
add("era", "clear", action="ERA Center 0 checks $0.00 before and after; nothing uploaded, posted or cleared; Availity: no new PDF / Check-EFT export; Treasury: nothing new")
for r in sw:
    add("uni20/bcbs pre-5/1 pass 131", "sweep", r.get("patient", ""), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit=str(r.get("visitid")), amt=r.get("balance"))
with open("_run report 10-17 2110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
# ---- needs section
sec = """## %s - backend billing run, 5 PM ET 10/17/2026 slot (ehpa cloud) - 21:10-21:4xZ

Bootstrap: repo ATTACHED (origin/main f9c7938 at start; main checked out, symlinked as /home/claude/effinger-billing-backend; layout 1096 helper files; v12 precondition greps pass); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no credential file); ONE login 21:19Z, no lock, no 429. Guard: 1910Z START has its RUN COMPLETE digest (19:27Z), no newer START; own START uploaded 21:14Z, lock written. State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main. pseudonyms.json (406 names, Drive 10/8) in both secrets/; deceased_cache.json (Drive 10/16) merged (38 dated entries, unchanged). Missing required helpers: none. Learned from others: git log since 36 h = this routine's own runs + the Billing Button + the 0541Z cascade slot; SHARED_LESSONS lines newer than the 1910Z run: none - 0 applied.

Sources: Insurance Refresh Board (read_db only): 0 rows changed since 14:00Z; drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved, register 0 waiting; both drive_sync registries list no current inbox file - nothing trashed. Drive: the eight watched folders (hca / tmh / PCC facesheets, Claimocity drop, Optum + Availity ERA downloads, uhc downloads, treasury payments) hold nothing modified after 10/16 12:00Z except the 2310Z run report CSV. Pam Gmail (2 days): 10/17 16:18Z Aviata readmit chart 17472553 (worked 1710Z) and the 10/17 00:29Z Tapestry new admit (still no AMD chart per the 1710Z lookup; not re-asked). Three 10/15 admits remain chart-less.

Columns (columns_scan before 21:19Z -> after 21:3xZ) %s (overview 27 / $4,235 lags the list):
- CHARGE REVIEW 0. CLAIM INSPECTOR 0 batches.
- UNBILLED 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 - v19457778 / v19457794, v19457783 / v19457797, v19457784 / v19457791 (99223 10/12 + 99232 10/13/2026, $421 each, $1,263) 'Insurance order is missing' - cascade exhausted 10/15 (two are Capital Health Plan MA by Medicare's COB record, CHP answers 'subscriber not found' without the member id; one has no medical payer on file); no HCA / TMH / PCC facesheet, Pam email or board drop since; rows on William's turn unchanged.
- EXCLUSIONS 26: 25 AARP Medigap secondary rows of chart 17470713 on claim run 1700302 (subscriber id not found - the AARP supplement member number from her card is the only fix, William's turn) + 1 AET12 PREF0288 chart 24750 v19455937 (carrier master hold). Nothing rebilled, nothing completed.
- Dollars re-sent $0. Rebills 0. Write-offs none. No AdvancedMD write this slot.

ERA (step 5): (a) nothing to upload (no new 835); (b) GET /api/era/checks = 0 checks / $0.00 before and after (era_post --all-unposted --dry); (c)-(e) nothing to post or clear; era_details/ unchanged (empty). (g) Availity: no new PDF or Check/EFT export; Treasury nothing new. (b2) UNI20/BCBS pre-5/1 pass 131 (claim_status_sweep.py --min-age 169 --max 60 --carriers UNI20,BCBS --skip-answered <115 sweep registers, comma-joined>): 586 answered visits skipped, %d asked ($%.2f; %d Stedi 276 calls): %s - 16 PENDING chart 17472874 ($2,563; 15 'accepted for processing' + the 03/04/2026 visit 'adjudicated, awaiting payment cycle') + 1 UNKNOWN chart 17475632 v19433791 ($310, empty status), 0 candidates, 0 sent, 0 written off; register registers/uni20_bcbs_pre0501_sweep_%s.json.

Waiting on William: HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); AARP Medicare Supplement member number for chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); three 10/15 Pam admits without an AMD chart; the standing items of earlier digests unchanged.
Approvals: applied 0 / submitted 0 / waiting 0. Permission-classifier refusals: none. Script errors: none (one self-inflicted: a Bash wait loop's pkill pattern matched its own shell and killed the command - re-run, no effect on AMD). Calls learned: 0 new shapes (0 vocabulary entries). Shared lessons: 1 WATCH line.
""" % (S, cols, asked, askamt, asked, dict(byact), S)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
# ---- board updates
chk = lambda txt: {"checks": [{"ok": "na", "result": txt, "src": SRC, "when": W}]}
hold = "5 PM ET 10/17: chart still has 0 insurance plans (Unbilled list 21:19Z and 21:3xZ); no HCA / TMH / PCC facesheet, Pam email or board drop since the 10/15 cascade (watched folders: nothing after 10/16 12:00Z); the two HCA visits (99223 10/12 + 99232 10/13/2026, $421) stay in Unbilled 'Insurance order is missing' - your facesheet (HCA Florida Capital, admit 10/12/2026) is still the only source."
ops = [{"op": "update", "collection": "items", "id": i, "append": chk(hold)} for i in ("madison-digby-[first]-17478059", "[name]-17478063", "edgerton-jocelyn-17478064")]
ops.append({"op": "update", "collection": "items", "id": "poulter-ellery-gwen-denials", "append": chk("5 PM ET 10/17: the 25 AARP Medigap secondary rejections of claim run 1700302 stay on the exclusion list; held, not rebilled - the AARP Medicare Supplement member number from her card is still the only fix.")})
ops.append({"op": "update", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("5 PM ET 10/17: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937) stays on the list, not rebilled; carrier master still unchanged.")})
ops.append({"op": "update", "collection": "items", "id": "availity-remits-backlog", "append": chk("5 PM ET 10/17: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing since 10/15; the eight watched folders hold nothing after 10/16 12:00Z); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; 0 rows changed since 14:00Z; approvals 0 approved / 0 waiting; Pam Gmail: nothing newer than the 16:18Z Aviata readmit (worked 1710Z); the three 10/15 admits still have no AMD chart. ERA Center 0 checks before and after. Columns %s - every row a standing hold; no AMD write this slot. UNI20/BCBS pre-5/1 pass 131: 16 PENDING chart 17472874 ($2,563) + 1 UNKNOWN chart 17475632, 0 sent." % cols)})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
# ---- additions
open("captured_calls_additions_2026-10-17_2110UTC-5pmET-ehpa-cloud.md", "w").write("""# captured_calls additions - backend billing run %s (5 PM ET 10/17/2026, ehpa cloud)

No new call shapes this run. Calls used, all already in the registry: login (one attempt, AMD_PSW environment credential), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus + getclaimexclusioncharges (clearinghouse=1 payer=1; columns_scan.py before/after), GET /api/era/checks (0 checks; era_post.py --all-unposted --dry), massrebillsearch + Stedi 276/277 claim status x17 (claim_status_sweep.py pass 131, --skip-answered with the comma-joined sweep registers). No AdvancedMD write.
""" % S)
print(cols, "| sweep", asked, dict(byact))
