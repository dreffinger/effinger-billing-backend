# PLAIN ENGLISH (run outputs for the 9am ET 9/18/2026 slot - ehpa cloud run 2026-09-18T1310Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA
#   before/after snapshots, era_details/1051706.json, the unbilled/AET12 verify registers, then writes:
#   - "_run report 9-18 1310.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-18T1310Z.json (Insurance Refresh Board inbox file: appends on the standing rows only)
#   - denials_updates_2026-09-18T1310Z.json (Working Denials inbox file: one note command about the dismissed
#     WEL04 $0 denial check 1051706 - its two claims wait for the next 'rerun'; queue itself was empty)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final)
# Never touches: AMD, the board databases. Member ids / MBIs never leave the registers.
import csv, json, os, datetime, sys
S = "2026-09-18T1310Z"; SRC = "9am ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "9 AM ET 9/18"
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
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []); runs_n = ovb.get("claimrunstatuscount", "?")
# the one ERA check this run saw (dismissed): summarize its claims from the cache, visit ids only
chk = load("era_details/1051706.json", {}).get("eracheckdetails", [])
chk_lines = []
for c in chk:
    chk_lines.append("v%s DOS %s: %s / %s (insurance balance already $%.2f)" % (c.get("visitid"), (c.get("dos") or "")[:10],
                     ", ".join("%s $%.2f" % (x["reasoncode"], f(x["reasonamt"])) for x in c.get("carc", [])),
                     " ".join(sorted({x["remarkcode"] for x in c.get("rarc", []) if x.get("remarkcode") and not x["remarkcode"].startswith("#")})) or "no RARC",
                     f(c.get("insurancebalance"))))
CHK = "WEL04 check 1051706 (1003559395, dated 9/17, $0 paid, %d claims): %s; no MA63/M76/M64 - dismissed, the denial lines wait for the Working Denials 'rerun'" % (len(chk), "; ".join(chk_lines))
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row west-shirley-17471007 on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart, zero insplans (getdemographic re-read 13:17Z this run); cascade exhausted 9/18 05:xxZ (Stedi MBI ERR 72 / discovery 0, or CHP MA per CMS without a member id); no facesheet, Pam email or drop since - held on William's turn (0510Z board rows)"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17 or 9/18 - the AMD Automation Center EOD close appears stopped since 9/16); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action="%d unposted checks / $%.2f before -> %d / $%.2f after; locks release-expired sent; era_details cache 1 (new check); era_post --all-unposted 0 money checks; fallback dry+live 0 lines; era_clear 1 looked at, 1 dismissed ($0 denial-only), 0 $0 lines posted; 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments'; no MA63/M76/M64 work" % (nb, ab, na, aa))
add("ERA", "dismissed", carrier="WEL04", error="denial-only $0 check", action=CHK, check="1051706", payer="WEL04", amount="0.00")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: 189 rows on Claude's turn read, drops 0 new, no row updated after 09:30Z 9/18 (no new William note; his 02:15Z 'add the ability back to ocr a pdf' note was answered by the 0310Z run - OCR tools install in bootstrap layout and were present again this run); board inbox: neither registry's applied map lists a file still in the inbox - nothing trashed")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC), Claimocity drop, Optum ERA folder, treasury folder: nothing modified after 12:00Z 9/17 except the routine's own files (Claimocity drop: no file since 9/15, no download__20260918); Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read (row pam-admits-2026-09-17) - nothing newer")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 full-charge $0-denial lines are PR-39 / wrong-payer decisions); hold Florida Blue patient statements")
with open("_run report 9-18 1310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("aet12-carrier-cpid", "no", "9am ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted on 9/17 or 9/18 - the Automation Center EOD close looks stopped since 9/16). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. One new $0 denial-only check arrived and was dismissed: %s. locks release-expired sent; era_post --all-unposted 0 money checks; fallback dry + live 0 lines; 0 addpayments faults; no new 835s in 'bht Optum era downloads' (nothing to upload)." % (SRC, S, nb, ab, na, aa, CHK))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 12:00Z 9/17 outside this routine's own files) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the ten of 18:50Z 9/17 already read. Claimocity drop: no file since 9/15 - no 9/18 file.")
for rid, txt in (("connell-shelley-17477775", "chart still has zero insurance plans (getdemographic 13:17Z); no facesheet in hca/tmh/PCC/Claimocity folders, Pam Gmail sweep newer_than:2d = the ten 9/17 emails already read, no board drop; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("thomas-nancy-17477776", "chart still has zero insurance plans (getdemographic 13:17Z); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; no facesheet, Pam email or drop since; 3 visits stay in Unbilled"),
                 ("gordon-david-17477779", "chart still has zero insurance plans (getdemographic 13:17Z); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; 2 visits stay in Unbilled 'Insurance order is missing'")):
    app(rid, "no", txt)
app("west-shirley-17471007", "human", "9am ET 9/18: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance.")
app("bcbs-patient-balance-audit-0918", "na", "9am ET 9/18: not worked this run (same blocker as 0710Z/0910Z/1110Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements.")
app("facesheet-unread-omnissa-horizon-0916", "ok", "9am ET 9/18: OCR is back for good - tesseract-ocr + poppler-utils install in every run's bootstrap layout and ocr_pdf.py rides in the repo; both were present again this run. Your 02:15Z note was answered by the 3am ET run: 'Omnissa Horizon.pdf' is the Commure visits list for pat17471832 (not a facesheet), already cross-checked against the chart. Nothing left on this row.")
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("board ops", len(ops))
dops = [{"op": "upsert", "collection": "commands", "id": "cmd-claude-%s" % S, "set": {"command": "note", "by": "Claude", "target": "board", "status": "done", "note": "",
         "result": "9am ET 9/18 ERA step: %s. Queue was empty; nothing else dismissed." % CHK}}]
json.dump({"schema": "wd-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": dops}, open("denials_updates_%s.json" % S, "w"), indent=1)
print("denials ops", len(dops))
sec = """## %s columns run (ehpa cloud Code Routine, 13:09-%s UTC 9/18, run %s)
Bootstrap: repo ATTACHED (origin/main 2c5b929, session branch claude/pensive-einstein-j4c03e, layout 347 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC was still being uploaded by the 1110Z run (17 of 26 parts at 13:08Z) - not unpackable; registers restored from practices/ehpa/registers/ (85 files, 1110Z state), needs_facesheet sections rebuilt from nightly/runs/ (26 sections); captured_calls.md = GitHub main docs/captured_calls.md; pseudonyms.json 170 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 1110 START (11:13Z) older than 40 min and its RUN COMPLETE digest is on GitHub main (the Drive copy was not listed) - proceeded.
Boards: Insurance Refresh Board - 189 rows on Claude's turn read, drops 0 new, no row updated after 09:30Z 9/18 (William's 02:15Z OCR note was answered by the 0310Z run); Working Denials queue 0. Facesheet folders, Claimocity drop, Optum ERA folder, treasury folder: nothing modified after 12:00Z 9/17 except the routine's own files. Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read - nothing newer. Claimocity drop: no file since 9/15 (no download__20260918).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled %s -> %s ($%s): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read at 13:17Z; the 0510Z cascade stands - ERR 72 + discovery 0, or CHP MA per CMS without a member id; no new facesheet, Pam email or drop) held on William's turn, nothing re-spent on Stedi | Exclusions 0 -> 0 (no claim run newer than 1700202, %s runs listed - NO nightly claim run posted 9/17 or 9/18, the AMD Automation Center EOD close has not run since 9/16; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released, rebilled or written off by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after. %s. locks release-expired sent; era_post --all-unposted 0 money checks; fallback dry + live 0 lines; 0 addpayments faults; no new 835s (nothing to upload). Availity 5(g): nothing new.
OPEN (Claude's turn, from the 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 - not worked (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 $0-denial lines are PR-39 / wrong-payer decisions). Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes. Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ova.get("unbillableamount"), runs_n, aet_bal, nb, ab, na, aa, CHK, MIRROR)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + sec)
    os.makedirs("chat_history", exist_ok=True)
    addn = """# captured_calls additions - %s (9am ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 13:15Z 9/18 (78 runs): the third consecutive slot with no nightly claim run - nothing in the API starts one; William closes the day / checks the Automation Center rule.
- WEL04 $0 denial-only ERA 1051706 (2 claims, CO96 + OA23 with N448, one line also CO4/N56): both visits already at $0 insurance balance - era_clear dismisses such a check straight away (no money, no MA63/M76/M64); the denial lines go to the Working Denials rerun via the denials inbox note.
- Cross-container timing: the 1110Z run was still uploading its state bundle (one 8 KB part every ~4 minutes) when this run started two hours later; a bundle whose part count is short of its manifest is skipped and the repo's practices/ehpa/registers + nightly/runs are the restore source (same precedence as 1110Z).
""" % S
    open("captured_calls_additions_%s-9amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(addn)
    dig = "# %s run digest - backend billing run, 9am ET 9/18/2026 slot (ehpa cloud)\n\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
else:
    print(sec)
