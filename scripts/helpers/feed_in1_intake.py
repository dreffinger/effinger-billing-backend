# PLAIN ENGLISH (Insurance intake from the feed for charts that already exist - the secondaries the import never entered)
# Decides: which insurance blocks the Claimocity feed carried are worth putting on an EXISTING chart, and does it. Built 11/19/2026
#   (William: "fix it for the insurance intake for sure ... optimize getting the correct insurances for billing on the back end using
#   apis first") after the comparison of all 31 feed files with the charts: the import enters feed insurance only when it CREATES a
#   chart, so on existing charts 74 usable blocks (55 charts) never arrived - nearly all the Medicaid side of a nursing-home resident
#   (Florida Community Care, Medicaid, Sunshine, Simply) and a few Medigap plans.
# What it does, per chart, cheapest source first:
#   1. the feed block: payer name -> carrier and kind through the ONE table (feed_payer_map.py); rows that are not a plan to bill
#      (liability, coinsurance rows, pending, dental ...) and long-term-care-only plans are dropped;
#   2. the chart (free): a carrier the chart already holds, open or ended, is never added again; a chart that already has an open
#      Medicaid-family plan is left to the nightly cascade (listed, not changed);
#   3. a block that names a different PRIMARY plan is never entered here - the feed only informs; the dated eligibility check of the
#      import / the cascade decides who is primary (listed for it);
#   4. Medicaid side: ONE Florida Medicaid eligibility check through Stedi with the feed's Medicaid number (the ordinary eligibility
#      price) - active or not, and WHICH managed plan the state names; the plan the STATE names wins over the feed's wording. Not
#      active = nothing added. Medicaid cannot answer (an error, an outage) = nothing added, tried again next run;
#      11/25/2026 (William: "correct every one that comes to the correct date of birth and insurance and fix them ... where we know the
#      correct dob but claimocity sends the wrong one or the 01011900 default date"): Medicaid is asked
#      with the CHART's own name and birth date - from the chart answer read in step 2, no extra call - whenever the chart's birth date
#      is a real one; else with the feed's, as before; never a mix of the two. Until that day it was asked with the FEED's name and birth
#      date - also when the feed carries a wrong date or the year-1900 placeholder for a patient whose chart was corrected from a face
#      sheet. The line it prints and the register entry say which one was asked whenever the two dates are not the same - by the kind
#      of slip, never with a name or a date. See lookup_who;
#      11/25/2026, the review of that change (it holds for step 5 too):
#      nothing of the feed's insurance is asked about or entered while nobody knows that the chart is the feed's patient - two real
#      birth dates far apart; or a date that differs or is missing AND a name that is not the chart's; or only the date the same and
#      both names others - unless the chart carries the patient's Claimocity id (its additional number) or William said so for the
#      run (--same-person). Such a chart gets ONE line "feed insurance not entered - same person? ..." for William: no check is
#      bought, no plan is added, nothing is registered (a plan added here would let the next insurance check release the chart's
#      visits). A chart that could not be read is asked as before, and the line says it could not be read. See lookup_hold;
#      11/25/2026, the SECOND review of that part (it holds for step 5 too; each finding was reproduced before it was changed):
#      A NUMBER IN COMMON MAKES THE CHART KNOWN TOO - the same nine-digit Social Security number, or a member number of the feed's
#      insurance rows on one of the chart's plans. Until then such a chart - William's own case, "we know the correct dob but claimocity
#      sends the wrong one" - got the line "same person?" although the identity rule had matched it by the number. The numbers are weighed
#      the rule's own way (feed_identity.py beside this helper): the chart's from the chart answer of step 2, the feed's from the raw
#      files of --hl7-dir (PID-19, and IN1-49 else IN1-36), read into memory only. A number counts where the chart's name is a name
#      candidate of the feed's (the same last name, the first three letters of the first name - the rule's rule 4 goes no further);
#      under any other name it frees nobody - a member number can be a whole family's - and the line says it is there. The last four
#      alone free nobody; two DIFFERENT Social Security numbers free nobody whatever else is in common, and are said. A plan the
#      feed's OWN steps put on the chart (this step, the insurance check's look-up, the hand step - the registers say which) is never
#      weighed: its number came from the feed itself and proves nothing about whose chart it is. Without
#      feed_identity.py beside this helper no number proves anything and the line stands as it did. Also since that review:
#      EVERY record a feed patient comes with is judged, not the last one read (where ONE patient comes with two different real
#      birth dates and the chart carries none of its own, Medicaid is asked as before, with one of the two - chosen by what the
#      records carry, never by the order of the files - and the line says there were two); two feed patients the map sends to ONE chart that
#      carries no birth date of its own, with real birth dates far apart, are both left for William; his line names the Claimocity
#      id; his standing word (registers/feed_same_person.json) is read strictly, and ONE printed line, which begins SAME PERSON FILE:,
#      names every entry that does not count. A plan AdvancedMD refuses is said in fixed words -
#      AdvancedMD's own answer, which can name a member number, is kept under patient_db/ in the workspace and never printed.
#      See number_proof, lookup_judge, lookup_apart, same_person_gaps, chart_judge;
#      11/25/2026, ROUND 2 of that review (it holds for step 5 too; what the independent checkers of its fixes found, reproduced first):
#      A MEMBER NUMBER IN COMMON COUNTS ONLY WITH BIRTH DATES THAT AGREE - both sides carry a real birth date and the two are the same or
#      a slip apart. A family shares member numbers: with the paragraph above a husband's chart got his wife's Medicaid plan - Florida
#      Medicaid was asked with HIS name and birth date and HER number - and a father's chart his son's. With the dates far apart, or a
#      date missing on either side, a member number proves nothing: the chart gets its line "same person? ...", the line says that a plan
#      of the chart carries a member number Claimocity sent, and William is asked - once per chart, his yes is kept in his standing file.
#      The nine-digit Social Security number, the Claimocity id on the chart and his word count as before. See lookup_hold;
#      11/26/2026, ROUND 3 (it holds for step 5 too; identity rule 2026-11-26.5 - a relative is not the patient):
#      THE SAME NAME IS THE SAME FIRST WORD AND NO OTHER SUFFIX. 'A name that is the chart's' was also a first name that only BEGINS with
#      the chart's and the chart's name with another suffix (JR, SR, II ...): a wife or a son Claimocity sent with the year-1900
#      placeholder was asked about under the CHART's person - Florida Medicaid with HIS name and birth date and HER number - and the
#      plan went on his chart, without a line for William. Now such a name is alike but not the same: with a birth date missing on one
#      side, or a slip between the two, the chart gets its line "same person? ... and the names are alike but not the same" like any
#      other name. A middle initial or a second first name is still the same name, and William's own case - the chart's very own name
#      sent with the placeholder - is asked as before. See _name_kind, lookup_hold;
#      11/26/2026, ROUND 4 (identity rule 2026-11-26.6 - the identity check's two medium findings on round 3):
#      THE WHOLE FIRST NAME IS COMPARED AND A LONE V BEHIND THE FIRST NAME IS A MIDDLE INITIAL. lookup_who was handed the first WORD of
#      the feed's first name only, so the same name with JR behind the first name on both sides read '... the names are alike but not
#      the same' in the printed line and the register entry: it is handed the whole first name now, compares the names with it, and asks
#      Medicaid with its first word. And a lone V right behind the first word of the first name (MARY V) is a middle initial, not the
#      suffix V - MARY and MARY V are the same name (V stays a suffix behind the last name and behind a middle name or initial). See
#      _name_kind, lookup_who;
#   5. Medigap / TRICARE For Life / CHAMPVA: the plan is added and AdvancedMD's free eligibility check is run on it; a clear
#      'inactive' or 'not found' ends the plan again the same minute;
#   6. the plan is added with no group number and, when the chart's insurance order holds no Medicaid-family / secondary plan yet,
#      appended as the LAST plan of the order (Medicare or the Advantage plan stays first - William's standing order).
# Never touches: visits, claims, balances, the primary plan, a chart's existing plans. Nothing is re-billed here.
# Usage: python3 feed_in1_intake.py [--hl7-dir inbox/claimocity] [--live] [--max 60] [--stamp <run stamp>] [--same-person <chart>,...]
# Register: registers/feed_in1_intake.json (chart + carrier + outcome; one entry per chart and carrier - never asked twice)
import amd, add_ins, ins_update, elig_amd, stedi, adt_ingest, feed_payer_map as fpm, json, os, re, sys, time, datetime, collections
def opt(n, d=None): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
LIVE = "--live" in sys.argv; DIR = opt("--hl7-dir", "inbox/claimocity"); MAX = int(opt("--max", "60")); STAMP = opt("--stamp", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ"))
CAR = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CAR.items()}; CAR2CODE = {k: v[0] for k, v in CAR.items()}
PMAP = json.load(open("registers/claimocity_patient_map.json"))
REGF = "registers/feed_in1_intake.json"; REG = json.load(open(REGF)) if os.path.exists(REGF) else {}
SAME = {re.sub(r"\D", "", x) for x in (opt("--same-person", "") or "").split(",")} - {""}      # 11/25/2026 (review): William's word for THIS run - these charts are their feed patients (lookup_hold's sure)
SAME_YES = {}      # ... and his STANDING word (registers/feed_same_person.json: this chart AND this Claimocity id) - read once, below, where the helper's functions exist
STATE_PLAN = [(r"FLORIDA COMMUNITY", "FLO99"), (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"HUMANA", "HUM01"), (r"MOLINA", "MOL10"), (r"STAYWELL|WELLCARE", "STA03")]
norm = lambda s: re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def medicaid_answer(first, last, dob8, medicaid_id, pid):
    """('active'|'inactive'|'unknown', carrier code the state names or 'MCAD', short text). One Stedi eligibility check (payer 77027)."""
    try: j = stedi.elig("77027", first, last, dob8, medicaid_id, datetime.date.today().strftime("%Y%m%d"), pid=pid)
    except Exception as e: return "unknown", None, "Medicaid check failed (%s)" % type(e).__name__
    os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_medicaid_%s.json" % (pid, datetime.date.today().strftime("%Y%m%d")), "w"))
    errs = [str(e.get("code")) for e in j.get("errors") or []]
    if errs: return "unknown", None, "Medicaid answered error %s" % ",".join(errs)
    ben = j.get("benefitsInformation") or []
    if not any(b.get("code") == "1" for b in ben): return "inactive", None, "Medicaid: no active coverage"
    names = []
    for b in ben:
        if b.get("code") in ("MC", "1", "R", "U"):
            for e in b.get("benefitsRelatedEntities") or []:
                if e.get("entityName"): names.append((b.get("code"), " ".join(str(x) for x in (b.get("planCoverage"), b.get("insuranceType"), e.get("entityName")) if x)))
    mma = [t for c, t in names if c == "MC" and not re.search(r"\bLTC\b|LONG.?TERM|DENTAL|TRANSPORT", t.upper())] or [t for c, t in names if c == "MC" and re.search(r"FLORIDA COMMUNITY", t.upper())]
    for t in mma:
        for pat, code in STATE_PLAN:
            if re.search(pat, t.upper()): return "active", code, "Medicaid active; the state names %s" % t[:60]
    return "active", "MCAD", "Medicaid active; no managed medical plan named (%s)" % ("; ".join(t[:30] for c, t in names[:3]) or "fee-for-service")
# ---- William 11/25/2026 ("correct every one that comes to the correct date of birth and insurance and fix them figure our how to do this for other charts that have the
# same mistake where we know the correct dob but claimocity sends the wrong one or the 01011900 default date") - WHOM MEDICAID IS ASKED ABOUT -----------------------------
# The feed sends some patients with a WRONG birth date or with the year-1900 placeholder although the chart holds the right one. The Medicaid check below was asked with the
# FEED's name and birth date. How Florida Medicaid answers a check whose birth date is not the one it holds has not been captured (the repository's notes record the
# refusal AAA 71 for such a check from Centene - docs/captured_calls.md - and from Medicare - docs/SHARED_LESSONS.md); an answer that is an error counts as 'could not
# answer' here - nothing added, bought again next run. The chart is read here anyway (ins_update._plans, step 2) and its answer carries the patient's own name and birth
# date: lookup_who takes them from it - no extra call - and falls back to the feed's only when the chart's birth date is not a real one. What it says goes into the printed
# line and the register, so its words carry no name and no date.
# WHEN NOTHING IS ENTERED (11/25/2026, the review of the first version of this change): "the chart is the patient" is not always true - a Claimocity id the patient map
# knows goes to its chart with no check, and the old resolve rule put a patient on the single same-name chart whatever its birth date. The insurance check now holds
# such a chart with nothing bought and nothing added (claimocity_verify.py, 'same person?'); a plan added here - the Medicaid plan, or a Medigap plan of the feed that
# AdvancedMD's own check lets stand - would undo that: the next insurance check would find an active plan and release the chart's visits. So lookup_hold - the same
# text as there - judges first, once for a chart and feed patient, before the Medicaid check and before a plan of the feed is added; for 'same_person' this step asks
# nothing, adds nothing and registers nothing: one line for William (not_entered). Its other answer ('no_birth_date': no real birth date on either side) stops nothing
# here - unlike the look-up by name, a Medicaid check and a plan of the feed carry the patient's own number; they go on with what the feed sent, as before.
# _real_dob, _slip and _name_kind are the owner's rule as scripts/helpers/feed_identity.py states it (real_dob, slip, name_kind) - private copies here; the same text
# stands in claimocity_verify.py (and _real_dob, _slip in claimocity_import.py), and tools/selftest/test_pos_rule.py checks that they read the same. They are NOT
# drop-in equal to that module (the note above the copies in claimocity_verify.py says how: this helper's own shorter words for a slip, "far" for its empty answer).
# _dob8, _name_kind, _same_id, lookup_hold and lookup_who stand, the same text, in claimocity_verify.py (its paid look-up).
# SINCE THE SECOND REVIEW (11/25/2026 - step 4 of the header says what was found): a chart is ALSO known to be the feed's patient when a NUMBER proves it - the same
# nine-digit Social Security number on both sides, or a member number of the feed's insurance rows on one of the chart's plans (number_proof: the identity rule's own
# reading, taken from feed_identity.py beside this helper by identity_rule; the feed's numbers come from the raw files by feed_numbers, into memory only) and the chart's
# name is a name candidate of the feed's, as the rule's rule 4 asks. The last four alone free nobody, a number under another name frees nobody (the line says it is
# there), a plan the feed's own steps added - this step's among them - is never weighed (feed_added_plans: its number came from the feed itself), and two different
# Social Security numbers free nobody whatever else is in common. A feed patient is judged with EVERY record it comes with
# (lookup_judge), and on a chart that carries no birth date of its own the feed patients the map sends there are compared with each other (lookup_apart). William's
# standing word is asked through said_yes; what does not count in his file is named by same_person_gaps. All of these - with _show_id, _yes_entries and
# same_person_yes - stand, the same text, in claimocity_verify.py, and tools/selftest/test_pos_rule.py holds the two copies together letter for letter. chart_judge,
# further down, is this helper's own: it puts them together for one feed patient and its chart.
# SINCE ROUND 2 OF THAT REVIEW (11/25/2026): a MEMBER number in common is such a proof only where both sides carry a real birth date and the two are the same or a slip
# apart (_slip) - a family shares member numbers, and the chart that carries the number may be the husband's or the father's. With the dates far apart, or a date
# missing on either side, the chart keeps its line and the line says the number is there (lookup_hold). The Social Security number is weighed as before.
def _real_dob(d8, today8):
    """True when d8 is a REAL birth date (the owner's rule): 8 digits, a real calendar date, the year 1901 or later, not after today8 and not more than 120 years before
    it. Anything else - empty, the year-1900 placeholder, zeros, a day that does not exist - is NO BIRTH DATE. (The rule of real_dob in feed_identity.py.)"""
    d8 = str(d8 if d8 is not None else ""); today8 = str(today8 if today8 is not None else "")
    if not re.fullmatch(r"[0-9]{8}", d8) or not re.fullmatch(r"[0-9]{8}", today8) or d8[:4] < "1901": return False
    try: __import__("datetime").date(int(d8[:4]), int(d8[4:6]), int(d8[6:8]))
    except ValueError: return False
    return "%04d%s" % (int(today8[:4]) - 120, today8[4:]) <= d8 <= today8
def _slip(a8, b8):
    """How two REAL birth dates differ (the owner's rule) - the kind of slip, the first that fits: "one digit" (one digit differs), "two digits swapped" (two neighbouring
    digits swapped), "month and day swapped" (MMDD read as DDMM), "one day apart"; anything else is "far". "" when the two are the same date. (The rule of slip in
    feed_identity.py, in this helper's own shorter words; there far is the empty answer.)"""
    a8, b8 = str(a8), str(b8)
    if a8 == b8: return ""
    if len(a8) != 8 or len(b8) != 8: return "far"
    diff = [i for i in range(8) if a8[i] != b8[i]]
    if len(diff) == 1: return "one digit"
    if len(diff) == 2 and diff[1] == diff[0] + 1 and a8[diff[0]] == b8[diff[1]] and a8[diff[1]] == b8[diff[0]]: return "two digits swapped"
    if a8[:4] == b8[:4] and a8[4:6] == b8[6:8] and a8[6:8] == b8[4:6]: return "month and day swapped"
    try:
        day = __import__("datetime").date
        if abs((day(int(a8[:4]), int(a8[4:6]), int(a8[6:8])) - day(int(b8[:4]), int(b8[4:6]), int(b8[6:8]))).days) == 1: return "one day apart"
    except ValueError: pass
    return "far"
def _dob8(s):
    """A birth date as AdvancedMD writes it (MM/DD/YYYY, with or without leading zeros or a time behind it), as the feed writes it (YYYYMMDD, or longer with a time) or
    with dashes (YYYY-MM-DD) -> the 8 digits YYYYMMDD; "" for anything that cannot be read that way. It reads the shape only: whether the date is a REAL one is _real_dob's."""
    s = str(s if s is not None else "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return "%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m: return "".join(m.groups())
    x = re.sub(r"\D", "", s)
    return x[:8] if len(x) >= 8 else ""
def _name_kind(feed_last, feed_first, chart_last, chart_first, alike=False):
    """What a chart's name is to the feed's (the owner's rule for names, identity rule 2026-11-26.5): "full" - the SAME name: the same last name, the same first WORD of the
    first name (a middle initial or a second first name behind it does not matter) and the same suffix, or none; "name" - the same last name and the first names share their
    first three letters; "surname" - the same last name under another first name (or none); "" - another last name, or none. Last names are compared in upper case, letters
    only, without a trailing suffix word (JR, SR, II, III, IV, V); an accent is not a difference. The suffix of a name is one of those six words as the last word of the last
    name or as any word after the first word of the first name - but a lone V right behind the first word of the first name is a middle initial, not the suffix V (identity
    rule 2026-11-26.6: MARY V is MARY with an initial; V stays a suffix behind the last name and behind a middle name or initial). A name that is ALIKE BUT NOT THE SAME - the first word of one first name only begins the other's, or the two
    are one word and the suffixes differ (also when only one side carries one) - is "name" (until that version it was "full": a wife under a first name that begins with her
    husband's, a son of his father's name with JR); asked for it (alike=True) such a name is "alike", so that a hold can say what is true of it. (The rule of name_kind in
    feed_identity.py.)"""
    ud = __import__("unicodedata"); up = lambda s: "".join(c for c in ud.normalize("NFKD", str(s if s is not None else "")) if not ud.combining(c)).upper()
    sfx = ("JR", "SR", "II", "III", "IV", "V"); words = lambda s: re.findall(r"[A-Z]+", up(s))
    def key(s):
        w = words(s)
        return "".join(w[:-1] if len(w) > 1 and w[-1] in sfx else w)
    def suffix(last, first):      # the suffix words a name carries: the last word of the last name, any word after the first word of the first name - a lone V right behind the first word is a middle initial (identity rule .6)
        fw = [re.sub(r"[^A-Z]", "", x) for x in up(first).split()[1:]]; fw = fw[1:] if fw[:1] == ["V"] else fw
        return {w for w in (words(last)[-1:] if len(words(last)) > 1 else []) + fw if w in sfx}
    k = key(feed_last)
    if not k or k != key(chart_last): return ""
    a, b = re.sub(r"[^A-Z]", "", up(feed_first)), re.sub(r"[^A-Z]", "", up(chart_first))
    if not a or not b or a[:3] != b[:3]: return "surname"
    wa, wb = (re.sub(r"[^A-Z]", "", (up(x).split() or [""])[0]) for x in (feed_first, chart_first))
    if wa and wb and wa == wb and suffix(feed_last, feed_first) == suffix(chart_last, chart_first): return "full"
    return "alike" if alike and wa and wb and (wa.startswith(wb) or wb.startswith(wa)) else "name"
def _same_id(a, b):
    """True when a chart's additional number is this patient's Claimocity id: equal as upper-case letters and digits, and eight characters or more (the feed step and the
    old integration write the id there; an empty or short value is never one). (The evidence 'mrn' of feed_identity.py.)"""
    x, y = (re.sub(r"[^A-Z0-9]", "", str(v if v is not None else "").upper()) for v in (a, b))
    return len(x) >= 8 and x == y
def _show_id(i):
    """A Claimocity id as a printed line or a register may show it: its 24 hex characters - or fixed words in its place, because an id of another shape could be anything
    a sender typed. (show_id of feed_identity.py.)"""
    s = str(i if i is not None else "")
    return s if re.fullmatch(r"[0-9A-Fa-f]{24}", s) else "(an id that is not 24 hex characters)"
def identity_rule():
    """The identity rule's own module - feed_identity.py in the folder THIS helper stands in (the driver and the runbook copy the two together) - loaded for its reading
    of the numbers only (evidence, in1_member). None when the file is not there, is another file of that name or cannot be loaded: then no number proves anything and
    every hold stands as it did. Nothing is added to the loaded modules. It never raises."""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed_identity.py")
        if not os.path.isfile(p): return None
        iu = __import__("importlib.util").util; sp = iu.spec_from_file_location("feed_identity_beside", p); m = iu.module_from_spec(sp); sp.loader.exec_module(m)
        return m if all(callable(getattr(m, n, None)) for n in ("evidence", "in1_member")) else None
    except Exception: return None
def feed_numbers(folder, fi):
    """The feed's own Social Security and member numbers, by Claimocity id, from the RAW feed files of a folder (every file in it and under it; or the one file named):
    {id: {"ssn": [PID-19 as it was sent], "members": [the member number of each IN1 row - IN1-49, else IN1-36: fi.in1_member, the identity rule's reading]}}. The
    parsed feed message (feed_parsed_<stamp>.json) carries NEITHER number - the parse step leaves PID-19 out on purpose and keeps only the payer NAMES of the IN1 rows -
    so they are read here the way claimocity_match.py reads them: into memory only, never written, never printed. An id stands under PID-3 as it was sent and under its
    first component. fi = the identity rule's module (identity_rule); {} without it or without the folder, and a file that cannot be read is passed over: then no number
    proves anything. It never raises."""
    out = {}
    try:
        if fi is None or not folder or not os.path.exists(str(folder)): return out
        paths = [str(folder)] if os.path.isfile(str(folder)) else [os.path.join(d, f) for d, _s, fs in sorted(os.walk(str(folder))) for f in sorted(fs)]
    except Exception: return out
    for p in paths:
        try:
            cur = ()
            for line in open(p, errors="replace").read().replace("\r", "\n").split("\n"):
                s = line.split("|"); t = s[0].strip()
                if t == "MSH": cur = ()      # a message without a PID line never takes the numbers of the message before it
                elif t == "PID":
                    cur = tuple(k for k in dict.fromkeys((s[3], s[3].split("^")[0].strip()) if len(s) > 3 else ()) if k)
                    for k in cur:
                        e = out.setdefault(k, {"ssn": [], "members": []})
                        if len(s) > 19 and s[19].strip() and s[19] not in e["ssn"]: e["ssn"].append(s[19])
                elif t == "IN1" and cur:
                    n = fi.in1_member(s)
                    for k in cur:
                        if n and n not in out[k]["members"]: out[k]["members"].append(n)
        except Exception: continue
    return out
def feed_added_plans(folder="registers"):
    """The plans the feed's OWN steps put on each chart - {chart number: {plan ids}} - or None when nobody can say. A plan of the chart is proof by member number only
    when its number did not come from the feed itself: the intake adds a plan with the feed's own insurance row, and until 11/25/2026 the paid look-up was asked with the
    feed's name and birth date - so on a chart the patient map sends a feed patient to, such a plan carries that feed patient's number whoever the chart belongs to,
    and proves nothing about the chart (on 11/25/2026 the repository's registers listed about a hundred such plans). Read from the registers every bootstrapped workspace holds:
    feed_in1_intake.json (the intake - "ins" of each entry "<chart>|<carrier>"), feed_verify_<stamp>.json in the workspace and in the registers folder (the paid
    look-up - "discovery: added <carrier> plan -> ins123 ..."), feed_fixholds_<stamp>.json (the hand step - "added <carrier> seq 1 (ins123) ..."). A plan made with a
    NEW chart is not listed: that chart carries its patient's Claimocity id. A register that is not there adds nothing; one that cannot be read means nobody can say
    which plans the feed added: None - and then no member number proves anything in this run (number_proof). It never raises."""
    out = {}
    try:
        files = [os.path.join(folder, x) for x in (sorted(os.listdir(folder)) if os.path.isdir(folder) else []) if x == "feed_in1_intake.json" or (x.startswith(("feed_verify_", "feed_fixholds_")) and x.endswith(".json"))]
        files += [x for x in sorted(os.listdir(".")) if x.startswith("feed_verify_") and x.endswith(".json")]
        for f in files:
            with open(f) as fh: d = json.load(fh)
            for k, v in d.items():
                m = re.fullmatch(r"(?:pat)?0*([0-9]+)(?:\|.*)?", str(k))
                if not m or not isinstance(v, dict): continue
                ids = [v.get("ins")] + [i for x in (v.get("fixes") if isinstance(v.get("fixes"), list) else []) for i in re.findall(r"^(?:discovery: added \S+ plan -> |added \S+ seq \S+ \()(ins[0-9]+)", str(x))]
                out.setdefault(m.group(1), set()).update(i for i in ids if isinstance(i, str) and re.fullmatch(r"ins[0-9]+", i))
    except Exception: return None
    return out
def number_proof(fi, nums, pa, plans, own=None):
    """What the NUMBERS say about a chart and a feed patient, in ONE fixed word - the identity rule's own reading (fi.evidence; fi = feed_identity.py beside this helper,
    None when it is not there): "ssn" - the feed and the chart carry the same nine-digit Social Security number; "member" - a member number of the feed's insurance rows
    is the subscriber number of one of the chart's plans, open or ended; "contra" - the two sides carry two DIFFERENT Social Security numbers: proof of two people,
    whatever else they have in common; "" - nothing: no number on one side, only the last four in common (the weakest evidence frees nobody here), or no module.
    nums = the feed's own numbers for this Claimocity id ({"ssn": [...], "members": [...]} - feed_numbers), pa = the chart's own patient attributes (its ssn), plans =
    the chart's plan rows (id, subscribernum), own = the plan ids the feed's own steps added to this chart (feed_added_plans): such a plan is never weighed - its
    number came from the feed itself; None = nobody can say which plans those are, and then NO member number is weighed (the Social Security number still is).
    It works on the numbers and gives back the word only. It never raises: what cannot be weighed proves nothing."""
    try:
        if fi is None or not isinstance(nums, dict) or not isinstance(pa, dict): return ""
        subs = [] if own is None else [p.get("subscribernum") for p in (plans or []) if isinstance(p, dict) and p.get("subscribernum") and p.get("id") not in own]
        ev, contra = fi.evidence({"ssn": nums.get("ssn"), "members": nums.get("members")}, {"ssn": pa.get("ssn"), "members": subs})
        return "contra" if contra else "ssn" if "ssn" in ev else "member" if "member" in ev else ""
    except Exception: return ""
def lookup_hold(pa, first, last, dob8, fid="", today8=None, sure=False, proof="", apart=False):
    """Why a paid look-up of a chart is NOT asked - (key, words) - or ("", words) when it is asked (lookup_who says with what). pa = the chart's own patient attributes
    (name "LAST,FIRST ...", dob MM/DD/YYYY, additionalmrn when the answer carries it); first, last, dob8 = what the feed carries (first = the whole first name or its
    first word); fid = the patient's Claimocity id; sure = William's word that the chart is this patient; proof = what the NUMBERS say (number_proof: "ssn", "member",
    "contra" or ""); apart = another feed patient with a visit on this chart carries a birth date far from this one's (lookup_apart). The rule (11/25/2026, the review):
      "same_person" - nobody knows that the chart is the feed's patient: the two real birth dates are FAR apart; or they are a slip apart, or one side (or each) has no
          real one, AND the feed's name is not the chart's ("full" by _name_kind); or only the birth date is the same and BOTH names are others; or - the second review -
          the patient fits the chart by the name alone and stands apart from another feed patient of it. Not held when the chart carries the patient's Claimocity id
          (_same_id), when a number proves it, or on William's word - the second value then says which ("" when there was nothing to doubt). A number proves it the
          way the identity rule's rule 4 does (the second review: William was asked about a chart the rule itself had matched by the number): proof "ssn" or "member"
          AND a chart whose name is a name candidate of the feed's - the same last name and the first three letters of the first name ("name" or "full" by
          _name_kind). Under any other name a number in common frees nobody (a member number can be a whole family's) - the hold says it is there, for William.
          A MEMBER number proves it only with birth dates that AGREE (round 2 of that review: a husband's chart was freed for his wife and a father's for his son
          of the same name - a family shares member numbers): BOTH sides carry a real birth date and the two are the same or a slip apart. With the dates far
          apart, or a date missing on either side, it proves nothing: the hold stands and says the number is there. The Social Security number proves as before.
          Two DIFFERENT Social Security numbers (proof "contra") free nobody and are said behind the words, held or asked.
          Identity rule 2026-11-26.5 (a relative is not the patient): 'the chart's name' is the SAME name only - the same first word, no other suffix. A name that is
          ALIKE BUT NOT THE SAME (a first name that begins with the chart's, the chart's name with JR) is held like any other name, and the words say what is true of
          it: "... and the names are alike but not the same" - until then such a relative was asked about under the chart's person whenever a birth date was missing
          on one side or the two were a slip apart.
      "no_birth_date" - the chart is the patient, but neither side carries a real birth date: there is nothing to ask with (face sheet needed).
    A chart answer that shows no patient at all (neither a name nor a birth-date attribute - a read that failed) is not judged: ("", ""), the look-up is asked as before.
    The words are fixed - no name, no date, no number. It never raises: a comparison that cannot be made is held ("same_person")."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if "name" not in a and "dob" not in a: return "", ""
        cl, _, cf = __import__("html").unescape(str(a.get("name") or "")).partition(",")
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); cr = _real_dob(c8, today8); fr = _real_dob(f8, today8); kind = _name_kind(last, first, cl, cf, alike=True)
        names = " and the names are alike but not the same" if kind == "alike" else " and the names differ"      # (identity rule .5) what is true of the two names: a father and his son of one first name do not 'differ' by it
        if cr and fr and c8 == f8: why = "" if (kind or _name_kind("X", first, "X", cf) == "full") else "only the birth date is the same - both names differ"
        elif cr and fr and _slip(f8, c8) == "far": why = "Claimocity's birth date and this chart's are far apart"
        elif kind == "full": why = ""
        else: why = ("Claimocity's birth date is a slip from this chart's" if cr and fr else "one side carries no birth date" if cr or fr else "no birth date on either side") + names
        if apart and not why: why = "another Claimocity patient on this chart carries a birth date far from this one's and the chart carries none"
        known = _same_id(a.get("additionalmrn"), fid)
        proven = kind in ("name", "alike", "full") and (proof == "ssn" or (proof == "member" and cr and fr and _slip(f8, c8) != "far"))      # (round 2) a member number: only where both birth dates are real and the same or a slip apart
        num = "the chart and Claimocity carry the same Social Security number" if proof == "ssn" else "a plan of the chart carries a member number Claimocity sent" if proof == "member" else ""
        two = "the chart and Claimocity carry two different Social Security numbers" if proof == "contra" else ""
        if why and not (known or proven or sure): return "same_person", "same person? %s, and the chart's answer does not show this patient's Claimocity id%s" % (why, ("; " + (num or two)) if (num or two) else "")
        if not (cr or fr): return "no_birth_date", "neither Claimocity nor the chart carries a real birth date to ask with (face sheet needed)"
        how = "" if not why else "the chart carries this patient's Claimocity id" if known else num if proven else "William's word: same person"
        return "", "; ".join(x for x in (how, two) if x)
    except Exception:
        return "same_person", "same person? the chart's name and birth date could not be compared with Claimocity's"
def lookup_judge(pa, msgs, fid="", today8=None, sure=False, proof="", apart=False):
    """lookup_hold for ONE feed patient, asked with EVERY message a batch carries for its Claimocity id - (key, words, the message to ask with). msgs = [(first name, last
    name, birth date YYYYMMDD), ...]. 11/25/2026, the second review: one message was kept per id - the last one parsed - so a patient sent once with the chart's own birth
    date and once with a wrong one was held, or not, by the ORDER of the two messages. Now the patient is the chart's when ANY of its messages says so (the identity
    rule's way: a real date of the batch that is the chart's is enough); it is held 'same person?' only when NO message fits the chart, and 'no birth date' only when
    none of them can be asked with. Where the batch carries a real birth date for the id, that date stands for every message of it - again the rule's way: a message
    sent with the placeholder, or with no date, never counts as 'no birth date' beside a real one. The message to ask with is chosen by what it carries, never by its
    place in the file: the chart's own birth date before another real date, then by date and name; None when the patient is held 'same person?'. Two DIFFERENT real
    birth dates under one id are said behind the words; when the chart carries no real date of its own nobody knows which of the two to ask with - 'no birth date'
    (face sheet needed), as the identity rule writes a new chart with neither of them. apart = lookup_apart found this patient apart from another feed patient of the
    chart: handed on to lookup_hold for every message. It never raises: what cannot be judged is held ('same_person')."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        ms = sorted({tuple(str(x if x is not None else "") for x in (f, l, d)) for f, l, d in msgs}) or [("", "", "")]
        c8 = _dob8(a.get("dob")); real = sorted({_dob8(m[2]) for m in ms if _real_dob(_dob8(m[2]), today8)})
        if real: ms = sorted({(m[0], m[1], d) for m in ms for d in real})
        res = sorted(((lookup_hold(a, m[0], m[1], m[2], fid, today8, sure, proof, apart), m) for m in ms), key=lambda r: (0 if real and r[1][2] == c8 else 1, r[1]))
        ok = [r for r in res if not r[0][0]]; none = [r for r in res if r[0][0] == "no_birth_date"]
        if ok and len(real) > 1 and ("name" in a or "dob" in a) and not _real_dob(c8, today8):
            return "no_birth_date", "Claimocity sent two different birth dates for this patient and the chart carries none of its own - nobody knows which to ask with (face sheet needed)", ok[0][1]
        if ok: return "", "; ".join(x for x in (ok[0][0][1], "Claimocity sent two different birth dates for this patient" if len(real) > 1 else "") if x), ok[0][1]
        if none: return none[0][0][0], none[0][0][1], none[0][1]
        return res[0][0][0], res[0][0][1], None
    except Exception:
        return "same_person", "same person? the chart's name and birth date could not be compared with Claimocity's", None
def lookup_apart(pa, pats, today8=None):
    """The feed patients of ONE chart compared with EACH OTHER -> the positions in pats that stand APART from another one. pats = the messages of each feed patient with
    a visit on the chart, [[(first name, last name, birth date YYYYMMDD), ...], ...]. 11/25/2026, the second review: two feed patients of one name whose real birth
    dates are far apart were both put on the one same-name chart that carries NO birth date - each fits such a chart by the name alone - and the insurance check bought
    ONE look-up with the first one's date, added that plan and released both visits. Apart is a patient who carries a real birth date beside another feed patient of
    the chart whose real birth date is FAR from it - neither the same nor a slip. Only a chart that shows a patient and carries NO real birth date of its own is looked
    at: where the chart has one, lookup_hold has judged every patient against it. What it means is lookup_hold's (its apart): a patient who stands apart and is tied to
    the chart by no more than the name is held 'same person?'; one the chart is tied to - its Claimocity id, the same Social Security number, William's word - is
    asked, and the words say which (a member number ties nobody to a chart that carries no birth date: round 2 of that review). So two such patients are both held,
    and one beside a patient the chart is tied to is held alone. It never raises: when the comparison cannot be made every patient stands apart."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if ("name" not in a and "dob" not in a) or _real_dob(_dob8(a.get("dob")), today8): return set()
        real = [sorted({_dob8(m[2]) for m in ms if _real_dob(_dob8(m[2]), today8)}) for ms in pats]
        far = lambda x, y: bool(x) and bool(y) and not any(_slip(p, q) != "far" for p in x for q in y)
        return {n for n in range(len(pats)) if any(far(real[n], real[m]) for m in range(len(pats)) if m != n)}
    except Exception:
        return set(range(len(pats))) if isinstance(pats, (list, tuple)) else set()
def _yes_entries(pairs):
    """The entries of William's standing file read STRICTLY -> ([(chart number, {"feed_ids": [ids]}) for every entry that counts], [(its chart as "pat<number>" - "" when
    the key is not one chart, why it does not count or not in full)]). pairs = the file's (key, value) pairs as they stand in it: a chart named twice comes twice, and
    both entries count. 11/25/2026, the review of the standing word: a key was squeezed to its digits ("pat1, pat2" counted for chart 12), any text in approved_by was his
    yes (also one that says no), and an id in another case, with a blank beside it or sharing its text with a second id was dropped without a word. Now an entry counts
    when its key is exactly ONE chart (pat123 or 123, in any case, blanks around it), approved_by is his word in its own form - William, the day as MM/DD/YYYY, alone or
    with (board) or (chat) behind it: never a name, a card id or a no - and feed_ids is a list that names at least one Claimocity id. An id is read as upper-case
    letters and digits, so the same id in another case or with a blank beside it is that id, and two ids in one text are two ids. The whys are fixed words: nothing of
    the file is copied into them. It never raises: an entry that cannot be read does not count."""
    good, bad = [], []
    for k, v in pairs:
        num = ""; why = ""
        try:
            m = re.fullmatch(r"\s*(?:pat)?\s*0*([0-9]+)\s*", k, re.I) if isinstance(k, str) else None; num = m.group(1) if m else ""
            e = dict(v[1]) if isinstance(v, tuple) else None
            if not num: why = "its key is not one chart"
            elif e is None: why = "it is no entry with feed_ids and approved_by"
            elif not (isinstance(e.get("approved_by"), str) and re.fullmatch(r"William\s+(0?[1-9]|1[0-2])/(0?[1-9]|[12][0-9]|3[01])/20[0-9]{2}(\s+\((board|chat)\))?", e["approved_by"].strip(), re.I)):
                why = "approved_by is not his word in the form William MM/DD/YYYY - alone or with (board) or (chat) behind it"
            elif not isinstance(e.get("feed_ids"), list): why = "feed_ids is not a list"
            else:
                ids = [x.upper() for i in e["feed_ids"] if isinstance(i, str) for x in re.findall(r"[A-Za-z0-9]+", i)]
                if not ids: why = "feed_ids names no Claimocity id"
                else:
                    good.append((num, {"feed_ids": ids}))
                    if any(not isinstance(i, str) or not re.search(r"[A-Za-z0-9]", i) for i in e["feed_ids"]): why = "one of its feed_ids is no Claimocity id - the others count"
        except Exception: why = why or "it could not be read"
        if why: bad.append((("pat" + num) if num else "", why))
    return good, bad
def same_person_gaps(path="registers/feed_same_person.json"):
    """What in William's standing file does NOT count -> (ONE line to print, or ""; {chart number: why} for the entries whose key is one chart). 11/25/2026, the review of
    the standing word: an entry the readers did not take was dropped without a word - his kept yes was silently not kept, and the next batch asked him again. The line
    begins SAME PERSON FILE: and says TOP OF THE REPORT; it names a chart only as pat<number> and gives each why in fixed words (_yes_entries) - a key that is not one
    chart is counted, never printed: it could be anything a person typed. A file that is not there gives no line; one that cannot be read is said by same_person_yes.
    It never raises."""
    try:
        if not os.path.exists(path): return "", {}
        with open(path) as fh: d = json.load(fh, object_pairs_hook=lambda p: ("object", p))
        bad = _yes_entries(d[1])[1] if isinstance(d, tuple) else []
    except Exception: return "", {}
    if not bad: return "", {}
    named = ["%s (%s)" % (c, w) for c, w in bad if c]; odd = sum(1 for c, _w in bad if not c)
    said = "; ".join(named[:20] + (["%d more" % (len(named) - 20)] if len(named) > 20 else []) + (["%d with a key that is not one chart" % odd] if odd else []))
    return ("SAME PERSON FILE: %d entr%s of %s do%s not count, or not in full - TOP OF THE REPORT - William's word is NOT kept there and such a chart is asked about again: %s. An entry reads "
            "{\"pat<chart>\": {\"feed_ids\": [\"<one Claimocity id in each pair of quotes>\"], \"approved_by\": \"William MM/DD/YYYY (board)\"}}; for a chart that is already in the file the new id is "
            "added to its list - on main, on his word." % (len(bad), "y" if len(bad) == 1 else "ies", path, "es" if len(bad) == 1 else "", said)), {c[3:]: w for c, w in bad if c}
def said_yes(yes, chart, fid):
    """True when William's standing word (yes = what same_person_yes read) names this chart AND this Claimocity id: the chart by its number, with or without "pat" in
    front; the id as upper-case letters and digits, the way _yes_entries reads the file's. It never raises: what cannot be asked is no yes."""
    try: return re.sub(r"[^A-Z0-9]", "", str(fid if fid is not None else "").upper()) in yes.get(re.sub(r"\D", "", str(chart)).lstrip("0") or "0", ())
    except Exception: return False
def same_person_yes(path="registers/feed_same_person.json"):
    """William's STANDING word that a chart is a feed patient (11/25/2026): {"pat123": {"feed_ids": [the Claimocity ids his yes is about], "approved_by": his word and its
    date}}. The file's home is the repository (practices/ehpa/registers/); it is written only on his word, and the ingest copies it into the workspace. His yes counts for
    that chart AND that Claimocity id only. -> ({chart number: {Claimocity ids}}, a line to print or ""). The entries are read strictly (_yes_entries, since the review of
    the standing word): one that does not count frees nobody and is named by same_person_gaps - never dropped without a word; a chart the file names twice keeps both
    lists. A file that cannot be read counts for nobody and is said here. Whether his word names a chart and an id is asked with said_yes. It never raises."""
    try:
        if not os.path.exists(path): return {}, ""
        with open(path) as fh: d = json.load(fh, object_pairs_hook=lambda p: ("object", p))
        if not isinstance(d, tuple): raise ValueError("no JSON object")
    except Exception as e:
        return {}, "SAME PERSON FILE: %s could not be read (%s) - nobody's standing word counts in this run; a chart held 'same person?' stays held" % (path, type(e).__name__)
    out = {}
    for num, v in _yes_entries(d[1])[0]:
        if num and isinstance(v.get("feed_ids"), list):
            ids = {i for i in v["feed_ids"] if isinstance(i, str) and i}
            if ids: out.setdefault(num, set()).update(ids)
    return out, ""
def lookup_who(pa, first, last, dob8, today8=None, what="look-up"):
    """Whom a paid look-up of a chart is asked about: (first name, last name, birth date YYYYMMDD, words). pa = the chart's own patient attributes as AdvancedMD's
    getdemographic answer gives them (name "LAST,FIRST ...", dob MM/DD/YYYY) - the answer the caller already holds, so this costs no call. first, last, dob8 = what the
    feed carries - first the WHOLE first name (identity rule 2026-11-26.6, the identity check's finding B1: the callers handed over its first word only, and the same name
    with JR behind the first name on both sides read 'alike but not the same'); the names are compared with it, and the feed's name is asked with its first word. When
    the chart's birth date is a REAL one (_real_dob) and its name can be read, the answer is the CHART's first name (its first word), last name and birth date; else it
    is the feed's values as they were passed, the first name cut to its first word - never a mix of the two. words = which one was asked and how the other differs, in fixed
    words that carry no name and no date (a slip is named by its kind; another first name under the same last name, or another last name, is said behind them - 11/25/2026,
    the review; a name that is alike but not the same as the chart's says so, in the place of 'the first names differ' - identity rule 2026-11-26.5); they begin with `what` ("look-up", "Medicaid") and go into registers and reports. A chart answer that shows no patient at all (a read that failed) leaves
    the feed's values and says the chart could not be read - never that it has no birth date. Whether the look-up is asked at all is lookup_hold's.
    It never raises: whatever cannot be compared leaves the feed's values, and the words say so."""
    fw = (str(first).strip().split() or [""])[0] if first is not None else first      # (identity rule .6) the feed's name is asked with the first word of its first name
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if "name" not in a and "dob" not in a: return fw, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be read" % what
        cl, _, cn = __import__("html").unescape(str(a.get("name") or "")).partition(","); cl = cl.strip(); cf = cn.strip().split(" ")[0]
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); fr = _real_dob(f8, today8)
        kind = _name_kind(last, first, cl, cn, alike=True) if (cl and cf) else "full"
        names = "" if kind == "full" else "; the names are alike but not the same" if kind == "alike" else "; the first names differ" if kind else "; the last names differ"
        if _real_dob(c8, today8):
            if not (cl and cf): return fw, last, dob8, "%s asked with Claimocity's name and birth date; the chart's name could not be read" % what
            return cf, cl, c8, "%s asked with the chart's birth date; %s%s" % (what, ("Claimocity's is the same" if f8 == c8 else "Claimocity's differs: " + _slip(f8, c8)) if fr else "no birth date from Claimocity", names)
        return fw, last, dob8, ("%s asked with Claimocity's birth date; the chart has no birth date of its own" if fr else "%s asked with what Claimocity sent; no birth date on either side") % what + names
    except Exception:
        return fw, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be compared" % what
def not_entered(pid, words, said, fid=""):
    """The ONE line for a chart nobody knows to be this feed patient's (lookup_judge: 'same_person') - printed and counted once for that feed patient and chart, however
    many insurance blocks the feed carries for it. Since the second review of 11/25/2026 it names the Claimocity id in doubt (in its own shape, behind the words that
    were there before) and says when William's standing file has an entry for the chart that does not count. Nothing is asked, nothing is entered, nothing is
    registered. -> True (it has been said)."""
    if not said:
        gap = SAME_GAPS.get(str(pid).lstrip("0") or "0")
        print("  pat%s: feed insurance not entered - %s - for William; nothing asked, nothing added (Claimocity id %s%s)" % (
            pid, words, _show_id(fid), ("; his standing file has an entry for this chart that does not count: %s" % gap) if gap else "")); tally["same person? feed insurance not entered (for William)"] += 1
    return True
def who3(p):      # one record's patient as lookup_judge takes it: (the whole first name, the last name, the birth date as 8 digits)
    return str(p.get("first") or ""), str(p.get("last") or ""), re.sub(r"\D", "", str(p.get("dob") or ""))
def chart_judge(fid, pid, cpat, plans):
    """Whether the feed's insurance may be asked about and entered for ONE feed patient on its chart - lookup_judge's answer (key, words, the record to ask with) - with
    everything the second review of 11/25/2026 added: EVERY record the patient comes with (whos); what the numbers prove (the chart's own as they were read before this
    run added anything, the feed's from the raw files); William's word for the run or his standing word; and the other feed patients the map sends to the same chart -
    on a chart with no birth date of its own, one whose real birth date is far from another's stands apart (lookup_apart) and is left for William unless the chart is
    tied to it by more than the name."""
    mine = [who3(x) for x in (whos.get(fid) or [{}])]
    mates = [[who3(x) for x in whos[f]] for f in whos if f != fid and re.sub(r"\D", "", str(PMAP.get(f, "") or "")) == pid]
    own = None if OWN is None else OWN.get(pid.lstrip("0") or "0", set()) | {e.get("ins") for k, e in REG.items() if k.startswith(pid + "|") and isinstance(e, dict) and e.get("ins")}      # the plans the feed's own steps put on this chart - this run's included: never weighed
    return lookup_judge(cpat, mine, fid, sure=pid in SAME or said_yes(SAME_YES, pid, fid), proof=number_proof(FI, NUMS.get(fid), cpat, plans, own), apart=0 in lookup_apart(cpat, [mine] + mates))
def keep_refusal(pid, code, answer):
    """AdvancedMD's own answer to a plan it refused - kept under patient_db/<chart>/ in this workspace (patient data: the workspace and the Drive bundle only, never the
    repository) and never printed: it can name a member number or a patient. It never raises."""
    try:
        os.makedirs("patient_db/%s" % pid, exist_ok=True)
        json.dump({"carrier": code, "answer": str(answer)[:400], "stamp": STAMP}, open("patient_db/%s/addinsurance_refused_%s.json" % (pid, datetime.date.today().strftime("%Y%m%d")), "w"))
    except Exception: pass
recs = adt_ingest.read([DIR]); feed = collections.defaultdict(dict); whos = collections.defaultdict(list)      # whos (11/25/2026, the second review): EVERY record's patient of a Claimocity id - until then only the last one read was kept, and 'same person?' was judged by that one alone
for r in recs:
    fid = r["patient"].get("id"); whos[fid].append(r["patient"])
    for b in r["insurance"]:
        if not b["skip"] and b["member"]: feed[fid][(b["name"], b["member"])] = b
SAME_YES, _syl = same_person_yes()
if _syl: print(_syl)
_syg, SAME_GAPS = same_person_gaps()      # 11/25/2026 (the second review): what in his file does NOT count is said in ONE line here, and on the line of a chart it names - never dropped without a word
if _syg: print(_syg)
FI = identity_rule(); NUMS = feed_numbers(DIR, FI)      # the identity rule's own reading of the numbers (feed_identity.py beside this helper) and the feed's own numbers by Claimocity id, from the raw files - in memory only; without either no number proves anything
OWN = feed_added_plans()      # the plans the feed's own steps put on each chart (the registers say which): their numbers came from the feed itself and are never weighed
if OWN is None: print("PLAN ORIGIN: a feed register here could not be read, so nobody can say which plans the feed itself added - no member number proves anything in this run (a Social Security number still does); a chart that gets the line 'same person?' keeps it")
amd.login_cached(); done = 0; tally = collections.Counter()
print("feed files in %s: %d messages, %d patients with a usable insurance block%s" % (DIR, len(recs), len(feed), "" if LIVE else "  (DRY RUN - nothing is written)"))
for fid, blocks in feed.items():
    pid = re.sub(r"\D", "", PMAP.get(fid, ""))
    if not pid: tally["no chart yet"] += 1; continue
    r, plans, order = ins_update._plans(pid); plans = list(plans.values()); plans0 = plans      # plans0: the chart's plans as they stand BEFORE this run adds anything - the only ones a number is weighed against (a plan this step adds from the feed's own number proves nothing)
    _pt = re.search(r'<patient [^>]*>', r or ""); cpat = dict(re.findall(r'(\w+)="([^"]*)"', _pt.group(0))) if _pt else {}      # 11/25/2026: the chart's own patient attributes (its name, its birth date) from the answer just read - no extra call (lookup_who)
    have = {p.get("carrier") for p in plans}; live_codes = {CAR2CODE.get(p.get("carrier")) for p in plans if not p.get("enddate")}
    live_medicaid = bool((live_codes & fpm.MEDICAID_FAMILY) or any(CAR2CODE.get(p.get("carrier")) == "HUM01" and len(norm(p.get("subscribernum"))) == 10 and norm(p.get("subscribernum")).isdigit() for p in plans if not p.get("enddate")))
    asked_medicaid = False; _hold = None; _said = False      # 11/25/2026 (review): _hold = the judgement for this chart and feed patient (chart_judge: lookup_hold over every record of the patient, the numbers, the other feed patients of the chart), asked once - when a plan would be asked about or entered
    for (name, member), b in blocks.items():
        code = fpm.code(name); kind = fpm.kind(name, code)
        if not code or code not in CODE2CAR: tally["name not in the table"] += 1; continue
        if kind == "ltc": tally["long-term-care-only plan (not the physician's payer)"] += 1; continue
        if CODE2CAR[code] in have: tally["already on the chart"] += 1; continue
        key = "%s|%s" % (pid, code)
        if key in REG and REG[key].get("outcome", "").startswith(("added", "not active", "listed")): tally["settled by an earlier run"] += 1; continue
        if kind == "primary":
            REG[key] = {"outcome": "listed - the feed names another primary plan (%s); the dated check decides" % code, "stamp": STAMP}; tally["another PRIMARY named by the feed (listed for the cascade)"] += 1
            print("  pat%s: feed names %s as a plan the chart does not hold - primary plans are decided by the dated eligibility check, not entered here" % (pid, code)); continue
        if kind == "medicaid":
            if live_medicaid: REG[key] = {"outcome": "listed - the chart already has an open Medicaid-family plan; feed says %s" % code, "stamp": STAMP}; tally["chart already has a Medicaid plan (listed)"] += 1; continue
            if asked_medicaid: continue
            if not re.fullmatch(r"\d{10}", norm(member)): tally["Medicaid row without a 10-digit Medicaid number"] += 1; continue
            if done >= MAX: tally["over this run's limit (next run)"] += 1; continue
            asked_medicaid = True
            # 11/25/2026 (the review, WHEN NOTHING IS ENTERED above): a chart nobody knows to be this feed patient's is not asked about and gets no plan on this step's
            # own word - one line for William, no check bought, no register entry (the next run judges it again; William's word for a run: --same-person)
            _hold = _hold or chart_judge(fid, pid, cpat, plans0)
            if _hold[0] == "same_person": _said = not_entered(pid, _hold[1], _said, fid); continue
            done += 1
            # 11/25/2026 (William, WHOM MEDICAID IS ASKED ABOUT above): the chart's own name and birth date when the chart's birth date is a real one, else the feed's as
            # before - of the record the judgement chose by what it carries (the second review: never by its place in the files)
            _mf, _ml, _md, _how = lookup_who(cpat, _hold[2][0], _hold[2][1], _hold[2][2], what="Medicaid")      # (identity rule .6, finding B1) the WHOLE first name: lookup_who compares the names with it and cuts the first word itself
            if _hold[1] and not _hold[0]: _how += "; " + _hold[1]      # the Claimocity id on the chart, a number in common, or William's word, let it be asked: said with the rest
            elif _hold[0] == "no_birth_date" and _hold[1].startswith("Claimocity sent two different birth dates"):
                # (the second review) ONE feed patient came with two different real birth dates and the chart carries none of its own. 'no_birth_date' stops nothing
                # here (the note above), so Medicaid is asked as before with what the feed sent - with ONE of the two dates, chosen by what the records carry (never by
                # the order of the files) - and the line and the register entry SAY that there were two: nobody knows which is right until the chart has its own.
                _how += "; Claimocity sent two different birth dates for this patient and the chart carries none of its own - Medicaid was asked with one of them (face sheet needed)"
            status, scode, text = medicaid_answer(_mf, _ml, _md, norm(member), pid)
            if not _how.endswith("is the same"): text = "%s - %s" % (text, _how)      # which one was asked, in fixed words: into the printed line and the register entry
            if status == "unknown": print("  pat%s: %s - nothing added, asked again next run" % (pid, text)); tally["Medicaid could not answer (next run)"] += 1; continue
            if status == "inactive": REG[key] = {"outcome": "not active - " + text, "stamp": STAMP}; print("  pat%s: %s - nothing added" % (pid, text)); tally["Medicaid not active (nothing added)"] += 1; continue
            use = scode if scode in CODE2CAR else code
            if CODE2CAR[use] in have: REG[key] = {"outcome": "listed - the state names %s, already on the chart" % use, "stamp": STAMP}; tally["already on the chart"] += 1; continue
            fin = "MD"
        else:
            use = code; text = "feed block '%s'" % name[:30]; fin = "CC"
            if done >= MAX: tally["over this run's limit (next run)"] += 1; continue
            _hold = _hold or chart_judge(fid, pid, cpat, plans0)      # 11/25/2026 (review): the same judgement for a plan the feed names
            if _hold[0] == "same_person": _said = not_entered(pid, _hold[1], _said, fid); continue
            if _hold[1] and not _hold[0]: text += " - " + _hold[1]      # the Claimocity id on the chart, a number in common, or William's word, let it be entered: said in the register entry
            done += 1
        if LIVE: _r, _pl, order = ins_update._plans(pid); plans = list(_pl.values())      # 11/19/2026: read the order again - a second plan added on the same chart must not drop the first from it
        seqs = [s for s in (order or "").replace(" ", "").split(",") if s]
        if not LIVE:
            print("  pat%s: DRY would add %s (%s) and %s" % (pid, use, text, "append it to the order %s" % order if 1 <= len(seqs) <= 2 else "leave the order %r" % order)); tally["would add %s" % ("a Medicaid plan" if kind == "medicaid" else "a secondary plan")] += 1; continue
        insid, seq = add_ins.add(pid, CODE2CAR[use], norm(member) if kind == "medicaid" else member, "01/01/%d" % datetime.date.today().year, "1", fin)
        if not (isinstance(insid, str) and re.fullmatch(r"ins[0-9]+", insid)):
            # 11/25/2026 (the second review): AdvancedMD refused the plan - add_ins answers (None, AdvancedMD's own words). Until then those words were printed here
            # ("add ... FAILED <words>"), and a printed line travels: they can name the member number or a patient. Now the line says it in fixed words and the answer
            # stays in the workspace (keep_refusal). Nothing is registered, so the next run tries again.
            keep_refusal(pid, use, seq)
            print("  pat%s: %s was NOT added - AdvancedMD refused the plan (its own answer is not printed: it can name a member number - it is kept under patient_db/%s/ in this workspace); tried again next run" % (pid, use, pid)); tally["add failed"] += 1; continue
        time.sleep(0.4); msg = "added %s as %s seq %s (%s)" % (use, insid, seq, text)
        if kind != "medicaid":
            try: s = elig_amd.run_plan(pid, insid.replace("ins", ""), True); st = str(s.get("status") or "")
            except Exception as e: st = "check failed %s" % type(e).__name__
            if st.upper().startswith(("INACTIVE", "REJECTED")):
                ins_update.update(pid, insid, enddate="01/01/%d" % datetime.date.today().year)
                REG[key] = {"outcome": "not active - AdvancedMD's check on the feed's %s answered %s; plan ended again" % (use, st[:40]), "ins": insid, "stamp": STAMP}
                print("  pat%s: %s - but AdvancedMD's check answered %s: ended again" % (pid, msg, st[:40])); tally["secondary not active (ended again)"] += 1; continue
            msg += "; AdvancedMD 271 %s" % st[:30]
        if 1 <= len(seqs) <= 3 and seq not in seqs:
            first = [p["id"] for p in plans if p.get("sequence") == seqs[0]]
            medicaid_seqs = [x for x in seqs[1:] if any(p.get("sequence") == x and CAR2CODE.get(p.get("carrier")) in fpm.MEDICAID_FAMILY for p in plans)]
            new = [x for x in seqs if x not in medicaid_seqs] + ([str(seq)] + medicaid_seqs if kind != "medicaid" else medicaid_seqs + [str(seq)])      # Medicare / Advantage, then Medigap, Medicaid last
            if first:
                ok, m2 = ins_update.update(pid, first[0], sequence=",".join(new)); msg += "; order %s -> %s (%s)" % (order, ",".join(new), "ok" if ok else "NOT set: " + m2[:60])
        REG[key] = {"outcome": msg, "ins": insid, "stamp": STAMP}; print("  pat%s: %s" % (pid, msg)); tally["added %s" % ("a Medicaid plan" if kind == "medicaid" else "a secondary plan")] += 1
        json.dump(REG, open(REGF, "w"), indent=1); time.sleep(0.3)
    time.sleep(0.1)
if LIVE: json.dump(REG, open(REGF, "w"), indent=1)
print("RESULT feed insurance intake %s: %s" % (STAMP, "; ".join("%s %d" % (k, v) for k, v in sorted(tally.items()))))
