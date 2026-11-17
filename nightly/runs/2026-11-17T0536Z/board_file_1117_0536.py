# PLAIN ENGLISH (nightly cascade 2026-11-17T0536Z): writes tonight's Insurance Refresh Board inbox file
# (append-only ops on the Morland MA card) to outbox/board_updates_2026-11-17T0536Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-17T0536Z"; AT = "2026-11-17T05:45:00Z"; WHEN = "11/17"
ops = [{"op": "upsert", "collection": "items", "id": "[name]-17474611-ma", "set": {},
        "append": {
            "checks": [
                {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/15/2026: CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20260801) - v19461282 11/15 (99233, 160 dollars) had been entered at insorder 2,4 (Medicare first)", "src": "Stedi Medicare answer (pre-claim check 11/17, cached)", "when": WHEN},
                {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN},
                {"ok": "ok", "result": "v19461282 11/15 -> insorder 1 (UNI20 UHC MA), frequency 1, chargerebill seq 1 -> 204 (160 dollars); read back insbilled 0, insorder 1", "src": "AMD action: freq1_visit reroute 19461282 23374201 1 1", "when": WHEN}],
            "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                     "text": "DOS 20261115 ADVANTAGE PLAN on DOS: CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20260801)\nreroute: vst19461282 2,4 -> 1 204 (readback insbilled 0, insorder 1)"}],
            "notes": [{"who": "Claude", "at": AT, "text": "11/17 nightly: one more hospital visit (11/15, 160 dollars) was at Medicare first; now at the UHC Advantage plan alone as an original claim. Nothing for you here."}]}}]
doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
doc = clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print("wrote", p, len(doc["ops"]), "ops")
