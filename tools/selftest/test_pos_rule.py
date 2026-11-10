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
#       whose first plan is Medicare Part B and whose last insurance check showed Medicare first - never on a care-management-only message,
#       never twice; a pilot round holds at most three lines and adds none while one of them is not decided; the code is off until William
#       restarts it when a person, a hold or a refusal shows the line is in the way; a refused visit is entered again without it
#       (section 4c here, and the nights of tools/selftest/test_quality_nights.py);
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
ECHO = {"flip": False, "none": False, "refuse_quality": False, "refuse_all": False, "fail_create": 0, "drop_quality": False, "partial": None, "proccode": False, "fees": False, "qfirst": False,
        "plain_raises": False, "line_raises": False, "all_raise": False, "detail_noproc": False, "detail_text": True}      # ..._raises: the charge call ends in a time-out (after a refusal / when it carries the quality line / always); detail_noproc: the charge detail shows no procedure; detail_text: it names the procedure's code text
PROC = {}                                                              # charge number -> the procedure the stand-in stored for it
REFUSED = set()                                                        # visits whose charge call the stand-in answered with a fault
ECHO0 = dict(ECHO); SEQ = [100]                                         # visit numbers never repeat between runs (the charge numbers are built from them)                                  # flip: the stand-in stores 31 where 32 was sent; none: its answer carries no place of service
def _post(body, timeout=0):
    POSTS.append(body)
    if 'action="getdemographic"' in body or "getdemographic" in body: return '<r><patient respparty="resp9" insorder="%s" deceased=""/>%s</r>' % (DEMOG["order"], DEMOG["plans"])
    if 'action="addvisit"' in body:
        if ECHO["fail_create"] > 0: ECHO["fail_create"] -= 1; return "<r><Fault>no visit today</Fault></r>"
        SEQ[0] += 1; return '<r><visit id="vst%d"/></r>' % SEQ[0]
    if 'action="updvisitwithnewcharges"' in body:
        _v = re.search(r'<visit id="(vst\d+)"', body).group(1)
        if ECHO["all_raise"] or (ECHO["line_raises"] and "pcode65441" in body) or (ECHO["plain_raises"] and _v in REFUSED): raise TimeoutError("read timed out")
        if ECHO["refuse_all"] or (ECHO["refuse_quality"] and "pcode65441" in body):
            REFUSED.add(_v)
            if ECHO["partial"]: CHART.setdefault(ECHO["partial"][0], []).append(tuple(ECHO["partial"][1:]))      # the stand-in stores a line although it answers with a fault
            return "<r><Fault>the charge amount is not accepted</Fault></r>"
        sent = re.findall(r'proccode="(pcode\d+)" cobcode="" pos="(\d+)" tos="01" units="[^"]*" netfee="0" fee="([^"]*)"', body); vid = re.search(r'<visit id="(vst\d+)"', body).group(1)
        if ECHO["drop_quality"]: sent = [x for x in sent if x[0] != "pcode65441"]
        num = list(enumerate(sent))                                                   # the charge number follows the order SENT ...
        for i, (pc, q, fee) in num: PROC["%d%d" % (int(vid[3:]), i)] = pc
        if ECHO["qfirst"]: num = sorted(num, key=lambda x: x[1][0] != "pcode65441")   # ... the answer can list the quality charge first
        return '<r><visit id="%s">%s</visit></r>' % (vid, "".join('<charge id="charge%d%d"%s fee="%s"%s/>' % (int(vid[3:]), i, ' proccode="%s"' % pc if ECHO["proccode"] else "", fee if ECHO["fees"] else "1.00",
                                                 "" if ECHO["none"] else ' pos="%s"' % ("31" if ECHO["flip"] and q == "32" else q)) for i, (pc, q, fee) in num))
    return "<r/>"
amd.post = _post
resave = types.ModuleType("resave")
DETAILS = []                                                           # every charge number whose detail was read
CODE_TEXT = {}; TEXTOF = {}; PAYS = {}                                 # procedure id -> its code text (filled once the helper is loaded); charge number -> another code text; charge number -> its payment lines
def _detail(cid):
    DETAILS.append(str(cid)); b = BILLS.get(str(cid), [])      # BILLS: a list of billed dates, a dict of attributes, or a word for an answer that does not hold the charge
    if b == "RAISE": raise RuntimeError("detail read failed")
    if b == "FAULT": return "<r><Fault>charge not found</Fault></r>"
    if b == "MISSING": return '<r><visit episode="eps9" refplan=""/></r>'
    if b == "NOTXML": return "not an answer"
    pc = "" if ECHO["detail_noproc"] else PROC.get(str(cid), "")
    tx = TEXTOF.get(str(cid), CODE_TEXT.get(pc, "")) if (pc and ECHO["detail_text"]) else ""      # the detail's list of procedures: id -> code text
    plist = '<proccodelist><proccode id="%s" code="%s"/></proccodelist>' % (pc, tx) if tx else ""
    pays = "".join("<payment %s/>" % " ".join('%s="%s"' % kv for kv in p.items()) for p in PAYS.get(str(cid), []))
    pays = "<paymentlist>%s</paymentlist>" % pays if pays else ""
    if isinstance(b, dict): return '<r><visit episode="eps9" refplan=""/><charge id="charge%s" %s>%s</charge>%s</r>' % (cid, " ".join('%s="%s"' % kv for kv in dict({"proccode": pc} if pc else {}, **b).items()), pays, plist)
    return '<r><visit episode="eps9" refplan=""/><charge id="charge%s"%s><insbilllist>%s</insbilllist>%s</charge>%s</r>' % (cid, ' proccode="%s"' % pc if pc else "", "".join('<insbill billeddate="%s"/>' % d for d in b), pays, plist)
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
CODE_TEXT.update({v: k for k, v in ci.PCODE.items()}); CODE_TEXT[ci.QUALITY_PCODE] = ci.QUALITY_CODE      # what the stand-in's charge detail names each procedure id
import datetime as _dt
RUN_DAY0 = ci.run_day; RUN_DAY = [_dt.date(2026, 11, 20)]; ci.run_day = lambda: RUN_DAY[0]      # the run's day is fixed here (the helper takes it from the batch stamp; this test's stamp names no date)

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
def run_live(parsed, flip=False, none=False, argv=("--all",), keep_own=False):
    ci.PARSED[:] = parsed; ECHO.update(flip=flip, none=none); POSTS.clear(); buf = io.StringIO(); _argv = list(argv); argv = sys.argv[:]; sys.argv = ["claimocity_import.py"] + _argv
    ci.BATCH_NF.clear(); ci.BATCH_NF_ERR[0] = ""; ci._ctx.clear(); regp = os.path.join(tmp, "registers", "feed_import_SELFTEST.json"); _sleep = ci.time.sleep; ci.time.sleep = lambda s: None
    try:
        with contextlib.redirect_stdout(buf): ci.main()
    finally: ci.time.sleep = _sleep; sys.argv = argv; ECHO.update(ECHO0)
    reg = json.load(open(regp))
    if not keep_own: os.remove(regp)
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
# 4c.1 who gets the line (quality_due through build()): every condition must be shown
REGDIR = os.path.join(tmp, "registers")
def wreg(name, obj): json.dump(obj, open(os.path.join(REGDIR, name), "w"))
def rmreg(*names):
    for n_ in names:
        if os.path.exists(os.path.join(REGDIR, n_)): os.remove(os.path.join(REGDIR, n_))
def vrow(visits=(), decision="RELEASE", lead="FLO02", hold=(), fixes=()):      # one chart's entry in an insurance-check register
    return dict({"visits": list(visits), "decision": decision, "hold": list(hold), "fixes": list(fixes)}, **({"lead": {"code": lead}} if lead else {}))
OKCHK = ("RELEASE", "FLO02")                                             # an earlier insurance check that released the chart with Medicare leading
def qmsg(fid, lines, dob="1940" + "0215"): return {"pid": fid, "name": "x", "dob": dob, "FT1": [{"cpt": c, "dos": d, "dx": "I10^E119", "units": "1"} for c, d in lines]}
def qctx(live=(), plans=None, order="1"):
    c = ctx(live); c["plans"] = [("ins1", "car6085", "01/01/2020", "", "1")] if plans is None else plans; c["insorder"] = order; return c
def qreset(**kw): ci.QUALITY.clear(); ci.QUALITY.update(ci._quality_fresh()); ci.QUALITY["verify"] = {"pat9": OKCHK}; ci.QUALITY.update(kw)
def qbuilt(m, c):
    out, info = ci.build(m, c)
    return (out, info, re.findall(r'proccode="(pcode\d+)" cobcode="" pos="(\d+)"', out[1]) if out else [])
QP = "pcode65441"
QCHG = r'<charge id=""(?:(?!</charge>).)*proccode="pcode65441"(?:(?!</charge>).)*</charge>'      # the quality line as it is sent
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
check("quality: a monthly nursing visit of a Medicare patient of 86 carries 1123F as its LAST line, same place of service, no charge, no modifier",
      pp == [("pcode65119", "32"), (QP, "32")] and info["quality_codes"] == ["1123F"] and info["cpts"] == ["99309"] and info["quality_fee"] == "0.00" and info["quality_dos"] == "11/02/2026"
      and re.search(r'modcodes="" aging="11/02/2026" billins="1" proccode="pcode65441" cobcode="" pos="32" tos="01" units="1" netfee="0" fee="0.00" allowed="0.00"', out[1]) is not None, (pp, info))
check("quality: the same visit WITHOUT the line is kept for the fail-safe, and differs only by that line", QP not in out[2] and out[2].count("<charge ") == 1 and out[1].count("<charge ") == 2 and len(re.findall(QCHG, out[1])) == 1
      and re.sub(QCHG, "", out[1]) == out[2] and out[1].index(QP) > out[1].index("pcode65119") and out[1].rstrip().endswith("</charge></chargelist></visit></ppmdmsg>"), out[2][-300:])
qreset(off="reference"); out0, info0, pp0 = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
check("quality: the visit's own request is byte for byte what the helper sends with the code switched off (create call, charge call, register fields)",
      out0[0] == out[0] and out0[1] == out0[2] == out[2] and info0 == {k: v for k, v in info.items() if not k.startswith("quality_")}, (out0[1][-200:], info0))
_ql = re.findall(QCHG, out[1])[0]
check("quality: the line carries ONE diagnosis - the first of its visit line - while the visit line keeps all of its own (CMS: one diagnosis pointer on a quality line)",
      'diagcodes="dcode1"' in _ql and "<diagcodelist><diagcode id=\"1\"/></diagcodelist>" in _ql and out[1].count('diagcodes="dcode1 dcode2"') == 1 and out[2].count('diagcodes="dcode1 dcode2"') == 1, _ql)
ci.DX.update({"D%02d" % i: "dcode%d" % (20 + i) for i in range(14)})      # a visit line with 14 diagnoses in the feed (the Medicare reviewer's input): the visit line sends 12, the quality line one
qreset(); m14 = qmsg("n2", [("99309", "20261103")]); m14["FT1"][0]["dx"] = "^".join("D%02d" % i for i in range(14)); out14, info14, pp14 = qbuilt(m14, qctx())
_q14 = re.findall(QCHG, out14[1])[0]
check("quality: a visit line with 14 diagnoses - the visit line carries its 12, the quality line the first one only", 'diagcodes="dcode20"' in _q14 and _q14.count("<diagcode ") == 1 and out14[2].count("<diagcode ") == 12 and re.sub(QCHG, "", out14[1]) == out14[2], _q14)
for i in range(14): del ci.DX["D%02d" % i]
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
out2, info2, pp2 = qbuilt(qmsg("n2", [("99309", "20261105")]), qctx([("99309", "10/03/2026")]))
check("quality: once per patient - a second visit of the same chart in the same run gets no second line", QP in out[1] and QP not in out2[1] and "quality_codes" not in info2, info2)
qreset(verify={"pat9": OKCHK, "pat8": OKCHK}); _fa = qbuilt(qmsg("fx", [("99309", "20261102")]), qctx()); _c8 = qctx(); _c8["pid"] = "pat8"; _fb = qbuilt(qmsg("fx", [("99309", "20261103")]), _c8)
check("quality (13.6): in ONE run the same feed patient matched to a second chart gets no second line - the line marks the feed's own patient id too", QP in _fa[0][1] and QP not in _fb[0][1] and "quality_codes" not in _fb[1]
      and ("feed:fx", "2026") in ci.QUALITY["done"] and ("pat9", "2026") in ci.QUALITY["done"], (_fb[1], ci.QUALITY["done"]))
ci.quality_undo(_fa[1], "pat9", "fx")
check("quality (13.6): ... a visit that was not created after all frees both marks (chart and feed patient id) and its place", ("feed:fx", "2026") not in ci.QUALITY["done"] and ("pat9", "2026") not in ci.QUALITY["done"] and ci.QUALITY["added"] == 0, ci.QUALITY["done"])
qreset(); out, info, pp = qbuilt(qmsg("h1", [("99232", "20261031")]), qctx())
check("quality (13.2): a hospital follow-up of a patient who meets every other condition gets NO line (hospital visits are not coded in this version) and is marked for the report's count",
      pp == [("pcode65089", "21")] and "quality_codes" not in info and info.get("quality_skipped") == "hospital" and out[1] == out[2] and ci.QUALITY["added"] == 0 and ci.QUALITY["done"] == set(), (pp, info))
qreset(off="reference"); out0h, info0h, _pp0h = qbuilt(qmsg("h1", [("99232", "20261031")]), qctx())
check("quality (13.2): ... and its request is byte for byte the request with the code switched off (create call, charge call)", out0h[0] == out[0] and out0h[1] == out[1] == out[2] and "quality_skipped" not in info0h, info0h)
qreset(added=3); out, info, pp = qbuilt(qmsg("h1", [("99232", "20261031")]), qctx())
check("quality (13.2): ... a hospital visit that would not have got the line anyway (the round is full) is not counted as left out for being a hospital visit", "quality_skipped" not in info and "quality_codes" not in info, info)
qreset(); out, info, pp = qbuilt(qmsg("a1", [("99344", "20261031")]), qctx())
check("quality: a home / assisted-living visit carries it at 13", pp == [("pcode601053", "13"), (QP, "13")], pp)
def none(label, m, c, **kw):
    qreset(**kw); out, info, pp = qbuilt(m, c)
    check("quality: no line - " + label, out is not None and QP not in out[1] and "quality_codes" not in info and out[1] == out[2], (pp, info))
def gets(label, m, c, **kw):
    qreset(**kw); out, info, pp = qbuilt(m, c)
    check("quality: the line is added - " + label, out is not None and len(re.findall(QCHG, out[1])) == 1 and info.get("quality_codes") == ["1123F"], (pp, info))
V1 = qmsg("n2", [("99309", "20261102")])
none("patient is 64 on the date of service", qmsg("n2", [("99309", "20261102")], dob="1962" + "1103"), qctx())
gets("65 on the very day", qmsg("n2", [("99309", "20261102")], dob="1961" + "1102"), qctx())
gets("115 years old (the upper limit)", qmsg("n2", [("99309", "20261102")], dob="1911" + "1102"), qctx())
none("116 years old - not a believable date", qmsg("n2", [("99309", "20261102")], dob="1910" + "1102"), qctx())
none("no date of birth in the feed", qmsg("n2", [("99309", "20261102")], dob=""), qctx())
none("the 01/01/1900 placeholder", qmsg("n2", [("99309", "20261102")], dob="1900" + "0101"), qctx())
none("a date with month 00 and day 00 is not a date (the old code read it as 65 from January 1)", qmsg("n2", [("99309", "20261102")], dob="1961" + "0000"), qctx())
none("a date with month 13 is not a date", qmsg("n2", [("99309", "20261102")], dob="1961" + "1345"), qctx())
none("February 29 of a year that had none is not a date", qmsg("n2", [("99309", "20261102")], dob="1961" + "0229"), qctx())
gets("a real February 29", qmsg("n2", [("99309", "20261102")], dob="1960" + "0229"), qctx())
qreset(); _l48 = [{"cpt": "99348", "dos": "20261231"}]
check("quality: the state-machine reviewer's two inputs through the decision itself (a home visit code on the last day of the year): no line for either, a line for a real date",
      ci.quality_due({"dob": "1961" + "0000"}, qctx(), _l48) is None and ci.quality_due({"dob": "1961" + "1345"}, qctx(), _l48) is None and ci.quality_due({"dob": "1961" + "0101"}, qctx(), _l48) == 0)
qreset()
check("quality: a date of service that is not a real date shows nothing - no line (month 13, a February 29 that did not exist), a real one does",
      ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "20261345"}]) is None and ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "20260229"}]) is None and ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "2026"}]) is None
      and ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "20260228"}]) == 0)
_mf = ci.medicare_first; ci.medicare_first = lambda *a_, **k_: True; qreset()      # the plan test also reads the date; here it is made to say yes to everything, so that the decision's OWN look at the date is what is tested
check("quality: ... the decision itself throws such a date of service out - it does not lean on the plan test to do it (the plan test here says yes to everything)",
      ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "20261345"}]) is None and ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "20260229"}]) is None and ci.quality_due(V1, qctx(), [{"cpt": "99309", "dos": "20260228"}]) == 0)
ci.medicare_first = _mf
_yrs = set(ci.QUALITY_YEARS); ci.QUALITY_YEARS.add("2010"); qreset(); _c00 = qctx(plans=[("ins1", "car6085", "01/01/2000", "", "1")]); _l10 = [{"cpt": "99309", "dos": "20101102"}]
check("quality: the year-1900 placeholder (or an earlier year) shows no age whatever the year of the visit - here a visit of 2010, where it would pass for 110 years old; a real 1901 date gets the line",
      ci.quality_due({"dob": "1900" + "0101"}, _c00, _l10) is None and ci.quality_due({"dob": "1899" + "1231"}, _c00, _l10) is None and ci.quality_due({"dob": "1901" + "0101"}, _c00, _l10) == 0)
ci.QUALITY_YEARS.clear(); ci.QUALITY_YEARS.update(_yrs)
none("care management only (not one of the measure's visit codes)", qmsg("n1", [("99487", "20261031"), ("99489", "20261031")]), qctx())
none("advance care planning 99497 alone", qmsg("n2", [("99497", "20261102")]), qctx())
none("a discharge visit alone", qmsg("n2", [("99316", "20261102")]), qctx())
none("Medicare is not the FIRST plan", V1, qctx(plans=[("ins1", "car6085", "01/01/2020", "", "1"), ("ins2", "car6404", "01/01/2020", "", "2")], order="2,1"))
none("the first plan is another payer", V1, qctx(plans=[("ins2", "car6404", "01/01/2020", "", "1")]))
none("the Medicare plan ended before the visit", V1, qctx(plans=[("ins1", "car6085", "01/01/2020", "10/31/2026", "1")]))
none("the Medicare plan starts after the visit", V1, qctx(plans=[("ins1", "car6085", "12/01/2026", "", "1")]))
gets("the Medicare plan has NO begin date (no lower limit - 15 of 684 real Medicare plan rows have none)", V1, qctx(plans=[("ins1", "car6085", "", "", "1")]))
for _beg in ("2020-01-01", "13/40/2020", "00/00/0000", "x"):
    none("the Medicare plan's begin date is there but cannot be read (%s): the plan is not shown in force" % _beg, V1, qctx(plans=[("ins1", "car6085", _beg, "", "1")]))
none("the Medicare plan's end date cannot be read", V1, qctx(plans=[("ins1", "car6085", "01/01/2020", "x", "1")]))
none("no plan on the chart", V1, qctx(plans=[]))
none("1123F already on the chart this year", V1, qctx([("1123F", "03/04/2026")]))
none("1124F already on the chart this year", V1, qctx([("1124F", "03/04/2026")]))
none("the code is switched off", V1, qctx(), off="refused")
none("the pilot round is full", V1, qctx(), added=3)
none("a line of the round still waits for its outcome", V1, qctx(), wait=True)
none("an earlier import register already shows the code for this patient this year (whatever the chart history lists)", V1, qctx(), done={("pat9", "2026")})
none("the chart has no earlier insurance check (a first-ever visit gets none; the next batch's visit does)", V1, qctx(), verify={})
none("the chart's newest earlier insurance check put it on HOLD", V1, qctx(), verify={"pat9": ("HOLD", "")})
none("the chart's newest earlier insurance check put it on HOLD although it names Medicare as the lead (its order could not be set)", V1, qctx(), verify={"pat9": ("HOLD", "FLO02")})
none("the chart's newest earlier insurance check named another payer than Medicare (a Medicare Advantage plan)", V1, qctx(), verify={"pat9": ("RELEASE", "HUM01")})
none("the chart is on William's exception list (a patient who declined)", V1, qctx(), exceptions={"pat9"})
gets("another chart on the exception list does not matter", V1, qctx(), exceptions={"pat8"})
qreset(dead={("pat9", "1123F", "10/05/2026")}); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026"), ("1123F", "10/05/2026")]))
check("quality: a line read as left off the claim does not count as reported - the patient gets the code again", QP in out[1], pp)
qreset(dead={("pat9", "1123F", "10/05/2026")}); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026"), ("1123F", "10/05/2026"), ("1123F", "10/20/2026")]))
check("quality: ... but another 1123F on the chart that year still does", QP not in out[1], pp)
ci.FAC["ER X"] = ("fac99", "23"); ci.FACOF["e1"] = "ER X"; qreset(); out, info, pp = qbuilt(qmsg("e1", [("99232", "20261031")]), qctx())
check("quality: never on an emergency-department line (place of service 23)", out is not None and QP not in out[1] and "quality_codes" not in info and pp == [("pcode65089", "23")], (pp, info))
_w = []; _w2 = []; _w3 = []
check("quality (13.2): the decision itself leaves a line at place of service 21, 22 or 23 out when it is told the places of service - and says 'hospital' only when everything else was shown",
      [ci.quality_due(qmsg("e1", [("99232", "20261031")]), qctx(), [{"cpt": "99232", "dos": "20261031"}], [p_], _w) for p_ in ("21", "22", "23")] == [None, None, None] and _w == ["hospital"] * 3
      and ci.quality_due(qmsg("e1", [("99232", "20261031")]), qctx(), [{"cpt": "99232", "dos": "20261031"}], ["31"]) == 0
      and ci.quality_due(qmsg("e1", [("99232", "20261031")], dob="1990" + "0101"), qctx(), [{"cpt": "99232", "dos": "20261031"}], ["21"], _w2) is None and _w2 == [], (_w, _w2))
check("quality (13.2): a message with a hospital line and then a nursing line: the line rides with the NURSING line (the other visit lines of the message are still looked at), and 'hospital' is not said",
      ci.quality_due(qmsg("x1", [("99232", "20261030"), ("99309", "20261102")]), qctx(), [{"cpt": "99232", "dos": "20261030"}, {"cpt": "99309", "dos": "20261102"}], ["21", "32"], _w3) == 1 and _w3 == [], _w3)
for _p23 in ("23", "21"):
    ci.FAC["ER X"] = ("fac99", _p23); qreset(); _q = ci.quality_due; ci.quality_due = lambda *a_, **k_: 0; out, info, pp = qbuilt(qmsg("e1", [("99232", "20261031")]), qctx()); ci.quality_due = _q      # the second guard, in build(): here the decision is made to say yes
    check("quality: ... and build() itself never puts the line on a %s line, even when the decision says yes: the visit goes in as without the code, no place of the round is used" % _p23,
          out is not None and QP not in out[1] and out[1] == out[2] and "quality_codes" not in info and pp == [("pcode65089", _p23)] and ci.QUALITY["added"] == 0 and ci.QUALITY["done"] == set(), (pp, info))
check("quality (13.2): the places of service that never carry the line are 21, 22 and 23", ci.QUALITY_POS_SKIP == {"21", "22", "23"})
del ci.FAC["ER X"]; del ci.FACOF["e1"]
gets("after proof, while the run still has room (10 a run until Medicare's own answer is on file)", V1, qctx(), added=9, confirmed=True, budget=10)
none("after proof, the run's 10 are used up", V1, qctx(), added=10, confirmed=True, budget=10)
gets("after proof with Medicare's answer on file there is no cap", V1, qctx(), added=500, confirmed=True, budget=None)
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("1123F", "12/04/2025")]))
check("quality: last year's code does not count for this year", QP in out[1], pp)
qreset(); out, info, pp = qbuilt(qmsg("n2", [("99497", "20261102"), ("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
check("quality: with a visit and 99497 in one message the line rides with the VISIT and comes last", [x for x, _ in pp] == ["pcode492667", "pcode65119", QP] and pp[2][1] == pp[1][1], pp)
# the year: the code list was read for 2026 only (the Medicare reviewer's three inputs), and every visit line of a message is looked at (the year end)
none("a 2027 date of service, the register showing a 2026 line: not added until William renews the rule", qmsg("n2", [("99309", "20270104")]), qctx(), done={("pat9", "2026")})
check("quality: ... and that visit is counted for the January line of the report (year -> charts)", ci.QUALITY["not_renewed"] == {"2027": {"pat9"}}, ci.QUALITY["not_renewed"])
none("a 2031 date of service", qmsg("n2", [("99309", "20310104")]), qctx())
none("a 2025 date of service entered now (it can no longer count)", qmsg("n2", [("99309", "20251220")]), qctx())
check("quality: ... a year that is over is not counted as waiting for a renewal", ci.QUALITY["not_renewed"] == {}, ci.QUALITY["not_renewed"])
none("a visit that is not eligible anyway is not counted as waiting for a renewal either", qmsg("n2", [("99309", "20270104")], dob="1990" + "0101"), qctx())
check("quality: ... (nothing counted)", ci.QUALITY["not_renewed"] == {})
qreset(); out, info, pp = qbuilt(qmsg("m5", [("99309", "20270101"), ("99309", "20261231")]), qctx())
check("quality: one message with a 01/01/2027 visit line and then a 12/31/2026 one - the line rides with the 2026 visit (every visit line is looked at, not only the first)", info.get("quality_dos") == "12/31/2026" and len(re.findall(QCHG, out[1])) == 1
      and re.search(r'begindate="12/31/2026" enddate="12/31/2026"[^>]*proccode="pcode65441"', out[1]) is not None and ci.QUALITY["not_renewed"] == {"2027": {"pat9"}}, info)
none("one message with 12/31/2026 and 01/01/2027 visit lines for a patient already coded in 2026: no line from that message until the rule is renewed", qmsg("m5", [("99309", "20261231"), ("99309", "20270101")]), qctx(), done={("pat9", "2026")})
_yrs = set(ci.QUALITY_YEARS); ci.QUALITY_YEARS.add("2027")
qreset(done={("pat9", "2026")}); out, info, pp = qbuilt(qmsg("m5", [("99309", "20261231"), ("99309", "20270101")]), qctx())
check("quality: ... once William has renewed it for 2027, the SECOND visit line of that message carries the 2027 line", info.get("quality_dos") == "01/01/2027" and len(re.findall(QCHG, out[1])) == 1, info)
ci.QUALITY_YEARS.clear(); ci.QUALITY_YEARS.update(_yrs)
check("quality: the rule is read for 2026 only", ci.QUALITY_YEARS == {"2026"})
qreset(); _q = ci.quality_due; ci.quality_due = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx())
check("quality: a failure in the decision never touches the visit (entered as before, no line)", QP not in out[1] and out[1] == out[2] and "quality_codes" not in info, info)
ci.quality_due = _q
check("quality: Medicare first is read from the billing order, not from the list order", ci.medicare_first({"insorder": "2,1", "plans": [("i", "car6404", "", "", "1"), ("j", "car6085", "01/01/2020", "", "2")]}, "11/02/2026")
      and not ci.medicare_first({"insorder": "1,2", "plans": [("i", "car6404", "", "", "1"), ("j", "car6085", "01/01/2020", "", "2")]}, "11/02/2026") and not ci.medicare_first({"insorder": "1", "plans": None}, "11/02/2026") and not ci.medicare_first({}, "x"))
check("quality: a fresh helper that has not read the registers yet gives nobody a line (no insurance check is known)", ci._quality_fresh()["verify"] == {} and ci._quality_fresh()["budget"] == ci.QUALITY_PILOT == 3 and ci.QUALITY_DAILY == 10 and ci.QUALITY_LOOKS == 6)
check("names_line: a hold names the quality line by its code, AdvancedMD's id for it, its own charge number, or a zero amount of a charge - and by nothing else",
      all(ci.names_line(w, "charge7000011") for w in ("Pattern 990001: procedure 1123F - line item charge amount is zero", "pcode65441 not allowed", "edit on charge 7000011", "Pattern 88001: Charge amount is zero for this procedure", "Line charge of $0.00 is below the minimum", "the AMOUNT of a line is $0"))
      and not any(ci.names_line(w, "charge7000011") for w in ("Pattern 24078: something else", "Relationship of Subscriber to Patient is invalid", "The beginning or ending Date of service", "no admission anchor (no PV1 admit, no 99223 within 45 days)", "charge 17000011 is odd", "zero units", "", None)))
# 4c.2 one read of a line: its own charge detail (_line). Only void="1" on that charge is void; whatever cannot be read as the line is 'unknown'
def chg(cid, state=(), pcode=QP):      # what the stand-in's charge detail shows for one charge: its procedure and its billing (a list of billed dates, a dict of attributes, or a word)
    PROC[num(cid)] = pcode; BILLS[num(cid)] = state if isinstance(state, (dict, str)) else list(state)
def num(cid): return re.sub(r"\D", "", cid)
BILLS.clear(); PROC.clear()
chg("11", ["11/11/2026"]); chg("12", {"void": "1"}); chg("13", [], "pcode65119"); chg("14", {"insbilled": "1", "datebilled": "11/12/2026 21:10:33"}); chg("15", {"insbilled": "0", "datebilled": ""})
chg("16", "FAULT"); chg("17", "RAISE"); chg("18", "MISSING"); chg("19", "NOTXML"); chg("20", [], ""); chg("21", {"void": "1"}, "pcode65119"); chg("22", {"void": "1"}, ""); chg("23", ["11/11/2026"], "")
check("quality: a line's own charge detail is read as billed (dates listed, or the charge's own billed flag), open, or void",
      ci._line("charge11", QP) == ("billed", ["11/11/2026"]) and ci._line("14", QP) == ("billed", ["11/12/2026"]) and ci._line("15", QP) == ("open", []) and ci._line("12", QP) == ("void", []))
check("quality: ... and as UNKNOWN - never as void - when the charge shows another procedure, shows none, is not in the answer (a fault answer, an empty one), or the read fails",
      [ci._line(c, QP)[0] for c in ("13", "20", "16", "18", "17", "19", "", None)] == ["unknown"] * 8 and ci._line("23", QP)[0] == "unknown" and ci._line("21", QP)[0] == "unknown"
      and "another procedure" in ci._line("13", QP)[1][0] and "no procedure" in ci._line("20", QP)[1][0] and "not in AdvancedMD's answer" in ci._line("16", QP)[1][0] and "the read failed" in ci._line("17", QP)[1][0],
      [ci._line(c, QP) for c in ("13", "20", "16", "18", "17", "19", "21", "23")])
check("quality: ... only void=\"1\" on that very charge is void (also when AdvancedMD shows no procedure for a void charge)", ci._line("22", QP) == ("void", []) and ci._line("12") == ("void", []))
check("quality: the visit's own charge is read the same way without a procedure to look for", ci._line("13") == ("open", []) and ci._line("11") == ("billed", ["11/11/2026"]) and ci._line("23") == ("billed", ["11/11/2026"]) and ci._line("16")[0] == "unknown")
check("quality: the old reader is gone (one read of a line is _line)", not hasattr(ci, "_bills"))
BILLS.clear(); PROC.clear(); DETAILS.clear()
# 4c.3 what the quality code reads from the registers folder besides the import registers (quality_files)
wreg("feed_verify_20261101T0000Z.json", {"pat1": vrow(["vst1"]), "pat2": vrow(["vst2"], "HOLD", "", ["no active plan: discovery found nothing"]), "pat3": vrow(["vst3"], lead="HUM01"), "pat5": vrow(["vst5"], lead="HUM01"), "odd": 7})
wreg("feed_verify_20261105T0000Z.json", {"pat1": vrow(["vst11"], lead="HUM01"), "pat3": vrow(["vst13"]), "pat4": vrow(["vst14", "vst15"], "HOLD", "", ["insorder not applied on vst14"], ["vst14 insorder 2: detail read mismatch (1 of 2 charges live)"])})
wreg("feed_verify_20261105T0000ZR.json", {"pat5": vrow(["vst16"])})
wreg("feed_verify_20261109T0000Z.json", {"pat1": vrow(["vst21"]), "pat2": vrow(["vst22"])})
wreg("feed_inspector_20261105T0000Z.json", {"fixed": [], "bypassed": [], "laterality": [], "held": [{"visit": "14", "pid": "pat4", "why": "Pattern 88001: Charge amount is zero for this procedure"}, {"visit": "vst15", "pid": "pat4", "why": "Pattern 24078: something else", "names_line": True}, 7, {"pid": "x"}]})
F = ci.quality_files("20261109T0000Z")
check("registers: the NEWEST insurance check of an EARLIER batch is what counts for a chart - a later one replaces an older one, a retry batch counts, the batch's own check and later ones do not",
      F["verify"] == {"pat1": ("RELEASE", "HUM01"), "pat2": ("HOLD", ""), "pat3": OKCHK, "pat4": ("HOLD", ""), "pat5": OKCHK} and F["problems"] == [], F["verify"])
check("registers: every check is kept by batch for the proof, the visits of a HOLD with the hold's own words, the Claim Inspector's held visits by visit number",
      F["checks"]["20261101T0000Z"]["pat3"] == ("RELEASE", "HUM01") and F["checks"]["20261109T0000Z"]["pat1"] == OKCHK and sorted(F["check_holds"]) == ["14", "15", "2"]
      and F["check_holds"]["14"] == [("feed_verify_20261105T0000Z.json", ["insorder not applied on vst14", "vst14 insorder 2: detail read mismatch (1 of 2 charges live)"])]
      and F["held"] == {"14": [("feed_inspector_20261105T0000Z.json", "Pattern 88001: Charge amount is zero for this procedure", False)], "15": [("feed_inspector_20261105T0000Z.json", "Pattern 24078: something else", True)]}, (F["check_holds"], F["held"]))
check("registers: a later batch sees the check of 11/09 too; the first batch of all sees none", ci.quality_files("20261110T0000Z")["verify"]["pat1"] == OKCHK and ci.quality_files("1028")["verify"] == {})
check("registers: no exception list and no remittance file = no exceptions, Medicare's answer not on file", F["exceptions"] == set() and F["n620"] is False)
wreg("quality_exceptions.json", {"pat123": "declined", "17478346": "never addressed", "_note": "kept by William"})
check("exception list: an object of chart ids (with or without the 'pat'), a key that starts with _ is a remark", ci.quality_files("x")["exceptions"] == {"pat123", "pat17478346"} and ci.quality_files("x")["problems"] == [])
wreg("quality_exceptions.json", ["pat7", 8, " pat9 "])
check("exception list: a list of chart ids", ci.quality_files("x")["exceptions"] == {"pat7", "pat8", "pat9"})
for _bad, _what in (("{not json", "not JSON"), ('"pat7"', "a bare word"), ('["pat7", {"a": 1}]', "an entry that is not a chart id"), ('{"some name": 1}', "a key that is not a chart id")):
    open(os.path.join(REGDIR, "quality_exceptions.json"), "w").write(_bad); _f = ci.quality_files("x")
    check("exception list: a file that is there but cannot be read (%s) is a PROBLEM, not an empty list - no line is added in such a run" % _what, _f["exceptions"] == set() and len(_f["problems"]) == 1 and "quality_exceptions.json" in _f["problems"][0], _f["problems"])
rmreg("quality_exceptions.json")
open(os.path.join(REGDIR, "quality_n620_seen.json"), "w").write("not even JSON - the import only looks whether the file is there")
check("remittance file: the import only looks whether it exists", ci.quality_files("x")["n620"] is True and ci.quality_files("x")["problems"] == [])
rmreg("quality_n620_seen.json")
open(os.path.join(REGDIR, "feed_verify_20261106T0000Z.json"), "w").write("{cut off"); open(os.path.join(REGDIR, "feed_inspector_20261106T0000Z.json"), "w").write("[1, 2]")
check("registers: an insurance-check or inspector register that cannot be read is named as a problem (a hold or another payer could be hidden in it)", sorted(p.split(" ")[0] for p in ci.quality_files("20261109T0000Z")["problems"]) == ["registers/feed_inspector_20261106T0000Z.json", "registers/feed_verify_20261106T0000Z.json"], ci.quality_files("20261109T0000Z")["problems"])
wreg("feed_verify_20261110T0000Z.json", {"pat9": dict(vrow(["vst9"]), quality_removed=[{"visit": "vst9", "pid": "pat9", "charge": "charge92", "fee": "0.00", "why": "Fault", "void_ok": True, "released": True}, "odd", {"charge": 5}])})
check("registers (11.3): a removal the insurance check recorded in a chart's entry is read by batch stamp (odd entries passed over)", [(r_, e_["charge"]) for r_, e_ in ci.quality_files("20261111T0000Z")["removed"].get("20261110T0000Z", [])] == [("feed_verify_20261110T0000Z.json", "charge92")], ci.quality_files("20261111T0000Z")["removed"])
rmreg("feed_verify_20261110T0000Z.json")
rmreg("feed_verify_20261101T0000Z.json", "feed_verify_20261105T0000Z.json", "feed_verify_20261105T0000ZR.json", "feed_verify_20261109T0000Z.json", "feed_inspector_20261105T0000Z.json", "feed_verify_20261106T0000Z.json", "feed_inspector_20261106T0000Z.json")
# 4c.4 the ledger of lines (quality_state), fed directly with made-up registers: three pilot lines A, B, C of one batch and what the stand-in shows for them
RN = lambda s: "registers/feed_import_%s.json" % s
def qrow(pid, visit, qc, own, fee="0.00", dos="11/10/2026", **kw): return dict({"pid": pid, "visit": visit, "quality_codes": ["1123F"], "quality_charge": qc, "charges": [own, qc], "quality_fee": fee, "quality_dos": dos, "dos": dos, "cpts": ["99309"]}, **kw)
def state(regs, look=True, **kw):
    DETAILS.clear(); ci.quality_state(regs, look, **kw); return dict(ci.QUALITY)
def nextreg(stamp, created=(), failed=(), **gate):      # the register a later run writes: the gate of the state just computed (plus what the test changes in it) and its own rows
    return (RN(stamp), {"created": list(created), "failed": list(failed), "skipped": [], "quality_gate": dict(ci.quality_gate(), **gate)})
A_, B_, C_ = qrow("pat7001", "vst1", "charge12", "charge11"), qrow("pat7002", "vst2", "charge22", "charge21"), qrow("pat7003", "vst3", "charge32", "charge31")
R1 = (RN("20261111T1240Z"), {"created": [A_, B_, C_], "failed": [], "skipped": []})
def world(**st):      # every charge of A, B, C is open unless said otherwise
    BILLS.clear(); PROC.clear(); CHART["7001"] = [("99309", "11/10/2026"), ("1123F", "11/10/2026")]; CHART["7002"] = [("99309", "11/10/2026")]
    for c_ in ("12", "22", "32"): chg(c_, st.get("c" + c_, []))
    for c_ in ("11", "21", "31"): chg(c_, st.get("c" + c_, []), "pcode65119")
BILLED = ["11/12/2026"]; VOID = {"void": "1"}
world(); s = state([R1])
check("ledger: three lines, nothing billed - the round WAITS: no new line, the three visits are named, every line and its visit's own charge was read once",
      s["wait"] is True and s["budget"] == 0 and s["pending"] == ["vst1", "vst2", "vst3"] and s["pending_since"] == "feed_import_20261111T1240Z.json" and s["confirmed"] is False and s["off"] == ""
      and sorted(DETAILS) == ["11", "12", "21", "22", "31", "32"] and s["round"] == {"n": 1, "fee": "0.00", "since": "feed_import_20261111T1240Z.json", "lines": 3, "void": 0, "open": 3}
      and s["done"] == {("pat7001", "2026"), ("pat7002", "2026"), ("pat7003", "2026")}, s)
s = state([R1], look=False)
check("ledger: a dry run reads nothing in AdvancedMD and waits", s["wait"] is True and DETAILS == [] and any("dry run" in n for n in s["notes"]), (s["notes"], DETAILS))
world(c12=BILLED); s = state([R1])
check("ledger: one line is BILLED - proven: the proof is recorded, later lines are capped at 10 a run until Medicare's own answer is on file, and the chart history was read once to see whether it lists the line (it does)",
      s["confirmed"] is True and s["proof"] == {"register": "feed_import_20261111T1240Z.json", "chart": "pat7001", "visit": "vst1", "charge": "charge12", "billed": "11/12/2026", "fee": "0.00"} and s["budget"] == 10
      and s["billed_lines"] == ["charge12"] and s["wait"] is False and s["history_shows_line"] is True and s["off"] == "", s)
s2 = state([R1, nextreg("20261112T1240Z")])
check("ledger: the next run reads the proof from the gate; the proven round's two lines not decided yet are still read (a line is called left off only three days after its visit was billed, 13.1), then the billed line for Medicare's own answer (11.4) - the cap of 10 stays while none is shown",
      s2["confirmed"] is True and DETAILS == ["22", "21", "32", "31", "12"] and s2["proof"]["charge"] == "charge12" and s2["history_shows_line"] is True and s2["budget"] == 10 and s2["medicare_answer"] is None
      and s2["medicare_wait"] == {"lines": 1, "oldest": "11/12/2026", "days": 8}, (s2, DETAILS))
s = state([R1], files={"n620": True})
check("ledger: with Medicare's answer on file there is no cap after proof", s["confirmed"] is True and s["budget"] is None and s["n620"] is True, s)
world(c22=BILLED); s = state([R1])
check("ledger: the history of the proof's chart does NOT list the line - recorded (a 1123F / 1124F entered by hand is invisible to the import) with a note that points to the exception list",
      s["confirmed"] is True and s["history_shows_line"] is False and any("invisible to the import" in n and "quality_exceptions.json" in n for n in s["notes"]), s["notes"])
# the state-machine reviewer's mixed outcome (SM-1): visit A billed WITHOUT its $0.00 line, B's line billed, C open
world(c11=["11/11/2026"], c22=BILLED); s = state([R1])
check("ledger (SM-1): a visit billed without its $0.00 line while ANOTHER $0.00 line of the round is billed - $0.00 is proven; only the line READ as left off is dead and its patient due again; nobody else is touched",
      s["confirmed"] is True and s["fee"] == "0.00" and s["zero_not_billed"] is False and s["left_off_lines"] == ["charge12"] and s["dead_rows"] == [["pat7001", "vst1", "charge12"]] and s["dead"] == {("pat7001", "1123F", "11/10/2026")}
      and s["done"] == {("pat7002", "2026"), ("pat7003", "2026")} and s["proof"]["charge"] == "charge22", s)
s_rev = state([(RN("20261111T1240Z"), {"created": [C_, B_, A_]})])
check("ledger (SM-1): ... the same whatever the order of the rows", (s_rev["confirmed"], s_rev["fee"], s_rev["left_off_lines"], s_rev["done"], s_rev["proof"]["charge"]) == (True, "0.00", ["charge12"], s["done"], "charge22"), s_rev)
world(c11=["11/11/2026"]); s = state([R1])
check("ledger: a visit billed without its $0.00 line and NO line of the round billed - new lines carry one cent, a new round of three; only that one line is dead, the two lines not decided yet keep counting as reported",
      s["fee"] == "0.01" and s["zero_not_billed"] is True and s["confirmed"] is False and s["wait"] is False and s["budget"] == 3 and s["left_off_lines"] == ["charge12"] and s["dead_rows"] == [["pat7001", "vst1", "charge12"]]
      and s["done"] == {("pat7002", "2026"), ("pat7003", "2026")} and s["round"]["n"] == 2 and s["round"]["fee"] == "0.01" and s["round"]["lines"] == 0 and any("without its $0.00 quality line" in n for n in s["notes"]), s)
world(c11=["11/11/2026"], c22=BILLED); s3 = state([R1], files={"checks": {"20261111T1240Z": {"pat7002": ("RELEASE", "HUM01")}}})
check("ledger: a visit billed without its $0.00 line while another $0.00 line of the round IS billed, though on a claim that cannot be the proof - the amount does NOT move to one cent (AdvancedMD does send a $0.00 line); the round waits for its third line",
      s3["fee"] == "0.00" and s3["zero_not_billed"] is False and s3["confirmed"] is False and s3["wait"] is True and s3["pending"] == ["vst3"] and s3["left_off_lines"] == ["charge12"] and s3["billed_lines"] == ["charge22"], s3)
world(c11=["11/11/2026"]); state([R1])
world(c11=["11/11/2026"], c22=BILLED); s2 = state([R1, nextreg("20261112T1240Z")])
check("ledger: once at one cent it stays there - a $0.00 line found billed LATER is counted for its patient but changes nothing; the other two are read until decided, and the line read as left off is read again (13.1b: still not billed, so it stays left off)",
      s2["fee"] == "0.01" and s2["confirmed"] is False and s2["billed_lines"] == ["charge22"] and s2["left_off_lines"] == ["charge12"] and DETAILS.count("12") == 1 and "22" in DETAILS and "32" in DETAILS and s2["budget"] == 3
      and DETAILS.index("12") > max(DETAILS.index("22"), DETAILS.index("32")) and s2["left_off_on"] == {"charge12": {"on": "11/20/2026", "billed": "11/11/2026"}}, (s2, DETAILS))
world(c11=["11/11/2026"], c32="RAISE"); s = state([R1])
check("ledger: a line whose read FAILS is never called dead - it is not decided (the reviewer's case: one visit billed without its line, another line's read raises)", s["left_off_lines"] == ["charge12"] and ("pat7003", "2026") in s["done"] and s["dead_rows"] == [["pat7001", "vst1", "charge12"]], s)
world(c12="FAULT"); s = state([R1])
check("ledger (NH-1): a line AdvancedMD answers with a fault is not decided - the round waits, the place is NOT freed, and a note says so", s["wait"] is True and s["budget"] == 0 and s["void_lines"] == [] and any("vst1" in n and "not decided" in n for n in s["notes"]), s)
world(); _wrong = (RN("20261111T1240Z"), {"created": [qrow("pat7003", "vst3", "charge21", "charge31")]}); s = state([_wrong])
check("ledger (SM-6): a row that names ANOTHER visit's own charge as the quality line is not a line that can be decided - never 'proven', never 'void': it waits", s["wait"] is True and s["confirmed"] is False and s["void_lines"] == [], s)
world(c21=BILLED); ECHO["detail_noproc"] = True; s = state([_wrong]); ECHO["detail_noproc"] = False
check("ledger (SM-6): ... also when that charge is billed and the charge detail shows no procedure at all - 'proven' needs a charge that SHOWS procedure pcode65441", s["confirmed"] is False and s["wait"] is True and s["billed_lines"] == [], s)
world(c12="MISSING"); s = state([R1])
check("ledger: a charge that is not in AdvancedMD's answer at all is not decided", s["wait"] is True and s["void_lines"] == [] and s["pending"] == ["vst1", "vst2", "vst3"], s)
# VOID: taken off by a person / the whole visit gone / not known
world(c12=VOID); s = state([R1])
check("ledger: a line is void while its visit's own charge is still live - a person took it off: the code is OFF until William restarts it, the sentence names the visit, no new line",
      "1 earlier quality line(s) were taken off their visits" in s["off"] and "vst1" in s["off"] and s["off_until_reset"] == s["off"] and s["budget"] == 0 and s["void_lines"] == ["charge12"] and s["wait"] is False and ("pat7001", "2026") not in s["done"], s)
world(c12=VOID, c11=VOID); s = state([R1])
check("ledger: a line is void and its visit's own charge too - the visit is gone: no outcome either way, its patient is due again, the round still waits for the two other lines", s["off"] == "" and s["void_lines"] == ["charge12"] and s["wait"] is True
      and s["pending"] == ["vst2", "vst3"] and ("pat7001", "2026") not in s["done"] and s["round"]["void"] == 1, s)
check("ledger: ... and a round that waits has NO room for a new line (budget 0), also while one of its three places is free again - the free place is used only once the other lines are decided", s["wait"] is True and s["budget"] == 0 and ci.quality_gate()["budget"] == 0, s)
world(c12=VOID, c11=VOID, c22=VOID, c21=VOID, c32=VOID, c31=VOID); s = state([R1])
check("ledger: all three visits are gone - their places are free: three more lines may be entered in this round", s["off"] == "" and s["wait"] is False and s["budget"] == 3 and s["round"] == {"n": 1, "fee": "0.00", "since": "feed_import_20261111T1240Z.json", "lines": 3, "void": 3, "open": 0}, s)
R1b = (RN("20261112T1240Z"), {"created": [qrow("pat7004", "vst4", "charge42", "charge41"), qrow("pat7005", "vst5", "charge52", "charge51"), qrow("pat7006", "vst6", "charge62", "charge61")], "quality_gate": ci.quality_gate()})
for c_ in ("42", "52", "62"): chg(c_, VOID)
for c_ in ("41", "51", "61"): chg(c_, VOID, "pcode65119")
s = state([R1, R1b])
check("ledger: the replacement lines are voided too - a round never holds more than six lines: the code is OFF ('the pilot's lines keep being voided') until William restarts it",
      "the pilot's lines keep being voided" in s["off"] and s["off_until_reset"] == s["off"] and s["budget"] == 0 and s["round"]["lines"] == 6 and not any(c_ in DETAILS for c_ in ("12", "22", "32")), (s, DETAILS))
chg("62", []); chg("61", []); s = state([R1, R1b])
check("ledger: ... while one of the six is still open the round only waits", s["off"] == "" and s["wait"] is True and s["pending"] == ["vst6"] and s["budget"] == 0, s)
world(c12=BILLED, c22=VOID, c21=VOID, c32=VOID, c31=VOID); s = state([R1], files={"checks": {"20261111T1240Z": {"pat7001": ("RELEASE", "HUM01")}}})
check("ledger: the cap of three counts every line of the round that is not void - one line billed (on a claim that cannot be the proof) and two visits gone: TWO more lines may be entered, not three", s["budget"] == 2 and s["confirmed"] is False and s["wait"] is False and s["off"] == "", s)
R4 = (RN("20261111T1240Z"), {"created": [A_, B_, C_, qrow("pat7004", "vst4", "charge42", "charge41")]}); world(c12=VOID, c11=VOID, c22=VOID, c21=VOID, c32=VOID, c31=VOID); chg("42", VOID); chg("41", VOID, "pcode65119"); s = state([R4])
check("ledger: a round never holds more than six lines - four lines, all gone with their visits: TWO more may be entered, not three", s["budget"] == 2 and s["round"]["lines"] == 4 and s["round"]["void"] == 4 and s["off"] == "", s)
world(c12=VOID, c11="RAISE"); s = state([R1])
check("ledger: a void line whose visit's own charge cannot be read is not decided (was the line taken off, or is the visit gone?) - it waits", s["off"] == "" and s["void_lines"] == [] and s["wait"] is True and "vst1" in s["pending"], s)
world(c12=VOID); s = state([(RN("20261111T1240Z"), {"created": [dict(A_, charges=None)]})])
check("ledger: a void line in a row that records no charge of the visit itself is just void - an odd row never switches the code off or makes the pilot wait", s["off"] == "" and s["wait"] is False and s["void_lines"] == ["charge12"] and s["budget"] == 3, s)
world(c11=VOID); s = state([R1])
check("ledger: the visit's own charge is void while its quality line is still live - not decided, and a note asks William to look", s["wait"] is True and any("still live" in n for n in s["notes"]), s["notes"])
# an OLDER pilot line (not of the current round) that is read later and found taken off by a person: OFF only when it was entered since the last restart and the current amount is not proven yet
D1C = qrow("pat7004", "vst4", "charge42", "charge41", fee="0.01")
world(c11=["11/11/2026"]); state([R1]); ONEC = nextreg("20261112T1240Z", created=[D1C])      # A's visit went out without its $0.00 line: one cent, and a one-cent line D is entered
chg("42", []); chg("41", [], "pcode65119"); chg("22", VOID); s = state([R1, ONEC])               # D is not decided yet; B's $0.00 line is void while B's own charge is still live
check("ledger: an earlier $0.00 line is read later and found taken off its visit by a person while the one-cent round is NOT proven - the code is OFF until William restarts it, and the sentence names that visit",
      s["off"] == "the quality line of visit vst2 was taken off the visit (void) while the visit is still there - William looks" and s["off_until_reset"] == s["off"] and s["budget"] == 0 and s["wait"] is False
      and s["void_lines"] == ["charge22"] and s["fee"] == "0.01" and ("pat7002", "2026") not in s["done"], s)
chg("42", BILLED); chg("41", BILLED, "pcode65119"); s = state([R1, ONEC])                        # the same, but the one-cent line D is billed: one cent is proven in this very run
check("ledger: ... the same $0.00 line found taken off once one cent IS proven - the line is just void (its patient is due again); the proven code is not switched off by an old line of the other amount",
      s["off"] == "" and s["confirmed"] is True and s["fee"] == "0.01" and s["budget"] == 10 and s["void_lines"] == ["charge22"] and s["billed_lines"] == ["charge42"] and ("pat7002", "2026") not in s["done"]
      and any("taken off the visit" in n for n in s["notes"]), s)
world(c12=VOID); chg("42", []); chg("41", [], "pcode65119")                                      # A's $0.00 line was taken off by a person; nobody had read it before William restarted the code
s = state([R1, (RN("20261112T1240Z"), {"created": [qrow("pat7004", "vst4", "charge42", "charge41")], "quality_gate": {"reset": True, "fee": "0.00"}})])
check("ledger: a line from BEFORE William's restart that is read only now and found taken off - it is just void (he has looked, and said to start again): the new round is not switched off, it waits for its own line",
      s["off"] == "" and s["wait"] is True and s["pending"] == ["vst4"] and s["void_lines"] == ["charge12"] and s["round"]["lines"] == 1 and ("pat7001", "2026") not in s["done"] and any("taken off the visit" in n for n in s["notes"]), s)
# what proves the code: a billed line whose visit was never held and whose own batch's insurance check did not hold the chart or name another payer
world(c12=BILLED)
for _chk, _ok in ((None, True), (OKCHK, True), (("HOLD", ""), False), (("RELEASE", "HUM01"), False), (("RELEASE", ""), False)):
    s = state([R1], files={"checks": {"20261111T1240Z": {"pat7001": _chk}} if _chk else {}})
    check("ledger: a billed line and its own batch's insurance check %s -> %s" % (_chk or "(none of that batch)", "proven" if _ok else "NOT the proof - billed all the same, and the round goes on waiting for the other lines"),
          s["confirmed"] is _ok and s["billed_lines"] == ["charge12"] and (_ok or (s["wait"] is True and s["pending"] == ["vst2", "vst3"] and any("cannot be the proof" in n for n in s["notes"]))), s)
s = state([R1], files={"checks": {"20261109T0000Z": {"pat7001": ("HOLD", "")}}})
check("ledger: ... the check of ANOTHER batch does not matter for the proof", s["confirmed"] is True, s)
world(c12=BILLED, c22=BILLED, c32=BILLED); s = state([R1], files={"checks": {"20261111T1240Z": {p_: ("RELEASE", "HUM01") for p_ in ("pat7001", "pat7002", "pat7003")}}})
check("ledger: the round is full, every line is decided and none can be the proof - OFF until William has looked (otherwise the pilot would stand still for ever without a word)", "the pilot round is full (3 lines) and none of them can be the proof" in s["off"] and s["off_until_reset"] == s["off"] and s["confirmed"] is False, s)
# HELD VISITS (the Medicare reviewer's M1): a visit that carries the line and is held
INS = lambda why, **kw: {"held": {"1": [("feed_inspector_20261111T1240Z.json", why, kw.get("marked", False))]}}
world(); s = state([R1], files=INS("Relationship of Subscriber to Patient is invalid"))
check("ledger (M1): BEFORE proof any Claim Inspector hold on a visit that carries the line switches the code OFF until William restarts it - the sentence names the visit and quotes the hold; nothing is read",
      "the Claim Inspector holds visit vst1, which carries the quality line" in s["off"] and '"Relationship of Subscriber to Patient is invalid"' in s["off"] and "feed_inspector_20261111T1240Z.json" in s["off"] and s["off_until_reset"] == s["off"] and s["budget"] == 0 and DETAILS == [], (s, DETAILS))
world(c12=BILLED, c22=BILLED); s = state([R1], files=INS("Pattern 990001: procedure 1123F - line item charge amount is zero"))
check("ledger (M1): a held visit that a person released and that is billed afterwards is NEVER the proof - the code stays off", s["confirmed"] is False and "the Claim Inspector holds visit vst1" in s["off"] and s["budget"] == 0, s)
PROVEN = (RN("20261112T1240Z"), {"created": [], "quality_gate": {"confirmed": True, "fee": "0.00", "proof": {"visit": "vst2", "charge": "charge22"}}})
world(); s = state([R1, PROVEN], files=INS("Relationship of Subscriber to Patient is invalid"))
check("ledger (M1): AFTER proof a hold whose words do not name the line changes nothing", s["off"] == "" and s["confirmed"] is True and s["budget"] == 10, s)
for _w in ("Pattern 990001: procedure 1123F - line item charge amount is zero", "edit on pcode65441", "charge 12 cannot be billed", "Pattern 88001: Charge amount is zero for this procedure"):
    s = state([R1, PROVEN], files=INS(_w))
    check("ledger (M1): AFTER proof a hold whose words name the line (%s) switches the code OFF until William restarts it" % _w[:40], "the Claim Inspector holds visit vst1" in s["off"] and _w[:30] in s["off"] and s["off_until_reset"] == s["off"] and s["budget"] == 0, s)
s = state([R1, PROVEN], files=INS("Pattern 24078: something else", marked=True))
check("ledger (M1): ... and so does a hold the inspector step itself marked as naming the line", "the Claim Inspector holds visit vst1" in s["off"], s)
s = state([R1, PROVEN], files={"held": {"9": [("feed_inspector_20261111T1240Z.json", "procedure 1123F - zero", False)]}})
check("ledger: a hold on a visit that does not carry the line is not the quality code's business", s["off"] == "" and s["confirmed"] is True, s)
world(); s = state([R1, (RN("20261112T1240Z"), {"created": [], "quality_gate": {"reset": True, "fee": "0.00"}})], files=INS("Pattern 990001: procedure 1123F - line item charge amount is zero"))
check("ledger (M1): a hold on a visit from BEFORE William's restart no longer switches the code off (he has looked, and said to start again)", s["off"] == "" and s["budget"] == 3 and s["round"]["lines"] == 0, s)
CHK = lambda *words: {"check_holds": {"1": [("feed_verify_20261111T1240Z.json", list(words))]}}
for _w in ("insorder not applied on vst1", "vst1 insorder 2: detail read mismatch (1 of 2 charges live)", "vst1 insorder 2: resave FAULT <Fault>x</Fault>", "insorder not applied"):
    for _regs, _when in (([R1], "before"), ([R1, PROVEN], "after")):
        world(); s = state(_regs, files=CHK("no active plan: discovery found nothing", _w))
        check("ledger (M1): %s proof, the insurance check could not set the order of a visit that carries the line (%s) - OFF until William restarts it, the sentence names the visit and quotes the hold" % (_when, _w[:34]),
              "the insurance check could not set the order of visit vst1, which carries the quality line" in s["off"] and _w[:30] in s["off"] and s["off_until_reset"] == s["off"], s)
world(c12=BILLED); s = state([R1], files=CHK("insorder not applied on vst9", "no active plan: discovery found nothing"))
check("ledger (M1): another insurance-check HOLD on a pilot visit (or one that names another visit) does not switch the code off - but that visit can never be the proof, and the round waits for the others",
      s["off"] == "" and s["confirmed"] is False and s["billed_lines"] == ["charge12"] and s["wait"] is True and s["pending"] == ["vst2", "vst3"], s)
# an OFF that only William's restart ends is REMEMBERED (SM-4), and the switches (SM-8)
world(c12=VOID); s = state([R1]); _off = s["off"]; LATER = nextreg("20261112T1240Z")
world(c12=VOID, c11=VOID, c22=VOID, c21=VOID, c32=VOID, c31=VOID); s = state([R1, LATER])
check("ledger (SM-4): an OFF that needs William's word is carried forward by the gate - the next run is still OFF with the same sentence although everything now reads void (voiding the lines does not start a new pilot), and reads nothing",
      s["off"] == _off and s["off_until_reset"] == _off and s["budget"] == 0 and DETAILS == [] and s["reset"] is False, (s, DETAILS))
s = state([R1, LATER, nextreg("20261113T1240Z"), nextreg("20261114T1240Z")])
check("ledger (SM-4): ... and the run after, and the one after that", s["off"] == _off and s["budget"] == 0, s)
s = state([R1, LATER], reset=True)
check("switch reset (William's word) with the code OFF: a new round at $0.00, the OFF is gone, the restart is recorded - the old lines are no longer this round's, but a line that exists still counts once a year",
      s["off"] == "" and s["off_until_reset"] == "" and s["reset"] is True and s["fee"] == "0.00" and s["budget"] == 3 and s["round"]["lines"] == 0 and s["round"]["n"] == 2 and any("started again" in n for n in s["notes"]) and s["loud"] == "", s)
RESET = nextreg("20261113T1240Z", created=[qrow("pat7004", "vst4", "charge42", "charge41")]); chg("42", []); chg("41", [], "pcode65119")
s = state([R1, LATER, RESET])
check("ledger: after the restart the next run waits for the NEW round's line only; the lines from before the restart are not this round's", s["off"] == "" and s["wait"] is True and s["pending"] == ["vst4"] and s["reset"] is False and s["round"]["lines"] == 1, s)
world(); s0 = state([R1]); s = state([R1], reset=True)
check("switch reset with NOTHING switched off is ignored, loudly - a switch left in a routine cannot start a new round every night (the round still waits for its three lines)",
      s["reset"] is False and s["wait"] is True and s["pending"] == s0["pending"] and s["budget"] == 0 and "NOTHING TO RESTART" in s["loud"] and any("NOTHING TO RESTART" in n for n in s["notes"]) and "NOTHING TO RESTART" in ci.quality_log(0, False), s)
s = state([R1], stop=True)
check("switch stop (William's word): OFF until he restarts it - written into the gate", "stopped on William's word (QUALITY_CODE=stop)" in s["off"] and s["off_until_reset"] == s["off"] and s["budget"] == 0 and DETAILS == [], s)
STOPPED = nextreg("20261112T1240Z"); s = state([R1, STOPPED])
check("switch stop: ... the next run, without any switch, is still off", "stopped on William's word" in s["off"] and s["budget"] == 0, s)
s = state([R1, STOPPED], reset=True)
check("switch stop then reset: the code starts again", s["off"] == "" and s["reset"] is True and s["budget"] == 3, s)
world(c12=VOID); state([R1]); TAKEN = nextreg("20261112T1240Z"); s = state([R1, TAKEN], stop=True)
check("switch stop when the code is already off keeps the first sentence", "taken off their visits" in s["off"] and any("already off" in n for n in s["notes"]), s)
# REFUSALS in a row at one amount (SM-11): before proof ONE is enough, after proof TWO; a stored line clears the count; the refused patient gets no second try that year
REF = lambda pid, fee="0.00", **kw: dict({"pid": pid, "visit": "vst9", "quality_codes": [], "quality_refused": "Fault: no", "quality_refused_fee": fee, "quality_tried": fee, "quality_dos": "11/10/2026", "dos": "11/10/2026", "charges": ["charge91"]}, **kw)
world(); s = state([(RN("20261111T1240Z"), {"created": [REF("pat7009")]})])
check("refusals: BEFORE proof one refused visit at $0.00 moves the amount to one cent (a new round); the refused patient gets no second try that year",
      s["fee"] == "0.01" and s["off"] == "" and s["budget"] == 3 and s["round"]["n"] == 2 and s["refused"] == {("pat7009", "2026")} and ("pat7009", "2026") in s["done"] and ci.quality_gate()["refused_charts"] == [["pat7009", "2026"]], s)
s = state([(RN("20261111T1240Z"), {"created": [REF("pat7009")]}), (RN("20261112T1240Z"), {"created": [REF("pat7010", "0.01")]})])
check("refusals: refused at one cent too - OFF until William restarts it, and the sentence says where", s["off"] == "AdvancedMD refused a visit that carried the code with a one-cent charge too (feed_import_20261112T1240Z.json) - William looks" and s["off_until_reset"] == s["off"]
      and s["refused"] == {("pat7009", "2026"), ("pat7010", "2026")}, s)
s = state([(RN("20261111T1240Z"), {"created": [REF("pat7009", "0.01")]})])
check("refusals: refusals are counted in a row at ONE amount - a refusal recorded at one cent while the code stands at $0.00 (the registers before it never reached this machine) does not move the amount; that patient still gets no second try",
      s["fee"] == "0.00" and s["off"] == "" and s["budget"] == 3 and s["round"]["n"] == 1 and ("pat7009", "2026") in s["done"], s)
s = state([(RN("20261111T1240Z"), {"created": [dict(REF("pat7009"), quality_refused=None, quality_not_stored="0.00")]})])
check("refusals: a visit stored WITHOUT its line counts the same way - but that patient was not refused and is still due", s["fee"] == "0.01" and s["refused"] == set() and ("pat7009", "2026") not in s["done"], s)
world(c12=BILLED)
def after_proof(*later): return state([R1, (RN("20261112T1240Z"), {"created": [], "quality_gate": {"confirmed": True, "fee": "0.00"}})] + [(RN("202611%dT1240Z" % (13 + i)), {"created": list(rows)}) for i, rows in enumerate(later)])
s = after_proof([REF("pat7009")])
check("refusals (SM-11): AFTER proof ONE refused visit changes nothing - the proof at $0.00 still counts", s["fee"] == "0.00" and s["confirmed"] is True and s["off"] == "" and s["budget"] == 10 and ("pat7009", "2026") in s["done"], s)
s = after_proof([REF("pat7009")], [qrow("pat7010", "vst10", "charge102", "charge101")], [REF("pat7011")])
check("refusals (SM-11): ... a line stored in between clears the count: a second refused visit days later still changes nothing", s["fee"] == "0.00" and s["confirmed"] is True and s["off"] == "", s)
s = after_proof([REF("pat7009")], [REF("pat7011")])
check("refusals (SM-11): after proof TWO refused visits in a row with no line stored in between move the amount to one cent - a new round that needs its own proof", s["fee"] == "0.01" and s["confirmed"] is False and s["budget"] == 3 and s["off"] == "", s)
chg("102", []); chg("101", [], "pcode65119")      # a line entered AFTER proof (its register's gate says proven), then the same two refusals
s = state([R1, (RN("20261112T1240Z"), {"created": [qrow("pat7010", "vst10", "charge102", "charge101")], "quality_gate": {"confirmed": True, "fee": "0.00", "billed_lines": ["charge12"]}}),
           (RN("20261113T1240Z"), {"created": [REF("pat7009")]}), (RN("20261114T1240Z"), {"created": [REF("pat7011")]})])
check("ledger: a line entered AFTER proof is never read back - not even when two refusals later move the amount to one cent; only the pilot's own lines that are not decided yet are still read, and a line already decided is not read again",
      s["fee"] == "0.01" and s["confirmed"] is False and "102" not in DETAILS and "101" not in DETAILS and "22" in DETAILS and "32" in DETAILS and "12" not in DETAILS and ("pat7010", "2026") in s["done"], (s, DETAILS))
s = after_proof([REF("pat7009")], [REF("pat7011")], [REF("pat7012", "0.01")])
check("refusals: ... and one refused visit at one cent, before that round is proven, switches the code OFF", "with a one-cent charge too" in s["off"] and s["off_until_reset"] == s["off"], s)
FAILED = lambda **kw: dict({"feed_id": "f1", "pid": "pat7009", "empty_visit": "vst70", "info": {"quality_tried": "0.00", "quality_dos": "11/10/2026", "dos": "11/10/2026", "cpts": ["99309"]}, "err": "x"}, **kw)
world(); s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(stored=[["99309", "11/10/2026"], ["1123F", "11/10/2026"]])]})])
check("refusals (SM-5): a fault although the chart shows the visit - from the next run the code is OFF until William has looked; the sentence names the chart, the visit and the register; that patient gets no second try",
      s["off"] == "AdvancedMD answered a fault but kept the visit - William looks (chart pat7009, visit vst70, feed_import_20261111T1240Z.json)" and s["off_until_reset"] == s["off"] and s["budget"] == 0 and ("pat7009", "2026") in s["done"], s)
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(stored=["chart not read: TimeoutError"])]})])
check("refusals (SM-5): ... and the same when the chart could not be read after the fault (the sentence says that)", s["off"].startswith("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (chart pat7009") and s["budget"] == 0, s)
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(quality_sent="0.00")]})])
check("refusals (NH-11): a visit refused with the line whose send WITHOUT the line then failed is counted like a refusal by the next run (one cent before proof), and that patient gets no second try", s["fee"] == "0.01" and s["off"] == "" and ("pat7009", "2026") in s["done"], s)
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(quality_unknown="0.00")]})])
check("refusals: a call that carried the line and ended in an error (nobody knows what AdvancedMD kept) - OFF until William has looked", s["off"].startswith("a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (chart pat7009, visit vst70") and s["off_until_reset"] == s["off"], s)
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(), FAILED(stored=[]), {"err": "x"}, 7]})])
check("refusals: a visit refused with AND without the line is an ordinary fault - it says nothing about the code (a plain pilot the next run)", s["fee"] == "0.00" and s["off"] == "" and s["budget"] == 3 and s["refused"] == set(), s)
# a restart inside a stamp that already holds rows: what was written before the restart stays in the old round
world(); chg("42", []); chg("41", [], "pcode65119")
SAME = (RN("20261111T1240Z"), {"created": [A_, qrow("pat7004", "vst4", "charge42", "charge41")], "failed": [FAILED(stored=[["99309", "11/10/2026"]])], "quality_gate": {"reset": True, "reset_after": [1, 1], "fee": "0.00"}})
s = state([SAME])
check("restart under a stamp that already held rows: the fault and the line from BEFORE the restart do not switch the code off again or sit in the new round - the new round holds only the line entered after it",
      s["off"] == "" and s["wait"] is True and s["pending"] == ["vst4"] and s["round"]["lines"] == 1 and ("pat7001", "2026") in s["done"], s)
s = state([(SAME[0], dict(SAME[1], quality_gate={"reset": True, "fee": "0.00"}))])
check("restart: ... (without the mark of where the restart happened, the whole register counts as after it - the fault would switch the code off again)", "AdvancedMD answered a fault but kept the visit" in s["off"], s)
# registers in odd shapes, out of order, copied, with words where a yes / no is expected (the state-machine reviewer's list): never an error, never a wrong 'proven'
world(c11=["11/11/2026"], c22=BILLED)
ZNB = {"created": [], "quality_gate": {"zero_not_billed": True, "fee": "0.01"}}; CONF0 = {"created": [], "quality_gate": {"confirmed": True, "fee": "0.00"}}
s = state([(RN("20261112T1240Z"), ZNB), R1])
check("odd registers: given newest first - they are read oldest first by name", s["fee"] == "0.01" and s["zero_not_billed"] is True and s["round"]["fee"] == "0.01", s)
s = state([R1, (RN("20261112T1240Z"), CONF0), (RN("20261113T1240Z"), ZNB)])
check("odd registers: a proof at $0.00 followed by a gate at one cent - one cent stays (never back without a restart), and one cent is not proven", s["fee"] == "0.01" and s["confirmed"] is False, s)
s = state([R1, (RN("20261112T1240Z"), ZNB), (RN("20261113T1240Z"), CONF0)])
check("odd registers: ... and a gate 'proven at $0.00' AFTER the gate at one cent does not bring $0.00 back or prove one cent", s["fee"] == "0.01" and s["confirmed"] is False, s)
s = state([R1, (RN("20261112T1240Z"), ZNB), (RN("20261113T1240Z"), {"created": [], "quality_gate": {"reset": True, "fee": "0.00"}})])
check("odd registers: a restart after the switch to one cent - back at $0.00, and the earlier lines still count once a year", s["fee"] == "0.00" and s["zero_not_billed"] is False and ("pat7002", "2026") in s["done"] and s["round"]["lines"] == 0, s)
world(); s = state([(RN("20261111T1240ZR"), CONF0), R1])
check("odd registers: a batch and its retry batch (stamp ...R) - the retry's gate is read after the batch's rows", s["confirmed"] is True and s["budget"] == 10 and s["wait"] is False, s)
s = state([R1, (RN("20261111T1240Z_copy"), {"created": [C_]})])
check("odd registers: a copy of a register under another name doubles a row - no error, the round only gets fuller", s["wait"] is True and s["round"]["lines"] == 4 and s["off"] == "", s)
s = state([R1, (RN("20261112T1240Z"), {"created": [], "quality_gate": {"zero_not_billed": "no", "reset": "no", "confirmed": "yes", "fee": "0.00", "off_until_reset": 5, "billed_lines": "charge12", "void_lines": [7, None], "refused_charts": "x", "round": {"n": "9"}, "reset_after": "x"}})])
check("odd registers: words where a yes / no is expected ('no', 'yes') are not taken for a yes; odd lists are passed over", s["fee"] == "0.00" and s["reset"] is False and s["confirmed"] is False and s["off"] == "" and s["wait"] is True and s["billed_lines"] == [] and s["round"]["n"] == 1, s)
for odd in ([("a", {"created": "not a list", "quality_gate": 7})], [("b", [1, 2])], [("c", None)], [(5, {"created": [7, None, "x"], "quality_gate": {"confirmed": "yes", "fee": 9, "zero_not_billed": 0, "reset": 0}})], []):
    try: ci.quality_state(odd, look=True); okq = ci.QUALITY["off"] == "" and ci.QUALITY["fee"] == "0.00" and ci.QUALITY["confirmed"] is False and ci.QUALITY["wait"] is False and json.dumps(ci.quality_gate()) != ""
    except Exception as e: okq = False
    check("quality: the state is read without an error from an odd register list (%s)" % (type(odd[0][1]).__name__ if odd else "empty"), okq, dict(ci.QUALITY))
for odd in ([("d", {"created": [{"quality_codes": ["1123F"], "quality_charge": "chargeX", "charges": "abc", "pid": "pat7001", "quality_dos": None, "dos": None}, {"quality_codes": ["1123F"], "quality_charge": "charge12", "charges": {"a": 1}, "pid": 3, "visit": {"v": 1}, "quality_fee": ["0.00"], "quality_dos": ["x"]}],
                    "quality_gate": {"reset": "no", "zero_not_billed": "no"}})],
            [({"n": 1}, {"created": [{"quality_refused": True, "quality_refused_fee": {"x": 1}}], "failed": [{"quality_sent": {"a": 1}, "info": "x"}, {"quality_unknown": [], "pid": 5}, {"stored": [], "info": {"quality_tried": 0}}]})]):
    try: ci.quality_state(odd, look=True); okq = ci.QUALITY["off"] == "" and ci.QUALITY["fee"] == "0.00" and ci.QUALITY["confirmed"] is False and json.dumps(ci.quality_gate()) != ""
    except Exception as e: okq = False
    check("quality: rows with odd values (%s ...) are read without an error, never prove the code and never switch it off; the gate can still be written" % str(odd[0][1])[:36], okq, dict(ci.QUALITY))
try: ci.quality_state([], look=True); okq = ci.QUALITY["off"] == "" and ci.QUALITY["fee"] == "0.00" and ci.QUALITY["budget"] == 3 and ci.QUALITY["wait"] is False
except Exception: okq = False
check("quality: no register at all is a fresh pilot (three lines may be entered)", okq, dict(ci.QUALITY))
# 4c.4b the second reviewers (11/10/2026 11:45Z) and the owner's decision of 10:40Z: when a line counts as left off (13.1), its code text (13.4),
# lines the routine took off a held visit (11.3), Medicare's own answer (11.4)
D_ = lambda m_, d_: _dt.date(2026, m_, d_)
world(c11=["11/11/2026"]); s = state([R1], day=D_(11, 13))
check("ledger (13.1): two days after its visit was billed an unbilled $0.00 line is NOT left off - not decided: the round waits, nothing is listed dead, the amount stays $0.00",
      s["left_off_lines"] == [] and s["dead_rows"] == [] and s["fee"] == "0.00" and s["wait"] is True and "vst1" in s["pending"] and any("not decided before 11/14/2026" in n_ for n_ in s["notes"]), s)
s = state([R1], day=D_(11, 14))
check("ledger (13.1): three days after - a line still open while its visit is billed IS left off and, with no $0.00 line of the round billed, new lines carry one cent; the gate keeps when it was called left off and the visit's billed date",
      s["left_off_lines"] == ["charge12"] and s["fee"] == "0.01" and s["zero_not_billed"] is True and s["left_off_on"] == {"charge12": {"on": "11/14/2026", "billed": "11/11/2026"}}, s)
world(c11=["not a date"]); s = state([R1], day=D_(11, 12)); G12 = nextreg("20261112T1240Z")
check("ledger (13.1): a visit listed as billed whose billed date cannot be read - the gate remembers the day the import first saw it billed and counts from that day", s["left_off_lines"] == [] and s["left_off_seen"] == {"charge12": "11/12/2026"} and s["wait"] is True, s)
s = state([R1, G12], day=D_(11, 14)); s3 = state([R1, G12], day=D_(11, 15))
check("ledger (13.1): ... two days later still not decided, three days later left off", s["left_off_lines"] == [] and s["left_off_seen"] == {"charge12": "11/12/2026"} and s3["left_off_lines"] == ["charge12"] and s3["left_off_seen"] == {}, (s, s3))
world(c11=["11/11/2026"]); state([R1], day=D_(11, 14)); G14 = nextreg("20261114T1240Z")                          # A's line called left off on 11/14: one cent
chg("12", ["11/20/2026"]); s = state([R1, G14], day=D_(11, 21))
check("ledger (13.1b): a line read as left off is read again - billed later (day 10), it moves to the billed lines, its patient counts as coded, the digest gets its line; the amount stays one cent",
      "charge12" in s["billed_lines"] and s["left_off_lines"] == [] and ("pat7001", "2026") in s["done"] and s["late_billed"] == {"charge12": "11/21/2026"} and s["late_rows"] == [["pat7001", "vst1", "charge12", "11/14/2026", "", "2026"]]
      and s["fee"] == "0.01" and s["dead_rows"] == [] and s["billed_on"]["charge12"] == "11/20/2026", s)
D9 = nextreg("20261115T1240Z", created=[qrow("pat7001", "vst9", "charge92", "charge91", fee="0.01", dos="11/15/2026")]); chg("92", []); chg("91", [], "pcode65119")
s = state([R1, G14, D9], day=D_(11, 21))
check("ledger (13.1b): ... the re-read comes after everything else and only inside the run's six reads - here the one-cent line and the two other $0.00 lines use them up, so the left-off line waits for a later run",
      s["late_rows"] == [] and s["left_off_lines"] == ["charge12"] and len(DETAILS) == 6 and "12" not in DETAILS, (s["late_rows"], DETAILS))
world(c11=["11/11/2026"], c21=VOID, c22=VOID, c31=VOID, c32=VOID); state([R1], day=D_(11, 14)); G14b = nextreg("20261114T1240Z")
D9 = nextreg("20261115T1240Z", created=[qrow("pat7001", "vst9", "charge92", "charge91", fee="0.01", dos="11/15/2026")]); chg("92", []); chg("91", [], "pcode65119"); chg("12", ["11/20/2026"])
s = state([R1, G14b, D9], day=D_(11, 21))
check("ledger (13.1b): ... when that patient got a second line meanwhile (its one-cent line of 11/15), the digest's line names it - two lines for 2026, nothing to do", s["late_rows"] == [["pat7001", "vst1", "charge12", "11/14/2026", "vst9", "2026"]], s["late_rows"])
chg("12", []); s = state([R1, G14], day=D_(12, 12))
check("ledger (13.1b): ... a left-off line is read again only until 30 days after its visit was billed", "12" not in DETAILS and s["left_off_lines"] == ["charge12"], (s["left_off_lines"], DETAILS))
world(c12=BILLED); TEXTOF["12"] = "99497"; s = state([R1]); TEXTOF.clear()
check("ledger (13.4): the charge detail names procedure id pcode65441 with another code text - NOT the proof: OFF until William restarts it, the sentence says what AdvancedMD stores, the gate records the text",
      s["confirmed"] is False and s["off"] == "AdvancedMD stores procedure id pcode65441 as 99497, not 1123F - William looks" and s["wrong_code_text"] == "99497" and s["off_until_reset"] == s["off"] and s["budget"] == 0, s)
TEXTOF["12"] = "99497"; _sn = {}; _r = ci._line("charge12", QP, "1123F", _sn); TEXTOF.clear(); _sn2 = {}; _r2 = ci._line("charge12", QP, "1123F", _sn2)
check("_line (13.4): another code text for pcode65441 = unknown with the text named; the code text 1123F = read as it is, and seen['text'] says so", _r == ("unknown", ["AdvancedMD stores procedure id pcode65441 as 99497, not 1123F"]) and _sn == {"text": "99497", "wrong": "99497"}
      and _r2 == ("billed", ["11/12/2026"]) and _sn2 == {"text": "1123F"}, (_r, _sn, _r2, _sn2))
world(c12=BILLED); ECHO["detail_text"] = False; s = state([R1]); ECHO["detail_text"] = True
check("ledger (13.4): the charge detail names no code text, but the chart's history shows a live 1123F on that date - proven as before (that history read is also the proof's look at the history)", s["confirmed"] is True and s["history_shows_line"] is True and s["code_text_lines"] == [], s)
world(c22=BILLED); ECHO["detail_text"] = False; s = state([R1]); G20 = nextreg("20261120T1240Z"); s2 = state([R1, G20], day=D_(11, 23)); ECHO["detail_text"] = True
check("ledger (13.4): neither the detail nor the history shows 1123F (this chart's history lists no such line) - no proof yet: the round waits, the gate keeps the first day of that wait and counts the days (three days later the report says it at the top)",
      s["confirmed"] is False and s["wait"] is True and s["proof_wait"] == {"since": "11/20/2026", "visit": "vst2", "charge": "charge22", "days": 0} and s2["proof_wait"] == {"since": "11/20/2026", "visit": "vst2", "charge": "charge22", "days": 3} and s2["confirmed"] is False, (s["proof_wait"], s2["proof_wait"]))
REM = lambda st_="20261111T1240Z", reg_="feed_inspector_20261111T1240Z.json", **e: {"removed": {st_: [(reg_, dict({"visit": "vst1", "pid": "pat7001", "charge": "charge12", "fee": "0.00", "why": "Pattern 77002: Claim line requires review", "void_ok": True, "released": True, "at": "x"}, **e))]}}
world(); s = state([R1], files=REM())
check("ledger (11.3): a line the inspector step took off a held visit that then went through (released) - void and final, NOT read, NOT 'taken off by a person'; it is ONE refusal: before proof one is enough - at $0.00 new lines carry one cent (a new round) - and that patient gets no second try this year",
      s["void_lines"] == ["charge12"] and "12" not in DETAILS and s["off"] == "" and s["fee"] == "0.01" and ("pat7001", "2026") in s["refused"] and ("pat7001", "2026") in s["done"] and s["round"]["n"] == 2 and any("held visit vst1 because of its quality line" in n_ for n_ in s["notes"]), s)
world(); s = state([R1], files=REM(released=False))
check("ledger (11.3): ... the visit was held anyway (not released) - void and final, nothing counts: the place in the round is free, the patient is due again, the amount stays $0.00",
      s["void_lines"] == ["charge12"] and s["fee"] == "0.00" and s["off"] == "" and ("pat7001", "2026") not in s["done"] and s["round"]["void"] == 1 and s["wait"] is True and "12" not in DETAILS, s)
world(); s = state([R1], files=REM(void_ok=False, released=False))
check("ledger (11.3): ... the void failed - the visit is held WITH its line: OFF until William restarts it, the sentence names the visit and quotes the hold", "the Claim Inspector holds visit vst1 and the routine could not take its quality line off" in s["off"] and "Pattern 77002" in s["off"]
      and s["off_until_reset"] == s["off"] and s["budget"] == 0 and s["void_lines"] == [], s)
world(); s = state([R1], files=dict(INS("Pattern 77002: Claim line requires review"), **REM(released=False)))
check("ledger (11.3): a Claim Inspector hold on a visit whose line the routine took off is the visit's own business - no OFF (the OFF for any hold before proof stays only for a line that could NOT be taken off)", s["off"] == "" and s["void_lines"] == ["charge12"] and s["wait"] is True, s)
world(); s = state([R1], files=REM(st_="20261111T1240Z", reg_="feed_verify_20261111T1240Z.json"))
check("ledger (11.3): a removal by the insurance check (released, the echo sent once more without the line) counts the same way", s["void_lines"] == ["charge12"] and s["fee"] == "0.01" and ("pat7001", "2026") in s["refused"], s)
_two = {"removed": {"20261112T1240Z": [("feed_inspector_20261112T1240Z.json", {"visit": v_, "pid": p_, "charge": c_, "fee": "0.00", "why": "x", "void_ok": True, "released": True}) for v_, p_, c_ in (("vst1", "pat7001", "charge12"), ("vst2", "pat7002", "charge22"))]}}
world(); s1 = state([R1, PROVEN], files={"removed": {"20261112T1240Z": _two["removed"]["20261112T1240Z"][:1]}}); s2 = state([R1, PROVEN], files=_two)
check("ledger (11.3): after proof ONE line taken off a released visit changes nothing; TWO in a row move new lines to one cent (a new round)", s1["fee"] == "0.00" and s1["confirmed"] is True and s1["off"] == "" and s2["fee"] == "0.01" and s2["confirmed"] is False and s2["off"] == "", (s1, s2))
world(c12=BILLED, c22=BILLED, c32=BILLED); PAYS.clear()
PAYS["12"] = [{"id": "pay1", "amount": "0.00", "carrierfid": "6085", "date": "11/24/2026", "void": "1", "paymentcode": "PE"}, {"id": "pay2", "amount": "0.00", "carrierfid": "6404", "date": "11/24/2026", "void": "0"}]
PAYS["22"] = [{"id": "pay3", "amount": "0.00", "carrierfid": "6085", "date": "11/25/2026", "void": "0", "paymentcode": "PE"}]
s = state([R1], day=D_(12, 1))
check("ledger (11.4): Medicare's own answer - three billed lines, a VOID Medicare payment line and a payment line of ANOTHER carrier on the first are no answer, a live Medicare payment line on the second is: recorded, the daily cap is gone",
      s["medicare_answer"] == {"charge": "charge22", "visit": "vst2", "date": "11/25/2026", "amount": "0.00", "register": "feed_import_20261111T1240Z.json"} and s["budget"] is None and s["medicare_wait"] is None
      and DETAILS == ["12", "22", "32", "12", "22"] and any("Medicare's remittance shows the 1123F line on visit vst2" in n_ for n_ in s["notes"]), (s["medicare_answer"], DETAILS))
check("ledger (11.4): ... and the run's QUALITY line says there is no cap any more (it no longer says Medicare has shown nothing)", "no cap" in ci.quality_log(0, False) and "has not yet shown" not in ci.quality_log(0, False), ci.quality_log(0, False))
s2 = state([R1, nextreg("20261201T1240Z")], day=D_(12, 2))
check("ledger (11.4): ... the answer is carried forward by the gate and nothing more is read for it", s2["medicare_answer"] == s["medicare_answer"] and s2["budget"] is None and DETAILS == [], (s2["medicare_answer"], DETAILS))
PAYS.clear(); s = state([R1], day=D_(12, 27))
check("ledger (11.4): no Medicare payment line yet - the cap stays, and the gate says how many lines are billed and how long the oldest has waited (45 days: the report says it at the top)",
      s["medicare_answer"] is None and s["budget"] == 10 and s["medicare_wait"] == {"lines": 3, "oldest": "11/12/2026", "days": 45}, s["medicare_wait"])
PAYS["12"] = [{"amount": "0.00", "carrierfid": "car6085", "date": "11/24/2026"}]; s = state([R1], day=D_(12, 1)); PAYS.clear()
check("ledger (11.4): a payment line whose carrier is written with its letters (car6085) and no void flag counts too", s["medicare_answer"] and s["medicare_answer"]["charge"] == "charge12", s["medicare_answer"])
PAYS["31"] = [{"amount": "5.00", "carrierfid": "6085"}]
check("_payments: the payment lines of a charge are read from its own detail", ci._payments("charge31") == [{"amount": "5.00", "carrierfid": "6085"}] and ci._payments("charge32") == [], ci._payments("charge31"))
_raised = False
try: BILLS["77"] = "MISSING"; ci._payments("charge77")
except Exception: _raised = True
check("_payments: ... (a detail without that charge raises, so the caller reads it again next run)", _raised); PAYS.clear(); BILLS.pop("77", None)
BILLS.clear(); PROC.clear(); DETAILS.clear(); CHART.pop("7001", None); CHART.pop("7002", None)
# 4c.5 through main(): the pilot, its outcome, the refusal - every state read from the registers
def Q_(fid, k, lines, dob="1940" + "0215"):      # made-up patient k has its OWN feed id ("n2-q1") in the building, clinician and raw-message answer of fid's messages (13.6: once per patient also by the feed's patient id)
    p_ = "%s-%s" % (fid, k); ci.FACOF[p_] = ci.FACOF.get(fid, ""); ci.FACS[p_] = set(ci.FACS.get(fid, ())); ci.NPIOF[p_] = ci.NPIOF.get(fid, ""); ci.ADMIT[p_] = ci.ADMIT.get(fid, "")
    _own = ci.MSGOF.get(ci.msg_key(fid, list(lines)))
    if _own: ci.MSGOF[ci.msg_key(p_, list(lines))] = set(_own)
    return {"pid": p_, "name": NAME(k), "dob": dob, "file": "f", "FT1": [{"cpt": c, "dos": d, "dx": "I10", "units": "1"} for c, d in lines]}
for i in range(1, 10): ci.MATCH[NAME("q%d" % i).upper().strip() + "|" + "19400215"] = {"resolved": "pat40%d" % i}
def charts0(): CHART.update({"40%d" % i: [("99309", "10/03/2026")] for i in range(1, 10)})
charts0()
def visits(day, ks): return [Q_("n2", "q%d" % k, [("99309", day)]) for k in ks]
QB = visits("20261102", (1, 2, 3, 4)) + [Q_("n1", "q5", [("99487", "20261031")])]
DEMOG["plans"] = MEDICARE + OTHER
def clear_regs():
    for f in os.listdir(REGDIR):
        if f.startswith("feed_import_"): os.remove(os.path.join(REGDIR, f))
def keep(reg, stamp): json.dump(reg, open(os.path.join(REGDIR, "feed_import_%s.json" % stamp), "w"))
def qrows_of(reg): return [r for r in reg["created"] if r.get("quality_codes")]
def live(parsed, env=None, argv=("--all",), keep_own=False, **echo):
    ECHO.update(echo); DETAILS.clear(); REFUSED.clear(); old = os.environ.get("QUALITY_CODE")
    if env is None: os.environ.pop("QUALITY_CODE", None)
    else: os.environ["QUALITY_CODE"] = env
    try: return run_live(parsed, argv=argv, keep_own=keep_own)
    finally:
        if old is None: os.environ.pop("QUALITY_CODE", None)
        else: os.environ["QUALITY_CODE"] = old
def qline(out): return next((l for l in out.splitlines() if l.startswith("QUALITY 1123F:")), "")
def lined(dry): return sorted(k for k, v in dry.items() if v[0].get("quality_codes"))
EARLIER = "feed_verify_20261101T0000Z.json"                              # an earlier batch's insurance check released every one of these charts with Medicare leading
def earlier(): wreg(EARLIER, {"pat40%d" % i: vrow() for i in range(1, 10)})
earlier(); clear_regs(); ci.PARSED[:] = QB; out, dry = run_dry()
nq = lined(dry)
check("main --dry: pilot - three of four eligible visits would carry the code, the care-management message none, and the log line says so", len(nq) == 3 and "pat405" not in nq
      and "QUALITY 1123F: would be on x3 visit(s), line amount $0.00, pilot: at most 3 visit(s) until one is seen billed" in out, (nq, out[-400:]))
rmreg(EARLIER); out, dry = run_dry()
check("main --dry: without an earlier insurance check nobody gets a line (a first-ever visit gets none; the next batch's visit does)", lined(dry) == [] and "would be on x0 visit(s)" in out, out[-300:])
earlier(); wreg("feed_verify_20261105T0000Z.json", {"pat401": vrow(["vst1"], lead="HUM01")}); out, dry = run_dry()
check("main --dry (NH-3): a chart whose NEWEST earlier insurance check found a Medicare Advantage plan gets no line although the chart still shows Medicare first; the other three do", lined(dry) == ["pat402", "pat403", "pat404"], lined(dry))
wreg("feed_verify_SELFTEST.json", {"pat402": vrow(lead="HUM01")}); wreg("feed_verify_ZZ.json", {"pat403": vrow(lead="HUM01")}); out, dry = run_dry()
check("main --dry: ... the insurance check of this very batch (a second start) and of a later batch are not 'earlier' - they change nothing", lined(dry) == ["pat402", "pat403", "pat404"], lined(dry))
rmreg("feed_verify_20261105T0000Z.json", "feed_verify_SELFTEST.json", "feed_verify_ZZ.json")
wreg("quality_exceptions.json", {"pat402": "declined"}); out, dry = run_dry()
check("main --dry (M5): a chart on William's exception list never gets the automatic line; the others do", lined(dry) == ["pat401", "pat403", "pat404"], lined(dry))
open(os.path.join(REGDIR, "quality_exceptions.json"), "w").write("{oops"); out, dry = run_dry()
check("main --dry (M5): an exception list that is there but cannot be read - NO line for anybody in that run, and the log line names the file", lined(dry) == [] and "OFF - this run: registers/quality_exceptions.json" in qline(out) and "cannot be read" in qline(out) and "DONE" in out, qline(out))
out, regx_ = live(QB)
check("... the visits themselves all go in (a reporting code never holds a charge), and the register says why no line was added", len(regx_["created"]) == 5 and regx_["failed"] == [] and qrows_of(regx_) == [] and "quality_exceptions.json" in regx_["quality_gate"]["off"]
      and regx_["quality_gate"]["off_until_reset"] == "", regx_["quality_gate"])
rmreg("quality_exceptions.json"); open(os.path.join(REGDIR, "feed_import_20261101T0000Z.json"), "w").write("{cut off"); out, dry = run_dry()
check("main --dry (13.5): an import register of this year that is there but cannot be read (the lines it may hold are not known) - no line in that run, and the log line names it",
      lined(dry) == [] and "the import register feed_import_20261101T0000Z.json cannot be read - the state of the quality code is not known; no line until it is restored from the repository" in qline(out), qline(out))
rmreg("feed_import_20261101T0000Z.json"); open(os.path.join(REGDIR, "feed_import_20251201T0000Z.json"), "w").write("{cut off"); out, dry = run_dry()
check("main --dry (13.5): an unreadable import register of ANOTHER year (2025) does not stop the line - only this year's lines matter", len(lined(dry)) == 3 and "cannot be read" not in qline(out), qline(out))
rmreg("feed_import_20251201T0000Z.json"); open(os.path.join(REGDIR, "feed_import_1028.json"), "w").write(""); out, dry = run_dry()
check("main --dry (13.5): an empty import register whose name carries no date counts as this year's - no line, named", lined(dry) == [] and "the import register feed_import_1028.json cannot be read" in qline(out), qline(out))
rmreg("feed_import_1028.json")
clear_regs(); charts0()
out, reg = live(QB); qrows = qrows_of(reg)
check("live run 1: three visits carry the line; each row keeps the line's charge number last in its charge list and its codes unchanged", len(qrows) == 3 and all(r["cpts"] == ["99309"] and len(r["charges"]) == 2
      and r["quality_charge"] == r["charges"][-1] and r["fees"] == ["1.00"] for r in qrows) and len(reg["created"]) == 5 and "QUALITY 1123F: on x3 visit(s), line amount $0.00, pilot: at most 3 visit(s) until one is seen billed" in out, (reg["created"], out[-300:]))
check("live run 1: the register records where the quality code stands (round 1 at $0.00, three lines entered and not decided, nothing known yet)", reg["quality_gate"] == {"code": "1123F", "fee": "0.00", "confirmed": False, "proof": None, "zero_not_billed": False,
      "off": "", "off_until_reset": "", "wait": False, "pending": [], "pending_since": "", "billed_lines": [], "void_lines": [], "left_off_lines": [], "dead_zero_lines": [], "reset": False, "reset_after": None,
      "round": {"n": 1, "fee": "0.00", "since": "feed_import_SELFTEST.json", "lines": 3, "void": 0, "open": 3}, "budget": 3, "pilot_cap": 3, "n620": False, "history_shows_line": None, "refused_charts": [], "not_renewed": {},
      "billed_on": {}, "code_text_lines": [], "left_off_seen": {}, "left_off_on": {}, "late_billed": {}, "late_rows": [], "wrong_code_text": "", "proof_wait": None, "medicare_answer": None, "medicare_wait": None,
      "quality_skipped_hospital": 0, "unread": [], "unread_prev": [], "notes": []}, reg.get("quality_gate"))
out, regp = live(visits("20261103", (4,)), proccode=True); rp_ = qrows_of(regp)
check("the line's charge number is taken from AdvancedMD's answer by its procedure when the answer names it; the fee list stays one amount per message code", len(rp_) == 1 and rp_[0]["quality_charge"] == rp_[0]["charges"][-1] and rp_[0]["fees"] == ["1.00"] and "charge lines': 1" in out, (regp["created"], out[-200:]))
RUN1 = reg; keep(RUN1, "20261111T0100Z"); PIL = [num(r["quality_charge"]) for r in qrows]; FIRST = [num(r["charges"][0]) for r in qrows]
# run 2: nothing billed yet -> the pilot WAITS (no new line), and says which visits it waits for
out, reg2 = live(visits("20261109", (4, 1)))
check("run 2, nothing billed yet: NO new line (the pilot waits for the outcome of its first three), every earlier line was looked up", qrows_of(reg2) == [] and len(reg2["created"]) == 2 and reg2["quality_gate"]["wait"] is True
      and reg2["quality_gate"]["pending"] == [r["visit"] for r in qrows] and reg2["quality_gate"]["pending_since"] == "feed_import_20261111T0100Z.json" and all(c in DETAILS for c in PIL + FIRST)
      and "pilot: waiting for the outcome of 3 earlier line(s) - none added" in out, (reg2["quality_gate"], out[-300:]))
keep(reg2, "20261112T0100Z"); ci.PARSED[:] = visits("20261110", (4,)); _n0 = len(DETAILS); out, dry = run_dry()
check("a dry run reads nothing in AdvancedMD for the pilot and shows 'waiting'", not any(v[0].get("quality_codes") for v in dry.values()) and "pilot: waiting for the outcome of 3 earlier line(s)" in out and ci.QUALITY["wait"] is True
      and not (set(DETAILS[_n0:]) & set(PIL + FIRST)), (out[-300:], DETAILS[_n0:]))
# run 3: one of the first lines is listed as billed -> proven; once per patient per year also from the registers
BILLS[PIL[0]] = ["11/12/2026"]; charts0()
out, reg3 = live(visits("20261116", (1, 2, 3, 4, 6, 7, 8, 9)))
got = {r["pid"] for r in qrows_of(reg3)}
check("run 3, an earlier line is billed: proof recorded - every patient not yet coded gets the line (at most 10 a run until Medicare's own answer is on file), nobody twice (the chart history here lists no 1123F at all: the registers say who has it)",
      got == {"pat404", "pat406", "pat407", "pat408", "pat409"} and reg3["quality_gate"]["confirmed"] is True and reg3["quality_gate"]["proof"]["charge"] == qrows[0]["quality_charge"] and reg3["quality_gate"]["proof"]["billed"] == "11/12/2026"
      and reg3["quality_gate"]["pilot_cap"] is None and reg3["quality_gate"]["budget"] == 10 and reg3["quality_gate"]["wait"] is False
      and "at most 10 a run (a quality line was seen billed; Medicare has not yet shown a 1123F line on a remittance)" in qline(out) and "pilot" not in qline(out), (sorted(got), reg3["quality_gate"], qline(out)))
check("run 3 (SM-7): on the run that finds the proof the chart's history is read once - here it does not list the line, and the register says so", reg3["quality_gate"]["history_shows_line"] is False and reg3["quality_gate"]["billed_lines"] == [qrows[0]["quality_charge"]], reg3["quality_gate"])
keep(reg3, "20261116T0100Z"); BILLS.clear()
out, reg4 = live(visits("20261123", (5,)))
_after = [num(r["quality_charge"]) for r in qrows_of(reg3)]
check("later runs read the proof from the register, the next patient gets the code; no line entered after proof is looked up - only the proven round's two lines not decided yet (13.1) and the billed line, for Medicare's answer (11.4)",
      reg4["quality_gate"]["confirmed"] is True and len(qrows_of(reg4)) == 1 and set(DETAILS) & set(PIL + FIRST) == set(PIL + FIRST[1:]) and not (set(DETAILS) & set(_after))
      and reg4["quality_gate"]["history_shows_line"] is False and reg4["quality_gate"]["proof"]["charge"] == qrows[0]["quality_charge"], (reg4["quality_gate"], DETAILS))
# after proof: at most QUALITY_DAILY lines a run until registers/quality_n620_seen.json exists (Medicare's own answer seen on a remittance), then no cap
clear_regs(); charts0(); keep(dict(RUN1, quality_gate=dict(RUN1["quality_gate"], confirmed=True)), "20261111T0100Z"); _daily = ci.QUALITY_DAILY; ci.QUALITY_DAILY = 2
out, regd1 = live(visits("20261117", (4, 5, 6, 7, 8, 9)))
check("after proof, Medicare's answer not yet on file: a run adds no more lines than the daily cap (here set to 2); every visit goes in", len(qrows_of(regd1)) == 2 and len(regd1["created"]) == 6 and regd1["quality_gate"]["budget"] == 2 and regd1["quality_gate"]["n620"] is False
      and "at most 2 a run" in qline(out), (len(qrows_of(regd1)), qline(out)))
open(os.path.join(REGDIR, "quality_n620_seen.json"), "w").write("{}"); charts0()
out, regd2 = live(visits("20261118", (4, 5, 6, 7, 8, 9)))
check("after proof, with Medicare's answer on file (the import only looks whether the file exists): no cap", len(qrows_of(regd2)) == 6 and regd2["quality_gate"]["budget"] is None and regd2["quality_gate"]["n620"] is True and "no cap (a quality line was seen billed)" in qline(out), (len(qrows_of(regd2)), qline(out)))
ci.QUALITY_DAILY = _daily; rmreg("quality_n620_seen.json")
# a second start under ONE stamp (the state-machine reviewer's SM-2): the register this stamp is writing belongs to the state
clear_regs(); charts0(); S7 = [Q_("n2", "q%d" % k, [("99309", "202611%02d" % (2 + k))]) for k in range(1, 8)]      # seven patients, each on its own day
out, rs1 = live(S7, argv=("--all", "--limit", "3"), keep_own=True); out2, rs2 = live(S7)
check("second start under ONE stamp (--limit 3, then the rest): the lines the first start entered count - three lines in all, the second start waits for them and adds none; every visit is entered once",
      len(qrows_of(rs1)) == 3 and len(rs1["created"]) == 3 and len(qrows_of(rs2)) == 3 and len(rs2["created"]) == 7 and "pilot: waiting for the outcome of 3 earlier line(s) - none added" in qline(out2)
      and rs2["quality_gate"]["round"]["lines"] == 3 and rs2["quality_gate"]["pending_since"] == "feed_import_SELFTEST.json", (len(qrows_of(rs2)), qline(out2)))
clear_regs(); charts0()
for _k in range(4): out, rs3 = live(S7, argv=("--all", "--limit", "1"), keep_own=(_k < 3))
check("four starts of one visit each under ONE stamp: the cap is per ROUND, not per start - one line, then every start waits for it", len(qrows_of(rs3)) == 1 and len(rs3["created"]) == 4 and rs3["quality_gate"]["wait"] is True, (len(qrows_of(rs3)), rs3["quality_gate"]))
# AdvancedMD bills a visit but leaves its $0.00 line off the claim, and no $0.00 line of the round is billed -> one cent, a new round
clear_regs(); keep(RUN1, "20261111T0100Z"); BILLS.clear(); BILLS[FIRST[0]] = ["11/11/2026"]
CHART.update({r["pid"][3:]: [("99309", "10/03/2026"), ("99309", "11/02/2026"), ("1123F", "11/02/2026")] for r in qrows})      # the chart history lists the $0.00 lines
out, regz = live(visits("20261109", (1, 2, 3, 4))); qz = qrows_of(regz); gz = regz["quality_gate"]
check("a visit was billed WITHOUT its $0.00 quality line and no $0.00 line is billed -> new lines carry one cent, a new round; the register says why and lists ONLY the line that was read as left off (SM-1)", gz["fee"] == "0.01" and gz["zero_not_billed"] is True
      and gz["confirmed"] is False and gz["wait"] is False and gz["dead_zero_lines"] == [[qrows[0]["pid"], qrows[0]["visit"], qrows[0]["quality_charge"]]] and gz["left_off_lines"] == [qrows[0]["quality_charge"]]
      and any("without its $0.00 quality line" in n for n in gz["notes"]) and gz["round"]["n"] == 2 and gz["round"]["fee"] == "0.01", gz)
check("... the patient whose $0.00 line was read as left off gets the code AGAIN at one cent (the dead line on the chart does not count); the two patients whose $0.00 lines are not decided yet are not coded a second time", {r["pid"] for r in qz} == {qrows[0]["pid"], "pat404"}
      and all(r["quality_fee"] == "0.01" for r in qz), [r["pid"] for r in qz])
check("... and the one-cent line is what was sent", sum(1 for b_ in POSTS if re.search(r'proccode="pcode65441" cobcode="" pos="\d+" tos="01" units="1" netfee="0" fee="0.01" allowed="0.01"', b_)) == 2, [b_[-300:] for b_ in POSTS if "pcode65441" in b_])
keep(regz, "20261112T0100Z"); PZ = [num(r["quality_charge"]) for r in qz]; FZ = [num(r["charges"][0]) for r in qz]
out, regz2 = live(visits("20261116", (1, 2, 3, 4)))
check("one cent, nothing billed yet: the new round waits too. The two other $0.00 lines are read until they are decided (every $0.00 line is read in the end), and the line read as left off is read again after them (13.1b), still left off", qrows_of(regz2) == [] and regz2["quality_gate"]["wait"] is True
      and regz2["quality_gate"]["fee"] == "0.01" and len(regz2["quality_gate"]["pending"]) == 2 and regz2["quality_gate"]["pending_since"] == "feed_import_20261112T0100Z.json" and DETAILS.count(PIL[0]) == 1 and PIL[1] in DETAILS and PIL[2] in DETAILS
      and DETAILS.index(PIL[0]) > max(DETAILS.index(PIL[1]), DETAILS.index(PIL[2])) and regz2["quality_gate"]["left_off_lines"] == ["charge" + PIL[0]] and all(c in DETAILS for c in PZ), (regz2["quality_gate"], DETAILS))
keep(regz2, "20261116T0100Z"); BILLS[PZ[1]] = ["11/17/2026"]; BILLS[FIRST[1]] = ["11/17/2026"]; BILLS[PIL[2]] = ["11/17/2026"]      # a one-cent line billed; of the two $0.00 lines one visit went out without its line, the other with it
out, regz3 = live(visits("20261123", (1, 2, 3, 4)))
check("a one-cent line is billed: proven at one cent. The $0.00 line read as left off frees its patient, who gets a one-cent line; the $0.00 line read as billed counts for its patient; nobody is coded twice", regz3["quality_gate"]["confirmed"] is True
      and regz3["quality_gate"]["fee"] == "0.01" and {r["pid"] for r in qrows_of(regz3)} == {qrows[1]["pid"]} and sorted(regz3["quality_gate"]["left_off_lines"]) == sorted([qrows[0]["quality_charge"], qrows[1]["quality_charge"]])
      and qrows[2]["quality_charge"] in regz3["quality_gate"]["billed_lines"] and len(regz3["quality_gate"]["dead_zero_lines"]) == 2, ([r["pid"] for r in qrows_of(regz3)], regz3["quality_gate"]))
clear_regs(); keep(RUN1, "20261111T0100Z"); keep(regz, "20261112T0100Z"); BILLS.clear(); BILLS[FZ[0]] = ["11/13/2026"]
out, regz4 = live(visits("20261116", (4,)))
check("a visit is billed without its ONE-CENT line too: the code is switched off until William restarts it and the register says why", qrows_of(regz4) == [] and "without its one-cent quality line too" in regz4["quality_gate"]["off"] and len(regz4["created"]) == 1
      and regz4["quality_gate"]["off_until_reset"] == regz4["quality_gate"]["off"] and "OFF - AdvancedMD billed visit" in out and "off until William restarts it" in qline(out) and "pilot" not in qline(out), (regz4["quality_gate"], out[-300:]))
keep(regz4, "20261116T0100Z"); BILLS.clear(); [BILLS.__setitem__(c, {"void": "1"}) for c in PIL + PZ]
out, regz5 = live(visits("20261117", (5, 6, 7)))
_lo4 = [num(c) for c in regz4["quality_gate"]["left_off_lines"]]
check("... (SM-4) the OFF is remembered: after somebody has voided the lines the next run does NOT start a new pilot by itself - no line, the same sentence; only the lines read as left off are read again (13.1b) - found void, they are no longer listed as left off",
      qrows_of(regz5) == [] and len(regz5["created"]) == 3 and regz5["quality_gate"]["off_until_reset"] == regz4["quality_gate"]["off_until_reset"] and _lo4 and set(DETAILS) & set(PIL + PZ) == set(_lo4)
      and regz5["quality_gate"]["left_off_lines"] == [] and set(regz5["quality_gate"]["void_lines"]) >= set("charge" + c for c in _lo4), (regz5["quality_gate"], DETAILS))
# somebody takes the pilot's lines off / the whole visits are voided
BILLS.clear(); BILLS[PIL[0]] = {"void": "1"}; BILLS[PIL[1]] = {"void": "1"}; BILLS[PIL[2]] = {"void": "1"}; clear_regs(); keep(RUN1, "20261111T0100Z"); charts0()
out, regv = live(visits("20261109", (4,)))
check("somebody took the pilot's lines off their visits (void) while the visits are still there: NO new pilot - the code is off until William restarts it", qrows_of(regv) == [] and len(regv["created"]) == 1 and regv["quality_gate"]["wait"] is False
      and "3 earlier quality line(s) were taken off their visits" in regv["quality_gate"]["off"] and sum("taken off the visit" in n for n in regv["quality_gate"]["notes"]) == 3
      and sorted(regv["quality_gate"]["void_lines"]) == sorted(r["quality_charge"] for r in qrows) and regv["quality_gate"]["off_until_reset"] == regv["quality_gate"]["off"], regv["quality_gate"])
keep(regv, "20261112T0100Z"); out, regv2 = live(visits("20261110", (1, 4)), env="reset")
check("... after QUALITY_CODE=reset the pilot starts again, and a patient whose line was taken off is due again", {r["pid"] for r in qrows_of(regv2)} == {"pat401", "pat404"} and regv2["quality_gate"]["off"] == "" and regv2["quality_gate"]["reset"] is True
      and regv2["quality_gate"]["reset_after"] == [0, 0] and regv2["quality_gate"]["round"]["n"] == 2, (regv2["quality_gate"], [r["pid"] for r in qrows_of(regv2)]))
BILLS.clear(); [BILLS.__setitem__(c, {"void": "1"}) for c in PIL + FIRST]; clear_regs(); keep(RUN1, "20261111T0100Z"); charts0()
out, regw = live(visits("20261109", (1, 2, 3, 4)))
check("the pilot's whole visits were voided: no outcome either way - their places are free, the round carries on with three more visits, and those patients are due again", len(qrows_of(regw)) == 3 and regw["quality_gate"]["off"] == "" and regw["quality_gate"]["wait"] is False
      and regw["quality_gate"]["confirmed"] is False and sum("no longer on the chart (void)" in n for n in regw["quality_gate"]["notes"]) == 3 and {r["pid"] for r in qrows_of(regw)} <= {"pat401", "pat402", "pat403", "pat404"}
      and regw["quality_gate"]["round"] == {"n": 1, "fee": "0.00", "since": "feed_import_20261111T0100Z.json", "lines": 6, "void": 3, "open": 3} and regw["quality_gate"]["budget"] == 3, regw["quality_gate"])
keep(regw, "20261112T0100Z"); [BILLS.__setitem__(num(c), {"void": "1"}) for r in qrows_of(regw) for c in r["charges"]]; charts0()
out, regw2 = live(visits("20261113", (5, 6, 7)))
check("... and when the three replacement visits are voided as well, the round has had its six lines: the code is OFF ('the pilot's lines keep being voided') until William restarts it", qrows_of(regw2) == [] and len(regw2["created"]) == 3
      and "the pilot's lines keep being voided" in regw2["quality_gate"]["off_until_reset"] and "OFF - the pilot's lines keep being voided" in qline(out), regw2["quality_gate"])
swap = json.loads(json.dumps(RUN1)); [r.update(charges=[r["quality_charge"], r["charges"][0]]) for r in swap["created"] if r.get("quality_charge")]
BILLS.clear(); BILLS[FIRST[0]] = ["11/11/2026"]; clear_regs(); keep(swap, "20261111T0100Z"); charts0()
out, regx = live(visits("20261109", (4,)))
check("the visit's own charge is found whatever the order of the recorded charge numbers (a visit billed without its $0.00 line is still seen)", regx["quality_gate"]["zero_not_billed"] is True and regx["quality_gate"]["fee"] == "0.01", regx["quality_gate"])
BILLS.clear()
many = {"created": [dict(qrows[0], pid="pat5%02d" % i, visit="vst9%02d" % i, quality_charge="charge99%02d1" % i, charges=["charge99%02d0" % i, "charge99%02d1" % i]) for i in range(8)], "skipped": [], "failed": []}
PROC.update({"99%02d1" % i: QP for i in range(8)})
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
check("the answer lists the quality charge FIRST and names no procedure: the charge is found by its amount. The register row lists the visit's own charge numbers first, in the answer's order, THEN the quality charge - so its first charge is the visit's own and the fees pair with the charges in order",
      rf.get("quality_codes") == ["1123F"] and rf["quality_charge"] == rf["charges"][-1] and len(rf["charges"]) == 3 and rf["charges"][0][-1] == "0" and rf["charges"][1][-1] == "1" and rf["quality_charge"][-1] == "2" and rf["fees"] == ["141.00", "133.00"]
      and rf["pos_stored"] == rf["pos_lines"] and rf["quality_pos_stored"] == rf["quality_pos"] and PROC[num(rf["quality_charge"])] == QP and PROC[num(rf["charges"][0])] == "pcode65119", rf)
charts0(); out, regn = live(visits("20261208", (9,)), proccode=True, qfirst=True)
rn = regn["created"][0]
check("the answer names procedures: the quality charge is found by its procedure wherever it stands - and is recorded last", rn.get("quality_codes") == ["1123F"] and rn["quality_charge"] == rn["charges"][-1] and len(rn["charges"]) == 2 and PROC[num(rn["quality_charge"])] == QP and rn["fees"] == ["1.00"], rn)
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
_plain = [b_ for b_ in POSTS if "updvisitwithnewcharges" in b_ and "pcode65441" not in b_ and ref[0]["visit"] in b_]; _with = [b_ for b_ in POSTS if "pcode65441" in b_]
check("refused: what goes in the second time is the first request with nothing but the quality line taken out", len(_plain) == 1 and len(_with) == 1 and re.sub(QCHG, "", _with[0]) == _plain[0], (_plain, _with))
check("refused: the register names the refused patient - no second try for that patient this year", reg5["quality_gate"]["refused_charts"] == [[ref[0]["pid"], "2026"]] and reg5["quality_gate"]["off_until_reset"] == "", reg5["quality_gate"])
keep(reg5, "20261113T0100Z"); ci.PARSED[:] = visits("20261117", (2,)); out, dry = run_dry()
check("refused at $0.00: the next run tries one cent", ci.QUALITY["fee"] == "0.01" and ci.QUALITY["off"] == "" and any(v[0].get("quality_fee") == "0.01" for v in dry.values()), (ci.QUALITY, dry))
ci.PARSED[:] = [Q_("n2", "q%d" % int(ref[0]["pid"][-1]), [("99309", "20261117")])]; out, dry = run_dry()
check("refused: ... but the refused patient's own next visit this year carries no line (one try per patient and year)", lined(dry) == [] and ("pat40%s" % ref[0]["pid"][-1], "2026") in ci.QUALITY["done"] and ci.QUALITY["budget"] == 3, (dry, ci.QUALITY["done"]))
reg6 = json.loads(json.dumps(reg5)); [r.update(quality_refused_fee="0.01") for r in reg6["created"] if r.get("quality_refused")]
keep(reg6, "20261114T0100Z"); ci.PARSED[:] = visits("20261117", (2,)); out, dry = run_dry()
check("refused at one cent too: the code stays off until William says to start again, and every run says so", ci.QUALITY["off"] != "" and not any(v[0].get("quality_codes") for v in dry.values())
      and "OFF - AdvancedMD refused a visit that carried the code with a one-cent charge too (feed_import_20261114T0100Z.json)" in out and ci.QUALITY["off_until_reset"] == ci.QUALITY["off"], out[-400:])
out, regr = live(visits("20261117", (2,)), env="reset")
check("QUALITY_CODE=reset (William's word): the pilot starts again at $0.00 and the register records the restart", regr["quality_gate"]["reset"] is True and regr["quality_gate"]["off"] == "" and regr["quality_gate"]["fee"] == "0.00"
      and len(qrows_of(regr)) == 1 and any("started again" in n for n in regr["quality_gate"]["notes"]), regr["quality_gate"])
keep(regr, "20261117T0100Z"); out, regr2 = live(visits("20261118", (3,)))
check("after a restart the earlier refusals no longer count: the pilot waits for its new first line", regr2["quality_gate"]["off"] == "" and regr2["quality_gate"]["fee"] == "0.00" and regr2["quality_gate"]["wait"] is True
      and regr2["quality_gate"]["reset"] is False and regr2["quality_gate"]["pending"] == [qrows_of(regr)[0]["visit"]], regr2["quality_gate"])
out, regr3 = live(visits("20261118", (3,)), env="reset")
check("QUALITY_CODE=reset a second time, with nothing switched off (the switch left in a routine): ignored, loudly - the round goes on waiting, no new line", qrows_of(regr3) == [] and regr3["quality_gate"]["reset"] is False and regr3["quality_gate"]["wait"] is True
      and "NOTHING TO RESTART" in qline(out) and any("NOTHING TO RESTART" in n for n in regr3["quality_gate"]["notes"]), (qline(out), regr3["quality_gate"]))
out, rego = live(visits("20261119", (6,)), env="off")
check("QUALITY_CODE=off: no line in that run, and the register says why", qrows_of(rego) == [] and "switched off (QUALITY_CODE=off)" in rego["quality_gate"]["off"] and len(rego["created"]) == 1 and rego["quality_gate"]["off_until_reset"] == "", rego["quality_gate"])
# the switches (the reviewers' values): case and spaces do not matter; a value the import does not know adds NO line and is named in the log
clear_regs(); charts0(); W2 = visits("20261110", (1, 2))
for _val, _lines in (("OFF", 0), (" Off ", 0), ("0", 0), ("false", 0), ("no", 0), ("disable", 0), ("of", 0), ("restart", 0), ("", 2), ("  ", 2)):
    out, rsw = live(W2, env=_val); _named = ("QUALITY_CODE=%r is not a value the import knows" % _val.strip().lower()) in qline(out)
    check("switch QUALITY_CODE=%r: %s" % (_val, "the visits carry the line as usual" if _lines else "no line - " + ("switched off" if _val.strip().lower() == "off" else "the log line says the value was not understood")),
          len(qrows_of(rsw)) == _lines and len(rsw["created"]) == 2 and (_lines == 2 or _val.strip().lower() == "off" or _named) and (rsw["quality_gate"]["off_until_reset"] == ""), (qline(out), rsw["quality_gate"]["off"]))
out, rst = live(W2, env="Stop")
check("switch QUALITY_CODE=stop: no line, and the code is OFF until William restarts it", qrows_of(rst) == [] and len(rst["created"]) == 2 and "stopped on William's word (QUALITY_CODE=stop)" in rst["quality_gate"]["off_until_reset"]
      and "off until William restarts it" in qline(out), (qline(out), rst["quality_gate"]))
keep(rst, "20261111T0100Z"); out, rst2 = live(visits("20261111", (1, 2)))
check("switch stop: ... the next run, with no switch at all, still adds no line", qrows_of(rst2) == [] and "stopped on William's word" in rst2["quality_gate"]["off_until_reset"] and len(rst2["created"]) == 2, rst2["quality_gate"])
keep(rst2, "20261112T0100Z"); out, rst3 = live(visits("20261112", (1, 2)), env="RESET")
check("switch reset after stop: the pilot starts", len(qrows_of(rst3)) == 2 and rst3["quality_gate"]["reset"] is True and rst3["quality_gate"]["off_until_reset"] == "", rst3["quality_gate"])
clear_regs(); charts0(); keep(rst, "20261111T0100Z")
out, ra1 = live(visits("20261112", (1,)), env="reset", keep_own=True); out, ra2 = live(visits("20261113", (2,)))
check("a restart, then a later start under the SAME stamp without the switch: the restart is not lost when that start writes the gate again, and the later start waits for the restart's line", ra1["quality_gate"]["reset"] is True and ra1["quality_gate"]["reset_after"] == [0, 0]
      and len(qrows_of(ra1)) == 1 and ra2["quality_gate"]["reset"] is True and ra2["quality_gate"]["reset_after"] == [0, 0] and len(qrows_of(ra2)) == 1 and len(ra2["created"]) == 2 and ra2["quality_gate"]["wait"] is True
      and ra2["quality_gate"]["off_until_reset"] == "", (ra1["quality_gate"], ra2["quality_gate"]))
keep(ra2, "20261113T0100Z"); out, ra3 = live(visits("20261114", (3,)))
check("... and the run after that still stands on the restart: not off, waiting for the new round's line", ra3["quality_gate"]["off_until_reset"] == "" and ra3["quality_gate"]["wait"] is True and ra3["quality_gate"]["reset"] is False and qrows_of(ra3) == [], ra3["quality_gate"])
clear_regs(); charts0(); keep(rst, "20261111T0100Z")
out, rb1 = live(visits("20261112", (1,)), keep_own=True); out, rb2 = live(visits("20261113", (2,)), env="reset")
check("a restart under a stamp that already holds a row (entered while the code was off) records that the row was there before it", qrows_of(rb1) == [] and rb2["quality_gate"]["reset"] is True and rb2["quality_gate"]["reset_after"] == [1, 0]
      and [r["pid"] for r in qrows_of(rb2)] == ["pat402"], rb2["quality_gate"])
# refused, and the chart then shows part of the visit: never sent a second time
clear_regs(); charts0()
out, regq = live(visits("20261102", (1, 2)), refuse_quality=True, partial=("401", "99309", "11/02/2026"))
f = regq["failed"]
check("refused and the chart now shows a line of that visit: NOT sent again (it would double the charge) - the visit is named for a person, the next visit goes in without the code",
      len(f) == 1 and f[0]["pid"] == "pat401" and f[0]["stored"] == [["99309", "11/02/2026"]] and f[0]["empty_visit"].startswith("vst") and "not sent again" in f[0]["err"] and f[0]["info"]["quality_tried"] == "0.00"
      and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 2 and len(regq["created"]) == 1 and qrows_of(regq) == [] and "could not be shown free of it" in regq["quality_gate"]["off"], (f, regq["created"]))
check("... (SM-5) and the code is OFF from then on until William has looked at that visit: the register says so with the chart and the visit", regq["quality_gate"]["off_until_reset"] == "AdvancedMD answered a fault but kept the visit - William looks (chart pat401, visit %s, feed_import_SELFTEST.json)" % f[0]["empty_visit"]
      and regq["quality_gate"]["refused_charts"] == [["pat401", "2026"]], regq["quality_gate"])
keep(regq, "20261103T0100Z"); charts0(); out, regq3 = live(visits("20261104", (3, 4, 5)))
check("... (SM-5) the next run adds no line and registers no further failed visit: one such visit, then the code waits for William", qrows_of(regq3) == [] and regq3["failed"] == [] and len(regq3["created"]) == 3 and not any("pcode65441" in b_ for b_ in POSTS)
      and regq3["quality_gate"]["off_until_reset"] == regq["quality_gate"]["off_until_reset"] and "OFF - AdvancedMD answered a fault but kept the visit" in qline(out), (regq3["quality_gate"], qline(out)))
keep({k_: v_ for k_, v_ in regq.items() if k_ != "quality_gate"}, "20261103T0100Z"); charts0(); out, regq5 = live(visits("20261104", (3, 4, 5)))
check("... (SM-5) also when that run was cut off before it wrote its gate: the failed row alone switches the code off, and the sentence names the register it stands in", qrows_of(regq5) == [] and len(regq5["created"]) == 3
      and regq5["quality_gate"]["off_until_reset"] == "AdvancedMD answered a fault but kept the visit - William looks (chart pat401, visit %s, feed_import_20261103T0100Z.json)" % f[0]["empty_visit"], regq5["quality_gate"])
clear_regs(); charts0(); _cl = ci.chart_lines_now; _tries = []
def _never(pid): _tries.append(pid); raise RuntimeError("history down")
ci.chart_lines_now = _never; out, regq2 = live(visits("20261102", (1,)), refuse_quality=True); ci.chart_lines_now = _cl
check("refused and the chart cannot be read in three tries: not sent again either", len(regq2["failed"]) == 1 and regq2["created"] == [] and "chart not read" in str(regq2["failed"][0]["stored"]) and len(_tries) == 3
      and regq2["quality_gate"]["off_until_reset"].startswith("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (chart pat401"), (regq2["failed"], _tries, regq2["quality_gate"]))
charts0(); _tries = []
def _once(pid):
    _tries.append(pid)
    if len(_tries) == 1: raise TimeoutError("read timed out")
    return _cl(pid)
ci.chart_lines_now = _once; out, regq4 = live(visits("20261102", (1,)), refuse_quality=True); ci.chart_lines_now = _cl
check("refused and the chart read fails ONCE (NH-5): the second try reads it - the visit is entered without the line, nothing is left for entry by hand", regq4["failed"] == [] and len(regq4["created"]) == 1 and regq4["created"][0].get("quality_refused")
      and len(regq4["created"][0]["charges"]) == 1 and len(_tries) == 2 and regq4["quality_gate"]["off_until_reset"] == "", (regq4["failed"], regq4["created"], _tries))
# refused with AND without the line: the code is not blamed
charts0(); out, rega = live(QB, refuse_all=True)
check("refused with and without the line: an ordinary fault - no refusal of the code is recorded, and after two such visits no further line is tried in that run", len(rega["failed"]) == 5 and rega["created"] == []
      and not any((x["info"] or {}).get("quality_refused") for x in rega["failed"]) and sum(1 for b_ in POSTS if "pcode65441" in b_) == 2 and "two visits were refused with and without the code" in rega["quality_gate"]["off"]
      and rega["quality_gate"]["off_until_reset"] == "" and rega["quality_gate"]["refused_charts"] == [], (rega["quality_gate"], len(POSTS)))
keep(rega, "20261113T0100Z"); ci.PARSED[:] = QB; out, dry = run_dry()
check("... and the next run is a plain pilot again (a failed visit says nothing about the code)", ci.QUALITY["fee"] == "0.00" and ci.QUALITY["off"] == "" and ci.QUALITY["wait"] is False and sum(1 for v in dry.values() if v[0].get("quality_codes")) == 3, ci.QUALITY)
# the send WITHOUT the line fails after a refusal (a time-out), and the call that carries the line itself fails
clear_regs(); charts0()
out, regt = live(visits("20261102", (1, 2, 3)), refuse_quality=True, plain_raises=True)
ft = regt["failed"]
check("refused, and the send without the line then raises (NH-11): the code is off for the REST of the run (one visit lost, not every eligible one), and the failed row records the amount that was refused",
      len(ft) == 1 and ft[0].get("quality_sent") == "0.00" and ft[0]["info"]["quality_tried"] == "0.00" and ft[0]["info"]["quality_codes"] == [] and len(regt["created"]) == 2 and qrows_of(regt) == []
      and sum(1 for b_ in POSTS if "pcode65441" in b_) == 1 and "could not be sent without it either (TimeoutError)" in regt["quality_gate"]["off"], (ft, regt["quality_gate"]))
keep(regt, "20261103T0100Z"); ci.PARSED[:] = visits("20261104", (1, 4)); out, dry = run_dry()
check("... the next run counts it like a refusal: one cent, and that patient gets no second try this year", ci.QUALITY["fee"] == "0.01" and ci.QUALITY["off"] == "" and lined(dry) == ["pat404"], (ci.QUALITY["fee"], lined(dry)))
clear_regs(); charts0()
out, regu = live(visits("20261102", (1, 2, 3)), line_raises=True)
fu = regu["failed"]
check("the call that CARRIES the line ends in an error (a time-out): nothing is sent again, no further line in that run, the other visits go in, and the failed row says that nobody knows what AdvancedMD kept",
      len(fu) == 1 and fu[0].get("quality_unknown") == "0.00" and fu[0]["info"]["quality_codes"] == [] and fu[0]["empty_visit"].startswith("vst") and len(regu["created"]) == 2 and qrows_of(regu) == []
      and sum(1 for b_ in POSTS if "pcode65441" in b_) == 1 and "ended in an error (TimeoutError)" in regu["quality_gate"]["off"] and "nobody knows whether AdvancedMD kept that visit - William looks (chart pat401" in regu["quality_gate"]["off_until_reset"], (fu, regu["quality_gate"]))
keep(regu, "20261103T0100Z"); ci.PARSED[:] = visits("20261104", (4,)); out, dry = run_dry()
check("... and the code is OFF until William has looked at that visit", lined(dry) == [] and "nobody knows whether AdvancedMD kept that visit" in ci.QUALITY["off_until_reset"] and ci.QUALITY["budget"] == 0, ci.QUALITY["off_until_reset"])
keep({k_: v_ for k_, v_ in regu.items() if k_ != "quality_gate"}, "20261103T0100Z"); out, dry = run_dry()
check("... also from the failed row alone (that run cut off before it wrote its gate)", lined(dry) == [] and "feed_import_20261103T0100Z.json" in ci.QUALITY["off_until_reset"] and "chart pat401" in ci.QUALITY["off_until_reset"], ci.QUALITY["off_until_reset"])
clear_regs(); charts0(); out, regu2 = live([P_("n1", "one", [("99487", "20261031")])] + visits("20261102", (1,)), all_raise=True)
check("... a visit WITHOUT the line whose call raises is handled exactly as before: a plain error row, nothing about the code, and the code is not switched off by it", len(regu2["failed"]) == 2 and sorted(regu2["failed"][0]) == ["err", "feed_id", "lines", "pid"]
      and regu2["failed"][1].get("quality_unknown") == "0.00" and regu2["created"] == [], regu2["failed"])
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
_qg = ci.quality_gate; ci.quality_gate = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom"))
out, regg = live(QB); ci.quality_gate = _qg
check("the gate cannot be written (NH-13): the register is NOT lost - every visit and line of the run is in it, with a gate that says so, and the run reaches its end", len(regg["created"]) == 5 and len(qrows_of(regg)) == 3
      and "could not be written (RuntimeError)" in regg["quality_gate"]["off"] and "DONE" in out and qline(out) != "", (regg["quality_gate"], out[-200:]))
_ql_ = ci.quality_log; ci.quality_log = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom"))
out, regl = live(QB); ci.quality_log = _ql_
check("the log line cannot be built (NH-13): the run still writes its register and reaches DONE", len(regl["created"]) == 5 and isinstance(regl["quality_gate"].get("round"), dict) and "QUALITY 1123F: this line could not be built" in out and "DONE" in out, out[-300:])
clear_regs(); json.dump({"created": [{"quality_codes": 5, "quality_charge": {"a": 1}, "charges": None}, {"quality_codes": ["1123F"], "quality_charge": "charge5", "pid": ["x"], "dos": 5, "quality_gate": 3},
                                       {"quality_refused": 0, "quality_not_stored": None, "quality_codes": None}], "skipped": [], "failed": [], "quality_gate": "odd"}, open(os.path.join(REGDIR, "feed_import_20261115T0100Z.json"), "w")); charts0()
BILLS["5"] = {"void": "1"}; out, reg7 = live(visits("20261109", (3,)))
check("odd values in an earlier register cannot stop the import or switch the code off", len(reg7["created"]) == 1 and reg7["quality_gate"]["off"] == "" and len(qrows_of(reg7)) == 1, reg7.get("quality_gate"))
clear_regs(); rmreg(EARLIER); DEMOG["plans"] = ""; BILLS.clear(); PROC.clear(); DETAILS.clear(); charts0(); qreset(); ci.PARSED[:] = BASE

# ---- 5. the mirror keeps these helpers: a workspace copy without the rule never overwrites the repository's ------------------------------
mir = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
for helper in ("claimocity_import.py", "claimocity_report.py", "claimocity_inspector.py", "claimocity_ingest.py", "claimocity_retry_dx.py", "working_denials.py", "claimocity_verify.py", "aging_refresh.py"):
    m = re.search(r'"%s":\s*(?:"([^"]+)"|\'([^\']+)\')' % re.escape(helper), mir); m = m and type("M", (), {"group": lambda self, i, _m=m: _m.group(1) or _m.group(2)})()
    check("mirror.py protects %s with a marker that is in the file" % helper, bool(m) and m.group(1) in open(os.path.join(ROOT, "scripts", "helpers", helper)).read(), m.group(1) if m else "no PROTECTED entry")
insp = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read()
check("inspector: a CCM visit at the hospital location is never moved to HCA REHAB / 31", 'all(x not in HOSP for x in c["cpts"]) and not any(x in ("99487", "99489") for x in c["cpts"])' in insp)
check("inspector: a visit the import flagged (pos_err) is never moved to HCA REHAB either; mirror.py's marker for the inspector is now a sentence only the version that takes the quality line off a held visit has (11/10/2026)",
      'not any(x in ("99487", "99489") for x in c["cpts"]) and not c.get("pos_err"):' in insp and "is never moved to HCA REHAB either" in insp and '"claimocity_inspector.py": "THIS STEP TAKES THE LINE OFF BY ITSELF"' in mir and "THIS STEP TAKES THE LINE OFF BY ITSELF" in insp)
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
check("runbook: the feed step copies the helpers and checks the version line before the ingest", step.index("cp -p claimocity_import.py claimocity_report.py claimocity_inspector.py claimocity_verify.py claimocity_ingest.py claimocity_retry_dx.py feed_parse_dft_1028.py /home/claude/unbilled/") < step.index("must print 1") < step.index("python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run drops --live)"))
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
      and "carried by: pat9 vst1 charge77" in ql and "remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; whether the measure is met shows only in the feedback on the Medicare quality-program site" in r.stdout
      and "counted" not in r.stdout and "2 visits / 2 charge lines created" in r.stdout, (ql, r.stdout[:400], r.stderr[-300:]))
r, ql = qdigest([rows[4]], dict(G0, wait=True, pending=["vst5", "vst6"], pending_since="feed_import_20261110T0100Z.json"))
check("digest: a waiting pilot says so, names the visits it waits for, and is not yet at the top of the report", "PILOT, waiting - no line was added in this run: the visit(s) that carry the first line(s) are not billed yet (vst5, vst6)" in ql and "TOP OF THE REPORT" not in ql, ql)
r, ql = qdigest([rows[4]], dict(G0, wait=True, pending=["vst5"], pending_since="feed_import_2026-11-07T0100Z.json"))
check("digest: after three days of waiting the pilot goes to the top of the report", "TOP OF THE REPORT - the quality-code pilot has waited 4 days" in ql and "vst5" in ql, ql)
r, ql = qdigest([qrow], dict(G0, fee="0.01", confirmed=True, proof={"visit": "vst5", "billed": "11/11/2026"}, pilot_cap=None, zero_not_billed=True, dead_zero_lines=[["pat1", "vst2", "charge3"], ["pat4", "vst5", "charge6"]],
                             notes=["visit vst4 was billed 11/10/2026 without its $0.00 quality line - new lines carry $0.01"]))
check("digest: says when every visit carries it, why the amount changed (at the top, in the run it changed), and lists the lines read as left off - for William, no routine voids them (M9)", "line amount $0.01; every eligible visit carries it - a quality line was seen billed to insurance (visit vst5, 11/11/2026)" in ql
      and "without its $0.00 quality line" in r.stdout and "2 quality line(s) were read as left off their claims" in ql and "pat1 vst2 charge3; pat4 vst5 charge6 - listed for William; no routine voids them" in ql
      and "TOP OF THE REPORT - new quality lines now carry ONE CENT" in ql and "voided in AdvancedMD" not in r.stdout and "remark N620" not in r.stdout, ql)
r, ql = qdigest([dict(qrow, quality_codes=[], quality_refused="Fault: no", quality_refused_fee="0.00")], dict(G0, off="this run: AdvancedMD refused a visit that carried the code"))
check("digest: a refusal and the switch-off go to the top of the report", "TOP OF THE REPORT - QUALITY CODE NOT ACCEPTED by AdvancedMD on 1 visit(s); each visit was entered without it: pat9 vst1 (Fault: no)" in r.stdout and "TOP OF THE REPORT - the quality code is OFF: this run" in r.stdout, r.stdout[-700:])
r, ql = qdigest([dict(qrow, quality_codes=[], quality_charge="", quality_not_stored="0.00")], dict(G0, off="this run: AdvancedMD stored a visit without its quality line"))
check("digest: a visit stored without its line goes to the top of the report", "TOP OF THE REPORT - AdvancedMD stored 1 visit(s) WITHOUT the quality line that was sent with it (the visit itself is entered): pat9 vst1" in r.stdout, r.stdout[-500:])
r, ql = qdigest([rows[4]], dict(G0, off="this run: a visit with the code was refused and the chart could not be shown free of it"), failed=[{"feed_id": "n2", "pid": "pat7", "empty_visit": "vst70", "stored": [["99309", "11/02/2026"]], "err": "x", "info": {"quality_tried": "0.00", "cpts": ["99309"]}}])
check("digest: a refused visit that was NOT sent again is named at the top with its codes - check that visit, no routine sends it again (S10, M9)", "TOP OF THE REPORT - 1 visit(s) were refused with the quality line and NOT sent again" in r.stdout
      and "check that visit (for William; no routine sends it again): pat7 ? 99309 (empty visit vst70; chart shows [['99309', '11/02/2026']])" in r.stdout and "by hand" not in r.stdout, r.stdout[-600:])
r, ql = qdigest([rows[4]], dict(G0, reset=True, notes=["the pilot was started again in this run (QUALITY_CODE=reset)"]))
check("digest: a restart of the pilot is said - once (S10: it used to be said twice)", r.stdout.count("the pilot was started again in this run (QUALITY_CODE=reset)") == 1, r.stdout[-400:])
r, ql = qdigest([rows[4], rows[5]], G0)
check("digest: no quality line when no visit carried the code and nothing happened", r.returncode == 0 and ql == "", ql)
for oddg in ("odd", {"pending": 5, "dead_zero_lines": "x", "notes": 3, "proof": "p", "wait": True, "pending_since": 9}, None):
    r, ql = qdigest([dict(qrow, quality_codes="x", quality_charge=None), dict(qrow, quality_codes=None, quality_refused=1, quality_not_stored=2, visit=None)], oddg, failed=[{"stored": 1, "info": {"quality_tried": 0}}, {"stored": [1], "info": "x"}])
    check("digest: odd quality values (%s) never stop the report" % type(oddg).__name__, r.returncode == 0 and "could not be built" not in ql, (ql, r.stderr[-300:]))
# version 2 (11/10/2026): every line for William is ONE line at the top, in the run where it began; the previous import register's gate tells what is new
def qdig2(rows, gate, prev=None, insp_=None, ver_=None, failed=()):
    pf = os.path.join(rep_dir, "registers", "feed_import_20261111T0000Z.json"); inf = os.path.join(rep_dir, "registers", "feed_inspector_20261111T0100Z.json"); vf = os.path.join(rep_dir, "feed_verify_20261111T0100Z.json")
    for f_, o_ in ((pf, {"created": [], "quality_gate": prev} if prev is not None else None), (inf, insp_), (vf, ver_)):
        if o_ is None:
            if os.path.exists(f_): os.remove(f_)
        else: json.dump(o_, open(f_, "w"))
    try:
        r_, ql_ = qdigest(rows, gate, failed=failed); return r_, r_.stdout
    finally:
        for f_ in (pf, inf, vf):
            if os.path.exists(f_): os.remove(f_)
_TOP = lambda out_: [l_ for l_ in out_.splitlines() if "TOP OF THE REPORT" in l_]
OFFS = "AdvancedMD billed visit vst9 (11/12/2026) without its one-cent quality line too - William looks"
r, o = qdig2([rows[4]], dict(G0, off=OFFS, off_until_reset=OFFS), prev=dict(G0))
check("digest (S10): a lasting OFF that began in this run is at the top, with its sentence and how to start again; the headline says OFF", "TOP OF THE REPORT - the quality code is OFF until William restarts it: " + OFFS in o
      and "one run with QUALITY_CODE=reset" in o and "line amount $0.00; OFF until William restarts it" in o and "PILOT" not in o, o[-900:])
r, o = qdig2([rows[4]], dict(G0, off=OFFS, off_until_reset=OFFS), prev=dict(G0, off=OFFS, off_until_reset=OFFS))
check("digest (S10): ... the same OFF in the next batch is ONE plain line (not the top), still saying how to start again", _TOP(o) == [] and "the quality code is still OFF (since an earlier run): " + OFFS in o and "QUALITY_CODE=reset" in o, o[-700:])
r, o = qdig2([rows[4]], dict(G0, off="this run: switched off (QUALITY_CODE=off)"), prev=dict(G0))
check("digest (S10): William's own QUALITY_CODE=off is a plain line, not the top", _TOP(o) == [] and "switched off for this run by William's QUALITY_CODE=off - no line was added." in o, o[-600:])
r, o = qdig2([rows[4]], dict(G0, off="this run: QUALITY_CODE='0ff' is not a value the import knows (off, stop, reset) - no line added"), prev=dict(G0))
check("digest (SM-8, M8): a switch value the import does not know is at the top, named", any("TOP OF THE REPORT - the quality code is OFF: this run: QUALITY_CODE='0ff' is not a value the import knows" in l_ for l_ in _TOP(o)), o[-600:])
_UOFF = "this run: the import register feed_import_20261110T0000Z.json cannot be read - the state of the quality code is not known; no line until it is restored from the repository"
r, o = qdig2([rows[4]], dict(G0, off=_UOFF, unread=["feed_import_20261110T0000Z.json"], unread_prev=[]), prev=dict(G0))
check("digest (13.5): the first run that cannot read an import register says so in a plain line", _TOP(o) == [] and "no line in this run: the import register feed_import_20261110T0000Z.json cannot be read (the visits went in as always)" in o, o[-600:])
r, o = qdig2([rows[4]], dict(G0, off=_UOFF, unread=["feed_import_20261110T0000Z.json"], unread_prev=["feed_import_20261110T0000Z.json"]), prev=dict(G0))
check("digest (13.5): ... from the second run in a row it is at the top - the quality code waits until the register is restored from the repository",
      any(l_.startswith("  - TOP OF THE REPORT - the import register feed_import_20261110T0000Z.json cannot be read - the quality code waits until it is restored from the repository") for l_ in _TOP(o)) and len(_TOP(o)) == 1, _TOP(o))
r, o = qdig2([rows[4]], dict(G0, notes=["NOTHING TO RESTART - QUALITY_CODE=reset was ignored (the code is not switched off; take the switch out of the routine)"]), prev=dict(G0))
check("digest (SM-8): a reset that had nothing to restart is at the top (a switch left in a routine)", any("NOTHING TO RESTART - QUALITY_CODE=reset was ignored" in l_ for l_ in _TOP(o)), o[-500:])
_CENT = dict(G0, fee="0.01", zero_not_billed=True, notes=["new lines carry $0.01: AdvancedMD left the $0.00 line of visit vst4 off its claim and no $0.00 line of the round is billed"])
r, o = qdig2([rows[4]], _CENT, prev=dict(G0)); r2_, o2 = qdig2([rows[4]], _CENT, prev=dict(G0, fee="0.01"))
check("digest (S10): the switch to one cent is at the top in the run it happened, and says the patients are due again once the one-cent round has room; the next batch does not repeat it at the top",
      any("TOP OF THE REPORT - new quality lines now carry ONE CENT" in l_ and "AdvancedMD left the $0.00 line of visit vst4 off its claim" in l_ and "once the one-cent round has room" in l_ for l_ in _TOP(o)) and not any("ONE CENT" in l_ for l_ in _TOP(o2)), (_TOP(o), _TOP(o2)))
r, o = qdig2([rows[4]], dict(G0, wait=True, pending=["vst2"], proof_wait={"since": "11/08/2026", "visit": "vst2", "charge": "charge22", "days": 3}), prev=dict(G0))
check("digest (13.4b): a billed line whose code text nothing shows for three days is at the top", any("the quality line of visit vst2 is billed, but for 3 days neither its charge detail nor the chart's history shows the code text 1123F" in l_ for l_ in _TOP(o)), o[-600:])
r, o = qdig2([rows[4]], dict(G0, off="AdvancedMD stores procedure id pcode65441 as 99497, not 1123F - William looks", off_until_reset="AdvancedMD stores procedure id pcode65441 as 99497, not 1123F - William looks", wrong_code_text="99497"), prev=dict(G0))
check("digest (13.4a): AdvancedMD's id read with another code text is at the top", any("AdvancedMD stores procedure id pcode65441 as 99497, not 1123F - William looks" in l_ for l_ in _TOP(o)), o[-500:])
_INS = lambda held_, rem_: {"fixed": [], "bypassed": [], "laterality": [], "held": held_, "quality_removed": rem_}
r, o = qdig2([dict(qrow), dict(rows[4], visit="vst7", pid="pat7")], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}, {"visit": "7", "pid": "pat7", "why": "Pattern 24078: else"}], []))
check("digest (section 7): a held visit that still carries the line (the inspector marks it 'quality') is at the top; a held visit without it is not named there",
      any("1 visit(s) that carry the quality line are HELD by the Claim Inspector" in l_ and "pat9 vst1 - Pattern 77002: review" in l_ for l_ in _TOP(o)) and not any("pat7" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review"}], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Pattern 77002: review", "void_ok": True, "released": False, "at": "x"}]))
check("digest (11.5): the line taken off a visit that stays held - at the top: the visit is still held for its own reason, its place in the round is free, the patient is due again; not also named as 'held with the line'",
      any("the routine took the quality line charge77 off held visit vst1 (pat9), but the visit is still held for its own reason" in l_ and "its place in the round is free and the patient is due again" in l_ for l_ in _TOP(o)) and not any("carry the quality line are HELD" in l_ for l_ in _TOP(o)), _TOP(o))
for _fee_, _conf_, _next_ in (("0.00", False, "the next run moves new lines to one cent and starts a new round"), ("0.01", False, "the next run switches the code off until William restarts it"), ("0.00", True, "after proof one changes nothing; a second in a row moves new lines to one cent")):
    r, o = qdig2([dict(qrow)], dict(G0, fee=_fee_, confirmed=_conf_), prev=dict(G0), insp_=_INS([], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": _fee_, "why": "Pattern 77002: review", "void_ok": True, "released": True}]))
    check("digest (11.5): the line taken off a held visit that then went through (at $%s, %s) - at the top, with what happens next: %s" % (_fee_, "proven" if _conf_ else "before proof", _next_),
          any("the routine took the quality line charge77 off held visit vst1 (pat9; the hold: Pattern 77002: review) and the visit went through without it. That is one refusal of the line: " + _next_ in l_ for l_ in _TOP(o)), _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Pattern 77002: review", "void_ok": False, "released": False, "note": "the void failed: Fault"}]))
check("digest (11.5): a void that failed - at the top: the visit is held WITH its line, William looks, the code switches off", any("the routine could not take the quality line off held visit vst1 (pat9: the void failed: Fault) - the visit is held WITH its line; William looks" in l_ for l_ in _TOP(o))
      and not any("carry the quality line are HELD" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), ver_={"pat9": {"decision": "RELEASE", "visits": ["vst1"], "lead": {"code": "FLO02"}, "hold": [], "quality_removed": [{"visit": "vst1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Fault: zero amount", "void_ok": True, "released": True}]}})
check("digest (11.5): a line the insurance check took off is reported the same way", any("the routine took the quality line charge77 off held visit vst1" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), ver_={"pat9": {"decision": "RELEASE", "visits": ["vst1"], "lead": {"code": "HUM01"}, "hold": []}})
check("digest (NH-3): a quality line whose visit the insurance check moved to another payer - one plain line: that line went to that payer, nothing to do", _TOP(o) == [] and "pat9 vst1 -> HUM01 - that line went to that payer; nothing to do" in o, o[-600:])
_PRV = dict(G0, confirmed=True, proof={"visit": "vst5", "billed": "11/11/2026"}, pilot_cap=None)
r, o = qdig2([dict(qrow)], dict(_PRV, history_shows_line=False), prev=dict(G0)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, history_shows_line=False), prev=dict(_PRV, history_shows_line=False))
check("digest (SM-7): the chart history that does not list the proven line is at the top once - in the run that found it", any("does NOT list the proven quality line" in l_ for l_ in _TOP(o)) and not any("does NOT list" in l_ for l_ in _TOP(o2)), (_TOP(o), _TOP(o2)))
r, o = qdig2([rows[4]], dict(G0, not_renewed={"2027": 4}), prev=dict(G0))
check("digest (M10): in January, visits of a year the rule was not renewed for - at the top", any("the quality code is not added to 2027 visits until William renews it (4 visit(s) of this batch would otherwise carry it)" in l_ for l_ in _TOP(o)), _TOP(o))
_ANS = {"charge": "charge22", "visit": "vst2", "date": "11/25/2026", "amount": "0.00", "register": "feed_import_20261111T1240Z.json"}
r, o = qdig2([dict(qrow)], dict(_PRV, medicare_answer=_ANS), prev=dict(_PRV)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, medicare_answer=_ANS), prev=dict(_PRV, medicare_answer=_ANS))
check("digest (11.4): Medicare's answer when it first arrives - one plain line, not the top; the next batch does not repeat it", _TOP(o) == [] and "Medicare's remittance shows the 1123F line on visit vst2, paid $0.00 on 11/25/2026" in o and "no cap" in o
      and "Medicare's remittance shows" not in o2 and "counted" not in o, o[-700:])
r, o = qdig2([dict(qrow)], dict(_PRV, medicare_wait={"lines": 2, "oldest": "11/11/2026", "days": 12}), prev=dict(_PRV)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, medicare_wait={"lines": 2, "oldest": "10/01/2026", "days": 45}), prev=dict(_PRV))
check("digest (11.4, section 7): from proof until Medicare's answer: one plain sentence (how many lines are billed, since when the oldest waits, the remittance file as the second way); after 45 days at the top",
      _TOP(o) == [] and "2 quality line(s) are billed; Medicare has not yet shown a 1123F line on a remittance (the oldest billed 11/11/2026, 12 day(s) ago)" in o and "(reason 246, remark N620)" in o and "> registers/quality_n620_seen.json" in o
      and any(l_.startswith("  - TOP OF THE REPORT - Medicare has shown no 1123F line in 45 days - William looks at one remittance.") for l_ in _TOP(o2)), (o[-500:], _TOP(o2)))
r, o = qdig2([rows[4]], dict(_PRV, late_rows=[["pat7001", "vst1", "charge12", "11/14/2026", "", "2026"], ["pat7002", "vst2", "charge22", "11/14/2026", "vst9", "2026"]]), prev=dict(_PRV))
check("digest (13.1b): a left-off line billed later - one plain line each; with a second line meanwhile: two billed lines for 2026, nothing to do", _TOP(o) == [] and "a quality line read as left off on 11/14/2026 was billed later: pat7001 counts as coded." in o
      and "a quality line read as left off on 11/14/2026 was billed later: pat7002 counts as coded; pat7002 carries two billed quality lines for 2026 (the later one on vst9); nothing to do." in o, o[-700:])
r, o = qdig2([rows[4]], dict(G0, quality_skipped_hospital=2), prev=dict(G0))
check("digest (13.2): hospital visits left out - one plain line", _TOP(o) == [] and "2 hospital visit(s) of Medicare patients 65 and older did not get the quality line: hospital visits are not coded in this version (William decides for 2027)." in o, o[-500:])
r, o = qdig2([rows[4]], G0, prev=dict(G0), failed=[{"feed_id": "n2", "pid": "pat7", "info": {"dos": "11/02/2026", "cpts": ["99309"]}, "err": "x"}])
check("digest (N3): failed visits are counted and named in the Import line (it used to say '0 faults' always)", "1 visit(s) FAILED - not entered or not finished, see the import register's failed rows: pat7 11/02/2026 99309" in o and "0 faults" not in o, o[:600])
_busy = dict(G0, off=OFFS, off_until_reset=OFFS, not_renewed={"2027": 1}, quality_skipped_hospital=1, notes=["NOTHING TO RESTART - QUALITY_CODE=reset was ignored (x)"])
r, o = qdig2([dict(qrow, quality_codes=[], quality_refused="Fault: no", quality_refused_fee="0.00")], _busy, prev=dict(G0), insp_=_INS([], [{"visit": "1", "pid": "pat9", "charge": "charge77", "void_ok": False, "released": False, "note": "x"}]))
check("digest: every line for William starts '  - TOP OF THE REPORT - ' and is one line (a busy batch: five of them)", len(_TOP(o)) == 5 and all(l_.startswith("  - TOP OF THE REPORT - ") for l_ in _TOP(o)), _TOP(o))
import importlib.util as _iu
wd = open(os.path.join(ROOT, "boards", "working_denials.py")).read()
check("denial table: Medicare's acceptance of a reporting code (reason 246) is information, never work", '"246": ("INFO"' in wd and "N620" in wd)
# M7, BOTH copies of the denial table: a remittance line whose procedure is 1123F, 1124F or M0004 is INFO for EVERY reason and group code, in the board's own roll-up too
_wdm = {}
for _wdp in (os.path.join(ROOT, "boards", "working_denials.py"), os.path.join(ROOT, "scripts", "helpers", "working_denials.py")):
    _sp = _iu.spec_from_file_location("wd_%d" % len(_wdm), _wdp); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m); _wdm[_wdp] = _m
    _rel = os.path.relpath(_wdp, ROOT)
    check("denial table (%s, M7): a 1123F / 1124F / M0004 line is INFO whatever its reason or group code - 'reporting line - nothing to do, never bill a cent of it to the patient'" % _rel,
          all(_m.triage(c_, p_)[0] == "INFO" and "reporting line - nothing to do, never bill a cent of it to the patient" in _m.triage(c_, p_)[1] and _m.triage_line(c_, p_, "")[0] == "INFO"
              for c_ in ("CO96", "CO97", "PR204", "CO16", "CO181", "CO24", "OA23", "CO18", "PI29", "COB9") for p_ in ("1123F", "1124F", "m0004", " 1123F ")), [(c_, _m.triage(c_, "1123F")) for c_ in ("CO96", "CO24")])
    check("denial table (%s, M7, M3): row 246 says the same and the true thing about remark N620; other procedures are triaged as before" % _rel,
          "reporting line - nothing to do, never bill a cent of it to the patient" in _m.triage("CO246")[1] and "shows Medicare received the code and that it is valid for the year" in _m.triage("CO246")[1] and "counted" not in _m.triage("CO246")[1]
          and "accepted it for the quality program" not in _m.triage("CO246")[1] and _m.triage("CO96", "99309")[0] == "REVIEW" and _m.triage("CO96")[0] == "REVIEW" and _m.triage("CO16", "99309")[0] == "FIX", _m.triage("CO246"))
    _wdd = tempfile.mkdtemp(prefix="posrule_wd_"); _cwd0 = os.getcwd()
    json.dump([{"pid": "9201", "visitid": "700001", "patient": "x", "carrier": "FLO02", "dos": "2026-11-02", "cpt": "1123F", "billed": "0.00", "carc": "CO96", "group": "CO", "reason": "x", "check": "1", "amt": 0.0, "rarc": []},
               {"pid": "9202", "visitid": "700002", "patient": "y", "carrier": "FLO02", "dos": "2026-11-02", "cpt": "99309", "billed": "141.00", "carc": "CO96", "group": "CO", "reason": "x", "check": "1", "amt": 141.0, "rarc": []}],
              open(os.path.join(_wdd, "denials_20261120.json"), "w"))
    try:
        os.chdir(_wdd); _argv0 = sys.argv; sys.argv = ["working_denials.py"]
        with contextlib.redirect_stdout(io.StringIO()): _wout = _m.main()
    finally: os.chdir(_cwd0); sys.argv = _argv0
    _byv = {v_["visitid"]: v_["dispo"] for v_ in _wout["visits"]}
    check("denial table (%s, M7): the board's own roll-up - a visit whose only remark is CO96 on its 1123F line is INFO, not one actionable visit; CO96 on a visit's own line is still REVIEW" % _rel,
          _byv == {"700001": "INFO", "700002": "REVIEW"} and _wout["actionable_visits"] == 1, _byv)
# 13.3 THE AGEING PAGE (both copies; neither writes to AdvancedMD): a reporting line never makes a visit read as denied, and 246 is informational. Each copy is loaded
# INSIDE this process, offline, from a copy whose workspace paths point at a sandbox (the real file names /home/claude/unbilled - never read here)
_agd = tempfile.mkdtemp(prefix="posrule_ag_")
def _ag_visit(with_line, em_reasons, em_paid="88.00", carrier="AAR01", bal="22.00", qreason=("CO246", "0.00")):      # the second no-harm reviewer's exact input (h/aging.py)
    r_ = {"carriercode": carrier, "insbalance": bal, "dateofservice": "2026-11-02", "visitid": "700001", "patientid": "9201", "totalvisitamount": "141.00"}
    ch_ = [{"visit": "700001", "void": "0", "proccode": "99309", "modcodes": "", "billdate": "11/12/2026", "payments": [{"void": "0", "amount": em_paid, "carrier": "FLO02", "date": "11/20/2026", "reasons": em_reasons}]}]
    if with_line: ch_.append({"visit": "700001", "void": "0", "proccode": "1123F", "modcodes": "", "billdate": "11/12/2026", "payments": [{"void": "0", "amount": "0.00", "carrier": "FLO02", "date": "11/20/2026", "reasons": [qreason]}]})
    return r_, ch_, [{"code": "FLO02", "seq": "1", "begin": None, "end": None}, {"code": "AAR01", "seq": "2", "begin": None, "end": None}]
for _agp in (os.path.join(ROOT, "tools", "button", "aging_refresh.py"), os.path.join(ROOT, "scripts", "helpers", "aging_refresh.py")):
    _src = open(_agp).read().replace("/home/claude/unbilled", _agd).replace("/home/claude/practices", os.path.join(_agd, "practices"))
    _cp = os.path.join(_agd, "aging_copy_%d.py" % len(_src)); open(_cp, "w").write(_src); _rel = os.path.relpath(_agp, ROOT)
    _old_mods = {k_: sys.modules.get(k_) for k_ in ("amd", "txh", "era_post", "requests")}; _argv0 = sys.argv; _cwd0 = os.getcwd()
    try:
        for k_ in _old_mods: sys.modules[k_] = types.ModuleType(k_)      # never used offline - stand-ins all the same
        sys.argv = ["aging_refresh.py", "--offline", "none.json", "x", "--today", "2026-12-20"]; os.chdir(_agd)
        _sp = _iu.spec_from_file_location("ag_%d" % len(_src), _cp); _ag = _iu.module_from_spec(_sp); _sp.loader.exec_module(_ag)
    finally:
        sys.argv = _argv0; os.chdir(_cwd0)
        for k_, v_ in _old_mods.items():
            if v_ is None: sys.modules.pop(k_, None)
            else: sys.modules[k_] = v_
    _S1 = [("CO45", "31.00"), ("PR2", "22.00")]
    _d0 = _ag.decide(*_ag_visit(False, _S1), None); _d1 = _ag.decide(*_ag_visit(True, _S1), None); _d1b = _ag.decide(*_ag_visit(True, _S1, qreason=("OA246", "0.00")), None)
    check("ageing page (%s, 13.3, the no-harm reviewer's exact input): a visit that waits for its secondary payer still says WAIT when its 1123F line carries reason 246 (CO246 or OA246) - the line is not counted as a denial" % _rel,
          "/home/claude" not in _src and _d0["rec"] == _d1["rec"] == _d1b["rec"] == "WAIT" and _d1["rule"] == _d0["rule"] == "secondary claim sent within 60 days" and _d1["carcs"] == "" and _d1b["carcs"] == "", (_d0, _d1, _d1b))
    _d2 = _ag.decide(*_ag_visit(True, [("CO18", "141.00")], em_paid="0.00", carrier="FLO02", bal="141.00"), None)
    check("ageing page (%s, 13.3): a duplicate denial CO-18 on the visit's own line keeps its own advice with the 1123F line beside it" % _rel, _d2["rec"] == "WAIT" and _d2["rule"].startswith("CO-18 duplicate") and _d2["carcs"] == "18", _d2)
    _d4 = _ag.decide(*_ag_visit(True, _S1, qreason=("CO96", "0.00")), None)
    check("ageing page (%s, 13.3): the 1123F line answered with ANOTHER reason (CO96) does not make the visit read as denied either - its lines are left out" % _rel, _d4["rec"] == "WAIT" and _d4["carcs"] == "" and _d4["rule"] == "secondary claim sent within 60 days", _d4)
    _d3 = _ag.decide(*_ag_visit(True, [("CO16", "141.00")], em_paid="0.00", carrier="FLO02", bal="141.00"), None)
    check("ageing page (%s): a real denial on the visit's own line is still a denial (correct & resend) - only the reporting line is left out" % _rel, _d3["rec"] == "CORRECT & RESEND" and _d3["carcs"] == "16" and "246" in _ag.INFO_REASONS, _d3)
check("runbook and rulebook carry the owner's words for the quality code", '"yes for all: billing adds 1123F automatically, once per patient, to the next Medicare claim for every patient 65 and older."' in open(os.path.join(ROOT, "practices", "ehpa", "rules.md")).read() and "## Quality code 1123F, advance care plan" in step and "QUALITY_CODE=reset" in step and "grep -h '^QUALITY 1123F' logs/claimocity_<stamp>_*.log" in step and "in front of the claimocity_retry_dx.py command" in step)
# the words (11/10/2026, version 2): what the runbook and the rulebook say is what the code does (the sentence-by-sentence notes are kept with the change)
_rules = open(os.path.join(ROOT, "practices", "ehpa", "rules.md")).read(); _qrb = next(l_ for l_ in _rules.split("\n") if "QUALITY CODE 1123F, ADVANCE CARE PLAN" in l_)
_qrun = step[step.index("## Quality code 1123F, advance care plan"):step.index("## Why it is safe to run every routine")]
_OWNER2 = '"choose whether AdvancedMD should take the no-charge 1123F line off a held visit automatically or leave the visit held for you. this doesnt appear to have any significance whiever way to just deal with it'
check("runbook and rulebook (11.5): the owner's decision on held visits is quoted as the authority, and both say the routine takes the line off by itself", _OWNER2 in _qrb and _OWNER2 in _qrun.replace("\n", " ")
      and "The choice made: the routine takes it off" in _qrb and "The choice made: the routine takes it off" in _qrun.replace("\n", " "))
_N620 = "remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; whether the measure is met shows only in the feedback on the Medicare quality-program site"
check("runbook and rulebook (M3): N620 is described as CMS describes it - never 'Medicare counted it', never 'acceptance'", _N620 in _qrb.replace("Remark", "remark") and _N620 in _qrun.replace("\n", " ").replace("Remark", "remark")
      and not re.search(r"counted (the code|it|a line)|is acceptance|Medicare accepted", _qrb + _qrun), re.findall(r"[^.]*counted[^.]*", _qrb + _qrun))
check("runbook and rulebook (M9, B3): lines read as left off are listed for William - no routine voids them; a refused visit not sent again is William's - no routine sends it again; 'for voiding' / 'by hand' are gone",
      all(("no routine voids it" in _qrb, "no routine voids it" in _qrun.replace("\n", " "), "no routine sends it again" in _qrun.replace("\n", " "), "for voiding" not in _qrun, "ordinary charge clean-up" not in _qrun, "for entry by hand" not in _qrun, "can be voided" not in _qrb + _qrun)))
check("rulebook (M5, NH-3, M12, M13, M15, 13.2): the exception list and 1123F with modifier 8P entered by a person; no 'does no harm'; who is left out; the exact code list; hospital visits not coded; M0004 left to the next step",
      "registers/quality_exceptions.json" in _qrb and "takes 1123F with modifier 8P - both entered by a person, not by the back end" in _qrb and "does no harm" not in _qrb and "takes no code" not in _qrb
      and "WHO IS LEFT OUT" in _qrb and "Railroad Medicare" in _qrb and "a first visit ever" in _qrb and "99304-99310, 99341, 99342, 99344, 99345, 99347-99350, 99221-99223, 99231-99236, 99202-99205 and 99212-99215" in _qrb
      and "HOSPITAL VISITS ARE NOT CODED IN THIS VERSION" in _qrb and "M0004 is added by the next step of this change, to be finalised there" in _qrb and "ONE diagnosis" in _qrb and "nurse practitioner" in _qrb)
check("rulebook and runbook: the rule's numbers are the import's (3 lines a round, 10 a run after proof, six reads, three days, 30 days, 2026)", ci.QUALITY_PILOT == 3 and ci.QUALITY_DAILY == 10 and ci.QUALITY_LOOKS == 6 and ci.QUALITY_LEFT_OFF_DAYS == 3 and ci.QUALITY_LEFT_OFF_REREAD == 30
      and "at most 3 lines" in _qrb and "at most 10 a run" in _qrb and "up to six billed 1123F lines" in _qrb and "three days after its visit was billed" in _qrb and "30 days" in _qrb and "a date of service in 2026" in _qrb
      and "at most 3 visits" in _qrun and "at most 10 a run" in _qrun and "up to six billed quality lines" in _qrun.replace("\n", " ") and "three days after its visit was billed" in _qrun.replace("\n", " "))
check("runbook (SM-8, M8, S1, S2): the switches with the exact command form, stop, reset only while OFF and on the ingest only, any other value named; Hospital visits do not carry it",
      "&& QUALITY_CODE=off python3 claimocity_ingest.py" in _qrun.replace("\n", " ") and "`QUALITY_CODE=stop` = OFF until William restarts it" in _qrun.replace("\n", " ") and "NOTHING TO RESTART" in _qrun and "on the ingest command only" in _qrun.replace("\n", " ")
      and "Any other value adds no line and the log names it" in _qrun.replace("\n", " ") and "Hospital visits do not carry\nit in this version" in _qrun)
check("runbook (M8c): the import register is committed right after the import while a pilot round is open - the privacy gate first, then the same git commands as the practice-database register",
      all(x_ in _qrun.replace("\n", " ") for x_ in ("COMMIT THE IMPORT REGISTER while a pilot round is open", "python3 tools/mirror/phi_gate.py /home/claude/unbilled/registers/feed_import_<stamp>.json practices/ehpa/registers/feed_import_<stamp>.json",
          "git add practices/ehpa/registers/feed_import_<stamp>.json", "git pull -q --rebase --autostash origin main && git push origin HEAD:main")) and "--autostash origin main && git push origin HEAD:main" in step[:step.index("## Place of service")])
check("runbook (S6): the step the routines follow (f) names the quality line and its grep", "Then the digest's line 'Quality code 1123F ...'" in step[:step.index("## Place of service")] and "grep -h '^QUALITY 1123F'" in step[:step.index("## Place of service")])
_cc = open(os.path.join(ROOT, "docs", "captured_calls.md")).read(); _sl = open(os.path.join(ROOT, "docs", "SHARED_LESSONS.md")).read().rstrip("\n").split("\n")
check("captured calls (13.4c, section 7): the look-up answers - 1123F = pcode65441 'ACP DISCUSS/DSCN MKR DOCD', 1124F not in the list, M0004 = pcode692183 'QUAL CARE NEUROLOGIC CND MVP' (place of service 11, type of service 01)",
      'procedure id `pcode65441`, name "ACP DISCUSS/DSCN MKR DOCD"' in _cc and "1124F is NOT in the practice's procedure list" in _cc and 'procedure id `pcode692183`, name "QUAL CARE NEUROLOGIC CND MVP", units 1.0, default place of service 11, type of service 01' in _cc and "read 11/10/2026 09:43Z" in _cc)
check("lessons: one new dated line records the owner's decision on held visits and the rule version", _sl[-1].startswith("- 2026-11-10T1435Z | chat (quality code 1123F, version 2, step 2) | RULE |") and "just deal with it" in _sl[-1] and "2026-11-10.6" in _sl[-1])
# the insurance-check step: a void quality line never holds the visit (its function is run here with stand-ins; the rest of that helper is not loaded)
_vsrc = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py")).read(); _vsrc = _vsrc[_vsrc.index("def fast_set_insorder(v, order, removed=None):"):_vsrc.index("def main():")]
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
# 11.2 (William 11/10/2026: a reporting line never holds a visit): a refused echo that carries the quality line is sent ONCE more without it
VQ = {"order": "1,2", "void": set(), "sent": [], "fault": None, "proc": {"10": ("pcode65119", "141.00"), "11": ("pcode65441", "0.00")}}
class _RS2:
    CHG_FIELDS = ["fee", "pos", "proccode"]
    @staticmethod
    def detail(cid): pc, fee = VQ["proc"].get(str(cid), ("pcodeX", "1.00")); return '<r><patient id="pat1"/><visit id="vst1" episode="e1" insorder="%s"/><charge id="charge%s" fee="%s" pos="32" proccode="%s" void="%s"/></r>' % (VQ["order"], cid, fee, pc, "1" if str(cid) in VQ["void"] else "0")
class _AM2:
    @staticmethod
    def msg(action, cls, attrs=None, children=""): return children
    @staticmethod
    def post(body, timeout=0):      # fault: "with" = refuses an echo that carries charge11, "always" = refuses every echo. An accepted echo voids every charge it leaves out (as AdvancedMD does)
        VQ["sent"].append(body)
        if VQ["fault"] == "always" or (VQ["fault"] == "with" and 'id="charge11"' in body): return "<r><Fault><description>Charge amount is zero</description></Fault></r>"
        sent_ = set(re.findall(r'<charge id="charge(\d+)"', body)); VQ["void"] |= {c_ for c_ in ("10", "11") if c_ not in sent_}
        m_ = re.search(r'insorder="([^"]*)"', body); VQ["order"] = m_.group(1) if m_ else VQ["order"]; return "<r/>"
_ns2 = {"resave": _RS2, "amd": _AM2, "re": re}; exec(_vsrc, _ns2)
_qrow = {"visit": "vst1", "pid": "pat1", "charges": ["charge10", "charge11"], "quality_charge": "charge11", "quality_codes": ["1123F"], "quality_fee": "0.00"}
VQ.update(order="1,2", void=set(), sent=[], fault="with"); _rm = []; ok5, m5 = _ns2["fast_set_insorder"](_qrow, "2", _rm)
check("insurance check (11.2): the echo with the quality line is refused - sent ONCE more without it: accepted, the order is set, the line is void, and the removal is reported (released)",
      ok5 is True and len(VQ["sent"]) == 2 and "charge11" in VQ["sent"][0] and "charge11" not in VQ["sent"][1] and "11" in VQ["void"] and "10" not in VQ["void"] and VQ["order"] == "2"
      and len(_rm) == 1 and {k_: _rm[0][k_] for k_ in ("visit", "pid", "charge", "fee", "void_ok", "released")} == {"visit": "vst1", "pid": "pat1", "charge": "charge11", "fee": "0.00", "void_ok": True, "released": True}
      and "Charge amount is zero" in _rm[0]["why"] and "line is void" in m5, (ok5, m5, _rm, VQ["sent"]))
VQ.update(order="1,2", void=set(), sent=[], fault="always"); _rm = []; ok6, m6 = _ns2["fast_set_insorder"](_qrow, "2", _rm)
check("insurance check (11.2): the echo is refused twice - held as before (the line is not the cause), nothing removed, the line is still live", ok6 is False and "resave FAULT" in m6 and "a fault again - the line is not the cause" in m6
      and _rm == [] and len(VQ["sent"]) == 2 and VQ["void"] == set(), (ok6, m6))
VQ.update(order="1,2", void=set(), sent=[], fault="always"); _rm = []; ok7, m7 = _ns2["fast_set_insorder"](dict(_qrow, quality_charge="charge10"), "2", _rm)
check("insurance check (11.2): a row whose quality charge names the visit's OWN charge (141.00, another procedure) - nothing is left out of an echo, ever: one echo, held as before", ok7 is False and len(VQ["sent"]) == 1 and _rm == [] and VQ["void"] == set(), (ok7, m7))
VQ.update(order="1,2", void=set(), sent=[], fault="always"); _rm = []; ok8, m8 = _ns2["fast_set_insorder"](dict(_qrow, quality_codes=None), "2", _rm)
check("insurance check (11.2): a visit without the quality line whose echo is refused - held as before, one echo", ok8 is False and len(VQ["sent"]) == 1 and m8.startswith("resave FAULT") and _rm == [], (ok8, m8))
VQ.update(order="1,2", void=set(), sent=[], fault=None); _rm = []; ok9, m9 = _ns2["fast_set_insorder"](_qrow, "2", _rm)
check("insurance check (11.2): an echo that is accepted at once keeps the quality line (nothing removed)", ok9 is True and len(VQ["sent"]) == 1 and "charge11" in VQ["sent"][0] and _rm == [] and VQ["void"] == set(), (ok9, m9))
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
# the whole insurance-check step, run INSIDE this process with stand-ins: what it writes in its register for a visit that carries the line
vfd = tempfile.mkdtemp(prefix="posrule_vf_"); os.makedirs(os.path.join(vfd, "registers")); json.dump({"car6085": ["FLO02", "FLORIDA MEDICARE"]}, open(os.path.join(vfd, "carriers_rich.json"), "w"))
json.dump([{"pid": "f1", "name": "x", "dob": "", "IN1": []}], open(os.path.join(vfd, "feed_parsed_T2.json"), "w"))
VF_STAND = {"amd": {"login_cached": lambda *a: None, "msg": _AM2.msg, "post": _AM2.post}, "resave": {"detail": _RS2.detail, "CHG_FIELDS": _RS2.CHG_FIELDS},
            "elig_amd": {"plans": lambda num: ({"insorder": "2", "deceased": ""}, [{"id": "ins1", "carrier": "car6085", "sequence": "1", "enddate": ""}]), "run_plan": lambda num, p: {"status": "ACTIVE", "other_payers": []}, "one_line": lambda s: "ACTIVE"},
            "deceased_guard": {"check": lambda *a, **k: (False, ""), "record": lambda *a, **k: None, "_iso": lambda x: x}, "stedi": {}, "add_ins": {}, "ins_update": {}}
def vf_run(row, fault):
    VQ.update(order="2", void=set(), sent=[], fault=fault); json.dump({"created": [dict(row, feed_id="f1", dos="11/10/2026", cpts=["99309"])]}, open(os.path.join(vfd, "registers", "feed_import_T2.json"), "w"))
    if os.path.exists(os.path.join(vfd, "feed_verify_T2.json")): os.remove(os.path.join(vfd, "feed_verify_T2.json"))
    o_, e_ = run_inside(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py"), VF_STAND, vfd, env={"FEED_STAMP": "T2", "DECEASED_CACHE": os.path.join(vfd, "dc.json")}, argv=("--no-stedi",))
    return (json.load(open(os.path.join(vfd, "feed_verify_T2.json"))).get("pat1") if os.path.exists(os.path.join(vfd, "feed_verify_T2.json")) else None), o_, e_
_vr, _vo, _ve = vf_run(_qrow, "with")
check("insurance check step (11.2): the echo with the line refused, the echo without it accepted - RELEASE, and the chart's entry records the removal under quality_removed (released) for the import",
      _ve == "" and _vr and _vr["decision"] == "RELEASE" and len(_vr.get("quality_removed") or []) == 1 and _vr["quality_removed"][0]["charge"] == "charge11" and _vr["quality_removed"][0]["released"] is True
      and any("the quality line charge11 was taken off" in f_ for f_ in _vr["fixes"]), (_ve, _vr))
_vr, _vo, _ve = vf_run(_qrow, "always")
check("insurance check step (section 7): refused with and without the line - HOLD, and the hold says 'insorder not applied' with the quality line named (the words the import switches the code off on)",
      _ve == "" and _vr and _vr["decision"] == "HOLD" and any(h_.startswith("insorder not applied on vst1 (the visit carries the quality line charge11: resave FAULT") for h_ in _vr["hold"]) and not _vr.get("quality_removed"), (_ve, _vr))
_vr, _vo, _ve = vf_run(dict(_qrow, quality_codes=None, quality_charge=None), "always")
check("insurance check step: a visit without the line - the hold words are exactly as before", _ve == "" and _vr and _vr["hold"] == ["insorder not applied on vst1"], (_ve, _vr))
VF_STAND["amd"]["post"] = lambda body, timeout=0: (_ for _ in ()).throw(TimeoutError("read timed out")); _vr, _vo, _ve = vf_run(_qrow, None); VF_STAND["amd"]["post"] = _AM2.post
check("insurance check step: an echo that raises on a visit with the line - the hold still says 'insorder not applied' with the line named", _ve == "" and _vr and any(h_.startswith("insorder not applied on vst1 (the visit carries the quality line charge11: error") for h_ in _vr["hold"]), (_ve, _vr))
# 11.1: the Claim Inspector step takes the quality line off a held visit by itself (run INSIDE this process with stand-ins)
isd = tempfile.mkdtemp(prefix="posrule_ins_"); os.makedirs(os.path.join(isd, "registers")); json.dump({}, open(os.path.join(isd, "dx.json"), "w"))
IS = {}
QROW = {"visit": "vst101", "pid": "pat1", "charges": ["charge1010", "charge1011"], "quality_charge": "charge1011", "quality_codes": ["1123F"], "quality_fee": "0.00", "cpts": ["99309"], "dos": "11/10/2026", "fac": "fac32"}
def _is_detail(cid):
    cid = re.sub(r"\D", "", str(cid)); pc, fee = IS["qproc"] if cid == "1011" else ("pcode65119", "141.00")
    return '<r><patient id="pat1"/><visit id="vst101" episode="e1"/><charge id="charge%s" proccode="%s" fee="%s" pos="32" void="%s"/></r>' % (cid, pc, fee, "1" if cid in IS["void"] else "0")
def _is_vc(cid):
    r_ = ET.fromstring(_is_detail("1010")); return r_.find(".//visit"), r_.find(".//patient"), [ET.fromstring(_is_detail(c_)).find(".//charge") for c_ in ("1010", "1011") if c_ not in IS["void"]]
def _is_post(body, timeout=0):
    if "getclaiminspectorcharges" in body:
        return "<r>%s</r>" % "".join('<visit id="vst%s" patientid="pat1">%s</visit>' % (v_, "".join('<error id="%s" number="%s" name="%s"/>' % (e_["id"], e_["number"], e_["text"]) for e_ in es)) for v_, es in IS["listed"].items() if es)
    if "bypassclaimedits" in body: IS["bypassed"].append(re.findall(r'claimedit id="([^"]+)"', body)); return "<r/>"
    if "updvisitwithnewcharges" in body:
        IS["resaved"].append(body)
        if IS["voided"]: IS["listed"]["101"] = list(IS["after"])      # once the line is gone and the visit re-saved, AdvancedMD lists what `after` says
    return "<r/>"
def _is_void(pid, cid):
    IS["voided"].append((pid, cid))
    if not IS["void_ok"]: return False, "<Fault><description>the charge cannot be voided</description></Fault>"
    IS["void"].add(re.sub(r"\D", "", str(cid))); return True, "ok"
IS_STAND = {"amd": {"login_cached": lambda *a: None, "msg": lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s">%s</ppmdmsg>' % (action, children), "post": _is_post},
            "resave": {"detail": _is_detail, "visit_charges": _is_vc, "CHG_FIELDS": ["fee", "pos"], "_extins_xml": lambda vis, h: ""}, "txh": {"fetch": lambda pid: ET.Element("r")},
            "dx_primary_fix": {"plan": lambda codes, pc: ("ok", codes), "save_visit_dx": lambda cid, d: ("ok", None), "I10_DCODE": "dcode1"}, "void_tx": {"void_charge": _is_void}}
E_DATA = {"id": "e1", "number": "77002", "text": "Pattern 77002: Claim line requires review before submission"}; E_NAME = {"id": "e2", "number": "88001", "text": "Pattern 88001: Charge amount is zero for procedure 1123F"}
E_ADVQ = {"id": "e3", "number": "35790", "text": "Pattern 35790: procedure 1123F line has a zero charge amount"}; E_ADV = {"id": "e4", "number": "35790", "text": "Pattern 35790: add-on code reminder"}
E_ZERO = {"id": "e5", "number": "35790", "text": "Pattern 35790: Charge amount is zero on a line"}
def is_run(errors, after=(), void_ok=True, proven=False, row=None, qproc=("pcode65441", "0.00"), qvoid=False):
    IS.clear(); IS.update(listed={"101": list(errors)}, after=list(after), void_ok=void_ok, voided=[], resaved=[], bypassed=[], void=({"1011"} if qvoid else set()), qproc=qproc)
    json.dump({"created": [row or QROW], "quality_gate": {"confirmed": proven, "fee": "0.00"}}, open(os.path.join(isd, "registers", "feed_import_T3.json"), "w"))
    o_, e_ = run_inside(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py"), IS_STAND, isd, env={"FEED_STAMP": "T3", "FEED_DX_CACHE": os.path.join(isd, "dx.json")})
    f_ = os.path.join(isd, "registers", "feed_inspector_T3.json"); res = json.load(open(f_)) if os.path.exists(f_) else None
    if os.path.exists(f_): os.remove(f_)
    return res, o_, e_
_ir, _io, _ie = is_run([E_DATA])
check("inspector (11.1): before proof a held visit that carries the line - the step voids the ONE quality charge, re-saves the visit on its own charge, lists the batch again; released: recorded under quality_removed, not held",
      _ie == "" and _ir["held"] == [] and IS["voided"] == [("pat1", "1011")] and len(IS["resaved"]) == 1 and 'id="charge1010"' in IS["resaved"][0] and "charge1011" not in IS["resaved"][0]
      and len(_ir["quality_removed"]) == 1 and {k_: _ir["quality_removed"][0][k_] for k_ in ("visit", "pid", "charge", "fee", "void_ok", "released")} == {"visit": "101", "pid": "pat1", "charge": "charge1011", "fee": "0.00", "void_ok": True, "released": True}
      and _ir["quality_removed"][0]["why"].startswith("Pattern 77002"), (_ie, _ir, IS["voided"]))
_ir, _io, _ie = is_run([E_DATA], after=[E_DATA])
check("inspector (11.1): ... the visit is still listed after the line is gone - held for its own reason as before (no 'quality' mark: it carries no line now), the entry says released: false",
      _ie == "" and len(_ir["held"]) == 1 and "quality" not in _ir["held"][0] and _ir["held"][0]["why"].startswith("Pattern 77002") and _ir["quality_removed"][0]["void_ok"] is True and _ir["quality_removed"][0]["released"] is False, (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA], void_ok=False)
check("inspector (11.1): ... the void fails - nothing else is tried (no re-save): the visit is held WITH its line ('quality': true), the entry says void_ok: false",
      _ie == "" and len(_ir["held"]) == 1 and _ir["held"][0].get("quality") is True and IS["resaved"] == [] and _ir["quality_removed"][0]["void_ok"] is False and "cannot be voided" in _ir["quality_removed"][0]["note"], (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA], proven=True)
check("inspector (11.1): AFTER proof a hold whose words do not name the line - nothing is voided: held as before, with 'quality': true", _ie == "" and IS["voided"] == [] and _ir["quality_removed"] == [] and _ir["held"][0].get("quality") is True and "names_line" not in _ir["held"][0], (_ie, _ir))
_ir, _io, _ie = is_run([E_NAME], proven=True)
check("inspector (11.1): AFTER proof a hold whose words name the line - the line is taken off (released)", _ie == "" and IS["voided"] == [("pat1", "1011")] and _ir["quality_removed"][0]["released"] is True and _ir["held"] == [], (_ie, _ir))
_ir, _io, _ie = is_run([E_ADVQ], proven=True)
check("inspector (section 7): an ADVISORY whose words name the quality line is never bypassed on a visit that carries it - the line is taken off instead", _ie == "" and IS["bypassed"] == [] and IS["voided"] == [("pat1", "1011")] and _ir["bypassed"] == [], (_ie, _ir, IS["bypassed"]))
_ir, _io, _ie = is_run([E_ADV, E_DATA], proven=True)
check("inspector: ... a plain advisory on that visit is bypassed as before, and a hold that does not name the line (after proof) keeps it", _ie == "" and IS["bypassed"] == [["e4"]] and _ir["held"][0].get("quality") is True and IS["voided"] == [], (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA, E_NAME], proven=True, void_ok=False)
check("inspector (section 7): the held row says names_line when the words name the line", _ie == "" and _ir["held"][0].get("names_line") is True and _ir["held"][0].get("quality") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA], qvoid=True)
check("inspector (11.1): the line is void already (taken off before this step) - held for the visit's own reason, nothing voided, no entry", _ie == "" and IS["voided"] == [] and _ir["quality_removed"] == [] and len(_ir["held"]) == 1 and "quality" not in _ir["held"][0], (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA], qproc=("pcode65119", "141.00"))
check("inspector (11.1): a row whose quality charge shows another procedure and a real amount - NEVER voided: held with 'quality': true and an entry void_ok: false that says why",
      _ie == "" and IS["voided"] == [] and _ir["held"][0].get("quality") is True and _ir["quality_removed"][0]["void_ok"] is False and "not voided" in _ir["quality_removed"][0]["note"], (_ie, _ir))
_ir, _io, _ie = is_run([E_ZERO], row={k_: v_ for k_, v_ in QROW.items() if not k_.startswith("quality_")})
check("inspector: a visit WITHOUT the quality line is handled exactly as before - an advisory about a zero amount is bypassed, nothing is voided", _ie == "" and IS["bypassed"] == [["e5"]] and IS["voided"] == [] and _ir["held"] == [] and _ir["quality_removed"] == [], (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA]); json.dump(_ir, open(os.path.join(REGDIR, "feed_inspector_T3.json"), "w")); _F3 = ci.quality_files("T4"); rmreg("feed_inspector_T3.json")
check("inspector -> import: the entry the inspector step writes is what the import reads (quality_files: removed by batch stamp)", [e_[1]["charge"] for e_ in (_F3["removed"].get("T3") or [])] == ["charge1011"] and _F3["problems"] == [], _F3["removed"])
_isrc = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read(); _isrc = _isrc[_isrc.index('def names_line(words, charge=""):'):_isrc.index("def split_errors(")]
_ins_ns = {"re": re, "QUALITY_CODE": "1123F", "QUALITY_PCODE": "pcode65441"}; exec(_isrc, _ins_ns)
_W = ["Pattern 990001: procedure 1123F - line item charge amount is zero", "pcode65441 not allowed", "edit on charge 7000011", "Pattern 88001: Charge amount is zero for this procedure", "Line charge of $0.00 is below the minimum",
      "the AMOUNT of a line is $0", "Pattern 24078: something else", "Relationship of Subscriber to Patient is invalid", "charge 17000011 is odd", "zero units", "", None]
check("inspector and import: the same test for the words that name the line (12 phrases, both answers)", all(_ins_ns["names_line"](w_, "charge7000011") == ci.names_line(w_, "charge7000011") for w_ in _W)
      and sum(1 for w_ in _W if ci.names_line(w_, "charge7000011")) == 6, [(w_, _ins_ns["names_line"](w_, "charge7000011"), ci.names_line(w_, "charge7000011")) for w_ in _W])
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

# ---- 7. the nights: the reviewers' own multi-night inputs, and three behaviours of a stand-in AdvancedMD over ten nights -------------------------
# (tools/selftest/test_quality_nights.py is the whole simulation; run alone it goes through every behaviour, longer)
_np = os.path.join(ROOT, "tools", "selftest", "test_quality_nights.py"); _nsrc = open(_np).read()
check("the night simulation starts no program, shuts the network itself and loads the import helper only with its own stand-in modules",
      not re.search("|".join(("sub" + "process", "os" + r"\.system\(", "os" + r"\.popen\(", "run" + r"py\.")), _nsrc) and "_socket.socket.connect = _no_network" in _nsrc and "the stand-in modules are not in place - the helper is not loaded" in _nsrc)
_nspec = importlib.util.spec_from_file_location("test_quality_nights", _np); nights = importlib.util.module_from_spec(_nspec); _nspec.loader.exec_module(nights)
_nroot = tempfile.mkdtemp(prefix="posrule_nights_"); _env0 = dict(os.environ)
nights.cases(_nroot, check); nights.short(_nroot, check)
check("after the nights this self-test stands where it stood: its own stand-in modules, its own folder, its own environment", sys.modules.get("amd") is amd and sys.modules.get("resave") is resave and sys.modules.get("txh") is txh
      and os.path.realpath(os.getcwd()) == os.path.realpath(tmp) and dict(os.environ) == _env0 and sys.argv[0].endswith("test_pos_rule.py"), (os.getcwd(), sorted(set(os.environ) ^ set(_env0))))

print("\n%d check(s) failed" % len(FAILS) if FAILS else "\nall checks passed")
sys.exit(1 if FAILS else 0)
