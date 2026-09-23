# PLAIN ENGLISH (run outputs for the 3am ET 9/23/2026 slot - ehpa cloud run 2026-09-23T0710Z)
# Decides: nothing. Reads this run's registers (scan_0912/summary_before|after.json, registers/insp_2026-09-23T0710Z.json,
#   era_checks_before|after) and writes: "_run report 9-23 0310.csv"; board_updates_2026-09-23T0710Z.json (checks appends on the
#   standing rows only - no chart changed hands this run); a needs_facesheet_list.md section; the chat-history digest (--final).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-23T0710Z"; SRC = "3am ET 9/23 columns run (ehpa cloud)"; W = "9/23"; SLOT = "3 AM ET 9/23"
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
IN = load("registers/insp_%s.json" % S, {})
ERA_TXT = "%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center was empty the whole run (GET /api/era/checks = []); locks release-expired sent; era_details cache 0 (nothing to pull); era_post --all-unposted / fallback / era_clear not needed; 0 addpayments faults; payreasons.py --list: 0 Unbilled reason-code rows. No new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (the only new file there, THISTLEWOOD_PATIENT241_09022026.pdf 05:45Z, is a 9/2/2026 ALF admission progress note - not a remit); no ScanSnap batch (Gmail ScanSnap newer_than:1d = 0, Drive 'ScanSnap' folder nothing new). Nothing posted, dismissed or written off." % (nb, ab, na, aa)
HELD_EX = [("17472874", "19438061", "WEL04", "160.00"), ("17472874", "19438903", "WEL04", "160.00"), ("17472874", "19438993", "WEL04", "160.00"), ("17472874", "19439271", "WEL04", "160.00"), ("17472517", "19423193", "HUM01", "70.17"), ("20863", "19445850", "FLO99", "14.38")]
BOOT = ("Bootstrap: repo ATTACHED (origin/main b8cb909 = the 0510Z run's final commit; session branch claude/pensive-einstein-mkl2b6, work on main), bootstrap net = AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 07:14Z (columns_scan_0912.py before), no login lock. Cross-container guard: the 0510Z START has its RUN COMPLETE digest (06:18Z); START marker 2026-09-23T0710Z uploaded 07:12Z, lock written 07:12Z. Layout: tools/bootstrap_workspace.sh layout copied 555 helpers from main (carriers.json simple form 124 codes; tesseract + poppler present); registers = practices/ehpa/registers from main (285 files); needs_facesheet_list.md rebuilt from the 44 run sections in main; laterality_flag_log.md (Drive 9/22 11:45Z), precheck_cache.json (Drive 9/21 23:28Z, 28 pairs), pseudonyms.json (237 names, Drive 9/22 19:42Z) from 'workspace mirror'; the v9 insert (9/23 05:12Z: step 0 GITHUB INBOX + paper remits 5(f)) read; bootstrap check: columns_inspector2_0908.py and era_details_pull.py absent from main (not rewritten; columns_scan_0912.py + era_step_b_0913.py do their work). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules + the v9 GITHUB INBOX step applied. GITHUB INBOX: Drive 'github mirror' holds PACKAGE_effinger-billing-backend_2026-09-23_paper-eobs-2.manifest.json (sha256 629ec41b..., 6 commits fb8764b..4230ee4) but no .b64 beside it and tools/mirror/apply_bundle.py is not in main - the .b64 lives only in the Claude project doc, which this routine cannot read: package LEFT, not applied (William: push it from a session with the project doc, or upload the .b64 to 'github mirror').")
COLS = ("Charge Review %s -> %s | Claim Inspector %d -> %d | Unbilled %s -> %s | Exclusions %d -> %d rows (no new claim run since 1700227-1700229 of 9/22 21:06 AMD clock; getclaimrunstatus 82 runs)." % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a))
INSP_TXT = ("CLAIM INSPECTOR: 12 -> 11. No PENDING feed visits this slot (the 0510Z run's 16 resaves left the batch-1 rows). One advisory bypassed with a fresh id: pat17472124 v19446287 Pattern 11256 (Z89.619 unspecified laterality) -> bypassclaimedits ok, logged to laterality_flag_log.md; its batch 127180 emptied. Left: the 11 pat17472874 April-2026 hospital visits (v19437843, v19437926, v19437951, v19438356, v19438357, v19438358, v19438701, v19439010, v19439022, v19439233, v19439702; 'Hospitalization From Date empty', $1,763) - no 99223 anchor within 45 days, held for William's admission date (standing hold).")
UNB_TXT = ("UNBILLED: 13 -> 13, all standing holds: 11 pat17472874 'Unresolved Claim Inspector errors' (the April stay above); pat17470743 v19441047 MCAD 'A payment from the prior payor is required' ($16.93 crossover behind a reversed Medicare payment - held as before); pat17477183 v19455471 'Insurance order is missing' ($141, 99309 9/18/2026 - cascade exhausted 0510Z, row alcott-alfie-17477183 on William's turn; no facesheet in the hca/tmh/PCC/Claimocity folders, no Pam email, no board drop since). Nothing released.")
EXCL_TXT = ("EXCLUSIONS: 6 -> 6 (runs 1700227 x2, 1700229 x4), all 'CH 72 PDTP0303 MISSING RELATED ADMISSION DATE' on hospital secondaries with no 99223 anchor within 45 days - held as at 0510Z: %s. No new claim run posted, so no new rejections." % "; ".join("pat%s v%s %s $%s" % r for r in HELD_EX))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="%s -> %s (getreviewcharges empty)" % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount")))
add("Claim Inspector", "count", action="%d -> %d" % (insp_b, insp_a))
for b in IN.get("bypassed", []): add("Claim Inspector", "bypassed", patient="pat%s" % b["pid"], visit=b["vid"], error="; ".join(b["errs"]), action="bypassclaimedits (advisory, Pattern 11256 unspecified laterality - logged) %s" % ("ok" if b["ok"] else "FAULT"))
for b, v, p, e in IN.get("left", []): add("Claim Inspector", "remaining", patient="pat%s" % p, visit=v, error=e[0][1][:80], action="HELD - William's turn (HCA admission date, 4/7-4/21/2026 stay)" if p == "17472874" else "left", carrier="WEL04" if p == "17472874" else "")
add("Unbilled", "count", action="%s -> %s" % (ub_b, ub_a))
add("Unbilled", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Unresolved Claim Inspector errors x11", action="HELD - the inspector holds above", amount="1763.00")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment)", amount="16.93")
add("Unbilled", "remaining", patient="pat17477183", visit="19455471", dos="09/18/2026", error="Insurance order is missing on visit", action="HELD - cascade exhausted 0510Z -> row alcott-alfie-17477183 on William's turn; no new facesheet/email/drop", amount="141.00")
add("Exclusions", "count", action="%d -> %d rows (runs 1700227 x2, 1700229 x4)" % (ex_b, ex_a))
for pid, vid, car, amt in HELD_EX: add("Exclusions", "remaining", patient="pat%s" % pid, visit=vid, carrier=car, error="CH 72 PDTP0303 MISSING RELATED ADMISSION DATE", action="HELD - no 99223 anchor within 45 days (pat17472874 = the April stay awaiting William's admission date)", amount=amt)
add("ERA", "count", action="%d / $%.2f -> %d / $%.2f; %s" % (nb, ab, na, aa, ERA_TXT[:400]))
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): nothing newer than the 01:33Z Oakes readmit already worked at 0310Z. Drive: nothing new in the hca/tmh/PCC/Claimocity facesheet folders, 'treasury payments' or 'ScanSnap'; 'bht Optum era downloads' got THISTLEWOOD_PATIENT241_09022026.pdf (a 9/2/2026 Sodalis ALF admission progress note, 99344+99497, primary dx I63.9 - not a remit; watch: outpatient I63.9 -> I69.30 rule applies if that claim is ever denied). Board drops 0; Working Denials queue 0; Insurance Refresh Board rows on Claude's turn read (200+), no new William note asking for work since 0510Z.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17477183", action="row alcott-alfie-17477183: SNF facesheet / card for the plan after 8/31/2026 (99309 9/18/2026 $141 waiting)")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector + 4 April visits rejected PDTP0303 on run 1700229, held)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt (+ the v9 insert) into the routine - v7 still fires; push the chat's PACKAGE 2026-09-23 paper-eobs-2 bundle (its .b64 is only in the project doc; upload it to Drive 'github mirror' beside the manifest and the next run applies it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
with open("_run report 9-23 0310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    op = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: op["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(op)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) still held in the Claim Inspector and 4 more (4/10-4/20/2026, $640, run 1700229) on the exclusion list - unchanged, your turn for the HCA admission date." % SLOT)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT[:600]))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 6 rows, all PDTP0303 holds, none AET12; no claim run newer than 1700229." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (only a 9/2/2026 progress note landed 05:45Z); no ScanSnap batch; Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the 01:33Z Oakes readmit." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker) - hold Florida Blue patient statements." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 07:10-%s UTC 9/23, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops; rows on Claude's turn read - no new William instruction since 0510Z. Sources: Pam Gmail nothing new; Drive facesheet folders / treasury / ScanSnap nothing new; 'bht Optum era downloads' got a 9/2/2026 progress note (not a remit).
Claim runs: none new since 1700227-1700229 (9/22 21:06 AMD clock).
Columns: %s
%s
%s
%s
ERA step 5: %s
Write-offs: none. Insurance entered: none. Rebilled: none. Board: checks appended on thackeray-kendrew-17472874, era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918 (no new rows).
Script errors: none.
NEEDS WILLIAM: (1) alcott-alfie-17477183 - facesheet/card for coverage after 8/31/2026 ($141); (2) thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 inspector holds $1,763 + 4 exclusion holds $640); (3) exclusion holds without a 99223 anchor: %s; (4) paste prompt v8 (+ v9 insert) - v7 still fires; upload the chat's PACKAGE 2026-09-23 paper-eobs-2 .b64 to Drive 'github mirror' (or push it) - the routine cannot read the project doc; (5) AET12 carrier master (HOLD); (6) the standing items from the 0310Z/0510Z sections.
Calls learned: no new call shape. Vocabulary: unchanged (55).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, INSP_TXT, UNB_TXT, EXCL_TXT, ERA_TXT, "; ".join("pat%s v%s %s $%s" % r for r in HELD_EX), MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("# %s run digest - backend billing run, %s slot (ehpa cloud)\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, SEC))
    print("final written")
print("outputs written: csv rows %d, board ops %d" % (len(rows), len(ops)))
