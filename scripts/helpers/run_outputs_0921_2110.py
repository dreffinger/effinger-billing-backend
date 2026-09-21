# PLAIN ENGLISH (run outputs for the 5pm ET 9/21/2026 slot - ehpa cloud run 2026-09-21T2110Z)
# Decides: nothing. Reads this run's snapshots and registers and writes: "_run report 9-21 2110.csv"; board_updates_2026-09-21T2110Z.json
#   (checks/notes appends + one new row on William's turn for the N286 referring-provider cluster); a needs_facesheet_list.md section; the
#   chat-history digest (--final, after mirror_result.txt exists). Never touches: AMD, the board databases. Chart ids only - no patient names.
import csv, json, os, datetime, sys
S = "2026-09-21T2110Z"; SRC = "5pm ET 9/21 columns run (ehpa cloud)"; W = "9/21"; SLOT = "5 PM ET 9/21"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {}) or before
ova = after.get("overview", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
act = load("registers/era_1051726_act_%s.json" % S, [])
ERA_TXT = ("%d unposted check / $%.2f before -> %d / $%.2f after. New: Florida Medicaid check 1051726 (073041757, $0.00, 44 $0 denial claims). Post button: nothing postable (no money). Denial handling line by line after a live read of every visit + AMD 271 on 15 charts: WOLATE x5 $363.06 (2024 never-paid primaries: pat24344 x2, pat44976 x2, pat17469525); WOINS x5 $448.93 (Medicare CO45 contractual never adjusted on pat17473346 / pat17477607 / pat17477023; pat17477417 x2 deceased 6/22/2026, Medicaid FFS CO256 on the crossover); WOCAID2ND x3 $68.33 (dual coinsurance after a $0 Medicaid crossover: pat44955, pat45049, pat12231996 deceased); 3 wrong-order Medicaid-primary claims re-routed + freq-1 rebilled 204 (pat17477184 v19454398 -> Medicare seq 2; pat17469645 v19454249 -> UHC Dual Complete seq 3, the 271's H2509 D-SNP; pat23161 v19454225 -> FCC seq 2 per the SMMC rule; patient insurance orders set 2,3 / 3,1 / 2,3); 27 lines held: 8 FCC-dual coinsurance lines $180.07 (pat24039 x6, pat20863 x2 - Medicaid FFS answers the CMS crossover CO256 'managed care' because the patient is in FCC's MMA; FCC never pays, AAA 41 - FCC contracting item), Sunshine / United American / CHP secondaries in play (pat17473346 x2, pat17477383, pat17471131, pat17477607, pat17477023), the 9 prof13 CO208/N286 lines ($1,269, board row), 3 already at $0, 1 visit with no live charge. era_clear dismissed 1051726 (34 unvalidated $0 + 10 denial-with-writeoff lines); ERA Center empty after. INCIDENT + RECOVERY: an attempt to move 7 SLMB-only coinsurance lines on pat17477184 to the patient balance by resave (insportion=0) UNAPPLIED their 9/17 Medicare hand posts and voided the WOINS; recovered the same run - 7 unapplied credits voided (voidpayment), balances moved back to insurance, the 7 Medicare lines re-posted as they were (check 819803392: 66.36+WOINS 57.71 x6, 63.28+WOINS 126.58) - every charge verified: insurance balance 0, coinsurance 16.93/16.14 on the patient balance (correct for SLMB), payments live; reason codes still missing on those 7 (checkdetails for 1051693 no longer carries the posted lines) - lesson written to rules.md, never again. Locks release-expired sent; 0 addpayments faults; no new 835 / Availity file; no MA63/M76/M64 work." % (nb, ab, na, aa))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after; no new HCA feed batch this slot)")
add("Unbilled", "count", action="0 -> 0 (getclaimunbillablecharges totalcount 0 before and after; payreasons rows 0)")
add("Exclusions", "count", action="0 -> 0 rows on the per-run list calls (81 claim runs; overview 1/$198.00 lagging; no claim run newer than 1700211 at 9/20 02:04 AMD clock - no nightly claim run posted for 9/20 evening or 9/21). AET12: HOLD per William 9/21 - not rebilled, not re-verified this slot.")
add("ERA", "count", action=ERA_TXT)
for r in act:
    o = r["outcome"]
    add("ERA", "cleared" if o.startswith("writeoff") or o in ("rerouted-rebilled",) else ("held" if o == "held" else o), "pat%s" % r.get("pid"), "", r.get("carrier", ""), (r.get("why") or "")[:200], o + ("" if not r.get("code") else " " + r["code"]), "1051726", "FL Medicaid", r.get("vid", ""), r.get("amount", ""))
add("ERA", "recovered", "pat17477184", "", "FLO02", "7 Medicare hand posts unapplied by this run's to-patient resave", "voidpayment x7 + move_to_ins x7 + manual_post re-post x7 (check 819803392); verified ins 0 / pat 16.93 x6, 16.14 x1", "1051693", "Medicare", "19451189,19453359,19452834,19452073,19451568,19451541,19452413", "461.44")
add("Sources", "read", action="Pam Gmail: no admit email newer than the three Brynwood readmit records of 16:46Z 9/21 (worked by the 1910Z run). Six watched Drive folders: nothing modified after 12:00Z 9/21 except the routine's own files. Claimocity drop: nothing. Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated after 15:38Z (no new William note).")
add("Boards", "read", action="Board inbox: 21 files present (9/20 0345Z - 9/21 1910Z), none in the board's applied map (registry lastCheck 06:36Z 9/21) - nothing trashed.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main d2edb69, session branch claude/pensive-einstein-bev0bx), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 1910Z run's START has its RUN COMPLETE digest (19:37Z); proceeded 21:16Z. Registers from practices/ehpa/registers (217 files); needs_facesheet_list.md (Drive 07:50Z + the 0910Z/1110Z/1310Z/1910Z sections from main) / precheck_cache.json / laterality_flag_log.md / pseudonyms.json (223 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired; v8 (Drive 06:30Z, on main) not yet pasted - its rules followed.")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="medicaid-n286 cluster (pat17472419 x2, pat17472518 x7)", action="9 Medicaid-primary 99309s re-created under Effinger 9/13 ($1,269) deny CO208/N286 (NPI not matched / referring provider identifier) - check the referring provider on those visits' referral plan in the UI (Garcia's NPI is not on Medicaid's file), then say 'rebill' on the board row")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits (+ pat17473346's two coinsurance residuals wait on the same answer)")
add("Open on William's turn", "note", patient="FCC (car42008)", action="Medicaid FFS answers every FCC-dual crossover CO256 'managed care contract' - FCC (the MMA) has never paid and answers AAA 41; 8 coinsurance lines $180.07 held (pat24039, pat20863) - FCC contracting / payer id (credentialing item)")
add("Open on William's turn", "note", patient="Automation Center", action="no nightly claim run since 1700211 (9/20 02:04) - the EOD close looks stopped again; the 3 rebills of this run wait on it")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-21 2110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700211 (9/20 02:04) - no nightly claim run has posted for 9/20 evening or 9/21." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 12:00Z 9/21 outside the routine's own files) - nothing to parse, post or reconcile; Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("centene-m56-denials-0920", "na", "%s: Florida Medicaid FFS (check 1051726) also answered CO16/N290 on pat17473346 v19453034 and pat17477383 v19451168 - the same coinsurance residuals whose Sunshine crossover Centene denied M56. The 57.71 Medicare contractual on v19453034 was written off WOINS; the 16.93 coinsurance lines wait on the SUN01 payer-id answer." % SLOT)
app("varley-hilda-open", "ok", "%s: the 9/1/2026 99308 (v19454225, $107) had gone to Medicaid FFS as primary and denied CO256/N130 (managed care); AMD 271 names SMMC MMA Capitated FLORIDA COMMUNITY CARE -> patient insurance order set 2,3 (FCC then Medicaid), visit moved to FCC seq 2 and freq-1 rebilled (204). No GV added (no hospice denial on it)." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker) - hold Florida Blue patient statements." % SLOT)
ops.append({"op": "upsert", "collection": "items", "id": "medicaid-n286-referring-provider-0921", "set": {"patient": "FL MEDICAID CO208/N286 CLUSTER (2 charts)", "dob": "", "facility": "ALF / home visits (99309)", "amdid": "17472419, 17472518", "mbi": "", "inscarrier": "MCAD Florida Medicaid", "insid": "", "insplans": "", "amount": 1269, "status": "william", "created": NOW,
    "need": "WILLIAM: Florida Medicaid FFS (ERA check 1051726, 9/21) denied 9 Medicaid-primary 99309s CO208 'NPI not matched' + N286 'missing/incomplete/invalid referring provider primary identifier' - $1,269: pat17472419 v19454237 (2/2/2026) + v19454238 (1/2/2026); pat17472518 v19454239-v19454245 (10/2/2025, 11/3/2025, 12/5/2025, 2/6/2026, 3/2/2026, 4/9/2026, 5/11/2026). All nine are the visits re-created under your rendering profile (prof13) on 9/13; on this remit EVERY Effinger-rendered Medicaid claim answers N286 while every Garcia-rendered one answers N290 (rendering provider) - so the referring provider loop on the re-created visits carries an NPI Medicaid cannot match (most likely Pam Garcia as the referring provider on the referral plan the re-creation kept). Please open one of these visits' referral plan in the UI and set the referring provider to yourself / self-referral (or tell me which value), then say 'rebill' here and the run re-sends all nine freq-1 on the Medicaid sequence. Not rebilled, not written off (the 10/2 and 11/3/2025 dates reach 12 months in October/November).",
    "why": "ERA step 5 of the 5pm ET 9/21 run: 9 of the 44 $0 denial lines on Florida Medicaid check 1051726; the referral-plan referring provider is not a captured API write.", "notes": [{"who": "Claude", "text": "Created by the 5pm ET 9/21 run. Your turn: the referring provider on the re-created visits (UI), then 'rebill'.", "at": NOW}]},
    "append": {"checks": [{"ok": "no", "src": SRC, "result": "9 lines CO208/N286 on prof13 Medicaid-primary 99309s ($1,269) held; 24 CO16/N290 lines on Garcia-rendered lines were secondary residuals (worked) or the one primary re-routed to Medicare", "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 21:09-%s UTC 9/21, run %s)
Bootstrap: repo ATTACHED (origin/main d2edb69, session branch claude/pensive-einstein-bev0bx), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: the 1910Z run's START has its RUN COMPLETE digest (19:37Z); proceeded 21:16Z. Registers from practices/ehpa/registers (217 files); needs_facesheet_list.md / precheck_cache.json / laterality_flag_log.md / pseudonyms.json (223 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired (v8 on Drive and main, not yet pasted; its rules followed).
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no row updated after 15:38Z. Sources: six watched Drive folders hold nothing modified after 12:00Z 9/21 outside the routine's own files; Claimocity drop: nothing; Pam Gmail: nothing newer than the three 16:46Z readmit records (worked 1910Z).
Claim runs: none newer than 1700211 (9/20 02:04 AMD clock; 81 runs) - no nightly claim run posted for 9/20 evening or 9/21.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 0 -> 0 | Exclusions 0 -> 0 rows (overview 1/$198 lagging). AET12: HOLD.
ERA step 5: %s
Write-offs: WOLATE $363.06 (pat24344 61.57 + 62.58; pat44976 44.34 + 133.00; pat17469525 61.57), WOINS $448.93 (pat17473346 57.71; pat17477607 57.71; pat17477023 126.58; pat17477417 126.26 + 80.67), WOCAID2ND $68.33 (pat44955 16.93; pat45049 17.65; pat12231996 33.75). Rebilled: 3 re-routed primaries freq-1 (v19454398 Medicare $141, v19454249 UHC Dual Complete $107, v19454225 FCC $107). Insurance entered: none (3 patient insurance orders set).
NEEDS WILLIAM: (1) paste prompt v8; (2) board row medicaid-n286-referring-provider-0921 ($1,269, 9 visits) - referring provider on the re-created Effinger visits, then 'rebill'; (3) AET12 carrier master (HOLD); (4) centene-m56-denials-0920 ($772.92 + pat17473346's residuals); (5) FCC contracting - Medicaid FFS answers every FCC-dual crossover CO256 (8 lines $180.07 held); (6) nightly claim run stopped again after 1700211; (7) pat17477777 rplan18462071 Pre-Auth # (UI); (8) 6 Optum Pay remits; (9) BCBS patient-balance audit parked.
Calls learned: no new call shapes (voidpayment on an unapplied credit, move_to_ins, manual_post, updateinsurance sequence=patient insorder, chargerebill, era dismiss reused); LESSON in rules.md: a resave with insportion=0 unapplies the charge's payment and voids its write-off - never used again for an insurance-to-patient transfer. Vocabulary unchanged (54).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-21_2110UTC run digest - backend billing run, 5 PM ET 9/21 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, centene-m56-denials-0920, varley-hilda-open, bcbs-patient-balance-audit-0918; one new row medicaid-n286-referring-provider-0921 on William's turn) uploaded; nothing trashed (none of the 21 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0 (54 calls). Postman: unchanged.
Mirror: %s
State bundle: not uploaded (every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers)

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-21_2110UTC run digest.md", "w").write(dig)
    if S not in open("needs_facesheet_list.md").read():
        with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
