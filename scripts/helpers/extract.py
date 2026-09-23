#!/usr/bin/env python3
import os
"""Extract payments / claims / service lines from the OCR'd 9/22/2026 scan pile.
Input: pages.json (from classify.py) + ocr/<batch>/p-NN.txt.  Output: extracted.json
Every record keeps its (batch, page) so a human can open the scan page."""
import re, json, os, sys
from collections import defaultdict
PAGES = json.load(open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/pages.json"))
def txt(p): return open(p["file"], errors="ignore").read()
def money(s):
    s = s.replace(",", "").replace("$", "").replace("§", "").replace("O", "0").replace("o", "0").strip()
    s = re.sub(r"[^\d.\-()]", "", s)
    neg = s.startswith("(") or s.startswith("-")
    s = s.strip("()-")
    try: v = float(s)
    except ValueError: return None
    return -v if neg else v
MONEY = r"\(?\$?\s?-?[\d,]*\d[.,]\d\d\)?"
def fixacct(a):
    """AMD claim number: 8 digits + sequence letter.  Repairs common OCR slips (S->5, O->0, l/I->1, trailing letter)."""
    if not a: return None
    a = a.strip().replace(" ", "")
    m = re.match(r"^(\d{8})([A-Z])?", a)
    if m: return m.group(1) + (m.group(2) or "?")
    b = re.sub(r"[SsZ]", lambda x: {"S": "5", "s": "5", "Z": "2"}[x.group(0)], a[:8])
    b = b.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
    m = re.match(r"^(\d{8})", b)
    if m:
        tail = a[8:9]
        return m.group(1) + (tail if re.match(r"[A-Z]", tail or "") else "?")
    return None
DATE = r"(\d{1,2}/\d{1,2}/(?:20)?\d\d)"
def norm_date(d):
    if not d: return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", d)
    if not m: return None
    mm, dd, yy = m.groups(); yy = ("20" + yy) if len(yy) == 2 else yy
    return "%s-%02d-%02d" % (yy, int(mm), int(dd))
DOCCODE = re.compile(r"(20\d{6})\s?B0[A-Z0-9]\s+(J[0-9A-Z]{3})\s*\[\s*([\d,\.]+)\s*\]\s*(\d+)\s*of\s*(\d+)", re.I)
def doccode(t):
    m = DOCCODE.search(t)
    if m: return {"print": m.group(1), "jcode": m.group(2).upper(), "seq": m.group(3).replace(".", ","), "pg": int(m.group(4)), "of": int(m.group(5))}
    m = re.search(r"(J[0-9A-Z]{3})\s*\[\s*([\d,\.]+)\s*\]\s*(\d+)\s*of\s*(\d+)", t)
    if m: return {"print": None, "jcode": m.group(1).upper(), "seq": m.group(2).replace(".", ","), "pg": int(m.group(3)), "of": int(m.group(4))}
    m = re.search(r"\[\s*([\d,\.]+)\s*\]\s*(\d+)\s*of\s*(\d+)", t)
    if m: return {"print": None, "jcode": None, "seq": m.group(1).replace(".", ","), "pg": int(m.group(2)), "of": int(m.group(3))}
    return None

# ------------------------------------------------------------------ United American / Globe Life family (Medigap crossover)
def parse_ua_detail(t):
    claims = []
    blocks = re.split(r"\n(?=Patient:\s)", "\n" + t)
    for b in blocks:
        m = re.search(r"Patient:\s*([A-Z][A-Z .'\-|\[\]]+?)\s*\n", b)
        if not m: continue
        c = {"patient": re.sub(r"[|\[\]]", "I", m.group(1)).strip()}
        m = re.search(r"Patient Acct\s*#?:?\s*([0-9A-Z]{8,10})", b); c["acct"] = fixacct(m.group(1)) if m else None
        m = re.search(r"Medicare Control\s*#?:?\s*(\d{12,14})", b); c["icn"] = m.group(1) if m else None
        m = re.search(r"Medicare ID:?\s*([0-9A-Z]{11})", b); c["mbi"] = m.group(1) if m else None
        m = re.search(r"Policy\s*#?:?\s*(\d{6,10})", b); c["policy"] = m.group(1) if m else None
        lines = []
        for lm in re.finditer(r"(\d\d/\d\d/\d\d)-(\d\d/\d\d/\d\d)\s+(99\d{3}|G\d{4})\s*(?:\(([^)]*)\))?\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+([A-Z]{2}-?\d+)", b):
            lines.append({"dos": norm_date(lm.group(1)), "cpt": lm.group(3), "mod": (lm.group(4) or "").strip(), "billed": money(lm.group(5)),
                          "allowed": money(lm.group(6)), "adj": money(lm.group(7)), "adj_code": lm.group(8).replace("-", "")})
        c["lines"] = lines
        c["claim_adj"] = [{"code": am.group(2).replace("-", ""), "amount": money(am.group(1))} for am in re.finditer(r"Claims? Adjustment\s+(" + MONEY + r")\s+([A-Z]{2}-?\d+)", b)]
        m = re.search(r"Totals?\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")", b)
        if m: c["totals"] = {"billed": money(m.group(1)), "allowed": money(m.group(2)), "adjustments": money(m.group(3)), "paid": money(m.group(4)), "ptresp": money(m.group(5))}
        claims.append(c)
    return claims
def parse_ua_cover(t):
    p = {"payer": "UNITED AMERICAN INSURANCE CO", "family": "UA"}
    m = re.search(r"Payment Date:\s*([A-Za-z]+ \d{1,2}, 20\d\d|\d\d/\d\d/20\d\d)", t); p["date_text"] = m.group(1) if m else None
    p["date"] = None
    if m:
        import datetime
        for fmt in ("%B %d, %Y", "%m/%d/%Y"):
            try: p["date"] = datetime.datetime.strptime(m.group(1), fmt).strftime("%Y-%m-%d"); break
            except ValueError: pass
    m = re.search(r"Ch[ae]ck Number:\s*(\d{8,12})", t); p["check_number"] = m.group(1) if m else None
    for k, rx in [("total_charges", r"Total Charges:\s*(" + MONEY + ")"), ("ptresp", r"Total Patient Responsibility:\s*(" + MONEY + ")"), ("contractual", r"Total Contractual Adjustments:\s*(" + MONEY + ")"),
                  ("other_adj", r"Total Other Adjustments:\s*(" + MONEY + ")"), ("claim_payment", r"Total Claim Payment:\s*(" + MONEY + ")"), ("amount", r"Total Payment:\s*(" + MONEY + ")")]:
        m = re.search(rx, t); p[k] = money(m.group(1)) if m else None
    return p

# ------------------------------------------------------------------ Zelis virtual card stub
def parse_zelis_vcard(t):
    p = {"method": "vcard", "family": "ZELIS"}
    m = re.search(r"(5551-50\d\d-\d{4}-\d{4})", t); p["card"] = m.group(1) if m else None
    m = re.search(r"PAYMENT ID:?\s*(\d{6,})", t, re.I); p["payment_id"] = m.group(1) if m else None
    m = re.search(r"Valid Thru\.?\s*(\d\d/\d\d)", t); p["exp"] = m.group(1) if m else None
    m = re.search(r"\(?C?V[CV]2?\)?:?\s*(\d{3})\b", t); p["cvc"] = m.group(1) if m else None
    amts = [money(x) for x in re.findall(r"\$\s?([\d,]+\.\d\d)", t)]
    p["amount"] = amts[0] if amts else None
    m = re.search(r"Amount:?\s*\$?\s*([\d,]+\.\d\d)", t);
    if m: p["amount"] = money(m.group(1))
    return p

# ------------------------------------------------------------------ Washington National / Bankers Life (Zelis remit)
def parse_wn(t):
    p = {"payer": "WASHINGTON NATIONAL / BANKERS LIFE", "family": "WN"}
    m = re.search(r"Payment Date:\s*(\d\d/\d\d/20\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"Payment Amount:\s*(" + MONEY + ")", t); p["amount"] = money(m.group(1)) if m else None
    m = re.search(r"Document Trace Number:\s*(\d{6,})", t); p["trace"] = m.group(1) if m else None
    m = re.search(r"Payment Type:\s*([A-Za-z \-]+)", t); p["type"] = m.group(1).strip() if m else None
    rows = []
    for rm in re.finditer(r"(\d{8}[A-Z]?)\s+([A-Z][A-Z .'\-]+?)\s+(\d\d/\d\d/20\d\d)\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + ")", t):
        rows.append({"acct": fixacct(rm.group(1)), "patient": rm.group(2).strip(), "dos": norm_date(rm.group(3)), "billed": money(rm.group(4)), "reduction": money(rm.group(5)), "paid": money(rm.group(6))})
    p["summary"] = rows
    return p
def parse_generic_claim_detail(t):
    """'Claim #: 278923 Patient Acct #: 19444454A ... 06/08/2026 99223 1.00 $310.00 $31.94 $31.94 ...' (Washington National detail)"""
    claims = []
    for b in re.split(r"\n(?=Claim #:)", "\n" + t):
        m = re.search(r"Claim #:\s*(\d+)\s+Patient Acct #:\s*([0-9A-Z]{8,10})", b)
        if not m: continue
        c = {"payer_claim": m.group(1), "acct": fixacct(m.group(2))}
        m = re.search(r"Patient:\s*([A-Z][A-Z .'\-]+?)\s+Provider", b); c["patient"] = m.group(1).strip() if m else None
        m = re.search(r"Member:\s*(\d+)", b); c["member"] = m.group(1) if m else None
        lines = []
        for lm in re.finditer(r"(\d\d/\d\d/20\d\d)\s+(99\d{3}|G\d{4})(?:/(\d\d))?\s+([\d.]+)\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+([A-Z]{2}\d+)", b):
            lines.append({"dos": norm_date(lm.group(1)), "cpt": lm.group(2), "mod": lm.group(3) or "", "billed": money(lm.group(5)), "allowed": money(lm.group(6)), "paid": money(lm.group(7)),
                          "ptresp": money(lm.group(8)), "other_ins": money(lm.group(9)), "not_covered": money(lm.group(10)), "adj_code": lm.group(12)})
        c["lines"] = lines
        m = re.search(r"Total for Claim\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + ")", b)
        if m: c["totals"] = {"billed": money(m.group(1)), "allowed": money(m.group(2)), "paid": money(m.group(3))}
        claims.append(c)
    return claims

# ------------------------------------------------------------------ Aetna Senior Supplemental (American Continental / Continental Life)
def parse_aetna_ssi(t):
    p = {"payer": "AETNA SENIOR SUPPLEMENTAL (AMERICAN CONTINENTAL)", "family": "AET12"}
    m = re.search(r"Payment Date\s*(\d\d/\d\d/20\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"Total Claim Payment\s*(" + MONEY + ")", t); p["amount"] = money(m.group(1)) if m else None
    m = re.search(r"Payment Modality\s*([A-Za-z ]+)", t); p["modality"] = m.group(1).strip() if m else None
    m = re.search(r"Payment ID\s*(\d{6,})", t); p["payment_id"] = m.group(1) if m else None
    claims = []
    for b in re.split(r"\n(?=Tax ID:\s*814723941\s+Patient Acct)", "\n" + t):
        m = re.search(r"Patient Acct #:\s*([0-9A-Z]{8,10})\s+Claim Number:\s*(\d+)", b)
        if not m: continue
        c = {"acct": fixacct(m.group(1)), "payer_claim": m.group(2)}
        m = re.search(r"Patient Name:\s*([A-Z][A-Z .'\-|\[\]]+?)\s+Member Number:\s*([A-Z0-9]+)\s+Check Number:\s*(\d+)\s+Check Date:\s*(\d\d/\d\d/\d\d)", b)
        if m: c.update({"patient": re.sub(r"[|\[\]]", "I", m.group(1)).strip(), "member": m.group(2), "check_number": m.group(3), "check_date": norm_date(m.group(4))})
        lines = []
        for line in b.splitlines():
            lm = re.match(r"\s*(\d\d/\d\d/\d\d)-(\d\d/\d\d/\d\d)\s+(99\d{3}|G\d{4})(.*)$", line)
            if not lm: continue
            vals = [money(x) for x in re.findall(r"\$\s?[\d,]+\.\d\d", lm.group(4))]
            if len(vals) < 3: continue
            d = {"dos": norm_date(lm.group(1)), "cpt": lm.group(3), "billed": vals[0], "paid": vals[-1], "contractual": None, "other_payer": None, "coins": None, "copay": None, "deductible": None, "not_covered": None, "pt_bill": None}
            if len(vals) >= 9: d.update({"contractual": vals[1], "other_payer": vals[2], "coins": vals[3], "copay": vals[4], "deductible": vals[5], "not_covered": vals[6], "pt_bill": vals[7]})
            elif len(vals) >= 4: d.update({"contractual": vals[1], "other_payer": vals[2]})
            lines.append(d)
        c["lines"] = lines
        m = re.search(r"Total Claim Payment:\s*(" + MONEY + ")", b); c["claim_paid"] = money(m.group(1)) if m else None
        claims.append(c)
    p["claims"] = claims
    return p

# ------------------------------------------------------------------ CHAMPVA
def parse_champva(t):
    p = {"payer": "CHAMPVA", "family": "CHAMPVA"}
    m = re.search(r"Patient:?\s*\|?\s*([A-Z][A-Z ,.'\-]+?)\s+Date:\s*(\d{1,2}/\d{1,2}/\d\d)", t)
    p["patient"] = m.group(1).strip() if m else None; p["date"] = norm_date(m.group(2)) if m else None
    p["info_only"] = bool(re.search(r"Information only, no check enclosed", t)); p["by_eft"] = "payment by EFT" in t
    m = re.search(r"TOTAL PAYMENTS:\s*TO PROVIDER\s*(" + MONEY + ")", t); p["amount"] = money(m.group(1)) if m else None
    m = re.search(r"([A-Z0-9]{6})\s+(\d{11})\s*[-=]?\s*$", "\n".join(l for l in t.splitlines() if "no check enclosed" in l or "payment by EFT" in l)); p["ref"] = m.group(2) if m else None
    claims = []
    for lm in re.finditer(r"(\d{12})\s+(\d\d/\d\d/\d\d)\s+(\d\d/\d\d/\d\d)\s+(99\d{3}|G\d{4})\s+[A-Z /]+?\s+\$\s?([\d,]+\.\d\d)\s+\$\s?([\d,]+\.\d\d)\s+\$?\s?([\d,]+\.\d\d)\s+(\d+)?\s*\n\s*([0-9A-Z]{8,10})\s+OHI PAID:\s*\$?([\d,]+\.\d\d)\s+PATIENT PAID:\s*\$?([\d,]+\.\d\d)\s+CLAIM TOTAL:\s*\$\s?([\d,]+\.\d\d)\s+\$\s?([\d,]+\.\d\d)\s+\$\s?([\d,]+\.\d\d)", t):
        claims.append({"control": lm.group(1), "dos": norm_date(lm.group(2)), "cpt": lm.group(4), "billed": money(lm.group(5)), "allowed": money(lm.group(6)), "not_covered": money(lm.group(7)),
                       "remark": lm.group(8), "acct": fixacct(lm.group(9)), "ohi_paid": money(lm.group(10)), "patient": p["patient"]})
    m = re.search(r"PAYMENTS:\s*TO PROVIDER\s*\$?([\d,]+\.\d\d)\s+COST SHARE", t)
    if m and claims: claims[-1]["paid"] = money(m.group(1))
    p["claims"] = claims
    return p

# ------------------------------------------------------------------ Florida Community Care (FLO99)
def parse_fcc(t):
    p = {"payer": "FLORIDA COMMUNITY CARE", "family": "FLO99"}
    m = re.search(r"\b(019\d{5})\b", t); p["check_number"] = m.group(1) if m else None
    m = re.search(r"(\d\d/\d\d/\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"\$\s?([\d,]+\s?\.\s?\d\d)", t); p["amount"] = money(m.group(1).replace(" ", "")) if m else None
    p["zero_payment"] = "ZERO PAYMENT" in t.upper()
    claims = []
    for b in re.split(r"\n(?=PATIENT:\s)", "\n" + t):
        m = re.search(r"PATIENT:\s*([A-Z][A-Z .'\-]+?)\s+ID:\s*([\d\-]+)\s+CIN#?:?\s*(\d+)\s+CLAIM:\s*(\d{12,16})", b)
        if not m: continue
        c = {"patient": m.group(1).strip(), "member": m.group(2), "cin": m.group(3), "payer_claim": m.group(4)}
        m = re.search(r"PATIENT ACCT:\s*([0-9A-Z]{8,10})", b); c["acct"] = fixacct(m.group(1)) if m else None
        m = re.search(r"PROVIDER\s*:\s*([A-Z .]+?)\s+[TI]D", b); c["provider"] = m.group(1).strip() if m else None
        lines = []
        for lm in re.finditer(r"(\d{6})\s+(?:([A-Z0-9]{2})\s+)?(99\d{3}|G\d{4})\s+.*?\s(\d+\.\d\d)\s+(\d+\.\d\d)\s+(\d+\.\d\d)\s+(\d+\.\d\d)\s+(\d)\b\s*(\d{3})?", b):
            d = lm.group(1); lines.append({"dos": "20%s-%s-%s" % (d[4:6], d[0:2], d[2:4]), "mod": lm.group(2), "cpt": lm.group(3), "billed": money(lm.group(4)), "allowed": money(lm.group(5)),
                                           "copay_ded": money(lm.group(6)), "paid": money(lm.group(7)), "pc": lm.group(8), "msg": lm.group(9)})
        c["lines"] = lines
        m = re.search(r"ADJUSTMENTS DUE TO COB\s*:?\s*\*?\s*(-?[\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)", b)
        if m: c["cob_adj"] = {"billed": money(m.group(1)), "allowed": money(m.group(2)), "copay": money(m.group(3)), "paid": money(m.group(4))}
        m = re.search(r"TOTAL PAID THIS CLAIM\s*:?\s*\*?\s*(-?[\d,]+\.\d\d)", b); c["claim_paid"] = money(m.group(1)) if m else None
        m = re.search(r"TOTALS THIS CLAIM\s*[:;7]?\s*\*?\s*(-?[\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)", b)
        if m: c["totals"] = {"billed": money(m.group(1)), "allowed": money(m.group(2)), "copay": money(m.group(3)), "paid": money(m.group(4))}
        claims.append(c)
    p["claims"] = claims
    return p

# ------------------------------------------------------------------ Simply Healthcare (Zelis remit)
def parse_simply(t):
    p = {"payer": "SIMPLY HEALTHCARE PLANS", "family": "SIM01"}
    m = re.search(r"Payer:\s*([A-Za-z ]+)", t); p["payer"] = m.group(1).strip() if m else p["payer"]
    m = re.search(r"Payer Ck #:\s*(\d+)", t); p["check_number"] = m.group(1) if m else None
    m = re.search(r"Payment ID:\s*(\d+)", t); p["payment_id"] = m.group(1) if m else None
    m = re.search(r"Date:\s*(\d\d/\d\d/20\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"Total Payment:\s*(" + MONEY + ")", t); p["amount"] = money(m.group(1)) if m else None
    claims = []
    for b in re.split(r"\n(?=\[?Patient:)", "\n" + t):
        m = re.search(r"Patient\s?Acct\s?#?:?\s*\|?\s*([0-9A-Z]{8,10})\s+Claim #:\s*(\d+)", b)
        if not m: continue
        c = {"acct": fixacct(m.group(1)), "payer_claim": m.group(2)}
        m = re.search(r"\|\s*([A-Z][A-Z .'\-]+?)\s*\n", b); c["patient"] = m.group(1).strip() if m else None
        m = re.search(r"Insured ID:\s*(\d+)", b); c["member"] = m.group(1) if m else None
        m = re.search(r"\n\s*([A-Z][A-Za-z ]+?(?:LTSS|MMA|Medicaid|Medicare)[A-Za-z ]*)\s*;?\s*\n", "\n" + b); c["plan"] = m.group(1).strip() if m else None
        lines = []
        for lm in re.finditer(r"(\d\d/\d\d/\d\d)-(\d\d/\d\d/\d\d)\s+(99\d{3}|G\d{4})\s*(?:\(([^)]*)\))?\s+(\d+)\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+([A-Z0-9,]+)", b):
            lines.append({"dos": norm_date(lm.group(1)), "cpt": lm.group(3), "mod": lm.group(4), "billed": money(lm.group(6)), "contractual": money(lm.group(7)), "other_adj": money(lm.group(8)),
                          "allowed": money(lm.group(9)), "ptresp": money(lm.group(10)), "paid": money(lm.group(11)), "adj_code": lm.group(12)})
        c["lines"] = lines
        m = re.search(r"Totals\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + r")\s+(" + MONEY + ")", b)
        if m: c["totals"] = {"billed": money(m.group(1)), "contractual": money(m.group(2)), "other_adj": money(m.group(3)), "allowed": money(m.group(4)), "ptresp": money(m.group(5)), "paid": money(m.group(6))}
        claims.append(c)
    p["claims"] = claims
    return p

# ------------------------------------------------------------------ Florida Blue remittance advice
def parse_bcbs(t):
    p = {"payer": "FLORIDA BLUE", "family": "BCBS"}
    m = re.search(r"Check/EFT Date:\s*(\d\d/\d\d/20\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"Check/EFT Number:\s*(\d+)", t); p["check_number"] = m.group(1) if m else None
    m = re.search(r"Non-Payment Reference:\s*(\d+)", t); p["nonpay_ref"] = m.group(1) if m else None
    m = re.search(r"Total Amount Disbursed:\s*(" + MONEY + ")", t); p["amount"] = money(m.group(1)) if m else None
    m = re.search(r"Total Paid:\s*(" + MONEY + ")", t); p["total_paid"] = money(m.group(1)) if m else None
    claims = []
    cur = None
    for line in t.splitlines():
        m = re.match(r"^\s*(\w{5})\s+(.+?)\s+([A-Z]{1,4}\d{6,12}|\d{9,12})(?:\s+\S+)*\s+\$?(-?[\d,]+\.\d\d)\s*$", line)
        if m:
            names = m.group(2).strip(); prov = ""
            pm = re.match(r"(WILLIAM L EFFINGER|PAMELA P GARCIA|PAMELA GARCIA|WILLIAM EFFINGER)\s+(.*)$", names)
            if pm: prov, names = pm.group(1), pm.group(2)
            cur = {"provider": prov, "patient": names.strip(), "member": m.group(3), "claim_paid": money(m.group(4)), "lines": []}; claims.append(cur); continue
        m = re.match(r"\s*([A-Z]\d{12,16})\s+([0-9A-Z]{8,10})\s+(\d\d/\d\d/20\d\d)\s+(\d\d/\d\d/20\d\d)\s+(99\d{3}|G\d{4})\s+(?:(\d\d)\s+)?(\d{4})\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s*([\d,]*)", line)
        if m and cur is not None:
            cur["payer_claim"] = m.group(1); cur["acct"] = fixacct(m.group(2))
            cur["lines"].append({"dos": norm_date(m.group(3)), "cpt": m.group(5), "mod": m.group(6), "billed": money(m.group(8)), "allowed": money(m.group(9)), "diff": money(m.group(10)),
                                 "other_carrier": money(m.group(11)), "copay": money(m.group(12)), "coins": money(m.group(13)), "deductible": money(m.group(14)), "paid": money(m.group(15)), "remarks": m.group(16)})
    p["claims"] = claims
    return p

# ------------------------------------------------------------------ Mutual of Omaha / United of Omaha (Zelis remit)
def parse_moo(t):
    p = {"payer": "UNITED OF OMAHA LIFE (MUTUAL OF OMAHA)", "family": "MUT01"}
    m = re.search(r"Payment Date:\s*(\d\d/\d\d/20\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"Payment Reference Number:\s*(\d+)", t); p["ref"] = m.group(1) if m else None
    m = re.search(r"Payment Amount:\s*(" + MONEY + ")", t); p["amount"] = money(m.group(1)) if m else None
    p["summary"] = parse_summary_rows(t)
    return p
def parse_moo_detail(t):
    """Mutual of Omaha (Zelis) claim detail: 'Claim #: 586522284900-015 Patient Acct #: 19437265A Member #: 91008294M' + line
    '04/02/2026 001 99232 $111.00 $0.00 $96.62 $111.00 $0.00 $0.00 $0.00 $0.00 $0.00 $14.38 OA23'"""
    claims = []
    for b in re.split(r"\n(?=Claim #:)", "\n" + t):
        m = re.search(r"Claim #:\s*([\d\-]+)\s+Patient Acct #:\s*([0-9A-Z]{8,10})\s+Member #:\s*(\w+)", b)
        if not m: continue
        c = {"payer_claim": m.group(1), "acct": fixacct(m.group(2)), "member": m.group(3)}
        pm = re.search(r"Patient:\s*([A-Z][A-Z .'\-]+?)\s+Adjudication", b); c["patient"] = pm.group(1).strip() if pm else None
        lines = []
        for line in b.splitlines():
            lm = re.match(r"\s*(\d\d/\d\d/20\d\d)\s+\d{3}\s+(99\d{3}|G\d{4})(?:/(\d\d))?(.*)$", line)
            if not lm: continue
            vals = [money(x) for x in re.findall(r"\$\s?[\d,]+\.\d\d", lm.group(4))]
            if len(vals) < 3: continue
            lines.append({"dos": norm_date(lm.group(1)), "cpt": lm.group(2), "mod": lm.group(3) or "", "billed": vals[0], "other_ins": vals[2] if len(vals) > 2 else None, "paid": vals[-1]})
        c["lines"] = lines
        claims.append(c)
    return claims
def parse_summary_rows(t):
    rows = []
    for rm in re.finditer(r"(\d{8}[A-Z]?)\s+([A-Z][A-Z .'\-]+?)\s+(\d\d/\d\d/20\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)\s+\$?([\d,]+\.\d\d)", t):
        rows.append({"acct": fixacct(rm.group(1)), "patient": rm.group(2).strip(), "dos": norm_date(rm.group(3)), "billed": money(rm.group(4)), "reduction": money(rm.group(5)), "paid": money(rm.group(6))})
    return rows

# ------------------------------------------------------------------ ECHO / EPC virtual card (Physicians Life etc.)
def parse_echo(t):
    p = {"family": "ECHO", "method": "vcard"}
    m = re.search(r"\n\s*\w?\s*([A-Z][A-Z' ]+(?:INSURANCE|LIFE|MUTUAL)[A-Z ]*COMPANY)", t); p["payer"] = m.group(1).strip() if m else "ECHO VCARD PAYER"
    m = re.search(r"(\d{4} \d{4} \d{4} \d{4})", t); p["card"] = m.group(1) if m else None
    m = re.search(r"EPC Draft #[:;]?\s*(\d+)", t); p["draft"] = m.group(1) if m else None
    m = re.search(r"Payment Date:\s*(\d\d/\d\d\s?20\d\d)", t); p["date"] = norm_date(m.group(1).replace(" ", "/")) if m else None
    m = re.search(r"Good Thru\s*&?\s*\n?\s*(\d{3})?\s*(\d\d/\d\d)", t); p["exp"] = m.group(2) if m else None
    claims = []
    for b in re.split(r"\n(?=Provider[:;]\s)", "\n" + t):
        m = re.search(r"Patient Acct\s*#?:?\s*([0-9A-Z]{8,10})", b)
        if not m: continue
        c = {"acct": fixacct(m.group(1))}
        m = re.search(r"Claim Number[:;]?\s*[©0O]?([A-Z0-9\-]+)", b); c["payer_claim"] = m.group(1) if m else None
        m = re.search(r"Patient Name[:;]?\s*([A-Z][A-Z .'\-]+?)\s+Policy", b); c["patient"] = m.group(1).strip() if m else None
        m = re.search(r"Policy #:\s*(\d+)", b); c["policy"] = m.group(1) if m else None
        lines = []
        for lm in re.finditer(r"(\d\d/\d\d/\d\d|\d{6})\s*=?\s*\|?\s*(99\d{3}|G\d{4})\s*\|?\s*([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\)?\s*\|?\s*(\d{1,3})\s*\|?\s*([\d,]+\.\d\d)", b):
            d = lm.group(1); dos = norm_date(d) if "/" in d else "20%s-%s-%s" % (d[4:6], d[0:2], d[2:4])
            lines.append({"dos": dos, "cpt": lm.group(2), "billed": money(lm.group(3)), "allowed": money(lm.group(4)), "deductible": money(lm.group(5)), "copay": money(lm.group(6)), "carc": lm.group(7), "paid": money(lm.group(8))})
        c["lines"] = lines
        claims.append(c)
    p["claims"] = claims
    return p

# ------------------------------------------------------------------ paper checks
def parse_check(t, payer):
    p = {"method": "check", "payer": payer}
    m = re.search(r"CHECK[ _]*NUMBER[^\n]*\n[^\n]*?(\d{8,10})", t); p["check_number"] = m.group(1) if m else None
    if not p["check_number"]:
        cands = [x for x in re.findall(r"\b(\d{8,10})\b", t) if x not in ("814723941", "1629515325", "32308448", "323084486")]
        p["check_number"] = cands[0] if cands else None
    m = re.search(r"(\d\d/\d\d/20\d\d|\d{1,2}/\d{1,2}/\d\d)", t); p["date"] = norm_date(m.group(1)) if m else None
    m = re.search(r"\$+\s?\*{0,3}\s?([\d,]+\.\d\d)", t); p["amount"] = money(m.group(1)) if m else None
    m = re.search(r"Claim#?:?\s*_?-?\s*(\d{12,14})", t); p["icn"] = m.group(1) if m else None
    m = re.search(r"PAY\s+\*+([A-Za-z ]+?Dollars?[A-Za-z ]+?Cents?)", t, re.I); p["amount_words"] = m.group(1).strip() if m else None
    return p

def run():
    out = []
    for pg in PAGES:
        ty = pg["type"]; t = txt(pg); rec = {"batch": pg["batch"], "page": pg["page"], "type": ty, "doccode": doccode(t)}
        if ty == "ua_eob_detail": rec["claims"] = parse_ua_detail(t)
        elif ty == "ua_eop_cover": rec["payment"] = parse_ua_cover(t); rec["claims"] = parse_ua_detail(t)
        elif ty == "zelis_vcard": rec["payment"] = parse_zelis_vcard(t)
        elif ty == "wn_remit": rec["payment"] = parse_wn(t)
        elif ty == "eob_generic" and "Claim #:" in t and "Patient Acct #" in t: rec["claims"] = parse_generic_claim_detail(t); rec["type"] = "wn_detail"
        elif ty in ("eob_generic", "eob_other", "other") and ("EPC Draft" in t or "echovcards" in t): rec["payment"] = parse_echo(t); rec["type"] = "echo_vcard"
        elif ty == "aetna_ssi_remit": rec["payment"] = parse_aetna_ssi(t)
        elif ty == "champva_eob": rec["payment"] = parse_champva(t)
        elif ty in ("fcc_remit", "fcc_zero_payment"): rec["payment"] = parse_fcc(t)
        elif ty == "simply_remit" or (ty == "other" and "Simply" in t and "Patient" in t): rec["payment"] = parse_simply(t); rec["type"] = "simply_remit"
        elif ty in ("bcbs_remit", "medicare_remit") or (ty == "other" and "BlueCross" in t): rec["payment"] = parse_bcbs(t); rec["type"] = "bcbs_remit"
        elif ty == "moo_remit": rec["payment"] = parse_moo(t); rec["claims"] = parse_moo_detail(t)
        elif ty == "other" and "Patient Acct #:" in t and "Member #:" in t and "Zelis Ref" in t: rec["claims"] = parse_moo_detail(t); rec["type"] = "moo_detail"
        elif ty == "payment_summary": rec["summary"] = parse_summary_rows(t)
        elif ty == "check_front": rec["payment"] = parse_check(t, pg.get("payer"))
        elif ty == "other" and "COMMUNITY CARE" in t and "BankUnited" in t: rec["payment"] = parse_check(t, "FCC"); rec["type"] = "check_front"
        out.append(rec)
    json.dump(out, open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/extracted.json", "w"), indent=1)
    return out
if __name__ == "__main__":
    out = run()
    from collections import Counter
    print(Counter(r["type"] for r in out))
    nclaims = sum(len(r.get("claims", []) or r.get("payment", {}).get("claims", []) or []) for r in out)
    print("claims parsed:", nclaims)
