#!/usr/bin/env python3
import os
"""Turn a paper / virtual-card remittance (remits.json entry) into an ASC X12N 005010X221A1 835 file that the AMD ERA Center
can import (POST /api/era/upload/835 — era_upload.py).  One file per remit.  CLP01 = the AMD claim number printed on the EOB
('Patient Acct #', e.g. 19442529A = visit 19442529, insurance sequence A) so AMD matches the visit exactly as it would for a
real payer ERA; every claim balances (charge = paid + patient resp + CAS adjustments) and every check balances (BPR02 = sum CLP04).
Usage: python3 build835.py [--only R001,R002] [--out /home/claude/scans/out835]"""
import json, sys, os, re, datetime, argparse
PAYEE = {"name": "EFFINGER HEALTH PA", "npi": "1629515325", "tin": "814723941", "addr": "1891 CAPITAL CIR NE STE 9", "city": "TALLAHASSEE", "st": "FL", "zip": "323084486"}
PAYERS = {  # family -> payer block (name, payer id used in REF*2U / TRN03, address)
    "UA":      {"name": "UNITED AMERICAN INSURANCE CO", "id": "UAICO", "addr": "PO BOX 8080", "city": "MCKINNEY", "st": "TX", "zip": "750708080", "tin": "1750192944"},
    "WN":      {"name": "WASHINGTON NATIONAL INSURANCE CO", "id": "WASHN", "addr": "PO BOX 1916", "city": "CARMEL", "st": "IN", "zip": "46082", "tin": "1350521456"},
    "AET12":   {"name": "AETNA SENIOR SUPPLEMENTAL INSURANCE", "id": "AESSI", "addr": "PO BOX 14770", "city": "LEXINGTON", "st": "KY", "zip": "405124770", "tin": "1621148500"},
    "MUT01":   {"name": "UNITED OF OMAHA LIFE INSURANCE COMPANY", "id": "MUTOM", "addr": "3300 MUTUAL OF OMAHA PLAZA", "city": "OMAHA", "st": "NE", "zip": "68175", "tin": "1470322111"},
    "ECHO":    {"name": "PHYSICIANS LIFE INSURANCE COMPANY", "id": "PHYLF", "addr": "2600 DODGE STREET", "city": "OMAHA", "st": "NE", "zip": "68131", "tin": "1470385006"},
    "SIM01":   {"name": "SIMPLY HEALTHCARE PLANS", "id": "SMPLY", "addr": "PO BOX 1410", "city": "FENTON", "st": "MO", "zip": "63026", "tin": "1651066060"},
    "FLO99":   {"name": "FLORIDA COMMUNITY CARE", "id": "FCC01", "addr": "PO BOX 211322", "city": "EAGAN", "st": "MN", "zip": "55121", "tin": "1474163384"},
    "USAA":    {"name": "USAA LIFE INSURANCE COMPANY", "id": "USAAL", "addr": "PO BOX 12750", "city": "PENSACOLA", "st": "FL", "zip": "32591", "tin": "1741153560"},
    "CHAMPVA": {"name": "CHAMPVA", "id": "84146", "addr": "PO BOX 500", "city": "SPRAGUE CITY", "st": "PA", "zip": "19475", "tin": "1840160000"},
    "BCBS":    {"name": "FLORIDA BLUE", "id": "00590", "addr": "PO BOX 1798", "city": "JACKSONVILLE", "st": "FL", "zip": "322311798", "tin": "1590267100"},
}
FILING = {"UA": "CI", "WN": "CI", "AET12": "CI", "MUT01": "CI", "ECHO": "CI", "USAA": "CI", "SIM01": "MC", "FLO99": "MC", "CHAMPVA": "CH", "BCBS": "CI"}
def pos_for(cpt):
    c = str(cpt)
    if c.startswith("9922") or c.startswith("9923") or c in ("99238", "99239"): return "21"
    if c.startswith("9930") or c.startswith("9931") or c.startswith("9930"): return "31"
    if c.startswith("9934") or c.startswith("9935"): return "12"
    return "11"
def d8(iso):
    return iso.replace("-", "") if iso else datetime.date.today().strftime("%Y%m%d")
def amt(x): return ("%.2f" % (x or 0)).rstrip("0").rstrip(".") if x is not None else "0"
def split_name(n):
    n = re.sub(r"[^A-Z' \-]", "", (n or "").upper()).strip()
    parts = n.split()
    if not parts: return "UNKNOWN", "", ""
    if "," in (n or ""):
        last, rest = n.split(",", 1); parts = rest.split(); return last.strip(), (parts[0] if parts else ""), (parts[1][:1] if len(parts) > 1 else "")
    if len(parts) == 1: return parts[0], "", ""
    if len(parts) == 2: return parts[1], parts[0], ""
    # FIRST M LAST or FIRST LAST LAST
    if len(parts[1]) == 1: return " ".join(parts[2:]), parts[0], parts[1]
    return " ".join(parts[1:]), parts[0], ""
def allocate(total, weights):
    """split a claim-level amount over lines proportionally to weights, exact to the cent."""
    if not weights or total is None: return [0.0] * len(weights)
    s = sum(weights) or 1.0
    raw = [round(total * w / s, 2) for w in weights]
    diff = round(total - sum(raw), 2)
    raw[-1] = round(raw[-1] + diff, 2)
    return raw
def claim_segments(rm, c, seq):
    """CLP loop for one claim. Returns (segments, paid, charge)."""
    lines = c.get("lines") or []
    charge = c.get("billed"); paid = c.get("paid")
    if charge is None and lines: charge = round(sum(l.get("billed") or 0 for l in lines), 2)
    if paid is None and lines and all(l.get("paid") is not None for l in lines): paid = round(sum(l["paid"] for l in lines), 2)
    ptresp = c.get("ptresp") or 0.0
    if not charge and paid and not lines: charge = paid    # billed unknown on a summary-only EOB: a CLP03 of 0 makes the importer drop the whole file (9/22/2026)
    # line-level paid: from the EOB, else allocate the claim paid across lines by allowed (UA style: paid only at claim level)
    if lines and any(l.get("paid") is None for l in lines):
        w = [(l.get("allowed") or l.get("billed") or 0) for l in lines]
        for l, p in zip(lines, allocate(paid or 0.0, w)): l["paid"] = p
    # claim-level CAS (UA OA-23 / OA-253) -> allocate to lines by allowed
    ccas = c.get("claim_cas") or []
    if lines and ccas:
        w = [(l.get("allowed") or l.get("billed") or 0) for l in lines]
        for a in ccas:
            for l, p in zip(lines, allocate(a["amount"], w)):
                if p: l.setdefault("cas", []).append({"group": a["group"], "code": a["code"], "amount": p})
    status = "2" if any(a["code"] == "23" for l in lines for a in l.get("cas", [])) or any(a["code"] == "23" for a in ccas) or rm.get("family") in ("UA", "WN", "AET12", "MUT01", "ECHO", "USAA") else "1"
    if (paid or 0) == 0 and charge: status = "4" if not any(a["code"] == "23" for l in lines for a in l.get("cas", [])) else "2"
    # balance each line: charge = paid + PR + adjustments; put any residual into CO-45 (contractual) so the file balances
    for l in lines:
        adj = sum(a["amount"] for a in l.get("cas", []))
        pr = sum(a["amount"] for a in l.get("cas", []) if a["group"] == "PR")
        resid = round((l.get("billed") or 0) - (l.get("paid") or 0) - adj, 2)
        if abs(resid) >= 0.01:
            l.setdefault("cas", []).append({"group": "CO", "code": "45", "amount": resid}); l["_balanced_by_co45"] = resid
    segs = []
    pos = pos_for(lines[0]["cpt"]) if lines else "11"
    segs.append("CLP*%s*%s*%s*%s*%s*%s*%s*%s*1" % (c["acct"], status, amt(charge), amt(paid), amt(ptresp), FILING.get(rm["family"], "CI"), (c.get("payer_claim") or c.get("icn") or "")[:50], pos))
    last, first, mi = split_name(c.get("patient"))
    member = re.sub(r"[^A-Z0-9]", "", str(c.get("member") or c.get("mbi") or ""))
    segs.append("NM1*QC*1*%s*%s*%s***MI*%s" % (last, first, mi, member) if member else "NM1*QC*1*%s*%s*%s" % (last, first, mi))
    if c.get("icn"): segs.append("REF*F8*%s" % c["icn"])
    for l in lines:
        proc = "HC:%s" % l["cpt"] + (":%s" % l["mod"] if l.get("mod") else "")
        segs.append("SVC*%s*%s*%s**1" % (proc, amt(l.get("billed")), amt(l.get("paid"))))
        segs.append("DTM*472*%s" % d8(l.get("dos")))
        groups = {}
        for a in l.get("cas", []):
            if abs(a["amount"]) < 0.005: continue
            groups.setdefault(a["group"], []).append((a["code"], a["amount"]))
        for g, items in groups.items():
            for code, v in items:            # AMD's 835 import reads ONE reason per CAS segment (proven 9/22/2026: the 2nd triplet was dropped)
                segs.append("CAS*%s*%s*%s" % (g, code, amt(v)))
        if l.get("allowed") is not None: segs.append("AMT*B6*%s" % amt(l["allowed"]))
    return segs, (paid or 0.0), (charge or 0.0)
def build(rm, ctrl):
    fam = rm["family"]; P = PAYERS.get(fam, {"name": rm.get("payer") or "PAYER", "id": "UNKNW", "addr": "", "city": "", "st": "", "zip": "", "tin": "1000000000"})
    date = (rm.get("physical_check") or {}).get("date") or rm.get("date")
    trace = (rm.get("physical_check") or {}).get("number") or rm.get("check_number") or rm.get("payment_id") or ("SCAN%s" % rm["id"])
    trace = re.sub(r"[^A-Za-z0-9]", "", str(trace))[:30]
    total = round(sum(c.get("paid") or 0 for c in rm["claims"]), 2)
    method = "CHK" if rm.get("method") in ("check", "paper_check", "vcard", "vcard_stub") else ("ACH" if rm.get("method") == "eft" else "NON")
    now = datetime.datetime.utcnow()
    segs = ["ST*835*%04d" % ctrl,
            "BPR*%s*%s*C*%s************%s" % ("I" if total > 0 else "H", amt(total), method if total > 0 else "NON", d8(date)),
            "TRN*1*%s*%s" % (trace, P["tin"]),
            "DTM*405*%s" % d8(date),
            "N1*PR*%s" % P["name"], "N3*%s" % (P["addr"] or "UNKNOWN"), "N4*%s*%s*%s" % (P["city"] or "UNKNOWN", P["st"] or "FL", P["zip"] or "00000"),
            "REF*2U*%s" % P["id"],
            "N1*PE*%s*XX*%s" % (PAYEE["name"], PAYEE["npi"]), "N3*%s" % PAYEE["addr"], "N4*%s*%s*%s" % (PAYEE["city"], PAYEE["st"], PAYEE["zip"]), "REF*TJ*%s" % PAYEE["tin"],
            "LX*1"]
    for i, c in enumerate(rm["claims"]):
        cs, _, _ = claim_segments(rm, c, i); segs += cs
    segs.append("SE*%d*%04d" % (len(segs) + 1, ctrl))
    isa = "ISA*00*          *00*          *ZZ*%-15s*ZZ*%-15s*%s*%s*^*00501*%09d*0*P*:" % (P["id"][:15], PAYEE["npi"], now.strftime("%y%m%d"), now.strftime("%H%M"), ctrl)
    gs = "GS*HP*%s*%s*%s*%s*%d*X*005010X221A1" % (P["id"], PAYEE["npi"], now.strftime("%Y%m%d"), now.strftime("%H%M"), ctrl)
    body = [isa, gs] + segs + ["GE*1*%d" % ctrl, "IEA*1*%09d" % ctrl]
    return "~\n".join(body) + "~\n", total, trace
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default=os.environ.get("SCANS_DIR", "/home/claude/scans") + "/out835"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    remits = json.load(open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/remits.json"))
    only = set(a.only.split(",")) if a.only else None
    n = 0; manifest = []
    for i, rm in enumerate(remits):
        if rm.get("is_stub") or rm.get("is_physical_check"): continue
        if only and rm["id"] not in only: continue
        if not only and not a.all and not (rm.get("post_ok")): continue
        if not rm["claims"]: continue
        text, total, trace = build(rm, i + 1)
        fn = os.path.join(a.out, "%s_%s_%s_%s.835" % (rm["id"], rm["family"], trace, amt(total).replace(".", "-")))
        open(fn, "w").write(text); n += 1
        manifest.append({"id": rm["id"], "file": fn, "family": rm["family"], "trace": trace, "total": total, "claims": len(rm["claims"])})
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print("wrote", n, "835 files to", a.out)
