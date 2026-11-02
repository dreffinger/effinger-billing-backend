# PLAIN ENGLISH (Re-inspect the 10/22/2026 99309 of chart 17471793 after the CCM re-date, William 11/2/2026 "move 10/22 CCM to 10/21")
# Decides: nothing new. The CCM visit moved to 10/21, so the inspector's CCI hold (Pattern 24078, suitedate 10/30) on the 99309 visit
#   v19459299 is stale: a full-visit echo resave (same order 2,4, force=1) makes AMD re-run the inspector; the batch is re-listed, any
#   ADVISORY left (20657 timely, 35790 add-on, 4426 mod-25, 27261 AWV, 4310, 11256) is bypassed with the fresh ids, a CCI / missing-data
#   error stays; when the visit is clean its Unbilled row 'Unresolved Claim Inspector errors' is released (hideunbillavisits hide=-1).
# Never touches: other visits. --live writes.  Usage: python3 nesbit_inspect_1102.py [--live]
import sys, re, time, json
sys.path.insert(0, "/home/claude/unbilled")
import amd, move_to_ins
LIVE = "--live" in sys.argv; VID = "19459299"; CID = "23371744"
ADVISORY = {"20657", "35790", "4426", "27261", "4310", "11256", "7011", "3429", "35777", "33799"}
amd.login_cached()
if LIVE: print("resave:", move_to_ins.move(CID, "2,4", rebill=False)); time.sleep(3)
r = amd.post(amd.msg("getclaiminspectorcharges", "claimsreports", {"batchid": "1", "nocookie": "1"}, ""))
blk = re.search(r'<visit id="%s".*?</visit>' % VID, r, re.S)
errs = re.findall(r'<error id="(\d+)" number="\d+" name="\[Pattern (\d+)\][^"]*" data="([^"]*)" suite="[^"]*" suitedate="([^"]*)"', blk.group(0)) if blk else []
print("inspector rows for v%s:" % VID, errs or "none (clean)")
left = [e for e in errs if e[1] not in ADVISORY]
adv = [e[0] for e in errs if e[1] in ADVISORY]
if adv and LIVE:
    rr = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (VID, "".join('<claimedit id="%s"/>' % e for e in adv))))
    print("bypass", adv, "->", 'success="1"' in rr)
if not left and LIVE:
    rr = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"nocookie": "1"}, '<visitlist><visit id="%s" hide="-1"/></visitlist>' % VID))
    print("release unbilled v%s ->" % VID, 'success="1"' in rr, re.sub(r"\s+", " ", rr[100:260]))
else:
    print("still held:", left)
