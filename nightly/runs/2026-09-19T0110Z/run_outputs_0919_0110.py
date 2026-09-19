# PLAIN ENGLISH (run outputs for the 9pm ET 9/18/2026 slot - ehpa cloud run 2026-09-19T0110Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA
#   before/after snapshots + era_details cache, the unbilled/AET12 verify registers, then writes:
#   - "_run report 9-19 0110.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-19T0110Z.json (Insurance Refresh Board inbox file: appends on the standing rows, the
#     duplicate Wexford row closed)
#   - denials_updates_2026-09-19T0110Z.json (Working Denials inbox note: the HUM01 $0 denial lines for the next 'rerun')
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final)
# Never touches: AMD, the board databases. Member ids / MBIs never leave the registers. Row ids come from
#   inbox/rowids_0110.json (real ids live outside the mirrored script - PHI gate).
import csv, json, os, datetime, sys
S = "2026-09-19T0110Z"; SRC = "9pm ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "9 PM ET 9/18"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
IDS = json.load(open("inbox/rowids_0110.json"))
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
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []) or before.get("unbilled", []); runs_n = ovb.get("claimrunstatuscount", "?")
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. Two new HUM01 checks arrived since the 7pm run: 1051712 (200469474260918, $97.59, dated 9/17) - "
           "era_post --all-unposted posted its one line $97.59 onto visit 19454383 (99309 9/2/2026; CO45 $41.42 + CO253 $1.99 WOINS), the fallback read it back as already-posted, "
           "the check left the list on its own; 1051713 (NO-PAY-202609170005809, $0, 5 claims) - denial-only: PI252/N4 'attachment required' on visits 19420942 (99487+99489 10/25/2025, $315) "
           "and 19423627 (99487 11/15/2025, $206), OA23 prior-payer-adjudication secondary lines on 19430778 (1/27/2026), 19423677 (11/15/2025), 19433975 (2/26/2026); no MA63/M76/M64; "
           "era_clear dismissed it (0 $0 lines needed processing); the PI252 lines wait for the Working Denials 'rerun'. No new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments'; "
           "locks release-expired sent; 0 addpayments faults." % (nb, ab, na, aa))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart, zero insplans (getdemographic re-read 01:15Z this run); cascade exhausted 9/18 05:xxZ; no facesheet, Pam email or drop since - held on William's turn (0510Z board rows)"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17 or 9/18 - eighth consecutive worked slot); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
add("ERA", "auto-posted", dos="09/02/2026", carrier="HUM01", action="era_post --all-unposted posted the line; fallback read-back 'already-posted'; check left the unposted list", check="1051712", payer="HUM01 200469474260918", visit="19454383", amount="97.59")
add("ERA", "denial-only dismissed", carrier="HUM01", error="PI252/N4 attachment required x2 (visits 19420942, 19423627); OA23 secondary x3 (19430778, 19423677, 19433975)", action="era_clear dismissed the $0 check; lines go to the Working Denials board on the next 'rerun' (denials inbox note); no MA63/M76/M64 so no dx_primary_fix work", check="1051713", payer="HUM01 NO-PAY-202609170005809", amount="0.00")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: rows on Claude's turn read (189), drops 0 new, no William note newer than the 9/18 02:15Z OCR note (closed by the 7pm run); board inbox: neither registry's applied map lists a file still in the inbox - nothing trashed")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC), Claimocity drop, Optum ERA folder, treasury folder, billing agent project files: nothing modified after 20:00Z 9/18 except the routine's own files; Pam Gmail: no admit email newer than the 9/18 21:59Z Aviata admit already acted on")
add("Boards", "closed", "WEXFORD duplicate row", action="row %s is a duplicate of %s created 9/18 01:32Z under a pseudonymized id (a mirrored script's ids leaked onto the board) - closed with a note; the real row stays on William's turn" % (IDS["wexford_dup"], IDS["wexford"]))
add("Routine", "note", action="State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main; registers restored from practices/ehpa/registers + nightly/runs (needs_facesheet_list rebuilt from 36 run folders). Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run; hold Florida Blue patient statements")
with open("_run report 9-19 0110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "9pm ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted on 9/17 or 9/18, eighth consecutive worked slot). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SRC, S, ERA_TXT))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 20:00Z 9/18 outside this routine's own files) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 9/18 21:59Z Aviata admit already acted on.")
for key, txt in (("hca1", "chart still has zero insurance plans (getdemographic 01:15Z 9pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop since the 7pm run; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("hca2", "chart still has zero insurance plans (getdemographic 01:15Z 9pm ET 9/18); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; no facesheet, Pam email or drop since the 7pm run; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("hca3", "chart still has zero insurance plans (getdemographic 01:15Z 9pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop since the 7pm run; 2 visits stay in Unbilled 'Insurance order is missing'")):
    app(IDS[key], "no", txt)
app(IDS["wexford"], "human", "9pm ET 9/18: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance.")
app(IDS["wexford_dup"], "na", "Duplicate of row %s (same chart, same MV line): this row was created 9/18 01:32Z by a run that used a mirrored script's pseudonymized row id. Closed - the real row stays on William's turn." % IDS["wexford"],
    note="Duplicate row closed by the 9pm ET 9/18 run; see the row under the real name for the open MV line.", set_={"status": "done", "need": "CLOSED 9/18 - duplicate of the row under the real name (created from a pseudonymized script id). Nothing to do here."})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
dops = [{"op": "upsert", "collection": "commands", "id": "cmd-claude-%s" % S, "set": {"command": "note", "by": "Claude", "target": "board", "status": "done", "note": "",
         "result": "9pm ET 9/18 run: queue empty. New HUM01 $0 denial check 1051713 (NO-PAY-202609170005809, dated 9/17) dismissed from the ERA Center after its lines were recorded: PI252/N4 'attachment/documentation required' on visits 19420942 (99487+99489 10/25/2025, $315) and 19423627 (99487 11/15/2025, $206); OA23 prior-payer secondary lines on 19430778, 19423677, 19433975 (Medicare-paid CCM visits). The two PI252 claims need the next 'rerun' to land on this board; no MA63/M76/M64."}}]
json.dump({"schema": "wd-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": dops}, open("denials_updates_%s.json" % S, "w"), indent=1)
nfl = """## %s columns run (ehpa cloud Code Routine, 01:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main 89f1d84, session branch claude/pensive-einstein-f7q6eg, layout 368 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC (26 parts) is older than GitHub main - registers restored from practices/ehpa/registers/ (105 files), needs_facesheet sections rebuilt from nightly/runs/ (36 run folders); captured_calls.md = GitHub main docs/captured_calls.md (336 KB; every Drive additions file through 2310UTC is in main); pseudonyms.json 208 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 2310 START (23:14Z) had its RUN COMPLETE digest (23:53Z) - proceeded.
Boards: Insurance Refresh Board - 189 rows on Claude's turn read, drops 0 new, no William note newer than the 9/18 02:15Z OCR note (closed by the 7pm run); Working Denials queue 0. Facesheet folders, Claimocity drop, Optum ERA folder, treasury folder: nothing modified after 20:00Z 9/18 except the routine's own files. Pam Gmail: nothing newer than the 9/18 21:59Z Aviata admit (acted on by the 7pm run). Duplicate board row %s (pseudonymized id from a mirrored script) closed.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 20 -> 20 ($4094.26): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read 01:15Z; the 9/18 0510Z cascade stands; no new facesheet, Pam email or drop) held on William's turn | Exclusions 0 -> 0 (no claim run newer than 1700202, 78 runs listed - NO nightly claim run posted 9/17 or 9/18, eighth consecutive worked slot; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released, rebilled or written off by this run.
ERA step 5: %s Availity 5(g): nothing new.
OPEN (Claude's turn, from the 9/18 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 - not worked. Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes. Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, IDS["wexford_dup"], aet_bal, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(nfl)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + nfl)
    add_md = """# captured_calls additions - %s (backend billing run %s, ehpa cloud)

No new AMD or Stedi call shapes this run. Behaviours worth keeping:
- ERA Center: a Humana money check (1051712) that arrives with a single 99309 line auto-posts cleanly through posterapayments (era_post --all-unposted); the fallback's live read-back then reports the line as already-posted (payment carrying the check number is on the charge) and the check leaves GET /api/era/checks without a dismiss call.
- A Humana NO-PAY check (1051713) carrying only PI252/N4 and OA23 lines is dismissed by era_clear once every line is classed 'denial with write-off (cascade handles)'; its PI252 claims are handed to the Working Denials board through the denials inbox note, never manual-posted.
- Board hygiene: a mirrored (PHI-gated) run script carries pseudonymized row ids; re-using it verbatim from GitHub creates duplicate board rows under the pseudonym (seen 9/18 01:32Z). Row ids must come from a local, non-mirrored file (inbox/rowids_*.json) - done this run.
- getclaimrunstatus still lists 1700202 as the newest claim run at 01:15Z 9/19 (78 runs): eighth consecutive worked slot with no nightly claim run.
""" % (S, SLOT)
    open("captured_calls_additions_2026-09-19_0110UTC-9pmET-ehpa-cloud.md", "w").write(add_md)
    os.makedirs("chat_history", exist_ok=True)
    digest = "# %s run digest - backend billing run, %s slot (ehpa cloud)\n\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, nfl)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(digest)
print("rows", len(rows), "board ops", len(ops), "denials ops", len(dops), "ERA", nb, ab, "->", na, aa, "AET12 bal", aet_bal)
