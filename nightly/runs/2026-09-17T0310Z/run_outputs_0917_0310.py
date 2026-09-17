# PLAIN ENGLISH (run outputs for the 11pm ET 9/16/2026 slot - ehpa cloud run 2026-09-17T0310Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the Unbilled verify/release registers, the
#   AET12 re-verify (run 1700201), the ERA before/after snapshots, the era_chain log and the fallback register, then writes:
#   - "_run report 9-17 0310.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T0310Z.json (Insurance Refresh Board inbox file: update ops with appends keyed by src+when,
#     never set on status/need of an existing row; one new row for the WEST 'MV' charge on William's turn)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Copy of run_outputs_0917_0110.py with the 0310Z stamp, the 126-visit Unbilled
#   release and claim run 1700201 (new nightly run 9/16 18:45) instead of 1700193.
import csv, json, os, re, collections, datetime
S = "2026-09-17T0310Z"; SRC = "11pm ET 9/16 columns run (ehpa cloud)"; W = "9/17"; LOGF = "era_chain_0917_0310.log"
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
log = open(LOGF).read() if os.path.exists(LOGF) else ""
m = re.search(r"=== done: posted (\d+) visits, \$([\d.]+) ===", log)
auto_n, auto_amt = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb)
cnt = re.search(r"fallback LIVE.*?counts (\{.*?\})", log, re.S); dol = re.search(r"fallback LIVE.*?dollars (\{.*?\})", log, re.S)
counts = cnt.group(1) if cnt else str(dict(fo)); dollars = dol.group(1) if dol else ""
faults = len(re.findall(r"addpayments fault|FAULT", log.split("fallback LIVE")[-1].split("era_clear DRY")[0])) if "fallback LIVE" in log else 0
av = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in av), 2) if av else 2052.25
rel = load("registers/unbilled_release_%s.json" % S, {"released": [], "writeoffs": [], "errors": []})
uv = load("registers/unbilled_verify_%s.json" % S, {})
n_rel = sum(len(c["visits"]) for c in rel.get("released", []))
n_ub = len(after.get("unbilled", [])); n_ex = sum(len(v) for v in after.get("exclusions", {}).values())
n_ub0 = len(before.get("unbilled", [])); n_ex0 = sum(len(v) for v in before.get("exclusions", {}).values())
insp0 = before.get("inspector", {}); n_in0 = sum(len(v) for v in insp0.values()) if isinstance(insp0, dict) else len(insp0)
inspA = after.get("inspector", {}); n_in = sum(len(v) for v in inspA.values()) if isinstance(inspA, dict) else len(inspA)
n_cr0 = len(before.get("chargereview", [])); n_cr = len(after.get("chargereview", []))
aid = {c["id"] for c in ea}; bid = {c["id"] for c in eb}
cleared = [c for c in eb if c["id"] not in aid]; newc = [c for c in ea if c["id"] not in bid]
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
ub_before = {r["id"]: r for r in before.get("unbilled", [])}

# ---------- run report CSV
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="%d visits before, %d after" % (n_cr0, n_cr))
add("Claim Inspector", "clear", action="%d visits before, %d after (no batches)" % (n_in0, n_in))
for c in rel.get("released", []):
    for vid in c["visits"]:
        r = ub_before.get(vid, {}); d = uv.get(vid, {})
        add("Unbilled", "released", r.get("patientname", ""), (r.get("_chgs") or [{}])[0].get("dos", "").strip(), ",".join(d.get("carriers", [])) or (r.get("carriercode") or ""),
            "A payment from the prior payor is required", "released (hideunbillablevisits hide=-1) - primary claim out and unanswered (paid $%.2f, newest bill %s); re-queues on its own when the primary pays (9/8 rule)" % (f(d.get("paid")), d.get("newest_bill", "")), visit=vid, amt="%.2f" % f(d.get("insbal")))
for r in after.get("unbilled", []):
    err = r["_errs"][0] if r["_errs"] else ""
    if err.startswith("Payment reason"):
        act = "held - 9/13 payment posted with no CARC on a reversed 5/31 write-off; needs the remit reason codes re-posted (no captured call edits payment reason codes) or William's word to release"
    elif err.startswith("Bill Insurance"):
        act = "held - the visit carries a $75.68 'MV' line (not a CPT, batch 1, no carrier, Bill Insurance = No) with an insurance balance; origin unknown - William: delete the line or set Bill Insurance / move it to the patient balance (board row west-shirley-17471007)"
    else:
        act = "re-check next run"
    add("Unbilled", "remaining", r.get("patientname", ""), (r.get("_chgs") or [{}])[0].get("dos", "").strip(), r.get("carriercode", "") or "", err, act, visit=r.get("id", ""))
for rid, rs in after.get("exclusions", {}).items():
    for r in rs:
        err = " | ".join((e.get("name") or e.get("text") or "")[:70] for e in r["_errs"][:2])
        add("Exclusions", "remaining", "pat%s" % r.get("patientid", ""), (r.get("_chgs") or [{}])[0].get("dos", "").strip(), (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "", err,
            "held - claim run 1700201 (9/16 18:45, 80 claims) rejected all 59 AET12 claims again (claim letter G): the carrier record still transmits the TIN as the payer id; not rebilled - William: IDs dialog / Claim Fields / Box 33B REF*EI or an AMD case for the 837, then 'rebill'", visit=r.get("id", ""))
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
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' newer than the registered set (nothing modified there after 9/16 12:00Z; every PDF is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled); nothing parsed or posted")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board drops 0 new, 0 rows on William's turn, no row updated after 19:40Z 9/16; facesheet folders (hca/tmh/PCC/Claimocity/parent), Optum ERA folder, treasury folder: nothing new (Drive-wide listing 03:12Z 9/17); Pam Gmail (newer_than:2d) empty")
out = "_run report 9-17 0310.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

# ---------- board updates
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
ops = []
def row(id, checks=None, notes=None, api=None, op="update", set_=None):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if set_: o["set"] = set_
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    if api: o["append"]["api"] = api
    ops.append(o)
newtxt = ("; new check(s) since 9pm ET: " + ", ".join("%s %s $%.2f" % (c["id"], c.get("systemcarriercode") or "", f(c.get("unpostedamount"))) for c in newc)) if newc else "; no new checks arrived during the run"
posttxt = ("; manual fallback posted %d line(s) $%.2f + $%.2f WOINS (%s)" % (len(posted), fpay, fwo, ", ".join("%s %s" % (r.get("visitid"), r.get("cpt")) for r in posted))) if posted else "; fallback dry + live 0 postable"
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache %d/%d; "
            "era_post --all-unposted posted %d visits $%.2f%s (counts %s; residual-zero lines disregarded per your 9/13 rule); %d addpayments faults; era_clear dismissed %d%s, held %d%s."
            % (SRC, S, nb, ab, na, aa, pay, len(os.listdir("era_details")) if os.path.isdir("era_details") else 0, nb, auto_n, auto_amt, posttxt, counts, faults, len(cleared), (" (%s)" % ", ".join("%s %s" % (c["id"], c.get("systemcarriercode") or "") for c in cleared)) if cleared else "", na, newtxt))
row("aet12-carrier-cpid", checks=[chk("no", "NEW CLAIM RUN 1700201 (AMD clock 2026-09-16 18:45, MCKGRP, 80 claims $17,240) carried the 59 AET12 claims out again (claim letter G) and Change Health front-end rejected all 59 once more: PREF0288 INVALID PAYER ID/CPID 814723941 (TIN) + PREF0264 MISS/INVD PAYER DOC CONTRL NUM ($11,756 exclusion column; 15 charts, 68 AET12 charges re-read via gettxhistory: billdate 09/16/2026, no AET12 payment, insurance balance $%.2f open, none at $0). Whatever carrier-record change preceded this re-send did not change the transmitted payer id. Held, not rebilled, not completed (%s runs). Left: IDs dialog / Claim Fields / EDI-Other Box 33B REF*EI, or an AMD support case for the 837 of run 1700201 naming the segment carrying 814723941." % (aet_bal, runs_n), SRC + " - claim run 1700201")],
    notes=[{"who": "Claude", "at": NOW, "text": "11pm ET 9/16 run: the nightly claim run 1700201 (9/16 18:45) re-sent all 59 AET12 claims and every one bounced again with the TIN as payer id (PREF0288 + PREF0264). Not rebilling a further time - the record still needs the IDs dialog / Claim Fields / Box 33B check or the AMD 837 case; say 'rebill' when it is changed."}])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("unbilled-prior-payor-release-0917", op="upsert", set_={"patient": "UNBILLED - prior-payor secondaries (126 visits, 34 charts)", "dob": "", "facility": "", "amdid": "", "mbi": "", "need": "None - released. 126 Unbilled rows 'A payment from the prior payor is required before another claim can be submitted' appeared after claim run 1700201 (9/16 18:45): secondary claims whose primary was sent and is still unanswered (34 charts, DOS 9/2025-8/2026, $%.2f insurance balance). Verified via gettxhistory (primary billed, $0 paid or payment inside the 60-day window; Garrett's Medicaid payment 114 days old = window open) and released with hideunbillablevisits hide=-1 in 6 chunks; they re-queue on their own when the primary pays (9/8 rule). No write-offs." % sum(f(d.get("insbal")) for d in uv.values()), "why": "Unbilled column 138 -> %d this run: 126 prior-payor secondaries (released), 11 unbalanced-posting rows (held), 1 'Bill Insurance = No' row (west-shirley-17471007)" % n_ub, "amount": round(sum(f(d.get("insbal")) for d in uv.values()), 2), "status": "claude", "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 11pm ET 9/16 run (2026-09-17T0310Z): registers/unbilled_verify_%s.json + unbilled_release_%s.json." % (S, S)}]},
    checks=[chk("ok", "126 prior-payor rows verified (125 primary-unanswered, 1 Medicaid-paid inside the window) and released, 0 write-offs, 0 errors; Unbilled column %d -> %d" % (n_ub0, n_ub))])
row("west-shirley-17471007", op="upsert", set_={"patient": "WEST,SHIRLEY", "dob": "", "facility": "HCA (CHP visit 2/2/2024)", "amdid": "17471007", "mbi": "", "need": "WILLIAM: visit 19375395 (DOS 02/02/2024, 99232 to CHP, chart 2059) now carries a second line - charge 23365777, procedure code 'MV' (not a CPT), $75.68, batch 1, no carrier, Bill Insurance = No - with a $75.68 INSURANCE balance and no payment. The Unbilled column flags it 'Bill Insurance = No at charge level and charge has insurance balance'. The run does not know where the 'MV' line came from (it is not in any register), so it did not touch it. Please delete the line, or set Bill Insurance = Yes with the carrier, or move the $75.68 to the patient balance - then it drops off Unbilled.", "why": "Unbilled column: 'Bill Insurance = No at charge level and charge has insurance balance' on visit 19375395 (new this run)", "amount": 75.68, "status": "william", "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 11pm ET 9/16 run (2026-09-17T0310Z). gettxhistory: charge 23365777 proccode MV dos 02/02/2024 insbal 75.68 patbal 0 paid 0, no carrier, no payment or write-off on the visit; the 99232 line on the same visit is unchanged."}]},
    checks=[chk("human", "visit 19375395 'MV' $75.68 line with Bill Insurance = No - William to delete / set bill-insurance / move to patient balance")])
row("era-manual-post-0912", checks=[chk("ok" if (posted or auto_n or cleared) else "na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/16 12:00Z; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-16 11 PM ET columns run (ehpa cloud Code Routine, 03:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 03abf7d, layout 284 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. Drive 'workspace mirror' still holds no state bundle newer than workspace_state_2026-09-15_1836UTC (its manifest was fetched; the parts are older than the repo state, so nothing from it was used); registers restored from practices/ehpa/registers/ in the repo (0110Z state); needs_facesheet_list.md = the Drive 0630UTC copy + the repo's 0710Z-0110Z run sections; captured_calls.md = GitHub main docs/captured_calls.md; precheck_cache from Drive (9/16 06:25Z). Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 184 rows on Claude's turn, 0 on William's turn, 0 rows updated after 19:40Z 9/16; drops new = 0; Working Denials queue = 0. Board inbox: the registry's applied map lists only 9/12-9/14 files, none still in the inbox - nothing trashed (27 unapplied board_updates files wait for William to open the board). Facesheet folders (hca/tmh/PCC/Claimocity), Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new (Drive-wide listing 03:12Z 9/17).
NEW CLAIM RUN 1700201 (AMD clock 9/16 18:45, MCKGRP, 80 claims $17,240, %s runs): it re-sent the 59 AET12 claims (claim letter G) and Change Health rejected all 59 again (PREF0288 TIN + PREF0264); it also queued 126 secondary claims that landed in Unbilled as 'A payment from the prior payor is required'.
Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (no batches) | Unbilled %d -> %d: 126 prior-payor secondaries verified via gettxhistory (34 charts, primary billed and unanswered; Garrett Medicaid paid 114 days ago = window open) and RELEASED (hideunbillablevisits hide=-1, 6 chunks, 0 write-offs); 11 'Payment reason codes are missing or do not balance' ($2,422.58) held per the 9/15 chat rule; 1 NEW 'Bill Insurance = No at charge level and charge has insurance balance' - WEST,SHIRLEY visit 19375395 (2/2/2024 CHP) carries an unexplained 'MV' $75.68 line with Bill Insurance = No -> board row west-shirley-17471007 on William's turn | Exclusions %d -> %d: 59 AET12 PREF0288+PREF0264 on run 1700201 held ($11,756; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/16/2026, no AET12 payment) - not rebilled again.
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). era_post posted %d visits $%.2f%s. Fallback counts %s; dollars %s. era_clear dismissed %d (%s), held %d. %d addpayments faults%s. No new 835s in the Optum folder; Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none (every call this run is a captured shape: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, gettxhistory, hideunbillablevisits, GET /api/era/checks, checkdetails, posterapayments, locks/release-expired, checks/dismiss). Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, runs_n, n_cr0, n_cr, n_in0, n_in, n_ub0, n_ub, n_ex0, n_ex, aet_bal, nb, ab, na, aa, pay, auto_n, auto_amt, posttxt, counts, dollars, len(cleared), ", ".join(str(c["id"]) for c in cleared) or "none", na, faults, newtxt)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-11pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-16 11 PM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 11pm ET 9/16/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
