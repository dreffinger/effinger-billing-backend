# PLAIN ENGLISH (one-off, nightly cascade 2026-11-16T0536Z): builds board_updates_2026-11-16T0536Z.json for the Insurance
# Refresh Board from tonight's results (chart and visit ids only). Never touches AMD or the board itself.
import json, sys
sys.path.insert(0, "/home/claude/unbilled")
from board_ops import clean_file
STAMP = "2026-11-16T0536Z"; NOW = "2026-11-16T05:45:00Z"; WHEN = "11/16"
ops = []
CARD = json.load(open("/home/claude/unbilled/board_card_ids_1116.json"))  # chart -> card id (git-ignored; card ids carry names)
def row(rid, payer_line, plan_label, visits, prev_order, note):
    vtxt = ", ".join("v%s %s" % (v, d) for v, d in visits)
    dollars = 160 * len(visits)
    ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {"lastdos": "11/14/2026"}, "append": {
        "checks": [
            {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/14/2026: %s - %s (99233 x%d) had been entered at insorder %s (Medicare first)" % (payer_line, vtxt, len(visits), prev_order), "src": "Stedi Medicare answer (pre-claim check 11/16, cached)", "when": WHEN},
            {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN},
            {"ok": "ok", "result": "%s -> insorder 1 (%s), frequency 1, chargerebill seq 1 -> 204 x%d (%d dollars); read back insbilled 0, insorder 1" % (vtxt, plan_label, len(visits), dollars), "src": "AMD action: freq1_visit reroute <visit> <charge> 1 1", "when": WHEN}],
        "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": NOW,
                 "text": "DOS 20261114 ADVANTAGE PLAN on DOS: %s\nreroute: %s" % (payer_line, " | ".join("vst%s %s -> 1 204" % (v, prev_order) for v, _ in visits))}],
        "notes": [{"who": "Claude", "at": NOW, "text": note}]}})
row(CARD["17472826"], "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
    [("19461263", "11/13"), ("19461233", "11/14")], "2",
    "11/16 nightly: two more hospital visits (11/13, 11/14, 320 dollars) came in pointed at Medicare; both now at the BCBS (Medicare Plus Blue MA) plan as original claims. Your April reverse-or-leave question above still stands.")
row(CARD["17473090"], "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
    [("19461255", "11/13"), ("19461232", "11/14")], "2,1",
    "11/16 nightly: two more hospital visits (11/13, 11/14, 320 dollars) came in Medicare-first; both now at the BCBS (HCSC Medicare Advantage) plan as original claims. Nothing for you here.")
row(CARD["17474611-ma"], "CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20260801)", "UNI20 UHC MA",
    [("19460694", "11/08"), ("19461071", "11/09"), ("19461253", "11/13"), ("19461229", "11/14")], "2,4",
    "11/16 nightly: four more hospital visits (11/08, 11/09, 11/13, 11/14, 640 dollars) were at Medicare first (11/08 and 11/09 had already gone to Medicare on 11/10 and 11/12); all four now at the UHC Advantage plan alone as original claims. Nothing for you here.")
ops.append({"op": "upsert", "collection": "items", "id": CARD["17478395"], "append": {
    "checks": [{"ok": "no", "result": "still ADVANTAGE PLAN on DOS 11/13/2026: CAPITAL HEALTH PLAN (cached answer, no new lookup); chart still Medicare only, 5 visits 754 dollars waiting - no CHP member number yet", "src": "Stedi pre-claim check 11/16 (cached)", "when": WHEN}]}})
doc = clean_file({"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": NOW, "ops": ops})
json.dump(doc, open("/home/claude/unbilled/board_updates_%s.json" % STAMP, "w"), indent=1)
print(len(doc["ops"]), "ops")
