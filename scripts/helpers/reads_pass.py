# PLAIN ENGLISH (generic read-only pass, first used run 2026-10-01T0910Z; replaces the per-run reads_<slot>.py copies):
# Decides: nothing. (1) GET /api/era/checks -> era_checks_before_<stamp>.json with the count and dollar total of the unposted
#   list; caches era_details/<checkid>.json for every check not yet cached and prints each claim line. (2) lookuppatient for
#   every name pattern given on the command line (pending admits) -> registers/admit_lookup_<stamp>.json. (3) optional
#   --insorder <pid> prints that chart's default insurance order and plans. Stamp = $RUN_STAMP or .run_stamp or now.
# Never touches: AMD writes. Reuses the cached token (amd.login_cached()).
import amd, era_post, re, json, os, sys, time, datetime
STAMP = os.environ.get("RUN_STAMP") or (open(".run_stamp").read().strip() if os.path.exists(".run_stamp") else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ"))
args = sys.argv[1:]; pids = []
while "--insorder" in args:
    i = args.index("--insorder"); pids.append(args[i + 1]); del args[i:i + 2]
amd.login_cached()
cs = era_post.checks()
json.dump(cs, open("era_checks_before_%s.json" % STAMP, "w"), indent=1)
tot = sum(float(c.get("unpostedamount") or 0) for c in cs)
print("ERA unposted checks:", len(cs), "unposted $%.2f" % tot)
os.makedirs("era_details", exist_ok=True); os.makedirs("registers", exist_ok=True)
for c in cs:
    cid = str(c["id"])
    print("  check", cid, c.get("systemcarriercode"), c.get("paymentnumber"), (c.get("depositdate") or "")[:10], "paid", c.get("paymentamount"), "unposted", c.get("unpostedamount"))
    f = "era_details/%s.json" % cid
    if not os.path.exists(f):
        det = era_post.details(cid)
        wrapped = det if isinstance(det, dict) and "eracheckdetails" in det else {"eracheckdetails": det}
        json.dump(wrapped, open(f, "w"), indent=1); time.sleep(0.3)
    det = json.load(open(f))["eracheckdetails"]
    for cl in det:
        pa = float(cl.get("paymentamount") or 0)
        errs = [e.get("id") for e in (cl.get("errors") or [])]
        print("     claim", cl.get("id"), "visit", cl.get("visitid"), "pat", cl.get("patientid"), "paid", pa, "errs", errs,
              "lines", [(ch.get("procedurecode"), (ch.get("servicedate") or ch.get("dateofservice") or "")[:10], ch.get("paymentamount"), ch.get("insurancebalance")) for ch in (cl.get("charges") or [])][:4])
out = {}
for nm in args:
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
    pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    out[nm] = [{k: p.get(k) for k in ("id", "name", "chart", "dob")} for p in pats]
    print("lookup", nm, [(p.get("id"), p.get("dob")) for p in pats]); time.sleep(0.3)
if args: json.dump(out, open("registers/admit_lookup_%s.json" % STAMP, "w"), indent=1)
for pid in pids:
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
    m = re.search(r'<patient [^>]*>', d); attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    print("pat%s insorder=" % pid, attrs.get("insorder"), "| plans:", [(p.get("id"), p.get("sequence"), p.get("carrier"), p.get("enddate")) for p in plans])
