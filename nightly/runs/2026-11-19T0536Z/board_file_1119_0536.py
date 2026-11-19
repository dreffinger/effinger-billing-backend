# PLAIN ENGLISH (repo copy - names, MBIs, DOBs and addresses replaced by placeholders) (nightly cascade 2026-11-19T0536Z): writes tonight's Insurance Refresh Board inbox file
# (append ops on two existing Medicare Advantage cards + two new CHP cards on William's turn) to
# /home/claude/unbilled/outbox/board_updates_2026-11-19T0536Z.json. No AMD or board call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-19T0536Z"; AT = "2026-11-19T05:50:00Z"; WHEN = "11/19"
ops = []
for cid, plan, payer, vid, chg, note in [
    ("[name]-denials", "BCBS OF MICHIGAN MUTUAL INSURANCE COMPANY (coordinationOfBenefits 20260101)", "BCBS / BCBS-MI Medicare Plus Blue MA",
     "19461618", "23374537",
     "11/19 nightly: one more hospital visit (11/17, 99233, 160 dollars) came in Medicare-first; it is now at the BCBS (Medicare Plus Blue MA) plan as an original claim, same as the earlier nights. Heads-up: the 11/18 day run found Florida Blue answered the 11/7-11/12 stay CO-32 (not an eligible dependent), so these BCBS claims may come back the same way until the member suffix / relationship on the BCBS plan is fixed - your CO-32 and April reverse-or-leave questions above still stand."),
    ("[name]-17473090", "HEALTH CARE SERVICE CORPORATION (coordinationOfBenefits 20240101)", "BCBS / HCSC MA",
     "19461619", "23374538",
     "11/19 nightly: one more hospital visit (11/17, 99233, 160 dollars) came in Medicare-first; now at the BCBS (HCSC Medicare Advantage) plan as an original claim. Nothing for you here."),
]:
    ops.append({"op": "upsert", "collection": "items", "id": cid, "set": {},
        "append": {
            "checks": [
                {"ok": "no", "result": "ADVANTAGE PLAN on DOS 11/17/2026: %s - v%s 11/17 (99233) had been entered at insorder 2,1 (Medicare first)" % (plan, vid), "src": "Stedi Medicare answer (pre-claim check 11/19, cached)", "when": WHEN},
                {"ok": "ok", "result": "primary dx acceptable (dx_primary_fix plan) - no change", "src": "dx_primary_fix plan", "when": WHEN},
                {"ok": "ok", "result": "v%s 11/17 -> insorder 1 (%s), frequency 1, chargerebill seq 1 -> 204 (160 dollars); read back insbilled 0, insorder 1" % (vid, payer), "src": "AMD action: freq1_visit reroute %s %s 1 1" % (vid, chg), "when": WHEN}],
            "api": [{"src": "Stedi API - pre-claim check (cached Medicare answer) + AMD reroute", "at": AT,
                     "text": "DOS 20261117 ADVANTAGE PLAN on DOS: %s\nreroute: vst%s 2,1 -> 1 204" % (plan, vid)}],
            "notes": [{"who": "Claude", "text": note, "at": AT}]}})

NEW = [
    dict(id="[name]-17478452", patient="[NAME]", dob="[DOB]", amdid="17478452", mbi="[MBI]",
         facility="HCA FLORIDA CAPITAL HOSPITAL (99223 11/16, 99232 11/17/2026)", amount=421,
         visits="v19461642 11/16 99223 310 dollars; v19461630 11/17 99232 111 dollars", coord="20080301", h="H5938 N6:001",
         addr="[ADDR]", partab="Part A 20080201  Part B 20080201"),
    dict(id="[name]-17478455", patient="[NAME]", dob="[DOB]", amdid="17478455", mbi="[MBI]",
         facility="HCA FLORIDA CAPITAL HOSPITAL (99223 11/16/2026)", amount=310,
         visits="v19461640 11/16 99223 310 dollars", coord="20080201", h="H5938 N6:802",
         addr="[ADDR]", partab="Part A 20080201  Part B 20080201"),
]
for n in NEW:
    row = {"id": n["id"], "patient": n["patient"], "dob": n["dob"], "facility": n["facility"], "amdid": n["amdid"], "mbi": n["mbi"],
           "amount": n["amount"], "status": "william",
           "inscarrier": "FLO02 Medicare on the chart - Medicare says CAPITAL HEALTH PLAN Medicare Advantage (H5938) is the payer",
           "insplans": "1st FLO02 Medicare %s (only plan)" % n["mbi"], "lastfac": "HCA Capital Hospital",
           "need": "WILLIAM: CHP member number needed (%d dollars). Medicare's record says this patient is on CAPITAL HEALTH PLAN's Medicare Advantage plan (H5938, coordination of benefits since %s/%s), so the HCA visits (%s) cannot go to Medicare - and CHP needs its own member number (the MBI is not accepted). Drop the HCA facesheet or the CHP card (member number) and the next run adds CAP07 and sends the claims." % (n["amount"], n["coord"][4:6], n["coord"][:4], n["visits"]),
           "why": "Stedi pre-claim check 11/19: ADVANTAGE PLAN on DOS - CAPITAL HEALTH PLAN (coordinationOfBenefits %s); chart has only Medicare" % n["coord"],
           "checks": [
               {"ok": "no", "result": "ADVANTAGE PLAN on DOS: CAPITAL HEALTH PLAN (coordinationOfBenefits %s); %s; no date of death" % (n["coord"], n["partab"]), "src": "Stedi Medicare check (pre-claim check 11/19)", "when": WHEN},
               {"ok": "ok", "result": "seq 1 FLO02 %s ACTIVE | OT + HN 18:%s CAPITAL HEALTH PLAN - the only plan on the chart" % (n["mbi"], n["h"]), "src": "AMD eligibility (free 271) - elig_amd --all", "when": WHEN},
               {"ok": "na", "result": "not bought: CHP (95112) answers ERR 79 without its own member number", "src": "Stedi CHP eligibility", "when": WHEN},
               {"ok": "human", "result": "CHP member number (facesheet or card) for CAP07 car41826", "src": "William", "when": WHEN}],
           "api": [{"src": "Stedi API - Medicare check (pre-claim) + AMD 271", "at": AT,
                    "text": "%s  DOB %s\n%s  death none\nADVANTAGE PLAN on DOS: CAPITAL HEALTH PLAN  (coordinationOfBenefits %s)\nAMD 271 seq1 car6085 FLO02 %s ACTIVE | OT/HN 18:%s CAPITAL HEALTH PLAN | addr %s\nopen: %s" % (n["patient"], n["dob"], n["partab"], n["coord"], n["mbi"], n["h"], n["addr"], n["visits"])}],
           "notes": [{"who": "Claude", "at": AT, "text": "Created by the 11/19 nightly cascade. New HCA chart from the feed with only Medicare on it, but Medicare says Capital Health Plan's Advantage plan is the payer. CHP will not take the MBI - I need the CHP member number (facesheet or card) to add the plan and bill the hospital visits (same situation as chart 17478395)."}]}
    ops += plan_new_row([], row, now=AT)

doc = {"schema": "irb-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops}
clean_file(doc)
os.makedirs("/home/claude/unbilled/outbox", exist_ok=True)
p = "/home/claude/unbilled/outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1)
print(p, len(ops), "ops")
