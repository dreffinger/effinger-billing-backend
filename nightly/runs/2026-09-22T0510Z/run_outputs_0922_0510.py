# PLAIN ENGLISH (run outputs for the 1am ET 9/22/2026 slot - ehpa cloud run 2026-09-22T0510Z)
# Decides: nothing. Reads this run's snapshots (columns before/final, ERA before/after) and writes: "_run report 9-22 0510.csv";
#   board_updates_2026-09-22T0510Z.json (checks appends on the standing watch rows, new rows for the two new HCA charts and the
#   Tillman admission-date hold); a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only in the section/digest; patient names only in the board file (William's Drive inbox).
import csv, json, os, datetime, sys
S = "2026-09-22T0510Z"; SRC = "1am ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "1 AM ET 9/22"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); ov = before.get("overview", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty. Locks release-expired sent; era_post --all-unposted: nothing to post; fallback (era_fallback_0913b, ERA-linked payreasons.post_line) 0 lines, 0 faults; era_clear 0 looked at, 0 dismissed; no new 835 in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new anywhere in Drive after 03:23Z 9/22; the six UHC rejected_claims CSVs of 00:00-00:05Z were worked by the 0110Z run); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows." % (nb, ab, na, aa))
BOOT = "Bootstrap: repo ATTACHED (origin/main c6fe805, session branch claude/pensive-einstein-vlnp40), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 0310Z run's START has its RUN COMPLETE digest (03:22Z); proceeded 05:15Z. Registers from practices/ehpa/registers (227 files); needs_facesheet_list.md rebuilt from the 32 run sections on main; precheck_cache.json / laterality_flag_log.md / pseudonyms.json from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired; v8 (on main and Drive) rules followed."
COLS = ("Charge Review 0 -> 0 | Claim Inspector 37 -> 11 (all pat17472874) | Unbilled 19 -> 1 (the known v19441047 MCAD $16.93 crossover hold) | Exclusions 3 -> 0 rows (claim run 1700216, 9/21 21:09 AMD clock, 55 claims - the first nightly claim run since 1700211). "
        "CLAIM INSPECTOR: the 9/22 chat session's referring-provider correction (registers/fix_refprov_2026-09-22.txt: referral plans repointed rprov15 -> rprov13 on 96 charts) resaved old hospital and CCM visits, which re-ran the inspector and WIPED the Extra-Info admission date on already-PAID hospital visits. Worked in four passes as the wave landed: (1) admission dates + full-visit resave onhcfa=1 on pat17470940 x7 (08/05/2026 stay, own 99223 8/18) and pat12231996 x3 (12/16/2025 stay; the first pass missed the anchor because gettxhistory page 1 stops short on a 100-charge chart - history now read with txh.fetch); (2) CCM / timely / duplicate / frequency advisories (35790, 3429, 35777, 7011, 20657, 27261) bypassed with fresh ids on pat17469645 x9, pat17470939, pat17468923, pat12232512, pat17470802, pat17471725; Pattern 11256 bypassed + logged on pat12231909 v19420908 and pat17470875 v19443049; (3) PAID visits whose admission date the repoint wiped - pat17470697 x10 (10/22/2024 stay), pat17470875 v19443049 (05/21/2026), pat17472546 x3 (09/03/2026 stay, M86.9 still first), pat17471725 x2 (05/04/2026) - admission date written back (updextrainsinfo hospitalizationfrom only) and, because the chat repoint had already resaved these same paid visits an hour earlier, full-visit resaved onhcfa=1 with every live charge echoed by id (--allow-paid, this run only; payments untouched, readback live=n/n); updextrainsinfo alone does NOT re-run the inspector - the resave does. "
        "HELD: pat17472874 x11 (99233 4/7-4/19 + 99239 4/21/2026, WEL04, billed 9/20 by the chat rebill, $1,763 of a 15-visit $2,403 stay): no 99223 anywhere within 45 days and no sibling visit carries an admission date; the only Drive facesheet (Aviata PCC record 9/4) shows a 3/4/2026 discharge home - the April HCA admission date is William's (board row tillman-kenneth-17472874). More repoint batches were still landing at the end of the run (v19441315/v19442158 arrived after the 'after' scan and were fixed) - the next slot re-lists. "
        "UNBILLED: 14 'prior payor' rows released (rule b; v19441047 held as before); two NEW HCA charts (Insurance order missing, $842): pat17477818 - Stedi MBI lookup (SSN) = straight Medicare A/B since 9/1/2015, WellCare PDP only, QMB Medicaid COB 3/1/2026 -> FLO02 seq 1 added, AMD 271 ACTIVE (QMB shown); FL Medicaid 77027 answered AAA 42 'unable to respond' x4 so the Medicaid number waits for the next run; pat17477819 - Stedi MBI lookup = Medicare A/B since 5/1/2012 with a Humana PPO (CMS code U, COB 1/1/2026 = Medicare Advantage); Stedi Humana 61101 with the MBI: ACTIVE PPO 'Alcoa' group MA, member H49353396, begin 1/1/2026 -> HUM01 seq 1 added, AMD 271 ACTIVE. Both: dx gate ok (M17.1x), admission 09/18/2026 (own 99223), resave insorder 1 + onhcfa 1, address line 1 moved up from line 2 (phone-in-email field cleared), released. "
        "EXCLUSIONS: run 1700216 rejected 3 Florida Blue secondaries CH FH PREF0283 (no frequency code on the charge -> sent as a resubmission): no prior Florida Blue ICN on any of the three charges, so each went out again frequency 1 on the chart's Florida Blue sequence (v19386697 pat17471795, v19392347 pat23391, v19423631 pat48458 - 204 x3), exclusions completed, run re-lists 0. A second PREF0283 on these = complete per the crossover-wait rule. AET12: HOLD per William 9/21 - not rebilled, not re-verified.")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty)")
add("Claim Inspector", "count", action="37 -> 11 (30 batches; the 11 left are pat17472874's April-2026 stay, held for the admission date)")
add("Claim Inspector", "cleared", patient="pat17470940", dos="8/6-8/18/2026", carrier="", error="Hospitalization From Date empty", action="admission 08/05/2026 (most recent 99223 within 45d; 8/18 own 99223) written, full-visit resave onhcfa=1 x7, inspector clear")
add("Claim Inspector", "cleared", patient="pat12231996", dos="1/3-1/5/2026", error="Hospitalization From Date empty", action="admission 12/16/2025 (99223 within 45d, found once the full tx history was read) written, resave onhcfa=1 x3")
add("Claim Inspector", "cleared", patient="pat17470697", dos="10/23-11/3/2024", error="Hospitalization From Date empty + Pattern 20657", action="PAID visits (Medicare 2024) whose admission date the 9/22 chat repoint wiped: 10/22/2024 written back, resaved with every live charge echoed (--allow-paid), 20657/3429 bypassed x10")
add("Claim Inspector", "cleared", patient="pat17472546", dos="9/3-9/6/2026", error="Hospitalization From Date empty", action="PAID (Medicare) - admission 09/03/2026 written back and resaved x3; M86.9 still first")
add("Claim Inspector", "cleared", patient="pat17470875 / pat17471725", dos="5/24/2026 / 5/7-5/12/2026", error="Hospitalization From Date empty (+11256 / 27261)", action="PAID - admission 05/21/2026 / 05/04/2026 written back, resaved; 11256 bypassed + logged, 27261 AWV advisory bypassed")
add("Claim Inspector", "cleared", patient="pat17469645 x9, pat17470939, pat17468923, pat12232512, pat17470802, pat12231909", error="Patterns 35790 / 3429 / 35777 / 7011 / 20657 / 11256", action="advisories bypassed with fresh ids (no resave needed); 11256 logged to laterality_flag_log.md")
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date, no HCA facesheet for the April stay in Drive (the Aviata PCC record shows a 3/4/2026 discharge home) -> board row tillman-kenneth-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="19 -> 1 (14 prior-payor released, 4 new-chart visits released; v19441047 held as before)")
add("Unbilled", "cleared", patient="pat17477818", dos="9/18-9/19/2026", carrier="FLO02", error="Insurance order is missing", action="Stedi MBI lookup: straight Medicare A/B 9/1/2015, QMB Medicaid COB 3/1/2026, WellCare PDP; FLO02 seq 1 added, AMD 271 ACTIVE; admission 09/18/2026; address line 1 fixed; released. Medicaid number pending (77027 AAA 42 x4)", amount="421.00")
add("Unbilled", "cleared", patient="pat17477819", dos="9/18-9/19/2026", carrier="HUM01", error="Insurance order is missing", action="Stedi MBI lookup: Medicare + Humana MA PPO from 1/1/2026; Stedi Humana 61101 (MBI): ACTIVE PPO Alcoa group MA member H49353396; HUM01 seq 1 added, AMD 271 ACTIVE; admission 09/18/2026; address line 1 fixed; released", amount="421.00")
add("Unbilled", "cleared", patient="14 prior-payor rows (pat17473383 x2, pat17470743, pat17473343, pat17476868 x9, pat17477116, pat17474082)", error="A payment from the prior payor is required", action="released (rule b - primary out and unanswered; they re-queue when the primary posts)")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026)", amount="16.93")
add("Exclusions", "count", action="3 -> 0 rows (run 1700216 9/21 21:09 AMD clock, 55 claims; overview 1/$198 lagging). AET12: HOLD per William 9/21.")
add("Exclusions", "cleared", patient="pat17471795 / pat23391 / pat48458", visit="19386697 / 19392347 / 19423631", carrier="BCBS", error="CH FH PREF0283 MISSING PAYER DOC CONTROL NUM", action="no prior Florida Blue ICN on the charge -> re-sent frequency 1 on the Florida Blue sequence (204 x3), exclusions completed; a second PREF0283 = complete per the crossover-wait rule")
add("ERA", "count", action=ERA_TXT)
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): the three 16:46Z 9/21 readmit records already worked by the 1910Z run - nothing newer. Drive-wide: nothing modified after 03:23Z 9/22. Facesheet folders, Claimocity drop, 835 / Availity / treasury folders quiet. Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row on William's turn, no new William note.")
add("Boards", "read", action="Board inbox: 25 files present (9/20 0345Z - 9/22 0310Z), none in the board's applied map (registry lastCheck 04:47Z 9/22 - the page applied files at 04:46Z but the map still does not record them) - nothing trashed. Denials board registry: only the two 9/12 synctest files - nothing to trash.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none. Helper note: insp_0921_1910.py's history() reads gettxhistory page 1 only and missed a 12/16/2025 99223 on a 100-charge chart - the 0510b/c/d copies read txh.fetch (full history).")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (15 visits $2,403, WEL04, re-billed 9/20) - 11 visits held in the Claim Inspector; post the date (or drop the HCA facesheet) on row tillman-kenneth-17472874")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206); the 69 pre-5/1/2026 claims ($10,872.90) stay held under the no-rebill rule")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="8 coinsurance lines $180.07 held (pat24039, pat20863) - FCC contracting / payer id")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 0510.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, notes=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if notes: o["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    ops.append(o)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 3 -> 0 (Florida Blue PREF0283 secondaries, none AET12); a nightly claim run finally posted again (1700216, 9/21 21:09 AMD clock, 55 claims) - it carried no AET12 claims." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new anywhere in Drive after 03:23Z 9/22); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("bell-jr-ervin", "ok", "%s: the 9/22 chat session's referring-provider repoint resaved his PAID 9/3-9/6/2026 HCA visits (v19453767/58/39) and wiped their admission date, which put them back in the Claim Inspector; 09/03/2026 written back (M86.9 still first) and resaved - inspector clear, nothing needed from you." % SLOT)
app("uhc-rejected-claims-0922", "na", "%s: unchanged - waiting on the rejection reason for the 41 August-2026 UHC claims." % SLOT)
# the three NEW rows (patient names, DOBs, MBIs, member ids) live in secrets/board_rows_<stamp>.json - PHI never enters the repo
ops.extend(json.load(open("secrets/board_rows_%s.json" % S)))
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 05:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, 0 rows on William's turn, no new William note. Sources: Drive-wide nothing modified after 03:23Z 9/22; Claimocity drop: nothing; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records (worked 1910Z).
Claim runs: 1700216 (9/21 21:09 AMD clock, 55 claims, 4 exclusions) - the nightly claim run is back after 1700211 (9/20 02:04).
Columns: %s
ERA step 5: %s
Write-offs: none. Rebilled: 3 Florida Blue secondaries freq-1 ($198 + 2 more visits). Insurance entered: pat17477818 FLO02 (ACTIVE, QMB), pat17477819 HUM01 (ACTIVE, Alcoa group MA).
Script errors: none.
NEEDS WILLIAM: (1) NEW board row tillman-kenneth-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held in the inspector, $1,763 of $2,403); (2) board row uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (3) paste prompt v8; (4) AET12 carrier master (HOLD); (5) centene-m56-denials-0920 ($772.92); (6) FCC contracting (8 lines $180.07 held); (7) pat17477777 rplan18462071 Pre-Auth # (UI); (8) 6 Optum Pay remits; (9) BCBS patient-balance audit parked.
Calls learned: no new call shapes. Learned behaviour: updextrainsinfo alone never re-runs the Claim Inspector - only the full-visit resave does; a referral-plan repoint (updvisitwithcharges without extins) wipes hospitalizationfrom on the visit. Vocabulary unchanged (54).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-22_0510UTC run digest - backend billing run, 1 AM ET 9/22 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918, bell-jr-ervin, uhc-rejected-claims-0922; new rows tillman-kenneth-17472874 (William's turn), dave-javahar-17477818, salter-beverly-17477819) uploaded; nothing trashed (none of the 25 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0 (54 calls). Postman: unchanged.
Mirror: %s

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("digest written")
print("csv rows", len(rows), "| board ops", len(ops))
