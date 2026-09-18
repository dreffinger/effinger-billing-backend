# PLAIN ENGLISH (run outputs for the 11pm ET 9/17/2026 slot - ehpa cloud run 2026-09-18T0310Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA before/after
#   snapshots, the AET12 verify register, the pat17471832 visit-history cross-check + contractual-correction
#   registers and the Florida Blue patient-balance scope register, then writes:
#   - "_run report 9-18 0310.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-18T0310Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; set only on the
#     rows this run closes/answers/creates)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text (--final)
# Never touches: AMD, the board databases.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-18T0310Z"; SRC = "11pm ET 9/17 columns run (ehpa cloud)"; W = "9/17"
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
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
era_txt = open("era_summary.txt").read().strip() if os.path.exists("era_summary.txt") else "ERA chain not run"
insp_before = sum(len(v) for v in before.get("inspector", {}).values()); insp_after = sum(len(v) for v in after.get("inspector", {}).values())
sav = load("registers/pat17471832_correction_%s.json" % S, {})
sav_lines = sav.get("lines", []); sav_ok = [l for l in sav_lines if l.get("ok")]
sav_wo = round(sum(f(l.get("wo")) for l in sav_ok), 2)
bcbs = load("registers/bcbs_patbal_%s.json" % S, [])
bcbs_tot = round(sum(f(r.get("patbalance")) for r in bcbs), 2); bcbs_pats = len({r.get("patientid") for r in bcbs})
bcbs_full = [r for r in bcbs if abs(f(r.get("patbalance")) - f(r.get("totalchargeamount"))) < 0.01]
bcbs_full_tot = round(sum(f(r.get("patbalance")) for r in bcbs_full), 2)
stays = load("registers/pat17471832_stays_%s.json" % S, [])
nocharge = [s["stay"] for s in stays if s.get("charges") == 0]
partial = ["%s (%d of %d days charged)" % (s["stay"], s["dos_with_charge"], s["days"]) for s in stays if 0 < s.get("dos_with_charge", 0) < s.get("days", 0) - 1]

rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty; overview chargereviewcount 0)")
add("Claim Inspector", "clear", action="%d visits before, %d after (getclaiminspectorbatches empty; overview claiminspectorcount 0) - nothing to fix" % (insp_before, insp_after))
add("Unbilled", "clear", action="0 rows before and after (getclaimunbillablecharges totalcount 0)")
add("Exclusions", "clear", carrier="AET12", err="claim run 1700202 exclusion list empty at 03:24Z (59 AET12 PREF0288/PREF0264 rows were still there at 01:13Z)",
    action="The 59 AET12 rows were completed OUTSIDE the routine between 01:13Z and 03:24Z 9/18 (getclaimexclusioncharges 1700202 -> empty visitlist; overview exclusioncount 0; %s claim runs listed, none newer than 1700202). gettxhistory on the 15 charts: 68 AET12 charges still billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment (Medicare paid $%.2f) - NOT re-sent by anyone; they leave again only on a rebill after the carrier record is fixed. Nothing released, rebilled or written off in the four columns by this run." % (runs_n, aet_bal, aet_paid), amt="%.2f" % aet_bal)
add("ERA", "clear" if na == 0 else "held", action="GET /api/era/checks: %d unposted checks / $%.2f before -> %d / $%.2f after. %s" % (nb, ab, na, aa, era_txt))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads', 'treasury payments' or the four facesheet folders modified after 09:00Z 9/17 (only routine artifacts); registers/availity_register.json unchanged; nothing new parsed, posted or reconciled")
add("Facesheet OCR", "done", patient="pat17471832", action="William 02:15Z: 'add the ability back to ocr a pdf'. OCR restored this run: tesseract-ocr + poppler-utils now install in bootstrap layout (tools/bootstrap/bootstrap_workspace.sh), helper scripts/helpers/ocr_pdf.py added; Drive transport = download_file_content (an oversized result is spilled to a local tool-results file, extracted with jq - no transcription). 'Omnissa Horizon.pdf' (343 KB scan) read: it is the Commure PRO VISITS LIST 9/2021-9/2026 for pat17471832, not a facesheet - no insurance, auth or address on it.")
for s in stays:
    add("Facesheet OCR", "stay check", patient="pat17471832", dos=s["stay"], carrier=",".join(s.get("carriers", {}).keys()), action="%d charges on %d of %d stay days; paid %.2f; patient balance (before correction) %.2f; insurance balance %.2f" % (s["charges"], s["dos_with_charge"], s["days"], f(s["paid"]), f(s["patbal"]), f(s["insbal"])), amt="%.2f" % f(s["patbal"]))
add("Patient-balance correction", "done" if sav_ok else "none", patient="pat17471832", carrier="BCBS",
    err="Florida Blue lines posted 9/14 from the Availity remits carried NO CO-45 contractual write-off: AMD moved the whole remainder (CO-45 + PR-2) to the patient balance",
    action="%d of %d lines corrected: move_to_ins (patient balance back to insurance, no rebill) + manual_post pay 0 / WOINS = the remit's CO-45 with the Availity trace as check number and the check date as deposit date; AMD then auto-transferred the PR-2 coinsurance back to the patient. WOINS posted $%.2f. %s" % (len(sav_ok), len(sav_lines), sav_wo, sav.get("note", "")), amt="%.2f" % sav_wo)
for l in sav_lines:
    add("Patient-balance correction", "posted" if l.get("ok") else "skipped", patient="pat17471832", dos=l.get("dos"), carrier="BCBS", err=l.get("cas", ""), action=l.get("msg", ""), check=l.get("check"), visit=l.get("visit"), amt="%.2f" % f(l.get("wo")))
add("Patient-balance audit", "open", carrier="BCBS", err="masswriteoffsearch carrier 6062 isinsbalance:false (bills 9/2024-9/2026)",
    action="%d Florida Blue charges on %d charts carry a PATIENT balance totalling $%.2f; %d of them ($%.2f) carry the FULL charge (a $0 denial the ERA poster transferred to the patient - PR-39 auth, PR-22 other-payer-primary etc.); the rest are partly paid lines whose patient balance is charge minus payment (contractual not adjusted, the pat17471832 pattern). Register registers/bcbs_patbal_%s.json. Next runs: parse the Availity CheckDetails PDFs locally (new transport) and correct line by line per the remit (CO -> WOINS, PR stays, PR-22 -> insurance + re-route, PR-39 -> William's WONCS rule)." % (len(bcbs), bcbs_pats, bcbs_tot, len(bcbs_full), bcbs_full_tot, S), amt="%.2f" % bcbs_tot)
add("Pam admit emails", "none new", action="Gmail sweep from:pgarnp24work@gmail.com has:attachment newer_than:2d = the same 10 admit emails of 18:40-18:50Z 9/17 that the 3pm ET run read (board row pam-admits-2026-09-17); nothing newer - not re-read")
add("Boards", "1 note", action="Working Denials queue 0 queued; Insurance Refresh Board 189 rows on Claude's turn, ONE new William note (02:15Z, row facesheet-unread-omnissa-horizon-0916: 'add the ability back to ocr a pdf') - answered; drops 0 new; board inbox: both registries' applied maps still list only 9/12-9/15 files (the board applied the 0110Z file at 02:11-02:57Z without registering it), 42 run files waiting - nothing trashed.")
out = "_run report 9-18 0310.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
ops = []
def row(id, checks=None, notes=None, op="update", set_=None):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if set_: o["set"] = set_
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    ops.append(o)
row("aet12-carrier-cpid",
    checks=[chk("na", "11pm ET 9/17: the 59 AET12 exclusion rows of claim run 1700202 are GONE from the exclusion list (getclaimexclusioncharges 1700202 = empty at 03:24Z; they were still there at 01:13Z) - completed outside the routine. The 68 AET12 charges on the 15 charts are unchanged: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment, NOT re-sent (no new claim run; %s listed). They leave again only on 'rebill' after the carrier record is fixed." % (aet_bal, runs_n), SRC + " - claim run 1700202")])
row("era-manual-post-0912", checks=[chk("na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. %s" % (SRC, S, nb, ab, na, aa, era_txt[:400]), SRC + " - ERA step 5")])
row("availity-remits-backlog",
    checks=[chk("no", "No new Availity PDF or Check/EFT export (nothing modified after 09:00Z 9/17). FINDING on the 9/14 Availity posts: on pat17471832 every Florida Blue line posted from the remits carries patient balance = charge minus payment - the remit's CO-45 contractual was never written off, so the patient balance held CO-45 + PR-2 (e.g. 99233: charge 160, allowed 107.26, CO-45 52.74, PR-2 53.63, paid 53.63 -> AMD showed patient 106.37). Corrected %d lines on that chart tonight ($%.2f WOINS). Scope: %d Florida Blue charges / %d charts / $%.2f patient balance (register bcbs_patbal_%s.json) - see row bcbs-patient-balance-audit-0918." % (len(sav_ok), sav_wo, len(bcbs), bcbs_pats, bcbs_tot, S), SRC + " - ERA step 5(g)")])
row("facesheet-unread-omnissa-horizon-0916", op="upsert",
    set_={"status": "done", "need": "DONE 9/18 (11pm ET 9/17 run): OCR is back. The run now installs tesseract + poppler at bootstrap, keeps scripts/helpers/ocr_pdf.py, and pulls a scanned Drive PDF onto disk through the connector without transcription. 'Omnissa Horizon.pdf' read: it is the Commure PRO VISITS LIST (9/2021-9/2026) for pat17471832 - not a facesheet (no insurance, auth or address on it); the 7am ET 9/16 run had already rendered it but this row was never closed. Findings from it are on the selwyn-janis-17471832 row."},
    checks=[chk("ok", "tesseract-ocr + poppler-utils installed (apt) and pymupdf (pip) in the run container; ocr_pdf.py helper tested on a synthetic PNG (text read back exactly); 'Omnissa Horizon.pdf' (343,470 bytes) downloaded via the connector (oversized result spilled to the local tool-results file, extracted with jq), rendered with pdftoppm 250 dpi + tesseract, 2 pages, 30 visit rows read. The Drive connector itself does NOT OCR (a PNG probe uploaded to workspace mirror read back empty; probe trashed).", SRC + " - OCR restore")],
    notes=[{"who": "Claude", "at": NOW, "text": "Done - OCR works again in the run (the ability was there on 9/16; this row was just never closed). That file is the pat17471832 Commure visits list, read in full; see her row for what it showed."}])
row("selwyn-janis-17471832", op="upsert",
    set_={"status": "william", "need": "WILLIAM - two things from tonight's read of this chart (your Commure visits list of 9/16 was OCRed - every one of the 10 Effinger inpatient stays on it is fully charged in AMD, 109 charges): (1) DECIDE 'same' or 'appeal' on the two admission 99223s Florida Blue denied PR-39 (4/2/2026 v19437270 and 4/28/2026 v19440411, $310 each) plus the 12/31/2025 99223+99497 ($443, v19427723, $0 on check 213403769) - the ERA poster moved all $753 to the PATIENT balance on 9/9 and 9/16; 'same' = WONCS like the 5/27 admission, and the run moves them off the patient. (2) FYI corrected tonight: the Florida Blue lines posted 9/14 from the Availity remits had no contractual write-off, so the patient balance held CO-45 + coinsurance; WOINS posted per the remits, patient balance now = the remit's PR-2 only."},
    checks=[chk("ok", "Commure PRO visits list (Omnissa Horizon.pdf) OCRed: 30 visit rows 12/2021-5/2026, 10 Effinger inpatient stays; AMD tx history (typefilter 0 = all 109 charges) compared per stay: every stay day is charged (no charges missing%s). Open items (typefilter 1): 27 charges, $0 insurance balance, patient balance $2,972.37 before tonight's correction." % ("" if not nocharge else "; unexpected gaps: " + "; ".join(nocharge)), SRC + " - visits list vs AMD"),
            chk("ok" if sav_ok else "no", "Contractual correction: %d of %d Florida Blue lines fixed (move_to_ins no rebill + manual_post pay 0 / WOINS = remit CO-45, Availity trace as check number; AMD auto-transferred the PR-2 coinsurance back to the patient). WOINS $%.2f. %s" % (len(sav_ok), len(sav_lines), sav_wo, sav.get("note", "")), SRC + " - patient-balance correction")],
    notes=[{"who": "Claude", "at": NOW, "text": "Read your Commure visits list - all 10 stays are charged in AMD. Two items in the box above: the PR-39 admissions ($753 now sitting on the patient balance - say 'same' to write off) and the contractual fix posted tonight."}])
row("bcbs-patient-balance-audit-0918", op="upsert",
    set_={"patient": "FLORIDA BLUE - patient balances after the 9/14 Availity posts", "dob": "", "facility": "", "amdid": "", "mbi": "", "amount": bcbs_tot, "status": "claude",
          "need": "AUDIT (Claude): %d Florida Blue charges on %d charts carry a patient balance totalling $%.2f (masswriteoffsearch carrier 6062, isinsbalance false, bills 9/2024-9/2026). %d of them ($%.2f) hold the FULL charge = a $0 denial the ERA poster transferred to the patient (PR-39 auth denials, PR-22 other-payer-primary, etc.); the rest are partly paid lines where the remit's CO-45 was never written off (pat17471832 pattern, fixed tonight). Plan for the next runs: pull the Florida Blue CheckDetails PDFs from Drive onto disk (new transport), parse with availity_pdf.py, and per line: CO -> WOINS with the trace number, PR stays, PR-22 -> move to insurance + re-route to the primary, PR-39/CO-39 -> William's WONCS rule, $0 lines with no remit -> report. Register registers/bcbs_patbal_%s.json." % (len(bcbs), bcbs_pats, bcbs_tot, len(bcbs_full), bcbs_full_tot, S),
          "why": "Tonight's read of one chart (pat17471832) showed every Availity-posted Florida Blue line with patient balance = charge minus payment (CO-45 never adjusted) and $753 of PR-39/$0 denials on the patient balance - the same posting path touched 338 lines on 9/14-15, so the whole carrier needs the line-by-line check before any statement goes out."},
    checks=[chk("ok", "scope pulled: %d charges / %d charts / $%.2f patient balance; %d at full charge $%.2f; by DOS year %s" % (len(bcbs), bcbs_pats, bcbs_tot, len(bcbs_full), bcbs_full_tot, json.dumps({y: n for y, n in collections.Counter((r.get("dateofservice") or "")[:4] for r in bcbs).items()})), SRC + " - masswriteoffsearch")],
    notes=[{"who": "Claude", "at": NOW, "text": "Created by the 11pm ET 9/17 run. Nothing for you to do yet - the runs work it; hold Florida Blue patient statements until this row says done."}])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

sec = """
## 2026-09-17 11 PM ET columns run (ehpa cloud Code Routine, 03:08-%s UTC 9/18, run %s)
Bootstrap: repo ATTACHED (origin/main 1383119, session branch claude/pensive-einstein-01gccz, layout 327 helpers), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, not unpacked); registers restored from practices/ehpa/registers/ (0110Z state); captured_calls.md = GitHub main docs/captured_calls.md; pseudonyms.json (142 names) from the workspace mirror. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). OCR RESTORED (William 02:15Z 'add the ability back to ocr a pdf'): tesseract-ocr + poppler-utils + pymupdf installed in the container; bootstrap layout now installs them every run; new helper scripts/helpers/ocr_pdf.py; Drive transport for big scans = download_file_content whose oversized result the harness spills to a local tool-results file (jq .content | base64 -d) - 343,470 bytes reproduced exactly. The Drive connector does NOT OCR images (PNG probe read back empty).
Boards: Insurance Refresh Board - 189 rows on Claude's turn; one new William note (02:15Z, the OCR ask) - answered and the row closed; drops new = 0; Working Denials queue = 0. Board inbox: both registries' applied maps still list only 9/12-9/15 files (the board applied the 0110Z file at 02:11-02:57Z without registering it), 42 run files waiting - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder: nothing modified after 09:00Z 9/17. Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read (row pam-admits-2026-09-17) - nothing newer.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled 0 -> 0 | Exclusions 0 -> 0: the 59 AET12 rows of claim run 1700202 were completed OUTSIDE the routine between 01:13Z and 03:24Z (empty visitlist; %s claim runs listed, none newer than 1700202). gettxhistory on the 15 charts: 68 AET12 charges billdate 09/16/2026, $%.2f insurance balance open, none at $0, no AET12 payment (Medicare paid $%.2f) - not re-sent by anyone. Nothing released, rebilled or written off in the four columns by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after. %s Availity 5(g): nothing new. Working Denials: nothing queued, no denials file written.
FACESHEET OCR: 'Omnissa Horizon.pdf' = Commure PRO visits list 9/2021-9/2026 for pat17471832 (not a facesheet). Cross-check against AMD (gettxhistory typefilter 0 = all 109 charges; typefilter 1 shows only the 27 with an open balance): every stay day on the list is charged (gaps: %s; partial: %s) -> row selwyn-janis-17471832 on William's turn for the PR-39 'same/appeal' decision ($753 of $0-denied 99223/99497 lines now on the patient balance).
PATIENT-BALANCE FINDING (Florida Blue): the 9/14 Availity posts left patient balance = charge minus payment on pat17471832 (the remit's CO-45 was never written off). Corrected %d of %d lines tonight: move_to_ins (no rebill) + manual_post pay 0 / WOINS = remit CO-45 (Availity trace as check number, check date as deposit date); AMD auto-transfers the PR-2 coinsurance back to the patient. WOINS $%.2f. Scope for the next runs: masswriteoffsearch carrier 6062 isinsbalance false = %d charges / %d charts / $%.2f patient balance, %d of them at the full charge ($%.2f; $0 denials the ERA poster transferred to the patient) - new board row bcbs-patient-balance-audit-0918 on Claude's turn; hold Florida Blue patient statements until it is done.
Calls learned: no new AMD call shapes. Behaviours recorded in captured_calls.md: (1) Drive large-file transport for the run; (2) addpayments with pay 0 + WOINS on a charge whose patient balance was moved back to insurance -> AMD auto-transfers the remainder to the patient (the PR-2), so a contractual correction is move_to_ins + manual_post, no reverse move needed; (3) masswriteoffsearch isinsbalance false returns lastpaymentdate null. Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, runs_n, aet_bal, aet_paid, nb, ab, na, aa, era_txt, "; ".join(nocharge) or "none", "; ".join(partial) or "none", len(sav_ok), len(sav_lines), sav_wo, len(bcbs), bcbs_pats, bcbs_tot, len(bcbs_full), bcbs_full_tot, MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read() if os.path.exists("needs_facesheet_list.md") else "# needs_facesheet_list\n"
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 11 PM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("needs_facesheet_list_section.md", "w").write(sec.lstrip("\n"))
    open("captured_calls_additions_%s-11pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 11 PM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes (behaviours recorded)\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 11pm ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
