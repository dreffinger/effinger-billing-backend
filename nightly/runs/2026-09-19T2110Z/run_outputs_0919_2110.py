# PLAIN ENGLISH (run outputs for the 5pm ET 9/19/2026 slot - ehpa cloud run 2026-09-19T2110Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before|after.json), the ERA before/after snapshots + fallback
#   register and the AET12 verify register, then writes: "_run report 9-19 2110.csv"; board_updates_2026-09-19T2110Z.json
#   (standing-row heartbeats only - no batch landed this slot); a needs_facesheet_list.md section; the chat-history digest
#   (--final, after mirror_result.txt exists).
# AMD writes this run: none (columns 0/0/13/0 unchanged; ERA Post button + fallback + clear re-offered the same held lines).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys, collections
S = "2026-09-19T2110Z"; SRC = "5pm ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "5 PM ET 9/19"
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
fbc = collections.Counter(("residual" if str(r.get("outcome", "")).startswith("residual") else r.get("outcome")) for r in fb)
fb_posted = [r for r in fb if r.get("outcome") == "posted"]
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []) or before.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
unbal = [r for r in ua if (r.get("_errs") or [""])[0].startswith("Payment reason")]
ERA_EXTRA = os.environ.get("ERA_EXTRA", "")
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. Locks release-expired sent. %s"
           "Fallback (dry then live): outcomes %s - %d newly posted lines ($%.2f). 0 addpayments faults unless listed. No new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export; no MA63/M76/M64 work."
           % (nb, ab, na, aa, ERA_EXTRA, dict(fbc), len(fb_posted), sum(f(r.get("pay")) for r in fb_posted)))
INSP_TXT = "0 -> 0 (getclaiminspectorbatches empty before and after - no new HCA batch landed since the 1910Z slot)"
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action=INSP_TXT)
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Insurance order"): act = "new HCA chart (feed 9/16): still zero insplans (getdemographic 21:15Z); cascade exhausted 0510Z (MBI ERR 72 x2, discovery 0); no facesheet in Drive (nothing new in any folder after 19:00Z 9/19), no Pam email, no drop - facesheet row on William's turn"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); nothing new to act on" % (ovb.get("unbillablecount"), ova.get("unbillablecount", ovb.get("unbillablecount")), ovb.get("unbillableamount"), ova.get("unbillableamount", ovb.get("unbillableamount"))))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows on the list (overview shows 1 / $204.00 but getclaimexclusioncharges returns no row on any run - the count lags); no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or 9/19 - eighteenth consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
for r in fb_posted: add("ERA", "manual-posted (fallback)", "pat%s" % r["pid"], r["dos"], "FLO02", "", "pay %.2f + WOINS %.2f (ERA paid %.2f)" % (f(r.get("pay")), f(r.get("wo")), f(r.get("era_paid"))), r["checkid"], "MEDICARE PART B 819814877", r["visitid"], r.get("pay"))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new; no item updated after 05:00Z 9/19; board inbox holds the routine's 0500Z-1910Z files, none in the applied map (v1385), nothing trashed")
add("Sources", "read", action="Drive-wide modifiedTime > 19:00Z 9/19: nothing outside the routine's own files; bht Optum era downloads and treasury payments: nothing modified 9/19; Pam Gmail (newer_than:2d has:attachment): the three admit emails already acted on (9/18 21:59Z, 9/19 02:53Z, 9/19 16:45Z) - nothing newer")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main e1f2126, session branch claude/pensive-einstein-c432pe = main), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 1910Z START >40 min old with its RUN COMPLETE digest - proceeded at 21:09Z. State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main - not unpacked; registers from practices/ehpa/registers (142 files), needs_facesheet_list rebuilt from the nightly/runs sections. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache).")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it) before the next claim run - unchanged since 0510Z")
add("Open on William's turn", "note", patient="pat17477798", action="HCA facesheet / card (new chart 9/16, $421, cascade exhausted) - unchanged since 0510Z")
add("Open on William's turn", "note", patient="7 charts", action="'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919) - unchanged since 0910Z")
add("Open on William's turn", "note", patient="5 charts", action="GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919) - unchanged since 0910Z")
add("Open on William's turn", "note", patient="practice", action="no AMD nightly claim run since 9/16 (Automation Center EOD close stopped): the 20 HCA visits cleared at 1910Z ($3,489), the 24 of 9/18 and every rebill since 9/16 have not transmitted")
with open("_run report 9-19 2110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or 9/19, eighteenth consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there 9/19; Drive-wide nothing after 19:00Z 9/19 outside the routine's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 16:45Z Center Pointe admit already acted on (1710Z).")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("medicare-era-819814877-writeoffs-0919", "human", "%s: still waiting on your 'post' or 'leave' - the 41 Medicare-paid lines on written-off charges ($3,283.39) keep ERA checks 1051714/1051715 on the unposted list; the Post button refused the same lines again this run (they are the ones already posted by hand), nothing double-posted." % SLOT)
app("medicare-hospice-b9-denials-0919", "human", "%s: still waiting on your GV / GW / write-off direction per patient for the 5 CO-B9 hospice denials ($949); nothing rebilled or written off." % SLOT)
app("unbilled-unbalanced-postings-0915", "no", "%s: the %d 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % (SLOT, len(unbal)))
app("harris-dianne-17477798", "no", "%s: chart still has zero insurance plans (getdemographic 21:15Z); no facesheet in Drive (nothing new in any folder after 19:00Z 9/19), no Pam email, no board drop; visits 19455030/19455057 ($421) stay in Unbilled 'Insurance order is missing'." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z-1910Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("board-inbox-registry-0919", "na", "%s: applied map still v1385 (the 05:55Z chat repair); the routine's 0500Z-1910Z files plus this run's 2110Z file sit unapplied in 'board inbox' - nothing trashed; the page's own registry write is still not recording (lastCheck 04:48:56Z)." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
ERRS = "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua)))
SEC = """
## %s columns run (ehpa cloud Code Routine, 21:09-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main e1f2126, session branch claude/pensive-einstein-c432pe = main), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 1910Z START >40 min old with its RUN COMPLETE digest - proceeded at 21:09Z. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). pseudonyms.json 221 names (unchanged).
Boards: Working Denials queue 0; Insurance Refresh Board: drops 0, no item updated after 05:00Z 9/19. Facesheet folders / Claimocity drop / Optum ERA / treasury: nothing new 9/19 outside the routine's own files. Pam Gmail: the three admits already acted on (newest 16:45Z Center Pointe, worked 1710Z) - nothing newer.
Columns: Charge Review 0 -> 0 | Claim Inspector %s | Unbilled %s -> %s ($%s -> $%s): %s | Exclusions 0 -> 0 rows (overview 1/$204.00 lags the list; no claim run newer than 1700202, eighteenth consecutive slot; %d AET12 charges $%.2f open, held). Nothing released, rebilled or written off this slot.
ERA step 5: %s
NEEDS WILLIAM (unchanged): (1) 'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919); (2) GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919); (3) pat17477530's voided 9/2-9/4 visits (row ellery-hollis-17477530); pat17477777 rplan18462071 Pre-Auth #, pat17477798 facesheet; no AMD nightly claim run since 9/16 (Automation Center EOD close stopped - third night: the 20 HCA visits cleared at 1910Z, the 24 of 9/18 and every rebill since 9/16 have not transmitted).
Calls learned: no new call shapes; behaviours in captured_calls_additions_2026-09-19_2110UTC (quiet slot: no new batch, ERA Post button re-refused the held Medicare lines for the seventh slot in a row).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, INSP_TXT, ovb.get("unbillablecount"), ova.get("unbillablecount", ovb.get("unbillablecount")), ovb.get("unbillableamount"), ova.get("unbillableamount", ovb.get("unbillableamount")), ERRS, len(ver), aet_bal, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-19_2110UTC run digest - backend billing run, 5 PM ET 9/19 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: standing-row checks) uploaded; nothing trashed (applied map v1385 lists none of the inbox files). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_2110UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
