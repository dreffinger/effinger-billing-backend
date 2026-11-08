"""Sunday sweep 2026-11-08: chart plans + open charges (carrier, billdate, balances, payments) for the charts without a board card."""
import amd, txh, re, json, sys
amd.login_cached()
PIDS = ["23083", "17471273", "17476912", "17474798", "17473501", "25266", "17472834", "21021", "46678", "17477572", "17475407", "17477267"]
for pid in PIDS:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    print("\n== pid %s %s dob %s insorder=%s" % (pid, a.get("name"), a.get("dob"), a.get("insorder")))
    for m in re.findall(r'<insplan ([^>]*)>', r):
        d = dict(re.findall(r'(\w+)="([^"]*)"', m)); print("   plan", d.get("sequence"), d.get("carrier"), d.get("subscribernum"), d.get("begindate"), "-", d.get("enddate"))
    try:
        root = txh.fetch(pid)
    except Exception as e:
        print("   txh ERR", e); continue
    for ch in root.iter("charge"):
        c = ch.attrib
        if c.get("void") == "1": continue
        pays = [(pm.attrib.get("date"), pm.attrib.get("amount"), pm.attrib.get("carrier"), pm.attrib.get("void")) for pm in ch.iter("payment") if pm.attrib.get("void") != "1"]
        wos = [(w.attrib.get("date"), w.attrib.get("amount"), w.attrib.get("wocode")) for w in ch.iter("writeoff") if w.attrib.get("void") != "1"]
        ib = c.get("insbalance") or c.get("insurancebalance") or ""; pb = c.get("patbalance") or c.get("patientbalance") or ""
        if (ib in ("", "0.00", "0") and pb in ("", "0.00", "0")) and not pays: continue
        print("   CHG", c.get("id"), c.get("date") or c.get("dos"), c.get("proccode") or c.get("cpt"), c.get("carrier"), "bill", c.get("billdate"), "amt", c.get("amount") or c.get("fee"), "insbal", ib, "patbal", pb, "visit", c.get("visitid") or c.get("visit"), "pays", pays[:3], "wo", wos[:2])
