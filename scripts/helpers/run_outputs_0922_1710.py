# PLAIN ENGLISH (run outputs for the 1pm ET 9/22/2026 slot - ehpa cloud run 2026-09-22T1710Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after) and writes:
#   "_run report 9-22 1710.csv"; board_updates_2026-09-22T1710Z.json (checks appends on the standing rows only - no new
#   row this run); a needs_facesheet_list.md section; the chat-history digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-22T1710Z"; SRC = "1pm ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "1 PM ET 9/22"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. GET /api/era/checks was EMPTY at 17:25Z (the 1512Z run had cleared the last CAP07 check); locks release-expired sent; era_post --all-unposted: 0 checks; fallback dry+live: 0 lines; era_clear dry+live: 0 checks; no new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide search modifiedTime > 14:30Z 9/22 across the seven watched folders returned only the 1512Z run's own additions file); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows. Nothing posted, nothing dismissed, nothing written off." % (nb, ab, na, aa))
BOOT = ("Bootstrap: repo ATTACHED (origin/main 9b22436 = the 1512Z run's mirror commit; session branch claude/pensive-einstein-9lukn2), bootstrap net = AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 17:24Z (columns_scan_0912.py before), no login lock. Cross-container guard: the 1512Z START has its RUN COMPLETE digest (15:30Z); START marker 2026-09-22T1710Z uploaded 17:23Z, lock written 17:22Z. Layout: tools/bootstrap_workspace.sh layout copied 535 helpers from main into /home/claude/unbilled (carriers.json simple form, 124 codes; tesseract + poppler present); registers = practices/ehpa/registers from main (265 files, symlinked as /home/claude/unbilled/registers and /home/claude/practices/ehpa/registers); needs_facesheet_list.md rebuilt from the run sections in main (nightly/runs/*/needs_facesheet_list_section_*.md; the Drive 9/21 07:50Z body not re-downloaded), laterality_flag_log.md (Drive 9/22 11:45Z), precheck_cache.json (Drive 9/21 23:28Z), pseudonyms.json (231 names, Drive 15:29Z) from 'workspace mirror'; bootstrap check: 2 optional/required helpers reported absent (github_sync.py optional; columns_inspector2_0908.py and era_details_pull.py are not in main - not rewritten; columns_scan_0912.py + era_step_b_0913.py do their work). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules (payreasons repair, ERA-linked fallback, sweep rule) + the 9/22 DECEASED GUARD apply - no claim left this run at all, so no date-of-death lookup was needed.")
COLS = ("Charge Review 0 -> 0 | Claim Inspector 11 -> 11 (all pat17472874, the April-2026 stay held for William's admission date - error ids 394797-394807 unchanged, no new visit on any of the 7 batches) | Unbilled 1 -> 1 (the known v19441047 MCAD $16.93 crossover hold) | Exclusions 0 -> 0 rows on every claim run (overview 1/$198 lagging; getclaimrunstatus 82 runs, newest still 1700216, AMD clock 9/21 21:09 - no nightly claim run has posted for 9/22 yet). "
        "No new charge-review visit, no new inspector batch, no new unbilled row, no new exclusion since the 1512Z run - nothing to edit, bypass, release or complete. AET12: HOLD per William 9/21 - not rebilled, not re-verified.")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty)")
add("Claim Inspector", "count", action="11 -> 11 (7 batches 126638/126640/126664/126671/126691/126707/126725; all pat17472874's April-2026 stay, held for the admission date - unchanged)")
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row thackeray-kendrew-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="1 -> 1 (v19441047 held as before)")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026 - releasing would only hide it)", amount="16.93")
add("Exclusions", "count", action="0 -> 0 rows on every claim run (overview 1/$198 lagging; no claim run newer than 1700216). AET12: HOLD per William 9/21.")
add("ERA", "count", action=ERA_TXT)
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): only the three 16:46Z 9/21 readmit records already worked (1910Z 9/21). Drive: nothing new in the hca/tmh/PCC/Claimocity facesheet folders, 'bht Optum era downloads', 'treasury payments' or 'billing agent project files' since 14:30Z 9/22 except the 1512Z run's own additions file. Board drops 0; Working Denials queue 0; Insurance Refresh Board: the rows updated 16:55-16:57Z 9/22 are the board applying the 1512Z inbox file, no row updated after 16:57:35Z - no new William note.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17476603", action="row chp-coa1-17476603: CHP CO-A1 (no remark) on the 5/21/2026 HCA 99232 ($111) - CHP active, Lantern/SurgeryPlus listed as primary since 11/3/2025: SurgeryPlus surgical episode (bill Lantern) or appeal CHP?")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row thackeray-kendrew-17472874")
add("Open on William's turn", "note", patient="AWV PR-119 x2", action="row awv-pr119-0922: pat23617 + pat21885 G0439 7/13/2026 ($408) - appeal with the 11-full-months calculation, or WONCS")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 1710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, notes=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if notes: o["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(o)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new in the seven watched folders after 14:30Z 9/22 except the 1512Z run's own additions file); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - nothing changed since 1512Z, still your turn for the HCA admission date." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 17:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (rows updated 16:55-16:57Z 9/22 = the board applying the 1512Z inbox file; nothing updated after 16:57:35Z). Sources: nothing new in the facesheet folders, the Claimocity drop, 'bht Optum era downloads' or 'treasury payments'; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records (worked 1910Z 9/21).
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock; 82 runs listed).
Columns: %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none. No claim left this run. Board: no new row; checks appended on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918, thackeray-kendrew-17472874.
Script errors: none.
NEEDS WILLIAM: (0) chp-coa1-17476603 - Lantern/SurgeryPlus bundle or appeal to CHP ($111); (1) board row thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (2) awv-pr119-0922 - appeal or WONCS on the two 7/13/2026 AWVs ($408); (3) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (4) paste prompt v8; (5) AET12 carrier master (HOLD); (6) centene-m56-denials-0920 ($772.92); (7) FCC balances (reconcile paper checks / Square before any FLO99 write-off); (8) pat17477777 rplan18462071 Pre-Auth # (UI); (9) 6 Optum Pay remits.
Calls learned: no new call shapes. Vocabulary unchanged (54).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 1 PM ET 9/22 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + SEC + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("final written")
print("outputs written: %d csv rows, %d board ops" % (len(rows), len(ops)))
