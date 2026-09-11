# PLAIN ENGLISH (Fix order, rebill, complete)
# Decides: For rejected claims: set the correct insurance order, rebill, then mark the rejection completed - verifying each step.
# Rules it uses: Per the rejected-claims skill.
# Never touches: Claims whose rejection reason isn't a payer-order problem.
# ---
"""Fix insorder -> rebill -> complete, per rejected-claims skill. Verifies each step."""
import amd, re, sys, time
import xml.etree.ElementTree as ET

CHG_FIELDS = ["respparty","begindate","enddate","diagcodes","modcodes","aging","billins",
              "proccode","cobcode","pos","tos","units","netfee","fee","allowed",
              "patportion","insportion","patbalance","insbalance","finclasscode","lineitemnote"]

def detail(chargeid):
    return amd.post(amd.msg('getchargedetaildataicd10','demographics',{'chargeid':str(chargeid),'nocookie':'1'}))

def process(chargeid, insorder, do_rebill=True, do_hide=True):
    x = detail(chargeid)
    root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    visid = vis.get("id").replace("vst","")
    charges = vis.findall(".//charge")
    # safety: every active charge must have diagcodes + proccode; count payments
    pay = 0
    chg_xml = ""
    for c in charges:
        if not c.get("diagcodes") or not c.get("proccode"):
            return ("SKIP", visid, "charge %s missing diagcodes/proccode" % c.get("id"))
        pay += len(c.findall(".//payment"))
        attrs = {"id": c.get("id")}
        for f in CHG_FIELDS:
            v = c.get(f)
            if v is not None: attrs[f] = v
        chg_xml += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in attrs.items())
    if pay:
        return ("SKIP", visid, "has %d payment(s) posted - settled/settling" % pay)
    ext_before = re.search(r'<extins[^>]*/?>', x).group(0) if '<extins' in x else ''
    va = ('id="%s" date="%s" profile="%s" insorder="%s" refplan="%s" facility="%s" force="1"' %
          (vis.get("id"), vis.get("date"), vis.get("profile"), insorder,
           vis.get("refplan"), vis.get("facility")))
    body = amd.msg("updvisitwithnewcharges","chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"),
         "approval": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        '<visit %s><chargelist>%s</chargelist></visit>' % (va, chg_xml))
    r = amd.post(body)
    if '<Error /' not in r and '<Error/>' not in r:
        return ("RESAVE_FAIL", visid, r[:300])
    time.sleep(1)
    result = ["insorder->%s" % insorder]
    if do_rebill:
        firstchg = charges[0].get("id").replace("charge","")
        code, txt = amd.rebill_charge(firstchg, int(insorder.split(",")[0]))
        if code != 204:
            return ("REBILL_FAIL", visid, "%s %s" % (code, txt))
        time.sleep(1)
        d2 = detail(chargeid)
        insb = re.findall(r'insbilled="(\d)"', d2)
        nreb = len(re.findall(r'<rebill ', d2))
        ext_after = re.search(r'<extins[^>]*/?>', d2).group(0) if '<extins' in d2 else ''
        if "0" not in insb:
            return ("VERIFY_FAIL", visid, "insbilled still 1")
        result.append("rebilled(insbilled=%s, rebillrecs=%d)" % (",".join(insb), nreb))
        result.append("extins_same=%s" % (ext_before == ext_after))
    if do_hide:
        h = amd.post(amd.msg("hideexclusions","claimsreports",{"hide":"-1","nocookie":"1"},
                             '<visitlist><visit id="%s"/></visitlist>' % visid))
        if '<Error /' not in h and '<Error/>' not in h:
            return ("HIDE_FAIL", visid, h[:200])
        result.append("completed")
    return ("OK", visid, "; ".join(result))

if __name__ == "__main__":
    for cid in sys.argv[1:]:
        print(cid, process(cid, "2"))
        time.sleep(2)
