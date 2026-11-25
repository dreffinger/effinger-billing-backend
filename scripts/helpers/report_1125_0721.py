#!/usr/bin/env python3
# PLAIN ENGLISH (fold this run's by-hand work into the engine's report file, run 2026-11-25T0721Z)
# Decides: nothing. tools/button/run_all.py wrote reports/button/2026-11-25T0721Z.json for the steps it ran (columns, era, outstanding,
#   denials); this adds the steps the run did by hand - the feed, the board input (William's answers, the chat's 'next run' cards), the
#   cascade pre-check, packages, cred - with chart / visit / check ids and dollars only, re-totals posted / resent / written off, sets the
#   headline and the waiting list, and copies the file to latest.json. The privacy gate runs on both files after this (the prompt's order).
# Never touches: AMD, the board, Drive. Usage: python3 report_1125_0721.py
import json, datetime
S = "2026-11-25T0721Z"; P = "/home/claude/effinger-billing-backend/reports/button/%s.json" % S
d = json.load(open(P)); now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def step(name, title, status, summary, counts=None, dollars=None, lines=None, errors=None, started=None):
    return {"name": name, "title": title, "status": status, "summary": summary, "counts": counts or {}, "dollars": dollars or {}, "lines": lines or [], "errors": errors or [], "started": started or "2026-11-25T07:21:00Z", "ended": now}
feed = step("feed", "Claimocity feed ingest", "ok", "bucket 36 objects, 0 new (newest 20261124); ingest 'nothing new - done'; retry-dx nothing to retry (G0439 still not in the import tables); feed order sweep 20261125T072457Z: 0 checks bought, 0 saved, 2 not saved (v19458775 waits for the clinician move - chat; v19459226 - Medicare names another primary on 10/22/2026); feed registers + practice-db register committed to main; practice db 5 + 2 swept documents written; Neon: no connection string in this environment (NEON_DATABASE_URL absent, no 'neon database url' mail)",
            counts={"new_files": 0, "entered": 0, "sweep_saved": 0, "sweep_not_saved": 2}, started="2026-11-25T07:22:00Z")
board = step("board", "Insurance Refresh Board input", "ok",
             "0 drops, 0 denials commands; 13 cards worked (9 chat-filed 'next run' orders + 4 pastes of 07:18-07:26Z), 9 finished cards closed, 1 new card; board_updates_%s.json (24 ops, asof 07:33Z) uploaded, 0703Z file (applied) trashed; face-sheets email sent from facesheets_needed build (SYNC OK): 12 on William's turn $5,041.18" % S,
             counts={"cards_worked": 13, "closed": 9, "new_cards": 1, "handed_back": 5, "ops": 24, "william_turn": 12}, dollars={"william_turn": 5041.18},
             lines=[{"chart": "17476479", "what": "birth date corrected from William's sheet; Medicare identifies the chart (INACTIVE, date of death [DOB] recorded in the deceased cache; no charge after it); v19452652 coinsurance 44.09 re-routed to the Medigap plan seq 2 (204)"},
                    {"chart": "17473945", "what": "surname corrected from William's sheet; Medicare identifies the chart (INACTIVE, date of death [DOB] recorded; last charge 09/29/2025); 17.65 coinsurance waits on the AET12 carrier fix"},
                    {"chart": "17471061", "what": "sheet's Medicare number = chart's, still 72; charges 22477637 + 22477690 (04/07-04/08/2025): WOINS 35.17 each (contractual never posted), v19403439 + v19403500 re-routed 1,3 seq 3 to TRICARE For Life (204 x2); card closed (nothing open at Medicare)"},
                    {"chart": "17472491", "what": "v19461997 + v19462053 (11/19-11/20/2026, billed to Medicaid first) re-routed 3,4 seq 3 (204 x2); charge 23327550 (11/03/2025, $111, past 12 months) WOLATE; handed back - which Medicare contractor (First Coast ended 9/17, Railroad plan paying), HMO entity on the 271"},
                    {"chart": "17478413", "what": "v19461189: O24.419 removed from both charges (full-visit save), inspector clear, card done"},
                    {"chart": "44953", "what": "v19461125 v19461250 v19461227 v19461280 (Humana CO-16/M76): diagnosis list -> I10 alone, freq-7 with Humana claim numbers (204 x4), $640"},
                    {"chart": "17477353 / 48444 / 17472396", "what": "Humana 99489 modifier-25 step 1: WOINS taken back on charges 23372154 / 23371551 / 23371233 ($327), mcode7 removed (full-visit saves), freq-7 with Humana claim numbers (204 x3); card stays on Claude's turn for step 2"},
                    {"chart": "12182776 <- 20752", "what": "4 visits moved as originals: v19462413 (12/05/2025 99309), v19462414 (12/20/2025 99487+99489), v19462415 (01/12/2026 99309), v19462416 (01/27/2026 99487+99489) - $912, POS 32, insorder 1,2; old copies voided"},
                    {"chart": "20752", "what": "18 charges / $2,697 dated 06/06/2024+ voided (their $0 postings and WOINS lines first), read back void=1; 0 live charges dated 06/06/2024+ remain"},
                    {"chart": "17471238", "what": "v19462417 (11/09/2026 99309, $141) entered from the feed message, POS 31; G0439 of 11/10/2026 held (a G0439 of 07/10/2026 $204 is open) - decision card"},
                    {"chart": "17478219", "what": "CHP eligibility by name + DOB without member id: AAA 72 - handed back (CHP/CIO + 8-digit member number needed)"},
                    {"chart": "17477648", "what": "no SurgeryPlus / Employer Direct carrier in AMD (SUR 'SURGERY ONE' is another name) - handed back (carrier needed), nothing re-sent"},
                    {"chart": "feed charts x77", "what": "read-only duplicate audit: 1 new likely duplicate (17478216 ~ 17477499 / 21875, same birth date, $315 on the feed chart) -> new decision card; 17478345 and 17478434 known; register feed_duplicate_audit_%s.json" % S}],
             started="2026-11-25T07:33:00Z")
cascade = step("cascade", "Insurance cascade pre-check", "ok", "precheck --days 3 --max 120: 17 pairs, 0 new lookups, 0 flagged; void_rules: 1 open rule, 0 voids; Stedi 2026-11: 130 calls $54.40 at list (7 claim-status calls this run $2.10)", counts={"pairs": 17, "flagged": 0}, started="2026-11-25T08:00:00Z")
packages = step("packages", "Approval packages", "ok", "0 approved on the page, 0 approved / 0 waiting in the register; nothing refused this run, nothing submitted", counts={"applied": 0, "refused": 0, "skipped": 0, "submitted": 0})
cred = step("cred", "Credentialing check", "ok", "NPPES 3 records, 0 changed; LEIE 84,224 rows, 0 matches; reminders due none; no cred_updates file", counts={"nppes_changed": 0, "leie_matches": 0})
names = [s["name"] for s in d["steps"]]
d["steps"] = [feed, board] + [s for s in d["steps"] if s["name"] in ("columns", "era")] + [cascade, packages, cred] + [s for s in d["steps"] if s["name"] in ("outstanding", "denials")]
d["summary"]["posted"] = {"pay": 0.0, "woins": 70.34, "wocaid2nd": 0.0, "wolate": 111.0}
d["summary"]["resent"] = {"visits": 12, "dollars": 2334.84}   # 2 Scholey (30.82 secondary) + 2 Lawford (320) + 1 Mabry (44.09) + 4 Orwell (640) + 3 Humana (327 of 945 visits re-sent freq 7) + the 4 Castellane originals go out on the claim run (912)
d["summary"]["written_off"] = {"count": 3, "dollars": 181.34}
d["summary"]["voided"] = {"charges": 18, "dollars": 2697.0}
d["summary"]["board"] = {"william_turn": 12, "william_turn_dollars": 5041.18}
d["summary"]["packages"] = {"applied": 0, "refused": 0, "skipped": 0}
d["headline"] = "Columns 0/1/0/1 -> 0/0/0/1 (engine pass 0/5/0/1 -> 0/0/0/1); ERA 0 checks $0.00 -> 0; posted WOINS $70.34 + WOLATE $111; 13 board cards worked - 4 Castellane visits moved + 18 voided, 7 Humana freq-7 resends, Garland-G 99309 entered; 12 on William's turn $5,041.18"
d["waiting"] = [
    "TRAP (this run): the deceased guard's default cache path from the workspace is /home/claude/practices/ehpa/registers/deceased_cache.json - no bootstrap writes there, and deceased_cache_local.json held 1 entry; both merged from the workspace register this run (374 charts, 43 dated) - bootstrap_workspace.sh layout should do it",
    "Working Denials board inbox: denials_updates_2026-10-14T1710Z.json and 2026-10-16T1310Z.json still waiting (42 days; that board's registry has applied nothing since 10/23)",
    "chart 17478013: VA CCN authorization effective after the first admission - William's word (card on his turn, $1,430)",
    "charts 48458, 17471791, 17471643: new Medicare card needed (the sheets carry the chart's rejected number) - $396.59",
    "chart 17478219: Capital Health Plan member number (CHP/CIO + 8 digits) - $639",
    "chart 17473460: photo of the Medicare card (name mismatch 73) - $690.59; chart 17477168 name mismatch $310; chart 17476865 birth-date mismatch $315 - face sheets",
    "chart 17471238: enter the second wellness visit G0439 on 11/10/2026? (one of 07/10/2026 is open) - $204",
    "chart 17472491: which Medicare contractor pays her (First Coast plan end-dated 9/17/2026 vs Railroad plan paying; HMO entity on the 271); $111 of 11/03/2025 written off untimely - 'send to Railroad' reverses it",
    "chart 17477648: SurgeryPlus (Employer Direct Healthcare) carrier needed in Master Files before the three 9/2026 visits ($630) can be sent",
    "chart 17478216 ~ 17477499 / 21875: same person? (feed-made duplicate, $315) - decision card",
    "Humana 99489 modifier-25 step 2 waits on Humana's answer to the three freq-7 resends (chart 17477353 v19459605, 48444 v19459146, 17472396 v19458952)",
    "Neon: no connection string in this environment (NEON_DATABASE_URL absent; no 'neon database url' Gmail thread) - load-writes not done; AMD_PSW absent too (credential file written from Gregg's thread)",
    "feed: v19458775 (chart 17472729) waits for the clinician move to prof15 - a chat session runs --fix-clinician; v19459226 (chart 17478219) - CHP member number",
    "AET12 exclusion chart 24750 v19455937 PREF0288 - carrier record (standing hold)"]
d["ended"] = now
json.dump(d, open(P, "w"), indent=1); json.dump(d, open("/home/claude/effinger-billing-backend/reports/button/latest.json", "w"), indent=1)
print("report updated:", d["headline"])
