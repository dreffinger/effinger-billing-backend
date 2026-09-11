import json
from collections import Counter, defaultdict
rows=[json.loads(l) for l in open("medicaid_classify.jsonl")]
good=[r for r in rows if not r.get("err")]
errs=[r for r in rows if r.get("err")]
prof=Counter(r.get("profile") for r in good)
paidc=Counter((r.get("profile"), bool(r.get("paid"))) for r in good)
bal=defaultdict(float)
for r in good: bal[(r.get("profile"), bool(r.get("paid")))]+=float(r.get("insbalance") or 0)
print("classified:",len(rows)," good:",len(good)," errs:",len(errs))
print("profiles:", dict(prof))
print("profile x paid -> (visits,$):")
for k in sorted(paidc): print("  ",k, paidc[k], round(bal[k],2))
notpaid=[r for r in good if not r.get("paid")]
npp=Counter(r.get("profile") for r in notpaid); npb=defaultdict(float)
for r in notpaid: npb[r.get("profile")]+=float(r.get("insbalance") or 0)
print("UNANSWERED (not paid):", len(notpaid))
for p in npp: print("  ",p, npp[p], round(npb[p],2))
if errs: print("err sample:", errs[0].get("err"))
