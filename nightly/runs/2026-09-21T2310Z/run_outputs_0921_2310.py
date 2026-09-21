# PLAIN ENGLISH (run outputs for the 7pm ET 9/21/2026 slot - ehpa cloud run 2026-09-21T2310Z)
# Decides: nothing. Reads this run's snapshots and writes: "_run report 9-21 2310.csv"; board_updates_2026-09-21T2310Z.json
#   (checks appends on the standing watch rows); a needs_facesheet_list.md section; the chat-history digest (--final, after
#   mirror_result.txt exists). Never touches: AMD, the board databases. Chart ids only - no patient names.
import csv, json, os, datetime, sys
S = "2026-09-21T2310Z"; SRC = "7pm ET 9/21 columns run (ehpa cloud)"; W = "9/21"; SLOT = "7 PM ET 9/21"
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
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty. Locks release-expired sent; era_post --all-unposted: nothing to post; fallback (payreasons.post_line, ERA-linked) 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835 in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing modified after 19:00Z 9/21 outside the routine's own files) - nothing to parse, post or reconcile; no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows." % (nb, ab, na, aa))
BOOT = "Bootstrap: repo ATTACHED (origin/main 612b405, session branch claude/pensive-einstein-y5gaf6), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 2110Z run's START has its RUN COMPLETE digest (21:47Z); proceeded 23:11Z. Registers from practices/ehpa/registers (224 files); needs_facesheet_list.md rebuilt from the 9/21 run sections on main; precheck_cache.json / laterality_flag_log.md / pseudonyms.json (223 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired; v8 (Drive 06:30Z, on main) not yet pasted - its rules followed."
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after; no new HCA feed batch this slot)")
add("Unbilled", "count", action="0 -> 0 (getclaimunbillablecharges totalcount 0 before and after; payreasons rows 0)")
add("Exclusions", "count", action="0 -> 0 rows on the per-run list calls (81 claim runs; overview 1/$198.00 lagging; no claim run newer than 1700211 at 9/20 02:04 AMD clock - no nightly claim run posted for 9/20 evening or 9/21). AET12: HOLD per William 9/21 - not rebilled, not re-verified this slot.")
add("ERA", "count", action=ERA_TXT)
add("Unpaid (7pm)", "count", action="precheck --days 3 --max 120: 20 patient/payer pairs checked (3 new lookups), 0 flagged. No rebills, no write-offs.")
add("Face sheets (7pm)", "sent", action="'current face sheets needed' email sent to dreffinger@gmail.com: none needed today (Garcia Mercedes, Duncan Joseph, Connell, Thomas Nancy, Gordon Sr all resolved); open decisions on William's turn listed (N286 cluster, AET12, Centene M56, Sunshine see-remit x2, MacDonald UHC, FCC contracting, pat17477777 pre-auth, Optum Pay remits, prompt v8).")
add("Sources", "read", action="Pam Gmail: no admit email newer than the three Brynwood readmit records of 16:46Z 9/21 (worked by the 1910Z run). Drive-wide: nothing modified after 19:00Z 9/21 outside the routine's own files (facesheet folders, Claimocity drop, 835 / Availity / treasury folders all quiet). Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated after 15:38Z (no new William note); 3 rows on William's turn re-read (jackson-linda-j-denials, macdonald-charles-17469645, walker-lenon-denials - denial decisions, unchanged).")
add("Boards", "read", action="Board inbox: 22 files present (9/20 0345Z - 9/21 2110Z), none in the board's applied map (registry lastCheck 06:36Z 9/21) - nothing trashed. Denials board registry: only the two 9/12 synctest files - nothing to trash.")
add("Routine", "note", action=BOOT)
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="medicaid-n286 cluster (pat17472419 x2, pat17472518 x7)", action="9 Medicaid-primary 99309s re-created under Effinger 9/13 ($1,269) deny CO208/N286 - referring provider on those visits' referral plan in the UI, then 'rebill'")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="Medicaid FFS answers every FCC-dual crossover CO256 - 8 coinsurance lines $180.07 held (pat24039, pat20863) - FCC contracting / payer id")
add("Open on William's turn", "note", patient="Automation Center", action="no nightly claim run since 1700211 (9/20 02:04) - the EOD close looks stopped again; the 2110Z run's 3 rebills wait on it")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-21 2310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result):
    ops.append({"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700211 (9/20 02:04) - no nightly claim run has posted for 9/20 evening or 9/21." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing modified after 19:00Z 9/21 outside the routine's own files) - nothing to parse, post or reconcile; Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked. 7pm precheck --days 3: 20 pairs, 0 flagged; 'current face sheets needed' email sent (none needed today)." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 23:09-%s UTC 9/21, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no row updated after 15:38Z; 3 rows on William's turn (denial decisions, unchanged). Sources: Drive-wide nothing modified after 19:00Z 9/21 outside the routine's own files; Claimocity drop: nothing; Pam Gmail: nothing newer than the three 16:46Z readmit records (worked 1910Z).
Claim runs: none newer than 1700211 (9/20 02:04 AMD clock; 81 runs) - no nightly claim run posted for 9/20 evening or 9/21.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 0 -> 0 | Exclusions 0 -> 0 rows (overview 1/$198 lagging). AET12: HOLD.
ERA step 5: %s
7pm extras: precheck --days 3 --max 120: 20 pairs, 0 flagged; 'current face sheets needed' email sent to dreffinger@gmail.com (none needed today; open decisions listed); run report CSV also uploaded to Drive 'bht hca facesheets'.
Write-offs: none. Rebilled: none. Insurance entered: none.
NEEDS WILLIAM (unchanged): (1) paste prompt v8; (2) board row medicaid-n286-referring-provider-0921 ($1,269, 9 visits) - referring provider on the re-created Effinger visits, then 'rebill'; (3) AET12 carrier master (HOLD); (4) centene-m56-denials-0920 ($772.92); (5) FCC contracting (8 lines $180.07 held); (6) nightly claim run stopped again after 1700211; (7) pat17477777 rplan18462071 Pre-Auth # (UI); (8) 6 Optum Pay remits; (9) BCBS patient-balance audit parked.
Calls learned: no new call shapes. Vocabulary unchanged (54).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-21_2310UTC run digest - backend billing run, 7 PM ET 9/21 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918) uploaded; nothing trashed (none of the 22 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0 (54 calls). Postman: unchanged.
Mirror: %s

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("digest written")
print("csv rows", len(rows), "| board ops", len(ops))
