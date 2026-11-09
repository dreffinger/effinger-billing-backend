# PLAIN ENGLISH (run report, 1:39 AM ET 11/9/2026 slot, run 2026-11-09T0639Z) - READ ONLY.
# Decides: nothing. Builds "_run report 11-09 0139.csv" (per column: remaining rows with chart id, visit, carrier, error text and
# the standing action) from scan_2026-11-09T0639Z-engine/summary_after2.json and the engine report. Never touches AMD.
import json, csv, collections, sys
S = "2026-11-09T0639Z-engine"
s = json.load(open("scan_%s/summary_after2.json" % S))
eng = json.load(open("/home/claude/effinger-billing-backend/reports/button/%s.json" % S))
rows = []
HOLD = {"22322": "Pattern 4531 (provider type / 99223+99233) - coding call, William's turn (board row)"}
for b, vs in s["inspector"].items():
    for v in vs:
        errs = "; ".join(e[1][:90] for e in v["errs"])
        act = HOLD.get(str(v["pid"]), "standing hold")
        rows.append(["Claim Inspector", "remaining", "pat%s" % v["pid"], v["vid"], "", "", errs, act])
for r in s.get("unbilled", []):
    rows.append(["Unbilled", "remaining", "pat%s" % r["patientid"], r["id"], "", r.get("carriercode") or "", "; ".join(r.get("_errs", []))[:120], "see needs list"])
ex = collections.Counter()
for run, vs in s["exclusions"].items():
    for v in vs:
        e = v.get("_errs") or [""]
        txt = "; ".join((x.get("name") if isinstance(x, dict) else str(x))[:60] for x in e) if isinstance(e, list) else str(e)[:60]
        ex[(run, v.get("patientid"), v.get("carriercodeshort") or v.get("carriercode"), txt)] += 1
for (run, pid, car, err), n in sorted(ex.items()):
    act = "AET12 carrier master (payer id = TIN) - board row aet12-carrier-cpid, held, not rebilled" if car == "AET12" else "held"
    rows.append(["Exclusions", "remaining x%d" % n, "pat%s" % pid, "run %s" % run, "", car, err, act])
era = eng["summary"]["era"]
rows.append(["ERA", "summary", "", "", "", "", "%s checks / $%.2f before -> %s checks / $%.2f after" % (era["before"]["checks"], era["before"]["unposted"], era["after"]["checks"], era["after"]["unposted"]), "auto-posted $%.2f, manual 0, cleared 0" % eng["summary"]["posted"]["pay"]])
for w in eng.get("waiting", []):
    rows.append(["Waiting", "", "", "", "", "", w[:160], ""])
for e in eng.get("errors", []):
    rows.append(["Errors", "", "", "", "", "", str(e)[:160], ""])
cols = eng["summary"]["columns"]
rows.insert(0, ["Overview", "before -> after", "", "", "", "", "CR %s/%s CI %s/%s UB %s/%s EX %s/%s" % (cols["before"]["charge_review"], cols["after"]["charge_review"], cols["before"]["claim_inspector"], cols["after"]["claim_inspector"], cols["before"]["unbilled"], cols["after"]["unbilled"], cols["before"]["exclusions"], cols["after"]["exclusions"]), eng.get("headline", "")])
out = "_run report 11-09 0139.csv"
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["column", "status", "chart", "visit/run", "dos/cpt", "carrier", "error", "action"]); w.writerows(rows)
print(len(rows), "rows ->", out)
