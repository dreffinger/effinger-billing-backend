# PLAIN ENGLISH (repo copy - names and member numbers replaced by placeholders) (nightly cascade 2026-11-22T0535Z): writes tonight's Insurance Refresh Board inbox file
# (append ops on the three Medicare Advantage cards re-pointed tonight, the CHP card, and one new card for the UMR
# subscriber question) to /home/claude/unbilled/outbox/board_updates_2026-11-22T0535Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-22T0535Z"; AT = "2026-11-22T06:05:00Z"; WHEN = "11/22"
ops = []
for cid, plan, payer, rows, total, note in [
    ("[name]-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
     [("19462054", "23375068", "11/20", "2,1", "1")], 160,
     "11/22 nightly: one more hospital visit (11/20, 99233, 160 dollars) came in Medicare-first; now at the BCBS (Medicare Plus Blue MA) plan as an original claim. Your CO-32 / member-id question and the April reverse-or-leave question above still stand."),
    ("[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
     [("19462051", "23375065", "11/20", "2", "1")], 160,
     "11/22 nightly: one more hospital visit (11/20, 99233, 160 dollars) came in Medicare-first; now at the BCBS (HCSC Medicare Advantage) plan as an original claim. Nothing for you here."),
    ("[name]-17478471", "CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20250901-20261231)", "UNI20 / UHC AARP MA",
     [("19462041", "23375055", "11/18", "1,2", "2"), ("19462065", "23375079", "11/20", "1,2", "2")], 320,
     "11/22 nightly: two hospital visits (11/18 entered late, and 11/20; 99233, 160 each) came in Medicare-first; both now at the UHC AARP Medicare Advantage plan (seq 2) as original claims. Nothing for you here."),
]:
    checks = [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/20/2026: %s - %s entered Medicare first" % (plan, ", ".join("v%s %s (99233) insorder %s" % (v, d, o) for v, c, d, o, s in rows)), "src": "Stedi Medicare answer (pre-claim check 11/22, cached)", "when": WHEN},
              {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN}]
    for v, c, d, o, s in rows:
        checks.append({"ok": "ok", "result": "v%s %s -> insorder %s (%s), frequency 1, chargerebill seq %s -> 204 (160 dollars); read back insbilled 0, insorder %s" % (v, d, s, payer, s, s), "src": "AMD action: freq1_visit reroute %s %s %s %s" % (v, c, s, s), "when": WHEN})
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {}, "append": {
        "checks": checks,
        "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                 "text": "DOS 20261120 ADVANTAGE PLAN on DOS: %s\nreroute: %s" % (plan, " | ".join("vst%s %s -> %s 204" % (v, o, s) for v, c, d, o, s in rows))}],
        "notes": [{"who": "Claude", "text": note, "at": AT}]}})

ops.append({"op": "upsert", "collection": "items", "id": "[name]-17478455", "set": {}, "append": {
    "checks": [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/20/2026: CAPITAL HEALTH PLAN (coordinationOfBenefits 20080201) - open at Medicare: v19461640 11/16 99223 310, v19461968 11/17, v19461853 11/18, v19461990 11/19, v19462060 11/20 (99233 160 each) = 950 dollars; nothing re-sent", "src": "Stedi Medicare answer (pre-claim check 11/22, cached)", "when": WHEN}],
    "notes": [{"who": "Claude", "at": AT, "text": "11/22 nightly: one more hospital visit (11/20, 160 dollars) came in Medicare-first - 950 dollars now waiting on the CHP member number (facesheet or CHP card). Nothing re-sent."}]}})

ops.append({"op": "upsert", "collection": "items", "id": "[name]-17477648", "set": {
    "patient": "[NAME]", "dob": "", "facility": "hospital visits 9/2-9/4/2026 (99223 + 99233 x2)", "amdid": "17477648", "mbi": "",
    "need": "WILLIAM (630 dollars): UMR claims for 9/2, 9/3, 9/4/2026 (v19453782 99223 310, v19453773 99233 160, v19453753 99233 160) - sent 9/6, no answer in 77 days; UHC/UMR claim status answers 'entity not eligible' on all three. AMD's free 271 on the chart's UMR plan (member [MEMBER]) is ACTIVE today but names the SUBSCRIBER as [SUBSCRIBER NAME], not the patient. If the patient is the subscriber's dependent (spouse), the UMR plan on her chart needs subscriber = the subscriber and relationship = spouse - please confirm from the card or facesheet (and the subscriber's date of birth), or tell me the plan is set right and I will ask UMR another way.",
    "why": "Sunday claim-status sweep 11/22: NOT ELIGIBLE on the date of service (277 D0 / 109 entity not eligible) x3 UMR claims",
    "amount": 630, "status": "william"},
    "append": {
        "checks": [{"ok": "no", "result": "D0 / 109 Entity not eligible on v19453782 9/2, v19453773 9/3, v19453753 9/4 (asked 11/22, payer 87726)", "src": "Stedi claim status (UMR via 87726)", "when": WHEN},
                   {"ok": "ok", "result": "seq 1 car303242 UMR [MEMBER] ACTIVE; subscriber on the 271 = [SUBSCRIBER NAME]", "src": "AMD eligibility (free 271) - elig_amd --all", "when": WHEN},
                   {"ok": "na", "result": "not bought tonight: the 271 already says the plan is active - the question is who the subscriber is", "src": "Stedi payer eligibility", "when": WHEN},
                   {"ok": "human", "result": "card / facesheet: UMR subscriber (spouse?) + relationship + subscriber DOB", "src": "William", "when": WHEN}],
        "api": [{"src": "Stedi API - claim status 87726 + AMD 271", "at": AT, "text": "claim status 20261122: v19453782 DOS 20260902 310.00 D0/109 | v19453773 DOS 20260903 160.00 D0/109 | v19453753 DOS 20260904 160.00 D0/109\nAMD 271 seq1 car303242 UMR [MEMBER] ACTIVE | subscriber [SUBSCRIBER NAME] | addr [CITY]"}],
        "notes": [{"who": "Claude", "at": AT, "text": "Created by the 11/22 Sunday sweep. Three UMR hospital claims from early September never got an answer; UMR says 'not eligible' but AMD's own check says the plan is active under [subscriber] as subscriber. Most likely the claims went out with the patient as the subscriber. Nothing re-sent or written off - I need the card or facesheet to set the subscriber right."}]}})

doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print(p, len(ops), "ops")
