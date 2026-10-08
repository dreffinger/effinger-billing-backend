# PLAIN ENGLISH (ERA Center unposted list - READ ONLY)
# Decides: Nothing. It reads GET /api/era/checks (the whole unposted list), counts it and totals it, saves the list to
# registers/era_checks_<tag>_<stamp>.json, and caches GET /api/era/checkdetails for every check not yet in era_details/
# (through era_post.details, which writes era_details/<checkid>.json). No AMD write of any kind.
# Usage: python3 era_list.py <tag> <run stamp>      e.g. python3 era_list.py before 2026-10-08T0110Z
# ---
import sys, os, json, datetime
import era_post

tag = sys.argv[1] if len(sys.argv) > 1 else "before"
stamp = sys.argv[2] if len(sys.argv) > 2 else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
os.makedirs("registers", exist_ok=True)
lst = era_post.checks()
rows = lst if isinstance(lst, list) else (lst.get("erachecks") or lst.get("checks") or lst.get("data") or [])
tot = 0.0
print("ERA unposted checks (%s): %d" % (tag, len(rows)))
for c in rows:
    cid = c.get("id") or c.get("checkid") or c.get("eracheckid")
    amt = float(c.get("checkamount") or c.get("amount") or 0)
    unp = c.get("unpostedamount")
    tot += amt
    print("  check %s  payer=%s / %s  checknumber=%s  date=%s  amount=%.2f  unposted=%s  claims=%s" % (
        cid, c.get("eracarriername") or c.get("payername"), c.get("systemcarriername"), c.get("checknumber"),
        c.get("checkdate"), amt, unp, c.get("claimcount") or c.get("claims")))
    if cid and not os.path.exists(os.path.join("era_details", "%s.json" % cid)):
        try:
            d = era_post.details(cid)
            n = len(d.get("eracheckdetails") or [])
            print("    details cached: %d claim rows" % n)
        except Exception as e:
            print("    details pull failed: %s" % e)
print("TOTAL check amount: %.2f" % tot)
json.dump({"tag": tag, "stamp": stamp, "count": len(rows), "total": round(tot, 2), "checks": rows},
          open(os.path.join("registers", "era_checks_%s_%s.json" % (tag, stamp)), "w"), indent=1)
print("saved registers/era_checks_%s_%s.json" % (tag, stamp))
