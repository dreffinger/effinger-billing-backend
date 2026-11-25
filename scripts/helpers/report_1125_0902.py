#!/usr/bin/env python3
# PLAIN ENGLISH (write the button-run/1 report file for the DRY run 2026-11-25T0902Z)
# Decides: nothing. This firing carried no BUTTON PRESS line (live, all steps by default) but another Billing Button run
#   (2026-11-25T0900Z, a press of 08:10:30Z, steps columns + cascade) started 90 seconds earlier and was still importing the
#   monthly CCM feed file (320 visits) when the 0f guard's 60 minutes ran out - so by rule 0f this run went READ-ONLY (mode dry):
#   no AdvancedMD write, no board file, no email, no mirror beyond the digest. The report carries what the reads showed, with
#   chart / visit / check ids and dollars only. The privacy gate runs on both copies after this.
# Never touches: AMD, the board, Drive. Usage: python3 report_1125_0902.py
import json, datetime
S = "2026-11-25T0902Z"
R = "/home/claude/effinger-billing-backend/reports/button/"
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def step(name, title, status, summary, counts=None, dollars=None, lines=None, errors=None, started=None, ended=None):
    return {"name": name, "title": title, "status": status, "summary": summary, "counts": counts or {}, "dollars": dollars or {},
            "lines": lines or [], "errors": errors or [], "started": started or "2026-11-25T10:02:00Z", "ended": ended or now}
out = json.load(open("/home/claude/unbilled/outstanding_claims.json"))
den = json.load(open("/home/claude/unbilled/working_denials_latest.json"))
def g(d, *ks, default=None):
    for k in ks:
        if isinstance(d, dict) and k in d: return d[k]
    return default
steps = [
    step("feed", "Claimocity feed ingest", "skipped",
         "FEED NOT IMPORTED THIS RUN: another run's ingest (2026-11-25T0900Z) has been running since 2026-11-25T0901Z - the next run takes what is left. Bucket 37 objects, 1 new (20261125, 508 KB, the monthly CCM file, 306 messages - being imported by the 0900Z run: 320 visits created by 09:58Z); no retry (c1) by the same rule; feed order sweep 20261125T100420Z (dry): 25 visits read, 0 checks would be bought, 2 not saved (v19458775 chart 17472729 waits for the clinician move - chat; v19459226 chart 17478219 - Medicare names another primary on 10/22/2026); no intake (no file downloaded by this run)",
         counts={"new_files": 1, "entered": 0, "sweep_saved": 0, "sweep_not_saved": 2}, started="2026-11-25T10:03:00Z"),
    step("board", "Insurance Refresh Board input", "skipped",
         "read inline at 10:03Z (dry run - nothing acted on, no board file): 0 drops, 0 Working Denials commands; 6 cards on Claude's turn carry an answer of William's newer than the 0809Z run's read (08:19Z) - the 0900Z live run (steps columns = board input) holds the turn for them; board inbox: board_updates_2026-11-25T0809Z.json (08:42Z) not yet in the board's applied map (awaiting board sync, 1.4 h); Working Denials inbox: denials_updates_2026-10-14T1710Z.json + 2026-10-16T1310Z.json still waiting (42 days - that board's registry has applied nothing since 10/23); Drive hca / tmh / PCC / 835 folders and Pam Gmail: nothing new since 08:00Z",
         counts={"drops": 0, "commands": 0, "william_answers_waiting": 6},
         lines=[{"chart": "48458", "what": "William 08:26Z: PCC payer history pasted - check hospice spans, rebill with GV where hospice, use the Medicare number from the other charts (DANVERS / DANIELS), send every claim unless duplicate"},
                {"chart": "17471643", "what": "William 08:21Z: retry with the hospice modifier if before the death, then write it off ($218, 01/2026 visits at Medicare since 09/11)"},
                {"chart": "17471238", "what": "William 08:20Z: bill the second (11/10/2026 wellness) as a 99309"},
                {"chart": "17472491", "what": "William 08:22Z: 'send to railroad' - take back WOLATE 111.00 on charge 23327550 (11/03/2025) and send to the Railroad Medicare plan"},
                {"chart": "17477648", "what": "William 08:19Z: SurgeryPlus entered as a payer (bill paper) - add policy, send v19453782 v19453773 v19453753 ($630)"},
                {"chart": "17478216", "what": "William 08:19Z: 'yes same person' - move the 11/2026 CCM ($315) to the older chart (17477499 / 21875), repoint the feed patient map"}],
         started="2026-11-25T10:03:00Z"),
    step("columns", "Claims Center columns", "skipped",
         "read-only (dry): Charge Review 0 -> 0; Claim Inspector 90 -> 87 (the 0900Z run's CCM batch: Pattern 35790 add-on advisories, 11256 laterality, hospitalization-date holds - that run is working them); Unbilled 0 -> 0; Exclusions 1 -> 1 (AET12 chart 24750 v19455937 PREF0288 carrier CPID, standing hold)",
         counts={"before": {"charge_review": 0, "claim_inspector": 90, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 87, "unbilled": 0, "exclusions": 1}},
         started="2026-11-25T10:02:00Z", ended="2026-11-25T10:12:30Z"),
    step("era", "ERA posting", "skipped",
         "read-only (dry): 1 unposted check $230.53 - UHC W378708629 (ERA 1053641), 2 visits, both postable; nothing posted, nothing dismissed (the 0900Z run has no ERA step - the next live run posts it); era_upload not run (no new 835 in 'bht Optum era downloads'); no new Availity file",
         counts={"before": {"checks": 1, "unposted": 230.53}, "after": {"checks": 1, "unposted": 230.53}}, dollars={"unposted": 230.53},
         lines=[{"check": "1053641", "payer": "UNI20", "trn": "W378708629", "dollars": 230.53, "visits": 2, "action": "waits for the next live run"}],
         started="2026-11-25T10:05:00Z"),
    step("cascade", "Insurance cascade pre-check", "ok",
         "precheck --days 3 --max 120: 17 pairs, 0 new lookups (cache from the 0856UTC bundle), 0 flagged; void_rules --dry: 1 open rule, 0 voids; Stedi 2026-11: 122 calls $51.30 at list (0 this run)",
         counts={"pairs": 17, "flagged": 0, "stedi_calls_this_run": 0}, started="2026-11-25T10:05:00Z"),
    step("packages", "Approval packages", "ok", "0 approved on the page, register 94 items all done; nothing refused (no write attempted), nothing submitted",
         counts={"applied": 0, "refused": 0, "skipped": 0, "submitted": 0}),
    step("cred", "Credentialing check", "ok", "NPPES 3 records, 0 changed; LEIE 84,224 rows, 0 matches; reminders due none; no cred_updates file",
         counts={"nppes_changed": 0, "leie_matches": 0}),
    step("outstanding", "Outstanding claims", "ok",
         "%s visits on %s charts, $%s open (%s over 365 days, $%s) -> reports/button/outstanding_latest.json (identical to the 0809Z totals - the 320 feed visits entered at 09:30Z by the 0900Z run are not in it yet)" % (
             g(out, "visits", "total_visits", default="?"), g(out, "charts", "total_charts", default="?"), g(out, "total", "total_dollars", default="?"),
             g(g(out, "over_365", default={}) or {}, "n", "visits", default="?"), g(g(out, "over_365", default={}) or {}, "dollars", default="?")),
         started="2026-11-25T10:07:00Z"),
    step("denials", "Working denials refresh", "ok",
         "877 charts, 13,243 denial lines, 7,868 visits; 52 actionable $9,755 (51 inside 12 months $9,549); status WRITTEN-OFF 2998 / RESOLVED 4571 / RESUBMITTED 175 / OPEN 124; 0 errors -> reports/button/working_denials_latest.json",
         counts={"charts": 877, "lines": 13243, "visits": 7868, "actionable": 52}, dollars={"actionable": 9755.0}, started="2026-11-25T10:07:00Z"),
]
o365 = g(out, "over_365", default={}) or {}
d = {"schema": "button-run/1", "stamp": S, "mode": "dry", "status": "ok",
     "headline": "DRY RUN (rule 0f: the 0900Z run - a press of 08:10Z, steps columns + cascade - was still importing the monthly CCM feed file when the 60-minute guard ran out). Columns CR/CI/Unb/Exc 0/90/0/1 -> 0/87/0/1 read only; ERA 1 check $230.53 unposted, left for the next live run; posted $0; re-sent 0; 6 of William's board answers (08:19-08:26Z) wait on the 0900Z live run",
     "note": "no BUTTON PRESS line in this firing (defaults live / all / every package) - demoted to dry by the cross-container guard; feed not imported (another run's ingest running since 0901Z)",
     "run_url": "https://claude.ai/code/session_01HHfWREPgND3R3HApTU5F13", "started": "2026-11-25T09:02:00Z", "ended": now,
     "engine": "claude", "trigger": "trig_01S771Si8VJ8DvcwgHMHGYB5",
     "summary": {"columns": {"before": {"charge_review": 0, "claim_inspector": 90, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 87, "unbilled": 0, "exclusions": 1}},
                 "era": {"before": {"checks": 1, "unposted": 230.53}, "after": {"checks": 1, "unposted": 230.53}},
                 "posted": {"pay": 0.0, "woins": 0.0, "wocaid2nd": 0.0, "wolate": 0.0}, "resent": {"visits": 0, "dollars": 0.0},
                 "written_off": {"count": 0, "dollars": 0.0}, "packages": {"applied": 0, "refused": 0, "skipped": 0},
                 "outstanding": {"total": g(out, "total", "total_dollars", default=0), "visits": g(out, "visits", "total_visits", default=0), "charts": g(out, "charts", "total_charts", default=0),
                                 "over_365": {"n": g(o365, "n", "visits", default=0), "dollars": g(o365, "dollars", default=0)}}},
     "steps": steps, "packages": [],
     "waiting": [
         "RUN OVERLAP: this firing (09:02Z, no BUTTON PRESS line) started 90 s after the 0900Z press run; the 0f guard never cleared in 60 minutes (the 0900Z run was importing the 306-message monthly CCM file - 320 visits by 09:58Z, then its verify / inspector / columns / cascade steps) - this run is read-only; the 0900Z run carries the live work",
         "ERA 1053641 UHC W378708629 $230.53 (2 visits, postable) unposted - the 0900Z run has no ERA step; the next live run (6-hourly backend ~12:39Z or a press) posts it",
         "6 William answers on Claude's turn since 08:19Z (charts 48458, 17471643, 17471238, 17472491, 17477648, 17478216) - the 0900Z live run's board input step; if its digest does not show them worked, the next press does",
         "Working Denials board inbox: denials_updates_2026-10-14T1710Z.json and 2026-10-16T1310Z.json still waiting (42 days; that board's registry has applied nothing since 10/23)",
         "board_updates_2026-11-25T0809Z.json awaiting board sync (uploaded 08:42Z, not in meta/drive_sync.applied at 10:03Z)",
         "feed: v19458775 (chart 17472729) waits for the clinician move to prof15 - a chat session runs --fix-clinician; v19459226 (chart 17478219) - CHP member number",
         "AET12 exclusion chart 24750 v19455937 PREF0288 - carrier record (standing hold)",
         "Neon: no connection string in this environment (NEON_DATABASE_URL absent, no 'neon database url' Gmail thread); AMD_PSW absent (credential file written from Gregg's thread via transcript)",
         "skills billing-easy-task / billing-hard-task / rejected / unpaid / stedi not loaded this run (read-only counts only - the standing prompt's column rules were not needed)"],
     "errors": []}
json.dump(d, open(R + S + ".json", "w"), indent=1); json.dump(d, open(R + "latest.json", "w"), indent=1)
print("report written:", d["headline"][:120])
