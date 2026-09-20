# PLAIN ENGLISH (run outputs for the 5am ET 9/20/2026 slot - ehpa cloud run 2026-09-20T0910Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after, AET12 verify, the Unbilled fix register)
#   and writes: "_run report 9-20 0910.csv"; board_updates_2026-09-20T0910Z.json (real row ids, checks appends + one new watch row);
#   a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys, collections, re
S = "2026-09-20T0910Z"; SRC = "5am ET 9/20 columns run (ehpa cloud)"; W = "9/20"; SLOT = "5 AM ET 9/20"
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
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
fix = load("registers/unbilled_fix_%s.json" % S, {"fixed": [], "released": [], "held": [], "errors": []})
fixed = fix["fixed"]; fix_amt = round(sum(f(x.get("insbal")) for x in fixed), 2)
rel_ok = [r for r in fix["released"] if r.get("ok")]
log = open("run_chain_0910.log").read() if os.path.exists("run_chain_0910.log") else ""
refused = list(dict.fromkeys(re.findall(r'POST (\d+) visits \$([\d.]+) -> HTTP 200 ok=False.*?PaymentEntry=(\d+)', log)))
unb_cnt = collections.Counter((r.get("_errs") or [""])[0][:30] for r in ua)
payreason = sum(1 for r in ua if any(e.startswith("Payment reason") for e in (r.get("_errs") or [])))
prior_after = [r for r in ua if any(e.startswith("A payment from the prior") for e in (r.get("_errs") or []))]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after (the two held Medicare ERA 819814877 entries 1051714 / 1051715, check date 9/22). Locks release-expired sent. "
           "Post button (era_post --all-unposted) re-offered %s lines and AMD refused every one again (fault -2147217287 'post each payment manually', PaymentEntry=%s = the lines already posted by hand 9/13-9/20; nothing double-posted). "
           "Fallback (dry then live): 0 lines to post (147 register-skips). era_clear: both checks HELD (the phantom unposted amount = hand-posted lines the Center cannot see + the write-off lines on William's turn), 0 dismissed, 0 addpayments faults. "
           "No new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 9/19); no MA63/M76/M64 work; ERA cache 2/2 checks."
           % (nb, ab, na, aa, " + ".join(r[0] for r in refused) or "29 + 14", " / ".join(r[2] for r in refused) or "29 / 14"))
UNB_TXT = ("%s -> %s rows on the list call ($%s -> $%s on the lagging overview): the Unbilled snapshot had refreshed itself since the 3 AM run and re-listed the same 33 'prior payor' rows the 1 AM run released. Root cause found for 18 of them (visits 194542xx, Jan-Feb 2026 SNF 99308/99309, $%.2f): they are the 9/10 Garcia->Effinger profile-swap RE-CREATED Medicaid visits - never transmitted (charge carrier blank, insbilled 0) because each visit's insorder still read the chart default with Medicare first, so every chargerebill on Medicaid's sequence queued a SECONDARY claim that AMD holds for the primary's payment; releasing them (9/11, 9/16, 9/17, 9/20 0510Z) only hid the rows. Fixed this run per the skill's 'bill a non-primary plan without reordering' rule: full-visit resave with insorder = Medicaid's OWN sequence (move_to_ins.move, car6113, never insorder[0]) + freq-1 rebill on that sequence -> 204 x18 (36 rebills, 0 faults), then released. The other 14 'prior payor' rows (primary billed 9/5-9/13 to Medicare, $0 or unanswered; secondary queued) released per the 9/8 rule; 1 held (pat17470743 v19441047 MCAD $16.93 behind a reversed Medicare payment). 54 'Payment reason codes' rows untouched (9/15 rule, William's turn)."
           % (len(ub), len(ua), ovb.get("unbillableamount"), ova.get("unbillableamount"), fix_amt))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
add("Unbilled", "count", action=UNB_TXT)
for x in fixed:
    add("Unbilled", "cleared", "pat%s" % x["pid"], "", "MCAD", "A payment from the prior payor is required (re-created Medicaid visit, never billed)", "visit insorder %s -> %s (Medicaid's own sequence), freq-1 rebill seq %s -> 204, released" % (x.get("insorder_before"), x.get("insorder_after"), x.get("mcad_seq")), visit=x["vid"], amount="%.2f" % f(x.get("insbal")))
for r in rel_ok:
    if not any(x["vid"] == r["vid"] for x in fixed):
        add("Unbilled", "cleared", "", "", "", "A payment from the prior payor is required", "released (9/8 rule: primary out and unanswered; re-queues when the primary posts)", visit=r["vid"])
for h in fix["held"]: add("Unbilled", "remaining", "pat%s" % h.get("pid"), "05/01/2026", "MCAD", "A payment from the prior payor is required", h.get("why"), visit=h["vid"], amount="16.93")
add("Unbilled", "remaining", "%d visits" % payreason, "", "", "Payment reason codes are missing or do not balance", "held per the 9/15 rule: secondaries behind hand-posted primary payments (manual_post carries no CARCs); on William's turn since 0510Z: Payment Entry reason-code capture (a DevTools paste) or 'release'", amount=ova.get("unbillableamount"))
add("Exclusions", "count", action="0 -> 0 rows on every claim run (getclaimexclusioncharges); newest claim run still 1700210 (9/19 21:02 AMD clock). AET12: %d charges on 15 charts $%.2f open (Medicare paid $%.2f), billdate 09/16/2026, none at $0 - held on the carrier-master fix, not re-sent" % (len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
for c in ea: add("ERA", "still open (held)", "", "", "FLO02", "hand-posted lines AMD's Center cannot see; write-off lines on William's turn", "era_clear HOLD (postable money remains in the remit-stored view)", c.get("id") or c.get("checkid"), "MEDICARE PART B 819814877", "", "%.2f" % f(c.get("unpostedamount")))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new, no row updated since the 0710Z run - nothing new from William.")
add("Sources", "read", action="Drive-wide modifiedTime > 07:00Z 9/20: only the routine's own pre-merge registry snapshots; 'bht Optum era downloads' and 'treasury payments': nothing modified since 9/19; Pam Gmail (newer_than:2d has:attachment): the two admits already acted on (9/18 21:59Z, 9/19 02:53Z) - nothing newer; no board drop.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 94a962a, session branch claude/pensive-einstein-119m4w), AMD_OK, STEDI_CRED_OK (no key file), AMD password from the environment's AMD_PSW credential (Gmail not read), ONE amd.login_cached success, no login lock. Cross-container guard: 0710Z START >40 min old with its RUN COMPLETE digest - proceeded 09:16Z. Registers from practices/ehpa/registers (169 files); missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). needs_facesheet_list.md / precheck_cache.json restored from the 0725Z/0645Z 'workspace mirror' copies; newest Drive state bundle is still 2026-09-18_1123UTC (stale - not unpacked, the repo registers are newer).")
add("Open on William's turn", "note", patient="%d visits" % payreason, action="Unbilled 'Payment reason codes are missing or do not balance' $%s: a DevTools paste of Payment Entry editing a payment's reason codes (or 'release') unlocks these secondaries" % ova.get("unbillableamount"))
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case) then 'rebill' - 59 visits $%.2f" % aet_bal)
with open("_run report 9-20 0910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700210 (9/19 21:02; it carried no AET12 claims). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 9/19; Drive-wide nothing after 07:00Z 9/20 outside the routine's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 9/19 02:53Z Center Pointe admit already acted on.")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("unbilled-unbalanced-postings-0915", "no", "%s: %d 'Payment reason codes' rows ($%s) held per the 9/15 rule (no new claim run); the 33 'prior payor' rows that re-listed after the 0510Z release were worked for cause this run (18 re-created Medicaid visits set to Medicaid's own sequence + freq-1 rebilled, 14 released, 1 held - see row recreated-medicaid-visits-0910). Still on your turn: the Payment Entry reason-code capture or 'release'." % (SLOT, payreason, ova.get("unbillableamount")))
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z 9/18 - 0710Z 9/20: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
ops.append({"op": "upsert", "collection": "items", "id": "recreated-medicaid-visits-0910", "set": {
    "patient": "RE-CREATED MEDICAID VISITS (9/10 Garcia->Effinger profile swap, 16 charts)", "dob": "", "facility": "SNF (fac32 / fac34)", "amdid": ", ".join(sorted({x["pid"] for x in fixed})), "mbi": "",
    "amount": fix_amt, "status": "claude",
    "need": "Watching. 18 Jan-Feb 2026 99308/99309 visits (ids 19454223-19454251, $%.2f) that the 9/10 profile swap re-created under Effinger never transmitted: their visit insurance order still read the chart default (Medicare first), so every rebill on Medicaid's sequence queued a secondary claim AMD held for the primary's payment ('A payment from the prior payor is required'). This run set each visit's insorder to Medicaid's own sequence and freq-1 rebilled it (204 x18); they leave on the next claim run. If Medicaid answers 'Medicare EOB required' on any of them, that chart needs a Medicare-first decision from you." % fix_amt,
    "why": "Unbilled column 9/11-9/20: 18 'A payment from the prior payor is required' rows with a blank carrier and no bill date, re-listed after every release.",
    "notes": [{"who": "Claude", "text": "Created by the 5am ET 9/20 run. Nothing for you unless Medicaid bounces them.", "at": NOW}]},
    "append": {"checks": [{"ok": "ok", "src": SRC, "result": "insorder set to Medicaid's own sequence + freq-1 rebill 204 on: " + ", ".join("v%s (pat%s seq %s)" % (x["vid"], x["pid"], x["mcad_seq"]) for x in fixed), "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 09:09-%s UTC 9/20, run %s)
Bootstrap: repo ATTACHED (origin/main 94a962a, session branch claude/pensive-einstein-119m4w), AMD_OK, STEDI_CRED_OK (no key file), AMD password from the environment's AMD_PSW credential, ONE amd.login_cached success, no login lock. Cross-container guard: 0710Z START >40 min old with its RUN COMPLETE digest - proceeded 09:16Z. Registers from practices/ehpa/registers (169 files); needs_facesheet_list.md + precheck_cache.json from the 0725Z/0645Z 'workspace mirror' copies; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). pseudonyms.json 9/19 19:34Z copy (221 names). Newest Drive state bundle still 2026-09-18_1123UTC (stale, not unpacked).
Boards: Working Denials queue 0; Insurance Refresh Board drops 0; no row updated since the 0710Z run - nothing new from William. Sources: nothing new in any watched Drive folder or Pam Gmail since the 0710Z run.
Claim runs: none newer than 1700210 (9/19 21:02 AMD clock).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s | Exclusions 0 -> 0 rows; AET12 %d charges $%.2f open, held (carrier master).
ERA step 5: %s
Write-offs: none. Rebilled: 18 re-created Medicaid visits ($%.2f, freq-1 on Medicaid's own sequence). Insurance entered: none.
NEEDS WILLIAM (unchanged): (1) Payment Entry reason-code capture (or 'release') for the %d Unbilled 'Payment reason codes' secondaries ($%s); (2) pat17477777 rplan18462071 Pre-Auth # (UI); (3) AET12 carrier master then 'rebill'; (4) save the proposed skill line (hospice denial = GV + rebill) into the synced skills; (5) the 0530Z nightly cascade's rows (Orwell $2,777, Dunstan $521, CHP recoupments $1,879.18, MacAllister $629, Garcia facesheet, Sunshine trio, Logan) and its Paid_but_unposted_2026-09-20.csv.
Calls learned: no new call shape; one RULE captured (captured_calls_additions_2026-09-20_0910UTC-5amET-ehpa-cloud.md): a re-created visit inherits the chart's default insorder, so a rebill on a non-first plan queues a secondary claim that AMD holds for the prior payer - set the visit insorder to that plan's sequence (move_to_ins.move seq=) before the freq-1 rebill; releasing the Unbilled row never sends it.
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, UNB_TXT, len(ver), aet_bal, ERA_TXT, fix_amt, payreason, ova.get("unbillableamount"))
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-20_0910UTC run digest - backend billing run, 5 AM ET 9/20 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on the standing rows + new watch row recreated-medicaid-visits-0910; real row ids) uploaded; nothing trashed (none of the inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-20_0910UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
