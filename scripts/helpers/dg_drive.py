# PLAIN ENGLISH (deceased cache <-> Drive 'workspace mirror' copy, 10/14/2026)
# Decides: nothing. Packs the guard's cache (pid -> dod / checked / src / name) into the compact names-free form kept on
#   Drive 'workspace mirror' as deceased_cache.json ({"dated": {pid: [dod, checked]}, "nodeath": {pid: checked}} - and, since the third
#   round of 11/25/2026, "noday" and "off_record": the paragraph at the end of this header) and
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
#   own rule for two cache files); a real day still beats a '[DOB]'. A death is taken off the record on the owner's word only (below).
#   The reading of a day is the guard's own (deceased_guard._day - tools/selftest/test_lookup_rules.py holds the two together).
# 11/25/2026 (the third round - the second independent check of that day; each rule has its check in tools/selftest/test_lookup_rules.py):
#   THE COPY IS v2 - two more lists beside 'dated' and 'nodeath'. 'off_record' = {pid: [the date of the owner's word, the approval text]}: a chart
#   William said is alive, taken off the record by death_off_record.py. 'noday' = {pid: checked}: a death on record whose day is not known (the
#   chart's own mark, a placeholder) - it was in neither list, so on the next machine such a chart read 'clear' for a claim to another payer.
#   An older copy has neither list and is merged as before.
#   ONE RULE for the owner's word, the guard's own (deceased_guard._beats): his word of date D beats every day reported on or before D and a
#   death with no day reported on or before D; a day after D is a new death. So unpack applies an 'off_record' note over a cache entry whose
#   dod is a day on or before D, or a death with no day checked on or before D, and where the cache holds no death for the chart (the entry
#   becomes the OFF entry: dod null, off_record, approved_by; its name stays) - never over a later day; a 'dated' day on or before the date of
#   a word the CACHE holds is not taken (the copy of a run from before his word still lists it - it used to come back with step 0c), a later
#   day is taken; a 'noday' note counts against his word only when it was checked after it, and otherwise makes a chart the cache holds no
#   death for (no entry, or 'no death' checked before the note) a death on record with no day.
#   WHAT IS A DEATH ON RECORD is the guard's reading too (unread = deceased_guard._unread): the placeholder, 'day not known', a damaged date -
#   an entry with any other value in the day's place is one without an answer: packed into no list, and replaced by a note or a day.
#   A CACHE FILE THAT CANNOT BE READ IS NEVER WRITTEN OVER (it may hold dates of death - it was replaced by the table the copy gives): the
#   path is passed over with ONE line 'DECEASED CACHE NOT MERGED: <path> ... - TOP OF THE REPORT', the other paths are still merged, and the
#   command ends 1 when a path was passed over or could not be written. Each file is written through a temporary file, in one step.
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
def unread(v):
    """True for a dod value that is a death ON RECORD whose day cannot be read: no day, and the privacy gate's placeholder (an upper-case word in square
    brackets), the guard's 'day not known', or a text with at least four digits in it (a damaged date). False for a day and for every other value (None, '',
    blanks, the words None / null / unknown, '0', a number): that is NO dod. THE GUARD'S OWN READING (deceased_guard._unread), written out here as day() is -
    tools/selftest/test_lookup_rules.py holds the two and the import's together over every shape. (11/25/2026, the third round: until then any text in a dod
    field counted as a death on record.)"""
    if not isinstance(v, str) or day(v) is not None: return False
    s = v.strip()
    return bool(re.search(r"\[[A-Z]+\]", s)) or s == NO_DAY or len(re.findall(r"\d", s)) >= 4

OFF_SRC = "off the record on the owner's word"      # the guard's own OFF_SRC: the source of an entry death_off_record.py wrote (dod null, off_record = the date of William's word)
OFF_KEYS = ("off_record", "approved_by")            # the fields of his word: they go from an entry when a later day - a new death - is taken
def off(rec):
    """The date of the owner's word (YYYY-MM-DD) when the entry is OFF the record on his word - it holds no death and its off_record names a real day - else
    None. The guard's own reading (deceased_guard._off)."""
    if not isinstance(rec, dict) or day(rec.get("dod")) or unread(rec.get("dod")): return None
    return day(rec.get("off_record"))
def beats(word, d, checked):
    """ONE RULE for a death reported against the owner's word of date `word` - the guard's own (deceased_guard._beats): a DAY after that date is a new death
    and stands; a day on or before it does not. A death on record with no day (d None) stands only when it was reported - checked - after that date."""
    return (d > word) if d else (str(checked or "")[:10] > word)
FORMAT = ("deceased_cache_drive v2: dated = {pid: [dod, checked]}, nodeath = {pid: checked}, noday = {pid: checked} (a death on record whose day is not known), "
          "off_record = {pid: [the date of the owner's word, the approval text]} (taken off the record by death_off_record.py)")
def pack(cache_path, out_path):
    """The cache as the compact copy for Drive -> how many charts went into each list (dated, nodeath, noday, off_record). An entry taken off the record is
    'no death' with its check date AND a note of the owner's word; an entry whose dod is any other value that is no day (unread says which) is one without an
    answer and goes into no list."""
    c = json.load(open(cache_path)); c = {k: v for k, v in c.items() if isinstance(v, dict)}
    dated = {k: [day(v["dod"]), v.get("checked")] for k, v in c.items() if v.get("dod") and day(v["dod"])}
    nodeath = {k: v.get("checked") for k, v in c.items() if v.get("dod") in (None, "")}      # an entry with NO value in the day's place; one with any other value that is no day is an entry without an answer (unread) - in neither list
    noday = {k: v.get("checked") for k, v in c.items() if unread(v.get("dod"))}              # a death on record with no day that can be read: the chart's own mark ('day not known'), the placeholder
    off_record = {k: [off(v), v.get("approved_by")] for k, v in c.items() if off(v)}          # the owner's word: its date and the approval text
    json.dump({"format": FORMAT, "dated": dated, "nodeath": nodeath, "noday": noday, "off_record": off_record}, open(out_path, "w"), separators=(",", ":"), sort_keys=True)
    return len(dated), len(nodeath), len(noday), len(off_record)

NOT_MERGED = "DECEASED CACHE NOT MERGED: %s %s - TOP OF THE REPORT"      # one line for a cache path the merge left alone: the path as it was given and why - never an entry
def _table(path):
    """What a cache file holds -> (its table, "") - an empty table for a file that is not there yet or is empty - or (None, why) for a file that is THERE but
    cannot be read as a table (cut off, not JSON, a list). Such a file may hold dates of death: it is never written over (the guard's own rule, _put)."""
    try:
        with open(path) as fh: txt = fh.read()
    except FileNotFoundError: return {}, ""
    except Exception as e: return None, "is there but cannot be opened (%s)" % type(e).__name__
    if not txt.strip(): return {}, ""
    try: c = json.loads(txt)
    except Exception: return None, "is there but cannot be read (it is cut off or is no JSON)"
    return (c, "") if isinstance(c, dict) else (None, "is there but holds no table")
def _write(path, c):
    """The cache file, written whole: a temporary file beside it, then put in its place in one step - a write that fails half-way leaves the file as it was."""
    fd, tmp = tempfile.mkstemp(prefix=".deceased_cache.", suffix=".tmp", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w") as fh: json.dump(c, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
def _pair(e):
    """One entry of the Drive copy's 'dated' list -> (day as it stands there, check date or None); a bare day counts as a day with no check date, a check date
    that is no text as none - a hand-made copy must not end the merge on an error."""
    if isinstance(e, (list, tuple)): e = list(e) + [None, None]
    else: e = [e, None]
    return e[0], (e[1] if isinstance(e[1], str) else None)
def unpack(drive_path, cache_paths, skipped=None):
    """Merge the Drive copy into every cache path given -> the number of dated entries written. A path whose file is there but cannot be read, and a path that
    cannot be written, is passed over with ONE printed line (NOT_MERGED) and noted in `skipped` (a list, when the caller gives one); the other paths are still
    merged. (11/25/2026, the third round: such a file was replaced by the table the Drive copy gives - whatever day only that file held was gone.)"""
    d = json.load(open(drive_path)); n = 0; skipped = skipped if isinstance(skipped, list) else []
    def _text(x): return x if isinstance(x, str) else None      # a check date that is no text is none
    for cp in cache_paths:
        c, why = _table(cp)
        if c is None:
            skipped.append(cp); print(NOT_MERGED % (cp, why + " - it was left exactly as it is, never written over (it may hold dates of death); the other path(s) were merged")); continue
        m = 0; notes = d.get("nodeath") if isinstance(d.get("nodeath"), dict) else {}
        def entry(pid): return c.get(pid) if isinstance(c.get(pid), dict) else {}
        def plain(cur): return {k: v for k, v in cur.items() if k not in OFF_KEYS}      # the entry without the fields of the owner's word
        for pid, e in (d.get("dated") or {}).items():
            dod, checked = _pair(e)
            cur = entry(pid); new = day(dod); have = day(cur.get("dod")); word = off(cur)
            if not new: continue                                                     # the Drive copy holds days only; anything else is not taken
            if word and not beats(word, new, None): continue                         # the cache holds the OWNER'S WORD for the chart: a day on or before its date is not taken (the copy of a run from before his word still lists it); a later day is a new death
            if have and (new > have or (new == have and (checked or "") < (_text(cur.get("checked")) or ""))): continue      # of two days the EARLIER stays, whatever the check dates; the same day: the newer check date
            c[pid] = {**plain(cur), "dod": new, "checked": checked or (None if word else cur.get("checked")), "src": cur.get("src") if str(cur.get("src") or "").startswith(("stedi-medicare-271", "amd-medicare-271")) else "stedi-medicare-271 (drive copy)"}; m += 1
        for pid, checked in notes.items():
            cur = entry(pid); checked = _text(checked)
            if day(cur.get("dod")) or unread(cur.get("dod")): continue               # a death on record - a day that can be read OR one that cannot (unread: the placeholder) - is never undone by a no-death note
            if (checked or "") >= (_text(cur.get("checked")) or ""):
                c[pid] = {**cur, "dod": None, "checked": checked, "src": cur.get("src") or "stedi: no death on record (drive copy)"}
        # 11/25/2026 (the third round) - the copy's two more lists (an older copy has neither and is merged as before):
        for pid, checked in (d.get("noday") if isinstance(d.get("noday"), dict) else {}).items():      # 'noday': a death on record whose day is not known (the chart's own mark, a placeholder)
            cur = entry(pid); checked = _text(checked); word = off(cur)
            if day(cur.get("dod")) or unread(cur.get("dod")): continue               # a death of the cache's own - a day, or one with no day - stays as it is
            if word:
                if not beats(word, None, checked): continue                          # against the owner's word the note counts only when it was checked AFTER the date of his word
            elif cur and (checked or "") <= (_text(cur.get("checked")) or ""): continue      # 'no death on record' checked on or after the note stays
            c[pid] = {**plain(cur), "dod": NO_DAY, "checked": checked, "src": "a death on record, its day not known (drive copy)"}
        for pid, e in (d.get("off_record") if isinstance(d.get("off_record"), dict) else {}).items():      # 'off_record': the owner's word - its date and the approval text
            word, text = _pair(e); word = day(word)
            if not word: continue
            cur = entry(pid); have = day(cur.get("dod")); mark = unread(cur.get("dod"))
            if (off(cur) or "") >= word or ((have or mark) and beats(word, have, cur.get("checked"))): continue      # a later word of the cache's own stays; so does a death his word does NOT cover - a day after its date, a death with no day reported after it
            seen = (_text(notes.get(pid)) if (have or mark) else _text(cur.get("checked"))) or ""      # the check date that travels with the note: the copy's 'no death' note for the chart, or the cache's own entry when it held no death
            new = {"dod": None, "checked": max(seen, word), "src": OFF_SRC, "off_record": word, "approved_by": text}
            if "name" in cur: new["name"] = cur["name"]
            c[pid] = new
        try: _write(cp, c); n += m
        except Exception as e:
            skipped.append(cp); print(NOT_MERGED % (cp, "could not be written (%s) - the file is as it was; the other path(s) were merged" % type(e).__name__))
    return n

if __name__ == "__main__":
    if sys.argv[1] == "pack": print("packed dated/nodeath/noday/off_record:", pack(sys.argv[2], sys.argv[3]))
    elif sys.argv[1] == "unpack":
        _bad = []; print("dated entries merged:", unpack(sys.argv[2], sys.argv[3:], _bad))
        if _bad: sys.exit(1)      # a cache path was passed over or could not be written (its line is above): the merge is NOT complete - the run says so at the top of the report
    else: sys.exit(__doc__)
