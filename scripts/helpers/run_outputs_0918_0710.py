# PLAIN ENGLISH (run outputs for the 3am ET 9/18/2026 slot - ehpa cloud run 2026-09-18T0710Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA
#   before/after snapshots + the ERA chain log and the AET12 verify register, then writes:
#   - "_run report 9-18 0710.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-18T0710Z.json (Insurance Refresh Board inbox file: appends on the standing rows only)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final)
# Never touches: AMD, the board databases. Member ids / MBIs never leave the registers.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-18T0710Z"; SRC = "3am ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "3 AM ET 9/18"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
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
ovb = before.get("overview", {}); ova = after.get("overview", {})
ub = before.get("unbilled", []); ua = after.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")

# ---- run report CSV --------------------------------------------------------------------------------------------
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
NEW = {"17477775", "17477776", "17477779"}
for r in ua:
    err = (r.get("_errs") or [""])[0]
    pid = r.get("patientid") or ""
    if err.startswith("Payment reason"):
        act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"):
        act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row wexford-shelagh-17471007 on his turn since 9/17"
    elif err.startswith("Insurance order"):
        act = "new HCA chart, zero insplans (getdemographic re-read this run); cascade exhausted 9/18 05:xxZ (Stedi MBI ERR 72 / discovery 0, or CHP MA per CMS without a member id); no facesheet, Pam email or drop since - held on William's turn (0510Z board rows)"
    else:
        act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action="%d unposted checks / $%.2f before -> %d / $%.2f after; ERA Center empty: locks release-expired sent, era_post --all-unposted 0 checks, fallback dry+live 0 lines, era_clear 0 dismissed, 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 09:00Z 9/17); no MA63/M76/M64 work" % (nb, ab, na, aa))
add("Boards", "read", action="Working Denials queue 0 queued (no denials file); Insurance Refresh Board: drops 0 new, no item updated after 03:00Z 9/18 (William's last note 02:15Z, the OCR ask, already answered by the 0310Z run); board inbox: neither registry's applied map names a file present in the inbox root - nothing trashed")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC/Claimocity), Optum ERA folder, treasury folder: nothing modified after 09:00Z 9/17 except the routine's own report; Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read (row pam-admits-2026-09-17) - nothing newer")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (0310Z row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance (80 full-charge $0-denial lines $13,930.00 + 99 partial lines $8,569.90). Not worked this run: the contractual split needs each line's remit CO-45, and AMD's masswriteoffsearch allowedamount is NOT that number on manually posted lines (on pat17471832 it equals the amount paid: 53.63 vs remit allowed 107.26 on all 21 corrected lines) - the Availity CheckDetails rows (inbox/availity/checkdetails_rows_2026-09-18T0310Z.csv, not in the repo) have to be re-parsed from the 189 Check PDFs first")
with open("_run report 9-18 0710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# ---- board inbox file -----------------------------------------------------------------------------------------
ops = []
def app(id, ok, result, op="upsert", note=None, set_=None):
    o = {"op": op, "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "3am ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. ERA Center empty: locks release-expired sent; era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s in 'bht Optum era downloads' (nothing to upload); no MA63/M76/M64 work." % (SRC, S, nb, ab, na, aa))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 09:00Z 9/17) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the ten of 18:50Z 9/17 already read.")
for rid, pid, txt in (("conway-shelby-17477775", "17477775", "chart still has zero insurance plans (getdemographic 07:17Z); no facesheet in hca/tmh/PCC/Claimocity folders, Pam Gmail sweep newer_than:2d = the ten 9/17 emails already read, no board drop; 3 visits stay in Unbilled 'Insurance order is missing'"),
                      ("thurlow-nerys-17477776", "17477776", "chart still has zero insurance plans (getdemographic 07:17Z); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; no facesheet, Pam email or drop since; 3 visits stay in Unbilled"),
                      ("gorman-davin-17477779", "17477779", "chart still has zero insurance plans (getdemographic 07:17Z); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; 2 visits stay in Unbilled 'Insurance order is missing'")):
    app(rid, "no", txt)
app("bcbs-patient-balance-audit-0918", "na", "3am ET 9/18: not worked this run. The masswriteoffsearch allowedamount cannot stand in for the remit CO-45 on manually posted lines (pat17471832: 53.63 = the paid amount, remit allowed 107.26, on all 21 corrected lines), so the remaining 99 partial lines ($8,569.90) need the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines ($13,930.00) are denial decisions (PR-39 'same' / wrong payer) - hold Florida Blue patient statements until then.")
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("board ops", len(ops))

# ---- needs_facesheet section, additions file, digest -------------------------------------------------------------
sec = """## %s columns run (ehpa cloud Code Routine, 07:09-%s UTC 9/18, run %s)
Bootstrap: repo ATTACHED (origin/main 15325e0, session branch claude/pensive-einstein-fmn6n0, layout 337 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, not unpacked); registers restored from practices/ehpa/registers/ (0510Z state), needs_facesheet sections rebuilt from nightly/runs/; captured_calls.md = GitHub main docs/captured_calls.md + the 0510Z additions; pseudonyms.json 170 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 0510 START had its RUN COMPLETE digest - proceeded.
Boards: Insurance Refresh Board - drops 0 new; no item updated after 03:00Z 9/18 (William's 02:15Z OCR ask was answered by the 0310Z run); Working Denials queue 0 (no denials file). Board inbox: neither registry's applied map names a file present in the inbox root - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder: nothing modified after 09:00Z 9/17 except the routine's own report CSV. Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read - nothing newer.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled %s -> %s ($%s): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read at 07:17Z; the 0510Z cascade stands - ERR 72 + discovery 0, or CHP MA per CMS without a member id; no new facesheet, Pam email or drop) held on William's turn, nothing re-spent on Stedi | Exclusions 0 -> 0 (no claim run newer than 1700202, %s runs listed; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released, rebilled or written off by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after. ERA Center empty: locks release-expired sent; era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s (nothing to upload); no MA63/M76/M64 work. Availity 5(g): nothing new.
OPEN (Claude's turn, from the 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 (80 full-charge $0-denial lines $13,930.00 + 99 partial lines $8,569.90). Not worked: the masswriteoffsearch allowedamount is NOT the remit allowed on manually posted lines (pat17471832: allowedamount 53.63 = the paid amount, remit allowed 107.26, all 21 corrected lines), so the CO-45 split needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs (inbox/availity/checkdetails_rows_2026-09-18T0310Z.csv is not in the repo); the 80 $0-denial lines are PR-39 / wrong-payer decisions. Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes. Behaviour recorded: masswriteoffsearch (isinsbalance false) allowedamount on a manually posted charge equals the payment posted, not the payer's allowed - never derive a contractual write-off from it. Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ova.get("unbillableamount"), runs_n, aet_bal, nb, ab, na, aa, MIRROR)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + sec)
    os.makedirs("chat_history", exist_ok=True)
    addn = """# captured_calls additions - %s (3am ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- `POST /api/masswriteoff/masswriteoffsearch` with `isinsbalance:false` (patient balances): `allowedamount` on a charge whose payment was posted manually (`addpayments` via manual_post) is the PAYMENT amount, not the payer's allowed - on pat17471832 every one of the 21 lines corrected at 0310Z shows allowedamount 53.63 against a remit allowed of 107.26 (CO-45 52.74 + PR-2 53.63). Never derive a contractual write-off from it; the remit CAS is the only source.
- ERA Center stayed empty through the 0710Z run (GET /api/era/checks = [] before and after); the chain (era_step_b_0913 -> era_post --all-unposted -> era_fallback_0913b dry+live -> era_clear dry+live -> after snapshot) completes in ~6 s on an empty list.
- Cross-container guard: the 0510 START file plus a later digest ending RUN COMPLETE = proceed; the guard read costs one Drive listing.
""" % S
    open("captured_calls_additions_%s-3amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(addn)
    dig = "# %s run digest - backend billing run, 3am ET 9/18/2026 slot (ehpa cloud)\n\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
else:
    print(sec)
