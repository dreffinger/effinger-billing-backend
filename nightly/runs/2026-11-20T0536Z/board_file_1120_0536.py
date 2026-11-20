# PLAIN ENGLISH (repo copy - names, MBIs, DOBs, member numbers and addresses replaced by placeholders) (nightly cascade 2026-11-20T0536Z): writes tonight's Insurance Refresh Board inbox file
# (append ops on two Medicare Advantage cards + one CHP card, and one new card for a chart re-pointed to its UHC MA plan)
# to /home/claude/unbilled/outbox/board_updates_2026-11-20T0536Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-20T0536Z"; AT = "2026-11-20T05:45:00Z"; WHEN = "11/20"
ops = []
for cid, plan, payer, vid, chg, note in [
    ("[name]-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
     "19461846", "23374875",
     "11/20 nightly: one more hospital visit (11/18, 99233, 160 dollars) came in Medicare-first; now at the BCBS (Medicare Plus Blue MA) plan as an original claim. Your CO-32 and April reverse-or-leave questions above still stand. I see your 11/19 hospital-sheet paste lists 'BC PPO MCR OOS - [MEMBER]' while the chart's BCBS plan carries [MEMBER] - that member-id difference is the likely cause of the CO-32; I did not change the member id without your word (say 'use X3LM68527616' and the next run updates the BCBS plan and re-sends the November stay)."),
    ("[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
     "19461844", "23374873",
     "11/20 nightly: one more hospital visit (11/18, 99233, 160 dollars) came in Medicare-first; now at the BCBS (HCSC Medicare Advantage) plan as an original claim. Nothing for you here."),
]:
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {},
        "append": {
            "checks": [
                {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/18/2026: %s - v%s 11/18 (99233) had been entered at insorder 2,1 (Medicare first)" % (plan, vid), "src": "Stedi Medicare answer (pre-claim check 11/20, cached)", "when": WHEN},
                {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN},
                {"ok": "ok", "result": "v%s 11/18 -> insorder 1 (%s), frequency 1, chargerebill seq 1 -> 204 (160 dollars); read back insbilled 0, insorder 1" % (vid, payer), "src": "AMD action: rebill_patient_year <chart> 1 --days 2 (charge %s)" % chg, "when": WHEN}],
            "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                     "text": "DOS 20261118 ADVANTAGE PLAN on DOS: %s\nreroute: vst%s 2,1 -> 1 204" % (plan, vid)}],
            "notes": [{"who": "Claude", "text": note, "at": AT}]}})

ops.append({"op": "upsert", "collection": "items", "id": "[name]-17478455", "set": {},
    "append": {"checks": [{"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/18/2026: CAPITAL HEALTH PLAN (coordinationOfBenefits 20080201) - a new 11/18 hospital visit (160 dollars) is also at Medicare; nothing re-sent", "src": "Stedi Medicare answer (pre-claim check 11/20, cached)", "when": WHEN}],
               "notes": [{"who": "Claude", "at": AT, "text": "11/20 nightly: a second hospital visit (11/18, 160 dollars) came in Medicare-first - 470 dollars now waiting on the CHP member number. Nothing re-sent."}]}})

row = {"id": "[name]-17478471", "patient": "[NAME]", "dob": "[DOB]", "facility": "HCA (99223+99497 11/17/2026)",
       "amdid": "17478471", "mbi": "[MBI]", "amount": 443, "status": "claude",
       "inscarrier": "UNI20 UnitedHealthcare AARP Medicare Advantage Patriot (seq 2, chart order 2); FLO02 Medicare seq 1",
       "insplans": "1st FLO02 Medicare [MBI] - 2nd UNI20 [MEMBER] (added 11/20, begin 09/01/2026)", "lastfac": "HCA Capital Hospital",
       "need": "DONE (Claude): Medicare names a UnitedHealthcare Advantage plan (Care Improvement Plus H2406); discovery found the AARP Medicare Advantage Patriot plan [MEMBER] active 9/1-12/31/2026. Plan added, chart order set to it, the 11/17 admission (443 dollars) re-sent to UHC. Watch for the UHC answer.",
       "why": "Stedi pre-claim check 11/20: ADVANTAGE PLAN on DOS - CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20250901-20261231); chart had only Medicare",
       "checks": [
           {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/17/2026: CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20250901-20261231); Part A 20120801 Part B 20120801; no date of death", "src": "Stedi Medicare check (pre-claim check 11/20)", "when": WHEN},
           {"ok": "ok", "result": "seq 1 FLO02 [MBI] ACTIVE | PR 18:H2406 N6:130 CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. - the only plan on the chart", "src": "AMD eligibility (free 271) - elig_amd --all", "when": WHEN},
           {"ok": "ok", "result": "UNITEDHEALTHCARE (87726) member [MEMBER] Active - LPPO-AARP MEDICARE ADVANTAGE PATRIOT NO RX FL-MA2, plan 20260901-20261231 (also inactive WellCare 2025 and Aetna)", "src": "Stedi insurance discovery DOS 11/17/2026", "when": WHEN},
           {"ok": "ok", "result": "primary dx M48.02 acceptable - no change", "src": "dx_primary_fix plan", "when": WHEN},
           {"ok": "ok", "result": "add_ins UNI20 car6404 [MEMBER] begin 09/01/2026 -> ins9521366 seq 2; chart order 2", "src": "AMD action: add_ins + ins_update sequence=2", "when": WHEN},
           {"ok": "ok", "result": "v19461861 11/17 (99223 310 + 99497 133) -> insorder 2 (UNI20), frequency 1, chargerebill seq 2 -> 204 (443 dollars); read back insbilled 0, insorder 2", "src": "AMD action: rebill_patient_year 17478471 2 --days 4", "when": WHEN}],
       "api": [{"src": "Stedi API - Medicare check + insurance discovery + AMD 271", "at": AT,
                "text": "[NAME]  DOB [DOB]  DOS 20261117\nMBI [MBI]  Part A 20120801  Part B 20120801  death none\nADVANTAGE PLAN on DOS: CARE IMPROVEMENT PLUS SOUTH CENTRAL INSURANCE CO. (coordinationOfBenefits 20250901-20261231)\nAMD 271 seq1 car6085 FLO02 ACTIVE | PR 18:H2406 N6:130 CARE IMPROVEMENT PLUS SOUTH CENTRAL | addr [ADDR]\nDiscovery: UNITEDHEALTHCARE 87726 member [MEMBER] ACTIVE LPPO-AARP MEDICARE ADVANTAGE PATRIOT NO RX FL-MA2 plan 20260901-20261231\nadded ins9521366 UNI20 seq 2; v19461861 rebill seq 2 -> 204"}],
       "notes": [{"who": "Claude", "at": AT, "text": "Created by the 11/20 nightly cascade. New HCA chart with only Medicare on it; Medicare names a UnitedHealthcare Advantage plan, and discovery found the AARP Medicare Advantage Patriot member number. I added the UHC plan, made it the chart's payer and re-sent the 11/17 admission (443 dollars) to UHC. Nothing for you here."}]}
ops += plan_new_row([], row, now=AT)

doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print(p, len(ops), "ops")
