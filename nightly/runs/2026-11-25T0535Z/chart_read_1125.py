"""Read-only: list a chart's live charges (visit, dos, proc, last-billed carrier, billdate, balances, payments)."""
import sys, txh
root = txh.fetch(sys.argv[1])
for c in root.iter("charge"):
    a = c.attrib
    if a.get("void") == "1": continue
    pays = sum(float(p.get("amount") or 0) for p in c.iter("payment") if p.get("void") != "1")
    print(a.get("visit"), a.get("id"), a.get("dos"), a.get("proc") or a.get("proccode"), a.get("fee"), "car", a.get("carrier"), "billed", a.get("billdate"), "insbal", a.get("insbalance"), "pat", a.get("patbalance"), "paid", pays)
