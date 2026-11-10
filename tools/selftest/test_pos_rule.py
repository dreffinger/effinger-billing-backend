#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the place-of-service rule, 11/10/2026)
# Decides: nothing. Loads scripts/helpers/claimocity_import.py with stand-in amd / resave / txh modules in a throwaway folder
#   (no AMD, no network, no patient data - every id, building message and chart here is invented) and proves William's rule:
#     - CCM 99487/99489 in one of the five nursing buildings is entered as place of service 32 - except that it stays at the feed's 31,
#       listed for William, when the chart shows the resident seen at skilled frequency, admitted or readmitted in that calendar month;
#     - ALF / home CCM keeps 13, hospital lines keep 21, an unknown building keeps the old default - nothing else changes;
#     - a nursing facility visit is 32 only for the monthly visit (previous nursing visit 21 to 92 days earlier, not a discharge, no
#       hospital visit of ours in between); it is 31 when the resident is seen once or twice a week, for an initial visit, the first
#       nursing visit on the chart, the first visit of a new stay, and whenever the chart shows neither pattern;
#     - 99497 follows the visit line of the same date; modifier 25, fees, dedupe and the hospital admission date are as before;
#     - every visit takes its building, its clinician and its admission date from ITS OWN feed message (a resident's CCM under the
#       physician and the nurse practitioner's visits in one batch each keep their own clinician; a hospital message and a nursing
#       message of one patient each keep their own building); a message the raw files cannot answer falls back to the patient's
#       last-read values and is reported, and so is any failure inside the rule - the import carries on;
#     - a visit an earlier batch could not enter is still read as history; when the batch's own visits cannot be listed no line is 32;
#     - what AdvancedMD stored is read back from its answer and a different place of service is said loudly;
#     - the feed digest carries one line saying what the rule did, shouts when an old helper ran, and mirror.py never lets a copy of the
#       three helpers without the rule back onto main; the runbook copies them from the repository before every ingest.
# Run: python3 tools/selftest/test_pos_rule.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, importlib.util, io, re, contextlib
import xml.etree.ElementTree as ET
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = os.path.join(ROOT, "scripts", "helpers", "claimocity_import.py")
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)

# ---- a throwaway workspace: the helper reads its batch files from the current folder at import time -------------------------------
tmp = tempfile.mkdtemp(prefix="posrule_"); os.makedirs(os.path.join(tmp, "hl7")); os.makedirs(os.path.join(tmp, "registers"))
os.chdir(tmp)
os.environ.update(FEED_STAMP="SELFTEST", FEED_HL7_DIR=os.path.join(tmp, "hl7"), FEED_DX_CACHE=os.path.join(tmp, "dx.json"))
NPI = "1225327380"                                                     # the practice's own rendering NPI, already in the helper's PROFILE table
BUILDING = {"n1": "BRYNWOOD OPERATIONS LLC", "n2": "Aspire of Tallahassee", "n3": "Oakes Southwood", "a1": "Azalea Gardens ALF",
            "h1": "HCA Florida Capital Hospital", "u1": "A Building The Table Does Not Know"}
NP_NPI = "1235128869"                                                  # the nurse practitioner's, also in the PROFILE table (prof15)
def ft1(cpt, dos):
    f = ["FT1"] + [""] * 25; f[4] = dos; f[10] = "1"; f[19] = "I10"; f[25] = cpt + "^x"; return "|".join(f)
def hl7(fid, fac, admit="", lines=(), npi=NPI):
    pv1 = ["PV1", "1", "I", "", "", "", "", npi + "^x"] + [""] * 36 + [admit]
    return "MSH|^~\\&|feed|" + fac + "|x|x|20261102||DFT^P03|1|P|2.3\rPID|1||" + fid + "\r" + "|".join(pv1) + "\r" + "".join(ft1(c, d) + "\r" for c, d in lines)
open(os.path.join(tmp, "hl7", "a.hl7"), "w").write("".join(hl7(k, v, "20261030" if k == "h1" else "") for k, v in BUILDING.items()))
# b.hl7: messages WITH their charge lines, as the feed sends them (read after a.hl7, so they are "the last message read" per patient)
B = BUILDING
RAW = [("n1", B["n1"], "", [("99487", "20261031"), ("99489", "20261031")], NPI), ("n2", B["n2"], "", [("99309", "20261102")], NPI), ("n2", B["n2"], "", [("99309", "20261105")], NPI),
       ("n3", B["n3"], "", [("99306", "20261103")], NPI), ("a1", B["a1"], "", [("99487", "20261031")], NPI), ("u1", B["u1"], "", [("99487", "20261031")], NPI),
       # m1: the nurse practitioner's visit, then the physician's CCM for the same resident (the CCM is read last)
       ("m1", B["n1"], "", [("99309", "20261102")], NP_NPI), ("m1", B["n1"], "", [("99487", "20261031"), ("99489", "20261031")], NPI),
       # m2: hospital stay, then the nursing building - physician's admission visit, nurse practitioner's follow-up (read last)
       ("m2", B["h1"], "20261018", [("99232", "20261020")], NPI), ("m2", B["n2"], "", [("99306", "20261022")], NPI), ("m2", B["n2"], "", [("99309", "20261025")], NP_NPI),
       # m3: the SAME lines sent from two buildings - no single answer for the message
       ("m3", B["n2"], "", [("99487", "20261031")], NPI), ("m3", B["a1"], "", [("99487", "20261031")], NPI),
       # m4: a visit in one nursing building, the next one in another
       ("m4", B["n1"], "", [("99309", "20261001")], NPI), ("m4", B["n2"], "", [("99309", "20261025")], NPI),
       # m5: one message with two dates, then an admission visit on the later date
       ("m5", B["n1"], "", [("99498", "20270121"), ("99309", "20270120")], NPI), ("m5", B["n1"], "", [("99306", "20270121")], NPI),
       # s1: the visit after three refused ones
       ("s1", B["n2"], "", [("99309", "20261113")], NPI)]
open(os.path.join(tmp, "hl7", "b.hl7"), "w").write("".join(hl7(f, fac, adm, lines, npi) for f, fac, adm, lines, npi in RAW))
json.dump([], open("feed_parsed_SELFTEST.json", "w")); json.dump({}, open("feed_match_SELFTEST.json", "w"))
json.dump({"I10": "dcode1", "E119": "dcode2"}, open("dx.json", "w"))

# ---- stand-ins for the AMD modules (nothing here can reach AdvancedMD) -------------------------------------------------------------
POSTS = []
amd = types.ModuleType("amd")
amd.msg = lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s" class="%s">%s</ppmdmsg>' % (action, cls, children)
amd._msgtime = lambda: "t"
amd.login_cached = lambda: None
ECHO = {"flip": False, "none": False}                                  # flip: the stand-in stores 31 where 32 was sent; none: its answer carries no place of service
def _post(body, timeout=0):
    POSTS.append(body)
    if 'action="getdemographic"' in body or "getdemographic" in body: return '<r><patient respparty="resp9" insorder="1" deceased=""/></r>'
    if 'action="addvisit"' in body: return '<r><visit id="vst%d"/></r>' % len(POSTS)
    if 'action="updvisitwithnewcharges"' in body:
        sent = re.findall(r'proccode="pcode\d+" cobcode="" pos="(\d+)"', body); vid = re.search(r'<visit id="(vst\d+)"', body).group(1)
        return '<r><visit id="%s">%s</visit></r>' % (vid, "".join('<charge id="charge%d%d" fee="1.00"%s/>' % (len(POSTS), i, "" if ECHO["none"] else ' pos="%s"' % ("31" if ECHO["flip"] and q == "32" else q)) for i, q in enumerate(sent)))
    return "<r/>"
amd.post = _post
resave = types.ModuleType("resave"); resave.detail = lambda cid: '<r><visit episode="eps9" refplan=""/></r>'
CHART = {}                                                             # chart number -> [(cpt, 'MM/DD/YYYY')] the stand-in history returns
txh = types.ModuleType("txh")
def _fetch(num):
    root = ET.Element("r")
    for i, (cpt, dos) in enumerate(CHART.get(str(num), [])):
        ET.SubElement(root, "charge", {"id": "charge%d" % (i + 1), "proccode": cpt, "dos": dos, "void": "0", "fee": "1.00"})
    return root
txh.fetch = _fetch
sys.modules.update({"amd": amd, "resave": resave, "txh": txh})
spec = importlib.util.spec_from_file_location("claimocity_import", HELPER); ci = importlib.util.module_from_spec(spec); spec.loader.exec_module(ci)

# ---- 1. the visit rule, as a pure function -----------------------------------------------------------------------------------------
P = lambda cpt, dos, hist: ci.nf_visit_pos(cpt, dos, hist)[0]
K = lambda cpt, dos, hist: ci.nf_visit_kind(cpt, dos, hist)[0]
MONTHLY = [("99309", "09/05/2026"), ("99309", "10/03/2026")]
check("initial visit 99306 is 31 whatever came before", P("99306", "11/02/2026", [("99309", "09/01/2026")]) == "31" and K("99306", "11/02/2026", MONTHLY) == "initial")
check("initial visit 99304 / 99305 are 31", P("99304", "11/02/2026", []) == "31" and P("99305", "11/02/2026", []) == "31")
check("monthly visit (30 days after the last one) is 32", P("99309", "11/02/2026", MONTHLY) == "32" and K("99309", "11/02/2026", MONTHLY) == "monthly")
check("the 60-day schedule is 32", P("99309", "12/02/2026", [("99309", "10/03/2026")]) == "32")
check("twice-weekly visit (3 days after the last one) is 31, skilled", P("99309", "10/04/2026", [("99306", "10/01/2026")]) == "31" and K("99309", "10/04/2026", [("99306", "10/01/2026")]) == "skilled")
check("weekly visit (7 days after the last one) is 31", P("99310", "10/08/2026", [("99306", "10/01/2026")]) == "31")
check("14 days after the last visit is still 31", P("99309", "10/15/2026", [("99306", "10/01/2026")]) == "31")
check("15 to 20 days is neither weekly nor monthly: left at 31", [P("99309", d, [("99309", "10/01/2026"), ("99309", "09/01/2026")]) for d in ("10/16/2026", "10/21/2026")] == ["31", "31"] and K("99309", "10/16/2026", [("99309", "10/01/2026")]) == "between")
check("21 days is the first monthly gap (32), 92 the last, 93 is a new stay (31)", [P("99309", d, [("99309", "07/01/2026")]) for d in ("07/22/2026", "10/01/2026", "10/02/2026")] == ["32", "32", "31"])
check("a year since the last nursing visit is not 'the monthly visit' (31, stale)", P("99309", "10/15/2026", [("99306", "08/20/2025"), ("99309", "09/01/2025")]) == "31" and K("99309", "10/15/2026", [("99309", "09/01/2025")]) == "stale")
check("the first visit after a discharge visit is a new stay (31)", P("99309", "10/13/2026", [("99306", "09/01/2026"), ("99309", "09/04/2026"), ("99316", "09/08/2026")]) == "31" and K("99309", "10/13/2026", [("99316", "09/08/2026")]) == "discharge")
HOSP_BETWEEN = [("99309", "10/03/2026"), ("99223", "10/10/2026"), ("99232", "10/12/2026"), ("99239", "10/16/2026")]
check("the first visit back after one of our hospital visits is a new skilled stay (31)", P("99309", "10/20/2026", HOSP_BETWEEN) == "31" and K("99309", "10/20/2026", HOSP_BETWEEN) == "hospital")
check("a hospital visit BEFORE the previous nursing visit does not count", P("99309", "11/02/2026", [("99232", "09/20/2026"), ("99309", "10/03/2026")]) == "32")
check("the visits after a return from the hospital are skilled, not 'extra'", K("99309", "10/23/2026", HOSP_BETWEEN + [("99309", "10/20/2026")]) == "skilled")
check("first nursing visit on the chart is 31 (new admission)", P("99309", "10/01/2026", []) == "31" and K("99309", "10/01/2026", []) == "first")
check("first monthly visit after a skilled stay ends is 32", P("99309", "11/28/2026", [("99306", "10/01/2026"), ("99309", "10/04/2026"), ("99309", "10/29/2026")]) == "32")
check("an extra visit on a monthly resident is left at 31 and says so", P("99309", "11/05/2026", MONTHLY + [("99309", "11/02/2026")]) == "31" and K("99309", "11/05/2026", MONTHLY + [("99309", "11/02/2026")]) == "extra")
check("a visit entered out of order still reads the last EARLIER visit", P("99309", "10/08/2026", [("99306", "10/01/2026"), ("99309", "10/11/2026")]) == "31")
check("later visits never count (a 99306 after this date is ignored)", P("99309", "11/02/2026", [("99309", "10/03/2026"), ("99306", "11/20/2026")]) == "32")
check("a visit on the same day is not 'previous'", P("99309", "11/02/2026", [("99309", "11/02/2026"), ("99309", "10/03/2026")]) == "32")
check("CCM lines in the history are not visits", P("99309", "11/02/2026", [("99487", "10/30/2026"), ("99489", "10/30/2026"), ("99497", "10/20/2026"), ("99309", "10/03/2026")]) == "32")
check("one of our home / assisted-living visits since the previous nursing visit means the resident was away (31)", P("99309", "11/02/2026", [("99349", "10/20/2026"), ("99309", "10/03/2026")]) == "31" and K("99309", "11/02/2026", [("99349", "10/20/2026"), ("99309", "10/03/2026")]) == "away")
check("a home visit BEFORE the previous nursing visit does not count", P("99309", "11/02/2026", [("99349", "09/20/2026"), ("99309", "10/03/2026")]) == "32")
check("an admission visit known for the SAME day makes the day an admission day (31)", K("99309", "11/02/2026", [("99309", "10/03/2026"), ("99306", "11/02/2026")]) == "initial")
check("an initial visit that follows within two weeks keeps the visit before it at 31", K("99309", "11/02/2026", [("99309", "10/03/2026"), ("99306", "11/04/2026")]) == "preadmission" and K("99309", "11/02/2026", [("99309", "10/03/2026"), ("99306", "11/17/2026")]) == "monthly")
check("a hospital visit on the SAME date as the previous nursing visit counts as a hospital stay since", K("99309", "10/27/2026", [("99309", "10/03/2026"), ("99223", "10/03/2026")]) == "hospital")
MOVED = [("99309", "10/03/2026", "SEVEN HILLS HEALTH AND REHABILITATION CENTER CHC I")]
check("the previous nursing visit in ANOTHER building is a new admission here (31)", ci.nf_visit_kind("99309", "11/02/2026", MOVED, "fac32")[0] == "moved" and ci.nf_visit_pos("99309", "11/02/2026", MOVED, "fac32")[0] == "31")
check("the previous nursing visit in the SAME building reads as before (32)", ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026", "ASPIRE AT TALLAHASSEE")], "fac32")[0] == "monthly")
check("both facility records of the Southwood building are one building", ci.building_key("PRUITT SOUTHWOOD") == ci.building_key("OAKES SOUTHWOOD") == "fac1350" and ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026", "PRUITT SOUTHWOOD")], "fac1350")[0] == "monthly")
check("building keys: the five nursing buildings, another building keeps its own name, no name is unknown", [ci.building_key(n) for n in ("BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC", "ASPIRE AT TALLAHASSEE", "CENTRE POINTE HEALTH AND REHAB CENTER CENTRE POINT", "WESTMINSTER BERTRAND HEALTH CENTER", "OAKES SOUTHWOOD", "HCA REHAB", "", None)] == ["fac34", "fac32", "fac33", "fac58", "fac1350", "HCA REHAB", None, None])
check("when the chart gives no building name nothing is assumed (32 as before)", ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026", "")], "fac32")[0] == "monthly" and ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026")], "fac32")[0] == "monthly")
check("visits after a move are read as a stay that began with the move (skilled, not 'extra')", ci.nf_visit_kind("99309", "11/05/2026", MOVED + [("99309", "11/02/2026", "ASPIRE AT TALLAHASSEE")], "fac32")[0] == "skilled")
check("bad history rows are skipped, not fatal", P("99309", "11/02/2026", [(None, None), ("99309", ""), ("99309", "not a date"), ("99309", None), ("99309",), 7, ("99309", "10/03/2026", "x"), ("99309", "10/03/2026")]) == "32")
check("a discharge visit 99315 / 99316 is always kept at 31", [P(c, "10/20/2026", h) for c in ("99315", "99316") for h in ([("99306", "10/14/2026"), ("99309", "10/17/2026")], [("99309", "09/17/2026")], [])] == ["31"] * 6 and K("99316", "10/20/2026", [("99309", "09/17/2026")]) == "dischargeday")
check("the rule crosses a year end", P("99309", "01/02/2027", [("99306", "12/28/2026")]) == "31" and P("99309", "01/29/2027", [("99309", "12/28/2026")]) == "32")
check("the reason never carries a date", not any(re.search(r"\d{1,2}/\d{1,2}/\d{4}", ci.nf_visit_pos(c, d, h)[1]) for c, d, h in
      [("99306", "11/02/2026", []), ("99309", "11/02/2026", []), ("99309", "11/02/2026", [("99309", "10/30/2026")]), ("99309", "11/02/2026", MONTHLY), ("99309", "10/20/2026", HOSP_BETWEEN),
       ("99309", "10/13/2026", [("99316", "09/08/2026")]), ("99309", "10/15/2026", [("99309", "09/01/2025")]), ("99309", "10/16/2026", [("99309", "10/01/2026")])]))
check("32 is only ever the 'monthly' kind", [k for k, (p, _) in ci.NF_KINDS.items() if p == "32"] == ["monthly"])
check("every reason kept in the register says 'by rule' - it never states a resident's status as a fact", all(t.startswith(p + " by rule: ") for p, t in ci.NF_KINDS.values()) and not any(w in t for _, t in ci.NF_KINDS.values() for w in ("skilled", "long-term")))
check("the day limits are 14 / 21 / 92", (ci.SKILLED_GAP_DAYS, ci.MONTHLY_MIN_DAYS, ci.MONTHLY_MAX_DAYS) == (14, 21, 92))

# ---- 2. one message, every line ------------------------------------------------------------------------------------------------------
L = lambda lines, feed, nursing, hist=(): ci.pos_lines(lines, feed, nursing, hist)[0]
check("ALF CCM keeps 13", L([("99487", "10/31/2026"), ("99489", "10/31/2026")], "13", False) == ["13", "13"])
check("ALF CCM is untouched even with an admission visit on the chart", L([("99487", "10/31/2026")], "13", False, [("99306", "10/12/2026")]) == ["13"])
check("hospital lines keep 21", L([("99232", "10/31/2026")], "21", False) == ["21"])
check("nursing-building CCM is 32 on both lines", L([("99487", "10/31/2026"), ("99489", "10/31/2026")], "31", True) == ["32", "32"])
check("nursing-building CCM is 32 after ONE monthly visit that month", L([("99487", "10/31/2026")], "31", True, [("99309", "10/29/2026"), ("99309", "09/30/2026")]) == ["32"])
check("CCM with no nursing visit on the chart is 32", L([("99487", "10/31/2026")], "31", True, []) == ["32"])
check("CCM stays 31 when the resident had an admission visit that month", L([("99487", "10/31/2026"), ("99489", "10/31/2026")], "31", True, [("99306", "10/12/2026")]) == ["31", "31"])
check("CCM stays 31 when the resident was seen twice within 14 days that month", L([("99487", "10/31/2026")], "31", True, [("99309", "09/04/2026"), ("99309", "10/06/2026"), ("99309", "10/09/2026")]) == ["31"])
check("CCM stays 31 when the resident came back from the hospital that month", L([("99487", "10/31/2026")], "31", True, HOSP_BETWEEN + [("99309", "10/20/2026")]) == ["31"])
check("CCM stays 31 when one of our hospital visits falls in that month, even with no nursing visit after it", L([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99232", "10/25/2026")]) == ["31"])
check("CCM is 32 when our hospital visits were in ANOTHER month and the month's visit is monthly", L([("99487", "10/31/2026")], "31", True, [("99232", "08/10/2026"), ("99306", "08/14/2026"), ("99309", "09/01/2026"), ("99309", "10/01/2026")]) == ["32"])
check("CCM stays 31 in a month with a discharge visit", L([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99316", "10/12/2026")]) == ["31"])
check("two visit lines on ONE day in a message: any 31 keeps the whole day, and its 99497, at 31", L([("99309", "11/02/2026"), ("99306", "11/02/2026"), ("99497", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["31", "31", "31"] and L([("99497", "11/02/2026"), ("99306", "11/02/2026"), ("99309", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["31", "31", "31"])
check("CCM stays 31 when a visit that month followed one late the month before by 14 days or less", L([("99487", "10/31/2026")], "31", True, [("99309", "08/30/2026"), ("99309", "09/28/2026"), ("99309", "10/02/2026")]) == ["31"])
check("CCM is 32 when the close visits were in ANOTHER month", L([("99487", "10/31/2026")], "31", True, [("99306", "08/03/2026"), ("99309", "08/06/2026"), ("99309", "10/05/2026")]) == ["32"])
check("CCM is 32 when that month's visits are monthly or 15-20 days apart", L([("99487", "10/31/2026")], "31", True, [("99309", "09/01/2026"), ("99309", "10/01/2026"), ("99309", "10/17/2026")]) == ["32"])
_w = ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99306", "10/12/2026")])
check("a CCM line left at 31 names William, carries no date, and its kind says why", "William" in _w[1][0] and not re.search(r"\d{1,2}/\d{1,2}/\d{4}", _w[1][0]) and _w[2] == ["ccm-skilled-month"])
check("monthly visit + 99497: both 32", L([("99309", "11/02/2026"), ("99497", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["32", "32"])
check("weekly visit + 99497: both 31", L([("99309", "11/02/2026"), ("99497", "11/02/2026")], "31", True, [("99309", "10/29/2026")]) == ["31", "31"])
check("99497 listed BEFORE its visit still follows the visit", L([("99497", "11/02/2026"), ("99309", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["32", "32"])
check("99497 alone in a nursing building keeps the feed's 31", L([("99497", "11/02/2026")], "31", True) == ["31"])
check("99497 follows the visit of ITS OWN date, whatever the line order", L([("99309", "11/02/2026"), ("99309", "11/05/2026"), ("99497", "11/05/2026")], "31", True, [("99309", "10/03/2026")]) == ["32", "31", "31"]
      and L([("99497", "11/05/2026"), ("99309", "11/05/2026"), ("99309", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["31", "31", "32"])
check("99497 dated a day with no visit keeps the feed's 31", L([("99309", "11/02/2026"), ("99497", "11/03/2026")], "31", True, [("99309", "10/03/2026")]) == ["32", "31"])
check("two visit lines in one message read each other without the batch list", L([("99309", "11/02/2026"), ("99309", "11/05/2026")], "31", True, [("99309", "10/03/2026")]) == ["32", "31"])

check("one of our home / ALF visits on the previous nursing visit's OWN day also means the resident left (31, away)", K("99309", "11/02/2026", [("99309", "10/03/2026"), ("99349", "10/03/2026")]) == "away" and P("99309", "11/02/2026", [("99309", "10/03/2026"), ("99349", "10/03/2026")]) == "31")
check("a visit row that names another building for the previous visit is a move (31), the same building is not", K("99309", "11/02/2026", [("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC")]) == "monthly"
      and ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC")], "fac32")[0] == "moved" and ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026", "ASPIRE AT TALLAHASSEE")], "fac32")[0] == "monthly")
check("AdvancedMD's own facility names for the five buildings give the five building keys", [ci.building_key(n) for n in ("BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC", "ASPIRE AT TALLAHASSEE", "CENTRE POINTE HEALTH AND REHAB CENTER CENTRE POINT", "WESTMINSTER BERTRAND HEALTH CENTER", "PRUITT SOUTHWOOD")] == ["fac34", "fac32", "fac33", "fac58", "fac1350"]
      and [ci.building_key(B[k]) for k in ("n1", "n2", "n3")] == ["fac34", "fac32", "fac1350"] and ci.building_key("Centre Pointe Health And Rehab Center") == "fac33" and ci.building_key("Westminster Oaks-Bertrand Health Center") == "fac58")

# ---- 3. build(): the charge XML that would go to AMD -----------------------------------------------------------------------------------
def ctx(live=()): return {"live": set(live), "episode": "eps9", "resp": "resp9", "refplan": "", "insorder": "1", "pid": "pat9"}
def msg(fid, lines): return {"pid": fid, "name": "x", "dob": "", "FT1": [{"cpt": c, "dos": d, "dx": "I10^E119", "units": "1"} for c, d in lines]}
def built(fid, lines, live=()):
    out, info = ci.build(msg(fid, lines), ctx(live))
    if out is None: return None, info, []
    return out[1], info, re.findall(r'proccode="(pcode\d+)" cobcode="" pos="(\d+)"', out[1])
body, info, pp = built("n1", [("99487", "20261031"), ("99489", "20261031")])
check("build: Brynwood CCM goes out as 32 / 32", [p for _, p in pp] == ["32", "32"], pp)
check("build: register keeps the feed's 31 beside the 32", info["pos"] == "32" and info["pos_feed"] == "31" and info["pos_lines"] == ["32", "32"] and info["pos_kind"] == ["ccm", "ccm"] and info["pos_err"] == "" and info["fac"] == "fac34", info)
check("build: 99489 still carries modifier 25 beside 99487", 'modcodes="mcode7"' in body and body.count('modcodes=""') == 1)
check("build: fees unchanged (206.00 / 109.00)", 'fee="206.00"' in body and 'fee="109.00"' in body)
body, info, pp = built("a1", [("99487", "20261031"), ("99489", "20261031")])
check("build: ALF CCM still goes out as 13 / 13", [p for _, p in pp] == ["13", "13"] and info["pos"] == "13" and info["pos_lines"] == ["13", "13"] and info["fac"] == "fac37", (pp, info))
body, info, pp = built("h1", [("99232", "20261031")])
check("build: hospital visit still 21 with its admission date", [p for _, p in pp] == ["21"] and 'hospitalizationfrom="10/30/2026"' in body and info["pos"] == "21", (pp, info))
body, info, pp = built("h1", [("99487", "20261031")])
check("build: CCM that arrives from the hospital is NOT touched (21)", [p for _, p in pp] == ["21"], pp)
body, info, pp = built("u1", [("99487", "20261031")])
check("build: unknown building keeps the old default 31 and no facility", [p for _, p in pp] == ["31"] and info["fac"] == "" and info["pos_lines"] == ["31"] and info["pos_err"] == "", (pp, info))
body, info, pp = built("n2", [("99309", "20261102")], live=[("99309", "10/03/2026"), ("99487", "10/31/2026")])
check("build: Aspire monthly 99309 goes out as 32", [p for _, p in pp] == ["32"] and info["pos"] == "32" and info["pos_why"][0].startswith("32 by rule") and info["pos_kind"] == ["monthly"], (pp, info))
body, info, pp = built("n2", [("99309", "20261102")], live=[("99306", "10/26/2026"), ("99309", "10/29/2026")])
check("build: Aspire twice-weekly 99309 goes out as 31", [p for _, p in pp] == ["31"] and info["pos_why"][0].startswith("31 by rule") and info["pos_kind"] == ["skilled"], (pp, info))
body, info, pp = built("n2", [("99309", "20261020")], live=[("99309", "10/03/2026"), ("99232", "10/12/2026")])
check("build: back from the hospital (our 99232 on the chart) goes out as 31", [p for _, p in pp] == ["31"] and info["pos_kind"] == ["hospital"], (pp, info))
c9 = ctx(); c9["nfrows"] = {("99309", "10/03/2026", "ASPIRE AT TALLAHASSEE"), ("99232", "09/01/2026", "HCA FLORIDA CAPITAL HOSPITAL TALLAHASSEE MEDICAL C")}
out9, info9 = ci.build(msg("n2", [("99309", "20261102")]), c9)
check("build: the chart's visit rows with building names are what the rule reads (same building, monthly -> 32)", 'pos="32"' in out9[1] and info9["pos_kind"] == ["monthly"], info9)
c9 = ctx(); c9["nfrows"] = {("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC")}
out9, info9 = ci.build(msg("n2", [("99309", "20261102")]), c9)
check("build: previous nursing visit in another of the five buildings -> 31, kind moved", 'pos="31"' in out9[1] and info9["pos_kind"] == ["moved"], info9)
body, info, pp = built("n3", [("99306", "20261102")], live=[("99309", "09/01/2026")])
check("build: Oakes Southwood 99306 goes out as 31", [p for _, p in pp] == ["31"], pp)
body, info, pp = built("n2", [("99309", "20261102"), ("99497", "20261102")], live=[("99309", "10/03/2026")])
check("build: monthly visit + 99497 -> 32 / 32, modifier 25 on 99497", [p for _, p in pp] == ["32", "32"] and body.count('modcodes="mcode7"') == 1, pp)
body, info, pp = built("n2", [("99487", "20261031")], live=[("99306", "10/12/2026"), ("99309", "10/15/2026")])
check("build: CCM for a resident admitted that month stays 31 and is marked for William", [p for _, p in pp] == ["31"] and info["pos_kind"] == ["ccm-skilled-month"] and info["pos_err"] == "", (pp, info))
ci.BATCH_NF.clear(); ci.BATCH_NF["pat9"] = {("99306", "10/30/2026")}
body, info, pp = built("n2", [("99309", "20261102")], live=[("99309", "10/03/2026")])
check("build: a visit elsewhere in the SAME batch counts as history (31)", [p for _, p in pp] == ["31"], (pp, info))
ci.BATCH_NF.clear()
out, why, pp = built("n2", [("99309", "20261102")], live=[("99309", "11/02/2026")])
check("build: dedupe is as before (line already on the chart is skipped)", out is None and why == "all lines already in AMD", why)
out, why, pp = built("n2", [("99999", "20261102")])
check("build: unknown CPT is refused as before", out is None and why.startswith("unknown CPT"), why)
ci.FACS["n2"] = {"Aspire of Tallahassee", "HCA Florida Capital Hospital"}
body, info, pp = built("n2", [("99487", "20261031")])
check("build: two buildings and a message the raw files cannot answer: entered as before (31) and reported", [p for _, p in pp] == ["31"] and "2 buildings" in info["pos_err"] and info["pos_lines"] == ["31"] and info["msg_own"] is False, (pp, info))
ci.FACS["n2"] = {"Aspire of Tallahassee"}
ci.FACS["a1"] = {"Azalea Gardens ALF", "Aspire of Tallahassee"}
body, info, pp = built("a1", [("99487", "20261031")])
check("build: two buildings, the message's OWN building known (the ALF): entered there (13), nothing to report", [p for _, p in pp] == ["13"] and info["pos_err"] == "" and info["msg_own"] is True and info["fac"] == "fac37", (pp, info))
body, info, pp = built("a1", [("99487", "20261130")])
check("build: two buildings, one of them a nursing building, own building NOT readable, the ALF read last: what is sent is unchanged (13) and the visit is reported", [p for _, p in pp] == ["13"] and "2 buildings" in info["pos_err"] and info["msg_own"] is False, (pp, info))
ci.FACS["a1"] = {"Azalea Gardens ALF"}
# every visit from ITS OWN message: clinician, building, admission date
_, i_np, pp_np = built("m1", [("99309", "20261102")], live=[("99309", "10/03/2026")]); _, i_md, pp_md = built("m1", [("99487", "20261031"), ("99489", "20261031")])
check("build: the nurse practitioner's visit stays hers although the physician's CCM for the same resident was read last", i_np["prof"] == "prof15" and i_np["msg_own"] is True and [q for _, q in pp_np] == ["32"], i_np)
check("build: and the CCM stays the physician's, 32 / 32", i_md["prof"] == "prof13" and [q for _, q in pp_md] == ["32", "32"], i_md)
check("build: (the per-patient value alone would have named one clinician for both)", ci.NPIOF["m1"] == NPI and ci.msg_own(msg("m1", [("99309", "20261102")]))[1] == NP_NPI)
b_h, i_h, pp_h = built("m2", [("99232", "20261020")]); b_a, i_a, pp_a = built("m2", [("99306", "20261022")]); b_f, i_f, pp_f = built("m2", [("99309", "20261025")], live=[("99306", "10/22/2026")])
check("build: hospital message of a patient who also has nursing messages: hospital facility, 21, its own admission date, the physician", i_h["fac"] == "fac29" and [q for _, q in pp_h] == ["21"] and 'hospitalizationfrom="10/18/2026"' in b_h and i_h["prof"] == "prof13" and i_h["pos_err"] == "", i_h)
check("build: that patient's nursing messages: the nursing building, 31 (admission, then weekly), each under its own clinician, no admission date carried over", i_a["fac"] == "fac32" and i_f["fac"] == "fac32" and [q for _, q in pp_a + pp_f] == ["31", "31"] and (i_a["prof"], i_f["prof"]) == ("prof13", "prof15")
      and i_a["admit"] == "" and "hospitalizationfrom" not in b_a and i_a["pos_err"] == i_f["pos_err"] == "" and i_f["pos_kind"] == ["skilled"], (i_a, i_f))
body, info, pp = built("m3", [("99487", "20261031")])
check("build: the same lines sent from two buildings have no single answer: the last-read building is used as before and the visit is reported", info["msg_own"] is False and "2 buildings" in info["pos_err"] and [q for _, q in pp] == ["13"], (pp, info))
check("seen_lines: the visit lines of a message that is not entered, with its building, for the register", ci.seen_lines(msg("m2", [("99232", "20261020")])) == [["99232", "10/20/2026", B["h1"]]] and ci.seen_lines(msg("n1", [("99487", "20261031")])) == [])
_real = ci.nf_visit_kind
ci.nf_visit_kind = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
body, info, pp = built("n2", [("99309", "20261102")], live=[("99309", "10/03/2026")])
check("build: a failure in the rule falls back to the feed's 31 and says so", [p for _, p in pp] == ["31"] and info["pos_err"] == "boom" and info["pos_lines"] == ["31"] and info["pos_why"] == ["rule error"], (pp, info))
ci.nf_visit_kind = lambda *a, **k: (_ for _ in ()).throw(ValueError())
body, info, pp = built("n2", [("99309", "20261102")], live=[("99309", "10/03/2026")])
check("build: an error with no text is still reported", [p for _, p in pp] == ["31"] and info["pos_err"] == "ValueError", (pp, info))
ci.nf_visit_kind = _real
_realpl = ci.pos_lines
ci.pos_lines = lambda cd, fp, n, h: (["11"] * len(cd), [""] * len(cd), [""] * len(cd))
body, info, pp = built("n2", [("99309", "20261102")], live=[("99309", "10/03/2026")])
check("build: an impossible place of service from the rule is refused (31, reported)", [p for _, p in pp] == ["31"] and info["pos_err"] != "", (pp, info))
ci.pos_lines = _realpl
body, info, pp = built("a1", [("99487", "20261031")], live=[(None, None), ("x",), 7])
check("build: odd rows in the chart history cannot touch an ALF message", [p for _, p in pp] == ["13"] and info["pos_err"] == "", (pp, info))

# ---- 4. main() --dry over a small batch: the batch's own visits are read, counters print, nothing is posted but reads --------------------
NAME = lambda k: "zz test " + k                                         # not a person: the match key the ingest builds is name|dob
DOBK = "1900" + "0101"
ci.PARSED[:] = [
    {"pid": "n1", "name": NAME("one"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99487", "dos": "20261031", "dx": "I10", "units": "1"}, {"cpt": "99489", "dos": "20261031", "dx": "I10", "units": "1"}]},
    {"pid": "n2", "name": NAME("two"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99309", "dos": "20261102", "dx": "I10", "units": "1"}]},
    {"pid": "n2", "name": NAME("two"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99309", "dos": "20261105", "dx": "I10", "units": "1"}]},
    {"pid": "n3", "name": NAME("three"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99306", "dos": "20261103", "dx": "I10", "units": "1"}]},
    {"pid": "a1", "name": NAME("four"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99487", "dos": "20261031", "dx": "I10", "units": "1"}]},
    {"pid": "u1", "name": NAME("five"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99487", "dos": "20261031", "dx": "I10", "units": "1"}]},
]
ci.MATCH.clear()
for k, pid in (("one", "pat101"), ("two", "pat102"), ("three", "pat103"), ("four", "pat104"), ("five", "pat105")):
    ci.MATCH[NAME(k).upper().strip() + "|" + DOBK] = {"resolved": pid}
CHART.update({"102": [("99309", "10/03/2026")], "101": [], "103": [], "104": [], "105": []})
def run_dry():
    POSTS.clear(); buf = io.StringIO(); argv = sys.argv[:]; sys.argv = ["claimocity_import.py", "--dry"]; ci.BATCH_NF.clear(); ci.BATCH_NF_ERR[0] = ""; ci._ctx.clear()
    with contextlib.redirect_stdout(buf): ci.main()
    sys.argv = argv; out = buf.getvalue(); dry = {}
    for ln in out.splitlines():
        m = re.match(r"DRY (pat\d+) (\{.*\})$", ln)
        if m: dry.setdefault(m.group(1), []).append(eval(m.group(2)))      # the helper prints its own dict; this is its own output, no outside data
    return out, dry
out, dry = run_dry()
check("main --dry: six messages reach build", sum(len(v) for v in dry.values()) == 6, out[-600:])
check("main --dry: nursing CCM 32/32, ALF CCM 13", dry.get("pat101", [{}])[0].get("pos_lines") == ["32", "32"] and dry.get("pat104", [{}])[0].get("pos_lines") == ["13"], dry)
p102 = sorted(dry.get("pat102", []), key=lambda d: d["dos"])
check("main --dry: monthly visit 32, then the extra visit 3 days later in the same batch left at 31", [d["pos_lines"] for d in p102] == [["32"], ["31"]] and p102[1]["pos_kind"] == ["extra"], p102)
check("main --dry: 99306 is 31", dry.get("pat103", [{}])[0].get("pos_lines") == ["31"], dry.get("pat103"))
last3 = out.strip().splitlines()[-3:]
check("main --dry: one short POS RULE line sits within the last three log lines", any(l.startswith("POS RULE: CCM 32 x2, CCM 31 x0, visits 32 x1, visits 31 x2, not applied x0, unknown bldg x1") for l in last3) and len(next(l for l in last3 if l.startswith("POS RULE:"))) <= 110, last3)
check("main --dry: every message was matched to its own raw message (no fallback, no check line)", "not matched to its own" not in out and all(d.get("msg_own") is True for v in dry.values() for d in v), out[-300:])
check("main --dry: the DONE counters name the rule's results", all(k in out for k in ("POS 32 CCM (nursing building)", "POS 32 nursing visit (monthly)", "POS 31 nursing visit (weekly, admission or new stay)", "POS 31 nursing visit (kept at 31", "POS RULE: building not in the facility table")) and "POS RULE NOT APPLIED" not in out, out[-500:])
check("main --dry: nothing but reads was sent (no addvisit / updvisitwithnewcharges)", not any("addvisit" in b or "updvisitwithnewcharges" in b for b in POSTS), len(POSTS))
check("main --dry: no import register is written", not os.path.exists(os.path.join(tmp, "registers", "feed_import_SELFTEST.json")))
ci.PARSED.append({"pid": "n3", "name": NAME("six"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99309", "dos": "20261104", "dx": "I10", "units": "1"}]})
ci.MATCH[NAME("six").upper().strip() + "|" + DOBK] = {"resolved": ["not", "a", "chart"]}      # a match row the batch list cannot use
out, dry = run_dry(); ci.PARSED.pop(); del ci.MATCH[NAME("six").upper().strip() + "|" + DOBK]
check("main --dry: when the batch visit list cannot be built it is emptied, said and counted - and the run goes on", "batch visit list not built" in out and "POS RULE: batch visit list not built - nursing-building lines kept at the feed's 31" in out and ci.BATCH_NF == {} and "DONE" in out, out[-400:])
check("main --dry: ... and then NO nursing-building line is 32: each is kept at the feed's 31 and reported", all(d["pos_lines"] == ["31"] * len(d["cpts"]) and d["pos_err"] for k in ("pat101", "pat102", "pat103") for d in dry.get(k, [])) and "not applied x4" in out and dry.get("pat104", [{}])[0].get("pos_lines") == ["13"], dry)
ci.BATCH_NF_ERR[0] = ""
_regp = os.path.join(tmp, "registers", "feed_import_SELFTEST.json")       # the broken match row above made the run write a 'failed' row whose chart is a list
check("an odd row left in a register by a failed message (its chart not a chart number) is there for the next check", os.path.exists(_regp) and isinstance(json.load(open(_regp))["failed"][0]["pid"], list))
out, dry = run_dry()
check("main --dry: an odd row in an earlier register never switches the rule off for the next run", "batch visit list not built" not in out and dry.get("pat101", [{}])[0].get("pos_lines") == ["32", "32"] and "not applied x0" in out, out[-300:])
os.remove(_regp)

# ---- 4b. batches where one patient has two clinicians / two buildings, visits earlier batches could not enter, and live runs ---------------
def P_(fid, k, lines): return {"pid": fid, "name": NAME(k), "dob": DOBK, "file": "f", "FT1": [{"cpt": c, "dos": d, "dx": "I10", "units": "1"} for c, d in lines]}
BASE = ci.PARSED[:]
for k, pid in (("m1", "pat301"), ("m2", "pat302"), ("m4", "pat304"), ("m5", "pat305"), ("s1", "pat201")): ci.MATCH[NAME(k).upper().strip() + "|" + DOBK] = {"resolved": pid}
CHART.update({"301": [("99309", "09/05/2026"), ("99309", "10/03/2026")], "302": [], "304": [], "305": [("99309", "12/20/2026")], "201": [("99306", "10/20/2026")]})
M1 = [P_("m1", "m1", [("99309", "20261102")]), P_("m1", "m1", [("99487", "20261031"), ("99489", "20261031")])]
M2 = [P_("m2", "m2", [("99232", "20261020")]), P_("m2", "m2", [("99306", "20261022")]), P_("m2", "m2", [("99309", "20261025")])]
M4 = [P_("m4", "m4", [("99309", "20261001")]), P_("m4", "m4", [("99309", "20261025")])]
ci.PARSED[:] = M1 + M2 + M4
out, dry = run_dry()
d301 = {tuple(d["cpts"]): d for d in dry.get("pat301", [])}; d302 = {tuple(d["cpts"]): d for d in dry.get("pat302", [])}; d304 = sorted(dry.get("pat304", []), key=lambda d: d["dos"])
check("main --dry: one resident, two clinicians in the batch - each visit under its own (visit prof15 / 32, CCM prof13 / 32)", d301.get(("99309",), {}).get("prof") == "prof15" and d301.get(("99487", "99489"), {}).get("prof") == "prof13" and d301[("99309",)]["pos_lines"] == ["32"] and d301[("99487", "99489")]["pos_lines"] == ["32", "32"], d301)
check("main --dry: hospital, then nursing building, in one batch - each visit in its own building, the nursing visits 31, nothing 'not applied'", d302.get(("99232",), {}).get("fac") == "fac29" and d302[("99232",)]["pos_lines"] == ["21"] and d302.get(("99306",), {}).get("fac") == "fac32" and d302[("99306",)]["pos_kind"] == ["initial"]
      and d302.get(("99309",), {}).get("pos_kind") == ["skilled"] and d302[("99309",)]["prof"] == "prof15" and "not applied x0" in out, (d302, out[-300:]))
check("main --dry: a visit in another nursing building earlier in the SAME batch is a move, not the monthly visit (31), and has its own counter", [d["pos_kind"] for d in d304] == [["first"], ["moved"]] and [d["fac"] for d in d304] == ["fac34", "fac32"] and "POS 31 nursing visit (previous nursing visit in another building)" in out, (d304, out[-400:]))
ci.PARSED[:] = [P_("s1", "s1", [("99309", "20261113")])]
out, dry = run_dry()
check("main --dry: (without the earlier batches' refused visits the chart alone reads as monthly - 32)", dry.get("pat201", [{}])[0].get("pos_lines") == ["32"], dry)
json.dump({"created": [], "failed": [], "skipped": [{"feed_id": "s1", "pid": "pat201", "why": "unknown CPT 99310", "lines": [["99310", d, B["n2"]]]} for d in ("10/27/2026", "11/03/2026", "11/10/2026")]},
          open(os.path.join(tmp, "registers", "feed_import_20261111T0000Z.json"), "w"))
out, dry = run_dry()
check("main --dry: visits an EARLIER batch could not enter are still read: the visit three days after them is weekly (31)", dry.get("pat201", [{}])[0].get("pos_lines") == ["31"] and dry["pat201"][0]["pos_kind"] == ["skilled"], dry)
os.remove(os.path.join(tmp, "registers", "feed_import_20261111T0000Z.json"))
ci.PARSED[:] = [P_("n2", "two", [("99310", "20261102")])]
out, dry = run_dry()
check("main --dry: a refused message is said as before", "skip: unknown CPT 99310" in out, out[-300:])
def run_live(parsed, flip=False, none=False):
    ci.PARSED[:] = parsed; ECHO.update(flip=flip, none=none); POSTS.clear(); buf = io.StringIO(); argv = sys.argv[:]; sys.argv = ["claimocity_import.py", "--all"]
    ci.BATCH_NF.clear(); ci.BATCH_NF_ERR[0] = ""; ci._ctx.clear(); regp = os.path.join(tmp, "registers", "feed_import_SELFTEST.json"); _sleep = ci.time.sleep; ci.time.sleep = lambda s: None
    try:
        with contextlib.redirect_stdout(buf): ci.main()
    finally: ci.time.sleep = _sleep; sys.argv = argv; ECHO.update(flip=False, none=False)
    reg = json.load(open(regp)); os.remove(regp)
    return buf.getvalue(), reg
out, reg = run_live(M1 + M2 + [P_("n2", "two", [("99310", "20261102")])])
by = {(r["pid"], tuple(r["cpts"])): r for r in reg["created"]}
check("live run: five visits created, each under its own clinician, in its own building", len(reg["created"]) == 5 and by[("pat301", ("99309",))]["prof"] == "prof15" and by[("pat301", ("99487", "99489"))]["prof"] == "prof13"
      and by[("pat302", ("99232",))]["fac"] == "fac29" and by[("pat302", ("99309",))]["fac"] == "fac32" and by[("pat302", ("99309",))]["prof"] == "prof15", reg["created"])
check("live run: the profile sent to AdvancedMD is the message's own", sum(1 for b in POSTS if 'action="addvisit"' in b and 'profile="prof15"' in b) == 2 and sum(1 for b in POSTS if 'action="addvisit"' in b and 'profile="prof13"' in b) == 3, [b[:160] for b in POSTS if "addvisit" in b])
check("live run: what AdvancedMD stored is read back and matches what was sent", all(r["pos_stored"] == r["pos_lines"] for r in reg["created"]) and "POS NOT KEPT" not in out and "POS CHECK" not in out, out[-400:])
check("live run: the refused message leaves its visit line in the register for later batches", [r.get("lines") for r in reg["skipped"]] == [[["99310", "11/02/2026", B["n2"]]]], reg["skipped"])
out, reg = run_live(M1, flip=True)
last3 = out.strip().splitlines()[-3:]
check("live run: AdvancedMD storing 31 where 32 was sent is said per visit, counted, and shown in a short line within the last three", out.count("POS NOT KEPT") == 2 and any(l.startswith("POS CHECK: AdvancedMD stored another place of service x2; not matched to its own message x0") and len(l) <= 110 for l in last3)
      and any(l.startswith("POS RULE:") for l in last3) and all(r["pos_stored"] != r["pos_lines"] for r in reg["created"]), last3)
out, reg = run_live(M1, none=True)
check("live run: an answer without the place of service claims nothing either way", all(r["pos_stored"] is None for r in reg["created"]) and "POS NOT KEPT" not in out, reg["created"])
out, reg = run_live([P_("m5", "m5", [("99498", "20270121"), ("99309", "20270120")]), P_("m5", "m5", [("99306", "20270121")])])
check("live run: a message with two dates is remembered line by line - the admission visit of the later date is still entered", len(reg["created"]) == 2 and reg["created"][0]["dos_lines"] == ["01/21/2027", "01/20/2027"] and reg["created"][1]["cpts"] == ["99306"] and reg["skipped"] == [], (reg["created"], reg["skipped"]))
ci.PARSED[:] = BASE

# ---- 5. the mirror keeps these helpers: a workspace copy without the rule never overwrites the repository's ------------------------------
mir = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
for helper in ("claimocity_import.py", "claimocity_report.py", "claimocity_inspector.py"):
    m = re.search(r'"%s":\s*(?:"([^"]+)"|\'([^\']+)\')' % re.escape(helper), mir); m = m and type("M", (), {"group": lambda self, i, _m=m: _m.group(1) or _m.group(2)})()
    check("mirror.py protects %s with a marker that is in the file" % helper, bool(m) and m.group(1) in open(os.path.join(ROOT, "scripts", "helpers", helper)).read(), m.group(1) if m else "no PROTECTED entry")
insp = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read()
check("inspector: a CCM visit at the hospital location is never moved to HCA REHAB / 31", 'all(x not in HOSP for x in c["cpts"]) and not any(x in ("99487", "99489") for x in c["cpts"])' in insp)
step = open(os.path.join(ROOT, "nightly", "claimocity_feed_step.md")).read()
ver = 'POS_RULE_VERSION = "%s"' % ci.POS_RULE_VERSION
ingest = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_ingest.py")).read()
check("the rule's version line is the same in the helper, mirror.py, the ingest guard and the runbook's step (c)", ver in open(HELPER).read() and ver in mir and ver in ingest and ("grep -c '%s' /home/claude/unbilled/claimocity_import.py" % ver) in step, ver)
check("runbook: the feed step copies the helpers and checks the version line before the ingest", step.index("claimocity_retry_dx.py /home/claude/unbilled/") < step.index("must print 1") < step.index("python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run drops --live)"))
check("ingest: the guard replaces an old import helper with the repository's before step 5", ingest.index("POS_RULE = ") < ingest.index('cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py")') and "claimocity_inspector.py" in ingest[ingest.index("POS_RULE = "):ingest.index('cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py")')])
retry = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_retry_dx.py")).read()
check("retry: every batch's feed files go into one folder, and a batch without files waits (never entered without a building)", "never entered without a building" in retry and 'env["FEED_HL7_DIR"] = os.path.abspath(hdir)' in retry)

# ---- 6. the feed digest says what the rule did (claimocity_report.py over a made-up import register) ---------------------------------------
import subprocess
rep_dir = tempfile.mkdtemp(prefix="posrule_rep_"); os.makedirs(os.path.join(rep_dir, "registers"))
def reg_row(cpts, fac, feed, lines, kinds=None, err=""):
    return {"feed_id": "x", "pid": "pat9", "visit": "vst1", "charges": ["charge%d" % i for i in range(len(cpts))], "fees": ["1.00"] * len(cpts), "dos": "11/02/2026",
            "cpts": cpts, "fac": fac, "pos": lines[0], "pos_feed": feed, "pos_lines": lines, "pos_why": [""] * len(cpts), "pos_kind": kinds or [""] * len(cpts), "pos_err": err}
OLD_ROW = {"feed_id": "y", "pid": "pat8", "visit": "vst2", "charges": ["charge9"], "fees": ["1.00"], "dos": "10/01/2026", "cpts": ["99309"], "fac": "fac34", "pos": "31"}   # a row written by the helper from before the rule
rows = [reg_row(["99487", "99489"], "fac34", "31", ["32", "32"], ["ccm", "ccm"]), reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]),
        reg_row(["99309", "99497"], "fac32", "31", ["31", "31"], ["skilled", "with-visit"]), reg_row(["99306"], "fac33", "31", ["31"], ["initial"]),
        reg_row(["99487"], "fac37", "13", ["13"]), reg_row(["99232"], "fac29", "21", ["21"])]
def digest(rows, stamp="20261110T1319Z"):
    json.dump({"created": rows, "skipped": [], "failed": []}, open(os.path.join(rep_dir, "registers", "feed_import_%s.json" % stamp), "w"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")], cwd=rep_dir, env=dict(os.environ, FEED_STAMP=stamp), capture_output=True, text=True)
    return r, next((l for l in r.stdout.splitlines() if "Place of service in the nursing buildings" in l), "")
r, line = digest(rows)
check("digest: the report still runs with the new register fields", r.returncode == 0, r.stderr[-300:])
check("digest: one line - CCM 32 x2, visits 32 x1, visits 31 x2, nothing else", "CCM lines entered as 32: 2;" in line and "nursing visits 32 (monthly): 1;" in line and line.rstrip().endswith("nursing visits 31: 2."), line)
r, line = digest(rows + [reg_row(["99487", "99489"], "fac32", "31", ["31", "31"], ["ccm-skilled-month"] * 2), reg_row(["99309"], "fac32", "31", ["31"], ["extra"])])
check("digest: CCM lines and visits left at 31 are counted and explained", "CCM lines entered as 32: 2 (and 2 kept at 31 because the chart shows weekly visits, an admission or a new stay that month" in line and "nursing visits 31: 3 (1 of them kept at 31 because the chart shows neither pattern" in line, line)
check("digest: ... it says they go out at 31 unless William acts, and names the charts", "not held: they go out at 31 with the next claim run unless William changes them first" in line and "for William, not held - CCM kept at 31 (pos_kind ccm-skilled-month): pat9 11/02/2026 99487+99489" in r.stdout
      and "for William, not held - visits kept at 31, neither pattern shown (pos_kind extra / between): pat9 11/02/2026 99309" in r.stdout, r.stdout[-900:])
r, line = digest(rows + [reg_row(["99487"], "fac34", "31", ["31"], err="boom"), reg_row(["99487", "99309"], "", "31", ["31", "31"])])
check("digest: a visit the rule could not be applied to, and lines from an unknown building, are named", "POS RULE NOT APPLIED on 1 visit(s) - entered at the feed's place of service" in line and "2 CCM / nursing-visit line(s) came from a building the facility table does not know" in line, line)
check("digest: ... with their chart numbers for the top of the report", "TOP OF THE REPORT - rule not applied, check by hand before the claim run: pat9 11/02/2026 99487 (boom)" in r.stdout and "TOP OF THE REPORT - building the facility table does not know: pat9 11/02/2026 99487+99309" in r.stdout, r.stdout[-900:])
r, line = digest(rows + [dict(reg_row(["99309"], "fac32", "31", ["31"], ["moved"]))])
check("digest: visits kept at 31 because the previous visit was in another building are counted apart", "nursing visits 31: 3 (1 of them because the previous nursing visit was in another building)" in line, line)
r, line = digest([dict(x, pos_stored=list(x["pos_lines"])) for x in rows])
check("digest: says when AdvancedMD's own answer shows the place of service as sent", "AdvancedMD's own answer shows the place of service as sent on all 6 visit(s) it echoed." in r.stdout, r.stdout[-600:])
r, line = digest([dict(rows[0], pos_stored=["31", "31"])] + rows[1:])
check("digest: says loudly when AdvancedMD stored another place of service", "TOP OF THE REPORT - ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE on 1 of 1 visit(s) read back:" in r.stdout and "sent ['32', '32'] stored ['31', '31']" in r.stdout, r.stdout[-600:])
r, line = digest(rows)
check("digest: asks for one read-back by hand when the answer did not echo the place of service", "read ONE 32 line back by hand" in r.stdout, r.stdout[-600:])
r, line = digest(rows + [dict(reg_row(["99232"], "fac29", "21", ["21"]), msg_own=False)])
check("digest: a visit that could not be matched to its own feed message is named for a check of clinician and building", "Clinician and building: 1 visit(s) could not be matched to their own feed message" in r.stdout and "charts: pat9 11/02/2026 99232" in r.stdout, r.stdout[-600:])
r, line = digest(rows + [OLD_ROW])
check("digest: from 11/10/2026 on, a nursing-building row without the rule's fields means an old helper ran - said loudly", "PLACE OF SERVICE RULE DID NOT RUN on 1 visit(s)" in line, line)
r, line = digest([OLD_ROW, rows[4], rows[5]], stamp="20261028T0623Z")
check("digest: a batch from before the rule gets no line", r.returncode == 0 and line == "", r.stdout[-300:])
r, line = digest([rows[4], rows[5]])
check("digest: no line when the batch had no nursing-building charge", r.returncode == 0 and line == "", r.stdout[-300:])
r, line = digest(rows + [dict(reg_row(["99487"], "fac34", "31", ["32"]), pos_lines=[None]), dict(reg_row(["99309"], "fac34", "31", ["32"]), pos_lines=[32], pos_kind=None), dict(reg_row(["99309", "99497"], "fac34", "31", ["32"]), pos_kind=["monthly"])])
check("digest: odd values in a register never stop the report", r.returncode == 0 and line != "", r.stderr[-300:])

print("\n%d check(s) failed" % len(FAILS) if FAILS else "\nall checks passed")
sys.exit(1 if FAILS else 0)
