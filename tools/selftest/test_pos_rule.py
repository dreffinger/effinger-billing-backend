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
#     - any failure inside the rule falls back to the feed's place of service and is reported - the import carries on;
#     - the building, the rendering provider and the hospital admission date are taken from EACH feed message, not from the last message
#       read for the feed patient (section 7): a nursing-building CCM and a hospital visit of one patient in one batch are entered under
#       the nursing building (32 by the rule) and under the hospital (21); an assisted-living CCM and a nursing visit under 13 and the
#       nursing building. A message that cannot be matched to its own building (the same patient + date + codes under two buildings,
#       or a message that is not in the batch's files) keeps the patient-level building; when that patient has two buildings it is
#       reported and, in a nursing building, entered at the feed's place of service. A nursing visit earlier in the SAME batch counts
#       with the building it was sent from: after one in another building the visit is a new admission (31), never "the monthly
#       visit". Patients whose messages agree send byte-identical requests before and after;
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
def hl7(fid, fac, admit=""):
    pv1 = ["PV1", "1", "I", "", "", "", "", NPI + "^x"] + [""] * 36 + [admit]
    return "MSH|^~\\&|feed|" + fac + "|x|x|20261102||DFT^P03|1|P|2.3\rPID|1||" + fid + "\r" + "|".join(pv1) + "\r"
open(os.path.join(tmp, "hl7", "a.hl7"), "w").write("".join(hl7(k, v, "20261030" if k == "h1" else "") for k, v in BUILDING.items()))
json.dump([], open("feed_parsed_SELFTEST.json", "w")); json.dump({}, open("feed_match_SELFTEST.json", "w"))
json.dump({"I10": "dcode1", "E119": "dcode2"}, open("dx.json", "w"))

# ---- stand-ins for the AMD modules (nothing here can reach AdvancedMD) -------------------------------------------------------------
POSTS = []
amd = types.ModuleType("amd")
amd.msg = lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s" class="%s">%s</ppmdmsg>' % (action, cls, children)
amd._msgtime = lambda: "t"
amd.login_cached = lambda: None
def _post(body, timeout=0):
    POSTS.append(body)
    if 'action="getdemographic"' in body or "getdemographic" in body: return '<r><patient respparty="resp9" insorder="1" deceased=""/></r>'
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
check("build: a message that cannot be matched to its own building, of a feed patient with two buildings, is entered as before (31) and reported", [p for _, p in pp] == ["31"] and "2 buildings" in info["pos_err"] and info["pos_lines"] == ["31"]
      and "2 buildings" in info.get("site_unresolved", ""), (pp, info))
ci.FACS["n2"] = {"Aspire of Tallahassee"}
ci.FACS["a1"] = {"Azalea Gardens ALF", "Aspire of Tallahassee"}
body, info, pp = built("a1", [("99487", "20261031")])
check("build: the two-building guard never touches a non-nursing message (the unmatched building is still reported)", [p for _, p in pp] == ["13"] and info["pos_err"] == "" and "2 buildings" in info.get("site_unresolved", ""), (pp, info))
ci.FACS["a1"] = {"Azalea Gardens ALF"}
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
check("main --dry: one short POS RULE line sits within the last three log lines", any(l.startswith("POS RULE: CCM 32 x2, CCM left 31 x0, visits 32 x1, visits 31 x2, not applied x0, unknown building x1") for l in last3) and len(next(l for l in last3 if l.startswith("POS RULE:"))) <= 110, last3)
check("main --dry: the DONE counters name the rule's results", all(k in out for k in ("POS 32 CCM (nursing building)", "POS 32 nursing visit (monthly)", "POS 31 nursing visit (weekly, admission or new stay)", "POS 31 nursing visit (kept at 31", "POS RULE: building not in the facility table")) and "POS RULE NOT APPLIED" not in out, out[-500:])
check("main --dry: nothing but reads was sent (no addvisit / updvisitwithnewcharges)", not any("addvisit" in b or "updvisitwithnewcharges" in b for b in POSTS), len(POSTS))
check("main --dry: no import register is written", not os.path.exists(os.path.join(tmp, "registers", "feed_import_SELFTEST.json")))
ci.PARSED.append({"pid": "n3", "name": NAME("six"), "dob": DOBK, "file": "f", "FT1": [{"cpt": "99309", "dos": "20261104", "dx": "I10", "units": "1"}]})
ci.MATCH[NAME("six").upper().strip() + "|" + DOBK] = {"resolved": ["not", "a", "chart"]}      # a match row the batch list cannot use
out, dry = run_dry(); ci.PARSED.pop(); del ci.MATCH[NAME("six").upper().strip() + "|" + DOBK]
check("main --dry: when the batch visit list cannot be built it is emptied, said and counted - and the run goes on", "batch visit list not built" in out and "POS RULE: batch visit list not built - chart history alone used" in out and ci.BATCH_NF == {} and "DONE" in out, out[-400:])
ci.BATCH_NF_ERR[0] = ""

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
r, line = digest(rows + [reg_row(["99487"], "fac34", "31", ["31"], err="boom"), reg_row(["99487", "99309"], "", "31", ["31", "31"])])
check("digest: a visit the rule could not be applied to, and lines from an unknown building, are named", "POS RULE NOT APPLIED on 1 visit(s) - entered at the feed's place of service" in line and "2 CCM / nursing-visit line(s) came from a building the facility table does not know" in line, line)
r, line = digest(rows + [OLD_ROW])
check("digest: from 11/10/2026 on, a nursing-building row without the rule's fields means an old helper ran - said loudly", "PLACE OF SERVICE RULE DID NOT RUN on 1 visit(s)" in line, line)
r, line = digest([OLD_ROW, rows[4], rows[5]], stamp="20261028T0623Z")
check("digest: a batch from before the rule gets no line", r.returncode == 0 and line == "", r.stdout[-300:])
r, line = digest([rows[4], rows[5]])
check("digest: no line when the batch had no nursing-building charge", r.returncode == 0 and line == "", r.stdout[-300:])
r, line = digest(rows + [dict(reg_row(["99487"], "fac34", "31", ["32"]), pos_lines=[None]), dict(reg_row(["99309"], "fac34", "31", ["32"]), pos_lines=[32], pos_kind=None), dict(reg_row(["99309", "99497"], "fac34", "31", ["32"]), pos_kind=["monthly"])])
check("digest: odd values in a register never stop the report", r.returncode == 0 and line != "", r.stderr[-300:])
AMB = "same patient, date and codes under 2 buildings in this batch - the patient-level building, provider and admission date were used"
r, line = digest([rows[5], dict(reg_row(["99487"], "fac37", "13", ["13"]), site_unresolved=AMB)])
check("digest: a visit whose building is uncertain is named even when no nursing building is involved", r.returncode == 0 and "BUILDING AMBIGUOUS on 1 visit(s)" in line and "POS RULE NOT APPLIED" not in line, line or r.stdout[-300:])
r, line = digest(rows + [dict(reg_row(["99487"], "fac34", "31", ["31"], err=AMB), site_unresolved=AMB), dict(reg_row(["99487"], "fac37", "13", ["13"]), site_unresolved=AMB)])
check("digest: ... in a nursing building it is counted as POS RULE NOT APPLIED too", "POS RULE NOT APPLIED on 1 visit(s)" in line and "BUILDING AMBIGUOUS on 2 visit(s)" in line and "CCM lines entered as 32: 2" in line, line)

# ---- 7. building, provider and admission date per MESSAGE (11/10/2026): two buildings, one feed patient ---------------------------------
# Until now the importer kept the three per feed PATIENT (PID-3) and the last message read won, so a patient with messages from two
# buildings in one batch had every visit entered under ONE building (care management at the hospital with place of service 21, a nursing
# visit at an assisted-living facility, a hospital visit dated from the nursing home's admission) and the rule above stepped aside for
# every nursing-building message of such a patient. This section runs whole batches: invented messages are written as HL7 files, parsed
# by the real feed_parse_dft_1028.py (so the message key the importer builds from the raw files is proven against the entries of
# feed_parsed_<stamp>.json) and entered by a fresh copy of the importer through stand-ins that answer like AMD. The buildings, clinician
# keys, procedure ids and fees are invented and replace the importer's tables after loading: master data is not under test here, and a
# fee-schedule or facility-table edit never moves the fingerprints of 7F.
def per_message_cases():
    import atexit, shutil, socket, hashlib, datetime
    def no_network(*a, **k): raise AssertionError("network use in an offline self-test")
    socket.socket = no_network; socket.create_connection = no_network
    os.environ.pop("DECEASED_CACHE", None)                                # a run shell's own cache must never decide what these invented charts get
    sys.dont_write_bytecode = True
    PARSER = os.path.join(ROOT, "scripts", "helpers", "feed_parse_dft_1028.py")
    TMP = tempfile.mkdtemp(prefix="posrule_site_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
    STAMP = "20261110T0000Z"; MSGTIME = "11/10/2026 1:00:00 AM"
    SENT = []; N = {"visit": 0, "charge": 0, "login": 0}; LIVE = {}      # LIVE: chart number -> [(CPT, mm/dd/yyyy)] already on that chart
    def s_msg(action, cls, attrs=None, children=""):
        return '<ppmdmsg action="%s" class="%s" msgtime="%s" %s>%s</ppmdmsg>' % (action, cls, MSGTIME, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
    def s_post(body, timeout=None):
        SENT.append(body); act = re.search(r'action="(\w+)"', body).group(1)
        if act == "getdemographic":
            pid = re.search(r'patientid="([^"]*)"', body).group(1)
            return ('<PPMDResults><Results><patient id="%s" respparty="resp%s" insorder="1" deceased=""/>'
                    '<insplan id="ins1" carrier="car1" begindate="01/01/2020" enddate="" sequence="1"/></Results></PPMDResults>') % (pid, re.sub(r"\D", "", pid))
        if act == "addvisit":
            N["visit"] += 1; return '<PPMDResults><Results success="1"><visit id="vst%d"/></Results></PPMDResults>' % (7000 + N["visit"])
        if act == "updvisitwithnewcharges":
            out = ""
            for fee in re.findall(r'<charge id="" [^>]*? fee="([^"]*)"', body):
                N["charge"] += 1; out += '<charge id="charge%d" fee="%s"/>' % (50000 + N["charge"], fee)
            return '<PPMDResults><Results success="1"><visit id="%s"><chargelist>%s</chargelist></visit></Results></PPMDResults>' % (re.search(r'<visit id="(vst\d+)"', body).group(1), out)
        if act == "updextrainsinfo":
            return '<PPMDResults><Results success="1"><extins %s/></Results></PPMDResults>' % re.search(r'hospitalizationfrom="[^"]*"', body).group(0)
        raise AssertionError("request the import never sends: " + act)
    def s_login(psw=None): N["login"] += 1
    def s_history(num):
        root = ET.Element("PPMDResults")
        for k, (cpt, dos) in enumerate(LIVE.get(str(num), [])):
            ET.SubElement(root, "charge", {"id": "charge%s%d" % (num, k), "proccode": cpt, "dos": dos, "void": "0", "fee": "100.00"})
        return root
    amd.msg, amd.post, amd._msgtime, amd.login_cached = s_msg, s_post, (lambda: MSGTIME), s_login
    txh.fetch = s_history
    resave.detail = lambda c: '<PPMDResults><Results><visit id="vst1" episode="ep%s" refplan="ref%s"/><charge id="charge%s" respparty="resp1"/></Results></PPMDResults>' % (str(c)[-3:], str(c)[-2:], c)
    # invented master data
    HOSPITAL = "SELFTEST HOSPITAL"; NURS = ["SELFTEST NURSING ONE", "SELFTEST NURSING TWO"]; ALF = ["SELFTEST ASSISTED LIVING ONE", "SELFTEST ASSISTED LIVING TWO"]
    FAC = {HOSPITAL: ("fac9001", "21"), NURS[0]: ("fac9002", "31"), NURS[1]: ("fac9003", "31"), ALF[0]: ("fac9004", "13"), ALF[1]: ("fac9005", "13")}
    F = lambda b: FAC[b][0]
    NPI_A, NPI_B = "10000000" + "17", "10000000" + "25"; PROF_A, PROF_B = "prof901", "prof902"
    CODES = "99223 99232 99233 99239 99306 99308 99309 99316 99344 99487 99489 99497".split()
    PCODE = {c: "pcode9" + c for c in CODES}; FEE = {c: "%d.00" % (100 + 7 * k) for k, c in enumerate(CODES)}; CPT_OF = {v: k for k, v in PCODE.items()}
    DX = {"I10": "dcode101", "E119": "dcode102", "N390": "dcode103", "F0390": "dcode104"}      # "R000" is deliberately not in AMD's list
    def workspace(name):
        ws = os.path.join(TMP, name); os.makedirs(os.path.join(ws, "hl7")); os.makedirs(os.path.join(ws, "registers"))
        json.dump(DX, open(os.path.join(ws, "dx_cache_feed.json"), "w")); return ws
    def load(ws):
        os.chdir(ws); os.environ.update(FEED_STAMP=STAMP, FEED_HL7_DIR=os.path.join(ws, "hl7"), FEED_DX_CACHE="dx_cache_feed.json")
        sp = importlib.util.spec_from_file_location("claimocity_import_site", HELPER); mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
        mod.FAC, mod.PROFILE, mod.PCODE, mod.FEE = dict(FAC), {NPI_A: PROF_A, NPI_B: PROF_B}, dict(PCODE), dict(FEE)
        mod.time = types.SimpleNamespace(sleep=lambda s: None)          # the pause between visits is not under test
        return mod
    # invented feed messages, assembled at run time
    BASE = datetime.date(2026, 11, 2)
    day = lambda n: (BASE + datetime.timedelta(days=n)).strftime("%Y%m%d")
    us = lambda d: "%s/%s/%s" % (d[4:6], d[6:8], d[:4])
    fid = lambda n: "FEEDT%03d" % n                                       # invented feed patient id (PID-3)
    chart = lambda n: "pat%d" % (9100000 + n)                             # invented chart
    def message(n, building, lines, npi="", admit=""):
        """One DFT^P03 message of invented patient n. lines = [(day number, CPT, [dx codes], units)]."""
        born = (datetime.date(1931, 1, 1) + datetime.timedelta(days=41 * n)).strftime("%Y%m%d")
        segs = [["MSH", "^~\\&", "FEED", "GRP%d^%s" % (n, building), "RECEIVING APPLICATION", "RCV", day(0) + "0101", "", "DFT^P03", "CTL%d" % n, "P", "2.5"],
                ["EVN", "P03", day(0)],
                ["PID", "1", "", fid(n), "", "ZZ" + "INVENTED" + chr(65 + n % 26) * 2 + "^" + "TESTCASE", "", born, "U"]]
        pv = ["PV1", "1", "I"] + [""] * 48; pv[7] = (npi + "^CLINICIAN^TEST") if npi else ""; pv[44] = admit; segs.append(pv)
        for k, (d, cpt, dx, units) in enumerate(lines):
            ft = ["FT1", str(k + 1)] + [""] * 30
            ft[4] = day(d) + ("1200" if (n + k) % 2 else ""); ft[5] = day(d + 1); ft[10] = units; ft[19] = "^".join(dx); ft[25] = cpt + "^TEST SERVICE"
            segs.append(ft)
        segs += [["DG1", "1", "", lines[0][2][0]], ["IN1", "1", "", "", "TEST PAYER^X"]]
        return ["|".join(x) for x in segs]
    def write(ws, name, messages, eol="\r"):
        open(os.path.join(ws, "hl7", name), "wb").write("".join(eol.join(m) + eol for m in messages).encode())
    def run(ws, mode="--all", charts=None, extra=None, same_chart=None, before_main=None):
        """parse the workspace's HL7 files with the real parser, then run the importer on them -> (module, register, requests, log).
        charts: only these patients have a chart; same_chart: {patient number: the patient whose chart it shares}."""
        pf = os.path.join(ws, "feed_parsed_%s.json" % STAMP)
        subprocess.run([sys.executable, "-I", PARSER, os.path.join(ws, "hl7"), pf], check=True, stdout=subprocess.DEVNULL)
        parsed = json.load(open(pf)); parsed += extra(parsed) if extra else []
        json.dump(parsed, open(pf, "w"))
        num = lambda m: int(m["pid"][-3:])
        match = {m["name"].upper().strip() + "|" + m["dob"][:8]: {"resolved": chart((same_chart or {}).get(num(m), num(m)))} for m in parsed if charts is None or num(m) in charts}
        json.dump(match, open(os.path.join(ws, "feed_match_%s.json" % STAMP), "w"))
        rf = os.path.join(ws, "registers", "feed_import_%s.json" % STAMP)
        if os.path.exists(rf): os.remove(rf)                              # every run is a first import of its batch
        SENT.clear(); N.update(visit=0, charge=0)
        mod = load(ws); buf = io.StringIO(); argv = sys.argv; sys.argv = ["claimocity_import.py", mode]
        if before_main: before_main(mod)
        try:
            with contextlib.redirect_stdout(buf): mod.main()
        finally: sys.argv = argv
        return mod, (json.load(open(rf)) if os.path.exists(rf) else None), list(SENT), buf.getvalue()
    attrs = lambda tag, body: dict(re.findall(r'(\w+)="([^"]*)"', re.search(r"<%s [^>]*>" % tag, body).group(0)))
    norm = lambda body: re.sub(r"vst\d+", "vst#", body)                   # the visit id is AMD's answer, not the importer's choice
    def visits(sent):
        """the write requests of one run, grouped per entered visit and keyed (chart, date, sorted CPTs)"""
        out = {}; cur = None
        for body in sent:
            act = re.search(r'action="(\w+)"', body).group(1)
            if act == "addvisit":
                a = attrs("appt", body); cur = {"appt": (a["facility"], a["profile"], a["onhcfa"]), "chart": a["patient"], "requests": [norm(body)], "admit_calls": []}
            elif act == "updvisitwithnewcharges":
                v = attrs("visit", body); lines = [(CPT_OF[p], pos) for p, pos in re.findall(r'<charge id="" [^>]*proccode="(pcode\d+)"[^>]*? pos="(\d*)"', body)]
                ext = re.search(r'<extins hospitalizationfrom="([^"]*)"/>', body)
                cur.update(facility=v["facility"], profile=v["profile"], onhcfa=v["onhcfa"], pos=[p for c, p in lines], ext=ext.group(1) if ext else None)
                cur["requests"].append(norm(body)); out[(cur["chart"], v["date"], tuple(sorted(c for c, p in lines)))] = cur
            elif act == "updextrainsinfo":
                cur["requests"].append(norm(body)); cur["admit_calls"].append(attrs("extins", body)["hospitalizationfrom"])
        return out
    one = lambda vis, n, d, *cpts: vis.get((chart(n), us(day(d)), tuple(sorted(cpts))))
    where = lambda v: None if v is None else {k: v[k] for k in ("appt", "facility", "pos", "profile", "ext", "admit_calls")}
    def row(reg, n, d, *cpts):
        return next((r for r in reg["created"] if r["pid"] == chart(n) and r["dos"] == us(day(d)) and sorted(r["cpts"]) == sorted(cpts)), {})

    # ---- the mixed batch: cases A, B, C, D in one run -------------------------------------------------------------------------------------
    CCM_OCT = [(-2, "99487", ["I10", "E119"], "1"), (-2, "99489", ["I10"], "1")]     # care management + its add-on, dated 10/31
    CCM_NOV = [(0, "99487", ["I10", "E119"], "1"), (0, "99489", ["I10"], "1")]       # ... dated 11/02
    ADM1, ADM2 = day(-3), day(4)
    M = {
     # A: nursing-building care management (10/31) + a hospital visit (11/02) - patient 1 nursing first, patient 2 hospital first
     "a1_ccm":  message(1, NURS[0], CCM_OCT[::-1], NPI_B, day(-40)),            # add-on line first in the file: the key sorts the codes
     "a1_hosp": message(1, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, ADM1),
     "a2_hosp": message(2, HOSPITAL, [(0, "99233", ["N390"], "1")], NPI_A, ADM1),
     "a2_ccm":  message(2, NURS[1], CCM_OCT, NPI_B, day(-40)),
     # A: the same pair inside ONE calendar month - the rule's own exception keeps that care management at 31 for William
     "a7_ccm":  message(7, NURS[0], CCM_NOV, NPI_B, day(-40)),
     "a7_hosp": message(7, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, ADM1),
     # B: assisted-living care management + a nursing visit (the patient moved to a nursing home) - both orders
     "b3_ccm":  message(3, ALF[0], [(0, "99487", ["I10"], "1")], NPI_A),
     "b3_nurs": message(3, NURS[0], [(1, "99309", ["F0390"], "1")], NPI_B, day(1)),
     "b4_nurs": message(4, NURS[1], [(1, "99308", ["F0390"], "1")], NPI_B, day(1)),
     "b4_ccm":  message(4, ALF[1], [(0, "99487", ["I10"], "1")], NPI_A),
     # C: same patient, same date, same codes under two buildings (+ a message that can be told apart). Patient 5: the nursing twin is
     # read last, so the patient-level building is a nursing building; patient 9: the assisted-living twin is read last
     "c5_hosp": message(5, HOSPITAL, [(1, "99232", ["N390"], "1")], NPI_A, ADM1),
     "c5_alf":  message(5, ALF[0], [(-2, "99487", ["I10"], "1")], NPI_A),
     "c5_nurs": message(5, NURS[0], [(-2, "99487", ["I10"], "1")], NPI_B),
     "c9_nurs": message(9, NURS[1], [(-2, "99487", ["I10"], "1")], NPI_B),
     "c9_alf":  message(9, ALF[1], [(-2, "99487", ["I10"], "1")], NPI_A),
     # H: nursing visits a month apart in ONE batch - from two nursing buildings (21), from the hospital building and then a nursing
     # building (22: the rehab-unit pattern), and from the same building twice (23)
     "h21_one": message(21, NURS[0], [(-30, "99309", ["F0390"], "1")], NPI_B),
     "h21_two": message(21, NURS[1], [(0, "99309", ["F0390"], "1")], NPI_B),
     "h22_hosp": message(22, HOSPITAL, [(-30, "99309", ["F0390"], "1")], NPI_A),
     "h22_nurs": message(22, NURS[0], [(0, "99309", ["F0390"], "1")], NPI_B),
     "h23_one": message(23, NURS[1], [(-30, "99309", ["F0390"], "1")], NPI_B),
     "h23_two": message(23, NURS[1], [(0, "99309", ["F0390"], "1")], NPI_B),
     # K: same patient, same date, same FIRST code, another code set, two buildings - told apart by the whole key
     "k25_alf":  message(25, ALF[0], [(-2, "99487", ["I10"], "1")], NPI_A),
     "k25_nurs": message(25, NURS[1], CCM_OCT, NPI_B),
     # D: one building, three hospital days: two clinicians, then a second admission
     "d6_day0": message(6, HOSPITAL, [(0, "99223", ["N390"], "1")], NPI_A, ADM1),
     "d6_day1": message(6, HOSPITAL, [(1, "99232", ["N390"], "1")], NPI_B, ADM1),
     "d6_day5": message(6, HOSPITAL, [(5, "99223", ["N390"], "1")], NPI_A, ADM2),
     # D: one message in the files; a second one reaches the importer only through the parsed file
     "d8_only": message(8, ALF[1], [(0, "99344", ["I10"], "1")], NPI_B),
     # D: the same message sent twice from ONE building (a re-send with another clinician and admission date): the last one read counts
     "d10_first": message(10, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_A, ADM1),
     "d10_again": message(10, HOSPITAL, [(0, "99232", ["N390"], "1")], NPI_B, ADM2),
    }
    TWO = ("a1_ccm", "a1_hosp", "a2_hosp", "a2_ccm", "a7_ccm", "a7_hosp", "b3_ccm", "b3_nurs", "b4_nurs", "b4_ccm")      # the two-building patients of A and B
    def not_in_files(parsed):
        """three parsed entries with no message in the files: of patient 8 (one building there), of patient 2 (two buildings there) and of
        patient 20, who is not in the files at all"""
        out = []
        for n, d, cpt in ((8, 2, "99487"), (2, 3, "99308"), (20, 4, "99487")):
            m = dict(next(x for x in parsed if x["pid"] == fid(min(n, 8)))); m["FT1"] = [{"dos": day(d), "posted": day(d + 1), "units": "1", "dx": "I10", "cpt": cpt}]
            if n == 20: m.update(pid=fid(20), name="ZZ" + "INVENTED" + "ABSENT, TESTCASE", dob="19" + "310" + "704")
            out.append(m)
        return out
    ws = workspace("mixed")
    write(ws, day(0) + "aaaa0000.hl7", [M[k] for k in TWO + ("c5_hosp", "c5_alf", "c5_nurs", "c9_nurs", "c9_alf")], eol="\r")
    write(ws, day(1) + "bbbb0000.hl7", [M[k] for k in ("d6_day0", "d6_day1", "d6_day5", "d8_only", "d10_first", "d10_again", "h21_one", "h21_two", "h22_hosp", "h22_nurs", "h23_one", "h23_two", "k25_alf", "k25_nurs")], eol="\r\n")
    mod, reg, sent, dry_log = run(ws, "--dry", extra=not_in_files)
    check("7: the stand-ins are what the importer imported (never the real AMD helper), and a dry run only reads",
          mod.amd is amd and mod.txh is txh and mod.resave is resave and reg is None and not [b for b in sent if re.search(r'action="(addvisit|updvisitwithnewcharges|updextrainsinfo)"', b)])
    mod, reg, sent, log = run(ws, extra=not_in_files)
    V = visits(sent)
    check("7: every message is entered once (29 visits; each pair of twins in C, and the re-sent message of D, is one visit)", len(reg["created"]) == 29 and len(V) == 29 and not reg["failed"] and N["login"] == 2, (len(reg["created"]), len(V), reg["failed"], N))
    check("7: the building is read from MSH index 3 (last ^ part), as proven against the FAC table - never the next field", all(r["fac"] for r in reg["created"] if r["feed_id"] != fid(20)), [r["fac"] for r in reg["created"]])
    # A
    for n, nb, hcpt in ((1, NURS[0], "99232"), (2, NURS[1], "99233")):
        c = one(V, n, -2, "99487", "99489"); h = one(V, n, 0, hcpt); rc = row(reg, n, -2, "99487", "99489")
        check("7A%d nursing-building CCM of a patient who also has a hospital visit: entered under the NURSING building at 32 by the rule" % n,
              c and c["facility"] == F(nb) and c["appt"][0] == F(nb) and c["pos"] == ["32", "32"] and rc.get("pos_err") == "" and set(rc.get("pos_kind")) == {"ccm"}, (where(c), rc))
        check("7A%d that CCM: its own provider, no admission date, onhcfa 0" % n, c and c["profile"] == PROF_B and c["ext"] is None and not c["admit_calls"] and c["onhcfa"] == "0", where(c))
        check("7A%d the hospital visit: under the hospital at 21, its own provider and ITS admission date (visit + updextrainsinfo)" % n,
              h and h["facility"] == F(HOSPITAL) and h["appt"][0] == F(HOSPITAL) and h["pos"] == ["21"] and h["profile"] == PROF_A and h["ext"] == us(ADM1) and h["admit_calls"] == [us(ADM1)] and h["onhcfa"] == "1", where(h))
    c = one(V, 7, 0, "99487", "99489"); rc = row(reg, 7, 0, "99487", "99489"); h = one(V, 7, 0, "99232")
    check("7A7 CCM and hospital visit in ONE calendar month: the CCM is under the nursing building and the RULE keeps it at 31 for William (applied, not skipped)",
          c and c["facility"] == F(NURS[0]) and c["pos"] == ["31", "31"] and rc.get("pos_err") == "" and set(rc.get("pos_kind")) == {"ccm-skilled-month"} and h and h["facility"] == F(HOSPITAL) and h["pos"] == ["21"], (where(c), rc, where(h)))
    # B
    for n, ab, nb, ncpt in ((3, ALF[0], NURS[0], "99309"), (4, ALF[1], NURS[1], "99308")):
        c = one(V, n, 0, "99487"); v = one(V, n, 1, ncpt); rv = row(reg, n, 1, ncpt)
        check("7B%d assisted-living CCM of a patient who also has a nursing visit: entered at the assisted-living facility at 13" % n, c and c["facility"] == F(ab) and c["pos"] == ["13"] and c["profile"] == PROF_A, where(c))
        check("7B%d the nursing visit: under the nursing building, the rule applied (first nursing visit on the chart: 31)" % n,
              v and v["facility"] == F(nb) and v["pos"] == ["31"] and v["profile"] == PROF_B and rv.get("pos_err") == "" and rv.get("pos_kind") == ["first"], (where(v), rv))
    # C
    t5 = one(V, 5, -2, "99487"); r5 = row(reg, 5, -2, "99487"); h5 = one(V, 5, 1, "99232"); t9 = one(V, 9, -2, "99487"); r9 = row(reg, 9, -2, "99487")
    check("7C same patient + date + codes under two buildings keeps the patient-level building and provider (the last message read), as before",
          t5 and t5["facility"] == F(NURS[0]) and t5["profile"] == PROF_B and t9 and t9["facility"] == F(ALF[1]) and t9["pos"] == ["13"] and t9["profile"] == PROF_A, (where(t5), where(t9)))
    check("7C ... a nursing building there: entered at the feed's 31, POS RULE NOT APPLIED (the narrowed two-building guard)",
          t5 and t5["pos"] == ["31"] and "same patient, date and codes under 2 buildings" in r5.get("pos_err", "") and r5.get("pos_lines") == ["31"], (where(t5), r5))
    check("7C ... reported in the register row whatever the building, with the two buildings it was sent from",
          all("same patient, date and codes under 2 buildings" in r.get("site_unresolved", "") for r in (r5, r9)) and r9.get("pos_err") == ""
          and r5.get("site_among") == sorted([ALF[0], NURS[0]]) and r9.get("site_among") == sorted([ALF[1], NURS[1]]), (r5, r9))
    check("7C the same patient's other message is still resolved per message", h5 and h5["facility"] == F(HOSPITAL) and h5["pos"] == ["21"] and h5["ext"] == us(ADM1), where(h5))
    # D
    d0, d1, d5 = one(V, 6, 0, "99223"), one(V, 6, 1, "99232"), one(V, 6, 5, "99223")
    check("7D one building, two clinicians: each hospital day under the clinician of ITS message", d0 and d1 and d5 and [d0["profile"], d1["profile"], d5["profile"]] == [PROF_A, PROF_B, PROF_A], [where(x) for x in (d0, d1, d5)])
    check("7D one building, two admissions: each visit carries the admission date of ITS message", d0 and d1 and d5 and [d0["ext"], d1["ext"], d5["ext"]] == [us(ADM1), us(ADM1), us(ADM2)]
          and d5["admit_calls"] == [us(ADM2)], [where(x) for x in (d0, d1, d5)])
    p8 = one(V, 8, 2, "99487"); r8 = row(reg, 8, 2, "99487"); p2 = one(V, 2, 3, "99308"); r2 = row(reg, 2, 3, "99308")
    check("7D a message that is not in the batch's HL7 files keeps the patient-level building and provider, as before, unreported",
          p8 and p8["facility"] == F(ALF[1]) and p8["pos"] == ["13"] and p8["profile"] == PROF_B and "site_unresolved" not in r8, (where(p8), r8))
    check("7D ... and when its patient has two buildings in the files: patient-level value as before, reported, the rule not applied",
          p2 and p2["facility"] == F(NURS[1]) and p2["pos"] == ["31"] and p2["profile"] == PROF_B and "not in the batch's HL7 files" in r2.get("site_unresolved", "") and "2 buildings" in r2.get("pos_err", "")
          and r2.get("site_among") == sorted([HOSPITAL, NURS[1]]) and r2.get("pos_err") == r2.get("site_unresolved"), (where(p2), r2))
    p20 = one(V, 20, 4, "99487"); r20 = row(reg, 20, 4, "99487")
    check("7D ... and of a patient who is not in the files at all: no facility, the default 31, as before, unreported as a building question",
          p20 and p20["facility"] == "" and p20["pos"] == ["31"] and "site_unresolved" not in r20 and r20.get("pos_err") == "", (where(p20), r20))
    p10 = one(V, 10, 0, "99232"); r10 = row(reg, 10, 0, "99232")
    check("7D the same message twice from one building is one visit with the provider and admission date of the copy read last, unreported",
          p10 and p10["facility"] == F(HOSPITAL) and p10["profile"] == PROF_B and p10["ext"] == us(ADM2) and "site_unresolved" not in r10 and r10.get("pos_err") == "", (where(p10), r10))
    # H: the batch's own nursing visits are read with the building they were sent from
    h1, h2 = one(V, 21, -30, "99309"), one(V, 21, 0, "99309"); rh2 = row(reg, 21, 0, "99309")
    check("7H a nursing visit a month after one in ANOTHER nursing building, both in this batch: a new admission here - 31 by the rule, never 'the monthly visit'",
          h1 and h1["facility"] == F(NURS[0]) and h2 and h2["facility"] == F(NURS[1]) and h2["pos"] == ["31"] and rh2.get("pos_kind") == ["moved"] and rh2.get("pos_err") == "", (where(h2), rh2))
    h1, h2 = one(V, 22, -30, "99309"), one(V, 22, 0, "99309"); rh2 = row(reg, 22, 0, "99309")
    check("7H ... the same after a nursing visit sent from the HOSPITAL building (its rehab unit): that one stays where the feed put it (21), this one is 31, moved",
          h1 and h1["facility"] == F(HOSPITAL) and h1["pos"] == ["21"] and h2 and h2["facility"] == F(NURS[0]) and h2["pos"] == ["31"] and rh2.get("pos_kind") == ["moved"] and rh2.get("pos_err") == "", (where(h1), where(h2), rh2))
    h2 = one(V, 23, 0, "99309"); rh2 = row(reg, 23, 0, "99309")
    check("7H ... and in the SAME building the second one is still the monthly visit (32)", h2 and h2["facility"] == F(NURS[1]) and h2["pos"] == ["32"] and rh2.get("pos_kind") == ["monthly"], (where(h2), rh2))
    k1, k2 = one(V, 25, -2, "99487"), one(V, 25, -2, "99489"); rk = [row(reg, 25, -2, c) for c in ("99487", "99489")]
    check("7K the key is the WHOLE code list: same patient, date and first code under two buildings with different codes are told apart",
          k1 and k1["facility"] == F(ALF[0]) and k1["pos"] == ["13"] and k2 and k2["facility"] == F(NURS[1]) and not any(r.get("site_unresolved") for r in rk), (where(k1), where(k2), rk))
    amb = lambda text: [l.split()[2] for l in text.splitlines() if l.startswith("BUILDING AMBIGUOUS ")]
    check("7C + 7D exactly those three visits are reported BUILDING AMBIGUOUS (log, DONE count, register; a dry run lists both twins - neither is entered yet)",
          amb(log) == [chart(5), chart(9), chart(2)] and amb(dry_log) == [chart(5)] * 2 + [chart(9)] * 2 + [chart(2)] and bool(re.search(r"(?m)^DONE .*building ambiguous[^,}]*: 3\b", log))
          and [r["feed_id"] for r in reg["created"] if r.get("site_unresolved")] == [fid(5), fid(9), fid(2)], (amb(log), amb(dry_log), [l for l in log.splitlines() if l.startswith("DONE")]))
    check("7C + 7D POS RULE NOT APPLIED only for the two of them that sit in a nursing building - never again for a patient just because of two buildings",
          [l.split()[4] for l in log.splitlines() if l.startswith("POS RULE NOT APPLIED ")] == [chart(5), chart(2)] and "not applied x2" in log and [r["pid"] for r in reg["created"] if r.get("pos_err")] == [chart(5), chart(2)],
          [l[:60] for l in log.splitlines() if l.startswith("POS RULE")])
    rep = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")], cwd=ws, env=dict(os.environ, FEED_STAMP=STAMP), capture_output=True, text=True)
    dline = next((l for l in rep.stdout.splitlines() if "Place of service in the nursing buildings" in l), "")
    check("7C + 7D the feed digest names them: BUILDING AMBIGUOUS on 3 visits, POS RULE NOT APPLIED on the 2 in a nursing building",
          rep.returncode == 0 and "BUILDING AMBIGUOUS on 3 visit(s)" in dline and "POS RULE NOT APPLIED on 2 visit(s)" in dline, dline or rep.stderr[-300:])
    site = getattr(mod, "site_of", None); parsed = json.load(open(os.path.join(ws, "feed_parsed_%s.json" % STAMP)))
    check("7: site_of(message) -> (building, provider key, admission date, why, candidate buildings) for every parsed message; why only for C's twins and D's second message, and short enough to be kept whole",
          callable(site) and all(len(site(m)) == 5 for m in parsed) and [m["pid"] for m in parsed if site(m)[3]] == [fid(5), fid(5), fid(9), fid(9), fid(2)]
          and all(len(site(m)[3]) <= 200 and bool(site(m)[3]) == bool(site(m)[4]) for m in parsed),
          None if not callable(site) else [(m["pid"], len(site(m)[3]), site(m)[3][:40]) for m in parsed if site(m)[3]])
    if callable(site):
        mod.SITES[("NOPV1", day(0), ("99309",))] = [(NURS[0], None, None)]; mod.FACOF["NOPV1"] = HOSPITAL; mod.NPIOF["NOPV1"] = NPI_A; mod.ADMIT["NOPV1"] = ADM1
        check("7: a message with no PV1 takes its own building and the patient-level provider and admission date", tuple(site({"pid": "NOPV1", "FT1": [{"dos": day(0), "cpt": "99309"}]})[:4]) == (NURS[0], NPI_A, ADM1, ""),
              site({"pid": "NOPV1", "FT1": [{"dos": day(0), "cpt": "99309"}]}))

    # ---- E: a two-building feed patient is entered exactly like two one-building feed patients on the same chart -----------------------------
    ws = workspace("split")
    other = {k: (k.endswith("_hosp") or k.endswith("_nurs")) for k in TWO}             # the hospital / nursing-visit message moves to feed patient n + 50
    re_id = lambda m, n: [seg.replace("|" + fid(n) + "|", "|" + fid(n + 50) + "|") if seg.startswith("PID|") else seg for seg in m]
    write(ws, day(0) + "cccc0000.hl7", [re_id(M[k], int(k[1])) if other[k] else M[k] for k in TWO])
    V2 = visits(run(ws, same_chart={n + 50: n for n in (1, 2, 3, 4, 7)})[2])
    keys = [k for k in V if k[0] in (chart(1), chart(2), chart(3), chart(4), chart(7)) and k != (chart(2), us(day(3)), ("99308",))]
    check("7E each visit of a two-building feed patient is sent byte for byte as for two one-building feed patients on the same chart (10 visits)",
          len(keys) == 10 and sorted(keys) == sorted(V2) and all(V[k]["requests"] == V2[k]["requests"] for k in keys), [k for k in keys if k not in V2 or V[k]["requests"] != V2[k]["requests"]])

    # ---- F: patients whose messages agree - nothing they send has changed -------------------------------------------------------------------------
    G = {
     "g1a": message(11, HOSPITAL, [(0, "99223", ["N390", "I10"], "1"), (0, "99497", ["I10"], "1")], NPI_A, ADM1),     # ACP add-on: modifier 25
     "g1b": message(11, HOSPITAL, [(1, "99232", ["N390"], "1")], NPI_A, ADM1),
     "g1c": message(11, HOSPITAL, [(2, "99239", ["N390"], "1")], NPI_A, ADM1),
     "g2a": message(12, NURS[0], [(0, "99306", ["F0390", "R000"], "1")], NPI_B, day(-2)),                               # initial visit; one dx not in AMD's list
     "g2b": message(12, NURS[0], [(1, "99309", ["F0390"], "2")], NPI_B, day(-2)),
     "g2c": message(12, NURS[0], CCM_NOV, NPI_B, day(-2)),                                                               # CCM in the month of an admission
     "g3a": message(13, ALF[0], [(0, "99344", ["I10"], "1")], NPI_A),
     "g3b": message(13, ALF[0], [(1, "99487", ["I10", "E119"], "1")], NPI_A),
     "g4a": message(14, NURS[1], [(0, "99309", ["F0390"], "1")], NPI_B),                                               # already on the chart
     "g4b": message(14, NURS[1], [(30, "99308", ["F0390"], "1"), (30, "99497", ["I10"], "1")], NPI_B),                 # the monthly visit + ACP
     "g5a": message(15, NURS[1], [(0, "99309", ["F0390"], "1")], NPI_B),                                               # no chart
     "g6a": message(16, HOSPITAL, [(0, "99233", ["N390"], "1")], "19" + "9" * 8, ADM2),                                # a clinician with no profile
     "g7a": message(17, "A BUILDING THAT IS NOT IN THE TABLE", [(0, "99309", ["F0390"], "1")], NPI_A),
     "g8a": message(18, NURS[1], [(0, "99316", ["R000"], "1")], NPI_A),                                                # no usable dx
     "g9a": message(19, NURS[0], CCM_OCT, NPI_B),                                                                      # nursing-building CCM, nothing else known
    }
    ws = workspace("agree")
    write(ws, day(0) + "dddd0000.hl7", [G[k] for k in ("g1a", "g1b", "g2a", "g2b", "g3a", "g4a", "g5a", "g6a", "g7a", "g8a", "g9a")], eol="\r")
    write(ws, day(2) + "eeee0000.hl7", [G[k] for k in ("g1c", "g2c", "g3b", "g4b")], eol="\n")
    agree = lambda **k: run(ws, charts=[11, 12, 13, 14, 16, 17, 18, 19], **k)
    LIVE[re.sub(r"\D", "", chart(14))] = [("99309", us(day(0)))]
    mod, reg, sent, log = agree()
    prints = [hashlib.sha256(norm(b).encode()).hexdigest()[:12] for b in sent]
    # Fingerprints (sha256, first 12 hex digits, visit ids masked) of this batch's requests as the importer of main 6bafe7f sent them: the
    # last one that kept the building per patient, rule version 2026-11-10.2. Recorded by running this section on that commit. They also
    # move when the place-of-service rule itself is revised: re-record ONLY for an intended change of what the importer sends - run this
    # test on the commit before that change and paste its "sent now" line.
    BEFORE = """
              75e55d4b15db 353041db6751 6199238ea6be e43fd5550072 1a7b5b51e8ba 8a97fd760f1e b97529540bdb bfd643b45d80 cd8889ba998d
              1975e2a0d0ad dda4a1cca5d6 8bcb31732d1e 604c3aa8194d 4c326002b8a8 43c3e528af65 6140850e6ca1 48ca356a2b05 ad7eec73106e
              65398782598a 999e1026cbd9 6892feffc816 bf9b31ee84ef 8fd6449f5265 4a999517fbaf 6a700f630c96 9b3ee73c03d7 9a35da5368f9
              e7a950cb7eb0 d9134609ad6b 459a79b7fac7 cd8889ba998d f105c518d5d7 527937ad4a64 1cd626405b8b 3b67df6b411f 1377c8f76535""".split()
    check("7F the batch covers entered, already-on-chart, no-chart and no-usable-dx messages and six kinds of line the rule decides",
          len(reg["created"]) == 12 and len(reg["skipped"]) == 2 and "'no chart': 1" in log and {k for r in reg["created"] for k in r["pos_kind"]} >= {"ccm", "ccm-skilled-month", "initial", "skilled", "monthly", "with-visit"},
          (len(reg["created"]), [r["why"] for r in reg["skipped"]], sorted({k for r in reg["created"] for k in r["pos_kind"]})))
    check("7F patients whose messages agree: every request byte-identical to before the change (%d requests)" % len(BEFORE), prints == BEFORE,
          "request(s) that differ: %s" % ([i for i, (a, b) in enumerate(zip(prints, BEFORE)) if a != b] or "count %d vs %d" % (len(prints), len(BEFORE))))
    if prints != BEFORE: print("     sent now: " + " ".join(prints))
    check("7F nothing is reported for them", not [r for r in reg["created"] if r.get("site_unresolved") or r.get("pos_err")] and "BUILDING AMBIGUOUS" not in log and "POS RULE NOT APPLIED" not in log)
    def patient_level(m): m.SITES.clear()                                 # no per-message entry: every message takes the patient-level values, as before
    mod2, reg2, sent2, log2 = agree(before_main=patient_level) if hasattr(mod, "SITES") else (None, None, None, None)
    check("7F the per-message values of these patients ARE the patient-level values: the same requests with the per-message table emptied",
          sent2 is not None and [norm(b) for b in sent2] == [norm(b) for b in sent] and len(sent) > 30, None if sent2 is None else len(sent2))
    LIVE.clear(); os.chdir(tmp)
per_message_cases()

print("\n%d check(s) failed" % len(FAILS) if FAILS else "\nall checks passed")
sys.exit(1 if FAILS else 0)
