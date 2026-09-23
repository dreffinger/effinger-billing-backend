# PLAIN ENGLISH (run outputs for the 11pm ET 9/22/2026 slot - ehpa cloud run 2026-09-23T0310Z)
# Decides: nothing. Reads this run's snapshots (columns before/after from scan_0912/summary_*.json, ERA before/after)
#   and writes: "_run report 9-22 2310.csv"; board_updates_2026-09-23T0310Z.json (a new row for the Oakes readmit chart
#   worked from Pam's email + checks appends on the standing rows); a needs_facesheet_list.md section; the chat-history
#   digest (--final, once mirror_result.txt exists).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-23T0310Z"; SRC = "11pm ET 9/22 columns run (ehpa cloud)"; W = "9/22"; SLOT = "11 PM ET 9/22"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
PHI = load("pam_readmit_0310.json", {"dob":"","uhc":"","mcd":""})
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", sb)
def cnt(s, k): return (s.get("overview") or {}).get(k, "?")
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount")
ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center was empty the whole run (GET /api/era/checks = [] at 03:21Z; the 9/22 evening chat session had posted 95 paper/virtual-card remit lines through the ERA Center and dismissed the checks before this run). Locks release-expired sent; era_details cache 0 (nothing to pull); era_post --all-unposted / fallback / era_clear not needed (0 checks); 0 addpayments faults; payreasons.py --list: 0 Unbilled reason-code rows. No new 835 / Availity PDF / Check-EFT export in 'bht Optum era downloads' / 'treasury payments' - the only new file there is a second copy of the Burnell progress note (BURNELL_MICAH_09012026 (1).pdf, 02:11Z 9/23 - not a remit, no action). No MA63/M76/M64 work. Nothing posted, dismissed, rebilled or written off." % (nb, ab, na, aa))
BOOT = ("Bootstrap: repo ATTACHED (origin/main fb8764b = the 0110Z run's mirror commit; session branch claude/pensive-einstein-co2ect), bootstrap net = AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0 -> .amd_cred.json, ONE amd.login_cached success 03:16Z (columns_scan_0912.py before), no login lock. Cross-container guard: the 0110Z START has its RUN COMPLETE digest (01:22Z); START marker 2026-09-23T0310Z uploaded 03:11Z, lock written 03:11Z. Layout: tools/bootstrap_workspace.sh layout copied 547 helpers from main into /home/claude/unbilled (carriers.json simple form, 124 codes; tesseract + poppler installed); registers = practices/ehpa/registers from main (283 files); needs_facesheet_list.md rebuilt from the 82 run sections in main; laterality_flag_log.md (Drive 9/22 11:45Z), precheck_cache.json (Drive 9/21 23:28Z, 28 pairs), pseudonyms.json (237 names, Drive 9/22 19:42Z) from 'workspace mirror'; bootstrap check: columns_inspector2_0908.py and era_details_pull.py absent from main (not rewritten; columns_scan_0912.py + era_step_b_0913.py do their work), github_sync.py optional. Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked; main carries every helper and register). Prompt v7 fired; v8 rules + the 9/22 DECEASED GUARD apply - no claim left this run. A chat session was working at the same time (paper-remits digest 03:11Z): its GitHub bundle was NOT yet in Drive 'github mirror' when this run mirrored, so its commit 33494b9 stays for the next run; its captured_calls_additions_2026-09-22_paper-remits-chat.md was merged into the registry by this run.")
COLS = ("Charge Review %s -> %s | Claim Inspector %d -> %d (all pat17472874, the April-2026 stay held for William's admission date - error ids 394797-394807 unchanged on the 7 batches 126638-126725, no new batch) | Unbilled %s -> %s (the known v19441047 MCAD $16.93 crossover hold) | Exclusions %d -> %d rows on every claim run (overview 1/$198 lagging; getclaimrunstatus 81 runs, newest still 1700216, AMD clock 9/21 21:09 - no nightly claim run has posted for 9/22 yet). No new charge-review visit, no new inspector batch, no new unbilled row, no new exclusion since the 0110Z run - nothing to edit, bypass, release or complete. AET12: HOLD per William 9/21 - not rebilled, not re-verified." % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount"), insp_b, insp_a, ub_b, ub_a, ex_b, ex_a))
OSGOOD = ("Pam's 01:33Z 9/23 email 'NA Oakes' (PCC Payer Information screen, phone photo): readmit at Oakes, existing chart pat17470849 (lookuppatient name + DOB match). Chart plan UNI20 plan carried a GROUP NUMBER (82976) - stripped per William's no-group rule (updateinsurance wrapped shape, success 1). AMD 271 on it: ACTIVE, HMO-POS AARP Medicare Advantage from UHC (H1045-041) = the sheet's 'UHC Levels' member number (same id), so UHC is primary (no Medicare plan needed). The sheet's Medicaid number was not on the chart: MCAD (car6113) added seq 2 -> AMD 271 ACTIVE, Full Medicaid, and Florida Medicaid names SMMC MMA Capitated + LTC = HUMANA MEDICAL PLAN INC, so HUM01 (car6285) with the Medicaid number added seq 3 -> AMD 271 ACTIVE 'MC MEDICAID GATE CAP DIR'. Patient insurance order set 1,3 (UHC MA primary, Humana Medicaid secondary; Medicaid FFS seq 2 kept on the chart, out of the default order). No visit on the columns yet (the Claimocity feed has not sent the readmit charges). Address line 1 is BLANK (street 5532 MOSSY TOP WAY sits in line 2; no phone on the chart): the captured line-1 PATCH answered 500 'Phone Type is required.' - a chart with no phone at all needs a phone type before AMD accepts the address; left for the next run / William's UI edit (PN3-0107 risk once a charge lands).")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="%s -> %s (getreviewcharges empty)" % (cnt(sb, "chargereviewcount"), cnt(sa, "chargereviewcount")))
add("Claim Inspector", "count", action="%d -> %d (no new batch; the 11 pat17472874 April-2026 visits held as before)" % (insp_b, insp_a))
add("Claim Inspector", "remaining", patient="pat17472874", dos="4/7-4/21/2026", carrier="WEL04", error="Hospitalization From Date empty x11", action="HELD - no 99223 within 45 days, no sibling visit carries the admission date -> board row thackeray-kendrew-17472874 on William's turn", amount="1763.00")
add("Unbilled", "count", action="%s -> %s (v19441047 held as before)" % (ub_b, ub_a))
add("Unbilled", "remaining", patient="pat17470743", visit="19441047", carrier="MCAD", error="A payment from the prior payor is required", action="held as before (MCAD crossover $16.93 behind a reversed Medicare payment 5/26/2026 - releasing would only hide it)", amount="16.93")
add("Exclusions", "count", action="%d -> %d rows on every claim run (81 runs, newest 1700216). AET12: HOLD per William 9/21." % (ex_b, ex_a))
add("ERA", "count", action="%d / $%.2f -> %d / $%.2f; ERA Center empty, nothing to post or clear" % (nb, ab, na, aa))
add("Insurance entered", "done", patient="pat17470849", carrier="UNI20 / MCAD / HUM01", action=OSGOOD)
add("Sources", "read", action="Pam Gmail (newer_than:2d has:attachment): one new admit email 01:33Z 9/23 (Oakes readmit, worked - row osgood-marian-17470849); the three 16:46Z 9/21 readmit records already worked. Drive: nothing new in the hca/tmh/PCC/Claimocity facesheet folders or 'treasury payments'; 'bht Optum era downloads' got a duplicate copy of the Burnell progress note (no action); the 9/22 chat session added 'paper remits 2026-09-22' + captured_calls_additions_2026-09-22_paper-remits-chat.md to project files (merged) and a paper-remits digest to chat history. Board drops 0; Working Denials queue 0; Insurance Refresh Board: the page applied the 0110Z inbox file 03:06-03:08Z 9/23 - no new William note (no row updated by William after 01:22Z).")
add("Routine", "note", action=BOOT)
add("Script errors", "none", action="none (addr_line1_fix.py on pat17470849 returned AMD's 500 'Phone Type is required.' - recorded, not a script fault)")
add("Open on William's turn", "note", patient="pat17470849", action="FYI: address line 1 blank on the Oakes readmit chart (street in line 2, no phone) - AMD refuses the API address fix without a phone type; a UI Edit-address (move 5532 MOSSY TOP WAY to line 1, add a phone) avoids a PN3-0107 bounce when the readmit charges land")
add("Open on William's turn", "note", patient="pat17476603", action="row chp-coa1-17476603: CHP CO-A1 (no remark) on the 5/21/2026 HCA 99232 ($111) - SurgeryPlus surgical episode (bill Lantern) or appeal CHP?")
add("Open on William's turn", "note", patient="pat17472874", action="HCA admission date for the 4/7-4/21/2026 stay (11 visits $1,763 held in the Claim Inspector) - post the date (or drop the HCA facesheet) on row thackeray-kendrew-17472874")
add("Open on William's turn", "note", patient="AWV PR-119 x2", action="row awv-pr119-0922: pat23617 + pat21885 G0439 7/13/2026 ($408) - appeal with the 11-full-months calculation, or WONCS")
add("Open on William's turn", "note", patient="UHC rejected claims", action="row uhc-rejected-claims-0922: the rejection reason for the 41 August-2026 UHC claims ($8,206)")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $806.78 on 7 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="FLO99 balances held per the 9/22 rule (paid by paper check into Square - reconcile before any write-off/reroute); FCC CO-26 x4 on pat24039 ($92.47)")
add("Open on William's turn", "note", patient="paper remits (chat 9/22)", action="from the chat digest: key the 33 Zelis virtual cards in Square (6 expire 9/30, $317.50 of $3,306.72); decide the Simply/Washington National double payment on pat17473010 v19449180 ($31.94); Optum records requests x2; UHC additional-info letter; Cigna recredentialing; push the paper-remits git bundle when it lands in 'github mirror' (not there yet at 03:2xZ)")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-22 2310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    op = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: op["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(op)
ops.append({"op": "upsert", "collection": "items", "id": "osgood-marian-17470849",
    "set": {"patient": "OSGOOD,MARIAN", "dob": PHI["dob"], "facility": "OAKES SOUTHWOOD", "amdid": "17470849", "mbi": "",
            "inscarrier": "UNI20 United Healthcare", "insid": PHI["uhc"],
            "insplans": "1st UNI20 United Healthcare %s (AARP Medicare Advantage HMO-POS) · 2nd MCAD Florida Medicaid %s · 3rd HUM01 Humana (Medicaid SMMC MMA/LTC) %s; patient order 1,3" % (PHI["uhc"], PHI["mcd"], PHI["mcd"]),
            "need": "None for billing - Oakes readmit 9/22 (Pam 'NA Oakes'): chart verified, group number stripped, Medicaid + Humana Medicaid plans added, order set UHC MA first / Humana Medicaid second; charges arrive with the Claimocity feed. FYI: address line 1 is blank (street in line 2, no phone) and AMD refuses the API address fix without a phone type - a UI Edit-address (line 1 = 5532 MOSSY TOP WAY, add a phone) avoids a PN3-0107 bounce.",
            "why": "Pam admit email 01:33Z 9/23 (PCC Payer Information screen): UHC Levels, Medicare A/B, Medicaid FL co-ins, managed care 'No' - the chart had UHC only, with a group number.",
            "amount": 0, "status": "claude", "created": NOW, "updated": NOW},
    "append": {"checks": [
        {"ok": "ok", "src": "AMD eligibility (free 271) - UNI20 ins9509924", "result": "ACTIVE - HMO-POS AARP MEDICARE ADVANTAGE FROM UHC (H1045-041), UHC 87726; group number 82976 stripped (no-group rule)", "when": W},
        {"ok": "ok", "src": "AMD eligibility (free 271) - MCAD ins9520530 (added)", "result": "ACTIVE Full Medicaid; SMMC MMA Capitated + LTC = HUMANA MEDICAL PLAN INC", "when": W},
        {"ok": "ok", "src": "AMD eligibility (free 271) - HUM01 ins9520531 (added, Medicaid id)", "result": "ACTIVE - MC MEDICAID GATE CAP DIR; patient insorder set 1,3", "when": W},
        {"ok": "no", "src": "AMD address PATCH (addr_line1_fix)", "result": "500 'Phone Type is required.' - chart has no phone; line 1 still blank", "when": W}],
        "notes": [{"who": "Claude", "text": "Created by the 11pm ET 9/22 run from Pam's Oakes readmit email. Plans and order are set; nothing needed from you unless you want to fix the address line 1 / phone in the UI.", "at": NOW}]}})
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700216 (9/21 21:09 AMD clock)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (only a duplicate copy of the Burnell progress note, 02:11Z 9/23); Working Denials queue 0; board drops 0; Pam Gmail: one new admit email 01:33Z 9/23 (Oakes readmit pat17470849 - worked, row osgood-marian-17470849). The 9/22 evening chat session posted 95 paper/virtual-card remit lines ($3,046.70) through the ERA Center and left it empty." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
app("thackeray-kendrew-17472874", "na", "%s: the 11 April-2026 visits (v19437843-v19439702, $1,763) are still held in the Claim Inspector - unchanged, still your turn for the HCA admission date." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 03:10-%s UTC 9/23, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (the page applied the 0110Z inbox file 03:06-03:08Z 9/23). Sources: Pam Gmail one new admit (Oakes readmit pat17470849, worked); Drive facesheet folders / treasury folder nothing new; 'bht Optum era downloads' holds a duplicate copy of the Burnell progress note (no action); the 9/22 chat session's paper-remits files (project files + chat history) read - its registry additions merged, its git bundle not yet on Drive.
Claim runs: none newer than 1700216 (9/21 21:09 AMD clock; 81 runs listed).
Columns: %s
Pam admit: %s
ERA step 5: %s
Write-offs: none. Rebilled: none. Insurance entered: pat17470849 MCAD seq 2 + HUM01 (Medicaid id) seq 3, UNI20 group number stripped, order 1,3 (all three 271 ACTIVE). No claim left this run. Board: new row osgood-marian-17470849 (Claude's turn); checks appended on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918, thackeray-kendrew-17472874.
Script errors: none (AMD 500 'Phone Type is required.' on the address PATCH for a chart with no phone - recorded).
NEEDS WILLIAM: (0) FYI pat17470849 address line 1 / phone (UI); (1) chp-coa1-17476603 - Lantern/SurgeryPlus bundle or appeal to CHP ($111); (2) board row thackeray-kendrew-17472874 - the HCA admission date for the 4/7-4/21/2026 stay (11 visits held, $1,763); (3) awv-pr119-0922 - appeal or WONCS on the two 7/13/2026 AWVs ($408); (4) uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206); (5) paste prompt v8; (6) AET12 carrier master (HOLD); (7) centene-m56-denials-0920 ($806.78 on 7 visits); (8) FCC balances (reconcile paper checks / Square before any FLO99 write-off; FCC CO-26 x4 on pat24039, $92.47); (9) paper remits (chat 9/22): key the 33 Zelis virtual cards in Square (6 expire 9/30), the Simply/Washington National double payment on v19449180, Optum records x2, UHC additional-info letter, Cigna recredentialing, push the paper-remits bundle when it lands in 'github mirror'; (10) pat17477777 rplan18462071 Pre-Auth # (UI); (11) 6 Optum Pay remits.
Calls learned: no new call shapes (lesson: the Edit-address PATCH answers 500 'Phone Type is required.' on a chart with no phone at all). Vocabulary: +1 entry (payments-era/upload-835, the multipart 835 import the 9/22 chat proved with synthetic 835s) = 55.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, COLS, OSGOOD, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(SEC)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("# %s run digest - backend billing run, %s slot (ehpa cloud)\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, SEC))
    print("final written")
