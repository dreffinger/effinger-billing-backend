# PLAIN ENGLISH (one-off, nightly cascade 2026-11-15T0535Z): builds board_updates_2026-11-15T0535Z.json for the Insurance
# Refresh Board from tonight's results. Names/DOBs come from the inline board read saved locally (board_items_1115.json, git-ignored);
# this file holds chart and visit ids only. Never touches AMD or the board itself.
import json, sys
sys.path.insert(0, "/home/claude/unbilled")
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-15T0535Z"; NOW = "2026-11-15T05:55:00Z"; WHEN = "11/15"
items = json.load(open("/home/claude/unbilled/board_items_1115.json"))
byid = {r["id"]: r for r in items}
ops = []
mb = [r for r in items if r["amdid"] == "17473090"][0]["id"]
ops.append({"op": "upsert", "collection": "items", "id": mb, "set": {"lastdos": "11/12/2026"}, "append": {
    "checks": [
        {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/12/2026: HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101) - the 11/08, 11/09 and 11/12 hospital visits (99233 x3) were still at insorder 2,1 (Medicare first)", "src": "Stedi Medicare answer (pre-claim check, cached, MBI on chart)", "when": WHEN},
        {"ok": "ok", "result": "primary dx R55 acceptable on all three - no change", "src": "dx_primary_fix --dry visits 19460675, 19461075, 19461183", "when": WHEN},
        {"ok": "ok", "result": "v19460675 11/08, v19461075 11/09, v19461183 11/12/2026 (99233, 160 each) -> insorder 1 (BCBS), frequency 1, chargerebill seq 1 -> 204 x3 (480 dollars)", "src": "AMD action: freq1_visit reroute <visit> <charge> 1 1", "when": WHEN}],
    "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": NOW,
             "text": "DOS 20261112 ADVANTAGE PLAN on DOS: HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)\nchart plans: seq1 car6062 BCBS ACTIVE (271 11/14) | seq2 car6085 FLO02 ACTIVE\nreroute: vst19460675 2,1 -> 1 204 | vst19461075 2,1 -> 1 204 | vst19461183 2,1 -> 1 204"}],
    "notes": [{"who": "Claude", "at": NOW, "text": "11/15 nightly: three more hospital visits (11/08, 11/09, 11/12, 480 dollars) had come in pointed at Medicare; all three now at the BCBS (HCSC Medicare Advantage) plan as original claims. Nothing for you here - the feed keeps entering her hospital visits Medicare-first."}]}})
col = [r for r in items if r["amdid"] == "17478395"][0]["id"]
ops.append({"op": "upsert", "collection": "items", "id": col, "append": {
    "checks": [{"ok": "no", "result": "still ADVANTAGE PLAN on DOS 11/12/2026: CAPITAL HEALTH PLAN (cached answer, no new lookup); chart still Medicare only - no CHP member number yet", "src": "Stedi pre-claim check (cached)", "when": WHEN}]}})
cam = [r for r in items if r["amdid"] == "17476912"][0]["id"]
ops.append({"op": "upsert", "collection": "items", "id": cam, "append": {
    "checks": [{"ok": "no", "result": "v19445941 6/22/2026 389 dollars: FINALIZED 0 dollars, exact-date answer, WellCare check 1003519162 paid date 7/9/2026, payer claim 3852429138; Working Denials lists CARC 252 (attachment / documentation required)", "src": "Stedi 277 WellCare (14163) claim status, exact date of service", "when": WHEN},
               {"ok": "no", "result": "WEL04 INACTIVE today (only plan on the chart)", "src": "AMD eligibility (free 271)", "when": WHEN}],
    "notes": [{"who": "Claude", "at": NOW, "text": "11/15 Sunday sweep: the exact-date check confirms WellCare finalized the 6/22 visit at zero (CARC 252 - they want documentation). Coverage was fine (WellCare paid the 6/25 visit), so no insurance change - this stays a resubmit-with-records / appeal decision."}]}})
scr_old = [r for r in items if r["amdid"] == "17477375"][0]
new_row = {"id": "<chart17477375>-dup0807", "patient": scr_old["patient"], "dob": scr_old.get("dob", ""), "facility": "SNF (99306 8/7/2026)",
    "amdid": "17477375", "mbi": "", "amount": 256, "status": "william",
    "need": "WILLIAM: void v19455316? It is a second 99306 for 8/7/2026 (256 dollars, charge 23366554, entered later) - the first one, v19451040 (charge 23361053), was PAID by WellCare on 9/4/2026 (check 1008803098). WellCare denied the second as a duplicate (277 code 54, 10/2/2026, claim 3879905006). Say void and the next run voids it; no rebill.",
    "why": "Sunday claim-status sweep 11/15: WEL04 8/7/2026 DENIED - duplicate of a previously processed claim",
    "checks": [{"ok": "no", "result": "v19455316 8/7/2026 99306 256 dollars: DENIED code 54 'duplicate of a previously processed claim/line', check 1003567422, 10/2/2026", "src": "Stedi 277 WellCare (14163) claim status, exact date", "when": WHEN},
               {"ok": "ok", "result": "v19451040 8/7/2026 99306 at WEL04 paid 9/4/2026 check 1008803098 + WOINS; v19455316 same DOS/CPT open 256 dollars, no payment", "src": "AMD gettxhistory (live chart)", "when": WHEN},
               {"ok": "no", "result": "Medicare 271 date of death [DOB] (DOS 8/7 is before it - no post-death charges on the chart)", "src": "AMD eligibility (free 271) elig_amd --all", "when": WHEN},
               {"ok": "human", "result": "void the duplicate charge 23366554 (William's word needed)", "src": "William", "when": WHEN}],
    "notes": [{"who": "Claude", "at": NOW, "text": "The 8/7 admission visit was entered twice. WellCare paid the first one in September and denies the second as a duplicate every time it goes out. It is not a hospice question - it just needs voiding. Say void and I'll do it."}],
    "created": NOW}
ops += plan_new_row(items, new_row, same_item=False, now=NOW)
doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": NOW, "ops": ops}
doc = clean_file(doc)
json.dump(doc, open("/home/claude/unbilled/board_updates_%s.json" % STAMP, "w"), indent=1)
print(len(doc["ops"]), "ops")
