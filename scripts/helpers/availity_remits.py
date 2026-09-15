#!/usr/bin/env python3
# PLAIN ENGLISH: Availity Remittance Viewer "Check/EFT list" exports are the exact source of
# (check number, payer, check date, amount) for every remit a payer delivered through Availity.
# This helper turns one or more of those CSVs into a check register, decodes the payer's
# check-number series into the bank lines they land on, and matches every money remit to a
# Regions deposit in the Treasury ledger by EXACT amount inside the payer's lag window
# (replacing the lag-only guesses the nightly e-mails allow). Read-only. No PHI in or out.
#
# Usage: python3 availity_remits.py --remits RemittanceViewer_CheckEftList_*.csv
#                                   --ledger deposits_ledger.csv --out availity_remit_recon.csv
"""Availity Check/EFT list -> check register + exact deposit matching (Treasury Payments)."""
import argparse, csv, datetime as dt, glob, re, sys
from collections import defaultdict

# Check-number series -> (family, bank descriptor(s) the money lands under, label).
# Learned 9/14/2026 from the Florida Blue export matched against Regions deposits.
SERIES = [
    (re.compile(r"^213\d{6}$"),   "BCBS", "Bcbsf",  "Florida Blue weekly main remit (Wednesdays)"),
    (re.compile(r"^423[78]\d{5}$"), "BCBS", "Bcbsf", "Florida Blue second line"),
    (re.compile(r"^190\d{6}$"),   "BCBS", "Feps2",  "Florida Blue - Federal Employee Program (FEP) line"),
    (re.compile(r"^355\d{6}$"),   "BCBS", "Pepf",   "Florida Blue - PEPF line"),
    (re.compile(r"^130\d{6}$"),   "BCBS", "?",      "Florida Blue - 130 series (bank line unconfirmed)"),
    (re.compile(r"^620\d{6}$"),   "BCBS", "?",      "Florida Blue - 620 series (bank line unconfirmed)"),
    (re.compile(r"^705\d{6}$"),   "BCBS", "?",      "Health Options, Inc. (Florida Blue HMO) money remit"),
    (re.compile(r"^26\d{8}$"),    "BCBS", "-",      "Florida Blue / Health Options $0 denial-only remit (26YYMMDD + seq)"),
    (re.compile(r"^\d{9}26\d{4}$"), "HUM01", "Hmp|Humana Ins Co|Eic", "Humana (9 digits + YYMMDD)"),
    (re.compile(r"^81[89]\d{6}$"), "FLO02", "FCSO Medicare", "Medicare Part B FCSO"),
    (re.compile(r"^41\d{5}$"),    "CAP07", "Capital Health P", "Capital Health Plan"),
    (re.compile(r"^09\d{8}$"),    "CENTENE", "Sunshine State H|Marketplace", "Centene (Sunshine / Ambetter)"),
]
PAYER_FAMILY = {"florida blue": "BCBS", "health options, inc.": "BCBS", "humana": "HUM01", "aetna": "AET"}
# Money lands this many calendar days after the check date, inclusive window.
LAG = {"BCBS": (0, 3), "HUM01": (0, 4), "FLO02": (0, 4), "CAP07": (0, 2), "CENTENE": (0, 4), "AET": (0, 5)}

def decode(check, payer):
    for rx, fam, bank, label in SERIES:
        if rx.match(check):
            return fam, bank, label
    return PAYER_FAMILY.get(payer.lower(), "?"), "?", "unrecognised series"

def money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    return round(float(s), 2) if s not in ("", "-") else 0.0

def mdy(s):
    return dt.datetime.strptime(s.strip(), "%m/%d/%Y").date()

def load_remits(paths):
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                check = r["Check/EFT #"].strip()
                fam, bank, label = decode(check, r["Payer"].strip())
                rows.append({"check": check, "payer": r["Payer"].strip(), "check_date": mdy(r["Check/EFT Date"]),
                             "received": mdy(r["Received by Availity"]), "amount": money(r["Check/EFT Amount"]),
                             "family": fam, "bank_line": bank, "series": label, "source": p})
    # de-duplicate across overlapping exports
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (r["check_date"], r["check"])):
        if r["check"] in seen: continue
        seen.add(r["check"]); out.append(r)
    return out

def load_ledger(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["_date"] = dt.date.fromisoformat(r["date"])
        r["_amount"] = money(r["amount"]) if r["amount"] else None
    return rows

def reconcile(remits, ledger):
    used = set()
    for rem in remits:
        rem["match"] = None
        if rem["amount"] <= 0: rem["status"] = "ZERO-PAY"; continue
        lo, hi = LAG.get(rem["family"], (0, 5))
        cands = [d for i, d in enumerate(ledger) if i not in used and d["_amount"] == rem["amount"]
                 and d.get("family") == rem["family"] and lo <= (d["_date"] - rem["check_date"]).days <= hi]
        if cands:
            d = cands[0]; used.add(ledger.index(d))
            rem["match"] = d; rem["status"] = "MATCHED"
            rem["prior_ledger_check"] = d.get("era_check", ""); rem["prior_ledger_status"] = d.get("status", "")
        else:
            span = [d["_date"] for d in ledger if d["_amount"] is not None]
            first_land = rem["check_date"] + dt.timedelta(days=lo)
            inside = span and min(span) <= first_land <= max(span)
            rem["status"] = "NO-DEPOSIT" if inside else "OUTSIDE-LEDGER"
    return remits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remits", nargs="+", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", default="availity_remit_recon.csv")
    a = ap.parse_args()
    paths = [p for pat in a.remits for p in glob.glob(pat)]
    remits = reconcile(load_remits(paths), load_ledger(a.ledger))
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["check", "payer", "series", "bank_line", "check_date", "received_by_availity", "amount",
                    "status", "deposit_date", "deposit_descriptor", "deposit_amount", "lag_days",
                    "ledger_previous_check", "ledger_previous_status"])
        for r in remits:
            m = r["match"]
            w.writerow([r["check"], r["payer"], r["series"], r["bank_line"], r["check_date"], r["received"],
                        f'{r["amount"]:.2f}', r["status"],
                        m["date"] if m else "", m["descriptor"] if m else "", m["amount"] if m else "",
                        (m["_date"] - r["check_date"]).days if m else "",
                        r.get("prior_ledger_check", ""), r.get("prior_ledger_status", "")])
    tot = defaultdict(float); n = defaultdict(int)
    for r in remits: tot[r["status"]] += r["amount"]; n[r["status"]] += 1
    print(f"{len(remits)} remits from {len(paths)} export(s); wrote {a.out}")
    for s in ("MATCHED", "NO-DEPOSIT", "OUTSIDE-LEDGER", "ZERO-PAY"):
        if n[s]: print(f"  {s:15} {n[s]:3}  ${tot[s]:,.2f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
