# PLAIN ENGLISH (run outputs for the 9am ET 9/24/2026 slot - ehpa cloud run 2026-09-24T1310Z)
# Decides: nothing. Reads this run's registers (scan_0912 before/after, ERA snapshots, excl_dup register) and writes:
#   "_run report 9-24 0910.csv", board_updates_2026-09-24T1310Z.json (appends only), a needs_facesheet_list.md section,
#   captured_calls_additions_*.md and the chat-history digest (--final adds the mirror result from mirror_result.txt).
# Never touches: AMD, the board databases.
import csv, json, os, re, datetime, sys
S = "2026-09-24T1310Z"; SRC = "9am ET 9/24 columns run (ehpa cloud)"; W = "9/24"; SLOT = "9 AM ET 9/24"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def rd(p, d): return open(p).read().strip() if os.path.exists(p) else d
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
MIRROR = rd("mirror_result.txt", "pending")
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
ex = load("registers/excl_dup_1700228_%s.json" % S, {})
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount"); ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
def pat(pid): return "pat%s" % pid
rows = []
def add(col, status, **k):
    r = {"column": col, "status": status, "patient": "", "dos": "", "carrier": "", "error": "", "action": "", "amount": "", "checkid": "", "visit": ""}; r.update(k); rows.append(r)
add("Charge Review", "0 -> 0", action="nothing to review")
add("Claim Inspector", "%d -> %d" % (insp_b, insp_a), action="20 standing holds unchanged, re-read live; nothing bypassed or resaved")
for h in [("17472874", "15 April-2026 hospital visits", "Hospitalization From Date empty", "HELD - HCA admission date (row thackeray-kendrew-17472874)", "2403.00"), ("17473477", "19455625", "Pattern 35790 + deceased guard", "HELD for William", ""), ("45668", "19455691", "Pattern 20389 F02.80 + deceased guard", "HELD for William: void", ""), ("20863", "19455936", "Pattern 24078 CCI", "HELD for William", ""), ("17477208", "19455940", "duplicate 99487+99489 lines", "HELD for William", ""), ("17474541", "19430630", "Pattern 15775", "HELD for William", "109.00")]:
    add("Claim Inspector", "held", patient=pat(h[0]), visit=h[1], error=h[2], action=h[3], amount=h[4])
add("Unbilled", "%s -> %s" % (ub_b, ub_a), action="25 standing holds unchanged ($4,863.00): 16 pat17472874 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; 8 'Insurance order is missing' rows on William's turn (alcorn x2, whitehouse, powell, whitson, joiner, griffin x2)")
for r in sb.get("unbilled", []):
    add("Unbilled", "held", patient=pat(r["patientid"]), visit=r["id"], dos=", ".join(sorted({x.get("dos", "").strip() for x in r["_chgs"]})), carrier=r.get("carriercode", ""), error="; ".join(r.get("errors") or [])[:120], action="standing hold (see needs list)", amount="%.2f" % sum(f(x.get("fee")) for x in r["_chgs"]))
add("Exclusions", "%d -> %d" % (ex_b, ex_a), action="claim run 1700228: 2 HUM01 PAYER duplicate-claim rejections completed (standing rule: never rebilled) - hideexclusions success=1, run re-lists 0")
for r in ex.get("rows", []):
    fee = sum(f(c.get("insbal")) + f(c.get("paid")) for c in ex.get("charges", []) if c["visit"] == r["visit"])
    add("Exclusions", "cleared", patient=pat(r["pid"]), visit=r["visit"], dos=r["dos"], carrier="HUM01", error=r["err"][:100], action="completed, no rebill (duplicate of a claim Humana already adjudicated; the 9/22 re-send came from that day's chat referral-plan repoint)", amount="%.2f" % fee)
add("Exclusions", "held", patient="pat17472517", visit="19423193", carrier="HUM01", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="70.17")
add("Exclusions", "held", patient="pat20863", visit="19445850", carrier="FLO99", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="14.38")
add("ERA", "%d checks / $%.2f -> %d / $%.2f" % (len(eb), sum(f(x.get("unpostedamount")) for x in eb), len(ea), sum(f(x.get("unpostedamount")) for x in ea)), action="locks released; no new 835; Post button refused check 1052828 again (PaymentEntry=1, over-apply guard v19420915); fallback: residual-zero $68.62 + already-posted $37.13, nothing to post; era_clear holds the check (postable money by the remit-stored balance)")
add("ERA", "held", checkid="1052828", carrier="FLO02 Medicare 819843767", visit="19420915", amount="105.75", action="residual on a $0 charge (99487 $68.62, paid/adjusted by check 348567230 6/1/2026) + 99489 already manual-posted 9/24 0530Z ($9.47 PR-2 open) - disregarded per William 9/13; check stays on the list")
add("ERA", "Availity 5(g)", action="no new Remittance Viewer PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (only the 06:53Z Windows .exe); nothing to parse, post or reconcile")
csvname = "_run report 9-24 0910.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
# ---------------- board updates (appends only)
ops = []
def chk(rid, result, ok="ok"): ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
chk("orwell-padraig-44953", "9 AM ET 9/24: claim run 1700228 (9/22 evening) carried his 8/7/2026 99239 (v19450843, $163) to Humana again - the 9/22 chat referral-plan repoint resaved it - and Humana returned it 'duplicate of a previously processed claim'. Completed off the exclusion list, NOT rebilled (no-rebill list since 9/19; the 277 F0/107 verdict stands). Balance $163 still open on HUM01 - part of the contractual decision on this row.", "na")
chk("aet12-carrier-cpid", "9 AM ET 9/24: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 4 -> 2 (the two new rows were HUM01 duplicate rejections on run 1700228, none AET12); no claim run newer than 1700236.", "na")
chk("availity-remits-backlog", "9 AM ET 9/24: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; ERA Center 1 check ($105.75 residual on 1052828, held); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the 02:41Z Sodalis admit.", "na")
chk("bcbs-patient-balance-audit-0918", "9 AM ET 9/24: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements.", "na")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(board, open("board_updates_%s.json" % S, "w"), indent=1)
# ---------------- needs section
sec = """
## %s columns run (ehpa cloud Code Routine, run %s) - %s
- Bootstrap: repo ATTACHED (origin/main 2670eac = the 1113Z finalize commit; session branch claude/pensive-einstein-vvbpiy, work on main via a worktree); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread; ONE amd.login_cached success 13:14Z; no login lock; START marker uploaded 13:12Z. Layout from main (618 helpers, 350 registers, needs list rebuilt from the run sections); pseudonyms, precheck cache, laterality log from 'workspace mirror'. bootstrap check: era_details_pull.py and columns_inspector2_0908.py MISSING from main (not rewritten; era_step_b_0913.py fills the era_details cache, insp_*.py scripts are the inspector template). Newest Drive state bundle still 2026-09-18_1123UTC (older than main - not unpacked). GITHUB INBOX: no unapplied PACKAGE_* manifest. Boards: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 11:00Z. Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked). Drive: 'bht Optum era downloads' / 'treasury payments' / the four facesheet folders unchanged (only the 06:53Z Windows .exe).
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d ($3846) | Unbilled %s -> %s ($4863.00) | Exclusions %d -> %d (list; overview 5/$947 lagging) - inspector and Unbilled rows are the standing holds of the 0510Z run, re-read live; no claim run newer than 1700236.
- EXCLUSIONS: claim run 1700228 surfaced two HUM01 PAYER rejections 'ACK/RETURNED AS UNPROCESSABLE CLAIM ... DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM/LINE': pat17472396 v19448871 (7/17/2026 99487+99489 $315 - Humana already paid $289.94, $25.06 coinsurance open) and pat44953 v19450843 (8/7/2026 99239 $163, the Humana no-rebill chart). Both were re-sent 9/22 by that day's chat referral-plan repoint. Standing rule: duplicate-claim rejections -> completed, no rebill (hideexclusions success=1, run re-lists 0). Standing PDTP0303 holds unchanged: pat17472517 v19423193 HUM01 $70.17, pat20863 v19445850 FLO99 $14.38.
- Claim Inspector holds (20): pat17472874 x15 April-2026 HCA 'Hospitalization From Date empty' (admission date from William); pat17474541 v19430630 Pattern 15775 + 4426; pat17473477 v19455625 + pat45668 v19455691 deceased guard; pat20863 v19455936 CCI 24078; pat17477208 v19455940 duplicate CCM lines.
- Unbilled holds (25): 16 pat17472874 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; pat17477183 v19455471 + v19455759 (facesheet - William); pat17473232 v19455597 and pat17471681 v19455606 (CCM after DOD - William); pat17477639 v19455621 (no plan - William); pat17477842 v19455665 (duplicate chart - William: merge); pat17477850 v19455868 + v19455898 (CHP member id - William).
- ERA step 5: %d unposted check / $%.2f -> %d / $%.2f. Locks released. Check 1052828 (Medicare 819843767) = the 0530Z residual: Post button refused again (PaymentEntry=1, over-apply guard v19420915 pay 105.75 vs balance 9.47); fallback: residual-zero $68.62 + already-posted $37.13 (both in registers/era_manual_register.json), nothing to post; era_clear holds the check ('postable money' 1 by the remit-stored balance) - left on the list, residual disregarded per William 9/13. Auto-posted $0, manual-posted 0, checks cleared 0. Availity 5(g): no new PDF / Check-EFT export.
- Dollars re-sent: $0. Insurance entered: none. Write-offs: none.
- Calls learned: no new call shape (captured_calls_additions_2026-09-24_1310UTC-9amET-ehpa-cloud.md, behaviours only).
- Mirror: %s
""" % (SLOT, S, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a, len(eb), sum(f(x.get("unpostedamount")) for x in eb), len(ea), sum(f(x.get("unpostedamount")) for x in ea), MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
if "--final" in sys.argv: open("needs_facesheet_list.md", "a").write(sec)
adds = """# captured_calls additions - run %s (9am ET 9/24/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- getclaimexclusioncharges (clearinghouse=1 payer=1) on run 1700228 returned two rows whose <error> carries isexclusion="0" and name 'PA  ACK,RETURND AS UNPRCESSBLE CLM- CLM,ENCNTER BEEN REJECTD AND NOT ENTERD INTO ADJUDICATION SYS.:DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM, LINE.' (+ the long-form 'PA R ACKNOWLEDGEMENT/RETURNED AS UNPROCESSABLE CLAIM ...') = Humana payer-level duplicate rejection (payer id 2449). hideexclusions claimrunid=1700228 hide=-1 with <visit id claimid/> x2 -> success=1; the run re-lists empty. Both visits had been re-sent by a 9/22 referral-plan repoint resave (billdate 09/22/2026) on claims Humana had already adjudicated (pat17472396 paid, pat44953 F0/107 $0) - a resave that re-queues a claim to a payer that already adjudicated it draws this rejection; completing it is the whole fix.
- gettxhistory charge attrs on the Humana-paid CCM (pat17472396 v19448871): carrier=HUM01, paid=189.86/100.08, insbal=16.14/8.92 (coinsurance residual), payerinfo 'Payor ID: 2449'.
- ERA chain on check 1052828 unchanged from 0710Z/0910Z/1113Z: era_post --all-unposted -> fault -2147217287 (Error Counters PaymentEntry=1) on the over-apply guard visit; era_fallback_0913b classifies residual-zero $68.62 / already $37.13; era_clear holds ('postable money' 1). GET /api/era/checks before = after (1 / $105.75). POST /api/era/locks/release-expired sent.
- Bootstrap in a Claude Code cloud session: the repo clone lives at /home/user/effinger-billing-backend on a session branch; `git worktree add -B main /home/claude/effinger-billing-backend origin/main` gives the routine its /home/claude/effinger-billing-backend main checkout without touching the session branch.
""" % S
open("captured_calls_additions_2026-09-24_1310UTC-9amET-ehpa-cloud.md", "w").write(adds)
dig = """# %s run digest - backend billing run, %s slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main 2670eac; session branch claude/pensive-einstein-vvbpiy, main checked out as a worktree at /home/claude/effinger-billing-backend); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread 1866ce7e2233e4c0; ONE amd.login_cached success 13:14Z; no login lock; START marker 13:12Z. Layout from main (618 helpers, 350 registers); pseudonyms, precheck cache, laterality log from 'workspace mirror'. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten). State bundle restored: none (newest Drive bundle 2026-09-18_1123UTC is older than main). GITHUB INBOX: no unapplied PACKAGE_* manifest.
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 11:00Z; Pam Gmail: nothing newer than the 02:41Z Sodalis admit (worked); Drive: era downloads / treasury / facesheet folders unchanged.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d | Unbilled %s -> %s ($4,863.00) | Exclusions %d -> %d. Inspector + Unbilled = the standing holds (unchanged). Exclusions: 2 HUM01 payer duplicate-claim rejections on run 1700228 (pat17472396 v19448871 $315 CCM 7/17/2026 - Humana already paid; pat44953 v19450843 $163 99239 8/7/2026 - no-rebill chart) completed, no rebill. $0 re-sent; no insurance entered; no write-offs.
- ERA: %d unposted check / $%.2f -> %d / $%.2f. Check 1052828 (Medicare 819843767) residual held again (Post button PaymentEntry=1; fallback residual-zero $68.62 + already $37.13; era_clear holds). Availity 5(g): no new files. Auto-posted $0, manual-posted 0, residual disregarded $68.62 (recorded 0710Z), checks cleared 0.
- Board: board_updates_%s.json (4 appends: orwell-padraig-44953, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918) -> board inbox; inbox registry lists none of the current inbox files - nothing trashed; denials inbox: nothing queued, no file.
- Calls learned: no new call shape (captured_calls_additions_2026-09-24_1310UTC-9amET-ehpa-cloud.md, behaviours only). Vocabulary entries added: 0.
- Mirror: %s
- Waiting on William: unchanged from 0510Z (whitson-shane-17477639 facesheet, jarvis-marisa-17477842 duplicate chart, griffin-jayson-17477850 CHP member id, whitfield-rowan-17473232 + penhale-rupert-17471681 CCM after death, alcorn-alfred-17477183 facesheet, thackeray-kendrew-17472874 HCA admission date, AET12 carrier master, Florida Blue / VA CCN ERA setup, deistchle 8/22 CCM CO-151, centene-m56-denials-0920, Optum Pay remits to download, prompt v8 + v9 insert not yet pasted).
- Script errors: none.

RUN COMPLETE
""" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, insp_b, insp_a, ub_b, ub_a, ex_b, ex_a, len(eb), sum(f(x.get("unpostedamount")) for x in eb), len(ea), sum(f(x.get("unpostedamount")) for x in ea), S, MIRROR)
os.makedirs("chat_history", exist_ok=True)
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print("wrote", csvname, "board ops", len(ops))
