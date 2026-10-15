# PLAIN ENGLISH (paperwork only - 7 AM ET 10/14/2026 run, 2026-10-14T1110Z): writes the run's needs-list section, run report CSV, digest,
#   shared-lessons lines, captured-calls additions file and the board update file from this run's registers. No AMD call of any kind.
import json, csv, os, datetime, collections
S = "2026-10-14T1110Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
before = json.load(open("scan_%s/summary_before.json" % S)); after = json.load(open("scan_%s/summary_after.json" % S))
era = json.load(open("registers/era_new_%s.json" % S)); lines = era["lines"]
sweep = json.load(open("registers/uni20_bcbs_pre0501_sweep_%s.json" % S))
chkb = json.load(open("registers/era_checks_before_%s.json" % S)); chka = json.load(open("registers/era_checks_after_%s.json" % S))
cb = chkb.get("checks", chkb); ca = chka.get("checks", chka)
def tot(l): return sum(float(c.get("unpostedamount") or 0) for c in l)
posted = [r for r in lines if r["outcome"] == "posted"]; resid = [r for r in lines if r["outcome"].startswith("residual")]
pay = sum(r["pay"] for r in posted); wo = sum(r["wo"] for r in posted); rz = sum(float(r["outcome"].split()[1]) for r in resid)
nexcl = lambda s: sum(len(v) for v in s["exclusions"].values())
cols = "Charge Review %d -> %d | Claim Inspector %d -> %d | Unbilled %d -> %d | Exclusions %d -> %d" % (
    len(before["chargereview"]), len(after["chargereview"]), len(before.get("inspector_visits", before.get("inspector", []))) if isinstance(before.get("inspector_visits", before.get("inspector", [])), list) else 5, 5,
    len(before["unbilled"]), len(after["unbilled"]), nexcl(before), nexcl(after))
act = collections.Counter(r["action"].split(" - ")[0].split(" $")[0] for r in sweep)
pend = sorted({str(r["patientid"]) for r in sweep if r["action"].startswith("PENDING")}); den = sorted({str(r["patientid"]) for r in sweep if r["action"].startswith("DENIED")})
nof = sorted({str(r["patientid"]) for r in sweep if r["action"].startswith("NOT ON FILE")}); paidfb = [r for r in sweep if r["action"].startswith("PAID")]
eraline = ("ERA: 2 checks / $%.2f unposted -> %d check / $%.2f. NEW Medicare Part B 819970542 (1053153, $4,210.92, 43 claims / 61 charge lines on charts 21483 x29, 22322 x11, 22603 x2, "
           "17476681 x2, 17471174, 17471334; DOS 10/2025-9/2026 = the 10/13 patient-balance execution's re-sent claims): %d lines posted ERA-linked by era_new_1014_1110.py - pay $%.2f + WOINS $%.2f "
           "(CO-45 + CO-253 capped to the open balance, PR-2 coinsurance left for the secondary / patient), 0 faults; %d lines residual $%.2f (chart 22603 v19420337 55.97 + v19422862 47.57: 99308 10/16 + 11/6/2025, "
           "Medicare had denied them $0 on 9/10/2026 (check 349929519) and both were written off WOINS 107.00 the same day - live balance 0, nothing posted, disregarded per the 9/13 rule; "
           "voiding the two 9/10 WOINS write-offs and posting the $103.54 would recover it - William's call, report only). Check 1053153 dismissed by act_1014_1110_dismiss.py (200 issuccess), "
           "GET /api/era/checks confirms 1 left: 1053116 UHC W0020208 $71 (takeback pair, held for William's decision). Post button (posterapayments) not pressed; era_post --dry: 41 postable / 2 skipped; "
           "era_clear --dry held both before the posts. (a) nothing to upload - no new 835 in 'bht Optum era downloads'; (g) no Availity PDF / Check-EFT export - nothing to parse or reconcile.") % (
           tot(cb), len(ca), tot(ca), len(posted), pay, wo, len(resid), rz)
sweepline = ("UNI20/BCBS pre-5/1 pass 92 (--min-age 166 --max 60 --carriers UNI20,BCBS, --skip-answered passes 1-91 on disk, 86 registers): %d asked - %d PENDING (chart %s), %d DENIED 585 (UNI20 2025 DOS, charts %s - earlier answers, 835s not in AMD, no CARC in hand: no write-off, no resend), "
             "%d NOT ON FILE (BCBS, charts %s), %d PAID (Florida Blue 277, chart 12180329 v19436825/v19436828/v19436829/v19437116, $21.80 balances, FB checks 423696373 / 423795599 / 423802576 - 835 not in AMD: awaiting-835), 1 FINALIZED $0 (chart 17472305 v19393939), 1 UNKNOWN (chart 17475632 v19433791). "
             "All 23 NOT-ON-FILE / PAID / FINALIZED rows read live (gettxhistory): every one carries billdate 10/13/2026 = the 10/13 BILL-SECONDARY sends (Medicare paid, the coinsurance went to the Florida Blue secondary on 10/13) - a D0 inside 30 days of the billdate is 'not yet on file'; 0 candidates, 0 sent. Timely-filing watch: no new CARC 29.") % (
             len(sweep), act.get("PENDING at payer", 0), "/".join(pend), act.get("DENIED/REVISED", 0), "/".join(den), act.get("NOT ON FILE / rejected", 0), "/".join(nof), len(paidfb))
holds = ("Claim Inspector 5 -> 5: every row a standing hold - chart 23177 v19451190 (Pattern 24078 CCI 99309 vs CCM + 15775 add-on), chart 44983 v13979435 + v13984519 (Pattern 4852 discharge 99239 + 3429 / 35777), "
         "chart 22845 v19364378 (Pattern 4852 + 20657 + 33799), chart 17472519 v19395738 (S06.5XAS only in the first slot, payment on the charge - board row). Unbilled 28 -> 28: 20 'Unresolved Claim Inspector errors' (chart 22845 TRI05 x11 incl. v19362172 - Olson/TRI05 carrier hold; "
         "chart 44983 GEH04 x2; chart 17469045 v19362925 BCBS, chart 12183413 v19364497, chart 23456 v19367114, chart 21021 v19372311 / v19372463 HUM01, chart 47127 v19372604 TRI05 - 2024 visits with charge-level inspector errors; chart 17472519 v19395738) + 8 'Insurance order is missing' chart 17478013 "
         "(HCA 10/5-10/12/2026, $1,430, zero plans; row on William's turn - every lookup ERR 72 / discovery 0; HCA facesheet needed; no new facesheet, Pam email or drop this slot). Exclusions 1 -> 1: AET12 chart 24750 v19455937 PREF0288 + PREF0264 (carrier-master hold). Charge Review 0 -> 0. Overview after: 0 / 5 / 28 $5,369.61 / 6 $1,769.00 (lags the list).")
sec = """
## %s run - 7 AM ET 10/14/2026 backend billing run (ehpa cloud)
Bootstrap: repo ATTACHED (origin/main 8b4785e at start, main checked out, symlinked); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD_PSW environment credential; ONE login 11:16Z (columns_scan.py before); no lock; no START younger than 40 min (0910Z digest carries RUN COMPLETE); v12 precondition greps pass; pseudonyms.json (406 names, Drive 10/8) in both secrets folders; layout from the repo (966 files). State bundle restored: none (Drive newest 2026-09-18, older than main). Missing required helpers: none. Routine text delivered v7; the v12 rules on main applied.
Sources: denials queue 0, board drops 0, board rows updated since 08:30Z 0, Mandatory Approvals page 0 approved; Pam Gmail nothing in 2 days; Drive: no 835 / Availity / Check-EFT / facesheet / Claimocity file after 08:30Z.
Columns (list counts): %s
- %s
%s
%s
Approvals (step 0h, last): page 0 approved; nothing to apply, nothing submitted.
Writes in AdvancedMD: 59 ERA-linked addpayments (era_new_1014_1110.py --live) + 1 ERA dismiss (act_1014_1110_dismiss.py --live) = 60, via named helpers; 0 column writes. Dollars re-sent: $0. Write-offs: WOINS $%.2f contractual on the Medicare lines (no bad-debt / timely write-off). Permission-classifier refusals: none.
Calls learned: 0 new shapes. Vocabulary entries added: 0. Helpers this run: era_new_1014_1110.py (stamp copy of era_new_1013_2110.py), act_1014_1110_dismiss.py, report_1014_1110.py (paperwork).
Waiting on William: the 1053116 UHC W0020208 takeback decision ($71); the $103.54 Medicare residual on chart 22603 (void the 9/10 WOINS write-offs to post it, or leave it); chart 17478013 HCA facesheet ($1,430, 8 visits); the AET12 carrier master (chart 24750); the standing inspector holds (charts 23177 / 44983 / 22845 / 17472519).
""" % (S, cols, holds, eraline, sweepline, wo)
open("needs_facesheet_list.md", "a").write(sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
# run report CSV
with open("_run report 10-14 0710.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["column", "status", "chart", "visit", "dos", "carrier", "error / payer", "amount", "action"])
    for bid, rows in before.get("inspector", {}).items() if isinstance(before.get("inspector"), dict) else []:
        for v in rows: w.writerow(["Claim Inspector", "remaining", v.get("pid"), v.get("vid"), "", "", "; ".join(e[1][:60] for e in v.get("errs", [])), "", "standing hold"])
    for r in before["unbilled"]:
        w.writerow(["Unbilled", "remaining", r.get("pid"), r.get("vid"), r.get("dos", ""), r.get("carrier", ""), "; ".join(r.get("reasons", [])) if isinstance(r.get("reasons"), list) else r.get("reasons", ""), r.get("amount", ""), "standing hold (inspector errors / chart 17478013 facesheet)"])
    for run, rows in before["exclusions"].items():
        for v in rows: w.writerow(["Exclusions", "remaining", v.get("patientid"), v.get("id"), (v.get("_chgs") or [{}])[0].get("dos", ""), v.get("carriercodeshort"), "; ".join(e["name"] for e in v.get("_errs", [])), sum(float(c.get("totalfee") or 0) for c in v.get("_chgs", [])), "carrier-master hold"])
    for r in lines:
        w.writerow(["ERA", r["outcome"].split()[0], r["pid"], r["visitid"], r["dos"], "MEDICARE PART B 819970542 (1053153)", "+".join(r["carcs"]), r["paid"], "posted ERA-linked pay %.2f + WOINS %.2f" % (r["pay"], r["wo"]) if r["outcome"] == "posted" else r["outcome"] + " - charge at $0 since the 9/10/2026 $0 denial + WOINS; report only"])
    w.writerow(["ERA", "held", "", "", "", "UHC W0020208 (1053116)", "takeback pair", 71.00, "William's decision"])
    for r in sweep: w.writerow(["UNI20/BCBS pre-5/1 sweep 92", r["action"].split(" - ")[0], r["patientid"], r["visitid"], r["dos"], r["carrier"], r["action"], r["balance"], "billdate 10/13/2026 - not a candidate" if r["action"].startswith(("NOT ON FILE", "PAID", "FINALIZED")) else "wait / answered"])
# digest
dig = """# %s run digest - backend billing run, 7 AM ET 10/14 (ehpa cloud)
%s
Mirror: see the final summary (GitHub / Postman / Drive / state bundle). Board inbox: board_updates_%s.json (1 op: availity-remits-backlog check - the 4 Florida Blue 277 PAID answers awaiting-835). State bundle not uploaded (481 parts; registers on main; era_details 2 checks, patient_db empty).

## SHARED LESSONS
- %s | backend billing run | WATCH | ERA Center: NEW Medicare 819970542 (1053153, $4,210.92, 43 claims) = the 10/13 patient-balance execution's re-sent claims paying - 59 lines posted ERA-linked (pay $%.2f + WOINS $%.2f, 0 faults) by the era_new stamp copy, check dismissed; 2 residual lines $103.54 on chart 22603 charges Medicare denied $0 on 9/10 and that were written off WOINS the same day - report only; 1053116 held | registers/era_new_%s.json
- %s | backend billing run | WATCH | UNI20/BCBS pre-5/1 pass 92: 60 asked - 16 PENDING, 20 DENIED 585, 18 NOT-ON-FILE, 4 Florida Blue PAID (chart 12180329, checks 423696373 / 423795599 / 423802576, 835 not in AMD - awaiting-835), 1 FINALIZED $0, 1 UNKNOWN; all 23 NOT-ON-FILE / PAID / FINALIZED rows carry billdate 10/13/2026 (the 10/13 BILL-SECONDARY sends) - 0 candidates, 0 sent; --skip-answered with 86 registers still re-asked the 20 DENIED 585 rows (a DENIED 277 is not treated as final) | registers/uni20_bcbs_pre0501_sweep_%s.json
- %s | backend billing run | WATCH | columns 0/5/28/1 unchanged (standing holds); the Billing Button's live columns run at :17/:31 overlapped the hour this routine posted 59 ERA-linked lines (11:24-11:26Z) - the per-line 'already posted by check number' guard is the only protection | reports/button/latest.json

RUN COMPLETE
""" % (S, sec.strip(), S, NOW, pay, wo, S, NOW, S, NOW)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(dig)
open("captured_calls_additions_2026-10-14_1110UTC-7amET-ehpa-cloud.md", "w").write("""# captured_calls additions - 2026-10-14 1110 UTC (7 AM ET 10/14) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt; AMD_PSW environment credential), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after), posterapayments dry (era_post.py --all-unposted --dry), era_clear.py --dry, addpayments postingmethod=era with eraclaimid/erareportid + the remit reasonlist (payreasons.post_line x59 via era_new_1014_1110.py --live), POST /api/era/checks/dismiss (act_1014_1110_dismiss.py --live, 1053153), POST /api/claim/massrebillsearch + Stedi 276/277 x60 (claim_status_sweep.py pass 92), gettxhistory (txh.fetch_visit: 43 ERA visits before/after each post + 23 sweep visits, read-only).

Behaviors noted:
- Medicare 835 lines on charges that an earlier Medicare $0 denial + WOINS had already taken to $0 (chart 22603 x2, 9/10/2026) come through the remit with insurancebalance 0 - era_post skips them, era_clear holds the check as 'unrecorded payment (reversal pipeline)'; after every other line is settled the check is dismissed by a named helper (act_<mmdd>_<slot>_dismiss.py) that reads the posting register first.
- claim_status_sweep.py --skip-answered (86 registers) still re-asked 20 DENIED/REVISED (F2 585) UHC rows - the skip list treats only PAID / FINALIZED as final.
""")
# board update file
bu = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": [
    {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": "7am ET 10/14 columns run (ehpa cloud) - run %s" % S, "when": "10/14",
        "result": "No Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new after 08:30Z 10/14); ERA Center 2 checks $4,281.87 -> 1 check $71.00: NEW Medicare Part B 819970542 (1053153, 43 claims) posted ERA-linked $4,107.33 + WOINS $4,650.12 and dismissed (2 lines $103.54 on chart 22603 charges already written off after the 9/10 $0 denial - report only); 1053116 held. Florida Blue 277 PAID answers with no 835 in AMD and no payment on the charge: chart 12180329 v19436825 / v19436828 / v19436829 / v19437116 (3/26-4/1/2026 secondary coinsurance $21.80 each, FB checks 423696373 / 423795599 / 423802576, billed 10/13) - awaiting-835 per the 10/6 rule; if still missing after 10/27 one row asks you to pull those 835s from the Availity portal into 'bht Optum era downloads'."}]}}]}
json.dump(bu, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote needs section, CSV, digest, additions, board_updates; posted %d pay %.2f wo %.2f resid %.2f; sweep %s" % (len(posted), pay, wo, rz, dict(act)))
