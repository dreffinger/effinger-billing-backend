# PLAIN ENGLISH (Exclusions column, 7 AM ET 10/15/2026 run 2026-10-15T1110Z) - READ ONLY.
# Decides: nothing. For every open exclusion row of claim runs 1700295 / 1700296 (the 100 Humana / VA CCN payer rejections that
#   appeared after the 10/13 patient-balance re-sends) it reads the visit's LIVE transaction history (gettxhistory) and records,
#   per charge: fee, paid, insurance balance, patient balance, last-billed carrier and billdate, and every non-void payment
#   (amount, check number, carrier). Output registers/excl_read_2026-10-15T1110Z.json + a one-line summary per visit.
# Never touches: AMD writes of any kind.
import amd, txh, json, sys, re
S = "2026-10-15T1110Z"
rows = [l.split() for l in open("scan_2026-10-15/excl_rows_before.txt") if l.startswith(("1700295", "1700296"))]
amd.login_cached()
out = {"stamp": S, "visits": []}
for parts in rows:
    run, claim, pat = parts[0], parts[1], parts[2][3:]
    vid = re.sub(r"[A-Z]$", "", claim)
    root = txh.fetch_visit(pat, vid)
    chs = []
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != vid: continue
        pays = [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip()[:14], p.get("carrier"), p.get("void"), (p.get("date") or p.get("postdate") or "")[:10]) for p in c.iter("payment") if p.get("void") != "1"]
        chs.append({"cid": c.get("id").replace("charge", ""), "cpt": c.get("proccode"), "dos": (c.get("dos") or "")[:10], "fee": float(c.get("fee") or 0),
                    "paid": float(c.get("paid") or 0), "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0),
                    "carrier": c.get("carrier"), "billdate": (c.get("billdate") or "")[:10], "pays": pays})
    out["visits"].append({"run": run, "claim": claim, "pid": pat, "vid": vid, "charges": chs})
    print(run, claim, "pat" + pat, " | ".join("%s %s %s fee %.2f paid %.2f ins %.2f pat %.2f @%s %s pays=%s" % (x["cid"], x["cpt"], x["dos"], x["fee"], x["paid"], x["insbal"], x["patbal"], x["carrier"], x["billdate"], x["pays"]) for x in chs), flush=True)
json.dump(out, open("registers/excl_read_%s.json" % S, "w"), indent=1)
