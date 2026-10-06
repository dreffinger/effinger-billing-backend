# PLAIN ENGLISH (chat session 10/4/2026, after the main waves): the three "prior payor" rows left in Unbilled.
#  - pat17470743 v19441047 (05/01/2026 99309): Medicare paid 5/26/2026, the $16.93 coinsurance went to FL Medicaid as a crossover and
#    Medicaid answered $0 twice -> William's rule: a Medicaid crossover that pays $0 on Medicare coinsurance is contractual -> WOCAID2ND, release.
#  - pat23391 v19392347 (10/24/2024 99233+G0316): Medicare paid the 99233 (secondary balance $23.62 billed to Florida Blue 9/21); the G0316 primary
#    claim went to Medicare 9/10/2026 and has no answer yet -> nothing to bill today -> release (it comes back by itself if still blocked).
#  - pat17473343 v19442414 (CCM re-dated 05/31/2026): UHC (UNI20) covered May 2026 (plan ends 05/31/2026) and the $0 CO-151 posting is UHC's,
#    so the May monthly total belongs to UHC, not Medicare -> insorder 1,3 (UHC, Sunshine), freq-1 to seq 1, release.
# Usage: cd /home/claude/unbilled && python3 chat_1004_unbilled_tail.py [--dry]
import sys, time
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, DRY
import move_to_ins, freq1_visit, amd
amd.login_cached()
L("== unbilled tail (DRY=%s)" % DRY)
# 1. Garrow
ok = A.writeoff("garrett", "23348845", "MCAD", 16.93, "WOCAID2ND",
                "Medicaid crossover paid 0.00 on the Medicare coinsurance (Medicare paid 5/26/2026; Medicaid 0.00 postings 6/1 and 9/12/2026) - contractual per William's rule; chat 10/4/2026")
L("   garrett writeoff -> %s" % ok)
# 2. trosclair May CCM -> UHC
cid = "23350510"; vid = "19442414"
if done("uhc_may", vid): L("   trosclair already moved (register)")
elif DRY: L("   DRY move_to_ins.move(%s, '1,3', rebill_seq=1)" % cid)
else:
    r = move_to_ins.move(cid, "1,3", rebill_seq=1)
    L("   trosclair v%s -> UHC seq 1: %s" % (vid, str(r)[:300]))
    rec("uhc_may", vid, "FAULT" not in str(r) and "BLOCKED" not in str(r) and "500" not in str(r)[:40], msg=str(r)[:200])
# 3. release the three
if not DRY:
    time.sleep(1.0)
    L("   release -> %s" % A.release_unbilled(["19441047", "19392347", "19442414"]))
L("== done")
