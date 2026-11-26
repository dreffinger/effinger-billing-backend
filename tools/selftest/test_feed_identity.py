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
#      11/25/2026 (review of the identity rule - three things it reproduced): a chart that writes the last name with an apostrophe, a
#      space, a period or a hyphen the FEED does not have is weighed like any other (several hundred patients put together at random
#      go through the match and resolve steps and must come out as the rule answers when it is given EVERY chart of the stand-in); a
#      lookup form AdvancedMD does not answer never makes a second chart (wherever in a run the two unanswered asks fall); and one name
#      with no birth date under two Claimocity ids is weighed for each id and entered when the rule gives both the same chart.
#      11/25/2026 (the independent verification - a rule without proof could put a visit on ANOTHER person's chart; each case below was
#      seen failing here before the rule was changed): the same feed is run several times, as the driver runs it (Feed: the patient map
#      learns the charts, a file is read again while a patient of it has no chart) - of three new ids of one name the one without a
#      birth date ends on a chart of its own and never on the chart of either dated one, whichever id sorts first; a newcomer's second
#      id never goes on a long-time namesake's chart in the run that makes the newcomer a chart; two ids of rule 3's relation get one
#      chart; a chart with no birth date takes neither two far-apart patients of one batch nor, over three runs, every same-name
#      patient that comes (the patient map); a patient that waits for a chart AdvancedMD refused is for William, in true words; an id
#      with proof of its own chart keeps it on a key several ids share; a chart William called a duplicate is never offered - the
#      proper chart stands in its place; the new-chart register keeps none of the feed's payer text. And what must stay: one person
#      under two new ids ends on one chart, a patient with proof never waits, a batch in which nobody gets a new chart is decided as
#      before, a chart nobody in the map owns is chosen as on 11/8.
#      11/25/2026 (the checkers of those fixes - identity rule .4; each case below was seen failing here before the rule was changed):
#      the patient map holds back only a chart WITHOUT a date of its own (rules 6 and 8) - a patient the feed already knows, sent under
#      a NEW Claimocity id with the placeholder, goes to her own chart by rule 7 without a question, also when that chart is another
#      id's in the map, and one person under two new ids, the second without a date, ends on ONE chart with BOTH visits; a slip in the
#      date (rule 5) does not wait for ANOTHER patient's new chart - only an answer by the name alone (rules 6 to 8) and a patient that
#      would get a new chart do; and the rule's version line changed with the rule, in the helper and in the two tables that pin it.
#   The stand-in AdvancedMD refuses every action a step is not supposed to send (a stray write fails the test) and counts addpatient.
# Every name, birth date, Social Security number and member number here is invented, and each is put together at run time (lf, ymd, the
#   + signs) so that no such value sits in this file as a literal: tools/mirror/phi_gate.py scrubs this file like any other before a
#   commit - the last section checks that it finds nothing to change here or in the four helpers.
# Run: python3 tools/selftest/test_feed_identity.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, importlib.util, io, re, contextlib, random, itertools, datetime, collections, unicodedata
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
# 11/25/2026 (review of the identity rule): a PLACEHOLDER number shown masked is no number either. Until then the last four of nine nines on a
# lookup row (the stars and four nines) counted as proof of another person beside any real number of the feed: the chart with the patient's own name and birth
# date was passed over and a second chart made. Four digits that are all one digit, or 6789 (one to nine in a row), are the mask of a placeholder;
# so are the four digits a side shows when the SAME side shows a nine-digit placeholder ending in them.
T("a masked placeholder is no number: four digits all alike, or 6789 - neither the last four nor anything else", lambda: [FI.ssn4_key(x) for x in ("***-**-9999", "xxx-xx-1111", "7777", "***-**-6789", "0000")] == [""] * 5)
T("... so a masked placeholder on the chart is neither evidence nor proof of another person beside the feed's real number", lambda: EV({"ssn": S1}, {"ssn": "***-**-9999"}) == ([], False) and EV({"ssn": S1}, {"ssn": ["xxx-xx-6789", ""]}) == ([], False)
  and EV({"ssn": "***-**-1111"}, {"ssn": dash(S1)}) == ([], False))
T("... and the four digits a side shows beside its OWN nine-digit placeholder ending in them are that placeholder's mask: nothing usable (a real number beside them still counts)",
  lambda: EV({"ssn": S1}, {"ssn": ["***-**-" + S3[5:], "000" + S3[3:]]}) == ([], False) and EV({"ssn": S1}, {"ssn": ["***-**-" + S3[5:], "9" + S3[1:]]}) == ([], False)
  and EV({"ssn": S1}, {"ssn": ["***-**-" + S1[5:], "000" + S3[3:]]}) == (["ssn4"], False) and EV({"ssn": S1}, {"ssn": ["***-**-" + S3[5:], dash(S3)]}) == ([], True))
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
X("a chart with the patient's name and birth date whose number is a masked PLACEHOLDER is the patient's chart (rule 2) - the placeholder proves nobody else (11/25/2026)", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", B, ssn="***-**-9999")], "pat1", 2)
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
# 11/25/2026 (review of the identity rule): the lookup for ANY first name (rule 3) can come back full too - until then nobody noticed
X("a list that may be cut only for charts under ANOTHER first name ('first'): every name candidate is there - rule 6 is still asked", dict(F(ZO, "XANTHIA", B), cut="first"), [C(1, ZO, "XANTHIA", P8)], "pat1", 6, ["chart has no birth date"], william=True)
X("... and so are rule 5", dict(F(ZO, "XANTHIA", B_DIGIT), cut="first"), [C(1, ZO, "XANTHIA", B)], "pat1", 5, ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [], william=False)
X("... rule 7", dict(F(QU, "ZEBEDIAH", P8), cut="first"), [C(1, QU, "ZEBEDIAH", B2)], "pat1", 7, ["no birth date from Claimocity"], william=False)
X("... and rule 3 itself, for the charts that were listed", dict(F(ZO, "XANTHIA", B), cut="first"), [C(1, ZO, "ELSPETH", B)], "pat1", 3, ["first name differs"], william=True)
X("... but a NEW chart for a patient with a real date is flagged, for William: a chart of that last name and date under another first name (rule 3) may be among those not listed", dict(F(WE, "OTTOLINE", B), cut="first"), [], None, 9, _CUT, william=True, feed_dob="real")
X("... beside same-name charts as well", dict(F(ZO, "XANTHIA", B), cut="first"), [C(1, ZO, "XANTHIA", FARD)], None, 9, NOT_USED + _CUT, william=True)
X("... not when Claimocity sent no birth date: rule 3 is never asked then, so nothing it could have found is missing (the new chart is for William anyway - face sheet needed)", dict(F(WE, "OTTOLINE", P8), cut="first"), [], None, 9, ["no birth date from Claimocity"], william=True, feed_dob="none")
# ... and a patient can be weighed without the lookup that finds every SPELLING of the last name (AdvancedMD did not answer it for this one, though it does answer it): 'spelling'
X("a list that may lack the charts that write the last name another way than the feed ('spelling' - all the steps ever saw until 11/25/2026): no rule is switched off for it - the slip is read (rule 5)", dict(F(ZO, "XANTHIA", B_DIGIT), cut="spelling"), [C(1, ZO, "XANTHIA", B)], "pat1", 5,
  ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [], william=False)
X("... rule 6 is asked", dict(F(ZO, "XANTHIA", B), cut="spelling"), [C(1, ZO, "XANTHIA", P8)], "pat1", 6, ["chart has no birth date"], william=True)
X("... rule 7", dict(F(QU, "ZEBEDIAH", P8), cut="spelling"), [C(1, QU, "ZEBEDIAH", B2)], "pat1", 7, ["no birth date from Claimocity"], william=False)
X("... rule 8", dict(F(QU, "ZEBEDIAH", ""), cut="spelling"), [C(1, QU, "ZEBEDIAH", "")], "pat1", 8, ["no birth date on either side"], william=True)
X("... but a NEW chart made on such a list is flagged, for William (is there a chart of this patient already?) - with a real date", dict(F(WE, "OTTOLINE", B), cut="spelling"), [], None, 9, _CUT, william=True, feed_dob="real")
X("... and with none (beside 'face sheet needed')", dict(F(WE, "OTTOLINE", P8), cut="spelling"), [], None, 9, ["no birth date from Claimocity"] + _CUT, william=True, feed_dob="none")
T("... what goes to William for it: the question, and - with no date - the face sheet too", lambda: (lambda a, b: (len(a) == 1 and "may be incomplete" in a[0] and "pat900" in a[0] and len(b) == 2 and "face sheet needed" in b[1], (a, b)))(
    FI.william_lines(D(dict(F(WE, "OTTOLINE", B), cut="spelling"), []), "pat900", FID), FI.william_lines(D(dict(F(WE, "OTTOLINE", P8), cut="spelling"), []), "pat900", FID)))
# ---- rules without proof and the patient map (11/25/2026, the independent verification) -------------------------------------------------
# Rules 6, 7 and 8 choose a chart by the name alone. A chart with no birth date took every same-name patient that came, one run after the other:
# a patient with a real date by rule 6, the next one without a date by rule 8 - two people on one chart, the second one's visit on the first one's
# plan. The feed's patient map knows which Claimocity id every chart the feed has used belongs to ("owned": the match step says it of each chart):
# a chart WITHOUT a date of its own that belongs there to ANOTHER Claimocity id is not taken on the name alone (rules 6 and 8) - no chart, none
# made, for William. A chart nobody in the map owns (it was there before the feed: the 11/8 patient's own case) is chosen as before, and so is
# every chart a rule WITH proof chooses.
# Identity rule .4 (the checkers of that verification): rule 7 is NOT among the rules the map holds back. Claimocity sent no date and every
# same-name chart carries ONE date - that is William's written rule for the very case: a patient the feed already knows, sent under a NEW
# Claimocity id with the placeholder, goes to her own chart without a question. Round 1 held rule 7 back with the two others: such a patient
# was not entered and the same question stood at the top run after run - about ten right placements lost for each wrong one avoided.
_OWNED = getattr(FI, "WHY_OWNED", "?")
X("rule 6 on a chart the patient map gives to ANOTHER Claimocity id: not taken on the name alone - no chart, none made, for William; the chart in question is the one named",
  F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", P8, owned=True)], None, 0, [], william=True, candidates=["pat1"], feed_dob="real")
X("rule 8 on such a chart: the same", F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", "", owned=True)], None, 0, [], william=True, candidates=["pat1"], feed_dob="none")
for nd in NONE_DATES:
    X("rule 7 is NOT held back by the map (identity rule .4): Claimocity sent no date (%r) and the same-name chart carries one - the patient the feed already knows, sent under a NEW Claimocity id, goes to her own chart although that chart "
      "is another Claimocity id's in the map; no flag but the missing date, not for William (round 1 held it back like rules 6 and 8: no chart, the same question run after run)" % (nd if nd != P8 else "placeholder"),
      F(QU, "ZEBEDIAH", nd), [C(1, QU, "ZEBEDIAH", B2, owned=True)], "pat1", 7, ["no birth date from Claimocity"], william=False, candidates=["pat1"], feed_dob="none", group=["pat1"])
X("... rule 7 with several same-name charts of ONE date, one of them the map's (and not the live one): the live chart of the group, as on 11/8 - the map holds nothing back where the charts carry a date", F(QU, "ZEBEDIAH", P8),
  [C(1, QU, "ZEBEDIAH", B2, last_dos=ymd(2026, 1, 1), charges=1, owned=True), C(2, QU, "ZEBEDIAH", B2, last_dos=ymd(2026, 9, 1), charges=3)], "pat2", 7, ["no birth date from Claimocity"], william=False, group=["pat1", "pat2"])
T("... the answer of a chart that IS held back (no date of its own - rule 8 here) says why in fixed words of its own, and what goes to William is ONE line that names the Claimocity id, the chart and the question",
  lambda: (lambda d, ls: (d["why"] == _OWNED and _OWNED in FI.WHY_WORDS and FI.problems(d) == [] and d["new_chart"] is False and len(ls) == 1 and FID in ls[0] and "pat1" in ls[0] and "same person or not?" in ls[0], (d, ls)))(
      D(F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", "", owned=True)]), FI.william_lines(D(F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", "", owned=True)]), "", FID)))
X("... also when the chart the map gives to another Claimocity id is not the live one of the group but another chart of it: the rule takes the live chart of a GROUP it calls one person's - that person has another Claimocity id (rule 8: two charts, neither with a date)",
  F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", "", last_dos=ymd(2026, 1, 1), charges=1, owned=True), C(2, QU, "ZEBEDIAH", "", last_dos=ymd(2026, 9, 1), charges=3)], None, 0, [], william=True, candidates=["pat1"])
X("... and the same for rule 6 (the feed has a date, neither chart has one)",
  F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", "", last_dos=ymd(2026, 1, 1), charges=1, owned=True), C(2, ZO, "XANTHIA", P8, last_dos=ymd(2026, 9, 1), charges=3)], None, 0, [], william=True, candidates=["pat1"], feed_dob="real")
X("a chart NOBODY in the map owns is chosen as before - rule 7, the 11/8 patient's own case (the six charts were there before the feed)", F(QU, "ZEBEDIAH", P8),
  [C(n, QU, "ZEBEDIAH", B2, last_dos=ymd(2026, n - 10, 3), charges=20 - n, owned=False) for n in range(11, 17)], "pat16", 7, ["no birth date from Claimocity"], william=False)
X("... rule 6 and rule 8 as well", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", P8, owned=False)], "pat1", 6, ["chart has no birth date"], william=True)
X("rule 5 is NOT held back by the map: the slip is evidence of its own - the full name and a birth date one keystroke from the chart's (William 11/25/2026: 'where we know the correct dob but claimocity sends the wrong one')",
  F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANTHIA", B, owned=True)], "pat1", 5, ["birth date differs: " + FI.SLIP_DIGIT] if not FI_ERR else [], william=False)
X("rules 1 to 4 are not held back either: the Claimocity id on the chart", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", FARD, mrn=FID, owned=True)], "pat1", 1, [])
X("... the same name and birth date", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B, owned=True)], "pat1", 2, [])
X("... the same last name and birth date under another first name", F(ZO, "XANTHIA", B), [C(1, ZO, "ELSPETH", B, owned=True)], "pat1", 3, ["first name differs"])
X("... a number in common", F(ZO, "XANTHIA", B, ssn=S1), [C(1, ZO, "XANTHIA", P8, ssn=S1, owned=True)], "pat1", 4, ["birth date differs: chart has no birth date"])
X("one Claimocity id under its real date and the placeholder in one batch, the real one the chart's own: decided once, by the date (rule 2) - that the chart is another Claimocity id's in the map plays no part", dict(F(ZO, "XANTHIA"), dobs=[B, P8]), [C(1, ZO, "XANTHIA", B, owned=True)], "pat1", 2, [])
T("which rules those are is said once, in the rule itself: 1 to 4 choose by proof, 5 to 8 by what the same-name charts look like; 6 to 8 have nothing but the name (such an answer waits for a chart the batch is making), "
  "and of those 6 and 8 take a chart WITHOUT a date of its own (the patient map holds such a chart back; identity rule .4: not rule 7)",
  lambda: (tuple(FI.RULES_BY_PROOF), tuple(FI.RULES_BY_CHARTS), tuple(FI.RULES_NAME_ALONE), tuple(FI.RULES_CHART_NO_DOB)) == ((1, 2, 3, 4), (5, 6, 7, 8), (6, 7, 8), (6, 8)))
# ---- a chart William called a duplicate (11/25/2026, the independent verification; his word of 11/9/2026) -----------------------------------
# After his 'duplicate' the feed patient was re-pointed in the map, but the duplicate chart stood in AdvancedMD and caught that patient's NEXT
# Claimocity id by rule 2 without a word. A listed duplicate is never the chart a visit goes to: the PROPER chart stands in its place. What
# speaks for the duplicate - its name, its birth date, its numbers: what Claimocity knows that person by - speaks for the proper chart
# ("also": the names and dates of its listed duplicates), and for the rules that go by what the charts look like the two are ONE chart.
_DUP = getattr(FI, "FLAG_DUPLICATE", "?")
def ALSO(last, first, d8): return [{"name": lf(last, first), "dob": d8}]
X("a proper chart that stands in the place of a listed duplicate: the feed's date is the DUPLICATE's (the wrong date Claimocity keeps sending) - that is name and the same birth date, and the visit goes to the proper chart; a flag says so",
  F(ZO, "XANTHIA", FARD), [C(1, ZO, "XANTHIA", B, also=ALSO(ZO, "XANTHIA", FARD))], "pat1", 2, [_DUP], william=False, candidates=["pat1"])
X("... the proper chart's own date still decides as before, and the flag still says a duplicate stood behind it", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B, also=ALSO(ZO, "XANTHIA", FARD))], "pat1", 2, [_DUP])
X("... no birth date from Claimocity: the two are ONE chart with ONE date, the proper chart's - rule 7 (as two charts their two dates made a NEW chart for a patient who had two already)",
  F(ZO, "XANTHIA", P8), [C(1, ZO, "XANTHIA", B, also=ALSO(ZO, "XANTHIA", FARD))], "pat1", 7, ["no birth date from Claimocity", _DUP], william=False)
X("... a slip is read from the proper chart's own date only", F(ZO, "XANTHIA", B_DIGIT), [C(1, ZO, "XANTHIA", B, also=ALSO(ZO, "XANTHIA", FARD))], "pat1", 5, ["birth date differs: " + FI.SLIP_DIGIT, _DUP] if not FI_ERR else [])
X("... a date that is neither the proper chart's nor the duplicate's: a new chart beside it, for William - as for any chart", F(ZO, "XANTHIA", B2), [C(1, ZO, "XANTHIA", B, also=ALSO(ZO, "XANTHIA", FARD))], None, 9, NOT_USED, william=True)
X("... also a date one digit off the DUPLICATE's: the duplicate's date counts where it is exactly the feed's (proof) - no slip is read from a date that may itself be the wrong one", F(ZO, "XANTHIA", ymd(1952, 9, 28)),
  [C(1, ZO, "XANTHIA", B, also=ALSO(ZO, "XANTHIA", FARD))], None, 9, NOT_USED, william=True)
X("... the duplicate was written under another first name than the proper chart: the proper chart is a name candidate through its duplicate's name",
  F(ZO, "XANTHIA", FARD), [C(1, ZO, "ELSPETH", B, also=ALSO(ZO, "XANTHIA", FARD))], "pat1", 2, [_DUP])
X("... and under the proper chart's OWN other first name rule 3 reads the duplicate's date as well (the same last name, another first name, exactly the date)",
  F(ZO, "XANTHIA", FARD), [C(1, ZO, "ELSPETH", B, also=ALSO(ZO, "ELSPETH", FARD))], "pat1", 3, ["first name differs", _DUP], william=True)
X("... a chart without a listed duplicate carries no such flag (and 'also' of another shape counts for nothing)", F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", B, also="pat7")], "pat1", 2, [])
T("the flag is one of the fixed words, with no digit in it", lambda: _DUP in FI.FLAG_WORDS and not re.search(r"\d", _DUP))
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
        if rnd.random() < 0.15: f["cut"] = rnd.choice(["first", "spelling", "name", "full"])
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
            if (r in (5, 7, 8) and f.get("cut") == "full") or (r == 6 and f.get("cut") in ("name", "full")): why.append("rule %d on a list that may be cut short" % r)
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
def _pat(ids, keys, decide=None, shared=()): return {"ids": sorted(ids), "keys": sorted(keys), "decide_keys": sorted(keys if decide is None else decide), "shared_keys": sorted(shared)}
T("the patients of a batch: one Claimocity id under its real date and under the placeholder is ONE patient - both keys are decided together", lambda: FI.patients({k1: [FID], k2: [FID], k3: [FID2]}, TODAY) == ([_pat([FID], [k1, k2]), _pat([FID2], [k3])], {}))
T("... two Claimocity ids under one name and one REAL date are one patient", lambda: FI.patients({k1: [FID2, FID], k2: [FID]}, TODAY) == ([_pat([FID, FID2], [k1, k2])], {}))
T("... also when the feed carries the SAME Social Security number for both, or one for only one of them", lambda: all(FI.patients({k1: [FID, FID2]}, TODAY, ssn_of=x.get) == ([_pat([FID, FID2], [k1])], {}) for x in ({FID: [S1], FID2: [dash(S1)]}, {FID2: [S1]})))
# 11/25/2026 (review of the identity rule): until then such a key was decided for nobody before anything was weighed - no lookup, no chart, neither visit entered
T("... two Claimocity ids under one name and NO date are not known to be one person, and the import can give their key only ONE chart: each id is still a patient of its own and is weighed - the key is theirs TOGETHER "
  "(the resolve step writes a chart under it only when the rule gives every one of them the same chart), each id keeps its other keys",
  lambda: (lambda ps, un: (ps == [_pat([FID], [k1, k2], [k1], [k2]), _pat([FID2], [k2, k3], [k3], [k2])] and un == {}, (ps, un)))(*FI.patients({k1: [FID], k2: [FID, FID2], k3: [FID2]}, TODAY)))
T("... also when neither of them comes with another key", lambda: (lambda r: (r == ([_pat([FID], [k2], [], [k2]), _pat([FID2], [k2], [], [k2])], {}), r))(FI.patients({k2: [FID2, FID]}, TODAY)))
# 11/25/2026 (the independent verification): such a key was decided for nobody before anything was weighed - also when one of the ids had PROOF of
# its own chart (the chart's own Social Security number), run after run. Each id is weighed; the key itself still never gets ONE chart.
T("... but not when the feed itself carries two different Social Security numbers for them (two people for certain): that key never gets ONE chart, whatever chart each would get - "
  "each id is still weighed on its own (the key stands among the keys they share AND among those nobody can decide together), so that an id with proof of its own chart keeps it",
  lambda: (lambda ps, un: (ps == [_pat([FID], [k2], [], [k2]), _pat([FID2], [k2], [], [k2])] and list(un) == [k2] and un[k2] == FI.WHY_SHARED, (ps, un)))(*FI.patients({k2: [FID, FID2]}, TODAY, ssn_of={FID: [S1], FID2: [dash(S2)]}.get)))
T("... the same Social Security number on both, or one on only one side, proves nothing against it", lambda: all(FI.patients({k2: [FID, FID2]}, TODAY, ssn_of=x.get) == ([_pat([FID], [k2], [], [k2]), _pat([FID2], [k2], [], [k2])], {}) for x in ({FID: [S1], FID2: [dash(S1)]}, {FID: [S1]}, {})))
T("... two Claimocity ids under one name and one real date whose Social Security numbers DIFFER are two people: not put together, the key never ONE chart - and each weighed on its own, like the two above",
  lambda: (lambda ps, un: (ps == [_pat([FID], [k1], [], [k1]), _pat([FID2], [k1], [], [k1])] and list(un) == [k1], (ps, un)))(*FI.patients({k1: [FID, FID2]}, TODAY, ssn_of={FID: [S1], FID2: [dash(S2)]}.get)))
T("... a message without a Claimocity id is nobody's: its key is not decided - unless a Claimocity id carries the same name and the same real date",
  lambda: (lambda ps, un: ps == [_pat([FID], [k1])] and list(un) == [k4] and un[k4] in FI.WHY_WORDS)(*FI.patients({k1: [FID, ""], k4: [""]}, TODAY)))
T("... and under a name with NO date that a Claimocity id also carries nobody can say whose it is: that key is decided for nobody (it is not one the rule could settle - a message without an id is never weighed), the id keeps its other keys",
  lambda: (lambda ps, un: (ps == [_pat([FID], [k1, k2], [k1])] and list(un) == [k2] and un[k2] in FI.WHY_WORDS, (ps, un)))(*FI.patients({k1: [FID], k2: [FID, ""]}, TODAY)))
def _shared_cases():      # the answers of patients that came under ONE name with no birth date, each decided on its own
    one = [C(1, QU, "ZEBEDIAH", B2)]; two = one + [C(2, QU, "ZEBEDIAH", B)]; other = dict(F(QU, "ZEBEDIAH", P8), id=FID2)
    return {"r2": D(F(QU, "ZEBEDIAH", B2), one), "r7": D(other, one), "r2b": D(F(QU, "ZEBEDIAH", B), two), "new": D(other, two), "none": D(dict(F(QU, "ZEBEDIAH"), dobs=[B, B2]), two),
            "r8": D(other, [C(3, QU, "ZEBEDIAH", "")])}
def _sh(*names): return (lambda c: FI.shared_answer([c[n] for n in names]))(_shared_cases())
T("the cases below are what they are meant to be: rule 2 and rule 7 on one chart, rule 2 on another, a new chart, nobody, rule 8", lambda: (lambda c: ([(c[n]["rule"], c[n]["chart"]) for n in ("r2", "r7", "r2b", "new", "none", "r8")] == [(2, "pat1"), (7, "pat1"), (2, "pat2"), (9, None), (0, None), (8, "pat3")], c))(_shared_cases()))
T("a name-and-date key several patients share: the rule gave every one of them, each on its own, the SAME chart - the key carries that chart, under the weakest of their answers (the highest rule number: its flags say what was not known), in any order",
  lambda: (lambda s: (s["chart"] == "pat1" and s["rule"] == 7 and s["why"] == FI.WHY[7] and s["flags"] == ["no birth date from Claimocity"] and s["candidates"] == ["pat1"] and s["group"] == ["pat1"] and s["feed_dob"] == "none"
                      and s["for_william"] is False and s["new_chart"] is False and FI.problems(s) == [] and s == _sh("r7", "r2") and _sh("r7", "r7")["rule"] == 7, s))(_sh("r2", "r7")))
T("... the rule gave them two DIFFERENT charts: not known to be one person - NO chart under the key and none made, for William; the charts that were considered are named",
  lambda: (lambda s: (s["chart"] is None and s["rule"] == 0 and s["why"] == FI.WHY_SHARED and s["candidates"] == ["pat1", "pat2"] and s["for_william"] is True and s["new_chart"] is False and s["flags"] == [] and FI.problems(s) == [] and s == _sh("r2b", "r7"), s))(_sh("r7", "r2b")))
T("... one of them a chart, the other a new chart - or both a new chart (nobody knows them to be one person: never ONE new chart for two ids, never two under one key) - or one of them not decided: no chart, none made, for William",
  lambda: all((lambda s: s["chart"] is None and s["rule"] == 0 and s["why"] == FI.WHY_SHARED and s["for_william"] is True and s["new_chart"] is False and FI.problems(s) == [])(_sh(*ns)) for ns in (("r2", "new"), ("new", "r7"), ("new", "new"), ("r7", "none"), ("none", "none"), ())))
T("... what goes to William then is one line that names the Claimocity id; a chart the rule gave them all by rule 8 is still the FYI of rule 8",
  lambda: (lambda a, b: (len(a) == 1 and FID in a[0] and len(b) == 1 and "pat3" in b[0] and "(FYI)" in b[0], (a, b)))(FI.william_lines(_sh("r7", "r2b"), "", FID), FI.william_lines(_sh("r8", "r8"), "pat3", FID)))
# 11/25/2026 (the independent verification): what else a key that several patients share can say
T("... one of them WAITS for a new chart of this batch: the key waits with it - no chart, none made, the plain words of the wait, NOT for William (the next run decides it)",
  lambda: (lambda c: (lambda s: (s["chart"] is None and s["rule"] == 0 and s["why"] == FI.WHY_SAME_RUN and s["for_william"] is False and s["new_chart"] is False and FI.problems(s) == [] and FI.william_lines(s, "", FID) == []
                                 and s == FI.shared_answer([FI.waits(c["new"]), c["r7"]]), s))(FI.shared_answer([c["r7"], FI.waits(c["new"])])))(_shared_cases()))
T("... every one of them was held back for the SAME reason (the chart, which has no date of its own, belongs to another Claimocity id in the patient map): the key says that reason and names that chart - not 'several ids ... not known to be one person'",
  lambda: (lambda o_: (lambda s: (o_["why"] == FI.WHY_OWNED and s["rule"] == 0 and s["why"] == FI.WHY_OWNED and s["candidates"] == ["pat1"] and s["for_william"] is True and FI.problems(s) == [], s))(FI.shared_answer([o_, dict(o_)])))(
      D(F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", "", owned=True)])))
T("... and when the chart carries a date (rule 7 for each of them - the map holds nothing back, identity rule .4) the key carries that chart: both ids of the 11/8 kind are entered",
  lambda: (lambda o_: (lambda s: (o_["rule"] == 7 and s["chart"] == "pat1" and s["rule"] == 7 and s["for_william"] is False and FI.problems(s) == [], s))(FI.shared_answer([o_, dict(o_)])))(
      D(F(QU, "ZEBEDIAH", P8), [C(1, QU, "ZEBEDIAH", B2, owned=True)])))
T("... a key whose ids the feed itself shows to be two people ('apart') never gets ONE chart, also when the rule gives each of them the same one",
  lambda: (lambda s: (s["chart"] is None and s["rule"] == 0 and s["why"] == FI.WHY_SHARED and s["for_william"] is True and s["candidates"] == ["pat1"], s))(FI.shared_answer([_shared_cases()["r7"], _shared_cases()["r7"]], apart=True)))
# two patients of ONE batch on one chart by the name alone (11/25/2026, the independent verification: rule 6 twice - two people on one chart with no birth date)
FAR_ = lambda *ps: FI.same_chart_far([{"chart": c, "rule": r, "dobs": list(d)} for c, r, d in ps])
T("same_chart_far: two patients of one batch whom the name alone puts on ONE chart and whose real birth dates are FAR apart - neither answer stands; equal dates, a slip between them, or no date on one side leave both",
  lambda: FAR_(("pat1", 6, [B]), ("pat1", 6, [FARD])) == [0, 1] and FAR_(("pat1", 6, [B]), ("pat1", 6, [B_DIGIT])) == [] and FAR_(("pat1", 6, [B]), ("pat1", 6, [B])) == [] and FAR_(("pat1", 6, [B]), ("pat1", 8, [])) == []
  and FAR_(("pat1", 6, [B, B2]), ("pat1", 6, [FARD, B_DIGIT])) == [] and FAR_() == [])
T("... a patient with PROOF of that chart (rules 1 to 4) keeps it and only the other one loses it; two patients with proof are not touched; two charts, or no chart, are no pair",
  lambda: FAR_(("pat1", 4, [B]), ("pat1", 6, [FARD])) == [1] and FAR_(("pat1", 2, [B]), ("pat1", 4, [FARD])) == [] and FAR_(("pat1", 6, [B]), ("pat2", 6, [FARD])) == [] and FAR_((None, 9, [B]), (None, 9, [FARD])) == [])
T("... the answer of such a patient: no chart, none made, rule 0 in fixed words of its own, for William - ONE line that names the Claimocity id and the chart in question",
  lambda: (lambda a: (lambda ls: ((a["chart"], a["rule"], a["why"], a["new_chart"], a["for_william"], a["candidates"], a["feed_dob"], FI.problems(a)) == (None, 0, FI.WHY_FAR_PAIR, False, True, ["pat7"], "real", [])
                                  and len(ls) == 1 and FID in ls[0] and "pat7" in ls[0], (a, ls)))(FI.william_lines(a, "", FID)))(FI.undecided(D(F(ZO, "XANTHIA", B), [C(7, ZO, "XANTHIA", ""), C(8, ZO, "XANDER", FARD)]), FI.WHY_FAR_PAIR, ["pat7"])))
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
# 11/25/2026 (the independent verification): two feed patients on one chart gave William the same FYI line twice, and neither said which Claimocity id it was about
T("for William: the FYI of rules 3, 6 and 8 names the Claimocity id it is about - or every id, when it is said for several at once",
  lambda: (lambda one, two: (len(one) == 1 and one[0].startswith("pat1 ") and "(FYI)" in one[0] and FID in one[0] and len(two) == 1 and FID in two[0] and FID2 in two[0], (one, two)))(
      _w(D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", P8)]), "pat1"), _w(D(F(ZO, "XANTHIA", B), [C(1, ZO, "XANTHIA", P8)]), "pat1", [FID, FID2])))
T("for William: a patient that waits behind a chart that could NOT be made brings a line that says so and names it; the wait as such brings none, and neither does a key whose ids each went to the chart their own proof names",
  lambda: (lambda wt: (lambda bad, plain, each: (len(bad) == 1 and FID in bad[0] and "could not be made" in bad[0] and plain == [] and each == [], (bad, plain, each)))(
      _w(dict(wt, why=FI.WHY_WAIT_FAILED, for_william=True)), _w(wt), _w(dict(wt, why=FI.WHY_EACH_PROOF))))(FI.waits(D(F(ZO, "XANTHIA", B), [C(7, ZO, "XANTHIA", FARD)]))))
T("the new fixed words are in the list the registers are checked against, and which of them are no question for William is said once (the wait, each id by its own proof); the wait's own words do not say a chart IS made before it is",
  lambda: ({FI.WHY_SAME_RUN, FI.WHY_WAIT_FAILED, FI.WHY_OWNED, FI.WHY_FAR_PAIR, FI.WHY_EACH_PROOF} <= set(FI.WHY_WORDS) and set(FI.PLAIN_WORDS) == {FI.WHY_SAME_RUN, FI.WHY_EACH_PROOF}
           and "is made" not in FI.WHY_SAME_RUN and len({FI.WHY_SAME_RUN, FI.WHY_WAIT_FAILED, FI.WHY_OWNED, FI.WHY_FAR_PAIR, FI.WHY_EACH_PROOF, FI.WHY_SHARED}) == 6))
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
def spelt(pattern): return re.search(r"(?:^|%)[A-Z]%[A-Z]%", pattern.upper().split(",")[0]) is not None      # a lookup with a % between the LETTERS of the last name (the form that finds every spelling)
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
        s.no_spell = False; s.mute_spell = False; s.no_inner = False; s.junk_spell = False; s.also = []; s.limits = []
    def msg(s, action, cls, attrs=None, children=""): return '<ppmdmsg action="%s" class="%s" %s>%s</ppmdmsg>' % (action, cls, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
    def post(s, body, timeout=0):
        a = dict(re.findall(r'(\w+)="([^"]*)"', body.split(">", 1)[0])); action = a.get("action", "?")
        s.calls.append((s.script, action))
        if action == "lookuppatient" and "name" in a: s.limits.append((a["name"], timeout))      # how long the step is ready to wait for each name lookup (0 = it did not say: amd.post's own three minutes)
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
            if s.no_spell and spelt(a.get("name", "")): return FAULT % "Server Error (test)"       # ... that does not take a % between the letters of the last name
            if s.mute_spell and spelt(a.get("name", "")): return OKAY % "<patientlist></patientlist>"      # ... that answers such a lookup with no chart, whatever it holds
            if s.no_inner and "%" in a.get("name", "")[:-1]: return FAULT % "Server Error (test)"         # ... that takes a % at the END of a lookup only (the two lookups the steps made until 11/25/2026, for a name without an apostrophe)
        if "code" in a: rows = [] if s.blind else [c for c in s.charts.values() if c["chartno"].upper() == a["code"].upper()]
        elif s.junk_spell and spelt(a.get("name", "")): rows = sorted(s.charts.values(), key=lambda c: (c["last"], c["first"], c["id"]))[:50]      # ... that does not understand such a lookup and answers its first 50 charts, whatever was asked
        else: rows = sorted((c for c in s.charts.values() if like(a.get("name", ""), lf(c["last"], c["first"])) or c["id"] in s.also), key=lambda c: (c["last"], c["first"], c["id"]))[:50]      # AdvancedMD answers the first 50 by name (s.also: charts it lists for a reason of its own, say a former name)
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
        pid = "pat%d" % s.nextid; s.nextid += 1; last, _, first = p["name"].partition(","); _d = re.fullmatch(r"(\d\d)/(\d\d)/(\d{4})", p.get("dob", ""))
        s.charts[pid] = chart(int(pid[3:]), last, first, _d.group(3) + _d.group(1) + _d.group(2) if _d else "", mrn=p.get("additionalmrn", ""), chartno=p["chart"], made=p)      # the chart carries the date it was written with (a later run of the same feed lists it)
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
    """One throwaway workspace (the feed files of one batch, parsed by the real parser) and the stand-in AdvancedMD behind it. pmap: the workspace's
    patient map as the driver keeps it ({Claimocity id: chart id}); dups: the charts William called duplicates (the file's content - or its text, to
    write a file that cannot be read). Neither file is written when it is not given: a workspace before the feed's first run."""
    def __init__(s, msgs, charts=(), pmap=None, dups=None):
        s.dir = tempfile.mkdtemp(prefix="feedid_"); os.makedirs(os.path.join(s.dir, "registers")); os.makedirs(os.path.join(s.dir, "hl7"))
        open(os.path.join(s.dir, "hl7", STAMP[:8] + "feed.hl7"), "w").write(hl7_text(msgs))
        json.dump({"car6085": ["FLO02", "FLORIDA MEDICARE"], "car6285": ["HUM01", "HUMANA"]}, open(os.path.join(s.dir, "carriers_rich.json"), "w"))
        for _name, _doc in (("claimocity_patient_map.json", pmap), ("feed_duplicate_charts.json", dups)):
            if _doc is not None: open(os.path.join(s.dir, "registers", _name), "w").write(_doc if isinstance(_doc, str) else json.dumps(_doc))
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
class Feed:
    """SEVERAL RUNS of one feed (11/25/2026, the independent verification: what the rule does to a patient shows only over two or three runs). The driver's
    own part between the steps is kept here as small as it is in claimocity_ingest.py: a message whose Claimocity id the patient map knows is entered on
    the map's chart without a lookup; for the others the three steps run; an entry names the chart of each Claimocity id it was decided for ("resolved" -
    and, on a key several ids share, the chart an id's own proof names: "by_proof"); the map learns those charts; and a file is read again by the next
    run while one of its messages has no chart. AdvancedMD's charts - the new ones too - stand from run to run. A message is entered once."""
    def __init__(s, charts=(), pmap=None, dups=None, **opts):
        s.charts = [dict(c) for c in charts]; s.pmap = dict(pmap or {}); s.dups = dups; s.opts = opts; s.files = []; s.entered = []; s.worlds = []; s.nextid = 9001; s._in = set(); s.made = []
    def drop(s, *msgs): s.files.append(list(msgs)); return s
    def run(s, **opts):
        msgs = [m for f in s.files for m in f]; new = [m for m in msgs if m["fid"] not in s.pmap]; by = {}; w = None
        if new:
            w = World(new, s.charts, pmap=s.pmap, dups=s.dups); w.amd.nextid = s.nextid; w.amd.blind = False      # (the number probe sees the numbers the earlier runs took)
            for k, v in dict(s.opts, **opts).items(): setattr(w.amd, k, v)
            before = set(w.amd.charts); w.ingest(); s.charts = [dict(c) for c in w.amd.charts.values()]; s.nextid = w.amd.nextid; s.made += sorted(set(w.amd.charts) - before)
            if w.clean():
                for k, v in w.match().items():
                    b = by.setdefault(k, {})
                    if v.get("resolved"): b.update({i: v["resolved"] for i in (v.get("decided_for") or v.get("feed_ids") or [])})
                    for i, c in (v.get("by_proof") or {}).items(): b.setdefault(i, c)
        s.worlds.append(w); left = []
        for f in s.files:
            done = True
            for m in f:
                c = s.pmap.get(m["fid"]) or by.get(K(m["last"], m["first"], m["dob"]), {}).get(m["fid"])
                if not c: done = False
                elif id(m) not in s._in: s._in.add(id(m)); s.entered.append((m["fid"], c))
            if not done: left.append(f)
        for b in by.values(): s.pmap.update(b)
        s.files = left; return w
    def runs(s, n):
        for _ in range(n):
            if s.files: s.run()
        return s
    def clean(s): return all(w.clean() for w in s.worlds if w is not None)
    def on(s, fid): return sorted({c for i, c in s.entered if i == fid})      # the chart(s) the visits of one Claimocity id were entered on
    def said(s, n=None): return [l for w in (s.worlds if n is None else s.worlds[n:n + 1]) if w is not None for l in _william(w)]      # the lines for William, of every run or of run n
    def log(s, n, script="claimocity_resolve.py"): return (s.worlds[n].out.get(script, "") if n < len(s.worlds) and s.worlds[n] is not None else "")
    def born(s, pid): return next((c["dob"] for c in s.charts if c["id"] == pid), None)
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

# ---- the name as the match step asks AdvancedMD for it (feed_identity.lookup_forms), read the stand-in's strict way ---------------------
# 11/25/2026 (review of the identity rule): the rule compares last names by their LETTERS, the lookups asked for them as the feed writes
# them - so a chart with an apostrophe, a space, a period or a hyphen the feed does not have was never listed, and a namesake's chart was
# taken by the name alone, or a second chart made, without a word.
def LK(last, first="XANTHIA"): return FI.lookup_forms(last, first)
FAMILIES = [["O" + ZO, "O'" + ZO, "O " + ZO], ["MC" + QU, "MC " + QU, "Mc" + QU.title()], ["VAN" + WE, "VAN " + WE, "VAN-" + WE], ["DELA" + YA, "DE LA " + YA, "DELA " + YA, "DE-LA-" + YA],
            ["ST" + TH, "ST " + TH, "ST. " + TH, "ST." + TH], [TH + YA, TH + "-" + YA, TH + " " + YA], [ZO, ZO + " JR", ZO + " SR.", ZO + " III"]]      # each: one last name to the rule, spelled several ways
WRITTEN = [f[1] for f in FAMILIES[:4]] + ["ST. " + TH, TH + "-" + YA, ZO + " III"]      # of each family the spelling that writes every apostrophe, space, period and hyphen
T("the families of spellings below are what they are meant to be: one last name each to the rule, and no two of them the same name", lambda: all(len({FI.last_key(x) for x in fam}) == 1 for fam in FAMILIES) and len({FI.last_key(fam[0]) for fam in FAMILIES}) == len(FAMILIES))
T("the letters form of a last name - its letters with a % between them: every chart that spells the same letters answers to it, whatever it writes between them and after them (any first name: the lookup of rule 3)",
  lambda: [(a, b) for fam in FAMILIES for a in fam for b in fam if not like(LK(a)["letters"] + "%", lf(b, "ELSPETHA"))] == [])
T("... and with the first three letters of the first name, a % between them too (X.A.N. and XAN THIA are XAN to the rule)",
  lambda: [(a, b, f) for fam in FAMILIES for a in fam for b in fam for f in ("XANTHIA", "XAN THIA K", "X.A.N.", "xander") if not like("%s%%, %s%%" % (LK(a, "Xan-thia")["letters"], LK(a, "Xan-thia")["first3"]), lf(b, f))] == [])
T("... it is still a search for THIS name: a last name with a letter less, or with two letters the other way round, does not answer",
  lambda: not like(LK(ZO)["letters"] + "%", lf(ZO[:-1], "X")) and not like(LK(ZO)["letters"] + "%", lf(ZO[1] + ZO[0] + ZO[2:], "X")) and not like("%s%%, %s%%" % (LK(ZO)["letters"], LK(ZO)["first3"]), lf(ZO, "ELSPETHA")))
T("what the forms are: letters and % only; a trailing suffix word is no part of them; the words form keeps the words whole with a % for whatever stands between them",
  lambda: (lambda vals: (all(re.fullmatch(r"[A-Z%]+", v) for v in vals) and LK(ZO)["letters"] == "%".join(ZO) and LK(ZO + " Jr.")["letters"] == "%".join(ZO) and LK(ZO)["words"] == ZO and LK(ZO + " III")["words"] == ZO
                         and LK("o'" + ZO.lower())["words"] == "O%" + ZO and LK("De La " + YA)["words"] == "DE%LA%" + YA and LK("St. " + TH)["words"] == "ST%" + TH and LK("V")["letters"] == "V", vals))(
      [v for fam in FAMILIES for a in fam for v in (LK(a)["letters"], LK(a)["words"], LK(a)["first3"], LK(a)["first4"], LK(a)["first_word"])]))
T("the words form finds the chart whatever it writes where the FEED has an apostrophe, a space, a period or a hyphen - and any longer form of the last name (a suffix, a second name)",
  lambda: [(a, b) for fam, a in zip(FAMILIES, WRITTEN) for b in fam if not like(LK(a)["words"] + "%", lf(b, "ELSPETHA"))] == [] and like(LK(ZO)["words"] + "%", lf(ZO + " SR.", "X")) and like(LK(ZO)["words"] + "%", lf(ZO + "-" + QU, "X")))
T("... but not a chart that has one where the feed has NONE (the lookups the step made until now): that takes the letters form",
  lambda: not like(LK("O" + ZO)["words"] + "%", lf("O'" + ZO, "X")) and like(LK("O" + ZO)["letters"] + "%", lf("O'" + ZO, "X")) and not like(LK("DELA" + YA)["words"] + "%", lf("DE LA " + YA, "X")))
T("the first name's forms: three letters, four letters of its first word (none when that word has fewer - every full-name candidate begins with them), the whole first word when it has more than four",
  lambda: ([(LK(ZO, f)["first3"], LK(ZO, f)["first4"], LK(ZO, f)["first_word"]) for f in ("Xanthia", "ANN K", "MARY ANN", "A.J.", "Jo Ann", "X'ORWEN")]
           == [("X%A%N", "X%A%N%T", "%".join("XANTHIA")), ("A%N%N", None, ""), ("M%A%R", "M%A%R%Y", ""), ("A%J", None, ""), ("J%O%A", None, ""), ("X%O%R", "X%O%R%W", "X%O%R%W%E%N")]))
T("... every full-name candidate answers to the four letters (a middle name, a longer form, a hyphen written as a space)",
  lambda: [(a, b) for a, b in (("XANTHIA", "XANTHIA K"), ("XANTHIA", "XANT"), ("XANT", "XANTHIANNE"), ("MARY", "MARYANN"), ("MARY-ANN", "MARY ANN"), ("X'ORWEN", "XORWEN"))
           if FI.name_kind(ZO, a, ZO, b) != "full" or not like("%s%%, %s%%" % (LK(ZO, a)["letters"], LK(ZO, a)["first4"]), lf(ZO, b))] == [])
_ENYE = ZO[:2] + "Ñ" + ZO[2:]      # an accented letter inside the invented name
T("a letter that carries an accent is left out of the forms (a gap: AdvancedMD may hold it with or without) - the chart answers either way, and the two ways of writing the accent give the same forms",
  lambda: (LK(_ENYE)["letters"] == "%".join(ZO) and LK(_ENYE)["words"] == ZO[:2] + "%" + ZO[2:] and like(LK(_ENYE)["letters"] + "%", lf(_ENYE, "X")) and like(LK(_ENYE)["words"] + "%", lf(ZO[:2] + "N" + ZO[2:], "X"))
           and LK(unicodedata.normalize("NFD", _ENYE)) == LK(_ENYE) and FI.name_kind(_ENYE, "X", ZO[:2] + "N" + ZO[2:], "X") == "full", LK(_ENYE)))
T("a name that begins with something else than a plain letter is asked for with a % in front (never a search that begins in the middle of every other name)",
  lambda: (LK("'T " + ZO)["letters"] == "%T%" + "%".join(ZO) and like(LK("'T " + ZO)["letters"] + "%", lf("'T " + ZO, "X")) and like(LK("'T " + ZO)["letters"] + "%", lf("T" + ZO, "X")) and LK("'T " + ZO)["words"] == "%T%" + ZO
           and LK(ZO, "'Xan")["first3"] == "%X%A%N" and not LK(ZO)["letters"].startswith("%") and not LK(ZO)["words"].startswith("%"), LK("'T " + ZO)))
T("a chart AdvancedMD lists for a lookup must itself answer to it - the letters of the pattern, in their order, among the letters of its name (case, accents and whatever stands between them aside): that is how the step tells an answer from a page of anything",
  lambda: (all(FI.answers_to(p, n) for p, n in ((LK(ZO)["letters"] + "%", lf("o'" + ZO.lower() + " III", "Elspetha")), ("%s%%, %s%%" % (LK(ZO)["letters"], LK(ZO)["first3"]), lf(_ENYE.replace("Ñ", "") , "XAN-THIA")), (ZO + "%", lf(ZO + "-" + QU, "X")),
                                                 (LK(ZO[:2] + "N" + ZO[2:])["letters"] + "%", lf(_ENYE, "X")), ("%", lf(QU, "X")), ("", "")))
           and not any(FI.answers_to(p, n) for p, n in ((LK(ZO)["letters"] + "%", lf(QU, "ZEBEDIAH")), (LK(ZO)["letters"] + "%", lf(ZO[:-1], "XANTHIA")), ("%s%%, %s%%" % (LK(ZO)["letters"], LK(ZO)["first3"]), lf(ZO, "ELSPETHA")), (ZO + "%", "")))))
def _sprinkle(rnd, word, p=0.2): return "".join(c + (rnd.choice(["'", " ", "-", ".", ". "]) if rnd.random() < p and i < len(word) - 1 else "") for i, c in enumerate(word))
def _forms_hold(n):
    """n pairs of a feed name and a chart name put together at random from the invented words - apostrophes, spaces, hyphens and periods sprinkled into both, a suffix on either,
    upper and lower case: whatever the rule calls the same name, the forms must find (what is NOT found is never weighed - that is how a second chart gets made)."""
    rnd = random.Random(2511); bad = []; kinds = collections.Counter()
    cores = [ZO, QU, WE, TH, YA, "O" + ZO, "MC" + QU, "DELA" + YA, TH + YA, "NG", "LI"]; sufs = ["", "", "", " JR", " SR.", " III", " V"]; firsts = ["XANTHIA", "XANT", "XANTHIANNE", "XANDRA", "XAN", "AJ", "JOANN", "MARYANN", "MARY", "ELSPETHA"]
    for i in range(n):
        core = rnd.choice(cores); fl = _sprinkle(rnd, core) + rnd.choice(sufs); cl = _sprinkle(rnd, core) + rnd.choice(sufs); ff = _sprinkle(rnd, rnd.choice(firsts), 0.1); cfirst = _sprinkle(rnd, rnd.choice(firsts), 0.1) + rnd.choice(["", "", " K", " Q."])
        if rnd.random() < 0.3: cl = cl.title(); cfirst = cfirst.lower()
        kind = FI.name_kind(fl, ff, cl, cfirst); f = FI.lookup_forms(fl, ff); name = lf(cl, cfirst); kinds[kind] += 1
        ok = kind == "" or like(f["letters"] + "%", name)                                                             # the same last name under any first name
        if kind in ("name", "full"): ok = ok and like("%s%%, %s%%" % (f["letters"], f["first3"]), name)               # a name candidate
        if kind == "full" and f["first4"] is not None: ok = ok and like("%s%%, %s%%" % (f["letters"], f["first4"]), name)      # a full-name candidate
        if not ok: bad.append((fl, ff, cl, cfirst, kind, f))
    return bad, kinds
T("3,000 pairs of names put together at random: every chart the rule calls the same last name answers to the letters form, every name candidate to it with three letters of the first name, every full-name candidate with four",
  lambda: (lambda bad, kinds: (bad == [] and kinds["surname"] > 100 and kinds["name"] > 100 and kinds["full"] > 100, (bad[:2], dict(kinds))))(*_forms_hold(3000)))

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
              and rn.get("plans") == [{"code": "FLO02", "ins": "ins701", "seq": "1"}] and wn.ins == [("pat9001", "car6085", M1)], (rn, wn.ins)))
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
step("rule 3 in the steps: no chart of that first name, two charts of the same last name carry exactly the date under ANOTHER first name - the live one of them, 'first name differs', and one FYI line for William with the chart id and the Claimocity id",
     lambda: (w3r.clean() and ok_field(e3r, resolved="pat102", rule=3, status="AMBIGUOUS", flags=["first name differs"], pids=["pat101", "pat102"], candidates=["pat101", "pat102"], for_william=True) and w3r.amd.added == []
              and [l for l in w3r.out["claimocity_resolve.py"].splitlines() if l.startswith("FOR WILLIAM: ")] == ["FOR WILLIAM: pat102 %s (FYI) - Claimocity id %s" % (FI.WHY[3], FID)]
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
# ---- one name with NO birth date under two Claimocity ids in one batch (11/25/2026, review of the identity rule) --------------------------
# Until then such a key was decided for nobody before anything was weighed: no lookup, no chart, neither visit entered - although the rule
# gives each of the two ids, on its own, the same chart (and did, when the same two messages came in two batches).
def _steps(msgs, charts, **opts):
    w = World(list(msgs), list(charts))
    for k, v in opts.items(): setattr(w.amd, k, v)
    return w.ingest()
def _william(w): return [l for o_ in w.out.values() for l in o_.splitlines() if l.startswith("FOR WILLIAM: ")]
def brief(e): return {k: v for k, v in (e or {}).items() if k not in ("lookup", "sharers")}
SIX = [chart(n, QU, B_FIRST, BD2, charges=[(ymd(Y - 1, n - 110, 3), 0)] * (117 - n)) for n in range(111, 117)]      # the six same-name charts of 11/8: one date, pat116 the live one
x1 = _steps([msg(FID, QU, B_FIRST, P8), msg(FID2, QU, B_FIRST, P8)], SIX); ex1 = x1.match().get(K(QU, B_FIRST, P8), {})
step("the 11/8 patient under TWO Claimocity ids in one batch (the placeholder under both, six same-name charts with one date): each id is weighed on its own, the rule gives both the live chart, and their one name-and-date key carries it - "
     "both visits are entered, both ids stand on the key (the patient map learns them), no chart is made",
     lambda: (x1.clean() and ok_field(ex1, resolved="pat116", rule=7, status="AMBIGUOUS", flags=["no birth date from Claimocity"], feed_ids=[FID, FID2], decided_for=[FID, FID2], pids=["pat%d" % n for n in range(111, 117)], feed_dob="none", for_william=False)
              and ex1.get("why") == FI.WHY[7] and x1.amd.added == [] and "claimocity_newcharts.py" not in x1.out and len(x1.amd.asked) >= 2 and _william(x1) == [], (x1.err, brief(ex1), _william(x1), x1.amd.asked)))
def _again(w):      # the resolve step run a second time over the file it has just written
    before = w.match(); said, _e = w.run("claimocity_resolve.py", READS)
    return (w.clean() and w.match() == before and "NEW CHART" not in said and "FOR WILLIAM" not in said and "RESOLVE 2 Claimocity patient(s): rule 7 x2;" in said, (w.err, said, {k[-8:]: brief(v) for k, v in w.match().items()}))
step("... and the resolve step run a second time over that file writes - and says - the same again (the two ids on the key are still two patients, each decided on its own; never one patient with no chart to weigh, for whom a new chart would be called)", lambda: _again(x1))
x2 = _steps([msg(FID, ZO, A_FIRST, BD), msg(FID, ZO, A_FIRST, P8), msg(FID2, ZO, A_FIRST, P8)], [chart(101, ZO, A_FIRST, BD)]); m2x = x2.match()
step("... one of the two ids also comes with its real date: it is decided ONCE, with that date (rule 2) - and its message under the placeholder is entered too, because the rule gives the other id, on its own, the same chart (rule 7); "
     "the key they share says the weaker of the two answers",
     lambda: (x2.clean() and ok_field(m2x.get(K(ZO, A_FIRST, BD), {}), resolved="pat101", rule=2, status="FOUND", decided_for=[FID], feed_ids=[FID], for_william=False)
              and ok_field(m2x.get(K(ZO, A_FIRST, P8), {}), resolved="pat101", rule=7, status="FOUND", flags=["no birth date from Claimocity"], decided_for=[FID, FID2], feed_ids=[FID, FID2], for_william=False)
              and x2.amd.added == [] and _william(x2) == [], (x2.err, {k[-8:]: brief(v) for k, v in m2x.items()}, _william(x2))))
x3 = _steps([msg(FID, ZO, A_FIRST, BD), msg(FID, ZO, A_FIRST, P8), msg(FID2, ZO, A_FIRST, P8)], [chart(101, ZO, A_FIRST, BD), chart(102, ZO, A_FIRST, BD_FAR)]); m3x = x3.match(); e3x = m3x.get(K(ZO, A_FIRST, P8), {})
step("... but when the rule does NOT give them the same chart (the second id, with no date, stands before two same-name charts with two dates - on its own it would get a new chart): the key they share gets NO chart of its own and none is made for it - "
     "never one chart for two ids nobody knows to be one person. The first id has PROOF of its own chart (the same name and birth date, under its own key): its message under the shared key goes there too - "
     "'by_proof' names the chart of each id that has proof (11/25/2026, the independent verification: until then neither message was entered, run after run). The second id stays without a chart: William's ONE line names it, and what each would get on its own",
     lambda: (x3.clean() and ok_field(m3x.get(K(ZO, A_FIRST, BD), {}), resolved="pat101", rule=2, status="FOUND", decided_for=[FID])
              and ok_field(e3x, rule=0, status="AMBIGUOUS", decided_for=[FID2], by_proof={FID: "pat101"}, feed_ids=[FID, FID2], for_william=True, candidates=["pat101", "pat102"], why=FI.WHY_SHARED, flags=[]) and "resolved" not in e3x
              and x3.amd.added == [] and "claimocity_newcharts.py" not in x3.out and len(_william(x3)) == 1 and _william(x3)[0].startswith("FOR WILLIAM: no chart chosen and none made for Claimocity id %s:" % FID2)
              and all(t_ in _william(x3)[0] for t_ in (FID, FID2, "pat101", "a new chart")), (x3.err, {k[-8:]: brief(v) for k, v in m3x.items()}, _william(x3))))
x4 = _steps([msg(FID, WE, C_FIRST, P8), msg(FID2, WE, C_FIRST, P8)], []); e4x = x4.match().get(K(WE, C_FIRST, P8), {})
step("... nor when both would get a NEW chart (no chart of that name at all): nobody knows the two ids to be one person - no chart is made for either, for William",
     lambda: (x4.clean() and ok_field(e4x, rule=0, status="AMBIGUOUS", decided_for=[], by_proof={}, feed_ids=[FID, FID2], for_william=True, why=FI.WHY_SHARED) and "resolved" not in e4x and x4.amd.added == [] and "claimocity_newcharts.py" not in x4.out
              and len(_william(x4)) == 1 and FID in _william(x4)[0] and FID2 in _william(x4)[0], (x4.err, brief(e4x), _william(x4))))
x5 = _steps([msg(FID, QU, B_FIRST, P8, ssn=S1), msg(FID2, QU, B_FIRST, P8, ssn=dash(S2))], [chart(111, QU, B_FIRST, BD2)]); e5x = x5.match().get(K(QU, B_FIRST, P8), {})
step("... and never when the feed itself carries two different Social Security numbers for the two ids: two people for certain - the key gets no chart although each of them alone would be given the one same-name chart "
     "(by the name alone: neither has proof of it); each of them IS weighed, and William's ONE line says what each would get on its own and that Claimocity's own numbers show two people",
     lambda: (x5.clean() and ok_field(e5x, rule=0, status="AMBIGUOUS", decided_for=[], by_proof={}, feed_ids=[FID, FID2], for_william=True, why=FI.WHY_SHARED, candidates=["pat111"]) and "resolved" not in e5x and x5.amd.added == []
              and len(_william(x5)) == 1 and all(t_ in _william(x5)[0] for t_ in (FID, FID2, "pat111", "two people")), (x5.err, brief(e5x), _william(x5))))
x6 = _steps([msg(FID, QU, B_FIRST, P8), msg(FID2, QU, B_FIRST, P8)], [chart(111, QU, B_FIRST, "")]); e6x = x6.match().get(K(QU, B_FIRST, P8), {})
step("... a chart the rule gives them both by rule 8 (no birth date on either side) is the FYI of rule 8, said ONCE for the key - with both Claimocity ids in it",
     lambda: (x6.clean() and ok_field(e6x, resolved="pat111", rule=8, status="FOUND", decided_for=[FID, FID2], for_william=True, flags=["no birth date on either side"]) and x6.amd.added == []
              and _william(x6) == ["FOR WILLIAM: pat111 %s (FYI) - Claimocity ids %s, %s" % (FI.WHY[8], FID, FID2)], (x6.err, brief(e6x), _william(x6))))
x7 = _steps([msg(FID, QU, B_FIRST, P8), msg(FID, QU, B_FIRST, ""), msg(FID2, QU, B_FIRST, "")], [chart(111, QU, B_FIRST, "")]); m7x = x7.match()
step("... and not said twice for one id: the first id (it came under the placeholder too) says it under its own key, the key the two share says it for the second id only - two keys, one chart, one line for each Claimocity id",
     lambda: (x7.clean() and ok_field(m7x.get(K(QU, B_FIRST, P8), {}), resolved="pat111", rule=8, decided_for=[FID]) and ok_field(m7x.get(K(QU, B_FIRST, ""), {}), resolved="pat111", rule=8, decided_for=[FID, FID2]) and x7.amd.added == []
              and _william(x7) == ["FOR WILLIAM: pat111 %s (FYI) - Claimocity id %s" % (FI.WHY[8], i_) for i_ in (FID, FID2)], (x7.err, {k.rpartition("|")[2] or "none": brief(v) for k, v in m7x.items()}, _william(x7))))
# ---- several ids under one name, an id with PROOF of its own chart (11/25/2026, the independent verification) ----------------------------------
# Until then a key that several Claimocity ids share got a chart only when the rule gave every one of them the SAME chart; otherwise none of
# their messages was entered, run after run - also when an id had PROOF of its own chart (its Claimocity id on the chart, the chart's own
# Social Security number). The import asks for the chart of the message's OWN Claimocity id, so each id that has proof keeps its chart: the
# entry names it ("by_proof"). An id without proof stays without a chart, and the line for William names that id.
_W_FAILED, _W_OWNED, _W_FAR, _W_EACH, _F_DUP = (getattr(FI, n_, "(no such word in feed_identity.py)") for n_ in ("WHY_WAIT_FAILED", "WHY_OWNED", "WHY_FAR_PAIR", "WHY_EACH_PROOF", "FLAG_DUPLICATE"))
def _first(f, key): return f.worlds[0].match().get(key, {}) if f.worlds and f.worlds[0] is not None else {}
p1 = Feed([chart(101, QU, B_FIRST, BD2, mrn=FID.upper()), chart(102, QU, B_FIRST, BD_FAR, mrn=FID2.upper())]).drop(msg(FID, QU, B_FIRST, P8), msg(FID2, QU, B_FIRST, P8)); p1.run(); ep1 = _first(p1, K(QU, B_FIRST, P8))
step("two Claimocity ids under one name with no birth date, each on a chart of its OWN that carries its Claimocity id (rule 1 for each - two charts): each visit goes to its own id's chart in the first run - "
     "the key names the chart of each id ('by_proof'), carries no chart of its own, and is no question for William",
     lambda: (p1.clean() and ok_field(ep1, rule=0, why=_W_EACH, status="AMBIGUOUS", by_proof={FID: "pat101", FID2: "pat102"}, decided_for=[FID, FID2], for_william=False) and "resolved" not in ep1
              and sorted(p1.entered) == [(FID, "pat101"), (FID2, "pat102")] and p1.files == [] and p1.made == [] and p1.said() == [], (p1.worlds[0].err, brief(ep1), p1.entered, p1.said())))
p2 = Feed([chart(101, QU, B_FIRST, BD2, ssn=S1)]).drop(msg(FID, QU, B_FIRST, P8, ssn=S1), msg(FID2, QU, B_FIRST, P8, ssn=dash(S2))); p2.run(); ep2 = _first(p2, K(QU, B_FIRST, P8))
step("... one of the two carries the chart's own Social Security number, the other another number (two people by Claimocity's own numbers - until then NEITHER was even weighed): the one with proof goes to that chart; "
     "the other gets no chart on this key and none is made for it - William's ONE line names that id, not the one that has its chart",
     lambda: (p2.clean() and ok_field(ep2, rule=0, why=FI.WHY_SHARED, by_proof={FID: "pat101"}, decided_for=[FID2], for_william=True) and "resolved" not in ep2 and p2.entered == [(FID, "pat101")] and len(p2.files) == 1 and p2.made == []
              and len(p2.said()) == 1 and p2.said()[0].startswith("FOR WILLIAM: no chart chosen and none made for Claimocity id %s:" % FID2), (p2.worlds[0].err, brief(ep2), p2.entered, p2.said())))
p3 = Feed([chart(101, QU, B_FIRST, BD2, members=[M1])]).drop(msg(FID, QU, B_FIRST, P8, ssn=S1, in1=[("Humana Gold", M1)]), msg(FID2, QU, B_FIRST, P8, ssn=dash(S2), in1=[("Humana Gold", M1)])); p3.run(); ep3 = _first(p3, K(QU, B_FIRST, P8))
step("... both carry a member number of ONE chart while Claimocity's own Social Security numbers show them to be two people: a chart two of them claim is nobody's by proof - neither is entered, for William",
     lambda: (p3.clean() and ok_field(ep3, rule=0, why=FI.WHY_SHARED, by_proof={}, decided_for=[], for_william=True) and "resolved" not in ep3 and p3.entered == [] and len(p3.said()) == 1 and FID in p3.said()[0] and FID2 in p3.said()[0],
              (p3.worlds[0].err, brief(ep3), p3.entered, p3.said())))
step("... each id that goes to its chart by proof has a row of its own for the register on main, in the fixed words: its Claimocity id, its chart, the rule that is its proof ('proof_rows' - the entry's own fields are about the ids left without a chart)",
     lambda: ([(r_.get("feed_ids"), r_.get("chart"), r_.get("rule"), r_.get("why"), r_.get("for_william"), FI.problems(r_)) for r_ in ep1.get("proof_rows") or []]
              == [([FID], "pat101", 1, FI.WHY[1], False, []), ([FID2], "pat102", 1, FI.WHY[1], False, [])] and [r_.get("feed_ids") for r_ in ep2.get("proof_rows") or []] == [[FID]] and ep3.get("proof_rows") == [], ep1.get("proof_rows")))
p4 = Feed([chart(101, ZO, A_FIRST, BD), chart(102, ZO, A_FIRST, BD_FAR)]).drop(msg(FID, ZO, A_FIRST, BD_OFF), msg(FID, ZO, A_FIRST, P8), msg(FID2, ZO, A_FIRST, P8)); p4.run(); ep4 = _first(p4, K(ZO, A_FIRST, P8))
step("... an id whose own answer is a chart WITHOUT proof (a slip in the birth date - rule 5, under its own key) keeps that chart under its own key; the key it shares names no chart for it ('by_proof' is for rules 1 to 4 only), "
     "and William's line names both ids of that key",
     lambda: (p4.clean() and _first(p4, K(ZO, A_FIRST, BD_OFF)).get("rule") == 5 and ok_field(ep4, rule=0, why=FI.WHY_SHARED, by_proof={}, decided_for=[], for_william=True) and "resolved" not in ep4 and p4.entered == [(FID, "pat101")]
              and len(p4.said()) == 1 and p4.said()[0].startswith("FOR WILLIAM: no chart chosen and none made for Claimocity ids %s, %s:" % (FID, FID2)), (p4.worlds[0].err, brief(ep4), p4.entered, p4.said())))
p4.run()
step("... the next run knows the first id from the map: its message under that key goes to its chart, and the other id - now alone under the key - is decided like any other patient (here: two same-name charts with two dates - a chart of its own, for William)",
     lambda: (p4.clean() and p4.files == [] and p4.entered[:2] == [(FID, "pat101"), (FID, "pat101")] and len(p4.made) == 1 and p4.on(FID2) == p4.made and any(p4.made[0] in l and "beside 2 same-name chart(s)" in l for l in p4.said(1)), (p4.entered, p4.made, p4.said(1))))
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
     lambda: (wi.clean() and (wi.reg()["created"] or [{}])[0].get("plans") == [{"code": "FLO02", "ins": "ins700", "seq": "1"}, {"code": "HUM01", "err": FI.PLAN_NOT_ADDED}], (wi.err, wi.reg())))
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
# ---- every spelling of the last name: a chart with an apostrophe, a space, a period or a hyphen the FEED does not have (11/25/2026, review of the identity rule) ----
PLAIN, APOS = "O" + ZO, "O'" + ZO
sa = _steps([msg(FID, PLAIN, A_FIRST, P8)], [chart(101, PLAIN, A_FIRST, BD), chart(102, APOS, A_FIRST, BD_FAR)]); ea = sa.match().get(K(PLAIN, A_FIRST, P8), {})
step("a namesake whose chart writes the last name with an apostrophe the feed does not have: BOTH charts are weighed - two dates, so nobody is matched by the name alone: a new chart beside the two, for William "
     "(until then only the chart spelled like the feed was listed, and rule 7 took it without a word)",
     lambda: (sa.clean() and ok_field(ea, rule=9, candidates=["pat101", "pat102"], for_william=True, flags=["same-name charts not used", "no birth date from Claimocity"], resolved="pat9001", cut="", every_spelling=True) and len(sa.amd.added) == 1
              and any("beside 2 same-name chart(s) (pat101, pat102)" in l for l in _william(sa)), (sa.err, brief(ea), _william(sa), sa.amd.asked)))
sb = _steps([msg(FID, PLAIN, A_FIRST, BD_OFF)], [chart(101, PLAIN, A_FIRST, BD), chart(102, APOS, A_FIRST, BD_OFF)]); eb = sb.match().get(K(PLAIN, A_FIRST, BD_OFF), {})
step("... and when the chart with the apostrophe carries exactly the feed's date while the chart spelled like the feed is one digit off: the same date decides (rule 2) - no slip is read into the other chart (until then: rule 5, the other chart)",
     lambda: (sb.clean() and ok_field(eb, resolved="pat102", rule=2, status="FOUND", flags=[], candidates=["pat101", "pat102"], for_william=False) and sb.amd.added == [], (sb.err, brief(eb), sb.amd.asked)))
for _label, _fl, _cl in (("an apostrophe", PLAIN, APOS), ("MC as a word of its own", "MC" + QU, "MC " + QU), ("DE as a word of its own", "DE" + YA, "DE " + YA), ("VAN as a word of its own", "VAN" + QU, "VAN " + QU),
                         ("ST without the period the feed writes", "ST. " + WE, "ST " + WE), ("a hyphen between two names the feed writes as one", TH + YA, TH + "-" + YA), ("DE LA where the feed writes DELA", "DELA " + YA, "DE LA " + YA)):
    step("the patient's ONLY chart writes the last name another way than the feed (%s): it is found - by the Claimocity id it carries (rule 1), and without the id by the same date (rule 2) - and no second chart is made" % _label,
         lambda _fl=_fl, _cl=_cl: (lambda a, b: (a.clean() and b.clean() and ok_field(a.match().get(K(_fl, A_FIRST, BD), {}), resolved="pat101", rule=1, flags=[], for_william=False) and ok_field(b.match().get(K(_fl, A_FIRST, BD), {}), resolved="pat101", rule=2, flags=[], for_william=False)
                                                 and a.amd.added == [] and b.amd.added == [], (a.err, b.err, brief(a.match().get(K(_fl, A_FIRST, BD))), brief(b.match().get(K(_fl, A_FIRST, BD))), b.amd.asked)))(
             _steps([msg(FID, _fl, A_FIRST, BD)], [chart(101, _cl, A_FIRST, BD_FAR, mrn=FID.upper())]), _steps([msg(FID, _fl, A_FIRST, BD)], [chart(101, _cl, A_FIRST, BD)])))
sp1 = _steps([msg(FID, PLAIN, A_FIRST, BD_OFF)], [chart(190, APOS, A_FIRST, BD)] + [chart(200 + n, "O " + ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)]); es1 = sp1.match().get(K(PLAIN, A_FIRST, BD_OFF), {})
step("more charts of that last name - in all its spellings - than AdvancedMD lists (50), the patient's own chart under another spelling and not among those listed: the every-spelling lookup is asked again WITH the first name, and finds it",
     lambda: (sp1.clean() and ok_field(es1, resolved="pat190", rule=5, cut="", every_spelling=True, for_william=False) and sp1.amd.added == [] and len([n for n in sp1.amd.asked if spelt(n)]) == 2, (sp1.err, brief(es1), sp1.amd.asked)))
sp2 = _steps([msg(FID, PLAIN, A_FIRST, BD_OFF)], [chart(190, PLAIN, A_FIRST, BD)] + [chart(200 + n, APOS, A_FIRST + " A%02d" % n, BD_FAR) for n in range(1, 56)]); es2 = sp2.match().get(K(PLAIN, A_FIRST, BD_OFF), {})
step("... more FULL-name charts under ANOTHER spelling than AdvancedMD lists: the list the feed's own spelling brings looks whole (one chart), but it is not - nobody can say 'all of them carry one date': no chart by the slip alone, a new chart, flagged, for William",
     lambda: (sp2.clean() and ok_field(es2, rule=9, cut="full", for_william=True, resolved="pat9001") and es2.get("flags") == ["same-name charts not used", FI.FLAG_CUT] and len(sp2.amd.added) == 1, (sp2.err, brief(es2), sp2.amd.asked)))
sp3 = _steps([msg(FID, PLAIN, A_FIRST, BD)], [chart(190, APOS, D_FIRST, BD)] + [chart(200 + n, PLAIN, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)]); es3 = sp3.match().get(K(PLAIN, A_FIRST, BD), {})
step("... and a chart of rule 3 (another first name, exactly the date) under another spelling: the full page of the every-spelling lookup is still read - the chart on it is weighed (the list stays marked as cut for other first names)",
     lambda: (sp3.clean() and ok_field(es3, resolved="pat190", rule=3, flags=["first name differs"], cut="first", for_william=True) and sp3.amd.added == [], (sp3.err, brief(es3), sp3.amd.asked)))
# ---- one person under two NEW Claimocity ids in one batch (11/25/2026, review of the identity rule) ---------------------------------------------
# Until then each of the two got a new chart (the second birth date a digit off, or none) - where the same two messages in two batches got ONE: the
# second run found the first one's new chart and the rule took it. Now the chart is made for one of them (the one with a real birth date first) and
# the other waits for the next run, which weighs it against that chart: no second chart, no line for William, its file read again.
NW = lambda *ps: FI.new_chart_waits([{"names": list(n), "real": r} for n, r in ps])
T("new_chart_waits: two new patients whose names are name candidates of each other - the second waits; the one with a real birth date is made first, whatever the order; another last name, or only the last name in common, waits for nobody",
  lambda: NW(([(ZO, A_FIRST)], True), ([(ZO, A_FIRST)], True)) == [1] and NW(([(ZO, A_FIRST)], False), ([(ZO, A_FIRST)], True)) == [0] and NW(([(ZO, A_FIRST)], True), ([(QU, A_FIRST)], True)) == []
  and NW(([(ZO, A_FIRST)], True), ([(ZO, B_FIRST)], True)) == [] and NW(([(ZO, A_FIRST)], True), ([(ZO, A_FIRST[:4])], False), ([(ZO + " JR", A_FIRST)], True)) == [1, 2] and NW() == [] and NW(([(ZO, A_FIRST)], True)) == [])
T("... a patient that waits is weighed against nobody else that waits: three of one name - one chart is made, two wait; two names of one patient count each", lambda: NW(([(ZO, A_FIRST)], False), ([(ZO, A_FIRST)], False), ([(ZO, A_FIRST)], False)) == [1, 2]
  and NW(([(QU, B_FIRST), (ZO, A_FIRST)], True), ([(ZO, A_FIRST)], True)) == [1])
T("the answer of a patient that waits: no chart, none made, rule 0 in the fixed words - and NOT for William (the next run decides it; no board card for a wait)",
  lambda: (lambda a: (a["chart"], a["rule"], a["why"], a["new_chart"], a["for_william"], a["candidates"], a["feed_dob"], FI.problems(a), _w(a)) == (None, 0, FI.WHY_SAME_RUN, False, False, ["pat7"], "real", [], []))(
      FI.waits(dict(D(F(ZO, A_FIRST, BD), [C(7, ZO, A_FIRST, BD_FAR)])))))
def _made(w): return [(x.get("name"), x.get("dob"), x.get("additionalmrn")) for x in w.amd.added]
nw1 = _steps([msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_OFF)], []); m_nw1 = nw1.match(); _a1, _b1 = m_nw1.get(K(ZO, A_FIRST, BD), {}), m_nw1.get(K(ZO, A_FIRST, BD_OFF), {})
_first1, _wait1 = (_a1, _b1) if _a1.get("rule") == 9 else (_b1, _a1)
step("one person under two NEW Claimocity ids in one batch, the second birth date one digit off: ONE new chart is made - the other id waits (no chart, none made, not for William, said in a plain line) and its file is read again by the next run",
     lambda: (nw1.clean() and len(nw1.amd.added) == 1 and ok_field(_first1, rule=9, status="MISSING", resolved="pat9001") and ok_field(_wait1, rule=0, status="AMBIGUOUS", why=FI.WHY_SAME_RUN, for_william=False, pids=[])
              and "resolved" not in _wait1 and len(_wait1.get("decided_for") or []) == 1 and not any(_wait1["decided_for"][0] in l for l in _william(nw1))
              and any(_wait1["decided_for"][0] in l and "waits" in l for l in nw1.out["claimocity_resolve.py"].splitlines()), (nw1.err, brief(_a1), brief(_b1), _made(nw1), _william(nw1), nw1.out.get("claimocity_resolve.py", "")[-600:])))
def _next_run(first, waiting):      # the next run: only the message that waited is new, and the chart made for the other id stands in AdvancedMD (its Claimocity id on it)
    fd = first.get("decided_for", [""])[0]; wd_ = waiting.get("decided_for", [""])[0]; dob_of = {FID: BD, FID2: BD_OFF}
    return _steps([msg(wd_, ZO, A_FIRST, dob_of.get(wd_, ""))], [chart(9001, ZO, A_FIRST, dob_of.get(fd, ""), mrn=fd.upper())]), K(ZO, A_FIRST, dob_of.get(wd_, ""))
nw1b, _k1b = _next_run(_first1, _wait1); _e1b = nw1b.match().get(_k1b, {})
step("... and the NEXT run weighs the id that waited against that new chart: the rule takes it by the slip in the date (rule 5) - one chart for the one person, as when the two messages come in two batches",
     lambda: (nw1b.clean() and ok_field(_e1b, resolved="pat9001", rule=5, status="FOUND") and _e1b.get("flags") == [FI.FLAG_DATE + FI.SLIP_DIGIT] and nw1b.amd.added == [], (nw1b.err, brief(_e1b))))
nw2 = _steps([msg(FID, ZO, A_FIRST, P8), msg(FID2, ZO, A_FIRST, BD)], []); m_nw2 = nw2.match()
step("... one of the two ids comes with NO birth date: the chart is made for the id WITH the real date (and written with it) - the other waits, whatever the order of the two in the batch",
     lambda: (nw2.clean() and [(d_, m_) for _n, d_, m_ in _made(nw2)] == [(mdy(BD), FID2.upper())] and ok_field(m_nw2.get(K(ZO, A_FIRST, BD), {}), rule=9, resolved="pat9001")
              and ok_field(m_nw2.get(K(ZO, A_FIRST, P8), {}), rule=0, why=FI.WHY_SAME_RUN, for_william=False, status="AMBIGUOUS") and "resolved" not in m_nw2.get(K(ZO, A_FIRST, P8), {}), (nw2.err, _made(nw2), {k[-8:]: brief(v) for k, v in m_nw2.items()})))
nw3 = _steps([msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, B_FIRST, BD2), msg(FID3, QU, A_FIRST, BD)], []); m_nw3 = nw3.match()
step("... two NEW patients who share only the last name, and one of another last name: nobody waits - three charts, as before",
     lambda: (nw3.clean() and len(nw3.amd.added) == 3 and all(ok_field(v, rule=9, status="MISSING") and v.get("resolved") for v in m_nw3.values()) and len(m_nw3) == 3, (nw3.err, _made(nw3), {k: brief(v) for k, v in m_nw3.items()})))
# ---- the wait, for every patient the same run would decide blind to a chart it is making (11/25/2026, the independent verification) --------------
# The wait held back only the patients the rule gives a NEW chart. A patient whose own answer rests on what the same-name charts look like
# (rules 5 to 8: "ONE date", "the only name candidates") was decided against the charts AdvancedMD held at that moment - blind to a same-name
# chart the SAME run was making. Of three new ids of one name the one without a birth date went, by rule 7 and without a word, on the chart of
# whichever dated patient had the smaller Claimocity id; a newcomer's second id went on a long-time namesake's chart in the very run that made
# the newcomer a chart of her own. Now such a patient waits as well: no chart in that run, its file is read again, and the next run weighs it
# against every chart of the batch. Feed (above) runs the same feed several times, as the driver does.
REL = lambda a, b: FI.related({"names": a[0], "dobs": a[1]}, {"names": b[0], "dobs": b[1]})
T("related - whose new chart a patient must be weighed against: a NAME CANDIDATE (three letters of the first name), whatever the dates; and rule 3's relation - the same last name under ANOTHER first name and the ONE real "
  "birth date the other's chart is written with (with two dates, or none, that chart carries no date rule 3 could go by); nothing else",
  lambda: [REL(([(ZO, A_FIRST)], [BD]), ([(ZO, "XANDER")], [BD_FAR])), REL(([(ZO, A_FIRST)], [BD]), ([(ZO, D_FIRST)], [BD])), REL(([(ZO, A_FIRST)], [BD, BD_FAR]), ([(ZO, D_FIRST)], [BD_FAR])),
           REL(([(ZO, A_FIRST)], [BD]), ([(ZO, D_FIRST)], [BD_FAR])), REL(([(ZO, A_FIRST)], [BD]), ([(QU, A_FIRST)], [BD])), REL(([(ZO, A_FIRST)], [BD]), ([(ZO, D_FIRST)], [BD, BD_FAR])), REL(([(ZO, A_FIRST)], []), ([(ZO, D_FIRST)], []))]
          == [True, True, True, False, False, False, False])
NWD = lambda *ps: FI.new_chart_waits([{"names": list(n), "real": bool(d), "dobs": list(d)} for n, d in ps])
T("new_chart_waits: two new patients of one last name and ONE real birth date under two first names (rule 3's own relation) - the second waits too; with two different dates, or no date, nobody waits",
  lambda: NWD(([(ZO, A_FIRST)], [BD]), ([(ZO, D_FIRST)], [BD])) == [1] and NWD(([(ZO, A_FIRST)], [BD]), ([(ZO, D_FIRST)], [BD_FAR])) == [] and NWD(([(ZO, A_FIRST)], []), ([(ZO, D_FIRST)], [])) == [])
T("... a new patient waits only for a chart that IS made in this run, never for a patient that itself waits: the third one's chart is made at once, and the one that waits is weighed against both in the next run",
  lambda: NW(([(ZO, A_FIRST)], True), ([(ZO, A_FIRST), (QU, B_FIRST)], True), ([(QU, B_FIRST)], True)) == [1])
def _three(d_first, d_second): return Feed().drop(msg(FID, ZO, A_FIRST, d_first), msg(FID2, ZO, A_FIRST, d_second), msg(FID3, ZO, A_FIRST, P8)).runs(6)
def _three_ok(f):
    own = f.on(FID3); ls = f.said()
    return (f.clean() and f.files == [] and len(f.made) == 3 and len(own) == 1 and own != f.on(FID) and own != f.on(FID2) and f.on(FID) != f.on(FID2) and f.born(own[0]) == P8
            and any(own[0] in l and "beside 2 same-name chart(s)" in l and "same person or not?" in l for l in ls) and any(own[0] in l and "face sheet needed" in l for l in ls)
            and len(f.worlds) == 3 and not any(FID3 in l for n in (0, 1) for l in f.said(n))      # while it waits William is asked nothing about it. In the second run its own answer is rule 7 on the FIRST id's chart (since identity rule .4 the map does not hold that back): it is the WAIT that keeps it off that chart - the run is making the second id's
            and (f.worlds[1].match().get(K(ZO, A_FIRST, P8), {}).get("why"), f.worlds[1].match().get(K(ZO, A_FIRST, P8), {}).get("waits_for")) == (FI.WHY_SAME_RUN, [FID2]),
            ([w.err for w in f.worlds if w], f.entered, f.made, ls, f.log(1)[-900:]))
t3a, t3b = _three(BD, BD_FAR), _three(BD_FAR, BD)
step("three NEW Claimocity ids of one name in one batch, two of them with far-apart birth dates (two people) and the third with none: the visit of the third is never entered on the chart of either - it waits while a run makes "
     "a same-name chart, and ends on a chart of its own beside both, with 'same person or not?' and the face sheet for William (until then it went, by rule 7 and without a word, on the chart of whichever dated id sorted first)", lambda: _three_ok(t3a))
step("... the same with the Claimocity ids of the two dated patients the other way round: the same outcome - which chart a visit goes on never depends on the order of the ids", lambda: _three_ok(t3b))
o1 = Feed([chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 3), 0)])]).drop(msg(FID2, ZO, A_FIRST, BD_FAR), msg(FID3, ZO, A_FIRST, P8)).runs(5)
step("a long-time patient's chart, and in ONE batch a newcomer of the same name under two new ids - one with her own birth date, one with none: the id without a date is NOT entered on the long-time patient's chart by rule 7 in the run "
     "that makes the newcomer a chart (and asks William about it) - it waits, and the next run, with two same-name charts and two dates before it, gives it a chart of its own beside both, with the question and the face sheet",
     lambda: (o1.clean() and o1.files == [] and len(o1.made) == 2 and len(o1.on(FID3)) == 1 and "pat101" not in o1.on(FID3) and o1.on(FID3) != o1.on(FID2) and [i_ for i_, _c in o1.entered[:1]] == [FID2] and len(o1.worlds[0].amd.added) == 1
              and any(FID3 in l and "waits" in l for l in o1.log(0).splitlines()) and not any(FID3 in l for l in o1.said(0))
              and any(o1.on(FID3)[0] in l and "beside 2 same-name chart(s) (pat101, " in l for l in o1.said()), (o1.entered, o1.made, o1.said(), o1.log(0)[-700:])))
o1m = Feed([chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 3), 0)])], pmap={FID5: "pat101"}).drop(msg(FID2, ZO, A_FIRST, BD_FAR), msg(FID3, ZO, A_FIRST, P8)).runs(5)
step("... the same when the feed already KNOWS the long-time patient (her chart is an earlier Claimocity id's in the patient map): since identity rule .4 the map does not hold rule 7 back - it is the WAIT that keeps the id without a date "
     "off the long-time chart in the run that makes the newcomer's chart; it ends on a chart of its own beside both, with the question",
     lambda: (o1m.clean() and o1m.files == [] and len(o1m.made) == 2 and len(o1m.on(FID3)) == 1 and "pat101" not in o1m.on(FID3) and o1m.on(FID3) != o1m.on(FID2) and [i_ for i_, _c in o1m.entered[:1]] == [FID2]
              and ok_field(_first(o1m, K(ZO, A_FIRST, P8)), rule=0, why=FI.WHY_SAME_RUN, for_william=False, waits_for=[FID2]) and not any(FID3 in l for l in o1m.said(0))
              and any(o1m.on(FID3)[0] in l and "beside 2 same-name chart(s) (pat101, " in l for l in o1m.said()), (o1m.entered, o1m.made, o1m.said(), o1m.log(0)[-700:])))
c1 = Feed([chart(101, ZO, A_FIRST, BD)]).drop(msg(FID3, ZO, A_FIRST, P8), msg(FID2, QU, B_FIRST, BD2)).runs(3)
step("what must stay - the patient without a birth date beside a NEW patient of ANOTHER last name in the batch: nobody waits - rule 7 at once, one new chart for the other",
     lambda: (c1.clean() and len(c1.worlds) == 1 and c1.files == [] and c1.on(FID3) == ["pat101"] and len(c1.made) == 1 and c1.on(FID2) == c1.made and c1.said() == [], (c1.entered, c1.made, c1.said())))
c2 = Feed([chart(101, ZO, A_FIRST, BD), chart(111, QU, B_FIRST, BD2)]).drop(msg(FID, ZO, A_FIRST, BD_OFF), msg(FID2, QU, B_FIRST, P8), msg(FID3, ZO, A_FIRST, P8)).runs(3)
step("... a batch in which NOBODY gets a new chart is decided exactly as before, in one run: the slip (rule 5), the placeholder (rule 7) - also two patients of one name side by side",
     lambda: (c2.clean() and len(c2.worlds) == 1 and c2.files == [] and c2.made == [] and sorted(c2.entered) == [(FID, "pat101"), (FID2, "pat111"), (FID3, "pat101")]
              and [c2.worlds[0].match()[k]["rule"] for k in (K(ZO, A_FIRST, BD_OFF), K(QU, B_FIRST, P8), K(ZO, A_FIRST, P8))] == [5, 7, 7], (c2.entered, c2.said())))
c3 = Feed([chart(101, ZO, A_FIRST, BD_FAR, ssn=S1)]).drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD2, ssn=S1)).runs(3)
step("... a patient with PROOF never waits: beside a same-name patient who gets a new chart in the same batch, the one whose Social Security number is the chart's goes to that chart in the first run (rule 4)",
     lambda: (c3.clean() and c3.on(FID2) == ["pat101"] and c3.worlds[0].match()[K(ZO, A_FIRST, BD2)]["rule"] == 4 and (FID2, "pat101") in c3.entered[:2] and len(c3.worlds[0].amd.added) == 1 and c3.on(FID) == c3.made, (c3.entered, c3.made, c3.said())))
k2 = Feed().drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_OFF)).runs(4)
step("... ONE person under two new ids, the second birth date a digit off: ONE chart, the second id on it after the next run - by the slip (rule 5), which the patient map does not hold back although that chart is the first id's there by then",
     lambda: (k2.clean() and k2.files == [] and len(k2.made) == 1 and k2.on(FID) == k2.on(FID2) == k2.made and len(k2.worlds) == 2 and k2.worlds[1].match()[K(ZO, A_FIRST, BD_OFF)]["rule"] == 5 and k2.said() == [], (k2.entered, k2.made, k2.said())))
k1 = Feed().drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, P8)).runs(4); ek1 = k1.worlds[1].match().get(K(ZO, A_FIRST, P8), {}) if len(k1.worlds) > 1 and k1.worlds[1] is not None else {}
step("... the second id comes with NO birth date: ONE chart, and BOTH visits on it after the next run. The id without a date waits a run - for the chart that run is making; then Claimocity's missing date and the ONE date the same-name chart "
     "carries are rule 7. By then that chart is the first id's in the patient map, and since identity rule .4 that does not hold rule 7 back (round 1 held it: the second id was never entered - the same question at the top, run after run)",
     lambda: (k1.clean() and len(k1.made) == 1 and k1.on(FID) == k1.on(FID2) == k1.made and k1.files == [] and len(k1.worlds) == 2 and ok_field(_first(k1, K(ZO, A_FIRST, P8)), rule=0, why=FI.WHY_SAME_RUN, for_william=False, waits_for=[FID])
              and ok_field(ek1, rule=7, resolved=k1.made[0], status="FOUND", flags=["no birth date from Claimocity"], for_william=False) and k1.said() == [], (k1.entered, k1.made, brief(ek1), k1.said())))
n7 = Feed([chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 3), 0)])], pmap={FID5: "pat101"}).drop(msg(FID, ZO, A_FIRST, P8)).runs(3)
step("William's own case, through the runs: a patient the feed already KNOWS - her chart carries her date and is an earlier Claimocity id's in the patient map - is sent under a NEW Claimocity id with the placeholder: "
     "her visit is entered on her own chart in the first run by rule 7, nothing is asked, the file is done and the map learns the new id (round 1: no chart, the same question at the top of every run, the file never done)",
     lambda: (n7.clean() and len(n7.worlds) == 1 and n7.files == [] and n7.entered == [(FID, "pat101")] and n7.made == [] and n7.said() == [] and n7.pmap.get(FID) == "pat101"
              and ok_field(_first(n7, K(ZO, A_FIRST, P8)), rule=7, resolved="pat101", status="FOUND", flags=["no birth date from Claimocity"], for_william=False, feed_dob="none"), (n7.entered, n7.files, n7.said(), brief(_first(n7, K(ZO, A_FIRST, P8))))))
y1 = Feed().drop(msg(FID, ZO, A_FIRST, P8)); y1.run(); y1.drop(msg(FID2, ZO, A_FIRST, BD)); y1.run(); ey1 = y1.worlds[1].match().get(K(ZO, A_FIRST, BD), {}) if len(y1.worlds) > 1 and y1.worlds[1] is not None else {}
step("what the map still holds back - a chart WITHOUT a date of its own: the feed made a chart with the placeholder for an id sent without a date; the next id of that name, sent with a real date, is not entered on it by rule 6 "
     "(nothing but the name ties the two) - ONE line for William with the id, the chart and the question; no second chart, the file kept",
     lambda: (y1.clean() and len(y1.made) == 1 and y1.entered == [(FID, y1.made[0])] and len(y1.files) == 1 and ok_field(ey1, rule=0, why=_W_OWNED, candidates=y1.made, for_william=True, status="AMBIGUOUS") and "resolved" not in ey1
              and y1.said(1) == ["FOR WILLIAM: no chart chosen and none made for Claimocity id %s: %s (chart %s) - same person or not?" % (FID2, _W_OWNED, y1.made[0])], (y1.entered, y1.made, brief(ey1), y1.said())))
def _yes(f, fid): f.pmap[fid] = f.made[0]; f.run(); return f      # William's yes, written into the patient map (the repository's map, which the ingest takes at its start)
step("... and William's yes, written into the patient map, enters the visit on that chart at the next run - no lookup, no second chart",
     lambda: (lambda f: (f.clean() and f.on(FID2) == f.made and f.files == [] and len(f.made) == 1 and f.worlds[-1] is None, (f.entered, f.made)))(_yes(y1, FID2)))
r3 = Feed().drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, D_FIRST, BD)).runs(4)
step("two NEW Claimocity ids of one last name and ONE real birth date under two first names - rule 3's own relation - in one batch: ONE chart is made and the other id waits (until then two charts and not a word, where the same two "
     "messages in two batches gave one chart); the next run weighs it against that chart and takes it by rule 3, with the FYI for William that names the Claimocity id",
     lambda: (r3.clean() and r3.files == [] and len(r3.made) == 1 and len(r3.worlds[0].amd.added) == 1 and r3.on(FID) == r3.on(FID2) == r3.made and r3.worlds[1].match()[K(ZO, D_FIRST, BD)]["rule"] == 3
              and r3.said() == ["FOR WILLIAM: %s %s (FYI) - Claimocity id %s" % (r3.made[0], FI.WHY[3], FID2)], (r3.entered, r3.made, r3.said(), r3.log(0)[-500:])))
f1 = Feed().drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, "XANDER", BD)).runs(4)
step("two NEW ids of one last name and one birth date whose first names share three letters and are not the same word: one chart is made, the other id waits and takes it in the next run by name and the same birth date (rule 2) - "
     "a wait that asked for the FULL first name would make two charts",
     lambda: (f1.clean() and f1.files == [] and len(f1.made) == 1 and len(f1.worlds[0].amd.added) == 1 and f1.on(FID) == f1.on(FID2) == f1.made and f1.worlds[1].match()[K(ZO, "XANDER", BD)]["rule"] == 2, (f1.entered, f1.made)))
cw = Feed([chart(111, QU, B_FIRST, BD2)]).drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_FAR), msg(FID2, QU, B_FIRST, BD_FAR), msg(FID3, QU, B_FIRST, P8)); cw.run()
step("a patient that waits behind one that itself waits: the second id came under TWO names and waits for the first id's new chart (one of its names); the third, without a birth date, would go by rule 7 on the one chart of the second "
     "id's OTHER name - and waits as well, because that id may yet get a chart under this name. Its entry names the Claimocity id whose chart is made in this run - the chart all of them wait behind",
     lambda: (lambda m: (cw.clean() and len(cw.worlds[0].amd.added) == 1 and cw.entered == [(FID, cw.made[0])] and ok_field(m.get(K(QU, B_FIRST, P8), {}), rule=0, why=FI.WHY_SAME_RUN, for_william=False, waits_for=[FID])
                         and all(ok_field(m.get(k, {}), rule=0, why=FI.WHY_SAME_RUN, waits_for=[FID]) for k in (K(ZO, A_FIRST, BD_FAR), K(QU, B_FIRST, BD_FAR))) and cw.said(0) == [], ({k[:9] + k[-9:]: brief(v) for k, v in m.items()}, cw.said(0))))(cw.worlds[0].match()))
cw.runs(4)
step("... and it ends: the second id gets its chart in the next run - under the very name the third one carries, with another birth date - and the run after weighs the third against both charts of that name: two dates, so a chart "
     "of its own beside them and the question for William (decided in the first run it would have gone on the older chart by rule 7, blind to the chart that was coming)",
     lambda: (cw.clean() and cw.files == [] and len(cw.worlds) == 3 and len(cw.made) == 3 and cw.on(FID2) == cw.made[1:2] and cw.on(FID3) == cw.made[2:] and "pat111" not in cw.on(FID3)
              and any(cw.made[2] in l and "beside 2 same-name chart(s) (pat111, %s)" % cw.made[1] in l for l in cw.said(2)), (cw.entered, cw.made, cw.said())))
r1 = Feed().drop(msg(FID, ZO, A_FIRST, P8), msg(FID2, ZO, A_FIRST, P8), msg(FID3, ZO, A_FIRST, "")); r1.run(); er1 = _first(r1, K(ZO, A_FIRST, P8))
step("two ids that share one name-and-date key (the placeholder under both - neither has a key of its own) beside a third id of that name under a key of its own: a chart is made only for a patient with a key of its own, so the THIRD "
     "one's chart is made in the first run - a patient that comes only under a shared key never counts as the one whose chart is made (the third would wait behind it for ever); the two others wait for that chart, said plainly, no question for William",
     lambda: (r1.clean() and [(d_, m_) for _n, d_, m_ in _made(r1.worlds[0])] == [(P_MDY, FID3.upper())] and r1.entered == [(FID3, r1.made[0])] and ok_field(er1, rule=0, why=FI.WHY_SAME_RUN, for_william=False, decided_for=[], by_proof={}, waits_for=[FID3])
              and "resolved" not in er1 and not any(FID in l or FID2 in l for l in r1.said(0)), (r1.worlds[0].err, _made(r1.worlds[0]), brief(er1), r1.said(), r1.log(0)[-900:])))
r1.run(); er1b = r1.worlds[1].match().get(K(ZO, A_FIRST, P8), {}) if len(r1.worlds) > 1 and r1.worlds[1] is not None else {}
step("... and the next run weighs the two against it: nothing but the name ties them to the chart the feed made for the third id, and that chart has no birth date - not entered there on the name alone; ONE line for William names both ids and the chart",
     lambda: (r1.clean() and ok_field(er1b, rule=0, why=_W_OWNED, candidates=r1.made, for_william=True, decided_for=[]) and len(r1.made) == 1 and r1.entered == [(FID3, r1.made[0])]
              and r1.said(1) == ["FOR WILLIAM: no chart chosen and none made for Claimocity ids %s, %s: %s (chart %s) - same person or not?" % (FID, FID2, _W_OWNED, r1.made[0])], (brief(er1b), r1.said(1))))
# ---- the chart a patient waits for could not be made (11/25/2026, the independent verification) ----------------------------------------------------
# Who waits is settled by the resolve step, before the new-chart step knows whether the chart can be made. When AdvancedMD refused it, the id
# that waited for it said in every run 'a new chart is made in this run for another Claimocity id', which was not true, and was never a
# question for William. The new-chart step knows the refusal: it says so, in fixed words of its own, at the top beside the first id's line.
rf = Feed(addfault="the chart could not be saved (test)").drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, "XANDER", BD_FAR)); rf.run(); rf.run()
def _rf(n): return rf.worlds[n].match().get(K(ZO, "XANDER", BD_FAR), {}) if n < len(rf.worlds) and rf.worlds[n] is not None else {}
step("AdvancedMD refuses the first id's new chart: the id that waits for it does not wait on a sentence that is not true - the new-chart step says that the chart it waits for could NOT be made, for William, beside the first id's own line, "
     "in every run in which the refusal stands (until then: 'a new chart is made in this run', not for William, run after run)",
     lambda: (rf.clean() and rf.made == [] and rf.entered == [] and len(rf.files) == 1 and FI.problems(_rf(0)) == []
              and all(ok_field(_rf(n), rule=0, why=_W_FAILED, for_william=True, status="AMBIGUOUS") and "resolved" not in _rf(n) and len([l for l in rf.said(n) if FID2 in l and _W_FAILED in l]) == 1
                      and len([l for l in rf.said(n) if FID in l and "could NOT be made" in l]) == 1 for n in (0, 1)), ([w.err for w in rf.worlds if w], brief(_rf(0)), rf.said(0), rf.said(1))))
rnum = Feed(dup_always=True).drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_OFF)); rnum.run(); ernum = _first(rnum, K(ZO, A_FIRST, BD_OFF))
step("... the same when no chart NUMBER could be found for the first id (every number answered 'Duplicate chart'): whatever the reason the awaited chart was not made, the id that waits for it says so, for William",
     lambda: (rnum.clean() and rnum.made == [] and ok_field(ernum, rule=0, why=_W_FAILED, for_william=True) and [f_.get("why") for f_ in rnum.worlds[0].reg()["failed"]] == [FI.FAIL_NUMBER]
              and len([l for l in rnum.said(0) if FID2 in l and _W_FAILED in l]) == 1, (rnum.worlds[0].err, brief(ernum), rnum.said(0))))
rkey = Feed(addfault="the chart could not be saved (test)").drop(msg(FID, ZO, A_FIRST, P8), msg(FID2, ZO, A_FIRST, P8), msg(FID3, ZO, A_FIRST, "")); rkey.run(); erkey = _first(rkey, K(ZO, A_FIRST, P8))
step("... and a key that several ids share and that waits for the refused chart says it once, for William, with every id of the key",
     lambda: (rkey.clean() and rkey.made == [] and ok_field(erkey, rule=0, why=_W_FAILED, for_william=True, decided_for=[]) and "resolved" not in erkey
              and [l for l in rkey.said(0) if _W_FAILED in l] == ["FOR WILLIAM: no chart chosen and none made for Claimocity ids %s, %s: %s" % (FID, FID2, _W_FAILED)], (rkey.worlds[0].err, brief(erkey), rkey.said(0))))
rf.opts = {}; rf.run(); rf.run()
step("... and when AdvancedMD takes the chart again it is made, the other id waits ONE run in the plain words of the wait (no question for William), and the run after weighs it against that chart - "
     "here a namesake with a far-apart birth date: a chart of its own beside it, with the question",
     lambda: (rf.clean() and rf.files == [] and len(rf.made) == 2 and ok_field(_rf(2), rule=0, why=FI.WHY_SAME_RUN, for_william=False) and not any(FID2 in l for l in rf.said(2)) and rf.on(FID) == rf.made[:1] and rf.on(FID2) == rf.made[1:]
              and any("beside 1 same-name chart(s)" in l and rf.made[1] in l for l in rf.said(3)), ([w.err for w in rf.worlds if w], rf.entered, rf.made, rf.said(2), rf.said(3))))
# ---- a slip in the date does not wait (identity rule .4 - the checkers of round 1) -----------------------------------------------------------------
# Round 1 let EVERY answer by rules 5 to 8 wait while the batch makes a same-name chart. A patient whose own chart carries a date one keystroke
# from the feed's (rule 5) has evidence of her own - the full name and the slip: she does not wait for ANOTHER patient's new chart. Round 1 made
# her wait, and while AdvancedMD refused that other chart neither visit was entered, run after run ('no chart until that chart is made'). Only an
# answer by the name alone (rules 6, 7 and 8) and a patient that would get a new chart still wait.
SLIPPED = [chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 3), 0)])]      # her own chart; the feed sends her date one digit off
s2 = Feed(SLIPPED, addfault="the chart could not be saved (test)").drop(msg(FID, ZO, "XANDER", BD_FAR), msg(FID2, ZO, A_FIRST, BD_OFF)); s2.run(); s2.run(); es2 = _first(s2, K(ZO, A_FIRST, BD_OFF))
step("a patient whose OWN chart carries a date one digit off the feed's (rule 5) beside a NEW patient of the same last name whose first name shares three letters, AdvancedMD refusing the new patient's chart run after run: her visit is entered "
     "on her own chart in the FIRST run - she does not wait for another patient's chart (round 1: she waited behind it and neither visit was entered, run after run); of the two ids only the new patient's stands at the top, and the next run looks up him alone",
     lambda: (s2.clean() and s2.entered == [(FID2, "pat101")] and s2.made == [] and len(s2.files) == 1 and ok_field(es2, rule=5, resolved="pat101", status="FOUND", for_william=False, flags=[FI.FLAG_DATE + FI.SLIP_DIGIT]) and "waits_for" not in es2
              and all(len([l for l in s2.said(n) if FID in l and "could NOT be made" in l]) == 1 and not any(FID2 in l for l in s2.said(n)) for n in (0, 1)) and set(s2.worlds[1].match()) == {K(ZO, "XANDER", BD_FAR)},
              ([w.err for w in s2.worlds if w], s2.entered, brief(es2), s2.said(0), s2.said(1))))
s1 = Feed(SLIPPED).drop(msg(FID, ZO, "XANDER", BD_FAR), msg(FID2, ZO, A_FIRST, BD_OFF)).runs(3)
step("... and when AdvancedMD takes the new chart: ONE run - her visit on her own chart by the slip, his on his new chart (with the question about it for William); nobody waits and the file is done",
     lambda: (s1.clean() and len(s1.worlds) == 1 and s1.files == [] and len(s1.made) == 1 and sorted(s1.entered) == sorted([(FID, s1.made[0]), (FID2, "pat101")]) and _first(s1, K(ZO, A_FIRST, BD_OFF)).get("rule") == 5
              and not any(v.get("why") == FI.WHY_SAME_RUN for v in s1.worlds[0].match().values()) and not any(FID2 in l for l in s1.said()), (s1.entered, s1.made, s1.said())))
NODOB = [chart(101, ZO, A_FIRST, "", charges=[(ymd(Y - 1, 10, 3), 0)])]      # the same chart without a date of its own
for _rule, _d in ((6, BD), (8, P8)):
    def _still(_rule=_rule, _d=_d):
        alone = World([msg(FID2, ZO, A_FIRST, _d)], NODOB).ingest().match().get(K(ZO, A_FIRST, _d), {})
        f = Feed(NODOB).drop(msg(FID, ZO, "XANDER", BD_FAR), msg(FID2, ZO, A_FIRST, _d)); f.run(); e = _first(f, K(ZO, A_FIRST, _d))
        return (f.clean() and (alone.get("rule"), alone.get("resolved")) == (_rule, "pat101") and len(f.made) == 1 and f.entered == [(FID, f.made[0])] and ok_field(e, rule=0, why=FI.WHY_SAME_RUN, for_william=False, waits_for=[FID])
                and "resolved" not in e and not any(FID2 in l for l in f.said(0)), (alone.get("rule"), f.entered, brief(e), f.said(0)))
    step("what still waits beside such a new patient - an answer by the NAME ALONE, rule %d (alone in a batch it takes the chart at once; here: no chart in this run, the plain words of the wait, the id it waits for named, nothing for William; "
         "rule 7 waits the same way - the long-time chart above)" % _rule, _still)
def _held_waits():      # the same chart without a date, now an earlier Claimocity id's in the patient map: alone, the id is asked about at once; beside a new patient of the batch it waits first
    alone = World([msg(FID2, ZO, A_FIRST, BD)], NODOB, pmap={FID5: "pat101"}).ingest(); ea = alone.match().get(K(ZO, A_FIRST, BD), {})
    f = Feed(NODOB, pmap={FID5: "pat101"}).drop(msg(FID, ZO, "XANDER", BD_FAR), msg(FID2, ZO, A_FIRST, BD)); f.run(); e = _first(f, K(ZO, A_FIRST, BD)); f.run()
    return (f.clean() and alone.clean() and ok_field(ea, rule=0, why=_W_OWNED, for_william=True) and len([l for l in _william(alone) if FID2 in l and "same person or not?" in l]) == 1
            and ok_field(e, rule=0, why=FI.WHY_SAME_RUN, for_william=False, waits_for=[FID]) and not any(FID2 in l for l in f.said(0)) and len(f.worlds) == 2 and len(f.made) == 2 and f.on(FID2) == f.made[1:] and "pat101" not in f.on(FID2)
            and any(f.made[1] in l and "beside 2 same-name chart(s) (pat101, %s)" % f.made[0] in l for l in f.said(1)), (brief(ea), brief(e), f.entered, f.made, f.said()))
step("... and so does an answer the patient map HELD BACK (rule 6 on a chart without a date that is another Claimocity id's): alone in a batch William is asked about it at once; beside a new patient of the batch it waits first - "
     "no question in that run, because the next run weighs it against the chart that run made (here: no longer the only same-name chart - a chart of its own beside both, with the question)", _held_waits)
# ---- rules without proof: two of one batch on one chart, and the patient map (11/25/2026, the independent verification) ---------------------------
NODATE = [chart(101, ZO, A_FIRST, "")]
d1 = Feed(NODATE).drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_FAR)); d1.run(); md1 = d1.worlds[0].match()
step("ONE same-name chart with no birth date and, in one batch, two feed patients of that name with far-apart birth dates (two people): NEITHER takes the chart (until then both did, by rule 6 - the second one's visit on the first "
     "one's chart and plan, and William got the same FYI line twice); no chart is made; ONE line each for William names the Claimocity id and the chart",
     lambda: (d1.clean() and d1.entered == [] and d1.made == [] and all(ok_field(md1.get(k, {}), rule=0, why=_W_FAR, candidates=["pat101"], for_william=True, status="AMBIGUOUS") and "resolved" not in md1.get(k, {}) for k in (K(ZO, A_FIRST, BD), K(ZO, A_FIRST, BD_FAR)))
              and len(d1.said()) == 2 and all(len([l for l in d1.said() if i_ in l and "pat101" in l and _W_FAR in l]) == 1 for i_ in (FID, FID2)), (d1.worlds[0].err, {k[-8:]: brief(v) for k, v in md1.items()}, d1.said())))
d2 = Feed(NODATE).drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_OFF)); d2.run()
step("... two whose birth dates are one digit apart may be one person: rule 6 for both, as before - each FYI line names its own Claimocity id",
     lambda: (d2.clean() and sorted(d2.entered) == [(FID, "pat101"), (FID2, "pat101")] and sorted(d2.said()) == sorted("FOR WILLIAM: pat101 %s (FYI) - Claimocity id %s" % (FI.WHY[6], i_) for i_ in (FID, FID2)), (d2.entered, d2.said())))
d3 = Feed(NODATE).drop(msg(FID, ZO, A_FIRST, BD), msg(FID2, ZO, A_FIRST, P8)); d3.run()
step("... one with a real date beside one with none: rules 6 and 8, as before", lambda: (d3.clean() and sorted(d3.entered) == [(FID, "pat101"), (FID2, "pat101")] and sorted(v["rule"] for v in d3.worlds[0].match().values()) == [6, 8], (d3.entered, d3.said())))
d4 = Feed(NODATE).drop(msg(FID, ZO, A_FIRST, BD)); d4.run()
step("... and one patient alone: rule 6 with its FYI, as before (the chart was there before the feed: nobody in the patient map owns it)",
     lambda: (d4.clean() and d4.entered == [(FID, "pat101")] and d4.said() == ["FOR WILLIAM: pat101 %s (FYI) - Claimocity id %s" % (FI.WHY[6], FID)], (d4.entered, d4.said())))
sk = Feed().drop(msg(FID, ZO, A_FIRST, P8)); sk.run(); sk.drop(msg(FID2, ZO, A_FIRST, BD)); sk.run(); sk.drop(msg(FID3, ZO, A_FIRST, "")); sk.run()
def _sk(n, k): return sk.worlds[n].match().get(k, {}) if n < len(sk.worlds) and sk.worlds[n] is not None else {}
step("the same over three runs: a new patient sent with no birth date gets a chart with the placeholder date; the NEXT same-name patient, with a real date, is not entered on it by rule 6, and a third without a date not by rule 8 - "
     "that chart is the first Claimocity id's in the patient map and nothing but the name ties the others to it (until then a chart with no birth date took every same-name patient that came, one run after the other). "
     "No chart is made; ONE line for William each, with the id, the chart and the question",
     lambda: (sk.clean() and len(sk.made) == 1 and sk.entered == [(FID, sk.made[0])] and len(sk.files) == 2 and ok_field(_sk(1, K(ZO, A_FIRST, BD)), rule=0, why=_W_OWNED, candidates=sk.made, for_william=True)
              and ok_field(_sk(2, K(ZO, A_FIRST, "")), rule=0, why=_W_OWNED, candidates=sk.made, for_william=True)
              and sk.said(1) == ["FOR WILLIAM: no chart chosen and none made for Claimocity id %s: %s (chart %s) - same person or not?" % (FID2, _W_OWNED, sk.made[0])]
              and len([l for l in sk.said(2) if FID3 in l and sk.made[0] in l and "same person or not?" in l]) == 1, ([w.err for w in sk.worlds if w], sk.entered, sk.said())))
o7 = World([msg(FID, QU, B_FIRST, P8)], SIX, pmap={FID5: "pat113", FID4: "pat999"}).ingest(); e7o = o7.match().get(K(QU, B_FIRST, P8), {})
step("the 11/8 patient under a NEW Claimocity id when the feed's patient map already gives one of the six charts to ANOTHER Claimocity id (the feed knows this patient): Claimocity sent no date and the six charts carry ONE - rule 7, the live chart, "
     "at once and without a question, exactly as when nobody in the map owns a chart (identity rule .4; round 1 asked William 'same person or not?' and entered nothing, run after run)",
     lambda: (o7.clean() and ok_field(e7o, resolved="pat116", rule=7, status="AMBIGUOUS", flags=["no birth date from Claimocity"], pids=["pat%d" % n for n in range(111, 117)], feed_dob="none", for_william=False) and o7.amd.added == []
              and sorted(o7.txh_calls) == ["pat%d" % n for n in range(111, 117)] and _william(o7) == [], (o7.err, brief(e7o), _william(o7))))
SIX0 = [dict(c, dob="") for c in SIX]      # the same six charts WITHOUT a date of their own
o8 = World([msg(FID, QU, B_FIRST, P8)], SIX0, pmap={FID5: "pat113", FID4: "pat999"}).ingest(); e8o = o8.match().get(K(QU, B_FIRST, P8), {})
step("... but six same-name charts WITHOUT a date, one of them another Claimocity id's in the map: no date on either side, nothing but the name (rule 8) - no chart on the rule's own word; William is asked, "
     "the chart named is the one the map knows (his answer goes into the repository's map), and no chart's activity is read for it",
     lambda: (o8.clean() and ok_field(e8o, rule=0, why=_W_OWNED, candidates=["pat113"], for_william=True, status="AMBIGUOUS", pids=[]) and "resolved" not in e8o and o8.amd.added == [] and o8.txh_calls == []
              and _william(o8) == ["FOR WILLIAM: no chart chosen and none made for Claimocity id %s: %s (chart pat113) - same person or not?" % (FID, _W_OWNED)], (o8.err, brief(e8o), _william(o8))))
u7 = World([msg(FID, QU, B_FIRST, P8)], SIX0, pmap={FID5: "pat999", FID: "pat113"}).ingest(); e7u = u7.match().get(K(QU, B_FIRST, P8), {})
step("... a map that gives those charts to nobody else (another chart is another patient's; an entry under this patient's OWN Claimocity id is not 'another id'): rule 8, the live chart, with its FYI",
     lambda: (u7.clean() and ok_field(e7u, resolved="pat116", rule=8, for_william=True) and u7.amd.added == [], (u7.err, brief(e7u))))
b7 = World([msg(FID, QU, B_FIRST, P8)], SIX0, pmap="{ this is no JSON").ingest(); e7b = b7.match().get(K(QU, B_FIRST, P8), {})
step("... a patient map that cannot be read is said in ONE line and nothing is held back on it (the driver itself stops on such a file before any step runs)",
     lambda: (b7.clean() and ok_field(e7b, resolved="pat116", rule=8) and len([l for l in b7.out["claimocity_match.py"].splitlines() if l.startswith("MATCH: registers/claimocity_patient_map.json could not be read")]) == 1,
              (b7.err, brief(e7b), b7.out.get("claimocity_match.py"))))
s5 = World([msg(FID, ZO, A_FIRST, BD_OFF)], [chart(101, ZO, A_FIRST, BD)], pmap={FID5: "pat101"}).ingest(); e5s = s5.match().get(K(ZO, A_FIRST, BD_OFF), {})
step("... and a slip in the birth date (rule 5) is not held back by the map - nor is a rule with proof (here rule 2, the same date)",
     lambda: (lambda w2: (s5.clean() and ok_field(e5s, resolved="pat101", rule=5, for_william=False) and w2.clean() and ok_field(w2.match().get(K(ZO, A_FIRST, BD), {}), resolved="pat101", rule=2), (brief(e5s), w2.err)))(
         World([msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO, A_FIRST, BD)], pmap={FID5: "pat101"}).ingest()))
# ---- a chart William called a duplicate (11/25/2026, the independent verification; his word of 11/9/2026) -------------------------------------------
# registers/feed_duplicate_charts.json - {"pat<duplicate>": {"proper": "pat<proper>", "approved_by": his word and its date}} - written only on
# his word (its home is the repository; the ingest copies it into the workspace). A listed duplicate is never offered as a candidate: the
# proper chart stands in its place. An entry without his word, or of another shape, counts for nothing.
def WORD(): return "William %d/%d/%d" % (11, 25, 2026)
DUPS = {"pat102": {"proper": "pat101", "approved_by": WORD()}}
TWO = [chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 3), 0)]), chart(102, ZO, A_FIRST, BD_FAR, mrn=FID2.upper(), charges=[(ymd(Y, 1, 5), 0)])]      # the proper chart - and the chart the feed once made for another id of this patient, with Claimocity's wrong date
def _dup(msgs, charts, key, **k): w = World(list(msgs), list(charts), **k).ingest(); return w, w.match().get(key, {})
g0, eg0 = _dup([msg(FID3, ZO, A_FIRST, BD_FAR)], TWO, K(ZO, A_FIRST, BD_FAR), pmap={FID2: "pat101"})
step("the defect as it was, and as it stays while his word is not in the workspace: William called the second chart a duplicate and the map was re-pointed, but the chart stands in AdvancedMD - the patient's NEXT Claimocity id, "
     "sent with the same wrong date, is matched to the duplicate by name and the same birth date (rule 2), without a word", lambda: (g0.clean() and ok_field(eg0, resolved="pat102", rule=2, flags=[]), (g0.err, brief(eg0))))
g1, eg1 = _dup([msg(FID3, ZO, A_FIRST, BD_FAR)], TWO, K(ZO, A_FIRST, BD_FAR), pmap={FID2: "pat101"}, dups=DUPS)
step("... with his word in registers/feed_duplicate_charts.json the duplicate is never offered: the PROPER chart stands in its place - the name and the birth date Claimocity keeps sending are the duplicate's, so the visit goes "
     "to the proper chart (rule 2); a flag says a duplicate stood behind it, and the match step says in a line of chart ids which chart stood for which",
     lambda: (g1.clean() and ok_field(eg1, resolved="pat101", rule=2, status="FOUND", flags=[_F_DUP], candidates=["pat101"], pids=["pat101"], for_william=False) and g1.amd.added == [] and FI.problems(eg1) == []
              and not any(c.get("pid") == "pat102" for c in eg1.get("lookup") or []) and len([l for l in g1.out["claimocity_match.py"].splitlines() if "pat102" in l and "pat101" in l and "duplicate" in l]) == 1,
              (g1.err, brief(eg1), g1.out.get("claimocity_match.py"))))
g2, eg2 = _dup([msg(FID3, ZO, A_FIRST, P8)], TWO, K(ZO, A_FIRST, P8), dups=DUPS)
step("... the next id comes with NO birth date: the two are ONE chart with one date, the proper chart's - rule 7 (as two charts their two dates would have made a THIRD chart for this patient)",
     lambda: (g2.clean() and ok_field(eg2, resolved="pat101", rule=7, candidates=["pat101"], flags=["no birth date from Claimocity", _F_DUP]) and g2.amd.added == [], (g2.err, brief(eg2))))
g2m, eg2m = _dup([msg(FID3, ZO, A_FIRST, P8)], TWO, K(ZO, A_FIRST, P8), pmap={FID4: "pat102"}, dups=DUPS)
step("... also when the map still gives another Claimocity id to the DUPLICATE: the proper chart carries a date, and rule 7 is not held back by the map (identity rule .4)",
     lambda: (g2m.clean() and ok_field(eg2m, resolved="pat101", rule=7, candidates=["pat101"], flags=["no birth date from Claimocity", _F_DUP], for_william=False) and g2m.amd.added == [], (g2m.err, brief(eg2m))))
TWO0 = [dict(TWO[0], dob=""), TWO[1]]      # the proper chart WITHOUT a date of its own, and its listed duplicate (which carries one)
g2n, eg2n = _dup([msg(FID3, ZO, A_FIRST, BD2)], TWO0, K(ZO, A_FIRST, BD2), pmap={FID4: "pat102"}, dups=DUPS)
step("... and a Claimocity id the map still gives to the DUPLICATE counts as the proper chart's: a proper chart WITHOUT a date of its own is not taken on the name alone by a third id (rule 6) - held back there too, for William, the proper chart named",
     lambda: (g2n.clean() and ok_field(eg2n, rule=0, why=_W_OWNED, candidates=["pat101"], for_william=True) and "resolved" not in eg2n and g2n.amd.added == [], (g2n.err, brief(eg2n))))
g2o, eg2o = _dup([msg(FID3, ZO, A_FIRST, BD2)], TWO0, K(ZO, A_FIRST, BD2), dups=DUPS)
step("... (the same two charts when the map gives neither to anybody: rule 6, the proper chart - the flag says a duplicate stood behind it)",
     lambda: (g2o.clean() and ok_field(eg2o, resolved="pat101", rule=6, candidates=["pat101"], for_william=True) and _F_DUP in (eg2o.get("flags") or []) and g2o.amd.added == [], (g2o.err, brief(eg2o))))
g3, eg3 = _dup([msg(FID3, ZO, A_FIRST, BD_FAR)], [chart(101, WE, C_FIRST, BD), TWO[1]], K(ZO, A_FIRST, BD_FAR), dups=DUPS)
step("... the proper chart stands under ANOTHER name (the lookups for this name do not list it): it still stands in the duplicate's place - what speaks for the duplicate is weighed under the proper chart's id",
     lambda: (g3.clean() and ok_field(eg3, resolved="pat101", rule=2, candidates=["pat101"], flags=[_F_DUP]) and g3.amd.added == [], (g3.err, brief(eg3))))
g4, eg4 = _dup([msg(FID3, ZO, A_FIRST, BD2, in1=[("Humana Gold", M1)])], [TWO[0], dict(TWO[1], members=[M1])], K(ZO, A_FIRST, BD2), dups=DUPS)
step("... a number the feed has in common with the DUPLICATE (the member number the feed itself once put on it) speaks for the proper chart: rule 4, whatever the dates",
     lambda: (g4.clean() and ok_field(eg4, resolved="pat101", rule=4, evidence=["member"], candidates=["pat101"]) and _F_DUP in (eg4.get("flags") or []) and g4.amd.added == [], (g4.err, brief(eg4))))
g5, eg5 = _dup([msg(FID3, ZO, A_FIRST, BD_FAR)], TWO + [chart(103, ZO, A_FIRST, BD2)], K(ZO, A_FIRST, BD_FAR), dups={"pat102": {"proper": "pat103", "approved_by": WORD()}, "pat103": {"proper": "pat101", "approved_by": WORD()}})
step("... a duplicate of a duplicate: the chart at the end of the chain stands for both", lambda: (g5.clean() and ok_field(eg5, resolved="pat101", rule=2, candidates=["pat101"], flags=[_F_DUP]), (g5.err, brief(eg5))))
for _what, _bad in (("without approved_by", {"pat102": {"proper": "pat101"}}), ("whose approved_by is empty", {"pat102": {"proper": "pat101", "approved_by": " "}}), ("whose proper chart is no chart id", {"pat102": {"proper": "101", "approved_by": WORD()}}),
                    ("that is no entry of this shape", {"pat102": "pat101"}), ("that names itself", {"pat102": {"proper": "pat102", "approved_by": WORD()}}),
                    ("of two charts that are each listed as the other's duplicate (which is the proper one nobody knows)", {"pat102": {"proper": "pat101", "approved_by": WORD()}, "pat101": {"proper": "pat102", "approved_by": WORD()}})):
    step("an entry %s counts for nothing: the chart is weighed like any other (and is chosen here, by name and the same birth date)" % _what,
         lambda _bad=_bad: (lambda w, e: (w.clean() and ok_field(e, resolved="pat102", rule=2, flags=[], candidates=["pat101", "pat102"]), (w.err, brief(e))))(*_dup([msg(FID3, ZO, A_FIRST, BD_FAR)], TWO, K(ZO, A_FIRST, BD_FAR), dups=_bad)))
for _what, _bad in (("that cannot be read", "{ this is no JSON"), ("that is a list", [DUPS])):
    step("a duplicates file %s is said in ONE line and nothing is decided on it: every chart is weighed as without the file" % _what,
         lambda _bad=_bad: (lambda w, e: (w.clean() and ok_field(e, resolved="pat102", rule=2, flags=[]) and len([l for l in w.out["claimocity_match.py"].splitlines() if l.startswith("MATCH: registers/feed_duplicate_charts.json could not be read")]) == 1,
                                           (w.err, brief(e), w.out.get("claimocity_match.py"))))(*_dup([msg(FID3, ZO, A_FIRST, BD_FAR)], TWO, K(ZO, A_FIRST, BD_FAR), dups=_bad)))
# ---- the new-chart register and the feed's own payer text (11/25/2026, the independent verification) ----------------------------------------------
wpf = World([msg(FID, WE, C_FIRST, BD, in1=[("HUMANA - " + WE + " " + C_FIRST, M2)])], []).ingest(); rpf = (wpf.reg()["created"] or [{}])[0]
step("the new-chart register keeps nothing of the feed's own payer text: of a carrier field that carries more than a payer (here the patient's name behind it) it keeps the carrier code the payer was mapped to, AdvancedMD's plan id "
     "and its place in the order - until then 'from' kept the first 30 characters of the text and they went to the repository",
     lambda: (wpf.clean() and rpf.get("plans") == [{"code": "HUM01", "ins": "ins701", "seq": "1"}] and wpf.ins == [("pat9001", "car6285", M2)] and WE not in json.dumps(wpf.reg()) and C_FIRST not in json.dumps(wpf.reg()), (wpf.err, wpf.reg(), wpf.ins)))
sp4 = _steps([msg(FID, ZO, A_FIRST, BD_OFF), msg(FID, ZO, "YOLANDRA", BD_OFF)], [chart(190, ZO, A_FIRST, BD)] + [chart(200 + n, ZO, A_FIRST + " A%02d" % n, BD_FAR) for n in range(1, 56)]); ms4 = sp4.match()
step("one Claimocity id under two first names in one batch, the list of same-name charts cut short for ONE of them: the worst of the two counts for the patient - no chart by the slip alone; one new chart, flagged, for William",
     lambda: (sp4.clean() and len(ms4) == 2 and all(ok_field(v, rule=9, cut="full", for_william=True, resolved="pat9001") and v.get("flags") == ["same-name charts not used", FI.FLAG_CUT] for v in ms4.values()) and len(sp4.amd.added) == 1,
              (sp4.err, {k.split("|")[0][-8:]: brief(v) for k, v in ms4.items()})))
def _differential(n, seed, spellings=None, **opts):
    """n feed patients put together at random - the last name in one of its spellings, up to five charts of that name in others (now and then a chart of another name) - go through the match and
    resolve steps, and each must come out as the rule itself answers when it is given EVERY chart of the stand-in. A difference means a chart was not weighed that the rule calls the same name."""
    rnd = random.Random(seed); bad = []; rules = collections.Counter(); t8 = datetime.date.today().strftime("%Y%m%d")
    firsts = [A_FIRST, A_FIRST + " K", "XANDRA", "XAN", A_FIRST + "NNE", D_FIRST, B_FIRST[:3], B_FIRST]; dates = [BD, BD_OFF, ymd(Y - 85, 4, 15), BD_FAR, P8, "", BD2]; ssns = ["", "", "", S1, S2]; mems = [[], [], [], [M1], [M2]]
    for i in range(n):
        f = rnd.randrange(len(FAMILIES)); fam = FAMILIES[f]; fl = spellings[f] if spellings else rnd.choice(fam); ff = rnd.choice(firsts); fd = rnd.choice(dates); fs = rnd.choice(ssns); fm = rnd.choice(mems)
        charts = [chart(nn, rnd.choice(rnd.choice(FAMILIES) if rnd.random() < 0.1 else fam), rnd.choice(firsts), rnd.choice(dates), ssn=rnd.choice(ssns), members=rnd.choice(mems), mrn=rnd.choice(["", "", "", FID.upper()]),
                        charges=[(ymd(Y - 1, rnd.randint(1, 12), rnd.randint(1, 28)), 0)] * rnd.randint(0, 3)) for nn in rnd.sample(range(101, 140), rnd.randint(0, 5))]
        w = World([msg(FID, fl, ff, fd, ssn=fs, in1=[("Humana Gold", x) for x in fm])], charts)
        for k, v in opts.items(): setattr(w.amd, k, v)
        w.run("claimocity_match.py", READS, argv=("feed_unknown_%s.json" % STAMP,))
        if not w.err["claimocity_match.py"]: w.run("claimocity_resolve.py", READS)
        e = w.match().get(K(fl, ff, fd), {})
        all_charts = [{"id": c["id"], "name": lf(c["last"], c["first"]), "dob": c["dob"], "mrn": c["mrn"], "ssn": c["ssn"], "members": c["members"], "last_dos": max([d for d, v in c["charges"] if not v] or [""]), "charges": len([d for d, v in c["charges"] if not v])} for c in charts]
        want = FI.decide({"id": FID, "name": cf(fl, ff), "dob": fd, "ssn": fs, "members": fm}, all_charts, t8); rules[want["rule"]] += 1
        if not w.clean() or [e.get(x) for x in ("rule", "resolved", "flags", "candidates", "for_william")] != [want["rule"], want["chart"], want["flags"], want["candidates"], want["for_william"]]:
            bad.append({"steps": [e.get(x) for x in ("rule", "resolved", "flags", "candidates", "for_william", "cut")], "the rule given every chart": [want[x] for x in ("rule", "chart", "flags", "candidates", "for_william")], "errors": {k: v for k, v in w.err.items() if v}, "asked": len(w.amd.asked)})
    return bad, rules
step("300 feed patients put together at random, the last name spelled one way in the feed and other ways on the charts: the match and resolve steps answer for every one of them what the rule answers when it is given EVERY chart of the stand-in - "
     "no chart the rule calls the same name goes unweighed (until then 60 of these 300 came out otherwise: a chart missed, a namesake taken, a second chart made)",
     lambda: (lambda bad, rules: (bad == [] and len(rules) >= 8, (len(bad), bad[:2], dict(rules))))(*_differential(300, 1125)))
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
# ---- a lookup form AdvancedMD does not answer (11/25/2026, review of the identity rule): never a second chart for it -------------------------
# Until then ONE 'begins with' lookup that went unanswered twice switched rules 5 to 8 off for every patient after it in the run: the 11/17
# and the 11/8 patient each got a second chart again. Now a form the step can do without never costs a chart: the step goes on with the
# lookups it has always made, and the list of same-name charts counts as cut short only when a page of it really came back full.
B3 = [msg(FID, WE, C_FIRST, BD), msg(FID2, ZO, A_FIRST, BD_OFF), msg(FID3, QU, B_FIRST, P8)]      # an ordinary new patient, the 11/17 patient, the 11/8 patient
C3 = [chart(101, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 10, 2), 0)] * 3), chart(102, ZO, A_FIRST, BD, charges=[(ymd(Y - 1, 12, 14), 0)])] + SIX
def _b3_ok(w, without=""):      # without: which of the three was weighed WITHOUT the every-spelling lookup in a run in which AdvancedMD does answer it - N the new patient, S the slip (11/17), P the placeholder (11/8)
    m = w.match(); c = lambda x: "spelling" if x in without else ""
    return (ok_field(m.get(K(ZO, A_FIRST, BD_OFF), {}), resolved="pat102", rule=5, for_william=False, cut=c("S")) and ok_field(m.get(K(QU, B_FIRST, P8), {}), resolved="pat116", rule=7, for_william=False, cut=c("P"))
            and ok_field(m.get(K(WE, C_FIRST, BD), {}), rule=9, flags=[FI.FLAG_CUT] if "N" in without else [], for_william="N" in without, resolved="pat9001", cut=c("N")) and [p["name"] for p in w.amd.added] == [lf(WE, C_FIRST)])
def _b3_said(w): return (w.err, [(x["chart"], x["dob"] == P_MDY) for x in w.amd.added], {k.rpartition("|")[2] or "none": (v.get("rule"), v.get("resolved"), v.get("cut"), v.get("flags")) for k, v in w.match().items()})
h0 = _steps(B3, C3); N_LOOKUPS = len(h0.amd.asked)
step("three unknown patients in one batch - an ordinary new one, the 11/17 patient, the 11/8 patient: ONE new chart, the two others on their live charts; three name lookups for each (the two the steps have always made - "
     "the name as the feed writes it, and its last name under any first name - and every spelling of the last name)",
     lambda: (h0.clean() and _b3_ok(h0) and N_LOOKUPS == 9 and len([n for n in h0.amd.asked if spelt(n)]) == 3 and not any("%," in n for n in h0.amd.asked) and all(v.get("every_spelling") is True for v in h0.match().values()), (_b3_said(h0), h0.amd.asked)))
def _hiccups():      # the same batch, lookup number p+1 of the run timing out twice and every later call answered - for every p
    bad = []; stopped = 0
    for p in range(N_LOOKUPS):
        w = World(B3, C3); w.amd.bad["lookuppatient"] = ["ok"] * p + ["raise", "raise"]; w.ingest()
        if w.err.get("claimocity_match.py"): stopped += 1; good = w.amd.added == [] and "claimocity_resolve.py" not in w.out and not w.amd.refused and not any(v["status"] == "MISSING" for v in w.match().values())
        else: good = w.clean() and _b3_ok(w, {2: "N", 5: "S", 8: "P"}.get(p, ""))      # (the third lookup of each patient is the one the step can do without)
        if not good: bad.append((p, _b3_said(w)))
    return bad, stopped
step("... the same batch with ONE lookup that times out twice, at every place of the run in turn: either the step STOPS with nothing decided and nothing made (a lookup it cannot do without - the next run reads the files again), "
     "or everybody is decided as above - the 11/17 and the 11/8 patient never get a second chart for a lookup AdvancedMD did not answer, wherever in the run it falls; "
     "and when it fell on the NEW patient, whose chart was then made without the every-spelling lookup AdvancedMD answers for the others, that new chart is flagged, for William",
     lambda: (lambda bad, stopped: (bad == [] and stopped == 6 and N_LOOKUPS == 9, (bad[:2], stopped, N_LOOKUPS)))(*_hiccups()))
step("... a lookup the step can do without waits ONE minute at most for its answer (asked twice); the two it cannot do without wait as long as every other AdvancedMD call",
     lambda: (len(h0.amd.limits) == 9 and all(t == (60 if spelt(n) else 0) for n, t in h0.amd.limits), h0.amd.limits))
def _twice_apart():      # four unknown patients; the every-spelling lookup times out twice for the first and for the third, and is answered for the second
    w = World(B3 + [msg(FID4, TH, D_FIRST, BD2)], C3); w.amd.bad["lookuppatient"] = ["ok", "ok", "raise", "raise"] + ["ok"] * 5 + ["raise", "raise"]; w.ingest(); m = w.match()
    return (w.clean() and [m.get(k, {}).get("every_spelling") for k in (K(WE, C_FIRST, BD), K(ZO, A_FIRST, BD_OFF), K(QU, B_FIRST, P8), K(TH, D_FIRST, BD2))] == [False, True, False, True] and len(w.amd.added) == 2
            and not any("not asked again in this run" in l for l in w.out["claimocity_match.py"].splitlines())
            and ok_field(m.get(K(WE, C_FIRST, BD), {}), rule=9, cut="spelling", flags=[FI.FLAG_CUT], for_william=True) and ok_field(m.get(K(QU, B_FIRST, P8), {}), resolved="pat116", rule=7, cut="spelling", for_william=False)
            and ok_field(m.get(K(TH, D_FIRST, BD2), {}), rule=9, cut="", flags=[], for_william=False) and len([l for l in _william(w) if "was made although AdvancedMD's list of same-name charts may be incomplete" in l]) == 1,
            (w.err, {k.rpartition("|")[2] or "none": (v.get("every_spelling"), v.get("cut"), v.get("flags")) for k, v in m.items()}, w.out.get("claimocity_match.py"), _william(w)))
step("... the every-spelling lookup unanswered for one patient, answered for the next, unanswered for a third: that is not 'twice in a row' - it is asked again for the fourth (only two in a row end it for the run); "
     "the NEW chart of the first, made without a lookup AdvancedMD does answer in this run, is flagged for William with the question - the new chart of the fourth, weighed in full, is not", _twice_apart)
def _both_marks():      # no birth date, more charts of the last name than AdvancedMD lists (cut for other first names) AND the every-spelling lookup unanswered for this patient, answered for the next
    w = World([msg(FID, ZO, A_FIRST, ""), msg(FID2, WE, C_FIRST, BD)], [chart(200 + n, ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)]); w.amd.bad["lookuppatient"] = ["ok", "ok", "raise", "raise"]; w.ingest(); e = w.match().get(K(ZO, A_FIRST, ""), {})
    return (w.clean() and ok_field(e, rule=9, cut="spelling", every_spelling=False, for_william=True, flags=["no birth date from Claimocity", FI.FLAG_CUT]) and len(w.amd.added) == 2, (w.err, brief(e), w.amd.asked))
step("... two reasons at once why the list may fall short - cut for other first names, and weighed without the every-spelling lookup: the heavier one counts (the new chart is flagged also when Claimocity sent no birth date)", _both_marks)
def _sharer_marked():      # two ids under one name with no birth date; the every-spelling lookup unanswered for the first (twice), answered for the second
    w = World([msg(FID, QU, B_FIRST, P8), msg(FID2, QU, B_FIRST, P8)], SIX); w.amd.bad["lookuppatient"] = ["ok", "ok", "raise", "raise"]; w.ingest(); e = w.match().get(K(QU, B_FIRST, P8), {})
    return (w.clean() and ok_field(e, resolved="pat116", rule=7, decided_for=[FID, FID2]) and [(s["ids"], s["every_spelling"], s["cut"]) for s in e.get("sharers") or []] == [([FID], False, "spelling"), ([FID2], True, "")] and w.amd.added == [],
            (w.err, brief(e), [(s["ids"], s["every_spelling"], s["cut"]) for s in e.get("sharers") or []]))
step("... and what was gathered for a patient under a key it SHARES carries the same mark (the key still gets the chart the rule gives them both: no rule is switched off)", _sharer_marked)
wb = _steps(B3, C3, no_spell=True, no_begin=True); mb = wb.match()
step("an AdvancedMD that answers neither a % between the letters of the last name nor the 'begins with' form does not stop the feed and costs nobody a chart: the step says so, asks the first for two patients only (twice each), "
     "the second not at all, and goes on with the lookups it has always made - the slip is still read, the placeholder still matched, the new patient gets a plain new chart",
     lambda: (wb.clean() and _b3_ok(wb) and len([n for n in wb.amd.asked if spelt(n)]) == 4 and not any("%," in n for n in wb.amd.asked) and all(v.get("every_spelling") is False for v in mb.values())
              and len([l for l in wb.out["claimocity_match.py"].splitlines() if l.startswith("MATCH: AdvancedMD did not answer the lookup by every spelling of the last name")]) == 2
              and len([l for l in wb.out["claimocity_match.py"].splitlines() if "not asked again in this run" in l]) == 1, (_b3_said(wb), wb.amd.asked, wb.out.get("claimocity_match.py"))))
wi_ = _steps(B3 + [msg(FID4, "DE LA " + YA, E_FIRST, BD2), msg(FID5, TH + "-" + YA, D_FIRST, BD_OFF)], C3 + [chart(121, "DE LA " + YA, E_FIRST, BD2), chart(122, TH + " " + YA, D_FIRST, BD)], no_inner=True); mi_ = wi_.match()
step("an AdvancedMD that takes a % at the END of a lookup only - the lookups the steps have made until now, and nothing else: the step does not stop, also not for a last name of several words (asked for with a % between its words first; "
     "unanswered, then by its first word and as the feed writes it - the two searches the steps have always made); everybody is decided as before, a two-word last name and a hyphen the chart writes as a space included",
     lambda: (wi_.clean() and _b3_ok(wi_) and ok_field(mi_.get(K("DE LA " + YA, E_FIRST, BD2), {}), resolved="pat121", rule=2, every_spelling=False) and ok_field(mi_.get(K(TH + "-" + YA, D_FIRST, BD_OFF), {}), resolved="pat122", rule=5, every_spelling=False)
              and len(wi_.amd.added) == 1, (_b3_said(wi_), wi_.amd.asked, wi_.out.get("claimocity_match.py"))))
BIG = [chart(190, ZO, A_FIRST, BD)] + [chart(200 + n, ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)]      # the patient's own chart (a slip from the feed's date) among 56 of one last name
wf1 = _steps([msg(FID, ZO, A_FIRST, BD_OFF)], BIG, no_spell=True); ef1 = wf1.match().get(K(ZO, A_FIRST, BD_OFF), {})
step("... under a last name with more charts than AdvancedMD lists (50) the 'begins with' form IS asked - only then: answered, every name candidate is in hand and the slip is read (rule 5); the list counts as cut only for other first names",
     lambda: (wf1.clean() and ok_field(ef1, resolved="pat190", rule=5, cut="first", every_spelling=False, for_william=False) and wf1.amd.added == [] and len([n for n in wf1.amd.asked if "%," in n]) == 1, (wf1.err, brief(ef1), wf1.amd.asked)))
wf2 = _steps([msg(FID, ZO, A_FIRST, BD_OFF)], BIG, no_spell=True, no_begin=True); ef2 = wf2.match().get(K(ZO, A_FIRST, BD_OFF), {})
step("... and when that goes unanswered too, the list of same-name charts really may be cut short: nobody is matched by the name alone - a new chart, flagged, for William (the one case left in which a lookup AdvancedMD does not answer costs a chart: a full page AND no narrower lookup)",
     lambda: (wf2.clean() and ok_field(ef2, rule=9, cut="full", for_william=True, flags=["same-name charts not used", FI.FLAG_CUT], resolved="pat9001") and len(wf2.amd.added) == 1, (wf2.err, brief(ef2), wf2.amd.asked)))
wf3 = _steps([msg(FID, ZO, A_FIRST, "")], [chart(101, ZO, A_FIRST, BD), chart(102, ZO + " III", A_FIRST, BD2)] + [chart(200 + n, ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)], no_spell=True); ef3 = wf3.match().get(K(ZO, A_FIRST, ""), {})
step("... the father and the son again (a suffix on one chart, more charts of the last name than AdvancedMD lists), without the every-spelling lookup: the 'begins with' form brings both - two dates, nobody matched by the name alone",
     lambda: (wf3.clean() and ok_field(ef3, rule=9, candidates=["pat101", "pat102"], for_william=True, flags=["same-name charts not used", "no birth date from Claimocity"], every_spelling=False, cut="first") and len(wf3.amd.added) == 1, (wf3.err, brief(ef3), wf3.amd.asked)))
wm2 = _steps([msg(FID, ZO, A_FIRST, BD_OFF), msg(FID2, WE, C_FIRST, BD)], [chart(101, ZO, A_FIRST, BD)], mute_spell=True); mm2 = wm2.match()
step("an AdvancedMD that answers the every-spelling lookup with NO chart although the plain lookup has just listed one: that answer is not believed (the step says so) - the patient is weighed with the lookups the step has always made",
     lambda: (wm2.clean() and ok_field(mm2.get(K(ZO, A_FIRST, BD_OFF), {}), resolved="pat101", rule=5, every_spelling=False, cut="spelling") and ok_field(mm2.get(K(WE, C_FIRST, BD), {}), rule=9, flags=[], every_spelling=True, cut="") and len(wm2.amd.added) == 1
              and len([l for l in wm2.out["claimocity_match.py"].splitlines() if l.startswith("MATCH: AdvancedMD's answer to the lookup by every spelling of the last name")]) == 1, (wm2.err, {k[-8:]: brief(v) for k, v in mm2.items()}, wm2.out.get("claimocity_match.py"))))
wj = _steps(B3, C3 + [chart(300 + n, "AAB%02dKELT" % n, C_FIRST, BD_FAR) for n in range(1, 61)], junk_spell=True)
step("an AdvancedMD that does not understand the every-spelling lookup and answers it with its first 50 charts, whatever was asked: a full page of charts that do not answer to the lookup is no answer - "
     "it is not taken for 'the list is cut short' (which would switch the name-alone rules off for everybody); the step says so and goes on as without it",
     lambda: (wj.clean() and _b3_ok(wj) and all(v.get("every_spelling") is False for v in wj.match().values()) and len([n for n in wj.amd.asked if spelt(n)]) == 2
              and len([l for l in wj.out["claimocity_match.py"].splitlines() if l.startswith("MATCH: AdvancedMD did not answer the lookup by every spelling of the last name")]) == 2, (_b3_said(wj), wj.amd.asked, wj.out.get("claimocity_match.py"))))
wa = _steps([msg(FID, PLAIN, A_FIRST, BD)], [chart(101, APOS, A_FIRST, BD), chart(301, QU, B_FIRST, BD2), chart(302, WE, C_FIRST, BD_FAR)], also=["pat301", "pat302"]); ewa = wa.match().get(K(PLAIN, A_FIRST, BD), {})
step("... but a SHORT answer is used as it comes, also when AdvancedMD lists charts in it for a reason of its own (two charts of other names beside the patient's): only a full page of other charts is no answer",
     lambda: (wa.clean() and ok_field(ewa, resolved="pat101", rule=2, candidates=["pat101"], every_spelling=True) and wa.amd.added == [], (wa.err, brief(ewa), wa.amd.asked)))
wm3 = _steps([msg(FID, ZO, A_FIRST, BD)], [chart(101, ZO + " III", A_FIRST, BD)], mute_spell=True); em3 = wm3.match().get(K(ZO, A_FIRST, BD), {})
step("... also when only the lookup under any first name had listed it (a suffix on the chart: the name as the feed writes it does not list it): whatever the every-spelling lookup answers, the step never sees LESS than the two lookups it has always made",
     lambda: (wm3.clean() and ok_field(em3, resolved="pat101", rule=2, every_spelling=False) and wm3.amd.added == [], (wm3.err, brief(em3), wm3.amd.asked)))
step("120 more patients at random against an AdvancedMD that does not answer the every-spelling lookup, the feed writing every apostrophe, space, period and hyphen of the last name: the lookups the step has always made still bring every chart the rule calls the same name",
     lambda: (lambda bad, rules: (bad == [], (len(bad), bad[:2])))(*_differential(120, 2611, spellings=WRITTEN, no_spell=True)))
# ---- the lookup for ANY first name (rule 3) - 11/25/2026, review of the identity rule ------------------------------------------------------
VQ = "VAN " + QU
r3a = _steps([msg(FID, VQ, A_FIRST, BD)], [chart(190, VQ, D_FIRST, BD)] + [chart(200 + n, "VAN A%02dKELT" % n, C_FIRST, BD_FAR) for n in range(1, 56)]); e3a = r3a.match().get(K(VQ, A_FIRST, BD), {})
step("rule 3 under a two-word last name, beside 55 charts of OTHER last names that begin with the same word: the lookup for any first name asks for THIS last name, not for its first word - the chart is found "
     "(asked by the first word alone the page came back full without it, and a second chart was made without a word)",
     lambda: (r3a.clean() and ok_field(e3a, resolved="pat190", rule=3, flags=["first name differs"], for_william=True, cut="") and r3a.amd.added == [], (r3a.err, brief(e3a), r3a.amd.asked)))
r3c = _steps([msg(FID, VQ, A_FIRST, BD)], [chart(190, VQ, D_FIRST, BD)] + [chart(200 + n, "VAN A%02dKELT" % n, C_FIRST, BD_FAR) for n in range(1, 56)], no_inner=True); e3c = r3c.match().get(K(VQ, A_FIRST, BD), {})
step("... the same against an AdvancedMD that takes a % at the END of a lookup only: the last name is asked for as the feed writes it too (the search the match step made until now), and the chart is found there",
     lambda: (r3c.clean() and ok_field(e3c, resolved="pat190", rule=3, flags=["first name differs"], for_william=True, every_spelling=False) and r3c.amd.added == [], (r3c.err, brief(e3c), r3c.amd.asked)))
r3b = _steps([msg(FID, ZO, A_FIRST, BD)], [chart(100 + n, ZO, "A%02dLMA" % n, BD_FAR) for n in range(1, 56)] + [chart(190, ZO, D_FIRST, BD)]); e3b = r3b.match().get(K(ZO, A_FIRST, BD), {})
step("rule 3 under a last name with more charts than AdvancedMD lists (50), the patient's chart - another first name, exactly the date - not among those listed: the step cannot see it, but it KNOWS the list was cut: "
     "the new chart is flagged, for William, with the question (until then: a plain new chart and not a word)",
     lambda: (r3b.clean() and ok_field(e3b, rule=9, cut="first", flags=[FI.FLAG_CUT], for_william=True, resolved="pat9001") and len(r3b.amd.added) == 1 and any("may be incomplete" in l and "pat9001" in l for l in _william(r3b)), (r3b.err, brief(e3b), _william(r3b))))
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
             "claimocity_resolve.py": "NOR DOES A PATIENT WHOSE OWN CHART IS A SLIP AWAY",
             "claimocity_newcharts.py": "A NEW CHART IS MADE ONLY ON RULE 9 OF THE IDENTITY RULE, ONE PER CLAIMOCITY ID, NEVER WITH AN EMPTY BIRTH DATE"}
def _header(src): return "\n".join(itertools.takewhile(lambda l: l.startswith("#"), src.splitlines()))
for _f, _s in SENTENCES.items():
    check("%s: its PLAIN ENGLISH header carries the one sentence only this version has (the mirror will know the file by it), and the step loads feed_identity" % _f,
          read(_f).startswith("# PLAIN ENGLISH (") and _s in _header(read(_f)) and "feed_identity" in loads(read(_f)), _header(read(_f))[:200])
check("feed_identity.py starts with its PLAIN ENGLISH header and carries the rule's version line", read("feed_identity.py").startswith("# PLAIN ENGLISH (") and re.search(r'(?m)^IDENTITY_RULE_VERSION = "\d{4}-\d\d-\d\d\.\d+"', read("feed_identity.py")) is not None)
# Identity rule .4: the rule changed again, so its version line changes with it - in the helper and in the two tables that name it
# (tools/mirror/mirror.py PROTECTED, claimocity_helpers_current.VERSION_LINES). The checkers of round 1 had found that round's patch changing
# the rule under the old line: a copy of the helpers from before passed as current (the mirror let it go back over the repository's, the
# driver's helper check called it current). The line changes with EVERY revision of the rule, in all three places together.
import shutil
_VNOW, _VOLD = ("2026-11-25." + n_ for n_ in ("4", "3")); _VLINE = 'IDENTITY_RULE_VERSION = "%s"' % _VNOW; _VLINE_OLD = 'IDENTITY_RULE_VERSION = "%s"' % _VOLD
_mirror_src = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
try: HCUR = load("claimocity_helpers_current"); HCUR_ERR = ""
except Exception as e: HCUR = None; HCUR_ERR = "%s: %s" % (type(e).__name__, e)
T("the rule's version line is 2026-11-25.4 - the round in which rule 7 is no longer held back by the patient map and a slip no longer waits: it stands ONCE in feed_identity.py, the mirror's marker for feed_identity.py and the helper check's "
  "version line are that very line, and the line of the round before stands in none of the three (a copy of the round before never passes as current)",
  lambda: (FI.IDENTITY_RULE_VERSION == _VNOW and len(re.findall(r'(?m)^' + re.escape(_VLINE), read("feed_identity.py"))) == 1 and ('"feed_identity.py": \'%s\'' % _VLINE) in _mirror_src and HCUR.VERSION_LINES.get("feed_identity.py") == _VLINE
           and not [f_ for f_, t_ in (("feed_identity.py", read("feed_identity.py")), ("mirror.py", _mirror_src), ("claimocity_helpers_current.py", read("claimocity_helpers_current.py"))) if _VLINE_OLD in t_],
           (getattr(FI, "IDENTITY_RULE_VERSION", None), HCUR_ERR or HCUR.VERSION_LINES.get("feed_identity.py"), ('"feed_identity.py": \'%s\'' % _VLINE) in _mirror_src)))
def _stale_copy_named():
    """The driver's helper check, with no repository clone, over a workspace that holds the current helpers - and again with a copy of feed_identity.py from the round before in it (the same rule file under that round's version line)."""
    rule = re.search(r"POS_RULE = '([^']+)'", read("claimocity_ingest.py")).group(1); d = tempfile.mkdtemp(prefix="feedid_hc_")
    try:
        for f_ in HCUR.FEED_HELPERS: shutil.copy(os.path.join(H, f_), os.path.join(d, f_))
        now = HCUR.make_current(d, repo=os.path.join(d, "no clone here"), rule=rule)[1]
        open(os.path.join(d, "feed_identity.py"), "w").write(read("feed_identity.py").replace(_VLINE, _VLINE_OLD))
        old = HCUR.make_current(d, repo=os.path.join(d, "no clone here"), rule=rule)[1]
        return ("feed_identity.py" not in now and "FEED HELPERS NOT ALL CURRENT" in old and "feed_identity.py" in old, (now, old))
    finally: shutil.rmtree(d, ignore_errors=True)
T("... and it bites: the driver's helper check (claimocity_helpers_current.make_current, no repository clone) calls the current feed_identity.py current and names a copy of the round before - the same rule file under that round's version line - "
  "in its warning for the top of the report", _stale_copy_named)
def _stale_resolve_named():
    """The same check over a workspace whose claimocity_resolve.py lacks the one sentence only the file of identity rule .4 carries - what a copy of the round before looks like to the check (that round's file decided otherwise: a patient whose own chart is a slip away waited for another patient's new chart)."""
    rule = re.search(r"POS_RULE = '([^']+)'", read("claimocity_ingest.py")).group(1); d = tempfile.mkdtemp(prefix="feedid_hc_"); s_ = SENTENCES["claimocity_resolve.py"]
    try:
        for f_ in HCUR.FEED_HELPERS: shutil.copy(os.path.join(H, f_), os.path.join(d, f_))
        now = HCUR.make_current(d, repo=os.path.join(d, "no clone here"), rule=rule)[1]
        open(os.path.join(d, "claimocity_resolve.py"), "w").write(read("claimocity_resolve.py").replace(s_, s_.lower()))
        old = HCUR.make_current(d, repo=os.path.join(d, "no clone here"), rule=rule)[1]
        return ("claimocity_resolve.py" not in now and "FEED HELPERS NOT ALL CURRENT" in old and "claimocity_resolve.py" in old and read("claimocity_resolve.py").count(s_) == 1
                and HCUR.VERSION_LINES.get("claimocity_resolve.py") == s_ and ('"claimocity_resolve.py": "%s"' % s_) in _mirror_src, (now, old))
    finally: shutil.rmtree(d, ignore_errors=True)
T("the resolve step's sentence is the one only the file of rule .4 has ('a slip away' does not wait): the helper check and the mirror know the file by it, and a copy without it - the round before - is named in the warning for the top of the report",
  _stale_resolve_named)
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
