#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the feed's patient-identity rule, 11/25/2026)
# Decides: nothing. Proves, with no AdvancedMD and no network, the rule that puts a Claimocity feed patient on the RIGHT chart and never
#   makes a second one (William 11/25/2026, after the feed twice made a second chart for a patient whose own chart was already there;
#   William 11/9/2026: "if a duplicate chart shows up with visits in it just put the visits in the proper chart"). Two layers:
#   1. the rule itself, scripts/helpers/feed_identity.py - pure functions: what a real birth date is, what a slip between two dates is,
#      how names, Social Security numbers and member numbers are compared, which chart of a group is the live one, and decide(), rules
#      1 to 9 in their order with both sides of every line (a slip against far, three letters against the full first name, a number
#      equal / different / junk / four digits, a member number with and without its prefix, one date against two, the placeholder on
#      either side, an empty date, a suffix in the last name) - in every order AdvancedMD could list the charts;
#   2. the three steps that use it, run INSIDE this process with stand-in amd / txh / add_ins modules (never started as programs, the
#      real amd never loads): claimocity_match.py, claimocity_resolve.py, claimocity_newcharts.py - the two charts of 11/17 (the feed one
#      digit off: the live chart, no new one), the six charts of 11/8 (the feed sent the placeholder: the live chart, no new one), a new
#      patient (one chart, the real date), a patient with no date (the placeholder date for the patient AND the responsible party, never
#      an empty one), four "Duplicate chart" answers in a row (the fifth number is used), one Claimocity id with two dates in one batch
#      (decided once, one chart), the name lookups whatever the spelling of the last name (the stand-in takes a lookup the strict way:
#      SQL LIKE, 50 charts at most), a list AdvancedMD cuts short (nobody is then matched by the name alone), and what the steps must
#      never do: decide on a half-read, make a chart on an older step's word, write a name, a date, a Social Security number or a
#      member number into a register, a printed line or one of the fields the driver copies.
#   The stand-in AdvancedMD refuses every action a step is not supposed to send (a stray write fails the test) and counts addpatient.
# Every name, birth date, Social Security number and member number here is invented, and each is put together at run time (lf, ymd, the
#   + signs) so that no such value sits in this file as a literal: tools/mirror/phi_gate.py scrubs this file like any other before a
#   commit - the last section checks that it finds nothing to change here or in the four helpers.
# Run: python3 tools/selftest/test_feed_identity.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, importlib.util, io, re, contextlib, random, itertools, datetime
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True      # this test leaves no __pycache__ beside the helpers it loads
# THIS SELF-TEST NEVER REACHES ADVANCEDMD OR ANY OTHER HOST (the same three locks as tools/selftest/test_pos_rule.py): the network is shut
# for this process before anything else is loaded, no helper is started as a program, and a helper that talks to AdvancedMD is only ever
# run inside this process with stand-in modules (run_inside refuses to run one whose modules are not all stand-ins).
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
AMD_MODULES = ("amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update", "add_ins", "stedi", "elig_amd", "requests")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
H = os.path.join(ROOT, "scripts", "helpers")
STEPS = ("claimocity_match.py", "claimocity_resolve.py", "claimocity_newcharts.py")
FAILS = []; COUNT = [0]
def check(name, cond, extra=""):
    COUNT[0] += 1
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:600]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
def T(name, fn):
    """One check whose test may raise: an exception is a FAIL that says so (while feed_identity.py is missing every check of the rule fails this way)."""
    try: r = fn()
    except Exception as e: check(name, False, "%s: %s" % (type(e).__name__, e)); return
    ok, extra = r if isinstance(r, tuple) else (r, r)
    check(name, bool(ok), extra)
def loads(src):
    """The names a piece of Python loads with import / from, first name of each (import a.b as c -> a)."""
    out_ = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out_.add(n)
    return out_
def read(name):
    try: return open(os.path.join(H, name)).read()
    except OSError: return ""
def load(name):
    """A PURE helper (no AdvancedMD module among its imports), loaded by its path - scripts/helpers is never put on the search path."""
    src = read(name + ".py")
    if loads(src) & set(AMD_MODULES): raise RuntimeError("%s.py loads %s - not a pure helper, not loaded" % (name, sorted(loads(src) & set(AMD_MODULES))))
    spec = importlib.util.spec_from_file_location(name, os.path.join(H, name + ".py")); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
class _Missing:
    def __init__(s, why): s.why = why
    def __getattr__(s, n): raise RuntimeError("scripts/helpers/feed_identity.py did not load (%s)" % s.why)
try: FI = load("feed_identity"); FI_ERR = ""
except Exception as e: FI_ERR = "%s: %s" % (type(e).__name__, e); FI = _Missing(FI_ERR)
check("scripts/helpers/feed_identity.py is there and loads", FI_ERR == "", FI_ERR)
_src = read("feed_identity.py")
check("feed_identity.py is pure: it loads only re / datetime / unicodedata, opens no file, prints nothing, starts nothing",
      _src != "" and loads(_src) <= {"re", "datetime", "unicodedata"} and not re.search(r"\bopen\(|\bprint\(|\bos\.|subprocess|socket|requests|urllib|\bamd\b\.", _src), sorted(loads(_src)))

# ---- invented values, each put together here --------------------------------------------------------------------------------------
def lf(last, first): return last + "," + first          # AdvancedMD's own form
def cf(last, first): return last + ", " + first         # the feed's form (the parser writes the PID name that way)
def ymd(y, m, d): return "%04d%02d%02d" % (y, m, d)
def mdy(d8): return "%s/%s/%s" % (d8[4:6], d8[6:], d8[:4])
def iso(d8): return "%s-%s-%s" % (d8[:4], d8[4:6], d8[6:])
def dash(s): return s[:3] + "-" + s[3:5] + "-" + s[5:]
TODAY = ymd(2026, 11, 25)
P8 = ymd(1900, 1, 1); P_MDY = "01/01/" + "1900"            # the placeholder Claimocity sends, and the date a chart is written with instead of none
ZO, QU, WE, TH, YA = "ZORNDIKE", "QUAGGLEBY", "WEXLOWE", "THRUMBLECK", "YARROWBIE"
S1 = "517" + "20" + "3391"; S2 = "517" + "20" + "3392"; S3 = "448" + "61" + "9027"
M1 = "ZQ" + "81726354"; M2 = "HK" + "40917733"; PFX = "XJB"
FID = "5f0" + "0" * 18 + "a17"; FID2 = "5f0" + "0" * 18 + "b28"; FID3 = "5f0" + "0" * 18 + "c39"; FID4 = "5f0" + "0" * 18 + "d40"; FID5 = "5f0" + "0" * 18 + "e51"
B = ymd(1941, 3, 12); B_DIGIT = ymd(1941, 3, 13); B_SWAP = ymd(1941, 3, 21); B_MD = ymd(1941, 12, 3); FARD = ymd(1952, 9, 27); B2 = ymd(1938, 7, 4)
NONE_DATES = ("", P8, "00000000", ymd(1941, 2, 30))

# =====================================================================================================================================
# 1. THE RULE (feed_identity.py)
# =====================================================================================================================================
t = TODAY
T("a real birth date: eight digits, a day of the calendar", lambda: FI.real_dob(B, t) is True and FI.real_dob(ymd(1940, 2, 29), t) is True)
T("... empty, nothing, the placeholder, zeros, seven or nine digits, a letter among them - NO BIRTH DATE", lambda: [FI.real_dob(x, t) for x in ("", None, P8, "00000000", B[:7], B + "0", B[:4] + "O" + B[5:], " ")] == [False] * 8)
T("... a date that does not exist (30 February, 29 February of a common year, month 13, day 0) - NO BIRTH DATE", lambda: [FI.real_dob(x, t) for x in (ymd(1941, 2, 30), ymd(1941, 2, 29), ymd(1941, 13, 1), ymd(1941, 4, 0))] == [False] * 4)
T("... year 1901 or later: the last day of 1900 is not real, the first day of 1901 is (seen from 2020, inside the 120 years)", lambda: (FI.real_dob(ymd(1900, 12, 31), ymd(2020, 1, 1)), FI.real_dob(ymd(1901, 1, 1), ymd(2020, 1, 1))) == (False, True))
T("... not after today: today is real, tomorrow is not", lambda: (FI.real_dob(t, t), FI.real_dob(ymd(2026, 11, 26), t)) == (True, False))
T("... not more than 120 years ago: 120 years ago to the day is real, the day before is not", lambda: (FI.real_dob(ymd(1906, 11, 25), t), FI.real_dob(ymd(1906, 11, 24), t)) == (True, False))
T("... seen from a 29 February the rule still answers", lambda: FI.real_dob(B, ymd(2020, 2, 29)) is True and FI.real_dob(ymd(1904, 2, 29), ymd(2024, 2, 29)) is True and FI.real_dob(ymd(1904, 2, 28), ymd(2024, 2, 29)) is False)
def _raises(fn):
    try: fn()
    except ValueError: return True
    except Exception as e: return (False, "%s: %s" % (type(e).__name__, e))
    return False
T("... today itself must be a date (a wrong today is an error, never a quiet 'not real')", lambda: _raises(lambda: FI.real_dob(B, "")) is True and _raises(lambda: FI.real_dob(B, ymd(2026, 2, 30))) is True)

T("the four kinds of slip are four different fixed words with no digit in them", lambda: len({FI.SLIP_DIGIT, FI.SLIP_SWAP, FI.SLIP_MONTH_DAY, FI.SLIP_DAY}) == 4 and all(isinstance(k, str) and k and not re.search(r"\d", k) for k in (FI.SLIP_DIGIT, FI.SLIP_SWAP, FI.SLIP_MONTH_DAY, FI.SLIP_DAY)))
T("a slip (a): one digit differs - in the day, the month, the decade (twenty years off)", lambda: [FI.slip(B, x) for x in (B_DIGIT, ymd(1941, 8, 12), ymd(1961, 3, 12), ymd(1941, 3, 22))] == [FI.SLIP_DIGIT] * 4)
T("a slip (b): two neighbouring digits swapped - in the day, across month and day, in the year", lambda: [FI.slip(B, B_SWAP), FI.slip(ymd(1941, 1, 20), ymd(1941, 10, 20)), FI.slip(B, ymd(1914, 3, 12))] == [FI.SLIP_SWAP] * 3)
T("a slip (c): month and day swapped", lambda: FI.slip(B, B_MD) == FI.SLIP_MONTH_DAY and FI.slip(ymd(1941, 4, 11), ymd(1941, 11, 4)) == FI.SLIP_MONTH_DAY)
T("a slip (d): one day apart, across a month end and a year end", lambda: FI.slip(ymd(1941, 1, 31), ymd(1941, 2, 1)) == FI.SLIP_DAY and FI.slip(ymd(1940, 12, 31), ymd(1941, 1, 1)) == FI.SLIP_DAY)
T("... one kind per pair, the first that fits (one digit AND one day apart is 'one digit'), and the order of the two dates does not matter",
  lambda: FI.slip(B, B_DIGIT) == FI.SLIP_DIGIT and all(FI.slip(a, b) == FI.slip(b, a) for a, b in ((B, B_DIGIT), (B, B_SWAP), (B, B_MD), (B, FARD), (ymd(1941, 1, 31), ymd(1941, 2, 1)))))
T("FAR is no slip: two digits, another month and day, eleven days, another year, two days apart across a month end", lambda: [FI.slip(B, x) for x in (ymd(1941, 3, 25), ymd(1941, 7, 30), ymd(1941, 3, 23), FARD, ymd(1943, 3, 14))] + [FI.slip(ymd(1941, 1, 31), ymd(1941, 2, 2))] == [""] * 6)
T("equal dates are not a slip", lambda: FI.slip(B, B) == "")
T("never a slip with the placeholder, an empty date or a date that does not exist (the placeholder against a real date one digit away is still no slip)",
  lambda: [FI.slip(P8, ymd(1910, 1, 1)), FI.slip(ymd(1910, 1, 1), P8), FI.slip("", B), FI.slip(B, None), FI.slip(ymd(1941, 2, 30), ymd(1941, 2, 20)), FI.slip("00000000", "00000001")] == [""] * 6)

T("last name key: upper case, letters only (apostrophe, hyphen, spaces, accents dropped)", lambda: (FI.last_key("o'Zimbra-Kolt"), FI.last_key(" Van  Dekoltz "), FI.last_key("Peñalba")) == ("OZIMBRAKOLT", "VANDEKOLTZ", "PENALBA"))
T("... a trailing suffix word is dropped: JR, SR, II, III, IV, V - any case, with or without the period", lambda: [FI.last_key(ZO + " " + s) for s in ("JR", "Sr.", "II", "iii", "IV", "V", "jr.")] == [ZO] * 7)
T("... but not a suffix that is the whole name, the first word, or the end of a longer word", lambda: (FI.last_key("V"), FI.last_key("JR " + ZO), FI.last_key(ZO + "JR"), FI.last_key(ZO + " VI")) == ("V", "JR" + ZO, ZO + "JR", ZO + "VI"))
T("split_name: AdvancedMD's form and the feed's form; a name without a comma has no first name", lambda: (FI.split_name(lf(ZO, "MARY K")), FI.split_name(cf(ZO, "MARY")), FI.split_name(" " + ZO + " ")) == ((ZO, "MARY K"), (ZO, "MARY"), (ZO, "")))
NK = lambda fl, ff, cl, cf_: FI.name_kind(fl, ff, cl, cf_)
T("NAME CANDIDATE: the same last name and the first three letters of the first name", lambda: NK(ZO, "MARTHA", ZO, "MARY") == "name" and NK(ZO, "Mar", ZO, "MARIGOLD") == "name")
T("FULL-NAME candidate: the first word of the first name is the same (a middle name or initial does not matter)", lambda: NK(ZO, "MARY", ZO, "MARY K") == "full" and NK(ZO, "Mary Ann", ZO, "MARY") == "full" and NK(ZO, "MARY", ZO, "mary") == "full")
T("FULL-NAME candidate: the shorter first word has four letters or more and begins the longer one (MARY / MARYANN)", lambda: NK(ZO, "MARY", ZO, "MARYANN") == "full" and NK(ZO, "MARYANN", ZO, "MARY") == "full")
T("... three letters do not make that (ANN / ANNABEL is a name candidate only)", lambda: NK(ZO, "ANN", ZO, "ANNABEL") == "name" and NK(ZO, "ANNABEL", ZO, "ANN") == "name")
T("... JO ANN / JOANN: the first words are JO and JOANN - a name candidate only", lambda: NK(ZO, "JO ANN", ZO, "JOANN") == "name")
T("another first name under the same last name is 'surname' (rule 3 only); another last name is nothing", lambda: NK(ZO, "MARY", ZO, "ELSPETH") == "surname" and NK(ZO, "MARY", QU, "MARY") == "" and NK(ZO, "MARY", ZO + "SON", "MARY") == "")
T("a first name of two letters is a candidate only of the same two letters (JO / JOSEPHINE share no three letters)", lambda: NK(ZO, "JO", ZO, "JO") == "full" and NK(ZO, "JO", ZO, "JOSEPHINE") == "surname")
T("the suffix and the punctuation of the last name do not matter on either side", lambda: NK(ZO + " JR", "MARY", ZO, "MARY") == "full" and NK("O'" + ZO, "MARY", "O " + ZO + " III", "MARY") == "full")
T("name_candidate / full_name_candidate say the same in two words", lambda: (FI.name_candidate(ZO, "MARTHA", ZO, "MARY"), FI.full_name_candidate(ZO, "MARTHA", ZO, "MARY"), FI.name_candidate(ZO, "MARY", ZO, "MARYANN"), FI.full_name_candidate(ZO, "MARY", ZO, "MARYANN"),
                                                                                  FI.name_candidate(ZO, "MARY", ZO, "ELSPETH"), FI.name_candidate(ZO, "MARY", QU, "MARY")) == (True, False, True, True, False, False))
T("no last name, or no first name, on either side is never a name candidate", lambda: NK("", "MARY", "", "MARY") == "" and NK(ZO, "", ZO, "MARY") == "surname" and NK(ZO, "MARY", ZO, "") == "surname")

T("Social Security number: nine digits, with or without the dashes", lambda: FI.ssn_key(dash(S1)) == S1 and FI.ssn_key(S1) == S1 and FI.ssn_key(" " + S1 + " ") == S1)
T("... junk is never a number: all one digit, one to nine in a row, starting 000 / 666 / 9", lambda: [FI.ssn_key(x) for x in ("1" * 9, "7" * 9, "".join(str(i) for i in range(1, 10)), "000" + S1[3:], "666" + S1[3:], "9" + S1[1:], "900" + S1[3:])] == [""] * 7)
T("... eight or ten digits, empty, nothing - no number", lambda: [FI.ssn_key(x) for x in (S1[:8], S1 + "1", "", None)] == [""] * 4)
T("the last four: only when the value shows exactly four digits", lambda: (FI.ssn4_key("***-**-" + S1[5:]), FI.ssn4_key("xxx-xx-" + S1[5:]), FI.ssn4_key(S1[5:]), FI.ssn4_key(S1), FI.ssn4_key(""), FI.ssn4_key("0000")) == (S1[5:], S1[5:], S1[5:], "", "", ""))
EV = lambda feed, chart: FI.evidence(feed, chart)
T("evidence ssn: nine digits on both sides, equal", lambda: EV({"ssn": dash(S1)}, {"ssn": S1}) == (["ssn"], False))
T("nine digits on both sides that DIFFER: proof of two people - no evidence, 'contra'", lambda: EV({"ssn": S1}, {"ssn": dash(S2)}) == ([], True))
T("junk on either side is neither evidence nor proof", lambda: EV({"ssn": "1" * 9}, {"ssn": "1" * 9}) == ([], False) and EV({"ssn": S1}, {"ssn": "000" + S2[3:]}) == ([], False) and EV({"ssn": ""}, {"ssn": S1}) == ([], False))
T("evidence ssn4: a side shows only four digits and the last four are equal", lambda: EV({"ssn": S1}, {"ssn": "xxx-xx-" + S1[5:]}) == (["ssn4"], False) and EV({"ssn": S1[5:]}, {"ssn": dash(S1)}) == (["ssn4"], False))
T("... four digits that differ from the other side's last four: two people as well (the safest reading - no chart by name alone)", lambda: EV({"ssn": S1}, {"ssn": "xxx-xx-" + S3[5:]}) == ([], True))
T("the lookup row's masked number beside the chart's full one: the full one counts", lambda: EV({"ssn": S1}, {"ssn": ["***-**-" + S1[5:], dash(S1)]}) == (["ssn"], False))
T("a side that carries two different nine-digit numbers is not used at all", lambda: EV({"ssn": [S1, S2]}, {"ssn": S1}) == ([], False))

T("member number key: upper case, letters and digits only", lambda: FI.member_key(" " + M1[:2].lower() + "-" + M1[2:5] + " " + M1[5:] + " ") == M1)
T("member numbers equal after that", lambda: FI.member_equal(M1.lower(), M1[:2] + "-" + M1[2:]) is True and FI.member_equal(M1, M2) is False)
T("... also when a leading three-letter prefix is dropped from either side", lambda: FI.member_equal(PFX + M1, M1) is True and FI.member_equal(M1, PFX.lower() + "-" + M1) is True)
T("... but not under two different prefixes, and not a prefix of two or of four letters", lambda: (FI.member_equal(PFX + M1, "QRT" + M1), FI.member_equal(PFX[:2] + M1, M1), FI.member_equal(PFX + "K" + M1, M1)) == (False, False, False))
T("... at least eight characters: seven are not enough, also after the prefix is dropped; eight are", lambda: (FI.member_equal(M1[:7], M1[:7]), FI.member_equal(PFX + M1[:7], M1[:7]), FI.member_equal(M1[:8], M1[:8]), FI.member_equal(PFX + M1[:8], M1[:8])) == (False, False, True, True))
T("... letters only, or one character over and over, is no member number", lambda: (FI.member_equal("UNKNOWNID", "UNKNOWNID"), FI.member_equal("0" * 10, "0" * 10), FI.member_equal("", "")) == (False, False, False))
def in1(v49="", v36=""):
    s = ["IN1"] + [""] * 49; s[49] = v49; s[36] = v36; return s
def _old_in1():
    m = re.search(r"(?m)^def in1_member\(s\):\n(?:    .*\n)+", read("claimocity_newcharts.py")); ns = {"re": re}; exec(m.group(0), ns); return ns["in1_member"]
_IN1 = [in1(M1), in1("", M1), in1(S1, M1), in1(dash(S1), ""), in1("+", ""), in1("12345", ""), in1(" " + M2 + " ", M1), in1("AB 12 345 678", ""), in1(M1[:6], ""), ["IN1", "1"], in1("A" * 21, M2)]
T("the feed's member number is the one claimocity_newcharts.py already reads: IN1-49, else IN1-36, never a value shaped like a Social Security number, never junk",
  lambda: ([FI.in1_member(s) for s in _IN1] == [_old_in1()(s) for s in _IN1] and [FI.in1_member(s) for s in _IN1[:5]] == [M1, M1, M1, "", ""], [FI.in1_member(s) for s in _IN1]))
T("evidence member: a feed member number equals a subscriber number of one of the chart's plans", lambda: EV({"members": [M2, PFX + M1]}, {"members": ["", M1.lower()]}) == (["member"], False) and EV({"members": [M1]}, {"members": [M2]}) == ([], False))
T("evidence mrn: the chart's additional number is this Claimocity id, in either case", lambda: EV({"id": FID}, {"mrn": FID.upper()}) == (["mrn"], False) and EV({"ids": [FID2, FID]}, {"mrn": FID}) == (["mrn"], False))
T("... not another id, not an empty one, not a short number that is no Claimocity id", lambda: EV({"id": FID}, {"mrn": FID2}) == ([], False) and EV({"id": FID}, {"mrn": ""}) == ([], False) and EV({"id": "1234"}, {"mrn": "1234"}) == ([], False) and EV({"id": ""}, {"mrn": ""}) == ([], False))
T("all the evidence of one chart, strongest first: mrn, ssn, member (ssn4 only where a side shows four digits)", lambda: EV({"id": FID, "ssn": S1, "members": [M1]}, {"mrn": FID, "ssn": S1, "members": [M1]}) == (["mrn", "ssn", "member"], False))
T("AdvancedMD's date forms: month/day/year with or without the leading zeros, and the ISO form", lambda: (FI.amd_dob(mdy(B)), FI.amd_dob("3/12/" + B[:4]), FI.amd_dob(iso(B) + "T00:00:00"), FI.amd_dob(""), FI.amd_dob(None), FI.amd_dob("//")) == (B, B, B, "", "", ""))

def ch(n, d8="", last="", n_chg=0): return {"id": "pat%d" % n, "dob": d8, "last_dos": last, "charges": n_chg}
def live(cs): return FI.live_chart(cs, TODAY)["id"]
def every_order(cs, want): return all(live(list(p)) == want for p in itertools.permutations(cs))
T("the live chart: a real birth date comes before none, whatever the charges say", lambda: every_order([ch(1, "", ymd(2026, 11, 1), 9), ch(2, B, ymd(2020, 1, 1), 1), ch(3, P8, ymd(2026, 11, 20), 30)], "pat2"))
T("... then the most recent charge that is not void", lambda: every_order([ch(4, B, ymd(2026, 3, 1), 40), ch(5, B, ymd(2026, 9, 2), 1), ch(6, B, "", 0)], "pat5"))
T("... then the most charges", lambda: every_order([ch(7, B, ymd(2026, 9, 2), 2), ch(8, B, ymd(2026, 9, 2), 5), ch(9, B, ymd(2026, 9, 2), 4)], "pat8"))
T("... then the lowest chart id - by its number (pat9 before pat10), so the answer never depends on the order AdvancedMD lists them", lambda: every_order([ch(10, B), ch(9, B), ch(100, B), ch(11, B)], "pat9"))

# ---- decide(): rules 1 to 9 ----------------------------------------------------------------------------------------------------------
def C(n, last, first, d8="", **k): return dict({"id": "pat%d" % n, "name": lf(last, first), "dob": d8}, **k)
def F(last, first, d8="", **k): return dict({"id": FID, "name": cf(last, first), "dob": d8}, **k)
def D(feed, cands): return FI.decide(feed, cands, TODAY)
SEEN = []
def X(name, feed, cands, chart, rule, flags=(), william=None, evidence=None, group=None, feed_dob=None, candidates=None):
    def run():
        outs = set(); rnd = random.Random(7)
        for i in range(10):
            cs = list(cands); rnd.shuffle(cs); outs.add(json.dumps(D(feed, cs), sort_keys=True))
        if len(outs) != 1: return False, "the answer depends on the order of the charts: %s" % sorted(outs)[:2]
        d = json.loads(outs.pop()); SEEN.append(d)
        ok = d["chart"] == chart and d["rule"] == rule and d["flags"] == list(flags) and d["new_chart"] is (rule == 9) and FI.problems(d) == []
        if william is not None: ok = ok and d["for_william"] is william
        if evidence is not None: ok = ok and d["evidence"] == list(evidence)
        if group is not None: ok = ok and d["group"] == list(group)
        if feed_dob is not None: ok = ok and d["feed_dob"] == feed_dob
        if candidates is not None: ok = ok and d["candidates"] == list(candidates)
        return ok, d
    T(name, run)
T("the flag words are the owner's order's words", lambda: (FI.FLAG_FIRST_NAME, FI.FLAG_DATE, FI.FAR, FI.FLAG_CHART_NO_DOB, FI.FLAG_NO_FEED_DOB, FI.FLAG_NO_DOB_EITHER, FI.FLAG_NOT_USED)
  == ("first name differs", "birth date differs: ", "far", "chart has no birth date", "no birth date from Claimocity", "no birth date on either side", "same-name charts not used"))
NOT_USED = ["same-name charts not used"]
# rule 1
X("rule 1: a name candidate carries this Claimocity id - that chart, whatever the birth dates say, no flag, not for William", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", FARD, mrn=FID.upper())], "pat1", 1, [], william=False, evidence=["mrn"], feed_dob="real")
X("rule 1 comes before rule 2: another chart of the same name carries exactly the feed's date - the chart with the Claimocity id wins", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", FARD, mrn=FID), C(2, ZO, "XANTHIA", B)], "pat1", 1, [], candidates=["pat1", "pat2"])
X("rule 1: three letters of the first name are enough (a name candidate)", F(ZO, "XANTHIA", B), [C(1, ZO, "XANDRA", "", mrn=FID)], "pat1", 1, [])
X("rule 1: several charts carry the id - the live one", F(ZO, "XANTHIA", B), [C(3, ZO, "XANTHIA", B, mrn=FID, last_dos=ymd(2026, 2, 1), charges=9), C(4, ZO, "XANTHIA", B, mrn=FID, last_dos=ymd(2026, 10, 1), charges=1), C(5, ZO, "XANTHIA", B, last_dos=ymd(2026, 11, 1), charges=3)],
  "pat4", 1, [], group=["pat3", "pat4"])
X("rule 1: a different Social Security number does not stop it (the Claimocity id still wins)", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", FARD, mrn=FID, ssn=S2)], "pat1", 1, [])
X("rule 1 is for name candidates only: the id on a chart under another first name and another date is not used - a plain new chart", F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", FARD, mrn=FID)], None, 9, [], william=False, candidates=[])
# rule 2
X("rule 2: the feed's date is real and a name candidate carries exactly that date", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA M", B), C(2, ZO, "XANTHIA", FARD)], "pat1", 2, [], william=False, evidence=[], group=["pat1"])
X("rule 2: three letters of the first name are enough when the date is the same", F(ZO, "XANTHIA", B), [C(1, ZO, "XANDER", B)], "pat1", 2, [])
X("rule 2: two charts carry the date - the live one (the most recent charge), both named as the group", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B, last_dos=ymd(2026, 1, 9), charges=7), C(2, ZO, "XANTHIA", B, last_dos=ymd(2026, 8, 9), charges=1)], "pat2", 2, [], group=["pat1", "pat2"])
X("rule 2: the same number on the chosen chart is said as evidence too", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=dash(S1))], "pat1", 2, [], evidence=["ssn"])
X("... but a chart of that name and date whose nine-digit number DIFFERS is another person: not chosen - a new chart beside it, for William", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S2)], None, 9, NOT_USED, william=True, candidates=["pat1"])
X("... and a second chart of that name and date beside the proven other person is not chosen by name and date either (it may be that person's duplicate)", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S2), C(2, ZO, "XANTHIA", B)], None, 9, NOT_USED, william=True)
X("... unless a number says it is the feed's patient: rule 4 (the same Social Security number), no flag because the dates are the same", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S2), C(2, ZO, "XANTHIA", B, ssn=S1)], "pat2", 4, [], evidence=["ssn"])
# rule 3
X("rule 3: no name candidate carries the date, a chart of the same last name under ANOTHER first name does - that chart, 'first name differs', for William (an FYI)", F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", B), C(2, ZO, "XANTHIA", FARD)], "pat1", 3, ["first name differs"], william=True, candidates=["pat1", "pat2"])
X("rule 3: several such charts - the live one", F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", B, last_dos=ymd(2026, 9, 9), charges=1), C(2, ZO, "ELSPETH A", B, last_dos=ymd(2026, 1, 9), charges=5)], "pat1", 3, ["first name differs"], group=["pat1", "pat2"])
X("rule 2 comes before rule 3: a name candidate carries the date", F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", B), C(2, ZO, "XANTHIA", B)], "pat2", 2, [])
X("rule 3 needs exactly the date: another first name with a date one digit off is no match - a plain new chart (no chart of this name)", F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", B_DIGIT)], None, 9, [], william=False)
X("rule 3 needs the same last name: another last name with the same date is nobody", F(ZO, "XANTHIA", B), [C(1, QU, "XANTHIA", B)], None, 9, [], william=False)
X("rule 3: a Social Security number that differs is a twin, not the patient - a plain new chart", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "ELSPETH", B, ssn=S2)], None, 9, [], william=False)
X("rule 3: ... and no other chart of that last name and date is taken beside the twin", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "ELSPETH", B, ssn=S2), C(2, ZO, "OTTOLINE", B)], None, 9, [], william=False)
X("rule 3 is not asked when a name candidate carries the date (here one that another Social Security number rules out): the other first name is not taken instead", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S2), C(2, ZO, "ELSPETH", B)], None, 9, NOT_USED, william=True, candidates=["pat1"])
for nd in NONE_DATES:
    X("rule 3 never fires without a real date from the feed (%r): a new chart, the missing date flagged, for William" % (nd if nd != P8 else "placeholder"), F(ZO, "XANTHIA", nd), [C(1, ZO, "ELSPETH", B)], None, 9, ["no birth date from Claimocity"], william=True, feed_dob="none")
# rule 4
X("rule 4: the same Social Security number on a name candidate whose date is FAR - that chart, flag 'birth date differs: far', not for William", F(ZO, "XANTHIA", B, ssn=dash(S1)), [C(1, ZO, "XANTHIA", FARD, ssn=S1), C(2, ZO, "XANTHIA", B2)], "pat1", 4, ["birth date differs: far"], william=False, evidence=["ssn"])
X("rule 4: ... whose date is a slip - the kind of slip is the flag and part of the evidence", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANDRA", B_SWAP, ssn=S1)], "pat1", 4, ["birth date differs: " + FI.SLIP_SWAP] if not FI_ERR else [], evidence=["ssn", "slip:" + FI.SLIP_SWAP] if not FI_ERR else [])
for nd in NONE_DATES:
    X("rule 4: ... the feed has no birth date (%r) - flag 'birth date differs: no birth date from Claimocity'" % (nd if nd != P8 else "placeholder"), F(ZO, "XANTHIA", nd, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S1), C(2, ZO, "XANTHIA", B2)], "pat1", 4, ["birth date differs: no birth date from Claimocity"], feed_dob="none")
X("rule 4: ... the chart has no birth date - flag 'birth date differs: chart has no birth date'", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", P8, ssn=S1), C(2, ZO, "XANTHIA", FARD)], "pat1", 4, ["birth date differs: chart has no birth date"])
X("rule 4: ... neither side has one - flag 'no birth date on either side'", F(ZO, "XANTHIA", "", ssn=S1), [C(1, ZO, "XANTHIA", "", ssn=S1), C(2, ZO, "XANTHIA", B), C(3, ZO, "XANTHIA", B2)], "pat1", 4, ["no birth date on either side"])
X("rule 4: the same member number (the chart's has the three-letter prefix)", F(ZO, "XANTHIA", B, members=[M2, M1]), [C(1, ZO, "XANTHIA", FARD, members=[PFX + M1]), C(2, ZO, "XANTHIA", B2, members=[M1[:7]])], "pat1", 4, ["birth date differs: far"], evidence=["member"])
X("rule 4: a member number of seven characters is no evidence - a new chart beside the same-name chart, for William", F(ZO, "XANTHIA", B, members=[M1[:7]]), [C(1, ZO, "XANTHIA", FARD, members=[M1[:7]])], None, 9, NOT_USED, william=True)
X("rule 4: the last four of the Social Security number where the chart shows only four", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", FARD, ssn="***-**-" + S1[5:])], "pat1", 4, ["birth date differs: far"], evidence=["ssn4"])
X("rule 4: the strongest evidence wins - the full number on one chart beats the member number on another", F(ZO, "XANTHIA", B, ssn=S1, members=[M1]), [C(1, ZO, "XANTHIA", FARD, members=[M1], last_dos=ymd(2026, 11, 1), charges=9), C(2, ZO, "XANTHIA", B2, ssn=S1)], "pat2", 4, ["birth date differs: far"], evidence=["ssn"], group=["pat2"])
X("rule 4: the member number beats the last four", F(ZO, "XANTHIA", B, ssn=S1, members=[M1]), [C(1, ZO, "XANTHIA", FARD, ssn="xxx-xx-" + S1[5:]), C(2, ZO, "XANTHIA", B2, members=[M1])], "pat2", 4, ["birth date differs: far"], evidence=["member"])
X("rule 4: a junk number equal on both sides is no evidence", F(ZO, "XANTHIA", B, ssn="1" * 9), [C(1, ZO, "XANTHIA", FARD, ssn="1" * 9)], None, 9, NOT_USED, william=True)
X("rule 4 is for name candidates only: the number on a chart under another first name is not used", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "ELSPETH", FARD, ssn=S1)], None, 9, [], william=False)
X("rule 4: a member number shared with a chart whose Social Security number DIFFERS proves nothing (one plan, two people) - no chart by it", F(ZO, "XANTHIA", B, ssn=S1, members=[M1]), [C(1, ZO, "XANTHIA", FARD, ssn=S2, members=[M1])], None, 9, NOT_USED, william=True)
# rule 5
X("rule 5: a full-name candidate whose date is a SLIP from the feed's (one digit) - that chart, the kind of slip as flag and evidence, not for William", F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANTHIA", B)], "pat1", 5, ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [], william=False, evidence=["slip:" + FI.SLIP_DIGIT] if not FI_ERR else [])
for _n, (_a, _b, _k) in enumerate(((B, B_SWAP, "SLIP_SWAP"), (B, B_MD, "SLIP_MONTH_DAY"), (ymd(1941, 1, 31), ymd(1941, 2, 1), "SLIP_DAY"))):
    X("rule 5: ... %s" % _k, F(ZO, "XANTHIA", _b), [C(1, ZO, "XANTHIA", _a)], "pat1", 5, ["birth date differs: " + getattr(FI, _k)] if not FI_ERR else [])
X("rule 5 - the two charts of 11/17: both carry the corrected date, the feed is one digit off - the live one of the two", F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANTHIA", B, last_dos=ymd(2026, 10, 2), charges=4), C(2, ZO, "XANTHIA", B, last_dos=ymd(2026, 11, 14), charges=1)], "pat2", 5,
  ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [], group=["pat1", "pat2"])
X("rule 5: two full-name charts carry two DIFFERENT dates that are both slips - nobody can say which: a new chart, for William", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B_DIGIT), C(2, ZO, "XANTHIA", B_SWAP)], None, 9, NOT_USED, william=True, candidates=["pat1", "pat2"])
X("rule 5 needs the FULL first name: three letters and a slip are not enough", F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANDER", B)], None, 9, NOT_USED, william=True)
X("rule 5: a date that is FAR is no slip - a new chart beside the same-name chart, for William (until 11/25 this one chart was taken without a word)", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", FARD)], None, 9, NOT_USED, william=True, feed_dob="real")
X("rule 5: a same-name chart with a FAR date (a father, a namesake) beside the chart with the slip does not stop it", F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", FARD)], "pat1", 5, ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [], group=["pat1"])
X("rule 5 is not asked when a name candidate carries the date itself and another Social Security number rules it out (a namesake with exactly this date): no slip is read into the next chart", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S2), C(2, ZO, "XANTHIA", B_DIGIT)], None, 9, NOT_USED, william=True)
X("rule 5: a chart whose date is the placeholder is no slip from anything", F(ZO, "XANTHIA", ymd(1910, 1, 1)), [C(1, ZO, "XANTHIA", P8), C(2, ZO, "XANTHIA", FARD)], None, 9, NOT_USED, william=True)
# rule 6
X("rule 6: the feed's date is real and the only name candidates are full-name candidates with NO real date - that chart, 'chart has no birth date', for William (an FYI)", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", P8)], "pat1", 6, ["chart has no birth date"], william=True)
X("rule 6: two such charts - the live one", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", "", last_dos=ymd(2026, 5, 5), charges=2), C(2, ZO, "XANTHIA J", P8, last_dos=ymd(2026, 6, 6), charges=1)], "pat2", 6, ["chart has no birth date"], group=["pat1", "pat2"])
X("rule 6: not when one of the name candidates shares only three letters", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", ""), C(2, ZO, "XANDER", "")], None, 9, NOT_USED, william=True)
X("rule 6: not when another name candidate carries a real date (that one is far)", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", ""), C(2, ZO, "XANTHIA", FARD)], None, 9, NOT_USED, william=True)
# rule 7
for nd in NONE_DATES:
    X("rule 7 - the six charts of 11/8: the feed has NO BIRTH DATE (%r), the full-name charts with a real date all carry ONE date - the live one of them, not for William" % (nd if nd != P8 else "placeholder"), F(QU, "ZEBEDIAH", nd),
      [C(n, QU, "ZEBEDIAH", B2, last_dos=ymd(2026, n - 10, 3), charges=20 - n) for n in range(11, 17)], "pat16", 7, ["no birth date from Claimocity"], william=False, feed_dob="none", group=["pat%d" % n for n in range(11, 17)])
X("rule 7: a full-name chart without a date beside them is not in the way and is not chosen", F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", B2), C(2, QU, "ZEBEDIAH", "", last_dos=ymd(2026, 11, 20), charges=50)], "pat1", 7, ["no birth date from Claimocity"], group=["pat1"])
X("rule 7: the same-name charts carry TWO dates - nobody can say which: a new chart, both flags, for William", F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", B2), C(2, QU, "ZEBEDIAH", B)], None, 9, ["same-name charts not used", "no birth date from Claimocity"], william=True, feed_dob="none")
X("rule 7 needs the FULL first name: three letters and one date are not enough", F(QU, "ZEBEDIAH", ""), [C(1, QU, "ZEBULON", B2)], None, 9, ["same-name charts not used", "no birth date from Claimocity"], william=True)
X("rule 7: a three-letter chart with another date beside the full-name chart is not in the way", F(QU, "ZEBEDIAH", ""), [C(1, QU, "ZEBEDIAH", B2), C(2, QU, "ZEBULON", B)], "pat1", 7, ["no birth date from Claimocity"])
X("rule 7: not when a full-name chart carries another Social Security number (a namesake is proven)", F(QU, "ZEBEDIAH", "", ssn=S1), [C(1, QU, "ZEBEDIAH", B2), C(2, QU, "ZEBEDIAH", B2, ssn=S2)], None, 9, ["same-name charts not used", "no birth date from Claimocity"], william=True)
# rule 8
X("rule 8: the feed has no birth date and no full-name chart has a real one - the live one of them, 'no birth date on either side', for William (an FYI)", F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", P8, last_dos=ymd(2026, 1, 1), charges=1), C(2, QU, "ZEBEDIAH K", "", last_dos=ymd(2026, 2, 1), charges=1)],
  "pat2", 8, ["no birth date on either side"], william=True, feed_dob="none", group=["pat1", "pat2"])
X("rule 8 needs the FULL first name", F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBULON", "")], None, 9, ["same-name charts not used", "no birth date from Claimocity"], william=True)
X("rule 8 takes the live chart among the FULL-name charts: a three-letter chart beside them is not chosen, however lively", F(QU, "ZEBEDIAH", ""), [C(1, QU, "ZEBEDIAH", "", last_dos=ymd(2026, 1, 1), charges=1), C(2, QU, "ZEBULON", "", last_dos=ymd(2026, 11, 1), charges=9)], "pat1", 8, ["no birth date on either side"], group=["pat1"])
# rule 9
X("rule 9: no chart of this name, a real date - a plain new chart: no flag, not for William", F(WE, "OTTOLINE", B), [], None, 9, [], william=False, feed_dob="real", candidates=[], evidence=[])
for nd in NONE_DATES:
    X("rule 9: no chart of this name and NO BIRTH DATE (%r) - a new chart, the missing date flagged, for William (face sheet needed)" % (nd if nd != P8 else "placeholder"), F(WE, "OTTOLINE", nd), [], None, 9, ["no birth date from Claimocity"], william=True, feed_dob="none")
# one Claimocity id with two birth dates, with two names
X("one Claimocity id with a real date and the placeholder in one batch: the real one is used", dict(F(ZO, "XANTHIA"), dobs=[P8, B, ""]), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", B2)], "pat1", 2, [], feed_dob="real")
X("... with two different REAL dates, one of them on a chart: that chart, and the flag says Claimocity sent two", dict(F(ZO, "XANTHIA"), dobs=[B, FARD]), [C(1, ZO, "XANTHIA", B)], "pat1", 2, [FI.FLAG_TWO_DATES] if not FI_ERR else [], feed_dob="real")
X("... each of the two dates on a chart of its own: the two dates point to two charts - NO chart is chosen and none is made, for William", dict(F(ZO, "XANTHIA"), dobs=[B, FARD]), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", FARD)], None, 0, [FI.FLAG_TWO_DATES] if not FI_ERR else [], william=True)
X("... no chart at all: a new chart with NO date written (which of the two is right nobody knows), for William", dict(F(WE, "OTTOLINE"), dobs=[B, FARD]), [], None, 9, [FI.FLAG_TWO_DATES] if not FI_ERR else [], william=True, feed_dob="none")
X("one Claimocity id under two spellings of the first name: a chart that fits one of them is found", {"id": FID, "names": [(ZO, "XANTHIA"), (ZO, "ZANTHIA")], "dob": B}, [C(1, ZO, "ZANTHIA", B)], "pat1", 2, [])
X("a feed patient without a last name or without a first name is not decided: no chart, no new chart, for William", {"id": FID, "names": [("", "XANTHIA"), (ZO, "")], "dob": B}, [C(1, ZO, "XANTHIA", B)], None, 0, [], william=True)
X("a same-name chart that could not be read: nothing is decided on half the facts - no chart, no new chart, for William", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", FARD, read=False)], None, 0, [], william=True)
# AdvancedMD lists 50 charts at most: where the list of same-name charts may be cut short, nobody is matched by the name alone
_CUT = [FI.FLAG_CUT] if not FI_ERR else []
X("a list that may be cut short ('full'): the slip is not read (rule 5 says 'ONE date' of ALL full-name charts) - a new chart, for William, and the flag says why", dict(F(ZO, "XANTHIA", B_DIGIT), cut="full"), [C(1, ZO, "XANTHIA", B)], None, 9, NOT_USED + _CUT, william=True)
X("... nor is rule 7 asked (no date from the feed, one date on the charts that were listed)", dict(F(QU, "ZEBEDIAH", P8), cut="full"), [C(1, QU, "ZEBEDIAH", B2)], None, 9, ["same-name charts not used", "no birth date from Claimocity"] + _CUT, william=True)
X("... nor rule 8, nor rule 6", dict(F(QU, "ZEBEDIAH", ""), cut="full"), [C(1, QU, "ZEBEDIAH", "")], None, 9, ["same-name charts not used", "no birth date from Claimocity"] + _CUT, william=True)
X("... nor rule 6 (the feed has a date, the one chart listed has none)", dict(F(ZO, "XANTHIA", B), cut="full"), [C(1, ZO, "XANTHIA", P8)], None, 9, NOT_USED + _CUT, william=True)
X("... but what a chart itself shows still decides: the same date (rule 2)", dict(F(ZO, "XANTHIA", B), cut="full"), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", FARD)], "pat1", 2, [])
X("... the Claimocity id (rule 1)", dict(F(ZO, "XANTHIA", B), cut="full"), [C(1, ZO, "XANTHIA", FARD, mrn=FID)], "pat1", 1, [])
X("... a number in common (rule 4), the same last name and date under another first name (rule 3)", dict(F(ZO, "XANTHIA", B, ssn=S1), cut="full"), [C(1, ZO, "XANTHIA", FARD, ssn=S1), C(2, ZO, "ELSPETH", B)], "pat2", 3, ["first name differs"])
X("... and a new patient with a cut list and no chart of the name is still for William (a chart of the name may be among those not listed)", dict(F(WE, "OTTOLINE", B), cut="full"), [], None, 9, _CUT, william=True)
X("a list of name candidates that may be cut while every full-name chart is there ('name'): the slip IS read (rule 5)", dict(F(ZO, "XANTHIA", B_DIGIT), cut="name"), [C(1, ZO, "XANTHIA", B)], "pat1", 5, ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [])
X("... rule 7 is asked too", dict(F(QU, "ZEBEDIAH", P8), cut="name"), [C(1, QU, "ZEBEDIAH", B2)], "pat1", 7, ["no birth date from Claimocity"])
X("... but not rule 6, which says 'the ONLY name candidates'", dict(F(ZO, "XANTHIA", B), cut="name"), [C(1, ZO, "XANTHIA", P8)], None, 9, NOT_USED + _CUT, william=True)
X("... anything else said about a cut list counts as the worst case", dict(F(ZO, "XANTHIA", B_DIGIT), cut=True), [C(1, ZO, "XANTHIA", B)], None, 9, NOT_USED + _CUT, william=True)
T("a group of several charts whose activity was not given: decide() names the charts whose activity it needs, and none once it has it",
  lambda: (D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", B), C(3, ZO, "XANTHIA", FARD)])["needs_activity"] == ["pat1", "pat2"]
           and D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B, last_dos="", charges=0), C(2, ZO, "XANTHIA", B, last_dos=ymd(2026, 1, 1), charges=1)])["needs_activity"] == [] and D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B)])["needs_activity"] == []))
def _pre(feed, cands):      # the same charts with the evidence worked out beforehand (what the match step writes: words only, never the numbers)
    out = []
    for c in cands:
        ev, contra = FI.evidence(feed, c); out.append(dict({k: v for k, v in c.items() if k not in ("ssn", "mrn", "members")}, ev=ev, contra=contra))
    return out
_CASES = [(F(ZO, "XANTHIA", B, ssn=S1, members=[M1]), [C(1, ZO, "XANTHIA", FARD, ssn=S2, members=[M1]), C(2, ZO, "XANTHIA", B2, ssn=S1), C(3, ZO, "XANTHIA", B_DIGIT, mrn=FID)]),
          (F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn=S2), C(2, ZO, "XANTHIA", B)]), (F(ZO, "XANTHIA", "", members=[M1]), [C(1, ZO, "XANTHIA", B, members=[PFX + M1])])]
T("the evidence worked out beforehand (words only) gives the same answer as the numbers themselves", lambda: all(D(f, c) == D({k: v for k, v in f.items() if k not in ("ssn", "members")}, _pre(f, c)) for f, c in _CASES))
def _random_cases(n):
    """n feed patients and their charts, put together at random from the invented values: what decide() answers must hold the rule's own lines whatever comes."""
    rnd = random.Random(1125); lasts = [ZO, ZO + " JR", "O'" + ZO, QU, ZO[:4] + "-" + ZO[4:]]; firsts = ["XANTHIA", "XANTHIA K", "XANDER", "XAN", "XANTHIANNE", "ELSPETH", "", "XANT"]
    dates = [B, B_DIGIT, B_SWAP, B_MD, FARD, P8, "", "00000000", ymd(1941, 2, 30), B2]; ssns = ["", S1, dash(S2), "***-**-" + S1[5:], "xxx-xx-" + S3[5:], "1" * 9, S3]
    mems = [[], [M1], [PFX + M1], [M2], [M1[:7]]]; bad = []; seen = set()
    for i in range(n):
        f = {"id": FID, "ssn": rnd.choice(ssns), "members": rnd.choice(mems)}
        if rnd.random() < 0.8: f["name"] = cf(rnd.choice(lasts), rnd.choice(firsts))
        else: f["names"] = [(rnd.choice(lasts), rnd.choice(firsts)) for _ in range(rnd.randint(1, 3))]
        if rnd.random() < 0.8: f["dob"] = rnd.choice(dates)
        else: f["dobs"] = [rnd.choice(dates) for _ in range(rnd.randint(1, 3))]
        if rnd.random() < 0.15: f["cut"] = rnd.choice(["name", "full"])
        cs = []
        for k in rnd.sample(range(1, 40), rnd.randint(0, 6)):
            c = C(k, rnd.choice(lasts), rnd.choice(firsts), rnd.choice(dates), ssn=rnd.choice(ssns), members=rnd.choice(mems), mrn=rnd.choice(["", "", "", FID.upper(), FID2]))
            if rnd.random() < 0.7: c.update(last_dos=rnd.choice(["", ymd(2026, 1, 1), ymd(2026, 11, 1), ymd(2025, 6, 6)]), charges=rnd.randint(0, 5))
            if rnd.random() < 0.03: c["read"] = False
            cs.append(c)
        d = D(f, cs); why = []; ids = {c["id"] for c in cs}; names = [FI.split_name(f["name"])] if "name" in f else f["names"]; seen.add(d["rule"])
        if len({json.dumps(D(f, rnd.sample(cs, len(cs))), sort_keys=True) for _ in range(3)} | {json.dumps(d, sort_keys=True)}) != 1: why.append("the order of the charts changes the answer")
        if FI.problems(d) or d["new_chart"] != (d["rule"] == 9) or (d["chart"] is None) != (d["rule"] in (0, 9)): why.append("shape")
        if not set(d["candidates"]) <= ids or not set(d["group"]) <= ids or (d["chart"] is not None and d["chart"] not in d["group"]): why.append("a chart that was not among those given")
        if d["chart"] in ids:
            c = [x for x in cs if x["id"] == d["chart"]][0]; ev, contra = FI.evidence(f, c); kinds = {FI.name_kind(l, fi, *FI.split_name(c["name"])) for l, fi in names}; r = d["rule"]
            if contra and r != 1: why.append("a chart with another Social Security number chosen by rule %d" % r)
            if (r == 1 and "mrn" not in ev) or (r == 4 and not set(ev) & {"ssn", "member", "ssn4"}): why.append("rule %d without its evidence" % r)
            if (r in (1, 2, 4) and not kinds & {"name", "full"}) or (r in (5, 6, 7, 8) and "full" not in kinds) or (r == 3 and "surname" not in kinds): why.append("rule %d on a chart whose name does not fit it" % r)
            if r in (2, 3) and not FI.real_dob(c["dob"], TODAY): why.append("rule %d on a chart without a real date" % r)
            if (r in (5, 7, 8) and f.get("cut") == "full") or (r == 6 and f.get("cut")): why.append("rule %d on a list that may be cut short" % r)
            if d["for_william"] != (r in (3, 6, 8)): why.append("for_william of a chosen chart")
        elif not d["for_william"] and not (d["rule"] == 9 and d["flags"] == [] and d["feed_dob"] == "real"): why.append("a flagged new chart, or no decision, that is not for William")
        if (len(FI.william_lines(d, "pat900", FID)) >= 1) != d["for_william"]: why.append("the lines for William")
        if why: bad.append((why, f, cs, d))
    return bad, seen
T("3,000 feed patients put together at random: decide() never fails, answers the same in every order of the charts, and keeps its own lines - no chart with another Social Security number but by rule 1, no rule without its evidence, "
  "no name-alone rule on a list that may be cut short, every answer that is flagged is for William; all ten outcomes (rules 0 to 9) come up", lambda: (lambda bad, seen: (bad == [] and seen == set(range(10)), (bad[:1], sorted(seen))))(*_random_cases(3000)))
T("a chart id that does not look like one, or the same chart twice, is an error (chart ids go into the registers)", lambda: _raises(lambda: D(F(ZO, "XANTHIA", B), [dict(C(1, ZO, "XANTHIA", B), id=lf(ZO, "XANTHIA"))])) is True and _raises(lambda: D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B), C(1, ZO, "XANTHIA", B)])) is True)
# the feed patients of one batch
K = lambda last, first, d8: (last + ", " + first).upper().strip() + "|" + d8[:8]
k1, k2, k3, k4 = K(ZO, "XANTHIA", B), K(ZO, "XANTHIA", P8), K(QU, "ZEBEDIAH", B2), K(ZO, "XANTHIA", "")
def _pat(ids, keys, decide=None): return {"ids": sorted(ids), "keys": sorted(keys), "decide_keys": sorted(keys if decide is None else decide)}
T("the patients of a batch: one Claimocity id under its real date and under the placeholder is ONE patient - both keys are decided together", lambda: FI.patients({k1: [FID], k2: [FID], k3: [FID2]}, TODAY) == ([_pat([FID], [k1, k2]), _pat([FID2], [k3])], {}))
T("... two Claimocity ids under one name and one REAL date are one patient", lambda: FI.patients({k1: [FID2, FID], k2: [FID]}, TODAY) == ([_pat([FID, FID2], [k1, k2])], {}))
T("... two Claimocity ids under one name and NO date are not known to be one person: that key is not decided (for William), each id keeps its other keys",
  lambda: (lambda ps, un: ps == [_pat([FID], [k1, k2], [k1]), _pat([FID2], [k2, k3], [k3])] and list(un) == [k2] and un[k2] in FI.WHY_WORDS)(*FI.patients({k1: [FID], k2: [FID, FID2], k3: [FID2]}, TODAY)))
T("... two Claimocity ids under one name and one real date whose Social Security numbers DIFFER are two people: not put together, the key not decided",
  lambda: (lambda ps, un: ps == [_pat([FID], [k1], []), _pat([FID2], [k1], [])] and list(un) == [k1])(*FI.patients({k1: [FID, FID2]}, TODAY, ssn_of={FID: [S1], FID2: [dash(S2)]}.get)))
T("... a message without a Claimocity id is nobody's: its key is not decided - unless a Claimocity id carries the same name and the same real date",
  lambda: (lambda ps, un: ps == [_pat([FID], [k1])] and list(un) == [k4] and un[k4] in FI.WHY_WORDS)(*FI.patients({k1: [FID, ""], k4: [""]}, TODAY)))
T("the date a new chart is written with: the feed's when it is real; otherwise the placeholder date and 'none' - never an empty date",
  lambda: ([FI.chart_dob(x, TODAY) for x in ([B], [P8, B, ""], [""], [P8], [], ["00000000"], [B, FARD], [ymd(1941, 2, 30)])] == [(mdy(B), "real")] * 2 + [(P_MDY, "none")] * 6 and FI.NO_DOB_MDY == P_MDY))
# what goes to William, and the fixed words
def _w(d, chart="", fid=FID): return FI.william_lines(d, chart, fid)
T("for William: a new chart beside same-name charts - ONE line with the chart ids, the count and the question",
  lambda: (lambda ls: len(ls) == 1 and "pat900" in ls[0] and "2 same-name chart(s)" in ls[0] and "pat1" in ls[0] and "pat2" in ls[0] and "same person or not?" in ls[0])(_w(D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B_DIGIT), C(2, ZO, "XANTHIA", B_SWAP)]), "pat900")))
T("for William: a new chart with no birth date - 'face sheet needed'; beside same-name charts too: two lines", lambda: (lambda a, b: len(a) == 1 and "pat900" in a[0] and "face sheet needed" in a[0] and len(b) == 2)(_w(D(F(WE, "OTTOLINE", P8), []), "pat900"), _w(D(F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", B2), C(2, QU, "ZEBEDIAH", B)]), "pat900")))
T("for William: before the chart is made the same lines say 'a new chart is needed'; a new chart that could NOT be made has a line of its own that names the Claimocity id",
  lambda: (lambda d: (lambda a, b: len(a) == 1 and a[0].startswith("a new chart is needed beside 1 same-name chart(s) (pat1)") and len(b) == 2 and FID in b[1] and "could NOT be made" in b[1])(_w(d), _w(dict(d, flags=d["flags"] + [FI.FLAG_NO_CHART_MADE]))))(D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", FARD)])))
T("for William: rules 3, 6 and 8 are one line each that names the rule ('matched by ...') - an FYI, not a question",
  lambda: all(len(ls) == 1 and "matched by" in ls[0] and "pat1" in ls[0] and "?" not in ls[0] for ls in (_w(D(F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", B)]), "pat1"), _w(D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", P8)]), "pat1"), _w(D(F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", "")]), "pat1"))))
T("for William: rules 1, 2, 4, 5 and 7 and a plain new chart bring no line (the digest's body says them); a patient nobody could decide brings one that names the Claimocity id",
  lambda: ([_w(D(f, c), "pat1") for f, c in ((F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", FARD, mrn=FID)]), (F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B)]), (F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", FARD, ssn=S1)]),
                                             (F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANTHIA", B)]), (F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", B2)]))] == [[]] * 5 and _w(D(F(WE, "OTTOLINE", B), []), "pat900") == []
           and (lambda ls: len(ls) == 1 and FID in ls[0])(_w(D(dict(F(ZO, "XANTHIA"), dobs=[B, FARD]), [C(1, ZO, "XANTHIA", B), C(2, ZO, "XANTHIA", FARD)])))))
T("for William: every answer that is for William brings at least one line, every other answer none (nothing is flagged without words, nothing is said that is not flagged)",
  lambda: (len(SEEN) > 60 and all((len(_w(d, "pat900")) >= 1) == d["for_william"] for d in SEEN), [d for d in SEEN if (len(_w(d, "pat900")) >= 1) != d["for_william"]][:2]))
T("the fixed words: every why, flag and evidence word decide() gave in this test is one of the constants, and none of them holds a digit (no date, no number can hide in one)",
  lambda: (len(SEEN) > 60 and all(FI.problems(d) == [] for d in SEEN) and not any(re.search(r"\d", w) for w in list(FI.WHY_WORDS) + list(FI.FLAG_WORDS)) and {e for d in SEEN for e in d["evidence"]} <= set(FI.EVIDENCE_WORDS), len(SEEN)))
T("... problems() names anything else: a why with a name in it, a flag that is not a constant, a chart id that is not one, a rule that is not 0 to 9 or 'map'",
  lambda: (lambda g: FI.problems(g) == [] and all(FI.problems(dict(g, **bad)) != [] for bad in ({"why": "matched " + ZO}, {"flags": [mdy(B)]}, {"candidates": [lf(ZO, "XANTHIA")]}, {"rule": 12}, {"evidence": [S1]}, {"feed_dob": B}, {"for_william": "yes"}))
           and FI.problems(dict(g, rule="map")) == [])({"rule": 2, "why": FI.WHY[2], "flags": [], "candidates": ["pat1"], "evidence": ["ssn"], "feed_dob": "real", "for_william": False}))
_PURE_TOKENS = [ZO, QU, WE, B, B_DIGIT, B_SWAP, B_MD, FARD, B2, mdy(B), iso(B), S1, S2, dash(S1), S1[5:], M1, M2, FID.upper()]
T("nothing decide() answers carries a name, a date or a number of the patients it weighed (chart ids, rule numbers and the fixed words only)", lambda: (len(SEEN) > 60 and not [tok for tok in _PURE_TOKENS for d in SEEN if tok.lower() in json.dumps(d).lower()], len(SEEN)))

# =====================================================================================================================================
# 2. THE THREE STEPS, run inside this process against a stand-in AdvancedMD
# =====================================================================================================================================
STAMP = ymd(2026, 11, 25) + "T0101Z"; STAMP_OLD = ymd(2026, 11, 25) + "T0001Z"; PREFIX = "F" + STAMP[2:8]
Y = datetime.date.today().year          # the steps read today's date themselves: the invented birth years here are counted back from this year
OKAY = "<PPMDResults><Results>%s</Results><Error /></PPMDResults>"
FAULT = "<PPMDResults><Error><Fault><detail><description>%s</description></detail></Fault></Error></PPMDResults>"
PAGE = "<html><body>503 Service Unavailable</body></html>"
READS = {"lookuppatient", "getdemographic"}                                           # all the match and resolve steps may ever send
NEWCHART = {"lookuppatient", "addpatient", "getdemographic", "updaterespparty"}       # all the new-chart step may ever send
_STD = set(getattr(sys, "stdlib_module_names", ())) or {"os", "sys", "re", "json", "time", "collections", "glob", "html", "datetime", "xml", "unicodedata", "hashlib", "io"}
def run_inside(path, standins, cwd, env=None, argv=()):
    """Run a helper INSIDE this process (the idea of tools/selftest/test_pos_rule.py): its amd / txh / add_ins are the stand-ins given here, put in
    sys.modules for the run and taken out again. A stand-in is a dict of functions (a module is built from it) or a pure module already loaded.
    Refuses to run unless EVERY module the helper loads is Python's own or one of the stand-ins - so the real amd can never load."""
    src = open(path).read(); foreign = sorted(n for n in loads(src) if n not in _STD and n not in standins)
    if foreign: raise RuntimeError("no stand-in for %s - the helper is not run" % foreign)
    old_mod = {k: sys.modules.get(k) for k in standins}; old_cwd = os.getcwd(); old_env = dict(os.environ); old_argv = list(sys.argv); out = io.StringIO(); err = ""
    import time as _time
    old_sleep = _time.sleep
    try:
        for k, v in standins.items():
            if isinstance(v, dict):
                m = types.ModuleType(k); m.STAND_IN = True
                for n, f in v.items(): setattr(m, n, f)
                v = m
            sys.modules[k] = v
        os.chdir(cwd); os.environ.update(env or {}); sys.argv = [path] + list(argv); _time.sleep = lambda *_a: None
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit as e:
                if e.code not in (None, 0): err = "exit %s" % (e.code if isinstance(e.code, int) else 1); print(e.code if not isinstance(e.code, int) else "", file=out)
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally:
        _time.sleep = old_sleep; os.chdir(old_cwd); sys.argv = old_argv
        for k in list(os.environ):
            if k not in old_env: del os.environ[k]
        os.environ.update(old_env)
        for k, v in old_mod.items():
            if v is None: sys.modules.pop(k, None)
            else: sys.modules[k] = v
    return out.getvalue(), err
PARSER = os.path.join(H, "feed_parse_dft_1028.py")
try: FPM = load("feed_payer_map")
except Exception as e: FPM = {}
check("the two helpers this test loads as they are (feed_identity.py, feed_payer_map.py) and the parser it runs load no module that talks to AdvancedMD",
      not (loads(read("feed_identity.py")) | loads(read("feed_payer_map.py")) | loads(read("feed_parse_dft_1028.py"))) & set(AMD_MODULES) and not isinstance(FPM, dict))
def esc(s): return s.replace("&", "&amp;").replace("'", "&apos;").replace('"', "&quot;")
def like(pattern, name):
    """AdvancedMD's name search as this stand-in takes it - the strict reading: SQL LIKE on LAST,FIRST, % = anything, upper case, no space after the comma."""
    p = re.sub(r"\s*,\s*", ",", pattern.upper()); n = re.sub(r"\s*,\s*", ",", name.upper())
    return re.fullmatch("".join(".*" if c == "%" else re.escape(c) for c in p), n) is not None
def chart(n, last, first, d8="", ssn="", mrn="", members=(), charges=(), **k):
    return dict(dict(id="pat%d" % n, last=last, first=first, dob=d8, ssn=ssn, mrn=mrn, chartno="C%d" % n, members=list(members), charges=list(charges), resp="resp%d" % n), **k)
def msg(fid, last, first, d8, ssn="", in1=(), nopid=False): return dict(fid=fid, last=last, first=first, dob=d8, ssn=ssn, in1=list(in1), nopid=nopid)
def hl7_text(msgs):
    out = []
    for i, m in enumerate(msgs):
        pid = ["PID", "1", "", m["fid"], "", m["last"] + "^" + m["first"], "", m["dob"], "F"] + [""] * 12
        pid[11] = "9 INVENTED WAY^^TALLAHASSEE^FL^32301"; pid[14] = "8505550100"; pid[19] = m["ssn"]
        ft1 = ["FT1"] + [""] * 25; ft1[4] = STAMP[:8]; ft1[10] = "1"; ft1[19] = "I10"; ft1[25] = "99309^x"
        segs = ["MSH|^~\\&|feed|TEST MANOR|x|x|%s||DFT^P03|%d|P|2.3" % (STAMP[:8], i + 1)] + ([] if m["nopid"] else ["|".join(pid)]) + ["PV1|1|I", "|".join(ft1)]
        for payer, member in m["in1"]:
            s = ["IN1", "1", "", "", payer] + [""] * 45; s[49] = member; segs.append("|".join(s))
        out.append("\r".join(segs) + "\r")
    return "".join(out)
class Amd:
    """The stand-in AdvancedMD: charts in memory. Every action a step sends is checked against what THAT step may send - anything else is refused,
    written down and raised (a stray write fails the test). It counts addpatient (s.added)."""
    def __init__(s, charts):
        s.charts = {c["id"]: dict(c) for c in charts}; s.calls = []; s.refused = []; s.added = []; s.resp = []; s.script = ""; s.allowed = set()
        s.nextid = 9001; s.dup = 0; s.dup_always = False; s.blind = True; s.bad = {}; s.addfault = ""; s.quote = '"'; s.bare_id = False; s.odd_row = ""; s.no_begin = False; s.asked = []
    def msg(s, action, cls, attrs=None, children=""): return '<ppmdmsg action="%s" class="%s" %s>%s</ppmdmsg>' % (action, cls, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
    def post(s, body, timeout=0):
        a = dict(re.findall(r'(\w+)="([^"]*)"', body.split(">", 1)[0])); action = a.get("action", "?")
        s.calls.append((s.script, action))
        if action not in s.allowed:
            s.refused.append((s.script, action)); raise RuntimeError("the stand-in AdvancedMD refuses %s from %s" % (action, s.script))
        if s.bad.get(action):
            kind = s.bad[action].pop(0)
            if kind == "raise": raise TimeoutError("read timed out (test)")
            if kind in ("fault", "page"): return FAULT % "Server Error (test)" if kind == "fault" else PAGE
        return getattr(s, "do_" + action)(a, body)
    def row(s, c): return '<patient id="%s" name="%s" chart="%s" ssn="%s" dob="%s"/>' % (c["id"], esc(lf(c["last"], c["first"])), c["chartno"], c.get("row_ssn", c["ssn"]), c.get("row_dob", mdy(c["dob"]) if c["dob"] else ""))
    def do_lookuppatient(s, a, body):
        if "code" not in a:
            s.asked.append(a.get("name", ""))
            if s.no_begin and "%," in a.get("name", ""): return FAULT % "Server Error (test)"      # an AdvancedMD that does not take the 'begins with' form of the last name
        if "code" in a: rows = [] if s.blind else [c for c in s.charts.values() if c["chartno"].upper() == a["code"].upper()]
        else: rows = sorted((c for c in s.charts.values() if like(a.get("name", ""), lf(c["last"], c["first"]))), key=lambda c: (c["last"], c["first"], c["id"]))[:50]      # AdvancedMD answers the first 50 by name
        return OKAY % ("<patientlist>%s</patientlist>" % ("".join(s.row(c) for c in rows).replace('"', s.quote) + ("" if "code" in a else s.odd_row)))
    def do_getdemographic(s, a, body):
        c = s.charts.get(a.get("patientid"))
        if c is None: return FAULT % "patient not found (test)"
        plans = "".join('<insplan id="ins%d" carrier="car7" subscribernum="%s" sequence="%d"/>' % (i + 1, m, i + 1) for i, m in enumerate(c["members"]))
        return OKAY % ('<patientlist><patient id="%s" name="%s" dob="%s" sex="F" ssn="%s" additionalmrn="%s" chart="%s" respparty="%s" insorder="1"><insplanlist>%s</insplanlist></patient></patientlist>'
                       % (c["id"][3:] if s.bare_id else c["id"], esc(lf(c["last"], c["first"])), c.get("row_dob", mdy(c["dob"]) if c["dob"] else ""), c["ssn"], c["mrn"], c["chartno"], c["resp"], plans)).replace('"', s.quote)
    def do_addpatient(s, a, body):
        p = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r"<patient [^>]*>", body).group(0))); s.added.append(p)
        if s.addfault: return FAULT % s.addfault
        if s.dup_always or s.dup > 0 or any(c["chartno"].upper() == p["chart"].upper() for c in s.charts.values()):
            s.dup = max(0, s.dup - 1); return FAULT % "Duplicate chart number - a chart number must be unique (test)"
        pid = "pat%d" % s.nextid; s.nextid += 1; last, _, first = p["name"].partition(",")
        s.charts[pid] = chart(int(pid[3:]), last, first, mrn=p.get("additionalmrn", ""), chartno=p["chart"], made=p)
        return '<PPMDResults><Results success="1"><patientlist><patient id="%s" chart="%s" respparty=""/></patientlist></Results><Error /></PPMDResults>' % (pid, p["chart"])
    def do_updaterespparty(s, a, body):
        s.resp.append(dict(dict(re.findall(r'(\w+)="([^"]*)"', re.search(r"<respparty [^>]*>", body).group(0))), patientid=a.get("patientid"))); return OKAY % ""
TOKENS = set(); NUMBERS = set(); PRINTED = []; WORLDS = []
def _tokens(m):
    for w in (m["last"], m["first"]):
        TOKENS.add(w)
    d = m.get("dob") or ""
    if re.fullmatch(r"\d{8}", d) and d not in (P8, "00000000"): TOKENS.update((d, mdy(d), iso(d)))
    if m.get("ssn"):
        n = re.sub(r"\D", "", m["ssn"])
        if len(n) == 9: NUMBERS.update((n, dash(n)))
    for x in list(m.get("members") or []) + [mem for _p, mem in (m.get("in1") or [])]:
        if x: NUMBERS.add(x)
class World:
    """One throwaway workspace (the feed files of one batch, parsed by the real parser) and the stand-in AdvancedMD behind it."""
    def __init__(s, msgs, charts=()):
        s.dir = tempfile.mkdtemp(prefix="feedid_"); os.makedirs(os.path.join(s.dir, "registers")); os.makedirs(os.path.join(s.dir, "hl7"))
        open(os.path.join(s.dir, "hl7", STAMP[:8] + "feed.hl7"), "w").write(hl7_text(msgs))
        json.dump({"car6085": ["FLO02", "FLORIDA MEDICARE"], "car6285": ["HUM01", "HUMANA"]}, open(os.path.join(s.dir, "carriers_rich.json"), "w"))
        s.amd = Amd(charts); s.txh_calls = []; s.txh_bad = {}; s.ins = []; s.ins_answer = None; s.out = {}; s.err = {}
        for m in [x for x in msgs if not x.get("nopid")] + list(charts): _tokens(m)
        _o, s.parse_err = run_inside(PARSER, {}, s.dir, argv=(os.path.join(s.dir, "hl7"), os.path.join(s.dir, "feed_unknown_%s.json" % STAMP)))
        WORLDS.append(s)
    def fetch(s, pid):
        s.txh_calls.append(pid)
        if s.txh_bad.get(pid):
            if s.txh_bad[pid].pop(0) == "raise": raise TimeoutError("read timed out (test)")
            return ET.fromstring(FAULT % "Server Error (test)")
        return ET.fromstring(OKAY % ("<chargelist>%s</chargelist>" % "".join('<charge id="chg%d" dos="%s" void="%s"/>' % (i, mdy(d), "1" if v else "0") for i, (d, v) in enumerate(s.amd.charts[pid]["charges"]))))
    def add(s, pid, carrier, subnum, begindate=None, coverage="1", finclass="CC"):
        s.ins.append((pid, carrier, subnum)); return s.ins_answer(subnum) if s.ins_answer else ("ins%d" % (700 + len(s.ins)), str(len(s.ins)))
    def run(s, script, allowed, argv=()):
        s.amd.script = script; s.amd.allowed = set(allowed)
        stand = {"amd": {"login_cached": lambda *a, **k: ("web", "token"), "msg": s.amd.msg, "post": s.amd.post}, "txh": {"fetch": s.fetch}, "add_ins": {"add": s.add}, "feed_payer_map": FPM}
        if not FI_ERR: stand["feed_identity"] = FI
        env = {"FEED_STAMP": STAMP, "FEED_HL7_DIR": os.path.join(s.dir, "hl7"), "FEED_CHART_PREFIX": PREFIX, "FEED_DX_CACHE": os.path.join(s.dir, "dx.json")}
        try: o, e = run_inside(os.path.join(H, script), stand, s.dir, env=env, argv=argv)
        except Exception as ex: o, e = "", "not run: %s" % ex
        s.out[script] = o; s.err[script] = e; PRINTED.append(o); return o, e
    def match(s):
        try: return json.load(open(os.path.join(s.dir, "feed_match_%s.json" % STAMP)))
        except (OSError, ValueError): return {}
    def reg(s):
        try: return json.load(open(os.path.join(s.dir, "registers", "feed_newcharts_%s.json" % STAMP)))
        except (OSError, ValueError): return {"created": [], "failed": []}
    def ingest(s):
        """The driver's own order (claimocity_ingest.py): match, resolve, then - live - the new-chart step exactly when an entry says MISSING with no chart. A failed step stops it."""
        s.run("claimocity_match.py", READS, argv=("feed_unknown_%s.json" % STAMP,))
        if not s.err["claimocity_match.py"]: s.run("claimocity_resolve.py", READS)
        if not any(s.err.values()) and any(v["status"] == "MISSING" and not v.get("resolved") for v in s.match().values()): s.run("claimocity_newcharts.py", NEWCHART)
        return s
    def clean(s): return not any(s.err.values()) and not s.amd.refused and not s.parse_err
_drv = read("claimocity_ingest.py"); _imp = read("claimocity_import.py")
check("the contract this test stands on is the driver's and the import's: match with the unknown file, then resolve, then - on MISSING with no chart - the new-chart step; the import finds a message's entry by name and date and takes the chart of the message's OWN Claimocity id from it (by_id - the driver writes it), else the entry's 'resolved'",
      0 < _drv.find('os.path.join(HERE, "claimocity_match.py"), "feed_unknown_%s.json" % stamp') < _drv.find('os.path.join(HERE, "claimocity_resolve.py")') < _drv.find('os.path.join(HERE, "claimocity_newcharts.py")')
      and 'v["status"] == "MISSING" and not v.get("resolved")' in _drv and "pid = chart_of(msg)" in _imp and 'e = MATCH.get(str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8])' in _imp
      and 'p_ = e["by_id"].get(m.get("pid"))' in _imp and 'return e.get("resolved")' in _imp and 'v["by_id"] = by' in _drv)      # 11/25/2026 (the integration): each Claimocity id keeps its own chart - the driver names it, the import asks by it
def _refuses():
    a = Amd([]); a.allowed = set(READS); a.script = "x"
    try: a.post(a.msg("addinsurance", "demographics", {"nocookie": "1"}, "<patient/>"))
    except RuntimeError: return a.refused == [("x", "addinsurance")]
    return False
check("the stand-in AdvancedMD refuses an action a step may not send, and writes it down", _refuses())
def step(name, fn):      # one scenario: whatever goes wrong inside it is a FAIL of its own check, never the end of the test
    T(name, fn)
def ok_field(v, **want): return all(v.get(k) == x for k, x in want.items())

# ---- the two charts of 11/17: both carry the corrected date, the feed is one digit off ------------------------------------------------
BD = ymd(Y - 85, 5, 14); BD_OFF = ymd(Y - 85, 5, 24); BD_FAR = ymd(Y - 70, 9, 27); BD2 = ymd(Y - 79, 2, 8)
A_FIRST, B_FIRST, C_FIRST, D_FIRST, E_FIRST = "XANTHIA", "ZEBEDIAH", "OTTOLINE", "ELSPETHA", "QUILLARA"
w17 = World([msg(FID, ZO, A_FIRST, BD_OFF)], [chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 2), 0)] * 3 + [(ymd(Y, 1, 2), 1)]), chart(102, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 12, 14), 0)])]).ingest()      # chart 101's newest charge is void
e17 = w17.match().get(K(ZO, A_FIRST, BD_OFF), {})
step("11/17: two same-name charts with the corrected date, the feed one digit off - the visit goes to the LIVE one (the most recent charge that is not void), and NO chart is made",
     lambda: (w17.clean() and e17.get("resolved") == "pat102" and len(w17.amd.added) == 0 and "claimocity_newcharts.py" not in w17.out, (w17.err, w17.amd.refused, e17)))
step("11/17: ... the entry says how: rule 5, the kind of slip as flag and evidence, both charts as the group, not for William - and only those two charts' activity was read",
     lambda: (ok_field(e17, rule=5, status="AMBIGUOUS", flags=[FI.FLAG_DATE + FI.SLIP_DIGIT], evidence=["slip:" + FI.SLIP_DIGIT], pids=["pat101", "pat102"], candidates=["pat101", "pat102"], feed_dob="real", for_william=False, feed_ids=[FID])
              and e17.get("why") in FI.WHY_WORDS and sorted(w17.txh_calls) == ["pat101", "pat102"], e17))
# ---- the six charts of 11/8: the feed sent the placeholder ----------------------------------------------------------------------------
w8 = World([msg(FID, QU, B_FIRST, P8)], [chart(n, QU, B_FIRST, BD2, charges=[(ymd(Y - 1, n - 110, 3), 0)] * (117 - n)) for n in range(111, 117)]).ingest()
e8 = w8.match().get(K(QU, B_FIRST, P8), {})
step("11/8: the feed sent the placeholder, six same-name charts carry ONE date - the visit goes to the live one, and NO chart is made",
     lambda: (w8.clean() and e8.get("resolved") == "pat116" and len(w8.amd.added) == 0, (w8.err, w8.amd.refused, e8)))
step("11/8: ... rule 7, flag 'no birth date from Claimocity', the six charts named, feed_dob 'none', not for William", lambda: (ok_field(e8, rule=7, status="AMBIGUOUS", flags=["no birth date from Claimocity"], pids=["pat%d" % n for n in range(111, 117)], feed_dob="none", for_william=False), e8))
# ---- one chart, the same name and date: nothing but the lookup and one chart read -------------------------------------------------
w1 = World([msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO, A_FIRST + " K", BD), chart(105, ZO + "SON", A_FIRST, BD), chart(106, ZO, D_FIRST, BD_FAR)]).ingest()
e1 = w1.match().get(K(ZO, A_FIRST, BD), {})
step("one chart of that name and date: FOUND, rule 2, no chart made, no activity read (one chart needs none), and only the charts that could be the patient were opened",
     lambda: (w1.clean() and ok_field(e1, resolved="pat101", status="FOUND", rule=2, flags=[], pids=["pat101"], for_william=False) and w1.amd.added == [] and w1.txh_calls == []
              and [c for c in w1.amd.calls if c[1] == "getdemographic"] == [("claimocity_match.py", "getdemographic")], (w1.err, e1, w1.amd.calls)))
# ---- a new patient --------------------------------------------------------------------------------------------------------------------
wn = World([msg(FID, WE, C_FIRST, BD, in1=[("Medicare Part B", M1)])], []).ingest()
en = wn.match().get(K(WE, C_FIRST, BD), {}); rn = (wn.reg()["created"] or [{}])[0]
step("a new patient: ONE addpatient, with the feed's real birth date, the Claimocity id as the chart's additional number, the first number of the day's series",
     lambda: (wn.clean() and len(wn.amd.added) == 1 and ok_field(wn.amd.added[0], name=lf(WE, C_FIRST), dob=mdy(BD), chart=PREFIX + "-01", additionalmrn=FID.upper()), (wn.err, wn.amd.refused, wn.amd.added)))
step("a new patient: the responsible party gets the same name and the same birth date", lambda: (len(wn.amd.resp) == 1 and ok_field(wn.amd.resp[0], name=lf(WE, C_FIRST), dob=mdy(BD), patientid="pat9001"), wn.amd.resp))
step("a new patient: the match entry now carries the new chart (what the import reads), still says rule 9 and why",
     lambda: (ok_field(en, resolved="pat9001", status="MISSING", rule=9, flags=[], candidates=[], feed_dob="real", for_william=False) and en.get("why") in FI.WHY_WORDS, en))
step("a new patient: the register row says rule, why, flags, dob 'real', for_william - beside the chart, the Claimocity id and the plan",
     lambda: (ok_field(rn, pid="pat9001", chart=PREFIX + "-01", feed_ids=[FID], rule=9, flags=[], dob="real", for_william=False, respparty_named=True) and rn.get("why") in FI.WHY_WORDS
              and rn.get("plans") == [{"code": "FLO02", "ins": "ins701", "seq": "1", "from": "Medicare Part B"}] and wn.ins == [("pat9001", "car6085", M1)], (rn, wn.ins)))
# ---- no birth date from the feed: the placeholder date, never an empty one -------------------------------------------------------------
wd = World([msg(FID, WE, C_FIRST, ""), msg(FID2, TH, D_FIRST, P8), msg(FID3, YA, E_FIRST, "00000000")], []).ingest()
step("a new patient with NO birth date (empty, the placeholder, zeros): each chart is written with the placeholder date - for the patient AND the responsible party - never an empty date",
     lambda: (wd.clean() and [p["dob"] for p in wd.amd.added] == [P_MDY] * 3 and [p["dob"] for p in wd.amd.resp] == [P_MDY] * 3 and not any("//" in json.dumps(p) for p in wd.amd.added + wd.amd.resp), (wd.err, wd.amd.added, wd.amd.resp)))
step("... each register row says dob 'none' and is for William (face sheet needed), the flag says Claimocity sent no birth date; three charts, three numbers",
     lambda: ((lambda rows: len(rows) == 3 and all(ok_field(r, rule=9, dob="none", for_william=True, flags=["no birth date from Claimocity"]) for r in rows) and [r["chart"] for r in rows] == [PREFIX + "-01", PREFIX + "-02", PREFIX + "-03"])(wd.reg()["created"]), wd.reg()))
# ---- the chart number ---------------------------------------------------------------------------------------------------------------
wc = World([msg(FID, WE, C_FIRST, BD)], []); wc.amd.dup = 4; wc.ingest()
step("the chart number: four 'Duplicate chart' answers in a row (the probe saw none of them taken) - the FIFTH number is used, the patient has a chart",
     lambda: (wc.clean() and [p["chart"] for p in wc.amd.added] == [PREFIX + "-0%d" % i for i in range(1, 6)] and ok_field((wc.reg()["created"] or [{}])[0], chart=PREFIX + "-05", pid="pat9001") and wc.reg()["failed"] == []
              and wc.match()[K(WE, C_FIRST, BD)].get("resolved") == "pat9001", (wc.err, [p["chart"] for p in wc.amd.added], wc.reg())))
wp = World([msg(FID, WE, C_FIRST, BD)], [chart(201, QU, B_FIRST, BD2, chartno=PREFIX + "-01"), chart(202, QU, D_FIRST, BD2, chartno=PREFIX.lower() + "-02")]); wp.amd.blind = False; wp.ingest()
step("the chart number: numbers the probe finds taken are passed over without an addpatient", lambda: (wp.clean() and [p["chart"] for p in wp.amd.added] == [PREFIX + "-03"], (wp.err, wp.amd.added)))
wh = World([msg(FID, WE, C_FIRST, BD)], [])
json.dump({"created": [{"pid": "pat1", "chart": PREFIX + "-07"}, {"pid": "pat2", "chart": PREFIX + "-03"}, {"pid": "pat3", "chart": "F" + ymd(2026, 11, 24)[2:] + "-40"}], "failed": []}, open(os.path.join(wh.dir, "registers", "feed_newcharts_%s.json" % STAMP_OLD), "w"))
json.dump([{"not": "a register of this shape"}], open(os.path.join(wh.dir, "registers", "feed_newcharts_%sR.json" % STAMP_OLD), "w"))
wh.ingest()
step("the chart number: counting starts after the HIGHEST number any feed_newcharts register in the workspace holds for the day's series (another day's series does not count)",
     lambda: (wh.clean() and [p["chart"] for p in wh.amd.added] == [PREFIX + "-08"], (wh.err, wh.amd.added)))
wx = World([msg(FID, WE, C_FIRST, BD), msg(FID2, TH, D_FIRST, BD2)], []); wx.amd.dup_always = True; wx.ingest()
fx = wx.reg()["failed"]
step("the chart number: when every number answers 'Duplicate chart' the step stops at 200 tries per patient - no endless loop, the next patient is still tried",
     lambda: (wx.clean() and len(wx.amd.added) == 400 and len(fx) == 2 and wx.reg()["created"] == [], (wx.err, len(wx.amd.added), fx)))
step("... the failed row is on disk and free of patient data: the Claimocity id, a fixed reason, the last number tried - no piece of the name",
     lambda: (sorted(f.get("feed_id") for f in fx) == [FID, FID2] and all(ok_field(f, why=FI.FAIL_NUMBER, tries=200) and "key" not in f and set(f) <= {"feed_id", "why", "chart", "tries"} and re.fullmatch(re.escape(PREFIX) + r"-\d+", f["chart"]) for f in fx)
              and all(not v.get("resolved") and v.get("for_william") is True for v in wx.match().values())
              and len([l for l in wx.out["claimocity_newcharts.py"].splitlines() if l.startswith("FOR WILLIAM: ") and "could NOT be made" in l and (FID in l or FID2 in l)]) == 2, fx))
wr = World([msg(FID, WE, C_FIRST, BD)], []); wr.amd.addfault = "The patient %s born %s could not be saved (test)" % (lf(WE, C_FIRST), mdy(BD)); wr.ingest()
step("a refusal that is not about the number is tried ONCE, and its words - which name the patient - reach no register and no printed line (the match file, which never leaves the workspace, keeps them)",
     lambda: (wr.clean() and len(wr.amd.added) == 1 and len(wr.reg()["failed"]) == 1 and ok_field(wr.reg()["failed"][0], feed_id=FID, why=FI.FAIL_REFUSED)
              and WE not in json.dumps(wr.reg()) and WE not in wr.out["claimocity_newcharts.py"] and WE in json.dumps(wr.match()[K(WE, C_FIRST, BD)].get("amd_answer", "")), (wr.err, wr.reg(), wr.out.get("claimocity_newcharts.py"))))
w3r = World([msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO, D_FIRST, BD, charges=[(ymd(Y - 1, 4, 4), 0)]), chart(102, ZO, D_FIRST + " B", BD, charges=[(ymd(Y - 1, 8, 8), 0)]), chart(103, ZO, D_FIRST, BD_FAR)]).ingest()
e3r = w3r.match().get(K(ZO, A_FIRST, BD), {})
step("rule 3 in the steps: no chart of that first name, two charts of the same last name carry exactly the date under ANOTHER first name - the live one of them, 'first name differs', and one FYI line for William with the chart id",
     lambda: (w3r.clean() and ok_field(e3r, resolved="pat102", rule=3, status="AMBIGUOUS", flags=["first name differs"], pids=["pat101", "pat102"], candidates=["pat101", "pat102"], for_william=True) and w3r.amd.added == []
              and [l for l in w3r.out["claimocity_resolve.py"].splitlines() if l.startswith("FOR WILLIAM: ")] == ["FOR WILLIAM: pat102 %s (FYI)" % FI.WHY[3]]
              and sorted(c[1] for c in w3r.amd.calls).count("getdemographic") == 2, (w3r.err, e3r, w3r.out)))
# ---- one Claimocity id with two dates in one batch -------------------------------------------------------------------------------------
w2 = World([msg(FID, ZO, A_FIRST, BD), msg(FID, ZO, A_FIRST, P8), msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO, A_FIRST, BD), chart(102, ZO, A_FIRST, BD_FAR)]).ingest()
m2 = w2.match()
step("one Claimocity id with a real date and the placeholder in one batch: decided ONCE with the real date - both name-and-date keys carry the same chart, the same rule",
     lambda: (w2.clean() and set(m2) == {K(ZO, A_FIRST, BD), K(ZO, A_FIRST, P8)} and all(ok_field(v, resolved="pat101", rule=2, status="FOUND", feed_dob="real", feed_ids=[FID]) for v in m2.values()) and w2.amd.added == []
              and len([c for c in w2.amd.calls if c[1] == "getdemographic"]) == 2, (w2.err, m2, w2.amd.calls)))
w3 = World([msg(FID, WE, C_FIRST, P8), msg(FID, WE, C_FIRST, BD)], []).ingest()
m3 = w3.match()
step("... and when the patient is new: ONE chart for the two keys, written with the real date; both keys carry it, the register has one row",
     lambda: (w3.clean() and len(w3.amd.added) == 1 and w3.amd.added[0]["dob"] == mdy(BD) and len(m3) == 2 and all(v.get("resolved") == "pat9001" for v in m3.values()) and len(w3.reg()["created"]) == 1 and ok_field(w3.reg()["created"][0], dob="real", feed_ids=[FID]), (w3.err, w3.amd.added, m3)))
w3n = World([msg(FID, WE, C_FIRST[:-1] + "Z", P8), msg(FID, WE, C_FIRST, BD)], []).ingest()
step("... and when the two messages spell the first name two ways: the one chart is written with the name that came with the real date",
     lambda: (w3n.clean() and len(w3n.amd.added) == 1 and ok_field(w3n.amd.added[0], name=lf(WE, C_FIRST), dob=mdy(BD)) and len(w3n.match()) == 2 and all(v.get("resolved") == "pat9001" for v in w3n.match().values()), (w3n.err, w3n.amd.added)))
w4 = World([msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD), msg(FID3, QU, B_FIRST, ""), msg(FID4, QU, B_FIRST, "")], [chart(101, ZO, A_FIRST, BD, mrn=FID2.upper())]).ingest()
m4 = w4.match()
step("two Claimocity ids under one name and one real date are one patient (rule 1 by either id, both ids on the key); under one name and NO date they are not - that key gets no chart and none is made, for William",
     lambda: (w4.clean() and ok_field(m4.get(K(ZO, A_FIRST, BD), {}), resolved="pat101", rule=1, evidence=["mrn"], feed_ids=[FID, FID2]) and ok_field(m4.get(K(QU, B_FIRST, ""), {}), rule=0, status="AMBIGUOUS", for_william=True)
              and "resolved" not in m4[K(QU, B_FIRST, "")] and w4.amd.added == [], (w4.err, m4)))
w0 = World([msg(FID, ZO, A_FIRST, BD), msg(FID, ZO, A_FIRST, BD_FAR)], [chart(101, ZO, A_FIRST, BD), chart(102, ZO, A_FIRST, BD_FAR)]).ingest()
m0 = w0.match()
step("one Claimocity id with two different REAL dates, each on a chart of its own: nobody can say which chart - NO chart under either key, none made, not 'MISSING', for William",
     lambda: (w0.clean() and len(m0) == 2 and all(ok_field(v, rule=0, status="AMBIGUOUS", for_william=True, flags=[FI.FLAG_TWO_DATES], candidates=["pat101", "pat102"]) and "resolved" not in v for v in m0.values()) and w0.amd.added == []
              and "claimocity_newcharts.py" not in w0.out and any(l.startswith("FOR WILLIAM: ") and FID in l for l in w0.out["claimocity_resolve.py"].splitlines()), (w0.err, m0, w0.out)))
we = World([msg(FID, ZO, A_FIRST, BD), msg("", ZO, A_FIRST, BD), msg("", WE, C_FIRST, BD)], [chart(101, ZO, A_FIRST, BD)]).ingest()
me = we.match()
step("a message with an EMPTY Claimocity id: under a name and real date a Claimocity id also carries it goes with that patient - and the empty id is never written among the ids (the patient map must not learn it); alone it is nobody's: no chart, none made",
     lambda: (we.clean() and ok_field(me.get(K(ZO, A_FIRST, BD), {}), resolved="pat101", rule=2, feed_ids=[FID], decided_for=[FID]) and ok_field(me.get(K(WE, C_FIRST, BD), {}), rule=0, status="AMBIGUOUS", feed_ids=[], for_william=True)
              and "resolved" not in me[K(WE, C_FIRST, BD)] and we.amd.added == [] and not any("" in (v.get("feed_ids") or []) for v in me.values()), (we.err, me)))
# ---- evidence by number: the numbers are read, weighed and never written -------------------------------------------------------------
ws = World([msg(FID, ZO, A_FIRST, BD, ssn=dash(S1), in1=[("Medicare Part B", M2)])], [chart(101, ZO, A_FIRST, BD_FAR, ssn=S1, row_ssn="***-**-" + S1[5:], charges=[(ymd(Y - 1, 3, 3), 0)]), chart(102, ZO, A_FIRST, BD2, members=[M2], charges=[(ymd(Y, 1, 3), 0)])]).ingest()
es = ws.match().get(K(ZO, A_FIRST, BD), {})
step("rule 4 in the steps: the feed's Social Security number (PID-19) equals the chart's - that chart although its date is far (the member number on another chart is weaker), flag 'birth date differs: far'",
     lambda: (ws.clean() and ok_field(es, resolved="pat101", rule=4, status="FOUND", evidence=["ssn"], flags=["birth date differs: far"], pids=["pat101"], for_william=False) and ws.amd.added == [], (ws.err, es)))
wm = World([msg(FID, ZO, A_FIRST, P8, in1=[("Patient Liability", ""), ("Humana Gold", PFX + M1)])], [chart(101, ZO, A_FIRST, BD_FAR, members=["", M1]), chart(102, ZO, A_FIRST, BD2)]).ingest()
em = wm.match().get(K(ZO, A_FIRST, P8), {})
step("rule 4 in the steps: the feed's member number (IN1-49, with the prefix) equals a subscriber number of the chart's plans - that chart, flag 'birth date differs: no birth date from Claimocity'",
     lambda: (wm.clean() and ok_field(em, resolved="pat101", rule=4, evidence=["member"], flags=["birth date differs: no birth date from Claimocity"], feed_dob="none"), (wm.err, em)))
wt = World([msg(FID, ZO, A_FIRST, BD, ssn=S1)], [chart(101, ZO, A_FIRST, BD, ssn=dash(S2))]).ingest()
et = wt.match().get(K(ZO, A_FIRST, BD), {})
step("the same name and date but another nine-digit Social Security number: another person - a NEW chart beside it, flagged for William, with the count of same-name charts",
     lambda: (wt.clean() and len(wt.amd.added) == 1 and ok_field(et, rule=9, flags=["same-name charts not used"], candidates=["pat101"], for_william=True, resolved="pat9001") and ok_field(wt.reg()["created"][0], for_william=True, flags=["same-name charts not used"], dob="real"), (wt.err, et, wt.reg())))
wf = World([msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO, A_FIRST, BD_FAR)]).ingest()
ef = wf.match().get(K(ZO, A_FIRST, BD), {})
step("ONE same-name chart whose date is far (until 11/25/2026 it was taken without a word - 'single same-name chart'): now a new chart beside it, for William to say 'same person or not?'",
     lambda: (wf.clean() and len(wf.amd.added) == 1 and ok_field(ef, rule=9, flags=["same-name charts not used"], candidates=["pat101"], for_william=True, resolved="pat9001")
              and any("FOR WILLIAM" in l and "pat9001" in l and "same person or not?" in l for l in wf.out["claimocity_newcharts.py"].splitlines()), (wf.err, ef, wf.out)))
wi = World([msg(FID, WE, C_FIRST, BD, in1=[("Medicare Part B", M1), ("Humana Gold", M2)])], []); wi.ins_answer = lambda sub: (None, "subscribernum %s is not valid for this carrier (test)" % sub) if sub == M2 else ("ins700", "1"); wi.ingest()
step("a plan AdvancedMD does not take: the register row says so in fixed words - not AdvancedMD's own answer, which names the member number",
     lambda: (wi.clean() and (wi.reg()["created"] or [{}])[0].get("plans") == [{"code": "FLO02", "ins": "ins700", "seq": "1", "from": "Medicare Part B"}, {"code": "HUM01", "err": FI.PLAN_NOT_ADDED}], (wi.err, wi.reg())))
wo = World([msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO, A_FIRST, BD_FAR, members=[M1])])      # (the parser itself stops on a message without a PID line: that message is put behind the parsed ones here)
open(os.path.join(wo.dir, "hl7", STAMP[:8] + "feed.hl7"), "a").write(hl7_text([msg("", "", "", "", in1=[("Medicare Part B", M1)], nopid=True)]))
_u = os.path.join(wo.dir, "feed_unknown_%s.json" % STAMP); json.dump(json.load(open(_u)) + [{"file": STAMP[:8], "FT1": [], "IN1": ["Medicare Part B"], "DG1": []}], open(_u, "w"))
wo.ingest()
eo = wo.match().get(K(ZO, A_FIRST, BD), {})
step("a message without a PID line (nobody's visit) never lends its insurance rows to the patient of the message before it: its member number is no evidence for that patient, and it is not put on that patient's new chart",
     lambda: (wo.clean() and len(wo.match()) == 1 and ok_field(eo, rule=9, evidence=[], flags=["same-name charts not used"], resolved="pat9001") and wo.ins == [] and (wo.reg()["created"] or [{}])[0].get("plans") == [], (wo.err, eo, wo.ins, wo.reg())))
# ---- the lookup lessons: apostrophe, two words, hyphen, a suffix on the chart ---------------------------------------------------------
AP = "O'" + ZO; TW = "VAN " + QU; HY = TH + "-" + YA
wl = World([msg(FID, AP, A_FIRST, BD), msg(FID2, TW, B_FIRST, BD), msg(FID3, HY, C_FIRST, BD), msg(FID4, WE, D_FIRST, BD), msg(FID5, YA + " JR", E_FIRST, BD)],
           [chart(101, "O" + ZO, A_FIRST, BD), chart(102, TW, B_FIRST + " Q", BD), chart(103, TH + " " + YA, C_FIRST, BD), chart(104, WE + " SR", D_FIRST, BD), chart(105, YA, E_FIRST, BD)]).ingest()
ml = wl.match()
step("the name lookups find the chart whatever the spelling of the last name: an apostrophe the chart does not have, two words, a hyphen the chart writes as a space, a suffix on the chart only, a suffix in the feed only",
     lambda: (wl.clean() and [ml.get(K(l, f, BD), {}).get("resolved") for l, f in ((AP, A_FIRST), (TW, B_FIRST), (HY, C_FIRST), (WE, D_FIRST), (YA + " JR", E_FIRST))] == ["pat101", "pat102", "pat103", "pat104", "pat105"] and wl.amd.added == [],
              (wl.err, {k.split("|")[0]: v.get("resolved") for k, v in ml.items()})))
wq = World([msg(FID, AP, A_FIRST, BD)], [chart(101, "O'" + ZO, A_FIRST, BD)]).ingest()
step("... and a name AdvancedMD answers with its apostrophe written as an XML entity is still the same name", lambda: (wq.clean() and wq.match().get(K(AP, A_FIRST, BD), {}).get("resolved") == "pat101", (wq.err, wq.match())))
wk = World([msg(FID, ZO, A_FIRST, BD)], [chart(100 + n, ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)] + [chart(190, ZO, A_FIRST, BD)]).ingest()
step("a last name with more charts than AdvancedMD answers at once (50): the narrow lookup still finds the patient's own chart", lambda: (wk.clean() and wk.match().get(K(ZO, A_FIRST, BD), {}).get("resolved") == "pat190", (wk.err, wk.match().get(K(ZO, A_FIRST, BD)))))
wk2 = World([msg(FID, ZO, A_FIRST, BD)], [chart(100 + n, ZO, "XANA%02dQ" % n, BD_FAR) for n in range(1, 56)] + [chart(190, ZO, A_FIRST, BD)]).ingest()
step("... and when even the narrow lookup comes back full (50 charts share the three letters), the patient's own chart is asked for by its whole first name", lambda: (wk2.clean() and wk2.match().get(K(ZO, A_FIRST, BD), {}).get("resolved") == "pat190", (wk2.err, wk2.match().get(K(ZO, A_FIRST, BD)))))
wk3 = World([msg(FID, ZO, A_FIRST, BD_OFF)], [chart(100 + n, ZO, "XANA%02dQ" % n, BD_FAR) for n in range(1, 56)] + [chart(190, ZO, A_FIRST, BD)]).ingest()
step("a full page of three-letter charts and the patient's own chart with a slip in its date: four letters of the first name bring every full-name chart - rule 5 still decides ('name' cut only)",
     lambda: (wk3.clean() and ok_field(wk3.match().get(K(ZO, A_FIRST, BD_OFF), {}), resolved="pat190", rule=5, cut="name") and wk3.amd.added == [], (wk3.err, {k: v for k, v in wk3.match().get(K(ZO, A_FIRST, BD_OFF), {}).items() if k != "lookup"})))
wk4 = World([msg(FID, ZO, A_FIRST, BD_OFF)], [chart(190, ZO, A_FIRST, BD)] + [chart(200 + n, ZO, A_FIRST + " A%02d" % n, BD_FAR) for n in range(1, 56)]).ingest()
step("more FULL-name charts than AdvancedMD lists (50): nobody can say 'all of them carry one date' - no chart by the slip alone; a new chart, flagged, for William",
     lambda: (wk4.clean() and ok_field(wk4.match().get(K(ZO, A_FIRST, BD_OFF), {}), resolved="pat9001", rule=9, cut="full", for_william=True, flags=["same-name charts not used", FI.FLAG_CUT]) and len(wk4.amd.added) == 1,
              (wk4.err, {k: v for k, v in wk4.match().get(K(ZO, A_FIRST, BD_OFF), {}).items() if k != "lookup"})))
wk5 = World([msg(FID, ZO, "ZYX", BD_OFF)], [chart(190, ZO, "ZYX", BD)] + [chart(200 + n, ZO, "ZYXA%02dX" % n, BD_FAR) for n in range(1, 56)]).ingest()
step("a first name of three letters whose page comes back full cannot be asked more narrowly: full-name charts may be missing - no chart by the slip alone",
     lambda: (wk5.clean() and ok_field(wk5.match().get(K(ZO, "ZYX", BD_OFF), {}), resolved="pat9001", rule=9, cut="full", for_william=True) and len(wk5.amd.added) == 1, (wk5.err, {k: v for k, v in wk5.match().get(K(ZO, "ZYX", BD_OFF), {}).items() if k != "lookup"})))
wk6 = World([msg(FID, YA + " JR", E_FIRST, BD)], [chart(100 + n, YA, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)] + [chart(190, YA, E_FIRST, BD)]).ingest()
step("a suffix the feed writes and the chart does not, under a last name with more charts than AdvancedMD lists: the lookup by the last name's first word AND the first name finds the chart",
     lambda: (wk6.clean() and wk6.match().get(K(YA + " JR", E_FIRST, BD), {}).get("resolved") == "pat190" and wk6.amd.added == [], (wk6.err, {k: v for k, v in wk6.match().get(K(YA + " JR", E_FIRST, BD), {}).items() if k != "lookup"})))
wk7 = World([msg(FID, ZO, A_FIRST, "")], [chart(101, ZO, A_FIRST, BD), chart(102, ZO + " III", A_FIRST, BD2)] + [chart(200 + n, ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)]).ingest()
e7 = wk7.match().get(K(ZO, A_FIRST, ""), {})
step("a namesake whose chart carries a suffix (a father and a son), under a last name with more charts than AdvancedMD lists: the lookup by the BEGINNING of the last name brings both - two dates, so nobody is matched by the name alone (without it only one of the two would be seen, and taken)",
     lambda: (wk7.clean() and ok_field(e7, rule=9, candidates=["pat101", "pat102"], for_william=True, flags=["same-name charts not used", "no birth date from Claimocity"], resolved="pat9001") and len(wk7.amd.added) == 1 and wk7.amd.added[0]["dob"] == P_MDY, (wk7.err, {k: v for k, v in e7.items() if k != "lookup"})))
wb = World([msg(FID, ZO, A_FIRST, BD_OFF), msg(FID2, QU, B_FIRST, BD2), msg(FID3, WE, C_FIRST, BD)], [chart(101, ZO, A_FIRST, BD), chart(111, QU, B_FIRST, BD2)]); wb.amd.no_begin = True; wb.ingest()
mb = wb.match()
step("an AdvancedMD that does not answer the 'begins with' form of the last name does not stop the feed: the step says so ONCE, asks it no more, and matches nobody by the name alone - the same date still decides, a slip does not, every new chart is flagged for William",
     lambda: (wb.clean() and ok_field(mb.get(K(QU, B_FIRST, BD2), {}), resolved="pat111", rule=2, cut="full") and ok_field(mb.get(K(ZO, A_FIRST, BD_OFF), {}), rule=9, cut="full", for_william=True, flags=["same-name charts not used", FI.FLAG_CUT])
              and ok_field(mb.get(K(WE, C_FIRST, BD), {}), rule=9, for_william=True, flags=[FI.FLAG_CUT]) and len(wb.amd.added) == 2
              and len([l for l in wb.out["claimocity_match.py"].splitlines() if l.startswith("MATCH: AdvancedMD did not answer the lookup by the BEGINNING of the last name")]) == 1 and len([n for n in wb.amd.asked if "%," in n]) == 2,
              (wb.err, {k.split("|")[0][:3]: {x: y for x, y in v.items() if x != "lookup"} for k, v in mb.items()}, wb.amd.asked)))
def _odd(charts, **opts):
    w = World([msg(FID, ZO, A_FIRST, BD)], list(charts))
    for k, v in opts.items(): setattr(w.amd, k, v)
    return w.ingest()
step("AdvancedMD's answers are read as they come: attributes in single quotes, a chart read whose patient element carries the bare chart number", lambda: (lambda w: (w.clean() and ok_field(w.match()[K(ZO, A_FIRST, BD)], resolved="pat101", rule=1), (w.err, w.match())))(_odd([chart(101, ZO, A_FIRST, BD_FAR, mrn=FID)], quote="'", bare_id=True)))
for _row, _what in (('<patient id="17" chart="C9"/>', "carries no chart id"), ('<patient id=pat7 chart="C9"/>', "cannot be read")):
    step("a lookup answer with a row that %s STOPS the match step - a chart left out of a lookup without a word is how a second chart gets made" % _what,
         lambda _row=_row: (lambda w: (w.err["claimocity_match.py"] != "" and w.amd.added == [] and "claimocity_resolve.py" not in w.out and not w.amd.refused, (w.err, w.match())))(_odd([chart(101, ZO, A_FIRST, BD)], odd_row=_row)))
# ---- what the steps must never do --------------------------------------------------------------------------------------------------------
g1 = World([msg(FID, WE, C_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_OFF)], [chart(101, ZO, A_FIRST, BD)])
g1.run("claimocity_match.py", READS, argv=("feed_unknown_%s.json" % STAMP,)); mg = g1.match()
step("the match step alone decides nothing: no entry says MISSING (which would read 'make a new chart'), none carries a chart, each waits for the resolve step - and an older resolve step cannot work on it (no chart ids under 'pids')",
     lambda: (not g1.err["claimocity_match.py"] and len(mg) == 2 and all(v["status"] == "AMBIGUOUS" and "resolved" not in v and v["pids"] == [] and v.get("rule") == 0 and v.get("for_william") is True and v.get("why") in FI.WHY_WORDS for v in mg.values()), (g1.err, mg)))
step("the match file never holds a number: no Social Security number, no member number, also not a chart's - only chart ids, names, dates and the evidence WORDS", lambda: (lambda w: w.clean() and not [n for n in (S1, dash(S1), S1[5:], M2) if n in open(os.path.join(w.dir, "feed_match_%s.json" % STAMP)).read()])(ws))
g2 = World([msg(FID, WE, C_FIRST, BD)], [])
_old = {K(WE, C_FIRST, BD): {"status": "MISSING", "pids": [], "amd_names": [], "feed_ids": [FID]}}
json.dump(_old, open(os.path.join(g2.dir, "feed_match_%s.json" % STAMP), "w")); g2.run("claimocity_resolve.py", READS)
step("the resolve step refuses a match file that this version's match step did not write (an older copy's): it stops, changes nothing, decides nothing", lambda: (g2.err["claimocity_resolve.py"] != "" and g2.match() == _old and g2.amd.calls == [], (g2.err, g2.match())))
g2.run("claimocity_newcharts.py", NEWCHART)
step("the new-chart step makes NO chart on an older step's word (an entry that says MISSING but was not decided by rule 9): no addpatient, a failed row with a fixed reason and the Claimocity id",
     lambda: (not g2.err["claimocity_newcharts.py"] and g2.amd.added == [] and g2.reg()["created"] == [] and len(g2.reg()["failed"]) == 1 and ok_field(g2.reg()["failed"][0], feed_id=FID, why=FI.FAIL_NOT_DECIDED) and "resolved" not in g2.match()[K(WE, C_FIRST, BD)], (g2.err, g2.reg())))
def _stops(kind, action, times, script="claimocity_match.py", charts=()):
    w = World([msg(FID, ZO, A_FIRST, BD)], list(charts)); w.amd.bad[action] = [kind] * times; w.ingest(); return w
step("a name lookup AdvancedMD answers with a fault is asked again; answered the second time, everything is as usual", lambda: (lambda w: (w.clean() and w.match()[K(ZO, A_FIRST, BD)].get("resolved") == "pat101", (w.err, w.match())))(_stops("fault", "lookuppatient", 1, charts=[chart(101, ZO, A_FIRST, BD)])))
for _kind, _what in (("fault", "a fault"), ("page", "a page that is no AdvancedMD answer"), ("raise", "no answer at all")):
    step("a name lookup that brings %s twice STOPS the match step (until 11/25/2026 it read as 'no chart of this name' and a new chart was made): nothing decided, no chart made, the next run reads the files again" % _what,
         lambda _kind=_kind: (lambda w: (w.err["claimocity_match.py"] != "" and "claimocity_resolve.py" not in w.out and w.amd.added == [] and not any(v["status"] == "MISSING" for v in w.match().values()) and not w.amd.refused, (w.err, w.match())))(_stops(_kind, "lookuppatient", 2, charts=[chart(101, ZO, A_FIRST, BD)])))
step("a chart that cannot be read (twice) STOPS the match step too - no decision on half the facts", lambda: (lambda w: (w.err["claimocity_match.py"] != "" and w.amd.added == [] and not any(v.get("resolved") or v["status"] == "MISSING" for v in w.match().values()), (w.err, w.match())))(_stops("fault", "getdemographic", 2, charts=[chart(101, ZO, A_FIRST, BD)])))
def _activity(times, kind="raise"):
    w = World([msg(FID, ZO, A_FIRST, BD_OFF)], [chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 2), 0)]), chart(102, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 12, 14), 0)])]); w.txh_bad["pat102"] = [kind] * times; w.ingest(); return w
step("a chart's activity that fails once is read again: the live chart is still the right one", lambda: (lambda w: (w.clean() and w.match()[K(ZO, A_FIRST, BD_OFF)].get("resolved") == "pat102", (w.err, w.match())))(_activity(1)))
for _kind in ("raise", "fault"):
    step("a chart's activity that cannot be read twice (%s) STOPS the resolve step: the live chart is not guessed, the entry stays undecided (no chart, not MISSING)" % ("no answer" if _kind == "raise" else "a fault, which reads like 'no charges'"),
         lambda _kind=_kind: (lambda w: (w.err["claimocity_resolve.py"] != "" and w.amd.added == [] and all(v["status"] == "AMBIGUOUS" and "resolved" not in v for v in w.match().values()), (w.err, w.match())))(_activity(2, _kind)))
check("no step sent AdvancedMD an action it may not send, in any scenario above (the match and resolve steps only read; the new-chart step sends addpatient, the chart read, the responsible party and the number probe)",
      sum(len(w.amd.refused) for w in WORLDS) == 0 and len(WORLDS) > 25, [w.amd.refused for w in WORLDS if w.amd.refused][:3])
step("the match and resolve steps read and never write, also by their own text: no AdvancedMD action word but lookuppatient / getdemographic in them, and resolve asks AdvancedMD nothing but the chart activity",
     lambda: (set(re.findall(r'amd\.msg\(\s*"(\w+)"', read("claimocity_match.py"))) == READS and re.findall(r'amd\.msg\(\s*"(\w+)"', read("claimocity_resolve.py")) == [] and "txh.fetch" in read("claimocity_resolve.py")
              and not [c for w in WORLDS for c in w.amd.calls if c[0] == "claimocity_resolve.py"], [c for w in WORLDS for c in w.amd.calls if c[0] == "claimocity_resolve.py"][:3]))
# ---- what the driver, the import and the reconciliation read from the match file ----------------------------------------------------
def _unknown_keys(w):
    try: return {str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8] for m in json.load(open(os.path.join(w.dir, "feed_unknown_%s.json" % STAMP))) if m.get("pid") is not None}
    except (OSError, ValueError): return set()
_done = [w for w in WORLDS if w.out.get("claimocity_resolve.py") is not None and not w.err.get("claimocity_match.py") and not w.err.get("claimocity_resolve.py")]
def _entry_ok(v):
    return (v.get("status") in ("FOUND", "AMBIGUOUS", "MISSING") and isinstance(v.get("feed_ids"), list) and "" not in v["feed_ids"] and isinstance(v.get("pids"), list) and isinstance(v.get("resolution"), str)
            and (("resolved" not in v) or re.fullmatch(r"pat\d+", v["resolved"]) is not None) and (v["status"] != "FOUND" or "resolved" in v) and (v["status"] != "MISSING" or v.get("rule") == 9)
            and (v.get("rule") != 0 or "resolved" not in v) and (v.get("rule") not in (1, 2, 3, 4, 5, 6, 7, 8) or "resolved" in v))
T("the match file keeps its contract in every scenario that ran through: EVERY name-and-date key of the batch has an entry (the import looks each one up), and each entry carries what the driver and the reconciliation read - a status of the three words, the Claimocity ids (never an empty one: the patient map would learn it), 'resolved' exactly when a chart was chosen or made, MISSING only for rule 9",
  lambda: (len(_done) >= 25 and all(_unknown_keys(w) and _unknown_keys(w) == set(w.match()) for w in _done) and all(_entry_ok(v) for w in _done for v in w.match().values()),
           [(sorted(_unknown_keys(w) ^ set(w.match())), [v for v in w.match().values() if not _entry_ok(v)][:1]) for w in _done if _unknown_keys(w) != set(w.match()) or not all(_entry_ok(v) for v in w.match().values())][:2]))
# ---- privacy: registers, printed lines and the fields the driver copies ----------------------------------------------------------------
def _hits(text, tokens): return sorted({tok for tok in tokens if tok and tok.lower() in text.lower()})
_printed = "\n".join(PRINTED)
T("privacy: no line the three steps printed, in any scenario, holds an invented name, birth date, Social Security number or member number", lambda: (len(_printed) > 2000 and _hits(_printed, TOKENS | NUMBERS) == [], _hits(_printed, TOKENS | NUMBERS)))
def _free(w):
    out = []
    for v in w.match().values(): out.append(json.dumps({k: v.get(k) for k in tuple(FI.PHI_FREE_FIELDS) + ("status", "pids", "feed_ids", "resolved", "resolution", "decided_for")}))
    return "\n".join(out)
T("privacy: the fields of the match file that the driver copies (rule, why, flags, candidates, evidence, feed_dob, for_william) and status / pids / feed_ids / resolved / resolution hold none of them, in any scenario",
  lambda: (tuple(FI.PHI_FREE_FIELDS) == ("rule", "why", "flags", "candidates", "evidence", "feed_dob", "for_william") and _hits("\n".join(_free(w) for w in WORLDS), TOKENS | NUMBERS) == [] and all(FI.problems(v) == [] for w in WORLDS for v in w.match().values() if "rule" in v),
           _hits("\n".join(_free(w) for w in WORLDS), TOKENS | NUMBERS)))
def _regs(w): return "\n".join(open(os.path.join(w.dir, "registers", f)).read() for f in sorted(os.listdir(os.path.join(w.dir, "registers"))))
T("privacy: no register the steps wrote holds any of them (the new-chart register travels to the repository)", lambda: (sum(1 for w in WORLDS if _regs(w)) >= 8 and _hits("\n".join(_regs(w) for w in WORLDS), TOKENS | NUMBERS) == [], _hits("\n".join(_regs(w) for w in WORLDS), TOKENS | NUMBERS)))
def _files(w):
    out = []
    for d, _dirs, fs in os.walk(w.dir):
        if os.path.basename(d) == "hl7": continue
        out += [open(os.path.join(d, f), errors="replace").read() for f in fs]
    return "\n".join(out)
T("privacy: the Social Security numbers and member numbers the steps read (the feed's and the charts') are in NO file of any workspace - only in the feed files they came from", lambda: (len(NUMBERS) >= 6 and _hits("\n".join(_files(w) for w in WORLDS), NUMBERS) == [], _hits("\n".join(_files(w) for w in WORLDS), NUMBERS)))
# ---- the files themselves --------------------------------------------------------------------------------------------------------------
SENTENCES = {"claimocity_match.py": "THE MATCH STEP ONLY GATHERS: EVERY ENTRY IT WRITES IS UNDECIDED UNTIL claimocity_resolve.py APPLIES THE IDENTITY RULE",
             "claimocity_resolve.py": "THE CHART IS CHOSEN BY THE IDENTITY RULE (feed_identity.decide), ONCE PER CLAIMOCITY ID - NEVER BY A SINGLE SAME-NAME CHART ALONE",
             "claimocity_newcharts.py": "A NEW CHART IS MADE ONLY ON RULE 9 OF THE IDENTITY RULE, ONE PER CLAIMOCITY ID, NEVER WITH AN EMPTY BIRTH DATE"}
def _header(src): return "\n".join(itertools.takewhile(lambda l: l.startswith("#"), src.splitlines()))
for _f, _s in SENTENCES.items():
    check("%s: its PLAIN ENGLISH header carries the one sentence only this version has (the mirror will know the file by it), and the step loads feed_identity" % _f,
          read(_f).startswith("# PLAIN ENGLISH (") and _s in _header(read(_f)) and "feed_identity" in loads(read(_f)), _header(read(_f))[:200])
check("feed_identity.py starts with its PLAIN ENGLISH header and carries the rule's version line", read("feed_identity.py").startswith("# PLAIN ENGLISH (") and re.search(r'(?m)^IDENTITY_RULE_VERSION = "\d{4}-\d\d-\d\d\.\d+"', read("feed_identity.py")) is not None)
check("the old rule is gone from the steps: no 'single same-name chart', no first letters of a name in a printed line or a register row",
      not re.search(r"single same-name chart\"|last\[:5\]|k\[:6\]|\[:12\] \+ \"\*\"", read("claimocity_match.py") + read("claimocity_resolve.py") + read("claimocity_newcharts.py")))
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror"))
try: import phi_gate
except Exception as e: phi_gate = None
for _f in ("feed_identity.py",) + STEPS:
    _t = read(_f)
    T("the PHI gate that scrubs every file before a commit (tools/mirror/phi_gate.py) finds nothing to change or to block in %s" % _f, lambda _t=_t: (_t != "" and phi_gate.redact(_t, {}, code=True) == _t and phi_gate.check(_t) == [], phi_gate.check(_t)[:3]))
_me = open(os.path.abspath(__file__)).read()
T("... nor in this test: every invented value is put together at run time", lambda: (phi_gate.redact(_me, {}, code=True) == _me and phi_gate.check(_me) == [], phi_gate.check(_me)[:3]))
import shutil
for _w in WORLDS: shutil.rmtree(_w.dir, ignore_errors=True)      # the throwaway workspaces (invented data only) are not left behind
print("\n%d check(s): %d ok, %d FAIL" % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS)))
if FAILS:
    print("FAILED: " + "; ".join(f[:90] for f in FAILS[:12]) + (" ..." if len(FAILS) > 12 else ""))
sys.exit(1 if FAILS else 0)
