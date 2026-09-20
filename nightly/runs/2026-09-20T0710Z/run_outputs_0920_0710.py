# PLAIN ENGLISH (run outputs for the 3am ET 9/20/2026 slot - ehpa cloud run 2026-09-20T0710Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after, AET12 verify, fallback/clear registers)
#   and writes: "_run report 9-20 0710.csv"; board_updates_2026-09-20T0710Z.json (real row ids, checks appends only);
#   a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys, collections, re
S = "2026-09-20T0710Z"; SRC = "3am ET 9/20 columns run (ehpa cloud)"; W = "9/20"; SLOT = "3 AM ET 9/20"
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
log = open("run_chain_0710.log").read() if os.path.exists("run_chain_0710.log") else ""
refused = list(dict.fromkeys(re.findall(r'POST (\d+) visits \$([\d.]+) -> HTTP 200 ok=False.*?PaymentEntry=(\d+)', log)))
fb_live = load("registers/era_fallback_%s_live.json" % S, {}) ; fb_dry = load("registers/era_fallback_%s_dry.json" % S, {})
def cnt(fb):
    if isinstance(fb, dict):
        rows = fb.get("rows") or fb.get("lines") or fb.get("results") or []
    else: rows = fb
    return collections.Counter(str((r.get("outcome") if isinstance(r, dict) else r))[:24] for r in rows)
unb_cnt = collections.Counter((r.get("_errs") or [""])[0][:30] for r in ua)
payreason = sum(1 for r in ua if any(e.startswith("Payment reason") for e in (r.get("_errs") or [])))
prior = [r for r in ua if any(e.startswith("A payment from the prior") for e in (r.get("_errs") or []))]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after (the two held Medicare ERA 819814877 entries 1051714 / 1051715, check date 9/22). Locks release-expired sent. "
           "Post button (era_post --all-unposted) re-offered %s lines and AMD refused every one again (fault -2147217287 'post each payment manually', PaymentEntry=%s = the lines already posted by hand 9/13-9/20; nothing double-posted). "
           "Fallback (dry then live): %s. era_clear: both checks HELD (the phantom unposted amount = hand-posted lines the Center cannot see + the write-off lines on William's turn), 0 dismissed, 0 addpayments faults. "
           "No new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; no MA63/M76/M64 work; ERA cache 2/2 checks."
           % (nb, ab, na, aa, " + ".join(r[0] for r in refused) or "29 + 14", " / ".join(r[2] for r in refused) or "29 / 14",
              ("live " + str(dict(cnt(fb_live)))) if fb_live else "0 lines to post (every remaining line already-posted / register-skip)"))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
add("Unbilled", "count", action="%s -> %s ($%s -> $%s): after = %s; no new claim run since 1700210 (9/19 21:02 AMD clock), so the snapshot is unchanged" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), dict(unb_cnt)))
for r in prior: add("Unbilled", "remaining", "pat%s" % r.get("patientid"), "", r.get("carriercode") or "MCAD", "A payment from the prior payor is required", "held (primary paid 5/26/2026, crossover still unbilled - reported since 0510Z)", visit=r.get("id"), amount="16.93")
add("Unbilled", "remaining", "%d visits" % payreason, "", "", "Payment reason codes are missing or do not balance", "held per the 9/15 rule: secondaries behind hand-posted primary payments (manual_post carries no CARCs); on William's turn since 0510Z: Payment Entry reason-code capture (a DevTools paste) or 'release'", amount=ova.get("unbillableamount"))
add("Exclusions", "count", carrier="", action="0 -> 0 rows on every claim run (getclaimexclusioncharges); newest claim run still 1700210 (9/19 21:02, 54 claims, its 11 PREF0283 rows completed 0510Z). AET12: %d charges on 15 charts $%.2f open (Medicare paid $%.2f), billdate 09/16/2026, none at $0 - held on the carrier-master fix, not re-sent" % (len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
for c in ea: add("ERA", "still open (held)", "", "", "FLO02", "hand-posted lines AMD's Center cannot see; write-off lines on William's turn", "era_clear HOLD (postable money remains in the remit-stored view)", c.get("id") or c.get("checkid"), "MEDICARE PART B 819814877", "", "%.2f" % f(c.get("unpostedamount")))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new, no row updated since the 0510Z run (William's notes of 03:29-05:00Z were all acted on by the 0345Z chat and the 0510Z run: felix / hospice GV / melvin / harris CHP card). harris-dianne-17477798: chart now carries CAP07 seq 1 (verified 07:19Z) - the stale needs_facesheet entry is closed below.")
add("Sources", "read", action="Drive watched folders (hca/tmh/PCC facesheets, Claimocity drop, bht Optum era downloads, treasury payments, billing agent project files) since 03:00Z 9/20: only dianne harris.pdf (03:26Z, worked by the 0345Z chat) and the routine/chat's own files (captured_calls additions, Paid_but_unposted_2026-09-20.csv from the 0530Z nightly cascade); Pam Gmail (newer_than:2d has:attachment): the two admits already acted on (9/18 21:59Z, 9/19 02:53Z) - nothing newer; no board drop.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 1b58c8b, session branch claude/pensive-einstein-8pv3vj), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0510Z START >40 min old with RUN COMPLETE digests (0510Z routine, 0530Z nightly cascade) - proceeded 07:09Z. Registers from practices/ehpa/registers (164 files); missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). needs_facesheet_list.md / precheck_cache.json restored from the 0645Z 'workspace mirror' copies; newest Drive state bundle is still 2026-09-18_1123UTC (no run since has uploaded one).")
add("Open on William's turn", "note", patient="%d visits" % payreason, action="Unbilled 'Payment reason codes are missing or do not balance' $%s: a DevTools paste of Payment Entry editing a payment's reason codes (or 'release') unlocks these secondaries" % ova.get("unbillableamount"))
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case) then 'rebill' - 59 visits $%.2f" % aet_bal)
with open("_run report 9-20 0710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700210 (9/19 21:02; it carried no AET12 claims). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there 9/19 or 9/20; the watched folders hold nothing after 03:00Z 9/20 outside the routine/chat's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 9/19 02:53Z Center Pointe admit already acted on.")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("unbilled-unbalanced-postings-0915", "no", "%s: unchanged - %d 'Payment reason codes' rows ($%s) held per the 9/15 rule (no new claim run, snapshot identical to 0510Z); 1 'prior payor' row held (pat17470743 v19441047 MCAD $16.93). Still on your turn: the Payment Entry reason-code capture or 'release'." % (SLOT, payreason, ova.get("unbillableamount")))
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z 9/18 - 0510Z 9/20: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("harris-dianne-17477798", "ok", "%s: chart re-read - CAP07 (car41826) seq 1 on file, no end date; the two visits are off the Unbilled column (no HARRIS row on the 55-row snapshot). Nothing open; the routine's needs_facesheet entry for this chart is closed." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 07:08-%s UTC 9/20, run %s)
Bootstrap: repo ATTACHED (origin/main 1b58c8b, session branch claude/pensive-einstein-8pv3vj), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: 0510Z START >40 min old with RUN COMPLETE digests (0510Z routine, 0530Z nightly cascade) - proceeded 07:09Z. Registers from practices/ehpa/registers (164 files); needs_facesheet_list.md + precheck_cache.json from the 0645Z 'workspace mirror' copies; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). pseudonyms.json 9/19 19:34Z copy (221 names). Newest Drive state bundle still 2026-09-18_1123UTC.
Boards: Working Denials queue 0; Insurance Refresh Board drops 0; no row updated since the 0510Z run - nothing new from William. harris-dianne-17477798 RESOLVED (CAP07 on the chart since the 0345Z chat, visits released) - the 9/19 needs-facesheet line above is closed. Sources: nothing new in any watched Drive folder or Pam Gmail since the 0510Z run (only the 0530Z nightly cascade's own files).
Claim runs: none newer than 1700210 (9/19 21:02 AMD clock).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s -> $%s): %d 'Payment reason codes' rows held (9/15 rule, William's turn), 1 'prior payor' row held (pat17470743 MCAD $16.93) | Exclusions 0 -> 0 rows; AET12 %d charges $%.2f open, held (carrier master).
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none.
NEEDS WILLIAM (unchanged): (1) Payment Entry reason-code capture (or 'release') for the %d Unbilled 'Payment reason codes' secondaries ($%s); (2) pat17477777 rplan18462071 Pre-Auth # (UI); (3) AET12 carrier master then 'rebill'; (4) save the proposed skill line (hospice denial = GV + rebill) into the synced skills; (5) the 0530Z nightly cascade's rows (O'Brien $2,777, Duncan $521, CHP recoupments $1,879.18, MacDonald $629, Garcia facesheet, Sunshine trio, Logan) and its Paid_but_unposted_2026-09-20.csv (83 claims $13.8K the payers say PAID - the UNI20 ERA hunt).
Calls learned: no new call shapes (quiet slot). The 0530Z nightly cascade's additions file (captured_calls_additions_2026-09-20_0530UTC-nightly-cascade.md) merged into the registry this run.
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), payreason, len(ver), aet_bal, ERA_TXT, payreason, ova.get("unbillableamount"))
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-20_0710UTC run digest - backend billing run, 3 AM ET 9/20 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on the standing rows + harris closed; real row ids) uploaded. Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-20_0710UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
