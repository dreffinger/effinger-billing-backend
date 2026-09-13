# PLAIN ENGLISH (ERA step 5a/5b snapshot, 5am ET 9/13/2026 run - prompt v5)
# Decides: nothing. Releases expired ERA locks, reads GET /api/era/checks (the whole unposted list),
#   saves it as era_checks_<tag>_<stamp>.json, prints count + dollar totals, and fills the era_details/<checkid>.json
#   cache for every check not yet cached (GET /api/era/checkdetails?checkid=).
# Never touches: posting, dismissing, any AMD write.
"""Usage: python3 era_step_b_0913.py <tag before|after> <stamp e.g. 2026-09-13T0930Z>"""
import era_post, json, os, sys, time, requests
tag, stamp = sys.argv[1], sys.argv[2]
os.makedirs("era_details", exist_ok=True)
if tag == "before":
    try:
        requests.post(era_post.API + "/era/locks/release-expired", headers=era_post.H(), data=json.dumps(""), timeout=60)
        print("locks: release-expired sent")
    except Exception as e:
        print("locks error", str(e)[:120])
chk = era_post.checks()
json.dump(chk, open("era_checks_%s_%s.json" % (tag, stamp), "w"), indent=1)
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
n = len(chk); unp = sum(f(c.get("unpostedamount")) for c in chk); pay = sum(f(c.get("paymentamount")) for c in chk)
print("ERA %s: %d unposted checks | unpostedamount %.2f | paymentamount %.2f" % (tag, n, unp, pay))
if tag == "before":
    miss = [c for c in chk if not os.path.exists("era_details/%s.json" % c["id"])]
    print("details to pull:", len(miss))
    for c in miss:
        try:
            d = era_post.details(c["id"])
            json.dump(d, open("era_details/%s.json" % c["id"], "w"))
        except Exception as e:
            print("details error", c["id"], str(e)[:100])
        time.sleep(0.25)
    print("cache size:", len(os.listdir("era_details")))
for c in sorted(chk, key=lambda c: -f(c.get("unpostedamount")))[:60]:
    print("  %s %-6s %-22s unposted %8.2f  paid %9.2f  %s" % (c["id"], c.get("systemcarriercode") or "", (c.get("paymentnumber") or "")[:22], f(c.get("unpostedamount")), f(c.get("paymentamount")), (c.get("depositdate") or c.get("receiveddate") or "")[:10]))
