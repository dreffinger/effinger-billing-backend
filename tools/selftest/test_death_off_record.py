#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of death_off_record.py - the ONE way a death comes off the deceased guard's record: on the owner's word.
#   The third round (11/25/2026) of the date-of-death check - the second independent check's finding 2: the guard keeps a death for good, and
#   a death on record that is WRONG - one answer for another person, a stale placeholder in a stray file - had no way out but a hand edit in
#   up to five places, which the next carry or the next merge of the Drive copy undid.)
# Decides: nothing. It runs the helper (scripts/helpers/death_off_record.py) INSIDE this process, as the program a run starts, in throwaway
#   workspaces - and once as a real program in a workspace that holds nothing but the helper and the guard. The guard beside it is the REAL
#   scripts/helpers/deceased_guard.py, loaded as if it stood in that workspace (so its cache is the workspace's register and its other cache
#   files are the workspace's); the Drive tool (dg_drive.py) and the import's reading of the cache files (claimocity_import.death_read) are the
#   real ones too. No network, no AdvancedMD, no vendor: nothing here loads a module that could reach either, and the network is shut.
#   Every chart number and every day is invented and put together at run time. It proves:
#     - the word: the approval must be exactly 'William <M>/<D>/<YYYY> (board)' or '(chat)', a real calendar date not after today - anything
#       else changes nothing and ends 2, and what was typed is never printed back; a chart number is digits (with or without 'pat');
#     - the work: in the guard's cache in use and in every other cache file the guard knows, the chart's entry that holds a death - a day, or
#       a death on record with no day - becomes the OFF entry (dod null, checked today, the fixed source, the date of his word, the approval
#       text; the entry's name stays); the cache in use gets it whenever any file held a death; nothing else in any file changes; a file
#       that cannot be read is passed over and said; a day AFTER the date of his word is a new death and is not taken off;
#     - what it says and keeps: one line per file, a last line that starts 'DEATH OFF THE RECORD:' and ends ' - TOP OF THE REPORT', never
#       the day itself; ONE row in registers/death_off_record.json - the chart, a UTC stamp, the approval text, the number of files changed;
#     - the exit codes: 0 done, 3 nothing on record (nothing changed, no row), 2 usage / approval / an error of its own - one plain line,
#       never a traceback; --dry changes nothing;
#     - what the OFF entry MEANS afterwards (one rule: his word of date D beats every day reported on or before D; a day after D is a new
#       death): the guard does not block and does not take the same day again - from an answer, from a look-up, from another cache file,
#       from the Drive copy - while a LATER day is taken as for any chart; the Drive copy carries the note to the next machine; the import
#       reads the entry as 'no death' and lets no other file's older day stand against it.
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
OFF_SRC = "off the record on the owner's word"
SECRETS = faces(GONE) + faces(GONE2)      # no printed line and no register may show a day somebody passed away on
def leaks(text): return [s for s in SECRETS if s in str(text)]
def off_entry(d=None, text=None, **more):
    d = d or TODAY; e = {"dod": None, "checked": iso(TODAY), "src": OFF_SRC, "off_record": iso(d), "approved_by": text or word(d)}; e.update(more); return e

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
def framed(r): return last(r).startswith("DEATH OFF THE RECORD:") and last(r).endswith(" - TOP OF THE REPORT")
def rows(w):
    t = table(row_file(w)); return t.get("rows") if isinstance(t, dict) else t
CLAIM = ("car6404", "99349")      # a claim to another payer with an ordinary code: the guard answers it from its cache alone
def asks(w, chart, dos, g=None):
    """what the guard of that workspace (a new module: a new process) answers for a claim of that chart and date, from its cache only -> 'blocked' / 'clear' / 'lost' / the error's kind"""
    g = g or guard_at(w)
    try: return "blocked" if g.check(chart, iso(dos), CLAIM[0], CLAIM[1], allow_lookup=False)[0] else "clear"
    except Exception as e: return "lost" if type(e).__name__ == "DayLost" else type(e).__name__

# ---- 0. the safety block holds, and the helper is where the workspace builders copy helpers from -----------------------------------------------
check("0a safety: the real `requests`, a live helper and any module of the checkout are refused by the import blocker; the network is shut",
      lambda: _raises(lambda: _Refuse().find_spec("requests"), ImportError) and _raises(lambda: _Refuse().find_spec("amd"), ImportError) and _raises(lambda: _socket.create_connection(("127.0.0.1", 9)), RuntimeError))
check("0b the helper is in the repository, in the folder the workspace builders copy helpers from (scripts/helpers)", lambda: _exists(HELPER), HELPER)

# ---- 1. the word: who, when, where - and nothing else ----------------------------------------------------------------------------------------------
ONE = {"7401": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept as it was"}, "7402": {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}}
Y = TODAY.year; SOON = TODAY + datetime.timedelta(days=1)
BAD_WORDS = ["William", "William (board)", word().replace("William", "william"), word().replace("William", "Bill"), word().replace(" (board)", ""), word(where="email"), word(where="Board"), word() + " and more", " " + word(), word() + " ",
             "Dr. " + word(), word().replace("William ", "William  "), "William %s (board)" % iso(TODAY), "William %d/%d/%02d (board)" % (TODAY.month, TODAY.day, Y % 100), "William 13/45/%d (board)" % Y, "William 2/30/%d (board)" % Y,
             "William 0/10/%d (board)" % Y, word(SOON), word(TODAY + datetime.timedelta(days=400)), "the chart is alive - William said so", "", word().replace("(board)", "[board]"), word() + "\n" + word()]
w1 = ws(register=ONE); t1 = text_of(reg_of(w1)); res1 = []
for b in BAD_WORDS:
    r = run(w1, ["7401", "--approved-by", b]); res1.append((b, r.code, len(r.lines), framed(r), r.err, text_of(reg_of(w1)) == t1, os.path.exists(row_file(w1)), (b.strip() != "" and len(b) > 9 and b.strip() in r.out)))
check("1a the approval must be EXACTLY 'William <M>/<D>/<YYYY> (board)' or '(chat)' with a real calendar date not after today: every other text - no date, another name, another place, more words, a date that is none, a date after today, a date in another shape - changes NOTHING and ends 2 with one plain line",
      lambda: len(res1) == len(BAD_WORDS) >= 20 and all(x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5] and not x[6] for x in res1), lambda: [x for x in res1 if not (x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5] and not x[6])][:4])
check("1b ... and what was typed is never printed back (no free text reaches a log or a report: this helper's register goes to a public repository)", lambda: not any(x[7] for x in res1), lambda: [x[0] for x in res1 if x[7]])
ARGS = [[], ["7401"], ["--approved-by", word()], ["7401", "--approved-by"], ["7401", "7402", "--approved-by", word()], ["74x1", "--approved-by", word()], ["pat", "--approved-by", word()], ["", "--approved-by", word()],
        ["7401", "--approved-by", word(), "--live"], ["7401", "--approved-by", word(), "--approved-by", word()], ["7401", "--by", word()], ["7401 7402", "--approved-by", word()], ["-7401", "--approved-by", word()]]
res2 = [(a, r.code, len(r.lines), framed(r), r.err, text_of(reg_of(w1)) == t1) for a in ARGS for r in [run(w1, a)]]
check("1c the usage: ONE chart number (digits, with or without 'pat' before them) and ONE approval - no chart, two charts, a chart that is no number, no approval, two approvals, an option it does not know: nothing is changed, exit 2, one plain line",
      lambda: all(x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5] for x in res2), lambda: [x for x in res2 if not (x[1] == 2 and x[2] == 1 and x[3] and x[4] == "" and x[5])][:4])
GOOD = [word(), word(padded=True), word(where="chat"), word(ago(1)), word(ago(35), "chat"), word(ago(35), "board", padded=True)]      # (the entry's day lies 40 days back: each of these words is of a later date, so it covers that day)
res3 = []
for g_ in GOOD:
    w = ws(register=ONE); r = run(w, ["7401", "--approved-by", g_]); res3.append((g_, r.code, r.err, (table(reg_of(w)) or {}).get("7401")))
check("1d the word in its shape is taken: today's date or an earlier one, with or without a leading zero, said on the board or in chat - exit 0, and the entry carries that very text and the date of his word as YYYY-MM-DD",
      lambda: all(x[1] == 0 and x[2] == "" and isinstance(x[3], dict) and x[3].get("approved_by") == x[0] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(x[3].get("off_record"))) for x in res3)
      and res3[0][3]["off_record"] == res3[1][3]["off_record"] == iso(TODAY) and res3[3][3]["off_record"] == iso(ago(1)), lambda: res3)

# ---- 2. the work: every cache file the guard knows -------------------------------------------------------------------------------------------------
REG = {"7411": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept as it was"}, "7412": {"dod": iso(GONE2), "checked": iso(ago(9)), "src": "x"}, "7413": {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}}
LOC = {"7411": {"dod": LOSTD, "checked": iso(ago(60)), "src": "stedi-medicare-271"}, "7414": {"dod": LOSTD, "checked": iso(ago(60))}}
OLD = {"7411": {"dod": "day not known", "checked": iso(ago(3)), "src": "amd: deceased on the chart, no date"}, "7415": {"dod": ymd(GONE2), "checked": iso(ago(9))}, "a line": "that is no entry"}
w2 = ws(register=REG, local=LOC, old=OLD); before2 = asks(w2, "7411", ago(5)); g2 = guard_at(w2); files2 = [g2.CACHE] + list(g2._others())
w2 = ws(register=REG, local=LOC, old=OLD)      # (asking the guard above carried the other files' entries into the register: the helper gets a workspace nobody has touched)
r2 = run(w2, ["7411", "--approved-by", word()]); T2 = {"reg": table(reg_of(w2)), "loc": table(local_of(w2)), "old": table(old_of(w2))}
check("2a the chart's entry becomes the OFF entry in the guard's cache in use AND in every other cache file the guard knows - a day, the placeholder, 'day not known' alike: dod null, checked today, the fixed source, the date of his word, the approval text - and the name the entry had stays",
      lambda: r2.code == 0 and r2.err == "" and len(files2) == 3 and T2["reg"]["7411"] == off_entry(name="kept as it was") and T2["loc"]["7411"] == off_entry() and T2["old"]["7411"] == off_entry(),
      lambda: (r2.code, r2.err, r2.lines, files2, {k: (v.get("7411") if isinstance(v, dict) else v) for k, v in T2.items()}))
check("2b ... and NOTHING else in any of those files changes: every other chart's entry, and a line that is no entry, are as they were",
      lambda: {k: v for k, v in T2["reg"].items() if k != "7411"} == {k: v for k, v in REG.items() if k != "7411"} and {k: v for k, v in T2["loc"].items() if k != "7411"} == {k: v for k, v in LOC.items() if k != "7411"}
      and {k: v for k, v in T2["old"].items() if k != "7411"} == {k: v for k, v in OLD.items() if k != "7411"}, lambda: T2)
check("2c what it prints: ONE line for each cache file (the path, what stood there in words, what was done) and a LAST line that starts 'DEATH OFF THE RECORD:' and ends ' - TOP OF THE REPORT' and names the chart, the number of files and the approval - never the day itself",
      lambda: len(r2.lines) == 4 and framed(r2) and all(any(p in l for l in r2.lines[:3]) for p in (reg_of(w2), local_of(w2), old_of(w2))) and "pat7411" in last(r2) and "3 cache file(s)" in last(r2) and word() in last(r2)
      and leaks(r2.out) == [] and LOSTD not in r2.out, lambda: r2.lines)
R2ROW = rows(w2)
check("2d what it keeps: ONE row in registers/death_off_record.json - the chart, a UTC stamp, the approval text, the number of files changed - and nothing else",
      lambda: isinstance(R2ROW, list) and len(R2ROW) == 1 and sorted(R2ROW[0]) == ["approved_by", "at", "chart", "files"] and R2ROW[0]["chart"] == "pat7411" and R2ROW[0]["approved_by"] == word() and R2ROW[0]["files"] == 3
      and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", R2ROW[0]["at"]) is not None and leaks(text_of(row_file(w2))) == [], lambda: (R2ROW, text_of(row_file(w2))))
check("2e afterwards the guard - a new process in that workspace - does not block the claim it blocked before, and the chart is no death on record in any file (nothing is carried back in)",
      lambda: before2 == "blocked" and asks(w2, "7411", ago(5)) == "clear" and asks(w2, "7412", ago(5)) == "blocked" and guard_at(w2).cache_state()["lost"] == 1 and table(reg_of(w2))["7411"] == off_entry(name="kept as it was"),
      lambda: (before2, asks(w2, "7411", ago(5)), asks(w2, "7412", ago(5)), table(reg_of(w2)).get("7411")))
r2b = run(w2, ["7411", "--approved-by", word()]); r2c = run(w2, ["pat7412", "--approved-by", word(ago(1), "chat")])
check("2f a second start for the same chart finds nothing on record - exit 3, nothing changed, no second row; another chart (given with 'pat' before its number) is a second row - the register is appended to, never written anew",
      lambda: r2b.code == 3 and framed(r2b) and r2c.code == 0 and [(x["chart"], x["approved_by"], x["files"]) for x in rows(w2)] == [("pat7411", word(), 3), ("pat7412", word(ago(1), "chat"), 1)]
      and table(reg_of(w2))["7412"] == off_entry(ago(1), word(ago(1), "chat")), lambda: (r2b.code, r2b.lines, r2c.code, r2c.lines, rows(w2)))
# the cache in use holds NO death for the chart, a stray file does (the checker's own case: Medicare said 'no death on record' yesterday, a stray copy still carries the placeholder)
w3 = ws(register={"7421": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record", "name": "kept"}}, old={"7421": {"dod": LOSTD, "checked": iso(ago(90)), "src": "stedi-medicare-271"}})
before3 = asks(ws(register=table(reg_of(w3)), old=table(old_of(w3))), "7421", ago(5)); r3 = run(w3, ["7421", "--approved-by", word()])
w3b = ws(register=None, local={"7422": {"dod": iso(GONE), "checked": iso(ago(9))}}); r3b = run(w3b, ["7422", "--approved-by", word()])
w3c = ws(register={"7499": {"dod": None, "checked": iso(ago(1))}}, local={"7423": {"dod": iso(GONE), "checked": iso(ago(9))}}); r3c = run(w3c, ["7423", "--approved-by", word()])
check("2g the cache in use gets the OFF entry whenever ANY file held a death for the chart - also when its own entry says 'no death on record' (the name stays), when it has no entry for the chart, and when the file is not there yet: the next carry, or a look-up that hits the same wrong answer again, finds the owner's word in the cache the guard answers from",
      lambda: before3 == "lost" and r3.code == 0 and table(reg_of(w3))["7421"] == off_entry(name="kept") and table(old_of(w3))["7421"] == off_entry() and asks(w3, "7421", ago(5)) == "clear" and rows(w3)[0]["files"] == 2
      and r3b.code == 0 and table(reg_of(w3b)) == {"7422": off_entry()} and table(local_of(w3b))["7422"] == off_entry()
      and r3c.code == 0 and table(reg_of(w3c)) == {"7499": {"dod": None, "checked": iso(ago(1))}, "7423": off_entry()}, lambda: (before3, r3.code, r3.lines, table(reg_of(w3)), r3b.lines, table(reg_of(w3b)), r3c.lines, table(reg_of(w3c))))
# nothing on record
w4 = ws(register={"7431": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record"}, "7432": {"dod": "unknown", "checked": iso(ago(1))}, "7433": off_entry(ago(3))}, local={"7434": {"dod": iso(GONE)}}); t4 = (text_of(reg_of(w4)), text_of(local_of(w4)))
res4 = [(c_, r.code, framed(r), r.err, len(r.lines)) for c_ in ("7431", "7432", "7433", "7439") for r in [run(w4, [c_, "--approved-by", word()])]]
check("3a nothing on record for the chart - 'no death on record', a value that is no death on record ('unknown'), an entry that is OFF already, a chart no file knows: exit 3, nothing is changed in any file and no row is written; the last line says so",
      lambda: all(x[1] == 3 and x[2] and x[3] == "" for x in res4) and (text_of(reg_of(w4)), text_of(local_of(w4))) == t4 and not os.path.exists(row_file(w4)), lambda: res4)
# a file that cannot be read
w5 = ws(register=REG, local='{"7411": {"dod": "20', old="[1, 2, 3]"); r5 = run(w5, ["7411", "--approved-by", word()])
check("3b a cache file that cannot be read - cut off, or no table - is passed over and SAID in its line; it is left byte for byte as it is, the other files are changed, and the start ends 0",
      lambda: r5.code == 0 and text_of(local_of(w5)) == '{"7411": {"dod": "20' and text_of(old_of(w5)) == "[1, 2, 3]" and table(reg_of(w5))["7411"] == off_entry(name="kept as it was") and rows(w5)[0]["files"] == 1
      and sum(1 for l in r5.lines[:-1] if "cannot be read" in l and "passed over" in l) == 2 and framed(r5), lambda: (r5.code, r5.lines))
w5b = ws(register='{"7411": {"dod": "20', local={"7411": {"dod": iso(GONE), "checked": iso(ago(9))}}); r5b = run(w5b, ["7411", "--approved-by", word()])
check("3c ... the same when the cache IN USE is the file that cannot be read: it is never written over; the other file's entry is taken off (the guard, which cannot read that file either, then holds nothing of the chart in memory) - and the last line says a file could not be read",
      lambda: r5b.code == 0 and text_of(reg_of(w5b)) == '{"7411": {"dod": "20' and table(local_of(w5b))["7411"] == off_entry() and "could not be read" in last(r5b) and asks(w5b, "7411", ago(5)) == "clear", lambda: (r5b.code, r5b.lines))
# --dry
w6 = ws(register=REG, local=LOC, old=OLD); t6 = [text_of(p) for p in (reg_of(w6), local_of(w6), old_of(w6))]; r6 = run(w6, ["7411", "--approved-by", word(), "--dry"]); r6b = run(w6, ["--dry", "7413", "--approved-by", word()])
check("4a --dry shows what a live start would do - the same line for each file, in 'would' words, and a last line that says DRY - and changes NOTHING: every cache file is byte for byte as it was and no row is written; exit 0 when there is something to take off, 3 when there is nothing",
      lambda: r6.code == 0 and len(r6.lines) == 4 and framed(r6) and "DRY" in last(r6) and [text_of(p) for p in (reg_of(w6), local_of(w6), old_of(w6))] == t6 and not os.path.exists(row_file(w6)) and r6b.code == 3 and "DRY" in last(r6b), lambda: (r6.code, r6.lines, r6b.code, r6b.lines))
# ---- 5. what his word covers: every day reported on or before its date - a LATER day is a new death ----------------------------------------------
w7 = ws(register={"7441": {"dod": iso(ago(5)), "checked": iso(ago(4)), "src": "stedi-medicare-271"}, "7442": {"dod": LOSTD, "checked": iso(ago(4)), "src": "x"}, "7443": {"dod": iso(ago(10)), "checked": iso(ago(4))}, "7444": {"dod": LOSTD, "checked": iso(ago(10))}},
         local={"7441": {"dod": iso(ago(40)), "checked": iso(ago(30))}}); t7 = text_of(reg_of(w7))
r7a = run(w7, ["7441", "--approved-by", word(ago(10))]); r7b = run(w7, ["7442", "--approved-by", word(ago(10))]); mid7 = (text_of(reg_of(w7)) == t7, table(local_of(w7)).get("7441"))
r7c = run(w7, ["7443", "--approved-by", word(ago(10))]); r7d = run(w7, ["7444", "--approved-by", word(ago(10))])
check("5a a day that lies AFTER the date of his word is a NEW death: it is NOT taken off, and its line says so - the cache in use keeps it and the claim after it stays blocked - while a day on or before that date, in another file of the same chart, is taken off there; a death on record with no day that was reported AFTER his word stays too",
      lambda: r7a.code == 0 and mid7[0] and mid7[1] == off_entry(ago(10)) and any("AFTER" in l for l in r7a.lines[:-1]) and table(reg_of(w7))["7441"]["dod"] == iso(ago(5)) and asks(w7, "7441", ago(2)) == "blocked"
      and r7b.code == 3 and any("AFTER" in l for l in r7b.lines[:-1]) and table(reg_of(w7))["7442"]["dod"] == LOSTD, lambda: (r7a.code, r7a.lines, mid7, r7b.code, r7b.lines))
check("5b ... a day ON the date of his word, and a death with no day reported on that date, ARE covered by it: both are taken off", lambda: r7c.code == 0 and r7d.code == 0 and table(reg_of(w7))["7443"] == off_entry(ago(10)) and table(reg_of(w7))["7444"] == off_entry(ago(10)),
      lambda: (r7c.code, r7c.lines, r7d.code, r7d.lines, table(reg_of(w7))))
# his word of an EARLIER date never takes the place of a later word (the guard's carry and the Drive merge hold the same): the cache in use holds his word of
# 3 days ago; a stray file still holds the old day; the helper is started once more with his word of 10 days ago (an older board card worked a second time)
LATER_WORD = dict(off_entry(ago(3)), checked=iso(ago(3)), name="kept")
w7e = ws(register={"7445": dict(LATER_WORD), "7446": dict(off_entry(ago(20)), checked=iso(ago(20)))}, local={"7445": {"dod": iso(ago(40)), "checked": iso(ago(30))}, "7446": {"dod": iso(ago(40)), "checked": iso(ago(30))}}); t7e = table(reg_of(w7e))
r7e = run(w7e, ["7445", "--approved-by", word(ago(10))]); r7f = run(w7e, ["7446", "--approved-by", word(ago(10))]); r7g = run(w7e, ["7445", "--approved-by", word(ago(10)), "--dry"])
check("5c his word of an EARLIER date never takes the place of a LATER word: a cache in use that already holds his word of a later date keeps it exactly as it is (its line says so) while the other file's day is taken off on the word given - a day reported between the two dates stays covered; a word in the cache in use that is OLDER than the one given is replaced by it",
      lambda: r7e.code == 0 and table(reg_of(w7e))["7445"] == LATER_WORD and table(local_of(w7e))["7445"] == off_entry(ago(10)) and any("later date" in l and "unchanged" in l for l in r7e.lines[:-1]) and "1 cache file(s)" in last(r7e)
      and [x["files"] for x in rows(w7e)] == [1, 2] and r7f.code == 0 and table(reg_of(w7e))["7446"] == off_entry(ago(10)) and table(local_of(w7e))["7446"] == off_entry(ago(10)) and r7g.code == 3,
      lambda: (r7e.code, r7e.lines, table(reg_of(w7e)), table(local_of(w7e)), r7f.code, r7f.lines, rows(w7e), r7g.code))

# ---- 6. errors of its own: one plain line, exit 2, never a traceback ---------------------------------------------------------------------------------
w8 = ws(register=REG); t8 = text_of(reg_of(w8)); r8a = run(w8, ["7411", "--approved-by", word()], guard=None)
OLD_GUARD = types.ModuleType("deceased_guard"); OLD_GUARD.CACHE = reg_of(w8); OLD_GUARD._others = lambda: []; OLD_GUARD._day = lambda v: None      # a guard from before the third round: it knows no entry taken off the record
r8b = run(w8, ["7411", "--approved-by", word()], guard=OLD_GUARD)
check("6a no deceased_guard.py beside the helper, or a guard from before the third round (it would not know what the OFF entry means): nothing is changed, exit 2, one plain line that says which of the two it is (and what to do about the second: the repository's two helpers first) - never a traceback, never 'an error of its own'",
      lambda: all(r.code == 2 and len(r.lines) == 1 and framed(r) and r.err == "" and "error of its own" not in last(r) for r in (r8a, r8b)) and "could not be loaded" in last(r8a) and "is from before" in last(r8b)
      and "make the two helpers the repository's first" in last(r8b) and text_of(reg_of(w8)) == t8 and not os.path.exists(row_file(w8)), lambda: (r8a.code, r8a.lines, r8a.err, r8b.code, r8b.lines, r8b.err))
os.makedirs(os.path.dirname(row_file(w8)), exist_ok=True)
with open(row_file(w8), "w") as _fh: _fh.write("{ this register cannot be read")
r8c = run(w8, ["7411", "--approved-by", word()])
check("6b its own register is there but cannot be read: NOTHING is changed (the row could not be kept, so no cache file is touched), exit 2 - and the register is left as it is",
      lambda: r8c.code == 2 and framed(r8c) and r8c.err == "" and text_of(reg_of(w8)) == t8 and text_of(row_file(w8)) == "{ this register cannot be read", lambda: (r8c.code, r8c.lines, r8c.err))
w9 = ws(register=REG, local=LOC); g9 = guard_at(w9); _real_replace = os.replace
def _no_replace(a, b):
    if os.path.abspath(b) == os.path.abspath(local_of(w9)): raise PermissionError(13, "the stand-in refuses this file")
    return _real_replace(a, b)
os.replace = _no_replace
try: r9 = run(w9, ["7411", "--approved-by", word()], guard=g9)
finally: os.replace = _real_replace
check("6c a cache file that cannot be WRITTEN: its line says so, the other files are still changed, the row counts what was really changed, and the start ends 2 - the death is NOT off the record everywhere, and the last line says it; no temporary file is left behind",
      lambda: r9.code == 2 and r9.err == "" and framed(r9) and table(reg_of(w9))["7411"] == off_entry(name="kept as it was") and table(local_of(w9))["7411"] == LOC["7411"] and rows(w9)[0]["files"] == 1
      and any("could NOT be written" in l for l in r9.lines[:-1]) and "NOT" in last(r9) and sorted(os.listdir(w9)) == ["deceased_cache_local.json", "registers"] and sorted(os.listdir(os.path.join(w9, "registers"))) == ["death_off_record.json", "deceased_cache.json"],
      lambda: (r9.code, r9.lines, r9.err, sorted(os.listdir(w9)), sorted(os.listdir(os.path.join(w9, "registers")))))

# ---- 7. started as a run starts it: a real program in a workspace that holds nothing but the helper and the guard --------------------------------
w10 = ws(register=REG, local=LOC, old=OLD)
for n_ in (HELPER, GUARD): shutil.copy(os.path.join(ROOT, n_), os.path.join(w10, os.path.basename(n_)))
_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.path.join(TMP, "home"), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8", "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9", "NO_PROXY": "", "no_proxy": ""}
def start(argv): p = subprocess.run([sys.executable, "death_off_record.py"] + list(argv), cwd=w10, env=_env, capture_output=True, text=True, timeout=120); SEEN.append(p.stdout); return p.returncode, [l for l in p.stdout.splitlines() if l.strip()], p.stderr
P1 = _try(lambda: start(["7411", "--approved-by", word()]), (None, [], "not started")); P2 = _try(lambda: start(["7411", "--approved-by", "William said so"]), (None, [], "not started")); P3 = _try(lambda: start(["7411", "--approved-by", word()]), (None, [], "not started"))
check("7a as a program a run starts in its workspace (`python3 death_off_record.py <chart number> --approved-by \"William M/D/YYYY (board)\"`, the guard beside it): exit 0, the three files changed, the row written; a word out of shape ends 2; a second start ends 3 - and nothing is written to the error output",
      lambda: P1[0] == 0 and P1[2] == "" and len(P1[1]) == 4 and P1[1][-1].startswith("DEATH OFF THE RECORD:") and P1[1][-1].endswith(" - TOP OF THE REPORT") and table(reg_of(w10))["7411"] == off_entry(name="kept as it was")
      and table(local_of(w10))["7411"] == off_entry() and table(old_of(w10))["7411"] == off_entry() and [x["files"] for x in rows(w10)] == [3] and P2[0] == 2 and P2[2] == "" and P3[0] == 3 and P3[2] == "", lambda: (P1, P2, P3))

# ---- 8. what the OFF entry MEANS afterwards: the day does not come back - from an answer, another file, the Drive copy - and a LATER day is taken -----
# (the rule itself is shown rule by rule in tools/selftest/test_lookup_rules.py; here the road of ONE wrong day, with the entry the REAL helper wrote)
def module(rel, name):
    m = types.ModuleType(name); m.__file__ = os.path.join(ROOT, rel); m.UNDER_TEST = True; exec(compile(_read(rel), m.__file__, "exec"), m.__dict__); return m
def lift(rel, *names):
    """functions and constants of a helper by their names, run from its text alone (the import helper cannot be loaded here: it reads its batch files when it is loaded)"""
    import ast
    body = [n for n in ast.parse(_read(rel)).body if (isinstance(n, ast.FunctionDef) and n.name in names) or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    ns = {"re": re, "datetime": datetime}; exec(compile(ast.Module(body=body, type_ignores=[]), rel, "exec"), ns); return ns
WRONG = {"7451": {"dod": iso(GONE), "checked": iso(ago(30)), "src": "stedi-medicare-271", "name": "kept"}}
w11 = ws(register=WRONG, local={"7451": {"dod": LOSTD, "checked": iso(ago(60))}}); r11 = run(w11, ["7451", "--approved-by", word()]); g11 = guard_at(w11)
again11 = _try(lambda: g11.record("7451", {"dateOfDeath": ymd(GONE)})); e11 = dict(table(reg_of(w11)).get("7451") or {}); c11 = asks(w11, "7451", ago(1), g11)
later11 = _try(lambda: g11.record("7452", {"dateOfDeath": ymd(GONE)})); l11 = asks(w11, "7452", ago(1), g11)      # control: for a chart nobody took off the record the same answer is taken and blocks
check("8a after the helper, the SAME wrong day reported again - the hook that keeps every Medicare answer hands it to the guard - is NOT taken: the entry stays OFF with his word in it, and the claim is not blocked; for a chart nobody took off the record that answer blocks as always",
      lambda: r11.code == 0 and again11 == iso(GONE) and e11.get("dod") is None and e11.get("off_record") == iso(TODAY) and e11.get("approved_by") == word() and e11.get("name") == "kept" and c11 == "clear" and later11 == iso(GONE) and l11 == "blocked",
      lambda: (r11.code, r11.lines, again11, e11, c11, l11))
DD = _try(lambda: module(DRIVE, "dg_drive_under_test"), None); copy11 = os.path.join(TMP, "drive_copy_11.json"); n11 = _try(lambda: DD.pack(reg_of(w11), copy11)); pk11 = table(copy11)
w12 = ws(register=WRONG, old={"7451": {"dod": LOSTD, "checked": iso(ago(60)), "src": "stedi-medicare-271"}}); before12 = asks(ws(register=WRONG), "7451", ago(1))      # the NEXT machine: its register still holds the day, the copy at the old path the placeholder
m12 = _try(lambda: DD.unpack(copy11, [reg_of(w12), old_of(w12)])); c12 = asks(w12, "7451", ago(1))
check("8b the Drive copy packed from that cache carries his word (the list 'off_record': the chart, the date of his word, the approval text - no day); merged on the NEXT machine it takes the day off the register and the placeholder off the other copy, and the guard there does not block the claim it blocked before the merge",
      lambda: isinstance(pk11, dict) and pk11.get("off_record") == {"7451": [iso(TODAY), word()]} and "7451" not in (pk11.get("dated") or {}) and leaks(json.dumps(pk11.get("off_record"))) == [] and m12 != "raised" and before12 == "blocked"
      and table(reg_of(w12))["7451"].get("off_record") == table(old_of(w12))["7451"].get("off_record") == iso(TODAY) and table(reg_of(w12))["7451"]["dod"] is None and table(reg_of(w12))["7451"].get("name") == "kept" and c12 == "clear",
      lambda: (n11, pk11, m12, before12, table(reg_of(w12)), table(old_of(w12)), c12))
F = _try(lambda: lift(IMPORT, "death_day", "death_unread", "death_read", "DEATH_NO_DAY"), {}); reads = F.get("death_read")
d13 = _try(lambda: reads([table(reg_of(w11)), {"7451": {"dod": iso(GONE), "checked": iso(ago(30))}}, {"7451": {"dod": LOSTD, "checked": iso(ago(60))}}]))
d14 = _try(lambda: reads([table(reg_of(w11)), {"7451": {"dod": iso(TODAY + datetime.timedelta(days=2)), "checked": iso(TODAY)}}]))
check("8c the feed's import reads that entry as 'no death' and lets no OTHER file's older day - nor its placeholder - stand against it: the chart's visits are entered; a day AFTER the date of his word in another file is a new death and keeps the later visits out",
      lambda: d13 != "raised" and "7451" not in d13[0] and "7451" not in d13[1] and d13[0]["7452"]["dod"] == iso(GONE) and d14 != "raised" and d14[0]["7451"]["dod"] == iso(TODAY + datetime.timedelta(days=2)) and d14[1] == set(), lambda: (d13, d14))      # (7452: the control chart of 8a - its day stands, nobody took it off)
w15 = ws(register={"7461": off_entry(ago(3))}); g15 = guard_at(w15); new15 = _try(lambda: g15.record("7461", {"dateOfDeath": ymd(ago(1))})); e15 = dict(table(reg_of(w15)).get("7461") or {})
check("8d ... and at the guard: a day AFTER the date of his word is a NEW death - it is taken as for any chart, his word is gone from the entry, and the claim after that day is blocked (his word never covers a death that comes later)",
      lambda: new15 == iso(ago(1)) and e15.get("dod") == iso(ago(1)) and "off_record" not in e15 and "approved_by" not in e15 and asks(w15, "7461", TODAY, g15) == "blocked", lambda: (new15, e15))

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
check("9a the helper keeps its PLAIN ENGLISH header: what it decides (nothing - the owner does), on whose word, what it writes, what it prints, the three exit codes, the usage, and what it never does",
      lambda: helper_text().startswith("#!/usr/bin/env python3\n# PLAIN ENGLISH (") and all(x in header(helper_text()) for x in ("Decides: NOTHING", "William", "ON WHOSE WORD", "WHAT IT WRITES", "WHAT IT PRINTS", "EXIT: 0 =", "3 =", "2 =", "--approved-by", "--dry", "Never", "TOP OF THE REPORT",
                                                                                                                                 "every day reported on or before", "a later day is a new death")), lambda: header(helper_text())[:500])
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
_off_only = [json.dumps({k: v for k, v in (json.loads(t) if t.strip().startswith("{") else {}).items() if isinstance(v, dict) and v.get("off_record")}, indent=1, sort_keys=True) for t in _written if _try(lambda t=t: json.loads(t), None) is not None and "off_record" in t]
check("9e the gate also leaves alone every line the helper printed, every row it kept and every OFF entry it wrote into a cache file (the date of his word and the approval text reach the repository as they were written: the entry still says what it means there)",
      lambda: len(SEEN) > 60 and len(_off_only) > 10 and [s[:120] for s in SEEN + _off_only if s and GATE.redact(s, {}, code=False) != s] == [],
      lambda: [[(a, b) for a, b in zip(s.splitlines(), GATE.redact(s, {}, code=False).splitlines()) if a != b][:1] for s in SEEN + _off_only if s and GATE.redact(s, {}, code=False) != s][:3])
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, lambda: sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_death_off_record: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
