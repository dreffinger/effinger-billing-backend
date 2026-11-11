#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/11/2026): census inputs - the category the Claimocity feed is one section of.
# Decides: nothing. William 11/11/2026: a practice can send its daily census in more than one way - the Claimocity feed (electronic, the
#   best one and the record), a screenshot of the Claimocity app's census list, a picture / scan / fax of a hospital census or an ortho
#   report, a daily census another practice sends in - and every one of them carries the same kind of information: date, patient name,
#   location, code, and whatever else is on the page. The other inputs support the feed and stand in for it when it is not available.
#   This test proves, on invented censuses only:
#     - scripts/helpers/census_inputs.py SAVES what a session read from a picture or PDF only when it is well formed (date, place,
#       source, rows with a name or an honest "could not read"), never guesses, never keeps a note or a reason for visit, and ties the
#       record to the exact file it was read from; the same file sent twice is read once;
#     - what it writes for GitHub (registers/census_inputs.json, registers/census_check_<date>.json) carries counts, chart ids and row
#       numbers - never a name or a date of birth; the names stay in the workspace files beside them;
#     - it COMPARES each census with the Claimocity feed of the same day and the same kind of place, and the feed is the record:
#       on both (same code / another code), on the census only, in the feed only; two censuses of one day are read as one list;
#       it says plainly when the feed's names are not on hand (then counts and code mix only), when the feed has nothing YET, and when
#       it has nothing after three days - then the census is the worklist, at the top of the report, and still no routine enters a visit;
#     - scripts/helpers/ringcentral_fax.py signs in the way RingCentral's guide describes, lists received faxes page by page, downloads
#       each PDF once, never changes anything in RingCentral, never prints a secret, and stops with a plain line when it has no key;
#     - the words of nightly/census_inputs_step.md are the code's, and census pictures cannot be committed.
# Never touches: AdvancedMD, RingCentral, Gmail, Drive, the workspace. Nothing is started as a program: both helpers are run INSIDE this
#   process, the fax helper with a stand-in for the network; every network route is closed first. Writes only to a temp directory.
# No patient data: every name, birth day, room and number here is invented and assembled at run time.
# Run: python3 tools/selftest/test_census_inputs.py   (exit 1 on any failure; the last line says how many checks ran)
import os, sys, re, io, json, types, atexit, shutil, tempfile, datetime, contextlib, hashlib, base64, importlib.util
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPERS = os.path.join(ROOT, "scripts", "helpers")
CENSUS = os.path.join(HELPERS, "census_inputs.py"); FAX = os.path.join(HELPERS, "ringcentral_fax.py")
TMP = tempfile.mkdtemp(prefix="selftest_census_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:700]))
    if not cond: FAILS.append(name)
def loads(src):
    out_ = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#;]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out_.add(n)
    return out_
AMD_MODULES = {"amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update", "add_ins"}
for _n in AMD_MODULES: sys.modules[_n] = types.ModuleType(_n)      # an empty stand-in each: a use would fail here, it never reaches the real one
def src_of(p): return open(p, encoding="utf-8").read() if os.path.exists(p) else ""
check("both helpers are there, load nothing that talks to AdvancedMD and nothing that starts a program",
      src_of(CENSUS) != "" and src_of(FAX) != "" and not (loads(src_of(CENSUS)) | loads(src_of(FAX))) & (AMD_MODULES | {"subprocess"}), (os.path.exists(CENSUS), os.path.exists(FAX), sorted((loads(src_of(CENSUS)) | loads(src_of(FAX))) & (AMD_MODULES | {"subprocess"}))))
if FAILS: print("\ntest_census_inputs: %d checks, %d failed - the helpers are not there, nothing else can be checked" % (RAN[0], len(FAILS))); sys.exit(1)
def run(path, ws, argv=(), env=None):
    """Run a helper written as a program INSIDE this process (never as a program of its own) -> (what it printed, exit code, error)"""
    old_cwd = os.getcwd(); old_argv = list(sys.argv); old_env = dict(os.environ); out = io.StringIO(); err = ""; code = 0
    try:
        os.environ.update(dict({"BILLING_WORKSPACE": ws}, **(env or {}))); os.chdir(ws); sys.argv = [path] + [str(a) for a in argv]
        with contextlib.redirect_stdout(out):
            try: exec(compile(src_of(path), path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit as e: code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1); out.write("" if isinstance(e.code, int) or e.code is None else str(e.code) + "\n")
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally:
        os.chdir(old_cwd); sys.argv = old_argv; os.environ.clear(); os.environ.update(old_env)
    return out.getvalue(), code, err
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
CI = load(CENSUS, "census_inputs_t")

# ------------------------------------------------------------------ invented people and one invented day
DAY = datetime.date(2026, 11, 8)
iso = lambda n=0: (DAY + datetime.timedelta(days=n)).isoformat()
ymd = lambda n=0: (DAY + datetime.timedelta(days=n)).strftime("%Y%m%d")
def person(n):
    """(family name, given name, birth day) of invented patient n"""
    return ("ZZ" + "CENSUS" + chr(65 + n % 26) + chr(66 + n % 24), "TESTER" + chr(65 + n % 26), (datetime.date(1935, 1, 1) + datetime.timedelta(days=53 * n)).isoformat())
def shown(n, style="app"): f, g, b = person(n); return (f + ", " + g.title() + " Q") if style == "app" else (f + "," + g + " Q (PREF)")
def workspace(name):
    ws = os.path.join(TMP, name); os.makedirs(os.path.join(ws, "registers")); os.makedirs(os.path.join(ws, "inbox", "census")); return ws
def picture(ws, name, body=b"invented picture bytes"):
    p = os.path.join(ws, "inbox", "census", name); open(p, "wb").write(body); return p
def record(rows, source="claimocity_app", place="hospital", date=None, **more):
    return dict({"schema": "census/1", "source": source, "practice": "ehpa", "date": date or iso(), "place": place, "facility": "Invented General Hospital", "rows": rows}, **more)
def row(n, k, code=None, style="app", **more):
    f, g, b = person(k)
    return dict({"n": n, "name": shown(k, style), "room": "T.%d" % (400 + k), "code": code}, **more)
def save(ws, rec, pic, *extra):
    rp = os.path.join(ws, "inbox", "census", "read_%d.json" % len(os.listdir(os.path.join(ws, "inbox", "census")))); json.dump(rec, open(rp, "w"))
    return run(CENSUS, ws, ("save", rp, "--file", pic) + extra)
reg = lambda ws: json.load(open(os.path.join(ws, "registers", "census_inputs.json"))) if os.path.exists(os.path.join(ws, "registers", "census_inputs.json")) else None
def private(text, *ks):
    """the family names and birth days of these invented patients that a text carries (a text for GitHub may carry none)"""
    blob = text if isinstance(text, str) else json.dumps(text)
    return [w for k in ks for w in (person(k)[0], person(k)[2], person(k)[2].replace("-", "")) if w in blob]

# ------------------------------------------------------------------ 1. the category and what a census record must be
check("1 the category is 'Census inputs' and the Claimocity feed is its first section - the record; every other way in is a section beside it",
      CI.CATEGORY == "Census inputs" and list(CI.SECTIONS)[0] == "claimocity_feed" and {"claimocity_app", "hospital_census", "ortho_fax", "practice_census"} <= set(CI.SECTIONS)
      and "record" in CI.SECTIONS["claimocity_feed"].lower(), list(CI.SECTIONS))
good = record([row(1, 1, "99233"), row(2, 2, "99232"), row(3, 3, None, unread=["code"])])
check("1 a well-formed record has no problem: date, place, source, facility, rows with a name (or an honest 'could not read')", CI.problems(good) == [], CI.problems(good))
BAD = {"another schema": dict(good, schema="census/9"), "a source nobody knows": dict(good, source="somewhere"), "the feed itself (it is never saved through this helper)": dict(good, source="claimocity_feed"),
       "no date": {k: v for k, v in good.items() if k != "date"}, "a date that is not a day": dict(good, date="2026-13-45"), "a date written another way": dict(good, date="11/08/2026"),
       "a place nobody knows": dict(good, place="somewhere"), "no rows": dict(good, rows=[]), "rows that are not a list": dict(good, rows="three"),
       "a row without a name that does not say the name could not be read": dict(good, rows=[dict(row(1, 1), name=None)]),
       "a code that is not a five-character code": dict(good, rows=[row(1, 1, "9923")]), "a birth day that is not a day": dict(good, rows=[dict(row(1, 1), dob="-".join(("1946", "21", "10")))]),
       "two rows with one number": dict(good, rows=[row(1, 1), row(1, 2)]), "a row that keeps a note (the reason for a visit, handwriting)": dict(good, rows=[dict(row(1, 1), reason="invented reason")]),
       "an 'unread' that names no field": dict(good, rows=[dict(row(1, 1), unread=["everything"])]), "a code AND 'the code could not be read'": dict(good, rows=[dict(row(1, 1, "99233"), unread=["code"])])}
check("1 a record that is not well formed is refused - sixteen ways, each named", all(CI.problems(v) != [] for v in BAD.values()), [k for k, v in BAD.items() if CI.problems(v) == []])
check("1 a name the page did not show is said, never made up: a row may have no name only when it says the name could not be read", CI.problems(dict(good, rows=[dict(row(1, 1), name=None, unread=["name"])])) == [])

# ------------------------------------------------------------------ 2. saving: tied to the file, once, and nothing private in the register
ws = workspace("save"); pic = picture(ws, "app list.png")
out, code, err = save(ws, good, pic, "--drive-id", "DRIVEID0001"); r = reg(ws); sha = hashlib.sha256(b"invented picture bytes").hexdigest()
saved = os.path.join(ws, "census", iso(), "claimocity_app_%s.json" % sha[:8])
check("2 save: the record goes into the workspace under its day, named by its source and its file; one line says what was saved",
      err == "" and code == 0 and os.path.exists(saved) and json.load(open(saved))["rows"][0]["name"] == shown(1) and re.search(r"census saved: claimocity_app %s hospital - 3 row\(s\) \(2 with a code, 0 with a birth date, 1 cell\(s\) could not be read\)" % iso(), out), (err, code, out))
check("2 save: the register for GitHub ties the record to the file (sha256, Drive id) and counts - source, day, place, rows, codes, unread cells",
      r is not None and r.get("schema") == "census-inputs/1" and sha in r["files"] and {k: r["files"][sha].get(k) for k in ("source", "date", "place", "rows", "with_code", "with_dob", "unread", "drive_ids")}
      == {"source": "claimocity_app", "date": iso(), "place": "hospital", "rows": 3, "with_code": 2, "with_dob": 0, "unread": 1, "drive_ids": ["DRIVEID0001"]}, r)
check("2 save: ... and carries no name, no birth day, no room and no file name", r is not None and private(r, 1, 2, 3) == [] and "T.40" not in json.dumps(r) and "app list" not in json.dumps(r), json.dumps(r)[:300])
out2, code2, err2 = save(ws, good, picture(ws, "the same list again.png"), "--drive-id", "DRIVEID0002"); r2 = reg(ws)
check("2 save: the same file sent in twice (another name, another Drive id) is read once - the second is noted as the same content",
      err2 == "" and code2 == 0 and "already saved" in out2 and len(r2["files"]) == 1 and r2["files"][sha]["drive_ids"] == ["DRIVEID0001", "DRIVEID0002"] and len(os.listdir(os.path.join(ws, "census", iso()))) == 1, (out2, r2))
out3, code3, err3 = save(ws, dict(good, rows=good["rows"][:2]), pic)
check("2 save: another reading of a file already saved is refused unless --replace is given (then it takes the place of the first)", code3 == 2 and "--replace" in out3 and len(json.load(open(saved))["rows"]) == 3
      and save(ws, dict(good, rows=good["rows"][:2]), pic, "--replace")[1] == 0 and len(json.load(open(saved))["rows"]) == 2 and reg(ws)["files"][sha]["rows"] == 2, (code3, out3))
out4, code4, err4 = save(ws, BAD["a code that is not a five-character code"], picture(ws, "other.png", b"other bytes"))
check("2 save: a record with a problem is not saved - exit 2, the problem in words, nothing written", code4 == 2 and "NOT SAVED" in out4 and "code" in out4 and len(reg(ws)["files"]) == 1, (code4, out4))
out5, code5, err5 = run(CENSUS, ws, ("status",))
check("2 status: one line per file read (file, source, day, place, rows, its Drive ids) so a run can tell which uploads are new - no name in it",
      err5 == "" and code5 == 0 and sha[:8] in out5 and "DRIVEID0001" in out5 and "DRIVEID0002" in out5 and "claimocity_app" in out5 and private(out5, 1, 2, 3) == [], out5)
out6, code6, err6 = run(CENSUS, ws, ("save", os.path.join(ws, "nowhere.json"), "--file", pic))
check("2 save: a record or a file that is not there is said in one line (exit 2), never a stop with a trace", err6 == "" and code6 == 2 and "NOT SAVED" in out6, (err6, code6, out6))

# ------------------------------------------------------------------ 3. the comparison: the feed is the record
def feed(ws, stamp, visits, with_names=True, with_recon=True):
    """an invented feed batch in the workspace: visits = [(patient number, day offset, [codes], outcome)]"""
    if with_names:
        json.dump([{"file": ymd(1), "pid": "FEEDC%03d" % k, "name": person(k)[0] + ", " + person(k)[1], "dob": person(k)[2].replace("-", ""), "provider": "", "admit": "",
                    "FT1": [{"dos": ymd(d) + "1200", "posted": ymd(d + 1), "units": "1", "dx": "I10", "cpt": c} for c in codes], "IN1": [], "DG1": []} for k, d, codes, s in visits],
                  open(os.path.join(ws, "feed_parsed_%s.json" % stamp), "w"))
    if with_recon:
        json.dump({"schema": "feed-recon/1", "stamp": stamp, "rows": [{"f": "FEEDC%03d" % k, "d": iso(d), "c": codes, "s": s, "p": "pat%d" % (9400000 + k), "fac": "fac29"} for k, d, codes, s in visits]},
                  open(os.path.join(ws, "registers", "feed_recon_%s.json" % stamp), "w"))
def compare(ws, *argv, today=None):
    out, code, err = run(CENSUS, ws, ("compare",) + argv, env={"CENSUS_TODAY": today or iso(5)})
    cf = os.path.join(ws, "registers", "census_check_%s.json" % iso()); md = os.path.join(ws, "census", iso(), "census_check_%s.md" % iso())
    return out, code, err, (json.load(open(cf)) if os.path.exists(cf) else None), (open(md).read() if os.path.exists(md) else "")
ws = workspace("compare")
# the app list: patients 1-5 (5 has no code on the page); the faxed hospital census of the same day: 2-6 with birth days, no codes
save(ws, record([row(1, 1, "99233"), row(2, 2, "99232"), row(3, 3, "99233"), row(4, 4, "99223", more_codes=1), row(5, 5, None, unread=["code"])]), picture(ws, "a.png", b"app"))
save(ws, record([dict(row(i, k, None, "fax"), dob=person(k)[2], mrn="R00%d" % k, admit=iso(-3)) for i, k in enumerate((2, 3, 4, 5, 6), 1)], source="hospital_census"), picture(ws, "b.pdf", b"fax"))
# the feed of that day: 1 as on the list, 2 with ANOTHER code, 3 and 4 as listed (4 with its second code), 7 on no census; 8 is a nursing visit and 9 care management - neither belongs to a hospital census
feed(ws, "20261109T0040Z", [(1, 0, ["99233"], "entered"), (2, 0, ["99233"], "entered"), (3, 0, ["99233"], "already"), (4, 0, ["99223", "99497"], "entered"), (7, 0, ["99232"], "entered"),
                           (8, 0, ["99309"], "entered"), (9, 0, ["99487"], "entered"), (1, -1, ["99232"], "entered")])
out, code, err, chk, md = compare(ws, "--date", iso())
H = (chk or {}).get("places", {}).get("hospital", {})
check("3 compare: two censuses of one day are read as ONE list (six patients), against the feed's hospital visits of that day (five) - a nursing visit, care management and another day's visit are not this census's business",
      err == "" and code == 0 and H.get("census_rows") == 6 and H.get("census_files") == 2 and H.get("feed_visits") == 5 and H.get("names_compared") is True and H.get("feed_state") == "present", (err, code, out, H))
check("3 compare: on both = four; one of them with ANOTHER code in the feed - listed with both codes, and the feed's code stands (the feed is the record)",
      H.get("both") == 4 and H.get("code_differs") == [{"chart": "pat9400002", "feed": "FEEDC002", "census_code": "99232", "feed_codes": ["99233"], "stands": "feed"}], H.get("code_differs"))
check("3 compare: on the census only = two (one on both censuses, one on the fax alone) - named by file and row for GitHub; in the feed only = one, by chart",
      sorted((x["file"], x["n"]) for x in H.get("census_only") or []) == sorted([(hashlib.sha256(b"app").hexdigest()[:8], 5), (hashlib.sha256(b"fax").hexdigest()[:8], 5)]) and len(H.get("census_only")) == 2
      and H.get("feed_only") == [{"chart": "pat9400007", "feed": "FEEDC007", "codes": ["99232"]}], (H.get("census_only"), H.get("feed_only")))
check("3 compare: one line for the report says it all, and the register for GitHub carries no name and no birth day",
      re.search(r"census check %s hospital: census 6 patient\(s\) from 2 file\(s\) \| feed 5 visit\(s\) \| on both 4 \(code differs 1\) \| census only 2 \| feed only 1" % iso(), out) is not None
      and private(chk, 1, 2, 3, 4, 5, 6, 7) == [] and private(out, 1, 2, 3, 4, 5, 6, 7) == [], (out, private(chk, 1, 2, 3, 4, 5, 6, 7)))
check("3 compare: the names are in the workspace file for William beside the censuses - who is on the census only, who in the feed only, whose code differs",
      all(person(k)[0] in md for k in (2, 5, 6, 7)) and "feed is the record" in md.lower() and "99232" in md and "99233" in md, md[:400])
check("3 compare: three days on, patients on a census with no visit in a feed that DID bring that day's visits go to the top of the report - possible missed charges, for William; no routine enters a visit",
      any(l.startswith("  - TOP OF THE REPORT - ON THE CENSUS, NOT IN THE FEED: 2 patient(s) on %s (hospital)" % iso()) and "no routine enters a visit from a census" in l for l in out.split("\n")), out)
out_e, code_e, err_e, chk_e, md_e = compare(ws, "--date", iso(), today=iso(1))
check("3 compare: the day after, the same two are counted but not yet at the top (the feed brings charges a day or two after the visit)",
      err_e == "" and "census only 2" in out_e and "TOP OF THE REPORT" not in out_e and chk_e["places"]["hospital"]["feed_state"] == "present", out_e)
# a birth day that differs between the census and the feed: matched by name, and said
ws = workspace("dob"); save(ws, record([dict(row(1, 1, "99233"), dob=person(2)[2])]), picture(ws, "a.png", b"dob"))
feed(ws, "20261109T0040Z", [(1, 0, ["99233"], "entered")]); out, code, err, chk, md = compare(ws, "--date", iso())
check("3 compare: same name, another birth day on the census than in the feed - still one patient, counted under 'birth date differs' and named for William (a wrong chart is worse than a question)",
      err == "" and chk["places"]["hospital"]["both"] == 1 and chk["places"]["hospital"]["dob_differs"] == 1 and "birth date differs" in md and private(chk, 1, 2) == [], (err, chk and chk["places"]["hospital"]))

# ------------------------------------------------------------------ 4. what the feed side can and cannot say
ws = workspace("no_names"); save(ws, record([row(1, 1, "99233"), row(2, 2, "99232")]), picture(ws, "a.png", b"nn"))
feed(ws, "20261109T0040Z", [(1, 0, ["99233"], "entered"), (3, 0, ["99232"], "entered")], with_names=False); out, code, err, chk, md = compare(ws, "--date", iso())
N = (chk or {}).get("places", {}).get("hospital", {})
check("4 the feed's names are not on hand (a fresh machine has the registers, not the parsed files): counts and code mix only - 2 against 2, each code - and it says so; nobody is called missing on a count",
      err == "" and code == 0 and N.get("names_compared") is False and N.get("census_rows") == 2 and N.get("feed_visits") == 2 and N.get("census_codes") == {"99232": 1, "99233": 1} and N.get("feed_codes") == {"99232": 1, "99233": 1}
      and N.get("census_only") == [] and N.get("feed_only") == [] and "names not on hand" in out and "TOP OF THE REPORT" not in out, (err, out, N))
ws = workspace("no_feed"); save(ws, record([row(1, 1, "99233"), row(2, 2, "99232"), row(3, 3, None, unread=["code"])]), picture(ws, "a.png", b"nf"))
feed(ws, "20261107T0040Z", [(4, -2, ["99232"], "entered")])      # the feed is alive, but has nothing for this day
out1, c1, e1, chk1, md1 = compare(ws, "--date", iso(), today=iso(1)); out3, c3, e3, chk3, md3 = compare(ws, "--date", iso(), today=iso(3))
check("4 the feed has nothing for the day YET (the day after): said plainly, compared again at the next run, nothing at the top",
      e1 == "" and chk1["places"]["hospital"]["feed_state"] == "nothing yet" and "nothing yet" in out1 and "TOP OF THE REPORT" not in out1, out1)
check("4 ... and still nothing three days on: the census is the worklist - ONE line at the top of the report with the count; the names are in the workspace file; no routine enters a visit from a census",
      e3 == "" and chk3["places"]["hospital"]["feed_state"] == "not available" and [l for l in out3.split("\n") if l.startswith("  - TOP OF THE REPORT - CENSUS WITHOUT A FEED: %s (hospital)" % iso())] != []
      and "3 patient(s)" in out3 and "no routine enters a visit from a census" in out3 and all(person(k)[0] in md3 for k in (1, 2, 3)) and private(out3, 1, 2, 3) == [] and private(chk3, 1, 2, 3) == [], out3)
ws = workspace("no_registers"); save(ws, record([row(1, 1, "99233")]), picture(ws, "a.png", b"nr")); out, code, err, chk, md = compare(ws, "--date", iso())
check("4 a workspace with no feed file at all (neither registers nor parsed files): 'not known' - never called 'not available', nothing at the top",
      err == "" and chk["places"]["hospital"]["feed_state"] == "not known" and "not on hand" in out and "TOP OF THE REPORT" not in out, out)
src = src_of(CENSUS)
check("4 the helper writes nothing in AdvancedMD and knows no way to: it loads the standard library only", loads(src) <= {"os", "sys", "re", "json", "glob", "hashlib", "datetime", "collections"}, loads(src))
out, code, err = run(CENSUS, ws, ("compare", "--recent", "7"), env={"CENSUS_TODAY": iso(3)})
check("4 compare --recent 7 checks every census day of the last week again (the feed arrives late), one line each", err == "" and code == 0 and out.count("census check ") == 1 and iso() in out, (err, out))
out, code, err = run(CENSUS, workspace("empty"), ("compare", "--recent", "7"))
check("4 with no census saved the comparison is one quiet line", err == "" and code == 0 and "no census" in out, (err, out))

# ------------------------------------------------------------------ 5. faxes from RingCentral (the API route William chose 11/11/2026)
RF = load(FAX, "ringcentral_fax_t")
class Net:
    """a stand-in for RingCentral: answers the sign-in, the list of received faxes (two pages) and each fax's PDF; notes every request"""
    def __init__(self, faxes, token_status=200): self.calls = []; self.faxes = faxes; self.token_status = token_status
    def __call__(self, method, url, headers=None, body=None):
        self.calls.append((method, url, dict(headers or {}), body))
        if url.endswith("/restapi/oauth/token"):
            return (self.token_status, {}, json.dumps({"access_token": "TOKEN-INVENTED", "expires_in": 3600} if self.token_status == 200 else {"error": "invalid_grant", "error_description": "invented"}).encode())
        if "/message-store?" in url or url.endswith("/message-store"):
            page = int(re.search(r"[?&]page=(\d+)", url).group(1)) if re.search(r"[?&]page=(\d+)", url) else 1
            part = self.faxes[(page - 1) * 2:page * 2]
            recs = [{"id": i, "type": "Fax", "direction": "Inbound", "creationTime": t, "faxPageCount": n, "from": {"phoneNumber": "+15550100%02d" % (i % 100)},
                     "attachments": [{"id": i * 10, "uri": "https://media.ringcentral.com/restapi/v1.0/account/1/extension/2/message-store/%d/content/%d" % (i, i * 10), "type": "RenderedDocument", "contentType": "application/pdf"}]} for i, t, n in part]
            nav = {"nextPage": {"uri": "x"}} if page * 2 < len(self.faxes) else {}
            return 200, {}, json.dumps({"records": recs, "navigation": nav}).encode()
        m = re.search(r"/message-store/(\d+)/content/", url)
        if m: return 200, {"Content-Type": "application/pdf"}, b"%PDF-invented fax " + m.group(1).encode()
        return 404, {}, b"{}"
KEYS = {"RINGCENTRAL_CLIENT_ID": "CLIENT-INVENTED", "RINGCENTRAL_CLIENT_SECRET": "SECRET-INVENTED", "RINGCENTRAL_JWT": "JWT-INVENTED"}
FAXES = [(9001, "2026-11-07T20:42:11.000Z", 2), (9002, "2026-11-08T13:05:00.000Z", 1), (9003, "2026-11-08T21:15:30.000Z", 3)]
def fax_run(ws, argv, net, env=None):
    old = dict(os.environ); out = io.StringIO()
    try:
        for k in KEYS: os.environ.pop(k, None)
        os.environ.update(dict({"BILLING_WORKSPACE": ws}, **(KEYS if env is None else env)))
        with contextlib.redirect_stdout(out):
            code = RF.main(list(argv), http=net, sleep=lambda s: None)
    finally: os.environ.clear(); os.environ.update(old)
    return out.getvalue(), code
ws = workspace("fax"); net = Net(FAXES); out, code = fax_run(ws, ["--fetch", "--since", "2026-11-01"], net)
tok = [c for c in net.calls if c[1].endswith("/restapi/oauth/token")]
check("5 sign-in as RingCentral's guide says: ONE call to platform.ringcentral.com/restapi/oauth/token, the app's id and secret as Basic, the JWT as the assertion of a jwt-bearer grant",
      len(tok) == 1 and tok[0][0] == "POST" and tok[0][1] == "https://platform.ringcentral.com/restapi/oauth/token" and tok[0][2].get("Authorization") == "Basic " + base64.b64encode(b"CLIENT-INVENTED:SECRET-INVENTED").decode()
      and b"grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer" in tok[0][3] and b"assertion=JWT-INVENTED" in tok[0][3], tok and (tok[0][1], tok[0][3]))
lst = [c for c in net.calls if "/message-store?" in c[1]]
check("5 the list asks for RECEIVED FAXES only, from the day given, page by page until there is no next page - with the token, never the secret",
      len(lst) == 2 and all("messageType=Fax" in c[1] and "direction=Inbound" in c[1] and "dateFrom=2026-11-01" in c[1] and c[2].get("Authorization") == "Bearer TOKEN-INVENTED" for c in lst), [c[1] for c in lst])
saved = sorted(os.listdir(os.path.join(ws, "inbox", "faxes"))) if os.path.isdir(os.path.join(ws, "inbox", "faxes")) else []
fr = json.load(open(os.path.join(ws, "registers", "ringcentral_faxes.json"))) if os.path.exists(os.path.join(ws, "registers", "ringcentral_faxes.json")) else {}
check("5 every fax's PDF is saved once in the workspace's fax inbox, named by its day, time and message id; the register for GitHub has id, time received, pages, sha256 and size - no telephone number",
      code == 0 and saved == ["20261107_2042_9001.pdf", "20261108_1305_9002.pdf", "20261108_2115_9003.pdf"] and sorted(fr.get("faxes", {})) == ["9001", "9002", "9003"]
      and fr["faxes"]["9001"] == {"received": "2026-11-07T20:42:11.000Z", "pages": 2, "sha256": hashlib.sha256(b"%PDF-invented fax 9001").hexdigest(), "size": len(b"%PDF-invented fax 9001"), "file": "20261107_2042_9001.pdf"}
      and "555" not in json.dumps(fr) and "3 new fax(es)" in out, (code, saved, out, fr))
check("5 the helper works in the workspace it is given at each start (a workspace named when the file was loaded is not remembered)", RF.WS == ws and os.path.isdir(os.path.join(ws, "inbox", "faxes")), RF.WS)
check("5 nothing is ever changed in RingCentral: one POST (the sign-in), every other request a GET - no delete, no 'mark as read'", sorted({c[0] for c in net.calls}) == ["GET", "POST"] and sum(1 for c in net.calls if c[0] == "POST") == 1)
check("5 no secret is printed or written: not the app's secret, not the JWT, not the token", not any(s in out or s in json.dumps(fr) for s in ("SECRET-INVENTED", "JWT-INVENTED", "TOKEN-INVENTED")), out)
net2 = Net(FAXES + [(9004, "2026-11-09T12:00:00.000Z", 1)]); out2, code2 = fax_run(ws, ["--fetch", "--since", "2026-11-01"], net2)
check("5 a second run downloads only what is new (the three it has are not fetched again)", code2 == 0 and [m.group(1) for c in net2.calls for m in [re.search(r"/message-store/(\d+)/content/", c[1])] if m] == ["9004"] and "1 new fax(es)" in out2, out2)
net3 = Net(FAXES); out3, code3 = fax_run(workspace("fax_list"), ["--list", "--since", "2026-11-01"], net3)
check("5 --list shows what is there (id, time, pages) and downloads nothing", code3 == 0 and "9001" in out3 and "3 received fax(es)" in out3 and not any("/content/" in c[1] for c in net3.calls), out3)
net4 = Net(FAXES); out4, code4 = fax_run(workspace("fax_nokey"), ["--fetch"], net4, env={})
check("5 with no key the helper stops with one plain line (exit 4) and makes no request at all", code4 == 4 and net4.calls == [] and "no RingCentral key" in out4, (code4, out4))
net5 = Net(FAXES, token_status=400); out5, code5 = fax_run(workspace("fax_refused"), ["--fetch"], net5)
check("5 a refused sign-in is reported with RingCentral's own error word (exit 5), nothing is listed or downloaded, no secret in the line", code5 == 5 and "invalid_grant" in out5 and len(net5.calls) == 1 and "SECRET-INVENTED" not in out5 and "JWT-INVENTED" not in out5, (code5, out5))
check("5 the fax helper loads the standard library only", loads(src_of(FAX)) <= {"os", "sys", "re", "json", "time", "base64", "hashlib", "datetime", "urllib"}, loads(src_of(FAX)))

# ------------------------------------------------------------------ 6. the words, and census pictures never in a commit
STEP = src_of(os.path.join(ROOT, "nightly", "census_inputs_step.md")); STEPN = STEP.replace("\n", " ")
check("6 runbook: the category and its sections are the code's, the Claimocity feed first and called the record; the folder is named; the commands are the helpers' own",
      STEP != "" and "Census inputs" in STEPN and all(v.split(" (")[0] in STEPN for v in CI.SECTIONS.values()) and "aa census imports files" in STEPN and "python3 census_inputs.py save" in STEPN
      and "python3 census_inputs.py compare --recent 7" in STEPN and "python3 census_inputs.py status" in STEPN and "python3 ringcentral_fax.py --fetch" in STEPN, [v for v in CI.SECTIONS.values() if v.split(" (")[0] not in STEPN])
check("6 runbook: what a routine never does - enter a visit from a census, guess a cell, keep a note, send a census picture anywhere but Drive and the workspace - and what the top-of-report lines mean",
      all(w in STEPN for w in ("no routine enters a visit from a census", "never guessed", "CENSUS WITHOUT A FEED", "ON THE CENSUS, NOT IN THE FEED", "the feed is the record", "python3 tools/selftest/test_census_inputs.py")),
      [w for w in ("no routine enters a visit from a census", "never guessed", "CENSUS WITHOUT A FEED", "ON THE CENSUS, NOT IN THE FEED", "the feed is the record") if w not in STEPN])
check("6 runbook: every field name it gives a session to write is one the helper accepts, and every source and place too",
      all(("`%s`" % f) in STEP for f in CI.FIELDS) and all(("`%s`" % s) in STEP for s in CI.SECTIONS if s != "claimocity_feed") and all(("`%s`" % p) in STEP for p in CI.PLACES), [f for f in CI.FIELDS if ("`%s`" % f) not in STEP])
GI = src_of(os.path.join(ROOT, ".gitignore")).split("\n")
check("6 a census picture, scan or fax cannot be committed from the folders run files are copied into (the privacy gate reads text files only)",
      all(("practices/**/*.%s" % e) in GI for e in ("pdf", "png", "jpg", "jpeg", "heic", "tif", "tiff")) and "census/" in GI and "inbox/" in GI, [l for l in GI if "practices/**" in l])
PJ = json.load(open(os.path.join(ROOT, "practices", "ehpa", "practice.json")))
check("6 the practice file names the folder the censuses are uploaded to and the ways in", PJ.get("drive", {}).get("census_inbox") == "1FCZQpMV9hE5UHJ-VdV_n-sVgOMJMIGsa" and "census_inputs" in PJ.get("input_channels", {}), list(PJ.get("drive", {})))
_me = src_of(os.path.abspath(__file__))
check("6 this self-test starts nothing as a program", re.findall(r"^[ \t]*(?:import|from)[ \t]+" + "subprocess" + r"\b|" + "os" + r"\.(?:system|popen|exec\w*|spawn\w*|fork)\(|" + "runpy" + r"\.", _me, re.M) == [])
os.chdir(ROOT)
print("\ntest_census_inputs: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1500]))
sys.exit(1 if FAILS else 0)
