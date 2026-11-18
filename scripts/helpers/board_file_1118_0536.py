# PLAIN ENGLISH (nightly cascade 2026-11-18T0536Z): writes tonight's Insurance Refresh Board inbox file
# (append-only ops on three existing Medicare Advantage cards) to outbox/board_updates_2026-11-18T0536Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-18T0536Z"; AT = "2026-11-18T05:45:00Z"; WHEN = "11/18"
CARDS = [
    ("karnes-chester-dougal-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
     [("19461426", "23374321", "11/15", "2,1"), ("19461440", "23374336", "11/16", "2,1")],
     "11/18 nightly: two more hospital visits (11/15, 11/16, 320 dollars) came in Medicare-first; both now at the BCBS (Medicare Plus Blue MA) plan as original claims. Your April reverse-or-leave question above still stands."),
    ("marsh-[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
     [("19461425", "23374320", "11/15", "2"), ("19461438", "23374334", "11/16", "2")],
     "11/18 nightly: two more hospital visits (11/15, 11/16, 320 dollars) came in Medicare-first; both now at the BCBS (HCSC Medicare Advantage) plan as original claims. Nothing for you here."),
    ("[name]-17474611-ma", "CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20260801)", "UNI20 UHC MA",
     [("19461436", "23374332", "11/16", "2,4")],
     "11/18 nightly: one more hospital visit (11/16, 160 dollars) was at Medicare first; now at the UHC Advantage plan alone as an original claim. Nothing for you here."),
]
ops = []
for cid, plan, payer, visits, note in CARDS:
    vlist = ", ".join("v%s %s" % (v, d) for v, c, d, o in visits)
    dollars = 160 * len(visits)
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {},
        "append": {
            "checks": [
                {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/16/2026: %s - %s (99233 x%d) had been entered Medicare first" % (plan, vlist, len(visits)), "src": "Stedi Medicare answer (pre-claim check 11/18, cached)", "when": WHEN},
                {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN},
                {"ok": "ok", "result": "%s -> insorder 1 (%s), frequency 1, chargerebill seq 1 -> 204 x%d (%d dollars); read back insbilled 0, insorder 1" % (vlist, payer, len(visits), dollars), "src": "AMD action: freq1_visit reroute <visit> <charge> 1 1", "when": WHEN}],
            "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                     "text": "DOS 20261116 ADVANTAGE PLAN on DOS: %s\nreroute: %s" % (plan, " | ".join("vst%s %s -> 1 204" % (v, o) for v, c, d, o in visits))}],
            "notes": [{"who": "Claude", "at": AT, "text": note}]}})
doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
doc = clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print("wrote", p, len(doc["ops"]), "ops")
