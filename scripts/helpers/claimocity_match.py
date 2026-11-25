# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 2, READ-ONLY):
# For every patient of the batch that the patient map does not know (feed_unknown_<stamp>.json), once per Claimocity id (PID-3): finds
# the AdvancedMD charts that could be that person and notes what speaks for each one. No AMD write.
# THE MATCH STEP ONLY GATHERS: EVERY ENTRY IT WRITES IS UNDECIDED UNTIL claimocity_resolve.py APPLIES THE IDENTITY RULE
# (feed_identity.py - William 11/25/2026, after the feed step twice made a second chart for a patient whose own chart was there under
# the right date). Until then this step chose a chart by an EQUAL date alone, grouped the patients by name and date instead of by
# Claimocity id, and took a lookup AdvancedMD did not answer for "no such chart".
#  1 the patients: one per Claimocity id; two ids under one name and one REAL date are one patient; a name-and-date key that two
#    patients share, or that no Claimocity id carries, is decided for nobody (feed_identity.patients).
#  2 the charts: lookuppatient "LAST, FIR%" as before; "WORD%, FIR%" - every last name that BEGINS with the feed's first word (a
#    suffix only the chart carries, a second word, a hyphen written as a space); and the last name's first word alone (any first name -
#    what the resolve step used to ask). An apostrophe becomes %. When a lookup comes back full (50 charts - AdvancedMD answers no
#    more) it is asked again with four letters of the first name, then with its whole first word; what may still be cut short is
#    written down ("cut"), and the rule then matches nobody by the name alone. Should AdvancedMD not answer the "WORD%, FIR%" form
#    (this step has not always asked it), the step says so once and goes on with "cut" set - it does not stop. Kept: the name
#    candidates (the same last name, the first three letters of the first name) and, for rule 3, the charts of the same last name
#    that carry exactly the feed's real date.
#  3 each kept chart is read ONCE (getdemographic: additionalmrn, ssn, the plans' subscribernum) and weighed against the feed's own
#    Claimocity id, PID-19 and insurance numbers (IN1-49, else IN1-36) from the raw .hl7 files. The numbers stay in memory: the match
#    file gets the chart id, its name and date, and the evidence WORDS (mrn / ssn / member / ssn4, and whether a number contradicts).
#  A lookup or a chart read AdvancedMD does not answer (a fault, a page that is no answer, nothing at all, a row that cannot be read
#  as a chart) is asked once more; not answered again, the step STOPS (exit 1) with nothing decided - the driver stops the ingest and
#  the next run reads the files again. A lookup that answers with no chart at all (an empty result) is an answer: a new patient.
# Writes feed_match_<stamp>.json: every name-and-date key of the batch, each "AMBIGUOUS" with no chart and no chart ids under "pids"
# (never "MISSING", which reads "make a new chart"). Prints Claimocity ids, chart ids and counts - never a name, a date or a number.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, re, json, sys, time, collections, glob, html, datetime
try:
    import feed_identity as FI
except ImportError:      # a workspace that does not hold the rule yet: the repository clone's copy (the bootstrap and the driver's make_current copy the helpers from there)
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("feed_identity", "/home/claude/effinger-billing-backend/scripts/helpers/feed_identity.py"); FI = _iu.module_from_spec(_sp); _sp.loader.exec_module(FI)
SRC = sys.argv[1]
msgs = json.load(open(SRC))
TODAY8 = datetime.date.today().strftime("%Y%m%d")
# ---- the feed's own Social Security and member numbers, from the raw files - in memory only, never written, never printed ---------------
SSN = collections.defaultdict(list); MEMBER = collections.defaultdict(list)
for f in sorted(glob.glob(HL7_DIR + "/*.hl7")):
    cur = None
    for line in open(f, errors="replace").read().replace("\r", "\n").split("\n"):
        s = line.split("|")
        if s[0] == "MSH": cur = None      # a message without a PID line never takes the numbers of the message before it
        elif s[0] == "PID":
            cur = s[3] if len(s) > 3 else None
            if cur and len(s) > 19 and s[19].strip(): SSN[cur].append(s[19])
        elif s[0] == "IN1" and cur:
            num = FI.in1_member(s)
            if num and num not in MEMBER[cur]: MEMBER[cur].append(num)
# ---- the patients: one per Claimocity id (11/25/2026 - until then one per name and date, so one id with two dates was two patients) ----
KEYS = collections.OrderedDict()      # the import's own key (NAME|DOB) -> the Claimocity ids of the messages that carry it
for m in msgs:
    if not isinstance(m, dict) or m.get("pid") is None: continue      # no PID line: nobody's visit - the import passes it over as well
    k = str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8]
    pid = str(m["pid"]) if str(m["pid"]).strip() else ""      # an empty PID-3 is no Claimocity id: it is never written among the ids (the patient map must not learn it)
    if pid not in KEYS.setdefault(k, []): KEYS[k].append(pid)
PATIENTS, UNDECIDED = FI.patients(KEYS, TODAY8, ssn_of=lambda i: SSN.get(i))
amd.login_cached()
def answered(r):
    """An AdvancedMD answer that can be read: its envelope is there and it carries no Fault ELEMENT (the letters in a name are not one)."""
    return isinstance(r, str) and re.search(r"<\s*(?:\w+:)?(?:PPMDResults|Results)\b", r) is not None and re.search(r"<\s*(?:\w+:)?Fault\b", r) is None
def ask(what, who, send, good=answered, must=True):
    """One read, asked twice at most. Not answered: the step stops - a lookup that failed is NOT 'no chart of this name' (that made new charts).
    must=False (the one lookup form this step has not always made): None instead of stopping - the caller then matches nobody by the name alone."""
    why = ""
    for n in (1, 2):
        try:
            r = send()
            if good(r): return r
            why = "a fault or no AdvancedMD answer"
        except Exception as e: why = type(e).__name__
        time.sleep(2)
    if not must: return None
    print("MATCH STOPPED: AdvancedMD did not answer the %s for %s (asked twice: %s). Nothing is decided; no chart is chosen and none is made on a half-read - the next run reads the files again." % (what, who, why))
    sys.exit(1)
def pat(s): return re.sub(r"[^A-Za-z0-9 ,.\-]", "%", s)      # a name as a lookup pattern: an apostrophe (the 9/14 lesson) and anything else that is no letter, digit, space, comma, period or hyphen becomes %
_ATTR = r"[\w:.\-]+\s*=\s*(?:\"[^\"]*\"|'[^']*')"
def elements(tag, r):
    """The attributes of every <tag ...> element of an answer (a name comes with its apostrophe as an XML entity) - None when one of them cannot be
    read: the whole answer then counts as not understood, because a chart silently left out of a lookup is how a second chart gets made."""
    found = re.findall(r"<%s\b((?:\s+%s)*)\s*/?>" % (tag, _ATTR), r)
    if len(found) != len(re.findall(r"<%s\b" % tag, r)): return None
    return [{k: html.unescape(a or b) for k, a, b in re.findall(r"([\w:.\-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", x)} for x in found]
LOOKED = {}; CHART = {}; NOT_TAKEN = []
def rows(pattern, who, must=True):
    if pattern not in LOOKED:
        if not must and NOT_TAKEN: return None
        every = lambda r: answered(r) and elements("patient", r) is not None and all(re.fullmatch(r"pat[0-9]+", p.get("id") or "") for p in elements("patient", r))      # every row is a chart with its id
        r = ask("name lookup", who, lambda: amd.post(amd.msg("lookuppatient", "lookup", {"name": pattern, "nocookie": "1"})), every, must)
        if r is None:
            NOT_TAKEN.append(who); print("MATCH: AdvancedMD did not answer the lookup by the BEGINNING of the last name (asked twice, first for %s) - not asked again in this run. Without it a chart under a longer form of the last name may be missing: the rule matches nobody by the name alone (rules 5 to 8) in this run." % who)
            return None
        LOOKED[pattern] = elements("patient", r); time.sleep(0.25)
    return LOOKED[pattern]
def chart(pid):
    """The chart's own Claimocity id, Social Security number and member numbers - read once, kept in memory only."""
    if pid not in CHART:
        def mine(r):      # this chart's own patient element: the one that carries its number - else, as every other helper takes it, the first one with no id at all
            ps = elements("patient", r) or []; num = re.sub(r"\D", "", pid)
            return next((x for x in ps if re.sub(r"\D", "", x.get("id") or "") == num), None) or next((x for x in ps if not x.get("id")), None)
        r = ask("chart read", pid, lambda: amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}, ""), timeout=60), lambda r: answered(r) and mine(r) is not None)
        a = mine(r)
        CHART[pid] = {"mrn": a.get("additionalmrn") or "", "ssn": a.get("ssn") or "", "members": [x["subscribernum"] for x in elements("insplan", r) or [] if x.get("subscribernum")]}
        time.sleep(0.25)
    return CHART[pid]
def by_name(last, first, who):
    """Every chart AdvancedMD lists for one name of the feed, and how far the list may be cut short: "" = whole; "name" = name candidates may be
    missing but every full-name candidate is there; "full" = full-name candidates may be missing too. Two forms are asked: the last name as the
    feed writes it ("LAST, FIR%" - the lookup this step has always made) and everything that BEGINS with its first word ("WORD%, FIR%": a suffix
    the chart carries and the feed does not, a second word, a hyphen written as a space - docs/captured_calls.md: a two-word or hyphenated last
    name is found by its first word). AdvancedMD answers 50 charts at most, so a full page is asked again with four letters of the first name
    (that list holds every full-name candidate), and a full page of those with the whole first word (to find at least the patient's own chart)."""
    word = re.split(r"[ \-]+", last.strip())[0]; w = pat(first.split()[0]); fir = pat(first)[:3].strip(); found = []; cut = ""
    for part, must in ((pat(last), True), (pat(word) + "%", False)):
        got = rows("%s, %s%%" % (part, fir), who, must)
        if got is None: cut = "full"; continue
        found += got
        if len(got) < 50: continue
        if len(w) < 4: cut = "full"; continue
        got = rows("%s, %s%%" % (part, w[:4]), who, must)
        if got is None: cut = "full"; continue
        found += got; cut = cut or "name"
        if len(got) >= 50: cut = "full"; found += (rows("%s, %s%%" % (part, w), who, must) or []) if len(w) > 4 else []
    return found + rows("%s%%" % pat(word), who), cut      # and the last name's first word alone: any first name (rule 3) - the lookup the resolve step used to make
def waiting(why, **more):      # an entry nobody has decided: no chart, not "MISSING", no chart ids under "pids" (an older resolve step cannot work on it)
    return dict({"status": "AMBIGUOUS", "pids": [], "feed_ids": [], "decided_for": [], "identity_rule": FI.IDENTITY_RULE_VERSION, "lookup": [], "rule": 0, "why": why, "flags": [],
                 "candidates": [], "evidence": [], "feed_dob": "none", "for_william": True, "resolution": why}, **more)
def dated(k): return "real" if FI.real_dob(k.rpartition("|")[2], TODAY8) else "none"
out = collections.OrderedDict(); with_charts = 0
for p in PATIENTS:
    if not p["decide_keys"]: continue
    ids = p["ids"]; who = FI.show_id(ids[0])
    names = sorted({FI.split_name(k.rpartition("|")[0]) for k in p["keys"]}); real = sorted({k.rpartition("|")[2] for k in p["keys"] if dated(k) == "real"})
    feed = {"ids": ids, "ssn": [x for i in ids for x in SSN.get(i, [])], "members": [x for i in ids for x in MEMBER.get(i, [])]}
    found = {}; cut = ""
    for last, first in names:
        if not FI.last_key(last) or not re.search(r"[A-Za-z]", first): continue      # no usable name: nothing to look up (feed_identity.decide says so)
        listed, short = by_name(last, first, who); cut = "full" if "full" in (cut, short) else (cut or short)
        for r in listed:
            kind = FI.name_kind(last, first, *FI.split_name(r.get("name") or ""))
            if kind in ("name", "full") or (kind == "surname" and FI.amd_dob(r.get("dob")) in real): found.setdefault(r["id"], r)
    look = []
    for cid in sorted(found, key=lambda c: (FI.chart_number(c), c)):
        r = found[cid]; c = chart(cid)
        ev, contra = FI.evidence(feed, {"mrn": c["mrn"], "ssn": [r.get("ssn") or "", c["ssn"]], "members": c["members"]})
        look.append({"pid": cid, "name": r.get("name") or "", "dob": FI.amd_dob(r.get("dob")), "ev": ev, "contra": contra})
    for k in p["decide_keys"]:
        out[k] = waiting(FI.WHY_NOT_YET, feed_ids=[i for i in KEYS[k] if i], decided_for=ids, lookup=look, cut=cut, candidates=[c["pid"] for c in look], feed_dob="real" if real else "none")
    with_charts += 1 if look else 0
    print("  %s%s: %d chart(s) to weigh %s%s" % (who, " (+%d more id(s))" % (len(ids) - 1) if len(ids) > 1 else "", len(look), [c["pid"] for c in look], " - AdvancedMD's list of same-name charts may be incomplete (%s)" % cut if cut else ""))
for k in KEYS:      # a key that two patients share, or that no Claimocity id carries: decided for nobody
    if k not in out: out[k] = waiting(UNDECIDED.get(k, FI.WHY_NO_ID), feed_ids=[i for i in KEYS[k] if i], feed_dob=dated(k))
json.dump(out, open(("feed_match_%s.json" % STAMP), "w"), indent=1)
decided = sum(1 for p in PATIENTS if p["decide_keys"])
print("MATCH %d Claimocity patient(s) under %d name-and-date key(s): %d with same-name chart(s) in AdvancedMD (%d chart(s) read, %d lookup(s)), %d with none; %d key(s) that cannot be decided. Nothing is decided here - claimocity_resolve.py applies the identity rule." % (
    decided, len(out), with_charts, len(CHART), len(LOOKED), decided - with_charts, sum(1 for v in out.values() if not v["decided_for"])))
