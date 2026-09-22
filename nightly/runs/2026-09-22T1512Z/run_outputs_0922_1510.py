# PLAIN ENGLISH (run outputs for the 11am ET 9/22/2026 slot - ehpa cloud run 2026-09-22T1512Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after, the denial register) and writes:
#   "_run report 9-22 1510.csv"; board_updates_2026-09-22T1512Z.json (checks appends on the standing rows + the new
#   chp-coa1-17476603 row on William's turn); the ERA denial register for check 1051732; a needs_facesheet_list.md
#   section; the chat-history digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-22T1512Z"; SRC = "11am ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "11 AM ET 9/22"
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
# ERA denial register for check 1051732 (CAP07 4123363, $469.27, dated 9/22)
DEN = [
 {"checkid": "1051732", "checkclaimid": 15440355, "visitid": "19375395", "chargeid": "22443545", "pid": "17471007", "dos": "02/02/2024", "cpt": "99232", "carc": "CO29", "rarc": "N702", "amount": 111.0,
  "outcome": "already-settled", "why": "live gettxhistory: CHP paid $75.68 (check 4015323, 9/25/2024) after a $-75.68 reversal 3/11/2024; contractual -35.32 and WOINSBANK -75.68 (5/30/2026); insurance and patient balance $0. The 9/16/2026 freq-1 rebill drew the CO-29. Nothing to post, nothing to write off, never rebill."},
 {"checkid": "1051732", "checkclaimid": 15440356, "visitid": "19442947", "chargeid": "23351214", "pid": "17476603", "dos": "05/21/2026", "cpt": "99232", "carc": "COA1", "rarc": "", "amount": 111.0,
  "outcome": "denial-william", "why": "CHP $0 CO-A1 (no remark code) on the 5/21/2026 99232 billed 9/10/2026, $111 open on insurance. Cascade: AMD 271 on the CHP plan ACTIVE (HMO commercial); Stedi CHP 95112 at DOS 5/21/2026 ACTIVE Commercial HMO, plan begin 1/1/2019, but CHP lists 'Lantern (was SurgeryPlus)' as an Other/Additional Payor - Primary Payer, group policy, coordination of benefits 11/3/2025-open; Stedi MBI lookup NC + FL ERR 72 (not a Medicare beneficiary, age 64 at DOS). No write, no rebill: board row chp-coa1-17476603 on William's turn (was the 5/21/2026 HCA stay a Lantern/SurgeryPlus surgical episode -> bill Lantern; otherwise appeal/call CHP 850-523-7361 for the A1 reason)."},
]
os.makedirs("registers", exist_ok=True)
json.dump({"stamp": S, "check": "1051732", "lines": DEN}, open("registers/era_denials_1051732_%s.json" % S, "w"), indent=1)
ERA_TXT = ("%d unposted check / $%.2f before -> %d / $%.2f after. One new Capital Health Plan check (CAP07 1051732, check 4123363, $469.27, dated 9/22) with 6 claim lines: the ERA Center Post button (era_post --all-unposted) posted all 4 paid lines, $469.27 - pat17473782 v19454879 99223 9/14 $199.63 (+$110.37 CO-45), v19454912 99232 9/15 $89.88 (+$21.12), v19454938 99232 9/16 $89.88 (+$21.12); pat17477720 v19454894 99232 9/14 $89.88 (+$21.12); fallback dry+live: 0 lines (4 'already posted'); residual disregarded $0. Two $0 denial lines: pat17471007 v19375395 99232 2/2/2024 CO-29 = already settled (CHP paid $75.68 9/25/2024, WOINSBANK 5/30/2026, $0 open - the 9/16 rebill drew it); pat17476603 v19442947 99232 5/21/2026 CO-A1 no remark, $111 open -> cascade run (CHP ACTIVE at DOS, Lantern/SurgeryPlus listed as COB primary since 11/3/2025, not Medicare) -> board row chp-coa1-17476603 on William's turn, nothing written off. era_clear dismissed 1051732 (2 denial lines held for the cascade, register era_denials_1051732_%s.json); GET /api/era/checks after = 0. Locks release-expired sent; no new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (only the six UHC rejected_claims CSVs of 9/22 00:0xZ, worked 0110Z); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows." % (nb, ab, na, aa, S))
BOOT = ("Bootstrap: repo ATTACHED (origin/main b976088 = the 1310Z run's mirror commit; session branch claude/pensive-einstein-d0i4ng), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success 15:18Z, no login lock. Cross-container guard: the 1310Z START has its RUN COMPLETE digest (13:30Z); START marker 2026-09-22T1512Z uploaded 15:17Z, lock written. Registers from practices/ehpa/registers (261 files, symlinked as /home/claude/unbilled/registers and /home/claude/practices/ehpa/registers); needs_facesheet_list.md (Drive 9/21 07:50Z copy + the 12 run sections since, from main), laterality_flag_log.md (9/22 11:45Z), precheck_cache.json (9/21 23:28Z), pseudonyms.json (227 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules (payreasons repair, ERA-linked fallback, sweep rule) + the 9/22 DECEASED GUARD followed - no claim left this run at all.")
COLS = ("Charge Review 0 -> 0 | Claim Inspector 11 -> 11 (all pat17472874, the April-2026 stay held for William's admission date - unchanged since 1110Z, no new visit on any batch) | Unbilled 1 -> 1 (the known v19441047 MCAD $16.93 crossover hold) | Exclusions 0 -> 0 rows (overview 1/$198 lagging; no claim run newer than 1700216, 9/21 21:09 AMD clock). "
        "No new charge-review visit, no new inspector batch, no new unbilled row, no new exclusion since the 1310Z run - nothing to edit, bypass, release or complete. AET12: HOLD per William 9/21 - not rebilled, not re-verified.")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty)")
add("Claim Inspector", "count", action="11 -> 11 (7 batches; all pat17472874's April-2026 stay, held for the admission date - unchanged)")
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row tillman-kenneth-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="1 -> 1 (v19441047 held as before)")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026)", amount="16.93")
add("Exclusions", "count", action="0 -> 0 rows on every claim run (overview 1/$198 lagging; no claim run newer than 1700216). AET12: HOLD per William 9/21.")
add("ERA", "count", action=ERA_TXT)
for v, cpt, d, amt, wo in (("19454879", "99223", "9/14/2026", "199.63", "110.37"), ("19454912", "99232", "9/15/2026", "89.88", "21.12"), ("19454938", "99232", "9/16/2026", "89.88", "21.12")):
    add("ERA", "auto-posted", check="1051732", payer="CAP07 Capital Health Plan 4123363", patient="pat17473782", visit=v, dos=d, amount=amt, error="CO-45 %s" % wo, action="posted by the ERA Center Post button (posterapayments), %s" % cpt)
add("ERA", "auto-posted", check="1051732", payer="CAP07 Capital Health Plan 4123363", patient="pat17477720", visit="19454894", dos="9/14/2026", amount="89.88", error="CO-45 21.12", action="posted by the ERA Center Post button (posterapayments), 99232")
add("ERA", "already settled", check="1051732", payer="CAP07 Capital Health Plan 4123363", patient="pat17471007", visit="19375395", dos="2/2/2024", amount="111.00", error="CO-29 untimely (N702)", action="CHP paid $75.68 9/25/2024, WOINSBANK 5/30/2026 - $0 open; the 9/16/2026 freq-1 rebill drew the CO-29; nothing to do, never rebill")
add("ERA", "denial - William", check="1051732", payer="CAP07 Capital Health Plan 4123363", patient="pat17476603", visit="19442947", dos="5/21/2026", amount="111.00", error="CO-A1 no remark code", action="cascade: CHP ACTIVE at DOS (Stedi 95112 + AMD 271), Lantern (SurgeryPlus) listed as COB primary payer since 11/3/2025, not Medicare (MBI ERR 72 NC/FL) -> board row chp-coa1-17476603 on William's turn: SurgeryPlus episode -> bill Lantern, else appeal/call CHP for the A1 reason; nothing written off")
add("ERA", "cleared", check="1051732", payer="CAP07 Capital Health Plan 4123363", amount="469.27", action="era_clear dismiss -> ok (all money posted); GET /api/era/checks after = 0")
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): only the three 16:46Z 9/21 readmit records already worked (1910Z). Drive: nothing new in the hca/tmh/PCC/Claimocity facesheet folders, 'bht Optum era downloads' or 'treasury payments' since the 0110Z run (the 'FCC checks & EOBs' subfolder + FCC open balances sheet of 06:31Z were the 0710Z/chat session's). Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated after 13:00Z 9/22 - no new William note.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17476603", action="NEW row chp-coa1-17476603: CHP CO-A1 (no remark) on the 5/21/2026 HCA 99232 ($111) - CHP active, Lantern/SurgeryPlus listed as primary since 11/3/2025: was the stay a SurgeryPlus surgical episode (bill Lantern) or should the run appeal CHP?")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row tillman-kenneth-17472874")
add("Open on William's turn", "note", patient="AWV PR-119 x2", action="row awv-pr119-0922: pat23617 + pat21885 G0439 7/13/2026 ($408) - appeal with the 11-full-months calculation, or WONCS")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 1510.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, notes=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if notes: o["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(o)
# new row on William's turn (created this run -> full row via upsert set; PHI kept out of this file)
ops.append({"op": "upsert", "collection": "items", "id": "chp-coa1-17476603", "set": json.load(open("private_0922_1510.json"))})  # the row text (name, DOB, member id, address) lives in the never-committed private_0922_1510.json
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new there since the six UHC rejected_claims CSVs of 9/22 00:0xZ, worked 0110Z); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("tillman-kenneth-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - nothing changed since 1310Z, still your turn for the HCA admission date." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 15:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (no row updated after 13:00Z 9/22). Sources: nothing new in the facesheet folders, the Claimocity drop, 'bht Optum era downloads' or 'treasury payments'; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records (worked 1910Z).
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock).
Columns: %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none. No claim left this run. Board: NEW row chp-coa1-17476603 on William's turn (CHP CO-A1 / Lantern COB question, $111).
Script errors: none.
NEEDS WILLIAM: (0) NEW chp-coa1-17476603 - Lantern/SurgeryPlus bundle or appeal to CHP ($111); (1) board row tillman-kenneth-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (2) awv-pr119-0922 - appeal or WONCS on the two 7/13/2026 AWVs ($408); (3) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (4) paste prompt v8; (5) AET12 carrier master (HOLD); (6) centene-m56-denials-0920 ($772.92); (7) FCC balances (reconcile paper checks / Square before any FLO99 write-off); (8) pat17477777 rplan18462071 Pre-Auth # (UI); (9) 6 Optum Pay remits.
Calls learned: no new call shapes. Learned: a CHP 271 can carry 'Lantern (was SurgeryPlus)' as an Other/Additional Payor - Primary Payer with a COB window - an employer surgical-bundle program, not a medical insurer; treat it as a William question, never as a wrong-payer re-route. Vocabulary unchanged (54).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 11 AM ET 9/22 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + SEC + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("final written")
print("outputs written: %d csv rows, %d board ops" % (len(rows), len(ops)))
