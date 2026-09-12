# PLAIN ENGLISH (inspector state check, 9/12 7am ET run): for each visit sitting in the Claim Inspector, read the patient's
# tx history and print the visit's charges (cpt, dos, insbal, patbal, paid, writeoffs, billdate, carrier, modifiers) - reads only.
import txh, json, sys
s = json.load(open("scan_0912/summary_before.json"))
vis = [(b, v) for b, vs in s["inspector"].items() for v in vs]
pids = sorted({v["pid"] for _, v in vis})
for pid in pids:
    root = txh.fetch(pid)
    want = {v["vid"] for _, v in vis if v["pid"] == pid}
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("visit") not in want or a.get("void") == "1": continue
        wos = [(w.get("wocode"), w.get("amount"), w.get("void")) for w in c.iter("writeoff")]
        pays = [(p.get("amount"), p.get("carrier") or p.get("payer"), p.get("void")) for p in c.iter("payment")]
        print(pid, "v"+a.get("visit"), a.get("id"), a.get("proccode"), a.get("dos"), "mods=%s" % a.get("modifiers"), "fee=%s insbal=%s patbal=%s paid=%s" % (a.get("fee") or a.get("amount"), a.get("insbal"), a.get("patbal"), a.get("paid")), "car=%s bill=%s pos=%s" % (a.get("carrier"), a.get("billdate"), a.get("pos")), "wo=%s pay=%s" % (wos, pays))
