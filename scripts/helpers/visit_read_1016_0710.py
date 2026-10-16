# PLAIN ENGLISH (visit live read, 3 AM ET 10/16/2026 run 2026-10-16T0710Z) - READ ONLY.
# Decides: nothing. For "pid:vid,vid,..." arguments it prints every live charge of those visits with fee, paid, insurance and
#   patient balance, last-billed carrier, and the non-void payments (amount, carrier, check number, date, reason codes) so the
#   run can decide the exclusion rows from the chart itself. Writes registers/visit_read_<stamp>.json (ids + dollars only).
import amd, txh, payreasons, json, sys, time
STAMP = "2026-10-16T0710Z"; amd.login_cached(); out = {}
for arg in sys.argv[1:]:
    pid, vids = arg.split(":"); root = txh.fetch(pid)
    for vid in vids.split(","):
        st = payreasons.visit_state(pid, vid, root); out["%s:%s" % (pid, vid)] = st
        for c in st:
            print(pid, vid, "c%s" % c["cid"], c["cpt"], c["dos"], "fee %.2f paid %.2f insbal %.2f patbal %.2f carrier %s" % (c["fee"], c["paid"], c["insbalance"], c["patbalance"], c["carrier"]))
            for p in c["pays"]:
                if p["void"] != "1": print("      pay %.2f %s chk=%s %s reasons=%s" % (p["amount"], p["carrier"], p["checkno"], p["date"], p["reasons"]))
            for w in c["wos"]:
                if w["void"] != "1": print("      wo %.2f %s %s" % (w["amount"], w["code"], w["date"]))
    time.sleep(0.3)
json.dump(out, open("registers/visit_read_%s.json" % STAMP, "w"), indent=1, default=str)
