# PLAIN ENGLISH (run outputs for the 3am ET 9/17/2026 slot - ehpa cloud run 2026-09-17T0710Z)
# Decides: nothing. Reads this run's column scan (scan_0912/summary_before.json), the ERA before/after snapshots, the
#   AET12 verify register for claim run 1700202, then writes:
#   - "_run report 9-17 0710.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T0710Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; no set on
#     status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Special to this run: a NEW claim run 1700202 (9/16 22:16 AMD clock, 60 claims)
#   rejected the same 59 AET12 claims again (PREF0288 TIN + PREF0264) after William completed the 1700201 rows and re-sent them.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-17T0710Z"; SRC = "3am ET 9/17 columns run (ehpa cloud)"; W = "9/17"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ex = load("registers/aet12_excl_1700202_%s.json" % S, [])
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
n_charts = len({c["patientid"] for c in ex}); runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
bychart = collections.Counter(r["patientid"] for r in ex)
chart_txt = ", ".join("pat%s x%d" % (p, n) for p, n in bychart.most_common())
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty)")
add("Claim Inspector", "clear", action="0 batches / 0 visits before and after (getclaiminspectorbatches empty)")
add("Unbilled", "clear", action="0 rows before and after (getclaimunbillablecharges totalcount 0)")
add("Exclusions", "held", carrier="AET12", err="CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM (claim run 1700202, 2026-09-16 22:16 AMD clock, 60 claims sent $11,867, 59 exclusions)",
    action="NEW claim run 1700202 rejected the same 59 AET12 claims again ($11,756 fees, 15 charts: %s). gettxhistory on all 15 charts: 68 AET12 charges billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment (Medicare paid $%.2f on the same visits). Held open - not rebilled, not completed; the carrier record (IDs dialog / Claim Fields / Box 33B REF*EI / AMD 837 case) is still the only fix. %s runs listed." % (chart_txt, aet_bal, aet_paid, runs_n), amt="%.2f" % aet_bal)
for r in ex:
    add("Exclusions", "remaining", patient="pat%s" % r["patientid"], carrier="AET12", err="; ".join(sorted(set(r["errs"]))), action="held on claim run 1700202 (carrier-master fix pending)", visit=r["visit"], amt="%.2f" % r["fee"])
add("ERA", "clear", action="GET /api/era/checks = [] before and after (%d / $%.2f -> %d / $%.2f); locks release-expired sent; era_post --all-unposted posted 0 visits $0.00; fallback dry+live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s in 'bht Optum era downloads'; era_details cache empty (nothing to cache)" % (nb, ab, na, aa))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' (newest 9/15 03:30Z) or 'treasury payments' (newest 9/15 02:31Z) since the registered set; every PDF is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled - nothing parsed or posted")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board drops 0 new, 0 rows updated after 04:00Z 9/17 (184 on Claude's turn, all watch/hold); facesheet folders, Optum ERA folder, treasury folder: nothing new; Pam Gmail (newer_than:2d) empty.")
out = "_run report 9-17 0710.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
ops = []
def row(id, checks=None, notes=None, op="update", set_=None):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if set_: o["set"] = set_
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    ops.append(o)
row("aet12-carrier-cpid",
    checks=[chk("no", "VERDICT on the 9/16 re-send: NOT FIXED. A new claim run 1700202 (2026-09-16 22:16 AMD clock, MCKGRP, 60 claims $11,867) rejected the same 59 AET12 claims again - CH FH PREF0288 INVALID PAYER ID/CPID 814723941 (TIN) + PREF0264 MISS/INVD PAYER DOC CONTRL NUM - after the 1700201 rows were completed and re-sent outside the routine. 68 AET12 charges on the 15 charts re-read via gettxhistory: billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment. Held on the exclusion list (59 rows), not rebilled, not completed - whatever was changed on the carrier record before the 9/16 re-send did not change the transmitted payer id either." % aet_bal, SRC + " - claim run 1700202")],
    notes=[{"who": "Claude", "at": NOW, "text": "3am ET 9/17 run: the 9/16 evening claim run (1700202) rejected all 59 AET12 claims with the TIN again (PREF0288 + PREF0264). Held, not re-sent. Still unchecked per the 9/14 analysis: the EDI/Other tab's Box 33B supplemental number (qualifier EI = Tax ID prints as the payer id REF*EI), the IDs dialog (red indicator) and Claim Fields; an AMD support case for the 837 of run 1700202 names the segment carrying 814723941 definitively. Say 'rebill' on this row once the record is changed."}])
row("era-manual-post-0912", checks=[chk("na", "ERA step 5 (%s, run %s): GET /api/era/checks = [] before and after (0 / $0.00); locks release-expired sent; era_post --all-unposted 0 posted; fallback dry+live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s in the Optum folder." % (SRC, S), SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (newest files 9/15 03:30Z / 02:31Z; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

sec = """
## 2026-09-17 3 AM ET columns run (ehpa cloud Code Routine, 07:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 080754e, layout 294 helpers), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, not unpacked); registers restored from practices/ehpa/registers/ in the repo (0510Z state); needs_facesheet_list.md = the Drive 0550UTC copy + the repo's 12 run sections; captured_calls.md = GitHub main docs/captured_calls.md (already carries the 0510Z additions); pseudonyms.json (142 names) from the workspace mirror. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 184 rows on Claude's turn (all watch/hold), 0 on William's turn, 0 rows updated after 04:00Z 9/17; drops new = 0; Working Denials queue = 0. Facesheet folders, Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled 0 -> 0 | Exclusions 59 -> 59 HELD: NEW claim run 1700202 (2026-09-16 22:16 AMD clock, 60 claims $11,867, 80 runs listed) rejected the same 59 AET12 claims again - PREF0288 INVALID PAYER ID/CPID 814723941 (TIN) + PREF0264 - after the 1700201 rows were completed and re-sent outside the routine (William, 9/16 evening). gettxhistory on the 15 charts: 68 AET12 charges billdate 09/16/2026, $%.2f insurance balance open, none at $0, no AET12 payment (Medicare paid $%.2f on those visits). Not rebilled, not completed - carrier-record fix still William's. Nothing released, rebilled or written off by this run.
ERA step 5: 0 checks / $0.00 before -> 0 / $0.00 after (GET /api/era/checks empty); locks release-expired sent; era_post posted 0 visits $0.00; fallback dry + live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s in the Optum folder; era_details cache empty. Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none (every call this run is a captured shape: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusionclaimruns, getclaimexclusioncharges, gettxhistory, GET /api/era/checks, POST /api/era/locks/release-expired). Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, aet_bal, aet_paid, MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 3 AM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("captured_calls_additions_%s-3amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 3 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 3am ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
