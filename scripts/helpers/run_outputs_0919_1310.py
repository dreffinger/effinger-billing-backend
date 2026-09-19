# PLAIN ENGLISH (run outputs for the 9am ET 9/19/2026 slot - ehpa cloud run 2026-09-19T1310Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before|after.json), the ERA before/after snapshots, the fallback
#   register of this run and the AET12 verify register, then writes: "_run report 9-19 1310.csv"; board_updates_2026-09-19T1310Z.json
#   (standing-row heartbeats only - no AMD write this run beyond era_clear's dismissal of one $0 denial check); a needs_facesheet_list.md
#   section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys, collections
S = "2026-09-19T1310Z"; SRC = "9am ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "9 AM ET 9/19"
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
fb = load("registers/era_fallback_%s_live.json" % S, [])
fbc = collections.Counter(r.get("outcome") for r in fb)
fb_posted = [r for r in fb if r.get("outcome") == "posted"]
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []) or before.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
unbal = [r for r in ua if (r.get("_errs") or [""])[0].startswith("Payment reason")]
WEL_TXT = ("NEW this slot: a $0 Wellcare (WEL04) remit 1003560017 (check date 9/18, received 05:21Z 9/19) landed as ERA check 1051717 - one claim, pat12231996 v19426729 (99223 + 99497-25, DOS 12/16/2025, insorder WEL04 first / Medicaid second): "
           "CO23 174.99 + OA23 135.01 on the 99223 and CO4 133.00 / RARC N56 on the 99497 = the payer re-adjudicating the 9/6 freq-1 rebill of a claim it had already paid on remit 1008809130 (9/10: 132.31 paid + WOINS 143.94 + WOMCAD 33.75 on the 99223; $0 + WOINS 133.00 on the 99497). "
           "Live read: both charges at $0 insurance and $0 patient balance, the 99497 already carries modifier 25 (mcode7) - already adjudicated, nothing to post, nothing owed, no rebill (a payment is posted). era_clear classified the line 'denial with write-off (cascade handles)' and dismissed the check (zero postable money); registered as denial-only-handled in era_manual_register.json.")
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. Locks release-expired sent. %s "
           "The two held Medicare ERA 819814877 entries (1051714 / 1051715) are unchanged: Post button (era_post --all-unposted) re-offered 29 + 14 lines and AMD refused all 43 again (fault -2147217287, PaymentEntry=29 / PaymentEntry=14 = the lines already posted by hand 0910Z, nothing double-posted). "
           "Fallback (dry then live): register outcomes %s - %d newly posted lines ($%.2f). era_clear: both Medicare checks HELD (the 41 Medicare-paid lines on written-off charges $3,283.39 wait on William's 'post'/'leave', plus the orphan $85.46 on pat17477530's voided 9/2 visit). "
           "0 addpayments faults. No new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export; no MA63/M76/M64 work."
           % (nb, ab, na, aa, WEL_TXT, dict(fbc) or "{}", len(fb_posted), sum(f(r.get("pay")) for r in fb_posted)))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart (feed 9/16): still zero insplans (getdemographic 13:19Z); cascade exhausted 0510Z (MBI ERR 72 x2, discovery 0); no facesheet in Drive (title search 'harris' empty), no Pam email, no drop - facesheet row on William's turn"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); nothing new to act on" % (ovb.get("unbillablecount"), ova.get("unbillablecount", ovb.get("unbillablecount")), ovb.get("unbillableamount"), ova.get("unbillableamount", ovb.get("unbillableamount"))))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows on the list (overview shows 1 / $204.00 but getclaimexclusioncharges returns no row on any run - the count lags); no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or 9/19 - fourteenth consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
add("ERA", "denial-only-handled", "pat12231996", "12/16/2025", "WEL04", "CO23/OA23 on 99223; CO4 N56 on 99497-25", "already adjudicated (Wellcare remit 1008809130 9/10 paid 132.31 + write-offs; balances $0) - nothing to post, no rebill; check dismissed by era_clear", "1051717", "WELLCARE 1003560017", "19426729", "0.00")
for r in fb_posted: add("ERA", "manual-posted (fallback)", "pat%s" % r["pid"], r["dos"], "FLO02", "", "pay %.2f + WOINS %.2f (ERA paid %.2f)" % (f(r.get("pay")), f(r.get("wo")), f(r.get("era_paid"))), r["checkid"], "MEDICARE PART B 819814877", r["visitid"], r.get("pay"))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new; rows on Claude's turn re-read - William's two 04:26-04:27Z notes (board-inbox registry 'im here does that solve it', pat17477775 'i uploaded a va facesheet') were handled by the 0500Z chat / 0510Z run (pat17477775 is off the Unbilled list); board inbox: 5 files (0500Z, 0510Z, 0710Z, 0910Z, 1110Z) not in the applied map (v1385) - nothing trashed")
add("Sources", "read", action="Drive-wide modifiedTime > 11:00Z 9/19: only the 1110Z run's own files; bht hca/tmh/PCC facesheets, Claimocity drop, bht Optum era downloads, treasury payments: nothing new; Pam Gmail (newer_than:2d has:attachment): nothing newer than the 9/19 02:53Z Center Pointe admit (handled 0310Z)")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 7c0801f, session branch claude/pensive-einstein-6zynzu), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 1110Z START >40 min old with its RUN COMPLETE digest - proceeded at 13:17Z. State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main - not unpacked; registers from practices/ehpa/registers (127 files), needs_facesheet_list rebuilt from the nightly/runs sections. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache).")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it) before the next claim run - unchanged since 0510Z")
add("Open on William's turn", "note", patient="pat17477798", action="HCA facesheet / card (new chart 9/16, $421, cascade exhausted) - unchanged since 0510Z")
add("Open on William's turn", "note", patient="7 charts", action="'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919) - unchanged since 0910Z")
add("Open on William's turn", "note", patient="5 charts", action="GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919) - unchanged since 0910Z")
with open("_run report 9-19 1310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or 9/19, fourteenth consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified anywhere in Drive after 11:00Z 9/19 outside the routine's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit already acted on; Claimocity drop and the three facesheet folders: no new file.")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("medicare-era-819814877-writeoffs-0919", "human", "%s: still waiting on your 'post' or 'leave' - the 41 Medicare-paid lines on written-off charges ($3,283.39) keep ERA checks 1051714/1051715 on the unposted list; the Post button refused the same 43 lines again this run (they are the ones already posted by hand), nothing double-posted." % SLOT)
app("medicare-hospice-b9-denials-0919", "human", "%s: still waiting on your GV / GW / write-off direction per patient for the 5 CO-B9 hospice denials ($949); nothing rebilled or written off." % SLOT)
app("wexford-shelagh-17471007", "human", "%s: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance." % SLOT)
app("unbilled-unbalanced-postings-0915", "no", "%s: the %d 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % (SLOT, len(unbal)))
app("harwick-delwen-17477798", "no", "%s: chart still has zero insurance plans (getdemographic 13:19Z); no facesheet in Drive (title search 'harris' empty since 9/15), no Pam email, no board drop; visits 19455030/19455057 ($421) stay in Unbilled 'Insurance order is missing'." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z-1110Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("board-inbox-registry-0919", "na", "%s: applied map still v1385 (the 05:55Z chat repair); five unapplied files in 'board inbox' (0500Z, 0510Z, 0710Z, 0910Z, 1110Z) plus this run's - nothing trashed; the page's own registry write is still not recording (lastCheck 04:48:56Z)." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
ERRS = "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua)))
SEC = """
## %s columns run (ehpa cloud Code Routine, 13:09-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main 7c0801f, session branch claude/pensive-einstein-6zynzu), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 1110Z START >40 min old with its RUN COMPLETE digest - proceeded at 13:17Z. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten).
Boards: Working Denials queue 0; Insurance Refresh Board: drops 0, William's 04:26-04:27Z notes already handled by the 0500Z/0510Z passes. Facesheet folders / Claimocity drop / Optum ERA / treasury / Pam Gmail: nothing new after 11:00Z.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s -> $%s): %s | Exclusions 0 -> 0 rows (overview 1/$204.00 lags the list; no claim run newer than 1700202, fourteenth consecutive slot; %d AET12 charges $%.2f open, held). Nothing rebilled, released or written off.
ERA step 5: %s
NEEDS WILLIAM (unchanged): (1) 'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919); (2) GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919); (3) pat17477530's voided 9/2-9/4 visits (row ellery-hollis-17477530); pat17477777 rplan18462071 Pre-Auth #, pat17477798 facesheet, pat17471007 MV line; no AMD nightly claim run since 9/16 (Automation Center EOD close stopped - third night).
Calls learned: no new call shapes; behaviour in captured_calls_additions_2026-09-19_1310UTC (a $0 secondary re-adjudication remit lands as its own ERA check; era_clear's 'denial with write-off (cascade handles)' class dismisses it once the live visit is at $0 - verify the live charges before trusting the dismissal).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount", ovb.get("unbillablecount")), ovb.get("unbillableamount"), ova.get("unbillableamount", ovb.get("unbillableamount")), ERRS, len(ver), aet_bal, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-19_1310UTC run digest - backend billing run, 9 AM ET 9/19 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (10 standing-row checks, no new rows) uploaded; nothing trashed (applied map v1385 lists none of the inbox files). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_1310UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
