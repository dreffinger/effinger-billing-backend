# PLAIN ENGLISH (repo copy - names replaced by placeholders) (nightly cascade 2026-11-26T0536Z): writes tonight's Insurance Refresh Board inbox file
# (append ops on the five Medicare Advantage cards re-pointed tonight + one new card on William's turn for chart 17478516)
# to /home/claude/unbilled/outbox/board_updates_2026-11-26T0536Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-26T0536Z"; AT = "2026-11-26T06:00:00Z"; ASOF = "2026-11-26T05:50:00Z"; WHEN = "11/26"
ops = []
def mk(cid, plan, payer, rows, note, cached=True):
    checks = [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/24/2026: %s - %s entered Medicare first" % (plan, ", ".join("v%s %s (%s) insorder %s" % (v, d, cpt, o) for v, c, d, cpt, o, s, amt in rows)),
               "src": "Stedi Medicare answer (pre-claim check 11/26%s)" % (", cached" if cached else ""), "when": WHEN},
              {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix --dry) - no change", "src": "dx_primary_fix --dry", "when": WHEN}]
    for v, c, d, cpt, o, s, amt in rows:
        checks.append({"ok": "ok", "result": "v%s %s -> insorder %s (%s), frequency 1, chargerebill seq %s -> 204 (%s dollars); read back insbilled 0, insorder %s" % (v, d, s, payer, s.split(",")[0], amt, s),
                       "src": "AMD action: freq1_visit reroute %s %s %s %s" % (v, c, s, s.split(",")[0]), "when": WHEN})
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {}, "append": {
        "checks": checks,
        "api": [{"src": "Stedi API - pre-claim check (Medicare answer) + AMD reroute", "at": AT,
                 "text": "DOS 20261124 ADVANTAGE PLAN on DOS: %s\nreroute: %s" % (plan, " | ".join("vst%s %s -> %s 204" % (v, o, s) for v, c, d, cpt, o, s, amt in rows))}],
        "notes": [{"who": "Claude", "text": note, "at": AT}]}})

mk("[name]-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
   [("19462724", "23376048", "11/23", "99233", "2,1", "1", 160), ("19462701", "23376024", "11/24", "99233", "2,1", "1", 160)],
   "11/26 nightly: two more hospital visits (11/23, 11/24, 99233, 320 dollars) came in Medicare-first; both now at the BCBS (Medicare Plus Blue MA) plan as original claims. Nothing for you here.")
mk("[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
   [("19462722", "23376046", "11/23", "99233", "2,1", "1", 160), ("19462699", "23376022", "11/24", "99233", "2,1", "1", 160)],
   "11/26 nightly: two more hospital visits (11/23, 11/24, 99233, 320 dollars) came in Medicare-first; both now at the BCBS (HCSC Medicare Advantage) plan as original claims. Nothing for you here.")
mk("[name]-17475777", "PREFERRED CARE PARTNERS, INC. (coordinationOfBenefits 20260701)", "UNI20 AARP MA from UHC",
   [("19462075", "23375090", "11/17", "99309", "2,1", "1", 141), ("19462602", "23375843", "11/24", "99487+99489", "2,1", "1", 315)],
   "11/26 nightly: the 11/17 SNF visit (141 dollars) and the 11/24 CCM (315 dollars) had gone to Medicare first again; both now at the AARP Medicare Advantage (UHC) plan as original claims (456 dollars). Note for coding: the 11/24 CCM carries a single diagnosis (U07.1) - CCM normally lists two or more chronic conditions, so UHC may question it.")
mk("[name]-17475837", "CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20240401)", "UNI20 AARP MA Patriot",
   [("19462494", "23375642", "11/24", "99487+99489", "1,2", "2", 315)],
   "11/26 nightly: the 11/24 CCM (315 dollars) came in Medicare-first; now at the AARP Medicare Advantage Patriot plan (seq 2, which paid October) as an original claim. Nothing for you here.")
mk("[name]-25558", "CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20250301)", "UHCMA UHC Dual Complete",
   [("19462580", "23375799", "11/24", "99487+99489", "1,5", "4,5", 315)],
   "11/26 nightly: the 11/24 CCM (315 dollars) came in Medicare-first; now at the UHC Dual Complete plan (order 4,5, Medicaid behind it) as an original claim. Nothing for you here.")

items = json.load(open("/home/claude/unbilled/board_items_1126.json"))
row = {"id": "[name]-17478516", "patient": "[name]", "dob": "[dob]", "facility": "hospital (99223/99233)", "amdid": "17478516",
       "mbi": "[mbi]", "amount": 470, "status": "william",
       "need": "WILLIAM: her Anthem Medicare Advantage member number (card or hospital face sheet). Medicare's record names ANTHEM INSURANCE COMPANIES (H4036, Georgia) as her Advantage plan since 1/1/2025; the chart has only Medicare, so the 11/23 and 11/24 hospital visits (470 dollars) went to Medicare, which will deny. With the number I add the plan and re-send both.",
       "why": "nightly cascade pre-check 11/26: new hospital admit billed to Medicare while Medicare names an Anthem Advantage plan",
       "checks": [
           {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/24/2026: ANTHEM INSURANCE COMPANIES, INC. (coordinationOfBenefits 20250101-20261231); Part A/B 20130501; no date of death", "src": "Stedi plain Medicare check (pre-claim check 11/26)", "when": WHEN},
           {"ok": "ok", "result": "FLO02 ACTIVE; other payer OT/PR 18:H4036 ANTHEM INSURANCE COMPANIES, INC.; address [city] GA", "src": "AMD eligibility (free 271) - FLO02 ins9521411", "when": WHEN},
           {"ok": "no", "result": "4 coverages: UHC 87726 Inactive (x2), Aetna dental inactive, CMS active - no Anthem record / member number", "src": "Stedi insurance discovery (DOS 11/24/2026)", "when": WHEN},
           {"ok": "human", "result": "Anthem MA member number (card / face sheet) - v19462733 11/23 99223 310 + v19462690 11/24 99233 160 left at Medicare", "src": "William", "when": WHEN}],
       "api": [{"src": "Stedi API - Medicare check + discovery; AMD 271", "at": AT,
                "text": "[name] DOB [dob] DOS 20261124\nMedicare: Part A 20130501 Part B 20130501, ADVANTAGE PLAN ANTHEM INSURANCE COMPANIES, INC. (COB 20250101-20261231)\nAMD 271 FLO02 [mbi] ACTIVE | OT/PR 18:H4036 N6:801 ANTHEM INSURANCE COMPANIES, INC. | addr [address]\nDiscovery: coveragesFound 4 - UNITEDHEALTHCARE 87726 Inactive x2; AETNA dental Inactive; CMS Active. No Anthem member id."}],
       "notes": [{"who": "Claude", "at": AT, "text": "New admit 11/23: Medicare says Anthem (Georgia, H4036) Medicare Advantage covers her; AMD's 271 agrees. Discovery found no Anthem member number, so I could not add the plan. Both hospital visits (470 dollars) are at Medicare for now. Please paste her Anthem card or face sheet number here."}]}
ops += plan_new_row(items, row, now=AT)

doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "asof": ASOF, "ops": ops}
clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print(p, len(ops), "ops")
