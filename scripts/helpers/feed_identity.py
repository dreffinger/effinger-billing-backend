# PLAIN ENGLISH (Feed patient identity: the right chart, never a second one - William 11/25/2026)
# Decides: for ONE patient of the Claimocity feed that the patient map does not know yet, which AdvancedMD chart is that person - or that
#   a new chart is needed - or that nobody can say (then no chart is chosen and none is made: it goes to William). William 11/25/2026:
#   "correct every one that comes to the correct date of birth and insurance and fix them figure our how to do this for other charts
#   that have the same mistake where we know the correct dob but claimocity sends the wrong one or the 01011900 default date". What
#   happened: the feed sent a patient with a WRONG birth date (one digit off; the placeholder) although AdvancedMD held that patient's
#   chart under the right one, and the feed step made a SECOND chart (11/8 and 11/17/2026). His earlier word, 11/9/2026: "if a
#   duplicate chart shows up with visits in it just put the visits in the proper chart".
# Rules it uses (decide() works them once per Claimocity id; the first rule that fits wins):
#   words - a birth date is REAL when it is eight digits, a day of the calendar, year 1901 or later, not after today and not more than
#     120 years ago; anything else (empty, the placeholder, zeros, a day that does not exist) is NO BIRTH DATE. A SLIP between two real
#     dates is exactly one of: one digit differs, two neighbouring digits swapped, month and day swapped, one day apart; anything else
#     is FAR. Last names are compared in upper case, letters only, without a trailing JR / SR / II / III / IV / V. A chart is a NAME
#     CANDIDATE when the last name is the same and the first name shares its first three letters; a FULL-NAME candidate when in
#     addition the first word of the first name is the same, or the shorter of the two has four letters or more and begins the longer
#     one (MARY / MARYANN).
#   evidence that two records are one person, strongest first - mrn: the chart's additional number is this Claimocity id; ssn: nine
#     digits on both sides, equal, never a junk value (all one digit, one to nine in a row, starting 000 / 666 / 9); member: a member
#     number of the feed's insurance rows equals a subscriber number of one of the chart's plans (letters and digits only, a leading
#     three-letter prefix dropped from either side, eight characters or more); ssn4: a side shows only four digits and the last four
#     are equal - the weakest. A Social Security number that DIFFERS (nine digits on both sides - or the last four, where a side shows
#     only four) is proof of two people: such a chart is never chosen by name, slip or birth date, and neither is another chart of the
#     group it stands in (it may be that other person's duplicate; a member number the two share proves nothing) - only rule 1 still
#     wins.
#   1 a name candidate carries this Claimocity id -> that chart.
#   2 real date, name candidates carry exactly that date -> the live one of them.
#   3 real date, no name candidate carries it, charts of the same last name under ANOTHER first name do -> the live one; "first name differs".
#   4 ssn / member / ssn4 points to name candidates -> the live chart of the strongest evidence; "birth date differs: ..." unless equal.
#   5 real date, full-name candidates carry ONE date that is a slip from it -> the live one; "birth date differs: <the kind of slip>".
#   6 real date, the only name candidates are full-name candidates with no real date -> the live one; "chart has no birth date".
#   7 no birth date from the feed, the full-name candidates with a real date all carry ONE date -> the live one; "no birth date from Claimocity".
#   8 no birth date from the feed, no full-name candidate has a real one -> the live one; "no birth date on either side".
#   9 anything else -> NEW CHART (when name candidates stood beside it: "same-name charts not used", for William).
#   0 not decided (a chart that could not be read; two dates or two spellings that point to two charts; no name; no Claimocity id; a
#     name-and-date key that several Claimocity ids share without a real date to tie them - unless the rule gives every one of them,
#     each weighed on its own, the SAME chart: shared_answer; and the cases of RULES WITHOUT PROOF below): no chart is chosen and none
#     is made - William.
#   RULES WITHOUT PROOF (11/25/2026, the independent verification of this rule: such a rule could put a visit on ANOTHER person's
#   chart). Rules 1 to 4 choose by what a chart itself shows - the Claimocity id, the same date, a number. Rules 5 to 8 choose by what
#   the same-name charts LOOK LIKE ("ONE date", "the only name candidates", "no date"), and rules 6, 7 and 8 have nothing but the name:
#     a) THE WAIT. While the same batch makes a new chart for another Claimocity id of this last name - a name candidate, or rule 3's
#        relation: another first name under one real date (related) - the charts an answer by rules 5 to 8 rests on are about to
#        change. Such a patient gets no chart in that run, its file is read again, and the next run weighs it against every chart of
#        the batch (until then: of three new ids of one name the one without a date went, by rule 7, on the chart of whichever dated
#        id sorted first). A NEW patient waits the same way for the new chart of the one before it (new_chart_waits: one person
#        under two new ids got two charts - also two ids of rule 3's relation, which now wait too: two charts in one batch and one
#        chart in two was the fault the wait was built for, and one chart with the FYI of rule 3 at the top is what William can
#        still correct; two charts nobody looks at he cannot). A patient with proof never waits. A wait is no question for William;
#        the chart it waits for that could NOT be made is one (claimocity_newcharts.py says it: WHY_WAIT_FAILED).
#     b) THE PATIENT MAP. A chart of the group rule 6, 7 or 8 chooses from that the feed's patient map gives to ANOTHER Claimocity id
#        is not taken on the name alone: nothing shows the two ids are one person (a chart with no birth date took every same-name
#        patient that came, one run after the other - with a real date by rule 6, without one by rule 8). No chart, none made, for
#        William; his answer goes into the repository's map. A chart nobody in the map owns - it was there before the feed, the
#        patient of 11/8/2026 - is chosen as before. Rule 5 is NOT held back: the slip is evidence of its own (the full name and a
#        date one keystroke from the chart's; it stands in the answer's evidence), and it is the case William's word is about -
#        "where we know the correct dob but claimocity sends the wrong one".
#     c) TWO OF ONE BATCH. Two feed patients of one batch whose real dates are FAR apart never both take one chart by rule 6, 7 or 8
#        (that chart has no date to tell them apart): none of them takes it - William. One with proof of the chart keeps it. Two
#        that MAY be one person - equal dates, a slip between them, no date on one side or on both - still take a chart together in
#        one batch, as before (shared_answer); when they come in two runs, b) asks William about the second.
#   A CHART WILLIAM CALLED A DUPLICATE (his word of 11/9/2026; registers/feed_duplicate_charts.json, read by claimocity_match.py) is
#   never the chart a visit goes to: the PROPER chart stands in its place. What speaks for the duplicate - its name, its date, its
#   numbers: what Claimocity knows that person by - speaks for the proper chart ("also"), and for rules 5 to 8 the two are ONE chart
#   with the proper chart's own date. Until then the duplicate caught that patient's NEXT Claimocity id by rule 2, without a word.
#   SEVERAL IDS UNDER ONE NAME, an id with proof: on a key several Claimocity ids share, an id whose own answer is a chart by rules 1
#   to 4 keeps that chart (claimocity_resolve.py writes "by_proof"); an id without proof stays without one - William.
#   The LIVE chart of a group: a real birth date before none, then the most recent charge that is not void, then the most charges, then
#   the lowest chart id - never the order AdvancedMD lists them in. AdvancedMD lists 50 charts at most: where the list of name
#   candidates may be cut short rule 6 ("the only name candidates") is not asked, and where full-name candidates may be missing too
#   neither are rules 5, 7 and 8 ("all", "ONE date") - rules 1 to 4 stay; else rule 9, flagged, for William. Where only charts under
#   ANOTHER first name may be missing (rule 3 may not have seen them all) every rule is asked, and a new chart for a patient with a real
#   date is flagged, for William. Where the charts that write the last name another way were not asked for (a lookup AdvancedMD did
#   not answer for this patient) every rule is asked as well - no rule is switched off for an unanswered lookup - and a new chart is
#   flagged, for William.
#   What AdvancedMD is asked for must be as wide as what the rule calls the same name: lookup_forms gives the name of a feed patient as
#   the lookups take it - the words of the last name with a % between them, and its LETTERS with a % between them (a chart may write an
#   apostrophe, a space, a period or a hyphen where the feed has none).
#   When a batch carries one Claimocity id with a real date and with
#   none, the real one is used for every message; with two different real dates each is tried, they must not point to two charts, and
#   a NEW chart is written with neither of them (which is right nobody knows: the placeholder date, face sheet needed).
#   To William (top of the report, chart ids and Claimocity ids only): rule 9 beside same-name charts (a question), a new chart with
#   no birth date (face sheet needed), rules 3, 6 and 8 (an FYI - it names the Claimocity id it is about, since two feed patients on
#   one chart gave the same line twice), rule 0 - with the chart in question where the patient map or a second patient of the batch
#   held the answer back; but not a wait and not a key whose ids each went to the chart their own proof names (PLAIN_WORDS: said in
#   the body). Rules 1, 2, 4, 5 and 7 are said in the digest's body.
# Never touches: anything. Pure functions - no AdvancedMD call, no file, no network, no clock (today's date is handed in), nothing
#   printed. Every why, flag and evidence word is a constant of this file, so no name, date or number of a patient can reach a register
#   through them; problems() proves it for any answer. Used by claimocity_match.py, claimocity_resolve.py and claimocity_newcharts.py.
import re, datetime, unicodedata
IDENTITY_RULE_VERSION = "2026-11-25.2"      # (.2, 11/25/2026 - the review: every spelling of the last name is asked for; several ids under one name with no birth date are weighed each on its own; a second new id of one name waits a run; a masked placeholder number is no number) the match step stamps every entry with it; the resolve and new-chart steps refuse an entry of another version
NO_DOB_MDY = "01/01/1900"                   # what a NEW chart is written with when Claimocity sent no usable date - never an empty one
CHART_TRIES = 200                           # how many chart numbers the new-chart step may take for one patient
SUFFIXES = ("JR", "SR", "II", "III", "IV", "V")
# ---- the fixed words ------------------------------------------------------------------------------------------------------------------
SLIP_DIGIT, SLIP_SWAP, SLIP_MONTH_DAY, SLIP_DAY = "one digit differs", "two neighbouring digits swapped", "month and day swapped", "one day apart"
SLIP_KINDS = (SLIP_DIGIT, SLIP_SWAP, SLIP_MONTH_DAY, SLIP_DAY)
FAR = "far"
FLAG_FIRST_NAME = "first name differs"
FLAG_DATE = "birth date differs: "          # + a kind of slip / far / no birth date from Claimocity / chart has no birth date
FLAG_CHART_NO_DOB = "chart has no birth date"
FLAG_NO_FEED_DOB = "no birth date from Claimocity"
FLAG_NO_DOB_EITHER = "no birth date on either side"
FLAG_NOT_USED = "same-name charts not used"
FLAG_TWO_DATES = "Claimocity sent two birth dates"
FLAG_NO_CHART_MADE = "new chart not made"
FLAG_CUT = "list of same-name charts may be incomplete"      # a page of a lookup came back full (AdvancedMD lists 50 charts at most) and no narrower lookup brought the rest - or a lookup AdvancedMD answers went unanswered for this patient
FLAG_DUPLICATE = "in the place of a chart William called a duplicate"      # the chosen chart stood in the place of a listed duplicate: that chart still stands in AdvancedMD (11/25/2026)
FLAG_WORDS = frozenset([FLAG_FIRST_NAME, FLAG_CHART_NO_DOB, FLAG_NO_FEED_DOB, FLAG_NO_DOB_EITHER, FLAG_NOT_USED, FLAG_TWO_DATES, FLAG_NO_CHART_MADE, FLAG_CUT, FLAG_DUPLICATE]
                       + [FLAG_DATE + k for k in SLIP_KINDS + (FAR, FLAG_NO_FEED_DOB, FLAG_CHART_NO_DOB)])
RULES_BY_PROOF = (1, 2, 3, 4)               # the rules that choose by what a chart itself shows: such an answer never waits, and the patient map never holds it back
RULES_BY_CHARTS = (5, 6, 7, 8)              # the rules that choose by what the same-name charts LOOK LIKE: such an answer waits while the same batch makes a same-name chart
RULES_NAME_ALONE = (6, 7, 8)                # ... and of those the ones with nothing but the name: held back where the patient map gives the chart to another Claimocity id (not 5: the slip is evidence of its own)
EVIDENCE = ("mrn", "ssn", "member", "ssn4")                                   # strongest first
EVIDENCE_WORDS = frozenset(EVIDENCE + tuple("slip:" + k for k in SLIP_KINDS))
WHY_NEW = "new chart - no chart with this name"
WHY_NEW_BESIDE = "new chart - same-name charts not used"
WHY = {1: "matched by the Claimocity id on the chart", 2: "matched by name and the same birth date", 3: "matched by last name and the same birth date - the first name differs",
       4: "matched by name and a number in common", 5: "matched by full name - the birth date is a slip from the chart's", 6: "matched by full name - the chart has no birth date",
       7: "matched by full name - Claimocity sent no birth date and the same-name charts carry one date", 8: "matched by full name - no birth date on either side", 9: WHY_NEW}
WHY_MAP = "known from the patient map"                                        # for the driver's own entries (rule "map")
WHY_NOT_YET = "not decided yet - the resolve step has not run"
WHY_UNREAD = "a same-name chart could not be read"
WHY_DISAGREE = "the birth dates or names Claimocity sent point to different charts"
WHY_SHARED = "several Claimocity ids under one name are not known to be one person"
WHY_NO_ID = "the message carries no Claimocity id"
WHY_NO_NAME = "Claimocity sent no last name or no first name"
# (11/25/2026, the independent verification) The wait's words said "a new chart is made in this run for another Claimocity id of this name" - before
# the new-chart step had made it, and also when AdvancedMD then refused it: untrue, run after run. They now say what is waited FOR, and
# "last name" (the wait also holds for rule 3's relation, another first name); the new-chart step puts WHY_WAIT_FAILED in their place when
# that chart could not be made. (Both read the same for one Claimocity id and for a key several ids share.)
WHY_SAME_RUN = "waiting for the new chart of another Claimocity id of this last name in this batch - the next run decides, against the charts that are there then"
WHY_WAIT_FAILED = "waiting for the new chart of another Claimocity id, which could not be made in this run - no chart until that chart is made"
WHY_OWNED = "the chart that fits by the name alone belongs to another Claimocity id in the patient map - nothing shows the two are one person"
WHY_FAR_PAIR = "another feed patient of this batch with a far-apart birth date fits the same chart, which has no birth date - nothing shows whose chart it is"
WHY_EACH_PROOF = "several Claimocity ids under one name - each goes to the chart its own proof names"
WHY_WORDS = frozenset(list(WHY.values()) + [WHY_NEW_BESIDE, WHY_MAP, WHY_NOT_YET, WHY_UNREAD, WHY_DISAGREE, WHY_SHARED, WHY_NO_ID, WHY_NO_NAME, WHY_SAME_RUN, WHY_WAIT_FAILED, WHY_OWNED, WHY_FAR_PAIR, WHY_EACH_PROOF])
PLAIN_WORDS = frozenset([WHY_SAME_RUN, WHY_EACH_PROOF])      # rule 0 that is no question for William: a wait (the next run decides it), and a key whose ids each have their own chart
ASKS = {WHY_OWNED: "same person or not?", WHY_FAR_PAIR: "whose chart is it?"}      # what William is asked where an answer was held back for a chart: his line names that chart
FAIL_NO_PID = "no PID segment for this Claimocity id in the feed files"       # why the new-chart step made no chart (its failed rows)
FAIL_NUMBER = "every chart number tried answered Duplicate chart"
FAIL_REFUSED = "AdvancedMD refused the new chart"
FAIL_NOT_DECIDED = "not decided by the identity rule - no chart is made on an older step's word"
FAIL_WORDS = frozenset([FAIL_NO_PID, FAIL_NUMBER, FAIL_REFUSED, FAIL_NOT_DECIDED])
PLAN_NOT_ADDED = "AdvancedMD did not add the plan"
PHI_FREE_FIELDS = ("rule", "why", "flags", "candidates", "evidence", "feed_dob", "for_william")      # the fields of a match-file entry the driver copies to the register on main

def _list(x):
    if x is None: return []
    return list(x) if isinstance(x, (list, tuple, set, frozenset)) else [x]
def _d8(d): return str(d if d is not None else "").strip()[:8]
def _digits(s): return re.sub(r"[^0-9]", "", str(s if s is not None else ""))

# ---- birth dates ------------------------------------------------------------------------------------------------------------------------
def _date(d8):
    """YYYYMMDD -> a date; None when it is not eight digits or not a day of the calendar."""
    s = str(d8 if d8 is not None else "").strip()
    if not re.fullmatch(r"[0-9]{8}", s): return None
    try: return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:]))
    except ValueError: return None
def real_dob(d8, today8):
    """True when d8 is a REAL birth date seen from today8 (YYYYMMDD both): eight digits, a day of the calendar, year 1901 or later, not after
    today, not more than 120 years ago. A today that is no date is an error, never a quiet 'not real'."""
    d, t = _date(d8), _date(today8)
    if t is None: raise ValueError("today must be YYYYMMDD")
    if d is None or d.year < 1901 or d > t: return False
    try: oldest = t.replace(year=t.year - 120)
    except ValueError: oldest = t.replace(year=t.year - 120, day=28)      # today is 29 February and the year 120 years back has none
    return d >= oldest
def slip(a8, b8):
    """The kind of slip between two dates - one of the four SLIP_ words, the first that fits - or "" when they are equal, FAR, or one of them is
    not a day of the calendar from 1901 on (the placeholder is never a slip from anything). Whether both are REAL is the caller's to ask."""
    a, b = _date(a8), _date(b8)
    if a is None or b is None or a.year < 1901 or b.year < 1901 or a == b: return ""
    x, y = str(a8).strip(), str(b8).strip(); diff = [i for i in range(8) if x[i] != y[i]]
    if len(diff) == 1: return SLIP_DIGIT
    if len(diff) == 2 and diff[1] == diff[0] + 1 and x[diff[0]] == y[diff[1]] and x[diff[1]] == y[diff[0]]: return SLIP_SWAP
    if x[:4] == y[:4] and x[4:6] == y[6:] and x[6:] == y[4:6]: return SLIP_MONTH_DAY
    if abs((a - b).days) == 1: return SLIP_DAY
    return ""
def amd_dob(s):
    """AdvancedMD's date -> YYYYMMDD, "" when there is none: month/day/year (with or without the leading zeros) or the ISO form."""
    t = str(s if s is not None else "").strip()
    m = re.match(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})", t)
    if m: return "%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", t)
    return m.group(1) + m.group(2) + m.group(3) if m else ""
def birth_date(dates, today8):
    """The ONE real birth date among those a batch carries for a patient; "" when there is none - or two different ones (which is right nobody knows)."""
    real = sorted({_d8(d) for d in _list(dates) if real_dob(_d8(d), today8)})
    return real[0] if len(real) == 1 else ""
def chart_dob(dates, today8):
    """What a NEW chart is written with: (the feed's date as MM/DD/YYYY, "real") or (the placeholder date, "none") - never an empty date."""
    d = birth_date(dates, today8)
    return ("%s/%s/%s" % (d[4:6], d[6:8], d[:4]), "real") if d else (NO_DOB_MDY, "none")

# ---- names ------------------------------------------------------------------------------------------------------------------------------
def _up(s):
    t = unicodedata.normalize("NFKD", str(s if s is not None else ""))
    return "".join(c for c in t if not unicodedata.combining(c)).upper()
def _letters(s): return re.sub(r"[^A-Z]", "", _up(s))
def last_key(last):
    """A last name as it is compared: upper case, letters only, a trailing suffix WORD (JR, SR, II, III, IV, V) dropped."""
    words = re.findall(r"[A-Z]+", _up(last))
    if len(words) > 1 and words[-1] in SUFFIXES: words = words[:-1]
    return "".join(words)
def split_name(name):
    """AdvancedMD's LAST,FIRST or the feed's LAST, FIRST -> (last, first); a name without a comma has no first name."""
    last, _, first = str(name if name is not None else "").partition(",")
    return last.strip(), first.strip()
def _first_word(first):
    w = _up(first).split()
    return re.sub(r"[^A-Z]", "", w[0]) if w else ""
def name_kind(feed_last, feed_first, chart_last, chart_first):
    """What a chart's name is to the feed's: "full" (a FULL-NAME candidate), "name" (a NAME CANDIDATE only), "surname" (the same last name under
    another first name - rule 3 only), "" (another last name, or no last name)."""
    k = last_key(feed_last)
    if not k or k != last_key(chart_last): return ""
    a, b = _letters(feed_first), _letters(chart_first)
    if not a or not b or a[:3] != b[:3]: return "surname"
    wa, wb = _first_word(feed_first), _first_word(chart_first)
    if wa and wb and (wa == wb or (min(len(wa), len(wb)) >= 4 and (wa.startswith(wb) or wb.startswith(wa)))): return "full"
    return "name"
def name_candidate(feed_last, feed_first, chart_last, chart_first): return name_kind(feed_last, feed_first, chart_last, chart_first) in ("name", "full")
def full_name_candidate(feed_last, feed_first, chart_last, chart_first): return name_kind(feed_last, feed_first, chart_last, chart_first) == "full"
# 11/25/2026 (review of the identity rule): the rule above compares last names by their LETTERS, but the lookups asked AdvancedMD for the name as the
# feed writes it - a chart with an apostrophe, a space, a period or a hyphen the feed does not have (O'x for Ox, MC x for MCx, DE LA x for DELAx) was
# never listed: a namesake's chart was then taken by the name alone, or a second chart made, without a word. What is asked for must be as wide as
# what the rule calls the same name; these are the forms for it.
def _marked(s):
    """A name as the rule reads it (_up: upper case, accents taken off) - but with every letter that was not written as a plain letter (it carried an
    accent, or one character stood for two letters) in LOWER case: a lookup cannot rely on how AdvancedMD holds such a letter - in a lookup it is a gap."""
    out = []
    for c in unicodedata.normalize("NFKD", str(s if s is not None else "")):
        if unicodedata.combining(c):
            if out and "A" <= out[-1] <= "Z": out[-1] = out[-1].lower()
        else:
            u = c.upper(); out.append(u if len(u) == 1 else u.lower())
    return "".join(out)
def _plain(marked): return "%".join(c for c in marked if "A" <= c <= "Z")          # the plain letters of a marked run, a % between them
def _lead(marked): return "" if "A" <= marked[:1] <= "Z" else "%"                  # a name that begins with something else than a plain letter is asked for with a % in front
def lookup_forms(last, first):
    """One name of the feed as AdvancedMD's name search can be asked for it (% = anything, also nothing; none of the forms ends with one - the caller adds it):
      "words"   - the words of the last name with a % for whatever stands between them, a trailing suffix word dropped: finds the chart whatever it
                  writes where the FEED has an apostrophe, a space, a period or a hyphen, and any longer form of the last name (a suffix, a second name);
      "letters" - its letters with a % between them: finds the chart ALSO when it writes one of those where the feed has none. Every chart the rule
                  calls the same last name answers to it - if its last name begins with the same plain letter (a name the FEED begins otherwise is
                  asked for with a % in front; never every name, which would be a search in the middle of all the others);
      "first3"  - the first three letters of the first name, a % between them (a name candidate begins with them);
      "first4"  - the first four letters of its first word, None when that word has fewer (every FULL-name candidate begins with them);
      "first_word" - that whole word, "" when it has no more than four letters (at least the patient's own chart).
    Letters and % only. A letter that carries an accent is left out: it is a gap, like everything else that is no plain letter."""
    words = re.findall(r"[A-Za-z]+", _marked(last))
    if len(words) > 1 and words[-1].upper() in SUFFIXES: words = words[:-1]
    lead = _lead(_marked(last).strip())
    whole = re.sub(r"%+", "%", "%".join(re.sub(r"[a-z]+", "%", w) for w in words)).strip("%")
    m = _marked(first).strip(); fl = "".join(c for c in m if "A" <= c.upper() <= "Z"); fw = "".join(c for c in (m.split() or [""])[0] if "A" <= c.upper() <= "Z"); fd = _lead(m)
    return {"words": lead + whole, "letters": lead + _plain("".join(words)), "first3": fd + _plain(fl[:3]),
            "first4": fd + _plain(fw[:4]) if len(fw) >= 4 else None, "first_word": fd + _plain(fw) if len(fw) > 4 else ""}
def answers_to(pattern, name):
    """Whether a chart's name, as AdvancedMD lists it, can be an answer to a lookup at all: the letters of the pattern stand, in their order, among the
    letters of the name (case, accents and whatever is written between them aside). A page of charts that do not is the sign that AdvancedMD did
    not make the search it was asked for."""
    return re.search(".*".join(re.sub(r"[^A-Z]", "", str(pattern if pattern is not None else "").upper())), _letters(name)) is not None

# ---- numbers ----------------------------------------------------------------------------------------------------------------------------
def ssn_junk(d):
    """A nine-digit value that is no Social Security number: all one digit, one to nine in a row, starting 000 / 666 / 9, a middle 00 or a last 0000."""
    return len(set(d)) == 1 or d == "123456789" or d[:3] in ("000", "666") or d[0] == "9" or d[3:5] == "00" or d[5:] == "0000"
def ssn_key(s):
    """The nine digits of a usable Social Security number, "" for anything else."""
    d = _digits(s)
    return d if len(d) == 9 and not ssn_junk(d) else ""
def ssn4_junk(d):
    """Four digits that are the mask of a placeholder, not the last four of a number: all one digit (nine nines, nine ones ...) or 6789 (one to nine in a row)."""
    return len(set(d)) == 1 or d == "6789"
def ssn4_key(s):
    """The last four when the value shows EXACTLY four digits (a masked number), "" for anything else - also for the mask of a placeholder (11/25/2026,
    review of the identity rule: a placeholder shown masked on a lookup row counted as proof of another person, and a second chart was made)."""
    d = _digits(s)
    return d if len(d) == 4 and not ssn4_junk(d) else ""
def _ssn_side(v):
    """What one side shows: (nine digits, "") or ("", the last four) or ("", "") - nothing usable, also when it carries two different numbers. The four
    digits a side shows beside its OWN nine-digit placeholder that ends in them are that placeholder's mask: no number."""
    vals = [x for x in _list(v) if x]
    nine = {ssn_key(x) for x in vals} - {""}; four = {ssn4_key(x) for x in vals} - {""}
    four -= {_digits(x)[-4:] for x in vals if len(_digits(x)) == 9 and ssn_junk(_digits(x))}
    if len(nine) == 1: return nine.pop(), ""
    if not nine and len(four) == 1: return "", four.pop()
    return "", ""
def member_key(s): return re.sub(r"[^A-Z0-9]", "", _up(s))
def _member_ok(k): return len(k) >= 8 and re.search(r"[0-9]", k) is not None and len(set(k)) > 1      # letters only, or one character over and over, is no number
def _no_prefix(k): return k[3:] if re.match(r"[A-Z]{3}.", k) else None
def member_equal(a, b):
    """Two member numbers are the same: equal as letters and digits, or equal once a leading three-letter prefix is dropped from ONE of them -
    and what is equal has eight characters or more."""
    x, y = member_key(a), member_key(b)
    return any(p is not None and p == q and _member_ok(p) for p, q in ((x, y), (_no_prefix(x), y), (x, _no_prefix(y))))
def in1_member(s):
    """The member number of one IN1 row (its fields), the rule claimocity_newcharts.py has had since 10/28/2026: IN1-49, else IN1-36; a value
    shaped like a Social Security number or junk ('+', 1-5 characters) is never one."""
    for i in (49, 36):
        v = (s[i].strip() if len(s) > i else "")
        if v and not re.fullmatch(r"\d{3}-?\d{2}-?\d{4}", v) and re.fullmatch(r"[A-Za-z0-9\-]{6,20}", v): return v
    return ""
def _id_key(s): return re.sub(r"[^A-Z0-9]", "", _up(s))
def mrn_equal(feed_id, mrn):
    """The chart's additional number IS this Claimocity id (the new-chart step writes its first 24 characters in upper case; a short number is no Claimocity id)."""
    a, b = _id_key(feed_id), _id_key(mrn)
    return len(a) >= 12 and len(b) >= 12 and (a == b or (len(a) > 24 and a[:24] == b))
def show_id(i):
    """A Claimocity id as a printed line may show it: the 24 hex characters, or a word in its place (an id of another shape is not printed)."""
    return i if re.fullmatch(r"[0-9A-Fa-f]{24}", str(i if i is not None else "")) else "(an id that is not 24 hex characters)"
def evidence(feed, chart):
    """(the evidence that feed and chart are one person, strongest first; whether a Social Security number proves they are two).
    feed: id / ids, ssn, members - chart: mrn, ssn, members (a value or a list each). Works on the numbers and gives back WORDS only."""
    ids = [i for i in _list(feed.get("ids") if feed.get("ids") is not None else feed.get("id")) if i]; ev = []; contra = False
    if any(mrn_equal(i, m) for i in ids for m in _list(chart.get("mrn"))): ev.append("mrn")
    fn, f4 = _ssn_side(feed.get("ssn")); cn, c4 = _ssn_side(chart.get("ssn"))
    if fn and cn:
        if fn == cn: ev.append("ssn")
        else: contra = True
    if any(member_equal(a, b) for a in _list(feed.get("members")) for b in _list(chart.get("members"))): ev.append("member")
    fl, cl = (fn[-4:] if fn else f4), (cn[-4:] if cn else c4)
    if fl and cl and not (fn and cn):                 # a side shows only four digits
        if fl == cl: ev.append("ssn4")
        else: contra = True                           # the last four differ: two numbers, two people (the safest reading)
    return ev, contra

# ---- the live chart ---------------------------------------------------------------------------------------------------------------------
def chart_number(cid):
    m = re.search(r"[0-9]+", str(cid)); return int(m.group(0)) if m else 0
def _dos(x):
    d = _digits(x)[:8]; return int(d) if _date(d) else 0
def live_chart(charts, today8):
    """The LIVE chart of a group (dicts with id, dob, last_dos, charges): a real birth date before none, then the most recent charge that is not
    void, then the most charges, then the lowest chart id - by its number. None for an empty group."""
    if not charts: return None
    return min(charts, key=lambda c: (0 if real_dob(c.get("dob"), today8) else 1, -_dos(c.get("last_dos")), -int(c.get("charges") or 0), chart_number(c.get("id")), str(c.get("id"))))

# ---- the feed patients of one batch -------------------------------------------------------------------------------------------------------
def patients(key_ids, today8, ssn_of=None):
    """Who the patients of a batch are. key_ids: {"NAME|DOB" key (the import's own): [the Claimocity ids of the messages that carry it]}, "" for a
    message without an id; ssn_of(id) -> the Social Security values the feed carries for that id. Answers
      ([{"ids": [...], "keys": [every key the patient came with], "decide_keys": [the keys its own answer is written under],
         "shared_keys": [the keys it shares with another patient - see shared_answer]}, ...] by id, {key: why it cannot be decided}).
    One patient per Claimocity id. Two ids under one name and one REAL birth date are one patient (the same reasoning as rule 2) - unless the feed
    carries two different Social Security numbers for them. A key that two patients share (one name, no birth date: not known to be one person) can
    carry only ONE chart (the import reads the chart by the key): each of them is weighed and decided on its own, and the key gets a chart only when
    the rule gives every one of them the same chart (shared_answer; 11/25/2026, review of the identity rule - until then such a key was decided for
    nobody before anything was weighed, and neither visit was entered). A key that no Claimocity id carries, and one a message without an id shares
    with a Claimocity id under no real date (nobody can say whose it is), are decided for nobody: no chart, none made, for William. A key whose
    ids the feed itself proves to be two people (two different Social Security numbers) never gets ONE chart either and stands among the keys
    nobody can decide together - but each of its ids is still weighed (it is among their shared keys as well): an id with proof of its own chart
    keeps it (11/25/2026, the independent verification - until then neither of them was even weighed, run after run)."""
    tok = lambda k, i: i if i else "\x00" + k          # a message without an id is nobody's own: one token per key
    par = {}
    def find(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for k in sorted(key_ids):
        for i in key_ids[k]: par.setdefault(tok(k, i), tok(k, i))
    for k in sorted(key_ids):
        ts = sorted({tok(k, i) for i in key_ids[k]})
        if len(ts) < 2 or not real_dob(k.rpartition("|")[2], today8): continue
        nines = {n for n in (_ssn_side(ssn_of(x))[0] for x in ts if not x.startswith("\x00")) if n} if ssn_of else set()
        if len(nines) > 1: continue
        for x in ts[1:]: par[find(x)] = find(ts[0])
    comp = {}
    for x in par: comp.setdefault(find(x), set()).add(x)
    out = {}; undecided = {}
    for k in sorted(key_ids):
        roots = sorted({find(tok(k, i)) for i in key_ids[k]})
        for r in roots:
            ids = sorted(x for x in comp[r] if not x.startswith("\x00"))
            if ids: out.setdefault(r, {"ids": ids, "keys": [], "decide_keys": [], "shared_keys": []})["keys"].append(k)
        if len(roots) > 1:
            nines = {n for n in (_ssn_side(ssn_of(i))[0] for i in key_ids[k] if i) if n} if ssn_of else set()
            if all(r in out for r in roots):                      # every one of them can be weighed, each on its own
                for r in roots: out[r]["shared_keys"].append(k)
                if real_dob(k.rpartition("|")[2], today8) or len(nines) > 1: undecided[k] = WHY_SHARED      # ... but the feed itself says they are two people: the key never gets ONE chart
            else: undecided[k] = WHY_SHARED
        elif not roots or roots[0] not in out: undecided[k] = WHY_NO_ID
        else: out[roots[0]]["decide_keys"].append(k)
    return sorted(out.values(), key=lambda p: p["ids"]), undecided
def shared_answer(answers, apart=False):
    """The answer for a name-and-date key that several patients of one batch share (patients: one name, no real birth date - not known to be one
    person; the import can give the key only ONE chart). answers: what decide() answered for each of them, each weighed on its own. The key carries
    a chart only when every one of them was given that SAME chart - then under the weakest of their answers (the highest rule number: its flags say
    what was not known). Anything else - two charts, a chart and a new chart, a new chart for each (never ONE new chart for two ids nobody knows to
    be one person, never two charts under one key), one of them not decided - is rule 0: no chart and none made, for William.
    11/25/2026 (the independent verification): apart - the feed itself shows the ids to be two people (patients): never ONE chart, whatever each
    was given. One of them WAITS for a new chart of the batch (waits): the key waits with it, in the wait's own words, not for William - the
    next run decides. Every one of them was held back for one and the same reason that names a chart (ASKS: the patient map, a far-apart pair):
    the key says that reason. (claimocity_resolve.py still gives each id that has PROOF of its own chart that chart: "by_proof".)"""
    rs = list(answers); cands = _sorted_ids(i for r in rs for i in r["candidates"])
    if rs and not apart and all(r["chart"] for r in rs) and len({r["chart"] for r in rs}) == 1:
        a = dict(max(rs, key=lambda r: (r["rule"], 1 if r["for_william"] else 0, tuple(r["flags"]), tuple(r["evidence"]), tuple(r["group"]), r["feed_dob"])))      # (the same for every order of the answers)
        a["flags"] = list(a["flags"]); a["evidence"] = list(a["evidence"]); a["group"] = list(a["group"])
    elif any(r["rule"] == 0 and r["why"] == WHY_SAME_RUN for r in rs): a = _answer(0, WHY_SAME_RUN)
    elif rs and all(r["rule"] == 0 for r in rs) and len({r["why"] for r in rs}) == 1 and rs[0]["why"] in ASKS: a = _answer(0, rs[0]["why"], william=True)
    else: a = _answer(0, WHY_SHARED, william=True)
    a["candidates"] = cands; a["needs_activity"] = []; a["new_chart"] = False
    return a
def related(p, q):
    """Whether the new chart of patient q is a chart the rule would weigh patient p against (11/25/2026, the independent verification): a name of p
    is a NAME CANDIDATE of a name of q - or, rule 3's relation, the two share the last name under another first name and q's chart is written
    with a real birth date that p carries too (q has exactly ONE: with two dates, or none, its chart is written with no date rule 3 could go
    by). p, q: {"names": [(last, first), ...], "dobs": [the REAL birth dates the batch carries for it]} - which dates are real is the caller's
    to say (this file has no clock). Pure."""
    kinds = {name_kind(str(l or ""), str(f or ""), str(ml or ""), str(mf or "")) for l, f in (p.get("names") or []) for ml, mf in (q.get("names") or [])}
    if kinds & {"name", "full"}: return True
    qd = sorted({_d8(d) for d in _list(q.get("dobs")) if _d8(d)})
    return "surname" in kinds and len(qd) == 1 and qd[0] in {_d8(d) for d in _list(p.get("dobs"))}
def new_chart_waits(patients):
    """One person under two NEW Claimocity ids in one batch (the second birth date a digit off, or none) got two new charts - where the same two
    messages in two batches got ONE: the second run finds the first one's new chart and the rule takes it (11/25/2026, review of the identity rule).
    patients: the patients of one batch that rule 9 gives a new chart, each {"names": [(last, first), ...], "real": the batch carries a real birth date
    for it, "dobs": [those real dates]}. -> the positions of those whose new chart is NOT made in this run: a patient the rule would weigh against
    the chart of one whose chart IS made (related: a name candidate - or, since the independent verification of 11/25/2026, rule 3's relation;
    without "dobs" only the name is asked). Never for one that itself waits: that one's chart is not made now, and the next run weighs it
    against both. The charts are made for the patients with a real birth date first (the chart the other is weighed against carries its date),
    then in the order given. A patient that waits gets no chart in this run; the next run weighs it against the chart made now - and takes it,
    or makes a new chart beside it and asks William. Pure."""
    ps = list(patients); made = []; wait = []
    for i in sorted(range(len(ps)), key=lambda i: (0 if ps[i].get("real") else 1, i)):
        if any(related(ps[i], ps[j]) for j in made): wait.append(i)
        else: made.append(i)
    return sorted(wait)
def waits(d):
    """The answer of a patient that waits for the next run - one whose new chart waits (new_chart_waits), and one whose answer rests on the same-name
    charts while the batch makes another of them (claimocity_resolve.py): no chart, none made - and not for William, the next run decides."""
    a = _answer(0, WHY_SAME_RUN); a["candidates"] = list(d.get("candidates") or []); a["feed_dob"] = d.get("feed_dob") if d.get("feed_dob") in ("real", "none") else "none"
    return a
def undecided(d, why, charts=None):
    """The answer of a patient whose own answer d does not stand for a reason the rule sees only across the batch: no chart, none made, rule 0 under
    the fixed words given, for William; charts - the chart(s) in question, named to him (without them: the charts d had considered)."""
    if why not in WHY_WORDS: raise ValueError("not one of the fixed words")
    a = _answer(0, why, william=True); a["candidates"] = _sorted_ids(charts if charts is not None else (d.get("candidates") or []))
    a["feed_dob"] = d.get("feed_dob") if d.get("feed_dob") in ("real", "none") else "none"
    return a
def same_chart_far(patients):
    """Two feed patients of ONE batch with far-apart real birth dates were both put on one chart that has no birth date (rule 6 twice): two people on
    one chart, the second one's visit on the first one's plan (11/25/2026, the independent verification). patients: the patients of a batch, each
    {"chart": the chart its answer names (or None), "rule": its rule number, "dobs": [its REAL birth dates]}. -> the positions of those whose answer
    does not stand: a chart by the name alone (RULES_NAME_ALONE) that ANOTHER patient of the batch was given too - by any rule - while the two
    are FAR apart: each carries a real date, and no date of the one equals, or is a slip from, a date of the other. A patient with proof of the
    chart keeps it; two that may be one person (equal dates, a slip, no date on one side) are left as they are. Pure."""
    def far(a, b):
        a, b = {_d8(x) for x in _list(a) if _d8(x)}, {_d8(x) for x in _list(b) if _d8(x)}
        return bool(a) and bool(b) and not any(x == y or slip(x, y) for x in a for y in b)
    ps = list(patients)
    return [i for i, p in enumerate(ps) if p.get("chart") and p.get("rule") in RULES_NAME_ALONE
            and any(j != i and q.get("chart") == p["chart"] and far(p.get("dobs"), q.get("dobs")) for j, q in enumerate(ps))]

# ---- decide() ---------------------------------------------------------------------------------------------------------------------------
def _ids(cs): return [c["id"] for c in sorted(cs, key=lambda c: (chart_number(c["id"]), c["id"]))]
def _sorted_ids(ids): return sorted(set(ids), key=lambda i: (chart_number(i), i))
def _contra(cs): return any(c["contra"] for c in cs)
def _answer(rule, why, chart=None, flags=(), ev=(), considered=(), group=(), william=False):
    return {"chart": chart, "rule": rule, "why": why, "flags": list(flags), "evidence": list(ev), "candidates": _ids(considered), "group": _ids(group), "needs_activity": [],
            "feed_dob": "none", "for_william": william, "new_chart": rule == 9}
def _date_flags(d, cd):
    """Rule 4's flag: how the feed's date d and the chosen chart's date cd stand to each other ("" = none on that side)."""
    if d and cd: return [] if d == cd else [FLAG_DATE + (slip(d, cd) or FAR)]
    if cd: return [FLAG_DATE + FLAG_NO_FEED_DOB]
    if d: return [FLAG_DATE + FLAG_CHART_NO_DOB]
    return [FLAG_NO_DOB_EITHER]
def _chosen(rule, group, flags, considered, d, today8):
    live = live_chart(group, today8); ev = list(live["ev"]); k = slip(d, live["dob"]) if d and live["dob"] else ""
    if k: ev.append("slip:" + k)
    a = _answer(rule, WHY[rule], live["id"], _date_flags(d, live["dob"]) if flags is None else flags, ev, considered, group, rule in (3, 6, 8))
    if live["dup"]: a["flags"].append(FLAG_DUPLICATE)      # the chosen chart stood in the place of a chart William called a duplicate
    a["needs_activity"] = _ids([c for c in group if not c["act"]]) if len(group) > 1 else []      # the live chart of several needs their activity
    return a
def _kind(last, first, c):
    """What a chart is to one name of the feed: by its own name - or by the name of a chart William called its duplicate, where that says more."""
    ks = {name_kind(last, first, l, f) for l, f in c["names"]}
    return next((k for k in ("full", "name", "surname") if k in ks), "")
def _one(last, first, d, cs, today8, cut=""):
    """Rules 1 to 9 for ONE name and ONE date of the feed (d = its real birth date, "" when it has none). cut: AdvancedMD's list of same-name charts
    may be cut short - "first": only charts under ANOTHER first name may be missing (rule 3 may not have seen them all: every rule is still asked, but
    a NEW chart for a patient with a real date is flagged, for William); "spelling": the charts that write the last name another way than the feed
    were not asked for (AdvancedMD did not answer that lookup for this patient - the list is what these steps saw until 11/25/2026: every rule is
    asked, as it always was, but a NEW chart is flagged, for William); "name": name candidates may be missing (rule 6 says 'the ONLY name
    candidates': not asked); "full": full-name candidates may be missing too (rules 5, 7 and 8 say 'all' and 'ONE date': not asked either).
    Rules 1 to 4 choose by what a chart itself shows and stay.
    A chart that stands in the place of charts William called its duplicates (decide: "also") is to the rules that go by PROOF every name and
    every date it is known under - the feed's date on the duplicate is 'the same birth date' (rules 2 and 3) - and to the rules that go by what
    the charts look like (5 to 8) ONE chart with its own date."""
    kind = {c["id"]: _kind(last, first, c) for c in cs}
    name_c = [c for c in cs if kind[c["id"]] in ("name", "full")]; full_c = [c for c in name_c if kind[c["id"]] == "full"]
    sur_c = [c for c in cs if kind[c["id"]] == "surname" and d and d in c["dates"]]      # the same last name and exactly the date, under another first name
    exact = [c for c in name_c if d and d in c["dates"]]
    if any(not c["read"] for c in name_c + sur_c): return _answer(0, WHY_UNREAD, considered=name_c + sur_c, william=True)
    g = [c for c in name_c if "mrn" in c["ev"]]
    if g: return _chosen(1, g, [], name_c, d, today8)
    if exact and not _contra(exact): return _chosen(2, exact, [], name_c, d, today8)
    if d and not exact and sur_c and not _contra(sur_c): return _chosen(3, sur_c, [FLAG_FIRST_NAME], name_c + sur_c, d, today8)
    for e in ("ssn", "member", "ssn4"):
        g = [c for c in name_c if e in c["ev"]]
        if g:
            if not _contra(g): return _chosen(4, g, None, name_c, d, today8)
            break                                      # the number is shared with a chart that is proven another person: it proves nothing here
    if d and not exact and cut != "full":              # (a name candidate WITH the date that rule 2 could not take is a namesake: no slip is read then)
        g = [c for c in full_c if c["dob"] and slip(d, c["dob"])]
        if g and len({c["dob"] for c in g}) == 1 and not _contra(g): return _chosen(5, g, [FLAG_DATE + slip(d, g[0]["dob"])], name_c, d, today8)
    if d and cut in ("", "first", "spelling") and name_c and len(full_c) == len(name_c) and not any(c["dob"] for c in name_c) and not _contra(name_c): return _chosen(6, name_c, [FLAG_CHART_NO_DOB], name_c, d, today8)
    if not d and cut != "full" and full_c and not _contra(full_c):       # no date to go by at all: a proven namesake among the full-name charts stops both rules
        dated = [c for c in full_c if c["dob"]]
        if dated and len({c["dob"] for c in dated}) == 1: return _chosen(7, dated, [FLAG_NO_FEED_DOB], name_c, d, today8)
        if not dated: return _chosen(8, full_c, [FLAG_NO_DOB_EITHER], name_c, d, today8)
    short = bool(cut) and (cut != "first" or bool(d))      # (a list cut only for other first names matters to rule 3 alone, and rule 3 is never asked without a real date)
    flags = ([FLAG_NOT_USED] if name_c else []) + ([] if d else [FLAG_NO_FEED_DOB]) + ([FLAG_CUT] if short else [])
    return _answer(9, WHY_NEW_BESIDE if name_c else WHY_NEW, flags=flags, considered=name_c, william=bool(name_c) or short)      # (a new chart with no date is for William too: decide() says so)
def _combine(rs):
    """One answer from the answers of every name and date the feed carries for the patient: a chart only when all that chose one chose the same."""
    needs = _sorted_ids(i for r in rs for i in r["needs_activity"]); cands = _sorted_ids(i for r in rs for i in r["candidates"])
    zero = [r for r in rs if r["rule"] == 0]; chose = [r for r in rs if r["chart"]]
    if zero: a = dict(zero[0])
    elif chose and len({r["chart"] for r in chose}) == 1: a = dict(min(chose, key=lambda r: r["rule"]))
    elif chose: a = _answer(0, WHY_DISAGREE, william=True)
    else:
        flags = [x for x in (FLAG_NOT_USED, FLAG_NO_FEED_DOB, FLAG_CUT) if any(x in r["flags"] for r in rs)]
        a = dict(rs[0], flags=flags, why=WHY_NEW_BESIDE if FLAG_NOT_USED in flags else WHY_NEW, for_william=any(r["for_william"] for r in rs))
    a["flags"] = list(a["flags"]); a["candidates"] = cands; a["needs_activity"] = needs
    return a
def decide(feed, candidates, today8):
    """Which chart is this feed patient? Pure and the same for every order of the charts.
    feed: {"id" or "ids": the Claimocity id(s), "name" ("LAST, FIRST") or "names" [(last, first), ...], "dob" or "dobs": the birth date(s) the batch
           carries (YYYYMMDD), "ssn": value(s), "members": [member numbers], "cut": "" | "first" | "spelling" | "name" | "full" - how far the list
           of same-name charts may fall short (AdvancedMD answers 50 at most, and may not answer a lookup): see _one}
    candidates: the charts found by name, each {"id": "pat123", "name": "LAST,FIRST", "dob": YYYYMMDD or "", and EITHER the chart's own "mrn" / "ssn" /
           "members" OR the words worked out beforehand "ev" [...] / "contra" bool, "read": False when the chart could not be read, "last_dos" (YYYYMMDD)
           and "charges" (how many) once its activity was read, "owned": True when the feed's patient map gives this chart to ANOTHER Claimocity id
           (claimocity_match.py says it), "also": [{"name", "dob"} of each chart William called a duplicate of this one - it stands in their place]}
    Answers {"chart": the chart id or None, "rule": 1..9 (0 = not decided: no chart and no new chart), "why": fixed words, "flags": [...], "evidence": [...]
           of the chosen chart, "candidates": [chart ids considered - for an answer held back for a chart (ASKS) the chart(s) in question], "group": [the
           charts the live one was taken from], "needs_activity": [charts of a group of several whose activity was not given - read it and ask again;
           until then the chart is not final], "feed_dob": "real" | "none", "for_william": bool, "new_chart": bool}.
    11/25/2026 (the independent verification): an answer by the name alone (RULES_NAME_ALONE) whose group holds a chart that is "owned" is held back -
           rule 0, WHY_OWNED, for William, those charts named: nothing shows the two Claimocity ids are one person. The whole group counts, not
           only its live chart: the rule takes the live one of charts it calls ONE person's, and that person has another Claimocity id."""
    ids = [i for i in _list(feed.get("ids") if feed.get("ids") is not None else feed.get("id")) if i]
    if feed.get("names") is not None: names = [tuple(n) for n in feed["names"]]
    elif feed.get("name") is not None: names = [split_name(feed["name"])]
    else: names = [(feed.get("last"), feed.get("first"))]
    names = sorted({(str(l if l is not None else "").strip(), str(f if f is not None else "").strip()) for l, f in names})
    names = [(l, f) for l, f in names if last_key(l) and _letters(f)]
    real = sorted({_d8(d) for d in _list(feed.get("dobs") if feed.get("dobs") is not None else feed.get("dob")) if real_dob(_d8(d), today8)})
    cs = []
    for c in candidates:
        cid = c.get("id") if c.get("id") is not None else c.get("pid")
        if not isinstance(cid, str) or not re.fullmatch(r"pat[0-9]+", cid): raise ValueError("a chart id must look like pat123")
        last, first = split_name(c["name"]) if c.get("name") is not None else (c.get("last") or "", c.get("first") or "")
        if "ev" in c: ev, contra = [e for e in EVIDENCE if e in (c.get("ev") or [])], bool(c.get("contra"))
        else: ev, contra = evidence({"ids": ids, "ssn": feed.get("ssn"), "members": feed.get("members")}, c)
        dob = _d8(c.get("dob")); dob = dob if real_dob(dob, today8) else ""
        also = [(split_name(x.get("name")), _d8(x.get("dob"))) for x in (c.get("also") if isinstance(c.get("also"), (list, tuple)) else []) if isinstance(x, dict)]      # the charts it stands in the place of
        cs.append({"id": cid, "last": last, "first": first, "dob": dob, "ev": ev, "contra": contra, "read": c.get("read", True) is not False,
                   "act": "last_dos" in c or "charges" in c, "last_dos": c.get("last_dos") or "", "charges": c.get("charges") or 0, "owned": c.get("owned") is True, "dup": bool(also),
                   "names": [(last, first)] + [n for n, _d in also], "dates": {x for x in [dob] + [x for _n, x in also if real_dob(x, today8)] if x}})
    cs.sort(key=lambda c: (chart_number(c["id"]), c["id"]))
    if len({c["id"] for c in cs}) != len(cs): raise ValueError("the same chart was given twice")
    two = len(real) > 1; cut = feed.get("cut") if feed.get("cut") in ("", "first", "spelling", "name", None) else "full"      # anything else that is said about a cut list counts as the worst
    if not names: a = _answer(0, WHY_NO_NAME, william=True)
    else:
        a = _combine([_one(l, f, d, cs, today8, cut or "") for l, f in names for d in (real or [""])])
        theirs = [c for c in cs if c["id"] in a["group"] and c["owned"]] if a["chart"] and a["rule"] in RULES_NAME_ALONE else []
        if theirs: a = _answer(0, WHY_OWNED, considered=theirs, william=True)      # the name alone, and the patient map gives a chart of that group to another Claimocity id: not taken on the rule's own word
        if two and FLAG_TWO_DATES not in a["flags"]: a["flags"].append(FLAG_TWO_DATES)
    a["feed_dob"] = "real" if real and not (a["rule"] == 9 and two) else "none"      # a NEW chart of a patient with two real dates is written with none of them
    if a["rule"] == 9 and a["feed_dob"] == "none": a["for_william"] = True               # face sheet needed
    return a

# ---- what the fields may hold, and what goes to William ---------------------------------------------------------------------------------
def problems(d):
    """What in an answer - or in a match-file entry - is NOT one of the fixed words, a chart id, a rule number or a yes/no: the names of the fields.
    An empty list is the proof that no name, date or number of a patient sits in the fields the driver copies to the register on main."""
    out = []; rule = d.get("rule")
    if not (rule == "map" or (isinstance(rule, int) and not isinstance(rule, bool) and 0 <= rule <= 9)): out.append("rule")
    if d.get("why") not in WHY_WORDS: out.append("why")
    if not isinstance(d.get("flags"), list) or any(x not in FLAG_WORDS for x in d["flags"]): out.append("flags")
    if not isinstance(d.get("evidence"), list) or any(x not in EVIDENCE_WORDS for x in d["evidence"]): out.append("evidence")
    if not isinstance(d.get("candidates"), list) or any(not isinstance(x, str) or not re.fullmatch(r"pat[0-9]+", x) for x in d["candidates"]): out.append("candidates")
    if d.get("feed_dob") not in ("real", "none"): out.append("feed_dob")
    if not isinstance(d.get("for_william"), bool): out.append("for_william")
    return out
def william_lines(d, chart="", feed_id=""):
    """What goes to William for one patient - the top of the report, one line each, chart ids and Claimocity ids only (a run turns it into a board
    card with the names). d: an answer or a match-file entry; chart: the chart chosen, or the new chart once it is made ("" = not made yet);
    feed_id: the Claimocity id the line is about - or the list of them, when one answer stands for several ids.
    11/25/2026 (the independent verification): the FYI of rules 3, 6 and 8 names the Claimocity id (two feed patients on one chart gave the same
    line twice, and nobody could tell which id each was about); an answer held back for a chart (ASKS) names that chart and asks the question."""
    rule = d.get("rule"); flags = d.get("flags") or []; cands = [c for c in (d.get("candidates") or []) if isinstance(c, str) and re.fullmatch(r"pat[0-9]+", c)]; out = []
    why = d.get("why") if d.get("why") in WHY_WORDS else ""; chart = chart if re.fullmatch(r"pat[0-9]+", str(chart or "")) else ""      # a chart id or nothing: these lines are printed
    ids = [i for i in _list(feed_id) if i] or [""]; who = "Claimocity id%s %s" % ("s" if len(ids) > 1 else "", ", ".join(show_id(i) for i in ids))
    made = ("new chart %s was made" % chart) if chart else "a new chart is needed"
    if rule == 0:
        if why not in PLAIN_WORDS:      # (a wait for the next run is no question for William; nor is a key whose ids each went to the chart of their own proof)
            out.append("no chart chosen and none made for %s: %s%s" % (who, why, " (chart%s %s) - %s" % ("s" if len(cands) > 1 else "", ", ".join(cands), ASKS[why]) if why in ASKS and cands else ""))
    elif rule in (3, 6, 8): out.append("%s %s (FYI) - %s" % (chart or "a chart", why, who))
    elif rule == 9:
        if FLAG_NOT_USED in flags: out.append("%s beside %d same-name chart(s) (%s) with other birth dates and no number in common - same person or not?" % (made, len(cands), ", ".join(cands)))
        if FLAG_CUT in flags and FLAG_NOT_USED not in flags: out.append("%s although AdvancedMD's list of same-name charts may be incomplete - is there a chart of this patient already?" % made)
        if d.get("feed_dob") == "none": out.append("%s: Claimocity sent %s - face sheet needed" % (made, "two different birth dates" if FLAG_TWO_DATES in flags else "no birth date"))
        if FLAG_NO_CHART_MADE in flags: out.append("the new chart for %s could NOT be made - its visits are not entered" % who)
    return out
