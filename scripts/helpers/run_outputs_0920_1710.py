# PLAIN ENGLISH (run outputs for the 1pm ET 9/20/2026 slot - ehpa cloud run 2026-09-20T1710Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after, AET12 verify, the ERA chain log)
#   and writes: "_run report 9-20 1710.csv"; board_updates_2026-09-20T1710Z.json (real row ids, checks appends only -
#   no status/need changes); a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt
#   exists). Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys, collections, re
S = "2026-09-20T1710Z"; SRC = "1pm ET 9/20 columns run (ehpa cloud)"; W = "9/20"; SLOT = "1 PM ET 9/20"
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
ERA_TXT = os.environ.get("ERA_TXT") or ("%d unposted checks / $%.2f before -> %d / $%.2f after. Locks release-expired sent. %s" % (nb, ab, na, aa, os.environ.get("ERA_DETAIL", "")))
def payreason_rows(rows): return [r for r in rows if any(e.startswith("Payment reason") for e in (r.get("_errs") or []))]
payreason = len(payreason_rows(ua))
prior_after = [r for r in ua if any(e.startswith("A payment from the prior") for e in (r.get("_errs") or []))]
UNB_TXT = ("%s -> %s rows ($%s -> $%s on the overview): %d 'Payment reason codes are missing or do not balance' rows (37 listed at the visit level + 17 under 'One or more charges within this visit have errors') held per the 9/15 rule (William's turn: Payment Entry reason-code capture or 'release'); %d 'A payment from the prior payor is required' row(s) held (pat17470743 v19441047 MCAD $16.93 behind a reversed Medicare payment). Nothing new on the snapshot since the 1510Z run."
           % (len(ub), len(ua), ovb.get("unbillableamount"), ova.get("unbillableamount"), payreason, len(prior_after)))
EXC_TXT = ("%d -> %d rows on the per-run list calls (the lagging overview showed exclusioncount 1 / $198.00 before; every claim run's getclaimexclusioncharges returned an empty visit list - no run newer than 1700211). AET12: %d charges on 15 charts $%.2f open (Medicare paid $%.2f), billdate 09/16/2026, none at $0, not on any open exclusion run - held on the carrier-master fix, not re-sent."
           % (exb, exa, len(ver), aet_bal, aet_paid))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
add("Unbilled", "count", action=UNB_TXT)
add("Unbilled", "remaining", "pat17470743", "05/01/2026", "MCAD", "A payment from the prior payor is required", "held - Medicaid crossover behind a reversed Medicare payment", visit="19441047", amount="16.93")
add("Unbilled", "remaining", "%d visits" % payreason, "", "", "Payment reason codes are missing or do not balance", "held per the 9/15 rule: secondaries behind hand-posted primary payments (manual_post carries no CARCs); on William's turn: Payment Entry reason-code capture (a DevTools paste) or 'release'", amount=ova.get("unbillableamount"))
add("Exclusions", "count", action=EXC_TXT)
add("ERA", "count", action=ERA_TXT)
for c in ea: add("ERA", "still open (held)", "", "", c.get("systemcarriercode") or "", "", "era_clear HOLD - see the ERA section", c.get("id") or c.get("checkid"), (c.get("paymentnumber") or ""), "", "%.2f" % f(c.get("unpostedamount")))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: drops 0 new, no row updated after 15:00Z 9/20 - nothing new from William; board inbox: applied-map check in the digest.")
add("Sources", "read", action="Drive-wide modifiedTime > 15:00Z 9/20 search: only the 1510Z run's board_updates file; 'bht Optum era downloads' + 'treasury payments': nothing modified since 9/19; Pam Gmail (newer_than:2d has:attachment): the two admits already acted on (9/18 21:59Z, 9/19 02:53Z) - nothing newer; no board drop.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 535784e, session branch claude/pensive-einstein-s898ua), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 (matches the environment AMD_PSW credential), ONE amd.login_cached success, no login lock. Cross-container guard: 1510Z START ~2 h old with its RUN COMPLETE digest - proceeded 17:10Z. Registers from practices/ehpa/registers (187 files); missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). needs_facesheet_list.md / precheck_cache.json / pseudonyms.json restored from the 1532Z/0645Z/9-19 'workspace mirror' copies; newest Drive state bundle is still 2026-09-18_1123UTC (stale - not unpacked, the repo registers are newer).")
add("Open on William's turn", "note", patient="%d visits" % payreason, action="Unbilled 'Payment reason codes are missing or do not balance' $%s: a DevTools paste of Payment Entry editing a payment's reason codes (or 'release') unlocks these secondaries" % ova.get("unbillableamount"))
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case) then 'rebill' - 59 visits $%.2f" % aet_bal)
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check (Centene CO16/M56 on two primary Sunshine claims), or 'rebill' - $772.92 on 5 visits")
with open("_run report 9-20 1710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("aet12-carrier-cpid", "no", "%s: unchanged - no claim run newer than 1700211 (9/20 02:04 AMD clock), Exclusions column 0 rows. %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, len(ver), aet_bal))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 9/19; Drive-wide nothing after 15:00Z 9/20 outside the routine's own files) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the 9/19 02:53Z Center Pointe admit already acted on.")
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("unbilled-unbalanced-postings-0915", "no", "%s: %d 'Payment reason codes' rows ($%s) held per the 9/15 rule; no new Unbilled rows since the 1510Z run. Still on your turn: the Payment Entry reason-code capture or 'release'." % (SLOT, payreason, ova.get("unbillableamount")))
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker as 0710Z 9/18 - 1510Z 9/20: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 17:08-%s UTC 9/20, run %s)
Bootstrap: repo ATTACHED (origin/main 535784e, session branch claude/pensive-einstein-s898ua), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 (matches the environment AMD_PSW credential), ONE amd.login_cached success, no login lock. Cross-container guard: 1510Z START ~2 h old with its RUN COMPLETE digest - proceeded 17:10Z. Registers from practices/ehpa/registers (187 files); needs_facesheet_list.md + precheck_cache.json + pseudonyms.json from the 1532Z/0645Z/9-19 'workspace mirror' copies; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). Newest Drive state bundle still 2026-09-18_1123UTC (stale, not unpacked).
Boards: Working Denials queue 0; Insurance Refresh Board drops 0; no row updated after 15:00Z - nothing new from William. Sources: nothing new in any watched Drive folder or Pam Gmail since the 1510Z run.
Claim runs: none newer than 1700211 (9/20 02:04 AMD clock).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s | Exclusions %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none.
NEEDS WILLIAM (unchanged): (1) Payment Entry reason-code capture (or 'release') for the %d Unbilled 'Payment reason codes' secondaries ($%s); (2) pat17477777 rplan18462071 Pre-Auth # (UI); (3) AET12 carrier master then 'rebill'; (4) save the proposed skill line (hospice denial = GV + rebill) into the synced skills; (5) the 0530Z nightly cascade's rows (Orwell $2,777, Dunstan $521, CHP recoupments $1,879.18, MacAllister $629, Garland-G facesheet, Sunshine trio, Logan) and its Paid_but_unposted_2026-09-20.csv; (6) the morning report's 6 Optum Pay remits still to download into 'bht Optum era downloads'; (7) board row centene-m56-denials-0920 ($772.92) - SUN01 carrier payer id / CPID check, or 'rebill'.
Calls learned: none (quiet slot - no new call shape, no new behaviour).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, UNB_TXT, EXC_TXT, ERA_TXT, payreason, ova.get("unbillableamount"))
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-20_1710UTC run digest - backend billing run, 1 PM ET 9/20 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on the standing rows; real row ids; no status/need changes) uploaded; nothing trashed (none of the inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0. Postman: unchanged.
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-20_1710UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
