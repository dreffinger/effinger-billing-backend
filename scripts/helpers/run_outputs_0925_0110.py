# PLAIN ENGLISH (run outputs for the 9pm ET 9/24/2026 slot - ehpa cloud run 2026-09-25T0110Z)
# Decides: nothing. Reads this run's registers (scan_0912 before/after, ERA snapshots) and writes:
#   "_run report 9-24 2110.csv", board_updates_2026-09-25T0110Z.json (appends only), a needs_facesheet_list.md section,
#   captured_calls_additions_*.md and the chat-history digest (--final adds the mirror result from mirror_result.txt).
# Never touches: AMD, the board databases.
import csv, json, os, re, datetime, sys
S = "2026-09-25T0110Z"; SRC = "9pm ET 9/24 columns run (ehpa cloud)"; W = "9/24"; SLOT = "9 PM ET 9/24"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def rd(p, d): return open(p).read().strip() if os.path.exists(p) else d
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
MIRROR = rd("mirror_result.txt", "pending")
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", {}) or sb
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount"); ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
eb_amt = sum(f(x.get("unpostedamount")) for x in eb); ea_amt = sum(f(x.get("unpostedamount")) for x in ea)
def pat(pid): return "pat%s" % pid
rows = []
def add(col, status, **k):
    r = {"column": col, "status": status, "patient": "", "dos": "", "carrier": "", "error": "", "action": "", "amount": "", "checkid": "", "visit": ""}; r.update(k); rows.append(r)
add("Charge Review", "0 -> 0", action="nothing to review")
add("Claim Inspector", "%d -> %d" % (insp_b, insp_a), action="no new rows; 20 standing holds unchanged, re-read live (batches 126125-127783); no new batch since 127787")
for h in [("17472874", "15 April-2026 hospital visits", "Hospitalization From Date empty", "HELD - HCA admission date (row thackeray-kendrew-17472874)", "2403.00"), ("17473477", "19455625", "Pattern 35790 + deceased guard", "HELD for William", ""), ("45668", "19455691", "Pattern 20389 F02.80 + deceased guard", "HELD for William: void", ""), ("20863", "19455936", "Pattern 24078 CCI", "HELD for William", ""), ("17477208", "19455940", "duplicate 99487+99489 lines", "HELD for William", ""), ("17474541", "19430630", "Pattern 15775 + 4426", "HELD for William", "109.00")]:
    add("Claim Inspector", "held", patient=pat(h[0]), visit=h[1], error=h[2], action=h[3], amount=h[4])
add("Unbilled", "%s -> %s" % (ub_b, ub_a), action="25 standing holds unchanged ($4,863.00): 16 pat17472874 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; 8 'Insurance order is missing' rows on William's turn (alcott x2, whitfield, powell, whitlow, jarvis, griffith x2)")
for r in sb.get("unbilled", []):
    add("Unbilled", "held", patient=pat(r["patientid"]), visit=r["id"], dos=", ".join(sorted({x.get("dos", "").strip() for x in r["_chgs"]})), carrier=r.get("carriercode", ""), error="; ".join(r.get("errors") or [])[:120], action="standing hold (see needs list)", amount="%.2f" % sum(f(x.get("fee")) for x in r["_chgs"]))
add("Exclusions", "%d -> %d" % (ex_b, ex_a), action="2 standing PDTP0303 holds unchanged; no claim run newer than 1700236 (overview 8/$1268 lags the list calls)")
add("Exclusions", "held", patient="pat17472517", visit="19423193", carrier="HUM01", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="70.17")
add("Exclusions", "held", patient="pat20863", visit="19445850", carrier="FLO99", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="14.38")
add("ERA", "%d checks / $%.2f -> %d / $%.2f" % (len(eb), eb_amt, len(ea), ea_amt), action="locks released; no new 835 to upload; Post button posted 2 new Humana checks (12 visits, $379.04); check 1052839 left the list on its own, 1052838 dismissed after its one $0 OA-23 line was settled WOCAID2ND; Post button refused check 1052828 again (PaymentEntry=1, over-apply guard v19420915 pay 105.75 vs balance 9.47) - residual held")
add("ERA", "auto-posted", checkid="1052838", carrier="HUM01 Humana Medicaid MMA 200940909260924", visit="19435320, 19442596, 19451354, 19422868, 19444044, 19428125, 19432979, 19426931, 19447325, 19438973", amount="165.40", action="10 secondary coinsurance lines posted by the Post button (payment only; over-apply guard, each = the open balance)")
add("ERA", "denial-only handled", checkid="1052838", carrier="HUM01 Humana Medicaid MMA 200940909260924", visit="19392338", amount="23.62", action="pat20903 99233 10/24/2024: Humana Medicaid secondary answered $0 with OA-23 $160 (primary paid >= Medicaid allowed; RARC #AM) - open secondary balance $23.62 written off WOCAID2ND per the 9/20-9/23 Humana Medicaid-secondary rule (manual_post pay 0 / wo 23.62, check 200940909260924, deposit 9/23; paymentid 10164127); the visit's G0316 line ($30.97) stays at Medicare, not on this ERA")
add("ERA", "auto-posted", checkid="1052839", carrier="HUM01 Humana 200940910260924", visit="19453779, 19453752", amount="213.64", action="2 primary 99233 lines (9/3 + 9/4/2026) posted by the Post button with CO-45 + CO-253; check left the unposted list")
add("ERA", "held", checkid="1052828", carrier="FLO02 Medicare 819843767", visit="19420915", amount="105.75", action="residual on a $0 charge (99487 $68.62, paid/adjusted by check 348567230 6/1/2026) + 99489 already manual-posted 9/24 0530Z ($9.47 PR-2 open) - disregarded per William 9/13; check stays on the list (era_clear holds it by the remit-stored balance)")
add("ERA", "Availity 5(g)", action="no new Remittance Viewer PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (only the 9/24 06:53Z Windows .exe, not a remit); nothing to parse, post or reconcile")
csvname = "_run report 9-24 2110.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
# ---------------- board updates (appends only)
ops = []
def chk(rid, result, ok="ok"): ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
chk("aet12-carrier-cpid", "9 PM ET 9/24: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 2 -> 2 (both PDTP0303 holds, none AET12); no claim run newer than 1700236.", "na")
chk("availity-remits-backlog", "9 PM ET 9/24: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; ERA Center 3 checks $484.79 -> 1 / $105.75: two new Humana 835s posted by the Post button (200940909260924: 10 Medicaid-secondary coinsurance lines $165.40 + one OA-23 $0 line settled WOCAID2ND $23.62 on v19392338; 200940910260924: 2 primary 99233 lines $213.64) and cleared; 1052828 residual still held. Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the 02:41Z Sodalis admit (worked 0510Z); facesheet folders and Claimocity drop: nothing new.", "ok")
chk("bcbs-patient-balance-audit-0918", "9 PM ET 9/24: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements.", "na")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(board, open("board_updates_%s.json" % S, "w"), indent=1)
# ---------------- needs section
sec = """
## %s columns run (ehpa cloud Code Routine, run %s) - %s
- Bootstrap: repo ATTACHED (origin/main 1ab6eb7 = the 2310Z run finalize commit; session branch claude/pensive-einstein-sprd9e, main checked out in the session clone (symlinked as /home/claude/effinger-billing-backend)); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread; ONE amd.login_cached success 01:19Z; no login lock; START marker uploaded 01:11Z. Layout from main (632 helpers; needs list rebuilt from the 65 run sections; 351 registers from practices/ehpa/registers); pseudonyms (302 names), precheck cache (37 entries), laterality log from 'workspace mirror'. bootstrap check: era_details_pull.py and columns_inspector2_0908.py MISSING from main (not rewritten; era_step_b_0913.py fills the era_details cache, insp_*.py scripts are the inspector template). Newest Drive state bundle still 2026-09-18_1123UTC (older than main - not unpacked). GITHUB INBOX: no unapplied PACKAGE_* manifest (both 9/23 packages APPLIED). Boards: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 22:00Z (query on updated), inbox registry lists none of the current inbox files - nothing trashed. Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked 0510Z). Drive: 'bht Optum era downloads' / 'treasury payments' / the three facesheet folders / Claimocity drop: nothing new (only the 06:53Z Windows .exe, not a remit).
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d ($3846) | Unbilled %s -> %s ($4863.00) | Exclusions %d -> %d (list; overview 8/$1268 lagging) - NO new rows in any column this slot; every row is a standing hold of the 0510Z run, re-read live; no claim run newer than 1700236.
- EXCLUSIONS: 2 standing PDTP0303 holds unchanged (pat17472517 v19423193 HUM01 $70.17, pat20863 v19445850 FLO99 $14.38 - no 99223 anchor within 45 days); every other run lists 0.
- Claim Inspector holds (20): pat17472874 x15 April-2026 HCA 'Hospitalization From Date empty' (admission date from William); pat17474541 v19430630 Pattern 15775 + 4426; pat17473477 v19455625 + pat45668 v19455691 deceased guard; pat20863 v19455936 CCI 24078; pat17477208 v19455940 duplicate CCM lines.
- Unbilled holds (25): 16 pat17472874 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; pat17477183 v19455471 + v19455759 (facesheet - William); pat17473232 v19455597 and pat17471681 v19455606 (CCM after DOD - William); pat17477639 v19455621 (no plan - William); pat17477842 v19455665 (duplicate chart - William: merge); pat17477850 v19455868 + v19455898 (CHP member id - William).
- ERA step 5: %d unposted checks / $%.2f -> %d / $%.2f. Locks released; no new 835 in 'bht Optum era downloads'. TWO NEW HUMANA CHECKS (dated 9/23): 1052838 (200940909260924, $165.40, Humana Medicaid MMA secondary) - Post button posted 10 Medicare-coinsurance residual lines $165.40 (payment only, over-apply guard = open balance each: v19435320, v19442596, v19451354, v19422868, v19444044, v19428125, v19432979, v19426931, v19447325, v19438973); its one $0 line (pat20903 v19392338 99233 10/24/2024, OA-23 $160 'impact of prior payer', RARC #AM, 'Procedure codes do not match' = not validated) is the Medicaid-secondary-pays-nothing case: open HUM01 balance $23.62 written off WOCAID2ND (manual_post pay 0 / wo 23.62, check 200940909260924, deposit 9/23, paymentid 10164127) per the 9/20-9/23 Humana Medicaid-secondary rule; era_clear then dismissed the check. 1052839 (200940910260924, $213.64, Humana primary) - Post button posted both 99233 lines (v19453779 9/3, v19453752 9/4/2026, CO-45 51.00 + CO-253 2.18 each); the check left the list on its own. 1052828 (Medicare 819843767) = the 0530Z residual: Post button refused again (PaymentEntry=1, over-apply guard v19420915 pay 105.75 vs balance 9.47); fallback: residual-zero $68.62 + register-skip $37.13 (settled in registers/era_manual_register.json), nothing to post; era_clear holds it - left on the list, residual disregarded per William 9/13. Auto-posted $379.04 (12 visits), manual-posted 0 (one denial-only write-off $23.62), checks cleared 2 (1 dismissed, 1 fully posted). Availity 5(g): no new PDF / Check-EFT export. payreasons --list: 0 Unbilled payment-reason rows.
- Dollars re-sent: $0. Insurance entered: none. Write-offs: pat20903 v19392338 $23.62 WOCAID2ND (Humana Medicaid secondary OA-23).
- Calls learned: no new call shape (captured_calls_additions_2026-09-25_0110UTC-9pmET-ehpa-cloud.md, behaviours only).
- Mirror: %s
""" % (SLOT, S, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a, len(eb), eb_amt, len(ea), ea_amt, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
if "--final" in sys.argv: open("needs_facesheet_list.md", "a").write(sec)
adds = """# captured_calls additions - run %s (9pm ET 9/24/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- Claims Center at 01:19Z 9/25: getclaimcenteroverview 0/20/25/8($1268) vs the list calls 0/20/25/2 (overview lags: the exclusion list on run 1700227 returns the 2 PDTP0303 rows only; every other run 0). getclaimexclusionclaimruns still lists 1700236 (2026-09-23 21:10, MCKPRV) as the newest run. No new inspector batch since 127787.
- ERA Center: GET /api/era/checks answered 3 unposted (2 new Humana checks dated 9/23 + the standing 1052828). posterapayments (Post button) on a Humana Medicaid-MMA SECONDARY check: era_post's over-apply guard drops the OA-23 adjustment and posts 'payment only' = the open coinsurance balance on each line (10 lines, HTTP 200 ok) - the balances close exactly, no residual. The same check's one $0 line (OA-23 for the whole charge, RARC #AM, claim status 2) comes back from checkdetails with errors [{id 5, 'Procedure codes do not match.'}] and processok false = 'not validated'; era_clear counts it 'not validated $0' and DISMISSES the check once the money lines are posted (POST /api/era/checks/dismiss ok). The line itself was settled by manual_post (addpayments pay 0 / wo WOCAID2ND, checknumber = the Humana trace) BEFORE the dismiss; checkdetails' insurancebalance (54.59) was stale - the live gettxhistory insbal (23.62) is what manual_post applies.
- Humana primary check 1052839 (2 x 99233, CO-45 + CO-253): posted in full by the Post button and left GET /api/era/checks on its own (no dismiss needed).
- ERA chain on check 1052828 unchanged from 9/24: fault -2147217287 (PaymentEntry=1) on the over-apply guard visit 19420915; fallback residual-zero $68.62 / register-skip $37.13; era_clear holds. POST /api/era/locks/release-expired sent. payreasons --list: 0 Unbilled payment-reason rows.
- Board read shape: ArtifactData query on items with where [["updated",">","2026-09-24T22:00:00Z"]] answers 'rows changed since' directly (0 docs); drops status==new 0; Working Denials commands status==queued 0; meta/drive_sync 'applied' map still ends at the 9/20 chat re-registration (none of the current inbox files listed - nothing trashed).
""" % S
open("captured_calls_additions_2026-09-25_0110UTC-9pmET-ehpa-cloud.md", "w").write(adds)
dig = """# %s run digest - backend billing run, %s slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main 1ab6eb7; session branch claude/pensive-einstein-sprd9e, main checked out in the session clone symlinked as /home/claude/effinger-billing-backend); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread 1866ce7e2233e4c0; ONE amd.login_cached success 01:19Z; no login lock; START marker 01:11Z. Layout from main (632 helpers, 351 registers); pseudonyms, precheck cache, laterality log from 'workspace mirror'; needs list rebuilt from the run sections. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten). State bundle restored: none (newest Drive bundle 2026-09-18_1123UTC is older than main). GITHUB INBOX: no unapplied PACKAGE_* manifest.
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 22:00Z (query on updated), inbox registry lists none of the current inbox files - nothing trashed; Pam Gmail: nothing newer than the 02:41Z Sodalis admit (worked); Drive: era downloads / treasury / facesheet folders / Claimocity drop unchanged.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d | Unbilled %s -> %s ($4,863.00) | Exclusions %d -> %d. No new rows in any column; every row = the standing holds (unchanged). Exclusions: the 2 standing PDTP0303 holds; no claim run newer than 1700236. $0 re-sent; no insurance entered.
- ERA: %d unposted checks / $%.2f -> %d / $%.2f. Two new Humana checks: 1052838 (200940909260924, Medicaid-MMA secondary) 10 coinsurance lines $165.40 auto-posted + its OA-23 $0 line (v19392338) settled WOCAID2ND $23.62 and the check dismissed; 1052839 (200940910260924) 2 x 99233 $213.64 auto-posted, check gone on its own. 1052828 (Medicare 819843767) residual held again (Post button PaymentEntry=1; fallback residual-zero $68.62 + register-skip $37.13; era_clear holds). Availity 5(g): no new files. Auto-posted $379.04 (12 visits), manual-posted 0, write-off $23.62 (WOCAID2ND), residual disregarded $68.62 (recorded 0710Z 9/24), checks cleared 2.
- Board: board_updates_%s.json (3 appends: aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918) -> board inbox; inbox registry lists none of the current inbox files - nothing trashed; denials inbox: nothing queued, no file.
- Calls learned: no new call shape (captured_calls_additions_2026-09-25_0110UTC-9pmET-ehpa-cloud.md, behaviours only). Vocabulary entries added: 0.
- Mirror: %s
- Waiting on William: unchanged from 0510Z 9/24 (whitlow-shay-17477639 facesheet, jarvis-marisa-17477842 duplicate chart, griffith-jace-17477850 CHP member id, whitfield-rowan-17473232 + penhale-rupert-17471681 CCM after death, alcott-alfie-17477183 facesheet, thackeray-kendrew-17472874 HCA admission date, AET12 carrier master, Florida Blue / VA CCN ERA setup, dettmer 8/22 CCM CO-151, centene-m56-denials-0920, Optum Pay remits to download, prompt v8 + v9 insert not yet pasted).
- Script errors: none.

RUN COMPLETE
""" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, insp_b, insp_a, ub_b, ub_a, ex_b, ex_a, len(eb), eb_amt, len(ea), ea_amt, S, MIRROR)
os.makedirs("chat_history", exist_ok=True)
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print("wrote", csvname, "board_updates_%s.json" % S, "needs section, additions, digest (mirror=%s)" % MIRROR[:60])
