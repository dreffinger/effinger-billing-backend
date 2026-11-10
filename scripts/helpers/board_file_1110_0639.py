# PLAIN ENGLISH (board inbox file for the 1:39 AM ET 11/10 columns run, fired 06:39Z): writes ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db, no approval). Decides nothing in AMD.
#   Ops: (1) Pam's two Centrepointe admit emails of 00:43Z / 01:04Z 11/10 (after the 00:39Z run started; that run left no digest):
#   orchard-bethan-17469476 is a NEW card (chart found by name + DOB, the chart's only plan = the sheet's Capital Health Plan
#   policy, AMD 271 ACTIVE; the chart's blank address line 1 filled from line 2 with addr_line1_fix - nothing else to change);
#   thorney-marcella-25994 gets a checks/notes append (Medicare A + BCBS Medigap on the sheet = the chart's two plans, both ACTIVE).
#   (2) standing append-only checks on availity-remits-backlog and aet12-carrier-cpid with this run's column/ERA numbers read from
#   the engine report reports/button/<stamp>-engine.json. Built through board_ops (plan_new_row, clean_file): no `updated`, no
#   status/need/why on rows William already owns. Never touches: AMD, the board DB, Drive (the upload is the connector's).
# Usage: python3 board_file_1110_0639.py  -> outbox/board_updates_2026-11-10T0639Z.json
import json, os, datetime
from board_ops import clean_file, plan_new_row
IDS = json.load(open("secrets/run_0639_ids.json"))   # PHI identifiers live here, never in the script
def fill(x):
    if isinstance(x, str):
        for k, v in IDS.items(): x = x.replace("{{%s}}" % k, v)
        return x
    if isinstance(x, list): return [fill(i) for i in x]
    if isinstance(x, dict): return {k: fill(v) for k, v in x.items()}
    return x
STAMP = "2026-11-10T0639Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/10"
SRC = "1:39am ET 11/10 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
rep = {}
p = "/home/claude/effinger-billing-backend/reports/button/%s-engine.json" % STAMP
if os.path.exists(p): rep = json.load(open(p))
s = rep.get("summary", {}); cb = s.get("columns", {}).get("before", {}); ca = s.get("columns", {}).get("after", {}); eb = s.get("era", {}).get("before", {}); ea = s.get("era", {}).get("after", {})
K = ("charge_review", "claim_inspector", "unbilled", "exclusions")
cols = "Columns %s -> %s" % ("/".join(str(cb.get(k, "?")) for k in K), "/".join(str(ca.get(k, "?")) for k in K))
era = "ERA Center %s checks $%.2f -> %s checks $%.2f" % (eb.get("checks", "?"), float(eb.get("unposted", 0) or 0), ea.get("checks", "?"), float(ea.get("unposted", 0) or 0))
ops = []
# (1a) Orchard - chart 17469476 found by name + DOB; no card exists on that chart (board query amdid==17469476 empty)
ops += plan_new_row([], {"id": "orchard-bethan-17469476", "patient": "ORCHARD,BETHAN C", "dob": "{{ORCHARD_DOB}}", "facility": "CENTRE POINTE HEALTH & REHAB (SNF) - admitted 11/09/2026 from Tallahassee Memorial Hospital",
    "amdid": "17469476", "mbi": "{{ORCHARD_MBI}}", "amount": 0, "status": "claude",
    "inscarrier": "CAP07 Capital Health Plan (Medicare Advantage)", "insid": "{{ORCHARD_POL}}",
    "insplans": "1st CAP07 Capital Health Plan {{ORCHARD_POL}} (since 01/17/2023, ACTIVE on AMD's 271) - the only plan; chart insorder 1",
    "need": "None - chart already right. Pam's 11/9 Centrepointe admission record (new admit 11/09/2026 from TMH): Insurance Name CHP, Primary Payer Capital Health Plans PDPM, policy {{ORCHARD_POL}}, Ins. Company Capital Health Plan, Second Payer 'Managed Care A Co-Ins Private', Medicaid # N, MBI {{ORCHARD_MBI}} printed. Per the facesheet Medicare rule (another insurer named alongside the Medicare #) CHP Medicare Advantage is the ONLY payer - the chart's one plan is that CHP policy and AMD's 271 answers ACTIVE (payer address [address] Midway - the sheet and chart say 87). The chart's address line 1 was BLANK with the street in line 2 (a PN3-0107 clearinghouse bounce waiting to happen): addr_line1_fix put {{ORCHARD_ADDR}} into line 1 (AMD refuses to blank line 2 afterwards, so line 2 repeats the street - cosmetic). No charges on the chart from this stay yet; the Centre Pointe visits bill CHP when the feed delivers them.",
    "why": "Pam admit email 11/10 00:43Z - 'New admit Centrepointe' (PCC admission record photo, admitted 11/09/2026 from Tallahassee Memorial Hospital); chart verified by name + DOB (lookuppatient ORCHARD,[first]% -> one chart, DOB {{ORCHARD_DOB}}).",
    "checks": [{"ok": "ok", "src": "AMD lookuppatient ORCHARD,[first]% + getdemographic 17469476", "when": WHEN, "result": "one chart, DOB {{ORCHARD_DOB}} = the sheet; one plan CAP07 {{ORCHARD_POL}} seq 1 (= the sheet's policy), insorder 1"},
               {"ok": "ok", "src": "AMD eligibility (free 271) - elig_amd 17469476 --all", "when": WHEN, "result": "CAP07 {{ORCHARD_POL}} ACTIVE (payer record address [address] MIDWAY FL 32343; sheet/chart [address])"},
               {"ok": "ok", "src": "AMD address PATCH (addr_line1_fix 17469476)", "when": WHEN, "result": "line 1 blank -> {{ORCHARD_ADDR}} (HTTP 200); the clear-line-2 step answered 500 as always, line 2 still repeats the street (cosmetic); readback confirmed"}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 1:39 AM ET 11/10 run from Pam's admit email. Chart verified against the record (CHP Medicare Advantage, ACTIVE) and the blank address line 1 filled - nothing for you here."}]}, now=NOW)
# (1b) Thorney - existing card, same work item (this chart's insurance / admits): append only
ops.append({"op": "upsert", "collection": "items", "id": "thorney-marcella-25994", "set": {}, "append": {
    "checks": [{"ok": "ok", "src": "Pam admit email 11/10 01:04Z (Centrepointe admission record, readmitted 11/07/2026 from TMH; most recent hospital stay 10/30-11/07/2026) + AMD 271", "when": WHEN,
                "result": "Facesheet: Primary Payer Medicare A, Medicare # {{THORNEY_MBI}} (= the chart's FLO02 member id), Insurance Name BCBS policy {{THORNEY_POL}} (= the chart's BCBS Medigap seq 2), Second Payer Medicare A Co-Ins Private, Third Payer Medicare A - Vaccines; DOB matches. AMD 271 tonight: Medicare ACTIVE (A 2/1/2007, B 7/1/2014, Part D BCBS Association only, no Advantage entity), Florida Blue ACTIVE 1/1/2025-open 'STANDARD SECONDARY'. Chart order 1,2 stands; address line 1 already filled 9/18. Nothing changed."}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Pam's 11/9 Centrepointe record for the 11/7 readmission (from TMH after a 10/30-11/07 hospital stay) matches the chart (Medicare + Florida Blue Medigap, both ACTIVE). Nothing needed from you here."}]}})
# (2) standing watch rows - append-only
wait = "; ".join(rep.get("waiting", [])[:4]) or "none listed"
ops.append({"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "1:39 AM ET 11/10: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new there after 19:00Z 11/9 outside the routines' own files); no new 835 or facesheet file (hca / tmh / PCC folders empty since 19:00Z); Claimocity feed 22 objects, 0 new (newest 20261109); Working Denials queue 0; board drops 0; rows William changed after he opened the board at 04:18Z: 0; Pam Gmail: two new Centrepointe admit emails 00:43Z / 01:04Z 11/10 worked (rows orchard-bethan-17469476, thorney-marcella-25994). %s. %s (engine pass). NOTE: the 00:39Z 11/9 evening run posted its START but left no RUN COMPLETE digest - its evening extras (precheck, 'current face sheets needed' email, Drive CSV) did not run. Waiting: %s" % (era, cols, wait)}]}})
ops.append({"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "1:39 AM ET 11/10: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]}})
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
doc = clean_file(fill(doc))
os.makedirs("outbox", exist_ok=True); out = "outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(out, "w"), indent=1); print("wrote", out, len(ops), "ops;", "engine report" if rep else "NO engine report yet")
