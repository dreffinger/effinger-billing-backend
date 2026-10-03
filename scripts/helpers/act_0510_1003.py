# PLAIN ENGLISH (1 AM ET 10/3 slot, run 2026-10-03T0510Z): (1) releases the three 'A payment from the prior payor is required'
# Unbilled rows whose primary claim is out and unanswered (rule b - they re-queue on their own): v19392347 (G0316 at Medicare
# since 9/10, 99233 coinsurance at Florida Blue), v19441047 (Medicare paid 5/26, $16.93 coinsurance at Medicaid secondary),
# v19442414 (CCM at Medicare since 9/5; the $0 line is UHC's wrong-payer answer). (2) ERA step 5(a)-(b): release expired ERA
# locks, list GET /api/era/checks (count + dollars), cache checkdetails for every unposted check into era_details/.
# Never touches: payments, write-offs, claim rebills.
import amd, era_post, json, os, time, sys
amd.login_cached()
rel = ["19392347", "19441047", "19442414"]
r = amd.post(amd.msg('hideunbillablevisits', 'claimsreports', {'nocookie': '1', 'hide': '-1'}, '<visitlist>%s</visitlist>' % ''.join('<visit id="%s"/>' % v for v in rel)))
print("RELEASE", rel, "ok" if "Fault" not in r else r[:300])
try:
    print("LOCKS", str(era_post.locks(""))[:200])
except Exception as e:
    print("locks:", repr(e))
chks = era_post.checks()
print("ERA UNPOSTED CHECKS:", len(chks))
tot = 0.0; os.makedirs("era_details", exist_ok=True)
for c in chks:
    keys = [k for k in c.keys() if any(s in k.lower() for s in ("id", "payer", "amount", "date", "check", "trn", "unposted", "status"))]
    print("  ", {k: c.get(k) for k in keys})
    try: tot += float(c.get("unpostedamount") or c.get("checkamount") or 0)
    except: pass
    cid = c.get("id") or c.get("checkid")
    p = "era_details/%s.json" % cid
    if cid and not os.path.exists(p):
        det = era_post.details(cid); json.dump(det, open(p, "w"), indent=1); time.sleep(0.3)
print("TOTAL unposted $%.2f" % tot)
json.dump(chks, open("registers/era_checks_before_2026-10-03T0510Z.json", "w"), indent=1)
