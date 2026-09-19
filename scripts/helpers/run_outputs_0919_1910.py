# PLAIN ENGLISH (run outputs for the 3pm ET 9/19/2026 slot - ehpa cloud run 2026-09-19T1910Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before|after.json), the inspector register, the Whitlock recode
#   register, the ERA before/after snapshots + fallback register and the AET12 verify register, then writes: "_run report 9-19 1910.csv";
#   board_updates_2026-09-19T1910Z.json (standing-row heartbeats + the rows touched by the inspector batch); a needs_facesheet_list.md
#   section; the chat-history digest (--final, after mirror_result.txt exists).
# AMD writes this run (done before this script, recorded here): 20 HCA visits admission date + resave; 2 add-I10 + freq-1 rebills;
#   1 M86.9-first recode; 1 procedure swap 99344 -> 99349 + freq-1. Never touches: AMD, the board databases.
import csv, json, os, datetime, sys, collections
S = "2026-09-19T1910Z"; SRC = "3pm ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "3 PM ET 9/19"
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
ins = load("registers/insp_%s.json" % S, {"visits": [], "held": [], "left": []}); walsh = load("registers/whitlock_recode_%s.json" % S, {})
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []) or before.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
insp_before = sum(len(v) for v in before.get("inspector", {}).values()); insp_after = sum(len(v) for v in after.get("inspector", {}).values())
unbal = [r for r in ua if (r.get("_errs") or [""])[0].startswith("Payment reason")]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. Locks release-expired sent. No new ERA check landed since the 1710Z slot. "
           "The two held Medicare ERA 819814877 entries (1051714 / 1051715) are unchanged: Post button (era_post --all-unposted) re-offered 29 + 14 lines and AMD refused all 43 again (fault -2147217287, PaymentEntry=29 / PaymentEntry=14 = the lines already posted by hand 0910Z, nothing double-posted; sixth slot in a row). "
           "Fallback (dry then live): register-skip / residual-zero %d ($3,283.39) / orphan 1 ($85.46) - %d newly posted lines ($%.2f). era_clear: both Medicare checks HELD (the 41 Medicare-paid lines on written-off charges $3,283.39 wait on William's 'post'/'leave', plus the orphan $85.46 on pat17477530's voided 9/2 visit). "
           "0 addpayments faults. No new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export; no MA63/M76/M64 work."
           % (nb, ab, na, aa, fbc.get("residual", 0), len(fb_posted), sum(f(r.get("pay")) for r in fb_posted)))
INSP_TXT = ("%d -> %d: one new HCA batch 127741 (21 visits on 19 charts, $3,489.00) landed between the 1710Z and 1910Z slots, 20 held 'Hospitalization From Date empty' + 1 Pattern 4310. "
            "20 admission dates written by rule (own 99223 / most recent 99223 within 45 days / the same stay's date already on an earlier visit), full-visit resave onhcfa=1; primary-dx gate: pat17477774 v19455119 (Z96.641 only) and pat17470950 v19455122 (Z96.651 only) got I10 in front via dx_primary_fix add-i10 + freq-1 (204 x2), pat17472546 v19455131 S81.801S got M86.9 in front (William 9/6 rule); "
            "the UMR 'Source of Payment not typical' advisory on v19455119 bypassed with its fresh id; pat17474446 v19455133 99344 (new-patient home visit) held by Pattern 4310 (same practice saw the patient 12/20/2025) -> recoded 99349 (pcode65142) per the standing established-patient rule, fee kept $300, freq-1 204; batch list empty after." % (insp_before, insp_after))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action=INSP_TXT)
for v in ins.get("visits", []):
    adm = [s for s in v["steps"] if s.startswith("admission")]; extra = [s for s in v["steps"] if "PRIMARY-DX" in s or "Winslow" in s or "mcode7" in s]
    add("Claim Inspector", "cleared", v["name"], "", "", "Hospitalization From Date empty", (adm[0] if adm else "") + (" | " + "; ".join(x[:120] for x in extra) if extra else ""), visit=v["vid"])
if walsh.get("swap"):
    add("Claim Inspector", "cleared", "WHITLOCK,JOANNA", "09/17/2026", "FLO02", "Pattern 4310 established patient", "99344 -> 99349 (pcode65142) recode.swap_proc, fee kept $300.00, freq-1 rebill 204; inspector clear on the resave", visit="19455133", amount="300.00")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Insurance order"): act = "new HCA chart (feed 9/16): still zero insplans (getdemographic 19:22Z); cascade exhausted 0510Z (MBI ERR 72 x2, discovery 0); no facesheet in Drive (title search 'harris' = a different patient's 8/29 sheet), no Pam email, no drop - facesheet row on William's turn"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); nothing new to act on" % (ovb.get("unbillablecount"), ova.get("unbillablecount", ovb.get("unbillablecount")), ovb.get("unbillableamount"), ova.get("unbillableamount", ovb.get("unbillableamount"))))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows on the list (overview shows 1 / $204.00 but getclaimexclusioncharges returns no row on any run - the count lags); no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or 9/19 - seventeenth consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
for r in fb_posted: add("ERA", "manual-posted (fallback)", "pat%s" % r["pid"], r["dos"], "FLO02", "", "pay %.2f + WOINS %.2f (ERA paid %.2f)" % (f(r.get("pay")), f(r.get("wo")), f(r.get("era_paid"))), r["checkid"], "MEDICARE PART B 819814877", r["visitid"], r.get("pay"))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new; no item updated after 05:00Z 9/19; board inbox holds the routine's 0500Z-1710Z files, none in the applied map (v1385), nothing trashed")
add("Sources", "read", action="Drive-wide modifiedTime > 17:00Z 9/19: nothing outside the routine's own files; bht Optum era downloads and treasury payments: nothing modified 9/19; Pam Gmail (newer_than:2d has:attachment): the three admit emails already acted on (9/18 21:59Z, 9/19 02:53Z, 9/19 16:45Z) - nothing newer")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main d96e9e3, session branch claude/pensive-einstein-qoonww), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 1710Z START >40 min old with its RUN COMPLETE digest - proceeded at 19:10Z. State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main - not unpacked; registers from practices/ehpa/registers (136 files), needs_facesheet_list rebuilt from the nightly/runs sections. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache).")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it) before the next claim run - unchanged since 0510Z")
add("Open on William's turn", "note", patient="pat17477798", action="HCA facesheet / card (new chart 9/16, $421, cascade exhausted) - unchanged since 0510Z")
add("Open on William's turn", "note", patient="7 charts", action="'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919) - unchanged since 0910Z")
add("Open on William's turn", "note", patient="5 charts", action="GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919) - unchanged since 0910Z")
add("Open on William's turn", "note", patient="practice", action="no AMD nightly claim run since 9/16 (Automation Center EOD close stopped): the 20 HCA visits cleared this slot ($3,489), the 24 of 9/18 and every rebill since 9/16 have not transmitted")
with open("_run report 9-19 1910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or 9/19, seventeenth consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there 9/19; Drive-wide nothing after 17:00Z 9/19 outside the routine's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 16:45Z Center Pointe admit already acted on (1710Z).")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("medicare-era-819814877-writeoffs-0919", "human", "%s: still waiting on your 'post' or 'leave' - the 41 Medicare-paid lines on written-off charges ($3,283.39) keep ERA checks 1051714/1051715 on the unposted list; the Post button refused the same 43 lines again this run (they are the ones already posted by hand), nothing double-posted." % SLOT)
app("medicare-hospice-b9-denials-0919", "human", "%s: still waiting on your GV / GW / write-off direction per patient for the 5 CO-B9 hospice denials ($949); nothing rebilled or written off." % SLOT)
app("unbilled-unbalanced-postings-0915", "no", "%s: the %d 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % (SLOT, len(unbal)))
app("harwick-delwen-17477798", "no", "%s: chart still has zero insurance plans (getdemographic 19:22Z); no facesheet in Drive (title search 'harris' = a different patient's 8/29 sheet), no Pam email, no board drop; visits 19455030/19455057 ($421) stay in Unbilled 'Insurance order is missing'." % SLOT,
    set_={"patient": "HARWICK,DELWEN", "facility": "HCA FLORIDA CAPITAL HOSPITAL", "amdid": "17477798", "amount": 421, "status": "william",
          "need": "WILLIAM: admission facesheet or card for HARWICK,DELWEN (HCA Florida Capital Hospital, admitted 9/16/2026). Age 73 but CMS has no Medicare record (Stedi MBI lookup with and without the chart SSN: ERR 72); Stedi discovery (FL, DOS 9/16/2026): coveragesFound 0; no facesheet in the HCA/TMH/PCC/Claimocity folders, no Pam email, no board drop. 2 visits (99223 9/16 v19455057, 99232 9/17 v19455030 = $421) wait in Unbilled 'Insurance order is missing'.",
          "why": "Unbilled column 9/19: new chart from the Claimocity feed with no insurance plan ('Insurance order is missing on visit')"})
app("winslow-jr-erwin", "ok", "New HCA 99233 visit 9/18 (v19455131) came through the feed with S81.801S as the only dx again; same 9/3 stay -> admission 09/03/2026 written, M86.9 (dcode1034545415) put in front per your 9/6 rule, full-visit resave onhcfa=1, inspector clear (Pattern 20389 did not re-raise).", note="9/18 visit recoded M86.9 first (same 9/3 stay) and released from the inspector; nothing needed from you.")
app("lisle-keziah-17477774", "ok", "New HCA 99232 visit 9/18 (v19455119): admission 09/14/2026 written; the feed again sent Z96.641 as the only diagnosis -> I10 added in front (dx_primary_fix add-i10) + freq-1 204; UMR 'Source of Payment not typical' advisory bypassed with its fresh id; inspector clear - queued to UMR on the next claim run.")
app("denholt-tracen-17477722", "ok", "New HCA 99232 visit 9/18 (v19455127): admission 09/10/2026 (most recent 99223 within 45d) written, onhcfa=1, inspector clear - queued to UNI20 on the next claim run.")
app("conway-shelby-17477775", "ok", "New HCA 99232 visit 9/18 (v19455129, $111): admission 09/14/2026 written, full-visit resave onhcfa=1, inspector clear - it did NOT land in Unbilled, so the chart's insurance order from your VA facesheet (worked by the 0510Z run) carries it; queued on the next claim run.")
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z-1710Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("board-inbox-registry-0919", "na", "%s: applied map still v1385 (the 05:55Z chat repair); the routine's 0500Z-1710Z files plus this run's 1910Z file sit unapplied in 'board inbox' - nothing trashed; the page's own registry write is still not recording (lastCheck 04:48:56Z)." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
ERRS = "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua)))
SEC = """
## %s columns run (ehpa cloud Code Routine, 19:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main d96e9e3, session branch claude/pensive-einstein-qoonww), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 1710Z START >40 min old with its RUN COMPLETE digest - proceeded at 19:10Z. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). pseudonyms.json 217 -> 221 names.
Boards: Working Denials queue 0; Insurance Refresh Board: drops 0, no item updated after 05:00Z 9/19. Facesheet folders / Claimocity drop / Optum ERA / treasury: nothing new 9/19 outside the routine's own files. Pam Gmail: the three admits already acted on (newest 16:45Z Center Pointe, worked 1710Z) - nothing newer.
Columns: Charge Review 0 -> 0 | Claim Inspector %s | Unbilled %s -> %s ($%s -> $%s): %s | Exclusions 0 -> 0 rows (overview 1/$204.00 lags the list; no claim run newer than 1700202, seventeenth consecutive slot; %d AET12 charges $%.2f open, held). Nothing released or written off; 3 visits freq-1 rebilled by the dx cascade / recode (they were never billed - the rebill only queues them).
ERA step 5: %s
NEEDS WILLIAM (unchanged): (1) 'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919); (2) GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919); (3) pat17477530's voided 9/2-9/4 visits (row ellery-hollis-17477530); pat17477777 rplan18462071 Pre-Auth #, pat17477798 facesheet; no AMD nightly claim run since 9/16 (Automation Center EOD close stopped - third night: the 20 HCA visits cleared this slot, the 24 of 9/18 and every rebill since 9/16 have not transmitted).
Calls learned: no new call shapes; behaviours in captured_calls_additions_2026-09-19_1910UTC (HCA batch 127741 cleared by the 9/18 recipe; recode.swap_proc 99344 -> 99349 applied by the routine for the first time, fee kept; overview counters lag the list).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, INSP_TXT, ovb.get("unbillablecount"), ova.get("unbillablecount", ovb.get("unbillablecount")), ovb.get("unbillableamount"), ova.get("unbillableamount", ovb.get("unbillableamount")), ERRS, len(ver), aet_bal, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-19_1910UTC run digest - backend billing run, 3 PM ET 9/19 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: standing-row checks + the inspector-batch rows) uploaded; nothing trashed (applied map v1385 lists none of the inbox files). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_1910UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
