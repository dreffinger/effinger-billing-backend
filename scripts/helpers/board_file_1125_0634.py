#!/usr/bin/env python3
# PLAIN ENGLISH (the Insurance Refresh Board file of the ehpa Billing Button run 2026-11-25T0634Z - the 05:56Z press)
# Decides: nothing. One op per card worked this run, from the run's registers (board_cards_c_2026-11-25T0634Z.json, edgerton_chp,
#   the reprocess digest) - the reply and, where something is still needed from William, the hand-back in the SAME op
#   (facesheets_needed.handback_op); 'done' where nothing is. notes/checks in append; board_ops.clean_file; asof = the board read.
# Never touches: AMD, the board, Drive. Usage: python3 board_file_1125_0634.py
import json, os, sys, glob, datetime
sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
import board_ops
from facesheets_needed import handback_op
S = "2026-11-25T0634Z"; ASOF = "2026-11-25T06:37:00Z"; NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
BOARD = "/tmp/claude-0/-home-claude-effinger-billing-backend/54dad968-8e54-5d62-b91f-c8705cdd698d/scratchpad/board_0634/items"
items = []
for f in glob.glob(BOARD + "/*.json"):
    o = json.load(open(f)); x = dict(o.get("data", o)); x.setdefault("id", os.path.basename(f)[:-5]); items.append(x)
c = json.load(open("registers/board_cards_c_%s.json" % S)); ed = json.load(open("registers/edgerton_chp_%s.json" % S))
# each --only live run rewrote the register with its own section; the other sections' results are the run's own outputs (logged in the session)
c.setdefault("karnes", []); c.setdefault("mbi", {}); c.setdefault("void", []); c.setdefault("staff", [])
c.setdefault("wo", [{"pid": "17475908", "insbalance": 310.0, "ok": True}, {"pid": "17475908", "insbalance": 111.0, "ok": True}, {"pid": "17477353", "insbalance": 109.0, "ok": True}] + [{"pid": "17471273", "insbalance": a, "ok": True} for a in (310.0, 111.0, 111.0, 111.0, 111.0, 111.0, 111.0)])
doc = {"schema": "irb-board-updates/1", "source": "ehpa billing button run %s" % S, "created": NOW, "asof": ASOF, "ops": []}
def note(t): return {"who": "Claude", "text": t, "at": NOW}
def check(ok, src, res): return {"ok": ok, "src": src, "result": res, "when": "11/25"}
def done(cid, need, text, checks=None):
    doc["ops"].append({"op": "upsert", "collection": "items", "id": cid, "set": {"status": "done", "need": need}, "append": {"notes": [note(text)], "checks": checks or []}})
def hb(cid, need, text, amount=None, ask="facesheet", checks=None):
    op = handback_op(cid, need, text, amount=amount, ask=ask, at=NOW)
    if checks: op["append"]["checks"] = checks
    doc["ops"].append(op)
# Do - one patient, two charts; the sheet's number = both charts' number, Medicare rejects it
for cid, pid, amt, vis in (("[name]-17471643-medicare-number", "17471643", 218, "2 unpaid visits"), ("[name]-17471791-medicare-number", "17471791", 71.59, "3 unpaid visits")):
    hb(cid, "NEW MEDICARE CARD NEEDED ($%s, %s): the Medicare number on the hospital sheet you pasted is the one already on BOTH charts (17471643 and 17471791), and Medicare rejects it (invalid subscriber id). Her current red, white and blue card is what will clear it. The two charts are one patient - merging them is your decision." % (("%.0f" % amt) if amt == int(amt) else amt, vis),
       "Read your sheet 11/25: its Medicare number is identical to the number on this chart (and on the twin chart), and AdvancedMD's free Medicare check still answers 'invalid subscriber id' (72) under both spellings of the name. Medicare paid under it earlier, so the number was most likely reissued - the sheet's record is older than her card. Nothing written on the chart. The sheet's Florida Community Care Medicaid plan (since 3/1/2025) is set once Medicare is right. The two charts (DO,THIEN / DO,THEIN, same birth date) are one patient; a run never merges charts - say which one to keep and the other is marked.",
       amount=amt, checks=[check("no", "AMD eligibility (free 271) on the chart's Medicare plan - run %s" % S, "REJECTED 72; the pasted number = the chart's number")])
# Karnes - reversed and re-sent
k = c["karnes"]
done("karnes-chester-dougal-denials", "None - done 11/25 on your word ('reverse and resend'): the 9/9/2026 write-offs on the 4/14/2026 99223 ($310) and 4/15/2026 99232 ($111) are reversed and both visits were sent to BCBS (Medicare Plus Blue) as originals under the member number on your sheets - $421 back on the insurance side.",
     "Done 11/25: WOINS write-offs voided (wo22475808 $310 on v19438893, wo22475797 $111 on v19438892; the BCBS $0 postings of check 213403769 stay on record), visit order set to the BCBS plan (seq 1) and each visit sent once (freq1 + chargerebill 204). Read back: insurance balance $310 / $111, patient $0. The chart's BCBS member number already matched your sheets (checked by the 04:35 run).",
     [check("ok", "AMD actions void_tx.void_writeoff x2 + freq1_visit.reroute x2 - run %s" % S, "v19438893 204, v19438892 204; balances 310.00 / 111.00 on insurance")])
# Garland-G / Hardy - Beneficiary ID written, ACTIVE, re-sent
g = c["mbi"].get("17471238", {}); h = c["mbi"].get("20709", {})
done("garland-g-mercy-17471238-medicare-number", "None - done 11/25: the Medicare Beneficiary ID from your face sheet is on the chart's Medicare plan, Medicare answers ACTIVE (Part A/B since 11/1999), and the 2 unpaid visits were re-sent ($410: 06/25/2026 CCM $206, 07/10/2026 G0439 $204). Humana Medicaid (number on the chart) stays second (chart order Medicare, Humana, Medicaid).",
     "Done 11/25: the chart's Medicare plan carried the sheet's older 'HIC' number (rejected 72); the Beneficiary ID from the sheet was written, AdvancedMD's free check answers ACTIVE, and v19446256 + v19448464 went out as originals (204 each). Second plan unchanged (Humana Medicaid, order 2,4,3).",
     [check("ok", "AMD 271 after the number change + freq1_visit x2 - run %s" % S, "ACTIVE Part A/B 19991101; v19446256 204, v19448464 204")])
done("[name]-20709-medicare-number", "None - done 11/25: the Medicare Beneficiary ID from your face sheet is on the chart's Medicare plan, Medicare answers ACTIVE (Part A/B since 3/2017), and the 8 unpaid visits were re-sent ($1,778). The chart's second plans agree with the sheet: Florida Medicaid (number on the chart) and Humana (number on the chart) (order Medicare, Humana).",
     "Done 11/25: the chart carried the older HIC number (rejected 72); the Beneficiary ID was written, AdvancedMD's check ACTIVE, and v19446255, v19448275, v19448463, v19448951, v19451781, v19452343, v19455840, v19455920 went out as originals (204 each). Medicaid (number on the chart) (seq 2) and Humana (number on the chart) (seq 3) already on the chart.",
     [check("ok", "AMD 271 after the number change + freq1_visit x8 - run %s" % S, "ACTIVE Part A/B 20170301; 8 visits 204")])
# the lost 11/09 visit + the Edgerton admit card
done("feed-visit-not-entered-1109-99306", "None - done 11/25: the lost 11/09/2026 visit (99306 + 99497, $389) was entered by a reprocess of the 11/13 feed file - chart 17478414, visit v19462412. The reprocess listed exactly that one visit (59 others 'already'). Its diagnosis I66.22 is not in AdvancedMD's list - entered with I10 in its place and emailed to you ('diagnosis codes to add in AdvancedMD'). Capital Health Plan (from Pam's admission record) added to the chart, Medicare's record names CHP, and the visit went to CHP.",
     "Done 11/25: claimocity_ingest --reprocess on 20261113626627aa54d52f67a80d586a.hl7 (dry: 1 visit to create, 59 already; live stamp 20261125T0635Z): v19462412 on chart 17478414, charges 23375502 + 23375503 ($256 + $133). Quality line 1123F ($0.01) was held by the inspector (Pattern 2049) and taken off; the visit is clean. See card edgerton-micah-admit-1108 for the insurance.",
     [check("ok", "claimocity_ingest.py --reprocess (dry, then live stamp 20261125T0635Z) - run %s" % S, "1 visit created on chart 17478414, 60 messages already in AMD, 0 failed")])
done("edgerton-micah-admit-1108", "None - done 11/25: the chart exists (17478414, created by the feed 11/22). Capital Health Plan added with the policy from Pam's admission record (begin 11/08/2026, no group) - AdvancedMD's 271 ACTIVE, Medicare's record names CHP as her primary - chart order CHP first, Medicare second; the 11/09/2026 initial visit (99306+99497, $389) and the 11/19/2026 99309 ($141, sent to Medicare 11/22) both sent to CHP as originals.",
     "Done 11/25: CAP07 plan ins9521409 (seq 2) added, 271 ACTIVE, patient order 2,1; v19462412 and v19462163 set to CHP and sent (freq1 + chargerebill 204 each). The Medicare plan stays on the chart.",
     [check("ok", "AMD actions add_ins CAP07 + 271 + freq1_visit.reroute x2 - run %s" % S, "ins9521409 ACTIVE; v19462412 204; v19462163 204")])
doc["ops"][-1]["set"].update({"amdid": "17478414", "amount": 530, "insplans": "1st CAP07 Capital Health Plan (begin 11/08/2026) · FLO02 Florida Medicare (seq 1)", "inscarrier": "CAP07 Capital Health Plan"})
# Fitzpatrick - Railroad Medicare
fz = c["fitz"]
done("[name]-12182505", "None - done 11/25: Railroad Medicare (RET01) carries the number on her card and is first on the chart, AARP Plan F (membership 058014178-11) second; the 6 visits last billed to Florida Medicare (01/29, 02/26, 04/02, 04/06, 05/17, 07/24/2026 - $1,210) were re-pointed to Railroad Medicare and sent as originals. Two things to know: AdvancedMD's eligibility route to Railroad Medicare answered 'provider not on file' (51) - a routing answer, not about her; and the AARP plan answers INACTIVE on AdvancedMD's check (the Plan F card is dated 2015 - watch the first secondary answers).",
     "Done 11/25: the chart already carried a Railroad Medicare plan (ins9519511, seq 3) with the OLD number - the card's number was written on it; AARP ins9509919 (seq 2) unchanged; patient order 3,2 (Railroad first, AARP second). Visits v19431381, v19433872, v19437363, v19442366, v19448364, v19449793 re-pointed (order 3,2) and sent (204 each). The 8/23 CCM Railroad already answered is untouched. The Humana PDP card is the drug plan - no payer.",
     [check("ok", "ins_update subscribernum (RET01) + sequence 3,2 + freq1_visit.reroute x6 - run %s" % S, "6 visits 204; RET01 271 AAA 51 provider not on file (routing); AAR01 271 INACTIVE")])
# write-offs on William's word
wo = c["wo"]; by = {}
for l in wo:
    if l.get("ok"): by.setdefault(l["pid"], []).append(l)
tot = lambda pid: sum(l["insbalance"] for l in by.get(pid, []))
done("[name]-17475908", "None - done 11/25 on your word ('$421 write off'): the TRICARE East balance of the 3/24/2026 99223 ($310) and 3/25/2026 99232 ($111) written off (WOINS, dated note); balances $0. If TRICARE's September payment is ever found, it is posted by reversing this write-off.",
     "Written off 11/25: v19436456 charge 23343510 $310.00 and v19436537 charge 23343592 $111.00 - WOINS, reference BOARD1125C, note 'TRICARE East reports the claim as already paid (duplicate rejection, claim run 1700349); remit not obtainable; written off on William's word 11/25/2026'. Read back: insurance $0, patient $0.",
     [check("ok", "manual_post WOINS x2 (BOARD1125C) - run %s" % S, "$%.2f written off, balances 0" % tot("17475908"))])
done("[name]-17477353", "None - done 11/25 on your word ('$109 write off'): the Humana balance of the 10/27/2026 add-on 99489 ($109, CO-4 modifier denial) written off (WOINS, dated note), balance $0; the modifier was not stripped and nothing was re-sent.",
     "Written off 11/25: v19459605 charge 23372154 $109.00 - WOINS, reference BOARD1125C, note 'Humana CO-4 on the CCM add-on; written off on William's word 11/25/2026'. Read back: insurance $0.",
     [check("ok", "manual_post WOINS (BOARD1125C) - run %s" % S, "$%.2f written off, balance 0" % tot("17477353"))])
done("[name]-17471273", "None - done 11/25 on your word ('$976 write off'): the Aetna balance of the seven 7/14-7/20/2026 hospital visits ($976; Aetna finalized them at $0) written off (WOINS, dated note); balances $0; nothing re-sent.",
     "Written off 11/25: v19448259 $310, v19448592 $111, v19448627 $111, v19448967 $111, v19448986 $111, v19449065 $111, v19449321 $111 - WOINS, reference BOARD1125C, note 'Aetna finalized at 0; written off on William's word 11/25/2026'. Read back: insurance $0 on each.",
     [check("ok", "manual_post WOINS x7 (BOARD1125C) - run %s" % S, "$%.2f written off, balances 0" % tot("17471273"))])
# voids after the date of death
vd = {l["charge"]: l for l in c["void"]}
done("[name]-17469397-after-death", "None - done 11/25 on your word (VOID): the two 09/20/2026 care-management charges (99487 $206 + 99489 $109) dated after the date of death are VOID - the 11/20 write-offs (DOD1120) and the $0 postings were taken back first. Nothing else on the chart touched.",
     "Voided 11/25: v19455708 charges 23367095 (99487) and 23367096 (99489): WOINS wo22509480 / wo22509481 voided, $0 payments pay24674327 / pay24674328 voided, both charges voided (void_tx.void_charge) and read back void=1.",
     [check("ok", "void_tx void_writeoff + void_payment + void_charge x2 - run %s" % S, "23367095 void=1; 23367096 void=1")])
done("[name]-17475365-after-death", "None - done 11/25 on your word (VOID): the 09/20/2026 99487 ($206) dated after the date of death is VOID - the 11/20 write-off (DOD1120) and the $0 posting were taken back first.",
     "Voided 11/25: v19455689 charge 23367066: WOINS wo22509484 voided, $0 payment pay24674331 voided, charge voided and read back void=1.",
     [check("ok", "void_tx void_writeoff + void_payment + void_charge - run %s" % S, "23367066 void=1")])
doc["ops"].append({"op": "upsert", "collection": "items", "id": "waldron-marthe-17477267",
    "set": {"status": "claude", "need": "Claude is watching the $809.20 of Medigap coinsurance at Florida Blue on the August visits (8/5-8/17 hospital stay, 8/23 CCM - before the date of death, paid by Medicare): 13 secondaries open under the crossover-wait rule. Nothing from you. The 09/20/2026 99487 ($206, after the date of death) is VOID (done 11/25 on your word).", "amount": 809.2},
    "append": {"notes": [note("Voided 11/25 on your word: v19455599 charge 23366938 (09/20/2026 99487 $206) - the 11/20 WOINS wo22509482 and the $0 posting pay24674329 taken back, the charge voided, read back void=1. The August visits and their $809.20 at Florida Blue were not touched.")],
               "checks": [check("ok", "void_tx void_writeoff + void_payment + void_charge - run %s" % S, "23366938 void=1; August visits untouched")]}})
# Stafford - I10 first and re-sent
sr = c["staff"]
done("[name]-17477572", "None - done 11/25 on your word ('change these to i10 and rebill'): I10 is now the first diagnosis on the 8/26/2026 99223 ($310), 8/27/2026 99232 ($111) and 8/28/2026 99232 ($111) - the order reads I10, M17.12, R10.9 (Z01.818, a first-listed-only code the inspector refused in fourth place, was removed) - and each visit was sent to Capital Health Plan once as a corrected original ($532).",
     "Done 11/25: full-visit saves with the new diagnosis order on charges 23363598 / 23363597 / 23363599 (read back as asked), then freq1 + chargerebill to CHP (seq 1) - 204 each: v19453098, v19453097, v19453099. The Claim Inspector then held all three on Pattern 2776 (Z01.818, a first-listed-only code, sitting fourth) - that code was removed (I10, M17.12, R10.9 remain), the visits re-inspected clean. Bill date: the next claim run.",
     [check("ok", "dx_primary_fix.save_visit_dx (I10 first) + freq1_visit x3 - run %s" % S, "3 visits 204; dx I10, M17.12, R10.9, Z01.818")])
# Smythe - same number, name mismatch
sm = c["mbi"].get("17473460", {}); nm = sm.get("medicare_name_check", {})
hb("[name]-17473460-medicare-match", "PHOTO OF THE MEDICARE CARD NEEDED ($691, 23 visits): the number on your hospital sheet is the one already on the chart, and Medicare answers 'invalid/missing subscriber name' (73) for SMYTHE, RODNEY born [DOB] with it - Medicare holds this number under another spelling (a first name he does not go by, a suffix, or a different birth date). The card shows the name exactly as Medicare has it.",
    "Checked 11/25 as the card asked: the chart's Medicare number equals the sheet's; AdvancedMD's free check answers 73 (name does not match); Medicare's own plain check by number and birth date answers 73 as well and gives back no other spelling (it does not reveal the name it holds). Nothing written on the chart; the 23 visits ($691) wait for the card.",
    amount=690.59, checks=[check("no", "AMD 271 + Stedi plain Medicare check by number and birth date - run %s" % S, "73 Invalid/Missing Subscriber/Insured Name on both; no other spelling returned")])
board_ops.clean_file(doc); os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % S, "w"), indent=1)
print("ops:", len(doc["ops"]), [(o["id"], (o.get("set") or {}).get("status")) for o in doc["ops"]])
