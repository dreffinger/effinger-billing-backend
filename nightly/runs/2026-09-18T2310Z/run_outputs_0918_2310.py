# PLAIN ENGLISH (run outputs for the 7pm ET 9/18/2026 slot - ehpa cloud run 2026-09-18T2310Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA before/after
#   snapshots, the unbilled/AET12 verify registers and the precheck log, then writes:
#   - "_run report 9-18 2310.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-18T2310Z.json (Insurance Refresh Board inbox file: the new Aviata admit row, the closed
#     unread-facesheet row, appends on the standing rows)
#   - facesheets_email_2026-09-18T2310Z.txt (the standing 7pm 'current face sheets needed' email body)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final)
# Never touches: AMD, the board databases. Member ids / MBIs never leave the registers.
import csv, json, os, datetime, sys
S = "2026-09-18T2310Z"; SRC = "7pm ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "7 PM ET 9/18"
P = json.load(open("inbox/phi_2310.json"))  # DOBs live outside the mirrored script (PHI gate)
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ver = load("registers/aet12_verify_%s.json" % S, []); aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []) or before.get("unbilled", []); runs_n = ovb.get("claimrunstatuscount", "?")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row west-shirley-17471007 on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart, zero insplans (getdemographic re-read 23:17Z this run); cascade exhausted 9/18 05:xxZ; no facesheet, Pam email or drop since - held on William's turn (0510Z board rows); listed in tonight's 'current face sheets needed' email"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17 or 9/18 - the AMD Automation Center EOD close appears stopped since 9/16, seventh consecutive worked slot); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action="%d unposted checks / $%.2f before -> %d / $%.2f after; ERA Center empty; locks release-expired sent; era_post --all-unposted 0 checks; fallback dry+live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments'; no MA63/M76/M64 work" % (nb, ab, na, aa))
add("Pam admit emails", "acted", "MARCUS,BACCHUS (chart 3873, pat17473669)", "09/18/2026", "AMB03", "Pam 9/18 21:59Z: new patient at Aviata (PCC Clinical Resident Profile photo); sheet payer UHC/AARP Secure Horizon COMM 132948183; chart had the name order reversed, zero insplans, address line 1 blank",
    "chart renamed to last MARCUS / first BACCHUS (PCC + Pam + payer 271 agree; AAA 73 under the old order); UNI20 132948183 added then end-dated 05/31/2026 (Stedi UHC 87726 INACTIVE at 9/18/2026, 3/1/2026, 10/1/2025; not Medicare - MBI ERR 72); Stedi discovery = Ambetter (AMB03) UZ081830501 Elite Bronze 6/1-12/31/2026 -> plan added seq 2, AMD 271 ACTIVE, patient order 2,1; address 2230 W TENNESSEE ST Tallahassee 32304 (payer-confirmed) into line 1. No charges on the chart yet - the Aviata visits bill Ambetter when they land. Board row marcus-bacchus-17473669 (Claude's turn, watching).")
add("Precheck", "7pm extra", action="precheck --days 3 --max 120: 17 patient/payer pairs, 8 flagged - BELL JR (known JR-suffix Stedi name-match false positive, AMD 271 Medicare ACTIVE) and 7 'no <carrier> plan on chart' (pat17477640 HUM01, pat17472703 SUN01, pat17477716 UNI20, pat17476608 BCBS, pat17473782 CAP07, pat17477722 UNI20, pat17477706 VACCN): every one of those charts DOES carry that plan at sequence 1 (getdemographic re-read 23:2xZ) - precheck's plan match (CARRIERS.get(car) vs the parsed insplan tuple) is failing this run; claims stay as billed, no action. Helper defect noted for the next chat session.")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: rows on Claude's turn read (189), drops 0 new, no row updated after 03:30Z 9/18 (no new William note); board inbox: neither registry's applied map lists a file still in the inbox - nothing trashed")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC), Claimocity drop, Optum ERA folder, treasury folder: nothing modified after 12:00Z 9/17 except the routine's own report CSV; Pam Gmail: ONE new admit email 21:59Z 9/18 (Bacchus Marcus, Aviata) - read and acted on; the ten 9/17 emails were already read")
add("Boards", "closed", "UNREAD FACESHEET (Omnissa Horizon.pdf)", action="row facesheet-unread-omnissa-horizon-0916 closed: William 9/18 02:15Z asked for OCR back - tesseract + poppler-utils are installed by bootstrap layout in every run since the 0310Z 9/18 run, and the 0510Z run already OCR'd the file (Commure PRO visits list for pat17471832, not a facesheet; every stay day is charged). Nothing pending on it.")
add("Face sheets email", "sent", action="'current face sheets needed' to dreffinger@gmail.com: 3 new HCA charts (8 visits, $1,286) need a facesheet/card; AET12 carrier record + West MV line listed as the open decisions")
add("Routine", "note", action="State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main; registers restored from practices/ehpa/registers + nightly/runs. Bundle re-packed and uploaded this run (patient_db 1 record, era_details 0).")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 full-charge $0-denial lines are PR-39 / wrong-payer decisions); hold Florida Blue patient statements")
with open("_run report 9-18 2310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
ops.append({"op": "upsert", "collection": "items", "id": "marcus-bacchus-17473669",
    "set": {"id": "marcus-bacchus-17473669", "patient": "MARCUS,BACCHUS", "dob": P["dob_marcus"], "facility": "AVIATA (ASPIRE) AT TALLAHASSEE", "amdid": "17473669", "mbi": "",
            "need": "Watching. Pam's 9/18 admit sheet (Aviata PCC profile) lists UHC/AARP Secure Horizon COMM 132948183, but UHC says INACTIVE on every date checked and he is not a Medicare beneficiary; Stedi discovery found Ambetter (Sunshine marketplace) UZ081830501 Elite Bronze 6/1-12/31/2026 and AMD's own 271 on it is ACTIVE. Chart set: Ambetter first (seq 2), UHC end-dated 5/31/2026, name order corrected to MARCUS (last) / BACCHUS (first), street 2230 W Tennessee St. No charges yet - the Aviata visits bill Ambetter when they land. Nothing for you unless Ambetter denies.",
            "why": "Pam admit email 9/18 21:59Z: 'Marcus is the last name, Bacchus is the first name, new patient at Aviata'. Chart 3873 existed with the names reversed, no insurance plan and a blank street.",
            "amount": 0, "status": "claude", "inscarrier": "AMB03 Ambetter From Sunshine Health", "insid": "UZ081830501", "insplans": "1st AMB03 Ambetter UZ081830501 (6/1/2026-) · UNI20 United Healthcare 132948183 (ended 05/31/2026)", "lastfac": "Aviata at Tallahassee", "created": NOW, "updated": NOW},
    "append": {"notes": [{"who": "Claude", "text": "Created by the 7pm ET 9/18 run from Pam's admit email (photo of the PCC Clinical Resident Profile, admitted 09/18/2026 from Capital Regional; orig admit 08/08/2025).", "at": NOW}],
               "checks": [{"ok": "ok", "src": "Pam admit email 9/18 21:59Z (PCC profile photo)", "result": "MGD LEVEL-UHC/AARP SECURE HORIZON COMM, policy 132948183, Ins. Company United Healthcare; no Medicare/Medicaid number; DOB %s = chart" % P["dob_marcus"] + "", "when": W},
                          {"ok": "no", "src": "Stedi eligibility UHC 87726 (member 132948183)", "result": "INACTIVE (planStatus 6) at DOS 9/18/2026, 3/1/2026 and 10/1/2025 once the name is sent as last MARCUS / first BACCHUS (AAA 73 under the chart's old order)", "when": W},
                          {"ok": "no", "src": "Stedi MBI lookup", "result": "ERR 72 - not a Medicare beneficiary", "when": W},
                          {"ok": "ok", "src": "Stedi insurance discovery", "result": "Ambetter from Sunshine State Health Plan, member UZ081830501, Elite Bronze, plan 6/1-12/31/2026, Active Coverage (REVIEW_NEEDED); Centene 68069 direct check answered AAA 42 (payer transient)", "when": W},
                          {"ok": "ok", "src": "AMD eligibility (free 271) - AMB03 ins9519482", "result": "ACTIVE 9/18/2026; payer address 2230 W Tennessee St Tallahassee 32304", "when": W},
                          {"ok": "ok", "src": "AMD action", "result": "names PATCH first BACCHUS / last MARCUS (lookuppatient now MARCUS,BACCHUS); add_ins UNI20 car6404 132948183 -> ins9519481 then enddate 05/31/2026; add_ins AMB03 car6802 UZ081830501 begin 06/01/2026 -> ins9519482 seq 2; patient insorder 2,1; address line 1 2230 W TENNESSEE ST (line 2 'aspire' kept), zip 32304", "when": W}]}})
app("facesheet-unread-omnissa-horizon-0916", "ok", "Closed 7pm ET 9/18: OCR is back - bootstrap layout installs tesseract + poppler-utils in every run (since the 0310Z 9/18 run) and ocr_pdf.py is in the workspace; 'Omnissa Horizon.pdf' was already OCR'd by the 0510Z run: it is the Commure PRO visits list 9/2021-9/2026 for pat17471832 (not a facesheet), every stay day charged - nothing pending.",
    note="You asked 9/18 02:15Z to add OCR back - done: every run now installs tesseract + poppler and reads scanned PDFs with ocr_pdf.py. This file turned out to be the Commure visit list for the Savage chart (handled on row savage-janice-17471832), so this row is closed.", set_={"status": "done", "need": "CLOSED 9/18 - OCR restored (tesseract + poppler in every run); the file was the Commure visit list for pat17471832, already read and handled."})
app("aet12-carrier-cpid", "no", "7pm ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted on 9/17 or 9/18 - the Automation Center EOD close looks stopped since 9/16, seventh consecutive worked slot). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. ERA Center empty: locks release-expired sent; era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s in 'bht Optum era downloads' (nothing to upload); no MA63/M76/M64 work." % (SRC, S, nb, ab, na, aa))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 12:00Z 9/17 outside this routine's own files) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: one new admit email 21:59Z 9/18 (Aviata, pat17473669 - acted on, row marcus-bacchus-17473669); 7pm precheck (3 days) 17 pairs, 8 flags = 1 known JR false positive + 7 precheck plan-match misses (charts carry the plan).")
for rid, txt in (("conway-shelby-17477775", "chart still has zero insurance plans (getdemographic 23:17Z 7pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, Pam Gmail: only the 9/18 Aviata admit (a different patient), no board drop; 3 visits stay in Unbilled 'Insurance order is missing'; listed in tonight's 'current face sheets needed' email"),
                 ("thurlow-nerys-17477776", "chart still has zero insurance plans (getdemographic 23:17Z 7pm ET 9/18); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; a 4th visit (99232 9/17, vst19455052) has landed on the chart; no facesheet, Pam email or drop since; listed in tonight's 'current face sheets needed' email"),
                 ("gorman-davin-17477779", "chart still has zero insurance plans (getdemographic 23:17Z 7pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; 2 visits stay in Unbilled 'Insurance order is missing'; listed in tonight's 'current face sheets needed' email")):
    app(rid, "no", txt)
app("west-shirley-17471007", "human", "7pm ET 9/18: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance.")
app("bcbs-patient-balance-audit-0918", "na", "7pm ET 9/18: not worked this run (same blocker as 0710Z-2110Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements.")
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("board ops", len(ops))
email = """Current face sheets needed - 7 PM ET run, Friday 9/18/2026 (backend billing run %s)

Three new HCA Florida Capital Hospital charts from the Claimocity feed have no insurance on file and every automated source is exhausted (MBI lookup, discovery, Drive facesheet folders, Pam's emails, board drops). Their visits sit in the Unbilled column ('Insurance order is missing'):

1. CONNELL, SHELLEY DOUGLAS - DOB %s - HCA Florida Capital Hospital (admitted ~9/14/2026) - payer unknown (not Medicare; discovery 0) - need the admission facesheet or card - 3 visits waiting (99223 9/14, 99232 9/15, 99232 9/16; $532).
2. THOMAS, NANCY L - DOB %s - HCA Florida Capital Hospital (admitted 9/14/2026) - CMS names CAPITAL HEALTH PLAN (Medicare Advantage) since 11/2016; the CHP member id is the missing piece - need the facesheet or CHP card - 4 visits waiting (99223 9/14, 99232 9/15, 9/16, 9/17; $643).
3. GORDON SR, DAVID J - DOB %s - HCA Florida Capital Hospital (Cairo GA resident) - payer unknown (not Medicare; discovery 0) - need the admission facesheet or card - 2 visits waiting (99223 9/14, 99232 9/15; $421).

Acted on tonight without you: Pam's 9/18 admit email for MARCUS, BACCHUS (Aviata) - chart name order corrected, Ambetter UZ081830501 attached (active per AMD's 271), UHC on the sheet is inactive and end-dated; visits bill Ambetter when they arrive.

Still open decisions (unchanged): the AET12 (Aetna Senior Supplemental) carrier record - 59 claims / $2,052.25 held until the transmitted payer id stops printing the TIN; the WEST, SHIRLEY 'MV' $75.68 line on visit 19375395 (Bill Insurance = No).

Columns tonight: Charge Review 0, Claim Inspector 0, Unbilled 20 (11 payment-reason-code holds, 1 MV line, 8 visits of the 3 charts above), Exclusions 0 (no nightly claim run has posted since 9/16 - seventh slot in a row). ERA Center empty (0 checks before and after).
""" % (S, P["dob_connell"], P["dob_thomas"], P["dob_gordon"])
open("facesheets_email_%s.txt" % S, "w").write(email)
sec = """## %s columns run (ehpa cloud Code Routine, 23:08-%s UTC 9/18, run %s)
Bootstrap: repo ATTACHED (origin/main da4f1d6, session branch claude/pensive-einstein-23yq20, layout 364 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC (26 parts) is older than GitHub main - registers restored from practices/ehpa/registers/ (103 files), needs_facesheet sections rebuilt from nightly/runs/ (35 run folders); captured_calls.md = GitHub main docs/captured_calls.md (336 KB; the Drive additions through 2110UTC are all in main); pseudonyms.json 206 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 2110 START (21:12Z) had its RUN COMPLETE digest (21:21Z) - proceeded.
Boards: Insurance Refresh Board - 189 rows on Claude's turn read, drops 0 new, no row updated after 03:30Z 9/18; Working Denials queue 0. Facesheet folders, Claimocity drop, Optum ERA folder, treasury folder: nothing modified after 12:00Z 9/17 except the routine's own run-report CSV. Pam Gmail: ONE new admit email 21:59Z 9/18 - MARCUS,BACCHUS at Aviata (pat17473669): chart had the names reversed, zero insplans, blank street -> renamed (PCC + Pam + payer agree), UNI20 132948183 from the sheet added and end-dated 05/31/2026 (Stedi UHC INACTIVE on every date; not Medicare), Ambetter UZ081830501 from Stedi discovery added seq 2 (AMD 271 ACTIVE), patient order 2,1, address 2230 W TENNESSEE ST into line 1; no charges yet; board row marcus-bacchus-17473669. The Omnissa Horizon row closed (OCR restored, file already read 9/18 05:xxZ).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read 23:17Z; the 0510Z cascade stands; no new facesheet, Pam email or drop) held on William's turn and listed in tonight's email | Exclusions 0 -> 0 (no claim run newer than 1700202, %s runs listed - NO nightly claim run posted 9/17 or 9/18, seventh consecutive worked slot; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released, rebilled or written off by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after - ERA Center empty; locks release-expired sent; era_post 0; fallback 0; era_clear 0; 0 faults; no new 835s. Availity 5(g): nothing new.
7 PM extras: (a) precheck --days 3 --max 120: 17 pairs, 8 flagged - BELL JR (known JR-suffix false positive) + 7 'no <carrier> plan on chart' that are precheck plan-match misses (each chart carries that plan at seq 1; claims stay as billed; helper defect for the next chat session). (c) 'current face sheets needed' email sent to dreffinger@gmail.com (3 HCA charts, 9 visits). (d) run report CSV uploaded to Drive 'bht hca facesheets'.
OPEN (Claude's turn, from the 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 - not worked. Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes (names PATCH via patient_patch.patch({'names': [...]}) re-used from the 9/14 Brown rename; addr_line1_fix + family_address with line 2 kept). Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ova.get("unbillableamount"), runs_n, aet_bal, nb, ab, na, aa, MIRROR)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + sec)
    os.makedirs("chat_history", exist_ok=True)
    addn = """# captured_calls additions - %s (7pm ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- A chart whose first/last names are REVERSED answers AAA 73 'Invalid/Missing Subscriber Name' on AMD's free 271 and on Stedi for every payer; the payer recognizes the member the moment the names are sent the other way round (pat17473669: PCC sheet, Pam's email and the UHC/Ambetter 271s all say last MARCUS / first BACCHUS). Fix = patient_patch.patch(pid, {'names': [<the names list with firstname/lastname swapped>]}) -> HTTP 200; lookuppatient name='MARCUS, BACCHUS%%' finds the chart afterwards. Same PATCH as the 9/14 Brown first-name change.
- Address line 1 on a chart whose line 1 is blank: addr_line1_fix.fix() (capturepreviousaddress=true, line 2 kept) saves; a follow-up family_address() that BLANKS line 2 answers 500 'Address is required.' - re-send with the existing line-2 text and it saves (street corrected 2330 -> 2230 W Tennessee St from the payers' 271 address).
- Stedi discovery on a 55-year-old with a stale UHC/AARP line on the SNF sheet returned the live marketplace plan (Ambetter Elite Bronze 6/1-12/31/2026); Centene 68069 direct eligibility answered AAA 42 (unable to respond) four times in a row while AMD's own 271 on the new AMB03 plan answered ACTIVE at once - AMD 271 first, Stedi discovery second, is the right order for a chart with no plan.
- precheck.py (7pm extra) reported 'no <carrier> plan on chart' on 7 charts that DO carry the plan at seq 1 - its CARRIERS.get(car) match against the parsed insplan tuple misses this run (carriers.json is the simple code->carN map the bootstrap writes). Not fixed this run; verify by getdemographic before acting on that flag.
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 23:15Z 9/18 (78 runs): seventh consecutive worked slot with no nightly claim run - nothing in the API starts one.
""" % S
    open("captured_calls_additions_%s-7pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(addn)
    dig = "# %s run digest - backend billing run, 7pm ET 9/18/2026 slot (ehpa cloud)\n\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
else:
    print(sec)
