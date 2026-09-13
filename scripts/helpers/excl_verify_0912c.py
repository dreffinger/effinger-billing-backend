# PLAIN ENGLISH (exclusion balance verify, 9/12/2026 12:50am ET ehpa cloud run)
# Decides: which exclusion rows already sit at a $0 insurance balance (those may be completed) - reads only.
# Rules it uses: gettxhistory per patient; a visit is "settled" when every non-void charge on it has insbal 0.
# Never touches: AMD writes.
import json, txh, time, sys, os
from collections import defaultdict
s = json.load(open("scan_0912/summary_before.json"))
rows = [(rid, r) for rid, rs in s["exclusions"].items() for r in rs]
pids = sorted({r["patientid"] for _, r in rows})
bal = {}
for pid in pids:
    try:
        root = txh.fetch(pid)
    except Exception as e:
        print("txh error", pid, e); continue
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        v = a.get("visit") or a.get("visitid")
        bal.setdefault(v, []).append((a.get("id"), a.get("proccode"), a.get("dos"), float(a.get("insbal") or 0), float(a.get("patbal") or 0), a.get("carrier"), a.get("billdate")))
    time.sleep(0.4)
out = []
zero = []
for rid, r in rows:
    v = r.get("id"); chs = bal.get(v, [])
    ins = sum(x[3] for x in chs); pat = sum(x[4] for x in chs)
    err = (r["_errs"][0].get("name") or r["_errs"][0].get("text") or "")[:80] if r["_errs"] else ""
    out.append({"run": rid, "visit": v, "claimid": r.get("claimid"), "pid": r.get("patientid"), "patient": r.get("patientname"), "carrier": r.get("carriercode"), "dos": (r["_chgs"][0].get("dos") if r["_chgs"] else ""), "insbal": ins, "patbal": pat, "nchg": len(chs), "err": err, "billdate": (chs[0][6] if chs else "")})
    if chs and ins == 0 and pat == 0: zero.append(out[-1])
json.dump(out, open("registers/excl_balances_2026-09-12_1530UTC.json", "w"), indent=1)
print("exclusion rows", len(out), "patients", len(pids), "insbal total %.2f" % sum(o["insbal"] for o in out), "patbal total %.2f" % sum(o["patbal"] for o in out))
print("ZERO-balance rows (candidates to complete):", len(zero))
for z in zero: print("   ", z)
from collections import Counter
c = Counter((o["carrier"], o["pid"]) for o in out)
for k, n in sorted(c.items()): print("  ", n, k, "insbal %.2f" % sum(o["insbal"] for o in out if (o["carrier"], o["pid"]) == k))
