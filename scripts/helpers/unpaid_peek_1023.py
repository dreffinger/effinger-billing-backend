# Nightly 2026-10-23: how fresh is the unpaid list? (read-only; explains a 0-pair precheck window)
import amd, era_post, requests, json, datetime, collections
amd.login_cached()
unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=120).json()
today = datetime.date.today()
ages = collections.Counter()
for v in unp:
    d = (today - datetime.datetime.fromisoformat(v["dateofservice"]).date()).days
    ages["<=3" if d <= 3 else "4-7" if d <= 7 else "8-14" if d <= 14 else "15-30" if d <= 30 else ">30"] += 1
print("unpaid visits:", len(unp), "total insbalance: %.2f" % sum(v.get("insbalance") or 0 for v in unp))
print("age bands:", dict(ages))
newest = sorted(unp, key=lambda v: v["dateofservice"], reverse=True)[:8]
for v in newest: print(" ", v["dateofservice"][:10], v["carriercode"].strip(), v["patientid"], "%.2f" % (v.get("insbalance") or 0))
json.dump(unp, open("unpaid_2026-10-23.json", "w"))
