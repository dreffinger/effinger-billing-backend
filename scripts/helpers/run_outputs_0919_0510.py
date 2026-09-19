# PLAIN ENGLISH (run outputs for the 1am ET 9/19/2026 slot - ehpa cloud run 2026-09-19T0510Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before|after.json), the ERA before/after snapshots and the
#   registers written tonight (unbilled_fix, lazenby_plan, charts_read, visit_detail, aet12_verify), then writes:
#   "_run report 9-19 0510.csv"; board_updates_2026-09-19T0510Z.json (Insurance Refresh Board inbox file: the three charts
#   William answered on the board / by facesheet upload, the referral-plan cross-write found on pat17477777 (William's turn),
#   the MSP-code fixes, one new row for the new HCA chart pat17477798, William's registry question answered, the standing rows'
#   appends, the pseudonymized duplicate rows closed); a needs_facesheet_list.md section; the captured_calls additions file;
#   the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Names/member ids on the board only. Row ids come from inbox/rowids_0510.json
#   (real ids live outside the mirrored script - PHI gate). Auth numbers are read from the facesheet OCR text, never typed here.
import csv, json, os, datetime, sys, re
S = "2026-09-19T0510Z"; SRC = "1am ET 9/19 columns run (ehpa cloud)"; W = "9/19"; SLOT = "1 AM ET 9/19"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
IDS = json.load(open("inbox/rowids_0510.json"))
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
def auth_from(txt):
    m = re.search(r'Auth\w*\s*#?\s*\n?\s*([A-Z0-9]{8,})/', txt); return m.group(1) if m else "?"
AUTH_C = auth_from(open("inbox/facesheets/conway_shelby.txt").read()) if os.path.exists("inbox/facesheets/conway_shelby.txt") else "?"
AUTH_G = auth_from(open("inbox/facesheets/gorman_sr.txt").read()) if os.path.exists("inbox/facesheets/gorman_sr.txt") else "?"
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ver = load("registers/aet12_verify_%s.json" % S, []); aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
fix = load("registers/unbilled_fix_%s.json" % S, {}); laz = load("registers/lazenby_plan_%s.json" % S, {})
ovb = before.get("overview", {}); ova = after.get("overview", {}); ub = before.get("unbilled", []); ua = after.get("unbilled", [])
runs_n = ovb.get("claimrunstatuscount", "?")
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. ERA Center empty the whole run: locks release-expired sent; era_post --all-unposted 0 checks; "
           "fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments' "
           "(nothing modified there after 03:00Z 9/19); no MA63/M76/M64 work." % (nb, ab, na, aa))
CONWAY_TXT = ("Your VA facesheet (connell, shelley.pdf, HCA Commure print 9/18 23:30, OCR): OPTUM VA CCN, policy = the ICN, effective 09/01/26, Auth %s (12 bytes, the value before the slash), "
               "arrival 9/14, discharge 9/18. Your 04:45Z chat session had already added the VACCN plan (ins9519485, ICN as member id, no group) and written the auth on the chart's main referral plan rplan18462069, "
               "with the 9/14 + 9/15 visits resaved (insorder 1, admit 09/14/2026, onhcfa 1) - AMD 271 on the plan: ACTIVE (verified this run). FIX this run: the 9/16 (v19454951) and 9/17 (v19455049) visits had been pointed at "
               "rplan18462071, which is another patient's main referral plan (pat17477777) - repointed both to rplan18462069 with the auth, admit 09/14/2026, onhcfa 1 (readback ok, 1/1 charges live). "
               "All 4 visits ($643) are off the Unbilled column and queue to VA CCN on the next claim run." % AUTH_C)
THURLOW_TXT = ("Your TMH paste 04:32Z (CHP ADVANTAGE PLUS, member CIO01040626, eff 1/1/2024, subscriber self; Epic group 00000 not entered): CAP07 Capital Health Plan (car41826) is on the chart as seq 1 "
              "(ins9519484, begin 01/01/2024, no group) - added by your 04:45Z chat session; AMD 271 on it this run: ACTIVE (HN = HMO Medicare Risk). All 4 HCA visits (99223 9/14, 99232 9/15, 9/16, 9/17 = $643) "
              "carry insorder 1, admission 09/14/2026, onhcfa 1 on the chart's own referral plan and are off the Unbilled column - they bill CAP07 on the next claim run. Nothing left for you.")
GORMAN_TXT = ("Your facesheet (gordon sr.pdf, HCA Commure print 9/19 00:31, OCR): Primary WELLCARE MCR (Medicare Advantage, policy 37708503, eff 09/01/26, group GA131 NOT entered, Auth %s = the value before the slash), "
              "Secondary MEDICAID GEORGIA (policy 222119786913, eff 09/01/26); arrival 9/14, discharge 9/15; financial class Managed Care Medicare. Your 04:45Z chat session had added both plans (WEL04 car6174 seq 1 ins9519486, "
              "GEO05 Georgia Medicaid car6128 seq 2 ins9519487, begin 09/01/2026, no groups) with the visits resaved insorder 1. THIS RUN: AMD 271 - WellCare ACTIVE (South Georgia Physicians Association affiliation), "
              "Georgia Medicaid AAA 42 (payer could not respond - not a coverage answer); both visits (99223 9/14 v19454907, 99232 9/15 v19454927 = $421) resaved insorder 1,2 so Georgia Medicaid queues as the secondary "
              "after WellCare pays, and the HCA auth %s written on his own referral plan rplan18462073 (readback ok). Off the Unbilled column; they leave on the next claim run. Nothing for you." % (AUTH_G, AUTH_G))
LAZ_TXT = ("WILLIAM: please clear the Pre-Auth # on this chart's MAIN referral plan rplan18462071 (chart 17477777, Referral Plans) - it now reads %s, which is pat17477775's VA CCN authorization. "
           "Cause: the 04:45Z chat-session resave that attached Conway's 9/16 + 9/17 visits pointed them at this plan (rplan18462071 instead of his rplan18462069) and the preauth write landed here. "
           "This run repointed Conway's visits to his own plan, but the API cannot blank a referral plan's auth: a full-visit resave with preauth=\"\" is ignored, and addreferralplan (both status spellings) get-or-returns the main plan "
           "instead of creating a blank one. Her two Florida Blue HCA claims (99223 9/14 v19454905, 99232 9/15 v19454919, $421, not yet transmitted - no claim run since 9/16) would print that VA number as the prior-auth "
           "on the next claim run. One UI edit clears it; nothing else on this chart changed (plan BCBS seq 1, visits insorder 1, admit 09/14/2026, onhcfa 1 - re-verified)." % AUTH_C)
LISLE_TXT = ("Unbilled column 1am ET 9/19: the 9/17 99232 (v19455048, $111) landed with 'When billing Medicare as the non-primary carrier, the MSP Code on the Insurance Tab is required' - the Medicare seq-2 plan had no MSP code. "
             "Set mspcode 43 (disabled beneficiary, large group health plan primary = the CMS coordination record type the 9/18 cascade read) on ins9519462 via updateinsurance (success 1, readback 43); visit released "
             "(insorder 1,2, admit 09/14/2026, onhcfa 1 already on it). The 9/14-9/16 UMR visits show billdate 09/18/2026.")
PELLAM_TXT = ("Preventive: same MSP rule as pat17477774 - the Medicare seq-2 plan (ins9519460) behind the Cigna group plan now carries MSP code 12 (working aged, the CMS record type from the 9/18 cascade) so the "
               "Unbilled column will not hold his visits for it (updateinsurance success 1, readback 12).")
HARRIS_NEED = ("WILLIAM: admission facesheet or card for %s (DOB %s, HCA Florida Capital Hospital, admitted 9/16/2026). Age 73 but CMS has no Medicare record (Stedi MBI lookup with the chart SSN and without it: ERR 72); "
               "Stedi discovery (FL, DOS 9/16/2026): coveragesFound 0; no facesheet in the HCA/TMH/PCC/Claimocity folders, no Pam email, no board drop; no other chart of that name in AMD. Address line 1 filled "
               "(5294 WATER VALLEY DR; %s). 2 visits (99223 9/16 v19455057, 99232 9/17 v19455030 = $421) wait in Unbilled 'Insurance order is missing'." % (IDS["harris_patient"], IDS["harris_dob"], IDS["harris_phone_note"]))
REGISTRY_TXT = ("No - being on the board does not fix it. At 04:46-04:48Z (while you were on it) the page re-applied the inbox files again: the rows' versions bumped and the registry's applied map is still only the 9/12-9/14 "
                "files (meta/drive_sync version 1384, lastCheck 04:48:56Z). Until the page's registry write is repaired (a chat session with write_db re-registering the 9/15-9/19 board_updates / denials_updates file ids "
                "as applied, as was done 9/14), or the 9/15-9/18 files are moved out of 'board inbox' into 'ingested before 9-14' by hand, every open re-applies them and the pseudonymized duplicate rows come back. "
                "The runs keep closing the duplicates in their update files (done again this run).")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart (feed 9/16): no plan; Stedi MBI ERR 72 with and without SSN, discovery 0, no facesheet/email/drop; address line 1 filled; row on William's turn"
    elif err.startswith("When billing Medicare"): act = "MSP code set on the Medicare plan and released this run (row was on the before-snapshot only)"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "cleared", "pat17477775", "09/16-09/17/2026", "VACCN", "visits pointed at another patient's referral plan", "repointed v19454951 + v19455049 to rplan18462069 with the facesheet auth, admit 09/14/2026, onhcfa 1", visit="19454951,19455049", amount="222.00")
add("Unbilled", "cleared", "pat17477779", "09/14-09/15/2026", "WEL04,GEO05", "secondary not in the visit order; HCA auth not on the plan", "insorder 1,2 + auth on rplan18462073 (readback ok); AMD 271 WellCare ACTIVE, GA Medicaid AAA 42", visit="19454907,19454927", amount="421.00")
add("Unbilled", "cleared", "pat17477776", "09/14-09/17/2026", "CAP07", "verify only", "CAP07 CIO... seq 1 on the chart (chat session), AMD 271 ACTIVE, 4 visits insorder 1 / admit 9/14 / onhcfa 1 - off the column", visit="19454904,19454910,19454936,19455052", amount="643.00")
add("Unbilled", "cleared", "pat17477774", "09/17/2026", "UMR/FLO02", "MSP Code on the Insurance Tab is required", "mspcode 43 on the Medicare seq-2 plan (updateinsurance, readback 43); hideunbillevisits ok", visit="19455048", amount="111.00")
add("Unbilled", "acted", "pat17477773", "", "CIG09/FLO02", "preventive", "mspcode 12 (working aged) on the Medicare seq-2 plan (readback 12)", visit="", amount="")
add("Unbilled", "count", action="%s -> %s ($%s -> $%s); 1 released (MSP fix), 2 charts' visits corrected, 1 new chart on William's turn" % (ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or so far 9/19 - tenth consecutive worked slot); %d AET12 charges on 15 charts re-read: $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, len(ver), aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
add("Sources", "acted", "pat17477775", "09/14/2026", "VACCN", "William: 'i uploaded a va facesheet' (04:27Z)", CONWAY_TXT, visit="pat17477775")
add("Sources", "acted", "pat17477779", "09/14/2026", "WEL04+GEO05", "William: 'georgi medicaid facesheet uploaded' (04:30Z)", GORMAN_TXT, visit="pat17477779")
add("Sources", "acted", "pat17477776", "09/14/2026", "CAP07", "William: TMH paste on the board (04:32Z)", THURLOW_TXT, visit="pat17477776")
add("Sources", "william", "pat17477777", "09/14/2026", "BCBS", "referral plan carries another patient's VA auth", LAZ_TXT, visit="pat17477777")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: rows on Claude's turn read, drops 0 new; William notes since the 0310Z run: 4 (Conway, Gorman, Thurlow, board-inbox registry) - all acted on; board inbox: the registry's applied map lists only 9/12-9/14 files - nothing trashed")
add("Routine", "note", action="Cross-container guard: a chat-session START marker (2026-09-19T0445Z run START.md, 04:42Z) with no RUN COMPLETE digest was 27-40 min old; waited per the 0f rule and proceeded at 05:22Z. That session had attached the three charts' plans by then; this run verified and corrected its work (referral-plan cross-write). State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main; registers restored from practices/ehpa/registers (113 files) + needs_facesheet_list rebuilt from 33 nightly/runs sections. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run; hold Florida Blue patient statements")
with open("_run report 9-19 0510.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app(IDS["connell"], "ok", CONWAY_TXT, "Your VA facesheet read; the plan and auth your chat session attached are right, and the two later visits that had been pointed at another chart's referral plan are now on his own. All four visits queue to VA CCN on the next claim run - nothing for you.",
    {"status": "claude", "need": "None - billed to Optum VA CCN (ICN as member id, auth %s on referral plan rplan18462069, admission 09/14/2026) - 4 visits 9/14-9/17 ($643) off the Unbilled column, queued for the next claim run." % AUTH_C, "inscarrier": "VACCN Optum Va Ccn", "amount": 643})
app(IDS["thomas"], "ok", THURLOW_TXT, "CHP Advantage Plus member id read from your paste - the plan is on the chart, CHP says ACTIVE, and all four visits are queued. Nothing for you.",
    {"status": "claude", "need": "None - billed to CAP07 Capital Health Plan (CHP Advantage Plus, seq 1, begin 01/01/2024, no group; AMD 271 ACTIVE); 4 visits 9/14-9/17 ($643) off the Unbilled column, queued for the next claim run.", "inscarrier": "CAP07 Capital Health Plan (Medicare Advantage)", "amount": 643})
app(IDS["gordon"], "ok", GORMAN_TXT, "Facesheet read: WellCare Medicare Advantage first with the HCA auth, Georgia Medicaid second. Both visits queued - nothing for you.",
    {"status": "claude", "need": "None - billed WellCare MA (WEL04 seq 1, auth %s on the referral plan) first, Georgia Medicaid (GEO05 seq 2) second; visits insorder 1,2, admission 09/14/2026; off the Unbilled column, queued for the next claim run." % AUTH_G, "inscarrier": "WEL04 WellCare (Medicare Advantage) + GEO05 Georgia Medicaid", "amount": 421})
app(IDS["lazarchik"], "human", LAZ_TXT, "One UI edit for you: clear the Pre-Auth # on her main referral plan (it holds pat17477775's VA number from the chat resave). Her claims are otherwise right.",
    {"status": "william", "need": LAZ_TXT})
app(IDS["lewis"], "ok", LISLE_TXT, None, {"status": "claude"})
app(IDS["johnson"], "ok", PELLAM_TXT, None, {"status": "claude"})
ops.append({"op": "upsert", "collection": "items", "id": IDS["harris"], "set": {"patient": IDS["harris_patient"], "dob": IDS["harris_dob"], "facility": "HCA FLORIDA CAPITAL HOSPITAL", "amdid": "17477798", "mbi": "", "need": HARRIS_NEED, "amount": 421, "status": "william",
    "why": "Unbilled column 9/19: new chart from the Claimocity feed with no insurance plan ('Insurance order is missing on visit')", "created": NOW},
    "append": {"checks": [{"ok": "human", "src": SRC + " - insurance cascade", "result": "Cascade exhausted: no plan on the chart; Stedi MBI lookup with the chart SSN and without it: ERR 72; Stedi discovery (FL, DOS 9/16/2026): coveragesFound 0; lookuppatient: no other chart of that name; no facesheet in the HCA/TMH/PCC/Claimocity folders, no Pam email, no board drop. Address line 1 filled (street moved up from line 2). Visits 19455057 (99223 9/16), 19455030 (99232 9/17) = $421 stay in Unbilled.", "when": W}],
               "notes": [{"who": "Claude", "text": "Created by the %s run. Every automated source is exhausted - your turn for the facesheet / card (HCA Omnissa).", "at": NOW}]}})
ops[-1]["append"]["notes"][0]["text"] = ops[-1]["append"]["notes"][0]["text"] % SLOT
app(IDS["registry"], "no", "Registry still not recording: meta/drive_sync applied map unchanged (9/12-9/14 files only), version 1384, lastCheck 04:48:56Z, while the rows were re-applied at 04:46-04:48Z during your visit.", REGISTRY_TXT, {"status": "william"})
for d in IDS["dups"]:
    ops.append({"op": "upsert", "collection": "items", "id": d, "set": {"status": "done", "need": ""}, "append": {"notes": [{"who": "Claude", "text": "Duplicate row (pseudonymized id re-created by the inbox re-apply) closed by the %s run; see the row under the real name." % SLOT, "at": NOW}]}})
app(IDS["aet12"], "no", "%s: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted 9/17, 9/18 or so far 9/19, tenth consecutive worked slot). %d AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (SLOT, runs_n, len(ver), aet_bal))
app(IDS["bcbs"], "na", "%s: not worked this run (same blocker as 0710Z 9/18 - 0310Z 9/19: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements." % SLOT)
app(IDS["availity"], "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 03:00Z 9/19) - nothing to parse, post or reconcile; board drops, Working Denials queue: nothing new; Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit already acted on; Claimocity drop: no new file. Two new HCA facesheets in 'bht hca facesheets' (Conway 03:29Z, Gorman 04:30Z) read by OCR and acted on - see their rows.")
app(IDS["era"], "na", "ERA step 5 (%s columns run (ehpa cloud), run %s): %s" % (SLOT.lower().replace(" et", " ET"), S, ERA_TXT))
app(IDS["west"], "human", "%s: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance." % SLOT)
app(IDS["unbal"], "no", "%s: the 11 'Payment reason codes are missing or do not balance' rows ($2,422.58; 2024 SUN01/BCBS/HUM01/TRI05 visits whose 9/13 manual ERA posts carry no CARC) are on the Unbilled snapshot again - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release." % SLOT)
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
open("needs_facesheet_list_section_%s.md" % S, "w").write("""
## %s columns run (ehpa cloud Code Routine, 05:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main aceb429), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Cross-container guard: chat-session START 0445Z (04:42Z) with no digest - waited, proceeded 05:22Z. Registers from practices/ehpa/registers; missing helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten).
Boards: Working Denials queue 0; Insurance Refresh Board drops 0; William notes since 03:22Z: connell 'i uploaded a va facesheet', gordon 'georgi medicaid facesheet uploaded', thomas TMH paste (CHP Advantage Plus CIO01040626), board-inbox 'im here does that solve it' - all answered through board_updates_%s.json.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s: %s | Exclusions 0 -> 0 (no claim run newer than 1700202, tenth consecutive slot; %d AET12 charges $%.2f open, held).
Facesheets (bht hca facesheets, OCR): pat17477775 VA CCN auth %s (chat session attached plan+auth; this run repointed the 9/16+9/17 visits from pat17477777's referral plan rplan18462071 back to rplan18462069) | pat17477779 WellCare MA %s + Georgia Medicaid (insorder 1,2 + auth on rplan18462073) | pat17477776 CAP07 CIO... verified ACTIVE, 4 visits queued.
NEEDS WILLIAM: pat17477777 main referral plan rplan18462071 still carries pat17477775's VA auth (cross-write by the chat resave; API cannot blank it - preauth="" ignored, addreferralplan get-or-returns main) -> clear in the UI before the next claim run. pat17477798 (new HCA chart 9/16, $421): no plan, MBI ERR 72 x2, discovery 0 -> facesheet needed (row on his turn).
MSP fixes: pat17477774 Medicare seq-2 mspcode 43 (Unbilled 'MSP Code on the Insurance Tab is required' on v19455048 -> released); pat17477773 mspcode 12 preventive.
ERA step 5: %s
Calls learned: no new call shapes. Behaviours: updateinsurance mspcode=NN via ins_update works (readback); a full-visit resave with preauth="" does NOT blank a referral plan's auth; addreferralplan with status="stat1" or "status1" get-or-returned the existing main plan (no blank plan created this run); a resave whose refplan= names another patient's plan writes the preauth onto THAT patient's plan (cross-patient) - always read refplan ownership (getdemographic refplanlist) before a preauth resave.
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, S, ovb.get("unbillablecount"), ova.get("unbillablecount"), "; ".join(sorted(set((r.get("_errs") or [""])[0][:60] for r in ua))), len(ver), aet_bal, AUTH_C, AUTH_G, ERA_TXT))
open("captured_calls_additions_2026-09-19_0510UTC-1amET-ehpa-cloud.md", "w").write("""# captured_calls additions - 2026-09-19 0510 UTC (1am ET 9/19 backend billing run, ehpa cloud)

No new AMD call shapes. Behaviours proven this run (chart ids only):
- `updateinsurance` (wrapped shape via ins_update.update) with `mspcode="43"` / `mspcode="12"` on a Medicare seq-2 insplan -> success=1, getdemographic readback shows the code. This clears the Unbilled column error "When billing Medicare as the non-primary carrier, the MSP Code on the Insurance Tab is required." (pat17477774 v19455048, released with hideunbillablevisits afterwards). MSP codes: 12 working aged (employer group primary), 43 disabled with a large group health plan primary - take them from the CMS coordination-of-benefits record type the Stedi MBI lookup returns.
- A full-visit `updvisitwithnewcharges` resave with `preauth=""` does NOT blank the referral plan's preauth (pat17477777 rplan18462071 kept the value; readback unchanged). Only a non-empty preauth writes.
- `addreferralplan` class=chargeentry with the 9/8 registry shape (id="" patient=patN ismain="0" status="stat1" sequence="2" ...) and with status="status1" both get-or-RETURNED the chart's existing main plan (echoing its preauth) instead of creating a blank plan - the 9/8 create shape did not create a second plan this run. Whatever made it insert on 9/8 is not in the registry; do not rely on it.
- A resave whose `refplan=` names ANOTHER patient's referral plan repoints the visit there and writes the preauth onto that patient's plan (seen 04:45Z 9/19: pat17477775's 9/16-9/17 visits on pat17477777's main plan rplan18462071, her plan now carrying his VA auth). Rule: read the chart's refplanlist (getdemographic) and confirm ownership before any refplan/preauth resave; visit_charges' refplan readback shows the pointer.
- getclaimrunstatus at 05:2xZ 9/19 still lists 1700202 (2026-09-16 22:16) as the newest claim run (78 runs): tenth consecutive worked slot with no nightly claim run.
- ERA Center empty (0 checks) at 05:22Z 9/19 - era_post / fallback / era_clear all no-ops.
""")
if "--final" in sys.argv:
    dig = """# 2026-09-19_0510UTC run digest - backend billing run, 1 AM ET 9/19 slot (ehpa cloud)

## %s columns run (ehpa cloud Code Routine, 05:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main aceb429, session branch claude/pensive-einstein-th71h4, layout 376 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC (26 parts) is older than GitHub main - registers restored from practices/ehpa/registers/ (113 files), needs_facesheet sections rebuilt from nightly/runs/ (33 sections); captured_calls.md = GitHub main docs/captured_calls.md; pseudonyms.json 208 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: a chat-session START marker '2026-09-19T0445Z run START.md' (04:42Z, 'William-requested full run', no RUN COMPLETE digest) was 27 min old at 05:09Z - waited, re-checked at 05:22Z (40 min, unchanged) and proceeded per the 0f rule; that session had already attached the three charts' plans by then.
Boards: Working Denials queue 0. Insurance Refresh Board: rows on Claude's turn read, drops 0 new; four William inputs since the 0310Z run acted on - VA facesheet for pat17477775, Georgia Medicaid facesheet for pat17477779 (both 'bht hca facesheets', image PDFs, OCR'd with ocr_pdf.py), TMH paste for pat17477776 (CHP Advantage Plus), and 'im here does that solve it' on the board-inbox registry row (answer: no - the registry's applied map is unchanged at version 1384 while the page re-applied the inbox at 04:46-04:48Z). Facesheet folders / Claimocity drop / Optum ERA / treasury: nothing else new. Pam Gmail: nothing newer than the 9/19 02:53Z Center Pointe admit.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled %s -> %s ($%s -> $%s): 11 'Payment reason codes' rows back on the snapshot and held, pat17471007 MV line William's, pat17477798 (new HCA chart, cascade exhausted) on William's turn, pat17477774 'MSP Code required' fixed (mspcode 43 on the Medicare seq-2 plan) and released; pat17477775 / pat17477776 / pat17477779 were already off the column (chat session) - verified: AMD 271 ACTIVE on VACCN, CAP07, WEL04 (GEO05 AAA 42); CORRECTED pat17477775's 9/16+9/17 visits (they pointed at pat17477777's main referral plan rplan18462071, which now carries his VA auth) -> repointed to rplan18462069 with the auth; pat17477779 visits insorder 1,2 + HCA auth on his plan; pat17477773 mspcode 12 preventive | Exclusions 0 -> 0 (no claim run newer than 1700202, 78 runs, tenth consecutive worked slot with no nightly claim run; %d AET12 charges $%.2f open, held, not re-sent). Nothing rebilled or written off.
NEEDS WILLIAM: (1) clear the Pre-Auth # on pat17477777's main referral plan rplan18462071 in the UI (it holds pat17477775's VA CCN auth from the chat resave; the API cannot blank it: preauth="" is ignored, addreferralplan get-or-returns the main plan with either status spelling) before the next claim run; (2) HCA facesheet / card for pat17477798 (DOB 1952, admitted 9/16, $421; MBI ERR 72 with and without SSN, discovery 0).
ERA step 5: %s Availity 5(g): nothing new.
Calls learned: no new AMD call shapes; behaviours recorded in the additions file (updateinsurance mspcode works; preauth="" does not blank a plan; addreferralplan get-or-returns main; cross-patient refplan writes). Vocabulary entries added: 0.
Mirror: %s

RUN COMPLETE
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, ovb.get("unbillablecount"), ova.get("unbillablecount"), ovb.get("unbillableamount"), ova.get("unbillableamount"), len(ver), aet_bal, ERA_TXT, MIRROR)
    os.makedirs("chat_history", exist_ok=True); open("chat_history/2026-09-19_0510UTC run digest.md", "w").write(dig)
    with open("needs_facesheet_list.md", "a") as fh: fh.write(open("needs_facesheet_list_section_%s.md" % S).read())
print("wrote report csv, board file (%d ops), needs_facesheet section, additions%s" % (len(ops), ", digest" if "--final" in sys.argv else ""))
