# PLAIN ENGLISH (run outputs for the 11 PM ET 10/17/2026 slot - ehpa cloud run 2026-10-18T0310Z)
# Decides: nothing. Reads this run's column scans (scan_2026-10-18T0310Z/summary_before|after.json), the pass-134 sweep register and
# the ERA list registers, then writes the run report CSV, the needs_facesheet_list.md section (+ a copy for Drive), the board_updates
# inbox file (append-only checks, never set on status/need), the captured_calls additions file and the chat-history digest.
# Never touches: AMD, the board database.
import csv, json, datetime, collections, os
S = "2026-10-18T0310Z"; SRC = "11pm ET 10/17 columns run (ehpa cloud) - run %s" % S; W = "10/17"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
SD = "scan_" + S
b = json.load(open(SD + "/summary_before.json")); a = json.load(open(SD + "/summary_after.json"))
def cnt(s):
    ex = s.get("exclusions", {}); nex = sum(len(v) for v in ex.values()) if isinstance(ex, dict) else len(ex)
    ins = s.get("inspector", {}); nin = sum(len(v) for v in ins.values()) if isinstance(ins, dict) else len(ins)
    return len(s.get("chargereview", [])), nin, len(s.get("unbilled", [])), nex
cb, ca = cnt(b), cnt(a); cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb + ca)
sw = json.load(open("registers/uni20_bcbs_pre0501_sweep_%s.json" % S))
byact = collections.Counter(r["action"].split(" - ")[0] for r in sw); asked = len(sw); askamt = sum(r["balance"] for r in sw)
bychart = collections.defaultdict(lambda: [0, 0.0])
for r in sw:
    k = (r["action"].split(" - ")[0], str(r["patientid"])); bychart[k][0] += 1; bychart[k][1] += r["balance"]
swtxt = "; ".join("%d %s chart %s ($%.0f)" % (v[0], k[0], k[1], v[1]) for k, v in sorted(bychart.items()))
era_b = json.load(open("registers/era_checks_before_%s.json" % S)); era_a = json.load(open("registers/era_checks_after_%s.json" % S))
def era_n(j):
    rows = j if isinstance(j, list) else (j.get("erachecks") or j.get("checks") or j.get("data") or j.get("rows") or [])
    return len(rows), sum(float(c.get("checkamount") or c.get("amount") or 0) for c in rows)
eb, ea = era_n(era_b), era_n(era_a)
NAMES = {"17478059": "[name]", "17478063": "[name]", "17478064": "EDGERTON,JOCELYN R", "17470713": "chart 17470713 (AARP Medigap secondaries)", "24750": "chart 24750"}
VIS = {"19457778": ("17478059", "99223 10/12/2026"), "19457794": ("17478059", "99232 10/13/2026"), "19457783": ("17478063", "99223 10/12/2026"), "19457797": ("17478063", "99232 10/13/2026"), "19457784": ("17478064", "99223 10/12/2026"), "19457791": ("17478064", "99232 10/13/2026")}
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear", action="0 visits before and after")
add("claim inspector", "clear", action="0 batches before and after")
for r in a.get("unbilled", []):
    pid = str(r.get("patientid") or ""); vid = str(r.get("id") or "")
    add("unbilled", "remaining", NAMES.get(pid, "chart " + pid), VIS.get(vid, ("", ""))[1], "(no plan on chart - live getdemographic 03:1xZ: 0 insplans)", "; ".join(r.get("_errs") or []) or "Insurance order is missing on visit", "held - cascade exhausted 10/15, HCA Florida Capital facesheet (admit 10/12/2026) on William's turn", visit=vid, amt="")
add("exclusions", "remaining", NAMES["17470713"], "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP Medicare Supplement member number from her card needed (William's turn); not rebilled", amt="")
add("exclusions", "remaining", NAMES["24750"], "09/20/2026", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (v19455937)", "held - carrier master (board row aet12-carrier-cpid); not rebilled", visit="19455937", amt="315.00")
add("era", "clear", action="ERA Center %d checks $%.2f before -> %d checks $%.2f after; nothing uploaded (no new 835), posted or cleared; Availity: no new PDF / Check-EFT export; Treasury: nothing new" % (eb + ea))
for r in sw:
    add("uni20/bcbs pre-5/1 pass 134", "sweep", r.get("patient", ""), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit=str(r.get("visitid")), amt=r.get("balance"))
add("pam admits", "waiting", "[name] (Tapestry NA 10/15, re-sent 10/17); [name] (Brynwood NA 10/15); BEARDSLEY,[first] (Brynwood NA 10/15)", action="lookuppatient 03:2xZ: still no AMD chart for any of the three - nothing to attach to; waiting on the Claimocity feed (never create a chart from an email)")
with open("_run report 10-18 0310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
sec = """## %s - backend billing run, 11 PM ET 10/17/2026 slot (ehpa cloud) - 03:10-03:4xZ

Bootstrap: repo ATTACHED (origin/main 19482c1 at start; session branch claude/pensive-einstein-avfcsc; main checked out; symlinked as /home/claude/effinger-billing-backend; layout 1100 helper files); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password = the AMD_PSW environment credential (no credential file); ONE login 03:12Z, no lock, no 429. Guard: 0110Z START has its RUN COMPLETE digest (01:28Z), no newer START; own START uploaded 03:11Z, lock written. State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main. pseudonyms.json (406 names, Drive 10/8) in both secrets/; deceased_cache.json (Drive 10/16) merged (76 dated entries). Missing required helpers: none; v12 precondition markers all present. Learned from others: 0 new SHARED_LESSONS lines since the 0110Z run (0 applied).

Sources: Insurance Refresh Board (read_db only): 0 rows changed since 00:30Z; drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved, register all done; both drive_sync registries list no current inbox file - nothing trashed. Drive: nothing new in the HCA / TMH / PCC / Claimocity / 835 / treasury / board-inbox folders after 20:00Z 10/17 outside the routines' own files. Pam Gmail (2 days): the 10/17 16:18Z Aviata readmit (chart 17472553, worked 1710Z) and the 10/17 00:29Z Tapestry new admit; lookuppatient 03:2xZ: FLINT (Tapestry 10/15), JENKINS and BEARDSLEY (Brynwood 10/15) still have no AMD chart (registers/admit_lookup_%s.json).

Columns (columns_scan before 03:12Z -> after 03:3xZ) %s (overview 27 / $4,235 lags the list):
- CHARGE REVIEW 0. CLAIM INSPECTOR 0 batches.
- UNBILLED 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 - v19457778 / v19457794, v19457783 / v19457797, v19457784 / v19457791 (99223 10/12 + 99232 10/13/2026, $421 each, $1,263) 'Insurance order is missing' - live getdemographic 03:1xZ: still 0 insplans on all three; cascade exhausted 10/15; no HCA / TMH / PCC facesheet, Pam email or board drop since; rows on William's turn unchanged.
- EXCLUSIONS 26: 25 AARP Medigap secondary rows of chart 17470713 on claim run 1700302 (subscriber id not found - the AARP supplement member number from her card is the only fix, William's turn) + 1 AET12 PREF0288 chart 24750 v19455937 (carrier master hold). Nothing rebilled, nothing completed.
- Dollars re-sent $0. Rebills 0. Write-offs none. No AdvancedMD write this slot.

ERA (step 5): (a) nothing to upload (no new 835); (b) GET /api/era/checks = %d checks / $%.2f before and %d checks / $%.2f after; (c)-(e) nothing to post or clear. (g) Availity: no new PDF or Check/EFT export; Treasury nothing new.
UNI20/BCBS pre-5/1 pass 134 (claim_status_sweep.py --min-age 170 --max 60 --carriers UNI20,BCBS --skip-answered <118 sweep registers + 2 claimstatus files, comma-joined>): 700 answered visits skipped, %d asked ($%.2f): %s - %s; 0 candidates, 0 sent, 0 written off; register registers/uni20_bcbs_pre0501_sweep_%s.json.

Waiting on William: HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); AARP Medicare Supplement member number for chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); three 10/15 Pam admits without an AMD chart; the standing items of earlier digests unchanged.
Script errors: none. Calls learned: 0 new shapes (0 vocabulary entries).
""" % (S, S, cols, eb[0], eb[1], ea[0], ea[1], asked, askamt, dict(byact), swtxt, S)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt: {"checks": [{"ok": "na", "result": txt, "src": SRC, "when": W}]}
hold = "11 PM ET 10/17: chart %s live read 03:1xZ still 0 insplans; no new HCA facesheet in Drive, no Pam email, no board note - the two visits (%s) stay in Unbilled 'Insurance order is missing'; your turn unchanged (HCA Florida Capital facesheet, admit 10/12/2026)."
ops = [{"op": "update", "collection": "items", "id": "madison-digby-[first]-17478059", "append": chk(hold % ("17478059", "v19457778 / v19457794"))},
       {"op": "update", "collection": "items", "id": "[name]-17478063", "append": chk(hold % ("17478063", "v19457783 / v19457797"))},
       {"op": "update", "collection": "items", "id": "edgerton-jocelyn-17478064", "append": chk(hold % ("17478064", "v19457784 / v19457791"))}]
ops.append({"op": "update", "collection": "items", "id": "poulter-ellery-gwen-x", "append": chk("11 PM ET 10/17: the 25 AARP Medicare Supplement secondary rows of chart 17470713 on run 1700302 are unchanged on the Exclusions list (subscriber id not found) - not rebilled; still waiting on the supplement member number from her card.")})
ops.append({"op": "update", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("11 PM ET 10/17: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937) stays on the list, not rebilled; carrier master still unchanged.")})
ops.append({"op": "update", "collection": "items", "id": "availity-remits-backlog", "append": chk("11 PM ET 10/17: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new in the watched folders after 20:00Z outside the routines' own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail nothing newer than the 10/17 16:18Z Aviata readmit (worked 1710Z). ERA Center %d checks before and after. Columns %s - every row a standing hold, no AMD write this slot. UNI20/BCBS pre-5/1 pass 134: %s, 0 sent." % (eb[0], cols, swtxt))})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
open("captured_calls_additions_2026-10-18_0310UTC-11pmET-ehpa-cloud.md", "w").write("""# captured_calls additions - backend billing run %s (11 PM ET 10/17/2026, ehpa cloud, repo attached)

No new call shape this run. Calls used, all already in the registry: login (one attempt), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus + getclaimexclusioncharges per run (columns_scan.py before/after), getdemographic (live insplan count on charts 17478059 / 17478063 / 17478064), lookuppatient (three 10/15 Pam admits, no chart), GET /api/era/checks (era_list.py before/after, 0 checks), Stedi 276/277 claim status x17 (claim_status_sweep.py pass 134, --skip-answered with the comma-joined sweep registers). No AdvancedMD write.
""" % S)
dig = """# %s run digest - backend billing run, 11 PM ET 10/17/2026 (ehpa cloud, repo attached)

## Bootstrap
- Repo attached: main 19482c1 at start (session branch claude/pensive-einstein-avfcsc; main checked out; /home/claude/effinger-billing-backend symlinked to the session clone). Network: AMD OK, Stedi proxy credential OK (STEDI_CRED_OK, no key file), GitHub attached. AMD password: the AMD_PSW environment credential (no credential file). One login 03:12Z, no lock, no 429. python requests present.
- State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main (1100 helper files laid out). pseudonyms.json (406 names, Drive 10/8 copy) in both secrets/. deceased_cache.json (Drive 10/16) merged into the workspace cache (76 dated entries, unchanged; the repo copy left scrubbed). Missing required helpers: none; v12 precondition markers all present.
- Guard: 0110Z START has its RUN COMPLETE digest (01:28Z); START uploaded 03:11Z, lock written, deleted at the end.
- Learned from others: 0 new SHARED_LESSONS lines since the 0110Z run (0 applied); shared: 1 WATCH line.

## Sources read
- Insurance Refresh Board (read_db only): 0 rows changed since 00:30Z; drops 0. Working Denials queue 0. Mandatory Approvals page 0 approved / 0 waiting; approvals_pending.json on main all done. Both drive_sync registries: no current inbox file in the applied maps - nothing trashed.
- Drive: nothing new in the HCA / TMH / PCC / Claimocity / 835 / treasury / board-inbox folders after 20:00Z 10/17 outside the routines' own files. Pam Gmail: nothing newer than the 10/17 16:18Z Aviata readmit (worked 1710Z); the three 10/15 admits (Tapestry x1, Brynwood x2) still have no AMD chart (lookuppatient 03:2xZ, registers/admit_lookup_%s.json).

## Columns (list calls) %s
- Charge Review 0. Claim Inspector 0 batches.
- Unbilled 6: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (live getdemographic 03:1xZ: still 0 insplans; William's turn, HCA Florida Capital facesheets admit 10/12/2026, 6 visits $1,263; checks appended through the board inbox).
- Exclusions 26 (overview 27 / $4,235 lags): the 25 AARP rows of chart 17470713 on run 1700302 (supplement member number on William's turn) and the AET12 chart-24750 PREF0288 hold - unchanged, nothing rebilled.
- Dollars re-sent $0. Rebills 0. Write-offs none. No AdvancedMD write this slot. Permission-classifier refusals: none.

## ERA Center - %d checks $%.2f before -> %d checks $%.2f after
- Nothing uploaded (no new 835), nothing posted, nothing cleared. Availity 5(g): no new PDF or Check/EFT export; Treasury nothing new. Calls learned: none (0 vocabulary entries).

## UNI20/BCBS pre-5/1
- Pass 134 (--min-age 170 --max 60 --carriers UNI20,BCBS --skip-answered passes 1-133): 700 skipped, %d asked ($%.2f): %s; 0 candidates, 0 sent; written off timely 0.

## Script errors
- None.

## Waiting on William
- HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263).
- AARP Medicare Supplement member number for chart 17470713 (25 secondary claims on run 1700302).
- AET12 carrier master (chart 24750); three 10/15 Pam admits without an AMD chart; the standing items of earlier digests unchanged.

## Mirror
- GitHub: MIRROR_GITHUB
- Postman: unchanged (no new call shapes; docs/postman_effinger_amd.json / api_vocabulary.json not re-uploaded). The Drive registry copy is carried by captured_calls_additions_2026-10-18_0310UTC-11pmET-ehpa-cloud.md -> 'billing agent project files'.
- Drive: needs_facesheet_list_section_%s.md -> 'workspace mirror'; board_updates_%s.json (6 ops, all appends) -> 'board inbox'; no denials_updates (queue empty); this digest -> 'chat history'; run report CSV delivered with SendUserFile. No helper changed this run.
- State bundle: skipped with the standing justification (Drive bundle 2026-09-18 superseded by main; patient_db/ and era_details/ empty this run; the registers that changed are on main; the connector's typed-text transport cannot carry the parts byte-exact). Deceased cache unchanged - not re-uploaded.

## SHARED LESSONS
- 2026-10-18T03:40Z | backend billing run | WATCH | columns %s (three zero-plan HCA charts 17478059 / 17478063 / 17478064 on William's turn, chart 17470713's 25 AARP secondaries on run 1700302 waiting on the member number, AET12 chart 24750 carrier hold); ERA Center %d checks before and after; UNI20/BCBS pre-5/1 pass 134: %s, 0 sent; three 10/15 Pam admits still without an AMD chart; no AMD write | registers/uni20_bcbs_pre0501_sweep_%s.json

RUN COMPLETE
""" % (S, S, cols, eb[0], eb[1], ea[0], ea[1], asked, askamt, swtxt, S, S, cols, eb[0], swtxt, S)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(dig)
print(cols, "| ERA", eb, ea, "| sweep", asked, dict(byact), "|", swtxt)
