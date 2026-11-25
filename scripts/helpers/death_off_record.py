#!/usr/bin/env python3
# PLAIN ENGLISH (taking a death OFF the deceased guard's record - the ONE way out of a death the guard holds WRONGLY; written 11/25/2026, in
#   the third round of the date-of-death check)
# Why: the deceased guard keeps a death for good (deceased_guard.py: no answer without a day undoes one, the carry and the merge of the Drive
#   copy bring it back from every place that still holds it), and the run VOIDS a charge dated after it - never a question for William. So a
#   death on record that is WRONG - ONE Medicare answer that hit another person, a stale placeholder in a stray cache file, a mark on the
#   chart - blocked a living patient's claims for good, and nothing but a hand edit in up to five places took it out again; the next carry or
#   the next merge undid the hand edit (the second independent check of that day, finding 2).
# Decides: NOTHING. The owner decides - William - and this helper writes down that he did.
# ON WHOSE WORD: William's, and only his. The approval is given word for word with --approved-by and must read exactly
#   William <M>/<D>/<YYYY> (board)   or   William <M>/<D>/<YYYY> (chat)
#   - the date of his word (a real calendar date, not after today) and where he said it: on the board or in chat. Anything else - another
#   name, another place, more words, a date that is none - changes NOTHING and ends 2. No free text: the approval is kept in the cache
#   entries and in this helper's register, and both reach a public repository. What was typed is never printed back.
# WHAT HIS WORD COVERS (one rule, the guard's own - deceased_guard._beats): every day reported on or before its date, and a death on record
#   with no day that was reported on or before its date. A day AFTER the date of his word is a new death: it is NOT taken off here (its line
#   says so), and wherever it is reported later the guard takes it as for any chart. To take such a day off he gives his word again, of a
#   later date.
# WHAT IT DOES: it reads the guard's cache in use (deceased_guard.CACHE) and every other cache file the guard knows (deceased_guard._others():
#   the feed helpers' file of before, a register beside the helpers, the copies at the old paths) - each file itself, never through the guard's
#   own read (that one carries entries from file to file). Where the chart's entry holds a death his word covers - a day, or a death on
#   record whose day cannot be read (the guard's own reading: _day, _unread) - the entry becomes the OFF entry:
#     {"dod": null, "checked": <today>, "src": "off the record on the owner's word", "off_record": <the date of his word, YYYY-MM-DD>,
#      "approved_by": <the approval text>}   (a name the entry had is kept; nothing else of the file changes).
#   The cache in use gets the OFF entry whenever ANY file held such a death for the chart - also when its own entry said 'no death on record'
#   or it had none: the guard answers from that file, and the owner's word must stand there when the same wrong answer comes in again.
#   Only a cache in use that already holds his word of the same or a LATER date keeps that entry as it is: an earlier word never takes the
#   place of a later one (the guard's carry and the Drive merge hold the same) - a day reported between the two dates stays covered.
#   A file that cannot be read is passed over and said (it is never written over). Each file is read again just before it is written and
#   replaced in one step.
# WHAT THE OFF ENTRY MEANS afterwards is the guard's and the Drive tool's business (deceased_guard.py, dg_drive.py): the chart is 'no death on
#   record'; a day on or before the date of his word is not taken again - from an answer, a look-up, another cache file or the Drive copy;
#   a later day is a new death and is taken. The Drive copy learns of it at the next pack (step 0c: pack the cache again at the end of the
#   run), and its note takes the day off the caches of the next machine. One thing stays the chart's own: when the chart's AdvancedMD record
#   itself says deceased (a mark with no date), the guard reads that mark again at its next look-up after the day of his word and holds the
#   claim again - the mark has to come off the chart in AdvancedMD too.
# WHAT IT WRITES: the cache files above, and ONE row appended to registers/death_off_record.json under the folder it is started in - the chart
#   id, a UTC stamp, the approval text, the number of cache files changed - and nothing else. --dry writes nothing at all.
# WHAT IT PRINTS: one line for each cache file - the path, what stood there in words (never the day itself), what was done - and a LAST line
#   that starts 'DEATH OFF THE RECORD:' and ends ' - TOP OF THE REPORT': the run puts it at the top of its report, word for word.
# EXIT: 0 = done (with --dry: there is something to take off). 3 = nothing on record for that chart that his word covers - nothing was
#   changed, no row was written. 2 = the usage or the approval is not in shape, the guard beside it is missing or from before 11/25/2026,
#   its own register cannot be read, a cache file could not be written, or an error of its own - one plain line, never a traceback; after
#   a 2 read the lines above it: they say what was written before it stopped.
# Usage (from the workspace, beside deceased_guard.py):
#   python3 death_off_record.py <chart number> --approved-by "William MM/DD/YYYY (board)"     ("(chat)" when he said it in chat; --dry shows what it would do)
# Never: decides anything; takes a word that is not William's in the shape above; talks to AdvancedMD or the vendor; asks Medicare; prints or
#   writes a day somebody passed away on, a name or a number; touches a charge, a visit or a claim; changes an entry of another chart; writes
#   over a file it cannot read. A charge the run already voided for that death is not put back by this helper - that is William's to say.
import os, re, sys, json, datetime, tempfile
DEATH_OFF_RECORD_VERSION = "2026-11-25.1"      # this helper's own version: change it with EVERY revision
APPROVAL = re.compile(r"William (\d{1,2})/(\d{1,2})/(\d{4}) \((board|chat)\)")      # the owner's word, exactly: who, the date, where - and nothing else
USAGE = 'usage: python3 death_off_record.py <chart number> --approved-by "William MM/DD/YYYY (board)" [--dry] - exactly that text with the date of his word (not after today), "(board)" or "(chat)"'
REGISTER = os.path.join("registers", "death_off_record.json")
HEAD = "DEATH OFF THE RECORD: "; TAIL = " - TOP OF THE REPORT"
NEEDS = ("CACHE", "_others", "_day", "_unread", "_beats", "_off", "OFF_SRC")      # what the guard beside this helper must have: the third round's guard (it knows what the OFF entry means)
def kind_of(e): return re.sub(r"[^A-Za-z]", "", type(e).__name__)[:40] or "error"      # an error by its kind - never by its words
def said(line): print(line, flush=True)
def refuse(why):
    """ONE plain line for a start that changes nothing, and the exit code 2."""
    said(HEAD + "NOT DONE, nothing was changed - " + why + TAIL); return 2
def approved(text):
    """The owner's word in its one shape -> the date of his word as YYYY-MM-DD; None for every other text (another name, another place, more words, a date
    that is no calendar date, a date after today)."""
    m = APPROVAL.fullmatch(text) if isinstance(text, str) else None
    if not m: return None
    try: d = datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError: return None
    return d.isoformat() if d <= datetime.date.today() else None
def look(path):
    """What a cache file holds -> ("table", its table) / ("no file", {}) for a file that is not there or is empty / ("unreadable", None) for a file that is
    there but cannot be read as a table (cut off, no JSON, a list): such a file may hold dates of death and is never written over."""
    try:
        with open(path) as fh: txt = fh.read()
    except FileNotFoundError: return "no file", {}
    except Exception: return "unreadable", None
    if not txt.strip(): return "no file", {}
    try: c = json.loads(txt)
    except Exception: return "unreadable", None
    return ("table", c) if isinstance(c, dict) else ("unreadable", None)
def write(path, obj):
    """A file written whole: a temporary file beside it, then put in its place in one step (none is left behind; a write that fails leaves the file as it was)."""
    d = os.path.dirname(os.path.abspath(path)); os.makedirs(d, exist_ok=True); fd, tmp = tempfile.mkstemp(prefix=".death_off_record.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as fh: json.dump(obj, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
def stands(G, entry, off):
    """What the chart's entry in ONE cache file holds, by the guard's own reading -> "day" / "no day" (a death his word of date `off` covers), "later day" /
    "later no day" (a death his word does NOT cover: a day after its date, a death with no day reported after it), "" (no death on record there)."""
    if not isinstance(entry, dict): return ""
    day = G._day(entry.get("dod"))
    if day: return "later day" if G._beats(off, day, None) else "day"
    if G._unread(entry.get("dod")): return "later no day" if G._beats(off, None, entry.get("checked")) else "no day"
    return ""
WAS = {"day": "a day was on record", "no day": "a death was on record with no day that can be read", "": "no death on record for this chart"}
LATER = {"later day": "the day on record lies AFTER the date of his word - NOT taken off (a later day is a new death: it takes his word of a later date)",
         "later no day": "a death with no day was put on record AFTER the date of his word - NOT taken off (it takes his word of a later date)"}

def main(argv=None):
    """The helper's run -> its exit code. An error of its own ends it with ONE plain line - the error's kind and the line of this file, never the error's
    words - and exit 2: it is never a traceback in a run's log."""
    try: return work(sys.argv[1:] if argv is None else argv)
    except Exception as e:
        here = main.__code__.co_filename; n = 0; tb = e.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == here: n = tb.tb_lineno
            tb = tb.tb_next
        said(HEAD + "NOT DONE - this helper ended on an error of its own (%s at line %d of death_off_record.py); the lines above say what was written before it stopped" % (kind_of(e), n) + TAIL); return 2
def work(argv):
    a = [str(x) for x in argv]; dry = False; chart = None; text = None; i = 0
    while i < len(a):
        x = a[i]; i += 1
        if x == "--dry": dry = True
        elif x == "--approved-by":
            if text is not None or i >= len(a): return refuse("--approved-by wants ONE approval behind it (%s)" % USAGE)
            text = a[i]; i += 1
        elif x.startswith("-") or chart is not None: return refuse("ONE chart number and ONE approval, and no option but --dry (%s)" % USAGE)
        else: chart = x
    m = re.fullmatch(r"(?:pat)?([0-9]{1,12})", chart or "")
    if not m: return refuse("the chart number is missing or is no number (%s)" % USAGE)
    num = m.group(1); off = approved(text)
    if off is None: return refuse("the approval is missing or not in shape: it must be William's word, its date (a real date, not after today) and where he said it (%s)" % USAGE)
    try: import deceased_guard as G
    except Exception as e: return refuse("deceased_guard.py could not be loaded beside this helper (%s)" % kind_of(e))
    if not all(hasattr(G, n) for n in NEEDS) or not isinstance(G.CACHE, str) or not G.CACHE:
        return refuse("the deceased_guard.py beside this helper is from before 11/25/2026 and does not know an entry taken off the record - make the two helpers the repository's first, then start this helper again")
    try: reg = look(REGISTER)
    except Exception: reg = ("unreadable", None)
    if reg[0] == "unreadable" or not isinstance((reg[1] or {}).get("rows", []), list):
        return refuse("this helper's own register %s is there but cannot be read: the row could not be kept, so no cache file was touched" % REGISTER)
    paths = [G.CACHE] + [p for p in (G._others() or []) if isinstance(p, str) and p]
    seen = [(p, ) + look(p) for p in paths]      # (path, "table" / "no file" / "unreadable", the table)
    what = [stands(G, (t or {}).get(num), off) for p, k, t in seen]
    hits = [j for j, w in enumerate(what) if w in ("day", "no day")]      # the files that hold a death his word covers
    unread = sum(1 for p, k, t in seen if k == "unreadable"); today = datetime.date.today().isoformat(); would = "would be " if dry else ""
    new = {"dod": None, "checked": today, "src": G.OFF_SRC, "off_record": off, "approved_by": text}
    done = failed = 0
    for j, (p, k, t) in enumerate(seen):
        tag = p + (" (the cache in use)" if j == 0 else ""); w = what[j]
        if k == "unreadable": said("%s: cannot be read - passed over, left exactly as it is" % tag); continue
        if w in LATER: said("%s: %s" % (tag, LATER[w])); continue
        if j == 0 and hits and j not in hits and k == "table" and (G._off(t.get(num)) or "") >= off:      # the cache in use holds his word already, of the same or a later date: an earlier word never takes its place
            said("%s: his word of the same or a later date stands here already - unchanged" % tag); continue
        if j not in hits and not (j == 0 and hits):
            said("%s: %s - unchanged" % (tag, WAS[""] if k == "table" else "no such file")); continue
        if dry:
            said("%s: %s - %staken off the record" % (tag, WAS[w] if w else "no death on record here, another file held one", would)); done += 1; continue
        try:
            k2, t2 = look(p)      # read again just before the write: what another helper wrote meanwhile stays
            if k2 == "unreadable": raise ValueError("the file cannot be read any more")
            old = t2.get(num) if isinstance(t2.get(num), dict) else {}; entry = dict(new)
            if "name" in old: entry["name"] = old["name"]
            t2[num] = entry; write(p, t2); done += 1
            said("%s: %s - taken off the record" % (tag, WAS[w] if w else "no death on record here, another file held one: the owner's word is written here too"))
        except Exception as e:
            failed += 1; said("%s: %s - could NOT be written (%s): unchanged" % (tag, WAS[w] if w else "no death on record here", kind_of(e)))
    notes = ("; %d file(s) could not be read and were passed over" % unread if unread else "") + ("; a death his word does not cover stays on record in %d file(s) - see the line(s) above" % sum(1 for w in what if w in LATER) if any(w in LATER for w in what) else "")
    if not hits:
        said(HEAD + ("DRY - " if dry else "") + "nothing is on record for pat%s that his word covers - nothing was changed (%d cache file(s) looked at)%s" % (num, len(seen), notes) + TAIL); return 3
    if dry:
        said(HEAD + "DRY - nothing was changed; a live start would take pat%s off the record in %d cache file(s) on the owner's word: %s%s" % (num, done, text, notes) + TAIL); return 0
    row = {"chart": "pat" + num, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "approved_by": text, "files": done}; kept = ""
    try:
        k3, cur = look(REGISTER)
        if k3 == "unreadable" or not isinstance((cur or {}).get("rows", []), list): raise ValueError("the register cannot be read any more")
        cur = dict(cur or {}); cur["helper"] = "death_off_record.py"; cur["rows"] = list(cur.get("rows") or []) + [row]; write(REGISTER, cur)
    except Exception as e: kept = "; the row could NOT be written to %s (%s)" % (REGISTER, kind_of(e))
    if failed or kept or not done:
        said(HEAD + "NOT everywhere - pat%s was taken off the record in %d cache file(s), %d could NOT be written%s%s: the guard may bring the death back from a file that still holds it - start this helper again" % (num, done, failed, kept, notes) + TAIL); return 2
    said(HEAD + "pat%s was taken off the record in %d cache file(s) on the owner's word: %s - his word covers every day reported on or before its date, a later day is a new death; pack the cache for Drive again at the end of the run (step 0c)%s - register %s" % (
        num, done, text, notes, REGISTER) + TAIL)
    return 0
if __name__ == "__main__": sys.exit(main())
