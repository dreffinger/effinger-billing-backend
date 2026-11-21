# PLAIN ENGLISH (repo copy - names and member numbers replaced by placeholders) (nightly cascade 2026-11-21T0535Z): writes tonight's Insurance Refresh Board inbox file
# (append ops on three Medicare Advantage cards re-pointed tonight + one CHP card) to
# /home/claude/unbilled/outbox/board_updates_2026-11-21T0535Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-21T0535Z"; AT = "2026-11-21T05:45:00Z"; WHEN = "11/21"
ops = []
for cid, plan, payer, vid, chg, order, note in [
    ("[name]-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
     "19461982", "23375011", "2,1 -> 1",
     "11/21 nightly: one more hospital visit (11/19, 99233, 160 dollars) came in Medicare-first; now at the BCBS (Medicare Plus Blue MA) plan as an original claim. Your CO-32 / member-id question (hospital sheet [MEMBER] vs chart [MEMBER]) and the April reverse-or-leave question above still stand."),
    ("[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
     "19461981", "23375010", "2,1 -> 1",
     "11/21 nightly: one more hospital visit (11/19, 99233, 160 dollars) came in Medicare-first; now at the BCBS (HCSC Medicare Advantage) plan as an original claim. Nothing for you here."),
    ("[name]-17478471", "CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20250901-20261231)", "UNI20 / UHC AARP MA Patriot",
     "19461975", "23375004", "1,2 -> 2",
     "11/21 nightly: a new hospital visit (11/19, 99233, 160 dollars) came in Medicare-first; now at the UHC AARP Medicare Advantage plan (seq 2) as an original claim. Nothing for you here."),
]:
    seq = order.split("-> ")[1]
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {},
        "append": {
            "checks": [
                {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/19/2026: %s - v%s 11/19 (99233) had been entered at insorder %s (Medicare first)" % (plan, vid, order.split(" ->")[0]), "src": "Stedi Medicare answer (pre-claim check 11/21, cached)", "when": WHEN},
                {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN},
                {"ok": "ok", "result": "v%s 11/19 -> insorder %s (%s), frequency 1, chargerebill seq %s -> 204 (160 dollars); read back insbilled 0, insorder %s" % (vid, seq, payer, seq, seq), "src": "AMD action: freq1_visit reroute %s %s %s %s" % (vid, chg, seq, seq), "when": WHEN}],
            "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                     "text": "DOS 20261119 ADVANTAGE PLAN on DOS: %s\nreroute: vst%s %s 204" % (plan, vid, order)}],
            "notes": [{"who": "Claude", "text": note, "at": AT}]}})

ops.append({"op": "upsert", "collection": "items", "id": "[name]-17478455", "set": {},
    "append": {"checks": [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/19/2026: CAPITAL HEALTH PLAN (coordinationOfBenefits 20080201) - open at Medicare: v19461640 11/16 99223 310, v19461968 11/17 99233 160, v19461853 11/18 99233 160, v19461990 11/19 99233 160 (790 dollars); nothing re-sent", "src": "Stedi Medicare answer (pre-claim check 11/21, cached)", "when": WHEN}],
               "notes": [{"who": "Claude", "at": AT, "text": "11/21 nightly: two more hospital visits (11/17 and 11/19, 160 each) came in Medicare-first - 790 dollars now waiting on the CHP member number (facesheet or CHP card). Nothing re-sent."}]}})

doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print(p, len(ops), "ops")
