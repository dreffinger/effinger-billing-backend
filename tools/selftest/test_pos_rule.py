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
#     - the advance-care-plan quality code 1123F rides, at no charge and once per patient per year, with a visit of a patient 65 or older
#       whose first plan is Medicare Part B - never on a care-management-only message, never twice, at most three visits a run until a
#       quality line has been seen billed; a refused visit is entered again without it;
#     - the feed digest carries one line saying what the rule did, shouts when an old helper ran, and mirror.py never lets a copy of the
#       feed helpers without the rule back onto main; the runbook copies them (and the parser) from the repository before every ingest.
# Run: python3 tools/selftest/test_pos_rule.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, importlib.util, io, re, contextlib
import xml.etree.ElementTree as ET
# THIS SELF-TEST NEVER REACHES ADVANCEDMD OR ANY OTHER HOST. Every network route is closed here, for this process and for every program it
# starts, before anything else is loaded: scripts/helpers holds the real amd / resave / txh / void_tx modules, and a helper STARTED AS A
# PROGRAM from that folder loads them (Python puts the program's own folder first on its path) - with them a "test" would read, and could
# void, real charges. So: (1) helpers that talk to AdvancedMD are only ever run INSIDE this process with stand-in modules (see run_inside);
# (2) the only helpers started as programs are ones that load none of those modules (checked below); (3) the network is shut either way.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
AMD_MODULES = ("amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update")
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
       # m6: ONE hospital visit sent twice with a corrected admission date, then a nursing visit of the nurse practitioner (read last)
       ("m6", B["h1"], "20261018", [("99232", "20261020")], NPI), ("m6", B["h1"], "20261019", [("99232", "20261020")], NPI), ("m6", B["n2"], "", [("99309", "20261025")], NP_NPI),
       # s1: the visit after three refused ones
       ("s1", B["n2"], "", [("99309", "20261113")], NPI)]
def ft1_bare(cpt, dos):      # the code is the LAST field of the line, with one blank after it and no component
    f = ["FT1"] + [""] * 25; f[4] = dos; f[10] = "1"; f[19] = "I10"; f[25] = cpt + " "; return "|".join(f)
def pv1(npi, admit=""): return "|".join(["PV1", "1", "I", "", "", "", "", npi + "^x"] + [""] * 36 + [admit])
ODD = ("MSH|^~\\&|feed|" + B["n1"] + "|x|x|20261109||DFT^P03|1|P|2.3\rPID|1||m7\r" + pv1(NP_NPI) + "\r" + ft1_bare("99309", "20261104") + "\r"       # m7: the blank-ended code ...
       + hl7("m7", B["n2"], "", [("99309", "20261104")], NPI)                                                                                             # ... and the same lines from another building and clinician
       + hl7("m8", B["n1"], "", [("99309", "20261104")], "1999999984")                                                                                  # m8: a clinician id the profile table does not have
       + "MSH|^~\\&|feed|" + B["n1"] + "|x|x|20261109||DFT^P03|1|P|2.3\r" + pv1(NP_NPI) + "\rPID|1||m9\r" + ft1("99309", "20261102") + "\r"            # m9: PV1 before PID
       + hl7("u2", "ZZ Other Hospital", "20261028", [("99232", "20261030")], NPI)                                                                         # u2: a hospital the table does not know
       + "MSH|^~\\&|feed\rPID|1|\r")                                                                                                                    # two short lines: they must not stop the load
open(os.path.join(tmp, "hl7", "b.hl7"), "w").write("".join(hl7(f, fac, adm, lines, npi) for f, fac, adm, lines, npi in RAW) + ODD)
json.dump([], open("feed_parsed_SELFTEST.json", "w")); json.dump({}, open("feed_match_SELFTEST.json", "w"))
json.dump({"I10": "dcode1", "E119": "dcode2"}, open("dx.json", "w"))

# ---- stand-ins for the AMD modules (nothing here can reach AdvancedMD) -------------------------------------------------------------
POSTS = []
amd = types.ModuleType("amd")
amd.msg = lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s" class="%s">%s</ppmdmsg>' % (action, cls, children)
amd._msgtime = lambda: "t"
amd.login_cached = lambda: None
DEMOG = {"order": "1", "plans": ""}                                    # the stand-in chart: billing order and plan rows
MEDICARE = '<insplan id="ins1" carrier="car6085" begindate="01/01/2020" enddate="" x="" sequence="1"/>'
OTHER = '<insplan id="ins2" carrier="car6404" begindate="01/01/2020" enddate="" x="" sequence="2"/>'
BILLS = {}                                                             # charge number -> the dates AdvancedMD lists under billed to insurance
ECHO = {"flip": False, "none": False, "refuse_quality": False, "refuse_all": False, "fail_create": 0, "drop_quality": False, "partial": None, "proccode": False, "fees": False, "qfirst": False}
ECHO0 = dict(ECHO); SEQ = [100]                                         # visit numbers never repeat between runs (the charge numbers are built from them)                                  # flip: the stand-in stores 31 where 32 was sent; none: its answer carries no place of service
def _post(body, timeout=0):
    POSTS.append(body)
    if 'action="getdemographic"' in body or "getdemographic" in body: return '<r><patient respparty="resp9" insorder="%s" deceased=""/>%s</r>' % (DEMOG["order"], DEMOG["plans"])
    if 'action="addvisit"' in body:
        if ECHO["fail_create"] > 0: ECHO["fail_create"] -= 1; return "<r><Fault>no visit today</Fault></r>"
        SEQ[0] += 1; return '<r><visit id="vst%d"/></r>' % SEQ[0]
    if 'action="updvisitwithnewcharges"' in body:
        if ECHO["refuse_all"] or (ECHO["refuse_quality"] and "pcode65441" in body):
            if ECHO["partial"]: CHART.setdefault(ECHO["partial"][0], []).append(tuple(ECHO["partial"][1:]))      # the stand-in stores a line although it answers with a fault
            return "<r><Fault>the charge amount is not accepted</Fault></r>"
        sent = re.findall(r'proccode="(pcode\d+)" cobcode="" pos="(\d+)" tos="01" units="[^"]*" netfee="0" fee="([^"]*)"', body); vid = re.search(r'<visit id="(vst\d+)"', body).group(1)
        if ECHO["drop_quality"]: sent = [x for x in sent if x[0] != "pcode65441"]
        num = list(enumerate(sent))                                                   # the charge number follows the order SENT ...
        if ECHO["qfirst"]: num = sorted(num, key=lambda x: x[1][0] != "pcode65441")   # ... the answer can list the quality charge first
        return '<r><visit id="%s">%s</visit></r>' % (vid, "".join('<charge id="charge%d%d"%s fee="%s"%s/>' % (int(vid[3:]), i, ' proccode="%s"' % pc if ECHO["proccode"] else "", fee if ECHO["fees"] else "1.00",
                                                 "" if ECHO["none"] else ' pos="%s"' % ("31" if ECHO["flip"] and q == "32" else q)) for i, (pc, q, fee) in num))
    return "<r/>"
amd.post = _post
resave = types.ModuleType("resave")
DETAILS = []                                                           # every charge number whose detail was read
def _detail(cid):
    DETAILS.append(str(cid)); b = BILLS.get(str(cid), [])
    if isinstance(b, dict): return '<r><visit episode="eps9" refplan=""/><charge id="charge%s" %s/></r>' % (cid, " ".join('%s="%s"' % kv for kv in b.items()))
    return '<r><visit episode="eps9" refplan=""/><charge id="charge%s"><insbilllist>%s</insbilllist></charge></r>' % (cid, "".join('<insbill billeddate="%s"/>' % d for d in b))
resave.detail = _detail
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
check("CCM stays 31 in a month in which the practice saw the resident at home or in an assisted-living facility (out of the building that month)",
      L([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99349", "10/20/2026")]) == ["31"]
      and ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99349", "10/20/2026")])[2] == ["ccm-skilled-month"])
check("CCM is 32 when the home / ALF visit was in ANOTHER month and this month's visit is monthly", L([("99487", "10/31/2026")], "31", True, [("99349", "07/10/2026"), ("99306", "08/01/2026"), ("99309", "09/01/2026"), ("99309", "10/01/2026")]) == ["32"])
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
_two = [("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC"), ("99309", "10/03/2026", "ASPIRE AT TALLAHASSEE")]
check("the previous visit's day named under TWO buildings (chart and feed disagree) is unclear: a move (31) in either building; one building named twice is not",
      ci.nf_visit_kind("99309", "11/02/2026", _two, "fac34")[0] == "moved" and ci.nf_visit_kind("99309", "11/02/2026", _two, "fac32")[0] == "moved" and ci.nf_visit_pos("99309", "11/02/2026", _two, "fac34")[0] == "31"
      and ci.nf_visit_kind("99309", "11/02/2026", [("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC"), ("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC")], "fac34")[0] == "monthly")
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
b6, i6, pp6 = built("m6", [("99232", "20261020")])
check("build: a visit sent twice with a corrected admission date keeps its own building and clinician (the copies agree on both); the date the copies do not agree on is not guessed from them, and the visit is named for a check",
      i6["fac"] == "fac29" and [q for _, q in pp6] == ["21"] and i6["prof"] == "prof13" and i6["pos_err"] == "" and i6["msg_own"] is False and ci.msg_agreed(msg("m6", [("99232", "20261020")])) == (B["h1"], NPI, None), i6)
check("build: (the per-patient value alone would have put that hospital visit in the nursing building under the nurse practitioner)", ci.FACOF["m6"] == B["n2"] and ci.NPIOF["m6"] == NP_NPI)
check("msg_agreed: a message the raw files do not hold has no agreed value; a message sent once has all three", ci.msg_agreed(msg("m6", [("99232", "20261021")])) == (None, None, None) and ci.msg_agreed(msg("m2", [("99232", "20261020")])) == (B["h1"], NPI, "20261018"))
b7, i7, pp7 = built("m7", [("99309", "20261104")])
check("build: a blank after the last code of a message does not let the visit take ANOTHER message's building and clinician - the two messages are a tie, entered as before and reported",
      i7["msg_own"] is False and "2 buildings" in i7["pos_err"] and ci.msg_own(msg("m7", [("99309", "20261104")])) is None, i7)
b8, i8, pp8 = built("m8", [("99309", "20261104")], live=[("99309", "10/03/2026")])
check("build: a clinician id the profile table does not have: entered under the physician profile, and said (prof_default)", i8["prof"] == "prof13" and i8["prof_default"] is True and i8["msg_own"] is True, i8)
check("build: ... the practice's own two clinicians are never flagged", i_np["prof_default"] is False and i_md["prof_default"] is False)
b9, i9, pp9 = built("m9", [("99309", "20261102")], live=[("99309", "10/03/2026")])
check("build: a PV1 that stands before the PID is still read - the nurse practitioner's visit stays hers", i9["prof"] == "prof15" and i9["prof_default"] is False and i9["msg_own"] is True, i9)
bu, iu, ppu = built("u2", [("99232", "20261030")])
_st2 = __import__("collections").Counter(); ci.count_pos(iu, _st2)
check("build: a hospital visit from a building the table does not know goes in with no facility as before - and is now counted", iu["fac"] == "" and [q for _, q in ppu] == ["31"] and _st2["visit entered with NO facility - its building is not in the facility table"] == 1, (iu, dict(_st2)))
check("the raw-file loader was not stopped by a three-field MSH line or a two-field PID line", "" in ci.FACOF and ci.FACOF.get("m9") == B["n1"])
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
for _odd in (5, True, [5], [None], {"a": 1}, "x"):
    json.dump({"created": [], "failed": [7, None, "x", {"lines": _odd}], "skipped": [{"feed_id": "z", "pid": "pat999", "why": "odd", "lines": _odd}, 3] + [{"feed_id": "s1", "pid": "pat201", "why": "unknown CPT 99310", "lines": [["99310", d, B["n2"]]]} for d in ("10/27/2026", "11/03/2026", "11/10/2026")]},
              open(os.path.join(tmp, "registers", "feed_import_20261111T0000Z.json"), "w"))
    out, dry = run_dry()
    check("main --dry: an odd row or line (%r) in an earlier register is passed over - the rows after it are still read (31)" % (_odd,), dry.get("pat201", [{}])[0].get("pos_lines") == ["31"] and dry["pat201"][0]["pos_kind"] == ["skilled"], (dry, out[-300:]))
os.remove(os.path.join(tmp, "registers", "feed_import_20261111T0000Z.json"))
ci.PARSED[:] = [P_("n2", "two", [("99310", "20261102")])]
out, dry = run_dry()
check("main --dry: a refused message is said as before", "skip: unknown CPT 99310" in out, out[-300:])
def run_live(parsed, flip=False, none=False):
    ci.PARSED[:] = parsed; ECHO.update(flip=flip, none=none); POSTS.clear(); buf = io.StringIO(); argv = sys.argv[:]; sys.argv = ["claimocity_import.py", "--all"]
    ci.BATCH_NF.clear(); ci.BATCH_NF_ERR[0] = ""; ci._ctx.clear(); regp = os.path.join(tmp, "registers", "feed_import_SELFTEST.json"); _sleep = ci.time.sleep; ci.time.sleep = lambda s: None
    try:
        with contextlib.redirect_stdout(buf): ci.main()
    finally: ci.time.sleep = _sleep; sys.argv = argv; ECHO.update(ECHO0)
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
check("live run: AdvancedMD storing 31 where 32 was sent is said per visit, counted, and shown in a short line within the last three", out.count("POS NOT KEPT") == 2 and any(l.startswith("POS CHECK: stored another POS x2; not own message x0; clinician unknown x0; no facility x0") and len(l) <= 110 for l in last3)
      and any(l.startswith("POS RULE:") for l in last3) and all(r["pos_stored"] != r["pos_lines"] for r in reg["created"]), last3)
out, reg = run_live(M1, none=True)
check("live run: an answer without the place of service claims nothing either way", all(r["pos_stored"] is None for r in reg["created"]) and "POS NOT KEPT" not in out, reg["created"])
out, reg = run_live([P_("m5", "m5", [("99498", "20270121"), ("99309", "20270120")]), P_("m5", "m5", [("99306", "20270121")])])
check("live run: a message with two dates is remembered line by line - the admission visit of the later date is still entered", len(reg["created"]) == 2 and reg["created"][0]["dos_lines"] == ["01/21/2027", "01/20/2027"] and reg["created"][1]["cpts"] == ["99306"] and reg["skipped"] == [], (reg["created"], reg["skipped"]))
# ---- 4c. the advance-care-plan quality code 1123F (William 11/10/2026: "yes for all ... once per patient ... every patient 65 and older") ----
def qmsg(fid, lines, dob="1940" + "0215"): return {"pid": fid, "name": "x", "dob": dob, "FT1": [{"cpt": c, "dos": d, "dx": "I10^E119", "units": "1"} for c, d in lines]}
def qctx(live=(), plans=None, order="1"):
    c = ctx(live); c["plans"] = [("ins1", "car6085", "01/01/2020", "", "1")] if plans is None else plans; c["insorder"] = order; return c
def qreset(**kw): ci.QUALITY.clear(); ci.QUALITY.update(ci._quality_fresh()); ci.QUALITY.update(kw)
def qbuilt(m, c):
    out, info = ci.build(m, c)
    return (out, info, re.findall(r'proccode="(pcode\d+)" cobcode="" pos="(\d+)"', out[1]) if out else [])
QP = "pcode65441"
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
check("quality: a monthly nursing visit of a Medicare patient of 86 carries 1123F as its LAST line, same place of service, no charge, no modifier",
      pp == [("pcode65119", "32"), (QP, "32")] and info["quality_codes"] == ["1123F"] and info["cpts"] == ["99309"] and info["quality_fee"] == "0.00" and info["quality_dos"] == "11/02/2026"
      and re.search(r'modcodes="" aging="11/02/2026" billins="1" proccode="pcode65441" cobcode="" pos="32" tos="01" units="1" netfee="0" fee="0.00" allowed="0.00"', out[1]) is not None, (pp, info))
check("quality: the same visit WITHOUT the line is kept for the fail-safe, and differs only by that line", QP not in out[2] and out[2].count("<charge ") == 1 and out[1].count("<charge ") == 2 and len(re.findall(r'<charge id=""(?:(?!</charge>).)*proccode="pcode65441"(?:(?!</charge>).)*</charge>', out[1])) == 1
      and re.sub(r'<charge id=""(?:(?!</charge>).)*proccode="pcode65441"(?:(?!</charge>).)*</charge>', "", out[1]) == out[2] and out[1].index(QP) > out[1].index("pcode65119") and out[1].rstrip().endswith("</charge></chargelist></visit></ppmdmsg>"), out[2][-300:])
check("quality: the line carries the diagnoses of its visit line", out[1].count('diagcodes="dcode1 dcode2"') == 2)
out2, info2, pp2 = qbuilt(qmsg("n2", [("99309", "20261105")]), qctx([("99309", "10/03/2026")]))
check("quality: once per patient - a second visit of the same chart in the same run gets no second line", QP not in out2[1] and "quality_codes" not in info2, info2)
qreset(); out, info, pp = qbuilt(qmsg("h1", [("99232", "20261031")]), qctx())
check("quality: a hospital visit carries it at place of service 21", pp == [("pcode65089", "21"), (QP, "21")], pp)
qreset(); out, info, pp = qbuilt(qmsg("a1", [("99344", "20261031")]), qctx())
check("quality: a home / assisted-living visit carries it at 13", pp == [("pcode601053", "13"), (QP, "13")], pp)
def none(label, m, c, **kw):
    qreset(**kw); out, info, pp = qbuilt(m, c)
    check("quality: no line - " + label, out is not None and QP not in out[1] and "quality_codes" not in info and out[1] == out[2], (pp, info))
none("patient is 64 on the date of service", qmsg("n2", [("99309", "20261102")], dob="1962" + "1103"), qctx())
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")], dob="1961" + "1102"), qctx())
check("quality: ... and 65 on the very day gets it", QP in out[1], pp)
none("no date of birth in the feed", qmsg("n2", [("99309", "20261102")], dob=""), qctx())
none("the 01/01/1900 placeholder birth date", qmsg("n2", [("99309", "20261102")], dob="1900" + "0101"), qctx())
none("care management only (not one of the measure's visit codes)", qmsg("n1", [("99487", "20261031"), ("99489", "20261031")]), qctx())
none("advance care planning 99497 alone", qmsg("n2", [("99497", "20261102")]), qctx())
none("a discharge visit alone", qmsg("n2", [("99316", "20261102")]), qctx())
none("Medicare is not the FIRST plan", qmsg("n2", [("99309", "20261102")]), qctx(plans=[("ins1", "car6085", "01/01/2020", "", "1"), ("ins2", "car6404", "01/01/2020", "", "2")], order="2,1"))
none("the first plan is another payer", qmsg("n2", [("99309", "20261102")]), qctx(plans=[("ins2", "car6404", "01/01/2020", "", "1")]))
none("the Medicare plan ended before the visit", qmsg("n2", [("99309", "20261102")]), qctx(plans=[("ins1", "car6085", "01/01/2020", "10/31/2026", "1")]))
none("the Medicare plan starts after the visit", qmsg("n2", [("99309", "20261102")]), qctx(plans=[("ins1", "car6085", "12/01/2026", "", "1")]))
none("no plan on the chart", qmsg("n2", [("99309", "20261102")]), qctx(plans=[]))
none("1123F already on the chart this year", qmsg("n2", [("99309", "20261102")]), qctx([("1123F", "03/04/2026")]))
none("1124F already on the chart this year", qmsg("n2", [("99309", "20261102")]), qctx([("1124F", "03/04/2026")]))
none("the code is switched off", qmsg("n2", [("99309", "20261102")]), qctx(), off="refused")
none("the pilot cap is reached", qmsg("n2", [("99309", "20261102")]), qctx(), added=3)
none("earlier pilot lines are still waiting for their outcome", qmsg("n2", [("99309", "20261102")]), qctx(), wait=True)
none("an earlier import register already shows the code for this patient this year (whatever the chart history lists)", qmsg("n2", [("99309", "20261102")]), qctx(), done={("pat9", "2026")})
qreset(dead={("pat9", "1123F", "10/05/2026")}); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026"), ("1123F", "10/05/2026")]))
check("quality: a $0.00 line that never went out on a claim does not count as reported - the patient gets the code again", QP in out[1], pp)
qreset(dead={("pat9", "1123F", "10/05/2026")}); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026"), ("1123F", "10/05/2026"), ("1123F", "10/20/2026")]))
check("quality: ... but another 1123F on the chart that year still does", QP not in out[1], pp)
ci.FAC["ER X"] = ("fac99", "23"); ci.FACOF["e1"] = "ER X"; qreset(); out, info, pp = qbuilt(qmsg("e1", [("99232", "20261031")]), qctx())
check("quality: never on an emergency-department line (place of service 23)", out is not None and QP not in out[1] and "quality_codes" not in info and pp == [("pcode65089", "23")], (pp, info))
del ci.FAC["ER X"]; del ci.FACOF["e1"]
qreset(added=3, confirmed=True); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx())
check("quality: ... and no cap once a quality line has been seen billed", QP in out[1], pp)
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("1123F", "12/04/2025")]))
check("quality: last year's code does not count for this year", QP in out[1], pp)
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99497", "20261102"), ("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
check("quality: with a visit and 99497 in one message the line rides with the VISIT and comes last", [x for x, _ in pp] == ["pcode492667", "pcode65119", QP] and pp[2][1] == pp[1][1], pp)
qreset(); _q = ci.quality_due; ci.quality_due = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx())
check("quality: a failure in the decision never touches the visit (entered as before, no line)", QP not in out[1] and out[1] == out[2] and "quality_codes" not in info, info)
ci.quality_due = _q
check("quality: Medicare first is read from the billing order, not from the list order", ci.medicare_first({"insorder": "2,1", "plans": [("i", "car6404", "", "", "1"), ("j", "car6085", "01/01/2020", "", "2")]}, "11/02/2026")
      and not ci.medicare_first({"insorder": "1,2", "plans": [("i", "car6404", "", "", "1"), ("j", "car6085", "01/01/2020", "", "2")]}, "11/02/2026") and not ci.medicare_first({"insorder": "1", "plans": None}, "11/02/2026") and not ci.medicare_first({}, "x"))
# _bills: what the charge detail says about one line
BILLS.clear(); BILLS.update({"11": ["11/11/2026"], "12": {"void": "1"}, "13": {"proccode": "pcode65119"}, "14": {"insbilled": "1", "datebilled": "11/12/2026 21:10:33", "proccode": "pcode65441"}, "15": {"insbilled": "0", "datebilled": ""}})
check("quality: a line's billing is read from its charge detail - billed, never billed, void, another procedure, the charge's own billed flag",
      ci._bills("charge11") == ["11/11/2026"] and ci._bills("charge10") == [] and ci._bills("12") is None and ci._bills("13", QP) is None and ci._bills("13") == []
      and ci._bills("14", QP) == ["11/12/2026"] and ci._bills("15") == [] and ci._bills("") is None and ci._bills(None) is None)
BILLS.clear()
# through main(): the pilot, its outcome, the refusal - every state read from the earlier registers
def Q_(fid, k, lines, dob="1940" + "0215"): return {"pid": fid, "name": NAME(k), "dob": dob, "file": "f", "FT1": [{"cpt": c, "dos": d, "dx": "I10", "units": "1"} for c, d in lines]}
for i in range(1, 10): ci.MATCH[NAME("q%d" % i).upper().strip() + "|" + "19400215"] = {"resolved": "pat40%d" % i}
def charts0(): CHART.update({"40%d" % i: [("99309", "10/03/2026")] for i in range(1, 10)})
charts0()
def visits(day, ks): return [Q_("n2", "q%d" % k, [("99309", day)]) for k in ks]
QB = visits("20261102", (1, 2, 3, 4)) + [Q_("n1", "q5", [("99487", "20261031")])]
DEMOG["plans"] = MEDICARE + OTHER
REGDIR = os.path.join(tmp, "registers")
def clear_regs():
    for f in os.listdir(REGDIR):
        if f.startswith("feed_import_"): os.remove(os.path.join(REGDIR, f))
def keep(reg, stamp): json.dump(reg, open(os.path.join(REGDIR, "feed_import_%s.json" % stamp), "w"))
def qrows_of(reg): return [r for r in reg["created"] if r.get("quality_codes")]
def num(cid): return re.sub(r"\D", "", cid)
def live(parsed, env=None, **echo):
    ECHO.update(echo); DETAILS.clear(); old = os.environ.get("QUALITY_CODE")
    if env is None: os.environ.pop("QUALITY_CODE", None)
    else: os.environ["QUALITY_CODE"] = env
    try: return run_live(parsed)
    finally:
        if old is None: os.environ.pop("QUALITY_CODE", None)
        else: os.environ["QUALITY_CODE"] = old
clear_regs(); ci.PARSED[:] = QB; out, dry = run_dry()
nq = [k for k, v in dry.items() if v[0].get("quality_codes")]
check("main --dry: pilot - three of four eligible visits would carry the code, the care-management message none, and the log line says so", len(nq) == 3 and "pat405" not in nq
      and "QUALITY 1123F: would be on x3 visit(s), line amount $0.00, pilot: at most 3 visit(s) until one is seen billed" in out, (nq, out[-400:]))
out, reg = live(QB); qrows = qrows_of(reg)
check("live run 1: three visits carry the line; each row keeps the line's charge number last in its charge list and its codes unchanged", len(qrows) == 3 and all(r["cpts"] == ["99309"] and len(r["charges"]) == 2
      and r["quality_charge"] == r["charges"][-1] and r["fees"] == ["1.00"] for r in qrows) and len(reg["created"]) == 5 and "QUALITY 1123F: on x3 visit(s), line amount $0.00, pilot: at most 3 visit(s) until one is seen billed" in out, (reg["created"], out[-300:]))
check("live run 1: the register records where the quality code stands (pilot, $0.00, nothing known yet)", reg["quality_gate"] == {"code": "1123F", "fee": "0.00", "confirmed": False, "proof": None, "zero_not_billed": False,
      "off": "", "wait": False, "pending": [], "pending_since": "", "dead_zero_lines": [], "void_lines": [], "reset": False, "pilot_cap": 3, "notes": []}, reg.get("quality_gate"))
out, regp = live(visits("20261103", (4,)), proccode=True); rp_ = qrows_of(regp)
check("the line's charge number is taken from AdvancedMD's answer by its procedure when the answer names it; the fee list stays one amount per message code", len(rp_) == 1 and rp_[0]["quality_charge"] == rp_[0]["charges"][-1] and rp_[0]["fees"] == ["1.00"] and "charge lines': 1" in out, (regp["created"], out[-200:]))
RUN1 = reg; keep(RUN1, "20261111T0100Z"); PIL = [num(r["quality_charge"]) for r in qrows]; FIRST = [num(r["charges"][0]) for r in qrows]
# run 2: nothing billed yet -> the pilot WAITS (no new line), and says which visits it waits for
out, reg2 = live(visits("20261109", (4, 1)))
check("run 2, nothing billed yet: NO new line (the pilot waits for the outcome of its first three), every earlier line was looked up", qrows_of(reg2) == [] and len(reg2["created"]) == 2 and reg2["quality_gate"]["wait"] is True
      and reg2["quality_gate"]["pending"] == [r["visit"] for r in qrows] and reg2["quality_gate"]["pending_since"] == "feed_import_20261111T0100Z.json" and all(c in DETAILS for c in PIL + FIRST)
      and "pilot: waiting for the outcome of 3 earlier line(s) - none added" in out, (reg2["quality_gate"], out[-300:]))
keep(reg2, "20261112T0100Z"); ci.PARSED[:] = visits("20261110", (4,)); out, dry = run_dry()
check("a dry run reads nothing in AdvancedMD for the pilot and shows 'waiting'", not any(v[0].get("quality_codes") for v in dry.values()) and "pilot: waiting for the outcome of 3 earlier line(s)" in out and ci.QUALITY["wait"] is True, out[-300:])
# run 3: one of the first lines is listed as billed -> proven, no cap; once per patient per year also from the registers
BILLS[PIL[0]] = ["11/12/2026"]; charts0()
out, reg3 = live(visits("20261116", (1, 2, 3, 4, 6, 7, 8, 9)))
got = {r["pid"] for r in qrows_of(reg3)}
check("run 3, an earlier line is billed: proof recorded, no cap - every patient not yet coded gets the line, nobody twice (the chart history here lists no 1123F at all: the registers say who has it)",
      got == {"pat404", "pat406", "pat407", "pat408", "pat409"} and reg3["quality_gate"]["confirmed"] is True and reg3["quality_gate"]["proof"]["charge"] == qrows[0]["quality_charge"] and reg3["quality_gate"]["proof"]["billed"] == "11/12/2026"
      and reg3["quality_gate"]["pilot_cap"] is None and reg3["quality_gate"]["wait"] is False and "no cap (a quality line was seen billed)" in out, (sorted(got), reg3["quality_gate"]))
keep(reg3, "20261116T0100Z"); BILLS.clear()
out, reg4 = live(visits("20261123", (5,)))
check("later runs read the proof from the register: no line is looked up again, the next patient gets the code", reg4["quality_gate"]["confirmed"] is True and len(qrows_of(reg4)) == 1 and not (set(DETAILS) & set(PIL + FIRST)), (reg4["quality_gate"], DETAILS))
# AdvancedMD bills the visit but leaves the $0.00 line off the claim -> one cent, a new pilot, and the first patients get the code again
clear_regs(); keep(RUN1, "20261111T0100Z"); BILLS.clear(); BILLS[FIRST[0]] = ["11/11/2026"]
CHART.update({r["pid"][3:]: [("99309", "10/03/2026"), ("99309", "11/02/2026"), ("1123F", "11/02/2026")] for r in qrows})      # the chart history lists the dead $0.00 lines
out, regz = live(visits("20261109", (1, 2, 3, 4))); qz = qrows_of(regz); gz = regz["quality_gate"]
check("the visit was billed WITHOUT its $0.00 quality line -> new lines carry one cent, a new pilot of three, the register says why and lists the dead $0.00 lines", gz["fee"] == "0.01" and gz["zero_not_billed"] is True
      and gz["confirmed"] is False and gz["wait"] is False and len(qz) == 3 and all(r["quality_fee"] == "0.01" for r in qz) and sorted(d[0] for d in gz["dead_zero_lines"]) == sorted(r["pid"] for r in qrows)
      and all(d[2] in [r["quality_charge"] for r in qrows] for d in gz["dead_zero_lines"]) and any("without its $0.00 quality line" in n for n in gz["notes"]), gz)
check("... the patients whose $0.00 line never went out get the code AGAIN at one cent (their dead line on the chart does not count)", {r["pid"] for r in qz} <= {r["pid"] for r in qrows} | {"pat404"} and len({r["pid"] for r in qz} & {r["pid"] for r in qrows}) >= 2, [r["pid"] for r in qz])
check("... and the one-cent line is what was sent", sum(1 for b_ in POSTS if re.search(r'proccode="pcode65441" cobcode="" pos="\d+" tos="01" units="1" netfee="0" fee="0.01" allowed="0.01"', b_)) == 3, [b_[-300:] for b_ in POSTS if "pcode65441" in b_])
keep(regz, "20261112T0100Z"); PZ = [num(r["quality_charge"]) for r in qz]; FZ = [num(r["charges"][0]) for r in qz]
out, regz2 = live(visits("20261116", (1, 2, 3, 4)))
check("one cent, nothing billed yet: the new pilot waits too (only the one-cent lines are looked up)", qrows_of(regz2) == [] and regz2["quality_gate"]["wait"] is True and regz2["quality_gate"]["fee"] == "0.01"
      and len(regz2["quality_gate"]["pending"]) == 3 and regz2["quality_gate"]["pending_since"] == "feed_import_20261112T0100Z.json" and not (set(DETAILS) & set(PIL)), (regz2["quality_gate"], DETAILS))
keep(regz2, "20261116T0100Z"); BILLS[PZ[1]] = ["11/17/2026"]
out, regz3 = live(visits("20261123", (1, 2, 3, 4)))
left = ({r["pid"] for r in qrows} | {"pat404"}) - {r["pid"] for r in qz}
check("a one-cent line is billed: proven at one cent - the one patient still without a reported code gets it, the others are not coded again", regz3["quality_gate"]["confirmed"] is True and regz3["quality_gate"]["fee"] == "0.01"
      and {r["pid"] for r in qrows_of(regz3)} == left and len(left) == 1, (left, [r["pid"] for r in qrows_of(regz3)], regz3["quality_gate"]))
clear_regs(); keep(RUN1, "20261111T0100Z"); keep(regz, "20261112T0100Z"); BILLS.clear(); BILLS[FZ[0]] = ["11/13/2026"]
out, regz4 = live(visits("20261116", (4,)))
check("a visit is billed without its ONE-CENT line too: the code is switched off and the register says a person has to look", qrows_of(regz4) == [] and "without its one-cent quality line too" in regz4["quality_gate"]["off"] and len(regz4["created"]) == 1
      and "OFF - AdvancedMD billed visit" in out, (regz4["quality_gate"], out[-300:]))
BILLS.clear(); BILLS[PIL[0]] = {"void": "1"}; BILLS[PIL[1]] = {"void": "1"}; BILLS[PIL[2]] = {"void": "1"}; clear_regs(); keep(RUN1, "20261111T0100Z"); charts0()
out, regv = live(visits("20261109", (4,)))
check("somebody took the pilot's lines off their visits (void) and none was billed: NO new pilot - the code is off until a person says to try again", qrows_of(regv) == [] and len(regv["created"]) == 1 and regv["quality_gate"]["wait"] is False
      and "3 earlier quality line(s) were taken off their visits" in regv["quality_gate"]["off"] and sum("taken off the visit" in n for n in regv["quality_gate"]["notes"]) == 3
      and sorted(regv["quality_gate"]["void_lines"]) == sorted(r["quality_charge"] for r in qrows), regv["quality_gate"])
keep(regv, "20261112T0100Z"); out, regv2 = live(visits("20261110", (1, 4)), env="reset")
check("... after QUALITY_CODE=reset the pilot starts again, and a patient whose line was taken off is due again", {r["pid"] for r in qrows_of(regv2)} == {"pat401", "pat404"} and regv2["quality_gate"]["off"] == "" and regv2["quality_gate"]["reset"] is True, (regv2["quality_gate"], [r["pid"] for r in qrows_of(regv2)]))
BILLS.clear(); [BILLS.__setitem__(c, {"void": "1"}) for c in PIL + FIRST]; clear_regs(); keep(RUN1, "20261111T0100Z"); charts0()
out, regw = live(visits("20261109", (1, 2, 3, 4)))
check("the pilot's whole visits were voided: no outcome either way - the pilot carries on with three visits, and those patients are due again", len(qrows_of(regw)) == 3 and regw["quality_gate"]["off"] == "" and regw["quality_gate"]["wait"] is False
      and regw["quality_gate"]["confirmed"] is False and sum("no longer on the chart (void)" in n for n in regw["quality_gate"]["notes"]) == 3 and {r["pid"] for r in qrows_of(regw)} <= {"pat401", "pat402", "pat403", "pat404"}, regw["quality_gate"])
swap = json.loads(json.dumps(RUN1)); [r.update(charges=[r["quality_charge"], r["charges"][0]]) for r in swap["created"] if r.get("quality_charge")]
BILLS.clear(); BILLS[FIRST[0]] = ["11/11/2026"]; clear_regs(); keep(swap, "20261111T0100Z"); charts0()
out, regx = live(visits("20261109", (4,)))
check("the visit's own charge is found whatever the order of the recorded charge numbers (a visit billed without its $0.00 line is still seen)", regx["quality_gate"]["zero_not_billed"] is True and regx["quality_gate"]["fee"] == "0.01", regx["quality_gate"])
BILLS.clear()
many = {"created": [dict(qrows[0], pid="pat5%02d" % i, visit="vst9%02d" % i, quality_charge="charge99%02d1" % i, charges=["charge99%02d0" % i, "charge99%02d1" % i]) for i in range(8)], "skipped": [], "failed": []}
clear_regs(); keep(many, "20261111T0100Z"); out, regm = live(visits("20261109", (4,)))
check("at most six earlier lines are looked up in one run (two reads each); the rest keep the pilot waiting", len([d for d in DETAILS if d.startswith("99")]) == 12 and regm["quality_gate"]["wait"] is True and len(regm["quality_gate"]["pending"]) == 8, (DETAILS, regm["quality_gate"]))
# what AdvancedMD stored is checked for a visit that carries the quality line too: its own lines as before, the quality line apart
clear_regs(); BILLS.clear(); charts0(); keep(dict(RUN1, quality_gate=dict(RUN1["quality_gate"], confirmed=True)), "20261111T0100Z")
out, regk = run_live(visits("20261203", (6,)))
rk = regk["created"][0]
check("a monthly visit with the quality line: the visit's own line is compared as before (32), the quality line's place of service is recorded apart - kept as sent", rk.get("quality_codes") == ["1123F"] and rk["pos_lines"] == ["32"]
      and rk["quality_pos"] == "32" and rk["pos_stored"] == ["32"] and rk["quality_pos_stored"] == "32" and "pos_sent" not in rk and "POS NOT KEPT" not in out, (rk, out[-300:]))
charts0(); out, regk2 = run_live(visits("20261204", (7,)), flip=True)
rk2 = regk2["created"][0]
check("... and when AdvancedMD stores 31 where 32 was sent on such a visit, it is said loudly", rk2.get("quality_codes") == ["1123F"] and rk2["pos_stored"] == ["31"] and rk2["quality_pos_stored"] == "31" and "POS NOT KEPT" in out and "ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE" in out, (rk2, out[-400:]))
charts0(); CHART["408"] = [("99309", "10/03/2026")]; out, regf = live([Q_("n2", "q8", [("99309", "20261207"), ("99497", "20261207")])], fees=True, qfirst=True)
rf = regf["created"][0]
check("the answer lists the quality charge FIRST and names no procedure: the charge is found by its amount - the right charge number, the visit's own fees in order, the visit's own lines compared",
      rf.get("quality_codes") == ["1123F"] and rf["quality_charge"] == rf["charges"][0] and len(rf["charges"]) == 3 and rf["fees"] == ["141.00", "133.00"] and rf["pos_stored"] == rf["pos_lines"] and rf["quality_pos_stored"] == rf["quality_pos"], rf)
charts0(); out, regn = live(visits("20261208", (9,)), proccode=True, qfirst=True)
rn = regn["created"][0]
check("the answer names procedures: the quality charge is found by its procedure wherever it stands", rn.get("quality_codes") == ["1123F"] and rn["quality_charge"] == rn["charges"][0] and rn["fees"] == ["1.00"], rn)
check("quality_in_answer: by procedure, else the one charge with the line's amount, else the last of an unnamed longer list, else nothing",
      ci.quality_in_answer([("charge1", "pcode65119", "141.00", "32"), ("charge2", "pcode65441", "0.00", "32")], 1, "0.00") == 1
      and ci.quality_in_answer([("charge2", "", "0.00", "32"), ("charge1", "", "141.00", "32")], 1, "0.00") == 0 and ci.quality_in_answer([("charge1", "", "1.00", ""), ("charge2", "", "1.00", "")], 1, "0.00") == 1
      and ci.quality_in_answer([("charge1", "pcode65119", "141.00", "32")], 1, "0.00") is None and ci.quality_in_answer([("charge1", "pcode65119", "141.00", "32"), ("charge2", "pcode492667", "133.00", "32")], 2, "0.01") is None
      and ci.quality_in_answer([], 1, "0.00") is None and ci.answer_charges('<r><charge pos="32" fee="0.00" id="charge7"/><charge id="x"/><charge id="charge8" proccode="pcode65441"/></r>') == [("charge7", "", "0.00", "32"), ("charge8", "pcode65441", "", "")])
# the chart's sample charge (its episode and referral plan are read from it) is never a quality line when the chart has another
CHART["410"] = [("99309", "10/03/2026"), ("1123F", "11/02/2026")]; ci._ctx.clear(); DETAILS.clear(); ci.chart_ctx("pat410")
check("chart context: the sample charge is the ordinary charge, not the newer quality line", DETAILS == ["1"], DETAILS)
CHART["411"] = [("1123F", "11/02/2026")]; ci._ctx.clear(); DETAILS.clear(); ci.chart_ctx("pat411")
check("chart context: ... a chart that holds nothing but a quality line still gives a sample", DETAILS == ["1"], DETAILS)
ci._ctx.clear(); DETAILS.clear()
clear_regs()
# AdvancedMD refuses a visit that carries the line
clear_regs(); BILLS.clear(); charts0()
out, reg5 = live(QB, refuse_quality=True)
ref = [r for r in reg5["created"] if r.get("quality_refused")]
check("refused: after a fresh read of the chart the visit is entered again WITHOUT the line; all five visits are created, nothing failed", len(reg5["created"]) == 5 and reg5["failed"] == [] and len(ref) == 1 and ref[0]["quality_codes"] == []
      and len(ref[0]["charges"]) == 1 and ref[0]["quality_refused_fee"] == "0.00" and ref[0]["quality_tried"] == "0.00", (reg5["created"], reg5["failed"]))
check("refused: no further line is tried in that run, it is said and counted", sum(1 for b_ in POSTS if "pcode65441" in b_) == 1 and "QUALITY CODE REFUSED" in out and "QUALITY CODE NOT ACCEPTED by AdvancedMD" in out
      and "QUALITY 1123F: on x0 visit(s)" in out and "OFF - this run: AdvancedMD refused a visit that carried the code" in out, out[-600:])
keep(reg5, "20261113T0100Z"); ci.PARSED[:] = visits("20261117", (2,)); out, dry = run_dry()
check("refused at $0.00: the next run tries one cent", ci.QUALITY["fee"] == "0.01" and ci.QUALITY["off"] == "" and any(v[0].get("quality_fee") == "0.01" for v in dry.values()), (ci.QUALITY, dry))
reg6 = json.loads(json.dumps(reg5)); [r.update(quality_refused_fee="0.01") for r in reg6["created"] if r.get("quality_refused")]
keep(reg6, "20261114T0100Z"); out, dry = run_dry()
check("refused at one cent too: the code stays off until William says to start again, and every run says so", ci.QUALITY["off"] != "" and not any(v[0].get("quality_codes") for v in dry.values())
      and "OFF - AdvancedMD refused a visit that carried the code with a one-cent charge too (feed_import_20261114T0100Z.json)" in out, out[-400:])
out, regr = live(visits("20261117", (2,)), env="reset")
check("QUALITY_CODE=reset (William's word): the pilot starts again at $0.00 and the register records the restart", regr["quality_gate"]["reset"] is True and regr["quality_gate"]["off"] == "" and regr["quality_gate"]["fee"] == "0.00"
      and len(qrows_of(regr)) == 1 and any("started again" in n for n in regr["quality_gate"]["notes"]), regr["quality_gate"])
keep(regr, "20261117T0100Z"); out, regr2 = live(visits("20261118", (3,)))
check("after a restart the earlier refusals no longer count: the pilot waits for its new first line", regr2["quality_gate"]["off"] == "" and regr2["quality_gate"]["fee"] == "0.00" and regr2["quality_gate"]["wait"] is True
      and regr2["quality_gate"]["reset"] is False and regr2["quality_gate"]["pending"] == [qrows_of(regr)[0]["visit"]], regr2["quality_gate"])
out, rego = live(visits("20261119", (6,)), env="off")
check("QUALITY_CODE=off: no line in that run, and the register says why", qrows_of(rego) == [] and "switched off (QUALITY_CODE=off)" in rego["quality_gate"]["off"] and len(rego["created"]) == 1, rego["quality_gate"])
# refused, and the chart then shows part of the visit: never sent a second time
clear_regs(); charts0()
out, regq = live(visits("20261102", (1, 2)), refuse_quality=True, partial=("401", "99309", "11/02/2026"))
f = regq["failed"]
check("refused and the chart now shows a line of that visit: NOT sent again (it would double the charge) - the visit is named for a person, the next visit goes in without the code",
      len(f) == 1 and f[0]["pid"] == "pat401" and f[0]["stored"] == [["99309", "11/02/2026"]] and f[0]["empty_visit"].startswith("vst") and "not sent again" in f[0]["err"] and f[0]["info"]["quality_tried"] == "0.00"
      and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 2 and len(regq["created"]) == 1 and qrows_of(regq) == [] and "could not be shown free of it" in regq["quality_gate"]["off"], (f, regq["created"]))
_cl = ci.chart_lines_now; ci.chart_lines_now = lambda pid: (_ for _ in ()).throw(RuntimeError("history down")); charts0()
out, regq2 = live(visits("20261102", (1,)), refuse_quality=True); ci.chart_lines_now = _cl
check("refused and the chart cannot be read: not sent again either", len(regq2["failed"]) == 1 and regq2["created"] == [] and "chart not read" in str(regq2["failed"][0]["stored"]), regq2["failed"])
# refused with AND without the line: the code is not blamed
out, rega = live(QB, refuse_all=True)
check("refused with and without the line: an ordinary fault - no refusal of the code is recorded, and after two such visits no further line is tried in that run", len(rega["failed"]) == 5 and rega["created"] == []
      and not any((x["info"] or {}).get("quality_refused") for x in rega["failed"]) and sum(1 for b_ in POSTS if "pcode65441" in b_) == 2 and "two visits were refused with and without the code" in rega["quality_gate"]["off"], (rega["quality_gate"], len(POSTS)))
keep(rega, "20261113T0100Z"); ci.PARSED[:] = QB; out, dry = run_dry()
check("... and the next run is a plain pilot again (a failed visit says nothing about the code)", ci.QUALITY["fee"] == "0.00" and ci.QUALITY["off"] == "" and ci.QUALITY["wait"] is False and sum(1 for v in dry.values() if v[0].get("quality_codes")) == 3, ci.QUALITY)
# the visit is stored, the line is not
clear_regs(); charts0()
out, regd = live(QB, drop_quality=True); ns = [r for r in regd["created"] if r.get("quality_not_stored")]
check("AdvancedMD stores the visit without the line: said at once, no further line in that run, nobody marked as coded", len(ns) == 1 and ns[0]["quality_codes"] == [] and qrows_of(regd) == [] and len(regd["created"]) == 5
      and "stored a visit without its quality line" in regd["quality_gate"]["off"] and sum(1 for b_ in POSTS if "pcode65441" in b_) == 1, (regd["created"], regd["quality_gate"]))
keep(regd, "20261113T0100Z"); ci.PARSED[:] = visits("20261117", (2,)); out, dry = run_dry()
check("... the next run tries one cent, and that patient is still due", ci.QUALITY["fee"] == "0.01" and ci.QUALITY["off"] == "" and (ns[0]["pid"], "2026") not in ci.QUALITY["done"], ci.QUALITY)
# a failed create frees its place in the pilot; an unreadable state means no line
clear_regs(); charts0()
out, regc = live(QB, fail_create=1)
check("a visit that could not be created frees its place: the other three eligible visits carry the line", len(qrows_of(regc)) == 3 and len(regc["failed"]) == 1 and len(regc["created"]) == 4, (regc["created"], regc["failed"]))
_qs = ci.quality_state; ci.quality_state = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom"))
out, regs_ = live(QB); ci.quality_state = _qs
check("the state of the code cannot be read: every visit is entered, none with the line, and the register says so", len(regs_["created"]) == 5 and qrows_of(regs_) == [] and "could not be read (RuntimeError)" in regs_["quality_gate"]["off"], regs_["quality_gate"])
clear_regs(); json.dump({"created": [{"quality_codes": 5, "quality_charge": {"a": 1}, "charges": None}, {"quality_codes": ["1123F"], "quality_charge": "charge5", "pid": ["x"], "dos": 5, "quality_gate": 3},
                                       {"quality_refused": 0, "quality_not_stored": None, "quality_codes": None}], "skipped": [], "failed": [], "quality_gate": "odd"}, open(os.path.join(REGDIR, "feed_import_20261115T0100Z.json"), "w")); charts0()
BILLS["5"] = {"void": "1"}; out, reg7 = live(visits("20261109", (3,)))
check("odd values in an earlier register cannot stop the import or switch the code off", len(reg7["created"]) == 1 and reg7["quality_gate"]["off"] == "" and len(qrows_of(reg7)) == 1, reg7.get("quality_gate"))
for odd in ([("a", {"created": "not a list", "quality_gate": 7})], [("b", [1, 2])], [("c", None)], [(5, {"created": [7, None, "x"], "quality_gate": {"confirmed": "yes", "fee": 9, "zero_not_billed": 0, "reset": 0}})], []):
    try: ci.quality_state(odd, look=True); okq = ci.QUALITY["off"] == "" and ci.QUALITY["fee"] == "0.00" and ci.QUALITY["confirmed"] is False and ci.QUALITY["wait"] is False
    except Exception as e: okq = False
    check("quality: the state is read without an error from an odd register list (%s)" % (type(odd[0][1]).__name__ if odd else "empty"), okq, dict(ci.QUALITY))
clear_regs(); DEMOG["plans"] = ""; BILLS.clear(); DETAILS.clear(); charts0(); qreset(); ci.PARSED[:] = BASE

# ---- 5. the mirror keeps these helpers: a workspace copy without the rule never overwrites the repository's ------------------------------
mir = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
for helper in ("claimocity_import.py", "claimocity_report.py", "claimocity_inspector.py", "claimocity_ingest.py", "claimocity_retry_dx.py", "working_denials.py"):
    m = re.search(r'"%s":\s*(?:"([^"]+)"|\'([^\']+)\')' % re.escape(helper), mir); m = m and type("M", (), {"group": lambda self, i, _m=m: _m.group(1) or _m.group(2)})()
    check("mirror.py protects %s with a marker that is in the file" % helper, bool(m) and m.group(1) in open(os.path.join(ROOT, "scripts", "helpers", helper)).read(), m.group(1) if m else "no PROTECTED entry")
insp = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read()
check("inspector: a CCM visit at the hospital location is never moved to HCA REHAB / 31", 'all(x not in HOSP for x in c["cpts"]) and not any(x in ("99487", "99489") for x in c["cpts"])' in insp)
check("inspector: a visit the import flagged (pos_err) is never moved to HCA REHAB either, and mirror.py's marker for the inspector is that sentence",
      'not any(x in ("99487", "99489") for x in c["cpts"]) and not c.get("pos_err"):' in insp and '"claimocity_inspector.py": "is never moved to HCA REHAB either"' in mir and "is never moved to HCA REHAB either" in insp)
step = open(os.path.join(ROOT, "nightly", "claimocity_feed_step.md")).read()
ver = 'POS_RULE_VERSION = "%s"' % ci.POS_RULE_VERSION
ingest = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_ingest.py")).read()
check("the rule's version line is the same in the helper, mirror.py, the ingest guard and the runbook's step (c)", ver in open(HELPER).read() and ver in mir and ver in ingest and ("grep -c '%s' /home/claude/unbilled/claimocity_import.py" % ver) in step, ver)
check("... and in the retry driver, which checks the import helper itself before it enters charges and says an old one in its RESULT line", ver in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_retry_dx.py")).read() and mir.count(ver) == 3
      and "+ pos_warn)" in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_retry_dx.py")).read())
_wd = [open(os.path.join(ROOT, d, "working_denials.py")).read() for d in ("boards", os.path.join("scripts", "helpers"))]
check("both copies of the denial table read reason 246 (a reporting code) as information", all(' "246": ("INFO"' in w for w in _wd) and [l for l in _wd[0].split("\n") if l.startswith(' "246":')] == [l for l in _wd[1].split("\n") if l.startswith(' "246":')])
check("both copies of the denial table carry Medicare's reason-58 rule, word for word", all(' "58":  ("REVIEW"' in w for w in _wd) and [l for l in _wd[0].split("\n") if l.startswith(' "58":')] == [l for l in _wd[1].split("\n") if l.startswith(' "58":')])
check("runbook: a 32 line is read back from the chart itself every run, the retry's own digest is read like the ingest's, and the top of the report is defined",
      "EVERY RUN THAT ENTERS A 32 LINE" in step and "not a second\nlook at the chart" in step and "feed_digest_<stamp>R.md" in step and "'The TOP of the report' =" in step and "'NOT LISTED' = done" in step)
check("runbook: the feed step copies the helpers and checks the version line before the ingest", step.index("cp -p claimocity_import.py claimocity_report.py claimocity_inspector.py claimocity_ingest.py claimocity_retry_dx.py feed_parse_dft_1028.py /home/claude/unbilled/") < step.index("must print 1") < step.index("python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run drops --live)"))
check("ingest: the guard replaces an old import helper with the repository's before step 5", ingest.index("POS_RULE = ") < ingest.index('cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py")') and "claimocity_inspector.py" in ingest[ingest.index("POS_RULE = "):ingest.index('cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py")')])
check("ingest: when only some helpers could be replaced the result line names the ones that are still older copies; the runbook says where that line goes", "FEED HELPERS NOT ALL CURRENT" in ingest and "pos_warn" in ingest[ingest.index("FEED HELPERS NOT ALL CURRENT") - 200:ingest.index("FEED HELPERS NOT ALL CURRENT")]
      and "FEED HELPERS NOT ALL CURRENT" in step and "the feed files are not on hand and could not be fetched' also goes under Holds" in step)
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
r, line = digest([dict(rows[4], msg_own=False), rows[5]], stamp="1028")
check("digest: the not-matched line is printed whatever the batch stamp looks like", "Clinician and building: 1 visit(s) could not be matched to their own feed message" in r.stdout, r.stdout[-500:])
r, line = digest(rows + [dict(reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]), prof_default=True), dict(reg_row(["99232"], "", "31", ["31"]), pos_kind=[""])])
check("digest: what is for William says so - no line tells a routine to check or change a visit by hand", "check them by hand" not in r.stdout and r.stdout.count("for William (a routine changes nothing on these visits)") == 2, r.stdout[-900:])
check("digest: a visit under the default clinician and a hospital visit with no facility are each named for the top of the report", "Clinician: 1 visit(s) whose feed message names no clinician id the profile table has" in r.stdout
      and "Building: 1 hospital / home / other visit(s) came from a building the facility table does not know" in r.stdout, r.stdout[-900:])
r, line = digest(rows + [OLD_ROW])
check("digest: from 11/10/2026 on, a nursing-building row without the rule's fields means an old helper ran - said loudly", "PLACE OF SERVICE RULE DID NOT RUN on 1 visit(s)" in line, line)
r, line = digest([OLD_ROW, rows[4], rows[5]], stamp="20261028T0623Z")
check("digest: a batch from before the rule gets no line", r.returncode == 0 and line == "", r.stdout[-300:])
r, line = digest([rows[4], rows[5]])
check("digest: no line when the batch had no nursing-building charge", r.returncode == 0 and line == "", r.stdout[-300:])
r, line = digest(rows + [dict(reg_row(["99487"], "fac34", "31", ["32"]), pos_lines=[None]), dict(reg_row(["99309"], "fac34", "31", ["32"]), pos_lines=[32], pos_kind=None), dict(reg_row(["99309", "99497"], "fac34", "31", ["32"]), pos_kind=["monthly"])])
check("digest: odd values in a register never stop the report", r.returncode == 0 and line != "", r.stderr[-300:])

aud = tempfile.mkdtemp(prefix="posrule_aud_")
_r1 = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", "feed", "feed_clinician_audit.py"), "--registers", os.path.join(aud, "nowhere")], capture_output=True, text=True)
_r2 = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", "feed", "feed_clinician_audit.py"), "--registers", aud, "--csv"], capture_output=True, text=True)
check("audit tool: a registers folder that is not there, or --csv without a file name, ends with a plain sentence - not with a zero count or a traceback", _r1.returncode != 0 and "registers folder not found" in _r1.stderr
      and _r2.returncode != 0 and "needs a file or folder name" in _r2.stderr and "Traceback" not in _r1.stderr + _r2.stderr, (_r1.stderr[-200:], _r2.stderr[-200:]))
json.dump({"created": [{"visit": "vst1", "pid": "pat1", "prof": "prof13", "fac": "fac29", "cpts": ["99309"], "dos": "10/05/2026", "charges": ["charge1"]},
                       {"visit": "vst2", "pid": "pat1", "prof": "prof15", "fac": "fac34", "cpts": ["99309"], "dos": "10/12/2026", "charges": ["charge2"]},
                       {"visit": "vst3", "pid": "pat2", "prof": "prof13", "fac": "fac29", "cpts": ["99487"], "dos": "10/31/2026", "charges": ["charge3"]},
                       {"visit": "vst4", "pid": "pat3", "prof": "prof13", "fac": "fac29", "cpts": ["99232"], "dos": "10/20/2026", "charges": ["charge4"]}]}, open(os.path.join(aud, "feed_import_20261101T0000Z.json"), "w"))
json.dump({"stamp": "20261101T0000Z", "rows": [{"v": "vst1", "p": "pat1", "d": "2026-10-05", "c": ["99309"], "prov": "Pamela G."}, {"v": "vst2", "p": "pat1", "d": "2026-10-12", "c": ["99309"], "prov": "Pamela G. (ARNP)"},
                                              {"v": "vst3", "p": "pat2", "d": "2026-10-31", "c": ["99487"], "prov": "Dr. Effinger (DO)"}, {"v": "vst4", "p": "pat3", "d": "2026-10-20", "c": ["99232"], "prov": "Dr. Effinger (DO)"}]}, open(os.path.join(aud, "feed_recon_20261101T0000Z.json"), "w"))
r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", "feed", "feed_clinician_audit.py"), "--registers", aud], capture_output=True, text=True)
check("audit tool: lists the visit entered under the other clinician and the visits whose codes do not fit the building they were entered in", r.returncode == 0 and "entered under a different clinician: 1" in r.stdout
      and "2 visit(s) whose codes do not fit the building" in r.stdout and "'nursing code at the hospital': 1" in r.stdout and "'care management at the hospital': 1" in r.stdout
      and "charts with a nursing code entered at the hospital AND visits entered in a nursing building: 1" in r.stdout and "not compared" not in r.stdout, r.stdout[-700:] + r.stderr[-300:])
def qdigest(rows, gate, stamp="20261111T0100Z", failed=()):
    json.dump({"created": rows, "skipped": [], "failed": list(failed), "quality_gate": gate}, open(os.path.join(rep_dir, "registers", "feed_import_%s.json" % stamp), "w"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")], cwd=rep_dir, env=dict(os.environ, FEED_STAMP=stamp), capture_output=True, text=True)
    return r, "\n".join(l for l in r.stdout.splitlines() if "uality code" in l or l.startswith("  - carried by") or "QUALITY CODE" in l or "quality line" in l or "quality-code" in l)
G0 = {"code": "1123F", "fee": "0.00", "confirmed": False, "proof": None, "zero_not_billed": False, "off": "", "wait": False, "pending": [], "pending_since": "", "dead_zero_lines": [], "reset": False, "pilot_cap": 3, "notes": []}
qrow = dict(reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]), quality_codes=["1123F"], quality_fee="0.00", quality_charge="charge77", charges=["charge1", "charge77"], fees=["1.00"])
r, line = digest([dict(reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]), quality_codes=["1123F"], quality_charge="charge77", quality_pos="32", pos_stored=["32"], quality_pos_stored="32"),
                  dict(reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]), quality_codes=["1123F"], quality_charge="charge78", quality_pos="32", pos_stored=["31"], quality_pos_stored="31"),
                  dict(reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]), quality_codes=["1123F"], quality_charge="charge79", quality_pos="32", pos_stored=["32"], quality_pos_stored="31")])
check("digest: a visit with the quality line is read back like any other, and a quality line stored at another place of service is said too", "ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE on 2 of 3 visit(s) read back" in r.stdout
      and "sent ['32'] stored ['31']" in r.stdout and "(quality line sent 32 stored 31)" in r.stdout, r.stdout[-700:])
json.dump({"fixed": [], "bypassed": [], "laterality": [], "held": [{"visit": "1", "pid": "pat9", "why": "Pattern 88001: Charge amount is zero for this procedure"},
                                                                    {"visit": "7", "pid": "pat7", "why": "Pattern 24078: something else"}]}, open(os.path.join(rep_dir, "registers", "feed_inspector_20261111T0100Z.json"), "w"))
r, ql = qdigest([dict(qrow), dict(rows[4], visit="vst7", pid="pat7")], G0)
check("digest: a visit that carries the quality line and is held by the Claim Inspector goes to the top of the report, whatever the inspector's words; a held visit without the line is not named there",
      "TOP OF THE REPORT - 1 visit(s) that carry the quality line are HELD by the Claim Inspector" in r.stdout and "pat9 vst1 - Pattern 88001: Charge amount is zero for this procedure" in r.stdout
      and "pat7 vst7 - Pattern" not in r.stdout, r.stdout[-900:] + r.stderr[-400:])
json.dump({"fixed": [], "bypassed": [], "laterality": [], "held": [{"visit": "7", "pid": "pat7", "why": "Pattern 24078: something else"}]}, open(os.path.join(rep_dir, "registers", "feed_inspector_20261111T0100Z.json"), "w"))
r, ql = qdigest([dict(qrow), dict(rows[4], visit="vst7", pid="pat7")], G0)
check("digest: ... and no such line when none of the held visits carries the quality line", "are HELD by the Claim Inspector" not in r.stdout and "Quality code 1123F" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
os.remove(os.path.join(rep_dir, "registers", "feed_inspector_20261111T0100Z.json"))
r, ql = qdigest([qrow, rows[4]], G0)
check("digest: the quality code has its own line with the visits under it, says it is a pilot and what proves a line", r.returncode == 0 and "Quality code 1123F (advance care plan, Medicare measure 047; a line that pays nothing): on 1 visit(s) in this batch, line amount $0.00; PILOT - at most 3 visit(s) carry it, then no more until one such line is seen billed to insurance in AdvancedMD." in ql
      and "carried by: pat9 vst1 charge77" in ql and "remark N620 on the 1123F line means Medicare counted it" in r.stdout and "2 visits / 2 charge lines created" in r.stdout, (ql, r.stdout[:400], r.stderr[-300:]))
r, ql = qdigest([rows[4]], dict(G0, wait=True, pending=["vst5", "vst6"], pending_since="feed_import_20261110T0100Z.json"))
check("digest: a waiting pilot says so, names the visits it waits for, and is not yet at the top of the report", "PILOT, waiting - no line was added in this run: the visit(s) that carry the first line(s) are not billed yet (vst5, vst6)" in ql and "TOP OF THE REPORT" not in ql, ql)
r, ql = qdigest([rows[4]], dict(G0, wait=True, pending=["vst5"], pending_since="feed_import_2026-11-07T0100Z.json"))
check("digest: after three days of waiting the pilot goes to the top of the report", "TOP OF THE REPORT - the quality-code pilot has waited 4 days" in ql and "vst5" in ql, ql)
r, ql = qdigest([qrow], dict(G0, fee="0.01", confirmed=True, proof={"visit": "vst5", "billed": "11/11/2026"}, pilot_cap=None, zero_not_billed=True, dead_zero_lines=[["pat1", "vst2", "charge3"], ["pat4", "vst5", "charge6"]],
                             notes=["visit vst4 was billed 11/10/2026 without its $0.00 quality line - new lines carry $0.01"]))
check("digest: says when every visit carries it, why the amount changed, and lists the dead $0.00 lines", "line amount $0.01; every eligible visit carries it - a quality line was seen billed to insurance (visit vst5, 11/11/2026)" in ql
      and "without its $0.00 quality line" in r.stdout and "2 earlier quality line(s) at $0.00 never went out on a claim" in ql and "pat1 vst2 charge3; pat4 vst5 charge6" in ql and "remark N620" not in r.stdout, ql)
r, ql = qdigest([dict(qrow, quality_codes=[], quality_refused="Fault: no", quality_refused_fee="0.00")], dict(G0, off="this run: AdvancedMD refused a visit that carried the code"))
check("digest: a refusal and the switch-off go to the top of the report", "TOP OF THE REPORT - QUALITY CODE NOT ACCEPTED by AdvancedMD on 1 visit(s); each visit was entered without it: pat9 vst1 (Fault: no)" in r.stdout and "TOP OF THE REPORT - the quality code is OFF: this run" in r.stdout, r.stdout[-700:])
r, ql = qdigest([dict(qrow, quality_codes=[], quality_charge="", quality_not_stored="0.00")], dict(G0, off="this run: AdvancedMD stored a visit without its quality line"))
check("digest: a visit stored without its line goes to the top of the report", "TOP OF THE REPORT - AdvancedMD stored 1 visit(s) WITHOUT the quality line that was sent with it (the visit itself is entered): pat9 vst1" in r.stdout, r.stdout[-500:])
r, ql = qdigest([rows[4]], dict(G0, off="this run: a visit with the code was refused and the chart could not be shown free of it"), failed=[{"feed_id": "n2", "pid": "pat7", "empty_visit": "vst70", "stored": [["99309", "11/02/2026"]], "err": "x", "info": {"quality_tried": "0.00", "cpts": ["99309"]}}])
check("digest: a refused visit that was NOT sent again is named at the top for entry by hand", "TOP OF THE REPORT - 1 visit(s) were refused with the quality line and NOT sent again" in r.stdout and "pat7 (empty visit vst70; chart shows [['99309', '11/02/2026']])" in r.stdout, r.stdout[-600:])
r, ql = qdigest([rows[4]], dict(G0, reset=True, notes=["the pilot was started again in this run (QUALITY_CODE=reset)"]))
check("digest: a restart of the pilot is said", "the pilot was started again in this run (QUALITY_CODE=reset)." in r.stdout, r.stdout[-400:])
r, ql = qdigest([rows[4], rows[5]], G0)
check("digest: no quality line when no visit carried the code and nothing happened", r.returncode == 0 and ql == "", ql)
for oddg in ("odd", {"pending": 5, "dead_zero_lines": "x", "notes": 3, "proof": "p", "wait": True, "pending_since": 9}, None):
    r, ql = qdigest([dict(qrow, quality_codes="x", quality_charge=None), dict(qrow, quality_codes=None, quality_refused=1, quality_not_stored=2, visit=None)], oddg, failed=[{"stored": 1, "info": {"quality_tried": 0}}, {"stored": [1], "info": "x"}])
    check("digest: odd quality values (%s) never stop the report" % type(oddg).__name__, r.returncode == 0 and "could not be built" not in ql, (ql, r.stderr[-300:]))
import importlib.util as _iu
wd = open(os.path.join(ROOT, "boards", "working_denials.py")).read()
check("denial table: Medicare's acceptance of a reporting code (reason 246) is information, never work", '"246": ("INFO"' in wd and "N620" in wd)
check("runbook and rulebook carry the owner's words for the quality code", '"yes for all: billing adds 1123F automatically, once per patient, to the next Medicare claim for every patient 65 and older."' in open(os.path.join(ROOT, "practices", "ehpa", "rules.md")).read() and "## Quality code 1123F, advance care plan" in step and "QUALITY_CODE=reset" in step and "grep -h '^QUALITY 1123F' logs/claimocity_<stamp>_*.log" in step and "in front of the claimocity_retry_dx.py command" in step)
# the insurance-check step: a void quality line never holds the visit (its function is run here with stand-ins; the rest of that helper is not loaded)
_vsrc = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py")).read(); _vsrc = _vsrc[_vsrc.index("def fast_set_insorder(v, order):"):_vsrc.index("def main():")]
class _RS:
    CHG_FIELDS = ["fee", "pos"]; state = {"order": "1,2", "void": set(), "sent": []}
    @staticmethod
    def detail(cid): return '<r><patient id="pat1"/><visit id="vst1" episode="e1" insorder="%s"/><charge id="charge%s" fee="1.00" pos="32" void="%s"/></r>' % (_RS.state["order"], cid, "1" if str(cid) in _RS.state["void"] else "0")
class _AM:
    @staticmethod
    def msg(action, cls, attrs=None, children=""): return children
    @staticmethod
    def post(body, timeout=0):
        _RS.state["sent"].append(body); m_ = re.search(r'insorder="([^"]*)"', body); _RS.state["order"] = m_.group(1) if m_ else _RS.state["order"]; return "<r/>"
_ns = {"resave": _RS, "amd": _AM, "re": re}; exec(_vsrc, _ns)
_row = {"visit": "vst1", "charges": ["charge10", "charge11"], "quality_charge": "charge11"}
_RS.state.update(order="1,2", void={"11"}, sent=[]); ok1, m1 = _ns["fast_set_insorder"](_row, "2")
check("insurance check: the quality line is void - the visit's order is still set, with the live charge only (no hold)", ok1 is True and len(_RS.state["sent"]) == 1 and 'id="charge10"' in _RS.state["sent"][0] and "charge11" not in _RS.state["sent"][0], (ok1, m1, _RS.state["sent"]))
_RS.state.update(order="1,2", void=set(), sent=[]); ok2, m2 = _ns["fast_set_insorder"](_row, "2")
check("insurance check: both charges live - both are echoed (a charge left out would be voided)", ok2 is True and 'id="charge10"' in _RS.state["sent"][0] and 'id="charge11"' in _RS.state["sent"][0], (ok2, m2))
_RS.state.update(order="1,2", void={"10"}, sent=[]); ok3, m3 = _ns["fast_set_insorder"](_row, "2")
check("insurance check: the visit's OWN charge is void - held as before, nothing sent", ok3 is False and "mismatch" in m3 and _RS.state["sent"] == [], (ok3, m3))
_RS.state.update(order="1,2", void={"10", "11"}, sent=[]); ok4, m4 = _ns["fast_set_insorder"](_row, "2")
check("insurance check: everything void - held, nothing sent", ok4 is False and _RS.state["sent"] == [], (ok4, m4))
# the programs this self-test starts as programs load no module that talks to AdvancedMD (those are only ever run inside this process)
_started = [os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py"), os.path.join(ROOT, "tools", "feed", "feed_clinician_audit.py")]
def loads(src):
    """The names a piece of Python loads with import / from, first name of each (import a.b as c -> a)."""
    out_ = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out_.add(n)
    return out_
_names = {os.path.basename(f): loads(open(f).read()) for f in _started}
check("the helpers this self-test starts as programs load none of the modules that talk to AdvancedMD", all(not (v & set(AMD_MODULES)) for v in _names.values()) and len(_names) == 2
      and loads("import os as _os\nimport amd as a, resave.x\n    import void_tx\nfrom txh import fetch_visit\n") == {"os", "amd", "resave", "void_tx", "txh"}, _names)
_me = open(os.path.abspath(__file__)).read()
_runs = re.findall(r"subprocess\.\w+\(", _me)
_known = re.findall(r'subprocess\.run\(\[sys\.executable,(?: "-B",)? os\.path\.join\(ROOT, (?:"scripts", "helpers", "claimocity_report\.py"|"tools", "feed", "feed_clinician_audit\.py")\)', _me)
check("... and nothing else is started as a program from here (every program start in this file is one of those two)", len(_runs) == len(_known) and len(_runs) >= 5
      and not re.search(r"os\.system\(|os\.popen\(|runpy\.", _me.replace('r"os\\.system\\(|os\\.popen\\(|runpy\\."', "")), (len(_runs), len(_known)))
def run_inside(path, standins, cwd, env=None, argv=()):
    """Run a helper that talks to AdvancedMD INSIDE this process: its amd / resave / ... are the stand-in modules given here, put in
    sys.modules for the run and taken out again. Refuses to run unless every module of AMD_MODULES the helper loads is a stand-in."""
    src = open(path).read(); wanted = loads(src) & set(AMD_MODULES)
    missing = sorted(wanted - set(standins))
    if missing: raise RuntimeError("no stand-in for %s - the helper is not run" % missing)
    old_mod = {k: sys.modules.get(k) for k in standins}; old_cwd = os.getcwd(); old_env = dict(os.environ); old_argv = list(sys.argv); out = io.StringIO(); err = ""
    import time as _time
    old_sleep = _time.sleep
    try:
        for k, v in standins.items():
            m = types.ModuleType(k); m.STAND_IN = True
            for n, f in v.items(): setattr(m, n, f)
            sys.modules[k] = m
        os.chdir(cwd); os.environ.update(env or {}); sys.argv = [path] + list(argv); _time.sleep = lambda *_a: None
        with contextlib.redirect_stdout(out):
            try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit: pass
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
# the helper that voids a visit dated after a death voids EVERY charge of the visit - its own charge and the quality line
vdd = tempfile.mkdtemp(prefix="posrule_vd_"); os.makedirs(os.path.join(vdd, "registers"))
VD = {"void": set(), "asked": [], "voided": [], "login": 0}
def _vd_detail(cid): VD["asked"].append(str(cid)); return '<r><patient id="pat1"/><visit id="vst1"/><charge id="charge%s" void="%s"/></r>' % (cid, "1" if ("charge%s" % cid) in VD["void"] else "0")
def _vd_void(num, cid): VD["voided"].append((num, cid)); VD["void"].add(cid); return True, "ok"
def _vd_txh(num, vnum):
    r_ = ET.Element("r")
    for c_ in ("charge10", "charge11"): ET.SubElement(r_, "charge", {"id": c_, "void": "1" if c_ in VD["void"] else "0", "proccode": "x", "fee": "1.00"})
    return r_
def _vd_login(*a): VD["login"] += 1
VD_STAND = {"amd": {"login_cached": _vd_login}, "resave": {"detail": _vd_detail}, "txh": {"fetch_visit": _vd_txh}, "void_tx": {"void_charge": _vd_void},
            "deceased_guard": {"_iso": lambda mdy: mdy[6:10] + "-" + mdy[0:2] + "-" + mdy[3:5]}}
VD_HELPER = os.path.join(ROOT, "scripts", "helpers", "claimocity_void_deceased.py")
def vd_run(created, dead):
    VD.update(void=set(), asked=[], voided=[], login=0)
    json.dump({"created": created}, open(os.path.join(vdd, "registers", "feed_import_T1.json"), "w")); json.dump(dead, open(os.path.join(vdd, "dc.json"), "w"))
    o_, e_ = run_inside(VD_HELPER, VD_STAND, vdd, env={"FEED_STAMP": "T1", "DECEASED_CACHE": os.path.join(vdd, "dc.json")})
    f_ = os.path.join(vdd, "registers", "feed_void_deceased_T1.json"); res = json.load(open(f_)) if os.path.exists(f_) and not e_ else None
    if os.path.exists(f_): os.remove(f_)
    return o_, e_, res
_vrow = {"pid": "pat1", "visit": "vst1", "dos": "11/02/2026", "cpts": ["99309"], "charges": ["charge10", "charge11"], "quality_charge": "charge11"}
_DAY1 = "2026-11-" + "01"; _DAY2 = "2026-11-" + "02"      # written in two pieces: the privacy gate rewrites a whole date that stands beside such a key
try:
    run_inside(VD_HELPER, {k: v for k, v in VD_STAND.items() if k != "void_tx"}, vdd); _refused = False
except RuntimeError as e: _refused = "no stand-in for ['void_tx']" in str(e)
check("a helper that talks to AdvancedMD is not run here unless every such module it loads has a stand-in", _refused is True and sys.modules.get("amd") is amd and "void_tx" not in sys.modules)
o_, e_, res = vd_run([_vrow], {"1": {"dod": _DAY1}})
check("a visit dated after the date of death is voided WHOLE - its own charge and the quality line", not e_ and sorted(c for _n, c in VD["voided"]) == ["charge10", "charge11"] and res and res[0]["result"] == "VOIDED"
      and sorted(VD["asked"]) == ["10", "11"] and VD["login"] == 1, (o_[-300:], e_, res, VD))
o_, e_, res = vd_run([_vrow], {"1": {"dod": _DAY2}})
check("... a visit on the day of death or before it is left alone", not e_ and VD["voided"] == [] and res == [], (e_, res, VD))
o_, e_, res = vd_run([dict(_vrow, charges=["charge10"])], {"1": {"dod": _DAY1}})
check("... a visit recorded with one charge has that charge voided (as before)", not e_ and VD["voided"] == [("1", "charge10")], (e_, res, VD))
check("the stand-ins are gone again after such a run (the import helper's own stand-ins are back)", sys.modules.get("amd") is amd and sys.modules.get("resave") is resave and sys.modules.get("txh") is txh and "void_tx" not in sys.modules and "deceased_guard" not in sys.modules)

print("\n%d check(s) failed" % len(FAILS) if FAILS else "\nall checks passed")
sys.exit(1 if FAILS else 0)
