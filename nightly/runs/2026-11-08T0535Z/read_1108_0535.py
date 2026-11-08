"""Nightly cascade 2026-11-08T0535Z: read live charge detail (visit insorder, dx, fee, balances) for the flagged visits + stay-mates."""
import amd, resave, re, sys
amd.login_cached()
CIDS = {"haywood": ["23373090", "23373007"], "orwell": ["23373077", "23373001"], "pembroke": ["23373081", "23373028"],
        "rathmore": ["23373070", "23373104", "23373105"], "samson": ["23373106", "23372372"]}
for who, cids in CIDS.items():
    for cid in cids:
        x = resave.detail(cid)
        v = re.search(r'<visit ([^>]*)>', x); va = dict(re.findall(r'(\w+)="([^"]*)"', v.group(1))) if v else {}
        print(who, cid, "visit", va.get("id"), va.get("date"), "insorder", va.get("insorder"), "fac", va.get("facility"), "onhcfa", va.get("onhcfa"))
        for m in re.findall(r'<charge ([^>]*)>', x):
            c = dict(re.findall(r'(\w+)="([^"]*)"', m))
            print("    ", {k: c.get(k) for k in ("id", "proccode", "diagcodes", "amount", "insbalance", "patbalance", "insbilled", "carrier", "billdate", "void", "pos", "placeofservice", "units") if k in c})
