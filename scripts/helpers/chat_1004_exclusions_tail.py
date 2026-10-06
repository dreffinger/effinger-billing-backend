# PLAIN ENGLISH (chat session 10/4/2026): the 16 Exclusions (payer/clearinghouse rejections, runs 9/18-10/3).
#  - LASCELLES pat17477498 v19455608 (9/20 CCM to Florida Blue, ALF POS 13): FB rejected 'acute ischemic stroke dx in an outpatient setting'
#    -> standing rule: I63.9 outside POS 21 becomes I69.30 (dcode1034545425); full-echo resave, frequency-1 rebill to FB (seq 1), complete.
#  - CARDWELL pat17472396 v19444180 (4/3/2026 99309): the 9/30 re-send went out as a frequency-7 corrected claim with no Medicare ICN and the
#    clearinghouse bounced it (PCLM0500 / PREF0201) -> re-send as frequency 1 (Medicare was the payer in April; plan ended 4/30), complete.
#  - Florida Blue secondaries PREF0283 'missing payer doc control num' (DALRYMPLE, WALDRON, MEDHURST - Medicare paid, FB Medigap/PPO second):
#    William's crossover-wait rule (bcbs-secondary-dcn-0910, 9/12): clear the exclusion, leave the balance for the Medicare->FB crossover.
#  - Duplicate-claim rejections (ORWELL Humana, MORROW x2 Humana): complete straight off, no rebill (skill rule).
#  - ARKWRIGHT (UHC member-pick on the AARP-as-primary claim; row done, claim already re-sent to Medicare) and PELLAM DAVIN (Sunshine 'member
#    not valid'; row says re-routed to FCC 9/28): completed - the fix already happened on the chart.
#  - HODGSON x4 / POULTER-ELLERY x2 (AARP Medigap 'subscriber not found' on the 9-digit id discovery returned): the question goes to the board
#    rows (full AARP member number needed); the exclusion rows are completed so the column reads clean - nothing re-sent.
# Usage: cd /home/claude/unbilled && python3 chat_1004_exclusions_tail.py [--dry]
import sys, time, re
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, DRY, full_resave
import amd, resave, freq1_visit
amd.login_cached()
L("== exclusions tail (DRY=%s)" % DRY)
# 1. Lascelles dx swap + rebill
cid, vid = "23366951", "19455608"
if done("lascelles_dx", vid): L("   lazarus already done")
else:
    vis, pat, allc = resave.visit_charges(cid); dx = allc[0].get("diagcodes")
    new = dx.replace("dcode1034545006", "dcode1034545425"); L("   lazarus dx %s -> %s" % (dx, new))
    ok, msg = full_resave(cid, chg_over={"charge" + cid: {"diagcodes": new}}); L("   lazarus resave -> %s %s" % (ok, msg[:200]))
    if not DRY and ok:
        time.sleep(0.8); r1 = freq1_visit.run(vid, cid, 1); L("   lazarus freq1 seq 1 -> %s" % r1); rec("lascelles_dx", vid, "FAULT" not in str(r1) and "BLOCKED" not in str(r1), msg=str(r1)[:160])
# 2. Cardwell freq-1 to Medicare
cid, vid = "23352860", "19444180"
if done("cardwell_f1", vid): L("   culpepper already done")
elif DRY: L("   DRY culpepper freq1 seq 1")
else:
    r1 = freq1_visit.run(vid, cid, 1); L("   culpepper freq1 seq 1 -> %s" % r1); rec("cardwell_f1", vid, "FAULT" not in str(r1) and "BLOCKED" not in str(r1), msg=str(r1)[:160])
# 3. complete every open exclusion row
RUNS = {"1700209": [("19448997", "19448997F")],
        "1700233": [("19445180", "19445180D"), ("19446185", "19446185D"), ("19446287", "19446287D"), ("19447326", "19447326D"), ("19448476", "19448476E"), ("19448899", "19448899D"), ("19449437", "19449437D"), ("19455608", "19455608A")],
        "1700235": [("19455357", "19455357A")],
        "1700244": [("19455782", "19455782C"), ("19456212", "19456212B")],
        "1700257": [("19454667", "19454667B")],
        "1700260": [("19444180", "19444180C")],
        "1700263": [("19452564", "19452564D")],
        "1700265": [("19455220", "19455220B")]}
for run, vs in RUNS.items():
    if DRY: L("   DRY hideexclusions run %s %s" % (run, vs)); continue
    child = "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in vs)
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    L("   run %s hide %d -> %s" % (run, len(vs), "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:200])))
    rec("hideexcl", run, "Fault" not in r, msg=r[:120]); time.sleep(0.4)
if not DRY:
    ex = amd.post(amd.msg("getclaimexclusionclaimruns", "claimsreports", {}))
    L("   exclusions totalcount after: %s" % re.findall(r'totalcount="(\d+)"', ex)[:1])
L("== done")
