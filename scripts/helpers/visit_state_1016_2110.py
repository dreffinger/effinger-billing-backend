# PLAIN ENGLISH (live visit state, 5 PM ET 10/16/2026 run 2026-10-16T2110Z) - READ ONLY.
# Decides: nothing. For each pid:visit pair it prints every live charge of the visit (charge id, CPT, DOS, fee, insurance
#   balance, patient balance, last-billed carrier) and every payment / write-off on it (amount, carrier, check number,
#   void flag, reason codes) from gettxhistory via payreasons.visit_state. No AMD write of any kind.
# Usage: python3 visit_state_1016_1510.py <pid>:<visitid> ...
import sys, json, payreasons, amd
amd.login_cached()
for arg in sys.argv[1:]:
    pid, vid = arg.split(":")
    try: ch = payreasons.visit_state(pid, vid)
    except Exception as e: print(arg, "ERR", str(e)[:120]); continue
    print("== pid %s visit %s" % (pid, vid))
    for c in ch:
        print("  chg %s %s %s fee %s insbal %s patbal %s carrier %s billdate %s" % (c.get("id"), c.get("cpt") or c.get("proccode"), c.get("dos"), c.get("fee"), c.get("insbalance"), c.get("patbalance"), c.get("carrier"), c.get("billdate")))
        for p in c.get("pays", []): print("     pay %s carrier %s chk %s void %s reasons %s" % (p.get("amount"), p.get("carrier"), p.get("check"), p.get("void"), p.get("reasons")))
        for w in c.get("wos", []): print("     wo  %s" % json.dumps(w)[:160])
