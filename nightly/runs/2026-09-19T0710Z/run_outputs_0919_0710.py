# PLAIN ENGLISH (run outputs for the 3am ET 9/19/2026 slot - ehpa cloud run 2026-09-19T0710Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before|after.json), the ERA before/after snapshots and the
#   AET12 verify register, then writes: "_run report 9-19 0710.csv"; board_updates_2026-09-19T0710Z.json (standing-row heartbeats
#   only - nothing changed in AMD this run); a needs_facesheet_list.md section; the captured_calls additions file; the chat-history
#   digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Row ids come from inbox/rowids_0710.json (workspace only - PHI gate).
import csv, json, os, datetime, sys
S = "2026-09-19T0710Z"; SRC = "3am ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "3 AM ET 9/19"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
IDS = json.load(open("inbox/rowids_0710.json"))
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ver = load("registers/aet12_verify_%s.json" % S, []); aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
ovb = before.get("overview", {}); ova = after.get("overview", {}); ub = before.get("unbilled", []); ua = after.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
unbal = [r for r in ua if (r.get("_errs") or [""])[0].startswith("Payment reason")]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. ERA Center empty the whole run: locks release-expired sent; era_post --all-unposted 0 checks; "
           "fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments' "
           "(nothing modified there after 05:00Z 9/19); no MA63/M76/M64 work." % (nb, ab, na, aa))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart (feed 9/16): no plan; cascade exhausted 0510Z (MBI ERR 72 x2, discovery 0); facesheet row on William's turn - no new input since"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); the 0510Z release of v19455048 (MSP fix) has now left the snapshot; nothing new to act on" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or so far 9/19 - eleventh consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: no item updated since 05:25Z, drops 0 new, no William note since the 0510Z run; board inbox: applied map (v1385, chat 05:55Z re-registered 66 files and trashed them) lists neither of the two files still in the inbox (0500Z, 0510Z) - nothing trashed")
add("Sources", "read", action="bht hca/tmh/PCC facesheets, Claimocity drop, bht Optum era downloads, treasury payments, billing agent project files: nothing modified after 05:00Z 9/19 except this project's own 0510Z/0500Z outputs; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit (handled 0310Z)")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main abc0f05), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0510Z START 40+ min old with RUN COMPLETE digests for 0500Z and 0510Z - proceeded. State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main (27 parts downloaded, not unpacked); registers restored from practices/ehpa/registers (116 files), needs_facesheet_list rebuilt from nightly/runs sections (323 lines). Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it) before the next claim run - unchanged since 0510Z")
add("Open on William's turn", "note", patient="pat17477798", action="HCA facesheet / card (new chart 9/16, $421, cascade exhausted) - unchanged since 0510Z")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run; hold Florida Blue patient statements")
with open("_run report 9-19 0710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app(IDS["aet12"], "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or so far 9/19, eleventh consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app(IDS["bcbs"], "na", "%s: not worked this run (same blocker as 0710Z 9/18 - 0510Z 9/19: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements." % SLOT)
app(IDS["availity"], "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 05:00Z 9/19) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit already acted on; Claimocity drop and the three facesheet folders: no new file.")
app(IDS["era"], "na", "ERA step 5 (%s columns run (ehpa cloud), run %s): %s" % (SLOT.lower().replace(" et", " ET"), S, ERA_TXT))
app(IDS["wexford"], "human", "%s: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance." % SLOT)
app(IDS["unbal"], "no", "%s: the %d 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % (SLOT, len(unbal)))
app(IDS["registry"], "ok", "%s: your 05:55Z chat session re-registered 66 inbox files (9/13 - 9/19 0310Z) as applied in meta/drive_sync (now version 1385) and trashed them from 'board inbox'; only board_updates_2026-09-19T0500Z.json and _0510Z.json remain there for the page to apply on your next open (this run's file joins them). The page's own registry write is still not recording (lastCheck 04:48:56Z) - the duplicate-row re-apply loop should stop now that the old files are gone; this run trashed nothing (neither remaining file is in the applied map)." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
ERRS = "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua)))
open("needs_facesheet_list_section_%s.md" % S, "w").write("""
## %s columns run (ehpa cloud Code Routine, 07:09-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main abc0f05), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0510Z START >40 min old with RUN COMPLETE digests for 0500Z and 0510Z - proceeded. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten).
Boards: Working Denials queue 0; Insurance Refresh Board: no item updated since 05:25Z, drops 0, no William note since the 0510Z run. Facesheet folders / Claimocity drop / Optum ERA / treasury / Pam Gmail: nothing new.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s -> $%s): %s | Exclusions 0 -> 0 (no claim run newer than 1700202, eleventh consecutive slot; %d AET12 charges $%.2f open, held). Nothing rebilled, released or written off.
NEEDS WILLIAM (unchanged since 0510Z): pat17477777 main referral plan rplan18462071 still carries pat17477775's VA auth -> clear in the UI before the next claim run. pat17477798 (new HCA chart 9/16, $421): facesheet / card needed (row on his turn). Wexford pat17471007 MV $75.68 line. No AMD nightly claim run since 9/16.
ERA step 5: %s
Calls learned: no new call shapes; no new behaviours.
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), ERRS, len(ver), aet_bal, ERA_TXT))
open("captured_calls_additions_2026-09-19_0710UTC-3amET-ehpa-cloud.md", "w").write("""# captured_calls additions - 2026-09-19 0710 UTC (3am ET 9/19 backend billing run, ehpa cloud)

No new AMD call shapes and no new behaviours. Read-only observations (chart ids only):
- getclaimrunstatus at 07:2xZ 9/19 still lists 1700202 (2026-09-16 22:16) as the newest claim run (78 runs): eleventh consecutive worked slot with no nightly claim run.
- getclaimunbillablecharges snapshot: 14 rows / $3,030.26 (the 0510Z hideunbillablevisits release of v19455048 has left the snapshot; the 11 'Payment reason codes' rows, pat17471007's MV line and pat17477798's two 'Insurance order is missing' rows remain).
- ERA Center empty (0 checks) at 07:25Z 9/19 - era_post / fallback / era_clear all no-ops.
""")
if "--final" in sys.argv:
    dig = """# 2026-09-19_0710UTC run digest - backend billing run, 3 AM ET 9/19 slot (ehpa cloud)

## %s columns run (ehpa cloud Code Routine, 07:09-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main abc0f05, session branch claude/pensive-einstein-gbw9i3), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC (27 parts) is older than GitHub main - downloaded, not unpacked; registers restored from practices/ehpa/registers/ (116 files), needs_facesheet sections rebuilt from nightly/runs/ (323 lines); captured_calls.md = GitHub main docs/captured_calls.md; pseudonyms.json 217 names; precheck.py + precheck_cache from the 9/19 chat fixes. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 0510Z START marker >40 min old and RUN COMPLETE digests present for the 0500Z chat session and the 0510Z run - proceeded at 07:20Z.
Boards: Working Denials queue 0. Insurance Refresh Board: no item updated since 05:25Z, drops 0 new, no William note since the 0510Z run. Facesheet folders / Claimocity drop / Optum ERA / treasury: nothing modified after 05:00Z except the 0500Z/0510Z run outputs. Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s -> $%s): 11 'Payment reason codes' rows held (9/15 rule), pat17471007 MV line William's, pat17477798 x2 (new HCA chart, cascade exhausted 0510Z) on William's turn; the 0510Z MSP release has left the snapshot | Exclusions 0 -> 0 (no claim run newer than 1700202, 78 runs, eleventh consecutive worked slot with no nightly claim run; %d AET12 charges $%.2f open, held, not re-sent). Nothing rebilled, released or written off. No AMD writes this run.
NEEDS WILLIAM (unchanged since 0510Z): (1) clear the Pre-Auth # on pat17477777's main referral plan rplan18462071 in the UI before the next claim run; (2) HCA facesheet / card for pat17477798; (3) the Wexford MV line; (4) no AMD nightly claim run since 9/16 - three days of charges (Conway, Thurlow, Gorman, Lisle, Lazenby and every other 9/17-9/19 visit) are waiting for one.
ERA step 5: %s Availity 5(g): nothing new.
Board inbox: applied map v1385 (chat 05:55Z re-registered 66 files and trashed them); the two files still in the inbox (0500Z, 0510Z) are not in the map - nothing trashed; board_updates_%s.json (7 standing-row checks, no status changes) uploaded. Denials file skipped (queue 0).
Calls learned: none. Vocabulary entries added: 0.
Mirror: %s

RUN COMPLETE
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), len(ver), aet_bal, ERA_TXT, S, MIRROR)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_0710UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(open("needs_facesheet_list_section_%s.md" % S).read())
print("wrote report csv, board file (%d ops), needs_facesheet section, additions%s" % (len(ops), ", digest" if "--final" in sys.argv else ""))
