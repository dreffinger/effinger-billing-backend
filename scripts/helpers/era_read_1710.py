# PLAIN ENGLISH (ERA reads, run 2026-09-30T1710Z): lists the ERA Center's unposted checks after the Post pass and caches each check's
# details (every claim line's paid amount, adjustments, CARC/RARC) under era_details/<checkid>.json. Reads only, no posting.
import era_post, json, os
os.makedirs("era_details", exist_ok=True)
chks = era_post.checks()
print("UNPOSTED after Post:", len(chks), sum(float(c.get("unpostedamount") or c.get("checkamount") or 0) for c in chks))
for c in chks:
    print(" ", c.get("id"), c.get("carriercode"), c.get("checknumber"), c.get("checkamount"), "unposted", c.get("unpostedamount"), c.get("checkdate"))
for cid in ["1052905", "1052906", "1052907"]:
    d = era_post.details(cid); json.dump(d, open("era_details/%s.json" % cid, "w"), indent=1)
    vs = d.get("visits") or d.get("claims") or []
    print("details", cid, "top keys", list(d.keys())[:8], "lines", len(vs))
