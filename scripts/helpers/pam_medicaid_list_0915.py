# PLAIN ENGLISH (dry list of Pam's open Medicaid-family claims - William 11/19/2026 press, item D) - READ ONLY.
# Decides: nothing. From outstanding_claims.json (this run's read-only snapshot) takes every visit whose open insurance balance sits at a
#   Medicaid-family carrier (MCAD, SUN01, FLO99, SIM01, HUM01, WEL04, UHCMA), reads its live charges (gettxhistory per visit) and keeps
#   the ones rendered by the nurse practitioner (provname carries GARLAND-G or GARLAND - the NP is GARLAND-G, PAMELA, provcode GARLAND-G). Per visit: chart, visit, DOS, CPT, carrier, last bill date,
#   last payer answer (newest non-void payment row: amount / carrier / date), open dollars, and the dry plan: a visit with a non-zero
#   payment posted = SETTLING (never re-rendered); otherwise RE-RENDER -> Dr. Effinger under the group NPI, frequency 1 unless a payer
#   ICN is on the charge (then frequency 7 with the ICN). Writes registers/pam_medicaid_list_<stamp>.json + .csv. Never writes to AMD.
import txh, amd, json, csv, sys, re, datetime
MEDICAID = {"MCAD","SUN01","FLO99","SIM01","HUM01","WEL04","UHCMA"}
stamp = sys.argv[1] if len(sys.argv) > 1 else "now"
amd.login_cached()
o = json.load(open("outstanding_claims.json"))
rows = [r for r in o["rows"] if r["carriercode"] in MEDICAID]
out = []; seen = set()
for i, r in enumerate(rows):
    key = (r["patientid"], r["visitid"])
    if key in seen: continue
    seen.add(key)
    try: root = txh.fetch_visit(r["patientid"], r["visitid"])
    except Exception as e: out.append({"pid": r["patientid"], "vid": r["visitid"], "kind": "READ-FAIL", "err": str(e)[:80]}); continue
    chs = [c.attrib for c in root.iter("charge") if c.attrib.get("void") != "1" and re.sub(r"\D","",c.attrib.get("visit") or "") == str(r["visitid"])]
    if not chs: out.append({"pid": r["patientid"], "vid": r["visitid"], "kind": "NO-LIVE"}); continue
    prov = (chs[0].get("provname") or "").upper(); npi = chs[0].get("npi")
    if "GARLAND" not in prov and "GARLAND-G" not in prov: continue
    pays = []
    for c in root.iter("charge"):
        if re.sub(r"\D","",c.attrib.get("visit") or "") != str(r["visitid"]): continue
        for p in c.iter("payment"):
            if p.attrib.get("void") == "1": continue
            pays.append((p.attrib.get("date") or "", float(p.attrib.get("amount") or 0), p.attrib.get("carrier") or "", p.attrib.get("checknumber") or ""))
    pays.sort()
    paid = any(a != 0 for _, a, _, _ in pays)
    last = pays[-1] if pays else None
    icn = ""
    for c in root.iter("charge"):
        if re.sub(r"\D","",c.attrib.get("visit") or "") == str(r["visitid"]):
            for p in c.iter("payment"):
                if p.attrib.get("origrefnum"): icn = p.attrib.get("origrefnum")
    bal = sum(float(c.get("insbal") or 0) for c in chs)
    plan = "SETTLING - a payment is posted, never re-rendered" if paid else ("RE-RENDER prof13 under the group NPI, frequency 7 with ICN " + icn if icn else "RE-RENDER prof13 under the group NPI, frequency 1")
    out.append({"pid": r["patientid"], "vid": r["visitid"], "dos": chs[0].get("dos"), "cpts": "+".join(c.get("proccode") for c in chs), "carrier": r["carriercode"],
                "billdate": chs[0].get("billdate"), "last_answer": ("%s %s %.2f %s" % (last[0], last[2], last[1], last[3])) if last else "none", "dollars": round(bal, 2), "prov": prov[:20], "plan": plan})
    if i % 50 == 0: print("..", i, "of", len(rows), flush=True)
json.dump(out, open("registers/pam_medicaid_list_%s.json" % stamp, "w"), indent=0)
with open("registers/pam_medicaid_list_%s.csv" % stamp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["pid","vid","dos","cpts","carrier","billdate","last_answer","dollars","prov","plan"]); w.writeheader()
    for x in out:
        if "kind" not in x: w.writerow(x)
ok = [x for x in out if "kind" not in x]
print("NP Medicaid-family open visits: %d, $%.2f; re-render candidates %d ($%.2f), settling %d ($%.2f); scanned %d Medicaid-family visits" % (
    len(ok), sum(x["dollars"] for x in ok), sum(1 for x in ok if x["plan"].startswith("RE-RENDER")), sum(x["dollars"] for x in ok if x["plan"].startswith("RE-RENDER")),
    sum(1 for x in ok if x["plan"].startswith("SETTLING")), sum(x["dollars"] for x in ok if x["plan"].startswith("SETTLING")), len(rows)))
