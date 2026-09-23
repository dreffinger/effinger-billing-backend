#!/usr/bin/env python3
import os
"""Classify every OCR'd page of the 9/22/2026 ScanSnap batches by document type.
Writes pages.json: [{batch, page, file, type, payer, hints...}]"""
import re, os, glob, json, sys
ROOT = os.environ.get("SCANS_DIR", "/home/claude/scans") + "/ocr"
def norm(t): return re.sub(r"[ \t]+", " ", t)
def classify(t):
    u = t.upper(); n = len(t.strip())
    hints = {}
    if n < 40: return "blank_or_noise", hints
    if "INTENTIONALLY LEFT BLAN" in u: return "blank", hints
    if re.search(r"ENDORSE (CHECK )?HERE", u) and "PAY" not in u[:400]: return "check_back", hints
    if "DEPOSITORY BANK ENDORSEMENT" in u or "RESERVED FOR FINANCIAL INSTITUTION" in u: return "check_back", hints
    if ("PAYMENT ENCLOSED" in u and "CARD" in u) or re.search(r"5551-50\d\d-\d{4}-\d{4}", t):
        m = re.search(r"(5551-50\d\d-\d{4}-\d{4})", t); hints["card"] = m.group(1) if m else None
        m = re.search(r"PAYMENT ID:?\s*(\d{6,})", u); hints["payment_id"] = m.group(1) if m else None
        m = re.search(r"\$\s?([\d,]+\.\d\d)", t); hints["amount"] = m.group(1) if m else None
        m = re.search(r"Valid Thru\.?\s*(\d\d/\d\d)", t); hints["exp"] = m.group(1) if m else None
        return "zelis_vcard", hints
    if "CHAMPVA" in u and "EXPLANATION OF BENEFITS" in u: return "champva_eob", hints
    if "FLORIDA COMMUNITY CARE" in u or "FCCHEALTHPLAN" in u or "FLORIDA\nCOMMUNITY CARE" in u:
        if "CHECK NUMBER" in u and "BANKUNITED" in u: return "check_front", {"payer": "FCC"}
        if "ZERO PAYMENT" in u: return "fcc_zero_payment", hints
        return "fcc_remit", hints
    if re.search(r"CHECK[ _]*NUMBER", u) and ("UMB BANK" in u or "JPMORGAN" in u or "BANKUNITED" in u or "USAA" in u or "VOID AFTER" in u or "PAY TO THE" in u):
        p = "UNITED AMERICAN" if "MCKINNEY" in u or "UNITED AMERICAN" in u else ("MUTUAL OF OMAHA" if "OMAHA" in u else ("USAA" if "USAA" in u else ("FCC" if "BANKUNITED" in u else "?")))
        m = re.search(r"\$\$*\s?([\d,]+\.\d\d)", t); hints["amount"] = m.group(1) if m else None
        m = re.search(r"Claim#?:?\s*_?\s*(\d{10,})", t); hints["claim"] = m.group(1) if m else None
        m = re.search(r"(\d\d/\d\d/20\d\d)", t); hints["date"] = m.group(1) if m else None
        return "check_front", {"payer": p, **hints}
    if "UNITED AMERICAN INSURANCE CO" in u and "EXPLANATION OF PAYMENT" in u: return "ua_eop_cover", hints
    if "PATIENT ACCT #" in u and "MEDICARE CONTROL #" in u: return "ua_eob_detail", hints
    if "WASHINGTON NATIONAL" in u or "BANKERSLIFE" in u or "BANKERS LIFE" in u: return "wn_remit", hints
    if "SENIOR SUPPLEMENTAL" in u or "AETNASENIORPRODUCTS" in u or "AMERICAN CONTINENTAL" in u or "CONTINENTAL LIFE" in u: return "aetna_ssi_remit", hints
    if "UNITED OF OMAHA" in u or "MUTUAL OF OMAHA" in u: return "moo_remit", hints
    if "GLOBE LIFE" in u and "EPROVIDER" in u: return "globe_notice", hints
    if "SIMPLY HEALTHCARE" in u or "SIMPLY" in u and "MEDICAID" in u: return "simply_remit", hints
    if "FLORIDA BLUE" in u or "BLUE CROSS" in u or "BCBS" in u: return "bcbs_remit", hints
    if "HUMANA" in u: return "humana_remit", hints
    if "TRIWEST" in u or "VA CCN" in u or "OPTUM" in u and "VETERAN" in u or "COMMUNITY CARE NETWORK" in u: return "va_remit", hints
    if "MEDICARE" in u and ("REMITTANCE" in u or "REMIT" in u): return "medicare_remit", hints
    if "PATIENT ACCT" in u and re.search(r"\b99\d\d\d\b", u): return "eob_generic", hints
    if "PAYMENT SUMMARY" in u: return "payment_summary", hints
    if "EXPLANATION OF" in u or "REMITTANCE" in u: return "eob_other", hints
    return "other", hints
out = []
for d in sorted(glob.glob(ROOT + "/*/")):
    b = os.path.basename(d.rstrip("/"))
    for f in sorted(glob.glob(d + "p-*.txt")):
        t = norm(open(f, errors="ignore").read())
        ty, h = classify(t)
        pg = int(re.search(r"p-(\d+)", f).group(1))
        out.append({"batch": b, "page": pg, "file": f, "type": ty, **h, "head": t.strip()[:120].replace("\n", " | ")})
json.dump(out, open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/pages.json", "w"), indent=1)
from collections import Counter
print(Counter(p["type"] for p in out))
if "--list" in sys.argv:
    for p in out: print(p["batch"][-14:], "p%02d" % p["page"], p["type"].ljust(18), p.get("payer", ""), p.get("amount", ""), "|", p["head"][:90])
