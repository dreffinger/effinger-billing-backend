# PLAIN ENGLISH (Void a payment or write-off)
# Decides: Nothing by itself. Voids one payment or write-off on one charge, the way Payment Entry's Void button does.
# Rules it uses: Only called by scripts that have decided a posting was wrong (CO24 restore, GV rebill).
# Never touches: Charges or claims.
# ---
"""Void a write-off / payment on a charge (captured from William's Payment-Entry Void, 9/2/2026).
action="void" class="void" patientid="patN" child <patient id="patN"><charge id="CID" void="0"><writeoff id="WOID"/></charge></patient>
(payment: <payment id="PID"/> presumably)."""
import amd, resave, re, sys, time
def void_writeoff(pid, cid, woid):
    pid = "pat%s" % re.sub(r"\D", "", str(pid)); cid = re.sub(r"\D", "", str(cid)); woid = re.sub(r"\D", "", str(woid))
    r = amd.post(amd.msg("void", "void", {"patientid": pid, "nocookie": "1"},
        '<patient id="%s"><charge id="%s" void="0"><writeoff id="%s"/></charge></patient>' % (pid, cid, woid)))
    return ("Fault" not in r), (re.search(r"<description>([^<]*)", r).group(1)[:200] if "Fault" in r else re.sub(r"\s+", " ", r)[100:260])
def void_payment(pid, cid, payid):
    pid = "pat%s" % re.sub(r"\D", "", str(pid)); cid = re.sub(r"\D", "", str(cid)); payid = re.sub(r"\D", "", str(payid))
    r = amd.post(amd.msg("void", "void", {"patientid": pid, "nocookie": "1"},
        '<patient id="%s"><charge id="%s" void="0"><payment id="%s"/></charge></patient>' % (pid, cid, payid)))
    return ("Fault" not in r), (re.search(r"<description>([^<]*)", r).group(1)[:200] if "Fault" in r else re.sub(r"\s+", " ", r)[100:260])
def charge_state(cid):
    x = resave.detail(cid)
    ch = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<charge [^>]*>', x).group(0)))
    wos = [dict(re.findall(r'(\w+)="([^"]*)"', w)) for w in re.findall(r'<writeoff [^>]*>', x)]
    pays = [dict(re.findall(r'(\w+)="([^"]*)"', p)) for p in re.findall(r'<payment [^>]*>', x)]
    return ch, wos, pays
if __name__ == "__main__":
    print(void_writeoff(*sys.argv[1:4]))

def void_unapplied(paymentid):
    """Void an UNAPPLIED credit (captured from William 9/3/2026): action voidpayment class=void, <payment id=ACTVPAYMENTID/>.
    Use the unappliedpayment's actvpaymentid from gettxhistory (e.g. 10106982), not the tx-history row id."""
    pid = re.sub(r"\D", "", str(paymentid))
    r = amd.post(amd.msg("voidpayment", "void", {"nocookie": "1"}, '<payment id="%s"/>' % pid))
    return ("Fault" not in r), re.sub(r"\s+", " ", r)[100:260]

def void_charge(pid, cid):
    """Void a CHARGE (proven 9/4/2026 on Craft): action=void class=void <patient id=patN><charge id=CID void="1"/></patient>."""
    pid = re.sub(r"\D", "", str(pid)); cid = re.sub(r"\D", "", str(cid))
    r = amd.post(amd.msg("void", "void", {"patientid": "pat" + pid, "nocookie": "1"}, '<patient id="pat%s"><charge id="%s" void="1"/></patient>' % (pid, cid)))
    return ('success="1"' in r), re.sub(r"\s+", " ", r)[100:260]
