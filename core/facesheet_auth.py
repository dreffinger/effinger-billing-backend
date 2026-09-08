# PLAIN ENGLISH (Facesheet authorization OCR)
# Decides: Which number on a hospital facesheet is the authorization, using OCR on the PDF.
# Rules it uses: VA 'Track' / B-prefixed numbers are tracking numbers, not billable auths.
# Never touches: AMD - it prints candidates for a person to confirm.
# ---
"""Extract the Authorization / referral number from a hospital facesheet PDF (HCA/TMH
print-to-PDF, image-based -> OCR). Usage: python3 facesheet_auth.py <pdf> [<pdf>...]
Prints: filename | payer | policy | auth candidates. Per William's VA rule, 'Track'/B-prefixed
numbers are TRACKING numbers, not billable auths — flagged as such."""
import sys, re, subprocess, os, tempfile

def ocr(pdf):
    d = tempfile.mkdtemp()
    subprocess.run(["pdftoppm", "-r", "220", "-png", pdf, os.path.join(d, "p")],
                   check=True, capture_output=True)
    txt = ""
    for f in sorted(os.listdir(d)):
        if f.endswith(".png"):
            r = subprocess.run(["tesseract", os.path.join(d, f), "-"], capture_output=True, text=True)
            txt += r.stdout + "\n"
    return txt

def extract(txt):
    out = {}
    m = re.search(r"Company\s+([A-Z][A-Z0-9 &/.-]{2,40})", txt)
    out["payer"] = m.group(1).strip() if m else None
    m = re.search(r"Policy\s*#\s*([A-Z0-9]{5,25})", txt)
    out["policy"] = m.group(1) if m else None
    # auth candidates: tokens after 'Authorization' up to Primary Care Physician
    seg = re.search(r"Authorization(.{0,200}?)Primary Care", txt, re.S)
    seg = seg.group(1) if seg else ""
    cands = re.findall(r"\b([A-Z]{0,3}\d{7,20}[A-Z0-9/-]*)\b", seg)
    out["auth_candidates"] = cands
    out["tracking_only"] = bool(re.search(r"Track", seg)) and all(c.startswith("B") for c in cands) if cands else False
    return out

if __name__ == "__main__":
    for pdf in sys.argv[1:]:
        t = ocr(pdf); e = extract(t)
        flag = "  (TRACKING# only — NOT a billable auth)" if e["tracking_only"] else ""
        print("%s | payer=%s | policy=%s | auth=%s%s" % (os.path.basename(pdf), e["payer"], e["policy"], e["auth_candidates"], flag))
