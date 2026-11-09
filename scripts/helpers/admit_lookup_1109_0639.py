# PLAIN ENGLISH (pending-admit chart check, 1:39 AM ET 11/9 slot run (fired 06:39Z)): READ-ONLY.
# Decides: nothing. For each name pattern given on the command line it runs lookuppatient (LAST,FIR%) and prints the AMD
#   chart ids + DOBs found, so the run can tell whether the Claimocity feed has created a chart for a Pam admit that had none
#   at the last run. Writes registers/admit_lookup_<stamp>.json (chart ids only, no names). No AMD write of any kind.
# Usage: python3 admit_lookup_1027_1240.py "[name]%" "FLAXLEY,[first]%"
import amd, re, json, sys, time
STAMP = "2026-11-09T0639Z"; amd.login_cached(); out = {"stamp": STAMP, "lookups": []}
for pat in sys.argv[1:]:
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": pat, "nocookie": "1"}))
    rows = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    found = [{"id": p.get("id"), "dob": p.get("dob"), "chart": p.get("chart")} for p in rows]
    print(pat.split(",")[0][:3] + "*:", [(f["id"], f["dob"]) for f in found] or "no chart")
    out["lookups"].append({"pattern_hash": str(abs(hash(pat)) % 10**6), "charts": [f["id"] for f in found]}); time.sleep(0.3)
json.dump(out, open("registers/admit_lookup_%s.json" % STAMP, "w"), indent=1)
