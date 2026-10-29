# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 2b, READ-ONLY):
# Resolves AMBIGUOUS (duplicate same-DOB charts) and MISSING feed patients.
#  AMBIGUOUS -> the candidate chart with the most recent non-void charge (ties: most charges) = the live chart.
#  MISSING   -> surname-only lookup; if exactly ONE chart carries the same surname + first 3 letters (DOB differs) it is
#               taken as a DOB mismatch (feed DOB wrong, Jarvis pattern); otherwise stays MISSING (new chart needed).
# Writes feed_match_1028.json back with "resolved" pids. No AMD write.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, re, json, time, collections
import xml.etree.ElementTree as ET
import txh
o = json.load(open(("feed_match_%s.json" % STAMP)))
amd.login_cached()
def activity(pid):
    try:
        root = txh.fetch(pid)
    except Exception as e:
        return ("", 0)
    last = ""; n = 0
    for c in root.iter("charge"):
        if c.attrib.get("void") == "1": continue
        n += 1
        d = c.attrib.get("dos") or c.attrib.get("dateofservice") or ""
        mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", d)
        if mm: last = max(last, mm.group(3) + mm.group(1) + mm.group(2))
    return (last, n)
def amd_dob(d):
    mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", d or "")
    return mm.group(3) + mm.group(1) + mm.group(2) if mm else ""
def search(pattern):
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": pattern, "nocookie": "1"}))
    rows = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    return [(p.get("id"), amd_dob(p.get("dob")), p.get("name", "")) for p in rows]
for k, v in o.items():
    name, dob = k.split("|"); last, _, first = name.partition(","); last = last.strip(); first = first.strip()
    if v["status"] == "AMBIGUOUS":
        acts = {pid: activity(pid) for pid in v["pids"]}
        best = max(acts, key=lambda p: acts[p])
        v["resolved"] = best; v["resolution"] = "most recent charge %s (%d charges)" % acts[best]
        v["candidates"] = {p: {"last_dos": a[0], "charges": a[1]} for p, a in acts.items()}
        print("AMBIG ->", best, v["resolution"], "| others", {p: a for p, a in acts.items() if p != best})
        time.sleep(0.3)
    elif v["status"] == "MISSING":
        hits = search("%s%%" % last.split(" ")[0].replace("'", "%").replace("(", "%"))
        samefirst = [h for h in hits if h[2].upper().replace(" ", "").startswith((last.replace(" ", "") + "," + first[:3]).upper())]
        v["name_hits"] = [{"pid": h[0], "dob": h[1]} for h in samefirst]
        if len(samefirst) == 1:
            v["resolved"] = samefirst[0][0]; v["resolution"] = "DOB MISMATCH feed %s vs chart %s - single same-name chart" % (dob, samefirst[0][1])
            print("MISSING -> DOB mismatch", last[:5] + "*", v["resolution"])
        elif len(samefirst) > 1:
            same_last = {h[1] for h in samefirst}
            v["resolution"] = "several same-name charts, none with this DOB: " + str(v["name_hits"])
            print("MISSING multi", last[:5] + "*", v["resolution"])
        else:
            v["resolution"] = "no chart with this name - NEW CHART NEEDED"
            print("MISSING new", last[:5] + "*", "(%d surname hits)" % len(hits))
        time.sleep(0.3)
    else:
        v["resolved"] = v["pids"][0]
json.dump(o, open(("feed_match_%s.json" % STAMP), "w"), indent=1)
print(collections.Counter(("resolved" in v, v["status"]) for v in o.values()))
