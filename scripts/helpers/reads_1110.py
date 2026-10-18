# PLAIN ENGLISH (7 AM ET 10/18/2026 run 2026-10-18T1110Z): READ-ONLY status reads for the standing holds.
# Decides: nothing. getdemographic plan summary on the three zero-plan HCA charts + the AARP chart; lookuppatient for the
# three Pam admits without a chart; GET /api/era/checks count. Writes registers/admit_lookup_<stamp>.json (chart ids only).
import amd, re, json, sys, time
STAMP = open(".run_stamp").read().strip(); amd.login_cached()
for pid in ["17478059", "17478063", "17478064", "17470713"]:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
    plans = re.findall(r'<insplan [^>]*/?>', r)
    po = re.search(r'<patient [^>]*insorder="([^"]*)"', r)
    print("chart", pid, "insplans", len(plans), "insorder", po.group(1) if po else "?")
    for p in plans:
        a = dict(re.findall(r'(\w+)="([^"]*)"', p))
        print("   ", a.get("id"), a.get("carrier"), a.get("carriercode") or a.get("carriername", "")[:20], "seq", a.get("sequence"), "sub", (a.get("subscribernum") or "")[:3] + "...", "beg", a.get("begindate"), "end", a.get("enddate"))
    time.sleep(0.3)
out = {"stamp": STAMP, "lookups": []}
for pat in sys.argv[1:]:
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": pat, "nocookie": "1"}))
    rows = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    print(pat.split(",")[0][:3] + "*:", [(f.get("id"), f.get("dob")) for f in rows] or "no chart")
    out["lookups"].append({"pattern_hash": str(abs(hash(pat)) % 10**6), "charts": [f.get("id") for f in rows]}); time.sleep(0.3)
json.dump(out, open("registers/admit_lookup_%s.json" % STAMP, "w"), indent=1)
import era_post
ch = era_post.checks()
print("ERA unposted checks:", len(ch), "total", round(sum(float(c.get("checkamount") or c.get("amount") or 0) for c in ch), 2))
for c in ch[:20]: print("  ", {k: c.get(k) for k in list(c.keys())[:8]})
json.dump(ch, open("era_checks_%s_before.json" % STAMP, "w"))
