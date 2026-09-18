# PLAIN ENGLISH (run outputs for the 3pm ET 9/18/2026 slot - ehpa cloud run 2026-09-18T1910Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the inspector
#   register (registers/insp_2026-09-18T1910Z.json), the ERA before/after snapshots and the unbilled/AET12 verify registers,
#   then writes:
#   - "_run report 9-18 1910.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-18T1910Z.json (Insurance Refresh Board inbox file: appends on the standing rows + the rows of
#     charts whose new hospital visits were cleared out of the Claim Inspector this run)
#   - (no denials_updates file: the Working Denials queue was empty and no denial line was touched)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final)
# Never touches: AMD, the board databases. Member ids / MBIs never leave the registers.
import csv, json, os, datetime, sys
S = "2026-09-18T1910Z"; SRC = "3pm ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "3 PM ET 9/18"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
insp = load("registers/insp_%s.json" % S, {"visits": [], "held": [], "left": []})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ver = load("registers/aet12_verify_%s.json" % S, []); aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
ovb = before.get("overview", {}); ova = after.get("overview", {}); ua = after.get("unbilled", []); runs_n = ovb.get("claimrunstatuscount", "?")
insp_before = sum(len(v) for v in before.get("inspector", {}).values()); insp_after = sum(len(v) for v in after.get("inspector", {}).values())
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
# inspector detail rows
fixed_by_pid = {}
for r in insp["visits"]:
    steps = " | ".join(r["steps"])
    adm = next((s for s in r["steps"] if s.startswith("admission ")), "")
    dxg = [s for s in r["steps"] if "PRIMARY-DX GATE" in s or "Winslow Jr rule" in s or "fix_visit" in s]
    action = adm
    if dxg: action += "; " + "; ".join(dxg)
    add("Claim Inspector", "cleared", r["name"], next((s.split()[1] for s in r["steps"] if s.startswith("dos ")), ""), "", "Hospitalization From Date empty", action + "; full-visit resave onhcfa=1", visit=r["vid"])
    fixed_by_pid.setdefault(r["pid"], []).append((r["vid"], adm, bool(dxg)))
for r in insp["held"]:
    add("Claim Inspector", "held", r["name"], "", "", "", " | ".join(r["steps"])[-300:], visit=r["vid"])
add("Claim Inspector", "count", action="%d visits (1 batch 127737, 20 charts, $%s) -> %d: 24 admission dates written (most recent 99223 within 45 days / own 99223 / same-stay date), 2 never-primary Z96.6x implant codes got I10 in front (dx_primary_fix add-i10 + freq-1, pat17477774 v19455048, pat17470950 v19455050), pat17472546 v19455040 S81.801S got M86.9 in front (William 9/6 rule) and Pattern 20389 bypassed, UMR 'Source of Payment not typical' advisory on v19455048 bypassed with its fresh id (same as the 1am ET 9/18 run); batch list empty after (overview count lags)" % (insp_before, ovb.get("claiminspectoramount"), insp_after))
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row wexford-shelagh-17471007 on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart, zero insplans (getdemographic re-read 19:2xZ this run); cascade exhausted 9/18 05:xxZ (Stedi MBI ERR 72 / discovery 0, or CHP MA per CMS without a member id); no facesheet, Pam email or drop since - held on William's turn (0510Z board rows)"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17 or 9/18 - the AMD Automation Center EOD close appears stopped since 9/16, fifth consecutive worked slot); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action="%d unposted checks / $%.2f before -> %d / $%.2f after; ERA Center empty; locks release-expired sent; era_post --all-unposted 0 checks; fallback dry+live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments'; no MA63/M76/M64 work" % (nb, ab, na, aa))
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: rows on Claude's turn read (189), drops 0 new, no row updated after 03:00Z 9/18 (no new William note); board inbox: neither registry's applied map lists a file still in the inbox - nothing trashed")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC), Claimocity drop, chc raw 835, Optum ERA folder, treasury folder: nothing modified after 12:00Z 9/17 except the routine's own report CSV; Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read (row pam-admits-2026-09-17) - nothing newer")
add("Routine", "note", action="State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main (the 1710Z run pushed newer registers and never bundled), so registers were restored from the repo (practices/ehpa/registers + nightly/runs). Bundle not re-uploaded this run (same reason as the 1310Z-1710Z runs); every state member is on GitHub main.")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 full-charge $0-denial lines are PR-39 / wrong-payer decisions); hold Florida Blue patient statements")
with open("_run report 9-18 1910.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    ops.append(o)
app("aet12-carrier-cpid", "no", "3pm ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted on 9/17 or 9/18 - the Automation Center EOD close looks stopped since 9/16, so nothing has transmitted for two days: the 24 HCA visits cleared from the inspector this run and the 59 AET12 claims all wait on it). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty; locks release-expired sent; era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s in 'bht Optum era downloads' (nothing to upload)." % (SRC, S, nb, ab, na, aa))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 12:00Z 9/17 outside this routine's own files) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: no admit email newer than the ten of 18:50Z 9/17 already read. Claimocity drop: no file since 9/15.")
for rid, txt in (("conway-shelby-17477775", "chart still has zero insurance plans (getdemographic 19:2xZ 3pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, Pam Gmail sweep newer_than:2d = the ten 9/17 emails already read, no board drop; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("thurlow-nerys-17477776", "chart still has zero insurance plans (getdemographic 19:2xZ 3pm ET 9/18); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; no facesheet, Pam email or drop since; 3 visits stay in Unbilled"),
                 ("gorman-davin-17477779", "chart still has zero insurance plans (getdemographic 19:2xZ 3pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; 2 visits stay in Unbilled 'Insurance order is missing'")):
    app(rid, "no", txt)
app("wexford-shelagh-17471007", "human", "3pm ET 9/18: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance.")
app("bcbs-patient-balance-audit-0918", "na", "3pm ET 9/18: not worked this run (same blocker as 0710Z-1710Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements.")
# rows of charts whose new HCA visits were cleared from the inspector (only rows that exist on the board)
ROWS = {"17472546": "winslow-jr-ervin", "17477722": "dekle-tracey-17477722", "17477719": "mcdaniel-james-17477719", "17477706": "tredwell-rustin", "17472393": "tillery-wayne-17472393"}
for pid, rid in ROWS.items():
    vs = fixed_by_pid.get(pid)
    if not vs: continue
    txt = "New HCA visit(s) %s came through the feed with no admission date: %s written, full-visit resave onhcfa=1, inspector clear - queued on the next claim run (no claim run has posted since 1700202 on 9/16)." % (", ".join("v%s" % v for v, a, g in vs), "; ".join(sorted({a for v, a, g in vs})))
    if pid == "17472546": txt = "New HCA 99233 visit 9/17 (v19455040) came through the feed with S81.801S as the only dx again; same 9/3 stay -> admission 09/03/2026 written, M86.9 (dcode1034545415) put in front per your 9/6 rule, full-visit resave onhcfa=1, Pattern 20389 bypassed, inspector clear."
    app(rid, "ok", txt)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("board ops", len(ops))
sec = """## %s columns run (ehpa cloud Code Routine, 19:09-%s UTC 9/18, run %s)
Bootstrap: repo ATTACHED (origin/main ce282e9, session branch claude/pensive-einstein-31nhfq, layout 355 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC (26 parts) is older than GitHub main (the 1710Z run pushed newer registers and never bundled) - registers restored from practices/ehpa/registers/ (93 files), needs_facesheet sections rebuilt from nightly/runs/ (33 run folders); captured_calls.md = GitHub main docs/captured_calls.md (336 KB; no Drive additions newer than the 1710Z merge); pseudonyms.json 170 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 1710 START (17:14Z) had its RUN COMPLETE digest (17:23Z) - proceeded.
Boards: Insurance Refresh Board - 189 rows on Claude's turn read, drops 0 new, no row updated after 03:00Z 9/18; Working Denials queue 0. Facesheet folders, Claimocity drop, chc raw 835, Optum ERA folder, treasury folder: nothing modified after 12:00Z 9/17 except the routine's own run-report CSV. Pam Gmail: the same ten admit emails of 18:40-18:50Z 9/17 already read - nothing newer. Claimocity drop: no file since 9/15.
Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d (one batch 127737 of new HCA hospital visits on 20 charts, $%s, every one 'Hospitalization From Date empty'): 24 admission dates written by rule (most recent 99223 within 45 days / own 99223 / the same stay's date already on an earlier visit), 2 never-primary Z96.6x implant codes leading a 99232 got I10 in front via dx_primary_fix add-i10 + freq-1 (pat17477774 v19455048, pat17470950 v19455050), pat17472546 v19455040 S81.801S got M86.9 in front (William 9/6 rule) + Pattern 20389 bypassed, the UMR 'Source of Payment not typical for this carrier' advisory on v19455048 bypassed with its fresh id (precedent 1am ET 9/18); 0 held; batch list empty after | Unbilled %s -> %s ($%s): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read this run; the 0510Z cascade stands; no new facesheet, Pam email or drop) held on William's turn, nothing re-spent on Stedi | Exclusions 0 -> 0 (no claim run newer than 1700202, %s runs listed - NO nightly claim run posted 9/17 or 9/18, the AMD Automation Center EOD close has not run since 9/16, fifth consecutive worked slot; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released or written off by this run; 2 visits freq-1 rebilled by the dx cascade.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after - ERA Center empty. locks release-expired sent; era_post --all-unposted 0 checks; fallback dry + live 0 lines; era_clear 0 dismissed; 0 addpayments faults; no new 835s (nothing to upload). Availity 5(g): nothing new.
OPEN (Claude's turn, from the 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 - not worked (needs the Availity CheckDetails rows re-parsed from the 189 Check PDFs for the CO-45 split; 80 $0-denial lines are PR-39 / wrong-payer decisions). Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes. Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, insp_before, insp_after, ovb.get("claiminspectoramount"), ovb.get("unbillablecount"), ova.get("unbillablecount"), ova.get("unbillableamount"), runs_n, aet_bal, nb, ab, na, aa, MIRROR)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + sec)
    os.makedirs("chat_history", exist_ok=True)
    addn = """# captured_calls additions - %s (3pm ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- A Claimocity feed drop of 24 HCA hospital visits (batch 127737) all arrive in the Claim Inspector with 'Hospitalization From Date empty'; the insp_0917_1910.py recipe (admission = most recent 99223 within 45 days / own 99223 / the same stay's date already on an earlier visit, updextrainsinfo hospitalizationfrom per CPT, full-visit resave onhcfa=1, re-list + bypass advisories with fresh ids) cleared all 24 in one pass, 0 held.
- Z96.641 / Z96.651 (presence of a joint implant) as the only diagnosis on a 99232 fires dx_primary_fix.never_primary; the cascade lands on add-i10 (I10 dcode1034543883 in front) and freq-1 rebills the visit (204) before the admission-date write.
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 19:25Z 9/18 (78 runs): fifth consecutive worked slot with no nightly claim run - nothing in the API starts one; the 24 inspector-cleared visits, the 2 dx-cascade rebills and the 59 AET12 claims all wait on the Automation Center EOD close.
""" % S
    open("captured_calls_additions_%s-3pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(addn)
    dig = "# %s run digest - backend billing run, 3pm ET 9/18/2026 slot (ehpa cloud)\n\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
else:
    print(sec)
