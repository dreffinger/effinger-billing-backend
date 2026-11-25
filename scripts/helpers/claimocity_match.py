# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 2, READ-ONLY):
# For every patient of the batch that the patient map does not know (feed_unknown_<stamp>.json), once per Claimocity id (PID-3): finds
# the AdvancedMD charts that could be that person and notes what speaks for each one. No AMD write.
# THE MATCH STEP ONLY GATHERS: EVERY ENTRY IT WRITES IS UNDECIDED UNTIL claimocity_resolve.py APPLIES THE IDENTITY RULE
# (feed_identity.py - William 11/25/2026, after the feed step twice made a second chart for a patient whose own chart was there under
# the right date). Until then this step chose a chart by an EQUAL date alone, grouped the patients by name and date instead of by
# Claimocity id, and took a lookup AdvancedMD did not answer for "no such chart".
#  1 the patients: one per Claimocity id; two ids under one name and one REAL date are one patient. A name-and-date key that two
#    patients share (one name, no birth date) can carry only ONE chart: each of them is weighed here like any other patient, and
#    what was gathered for each is written under that key ("sharers") - claimocity_resolve.py gives the key a chart only when the
#    rule gives every one of them the same chart (11/25/2026, review of the identity rule: until then nothing was looked up for
#    them and neither visit was entered). A key that no Claimocity id carries, or whose ids the feed itself shows to be two people,
#    is decided for nobody (feed_identity.patients).
#  2 the charts (by_name), three lookups for each name of the feed: "LAST, FIR%" as before; the last name under ANY first name
#    ("LAST%" - its words with a % for whatever stands between them: a suffix only the chart carries, a second word, a hyphen
#    written as a space, and the charts of rule 3); and the LETTERS of the last name with a % between them - every chart the rule
#    calls the same last name, whatever it writes between the letters (11/25/2026, review of the identity rule: the rule compares
#    last names by their letters, so the lookups must - a chart with an apostrophe, a space, a period or a hyphen the feed does NOT
#    have was never listed, and a namesake's chart was taken by the name alone, or a second chart made, without a word). When a
#    lookup comes back full (50 charts - AdvancedMD answers no more) it is asked again with the first name: three letters, four,
#    the whole first word; what may still be cut short is written down ("cut": for other first names only / for name candidates /
#    for full-name candidates too), and the rule then matches nobody by the name alone where the list it needs may be cut.
#    AdvancedMD has not been asked the letters form before, nor a % for a space or a hyphen, nor a % before the comma: these are
#    lookups the step can do WITHOUT. Not answered (asked twice, a minute each at most - or answered with a full page of charts that
#    do not answer to the lookup, or without a chart the other lookups have just listed), the step says so and goes on with the two
#    lookups it has always made - it does not stop, and no rule is switched off for it (11/25/2026, review of the identity rule:
#    until then one such lookup, unanswered twice, cost every later patient of the run the rules 5 to 8 - the patients of 11/8 and
#    11/17 each got a second chart again). The letters form unanswered twice in a row is not asked again in that run. A patient
#    weighed without it is marked ("every_spelling": false): for that patient a chart that writes the last name another way than
#    the feed is not seen - as none was before 11/25/2026. When AdvancedMD did answer the lookup for another patient of the run,
#    a NEW chart made for such a patient is flagged, for William ("cut": "spelling"); in a run in which it never answers nothing
#    is flagged (every new patient would be).
#    Kept: the name candidates (the same last name, the first three letters of the first name) and, for rule 3, the charts of the
#    same last name that carry exactly the feed's real date.
#  3 each kept chart is read ONCE (getdemographic: additionalmrn, ssn, the plans' subscribernum) and weighed against the feed's own
#    Claimocity id, PID-19 and insurance numbers (IN1-49, else IN1-36) from the raw .hl7 files. The numbers stay in memory: the match
#    file gets the chart id, its name and date, and the evidence WORDS (mrn / ssn / member / ssn4, and whether a number contradicts).
#  One of the two lookups the step has always made, or a chart read, that AdvancedMD does not answer (a fault, a page that is no
#  answer, nothing at all, a row that cannot be read as a chart) is asked once more; not answered again, the step STOPS (exit 1) with
#  nothing decided - the driver stops the ingest and the next run reads the files again. A lookup that answers with no chart at all
#  (an empty result) is an answer: a new patient.
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
    must=False (a lookup form this step has not always made): None instead of stopping - the caller then goes on with the forms it has always made."""
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
PAGE = 50                                   # AdvancedMD answers 50 charts at most to one lookup: a page of 50 may be cut short
CUTS = ("", "first", "spelling", "name", "full")      # how far a list of same-name charts may fall short, each worse than the one before (feed_identity._one)
def worse(a, b): return a if CUTS.index(a) >= CUTS.index(b) else b
LOOKED = {}; CHART = {}; SPELL = {"missed": 0, "off": False, "answered": 0}
def rows(pattern, who, must=True):
    """The charts AdvancedMD lists for one lookup (each asked once in a run). must=False - a form this step has not always asked: None when AdvancedMD
    does not answer it (asked twice, a minute each at most) - or answers it with a FULL page of which not even half the charts answer to the lookup
    (it did not make the search it was asked for: such a page is no list of same-name charts, and it is not taken for one that is cut short)."""
    if pattern not in LOOKED:
        every = lambda r: answered(r) and elements("patient", r) is not None and all(re.fullmatch(r"pat[0-9]+", p.get("id") or "") for p in elements("patient", r))      # every row is a chart with its id
        r = ask("name lookup", who, lambda: amd.post(amd.msg("lookuppatient", "lookup", {"name": pattern, "nocookie": "1"}), **({} if must else {"timeout": 60})), every, must)
        if r is None: return None
        got = elements("patient", r)
        if not must and len(got) >= PAGE and 2 * sum(1 for x in got if FI.answers_to(pattern, x.get("name") or "")) < len(got): return None
        LOOKED[pattern] = got; time.sleep(0.25)
    return LOOKED[pattern]
def narrow(part, three, four, word, who, must=True):
    """"PART, FIR%" - and, while a page comes back full, the same with four letters of the first name (that list holds every full-name candidate), then
    with its whole first word (to find at least the patient's own chart). -> (the charts, how far the list may be cut short: "" / "name" / "full");
    None when AdvancedMD did not answer a form the step can do without (must=False)."""
    got = rows("%s, %s%%" % (part, three), who, must)
    if got is None: return None
    if len(got) < PAGE: return list(got), ""
    if not four: return list(got), "full"      # a first name of fewer than four letters cannot be asked for more narrowly
    more = rows("%s, %s%%" % (part, four), who, must)
    if more is None: return None
    if len(more) < PAGE: return got + more, "name"
    return got + more + ((rows("%s, %s%%" % (part, word), who, must) or []) if word else []), "full"
def every_spelling(pattern, who, listed):
    """The lookup with a % between the LETTERS of the last name, any first name: it lists a chart whatever that chart writes between them (11/25/2026,
    review of the identity rule - see by_name). A form this step has not always asked, so the step can do without it: None when AdvancedMD does not
    answer it - or answers it without a chart of the same last name that the lookups before it have just listed (then it is not the search it is
    taken for). Said every time; unanswered twice in a row, it is not asked again in this run (each ask may wait a minute)."""
    if SPELL["off"]: return None
    got = rows(pattern, who, False); said = "MATCH: AdvancedMD did not answer the lookup by every spelling of the last name for %s (asked twice - or it answered a page of other charts)" % who
    if got is not None and len(got) < PAGE and not listed <= {r["id"] for r in got}:
        got = None; said = "MATCH: AdvancedMD's answer to the lookup by every spelling of the last name for %s left out a chart the plain lookups had just listed - it is not used" % who
    if got is not None: SPELL["missed"] = 0; SPELL["answered"] += 1; return got
    SPELL["missed"] += 1; SPELL["off"] = SPELL["missed"] >= 2
    print(said + ": this patient is weighed with the lookups this step has always made - a chart that writes the last name another way than the feed (an apostrophe, a space, a period or a hyphen the feed does not have) is not seen."
          + (" The second time in a row: not asked again in this run." if SPELL["off"] else ""))
    return None
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
    """Every chart AdvancedMD lists for one name of the feed -> (the charts, how far the list may be cut short, whether every spelling was asked for).
    Cut short: "" = whole; "first" = only charts under ANOTHER first name may be missing (rule 3); "name" = name candidates may be missing but
    every full-name candidate is there; "full" = full-name candidates may be missing too. The lookups (feed_identity.lookup_forms has the forms):
      1 "LAST, FIR%" - the last name as the feed writes it: the lookup this step has always made. The step stops without it.
      2 the WORDS of the last name with a % for whatever stands between them, any first name: the chart whatever it writes where the FEED has an
        apostrophe, a space, a period or a hyphen, and any longer form (a suffix, a second name). For a last name of one word this is "LAST%",
        the search these steps have always made - the step stops without it. With a % between two words it is a form AdvancedMD has not been
        asked before for a space or a hyphen: not answered, the two searches the steps have always made are made instead - the last name as
        the feed writes it ("LAST%") and its first word ("WORD%": a hyphen written as a space, a second name). The step stops without those.
      3 the LETTERS of the last name with a % between them, any first name: every chart the identity rule calls the same last name, whatever it
        writes between the letters and after them (11/25/2026, review of the identity rule: the rule compares last names by their letters, the
        lookups did not - a chart with an apostrophe, a space, a period or a hyphen the feed does NOT have was never listed, and a namesake's chart
        was taken by the name alone, or a second chart made, without a word). When this page is not full NOTHING can be missing. A full page is
        asked again with the first name (three letters, four, the whole first word) - that brings the name candidates of every spelling; a chart
        of rule 3 (ANOTHER first name) that also writes the last name another way than the feed is listed on this page only, and beyond a full
        page it is not seen (not marked: the mark would flag every new patient of a short last name). AdvancedMD has not been asked this form
        before (ONE % inside a last name it takes - docs/captured_calls.md, the lookup lesson of 9/14/2026), so the step can do without it:
        every_spelling.
      4 only when 3 did not bring the name candidates and page 2 came back full: the same search with the first name ("WORDS%, FIR%") - the name
        candidates under a longer form of the last name (a form with a % before the comma: not asked before either).
    11/25/2026 (review of the identity rule): a lookup the step can do without (3, 4) that AdvancedMD does not answer never switches a rule off by
    itself. Until then one such lookup, unanswered twice, set "full" for every patient after it in the run: rules 5 to 8 were not asked, and the
    patients of 11/8 and 11/17 each got a second chart again. Now the list counts as cut short only where a page of it really came back full and
    no narrower lookup was answered; without lookup 3 the step sees what it has always seen (1 and 2) - no less."""
    f = FI.lookup_forms(last, first); w = pat(first.split()[0]); own = (pat(first)[:3].strip(), w[:4] if len(w) >= 4 else None, w if len(w) > 4 else "")      # own: the first name as the feed writes it - three letters, four, the whole first word
    found, cut = narrow(pat(last), *own, who)                                                                                              # 1
    part = f["words"] + "%"; base = rows(part, who, "%" not in f["words"])                                                                 # 2
    if base is None:      # not answered with a % between the words: the two searches these steps have always made instead - the last name as the feed writes it, and its first word (a hyphen written as a space, a second name)
        part = pat(re.split(r"[ \-]+", last.strip())[0]) + "%"; found = found + rows(pat(last) + "%", who); base = rows(part, who)
    found = found + base
    same = {r["id"] for r in found if FI.name_kind(last, first, *FI.split_name(r.get("name") or ""))}                                      # every chart listed so far that the rule calls the same last name
    every = every_spelling(f["letters"] + "%", who, same) if len(f["letters"].replace("%", "")) > 1 else None                             # 3 (a last name of one plain letter has no letters to put a % between)
    if every is not None and len(every) < PAGE: return found + every, "", True                                                             # the whole list
    spelt = narrow(f["letters"] + "%", f["first3"], f["first4"], f["first_word"], who, False) if every is not None else None
    found += every or []
    if spelt is not None: found += spelt[0]; cut = worse(cut, spelt[1])
    elif len(base) >= PAGE:
        begins = narrow(part, *own, who, False)                                                                                            # 4
        if begins is None: cut = "full"            # a full page and no narrower lookup: name candidates under a longer form of the last name may be missing
        else: found += begins[0]; cut = worse(cut, begins[1])
    if len(base) >= PAGE: cut = worse(cut, "first")      # (until 11/25/2026 nobody looked whether this page was full: a chart of rule 3 beyond it was missed without a word)
    return found, cut, spelt is not None
def waiting(why, **more):      # an entry nobody has decided: no chart, not "MISSING", no chart ids under "pids" (an older resolve step cannot work on it)
    return dict({"status": "AMBIGUOUS", "pids": [], "feed_ids": [], "decided_for": [], "identity_rule": FI.IDENTITY_RULE_VERSION, "lookup": [], "rule": 0, "why": why, "flags": [],
                 "candidates": [], "evidence": [], "feed_dob": "none", "for_william": True, "resolution": why}, **more)
def dated(k): return "real" if FI.real_dob(k.rpartition("|")[2], TODAY8) else "none"
out = collections.OrderedDict(); with_charts = 0; weighed = 0; plain = []
for p in PATIENTS:
    if not p["decide_keys"] and not p["shared_keys"]: continue      # (11/25/2026: a patient that comes only under a key it shares is weighed like any other - until then it was passed over here)
    ids = p["ids"]; who = FI.show_id(ids[0])
    names = sorted({FI.split_name(k.rpartition("|")[0]) for k in p["keys"]}); real = sorted({k.rpartition("|")[2] for k in p["keys"] if dated(k) == "real"})
    feed = {"ids": ids, "ssn": [x for i in ids for x in SSN.get(i, [])], "members": [x for i in ids for x in MEMBER.get(i, [])]}
    found = {}; cut = ""; spelt = []
    for last, first in names:
        if not FI.last_key(last) or not re.search(r"[A-Za-z]", first): continue      # no usable name: nothing to look up (feed_identity.decide says so)
        listed, short, every = by_name(last, first, who); cut = worse(cut, short); spelt.append(every)
        for r in listed:
            kind = FI.name_kind(last, first, *FI.split_name(r.get("name") or ""))
            if kind in ("name", "full") or (kind == "surname" and FI.amd_dob(r.get("dob")) in real): found.setdefault(r["id"], r)
    look = []
    for cid in sorted(found, key=lambda c: (FI.chart_number(c), c)):
        r = found[cid]; c = chart(cid)
        ev, contra = FI.evidence(feed, {"mrn": c["mrn"], "ssn": [r.get("ssn") or "", c["ssn"]], "members": c["members"]})
        look.append({"pid": cid, "name": r.get("name") or "", "dob": FI.amd_dob(r.get("dob")), "ev": ev, "contra": contra})
    gathered = {"lookup": look, "cut": cut, "every_spelling": bool(spelt) and all(spelt)}      # every_spelling False: this patient was weighed with the lookups the step has always made only
    mine = []      # where what was gathered for this patient is written: under its own keys, and among the "sharers" of a key it shares
    for k in p["decide_keys"]:
        out[k] = waiting(FI.WHY_NOT_YET, feed_ids=[i for i in KEYS[k] if i], decided_for=ids, candidates=[c["pid"] for c in look], feed_dob="real" if real else "none", **gathered); mine.append(out[k])
    for k in p["shared_keys"]:      # a key several patients share: what was gathered for EACH of them, under the key - claimocity_resolve.py decides each and writes a chart only when they all get the same one
        e = out.setdefault(k, waiting(FI.WHY_NOT_YET, feed_ids=[i for i in KEYS[k] if i], feed_dob=dated(k), sharers=[]))
        e["sharers"].append(dict({"ids": ids}, **gathered)); mine.append(e["sharers"][-1]); e["candidates"] = sorted(set(e["candidates"]) | {c["pid"] for c in look}, key=lambda c: (FI.chart_number(c), c))
    weighed += 1; with_charts += 1 if look else 0; plain += [mine] if spelt and not gathered["every_spelling"] else []
    print("  %s%s: %d chart(s) to weigh %s%s%s" % (who, " (+%d more id(s))" % (len(ids) - 1) if len(ids) > 1 else "", len(look), [c["pid"] for c in look], " - AdvancedMD's list of same-name charts may be incomplete (%s)" % cut if cut else "",
                                                 "" if gathered["every_spelling"] or not spelt else " - weighed WITHOUT the lookup by every spelling of the last name"))
# 11/25/2026 (review of the identity rule): a patient weighed WITHOUT the every-spelling lookup in a run in which AdvancedMD did answer that lookup
# for another patient: its list may lack a chart that the lookup would have brought ("spelling"). No rule is switched off for it - a lookup that
# went unanswered never costs a chart by itself - but a NEW chart made on such a list is flagged, for William (feed_identity._one). In a run in
# which AdvancedMD never answers that lookup nothing is marked: every new patient would be flagged, for a lookup this AdvancedMD does not have.
if SPELL["answered"]:
    for mine in plain:
        for e in mine: e["cut"] = worse(e["cut"], "spelling")
for k in KEYS:      # a key that no Claimocity id carries, or that several share who cannot be decided together (feed_identity.patients): decided for nobody
    if k not in out: out[k] = waiting(UNDECIDED.get(k, FI.WHY_NO_ID), feed_ids=[i for i in KEYS[k] if i], feed_dob=dated(k))
json.dump(out, open(("feed_match_%s.json" % STAMP), "w"), indent=1)
print("MATCH %d Claimocity patient(s) under %d name-and-date key(s): %d with same-name chart(s) in AdvancedMD (%d chart(s) read, %d lookup(s)), %d with none; %d key(s) several patients share, %d key(s) that cannot be decided%s. Nothing is decided here - claimocity_resolve.py applies the identity rule." % (
    weighed, len(out), with_charts, len(CHART), len(LOOKED), weighed - with_charts, sum(1 for v in out.values() if v.get("sharers")), sum(1 for v in out.values() if not v["decided_for"] and not v.get("sharers")),
    "; %d patient(s) weighed WITHOUT the lookup by every spelling of the last name - with the lookups this step has always made%s" % (len(plain), " (a new chart made for one of them is flagged for William: AdvancedMD does answer that lookup)" if SPELL["answered"] else "") if plain else ""))
