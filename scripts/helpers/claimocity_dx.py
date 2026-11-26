# PLAIN ENGLISH (Claimocity feed ingest - diagnosis-code cache):
# Every ICD-10 code the parsed feed carries (FT1-19, dotted - the DG1-3 copies are the same codes without the dot) must be turned into AMD's numeric dcode id before a charge can be
# written. This fills the shared cache (FEED_DX_CACHE, default dx_cache_feed.json): one lookupdiagcode codeset="10" per code not yet
# cached. A code AMD does not know is cached as null and is looked up AGAIN whenever a later batch carries it (William may have added it
#   to the practice's AMD diagnosis list since - 10/31/2026: M51.17 and M51.86 are valid ICD-10 but were not in the list).
# 11/25/2026 (William, STANDING: "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to be added"; the independent review of
#   that rule): since that day a null in this cache is no longer "the code is left off the charge" - claimocity_import.py puts I10 on the claim IN THE CODE'S PLACE and William's
#   email asks him to add the code. So a null is written ONLY for a real lookup answer: an answer that lists codes, or one that holds no "Fault", no success="0" and holds "<Results" (a lookup with
#   no match returns an empty <Results/> element - docs/captured_calls.md) or AdvancedMD's own envelope "<PPMDResults" (the no-match answer WITH codeset="10" was never recorded
#   word for word; were it the envelope without a Results element, a rule that knew only <Results would stop every ingest that carries a code the list lacks). Any other answer - a fault, an error page, an empty
#   body - does NOT say "not in the list": the code is asked ONCE more after a short pause, and when that is no lookup answer either, the cache is written as it stands WITHOUT that
#   code and this step ends with exit 1 and one plain line that names the code. It is a must-step: the ingest and the retry then stop with 'STEP FAILED: dx' before anything is
#   entered, and the next run asks again. (Before: ONE fault or error page was cached as "not in the list" and the step ended well - under the I10 rule that puts I10 on a claim in
#   the place of a code AdvancedMD's list HAS, and the email asks William for a code he already added.)
#   The same day: I10 ITSELF (DX_INSTEAD below - the code that stands in a missing code's place) is looked up whenever the cache holds no id for it, also when no message of the
#   batch carries it. The import and the retry apply the rule only when the cache holds an id for I10: with a new cache, or one that lacks I10, and a batch that does not carry
#   I10, the rule was switched off without a word (codes left off, 'no usable dx' skips) and the digest gave two reasons of which neither was true.
#   A blank between two ^ is not a code: it is never looked up (it used to be asked as "%", a search for every code of the list - a fault to that search must not stop an ingest).
# Reads: feed_parsed_<STAMP>.json. Writes: the cache only. One AMD login (login_cached), read-only calls. Exit 0 = every code of the batch has its answer in the cache; 1 = see above.
# Usage: FEED_STAMP=<stamp> python3 claimocity_dx.py
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")
import amd, re, json, time, os, sys
DX_INSTEAD = "I10"      # the code that stands in a missing code's place - the same line as in claimocity_import.py and claimocity_retry_dx.py (William 11/25/2026); the self-test holds the three together
parsed = json.load(open("feed_parsed_%s.json" % STAMP))
cache = json.load(open(DXCACHE)) if os.path.exists(DXCACHE) else {}
codes = set()
for m in parsed:
    for c in m.get("FT1", []):
        for code in (c.get("dx") or "").split("^"):
            if code.strip(): codes.add(code.strip())      # 11/25/2026: a blank between two ^ is not a code
feed_n = len(codes); codes.add(DX_INSTEAD)      # 11/25/2026: the rule's own stand-in code must be in this cache, also when no message of the batch carries it (the first line below still counts the FEED's codes)
todo = sorted(c for c in codes if not cache.get(c))   # unknown AND previously-null codes (null = not in AMD's list at the time)
print("dx codes in feed: %d%s, cached: %d, to look up: %d" % (feed_n, (" (and %s, the code that stands in for a code the list lacks)" % DX_INSTEAD) if len(codes) > feed_n else "", len(codes) - len(todo), len(todo)))
def ask(v):
    """one lookupdiagcode for the code as written in v -> (the answer, the codes it lists, whether it IS a lookup answer - the header, 11/25/2026)"""
    r = amd.post(amd.msg("lookupdiagcode", "lookup", {"code": v + "%", "exactmatch": "0", "codeset": "10", "orderby": "code", "page": "1", "nocookie": "1"}, "")) or ""
    hits = re.findall(r'<diagcode id="(dcode\d+)" code="([^"]*)"', r)
    return r, hits, bool(hits) or ("Fault" not in r and 'success="0"' not in r and ("<Results" in r or "<PPMDResults" in r))      # success="0": the registry's other mark of a failed call (docs/captured_calls.md: 'Detect faults on <Fault / success="0"') - never a lookup answer either; AdvancedMD's own envelope without a fault counts beside <Results (the header)
if todo:
    amd.login_cached()
    for code in todo:
        # AMD stores ICD-10 with the dot (I10, E11.9); the feed sometimes sends it without one in DG1-3 (I82401) - try both
        variants = [code]
        if "." not in code and len(code) > 3: variants.append(code[:3] + "." + code[3:])
        found = None
        for v in variants:
            r, hits, real = ask(v)
            if not real: time.sleep(3); r, hits, real = ask(v)      # 11/25/2026: not a lookup answer (a fault, an error page, an empty body) - asked ONCE more after a short pause
            if not real:      # still none: NEVER cached as "not in the list" - a null now puts I10 on the claim in the code's place. The cache as it stands, WITHOUT this code; the step stops; the next run asks again
                cache.pop(code, None); json.dump(cache, open(DXCACHE, "w"), indent=0, sort_keys=True)
                print("dx: %s%s - no lookup answer in two tries, nothing was cached for it; the next run asks again (the answer was %s%s)" % (
                    code, (" (asked as %s)" % v) if v != code else "", "a fault" if "Fault" in r or 'success="0"' in r else "empty" if not r.strip() else "not a lookup answer (no <Results>)",
                    (" - it began: " + re.sub(r"\s+", " ", r).strip()[:120]) if r.strip() else ""))
                sys.exit(1)
            exact = [h for h in hits if h[1].upper() == v.upper()]
            if exact: found = exact[0][0]; break
        cache[code] = found
        time.sleep(0.15)
    json.dump(cache, open(DXCACHE, "w"), indent=0, sort_keys=True)
    print("looked up %d: %d found, %d not in AMD" % (len(todo), sum(1 for c in todo if cache[c]), sum(1 for c in todo if not cache[c])))
