# PLAIN ENGLISH (ERA Center unposted list read, 5 AM ET 10/17/2026 run 2026-10-17T0910Z): READ-ONLY.
# Decides: nothing. GET /api/era/checks (the whole unposted list) -> prints count + total and writes
#   registers/era_checks_<tag>_<stamp>.json (check id, payer, amount, date only). No AMD write.
import era_post, json, sys, time
tag = sys.argv[1] if len(sys.argv) > 1 else "before"; STAMP = "2026-10-17T0910Z"
cs = era_post.checks()
rows = [{"checkid": c.get("checkid") or c.get("id"), "payer": c.get("payername") or c.get("payer"), "amount": c.get("checkamount") or c.get("amount"), "date": c.get("checkdate") or c.get("date"), "number": c.get("checknumber")} for c in cs]
tot = sum(float(r["amount"] or 0) for r in rows)
print("ERA unposted checks:", len(rows), "total $%.2f" % tot)
for r in rows: print("  ", r)
json.dump({"stamp": STAMP, "tag": tag, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "count": len(rows), "total": round(tot, 2), "checks": rows}, open("registers/era_checks_%s_%s.json" % (tag, STAMP), "w"), indent=1)
