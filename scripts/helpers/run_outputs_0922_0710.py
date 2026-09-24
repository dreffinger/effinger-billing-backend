# PLAIN ENGLISH (run outputs for the 3am ET 9/22/2026 slot - ehpa cloud run 2026-09-22T0710Z)
# Decides: nothing. Reads this run's snapshots (columns before/final, ERA before/after, the inspector register) and writes:
#   "_run report 9-22 0710.csv"; board_updates_2026-09-22T0710Z.json (checks appends on the standing watch rows only - no
#   status/need changes); a needs_facesheet_list.md section; the chat-history digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only in the section/digest and the board appends.
import csv, json, os, datetime, sys
S = "2026-09-22T0710Z"; SRC = "3am ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "3 AM ET 9/22"
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
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty. Locks release-expired sent; era_post --all-unposted: nothing to post; fallback (era_fallback_0913b, ERA-linked payreasons.post_line) 0 lines, 0 faults; era_clear 0 looked at, 0 dismissed; no new 835 in 'bht Optum era downloads' (its newest files are the six 9/22 00:00-00:05Z UHC rejected_claims CSVs, worked by the 0110Z run); no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide the only file modified after 05:30Z 9/22 is the chat session's 'FCC open balances by patient (9-22-2026)' sheet at 06:31Z); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows." % (nb, ab, na, aa))
BOOT = "Bootstrap: repo ATTACHED (origin/main 137cda0, session branch claude/pensive-einstein-xm1xe9), AMD_OK (AMD REST root 404 = reachable), STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success 07:17Z, no login lock. Cross-container guard: the 0510Z START has its RUN COMPLETE digest (06:08Z); START marker 2026-09-22T0710Z uploaded 07:16Z, lock written. Registers from practices/ehpa/registers (250 files); precheck_cache.json / laterality_flag_log.md / pseudonyms.json from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache, insp_0922_0710.py does the inspector). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 (on main and Drive) rules followed."
COLS = ("Charge Review 0 -> 0 | Claim Inspector 21 -> 11 (all pat17472874, the April-2026 stay held for William's admission date) | Unbilled 1 -> 1 (the known v19441047 MCAD $16.93 crossover hold) | Exclusions 0 -> 0 rows (overview 1/$198 lagging; no claim run newer than 1700216). "
        "CLAIM INSPECTOR: the same repoint/re-render wave as the 0510Z slot (chat commits 1995a1d Humana Garland-G->Effinger and 137cda0 FCC resubmission resave old visits without extins, which wipes hospitalizationfrom on PAID hospital visits): (1) admission dates written back (updextrainsinfo hospitalizationfrom only) and full-visit resaved onhcfa=1 with every live charge echoed by id (--allow-paid, payments untouched, readback live=n/n) on pat17472393 x4 (8/27/2026 own 99223 + 9/1, 9/3, 9/4 99233s -> 08/27/2026), pat17472517 x2 (2/20/2026 99233 -> 02/18/2026; 11/12/2025 99233 -> 11/08/2025, most recent 99223 within 45d), and the unpaid pat44953 8/7/2026 99239 -> 08/04/2026; (2) CCM advisories bypassed with fresh ids: pat23161 v19455335 (a re-created 12/1/2025 99487+99489 on batch 1, Patterns 35790 + 7011), pat17472396 v19448871 and pat22858 v19452423 (Pattern 35790). Primary-dx gate: no never-primary first code on any of the 21 visits. "
        "HELD: pat17472874 x11 (99233 4/7-4/19 + 99239 4/21/2026, WEL04, $1,763): no 99223 within 45 days, no sibling visit carries an admission date - board row thackeray-kendrew-17472874 stays on William's turn. "
        "UNBILLED: only the known v19441047 hold. EXCLUSIONS: 0 rows on every run. AET12: HOLD per William 9/21 - not rebilled, not re-verified.")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty)")
add("Claim Inspector", "count", action="21 -> 11 (17 batches; the 11 left are pat17472874's April-2026 stay, held for the admission date)")
add("Claim Inspector", "cleared", patient="pat17472393", visit="19453088 / 19453500 / 19453716 / 19453750", dos="8/27-9/4/2026", error="Hospitalization From Date empty", action="PAID visits whose admission date the chat repoint wiped: 08/27/2026 (own 99223) written back on 99223/99497/99233, resaved onhcfa=1 with every live charge echoed (--allow-paid); 99497 keeps mcode7")
add("Claim Inspector", "cleared", patient="pat17472517", visit="19433214 / 19423205", dos="2/20/2026 / 11/12/2025", error="Hospitalization From Date empty", action="PAID visits: admission 02/18/2026 and 11/08/2025 (most recent 99223 within 45d) written back, resaved onhcfa=1 (--allow-paid)")
add("Claim Inspector", "cleared", patient="pat44953", visit="19450843", dos="8/7/2026", error="Hospitalization From Date empty", action="admission 08/04/2026 (most recent 99223 within 45d) written, resave onhcfa=1")
add("Claim Inspector", "cleared", patient="pat23161 / pat17472396 / pat22858", visit="19455335 / 19448871 / 19452423", error="Patterns 35790 / 7011 (CCM add-on / frequency advisories)", action="bypassed with fresh ids; no resave needed")
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row thackeray-kendrew-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="1 -> 1 (v19441047 held as before)")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026)", amount="16.93")
add("Exclusions", "count", action="0 -> 0 rows on every claim run (overview 1/$198 lagging; no claim run newer than 1700216). AET12: HOLD per William 9/21.")
add("ERA", "count", action=ERA_TXT)
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): the three 16:46Z 9/21 readmit records already worked by the 1910Z run - nothing newer. Drive-wide: nothing modified after 05:30Z 9/22 except the chat session's FCC balances sheet (06:31Z). Facesheet folders, Claimocity drop, 835 / Availity / treasury folders quiet. Board drops 0; Working Denials queue 0; Insurance Refresh Board: rows updated 07:11-07:16Z 9/22 are the page applying the 0510Z run's file (checks echoes) - no new William note seen.")
add("Boards", "read", action="Board inbox: 26 files present (9/20 0345Z - 9/22 0510Z), none in the board's applied map (registry lastCheck 07:11Z 9/22) - nothing trashed. Denials board registry: only the two 9/12 synctest files - nothing to trash.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row thackeray-kendrew-17472874")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute); 8 coinsurance lines $180.07 (pat24039, pat20863)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 0710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, notes=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if notes: o["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(o)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing new after 05:30Z 9/22 except the chat's FCC balances sheet); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - no 99223 within 45 days and no sibling visit carries the admission date; nothing changed, still your turn for the HCA admission date." % SLOT)
app("orwell-padraig-44953", "ok", "%s: his 8/7/2026 99239 (v19450843) surfaced in the Claim Inspector with no admission date (the chat session's referral-plan repoint resaved it); 08/04/2026 (most recent 99223 within 45 days) written and the visit resaved onhcfa=1 - inspector clear, nothing needed from you." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 07:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (rows updated 07:11-07:16Z are the page applying the 0510Z file). Sources: Drive-wide nothing modified after 05:30Z 9/22 except the chat session's 'FCC open balances by patient (9-22-2026)' sheet (06:31Z); Claimocity drop: nothing; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records (worked 1910Z).
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock).
Columns: %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none.
Script errors: none.
NEEDS WILLIAM: (1) board row thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (2) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (3) paste prompt v8; (4) AET12 carrier master (HOLD); (5) centene-m56-denials-0920 ($772.92); (6) FCC balances (reconcile paper checks / Square before any FLO99 write-off); (7) pat17477777 rplan18462071 Pre-Auth # (UI); (8) 6 Optum Pay remits.
Calls learned: no new call shapes. Learned behaviour (repeat of 0510Z): a chat-session referral-plan repoint / re-render (updvisitwithcharges without extins) wipes hospitalizationfrom on PAID hospital visits and puts them in the Claim Inspector; updextrainsinfo + a full-visit resave with every live charge echoed restores them without touching payments. Vocabulary unchanged (54).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 3 AM ET 9/22 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + SEC + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("final written")
print("outputs written: %d csv rows, %d board ops" % (len(rows), len(ops)))
