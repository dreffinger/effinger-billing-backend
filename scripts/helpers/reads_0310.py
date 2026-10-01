# PLAIN ENGLISH (11 PM ET 9/30 slot, run 2026-10-01T0310Z): READ-ONLY pass before the ERA column and the admit follow-ups.
# Decides: nothing. (1) GET /api/era/checks -> era_checks_before_2026-10-01T0310Z.json with the count and dollar total of the
#   unposted list; caches era_details/<checkid>.json for every check not yet cached. (2) lookuppatient for the four pending admits
#   so a chart created by the Claimocity feed since the last run is noticed. (3) getdemographic on pat17476868: the chart's
#   default insurance order and plan ids (board row asked the routine to verify Medicare-first).
# Never touches: AMD writes.
import amd, era_post, re, json, os, sys, time
STAMP = "2026-10-01T0310Z"
amd.login_cached()
cs = era_post.checks()
json.dump(cs, open("era_checks_before_%s.json" % STAMP, "w"), indent=1)
tot = sum(float(c.get("unpostedamount") or 0) for c in cs)
print("ERA unposted checks:", len(cs), "unposted $%.2f" % tot)
os.makedirs("era_details", exist_ok=True)
for c in cs:
    cid = str(c["id"])
    print("  check", cid, c.get("systemcarriercode"), c.get("paymentnumber"), c.get("depositdate", "")[:10], "paid", c.get("paymentamount"), "unposted", c.get("unpostedamount"))
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
for nm in sys.argv[1:]:
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
    pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    out[nm] = [{k: p.get(k) for k in ("id", "name", "chart", "dob")} for p in pats]
    print("lookup", nm, [(p.get("id"), p.get("dob")) for p in pats]); time.sleep(0.3)
json.dump(out, open("registers/admit_lookup_%s.json" % STAMP, "w"), indent=1)
d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17476868", "nocookie": "1"}))
m = re.search(r'<patient [^>]*>', d); attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
print("pat17476868 insorder=", attrs.get("insorder"), "| plans:", [(dict(re.findall(r'(\w+)="([^"]*)"', x)).get("id"), dict(re.findall(r'(\w+)="([^"]*)"', x)).get("sequence"), dict(re.findall(r'(\w+)="([^"]*)"', x)).get("carrier"), dict(re.findall(r'(\w+)="([^"]*)"', x)).get("enddate")) for x in re.findall(r'<insplan [^>]*/?>', d)])
