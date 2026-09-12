# PLAIN ENGLISH (Probe: post a $0 payment WITH reason codes through addpayments - William 9/12/2026 'yes do this')
# Decides: on ONE charge (Maplin 12/02/2025 99309, the Unbilled 'Payment reason codes are missing or do not balance' row):
#   void the $0 payment that has no reason codes (proven void call), then try to re-post a $0 payment carrying a
#   reason list (OA23 = amount the prior payer paid, PR2 = the coinsurance) so the payment balances to the fee.
#   Two shapes are tried; each is read back through gettxhistory; a probe payment that lands WITHOUT reasons is voided
#   again so the chart never ends worse than 'Medicare payment only' (which is itself billable to the secondary).
# Never touches: the balanced Medicare payment, other charges.
import amd, void_tx, resave, txh, re, sys, time, json
amd.login_cached()
PID, CID, BADPAY = "17469446", "23331342", "24570388"
FEE, PRIOR_PAID, COINS = "141.00", "123.35", "17.65"
CARRIER = "FLO02"; CHECK = "072350607"; DEPOSIT = "05/30/2026"
LOG = open("payreason_probe_0912.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def pays():
    out = []
    for c in txh.fetch(PID).iter("charge"):
        if c.get("id") == CID:
            for p in c.iter("payment"):
                out.append((p.get("id"), p.get("amount"), p.get("carrier"), p.get("void"), [(r.get("code"), r.get("amount")) for r in p.iter("payreason")]))
            return out, c.get("insbal"), c.get("patbal")
L("before: %s" % (pays(),))
ok, msg = void_tx.void_payment(PID, CID, BADPAY); L("void %s -> %s %s" % (BADPAY, ok, msg))
time.sleep(0.8); L("after void: %s" % (pays(),))
rt = __import__("xml.etree.ElementTree", fromlist=["ET"]).fromstring(resave.detail(CID)); vis = rt.find(".//visit")
c = [x for x in rt.iter("charge") if x.get("id") == "charge" + CID][0]; prof = vis.get("profile")
carN = json.load(open("carriers_rich.json")); carid = [k for k, v in carN.items() if v[0] == CARRIER][0]
def post(reason_xml, label):
    chg = ('<charge id="charge%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%s" patbalance="%s" profile="%s">'
           '<paymentlist><payment amount="0.00" id="" status="B">%s</payment></paymentlist><writeofflist/></charge>'
           % (CID, c.get("insportion"), c.get("patportion") or "0.00", c.get("insbalance"), c.get("patbalance") or "0.00", prof, reason_xml))
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="" amount="0.00" paycode="PE" woamount="0.00" paymethod="9" carrierid="%s" '
           'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), PID, carid, DEPOSIT, "re-post with reason codes (probe 9/12/2026, William OK)", CHECK, chg))
    r = amd.post(xml); L("%s -> %s %s" % (label, 'success="1"' in r, re.sub(r"\s+", " ", r[:220])))
    time.sleep(0.8); p, ib, pb = pays(); L("  readback: %s insbal %s patbal %s" % (p, ib, pb))
    new = [x for x in p if x[3] != "1" and x[1] in ("0.00", "0") and x[0] != BADPAY]
    return new
shapes = [
 ('<payreasonlist><payreason code="OA23" amount="%s"/><payreason code="PR2" amount="%s"/></payreasonlist>' % (PRIOR_PAID, COINS), "shape A payreasonlist/payreason code+amount"),
 ('<reasonlist><reason code="OA23" amount="%s" group="OA"/><reason code="PR2" amount="%s" group="PR"/></reasonlist>' % (PRIOR_PAID, COINS), "shape B reasonlist/reason code+amount+group"),
]
result = "none"
for reason_xml, label in shapes:
    new = post(reason_xml, label)
    with_reasons = [x for x in new if x[4]]
    if with_reasons:
        result = "%s WORKS: payment %s reasons %s" % (label, with_reasons[0][0], with_reasons[0][4]); L(result); break
    for x in new:   # a probe payment that landed without reasons blocks the claim again - void it
        ok, msg = void_tx.void_payment(PID, CID, x[0]); L("  probe payment %s had no reasons -> voided %s %s" % (x[0], ok, msg))
    time.sleep(0.5)
L("final: %s" % (pays(),)); L("RESULT: " + result)
