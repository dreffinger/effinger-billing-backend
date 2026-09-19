# PLAIN ENGLISH (run outputs for the 5am ET 9/19/2026 slot - ehpa cloud run 2026-09-19T0910Z)
# Decides: nothing. Reads this run's column scans, ERA before/after snapshots and the three ERA registers (fallback, patient-balance
#   pass, true residuals), then writes: "_run report 9-19 0910.csv"; board_updates_2026-09-19T0910Z.json (standing-row checks + three
#   new rows on William's turn: the 41 Medicare-paid lines on written-off charges, the 5 CO-B9 hospice denials, the voided 9/2-9/4 visits
#   of pat17477530); a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys, collections
S = "2026-09-19T0910Z"; SRC = "5am ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "5 AM ET 9/19"
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
fb = load("registers/era_fallback_%s_live.json" % S, []); pb = load("registers/era_patbal_%s_live.json" % S, []); tr = load("registers/era_true_residual_%s.json" % S, [])
fb_posted = [r for r in fb if r["outcome"] == "posted"]; fb_already = [r for r in fb if r["outcome"] == "already-posted"]; fb_orphan = [r for r in fb if r["outcome"] == "orphan"]
pb_lines = [r for r in pb if r["outcome"] == "posted" or "has payment" in r.get("why", "")]
pb_pay = sum(f(r.get("pay")) if r["outcome"] == "posted" else f(r["era_paid"]) for r in pb_lines)
pb_wo = round(sum(f(r.get("wo")) for r in pb if r["outcome"] == "posted") + 4609.37, 2)   # 4609.37 = WOINS of the 79 lines posted by the first (timed-out) pass, from the dry register
pb_moved = 11365.00
ovb = before.get("overview", {}); ova = after.get("overview", {}); ub = before.get("unbilled", []); ua = after.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
unbal = [r for r in ua if (r.get("_errs") or [""])[0].startswith("Payment reason")]
d16 = load("era_details/1051716.json", {}).get("eracheckdetails", [])
HOSP = [(c["visitid"], c["patientid"], c.get("patientname"), str(c.get("dos"))[:10], [(x.get("chargecode"), x.get("paymentamount")) for x in c.get("charges") or []], c.get("insurancebalance")) for c in d16]
ERA_TXT = ("Medicare Part B ERA 819814877 ($46,350.13, AMD entries 1051714 + 1051715, deposit 09/22/2026) arrived 02:03 AMD clock 9/19 with a $0 denial check 349974158 (1051716). "
           "Unposted before %d checks / $%.2f -> after %d / $%.2f. Post button (era_post --all-unposted): 486 lines / $33,915.25 posted (AMD answered fault -2147217287 for the 449 refused lines but posted the rest). "
           "Fallback manual posts: %d lines / $%.2f paid + $%.2f WOINS (residual disregarded $52.21). Patient-balance pass (new helper era_patbal_post_0919_0910.py): 83 lines / 74 visits / 6 charts whose earlier wrong-payer $0 denial (BCBS 213403769, UNI20 26007B1000256937, SUN01 0917650774) had pushed the whole charge to the patient - $11,365.00 moved back to insurance, Medicare $5,138.10 posted + $4,916.18 WOINS, PR coinsurance left for the secondary/patient. "
           "Still unposted $12,434.88 = the manual posts the Center cannot see ($9,013.82) + 41 lines / $3,283.39 Medicare paid on charges already WRITTEN OFF (WOINS x39 9/4-9/17, WOMCAD x2 9/11; 7 charts) - William's decision (void the write-offs and post) - + 1 orphan line $85.46 (pat17477530 v19453715 99233 09/02/2026, charge voided). "
           "1051716 (5 CO-B9 hospice denials, $949, RARC MA01) dismissed after its lines were cached (reversedismiss -> checkdetails -> dismiss); no MA63/M76/M64 lines. 1051714/1051715 HELD by era_clear (orphan + the written-off lines). 0 addpayments faults. No new 835s or Availity/treasury files; Availity 5(g) nothing new."
           % (nb, ab, na, aa, len(fb_posted), sum(f(r.get("pay")) for r in fb_posted), sum(f(r.get("wo")) for r in fb_posted)))
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
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); nothing new to act on" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or so far 9/19 - twelfth consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
for r in fb_posted: add("ERA", "manual-posted (fallback)", "pat%s" % r["pid"], r["dos"], "FLO02", "", "pay %.2f + WOINS %.2f (ERA paid %.2f)" % (r["pay"], r["wo"], r["era_paid"]), r["checkid"], "MEDICARE PART B 819814877", r["visitid"], r["pay"])
for r in pb_lines: add("ERA", "manual-posted (patient balance moved back to insurance)", "pat%s" % r["pid"], r["dos"], "FLO02", "wrong-payer $0 denial had transferred the charge to the patient", "%s: pay %.2f + WOINS %.2f" % (r["cpt"], f(r.get("pay")) or f(r["era_paid"]), f(r.get("wo"))), r["checkid"], "MEDICARE PART B 819814877", r["visitid"], f(r.get("pay")) or f(r["era_paid"]))
for r in tr: add("ERA", "unposted - charge written off (William)", "pat%s" % r["pid"], r["dos"], "FLO02", "Medicare paid %.2f on a charge at $0 after %s" % (r["era_paid"], r["writeoffs"]), "%s: void the write-off and post? (William)" % r["cpt"], "1051714/1051715", "MEDICARE PART B 819814877", r["visit"], r["era_paid"])
for r in fb_orphan: add("ERA", "orphan", "pat%s" % r["pid"], r["dos"], "FLO02", r.get("why", ""), "left in the ERA Center; the 9/2-9/4 visits of this chart are voided with no live replacement (William)", r["checkid"], "MEDICARE PART B 819814877", r["visitid"], r["era_paid"])
for v, p, nm, dos, ch, bal in HOSP: add("ERA", "denial CO-B9 hospice (William GV/GW)", "pat%s" % p, dos, "FLO02", "CO-B9 patient enrolled in hospice, RARC MA01", "%s $%.2f open - needs GV/GW direction, not rebilled, not written off" % (ch[0][0] if ch else "", f(bal)), "1051716", "MEDICARE PART B 349974158", v, bal)
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new; William's 04:26-04:27Z notes ('im here does that solve it', 'i uploaded a va facesheet') were answered/acted on by the 0500Z chat and 0510Z run; board inbox: 3 files (0500Z, 0510Z, 0710Z) not in the applied map (v1385) - nothing trashed")
add("Sources", "read", action="bht hca/tmh/PCC facesheets, Claimocity drop, bht Optum era downloads, treasury payments, chc raw 835: nothing modified after 04:30Z 9/19 (gordon sr.pdf 04:30Z was acted on by the 0500Z chat / 0510Z run); Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit (handled 0310Z)")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 863d00c), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0710Z START >40 min old with its RUN COMPLETE digest - proceeded. State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main - not unpacked; registers from practices/ehpa/registers (117 files), needs_facesheet section from nightly/runs. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache).")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it) before the next claim run - unchanged since 0510Z")
add("Open on William's turn", "note", patient="pat17477798", action="HCA facesheet / card (new chart 9/16, $421, cascade exhausted) - unchanged since 0510Z")
with open("_run report 9-19 0910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or so far 9/19, twelfth consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app("bcbs-patient-balance-audit-0918", "ok", "%s: the Medicare ERA 819814877 settled part of this: 83 Florida-Blue-denied lines on 6 charts (pat17470713 x27, pat17472124 x21, pat17474516 x16, pat17475338 x15, pat17473570 x3, pat17476544 x1) whose $0 PR-22/CO-22 denial had put the whole charge on the patient were moved back to insurance ($11,365.00) and Medicare's payment posted ($5,138.10 + $4,916.18 WOINS); only the PR coinsurance now shows as patient balance on those lines. The rest of the audit (CO-45 split on the Availity-posted lines, the 80 full-charge $0 denials) is unchanged - hold Florida Blue patient statements." % SLOT)
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 04:30Z 9/19) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit already acted on; Claimocity drop and the three facesheet folders: no new file since gordon sr.pdf (04:30Z, handled 0500Z/0510Z).")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("west-shirley-17471007", "human", "%s: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance." % SLOT)
app("unbilled-unbalanced-postings-0915", "no", "%s: the %d 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % (SLOT, len(unbal)))
app("board-inbox-registry-0919", "na", "%s: applied map still v1385 (the 05:55Z chat repair); three unapplied files in 'board inbox' (0500Z, 0510Z, 0710Z) plus this run's - nothing trashed; the page's own registry write is still not recording (lastCheck 04:48:56Z)." % SLOT)
# new rows on William's turn
wo_lines = "; ".join("pat%s v%s %s %s $%.2f (%s %s %s)" % (r["pid"], r["visit"], r["cpt"], r["dos"], r["era_paid"], r["writeoffs"][0][0], r["writeoffs"][0][1], r["writeoffs"][0][2]) for r in tr) if tr else ""
ops.append({"op": "upsert", "collection": "items", "id": "medicare-era-819814877-writeoffs-0919", "set": {
    "patient": "MEDICARE ERA 819814877 - 41 paid lines on charges already written off", "dob": "", "facility": "ERA Center 1051714 / 1051715", "amdid": "", "mbi": "",
    "need": "WILLIAM: Medicare's 9/19 ERA 819814877 pays 41 lines ($3,283.39) on 7 charts whose charges are already at $0 because a run wrote them off between 9/4 and 9/17 (WOINS x39, WOMCAD x2 - the $0 wrong-payer denials of BCBS/UNI20/SUN01 were adjusted off instead of re-routed). The money is real and in the bank. Say 'post' and the next run voids those write-offs (void_tx.void_writeoff) and posts the Medicare payment + contractual WOINS on each line with the ERA check number; say 'leave' and they stay as residuals. Charts: pat17471388 x22 ($1,922.80), pat17472559 x6 ($413.02), pat17472393 x5 ($361.22), pat17473383 x3 ($207.63), pat17472625 x2 ($192.73), pat21442 x2 ($116.78), pat46673 x1 ($69.21). Until then ERA checks 1051714/1051715 stay on the unposted list ($12,434.88 shown, of which $9,013.82 is manual posts the Center cannot see).",
    "why": "ERA step 5, 5am ET 9/19 run: the fallback's '$0 balance = already adjudicated' gate caught these; their charges carry no payment at all, only a write-off.", "amount": 3283.39, "status": "william", "created": NOW, "updated": NOW,
    "notes": [{"who": "Claude", "text": "Created by the 5 AM ET 9/19 run. Line list: " + wo_lines, "at": NOW}],
    "checks": [{"ok": "human", "src": SRC, "result": "41 lines / $3,283.39 Medicare-paid on written-off charges - needs your 'post' or 'leave'", "when": W}]}})
hosp_txt = "; ".join("%s (pat%s) v%s %s %s $%.2f open" % (nm, p, v, ch[0][0] if ch else "", dos, f(bal)) for v, p, nm, dos, ch, bal in HOSP)
ops.append({"op": "upsert", "collection": "items", "id": "medicare-hospice-b9-denials-0919", "set": {
    "patient": "MEDICARE $0 CHECK 349974158 - 5 CO-B9 hospice denials", "dob": "", "facility": "ALF / SNF (99349 / 99309 / 99487)", "amdid": "", "mbi": "",
    "need": "WILLIAM: Medicare denied 5 claims ($949) CO-B9 'patient is enrolled in hospice' (RARC MA01) on the 9/19 $0 check 349974158: %s. Per the POYNOR rule these are not rebilled or written off without your GV/GW direction - say per patient 'GV' (attending physician, bill Medicare with GV), 'GW' (unrelated to the terminal condition) or 'write off' (WONCS), and the next run recodes + freq-1 rebills or posts the write-off." % hosp_txt,
    "why": "ERA step 5, 5am ET 9/19 run: denial-only Medicare check dismissed after its lines were cached; hospice modifier decisions are William's.", "amount": 949, "status": "william", "created": NOW, "updated": NOW,
    "notes": [{"who": "Claude", "text": "Created by the 5 AM ET 9/19 run.", "at": NOW}],
    "checks": [{"ok": "human", "src": SRC, "result": "5 CO-B9 hospice denials $949 - GV / GW / write-off direction needed", "when": W}]}})
ops.append({"op": "upsert", "collection": "items", "id": "melvin-willis-17477530", "set": {
    "patient": "MELVIN,WILLIS F", "dob": "", "facility": "HCA FLORIDA CAPITAL HOSPITAL", "amdid": "17477530", "mbi": "",
    "need": "WILLIAM: Medicare ERA 819814877 pays $85.46 for the 09/02/2026 99233 (visit 19453715, billed to Medicare 9/4) but that charge is VOIDED in AMD, and so are the 09/03 (v19453774) and 09/04 (v19453755) 99233 visits - none has a live replacement. The chart's 08/24-09/01 visits are live on CIG13 Cigna HealthSpring MA (paid 9/11-9/17). Decide: restore / re-enter the 9/2-9/4 visits (to Cigna HealthSpring like the rest, with the 8/24 admission) and treat Medicare's $85.46 as an overpayment to refund, or tell me the visits were voided on purpose. The ERA line stays orphaned in the Center until then.",
    "why": "ERA step 5, 5am ET 9/19 run: orphan money line (AMD error 5 'procedure codes do not match') on a voided charge.", "amount": 85.46, "status": "william", "created": NOW, "updated": NOW,
    "notes": [{"who": "Claude", "text": "Created by the 5 AM ET 9/19 run.", "at": NOW}],
    "checks": [{"ok": "human", "src": SRC, "result": "9/2-9/4/2026 99233 visits voided with no live replacement; Medicare paid the 9/2 line $85.46", "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
ERRS = "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua)))
SEC = """
## %s columns run (ehpa cloud Code Routine, 09:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main 863d00c), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0710Z START >40 min old with its RUN COMPLETE digest - proceeded. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten).
Boards: Working Denials queue 0; Insurance Refresh Board: drops 0; William's 04:26-04:27Z notes were handled by the 0500Z chat / 0510Z run. Facesheet folders / Claimocity drop / Optum ERA / treasury / Pam Gmail: nothing new after 04:30Z.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s -> $%s): %s | Exclusions 0 -> 0 (no claim run newer than 1700202, twelfth consecutive slot; %d AET12 charges $%.2f open, held). Nothing rebilled, released or written off in the columns.
ERA step 5: %s
NEEDS WILLIAM: (1) 'post' or 'leave' for the 41 Medicare-paid lines on written-off charges ($3,283.39, row medicare-era-819814877-writeoffs-0919); (2) GV / GW / write-off for the 5 CO-B9 hospice denials ($949, row medicare-hospice-b9-denials-0919); (3) pat17477530's voided 9/2-9/4 visits (row melvin-willis-17477530); unchanged: pat17477777 rplan18462071 Pre-Auth #, pat17477798 facesheet, pat17471007 MV line, no AMD nightly claim run since 9/16.
Calls learned: no new call shapes; behaviours in captured_calls_additions_2026-09-19_0910UTC (Post button posts the accepted lines despite the fault; $0-balance-with-no-payment = wrong-payer transfer, move back + post; dismissed-check lines readable via reversedismiss).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), ERRS, len(ver), aet_bal, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-19_0910UTC run digest - backend billing run, 5 AM ET 9/19 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (7 standing-row checks + 3 new rows on William's turn) uploaded; nothing trashed (applied map v1385 lists none of the inbox files). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_0910UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
