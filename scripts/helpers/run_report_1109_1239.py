#!/usr/bin/env python3
# PLAIN ENGLISH (report + board file of the 2026-11-09T1239Z columns run)
# Decides: nothing. Writes this run's needs_facesheet section, the run report CSV and board_updates_<stamp>.json
#   (board_ops.clean_file / plan_new_row) from the feed registers and the engine scan. Names only in the CSV and the board file
#   (William's channels); chart ids elsewhere.
import json, sys, csv, datetime, os
sys.path.insert(0, "/home/claude/unbilled"); sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-09T1239Z"; NOW = "2026-11-09T13:05:00Z"; WHEN = "11/9"; SRC = "7:39am ET 11/9 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
reg = json.load(open("registers/feed_import_20261109T1239Z.json"))["created"]
parsed = json.load(open("feed_parsed_20261109T1239Z.json"))
pm = {}
for m in parsed:
    pm.setdefault(m["name"], m)
match = json.load(open("feed_match_20261109T1239Z.json"))
name_of = {}
for k, v in match.items():
    if v.get("resolved"): name_of[v["resolved"].replace("pat", "")] = k.split("|")[0]
visits = {}
for r in reg:
    visits.setdefault(r["pid"].replace("pat", ""), []).append(r)
def dob(name):
    d = pm.get(name, {}).get("dob", "")
    return "%s/%s/%s" % (d[4:6], d[6:8], d[0:4]) if len(d) >= 8 else ""
def vis_txt(pid):
    return "; ".join("%s %s %s $%s" % (r["visit"].replace("vst", "v"), r["dos"], "+".join(r["cpts"]), "+".join(r["fees"])) for r in visits.get(pid, []))
def amt(pid): return round(sum(float(f) for r in visits.get(pid, []) for f in r["fees"]), 2)
FAC = "HCA FLORIDA CAPITAL HOSPITAL (feed fac29, admitted 11/06/2026)"
charts = {
 "17478347": dict(slug="[name]-17478347", car="HUM01 Humana (HumanaChoice MA)", ins="H71216570", insid="ins9521194",
                  disc="Stedi insurance discovery (FL): HUMANA member [member id] Active Coverage -> HUM01 car6285 plan added seq 1 (no group); AMD 271 ACTIVE (HumanaChoice)"),
 "17478348": dict(slug="atherton-susanna-17478348", car="UNI20 UnitedHealthcare (MA)", ins="134444982", insid="ins9521195",
                  disc="Stedi insurance discovery (FL): UNITEDHEALTHCARE member [member id] Active Coverage -> UNI20 car6404 plan added seq 1 (no group); AMD 271 ACTIVE (MBI pointer F6 on the 271, Optum Rx, dental rider)"),
 "17478349": dict(slug="addison-[first]-17478349", car="UMR (UHC TPA, commercial)", ins="50242529", insid="UMR plan (car303242) seq 1",
                  disc="Stedi insurance discovery (FL): UMR member [member id] Active Coverage planBegin 07/01/2026 (+ WellCare PDP 21534195 ended 04/30/2023) -> the feed verify step held (no UMR entry in its payer map); this run added UMR car303242 50242529 begin 07/01/2026 (no group), chart order 1, AMD 271 ACTIVE (GP, Bainbridge GA address), both visits insorder 1"),
 "17478350": dict(slug="dorrance-seton-17478350", car="SUN01 Sunshine State Health Plan (Medicaid MMA)", ins="UZ162141901", insid="ins9521196",
                  disc="Stedi insurance discovery (FL): SUNSHINE STATE HEALTH PLAN member [member id] Active Coverage -> SUN01 car6194 plan added seq 1 (no group); AMD 271 ACTIVE"),
}
# --- needs section
sec = ["", "## %s - 7:39 AM ET Mon 11/9/2026 backend billing run (ehpa cloud, six-hourly slot)" % STAMP,
       "- Columns 0/2/0/1 -> 0/2/0/1 (engine pass tools/button/run_all.py --mode live --profile columns --stedi-proxy 12:51-12:5xZ): Charge Review 0; Claim Inspector 2 = chart 22322 Pattern 4531 x2 (v19460343 / v19460347, coding call, $603) standing; Unbilled 0; Exclusions 1 = AET12 chart 24750 v19455937 PREF0288+PREF0264 ($315) standing hold.",
       "- FEED: gcs 22 objects, 1 new (20261109, 8.7 KB) -> 10 messages, 10 visits / $2,051 entered (99223 x4, 99232 x4, 99233 x1, 99316 x1), 4 new charts F261109-01..04 (charts 17478347 / 17478348 / 17478349 / 17478350), 3 plans added from discovery (HUM01, UNI20, SUN01), 0 already in AMD, 0 faults; inspector pass 0 flagged.",
       "- Feed holds worked: chart 17478349 (new) - discovery found UMR 50242529 ACTIVE from 7/1/2026; the verify helper had no UMR mapping -> UMR plan added by hand (feed_holds_1109_1239.py), AMD 271 ACTIVE, visits v19460539 (99223 11/6) + v19460546 (99232 11/7) insorder 1; mapping added to claimocity_verify.py. chart 17477946 (TRICARE East) - the 271 answered EB*I under 'Direct Care Plan 008' (read as 'no active plan'); TRI00 has paid every SNF visit since 9/28 -> v19460541 (99316 11/4, $207) kept on TRI00 insorder 1, nothing to fix.",
       "- ERA: 0 unposted checks / $0.00 before and after; nothing to upload; auto-posted $0; manual-posted 0; residuals $0; cleared 0; orphans 0; takebacks 0. Availity 5(g): no new PDF / Check-EFT export; Treasury nothing.",
       "- Sources: board drops 0, Working Denials queue 0, rows updated since 07:00Z 0; Drive watched folders nothing new since 06:30Z; Pam Gmail (2d): the 11/8 Huntley Jr thread only (worked earlier). Not an evening run.",
       "- Waiting on William (unchanged): coding call chart 22322 ($603); AET12 carrier master (chart 24750, $315); HCA facesheet chart 17478319 ($532); duplicate chart decision chart 17478345 ($141); Huntley Jr / Hawksworth admits chartless; chart 17477267 Medigap coinsurance waits on the crossover."]
open("needs_facesheet_list.md", "a").write("\n".join(sec) + "\n")
open("needs_facesheet_list_%s.md" % STAMP, "w").write("\n".join(sec) + "\n")
# --- CSV
rows = [["column", "status", "patient", "chart", "dos", "carrier", "error / item", "action"]]
rows.append(["claim inspector", "remaining", "(chart 22322)", "22322", "11/07/2026", "FLO02", "Pattern 4531 hospital E&M at non-hospital location x2 (v19460343, v19460347) $603", "coding call - William"])
rows.append(["exclusions", "remaining", "(chart 24750)", "24750", "", "AET12", "run 1700294 v19455937 PREF0288 INVALID PAYER ID/CPID + PREF0264 $315", "standing hold - carrier master (William)"])
for pid, c in charts.items():
    rows.append(["feed", "entered + insured", name_of.get(pid, ""), pid, "; ".join(r["dos"] for r in visits[pid]), c["car"], vis_txt(pid), c["disc"][:160]])
rows.append(["feed", "entered", name_of.get("17477946", "CHRISTENSEN, CHRISTA"), "17477946", "11/04/2026", "TRI00", vis_txt("17477946"), "TRICARE East paying since 9/28; 271 EB*I Direct Care read as hold - kept insorder 1"])
rows.append(["feed", "entered", "(chart 22322)", "22322", "11/07/2026", "FLO02", vis_txt("22322"), "traditional Medicare ACTIVE, released by the verify step"])
rows.append(["era", "none", "", "", "", "", "0 unposted checks $0.00 before and after", "nothing to post"])
csv.writer(open("_run report 11-09 0739.csv", "w", newline="")).writerows(rows)
# --- board file
items = []
cj = json.load(open("board_read_1239/items/christensen-christa-admit-0925.json"))
crow = dict(cj.get("data") or {}); crow["id"] = "christensen-christa-admit-0925"; items.append(crow)
ops = []
for pid, c in charts.items():
    nm = name_of.get(pid, "")
    row = {"id": c["slug"], "patient": nm, "dob": dob(nm), "facility": FAC, "amdid": pid, "mbi": "", "amount": amt(pid), "status": "claude",
           "inscarrier": c["car"], "insid": c["ins"], "insplans": "1st %s %s" % (c["car"], c["ins"]), "lastdos": visits[pid][-1]["dos"], "lastfac": "HCA Capital Hospital",
           "need": "None - entered and insured. Claimocity feed 11/9 (HCA admission 11/06/2026, no IN1 on the feed): %s. Visits %s - approved + inspected, insorder 1, leave on the next claim run." % (c["disc"], vis_txt(pid)),
           "why": "Claimocity feed 2026-11-09: new chart created by the ingest (F261109 series) with no insurance on the feed - Stedi discovery named the payer",
           "created": NOW,
           "notes": [{"who": "Claude", "text": "Created by the 7:39 AM ET 11/9 run - new HCA chart from the Claimocity feed, insured from Stedi discovery and AMD's 271; nothing for you here.", "at": NOW}],
           "checks": [{"ok": "ok", "src": "Stedi insurance discovery + AMD eligibility (free 271)", "result": c["disc"], "when": WHEN},
                      {"ok": "ok", "src": SRC, "result": "visits %s entered by the feed ingest (admission 11/06/2026 written), insorder 1" % vis_txt(pid), "when": WHEN}],
           "api": [{"src": "Stedi API - insurance discovery (FL)", "at": NOW, "text": c["disc"]}]}
    ops += plan_new_row(items, row, same_item=False, now=NOW)
ops.append({"op": "upsert", "collection": "items", "id": "christensen-christa-admit-0925", "append": {"checks": [{"ok": "ok", "src": SRC,
            "result": "11/4/2026 99316 (v19460541, $207) entered from the Claimocity feed, insorder 1 TRICARE East. TRI00 has paid every SNF visit since 9/28 (checks 0010047450ER7, 0010086437ER7, 0010151228ER7 - 99306+99497 9/28, 99309 10/4, 10/12, 10/19, 10/23, 10/27, 10/29); the 10/22 CCM 99487+99489 ($315, billed 10/28) is still unanswered. AMD 271 today: EB*I for STC 30 under 'PLAN 008 MILITARY HEALTH CARE SYSTEMS DIRECT CARE' (plan begin 11/01/2026) - a TRICARE Direct-Care benefit line, not a coverage denial; the verify step read it as 'no active plan' and held, nothing to fix.", "when": WHEN}]}})
ops.append({"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "append": {"checks": [{"ok": "na", "src": SRC,
            "result": "7:39 AM ET 11/9: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged.", "when": WHEN}]}})
ops.append({"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "append": {"checks": [{"ok": "na", "src": SRC,
            "result": "7:39 AM ET 11/9: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive watched folders nothing new since 06:30Z); no new 835 or facesheet; Working Denials queue 0; board drops 0; 0 rows changed since 07:00Z; Pam Gmail: the 11/8 Huntley Jr thread only (worked). Claimocity feed: 1 new file (20261109), 10 visits / $2,051 entered, 4 new charts insured from discovery (HUM01, UNI20, UMR, SUN01). ERA Center 0 checks $0.00 before and after (engine pass 12:51-12:55Z). Columns 0/2/0/1 -> 0/2/0/1 - every row a standing hold (chart 22322 Pattern 4531 x2, AET12 chart 24750).", "when": WHEN}]}})
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
doc = clean_file(doc)
json.dump(doc, open("board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [ (o["op"], o["id"]) for o in doc["ops"]])
print("csv rows", len(rows) - 1)
