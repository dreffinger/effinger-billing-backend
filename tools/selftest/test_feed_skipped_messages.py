#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/11/2026): a feed message that cannot be read never stops a feed batch.
# Decides: nothing. Three malformed DFT messages each stopped a whole batch until 11/11/2026 (found with invented messages - none
#   had been seen in a real feed file):
#     1  a message with NO PV1 segment         - the parser ended with KeyError 'provider' and wrote no parsed file: nothing was entered;
#     2  an FT1 line with fewer than 20 fields - the parser ended with IndexError: nothing was entered;
#     3  a message with NO FT1 line            - it passed the parser and stopped the import at that message: the visits before it
#        were entered, the ones after it were not, and every re-run stopped at the same message.
#   For each of the three this test writes a batch of invented messages as an HL7 file - the bad message between good ones - and runs
#   the REAL scripts/helpers/feed_parse_dft_1028.py, a fresh copy of scripts/helpers/claimocity_import.py and the digest
#   scripts/helpers/claimocity_report.py over it. It proves:
#     - the batch's other visits are entered (every one of them, once) and nothing of the bad message is;
#     - the bad message is named - by its message control id and the reason - in the parser's list of skipped messages
#       (feed_skipped_<stamp>.json, cases 1 and 2), in the import register under "skipped_messages" (all three) and in ONE digest line
#       that starts "  - TOP OF THE REPORT - " and says how many, which control ids, and that a person must look at the feed file;
#     - none of those places carries the patient's name, date of birth or member id;
#     - a re-run of the same batch enters nothing twice and still names the message once;
#   and besides: the three in ONE batch (with a message that has no PID segment, one whose MSH line carries no control id and one whose
#   only charge line is two fields long), a message with one good and one short charge line is skipped whole, a batch with nothing
#   wrong gets no line and no register key, a dry run writes nothing, a readable message is still read exactly as before, the same
#   batch seen again under a later stamp enters nothing, and the retry of visits that waited on a diagnosis code is not stopped by a
#   message with no FT1 line either. The words the runbook gives the routine are tied to the code's.
# Never touches: AMD, Gmail, Drive, the workspace. NOTHING IS STARTED AS A PROGRAM: scripts/helpers holds the real amd / resave / txh /
#   void_tx modules, and a helper started as a program from that folder loads them (docs/SHARED_LESSONS.md, 2026-11-10T1030Z). The
#   parser, the importer, the digest and the retry driver are run INSIDE this process - the importer with stand-in amd / resave / txh
#   modules, the retry driver with a stand-in for the programs it would start - and every network route is closed first. Writes only
#   to a temp directory, removed at the end.
# No patient data: every patient id, name, date of birth, member id and chart number is invented and assembled at run time. The
#   buildings and the clinician ids are read from the importer's own FAC / PROFILE tables at run time, so none is written here.
# Run: python3 tools/selftest/test_feed_skipped_messages.py   (exit 1 on any failure; the last line says how many checks ran)
import os, sys, re, io, json, types, atexit, shutil, tempfile, datetime, contextlib, importlib.util
import xml.etree.ElementTree as ET
# THIS SELF-TEST NEVER REACHES ADVANCEDMD OR ANY OTHER HOST: every network route is closed before anything else is loaded.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
sys.dont_write_bytecode = True                                        # nothing is written into the checkout, not even a cache
AMD_MODULES = ("amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPERS = os.path.join(ROOT, "scripts", "helpers")
PARSER = os.path.join(HELPERS, "feed_parse_dft_1028.py"); IMPORT = os.path.join(HELPERS, "claimocity_import.py")
REPORT = os.path.join(HELPERS, "claimocity_report.py"); RETRY = os.path.join(HELPERS, "claimocity_retry_dx.py")
TMP = tempfile.mkdtemp(prefix="selftest_feed_skipped_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
STAMP = "20261111T0000Z"; LATER = "20261112T0000Z"; MSGTIME = "11/11/2026 1:00:00 AM"
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:600]))
    if not cond: FAILS.append(name)

# ------------------------------------------------------------------ stand-ins: no real amd / resave / txh / void_tx, no socket
# whatever the calling shell exports, none of the importer's switches or caches decides what these invented charts get
for _name in set(re.findall(r'environ(?:\.get\(|\[)\s*"([A-Za-z_][A-Za-z0-9_]*)"', open(IMPORT, encoding="utf-8").read())): os.environ.pop(_name, None)
SENT = []; N = {"visit": 0, "charge": 0}
def _msg(action, cls, attrs=None, children=""):
    return '<ppmdmsg action="%s" class="%s" msgtime="%s" %s>%s</ppmdmsg>' % (action, cls, MSGTIME, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
def _post(body, timeout=None):
    SENT.append(body); act = re.search(r'action="(\w+)"', body).group(1)
    if act == "getdemographic":                      # one open plan that is not Medicare: no reporting line is ever added to these visits
        pid = re.search(r'patientid="([^"]*)"', body).group(1)
        return ('<PPMDResults><Results><patient id="%s" respparty="resp%s" insorder="1" deceased=""/>'
                '<insplan id="ins1" carrier="car1" begindate="01/01/2020" enddate="" sequence="1"/></Results></PPMDResults>') % (pid, re.sub(r"\D", "", pid))
    if act == "addvisit":
        N["visit"] += 1; return '<PPMDResults><Results success="1"><visit id="vst%d"/></Results></PPMDResults>' % (7000 + N["visit"])
    if act == "updvisitwithnewcharges":              # AMD's answer echoes each charge with the place of service it stored
        out = ""
        for pos, fee in re.findall(r'<charge id="" [^>]*? pos="(\d*)"[^>]*? fee="([^"]*)"', body):
            N["charge"] += 1; out += '<charge id="charge%d" pos="%s" fee="%s"/>' % (50000 + N["charge"], pos, fee)
        return '<PPMDResults><Results success="1"><visit id="%s"><chargelist>%s</chargelist></visit></Results></PPMDResults>' % (re.search(r'<visit id="(vst\d+)"', body).group(1), out)
    if act == "updextrainsinfo":
        return '<PPMDResults><Results success="1"><extins %s/></Results></PPMDResults>' % re.search(r'hospitalizationfrom="[^"]*"', body).group(0)
    raise AssertionError("request the import never sends: " + act)
amd = types.ModuleType("amd"); amd.post = _post; amd.msg = _msg; amd._msgtime = lambda: MSGTIME; amd.login_cached = lambda psw=None: None
txh = types.ModuleType("txh"); txh.fetch = lambda num: ET.Element("PPMDResults")          # every invented chart starts empty: only the registers can stop a second entry
resave = types.ModuleType("resave"); resave.detail = lambda c: "<PPMDResults/>"
STAND = {"amd": amd, "txh": txh, "resave": resave}
for _n in AMD_MODULES: STAND.setdefault(_n, types.ModuleType(_n))     # an empty stand-in for every other module that talks to AdvancedMD: a use fails here, it never reaches the real one
for _n, _m in STAND.items(): _m.STAND_IN = True
sys.modules.update(STAND)
_live = [p for p in sys.path if os.path.abspath(p or ".") in (HELPERS, os.path.join(ROOT, "core"))]
check("the folders that hold the real amd / resave / txh / void_tx are not on this process's module path", not _live, _live)
def loads(src):
    """The names a piece of Python loads with import / from, first name of each (import a.b as c -> a)."""
    out_ = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#;]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out_.add(n)
    return out_
PLAIN = {"os", "sys", "re", "json", "glob", "collections", "datetime"}                    # standard library only
check("the parser and the digest load the standard library only - nothing that talks to AdvancedMD, nothing that starts a program",
      loads(open(PARSER).read()) <= PLAIN and loads(open(REPORT).read()) <= PLAIN, (loads(open(PARSER).read()) - PLAIN, loads(open(REPORT).read()) - PLAIN))
check("the importer loads amd, resave and txh - each a stand-in here - and no other module that talks to AdvancedMD",
      loads(open(IMPORT).read()) & set(AMD_MODULES) == {"amd", "resave", "txh"}, loads(open(IMPORT).read()) & set(AMD_MODULES))
def run_script(path, cwd, argv=(), extra=None):
    """Run a helper that is written as a program INSIDE this process (never as a program of its own): its source is executed here with
    this process's stand-in modules, its own folder is NOT put on the module path. extra = further stand-in modules for this run.
    Refuses a helper that loads a module which talks to AdvancedMD, or the program starter, without a stand-in. -> (what it printed, error)"""
    src = open(path, encoding="utf-8").read(); want = loads(src)
    bad = sorted(n for n in want & (set(AMD_MODULES) | {"subprocess"}) if not getattr(dict(STAND, **(extra or {})).get(n), "STAND_IN", False))
    if bad: raise RuntimeError("no stand-in for %s - the helper is not run" % bad)
    old_mod = {k: sys.modules.get(k) for k in (extra or {})}; old_cwd = os.getcwd(); old_argv = list(sys.argv); out = io.StringIO(); err = ""
    try:
        sys.modules.update(extra or {}); os.chdir(cwd); sys.argv = [path] + list(argv)
        with contextlib.redirect_stdout(out):
            try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit: pass
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally:
        os.chdir(old_cwd); sys.argv = old_argv
        for k, v in old_mod.items():
            if v is None: sys.modules.pop(k, None)
            else: sys.modules[k] = v
    return out.getvalue(), err

# ------------------------------------------------------------------ the importer, loaded fresh per run from its file
DX = {"I10": "dcode101"}                                              # ICD-10 -> AMD id for the invented messages
LOADS = [0]
def workspace(name):
    ws = os.path.join(TMP, name); os.makedirs(os.path.join(ws, "hl7")); os.makedirs(os.path.join(ws, "registers"))
    json.dump(DX, open(os.path.join(ws, "dx_cache_feed.json"), "w")); json.dump({}, open(os.path.join(ws, "deceased_cache_selftest.json"), "w")); return ws
def load(ws, stamp=STAMP):
    os.chdir(ws); LOADS[0] += 1
    os.environ.update(FEED_STAMP=stamp, FEED_HL7_DIR=os.path.join(ws, "hl7"), FEED_DX_CACHE="dx_cache_feed.json", DECEASED_CACHE=os.path.join(ws, "deceased_cache_selftest.json"))
    spec = importlib.util.spec_from_file_location("claimocity_import_skipped_%d" % LOADS[0], IMPORT); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.time = types.SimpleNamespace(sleep=lambda *_a: None)          # the pause between visits is not under test
    return mod
ws0 = workspace("tables")
for f, v in (("feed_parsed_%s.json" % STAMP, []), ("feed_match_%s.json" % STAMP, {})): json.dump(v, open(os.path.join(ws0, f), "w"))
T = load(ws0)                                                         # the buildings and the clinician ids, from the importer's own tables
check("the stand-ins are what the importer imported (never the real AMD helper)", T.amd is amd and T.txh is txh and T.resave is resave)
HOSP = [b for b, (f, p) in T.FAC.items() if p == "21"]; NURS = [b for b, (f, p) in T.FAC.items() if p == "31"]; CLIN = list(T.PROFILE.items())
CODES = ("99232", "99308", "99309")                                   # every code the good messages carry
check("tables: a hospital at 21, two nursing buildings at 31, two clinician profiles, every code of these messages known",
      HOSP and len(NURS) >= 2 and len(CLIN) >= 2 and all(c in T.PCODE and c in T.FEE for c in CODES), (len(HOSP), len(NURS), len(CLIN)))
if FAILS: print("\n%d failure(s): %s - the batches below cannot be built without these tables" % (len(FAILS), "; ".join(FAILS))); sys.exit(1)
HOSPITAL = HOSP[0]; (NPI_A, PROF_A), (NPI_B, PROF_B) = CLIN[:2]
CPT_OF = {T.PCODE[c]: c for c in CODES}

# ------------------------------------------------------------------ invented feed messages, assembled at run time
BASE = datetime.date(2026, 11, 2)
def day(n): return (BASE + datetime.timedelta(days=n)).strftime("%Y%m%d")
def us(d): return "%s/%s/%s" % (d[4:6], d[6:8], d[:4])
def fid(n): return "FEEDS%03d" % n                                    # invented feed patient id (PID-3)
def chart(n): return "pat%d" % (9300000 + n)                          # invented chart
def ctl(n): return "CTL%04d" % (7700 + n)                             # invented message control id (MSH-10)
def person(n):
    """(family name, given name, birth day as the feed writes it, member id) of invented patient n - none of them may leave the parsed file"""
    return ("ZZ" + "SKIPTEST" + chr(65 + n % 26) * 2, "INVENTED", (datetime.date(1930, 1, 1) + datetime.timedelta(days=37 * n)).strftime("%Y%m%d"), "ZM" + "%07d" % (4400000 + 13 * n))
def message(n, building, lines, npi="", admit="", pv1=True, pid=True, cut=None, msh_fields=12, dg1_fields=4):
    """One DFT^P03 message of invented patient n. lines = [(day number, code)]. pv1 / pid False = the message comes without that segment;
    cut = {line number from 0: how many fields that FT1 line keeps}; msh_fields = how many fields the MSH line keeps (the control id is the
    tenth); dg1_fields = how many fields the DG1 line keeps."""
    family, given, born, member = person(n)
    segs = [["MSH", "^~\\&", "FEED", "GRP%d^%s" % (n, building), "RECEIVING APPLICATION", "RCV", day(0) + "0101", "", "DFT^P03", ctl(n), "P", "2.5"][:msh_fields], ["EVN", "P03", day(0)]]
    if pid: segs.append(["PID", "1", "", fid(n), "", family + "^" + given, "", born, "U"])
    pv = ["PV1", "1", "I"] + [""] * 48; pv[7] = (npi + "^CLINICIAN^TEST") if npi else ""; pv[44] = admit
    if pv1: segs.append(pv)
    for k, (d, cpt) in enumerate(lines):
        ft = ["FT1", str(k + 1)] + [""] * 30
        ft[4] = day(d); ft[5] = day(d + 1); ft[10] = "1"; ft[19] = "I10"; ft[25] = cpt + "^TEST SERVICE"
        segs.append(ft[:cut[k]] if cut and k in cut else ft)
    in1 = ["IN1", "1", "", "", "TEST PAYER^X"] + [""] * 45; in1[49] = member
    segs += [["DG1", "1", "", "I10"][:dg1_fields], in1]
    return "\r".join("|".join(x) for x in segs) + "\r"
FILE = day(0)                                                         # the parser names a file by the first eight characters of its name
def write(ws, messages): open(os.path.join(ws, "hl7", FILE + "selftest.hl7"), "wb").write("".join(messages).encode())
def parse(ws, stamp=STAMP):
    """the REAL parser over the workspace's HL7 folder, started the way the ingest starts it (folder, then the parsed file's name in the
    workspace) -> (parsed messages or None, its list of skipped messages or None, what it printed, error)"""
    pf = os.path.join(ws, "feed_parsed_%s.json" % stamp); sf = os.path.join(ws, "feed_skipped_%s.json" % stamp)
    for f in (pf, sf):
        if os.path.exists(f): os.remove(f)
    out, err = run_script(PARSER, ws, (os.path.join(ws, "hl7"), "feed_parsed_%s.json" % stamp))
    rd = lambda f: json.load(open(f)) if os.path.exists(f) else None
    return rd(pf), rd(sf), out, err
def run_import(ws, mode="--all", stamp=STAMP):
    """a fresh copy of the importer over the workspace's parsed file -> (import register or None, the requests it sent, its log, error).
    The chart of each feed patient is found as the ingest finds it: by name and date of birth, from the parsed file."""
    parsed = json.load(open(os.path.join(ws, "feed_parsed_%s.json" % stamp)))
    match = {m["name"].upper().strip() + "|" + m["dob"][:8]: {"resolved": chart(int(m["pid"][-3:]))} for m in parsed if isinstance(m, dict) and m.get("pid") and "name" in m and "dob" in m}
    json.dump(match, open(os.path.join(ws, "feed_match_%s.json" % stamp), "w"))
    SENT.clear(); mod = load(ws, stamp); buf = io.StringIO(); argv = sys.argv; sys.argv = ["claimocity_import.py", mode]; err = ""
    try:
        with contextlib.redirect_stdout(buf):
            try: mod.main()
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally: sys.argv = argv
    rf = os.path.join(ws, "registers", "feed_import_%s.json" % stamp)
    return (json.load(open(rf)) if os.path.exists(rf) else None), list(SENT), buf.getvalue(), err
def run_digest(ws, stamp=STAMP):
    """the digest helper over the workspace's registers -> (the digest it wrote, error)"""
    os.environ["FEED_STAMP"] = stamp; df = os.path.join(ws, "feed_digest_%s.md" % stamp)
    if os.path.exists(df): os.remove(df)
    out, err = run_script(REPORT, ws)
    return (open(df).read() if os.path.exists(df) else ""), err
attrs = lambda tag, body: dict(re.findall(r'(\w+)="([^"]*)"', re.search(r"<%s [^>]*>" % tag, body).group(0)))
def entered(sent):
    """the visits one run entered: [(chart, date, the codes on it)] - one per addvisit that was followed by its charges"""
    out = []; cur = None
    for body in sent:
        act = re.search(r'action="(\w+)"', body).group(1)
        if act == "addvisit": cur = attrs("appt", body)["patient"]
        elif act == "updvisitwithnewcharges":
            out.append((cur, attrs("visit", body)["date"], tuple(sorted(CPT_OF.get(p, p) for p in re.findall(r'<charge id="" [^>]*proccode="([^"]*)"', body))))); cur = None
    return sorted(out)
writes = lambda sent: [b for b in sent if re.search(r'action="(addvisit|updvisitwithnewcharges|updextrainsinfo)"', b)]
TOP = "  - TOP OF THE REPORT - FEED MESSAGES SKIPPED:"
top_lines = lambda digest: [l for l in digest.split("\n") if l.startswith(TOP)]
def private(n, *texts):
    """the family name, birth day or member id of invented patient n that any of these texts carries (none may)"""
    family, given, born, member = person(n); blob = "\n".join(t if isinstance(t, str) else json.dumps(t) for t in texts)
    return [w for w in (family, born, member) if w in blob]
skip_lines = lambda log: [l for l in log.split("\n") if l.startswith("SKIPPED MESSAGE")]

# ------------------------------------------------------------------ the batches: three good messages, the bad one second
GOOD = {1: lambda: message(1, NURS[0], [(0, "99309")], NPI_B), 3: lambda: message(3, HOSPITAL, [(1, "99232")], NPI_A, admit=day(-2)), 4: lambda: message(4, NURS[1], [(2, "99308")], NPI_B)}
EXPECT = sorted([(chart(1), us(day(0)), ("99309",)), (chart(3), us(day(1)), ("99232",)), (chart(4), us(day(2)), ("99308",))])
BAD = {
 # 1: no PV1 segment - patient, charge line, diagnosis and payer are all there
 "no PV1 segment": (lambda: message(2, NURS[0], [(0, "99309")], NPI_B, pv1=False), "parser", "no PV1 segment"),
 # 2: the SECOND charge line stops after twelve fields (the date of service and the units are there, the diagnosis and the code are not)
 "a short FT1 line": (lambda: message(2, NURS[0], [(0, "99309"), (0, "99308")], NPI_B, cut={1: 12}), "parser", "FT1 line 2 has 12 fields - the parser reads 20"),
 # 3: no FT1 line at all - nothing to enter
 "no FT1 line": (lambda: message(2, NURS[0], [], NPI_B), "import", "no FT1 line - no charge to enter"),
}
for case, (bad, by, why) in BAD.items():
    ws = workspace("case_" + re.sub(r"\W+", "_", case)); write(ws, [GOOD[1](), bad(), GOOD[3](), GOOD[4]()])
    parsed, skipped, plog, perr = parse(ws)
    check("%s: the parser reads the whole file and writes the parsed file" % case, perr == "" and isinstance(parsed, list), (perr, plog[-200:]))
    if by == "parser":
        check("%s: the parsed file holds the three good messages and not the bad one" % case, isinstance(parsed, list) and [m.get("pid") for m in parsed] == [fid(1), fid(3), fid(4)], parsed and [m.get("pid") for m in parsed])
        check("%s: the parser's own list names the bad message - file, place in the file, control id and the reason, nothing else" % case,
              skipped == [{"file": FILE, "msg": 2, "ctl": ctl(2), "why": why}], skipped)
        check("%s: ... and its log says so in a line of its own" % case, [l for l in skip_lines(plog) if ctl(2) in l and why in l and "message 2" in l] != [] and len(skip_lines(plog)) == 1, skip_lines(plog) or plog[-300:])
        check("%s: ... without the patient's name, birth day or member id" % case, skipped is not None and private(2, skipped, "\n".join(skip_lines(plog))) == [], private(2, skipped, plog))
    else:
        check("%s: the parser passes the message on (it can be read: the import is the one that finds nothing to enter) and skips none" % case,
              isinstance(parsed, list) and [m.get("pid") for m in parsed] == [fid(1), fid(2), fid(3), fid(4)] and parsed[1]["FT1"] == [] and skipped == [], (parsed and [m.get("pid") for m in parsed], skipped))
    if not isinstance(parsed, list):                                   # nothing to import: every check below fails with the reason
        for name in ("the import runs to its end", "the batch's other three visits are entered, each once", "nothing of the bad message is entered", "the import register names the bad message under skipped_messages",
                     "the import log names it", "the register carries no name, birth day or member id", "the digest has ONE top-of-report line", "a re-run enters nothing twice", "the re-run still names the message once"):
            check("%s: %s" % (case, name), False, "the parser wrote no parsed file (%s)" % perr)
        continue
    reg, sent, log, err = run_import(ws)
    check("%s: the import runs to its end" % case, err == "" and "DONE" in log, (err, log[-300:]))
    check("%s: the batch's other three visits are entered, each once" % case, entered(sent) == EXPECT and reg is not None and len(reg["created"]) == 3, (entered(sent), reg and len(reg["created"])))
    check("%s: nothing of the bad message is entered - no request names its chart, no register row is its" % case,
          not any(chart(2) in b for b in sent) and reg is not None and not any(r.get("feed_id") == fid(2) or r.get("pid") == chart(2) for k in ("created", "skipped", "failed") for r in reg[k]), [b[:120] for b in sent if chart(2) in b])
    want = [{"ctl": ctl(2), "file": FILE, "msg": 2, "why": why, "by": by}]
    check("%s: the import register names the bad message under skipped_messages - control id, file, place in the file, reason, who skipped it" % case, reg is not None and reg.get("skipped_messages") == want, reg and reg.get("skipped_messages"))
    check("%s: the import log names it in a line of its own and counts it in its closing line" % case,
          [l for l in skip_lines(log) if ctl(2) in l and why in l] != [] and len(skip_lines(log)) == 1 and "FEED MESSAGE SKIPPED" in log.split("\n")[-2], (skip_lines(log), log.split("\n")[-2][-200:]))
    check("%s: the register and the import log carry no name, birth day or member id of that patient" % case, reg is not None and private(2, reg, "\n".join(skip_lines(log))) == [], private(2, reg, log))
    digest, derr = run_digest(ws); tops = top_lines(digest)
    check("%s: the digest has ONE top-of-report line - how many, the control id, the reason, and that a person must look at the feed file" % case,
          derr == "" and len(tops) == 1 and tops[0].startswith(TOP + " 1 message(s)") and ctl(2) in tops[0] and why in tops[0] and "a person must look at the feed file" in tops[0] and "NOT entered" in tops[0]
          and private(2, digest) == [], (derr, tops or digest[:300]))
    reg2, sent2, log2, err2 = run_import(ws)
    check("%s: a re-run enters nothing twice - it runs to its end, sends no visit and no charge, and the three visits stay as they were" % case,
          err2 == "" and writes(sent2) == [] and reg2 is not None and [(r["pid"], r["dos"], r["visit"], r["charges"]) for r in reg2["created"]] == [(r["pid"], r["dos"], r["visit"], r["charges"]) for r in reg["created"]], (err2, len(writes(sent2))))
    check("%s: the re-run still names the message once (its register, its log, the digest)" % case,
          reg2 is not None and reg2.get("skipped_messages") == want and len(skip_lines(log2)) == 1 and len(top_lines(run_digest(ws)[0])) == 1, reg2 and reg2.get("skipped_messages"))

# ------------------------------------------------------------------ the three in ONE batch, with three more of their kind
ws = workspace("all_in_one")
ALL = [GOOD[1](), BAD["no PV1 segment"][0](), GOOD[3](),
       message(5, NURS[1], [(0, "99309"), (0, "99308")], NPI_B, cut={1: 12}),      # 4th message: a short second charge line
       message(6, NURS[0], [], NPI_A),                                                 # 5th: no charge line
       message(7, NURS[0], [(0, "99309")], NPI_B, pid=False),                          # 6th: no PID segment
       message(8, NURS[1], [(0, "99309")], NPI_B, pv1=False, msh_fields=3),            # 7th: no PV1 segment, and an MSH line that stops before the control id
       message(9, NURS[1], [(0, "99309")], NPI_B, cut={0: 2}),                         # 8th: its only charge line is two fields long
       GOOD[4]()]
write(ws, ALL); parsed, skipped, plog, perr = parse(ws)
WANT_P = [{"file": FILE, "msg": 2, "ctl": ctl(2), "why": "no PV1 segment"}, {"file": FILE, "msg": 4, "ctl": ctl(5), "why": "FT1 line 2 has 12 fields - the parser reads 20"},
          {"file": FILE, "msg": 6, "ctl": ctl(7), "why": "no PID segment"}, {"file": FILE, "msg": 7, "ctl": "", "why": "no PV1 segment"},
          {"file": FILE, "msg": 8, "ctl": ctl(9), "why": "FT1 line 1 has 2 fields - the parser reads 20"}]
check("one batch, six bad messages: the parser reads on to the end, keeps the three good ones and the one with no charge line, and lists the other five - each with its place in the file; one has no control id to give",
      perr == "" and isinstance(parsed, list) and [m.get("pid") for m in parsed] == [fid(1), fid(3), fid(6), fid(4)] and skipped == WANT_P, (perr, parsed and [m.get("pid") for m in parsed], skipped))
check("... a message with one good and one short charge line is skipped WHOLE (its good line is not in the parsed file either)", isinstance(parsed, list) and not any(m.get("pid") == fid(5) for m in parsed))
check("... and the parser's log ends with those five lines (the ingest shows the last lines of each step)", len(skip_lines(plog)) == 5 and [l.startswith("SKIPPED MESSAGE") for l in plog.strip().split("\n")[-5:]] == [True] * 5
      and any("no control id" in l and "message 7" in l for l in skip_lines(plog)), plog.strip().split("\n")[-6:])
if isinstance(parsed, list):
    reg, sent, log, err = run_import(ws); digest, derr = run_digest(ws) if reg is not None else ("", "no register"); tops = top_lines(digest)
    WANT_R = [dict(x, by="parser") for x in WANT_P] + [{"ctl": ctl(6), "file": FILE, "msg": 5, "why": "no FT1 line - no charge to enter", "by": "import"}]
    key = lambda x: (x.get("file"), x.get("msg"))
    check("one batch: the import runs to its end and enters exactly the three good visits", err == "" and entered(sent) == EXPECT and reg is not None and len(reg["created"]) == 3, (err, entered(sent)))
    check("one batch: the register lists all six - the parser's five and the import's one", reg is not None and sorted(reg.get("skipped_messages") or [], key=key) == sorted(WANT_R, key=key), reg and reg.get("skipped_messages"))
    check("one batch: still ONE top-of-report line - it says 6 message(s), gives the five control ids, and for the message without one the file and its place in it",
          derr == "" and len(tops) == 1 and tops[0].startswith(TOP + " 6 message(s)") and all(ctl(n) in tops[0] for n in (2, 5, 6, 7, 9)) and "no control id (file %s, message 7" % FILE in tops[0], (derr, tops))
    check("one batch: no name, birth day or member id of any of the six in the register, the digest or the log's lines",
          [private(n, reg, digest, "\n".join(skip_lines(log)), "\n".join(skip_lines(plog)), skipped) for n in (2, 5, 6, 7, 8, 9)] == [[]] * 6)
    reg2, sent2, log2, err2 = run_import(ws)
    check("one batch: a re-run enters nothing twice and lists the same six once each", err2 == "" and writes(sent2) == [] and reg2 is not None and len(reg2["created"]) == 3 and sorted(reg2.get("skipped_messages") or [], key=key) == sorted(WANT_R, key=key), (err2, len(writes(sent2))))
else:
    for name in ("the import runs to its end", "the register lists all six", "ONE top-of-report line", "no name, birth day or member id", "a re-run enters nothing twice"): check("one batch: " + name, False, "the parser wrote no parsed file (%s)" % perr)

# ------------------------------------------------------------------ a batch with nothing wrong: no line, no register key, and every message read as before
ws = workspace("nothing_wrong"); write(ws, [GOOD[1](), GOOD[3](), GOOD[4]()]); parsed, skipped, plog, perr = parse(ws)
family, given, born, member = person(3)
OLD = {"file": FILE, "FT1": [{"dos": day(1), "posted": day(2), "units": "1", "dx": "I10", "cpt": "99232"}], "IN1": ["TEST PAYER"], "DG1": ["I10"], "facility": "RECEIVING APPLICATION", "msgtime": "",
       "pid": fid(3), "name": family + ", " + given, "dob": born, "provider": "CLINICIAN TEST", "admit": day(-2)}
check("nothing wrong: a readable message is read exactly as before - every field the parser wrote until now, value for value",
      isinstance(parsed, list) and len(parsed) == 3 and {k: v for k, v in parsed[1].items() if k in OLD} == OLD, parsed and parsed[1])
check("nothing wrong: ... and it now also carries its message control id and its place in the file (so the import can name a message it skips)",
      isinstance(parsed, list) and len(parsed) == 3 and [(m.get("ctl"), m.get("msg")) for m in parsed] == [(ctl(1), 1), (ctl(3), 2), (ctl(4), 3)] and set(parsed[1]) == set(OLD) | {"ctl", "msg"}, parsed and [(m.get("ctl"), m.get("msg")) for m in parsed])
check("nothing wrong: the parser writes an EMPTY list of skipped messages (a list left by an earlier parse of the same stamp never lingers) and its log has no such line", skipped == [] and skip_lines(plog) == [], (skipped, skip_lines(plog)))
reg, sent, log, err = run_import(ws); digest, derr = run_digest(ws)
check("nothing wrong: three visits entered, no skipped_messages key in the register, no such line in the import log or the digest",
      err == "" and entered(sent) == EXPECT and reg is not None and "skipped_messages" not in reg and skip_lines(log) == [] and "FEED MESSAGE SKIPPED" not in log and derr == "" and top_lines(digest) == [] and "SKIPPED" not in digest,
      (err, entered(sent), reg and reg.get("skipped_messages"), top_lines(digest)))

# ------------------------------------------------------------------ a dry run writes nothing; the same file under a later stamp enters nothing
ws = workspace("dry_then_live"); write(ws, [GOOD[1](), BAD["no FT1 line"][0](), GOOD[3](), GOOD[4]()]); parsed, skipped, plog, perr = parse(ws)
reg, sent, log, err = run_import(ws, "--dry")
check("dry run: the import runs to its end, names the message with no FT1 line in its log, sends no visit and writes no register",
      err == "" and writes(sent) == [] and reg is None and len(skip_lines(log)) == 1 and ctl(2) in skip_lines(log)[0] and log.count("\nDRY ") + log.startswith("DRY ") == 3, (err, len(writes(sent)), reg is not None, skip_lines(log)))
reg, sent, log, err = run_import(ws)
check("... and the live run after it enters the three visits and names the message (the dry run left nothing behind that could hide it)",
      err == "" and entered(sent) == EXPECT and reg is not None and [x.get("ctl") for x in reg.get("skipped_messages") or []] == [ctl(2)], (err, entered(sent)))
write(ws, [GOOD[1](), BAD["no PV1 segment"][0](), BAD["no FT1 line"][0]().replace(ctl(2), ctl(12)).replace(fid(2), fid(12)), GOOD[3](), GOOD[4]()])
parsed, skipped, plog, perr = parse(ws, LATER)
if isinstance(parsed, list):
    regL, sentL, logL, errL = run_import(ws, stamp=LATER); digL, derrL = run_digest(ws, LATER) if regL is not None else ("", "no register")
    check("the same visits seen again under a LATER stamp (a batch run again): nothing is entered twice, and that batch's own register and digest name its two bad messages",
          errL == "" and writes(sentL) == [] and regL is not None and regL["created"] == [] and sorted(x.get("ctl") for x in regL.get("skipped_messages") or []) == sorted([ctl(2), ctl(12)])
          and len(top_lines(digL)) == 1 and top_lines(digL)[0].startswith(TOP + " 2 message(s)"), (errL, len(writes(sentL)), regL and regL.get("skipped_messages"), top_lines(digL)))
    check("... while the first batch's register is as it was (three visits, its one message)", [x.get("ctl") for x in json.load(open(os.path.join(ws, "registers", "feed_import_%s.json" % STAMP))).get("skipped_messages") or []] == [ctl(2)]
          and len(json.load(open(os.path.join(ws, "registers", "feed_import_%s.json" % STAMP)))["created"]) == 3)
else:
    for name in ("nothing is entered twice", "the first batch's register is as it was"): check("the same visits seen again under a LATER stamp: " + name, False, "the parser wrote no parsed file (%s)" % perr)

# ------------------------------------------------------------------ the parser's list that cannot be read is said, never taken as "nothing skipped"
ws = workspace("list_unread"); write(ws, [GOOD[1](), GOOD[3](), GOOD[4]()]); parsed, skipped, plog, perr = parse(ws)
open(os.path.join(ws, "feed_skipped_%s.json" % STAMP), "w").write("[{")      # cut off in the middle
reg, sent, log, err = run_import(ws); digest, derr = run_digest(ws) if reg is not None else ("", "no register"); tops = top_lines(digest)
check("a list of skipped messages that is there but cannot be read: the visits are entered all the same, and the register, the import log and ONE top-of-report line say that the list could not be read - a person looks at the parser's log",
      err == "" and entered(sent) == EXPECT and reg is not None and "skipped_messages" not in reg and "could not be read" in str(reg.get("skipped_messages_unread") or "") and "feed_skipped_%s.json" % STAMP in str(reg.get("skipped_messages_unread") or "")
      and len(tops) == 1 and "could not be read" in tops[0] and "logs/claimocity_%s_parse.log" % STAMP in tops[0] and "a person must look at the feed file" in tops[0], (err, reg and reg.get("skipped_messages_unread"), tops))

# ------------------------------------------------------------------ whatever else fails while ONE message is read: that message, never the batch
ws = workspace("anything_else"); write(ws, [GOOD[1](), message(2, NURS[0], [(0, "99309")], NPI_B, dg1_fields=2), GOOD[3](), GOOD[4]()]); parsed, skipped, plog, perr = parse(ws)
check("a message that fails in a way nobody listed (its DG1 line is two fields long - the parser ended there too): skipped and named with the kind of failure, the rest is read",
      perr == "" and isinstance(parsed, list) and [m.get("pid") for m in parsed] == [fid(1), fid(3), fid(4)] and skipped == [{"file": FILE, "msg": 2, "ctl": ctl(2), "why": "could not be read (IndexError)"}], (perr, skipped))
if isinstance(parsed, list):
    reg, sent, log, err = run_import(ws)
    check("... the other three visits are entered and the register names it", err == "" and entered(sent) == EXPECT and reg is not None and reg.get("skipped_messages") == [{"ctl": ctl(2), "file": FILE, "msg": 2, "why": "could not be read (IndexError)", "by": "parser"}], (err, reg and reg.get("skipped_messages")))
else: check("... the other three visits are entered and the register names it", False, perr)

# ------------------------------------------------------------------ a parsed file from before this change, or one put together by hand
ws = workspace("older_parsed_file"); write(ws, [GOOD[1](), BAD["no FT1 line"][0](), GOOD[3](), GOOD[4]()]); parsed, skipped, plog, perr = parse(ws)
if isinstance(parsed, list):
    json.dump([{k: v for k, v in m.items() if k not in ("ctl", "msg")} for m in parsed], open(os.path.join(ws, "feed_parsed_%s.json" % STAMP), "w"))      # as the parser wrote it until 11/11/2026 ...
    if os.path.exists(os.path.join(ws, "feed_skipped_%s.json" % STAMP)): os.remove(os.path.join(ws, "feed_skipped_%s.json" % STAMP))                     # ... and with no list of skipped messages
    reg, sent, log, err = run_import(ws); digest, derr = run_digest(ws) if reg is not None else ("", "no register"); tops = top_lines(digest)
    check("a parsed file written before this change (no control ids, no list of skipped messages): the message with no FT1 line is skipped all the same and named by its file - the three visits are entered",
          err == "" and entered(sent) == EXPECT and reg is not None and reg.get("skipped_messages") == [{"ctl": "", "file": FILE, "msg": None, "why": "no FT1 line - no charge to enter", "by": "import"}] and "skipped_messages_unread" not in reg
          and len(tops) == 1 and "no control id (file %s: no FT1 line - no charge to enter)" % FILE in tops[0], (err, reg and reg.get("skipped_messages"), tops))
else: check("a parsed file written before this change: the message with no FT1 line is skipped all the same", False, perr)
ws = workspace("by_hand"); write(ws, [GOOD[1]()]); parsed, skipped, plog, perr = parse(ws)
if isinstance(parsed, list) and parsed:
    g = parsed[0]
    odd = ["not a record", dict({k: v for k, v in g.items() if k != "name"}, pid=fid(21), ctl=ctl(21), msg=5), dict(g, pid=fid(22), ctl=ctl(22), msg=6, FT1=[{"units": "1"}]), g]
    json.dump(odd, open(os.path.join(ws, "feed_parsed_%s.json" % STAMP), "w"))
    reg, sent, log, err = run_import(ws)
    check("records the import cannot key (not a record at all, one without a name, one whose charge line has no date and no code): each is skipped and named, the good visit after them is entered, and the place-of-service rule still reads the batch",
          err == "" and entered(sent) == [EXPECT[0]] and reg is not None and [(x.get("ctl"), x.get("why"), x.get("by")) for x in reg.get("skipped_messages") or []] == [("", "not a message record", "import"),
          (ctl(21), "no patient id, name or date of birth in the parsed record", "import"), (ctl(22), "an FT1 line without a date of service or a code", "import")] and "batch visit list not built" not in log, (err, entered(sent), reg and reg.get("skipped_messages"), [l for l in log.split("\n") if "POS RULE" in l]))
else: check("records the import cannot key: each is skipped and named", False, perr)

# ------------------------------------------------------------------ the retry of visits that waited on a diagnosis code
ws = workspace("retry"); EARLIER = "20261109T0000Z"
# 11/12/2026 (merge of main's 99349 / unknown-CPT retry): the retry enters a visit only when every code of it is in BOTH the PCODE and the FEE table of
# the import copy beside it (it reads them as text, never runs it) - the sandbox gets those two tables of the importer, read from it here, and nothing else
_isrc = open(IMPORT, encoding="utf-8").read()
open(os.path.join(ws, "claimocity_import.py"), "w", encoding="utf-8").write("".join(re.search(r"^%s\s*=\s*\{.*?\}\n" % t_, _isrc, re.S | re.M).group(0) for t_ in ("PCODE", "FEE")))
json.dump({"created": [], "failed": [], "skipped": [{"feed_id": fid(2), "pid": chart(2), "why": "no usable dx for 99308"}]}, open(os.path.join(ws, "registers", "feed_import_%s.json" % EARLIER), "w"))
family, given, born, member = person(2)
json.dump([{"file": FILE, "FT1": [], "IN1": [], "DG1": [], "facility": "", "msgtime": "", "pid": fid(2), "name": family + ", " + given, "dob": born, "provider": "", "admit": ""},      # the same patient's message with no charge line, read first
           {"file": FILE, "FT1": [{"dos": day(0), "posted": day(1), "units": "1", "dx": "M5117", "cpt": "99308"}], "IN1": [], "DG1": [], "facility": "", "msgtime": "", "pid": fid(2), "name": family + ", " + given, "dob": born, "provider": "", "admit": ""}],
          open(os.path.join(ws, "feed_parsed_%s.json" % EARLIER), "w"))
json.dump({"M5117": None}, open(os.path.join(ws, "dx_cache_feed.json"), "w")); json.dump({fid(2): chart(2)}, open(os.path.join(ws, "registers", "claimocity_patient_map.json"), "w"))
STARTED = []
programs = types.ModuleType("subprocess"); programs.STAND_IN = True; programs.STDOUT = -2; programs.PIPE = -1      # the programs the retry would start: none is started, each is noted
def _would_start(cmd, **k):
    STARTED.append([os.path.basename(str(x)) for x in cmd])
    if hasattr(k.get("stdout"), "write"): k["stdout"].write("DONE {}\n")
    return types.SimpleNamespace(returncode=0, stdout="", stderr="")
programs.run = _would_start
def run_retry(ws):
    """the retry driver INSIDE this process: its workspace and repository lines are pointed at the sandbox, every program it would start is only noted"""
    src = open(RETRY, encoding="utf-8").read()
    src = src.replace('WS = "/home/claude/unbilled"', "WS = %r" % ws, 1).replace('REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"', "REPO_HELPERS = %r" % os.path.join(ws, "no_clone"), 1)
    left = [ln for ln in src.split("\n") if ("/home/claude/unbilled" in ln or "/home/claude/effinger-billing-backend" in ln) and not ln.lstrip().startswith("#")]
    if left: raise RuntimeError("the sandbox copy still names a live folder outside a comment - not run: %r" % left[:2])
    path = os.path.join(ws, "claimocity_retry_dx.py"); open(path, "w", encoding="utf-8").write(src)
    return run_script(path, ws, ("--stamp", "2026-11-11T0100Z"), extra={"subprocess": programs})
os.environ["FEED_DX_CACHE"] = "dx_cache_feed.json"; rout, rerr = run_retry(ws)
check("retry: a message with no FT1 line of a patient whose visit waits on a diagnosis code does not stop the retry - it reads on and reports the visit that still waits",
      rerr == "" and "1 visit(s) still wait on codes not in AMD's diagnosis list: M5117" in rout and [c[1] for c in STARTED] == ["claimocity_dx.py"], (rerr, rout[-300:], STARTED))

# ------------------------------------------------------------------ the words: the mirror's guard, the shared helper, the runbook
rd = lambda *p: open(os.path.join(ROOT, *p), encoding="utf-8").read()
MIR = rd("tools", "mirror", "mirror.py"); HCS = rd("scripts", "helpers", "claimocity_helpers_current.py"); STEP = rd("nightly", "claimocity_feed_step.md"); STEPN = STEP.replace("\n", " ")
PSRC = rd("scripts", "helpers", "feed_parse_dft_1028.py"); ISRC = rd("scripts", "helpers", "claimocity_import.py"); RSRC = rd("scripts", "helpers", "claimocity_report.py")
MARK = "a message this parser cannot read is skipped and named"
check("mirror.py never lets a parser from before this change back onto main: its marker is a sentence only this parser has, and the shared helper checks the same sentence when there is no repository copy",
      '"feed_parse_dft_1028.py": "%s"' % MARK in MIR and MARK in PSRC and '"feed_parse_dft_1028.py": "%s"' % MARK in HCS, (MARK in PSRC, '"feed_parse_dft_1028.py"' in MIR, '"feed_parse_dft_1028.py": "' in HCS))
_sec = STEP[STEP.index("## Feed messages that could not be read"):] if "## Feed messages that could not be read" in STEP else ""
_sec = _sec[:_sec.index("\n## ", 5)] if "\n## " in _sec[5:] else _sec; _secn = _sec.replace("\n", " ")
check("runbook: a section says what the routine does with the line - it names the digest's own words, the register key, the parser's file and the log lines, and every reason is one the code gives",
      _sec != "" and "FEED MESSAGES SKIPPED" in _secn and "FEED MESSAGES SKIPPED" in RSRC and "skipped_messages" in _secn and "feed_skipped_<stamp>.json" in _secn and "SKIPPED MESSAGE" in _secn
      and all(w in _secn and (w in PSRC or w in ISRC) for w in ("no PV1 segment", "no PID segment", "no FT1 line")) and "goes to the top of the report word for word" in _secn
      and "python3 tools/selftest/test_feed_skipped_messages.py" in _secn, [w for w in ("FEED MESSAGES SKIPPED", "skipped_messages", "feed_skipped_<stamp>.json", "SKIPPED MESSAGE", "no PV1 segment", "no PID segment", "no FT1 line") if w not in _secn])
check("runbook: ... a routine changes nothing on such a message - it does not edit the feed file, enter the visit by hand or run the file again; a person looks at the feed file",
      all(w in _secn for w in ("does not edit the feed file", "does not enter the visit by hand", "does not run the file again", "a person must look at the feed file")), _secn[:400])
check("runbook: the step the routines follow (f) names the line among those that go to the top", "FEED MESSAGES SKIPPED" in STEP[STEP.index("(f) Report line"):STEP.index("Duplicates: should Gregg")])

# ------------------------------------------------------------------ this test stood where it said it stands
_me = open(os.path.abspath(__file__), encoding="utf-8").read()
_starts = re.findall(r"^[ \t]*(?:import|from)[ \t]+" + "subprocess" + r"\b|" + "os" + r"\.(?:system|popen|exec\w*|spawn\w*|fork)\(|" + "runpy" + r"\.", _me, re.M)
check("this self-test starts nothing as a program: it neither loads the program starter nor calls the shell", _starts == [], _starts)
check("after everything the stand-ins are still what a helper would load, and no real helper module was ever loaded from scripts/helpers or core",
      all(sys.modules.get(n) is m for n, m in STAND.items()) and not [n for n, m in list(sys.modules.items()) if getattr(m, "__file__", None) and (os.path.abspath(m.__file__).startswith(HELPERS + os.sep) or os.path.abspath(m.__file__).startswith(os.path.join(ROOT, "core") + os.sep))])
os.chdir(ROOT)
print("\ntest_feed_skipped_messages: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1500]))
sys.exit(1 if FAILS else 0)
