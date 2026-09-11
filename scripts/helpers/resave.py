# PLAIN ENGLISH (Full-visit resave)
# Decides: How to save a visit back to AMD safely: fetch the whole visit, echo every charge, then reinspect and approve.
# Rules it uses: Never save a visit from one charge's detail - AMD voids the charges you leave out. Cleans 01/01/1900 dates out of the claim fields.
# Never touches: Balances or insurance order on its own; callers pass those in.
# ---
"""Resave + reinspect + approve a visit, echoing detail attrs (proven pattern 8/29)."""
import amd, re, sys
import xml.etree.ElementTree as ET

def detail(chargeid):
    return amd.post(amd.msg('getchargedetaildataicd10','demographics',{'chargeid':str(chargeid),'nocookie':'1'}))

CHG_FIELDS = ["respparty","begindate","enddate","diagcodes","modcodes","aging","billins",
              "proccode","cobcode","pos","tos","units","netfee","fee","allowed",
              "patportion","insportion","patbalance","insbalance","finclasscode","lineitemnote"]

def _extins_xml(vis, hospfrom):
    """Echo the visit's full extins attr set, overriding hospitalizationfrom only."""
    base = {"id": "", "hospitalizationto": "", "unabletoworkfrom": "", "unabletoworkto": "",
            "datesimilarsymptom": "", "dateofinjury": "", "otheraccident": "0", "emergency": "0",
            "employment": "0", "outsidelab": "0", "payprov": "1", "patsignature": "1", "epsdt": "0",
            "accidentstate": "", "autoaccident": "0", "datelastseen": "", "resubmissioncode": "",
            "origrefnum": ""}
    e = vis.find("extins")
    if e is not None:
        for k, v in e.attrib.items():
            base[k] = v
    base["hospitalizationfrom"] = hospfrom
    return "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in base.items())

def resave(anychargeid, batchid, hospfrom=None, extra_charge_xml=""):
    x = detail(anychargeid)
    root = ET.fromstring(x)
    pat = root.find(".//patient")
    vis = root.find(".//visit")
    charges = vis.findall(".//charge")
    chg_xml = ""
    for c in charges:
        attrs = {"id": c.get("id")}
        for f in CHG_FIELDS:
            v = c.get(f)
            if v is not None: attrs[f] = v
        a = " ".join('%s="%s"' % (k, v) for k, v in attrs.items())
        chg_xml += "<charge %s/>" % a
    vattrs = {"id": vis.get("id"), "date": vis.get("date"), "profile": vis.get("profile"),
              "insorder": vis.get("insorder"), "refplan": vis.get("refplan"),
              "facility": vis.get("facility"), "force": "1"}
    va = " ".join('%s="%s"' % (k, v) for k, v in vattrs.items() if v is not None)
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"),
         "approval": "1", "inspectorenabled": "1", "batchid": str(batchid),
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        '<visit %s><chargelist>%s%s</chargelist>%s</visit>' % (
            va, chg_xml, extra_charge_xml,
            _extins_xml(vis, hospfrom) if hospfrom else ""))
    return amd.post(body)

if __name__ == "__main__":
    hf = sys.argv[3] if len(sys.argv) > 3 else None
    print(resave(sys.argv[1], sys.argv[2], hf)[:3000])

def visit_charges(chargeid):
    """ALL live charges of the visit that owns `chargeid` (getchargedetaildataicd10 returns only ONE charge, and a
    resave that omits a sibling VOIDS it — learned the hard way 9/3/2026).  Returns (visit_elem, patient_elem,
    [charge_elem...]) with each charge element taken from its own detail call."""
    import xml.etree.ElementTree as ET, re
    x = detail(chargeid); root = ET.fromstring(x)
    vis = root.find(".//visit"); pat = root.find(".//patient")
    vid = re.sub(r"\D", "", vis.get("id")); pid = re.sub(r"\D", "", pat.get("id"))
    body = amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': '1', 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'})
    th = ET.fromstring(amd.post(body, timeout=120))
    ids = [c.get("id") for c in th.iter("charge") if c.get("visit") == vid and c.get("void") != "1" and not (c.get("fee") or "").startswith("-")]
    charges = []
    for cid in ids:
        r = ET.fromstring(detail(cid))
        c = [e for e in r.iter("charge") if e.get("id") == "charge" + cid]
        if c and c[0].get("void") != "1": charges.append(c[0])
    return vis, pat, charges

DATE_ATTRS = {"hospitalizationfrom", "hospitalizationto", "unabletoworkfrom", "unabletoworkto", "datesimilarsymptom", "dateofinjury", "datelastseen", "datelmp", "dateofsymptom"}
def clean_extins(attrs):
    """NEVER send an empty/space date attribute on updextrainsinfo: AMD stores it as 01/01/1900 and the claim rejects.
    Omit blank or 1900 date attrs (omission clears them).  Learned 9/4/2026 on Tillery."""
    return {k: v for k, v in attrs.items() if not (k in DATE_ATTRS and (not str(v).strip() or "1900" in str(v)))}
