# PLAIN ENGLISH (run outputs for the 7am ET 9/23/2026 slot - ehpa cloud run 2026-09-23T1110Z)
# Decides: nothing. Reads this run's registers (scan_0912/summary_before|after.json, era_checks_before|after) and writes:
#   "_run report 9-23 0710.csv"; board_updates_2026-09-23T1110Z.json (checks appends on the standing rows only - no new rows this slot);
#   a needs_facesheet_list.md section; the chat-history digest (--final).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-23T1110Z"; SRC = "7am ET 9/23 columns run (ehpa cloud)"; W = "9/23"; SLOT = "7 AM ET 9/23"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", sb)
def cnt(s, k): return (s.get("overview") or {}).get(k, "?")
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount")
ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
HELD_EX = [("17472517", "19423193", "HUM01", "70.17", "11/11/2025 99233"), ("20863", "19445850", "FLO99", "14.38", "06/23/2026 99232")]
HOLD15 = ["19437843", "19437926", "19437951", "19438061", "19438356", "19438357", "19438358", "19438701", "19438903", "19438993", "19439010", "19439022", "19439233", "19439271", "19439702"]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. GET /api/era/checks empty at 11:18Z (locks release-expired sent; era_details cache: nothing to pull); the Post button, fallback and era_clear had nothing to do; 0 addpayments faults; payreasons.py --list: 0 Unbilled reason-code rows. "
           "No new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 07:00Z 9/23); no ScanSnap batch (Gmail ScanSnap newer_than:2d = 0, Drive 'ScanSnap' nothing new); no paper/virtual-card remits to run." % (nb, ab, na, aa))
BOOT = ("Bootstrap: repo ATTACHED (origin/main 24e6c66 = the 0910Z run's final commit; session branch claude/pensive-einstein-j94gv3, work on main), bootstrap net = AMD_OK (login gateway 200, Stedi 403 = proxy credential path, GitHub 200), STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 11:16Z (columns_scan_0912.py before), no login lock. "
        "Cross-container guard: the 0910Z START has its RUN COMPLETE digest (09:28Z); START marker 2026-09-23T1110Z uploaded 11:11Z, lock written 11:14Z. Layout: tools/bootstrap_workspace.sh layout copied 562 helpers from main (carriers.json simple form 124 codes; tesseract + poppler present); registers = practices/ehpa/registers from main (289 files); needs_facesheet_list.md rebuilt from the run sections in main (530 lines); laterality_flag_log.md (Drive 9/23 09:28Z) and pseudonyms.json (237 names, Drive 9/22 19:42Z) from 'workspace mirror'; precheck_cache.json not restored (7pm-only helper). "
        "bootstrap check: github_sync.py optional-absent only; every required helper present. Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules (payreasons) + the v9 insert (step 0 GITHUB INBOX, paper remits 5(f)) + the 9/22 deceased guard applied. "
        "GITHUB INBOX: Drive 'github mirror' still holds PACKAGE_effinger-billing-backend_2026-09-23_paper-eobs-2.manifest.json (sha256 629ec41b..., head 4230ee4, base fb8764b) with no .b64 beside it; its commits (4230ee4, 9effc16) are not in main and tools/mirror/apply_bundle.py is not in main - the .b64 lives only in the Claude project doc, which this routine cannot read: package LEFT, not applied (William: push it from a session with the project doc, or upload the .b64 to 'github mirror').")
COLS = ("Charge Review %s -> %s | Claim Inspector %d -> %d | Unbilled %s -> %s | Exclusions %d -> %d list rows (overview 3 rows / $469 lags; no new claim run since 1700227-1700229 of 9/22 21:06 AMD clock; getclaimrunstatus 82 runs)." % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a))
INSP_TXT = ("CLAIM INSPECTOR: 16 -> 16, every row a standing hold; no PENDING feed visits, no advisory to bypass, nothing resaved. pat17474541 v19430630 (batch 126125, CCM 1/27/2026, $109) Pattern 15775 'add-on 99489 without a primary' + 4426 - the 99487 on the visit is voided; row rodway-rosalind-17474541 on William's turn since 0910Z (restore the 99487 or void/write off the 99489), not bypassable. "
            "15 pat17472874 April-2026 hospital visits (%s; 'Hospitalization From Date empty', $2,403) - no 99223 anchor within 45 days, held for William's admission date (row thackeray-kendrew-17472874, standing hold)." % ", ".join("v" + v for v in HOLD15))
UNB_TXT = ("UNBILLED: 13 -> 13, all standing holds: 11 pat17472874 'Unresolved Claim Inspector errors' (the April stay above); pat17470743 v19441047 MCAD 'A payment from the prior payor is required' ($16.93 crossover behind a reversed Medicare payment - held as before); pat17477183 v19455471 'Insurance order is missing' ($141, 99309 9/18/2026 - cascade exhausted 0510Z, row alcott-alfie-17477183 on William's turn; no facesheet in the hca/tmh/PCC/Claimocity folders, no Pam email, no board drop since). Nothing released.")
EXCL_TXT = ("EXCLUSIONS: 2 -> 2 list rows (run 1700227), both 'CH 72 PDTP0303 MISSING RELATED ADMISSION DATE' on hospital secondaries with no 99223 anchor within 45 days - held as at 0710Z/0910Z: %s. No new claim run posted (82 runs), so no new rejections." % "; ".join("pat%s v%s %s $%s (%s)" % r for r in HELD_EX))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="%s -> %s (getreviewcharges empty)" % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount")))
add("Claim Inspector", "count", action="%d -> %d (all standing holds; nothing bypassed or resaved)" % (insp_b, insp_a))
add("Claim Inspector", "remaining", patient="pat17474541", visit="19430630", dos="01/27/2026", carrier="PHI01", error="Pattern 15775 add-on 99489 without a primary + Pattern 4426", action="HELD - 99487 (charge 23336997) is VOIDED, lone 99489 $109 remains; row rodway-rosalind-17474541 on William's turn (restore the 99487 or void/write off the 99489)", amount="109.00")
for v in HOLD15: add("Claim Inspector", "remaining", patient="pat17472874", visit=v, error="Hospitalization From Date in the Extra Info tab is empty", action="HELD - William's turn (HCA admission date, 4/7-4/21/2026 stay)", carrier="WEL04")
add("Unbilled", "count", action="%s -> %s" % (ub_b, ub_a))
add("Unbilled", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Unresolved Claim Inspector errors x11", action="HELD - the inspector holds above", amount="1763.00")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment)", amount="16.93")
add("Unbilled", "remaining", patient="pat17477183", visit="19455471", dos="09/18/2026", error="Insurance order is missing on visit", action="HELD - cascade exhausted 0510Z -> row alcott-alfie-17477183 on William's turn; no new facesheet/email/drop", amount="141.00")
add("Exclusions", "count", action="%d -> %d list rows (run 1700227 x2; overview 3/$469 lags)" % (ex_b, ex_a))
for pid, vid, car, amt, d in HELD_EX: add("Exclusions", "remaining", patient="pat%s" % pid, visit=vid, dos=d, carrier=car, error="CH 72 PDTP0303 MISSING RELATED ADMISSION DATE", action="HELD - no 99223 anchor within 45 days", amount=amt)
add("ERA", "count", action="%d / $%.2f -> %d / $%.2f (ERA Center empty; nothing to post, fall back on or clear)" % (nb, ab, na, aa))
add("ERA", "availity", action="no new Availity PDF / Check-EFT export / 835 in 'bht Optum era downloads' or 'treasury payments' after 07:00Z 9/23; no ScanSnap batch - nothing parsed, posted or reconciled")
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): nothing newer than the 01:33Z 9/23 Pruitt readmit already worked at 0310Z. Drive: nothing new after 07:00Z in the hca/tmh/PCC/Claimocity facesheet folders, 'bht Optum era downloads', 'treasury payments', 'ScanSnap' or the project-files root (only the 0710Z/0910Z additions files). Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated since 09:00Z (no new William instruction since 0910Z).")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17474541", action="row rodway-rosalind-17474541: CCM 1/27/2026 v19430630 - the 99487 is voided, only the 99489 add-on ($109) remains and the inspector blocks it: say 'restore' (restore_charge.py 23336997 + rebill Medicare first) or 'void the 99489' / write off")
add("Open on William's turn", "note", patient="pat17477183", action="row alcott-alfie-17477183: SNF facesheet / card for the plan after 8/31/2026 (99309 9/18/2026 $141 waiting)")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (15 visits $2,403 held in the Claim Inspector, 11 of them also in Unbilled)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt (+ the v9 insert) into the routine - v7 still fires; push the chat's PACKAGE 2026-09-23 paper-eobs-2 bundle (its .b64 is only in the project doc; upload it to Drive 'github mirror' beside the manifest and the next run applies it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
with open("_run report 9-23 0710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    op = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: op["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(op)
app("thackeray-kendrew-17472874", "na", "%s: unchanged - 15 April-2026 visits held in the Claim Inspector ($2,403, 'Hospitalization From Date empty', no 99223 anchor within 45 days), 11 of them also in Unbilled; your turn for the HCA admission date." % SLOT)
app("rodway-rosalind-17474541", "na", "%s: unchanged - v19430630 still held by Pattern 15775 (the 99487 is voided, the lone 99489 $109 stays); waiting on your word: restore or void/write off." % SLOT)
app("alcott-alfie-17477183", "no", "%s: still no facesheet in the hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; v19455471 ($141) stays in Unbilled 'Insurance order is missing'." % SLOT)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT[:700]))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 2 list rows, both PDTP0303 holds, none AET12; no claim run newer than 1700229 (82 runs)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 07:00Z 9/23); no ScanSnap batch; Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the 01:33Z Pruitt readmit. ERA Center empty." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 11:10-%s UTC 9/23, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops; rows on Claude's turn: none updated since 09:00Z, no new William instruction since 0910Z. Sources: Pam Gmail nothing newer than the 01:33Z Pruitt readmit (worked 0310Z); Drive facesheet folders / era downloads / treasury / ScanSnap / project-files root: nothing new after 07:00Z except the routine's own additions files.
Claim runs: none new since 1700227-1700229 (9/22 21:06 AMD clock; 82 runs).
Columns: %s
%s
%s
%s
ERA step 5: %s
Write-offs: none. Insurance entered: none. Rebilled: none. AMD writes this run: none (read-only slot). Board: checks appended on thackeray-kendrew-17472874, rodway-rosalind-17474541, alcott-alfie-17477183, era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918; no new rows.
Script errors: none.
NEEDS WILLIAM: (1) rodway-rosalind-17474541 - restore the voided 99487 on v19430630 (1/27/2026 CCM) or void/write off the lone 99489 ($109); (2) alcott-alfie-17477183 - facesheet/card for coverage after 8/31/2026 ($141); (3) thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (15 inspector holds $2,403); (4) exclusion holds without a 99223 anchor: %s; (5) paste prompt v8 (+ v9 insert) - v7 still fires; upload the chat's PACKAGE 2026-09-23 paper-eobs-2 .b64 to Drive 'github mirror' (or push it); (6) AET12 carrier master (HOLD); (7) the standing items from the 0310Z-0910Z sections.
Calls learned: no new call shape. Vocabulary: unchanged (55).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, INSP_TXT, UNB_TXT, EXCL_TXT, ERA_TXT, "; ".join("pat%s v%s %s $%s" % r[:4] for r in HELD_EX), MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("# %s run digest - backend billing run, %s slot (ehpa cloud)\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, SEC))
    print("final written")
print("outputs written: csv rows %d, board ops %d" % (len(rows), len(ops)))
