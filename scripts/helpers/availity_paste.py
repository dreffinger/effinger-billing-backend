#!/usr/bin/env python3
# PLAIN ENGLISH: William pastes screens from Availity's Remittance Viewer into chat (or into a
# text file on Drive). Two shapes exist: (A) the CLAIM LIST under a check - 11 lines per claim:
# service dates, payer claim number (ICN), payer, check number, (check date), patient, (AMD
# account = visit id + claim letter), (member id), patient responsibility, billed, paid; and
# (B) the CLAIM DETAIL - labelled header, then the values, then the service lines (HC:CPT,
# units, allowed, charge, adj, paid) and the code blocks (payer proprietary codes, RARCs,
# CAS group + reason + amount). This helper turns either shape into ERA-style rows the run
# can post or verify: one row per service line (or per claim when no lines were pasted) with
# check, check date, ICN, visit id, claim letter, CPT, charge, allowed, paid, patient resp,
# contractual adj and the codes. Names and member ids are dropped on output (visit id is enough).
#
# Usage: python3 availity_paste.py <pasted.txt> [more.txt ...] [--json out.json] [--csv out.csv]
"""Parse Availity Remittance Viewer pastes (claim list / claim detail) into ERA-style rows."""
import csv, json, re, sys

MONEY = re.compile(r"^\(?-?\$?[\d,]*\.\d{2}\)?$")
DATES = re.compile(r"^(\d{2}/\d{2}/\d{4}) - (\d{2}/\d{2}/\d{4})$")
ICN   = re.compile(r"^[A-Z]?\d{10,20}$")
ACCT  = re.compile(r"^\(?(\d{7,9})([A-Z])?\)?$")
CHECK = re.compile(r"^\d{6,16}$")
CPT   = re.compile(r"^HC:([A-Z0-9]{5})(?::(\w+))?")
GROUP = re.compile(r"^(CO|PR|OA|PI|CR) - ")
CARC  = re.compile(r"^(\d{1,3}) - (.*)$")
RARC  = re.compile(r"^(M[A-Z]?\d{1,3}|N\d{1,3}) - (.*)$")
PROP  = re.compile(r"^([A-Z][A-Z0-9]{3,7}) - (.*)$")
STATUS = re.compile(r"^(\d{1,2}) - (.*)$")

def money(s):
    neg = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()").replace("$", "").replace(",", "") or 0)
    return -v if neg else v

def lines_of(path):
    return [l.strip() for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]

def parse_list(L):
    """Shape A: blocks of 11 lines starting with a date range."""
    out, i = [], 0
    while i < len(L):
        m = DATES.match(L[i])
        if not m or i + 10 >= len(L) or not ICN.match(L[i+1]):
            i += 1; continue
        acct = ACCT.match(L[i+6].strip("()"))
        out.append({"shape": "list", "dos_from": m.group(1), "dos_to": m.group(2), "icn": L[i+1],
                    "payer": L[i+2], "check": L[i+3], "check_date": L[i+4].strip("()"),
                    "visit": acct.group(1) if acct else "", "claim_letter": (acct.group(2) or "") if acct else "",
                    "patient_resp": money(L[i+8]), "charge": money(L[i+9]), "paid": money(L[i+10]),
                    "cpt": "", "allowed": None, "adj": None, "status": "", "codes": [], "rarc": [], "prop": []})
        i += 11
    return out

def parse_detail(L):
    """Shape B: one claim detail screen (labels first, then values)."""
    if "Payer Claim Control #" not in L: return []
    hdr = L.index("Payer Claim Control #")
    dos = next((DATES.search(l) for l in L if DATES.search(l)), None)
    # the value block starts after the last header label ("Total Paid")
    v = L.index("Total Paid") + 1
    vals = L[v:v+8]                       # name, status, acct, icn, PR, charge, adj, paid
    acct = ACCT.match(vals[2]) if len(vals) > 2 else None
    st = STATUS.match(vals[1]) if len(vals) > 1 else None
    claim = {"shape": "detail", "dos_from": dos.group(1) if dos else "", "dos_to": dos.group(2) if dos else "",
             "icn": vals[3] if len(vals) > 3 else "", "status": st.group(2) if st else vals[1] if len(vals) > 1 else "",
             "visit": acct.group(1) if acct else "", "claim_letter": (acct.group(2) or "") if acct else "",
             "patient_resp": money(vals[4]), "charge": money(vals[5]), "adj": money(vals[6]), "paid": money(vals[7]),
             "payer": "", "check": "", "check_date": ""}
    # service lines: DOS, HC:CPT, units, allowed, charge, adj, paid
    rows, i = [], v + 8
    while i < len(L):
        d = DATES.match(L[i])
        if d and i + 6 < len(L) and CPT.match(L[i+1]):
            c = CPT.match(L[i+1])
            rows.append(dict(claim, dos_from=d.group(1), dos_to=d.group(2), cpt=c.group(1),
                             modifier=c.group(2) or "", units=L[i+2], allowed=money(L[i+3]),
                             charge=money(L[i+4]), adj=money(L[i+5]), paid=money(L[i+6]),
                             codes=[], rarc=[], prop=[]))
            i += 7; continue
        i += 1
    if not rows: rows = [dict(claim, cpt="", allowed=None, codes=[], rarc=[], prop=[])]
    # code blocks apply to the whole pasted claim (per-line attribution is not shown on screen)
    group = None
    for l in L:
        g = GROUP.match(l)
        if g: group = g.group(1); continue
        if group and CARC.match(l):
            for r in rows: r["codes"].append(f"{group}-{CARC.match(l).group(1)}")
            continue
        if RARC.match(l):
            for r in rows: r["rarc"].append(RARC.match(l).group(1))
        elif PROP.match(l) and not STATUS.match(l) and not GROUP.match(l):
            for r in rows: r["prop"].append(PROP.match(l).group(1))
    for r in rows:
        r["codes"] = sorted(set(r["codes"])); r["rarc"] = sorted(set(r["rarc"])); r["prop"] = sorted(set(r["prop"]))
    return rows

def main(argv):
    jout = argv[argv.index("--json")+1] if "--json" in argv else None
    cout = argv[argv.index("--csv")+1] if "--csv" in argv else None
    paths = [a for a in argv if not a.startswith("--") and a not in (jout, cout)]
    rows = []
    for p in paths:
        L = lines_of(p)
        rows += parse_detail(L) if "Payer Claim Control #" in L else parse_list(L)
    for r in rows:
        r["action"] = ("post: pay %.2f + WOINS %.2f" % (r["paid"], -(r["adj"] or 0)) if r["paid"] and r.get("adj")
                       else "post: pay %.2f" % r["paid"] if r["paid"]
                       else "patient/secondary: %.2f PR" % r["patient_resp"] if r["patient_resp"]
                       else "denial - read codes")
    if jout: json.dump(rows, open(jout, "w"), indent=1)
    if cout:
        keys = ["shape", "check", "check_date", "payer", "icn", "status", "visit", "claim_letter", "dos_from", "dos_to",
                "cpt", "units", "charge", "allowed", "paid", "patient_resp", "adj", "codes", "rarc", "prop", "action"]
        with open(cout, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader()
            for r in rows: w.writerow({k: (" ".join(v) if isinstance(v, list) else v) for k, v in r.items()})
    for r in rows:
        print(f'{r["shape"]:6} visit {r["visit"]}{r["claim_letter"]} icn {r["icn"]} dos {r["dos_from"]} cpt {r.get("cpt","") or "-":6} '
              f'charge {r["charge"]:.2f} paid {r["paid"]:.2f} PR {r["patient_resp"]:.2f} adj {r.get("adj") or 0:.2f} '
              f'{" ".join(r["codes"])} {" ".join(r["rarc"])} {" ".join(r["prop"])} -> {r["action"]}')
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
