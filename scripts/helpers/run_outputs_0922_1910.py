# PLAIN ENGLISH (run outputs for the 3pm ET 9/22/2026 slot - ehpa cloud run 2026-09-22T1910Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, inspector register, payer-switch register, ERA before/after)
#   and writes: "_run report 9-22 1910.csv"; board_updates_2026-09-22T1910Z.json (one NEW row for the AARP payer-switch chart,
#   checks appends on the standing rows and on the two inspector-batch charts that already have rows); a needs_facesheet_list.md
#   section; the chat-history digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys, re
S = "2026-09-22T1910Z"; SRC = "3pm ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "3 PM ET 9/22"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
LOC = load("board_row_17471365_local.json", {"patient": "pat17471365", "dob": "", "mbi": "", "member": ""})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
insp = load("registers/insp_%s.json" % S, {"visits": [], "held": [], "left": []})
sw = load("registers/payer_switch_17471365_%s.json" % S, {"steps": []})
dc = load("registers/deceased_cache.json", {})
BATCH = {"19455444": ("20729", "99233", "9/20/2026", "FLO02", "160.00"), "19455445": ("20729", "99233", "9/19/2026", "FLO02", "160.00"), "19455446": ("20729", "99223+99497", "9/18/2026", "FLO02", "443.00"),
         "19455449": ("17475816", "99233", "9/20/2026", "BCBS", "160.00"), "19455450": ("17477557", "99233", "9/20/2026", "FLO02", "160.00"), "19455451": ("17477640", "99233", "9/20/2026", "HUM01", "160.00"),
         "19455452": ("17472703", "99233", "9/20/2026", "SUN01", "160.00"), "19455453": ("17477516", "99233", "9/20/2026", "FLO02", "160.00"), "19455454": ("17474741", "99233", "9/20/2026", "FLO02", "160.00"),
         "19455455": ("17477774", "99232", "9/20/2026", "UMR", "111.00"), "19455456": ("17470940", "99233", "9/20/2026", "FLO02", "160.00"), "19455457": ("23969", "99233", "9/20/2026", "FLO02", "160.00"),
         "19455459": ("17470950", "99232", "9/20/2026", "FLO02", "111.00"), "19455460": ("17476583", "99233", "9/20/2026", "FLO02", "160.00"), "19455461": ("17475638", "99233", "9/20/2026", "FLO02", "160.00"),
         "19455463": ("17477497", "99233", "9/20/2026", "FLO02", "160.00"), "19455464": ("17476667", "99239", "9/20/2026", "HUM01", "163.00"), "19455465": ("17476667", "99223+99497", "9/19/2026", "HUM01", "443.00"),
         "19455466": ("17471916", "99239", "9/20/2026", "UNI20", "163.00")}
tot = round(sum(f(v[4]) for v in BATCH.values()), 2)
adm = {}
for v in insp.get("visits", []):
    m = [s for s in v["steps"] if s.startswith("admission ")]
    adm[v["vid"]] = m[0].split(" ")[1] if m else "?"
dxfix = [v["vid"] for v in insp.get("visits", []) if any("ADD-I10" in s for s in v["steps"])]
flo_pids = sorted({p for p, *_ in BATCH.values()} & {p for p, c, d, car, a in BATCH.values() if car == "FLO02"})
dg = {p: (dc.get(p) or {}) for p in flo_pids}
dg_txt = "; ".join("pat%s %s (%s)" % (p, "DOD " + r["dod"] if r.get("dod") else "no death on record", r.get("checked", "-")) for p, r in dg.items())
unver = [p for p, r in dg.items() if not r.get("checked") == "2026-09-22"]
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. GET /api/era/checks was EMPTY at 19:29Z; locks release-expired sent; era_post --all-unposted: 0 checks; fallback dry+live: 0 lines; era_clear dry+live: 0 checks; no new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (the only new item there is your 'FCC checks & EOBs' folder + 'FCC open balances by patient (9-22-2026)' sheet, 06:30Z 9/22 - Treasury, not ERA); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows. Nothing posted, nothing dismissed, nothing written off." % (nb, ab, na, aa))
BOOT = ("Bootstrap: repo ATTACHED (origin/main df203df = the 1710Z run's mirror commit; session branch claude/pensive-einstein-1iyme6), bootstrap net = AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 19:17Z (columns_scan_0912.py before), no login lock. Cross-container guard: the 1710Z START has its RUN COMPLETE digest (17:31Z); START marker 2026-09-22T1910Z uploaded 19:11Z, lock written 19:10Z. Layout: tools/bootstrap_workspace.sh layout copied 537 helpers from main into /home/claude/unbilled (carriers.json simple form, 124 codes; tesseract + poppler installed); registers = practices/ehpa/registers from main (268 files, symlinked); needs_facesheet_list.md rebuilt from the 38 run sections in main; laterality_flag_log.md (Drive 9/22 11:45Z), precheck_cache.json (Drive 9/21 23:28Z), pseudonyms.json (231 names, Drive 15:29Z; 237 after this run) from 'workspace mirror'; bootstrap check: columns_inspector2_0908.py and era_details_pull.py absent from main (not rewritten; columns_scan_0912.py + era_step_b_0913.py do their work), github_sync.py optional. Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules (payreasons repair, ERA-linked fallback, sweep rule) + the 9/22 DECEASED GUARD applied - deceased_guard.check ran before every inspector resave (patched this run to send no Authorization header when the Stedi key file is absent, so the proxy credential is used - it had answered 'unverified' before).")
COLS = ("Charge Review 0 -> 0 | Claim Inspector 30 -> 11 (new HCA batch 127765: 19 visits on 17 charts, $%.2f, all 'Hospitalization From Date empty' - admission dates written and every visit resaved onhcfa=1, three Z96.6x-led visits took the add-I10 cascade first, Pattern 11256 bypassed + logged x3 (pat20729), Source-of-Payment advisory bypassed x1 (pat17477774); batch cleared. The 11 left are pat17472874's April-2026 stay held for William's admission date, error ids 394797-394807 unchanged) | Unbilled 1 -> 1 (the known v19441047 MCAD $16.93 crossover hold) | Exclusions 0 -> 2 -> 0 (two UNI20 'SUBSCRIBER AND SUBSCRIBER ID NOT FOUND' rows surfaced on run 1700216 during the run: pat17471365's Medicare-secondary residuals - the seq-2 plan was an AARP Medicare Supplement entered under UNI20; AAR01 added seq 3, UNI20 end-dated 10/14/2025, both visits re-sent freq-1 on seq 3, exclusions completed; overview 1/$198 lagging). getclaimrunstatus 82 runs, newest still 1700216 (AMD clock 9/21 21:09). AET12: HOLD per William 9/21 - not rebilled, not re-verified." % tot)
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty)")
add("Claim Inspector", "count", action="30 -> 11 (batch 127765 cleared: 19 visits / $%.2f; 11 pat17472874 April-2026 visits held as before)" % tot)
for vid, (pid, cpt, dos, car, amt) in BATCH.items():
    add("Claim Inspector", "cleared", patient="pat%s" % pid, dos=dos, carrier=car, error="Hospitalization From Date empty" + (" + Pattern 11256" if pid == "20729" else "") + (" + Source of Payment advisory" if pid == "17477774" else ""),
        action="admission %s written (hospitalizationfrom only), full-visit resave onhcfa=1%s%s; inspector clear -> queued for the next claim run" % (adm.get(vid, "?"), "; add-I10 cascade (Z96.6x was first) + freq1 rebill" if vid in dxfix else "", "; Pattern 11256 bypassed + logged" if pid == "20729" else ""), visit=vid, amount=amt)
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row thackeray-kendrew-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="1 -> 1 (v19441047 held as before)")
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026 - releasing would only hide it)", amount="16.93")
add("Exclusions", "count", action="0 -> 2 -> 0 on run 1700216 (both pat17471365, worked this run); every other claim run 0 rows. AET12: HOLD per William 9/21.")
for vid, cid, dos, cpt, amt in (("19422334", "23327672", "10/15/2025", "99349 GV", "20.86"), ("19423579", "23329181", "11/15/2025", "99487 GV", "25.90")):
    add("Exclusions", "cleared", patient="pat17471365", dos=dos, carrier="UNI20 -> AAR01", error="PA ACK RETURNED AS UNPROCESSABLE: SUBSCRIBER AND SUBSCRIBER ID NOT FOUND + PA MEMBER PICK REJECT (Medicare-secondary residual)",
        action="wrong UHC entity: AMD 271 names 'AARP SUPPLEMENTAL PLANS INS BY UNITEDHEALTHCARE', Stedi AARP 36273 = ACTIVE Medicare Supplement Plan F at DOS; AAR01 car6600 added seq 3 (same member id, no group), UNI20 end-dated 10/14/2025, visit insorder 1,3 + freq1 rebill seq 3 -> 204, exclusion completed", visit=vid, amount=amt)
add("ERA", "count", action=ERA_TXT)
add("Deceased guard", "note", action="FLO02 charts in batch 127765 checked before their resaves (Medicare record via Stedi MBILUNOSSN + cache): %s%s" % (dg_txt, ("; UNVERIFIED (lookup not recorded today): pat" + ", pat".join(unver)) if unver else "; none blocked, none unverified"))
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): only the three 16:46Z 9/21 readmit records already worked. Drive: nothing new in the hca/tmh/PCC/Claimocity facesheet folders or 'bht Optum era downloads' since 9/21; 'treasury payments' has your new 'FCC checks & EOBs' folder with 'FCC open balances by patient (9-22-2026)' (06:30Z 9/22, Treasury task). Board drops 0; Working Denials queue 0; Insurance Refresh Board: rows updated 16:55-16:57Z 9/22 are the board applying the 1512Z inbox file, no new William note.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17471365", action="FYI only: AMD's Medicare 271 on this chart answers AAA 71 'birth date does not match' and the Stedi MBI lookup by name/DOB misses (ERR 72) although Medicare paid the primaries - the chart DOB (%s) may differ from CMS" % LOC["dob"] + "; check the card when convenient (row vallance-judeth-17471365, on Claude's turn)")
add("Open on William's turn", "note", patient="pat17476603", action="row chp-coa1-17476603: CHP CO-A1 (no remark) on the 5/21/2026 HCA 99232 ($111) - CHP active, Lantern/SurgeryPlus listed as primary since 11/3/2025: SurgeryPlus surgical episode (bill Lantern) or appeal CHP?")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row thackeray-kendrew-17472874")
add("Open on William's turn", "note", patient="AWV PR-119 x2", action="row awv-pr119-0922: pat23617 + pat21885 G0439 7/13/2026 ($408) - appeal with the 11-full-months calculation, or WONCS")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 1910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, notes=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if notes: o["append"]["notes"] = [{"who": "Claude", "text": notes, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
# NEW row for the payer-switch chart (Claude's turn - watching AARP's answer)
ops.append({"op": "upsert", "collection": "items", "id": "vallance-judeth-17471365",
    "set": {"id": "vallance-judeth-17471365", "patient": LOC["patient"], "dob": LOC["dob"], "facility": "ALF / home visit (99349, CCM)", "amdid": "17471365", "mbi": LOC["mbi"],
            "inscarrier": "FLO02 Florida Medicare", "insid": LOC["mbi"], "insplans": "1st FLO02 Florida Medicare %s · 2nd UNI20 United Healthcare %s (ended 10/14/2025) · 3rd AAR01 Aarp %s" % (LOC["mbi"], LOC["member"], LOC["member"]),
            "need": "Watching: the two Medicare-secondary residuals ($46.76: 99349 10/15/2025 $20.86, 99487 11/15/2025 $25.90, both GV) that UHC rejected 'subscriber not found' on run 1700216 were re-sent 9/22 to AARP (AAR01, Medicare Supplement Plan F, ACTIVE per Stedi) as originals on sequence 3. Nothing for William unless AARP bounces them. FYI: AMD's Medicare 271 answers AAA 71 (birth date does not match) and the Stedi MBI lookup by name/DOB misses, although Medicare paid the primaries - the chart DOB may differ from CMS.",
            "why": "Exclusions 9/22 (run 1700216): 2 UNI20 rows 'PA ACK RETURNED AS UNPROCESSABLE - SUBSCRIBER AND SUBSCRIBER ID NOT FOUND' + 'PA MEMBER PICK REJECT' on Medicare-secondary residuals - the seq-2 plan was an AARP Medigap entered under the UHC commercial carrier (CPID 3429).",
            "amount": 46.76, "status": "claude", "created": NOW, "updated": NOW},
    "append": {"notes": [{"who": "Claude", "text": "Created by the 3pm ET 9/22 run. Lookup order: AMD 271 on the seq-2 plan named 'AARP SUPPLEMENTAL PLANS INS BY UNITEDHEALTHCARE'; Stedi AARP (36273) with the same member id = ACTIVE 'AARP MEDICARE SUPPLEMENT PLAN F' at DOS 10/15/2025; UHC 87726 = no plan. AAR01 car6600 added (ins9519517, seq 3, begin 05/03/2023, no group), UNI20 ins9510649 end-dated 10/14/2025, visits 19422334 + 19423579 insorder 1,3 and freq-1 rebilled on seq 3 (204 x2), both exclusions on run 1700216 completed (0 rows left).", "at": NOW}],
               "checks": [{"ok": "no", "src": "AMD eligibility (free 271) - Medicare seq 1", "result": "REJECTED AAA 71 (birth date does not match) - Medicare still paid the primaries on check 819814877", "when": W},
                          {"ok": "ok", "src": "AMD eligibility (free 271) - UNI20 seq 2", "result": "no plan status; other payer named: AARP SUPPLEMENTAL PLANS INS BY UNITEDHEALTHCARE", "when": W},
                          {"ok": "ok", "src": "Stedi eligibility (AARP 36273) DOS 10/15/2025", "result": "ACTIVE - AARP MEDICARE SUPPLEMENT PLAN F, member %s" % LOC["member"], "when": W},
                          {"ok": "no", "src": "Stedi eligibility (UHC 87726) DOS 10/15/2025", "result": "no plan returned", "when": W},
                          {"ok": "no", "src": "Stedi MBI lookup (name/DOB, FL)", "result": "ERR 72 - not found by name/DOB (chart DOB %s)" % LOC["dob"], "when": W},
                          {"ok": "ok", "src": SRC, "result": "AAR01 seq 3 added (no group), UNI20 end-dated 10/14/2025, v19422334 + v19423579 insorder 1,3 + freq1 rebill seq 3 -> 204, exclusions 1700216 completed", "when": W}]}})
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows (the two rows that surfaced on 1700216 were pat17471365's UHC/AARP secondaries, not AET12); no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (only your new 'FCC checks & EOBs' folder + FCC open balances sheet, 06:30Z 9/22 - Treasury); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - unchanged since 1710Z, still your turn for the HCA admission date. (A new HCA batch of 19 other charts' 9/18-9/20 visits was cleared this run.)" % SLOT)
app("lisle-keziah-17477774", "ok", "New HCA 99232 visit 9/20/2026 (v19455455, $111, UMR): Z96.641 was the only diagnosis (secondary-only Z code) - I10 added in front per your primary-dx rule + freq-1, admission 09/14/2026 written, full-visit resave onhcfa=1, the Source-of-Payment advisory bypassed; inspector clear, queued for the next claim run.", notes="9/20 visit released with I10 leading (the feed sent only the joint-replacement status code); nothing needed from you.")
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 19:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note. Sources: Pam Gmail nothing new; Drive facesheet folders / 835 folders nothing new; 'treasury payments' has William's new 'FCC checks & EOBs' folder (06:30Z 9/22).
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock; 82 runs listed).
Columns: %s
ERA step 5: %s
Deceased guard: %s%s
Write-offs: none. Rebilled: pat17471365 v19422334 + v19423579 (freq-1 on the new AAR01 seq 3, $46.76) and the three add-I10 visits of batch 127765 (v19455449, v19455455, v19455459 - dx_primary_fix freq-1 rebill). Insurance entered: AAR01 (AARP Medicare Supplement Plan F, Stedi ACTIVE) seq 3 on pat17471365; UNI20 end-dated 10/14/2025. Claims released: the 19 HCA visits of batch 127765 ($%.2f) leave on the next claim run.
Board: new row vallance-judeth-17471365 (Claude's turn, watching); checks appended on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918, thackeray-kendrew-17472874, lisle-keziah-17477774.
Script errors: none.
NEEDS WILLIAM: (0) chp-coa1-17476603 - Lantern/SurgeryPlus bundle or appeal to CHP ($111); (1) board row thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (2) awv-pr119-0922 - appeal or WONCS on the two 7/13/2026 AWVs ($408); (3) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (4) paste prompt v8; (5) AET12 carrier master (HOLD); (6) centene-m56-denials-0920 ($772.92); (7) FCC balances (reconcile paper checks / Square before any FLO99 write-off); (8) pat17477777 rplan18462071 Pre-Auth # (UI); (9) 6 Optum Pay remits; (10) FYI pat17471365 chart DOB vs CMS (AAA 71).
Calls learned: no new call shapes (deceased_guard.py patched for the proxy-attached Stedi credential; payer-switch lesson recorded in the additions file). Vocabulary unchanged (54).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT, dg_txt, ("; UNVERIFIED: pat" + ", pat".join(unver)) if unver else "; none blocked, none unverified", tot, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("# %s run digest - backend billing run, %s slot (ehpa cloud)\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, SEC))
    print("final written")
else:
    print("csv rows", len(rows), "| board ops", len(ops), "| deceased:", dg_txt, "| unverified:", unver)
