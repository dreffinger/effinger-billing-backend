# PLAIN ENGLISH (run outputs for the 5am ET 9/17/2026 slot - ehpa cloud run 2026-09-17T0910Z)
# Decides: nothing. Reads this run's column scan (scan_0912/summary_before.json), the ERA before/after snapshots, the
#   manual-post register, the AET12 verify register and the write-off reversal register, then writes:
#   - "_run report 9-17 0910.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T0910Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; no set on
#     status/need of an existing row)
#   - denials_updates_2026-09-17T0910Z.json (one Claude note: the 14 FLO02 $0-denial visits of check 349961258 wait for 'rerun')
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board databases. Special to this run: two new Florida Blue ERAs - check 349961258 ($0, 33 denial
#   lines) and check 819803392 ($13,050.74): 152 visits auto-posted, 1 refused line manual-posted, 15 lines on visits our
#   9/7-9/10 $0-denial write-offs had zeroed reversed (write-offs voided, payments posted), 3 residual lines disregarded.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-17T0910Z"; SRC = "5am ET 9/17 columns run (ehpa cloud)"; W = "9/17"
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
reg = [r for r in load("registers/era_manual_register.json", []) if r.get("when") == S]
posted = [r for r in reg if r["outcome"] == "posted"]
already = [r for r in reg if r["outcome"] == "already-posted"]
rev = [r for r in load("era_clear_reversal_20260917.json", []) if str(r.get("checkid")) == "1051693"]
rev_ids = {str(r["visitid"]) for r in rev}
resid = [r for r in reg if r["outcome"].startswith("residual") and str(r["visitid"]) not in rev_ids]
auto_amt = round(sum(f(r["era_paid"]) for r in already), 2)
rev_amt = round(sum(f(r["era_pay"]) for r in rev), 2); rev_wo = round(sum(abs(f(w[3])) for r in rev for w in r["writeoffs"]), 2)
resid_amt = round(sum(f(r["era_paid"]) for r in resid), 2)
man_amt = round(sum(f(r["era_paid"]) for r in posted), 2)
d692 = load("era_details/1051692.json", {}).get("eracheckdetails", [])
den_visits = sorted({str(c["visitid"]) for c in d692}); den_lines = sum(len(c["charges"]) for c in d692)
den_adj = round(sum(f(ch["adjustmentamount"]) for c in d692 for ch in c["charges"]), 2)
den_codes = collections.Counter(x["reasoncode"] for c in d692 for ch in c["charges"] for x in (ch.get("carc") or []))

rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty)")
add("Claim Inspector", "clear", action="0 batches / 0 visits before and after (getclaiminspectorbatches empty)")
add("Unbilled", "clear", action="0 rows before and after (getclaimunbillablecharges totalcount 0)")
add("Exclusions", "held", carrier="AET12", err="CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM (claim run 1700202, 2026-09-16 22:16 AMD clock, 59 exclusions)",
    action="Same 59 AET12 rows as the 1am and 3am runs; no claim run newer than 1700202 (%s runs listed). gettxhistory on all 15 charts (%s): 68 AET12 charges billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment (Medicare paid $%.2f on the same visits). Held - not rebilled, not completed; the carrier record (IDs dialog / Claim Fields / Box 33B REF*EI / AMD 837 case) is still William's fix." % (runs_n, chart_txt, aet_bal, aet_paid), amt="%.2f" % aet_bal)
for r in ex:
    add("Exclusions", "remaining", patient="pat%s" % r["patientid"], carrier="AET12", err="; ".join(sorted(set(r["errs"]))), action="held on claim run 1700202 (carrier-master fix pending)", visit=r["visit"], amt="%.2f" % r["fee"])
add("ERA", "cleared", carrier="FLO02", check="1051693", amt="13050.74", action="check 819803392 (check date 9/18) $13,050.74: era_post --all-unposted posted 152 visits $%.2f (AMD's fault -2147217287 refused 1 line); fallback manual-posted %d line $%.2f (visit 19451570 99497 08/13/2026, pay 52.33 + WOINS 67.32 on a $133 balance); %d lines $%.2f on visits our 9/7-9/10 $0-denial write-offs had zeroed: write-offs voided ($%.2f) and the check posted for those visits (payments + contractual write-offs, coinsurance left on insurance for the secondary); %d residual lines $%.2f disregarded (visits already adjudicated by FLO02 REPOST-GARCIA + HUM01); era_clear dismissed the check; GET /api/era/checks empty after." % (auto_amt, len(posted), man_amt, len(rev), rev_amt, rev_wo, len(resid), resid_amt))
for r in posted: add("ERA", "manual-posted", patient="pat%s" % r["pid"], dos=r["dos"], carrier=r["carrier"], check=r["checkid"], visit=str(r["visitid"]), amt="%.2f" % f(r["era_paid"]), action="manual_post %s pay %.2f (fallback, refused by the Post button)" % (r["cpt"], f(r["era_paid"])))
for r in rev: add("ERA", "reversal-posted", patient="pat%s" % r["patientid"], dos=r["dos"], carrier="FLO02", check="1051693", visit=str(r["visitid"]), amt="%.2f" % f(r["era_pay"]), action="write-off %s voided, payment posted from check 819803392" % ", ".join("%s %s (%s)" % (w[2], w[3], w[4]) for w in r["writeoffs"]))
for r in resid: add("ERA", "residual-disregarded", patient="pat%s" % r["pid"], dos=r["dos"], carrier=r["carrier"], check=r["checkid"], visit=str(r["visitid"]), amt="%.2f" % f(r["era_paid"]), action=r.get("why", "")[:160])
add("ERA", "cleared", carrier="FLO02", check="1051692", amt="0.00", action="check 349961258 (check date 9/18) $0.00: %d $0 denial lines on %d visits, CO adjustments $%.2f (%s) - no MA63/M76/M64 principal-diagnosis remarks; era_clear zero-posted / dismissed it; the denial lines go to the Working Denials board ('rerun' loads them), nothing written off by this run." % (den_lines, len(den_visits), den_adj, ", ".join("%s x%d" % kv for kv in den_codes.most_common())))
for c in d692:
    for ch in c["charges"]:
        add("ERA", "denial-only", patient="pat%s" % c["patientid"], dos=ch["dos"][:10], carrier="FLO02", check="1051692", visit=str(c["visitid"]), amt="%.2f" % f(ch["adjustmentamount"]), err="; ".join("%s %s" % (x["reasoncode"], x["reasonamt"]) for x in (ch.get("carc") or [])) + " | " + ",".join(x["remarkcode"] for x in (ch.get("rarc") or []) if x["remarkcode"] != "#AM"), action="$0 line %s - Working Denials board (rerun), insurance balance %s" % (ch["chargecode"], c["insurancebalance"]))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' newer than the registered set (Drive-wide search modifiedTime > 07:15Z 9/17 returned only this routine's own files); nothing parsed or posted")
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board 0 rows on William's turn, 0 rows updated after 07:00Z 9/17, drops 0 new; facesheet folders, Optum ERA folder, treasury folder: nothing new; Pam Gmail (newer_than:2d) empty.")
out = "_run report 9-17 0910.csv"
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
    checks=[chk("no", "5am ET 9/17: unchanged - the 59 AET12 exclusions of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264) are still on the list, no newer claim run (%s listed). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed." % (runs_n, aet_bal), SRC + " - claim run 1700202")])
row("era-manual-post-0912", checks=[chk("ok", "ERA step 5 (%s, run %s): 2 new FLO02 checks / $13,050.74 unposted before -> 0 / $0.00 after. Check 819803392: 152 visits $%.2f auto-posted, 1 refused line manual-posted ($%.2f), %d lines $%.2f reversed-and-posted (our 9/7-9/10 $0-denial write-offs voided, $%.2f), %d residual lines $%.2f disregarded, dismissed. Check 349961258 ($0, %d denial lines, CO adjustments $%.2f) dismissed - denial lines wait for the Working Denials 'rerun'." % (SRC, S, auto_amt, man_amt, len(rev), rev_amt, rev_wo, len(resid), resid_amt, den_lines, den_adj), SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set (Drive-wide modifiedTime > 07:15Z 9/17 search) - nothing to parse, post or reconcile; board drops, Working Denials queue and Pam Gmail: nothing new.", SRC + " - ERA step 5(g)")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")
dops = [{"op": "upsert", "collection": "commands", "id": "cmd-claude-%s" % S, "set": {"command": "note", "by": "Claude", "target": "board", "status": "done", "note": "", "at": NOW,
        "result": "5am ET 9/17 run: Florida Blue ERA check 349961258 (ERA Center id 1051692, $0.00) carried %d $0 denial lines on %d visits - CO adjustments $%.2f (%s); RARCs MA01/N211/MA15/M86/N666, no principal-diagnosis remark. era_clear dismissed the check after registering the lines (nothing written off, nothing rebilled). Say 'rerun' to load these visits onto this board (visits: %s)." % (den_lines, len(den_visits), den_adj, ", ".join("%s x%d" % kv for kv in den_codes.most_common()), ", ".join(den_visits))}}]
json.dump({"schema": "wd-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": dops}, open("denials_updates_%s.json" % S, "w"), indent=1)
print("wrote denials_updates_%s.json" % S, len(dops), "ops")

sec = """
## 2026-09-17 5 AM ET columns run (ehpa cloud Code Routine, 09:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 40f7d26, layout 297 helpers), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, not unpacked); registers restored from practices/ehpa/registers/ in the repo (0710Z state); needs_facesheet_list.md = the Drive 0550UTC copy + the repo's 13 run sections; captured_calls.md = GitHub main docs/captured_calls.md (already carries the 0510Z and 0710Z additions); pseudonyms.json (142 names) from the workspace mirror. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board - 0 rows on William's turn, 0 rows updated after 07:00Z 9/17, drops new = 0; Working Denials queue = 0. Board inbox: the registries' applied maps list only 9/12-9/14 files, none still in the inbox - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled 0 -> 0 | Exclusions 59 -> 59 HELD: the same 59 AET12 claims of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264), no newer claim run (%s listed). gettxhistory on the 15 charts: 68 AET12 charges billdate 09/16/2026, $%.2f insurance balance open, none at $0, no AET12 payment (Medicare paid $%.2f on those visits). Not rebilled, not completed - carrier-record fix still William's. Nothing released, rebilled or written off in the four columns by this run.
ERA step 5: 2 checks / $13,050.74 unposted before (both FLO02, check date 9/18, new since the 3am run) -> 0 / $0.00 after. Check 819803392 (id 1051693, $13,050.74): era_post --all-unposted posted 152 visits $%.2f (fault -2147217287 refused 1 line); fallback manual-posted 1 line $%.2f (visit 19451570 99497 08/13/2026, pay 52.33 + WOINS 67.32, balance 133.00); %d lines $%.2f were on visits our 9/7-9/10 $0-denial posts had written off in full (WOINS, no payment ever) - the documented write-off reversal pipeline ran (wo_reversal_0917_0910.py: void_tx.void_writeoff x%d = $%.2f voided, then era_post.post_check with FORCE_VISITS -> 15 visits $%.2f posted, payment + contractual write-off each, ~20%% coinsurance left on insurance for the secondary); %d residual lines $%.2f disregarded (visits already adjudicated by FLO02 REPOST-GARCIA + HUM01); era_clear dismissed the check. Check 349961258 (id 1051692, $0.00): %d $0 denial lines on %d visits (CO adjustments $%.2f: %s; RARCs MA01/N211/MA15/M86/N666, no MA63/M76/M64) - era_clear registered and dismissed it; the denial lines wait for the Working Denials 'rerun' (note left in the denials inbox file). 0 addpayments faults. No new 835s in the Optum folder. Availity 5(g): nothing new.
Calls learned: no new AMD call shapes (void, posterapayments with FORCE_VISITS, dismiss, gettxhistory - all captured). Helper fix: wo_reversal_post.py now sets era_post.FORCE_VISITS before post_check (the registry's 9/10 lesson was never applied to the helper itself - it would have voided the write-offs and posted $0). Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, runs_n, aet_bal, aet_paid, auto_amt, man_amt, len(rev), rev_amt, len(rev), rev_wo, rev_amt, len(resid), resid_amt, den_lines, len(den_visits), den_adj, ", ".join("%s x%d" % kv for kv in den_codes.most_common()), MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 5 AM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("captured_calls_additions_%s-5amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 5 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 5am ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
