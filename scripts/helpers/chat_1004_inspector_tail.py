# PLAIN ENGLISH (chat session 10/4/2026, after the cascade): the new HCA charts released tonight now sit in the Claim Inspector with
# "Hospitalization From Date empty". Rule (Claims-Center skill): the admission date is the chart's most recent 99223 on/before the
# visit's date of service (within 45 days); it is written with updextrainsinfo per charge code and the visit is re-saved CMS-1500 (onhcfa=1),
# full-visit echo (void trap). A chart with NO 99223 (Herriot) is HELD - never guessed - and goes to William for the admission date.
# Also: Smythe Myra's 9/21 SNF visit has F02.80 (dementia in other diseases) listed FIRST - the inspector wants the underlying condition
# first (Pattern 20389), so the diagnosis ORDER is changed (same codes, F02.80 moved behind F20.0 / M06.9 / E78.5), nothing added or dropped.
# Usage: cd /home/claude/unbilled && python3 chat_1004_inspector_tail.py [--dry]
import sys, time
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, DRY, full_resave, set_hosp_date
import amd, resave
amd.login_cached()
L("== inspector tail (DRY=%s)" % DRY)
# (visit id, charge id for the echo, admission date, [charge codes])
HOSP = [
    ("19456840", "23368498", "10/01/2026", ["99223", "99497"]),   # PRIMROSE 10/01 admit
    ("19456831", "23368489", "10/01/2026", ["99233"]),
    ("19456895", "23368558", "10/01/2026", ["99223", "99497"]),   # MACFARLANE 10/01 admit
    ("19456847", "23368507", "10/01/2026", ["99233", "99497"]),
    ("19456898", "23368564", "09/30/2026", ["99223"]),            # TISDALE 9/30 admit
    ("19456868", "23368529", "09/30/2026", ["99232"]),
    ("19456900", "23368567", "09/28/2026", ["99223"]),            # SINGER 9/28 admit
    ("19456869", "23368530", "09/28/2026", ["99232"]),
    ("19456870", "23368531", "09/28/2026", ["99232"]),
]
for vid, cid, admit, codes in HOSP:
    if done("hospdate", vid): L("   v%s already done (register)" % vid); continue
    if DRY: L("   DRY v%s hospitalizationfrom %s codes %s + resave onhcfa=1" % (vid, admit, codes)); continue
    for code in codes:
        r = set_hosp_date(vid, code, admit); L("   v%s updextrainsinfo %s %s -> %s" % (vid, code, admit, "ok" if 'success="1"' in r or "<extins" in r else r[:160]))
    ok, msg = full_resave(cid, over={"onhcfa": "1"}); L("   v%s resave: %s %s" % (vid, ok, msg[:200]))
    rec("hospdate", vid, ok and (admit in msg), msg=msg[:200]); time.sleep(0.5)
# Smythe Myra: diagnosis order F20.0, F02.80, M06.9, E78.5 (F02.80 off the primary position)
cid = "23368114"; vid = "19456467"
if done("dxorder", vid): L("   v%s dx already reordered (register)" % vid)
else:
    new = "dcode1034544992 dcode1034545129 dcode1034545337 dcode1034544892"
    ok, msg = full_resave(cid, chg_over={"charge" + cid: {"diagcodes": new}}); L("   v%s dx reorder -> %s %s" % (vid, ok, msg[:200]))
    if not DRY: rec("dxorder", vid, ok, msg=msg[:200])
if not DRY:
    time.sleep(2)
    left = [r for r in A.inspector_rows() if r['vid'] in [h[0] for h in HOSP] + [vid]]
    L("   still listed: %s" % [(r['vid'], [e[1][:60] for e in r['errs']]) for r in left])
L("== done")
