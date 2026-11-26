# PLAIN ENGLISH (deceased cache <-> Drive 'workspace mirror' copy, 10/14/2026)
# Decides: nothing. Packs the guard's cache (pid -> dod / checked / src / name) into the compact names-free form kept on
#   Drive 'workspace mirror' as deceased_cache.json ({"dated": {pid: [dod, checked]}, "nodeath": {pid: checked}} - and, since the third
#   round of 11/25/2026, "noday": the paragraphs at the end of this header) and
#   unpacks that form back into the cache the guard reads - merging: a real date always beats a scrubbed '[DOB]' and an
#   entry with none; of two real dates for one chart the EARLIER stays; a 'no death' note never replaces an entry whose
#   dod is set, and otherwise the newest 'checked' wins (the GitHub copy is PHI-gated: its '[DOB]' is, to the guard, a
#   death ON RECORD whose day cannot be read - the copy on Drive is what gives the days back).
# Rules it uses: no names on Drive either (the guard never needs them); chart ids + dates only.
# Never touches: AMD, Stedi.
#   python3 dg_drive.py pack   <cache.json> <drive.json>
#   python3 dg_drive.py unpack <drive.json> <cache.json> [<cache2.json> ...]   (merge into every cache path given)
# 11/25/2026 (the second verification of that day's change): a day a helper wrote in eight digits or as MM/DD/YYYY IS a day - pack left
#   such a chart out of the Drive copy altogether (neither dated nor 'no death'), so the next run did not know it; and unpack stumbled over
#   an entry whose source is null. A day is now read in every shape a helper has written it in and goes to Drive as YYYY-MM-DD.
# 11/25/2026 (the independent check of that round - the merge of step 0c must not UNDO a death on record): a 'no death' note from the Drive
#   copy replaced a scrubbed '[DOB]' whenever its check date was the newer one - the chart then read 'no death on record' and its next claim
#   was cleared with nobody asked, by the very step that runs before the first guard call; and a LATER day from Drive replaced an EARLIER
#   day in the cache when Drive's check date was newer, so a visit between the two passed. Now: a note never replaces an entry whose dod is
#   set - a day that can be read OR one that cannot; of two days the EARLIER stays, whatever the check dates (it blocks more - the guard's
#   own rule for two cache files); a real day still beats a '[DOB]'. A death goes off the record on the owner's word only (below).
#   The reading of a day is the guard's own (deceased_guard._day - tools/selftest/test_lookup_rules.py holds the two together).
# 11/25/2026 (the third round - the second independent check of that day; each rule has its check in tools/selftest/test_lookup_rules.py):
#   THE COPY IS v2 - a third list beside 'dated' and 'nodeath'. 'noday' = {pid: checked}: a death on record whose day is not known (the chart's
#   own mark, a placeholder) - it was in neither list, so on the next machine such a chart read 'clear' for a claim to another payer. A 'noday'
#   note makes a chart the cache holds no death for (no entry, or 'no death' checked BEFORE the note) a death on record with no day; a 'no death'
#   checked on the same day as the note or after it, a day and a placeholder of the cache's own stay. An older copy has no such list and is
#   merged as before.
#   WHAT IS A DEATH ON RECORD is the guard's reading too (unread = deceased_guard._unread) - an entry with any other value in the day's place is
#   one without an answer: packed into no list, and replaced by a note or a day.
# 11/25/2026 (the fourth round - the third independent check of that day; tools/selftest/test_lookup_rules.py):
#   THE OWNER'S WORD. A death that is WRONG goes off the record on William's word only (death_off_record.py): his word resets the record and
#   Medicare is asked afresh - the helper writes the RE-ASK entry (no death, a check date long ago, reask = the day the helper ran). The third
#   round's copy carried a fourth list for his words, with the approval text; that list is GONE, and a copy that still has one: the list is
#   ignored. pack writes a RE-ASK entry as a 'no death' note with its check date as it stands - long ago, stale on every machine, so the chart
#   is asked about there. The copy carries no word to another machine: a cache that still holds the death keeps it until his word is given in
#   that workspace. ONE narrow rule is all the merge knows of his word (the guard's carry holds the same - deceased_guard._reask, _after): while
#   the entry of a cache carries reask, a day or a 'noday' note of the copy whose check date is ON OR BEFORE that day, or that has no check
#   date, is NOT brought into it - the older record must not come back before Medicare was asked (the copy of a run from before the reset still
#   lists it); a death checked AFTER that day is taken as for any chart, and the fields of the reset go. And a 'no death' note of the copy is no
#   answer to the fresh question: it leaves such an entry exactly as the helper wrote it - the check date too. (Written into the entry, a
#   note's newer check date went into the next copy packed from that cache, and the next machine read 'no death on record, checked
#   yesterday' - clear, with nobody asked.)
#   A CACHE FILE THAT CANNOT BE READ (cut off, no table) IS KEPT AND REPLACED. Until the third round the merge wrote over it - whatever day only
#   that file held was gone. The third round passed it over: it was never repaired, every later run started with a guard that knew nothing of
#   it, and a claim the copy's day would have blocked was approved. Now the file is MOVED ASIDE in its own folder, under its own name +
#   '.unreadable-<UTC stamp>', and the merged table - what the copy gives - is written in its place: nothing is lost, and the run knows the
#   days again. ONE line 'DECEASED CACHE REPLACED: <path> could not be read - kept as <name>; the Drive copy's table stands in its place - TOP
#   OF THE REPORT'; the command ends 0 when every path was merged. A path that cannot be WRITTEN (or an unreadable file that can be neither
#   moved nor replaced - it is then left exactly as it is) keeps the line 'DECEASED CACHE NOT MERGED: <path> ... - TOP OF THE REPORT', the
#   other paths are still merged, and the command ends 1. pack on a cache that cannot be read ends with ONE plain line 'DECEASED CACHE NOT
#   PACKED: ...' and exit 2 - it ended on a Python error. Each file is written through a temporary file, in one step.
#   WHAT IS A DEATH ON RECORD WITH NO DAY, a little wider (the guard's _unread says which, word for word): also any text in square or angle
#   brackets, a masked date, and the words deceased, dead, died, expired, redacted, y, yes.
import os, json, re, sys, datetime, tempfile
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
def day(v):
    """A day as YYYY-MM-DD when it is a real calendar date written YYYY-MM-DD, in eight digits or as MM/DD/YYYY (the first and the last may carry a time
    behind the day, as AdvancedMD stamps its dates); None for anything else. THE GUARD'S OWN READING, step for step (deceased_guard._iso and _day) - this tool
    loads no other helper, so the reading is written out here, and tools/selftest/test_lookup_rules.py holds the two together over every shape. (11/25/2026,
    the independent check of the second round: a day with a time behind it was a day to the guard and none here - pack left the chart out of both lists.)"""
    s = str(v or "").strip()
    if re.match(r"\d{8}$", s): s = "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    else:
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
        s = "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2))) if m else s[:10]
    if not v or not DATE.match(s): return None
    try: return datetime.date.fromisoformat(s).isoformat()
    except ValueError: return None
NO_DAY = "day not known"      # the guard's own NO_DAY: what stands in the day's place for a chart whose own record says deceased while nobody named a day
DEATH_WORDS = {"deceased", "dead", "died", "expired", "redacted", "y", "yes"}      # the guard's own DEATH_WORDS: the words that stand for a death with no day in a cache's day place
def unread(v):
    """True for a dod value that is a death ON RECORD whose day cannot be read: no day, and the guard's 'day not known', a text with at least four digits in
    it (a damaged date), any text in square or angle brackets in any letter case (the privacy gate's placeholder is one), a masked date (nothing but the
    letter X and separators, at least four X), or one of DEATH_WORDS as the whole value in any letter case. False for a day and for every other value (None,
    '', blanks, the words None / null / unknown, '0', a number): that is NO dod. THE GUARD'S OWN READING (deceased_guard._unread), written out here as day()
    is - tools/selftest/test_lookup_rules.py holds the two and the import's together over every shape. (11/25/2026, the third round: until then any text in a
    dod field counted as a death on record; the fourth round: the bracketed texts, the masked date and the words.)"""
    if not isinstance(v, str) or day(v) is not None: return False
    s = v.strip()
    return (s == NO_DAY or len(re.findall(r"\d", s)) >= 4 or bool(re.search(r"\[[^\[\]]*[A-Za-z][^\[\]]*\]|<[^<>]*[A-Za-z][^<>]*>", s))
            or s.lower() in DEATH_WORDS or (bool(re.fullmatch(r"[Xx/. -]+", s)) and len(re.findall(r"[Xx]", s)) >= 4))

REASK_KEYS = ("reask", "approved_by")      # the guard's own REASK_KEYS: the fields of an entry whose record was reset on the owner's word - they go when a death is written into it
REASK_UNDATED = "9999-12-31"               # the guard's own REASK_UNDATED: the day such an entry reads as reset on when its reask field names no date - later than any check date
def reask(rec):
    """The day the record of a death was reset on the owner's word (YYYY-MM-DD) when the entry is a RE-ASK entry - it carries reask and holds NO death -
    REASK_UNDATED when that field names no date, None for every other entry. The guard's own reading (deceased_guard._reask)."""
    if not isinstance(rec, dict) or not rec.get("reask") or day(rec.get("dod")) or unread(rec.get("dod")): return None
    return day(rec.get("reask")) or REASK_UNDATED
def after(checked, since):
    """True when a check date can be read - YYYY-MM-DD, a time behind it or not - and lies AFTER that day. Never for the day itself, a date in another shape,
    one that is no date, or none: such a death is the older record. The guard's own reading (deceased_guard._after)."""
    s = str(checked or "")[:10]
    return bool(DATE.match(s)) and day(s) is not None and s > since
FORMAT = "deceased_cache_drive v2: dated = {pid: [dod, checked]}, nodeath = {pid: checked}, noday = {pid: checked} (a death on record whose day is not known)"
def pack(cache_path, out_path):
    """The cache as the compact copy for Drive -> how many charts went into each list (dated, nodeath, noday). Chart ids and dates only: nothing else of an
    entry travels. An entry whose record was reset on the owner's word (a RE-ASK entry) is a 'no death' note with its check date as it stands - long ago; an
    entry whose dod is any other value that is no day (unread says which) is one without an answer and goes into no list. Raises when the cache cannot be read
    as a table; the copy is written through a temporary file, so a failure leaves whatever stood at out_path as it was."""
    with open(cache_path) as fh: c = json.load(fh)
    if not isinstance(c, dict): raise ValueError("the cache holds no table")
    c = {k: v for k, v in c.items() if isinstance(v, dict)}
    dated = {k: [day(v["dod"]), v.get("checked")] for k, v in c.items() if v.get("dod") and day(v["dod"])}
    nodeath = {k: v.get("checked") for k, v in c.items() if v.get("dod") in (None, "")}      # an entry with NO value in the day's place; one with any other value that is no day is an entry without an answer (unread) - in neither list
    noday = {k: v.get("checked") for k, v in c.items() if unread(v.get("dod"))}              # a death on record with no day that can be read: the chart's own mark ('day not known'), the placeholder
    fd, tmp = tempfile.mkstemp(prefix=".deceased_cache_drive.", suffix=".tmp", dir=os.path.dirname(os.path.abspath(out_path)))
    try:
        with os.fdopen(fd, "w") as fh: json.dump({"format": FORMAT, "dated": dated, "nodeath": nodeath, "noday": noday}, fh, separators=(",", ":"), sort_keys=True)
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return len(dated), len(nodeath), len(noday)

REPLACED = "DECEASED CACHE REPLACED: %s could not be read - kept as %s; the Drive copy's table stands in its place - TOP OF THE REPORT"      # one line for a cache file that could not be read: the path as it was given and the name it is kept under, in its own folder - never an entry
NOT_MERGED = "DECEASED CACHE NOT MERGED: %s %s - TOP OF THE REPORT"      # one line for a cache path the merge had to leave alone: the path as it was given and why - never an entry
NOT_PACKED = "DECEASED CACHE NOT PACKED: %s could not be read as the guard's cache, or its copy for Drive could not be written (%s) - no new copy was made, the copy on Drive stays as it is - TOP OF THE REPORT"
def _table(path):
    """What a cache file holds -> (its table, "") - an empty table for a file that is not there yet or is empty - or (None, why) for a file that is THERE but
    cannot be read as a table (cut off, not JSON, a list). Such a file may hold dates of death: it is never written over - unpack keeps it under another name."""
    try:
        with open(path) as fh: txt = fh.read()
    except FileNotFoundError: return {}, ""
    except Exception as e: return None, "is there but cannot be opened (%s)" % type(e).__name__
    if not txt.strip(): return {}, ""
    try: c = json.loads(txt)
    except Exception: return None, "is there but cannot be read (it is cut off or is no JSON)"
    return (c, "") if isinstance(c, dict) else (None, "is there but holds no table")
def _aside(path):
    """The name an unreadable cache file is kept under: its own name + '.unreadable-<UTC stamp>', in its own folder - one that is not taken yet."""
    base = path + ".unreadable-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"); name = base; n = 1
    while os.path.lexists(name): n += 1; name = "%s-%d" % (base, n)
    return name
def _write(path, c, aside=None):
    """The cache file, written whole: a temporary file beside it, then put in its place in one step - a write that fails half-way leaves the file as it was.
    aside: the name the file that stands at `path` now is kept under (an unreadable file - _aside): it is moved there only when the new table is safely in its
    temporary file, and put back when the last step fails - so the unreadable file is either kept AND replaced, or left exactly as it is."""
    fd, tmp = tempfile.mkstemp(prefix=".deceased_cache.", suffix=".tmp", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w") as fh: json.dump(c, fh, indent=1, sort_keys=True)
        if aside: os.replace(path, aside)
        try: os.replace(tmp, path)
        except Exception:
            if aside: os.replace(aside, path)
            raise
    finally:
        if os.path.exists(tmp): os.remove(tmp)
def _pair(e):
    """One entry of the Drive copy's 'dated' list -> (day as it stands there, check date or None); a bare day counts as a day with no check date, a check date
    that is no text as none - a hand-made copy must not end the merge on an error."""
    if isinstance(e, (list, tuple)): e = list(e) + [None, None]
    else: e = [e, None]
    return e[0], (e[1] if isinstance(e[1], str) else None)
def unpack(drive_path, cache_paths, skipped=None):
    """Merge the Drive copy into every cache path given -> the number of dated entries written. A cache file that is there but cannot be read is MOVED ASIDE in
    its own folder (_aside) and the merged table is written in its place, with ONE printed line (REPLACED). A path that cannot be written - and an unreadable
    file that can be neither moved nor replaced, which is then left exactly as it is - gets ONE printed line (NOT_MERGED) and is noted in `skipped` (a list, when
    the caller gives one); the other paths are still merged. (11/25/2026: until the third round an unreadable file was written over - whatever day only it held
    was gone; the third round passed it over - it was never repaired and the run did not know the days; the fourth round keeps it and replaces it.)"""
    d = json.load(open(drive_path)); n = 0; skipped = skipped if isinstance(skipped, list) else []
    def _text(x): return x if isinstance(x, str) else None      # a check date that is no text is none
    def _list(name): return d.get(name) if isinstance(d, dict) and isinstance(d.get(name), dict) else {}      # one list of the copy; a copy that has none, or holds something else under that name, has an empty one
    for cp in cache_paths:
        c, why = _table(cp); aside = None
        if c is None:
            if not os.path.isfile(cp):
                skipped.append(cp); print(NOT_MERGED % (cp, "is there but is no file - it was left as it is; the other path(s) were merged")); continue
            aside = _aside(cp); c = {}      # an unreadable file: the merged table of the copy alone takes its place, and the file is kept under that name (_write)
        m = 0; notes = _list("nodeath")
        def entry(pid): return c.get(pid) if isinstance(c.get(pid), dict) else {}
        def plain(cur): return {k: v for k, v in cur.items() if k not in REASK_KEYS}      # the entry without the fields of a reset: a death is written into it
        for pid, e in _list("dated").items():
            dod, checked = _pair(e)
            cur = entry(pid); new = day(dod); have = day(cur.get("dod")); since = reask(cur)
            if not new: continue                                                     # the Drive copy holds days only; anything else is not taken
            if since and not after(checked, since): continue                         # THE ONE RULE about the owner's word: the cache's record of this chart was reset on that day - a day checked on or before it, or with no check date, is the older record and does not come back before Medicare was asked
            if have and (new > have or (new == have and (checked or "") < (_text(cur.get("checked")) or ""))): continue      # of two days the EARLIER stays, whatever the check dates; the same day: the newer check date
            c[pid] = {**plain(cur), "dod": new, "checked": checked or cur.get("checked"), "src": cur.get("src") if str(cur.get("src") or "").startswith(("stedi-medicare-271", "amd-medicare-271")) else "stedi-medicare-271 (drive copy)"}; m += 1
        for pid, checked in notes.items():
            cur = entry(pid); checked = _text(checked)
            if day(cur.get("dod")) or unread(cur.get("dod")): continue               # a death on record - a day that can be read OR one that cannot (unread: the placeholder) - is never undone by a no-death note
            if reask(cur) is not None: continue                                      # an entry that waits for Medicare's fresh answer (the record was reset on the owner's word) is no 'no death on record' a newer note could bring up to date: it stays exactly as the helper wrote it - check date and all, so pack still writes it as a note of long ago
            if (checked or "") >= (_text(cur.get("checked")) or ""):
                c[pid] = {**cur, "dod": None, "checked": checked, "src": cur.get("src") or "stedi: no death on record (drive copy)"}
        for pid, checked in _list("noday").items():      # 'noday' (the third round): a death on record whose day is not known (the chart's own mark, a placeholder)
            cur = entry(pid); checked = _text(checked); since = reask(cur)
            if day(cur.get("dod")) or unread(cur.get("dod")): continue               # a death of the cache's own - a day, or one with no day - stays as it is
            if since:
                if not after(checked, since): continue                               # THE ONE RULE again: against a record that was reset the note counts only when it was checked AFTER that day
            elif cur and (checked or "") <= (_text(cur.get("checked")) or ""): continue      # 'no death on record' checked on the same day as the note or after it stays
            c[pid] = {**plain(cur), "dod": NO_DAY, "checked": checked, "src": "a death on record, its day not known (drive copy)"}
        try: _write(cp, c, aside); n += m
        except Exception as e:
            skipped.append(cp)
            print(NOT_MERGED % (cp, (why + " and could be neither kept under another name nor replaced (%s) - it was left exactly as it is, never written over (it may hold dates of death)" if aside else "could not be written (%s) - the file is as it was") % type(e).__name__ + "; the other path(s) were merged"))
            continue
        if aside: print(REPLACED % (cp, os.path.basename(aside)))
    return n

if __name__ == "__main__":
    if sys.argv[1] == "pack":
        try: print("packed dated/nodeath/noday:", pack(sys.argv[2], sys.argv[3]))
        except Exception as e:
            print(NOT_PACKED % (sys.argv[2], type(e).__name__)); sys.exit(2)      # the run's last step: one plain line for the top of the report, never a traceback
    elif sys.argv[1] == "unpack":
        _bad = []; print("dated entries merged:", unpack(sys.argv[2], sys.argv[3:], _bad))
        if _bad: sys.exit(1)      # a cache path could not be written (its line is above): the merge is NOT complete - the run says so at the top of the report
    else: sys.exit(__doc__)
