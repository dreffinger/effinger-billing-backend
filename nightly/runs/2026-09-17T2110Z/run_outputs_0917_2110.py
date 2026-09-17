# PLAIN ENGLISH (run outputs for the 5pm ET 9/17/2026 slot - ehpa cloud run 2026-09-17T2110Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA before/after
#   snapshots and the AET12 verify register, then writes:
#   - "_run report 9-17 2110.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T2110Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; no set on status/need)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text (--final)
# Never touches: AMD, the board databases.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-17T2110Z"; SRC = "5pm ET 9/17 columns run (ehpa cloud)"; W = "9/17"
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
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ex = load("registers/aet12_excl_1700202_2026-09-17T0710Z.json", [])
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
era_txt = open("era_summary.txt").read().strip() if os.path.exists("era_summary.txt") else "ERA chain not run"
insp_before = sum(len(v) for v in before.get("inspector", {}).values()); insp_after = sum(len(v) for v in after.get("inspector", {}).values())
bychart = collections.Counter(r["patientid"] for r in ex)
chart_txt = ", ".join("pat%s x%d" % (p, n) for p, n in bychart.most_common())
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty; overview chargereviewcount 0)")
add("Claim Inspector", "clear", action="%d visits before, %d after (getclaiminspectorbatches empty; overview claiminspectorcount 0) - nothing to fix" % (insp_before, insp_after))
add("Unbilled", "clear", action="0 rows before and after (getclaimunbillablecharges totalcount 0)")
add("Exclusions", "held", carrier="AET12", err="CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM (claim run 1700202, 59 exclusions)",
    action="Same 59 AET12 rows as every run since the 1am 9/17 slot; no claim run newer than 1700202 (%s runs listed; the 9/17 evening claim run has not posted yet at 21:15 UTC). gettxhistory on all 15 charts (%s): 68 AET12 charges billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment (Medicare paid $%.2f on the same visits). Held - not rebilled, not completed; the carrier record (IDs dialog / Claim Fields / Box 33B REF*EI / AMD 837 case) is still William's fix." % (runs_n, chart_txt, aet_bal, aet_paid), amt="%.2f" % aet_bal)
for r in ex:
    add("Exclusions", "remaining", patient="pat%s" % r["patientid"], carrier="AET12", err="; ".join(sorted(set(r["errs"]))), action="held on claim run 1700202 (carrier-master fix pending)", visit=r["visit"], amt="%.2f" % r["fee"])
add("ERA", "clear" if na == 0 else "held", action="GET /api/era/checks: %d unposted checks / $%.2f before -> %d / $%.2f after. %s" % (nb, ab, na, aa, era_txt))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads', 'treasury payments', 'chc raw 835 downloads' (empty) or the four facesheet folders modified after 09:00Z 9/17; registers/availity_register.json unchanged; nothing parsed, posted or reconciled")
add("Pam admit emails", "none new", action="Gmail sweep from:pgarnp24work@gmail.com has:attachment newer_than:2d = the same 10 admit emails of 18:40-18:50Z 9/17 that the 3pm ET run read (board row pam-admits-2026-09-17); nothing newer - not re-read")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board 184 rows on Claude's turn, no row updated after 9/16 06:00Z (no new William note), drops 0 new; board inbox: both registries' applied maps list only 9/12-9/15 files (board last synced 9/16 03:46Z), 37 run files still waiting in the inbox - nothing trashed.")
out = "_run report 9-17 2110.csv"
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
    checks=[chk("no", "5pm ET 9/17: unchanged - the 59 AET12 exclusions of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264) are still on the list, no newer claim run (%s listed). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed." % (runs_n, aet_bal), SRC + " - claim run 1700202")])
row("era-manual-post-0912", checks=[chk("na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. %s" % (SRC, S, nb, ab, na, aa, era_txt[:400]), SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 09:00Z 9/17; 'chc raw 835 downloads' empty) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the ten of 18:50Z 9/17 already read.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

sec = """
## 2026-09-17 5 PM ET columns run (ehpa cloud Code Routine, 21:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 218b9f7, session branch claude/pensive-einstein-6jho3h, layout 318 helpers), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, not unpacked); registers restored from practices/ehpa/registers/ in the repo (1910Z state); needs_facesheet_list.md rebuilt from the repo's 18 run sections; captured_calls.md = GitHub main docs/captured_calls.md (the Drive copy is a 92,698-byte stub); pseudonyms.json (142 names) from the workspace mirror. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Skills loaded: advancedmd-api-reference, billing-easy-task-charge-review-and-claim-inspector-columns, billing-hard-task-clearing-unbilled-column.
Boards: Insurance Refresh Board - 184 rows on Claude's turn, no row updated after 9/16 06:00Z (no new William note), drops new = 0; Working Denials queue = 0. Board inbox: both registries' applied maps list only 9/12-9/15 files (board last synced 9/16 03:46Z), 37 run files waiting - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder, 'chc raw 835 downloads' (new 9/17 04:04Z, empty): nothing modified after 09:00Z 9/17. Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 the 3pm ET run read (row pam-admits-2026-09-17) - nothing newer.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled 0 -> 0 | Exclusions 59 -> 59 HELD: the same 59 AET12 claims of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264), no newer claim run (%s listed; the 9/17 evening run had not posted by 21:15 UTC). gettxhistory on the 15 charts: 68 AET12 charges billdate 09/16/2026, $%.2f insurance balance open, none at $0, no AET12 payment (Medicare paid $%.2f on those visits). Not rebilled, not completed - carrier-record fix still William's. Nothing released, rebilled or written off in the four columns by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after. %s Availity 5(g): nothing new. Working Denials: nothing queued, no denials file written.
Calls learned: none (getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimexclusionclaimruns/charges, gettxhistory, GET /api/era/checks, POST /api/era/locks/release-expired - all captured). Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, runs_n, aet_bal, aet_paid, nb, ab, na, aa, era_txt, MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 5 PM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("needs_facesheet_list_section.md", "w").write(sec.lstrip("\n"))
    open("captured_calls_additions_%s-5pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 5 PM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 5pm ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
