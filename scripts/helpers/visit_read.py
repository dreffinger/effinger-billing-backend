# PLAIN ENGLISH (read one chart's charges, 10/1/2026): READ-ONLY. Prints every live charge of a chart (optionally only one CPT or one
#   visit) with fee / paid / insurance balance / patient balance / last-billed carrier / bill date, and the payments and write-offs
#   under it - so a rebill or write-off decision is made from live data.
# Never touches: AMD writes.
#   python3 visit_read.py <patientid> [--cpt 99487] [--visit 19455604]
import amd, txh, json, sys
amd.login_cached()
pid = sys.argv[1]; cpt = sys.argv[sys.argv.index("--cpt") + 1] if "--cpt" in sys.argv else None
vid = sys.argv[sys.argv.index("--visit") + 1] if "--visit" in sys.argv else None
root = txh.fetch("pat" + pid.replace("pat", ""))
for c in root.iter("charge"):
    a = c.attrib
    if a.get("void") == "1": continue
    if cpt and a.get("proccode") != cpt: continue
    if vid and (a.get("visit") or a.get("visitid")) != vid: continue
    print("CHG", a.get("id"), a.get("dos"), a.get("proccode"), "fee", a.get("fee"), "paid", a.get("paid"), "insbal", a.get("insbal"), "patbal", a.get("patbal"), "carrier", a.get("carrier"), "billdate", a.get("billdate"), "visit", a.get("visit"))
    for p in c.iter("payment"):
        q = p.attrib; print("    PAY", q.get("date"), q.get("carrier") or q.get("carriercode"), q.get("amount"), "chk", q.get("checknumber"), "void", q.get("void"), "code", q.get("paymentcode") or q.get("paycode"))
    for w in c.iter("writeoff"):
        q = w.attrib; print("    WO ", q.get("date"), q.get("writeoffcode") or q.get("code"), q.get("amount"), "void", q.get("void"))
