# PLAIN ENGLISH (Lisle 5/22/2026 initial-NF recode, William 11/9/2026)
# Decides: Nothing on its own. William's board answer on row lisle-jasper-23083 was "try to rebill it as a 99309 and see if
#          that pays": WellCare finalized the 5/22/2026 99306 (initial nursing-facility care) + 99497 at $0 while it PAID the
#          5/28/2026 99309 on the same chart, so the denial is the initial-visit code, not coverage. This swaps the 99306
#          (pcode65116) for a 99309 (pcode65119) on visit vst19443011 and rebills the visit to WellCare (sequence 3) as an
#          original claim. The 99497 keeps its modifier 25 (mcode7).
# Rules it uses: Full-visit echo (recode.swap_proc). A proccode change is a RECODE: AMD voids the charge and re-creates it
#          under a NEW id, so the new fee is re-read and reported. Neither charge carries a payment, so nothing to re-post.
# Never touches: Paid charges - it refuses if a payment is posted on the visit.
# Register: registers/recode_lisle_1109.json
import json, os, re, sys
import xml.etree.ElementTree as ET
import amd, resave, recode, txh

PID, VID, CID = "23083", "19443011", "23351281"
OLD, NEW = "pcode65116", "pcode65119"   # 99306 -> 99309
SEQ = "3"                                # WEL04 WellCare
live = "--live" in sys.argv

amd.login_cached()
root = txh.fetch_visit(PID, "vst" + VID)
charges = [c.attrib for c in root.iter("charge")
           if re.sub(r"\D", "", c.attrib.get("visitid") or c.attrib.get("visit") or "") == VID and c.attrib.get("void") != "1"]
pays = [p.attrib for c in root.iter("charge") for p in c.iter("payment")
        if re.sub(r"\D", "", c.attrib.get("visitid") or c.attrib.get("visit") or "") == VID and float(p.attrib.get("amount") or 0) != 0]
print("visit vst%s live charges:" % VID)
for c in charges:
    print("   chg%s %s dos %s fee %s insbal %s billed %s" % (c.get("id"), c.get("proccode"), c.get("dos"), c.get("fee"), c.get("insbal"), c.get("billdate")))
if pays:
    print("REFUSED - a payment is posted on this visit; a recode would unapply it:", pays); sys.exit(1)

before = ET.fromstring(resave.detail(CID))
cur = [c.attrib.get("proccode") for c in before.iter("charge") if c.attrib.get("id") == "charge" + CID]
print("charge%s proccode now: %s  ->  %s" % (CID, cur, NEW))
if not live:
    print("DRY - would swap %s -> %s on every live charge of the visit and rebill sequence %s" % (OLD, NEW, SEQ)); sys.exit(0)

msg = recode.swap_proc(CID, {OLD: NEW}, SEQ)
print("recode:", msg)

after = txh.fetch_visit(PID, "vst" + VID)
rows = []
for c in after.iter("charge"):
    a = c.attrib
    if re.sub(r"\D", "", a.get("visitid") or a.get("visit") or "") != VID: continue
    rows.append({"chg": a.get("id"), "proccode": a.get("proccode"), "dos": a.get("dos"), "fee": a.get("fee"),
                 "insbal": a.get("insbal"), "void": a.get("void"), "billdate": a.get("billdate"), "carrier": a.get("carrier")})
    print("   AFTER chg%s %s fee %s insbal %s void %s billed %s" % (a.get("id"), a.get("proccode"), a.get("fee"), a.get("insbal"), a.get("void"), a.get("billdate")))
os.makedirs("registers", exist_ok=True)
json.dump({"pid": PID, "visit": VID, "swap": {OLD: NEW}, "seq": SEQ, "result": msg, "after": rows,
           "why": "William 11/9/2026 board answer: try to rebill it as a 99309 and see if that pays"},
          open("registers/recode_lisle_1109.json", "w"), indent=1)
print("register -> registers/recode_lisle_1109.json")
