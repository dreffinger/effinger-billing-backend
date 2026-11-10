#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/10/2026): whole feed batches, from the raw HL7 text to the requests AdvancedMD would get.
# Decides: nothing. tools/selftest/test_pos_rule.py proves the place-of-service rule and the per-message reading of the feed import
#   on parsed entries built by hand. This test adds the one thing that leaves open: invented messages are written as HL7 files, parsed
#   by the REAL scripts/helpers/feed_parse_dft_1028.py and entered by a fresh copy of scripts/helpers/claimocity_import.py, so the way
#   the importer finds a parsed message in the raw files is proven against what the parser really writes. It checks what is SENT
#   (facility, place of service, clinician profile, admission date), so it holds for any way the importer does it:
#     A  one feed patient, nursing-building care management + a hospital visit in one batch (both read orders): the care management
#        goes under the nursing building (32 by the rule when the hospital visit is in another calendar month; kept at 31 by the
#        rule's own exception when both fall in one month), the hospital visit under the hospital at 21 with ITS admission date,
#        each under its own clinician;
#     B  assisted-living care management + a nursing visit (both orders): 13 and the nursing building;
#     C  the same patient + date + codes sent from two buildings cannot be told apart: the visit is entered once, at the feed's
#        place of service when it lands in a nursing building, and its register row says it is not the message's own reading;
#     R  a hospital message sent twice, the second copy with a corrected admission date, while another message of the same patient
#        is read last: one visit, with the admission date of its own last copy;
#     D  one building: each visit under the clinician and the admission date of its own message (also when PV1 stands after FT1);
#     H  nursing visits a month apart inside ONE batch: after one in another nursing building, or one sent from the hospital
#        building, the visit is a new admission (31); in the same building it is the monthly visit (32);
#     K  two messages with the same patient, date and first code but different code lists are told apart;
#     E  giving every message its own feed patient id (same charts) changes no request: a feed patient with several buildings or
#        clinicians is entered exactly like so many one-message feed patients;
#     F  before / after: patients whose messages agree on building, clinician and admission date are entered twice - every visit
#        from its own message, then every visit from the patient's values (the way it was until 11/10/2026: the importer is given
#        raw files that hold one other message per patient) - and the same bytes are sent both ways.
#   Until 11/10/2026 the importer kept building, clinician and admission date per feed PATIENT (last message read): in cases A, B, D
#   and H every visit of the patient went in under one building / clinician / admission date.
# Never touches: AMD (the importer gets stand-in amd / resave / txh modules in this process and every socket is refused), Gmail,
#   Drive, the workspace. The parser is started with python -I and imports only the standard library. Writes only to a temp
#   directory, removed at the end. No switch or cache of the calling shell is read: every environment name the importer knows is unset.
# No patient data: every patient id, name, date of birth and chart number is invented and assembled at run time. The buildings and
#   the two clinician ids are read from the importer's own FAC / PROFILE tables at run time, so none is written here.
# Not used on purpose: stored fingerprints of requests (they would move with every revision of the rule) and 99306 (who it is entered
#   under is a rule of its own, apart from the feed's clinician); lines the importer adds on its own to a visit are ignored.
# Run it together with test_pos_rule.py after ANY change to how the importer re-reads the raw files or to feed_parse_dft_1028.py.
# Run: python3 tools/selftest/test_feed_batches_real_parser.py   (exit 1 on any failure)
import os, sys, re, io, json, types, atexit, shutil, socket, tempfile, datetime, contextlib, subprocess, importlib.util
import xml.etree.ElementTree as ET
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = os.path.join(ROOT, "scripts", "helpers", "claimocity_import.py")
PARSER = os.path.join(ROOT, "scripts", "helpers", "feed_parse_dft_1028.py")
TMP = tempfile.mkdtemp(prefix="selftest_feed_batches_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
STAMP = "20261110T0000Z"; MSGTIME = "11/10/2026 1:00:00 AM"
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:500]))
    if not cond: FAILS.append(name)

# ------------------------------------------------------------------ stand-ins: no real amd / resave / txh, no socket
def _no_network(*a, **k): raise AssertionError("network use in an offline self-test")
socket.socket = _no_network; socket.create_connection = _no_network
# whatever the calling shell exports, none of the importer's switches or caches decides what these invented charts get: every
# environment name the importer reads is unset here (the three this test needs are set again at each load)
for _name in set(re.findall(r'environ(?:\.get\(|\[)\s*"([A-Za-z_][A-Za-z0-9_]*)"', open(HELPER, encoding="utf-8").read())): os.environ.pop(_name, None)
sys.dont_write_bytecode = True
SENT = []; N = {"visit": 0, "charge": 0, "login": 0}
def _msg(action, cls, attrs=None, children=""):
    return '<ppmdmsg action="%s" class="%s" msgtime="%s" %s>%s</ppmdmsg>' % (action, cls, MSGTIME, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
def _post(body, timeout=None):
    SENT.append(body); act = re.search(r'action="(\w+)"', body).group(1)
    if act == "getdemographic":
        pid = re.search(r'patientid="([^"]*)"', body).group(1)
        return ('<PPMDResults><Results><patient id="%s" respparty="resp%s" insorder="1" deceased=""/>'
                '<insplan id="ins1" carrier="car1" begindate="01/01/2020" enddate="" sequence="1"/></Results></PPMDResults>') % (pid, re.sub(r"\D", "", pid))
    if act == "addvisit":
        N["visit"] += 1; return '<PPMDResults><Results success="1"><visit id="vst%d"/></Results></PPMDResults>' % (7000 + N["visit"])
    if act == "updvisitwithnewcharges":                # AMD's answer echoes each charge with the place of service it stored
        out = ""
        for pos, fee in re.findall(r'<charge id="" [^>]*? pos="(\d*)"[^>]*? fee="([^"]*)"', body):
            N["charge"] += 1; out += '<charge id="charge%d" pos="%s" fee="%s"/>' % (50000 + N["charge"], pos, fee)
        return '<PPMDResults><Results success="1"><visit id="%s"><chargelist>%s</chargelist></visit></Results></PPMDResults>' % (re.search(r'<visit id="(vst\d+)"', body).group(1), out)
    if act == "updextrainsinfo":
        return '<PPMDResults><Results success="1"><extins %s/></Results></PPMDResults>' % re.search(r'hospitalizationfrom="[^"]*"', body).group(0)
    raise AssertionError("request the import never sends: " + act)
def _login(psw=None): N["login"] += 1
amd = types.ModuleType("amd"); amd.post = _post; amd.msg = _msg; amd._msgtime = lambda: MSGTIME; amd.login_cached = _login
txh = types.ModuleType("txh"); txh.fetch = lambda num: ET.Element("PPMDResults")          # every invented chart starts empty
resave = types.ModuleType("resave"); resave.detail = lambda c: "<PPMDResults/>"
sys.modules.update(amd=amd, txh=txh, resave=resave)

# ------------------------------------------------------------------ the importer, loaded fresh per batch from its file
DX = {"I10": "dcode101", "E119": "dcode102", "N390": "dcode103", "F0390": "dcode104"}      # ICD-10 -> AMD id for the invented messages
def workspace(name):
    ws = os.path.join(TMP, name); os.makedirs(os.path.join(ws, "hl7")); os.makedirs(os.path.join(ws, "registers"))
    json.dump(DX, open(os.path.join(ws, "dx_cache_feed.json"), "w")); return ws
def load(ws, hl7=None):
    os.chdir(ws); os.environ.update(FEED_STAMP=STAMP, FEED_HL7_DIR=hl7 or os.path.join(ws, "hl7"), FEED_DX_CACHE="dx_cache_feed.json")
    spec = importlib.util.spec_from_file_location("claimocity_import_batches", HELPER); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.time = types.SimpleNamespace(sleep=lambda s: None)          # the pause between visits is not under test
    return mod
ws0 = workspace("tables")
for f, v in (("feed_parsed_%s.json" % STAMP, []), ("feed_match_%s.json" % STAMP, {})): json.dump(v, open(os.path.join(ws0, f), "w"))
T = load(ws0)                                                         # the buildings and the clinician ids, from the importer's own tables
check("the stand-ins are what the importer imported (never the real AMD helper)", T.amd is amd and T.txh is txh and T.resave is resave)
HOSP = [b for b, (f, p) in T.FAC.items() if p == "21"]; NURS = [b for b, (f, p) in T.FAC.items() if p == "31"]; ALF = [b for b, (f, p) in T.FAC.items() if p == "13"]
CLIN = list(T.PROFILE.items())
FEED_CODES = "99223 99232 99233 99239 99308 99309 99316 99344 99487 99489".split()          # every code these messages carry
check("tables: a hospital at 21, two nursing buildings at 31, two assisted-living buildings at 13, two clinician profiles, every code known",
      HOSP and len(NURS) >= 2 and len(ALF) >= 2 and len(CLIN) >= 2 and CLIN[0][1] != CLIN[1][1] and all(c in T.PCODE and c in T.FEE for c in FEED_CODES),
      (len(HOSP), len(NURS), len(ALF), [v for k, v in CLIN[:2]], [c for c in FEED_CODES if c not in T.PCODE or c not in T.FEE]))
if FAILS: print("\n%d failure(s): %s - the batches below cannot be built without these tables" % (len(FAILS), "; ".join(FAILS))); sys.exit(1)
HOSPITAL = HOSP[0]; (NPI_A, PROF_A), (NPI_B, PROF_B) = CLIN[:2]
FACID = lambda b: T.FAC[b][0]                                         # the facility a building is entered under
CPT_OF = {T.PCODE[c]: c for c in FEED_CODES}

# ------------------------------------------------------------------ invented feed messages, assembled at run time
BASE = datetime.date(2026, 11, 2)
def day(n): return (BASE + datetime.timedelta(days=n)).strftime("%Y%m%d")
def us(d): return "%s/%s/%s" % (d[4:6], d[6:8], d[:4])
def fid(n): return "FEEDT%03d" % n                                    # invented feed patient id (PID-3)
def chart(n): return "pat%d" % (9100000 + n)                          # invented chart
def message(n, building, lines, npi="", admit="", as_id=None, pv1_last=False):
    """One DFT^P03 message of invented patient n (sent under feed id as_id when given). lines = [(day number, CPT, [dx codes], units)].
    pv1_last: the visit segment stands after the charge lines (neither reader may care where it stands)."""
    born = (datetime.date(1931, 1, 1) + datetime.timedelta(days=41 * n)).strftime("%Y%m%d")
    segs = [["MSH", "^~\\&", "FEED", "GRP%d^%s" % (n, building), "RECEIVING APPLICATION", "RCV", day(0) + "0101", "", "DFT^P03", "CTL%d" % n, "P", "2.5"],
            ["EVN", "P03", day(0)],
            ["PID", "1", "", fid(as_id or n), "", "ZZ" + "INVENTED" + chr(65 + n % 26) * 2 + "^" + "TESTCASE", "", born, "U"]]
    pv = ["PV1", "1", "I"] + [""] * 48; pv[7] = (npi + "^CLINICIAN^TEST") if npi else ""; pv[44] = admit
    if not pv1_last: segs.append(pv)
    for k, (d, cpt, dx, units) in enumerate(lines):
        ft = ["FT1", str(k + 1)] + [""] * 30
        ft[4] = day(d) + ("1200" if (n + k) % 2 else ""); ft[5] = day(d + 1); ft[10] = units; ft[19] = "^".join(dx); ft[25] = cpt + "^TEST SERVICE"
        segs.append(ft)
    if pv1_last: segs.append(pv)
    segs += [["DG1", "1", "", lines[0][2][0]], ["IN1", "1", "", "", "TEST PAYER^X"]]
    return ["|".join(x) for x in segs]
def write(ws, name, messages, eol="\r"):
    open(os.path.join(ws, "hl7", name), "wb").write("".join(eol.join(m) + eol for m in messages).encode())
def run(ws, mode="--all", same_chart=None, hl7=None):
    """parse the workspace's HL7 files with the real parser, then run the importer on them -> (register, requests, log).
    same_chart: {feed patient number: the patient whose chart it is}. hl7: the raw files the IMPORTER re-reads, when they are not
    the ones the parser read."""
    pf = os.path.join(ws, "feed_parsed_%s.json" % STAMP)
    subprocess.run([sys.executable, "-I", PARSER, os.path.join(ws, "hl7"), pf], check=True, stdout=subprocess.DEVNULL)
    parsed = json.load(open(pf)); num = lambda m: int(m["pid"][-3:])
    # the ingest keys the chart by name + date of birth; here two feed ids of one invented person share both, so they share the chart
    match = {m["name"].upper().strip() + "|" + m["dob"][:8]: {"resolved": chart((same_chart or {}).get(num(m), num(m)))} for m in parsed}
    json.dump(match, open(os.path.join(ws, "feed_match_%s.json" % STAMP), "w"))
    rf = os.path.join(ws, "registers", "feed_import_%s.json" % STAMP)
    if os.path.exists(rf): os.remove(rf)                              # every run is a first import of its batch
    SENT.clear(); N.update(visit=0, charge=0)
    mod = load(ws, hl7); buf = io.StringIO(); argv = sys.argv; sys.argv = ["claimocity_import.py", mode]
    try:
        with contextlib.redirect_stdout(buf): mod.main()
    finally: sys.argv = argv
    return (json.load(open(rf)) if os.path.exists(rf) else None), list(SENT), buf.getvalue()
attrs = lambda tag, body: dict(re.findall(r'(\w+)="([^"]*)"', re.search(r"<%s [^>]*>" % tag, body).group(0)))
norm = lambda body: re.sub(r"vst\d+", "vst#", body)                   # the visit id is AMD's answer, not the importer's choice
def visits(sent):
    """the write requests of one run, grouped per entered visit and keyed (chart, date, the feed's codes on it, sorted)"""
    out = {}; cur = None
    for body in sent:
        act = re.search(r'action="(\w+)"', body).group(1)
        if act == "addvisit":
            a = attrs("appt", body); cur = {"appt": (a["facility"], a["profile"], a["onhcfa"]), "chart": a["patient"], "requests": [norm(body)], "admit_calls": []}
        elif act == "updvisitwithnewcharges":
            v = attrs("visit", body); ext = re.search(r'<extins hospitalizationfrom="([^"]*)"/>', body)
            lines = [(CPT_OF[p], pos) for p, pos in re.findall(r'<charge id="" [^>]*proccode="([^"]*)"[^>]*? pos="(\d*)"', body) if p in CPT_OF]
            cur.update(facility=v["facility"], profile=v["profile"], onhcfa=v["onhcfa"], pos=[p for c, p in lines], ext=ext.group(1) if ext else None)
            cur["requests"].append(norm(body)); out[(cur["chart"], v["date"], tuple(sorted(c for c, p in lines)))] = cur
        elif act == "updextrainsinfo":
            cur["requests"].append(norm(body)); cur["admit_calls"].append(attrs("extins", body)["hospitalizationfrom"])
    return out
one = lambda vis, n, d, *cpts: vis.get((chart(n), us(day(d)), tuple(sorted(cpts))))
where = lambda v: None if v is None else {k: v[k] for k in ("appt", "facility", "pos", "profile", "ext", "admit_calls")}
def row(reg, n, d, *cpts):
    return next((r for r in reg["created"] if r["pid"] == chart(n) and r["dos"] == us(day(d)) and sorted(c for c in r["cpts"] if c in FEED_CODES) == sorted(cpts)), {})

# ------------------------------------------------------------------ the batch
CCM_OCT = [(-2, "99487", ["I10", "E119"], "1"), (-2, "99489", ["I10"], "1")]     # care management + its add-on, dated 10/31
CCM_NOV = [(0, "99487", ["I10", "E119"], "1"), (0, "99489", ["I10"], "1")]       # ... dated 11/02
ADM1, ADM2 = day(-3), day(4)
SPEC = {
 # A: nursing-building care management (10/31) + a hospital visit (11/02) - patient 1 nursing first, patient 2 hospital first
 "a1_ccm":   ((1, NURS[0], CCM_OCT[::-1], NPI_B, day(-40)), {}),            # add-on line first in the file
 "a1_hosp":  ((1, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, ADM1), {}),
 "a2_hosp":  ((2, HOSPITAL, [(0, "99233", ["N390"], "1")], NPI_A, ADM1), {}),
 "a2_ccm":   ((2, NURS[1], CCM_OCT, NPI_B, day(-40)), {}),
 # A: the same pair inside ONE calendar month - the rule's own exception keeps that care management at 31
 "a7_ccm":   ((7, NURS[0], CCM_NOV, NPI_B, day(-40)), {}),
 "a7_hosp":  ((7, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, ADM1), {}),
 # B: assisted-living care management + a nursing visit (the patient moved to a nursing home) - both orders
 "b3_ccm":   ((3, ALF[0], [(0, "99487", ["I10"], "1")], NPI_A), {}),
 "b3_nurs":  ((3, NURS[0], [(1, "99309", ["F0390"], "1")], NPI_B, day(1)), {}),
 "b4_nurs":  ((4, NURS[1], [(1, "99308", ["F0390"], "1")], NPI_B, day(1)), {}),
 "b4_ccm":   ((4, ALF[1], [(0, "99487", ["I10"], "1")], NPI_A), {}),
 # D: one building, three hospital days: two clinicians, then a second admission (in the second message PV1 stands after the charge line)
 "d6_day0":  ((6, HOSPITAL, [(0, "99223", ["N390"], "1")], NPI_A, ADM1), {}),
 "d6_day1":  ((6, HOSPITAL, [(1, "99232", ["N390"], "1")], NPI_B, ADM1), {'pv1_last': True}),
 "d6_day5":  ((6, HOSPITAL, [(5, "99223", ["N390"], "1")], NPI_A, ADM2), {}),
 # H: nursing visits a month apart in ONE batch - from two nursing buildings (21), from the hospital building and then a nursing
 # building (22: the rehab-unit pattern), and from the same building twice (23)
 "h21_one":  ((21, NURS[0], [(-30, "99309", ["F0390"], "1")], NPI_B), {}),
 "h21_two":  ((21, NURS[1], [(0, "99309", ["F0390"], "1")], NPI_B), {}),
 "h22_hosp": ((22, HOSPITAL, [(-30, "99309", ["F0390"], "1")], NPI_A), {}),
 "h22_nurs": ((22, NURS[0], [(0, "99309", ["F0390"], "1")], NPI_B), {}),
 "h23_one":  ((23, NURS[1], [(-30, "99309", ["F0390"], "1")], NPI_B), {}),
 "h23_two":  ((23, NURS[1], [(0, "99309", ["F0390"], "1")], NPI_B), {}),
 # K: same patient, same date, same FIRST code, another code list, two buildings
 "k25_alf":  ((25, ALF[0], [(-2, "99487", ["I10"], "1")], NPI_A), {}),
 "k25_nurs": ((25, NURS[1], CCM_OCT, NPI_B), {}),
}
M = {k: message(*a, **kw) for k, (a, kw) in SPEC.items()}
ORDER = list(M)
# C: the same patient, date and code from two buildings. Patient 5: the nursing copy is read last; patient 9: the assisted-living copy,
# which stands in the second file (files are read in name order, by the parser and by the importer alike)
C = {"c5_hosp": message(5, HOSPITAL, [(1, "99232", ["N390"], "1")], NPI_A, ADM1),
     "c5_alf":  message(5, ALF[0], [(-2, "99487", ["I10"], "1")], NPI_A),
     "c5_nurs": message(5, NURS[0], [(-2, "99487", ["I10"], "1")], NPI_B),
     "c9_nurs": message(9, NURS[1], [(-2, "99487", ["I10"], "1")], NPI_B),
     "c9_alf":  message(9, ALF[1], [(-2, "99487", ["I10"], "1")], NPI_A)}
# R: a hospital message sent twice - the second copy corrects the admission date - while another message of the patient is read last
R = [message(8, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, day(-9)), message(8, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, ADM1),
     message(8, NURS[0], [(2, "99309", ["F0390"], "1")], NPI_B, day(2))]
APART = (chart(5), chart(9), chart(8))                                # the charts of C and R: not every visit there is one message read once
ws = workspace("batch")
write(ws, day(0) + "aaaa0000.hl7", [M[k] for k in ORDER[:10]] + [C[k] for k in ("c5_hosp", "c5_alf", "c5_nurs", "c9_nurs")] + R, eol="\r")
write(ws, day(1) + "bbbb0000.hl7", [M[k] for k in ORDER[10:]] + [C["c9_alf"]], eol="\r\n")       # patient 9's twins are in two files: the later file is read last
reg, sent, dry_log = run(ws, "--dry")
check("dry run: reads only - no visit, charge or admission-date request, no register", reg is None and not [b for b in sent if re.search(r'action="(addvisit|updvisitwithnewcharges|updextrainsinfo)"', b)])
reg, sent, log = run(ws)
V = visits(sent)
check("every message is entered once (26 visits; each pair of twins in C and the message sent twice in R are one visit) and nothing failed",
      len(reg["created"]) == 26 and len(V) == 26 and not reg["failed"], (len(reg["created"]), len(V), reg["failed"]))
check("every visit has a facility: the building is read from the raw message as the facility table knows it", all(r["fac"] for r in reg["created"]), [r["fac"] for r in reg["created"]])
# A
for n, nb, hcpt in ((1, NURS[0], "99232"), (2, NURS[1], "99233")):
    c = one(V, n, -2, "99487", "99489"); h = one(V, n, 0, hcpt); rc = row(reg, n, -2, "99487", "99489")
    check("A%d nursing-building care management of a patient who also has a hospital visit: under the NURSING building, 32 by the rule" % n,
          c and c["facility"] == FACID(nb) and c["appt"][0] == FACID(nb) and c["pos"] == ["32", "32"] and not rc.get("pos_err"), (where(c), rc))
    check("A%d that care management: its own clinician, no admission date, onhcfa 0" % n, c and c["profile"] == PROF_B and c["ext"] is None and not c["admit_calls"] and c["onhcfa"] == "0", where(c))
    check("A%d the hospital visit: under the hospital at 21, its own clinician and ITS admission date (visit + updextrainsinfo)" % n,
          h and h["facility"] == FACID(HOSPITAL) and h["appt"][0] == FACID(HOSPITAL) and h["pos"] == ["21"] and h["profile"] == PROF_A and h["ext"] == us(ADM1) and h["admit_calls"] == [us(ADM1)] and h["onhcfa"] == "1", where(h))
c = one(V, 7, 0, "99487", "99489"); rc = row(reg, 7, 0, "99487", "99489"); h = one(V, 7, 0, "99232")
check("A7 care management and hospital visit in ONE calendar month: under the nursing building, kept at 31 by the RULE (applied, not skipped)",
      c and c["facility"] == FACID(NURS[0]) and c["pos"] == ["31", "31"] and not rc.get("pos_err") and h and h["facility"] == FACID(HOSPITAL) and h["pos"] == ["21"], (where(c), rc, where(h)))
# B
for n, ab, nb, ncpt in ((3, ALF[0], NURS[0], "99309"), (4, ALF[1], NURS[1], "99308")):
    c = one(V, n, 0, "99487"); v = one(V, n, 1, ncpt); rv = row(reg, n, 1, ncpt)
    check("B%d assisted-living care management of a patient who also has a nursing visit: at the assisted-living facility, 13" % n, c and c["facility"] == FACID(ab) and c["pos"] == ["13"] and c["profile"] == PROF_A, where(c))
    check("B%d the nursing visit: under the nursing building, the rule applied (the first nursing visit on the chart is 31)" % n,
          v and v["facility"] == FACID(nb) and v["pos"] == ["31"] and v["profile"] == PROF_B and not rv.get("pos_err"), (where(v), rv))
# C
t5 = one(V, 5, -2, "99487"); r5 = row(reg, 5, -2, "99487"); h5 = one(V, 5, 1, "99232"); t9 = one(V, 9, -2, "99487"); r9 = row(reg, 9, -2, "99487")
check("C the same patient + date + code from two buildings is ONE visit, in the building of the copy read last",
      t5 and t5["facility"] == FACID(NURS[0]) and t9 and t9["facility"] == FACID(ALF[1]) and t9["pos"] == ["13"], (where(t5), where(t9)))
check("C ... in a nursing building it stays at the feed's 31 and the rule says it was not applied", t5 and t5["pos"] == ["31"] and bool(r5.get("pos_err")), (where(t5), r5))
check("C ... and both register rows say the visit is not the message's own reading", r5.get("msg_own") is False and r9.get("msg_own") is False, (r5, r9))
check("C the same patient's other message keeps its own building and admission date", h5 and h5["facility"] == FACID(HOSPITAL) and h5["pos"] == ["21"] and h5["ext"] == us(ADM1), where(h5))
# R
h8 = one(V, 8, 0, "99232"); n8 = one(V, 8, 2, "99309")
check("R a hospital message sent twice with a corrected admission date, another message of the patient read last: ONE visit, with the date of its own LAST copy",
      h8 and h8["facility"] == FACID(HOSPITAL) and h8["profile"] == PROF_A and h8["ext"] == us(ADM1) and h8["admit_calls"] == [us(ADM1)]
      and n8 and n8["facility"] == FACID(NURS[0]) and n8["profile"] == PROF_B and n8["ext"] is None, (where(h8), where(n8), "the first copy said " + us(day(-9)), "the other message says " + us(day(2))))
# D
d0, d1, d5 = one(V, 6, 0, "99223"), one(V, 6, 1, "99232"), one(V, 6, 5, "99223")
check("D one building, two clinicians: each hospital day under the clinician of ITS message", d0 and d1 and d5 and [d0["profile"], d1["profile"], d5["profile"]] == [PROF_A, PROF_B, PROF_A], [where(x) for x in (d0, d1, d5)])
check("D one building, two admissions: each visit carries the admission date of ITS message", d0 and d1 and d5 and [d0["ext"], d1["ext"], d5["ext"]] == [us(ADM1), us(ADM1), us(ADM2)]
      and d5["admit_calls"] == [us(ADM2)], [where(x) for x in (d0, d1, d5)])
# H
h1, h2 = one(V, 21, -30, "99309"), one(V, 21, 0, "99309"); rh2 = row(reg, 21, 0, "99309")
check("H a nursing visit a month after one in ANOTHER nursing building, both in this batch: a new admission here - 31, never 'the monthly visit'",
      h1 and h1["facility"] == FACID(NURS[0]) and h2 and h2["facility"] == FACID(NURS[1]) and h2["pos"] == ["31"] and not rh2.get("pos_err"), (where(h2), rh2))
h1, h2 = one(V, 22, -30, "99309"), one(V, 22, 0, "99309"); rh2 = row(reg, 22, 0, "99309")
check("H ... the same after a nursing visit sent from the HOSPITAL building: that one stays where the feed put it (21), this one is 31",
      h1 and h1["facility"] == FACID(HOSPITAL) and h1["pos"] == ["21"] and h2 and h2["facility"] == FACID(NURS[0]) and h2["pos"] == ["31"] and not rh2.get("pos_err"), (where(h1), where(h2), rh2))
h2 = one(V, 23, 0, "99309"); rh2 = row(reg, 23, 0, "99309")
check("H ... and in the SAME building the second one is the monthly visit (32)", h2 and h2["facility"] == FACID(NURS[1]) and h2["pos"] == ["32"] and not rh2.get("pos_err"), (where(h2), rh2))
# K
k1, k2 = one(V, 25, -2, "99487"), one(V, 25, -2, "99489")
check("K same patient, date and first code under two buildings with different code lists are told apart", k1 and k1["facility"] == FACID(ALF[0]) and k1["pos"] == ["13"] and k2 and k2["facility"] == FACID(NURS[1]), (where(k1), where(k2)))
own = [r for r in reg["created"] if r["pid"] not in APART]
check("apart from the twins of C and the message sent twice in R, every visit is the reading of its own message and the rule was applied where it has a say",
      len(own) == 21 and not [r for r in own if r.get("msg_own") is False or r.get("pos_err")], [(r["pid"], r.get("msg_own"), r.get("pos_err")) for r in own if r.get("msg_own") is False or r.get("pos_err")])

# ------------------------------------------------------------------ E: every message under its own feed patient id, same charts
ws = workspace("own_ids")
split = {k: 100 + i for i, k in enumerate(ORDER)}                    # message -> a feed patient id of its own (101, 102, ...)
write(ws, day(0) + "cccc0000.hl7", [message(*a, as_id=split[k], **kw) for k, (a, kw) in SPEC.items()])
people = {split[k]: int(re.match(r"[a-z](\d+)_", k).group(1)) for k in ORDER}
V2 = visits(run(ws, same_chart=people)[1])
keys = [k for k in V if k[0] not in APART]
check("E every message under a feed patient id of its own (same charts): the same 21 visits, each sent byte for byte the same",
      len(keys) == 21 and sorted(keys) == sorted(V2) and all(V[k]["requests"] == V2[k]["requests"] for k in keys), [k for k in keys if k not in V2 or V[k]["requests"] != V2[k]["requests"]] or (len(keys), len(V2)))

# ------------------------------------------------------------------ F: before / after, for patients whose messages agree
# Until 11/10/2026 the importer took building, clinician and admission date from the feed PATIENT, and it still does for a message
# the raw files do not hold. So one batch is entered twice: with the raw files the parser read (every visit from its own message)
# and with raw files that hold ONE other message per patient (every visit from the patient's values, the way it was before).
# For a patient whose messages agree on building, clinician and admission date both ways must send the same bytes.
AGREE = {
 31: (HOSPITAL, NPI_A, ADM1, [[(0, "99223", ["N390"], "1")], [(1, "99232", ["N390"], "1")], [(2, "99239", ["N390"], "1")]]),      # one hospital stay
 32: (NURS[0], NPI_B, "", [[(-30, "99309", ["F0390"], "1")], [(0, "99309", ["F0390"], "1")], CCM_OCT]),                          # nursing visits + care management
 33: (ALF[0], NPI_B, "", [[(0, "99344", ["I10"], "1")], CCM_NOV[:1]]),                                                          # assisted living
 34: (NURS[1], NPI_A, "", [[(1, "99308", ["F0390"], "1")], [(3, "99316", ["F0390"], "1")]]),                                     # a short nursing stay
}
ws = workspace("agree_own_message"); ws2 = workspace("agree_patient_values")       # a workspace each: nothing one run leaves behind reaches the other
other = os.path.join(ws2, "hl7_one_other_message_per_patient"); os.makedirs(other)
for w in (ws, ws2): write(w, day(0) + "dddd0000.hl7", [message(n, b, lines, npi, adm) for n, (b, npi, adm, msgs) in AGREE.items() for lines in msgs])
open(os.path.join(other, day(0) + "eeee0000.hl7"), "wb").write("".join("\r".join(message(n, b, [(-300, "99487", ["I10"], "1")], npi, adm)) + "\r"
                                                                    for n, (b, npi, adm, msgs) in AGREE.items()).encode())
reg1, sent1, _ = run(ws); V1 = visits(sent1)
reg2, sent2, _ = run(ws2, hl7=other); V2 = visits(sent2)
check("F the batch of agreeing patients is entered in full both ways (10 visits, nothing failed)",
      len(V1) == 10 and len(V2) == 10 and not reg1["failed"] and not reg2["failed"], (len(V1), len(V2), reg1["failed"], reg2["failed"]))
check("F first way: every visit is the reading of its own message; second way: none is (the patient's values, as before 11/10/2026)",
      all(r.get("msg_own") is True for r in reg1["created"]) and all(r.get("msg_own") is False for r in reg2["created"]),
      ([r.get("msg_own") for r in reg1["created"]], [r.get("msg_own") for r in reg2["created"]]))
check("F a patient whose messages agree: the SAME BYTES are sent either way (single-building output unchanged)",
      sorted(V1) == sorted(V2) and all(V1[k]["requests"] == V2[k]["requests"] for k in V1), [k for k in V1 if k not in V2 or V1[k]["requests"] != V2[k]["requests"]])
v = one(V2, 32, 0, "99309")
check("F ... and the rule is applied either way: the monthly nursing visit is 32 also from the patient's values, nothing stepped aside",
      v and v["pos"] == ["32"] and not [r for r in reg1["created"] + reg2["created"] if r.get("pos_err")], (where(v), [r.get("pos_err") for r in reg2["created"]]))

os.chdir(ROOT)
print("\n%d failure(s)" % len(FAILS) + (": " + "; ".join(FAILS) if FAILS else " - every visit is entered from its own feed message, through the real parser"))
sys.exit(1 if FAILS else 0)
