"""Sunday sweep 2026-11-08: Hays 2026 charges + Morland Bettina 2023 charges (ids, billdates, balances)."""
import amd, txh, resave, re
amd.login_cached()
for pid, want in (("17471273", ("2026",)), ("21021", ("2023",))):
    root = txh.fetch(pid)
    for ch in root.iter("charge"):
        c = ch.attrib
        if c.get("void") == "1": continue
        d = c.get("date") or ""
        if d[-4:] not in want: continue
        pays = [(pm.attrib.get("date"), pm.attrib.get("amount"), pm.attrib.get("carrier")) for pm in ch.iter("payment") if pm.attrib.get("void") != "1"]
        wos = [(w.attrib.get("date"), w.attrib.get("amount"), w.attrib.get("wocode")) for w in ch.iter("writeoff") if w.attrib.get("void") != "1"]
        cid = c.get("id").replace("charge", "")
        try:
            x = resave.detail(cid); v = re.search(r'<visit ([^>]*)>', x); va = dict(re.findall(r'(\w+)="([^"]*)"', v.group(1))) if v else {}
            cm = re.search(r'<charge id="%s"[^>]*>' % c.get("id"), x); ca = dict(re.findall(r'(\w+)="([^"]*)"', cm.group(0))) if cm else {}
            ex = "insorder=%s insbal=%s patbal=%s" % (va.get("insorder"), ca.get("insbalance"), ca.get("patbalance"))
        except Exception as e: ex = "ERR %s" % e
        print(pid, "CHG", cid, d, c.get("proccode"), c.get("carrier"), "bill", c.get("billdate"), "amt", c.get("amount"), "v", c.get("visitid") or c.get("visit"), ex, "pays", pays[:3], "wo", wos[:2])
