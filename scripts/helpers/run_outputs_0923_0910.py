# PLAIN ENGLISH (run outputs for the 5am ET 9/23/2026 slot - ehpa cloud run 2026-09-23T0910Z)
# Decides: nothing. Reads this run's registers (scan_0912/summary_before|after.json, registers/insp_2026-09-23T0910Z.json,
#   era_checks_before|after, era_details/1052806.json) and writes: "_run report 9-23 0510.csv"; board_updates_2026-09-23T0910Z.json
#   (two new rows: rodway-rosalind-17474541 on William's turn, jarvis-marisa-17477607 watch; checks appends on the standing rows);
#   a needs_facesheet_list.md section; the chat-history digest (--final).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-23T0910Z"; SRC = "5am ET 9/23 columns run (ehpa cloud)"; W = "9/23"; SLOT = "5 AM ET 9/23"
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
PHI = load("board_rows_phi_%s.json" % S, {"rodriguez": {}, "joiner": {}})  # names / DOB / member ids live in the workspace only, never in this script
R, J = PHI["rodriguez"], PHI["joiner"]
ERA_TXT = ("%d unposted check / $%.2f before -> %d / $%.2f after. Humana check 1052806 (ACH 200700340260922, deposit 9/21/2026, $33.86, received 9/23 01:45Z; era_details cached): 3 claim lines. "
           "Post button (era_post --all-unposted): the 2 money lines posted, $33.86 - pat17469466 v19442087 99309 5/14/2026 $16.93 and v19435620 99309 3/12/2026 $16.93 (Medicare-coinsurance residuals, OA-23 124.07 each, over-apply guard = payment only); fallback dry+live: both 'already posted' (register updated). "
           "Denial-only line pat17477607 v19453346 99309 8/20/2026 CO-185 + N767 ($141 claim, $16.93 open): Humana is NOT on that chart (FLO02 seq 1, UNI01 United American Medigap seq 2); Medicare 819794238 paid $66.36 9/16 + WOINS $57.71 9/21, and the $16.93 coinsurance has been at United American since 9/16 (pending) - Humana answered a crossover it does not cover; nothing written off, nothing rebilled (rules.md 9/20 CO185 WOINS rule applies to Humana-secondary charts only). "
           "era_clear dismissed the check (no postable money left) and GET /api/era/checks confirms it gone; 0 addpayments faults; payreasons.py --list: 0 Unbilled reason-code rows. Locks release-expired sent. "
           "No new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (only the chat's paper_remits_posting_workbook_2026-09-23.xlsx, 04:48Z); no ScanSnap batch (Gmail newer_than:1d = 0)." % (nb, ab, na, aa))
HELD_EX = [("17472517", "19423193", "HUM01", "70.17", "11/11/2025 99233"), ("20863", "19445850", "FLO99", "14.38", "06/23/2026 99232")]
HOLD15 = ["19437843", "19437926", "19437951", "19438061", "19438356", "19438357", "19438358", "19438701", "19438903", "19438993", "19439010", "19439022", "19439233", "19439271", "19439702"]
BOOT = ("Bootstrap: repo ATTACHED (origin/main ed1ff21 = the 0710Z run's final commit; session branch claude/pensive-einstein-wc7dnm, work on main), bootstrap net = AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 09:15Z (columns_scan_0912.py before), no login lock. "
        "Cross-container guard: the 0710Z START has its RUN COMPLETE digest (07:24Z); START marker 2026-09-23T0910Z uploaded 09:11Z, lock written 09:10Z. Layout: tools/bootstrap_workspace.sh layout copied 559 helpers from main (carriers.json simple form 124 codes; tesseract + poppler present); registers = practices/ehpa/registers from main (286 files); needs_facesheet_list.md rebuilt from the 45 run sections in main; laterality_flag_log.md (Drive 9/23 07:24Z), pseudonyms.json (237 names, Drive 9/22 19:42Z) from 'workspace mirror'; precheck_cache.json not restored (7pm-only helper). "
        "bootstrap check: columns_inspector2_0908.py and era_details_pull.py absent from main (not rewritten; columns_scan_0912.py + era_step_b_0913.py do their work). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules + the v9 insert (9/23 05:12Z: step 0 GITHUB INBOX + paper remits 5(f)) applied. "
        "GITHUB INBOX: Drive 'github mirror' still holds PACKAGE_effinger-billing-backend_2026-09-23_paper-eobs-2.manifest.json with no .b64 beside it and tools/mirror/apply_bundle.py is not in main - the .b64 lives only in the Claude project doc, which this routine cannot read: package LEFT, not applied (William: push it from a session with the project doc, or upload the .b64 to 'github mirror').")
COLS = ("Charge Review %s -> %s | Claim Inspector %d -> %d | Unbilled %s -> %s | Exclusions %d -> %d list rows (overview 3 rows / $469 lags; no new claim run since 1700227-1700229 of 9/22 21:06 AMD clock; getclaimrunstatus 82 runs)." % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a))
INSP_TXT = ("CLAIM INSPECTOR: 17 -> 16. No PENDING feed visits this slot. One advisory bypassed with a fresh id: pat17476869 v19452593 (99487+99489 8/23/2026, $315) Pattern 11256 (M25.559 unspecified laterality) -> bypassclaimedits ok, logged to laterality_flag_log.md; its batch 127559 emptied. "
            "NEW HOLD (not bypassable): pat17474541 v19430630 (batch 126125, CCM 1/27/2026) Pattern 15775 'add-on 99489 without a primary' + 4426 - gettxhistory typefilter 0 shows the 99487 (charge 23336997, $206, billed 1/31/2026 to PHI01 Philadelphia American Life) is VOIDED and only the 99489 add-on (charge 23336998, $109, mcode7) survives, re-billed 9/4/2026 to PHI01, $0 paid; no register or run section records that void. Chart order was Medigap PHI01 seq 1 ahead of Medicare seq 2 -> patient insorder set 2,1 (ins_update, readback ok; the visit already carried 2,1). Row rodway-rosalind-17474541 on William's turn: restore the voided 99487 (restore_charge.py, his OK) and rebill Medicare first, or void/write off the lone 99489. "
            "Left: 15 pat17472874 April-2026 hospital visits (%s; 'Hospitalization From Date empty', $2,403) - the 11 of the 0710Z run plus v19438061, v19438903, v19438993, v19439271, whose WEL04 PDTP0303 rows left the exclusion list of run 1700229 between 07:23Z and 09:15Z (completed outside the routine) and now sit in the inspector with the same hold; no 99223 anchor within 45 days, held for William's admission date (standing hold)." % ", ".join("v" + v for v in HOLD15))
UNB_TXT = ("UNBILLED: 13 -> 13, all standing holds: 11 pat17472874 'Unresolved Claim Inspector errors' (the April stay above); pat17470743 v19441047 MCAD 'A payment from the prior payor is required' ($16.93 crossover behind a reversed Medicare payment - held as before); pat17477183 v19455471 'Insurance order is missing' ($141, 99309 9/18/2026 - cascade exhausted 0510Z, row alcott-alfie-17477183 on William's turn; no facesheet in the hca/tmh/PCC/Claimocity folders, no Pam email, no board drop since). Nothing released.")
EXCL_TXT = ("EXCLUSIONS: 2 -> 2 list rows (run 1700227), both 'CH 72 PDTP0303 MISSING RELATED ADMISSION DATE' on hospital secondaries with no 99223 anchor within 45 days - held as at 0710Z: %s. The 4 pat17472874 WEL04 rows of run 1700229 are gone from the exclusion list (completed outside the routine; their visits are now the inspector holds above). No new claim run posted, so no new rejections." % "; ".join("pat%s v%s %s $%s (%s)" % r for r in HELD_EX))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="%s -> %s (getreviewcharges empty)" % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount")))
add("Claim Inspector", "count", action="%d -> %d" % (insp_b, insp_a))
for b in IN.get("bypassed", []): add("Claim Inspector", "bypassed", patient="pat%s" % b["pid"], visit=b["vid"], error="; ".join(b["errs"]), action="bypassclaimedits (advisory, Pattern 11256 unspecified laterality - logged) %s" % ("ok" if b["ok"] else "FAULT"))
add("Claim Inspector", "remaining", patient="pat17474541", visit="19430630", dos="01/27/2026", carrier="PHI01", error="Pattern 15775 add-on 99489 without a primary + Pattern 4426", action="HELD - 99487 (charge 23336997) is VOIDED, lone 99489 $109 remains; chart order set Medicare first (insorder 2,1); row rodway-rosalind-17474541 on William's turn (restore the 99487 or void/write off the 99489)", amount="109.00")
for b, v, p, e in IN.get("left", []):
    if p == "17472874": add("Claim Inspector", "remaining", patient="pat%s" % p, visit=v, error=e[0][1][:80], action="HELD - William's turn (HCA admission date, 4/7-4/21/2026 stay)", carrier="WEL04")
add("Unbilled", "count", action="%s -> %s" % (ub_b, ub_a))
add("Unbilled", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Unresolved Claim Inspector errors x11", action="HELD - the inspector holds above", amount="1763.00")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment)", amount="16.93")
add("Unbilled", "remaining", patient="pat17477183", visit="19455471", dos="09/18/2026", error="Insurance order is missing on visit", action="HELD - cascade exhausted 0510Z -> row alcott-alfie-17477183 on William's turn; no new facesheet/email/drop", amount="141.00")
add("Exclusions", "count", action="%d -> %d list rows (run 1700227 x2; overview 3/$469 lags)" % (ex_b, ex_a))
for pid, vid, car, amt, d in HELD_EX: add("Exclusions", "remaining", patient="pat%s" % pid, visit=vid, dos=d, carrier=car, error="CH 72 PDTP0303 MISSING RELATED ADMISSION DATE", action="HELD - no 99223 anchor within 45 days", amount=amt)
add("ERA", "count", action="%d / $%.2f -> %d / $%.2f" % (nb, ab, na, aa))
add("ERA", "auto-posted", check="1052806", payer="HUMANA (HUM01)", patient="pat17469466", visit="19442087", dos="05/14/2026", amount="16.93", action="Post button posted (99309, Medicare-coinsurance residual, OA-23 124.07 payment-only); fallback: already posted")
add("ERA", "auto-posted", check="1052806", payer="HUMANA (HUM01)", patient="pat17469466", visit="19435620", dos="03/12/2026", amount="16.93", action="Post button posted (99309, Medicare-coinsurance residual, OA-23 124.07 payment-only); fallback: already posted")
add("ERA", "denial-handled", check="1052806", payer="HUMANA (HUM01)", patient="pat17477607", visit="19453346", dos="08/20/2026", amount="0.00", error="CO-185 / N767 (rendering provider not eligible)", action="Humana not on the chart (FLO02 + UNI01 United American Medigap); Medicare paid 66.36 + WOINS 57.71; $16.93 coinsurance at United American since 9/16 pending - nothing written off, nothing rebilled; watch row jarvis-marisa-17477607")
add("ERA", "cleared", check="1052806", payer="HUMANA (HUM01)", amount="33.86", action="era_clear dismiss (no postable money left) -> ok; GET /api/era/checks after = []")
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): nothing newer than the 01:33Z 9/23 Pruitt readmit already worked at 0310Z. Drive: nothing new after 07:26Z in the hca/tmh/PCC/Claimocity facesheet folders, 'bht Optum era downloads', 'treasury payments' or 'ScanSnap'. Board drops 0; Working Denials queue 0; Insurance Refresh Board rows on Claude's turn: none updated since 07:00Z (no new William instruction since 0710Z).")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17474541", action="row rodway-rosalind-17474541: CCM 1/27/2026 v19430630 - the 99487 is voided, only the 99489 add-on ($109) remains and the inspector blocks it: say 'restore' (restore_charge.py 23336997 + rebill Medicare first) or 'void the 99489' / write off")
add("Open on William's turn", "note", patient="pat17477183", action="row alcott-alfie-17477183: SNF facesheet / card for the plan after 8/31/2026 (99309 9/18/2026 $141 waiting)")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (15 visits $2,403 held in the Claim Inspector, 11 of them also in Unbilled)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt (+ the v9 insert) into the routine - v7 still fires; push the chat's PACKAGE 2026-09-23 paper-eobs-2 bundle (its .b64 is only in the project doc; upload it to Drive 'github mirror' beside the manifest and the next run applies it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
with open("_run report 9-23 0510.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    op = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: op["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(op)
ops.append({"op": "upsert", "collection": "items", "id": "rodway-rosalind-17474541",
    "set": {"id": "rodway-rosalind-17474541", "patient": R.get("patient", ""), "dob": R.get("dob", ""), "facility": "ALF / home visit (CCM)", "amdid": "17474541", "mbi": R.get("mbi", ""),
            "inscarrier": "FLO02 Florida Medicare (primary) / PHI01 Philadelphia American Life (Medigap)", "insid": R.get("insid", ""), "insplans": "1st FLO02 Florida Medicare %s (patient order set 2,1 on 9/23) / PHI01 Philadelphia American Life %s" % (R.get("mbi", ""), R.get("medigap_id", "")),
            "need": "WILLIAM: the 1/27/2026 CCM visit (v19430630) has its 99487 (charge 23336997, $206, billed 1/31/2026 to PHI01) VOIDED - only the 99489 add-on (charge 23336998, $109, modifier 25) is live, re-billed 9/4/2026 to PHI01, and the Claim Inspector blocks it (Pattern 15775 'add-on without a primary'). No register or run section records that void. Say 'restore' and the run restores the 99487 (restore_charge.py) and sends the visit Medicare first, or 'void the 99489' / 'write off' and it closes the visit. Chart order was PHI01 seq 1 ahead of Medicare - fixed to Medicare first (insorder 2,1) this run.",
            "why": "Claim Inspector 9/23: v19430630 Pattern 15775 add-on 99489 without a primary procedure (the 99487 on the visit is voided)", "amount": 109, "status": "william", "created": NOW, "updated": NOW,
            "notes": [{"who": "Claude", "text": "Created by the 5 AM ET 9/23 run. Nothing is billed until you say restore or void.", "at": NOW}],
            "checks": [{"ok": "no", "src": "AMD gettxhistory typefilter 0 + charge detail (5am ET 9/23 run)", "result": "v19430630: 99487 charge 23336997 void=1 (billdate 01/31/2026 PHI01, paid 0); 99489 charge 23336998 live, mcode7, insbal 109.00, billed 09/04/2026 PHI01, paid 0; inspector Pattern 15775 + 4426 (not advisory - not bypassed)", "when": W},
                       {"ok": "ok", "src": "AMD ins_update sequence 2,1 (5am ET 9/23 run)", "result": "patient insorder 2,1 (Medicare FLO02 first, PHI01 Medigap second); readback ok; visit 19430630 already insorder 2,1", "when": W}]}})
ops.append({"op": "upsert", "collection": "items", "id": "jarvis-marisa-17477607",
    "set": {"id": "jarvis-marisa-17477607", "patient": J.get("patient", ""), "dob": J.get("dob", ""), "facility": "PRUITT SOUTHWOOD", "amdid": "17477607", "mbi": J.get("mbi", ""),
            "inscarrier": "FLO02 Florida Medicare / UNI01 United American (Medigap)", "insid": J.get("insid", ""), "insplans": "1st FLO02 Florida Medicare %s / 2nd UNI01 United American %s" % (J.get("mbi", ""), J.get("medigap_id", "")),
            "need": "Watching (nothing for William): Humana ERA 1052806 (9/21) answered CO-185/N767 on the 8/20/2026 99309 (v19453346) although Humana is not on the chart - a crossover Humana does not cover. Medicare paid $66.36 (9/16) + WOINS $57.71; the $16.93 coinsurance is at United American (Medigap) since 9/16, pending. Nothing written off, nothing rebilled.",
            "why": "ERA step 5 (5am ET 9/23 run): Humana check 1052806 denial-only line CO-185/N767 on a chart whose secondary is United American", "amount": 16.93, "status": "claude", "created": NOW, "updated": NOW,
            "notes": [{"who": "Claude", "text": "Created by the 5 AM ET 9/23 run as the record of the stray Humana denial; the United American secondary claim (billed 9/16) decides the $16.93.", "at": NOW}],
            "checks": [{"ok": "na", "src": "Humana ERA 1052806 line 15441550 (5am ET 9/23 run)", "result": "v19453346 99309 8/20/2026 CO-185 141.00 / N767, paid 0; live charge: carrier UNI01 billdate 09/16/2026, insbal 16.93, Medicare 819794238 66.36 + WOINS 57.71 (check 073041757 9/21); chart FLO02 seq 1 + UNI01 seq 2, no Humana plan", "when": W}]}})
app("thackeray-kendrew-17472874", "na", "%s: 15 April-2026 visits now held in the Claim Inspector ($2,403) - the 11 of before plus v19438061, v19438903, v19438993, v19439271, whose WEL04 PDTP0303 exclusion rows (run 1700229, $640) were completed outside the routine between 07:23Z and 09:15Z; same 'Hospitalization From Date empty' hold, no 99223 anchor within 45 days - unchanged, your turn for the HCA admission date." % SLOT)
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT[:900]))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 2 list rows, both PDTP0303 holds, none AET12; no claim run newer than 1700229." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (only the chat's paper_remits_posting_workbook_2026-09-23.xlsx, 04:48Z); no ScanSnap batch; Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the 01:33Z Pruitt readmit. ERA Center: one Humana check (1052806, $33.86) posted and cleared." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker) - hold Florida Blue patient statements." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 09:10-%s UTC 9/23, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops; rows on Claude's turn read - none updated since 07:00Z, no new William instruction since 0710Z. Sources: Pam Gmail nothing new; Drive facesheet folders / era downloads / treasury / ScanSnap nothing new after 07:26Z.
Claim runs: none new since 1700227-1700229 (9/22 21:06 AMD clock).
Columns: %s
%s
%s
%s
ERA step 5: %s
Write-offs: none. Insurance entered: none (pat17474541 chart order set Medicare first, insorder 2,1). Rebilled: none. Board: new rows rodway-rosalind-17474541 (William's turn) and jarvis-marisa-17477607 (watch); checks appended on thackeray-kendrew-17472874, era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918.
Script errors: none.
NEEDS WILLIAM: (1) rodway-rosalind-17474541 - restore the voided 99487 on v19430630 (1/27/2026 CCM) or void/write off the lone 99489 ($109); (2) alcott-alfie-17477183 - facesheet/card for coverage after 8/31/2026 ($141); (3) thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (15 inspector holds $2,403); (4) exclusion holds without a 99223 anchor: %s; (5) paste prompt v8 (+ v9 insert) - v7 still fires; upload the chat's PACKAGE 2026-09-23 paper-eobs-2 .b64 to Drive 'github mirror' (or push it); (6) AET12 carrier master (HOLD); (7) the standing items from the 0310Z-0710Z sections.
Calls learned: no new call shape (lesson recorded in the additions file: gettxhistory typefilter 0 is the only way to see a voided primary behind a Pattern 15775 add-on hold). Vocabulary: unchanged (55).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, INSP_TXT, UNB_TXT, EXCL_TXT, ERA_TXT, "; ".join("pat%s v%s %s $%s" % r[:4] for r in HELD_EX), MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("# %s run digest - backend billing run, %s slot (ehpa cloud)\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, SEC))
    print("final written")
print("outputs written: csv rows %d, board ops %d" % (len(rows), len(ops)))
