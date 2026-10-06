# PLAIN ENGLISH (run outputs for the 1am ET 9/26/2026 slot - ehpa cloud run 2026-09-26T0510Z)
# Decides: nothing. Reads this run's registers (scan_0912 before/after, ERA snapshots, the release register) and writes: "_run report 9-26 0110.csv"
#   (names allowed - SendUserFile only), board_updates_2026-09-26T0510Z.json (appends on the standing watch rows), a
#   needs_facesheet_list.md section (pat ids only), captured_calls_additions_*.md and the chat-history digest (--final adds the
#   mirror result). Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-26T0510Z"; SRC = "1am ET 9/26 columns run (ehpa cloud)"; W = "9/26"; SLOT = "1 AM ET 9/26"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def rd(p, d): return open(p).read().strip() if os.path.exists(p) else d
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
MIRROR = rd("mirror_result.txt", "pending")
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", sb)
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount")
ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
eb_amt = sum(f(x.get("unpostedamount")) for x in eb); ea_amt = sum(f(x.get("unpostedamount")) for x in ea)
def pat(pid): return "pat%s" % pid
rows = []
def add(col, status, **k):
    r = {"column": col, "status": status, "patient": "", "dos": "", "carrier": "", "error": "", "action": "", "amount": "", "checkid": "", "visit": ""}; r.update(k); rows.append(r)
add("Charge Review", "0 -> 0", action="nothing to review (getreviewcharges empty)")
add("Claim Inspector", "%d -> %d" % (insp_b, insp_a), action="the 20 standing holds unchanged (same visits, same error text); no new batch since the 0310Z run")
for h in [("17472874", "15 April-2026 hospital visits", "Hospitalization From Date empty", "HELD - HCA admission date (row thackeray-kendrew-17472874)", "2403.00"), ("17473477", "19455625", "Pattern 35790 + deceased guard", "HELD for William", ""), ("45668", "19455691", "Pattern 20389 F02.80 + deceased guard", "HELD for William: void", ""), ("20863", "19455936", "Pattern 24078 CCI", "HELD for William", ""), ("17477208", "19455940", "duplicate 99487+99489 lines", "HELD for William", ""), ("17474541", "19430630", "Pattern 15775 + 4426", "HELD for William", "109.00")]:
    add("Claim Inspector", "held", patient=pat(h[0]), visit=h[1], error=h[2], action=h[3], amount=h[4])
add("Unbilled", "%s -> %s" % (ub_b, ub_a), action="5 new 'prior payor' rows released (primary claim out and unanswered - rule b); 26 standing holds unchanged")
add("Unbilled", "released", patient="pat24853 MARCHBANK,CHARLIZE", visit="19453094, 19453102, 19453106", dos="08/26-08/28/2026", carrier="HUM01", error="A payment from the prior payor is required", action="UHC (plan ended 12/31/2025) posted $0 PR-27 on 9/25 (check W0384723) onto charges already billed to Humana 9/23 (primary out, unanswered); patient balance 0 - released x3", amount="480.00")
add("Unbilled", "released", patient="pat17473343 TREMAYNE,DESMOND", visit="19442414", dos="05/17/2026", carrier="FLO02", error="A payment from the prior payor is required", action="CCM 99487 billed to Medicare 9/5 (unanswered); UHC $0 PR-27 9/6 (plan ended 5/31/2026); visit insorder 2,3 ok; PATIENT default insorder was '3' (Sunshine alone) -> set 2,3 (Medicare first, Sunshine last); released", amount="206.00")
add("Unbilled", "released", patient="pat23391 DELMAR,ANNIS", visit="19392347", dos="10/24/2024", carrier="BCBS / FLO02", error="A payment from the prior payor is required; charges have errors", action="99233: Medicare paid 92.58 (check 815876983, 9/20) + WOINS 43.80, $23.62 PR-2 crossed to Florida Blue seq 2 (billed 9/21, in flight); G0316 $30.97 billed to Medicare 9/10 with no answer posted (the 9/13 ERA had no posted line for it; dismissed-check details unreadable without restore) -> released (rule b); if Medicare denied it CO-29 it is a WOLATE next time the answer is in hand", amount="54.59")
for r in sa.get("unbilled", []):
    add("Unbilled", "held", patient="%s %s" % (pat(r["patientid"]), r.get("patientname", "")), visit=r["id"], dos=", ".join(sorted({x.get("dos", "").strip() for x in r["_chgs"]})), carrier=r.get("carriercode", ""), error="; ".join(r.get("_errs") or [])[:120], action="standing hold (see needs list)", amount="%.2f" % sum(f(x.get("fee")) for x in r["_chgs"]))
add("Exclusions", "%d -> %d" % (ex_b, ex_a), action="one row, unchanged: pat20863 v19445850 FLO99 PDTP0303 (no 99223 anchor within 45 days); no claim run newer than 1700236 (overview 7/$1108 lags the list call)")
add("Exclusions", "held", patient="pat20863", visit="19445850", carrier="FLO99", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="14.38")
add("ERA", "%d checks / $%.2f -> %d / $%.2f" % (len(eb), eb_amt, len(ea), ea_amt), action="ERA Center empty before and after (locks released, GET /api/era/checks = 0); nothing to upload from 'bht Optum era downloads'; nothing posted, nothing cleared")
add("ERA", "Availity 5(g)", action="no new Remittance Viewer PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (the seven watched folders hold nothing after 12:00Z 9/25 outside the routine's own files); no ScanSnap batch; nothing to parse, post or reconcile")
csvname = "_run report 9-26 0110.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
ops = []
def chk(rid, result, ok="ok"):
    ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
chk("aet12-carrier-cpid", "1 AM ET 9/26: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 1 row (the FLO99 PDTP0303 hold), none AET12; no claim run newer than 1700236.", "na")
chk("availity-remits-backlog", "1 AM ET 9/26: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; no ScanSnap batch; Working Denials queue 0; board drops 0; 0 rows changed since 20:00Z 9/25; Pam Gmail: nothing in the last 2 days; facesheet folders and Claimocity drop: nothing new. ERA Center 0 checks before and after. Columns 0/20/31/1 -> 0/20/26/1: five new Unbilled 'prior payor' rows released - UHC's $0 PR-27 (check W0384723, 9/25) on three Aug-2026 99233s already at Humana (v19453094/102/106), a 5/17/2026 CCM already at Medicare (v19442414; that chart's default order set Medicare first / Sunshine last), and a 10/24/2024 99233+G0316 whose Medicare payment crossed to Florida Blue (v19392347).", "na")
chk("bcbs-patient-balance-audit-0918", "1 AM ET 9/26: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements.", "na")
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
sec = """## %s columns run (ehpa cloud Code Routine, run %s) - %s
- Bootstrap: repo ATTACHED (origin/main 19f74f0 at start; session branch claude/pensive-einstein-4vi4q9, work done on main, symlinked as /home/claude/effinger-billing-backend); net AMD_OK (login gateway 200), STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread written to .amd_cred.json normally; ONE amd.login_cached success 05:17Z; no login lock; START marker 05:11Z (the 0310Z START is 2 h old and its digest ends RUN COMPLETE). Layout from main (663 helpers); pseudonyms (318 names), precheck_cache and laterality log from 'workspace mirror'; needs list rebuilt from the run sections in nightly/runs. bootstrap check: era_details_pull.py and columns_inspector2_0908.py MISSING from main (not rewritten; era_step_b_0913.py fills the era_details cache, insp_*.py scripts are the inspector template). Newest Drive state bundle still 2026-09-18_1123UTC (older than main - not unpacked). GITHUB INBOX: no unapplied PACKAGE_* manifest. Prompt v7 fired. Boards: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 20:00Z 9/25; both inbox registries list none of the current inbox files - nothing trashed. Pam Gmail: 0 attachments in the last 2 days. Watched folders: era downloads / treasury / facesheet folders / Claimocity drop - nothing new after 12:00Z 9/25 outside the routine's own files.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d ($3846.00) | Unbilled %s -> %s | Exclusions %d -> %d. No new inspector batch, no claim run newer than 1700236.
- UNBILLED released (5 rows, rule b - primary claim out and unanswered): pat24853 v19453094 / v19453102 / v19453106 (99233 8/26-8/28/2026, $480; UHC plan ended 12/31/2025 answered $0 PR-27 on 9/25 check W0384723; charges already at Humana seq 1 since 9/23; patient balance 0); pat17473343 v19442414 (99487 5/17/2026 $206 at Medicare since 9/5; UHC PR-27 9/6; visit order 2,3; PATIENT default insorder was '3' = Sunshine alone -> ins_update sequence 2,3, readback 2,3); pat23391 v19392347 (10/24/2024: 99233 paid by Medicare 9/20 check 815876983 92.58 + WOINS 43.80, PR-2 23.62 crossed to Florida Blue seq 2 billed 9/21; G0316 $30.97 at Medicare since 9/10, no answer posted - if Medicare's answer turns out CO-29 it is a WOLATE). Register registers/unbilled_release_%s.json.
- Claim Inspector holds (20, unchanged): pat17472874 x15 April-2026 HCA 'Hospitalization From Date empty' - admission date from William; pat17474541 v19430630 Pattern 15775 + 4426; pat17473477 v19455625 + pat45668 v19455691 deceased guard; pat20863 v19455936 CCI 24078; pat17477208 v19455940 duplicate CCM lines.
- Unbilled holds (26, unchanged): 16 pat17472874 + pat17474541 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; pat17477183 v19455471 + v19455759 (facesheet - William); pat17473232 v19455597 and pat17471681 v19455606 (CCM after DOD - William); pat17477639 v19455621 (no plan - William); pat17477842 v19455665 (duplicate chart - William: merge); pat17477850 v19455868 + v19455898 (CHP member id - William); pat17477870 v19456058 (duplicate chart - William: merge).
- EXCLUSIONS: 1 -> 1. pat20863 v19445850 FLO99 PDTP0303 $14.38 stays (no 99223 anchor within 45 days).
- ERA step 5: 0 unposted checks / $0.00 -> 0 / $0.00. Locks released; nothing in 'bht Optum era downloads' to upload; nothing posted, cleared or corrected; era_details cache 0 new. Availity 5(g): no new PDF / Check-EFT export; no ScanSnap batch.
- Dollars re-sent: $0 (releases only - no rebill). Insurance entered: none (one patient default order corrected). Write-offs: none. Residuals disregarded: $0. Exclusions completed: 0.
- Calls learned: no new call shape (captured_calls_additions_%s-1amET-ehpa-cloud.md - behaviours only). Vocabulary entries added: 0.
- NEEDS WILLIAM (unchanged): thackeray-kendrew-17472874 HCA admission date (15 inspector + 16 unbilled rows), alcott-alfie-17477183 facesheet, whitlow-shay-17477639 plan, griffith-jace-17477850 CHP member id, jarvis-marisa-17477842 + osgood-maryann-17477870 duplicate charts, whitfield-rowan-17473232 + penhale-rupert-17471681 CCM after death, the inspector holds (pat17474541, pat17473477, pat45668, pat20863, pat17477208), AET12 carrier master, carrier ERA setups (CO-45 auto write-off), centene-m56-denials-0920, harlington/gillespie/chp-coa1/copeland decisions, prompt v8 + v9 insert not yet pasted into the routine (this run still fired with the v7 text).
- Mirror: %s
""" % (SLOT, S, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a, S, S.replace("T", "_").replace("Z", "UTC"), MIRROR)
open("needs_section_%s.md" % S, "w").write(sec)
add_md = """# captured_calls additions - run %s (1am ET 9/26/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- Fresh container bootstrap: repo attached on session branch claude/pensive-einstein-4vi4q9 (main checked out for the work); bootstrap_workspace.sh net -> AMD_OK / STEDI_CRED_OK / GitHub reachable; .amd_cred.json written normally; ONE amd.login_cached success 05:17Z.
- getclaimcenteroverview at 05:17Z and 05:24Z: chargereview 0 / inspector 20 ($3,846) / unbilled 31 ($6,128.97 - the overview kept 31 after the five releases; the list call fell to 26) / exclusions 7 ($1,108 - lags; the per-run list call returns 1 row) / claimrunstatus 83 runs; newest claim run still 1700236.
- Unbilled 'A payment from the prior payor is required' rows appear when a payer posts a $0 PR-27 onto a charge whose LIVE carrier is already the re-routed primary (UHC check W0384723 9/25 on pat24853's three 99233s billed to Humana 9/23): the charge shows carrier HUM01 / billdate 9/23 with the UNI20 $0 payment attached; patient balance stays 0; hideunbillablevisits hide=-1 (numeric visit id) -> success=1, and the after-list dropped by all five released visits (the Delmar visit had TWO rows - blank carrier and BCBS - both left with one release).
- ins_update.update(pid, insid, sequence="2,3") answers <Results success="1"><patient insorder="2,3"/> and getdemographic reads the new patient insorder at once (pat17473343: '3' -> '2,3').
- payreasons.dismissed_index() lists 1750 dismissed checks since 8/1; payreasons.details(<dismissed checkid>) returns the eracheckdetails envelope with NO claim lines for a dismissed check (the 9/19 restore recipe is still the only way to read a dismissed check's lines).
- GET /api/era/checks at 05:23Z before and after: 0 unposted checks (POST /api/era/locks/release-expired sent first).
- Board reads (ArtifactData): commands where status==queued -> 0; items where status==claude -> 200+ rows (result capped); items where updated > 2026-09-25T20:00:00Z -> 0; drops where status==new -> 0. Both drive_sync registries unchanged since 9/24 06:16Z / 9/15 - none of the current inbox files are listed, nothing trashed.
""" % S
open("captured_calls_additions_%s-1amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(add_md)
print("rows", len(rows), "ops", len(ops), "insp", insp_b, insp_a, "ub", ub_b, ub_a, "ex", ex_b, ex_a, "era", len(eb), len(ea))
