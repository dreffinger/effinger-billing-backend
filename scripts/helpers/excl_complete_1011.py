# PLAIN ENGLISH (complete one Exclusions row whose visit was re-sent this run - 1 AM ET 10/11/2026 run 2026-10-11T0510Z)
# Decides: nothing new - the standing rule "complete every exclusion whose visit was re-sent this run". Claim run 1700286 row
#   19456319B (chart 17477516, Florida Blue Medigap secondary, PREF0283 missing payer doc control number): the visit's 99344 was
#   recoded 99349 and re-sent to Medicare this run (recode_99349_1011.py), so the secondary claim is rebuilt after Medicare
#   answers; the stale row is completed with hideexclusions hide=-1. Nothing is rebilled here.
# Never touches: charges, payments, write-offs, claims, any other row.
#   python3 excl_complete_1011.py          # dry
#   python3 excl_complete_1011.py --live   # register registers/excl_complete_2026-10-11T0510Z.json
import amd, json, re, sys
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"; RUN = "1700286"
ROWS = [("19456319", "19456319B")]
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "run": RUN, "rows": ROWS}
lst = "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in ROWS)
if LIVE:
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
    reg["hide_result"] = re.sub(r"\s+", " ", x[:300]); print("hideexclusions ->", reg["hide_result"])
else: print("DRY hideexclusions run %s %s" % (RUN, lst))
json.dump(reg, open("registers/excl_complete_%s.json" % S, "w"), indent=1)
