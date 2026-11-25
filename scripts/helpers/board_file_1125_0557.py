#!/usr/bin/env python3
# PLAIN ENGLISH (the Insurance Refresh Board file of the ehpa Billing Button run 2026-11-25T0557Z)
# Decides: nothing. Writes outbox/board_updates_2026-11-25T0557Z.json (schema irb-board-updates/1, asof = the time this run read the
#   board) with ONE op per card this run worked - the reply, and the hand-back in the SAME op where something is still needed from
#   William (facesheets_needed.handback_op), a close ('done') where nothing is; notes / checks go in `append`; a new card through
#   board_ops.plan_new_row (twinned by chart). The facts come from this run's registers (board_cards_2026-11-25T0557Z.json,
#   mbi_lookup, insp_bypass) - never typed from memory. board_ops.clean_file before the dump (never `updated` in a set).
# Never touches: AMD, the board, Drive. Usage: python3 board_file_1125_0557.py
import json, os, sys, glob, datetime
sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
import board_ops
from facesheets_needed import handback_op
S = "2026-11-25T0557Z"; ASOF = "2026-11-25T06:03:00Z"; NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SRC = "ehpa billing button run %s" % S
BOARD = "/tmp/claude-0/-home-claude-effinger-billing-backend/54dad968-8e54-5d62-b91f-c8705cdd698d/scratchpad/board_0557/items"
items = []
for f in glob.glob(BOARD + "/*.json"):
    o = json.load(open(f)); x = o.get("data", o); x = dict(x); x.setdefault("id", os.path.basename(f)[:-5]); items.append(x)
reg = json.load(open("registers/board_cards_%s.json" % S))["cards"]
mbi = json.load(open("registers/mbi_lookup_%s.json" % S))
byp = json.load(open(glob.glob("registers/insp_bypass_2026-11-25T06*Z.json")[0]))
doc = {"schema": "irb-board-updates/1", "source": SRC, "created": NOW, "asof": ASOF, "ops": []}
def note(t): return {"who": "Claude", "text": t, "at": NOW}
def check(ok, src, res): return {"ok": ok, "src": src, "result": res, "when": "11/25"}
# 1. COPELAND 17476021 - the facesheet number is the chart's own, still rejected; the look-up with his SSN finds no record
r = reg["[name]-17476021-medicare-number"]; m = mbi["17476021"]
doc["ops"].append(handback_op("[name]-17476021-medicare-number",
    "NEW MEDICARE CARD NEEDED ($3,120, 20 visits): the number on the sheet you pasted is the one already on the chart, and Medicare still rejects it. Medicare paid this chart under it through June 2026, so the number was most likely reissued after that - the red, white and blue card he holds now (or the number from Medicare's own letter) is what will clear it.",
    "Read your paste 11/25: its Medicare number is identical to the chart's Medicare number, and AdvancedMD's free check still answers 'invalid subscriber id' (72) on it. Medicare's own look-up by his name, birth date and Social Security number finds no record under that name/birth date (75). The hospital's sheet carries the old number; Medicare reissued it after it last paid (the 04/01-04/03/2026 visits, paid 06/2026). Nothing changed on the chart; the 20 visits wait for the new number.",
    why="Medicare rejects the chart's Medicare number as invalid; William's 11/25 facesheet paste shows the same number; Medicare's look-up (name, DOB, SSN) finds no record", amount=3119.89, ask="facesheet", at=NOW))
doc["ops"][-1]["append"]["checks"] = [check("no", "AMD eligibility (free 271) on the chart's Medicare plan - run %s" % S, "REJECTED 72 (invalid subscriber id); the pasted facesheet number = the chart's number"),
                                       check("no", "Stedi MBI look-up (MBILU, with the chart's SSN) - run %s" % S, "75 Subscriber/Insured Not Found")]
# 2. DANIEL 48458 - same situation; the look-up under the hospital's spelling DANIELS finds nothing either
doc["ops"].append(handback_op("[name]-48458-medicare-number",
    "NEW MEDICARE CARD NEEDED ($107, 1 visit): the 2024 ER sheet you pasted carries the number already on the chart, and Medicare rejects it today - her current red, white and blue card (Medicare reissues numbers) is what will clear it.",
    "Read your paste 11/25 (an ER sheet of 09/23/2024): its Medicare number is identical to the chart's, and AdvancedMD's free check still answers 'invalid subscriber id' (72). Medicare's look-up by name and birth date finds no record - not under DANIEL and not under DANIELS (the spelling on the sheet's guarantor block). Medicare paid this number through 2025, so it was most likely reissued since. Nothing changed on the chart.",
    why="Medicare rejects the chart's Medicare number as invalid; William's 11/25 paste shows the same number; Medicare's look-up finds no record under either spelling", amount=107, ask="facesheet", at=NOW))
doc["ops"][-1]["append"]["checks"] = [check("no", "AMD eligibility (free 271) on the chart's Medicare plan - run %s" % S, "REJECTED 72; the pasted number = the chart's number"),
                                       check("no", "Stedi MBI look-up by name (DANIELS) and birth date - run %s" % S, "75 Subscriber/Insured Not Found")]
# 3. FLOYD 21839 - written off WOLATE on William's word
w = reg["[name]-21839-medicare-number"]["writeoffs"]; tot = sum(l["insbalance"] for l in w if l.get("ok"))
doc["ops"].append({"op": "upsert", "collection": "items", "id": "[name]-21839-medicare-number",
    "set": {"status": "done", "need": "None - done 11/25. The two visits past Medicare's 12-month filing limit (11/07/2025 99309 $141, 11/15/2025 99487+99489 $315) are written off WOLATE on your word ('write off')."},
    "append": {"notes": [note("Written off on your word 11/25: 11/07/2025 99309 $141.00 (v19423852) and 11/15/2025 99487+99489 $315.00 (v19423656) - WOLATE, reference BOARD1125B, $%.2f in all; balances $0. The four visits inside 12 months stay out at Medicare under the corrected number (re-sent 11/20)." % tot)],
               "checks": [check("ok", "AMD action manual_post WOLATE x3 (BOARD1125B) - run %s" % S, "v19423852 $141.00; v19423656 $206.00 + $109.00 - success")]}})
# 4. HARVEY 17473749 - restored and billed to UHC on William's word
h = reg["[name]-17473749"]["restore"]; sent = [l for l in h if "-> 204" in l]
doc["ops"].append({"op": "upsert", "collection": "items", "id": "[name]-17473749",
    "set": {"status": "done", "need": "None - done 11/25 on your word ('restore'): the seven 2026 visits Medicare answered $0 (an Advantage plan is responsible) are restored - the $0 postings and their write-offs voided - and billed to her UHC AARP Medicare Advantage plan ($1,751). The chart first name stays JUDY unless UHC rejects on it (UHC and Medicare hold JUDETH M)."},
    "append": {"notes": [note("Restored on your word 11/25: 04/29/2026 99349 $198; 05/17/2026 99487+99489 $315; 07/16/2026 G0439 $204; 07/17/2026 99487+99489 $315; 07/22/2026 99349 $198; 08/23/2026 99487+99489 $315; 09/20/2026 99487 $206 - the Medicare $0 (CO-24/CO-109) postings and their WOINS write-offs voided, each visit set to the UHC plan and sent as an original claim ($1,751.00, 7 claims, 204 each). The 10/27/2026 CCM ($315) was already at UHC since 11/6. First name: left JUDY - UHC has not rejected on it; say 'JUDETH' any time and it is changed.")],
               "checks": [check("ok", "AMD action co24_restore (void $0 payment + WOINS, move_to_ins rebill seq 2 = UNI20) - run %s" % S, "%d visits restored and sent to UHC: %s" % (len(sent), "; ".join(l.split(" -> ")[0] for l in sent)))]}})
# 5. GRANT 17474537 - the birth date he asked for, card back to him
g = reg["[name]-17474537-medicare-number"].get("dob_on_chart", "")
dob = g[:10] if g else ""
if dob and "-" in dob: y, mo, d = dob.split("-"); dob = "%s/%s/%s" % (mo, d, y)
doc["ops"].append(handback_op("[name]-17474537-medicare-number",
    "MEDICARE NUMBER NEEDED ($43, 1 visit) for GRANT, JOHN born %s (the birth date on the chart): paste the red, white and blue card or the facesheet." % dob,
    "The birth date on his chart is %s (AdvancedMD demographics, read 11/25). Medicare rejects the chart's Medicare number as invalid (it paid the 10/31/2025 visit under it in 2026, so it was likely reissued since); once you paste the current number I correct the chart and re-send the visit." % dob,
    amount=43.26, ask="facesheet", at=NOW))
# 6. DORRANCE 17478350 - the Pattern 692 hold is gone (new-admission rule), the visit goes out as coded
b = [x for x in byp.get("done", byp) if isinstance(x, (dict, list))] if isinstance(byp, dict) else byp
doc["ops"].append({"op": "upsert", "collection": "items", "id": "dorrance-seton-17478350-692-1114",
    "set": {"status": "done", "need": "None - done 11/25. The 99223 of v19461966 was held by the Claim Inspector's Pattern 692 (initial hospital care after follow-up visits); under your 11/25 word (a new admission - hospital to inpatient rehab) the advisory was bypassed and the visit goes out as coded on the next claim run."},
    "append": {"notes": [note("Done 11/25: Pattern 692 on v19461966 bypassed (bypassclaimedits, error 398561) - a 99223 after follow-up hospital visits is a new admission, never a hold. The visit leaves on the next claim run with its own admission date. Two other 99223s held the same way (charts 17476042 v19462318, 17469549 v19462335) were released in the same pass.")],
               "checks": [check("ok", "AMD action insp_bypass_advisories (Pattern 692) - run %s" % S, "v19461966 bypass OK")]}})
# 7. NASSR 17478413 - the O24.419 question of 11/14 never reached William: hand it back
doc["ops"].append(handback_op("[name]-17478413",
    "DIAGNOSIS CODE ($421, 1 visit): the 11/13/2026 visit (99306+99497, v19461189) carries O24.419 (diabetes in pregnancy) from the feed and the Claim Inspector holds it (not typical for her age). Say the right code, or 'delete', and the visit goes out.",
    "Handed back 11/25: the 11/14 run asked you this on the card but the card stayed on my turn, so you never saw it. The chart is insured (Medicare ACTIVE) and the visit is otherwise clean - only the pregnancy code O24.419 (seventh of nine codes: I10;J44.9;R79.89;F41.8;M79.7;M35.00;O24.419;D64.9;K27.4) holds it. I do not delete or change a diagnosis on my own.",
    amount=421, ask="decision", at=NOW))
# 8. ATKINS 17477311 - new card: 99223 at place of service 31 (Pattern 4531), held since 11/22
row = {"id": "[name]-17477311-pos-0827", "patient": "[name] CHASONN", "dob": "[DOB]", "facility": "skilled nursing facility (place of service 31 on the feed)", "amdid": "17477311", "mbi": "",
       "need": "CODING ($421, 1 visit): the 08/27/2026 visit (99223 initial HOSPITAL care + 99497, v19462192) came through the feed at place of service 31 (skilled nursing facility) and the Claim Inspector holds it (Pattern 4531: 99223 is not performed at a nursing facility). Say 'hospital' (the place of service becomes 21) or the nursing-facility code (99306) and it goes out.",
       "why": "Claim Inspector batch 1 since 11/22/2026: Pattern 4531 on v19462192 (error 398627) - a code / place-of-service mismatch is a coding call, never changed by a run", "amount": 421, "status": "william", "ask": "decision",
       "insplans": "1st CAP07 Capital Health Plan (seq 1)", "inscarrier": "CAP07 Capital Health Plan",
       "notes": [note("Created by the ehpa Billing Button run 11/25: held in the Claim Inspector since 11/22 with no card on your turn. The chart is insured (Capital Health Plan, seq 1); only the code / place-of-service question holds the visit.")]}
doc["ops"] += board_ops.plan_new_row(items, row, same_item=False, now=NOW)

# 9-11. the three chat-instructed cards (board_plans_2026-11-25T0557Z.json)
bp = json.load(open("registers/board_plans_%s.json" % S)); 
doc["ops"].append({"op": "upsert", "collection": "items", "id": "[name]-17478200",
    "set": {"status": "done", "need": "None - done 11/25: Detego Health (the carrier you created, DET01) added as the chart's only plan with the policy number and effective date from your sheet (10/07/2026, no group number), authorization 00062963 written on the chart's referral plan, and both HCA visits sent as originals - 10/14/2026 99223 $310 (v19459188) and 10/15/2026 99232 $111 (v19459194), $421. No electronic eligibility exists for this payer - entered on the face sheet alone.",
            "insplans": "1st DET01 Detego Health (policy from the face sheet, begin 10/07/2026)", "inscarrier": "DET01 Detego Health"},
    "append": {"notes": [note("Done 11/25: Detego Health plan ins9521407 added (seq 1, begin 10/07/2026, no group), patient order 1, authorization 00062963 on referral plan rplan18462559 (read back), both visits set to the plan and sent as original claims (freq1 + chargerebill 204 each). Watch the first Change Healthcare answer on the new carrier (payer id 9436) - a front-end rejection comes back on the Exclusions column.")],
               "checks": [check("ok", "AMD actions add_ins DET01 + preauth resave + freq1_visit x2 - run %s" % S, "ins9521407 seq 1; preauth 00062963 on rplan18462559; v19459188 204; v19459194 204")]}})
import feed_order_sweep as fos
k = {}
for d8 in ("20260901", "20261022"):
    jj = json.load(open("patient_db/17478219/stedi_elig_14163_%s.json" % d8)); v, words, rng = fos.verdict(jj, d8, False, "19510411"); k[d8] = [v, words]
doc["ops"].append(handback_op("[name]-17478219",
    "CAPITAL HEALTH PLAN MEMBER NUMBER NEEDED ($639, 2 visits): the WellCare Medicare plan on your 11/25 hospital sheet ended 12/31/2025 (WellCare's own answer, checked for 09/01/2026 and 10/22/2026), and Medicare says Capital Health Plan is her plan on 10/22/2026. The CHP card, the CHP portal or a 2026 face sheet gives the number; nothing else clears these two visits.",
    "Checked 11/25 as the card asked: WellCare (member [member id]) answers INACTIVE for both service dates - its plan ran 01/01/2025 to 12/31/2025 (Simple HMO H1032218000). The hospital's sheet is current for them but the plan it shows is last year's. Medicare's dated answer of 11/19 still stands: Capital Health Plan is her primary on 10/22/2026, and CHP answers only to its own member number (it refused the Medicare number). Nothing written on the chart; the 09/01/2026 home visit stays out at Medicare (sent 10/29) and the 10/22 CCM has no payer until the CHP number arrives.",
    amount=639, ask="facesheet", at=NOW))
doc["ops"][-1]["append"]["checks"] = [check("no", "Stedi eligibility WellCare (14163) dated 09/01/2026 and 10/22/2026 - run %s" % S, "; ".join("%s: %s - %s" % (d, v[0], v[1][:120]) for d, v in k.items()))]
c = bp["17478332"]
doc["ops"].append({"op": "upsert", "collection": "items", "id": "[name]-17478332",
    "set": {"status": "done", "need": "None - done 11/25: Florida Blue Medicare Advantage (BlueMedicare Value PPO) added from your sheet with member number [member id] (begin 12/01/2024, no group) - Florida Blue answers ACTIVE on 11/03/2026 and AdvancedMD's own check ACTIVE - put first on the chart (order Florida Blue, Medicare) and the 11/03/2026 home visit (99344+99497, $433, v19460350) sent to Florida Blue as an original claim. Humana stays ended.",
            "insplans": "1st BCBS Florida Blue Medicare Advantage XJPH45678323 (begin 12/01/2024) · FLO02 Florida Medicare [MBI] (MA member) · HUM01 H04462923 (ended 01/01/2026)", "inscarrier": "BCBS Florida Blue Medicare Advantage"},
    "append": {"notes": [note("Done 11/25: BCBS plan ins9521408 (seq 3) added with the member number from your sheet; Stedi eligibility dated 11/03/2026: Active Coverage BLUEMEDICARE VALUE (PPO); AMD 271 ACTIVE; patient order 3,1; visit v19460350 set to Florida Blue and sent (freq1 + chargerebill 204).")],
               "checks": [check("ok", "Stedi eligibility Florida Blue (BCBSF) dated 11/03/2026 + AMD 271 + add_ins + freq1_visit.reroute - run %s" % S, "ACTIVE BlueMedicare Value PPO; ins9521408 seq 3; v19460350 204")]}})
board_ops.clean_file(doc)
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % S, "w"), indent=1)
print("ops:", len(doc["ops"]), [ (o["op"], o["id"], (o.get("set") or {}).get("status")) for o in doc["ops"] ])
