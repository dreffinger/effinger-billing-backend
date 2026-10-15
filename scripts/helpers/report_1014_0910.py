# PLAIN ENGLISH (run outputs, 5 AM ET 10/14/2026 run 2026-10-14T0910Z)
# Decides: nothing. Writes this run's paperwork from the registers already on disk: the dated section appended to
#   needs_facesheet_list.md, the run report CSV, the captured_calls additions file, the board update file for the
#   Insurance Refresh Board inbox, and the chat-history digest. Chart ids and visit ids only - no patient names.
# Never touches: AdvancedMD, Drive (the connector uploads what this writes), any register.
import json, csv, datetime, os, collections
STAMP = "2026-10-14T0910Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
os.makedirs("chat_history", exist_ok=True); os.makedirs("outbox", exist_ok=True)
before = json.load(open("scan_%s/summary_before.json" % STAMP))
after = json.load(open("scan_%s/summary_after.json" % STAMP)) if os.path.exists("scan_%s/summary_after.json" % STAMP) else before
sweep = json.load(open("registers/uni20_bcbs_pre0501_sweep_%s.json" % STAMP)); rows = sweep.get("rows", sweep)
sw = collections.Counter(str(r.get("action") or "")[:30] for r in rows); sw_bal = sum(float(r.get("balance") or 0) for r in rows)
def counts(s):
    insp = sum(len(b.get("visits", b) if isinstance(b, dict) else b) for b in (s.get("inspector") or {}).values()) if isinstance(s.get("inspector"), dict) else len(s.get("inspector") or [])
    ex = s.get("exclusions") or {}
    exn = sum(len(v) for v in ex.values()) if isinstance(ex, dict) else len(ex)
    return len(s.get("chargereview") or []), insp, len(s.get("unbilled") or []), exn
cb, ca = counts(before), counts(after)
ov = after.get("overview", {})

needs = """
## 2026-10-14 09:10 UTC - backend billing run (5 AM ET 10/14, ehpa cloud) - run %s

Bootstrap: repo ATTACHED (origin/main e9baa9f at start, main checked out, symlinked to /home/claude/effinger-billing-backend); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential (no credential file); ONE login 09:16Z (columns_scan.py before); no lock; no START younger than 40 min (0710Z digest carries RUN COMPLETE); v12 precondition greps pass; pseudonyms.json (406 names, Drive 10/8) installed in both secrets folders; layout from the repo (949 helper files, OCR tools installed). State bundle restored: none (Drive newest 2026-09-18, older than main - same call as the 0710Z run). Missing required helpers: none. Routine text delivered v7; the v12 rules on main applied. GitHub inbox: the two PACKAGE_* manifests on Drive (2026-10-11, 2026-10-12_weekly-metrics) are the known connector-transcription sets, not in bundles_applied.json - left as the earlier runs left them.
Sources: denials queue 0, board drops 0, board rows updated since 07:00Z 0, Mandatory Approvals page 0 approved (register: 45 done, 0 waiting); Pam Gmail nothing in 2 days; Drive: no 835 / Availity / Check-EFT / facesheet / Claimocity file after 10/13 20:00Z (recent-files list holds only routine, chat and button files; GeminiSetup.exe and Patient_balances_review_2026-10-13.xlsx are the chat's).

Columns (list counts): Charge Review %d -> %d | Claim Inspector %d -> %d | Unbilled %d -> %d | Exclusions %d -> %d (overview after: %s / %s / %s $%s / %s $%s - lags) | ERA 1 check $71.00 -> 1 check $71.00.
- Claim Inspector 5 -> 5: every row a standing hold - chart 23177 v19451190 (Pattern 24078 CCI 99309 vs CCM + 15775 add-on), chart 44983 v13979435 + v13984519 (Pattern 4852 discharge 99239 + 3429 / 35777), chart 22845 v19364378 (Pattern 4852 + 20657 + 33799), chart 17472519 v19395738 (S06.5XAS only in the first slot, payment on the charge - board row). No edit, no bypass this slot.
- Unbilled 28 -> 28: 20 'Unresolved Claim Inspector errors' = the standing holds (chart 22845 TRI05 x11 incl. v19362172 - Olson/TRI05 carrier hold; chart 44983 GEH04 x2; chart 17469045 v19362925 BCBS, chart 12183413 v19364497, chart 23456 v19367114, chart 21021 v19372311 / v19372463 HUM01, chart 47127 v19372604 TRI05 - 2024 visits with charge-level inspector errors; chart 17472519 v19395738) + 8 'Insurance order is missing' chart 17478013 (HCA 10/5-10/12/2026, $1,430, zero plans; row on William's turn since the 10/14 chat pass - every lookup ERR 72 / discovery 0; HCA facesheet needed). unbilled_repair.py not run (no reason-code or prior-payor row on the list).
- Exclusions 1 -> 1: AET12 chart 24750 PREF0288 (carrier-master hold). Overview 6 / $1,769 lags the list.
ERA (step 5): (a) nothing to upload (no new 835 in 'bht Optum era downloads'). (b) before = 1 check / $71.00 unposted: 1053116 UHC W0020208 (details cached, 3 claim rows). (c) era_post --all-unposted --dry: 0 postable / 3 skipped (v19421789 paid 0 settled; v19395670 $71 reversal 'This insurance reversal does not match any payments applied from the carrier' x2) - takeback pair, no posting rule, HELD for William's decision (unchanged since 10/11). era_clear --dry: 1 held (denial with write-off 1, unvalidated money 1, unvalidated $0 1). (d)-(e) nothing to post or clear; no live pass. after = 1 / $71.00. Auto-posted $0; manual-posted 0; residuals $0; checks cleared 0. (g) Availity / Treasury: no new Remittance Viewer PDF or Check/EFT export - nothing to parse or reconcile.
UNI20/BCBS pre-5/1 pass 91 (--min-age 166 --max 60 --carriers UNI20,BCBS --skip-answered passes 1-89 on disk; the 0710Z pass-90 register is not on main, so this pass re-asked pass 90's 60 visits): 60 asked ($%s) - %s. 0 candidates, 0 sent: every one of the 28 NOT-ON-FILE rows (25 x D0 'cannot provide further status electronically' / 'date(s) of service', 3 x E0) was read live (gettxhistory) - all 28 carry billdate 10/13/2026 = the 10/13 patient-balance execution's BILL-SECONDARY sends (Medicare-paid lines whose coinsurance went to the BCBS / UNI20 secondary on 10/13: charts 45052 x12, 17469067 x8, 17472305 x2, 17471979, 47643, 17472636, 23391, 25416, 46354, 42092, 17468781), so the 30-day billdate rule excludes them until 11/12/2026; none in the timely-filing watch; the 2 DENIED 585 (charts 23967-pool HAGEN / NUZZO-type lines) and 7 FINALIZED $0 are earlier answers already registered. The 1 PAID $30.96 (UHC check 211169256, 835 not in AMD) stays awaiting-835. Register registers/uni20_bcbs_pre0501_sweep_%s.json. Timely-filing watch: no new CARC 29.
Approvals (step 0h, last): page 0 approved / 0 waiting; register 45 done. Nothing to apply, nothing submitted.
Writes in AdvancedMD: none this slot (reads only: login, overview + four list calls, era checks / checkdetails, posterapayments dry, massrebillsearch + Stedi 276/277 x60, gettxhistory x16 charts). Dollars re-sent: $0. Write-offs: none. Permission-classifier refusals: none.
Calls learned: 0 new shapes. Vocabulary entries added: 0. Helpers this run: report_1014_0910.py (paperwork only).
Waiting on William: the 1053116 UHC W0020208 takeback decision ($71); chart 17478013 HCA facesheet ($1,430, 8 visits); chart 24197 CHP member id ($711); the AET12 carrier master (chart 24750); the standing inspector holds (charts 23177 / 44983 / 22845 / 17472519); the two engines (Billing Button live at :17/:31 + this routine at :10) still overlap every odd hour.
""" % (STAMP, cb[0], ca[0], cb[1], ca[1], cb[2], ca[2], cb[3], ca[3], ov.get("chargereviewcount"), ov.get("claiminspectorcount"), ov.get("unbillablecount"), ov.get("unbillableamount"), ov.get("exclusioncount"), ov.get("exclusionamount"),
       ("%.2f" % sw_bal), ", ".join("%d %s" % (n, k) for k, n in sw.most_common()), STAMP)
open("needs_facesheet_list.md", "a").write(needs)
open("outbox/needs_facesheet_list_section_%s.md" % STAMP, "w").write(needs)

csvp = "_run report 10-14 0910.csv"
with open(csvp, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["column", "status", "chart", "visit", "dos", "carrier", "error", "action"])
    w.writerow(["Charge Review", "cleared", "", "", "", "", "", "0 before -> 0 after"])
    insp = after.get("inspector") or {}
    items = []
    if isinstance(insp, dict):
        for bid, b in insp.items():
            for v in (b.get("visits", b) if isinstance(b, dict) else b): items.append(v)
    else: items = insp
    for v in items:
        w.writerow(["Claim Inspector", "remaining", v.get("pid"), v.get("vid"), "", "", "; ".join(e[1][:70] for e in (v.get("errs") or v.get("errors") or [])), "standing hold"])
    for r in after.get("unbilled") or []:
        vid = r.get("vid") or r.get("visitid") or r.get("id"); pid = r.get("pid") or r.get("patientid"); carr = r.get("carrier") or r.get("carriercode") or ""
        errs = "; ".join((e if isinstance(e, str) else str(e.get("text") or e)) for e in (r.get("_errs") or r.get("errors") or r.get("reasons") or []))
        act = "facesheet needed (William)" if str(pid) == "17478013" else "standing hold (inspector / carrier)"
        w.writerow(["Unbilled", "remaining", pid, vid, r.get("dos", ""), carr, errs, act])
    w.writerow(["Exclusions", "remaining", "24750", "", "", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID", "carrier-master hold (William)"])
    w.writerow(["ERA", "remaining", "", "19395670", "2024-06-12", "UHC W0020208 (check 1053116)", "$71 reversal does not match any payment from the carrier", "takeback pair held for William's decision"])
    for r in rows:
        if str(r.get("action", "")).startswith(("PAID", "UNKNOWN")):
            w.writerow(["UNI20/BCBS pre-5/1 pass 91", "remaining", r.get("patientid"), r.get("visitid"), r.get("dos"), r.get("carrier"), r.get("action"), "awaiting 835 / re-ask next pass"])
    w.writerow(["UNI20/BCBS pre-5/1 pass 91", "remaining", "", "", "", "UNI20/BCBS", "28 NOT-ON-FILE rows all billed 10/13/2026 (BILL-SECONDARY sends)", "not candidates until 11/12/2026 (30-day billdate rule); 16 pending; 0 sent"])
print("wrote", csvp)

add = """# captured_calls additions - 2026-10-14 0910 UTC (5 AM ET 10/14) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt; AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before), posterapayments dry (era_post.py --all-unposted --dry: 1053116 0 postable / 3 skipped), era_clear.py --dry (1 held), POST /api/claim/massrebillsearch + Stedi 276/277 x60 (claim_status_sweep.py pass 91), gettxhistory (txh.fetch + payreasons.visit_state, 16 charts read-only).

Behaviors noted:
- The 28 NOT-ON-FILE (D0 / E0) rows of the UNI20/BCBS pre-5/1 pool all carry billdate 10/13/2026: they are the 10/13 patient-balance execution's BILL-SECONDARY sends (Medicare paid ~80%%, the coinsurance went to the Florida Blue / UHC secondary on 10/13). The payer has not indexed them yet; the 30-day billdate rule keeps them out of the candidate list until 11/12/2026. A D0 answer within 30 days of the billdate is 'not yet on file', not 'never received'.
- The pass-90 sweep register (0710Z) is not on main (that run's mirror commit carried only 5 files), so this pass re-asked the same 60 visits - 60 Stedi 277 calls that --skip-answered would have saved. Commit every run's sweep register (practices/ehpa/registers) so the next pass skips it.
- No AMD write, no classifier refusal this slot.
"""
open("captured_calls_additions_2026-10-14_0910UTC-5amET-ehpa-cloud.md", "w").write(add)

row17478013 = None
try:
    prev = json.load(open("inbox/board_updates_2026-10-14T0710Z.json"))
    for o in prev.get("ops", []):
        if str(o.get("id", "")).endswith("-17478013"): row17478013 = o["id"]
except Exception: pass
chk = "5 AM ET 10/14: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing new for billing after 10/13 20:00Z); Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail nothing in 2 days. ERA Center 1 check $71.00 before and after (1053116 UHC W0020208 takeback pair, held for your decision). Columns 0/5/28/1 -> 0/5/28/1 - every row a standing hold (5 inspector holds charts 23177 / 44983 / 22845 / 17472519; 20 Unbilled inspector holds; chart 17478013 facesheet x8; AET12 chart 24750); no AMD write this slot. UNI20/BCBS pre-5/1 pass 91: 60 asked, 16 pending, 28 not-on-file = the 10/13 BILL-SECONDARY sends (billdate 10/13, outside the 30-day rule until 11/12), 0 sent."
ops = [{"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {},
        "append": {"checks": [{"ok": "na", "result": chk, "src": "5am ET 10/14 columns run (ehpa cloud) - run %s" % STAMP, "when": "10/14"}]}}]
if row17478013:
    ops.append({"op": "upsert", "collection": "items", "id": row17478013, "set": {},
                "append": {"checks": [{"ok": "no", "result": "5 AM ET 10/14: still no facesheet in the HCA/TMH/PCC/Claimocity folders, no Pam email, no board drop; the eight visits (99223 10/5 + 99233 10/6-10/12/2026, $1,430) stay in Unbilled 'Insurance order is missing' - your turn (HCA facesheet).", "src": "5am ET 10/14 columns run (ehpa cloud) - run %s" % STAMP, "when": "10/14"}]}})
bu = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
json.dump(bu, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)

digest = "# %s run digest - backend billing run, 5 AM ET 10/14 (ehpa cloud)\n" % STAMP + needs.split("\n", 2)[2] + """
Mirror: GitHub - gated tree (phi_gate tree .) committed by mirror.py sync and pushed through the session proxy to main + claude/effinger-billing-backend-mirror-w74pqv + claude/pensive-einstein-ynd922 (see the final summary for the result per leg); Postman unchanged (no new vocabulary entry); Drive: board_updates_%s.json to 'board inbox', captured_calls_additions to 'billing agent project files', needs section + report_1014_0910.py to 'workspace mirror', this digest to 'chat history'; run report CSV delivered with SendUserFile. State bundle not uploaded (no patient_db; era_details 1 check; registers on main). Board inbox: nothing trashed (neither registry lists a current inbox file).

## SHARED LESSONS
- %s | backend billing run | WATCH | UNI20/BCBS pre-5/1 pass 91 (--min-age 166 --max 60, --skip-answered passes 1-89): 60 asked - 16 PENDING, 28 NOT-ON-FILE, 7 DENIED 585, 7 FINALIZED $0, 1 PAID $30.96 (UHC 211169256, 835 not in AMD), 1 UNKNOWN; 0 sent - all 28 NOT-ON-FILE rows carry billdate 10/13/2026 (the 10/13 BILL-SECONDARY sends: charts 45052 x12, 17469067 x8, 17472305 x2 + 7 singles, $25-49 coinsurance lines) - a D0 inside 30 days of the billdate is 'not yet on file'; candidates again after 11/12/2026 | registers/uni20_bcbs_pre0501_sweep_%s.json
- %s | backend billing run | TRAP | the 0710Z pass-90 sweep register never reached main (that run's mirror commit carried 5 files), so pass 91 re-asked the same 60 visits (60 Stedi 277 calls --skip-answered would have saved): copy registers/uni20_bcbs_pre0501_sweep_<stamp>.json into practices/ehpa/registers before every mirror commit | practices/ehpa/registers/
- %s | backend billing run | WATCH | columns 0/5/28/1 unchanged, ERA 1 check $71 (1053116) held, no AMD write this slot; the Billing Button's live columns run at :17/:31 overlapped a read-only slot | reports/button/latest.json

RUN COMPLETE
""" % (STAMP, NOW, STAMP, NOW, NOW)
open("chat_history/%s run digest.md" % STAMP, "w").write(digest)
print("wrote needs section, additions, board_updates (%d ops), digest" % len(ops))
