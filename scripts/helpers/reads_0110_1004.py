# PLAIN ENGLISH (9 PM ET 10/3 slot, run 2026-10-04T0110Z): READ-ONLY pass. (1) lookuppatient for the 9/30 Pam admits still without
#   a chart (THORNEY / TRENT / HARLOW) + WILBOURNE/WILBOURNE so a chart created by the Claimocity feed since the last run is noticed.
# (2) getdemographic on every chart behind an 'Insurance order is missing' Unbilled row (plans, default insorder, address line 1) so a
#   plan William or a chat session added since the 5 PM run is caught and the visit can be released this run.
# (3) ERA step 5(b): GET /api/era/checks (count + dollars) and cache checkdetails for every unposted check into era_details/.
# Never touches: AMD writes.
import amd, re, json, time, os, era_post
STAMP = "2026-10-04T0110Z"
amd.login_cached()
out = {"admits": {}, "charts": {}, "era": {}}
for nm in ["WILBOURNE,PATIENT339%", "WILBOURNE,PATIENT339%", "THORNEY,[first]%", "TRENT,[first]%", "HARLOW,[first]%", "HARLOW,[first]%"]:
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
    pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    out["admits"][nm] = [{k: p.get(k) for k in ("id", "chart", "dob")} for p in pats]
    print("lookup", nm, [(p.get("id"), p.get("dob")) for p in pats]); time.sleep(0.3)
pids = ["17477183","17473232","17471681","17477639","17477842","17477850","17477870","17477892","17477898","17477933","17477946"]
for pid in pids:
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    m = re.search(r'<patient [^>]*>', d); attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    addr = re.search(r'<address [^>]*>', d); addr = dict(re.findall(r'(\w+)="([^"]*)"', addr.group(0))) if addr else {}
    out["charts"][pid] = {"insorder": attrs.get("insorder"), "dob": attrs.get("dob"), "addr1": addr.get("address1"),
        "plans": [{k: p.get(k) for k in ("id", "carrier", "sequence", "begindate", "enddate", "subscribernum")} for p in plans]}
    print("pat%s insorder=%s plans=%s addr1=%s" % (pid, attrs.get("insorder"),
          [(p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate")) for p in plans], bool(addr.get("address1"))))
    time.sleep(0.3)
chks = era_post.checks()
print("ERA UNPOSTED CHECKS:", len(chks)); tot = 0.0; os.makedirs("era_details", exist_ok=True)
for c in chks:
    keys = [k for k in c.keys() if any(s in k.lower() for s in ("id", "payer", "amount", "date", "check", "trn", "unposted", "status"))]
    print("  ", {k: c.get(k) for k in keys})
    try: tot += float(c.get("unpostedamount") or c.get("checkamount") or 0)
    except: pass
    cid = c.get("id") or c.get("checkid"); p = "era_details/%s.json" % cid
    if cid and not os.path.exists(p):
        det = era_post.details(cid); json.dump(det, open(p, "w"), indent=1); time.sleep(0.3)
print("TOTAL unposted $%.2f" % tot)
out["era"] = {"before_count": len(chks), "before_total": round(tot, 2), "checks": chks}
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1, default=str)
# (4) 7 PM addendum: the two admission-date holds in batch 127866 (pat17476868 x3, pat17472703 x4) - look for a 99223 within 45 days
#   before each held DOS in the live tx history (a 99223 the Claimocity feed delivered after the 5 PM run would unblock them).
import txh, datetime
HOLDS = {"17476868": ["19456834", "19456835", "19456836"]}
out["anchors"] = {}
for pid, vids in HOLDS.items():
    root = txh.fetch(pid); time.sleep(0.3)
    chs = [c for c in root.iter("charge") if c.get("void") != "1"]
    adm = sorted({c.get("dos") for c in chs if (c.get("proccode") or "").startswith("99223")})
    held = sorted({(c.get("visit"), c.get("dos"), c.get("proccode")) for c in chs if c.get("visit") in vids})
    out["anchors"][pid] = {"99223_dates": adm, "held": held}
    print("pat%s 99223 dates=%s held=%s" % (pid, adm, held))
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1, default=str)
