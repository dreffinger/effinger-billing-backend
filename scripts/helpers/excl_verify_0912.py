# PLAIN ENGLISH (exclusions balance verification, 9/12/2026)
# Decides: which exclusion rows are completable because the visit's insurance+patient balance is already $0
# (standing prompt: "Complete every exclusion whose visit balance is already $0"). Everything else stays held.
# Rules it uses: gettxhistory per patient (txh.fetch) - read-only here; completion (hideexclusions) is done by the caller only for $0 visits.
# Never touches: AMD writes.
import json, re, sys, time, collections
import txh
summ = json.load(open("scan_0912/summary_before.json"))
excl = summ["exclusions"]
pids = sorted({r.get("patientid") for rows in excl.values() for r in rows if r.get("patientid")})
print("patients:", len(pids))
hist = {}
for pid in pids:
    root = txh.fetch(pid)
    charges = []
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        charges.append(a)
    hist[pid] = charges
    time.sleep(0.3)
def num(x):
    try: return float(x or 0)
    except: return 0.0
out = []
zero = []
for rid, rows in excl.items():
    for r in rows:
        pid = r.get("patientid"); vid = str(r.get("id"))
        chs = [a for a in hist.get(pid, []) if str(a.get("visit")) == vid]
        insbal = sum(num(a.get("insbal") or a.get("insbalance")) for a in chs)
        patbal = sum(num(a.get("patbal") or a.get("patbalance")) for a in chs)
        car = (r.get("carriercode") or "").split()[0] if r.get("carriercode") else ""
        dos = (r["_chgs"][0].get("dos") or r["_chgs"][0].get("begindate") or "")[:10] if r.get("_chgs") else ""
        err = (r["_errs"][0].get("name") or r["_errs"][0].get("text") or "")[:80] if r.get("_errs") else ""
        rec = {"run": rid, "vid": vid, "claimid": r.get("claimid"), "pid": pid, "name": r.get("patientname"), "car": car, "dos": dos,
               "insbal": round(insbal, 2), "patbal": round(patbal, 2), "nchg": len(chs), "err": err}
        out.append(rec)
        if chs and insbal == 0 and patbal == 0: zero.append(rec)
json.dump(out, open("scan_0912/excl_balances_before.json", "w"), indent=1)
print("rows:", len(out), "with $0 visit balance:", len(zero), "rows with no matching charges:", sum(1 for o in out if o["nchg"] == 0))
tot = collections.Counter(); amt = collections.defaultdict(float)
for o in out: tot[(o["car"], o["pid"])] += 1; amt[(o["car"], o["pid"])] += o["insbal"]
for k, v in sorted(tot.items()): print("  %s %s n=%d insbal=$%.2f" % (k[0], k[1], v, amt[k]))
for z in zero: print("ZERO:", z)
