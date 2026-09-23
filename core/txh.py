# PLAIN ENGLISH (Transaction history dump)
# Decides: Nothing. Reads a patient's charges, payments, write-offs and balances (gettxhistory) so other scripts can decide.
# Rules it uses: Read-only.
# Never touches: Anything - it writes nothing.
# ---
"""gettxhistory dump: charges w/ balances, payments, unapplied credits.  Usage: python3 txh.py <patientid> [--raw]"""
import amd, sys, re, json
import xml.etree.ElementTree as ET
def fetch(pid):
    body = amd.msg('gettxhistory','demographics',{'patientid':str(pid),'filterhistory':'0','pagenumber':'1','typefilter':'0','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','profileid':'','getmemo':'false','nocookie':'1'})
    return ET.fromstring(amd.post(body, timeout=120))
def fetch_visit(pid, vid):
    """ONE visit's history (gettxhistory visitid=) - page 1 of the whole chart misses old visits on long charts (9/22/2026: pat21489 / pat23161)."""
    body = amd.msg('gettxhistory','demographics',{'patientid':str(pid),'filterhistory':'0','pagenumber':'1','typefilter':'0','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':str(vid),'profileid':'','getmemo':'false','nocookie':'1'})
    return ET.fromstring(amd.post(body, timeout=120))
if __name__ == "__main__":
    root = fetch(sys.argv[1])
    if "--raw" in sys.argv:
        print(ET.tostring(root)[:20000].decode()); sys.exit()
    tags = {}
    for e in root.iter(): tags[e.tag] = tags.get(e.tag, 0) + 1
    print("tags:", tags)
    for e in root.iter():
        if e.tag in ("unappliedpayment", "unappliedwriteoff"):
            print("UNAPPLIED", e.attrib)
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        bal = float(a.get("insbalance") or a.get("balance") or 0) + float(a.get("patbalance") or 0)
        print("CHG", a.get("id"), a.get("dos") or a.get("dateofservice"), a.get("proccode"), a.get("carrier") or a.get("carriercode"), "amt", a.get("amount"), "insbal", a.get("insbalance"), "patbal", a.get("patbalance"), "prov", a.get("provcode"), "visit", a.get("visitid") or a.get("visit"))
        for p in c.iter("payment"):
            print("    PAY", p.attrib)
        for w in c.iter("writeoff"):
            print("    WO ", w.attrib)
