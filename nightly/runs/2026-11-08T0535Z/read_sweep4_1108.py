"""Sunday sweep 2026-11-08: Hays 7 AET07 visits + Morland Bettina 2 HUM01 2023 visits via gettxhistory visitid= (charge ids, billdates, balances)."""
import amd, txh, resave, re
amd.login_cached()
for pid, vids in (("17471273", ["19448259", "19448592", "19448627", "19448967", "19448986", "19449065", "19449321"]), ("21021", ["19372463", "19372311"])):
    for vid in vids:
        try:
            root = txh.fetch_visit(pid, vid)
        except Exception as e:
            print(pid, vid, "ERR", e); continue
        for ch in root.iter("charge"):
            c = ch.attrib
            if c.get("void") == "1": continue
            cid = c.get("id").replace("charge", "")
            pays = [(pm.attrib.get("date"), pm.attrib.get("amount"), pm.attrib.get("carrier")) for pm in ch.iter("payment") if pm.attrib.get("void") != "1"]
            wos = [(w.attrib.get("date"), w.attrib.get("amount"), w.attrib.get("wocode")) for w in ch.iter("writeoff") if w.attrib.get("void") != "1"]
            try:
                x = resave.detail(cid); v = re.search(r'<visit ([^>]*)>', x); va = dict(re.findall(r'(\w+)="([^"]*)"', v.group(1))) if v else {}
                cm = re.search(r'<charge id="%s"[^>]*>' % c.get("id"), x); ca = dict(re.findall(r'(\w+)="([^"]*)"', cm.group(0))) if cm else {}
                ex = "insorder=%s insbal=%s patbal=%s dx=%s" % (va.get("insorder"), ca.get("insbalance"), ca.get("patbalance"), (ca.get("diagcodes") or "")[:50])
            except Exception as e: ex = "ERR %s" % e
            print(pid, "v%s CHG %s %s %s %s bill %s amt %s" % (vid, cid, c.get("date"), c.get("proccode"), c.get("carrier"), c.get("billdate"), c.get("amount")), ex, "pays", pays[:3], "wo", wos[:2])
