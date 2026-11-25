# PLAIN ENGLISH (this run's Insurance Refresh Board update file, ehpa Billing Button run 2026-11-25T0435Z)
# Decides: nothing in AMD. Writes outbox/board_updates_2026-11-25T0435Z.json - one op per card this run read and worked: what was done
#   (from the run's own registers: board_wo / board_void / board_plans / va_stay_auth / mbi_candidate / dob_fix) and, where something
#   is still needed from William, the hand-back op (status william + need + note in ONE op, facesheets_needed.handback_op).
#   notes go in `append`, never in `set`; no `updated` anywhere (board_ops.clean_file); "asof" = when this run read the board.
# Never touches: AMD, the board's database, Drive. Usage: python3 board_file_1125_0435.py
import sys, json, datetime
sys.path.insert(0, "/home/claude/effinger-billing-backend/scripts/helpers")
import board_ops, facesheets_needed as fn
S = "2026-11-25T0435Z"; ASOF = "2026-11-25T04:42:00Z"
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SRC = "ehpa Billing Button run %s" % S
ops = []
def done(card, need, note, check=None):
    op = {"op": "upsert", "collection": "items", "id": card, "set": {"status": "done", "need": need},
          "append": {"notes": [{"who": "Claude", "text": note, "at": now}]}}
    if check: op["append"]["checks"] = [{"ok": check[0], "src": check[1], "result": check[2], "when": "11/25"}]
    ops.append(op)
def claude(card, need, note):
    ops.append({"op": "upsert", "collection": "items", "id": card, "set": {"status": "claude", "need": need},
                "append": {"notes": [{"who": "Claude", "text": note, "at": now}]}})
def back(card, need, note, amount=None, ask=None):
    ops.append(fn.handback_op(card, need, note, amount=amount, ask=ask, at=now))

done("[name]-17476912", "None - written off 11/25 on your word.",
     "Done on your 'write off' (11/25): the 6/22/2026 initial NF visit v19445941 - 99306 $256 + 99497 $133 = $389 - written off WONCS (reference BOARD1125). Both charges read back at $0 insurance and $0 patient balance.")
done("chp-pr242-check-4131654", "None - written off 11/25 on your word.",
     "Done on your 'write off' (11/25): every open line of the seven CHP PR-242 / CO-243 visits written off WONCS (reference BOARD1125) - chart 46678 v19442338 $315, v19448386 $204, v19452574 $206; chart 21491 v19459620 $206; chart 48008 v19423586 $315; chart 17474083 v19434037 $206; chart 17476942 v19459617 $206 = $1,658 on 9 charges. Each read back at $0 insurance and $0 patient balance.")
done("[name]-17477258-after-death", "None - voided 11/25 on your word.",
     "Done on your 'void' (11/25): on the 09/20/2026 99487 (v19455614, charge 23366962, $206) the WOINS write-off and the $0 DOD1120 line were voided, then the charge itself was voided (reads back void). The 07/28 and 08/23 visits, dated before the death, are untouched.")
done("[name]-17478470", "None - done 11/25.",
     "Done from your HCA sheet (11/25): Capital Health Plan Medicare HMO added (member number from your sheet, effective 11/17/2026, no group) - AMD's free 271 answers ACTIVE. Both visits sent to CHP as originals: v19461860 11/17 99223+99497 $443 and v19461854 11/18 99233 $160 ($603). The feed sweep's 'no claim can be made' for this chart is cleared.")
done("[name]-17478452", "None - done 11/25.",
     "Done from your HCA sheet (11/25): Capital Health Plan (CAP07) added with the member number on your sheet (effective 11/01/2026, no group) - AMD's 271 ACTIVE; chart order CHP first, Medicare second. v19461642 11/16 99223 $310 and v19461630 11/17 99232 $111 re-pointed to CHP and sent as originals ($421). The authorization number on the sheet is kept here in case CHP asks.")
done("[name]-17478455", "None - done 11/25.",
     "Done from your HCA sheet (11/25): Capital Health Plan (CAP07) added with the member number on your sheet (effective 11/09/2026, no group) - AMD's 271 ACTIVE; chart order CHP first, Medicare second. All seven hospital visits 11/16-11/22 (v19461640 99223 $310; v19461968, v19461853, v19461990, v19462060, v19462187, v19462331 99233 $160 each) re-pointed to CHP and sent as originals ($1,270). The authorization on the sheet is kept here in case CHP asks.")
done("lowry-fenwick-17475970-stay-1105", "None - sent to VA CCN 11/25.",
     "Done from your HCA sheet (11/25): VA CCN authorization VA0065278022 written on the visits of the 11/04/2026 admission and all 15 of them (11/04 99223+99497, 11/05-11/18 99233s) re-pointed to VA CCN (seq 1) and sent as originals - none goes to Medicare any more. One thing to know: AMD would not create a separate referral plan for this stay (it returns the existing plan whenever the referring provider is the same), so the number sits on the chart's main plan, which the unpaid 6/20-6/28 and 9/7-9/14 visits also point to - a later re-send of those would print this number; they need their own plan before any re-send.")
done("[name]-17474021-medicare-number", "None - done 11/25.",
     "Done (11/25): the Medicare number on your sheet is the one already on the chart, and Medicare rejects it (AAA 72) - Medicare's look-up by name, birth date and SSN found nothing. The secondary's own eligibility answer (BCBS, ACTIVE) lists her current Medicare number among her other payers; written on the chart, AMD's free check answers ACTIVE (Part A 2012, Part B 2015), so it stays. Both 2025 hospital visits were already paid by Medicare; their remaining $49.16 was sent to the BCBS secondary (v19416417 $15.41, v19416418 $33.75).",
     check=("ok", "AMD 271 on the Medicare plan with the corrected number", "ACTIVE"))
done("[name]-17473160-medicare-match", "None - done 11/25.",
     "Done on your answer (11/25): birth date corrected [DOB] -> 06/05/1927; AMD's free check on the Medicare plan answers ACTIVE (Part A/B since 06/1992 - his 65th birthday, so the date is right). The 02/28/2026 CCM (v19442323, 99487+99489, $315) re-sent to Medicare as an original.",
     check=("ok", "AMD 271 Medicare after the birth-date correction", "ACTIVE"))
done("hic[member id]", "None - nothing waiting.",
     "Checked your 11/25 sheet against the chart: the Medicare number and the Cigna member number on it are the ones on the chart's plans already (Medicare seq 1, Cigna seq 4; chart order 1,4). The September stay is at Cigna (paid); the 11/03 home visit 99344 went to Medicare 11/05 and waits on its answer. Nothing needed from you.")
done("carmody-norcott-17473431", "None - the current Medicare number is on the chart.",
     "Read 11/25: your TMH sheet still carries the old number (the one Medicare rejects). The chart already holds her reissued Medicare number - added by the 10/28 cascade - and AMD's free check answers ACTIVE for it tonight, so nothing is needed from you on the number. Since the 11/5 railroad re-route her home visits go to Railroad Medicare (RET01), which answers 51 'provider not on file' on the same number - a Palmetto RRB enrollment matter, listed in the run report, not a face-sheet ask.")
done("sikora-lorena-17474671", "None - paid.",
     "Read 11/25: both visits on this card are paid - v19423438 (11/13/2025 99344+99497) and v19423668 (11/15/2025 CCM), check 819988060. Nothing more to do; your 10/5 note was the card's own text.")
done("[name]-17477225", "None - posted.",
     "Read 11/25: the IdeaLife $16.93 is posted on v19451940 (check 0800250945) beside Medicare's payment. Thank you for adding the carrier.")
done("forsyth-delphine-17477828", "None - both charts billed and paid.",
     "Read 11/25 on your 'fix the new charts and submit': both charts are right and every visit is paid - this chart's 9/18-9/24 stay by UHC; the duplicate chart 17477976's 9/28 visit by UHC and its 10/01-10/14 visits by Medicare. Nothing is waiting. The duplicate chart still exists in AMD (a merge is a UI step) - only if you want one chart.")
done("kirkbride-davin-17475338", "None - done.",
     "Read 11/25 on your 'go': already done by an earlier run - the Medicare contractual $153.50 is posted on v19431100 (check 819814877) and the chart order is Medicare first, Florida Blue second. Nothing is open for you.")
claude("[name]-17474258", "Claude (watching): UHC's answer on v19419622 (10/08/2025) and v19422181 (10/22/2025).",
       "Read 11/25 against your rule: v19419032 (10/01) and v19420346 (10/14) were answered and settled (written off); v19419622 (10/08) and v19422181 (10/22, $141 each) have no answer yet. Nothing has come back 'subscriber not found', so the member id stays as it is; when an answer arrives the run applies your rule (fix id and resend, or WOLATE on CARC 29 - timely-filing watch).")
back("[name]-20752-medicare-number",
     "MEDICARE NUMBER NEEDED ($1,225, 6 visits) for the Corvin Catalano born [DOB] (chart 20752) - the sheet you pasted is the younger Corvin Catalano's (born [DOB]).",
     "Read 11/25: the sheet you pasted (born [DOB], disabled, Sunshine Medicaid) belongs to the OTHER Corvin Catalano - chart 12182776 - and that chart already carries both numbers on it, so nothing changed there. This card's patient is born [DOB] (chart 20752); his chart's Medicare number differs from the younger man's by one character and Medicare rejects it - it may have been copied from the other chart. His own card or facesheet is still needed.",
     amount=1225, ask="facesheet")
back("[name]-17478013",
     "VA CCN authorization number for the FIRST admission, 10/05-10/12/2026 (8 visits, $1,430). The 10/21-10/31 stay is done.",
     "Done from your sheet (11/25): authorization VA9011260694 written on the referral plan of the 10/21-10/31 stay and those 11 visits (v19458908 ... v19459723, $1,910) re-sent to VA CCN as originals. The 10/05-10/12 visits belong to the first admission and still need that admission's own number - until then they are not re-sent. Also: tonight's run tried to give the second stay its own referral plan and AMD created a blank plan with the third referring provider instead; it is now the chart's MAIN referral plan (nothing points to it). In AMD: chart 17478013 > Referral Plans > open rplan18462365 (Effinger, carries the auth) > tick Main, Save - or delete the blank one.",
     amount=1430, ask="facesheet")
back("karnes-chester-dougal-denials",
     "YOUR CALL ($421): the 4/14-4/15/2026 visits written off 9/9 - say 'reverse and resend' or 'leave'.",
     "Read 11/25: the chart's BCBS plan carries exactly the member number on your sheets (X3LM68527616, no group) - nothing to correct. The November stay is at BCBS: 16 visits 11/07-11/21 sent 11/19-11/23; the 11/22 visit goes with the next claim run. What is left is your April question.",
     amount=421, ask="decision")

doc = {"schema": "irb-board-updates/1", "source": SRC, "created": now, "asof": ASOF, "ops": ops}
board_ops.clean_file(doc)
json.dump(doc, open("/home/claude/unbilled/outbox/board_updates_%s.json" % S, "w"), indent=1)
print("ops", len(ops), "->", "/home/claude/unbilled/outbox/board_updates_%s.json" % S)
