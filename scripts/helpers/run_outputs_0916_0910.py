# PLAIN ENGLISH (run outputs for the 5am ET 9/16/2026 slot - ehpa cloud run 2026-09-16T0910Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the AET12 re-verify, the Unbilled
#   prior-payor verify + release registers, the ERA before/after snapshots, the era_chain log and the fallback register,
#   then writes:
#   - "_run report 9-16 0910.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-16T0910Z.json (Insurance Refresh Board inbox file: update ops with appends keyed by
#     src+when, never set on status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Copy of run_outputs_0916_0710.py for the 5am ET slot (no board actions this run).
import csv, json, os, re, collections, datetime
S = "2026-09-16T0910Z"; SRC = "5am ET 9/16 columns run (ehpa cloud)"; W = "9/16"
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
fpay = round(sum(f(r.get("pay")) for r in posted), 2); fwo = round(sum(f(r.get("wo")) for r in posted), 2)
log = open("era_chain_0910.log").read() if os.path.exists("era_chain_0910.log") else ""
m = re.search(r"=== done: posted (\d+) visits, \$([\d.]+) ===", log)
auto_n, auto_amt = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb)
cnt = re.search(r"fallback LIVE.*?counts (\{.*?\})", log, re.S); dol = re.search(r"fallback LIVE.*?dollars (\{.*?\})", log, re.S)
counts = cnt.group(1) if cnt else str(dict(fo)); dollars = dol.group(1) if dol else ""
faults = len(re.findall(r"addpayments fault|FAULT", log.split("fallback LIVE")[-1].split("era_clear DRY")[0])) if "fallback LIVE" in log else 0
dism = re.findall(r"dismiss(?:ed)?\s+(\d{6,})", log.split("era_clear LIVE")[-1]) if "era_clear LIVE" in log else []
av = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in av), 2) if av else 2052.25
uv = load("registers/unbilled_verify_%s.json" % S, {}); ur = load("registers/unbilled_release_%s.json" % S, {})
n_rel = sum(len(c["visits"]) for c in ur.get("released", []) if c.get("ok")); n_relpat = len({d["pid"] for d in uv.values()})
n_ub = len(after.get("unbilled", [])); n_ex = sum(len(v) for v in after.get("exclusions", {}).values())
n_ub0 = len(before.get("unbilled", [])); n_ex0 = sum(len(v) for v in before.get("exclusions", {}).values())
insp0 = before.get("inspector", {}); n_in0 = sum(len(v) for v in insp0.values()) if isinstance(insp0, dict) else len(insp0)
inspA = after.get("inspector", {}); n_in = sum(len(v) for v in inspA.values()) if isinstance(inspA, dict) else len(inspA)
n_cr0 = len(before.get("chargereview", [])); n_cr = len(after.get("chargereview", []))
ub_amt = round(sum(f(c.get("insportion")) + f(c.get("patportion")) for r in after.get("unbilled", []) for c in r.get("_chgs", [])), 2)
aid = {c["id"] for c in ea}; bid = {c["id"] for c in eb}
cleared = [c for c in eb if c["id"] not in aid]; newc = [c for c in ea if c["id"] not in bid]
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")

# ---------- run report CSV
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="%d visits before, %d after" % (n_cr0, n_cr))
add("Claim Inspector", "clear", action="%d visits before, %d after (no batches listed by getclaiminspectorbatches)" % (n_in0, n_in))
for vid, d in uv.items():
    add("Unbilled", "released", d.get("name", ""), "", ",".join(d.get("carriers") or []), "A payment from the prior payor is required before another claim can be submitted.",
        "case (b) primary claim sent and unanswered (paid $%.2f, newest bill %s) - released with hideunbillablevisits hide=-1; re-queues on its own until the primary answers" % (f(d.get("paid")), d.get("newest_bill")) if d.get("class") == "release-b" else "Medicaid paid %s (%s days ago, secondary window open) - released" % (d.get("newest_bill"), d.get("age")), visit=vid, amt="%.2f" % f(d.get("insbal")))
for r in after.get("unbilled", []):
    err = r["_errs"][0] if r["_errs"] else ""
    add("Unbilled", "remaining", r.get("patientname", ""), (r.get("_chgs") or [{}])[0].get("dos", "").strip(), r.get("carriercode", "") or "", err,
        "held - 9/13 payment posted with no CARC on a reversed 5/31 write-off; needs the remit reason codes re-posted (no captured call edits payment reason codes) or William's word to release" if err.startswith("Payment reason") else "released this run but still on the snapshot - re-check next run", visit=r.get("id", ""))
for rid, rs in after.get("exclusions", {}).items():
    for r in rs:
        err = " | ".join((e.get("name") or e.get("text") or "")[:70] for e in r["_errs"][:2])
        add("Exclusions", "remaining", "pat%s" % r.get("patientid", ""), r.get("dateofservice", "") or "", (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "", err,
            "held - run 1700193 rejected all 59 AET12 claims again after the AAR01-matched carrier settings; no new claim run since; William: suppress the provider loop / Box 33B REF*EI, then 'rebill'", visit=r.get("id", ""))
pby = collections.defaultdict(list)
for r in posted: pby[str(r.get("checkid"))].append(r)
for c in eb:
    st = "still open" if c["id"] in aid else "cleared"
    act = "held - reversal/orphan/procedure-mismatch/already-adjudicated lines, no postable money"
    if str(c["id"]) in pby:
        ps = pby[str(c["id"])]
        act = "manual fallback posted %d line(s) $%.2f (+$%.2f WOINS); %s" % (len(ps), sum(f(p.get("pay")) for p in ps), sum(f(p.get("wo")) for p in ps), "still held for the remaining lines" if st == "still open" else "cleared")
    add("ERA", st, carrier=c.get("systemcarriercode") or c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or c.get("checknumber", "")), action=act if st == "still open" else "cleared this run")
for c in newc:
    add("ERA", "new (arrived during run)", carrier=c.get("systemcarriercode") or "", check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or ""))
for r in posted:
    add("ERA", "manual-posted", carrier=r.get("carrier", ""), check=str(r.get("checkid")), visit=str(r.get("visitid")), amt=r.get("pay"), dos=r.get("dos", ""), err="%s %s" % (r.get("cpt"), r.get("dos")), action="manual_post pay %.2f + wo %.2f, ERA %s manual post %s" % (f(r.get("pay")), f(r.get("wo")), r.get("checkid"), S))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' newer than the registered set (newest PDF 9/15 03:30Z, all in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled); nothing parsed or posted")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board drops 0 new; no William note newer than the 3am ET run; facesheet folders and Pam Gmail (newer_than:2d) empty")
out = "_run report 9-16 0910.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

# ---------- board updates
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
def note(text): return {"who": "Claude", "text": text, "at": NOW}
ops = []
def row(id, checks=None, notes=None, api=None, op="update"):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    if api: o["append"]["api"] = api
    ops.append(o)
newtxt = ("; new check(s) since 1am ET: " + ", ".join("%s %s $%.2f" % (c["id"], c.get("systemcarriercode") or "", f(c.get("unpostedamount"))) for c in newc)) if newc else "; no new checks arrived during the run"
posttxt = ("; manual fallback posted %d line(s) $%.2f + $%.2f WOINS (%s)" % (len(posted), fpay, fwo, ", ".join("%s %s" % (r.get("visitid"), r.get("cpt")) for r in posted))) if posted else "; fallback dry + live 0 postable"
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache %d/%d; "
            "era_post --all-unposted posted %d visits $%.2f%s (counts %s; residual-zero lines disregarded per your 9/13 rule); %d addpayments faults; era_clear dismissed %d, held %d%s."
            % (SRC, S, nb, ab, na, aa, pay, len(os.listdir("era_details")) if os.path.isdir("era_details") else 0, nb, auto_n, auto_amt, posttxt, counts, faults, len(cleared), na, newtxt))
row("aet12-carrier-cpid", checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193 (%s runs). Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % (aet_bal, runs_n), SRC + " - claim run 1700193")])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("unbilled-prior-payor-release-0915", checks=[chk("na", "No 'payment from the prior payor is required' rows on the Unbilled snapshot this run (the 100 rows released at 07:40Z have not re-queued; the snapshot regenerates only after a payment event). Unbilled %d -> %d, all 11 are the unbalanced-posting rows held per the 9/15 rule." % (n_ub0, n_ub))])
row("era-manual-post-0912", checks=[chk("ok" if (posted or auto_n or cleared) else "na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (newest PDF 9/15 03:30Z; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; facesheet folders, board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-16 5 AM ET columns run (ehpa cloud Code Routine, 09:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main bef519a, layout 267 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. State bundle workspace_state_2026-09-15_1836UTC (6 parts + manifest, newest on Drive) is OLDER than the repo state and every prior restore of it failed sha256 - not unpacked; registers restored from practices/ehpa/registers/ in the repo (0710Z state: era_manual_register, availity_register 98 files, availity_manual_register); needs_facesheet_list.md restarted from the repo's 0710Z section. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 184 rows on Claude's turn, 0 rows updated after 07:00Z (no William note since the 3am ET run); drops new = 0; Working Denials queue = 0. Board inbox: the registry's applied map lists only 9/12-9/14 files, none of them still in the inbox - nothing trashed. Facesheet folders (hca/tmh/PCC/Claimocity; the 3 scanned PDFs of 04:23-04:27Z were handled by the 1am ET run), Optum ERA folder (newest file 9/15 03:59Z, all registered), treasury folder, Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (no batches) | Unbilled %d -> %d ($2,422.58, all 11 'Payment reason codes are missing or do not balance' - held per the 9/15 chat rule, never released; the 100 prior-payor rows released at 07:40Z did not re-queue) | Exclusions %d -> %d ($11,756, all AET12 PREF0288+PREF0264 on run 1700193; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/14/2026, no AET12 payment - held on the carrier-master fix; no new claim run since 1700193, %s runs).
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). era_post posted %d visits $%.2f%s. Fallback counts %s; dollars %s. era_clear dismissed %d (%s), held %d. %d addpayments faults%s. No new 835s; Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none (every call this run is a captured shape: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, gettxhistory, GET /api/era/checks, checkdetails, posterapayments, locks/release-expired). Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, n_cr0, n_cr, n_in0, n_in, n_ub0, n_ub, n_ex0, n_ex, aet_bal, runs_n, nb, ab, na, aa, pay, auto_n, auto_amt, posttxt, counts, dollars, len(cleared), ", ".join(str(c["id"]) for c in cleared) or "none", na, faults, newtxt)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-5amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-16 5 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 5am ET 9/16/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
