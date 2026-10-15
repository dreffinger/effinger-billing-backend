# PLAIN ENGLISH (Read-only chart and column dump for the 2026-10-15T0510Z run)
# Decides: Nothing. Parses the before-scan XML (exclusions, unbilled), reads demographics for the charts
# this run must touch and the transaction history of the visits William answered on the board.
# Rules it uses: Read-only. Writes work/read_1015_0510.json for the action scripts to use.
# Never touches: Anything in AdvancedMD.
import amd, txh, json, glob, os, sys, time, re
import xml.etree.ElementTree as ET
amd.login_cached()
out = {"exclusions": [], "unbilled": [], "demo": {}, "tx": {}}
# A. exclusions
for f in sorted(glob.glob("scan_2026-10-15/excl_*_before.xml")):
    r = ET.parse(f).getroot()
    for v in r.iter("visit"):
        errs = [e.get("name") or e.get("text") or ET.tostring(e)[:200].decode() for e in v.iter("error")]
        chg = [{"cid": c.get("id"), "dos": (c.get("dos") or "").strip(), "cpt": c.get("chgcode"), "fee": c.get("totalfee"), "ins": c.get("insportion"), "pat": c.get("patportion"), "mods": c.get("modifiers"), "dx": c.get("diagcode")} for c in v.iter("charge")]
        out["exclusions"].append({"run": v.get("claimrunid"), "vid": v.get("id"), "claimid": v.get("claimid"), "pid": v.get("patientid"), "carrier": v.get("carriercodeshort") or v.get("carriercode"), "cpid": v.get("carriercpid"), "errs": errs, "charges": chg})
# B. unbilled
r = ET.parse("scan_2026-10-15/unbilled_before.xml").getroot()
for v in r.iter("visit"):
    errs = [e.get("name") for e in v.iter("error")]
    chg = [{"cid": c.get("id"), "dos": (c.get("dos") or "").strip(), "cpt": c.get("chgcode"), "fee": c.get("totalfee"), "billins": c.get("billinsurance"), "fin": c.get("finclassdescrip"), "dx": c.get("diagcode")} for c in v.iter("charge")]
    out["unbilled"].append({"vid": v.get("id"), "pid": v.get("patientid"), "carrier": v.get("carriercode"), "errs": errs, "charges": chg})
# C. demographics
def demo(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
    root = ET.fromstring(r.encode("latin-1", "ignore"))
    p = root.find(".//patient")
    if p is None: return {"raw": r[:300]}
    d = {"name": p.get("name"), "dob": p.get("dob"), "sex": p.get("sex"), "insorder": p.get("insorder"), "ssn": "yes" if (p.get("ssn") or "").strip() else "no", "plans": [], "refplans": []}
    a = root.find(".//address")
    if a is not None: d["addr"] = {k: a.get(k) for k in ("address1", "address2", "city", "state", "zipcode") if a.get(k) is not None}
    for ip in root.iter("insplan"):
        d["plans"].append({k: ip.get(k) for k in ("id", "carrier", "carriername", "subscribernum", "begindate", "enddate", "sequence", "coverage", "relationship", "grpnum", "eligibilitydate", "eligibilitystatus") if ip.get(k) is not None})
    for rp in root.iter("refplan"):
        d["refplans"].append({k: rp.get(k) for k in ("id", "ismain", "preauth", "begindate", "enddate", "refprov", "status") if rp.get(k) is not None})
    return d
pids = set(a for a in sys.argv[1:] if a.isdigit())
for pid in sorted(pids):
    try: out["demo"][pid] = demo(pid)
    except Exception as e: out["demo"][pid] = {"error": str(e)[:200]}
    time.sleep(0.3)
# D. tx history per visit
def tx(pid, vid):
    root = txh.fetch_visit(pid, vid)
    res = []
    for c in root.iter("charge"):
        a = c.attrib
        row = {k: a.get(k) for k in ("id", "dos", "proccode", "carrier", "amount", "insbal", "patbal", "paid", "billdate", "void", "visit", "modifiers", "payerinfo", "insbilled", "diagcodes", "provcode", "facname") if a.get(k) is not None}
        row["payments"] = [{k: p.get(k) for k in ("id", "amount", "carrier", "date", "checknumber", "void", "type", "code", "origrefnum", "reasons", "actvpaymentid", "writeoffcode", "payreasonwoamount") if p.get(k) is not None} for p in c.iter("payment")]
        row["_attrs"] = sorted(a.keys())
        res.append(row)
    return res
visits = [a for a in sys.argv[1:] if ":" in a]
for pv in visits:
    pid, vid = pv.split(":")
    try: out["tx"][pv] = tx(pid, vid)
    except Exception as e: out["tx"][pv] = {"error": str(e)[:200]}
    time.sleep(0.3)
os.makedirs("work", exist_ok=True)
json.dump(out, open("work/read_1015_0510.json", "w"), indent=1)
print("exclusions", len(out["exclusions"]), "unbilled", len(out["unbilled"]), "demo", len(out["demo"]), "tx", len(out["tx"]))
