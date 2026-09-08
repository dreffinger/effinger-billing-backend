# PLAIN ENGLISH (Manual post of an ERA line)
# Decides: Posts an ERA line ERA Center refuses (procedure codes don't match), replicating your 9/3 Proctor entry.
# Rules it uses: Payment = allowed, write-off = the adjustment, remainder to patient per the remit.
# Never touches: Lines with no matched charge.
# ---
"""Post an ERA line the way Payment Entry does when ERA Center can't auto-post it (e.g. 'Procedure codes do not
match'): replica of William's 9/3/2026 Proctor 03/20 addpayments capture.
Per visit: for each ERA service line matched to a charge (chargedetailid != -1):
   payment = allowedamount, write-off = charge balance - allowed (the CARC amounts), reasons echoed;
 any remainder of the visit's paid amount goes to an unapplied credit (exactly what the UI did).
Usage: python3 era_manual_post.py <checkid>:<visitid> [...] [--dry]"""
import amd, era_post, resave, json, re, sys, time
import xml.etree.ElementTree as ET

PAYMETHOD = {"ACH": "9", "NON": "10", "CHK": "11", "FWT": "12", "BOP": "13"}

def esc(s): return (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

def build(chk, v):
    charges = []; applied = 0.0; wo_total = 0.0; prof = "prof%s" % v["profileid"]
    for ch in v["charges"]:
        if int(ch.get("chargedetailid") or -1) <= 0:
            continue
        cid = str(ch["chargedetailid"])
        rt = ET.fromstring(resave.detail(cid))
        c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
        bal = float(c.get("insbalance") or 0)
        if bal <= 0 or c.get("void") == "1":
            continue
        allowed = float(ch.get("allowedamount") or 0)
        pay = min(allowed, bal)
        wo = round(bal - pay, 2)
        reasons = "".join('<reason id="%s" reasonid="%s" code="%s" name="%s" amount="%s" units="0" group="%s"/>'
                          % (r["reportreasondetailid"], r["payreasonid"], r["reasoncode"], esc(r["reasontext"]), r["reasonamt"], r["payreasongroup"])
                          for r in ch.get("carc", []))
        first = ch["carc"][0]["reasoncode"] if ch.get("carc") else ""
        charges.append('<charge id="charge%s" allowed="%.2f" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
                       '<paymentlist><payment amount="%.2f" id="" reason="%s" status="B"><reasonlist payment="%.2f" allowed="%.2f">%s</reasonlist></payment></paymentlist>'
                       '<writeofflist>%s</writeofflist></charge>'
                       % (cid, allowed, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof,
                          pay, first, pay, allowed, reasons,
                          ('<writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/>' % (wo, (ch.get("payreasonwocode") or "WOINS").strip() or "WOINS")) if wo > 0 else ""))
        applied += pay; wo_total += wo
    total = float(v["paymentamount"] or 0)
    rem = round(total - applied, 2)
    unapplied = ('<payment source="2" profile="%s" amount="%.2f" carrier="car%s"/>' % (prof, rem, chk["systemcarrierid"])) if rem > 0.005 else ""
    dd = chk["depositdate"][:10]; dd = "%s/%s/%s" % (dd[5:7], dd[8:10], dd[:4])
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="era" amount="%.2f" paycode="PE" woamount="%.2f" paymethod="%s" carrierid="car%s" '
           'depositdate="%s" eraclaimid="%s" erareportid="%s" case_note="" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist>%s</unappliedpaymentlist><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), v["patientid"], total, wo_total, PAYMETHOD.get(chk["paymentcode"], "13"), chk["systemcarrierid"], dd,
              v["checkclaimid"], chk["id"], chk["paymentnumber"], unapplied, "".join(charges)))
    return xml, applied, wo_total, rem, len(charges)

if __name__ == "__main__":
    dry = "--dry" in sys.argv
    targets = [a for a in sys.argv[1:] if ":" in a]
    log = open("era_manual_post.log", "a")
    def L(m): print(m); log.write(m + "\n"); log.flush()
    checks = {c["id"]: c for c in era_post.checks()}
    for t in targets:
        cid, vid = (int(x) for x in t.split(":"))
        chk = checks.get(cid)
        if not chk: L("check %s not found" % cid); continue
        det = era_post.details(cid)
        vs = [v for v in det["eracheckdetails"] if v["visitid"] == vid]
        if not vs: L("visit %s not on check %s" % (vid, cid)); continue
        v = vs[0]
        xml, applied, wo, rem, n = build(chk, v)
        L("%s %s dos %s paid %.2f -> apply %.2f + wo %.2f on %d charge(s), unapplied %.2f" % (v["patientname"], vid, v["dos"][:10], float(v["paymentamount"]), applied, wo, n, rem))
        if dry or n == 0: continue
        r = amd.post(xml)
        L("   -> %s" % re.sub(r"\s+", " ", r[:220]))
        time.sleep(0.7)
