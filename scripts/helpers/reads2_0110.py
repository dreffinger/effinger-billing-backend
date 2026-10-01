# PLAIN ENGLISH (run 2026-10-01T0110Z): READ-ONLY detail of the two CCM visits Florida Blue denied $0 on the 9/30 remits
#   (1052904 pat12232248 v19455716 PR-177; 1052905 pat48449 v19455604 PR-204) - every live charge attribute, payment and write-off,
#   plus the chart's plan list with sequence/begin/end dates, so the re-route decision is made from live data.
# Never touches: AMD writes.
import amd, txh, re, json, sys, time
import xml.etree.ElementTree as ET
amd.login_cached()
for pid, vid in (("12232248", "19455716"), ("48449", "19455604")):
    root = txh.fetch("pat" + pid)
    print("== pat%s visit %s" % (pid, vid))
    for c in root.iter("charge"):
        a = c.attrib
        if (a.get("visitid") or a.get("visit")) != vid: continue
        print(" CHG", json.dumps(a))
        for p in c.iter("payment"): print("    PAY", json.dumps(p.attrib))
        for w in c.iter("writeoff"): print("    WO ", json.dumps(w.attrib))
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    for x in re.findall(r'<insplan [^>]*/?>', d):
        p = dict(re.findall(r'(\w+)="([^"]*)"', x))
        print(" PLAN", {k: p.get(k) for k in ("id", "carrier", "carriercode", "sequence", "begindate", "enddate", "subscribernum", "finclasscode", "insorder")})
    m = re.search(r'<patient [^>]*>', d)
    if m:
        pa = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        print(" PATIENT insorder", pa.get("insorder"), "deceased", pa.get("deceased") or pa.get("dateofdeath"))
    time.sleep(0.3)
