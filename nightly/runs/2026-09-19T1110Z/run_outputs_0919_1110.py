# PLAIN ENGLISH (run outputs for the 7am ET 9/19/2026 slot - ehpa cloud run 2026-09-19T1110Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before|after.json), the ERA before/after snapshots, the fallback
#   register of this run and the AET12 verify register, then writes: "_run report 9-19 1110.csv"; board_updates_2026-09-19T1110Z.json
#   (standing-row heartbeats only - one inspector bypass and no other AMD write this run); a needs_facesheet_list.md section; the
#   chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys, collections
S = "2026-09-19T1110Z"; SRC = "7am ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "7 AM ET 9/19"
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
insp = load("registers/insp_bypass_%s.json" % S, [])
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
unbal = [r for r in ua if (r.get("_errs") or [""])[0].startswith("Payment reason")]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after (the two held Medicare ERA 819814877 entries 1051714/1051715). Locks release-expired sent. "
           "Post button (era_post --all-unposted): 43 lines re-offered, AMD refused all 43 again (fault -2147217287, PaymentEntry=43) - these are the lines the 0910Z run already posted by hand, so nothing was double-posted. "
           "Fallback (dry then live): register outcomes %s - %d newly posted lines ($%.2f). era_clear: both checks HELD (the 41 Medicare-paid lines on written-off charges $3,283.39 wait on William's 'post'/'leave', plus the orphan $85.46 on pat17477530's voided 9/2 visit). "
           "0 addpayments faults. No new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export; no MA63/M76/M64 work."
           % (nb, ab, na, aa, dict(fbc) or "{}", len(fb_posted), sum(f(r.get("pay")) for r in fb_posted)))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="1 -> 0: pat17472124 v19442479 (FLO02, CCM 99487+99489 05/17/2026, Medicare-paid 9/19, re-inspected after the 0910Z move-back) raised Pattern 3429 / 7011 / 33799 CCM-frequency advisories - all three bypassed with the fresh ids (batch 126912), getclaiminspectorbatches empty after")
for r in insp: add("Claim Inspector", "cleared", "pat%s" % r["pid"], "05/17/2026", "FLO02", "; ".join(e[2][:60] for e in r["errs"]), "bypassclaimedits advisories (CCM frequency) - ok=%s" % r["ok"], visit=r["vid"])
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart (feed 9/16): no plan; cascade exhausted 0510Z (MBI ERR 72 x2, discovery 0); facesheet row on William's turn - no new input since"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); nothing new to act on" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows on the list (overview shows 1 / $204.00 but getclaimexclusioncharges returns no row on any run - the count lags); no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or 9/19 - thirteenth consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
for r in fb_posted: add("ERA", "manual-posted (fallback)", "pat%s" % r["pid"], r["dos"], "FLO02", "", "pay %.2f + WOINS %.2f (ERA paid %.2f)" % (f(r.get("pay")), f(r.get("wo")), f(r.get("era_paid"))), r["checkid"], "MEDICARE PART B 819814877", r["visitid"], r.get("pay"))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new, no William note newer than the 04:26-04:27Z pair already handled (0500Z chat / 0510Z run); board inbox: 4 files (0500Z, 0510Z, 0710Z, 0910Z) not in the applied map (v1385) - nothing trashed")
add("Sources", "read", action="bht hca/tmh/PCC facesheets, Claimocity drop, bht Optum era downloads, treasury payments, chc raw 835: nothing modified after 09:00Z 9/19 except the 0910Z run's own files; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit (handled 0310Z)")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 5a1e0a7, session branch claude/pensive-einstein-s69fws), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0910Z START >40 min old with its RUN COMPLETE digest - proceeded at 11:09Z. State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main - not unpacked; registers from practices/ehpa/registers (123 files), needs_facesheet section from nightly/runs. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache).")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it) before the next claim run - unchanged since 0510Z")
add("Open on William's turn", "note", patient="pat17477798", action="HCA facesheet / card (new chart 9/16, $421, cascade exhausted) - unchanged since 0510Z")
add("Open on William's turn", "note", patient="7 charts", action="'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row [name]-819814877-writeoffs-0919) - unchanged since 0910Z")
add("Open on William's turn", "note", patient="5 charts", action="GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919) - unchanged since 0910Z")
with open("_run report 9-19 1110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or 9/19, thirteenth consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 09:00Z 9/19 outside the routine's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit already acted on; Claimocity drop and the three facesheet folders: no new file.")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("[name]-819814877-writeoffs-0919", "human", "%s: still waiting on your 'post' or 'leave' - the 41 Medicare-paid lines on written-off charges ($3,283.39) keep ERA checks 1051714/1051715 on the unposted list; the Post button refused the same 43 lines again this run (they are the ones already posted by hand), nothing double-posted." % SLOT)
app("medicare-hospice-b9-denials-0919", "human", "%s: still waiting on your GV / GW / write-off direction per patient for the 5 CO-B9 hospice denials ($949); nothing rebilled or written off." % SLOT)
app("[name]-17471007", "human", "%s: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance." % SLOT)
app("unbilled-unbalanced-postings-0915", "no", "%s: the %d 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % (SLOT, len(unbal)))
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z-0910Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("board-inbox-registry-0919", "na", "%s: applied map still v1385 (the 05:55Z chat repair); four unapplied files in 'board inbox' (0500Z, 0510Z, 0710Z, 0910Z) plus this run's - nothing trashed; the page's own registry write is still not recording (lastCheck 04:48:56Z)." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
ERRS = "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua)))
SEC = """
## %s columns run (ehpa cloud Code Routine, 11:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main 5a1e0a7, session branch claude/pensive-einstein-s69fws), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0910Z START >40 min old with its RUN COMPLETE digest - proceeded at 11:09Z. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten).
Boards: Working Denials queue 0; Insurance Refresh Board: drops 0, no William note newer than the 04:26-04:27Z pair already handled. Facesheet folders / Claimocity drop / Optum ERA / treasury / Pam Gmail: nothing new after 09:00Z.
Columns: Charge Review 0 -> 0 | Claim Inspector 1 -> 0 (pat17472124 v19442479 CCM 05/17/2026, Medicare-paid, re-inspected after the 0910Z move-back: Pattern 3429/7011/33799 advisories bypassed with the fresh ids) | Unbilled %s -> %s ($%s -> $%s): %s | Exclusions 0 -> 0 rows (overview 1/$204.00 lags the list; no claim run newer than 1700202, thirteenth consecutive slot; %d AET12 charges $%.2f open, held). Nothing rebilled, released or written off.
ERA step 5: %s
NEEDS WILLIAM (unchanged): (1) 'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row [name]-819814877-writeoffs-0919); (2) GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919); (3) pat17477530's voided 9/2-9/4 visits (row ellery-hollis-17477530); pat17477777 rplan18462071 Pre-Auth #, pat17477798 facesheet, pat17471007 MV line; no AMD nightly claim run since 9/16 (Automation Center EOD close stopped - third night).
Calls learned: no new call shapes; behaviour in captured_calls_additions_2026-09-19_1110UTC (Post button re-offered on a held check refuses the already-manual-posted lines, PaymentEntry = the full count, so re-running era_post on a held check is safe - no double post).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), ERRS, len(ver), aet_bal, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-19_1110UTC run digest - backend billing run, 7 AM ET 9/19 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (9 standing-row checks, no new rows) uploaded; nothing trashed (applied map v1385 lists none of the inbox files). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_1110UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
