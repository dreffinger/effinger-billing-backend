# PLAIN ENGLISH (Claimocity feed vs AMD)
# Decides: For each hospital patient in the Claimocity HL7 drop, whether the hospital's insurance (IN1) matches what AMD has.
# Rules it uses: Matches by name + DOB. Writes a report; read-only.
# Never touches: AMD - it only reports differences.
# ---
"""Claimocity HL7 DFT^P03 -> insurance diff against AdvancedMD.
Parses every *.hl7 under the staged 'Claimocity drop' folder, pulls PID/IN1/PV1/FT1/DG1,
matches each patient to AMD (name + DOB), compares the facility's IN1 plans with the AMD
insplans, and writes claimocity_in1_report.json / .md.  READ-ONLY against AMD.
Usage: python3 claimocity_in1.py [folder]   (default: the staged Drive folder)
"""
import glob, json, os, re, sys, time, collections
import xml.etree.ElementTree as ET
import amd

FOLDER = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/billing agent project files/Claimocity drop"
CARRIERS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "carriers.json")))  # car6085 -> [code, name]
CODE2NAME = {v[0]: v[1] for v in CARRIERS.values()}
ID2CODE = {k: v[0] for k, v in CARRIERS.items()}

# facility payer text -> AMD carrier code (extend as new names show up; None = ignore / needs review)
PAYER_MAP = [
    (r"MEDICARE A\b|FCSO|MEDICARE PART A|MEDICARE B\b|TRADITIONAL MEDICARE|^MEDICARE$", "FLO02"),
    (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"WELLCARE", "WEL04"), (r"HUMANA", "HUM01"),
    (r"CAPITAL HEALTH", "CAP07"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY CARE|FCC\b", "FLO99"),
    (r"UNITED ?HEALTH|UHC|AARP MEDICARE ADV", "UNI20"), (r"AARP", "AAR01"), (r"AETNA", "AET07"),
    (r"CIGNA", "CIG09"), (r"FLORIDA BLUE|BCBS|BLUE CROSS", "BCBS"), (r"TRICARE FOR LIFE|TFL", "TRI05"),
    (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03"), (r"VA COMMUNITY|VACCN|VETERAN", "VACCN"),
    (r"MEDICAID(?! MANAGED)|AHCA|FLORIDA MEDICAID", "MCAD"), (r"MOLINA", "MOL01"),
]

def map_payer(*fields):
    """Try each field in priority order (plan id, company, then plan name) so a company like
    SUNSHINE isn't overridden by a plan name like 'Medicare A coinsurance from Medicaid'."""
    for text in fields:
        t = (text or "").upper()
        if not t.strip():
            continue
        for pat, code in PAYER_MAP:
            if re.search(pat, t):
                return code
    return None

def parse_file(path):
    raw = open(path, encoding="latin-1").read()
    msgs = []
    for block in re.split(r"(?=MSH\|)", raw):
        if not block.startswith("MSH|"):
            continue
        m = {"file": os.path.basename(path), "dg1": [], "in1": [], "ft1": []}
        for seg in re.split(r"\r\n|\r|\n", block):
            f = seg.split("|")
            if f[0] == "MSH":
                m["facility"] = f[3].split("^")[-1] if len(f) > 3 else ""
                m["msgtime"] = f[6] if len(f) > 6 else ""
            elif f[0] == "PID":
                nm = f[5].split("^") if len(f) > 5 else [""]
                m["last"], m["first"] = nm[0].strip().upper(), (nm[1] if len(nm) > 1 else "").strip().upper()
                m["dob"] = f[7][:8] if len(f) > 7 else ""
                m["sex"] = f[8] if len(f) > 8 else ""
                m["claimocity_id"] = f[3].split("^")[0] if len(f) > 3 else ""
            elif f[0] == "DG1" and len(f) > 3:
                m["dg1"].append(f[3].split("^")[0])
            elif f[0] == "PV1" and len(f) > 7:
                m["attending"] = f[7].split("^")[0]
            elif f[0] == "IN1":
                g = lambda i: f[i] if len(f) > i else ""
                m["in1"].append({"seq": g(1), "plan": g(2).split("^")[0], "company": g(4), "addr": g(5).replace("^", " ").strip(),
                                 "eff": g(12), "end": g(13), "planname": g(8) or g(15), "subscriber": g(16).replace("^", " "),
                                 "rel": g(17), "policy": g(49) or g(36), "raw": seg[:300]})
            elif f[0] == "FT1":
                g = lambda i: f[i] if len(f) > i else ""
                m["ft1"].append({"dos": g(4)[:8], "cpt": g(25).split("^")[0], "units": g(10), "dx": g(19)})
        if "last" in m:
            msgs.append(m)
    return msgs

def amd_lookup(last, first, dob):
    r = amd.post('<ppmdmsg action="lookuppatient" class="lookup" msgtime="%s" name="%s,%s%%" nocookie="1"/>' % (amd._msgtime(), last, first[:3]))
    cands = [p.attrib for p in ET.fromstring(r).iter("patient")]
    d = "%s/%s/%s" % (dob[4:6], dob[6:8], dob[:4]) if len(dob) == 8 else ""
    hit = [p for p in cands if p.get("dob") == d] or cands[:1]
    return hit[0] if hit else None

def amd_plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    root = ET.fromstring(r)
    p = root.find(".//patient")
    order = (p.get("insorder") or "") if p is not None else ""
    plans = []
    for ip in root.iter("insplan"):
        plans.append({"id": ip.get("id"), "carrier": ID2CODE.get(ip.get("carrier"), ip.get("carrier")), "seq": ip.get("sequence"),
                      "begin": ip.get("begindate"), "end": ip.get("enddate"), "sub": ip.get("subscribernum"),
                      "active": ip.get("sequence") in order.split(",")})
    return order, plans

def main():
    files = sorted(glob.glob(os.path.join(FOLDER, "*.hl7")))
    msgs = [m for f in files for m in parse_file(f)]
    print("files", len(files), "messages", len(msgs), "with IN1", sum(1 for m in msgs if m["in1"]))
    seen, report = {}, []
    for m in msgs:
        key = (m["last"], m["first"], m["dob"])
        if key in seen:
            seen[key]["visits"].append(m["ft1"]); continue
        entry = {"patient": "%s,%s" % (m["last"], m["first"]), "dob": m["dob"], "facility": m.get("facility"), "attending": m.get("attending"),
                 "visits": [m["ft1"]], "facility_plans": [{**i, "amd_code": map_payer(i["plan"], i["company"], i["planname"])} for i in m["in1"]],
                 "amd": None, "status": "no-IN1" if not m["in1"] else "pending"}
        seen[key] = entry; report.append(entry)
    for e in report:
        if e["status"] == "no-IN1":
            continue
        try:
            last, first = e["patient"].split(",")
            p = amd_lookup(last, first, e["dob"])
            if not p:
                e["status"] = "NOT IN AMD"; continue
            order, plans = amd_plans(p["id"])
            e["amd"] = {"id": p["id"], "name": p.get("name"), "dob": p.get("dob"), "insorder": order, "plans": plans}
            fac = [x["amd_code"] for x in e["facility_plans"] if x["amd_code"]]
            active = [x["carrier"] for x in plans if x["active"]]
            unmapped = [x["plan"] for x in e["facility_plans"] if not x["amd_code"]]
            if unmapped:
                e["status"] = "UNMAPPED PAYER: " + "; ".join(unmapped)
            elif fac and fac[0] != (active[0] if active else None):
                e["status"] = "PRIMARY MISMATCH: facility %s vs AMD %s" % (fac[0], active[0] if active else "none")
            elif set(fac) - set(active):
                e["status"] = "MISSING IN AMD: " + ",".join(sorted(set(fac) - set(active)))
            else:
                e["status"] = "match"
        except Exception as ex:
            e["status"] = "ERROR " + str(ex)[:120]
        time.sleep(0.4)
    json.dump(report, open("claimocity_in1_report.json", "w"), indent=1)
    cnt = collections.Counter(e["status"].split(":")[0] for e in report)
    print(dict(cnt))
    with open("claimocity_in1_report.md", "w") as f:
        f.write("# Claimocity IN1 vs AMD insurance — %s\n\n" % time.strftime("%m/%d/%Y %H:%M"))
        for e in report:
            if e["status"] in ("match", "no-IN1"):
                continue
            f.write("- **%s** (DOB %s, %s) — %s\n" % (e["patient"], e["dob"], e["facility"], e["status"]))
            for x in e["facility_plans"]:
                f.write("    - facility seq %s: %s / %s eff %s policy %s -> %s\n" % (x["seq"], x["plan"], x["company"], x["eff"], x.get("policy", ""), x["amd_code"]))
            if e["amd"]:
                f.write("    - AMD order %s: %s\n" % (e["amd"]["insorder"], ", ".join("%s(seq %s%s)" % (p["carrier"], p["seq"], "" if p["active"] else " inactive") for p in e["amd"]["plans"])))
    print("wrote claimocity_in1_report.md")

if __name__ == "__main__":
    main()
