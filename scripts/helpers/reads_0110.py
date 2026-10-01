# PLAIN ENGLISH (9 PM ET 9/30 slot, run 2026-10-01T0110Z): READ-ONLY pass before the ERA column and the admit follow-ups.
# Decides: nothing. (1) GET /api/era/checks -> era_checks_before_2026-10-01T0110Z.json with the count and dollar total of the
#   unposted list; caches era_details/<checkid>.json (GET /api/era/checkdetails) for every check not yet cached, wrapped as
#   {"eracheckdetails": [...]} - the shape era_fallback_0913b.py reads. (2) lookuppatient for the four pending admits
#   (Wilbourne / Thorney / Trent / Harlow) so a chart created by the Claimocity feed since the last run is noticed.
# Never touches: AMD writes.
import amd, era_post, re, json, os, sys, time
STAMP = "2026-10-01T0110Z"
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
        if isinstance(det, dict) and "eracheckdetails" in det: wrapped = det
        else: wrapped = {"eracheckdetails": det}
        json.dump(wrapped, open(f, "w"), indent=1); time.sleep(0.3)
    det = json.load(open(f))["eracheckdetails"]
    for cl in det:
        pa = float(cl.get("paymentamount") or 0)
        errs = [e.get("id") for e in (cl.get("errors") or [])]
        print("     claim", cl.get("id"), "visit", cl.get("visitid"), "pat", cl.get("patientid"), "paid", pa, "errs", errs,
              "lines", [(ch.get("procedurecode"), (ch.get("servicedate") or ch.get("dateofservice") or "")[:10], ch.get("paymentamount"), ch.get("insurancebalance")) for ch in (cl.get("charges") or [])][:4])
out = {}
for nm in ("WILBOURNE,PATIENT339%", "THORNEY,[first]%", "TRENT,[first]%", "HARLOW,[first]%"):
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
    pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    out[nm] = [{k: p.get(k) for k in ("id", "name", "chart", "dob")} for p in pats]
    print("lookup", nm, [(p.get("id"), p.get("dob")) for p in pats]); time.sleep(0.3)
json.dump(out, open("registers/admit_lookup_%s.json" % STAMP, "w"), indent=1)
