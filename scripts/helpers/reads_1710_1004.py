# PLAIN ENGLISH (1 PM ET 10/4 slot, run 2026-10-04T1710Z): READ-ONLY pass.
# (1) getdemographic on the charts behind the 'Insurance order is missing' Unbilled rows (plans / default insorder) so a plan added
#     since the 11 AM run is caught. (2) 99223 anchor search for the two admission-date holds. (3) ERA step 5(b): GET /api/era/checks
#     (count + dollars) and cache checkdetails for every unposted check. Never touches: AMD writes.
import amd, re, json, time, os, era_post, txh
STAMP = "2026-10-04T1710Z"; amd.login_cached(); out = {"charts": {}, "anchors": {}, "era": {}}
for pid in ["17477898", "17477946", "17477973"]:
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    m = re.search(r'<patient [^>]*>', d); attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    out["charts"][pid] = {"insorder": attrs.get("insorder"), "plans": [{k: p.get(k) for k in ("id","carrier","sequence","begindate","enddate")} for p in plans]}
    print("pat%s insorder=%s plans=%s" % (pid, attrs.get("insorder"), [(p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate")) for p in plans])); time.sleep(0.3)
for pid, vids in {"17477972": ["19456851","19456860","19456879","19456886"], "17472874": ["19437843"]}.items():
    root = txh.fetch(pid); time.sleep(0.3)
    chs = [c for c in root.iter("charge") if c.get("void") != "1"]
    adm = sorted({c.get("dos") for c in chs if (c.get("proccode") or "").startswith("99223")})
    held = sorted({(c.get("visit"), c.get("dos"), c.get("proccode")) for c in chs if c.get("visit") in vids})
    out["anchors"][pid] = {"99223_dates": adm, "held": held}; print("pat%s 99223=%s held=%s" % (pid, adm, held))
chks = era_post.checks(); tot = 0.0; os.makedirs("era_details", exist_ok=True)
print("ERA UNPOSTED CHECKS:", len(chks))
for c in chks:
    print("  ", {k: c.get(k) for k in c if any(s in k.lower() for s in ("id","payer","amount","date","number","unposted","status"))})
    try: tot += float(c.get("unpostedamount") or c.get("checkamount") or 0)
    except: pass
    cid = c.get("id") or c.get("checkid"); p = "era_details/%s.json" % cid
    if cid and not os.path.exists(p): json.dump(era_post.details(cid), open(p, "w"), indent=1); time.sleep(0.3)
print("TOTAL unposted $%.2f" % tot); out["era"] = {"before_count": len(chks), "before_total": round(tot, 2), "checks": chks}
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1, default=str)
