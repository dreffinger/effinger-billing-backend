#!/usr/bin/env python3
# PLAIN ENGLISH (taking a death OFF the deceased guard's record - the ONE way out of a death the guard holds WRONGLY; written 11/25/2026, in
#   the third round of the date-of-death check, and made simpler in the fourth, the same day)
# Why: the deceased guard keeps a death for good (deceased_guard.py: no answer without a day undoes one, the carry and the merge of the Drive
#   copy bring it back from every place that still holds it), and the run VOIDS a charge dated after it - never a question for William. So a
#   death on record that is WRONG - ONE Medicare answer that hit another person, a stale placeholder in a stray cache file, a mark on the
#   chart - blocked a living patient's claims for good, and nothing but a hand edit in up to five places took it out again; the next carry or
#   the next merge undid the hand edit (the second independent check of that day, finding 2).
# Decides: NOTHING. The owner decides - William - and this helper writes down that he did.
# ON WHOSE WORD: William's, and only his. The approval is given word for word with --approved-by and must read exactly
#   William <M>/<D>/<YYYY> (board)   or   William <M>/<D>/<YYYY> (chat)
#   - the date of his word, written with the digits 0 to 9, and where he said it: on the board or in chat. The date must be a real calendar
#   date and not later than tomorrow by this machine's clock (the machine is on UTC and his day is Eastern; nothing else is made of that
#   date). Anything else - another name, another place, more words, a date that is none, digits of another script - changes NOTHING and ends
#   2. No free text: the approval is kept in the cache entries and in this helper's register, and both reach a public repository. What was
#   typed is never printed back.
# WHAT HIS WORD DOES - one plain thing: it resets the record, and Medicare is asked afresh. The chart is cleared ONLY when Medicare's fresh
#   answer names no death; until Medicare has answered the chart is NOT cleared. So:
#     - Medicare names no death: the chart is clear again;
#     - Medicare names the day again: the chart stays blocked. Then the chart's Medicare number or its birth date - or Medicare's own record -
#       is what is wrong, and that is what has to be put right: a second word does not settle it. And a word given for the WRONG chart cannot
#       let a claim out: Medicare names that patient's day again;
#     - nobody answers: the chart waits - not approved, not entered, not rebilled on that run - and the next run asks again.
#   Nothing is compared with the date of his word, and EVERY death on record for the chart goes: there is no 'covered' and 'not covered'.
#   (The third round had a rule for that - his word 'beat' every day reported up to its date. It is gone: a word for the wrong chart had no
#   way back, the chart was no longer asked about, and nobody could explain the boundary.)
#   HIS WORD RESETS THE GUARD'S RECORD - AND NOTHING ELSE. Two other holds of the feed do not go by it: the feed's import holds a chart whose
#   AdvancedMD record carries any 'deceased' value ('deceased flag on chart - William'), and the insurance check after the import holds when
#   a plan's eligibility answer names a date of death. For those the chart's own record and its plans have to be right in AdvancedMD - a
#   date or a mark on the chart's 'deceased' field has to come off there too: the guard reads a date there as the day, and a mark as a death
#   with no day.
# WHAT IT DOES: it reads the guard's cache in use (deceased_guard.CACHE) and every other cache file the guard knows (deceased_guard._others():
#   the feed helpers' file of before, a register beside the helpers, the copies at the old paths) - each file itself, never through the guard's
#   own read (that one carries entries from file to file). Where the chart's entry holds a death on record - a day, or a death with no day
#   that can be read (the guard's one reading: _day, _unread), whatever its day and whenever it was put there - the entry becomes the RE-ASK
#   entry:
#     dod null; checked = a day long ago (the entry is stale on every machine); src = "off the record on the owner's word - Medicare is asked
#     again"; reask = the UTC date this helper ran, YYYY-MM-DD; approved_by = the approval text   (a name the entry had is kept; nothing else of
#     the file changes).
#   The cache in use gets the RE-ASK entry whenever ANY file held a death for the chart - also when its own entry said 'no death on record'
#   or it had none: the guard answers from that file, and that is where it reads that the chart is to be asked about afresh. It is written
#   FIRST: when it cannot be read or cannot be written, NOTHING is changed anywhere (a death taken out of another file alone would leave a
#   chart nobody asks about). Another cache file that cannot be read is passed over and said (the guard cannot read it either); each file is
#   read again just before it is written and replaced in one step.
# WHAT THE RE-ASK ENTRY MEANS afterwards is the guard's business (deceased_guard.py): the chart is asked about at its next claim, whatever the
#   payer and the code, with a FRESH question - AdvancedMD's free check first, then the vendor on the wire; no answer kept from before
#   answers - and the entry stays as it is until somebody answers. While it stands, the older record does not come back from another cache
#   file or from the Drive copy (a death checked on or before the day of the reset is not brought in). The Drive copy carries chart ids and
#   dates only: pack the cache again at the end of the run (step 0c); a workspace that still holds the death in a cache of its own needs his
#   word there.
# WHAT IT DOES NOT REACH: the answer store (medicare_store.py - patient_db/medicare_answers.json). It keeps the Medicare answer a wrong day
#   came from for up to 92 days, and this helper does not touch it. After Medicare's fresh 'no death' cleared the chart, that kept answer can
#   name the day again with nobody asked anew - when a later look-up for the chart fails, or at a later claim of that answer's month of
#   service when the fresh question was about an earlier month. The chart is then blocked by the old day again and needs his word again.
# WHAT IT WRITES: the cache files above, and ONE row appended to registers/death_off_record.json under the folder it is started in - the chart
#   id, a UTC stamp, the approval text, the number of cache files changed - and nothing else. A row that could not be written is not lost for
#   good: a start that finds the RE-ASK entry in the cache in use and NO row for that chart with that approval writes the row and ends 0.
#   --dry writes nothing at all.
# WHAT IT PRINTS: one line for each cache file - the path, what stood there in words (never the day itself), what was done - and a LAST line
#   that starts 'DEATH OFF THE RECORD:' and ends ' - TOP OF THE REPORT': the run puts it at the top of its report, word for word. It says
#   that Medicare is asked again at the chart's next claim and that its answer decides.
# EXIT: 0 = no cache file the guard knows (and can read) holds a death for the chart any more - the record is reset (with --dry: there is
#   something to reset). 3 = nothing was on record for that chart - nothing was changed, no row was written. 2 = the usage or the approval
#   is not in shape, the guard beside it is missing or an earlier version, its own register or the cache in use cannot be read, the row could
#   not be written, or an error of its own - one plain line, never a traceback; or a file that holds the death could not be changed: the
#   last line then starts 'DEATH NOT OFF THE RECORD EVERYWHERE:' (and still ends ' - TOP OF THE REPORT'). After a 2 read the lines above it:
#   they say what was written before it stopped.
# Usage (from the workspace, beside deceased_guard.py):
#   python3 death_off_record.py <chart number> --approved-by "William MM/DD/YYYY (board)"     ("(chat)" when he said it in chat; --dry shows what it would do)
# Never: decides anything; takes a word that is not William's in the shape above; talks to AdvancedMD or the vendor; asks Medicare (the guard
#   does, at the chart's next claim); prints or writes a day somebody passed away on, a name or a number; touches a charge, a visit or a
#   claim; changes an entry of another chart; writes over a file it cannot read. A charge the run already voided for that death is not put
#   back by this helper - that is William's to say.
import os, re, sys, json, datetime, tempfile
DEATH_OFF_RECORD_VERSION = "2026-11-25.2"      # this helper's own version: change it with EVERY revision
APPROVAL = re.compile(r"William ([0-9]{1,2})/([0-9]{1,2})/([0-9]{4}) \((board|chat)\)")      # the owner's word, exactly: who, the date, where - and nothing else; the digits 0 to 9 only (a \d takes the digits of every script)
USAGE = 'usage: python3 death_off_record.py <chart number> --approved-by "William MM/DD/YYYY (board)" [--dry] - exactly that text with the date of his word (not later than tomorrow), "(board)" or "(chat)"'
REGISTER = os.path.join("registers", "death_off_record.json")
HEAD = "DEATH OFF THE RECORD: "; NOT_HEAD = "DEATH NOT OFF THE RECORD EVERYWHERE: "; TAIL = " - TOP OF THE REPORT"
NEEDS = ("CACHE", "_others", "_day", "_unread", "_reask", "NotAnswered", "REASK_SRC", "LONG_AGO")      # what the guard beside this helper must have: this round's guard - it knows the RE-ASK entry (an earlier guard would read it as 'no death on record' and clear the chart before Medicare has answered)
WHAT_NEXT = "Medicare is asked again at the chart's next claim and its answer decides: no death = the chart is clear again, the day named again = it stays blocked; until Medicare has answered the chart is not cleared"
def kind_of(e): return re.sub(r"[^A-Za-z]", "", type(e).__name__)[:40] or "error"      # an error by its kind - never by its words
def said(line): print(line, flush=True)
def refuse(why):
    """ONE plain line for a start that changes nothing, and the exit code 2."""
    said(HEAD + "NOT DONE, nothing was changed - " + why + TAIL); return 2
def approved(text):
    """True for the owner's word in its one shape, with a real calendar date not later than tomorrow by this machine's clock; False for every other text
    (another name, another place, more words, a date that is no calendar date, a later date, digits of another script). Nothing else is made of that date."""
    m = APPROVAL.fullmatch(text) if isinstance(text, str) else None
    if not m: return False
    try: d = datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError: return False
    return d <= datetime.date.today() + datetime.timedelta(days=1)
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
def stands(G, entry):
    """What the chart's entry in ONE cache file holds, by the guard's own reading -> "day" / "no day" (a death on record: a day, or a death with no day that
    can be read) / "" (no death on record there)."""
    if not isinstance(entry, dict): return ""
    return "day" if G._day(entry.get("dod")) else "no day" if G._unread(entry.get("dod")) else ""
WAS = {"day": "a day was on record", "no day": "a death was on record with no day that can be read", "": "no death on record for this chart"}

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
    num = m.group(1)
    if not approved(text): return refuse("the approval is missing or not in shape: it must be William's word, its date (a real date in the digits 0 to 9, not later than tomorrow) and where he said it (%s)" % USAGE)
    try: import deceased_guard as G
    except Exception as e: return refuse("deceased_guard.py could not be loaded beside this helper (%s)" % kind_of(e))
    if not all(hasattr(G, n) for n in NEEDS) or not isinstance(G.CACHE, str) or not G.CACHE:
        return refuse("the deceased_guard.py beside this helper is an earlier version: it does not know a record that was reset and would clear the chart before Medicare has answered - make the two helpers the repository's first, then start this helper again")
    try: reg = look(REGISTER)
    except Exception: reg = ("unreadable", None)
    if reg[0] == "unreadable" or not isinstance((reg[1] or {}).get("rows", []), list):
        return refuse("this helper's own register %s is there but cannot be read: the row could not be kept, so no cache file was touched" % REGISTER)
    paths = [G.CACHE] + [p for p in (G._others() or []) if isinstance(p, str) and p]
    seen = [(p, ) + look(p) for p in paths]      # (path, "table" / "no file" / "unreadable", the table) - the cache in use first
    if seen[0][1] == "unreadable":
        return refuse("the guard's cache in use (%s) is there but cannot be read: the reset has to stand in the file the guard answers from, and it cannot be written there - merge the copy from Drive first (step 0c keeps the unreadable file under another name and puts a table in its place), then start this helper again" % seen[0][0])
    what = [stands(G, (t or {}).get(num)) for p, k, t in seen]
    hits = [j for j, w in enumerate(what) if w]      # the files that hold a death on record for the chart - every one of them is reset
    unread = sum(1 for p, k, t in seen if k == "unreadable")
    notes = "; %d other cache file(s) could not be read and were passed over (the guard cannot read them either)" % unread if unread else ""
    rows_now = [r for r in ((reg[1] or {}).get("rows") or []) if isinstance(r, dict)]
    if not hits:
        for j, (p, k, t) in enumerate(seen):
            said("%s%s: %s" % (p, " (the cache in use)" if j == 0 else "", "cannot be read - passed over, left exactly as it is" if k == "unreadable" else (WAS[""] if k == "table" else "no such file") + " - unchanged"))
        waits = seen[0][1] == "table" and G._reask(seen[0][2].get(num)) is not None      # the record of this chart was reset before: its RE-ASK entry stands in the cache in use
        if waits and not any(r.get("chart") == "pat" + num and r.get("approved_by") == text for r in rows_now):
            # A ROW THAT COULD NOT BE WRITTEN IS NOT LOST FOR GOOD: the reset stands in the cache in use and the register holds no row for this chart with this approval - it is written now
            if dry:
                said(HEAD + "DRY - nothing was changed; the record of pat%s was reset before and the register holds no row for it with this approval: a live start would write that row%s" % (num, notes) + TAIL); return 0
            why = keep_row(num, text, 0)
            if why: said(HEAD + "pat%s - the record was reset before, but the row could NOT be written to %s (%s): start this helper again with the same approval - it writes the row%s" % (num, REGISTER, why, notes) + TAIL); return 2
            said(HEAD + "pat%s - the record of a death was reset before on the owner's word; the register held no row for this approval, and it is written now: %s - %s%s - register %s" % (num, text, WHAT_NEXT, notes, REGISTER) + TAIL); return 0
        said(HEAD + ("DRY - " if dry else "") + "nothing is on record for pat%s - nothing was changed (%d cache file(s) looked at)%s%s" % (
            num, len(seen), "; its record was reset before on the owner's word: " + WHAT_NEXT if waits else "", notes) + TAIL); return 3
    new = {"dod": None, "checked": G.LONG_AGO, "src": G.REASK_SRC, "reask": datetime.datetime.now(datetime.timezone.utc).date().isoformat(), "approved_by": text}
    done = failed = 0; stopped = False
    for j, (p, k, t) in enumerate(seen):      # the cache in use FIRST: when it cannot be written, nothing else is changed
        tag = p + (" (the cache in use)" if j == 0 else ""); w = what[j]
        if k == "unreadable": said("%s: cannot be read - passed over, left exactly as it is" % tag); continue
        if not w and j != 0:
            said("%s: %s - unchanged" % (tag, WAS[""] if k == "table" else "no such file")); continue
        was = WAS[w] if w else "no death on record here, another file held one"; does = "reset: Medicare is asked again" if w else "the reset is written here too: Medicare is asked again"
        if stopped:
            failed += 1; said("%s: %s - NOT changed: the cache in use could not be written" % (tag, was)); continue
        if dry:
            said("%s: %s - would be %s" % (tag, was, does)); done += 1; continue
        try:
            k2, t2 = look(p)      # read again just before the write: what another helper wrote meanwhile stays
            if k2 == "unreadable": raise ValueError("the file cannot be read any more")
            old = t2.get(num) if isinstance(t2.get(num), dict) else {}; entry = dict(new)
            if "name" in old: entry["name"] = old["name"]
            t2[num] = entry; write(p, t2); done += 1
            said("%s: %s - %s" % (tag, was, does))
        except Exception as e:
            failed += 1; stopped = stopped or j == 0; said("%s: %s - could NOT be written (%s): unchanged" % (tag, was, kind_of(e)))
    if dry:
        said(HEAD + "DRY - nothing was changed; a live start would reset the record of pat%s in %d cache file(s) on the owner's word: %s - %s%s" % (num, done, text, WHAT_NEXT, notes) + TAIL); return 0
    if stopped:
        said(NOT_HEAD + "pat%s - the guard's cache in use could not be written, so NOTHING was changed: the death stays on record in %d cache file(s) and the chart stays as it was - start this helper again%s" % (num, len(hits), notes) + TAIL); return 2
    why = keep_row(num, text, done)
    if failed:
        said(NOT_HEAD + "pat%s - the record was reset in %d cache file(s), but %d file(s) that hold the death could NOT be changed (the lines above say which)%s: the cache in use carries the reset, so %s - start this helper again to change the file(s) left%s" % (
            num, done, failed, "; the row could NOT be written to %s (%s)" % (REGISTER, why) if why else "", WHAT_NEXT, notes) + TAIL); return 2
    if why:
        said(HEAD + "pat%s - the record of a death was reset in %d cache file(s) on the owner's word, but the row could NOT be written to %s (%s): start this helper again with the same approval - it finds the reset and writes the row; %s%s" % (
            num, done, REGISTER, why, WHAT_NEXT, notes) + TAIL); return 2
    said(HEAD + "pat%s - the record of a death was reset in %d cache file(s) on the owner's word: %s - %s; pack the cache for Drive again at the end of the run (step 0c)%s - register %s" % (num, done, text, WHAT_NEXT, notes, REGISTER) + TAIL)
    return 0
def keep_row(num, text, files):
    """ONE row appended to this helper's register - the chart, a UTC stamp, the approval text, the number of cache files changed -> "" when it is written, else
    the kind of what went wrong (the register is read again just before the write and replaced in one step)."""
    row = {"chart": "pat" + num, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "approved_by": text, "files": files}
    try:
        k, cur = look(REGISTER)
        if k == "unreadable" or not isinstance((cur or {}).get("rows", []), list): raise ValueError("the register cannot be read any more")
        cur = dict(cur or {}); cur["helper"] = "death_off_record.py"; cur["rows"] = list(cur.get("rows") or []) + [row]; write(REGISTER, cur)
    except Exception as e: return kind_of(e)
    return ""
if __name__ == "__main__": sys.exit(main())
