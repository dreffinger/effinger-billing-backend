# PLAIN ENGLISH (Claimocity backlog import, William 10/28/2026 02:23 ET: "enter all of these encounters into advanced md
#   and bill them out, i dont care if we get duplicates later" - Gregg's pickup paused).
# Decides: for every DFT^P03 message in the 10/16-10/27 SFTP files whose patient has an AMD chart, creates the visit with
#   its charges (updvisitwithnewcharges on a NEW visit: id=""), diagnosis list, admission date on hospital stays, modifier
#   25 on 99497 / 99489 as the practice's existing charges carry it, facility/POS/profile copied from how the feed's own
#   earlier visits look in AMD. Charges enter Charge Review (approval=1, inspector on) like any feed charge.
# Dedupe: a feed line whose patient already has a live (non-void) charge with the same CPT + DOS is skipped.
# Clinician, building and admission date (11/10/2026): each visit takes them from ITS OWN feed message (MSH-4, PV1-7, PV1-44), found by
#   the message's patient id and its (code, DOS) lines. Until then ONE value per feed PATIENT was used - the last message read - so in a
#   batch that held a resident's CCM (the physician's) and the nurse practitioner's visits, the visits went in under the physician (149
#   visits in the October batches; registers/feed_recon_* name each message's own clinician). The per-patient value is now only the
#   fallback for a message the raw files do not answer exactly once, and that fallback is counted and reported.
# Place of service (William 11/10/2026, STANDING - practices/ehpa/rules.md): Claimocity can only send 31 for the nursing buildings, so the
#   place of service is set here per charge line BY WILLIAM'S FREQUENCY RULE (nobody has checked the building's Part A list): CCM
#   99487/99489 -> 32; a nursing facility visit -> 32 for the monthly visit, 31 when the resident is seen once or twice a week or the
#   chart shows a new stay; whatever the chart does not show stays 31.
#   ALF / home (13), hospital (21) and unknown-building lines are entered exactly as before. See NF_KINDS / nf_visit_kind / pos_lines below.
# Quality code (William 11/10/2026, STANDING - practices/ehpa/rules.md): the advance-care-plan code 1123F goes on as a no-charge line, once
#   per patient per year, with the next visit of every patient 65 or older whose first plan is Medicare Part B. See QUALITY_* below.
# Never touches: insurance plans (the cascade/precheck step verifies them afterwards), existing visits, patients without a chart.
# Usage: python3 feed_import_1028.py --dry | --one <feed pid> | --all [--limit N]
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, resave, txh, re, json, sys, time, datetime, collections
import xml.etree.ElementTree as ET
PARSED = json.load(open(("feed_parsed_%s.json" % STAMP)))
MATCH = json.load(open(("feed_match_%s.json" % STAMP)))
DX = json.load(open(DXCACHE))
REG = ("registers/feed_import_%s.json" % STAMP)
PCODE = {"99487": "pcode492676", "99489": "pcode492677", "99223": "pcode65084", "99232": "pcode65089", "99233": "pcode65090",
         "99239": "pcode65095", "99497": "pcode492667", "99498": "pcode492668", "99306": "pcode65116", "99308": "pcode65118",
         "99309": "pcode65119", "99316": "pcode65122", "99344": "pcode601053"}
FEE = {"99223": "310.00", "99232": "111.00", "99233": "160.00", "99239": "163.00", "99306": "256.00", "99308": "107.00", "99309": "141.00",
       "99487": "206.00", "99489": "109.00", "99497": "133.00", "99344": "300.00", "99316": "207.00", "99498": "115.00"}
PROFILE = {"1225327380": "prof13", "1235128869": "prof15"}          # Effinger DO / Garland-G ARNP
FAC = {"HCA Florida Capital Hospital": ("fac29", "21"), "BRYNWOOD OPERATIONS LLC": ("fac34", "31"), "Aspire of Tallahassee": ("fac32", "31"),
       "Centre Pointe Health And Rehab Center": ("fac33", "31"), "Westminster Oaks-Bertrand Health Center": ("fac58", "31"),
       "Oakes Southwood": ("fac1350", "31"), "Azalea Gardens ALF": ("fac37", "13"), "Tapestry Senior Living Lakeshore": ("fac55", "13"),
       "Opal Hermitage Boulevard ALF": ("fac53", "13"), "Capital Square at Tallahassee": ("fac54", "13"), "Canterfield of Tallahassee ALF": ("fac38", "13"),
       "Sodalis Senior Living ALF": ("fac65", "13"), "Allegro Senior Living ALF": ("fac57", "13")}
HOSP = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}
MOD25 = {"99497", "99489"}
def mdy(yyyymmdd):
    return "%s/%s/%s" % (yyyymmdd[4:6], yyyymmdd[6:8], yyyymmdd[0:4])
# ---- PLACE OF SERVICE IN THE NURSING BUILDINGS (William 11/10/2026, STANDING - practices/ehpa/rules.md) -------------------------------
# The five nursing buildings arrive from Claimocity as POS 31 whatever the resident's status ("that is the only way we have to do it in
# claimocity"), so the place of service is decided here by William's frequency rule, per charge line, when the charge is entered. It is
# an operating rule read from the chart's visit pattern, not a check of the building's Part A list. How the code reads Medicare's line: 31 is
# what was billed before; 32 is for a resident who is not in a Part A stay, and Medicare can match a 32 line to the facility's Part A claim. So 32 is
# given only where the chart SHOWS the long-term pattern, and everything unclear keeps the feed's 31 - exactly what was billed before.
#   CCM 99487 / 99489          -> 32: "all the ccm services performed in the nursing facility setting by us are done on our long term
#                                 residents that are not being actively skilled". ALF / home CCM keeps its home location (13).
#                                 Exception: the chart shows the resident seen at skilled frequency, admitted or readmitted in the CCM's
#                                 own calendar month -> the line stays at the feed's 31 and is listed for William.
#   nursing facility visit     -> 32 for "the snf residents that are being billed monthly face to face visits": the previous nursing visit
#   99304-99310, 99315, 99316     was MONTHLY_MIN_DAYS to MONTHLY_MAX_DAYS earlier, was not a discharge, and none of our hospital visits
#                                 falls in between.
#                              -> 31 for "the ones being billed once or twice weekly ... because they are being skilled": the previous
#                                 nursing visit was no more than SKILLED_GAP_DAYS earlier; and 31 for an initial visit 99304-99306, the first
#                                 nursing visit on the chart, the first visit after a discharge, after one of our hospital visits or after
#                                 more than MONTHLY_MAX_DAYS (a new stay), and for a gap between weekly and monthly (nothing shown).
#   any other line (99497/8)   -> the place of service of the visit line of the SAME date in the message, else the feed's.
# Only a line in a KNOWN nursing building (FAC says 31) is ever changed, and each message is read with ITS OWN building: a feed patient
# whose messages come from two buildings is handled message by message. Only when a message's own building cannot be read and the
# patient shows two buildings does the rule step aside for that visit - and says so (POS RULE NOT APPLIED).
# Hospital (21), ALF / home (13), HCA REHAB (the inspector step) and the unknown-building default are entered exactly as before. Any error
# in the rule falls back to the feed's place of service for the whole message and is counted as "POS RULE NOT APPLIED" - the import
# never stops for this rule.
POS_RULE_VERSION = "2026-11-10.5"       # change this line with EVERY revision of the rule - mirror.py PROTECTED, the runbook grep (step c) and the ingest guard name it
CCM = {"99487", "99489"}
NF_INITIAL = {"99304", "99305", "99306"}
NF_DISCHARGE = {"99315", "99316"}
NF_VISIT = NF_INITIAL | NF_DISCHARGE | {"99307", "99308", "99309", "99310"}
HOSP_VISIT = {"99221", "99222", "99223", "99231", "99232", "99233", "99234", "99235", "99236", "99238", "99239"}
HOME_VISIT = {"99341", "99342", "99344", "99345", "99347", "99348", "99349", "99350"}     # our home / assisted-living visits: the resident was out of the building
# which building a nursing visit on the chart was in, read from the facility name gettxhistory gives (one key per nursing building; any
# other name - another nursing home, the hospital's rehab unit - is its own key). The Southwood building has two facility records.
BUILDING_KEYS = (("BRYNWOOD", "fac34"), ("ASPIRE", "fac32"), ("CENTRE POINTE HEALTH", "fac33"), ("WESTMINSTER BERTRAND", "fac58"), ("WESTMINSTER OAKS", "fac58"), ("SOUTHWOOD", "fac1350"))
def building_key(facname):
    """The nursing building a facility name belongs to (its fac id), another building's own name, or None when no name is known."""
    n = " ".join(str(facname or "").upper().split())
    if not n: return None
    for word, fac in BUILDING_KEYS:
        if word in n: return fac
    return n
SKILLED_GAP_DAYS = 14      # weekly / twice-weekly visits (feed 9/1-11/5/2026: 100 gaps of 1-7 days, 10 of 8-14, 6 of 15-20, 41 of 21-35, 9 longer)
MONTHLY_MIN_DAYS = 21      # 32 needs the monthly pattern actually shown: previous nursing visit 21 ...
MONTHLY_MAX_DAYS = 92      # ... to 92 days back (the 60-day schedule fits; longer than that is a new stay, not a monthly visit)
BATCH_NF = {}              # chart -> {(cpt, DOS) or (cpt, DOS, building)}: nursing, hospital and home visits of THIS feed batch and the visits earlier batches could not enter (main() fills it); read with the chart's history
BATCH_NF_ERR = [""]        # why the batch list could not be built (then no nursing-building line is 32 in this run) - reaches the DONE line
FACS = {}                  # feed patient id -> every building name its messages carry in this batch
MSGOF = {}                 # one feed message (see msg_key) -> {(building name, clinician NPI, admission date)} read from the raw files
# ---- QUALITY CODE: ADVANCE CARE PLAN, Medicare measure 047 (William 11/10/2026, STANDING - practices/ehpa/rules.md) -------------------------
# "yes for all: billing adds 1123F automatically, once per patient, to the next Medicare claim for every patient 65 and older." 1123F says an
# advance care plan or a surrogate decision-maker is documented in the chart - William's statement for every patient the practice follows. CMS
# counts the code from the Medicare Part B claim itself: a no-charge line on the SAME claim as an eligible visit, once per patient per year
# (2026 claims specification of measure 047). It pays nothing. The line goes into the SAME create call as the visit's charges (a second call on
# the visit that left the other charges out would void them). If AdvancedMD refuses a visit that carries the line, the visit is entered again
# without it and no further line is tried in that run: a reporting code never holds a charge.
# PILOT: nobody has yet seen how AdvancedMD treats a no-charge line. So the first run puts the line on at most QUALITY_PILOT visits and later
# runs add NONE until the outcome of those lines is known (a read of each line's charge detail):
#   - a quality line is listed as billed to insurance            -> proven: from then on every eligible visit carries it (no cap);
#   - the visit was billed and its $0.00 line was left off        -> new lines carry $0.01 (CMS allows either); a new pilot of QUALITY_PILOT;
#     the patients whose $0.00 line never went out get the code again with their next visit (their dead lines are listed for voiding);
#   - AdvancedMD refuses the visit with the line, or stores the visit without it -> $0.01 next run; the same at $0.01 -> the code is OFF
#     until William says to start again (run once with QUALITY_CODE=reset; QUALITY_CODE=off keeps it off for one run);
#   - somebody took the pilot's lines off their visits (void) and none was billed -> OFF the same way: the import never starts a new pilot
#     over a person's correction. A whole visit that was voided is no outcome either way; its patient is simply due again.
# Once a line has been seen billed nothing is read back any more: a patient whose coded visit is voided LATER is not coded again that year.
# Every state is read from the import registers (each run writes "quality_gate"), so a fresh machine knows where things stand.
QUALITY_CODE = "1123F"; QUALITY_PCODE = "pcode65441"       # AdvancedMD's own id for 1123F (lookupproccode 11/10/2026)
QUALITY_SAME = {"1123F", "1124F"}                          # either one on the chart in the same year = already reported
QUALITY_PILOT = 3                                            # visits that may carry the line before one has been seen billed (then: no cap)
QUALITY_LOOKS = 6                                            # earlier quality lines read per run while the outcome is open (two reads each)
QUALITY_MIN_AGE = 65
MEDICARE_B = "car6085"                                       # FLORIDA MEDICARE (payer code FLO02) - the plan a Medicare Part B claim goes to
# the measure's eligible visit codes (2026 specification); CCM, advance care planning and discharge codes are not among them
QUALITY_VISITS = set("99304 99305 99306 99307 99308 99309 99310 99341 99342 99344 99345 99347 99348 99349 99350 99221 99222 99223 99231 99232 99233 "
                     "99234 99235 99236 99202 99203 99204 99205 99212 99213 99214 99215".split())
# this run's state (main() fills it from the registers). done: (chart, year) already coded; dead: (chart, code, DOS) of $0.00 lines that never
# went out on a claim; wait: earlier pilot lines whose outcome is still open - no new line this run
def _quality_fresh(): return {"fee": "0.00", "confirmed": False, "off": "", "wait": False, "added": 0, "done": set(), "dead": set(), "dead_rows": [],
                              "pending": [], "pending_since": "", "void_lines": [], "proof": None, "notes": [], "zero_not_billed": False, "reset": False, "twice": 0}
QUALITY = _quality_fresh()
def _mdy_day(s):
    try: return datetime.datetime.strptime((s or "")[:10], "%m/%d/%Y").date()
    except Exception: return None
def medicare_first(ctx, dos_mdy):
    """True when the chart's FIRST plan in billing order is Medicare Part B and is in force on that date (ctx['plans'] rows: plan id, carrier,
    begin date, end date, sequence; ctx['insorder'] = the sequences in billing order)."""
    day = _mdy_day(dos_mdy); first = (str(ctx.get("insorder") or "").replace(" ", "").split(",") or [""])[0]
    if day is None or not first: return False
    for row in ctx.get("plans") or ():
        try: _pid, car, beg, end, seq = row[:5]
        except Exception: continue
        if str(seq) != first: continue
        b = _mdy_day(beg); e = _mdy_day(end)
        return car == MEDICARE_B and (b is None or b <= day) and (not (end or "").strip() or (e is not None and e >= day))
    return False
def quality_due(msg, ctx, lines):
    """Index of the visit line the advance-care-plan code rides with, or None. Everything must be shown: an eligible visit code in THIS message,
    age 65 or more on that date (the feed's date of birth), Medicare Part B first on the chart, no 1123F / 1124F on the chart or in this run
    for that year, the code not switched off, no earlier pilot line still waiting for its outcome, and room under the pilot cap."""
    if QUALITY["off"] or QUALITY.get("wait") or (not QUALITY["confirmed"] and QUALITY["added"] >= QUALITY_PILOT): return None
    i = next((k for k, c in enumerate(lines) if c.get("cpt") in QUALITY_VISITS), None)
    if i is None: return None
    d8 = re.sub(r"\D", "", str(lines[i].get("dos") or ""))[:8]; dob = re.sub(r"\D", "", str(msg.get("dob") or ""))[:8]
    if len(d8) != 8 or len(dob) != 8 or not ("1900" < dob[:4] <= d8[:4]): return None      # no birth date, or the year-1900 placeholder: age not shown
    age = int(d8[:4]) - int(dob[:4]) - (1 if d8[4:] < dob[4:] else 0)
    if age < QUALITY_MIN_AGE or age > 115: return None
    if not medicare_first(ctx, mdy(d8)): return None
    if (ctx.get("pid"), d8[:4]) in QUALITY["done"]: return None
    dead = QUALITY.get("dead") or ()                      # a $0.00 line AdvancedMD left off the claim is on the chart but was never reported
    if any(c in QUALITY_SAME and str(d or "")[-4:] == d8[:4] and (ctx.get("pid"), c, d) not in dead
           for c, d in (r[:2] for r in ctx.get("live") or () if len(r) >= 2)): return None
    return i
def quality_undo(info, pid):
    """A visit that was built with the quality line was not created after all: its slot under the pilot cap and its once-a-year mark are freed."""
    try:
        if info.get("quality_dos"):
            QUALITY["added"] = max(0, QUALITY["added"] - 1); QUALITY["done"].discard((pid, str(info["quality_dos"])[-4:]))
    except Exception: pass
# what nf_visit_kind can answer: kind -> (place of service, the words for the register; %d = days since the previous nursing visit)
NF_KINDS = {
    "initial":      ("31", "31 by rule: initial visit"),
    "dischargeday": ("31", "31 by rule: discharge visit (kept at the feed's place of service)"),
    "first":        ("31", "31 by rule: no earlier nursing visit on the chart (read as a new admission)"),
    "hospital":     ("31", "31 by rule: first nursing visit after one of our hospital visits (%d days after the previous nursing visit)"),
    "away":         ("31", "31 by rule: one of our home or assisted-living visits since the previous nursing visit (%d days earlier)"),
    "discharge":    ("31", "31 by rule: the previous nursing visit, %d days earlier, was a discharge"),
    "moved":        ("31", "31 by rule: the previous nursing visit, %d days earlier, was in another building"),
    "preadmission": ("31", "31 by rule: an initial visit follows within two weeks (%d days after the previous nursing visit)"),
    "skilled":      ("31", "31 by rule: seen %d days after the previous nursing visit (weekly or more)"),
    "extra":        ("31", "31 by rule: seen %d days after the previous nursing visit, no admission visit at the start of this run of visits (an extra visit on a monthly resident?)"),
    "stale":        ("31", "31 by rule: %d days since the previous nursing visit, not a monthly pattern"),
    "between":      ("31", "31 by rule: %d days since the previous nursing visit, between weekly and monthly"),
    "monthly":      ("32", "32 by rule: %d days since the previous nursing visit (the monthly visit)"),
}
# a visit of one of these kinds in the CCM's month (or one of our hospital or home / assisted-living visits that month) keeps the CCM at the feed's 31, for William
SKILLED_KINDS = ("initial", "dischargeday", "first", "hospital", "away", "discharge", "moved", "preadmission", "skilled", "extra", "stale")
def _day(mdy_s):
    return datetime.datetime.strptime(mdy_s, "%m/%d/%Y").date()
def _history(nf_history):
    """Chart + batch rows -> (nursing visits {day: {codes}}, their buildings where known {day: {keys}}, days of our hospital visits, days of
    our home / assisted-living visits). A row is (cpt, 'MM/DD/YYYY') or (cpt, 'MM/DD/YYYY', facility name); odd rows are skipped."""
    visits = {}; where = {}; hosp = set(); home = set()
    for row in nf_history:
        try: c, d = row[0], row[1]
        except Exception: continue
        if not d or not isinstance(c, str): continue
        fam = "n" if c in NF_VISIT else "h" if c in HOSP_VISIT else "a" if c in HOME_VISIT else ""
        if not fam: continue
        try: dd = _day(d)
        except Exception: continue
        if fam == "h": hosp.add(dd)
        elif fam == "a": home.add(dd)
        else:
            visits.setdefault(dd, set()).add(c)
            try: k = building_key(row[2])
            except Exception: k = None
            if k: where.setdefault(dd, set()).add(k)
    return visits, where, hosp, home
def _kind_at(day, codes, hist, here=None):
    """(kind, days since the previous nursing visit) for a nursing visit with `codes` on `day`. hist = what _history returns; here = the
    building key of the visit when it is known. Everything that is not plainly the monthly visit answers a kind that is 31."""
    visits, where, hosp, home = hist
    codes = set(codes) | visits.get(day, set())
    if codes & NF_INITIAL: return "initial", 0
    if codes & NF_DISCHARGE: return "dischargeday", 0
    days = sorted(d for d in visits if d < day)
    if not days: return "first", 0
    here = here or next(iter(sorted(where.get(day, ()))), None)
    def new_stay(i, d2, here2):                          # does the nursing visit of d2 (the one after days[i-1] ...) start a stay?  i = index of the visit before it, or -1
        if i < 0: return True
        q = days[i]
        if (d2 - q).days > MONTHLY_MAX_DAYS or (visits[q] & NF_DISCHARGE): return True
        if any(q <= h <= d2 for h in hosp) or any(q <= a <= d2 for a in home): return True
        wq = where.get(q)
        return bool(here2 and wq and wq != {here2})      # a day that also names another building is not "the same building"
    prev = days[-1]; gap = (day - prev).days
    if any(prev <= h <= day for h in hosp): return "hospital", gap
    if any(prev <= a <= day for a in home): return "away", gap
    if visits[prev] & NF_DISCHARGE: return "discharge", gap
    if here and where.get(prev) and where[prev] != {here}: return "moved", gap      # chart and feed name two buildings for that day: unclear, so 31
    if any(day < d <= day + datetime.timedelta(days=SKILLED_GAP_DAYS) and (visits[d] & NF_INITIAL) for d in visits): return "preadmission", gap
    if gap <= SKILLED_GAP_DAYS:
        i = len(days) - 1                                # walk back through the run of close visits to its first visit
        while True:
            d2 = days[i]; h2 = next(iter(sorted(where.get(d2, ()))), None)
            if (visits[d2] & NF_INITIAL) or new_stay(i - 1, d2, h2): return "skilled", gap
            if (d2 - days[i - 1]).days > SKILLED_GAP_DAYS: return "extra", gap
            i -= 1
    if gap > MONTHLY_MAX_DAYS: return "stale", gap
    if gap < MONTHLY_MIN_DAYS: return "between", gap
    return "monthly", gap
def nf_visit_kind(cpt, dos_mdy, nf_history, here=None):
    """(kind, days) for ONE nursing facility visit line in a nursing building - see NF_KINDS. nf_history: iterable of (cpt, 'MM/DD/YYYY')
    or (cpt, 'MM/DD/YYYY', facility name): every nursing, hospital and home visit known for the resident (the chart's live charges + this
    feed batch). here = the building key of this line. Pure: no AMD call, no file."""
    return _kind_at(_day(dos_mdy), {cpt}, _history(nf_history), here)
def nf_visit_pos(cpt, dos_mdy, nf_history, here=None):
    """(pos, why) for ONE nursing facility visit line in a nursing building. why carries no date."""
    kind, gap = nf_visit_kind(cpt, dos_mdy, nf_history, here); pos, text = NF_KINDS[kind]
    return pos, (text % gap if "%d" in text else text)
def seen_at_skilled_frequency(dos_mdy, nf_history):
    """True when the chart shows, in the calendar month of dos_mdy, one of our hospital visits, one of our home / assisted-living visits (the
    resident was out of the building that month) or a nursing visit the rule reads as weekly, an admission, a discharge or a new stay (any
    kind in SKILLED_KINDS). Then a CCM line of that month stays at the feed's 31, for William."""
    day = _day(dos_mdy); hist = _history(nf_history); visits, where, hosp, home = hist
    same = lambda d: (d.year, d.month) == (day.year, day.month)
    if any(same(h) for h in hosp) or any(same(a) for a in home): return True      # the resident was in the hospital or out of the building that month
    for d in sorted(visits):
        if same(d) and _kind_at(d, visits[d], hist)[0] in SKILLED_KINDS: return True
    return False
def pos_lines(cpt_dos, feed_pos, nursing, nf_history, here=None):
    """Place of service for every line of ONE feed message. cpt_dos = [(cpt, 'MM/DD/YYYY')] in line order; nursing = the message comes from
    one of the practice's nursing buildings; here = that building's key. Returns ([pos per line], [why per line], [kind per line])."""
    n = len(cpt_dos)
    if not nursing: return [feed_pos] * n, [""] * n, [""] * n
    hist = []
    for row in nf_history:
        try: hist.append((row[0], row[1], row[2] if len(row) > 2 else None))
        except Exception: continue
    for cpt, d in cpt_dos:
        if cpt in NF_VISIT: hist.append((cpt, d, None))   # the message's own visit lines count as history for each other
    out = []; why = []; kinds = []; by_day = {}
    for cpt, d in cpt_dos:
        if cpt in CCM:
            if seen_at_skilled_frequency(d, hist): p, w, k = feed_pos, "31 kept: the chart shows a hospital visit, a home / assisted-living visit, or nursing visits in this CCM month that the rule reads as weekly, an admission or a new stay - for William", "ccm-skilled-month"
            else: p, w, k = "32", "32 by rule: CCM in a nursing building", "ccm"
        elif cpt in NF_VISIT:
            k, gap = nf_visit_kind(cpt, d, hist, here); p, text = NF_KINDS[k]; w = text % gap if "%d" in text else text
            by_day[d] = "31" if "31" in (p, by_day.get(d)) else p     # two visit lines on one day: any 31 keeps the day at 31
        else: p, w, k = None, "", ""
        out.append(p); why.append(w); kinds.append(k)
    for i, (cpt, d) in enumerate(cpt_dos):
        if out[i] is None:
            if d in by_day: out[i] = by_day[d]; why[i] = "same place of service as the visit line of that day"; kinds[i] = "with-visit"
            else: out[i] = feed_pos
    return out, why, kinds
def _bills(charge_id, pcode=None):
    """What AdvancedMD's charge detail says about ONE charge (a read): the dates it was billed to insurance ([] = never billed), or None when
    the charge is not in the answer, is void, or (pcode given) carries another procedure."""
    cid = re.sub(r"\D", "", str(charge_id or ""))
    if not cid: return None
    root = ET.fromstring(resave.detail(cid))
    for c in root.iter("charge"):
        if re.sub(r"\D", "", c.get("id") or "") != cid: continue
        if c.get("void") == "1" or (pcode and c.get("proccode") not in (None, "", pcode)): return None
        out = [b.get("billeddate") for b in c.findall("insbilllist/insbill") if b.get("billeddate")]
        if not out and c.get("insbilled") == "1" and (c.get("datebilled") or "").strip(): out = [c.get("datebilled").strip()[:10]]
        return out
    return None
def answer_charges(r):
    """Every charge AdvancedMD's answer lists, in its order: [(charge number, procedure id, amount, place of service)], '' where the answer
    does not carry a value."""
    out = []
    for m in re.finditer(r"<charge\b([^>]*)>", r or ""):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if re.match(r"charge\d+$", a.get("id") or ""): out.append((a["id"], a.get("proccode") or "", a.get("fee") or "", a.get("pos") or ""))
    return out
def quality_in_answer(ans, n_codes, fee):
    """Which of the answer's charges is the quality line (its index), or None when the answer does not hold it: by its procedure; else the ONE
    charge whose amount is the line's amount ($0.00 or $0.01 - no visit code has such a fee); else, when the answer names no procedure at
    all and lists more charges than the message has codes, the last one."""
    by = [i for i, c in enumerate(ans) if c[1] == QUALITY_PCODE]
    if by: return by[0]
    def money(x):
        try: return round(float(x), 2)
        except Exception: return None
    f = money(fee); same = [i for i, c in enumerate(ans) if c[2] != "" and money(c[2]) == f]
    if f is not None and len(same) == 1: return same[0]
    return len(ans) - 1 if (len(ans) > n_codes and not any(c[1] for c in ans)) else None
def chart_lines_now(pid):
    """(code, DOS) of every live charge on the chart right now - one read of the chart's history, the same lines chart_ctx calls live."""
    out = set()
    for c in txh.fetch(re.sub(r"\D", "", pid)).iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        out.add((a.get("proccode"), a.get("dos")))
    return out
def quality_state(regs, look, reset=False):
    """Fill QUALITY from the earlier import registers (oldest first). regs = [(file name, register)]. See the PILOT comment above for the
    states. look=False (a dry run) reads nothing in AdvancedMD: earlier lines whose outcome is open then simply mean 'wait'. reset=True
    (QUALITY_CODE=reset, William's word) starts the pilot again: refusals and open lines of earlier runs no longer count - but a line that
    exists still counts for 'once per patient per year'. Nothing here can stop the import: the caller turns any error into 'no line this run'."""
    q = _quality_fresh(); fee = "0.00"; off = ""; notes = []; rows = []; allrows = []; confirmed_at = set(); znb_seen = False
    void_ids = set()                                      # quality lines an earlier run found void: neither open nor reported, never read again
    def _gate(reg): g = reg.get("quality_gate") if isinstance(reg, dict) else None; return g if isinstance(g, dict) else {}
    for name, reg in sorted(regs, key=lambda x: str(x[0])):
        try:
            g = _gate(reg)
            if g.get("reset"): fee = "0.00"; off = ""; rows = []; confirmed_at = set(); znb_seen = False      # the pilot was started again in that run
            if g.get("zero_not_billed"): fee = "0.01"; znb_seen = True
            if isinstance(g.get("void_lines"), list): void_ids.update(x for x in g["void_lines"] if isinstance(x, str))
            if g.get("confirmed") and g.get("fee") in ("0.00", "0.01"): confirmed_at.add(g["fee"])
            for r in (reg.get("created") if isinstance(reg.get("created"), list) else []):
                if not isinstance(r, dict): continue
                qc = r.get("quality_codes") if isinstance(r.get("quality_codes"), list) else []
                qid = r.get("quality_charge") if isinstance(r.get("quality_charge"), str) else ""
                f = str(r.get("quality_refused_fee") or r.get("quality_not_stored") or r.get("quality_fee") or "0.00")
                if r.get("quality_refused") or r.get("quality_not_stored"):
                    what = "refused a visit that carried the code" if r.get("quality_refused") else "stored a visit without its quality line"
                    if f == "0.00": fee = "0.01"
                    else: off = "AdvancedMD %s with a one-cent charge too (%s) - a person has to look" % (what, _os.path.basename(str(name)))
                elif qc and qid: rows.append((name, r)); allrows.append((name, r))
        except Exception: continue
    if reset: fee = "0.00"; off = ""; rows = []; confirmed_at = set(); znb_seen = False; notes.append("the pilot was started again in this run (QUALITY_CODE=reset)")
    rows = [x for x in rows if x[1].get("quality_charge") not in void_ids]; allrows = [x for x in allrows if x[1].get("quality_charge") not in void_ids]
    confirmed = fee in confirmed_at; proof = None; znb = False; wait = False; gone = set()
    pending = [(n, r) for n, r in rows if str(r.get("quality_fee") or "0.00") == fee]
    if not confirmed and not off and pending:
        if not look: wait = True; notes.append("dry run: %d earlier quality line(s) were not looked up - a live run reads them" % len(pending))
        else:
            unknown = max(0, len(pending) - QUALITY_LOOKS); removed = 0
            for name, r in pending[:QUALITY_LOOKS]:
                try:      # the visit's own charge = the first recorded charge that is not the quality line
                    ql = _bills(r.get("quality_charge"), QUALITY_PCODE); first = _bills(next((c for c in (r.get("charges") or []) if c != r.get("quality_charge")), None))
                except Exception as e:
                    unknown += 1; notes.append("could not read the earlier quality line of visit %s (%s)" % (r.get("visit"), type(e).__name__)); continue
                if ql:
                    confirmed = True; proof = {"register": _os.path.basename(str(name)), "visit": r.get("visit"), "charge": r.get("quality_charge"), "billed": ql[0], "fee": fee}; break
                if ql is None:                            # the line is void (or no longer that procedure): this patient has no reported code
                    gone.add(id(r)); void_ids.add(r.get("quality_charge"))
                    if first is None: notes.append("visit %s is no longer on the chart (void), its quality line with it" % r.get("visit"))
                    else: removed += 1; notes.append("the quality line of visit %s was taken off the visit (void) while the visit itself is still there" % r.get("visit"))
                    continue
                if first:                                 # the visit went out on a claim, its quality line did not
                    if fee == "0.00": znb = True; notes.append("visit %s was billed %s without its $0.00 quality line - new lines carry $0.01" % (r.get("visit"), first[0]))
                    else: off = "AdvancedMD billed visit %s (%s) without its one-cent quality line too - a person has to look" % (r.get("visit"), first[0])
                    break
                unknown += 1                              # not billed yet: the answer is still out
            if not confirmed and not znb and not off:
                if unknown: wait = True
                elif removed:      # somebody took the pilot's lines off their visits: no new pilot until a person says so
                    off = "%d earlier quality line(s) were taken off their visits and none was seen billed - a person says whether to try again (QUALITY_CODE=reset)" % removed
    if znb: fee = "0.01"; znb_seen = True; pending = []
    for name, r in allrows:                               # once per patient per year - from the registers too, whatever the chart history shows
        try:
            d = str(r.get("quality_dos") or r.get("dos") or ""); pid = r.get("pid")
            if not isinstance(pid, str) or len(d) < 4 or id(r) in gone: continue      # a line found void does not count as reported
            if znb_seen and fee == "0.01" and str(r.get("quality_fee") or "0.00") == "0.00":
                q["dead"].add((pid, QUALITY_CODE, d)); q["dead_rows"].append([pid, r.get("visit"), r.get("quality_charge")])
            else: q["done"].add((pid, d[-4:]))
        except Exception: continue
    q.update(fee=fee, confirmed=confirmed, off=off, wait=wait, proof=proof, notes=notes, zero_not_billed=znb_seen and fee == "0.01", reset=bool(reset), void_lines=sorted(void_ids),
             pending=[r.get("visit") for _, r in pending] if (wait or (pending and not confirmed)) else [],
             pending_since=_os.path.basename(str(pending[0][0])) if (pending and not confirmed) else "")
    QUALITY.clear(); QUALITY.update(q)
def msg_building(msg):
    """The building name of a message for the visit history: its own, else the patient's when the batch shows only one, else ''."""
    try:
        o = msg_agreed(msg)
        if o[0] is not None: return o[0]
        f = FACS.get(msg.get("pid")) or ()
        return next(iter(f)) if len(f) == 1 else ""
    except Exception: return ""
def seen_lines(msg):
    """[[code, 'MM/DD/YYYY', building name]]: the nursing, hospital and home visit lines of a message that is NOT entered (a code the table
    does not have, no usable diagnosis, a fault). They go into the register row so a LATER batch still knows the feed showed them."""
    try:
        bn = msg_building(msg)
        return [[c["cpt"], mdy(c["dos"][:8]), bn] for c in msg.get("FT1") or []
                if (c.get("cpt") in NF_VISIT or c.get("cpt") in HOSP_VISIT or c.get("cpt") in HOME_VISIT) and len(c.get("dos") or "") >= 8]
    except Exception: return []
def count_pos(info, stats):
    """The DONE-line counters for one message that was entered (or would be, in a dry run)."""
    if info.get("msg_own") is False: stats["feed message not matched to its own raw message - the patient's last-read building / clinician used"] += 1
    if info.get("prof_default"): stats["clinician id of the feed message is not one of the practice's two - entered under the physician profile"] += 1
    if not info.get("fac"): stats["visit entered with NO facility - its building is not in the facility table"] += 1      # every code, not only CCM / nursing lines
    if info.get("pos_err"):
        stats["POS RULE NOT APPLIED (entered at the feed's place of service)"] += 1; return
    for cpt, p, k in zip(info["cpts"], info["pos_lines"], info.get("pos_kind") or [""] * len(info["cpts"])):
        if info.get("pos_feed") == "31" and not info.get("fac") and (cpt in CCM or cpt in NF_VISIT): stats["POS RULE: building not in the facility table - entered at the feed's 31"] += 1
        elif k == "ccm": stats["POS 32 CCM (nursing building)"] += 1
        elif k == "ccm-skilled-month": stats["POS 31 CCM kept for William (weekly visits, admission or new stay that month)"] += 1
        elif k == "monthly": stats["POS 32 nursing visit (monthly)"] += 1
        elif k in ("extra", "between"): stats["POS 31 nursing visit (kept at 31: neither pattern shown)"] += 1
        elif k == "moved": stats["POS 31 nursing visit (previous nursing visit in another building)"] += 1
        elif k and k != "with-visit": stats["POS 31 nursing visit (weekly, admission or new stay)"] += 1
# facility per feed message (MSH-4) and provider NPI per message (PV1-7) re-read from the raw files
import glob
FACOF = {}; NPIOF = {}; ADMIT = {}      # per feed PATIENT, the last message read: only the fallback since 11/10/2026 (see msg_own)
def msg_key(pid, pairs):
    """What names ONE feed message inside a batch: the feed patient id and its (code, DOS) lines - the same whether they are read from
    the raw file here or from the parsed file (feed_parse_dft reads FT1-4 and FT1-25 the same way)."""
    return (str(pid or ""), tuple(sorted((str(c or ""), str(d or "")[:8]) for c, d in pairs)))
def msg_own(msg):
    """(building name, clinician NPI, admission date) of ONE parsed message, or None when the raw files do not give exactly one answer
    for it (no such message, or the same lines sent from two buildings / by two clinicians): then the per-patient values are used."""
    try:
        own = MSGOF.get(msg_key(msg.get("pid"), [(c.get("cpt"), c.get("dos")) for c in msg.get("FT1") or []])) or ()
        return next(iter(own)) if len(own) == 1 else None
    except Exception: return None
def msg_agreed(msg):
    """(building, NPI, admission date) of ONE parsed message value by value: what EVERY raw copy of the message says; None for a value the
    copies do not agree on, or when the raw files do not hold the message. A visit sent twice with a corrected admission date keeps its building and clinician."""
    try:
        own = MSGOF.get(msg_key(msg.get("pid"), [(c.get("cpt"), c.get("dos")) for c in msg.get("FT1") or []])) or ()
        return tuple((next(iter({o[i] for o in own})) if len({o[i] for o in own}) == 1 else None) for i in range(3))
    except Exception: return (None, None, None)
for f in sorted(glob.glob((HL7_DIR + "/*.hl7"))):       # sorted: "the last message read" is the same on every machine (the parser sorts too)
    raw = open(f, errors="replace").read().replace("\r", "\n")
    for b in re.split(r"(?m)^(?=MSH\|)", raw):
        if not b.startswith("MSH|"): continue
        msh = b.split("\n")[0].split("|"); fac = msh[3].split("^")[-1] if len(msh) > 3 else ""; pid = None      # a short line never stops the load
        _npi = _adm = ""; _ft = []; _pv1 = False
        for line in b.strip().split("\n"):              # b.strip(): exactly what feed_parse_dft does to a block, so both readers see the same last field
            s = line.split("|")
            if s[0] == "PID": pid = s[3] if len(s) > 3 else ""; FACOF[pid] = fac; FACS.setdefault(pid, set()).add(fac)
            if s[0] == "PV1":                             # wherever it stands in the message (the parser does not care about the order either)
                _pv1 = True; _npi = s[7].split("^")[0] if len(s) > 7 else ""; _adm = s[44] if len(s) > 44 else ""
            if s[0] == "FT1": _ft.append((s[25].split("^")[0] if len(s) > 25 else "", s[4] if len(s) > 4 else ""))
        if pid and _pv1: NPIOF[pid] = _npi; ADMIT[pid] = _adm
        try:
            if pid: MSGOF.setdefault(msg_key(pid, _ft), set()).add((fac, _npi, _adm))
        except Exception: pass
_ctx = {}
def chart_ctx(pid):
    """episode, respparty, refplan, insorder, live {(cpt,dos)} from the chart's own history/detail."""
    if pid in _ctx: return _ctx[pid]
    num = re.sub(r"\D", "", pid)
    root = txh.fetch(num)
    live = set(); rows = set(); sample = None; newest = ""; qsample = None
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        live.add((a.get("proccode"), a.get("dos")))
        if a.get("proccode") in NF_VISIT or a.get("proccode") in HOSP_VISIT or a.get("proccode") in HOME_VISIT: rows.add((a.get("proccode"), a.get("dos"), a.get("facname") or ""))
        if a.get("proccode") in QUALITY_SAME: qsample = qsample or a.get("id")      # a quality line is the sample only when the chart has nothing else
        elif (a.get("dos") or "") > newest or sample is None:
            newest = a.get("dos") or ""; sample = a.get("id")
    ctx = {"live": live, "nfrows": rows, "episode": "", "resp": "", "refplan": "", "insorder": ""}   # nfrows: (code, DOS, facility name) of visit charges, for the place-of-service rule
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    ctx["resp"] = a.get("respparty", ""); ctx["insorder"] = a.get("insorder", "") or "1"; ctx["deceased"] = a.get("deceased", "")
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*sequence="(\d+)"', r)
    ctx["plans"] = pl
    sample = sample or qsample
    if sample:
        d = ET.fromstring(resave.detail(re.sub(r"\D", "", sample)))
        v = d.find(".//visit")
        if v is not None:
            ctx["episode"] = v.get("episode", ""); ctx["refplan"] = v.get("refplan", "")
            if not ctx["resp"]:
                ch = [e for e in d.iter("charge")]
                if ch: ctx["resp"] = ch[0].get("respparty", "")
    _ctx[pid] = ctx
    return ctx
# One face-to-face E/M per patient per day: a charge already on the chart for the same DOS from the same visit family IS this encounter,
# whatever level or new/established code it ended up with (the Claim Inspector swaps a second new-patient code to 99349; coders change
# levels). 10/30/2026: two 9/2 home visits were entered twice because the feed said 99344 and the chart carried 99349.
EM_FAMILY = [set("99341 99342 99344 99345 99347 99348 99349 99350".split()),            # home / ALF visits
             set("99221 99222 99223 99231 99232 99233 99238 99239 99234 99235 99236".split()),   # hospital
             set("99304 99305 99306 99307 99308 99309 99310 99315 99316".split()),      # SNF / NF
             set("99202 99203 99204 99205 99212 99213 99214 99215".split())]            # office
# (CCM 99487 + its add-on 99489 and ACP 99497/99498 legitimately share a DOS - those stay on the exact code + DOS rule)
def same_encounter(cpt, dos, live):
    fam = next((f for f in EM_FAMILY if cpt in f), None)
    if not fam: return False
    return any(lc in fam and ld == dos for lc, ld in live)
def build(msg, ctx):
    fid = msg["pid"]; own = msg_own(msg)             # this message's own (building, clinician NPI, admission date) - None = not readable
    _ag = msg_agreed(msg)                            # value by value: what every copy of the message says; the patient's last-read value only where the copies differ
    facname = _ag[0] if _ag[0] is not None else FACOF.get(fid, ""); npi = _ag[1] if _ag[1] is not None else NPIOF.get(fid, ""); admit = _ag[2] if _ag[2] is not None else ADMIT.get(fid, "")
    fac, pos = FAC.get(facname, ("", "31"))
    nursing = facname in FAC and pos == "31"        # one of the practice's nursing buildings (never the unknown-building default)
    prof = PROFILE.get(npi, "prof13")               # an id that is not one of the practice's two (or none at all) still goes in under the physician - and is said
    lines = []
    for c in msg["FT1"]:
        cpt = c["cpt"]
        if cpt not in PCODE: return None, "unknown CPT %s" % cpt
        if (cpt, mdy(c["dos"][:8])) in ctx["live"]: continue        # dedupe: same code, same DOS
        if same_encounter(cpt, mdy(c["dos"][:8]), ctx["live"]): continue   # dedupe: same E/M family, same DOS (10/30: 99344 vs the inspector's 99349)
        lines.append(c)
    if not lines: return None, "all lines already in AMD"
    dos = mdy(lines[0]["dos"][:8])
    chg = ""
    cpts = [c["cpt"] for c in lines]
    missing_dx = set()
    # place of service per line (11/10/2026 rule); any failure = the feed's place of service for every line, exactly as before the rule
    pos_err = ""; lkind = [""] * len(lines)
    try:
        if nursing and BATCH_NF_ERR[0]:
            raise ValueError("the visits of this batch could not be listed (%s), so nothing shows this resident's pattern - kept at the feed's place of service" % BATCH_NF_ERR[0])
        if _ag[0] is None and len(FACS.get(fid, ())) > 1 and (nursing or any(FAC.get(_n, ("", ""))[1] == "31" for _n in FACS[fid])):
            raise ValueError("this feed patient has messages from %d buildings in this batch and this message's own building could not be read - "
                             "check the facility, the clinician and the place of service of this visit by hand" % len(FACS[fid]))
        hist = (list(ctx.get("nfrows") or ctx.get("live") or ()) + list(BATCH_NF.get(ctx.get("pid"), ()))) if nursing else ()   # the history is only read for a nursing building
        lpos, lwhy, lkind = pos_lines([(c["cpt"], mdy(c["dos"][:8])) for c in lines], pos, nursing, hist, fac if nursing else None)
        if len(lpos) != len(lines) or any(p not in ("31", "32", pos) for p in lpos): raise ValueError("unexpected place of service %r" % (lpos,))
    except Exception as e:
        lpos = [pos] * len(lines); lwhy = ["rule error"] * len(lines); lkind = [""] * len(lines); pos_err = str(e)[:200] or type(e).__name__
    try: qi = quality_due(msg, ctx, lines)                # the visit line the advance-care-plan quality code rides with (None = no code)
    except Exception: qi = None
    qchg = ""
    for _k, (c, cpos) in enumerate(zip(lines, lpos)):
        dcodes = []
        for code in c["dx"].split("^"):
            if DX.get(code): dcodes.append(DX[code])
            elif code: missing_dx.add(code)
        if not dcodes: return None, "no usable dx for %s" % c["cpt"]
        mod = "mcode7" if c["cpt"] in MOD25 and len(cpts) > 1 else ""
        fee = FEE[c["cpt"]]; d = mdy(c["dos"][:8])
        dcodes = dcodes[:12]
        chg += ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" tos="01" '
                'units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote="">'
                '<diagcodelist>%s</diagcodelist></charge>') % (ctx["resp"], d, d, " ".join(dcodes), mod, d, PCODE[c["cpt"]], cpos, c["units"] or "1", fee, fee, fee, fee,
                "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes))
        if _k == qi and cpos != "23":      # same date, place of service and diagnoses as its visit line; no charge; never a modifier (the measure leaves out the emergency department, 23)
            qchg = ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" tos="01" '
                    'units="1" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote="">'
                    '<diagcodelist>%s</diagcodelist></charge>') % (ctx["resp"], d, d, " ".join(dcodes), d, QUALITY_PCODE, cpos, QUALITY["fee"], QUALITY["fee"], QUALITY["fee"], QUALITY["fee"],
                    "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes))
    ext = ""
    if any(c in HOSP for c in cpts) and admit:
        ext = '<extins hospitalizationfrom="%s"/>' % mdy(admit[:8])
    onh = "1" if ext else "0"
    # two-step create (proven 10/28/2026 on pat17476917 vst19458732): addvisit <appt> makes the empty visit, then
    # updvisitwithnewcharges on that visit id adds the charges. VISIT_ID is substituted by the caller.
    def _body(charges):
        vis = ('<visit id="%%VISIT%%" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1">'
               '<chargelist>%s</chargelist>%s</visit>') % (dos, prof, fac, ctx["refplan"], ctx["insorder"], onh, charges, ext)
        return amd.msg("updvisitwithnewcharges", "chargeentry",
                       {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                        "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis)
    plain = _body(chg)                                     # the visit exactly as before the quality code existed
    body = _body(chg + qchg) if qchg else plain            # the quality line is LAST in the list
    if qchg: QUALITY["added"] += 1; QUALITY["done"].add((ctx.get("pid"), re.sub(r"\D", "", str(lines[qi].get("dos") or ""))[:4]))
    appt = ('<appt id="" patient="%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" '
            'acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (ctx["pid"], ctx["episode"], dos, prof, fac, ctx["refplan"], ctx["insorder"], onh)
    create = amd.msg("addvisit", "chargeentry", {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                     "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt)
    # "pos" stays ONE value for the registers that read it (recon, monitor, the practice database): the first line's; pos_lines has every line
    # dos_lines: every line's own date (a message can carry two); msg_own: False = building / clinician came from the per-patient fallback
    # quality_codes: the reporting code that rides with this visit (never in cpts: the register dedupe keys on the message's own codes)
    return (create, body, plain), {"dos": dos, "dos_lines": [mdy(c["dos"][:8]) for c in lines], "cpts": cpts, "fac": fac, "pos": lpos[0], "pos_feed": pos, "pos_lines": lpos,
                            "pos_why": lwhy, "pos_kind": lkind, "pos_err": pos_err, "prof": prof, "prof_default": npi not in PROFILE, "msg_own": bool(own), "admit": admit, "missing_dx": sorted(missing_dx),
                            **({"quality_codes": [QUALITY_CODE], "quality_fee": QUALITY["fee"], "quality_dos": mdy(lines[qi]["dos"][:8]), "quality_pos": lpos[qi]} if qchg else {})}
def main():
    a = sys.argv[1:]; dry = "--dry" in a; one = a[a.index("--one") + 1] if "--one" in a else None
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
    amd.login_cached()
    reg = json.load(open(REG)) if __import__("os").path.exists(REG) else {"created": [], "skipped": [], "failed": []}
    # a feed id is the PATIENT (PID-3), not the message: dedupe on (patient, DOS, CPT set) - the live-charge check is the backstop.
    # EVERY earlier batch register counts (a visit re-dated after its import, e.g. the CCI 24078 re-dates, no longer matches the feed DOS
    # in AMD, so the live check alone would create it again - 10/29/2026 dry run).
    import glob as _glob
    done = set(); prior_seen = []        # prior_seen: (chart, [code, DOS, building]) visit lines earlier batches saw but did not enter
    prior_regs = []                      # (file name, register) of every earlier batch: the quality code's state is read from them
    for rf in _glob.glob("registers/feed_import_*.json"):
        if rf.endswith("_decisions.json"): continue
        try: prior = json.load(open(rf))
        except Exception: continue
        if rf != REG and isinstance(prior, dict): prior_regs.append((rf, prior))
        done |= {(r["feed_id"], r["dos"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id")}
        done |= {(r["feed_id"], r["dos_feed"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id") and r.get("dos_feed")}   # re-dated visits keep their feed DOS here
        if rf == REG: done |= {(r["feed_id"], None, None) for r in prior.get("skipped", [])}
        for _k in ("skipped", "failed"):                 # row by row and line by line: an odd row or line is skipped, the rows after it are still read
            _rows = prior.get(_k) if isinstance(prior, dict) else None
            for r in (_rows if isinstance(_rows, list) else []):
                try: _lns = r.get("lines"); _rp = r.get("pid")
                except Exception: continue
                for _ln in (_lns if isinstance(_lns, list) else []):
                    if isinstance(_ln, (list, tuple)): prior_seen.append((_rp, list(_ln)))
    # deceased guard before any write: a DOS after the cached date of death is never entered (William's standing rule)
    _dc = {}
    for _p in [__import__("os").environ.get("DECEASED_CACHE", ""), "deceased_cache_local.json", "registers/deceased_cache.json"]:
        if _p and __import__("os").path.exists(_p):
            try: _dc = json.load(open(_p)); break
            except Exception: pass
    def _dod(pid):
        v = _dc.get(re.sub(r"\D", "", pid)) or {}
        d = v.get("dod") or ""
        return d if re.match(r"\d{4}-\d{2}-\d{2}$", d) else None
    # nursing and hospital visits of THIS batch per chart: the place-of-service rule reads them together with the chart's own history,
    # so the result does not depend on the order the messages are entered in
    try:
        for _m in PARSED:
            _p = MATCH.get(_m["name"].upper().strip() + "|" + _m["dob"][:8], {}).get("resolved")
            if not _p: continue
            _bn = msg_building(_m)                               # the message's own building: a visit in another building is then seen as a move
            for _c in _m.get("FT1") or []:
                if (_c.get("cpt") in NF_VISIT or _c.get("cpt") in HOSP_VISIT or _c.get("cpt") in HOME_VISIT) and len(_c.get("dos") or "") >= 8:
                    BATCH_NF.setdefault(_p, set()).add((_c["cpt"], mdy(_c["dos"][:8]), _bn) if _bn else (_c["cpt"], mdy(_c["dos"][:8])))
        for _p, _ln in prior_seen:      # a visit an earlier batch could not enter still happened: the feed showed it
            try:                        # row by row: an odd row in an old register is skipped, it never switches the rule off
                if isinstance(_p, str) and _p and len(_ln) >= 2 and isinstance(_ln[0], str) and isinstance(_ln[1], str) and (_ln[0] in NF_VISIT or _ln[0] in HOSP_VISIT or _ln[0] in HOME_VISIT):
                    BATCH_NF.setdefault(_p, set()).add((_ln[0], _ln[1], _ln[2]) if len(_ln) > 2 and isinstance(_ln[2], str) and _ln[2] else (_ln[0], _ln[1]))
            except Exception: continue
    except Exception as e:
        BATCH_NF.clear(); BATCH_NF_ERR[0] = str(e)[:120] or type(e).__name__
        print("POS RULE: batch visit list not built (%s) - nursing-building lines stay at the feed's 31 this run (POS RULE NOT APPLIED)" % BATCH_NF_ERR[0])
    _qenv = (__import__("os").environ.get("QUALITY_CODE") or "").strip().lower()      # "off" = no line in this run; "reset" = start the pilot again (William's word)
    try: quality_state(prior_regs, look=not dry, reset=(_qenv == "reset"))
    except Exception as e:      # the state could not be read: NO line in this run (an unknown state is never treated as a fresh pilot)
        QUALITY.clear(); QUALITY.update(_quality_fresh()); QUALITY["off"] = "this run: the state of the quality code could not be read (%s)" % type(e).__name__
    if _qenv == "off": QUALITY["off"] = QUALITY["off"] or "this run: switched off (QUALITY_CODE=off)"
    n = 0; stats = collections.Counter()
    if BATCH_NF_ERR[0]: stats["POS RULE: batch visit list not built - nursing-building lines kept at the feed's 31"] += 1
    for msg in PARSED:
        fid = msg["pid"]
        if one and fid != one: continue
        mkey = (fid, mdy(msg["FT1"][0]["dos"][:8]), tuple(sorted(c["cpt"] for c in msg["FT1"])))
        if mkey in done or (fid, None, None) in done: stats["already created"] += 1; continue
        k = msg["name"].upper().strip() + "|" + msg["dob"][:8]; pid = MATCH.get(k, {}).get("resolved")
        if not pid: stats["no chart"] += 1; continue
        if n >= limit: break
        try:
            dod = _dod(pid)
            if dod and any(c["dos"][:8] > dod.replace("-", "") for c in msg["FT1"]):
                stats["DOS after date of death - not entered"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "DOS after date of death %s (deceased cache) - never billed" % dod}); json.dump(reg, open(REG, "w"), indent=1); continue
            ctx = chart_ctx(pid); ctx["pid"] = pid
            if ctx.get("deceased"):
                stats["deceased chart - held"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "deceased flag on chart - William"}); continue
            body, info = build(msg, ctx)
            if body is None:
                stats["skip: " + info] += 1
                reg["skipped"].append(dict({"feed_id": fid, "pid": pid, "why": info}, **({} if info == "all lines already in AMD" else {"lines": seen_lines(msg)}))); continue
            n += 1
            if info.get("pos_err"): print("POS RULE NOT APPLIED", pid, info["dos"], info["cpts"], info["pos_err"])
            if info.get("msg_own") is False and not info.get("pos_err"): print("POS CHECK not own message", pid, info["dos"], info["cpts"], "the raw files gave no single answer for this message - the patient's last-read building / clinician / admission date were used where its copies differ; for William")
            if info.get("prof_default"): print("POS CHECK clinician not known", pid, info["dos"], info["cpts"], "the feed message names no clinician id the profile table has - entered under the physician profile; for William")
            if not info.get("fac"): print("POS CHECK no facility", pid, info["dos"], info["cpts"], "the message's building is not in the facility table - entered without a facility at the feed's place of service; for William")
            if dry:
                print("DRY", pid, info); stats["dry"] += 1; stats["dry quality"] += 1 if info.get("quality_codes") else 0; count_pos(info, stats); continue
            create, body, plain = body
            r0 = amd.post(create, timeout=120)
            vm = re.search(r'<visit id="(vst\d+)"', r0)
            if not vm:
                quality_undo(info, pid)
                stats["FAULT create"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "err": "addvisit: " + re.sub(r"\s+", " ", r0[:500])})
                print("FAULT addvisit", pid, info["dos"], re.sub(r"\s+", " ", r0[:200])); json.dump(reg, open(REG, "w"), indent=1); continue
            r = amd.post(body.replace("%VISIT%", vm.group(1)), timeout=180)
            if ("Fault" in r or 'success="0"' in r) and info.get("quality_codes"):
                # A visit that carried the quality line was refused. A reporting code never holds a charge: the SAME visit goes in without the
                # line - but only when a fresh read of the chart shows that nothing of this visit was stored (a second send would double it).
                _why = re.sub(r"\s+", " ", r[:200]); _fee0 = info.get("quality_fee"); _mine = set(zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"]))) | {(QUALITY_CODE, info.get("quality_dos"))}
                quality_undo(info, pid); info["quality_codes"] = []; info["quality_tried"] = _fee0
                try: _stored = sorted(chart_lines_now(pid) & _mine)
                except Exception as e: _stored = ["chart not read: %s" % type(e).__name__]
                if _stored:
                    QUALITY["off"] = QUALITY["off"] or "this run: a visit with the code was refused and the chart could not be shown free of it"
                    stats["FAULT"] += 1; stats["QUALITY CODE: visit refused and NOT sent again (the chart shows part of it, or could not be read)"] += 1
                    reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "stored": [list(x) if isinstance(x, tuple) else x for x in _stored],
                                          "err": "refused with the quality line; not sent again because the chart shows %s - a person has to look: %s" % (_stored, _why)})
                    print("FAULT", pid, info["dos"], info["cpts"], "refused with the quality line; chart shows", _stored); json.dump(reg, open(REG, "w"), indent=1); continue
                r = amd.post(plain.replace("%VISIT%", vm.group(1)), timeout=180)
                if "Fault" in r or 'success="0"' in r:      # refused without the line as well: the quality code is not the cause
                    QUALITY["twice"] += 1
                    if QUALITY["twice"] >= 2: QUALITY["off"] = QUALITY["off"] or "this run: two visits were refused with and without the code - no further line tried"
                else:
                    info["quality_refused"] = _why; info["quality_refused_fee"] = _fee0
                    QUALITY["off"] = QUALITY["off"] or "this run: AdvancedMD refused a visit that carried the code"
                    stats["QUALITY CODE NOT ACCEPTED by AdvancedMD - the visit was entered without it"] += 1; print("QUALITY CODE REFUSED", pid, info["dos"], _why[:160])
            if "Fault" in r or 'success="0"' in r:
                stats["FAULT"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "err": re.sub(r"\s+", " ", r[:600])})
                print("FAULT", pid, info["dos"], info["cpts"], re.sub(r"\s+", " ", r[:300]))
            else:
                vid = re.search(r'<visit id="(vst\d+)"', r); cids = re.findall(r'<charge id="(charge\d+)"', r)
                fees = re.findall(r'<charge [^>]* fee="([^"]*)"', r)
                # what AdvancedMD stored: its answer echoes the charges - compare their place of service with what was sent (any order).
                # pos_stored None = the answer did not carry it for every line (then nothing is claimed either way)
                _qidx = None
                try:
                    if info.get("quality_codes"):      # find the quality charge first: the comparison below is about the visit's OWN lines
                        _ans = answer_charges(r); _qidx = quality_in_answer(_ans, len(info["cpts"]), info.get("quality_fee"))
                        _own = [c for i, c in enumerate(_ans) if i != _qidx]; _st = [c[3] for c in _own if c[3]]
                        if len(_st) != len(_own): _st = []
                        if _qidx is not None and _ans[_qidx][3]: info["quality_pos_stored"] = _ans[_qidx][3]
                    else:
                        _st = re.findall(r'<charge id="charge\d+"[^>]*?\bpos="(\d+)"', r)
                    info["pos_stored"] = _st if len(_st) == len(info["pos_lines"]) else None
                    if (info["pos_stored"] is not None and sorted(_st) != sorted(info["pos_lines"])) or (info.get("quality_pos_stored") and info.get("quality_pos") and info["quality_pos_stored"] != info["quality_pos"]):
                        stats["ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE (stored differs from sent)"] += 1
                        print("POS NOT KEPT", pid, info["dos"], info["cpts"], "sent", info["pos_lines"], "stored", _st, ("quality line sent %s stored %s" % (info.get("quality_pos"), info.get("quality_pos_stored"))) if info.get("quality_pos_stored") else "")
                except Exception: info["pos_stored"] = None
                if info["admit"] and any(c in HOSP for c in info["cpts"]):
                    # the extins child is ignored on create - write the admission date with the proven updextrainsinfo shape
                    for cpt in info["cpts"]:
                        if cpt in HOSP:
                            ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
                                   'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, mdy(info["admit"][:8]))
                            re_ = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": vm.group(1), "nocookie": "1"}, ext), timeout=120)
                            info["admit_written"] = "Fault" not in re_ and 'hospitalizationfrom="%s"' % mdy(info["admit"][:8]) in re_
                if info.get("quality_codes"):
                    info["quality_charge"] = _ans[_qidx][0] if _qidx is not None else ""      # by procedure, else by amount, else the last of an unnamed list
                    if not info["quality_charge"]:      # the visit was stored, the line was not: the next run reads this like a refusal
                        quality_undo(info, pid); info["quality_not_stored"] = info.get("quality_fee") or "0.00"; info["quality_codes"] = []
                        stats["QUALITY CODE: AdvancedMD stored the visit WITHOUT the line"] += 1
                        QUALITY["off"] = QUALITY["off"] or "this run: AdvancedMD stored a visit without its quality line"
                    else:                               # "fees" stays one amount per message code (feed_monitor pairs them in order); the line's own amount is quality_fee
                        try:
                            _i = cids.index(info["quality_charge"])
                            if len(fees) == len(cids): fees = fees[:_i] + fees[_i + 1:]
                        except Exception: pass
                reg["created"].append({"feed_id": fid, "pid": pid, "visit": vid.group(1) if vid else "", "charges": cids, "fees": fees, "at": datetime.datetime.utcnow().isoformat(), **info})
                for cpt, _d in zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"])): ctx["live"].add((cpt, _d))   # each line under its OWN date
                if info.get("quality_codes") and info.get("quality_charge"):
                    ctx["live"].add((QUALITY_CODE, info.get("quality_dos") or info["dos"])); stats["quality code 1123F added (advance care plan)"] += 1
                stats["created"] += 1; stats["charge lines"] += len(cids) - (1 if info.get("quality_charge") else 0); count_pos(info, stats)
                print("OK", pid, info["dos"], info["cpts"], vid.group(1) if vid else "?", cids, fees)
            json.dump(reg, open(REG, "w"), indent=1)
            time.sleep(0.6)
        except Exception as e:
            stats["error"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "lines": seen_lines(msg), "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
            json.dump(reg, open(REG, "w"), indent=1)
        if n % 25 == 0 and n: print("progress", n, dict(stats))
    # 10/29 05:49Z lesson: a live batch whose every line was already in AMD created nothing and so wrote NO import register (verify,
    # inspector, report and the recon then had nothing to read). The register is now always written at the end of a live run, skips included.
    reg["quality_gate"] = {"code": QUALITY_CODE, "fee": QUALITY["fee"], "confirmed": bool(QUALITY["confirmed"]), "proof": QUALITY.get("proof"), "zero_not_billed": bool(QUALITY.get("zero_not_billed")),
                           "off": QUALITY["off"], "wait": bool(QUALITY.get("wait")), "pending": list(QUALITY.get("pending") or []), "pending_since": QUALITY.get("pending_since") or "", "dead_zero_lines": list(QUALITY.get("dead_rows") or []), "void_lines": list(QUALITY.get("void_lines") or []),
                           "reset": bool(QUALITY.get("reset")), "pilot_cap": None if QUALITY["confirmed"] else QUALITY_PILOT, "notes": list(QUALITY.get("notes") or [])}
    if not dry: json.dump(reg, open(REG, "w"), indent=1)
    _qn = stats["dry quality"] if dry else stats["quality code 1123F added (advance care plan)"]
    print("QUALITY 1123F: %s x%d visit(s), line amount $%s, %s%s" % ("would be on" if dry else "on", _qn, QUALITY["fee"],
          "no cap (a quality line was seen billed)" if QUALITY["confirmed"] else
          ("pilot: waiting for the outcome of %d earlier line(s) - none added" % len(QUALITY.get("pending") or []) if QUALITY.get("wait") else "pilot: at most %d visit(s) until one is seen billed" % QUALITY_PILOT),
          ("; OFF - " + QUALITY["off"]) if QUALITY["off"] else ""))
    _pk = lambda w: sum(v for k, v in stats.items() if k.startswith(w))
    if _pk("ADVANCEDMD DID NOT KEEP") or _pk("feed message not matched") or _pk("clinician id of the feed message") or _pk("visit entered with NO facility"):
        # one SHORT line, like the next one (89 characters with one-digit counts)
        print("POS CHECK: stored another POS x%d; not own message x%d; clinician unknown x%d; no facility x%d" % (
            _pk("ADVANCEDMD DID NOT KEEP"), _pk("feed message not matched"), _pk("clinician id of the feed message"), _pk("visit entered with NO facility")))
    # one SHORT line (the ingest shows 110 characters of each of the last three log lines): 91 characters with one-digit counts
    print("POS RULE: CCM 32 x%d, CCM 31 x%d, visits 32 x%d, visits 31 x%d, not applied x%d, unknown bldg x%d" % (
        _pk("POS 32 CCM"), _pk("POS 31 CCM"), _pk("POS 32 nursing"), _pk("POS 31 nursing"), _pk("POS RULE NOT APPLIED"), _pk("POS RULE: building")))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
