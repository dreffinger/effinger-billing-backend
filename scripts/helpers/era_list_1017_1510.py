# PLAIN ENGLISH (ERA Center unposted list, 11 AM ET 10/17/2026 run 2026-10-17T1510Z) - READ ONLY.
# Decides: nothing. GET /api/era/checks (the whole unposted list) and prints each check's id, payer, deposit date and
#   unposted amount plus the count and total, so the run has its before/after ERA numbers. No AMD write of any kind.
import era_post, json, sys
cs = era_post.checks()
tot = sum(float(c.get("unpostedamount") or 0) for c in cs)
print("ERA unposted checks:", len(cs), "total $%.2f" % tot)
for c in cs:
    print("  ", c.get("id"), c.get("systemcarriercode"), c.get("payername", "")[:30], c.get("depositdate"), "$", c.get("unpostedamount"), "checknum", c.get("checknumber"))
json.dump([{k: c.get(k) for k in ("id", "systemcarriercode", "depositdate", "unpostedamount", "checknumber")} for c in cs], open("registers/era_list_%s.json" % (sys.argv[1] if len(sys.argv) > 1 else "2026-10-17T1510Z"), "w"), indent=1)
