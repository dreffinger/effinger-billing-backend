# PLAIN ENGLISH (Availity Remittance Viewer PDF -> check register)
# Decides: Nothing. Reads every CheckDetails / CheckMultipleDetails / ClaimDetails PDF William exported from Availity
#   (Drive "bht Optum era downloads") and writes one register: per check (trace number, payer, amount, date) the claims
#   (patient control number = AMD visit id + claim letter, claim number, charge/paid/patient-responsibility, claim status)
#   and lines (line control number = AMD charge id, DOS, CPT, charge, adjustments with group-CARC, paid, remark codes).
# Rules it uses: dedupe by trace number (the same check was exported more than once); ClaimDetails files are single-claim
#   views and are folded into the same check by trace number.
# Never touches: AMD. Output: registers/availity_checks_<stamp>.json  (PHI - stays in the workspace).
"""Usage: python3 avail_checks_parse.py [stamp]"""
import glob, json, re, sys, os
from pypdf import PdfReader
STAMP = sys.argv[1] if len(sys.argv) > 1 else "2026-09-15T0310Z"
MONEY = r"-?\$[\d,]+\.\d\d"
def money(s): return float(s.replace("$", "").replace(",", ""))

def text_of(pdf):
    try:
        r = PdfReader(pdf); return "\n".join((p.extract_text() or "") for p in r.pages), len(r.pages)
    except Exception as e:
        return "", 0

def parse_lines(block):
    """block = text between 'Charge' header line and 'Code Descriptions'. Returns list of line dicts."""
    out = []
    # split at each line control number that starts a line (7-9 digits followed by a date)
    parts = re.split(r"(?m)^(?=\d{7,9} \d\d/\d\d/\d{4}-)", block)
    for p in parts:
        m = re.match(r"(\d{7,9}) (\d\d/\d\d/\d{4})-\s*(\d\d/\d\d/\d{4})", p)
        if not m: continue
        cpt = re.search(r"HC:(\d{5}|[A-Z]\d{4})", p)
        amts = re.findall(MONEY, p)
        adjs = [(g, c, money(a)) for g, c, a in re.findall(r"\b(CO|PR|OA|PI|CR)-(\d{1,3})\s*\n?\s*(" + MONEY + ")", p)]
        # charge = first money with (B6)?? not always; take the first amount that is not preceded by CARC as charge
        charge = None
        mc = re.search(r"(" + MONEY + r")\s*(?:\(B6\)|Charge)", p)
        if mc: charge = money(mc.group(1))
        elif amts: charge = money(amts[0])
        paid = money(amts[-1]) if amts else None
        remarks = re.findall(r"\b(N\d{3}|M\d{2,3}|MA\d{2,3})\b", p)
        out.append({"chargeid": m.group(1), "dos": m.group(2), "cpt": cpt.group(1) if cpt else None, "charge": charge,
                    "adj": adjs, "paid": paid, "remarks": sorted(set(remarks))})
    return out

def parse_claims(text):
    claims = []
    for seg in re.split(r"(?=Claim Summary)", text)[1:]:
        g = lambda k: (re.search(k + r":\s*([^\n]*?)(?=\s{1,}[A-Z][A-Za-z/ ]+:|\n|$)", seg) or [None, None])[1]
        pcn = re.search(r"Patient Control Number:\s*(\d+)([A-Z]?)", seg)
        trace = re.search(r"Check/EFT Trace Number:\s*(\S+)", seg)
        cdate = re.search(r"Check/EFT Date:\s*(\d\d/\d\d/\d{4})", seg)
        c = {"payer": (re.search(r"Payer Name:\s*(.*?)\s+Patient Name:", seg) or [None, None])[1],
             "patient": (re.search(r"Patient Name:\s*(.*?)\s+Claim Charge Amount:", seg) or [None, None])[1],
             "claim_charge": money((re.search(r"Claim Charge Amount:\s*(" + MONEY + ")", seg) or [None, "$0.00"])[1]),
             "claim_paid": money((re.search(r"Claim Payment Amount:\s*(" + MONEY + ")", seg) or [None, "$0.00"])[1]),
             "pat_resp": money((re.search(r"Patient Responsibility:\s*(" + MONEY + ")", seg) or [None, "$0.00"])[1]),
             "claim_number": (re.search(r"Claim Number:\s*(\S+)", seg) or [None, None])[1],
             "member_id": (re.search(r"Patient ID:\s*(\S+)", seg) or [None, None])[1],
             "claim_dates": (re.search(r"Claim Date:\s*(\S+)", seg) or [None, None])[1],
             "visit": pcn.group(1) if pcn else None, "claim_letter": pcn.group(2) if pcn else None,
             "received": (re.search(r"Claim Received Date:\s*(\S+)", seg) or [None, None])[1],
             "status_code": (re.search(r"Claim Status Code:\s*(\d+)", seg) or [None, None])[1],
             "trace": trace.group(1) if trace else None, "check_date": cdate.group(1) if cdate else None,
             "lines": []}
        lb = re.search(r"Adjustments? Payment\n(.*?)(?:Code Descriptions|$)", seg, re.S) or re.search(r"Adj Amount Payment\n(.*?)(?:Code Descriptions|$)", seg, re.S)
        if lb: c["lines"] = parse_lines(lb.group(1))
        claims.append(c)
    return claims

def parse_check_header(text):
    h = {}
    m = re.search(r"Check Summary Transaction Date:(\S+)\n(.*?) Payee Tax ID", text, re.S)
    if m: h["payer"] = m.group(2).strip().split("\n")[-1]
    for k, rx in (("trace", r"Check/EFT Trace Number:\s*(\S+)"), ("amount", r"Payment Amount:\s*(" + MONEY + ")"),
                  ("check_date", r"Check/EFT Date:\s*(\d\d/\d\d/\d{4})"), ("payee_npi", r"Payee ID:\s*(\d{10})")):
        mm = re.search(rx, text); h[k] = mm.group(1) if mm else None
    if h.get("amount"): h["amount"] = money(h["amount"])
    return h

checks = {}; files = 0; claimfiles = 0
for pdf in sorted(glob.glob("era_pdfs/*.pdf")):
    t, n = text_of(pdf)
    if not t: print("unreadable", pdf); continue
    files += 1
    name = os.path.basename(pdf)
    if name.startswith("ClaimDetails"):
        claimfiles += 1
        for c in parse_claims(t):
            k = c["trace"] or "?"
            ck = checks.setdefault(k, {"trace": k, "payer": c["payer"], "amount": None, "check_date": c["check_date"], "files": [], "claims": {}, "claim_only": True})
            ck["files"].append(name)
            ck["claims"].setdefault((c["claim_number"] or "") + "|" + (c["visit"] or ""), c)
        continue
    # CheckDetails may hold several checks (CheckMultipleDetails): split on "Check Summary"
    for seg in re.split(r"(?=Check Summary Transaction Date)", t):
        if "Check Summary" not in seg: continue
        h = parse_check_header(seg)
        if not h.get("trace"): continue
        ck = checks.setdefault(h["trace"], {"trace": h["trace"], "payer": h.get("payer"), "amount": h.get("amount"), "check_date": h.get("check_date"), "files": [], "claims": {}, "claim_only": False})
        ck["claim_only"] = False; ck["amount"] = ck["amount"] or h.get("amount"); ck["payer"] = ck["payer"] or h.get("payer")
        ck["files"].append(name)
        for c in parse_claims(seg):
            ck["claims"].setdefault((c["claim_number"] or "") + "|" + (c["visit"] or ""), c)
for ck in checks.values():
    ck["claims"] = list(ck["claims"].values())
    ck["n_claims"] = len(ck["claims"]); ck["sum_claim_paid"] = round(sum(c["claim_paid"] for c in ck["claims"]), 2)
os.makedirs("registers", exist_ok=True)
out = "registers/availity_checks_%s.json" % STAMP
json.dump(sorted(checks.values(), key=lambda c: (c["check_date"] or "", c["trace"])), open(out, "w"), indent=1)
tot = sum((c["amount"] or 0) for c in checks.values() if not c["claim_only"])
print("files %d (claim-only %d) checks %d  total check $ %.2f  claims %d" % (files, claimfiles, len(checks), tot, sum(c["n_claims"] for c in checks.values())))
bad = [c["trace"] for c in checks.values() if not c["claim_only"] and abs((c["amount"] or 0) - c["sum_claim_paid"]) > 0.01]
print("checks whose claim payments do not sum to the check amount:", len(bad), bad[:15])
print("wrote", out)
