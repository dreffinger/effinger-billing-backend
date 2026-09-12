# PLAIN ENGLISH (tx-history reads, 9/12 7am ET run): for the patients William answered on, print the open charges
# (visit, charge, cpt, dos, insbal, patbal, paid, carrier, billdate, provider, write-off ids) - reads only.
import txh, sys, re
for pid in sys.argv[1:]:
    root = txh.fetch(pid)
    print("==", pid)
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        ib = float(a.get("insbal") or 0); pb = float(a.get("patbal") or 0)
        wos = [(w.get("id"), w.get("wocode"), w.get("amount")) for w in c.iter("writeoff") if w.get("void") != "1" and float(w.get("amount") or 0) != 0]
        pays = [(p.get("id"), p.get("amount"), p.get("carrier")) for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        if ib == 0 and pb == 0 and not ("--all" in sys.argv): continue
        print("  v%s c%s %s %s ins=%.2f pat=%.2f paid=%s car=%s bill=%s prov=%s wo=%s pay=%s" % (a.get("visit"), a.get("id"), a.get("proccode"), a.get("dos"), ib, pb, a.get("paid"), a.get("carrier"), a.get("billdate"), a.get("provider") or a.get("prov") or a.get("profile"), wos, pays))
