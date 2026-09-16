# PLAIN ENGLISH (run outputs for the 7am ET 9/16/2026 slot - ehpa cloud run 2026-09-16T1110Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the AET12 re-verify, the duplicate-exclusion
#   register (18 HUM01 rows on run 1700192 completed, no rebill), the ERA before/after snapshots, the era_chain log and the
#   fallback register, then writes:
#   - "_run report 9-16 1110.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-16T1110Z.json (Insurance Refresh Board inbox file: update ops with appends keyed by
#     src+when, never set on status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Copy of run_outputs_0916_0910.py for the 7am ET slot (+ duplicate exclusions,
#   + the three facesheet scans read visually with pdftoppm this run).
import csv, json, os, re, collections, datetime
S = "2026-09-16T1110Z"; SRC = "7am ET 9/16 columns run (ehpa cloud)"; W = "9/16"
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
log = open("era_chain_1110.log").read() if os.path.exists("era_chain_1110.log") else ""
m = re.search(r"=== done: posted (\d+) visits, \$([\d.]+) ===", log)
auto_n, auto_amt = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb)
cnt = re.search(r"fallback LIVE.*?counts (\{.*?\})", log, re.S); dol = re.search(r"fallback LIVE.*?dollars (\{.*?\})", log, re.S)
counts = cnt.group(1) if cnt else str(dict(fo)); dollars = dol.group(1) if dol else ""
faults = len(re.findall(r"addpayments fault|FAULT", log.split("fallback LIVE")[-1].split("era_clear DRY")[0])) if "fallback LIVE" in log else 0
av = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in av), 2) if av else 2052.25
dup = load("registers/excl_dup_1700192_%s.json" % S, {})
dup_rows = dup.get("rows", []); dup_bal = round(sum(f(c.get("insbal")) for c in dup.get("charges", [])), 2)
dup_ok = "success=\"1\"" in dup.get("hide_result", "") and not dup.get("relist_visits")
n_ub = len(after.get("unbilled", [])); n_ex = sum(len(v) for v in after.get("exclusions", {}).values())
n_ub0 = len(before.get("unbilled", [])); n_ex0 = sum(len(v) for v in before.get("exclusions", {}).values())
insp0 = before.get("inspector", {}); n_in0 = sum(len(v) for v in insp0.values()) if isinstance(insp0, dict) else len(insp0)
inspA = after.get("inspector", {}); n_in = sum(len(v) for v in inspA.values()) if isinstance(inspA, dict) else len(inspA)
n_cr0 = len(before.get("chargereview", [])); n_cr = len(after.get("chargereview", []))
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
for r in after.get("unbilled", []):
    err = r["_errs"][0] if r["_errs"] else ""
    add("Unbilled", "remaining", r.get("patientname", ""), (r.get("_chgs") or [{}])[0].get("dos", "").strip(), r.get("carriercode", "") or "", err,
        "held - 9/13 payment posted with no CARC on a reversed 5/31 write-off; needs the remit reason codes re-posted (no captured call edits payment reason codes) or William's word to release" if err.startswith("Payment reason") else "re-check next run", visit=r.get("id", ""))
for d in dup_rows:
    add("Exclusions", "completed", "pat%s" % dup.get("pid", ""), d.get("dos", ""), "HUM01", d.get("err", "")[:90],
        "payer duplicate-claim rejection on run %s -> hideexclusions (success=1, run re-lists 0), NOT rebilled (standing rule: duplicate rejections are completed, never re-sent; the visits stay open insurance balances for the Humana adjudication already on file - see board row obrien-patrick-44953)" % dup.get("run"), visit=d.get("visit", ""))
for rid, rs in after.get("exclusions", {}).items():
    for r in rs:
        err = " | ".join((e.get("name") or e.get("text") or "")[:70] for e in r["_errs"][:2])
        add("Exclusions", "remaining", "pat%s" % r.get("patientid", ""), (r.get("_chgs") or [{}])[0].get("dos", "").strip(), (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "", err,
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
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' newer than the registered set (nothing modified there after 9/15 12:00Z; every PDF is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled); nothing parsed or posted")
add("Facesheets", "read", "pat17471832", "05/27/2026", "BCBS", "PR-39 auth denial (5/27/2026 admission)", "the two 'Omnissa Horizon' scans (04:25/04:27Z) are HCA Commure pages for this chart: the visits list 9/2021-9/2026 and the 5/27-6/1/2026 visit detail (BC MCR BlueMedicare Value PPO XJPH46640684, Authorization # BLANK) - so no auth number exists to put on the visit; the 5/27 99223 WONCS write-off the 1am run posted on William's note stands. The 4/2 and 4/28/2026 admission 99223s ($620) are NOT denied - billed 9/10/2026 and still pending; nothing to do.", visit="19443552", amt="310.00")
add("Facesheets", "read", "pat17475906", "03/29/2026", "BCBS", "CO-22/N598 employer group primary", "moriarty.pdf (04:23Z) = the TMH EpicCare coverage page: BCBS FL Medicare Advantage XJPH45679241 eff 1/1/2025 + BCBS PPO XJBH22972394 eff 2/1/2019 (no end entered) - matches the chart (MA seq 1, group PPO seq 2 begin 01/01/2025 end 07/31/2026 per CMS COB; TMH shows no end date - kept CMS's 7/31/2026). Nothing further to do; the 10 rebilled visits are pending.", visit="19436843", amt="111.00")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board drops 0 new; no William note newer than the 1am ET run (rows updated after 09:00Z: 0); Pam Gmail (newer_than:2d) empty")
out = "_run report 9-16 1110.csv"
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
newtxt = ("; new check(s) since 5am ET: " + ", ".join("%s %s $%.2f" % (c["id"], c.get("systemcarriercode") or "", f(c.get("unpostedamount"))) for c in newc)) if newc else "; no new checks arrived during the run"
posttxt = ("; manual fallback posted %d line(s) $%.2f + $%.2f WOINS (%s)" % (len(posted), fpay, fwo, ", ".join("%s %s" % (r.get("visitid"), r.get("cpt")) for r in posted))) if posted else "; fallback dry + live 0 postable"
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache %d/%d; "
            "era_post --all-unposted posted %d visits $%.2f%s (counts %s; residual-zero lines disregarded per your 9/13 rule); %d addpayments faults; era_clear dismissed %d%s, held %d%s."
            % (SRC, S, nb, ab, na, aa, pay, len(os.listdir("era_details")) if os.path.isdir("era_details") else 0, nb, auto_n, auto_amt, posttxt, counts, faults, len(cleared), (" (%s)" % ", ".join("%s %s" % (c["id"], c.get("systemcarriercode") or "") for c in cleared)) if cleared else "", na, newtxt))
row("aet12-carrier-cpid", checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193 (%s runs). Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % (aet_bal, runs_n), SRC + " - claim run 1700193")])
row("obrien-patrick-44953", checks=[chk("ok" if dup_ok else "no", "Claim run 1700192 (9/14 21:07) carried 18 HUM01 payer rejections on this chart - 'ACK/RETURNED AS UNPROCESSABLE CLAIM ... DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM' on visits %s ($%.2f insurance balance, billdate 09/14/2026, paid $0). Standing rule: duplicate-claim rejections are completed, never rebilled -> hideexclusions run 1700192 x18 -> success=1, run re-lists 0. Nothing re-sent; the balances stay for the Humana adjudication already on file (frequency 7 with the ICN if a correction is ever needed). Exclusions column 77 -> %d." % (", ".join(d.get("visit", "") for d in dup_rows), dup_bal, n_ex), SRC + " - Exclusions")])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("era-manual-post-0912", checks=[chk("ok" if (posted or auto_n or cleared) else "na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/15 12:00Z; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
row("savage-janice-17471832", checks=[chk("na", "Read your two HCA Commure scans from 04:25/04:27Z ('Omnissa Horizon.pdf' = the visits list 9/2021-9/2026, 'Omnissa Horizon savage.pdf' = the 5/27-6/1/2026 visit detail: BC MCR BlueMedicare Value PPO XJPH46640684 eff 06/01/26, Authorization # BLANK) rendered with pdftoppm this run. No auth number exists for the 5/27 stay, so the WONCS write-off of the 5/27/2026 99223 ($310) the 1am run posted on your note stands. The 4/2 and 4/28/2026 admission 99223s ($620 insurance balance) are not denied - billed 9/10/2026 and pending. Nothing open here for you.", SRC + " - facesheet scans")],
    notes=[note("Your two HCA scans are this chart (SAVAGE, JANICE C): the visit detail for the 5/27 stay shows the Authorization # box empty, so nothing to put on the claim - the write-off stands. The April admissions are just pending.")])
row("moriarty-pate-nell-17475906", checks=[chk("ok", "Read moriarty.pdf (04:23Z, TMH EpicCare 'Active Insurance as of 9/16/2026') rendered with pdftoppm: BLUE CROSS FL MEDICARE ADVANTAGE XJPH45679241 eff 1/1/2025 and BCBS IN STATE PPO XJBH22972394 eff 2/1/2019 (no end entered). Chart matches what the 1am run built from your paste: MA XJPH45679241 seq 1, group PPO XJBH22972394 seq 2 (begin 01/01/2025, end 07/31/2026 = CMS's working-aged COB window; TMH shows no end date - CMS kept), patient order 2,1; the 10 rebilled visits are pending. Nothing further needed.", SRC + " - facesheet scan")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-16 7 AM ET columns run (ehpa cloud Code Routine, 11:09-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main cf96a3f, layout 270 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. State bundle workspace_state_2026-09-15_1836UTC (6 parts + manifest, newest on Drive) is OLDER than the repo state and every prior restore of it failed sha256 - not unpacked; registers restored from practices/ehpa/registers/ in the repo (0910Z state); needs_facesheet_list.md restarted from the repo's 0910Z section; captured_calls.md = the Drive copy (92,698 bytes, 09:42Z). Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). poppler-utils installed this run (pdftoppm/pdftotext) so scanned facesheets are readable.
Boards: Insurance Refresh Board - 184 rows on Claude's turn, 0 rows updated after 09:00Z (no William note since the 1am ET run); drops new = 0; Working Denials queue = 0. Board inbox: the registry's applied map lists only 9/12-9/14 files, none still in the inbox - nothing trashed. Facesheet folders: the 3 scanned PDFs of 04:23-04:27Z read VISUALLY this run - moriarty.pdf = TMH coverage page for pat17475906 (MA XJPH45679241 + group PPO XJBH22972394; chart already matches the 1am fix), the two 'Omnissa Horizon' scans = HCA Commure visits list + 5/27-6/1/2026 visit detail for pat17471832 (BlueMedicare Value PPO XJPH46640684, Authorization # blank -> the 1am WONCS write-off stands; the 4/2 + 4/28 99223s $620 are pending since 9/10, not denied). Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (no batches) | Unbilled %d -> %d ($2,422.58, all 11 'Payment reason codes are missing or do not balance' - held per the 9/15 chat rule, never released) | Exclusions %d -> %d: 18 NEW HUM01 payer duplicate-claim rejections on run 1700192 (pat44953, $%.2f, billdate 09/14/2026) completed with hideexclusions (success=1, re-list 0), NOT rebilled per the duplicate rule; 59 AET12 PREF0288+PREF0264 on run 1700193 held ($11,756; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/14/2026, no AET12 payment; no new claim run since 1700193, %s runs).
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). era_post posted %d visits $%.2f%s. Fallback counts %s; dollars %s. era_clear dismissed %d (%s), held %d. %d addpayments faults%s. The two dismissed checks are one NEW Medicare $0 no-pay ERA (check 349954684, split 1051672/1051673, 531 denial-only lines: OA18 duplicate x1,230 - the 9/14 mass rebills answered as duplicates of adjudicated claims, CO109 not-covered-by-this-payer x78, CO16/N382 x28, no MA63/M76/M64 so no dx_primary_fix work) - denial-only, dismissed; the lines go to the Working Denials board on the next 'rerun'. No new 835s; Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none (every call this run is a captured shape: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, hideexclusions, gettxhistory, getdemographic, GET /api/era/checks, checkdetails, posterapayments, locks/release-expired, checks/dismiss). Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, n_cr0, n_cr, n_in0, n_in, n_ub0, n_ub, n_ex0, n_ex, dup_bal, aet_bal, runs_n, nb, ab, na, aa, pay, auto_n, auto_amt, posttxt, counts, dollars, len(cleared), ", ".join(str(c["id"]) for c in cleared) or "none", na, faults, newtxt)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-7amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-16 7 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 7am ET 9/16/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
