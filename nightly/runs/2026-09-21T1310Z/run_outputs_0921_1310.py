# PLAIN ENGLISH (run outputs for the 9am ET 9/21/2026 slot - ehpa cloud run 2026-09-21T1310Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after) and writes:
#   "_run report 9-21 1310.csv"; board_updates_2026-09-21T1310Z.json (checks appends on the standing rows, no set ops);
#   a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys
S = "2026-09-21T1310Z"; SRC = "9am ET 9/21 columns run (ehpa cloud)"; W = "9/21"; SLOT = "9 AM ET 9/21"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
BUNDLE = open("bundle_result.txt").read().strip() if os.path.exists("bundle_result.txt") else "not attempted"
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
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is still empty. Locks release-expired sent; era_post --all-unposted 0 checks; fallback (payreasons.post_line, ERA-linked with reason codes) dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835 in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'treasury payments' (nothing modified in either folder after 12:00Z 9/20; Drive-wide nothing after 05:00Z 9/21 except the weekly-metrics spreadsheets/CSVs and routine files); no MA63/M76/M64 work; ERA cache 0 (nothing to pull)." % (nb, ab, na, aa))
UNB_TXT = ("%s -> %s rows ($%s -> $%s on the lagging overview): 0 'Payment reason codes are missing or do not balance' rows (payreasons.py --list = 0); the 1 row was the pat17470743 v19441047 'A payment from the prior payor is required' hold (99309 05/01/2026, MCAD seq 2, $16.93). Read live this run: the Medicare payment (check 819087561, 5/26) carries CO45 56.36 + PR2 16.93 + CO253 1.35 and balances to the $141.00 fee, the code-less MCAD $0 line is voided - so the secondary claim can be built and the row was a stale snapshot; RELEASED per the standing 'prior payor required' rule (hideunbillablevisits hide=-1, success 1); the charge now reads insbilled=0 (queued to the next payer on the next claim run) and the Unbilled list is empty. It re-queues on its own if AMD still cannot build the MCAD claim."
           % (len(ub), len(ua), ovb.get("unbillableamount"), ova.get("unbillableamount")))
EXC_TXT = ("%d -> %d rows on the per-run list calls (81 claim runs listed, every getclaimexclusioncharges empty; the lagging overview still shows exclusioncount 1 / $198.00; no run newer than 1700211, 9/20 02:04 AMD clock). AET12: HOLD per William 9/21 (chat 06:00Z) - not rebilled, not re-verified this slot; the 0510Z verify stands (68 charges on 15 charts, $2,052.25 open, Medicare paid $9,703.75, all crossover-marked C + X, billdate 09/16/2026)." % (exb, exa))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
add("Unbilled", "count", action=UNB_TXT)
add("Unbilled", "cleared", "pat17470743", "05/01/2026", "MCAD", "A payment from the prior payor is required", "released (hideunbillablevisits) - Medicare primary payment balances with reason codes CO45/PR2/CO253; $16.93 PR2 crossover queued to MCAD seq 2 (insbilled=0); register registers/unbilled_release_2026-09-21T1310Z.json", visit="19441047", amount="16.93")
add("Exclusions", "count", action=EXC_TXT)
add("ERA", "count", action=ERA_TXT)
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: 0 new drops; no item updated after 11:00Z 9/21. Board inbox: 18 files present (9/20 0345Z - 9/21 1110Z), none in the board's applied map (registry lastCheck 06:36Z 9/21, applied map unchanged) - nothing trashed.")
add("Sources", "read", action="Drive: 'bht Optum era downloads' and 'treasury payments' hold nothing modified after 12:00Z 9/20; Drive-wide after 05:00Z 9/21 only the weekly-metrics spreadsheets/CSVs, the compliance calendar and routine files; Pam Gmail (newer_than:2d has:attachment): nothing; Claimocity drop: nothing.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main e145bc7, session branch claude/pensive-einstein-k368d1), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 1110Z run's START has its RUN COMPLETE digest (11:42Z) - proceeded 13:13Z. Registers from practices/ehpa/registers (214 files); needs_facesheet_list.md (07:50Z + the 1110Z section from main) / precheck_cache.json / pseudonyms.json (221 names) from Drive 'workspace mirror'; payreasons.py + era_fallback_0913b.py from the repo helpers; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked, the repo registers are newer). Prompt: v7 fired; v8 (Drive 06:30Z, on main) not yet pasted into the routine - its Unbilled reason-code repair and ERA-linked fallback rules were followed anyway.")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt (Drive workspace mirror / nightly/ on main) into the routine - v7 still fires")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case); money comes from the Aetna side - 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check (Centene CO16/M56 on two primary Sunshine claims), or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads' (morning report 9/20)")
add("Open on William's turn", "note", patient="Automation Center", action="no ERA / End-of-Day-Close e-mail since 9/16 (weekly metrics run 9/21) - check the Automation Center rule / notification setting in AMD")
with open("_run report 9-21 1310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("unbilled-unbanced-postings-0915".replace("unbanced", "unbalanced"), "ok", "%s: Unbilled 1 -> 0 - 0 'Payment reason codes' rows (the 54/54 repair holds); the pat17470743 v19441047 'prior payor required' row was RELEASED: its Medicare payment (check 819087561) balances with CO45/PR2/CO253 to the $141 fee, so the $16.93 PR2 crossover to MCAD seq 2 can now build (charge insbilled=0, goes out on the next claim run). No decision needed unless it re-queues." % SLOT,
    note="The $16.93 Medicaid crossover row is released - Medicare's 5/26 payment carries its reason codes and balances, so nothing was holding it but the stale Unbilled snapshot. It bills MCAD on the next claim run; if it re-queues I will say so.")
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows, no claim run newer than 1700211 (9/20 02:04); the 0510Z read stands (68 charges / 15 charts / $2,052.25 open, all crossover-marked C + X). Waiting on the carrier record change or the Aetna-side money." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 12:00Z 9/20) - nothing to parse, post or reconcile; Working Denials queue 0; board drops 0; Pam Gmail 0." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 13:09-%s UTC 9/21, run %s)
Bootstrap: repo ATTACHED (origin/main e145bc7, session branch claude/pensive-einstein-k368d1), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: the 1110Z run's START has its RUN COMPLETE digest (11:42Z) - proceeded 13:13Z. Registers from practices/ehpa/registers (214 files); needs_facesheet_list.md / precheck_cache.json / pseudonyms.json (221 names) from Drive 'workspace mirror'; payreasons.py + era_fallback_0913b.py from the repo helpers; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired (v8 on Drive since 06:30Z and on main, not yet pasted; its rules followed anyway).
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no item updated after 11:00Z 9/21. Sources: Optum era downloads / treasury payments nothing after 12:00Z 9/20; Drive-wide after 05:00Z 9/21 only weekly-metrics + routine files; Pam Gmail: nothing; Claimocity drop: nothing. Weekly metrics bundle (10:00Z): %s.
Claim runs: none newer than 1700211 (9/20 02:04 AMD clock; 81 runs).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s | Exclusions %s
ERA step 5: %s
Write-offs: none. Rebilled: none (one Unbilled release queues the MCAD secondary of pat17470743 v19441047, $16.93). Insurance entered: none.
NEEDS WILLIAM: (1) paste prompt v8 into the routine; (2) pat17477777 rplan18462071 Pre-Auth # (UI); (3) AET12 carrier master (HOLD, Aetna-side money); (4) board row centene-m56-denials-0920 ($772.92) - SUN01 payer id / CPID check, or 'rebill'; (5) the 6 Optum Pay remits to download; (6) AMD Automation Center e-mails stopped 9/16 (check the rule); (7) BCBS patient-balance audit still parked.
Calls learned: no new call shapes (hideunbillablevisits hide=-1 with the numeric visit id reused); vocabulary unchanged (54).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BUNDLE, UNB_TXT, EXC_TXT, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-21_1310UTC run digest - backend billing run, 9 AM ET 9/21 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, unbilled-unbalanced-postings-0915 (+ a note), aet12-carrier-cpid, availity-remits-backlog; no set ops) uploaded; nothing trashed (none of the 18 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0 (54 calls). Postman: see mirror line.
Mirror: %s
State bundle: %s

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, open("state_bundle_result.txt").read().strip() if os.path.exists("state_bundle_result.txt") else "not uploaded (every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers)" % S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-21_1310UTC run digest.md", "w").write(dig)
    if S not in open("needs_facesheet_list.md").read():
        with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
