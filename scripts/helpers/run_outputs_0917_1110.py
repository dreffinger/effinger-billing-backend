# PLAIN ENGLISH (run outputs for the 7am ET 9/17/2026 slot - ehpa cloud run 2026-09-17T1110Z)
# Decides: nothing. Reads this run's column scan (scan_0912/summary_before.json), the ERA before/after snapshots and the
#   AET12 verify register, then writes:
#   - "_run report 9-17 1110.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T1110Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; no set on
#     status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# No denials_updates file: the Working Denials queue had nothing queued. Never touches: AMD, the board databases.
# This run: every column empty except the 59 AET12 exclusions (held), ERA Center empty (0 unposted checks), no new
#   Availity / 835 / facesheet / treasury files, no board work.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-17T1110Z"; SRC = "7am ET 9/17 columns run (ehpa cloud)"; W = "9/17"
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
ex = load("registers/aet12_excl_1700202_2026-09-17T0710Z.json", [])
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
bychart = collections.Counter(r["patientid"] for r in ex)
chart_txt = ", ".join("pat%s x%d" % (p, n) for p, n in bychart.most_common())
excl_rows = sum(len(v) for v in before.get("exclusions", {}).values()) if isinstance(before.get("exclusions"), dict) else "?"

rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty; overview chargereviewcount 0)")
add("Claim Inspector", "clear", action="0 batches / 0 visits before and after (getclaiminspectorbatches empty)")
add("Unbilled", "clear", action="0 rows before and after (getclaimunbillablecharges totalcount 0)")
add("Exclusions", "held", carrier="AET12", err="CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM (claim run 1700202, 59 exclusions)",
    action="Same 59 AET12 rows as the 1am, 3am and 5am runs; no claim run newer than 1700202 (%s runs listed). gettxhistory on all 15 charts (%s): 68 AET12 charges billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment (Medicare paid $%.2f on the same visits). Held - not rebilled, not completed; the carrier record (IDs dialog / Claim Fields / Box 33B REF*EI / AMD 837 case) is still William's fix." % (runs_n, chart_txt, aet_bal, aet_paid), amt="%.2f" % aet_bal)
for r in ex:
    add("Exclusions", "remaining", patient="pat%s" % r["patientid"], carrier="AET12", err="; ".join(sorted(set(r["errs"]))), action="held on claim run 1700202 (carrier-master fix pending)", visit=r["visit"], amt="%.2f" % r["fee"])
add("ERA", "clear", action="GET /api/era/checks: %d unposted checks / $%.2f before -> %d / $%.2f after; locks release-expired sent; no new 835s in 'bht Optum era downloads' (nothing to upload); era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults." % (nb, ab, na, aa))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads', 'treasury payments' or 'chc raw 835 downloads' newer than the registered set (Drive search modifiedTime > 04:00Z 9/15 on those folders returned nothing; Drive-wide modifiedTime > 09:00Z 9/17 returned only the 0910Z run's own files); registers/availity_register.json 98 files; nothing parsed, posted or reconciled")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board 184 rows on Claude's turn, 0 rows on William's turn, 0 rows updated after 07:00Z 9/17, drops 0 new; facesheet folders (hca/tmh/PCC/Claimocity), Optum ERA folder, treasury folder: nothing new since the 9/16 facesheets already worked; Pam Gmail (from:pgarnp24work newer_than:2d has:attachment) empty.")
out = "_run report 9-17 1110.csv"
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
    checks=[chk("no", "7am ET 9/17: unchanged - the 59 AET12 exclusions of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264) are still on the list, no newer claim run (%s listed). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed." % (runs_n, aet_bal), SRC + " - claim run 1700202")])
row("era-manual-post-0912", checks=[chk("na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after; no new 835s in the Optum folder; locks release-expired sent; era_post --all-unposted 0 checks; fallback 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new checks arrived." % (SRC, S, nb, ab, na, aa), SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 04:00Z 9/15 there; Drive-wide modifiedTime > 09:00Z 9/17 search returned only the 0910Z run's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

sec = """
## 2026-09-17 7 AM ET columns run (ehpa cloud Code Routine, 11:09-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 3dc5e92, session branch claude/pensive-einstein-2m2fbl, layout 301 helpers), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, downloaded but not unpacked); registers restored from practices/ehpa/registers/ in the repo (0910Z state); needs_facesheet_list.md rebuilt from the repo's 14 run sections; captured_calls.md = GitHub main docs/captured_calls.md (identical to the Drive copy the 0910Z run uploaded); pseudonyms.json (142 names) from the workspace mirror. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 184 rows on Claude's turn, 0 on William's turn, 0 rows updated after 07:00Z 9/17, drops new = 0; Working Denials queue = 0. Board inbox: the registries' applied maps list only 9/12-9/14 files, none still in the inbox - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder, chc raw 835 folder, Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled 0 -> 0 | Exclusions 59 -> 59 HELD: the same 59 AET12 claims of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264), no newer claim run (%s listed). gettxhistory on the 15 charts: 68 AET12 charges billdate 09/16/2026, $%.2f insurance balance open, none at $0, no AET12 payment (Medicare paid $%.2f on those visits). Not rebilled, not completed - carrier-record fix still William's. Nothing released, rebilled or written off in the four columns by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after (the ERA Center was already empty after the 5am run's two Florida Blue checks); no new 835s in the Optum folder; locks release-expired sent; era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 dismissed; 0 addpayments faults. Availity 5(g): nothing new (98 files registered).
Calls learned: none (getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, gettxhistory, GET /api/era/checks, POST /api/era/locks/release-expired - all captured). Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, runs_n, aet_bal, aet_paid, nb, ab, na, aa, MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 7 AM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("captured_calls_additions_%s-7amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 7 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 7am ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
