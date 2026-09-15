#!/usr/bin/env python3
# PLAIN ENGLISH: Availity's Remittance Viewer prints two PDFs - "Check Summary" (CheckDetails /
# CheckMultipleDetails: one file per check, EVERY claim on it) and "Claim Summary" (ClaimDetails:
# one claim). Both carry the full 835 content as text: check trace + date + amount, payer, the
# payer claim number (ICN), the AMD account (visit id + claim letter), claim status code, claim
# frequency, rendering NPI, and per service line the line control number, DOS, CPT/modifiers/units,
# allowed (B6), charge, CAS group-reason codes with their amounts, RARCs, payer proprietary codes
# and the payment. This helper turns those PDFs (or their extracted text) into ERA-style rows the
# run can post, verify or work as denials - the same shape availity_paste.py emits. Reads a PDF
# with `pdftotext -raw` when available, else expects .txt. Names/member ids are dropped on output.
#
# Usage: python3 availity_pdf.py <file.pdf|file.txt> [...] [--csv out.csv] [--json out.json]
"""Availity Remittance Viewer Check/Claim Summary PDFs -> ERA-style rows."""
import csv, json, re, shutil, subprocess, sys

MONEY = r"-?\$-?[\d,]+\.\d{2}"
HDR = {
    "check": r"Check/EFT Trace Number:\s*(\S+)",
    "check_date": r"Check/EFT Date:\s*(\d{2}/\d{2}/\d{4})",
    "check_amount": r"(?:Payment Amount|Total Paid):\s*(" + MONEY + ")",
    "payer": r"(?:Payer Name:|Payer:)\s*(.+?)\s+(?:Patient Name:|Check/EFT|Payee)",
}
CLAIM_SPLIT = re.compile(r"(?=Patient Name:\s)")
CF = {  # claim-level fields, both layouts
    "icn": r"Claim Number:\s*([A-Z0-9]+)",
    "dos": r"Claim Date:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})",
    "status_code": r"Claim Status Code:\s*(\d+)",
    "acct": r"Patient (?:Ctrl Nmbr|Control Number):\s*(\d{7,9})([A-Z]?)",
    "charge": r"Claim Charge(?: Amount)?:\s*(" + MONEY + ")",
    "paid": r"Claim Payment(?: Amount)?:\s*(" + MONEY + ")",
    "patient_resp": r"Patient Resp(?:onsibility)?:\s*(" + MONEY + ")",
    "orig_ref": r"Original Ref (?:Nmbr|Number):\s*([A-Z0-9]+)",
    "frequency": r"Claim Frequency:\s*(\d)?",
    "received": r"Claim Received Date:\s*(\d{2}/\d{2}/\d{4})",
    "rendering_npi": r"Rendering (?:Prv|Provider) ID:\s*(\d{10})",
}
LINE = re.compile(r"(?<!\d)(\d{8})\s+(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\s+(.*?)(?=(?<!\d)\d{8}\s+\d{2}/\d{2}/\d{4}\s*-|Patient Name:|Code Descriptions|$)", re.S)
CAS = re.compile(r"\b(CO|PR|OA|PI|CR)-(\d{1,3})\b")
RARC = re.compile(r"\b(N\d{1,3}|M[A-Z]?\d{1,3})\b")
PAYERCODE = re.compile(r"\b([A-Z]{4,6})\b")
STATUS = {"1": "Processed as Primary", "2": "Processed as Secondary", "3": "Processed as Tertiary", "4": "Denied",
          "19": "Processed as Primary, forwarded", "20": "Processed as Secondary, forwarded", "22": "Reversal of Previous Payment"}

def money(s):
    s = s.replace("$", "").replace(",", "").replace("\\", "")
    return round(float(s), 2)

def text_of(path):
    if path.lower().endswith(".pdf"):
        if not shutil.which("pdftotext"): raise SystemExit("pdftotext not installed - pass extracted .txt")
        return subprocess.run(["pdftotext", "-raw", path, "-"], capture_output=True, text=True, check=True).stdout
    return open(path, encoding="utf-8").read()

def grab(rx, s, flags=0):
    m = re.search(rx, s, flags); return m.groups() if m else None

def parse_line(seg_id, dos1, dos2, body):
    body = " ".join(body.split())
    m = re.match(r"HC:([A-Z0-9]{5})\s*((?:[A-Z0-9]{2}\s+)*)(?:/\s*/\s*)?(\d+)?", body)
    cpt, mods, units = (m.group(1), m.group(2).split(), m.group(3)) if m else ("", [], "")
    monies = [money(x) for x in re.findall(MONEY, body)]
    allowed = None
    a = re.search(r"(" + MONEY + r")\s*\(B6\)|B6\s*(" + MONEY + ")", body)
    if a: allowed = money(a.group(1) or a.group(2))
    cas = CAS.findall(body)
    # payment = last money; charge = the money right after the allowed (check layout) or after "Charge" (claim layout)
    payment = monies[-1] if monies else 0.0
    charge = None
    c = re.search(r"\(B6\)\s*(" + MONEY + ")", body) or re.search(r"Charge\s+(?:[A-Z]{2}-\d+\s+)*\\?(" + MONEY + ")", body)
    if c: charge = money(c.group(1))
    # CAS amounts: the monies between the charge and the payment, in CAS order
    cas_amts = []
    if cas:
        after = body[c.end():] if c else body
        cas_amts = [money(x) for x in re.findall(MONEY, after)][:len(cas)]
    codes = [f"{g}-{r}" + (f":{cas_amts[i]:.2f}" if i < len(cas_amts) else "") for i, (g, r) in enumerate(cas)]
    rarc = sorted(set(RARC.findall(body)))
    pc = sorted(set(t for t in PAYERCODE.findall(body) if t not in ("HC",)))
    return {"line_ctrl": seg_id, "dos_from": dos1, "dos_to": dos2, "cpt": cpt, "modifiers": " ".join(mods),
            "units": units or "", "allowed": allowed, "charge": charge, "paid": payment, "cas": codes,
            "rarc": rarc, "payer_codes": pc}

def action(row):
    cas = " ".join(row["cas"]); st = row["status_code"]
    if "OA-18" in cas: return "DUPLICATE of an adjudicated claim - find the original remit, do not rebill"
    if st == "22" or (row["charge"] or 0) < 0: return "REVERSAL - post the takeback, then re-route/rebill per the reason"
    if "PR-22" in cas or "CO-22" in cas: return "COB - another payer is primary: fix insorder, bill the primary"
    if row["paid"]: return "post: pay %.2f%s" % (row["paid"], " + WOINS %.2f" % row["contractual"] if row["contractual"] else "")
    if any(c.startswith("PR-") for c in row["cas"]): return "patient/secondary responsibility"
    if row["cas"]: return "denial - work codes " + cas
    return "read codes"

def parse(text):
    hdr = {k: (grab(rx, text) or [""])[0] for k, rx in HDR.items()}
    hdr["check_amount"] = money(hdr["check_amount"]) if hdr["check_amount"] else None
    rows = []
    for blk in CLAIM_SPLIT.split(text):
        if not blk.startswith("Patient Name:"): continue
        f = {}
        for k, rx in CF.items():
            g = grab(rx, blk); f[k] = g
        visit, letter = (f["acct"] or ("", ""))[:2]
        claim = {"check": hdr["check"], "check_date": hdr["check_date"], "check_amount": hdr["check_amount"],
                 "payer": hdr["payer"], "icn": (f["icn"] or [""])[0], "status_code": (f["status_code"] or [""])[0],
                 "status": "", "visit": visit, "claim_letter": letter,
                 "claim_charge": money(f["charge"][0]) if f["charge"] else None,
                 "claim_paid": money(f["paid"][0]) if f["paid"] else None,
                 "patient_resp": money(f["patient_resp"][0]) if f["patient_resp"] else 0.0,
                 "orig_ref": (f["orig_ref"] or [""])[0], "received": (f["received"] or [""])[0],
                 "rendering_npi": (f["rendering_npi"] or [""])[0]}
        claim["status"] = STATUS.get(claim["status_code"], claim["status_code"])
        lines = [parse_line(*m) for m in LINE.findall(blk)]
        if not lines:
            lines = [{"line_ctrl": "", "dos_from": (f["dos"] or ["", ""])[0], "dos_to": (f["dos"] or ["", ""])[1], "cpt": "",
                      "modifiers": "", "units": "", "allowed": None, "charge": claim["claim_charge"],
                      "paid": claim["claim_paid"] or 0.0, "cas": [], "rarc": [], "payer_codes": []}]
        for ln in lines:
            r = dict(claim, **ln)
            r["contractual"] = sum(float(c.split(":")[1]) for c in r["cas"] if c.startswith("CO-") and ":" in c)
            r["action"] = action(r); rows.append(r)
    return rows

def main(argv):
    jout = argv[argv.index("--json")+1] if "--json" in argv else None
    cout = argv[argv.index("--csv")+1] if "--csv" in argv else None
    paths = [a for a in argv if not a.startswith("--") and a not in (jout, cout)]
    rows = []
    for p in paths:
        for r in parse(text_of(p)): r["source"] = p.split("/")[-1]; rows.append(r)
    keys = ["source", "payer", "check", "check_date", "check_amount", "icn", "orig_ref", "status_code", "status", "received",
            "visit", "claim_letter", "rendering_npi", "line_ctrl", "dos_from", "dos_to", "cpt", "modifiers", "units",
            "charge", "allowed", "paid", "patient_resp", "contractual", "cas", "rarc", "payer_codes", "action"]
    if jout: json.dump(rows, open(jout, "w"), indent=1)
    if cout:
        with open(cout, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader()
            for r in rows: w.writerow({k: (" ".join(v) if isinstance(v, list) else v) for k, v in r.items()})
    for r in rows:
        print(f'{r["check"]} {r["check_date"]} | {r["icn"]} st{r["status_code"]} | visit {r["visit"]}{r["claim_letter"]} '
              f'{r["dos_from"]} {r["cpt"]} {r["modifiers"]} | chg {r["charge"]} allowed {r["allowed"]} paid {r["paid"]:.2f} '
              f'| {" ".join(r["cas"])} {" ".join(r["rarc"])} {" ".join(r["payer_codes"])} -> {r["action"]}')
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
