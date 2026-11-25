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
def _name_kind(feed_last, feed_first, chart_last, chart_first):
    """What a chart's name is to the feed's (the owner's rule for names): "full" - the same last name, and the first word of the first name is the same or the shorter of the
    two first words has four letters or more and begins the longer one (MARY / MARYANN); "name" - the same last name and the first names share their first three letters;
    "surname" - the same last name under another first name (or none); "" - another last name, or none. Last names are compared in upper case, letters only, without a
    trailing suffix word (JR, SR, II, III, IV, V); an accent is not a difference. (The rule of name_kind in feed_identity.py.)"""
    ud = __import__("unicodedata"); up = lambda s: "".join(c for c in ud.normalize("NFKD", str(s if s is not None else "")) if not ud.combining(c)).upper()
    def key(s):
        w = re.findall(r"[A-Z]+", up(s))
        return "".join(w[:-1] if len(w) > 1 and w[-1] in ("JR", "SR", "II", "III", "IV", "V") else w)
    k = key(feed_last)
    if not k or k != key(chart_last): return ""
    a, b = re.sub(r"[^A-Z]", "", up(feed_first)), re.sub(r"[^A-Z]", "", up(chart_first))
    if not a or not b or a[:3] != b[:3]: return "surname"
    wa, wb = (re.sub(r"[^A-Z]", "", (up(x).split() or [""])[0]) for x in (feed_first, chart_first))
    return "full" if wa and wb and (wa == wb or (min(len(wa), len(wb)) >= 4 and (wa.startswith(wb) or wb.startswith(wa)))) else "name"
def _same_id(a, b):
    """True when a chart's additional number is this patient's Claimocity id: equal as upper-case letters and digits, and eight characters or more (the feed step and the
    old integration write the id there; an empty or short value is never one). (The evidence 'mrn' of feed_identity.py.)"""
    x, y = (re.sub(r"[^A-Z0-9]", "", str(v if v is not None else "").upper()) for v in (a, b))
    return len(x) >= 8 and x == y
def lookup_hold(pa, first, last, dob8, fid="", today8=None, sure=False):
    """Why a paid look-up of a chart is NOT asked - (key, words) - or ("", words) when it is asked (lookup_who says with what). pa = the chart's own patient attributes
    (name "LAST,FIRST ...", dob MM/DD/YYYY, additionalmrn when the answer carries it); first, last, dob8 = what the feed carries (first = the whole first name or its
    first word); fid = the patient's Claimocity id; sure = William's word that the chart is this patient. The rule (11/25/2026, the review):
      "same_person" - nobody knows that the chart is the feed's patient: the two real birth dates are FAR apart; or they are a slip apart, or one side (or each) has no
          real one, AND the feed's name is not the chart's ("full" by _name_kind); or only the birth date is the same and BOTH names are others. Not held when the chart
          carries the patient's Claimocity id (_same_id) or on William's word - the second value then says which ("" when there was nothing to doubt).
      "no_birth_date" - the chart is the patient, but neither side carries a real birth date: there is nothing to ask with (face sheet needed).
    A chart answer that shows no patient at all (neither a name nor a birth-date attribute - a read that failed) is not judged: ("", ""), the look-up is asked as before.
    The words are fixed - no name, no date, no number. It never raises: a comparison that cannot be made is held ("same_person")."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if "name" not in a and "dob" not in a: return "", ""
        cl, _, cf = __import__("html").unescape(str(a.get("name") or "")).partition(",")
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); cr = _real_dob(c8, today8); fr = _real_dob(f8, today8); kind = _name_kind(last, first, cl, cf)
        if cr and fr and c8 == f8: why = "" if (kind or _name_kind("X", first, "X", cf) == "full") else "only the birth date is the same - both names differ"
        elif cr and fr and _slip(f8, c8) == "far": why = "Claimocity's birth date and this chart's are far apart"
        elif kind == "full": why = ""
        else: why = ("Claimocity's birth date is a slip from this chart's" if cr and fr else "one side carries no birth date" if cr or fr else "no birth date on either side") + " and the names differ"
        known = _same_id(a.get("additionalmrn"), fid)
        if why and not (known or sure): return "same_person", "same person? %s, and the chart's answer does not show this patient's Claimocity id" % why
        if not (cr or fr): return "no_birth_date", "neither Claimocity nor the chart carries a real birth date to ask with (face sheet needed)"
        return "", ("" if not why else "the chart carries this patient's Claimocity id" if known else "William's word: same person")
    except Exception:
        return "same_person", "same person? the chart's name and birth date could not be compared with Claimocity's"
def lookup_who(pa, first, last, dob8, today8=None, what="look-up"):
    """Whom a paid look-up of a chart is asked about: (first name, last name, birth date YYYYMMDD, words). pa = the chart's own patient attributes as AdvancedMD's
    getdemographic answer gives them (name "LAST,FIRST ...", dob MM/DD/YYYY) - the answer the caller already holds, so this costs no call. first, last, dob8 = what the
    feed carries. When the chart's birth date is a REAL one (_real_dob) and its name can be read, the answer is the CHART's first name (its first word), last name and
    birth date; else it is the feed's three values exactly as they were passed - never a mix of the two. words = which one was asked and how the other differs, in fixed
    words that carry no name and no date (a slip is named by its kind; another first name under the same last name, or another last name, is said behind them - 11/25/2026,
    the review); they begin with `what` ("look-up", "Medicaid") and go into registers and reports. A chart answer that shows no patient at all (a read that failed) leaves
    the feed's values and says the chart could not be read - never that it has no birth date. Whether the look-up is asked at all is lookup_hold's.
    It never raises: whatever cannot be compared leaves the feed's values, and the words say so."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if "name" not in a and "dob" not in a: return first, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be read" % what
        cl, _, cn = __import__("html").unescape(str(a.get("name") or "")).partition(","); cl = cl.strip(); cf = cn.strip().split(" ")[0]
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); fr = _real_dob(f8, today8)
        kind = _name_kind(last, first, cl, cn) if (cl and cf) else "full"; names = "" if kind == "full" else "; the first names differ" if kind else "; the last names differ"
        if _real_dob(c8, today8):
            if not (cl and cf): return first, last, dob8, "%s asked with Claimocity's name and birth date; the chart's name could not be read" % what
            return cf, cl, c8, "%s asked with the chart's birth date; %s%s" % (what, ("Claimocity's is the same" if f8 == c8 else "Claimocity's differs: " + _slip(f8, c8)) if fr else "no birth date from Claimocity", names)
        return first, last, dob8, ("%s asked with Claimocity's birth date; the chart has no birth date of its own" if fr else "%s asked with what Claimocity sent; no birth date on either side") % what + names
    except Exception:
        return first, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be compared" % what
def not_entered(pid, words, said):
    """The ONE line for a chart nobody knows to be this feed patient's (lookup_hold: 'same_person') - printed and counted once for the chart, however many insurance
    blocks the feed carries for it. Nothing is asked, nothing is entered, nothing is registered. -> True (it has been said)."""
    if not said: print("  pat%s: feed insurance not entered - %s - for William; nothing asked, nothing added" % (pid, words)); tally["same person? feed insurance not entered (for William)"] += 1
    return True
recs = adt_ingest.read([DIR]); feed = collections.defaultdict(dict); who = {}
for r in recs:
    fid = r["patient"].get("id"); who[fid] = r["patient"]
    for b in r["insurance"]:
        if not b["skip"] and b["member"]: feed[fid][(b["name"], b["member"])] = b
amd.login_cached(); done = 0; tally = collections.Counter()
print("feed files in %s: %d messages, %d patients with a usable insurance block%s" % (DIR, len(recs), len(feed), "" if LIVE else "  (DRY RUN - nothing is written)"))
for fid, blocks in feed.items():
    pid = re.sub(r"\D", "", PMAP.get(fid, ""))
    if not pid: tally["no chart yet"] += 1; continue
    r, plans, order = ins_update._plans(pid); plans = list(plans.values())
    _pt = re.search(r'<patient [^>]*>', r or ""); cpat = dict(re.findall(r'(\w+)="([^"]*)"', _pt.group(0))) if _pt else {}      # 11/25/2026: the chart's own patient attributes (its name, its birth date) from the answer just read - no extra call (lookup_who)
    have = {p.get("carrier") for p in plans}; live_codes = {CAR2CODE.get(p.get("carrier")) for p in plans if not p.get("enddate")}
    live_medicaid = bool((live_codes & fpm.MEDICAID_FAMILY) or any(CAR2CODE.get(p.get("carrier")) == "HUM01" and len(norm(p.get("subscribernum"))) == 10 and norm(p.get("subscribernum")).isdigit() for p in plans if not p.get("enddate")))
    asked_medicaid = False; _hold = None; _said = False      # 11/25/2026 (review): _hold = lookup_hold's answer for this chart and feed patient, asked once - when a plan would be asked about or entered
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
            p = who.get(fid, {}); asked_medicaid = True
            # 11/25/2026 (the review, WHEN NOTHING IS ENTERED above): a chart nobody knows to be this feed patient's is not asked about and gets no plan on this step's
            # own word - one line for William, no check bought, no register entry (the next run judges it again; William's word for a run: --same-person)
            _hold = _hold or lookup_hold(cpat, p.get("first", ""), p.get("last", ""), re.sub(r"\D", "", p.get("dob", "")), fid, sure=pid in SAME)
            if _hold[0] == "same_person": _said = not_entered(pid, _hold[1], _said); continue
            done += 1
            # 11/25/2026 (William, WHOM MEDICAID IS ASKED ABOUT above): the chart's own name and birth date when the chart's birth date is a real one, else the feed's as before
            _mf, _ml, _md, _how = lookup_who(cpat, p.get("first", "").split()[0] if p.get("first") else "", p.get("last", ""), re.sub(r"\D", "", p.get("dob", "")), what="Medicaid")
            if _hold[1] and not _hold[0]: _how += "; " + _hold[1]      # the Claimocity id on the chart, or William's word, let it be asked: said with the rest
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
            p = who.get(fid, {}); _hold = _hold or lookup_hold(cpat, p.get("first", ""), p.get("last", ""), re.sub(r"\D", "", p.get("dob", "")), fid, sure=pid in SAME)      # 11/25/2026 (review): the same judgement for a plan the feed names
            if _hold[0] == "same_person": _said = not_entered(pid, _hold[1], _said); continue
            if _hold[1] and not _hold[0]: text += " - " + _hold[1]      # the Claimocity id on the chart, or William's word, let it be entered: said in the register entry
            done += 1
        if LIVE: _r, _pl, order = ins_update._plans(pid); plans = list(_pl.values())      # 11/19/2026: read the order again - a second plan added on the same chart must not drop the first from it
        seqs = [s for s in (order or "").replace(" ", "").split(",") if s]
        if not LIVE:
            print("  pat%s: DRY would add %s (%s) and %s" % (pid, use, text, "append it to the order %s" % order if 1 <= len(seqs) <= 2 else "leave the order %r" % order)); tally["would add %s" % ("a Medicaid plan" if kind == "medicaid" else "a secondary plan")] += 1; continue
        insid, seq = add_ins.add(pid, CODE2CAR[use], norm(member) if kind == "medicaid" else member, "01/01/%d" % datetime.date.today().year, "1", fin)
        if not insid: print("  pat%s: add %s FAILED %s" % (pid, use, str(seq)[:100])); tally["add failed"] += 1; continue
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
