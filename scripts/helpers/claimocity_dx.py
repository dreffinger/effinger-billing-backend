# PLAIN ENGLISH (Claimocity feed ingest - diagnosis-code cache):
# Every ICD-10 code the parsed feed carries (FT1-19, dotted - the DG1-3 copies are the same codes without the dot) must be turned into AMD's numeric dcode id before a charge can be
# written. This fills the shared cache (FEED_DX_CACHE, default dx_cache_feed.json): one lookupdiagcode codeset="10" per code not yet
# cached. A code AMD does not know is cached as null and is looked up AGAIN whenever a later batch carries it (William may have added it
#   to the practice's AMD diagnosis list since - 10/31/2026: M51.17 and M51.86 are valid ICD-10 but were not in the list).
# Reads: feed_parsed_<STAMP>.json. Writes: the cache only. One AMD login (login_cached), read-only calls.
# Usage: FEED_STAMP=<stamp> python3 claimocity_dx.py
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")
import amd, re, json, time, os
parsed = json.load(open("feed_parsed_%s.json" % STAMP))
cache = json.load(open(DXCACHE)) if os.path.exists(DXCACHE) else {}
codes = set()
for m in parsed:
    for c in m.get("FT1", []):
        for code in (c.get("dx") or "").split("^"):
            if code: codes.add(code.strip())
todo = sorted(c for c in codes if not cache.get(c))   # unknown AND previously-null codes (null = not in AMD's list at the time)
print("dx codes in feed: %d, cached: %d, to look up: %d" % (len(codes), len(codes) - len(todo), len(todo)))
if todo:
    amd.login_cached()
    for code in todo:
        # AMD stores ICD-10 with the dot (I10, E11.9); the feed sometimes sends it without one in DG1-3 (I82401) - try both
        variants = [code]
        if "." not in code and len(code) > 3: variants.append(code[:3] + "." + code[3:])
        found = None
        for v in variants:
            r = amd.post(amd.msg("lookupdiagcode", "lookup", {"code": v + "%", "exactmatch": "0", "codeset": "10", "orderby": "code", "page": "1", "nocookie": "1"}, ""))
            hits = re.findall(r'<diagcode id="(dcode\d+)" code="([^"]*)"', r)
            exact = [h for h in hits if h[1].upper() == v.upper()]
            if exact: found = exact[0][0]; break
        cache[code] = found
        time.sleep(0.15)
    json.dump(cache, open(DXCACHE, "w"), indent=0, sort_keys=True)
    print("looked up %d: %d found, %d not in AMD" % (len(todo), sum(1 for c in todo if cache[c]), sum(1 for c in todo if not cache[c])))
