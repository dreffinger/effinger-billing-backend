#!/usr/bin/env python3
# PLAIN ENGLISH (post-Post-button audit, 1 PM ET 10/21/2026 run 2026-10-21T1710Z - READ ONLY): GitHub slot #128 (17:24-17:31Z) Post-buttoned
#   three remits - Florida Blue 620271529 (check 1053242), Medicare 190603661 (1053243), Florida Blue 423830695 (1053245) - with WOINS $0.
# Decides: nothing. Reads the named charts live (txh.fetch) and prints, for every charge that carries a non-void payment with one of
#   these check numbers, fee / paid / insurance + patient balance / the payment reasons / the write-offs, so the CO-45-on-the-patient
#   defect is visible; for the --visits list it prints every charge of those visits (carrier, billdate, balances) so the PR-22 / PR-177 /
#   CO-97 denial lines can be routed. Output registers/era_audit_<stamp>.json (chart / visit / charge ids + dollars only). No AMD write.
# Usage: python3 era_audit_1021_1710.py --checks 620271529,190603661,423830695 --charts 25994,24154 --visits 19453037,19452861
import json, sys, time, txh, amd
S = "2026-10-21T1710Z"
def arg(k, d=""): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
CHKS = [x for x in arg("--checks").split(",") if x]; CHARTS = [x for x in arg("--charts").split(",") if x]; VIS = set(x for x in arg("--visits").split(",") if x)
amd.login_cached(); out = []; vis = []; tot = 0.0; patflag = []
for pid in CHARTS:
    root = txh.fetch("pat%s" % pid if not str(pid).startswith("pat") else pid)
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        base = {"pid": pid, "vid": c.get("visit"), "cid": c.get("id"), "cpt": c.get("proccode"), "dos": c.get("dos"), "fee": c.get("fee"), "paid": c.get("paid"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "carrier": c.get("carrier"), "billdate": c.get("billdate"), "insorder": c.get("insorder")}
        pays = [p for p in c.iter("payment") if p.get("void") != "1"]
        hits = [p for p in pays if any(k in (p.get("checknumber") or "") for k in CHKS)]
        row = dict(base, pays=[{"amt": p.get("amount"), "car": p.get("carrier"), "date": p.get("date"), "chk": (p.get("checknumber") or "").strip()[:16], "reasons": [(r.get("code") or r.get("reasoncode"), r.get("amount")) for r in p.iter() if r.tag.lower().startswith("payreason") and r is not p]} for p in pays],
                   wos=[(w.get("amount"), (w.get("wocode") or w.get("code") or "").strip(), w.get("date")) for w in c.iter("writeoff") if w.get("void") != "1"])
        if hits:
            tot += sum(float(p.get("amount") or 0) for p in hits)
            if float(row["patbal"] or 0) > 0.004: patflag.append(row)
            out.append(row); print("HIT", json.dumps(row))
        if c.get("visit") in VIS:
            vis.append(row); print("VIS", json.dumps(row))
    time.sleep(0.4)
json.dump({"stamp": S, "checks": CHKS, "hits": out, "visits": vis}, open("registers/era_audit_%s.json" % S, "w"), indent=1)
print("hit lines", len(out), "paid total %.2f" % tot, "| patient balance > 0 on", len(patflag), "lines:", [(r["vid"], r["cpt"], r["patbal"]) for r in patflag])
