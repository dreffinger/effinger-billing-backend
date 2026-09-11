# PLAIN ENGLISH (Parse PCC facesheets)
# Decides: Nothing. Extracts name, DOB, facility, MBI, Medicaid number and payer block from a PointClickCare Admission Record PDF.
# Rules it uses: SSN is never printed or stored.
# Never touches: AMD.
# ---
"""Parse PCC 'Admission Record' facesheet PDFs (pdftotext -layout): name, DOB, facility, MBI, Medicaid #, payer block.
SSN is never printed or stored.  Usage: python3 pcc_parse.py <pdf> [...]  -> JSON list on stdout"""
import subprocess, re, sys, json
def parse(path):
    t = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    lines = t.splitlines()
    out = {"file": path.split("/")[-1], "facility": (lines[1].strip() if len(lines) > 1 else ""), "payers": [], "records": []}
    for i, l in enumerate(lines):
        if "Resident Name" in l and i + 1 < len(lines):
            v = lines[i + 1].strip(); out["name"] = re.split(r"\s{3,}", v)[0]
            m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\S+)\s*$", v)
            if m: out["admit"] = m.group(1); out["resident_no"] = m.group(4)
        if l.strip().startswith("Sex") and "Birthdate" in l and i + 1 < len(lines):
            m = re.search(r"\b([MF])\s+(\d{2}/\d{2}/\d{4})", lines[i + 1]);
            if m: out["sex"] = m.group(1); out["dob"] = m.group(2)
        if "Medicare Beneficiary ID" in l and "Medicaid #" in l and i + 1 < len(lines):
            hdr = l; val = lines[i + 1]
            def col(label):
                p = hdr.find(label); 
                if p < 0: return ""
                seg = val[max(0, p - 12): p + len(label) + 14]
                m = re.search(r"[A-Z0-9]{8,}", seg); return m.group(0) if m else ""
            out["mbi"] = col("Medicare Beneficiary ID"); out["hic"] = col("Medicare (HIC) #"); out["medicaid"] = col("Medicaid #")
        if "Insurance Name:" in l and i + 1 < len(lines):
            out["insurance_name_line"] = re.sub(r"\s{2,}", " | ", lines[i + 1].strip())
        m = re.match(r"\s*(Primary|Second|Third|Fourth|Fifth|Sixth) Payer\s+(.*)$", l)
        if m:
            rest = m.group(2)
            rest = re.sub(r"\d{3}-\d{2}-\d{4}", "***", rest)
            out["payers"].append(m.group(1) + ": " + re.sub(r"\s{2,}", " | ", rest.strip()))
    # every MBI-looking token on the page (some sheets have several)
    out["mbis_seen"] = sorted(set(re.findall(r"\b\d[A-Z][A-Z0-9]\d[A-Z][A-Z0-9]\d[A-Z]{2}\d{2}\b", t)))
    out["medicaids_seen"] = sorted(set(re.findall(r"Medicaid #\s*(\d{10})", t)))
    return out
if __name__ == "__main__":
    res = [parse(p) for p in sys.argv[1:]]
    print(json.dumps(res, indent=1))
