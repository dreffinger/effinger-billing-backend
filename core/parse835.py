# PLAIN ENGLISH (Parse 835 files)
# Decides: Nothing. Turns raw X12 835 remit files into a readable inventory (check, payer, amount, claims).
# Rules it uses: No PHI printed by default.
# Never touches: AMD.
# ---
"""Parse X12 835 files into a payment inventory (no PHI printed by default).
Usage: python3 parse835.py <dir-or-files...>  -> writes era_inventory.json + era_inventory.csv"""
import sys, os, re, json, csv, glob, hashlib

def segs(txt):
    txt = txt.strip()
    # element sep is char 3 of ISA, segment terminator is char 105 (after ISA fixed-length)
    esep = txt[3]; sterm = txt[105] if len(txt) > 105 else "~"
    comp = txt[104]
    out = []
    for s in txt.split(sterm):
        s = s.strip("\r\n ")
        if s: out.append(s.split(esep))
    return out

def parse(path):
    txt = open(path, encoding="latin-1").read()
    if not txt.startswith("ISA"): return None
    S = segs(txt)
    doc = {"file": os.path.basename(path), "sha1": hashlib.sha1(txt.encode()).hexdigest()[:12],
           "payer": None, "payee_npi": None, "check": None, "check_date": None, "amount": None,
           "method": None, "trace": None, "claims": [], "plb": []}
    cur = None; loop = None
    for s in S:
        t = s[0]
        if t == "BPR":
            doc["amount"] = float(s[2]); doc["method"] = s[4]; doc["check_date"] = s[16] if len(s) > 16 else None
        elif t == "TRN":
            doc["check"] = s[2]; doc["trace"] = s[3] if len(s) > 3 else None
        elif t == "N1" and s[1] == "PR": doc["payer"] = s[2]
        elif t == "N1" and s[1] == "PE": doc["payee_npi"] = s[4] if len(s) > 4 else None
        elif t == "CLP":
            cur = {"claim": s[1], "status": s[2], "billed": float(s[3]), "paid": float(s[4]),
                   "pat_resp": float(s[5]) if len(s) > 5 and s[5] else 0.0, "payer_icn": s[7] if len(s) > 7 else None,
                   "patient": None, "member_id": None, "svc": [], "adj": []}
            doc["claims"].append(cur)
        elif t == "NM1" and cur is not None and s[1] == "QC":
            cur["patient"] = (s[3] + "," + (s[4] if len(s) > 4 else "")).upper()
            cur["member_id"] = s[9] if len(s) > 9 else None
        elif t == "CAS" and cur is not None:
            if cur["svc"]: cur["svc"][-1]["adj"].append(s[1:])
            else: cur["adj"].append(s[1:])
        elif t == "SVC" and cur is not None:
            cur["svc"].append({"proc": s[1], "billed": float(s[2]), "paid": float(s[3]), "units": s[5] if len(s) > 5 else None, "dos": None, "adj": []})
        elif t == "DTM" and cur is not None and s[1] in ("472", "150", "151"):
            if cur["svc"]: cur["svc"][-1]["dos"] = s[2]
            else: cur["dos"] = s[2]
        elif t == "PLB":
            doc["plb"].append(s[1:])
    return doc

if __name__ == "__main__":
    files = []
    for a in sys.argv[1:]:
        files += sorted(glob.glob(os.path.join(a, "*"))) if os.path.isdir(a) else [a]
    docs = []; seen = {}
    for f in files:
        try: d = parse(f)
        except Exception as e: print("ERR", f, e); continue
        if not d: continue
        key = (d["check"], d["amount"])
        if key in seen: d["dup_of"] = seen[key]
        else: seen[key] = d["file"]
        docs.append(d)
    json.dump(docs, open("era_inventory.json", "w"), indent=1)
    uniq = [d for d in docs if "dup_of" not in d]
    with open("era_inventory.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["file","payer","check","check_date","method","amount","n_claims","claims_paid_sum"])
        for d in uniq:
            w.writerow([d["file"], d["payer"], d["check"], d["check_date"], d["method"], d["amount"], len(d["claims"]), round(sum(c["paid"] for c in d["claims"]),2)])
    from collections import Counter, defaultdict
    print("files=%d unique_checks=%d dups=%d" % (len(docs), len(uniq), len(docs)-len(uniq)))
    by = defaultdict(lambda: [0, 0.0, 0])
    for d in uniq:
        b = by[d["payer"]]; b[0] += 1; b[1] += d["amount"]; b[2] += len(d["claims"])
    for p, (n, amt, nc) in sorted(by.items(), key=lambda x: -x[1][1]):
        print("  %-45s checks=%3d  $%10.2f  claims=%d" % (p, n, amt, nc))
    dates = sorted(d["check_date"] for d in uniq if d["check_date"])
    print("check dates:", dates[0], "->", dates[-1])
