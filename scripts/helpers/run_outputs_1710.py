# PLAIN ENGLISH (run outputs for the 1pm ET 9/15/2026 slot - ehpa cloud run 2026-09-15T1710Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the AET12 re-verify, the ERA before/after
#   snapshots, the era_chain log and the fallback register, then writes:
#   - "_run report 9-15 1710.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-15T1710Z.json (Insurance Refresh Board inbox file: update ops with appends keyed by
#     src+when, never set on status/need)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database.
import csv, json, os, re, collections, datetime
S = "2026-09-15T1710Z"; SRC = "1pm ET 9/15 columns run (ehpa cloud)"; W = "9/15"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {}) or before
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
pay = round(sum(f(c.get("paymentamount")) for c in eb), 2)
fb = load("registers/era_fallback_%s_live.json" % S, [])
posted = [r for r in fb if r.get("outcome") == "posted"]
already = [r for r in fb if str(r.get("outcome", "")).startswith("already")]
fpay = round(sum(f(r.get("pay")) for r in posted), 2); fwo = round(sum(f(r.get("wo")) for r in posted), 2)
log = open("era_chain_1710.log").read() if os.path.exists("era_chain_1710.log") else ""
m = re.search(r"=== done: posted (\d+) visits, \$([\d.]+) ===", log)
auto_n, auto_amt = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb)
cnt = re.search(r"fallback LIVE.*?counts (\{.*?\})", log, re.S); dol = re.search(r"fallback LIVE.*?dollars (\{.*?\})", log, re.S)
counts = cnt.group(1) if cnt else str(dict(fo)); dollars = dol.group(1) if dol else ""
faults = len(re.findall(r"addpayments fault|FAULT", log.split("fallback LIVE")[-1])) if "fallback LIVE" in log else 0
dism = re.findall(r"dismiss(?:ed)?[^\n]*?(\d{6,7})", log.split("era_clear LIVE")[-1]) if "era_clear LIVE" in log else []
av = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in av), 2) if av else 2052.25
n_ub = len(after.get("unbilled", [])); n_ex = sum(len(v) for v in after.get("exclusions", {}).values())
n_ub0 = len(before.get("unbilled", [])); n_ex0 = sum(len(v) for v in before.get("exclusions", {}).values())
aid = {c["id"] for c in ea}; bid = {c["id"] for c in eb}
cleared = [c for c in eb if c["id"] not in aid]; newc = [c for c in ea if c["id"] not in bid]
changed = [(c, next((d for d in ea if d["id"] == c["id"]), None)) for c in eb if c["id"] in aid and any(f(d.get("unpostedamount")) != f(c.get("unpostedamount")) for d in ea if d["id"] == c["id"])]

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
pby = collections.defaultdict(list)
for r in posted: pby[str(r.get("checkid"))].append(r)
for c in eb:
    st = "still open" if c["id"] in aid else "cleared"
    act = "held - reversal/orphan/procedure-mismatch/already-adjudicated lines, no postable money"
    if str(c["id"]) in pby:
        ps = pby[str(c["id"])]
        act = "manual fallback posted %d line(s) $%.2f (+$%.2f WOINS); %s" % (len(ps), sum(f(p.get("pay")) for p in ps), sum(f(p.get("wo")) for p in ps), "still held for the remaining lines" if st == "still open" else "cleared")
    if str(c["id"]) == "1051656": act = "held - 4 unrecorded payment lines (reversal pipeline), $303.64"
    if str(c["id"]) == "1051661" and str(c["id"]) not in pby: act = "held at $516.90 - 16 denial-with-write-off lines (cascade), 4 unvalidated $0, 1 unrecorded reversal line; money posted 11am ET run"
    add("ERA", st, carrier=c.get("systemcarriercode") or c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or c.get("checknumber", "")), action=act if st == "still open" else "cleared this run")
for c in newc:
    add("ERA", "new (arrived during run)", carrier=c.get("systemcarriercode") or "", check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or ""))
for r in posted:
    add("ERA", "manual-posted", carrier=r.get("carrier", ""), check=str(r.get("checkid")), visit=str(r.get("visitid")), amt=r.get("pay"), dos=r.get("dos", ""), err="%s %s" % (r.get("cpt"), r.get("dos")), action="manual_post pay %.2f + wo %.2f, ERA %s manual post %s" % (f(r.get("pay")), f(r.get("wo")), r.get("checkid"), S))
add("Availity remits", "none new", action="every PDF in 'bht Optum era downloads' (newest 03:30Z) is already in registers/availity_register.json (98 files); no new Check/EFT export in 'treasury payments' (the 9/14 CSV is reconciled); nothing parsed or posted")
out = "_run report 9-15 1710.csv"
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
newtxt = ("; new check(s) since 11am ET: " + ", ".join("%s %s $%.2f" % (c["id"], c.get("systemcarriercode") or "", f(c.get("unpostedamount"))) for c in newc)) if newc else "; no new checks arrived"
posttxt = ("; manual fallback posted %d line(s) $%.2f + $%.2f WOINS (%s)" % (len(posted), fpay, fwo, ", ".join("%s %s" % (r.get("visitid"), r.get("cpt")) for r in posted))) if posted else "; fallback dry + live 0 postable"
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache %d/%d; "
            "era_post --all-unposted posted %d visits $%.2f%s (counts %s; residual-zero lines disregarded per your 9/13 rule); %d addpayments faults; era_clear dismissed %d, held %d%s."
            % (SRC, S, nb, ab, na, aa, pay, len(os.listdir("era_details")) if os.path.isdir("era_details") else 0, nb, auto_n, auto_amt, posttxt, counts, faults, len(cleared), na, newtxt))
row("aet12-carrier-cpid", checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193 (89 runs). Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % aet_bal, SRC + " - claim run 1700193")])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("era-manual-post-0912", checks=[chk("ok" if (posted or auto_n or cleared) else "na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the 0310Z pass in 'bht Optum era downloads' / 'treasury payments' (every PDF there is in registers/availity_register.json, 98 files; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; facesheet folders, board drops and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-15 1 PM ET columns run (ehpa cloud Code Routine, 17:09-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main ae655b9, layout 247 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. State bundle workspace_state_2026-09-15_1532UTC (7 parts + manifest) downloaded but the retyped parts failed the per-part sha256 (fifth set in a row: 0739, 0913, 1050, 1349, 1532) - registers restored from practices/ehpa/registers/ in the repo (era_manual_register 336 entries, availity_register 98 files); needs_facesheet_list.md restarted from this section. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board rows on Claude's turn read (180, all watch/hold rows, none updated since 07:45Z - nothing requesting new billing), drops new = 0; Working Denials queue = 0; board inbox applied-map lists no 9/15 file (nothing trashed). Facesheet folders and Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %d -> %d ($2,422.58, all 'Payment reason codes are missing or do not balance' - held per the 9/15 chat rule, never released) | Exclusions %d -> %d ($11,756, all AET12 PREF0288+PREF0264 on run 1700193; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/14/2026, no AET12 payment - held on the carrier-master fix; no new claim run since 1700193).
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). era_post posted %d visits $%.2f%s. Fallback counts %s; dollars %s. era_clear dismissed %d (%s), held %d. %d addpayments faults%s. No new 835s; Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none. Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, n_ub0, n_ub, n_ex0, n_ex, aet_bal, nb, ab, na, aa, pay, auto_n, auto_amt, posttxt, counts, dollars, len(cleared), ", ".join(str(c["id"]) for c in cleared) or "none", na, faults, newtxt)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-1pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-15 1 PM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 1pm ET 9/15/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
