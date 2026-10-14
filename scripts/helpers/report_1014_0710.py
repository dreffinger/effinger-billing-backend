# PLAIN ENGLISH (run outputs, 3 AM ET 10/14/2026 run 2026-10-14T0710Z)
# Decides: nothing. Writes this run's paperwork from the registers already on disk: the dated section appended to
#   needs_facesheet_list.md, the run report CSV, the captured_calls additions file, the board update file for the
#   Insurance Refresh Board inbox, and the chat-history digest. Chart ids and visit ids only - no patient names.
# Never touches: AdvancedMD, Drive (the connector uploads what this writes), any register.
import json, csv, datetime, os
STAMP = "2026-10-14T0710Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
os.makedirs("chat_history", exist_ok=True); os.makedirs("outbox", exist_ok=True)
insp = json.load(open("registers/insp_%s.json" % STAMP))
resaved = [(v["vid"], v["pid"], v.get("admission")) for v in insp["visits"]]
held = [(v["vid"], v["pid"], v["steps"][-1][:80]) for v in insp["held"]]
byp = [(b["vid"], b["pid"], "; ".join(b["errs"])) for b in insp["bypassed"]]
left = [(l[1], l[2], "; ".join(e[1][:50] for e in l[3])) for l in insp["left"]]
sweep = json.load(open("registers/uni20_bcbs_pre0501_sweep_%s.json" % STAMP))
rows = sweep.get("rows", sweep)
import collections
sw = collections.Counter(str(r.get("action") or "")[:30] for r in rows)
sw_bal = sum(float(r.get("balance") or 0) for r in rows)

needs = """
## 2026-10-14 07:10 UTC - backend billing run (3 AM ET 10/14, ehpa cloud) - run %s

Bootstrap: repo ATTACHED (origin/main cd01e4e at start, main checked out, symlinked to /home/claude/effinger-billing-backend); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no credential file); ONE login 07:15Z; no lock; no START younger than 40 min (0510Z digest carries RUN COMPLETE); v12 precondition greps pass; pseudonyms.json (406 names) installed in both secrets folders; layout from the repo (945 helper files). State bundle restored: none (Drive newest 2026-09-18, older than main). Missing required helpers: none. Routine text delivered v7; the v12 rules on main applied.
Sources: denials queue 0, board drops 0, board rows updated since 04:30Z 2 (both written by the 10/14 chat pass and already on William's turn: chart 17478013 facesheet, chart 24197 CHP member id), Mandatory Approvals page 0 waiting / 5 approved (A-2026-10-14T0155Z-C/J/J-dec/K/K-dec) - see Approvals; Pam Gmail nothing in 2 days; Drive-wide nothing new for billing (no 835 / Availity / facesheet / Claimocity file after 10/13 20:00Z; recent-files list holds only routine, chat and button files).

Columns (list counts): Charge Review 0 -> 0 | Claim Inspector 21 -> 5 | Unbilled 28 -> 28 | Exclusions 1 -> 1 (overview after: 0 / 21 / 28 $5,370 / 6 $1,769 - lags) | ERA 1 check $71.00 -> 1 check $71.00.
- Claim Inspector 21 -> 5: chart 48008's 11/30-12/7/2025 HCA stay (card A-2026-10-14T0510Z-C, re-routed to CAP07 by the 10/14 chat pass) - insp_1014_0710.py wrote admission 11/30/2025 (the chart's own 99223 / most recent 99223 within 45 days) on %d visits (%s) with updextrainsinfo hospitalizationfrom only + full-visit resave onhcfa=1, 0 faults, deceased guard clear (every DOS before the 02/03/2026 date of death); fresh-id bypasses: %d (%s - Pattern 11256 unspecified laterality M84.359A, logged to laterality_flag_log.md). The GitHub Billing Button's live 'columns' run 2026-10-14T0731Z overlapped this pass (its report: 0/20/28/1 -> 0/9/28/1) and bypassed the advisory-only rows (11256 / 20657 on chart 48008 v19426988 / v19427273 / v19427785 / v19427786 / v19428337, chart 44984 v19389068, chart 20670 v19420291) before this run's bypass loop reached them - two engines in the same hour again (docs/BILLING_BUTTON.md WATCH). LEFT 5 standing holds: chart 23177 v19451190 (CCI 24078 / 15775 add-on), chart 44983 v13979435 + v13984519 (Pattern 4852 discharge), chart 22845 v19364378 (Pattern 4852), chart 17472519 v19395738 (S06.5XAS only, payment on the charge - board row). Held by the helper: %s.
- Unbilled 28 -> 28 (unbilled_repair.py: reason rows 0, prior rows 0, left alone 28): 20 'Unresolved Claim Inspector errors' = the standing holds (chart 22845 TRI05 x11 incl. v19362172 - Olson/TRI05 carrier hold; chart 44983 GEH04 x2; chart 17469045 v19362925 BCBS, chart 12183413 v19364497, chart 23456 v19367114, chart 21021 v19372311 / v19372463 HUM01, chart 47127 v19372604 TRI05 - 2024 visits whose charge-level inspector errors are not cleared, left as the earlier runs left them; chart 17472519 v19395738) + 8 'Insurance order is missing' chart 17478013 (HCA 10/5-10/12/2026, $1,430, zero plans; row [name]-17478013 on William's turn since the 10/14 chat pass - every lookup ERR 72 / discovery 0; facesheet needed). The 33 'Payment reason codes', 12 'DOS outside coverage' and 9 chart-48008 rows of the 0510Z scan are gone (cards A-E applied by the 10/14 chat pass + the button's payreasons --unbilled --live).
- Exclusions 1 -> 1: AET12 chart 24750 PREF0288 (carrier-master hold). Overview 6 / $1,769 lags the list.
ERA (step 5): (a) nothing to upload (no new 835 in 'bht Optum era downloads'). (b) before = 1 check / $71.00 unposted: 1053116 UHC W0020208 (details cached, 3 claim rows). (c) era_post --all-unposted --dry: 0 postable / 3 skipped (v19421789 paid 0 settled; v19395670 $71 reversal 'does not match any payments applied from the carrier' x2) - takeback pair, no posting rule, HELD for William's decision (unchanged since 10/11). era_clear --dry: 1 held (denial with write-off 1, unvalidated money 1, unvalidated $0 1). (d)-(e) nothing to post or clear. after = 1 / $71.00. Auto-posted $0; manual-posted 0; residuals $0; checks cleared 0. (g) Availity / Treasury: no new Remittance Viewer PDF or Check/EFT export - nothing to parse or reconcile.
UNI20/BCBS pre-5/1 pass 90 (--min-age 166 --max 60 --carriers UNI20,BCBS --skip-answered passes 1-89): 60 asked ($%s) - %s; 0 candidates claimed, 0 sent (the 28 NOT-ON-FILE answers are the same E0/A7 'cannot provide further status electronically' Medigap-secondary and 2022-23 UHC lines the earlier passes left unsent; none in the timely-filing watch, none re-sent - the ONE REBILL rule and the pool-exhausted finding of passes 7-89 stand). Register registers/uni20_bcbs_pre0501_sweep_%s.json. Timely-filing watch: no new CARC 29.
Approvals (step 0h, last): page 0 waiting; the 5 approved old-claims cards A-2026-10-14T0155Z-C / J / J-dec / K / K-dec were ALREADY APPLIED by the 0310Z run (old_claims_apply.py --live, 10/13 23:47-23:50Z per its additions file) - this run read every named visit live (approvals_verify_1014_0710.py, registers/approvals_verify_%s.json): card C AET07 payments $653.49 (checks 825326000023348 / 825364000177048 / 882611801041201) + WOINS $373.51; J WOCAID2ND; J-dec WOINS $69.16; K WOCAID2ND + WOINS $254.81; K-dec $59.11 - every line insbal 0.00. Recorded done on the page (versions 4) and in practices/ehpa/registers/approvals_pending.json (own commit, pushed to main); not run again. Cards A-2026-10-14T0510Z-A..E: done by the 10/14 chat pass (page read 07:2xZ).
Writes in AdvancedMD: %d updextrainsinfo + %d full-visit resaves (admission dates), %d bypassclaimedits. Dollars re-sent: $0 (the 48008 claims were sent frequency-1 by the chat pass; this run only cleared their inspector holds). Write-offs: none by this run. Permission-classifier refusal (verbatim, not retried): `for k in C J J-dec K K-dec; do ... python3 old_claims_apply.py --only $k --stamp 1013 ...; done` (DRY runs) -> "Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Real-World Transactions]." - replaced by the read-only live verification above (no package was run).
Calls learned: 0 new shapes (gettxhistory visitid= read, updextrainsinfo, updvisitwithnewcharges full echo, bypassclaimedits, era checks/checkdetails, posterapayments dry, massrebillsearch + Stedi 276/277 - all in the registry). Vocabulary entries added: 0. Helpers this run: insp_1014_0710.py (stamp copy of insp_1014_0510.py), approvals_verify_1014_0710.py (read-only), approvals_record_1014_0710.py (register bookkeeping), report_1014_0710.py.
Waiting on William: the 1053116 UHC W0020208 takeback decision ($71); chart 17478013 HCA facesheet ($1,430, 8 visits); chart 24197 CHP member id ($711); the AET12 carrier master (chart 24750); the standing inspector holds (charts 23177 / 44983 / 22845 / 17472519); the two engines (Billing Button live at :17/:31 + this routine at :10) still overlap every odd hour.
""" % (STAMP, len(resaved), ", ".join("v%s" % v for v, p, a in resaved), len(byp), ", ".join("v%s" % v for v, p, e in byp),
       "; ".join("v%s pat%s %s" % h for h in held) or "none", ("%.2f" % sw_bal), ", ".join("%d %s" % (n, k) for k, n in sw.most_common()), STAMP, STAMP,
       sum(1 for v in resaved if v[2]), len(resaved), len(byp))
open("needs_facesheet_list.md", "a").write(needs)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(needs)

# run report CSV
csvp = "_run report 10-14 0710.csv"
with open(csvp, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["column", "status", "chart", "visit", "dos", "carrier", "error", "action"])
    w.writerow(["Charge Review", "cleared", "", "", "", "", "", "0 before -> 0 after"])
    for v, p, a in resaved: w.writerow(["Claim Inspector", "cleared", p, v, "", "CAP07", "Hospitalization From Date empty", "admission %s written, full-visit resave onhcfa=1" % a])
    for v, p, e in byp: w.writerow(["Claim Inspector", "cleared", p, v, "", "", e, "advisory bypassed (fresh id)"])
    for v, p, e in left: w.writerow(["Claim Inspector", "remaining", p, v, "", "", e, "standing hold"])
    for v, p, s in held: w.writerow(["Claim Inspector", "remaining", p, v, "", "", s, "held by the helper"])
    scan = json.load(open("scan_%s/summary_after.json" % STAMP))
    for r in scan["unbilled"]:
        vid = r.get("vid") or r.get("visitid") or r.get("id"); pid = r.get("pid") or r.get("patientid"); carr = r.get("carrier") or r.get("carriercode") or ""
        errs = "; ".join(r.get("errors") or r.get("reasons") or [])
        act = "facesheet needed (William)" if pid == "17478013" else "standing hold (inspector / carrier)"
        w.writerow(["Unbilled", "remaining", pid, vid, r.get("dos", ""), carr, errs, act])
    w.writerow(["Exclusions", "remaining", "24750", "", "", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID", "carrier-master hold (William)"])
    w.writerow(["ERA", "remaining", "", "19395670", "2024-06-12", "UHC W0020208 (check 1053116)", "$71 reversal does not match any payment from the carrier", "takeback pair held for William's decision"])
    w.writerow(["Approvals", "done", "", "", "", "", "A-2026-10-14T0155Z-C/J/J-dec/K/K-dec", "already applied 10/13 23:47-23:50Z by the 0310Z run; verified live, recorded done"])
print("wrote", csvp)

add = """# captured_calls additions - 2026-10-14 0710 UTC (3 AM ET 10/14) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt; AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory typefilter=0 (insp_1014_0710.py admission anchors; approvals_verify_1014_0710.py visitid= reads x15), getchargedetaildataicd10 (resave.detail), updextrainsinfo hospitalizationfrom + updvisitwithnewcharges full-visit resave onhcfa=1 (insp_1014_0710.py, 9 visits of chart 48008), bypassclaimedits (4 fresh ids), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after), posterapayments dry (era_post.py --all-unposted --dry: 1053116 0 postable / 3 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x60 (claim_status_sweep.py pass 90).

Behaviors noted:
- The Billing Button's live 'columns' run 2026-10-14T0731Z (commit 8dbfcc7) ran in the same minutes as this run's inspector pass: between the 07:20Z before-scan (21 inspector visits) and the helper's bypass loop (07:3xZ) seven advisory-only visits (11256 / 20657) and their batches were already gone - the button bypassed them. Neither engine wrote the same visit twice (the button bypasses advisory-only rows; this run resaved the Hospitalization-From-Date rows), but the overlap WATCH stands.
- The five approved old-claims cards were applied by the 0310Z run and left 'approved' on the page because that run's claim commit was refused; a read-only gettxhistory visitid= pass is enough to prove a package applied (check numbers OLD1013 / OLD1013B and the 277 check numbers on the payments) - record done, never re-run.
- The classifier refused a shell for-loop over old_claims_apply.py DRY runs ([Real-World Transactions]); single named-helper commands ran.
"""
open("captured_calls_additions_2026-10-14_0710UTC-3amET-ehpa-cloud.md", "w").write(add)

ops = [
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {},
  "append": {"checks": [{"ok": "na", "result": "3 AM ET 10/14: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing new for billing after 10/13 20:00Z); Working Denials queue 0; board drops 0; approvals 0 waiting (the 5 approved old-claims cards had already been applied by the 0310Z run - verified live and recorded done); Pam Gmail nothing in 2 days. ERA Center 1 check $71.00 before and after (1053116 UHC W0020208 takeback pair, held for your decision). Columns 0/21/28/1 -> 0/5/28/1: chart 48008's 9 re-routed HCA visits got admission 11/30/2025 + onhcfa=1 and cleared; the 5 standing inspector holds and the 28 Unbilled holds (chart 17478013 facesheet x8, the TRI05 / GEH04 / 2024 inspector holds) unchanged. UNI20/BCBS pre-5/1 pass 90: 60 asked, 16 pending, 28 not-on-file (unchanged pool), 0 sent.", "src": "3am ET 10/14 columns run (ehpa cloud) - run %s", "when": "10/14"}]}},
 {"op": "upsert", "collection": "items", "id": "[name]-17478013", "set": {},
  "append": {"checks": [{"ok": "no", "result": "3 AM ET 10/14: still no facesheet in the HCA/TMH/PCC/Claimocity folders, no Pam email, no board drop; the eight visits (99223 10/5 + 99233 10/6-10/12/2026, $1,430) stay in Unbilled 'Insurance order is missing' - your turn (HCA facesheet).", "src": "3am ET 10/14 columns run (ehpa cloud) - run %s", "when": "10/14"}]}},
]
bu = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": [dict(o, append={k: [dict(c) for c in v] for k, v in o["append"].items()}) for o in ops]}
for o in bu["ops"]:
    for c in o["append"]["checks"]: c["src"] = c["src"] % STAMP
json.dump(bu, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

digest = "# %s run digest - backend billing run, 3 AM ET 10/14 (ehpa cloud)\n" % STAMP + needs.split("\n", 2)[2] + """
Mirror: GitHub - approvals register committed alone and pushed to main first; then the gated tree (phi_gate tree .) committed and pushed to main + claude/effinger-billing-backend-mirror-w74pqv + claude/pensive-einstein-g8zbou (see the final summary for the result per leg); Postman unchanged (no new vocabulary entry); Drive: board_updates_%s.json (2 ops) to 'board inbox', captured_calls_additions to 'billing agent project files', needs section + this run's helpers to 'workspace mirror', this digest to 'chat history'; run report CSV delivered with SendUserFile. State bundle not uploaded (no patient_db; era_details 1 check; registers on main).

## SHARED LESSONS
- %s | backend billing run | WATCH | the Billing Button's live columns run (:17 / :31 past the odd hours) cleared 7 advisory-only inspector rows in the same minutes this routine resaved the Hospitalization-From-Date rows of the same chart (48008) - no double write, but the two engines keep overlapping | reports/button/latest.json
- %s | backend billing run | FIX | an approved package whose run was never recorded (claim commit refused) is proven applied by a read-only gettxhistory visitid= pass (payments / write-offs dated the run, check numbers OLD1013 / the 277 checks) - record done on the page + register, never re-run | approvals_verify_1014_0710.py

RUN COMPLETE
""" % (STAMP, NOW, NOW)
open("chat_history/%s run digest.md" % STAMP, "w").write(digest)
print("wrote needs section, additions, board_updates, digest")
