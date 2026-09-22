# PLAIN ENGLISH (run outputs for the 9am ET 9/22/2026 slot - ehpa cloud run 2026-09-22T1310Z)
# Decides: nothing. Reads this run's snapshots (columns before/final, ERA before/after, the denial register) and writes:
#   "_run report 9-22 1310.csv"; board_updates_2026-09-22T1310Z.json (checks appends on the standing rows);
#   a needs_facesheet_list.md section; the chat-history digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-22T1310Z"; SRC = "9am ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "9 AM ET 9/22"
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
ERA_TXT = ("%d unposted check / $%.2f before -> %d / $%.2f after. One new $0 Centene check (WEL04 1051731, trace 1003560795, dated 9/21, received 05:30Z 9/22) with 19 denial claims on 3 charts: every line sits on a charge already at $0 (live gettxhistory read, pages 1+2) - 15 CO-18 duplicates on pat17470743's Nov-Dec 2023 HCA visits (WellCare paid them 3/10/2024; the 9/11/2026 freq-1 rebill drew the duplicates; residuals written off WOMCAD 9/22 by the chat batch), 4 CO-29 untimely (pat17470743 x2 2023, pat12231996 8/4/2025, pat12182947 9/2/2025 - all WOINS'd 9/6 or WOMCAD'd 9/22), CO-96/N448 + CO-4/N56 on pat12231996's 8/17/2025 99487+99489 (WOINS 9/6/2026), and one CO-23/OA-23 secondary line (pat12231996 9/18/2025 99223+99497) already carrying WellCare's 9/15 payment + Medicaid's WOCAID2ND. Nothing posted, nothing rebilled, nothing written off; era_post 0 checks; fallback 0 lines; era_clear dismissed 1051731 (held 19 'denial with write-off' lines for the cascade = all already settled, register era_denials_1051731_%s.json); GET /api/era/checks after = 0. Locks release-expired sent; no new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/22 00:10Z); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows." % (nb, ab, na, aa, S))
BOOT = ("Bootstrap: repo ATTACHED (origin/main ca69bf1 = the 1110Z run's mirror commit; session branch claude/pensive-einstein-2rctvi), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success 13:2xZ, no login lock. Cross-container guard: the 1110Z START has its RUN COMPLETE digest (11:48Z); START marker 2026-09-22T1310Z uploaded 13:21Z, lock written. Registers from practices/ehpa/registers (257 files, symlinked as /home/claude/unbilled/registers and /home/claude/practices/ehpa/registers); precheck_cache.json / laterality_flag_log.md / pseudonyms.json (227 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules (payreasons repair, ERA-linked fallback, sweep rule) + the 9/22 DECEASED GUARD followed - no claim left this run at all.")
COLS = ("Charge Review 0 -> 0 | Claim Inspector 11 -> 11 (all pat17472874, the April-2026 stay held for William's admission date - unchanged since 1110Z, no new visit on any batch) | Unbilled 1 -> 1 (the known v19441047 MCAD $16.93 crossover hold) | Exclusions 0 -> 0 rows (overview 1/$198 lagging; no claim run newer than 1700216, 9/21 21:09 AMD clock). "
        "No new charge-review visit, no new inspector batch, no new unbilled row, no new exclusion since the 1110Z run - nothing to edit, bypass, release or complete. AET12: HOLD per William 9/21 - not rebilled, not re-verified.")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty)")
add("Claim Inspector", "count", action="11 -> 11 (7 batches; all pat17472874's April-2026 stay, held for the admission date - unchanged)")
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row thackeray-kendrew-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="1 -> 1 (v19441047 held as before)")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026)", amount="16.93")
add("Exclusions", "count", action="0 -> 0 rows on every claim run (overview 1/$198 lagging; no claim run newer than 1700216). AET12: HOLD per William 9/21.")
add("ERA", "count", action=ERA_TXT)
add("ERA", "already settled", check="1051731", payer="WEL04 Centene 1003560795", patient="pat17470743", visit="19368915 19368940 19369104 19369118 19369143 19369242 19369256 19369405 19369423 19369510 19372791 19372801 19372810 19373636 19373650", dos="11/6-12/27/2023", amount="2196.00", error="CO-18 exact duplicate x13, CO-29 untimely x2", action="paid by WellCare 3/10/2024, residuals WOMCAD 9/22/2026 (chat batch) - $0 open; never rebill (the 9/11/2026 freq-1 rebill drew the duplicates)")
add("ERA", "already settled", check="1051731", payer="WEL04 Centene 1003560795", patient="pat12231996", visit="19412901 / 19413587 / 19417241", dos="8/4, 8/17, 9/18/2025", amount="683.00", error="CO-29; CO-96/N448 + CO-4/N56; CO-23/OA-23 (secondary)", action="all at $0 (WOINS 9/6/2026; WellCare -132.31 + WOCAID2ND on the 9/18 visit) - nothing open")
add("ERA", "already settled", check="1051731", payer="WEL04 Centene 1003560795", patient="pat12182947", visit="19417150", dos="9/2/2025", amount="107.00", error="CO-29 untimely", action="WOINS 9/6/2026, $0 open - nothing to do")
add("ERA", "cleared", check="1051731", payer="WEL04 Centene 1003560795", amount="0.00", action="era_clear dismiss -> ok; GET /api/era/checks after = 0")
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): only the three 16:46Z 9/21 readmit records already worked (1910Z). Drive: nothing new in the hca/tmh/PCC/Claimocity facesheet folders, 'bht Optum era downloads' or 'treasury payments' since 9/22 00:10Z. Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated after 11:00Z 9/22 - no new William note.")
add("Boards", "read", action="Board inbox: 28 files present (9/20 0345Z - 9/22 1110Z), none in the board's applied map (registry lastCheck 07:11Z 9/22) - nothing trashed. Denials board registry: only the two 9/12 synctest files - nothing to trash.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row thackeray-kendrew-17472874")
add("Open on William's turn", "note", patient="AWV PR-119 x2", action="row awv-pr119-0922: pat23617 + pat21885 G0439 7/13/2026 ($408) - appeal with the 11-full-months calculation, or WONCS")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 1310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, notes=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if notes: o["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(o)
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/22 00:10Z); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - nothing changed since 1110Z, still your turn for the HCA admission date." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 13:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (no row updated after 11:00Z 9/22). Sources: nothing new in the facesheet folders, the Claimocity drop, 'bht Optum era downloads' or 'treasury payments'; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records (worked 1910Z).
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock).
Columns: %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none. No claim left this run.
Script errors: none.
NEEDS WILLIAM (unchanged): (1) board row thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (2) awv-pr119-0922 - appeal or WONCS on the two 7/13/2026 AWVs ($408); (3) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (4) paste prompt v8; (5) AET12 carrier master (HOLD); (6) centene-m56-denials-0920 ($772.92); (7) FCC balances (reconcile paper checks / Square before any FLO99 write-off); (8) pat17477777 rplan18462071 Pre-Auth # (UI); (9) 6 Optum Pay remits.
Calls learned: no new call shapes. Learned: gettxhistory is paged even in the txh.fetch shape (typefilter=0) - pat17470743's 195 charges came back 102 on page 1 and 93 on page 2, so the 2023 visits of the WEL04 check were invisible to every page-1 helper; read pagenumber 2+ when an ERA line's visit is missing. Vocabulary unchanged (54).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 9 AM ET 9/22 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + SEC + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("final written")
print("outputs written: %d csv rows, %d board ops" % (len(rows), len(ops)))
