# PLAIN ENGLISH (columns scan, 9/29/2026 7 AM ET slot - ehpa cloud copy)
# Decides: nothing. Reads the Claims Center board (overview + the four list calls) and writes the raw XML + a JSON summary
# so the run can act on the rows and report before/after counts. ONE login via amd.login_cached().
# Never touches: AMD writes.
import amd, re, json, time, sys, os
import xml.etree.ElementTree as ET
OUT = "scan_0929_1110"; os.makedirs(OUT, exist_ok=True)
tag = sys.argv[1] if len(sys.argv) > 1 else "before"
amd.login_cached()

def save(name, txt):
    open(os.path.join(OUT, "%s_%s.xml" % (name, tag)), "w").write(txt)

summary = {"tag": tag, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

# 1. overview
ov = amd.post(amd.msg("getclaimcenteroverview", "claimsreports", {"nocookie": "1"}), timeout=120); save("overview", ov)
ova = dict(re.findall(r'(\w+)="([^"]*)"', (re.search(r'<Results[^>]*>', ov) or re.search(r'<[a-zA-Z]+ [^>]*count[^>]*>', ov) or [""])[0] if isinstance(re.search(r'<Results[^>]*>', ov), re.Match) else ""))
if not ova:
    ova = {k: v for k, v in re.findall(r'(\w*count\w*|\w*amount\w*)="([^"]*)"', ov)}
summary["overview"] = ova
print("OVERVIEW:", {k: v for k, v in ova.items() if "count" in k or "amount" in k}, flush=True)

# 2. charge review
cr = amd.post(amd.msg("getreviewcharges", "chargeentry", {"nocookie": "1"}), timeout=120); save("chargereview", cr)
crv = []
try:
    root = ET.fromstring(cr)
    for v in root.iter("visit"):
        crv.append({"vid": v.get("id"), "pid": v.get("patientid") or "", "name": v.get("patientname") or "",
                    "charges": [(c.get("id"), c.get("proccode"), c.get("modcodes") or "", c.get("begindate") or c.get("dos") or "") for c in v.iter("charge")]})
except ET.ParseError as e:
    print("chargereview parse error:", e, cr[:300])
summary["chargereview"] = crv
print("CHARGE REVIEW visits:", len(crv), flush=True)
for v in crv: print("  ", v["pid"], v["name"], v["charges"])

# 3. inspector
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); save("inspbatches", ib)
bids = re.findall(r'<batch id="([^"]+)"', ib)
print("INSPECTOR batches:", len(bids), bids[:20], flush=True)
insp = {}
for bid in bids:
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120); save("insp_%s" % bid, t)
    vs = []
    try:
        root = ET.fromstring(t)
        for v in root.iter("visit"):
            errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:200], e.get("number") or "") for e in v.iter("error")]
            vs.append({"vid": v.get("id"), "pid": v.get("patientid") or "", "name": v.get("patientname") or "", "status": v.get("claimstatus") or "",
                       "errs": errs, "chgs": [(c.get("id"), c.get("proccode")) for c in v.iter("charge")]})
    except ET.ParseError as e:
        print("insp parse error", bid, e)
    if vs: insp[bid] = vs
    time.sleep(0.3)
summary["inspector"] = insp
n = sum(len(v) for v in insp.values()); print("INSPECTOR visits with rows:", n, flush=True)
for bid, vs in insp.items():
    for v in vs: print("  b%s v%s %s %s %s errs=%s" % (bid, v["vid"], v["pid"], v["name"], v["status"], [(p, x[:70]) for p, x, nnum in v["errs"]]))

# 4. unbilled
ub = amd.post(amd.msg("getclaimunbillablecharges", "claimsreports", {"lowdate": "", "highdate": "", "carrier": "", "provider": "", "nocookie": "1"}), timeout=300); save("unbilled", ub)
ubrows = []
try:
    root = ET.fromstring(ub); res = root.find(".//Results")
    summary["unbilled_totalcount"] = res.get("totalcount") if res is not None else None
    summary["unbilled_totalamount"] = res.get("totalamount") if res is not None else None
    for v in root.iter("visit"):
        row = {k: v.get(k) for k in v.keys()}
        row["_errs"] = [e.get("name") or (e.text or "") for e in v.iter("error")]
        row["_chgs"] = [{k: c.get(k) for k in c.keys()} for c in v.iter("charge")]
        ubrows.append(row)
except ET.ParseError as e:
    print("unbilled parse error", e, ub[:300])
summary["unbilled"] = ubrows
print("UNBILLED totalcount:", summary.get("unbilled_totalcount"), "rows:", len(ubrows), flush=True)
for r in ubrows: print("  ", r.get("id"), r.get("patientid"), r.get("patientname"), r.get("carriercode"), r["_errs"][:2])

# 5. exclusions
rs = amd.post(amd.msg("getclaimrunstatus", "claimsreports", {"nocookie": "1"}), timeout=120); save("runstatus", rs)
runs = [dict(re.findall(r'(\w+)="([^"]*)"', cr_)) for cr_ in re.findall(r'<claimrun [^>]*>', rs)]
exruns = [a for a in runs if int(a.get("totalexclusions") or 0) > 0]
print("EXCLUSION runs with exclusions:", [(a["id"], a.get("totalexclusions")) for a in exruns], flush=True)
excl = {}
for a in exruns:
    x = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": a["id"], "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120); save("excl_%s" % a["id"], x)
    rows = []
    try:
        root = ET.fromstring(x)
        for v in root.iter("visit"):
            row = {k: v.get(k) for k in v.keys()}
            row["_errs"] = [{k: e.get(k) for k in e.keys()} | ({"text": (e.text or "").strip()} if (e.text or "").strip() else {}) for e in v.iter("error")]
            row["_chgs"] = [{k: c.get(k) for k in c.keys()} for c in v.iter("charge")]
            rows.append(row)
    except ET.ParseError as e:
        print("excl parse error", a["id"], e)
    excl[a["id"]] = rows
    time.sleep(0.3)
summary["exclusions"] = excl
print("EXCLUSIONS total rows:", sum(len(r) for r in excl.values()), flush=True)
from collections import Counter
c = Counter()
for rid, rows in excl.items():
    for r in rows:
        car = (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "?"
        err = " | ".join((e.get("name") or e.get("text") or "")[:60] for e in r["_errs"][:1])
        c[(car, r.get("patientid"), err)] += 1
for k, v in sorted(c.items(), key=lambda kv: -kv[1]): print("  %2d %s %s %s" % (v, k[0], k[1], k[2]))
json.dump(summary, open(os.path.join(OUT, "summary_%s.json" % tag), "w"), indent=1, default=str)
print("saved", OUT, tag)
