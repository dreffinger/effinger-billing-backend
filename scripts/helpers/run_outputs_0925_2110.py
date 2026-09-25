# PLAIN ENGLISH (run outputs for the 5pm ET 9/25/2026 slot - ehpa cloud run 2026-09-25T2110Z)
# Decides: nothing. Reads this run's registers (scan_0912 before/after snapshots, ERA snapshots, the CO-45 correction register) and writes:
#   "_run report 9-25 1710.csv" (names allowed - SendUserFile only), board_updates_2026-09-25T2110Z.json (appends on the standing
#   watch rows), a needs_facesheet_list.md section (pat ids only), captured_calls_additions_*.md and the chat-history digest
#   (--final adds the mirror result).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-25T2110Z"; SRC = "5pm ET 9/25 columns run (ehpa cloud)"; W = "9/25"; SLOT = "5 PM ET 9/25"
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
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount"); ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
eb_amt = sum(f(x.get("unpostedamount")) for x in eb); ea_amt = sum(f(x.get("unpostedamount")) for x in ea)
ov = sb.get("overview") or {}; ova = sa.get("overview") or {}
def pat(pid): return "pat%s" % pid
rows = []
def add(col, status, **k):
    r = {"column": col, "status": status, "patient": "", "dos": "", "carrier": "", "error": "", "action": "", "amount": "", "checkid": "", "visit": ""}; r.update(k); rows.append(r)
add("Charge Review", "0 -> 0", action="nothing to review (getreviewcharges empty)")
add("Claim Inspector", "%d -> %d" % (insp_b, insp_a), action="no new row since the 1910Z run (batch 127789 gone, no claim run newer than 1700236); the 20 standing holds unchanged (batches 126125-127783, same error ids) - nothing to clear")
for h in [("17472874", "15 April-2026 hospital visits", "Hospitalization From Date empty", "HELD - HCA admission date (row thackeray-kendrew-17472874)", "2403.00"), ("17473477", "19455625", "Pattern 35790 + deceased guard", "HELD for William", ""), ("45668", "19455691", "Pattern 20389 F02.80 + deceased guard", "HELD for William: void", ""), ("20863", "19455936", "Pattern 24078 CCI", "HELD for William", ""), ("17477208", "19455940", "duplicate 99487+99489 lines", "HELD for William", ""), ("17474541", "19430630", "Pattern 15775 + 4426", "HELD for William", "109.00")]:
    add("Claim Inspector", "held", patient=pat(h[0]), visit=h[1], error=h[2], action=h[3], amount=h[4])
add("Unbilled", "%s -> %s" % (ub_b, ub_a), action="no new rows since the 1910Z run; 26 standing holds unchanged, nothing released")
for r in sb.get("unbilled", []):
    add("Unbilled", "held", patient="%s %s" % (pat(r["patientid"]), r.get("patientname", "")), visit=r["id"], dos=", ".join(sorted({x.get("dos", "").strip() for x in r["_chgs"]})), carrier=r.get("carriercode", ""), error="; ".join(r.get("_errs") or [])[:120], action="standing hold (see needs list)", amount="%.2f" % sum(f(x.get("fee")) for x in r["_chgs"]))
add("Exclusions", "%d -> %d" % (ex_b, ex_a), action="2 standing PDTP0303 holds unchanged; no claim run newer than 1700236 (overview 8/$1268 lags the list calls)")
add("Exclusions", "held", patient="pat17472517", visit="19423193", carrier="HUM01", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="70.17")
add("Exclusions", "held", patient="pat20863", visit="19445850", carrier="FLO99", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="14.38")
add("ERA", "%d checks / $%.2f -> %d / $%.2f" % (len(eb), eb_amt, len(ea), ea_amt), action="two new 835s since the 1910Z run: Ambetter 0934734717 (ERA 1052847, $115.80) and Sunshine 0917761409 (ERA 1052848, $166.26); locks released; Post button posted all 4 money lines ($282.06); Ambetter's two lines then needed the CO-45 contractual correction ($189.40 WOINS); 5 denial-only $0 lines on 1052848 all on charges already at $0; 1052848 dismissed, 1052847 left the list on posting; ERA Center empty after; payreasons --list 0 rows")
add("ERA", "posted (button)", patient="pat17477799", visit="19455058", dos="09/16/2026", carrier="AMB03", checkid="1052847 / 0934734717", amount="79.85", action="99223 paid 79.85 (CO-45 150.30, PR-2 79.85); Post button left CO-45 on the patient balance -> move_to_ins + WOINS 150.30 with the trace number; patient balance now 79.85 = coinsurance (single-plan chart)")
add("ERA", "posted (button)", patient="pat17477799", visit="19455032", dos="09/17/2026", carrier="AMB03", checkid="1052847 / 0934734717", amount="35.95", action="99232 paid 35.95 (CO-45 39.10, PR-2 35.95); CO-45 corrected WOINS 39.10; patient balance now 35.95 = coinsurance")
add("ERA", "posted (button)", patient="pat17472703", visit="19455116", dos="09/18/2026", carrier="SUN01", checkid="1052848 / 0917761409", amount="83.13", action="99233 paid 83.13 + WOMCAD 76.87 posted by the button; balance $0")
add("ERA", "posted (button)", patient="pat17472703", visit="19455042", dos="09/17/2026", carrier="SUN01", checkid="1052848 / 0917761409", amount="83.13", action="99233 paid 83.13 + WOMCAD 76.87 posted by the button; balance $0")
for vid, dos in (("19400169", "02/09/2025"), ("19403205", "04/02/2025"), ("19400279", "02/10/2025")):
    add("ERA", "denial-only, already adjudicated", patient="pat17471181", visit=vid, dos=dos, carrier="SUN01", checkid="1052848 / 0917761409", amount="0.00", action="CO-286 $0 line on a 99232 already at $0 both sides (Sunshine paid 57.37 + WOMCAD earlier) - recorded, nothing posted")
for vid, dos, cpt in (("19423425", "11/04/2025", "99309"), ("19419546", "10/07/2025", "99308")):
    add("ERA", "denial-only, already adjudicated", patient="pat21442", visit=vid, dos=dos, carrier="SUN01", checkid="1052848 / 0917761409", amount="0.00", action="CO-16/M56 $0 line on the Sunshine secondary of a %s already at $0 both sides (Medicare 819814877 paid 9/19, WOMCAD + WOCAID2ND 9/22) - Centene M56 cluster, nothing to post" % cpt)
add("ERA", "Availity 5(g)", action="no new Remittance Viewer PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing there after the 9/24 03:39Z ScanSnap enrollment forms, already read); no ScanSnap batch; nothing to parse, post or reconcile")
csvname = "_run report 9-25 1710.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
# ---------------- board updates (appends on the standing watch rows only)
ops = []
def chk(rid, result, ok="ok", note=None):
    op = {"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: op["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(op)
chk("aet12-carrier-cpid", "5 PM ET 9/25: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 2 -> 2 (both PDTP0303 holds, none AET12); no claim run newer than 1700236.", "na")
chk("availity-remits-backlog", "5 PM ET 9/25: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; no ScanSnap batch; Working Denials queue 0; board drops 0; 0 rows changed since 19:00Z; Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked); facesheet folders and Claimocity drop: nothing new. ERA Center 2 checks / $282.06 -> 0: Ambetter 0934734717 ($115.80, 2 lines) and Sunshine 0917761409 ($166.26, 2 money lines + 5 $0 lines already settled) posted and cleared. Columns 0/20/26/2 -> 0/20/26/2 (all standing holds).", "na")
chk("bcbs-patient-balance-audit-0918", "5 PM ET 9/25: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements. Same CO-45-on-the-patient defect seen tonight on the AMBETTER carrier (AMB03, check 0934734717: 2 lines / $189.40 corrected WOINS with the trace number; PR-2 coinsurance left on the patient - single-plan chart).", "na")
chk("centene-m56-denials-0920", "5 PM ET 9/25: Sunshine remit 0917761409 (ERA 1052848) carried two more CO-16/M56 $0 lines on Sunshine-secondary Medicare-coinsurance residuals - pat21442 v19423425 99309 11/4/2025 and v19419546 99308 10/7/2025 - both charges already at $0 both sides (Medicare 819814877 paid 9/19, WOMCAD + WOCAID2ND 9/22), so nothing open and nothing added to the cluster total; the payer-id question on the SUN01 record stands.", "na")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(board, open("board_updates_%s.json" % S, "w"), indent=1)
# ---------------- needs section (pat ids only)
sec = """
## %s columns run (ehpa cloud Code Routine, run %s) - %s
- Bootstrap: repo ATTACHED (origin/main ebf95ef = the 1910Z run's last commit; session branch claude/pensive-einstein-z749b7, work done on main, symlinked as /home/claude/effinger-billing-backend); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread; ONE amd.login_cached success 21:19Z; no login lock; START marker uploaded 21:18Z. Layout from main (656 helpers; 372 registers from practices/ehpa/registers; needs list rebuilt from the 75 run sections in nightly/runs); pseudonyms (318 names), precheck cache, laterality log from 'workspace mirror'. bootstrap check: era_details_pull.py and columns_inspector2_0908.py MISSING from main (not rewritten; era_step_b_0913.py fills the era_details cache, insp_*.py scripts are the inspector template). Newest Drive state bundle still 2026-09-18_1123UTC (older than main - not unpacked). GITHUB INBOX: no unapplied PACKAGE_* manifest (only the 9/23 payer-sweep parts, APPLIED). Prompt v7 fired; v8 rules applied where they arise. Boards: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 19:00Z (query on updated), inbox registry lists none of the current inbox files - nothing trashed. Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked 0510Z 9/24). Watched folders: era downloads / treasury / facesheet folders / Claimocity drop - nothing new after the routine's own files; no ScanSnap batch.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d ($%s) | Unbilled %s -> %s ($%s) | Exclusions %d -> %d (list; overview %s/$%s lagging). No new row in any column since the 1910Z run; no claim run newer than 1700236; every row a standing hold (same 20 inspector error ids). Nothing cleared, nothing released, $0 re-sent.
- Claim Inspector holds (20, unchanged): pat17472874 x15 April-2026 HCA 'Hospitalization From Date empty' (admission date from William); pat17474541 v19430630 Pattern 15775 + 4426; pat17473477 v19455625 + pat45668 v19455691 deceased guard; pat20863 v19455936 CCI 24078; pat17477208 v19455940 duplicate CCM lines.
- Unbilled holds (26, unchanged): 16 pat17472874 + pat17474541 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; pat17477183 v19455471 + v19455759 (facesheet - William); pat17473232 v19455597 and pat17471681 v19455606 (CCM after DOD - William); pat17477639 v19455621 (no plan - William); pat17477842 v19455665 (duplicate chart - William: merge); pat17477850 v19455868 + v19455898 (CHP member id - William); pat17477870 v19456058 (duplicate chart - William: merge).
- EXCLUSIONS: 2 standing PDTP0303 holds unchanged (pat17472517 v19423193 HUM01 $70.17, pat20863 v19445850 FLO99 $14.38 - no 99223 anchor within 45 days); every other run lists 0.
- ERA step 5: %d unposted checks / $%.2f -> %d / $%.2f. Two new 835s: Ambetter AMB03 0934734717 (ERA 1052847, $115.80: pat17477799 v19455058 99223 paid 79.85, v19455032 99232 paid 35.95) and Sunshine SUN01 0917761409 (ERA 1052848, $166.26: pat17472703 v19455116 + v19455042 99233 paid 83.13 each, WOMCAD 76.87 each). era_post --all-unposted posted all 4 money lines (HTTP 200); fallback: 4 already-posted. CO-45 DEFECT on the Ambetter carrier too: the button posted the CO-45 reason with payreasonwoamount 0, patient balance = fee - paid -> era_co45_fix_2110.py: move_to_ins + manual_post pay 0 / WOINS 150.30 and 39.10 (check 0934734717, deposit 09/25/2026); PR-2 79.85 / 35.95 stay on the patient (chart has AMB03 only, seq 1). 5 denial-only $0 lines on 1052848: pat17471181 x3 CO-286 (99232 2/9, 2/10, 4/2/2025 - charges at $0 since the 2025-26 Sunshine payments + WOMCAD) and pat21442 x2 CO-16/M56 (Sunshine secondary, 99309 11/4/2025 + 99308 10/7/2025 - $0 since Medicare 819814877 9/19 + WOCAID2ND 9/22) - recorded in registers/era_manual_register.json, nothing posted. era_clear dismissed 1052848 (held lines = denial with write-off, cascade); 1052847 left the list on posting. After: 0 checks. Auto-posted $282.06 (4 lines), manual-posted 0 money lines, contractual corrections 2 lines $189.40 WOINS, write-offs by the button $153.74 WOMCAD, residual disregarded $0, checks cleared 2. Availity 5(g): no new PDF / Check-EFT export; no ScanSnap batch. payreasons --list: 0 rows.
- Dollars re-sent: $0. Insurance entered: none. Write-offs: WOINS $189.40 (Ambetter contractual, pat17477799), WOMCAD $153.74 (Sunshine contractual by the button, pat17472703).
- Calls learned: no new call shape (captured_calls_additions_2026-09-25_2110UTC-5pmET-ehpa-cloud.md, behaviours only).
- Mirror: %s
""" % (SLOT, S, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), insp_b, insp_a, ov.get("claiminspectoramount", "?"), ub_b, ub_a, sb.get("unbilled_totalamount", "?"), ex_b, ex_a, ova.get("exclusioncount", "?"), ova.get("exclusionamount", "?"), len(eb), eb_amt, len(ea), ea_amt, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(sec.strip() + "\n")
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    marker = "## %s columns run (ehpa cloud Code Routine, run %s)" % (SLOT, S)
    if marker in txt:
        txt = txt[:txt.index(marker)].rstrip() + "\n\n" + sec.strip() + "\n"
    else:
        txt = txt.rstrip() + "\n\n" + sec.strip() + "\n"
    open("needs_facesheet_list.md", "w").write(txt)
adds = """# captured_calls additions - run %s (5pm ET 9/25/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- getclaimcenteroverview at 21:19Z: chargereview 0 / inspector 20 ($3,846) / unbilled 26 ($5,252) / exclusions 8 ($1,268 - lags; per-run list = 2) / claimrunstatus 83 runs; newest claim run still 1700236. No new inspector batch since 19:20Z (batch 127789 gone after the 1910Z clear).
- GET /api/era/checks at 21:20Z: 2 unposted checks ($282.06) - AMB03 0934734717 (ERA 1052847, 2 lines) and SUN01 0917761409 (ERA 1052848, 7 lines: 2 money + 5 $0 denials). posterapayments (era_post --all-unposted) HTTP 200 on both; the AMB03 posts carried the CO45 + PR2 reasons on the payment with payreasonwoamount 0 (patient balance = fee - paid) - the same ERA-setup defect as Florida Blue (9/23), VA CCN (9/23), CAP07/UHC (9/25 1510Z): AMBETTER (car6802) now on the list of carriers whose Post-button lines need the contractual correction pass. The SUN01 posts carried WOMCAD 76.87 each (Sunshine's ERA setup writes the contractual off).
- Contractual correction shape reused (era_co45_fix_2110.py): move_to_ins.move(cid) -> insbalance = the whole patient balance; manual_post.post(cid, 'AMB03', 0.0, wo, 'WOINS', checknumber=<trace>, depositdate=<check date>) -> AMD transfers the PR-2 remainder back to the patient on its own (after: insbal 0, patbal = PR-2).
- era_clear: dismissed 1052848 with 5 held 'denial with write-off (cascade handles)' lines ($581 CO amounts) - all five on charges already at $0 both sides (CO-286 appeal-time-limit x3 on pat17471181, CO-16/M56 x2 on pat21442's Sunshine secondary). POST /api/era/locks/release-expired sent; payreasons --list 0 rows.
- amd.login_cached(): one relogin at 21:19Z from a fresh container (.session.json written, .amd_login_lock cleared on success).
""" % S
open("captured_calls_additions_2026-09-25_2110UTC-5pmET-ehpa-cloud.md", "w").write(adds)
dig = """# %s run digest - backend billing run, 5 PM ET 9/25 slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main ebf95ef; session branch claude/pensive-einstein-z749b7, work on main, clone symlinked as /home/claude/effinger-billing-backend); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread 1866ce7e2233e4c0; ONE amd.login_cached success 21:19Z; no login lock; START marker 21:18Z. Layout from main (656 helpers, 372 registers); pseudonyms (318 names), precheck cache, laterality log from 'workspace mirror'; needs list rebuilt from the 75 run sections in nightly/runs. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten). State bundle restored: none (newest Drive bundle 2026-09-18_1123UTC is older than main). GITHUB INBOX: no unapplied PACKAGE_* manifest.
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 19:00Z, inbox registry lists none of the current inbox files - nothing trashed; Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked); Drive: era downloads / treasury / facesheet folders / Claimocity drop unchanged; no ScanSnap batch; GitHub inbox: no unapplied package.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d | Unbilled %s -> %s ($%s) | Exclusions %d -> %d. No new row in any column since the 1910Z run; no claim run newer than 1700236; every row a standing hold. $0 re-sent.
- ERA: %d unposted checks / $%.2f -> %d / $%.2f. Two new 835s posted through the Post button: Ambetter 0934734717 (ERA 1052847, $115.80, 2 lines on pat17477799) and Sunshine 0917761409 (ERA 1052848, $166.26, 2 lines on pat17472703 + WOMCAD 153.74). Ambetter's two lines then needed the CO-45 correction (the button left the contractual on the patient balance): WOINS 150.30 + 39.10 with the trace number, PR-2 coinsurance 79.85 + 35.95 stays on the patient (single-plan chart). 5 denial-only $0 lines on the Sunshine check (3 x CO-286 pat17471181, 2 x CO-16/M56 pat21442 Sunshine secondary) all on charges already at $0 - recorded, nothing posted. 1052848 dismissed, 1052847 left the list on posting; ERA Center empty after. Availity 5(g): no new files. payreasons --list 0 rows.
- Board: board_updates_%s.json (appends only on aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918, centene-m56-denials-0920; no new rows) -> board inbox; inbox registry lists none of the current inbox files - nothing trashed; denials inbox: nothing queued, no file.
- Waiting on William (unchanged from the 1910Z digest): harlington-karina-17474434 (CHP CO-29 after recoupment: appeal or WOLATE $210.95), gillespie-janis-46678 (CHP PR-242 CCM $206: WONCS / statement / appeal), chp-coa1-17476603 (Lantern vs appeal, the 5/20 99223 $310), copeland-jules-17476021 (current Medicare MBI), osgood-maryann-17477870 (merge the duplicate chart), whitson-shane-17477639 facesheet, jarvis-marisa-17477842 duplicate chart, griffin-jayson-17477850 CHP member id, whitfield-rowan-17473232 + penhale-rupert-17471681 CCM after death, alcorn-alfred-17477183 facesheet, thackeray-kendrew-17472874 HCA admission date, AET12 carrier master, carrier ERA setups (CO-45 auto write-off - now also AMBETTER), deistchle 8/22 CCM CO-151, centene-m56-denials-0920, Optum Pay remits to download, prompt v8 + v9 insert not yet pasted into the routine (this run still fired with the v7 text).
- Calls learned: no new call shape (captured_calls_additions_2026-09-25_2110UTC-5pmET-ehpa-cloud.md - the AMB03 CO-45 Post-button behaviour recorded). Vocabulary entries added: 0.
- Mirror: %s
- Script errors: none.

RUN COMPLETE
""" % (S, insp_b, insp_a, ub_b, ub_a, sb.get("unbilled_totalamount", "?"), ex_b, ex_a, len(eb), eb_amt, len(ea), ea_amt, S, MIRROR)
os.makedirs("chat_history", exist_ok=True)
open("chat_history/%s run digest.md" % S, "w").write(dig)
print("wrote", csvname, "board ops", len(ops), "digest ok")
