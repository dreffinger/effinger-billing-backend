# PLAIN ENGLISH (Post a PATIENT check to named charges - first use 11/19/2026, William: "just post them anyway you can")
# Decides: Nothing. The board card of chart 17477639: the guardian's check #9301, $433.00, pays the 9/2/2026 visit (99344 $300 +
#          99497 $133). This posts ONE patient payment the way Payment Entry's patient tab does - the same `addpayments` call the
#          patient write-off uses (patient_writeoff.py, proven 10/13/2026): paysource="1" (patient), no carrier, amount = the
#          check, paymethod 11 (check), each charge echoed with its live balances and a payment line of its share, no write-off.
#          Re-reads every charge live first and refuses when a share is more than that charge's live PATIENT balance; after the
#          post it reads the chart back and prints each charge's balance and the payment found on it.
# Never touches: insurance balances, other charges, write-offs.
# Usage: python3 patient_pay_1119.py <checknumber> <deposit mm/dd/yyyy> <chargeid>=<amount> [<chargeid>=<amount> ...] [--live]
import amd, resave, txh, re, sys, time
a = [x for x in sys.argv[1:] if not x.startswith("--")]; live = "--live" in sys.argv
check, dep = a[0], a[1]; shares = [(x.split("=")[0], float(x.split("=")[1])) for x in a[2:]]
amd.login_cached(); chg = ""; pid = None; tot = 0.0
for cid, amt in shares:
    t = resave.detail(cid)
    vis = re.search(r'<visit [^>]*>', t); c = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, t); pat = re.search(r'<patient [^>]*id="(?:pat)?(\d+)"', t)
    if not (vis and c and pat): print("charge %s not found" % cid); sys.exit(1)
    d = dict(re.findall(r'(\w+)="([^"]*)"', c.group(0))); prof = re.search(r'profile="([^"]*)"', vis.group(0)).group(1); pid = pat.group(1)
    patbal = float(d.get("patbalance") or 0)
    print("chg%s pat%s patient balance %.2f insurance balance %s -> pay %.2f" % (cid, pid, patbal, d.get("insbalance"), amt))
    if amt > patbal + 0.005: print("REFUSED - more than the live patient balance"); sys.exit(1)
    chg += ('<charge id="charge%s" allowed="%s" insportion="%s" patportion="%s" insbalance="%s" patbalance="%.2f" profile="%s">'
            '<paymentlist><payment amount="%.2f" id="" status="B"/></paymentlist><writeofflist/></charge>'
            % (cid, d.get("allowed") or d.get("fee") or "0.00", d.get("insportion") or "0.00", d.get("patportion") or "%.2f" % patbal, d.get("insbalance") or "0.00", patbal, prof, amt))
    tot += amt
xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
       '<patient patientid="pat%s" paysource="1" postingmethod="" amount="%.2f" paycode="PE" woamount="0.00" paymethod="11" carrierid="" '
       'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
       '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
       % (amd._msgtime(), pid, tot, dep, "patient check %s" % check, check, chg))
if not live: print("DRY would post patient check %s $%.2f deposit %s on %d charge(s)" % (check, tot, dep, len(shares))); sys.exit(0)
r = amd.post(xml); print("addpayments ->", re.sub(r"\s+", " ", r[100:330])); time.sleep(1.0)
ids = {c for c, _ in shares}
for c in txh.fetch(pid).iter("charge"):
    if c.get("id") in ids:
        print("read back chg%s fee %s paid %s patbal %s insbal %s payments %s" % (c.get("id"), c.get("fee"), c.get("paid"), c.get("patbal"), c.get("insbal"),
              [(p.get("amount"), p.get("checknumber"), p.get("source"), p.get("void")) for p in c.iter("payment")]))
for u in txh.fetch(pid).iter("unappliedpayment"): print("UNAPPLIED on the chart:", dict(u.attrib))
