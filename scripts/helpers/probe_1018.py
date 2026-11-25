#!/usr/bin/env python3
# PLAIN ENGLISH (read-only probe of the six board charts of the 11/25 09:03Z press - plans, live charges, carriers, bill dates, payments)
# Decides: nothing. Prints what the chart holds so the six helpers of this run act on the live state, not on the card text.
# Never touches: AMD writes. Usage: python3 probe_1018.py <pid> [...]
import amd, txh, re, sys, json
import xml.etree.ElementTree as ET
amd.login_cached()
MIN = [x for x in sys.argv[1:] if x.startswith("--min=")]; MIN = MIN[0][6:] if MIN else "0000"
for pid in [x for x in sys.argv[1:] if not x.startswith("--")]:
    pid = re.sub(r"\D", "", pid)
    d = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"})))
    p = d.find(".//patient")
    print("=== pat%s name=%s dob=%s insorder=%s" % (pid, (p.get("name") or "")[:3] + "***", "[DOB]", p.get("insorder")))
    for ip in d.iter("insplan"):
        print("   plan %s seq=%s carrier=%s code=%s num=***%s begin=%s end=%s" % (ip.get("id"), ip.get("sequence"), ip.get("carrier"), ip.get("carriercode") or ip.get("code") or "", (ip.get("subscribernum") or "")[-4:], ip.get("begindate"), ip.get("enddate")))
    root = txh.fetch(pid)
    seen = {}
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        dos = a.get("dos") or ""; key = dos[-4:] + dos[:2] + dos[3:5]
        if key < MIN and float(a.get("insbal") or 0) == 0 and float(a.get("patbal") or 0) == 0: continue
        pays = [(q.get("id"), q.get("amount"), q.get("void"), (q.get("checknumber") or q.get("checknum") or "")[-8:], q.get("date") or q.get("postdate") or "") for q in c.iter("payment")]
        wos = [(q.get("id"), q.get("amount"), q.get("void"), q.get("wocode")) for q in c.iter("writeoff")]
        print("   chg %s vst %s dos %s %s mods=%s carrier=%s billdate=%s fee=%s insbal=%s patbal=%s insbilled=%s pays=%s wos=%s" % (
            a.get("id"), a.get("visit"), a.get("dos"), a.get("proccode"), a.get("modifiers"), a.get("carrier"), a.get("billdate"), a.get("fee"), a.get("insbal"), a.get("patbal"), a.get("paid"), pays, wos))
