# PLAIN ENGLISH (visit payment read, 9 AM ET 10/16/2026 run 2026-10-16T1310Z) - READ ONLY.
# Decides: nothing. For each chart id given it reads gettxhistory (txh.fetch) and prints, per non-void charge of the visits
#   named (or every visit when none is named): visit, charge id, CPT, DOS, fee, carrier (last billed), billdate, insurance /
#   patient balance, and every non-void payment with its carrier, amount, check number and reason codes - so the run can tell
#   whether an ERA line is already posted, which claim an OA-18 duplicate points at, and what a denied visit carries. No AMD write.
import txh, sys, re
args = sys.argv[1:]; pid = args[0]; vids = set(args[1:])
root = txh.fetch("pat" + pid)
for ch in root.iter("charge"):
    if ch.get("void") == "1": continue
    if vids and ch.get("visit") not in vids: continue
    print("visit %s chg %s %s dos %s fee %s carrier %s billdate %s insbal %s patbal %s paid %s" % (
        ch.get("visit"), ch.get("id"), ch.get("proccode") or ch.get("cpt"), (ch.get("dos") or ch.get("begindate") or "")[:10], ch.get("fee") or ch.get("amount"),
        ch.get("carrier"), ch.get("billdate"), ch.get("insbalance") or ch.get("insurancebalance"), ch.get("patbalance") or ch.get("patientbalance"), ch.get("paid")))
    for p in ch.iter("payment"):
        if p.get("void") == "1": continue
        reasons = ["%s=%s" % (r.get("code") or r.get("reasoncode"), r.get("amount") or r.get("reasonamt")) for r in p.iter("reason")]
        print("     pay %s %s amt %s wo %s/%s check %s date %s reasons %s" % (p.get("id"), p.get("carrier") or p.get("type"), p.get("amount") or p.get("paid"), p.get("wocode"), p.get("woamount") or p.get("writeoff"), p.get("checknumber") or p.get("check"), (p.get("date") or p.get("createdate") or "")[:10], reasons))
