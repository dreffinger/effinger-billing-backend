# PLAIN ENGLISH (run outputs for the 5am ET 9/18/2026 slot - ehpa cloud run 2026-09-18T0910Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the ERA
#   before/after snapshots, the dismissed check's cached details and the AET12 verify register, then writes:
#   - "_run report 9-18 0910.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-18T0910Z.json (Insurance Refresh Board inbox file: appends on the standing rows only)
#   - denials_updates_2026-09-18T0910Z.json (one note: the $0 UNI01 denial-only check dismissed this run)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final)
# Never touches: AMD, the board databases. Member ids / MBIs never leave the registers.
import csv, json, os, datetime, sys
S = "2026-09-18T0910Z"; SRC = "5am ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "5 AM ET 9/18"
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
ERA_NEW = "1 new $0 check 1051705 UNI01 NO-PAY-202609160007055 (dated 9/16, one claim: visit 19452626 of pat17477023, claim status 1 = processed as primary, OA-23 $206.00 'impact of prior payer adjudication', remark #AM, no money, no MA63/M76/M64; the visit's insurance balance is $142.72 and stays for the denial handling)"
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row wexford-shelagh-17471007 on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart, zero insplans (getdemographic re-read 09:16Z this run); cascade exhausted 9/18 05:xxZ (Stedi MBI ERR 72 / discovery 0, or CHP MA per CMS without a member id); no facesheet, Pam email or drop since - held on William's turn (0510Z board rows)"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action="%d unposted checks / $%.2f before -> %d / $%.2f after; locks release-expired sent; era_details cache 1/1; era_post --all-unposted 0 money checks; fallback dry+live 0 lines; era_clear dismissed 1 (denial-only, no money); 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 09:00Z 9/17); no MA63/M76/M64 work" % (nb, ab, na, aa))
add("ERA", "dismissed", "pat17477023", "", "UNI01", "OA-23 $206.00 denial-only, remark #AM", "dismissed by era_clear (no postable money; the line waits for the Working Denials rerun)", check="1051705", payer="UNI01 NO-PAY-202609160007055", visit="19452626", amount="0.00")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: 189 rows on Claude's turn read, drops 0 new, no William note newer than 02:15Z 9/18 (already answered); board inbox: neither registry's applied map names a file present in the inbox root - nothing trashed")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC), Optum ERA folder, treasury folder, project-files root: nothing modified after 09:00Z 9/17 except the routine's own files; Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read (row pam-admits-2026-09-17) - nothing newer; Claimocity drop: newest HL7 copy is download__20260909... (9/9 07:30Z) - no download__20260918 file landed at the ~07:30Z pull despite the 9/18 chat redeploy (9 days stale, over the 2-day health line; the AMD charge path itself is unaffected)")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 full-charge $0-denial lines are PR-39 / wrong-payer decisions); hold Florida Blue patient statements")
with open("_run report 9-18 0910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("aet12-carrier-cpid", "no", "5am ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. %s. locks release-expired sent; era_post --all-unposted 0 money checks; fallback dry + live 0 lines; era_clear dismissed 1051705 (denial-only, no money); 0 addpayments faults; no new 835s in 'bht Optum era downloads' (nothing to upload)." % (SRC, S, nb, ab, na, aa, ERA_NEW))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 09:00Z 9/17) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the ten of 18:50Z 9/17 already read. Claimocity drop: newest HL7 copy still 9/9 07:30Z - no 9/18 file from the redeployed pull job.")
for rid, txt in (("conway-shelby-17477775", "chart still has zero insurance plans (getdemographic 09:16Z); no facesheet in hca/tmh/PCC/Claimocity folders, Pam Gmail sweep newer_than:2d = the ten 9/17 emails already read, no board drop; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("thurlow-nerys-17477776", "chart still has zero insurance plans (getdemographic 09:16Z); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; no facesheet, Pam email or drop since; 3 visits stay in Unbilled"),
                 ("gorman-davin-17477779", "chart still has zero insurance plans (getdemographic 09:16Z); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; 2 visits stay in Unbilled 'Insurance order is missing'")):
    app(rid, "no", txt)
app("bcbs-patient-balance-audit-0918", "na", "5am ET 9/18: not worked this run (same blocker as 0710Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements.")
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
dops = [{"op": "upsert", "collection": "commands", "id": "cmd-claude-%s" % S, "set": {"command": "note", "by": "Claude", "target": "board", "status": "done", "note": "", "result": "5am ET 9/18 run: ERA Center 1 -> 0. Dismissed check 1051705 UNI01 NO-PAY-202609160007055 ($0, dated 9/16): visit 19452626 OA-23 $206.00 'impact of prior payer adjudication' (remark #AM), no money, no MA63/M76/M64; the visit keeps its $142.72 insurance balance - this denial line joins the board on the next 'rerun'. Queue was empty; nothing else to act on."}}]
json.dump({"schema": "wd-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": dops}, open("denials_updates_%s.json" % S, "w"), indent=1)
print("board ops", len(ops), "denials ops", len(dops))
sec = """## %s columns run (ehpa cloud Code Routine, 09:09-%s UTC 9/18, run %s)
Bootstrap: repo ATTACHED (origin/main 360efdb, session branch claude/pensive-einstein-bs2y4d, layout 340 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_0721UTC was still uploading when this run started (part 23 of 25 at 09:10Z) - not unpacked; registers restored from practices/ehpa/registers/ (0710Z state), needs_facesheet sections rebuilt from nightly/runs/ (24 sections); captured_calls.md = GitHub main docs/captured_calls.md + the 0555Z nightly-cascade and 0710Z additions; pseudonyms.json 170 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 0710 START (07:14Z) had its RUN COMPLETE digest (07:23Z) - proceeded.
Boards: Insurance Refresh Board - 189 rows on Claude's turn read, drops 0 new, no William note newer than 02:15Z 9/18 (the OCR ask, answered by the 0310Z run); Working Denials queue 0. Board inbox: neither registry's applied map names a file present in the inbox root - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder, project-files root: nothing modified after 09:00Z 9/17 except the routine's own files. Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read - nothing newer. Claimocity drop: newest HL7 copy is still download__20260909 (9/9 07:30Z); the redeployed pull job produced no download__20260918 file at its ~07:30Z run - 9 days over the 2-day health line (the AMD charge path is separate and unaffected).
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 (no batches) | Unbilled %s -> %s ($%s): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read at 09:16Z; the 0510Z cascade stands - ERR 72 + discovery 0, or CHP MA per CMS without a member id; no new facesheet, Pam email or drop) held on William's turn, nothing re-spent on Stedi | Exclusions 0 -> 0 (no claim run newer than 1700202, %s runs listed; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released, rebilled or written off by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after. %s. locks release-expired sent; era_post --all-unposted 0 money checks; fallback dry + live 0 lines; era_clear dismissed 1051705 (denial with write-off proposed $206, no postable money); 0 addpayments faults; no new 835s (nothing to upload). Availity 5(g): nothing new.
OPEN (Claude's turn, from the 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 - not worked (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 $0-denial lines are PR-39 / wrong-payer decisions). Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes. Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ova.get("unbillableamount"), runs_n, aet_bal, nb, ab, na, aa, ERA_NEW, MIRROR)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + sec)
    os.makedirs("chat_history", exist_ok=True)
    addn = """# captured_calls additions - %s (5am ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- A UnitedHealthcare (UNI01) NO-PAY 835 with one OA-23 line (claim status 1, 'impact of prior payer adjudication', remark #AM) lands in the ERA Center as a $0 denial-only check; era_clear classifies it 'denial with write-off (cascade handles)' and dismisses it, and the visit keeps its open insurance balance for the Working Denials rerun. Not MA63/M76/M64 - no dx work.
- Cross-container guard: a START file whose run is still uploading its state bundle (0721UTC set at part 23/25 at 09:10Z) but already has its RUN COMPLETE digest = proceed; restore state from GitHub main practices/ehpa/registers/ + nightly/runs/ rather than an incomplete bundle set.
- Claimocity drop health line (proposed v8 prompt line): newest download__ file 9/9 07:30Z at 09:14Z 9/18 = 9 days; the 9/18 redeploy (google.auth.default + folder shared to the service account) produced no 9/18 file.
""" % S
    open("captured_calls_additions_%s-5amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(addn)
    dig = "# %s run digest - backend billing run, 5am ET 9/18/2026 slot (ehpa cloud)\n\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
else:
    print(sec)
