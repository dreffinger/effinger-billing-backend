# PLAIN ENGLISH (board inbox file for the 7:39 PM ET 11/11 evening columns run, fired 00:39Z 11/12): writes ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db, no approval). Decides nothing in AMD. Ops: NEW cards on William's turn for
#   the fifteen Claimocity feed charts the feed-order sweep has listed 'for William' since 10/28 and that had NO board card yet - ten charts
#   with zero insurance plans (the sweep's 'NO CLAIM CAN BE MADE ... 0 open medical plans' lines; MBI lookup / discovery / facesheet folders
#   empty on 10/28) and five charts whose dated eligibility check named a payer the chart does not carry (Cigna id invalid; Medicare names CHP /
#   Humana / Florida Blue as primary; a plan whose own dates do not cover the DOS) - with this run's Stedi discovery answers in the trail;
#   append-only checks on the standing watch rows (availity-remits-backlog, aet12-carrier-cpid) with this run's column / ERA numbers.
#   Names and DOBs come from secrets/run_0039_ids.json (never in this source - PHI gate 11/11). Built through board_ops.clean_file / plan_new_row.
# Usage: cd /home/claude/unbilled && python3 board_file_1112_0039.py -> outbox/board_updates_2026-11-12T0039Z.json
import json, os, datetime
from board_ops import clean_file, plan_new_row
ids = json.load(open("secrets/run_0039_ids.json"))
STAMP = "2026-11-12T0039Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/11"
SRC = "7:39pm ET 11/11 columns run (ehpa cloud, evening slot) - run %s" % STAMP
rp = "/home/claude/effinger-billing-backend/reports/button/%s-engine.json" % STAMP
cols = era = "engine report not written"
if os.path.exists(rp):
    s = json.load(open(rp))["summary"]; cb = s["columns"]["before"]; ca = s["columns"]["after"]; eb = s["era"]["before"]; ea = s["era"]["after"]
    cols = ("Columns %s/%s/%s/%s -> %s/%s/%s/%s" % (cb.get("charge_review"), cb.get("claim_inspector"), cb.get("unbilled"), cb.get("exclusions"), ca.get("charge_review"), ca.get("claim_inspector"), ca.get("unbilled"), ca.get("exclusions"))) if cb else "Columns 0/2/0/1 -> 0/0/0/1 by hand (the engine's columns_scan read-timed out on getclaimexclusioncharges - AMD slow at 00:48Z; its ERA / outstanding / denials steps ran): Claim Inspector 2 -> 0 (chart 17478349 UMR, two source-of-payment advisories bypassed by error id), Exclusions 1 (AET12 hold), Charge Review 0, Unbilled 0"
    era = "ERA Center %s checks $%.2f -> %s checks $%.2f" % (eb.get("checks"), float(eb.get("unposted") or 0), ea.get("checks"), float(ea.get("unposted") or 0))
extra = json.load(open("secrets/run_0039_extra.json")) if os.path.exists("secrets/run_0039_extra.json") else {}
items = []   # inline board read this run: no card on any of these fifteen charts (amdid 'in' query answered none)
ops = []
def slug(pid):
    n = ids[pid]["name"].split(",")[0].split()[0].lower().replace("'", ""); f = ids[pid]["name"].split(",")[1].split()[0].lower().strip("()") if "," in ids[pid]["name"] else "x"
    return "%s-%s-%s" % (n, f, pid)
# --- ten zero-plan charts (HCA F1028 backlog, two ALF CCM charts, one SNF initial visit)
ZERO = {
 "17478200": ("HCA Florida Capital Hospital (admitted 10/14/2026)", 421, "99223 10/14/2026 $310 (v19459188) + 99232 10/15/2026 $111 (v19459194)"),
 "17478201": ("HCA Florida Capital Hospital (admitted 10/14/2026)", 421, "99223 10/14/2026 $310 (v19459189) + 99232 10/15/2026 $111 (v19459192)"),
 "17478203": ("HCA Florida Capital Hospital (admitted 10/13/2026)", 111, "99232 10/15/2026 $111 (v19459191)"),
 "17478205": ("HCA Florida Capital Hospital (admission read as 10/19/2026 - after three of the visits; confirm)", 901, "99223 10/16 $310 (v19459197), 99233 10/17 $160 (v19459200), 99233 10/18 $160 (v19459198), 99233 10/19 $160 (v19459202), 99232 10/20 $111 (v19459206)"),
 "17478212": ("HCA Florida Capital Hospital (admitted 10/20/2026)", 421, "99223 10/20/2026 $310 (v19459215) + 99232 10/21/2026 $111 (v19459217)"),
 "17478214": ("HCA Florida Capital Hospital (admitted 10/21/2026)", 643, "99223 10/21 $310 (v19459220), 99232 10/22 $111 (v19459235), 99232 10/23 $111 (v19459246), 99232 10/24 $111 (v19459241)"),
 "17478215": ("HCA Florida Capital Hospital (admitted 10/21/2026)", 421, "99223 10/21/2026 $310 (v19459221) + 99232 10/22/2026 $111 (v19459234)"),
 "17478216": ("Tapestry Lakeshore ALF (CCM)", 315, "99487+99489 10/22/2026 $315 (v19459222)"),
 "17478221": ("Brookdale Hermitage ALF (CCM)", 315, "99487+99489 10/22/2026 $315 (v19459228)"),
 "17478228": ("Centre Pointe Health and Rehab (SNF initial visit; feed names the NP, entered under the NP - William confirms who saw the patient)", 389, "99306+99497 10/20/2026 $389 (v19459258)"),
}
for pid, (fac, amt, visits) in ZERO.items():
    d = ids[pid]
    row = {"id": slug(pid), "patient": d["name"], "dob": d["dob"], "facility": fac, "amdid": pid, "mbi": "", "inscarrier": "", "insid": "", "insplans": "none - 0 insurance plans on the chart", "amount": amt, "status": "william",
           "why": "Claimocity feed chart (10/28 backlog import, %s): the feed carried no insurance, the chart has 0 insurance plans, so the visits have no insurance order - AdvancedMD makes no claim for them and shows them on no work list (the feed-order sweep lists them 'NO CLAIM CAN BE MADE' every run since 11/10)" % d.get("chart", ""),
           "need": "FACESHEET OR CARD NEEDED ($%s): %s. Every automated source is empty - 10/28 chat pass: AMD has no plan to check, Stedi MBI lookup (no SSN on the chart) and insurance discovery found nothing; no facesheet for this name in bht hca / tmh / PCC facesheets, Pam's admit emails or the board drops since. Drop the %s facesheet (or the insurance card) and the next run adds the plan, sets the insurance order and sends the claims." % (amt, visits, "HCA" if "HCA" in fac else "facility"),
           "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 7:39 PM ET 11/11 evening run. These visits have been sitting with no payer since the 10/28 feed import - nothing automated can name one. A facesheet or card photo settles it."}],
           "checks": [{"ok": "no", "src": "10/28 chat pass (Claimocity backlog import) - AMD 271 / Stedi MBI lookup / Stedi insurance discovery", "when": "10/28", "result": "no plan on the chart to check; MBI lookup and insurance discovery found nothing"},
                      {"ok": "no", "src": "Drive bht hca / tmh / PCC facesheet folders, Pam Gmail (2 days), board drops - every run since", "when": WHEN, "result": "nothing for this name"},
                      {"ok": "human", "src": "William", "when": WHEN, "result": "facesheet or insurance card needed - %s" % visits}]}
    r = plan_new_row(items, row, same_item=False, now=NOW); ops.extend(r if isinstance(r, list) else [r])
# --- five charts whose dated eligibility check named another payer (round-7 sweep: for a person)
COV = {
 "17478204": ("HCA Florida Capital Hospital (admitted 10/14/2026)", 111, "99232 10/15/2026 $111 (v19459195)", "CIG09 Cigna (seq 1) - the only plan",
              "CIGNA MEDICAL MEMBER ID NEEDED ($111): the chart's only plan is Cigna (CIG09, seq 1) and Cigna's eligibility check dated to the 10/15/2026 service date answers AAA 72 'Invalid/Missing Subscriber/Insured ID'. Stedi insurance discovery tonight found only a CIGNA DENTAL HMO (active since 9/1/2025, member [member id]) - no medical plan. The HCA facesheet (or the medical card) with the medical member id, or the real payer, lets the next run fix the plan and send the claim.",
              [{"ok": "no", "src": "Stedi eligibility Cigna 62308 dated to DOS 10/15/2026 (feed order sweep 11/11)", "when": WHEN, "result": "AAA 72 Invalid/Missing Subscriber/Insured ID"},
               {"ok": "no", "src": "Stedi insurance discovery (FL, DOS 10/15/2026) - this run", "when": WHEN, "result": "coveragesFound 1: CIGNA Dental Health Inc, Dental HMO, Active Coverage since 20250901, member [member id] - dental only, no medical payer"}]),
 "17478219": ("Brookdale Hermitage ALF (CCM 10/22/2026; home visit 9/01/2026)", 639, "99487 10/22/2026 $206 (v19459226) + 99344+99497 09/01/2026 $433 (v19459521)", "FLO02 Florida Medicare (seq 1) - the only plan",
              "CAPITAL HEALTH PLAN MEMBER ID NEEDED ($639): the chart carries Medicare alone, but Medicare's eligibility check dated to 10/22/2026 says ANOTHER PRIMARY PAYER is on file for that date: CAPITAL HEALTH PLAN. Stedi insurance discovery tonight confirms Medicare active (MBI on the CMS record) with a long-inactive WellCare plan and NO CHP record it can name - CHP's own eligibility needs the member id. The CHP card (or facesheet) with the member id, or your word that Medicare is right, lets the next run add CHP first and send both visits.",
              [{"ok": "no", "src": "Stedi Medicare eligibility dated to DOS 10/22/2026 (feed order sweep 11/11)", "when": WHEN, "result": "Medicare names another primary payer on 10/22/2026: CAPITAL HEALTH PLAN"},
               {"ok": "na", "src": "Stedi insurance discovery (FL, DOS 10/22/2026) - this run", "when": WHEN, "result": "coveragesFound 2: CMS Active Coverage (MBI on record); WELLCARE Dividend HMO-POS H5698-199 Inactive (plan 12/01/2016 only) - no CHP member id discoverable"}]),
 "17478260": ("HCA Florida Capital Hospital (admitted 10/27/2026)", 421, "99223 10/27/2026 $310 (v19459636) + 99232 10/28/2026 $111 (v19459589)", "FLO02 Florida Medicare (seq 1) - the only plan",
              "HUMANA MEMBER ID NEEDED ($421): the chart carries Medicare alone, but Medicare's eligibility checks dated to 10/27 and 10/28/2026 say ANOTHER PRIMARY PAYER is on file: HUMANA INSURANCE COMPANY (a Humana Medicare Advantage plan). Stedi insurance discovery tonight: CMS active (MBI on record) and an inactive 2024 WellCare Part D - no Humana member id it can name. The HCA facesheet or Humana card lets the next run add HUM01 first and send both visits.",
              [{"ok": "no", "src": "Stedi Medicare eligibility dated to DOS 10/27 and 10/28/2026 (feed order sweep 11/11)", "when": WHEN, "result": "Medicare names another primary payer: HUMANA INSURANCE COMPANY"},
               {"ok": "na", "src": "Stedi insurance discovery (FL, DOS 10/27/2026) - this run", "when": WHEN, "result": "coveragesFound 2: CMS Active Coverage (MBI on record); WELLCARE Value Script PDP S4802145 Inactive (02/2024) - no Humana member id discoverable"}]),
 "17478332": ("Sodalis ALF (home visit 11/03/2026)", 433, "99344+99497 11/03/2026 $433 (v19460350)", "FLO02 Florida Medicare (seq 1) - the only plan",
              "FLORIDA BLUE MEMBER ID NEEDED ($433): the chart carries Medicare alone, but Medicare's eligibility check dated to 11/03/2026 says ANOTHER PRIMARY PAYER is on file: BLUE CROSS AND BLUE SHIELD OF FLORIDA (a Florida Blue Medicare plan). Stedi insurance discovery tonight: CMS active (MBI on record) and two INACTIVE UnitedHealthcare records (member [member id]) - no Florida Blue member id it can name. The Florida Blue card (or facesheet) lets the next run add BCBS first and send the visit.",
              [{"ok": "no", "src": "Stedi Medicare eligibility dated to DOS 11/03/2026 (feed order sweep 11/11)", "when": WHEN, "result": "Medicare names another primary payer on 11/03/2026: BLUE CROSS AND BLUE SHIELD OF FLORIDA, INC."},
               {"ok": "na", "src": "Stedi insurance discovery (FL, DOS 11/03/2026) - this run", "when": WHEN, "result": "coveragesFound 3: CMS Active Coverage (MBI on record); UNITEDHEALTHCARE 25463 and 87726 member [member id] both Inactive - no Florida Blue member id discoverable"}]),
 "17478224": ("Brookdale Hermitage ALF (CCM 10/22/2026)", 315, "99487+99489 10/22/2026 $315 (v19459239)", "FLO02 Florida Medicare (seq 1) - the only plan",
              "CONFIRM THE PAYER ($315): Medicare's eligibility check dated to the 10/22/2026 service date answers Active Coverage but with plan dates '10/22/2026 to 10/08/2026' - an end date before the begin date - so the sweep could not take it as proof of coverage and holds the visit (round 7: an answer that does not clear by waiting is for a person). Say 'Medicare is right' and the next run sets the insurance order and sends the CCM; or name the other payer.",
              [{"ok": "na", "src": "Stedi Medicare eligibility dated to DOS 10/22/2026 (feed order sweep 11/11)", "when": WHEN, "result": "Active Coverage; the plan's own dates (10/22/2026 to 10/08/2026) do not cover 10/22/2026"}]),
}
for pid, (fac, amt, visits, plans, need, checks) in COV.items():
    d = ids[pid]
    row = {"id": slug(pid), "patient": d["name"], "dob": d["dob"], "facility": fac, "amdid": pid, "mbi": "", "inscarrier": plans.split(" (")[0], "insid": "", "insplans": plans, "amount": amt, "status": "william",
           "why": "Claimocity feed chart (%s): the visits have no insurance order; the feed-order sweep's eligibility check dated to the service date (round 7, William 11/10) answered something a routine may not decide" % d.get("chart", ""),
           "need": need, "checks": checks + [{"ok": "human", "src": "William", "when": WHEN, "result": "card / facesheet or your word - " + visits}],
           "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 7:39 PM ET 11/11 evening run. The dated eligibility check does not match the chart's plan and the rulebook leaves that to you; the trail above has everything the lookups found."}]}
    r = plan_new_row(items, row, same_item=False, now=NOW); ops.extend(r if isinstance(r, list) else [r])
# --- standing watch rows
ops.append({"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "7:39 PM ET 11/11 (evening slot): no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there since 10/15); no new 835 or facesheet file (Drive watched folders: only the 19:45Z SHARED_LESSONS copies); Claimocity feed 24 objects, 0 new (newest 20261111); Working Denials queue 0; board drops 0; Claude-turn rows changed since 18:30Z: 0; Pam Gmail: nothing newer than the 17:49Z 11/11 Westminster Oaks admit (worked 1839Z). %s; %s (engine pass). Evening extras: pre-claim check not started here (11/10 rule - the nightly cascade owns it); 'current face sheets needed' email sent (15 feed charts - new cards tonight, see them). %s" % (era, cols, extra.get("watch_tail", ""))}]}})
ops.append({"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "7:39 PM ET 11/11: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]}})
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
doc = clean_file(doc)
os.makedirs("outbox", exist_ok=True)
out = "outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(out, "w"), indent=1)
print(out, len(doc["ops"]), "ops;", sum(1 for o in doc["ops"] if o.get("set", {}).get("status") == "william"), "new cards on William's turn")
