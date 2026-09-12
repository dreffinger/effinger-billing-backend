import amd, re, json
import xml.etree.ElementTree as ET
amd.login_cached()
t = amd.post(amd.msg("getclaimunbillablecharges","claimsreports",{"lowdate":"","highdate":"","carrier":"","provider":""}), timeout=300)
open("unbilled_0910.xml","w").write(t)
root = ET.fromstring(t)
res = root.find(".//Results")
print("totalcount:", res.get("totalcount"), "totalamount:", res.get("totalamount"))
rows = []
for v in root.iter("visit"):
    rows.append({k: v.get(k) for k in v.keys()})
# group by error text
from collections import Counter
errs = Counter()
for r in rows:
    e = None
    for k in r:
        if "error" in k.lower() or "reason" in k.lower() or "note" in k.lower(): e = r[k]
    errs[(e or "?")[:90]] += 1
print(json.dumps(rows[:2], indent=1))
for e,c in errs.most_common(): print(c, "|", e)
