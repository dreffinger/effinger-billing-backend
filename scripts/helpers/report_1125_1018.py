#!/usr/bin/env python3
# PLAIN ENGLISH (write the button-run/1 report file for the 11/25/2026 09:03Z press - run 2026-11-25T1018Z, mode live, steps columns + cascade)
# Decides: nothing. Chart / visit / check ids and dollars only; the privacy gate runs on both copies after this.
# Never touches: AMD, the board, Drive. Usage: python3 report_1125_1018.py
import json, datetime
S = "2026-11-25T1018Z"; R = "/home/claude/effinger-billing-backend/reports/button/"
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def step(name, title, status, summary, counts=None, dollars=None, lines=None, errors=None, started=None, ended=None):
    return {"name": name, "title": title, "status": status, "summary": summary, "counts": counts or {}, "dollars": dollars or {},
            "lines": lines or [], "errors": errors or [], "started": started or "2026-11-25T10:18:00Z", "ended": ended or now}
out = json.load(open("/home/claude/unbilled/outstanding_claims.json"))
steps = [
    step("feed", "Claimocity feed ingest", "skipped",
         "FEED NOT IMPORTED THIS RUN: another run's ingest (2026-11-25T0900Z) was running since 0901Z (RUNNING refreshed 0931Z, 0959Z, 1026Z: import done 320 visits, verify 287/306 at 10:25Z; its feed registers reached main 10:36Z, e7f5e31) - no ingest, no retry here; feed order sweep 20261125T101911Z (live): 25 visits read, 0 checks bought, 0 saved, 2 not saved (v19458775 chart 17472729 clinician move - chat; v19459226 chart 17478219 - CHP member number); no intake (no file downloaded by this run)",
         counts={"new_files": 0, "entered": 0, "sweep_saved": 0, "sweep_not_saved": 2}, started="2026-11-25T10:19:00Z"),
    step("board", "Insurance Refresh Board input", "ok",
         "the six cards William answered 08:19-08:26Z (his note 'all the insurance boards are done, file all those through and bill them all'), each read live first: 5 settled (done), 1 kept on Claude's turn (watching Medicare's answer); 0 drops, 0 denials commands; board_updates_%s.json (6 ops, asof 10:35Z) -> board inbox; face-sheets email sent from facesheets_needed build (SYNC OK): 2 on William's turn $412" % S,
         counts={"cards_worked": 6, "closed": 5, "kept": 1, "new_cards": 0, "handed_back": 0, "ops": 6, "william_turn": 2}, dollars={"william_turn": 412.0},
         lines=[{"chart": "17477648", "what": "SurgeryPlus carrier (car307813, paper) found; plan ***8050 begin 08/25/2026 added (ins9521413 seq 2), chart order 2; v19453782 $310 + v19453773 $160 + v19453753 $160 re-routed and re-set as originals (204 x3)"},
                {"chart": "17478216 -> 17477499", "what": "duplicate feed chart: v19459222 (10/22/2026 99487+99489 $315) -> v19462739 and v19462420 (11/24/2026 99487 $206, entered by the 0900Z ingest) -> v19462740 moved whole, feed-chart copies voided; patient map 6a89477a... -> 17477499 on main (421cb89 / bad57e2)"},
                {"chart": "17471238", "what": "11/10/2026 99309 $141 entered as v19462738 (charge 23376065, POS 31, order 2,4,3) - 'bill the second as a 99309'"},
                {"chart": "17472491", "what": "'send to railroad': WOLATE 22509876 (-111.00) + $0 marker 24674822 voided; v19422192 re-pointed 3,2,4 and re-set as an original to seq 3 (204); tf_writeoff_watch item railroad-17472491-2025 (c4e2d9b)"},
                {"chart": "17471643", "what": "v19428155 + v19428346 (01/05-01/06/2026 99233, $218, before the 03/09/2026 death) re-sent ONCE with GV (mcode713), frequency 1 -> 204 x2; card stays on Claude's turn for Medicare's answer, then the write-off on William's word"},
                {"chart": "48458 (+17469674, 17472573)", "what": "Medicare look-up with the SSN: the chart's number is valid; hospice spans 06/04-09/01, 09/02-11/30, 12/01-12/24/2025; date of death [DOB] (deceased cache). v19422680 (11/03/2025 99308 $107) re-sent with GV -> 204, timely advisory 20657 bypassed; v19427558 (12/28/2025 99487+99489 $315, after the death) VOIDED after its WOINS + $0 postings; the other two charts hold nothing after the death and nothing to send"}],
         started="2026-11-25T10:20:00Z"),
    step("columns", "Claims Center columns", "ok",
         "Charge Review 0 -> 0; Claim Inspector 87 -> 0 (the 0900Z run's CCM batch, cleared by that run's inspector pass while this run worked the cards; this run bypassed one 20657 timely advisory on v19422680); Unbilled 0 -> 0; Exclusions 1 -> 1 (AET12 chart 24750 v19455937 PREF0288 carrier CPID, standing hold)",
         counts={"before": {"charge_review": 0, "claim_inspector": 87, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 0, "unbilled": 0, "exclusions": 1}},
         started="2026-11-25T10:19:00Z", ended="2026-11-25T10:37:00Z"),
    step("era", "ERA posting", "skipped", "not in this press's steps (columns, cascade); 1 unposted check $230.53 (UNI20 W378708629, ERA 1053641, 2 visits postable) still waits for a run with the ERA step",
         counts={"before": {"checks": 1, "unposted": 230.53}, "after": {"checks": 1, "unposted": 230.53}}),
    step("cascade", "Insurance cascade pre-check", "ok", "precheck --days 3 --max 120 (10:05Z this session): 17 pairs, 0 new lookups, 0 flagged; void_rules: 1 open rule, 0 voids; Stedi 2026-11: 123 calls $52.30 at list (1 MBI look-up with SSN this run, $1.00)",
         counts={"pairs": 17, "flagged": 0, "stedi_calls_this_run": 1}, dollars={"stedi": 1.0}),
    step("packages", "Approval packages", "ok", "brief: packages none; page 0 approved; nothing refused, nothing submitted", counts={"applied": 0, "refused": 0, "skipped": 0, "submitted": 0}),
    step("outstanding", "Outstanding claims", "ok", "not refreshed this run (steps columns, cascade); reports/button/outstanding_latest.json from 10:06Z this session: %s visits / %s charts / $%s" % (out.get("visits"), out.get("charts"), out.get("total"))),
    step("denials", "Working denials refresh", "ok", "not refreshed this run; reports/button/working_denials_latest.json from 10:1xZ this session (52 actionable $9,755)"),
]
d = {"schema": "button-run/1", "stamp": S, "mode": "live", "status": "ok",
     "headline": "Six board cards worked on William's word: SurgeryPlus plan + 3 visits re-sent ($630), duplicate feed chart's 2 CCM visits moved to the proper chart ($521), a 99309 entered ($141), Lawford $111 to Railroad Medicare, 3 hospice GV re-sends ($325), 2 after-death charges voided ($315). Columns CR/CI/Unb/Exc 0/87/0/1 -> 0/0/0/1; ERA not in this press's steps (1 check $230.53 waits); 2 cards on William's turn $412",
     "note": "BUTTON PRESS 2026-11-25T09:03:30Z · mode: live · steps: columns, cascade · packages: none · note: William answered the last cards on his turn ... 'all the insurance boards are done, file all those through and bill them all' - work exactly these six cards. Worked from 10:18Z in the 0902Z session (the 0900Z run's START was older than 40 minutes; its ingest held the feed).",
     "run_url": "https://claude.ai/code/session_01HHfWREPgND3R3HApTU5F13", "started": "2026-11-25T10:18:00Z", "ended": now,
     "engine": "claude", "trigger": "trig_01S771Si8VJ8DvcwgHMHGYB5",
     "summary": {"columns": {"before": {"charge_review": 0, "claim_inspector": 87, "unbilled": 0, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 0, "unbilled": 0, "exclusions": 1}},
                 "era": {"before": {"checks": 1, "unposted": 230.53}, "after": {"checks": 1, "unposted": 230.53}},
                 "posted": {"pay": 0.0, "woins": 0.0, "wocaid2nd": 0.0, "wolate": -111.0},
                 "resent": {"visits": 9, "dollars": 1587.0},   # Prescot 3 (630) + Lawford 1 (111) + Do 2 (218) + Danvers 1 (107) + Shinwell 2 recreated as originals (521)
                 "written_off": {"count": 0, "dollars": 0.0}, "voided": {"charges": 5, "dollars": 836.0}, "entered": {"visits": 1, "dollars": 141.0},
                 "board": {"william_turn": 2, "william_turn_dollars": 412.0}, "packages": {"applied": 0, "refused": 0, "skipped": 0},
                 "outstanding": {"total": out.get("total"), "visits": out.get("visits"), "charts": out.get("charts"), "over_365": out.get("over_365")}},
     "steps": steps, "packages": [],
     "waiting": [
         "ERA 1053641 UHC W378708629 $230.53 (2 visits, postable) unposted - neither the 0900Z press (columns + cascade) nor this one (same steps) carries the ERA step; the next run with ERA (6-hourly backend ~12:39Z or a full press) posts it",
         "chart 17471643: Medicare's answer to the two GV re-sends ($218) - then the write-off of what it does not pay, on William's word (card on Claude's turn)",
         "chart 17472491 v19422192 $111 at Railroad Medicare (tf watch railroad-17472491-2025): paid -> posted; CARC 29 -> written off again",
         "chart 17478216: nothing live left - inactivating / merging the duplicate chart is William's (also 48458 / 17469674 / 17472573, one person, and 17477499 / 21875)",
         "the 0900Z press run (columns + cascade) still working at 10:37Z; its board step reads the same six cards (09:01Z read) - every helper this run used refuses a second application (plan present, GV present, visit present, source voided)",
         "Working Denials board inbox: denials_updates_2026-10-14T1710Z.json and 2026-10-16T1310Z.json still waiting (42 days)",
         "feed: v19458775 (chart 17472729) clinician move - chat; v19459226 (chart 17478219) - CHP member number",
         "AET12 exclusion chart 24750 v19455937 PREF0288 - carrier record (standing hold)"],
     "errors": ["lawford_railroad_1018.py: the first chargerebill to seq 3 answered HTTP 500 (the visit order was still 1,2); the re-route freq1_visit.py reroute 19422192 23327550 3,2,4 3 then answered 204 - no fault left"]}
json.dump(d, open(R + S + ".json", "w"), indent=1); json.dump(d, open(R + "latest.json", "w"), indent=1)
print("report written:", d["headline"][:100])
