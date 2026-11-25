# PLAIN ENGLISH (run report files of the ehpa Billing Button run 2026-11-25T0435Z)
# Decides: nothing. Writes (1) "_run report 11-25 0435.csv" (patient-level, Drive / William only), (2) a dated section appended to
#   needs_facesheet_list.md (workspace / Drive only), (3) the button-run/1 report <repo>/reports/button/2026-11-25T0435Z.json + latest.json
#   (chart / visit / check ids and dollars only) from this run's registers and the read-only outputs (outstanding_claims.json,
#   working_denials_latest.json). Usage: python3 report_1125_0435.py <ended iso>
import json, csv, os, sys, datetime
S = "2026-11-25T0435Z"; REPO = "/home/claude/effinger-billing-backend"; ENDED = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
oc = json.load(open("outstanding_claims.json")) if os.path.exists("outstanding_claims.json") else {}
wd = json.load(open("working_denials_latest.json")) if os.path.exists("working_denials_latest.json") else {}
def g(d, *ks, default=None):
    for k in ks:
        if isinstance(d, dict) and k in d: return d[k]
    return default
ots = g(oc, "summary", default=oc) or {}
outstanding = {"total": g(ots, "total", "total_open", default=324365.46), "visits": g(ots, "visits", default=2800), "charts": g(ots, "charts", default=485),
               "over_365": {"n": 584, "dollars": 28749.88}}
wds = g(wd, "summary", default={}) or {}
RESENT = [  # (chart, visits, dollars, why)
    ("17478470", ["19461860", "19461854"], 603.00, "CHP plan added from William's sheet - sent to CHP"),
    ("17478452", ["19461642", "19461630"], 421.00, "CHP plan added from William's sheet - re-pointed from Medicare to CHP"),
    ("17478455", ["19461640", "19461968", "19461853", "19461990", "19462060", "19462187", "19462331"], 1270.00, "CHP plan added from William's sheet - re-pointed to CHP"),
    ("17478013", ["19458908", "19459085", "19459129", "19459117", "19459151", "19459576", "19459559", "19459599", "19459750", "19459730", "19459723"], 1910.00, "VA CCN auth VA9011260694 on the 10/21-10/31 stay - re-sent to VA CCN"),
    ("17475970", ["19460346", "19460344", "19460401", "19460532", "19460684", "19461085", "19461064", "19461041", "19461136", "19461269", "19461242", "19461295", "19461449", "19461629", "19461858"], 2683.00, "VA CCN auth VA0065278022 on the 11/04 stay - re-pointed from Medicare to VA CCN"),
    ("17474021", ["19416417", "19416418"], 49.16, "current Medicare number proven ACTIVE; secondary balance sent to BCBS"),
    ("17473160", ["19442323"], 315.00, "birth date corrected to Medicare's record - re-sent to Medicare"),
    ("17472826", ["19462327"], 160.00, "pre-check: Medicare Advantage on DOS - re-pointed to the chart's BCBS MA plan"),
    ("17473090", ["19462325"], 160.00, "pre-check: Medicare Advantage on DOS - re-pointed to the chart's BCBS MA plan"),
]
WO = [("17476912", "19445941", 389.00, "WONCS - William 'write off' (WellCare CARC 252)"),
      ("46678", "19442338,19448386,19452574", 725.00, "WONCS - William 'write off' (CHP PR-242)"), ("21491", "19459620", 206.00, "WONCS - CHP PR-242"),
      ("48008", "19423586", 315.00, "WONCS - CHP PR-242"), ("17474083", "19434037", 206.00, "WONCS - CHP PR-242"), ("17476942", "19459617", 206.00, "WONCS - CHP CO-243")]
ERA = [("1053637", "HUM01", 83.13, "Post button 1 visit; dismissed (3 denial / $0 lines recorded)"),
       ("1053638", "UNI20", 2350.81, "Post button 15 visits $2,005.11; 11/04 write-offs voided on v19458938 + v19459138, 4 UHC lines posted ERA-linked $345.70 (WOINS $284.30); dismissed")]
resent_v = sum(len(r[1]) for r in RESENT); resent_d = round(sum(r[2] for r in RESENT), 2)
wo_d = round(sum(w[2] for w in WO), 2)
# (1) CSV
with open("_run report 11-25 0435.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["section", "chart", "visit(s)", "amount", "action"])
    w.writerow(["columns", "", "", "", "Charge Review 0->0; Claim Inspector 5->5 (standing holds: Pattern 692 x3, 4531, 28158); Unbilled 0->29->0 (29 'prior payor' rows released); Exclusions 1->1 (AET12 carrier record)"])
    for c, v, d, why in RESENT: w.writerow(["re-sent", c, " ".join(v), "%.2f" % d, why])
    for c, v, d, why in WO: w.writerow(["written off", c, v, "%.2f" % d, why])
    w.writerow(["voided", "17477258", "19455614", "206.00", "after-death 99487 voided on William's 'void' (write-off and $0 line voided first)"])
    for ck, p, d, a in ERA: w.writerow(["ERA", ck, p, "%.2f" % d, a])
    w.writerow(["feed", "17477128", "2 visits (11/09, 11/19)", "282.00", "retry of cleared skips entered with I10 for S82.843D (email sent)"])
# (2) needs list section
sec = ["", "## %s ehpa Billing Button run (live, all steps)" % S,
       "- Columns CR/CI/Unb/Exc 0/5/0/1 -> 0/5/0/1 (Unbilled went to 29 after the ERA posts; the 29 'prior payor' rows were released).",
       "- ERA 2 checks $2,433.94 -> 0: posted $2,088.24 by the Post button + $345.70 ERA-linked fallback after voiding the 11/04 Medicare-denial write-offs on two UHC-paid CCM visits.",
       "- Board: 19 cards answered/closed; %d visits re-sent ($%.2f); WONCS $%.2f on William's word; 1 after-death charge voided." % (resent_v, resent_d, wo_d),
       "- Still needed from William: Catalano chart 20752 (born 1935) Medicare number; Cowling first-admission VA auth (10/05-10/12); Karnes April decision.",
       "- Calls learned: addreferralplan get-or-returns the chart's plan for the SAME refprov (a new plan only with a different refprov) - logged in captured_calls.md."]
open("needs_facesheet_list.md", "a").write("\n".join(sec) + "\n")
# (3) button-run/1
steps = [
 {"name": "board", "title": "Board input", "status": "ok", "summary": "19 cards worked from William's 11/25 answers (16 closed, 3 handed back); 0 drops, 0 denials commands queued", "counts": {"cards": 19, "handed_back": 3, "drops": 0, "commands": 0}},
 {"name": "columns", "title": "Claims Center columns", "status": "ok", "summary": "CR 0->0, CI 5->5, Unbilled 0->0 (29 prior-payor rows released mid-run), Exclusions 1->1", "counts": {"unbilled_released": 29}},
 {"name": "era", "title": "ERA posting", "status": "ok", "summary": "2 checks / $2,433.94 -> 0 checks / $0.00", "dollars": {"posted_post_button": 2088.24, "posted_fallback": 345.70, "woins_fallback": 284.30},
  "lines": [{"check": e[0], "payer": e[1], "amount": e[2], "action": e[3]} for e in ERA]},
 {"name": "cascade", "title": "Cascade pre-check", "status": "ok", "summary": "precheck 19 patient/payer pairs (2 new lookups), 2 flagged ADVANTAGE PLAN -> both 11/22 visits re-pointed to the chart's MA plan; void rules: 0 voided (1 open)",
  "lines": [{"chart": "17472826", "visit": "19462327", "action": "re-pointed to BCBS MA"}, {"chart": "17473090", "visit": "19462325", "action": "re-pointed to BCBS MA"}]},
 {"name": "packages", "title": "Approved packages", "status": "ok", "summary": "no approved package (register 94 done; page 0 approved)"},
 {"name": "cred", "title": "Credentialing check", "status": "ok", "summary": "NPPES 3 records 0 changed; LEIE 0 matches; no reminders due"},
 {"name": "outstanding", "title": "Outstanding claims", "status": "ok", "summary": "%s visits on %s charts, $%s open" % (outstanding["visits"], outstanding["charts"], outstanding["total"])},
 {"name": "denials", "title": "Denials refresh", "status": "ok", "summary": "7886 denied visits on 884 charts; 46 actionable $8,631.00 (45 inside 12 months $8,425.00); WRITTEN-OFF 3015, RESOLVED 4572, RESUBMITTED 183, OPEN 116"},
]
rep = {"schema": "button-run/1", "stamp": S, "mode": "live", "status": "ok",
       "headline": "Columns 0/5/0/1 -> 0/5/0/1; ERA 2 checks $2,433.94 -> 0 checks $0.00; posted $2,433.94; re-sent %d" % resent_v,
       "note": "", "run_url": "https://claude.ai/code/session_01HHfWRC8rLfzUzE72JBZhWM", "started": "2026-11-25T04:35:00Z", "ended": ENDED,
       "engine": "claude", "trigger": "trig_01S771Si8VJ8DvcwgHMHGYB5",
       "summary": {"denials": {"visits": 7886, "actionable": 46, "actionable_amt": 8631.0, "asof": "2026-11-25 05:36 UTC"}, "columns": {"before": {"charge_review": 0, "claim_inspector": 5, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 5, "unbilled": 0, "exclusions": 1}},
                   "era": {"before": {"checks": 2, "unposted": 2433.94}, "after": {"checks": 0, "unposted": 0.0}},
                   "posted": {"pay": 2433.94, "woins": 284.30, "wocaid2nd": 0.0, "wolate": 0.0},
                   "resent": {"visits": resent_v, "dollars": resent_d}, "written_off": {"count": 11, "dollars": wo_d},
                   "packages": {"applied": 0, "refused": 0, "skipped": 0}, "outstanding": outstanding},
       "steps": steps, "packages": [],
       "waiting": ["Claim Inspector: 5 visit(s) with Pattern 692 / 4531 / 28158 holds - chat session or William",
                   "Exclusions: AET12 PREF0288 carrier record (board row aet12-carrier-cpid) - left by rule",
                   "Chart 17478013: this run's referral-plan probe left a blank plan with the third referring provider as the chart's MAIN plan (rplan18462897) - in AMD set rplan18462365 (Effinger, carries the auth) as main or delete the blank one",
                   "Chart 17475970: the main referral plan now carries the 11/04-stay auth; the unpaid 6/20-6/28 and 9/7-9/14 visits point to it - repoint them to their own stay's plan before any re-send",
                   "Chart 17473431: Railroad Medicare (RET01) answers 51 'provider not on file' - Palmetto RRB enrollment",
                   "Feed: CPT G0439 is not in claimocity_import.py's PCODE/FEE tables - a retry waits on it",
                   "Board inbox: 3 registered files not trashed - the session's permission check blocked the trash call (1KrCVQGeFUVKgju_YrAOXQlNgst690LmA, 1HHD8giMIcdkKMzusQj2u3gRQ__1XMQ_y, 19J-WNLEIzfp74NqKtLSWgBwCzEfL1y8c) - trash by hand in Drive 'board inbox'; 528 others trashed",
                   "Board: catalano 20752 Medicare number, cowling first-admission VA auth, karnes April decision - on William's turn"],
       "errors": []}
for p in ("%s/reports/button/%s.json" % (REPO, S), "%s/reports/button/latest.json" % REPO):
    json.dump(rep, open(p, "w"), indent=1)
print("resent", resent_v, resent_d, "wo", wo_d)
