# PLAIN ENGLISH (Deceased-patient guard - William 9/22/2026: "on any straight medicare claims we are never submitting bills on a
#          medicare deceased person"; check the MBI / Medicare record for a date of death before any claim goes out).
# Decides: whether a claim may be submitted. BLOCK when the date of service is AFTER the patient's date of death (any payer).
# Sources, in order: (1) the cache practices/ehpa/registers/deceased_cache.json (pid -> dod / checked date / source) - the GitHub copy is
#   PHI-scrubbed ('[DOB]' = a death ON RECORD whose day cannot be read here - see the last paragraph), the real dates live in the workspace and Drive 'workspace mirror',
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
# 11/25/2026 (the second verification of that day's change - each rule is shown by tools/selftest/test_lookup_rules.py and test_death_check_review.py):
#          ONE CACHE: with no DECEASED_CACHE named, the file is the workspace's own registers/deceased_cache.json (a flat workspace: the helpers side by
#          side with a registers folder), else the repository's register; and once per process every DAY another cache file of the workspace holds is
#          carried into it (_carry) - the feed's helpers kept a file of their own until then, and the two never met. A DAY IN ANOTHER SHAPE IS A DAY:
#          eight digits and MM/DD/YYYY are read (_day). A DEATH ON RECORD WHOSE DAY CANNOT BE READ (the scrubbed copy) IS NOT 'NO DEATH': the chart is
#          asked about whatever the payer and the code, once per process; only a DAY is an answer for it - Medicare's 'no death on record' does not
#          undo it, in check() or in record() - and while nobody names one check() raises DayLost: the caller fails closed (amd.rebill_charge answers
#          409, death_check_review.py says NOT CHECKED, the feed's import enters no visit). check_charge raises Unreadable when the charge's own detail
#          shows no chart, no visit date or no row of the charge - it used to answer 'not blocked'. What could not be written (a cache file that cannot
#          be read is never written over) is remembered for the rest of the process (_UNSAVED). cache_state() gives a caller the file's state in counts.
# 11/25/2026 (the independent check of that second round - each rule is shown by tools/selftest/test_lookup_rules.py, where each check names its finding):
#          THE GUARD KEEPS A DEATH FOR GOOD, ALSO AGAINST ITS OWN HOOK: record() no longer writes an answer WITHOUT a day over an entry that holds a dod - a day that
#          can be read, or one that cannot (it still wrote 'no death on record' over a readable day, and the chart's next claim passed with nobody asked). A death is
#          taken off the record by hand only. THE CHART'S OWN 'deceased' MARK WITHOUT A DATE is a death on record with no day: Medicare is asked for the day as for any
#          chart; a day that comes is the day; when none comes the entry says so (NO_DAY) and check() raises DayLost - the claim's own date of service used to be
#          taken for the day, and the claim cleared itself. THE DEFAULT CACHE GOES BY WHERE THIS FILE STANDS (_default_cache): a stray registers folder beside the
#          helpers of the repository's own layout no longer hides the repository's register. THE CARRY (_carry) also takes a placeholder that stands only in another
#          cache file, and with a cache in use that cannot be read it keeps in memory what the other files hold. cache_state() carries first; covered(pid, dos) says
#          whether the cache holds an answer that covers a claim (death_check_review.py asks it before it lets an 'unverified' line go); and no 'UNVERIFIED' line
#          is logged for a chart whose day is lost - that claim is not cleared, it does not 'go on'.
# CCM in the month of death: the DOS must be on/before the date of death; a month-end CCM date after the death is blocked.
import os, re, json, time, datetime, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
_REPO_PATHS = (os.path.join(REPO, "practices", "ehpa", "registers", "deceased_cache.json"),                      # the repository's register seen from core/ (one up) ...
               os.path.join(os.path.dirname(REPO), "practices", "ehpa", "registers", "deceased_cache.json"))      # ... and from scripts/helpers/ (two up)
def _default_cache():
    """Where the cache is when DECEASED_CACHE names none (11/25/2026). In a run's flat workspace - the helpers side by side, a registers folder
    beside them - it is that folder's deceased_cache.json: the file step 0c merges the copy from Drive into and the pack uploads, whatever other
    copy lies around (what such a copy holds is carried in - _carry). Anywhere else: the repository's register, seen from core/ or from
    scripts/helpers/, when it is there; else <this file's folder>/../practices/ehpa/registers/deceased_cache.json as before. Until that day only
    that last path was tried: in the flat workspace no step fills it (the runs' own lessons of that day), so the guard started EMPTY - every
    death the practice held was unknown to it until Medicare was asked again, and a look-up that failed let the charge through. (The second
    verification, the same day: a copy a run had made at that old path must not win over the workspace's register - what the guard learned
    went into a file no step packs.)
    The independent check of that round (a regression of it): the registers FOLDER beside this file was taken as soon as it was there - and in the
    REPOSITORY's own layout any helper started from scripts/helpers leaves such a folder (death_check_review.py writes its register under the folder it is
    started in). From then on the guard there read a file that is not there and the repository's register was not even one of the files it carries from: a
    visit after a day that register holds answered 'not blocked'. So the layout is decided by where this file STANDS:
      REPOSITORY layout - this folder is named core and <one up>/practices/ehpa/registers/deceased_cache.json is a file, or this folder is helpers under
        scripts and <two up>/practices/ehpa/registers/deceased_cache.json is a file: that register, whatever folder lies beside the helpers;
      otherwise a FLAT workspace when a registers folder is beside this file: <this folder>/registers/deceased_cache.json, file there or not;
      otherwise the first of the two repository paths that is a file, else the one-up path."""
    one, two = _REPO_PATHS
    name = os.path.basename(HERE)
    if name == "core" and os.path.isfile(one): return one
    if name == "helpers" and os.path.basename(REPO) == "scripts" and os.path.isfile(two): return two
    if os.path.isdir(os.path.join(HERE, "registers")): return os.path.join(HERE, "registers", "deceased_cache.json")
    for p in (one, two):
        if os.path.isfile(p): return p
    return one
CACHE = os.environ.get("DECEASED_CACHE") or _default_cache()
MEDICARE = {"FLO02", "car6085"}
CCM = {"99487", "99489", "99490", "99491", "99439", "99437", "G0556", "G0557", "G0558", "G2058",
       "pcode492674", "pcode492675", "pcode492676", "pcode492677"}
MAX_AGE_DAYS = 30
LOG = []
class DayLost(RuntimeError):
    """A date of death is on record for the chart, its day cannot be read here, and Medicare named none: the claim is NOT cleared."""
class Unreadable(RuntimeError):
    """The charge's own read shows nothing to compare (no chart, no visit date, no row of the charge): the charge is NOT cleared."""
LOST_WORDS = "a date of death is on record for this chart but its day cannot be read here, and Medicare named none - the claim is not cleared (merge the cache copy from Drive, or look the chart up)"
UNREADABLE_WORDS = "the charge's own detail shows no chart, no visit date or no row of this charge - there is nothing to compare, so the charge is not cleared"
_CARRIED = [False]       # whether the days of the workspace's other cache files were carried into the cache in use (once per process - _carry)
_LOST_ASKED = set()      # charts with a death on record whose day cannot be read, asked about in this process without a day coming back: a second question about one asks nobody again
_UNSAVED = {}            # chart -> the entry this process learned but could NOT write (the cache file cannot be read, so it is never written over): every later answer of the process still sees it
_ASKED = {}          # pid -> the day Medicare was asked for the answer stedi_lookup just used (a shared answer can be older than today)
_NODAY = {}          # pid -> True when the chart's own record says deceased and names NO day that can be read (stedi_lookup notes it, check() takes it) - see NO_DAY
NO_DAY = "day not known"                                # what check() writes in the day's place for such a chart: a death ON RECORD whose day is not known - never a day (_day reads it as none)
NO_DAY_SRC = "amd: deceased on the chart, no date"      # ... and the source of that entry
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
def _others():
    """The other cache files a workspace can hold beside the one in use: the feed helpers' own file of before (deceased_cache_local.json beside
    this file), the register beside this file, and the register at either repository path (one up: the copy a run made at the path this guard
    used to read; two up: the repository's own, seen from scripts/helpers) - every file _default_cache can choose, except the one in use. It
    only looks whether each is a file: it reads nothing and writes nothing."""
    mine = os.path.realpath(CACHE); out = []
    for p in (os.path.join(HERE, "deceased_cache_local.json"), os.path.join(HERE, "registers", "deceased_cache.json")) + _REPO_PATHS:
        if os.path.isfile(p) and os.path.realpath(p) != mine and os.path.realpath(p) not in [os.path.realpath(x) for x in out]: out.append(p)
    return out
def _carry():
    """ONE cache (11/25/2026, the second verification of that day's change). A workspace held up to three cache files that never met: the feed
    helpers kept their own (deceased_cache_local.json), the Charge Review check and the rebill read the register, and a run's hand copy lay at
    the old path. A day the feed had learned was unknown to the check before approvals, and the other way round. Now every day another cache
    file of this workspace holds is carried into the cache in use, once per process, before the first answer: a day that can be read beats
    none and beats one that cannot be read; of two days the EARLIER stays (it blocks more). A file that cannot be read is passed over. It
    never raises.
    The independent check of that round (its finding 8) - two things the carry left behind:
    (a) a PLACEHOLDER - a dod on record that is no day - that stands ONLY in another file. It is a death on record: when the cache in use holds
        no dod for that chart (no entry, or 'no death on record') it is carried as it stands, so the chart is asked about whatever its payer
        and is not cleared while nobody names the day (it read 'clear' with nobody asked, while the feed's import held the same chart). A day
        or a placeholder the cache in use holds itself stays as it is. An entry without any dod is still not carried - it is asked about
        again when it matters.
    (b) a cache in use that CANNOT BE READ. Nothing is written over it (_put's own rule) - but the carry gave up altogether, and a day another
        file held was unknown for the whole process. Now what would have been carried is kept in memory (_UNSAVED): every answer of the
        process sees it; the file stays as it was."""
    if _CARRIED[0]: return
    _CARRIED[0] = True
    try:
        mine = None; unreadable = False
        for path in _others():
            try:
                with open(path) as fh: other = json.load(fh)
            except Exception: continue
            if not isinstance(other, dict): continue
            if mine is None:
                try:
                    with open(CACHE) as fh: txt = fh.read()
                    mine = json.loads(txt) if txt.strip() else {}
                    if not isinstance(mine, dict): raise ValueError("the cache in use is no table")
                except FileNotFoundError: mine = {}
                except Exception: mine = {}; unreadable = True      # (b): nothing of it can be read and nothing is written over it - what is carried stays in memory
            for pid, rec in other.items():
                if not isinstance(rec, dict) or not rec.get("dod") or not re.match(r"\d+$", str(pid)): continue
                pid = str(pid); day = _day(rec.get("dod"))
                cur = mine.get(pid) if isinstance(mine.get(pid), dict) else {}
                have = _day(cur.get("dod"))
                if day:
                    if have and have <= day: continue
                elif cur.get("dod"): continue      # (a): a placeholder is carried only where the cache in use holds no dod at all for the chart
                new = dict(cur); new.update({"dod": day or str(rec.get("dod")), "checked": str(rec.get("checked") or cur.get("checked") or datetime.date.today().isoformat()),
                                             "src": str(rec.get("src") or cur.get("src") or "carried from another cache file of this workspace")})
                if unreadable: _UNSAVED[pid] = new
                elif not _put(pid, new): continue
                mine[pid] = new
    except Exception: pass
def _load():
    _carry()
    try: c = json.load(open(CACHE))
    except Exception: c = {}
    if not isinstance(c, dict): c = {}
    c.update(_UNSAVED)      # (11/25/2026, the second verification: with a cache file that cannot be read the guard kept nothing it learned, and a later question about the same chart in the same start was answered without it)
    return c
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
def _day(v):
    """A cached day as YYYY-MM-DD when it is a real calendar date in a shape a helper has written it in (YYYY-MM-DD, eight digits, MM/DD/YYYY);
    None for anything else - the scrubbed placeholder, a text, a date that is none. (11/25/2026, the second verification: two helpers of that
    day wrote the day as eight digits, and such an entry was read as 'unknown' - a claim to another payer passed with no word.)"""
    s = _iso(v) if v else ""
    if not re.match(r"\d{4}-\d{2}-\d{2}$", s): return None
    try: return datetime.date.fromisoformat(s).isoformat()
    except ValueError: return None
def _checked(rec):
    """The day an entry was checked, as a date; 1/1/2000 for an entry that names none or names it in another shape (the copy from Drive can
    carry null there) - such an entry is stale, and it raises nothing."""
    try: return datetime.date.fromisoformat(str((rec or {}).get("checked") or "")[:10])
    except ValueError: return datetime.date(2000, 1, 1)
def _stale(rec, dos):
    """Whether an entry that names no day must be asked about again for a claim of that date of service (dos as YYYY-MM-DD): there is no entry, it was
    checked more than MAX_AGE_DAYS ago, or - 11/10/2026, review fix - it was checked BEFORE the claim's date of service (before today, for a date still to
    come): it cannot know of a death since (one plain check asks again). ONE rule for check() and for covered()."""
    today = datetime.date.today()
    return rec is None or (today - _checked(rec)).days > MAX_AGE_DAYS or str(rec.get("checked") or "") < min(str(dos or ""), today.isoformat())
def covered(pid, dos):
    """True when the cache holds an answer that COVERS a claim of this chart and date of service: a day that can be read (the claim is decided by that
    day), or an entry that is not stale for that date by check()'s own rule (_stale: checked within MAX_AGE_DAYS and not before the date of service, or
    today for a date to come). False for everything else - no entry, an older answer, a death on record whose day cannot be read. It asks nobody, changes
    nothing and never raises. (11/25/2026, the independent check of the second round, finding 5: death_check_review.py asks it before it lets a 'date
    of death unverified' line go - the line was dropped although nobody had answered for that charge.)"""
    try:
        rec = _load().get(re.sub(r"\D", "", str(pid)))
        if not isinstance(rec, dict): return False
        if rec.get("dod"): return _day(rec.get("dod")) is not None
        return not _stale(rec, _iso(dos))
    except Exception: return False
def cache_state():
    """What the cache file looks like, in counts only - for a caller's one line, never an entry: {"file": it is there, "readable": it can be
    read as the table it is, "charts": its entries, "days": entries with a day that can be read, "lost": entries with a day on record that
    cannot be read here (the scrubbed copy)}. (11/25/2026, the second verification: a caller could tell only that the file was missing.)
    It carries the workspace's other cache files in FIRST (_carry - the independent check of that round, finding 11): the counts are of the cache the
    guard answers from. Taken before the carry they could be untrue - 'no file' two lines before a block by a day the carry had brought, '2 lost'
    although both days had been filled in. It reads the FILE: what the guard holds in memory only (_UNSAVED - a file that cannot be read) is not counted."""
    _carry()
    out = {"file": os.path.isfile(CACHE), "readable": False, "charts": 0, "days": 0, "lost": 0}
    if not out["file"]: return out
    try:
        with open(CACHE) as fh: txt = fh.read()
        c = json.loads(txt) if txt.strip() else {}
    except Exception: return out
    if not isinstance(c, dict): return out
    recs = [v for v in c.values() if isinstance(v, dict)]
    out.update(readable=True, charts=len(c), days=sum(1 for v in recs if _day(v.get("dod"))), lost=sum(1 for v in recs if v.get("dod") and not _day(v.get("dod"))))
    return out
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
    _ASKED.pop(pid, None); _FREE.pop(pid, None); _NODAY.pop(pid, None)
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60)
    m = re.search(r'<patient [^>]*>', t); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    # The chart's own 'deceased' attribute. With a DATE in it (any shape _day reads) that date is the day, as before - nothing is asked. WITHOUT a date that can be
    # read (a mark such as Y or true, a number, a date that is none) it is a death ON RECORD with no day. Until 11/25/2026 the claim's OWN date of service was then
    # taken for 'the day': the claim was cleared by itself and that date written into the cache as the day, for good (the independent check of that day's second
    # round, finding 10). Now Medicare is asked for the day as for any chart; a day that comes is the day; when none comes check() writes the entry as a death on
    # record whose day is not known (NO_DAY) and raises DayLost - the claim is not cleared.
    if a.get("deceased") not in (None, "", "0"):
        flagged = _day(a.get("deceased"))
        if flagged: return flagged, True
        _NODAY[pid] = True
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
    pid = re.sub(r"\D", "", str(pid)); dos = _iso(dos); c = _load(); rec = c.get(pid); lost = False
    if not isinstance(rec, dict): rec = None      # an entry of another shape (a text, a list) is no entry: the chart is asked about as one the cache does not know
    # 10/14/2026: a cache restored from GitHub carries the PHI gate's placeholder in place of the day (35 charts) - a day that cannot be read
    # is UNKNOWN (asked again), never compared as a string (which silently let every DOS through). 11/25/2026 (the second verification): a
    # day in eight digits or MM/DD/YYYY IS a day (two helpers wrote it so, and the claim passed); and a day that cannot be read is asked
    # about WHATEVER the payer and the code - until then only a Medicare or care-management claim was, and any other passed with no word.
    if isinstance(rec, dict) and rec.get("dod"):
        day = _day(rec.get("dod")); rec = dict(rec); c[pid] = rec
        if day is None: rec["dod"] = None; rec["checked"] = "2000-01-01"; lost = True
        else: rec["dod"] = day
    stale = _stale(rec, dos)
    needs = (carrier in MEDICARE) or ((proc or "") in CCM) or lost
    if allow_lookup and needs and stale and not (rec and rec.get("dod")) and not (lost and pid in _LOST_ASKED):
        dod, ok = stedi_lookup(pid, dos); noday = bool(_NODAY.pop(pid, None))      # noday: the chart's own record says deceased and names no day (stedi_lookup)
        if not ok and not dod:              # 11/10/2026 (review fix): a date of death the hook wrote during THIS check (a plain answer with 61) counts now
            try: seen = _load().get(pid); seen = _day(seen.get("dod")) if isinstance(seen, dict) else None
            except Exception: seen = None
            if seen: dod = seen
        if not ok and not dod: dod = _stored_death(pid)     # 11/10/2026 (re-check fix): a death an answer in the store already shows still blocks
        # 11/25/2026 (the second verification): for a chart with a death ON RECORD whose day cannot be read, only a DAY is an answer. Medicare's
        # 'no death on record' does not undo it: a death the practice learned from the facility or the chart is not in Medicare's answer for
        # weeks, and the placeholder stands where such a day stood. The entry stays as it is and the claim is not cleared (DayLost below).
        if (lost or noday) and not dod: _LOST_ASKED.add(pid)
        if noday and not dod and not lost:      # the chart says deceased, names no day, and Medicare named none: a death ON RECORD whose day is not known - written so, and not cleared (DayLost below). An entry that already says so (lost) stays as it was.
            rec = {"dod": NO_DAY, "checked": datetime.date.today().isoformat(), "src": NO_DAY_SRC}; c[pid] = rec; lost = True
            if not _put(pid, rec): _UNSAVED[pid] = rec
        elif dod or (ok and not lost):
            free = _FREE.pop(pid, None)         # 11/25/2026: the answer is AdvancedMD's free one - the source says so; the block wording and the staleness rule are the same
            rec = {"dod": dod, "checked": _ASKED.pop(pid, None) or datetime.date.today().isoformat(),
                   "src": ("amd-medicare-271" if free else "stedi-medicare-271") if dod else ("amd: no death on record" if free else "stedi: no death on record")}
            c[pid] = rec; lost = False
            if not _put(pid, rec): _UNSAVED[pid] = rec
        elif not ok and not lost: LOG.append(f"pat{pid} DOS {dos}: date of death UNVERIFIED (lookup failed)")      # never for a chart whose day is lost (the independent check of 11/25/2026, finding 13): 'unverified' means 'not a block - the charge goes on', and that claim does not - DayLost below; the caller says NOT CHECKED or holds the visit. A count of these lines (the feed's 'date of death UNVERIFIED xN') is so of charges that went on
    # 11/25/2026 (the second verification): a death IS on record for this chart, its day cannot be read here, and nobody answered (or nobody
    # was asked: a question from the cache only). That is not 'no death on record' - the claim is not cleared: the caller fails closed on this
    # error (amd.rebill_charge answers 409 and sends nothing; death_check_review.py says NOT CHECKED). The entry stays as it was.
    if lost: raise DayLost(LOST_WORDS)
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
    pid = re.sub(r"\D", "", p.get("id") or "") if p is not None else ""
    # 11/25/2026 (the second verification): a read that shows nothing to compare - a Fault, no chart, no visit date, no row of this charge -
    # was answered 'not blocked', and amd.rebill_charge sent the rebill although the cache held the day. Now it is an error the caller fails
    # closed on (the rebill answers 409 'could not verify', the check before approvals says NOT CHECKED). Fixed words: no chart, no date.
    if not pid or v is None or not str(v.get("date") or "").strip() or not ch: raise Unreadable(UNREADABLE_WORDS)
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
        old = c.get(pid) if isinstance(c.get(pid), dict) else {}
        # THE GUARD KEEPS A DEATH FOR GOOD - also against this hook. An answer WITHOUT a day never writes over an entry that holds a dod: a day that can be read, or
        # a death on record whose day cannot be read here. (The second verification of 11/25/2026 closed that for the unreadable day only; the independent check of
        # that round found the other half: a readable day was still written over by another helper's 'no death on record' - or by 'not a Medicare beneficiary', or by
        # a look-up that hit another person - and the chart's next claim passed with nobody asked.) A death is taken off the record by hand only.
        if not dod and old.get("dod"): return dod
        _put(pid, {"dod": dod, "checked": datetime.date.today().isoformat(), "name": old.get("name"),
                   "src": src if dod else ("stedi: not a Medicare beneficiary" if errs == ["72"] else "stedi: no death on record")})
    return dod
