# PLAIN ENGLISH (ERA payment-only post)
# Decides: For secondary/supplement remits whose 'allowed' doesn't match AMD, allocates the paid amount across the charges with no write-offs.
# Rules it uses: Per-line amount first, spill-over second, leftover to unapplied.
# Never touches: Write-offs.
# ---
"""ERA-linked payment-only post: allocate the visit's ERA paid amount across its matched charges up to each
charge's insurance balance (per-line ERA amount first, then spill-over), no write-offs; leftover -> unapplied.
For secondary/supplement remits where the payer's 'allowed' doesn't line up with AMD's remaining balance.
Usage: python3 era_alloc_post.py <checkid>:<visitid> ... [--dry]"""
import amd, era_post, resave, era_manual_post as emp, re, sys, time
import xml.etree.ElementTree as ET
def build(chk, v):
    prof = "prof%s" % v["profileid"]; total = float(v["paymentamount"] or 0)
    rows = []
    for ch in v["charges"]:
        if int(ch.get("chargedetailid") or -1) <= 0: continue
        cid = str(ch["chargedetailid"]); rt = ET.fromstring(resave.detail(cid))
        c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
        bal = float(c.get("insbalance") or 0)
        if bal <= 0 or c.get("void") == "1": continue
        rows.append([cid, c, bal, min(bal, float(ch.get("paymentamount") or 0)), ch])
    left = total - sum(r[3] for r in rows)
    for r in rows:
        if left <= 0.005: break
        add = min(left, r[2] - r[3]); r[3] += add; left -= add
    charges = ""; applied = 0.0
    for cid, c, bal, pay, ch in rows:
        if pay <= 0: continue
        reasons = "".join('<reason id="%s" reasonid="%s" code="%s" name="%s" amount="%s" units="0" group="%s"/>'
                          % (x["reportreasondetailid"], x["payreasonid"], x["reasoncode"], emp.esc(x["reasontext"]), x["reasonamt"], x["payreasongroup"]) for x in ch.get("carc", []))
        first = ch["carc"][0]["reasoncode"] if ch.get("carc") else ""
        charges += ('<charge id="charge%s" allowed="%.2f" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
                    '<paymentlist><payment amount="%.2f" id="" reason="%s" status="B"><reasonlist payment="%.2f" allowed="%.2f">%s</reasonlist></payment></paymentlist><writeofflist/></charge>'
                    % (cid, pay, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof, pay, first, pay, pay, reasons))
        applied += pay
    rem = round(total - applied, 2)
    unapplied = ('<payment source="2" profile="%s" amount="%.2f" carrier="car%s"/>' % (prof, rem, chk["systemcarrierid"])) if rem > 0.005 else ""
    dd = chk["depositdate"][:10]; dd = "%s/%s/%s" % (dd[5:7], dd[8:10], dd[:4])
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="era" amount="%.2f" paycode="PE" woamount="0.00" paymethod="%s" carrierid="car%s" '
           'depositdate="%s" eraclaimid="%s" erareportid="%s" case_note="" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist>%s</unappliedpaymentlist><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), v["patientid"], total, emp.PAYMETHOD.get(chk["paymentcode"], "13"), chk["systemcarrierid"], dd,
              v["checkclaimid"], chk["id"], chk["paymentnumber"], unapplied, charges))
    return xml, applied, rem, [(r[0], r[3]) for r in rows]
if __name__ == "__main__":
    dry = "--dry" in sys.argv; log = open("era_manual_post.log", "a")
    def L(m): print(m); log.write(m + "\n"); log.flush()
    checks = {c["id"]: c for c in era_post.checks()}
    for t in [a for a in sys.argv[1:] if ":" in a]:
        cid, vid = (int(x) for x in t.split(":")); chk = checks[cid]
        v = [x for x in era_post.details(cid)["eracheckdetails"] if x["visitid"] == vid][0]
        xml, applied, rem, alloc = build(chk, v)
        L("alloc %s %s dos %s paid %.2f -> %s unapplied %.2f" % (v["patientname"], vid, v["dos"][:10], float(v["paymentamount"]), alloc, rem))
        if dry: continue
        r = amd.post(xml); L("   -> %s" % re.sub(r"\s+", " ", r[:220])); time.sleep(0.7)
