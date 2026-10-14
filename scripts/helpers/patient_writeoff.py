# PLAIN ENGLISH (Patient-side write-off - captured 10/13/2026, William: "find a way to do this on the back end")
# Decides: nothing on its own. Writes off ONE charge's PATIENT balance with a practice write-off code, the way Payment Entry's
#   patient tab does: `addpayments` class=paymententry with paysource="1" (patient, not insurance), NO carrierid, amount 0,
#   woamount = the balance, and the charge echoed with its live patportion/patbalance plus a <writeoff code=...> line.
#   Proven 10/13/2026 on charge 22477857 (finclass SP, no plan, insorder empty): success="1", paymentid 10169045, patbalance
#   68.00 -> 0.00, the write-off shows in gettxhistory with source="1" and wocode WOBAD. An unknown code faults
#   "Cannot insert the value NULL into column 'WriteOffCodeFID'" - use a code from the Master Files list (WOBAD patient no-pay,
#   WOSMBAL, WOLATE, WOCAID2ND, WOMCAD, WOCLTREQ ...).
# Rules it uses: re-reads the charge live first; refuses when wo > the live patient balance; never touches the insurance side.
# Never touches: insurance balances, payments, other charges on the visit.
import amd, resave, re, time
def post(cid, wo, wocode, checknumber="", note="", dry=False):
    rt_txt = resave.detail(cid)
    vis = re.search(r'<visit [^>]*>', rt_txt); c = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, rt_txt)
    pat = re.search(r'<patient [^>]*id="(?:pat)?(\d+)"', rt_txt)
    if not (vis and c and pat): return False, "charge/visit/patient not found in detail"
    a = dict(re.findall(r'(\w+)="([^"]*)"', c.group(0))); prof = re.search(r'profile="([^"]*)"', vis.group(0)).group(1); pid = pat.group(1)
    patbal = float(a.get("patbalance") or 0)
    if wo > patbal + 0.005: return False, "over-apply: wo %.2f > patbalance %.2f" % (wo, patbal)
    chg = ('<charge id="charge%s" allowed="%s" insportion="%s" patportion="%s" insbalance="%s" patbalance="%.2f" profile="%s">'
           '<paymentlist><payment amount="0.00" id="" status="B"/></paymentlist><writeofflist><writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/></writeofflist></charge>'
           % (cid, a.get("allowed") or a.get("fee") or "0.00", a.get("insportion") or "0.00", a.get("patportion") or "%.2f" % patbal, a.get("insbalance") or "0.00", patbal, prof, wo, wocode))
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="1" postingmethod="" amount="0.00" paycode="PE" woamount="%.2f" paymethod="9" carrierid="" '
           'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, wo, time.strftime("%m/%d/%Y"), note.replace('"', "'"), checknumber, chg))
    if dry: return True, "DRY patbalance %.2f pid %s -> wo %.2f %s" % (patbal, pid, wo, wocode)
    r = amd.post(xml)
    return ('success="1"' in r), re.sub(r"\s+", " ", r[:200])
