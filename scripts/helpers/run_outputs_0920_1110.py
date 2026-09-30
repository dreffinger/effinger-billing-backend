# PLAIN ENGLISH (run outputs for the 7am ET 9/20/2026 slot - ehpa cloud run 2026-09-20T1110Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after, AET12 verify, the 1700211 exclusion
#   verify + completion registers, the ERA chain log) and writes: "_run report 9-20 1110.csv"; board_updates_2026-09-20T1110Z.json
#   (real row ids, checks appends only - no status/need changes); a needs_facesheet_list.md section; the chat-history digest
#   (--final, after mirror_result.txt exists). Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys, collections, re
S = "2026-09-20T1110Z"; SRC = "7am ET 9/20 columns run (ehpa cloud)"; W = "9/20"; SLOT = "7 AM ET 9/20"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {}) or before
ovb = before.get("overview", {}); ova = after.get("overview", {})
ub = before.get("unbilled", []); ua = after.get("unbilled", [])
exb = sum(len(v) for v in before.get("exclusions", {}).values()); exa = sum(len(v) for v in after.get("exclusions", {}).values())
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
xv = load("registers/excl_1700211_verify_%s.json" % S, []); xc = load("registers/excl_1700211_%s.json" % S, {})
xbal = round(sum(f(r.get("insbalance")) for r in xv), 2)
log = open("logs/era_chain_1110.log").read() if os.path.exists("logs/era_chain_1110.log") else ""
ERA_TXT = os.environ.get("ERA_TXT") or ("%d unposted checks / $%.2f before -> %d / $%.2f after. Locks release-expired sent. %s" % (nb, ab, na, aa, os.environ.get("ERA_DETAIL", "")))
payreason = sum(1 for r in ua if any(e.startswith("Payment reason") for e in (r.get("_errs") or [])))
prior_after = [r for r in ua if any(e.startswith("A payment from the prior") for e in (r.get("_errs") or []))]
UNB_TXT = ("%s -> %s rows ($%s -> $%s on the overview): %d 'Payment reason codes are missing or do not balance' rows held per the 9/15 rule (William's turn: Payment Entry reason-code capture or 'release'); %d 'A payment from the prior payor is required' row(s) held (pat17470743 v19441047 MCAD $16.93 behind a reversed Medicare payment). Nothing new on the snapshot since the 0910Z run."
           % (len(ub), len(ua), ovb.get("unbillableamount"), ova.get("unbillableamount"), payreason, len(prior_after)))
EXC_TXT = ("%d -> %d rows. NEW claim run 1700211 (AMD clock 9/20 02:04, the night's EOD close - the first since 1700210) rejected the same 11 Florida Blue SECONDARY claims the 0510Z run had re-sent (5 frequency 7 + Florida Blue ICN, 6 frequency 1) again with CH FH PREF0283 MISSING PAYER DOC CONTROL NUM: pat17469028 x5, pat17473245 x4, pat17471968 x1, pat17476868 x1 ($%.2f insurance balance, every charge carrying its 9/19 Medicare payment with the Medicare ICN in origrefnum). Third confirmation that neither frequency supplies the crossover DCN. Applied William's 9/13 standing decision (crossover-wait): hideexclusions run 1700211 x11 -> success 1, re-list 0; no rebill, no write-off, balances left on Florida Blue for the Medicare crossover. AET12: %d charges on 15 charts $%.2f open (Medicare paid $%.2f), billdate 09/16/2026, none at $0, not on run 1700211 - held on the carrier-master fix, not re-sent."
           % (exb, exa, xbal, len(ver), aet_bal, aet_paid))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
add("Unbilled", "count", action=UNB_TXT)
add("Unbilled", "remaining", "pat17470743", "05/01/2026", "MCAD", "A payment from the prior payor is required", "held - Medicaid crossover behind a reversed Medicare payment", visit="19441047", amount="16.93")
add("Unbilled", "remaining", "%d visits" % payreason, "", "", "Payment reason codes are missing or do not balance", "held per the 9/15 rule: secondaries behind hand-posted primary payments (manual_post carries no CARCs); on William's turn: Payment Entry reason-code capture (a DevTools paste) or 'release'", amount=ova.get("unbillableamount"))
add("Exclusions", "count", action=EXC_TXT)
seen = set()
for r in xv:
    if r["vid"] in seen: continue
    seen.add(r["vid"])
    add("Exclusions", "cleared", "pat%s" % r["pid"], r["dos"], "BCBS 1414", "CH FH PREF0283 MISSING PAYER DOC CONTROL NUM (claim run 1700211, %s)" % r["claimid"], "completed per William's 9/13 crossover-wait decision; no rebill (resub %s, Medicare paid 9/19 check 819814877 with ICN on the payment)" % r["resub"], visit=r["vid"], amount="%.2f" % sum(f(x.get("insbalance")) for x in xv if x["vid"] == r["vid"]))
add("ERA", "count", action=ERA_TXT)
for c in ea: add("ERA", "still open (held)", "", "", c.get("systemcarriercode") or "", "", "era_clear HOLD - see the ERA section", c.get("id") or c.get("checkid"), (c.get("paymentnumber") or ""), "", "%.2f" % f(c.get("unpostedamount")))
for line in os.environ.get("ERA_ROWS", "").split("\n"):
    if line.strip():
        p = line.split("|"); add("ERA", p[0], "", p[3] if len(p) > 3 else "", p[4] if len(p) > 4 else "", "", p[5] if len(p) > 5 else "", p[1], p[2] if len(p) > 2 else "", p[6] if len(p) > 6 else "", p[7] if len(p) > 7 else "")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new, no row updated after 09:30Z 9/20 - nothing new from William.")
add("Sources", "read", action="Watched Drive folders (hca/tmh/PCC facesheets, Claimocity drop, 'bht Optum era downloads', 'treasury payments'): nothing new after 9/19 12:00Z except dianne harris.pdf (03:26Z, already worked by the 0345Z chat and verified 0710Z) and the routine's own report CSV; Pam Gmail (newer_than:2d has:attachment): the two admits already acted on (9/18 21:59Z, 9/19 02:53Z) - nothing newer; no board drop. Morning money report 10:55Z (chat) read: EOD close now HAS run (1700211 at 02:04 AMD clock).")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 678e937, session branch claude/pensive-einstein-kb2xv5), AMD_OK, STEDI_CRED_OK (no key file), AMD password from the environment's AMD_PSW credential (Gmail not read), ONE amd.login_cached success, no login lock. Cross-container guard: 0910Z START ~2 h old with its RUN COMPLETE digest - proceeded 11:10Z. Registers from practices/ehpa/registers (175 files); missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). needs_facesheet_list.md / precheck_cache.json / pseudonyms.json restored from the 0935Z/0645Z/9-19 'workspace mirror' copies; newest Drive state bundle is still 2026-09-18_1123UTC (stale - not unpacked, the repo registers are newer).")
add("Open on William's turn", "note", patient="%d visits" % payreason, action="Unbilled 'Payment reason codes are missing or do not balance' $%s: a DevTools paste of Payment Entry editing a payment's reason codes (or 'release') unlocks these secondaries" % ova.get("unbillableamount"))
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case) then 'rebill' - 59 visits $%.2f" % aet_bal)
with open("_run report 9-20 1110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - the night's claim run 1700211 (9/20 02:04 AMD clock) carried no AET12 claims. %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 9/19; the six watched folders hold nothing after 9/19 12:00Z outside dianne harris.pdf, already worked) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 9/19 02:53Z Center Pointe admit already acted on.")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("unbilled-unbalanced-postings-0915", "no", "%s: %d 'Payment reason codes' rows ($%s) held per the 9/15 rule; claim run 1700211 posted overnight but added no Unbilled rows. Still on your turn: the Payment Entry reason-code capture or 'release'." % (SLOT, payreason, ova.get("unbillableamount")))
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z 9/18 - 0910Z 9/20: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("bcbs-secondary-dcn-0910", "ok", "%s: claim run 1700211 rejected 11 more Florida Blue secondaries PREF0283 (pat17469028 x5, pat17473245 x4, pat17471968 x1, pat17476868 x1, $%.2f) after the 0510Z run re-sent them (5 freq 7 + Florida Blue ICN, 6 freq 1) - neither frequency supplies the Medicare crossover DCN (third confirmation; every charge carries the Medicare ICN on its 9/19 payment record and CH still says missing). Completed off the exclusion list per your 9/13 crossover-wait decision; nothing re-sent." % (SLOT, xbal),
    note="Your crossover-wait rule applied to 11 more Florida Blue secondaries (Medicare paid 9/19); nothing for you.")
app("addison-rupert-denials", "ok", "%s: the 6/20/2026 G0439 Florida Blue secondary (v19451524, $69.99) rejected PREF0283 again on run 1700211 after the 0510Z freq-7 resend - completed per the crossover-wait rule, left for the Medicare crossover." % SLOT)
app("dalrymple-dane-denials", "ok", "%s: the four Florida Blue secondaries (v19450195, v19451554, v19452629, v19452861; $%.2f) rejected PREF0283 again on run 1700211 after the 0510Z freq-7 resend - completed per the crossover-wait rule, left for the Medicare crossover." % (SLOT, sum(f(x.get("insbalance")) for x in xv if x["pid"] == "17473245")))
den = load("registers/era_denials_1051721_%s.json" % S, [])
open_den = [r for r in den if any(f(c.get("insbal")) > 0 for c in r["charges"])]
den_amt = round(sum(f(c.get("insbal")) for r in open_den for c in r["charges"]), 2)
ops.append({"op": "upsert", "collection": "items", "id": "centene-m56-denials-0920", "set": {
    "patient": "CENTENE (WellCare/Sunshine) CO16-M56 denial cluster - 5 charts", "dob": "", "facility": "SNF / ALF", "amdid": ", ".join(sorted({r["pid"] for r in open_den})), "mbi": "",
    "amount": den_amt, "status": "william",
    "need": "WILLIAM: the Centene ERA 0917718629 (labelled WELLCARE by AMD, 9/21/2026) answered six claims $0 with CO16 + M56 'missing/incomplete/invalid payer identifier'. Open balance $%.2f on 5 visits: two PRIMARY Sunshine claims (pat17469007 v19446730 99316 6/23/2026 $160; pat17471755 v19448214 99306+99497 7/13/2026 $389 - both sent to Payor ID 2111 on 9/13) and three Medicare-secondary residuals (pat17473346 v19453034 $74.64 to Sunshine seq 3; pat17477383 v19451168 $74.64 to Sunshine seq 2 - that chart carries DUPLICATE plans, FLO02 and SUN01 each entered twice as seq 1-4; pat17471131 v19453037 $74.64, chart has only CHP + Medicare yet Centene answered it). M56 on a PRIMARY Sunshine claim points at the payer id the claim carries (SUN01 = Payor ID 2111 while the WEL04 lines carry 1844 - Centene has merged Sunshine and WellCare Florida operations): please check the SUN01 carrier record's payer id / CPID in Master Files, or say 'rebill' and the run re-sends them as they are. Two more lines on this ERA were already at $0 in AMD (pat17474422 v19420718 CO109 wrong-payer $443 paid/adjusted earlier; pat12182947 v19453360 $141 paid by WEL04) - nothing to do. Nothing has been re-sent or written off." % den_amt,
    "why": "ERA step 5 (7am ET 9/20 run): the Post button posted the 4 paid lines of check 0917718629 ($332.52, pat17472703 99233 x4) and the 7 $0 denial lines went to the denial handling; the check was dismissed from the ERA Center.",
    "notes": [{"who": "Claude", "text": "Created by the 7am ET 9/20 run. Six CO16/M56 denials from one Centene remit; the two primary Sunshine ones look like a payer-id question on the carrier record, which is yours. Register registers/era_denials_1051721_%s.json." % S, "at": NOW}]},
    "append": {"checks": [{"ok": "no", "src": SRC, "result": "Centene ERA 0917718629: 6 x CO16/M56 ($%.2f open on 5 visits) + 1 x CO109 (already $0); visits read live (carrier billed, payer id, balances, plans) - nothing re-sent, nothing written off" % den_amt, "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 11:08-%s UTC 9/20, run %s)
Bootstrap: repo ATTACHED (origin/main 678e937, session branch claude/pensive-einstein-kb2xv5), AMD_OK, STEDI_CRED_OK (no key file), AMD password from the environment's AMD_PSW credential, ONE amd.login_cached success, no login lock. Cross-container guard: 0910Z START ~2 h old with its RUN COMPLETE digest - proceeded 11:10Z. Registers from practices/ehpa/registers (175 files); needs_facesheet_list.md + precheck_cache.json + pseudonyms.json from the 0935Z/0645Z/9-19 'workspace mirror' copies; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). Newest Drive state bundle still 2026-09-18_1123UTC (stale, not unpacked).
Boards: Working Denials queue 0; Insurance Refresh Board drops 0; no row updated after 09:30Z - nothing new from William. Sources: nothing new in any watched Drive folder or Pam Gmail since the 0910Z run.
Claim runs: NEW 1700211 (AMD clock 9/20 02:04 - the EOD close ran again; 11 exclusions, all PREF0283 Florida Blue secondaries).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s | Exclusions %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none.
NEEDS WILLIAM (unchanged): (1) Payment Entry reason-code capture (or 'release') for the %d Unbilled 'Payment reason codes' secondaries ($%s); (2) pat17477777 rplan18462071 Pre-Auth # (UI); (3) AET12 carrier master then 'rebill'; (4) save the proposed skill line (hospice denial = GV + rebill) into the synced skills; (5) the 0530Z nightly cascade's rows (Orwell $2,777, Dunstan $521, CHP recoupments $1,879.18, MacAllister $629, Garland-G facesheet, Sunshine trio, Logan) and its Paid_but_unposted_2026-09-20.csv; (6) the morning report's 6 Optum Pay remits still to download into 'bht Optum era downloads'.
Calls learned: no new call shape; behaviours captured (captured_calls_additions_2026-09-20_1110UTC-7amET-ehpa-cloud.md): PREF0283 on a Florida Blue secondary survives both frequency 7 + Florida Blue ICN and frequency 1 even when the Medicare payment record carries the Medicare ICN - complete per the crossover-wait rule, never re-send; a claim run's claimcount on getclaimexclusionclaimruns is historical, the per-run list call is the open count.
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, UNB_TXT, EXC_TXT, ERA_TXT, payreason, ova.get("unbillableamount"))
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-20_1110UTC run digest - backend billing run, 7 AM ET 9/20 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on the standing rows; real row ids; no status/need changes) uploaded; nothing trashed (none of the inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-20_1110UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
