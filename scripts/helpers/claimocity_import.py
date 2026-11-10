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
# an operating rule read from the chart's visit pattern, not a check of the building's Part A list. Medicare's own line: 31 is
# always allowed; 32 is for a resident who is not in a Part A stay, and every 32 line is matched to the facility's Part A claim. So 32 is
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
POS_RULE_VERSION = "2026-11-10.3"       # change this line with EVERY revision of the rule - mirror.py PROTECTED, the runbook grep (step c) and the ingest guard name it
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
BATCH_NF = {}              # chart -> {(cpt, DOS)} nursing and hospital visits in THIS feed batch (main() fills it); read with the chart's history
BATCH_NF_ERR = [""]        # why the batch list could not be built (then the chart history alone is used) - reaches the DONE line
FACS = {}                  # feed patient id -> every building name its messages carry in this batch
MSGOF = {}                 # one feed message (see msg_key) -> {(building name, clinician NPI, admission date)} read from the raw files
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
# a visit of one of these kinds in the CCM's month (or one of our hospital visits that month) keeps the CCM at the feed's 31, for William
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
        return bool(here2 and wq and here2 not in wq)
    prev = days[-1]; gap = (day - prev).days
    if any(prev <= h <= day for h in hosp): return "hospital", gap
    if any(prev <= a <= day for a in home): return "away", gap
    if visits[prev] & NF_DISCHARGE: return "discharge", gap
    if here and where.get(prev) and here not in where[prev]: return "moved", gap
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
    """True when the chart shows, in the calendar month of dos_mdy, one of our hospital visits or a nursing visit the rule reads as weekly,
    an admission, a discharge or a new stay (any kind in SKILLED_KINDS). Then a CCM line of that month stays at the feed's 31, for William."""
    day = _day(dos_mdy); hist = _history(nf_history); visits, where, hosp, home = hist
    same = lambda d: (d.year, d.month) == (day.year, day.month)
    if any(same(h) for h in hosp): return True
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
            if seen_at_skilled_frequency(d, hist): p, w, k = feed_pos, "31 kept: the chart shows a hospital visit or nursing visits in this CCM month that the rule reads as weekly, an admission or a new stay - for William", "ccm-skilled-month"
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
def msg_building(msg):
    """The building name of a message for the visit history: its own, else the patient's when the batch shows only one, else ''."""
    try:
        o = msg_own(msg)
        if o: return o[0]
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
for f in sorted(glob.glob((HL7_DIR + "/*.hl7"))):       # sorted: "the last message read" is the same on every machine (the parser sorts too)
    raw = open(f, errors="replace").read().replace("\r", "\n")
    for b in re.split(r"(?m)^(?=MSH\|)", raw):
        if not b.startswith("MSH|"): continue
        msh = b.split("\n")[0].split("|"); fac = msh[3].split("^")[-1]; pid = None
        _npi = _adm = ""; _ft = []
        for line in b.split("\n"):
            s = line.split("|")
            if s[0] == "PID": pid = s[3]; FACOF[pid] = fac; FACS.setdefault(pid, set()).add(fac)
            if s[0] == "PV1" and pid:
                NPIOF[pid] = _npi = s[7].split("^")[0] if len(s) > 7 else ""
                ADMIT[pid] = _adm = s[44] if len(s) > 44 else ""
            if s[0] == "FT1": _ft.append((s[25].split("^")[0] if len(s) > 25 else "", s[4] if len(s) > 4 else ""))
        try:
            if pid: MSGOF.setdefault(msg_key(pid, _ft), set()).add((fac, _npi, _adm))
        except Exception: pass
_ctx = {}
def chart_ctx(pid):
    """episode, respparty, refplan, insorder, live {(cpt,dos)} from the chart's own history/detail."""
    if pid in _ctx: return _ctx[pid]
    num = re.sub(r"\D", "", pid)
    root = txh.fetch(num)
    live = set(); rows = set(); sample = None; newest = ""
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        live.add((a.get("proccode"), a.get("dos")))
        if a.get("proccode") in NF_VISIT or a.get("proccode") in HOSP_VISIT or a.get("proccode") in HOME_VISIT: rows.add((a.get("proccode"), a.get("dos"), a.get("facname") or ""))
        if (a.get("dos") or "") > newest or sample is None:
            newest = a.get("dos") or ""; sample = a.get("id")
    ctx = {"live": live, "nfrows": rows, "episode": "", "resp": "", "refplan": "", "insorder": ""}   # nfrows: (code, DOS, facility name) of visit charges, for the place-of-service rule
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    ctx["resp"] = a.get("respparty", ""); ctx["insorder"] = a.get("insorder", "") or "1"; ctx["deceased"] = a.get("deceased", "")
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*sequence="(\d+)"', r)
    ctx["plans"] = pl
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
    facname, npi, admit = own if own else (FACOF.get(fid, ""), NPIOF.get(fid, ""), ADMIT.get(fid, ""))
    fac, pos = FAC.get(facname, ("", "31"))
    nursing = facname in FAC and pos == "31"        # one of the practice's nursing buildings (never the unknown-building default)
    prof = PROFILE.get(npi, "prof13")
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
        if not own and len(FACS.get(fid, ())) > 1 and (nursing or any(FAC.get(_n, ("", ""))[1] == "31" for _n in FACS[fid])):
            raise ValueError("this feed patient has messages from %d buildings in this batch and this message's own building could not be read - "
                             "check the facility, the clinician and the place of service of this visit by hand" % len(FACS[fid]))
        hist = (list(ctx.get("nfrows") or ctx.get("live") or ()) + list(BATCH_NF.get(ctx.get("pid"), ()))) if nursing else ()   # the history is only read for a nursing building
        lpos, lwhy, lkind = pos_lines([(c["cpt"], mdy(c["dos"][:8])) for c in lines], pos, nursing, hist, fac if nursing else None)
        if len(lpos) != len(lines) or any(p not in ("31", "32", pos) for p in lpos): raise ValueError("unexpected place of service %r" % (lpos,))
    except Exception as e:
        lpos = [pos] * len(lines); lwhy = ["rule error"] * len(lines); lkind = [""] * len(lines); pos_err = str(e)[:200] or type(e).__name__
    for c, cpos in zip(lines, lpos):
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
    ext = ""
    if any(c in HOSP for c in cpts) and admit:
        ext = '<extins hospitalizationfrom="%s"/>' % mdy(admit[:8])
    onh = "1" if ext else "0"
    # two-step create (proven 10/28/2026 on pat17476917 vst19458732): addvisit <appt> makes the empty visit, then
    # updvisitwithnewcharges on that visit id adds the charges. VISIT_ID is substituted by the caller.
    vis = ('<visit id="%%VISIT%%" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1">'
           '<chargelist>%s</chargelist>%s</visit>') % (dos, prof, fac, ctx["refplan"], ctx["insorder"], onh, chg, ext)
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
                   {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                    "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis)
    appt = ('<appt id="" patient="%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" '
            'acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (ctx["pid"], ctx["episode"], dos, prof, fac, ctx["refplan"], ctx["insorder"], onh)
    create = amd.msg("addvisit", "chargeentry", {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                     "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt)
    # "pos" stays ONE value for the registers that read it (recon, monitor, the practice database): the first line's; pos_lines has every line
    # dos_lines: every line's own date (a message can carry two); msg_own: False = building / clinician came from the per-patient fallback
    return (create, body), {"dos": dos, "dos_lines": [mdy(c["dos"][:8]) for c in lines], "cpts": cpts, "fac": fac, "pos": lpos[0], "pos_feed": pos, "pos_lines": lpos,
                            "pos_why": lwhy, "pos_kind": lkind, "pos_err": pos_err, "prof": prof, "msg_own": bool(own), "admit": admit, "missing_dx": sorted(missing_dx)}
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
    for rf in _glob.glob("registers/feed_import_*.json"):
        if rf.endswith("_decisions.json"): continue
        try: prior = json.load(open(rf))
        except Exception: continue
        done |= {(r["feed_id"], r["dos"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id")}
        done |= {(r["feed_id"], r["dos_feed"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id") and r.get("dos_feed")}   # re-dated visits keep their feed DOS here
        if rf == REG: done |= {(r["feed_id"], None, None) for r in prior.get("skipped", [])}
        try:
            for r in list(prior.get("skipped") or []) + list(prior.get("failed") or []):
                for _ln in r.get("lines") or []: prior_seen.append((r.get("pid"), list(_ln)))
        except Exception: pass
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
            if dry:
                print("DRY", pid, info); stats["dry"] += 1; count_pos(info, stats); continue
            create, body = body
            r0 = amd.post(create, timeout=120)
            vm = re.search(r'<visit id="(vst\d+)"', r0)
            if not vm:
                stats["FAULT create"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "err": "addvisit: " + re.sub(r"\s+", " ", r0[:500])})
                print("FAULT addvisit", pid, info["dos"], re.sub(r"\s+", " ", r0[:200])); json.dump(reg, open(REG, "w"), indent=1); continue
            r = amd.post(body.replace("%VISIT%", vm.group(1)), timeout=180)
            if "Fault" in r or 'success="0"' in r:
                stats["FAULT"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "err": re.sub(r"\s+", " ", r[:600])})
                print("FAULT", pid, info["dos"], info["cpts"], re.sub(r"\s+", " ", r[:300]))
            else:
                vid = re.search(r'<visit id="(vst\d+)"', r); cids = re.findall(r'<charge id="(charge\d+)"', r)
                fees = re.findall(r'<charge [^>]* fee="([^"]*)"', r)
                # what AdvancedMD stored: its answer echoes the charges - compare their place of service with what was sent (any order).
                # pos_stored None = the answer did not carry it for every line (then nothing is claimed either way)
                try:
                    _st = re.findall(r'<charge id="charge\d+"[^>]*?\bpos="(\d+)"', r)
                    info["pos_stored"] = _st if len(_st) == len(info["pos_lines"]) else None
                    if info["pos_stored"] is not None and sorted(_st) != sorted(info["pos_lines"]):
                        stats["ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE (stored differs from sent)"] += 1
                        print("POS NOT KEPT", pid, info["dos"], info["cpts"], "sent", info["pos_lines"], "stored", _st)
                except Exception: info["pos_stored"] = None
                if info["admit"] and any(c in HOSP for c in info["cpts"]):
                    # the extins child is ignored on create - write the admission date with the proven updextrainsinfo shape
                    for cpt in info["cpts"]:
                        if cpt in HOSP:
                            ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
                                   'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, mdy(info["admit"][:8]))
                            re_ = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": vm.group(1), "nocookie": "1"}, ext), timeout=120)
                            info["admit_written"] = "Fault" not in re_ and 'hospitalizationfrom="%s"' % mdy(info["admit"][:8]) in re_
                reg["created"].append({"feed_id": fid, "pid": pid, "visit": vid.group(1) if vid else "", "charges": cids, "fees": fees, "at": datetime.datetime.utcnow().isoformat(), **info})
                for cpt, _d in zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"])): ctx["live"].add((cpt, _d))   # each line under its OWN date
                stats["created"] += 1; stats["charge lines"] += len(cids); count_pos(info, stats)
                print("OK", pid, info["dos"], info["cpts"], vid.group(1) if vid else "?", cids, fees)
            json.dump(reg, open(REG, "w"), indent=1)
            time.sleep(0.6)
        except Exception as e:
            stats["error"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "lines": seen_lines(msg), "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
            json.dump(reg, open(REG, "w"), indent=1)
        if n % 25 == 0 and n: print("progress", n, dict(stats))
    # 10/29 05:49Z lesson: a live batch whose every line was already in AMD created nothing and so wrote NO import register (verify,
    # inspector, report and the recon then had nothing to read). The register is now always written at the end of a live run, skips included.
    if not dry: json.dump(reg, open(REG, "w"), indent=1)
    _pk = lambda w: sum(v for k, v in stats.items() if k.startswith(w))
    if _pk("ADVANCEDMD DID NOT KEEP") or _pk("feed message not matched"):
        print("POS CHECK: AdvancedMD stored another place of service x%d; not matched to its own message x%d" % (_pk("ADVANCEDMD DID NOT KEEP"), _pk("feed message not matched")))
    # one SHORT line (the ingest shows 110 characters of each of the last three log lines): 91 characters with one-digit counts
    print("POS RULE: CCM 32 x%d, CCM 31 x%d, visits 32 x%d, visits 31 x%d, not applied x%d, unknown bldg x%d" % (
        _pk("POS 32 CCM"), _pk("POS 31 CCM"), _pk("POS 32 nursing"), _pk("POS 31 nursing"), _pk("POS RULE NOT APPLIED"), _pk("POS RULE: building")))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
