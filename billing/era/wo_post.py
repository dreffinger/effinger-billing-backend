# PLAIN ENGLISH (ERA-linked $0 + write-off)
# Decides: Posts approved write-offs on ERA lines (Medicaid non-covered CCM/AWV) with the CARC reason.
# Rules it uses: Only visits on your approved list.
# Never touches: Unapproved visits.
# ---
"""Post ERA-linked $0 payments with insurance write-offs (Payment Entry 'addpayments', captured 9/3/2026
from William's Menacof entry launched from ERA Center).  Used for the Medicaid CCM/AWV non-covered lines
William approved for write-off (mcad_ccm_writeoff_visits.json) and any other approved write-off list.
Each visit: header = $0 payment from the ERA check (postingmethod=era, eraclaimid/erareportid) +
one <writeoff> per charge for its current insurance balance.  The ERA line drops off the unposted list.
Usage: python3 wo_post.py --carrier MCAD --code WOMCAD [--visits id,id] [--dry]"""
import amd, era_post, resave, json, re, sys, time
import xml.etree.ElementTree as ET

WO_CPTS = {"99487", "99489", "99490", "99491", "G0439", "G0438"}

def fmt(v): return ("%.2f" % float(v))

def post_writeoff(chk, v, code, postedby="POI0712"):
    charges = []
    total = 0.0
    for ch in v["charges"]:
        if ch.get("chargecode") and ch["chargecode"] not in WO_CPTS:
            continue   # safety: only the approved non-covered codes
        cid = "charge%s" % ch["chargedetailid"]
        d = resave.detail(str(ch["chargedetailid"]))
        c = [x for x in ET.fromstring(d).iter("charge") if x.get("id") == cid]
        if not c:
            return False, "charge %s not found" % cid
        c = c[0]
        bal = float(c.get("insbalance") or 0)
        if c.get("void") == "1" or bal <= 0:
            continue
        total += bal
        charges.append('<charge id="%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%s" patbalance="%s" profile="%s">'
                       '<paymentlist><payment amount="0.00" id="" status="B"/></paymentlist>'
                       '<writeofflist><writeoff id="" risk="0" amount="%s" code="%s" status="B"/></writeofflist></charge>'
                       % (cid, c.get("insportion") or fmt(bal), c.get("patportion") or "0.00", fmt(bal), c.get("patbalance") or "0.00",
                          v.get("profilecode") and ("prof%s" % v["profileid"]) or "", fmt(bal), code))
    if not charges:
        return False, "nothing to write off (balances already 0)"
    carrier = "car%s" % chk["systemcarrierid"]
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="era" amount="0.00" paycode="PE" woamount="%s" paymethod="10" '
           'carrierid="%s" depositdate="%s" eraclaimid="%s" erareportid="%s" case_note="" checknumber="%s" inclstmt="0" postedby="%s" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), v["patientid"], fmt(total), carrier, chk["depositdate"][:10].split("-")[1] + "/" + chk["depositdate"][8:10] + "/" + chk["depositdate"][:4],
              v["checkclaimid"], chk["id"], chk["paymentnumber"], postedby, "".join(charges)))
    r = amd.post(xml)
    ok = "Fault" not in r and "<Error />" in r or ("Fault" not in r and "Error" not in r)
    return ok, re.sub(r"\s+", " ", r[:200]) + " | total %.2f" % total

if __name__ == "__main__":
    carrier = sys.argv[sys.argv.index("--carrier") + 1] if "--carrier" in sys.argv else "MCAD"
    code = sys.argv[sys.argv.index("--code") + 1] if "--code" in sys.argv else "WOMCAD"
    dry = "--dry" in sys.argv
    want = set(int(x) for x in sys.argv[sys.argv.index("--visits") + 1].split(",")) if "--visits" in sys.argv else set(json.load(open("mcad_ccm_writeoff_visits.json")))
    log = open("wo_post.log", "a")
    def L(m): print(m); log.write(m + "\n"); log.flush()
    L("=== wo_post %s carrier=%s code=%s dry=%s targets=%d ===" % (time.ctime(), carrier, code, dry, len(want)))
    n = 0; tot = 0.0
    for chk in era_post.checks():
        if chk["systemcarriercode"] != carrier or float(chk["unpostedamount"] or 0) < 0 and False:
            continue
        if chk["systemcarriercode"] != carrier: continue
        det = era_post.details(chk["id"])
        for v in det["eracheckdetails"]:
            if v["visitid"] not in want: continue
            cpts = [c["chargecode"] for c in v["charges"]]
            if dry:
                L("DRY check %s visit %s %s %s %s" % (chk["id"], v["visitid"], v["patientname"], v["dos"][:10], cpts)); continue
            ok, msg = post_writeoff(chk, v, code)
            L("%s check %s visit %s %s %s %s -> %s" % ("OK " if ok else "ERR", chk["id"], v["visitid"], v["patientname"], v["dos"][:10], cpts, msg))
            if ok:
                n += 1; tot += float(msg.rsplit("total", 1)[1])
            time.sleep(0.7)
    L("=== done: %d visits written off, $%.2f ===" % (n, tot))
