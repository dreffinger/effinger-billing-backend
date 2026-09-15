# PLAIN ENGLISH (run outputs for the 11am ET 9/15/2026 slot - ehpa cloud run 2026-09-15T1510Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the AET12 re-verify, the ERA before/after
#   snapshots, the era_post log and the fallback register, then writes:
#   - "_run report 9-15 1510.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-15T1510Z.json (Insurance Refresh Board inbox file: update ops with appends keyed by
#     src+when, never set on status/need)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database.
import csv, json, os, re, collections, datetime
S = "2026-09-15T1510Z"; SRC = "11am ET 9/15 columns run (ehpa cloud)"; W = "9/15"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
pay = round(sum(f(c.get("paymentamount")) for c in eb), 2)
fb = load("registers/era_fallback_%s_live.json" % S, [])
posted = [r for r in fb if r.get("outcome") == "posted"]
already = [r for r in fb if str(r.get("outcome", "")).startswith("already")]
fpay = round(sum(f(r.get("pay")) for r in posted), 2); fwo = round(sum(f(r.get("wo")) for r in posted), 2)
log = open("era_chain_1510.log").read()
m = re.search(r"=== done: posted (\d+) visits, \$([\d.]+) ===", log)
auto_n, auto_amt = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb)
cnt = re.search(r"fallback LIVE.*?counts (\{.*?\})", log, re.S); dol = re.search(r"fallback LIVE.*?dollars (\{.*?\})", log, re.S)
counts = cnt.group(1) if cnt else str(dict(fo)); dollars = dol.group(1) if dol else ""
av = load("registers/aet12_verify_%s.json" % S, None) or load("registers/aet12_verify_2026-09-15T0913Z.json", [])
aet_bal = 2052.25
n_ub = len(after.get("unbilled", [])); n_ex = sum(len(v) for v in after.get("exclusions", {}).values())

# ---------- run report CSV
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before and after")
add("Claim Inspector", "clear", action="0 batches before and after")
for r in after.get("unbilled", []):
    err = r["_errs"][0] if r["_errs"] else ""
    add("Unbilled", "remaining", r.get("patientname", ""), r.get("dateofservice", "") or "", r.get("carriercode", "") or "", err,
        "held - 9/13 payment posted with no CARC on a reversed 5/31 write-off; needs the remit reason codes re-posted (no captured call edits payment reason codes) or William's word to release", visit=r.get("id", ""))
for rid, rs in after.get("exclusions", {}).items():
    for r in rs:
        err = " | ".join((e.get("name") or e.get("text") or "")[:70] for e in r["_errs"][:2])
        add("Exclusions", "remaining", "pat%s" % r.get("patientid", ""), r.get("dateofservice", "") or "", (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "", err,
            "held - run 1700193 rejected all 59 AET12 claims again after the AAR01-matched carrier settings; William: suppress the provider loop / Box 33B REF*EI, then 'rebill'", visit=r.get("id", ""))
aid = {c["id"] for c in ea}; bid = {c["id"] for c in eb}
for c in eb:
    st = "still open" if c["id"] in aid else "cleared"
    act = "held - reversal/orphan/procedure-mismatch/already-adjudicated lines, no postable money"
    if str(c["id"]) == "1051661": act = "NEW CAP07 check: era_post posted 3 visits $%.2f, manual fallback posted 4 lines $%.2f (+$%.2f WOINS), 1 $0 line zero-posted; held for 16 denial-with-write-off lines + 4 unvalidated $0 lines + 1 unrecorded reversal-pipeline line ($864.43 -> $516.90 unposted)" % (auto_amt, fpay, fwo)
    if str(c["id"]) == "1051656": act = "held - 4 unrecorded payment lines (reversal pipeline), $303.64"
    add("ERA", st, carrier=c.get("systemcarriercode") or c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or c.get("checknumber", "")), action=act if st == "still open" else "cleared this run")
for c in ea:
    if c["id"] not in bid:
        add("ERA", "new (arrived during run)", carrier=c.get("systemcarriercode") or "", check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or ""))
for r in posted:
    add("ERA", "manual-posted", carrier="CAP07", check=str(r.get("checkid")), visit=str(r.get("visitid")), amt=r.get("pay"), dos=r.get("dos", ""), err="%s %s" % (r.get("cpt"), r.get("dos")), action="manual_post pay %.2f + WOINS %.2f, check 4122475, ERA %s manual post %s" % (f(r.get("pay")), f(r.get("wo")), r.get("checkid"), S))
for r in already:
    add("ERA", "auto-posted (era_post)", carrier="CAP07", check=str(r.get("checkid")), visit=str(r.get("visitid")), dos=r.get("dos", ""), err="%s %s" % (r.get("cpt"), r.get("dos")), action="posted by era_post --all-unposted (posterapayments); fallback saw the payment on the charge")
add("Availity remits", "none new", action="every PDF in 'bht Optum era downloads' (10 ClaimDetails, newest 03:30Z) is already in registers/availity_register.json (98 files); no new Check/EFT export in 'treasury payments' (the 9/14 CSV is reconciled); nothing parsed or posted")
out = "_run report 9-15 1510.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

# ---------- board updates
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
ops = []
def row(id, checks=None, notes=None):
    op = {"op": "update", "collection": "items", "id": id, "append": {}}
    if checks: op["append"]["checks"] = checks
    if notes: op["append"]["notes"] = notes
    ops.append(op)
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache refilled (39); "
            "NEW check 1051661 CAP07 4122475 ($864.43, 29 visits, dated 9/15): era_post --all-unposted posted %d visits $%.2f (19454295, 19454088, 19454298); manual fallback dry + live posted 4 more lines $%.2f pay + $%.2f WOINS at the open balance (19454081 99233 $136.25, 19452054 99232 $70.46, 19454084 99239 $105.78, 19454099 99309 $97.59) with check 4122475 as the check number; era_clear zero-posted 1 $0 line and HELD the check ($516.90 left: 16 denial-with-write-off lines for the cascade, 4 unvalidated $0, 1 unrecorded reversal-pipeline line). "
            "Everything else unchanged: fallback %s (residual-zero lines disregarded per your 9/13 rule); 0 addpayments faults; era_clear 39 looked at, 0 dismissed, 39 held (89 unvalidated money lines $8,203 / 169 already on the visit $4,720 / 1,261 denial-with-write-off / 5 unrecorded reversal $410)."
            % (SRC, S, nb, ab, na, aa, pay, auto_n, auto_amt, fpay, fwo, counts))
row("aet12-carrier-cpid", checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193 (89 runs). Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % aet_bal, SRC + " - claim run 1700193")])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("era-manual-post-0912", checks=[chk("ok", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the 0310Z pass in 'bht Optum era downloads' / 'treasury payments' (all 10 ClaimDetails PDFs there are in registers/availity_register.json, 98 files; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; facesheet folders, board drops and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-15 11 AM ET columns run (ehpa cloud Code Routine, 15:09-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 4e88fd4, layout 246 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. State bundle workspace_state_2026-09-15_1349UTC (7 parts + manifest) downloaded but the retyped parts failed the per-part sha256 (fourth set in a row: 0739, 0913, 1050, 1349) - registers restored from practices/ehpa/registers/ in the repo; needs_facesheet_list.md restarted from this section. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py.
Boards: Insurance Refresh Board rows on Claude's turn read (180, all watch/hold rows - nothing requesting new billing), drops new = 0; Working Denials queue = 0; board inbox applied-map lists no 9/15 file (nothing trashed). Facesheet folders and Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %d -> %d ($2,422.58, all 'Payment reason codes are missing or do not balance' - held per the 9/15 chat rule, never released) | Exclusions %d -> %d ($11,756, all AET12 PREF0288+PREF0264 on run 1700193; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/14/2026, no AET12 payment - held on the carrier-master fix; no new claim run since 1700193).
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). New CAP07 check 1051661 (4122475, $864.43, 29 visits): era_post posted %d visits $%.2f; fallback posted 4 lines $%.2f + $%.2f WOINS (19454081, 19452054, 19454084, 19454099); 1 $0 line zero-posted; check held at $516.90 (16 denial-with-write-off lines, 4 unvalidated $0, 1 unrecorded reversal line). Fallback counts %s; dollars %s. era_clear 0 dismissed, 39 held. 0 addpayments faults. No new 835s; Availity 5(g): nothing new (all 10 PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none. Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, len(before.get("unbilled", [])), n_ub, sum(len(v) for v in before.get("exclusions", {}).values()), n_ex, aet_bal, nb, ab, na, aa, pay, auto_n, auto_amt, fpay, fwo, counts, dollars)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-11amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-15 11 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 11am ET 9/15/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
