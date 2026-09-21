# PLAIN ENGLISH (run outputs for the 3pm ET 9/21/2026 slot - ehpa cloud run 2026-09-21T1910Z)
# Decides: nothing. Reads this run's snapshots (columns before/after, ERA before/after, the inspector register) and writes:
#   "_run report 9-21 1910.csv"; board_updates_2026-09-21T1910Z.json (checks/notes appends + one new row for pat20863);
#   a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only (patNNN) - no patient names.
import csv, json, os, datetime, sys
S = "2026-09-21T1910Z"; SRC = "3pm ET 9/21 columns run (ehpa cloud)"; W = "9/21"; SLOT = "3 PM ET 9/21"
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
ib = sum(len(v) for v in before.get("inspector", {}).values()); ia = sum(len(v) for v in after.get("inspector", {}).values())
exb = sum(len(v) for v in before.get("exclusions", {}).values()); exa = sum(len(v) for v in after.get("exclusions", {}).values())
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
insp = load("registers/insp_%s.json" % S, {})
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty. Locks release-expired sent; era_post --all-unposted 0 checks; fallback (payreasons.post_line, ERA-linked) dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835 in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (the six watched folders hold nothing modified after 12:00Z 9/20 except mercy.pdf, worked 0510Z); no MA63/M76/M64 work; ERA cache 0 (nothing to pull)." % (nb, ab, na, aa))
INSP_TXT = ("%d -> %d rows (overview %s/$%s lagging): one new HCA feed batch 127755 - 20 hospital visits (DOS 9/18-9/20/2026) on 18 charts, every one held 'Hospitalization From Date empty'. Admission dates written from the most recent 99223 within 45 days (own 99223 on pat17475816 v19455202 and pat17477719 v19455223; pat17472703 v19455216 from the same stay's earlier visit), full-visit resave onhcfa=1 x20. PRIMARY-DX GATE fired on 3 visits whose only diagnosis was a joint-status Z code (never-primary): pat17475816 v19455202 Z96.651, pat17477774 v19455206 Z96.641, pat17470950 v19455217 Z96.651 -> William's cascade added I10 in front (dx_primary_fix add-i10, full resave, freq-1 rebill 204 each). 99497 on v19455223 already carried modifier 25 (mcode7). Advisories bypassed with fresh ids: source-of-payment on v19455206; Pattern 11256 unspecified laterality I82.819 on pat17477719 x3 (v19455218, v19455219, v19455223) - logged to laterality_flag_log.md. Batch list empty after; 0 held." % (ib, ia, ova.get("claiminspectorcount"), ova.get("claiminspectoramount")))
EXC_TXT = ("%d -> %d rows on the per-run list calls (81 claim runs; no run newer than 1700211): the one row was a WEL04 'PA duplicate of a claim submitted 06/26/2026' rejection on run 1700211 (pat17476912 v19445941E, 99306 6/22/2026 $256) - completed with hideexclusions, no rebill (duplicate rule). AET12: HOLD per William 9/21 - not rebilled, not re-verified this slot (the 0510Z verify stands)." % (exb, exa))
PAM_TXT = ("Pam Gmail: three Brynwood PCC admission records 16:46Z 9/21 (readmits 9/17-9/18 from Capital Regional): pat17472393 (chart matches the sheet - Medicare seq 4 first, Humana Medicaid MMA seq 3, AMD 271 ACTIVE on both; NEW: the sheet's primary payer is HOSPICE MEDICAID via Big Bend Hospice - hospice election, so SNF visits from 9/17 fall under the 9/20 GV rule; no Brynwood charge dated after 9/17 yet; the 9/7-9/17 HCA Medicare claims are out and unanswered - a CO-B9 answer gets the GV rebill); pat20863 (chart matches - Medicare seq 1 ACTIVE + FCC seq 2, nothing to change); pat20379 (chart matches - Medicare seq 1 ACTIVE, Humana Medicaid MMA seq 4 ACTIVE 'MEDICAID GATE CAP DIR'; the PATIENT insurance order was blank -> set 1,4). All three charts had address line 1 BLANK with the street in line 2 -> addr_line1_fix moved the street into line 1 (line 2 still repeats it, cosmetic).")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action=INSP_TXT)
for v in insp.get("visits", []):
    steps = v.get("steps", []); adm = [s for s in steps if s.startswith("admission ")]; gate = [s for s in steps if "ADD-I10" in s or "add-i10" in s]
    add("Claim Inspector", "cleared", "pat%s" % v["pid"], "", "", "Hospitalization From Date empty" + (" + never-primary Z96.6x" if gate else ""), (adm[0] if adm else "") + (" | primary-dx cascade add-I10 + freq-1 rebill" if gate else "") + " | resave onhcfa=1", visit=v["vid"])
add("Unbilled", "count", action="0 -> 0 (getclaimunbillablecharges totalcount 0 before and after; payreasons rows 0)")
add("Exclusions", "count", action=EXC_TXT)
add("Exclusions", "cleared", "pat17476912", "06/22/2026", "WEL04", "PA duplicate of a claim submitted 06/26/2026", "completed (hideexclusions run 1700211), no rebill", visit="19445941", amount="256.00")
add("ERA", "count", action=ERA_TXT)
add("Sources", "read", action=PAM_TXT)
add("Sources", "action", "pat17472393", "", "FLO02/HUM01", "readmit 9/17 - hospice (Big Bend) on the sheet", "address line 1 set (was blank); chart plans verified; GV rule applies to SNF visits from 9/17 - note on the board row")
add("Sources", "action", "pat20863", "", "FLO02/FLO99", "readmit 9/17", "address line 1 set (was blank); chart plans verified, no change")
add("Sources", "action", "pat20379", "", "FLO02/HUM01", "readmit 9/18", "address line 1 set (was blank); patient insurance order blank -> 1,4 (Medicare, Humana MMA); chart plans verified")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: 0 new drops; rows updated after 13:00Z 9/21 are the page's own re-apply timestamps (15:36-15:37Z), no new William note. Board inbox: 20 files present (9/20 0345Z - 9/21 1310Z), none in the board's applied map (registry lastCheck 06:36Z 9/21) - nothing trashed.")
add("Routine", "note", action="Bootstrap: repo ATTACHED (origin/main 5f05466, session branch claude/pensive-einstein-sspd47), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 1310Z run's START has its RUN COMPLETE digest (13:25Z); no 1510Z/1710Z START on Drive - those slots did not fire; proceeded 19:16Z. Registers from practices/ehpa/registers (215 files); needs_facesheet_list.md (Drive 07:50Z + the 0910Z/1110Z/1310Z sections from main) / precheck_cache.json / pseudonyms.json (221 -> 223 names) from Drive 'workspace mirror'; payreasons.py + era_fallback_0913b.py from the repo helpers; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; insp_0921_1910.py = the 9/19 worked example, era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired; v8 (Drive 06:30Z, on main) not yet pasted - its rules followed.")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires; the 11am and 1pm ET 9/21 slots did not fire at all (no START marker on Drive)")
add("Open on William's turn", "note", patient="pat17472393", action="hospice election (Big Bend Hospice, hospice Medicaid primary on the 9/17 Brynwood readmit): the runs will put GV on his Brynwood visits from 9/17 per your 9/20 hospice rule - say 'GW' or 'hold' on the board row if you want otherwise")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI (carries pat17477775's VA CCN auth; API cannot blank it)")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case); 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check (Centene CO16/M56 on two primary Sunshine claims), or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads' (morning report 9/20)")
add("Open on William's turn", "note", patient="Automation Center", action="no ERA / End-of-Day-Close e-mail since 9/16 - check the Automation Center rule / notification setting in AMD")
with open("_run report 9-21 1910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 1 -> 0 (a WEL04 duplicate, not AET12), no claim run newer than 1700211; the 0510Z read stands (68 charges / 15 charts / $2,052.25 open)." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 12:00Z 9/20) - nothing to parse, post or reconcile; Working Denials queue 0; board drops 0; Pam Gmail: three Brynwood readmit records 16:46Z 9/21 (pat17472393, pat20863, pat20379) read and acted on." % SLOT)
app("tillotson-wainwright-17472393", "ok", "%s: Brynwood PCC admission record from Pam (readmit 9/17/2026 from Capital Regional, hospital stay 8/27-9/17): chart matches - Medicare 4E93... seq 4 first (AMD 271 ACTIVE A/B 7/1/2026, WellCare PDP), Humana Medicaid MMA 9663... seq 3 (271 ACTIVE MEDICAID GATE CAP DIR), Medicaid FFS 271 names Humana LTC + MMA. NEW on the sheet: Primary Payer = HOSPICE MEDICAID, Ins. Company BIG BEND HOSPICE (hospice election). No Brynwood charge dated after 9/17 yet; his 9/7-9/17 HCA 99233s ($160 each) are out to Medicare unanswered. Address line 1 was blank (street in line 2) -> set 2650 MUNICIPAL WAY." % SLOT,
    note="Pam's 9/17 readmit sheet says he is now on Big Bend Hospice (hospice Medicaid primary). Per your 9/20 hospice rule the runs will bill his Brynwood visits from 9/17 to Medicare with the GV modifier (attending physician, not hospice-employed); if Medicare answers CO-B9 on the 9/7-9/17 hospital claims they get the GV rebill too. Say 'GW' or 'hold' here if you want otherwise.")
app("fenner-maude-20379", "ok", "%s: Brynwood PCC admission record from Pam (readmit 9/18/2026, hospital stay 9/16-9/18): chart matches - Medicare 1DR8... seq 1 (271 ACTIVE A/B 11/1/2014), Humana Medicaid MMA H744... seq 4 (271 ACTIVE MEDICAID GATE CAP DIR, Medicare A/B named); WEL04 (ended 7/31/2026) and UNI20 (ended 4/1/2026) dead. The PATIENT insurance order was BLANK -> set 1,4 (Medicare first, Humana second; readback ok). Address line 1 was blank -> set [address] Nothing for William." % SLOT)
ops.append({"op": "upsert", "collection": "items", "id": "hatherley-dahlia-20863", "set": {"patient": "HATHERLEY,DAHLIA", "dob": "", "facility": "BRYNWOOD (Monticello)", "amdid": "20863", "mbi": "", "inscarrier": "FLO02 Florida Medicare", "insid": "", "insplans": "1st FLO02 Florida Medicare · 2nd FLO99 Florida Community Care (Medicaid LTC/coinsurance)", "need": "None - readmit 9/17/2026 verified from Pam's Brynwood admission record; chart already carries Medicare first (271 ACTIVE A/B 2/1/2010, FL QMB, WellCare PDP) and Florida Community Care second (271 AAA 41 as always). Address line 1 was blank -> set. Nothing for William.", "why": "Pam admit email 9/21 16:46Z: Brynwood readmit 9/17/2026 (hospital stay 8/30-9/17 at Capital Regional)", "amount": 0, "status": "claude", "created": NOW, "notes": [{"who": "Claude", "text": "Created by the 3pm ET 9/21 run from Pam's readmit sheet - chart verified, nothing to change but the blank street line.", "at": NOW}]},
    "append": {"checks": [{"ok": "ok", "src": SRC, "result": "Brynwood PCC admission record: Medicare A primary + Medicaid coinsurance via Florida Community Care - matches the chart (FLO02 seq 1 ACTIVE, FLO99 seq 2); addr line 1 set [address]", "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 19:09-%s UTC 9/21, run %s)
Bootstrap: repo ATTACHED (origin/main 5f05466, session branch claude/pensive-einstein-sspd47), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: the 1310Z run's START has its RUN COMPLETE digest (13:25Z); no 1510Z / 1710Z START on Drive (those slots did not fire) - proceeded 19:16Z. Registers from practices/ehpa/registers (215 files); needs_facesheet_list.md / precheck_cache.json / pseudonyms.json (221 -> 223 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired (v8 on Drive since 06:30Z and on main, not yet pasted; its rules followed).
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no new William note (rows updated 15:36-15:37Z are the page's re-apply). Sources: the six watched Drive folders hold nothing modified after 12:00Z 9/20 except mercy.pdf (worked 0510Z); Claimocity drop: nothing. %s
Claim runs: none newer than 1700211 (81 runs).
Columns: Charge Review 0 -> 0 | Claim Inspector %s | Unbilled 0 -> 0 | Exclusions %s
ERA step 5: %s
Write-offs: none. Rebilled: 3 inspector visits freq-1 by the dx cascade (v19455202, v19455206, v19455217 - new claims, $332 fee). Insurance entered: none (pat20379 patient insurance order 1,4 set; 3 address line-1 fixes).
NEEDS WILLIAM: (1) paste prompt v8 into the routine (and note the 11am/1pm ET 9/21 slots did not fire); (2) pat17472393 hospice - GV per the 9/20 rule unless he says GW/hold; (3) pat17477777 rplan18462071 Pre-Auth # (UI); (4) AET12 carrier master (HOLD); (5) board row centene-m56-denials-0920 ($772.92); (6) the 6 Optum Pay remits; (7) AMD Automation Center e-mails stopped 9/16; (8) BCBS patient-balance audit still parked.
Calls learned: no new call shapes (updextrainsinfo hospitalizationfrom, dx_primary_fix add-i10, bypassclaimedits, hideexclusions, addr_line1_fix PATCH, ins_update sequence=patient insorder reused); vocabulary unchanged (54).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, PAM_TXT, INSP_TXT, EXC_TXT, ERA_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-21_1910UTC run digest - backend billing run, 3 PM ET 9/21 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, tillotson-wainwright-17472393 (+ a note on the hospice election), fenner-maude-20379; one new row hatherley-dahlia-20863 on Claude's turn) uploaded; nothing trashed (none of the 20 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0 (54 calls). Postman: see mirror line.
Mirror: %s
State bundle: not uploaded (every register and script of this run is on GitHub main under nightly/runs/%s and practices/ehpa/registers)

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR, S)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-21_1910UTC run digest.md", "w").write(dig)
    if S not in open("needs_facesheet_list.md").read():
        with open("needs_facesheet_list.md", "a") as fh: fh.write(SEC)
print("wrote report csv (%d rows), board file (%d ops), needs_facesheet section%s" % (len(rows), len(ops), ", digest" if "--final" in sys.argv else ""))
