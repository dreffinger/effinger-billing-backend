# PLAIN ENGLISH (AMD's own eligibility check - the free one, William's capture re-pasted 9/7/2026)
# Decides: Nothing. Runs AMD's real-time eligibility (EligibilityDetailsLegacy/checkEligibility) on one insurance plan and turns the 271 into a short answer: active or not on the chart plan, plan dates, Medicare Part A/B dates, any Advantage / other payer the payer names (with member ids), hospice, date of death, address on file with the payer, and every AAA rejection reason. Saves the raw 271 and the summary under patient_db/<patientid>/ so the answer is never re-bought.
# Rules it uses: amd.check_eligibility(insplan id) - one call per plan; the payer answers for TODAY (no DOS in this call). Cached per plan per day.
# Never touches: Charts, plans, claims.
# ---
"""Usage: python3 elig_amd.py <patientid> [--all]   (default: the active plans on the chart; --all = every plan)
        python3 elig_amd.py --ins <insplanid>"""
import amd, json, re, sys, os, datetime
import xml.etree.ElementTree as ET
DB = "patient_db"
def plans(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    pl = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<insplan ([^>]*)>', r)]
    return a, pl
def _json271_to_xml(obj):
    """11/6/2026: AMD's checkEligibility sometimes answers JSON ({"PPMDResults":{"Results":{"@attr":..,"Edi271":{..}}}},
    attributes as "@name", children as dicts/lists) - rebuild the XML tree so summarize() reads it unchanged."""
    def build(tag, val, parent):
        el = ET.SubElement(parent, tag) if parent is not None else ET.Element(tag)
        if isinstance(val, dict):
            for k, v in val.items():
                if k.startswith("@"): el.set(k[1:], "" if v is None else str(v))
                elif k == "#text": el.text = "" if v is None else str(v)
                elif isinstance(v, list):
                    for item in v: build(k, item, el)
                else: build(k, v, el)
        elif val is not None: el.text = str(val)
        return el
    root_tag = next(iter(obj)); return build(root_tag, obj[root_tag], None)
def summarize(xml_text):
    """271 -> plain summary."""
    t = xml_text.lstrip()
    if t.startswith("{"):
        root = _json271_to_xml(json.loads(t))
    else:
        root = ET.fromstring(xml_text)
    res = root.find("Results"); out = {"status": None, "amd": dict(res.attrib) if res is not None else {}}
    aaa = [dict(x.attrib) for x in root.iter("RequestValidation")] + [dict(x.attrib) for x in root.iter("AAASegment")]
    out["aaa"] = [{k.split("_", 1)[-1]: v for k, v in a.items() if v} for a in aaa]
    ebs = []
    for wrap in root.iter("EligibilityOrBenefitInformation"):
        if wrap.attrib.get("EB01_EligibilityOrBenefitInformationCode"): continue      # the inner EB element itself
        inner = wrap.find("EligibilityOrBenefitInformation")
        if inner is None or not inner.attrib.get("EB01_EligibilityOrBenefitInformationCode"): continue
        a = inner.attrib
        e = {"code": a.get("EB01_EligibilityOrBenefitInformationCode"), "stc": a.get("EB03_ServiceTypeCode"), "type": a.get("EB04_InsuranceTypeCode"), "plan": a.get("EB05_PlanCoverageDescription"), "amount": a.get("EB07_MonetaryAmount"), "dates": [], "entities": [], "msgs": []}
        for n in wrap.iter():
            if n is inner: continue
            if n.tag == "DTPSegment": e["dates"].append((n.attrib.get("DTP01_DateTimeQualifier"), n.attrib.get("DTP03_DateTimePeriod")))
            elif n.attrib.get("NM103_LastOrOrganizationalName"): e["entities"].append({"role": n.attrib.get("NM101_EntityIdentifierCode"), "name": n.attrib.get("NM103_LastOrOrganizationalName"), "id": n.attrib.get("NM109_IdentificationCode")})
            elif n.tag == "MSGSegment": e["msgs"].append(n.attrib.get("MSG01_FreeFormMessageText"))
            elif n.attrib.get("REF02_ReferenceIdentification"): e["entities"].append({"role": n.attrib.get("REF01_ReferenceIdentificationQualifier"), "id": n.attrib.get("REF02_ReferenceIdentification")})
            elif n.attrib.get("PER03_CommunicationNumberQualifier"): e["msgs"].append("contact %s" % n.attrib.get("PER04_CommunicationNumber"))
        ebs.append(e)
    out["eb"] = ebs
    sub = next((n.attrib for n in root.iter("Name") if n.attrib.get("NM101_EntityIdentifierCode") == "IL"), {})
    out["subscriber"] = {"name": "%s, %s %s" % (sub.get("NM103_LastOrOrganizationalName"), sub.get("NM104_FirstName"), sub.get("NM105_MiddleName") or ""), "id": sub.get("NM109_IdentificationCode")}
    ad = next((n.attrib for n in root.iter("Address")), {}); cz = next((n.attrib for n in root.iter("CityStateZipCode")), {})
    out["address"] = " ".join(x for x in [ad.get("N301_AddressInformation"), ad.get("N302_AddressInformation"), cz.get("N401_CityName"), cz.get("N402_StateOrProvinceCode"), cz.get("N403_PostalCode")] if x)
    dmg = next((n.attrib for n in root.iter("DemographicInformation")), {}); out["dob"] = dmg.get("DMG02_DateTimePeriod"); out["sex"] = dmg.get("DMG03_GenderCode")
    for d in root.iter("DTPSegment"):
        if d.attrib.get("DTP01_DateTimeQualifier") == "442": out["date_of_death"] = d.attrib.get("DTP03_DateTimePeriod")
    act = [e for e in ebs if e["code"] == "1"]; inact = [e for e in ebs if e["code"] == "6"]
    out["status"] = "ACTIVE" if act else ("INACTIVE" if inact else ("REJECTED " + "; ".join(a.get("AAA03_RejectReasonCode", "") + " " + a.get("AAA04_FollowUpActionCode", "") for a in out["aaa"]) if out["aaa"] else "UNKNOWN"))
    def dates(code): return sorted({d[1] for e in ebs if e["type"] == code and e["code"] == "1" for d in e["dates"] if d[0] in ("291", "346", "356")})
    out["partA"] = dates("MA"); out["partB"] = dates("MB")
    out["other_payers"] = [{"code": e["code"], "type": e["type"], "plan": e["plan"], "entities": e["entities"], "dates": e["dates"]} for e in ebs if e["code"] in ("R", "U", "X", "Y") or e["type"] in ("HM", "HN", "PR", "PS", "MC", "MD", "IN")]
    out["hospice"] = [e for e in ebs if e["stc"] == "45" and e["code"] == "1"]
    out["plan_dates"] = sorted({d[1] for e in act for d in e["dates"] if d[0] in ("291", "346", "356")})
    return out
def run_plan(pid, insid, force=False):
    day = datetime.date.today().strftime("%Y%m%d"); d = os.path.join(DB, str(pid)); os.makedirs(d, exist_ok=True)
    raw = os.path.join(d, "elig_%s_%s.xml" % (insid, day)); summ = os.path.join(d, "elig_%s_%s.json" % (insid, day))
    if os.path.exists(summ) and not force: return json.load(open(summ))
    code, j = amd.check_eligibility(insid); text = j if isinstance(j, str) else json.dumps(j)
    open(raw, "w").write(text)
    try: s = summarize(text)
    except Exception as e: s = {"status": "PARSE ERROR %s" % str(e)[:80], "http": code, "head": text[:300]}
    s["insplan"] = insid; s["checked"] = day; json.dump(s, open(summ, "w"), indent=1); return s
def one_line(s):
    return "%s | plan %s | A %s B %s | others %s | death %s | addr %s | aaa %s" % (s.get("status"), ",".join(s.get("plan_dates") or []), ",".join(s.get("partA") or []), ",".join(s.get("partB") or []),
        "; ".join("%s %s %s" % (o.get("type"), o.get("plan") or "", " ".join("%s:%s" % (x.get("name") or x.get("role"), x.get("id") or "") for x in o.get("entities") or [])) for o in s.get("other_payers") or [])[:160], s.get("date_of_death") or "-", s.get("address"), s.get("aaa"))
if __name__ == "__main__":
    a = sys.argv[1:]; amd.login_cached()
    if "--ins" in a: print(json.dumps(run_plan("x", a[a.index("--ins") + 1], True), indent=1)); sys.exit()
    pid = a[0]; pa, pl = plans(pid)
    for p in pl:
        if p.get("enddate") and "--all" not in a: continue
        s = run_plan(pid, p["id"].replace("ins", ""), "--force" in a)
        print("%s seq %s %s %s -> %s" % (pa.get("name"), p.get("sequence"), p.get("carrier"), p.get("subscribernum"), one_line(s)))
