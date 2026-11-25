# PLAIN ENGLISH (Deceased-patient guard - William 9/22/2026: "on any straight medicare claims we are never submitting bills on a
#          medicare deceased person"; check the MBI / Medicare record for a date of death before any claim goes out).
# Decides: whether a claim may be submitted. BLOCK when the date of service is AFTER the patient's date of death (any payer).
# Sources, in order: (1) the cache practices/ehpa/registers/deceased_cache.json (pid -> dod / checked date / source) - the GitHub copy is
#   PHI-scrubbed ('[DOB]' = unknown, re-looked-up; 10/14/2026), the real dates live in the workspace and Drive 'workspace mirror',
#          (2) AMD getdemographic 'deceased', (3) a fresh Medicare answer whose 271 carries the date of death (DTP*442 / dateOfDeath):
#          AdvancedMD's own FREE eligibility check first, the vendor's paid answer only when the free one gives no usable answer (the
#          paragraph of 11/25/2026 below).
#          A fresh answer is asked when the claim goes to straight Medicare (FLO02 / car6085) or is CCM and the cache is missing or
#          older than 30 days. A lookup that fails does NOT block (logged 'unverified' for the daily report) - only a positive date of
#          death blocks.
#   11/10/2026 (look-ups part A): (3) is asked through the Stedi client, stedi.medicare(): a PLAIN Medicare check with the member number
#          of the chart's Medicare Part B plan (car6085: an open one first, else the one that ended last), and the look-up by name + DOB
#          + FL when the chart has no usable number, when Medicare does not know it, or when Medicare refuses the plain check for another
#          reason (41, 61, an answer with no Part A or Part B; after a refusal of OUR provider number the rest of the run skips the plain
#          check). The answer is shared with the pre-claim check through medicare_store.py: an answer any helper got in the last 30 days
#          is used (and its own date counts for the 30 days) - but only when it was asked on or after the claim's date of service (or
#          today, for a date still to come): an answer asked BEFORE that date cannot know of a death since, so Medicare is asked again
#          (one plain check; the same holds for the cache's own entry) unless that answer already shows a date of death, which is used
#          as it is with no call (a death is never undone) - and a chart whose call failed today is not bought again today
#          (it stays 'unverified', exactly as before). A date of death a Medicare answer carried during this very check (a plain answer
#          with error 61 and the date, then a look-up that failed) blocks this claim at once; so does a date of death any answer kept in
#          the store shows, whatever its age or month of service, when the guard's own call fails (11/10/2026 re-check fix: the store
#          and this cache travel apart - the cache may be lost, unreadable or scrubbed to '[DOB]'). That fallback takes the EARLIEST
#          date of death any kept answer shows, even when a newer kept answer shows none - it errs toward blocking, as this cache itself
#          keeps a death for good (once a death is in it, every claim of that chart dated after the death is blocked with no new call;
#          second re-check, 11/10/2026: kept as it is). A care-management
#          chart with no Medicare plan keeps the look-up by name, counted as 'guard, no Medicare plan on the chart'. The cache is
#          written one chart at a time into the ONE file it is configured with (DECEASED_CACHE, else the default below), read again just
#          before the write and replaced in one step, so nothing another helper learned meanwhile is lost. No own request, no key file.
#          Only a real Medicare answer is kept as 'no death on record': one that shows Part A / Part B (or a look-up's 72 alone, 'not a
#          Medicare beneficiary', as before); an empty reply with no error, a plain check's 'not found' or a failed call never is.
#   11/25/2026 (William: "do a stedi or advanced md check ... to verify date of death first so as not to bill any after the date of
#          death to straight medicare is stedi able to do that for free?" - the vendor is never free: stedi_prices.py, a plain Medicare
#          check $0.30 and a look-up $1.00 at the first tier; AdvancedMD's own eligibility check is free): when (3) is needed - the
#          same rule as before - the guard FIRST asks AdvancedMD's free check (amd.check_eligibility, 60 seconds, read with
#          elig_amd.summarize; nothing is written to disk for it) on the chart's Medicare Part B plan, the very plan whose number the
#          vendor would be asked with, and buys the vendor's answer only when the free check gives no usable answer. Usable is exactly:
#          a date of death of 8 digits that is a calendar date - taken whatever else the answer says (beside INACTIVE, beside a
#          rejection, on an ended plan, in an answer of an earlier day): it blocks in the same words, source 'amd-medicare-271'; or no
#          rejection at all, ACTIVE, Part A or Part B shown, no date-of-death segment in the answer at all, and every stamp the answer
#          carries about itself (created / changed / response) dated today on AdvancedMD's clock: kept as 'amd: no death on record',
#          checked today. Anything else - a rejection, INACTIVE with no date, a date-of-death segment whose date is empty or is no date
#          (never read as 'no death', whatever stands beside it), an empty or unreadable answer, an HTTP status other than 200, a
#          time-out, any error, an answer AdvancedMD kept from an earlier day - is NOT an answer, and the paid path then runs exactly
#          as before: the free check can never make the guard weaker than it was. Nothing is asked, free or paid, when the answer
#          store already holds an answer the client hands over with no call (one that shows a date of death, or one asked on or after
#          the claim's date of service) - as before; a chart whose paid call failed earlier today is still not bought again today, but
#          the free check costs nothing and is asked for it. After 3 free checks in a row whose call fails - a time-out, an HTTP status
#          other than 200, another error on the way - the free check is not tried again in this process (rules.md: 'If AMD eligibility
#          is down, skip to Stedi'); a rejection, an answer that came but cannot be read, or another unusable answer is not 'down': it
#          does not count and does not start the count again; a usable answer does.
#          DEATH_CHECK_FREE=off (or 0, no, false) switches the free check off; the default is on. No Medicare plan on the chart, a plan
#          with no id, a workspace without elig_amd.py or without amd.check_eligibility: no free check, the paid path as before.
#          COUNTS tells the caller how many checks were asked free, answered free and bought ('paid asked' counts a check the vendor
#          was really asked for - not an answer read back from the store; the usage log has every paid call) - the guard itself
#          prints nothing. A date of death the free check shows is also noted in the answer store, as a death-only entry about no date
#          of service: the store serves it to no reader as a Medicare answer, and the fallback above still finds it when this cache is
#          lost and nothing can be asked; the note leaves the store's 'asked and failed today' mark as it was, so no helper buys that
#          chart again that day. The free answer's name, number and birth date are read and dropped: nothing of them is
#          printed, logged or kept.
#   11/25/2026 (the independent review of that change, the same day - three corrections, each with its checks in
#          tools/selftest/test_lookup_rules.py): a date-of-death segment with no readable date had been read as 'no death on record'
#          and the paid check skipped; three answers in a row that cannot be read had switched the free check off for the run (the
#          order counts a time-out, an HTTP error and an error only); and the note in the answer store had taken the store's 'asked
#          and failed today' mark away, so another helper bought that failing chart again the same day.
# CCM in the month of death: the DOS must be on/before the date of death; a month-end CCM date after the death is blocked.
import os, re, json, time, datetime, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
def _default_cache():
    """Where the cache is when DECEASED_CACHE names none (11/25/2026). The first of these that EXISTS: (1) <this file's folder>/../practices/ehpa/
    registers/deceased_cache.json - the repository's register seen from core/, and a workspace in which a run put a copy there; (2) the flat
    workspace's own register <this file's folder>/registers/deceased_cache.json - the helpers stand side by side there and the copy from Drive is
    merged into that file before the first guard call; (3) the repository's register seen from scripts/helpers/. None exists yet: the
    workspace's registers folder when there is one (the folder a run packs), else (1) as before. Until that day only (1) was tried: in the flat
    workspace no step fills that path (the runs' own lessons of that day), so the guard started EMPTY - every death the practice held was
    unknown to it until Medicare was asked again, and a look-up that failed let the charge through."""
    one = os.path.join(REPO, "practices", "ehpa", "registers", "deceased_cache.json"); flat = os.path.join(HERE, "registers", "deceased_cache.json")
    for p in (one, flat, os.path.join(os.path.dirname(REPO), "practices", "ehpa", "registers", "deceased_cache.json")):
        if os.path.isfile(p): return p
    return flat if os.path.isdir(os.path.join(HERE, "registers")) else one
CACHE = os.environ.get("DECEASED_CACHE") or _default_cache()
MEDICARE = {"FLO02", "car6085"}
CCM = {"99487", "99489", "99490", "99491", "99439", "99437", "G0556", "G0557", "G0558", "G2058",
       "pcode492674", "pcode492675", "pcode492676", "pcode492677"}
MAX_AGE_DAYS = 30
LOG = []
_ASKED = {}          # pid -> the day Medicare was asked for the answer stedi_lookup just used (a shared answer can be older than today)
# 11/25/2026 (William: "is stedi able to do that for free?" - it is not; AdvancedMD's own eligibility check is): the free check comes before
#   the paid one (the header says when, and what counts as an answer). COUNTS is for the caller's one line - the guard itself prints nothing.
COUNTS = {"free asked": 0, "free answered": 0, "paid asked": 0}
FREE_TIMEOUT = 60        # seconds for the one free call
FREE_DOWN_AFTER = 3      # free checks in a row whose CALL fails (a time-out / an HTTP status other than 200 / another error on the way): then no more in this process
FREE_CLOCK = (7, 6, 8)   # AdvancedMD stamps an answer on its own clock - 7 hours behind UTC (docs/captured_calls.md, lesson of 11/6/2026; an
                         # answer asked on UTC day 9/25/2026 is stamped 09/24): 'today' is read on that clock, an hour either way allowed
FREE_STAMPS = ("eligibilitycreatedat", "eligibilitychangedat", "eligibilityresponsedate")     # what the answer's <Results> says about its own age
FREE_NO_DOS = "0" * 8    # the 'date of service' of a death-only note in the answer store: no reader asks about it (see _note_death)
_FREE_FAILS = [0]        # such failures in a row so far, in this process
_FREE = {}               # pid -> True when the answer stedi_lookup just used is AdvancedMD's free one (check() names the source by it)
def _load():
    try: return json.load(open(CACHE))
    except Exception: return {}
def _save(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); json.dump(c, open(CACHE, "w"), indent=1, sort_keys=True)
def _put(pid, rec):
    """11/10/2026: write ONE chart's entry into the one cache file (CACHE). The file is read again just before the write, so what another
    helper or the date-of-death hook wrote meanwhile stays; the new file replaces the old in one step (temporary file, then rename); a file
    that is there but cannot be read is never overwritten (it may hold dates of death)."""
    try:
        with open(CACHE) as fh: txt = fh.read()
        c = json.loads(txt) if txt.strip() else {}
    except FileNotFoundError: c = {}
    except Exception: return False
    if not isinstance(c, dict): return False
    c[pid] = rec; d = os.path.dirname(os.path.abspath(CACHE)); os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".deceased_cache.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as fh: json.dump(c, fh, indent=1, sort_keys=True)
        os.replace(tmp, os.path.abspath(CACHE))
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return True
def _iso(d):
    d = str(d or "").strip()
    if re.match(r"\d{8}$", d): return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else d[:10]
def dod_from_271(j):
    s = json.dumps(j)
    hits = re.findall(r'"[A-Za-z]*[Dd]eath[A-Za-z]*"\s*:\s*"(\d{8})"', s) + re.findall(r"DTP\*442\*D8\*(\d{8})", s)
    return _iso(sorted(set(hits))[0]) if hits else None
def _answered(j):
    """11/10/2026: True for an answer that says something about the patient - Part A or Part B lines or a date of death (an answer read
    back from medicare_store.py counts: the store keeps real answers only). An empty reply with no error is not an answer."""
    if not isinstance(j, dict): return False
    if isinstance(j.get("stored"), dict): return True
    return bool(dod_from_271(j)) or any(isinstance(x, dict) and x.get("insuranceTypeCode") in ("MA", "MB") for x in (j.get("benefitsInformation") or []))
def _medicare_plan(t, dos_iso):
    """11/25/2026: the chart's Medicare Part B plan (car6085) from the chart record already fetched, as its attributes - an open one first
    (no end date, or one on/after the date of service), else the one that ended last; None = no such plan. ONE choice for both: the member
    number the vendor is asked with (_medicare_member) and the plan AdvancedMD's free check is asked about (its id)."""
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r"<insplan [^>]*>", t or "")]
    med = [p for p in plans if p.get("carrier") == "car6085"]
    if not med: return None
    def end(p):
        mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", p.get("enddate") or ""); return f"{mm.group(3)}-{mm.group(1)}-{mm.group(2)}" if mm else ""
    still = [p for p in med if not end(p) or end(p) >= dos_iso]
    return (still or sorted(med, key=end, reverse=True))[0]
def _medicare_member(t, dos_iso):
    """11/10/2026: the member number of the chart's Medicare Part B plan (car6085) from the chart record already fetched - an open one first
    (no end date, or one on/after the date of service), else the one that ended last; "" when that plan has no number; None = no such plan."""
    p = _medicare_plan(t, dos_iso)
    return None if p is None else (p.get("subscribernum") or "").strip()
def _asked_before(j, dos_iso):
    """11/10/2026 (review fix): True for an answer read back from the store that was asked BEFORE the claim's date of service (or before
    today, for a date of service still to come) - it cannot know of a death since then, so the guard asks Medicare again."""
    asked = str(((j or {}).get("stored") or {}).get("asked") or "") if isinstance(j, dict) else ""
    return bool(asked) and asked < min(str(dos_iso or ""), datetime.date.today().isoformat())
def _stored_death(pid):
    """11/10/2026 (re-check fix): the date of death any Medicare answer kept in the answer store (medicare_store.py) shows for this chart,
    whatever its age or month of service - a death is never undone, so it still blocks when the guard's own call fails (the store and this
    cache travel apart: the cache may be lost, unreadable or scrubbed to '[DOB]'). -> YYYY-MM-DD or None."""
    try:
        import sys
        if HERE not in sys.path: sys.path.append(HERE)
        import medicare_store
        d = medicare_store.death(pid)
        return _iso(d) if d else None
    except Exception: return None
def _kept(pid, dos_iso):
    """11/25/2026: True when the answer store (medicare_store.py) already holds a Medicare answer the vendor client hands the guard with NO
    call - one of the last 30 days that shows a date of death, or one asked on or after the claim's date of service (the very tests
    stedi_lookup makes on it below). Then nothing is asked, free or paid: exactly as before the free check."""
    try:
        import sys
        if HERE not in sys.path: sys.path.append(HERE)
        import medicare_store
        hit = medicare_store.get(pid, MAX_AGE_DAYS, dos_iso.replace("-", ""))
    except Exception: return False
    if not isinstance(hit, dict) or hit.get("failed"): return False
    j = {"death": hit.get("death"), "stored": {"asked": hit.get("asked")}}
    return bool(dod_from_271(j)) or not _asked_before(j, dos_iso)
def _free_today(s):
    """11/25/2026: True when every stamp the free answer carries about itself (FREE_STAMPS on its <Results> element - 'amd' in the summary) is
    dated today, on AdvancedMD's clock (FREE_CLOCK) or this machine's. AdvancedMD can hand back an answer it kept (docs/captured_calls.md,
    lesson of 11/6/2026); one from an earlier day cannot know what happened since, so it is never taken as 'no death on record'. No stamp at
    all, or one that cannot be read (AdvancedMD writes MM/DD/YYYY and the time): False."""
    a = s.get("amd") or {}; now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    days = {(now - datetime.timedelta(hours=h)).date() for h in FREE_CLOCK} | {datetime.date.today()}
    def day(x):
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\b", x)
        try: return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except Exception: return None
    stamps = [x for x in (str(a.get(k) or "").strip() for k in FREE_STAMPS) if x]
    return bool(stamps) and all(day(x) in days for x in stamps)
def _real_d8(d):
    """True for 8 digits that are a calendar date (YYYYMMDD)."""
    try: return bool(re.fullmatch(r"\d{8}", d)) and bool(datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])))
    except Exception: return False
def _note_death(pid, d8):
    """11/25/2026: a date of death AdvancedMD's free check showed is noted in the answer store (medicare_store.py) too, as a death-only entry
    about no date of service (FREE_NO_DOS). The store hands an answer only to a reader asking about its own month of service or an earlier
    date, so nobody is served this entry as a Medicare answer - but medicare_store.death(), which _stored_death reads, shows every date of
    death kept. So a death the free check found still blocks when this cache is lost and nothing can be asked, as one the vendor found
    does. Never raises: the cache keeps the date either way.
    11/25/2026 (review): the store drops a chart's 'asked and failed today' mark for ANY answer written to it - but this note is no
    Medicare answer, so the mark is read first and put back as it was: no helper buys the same failing chart again that day."""
    try:
        import sys
        if HERE not in sys.path: sys.path.append(HERE)
        import medicare_store
        try: was = medicare_store.get(pid, 0, "9" * 8)       # a date of service later than any answer is about: only today's 'asked and failed' mark can come back
        except Exception: was = None
        medicare_store.put(pid, {"death": d8, "errors": []}, "amd free check, date of death only", "guard", FREE_NO_DOS)
        if isinstance(was, dict) and was.get("failed"):
            medicare_store.put(pid, {"errors": was.get("errors") or [], "reason": was.get("reason")}, "failed", was.get("who"), was.get("dos"))
    except Exception: pass
def free_down():
    """True once the free check is off for the rest of this process: FREE_DOWN_AFTER free checks in a row failed (the caller's line can say so)."""
    return _FREE_FAILS[0] >= FREE_DOWN_AFTER
def free_lookup(pid, plan):
    """11/25/2026: ONE free check - AdvancedMD's own eligibility check on the chart's Medicare plan (plan = _medicare_plan's attributes) - and
    what it says about a death -> (dod YYYY-MM-DD, True) for a date of death, (None, True) for 'no death on Medicare's record' as of today,
    (None, False) when it gives no usable answer or was not asked: the caller then buys the vendor's answer exactly as before. The header
    says what is usable. Never raises, prints nothing, keeps nothing of the answer but the date."""
    insid = re.sub(r"\D", "", str((plan or {}).get("id") or ""))               # AdvancedMD's check takes the digits of id="ins123"
    if not insid or free_down() or str(os.environ.get("DEATH_CHECK_FREE") or "").strip().lower() in ("off", "0", "no", "false"): return None, False
    try:
        import sys
        if HERE not in sys.path: sys.path.append(HERE)
        import amd, elig_amd
        free = amd.check_eligibility
    except Exception: return None, False                                        # a workspace without elig_amd.py or without the free call: not asked, the paid path as before
    COUNTS["free asked"] += 1
    try:
        code, body = free(insid, timeout=FREE_TIMEOUT)
        if code != 200: raise RuntimeError("HTTP %s" % code)
    except Exception:
        _FREE_FAILS[0] += 1; return None, False                                 # the CALL failed - a time-out, an HTTP status other than 200, another error on the way: 3 in a row and the free check is off
    try:
        s = elig_amd.summarize(body if isinstance(body, str) else json.dumps(body))
        d8 = str(s.get("date_of_death") or "").strip()
        # 11/25/2026 (review): 'no death on record' is taken only from an answer with NO date-of-death segment - summarize() sets the key whenever the answer
        # carries one (DTP 442), and a segment whose date is empty, missing or no date is never read as 'no death' (the paid check is then made, as before)
        alive = "date_of_death" not in s and not s.get("aaa") and s.get("status") == "ACTIVE" and bool(s.get("partA") or s.get("partB")) and _free_today(s)
    except Exception: return None, False                                        # 11/25/2026 (review): an answer that came but cannot be read is an unusable answer, not 'down' - neither counted nor a new start of the count
    if not (_real_d8(d8) or alive): return None, False                          # no answer (a rejection, INACTIVE with no date, an earlier day's answer, a date that is none): neither counted as down nor as answered
    _FREE_FAILS[0] = 0; COUNTS["free answered"] += 1
    if d8: _note_death(pid, d8)
    return (_iso(d8) if d8 else None), True
def stedi_lookup(pid, dos_iso):
    """Medicare record for pid as of dos -> (dod or None, ok). Since 11/25/2026 AdvancedMD's free check is asked before the vendor (free_lookup)."""
    import amd, stedi
    _ASKED.pop(pid, None); _FREE.pop(pid, None)
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60)
    m = re.search(r'<patient [^>]*>', t); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    if a.get("deceased") not in (None, "", "0"): return _iso(a.get("deceased")) if re.search(r"\d", a.get("deceased")) else dos_iso, True
    last, first = (a.get("name", "").split(",") + [""])[:2]; first = first.strip().split(" ")[0]
    mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", a.get("dob", "")); dob8 = f"{mm.group(3)}{mm.group(1)}{mm.group(2)}" if mm else ""
    # 11/10/2026: ONE Medicare answer through the client (it holds the key and the provider block, counts the call, shares the answer)
    number = _medicare_member(t, dos_iso)
    # 11/25/2026 (William): AdvancedMD's FREE check first, on that same plan - unless the answer store already holds an answer the client
    # hands over with no call (then nothing is asked at all, as before). A usable free answer ends the look-up here: nothing is bought.
    if not (hasattr(stedi, "medicare") and _kept(pid, dos_iso)):
        dod, ok = free_lookup(pid, _medicare_plan(t, dos_iso))
        if ok: _FREE[pid] = True; return dod, True
    ask = dict(member_id=number or None, dos=dos_iso.replace("-", ""), state="FL", pid=pid,
               who="guard" if number is not None else "guard, no Medicare plan on the chart")
    paid = 1                        # 11/25/2026, COUNTS: the vendor is asked now - unless the answer below is one read back from the answer store
    try:
        if hasattr(stedi, "medicare"):
            j, how = stedi.medicare(first, last.strip(), dob8, **ask, max_age_days=MAX_AGE_DAYS)
            if how != "failed" and not dod_from_271(j) and _asked_before(j, dos_iso):   # a shared answer asked BEFORE this date of service: asked again, fresh
                j, how = stedi.medicare(first, last.strip(), dob8, **ask)            # (re-check fix: one that already shows a death is used as it is - a death is never undone)
        else:                       # an older client in this workspace: the look-up as before, through the client
            j, how = stedi.mbi(first, last.strip(), dob8, "FL", dos_iso.replace("-", ""), pid=pid), "lookup"
        if isinstance(j, dict) and isinstance(j.get("stored"), dict): paid = 0
        errs = [str(e).split(" ")[0] for e in stedi.med_summ(j)["errors"]]
    except Exception: return None, False
    finally: COUNTS["paid asked"] += paid
    dod = dod_from_271(j)
    if how == "failed": return dod, False
    ok = how == "plain" or errs == ["72"] or (not errs and _answered(j))     # 72 on a LOOK-UP = not a Medicare beneficiary: nothing to find, still a valid answer
    if ok or dod: _ASKED[pid] = (j.get("stored") or {}).get("asked") or datetime.date.today().isoformat()
    return dod, ok
def check(pid, dos, carrier=None, proc=None, allow_lookup=True):
    """-> (blocked: bool, reason: str). Blocks only on a known date of death earlier than the DOS."""
    pid = re.sub(r"\D", "", str(pid)); dos = _iso(dos); c = _load(); rec = c.get(pid)
    # 10/14/2026: a cache restored from GitHub carries the PHI gate's '[DOB]' in place of the date of death (35 charts) - a
    # non-date dod is UNKNOWN (re-lookup), never compared as a string (which silently let every DOS through).
    if rec and rec.get("dod") and not re.match(r"\d{4}-\d{2}-\d{2}$", str(rec.get("dod"))):
        rec = dict(rec); rec["dod"] = None; rec["checked"] = "2000-01-01"; c[pid] = rec
    stale = rec is None or (datetime.date.today() - datetime.date.fromisoformat(rec.get("checked", "2000-01-01"))).days > MAX_AGE_DAYS
    # 11/10/2026 (review fix): an entry checked BEFORE this claim's date of service cannot know of a death since - asked again (one plain check)
    stale = stale or str(rec.get("checked") or "") < min(dos, datetime.date.today().isoformat())
    needs = (carrier in MEDICARE) or ((proc or "") in CCM)
    if allow_lookup and needs and stale and not (rec and rec.get("dod")):
        dod, ok = stedi_lookup(pid, dos)
        if not ok and not dod:              # 11/10/2026 (review fix): a date of death the hook wrote during THIS check (a plain answer with 61) counts now
            try: seen = (_load().get(pid) or {}).get("dod")
            except Exception: seen = None
            if seen and re.match(r"\d{4}-\d{2}-\d{2}$", str(seen)): dod = seen
        if not ok and not dod: dod = _stored_death(pid)     # 11/10/2026 (re-check fix): a death an answer in the store already shows still blocks
        if ok or dod:
            free = _FREE.pop(pid, None)         # 11/25/2026: the answer is AdvancedMD's free one - the source says so; the block wording and the staleness rule are the same
            rec = {"dod": dod, "checked": _ASKED.pop(pid, None) or datetime.date.today().isoformat(),
                   "src": ("amd-medicare-271" if free else "stedi-medicare-271") if dod else ("amd: no death on record" if free else "stedi: no death on record")}
            c[pid] = rec; _put(pid, rec)
        else: LOG.append(f"pat{pid} DOS {dos}: date of death UNVERIFIED (lookup failed)")
    dod = (rec or {}).get("dod")
    if dod and dos and dos > dod:
        return True, f"pat{pid} DOS {dos} is after date of death {dod} ({(rec or {}).get('src')}) - claim must not be submitted" + \
                     ("; CCM in the month of death needs a DOS on/before the death date, else void" if (proc or "") in CCM and dos[:7] == dod[:7] else "; void the charge")
    return False, ""
def check_charge(chargeid, sequencenumber=None, allow_lookup=True):
    """Reads the charge (patient, visit date, procedure, carrier at the billed sequence) and applies check()."""
    import resave
    import xml.etree.ElementTree as ET
    cid = re.sub(r"\D", "", str(chargeid)); d = ET.fromstring(resave.detail(cid))
    v = d.find(".//visit"); p = d.find(".//patient"); ch = [x for x in d.iter("charge") if x.get("id") == "charge" + cid]
    pid = re.sub(r"\D", "", p.get("id")) if p is not None else ""
    carrier = None
    if sequencenumber is not None:
        for ip in d.iter("insplan"):
            if str(ip.get("sequence")) == str(sequencenumber): carrier = ip.get("carrier")
    proc = ch[0].get("proccode") if ch else None
    return check(pid, v.get("date") if v is not None else "", carrier, proc, allow_lookup)
def record(pid, j, src="stedi-medicare-271"):
    """Store what a Medicare 271 says about death for pid (called by scripts/helpers/stedi.py on every Medicare lookup)."""
    pid = re.sub(r"\D", "", str(pid)); dod = dod_from_271(j); c = _load()
    errs = [e.get("code") for e in (j.get("errors") or [])]
    if dod or errs == ["72"] or (not errs and _answered(j)):          # 11/10/2026: an empty reply is not kept as 'no death on record'
        _put(pid, {"dod": dod, "checked": datetime.date.today().isoformat(), "name": (c.get(pid) or {}).get("name"),
                   "src": src if dod else ("stedi: not a Medicare beneficiary" if errs == ["72"] else "stedi: no death on record")})
    return dod
