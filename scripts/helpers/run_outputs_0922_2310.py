# PLAIN ENGLISH (run outputs for the 7pm ET 9/22/2026 slot - ehpa cloud run 2026-09-22T2310Z)
# Decides: nothing. Reads this run's snapshots (columns before/after from scan_0912/summary_*.json, ERA before/after,
#   the 1051741 denial register) and writes: "_run report 9-22 2310.csv"; board_updates_2026-09-22T2310Z.json (checks
#   appends on the standing rows + a checks/notes append on centene-m56-denials-0920 for the two new M56 lines);
#   a needs_facesheet_list.md section; the chat-history digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-22T2310Z"; SRC = "7pm ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "7 PM ET 9/22"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", {})
def cnt(s, k): return (s.get("overview") or {}).get(k, "?")
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount")
ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
den = load("registers/era_denials_1051741_%s.json" % S, {"lines": [], "posted": []})
ERA_TXT = ("%d unposted check / $%.2f before -> %d / $%.2f after. NEW Centene check 1051741 (AMD label FLO99, trace 0917735332, check date 9/22, $83.13, 9 claims on 6 charts): the ERA Center Post button (era_post --all-unposted) posted its one paid line - pat17472703 v19454648 99233 9/13/2026 $83.13 + CO45 $76.87 WOMCAD with the reason code (HTTP 200; fallback dry+live read it back as already-posted, 0 faults, residual $0). Its 8 $0 denial lines, each read live (gettxhistory): 4 x FCC CO-26 'prior to coverage' on pat24039's Medicare-coinsurance residuals (v19453377 $21.80, v19453357 $16.93, v19453215 $31.94, v19453385 $21.80 = $92.47 open to FCC seq 2; Medicare paid + WOINS posted 9/11-9/15) - HELD per your 9/22 FCC rule (reconcile paper checks/Square before any write-off or reroute; same FCC-dual group as 9/21); 2 x Sunshine CO-16/M56 on Medicare-coinsurance residuals (pat17472286 v19453355 $16.93, pat20729 v19453356 $16.93) - HELD, joined to the centene-m56-denials-0920 cluster (SUN01 payer-id question on your turn); 2 already settled at $0 (pat12231996 v19417241 CO-109 - WEL04 paid 9/15 + Medicaid crossover 9/21; pat17469541 v19444472 CO-16 - WOMCAD 9/15). No MA63/M76/M64. era_clear dismissed 1051741 (no postable money left); GET /api/era/checks after = 0. Locks release-expired sent; no new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 9/22 00:10Z outside the routine's own files); payreasons.py --list: 0 Unbilled reason-code rows. Nothing written off, nothing rebilled." % (nb, ab, na, aa))
BOOT = ("Bootstrap: repo ATTACHED (origin/main 5b4f839 = the 2110Z run's mirror commit; session branch claude/pensive-einstein-vltie0), bootstrap net = AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 23:19Z (columns_scan_0912.py before), no login lock. Cross-container guard: the 2110Z START has its RUN COMPLETE digest (21:23Z); START marker 2026-09-22T2310Z uploaded 23:13Z, lock written 23:13Z. Layout: tools/bootstrap_workspace.sh layout copied 543 helpers from main into /home/claude/unbilled (carriers.json simple form, 124 codes; tesseract + poppler installed); registers = practices/ehpa/registers from main (278 files, symlinked); needs_facesheet_list.md rebuilt from the 80 run sections in main; laterality_flag_log.md (Drive 9/22 11:45Z), precheck_cache.json (Drive 9/21 23:28Z), pseudonyms.json (237 names, Drive 19:42Z) from 'workspace mirror'; bootstrap check: columns_inspector2_0908.py and era_details_pull.py absent from main (not rewritten; columns_scan_0912.py + era_step_b_0913.py do their work), github_sync.py optional. Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules (payreasons repair, ERA-linked fallback, sweep rule) + the 9/22 DECEASED GUARD apply - no claim left this run, so no date-of-death lookup was needed.")
COLS = ("Charge Review %s -> %s | Claim Inspector %d -> %d (all pat17472874, the April-2026 stay held for William's admission date - error ids 394797-394807 unchanged on the 7 batches 126638-126725, no new batch) | Unbilled %s -> %s (the known v19441047 MCAD $16.93 crossover hold) | Exclusions %d -> %d rows on every claim run (overview 1/$198 lagging; getclaimrunstatus 82 runs, newest still 1700216, AMD clock 9/21 21:09 - no nightly claim run has posted for 9/22 yet). No new charge-review visit, no new inspector batch, no new unbilled row, no new exclusion since the 2110Z run - nothing to edit, bypass, release or complete. AET12: HOLD per William 9/21 - not rebilled, not re-verified." % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a))
PRECHECK = "7pm precheck --days 3 --max 120: 17 patient/payer pairs (2 new lookups), 0 flagged. 'current face sheets needed' email sent to dreffinger@gmail.com (none needed today)."
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="%s -> %s (getreviewcharges empty)" % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount")))
add("Claim Inspector", "count", action="%d -> %d (no new batch; the 11 pat17472874 April-2026 visits held as before)" % (insp_b, insp_a))
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row thackeray-kendrew-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="%s -> %s (v19441047 held as before)" % (ub_b, ub_a))
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026 - releasing would only hide it)", amount="16.93")
add("Exclusions", "count", action="%d -> %d rows on every claim run (82 runs, newest 1700216). AET12: HOLD per William 9/21." % (ex_b, ex_a))
add("ERA", "count", action="%d / $%.2f -> %d / $%.2f; check 1051741 auto-posted $83.13, 8 denial lines worked, dismissed" % (nb, ab, na, aa))
for p in den.get("posted", []):
    add("ERA", "auto-posted", patient="pat%s" % p["pid"], dos=p["dos"], carrier="SUN01", visit=p["visitid"], check="1051741", payer="Centene 0917735332", amount="%.2f" % p["paid"], action="%s (CO45 %.2f WOMCAD)" % (p["outcome"], p["wo"]))
for l in den.get("lines", []):
    add("ERA", l["outcome"], patient="pat%s" % l["pid"], dos=l["dos"], carrier="", visit=l["visitid"], check="1051741", payer="Centene 0917735332", error="%s/%s $%.2f" % (l["carc"], l["rarc"], l["amount"]), amount="%.2f open" % l["open"], action=l["why"])
add("ERA", "cleared", check="1051741", payer="Centene 0917735332", action=den.get("cleared", ""))
add("7pm extras", "precheck", action=PRECHECK)
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): only the three 16:46Z 9/21 readmit records already worked. Drive: nothing modified after 12:00Z 9/22 in the hca/tmh/PCC/Claimocity facesheet folders, 'bht Optum era downloads', 'treasury payments' or the parent except the routine's own additions files. Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated after 23:08Z 9/22 (the page applied the day's inbox files at 23:06-23:08Z) - no new William note.")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none")
add("Open on William's turn", "note", patient="pat17476603", action="row chp-coa1-17476603: CHP CO-A1 (no remark) on the 5/21/2026 HCA 99232 ($111) - SurgeryPlus surgical episode (bill Lantern) or appeal CHP?")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row thackeray-kendrew-17472874")
add("Open on William's turn", "note", patient="AWV PR-119 x2", action="row awv-pr119-0922: pat23617 + pat21885 G0439 7/13/2026 ($408) - appeal with the 11-full-months calculation, or WONCS")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - now $806.78 on 7 visits (two more $16.93 M56 lines tonight: pat17472286 v19453355, pat20729 v19453356)")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute); tonight FCC answered CO-26 on pat24039's four coinsurance residuals ($92.47)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
add("Open on William's turn", "note", patient="pat17471365", action="FYI only: AMD's Medicare 271 answers AAA 71 'birth date does not match' although Medicare paid the primaries - check the card when convenient (row vallance-judeth-17471365)")
with open("_run report 9-22 2310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    op = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: op["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(op)
app("era-manual-post-0912", "ok", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 00:10Z 9/22 outside the routine's own files); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked. 7pm precheck --days 3: 17 pairs, 0 flagged; 'current face sheets needed' email sent (none needed today)." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - unchanged since 1910Z, still your turn for the HCA admission date." % SLOT)
app("centene-m56-denials-0920", "no", "%s: Centene check 1051741 (0917735332, 9/22) answered two more CO-16/M56 lines on Medicare-coinsurance residuals billed to the Sunshine secondary - pat17472286 v19453355 99309 8/27/2026 $16.93 and pat20729 v19453356 99309 8/27/2026 $16.93 (Medicare 819785160 paid 66.36 + WOINS 57.71 on each). Held with the cluster; nothing re-sent or written off. Cluster now 7 visits / $806.78." % SLOT,
    note="Two more Sunshine M56 lines tonight ($33.86 total, coinsurance residuals) - same SUN01 payer-id question; held with this row.")
app("varley-hilda-open", "na", "%s: FCC (car42008) answered CO-26 'expenses incurred prior to coverage' on four of pat24039's Medicare-coinsurance residuals billed to FCC (not this chart) - noted here only as the FCC-dual pattern; nothing changed on this row." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 23:10-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (no row updated after 23:08Z 9/22; the page applied the day's inbox files 23:06-23:08Z). Sources: Pam Gmail nothing new; Drive facesheet folders / 835 folders / treasury folder nothing new.
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock; 82 runs listed).
Columns: %s
ERA step 5: %s
7pm extras: %s
Write-offs: none. Rebilled: none. Insurance entered: none. No claim left this run. Board: no new row; checks appended on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918, thackeray-kendrew-17472874, centene-m56-denials-0920 (+note), varley-hilda-open.
Script errors: none.
NEEDS WILLIAM: (0) chp-coa1-17476603 - Lantern/SurgeryPlus bundle or appeal to CHP ($111); (1) board row thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (2) awv-pr119-0922 - appeal or WONCS on the two 7/13/2026 AWVs ($408); (3) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (4) paste prompt v8; (5) AET12 carrier master (HOLD); (6) centene-m56-denials-0920 (now $806.78 on 7 visits); (7) FCC balances (reconcile paper checks / Square before any FLO99 write-off; FCC CO-26 x4 tonight on pat24039, $92.47); (8) pat17477777 rplan18462071 Pre-Auth # (UI); (9) 6 Optum Pay remits; (10) FYI pat17471365 chart DOB vs CMS (AAA 71).
Calls learned: no new call shapes. Vocabulary unchanged (54).
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, ERA_TXT, PRECHECK, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("# %s run digest - backend billing run, %s slot (ehpa cloud)\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, SEC))
    print("final written")
