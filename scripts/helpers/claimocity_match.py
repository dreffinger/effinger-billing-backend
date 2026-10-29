# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 2, READ-ONLY):
# For every patient in the parsed DFT backlog, lookuppatient "LAST, FIR%" and match by DOB.
# Writes feed_match_1028.json (pid per feed patient, or MISSING / AMBIGUOUS). No AMD write.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, re, json, sys, time, collections
SRC = sys.argv[1]
msgs = json.load(open(SRC))
pats = {}
for m in msgs:
    key = (m["name"].upper().strip(), m["dob"][:8])
    pats.setdefault(key, []).append(m["pid"])
amd.login_cached()
out = {}
def amd_dob(d):  # AMD "MM/DD/YYYY" -> YYYYMMDD
    mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", d or "")
    return mm.group(3) + mm.group(1) + mm.group(2) if mm else ""
def search(pattern):
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": pattern, "nocookie": "1"}))
    rows = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    return [(p.get("id"), amd_dob(p.get("dob")), p.get("name", "")) for p in rows]
n = 0
for (name, dob), fids in pats.items():
    last, _, first = name.partition(",")
    last = last.strip(); first = first.strip()
    pat1 = "%s, %s%%" % (last.replace("'", "%"), first[:3])
    hits = search(pat1)
    same_dob = [h for h in hits if h[1] == dob]
    if not same_dob and first:
        hits2 = search("%s%%" % last.replace("'", "%"))  # surname only, any first name
        same_dob = [h for h in hits2 if h[1] == dob]
    if len(same_dob) == 1:
        status = "FOUND"
    elif len(same_dob) > 1:
        status = "AMBIGUOUS"
    else:
        status = "MISSING"
    out[name + "|" + dob] = {"status": status, "pids": [h[0] for h in same_dob], "amd_names": [h[2] for h in same_dob], "feed_ids": fids}
    n += 1
    if n % 25 == 0: print(n, "done", collections.Counter(v["status"] for v in out.values()))
    time.sleep(0.25)
json.dump(out, open(("feed_match_%s.json" % STAMP), "w"), indent=1)
print("TOTAL", len(out), collections.Counter(v["status"] for v in out.values()))
for k, v in out.items():
    if v["status"] != "FOUND":
        print(v["status"], k.split("|")[0][:12] + "*", v["pids"], v["amd_names"][:3])
