# PLAIN ENGLISH (Manual payment / write-off on one charge)
# Decides: Nothing on its own: posts a payment and/or write-off to one charge with a note.
# Rules it uses: Refuses to over-apply beyond the insurance balance.
# Never touches: Charges at $0.
# ---
"""Manual (non-ERA) insurance payment + write-off on one charge via Payment Entry addpayments.
Usage: python3 manual_post.py <chargeid> <carriercode> <payamount> <woamount> <wocode> <checknumber> [depositdate mm/dd/yyyy] [note] [--dry]"""
import amd, resave, json, re, sys, time
import xml.etree.ElementTree as ET
CAR = {v[0]: k for k, v in json.load(open("carriers.json")).items()}
def post(cid, carrier, pay, wo, wocode="WOINS", checknumber="", depositdate=None, note="", dry=False):
    rt = ET.fromstring(resave.detail(cid)); vis = rt.find(".//visit"); pat = rt.find(".//patient")
    c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    bal = float(c.get("insbalance") or 0)
    if pay + wo > bal + 0.005: return False, "over-apply: pay %.2f + wo %.2f > insbalance %.2f" % (pay, wo, bal)
    prof = vis.get("profile"); pid = re.sub(r"\D", "", pat.get("id"))
    chg = ('<charge id="charge%s" allowed="%.2f" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
           '<paymentlist><payment amount="%.2f" id="" status="B"/></paymentlist><writeofflist>%s</writeofflist></charge>'
           % (cid, pay, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof, pay,
              ('<writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/>' % (wo, wocode)) if wo > 0 else ""))
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="" amount="%.2f" paycode="PE" woamount="%.2f" paymethod="9" carrierid="%s" '
           'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, pay, wo, CAR[carrier], depositdate or time.strftime("%m/%d/%Y"), note, checknumber, chg))
    if dry: return True, "DRY bal %.2f prof %s pid %s -> pay %.2f wo %.2f" % (bal, prof, pid, pay, wo)
    r = amd.post(xml)
    return ('success="1"' in r), re.sub(r"\s+", " ", r[:200])
if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--dry"]
    cid, car, pay, wo, code, chk = a[0], a[1], float(a[2]), float(a[3]), a[4], a[5]
    dd = a[6] if len(a) > 6 else None; note = a[7] if len(a) > 7 else ""
    ok, msg = post(cid, car, pay, wo, code, chk, dd, note, "--dry" in sys.argv)
    print(ok, msg)
    open("era_manual_post.log", "a").write("manual_post %s %s %s pay %.2f wo %.2f -> %s %s\n" % (time.ctime(), cid, car, pay, wo, ok, msg))
