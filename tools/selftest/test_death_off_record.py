#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of death_off_record.py - the ONE way a death comes off the deceased guard's record: on the owner's word.
#   Written in the third round (11/25/2026) of the date-of-death check, rewritten in the fourth: the third round's rule - his word 'beat' every
#   day reported up to its date - is gone. His word RESETS THE RECORD AND MEDICARE IS ASKED AFRESH; the chart is cleared only when Medicare's
#   fresh answer names no death, and until Medicare has answered it is not cleared.)
# Decides: nothing. It runs the helper (scripts/helpers/death_off_record.py) INSIDE this process, as the program a run starts, in throwaway
#   workspaces - and once as a real program in a workspace that holds nothing but the helper and the guard. The guard beside it is the REAL
#   scripts/helpers/deceased_guard.py, loaded as if it stood in that workspace (so its cache is the workspace's register and its other cache
#   files are the workspace's); the Drive tool (dg_drive.py) and the import's reading of the cache files (claimocity_import.death_read) are the
#   real ones too. No network, no AdvancedMD, no vendor: nothing here loads a module that could reach either, and the network is shut.
#   Every chart number and every day is invented and put together at run time. It proves:
#     - the word: the approval must be exactly 'William <M>/<D>/<YYYY> (board)' or '(chat)', written with the digits 0-9, a real calendar date
#       not later than tomorrow by the machine's clock - anything else changes nothing and ends 2, and what was typed is never printed back;
#     - the work: in the guard's cache in use and in every other cache file the guard knows, the chart's entry that holds a death - a day, or
#       a death on record with no day, whatever its date - becomes the RE-ASK entry (no death, a check date long ago, the fixed source, the
#       day the helper ran, the approval text; the entry's name stays); the cache in use gets it whenever any file held a death; nothing else
#       in any file changes; EVERY death on record for the chart goes - there is no 'covered' and 'not covered';
#     - what it says and keeps: one line per file, a last line that starts 'DEATH OFF THE RECORD:' and ends ' - TOP OF THE REPORT', never
#       the day itself; ONE row in registers/death_off_record.json - the chart, a UTC stamp, the approval text, the number of files changed;
#       a row that could not be written is written by the next start with the same approval;
#     - the exit codes: 0 = no cache file the guard knows holds a death for the chart any more, 3 = nothing was on record (nothing changed,
#       no row), 2 = usage / approval / an error of its own / a file that holds the death could not be changed - one plain line, never a
#       traceback; --dry changes nothing;
#     - what the RE-ASK entry MEANS afterwards: the chart is NOT cleared before Medicare has answered; the same day named again is taken
#       again (a word given for the wrong chart cannot let a claim out), 'no death' clears the chart; the Drive copy carries chart ids and
#       dates only; an older copy or another cache file does not bring the old record back before Medicare was asked.
# Run: python3 tools/selftest/test_death_off_record.py   (exit 1 on any failure; the last line says how many checks ran and how many failed)
import os, sys, io, re, json, glob, types, shutil, atexit, datetime, tempfile, contextlib, subprocess
import importlib.abc, importlib.machinery
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = "scripts/helpers/death_off_record.py"; GUARD = "scripts/helpers/deceased_guard.py"; DRIVE = "scripts/helpers/dg_drive.py"; IMPORT = "scripts/helpers/claimocity_import.py"
LIVE = {"amd", "resave", "txh", "void_tx", "era_post", "deceased_guard", "stedi", "requests", "medicare_store", "stedi_prices", "stedi_usage", "precheck", "elig_amd", "dg_drive", "death_off_record"}
class _Refuse(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in LIVE: raise ImportError("refused: %s is a live-system module - only what this test loads from its file is used here" % name)
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is not None and spec.origin and os.path.abspath(spec.origin).startswith(ROOT + os.sep):
            raise ImportError("refused: %s would be loaded from the checkout (%s)" % (name, spec.origin))
        return None
sys.meta_path.insert(0, _Refuse())
FAILS = []; COUNT = [0]
def check(name, cond, extra=""):
    """One check. cond may be a function: it is called here, and an error inside it is a failure (never a crash of the whole test)."""
    COUNT[0] += 1
    if callable(cond):
        try: cond = cond()
        except Exception as e: cond, extra = False, "raised %s: %s" % (type(e).__name__, e)
    if callable(extra):
        try: extra = extra()
        except Exception as e: extra = "(the detail raised %s)" % type(e).__name__
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:700]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
def _try(f, instead="raised"):
    try: return f()
    except Exception: return instead
def _raises(f, exc=Exception):
    try: f()
    except exc: return True
    except Exception: return False
    return False
def _read(rel):
    with open(os.path.join(ROOT, rel)) as fh: return fh.read()
def _exists(rel): return os.path.isfile(os.path.join(ROOT, rel))
TMP = tempfile.mkdtemp(prefix="deathoff_selftest_"); atexit.register(shutil.rmtree, TMP, True)
os.environ.pop("DECEASED_CACHE", None)      # the guard of each workspace finds its own cache - no shell names one for it
def _snapshot():
    out = {}
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in files:
            p = os.path.join(d, f)
            try: st = os.stat(p); out[p] = (st.st_size, st.st_mtime_ns)
            except OSError: pass
    return out
BEFORE = _snapshot(); _PATH = list(sys.path)

# ---- invented values: every chart number and every day is put together here, at run time -------------------------------------------------------
TODAY = datetime.date.today()
def utc_day(): return datetime.datetime.now(datetime.timezone.utc).date()      # the day the helper stamps a reset with
def ago(n): return TODAY - datetime.timedelta(days=n)
def iso(d): return d.isoformat()
def ymd(d): return d.strftime("%Y%m%d")
def mdy(d): return d.strftime("%m/%d/%Y")
def faces(d): return [iso(d), ymd(d), mdy(d), "%d/%d/%d" % (d.month, d.day, d.year)]
def word(d=None, where="board", padded=False):
    """The approval text as the owner's word is written down: William, the date of his word, where he said it."""
    d = d or TODAY; return "William %s (%s)" % (mdy(d) if padded else "%d/%d/%d" % (d.month, d.day, d.year), where)
GONE = ago(40); GONE2 = ago(33)      # the invented days a wrong answer named
LOSTD = "[" + "DOB" + "]"            # what the privacy gate leaves in a day's place in the repository's copy of the cache
LONG_AGO = "2000-01-" + "01"         # the check date of an entry that must be asked about again (the guard's own LONG_AGO)
REASK_SRC = "off the record on the owner's word - Medicare is asked again"
SECRETS = faces(GONE) + faces(GONE2)      # no printed line and no register may show a day somebody passed away on
def leaks(text): return [s for s in SECRETS if s in str(text)]
def reask_entry(text=None, **more):
    """The RE-ASK entry the helper writes: no death, a check date long ago, the fixed source, the UTC day the helper ran, the approval text"""
    e = {"dod": None, "checked": LONG_AGO, "src": REASK_SRC, "reask": iso(utc_day()), "approved_by": text or word()}; e.update(more); return e

# ---- throwaway workspaces, the real guard as it stands in one, and the helper as the program a run starts ---------------------------------------
WS_N = [0]; SEEN = []      # SEEN: everything the helper printed and every file it wrote, for the privacy checks at the end
def ws(register=None, local=None, old=None):
    """A run's flat workspace: <n>/home/ws, registers/ beside the helpers. register = the cache in use (a table; a text is written as it is; None = no
    file), local = the feed helpers' cache file of before (deceased_cache_local.json beside the helpers), old = a hand copy at the old path
    (<n>/home/practices/ehpa/registers/deceased_cache.json). -> the workspace folder."""
    WS_N[0] += 1; w = os.path.join(TMP, "w%d" % WS_N[0], "home", "ws"); os.makedirs(os.path.join(w, "registers"))
    for path, what in ((reg_of(w), register), (local_of(w), local), (old_of(w), old)):
        if what is None: continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh: fh.write(what if isinstance(what, str) else json.dumps(what, indent=1, sort_keys=True))
    return w
def reg_of(w): return os.path.join(w, "registers", "deceased_cache.json")
def local_of(w): return os.path.join(w, "deceased_cache_local.json")
def old_of(w): return os.path.join(os.path.dirname(w), "practices", "ehpa", "registers", "deceased_cache.json")
def row_file(w): return os.path.join(w, "registers", "death_off_record.json")
def table(path):
    try:
        with open(path) as fh: return json.load(fh)
    except FileNotFoundError: return "no file"
    except Exception: return "unreadable"
def text_of(path):
    try:
        with open(path) as fh: return fh.read()
    except OSError: return None
def guard_at(w, text=None):
    """The REAL guard as it stands in that workspace: its text is the checkout's, run under the name <workspace>/deceased_guard.py with no cache named by
    the environment. A new module each time, like a new process."""
    g = types.ModuleType("deceased_guard"); g.__file__ = os.path.join(w, "deceased_guard.py"); g.UNDER_TEST = True
    try: exec(compile(_read(GUARD) if text is None else text, g.__file__, "exec"), g.__dict__)
    finally: sys.path[:] = _PATH
    return g
def run(w, argv, guard="real", cwd=None):
    """One start of the helper in workspace w -> its exit code, its lines, its error output. guard: "real" = the real guard as it stands in w (a new
    module, like a new process); None = no deceased_guard beside the helper; a module = that one. Never raises: a helper that ends on an error of its own
    shows it in .err, and the checks fail on it."""
    out = io.StringIO(); err = io.StringIO(); code = "no exit"; crash = ""; path = os.path.join(ROOT, HELPER)
    try: src = _read(HELPER)
    except OSError: src = None; crash = "the helper is not there (%s)" % HELPER
    if src is not None:
        g = guard_at(w) if guard == "real" else guard; keep = sys.modules.get("deceased_guard"); old = (os.getcwd(), list(sys.argv))
        sys.modules.pop("deceased_guard", None)
        if g is not None: sys.modules["deceased_guard"] = g
        try:
            os.chdir(cwd or w); sys.argv = [path] + [str(x) for x in argv]
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
                except SystemExit as e: code = e.code
                except BaseException as e: crash = "ended with %s - a run would see a traceback" % type(e).__name__
        finally:
            os.chdir(old[0]); sys.argv = old[1]; sys.path[:] = _PATH; sys.modules.pop("deceased_guard", None)
            if keep is not None: sys.modules["deceased_guard"] = keep
    text = out.getvalue(); SEEN.append(text); SEEN.append(text_of(row_file(cwd or w)) or "")
    return types.SimpleNamespace(code=code, out=text, lines=[l for l in text.splitlines() if l.strip()], err=err.getvalue() + crash, w=w)
def last(r): return r.lines[-1] if r.lines else ""
HEAD = "DEATH OFF THE RECORD:"; NOT_HEAD = "DEATH NOT OFF THE RECORD EVERYWHERE:"; TAIL = " - TOP OF THE REPORT"
def framed(r, head=HEAD): return last(r).startswith(head) and last(r).endswith(TAIL)
def rows(w):
    t = table(row_file(w)); return t.get("rows") if isinstance(t, dict) else t
CLAIM = ("car6404", "99349")      # a claim to another payer with an ordinary code: the guard answers it from its cache alone
def asks(w, chart, dos, g=None):
    """what the guard of that workspace (a new module: a new process) answers for a claim of that chart and date, from its cache only -> 'blocked' / 'clear' /
    'reset' (NotAnswered: the record was reset and Medicare has not answered) / 'lost' (DayLost itself) / the error's kind"""
    g = g or guard_at(w)
    try: return "blocked" if g.check(chart, iso(dos), CLAIM[0], CLAIM[1], allow_lookup=False)[0] else "clear"
    except Exception as e: return {"NotAnswered": "reset", "DayLost": "lost"}.get(type(e).__name__, type(e).__name__)
def holds_death(w, chart):
    """the cache files the guard of that workspace knows that still hold a death for the chart - by the guard's own reading (a day, or a death with no day)"""
    g = guard_at(w); out = []
    for p in [g.CACHE] + list(g._others()):
        e = table(p); e = e.get(chart) if isinstance(e, dict) else None
        if isinstance(e, dict) and (g._day(e.get("dod")) or g._unread(e.get("dod"))): out.append(p)
    return out

# ---- 0. the safety block holds, and the helper is where the workspace builders copy helpers from -----------------------------------------------
check("0a safety: the real `requests`, a live helper and any module of the checkout are refused by the import blocker; the network is shut",
      lambda: _raises(lambda: _Refuse().find_spec("requests"), ImportError) and _raises(lambda: _Refuse().find_spec("amd"), ImportError) and _raises(lambda: _socket.create_connection(("127.0.0.1", 9)), RuntimeError))
check("0b the helper is in the repository, in the folder the workspace builders copy helpers from (scripts/helpers)", lambda: _exists(HELPER), HELPER)

# ---- 1. the word: who, when, where - and nothing else ----------------------------------------------------------------------------------------------
ONE = {"7401": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept as it was"}, "7402": {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}}
Y = TODAY.year; SOON = TODAY + datetime.timedelta(days=1); LATER = TODAY + datetime.timedelta(days=2)
def other_digits(text, zero):
    """the same text with every digit written in another script (zero = that script's digit 0): full-width, Arabic-Indic ..."""
    return "".join(chr(zero + int(c)) if c in "0123456789" else c for c in text)
BAD_WORDS = ["William", "William (board)", word().replace("William", "william"), word().replace("William", "Bill"), word().replace(" (board)", ""), word(where="email"), word(where="Board"), word() + " and more", " " + word(), word() + " ",
             "Dr. " + word(), word().replace("William ", "William  "), "William %s (board)" % iso(TODAY), "William %d/%d/%02d (board)" % (TODAY.month, TODAY.day, Y % 100), "William 13/45/%d (board)" % Y, "William 2/30/%d (board)" % Y,
             "William 0/10/%d (board)" % Y, word(LATER), word(TODAY + datetime.timedelta(days=400)), "the chart is alive - William said so", "", word().replace("(board)", "[board]"), word() + "\n" + word(),
             other_digits(word(), 0xFF10), other_digits(word(), 0x0660), other_digits(word(ago(3)), 0x06F0), word().replace(str(Y), other_digits(str(Y), 0x0966))]      # (the last four: the date, or its year alone, in the digits of another script)
w1 = ws(register=ONE); t1 = text_of(reg_of(w1)); res1 = []
for b in BAD_WORDS:
    r = run(w1, ["7401", "--approved-by", b]); res1.append((b, r.code, len(r.lines), framed(r), r.err, text_of(reg_of(w1)) == t1, os.path.exists(row_file(w1)), (b.strip() != "" and len(b) > 9 and b.strip() in r.out)))
check("1a the approval must be EXACTLY 'William <M>/<D>/<YYYY> (board)' or '(chat)' with a real calendar date not later than tomorrow: every other text - no date, another name, another place, more words, a date that is none, a date after tomorrow, a date in another shape - changes NOTHING and ends 2 with one plain line",
      lambda: len(res1) == len(BAD_WORDS) >= 24 and all(x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5] and not x[6] for x in res1), lambda: [x for x in res1 if not (x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5] and not x[6])][:4])
check("1b ... and what was typed is never printed back (no free text reaches a log or a report: this helper's register goes to a public repository)", lambda: not any(x[7] for x in res1), lambda: [x[0] for x in res1 if x[7]])
check("1b2 (finding 7 of the third check) ... its date must be written with the digits 0 to 9: the same words with the date in full-width, Arabic-Indic or Devanagari digits are not his word in shape (the third round took them, and kept them as typed in the cache and the register)",
      lambda: all(x[1] == 2 and x[5] and not x[6] for x in res1[-4:]) and all(re.search(r"[^\x00-\x7f]", x[0]) for x in res1[-4:]), lambda: [(x[0], x[1]) for x in res1[-4:]])
ARGS = [[], ["7401"], ["--approved-by", word()], ["7401", "--approved-by"], ["7401", "7402", "--approved-by", word()], ["74x1", "--approved-by", word()], ["pat", "--approved-by", word()], ["", "--approved-by", word()],
        ["7401", "--approved-by", word(), "--live"], ["7401", "--approved-by", word(), "--approved-by", word()], ["7401", "--by", word()], ["7401 7402", "--approved-by", word()], ["-7401", "--approved-by", word()],
        [other_digits("7401", 0xFF10), "--approved-by", word()], ["7401", "--approved-by", word(), "--back"]]
res2 = [(a, r.code, len(r.lines), framed(r), r.err, text_of(reg_of(w1)) == t1) for a in ARGS for r in [run(w1, a)]]
check("1c the usage: ONE chart number (the digits 0 to 9, with or without 'pat' before them) and ONE approval - no chart, two charts, a chart that is no number, no approval, two approvals, an option it does not know: nothing is changed, exit 2, one plain line",
      lambda: all(x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5] for x in res2), lambda: [x for x in res2 if not (x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5])][:4])
GOOD = [word(), word(padded=True), word(where="chat"), word(ago(1)), word(ago(35), "chat"), word(ago(35), "board", padded=True), word(SOON), word(ago(400))]
res3 = []
for g_ in GOOD:
    w = ws(register=ONE); r = run(w, ["7401", "--approved-by", g_]); res3.append((g_, r.code, r.err, (table(reg_of(w)) or {}).get("7401")))
check("1d the word in its shape is taken: today's date, an earlier one or tomorrow's (the machine's clock is UTC, his day is Eastern - and a machine behind him is a day back), with or without a leading zero, said on the board or in chat - exit 0, and the entry carries that very text",
      lambda: all(x[1] == 0 and x[2] == "" and isinstance(x[3], dict) and x[3].get("approved_by") == x[0] for x in res3), lambda: res3)
check("1e ... and NOTHING is made of the date of his word: whatever date the approval carries, the entry is the same RE-ASK entry - stamped with the day the helper RAN (UTC), never with the date he said it on (the third round compared every death with that date - the boundary nobody could explain)",
      lambda: all(x[3] == reask_entry(x[0], name="kept as it was") for x in res3) and len({json.dumps({k: v for k, v in x[3].items() if k != "approved_by"}, sort_keys=True) for x in res3}) == 1, lambda: res3)

# ---- 2. the work: every cache file the guard knows -------------------------------------------------------------------------------------------------
REG = {"7411": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept as it was"}, "7412": {"dod": iso(GONE2), "checked": iso(ago(9)), "src": "x"}, "7413": {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}}
LOC = {"7411": {"dod": LOSTD, "checked": iso(ago(60)), "src": "stedi-medicare-271"}, "7414": {"dod": LOSTD, "checked": iso(ago(60))}}
OLD = {"7411": {"dod": "day not known", "checked": iso(ago(3)), "src": "amd: deceased on the chart, no date"}, "7415": {"dod": ymd(GONE2), "checked": iso(ago(9))}, "a line": "that is no entry"}
w2 = ws(register=REG, local=LOC, old=OLD); before2 = asks(w2, "7411", ago(5)); g2 = guard_at(w2); files2 = [g2.CACHE] + list(g2._others())
w2 = ws(register=REG, local=LOC, old=OLD)      # (asking the guard above carried the other files' entries into the register: the helper gets a workspace nobody has touched)
r2 = run(w2, ["7411", "--approved-by", word()]); T2 = {"reg": table(reg_of(w2)), "loc": table(local_of(w2)), "old": table(old_of(w2))}
check("2a the chart's entry becomes the RE-ASK entry in the guard's cache in use AND in every other cache file the guard knows - a day, the placeholder, 'day not known' alike: no death, a check date long ago, the fixed source, the day the helper ran, the approval text - and the name the entry had stays",
      lambda: r2.code == 0 and r2.err == "" and len(files2) == 3 and T2["reg"]["7411"] == reask_entry(name="kept as it was") and T2["loc"]["7411"] == reask_entry() and T2["old"]["7411"] == reask_entry()
      and sorted(T2["loc"]["7411"]) == ["approved_by", "checked", "dod", "reask", "src"],
      lambda: (r2.code, r2.err, r2.lines, files2, {k: (v.get("7411") if isinstance(v, dict) else v) for k, v in T2.items()}))
check("2b ... and NOTHING else in any of those files changes: every other chart's entry, and a line that is no entry, are as they were",
      lambda: {k: v for k, v in T2["reg"].items() if k != "7411"} == {k: v for k, v in REG.items() if k != "7411"} and {k: v for k, v in T2["loc"].items() if k != "7411"} == {k: v for k, v in LOC.items() if k != "7411"}
      and {k: v for k, v in T2["old"].items() if k != "7411"} == {k: v for k, v in OLD.items() if k != "7411"}, lambda: T2)
check("2c what it prints: ONE line for each cache file (the path, what stood there in words, what was done) and a LAST line that starts 'DEATH OFF THE RECORD:' and ends ' - TOP OF THE REPORT', names the chart, the number of files and the approval, and says what his word does - Medicare is asked again at the chart's next claim and its answer decides; until then the chart is not cleared - never the day itself",
      lambda: len(r2.lines) == 4 and framed(r2) and all(any(p in l for l in r2.lines[:3]) for p in (reg_of(w2), local_of(w2), old_of(w2))) and "pat7411" in last(r2) and "3 cache file(s)" in last(r2) and word() in last(r2)
      and "Medicare is asked again at the chart's next claim" in last(r2) and "its answer decides" in last(r2) and "not cleared" in last(r2) and leaks(r2.out) == [] and LOSTD not in r2.out, lambda: r2.lines)
R2ROW = rows(w2)
check("2d what it keeps: ONE row in registers/death_off_record.json - the chart, a UTC stamp, the approval text, the number of files changed - and nothing else",
      lambda: isinstance(R2ROW, list) and len(R2ROW) == 1 and sorted(R2ROW[0]) == ["approved_by", "at", "chart", "files"] and R2ROW[0]["chart"] == "pat7411" and R2ROW[0]["approved_by"] == word() and R2ROW[0]["files"] == 3
      and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", R2ROW[0]["at"]) is not None and leaks(text_of(row_file(w2))) == [] and sorted(table(row_file(w2))) == ["helper", "rows"], lambda: (R2ROW, text_of(row_file(w2))))
check("2e afterwards the guard - a new process in that workspace - no longer holds the death in any file (exit 0 means exactly that) and does NOT clear the chart either: until Medicare has answered the fresh question the claim is not cleared (NotAnswered - also the claim it blocked before, also from the cache alone); nothing is carried back in, and the other chart's day still blocks",
      lambda: before2 == "blocked" and holds_death(w2, "7411") == [] and asks(w2, "7411", ago(5)) == "reset" and asks(w2, "7411", ago(60)) == "reset" and asks(w2, "7412", ago(5)) == "blocked" and guard_at(w2).cache_state()["lost"] == 1
      and table(reg_of(w2))["7411"] == reask_entry(name="kept as it was"), lambda: (before2, holds_death(w2, "7411"), asks(w2, "7411", ago(5)), asks(w2, "7412", ago(5)), table(reg_of(w2)).get("7411")))
r2b = run(w2, ["7411", "--approved-by", word()]); r2c = run(w2, ["pat7412", "--approved-by", word(ago(1), "chat")])
check("2f a second start for the same chart with the same approval finds nothing on record and its row in the register - exit 3, nothing changed, no second row; another chart (given with 'pat' before its number) is a second row - the register is appended to, never written anew",
      lambda: r2b.code == 3 and framed(r2b) and r2c.code == 0 and [(x["chart"], x["approved_by"], x["files"]) for x in rows(w2)] == [("pat7411", word(), 3), ("pat7412", word(ago(1), "chat"), 1)]
      and table(reg_of(w2))["7412"] == reask_entry(word(ago(1), "chat")), lambda: (r2b.code, r2b.lines, r2c.code, r2c.lines, rows(w2)))
# the cache in use holds NO death for the chart, a stray file does (Medicare said 'no death on record' yesterday, a stray copy still carries the placeholder)
w3 = ws(register={"7421": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record", "name": "kept"}}, old={"7421": {"dod": LOSTD, "checked": iso(ago(90)), "src": "stedi-medicare-271"}})
before3 = asks(ws(register=table(reg_of(w3)), old=table(old_of(w3))), "7421", ago(5)); r3 = run(w3, ["7421", "--approved-by", word()])
w3b = ws(register=None, local={"7422": {"dod": iso(GONE), "checked": iso(ago(9))}}); r3b = run(w3b, ["7422", "--approved-by", word()])
w3c = ws(register={"7499": {"dod": None, "checked": iso(ago(1))}}, local={"7423": {"dod": iso(GONE), "checked": iso(ago(9))}}); r3c = run(w3c, ["7423", "--approved-by", word()])
check("2g the cache in use gets the RE-ASK entry whenever ANY file held a death for the chart - also when its own entry says 'no death on record' (the name stays), when it has no entry for the chart, and when the file is not there yet: the cache the guard answers from is where it reads that the chart is to be asked about afresh",
      lambda: before3 == "lost" and r3.code == 0 and table(reg_of(w3))["7421"] == reask_entry(name="kept") and table(old_of(w3))["7421"] == reask_entry() and asks(w3, "7421", ago(5)) == "reset" and rows(w3)[0]["files"] == 2
      and r3b.code == 0 and table(reg_of(w3b)) == {"7422": reask_entry()} and table(local_of(w3b))["7422"] == reask_entry()
      and r3c.code == 0 and table(reg_of(w3c)) == {"7499": {"dod": None, "checked": iso(ago(1))}, "7423": reask_entry()}, lambda: (before3, r3.code, r3.lines, table(reg_of(w3)), r3b.lines, table(reg_of(w3b)), r3c.lines, table(reg_of(w3c))))
# EVERY death on record for the chart goes - whatever its day and whenever it was put on record (findings 6 and 9 of the third check: the third round left a death
# 'his word did not cover' in place and still ended 0 - a day after the date of his word, a death with no day stamped on the machine's NEXT day during his evening)
AHEAD = iso(TODAY + datetime.timedelta(days=1))
w7 = ws(register={"7441": {"dod": iso(ago(5)), "checked": iso(ago(4)), "src": "stedi-medicare-271"}, "7442": {"dod": "day not known", "checked": AHEAD, "src": "amd: deceased on the chart, no date"}, "7443": {"dod": iso(ago(10)), "checked": iso(ago(4))},
                  "7444": {"dod": LOSTD, "checked": iso(TODAY)}}, local={"7441": {"dod": iso(ago(40)), "checked": iso(ago(30))}, "7442": {"dod": LOSTD}})
res7 = [(c_, r.code, framed(r), r.err, holds_death(w7, c_), asks(w7, c_, TODAY)) for c_, d_ in (("7441", ago(10)), ("7442", ago(1)), ("7443", ago(10)), ("7444", ago(10))) for r in [run(w7, [c_, "--approved-by", word(d_)])]]
check("2h EVERY death on record for the chart goes - there is no 'covered' and 'not covered': a day that lies AFTER the date of his word, a day on that date, a death with no day stamped today - or tomorrow by a machine whose day is ahead of his - are all reset, in every file; the start ends 0 and no cache file the guard knows holds a death for the chart any more",
      lambda: all(x[1] == 0 and x[2] and x[3] == "" and x[4] == [] and x[5] == "reset" for x in res7) and table(reg_of(w7))["7441"] == reask_entry(word(ago(10))) and table(local_of(w7))["7441"] == reask_entry(word(ago(10)))
      and table(reg_of(w7))["7442"] == reask_entry(word(ago(1))) and [x["files"] for x in rows(w7)] == [2, 2, 1, 1], lambda: (res7, rows(w7)))
# nothing on record
w4 = ws(register={"7431": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record"}, "7432": {"dod": "unknown", "checked": iso(ago(1))}}, local={"7434": {"dod": iso(GONE)}}); t4 = (text_of(reg_of(w4)), text_of(local_of(w4)))
res4 = [(c_, r.code, framed(r), r.err, len(r.lines)) for c_ in ("7431", "7432", "7439") for r in [run(w4, [c_, "--approved-by", word()])]]
check("3a nothing on record for the chart - 'no death on record', a value that is no death on record ('unknown'), a chart no file knows: exit 3, nothing is changed in any file and no row is written; the last line says so",
      lambda: all(x[1] == 3 and x[2] and x[3] == "" for x in res4) and (text_of(reg_of(w4)), text_of(local_of(w4))) == t4 and not os.path.exists(row_file(w4)) and all("nothing" in last(run(w4, [c_, "--approved-by", word()])) for c_ in ("7431",)), lambda: res4)
# a file that cannot be read
w5 = ws(register=REG, local='{"7411": {"dod": "20', old="[1, 2, 3]"); r5 = run(w5, ["7411", "--approved-by", word()])
check("3b ANOTHER cache file that cannot be read - cut off, or no table - is passed over and SAID in its line (the guard cannot read it either); it is left byte for byte as it is, the files that can be read are changed, and the last line says that a file could not be read",
      lambda: r5.code == 0 and text_of(local_of(w5)) == '{"7411": {"dod": "20' and text_of(old_of(w5)) == "[1, 2, 3]" and table(reg_of(w5))["7411"] == reask_entry(name="kept as it was") and rows(w5)[0]["files"] == 1
      and sum(1 for l in r5.lines[:-1] if "cannot be read" in l and "passed over" in l) == 2 and framed(r5) and "could not be read" in last(r5), lambda: (r5.code, r5.lines))
w5b = ws(register='{"7411": {"dod": "20', local={"7411": {"dod": iso(GONE), "checked": iso(ago(9))}}); t5b = text_of(local_of(w5b)); r5b = run(w5b, ["7411", "--approved-by", word()])
check("3c the cache IN USE is the file that cannot be read: NOTHING is changed anywhere and the start ends 2 with one plain line - the reset has to stand in the cache the guard answers from, and it cannot be written there (taking the death out of the other file alone would leave a chart nobody asks about: cleared before Medicare has answered); the line says what to do first - merge the copy from Drive (step 0c keeps the unreadable file and puts a table in its place)",
      lambda: r5b.code == 2 and len(r5b.lines) == 1 and framed(r5b) and r5b.err == "" and text_of(reg_of(w5b)) == '{"7411": {"dod": "20' and text_of(local_of(w5b)) == t5b and not os.path.exists(row_file(w5b)) and "step 0c" in last(r5b)
      and asks(w5b, "7411", ago(5)) == "blocked", lambda: (r5b.code, r5b.lines, r5b.err))
# --dry
w6 = ws(register=REG, local=LOC, old=OLD); t6 = [text_of(p) for p in (reg_of(w6), local_of(w6), old_of(w6))]; r6 = run(w6, ["7411", "--approved-by", word(), "--dry"]); r6b = run(w6, ["--dry", "7413", "--approved-by", word()])
check("4a --dry shows what a live start would do - the same line for each file, in 'would' words, and a last line that says DRY - and changes NOTHING: every cache file is byte for byte as it was and no row is written; exit 0 when there is something to reset, 3 when there is nothing",
      lambda: r6.code == 0 and len(r6.lines) == 4 and framed(r6) and "DRY" in last(r6) and sum(1 for l in r6.lines[:3] if "would be" in l) == 3 and [text_of(p) for p in (reg_of(w6), local_of(w6), old_of(w6))] == t6 and not os.path.exists(row_file(w6))
      and r6b.code == 3 and "DRY" in last(r6b), lambda: (r6.code, r6.lines, r6b.code, r6b.lines))

# ---- 6. errors of its own: one plain line, exit 2, never a traceback ---------------------------------------------------------------------------------
w8 = ws(register=REG); t8 = text_of(reg_of(w8)); r8a = run(w8, ["7411", "--approved-by", word()], guard=None)
OLD_GUARD = types.ModuleType("deceased_guard"); OLD_GUARD.CACHE = reg_of(w8); OLD_GUARD._others = lambda: []; OLD_GUARD._day = lambda v: None; OLD_GUARD._unread = lambda v: False; OLD_GUARD.DayLost = type("DayLost", (RuntimeError,), {})      # an earlier guard: it knows no record that was reset
r8b = run(w8, ["7411", "--approved-by", word()], guard=OLD_GUARD)
check("6a no deceased_guard.py beside the helper, or an EARLIER guard (it knows no record that was reset: it would read the entry as 'no death on record' and clear the chart before Medicare has answered): nothing is changed, exit 2, one plain line that says which of the two it is (and what to do about the second: the repository's two helpers first) - never a traceback, never 'an error of its own', and no date in the words (the guard it refuses can be of that very day)",
      lambda: all(r.code == 2 and len(r.lines) == 1 and framed(r) and r.err == "" and "error of its own" not in last(r) for r in (r8a, r8b)) and "could not be loaded" in last(r8a) and "an earlier version" in last(r8b)
      and "make the two helpers the repository's first" in last(r8b) and not re.search(r"\d{1,2}/\d{1,2}/\d{4}", last(r8b)) and text_of(reg_of(w8)) == t8 and not os.path.exists(row_file(w8)), lambda: (r8a.code, r8a.lines, r8a.err, r8b.code, r8b.lines, r8b.err))
os.makedirs(os.path.dirname(row_file(w8)), exist_ok=True)
with open(row_file(w8), "w") as _fh: _fh.write("{ this register cannot be read")
r8c = run(w8, ["7411", "--approved-by", word()])
check("6b its own register is there but cannot be read: NOTHING is changed (the row could not be kept, so no cache file is touched), exit 2 - and the register is left as it is",
      lambda: r8c.code == 2 and framed(r8c) and r8c.err == "" and text_of(reg_of(w8)) == t8 and text_of(row_file(w8)) == "{ this register cannot be read", lambda: (r8c.code, r8c.lines, r8c.err))
_real_replace = os.replace
def refusing(*paths):
    """os.replace that refuses to put a file in the place of one of these paths - a file that cannot be WRITTEN"""
    def _no_replace(a, b):
        if os.path.abspath(b) in [os.path.abspath(p) for p in paths]: raise PermissionError(13, "the stand-in refuses this file")
        return _real_replace(a, b)
    return _no_replace
w9 = ws(register=REG, local=LOC); g9 = guard_at(w9); os.replace = refusing(local_of(w9))
try: r9 = run(w9, ["7411", "--approved-by", word()], guard=g9)
finally: os.replace = _real_replace
check("6c ANOTHER cache file that holds the death cannot be WRITTEN: its line says so, the cache in use and the files that can be written are changed, the row counts what was really changed, and the start ends 2 - the LAST line starts 'DEATH NOT OFF THE RECORD EVERYWHERE:' and still ends ' - TOP OF THE REPORT'; no temporary file is left behind",
      lambda: r9.code == 2 and r9.err == "" and framed(r9, NOT_HEAD) and table(reg_of(w9))["7411"] == reask_entry(name="kept as it was") and table(local_of(w9))["7411"] == LOC["7411"] and rows(w9)[0]["files"] == 1
      and any("could NOT be written" in l for l in r9.lines[:-1]) and holds_death(w9, "7411") == [local_of(w9)] and sorted(os.listdir(w9)) == ["deceased_cache_local.json", "registers"]
      and sorted(os.listdir(os.path.join(w9, "registers"))) == ["death_off_record.json", "deceased_cache.json"], lambda: (r9.code, r9.lines, r9.err, sorted(os.listdir(w9)), sorted(os.listdir(os.path.join(w9, "registers")))))
check("6c2 ... and the chart is still NOT cleared: the cache in use carries the reset, so the guard asks afresh - and the old record in the file that could not be changed does not come back before Medicare was asked (it was checked before the reset)",
      lambda: asks(w9, "7411", ago(5)) == "reset", lambda: asks(w9, "7411", ago(5)))
w9b = ws(register={"7413": {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}}, local=LOC, old={"7411": {"dod": iso(GONE), "checked": iso(ago(9))}}); t9b = [text_of(p) for p in (reg_of(w9b), local_of(w9b), old_of(w9b))]
os.replace = refusing(reg_of(w9b))
try: r9b = run(w9b, ["7411", "--approved-by", word()])
finally: os.replace = _real_replace
check("6d the cache IN USE cannot be written: NOTHING else is changed - no other file loses its death while the reset cannot stand where the guard answers from - no row is written, exit 2, and the last line starts 'DEATH NOT OFF THE RECORD EVERYWHERE:'; the chart stays as it was (here: not cleared, its day unreadable)",
      lambda: r9b.code == 2 and r9b.err == "" and framed(r9b, NOT_HEAD) and [text_of(p) for p in (reg_of(w9b), local_of(w9b), old_of(w9b))] == t9b and not os.path.exists(row_file(w9b)) and asks(w9b, "7411", ago(5)) == "blocked",
      lambda: (r9b.code, r9b.lines, r9b.err))
# the row cannot be written (the mutation h15 of the third check: nothing pinned the exit code there) - and it is not lost for good
w10r = ws(register=REG, local=LOC); os.replace = refusing(row_file(w10r))
try: r10a = run(w10r, ["7411", "--approved-by", word()])
finally: os.replace = _real_replace
st10 = (table(reg_of(w10r)).get("7411"), table(local_of(w10r)).get("7411"), os.path.exists(row_file(w10r)), holds_death(w10r, "7411"))
r10d = run(w10r, ["7411", "--approved-by", word(), "--dry"]); dry10 = os.path.exists(row_file(w10r)); r10b = run(w10r, ["7411", "--approved-by", word()]); rows10 = rows(w10r); r10c = run(w10r, ["7411", "--approved-by", word()])
check("6e (h15) the ROW cannot be written: the cache files ARE changed - no file holds the death any more - but the start ends 2, and its last line says that the row could not be written and what to do: start the helper again with the same approval (it ended 0 with one line changed, and said nothing)",
      lambda: r10a.code == 2 and r10a.err == "" and framed(r10a) and "row could NOT be written" in last(r10a) and "again" in last(r10a) and st10 == (reask_entry(name="kept as it was"), reask_entry(), False, []), lambda: (r10a.code, r10a.lines, r10a.err, st10))
check("6f (finding 7) ... and that row is not lost for good: the next start with the same approval finds the RE-ASK entry in the cache in use and NO row for that chart with that approval - it writes the row and ends 0 (the third round's second start ended 3 and the register never named the chart); --dry before it writes nothing; a third start finds the row and ends 3",
      lambda: r10d.code == 0 and "DRY" in last(r10d) and dry10 is False and r10b.code == 0 and framed(r10b) and r10b.err == "" and [(x["chart"], x["approved_by"], x["files"]) for x in rows10] == [("pat7411", word(), 0)]
      and r10c.code == 3 and len(rows(w10r)) == 1 and table(reg_of(w10r))["7411"] == reask_entry(name="kept as it was"), lambda: (r10d.code, r10d.lines, r10b.code, r10b.lines, rows10, r10c.code))
r10e = run(w10r, ["7411", "--approved-by", word(ago(1), "chat")]); rows10e = rows(w10r); r10f = run(w10r, ["7411", "--approved-by", word(ago(1), "chat")])
check("6g ... and a word given ONCE MORE for a chart whose record is reset already - another day, another place - changes no cache file (the entry keeps the approval it was reset on) but is written down: the register held no row for that chart with THAT approval, so it gets one, exit 0; the same word a second time: exit 3, no further row",
      lambda: r10e.code == 0 and framed(r10e) and [(x["chart"], x["approved_by"], x["files"]) for x in rows10e] == [("pat7411", word(), 0), ("pat7411", word(ago(1), "chat"), 0)] and table(reg_of(w10r))["7411"] == reask_entry(name="kept as it was")
      and r10f.code == 3 and len(rows(w10r)) == 2, lambda: (r10e.code, r10e.lines, rows10e, r10f.code))
w10s = ws(register=REG, local=LOC); os.replace = refusing(row_file(w10s))
try: r10s1 = run(w10s, ["7411", "--approved-by", word()]); r10s2 = run(w10s, ["7411", "--approved-by", word()]); none10s = os.path.exists(row_file(w10s))
finally: os.replace = _real_replace
r10s3 = run(w10s, ["7411", "--approved-by", word()])
check("6f2 ... and a start that finds the reset and cannot write the row EITHER ends 2 again and says so - it never ends 0 while the register holds no row for the chart; the start after it, with the register writable again, writes the row and ends 0",
      lambda: r10s1.code == 2 and r10s2.code == 2 and r10s2.err == "" and framed(r10s2) and "row could NOT be written" in last(r10s2) and "again" in last(r10s2) and none10s is False and r10s3.code == 0
      and [(x["chart"], x["approved_by"], x["files"]) for x in rows(w10s)] == [("pat7411", word(), 0)], lambda: (r10s1.code, r10s2.code, r10s2.lines, r10s2.err, none10s, r10s3.code, rows(w10s)))
w10t = ws(register=REG); r10t1 = run(w10t, ["7411", "--approved-by", word()]); os.replace = refusing(row_file(w10t))      # two charts on ONE word of his - the same approval text - and the second chart's row cannot be written
try: r10t2 = run(w10t, ["7412", "--approved-by", word()])
finally: os.replace = _real_replace
rows10t = rows(w10t); r10t3 = run(w10t, ["7412", "--approved-by", word()])
check("6h ... the row that is missing is looked for by the chart AND the approval: when his one word covered two charts and the second chart's row could not be written, the next start for that chart writes ITS row - the first chart's row with the same approval text is not taken for it",
      lambda: r10t1.code == 0 and r10t2.code == 2 and [(x["chart"], x["files"]) for x in rows10t] == [("pat7411", 1)] and r10t3.code == 0 and framed(r10t3)
      and [(x["chart"], x["approved_by"], x["files"]) for x in rows(w10t)] == [("pat7411", word(), 1), ("pat7412", word(), 0)] and table(reg_of(w10t))["7412"] == reask_entry(), lambda: (r10t1.code, r10t2.code, rows10t, r10t3.code, r10t3.lines, rows(w10t)))
w11 = ws(register=REG, local=LOC); meanwhile11 = {"dod": iso(GONE2), "checked": iso(TODAY), "src": "stedi-medicare-271"}
def _and_meanwhile(a, b):
    """os.replace - and, the moment the helper has put the cache in use in its place, ANOTHER helper writes another chart's day into the workspace's other cache file"""
    out = _real_replace(a, b)
    if os.path.abspath(b) == os.path.abspath(reg_of(w11)):
        t_ = table(local_of(w11)); t_["7499"] = dict(meanwhile11)
        with open(local_of(w11), "w") as fh_: json.dump(t_, fh_, indent=1, sort_keys=True)
    return out
os.replace = _and_meanwhile
try: r11 = run(w11, ["7411", "--approved-by", word()])
finally: os.replace = _real_replace
check("6i each cache file is read AGAIN just before it is written: what another helper wrote into it while this helper was at work - another chart's day, learned a moment ago - stays (written from the first reading, that day was gone and the chart's next claim passed)",
      lambda: r11.code == 0 and r11.err == "" and table(local_of(w11)).get("7499") == meanwhile11 and table(local_of(w11))["7411"] == reask_entry() and table(reg_of(w11))["7411"] == reask_entry(name="kept as it was")
      and asks(w11, "7499", ago(5)) == "blocked", lambda: (r11.code, r11.lines, r11.err, table(local_of(w11))))

# ---- 7. started as a run starts it: a real program in a workspace that holds nothing but the helper and the guard --------------------------------
w10 = ws(register=REG, local=LOC, old=OLD)
for n_ in (HELPER, GUARD): shutil.copy(os.path.join(ROOT, n_), os.path.join(w10, os.path.basename(n_)))
_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.path.join(TMP, "home"), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8", "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9", "NO_PROXY": "", "no_proxy": ""}
def start(argv): p = subprocess.run([sys.executable, "death_off_record.py"] + list(argv), cwd=w10, env=_env, capture_output=True, text=True, timeout=120); SEEN.append(p.stdout); return p.returncode, [l for l in p.stdout.splitlines() if l.strip()], p.stderr
P1 = _try(lambda: start(["7411", "--approved-by", word()]), (None, [], "not started")); P2 = _try(lambda: start(["7411", "--approved-by", "William said so"]), (None, [], "not started")); P3 = _try(lambda: start(["7411", "--approved-by", word()]), (None, [], "not started"))
check("7a as a program a run starts in its workspace (`python3 death_off_record.py <chart number> --approved-by \"William M/D/YYYY (board)\"`, the guard beside it): exit 0, the three files changed, the row written; a word out of shape ends 2; a second start ends 3 - and nothing is written to the error output",
      lambda: P1[0] == 0 and P1[2] == "" and len(P1[1]) == 4 and P1[1][-1].startswith("DEATH OFF THE RECORD:") and P1[1][-1].endswith(" - TOP OF THE REPORT") and table(reg_of(w10))["7411"] == reask_entry(name="kept as it was")
      and table(local_of(w10))["7411"] == reask_entry() and table(old_of(w10))["7411"] == reask_entry() and [x["files"] for x in rows(w10)] == [3] and P2[0] == 2 and P2[2] == "" and P3[0] == 3 and P3[2] == "", lambda: (P1, P2, P3))
w10z = ws(register=REG)
for n_ in (HELPER, GUARD): shutil.copy(os.path.join(ROOT, n_), os.path.join(w10z, os.path.basename(n_)))
_now = datetime.datetime.now(datetime.timezone.utc); _far = ("XXX-14", 14) if _now.hour >= 10 else ("XXX12", -12)      # a machine whose own calendar day is NOT the UTC day right now: its clock fourteen hours ahead of UTC, or twelve behind
_local_day = (_now + datetime.timedelta(hours=_far[1])).date(); _utc_days = {iso(_now.date())}
PZ = _try(lambda: subprocess.run([sys.executable, "death_off_record.py", "7411", "--approved-by", word(ago(3))], cwd=w10z, env=dict(_env, TZ=_far[0]), capture_output=True, text=True, timeout=120), None)
_utc_days.add(iso(utc_day())); SEEN.append(PZ.stdout if PZ is not None else "")
check("7b the day a reset is stamped with is the UTC day the helper ran - also on a machine whose own calendar day is another one right now (its clock fourteen hours ahead of UTC, or twelve behind): the entry carries the UTC day, never that machine's own",
      lambda: PZ is not None and PZ.returncode == 0 and PZ.stderr == "" and iso(_local_day) not in _utc_days and (table(reg_of(w10z)).get("7411") or {}).get("reask") in _utc_days,
      lambda: (PZ and PZ.returncode, PZ and PZ.stdout[-300:], PZ and PZ.stderr[-300:], _far, iso(_local_day), sorted(_utc_days), (table(reg_of(w10z)).get("7411") or {}).get("reask")))

# ---- 8. what the RE-ASK entry MEANS afterwards: the chart is asked about afresh, and Medicare's answer decides --------------------------------------------
# (the rule itself is shown rule by rule in tools/selftest/test_lookup_rules.py, with the real client and answer store on the way; here the road of ONE wrong
#  day, with the entry the REAL helper wrote - and the hook that hands every Medicare answer to the guard standing for Medicare's fresh answer)
def module(rel, name):
    m = types.ModuleType(name); m.__file__ = os.path.join(ROOT, rel); m.UNDER_TEST = True; exec(compile(_read(rel), m.__file__, "exec"), m.__dict__); return m
def lift(rel, *names):
    """functions and constants of a helper by their names, run from its text alone (the import helper cannot be loaded here: it reads its batch files when it is loaded)"""
    import ast
    body = [n for n in ast.parse(_read(rel)).body if (isinstance(n, ast.FunctionDef) and n.name in names) or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    ns = {"re": re, "datetime": datetime}; exec(compile(ast.Module(body=body, type_ignores=[]), rel, "exec"), ns); return ns
ALIVE = {"benefitsInformation": [{"code": "1", "insuranceTypeCode": "MA"}, {"code": "1", "insuranceTypeCode": "MB"}], "errors": []}      # a Medicare answer that shows no death (Part A and Part B lines, no error)
WRONG = {"7451": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept"}, "7453": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept"}}
w11 = ws(register=WRONG, local={"7451": {"dod": LOSTD, "checked": iso(ago(60))}}); r11 = run(w11, ["7451", "--approved-by", word()]); r11b = run(w11, ["7453", "--approved-by", word()]); g11 = guard_at(w11)
wait11 = (asks(w11, "7451", ago(1), g11), asks(w11, "7453", ago(1), g11), g11.covered("7451", iso(ago(1))))
again11 = _try(lambda: g11.record("7451", {"dateOfDeath": ymd(GONE)})); e11 = dict(table(reg_of(w11)).get("7451") or {}); c11 = asks(w11, "7451", ago(1), g11)
none11 = _try(lambda: g11.record("7453", json.loads(json.dumps(ALIVE)))); e11b = dict(table(reg_of(w11)).get("7453") or {}); c11b = asks(w11, "7453", ago(1), g11)
check("8a after the helper the chart is NOT cleared - not before Medicare has answered (NotAnswered; the guard's cache covers no claim of it). Medicare names the SAME day again: it is taken again as for any chart - the entry holds the day, the fields of the reset are gone, the claim is blocked. A word given for the wrong chart cannot let a claim out; and when the day comes again for the right chart, the chart's Medicare number or birth date - or Medicare's own record - is what is wrong (the third round did NOT take the day again: such a word had no way back)",
      lambda: r11.code == 0 and wait11 == ("reset", "reset", False) and again11 == iso(GONE) and e11.get("dod") == iso(GONE) and not {"reask", "approved_by"} & set(e11) and e11.get("name") == "kept" and c11 == "blocked",
      lambda: (r11.code, r11.lines, wait11, again11, e11, c11))
check("8a2 ... and Medicare's fresh answer names NO death: the entry is the ordinary 'no death on record' of today (its name kept, the fields of the reset gone) and the chart is clear again",
      lambda: r11b.code == 0 and none11 is None and e11b == {"dod": None, "checked": iso(TODAY), "name": "kept", "src": "stedi: no death on record"} and c11b == "clear", lambda: (r11b.code, none11, e11b, c11b))
w12 = ws(register=WRONG, local={"7451": {"dod": LOSTD, "checked": iso(ago(60))}}); r12 = run(w12, ["7451", "--approved-by", word()])
DD = _try(lambda: module(DRIVE, "dg_drive_under_test"), None); copy11 = os.path.join(TMP, "drive_copy_12.json"); n11 = _try(lambda: DD.pack(reg_of(w12), copy11)); pk11 = table(copy11)
older = os.path.join(TMP, "drive_copy_older.json")
with open(older, "w") as _fh: json.dump({"format": "deceased_cache_drive v2", "dated": {"7451": [iso(GONE), iso(ago(30))]}, "nodeath": {}, "noday": {"7451": iso(ago(60))}}, _fh)
m12 = _try(lambda: DD.unpack(older, [reg_of(w12)])); m12b = _try(lambda: DD.unpack(copy11, [reg_of(w12)])); e12 = table(reg_of(w12)).get("7451"); c12 = asks(w12, "7451", ago(1))
check("8b the Drive copy packed from that cache carries chart ids and dates only: the chart is a 'no death' note of long ago, in no other list, and no approval text travels (the third round's copy had a list of his words). An OLDER copy that still lists the day - and the death with no day - merged into this workspace at the next step 0c does not bring the old record back: the entry stays the RE-ASK entry, the chart is still to be asked about afresh",
      lambda: isinstance(pk11, dict) and sorted(k for k in pk11 if k != "format") == ["dated", "noday", "nodeath"] and pk11["nodeath"].get("7451") == LONG_AGO and "7451" not in pk11["dated"] and "7451" not in pk11["noday"] and "William" not in json.dumps(pk11)
      and leaks(json.dumps(pk11.get("nodeath"))) == [] and m12 != "raised" and m12b != "raised" and e12 == reask_entry(name="kept") and c12 == "reset", lambda: (n11, pk11, m12, m12b, e12, c12))
F = _try(lambda: lift(IMPORT, "death_day", "death_unread", "death_reask", "death_after", "death_read", "DEATH_NO_DAY", "DEATH_WORDS", "DEATH_REASK_UNDATED"), {}); reads = F.get("death_read")
d13 = _try(lambda: reads([table(reg_of(w12)), {"7451": {"dod": iso(GONE), "checked": iso(ago(30))}}, {"7451": {"dod": LOSTD, "checked": iso(ago(60))}}]))
d14 = _try(lambda: reads([table(reg_of(w12)), {"7451": {"dod": iso(ago(3)), "checked": iso(TODAY + datetime.timedelta(days=1))}}]))
check("8c the feed's import reads that entry as a record that was reset: the chart is asked about afresh before any visit of it is entered, and no OTHER file's older day - nor its placeholder - stands against it; a death another file's entry was checked AFTER the day of the reset stands as for any chart; the chart nobody reset keeps its day",
      lambda: d13 != "raised" and "7451" not in d13[0] and "7451" not in d13[1] and d13[2] == {"7451"} and d13[0]["7453"]["dod"] == iso(GONE) and d14 != "raised" and d14[0]["7451"]["dod"] == iso(ago(3)) and d14[1] == set() and d14[2] == set(), lambda: (d13, d14))

# ---- 9. the helper's own words, what it never does, and the privacy gate ---------------------------------------------------------------------------
def helper_text(): return _read(HELPER)
def header(src):
    out = []
    for l in src.splitlines():
        if not l.startswith("#"): break
        out.append(l.lstrip("# "))
    return " ".join(out)
def code_lines(src):
    """the helper's code alone: no comment line, no trailing comment, no docstring"""
    return "\n".join(l.split("  # ")[0] for l in re.sub(r'"""[\s\S]*?"""', '""', src).splitlines() if not l.lstrip().startswith("#"))
check("9a the helper keeps its PLAIN ENGLISH header: what it decides (nothing - the owner does), on whose word, what his word does (it resets the record, Medicare is asked afresh, its answer decides), what it writes, what it prints, the three exit codes, the usage, what it never does - and the two other holds his word does NOT reach (S4)",
      lambda: helper_text().startswith("#!/usr/bin/env python3\n# PLAIN ENGLISH (") and all(x in header(helper_text()) for x in ("Decides: NOTHING", "William", "ON WHOSE WORD", "WHAT HIS WORD DOES", "WHAT IT WRITES", "WHAT IT PRINTS", "EXIT: 0 =", "3 =", "2 =", "--approved-by", "--dry", "Never", "TOP OF THE REPORT",
                                                                                                                                 "resets the record", "Medicare is asked afresh", "until Medicare has answered", "deceased flag on chart - William", "eligibility answer names a date of death")), lambda: header(helper_text())[:500])
check("9a2 its version line is this round's, and the mirror's table of helpers holds the same line (a workspace copy of the round before must not come back over it)",
      lambda: 'DEATH_OFF_RECORD_VERSION = "2026-11-25.2"' in helper_text() and '"death_off_record.py": \'DEATH_OFF_RECORD_VERSION = "2026-11-25.2"\'' in _read("tools/mirror/mirror.py"), lambda: re.findall(r"DEATH_OFF_RECORD_VERSION = \S+", helper_text() + _read("tools/mirror/mirror.py")))
def imports(src):
    """the first names of every module a piece of Python loads, wherever the import stands in a line (import a.b as c, d / from a import b -> a, d)"""
    out = set()
    for m in re.finditer(r"\bfrom\s+([A-Za-z_][\w.]*)\s+import\b|\bimport\s+([A-Za-z_][\w.]*(?:\s+as\s+\w+)?(?:\s*,\s*[A-Za-z_][\w.]*(?:\s+as\s+\w+)?)*)", src):
        if m.group(1): out.add(m.group(1).split(".")[0])
        else: out.update(x.strip().split()[0].split(".")[0] for x in m.group(2).split(","))
    return out
check("9b it never talks to AdvancedMD or the vendor: its code loads nothing but the standard library and the guard, calls nothing of the guard that asks or carries (check, check_charge, record, stedi_lookup, free_lookup, _load, _carry, _put), and names no call that reaches a billing system",
      lambda: {"deceased_guard"} <= imports(code_lines(helper_text())) <= {"os", "re", "sys", "json", "datetime", "tempfile", "deceased_guard"}
      and not re.search(r"\bG\.(check|check_charge|record|stedi_lookup|free_lookup|_load|_carry|_put|covered|cache_state)\b", code_lines(helper_text())) and not re.search(r"\b(amd|stedi|requests|resave|urllib|socket|subprocess)\b", code_lines(helper_text())),
      lambda: (sorted(set(re.findall(r"\bG\.(\w+)", code_lines(helper_text())))), re.findall(r"\b(amd|stedi|requests|resave|urllib|socket|subprocess)\b", code_lines(helper_text()))[:5]))
GONE_RX = "|".join(["_be" + "ats", "_o" + r"ff\b", "OFF" + "_SRC", "off_" + 'record"', "LAT" + r"ER\b", "cov" + "ers"])      # the names of the third round's rule, put together here
check("9b2 nothing of the third round's rule is left in the helper: it compares no death with the date of his word (no 'covered' and 'not covered', no later day that stays)",
      lambda: not re.search(GONE_RX, code_lines(helper_text())) and ("on or before " + "its date") not in helper_text() and ("a later day is a n" + "ew death") not in helper_text(),
      lambda: re.findall(GONE_RX, code_lines(helper_text()))[:5])
check("9c in this whole self-test no printed line and no register of the helper showed a day somebody passed away on, or the placeholder that stands for one", lambda: len(SEEN) > 60 and [x for s in SEEN for x in leaks(s)] == [] and not any(LOSTD in s for s in SEEN), lambda: sorted({x for s in SEEN for x in leaks(s)}))
GATE = None
try:
    GATE = types.ModuleType("phi_gate_under_test"); GATE.__file__ = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
    exec(compile(_read("tools/mirror/phi_gate.py"), GATE.__file__, "exec"), GATE.__dict__)      # the gate's text transform only: pure, no file, no network
except Exception: GATE = None
for rel in ("tools/selftest/test_death_off_record.py", HELPER):
    check("9d the privacy gate's tree rules leave %s exactly as it is (every invented value is put together at run time)" % rel,
          lambda rel=rel: GATE.redact(_read(rel), {}, code=True) == _read(rel), lambda rel=rel: [(a, b) for a, b in zip(_read(rel).splitlines(), GATE.redact(_read(rel), {}, code=True).splitlines()) if a != b][:2])
_written = [text_of(p) or "" for p in glob.glob(os.path.join(TMP, "w*", "home", "ws", "registers", "*.json")) + glob.glob(os.path.join(TMP, "w*", "home", "ws", "*.json"))]
_tables = [json.loads(t) for t in _written if _try(lambda t=t: json.loads(t), None) is not None and "reask" in t]
_only = [{k: v for k, v in t.items() if isinstance(v, dict) and v.get("reask")} for t in _tables if isinstance(t, dict)]
_as_written = [json.dumps(t, indent=1, sort_keys=True) for t in _only] + [json.dumps(t) for t in _only] + [json.dumps(t, sort_keys=True) for t in _only]      # as the helper and the guard write a cache file (one entry to a block of lines), and on one line with the usual separators
check("9e the gate also leaves alone every line the helper printed, every row it kept and every RE-ASK entry it wrote into a cache file - as the cache files are written, and on one line too (the day the helper ran and the approval text reach the repository as they were written: the entry still says what it means there)",
      lambda: len(SEEN) > 60 and len(_only) > 10 and [s[:120] for s in SEEN + _as_written if s and GATE.redact(s, {}, code=False) != s] == [],
      lambda: [[(a, b) for a, b in zip(s.splitlines(), GATE.redact(s, {}, code=False).splitlines()) if a != b][:1] for s in SEEN + _as_written if s and GATE.redact(s, {}, code=False) != s][:3])
_tight = json.dumps({"7": reask_entry()}, sort_keys=True, separators=(",", ":")); _scrubbed = _try(lambda: json.loads(GATE.redact(_tight, {}, code=False)), {})
check("9f ... and should a copy written WITHOUT blanks ever reach the gate (nothing here writes one: the day the helper ran then stands sixteen characters behind the entry's day place, and the gate takes it for a day), the guard still reads the entry as a record that was reset - with no day it can read: asked afresh, nothing brought in, never cleared by it",
      lambda: isinstance(_scrubbed.get("7"), dict) and guard_at(w2)._reask(_scrubbed["7"]) is not None and _scrubbed["7"].get("approved_by") == word(), lambda: (_tight, _scrubbed))
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, lambda: sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_death_off_record: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
