# PLAIN ENGLISH (repo copy - names replaced by placeholders) (nightly cascade 2026-11-23T0536Z): writes tonight's Insurance Refresh Board inbox file
# (append ops on the two Medicare Advantage cards re-pointed tonight and on the CHP card) to
# /home/claude/unbilled/outbox/board_updates_2026-11-23T0536Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-23T0536Z"; AT = "2026-11-23T06:00:00Z"; WHEN = "11/23"
ops = []
for cid, plan, payer, rows, note in [
    ("[name]-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
     [("19462182", "23375227", "11/21", "2", "1")],
     "11/23 nightly: one more hospital visit (11/21, 99233, 160 dollars) came in Medicare-first; now at the BCBS (Medicare Plus Blue MA) plan as an original claim. Your CO-32 / member-id question and the April reverse-or-leave question above still stand."),
    ("[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
     [("19462180", "23375225", "11/21", "2", "1")],
     "11/23 nightly: one more hospital visit (11/21, 99233, 160 dollars) came in Medicare-first; now at the BCBS (HCSC Medicare Advantage) plan as an original claim. Nothing for you here."),
]:
    checks = [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/21/2026: %s - %s entered Medicare first" % (plan, ", ".join("v%s %s (99233) insorder %s" % (v, d, o) for v, c, d, o, s in rows)), "src": "Stedi Medicare answer (pre-claim check 11/23, cached)", "when": WHEN},
              {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN}]
    for v, c, d, o, s in rows:
        checks.append({"ok": "ok", "result": "v%s %s -> insorder %s (%s), frequency 1, chargerebill seq %s -> 204 (160 dollars); read back insbilled 0, insorder %s" % (v, d, s, payer, s, s), "src": "AMD action: freq1_visit reroute %s %s %s %s" % (v, c, s, s), "when": WHEN})
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {}, "append": {
        "checks": checks,
        "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                 "text": "DOS 20261121 ADVANTAGE PLAN on DOS: %s\nreroute: %s" % (plan, " | ".join("vst%s %s -> %s 204" % (v, o, s) for v, c, d, o, s in rows))}],
        "notes": [{"who": "Claude", "text": note, "at": AT}]}})

ops.append({"op": "upsert", "collection": "items", "id": "[name]-17478455", "set": {}, "append": {
    "checks": [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/21/2026: CAPITAL HEALTH PLAN (coordinationOfBenefits 20080201) - open at Medicare: v19461640 11/16 99223 310, v19461968 11/17, v19461853 11/18, v19461990 11/19, v19462060 11/20, v19462187 11/21 (99233 160 each) = 1110 dollars; nothing re-sent", "src": "Stedi Medicare answer (pre-claim check 11/23, cached)", "when": WHEN}],
    "notes": [{"who": "Claude", "at": AT, "text": "11/23 nightly: one more hospital visit (11/21, 160 dollars) came in Medicare-first - 1110 dollars now waiting on the CHP member number (facesheet or CHP card). Nothing re-sent."}]}})

doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print(p, len(ops), "ops")
