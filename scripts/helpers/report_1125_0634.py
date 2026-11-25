#!/usr/bin/env python3
# PLAIN ENGLISH (the button-run/1 report file of the ehpa Billing Button run 2026-11-25T0634Z - BUTTON PRESS 05:56:23Z, William's
#   12:35 AM ET order: work the refresh board + the info given in chat, fix the charts, rebill, report, new refresh list + email, update the board)
# Decides: nothing. Writes <repo>/reports/button/2026-11-25T0634Z.json + latest.json (schema button-run/1) from this run's registers -
#   one line per card worked (chart, what changed, what was re-sent / written off / voided with dollars, or exactly what is still needed)
#   and the G0439 look-up the brief asked for. Chart / visit / charge ids and dollars only, never a name.
# Usage: python3 report_1125_0634.py <ended iso>
import json, sys, datetime
S = "2026-11-25T0634Z"; REPO = "/home/claude/effinger-billing-backend"
ENDED = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
oc = json.load(open("outstanding_claims.json")); wd = json.load(open("working_denials_latest.json"))
o365 = oc.get("over_365"); o365 = o365 if isinstance(o365, dict) else {"n": len(o365), "dollars": round(sum(float(r.get("insbalance") or r.get("amount") or 0) for r in o365), 2)}
outstanding = {"total": oc.get("total"), "visits": oc.get("visits"), "charts": oc.get("charts"), "over_365": o365, "asof": "2026-11-25T0557Z run (not re-run: the press named steps columns + cascade)"}
RESENT = [("17472826", ["19438893", "19438892"], 421.00, "William: bill BCBS - WOINS wo22475808 $310 + wo22475797 $111 voided, order BCBS seq 1, sent once each"),
          ("17471238", ["19446256", "19448464"], 410.00, "Medicare Beneficiary ID from the sheet written (the chart carried the older HIC number, 72); 271 ACTIVE; sent as originals"),
          ("20709", ["19446255", "19448275", "19448463", "19448951", "19451781", "19452343", "19455840", "19455920"], 1778.00, "Medicare Beneficiary ID written (older HIC number rejected 72); 271 ACTIVE; sent as originals"),
          ("17478414", ["19462412", "19462163"], 530.00, "CAP07 plan ins9521409 added from Pam's admission record (seq 2, no group), 271 ACTIVE, order 2,1; both visits to CHP as originals (v19462412 created by the feed reprocess this run)"),
          ("12182505", ["19431381", "19433872", "19437363", "19442366", "19448364", "19449793"], 1210.00, "Railroad Medicare number rewritten on ins9519511 (the chart held the old number), order 3,2 (AARP second); re-pointed and sent"),
          ("17477572", ["19453098", "19453097", "19453099"], 532.00, "William: I10 first - diagnosis order saved on charges 23363598/23363597/23363599, sent to CHP; Z01.818 (first-listed-only, Pattern 2776) removed, inspector clean")]
WO = [("17475908", "19436456", 310.00, "WOINS - TRICARE East reports the claim already paid (duplicate), remit not obtainable; William 'write off' (BOARD1125C)"),
      ("17475908", "19436537", 111.00, "WOINS - same (BOARD1125C)"),
      ("17477353", "19459605", 109.00, "WOINS - Humana CO-4 on the CCM add-on; William 'write off' (BOARD1125C)"),
      ("17471273", "19448259", 310.00, "WOINS - Aetna finalized at $0; William 'write off' (BOARD1125C)")] + \
     [("17471273", v, 111.00, "WOINS - Aetna finalized at $0 (BOARD1125C)") for v in ("19448592", "19448627", "19448967", "19448986", "19449065", "19449321")]
VOIDED = [{"chart": "17469397", "visit": "19455708", "charges": ["23367095", "23367096"], "dollars": 315.00, "why": "after the date of death - WOINS wo22509480/81 + $0 payments voided, charges voided (read back void=1)"},
          {"chart": "17475365", "visit": "19455689", "charges": ["23367066"], "dollars": 206.00, "why": "after the date of death - WOINS wo22509484 + $0 payment voided, charge voided (void=1)"},
          {"chart": "17477267", "visit": "19455599", "charges": ["23366938"], "dollars": 206.00, "why": "after the date of death, on William's word - WOINS wo22509482 + $0 posting voided, charge voided (void=1); the August visits ($809.20 Medigap coinsurance at Florida Blue) untouched"}]
CARDS = [
 {"chart": "17471643", "result": "handed back", "action": "sheet's Medicare number = the chart's (and the twin chart 17471791's); AMD 271 AAA 72 under both spellings; nothing written - new Medicare card needed; the two charts are one patient, merge is William's call; FCC Medicaid plan set once Medicare is right", "dollars": 218.00},
 {"chart": "17471791", "result": "handed back", "action": "twin of 17471643 - same number, same answer (one card for both)", "dollars": 71.59},
 {"chart": "17472826", "result": "done", "action": "WOINS $310 + $111 voided, order BCBS seq 1, v19438893 + v19438892 sent once (204); balances back on insurance", "dollars": 421.00},
 {"chart": "17471238", "result": "done", "action": "Medicare Beneficiary ID written (chart held the older HIC number), 271 ACTIVE A/B 1999-11-01, v19446256 + v19448464 sent", "dollars": 410.00},
 {"chart": "20709", "result": "done", "action": "Medicare Beneficiary ID written (older HIC number rejected), 271 ACTIVE 2017-03-01, 8 visits sent; Medicaid seq 2 + Humana seq 3 already on the chart", "dollars": 1778.00},
 {"chart": "17478414", "result": "done", "action": "claimocity_ingest --reprocess created v19462412 (11/09/2026 99306+99497, charges 23375502 $256 + 23375503 $133); 1123F $0.01 held by Pattern 2049 and taken off; I66.22 -> I10 (dx email sent)", "dollars": 389.00},
 {"chart": "17478414", "result": "done", "action": "CAP07 ins9521409 added (policy from Pam's admission record, begin 11/08/2026, no group), 271 ACTIVE, order 2,1; v19462412 + v19462163 sent to CHP (204); Medicare plan stays", "dollars": 530.00},
 {"chart": "12182505", "result": "done", "action": "Railroad number rewritten on ins9519511, order 3,2; 6 visits re-pointed and sent (204); RET01 271 AAA 51 (provider not on file) and AARP INACTIVE - watch the remits; Humana PDP is the drug plan, no payer", "dollars": 1210.00},
 {"chart": "17475908", "result": "done", "action": "WOINS $310 + $111 (TRICARE duplicate, remit not obtainable) on William's word", "dollars": 421.00},
 {"chart": "17477353", "result": "done", "action": "WOINS $109 (Humana CO-4 on the CCM add-on) on William's word", "dollars": 109.00},
 {"chart": "17471273", "result": "done", "action": "WOINS $310 + 6 x $111 (Aetna finalized at $0) on William's word", "dollars": 976.00},
 {"chart": "17469397", "result": "done", "action": "after-death charges 23367095 + 23367096 voided (write-offs and $0 payments voided first)", "dollars": 315.00},
 {"chart": "17475365", "result": "done", "action": "after-death charge 23367066 voided", "dollars": 206.00},
 {"chart": "17477267", "result": "claude (crossover watch)", "action": "09/20/2026 99487 charge 23366938 voided on William's word; the August $809.20 Medigap coinsurance at Florida Blue stays on the crossover-wait rule", "dollars": 206.00},
 {"chart": "17477572", "result": "done", "action": "I10 first on 3 charges, sent to CHP (204 x3); Pattern 2776 cleared by removing Z01.818 (I10, M17.12, R10.9 remain)", "dollars": 532.00},
 {"chart": "17473460", "result": "handed back", "action": "chart's number = the sheet's; AMD 271 AAA 73 and Medicare's plain check 73 (name mismatch), nothing written - photo of the Medicare card needed (23 visits)", "dollars": 690.59}]
n_resent = sum(len(v) for _, v, _, _ in RESENT); d_resent = round(sum(d for _, _, d, _ in RESENT), 2); d_wo = round(sum(d for _, _, d, _ in WO), 2); d_void = round(sum(v["dollars"] for v in VOIDED), 2)
rep = {"schema": "button-run/1", "stamp": S, "mode": "live", "status": "ok",
 "headline": "BUTTON PRESS (William 12:35 AM ET): 16 refresh-board cards worked - 13 done, 3 handed back; re-sent %d visits $%.2f; written off $%.2f; voided after death $%.2f; Columns 0/5/0/1 -> 0/2/0/1; ERA not in this press" % (n_resent, d_resent, d_wo, d_void),
 "note": "BUTTON PRESS 2026-11-25T05:56:23Z · mode live · steps columns, cascade · packages none · William 11/25 ~12:35 AM ET: 'process all the new insurance info on the refresh board and given here fix the charts and rebill them and then give me a report here and then give me another insurance refresh list here and an email and update the board to keep working on'",
 "run_url": "https://claude.ai/code/session_01HHfWRDQzUP5c1sfAy6tDA5", "started": "2026-11-25T06:34:00Z", "ended": ENDED, "engine": "claude", "trigger": "trig_01S771Si8VJ8DvcwgHMHGYB5",
 "summary": {"columns": {"before": {"charge_review": 0, "claim_inspector": 5, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 2, "unbilled": 0, "exclusions": 1}},
             "era": {"before": {"checks": 0, "unposted": 0.0}, "after": {"checks": 0, "unposted": 0.0}, "note": "era step not in this press (0557Z run: 0 checks)"},
             "posted": {"pay": 0.0, "woins": d_wo, "wocaid2nd": 0.0, "wolate": 0.0},
             "resent": {"visits": n_resent, "dollars": d_resent},
             "written_off": {"count": len(WO), "dollars": d_wo},
             "voided": {"charges": sum(len(v["charges"]) for v in VOIDED), "dollars": d_void},
             "packages": {"applied": 0, "refused": 0, "skipped": 0},
             "outstanding": outstanding,
             "denials": {"visits": wd.get("total_visits"), "actionable": wd.get("actionable_visits"), "actionable_amt": wd.get("actionable_amt"), "asof": wd.get("asof")},
             "g0439": {"pcode": "pcode67716", "description": "ANNUAL WELLNESS VST; PPS SUBSQT VST", "standard_fee": 204.00, "how": "read-only AdvancedMD procedure look-up; $204.00 is the fee on every G0439 charge billed (e.g. v19448611, v19448364)"}},
 "steps": [
  {"name": "board", "title": "Board input (William's 12:35 AM order)", "status": "ok",
   "summary": "46 ids named on the press; cards an earlier board file already answered were skipped; 16 worked: 13 done (6 charts fixed + 23 visits re-sent, 3 write-offs on William's word, 3 after-death voids), 3 handed back (new Medicare card x2 incl. a merge decision, card photo x1); board file board_updates_2026-11-25T0634Z.json (27 ops incl. the 11 of the 0557Z file, asof 06:37Z) uploaded to the board inbox; face sheets email sent (19 cards on William's turn, $10,395.23)",
   "counts": {"cards": 16, "done": 13, "handed_back": 3, "resent_visits": n_resent, "written_off": len(WO), "voided_charges": sum(len(v["charges"]) for v in VOIDED)},
   "lines": CARDS},
  {"name": "feed", "title": "Claimocity feed", "status": "ok", "summary": "reprocess of the 11/13 HL7 created v19462412 on chart 17478414 (59 visits already entered); dx_codes_needed email sent (I66.22 -> I10); order sweep 065306Z 2 NO CLAIM (17472729 clinician move, 17478219 CHP number); feed registers + monitor + practice db register on main"},
  {"name": "columns", "title": "Claims Center columns", "status": "ok", "summary": "CR 0->0, CI 5->2 (Pattern 2776 x3 on chart 17477572 cleared by removing Z01.818), Unbilled 0->0, Exclusions 1->1 (AET12 hold)",
   "counts": {"inspector_cleared": 3, "inspector_held": 2}, "lines": [{"visit": "19461189", "chart": "17478413", "hold": "Pattern 28158 (O24.419) - card on William's turn"}, {"visit": "19462192", "chart": "17477311", "hold": "Pattern 4531 (99223 at POS 31) - card on William's turn"}, {"visit": "19455937", "chart": "24750", "hold": "AET12 PREF0288 carrier record"}]},
  {"name": "cascade", "title": "Cascade pre-check", "status": "ok", "summary": "precheck --days 3 --max 120: 17 pairs, 0 flagged; void_rules 1 open, 0 voided; Stedi this run: 1 Medicare plain check (chart 17473460)"},
  {"name": "lookup", "title": "G0439 look-up (read-only)", "status": "ok", "summary": "AdvancedMD pcode67716 'ANNUAL WELLNESS VST; PPS SUBSQT VST', standard fee $204.00"},
  {"name": "packages", "title": "Approved packages", "status": "ok", "summary": "none on this press (register: 94 done)"},
  {"name": "outstanding", "title": "Outstanding claims", "status": "ok", "summary": "$%.2f on %s visits / %s charts; over a year %s / $%.2f (0557Z figures)" % (outstanding["total"], outstanding["visits"], outstanding["charts"], o365["n"], o365["dollars"])},
  {"name": "denials", "title": "Working denials", "status": "ok", "summary": "%s visits, %s actionable $%.2f (0557Z refresh)" % (wd.get("total_visits"), wd.get("actionable_visits"), wd.get("actionable_amt") or 0)}],
 "packages": [],
 "resent": [{"chart": c, "visits": v, "dollars": d, "why": w} for c, v, d, w in RESENT],
 "written_off": [{"chart": c, "visit": v, "dollars": d, "why": w} for c, v, d, w in WO],
 "voided": VOIDED,
 "waiting": ["Chart 17471643 / 17471791 (one patient): new Medicare card + which chart to keep ($289.59); Florida Community Care Medicaid plan set once Medicare is right",
             "Chart 17473460: photo of the Medicare card - 73 name mismatch on AMD and on Medicare's plain check ($690.59, 23 visits)",
             "Chart 12182505: Railroad 271 AAA 51 (provider not on file) and AARP INACTIVE - 6 claims sent, watch the remits",
             "Chart 17477267: $809.20 Medigap coinsurance at Florida Blue (13 secondaries) on the crossover-wait rule",
             "Claim Inspector: v19461189 Pattern 28158 (chart 17478413) and v19462192 Pattern 4531 (chart 17477311) - cards on William's turn",
             "Exclusions: AET12 PREF0288 carrier record (chart 24750) - left by rule",
             "Feed order sweep: v19458775 (chart 17472729) waits for the clinician move; v19459226 (chart 17478219) waits on the CHP member number",
             "Working Denials board inbox: denials_updates 10/14 + 10/16 unapplied (registry lastCheck 10/23) - 40 days",
             "Neon: no NEON_DATABASE_URL in this container - the Neon leg was skipped (practice db register on main)"],
 "errors": []}
for p in ("%s/reports/button/%s.json" % (REPO, S), "%s/reports/button/latest.json" % REPO):
    json.dump(rep, open(p, "w"), indent=1)
print("written", rep["headline"])
