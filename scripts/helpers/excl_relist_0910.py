# PLAIN ENGLISH (exclusion re-list + zero-plan chart re-read, 5 AM ET 10/17/2026 run 2026-10-17T0910Z): READ-ONLY.
# Decides: nothing. Re-lists the exclusion rows of claim runs 1700302 and 1700305 (clearinghouse=1 payer=1) right before any
#   action, and re-reads the insurance plan count of the three zero-plan HCA charts and the AARP chart via getdemographic.
#   Writes registers/excl_relist_2026-10-17T0910Z.json (chart ids, visit ids, carrier, error text only). No AMD write.
import amd, re, json, time
STAMP = "2026-10-17T0910Z"; amd.login_cached(); out = {"stamp": STAMP, "runs": {}, "plans": {}}
for run in ("1700302", "1700305"):
    r = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": run, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    vs = re.findall(r'<visit [^>]*>', r)
    rows = []
    for v in vs:
        a = dict(re.findall(r'(\w+)="([^"]*)"', v)); rows.append({"vid": a.get("id"), "claimid": a.get("claimid"), "pid": a.get("patientid"), "carrier": a.get("carriercode"), "dos": a.get("dos") or a.get("begindate")})
    errs = re.findall(r'<error[^>]*>([^<]*)<', r)
    out["runs"][run] = {"rows": rows, "errors": sorted(set(e.strip()[:90] for e in errs))}
    print("run", run, "rows", len(rows), "carriers", sorted(set(x["carrier"] for x in rows)), "charts", sorted(set(x["pid"] for x in rows)), out["runs"][run]["errors"][:3]); time.sleep(0.3)
for pid in ("17478059", "17478063", "17478064", "17470713"):
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}), timeout=60)
    plans = re.findall(r'<insplan [^>]*>', d)
    info = [{k: v for k, v in dict(re.findall(r'(\w+)="([^"]*)"', p)).items() if k in ("id", "carrier", "sequence", "begindate", "enddate", "carriercode", "coverage")} for p in plans]
    io = re.search(r'insorder="([^"]*)"', d)
    out["plans"][pid] = {"n": len(plans), "plans": info, "insorder": io.group(1) if io else None}
    print("chart", pid, "insplans", len(plans), info, "insorder", io.group(1) if io else None); time.sleep(0.3)
json.dump(out, open("registers/excl_relist_%s.json" % STAMP, "w"), indent=1)
