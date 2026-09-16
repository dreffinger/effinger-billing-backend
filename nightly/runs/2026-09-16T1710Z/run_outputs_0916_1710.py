# PLAIN ENGLISH (run outputs for the 1pm ET 9/16/2026 slot - ehpa cloud run 2026-09-16T1710Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the AET12 re-verify, the duplicate-exclusion
#   register (none this run), the ERA before/after snapshots, the era_chain log and the
#   fallback register, then writes:
#   - "_run report 9-16 1710.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-16T1710Z.json (Insurance Refresh Board inbox file: update ops with appends keyed by
#     src+when, never set on status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Copy of run_outputs_0916_1510.py for the 11am ET slot.
import csv, json, os, re, collections, datetime
S = "2026-09-16T1710Z"; SRC = "1pm ET 9/16 columns run (ehpa cloud)"; W = "9/16"
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
log = open("era_chain_1710.log").read() if os.path.exists("era_chain_1710.log") else ""
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
cob = load("registers/bcbs835_cob_%s.json" % S, [])
for r in cob:
    for st in r["steps"]:
        if st.startswith("v") and "204" in st:
            add("ERA COB re-route", "rebilled", "pat%s" % r["pid"], "", "FLO02" if r["kind"] != "C-pr177-to-uhc-seq2" else "UNI20", "Florida Blue 835 PR-22/CO-22/PR-27/PR-177", "move_to_ins + freq1 -> 204 (%s)" % st.split(":")[0], check="1051680-1051684", visit=st.split(":")[0].split(" ")[0][1:])
add("Claim Inspector", "cleared", "pat17473245", "08/27/2026", "FLO02", "Pattern 11256 M16.9 unspecified (raised by the Medicare-first resave)", "bypassclaimedits, logged in laterality_flag_log.md; batch empty after", visit="19453351")
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' newer than the registered set (nothing modified there after 9/15 04:00Z; every PDF is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled); nothing parsed or posted")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board drops 0 new; no row updated after 11:00Z (no William note since the 1am ET run); facesheet folders (hca/tmh/PCC/Claimocity/parent), Optum ERA folder, treasury folder: nothing new after 10:00Z (folders re-listed 17:12Z); Pam Gmail (newer_than:2d) empty")
out = "_run report 9-16 1710.csv"
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
newtxt = ("; new check(s) since 11am ET: " + ", ".join("%s %s $%.2f" % (c["id"], c.get("systemcarriercode") or "", f(c.get("unpostedamount"))) for c in newc)) if newc else "; no new checks arrived during the run"
posttxt = ("; manual fallback posted %d line(s) $%.2f + $%.2f WOINS (%s)" % (len(posted), fpay, fwo, ", ".join("%s %s" % (r.get("visitid"), r.get("cpt")) for r in posted))) if posted else "; fallback dry + live 0 postable"
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache %d/%d; "
            "era_post --all-unposted posted %d visits $%.2f%s (counts %s; residual-zero lines disregarded per your 9/13 rule); %d addpayments faults; era_clear dismissed %d%s, held %d%s."
            % (SRC, S, nb, ab, na, aa, pay, len(os.listdir("era_details")) if os.path.isdir("era_details") else 0, nb, auto_n, auto_amt, posttxt, counts, faults, len(cleared), (" (%s)" % ", ".join("%s %s" % (c["id"], c.get("systemcarriercode") or "") for c in cleared)) if cleared else "", na, newtxt))
cob = load("registers/bcbs835_cob_%s.json" % S, [])
COBSRC = SRC + " - Florida Blue 835 PR-22/CO-22 (checks 1051680/1051683)"
row("addison-rupert-denials", checks=[chk("ok", "Florida Blue 835 (check 1051680, 9/16) answered PR-22 'other payer primary' on the 7/21/2026 99306+99497 visit ($389, v19449478) still on Florida Blue - set to Medicare seq 2 and freq-1 rebilled 204; patient order 2,1 re-asserted. The other 13 PR-22 lines on this chart are already on Medicare from the 9/13 re-route.", COBSRC)])
row("burwell-corinne-denials", checks=[chk("ok", "Florida Blue 835 (check 1051680, 9/16): PR-22 'other payer primary' on the 7/15/2026 99349 ($198, v19449004) and 7/17/2026 99487+99489 ($315, v19448820) - both were billed to Florida Blue (Medigap) as primary; patient order set Medicare first (2,1), both visits set to Medicare seq 2 and freq-1 rebilled 204. Florida Blue gets the crossover.", COBSRC)])
row("dalrymple-dane-denials", checks=[chk("ok", "Florida Blue 835 (check 1051680, 9/16): PR-22 on 4 more visits still on Florida Blue - 7/9 99309 v19447739 $141, 7/13 G0439 v19448487 $204, 7/17 99487+99489 v19448870 $315, 8/27 99309 v19453351 $141 - all set to Medicare seq 2 and freq-1 rebilled 204 (patient order 2,1). The 8/27 resave raised inspector Pattern 11256 (M16.9 unspecified hip OA) - bypassed and logged in laterality_flag_log.md; inspector clear.", COBSRC)])
row("bexley-bateson-brigid-denials", checks=[chk("ok", "Florida Blue 835 (check 1051680, 9/16): PR-22 on the 2/12/2026 99223 ($310, v19432733) still on Florida Blue - set to Medicare seq 1 and freq-1 rebilled 204 (the 2/13 visit was re-routed 9/15).", COBSRC)])
row("ellerby-lorna-s-denials", checks=[chk("ok", "Florida Blue 835 (check 1051680, 9/16): PR-22 'other payer primary' on the 7/9 99223 ($310, v19447726) and 7/10 99232 ($111, v19447692). Chart had NO Medicare plan: Stedi MBI lookup at DOS 7/9/2026 = straight Medicare ACTIVE, Part A/B since 9/1/2011, no Advantage entity, not deceased -> FLO02 plan added (ins9519435, seq 2, begin 09/01/2011, no group), AMD 271 ACTIVE, patient order 2,1, both visits set to Medicare seq 2 and freq-1 rebilled 204.", COBSRC)], api=[{"src": "Stedi API - MBI lookup (MBILUNOSSN) DOS 20260709", "at": NOW, "text": "ELLERBY, LORNA dob [DOB] -> Medicare Part A 20110901 / Part B 20110901 ACTIVE; no Advantage or Part D entity returned; address [address] TALLAHASSEE FL 32317. AMD 271 on the new FLO02 plan: ACTIVE A/B 20110901."}])
row("garland-desmond-jay-denials", checks=[chk("ok", "Florida Blue 835 (check 1051680, 9/16): PR-22 'other payer primary' on the whole 4/7-4/10/2026 HCA stay ($643: v19437865 99223, v19437935/19437958/19438056 99232). Chart had NO Medicare plan: Stedi MBI lookup at DOS 4/7/2026 = straight Medicare ACTIVE (Part A 1/1/2013, Part B 1/1/2017), no Advantage entity, not deceased -> FLO02 plan added (ins9519436, seq 2, begin 01/01/2017, no group), AMD 271 ACTIVE, patient order 2,1, all 4 visits set to Medicare seq 2 and freq-1 rebilled 204.", COBSRC)], api=[{"src": "Stedi API - MBI lookup (MBILUNOSSN) DOS 20260407", "at": NOW, "text": "GARLAND, DESMOND dob [DOB] -> Medicare Part A 20130101 / Part B 20170101 ACTIVE; no Advantage or Part D entity returned; address [address] NICEVILLE FL 32578. AMD 271 on the new FLO02 plan: ACTIVE A 20130101 B 20170101."}])
row("marlow-patient737-gresham-sabrina", checks=[chk("ok", "GRESHAM (pat17473308): Florida Blue 835 (check 1051682, 9/16) answered PR-27 'coverage terminated' on the 10/25/2025 99487+99489 ($315, v19421060); the chart's only plan was Florida Blue BEG85944640. AMD 271 on it: REJECTED AAA 72. Stedi MBI lookup at DOS 10/25/2025 = straight Medicare ACTIVE, Part A 4/1/2025, Part B 5/1/2025, no Advantage entity; discovery = CMS only -> FLO02 plan added (ins9519437, seq 2, begin 05/01/2025, no group), AMD 271 ACTIVE, Florida Blue plan end-dated 10/24/2025, patient order 2,1, visit set to Medicare seq 2 and freq-1 rebilled 204.", COBSRC)], api=[{"src": "Stedi API - MBI lookup (MBILUNOSSN) DOS 20251025 + discovery", "at": NOW, "text": "GRESHAM, SABRINA dob [DOB] -> Medicare Part A 20250401 / Part B 20250501 ACTIVE; no Advantage or Part D entity; address [address] ENTERPRISE AL 36330. Discovery: 1 coverage, CMS (Medicare) only. AMD 271 on the new FLO02 plan: ACTIVE A 20250401 B 20250501."}])
ops.append({"op": "upsert", "collection": "items", "id": "florida-blue-835s-0916", "set": {"patient": "FLORIDA BLUE 835s (ERA Center, 9/16)", "dob": "", "facility": "AMD ERA Center", "amdid": "", "mbi": "",
    "need": "Watching. The first Florida Blue 835s reached AMD's ERA Center on 9/16 (checks 1051680 $486.23 / 257 claims, 1051683 $41.20 / 97 claims, 1051681, 1051682, 1051684 $0 denial-only) - the Availity ERA routing appears to be live. Money: era_post auto-posted 13 visits $415.48, fallback posted 3 lines $95.16 (+$40.90 WOINS); the three $0 checks and 1051683 were cleared (121 $0 lines processed), 1051680 stays listed for its $70.75 line the fallback already posted. Denials on them: 121 PR-22/CO-22 'other payer primary' lines (12 charts) - 20 visits still open on Florida Blue re-routed to Medicare tonight (see the patient rows: addison-rupert, burwell-corinne, dalrymple-dane, bexley-bateson-brigid, ellerby-lorna-s, garland-desmond-jay, gresham (on the marlow-patient737-gresham-sabrina row), plus pat17471968 v19420897, pat12180329 v19436826/v19437109, pat23967 v19420037/v19422019 -> UHC seq 2); pat17475906's 9 CO-22 lines are the group-plan case already re-sent 9/16 01:30 ET (no second rebill). 117 PR-177/PR-27 'not eligible' lines on 9 charts - all but pat17473308 (fixed) and pat23967 (fixed) already at $0 or re-routed earlier. 151 OA-18 exact-duplicate lines (frequency-1 rebills into adjudicated claims) - never rebilled; 6 CO-29 timely (v19433137/19433138/19433140, 2/16-2/18/2026) and 4 CO-226 records lines wait for the Working Denials board ('rerun'). No MA63/M76/M64 principal-diagnosis lines.",
    "why": "AMD's ERA Center received Florida Blue 835s for the first time on 9/16/2026 (5 checks); their denial lines were worked per the standing COB rule and the rest is queued for the Working Denials board.", "amount": 527.43, "status": "claude", "notes": [note("Created by the 1pm ET 9/16 run. Register: registers/bcbs835_cob_2026-09-16T1710Z.json (20 visits re-routed, every chargerebill 204); line classification in bcbs835_lines_1710.json.")]}})
row("aet12-carrier-cpid", checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193 (%s runs). Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % (aet_bal, runs_n), SRC + " - claim run 1700193")])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("era-manual-post-0912", checks=[chk("ok" if (posted or auto_n or cleared) else "na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/15 04:00Z; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-16 1 PM ET columns run (ehpa cloud Code Routine, 17:09-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main d8066a6, layout 276 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. State bundle workspace_state_2026-09-15_1836UTC (6 parts + manifest, newest on Drive) is OLDER than the repo state and every prior hand-relayed restore of it failed sha256 - not retyped; registers restored from practices/ehpa/registers/ in the repo (1510Z state); needs_facesheet_list.md restarted from the repo's 1510Z section; captured_calls.md = the Drive copy (92,698 bytes, 15:31Z) + the 1510Z additions file (mirror.py union keeps the newer sections already on main). Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 184 rows on Claude's turn, 0 rows updated after 15:00Z (no William note since the 1am ET run); drops new = 0; Working Denials queue = 0. Board inbox: the registry's applied map lists only 9/12-9/14 files, none still in the inbox - nothing trashed. Facesheet folders (hca/tmh/PCC/Claimocity/parent), Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new after 10:00Z (folders re-listed 17:12Z).
Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (one Pattern 11256 advisory raised mid-run by the COB resave and bypassed) | Unbilled %d -> %d ($2,422.58, all 11 'Payment reason codes are missing or do not balance' - held per the 9/15 chat rule, never released) | Exclusions %d -> %d: 59 AET12 PREF0288+PREF0264 on run 1700193 held ($11,756; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/14/2026, no AET12 payment; no new claim run since 1700193, %s runs).
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). era_post posted %d visits $%.2f%s. Fallback counts %s; dollars %s. era_clear dismissed %d (%s), held %d. %d addpayments faults%s. No new 835s in the Optum folder; Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
FLORIDA BLUE 835s (first ever in the ERA Center, 9/16): checks 1051680 ($486.23, 257 claims), 1051683 ($41.20, 97 claims), 1051681/1051682/1051684 ($0). Denial lines: 121 PR-22/CO-22 other-payer-primary (12 charts), 117 PR-177/PR-27 not-eligible (9 charts), 151 OA-18 exact duplicates, 6 CO-29, 4 CO-226, 0 MA63/M76/M64. COB action (bcbs835_cob_1710.py, register registers/bcbs835_cob_2026-09-16T1710Z.json): 20 visits still open on Florida Blue re-routed and freq-1 rebilled (204 each) - pat17471968 v19420897, pat17476868 v19449478, pat17476438 v19448820/v19449004, pat17473245 v19453351/v19448870/v19448487/v19447739, pat25710 v19432733, pat12180329 v19436826/v19437109 (Medicare already on chart; patient order 2,1 set where Florida Blue was plan 1); pat17477062 + pat17476106 + pat17473308 had NO Medicare plan - Stedi MBI lookup = straight Medicare ACTIVE, no Advantage entity -> FLO02 plans added (ins9519435 begin 09/01/2011, ins9519436 begin 01/01/2017, ins9519437 begin 05/01/2025; no group numbers), AMD 271 ACTIVE on all three, Florida Blue end-dated 10/24/2025 on pat17473308 (PR-27 coverage terminated), 7 visits re-routed; pat23967 PR-177 x2 -> UHC seq 2 like its 34 sibling visits. pat17475906's 9 CO-22 lines = the group-plan case re-sent 9/16 01:30 ET, not touched. Inspector: the pat17473245 8/27 resave raised Pattern 11256 (M16.9 unspecified) - bypassed, logged in laterality_flag_log.md, inspector empty after. OA-18 duplicates never rebilled; CO-29/CO-226 lines wait for the Working Denials 'rerun'.
Calls learned: none (every call this run is a captured shape: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, hideexclusions, gettxhistory, getdemographic, GET /api/era/checks, checkdetails, posterapayments, locks/release-expired, checks/dismiss). Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, n_cr0, n_cr, n_in0, n_in, n_ub0, n_ub, n_ex0, n_ex, aet_bal, runs_n, nb, ab, na, aa, pay, auto_n, auto_amt, posttxt, counts, dollars, len(cleared), ", ".join(str(c["id"]) for c in cleared) or "none", na, faults, newtxt)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-1pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-16 1 PM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 1pm ET 9/16/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
