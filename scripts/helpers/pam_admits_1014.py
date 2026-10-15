# PLAIN ENGLISH (Pam's admit emails -> chart check, 10/14/2026 chat pass) - reads only.
# Decides: nothing. For each patient name from Pam Garland-G's admit emails (subject = patient name), finds the AMD chart(s)
# with lookuppatient (parsed as bytes - the reply declares ISO-8859-1), and lists each chart's plans, so the pass knows which
# admits still need their facesheet OCRed for insurance / demographics. Prints chart ids, DOBs and masked member ids only.
# Never touches: AMD writes.
import amd, re, sys, json
import xml.etree.ElementTree as ET
amd.login_cached()

def lookup(last, first):
    name = "%s,%s%%" % (last.upper(), first.upper()[:3])
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": name, "nocookie": "1"}))
    try: root = ET.fromstring(r.encode("latin-1", "ignore"))
    except ET.ParseError: return [], r[:200]
    rows = []
    for p in root.iter("patient"):
        rows.append({"id": re.sub(r"\D", "", p.get("id") or ""), "name": p.get("name"), "chart": p.get("chart"), "dob": p.get("dob")})
    return rows, ""

def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    out = []
    for tag in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', tag))
        if a.get("id"):
            n = a.get("subscribernum", "")
            out.append({"id": a["id"], "carrier": a.get("carrier"), "seq": a.get("sequence"), "begin": a.get("begindate"), "end": a.get("enddate"), "member_masked": "*" * max(0, len(n) - 4) + n[-4:], "elig": a.get("eligibilitystatusid")})
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', r)
    pat = re.search(r'<patient [^>]*>', r); pa = dict(re.findall(r'(\w+)="([^"]*)"', pat.group(0))) if pat else {}
    return out, (m.group(1) if m else None), pa.get("dob"), pa.get("deceased")

names = [x.split("|") for x in sys.argv[1:]]   # "LAST|FIRST|email-date|facility"
res = {}
for last, first, when, fac in names:
    rows, err = lookup(last, first)
    rec = {"when": when, "facility": fac, "charts": []}
    for r in rows:
        pl, order, dob, dec = plans(r["id"])
        rec["charts"].append({"pid": r["id"], "chart": r["chart"], "dob": dob or r["dob"], "deceased": dec, "insorder": order, "plans": pl})
    if err: rec["err"] = err
    res["%s,%s" % (last, first)] = rec
    print("%s,%s (%s %s): %d chart(s)" % (last, first, when, fac, len(rows)))
    for c in rec["charts"]:
        print("   pat%s chart %s dob %s insorder %s deceased %s plans %s" % (c["pid"], c["chart"], c["dob"], c["insorder"], c["deceased"], [(p["carrier"], p["seq"], p["begin"], p["end"], p["member_masked"]) for p in c["plans"]]))
json.dump(res, open("pam_admits_1014.json", "w"), indent=1)
