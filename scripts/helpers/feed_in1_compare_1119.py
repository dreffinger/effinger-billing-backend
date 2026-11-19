# PLAIN ENGLISH (Does the insurance the feed carries reach the chart? - comparison of 11/19/2026) - READ ONLY.
# Decides: Nothing. For every feed patient it takes the insurance blocks the feed carried (adt_ingest.py's reading of every feed
#          file) and the chart's plans in AdvancedMD today, and sorts each block: the import's payer table does not know the name
#          (UNMAPPED), the chart holds that carrier with the same member number (ON CHART), with another number (OTHER NUMBER), or
#          not at all (MISSING). Output: feed_in1_compare_1119.json (workspace only - patient data); the screen shows counts and
#          payer names only.
import amd, json, re, collections, sys, time
amd.login_cached()
src = open("claimocity_newcharts.py").read(); i = src.index("PAYER_MAP = ["); j = src.index("]\n", i) + 1
ns = {}; exec(src[i:j], ns); PAYER_MAP = ns["PAYER_MAP"]
if "--newmap" in sys.argv:
    import feed_payer_map; mapper = feed_payer_map.code
else:
    mapper = lambda name: next((c for pat, c in PAYER_MAP if re.search(pat, (name or "").upper())), None)
CAR = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CAR.items()}
pmap = json.load(open("registers/claimocity_patient_map.json"))
recs = json.load(open("patient_db/adt/feed_all_1119.json"))
feed = collections.defaultdict(dict)
for r in recs:
    fid = r["patient"].get("id")
    for b in r["insurance"]:
        if b["skip"]: continue
        feed[fid][(b["name"], b["member"])] = b
norm = lambda s: re.sub(r"[^A-Z0-9]", "", (s or "").upper())
out = []; cnt = collections.Counter(); unm = collections.Counter(); miss = collections.Counter(); nochart = 0; zero_plan = 0
for fid, blocks in feed.items():
    pid = re.sub(r"\D", "", pmap.get(fid, ""))
    if not pid: nochart += 1; continue
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan [^>]*>', r)]; plans = [p for p in plans if p.get("id")]
    live = [p for p in plans if not p.get("enddate")]
    if not live: zero_plan += 1
    for (name, member), b in blocks.items():
        code = mapper(name)
        if not code or code not in CODE2CAR: k = "UNMAPPED"; unm[name[:38]] += 1
        else:
            same = [p for p in plans if p.get("carrier") == CODE2CAR[code]]
            if any(norm(p.get("subscribernum")) == norm(member) for p in same): k = "ON CHART"
            elif same: k = "OTHER NUMBER"
            else: k = "MISSING"; miss[code] += 1
        cnt[k] += 1; out.append({"pid": pid, "feed_id": fid, "name": name, "member": member, "code": code, "class": k, "live_plans": len(live), "begin": b.get("begin")})
    time.sleep(0.15)
json.dump(out, open("feed_in1_compare_1119%s.json" % ("_new" if "--newmap" in sys.argv else ""), "w"))
print("feed patients with a usable insurance block: %d (no chart in the map: %d); charts with no open plan today: %d" % (len(feed), nochart, zero_plan))
print("blocks:", dict(cnt))
print("MISSING by carrier:", miss.most_common())
print("UNMAPPED payer names:", unm.most_common(60))
charts_missing = {o["pid"] for o in out if o["class"] == "MISSING"}; print("charts with at least one MISSING block: %d" % len(charts_missing))
