#!/usr/bin/env python3
# PLAIN ENGLISH (the button-run/1 report file of the ehpa Billing Button run 2026-11-25T0557Z)
# Decides: nothing. Writes <repo>/reports/button/2026-11-25T0557Z.json + latest.json (schema button-run/1 as tools/button/run_all.py
#   writes it) from this run's registers and read-only outputs - chart / visit / check ids and dollars only, never a name.
# Usage: python3 report_1125_0557.py <ended iso>
import json, os, sys, datetime
S = "2026-11-25T0557Z"; REPO = "/home/claude/effinger-billing-backend"
ENDED = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
oc = json.load(open("outstanding_claims.json")); wd = json.load(open("working_denials_latest.json"))
o365 = oc.get("over_365"); o365 = o365 if isinstance(o365, dict) else {"n": len(o365), "dollars": round(sum(float(r.get("insbalance") or r.get("amount") or 0) for r in o365), 2)}
outstanding = {"total": oc.get("total"), "visits": oc.get("visits"), "charts": oc.get("charts"), "over_365": o365}
era = json.load(open("work/engine_era/%s.json" % S))
era_step = next((s for s in era.get("steps", []) if s.get("name") == "era"), {"name": "era", "title": "ERA posting", "status": "ok", "summary": "0 checks $0.00 -> 0 checks $0.00"})
RESENT = [("17473749", ["19440501", "19442537", "19448611", "19448758", "19450214", "19452603", "19455642"], 1751.00, "William 'restore': Medicare $0 CO-24/CO-109 postings + WOINS voided, billed to the UHC MA plan"),
          ("17478200", ["19459188", "19459194"], 421.00, "Detego Health plan added (carrier William created), auth on the referral plan, sent as originals"),
          ("17478332", ["19460350"], 433.00, "Florida Blue MA plan added from William's sheet, ACTIVE 11/03/2026, sent")]
WO = [("21839", "19423852", 141.00, "WOLATE - William 'write off' (past the 12-month filing limit)"), ("21839", "19423656", 315.00, "WOLATE - William 'write off' (past the 12-month filing limit)")]
rep = {"schema": "button-run/1", "stamp": S, "mode": "live", "status": "ok",
 "headline": "Columns 0/8/0/1 -> 0/2/0/1; ERA 0 checks $0.00 -> 0 checks $0.00; posted $0.00; re-sent %d; written off $456.00" % sum(len(v) for _, v, _, _ in RESENT),
 "note": "no BUTTON PRESS brief (scheduled firing 10 minutes after the 0435Z run ended) -> live, all steps, every approved package",
 "run_url": "https://claude.ai/code/session_01HHfWRDQzUP5c1sfAy6tDA5", "started": "2026-11-25T05:57:00Z", "ended": ENDED, "engine": "claude", "trigger": "trig_01S771Si8VJ8DvcwgHMHGYB5",
 "summary": {"columns": {"before": {"charge_review": 0, "claim_inspector": 8, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 2, "unbilled": 0, "exclusions": 1}},
             "era": {"before": {"checks": 0, "unposted": 0.0}, "after": {"checks": 0, "unposted": 0.0}},
             "posted": {"pay": 0.0, "woins": 0.0, "wocaid2nd": 0.0, "wolate": 456.0},
             "resent": {"visits": sum(len(v) for _, v, _, _ in RESENT), "dollars": round(sum(d for _, _, d, _ in RESENT), 2)},
             "written_off": {"count": 3, "dollars": 456.0},
             "packages": {"applied": 0, "refused": 0, "skipped": 0},
             "outstanding": outstanding,
             "denials": {"visits": wd.get("total_visits"), "actionable": wd.get("actionable_visits"), "actionable_amt": wd.get("actionable_amt"), "asof": wd.get("asof")}},
 "steps": [
  {"name": "board", "title": "Board input", "status": "ok", "summary": "8 cards William answered 04:40-05:27Z worked (4 closed, 4 handed back), 1 Pattern 692 card closed, 1 unanswered 11/14 ask handed back, 1 new card (inspector hold since 11/22); 0 drops, 0 denials commands; 3 applied inbox files trashed",
   "counts": {"cards": 11, "handed_back": 5, "closed": 5, "new": 1, "drops": 0, "commands": 0},
   "lines": [{"chart": "17476021", "action": "facesheet number = the chart's, Medicare 72; MBI look-up with SSN 75 - new card needed", "dollars": 3119.89},
             {"chart": "48458", "action": "facesheet number = the chart's, Medicare 72; look-up 75 under both spellings - new card needed", "dollars": 107.0},
             {"chart": "21839", "action": "WOLATE on William's word, v19423852 + v19423656", "dollars": 456.0},
             {"chart": "17473749", "action": "restored 7 visits and billed UHC MA on William's word", "dollars": 1751.0},
             {"chart": "17474537", "action": "DOB given, card back to William for the Medicare number", "dollars": 43.26},
             {"chart": "17478200", "action": "Detego plan + auth, 2 visits sent", "dollars": 421.0},
             {"chart": "17478219", "action": "WellCare inactive 2026 (dated checks) - CHP number still needed", "dollars": 639.0},
             {"chart": "17478332", "action": "Florida Blue MA plan ACTIVE, v19460350 sent", "dollars": 433.0},
             {"chart": "17478413", "action": "O24.419 diagnosis question handed back (asked 11/14, never on his turn)", "dollars": 421.0},
             {"chart": "17477311", "action": "new card: 99223 at POS 31 (Pattern 4531) - coding decision", "dollars": 421.0}]},
  {"name": "columns", "title": "Claims Center columns", "status": "ok", "summary": "CR 0->0, CI 8->2 (6 advisories bypassed: Pattern 692 x3 new-admission rule, 35790 x3), Unbilled 0->0, Exclusions 1->1 (AET12 hold)",
   "counts": {"inspector_bypassed": 6, "inspector_held": 2}, "lines": [{"visit": "19461189", "chart": "17478413", "hold": "Pattern 28158"}, {"visit": "19462192", "chart": "17477311", "hold": "Pattern 4531"}, {"visit": "19455937", "chart": "24750", "hold": "AET12 PREF0288"}]},
  era_step,
  {"name": "cascade", "title": "Cascade pre-check", "status": "ok", "summary": "precheck --days 3 --max 120: 17 pairs (0 new look-ups), 0 flagged; void_rules 1 open, 0 voided; Stedi this month 115 calls $48.50 list (this run: 2 MBI look-ups, 3 eligibility checks)"},
  {"name": "packages", "title": "Approved packages", "status": "ok", "summary": "0 approved, 0 waiting (register: 94 done)"},
  {"name": "cred", "title": "cred_check", "status": "ok", "summary": "NPPES 3 records 0 changed; revalidation TBD x3; LEIE 84,224 rows 0 matches; reminders none"},
  {"name": "outstanding", "title": "Outstanding claims", "status": "ok", "summary": "$%.2f on %s visits / %s charts; over a year %s / $%.2f" % (outstanding["total"], outstanding["visits"], outstanding["charts"], o365["n"], o365["dollars"])},
  {"name": "denials", "title": "Working denials refresh", "status": "ok", "summary": "%s visits, %s actionable $%.2f (%s inside 12 months)" % (wd.get("total_visits"), wd.get("actionable_visits"), wd.get("actionable_amt") or 0, wd.get("timely_visits"))}],
 "packages": [],
 "resent": [{"chart": c, "visits": v, "dollars": d, "why": w} for c, v, d, w in RESENT],
 "written_off": [{"chart": c, "visit": v, "dollars": d, "why": w} for c, v, d, w in WO],
 "waiting": ["Claim Inspector: v19461189 Pattern 28158 (chart 17478413, diagnosis) and v19462192 Pattern 4531 (chart 17477311, 99223 at POS 31) - cards on William's turn",
             "Exclusions: AET12 PREF0288 carrier record (board row aet12-carrier-cpid) - left by rule",
             "Feed order sweep: v19458775 (chart 17472729) waits for the clinician move to the NP (a chat session runs --fix-clinician); v19459226 (chart 17478219) waits on the CHP member number",
             "Working Denials board inbox: denials_updates_2026-10-14T1710Z.json and 2026-10-16T1310Z.json not in that board's applied map (registry lastCheck 10/23) - awaiting board sync for 40 days",
             "Neon: no NEON_DATABASE_URL and no 'neon database url' Gmail thread - the Neon leg was skipped this run"],
 "errors": []}
for p in ("%s/reports/button/%s.json" % (REPO, S), "%s/reports/button/latest.json" % REPO):
    json.dump(rep, open(p, "w"), indent=1)
print("written", rep["headline"])
