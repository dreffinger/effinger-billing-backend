#!/usr/bin/env python3
"""x12_835.py — parse raw X12 835 (ERA) files into claim rows. stdlib only.

Why: AMD's ERA Center (`GET /api/era/checkdetails`) gives paid amounts and
CARC/RARC per line but NO payer claim number (CLP07 / ICN) and no posted
history. The raw 835 from the Change Healthcare portal (AMD's clearinghouse)
carries both. This turns a downloaded 835 into rows the toolkit can use:
ICN lookups for tricare4u / myVACCN registration, denial detail for the
run-alert exclusions, and a check-by-check register for treasury matching.

Usage:
  python3 x12_835.py <file.835|.txt|.edi> [more files]        -> JSON to stdout
  python3 x12_835.py --csv out.csv <files...>                  -> one row per CLP
  python3 x12_835.py --by-check <files...>                     -> check totals only

Rows carry patient control numbers (CLP01 = our claim/visit id) and the
payer's ICN (CLP07); they carry NO names, so they pass the PHI gate as long
as you don't add NM1 patient names to the CSV (we deliberately keep only the
last-name initial... nothing: names are dropped entirely).
"""
import csv
import json
import sys

CLP_STATUS = {
    "1": "processed as primary", "2": "processed as secondary", "3": "processed as tertiary",
    "4": "denied", "19": "primary, forwarded", "20": "secondary, forwarded",
    "21": "tertiary, forwarded", "22": "reversal of prior", "23": "not our claim, forwarded",
    "25": "predetermination", "27": "reviewed",
}


def _split(raw):
    """Return list of segments (each a list of elements). Handles ISA-declared delimiters."""
    raw = raw.lstrip("﻿ \r\n\t")
    if not raw.startswith("ISA"):
        raise ValueError("not an X12 interchange (no ISA)")
    elem = raw[3]
    seg_term = raw[105] if len(raw) > 105 else "~"
    body = raw.replace("\r\n", "").replace("\n", "") if seg_term != "\n" else raw
    segs = []
    for s in body.split(seg_term):
        s = s.strip()
        if s:
            segs.append(s.split(elem))
    return segs


def parse(raw):
    """One 835 file -> {'checks': [ {trn, payer, payee, amount, date, method, claims:[...]} ]}"""
    segs = _split(raw)
    checks, chk, clp, svc = [], None, None, None
    loop_payer = False
    for s in segs:
        tag = s[0]
        if tag == "ST" and s[1] == "835":
            chk = {"trn": "", "amount": "", "method": "", "date": "", "payer": "", "payer_id": "",
                   "payee_npi": "", "claims": []}
            checks.append(chk)
            clp = svc = None
        elif chk is None:
            continue
        elif tag == "BPR":
            chk["amount"] = s[2] if len(s) > 2 else ""
            chk["method"] = s[4] if len(s) > 4 else ""
            chk["date"] = s[16] if len(s) > 16 else ""
        elif tag == "TRN":
            chk["trn"] = s[2] if len(s) > 2 else ""
        elif tag == "N1":
            loop_payer = s[1] == "PR"
            if s[1] == "PR":
                chk["payer"] = s[2] if len(s) > 2 else ""
            elif s[1] == "PE":
                chk["payee_npi"] = s[4] if len(s) > 4 else ""
        elif tag == "REF" and loop_payer and clp is None and s[1] in ("2U", "EO", "HI", "NF"):
            chk["payer_id"] = s[2]
        elif tag == "CLP":
            clp = {
                "patient_control": s[1], "status": s[2], "status_text": CLP_STATUS.get(s[2], s[2]),
                "charged": s[3], "paid": s[4], "patient_resp": s[5] if len(s) > 5 else "",
                "filing_ind": s[6] if len(s) > 6 else "", "icn": s[7] if len(s) > 7 else "",
                "adjustments": [], "services": [], "remarks": [],
            }
            chk["claims"].append(clp)
            svc = None
        elif tag == "CAS" and clp is not None:
            target = svc if svc is not None else clp
            group = s[1]
            i = 2
            while i + 1 < len(s):
                if s[i]:
                    target["adjustments"].append({"group": group, "carc": s[i], "amount": s[i + 1]})
                i += 3
        elif tag == "SVC" and clp is not None:
            code = s[1].split(":")[1] if ":" in s[1] else s[1]
            svc = {"cpt": code, "charged": s[2], "paid": s[3],
                   "units": s[5] if len(s) > 5 else "", "dos": "", "adjustments": [], "remarks": []}
            clp["services"].append(svc)
        elif tag == "DTM" and clp is not None:
            if s[1] == "472" and svc is not None:
                svc["dos"] = s[2]
            elif s[1] in ("232", "233") and svc is None:
                clp.setdefault("claim_dates", []).append(s[2])
        elif tag == "LQ" and clp is not None and s[1] == "HE":
            (svc if svc is not None else clp)["remarks"].append(s[2])
        elif tag == "SE":
            clp = svc = None
        elif tag == "PLB":
            chk.setdefault("plb", []).append(s[1:])
    return {"checks": checks}


def rows(parsed, source=""):
    for chk in parsed["checks"]:
        for c in chk["claims"]:
            yield {
                "source": source, "payer": chk["payer"], "payer_id": chk["payer_id"],
                "check_trn": chk["trn"], "check_date": chk["date"], "check_amount": chk["amount"],
                "patient_control": c["patient_control"], "icn": c["icn"],
                "status": c["status"], "status_text": c["status_text"],
                "charged": c["charged"], "paid": c["paid"], "patient_resp": c["patient_resp"],
                "carcs": ";".join(f"{a['group']}{a['carc']}:{a['amount']}" for a in c["adjustments"]
                                  + [a for s in c["services"] for a in s["adjustments"]]),
                "rarcs": ";".join(c["remarks"] + [r for s in c["services"] for r in s["remarks"]]),
                "cpts": ";".join(f"{s['cpt']}@{s['dos']}={s['paid']}" for s in c["services"]),
            }


def _main(argv):
    out_csv, by_check, files = None, False, []
    it = iter(argv)
    for a in it:
        if a == "--csv":
            out_csv = next(it)
        elif a == "--by-check":
            by_check = True
        else:
            files.append(a)
    if not files:
        print(__doc__)
        return 2
    all_rows, summary = [], []
    for fn in files:
        with open(fn, encoding="utf-8", errors="replace") as f:
            p = parse(f.read())
        for chk in p["checks"]:
            summary.append({"source": fn, "payer": chk["payer"], "trn": chk["trn"], "date": chk["date"],
                            "amount": chk["amount"], "claims": len(chk["claims"]),
                            "denied": sum(1 for c in chk["claims"] if c["status"] == "4")})
        all_rows.extend(rows(p, fn))
    if by_check:
        print(json.dumps(summary, indent=1))
    elif out_csv:
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()) if all_rows else ["source"])
            w.writeheader()
            w.writerows(all_rows)
        print(f"{len(all_rows)} claim rows from {len(summary)} checks -> {out_csv}")
    else:
        print(json.dumps({"checks": summary, "rows": all_rows}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
