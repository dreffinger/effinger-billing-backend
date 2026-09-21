# PLAIN ENGLISH (run outputs for the 3am ET 9/21/2026 slot - ehpa cloud run 2026-09-21T0710Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after) and writes:
#   "_run report 9-21 0710.csv"; board_updates_2026-09-21T0710Z.json (checks appends on the standing rows, no set ops);
#   a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys
S = "2026-09-21T0710Z"; SRC = "3am ET 9/21 columns run (ehpa cloud)"; W = "9/21"; SLOT = "3 AM ET 9/21"
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
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty (the 05:30-06:35Z chat session processed + dismissed Medicare 819814877 entries 1051714 / 1051715 and re-dismissed the eight 2024 checks). Locks release-expired sent; era_post --all-unposted 0 checks; fallback (now payreasons.post_line, ERA-linked with reason codes) dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'treasury payments' (Drive-wide nothing modified after 05:00Z 9/21 except routine/chat files); no MA63/M76/M64 work; ERA cache 0 (nothing to pull)." % (nb, ab, na, aa))
def rows_with(rows, prefix): return [r for r in rows if any(e.startswith(prefix) for e in (r.get("_errs") or []))]
payreason = len(rows_with(ua, "Payment reason"))
prior_after = rows_with(ua, "A payment from the prior")
UNB_TXT = ("%s -> %s rows ($%s -> $%s on the overview): 0 'Payment reason codes are missing or do not balance' rows (all 54 repaired and released by the 05:30-06:35Z chat session with payreasons.py - William's 9/21 route); 1 'A payment from the prior payor is required' row held: pat17470743 v19441047 (99309 05/01/2026, MCAD seq 2, $16.93 = Medicare's PR2 coinsurance; Medicare paid 5/26 WITH reasons CO45/PR2/CO253, the code-less MCAD $0 line was voided 9/12) - the primary has paid, so this is not the rule-b 'primary out and unanswered' case; the Medicaid crossover of the PR2 is still unbilled. Same hold as 0110Z-0510Z."
           % (len(ub), len(ua), ovb.get("unbillableamount"), ova.get("unbillableamount")))
EXC_TXT = ("%d -> %d rows on the per-run list calls (72 claim runs re-listed, every getclaimexclusioncharges empty; the lagging overview shows exclusioncount 1 / $198.00; no run newer than 1700211, 9/20 02:04 AMD clock). AET12: HOLD per William 9/21 (chat 06:00Z) - not rebilled, not re-verified this slot; the 0510Z verify stands (68 charges on 15 charts, $2,052.25 open, Medicare paid $9,703.75, all crossover-marked C + X, billdate 09/16/2026)." % (exb, exa))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
add("Unbilled", "count", action=UNB_TXT)
add("Unbilled", "remaining", "pat17470743", "05/01/2026", "MCAD", "A payment from the prior payor is required", "held - Medicare primary paid 5/26 (reasons intact), Medicaid crossover of the $16.93 PR2 still unbilled; not a rule-b case, not released", visit="19441047", amount="16.93")
add("Exclusions", "count", action=EXC_TXT)
add("ERA", "count", action=ERA_TXT)
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: 0 new drops; no William note newer than 05:11Z 9/21 (all acted on by the 0510Z run and the chat); items on Claude's turn re-read (unbilled-unbalanced-postings-0915 done by the chat, era-manual-post-0912, aet12-carrier-cpid hold). Board inbox: 16 files present, none in the board's applied map (the page registry has not recorded applied files since 9/15) - nothing trashed.")
add("Sources", "read", action="Drive-wide modifiedTime > 05:00Z 9/21: only routine/chat files (0510Z run outputs, the chat's digests/additions/helpers, board_updates 0510Z + 0630Z); six watched folders (Optum era downloads, treasury payments, Claimocity drop, hca/tmh/PCC facesheets) nothing new; Pam Gmail (newer_than:2d has:attachment): nothing.")
add("Mirror", "note", action="Merged the chat's three additions files (0552 reason-codes route, 0600 AET12 crossover marker + hold, 0620 payreasons repair + sweep rule) into docs/captured_calls.md; vocabulary 52 -> 54 (ERA-linked addpayments with reason codes; reason-code repair recipe; hideunbillablevisits numeric id; posterapayments sweep rule); payreasons.py + the new era_fallback_0913b.py into scripts/helpers; rules.md +4; nightly/columns_task_prompt_ehpa_cloud_v8.txt added. NOT recovered from the chat (GitHub was blocked there): its registers payreason_repair_*.json / capped_fix_voids_2026-09-21T0605Z.json and nightly/runs/2026-09-21T0545Z-chat - they live only in the chat's bundle handed to William.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 8523e79, session branch claude/pensive-einstein-k88ay0), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 0510Z run's START has its RUN COMPLETE digest - proceeded 07:11Z. Registers from practices/ehpa/registers (211 files); pseudonyms.json / payreasons.py / era_fallback_0913b.py / captured_calls additions from Drive 'workspace mirror' + 'billing agent project files'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked, the repo registers are newer). Prompt: v7 fired; v8 (Drive, 06:30Z) not yet pasted into the routine.")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt (Drive workspace mirror / nightly/ on main) into the routine - v7 still fires")
add("Open on William's turn", "note", patient="pat17470743", action="v19441047 $16.93 MCAD crossover of Medicare's PR2 stuck on Unbilled 'prior payor required' (primary paid 5/26): say 'release' (hides it), 'rebill MCAD' (freq-1 to seq 2) or 'write off' (WOINS, the 9/20 Humana/Medicaid residual rule) - held until then")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case); money comes from the Aetna side - 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check (Centene CO16/M56 on two primary Sunshine claims), or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads' (morning report 9/20)")
add("Open on William's turn", "note", patient="chat bundle", action="the chat's 8 commits (registers payreason_repair_* / capped_fix_voids_*, nightly/runs/2026-09-21T0545Z-chat) exist only in the bundle it handed you - pull + push it when convenient; everything else from that session is on main after this run")
with open("_run report 9-21 0710.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("unbilled-unbalanced-postings-0915", "ok", "%s: Unbilled 1 -> 1 - 0 'Payment reason codes' rows left after your chat session's 54/54 repair (verified on the live list); the one row is pat17470743 v19441047 'prior payor required' ($16.93 MCAD crossover of Medicare's PR2, primary paid 5/26 with reasons) - held, reported on the run report; 'release' / 'rebill MCAD' / 'write off' are the choices. From this slot the fallback posts ERA lines through payreasons.post_line (reason codes kept), so no new rows of this kind should appear." % SLOT)
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows, no claim run newer than 1700211 (9/20 02:04); the 0510Z read stands (68 charges / 15 charts / $2,052.25 open, all crossover-marked C + X). Waiting on the carrier record change or the Aetna-side money." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing new after 05:00Z 9/21 except routine/chat files) - nothing to parse, post or reconcile; Working Denials queue 0; Pam Gmail 0." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 07:09-%s UTC 9/21, run %s)
Bootstrap: repo ATTACHED (origin/main 8523e79, session branch claude/pensive-einstein-k88ay0), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: the 0510Z run's START has its RUN COMPLETE digest - proceeded 07:11Z. Registers from practices/ehpa/registers (211 files); pseudonyms.json / payreasons.py / era_fallback_0913b.py / the chat's three captured_calls additions restored from Drive; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired (v8 on Drive since 06:30Z, not yet pasted).
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no William note newer than 05:11Z. Sources: Drive-wide nothing new after 05:00Z 9/21 except routine/chat files; Pam Gmail: nothing; Claimocity drop: nothing.
Claim runs: none newer than 1700211 (9/20 02:04 AMD clock).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s | Exclusions %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: none.
NEEDS WILLIAM: (1) paste prompt v8 into the routine; (2) pat17470743 v19441047 $16.93 MCAD crossover on Unbilled 'prior payor required' - 'release', 'rebill MCAD' or 'write off'; (3) pat17477777 rplan18462071 Pre-Auth # (UI); (4) AET12 carrier master (HOLD, Aetna-side money); (5) board row centene-m56-denials-0920 ($772.92) - SUN01 payer id / CPID check, or 'rebill'; (6) the 6 Optum Pay remits to download; (7) pull + push the chat's bundle (its registers + run folder are not on main); (8) BCBS patient-balance audit still parked.
Calls learned: no new call shapes; the chat's three additions files merged into the registry; vocabulary 52 -> 54 (ERA-linked addpayments with reason codes, reason-code repair recipe); rules.md +4.
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, UNB_TXT, EXC_TXT, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-21_0710UTC run digest - backend billing run, 3 AM ET 9/21 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, unbilled-unbalanced-postings-0915, aet12-carrier-cpid, availity-remits-backlog; no set ops) uploaded; nothing trashed (none of the 16 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 2 (payments-era/addpayments-era-linked-manual-post-with-reason-codes, payments-era/repair-payment-reason-codes-unbilled) + 3 entries amended (hideunbillablevisits numeric id, posterapayments sweep rule, plain addpayments retired for ERA lines). Postman: regenerated (54 calls).
Mirror: %s
State bundle: not uploaded (multi-part text-only connector upload exceeds the slot; every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers).

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-21_0710UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
