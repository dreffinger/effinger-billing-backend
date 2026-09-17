# PLAIN ENGLISH (run outputs for the 1am ET 9/17/2026 slot - ehpa cloud run 2026-09-17T0510Z)
# Decides: nothing. Reads this run's column scan (scan_0912/summary_before.json), the ERA before/after snapshots, the
#   era_chain log, the dismissed-checks probe and the AET12 open-balance search, then writes:
#   - "_run report 9-17 0510.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T0510Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; no set on
#     status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Special to this run: every column and the ERA list were already empty when the
#   run read them - William cleared them in the UI between 03:35Z and 05:25Z (34 ERA checks dismissed 21:52-22:06 AMD clock).
import csv, json, os, re, collections, datetime, sys
S = "2026-09-17T0510Z"; SRC = "1am ET 9/17 columns run (ehpa cloud)"; W = "9/17"; LOGF = "era_chain_0917_0510.log"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
prev_n, prev_amt = 34, 9581.36   # the 0310Z run's after-snapshot (03:35Z)
dismissed = [893547, 893590, 893741, 893905, 893960, 893970, 894006, 894007, 894057, 894153, 894671, 895325, 895428, 895469,
             1046255, 1046898, 1047829, 1048512, 1049142, 1049277, 1049308, 1049504, 1050727, 1050820, 1050822, 1050836, 1050849,
             1051025, 1051243, 1051390, 1051584, 1051661, 1051666, 1051680]
aet = load("registers/aet12_masswo_%s.json" % S, {}).get("chargedetails", [])
prev = load("registers/aet12_verify_2026-09-17T0310Z.json", []); pv = {c["visit"] for c in prev}
aet_open = [c for c in aet if str(c.get("visitid")) in pv]
aet_bal = round(sum(f(c.get("insbalance")) for c in aet_open), 2)
aet_all = round(sum(f(c.get("insbalance")) for c in aet), 2)
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
n_cr = len(before.get("chargereview", [])); insp = before.get("inspector", {}); n_in = sum(len(v) for v in insp.values()) if isinstance(insp, dict) else len(insp)
n_ub = len(before.get("unbilled", [])); n_ex = sum(len(v) for v in before.get("exclusions", {}).values())
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty)")
add("Claim Inspector", "clear", action="0 batches / 0 visits before and after (getclaiminspectorbatches empty)")
add("Unbilled", "clear", action="12 -> 0 outside the routine: the 11 'Payment reason codes are missing or do not balance' rows ($2,422.58) and the WEXFORD 'Bill Insurance = No' row were released from the Unbilled column between 03:35Z and 05:25Z 9/17 (William, UI); getclaimunbillablecharges totalcount 0. Nothing released by this run.")
add("Unbilled", "note", patient="WEXFORD,SHELAGH", dos="02/02/2024", carrier="CHP", err="Bill Insurance = No at charge level and charge has insurance balance", action="row left Unbilled but the 'MV' $75.68 line (charge 23365777, no carrier, Bill Insurance blank) is still on the visit with a $75.68 insurance balance - board row [name]-17471007 stays on William's turn", visit="19375395", amt="75.68")
add("Exclusions", "clear", carrier="AET12", err="PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (claim run 1700201)", action="59 -> 0 outside the routine: getclaimexclusioncharges for run 1700201 returns an empty visit list (completed in the UI between 03:35Z and 05:25Z); the 68 AET12 charges of those 59 claims still carry $%.2f open insurance balance (masswriteoffsearch car42009: %d AET12 charges $%.2f open in all), no AET12 payment; no new claim run since 1700201 (9/16 18:45 AMD clock; %s runs listed). Nothing rebilled by this run - the carrier-record fix is still William's." % (aet_bal, len(aet), aet_all, runs_n))
add("ERA", "cleared outside the routine", err="34 checks dismissed in ERA Center 21:52-22:06 9/16 AMD clock (04:52-05:06Z 9/17)", action="GET /api/era/checks = [] at 05:27Z; GET /api/era/checks/dismiss?DismissedDateBegin=2026-09-16 lists the 34 checks that were on the 03:35Z unposted list ($9,581.36) with dismissedat 21:52-22:06 - William dismissed them himself; the routine posted nothing and dismissed nothing. Their remaining lines (the 0310Z fallback register: 118 reversal lines $11,196.56, 27 orphan lines $1,808.67, 72 residual-zero lines $4,915.12, 21 register-skip) are no longer on the unposted list.", amt="%.2f" % prev_amt)
for cid in dismissed:
    add("ERA", "dismissed by William", check=str(cid), action="dismissed in ERA Center 9/16 21:52-22:06 AMD clock (not by the routine)")
add("ERA", "run result", action="era_step_b before: 0 checks / $0.00; era_post --all-unposted posted 0 visits $0.00; fallback dry+live 0 lines; era_clear 0 dismissed; after: 0 / $0.00; 0 addpayments faults; no new 835s in 'bht Optum era downloads'; locks release-expired sent")
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' modified after 9/16 00:00Z; every PDF is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled - nothing parsed or posted")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board drops 0 new, 0 rows on William's turn, 0 rows updated after 03:00Z 9/17 (184 on Claude's turn, all watch/hold); facesheet folders (hca/tmh/PCC/Claimocity/parent), Optum ERA folder, treasury folder: nothing new; Pam Gmail (newer_than:2d) empty. New in 'billing agent project files' since the 0310Z run: UHC_API_and_835_setup.md, captured_calls_additions_2026-09-17_0400UTC-chat-uhc-835.md (merged into the registry this run) and the folder 'chc raw 835 downloads' (empty).")
out = "_run report 9-17 0510.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
ops = []
def row(id, checks=None, notes=None, op="update", set_=None):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if set_: o["set"] = set_
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    ops.append(o)
row("aet12-carrier-cpid", checks=[chk("na", "The 59 AET12 PREF0288+PREF0264 exclusion rows on claim run 1700201 are GONE from the exclusion list (getclaimexclusioncharges returns an empty visit list at 05:26Z) - completed outside the routine between 03:35Z and 05:25Z 9/17 (your UI session, same window as the ERA Center dismissals). The 68 AET12 charges still carry $%.2f open insurance balance (no AET12 payment, none at $0); no new claim run since 1700201 (%s runs listed). Nothing rebilled by this run: the claims leave again only on 'rebill' after the carrier record (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case) is changed." % (aet_bal, runs_n), SRC + " - claim run 1700201")])
row("era-manual-post-0912", checks=[chk("na", "ERA step 5 (%s, run %s): the unposted list went 34 checks / $9,581.36 (03:35Z) -> 0 / $0.00 (05:27Z) before the run touched it: GET /api/era/checks/dismiss?DismissedDateBegin=2026-09-16 shows all 34 dismissed in ERA Center 21:52-22:06 AMD clock (04:52-05:06Z) - by you, not the routine. era_post/fallback/era_clear ran against an empty list (0 posted, 0 dismissed, 0 faults); no new 835s; locks released. The lines those checks still carried (118 reversal $11,196.56, 27 orphan $1,808.67, 72 residual-zero $4,915.12 per the 0310Z fallback register) are off the unposted list with them." % (SRC, S), SRC + " - ERA step 5")])
row("unbilled-unbalanced-postings-0915", checks=[chk("na", "The 11 'Payment reason codes are missing or do not balance' rows ($2,422.58) left the Unbilled column between 03:35Z and 05:25Z 9/17 (released outside the routine - your UI session); getclaimunbillablecharges totalcount 0. Nothing released by this run.")])
row("[name]-17471007", op="upsert", set_={"patient": "WEXFORD,SHELAGH", "amdid": "17471007"},
    checks=[chk("human", "Visit 19375395 left the Unbilled column (released outside the routine, 03:35Z-05:25Z 9/17) but gettxhistory at 05:35Z still shows charge 23365777 proccode 'MV' 02/02/2024 with a $75.68 INSURANCE balance, no carrier, $0 paid, not voided - the line itself is unchanged. Still yours: delete it, set Bill Insurance with the carrier, or move the $75.68 to the patient balance.")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/16 00:00Z; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

sec = """
## 2026-09-17 1 AM ET columns run (ehpa cloud Code Routine, 05:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 2e437ea, layout 289 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (manifest + 6 parts fetched; older than the repo state, so not unpacked); registers restored from practices/ehpa/registers/ in the repo (0310Z state); needs_facesheet_list.md = the Drive 0630UTC copy + the repo's 15 run sections; captured_calls.md = GitHub main docs/captured_calls.md + the Drive additions files (new: captured_calls_additions_2026-09-17_0400UTC-chat-uhc-835.md from William's 04:00Z chat - UHC API + 835 setup, pending, no proven call); pseudonyms.json (142 names), x12_835.py and uhc_api.py pulled from the workspace mirror; precheck_cache from Drive (9/16 06:25Z). Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 184 rows on Claude's turn (all watch/hold), 0 on William's turn, 0 rows updated after 03:00Z 9/17; drops new = 0; Working Denials queue = 0. Board inbox: the registry's applied map lists only 9/12-9/14 files, none still in the inbox - nothing trashed (28 unapplied board_updates files wait for William to open the board). Facesheet folders (hca/tmh/PCC/Claimocity/parent), Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new.
EVERYTHING WAS ALREADY CLEAR when the run read AMD at 05:25Z - William worked the Claims Center and ERA Center himself between the 0310Z run's after-scan (03:35Z) and this run: GET /api/era/checks/dismiss?DismissedDateBegin=2026-09-16 lists all 34 checks of the 03:35Z unposted list dismissed 21:52-22:06 AMD clock (04:52-05:06Z 9/17); getclaimexclusioncharges for run 1700201 returns an empty visit list; getclaimunbillablecharges totalcount 0.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled 12 -> 0 (released outside the routine: the 11 'Payment reason codes are missing or do not balance' rows $2,422.58 and WEXFORD visit 19375395 - whose 'MV' $75.68 line is still on the visit unchanged, board row [name]-17471007 stays on William's turn) | Exclusions 59 -> 0 (the 59 AET12 PREF0288+PREF0264 rows on run 1700201 completed outside the routine; masswriteoffsearch car42009: the 68 AET12 charges of those claims still carry $%.2f open, %d AET12 charges $%.2f open in all, no AET12 payment; no new claim run since 1700201 - %s runs listed). Nothing released, rebilled or written off by this run.
ERA step 5: 34 checks / $9,581.36 (03:35Z) -> 0 / $0.00 before the run (dismissed by William as above) -> 0 / $0.00 after. era_post posted 0 visits $0.00; fallback dry + live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s in the Optum folder; locks release-expired sent; era_details cache empty (nothing to cache). Lines those 34 checks still carried per the 0310Z fallback register: 118 reversal $11,196.56, 27 orphan $1,808.67, 72 residual-zero $4,915.12 - off the unposted list with the dismissals. Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none (every call this run is a captured shape: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusionclaimruns, getclaimexclusioncharges, gettxhistory, GET /api/era/checks, GET /api/era/checks/dismiss, POST /api/era/locks/release-expired, POST /api/masswriteoff/masswriteoffsearch). Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, aet_bal, len(aet), aet_all, runs_n, MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 1 AM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("captured_calls_additions_%s-1amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 1 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 1am ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
