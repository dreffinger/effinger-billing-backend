#!/usr/bin/env python3
# PLAIN ENGLISH (live insurance-plan count on held charts, 1 PM ET 10/21/2026 run 2026-10-21T1710Z): READ-ONLY.
# Decides: nothing. For each chart id on the command line it runs getdemographic and prints how many insurance plans the
#   chart carries (carrier code + whether a subscriber number is present), so the run can tell whether William entered the
#   facesheet since the last slot. Writes registers/plan_check_<stamp>.json (chart ids + counts only). No AMD write.
# Usage: python3 plan_check_1021_1710.py 17478059 17478063 17478064 17470713
import amd, re, json, sys, time
STAMP = "2026-10-21T1710Z"; amd.login_cached(); out = {"stamp": STAMP, "charts": {}}
for pid in sys.argv[1:]:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
    plans = re.findall(r'<insplan [^>]*>', r)
    rows = []
    for p in plans:
        a = dict(re.findall(r'(\w+)="([^"]*)"', p))
        rows.append({"id": a.get("id"), "carrier": a.get("carrier") or a.get("carriercode"), "seq": a.get("sequence"), "subscriber_present": bool(a.get("subscribernum") or a.get("subscriberid") or a.get("insuredid")), "begin": a.get("begindate"), "end": a.get("enddate")})
    print(pid, "plans:", len(rows), [(x["carrier"], x["seq"], x["subscriber_present"], x["begin"], x["end"]) for x in rows])
    out["charts"][pid] = rows; time.sleep(0.3)
json.dump(out, open("registers/plan_check_%s.json" % STAMP, "w"), indent=1)
