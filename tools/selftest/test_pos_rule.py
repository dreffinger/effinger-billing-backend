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
# the import's date-of-death guard reads DECEASED_CACHE first: this test names its OWN empty cache, so a cache the calling shell exports never decides a visit here (11/10/2026)
DECEASED_OWN = os.path.join(tmp, "deceased_cache_selftest.json"); open(DECEASED_OWN, "w").write("{}"); os.environ["DECEASED_CACHE"] = DECEASED_OWN
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
        "plain_raises": False, "line_raises": False, "all_raise": False, "detail_noproc": False, "detail_text": True,      # ..._raises: the charge call ends in a time-out (after a refusal / when it carries the quality line / always); detail_noproc: the charge detail shows no procedure; detail_text: it names the procedure's code text
        "refuse_mvp": False, "drop_mvp": False, "reverse": False}      # refuse_mvp: a fault to a charge call that carries the M0004 line; drop_mvp: stores the visit without its M0004 line; reverse: the answer lists the charges in reverse
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
        if ECHO["refuse_all"] or (ECHO["refuse_quality"] and "pcode65441" in body) or (ECHO["refuse_mvp"] and "pcode692183" in body):
            REFUSED.add(_v)
            if ECHO["partial"]: CHART.setdefault(ECHO["partial"][0], []).append(tuple(ECHO["partial"][1:]))      # the stand-in stores a line although it answers with a fault
            return "<r><Fault>the charge amount is not accepted</Fault></r>"
        sent = re.findall(r'proccode="(pcode\d+)" cobcode="" pos="(\d+)" tos="01" units="[^"]*" netfee="0" fee="([^"]*)"', body); vid = re.search(r'<visit id="(vst\d+)"', body).group(1)
        if ECHO["drop_quality"]: sent = [x for x in sent if x[0] != "pcode65441"]
        if ECHO["drop_mvp"]: sent = [x for x in sent if x[0] != "pcode692183"]
        num = list(enumerate(sent))                                                   # the charge number follows the order SENT ...
        for i, (pc, q, fee) in num: PROC["%d%d" % (int(vid[3:]), i)] = pc
        if ECHO["qfirst"]: num = sorted(num, key=lambda x: x[1][0] != "pcode65441")   # ... the answer can list the quality charge first
        if ECHO["reverse"]: num = list(reversed(num))                                 # ... or every charge in reverse
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
CHART = {}                                                             # chart number -> [(cpt, 'MM/DD/YYYY'[, facility name])] the stand-in history returns
txh = types.ModuleType("txh")
def _fetch(num):
    root = ET.Element("r")
    for i, row in enumerate(CHART.get(str(num), [])):
        ET.SubElement(root, "charge", dict({"id": "charge%d" % (i + 1), "proccode": row[0], "dos": row[1], "void": "0", "fee": "1.00"}, **({"facname": row[2]} if len(row) > 2 else {})))
    return root
txh.fetch = _fetch
sys.modules.update({"amd": amd, "resave": resave, "txh": txh})
spec = importlib.util.spec_from_file_location("claimocity_import", HELPER); ci = importlib.util.module_from_spec(spec); spec.loader.exec_module(ci)
CODE_TEXT.update({v: k for k, v in ci.PCODE.items()}); CODE_TEXT[ci.QUALITY_PCODE] = ci.QUALITY_CODE; CODE_TEXT[ci.MVP_PCODE] = ci.MVP_CODE      # what the stand-in's charge detail names each procedure id
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
check("build: a visit sent twice with a corrected admission date keeps its own building and clinician (the copies agree on both); the date the copies do not agree on comes from the message's own LAST copy (review W2), and the visit is named for a check",
      i6["fac"] == "fac29" and [q for _, q in pp6] == ["21"] and i6["prof"] == "prof13" and i6["pos_err"] == "" and i6["msg_own"] is False and ci.msg_agreed(msg("m6", [("99232", "20261020")])) == (B["h1"], NPI, None)
      and i6["admit"] == "20261019" and 'hospitalizationfrom="10/19/2026"' in b6 and i6.get("msg_fallback") == "admission date: this message's own last copy", i6)
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
_regp = os.path.join(tmp, "registers", "feed_import_SELFTEST.json")
check("main --dry: the broken match row is a failed message - and a dry run that meets one writes NO register (11/10/2026, challenge review: that register made the live run of the same stamp skip whole patients)",
      "ERR ['not', 'a', 'chart']" in out and not os.path.exists(_regp), (os.path.exists(_regp), out[-300:]))
json.dump({"created": [], "skipped": [], "failed": [{"feed_id": "n3", "pid": ["not", "a", "chart"], "lines": [], "err": "odd"}]}, open(_regp, "w"))      # the odd row a failed message used to leave (its chart not a chart number), written here
check("an odd row in a register (its chart not a chart number) is there for the next check", os.path.exists(_regp) and isinstance(json.load(open(_regp))["failed"][0]["pid"], list))
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
# ---- 4b2. round 6, step 4 (11/10/2026): what round 5's confirmation reviewers still found, and William's initial-visit rule ------------------------
# Each check is built from the finding's own exact input (feed patient, buildings, clinicians, dates, file order). The raw feed files are read when the
# helper loads, so a FRESH copy of the import helper is loaded for each input, over its own folder of raw files, with the same stand-in modules.
import builtins as _bi
_S4N = [0]
def s4_fresh(files, default_encoding=None):
    """A fresh copy of the import helper over its own raw feed files {name: text} (written as UTF-8). default_encoding: every open() of the helper
    that names no encoding reads with this one - a machine whose default is not UTF-8."""
    d_ = tempfile.mkdtemp(prefix="posrule_s4_", dir=tmp)
    for n_, t_ in files.items(): open(os.path.join(d_, n_), "w", encoding="utf-8").write(t_)
    _old = os.environ["FEED_HL7_DIR"]; os.environ["FEED_HL7_DIR"] = d_; _S4N[0] += 1
    try:
        sp_ = importlib.util.spec_from_file_location("claimocity_import_s4_%d" % _S4N[0], HELPER); m_ = importlib.util.module_from_spec(sp_)
        if default_encoding: m_.open = lambda f, mode="r", *a, **k: _bi.open(f, mode, *a, **(dict(k, encoding=default_encoding) if "b" not in mode and not k.get("encoding") else k))
        sp_.loader.exec_module(m_)
    finally: os.environ["FEED_HL7_DIR"] = _old
    if not (m_.amd is amd and m_.resave is resave and m_.txh is txh): raise RuntimeError("the fresh copy did not load the stand-in modules")
    m_.run_day = ci.run_day
    return m_
S4_REG = os.path.join(tmp, "registers", "feed_import_SELFTEST.json")
def s4_run(m_, parsed, match, argv=("--all",), keep=False):
    """main() of a fresh copy over parsed messages (live against the stand-in AdvancedMD, or --dry) -> (what it printed, its register or None)."""
    m_.PARSED[:] = parsed; m_.MATCH.clear(); m_.MATCH.update({NAME(k_).upper().strip() + "|" + DOBK: {"resolved": v_} for k_, v_ in match.items()})
    POSTS.clear(); buf_ = io.StringIO(); _argv = sys.argv[:]; sys.argv = ["claimocity_import.py"] + list(argv); m_._ctx.clear(); m_.BATCH_NF.clear(); m_.BATCH_NF_ERR[0] = ""; _sl = m_.time.sleep; m_.time.sleep = lambda s: None
    try:
        with contextlib.redirect_stdout(buf_): m_.main()
    finally: m_.time.sleep = _sl; sys.argv = _argv
    reg_ = json.load(open(S4_REG)) if os.path.exists(S4_REG) else None
    if reg_ is not None and not keep: os.remove(S4_REG)
    return buf_.getvalue(), reg_
def s4_rows(reg_, pid_): return sorted([r_ for r_ in (reg_ or {}).get("created", []) if r_.get("pid") == pid_], key=lambda r_: r_["dos"][6:] + r_["dos"][:5])
def s4_brief(rows_): return [(r_["dos"], r_["cpts"], r_["pos_lines"], r_["pos_kind"], r_.get("fac"), str(r_.get("pos_err"))[:24]) for r_ in rows_]
WO = "Westminster Oaks-Bertrand Health Center"; BRY_AMD = "BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC"
check("4b2 setup: no import register is left over from the sections before (each input below starts clean)", not any(f_.startswith("feed_import_") for f_ in os.listdir(os.path.join(tmp, "registers"))), os.listdir(os.path.join(tmp, "registers")))
# C1 (round-5 code review, should-fix; challenge review confirmed): a visit day the feed itself sends from two buildings must read as a move
s4c1 = s4_fresh({"20260905.hl7": hl7("t1", WO, "", [("99309", "20260905")], NPI) + hl7("t1", B["n1"], "", [("99309", "20260905")], NP_NPI)
                 + hl7("t1", WO, "", [("99308", "20261008")], NPI) + hl7("t1", WO, "", [("99487", "20261031")], NPI)})
CHART["801"] = [("99309", "08/03/2026", BRY_AMD)]
S4_C1A = [P_("t1", "t1", [("99309", "20260905")]), P_("t1", "t1", [("99309", "20260905")]), P_("t1", "t1", [("99308", "20261008")]), P_("t1", "t1", [("99487", "20261031")])]
s4o, s4r = s4_run(s4c1, S4_C1A, {"t1": "pat801"}); s4x = s4_rows(s4r, "pat801")
check("C1 (exact input): the 09/05 visit the feed sent from Westminster AND from Brynwood is entered once, at the feed's 31 and reported; the next visit (10/08, 33 days later) and the October CCM stay at 31 - that day reads as a move, as a day the chart and the feed name under two buildings does (1478f14: 32 monthly / 32 CCM, named nowhere)",
      [x_["dos"] for x_ in s4x] == ["09/05/2026", "10/08/2026", "10/31/2026"] and "2 buildings" in s4x[0]["pos_err"] and s4x[0]["pos_lines"] == ["31"]
      and s4x[1]["pos_lines"] == ["31"] and s4x[1]["pos_kind"] == ["moved"] and s4x[2]["pos_lines"] == ["31"] and s4x[2]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
check("C1: the visit's created row keeps every building its copies named (tie_lines), so a later batch still sees that day under two buildings; one-building visits carry none",
      s4x and s4x[0].get("tie_lines") == [["99309", "09/05/2026", B["n1"]], ["99309", "09/05/2026", WO]] and "tie_lines" not in s4x[1] and "tie_lines" not in s4x[2], s4x[0].get("tie_lines"))
check("C1: a message sent from two buildings that is NOT entered (a code the table lacks, a diagnosis AdvancedMD does not know) keeps its visit lines once per building in the register, so a later batch reads that day the same way",
      s4c1.seen_lines(P_("t1", "t1", [("99309", "20260905")])) == [["99309", "09/05/2026", B["n1"]], ["99309", "09/05/2026", WO]] and s4c1.seen_lines(P_("t1", "t1", [("99308", "20261008")])) == [["99308", "10/08/2026", WO]])
check("C1: the batch list carries that day once per building (msg_buildings), and a message sent from one building keeps exactly its own",
      s4c1.msg_buildings(P_("t1", "t1", [("99309", "20260905")])) == [B["n1"], WO] and s4c1.msg_buildings(P_("t1", "t1", [("99308", "20261008")])) == [WO], s4c1.BATCH_NF.get("pat801"))
# C1b: the review's second input - only the last hunk (the visit's OWN day named under two buildings) keeps the month's CCM at 31
s4c1b = s4_fresh({"20261002.hl7": hl7("t2", B["n2"], "", [("99309", "20261002")], NP_NPI) + hl7("t2", WO, "", [("99309", "20261002")], NPI) + hl7("t2", B["n2"], "", [("99487", "20261031")], NPI)})
CHART["802"] = [("99309", "09/03/2026", "ASPIRE AT TALLAHASSEE")]
s4o, s4r = s4_run(s4c1b, [P_("t2", "t2", [("99309", "20261002")]), P_("t2", "t2", [("99309", "20261002")]), P_("t2", "t2", [("99487", "20261031")])], {"t2": "pat802"}); s4x = s4_rows(s4r, "pat802")
check("C1b (exact input): the October CCM of a resident whose 10/02 visit the feed sent from Aspire AND Westminster stays at 31 (1478f14: 32)", [x_["dos"] for x_ in s4x] == ["10/02/2026", "10/31/2026"] and s4x[1]["pos_lines"] == ["31"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
check("C1b: the CCM-month check reads a visit whose OWN day is named under two buildings as a move even with no building for the CCM itself (the review's last hunk)",
      ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99309", "09/03/2026", "ASPIRE AT TALLAHASSEE"), ("99309", "10/02/2026", B["n2"]), ("99309", "10/02/2026", WO)])[2] == ["ccm-skilled-month"]
      and ci.nf_visit_kind("99309", "10/02/2026", [("99309", "09/03/2026", "ASPIRE AT TALLAHASSEE"), ("99309", "10/02/2026", B["n2"]), ("99309", "10/02/2026", WO)])[0] == "moved"
      and ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99309", "09/03/2026", "ASPIRE AT TALLAHASSEE"), ("99309", "10/02/2026", B["n2"])])[2] == ["ccm"])
# the challenge reviewer's limit of the review's fix (tie_then_next_batch): yesterday's batch entered the two-building visit; today's brings the next visit and the CCM
s4t = s4_fresh({"20260905.hl7": hl7("t3", B["n1"], "", [("99309", "20260905")], NP_NPI) + hl7("t3", WO, "", [("99309", "20260905")], NPI)})
CHART["803"] = [("99309", "08/03/2026", BRY_AMD)]
s4o, s4r = s4_run(s4t, [P_("t3", "t3", [("99309", "20260905")]), P_("t3", "t3", [("99309", "20260905")])], {"t3": "pat803"}, keep=True)
s4y = os.path.join(tmp, "registers", "feed_import_20261108T1200Z.json"); os.rename(S4_REG, s4y)                                   # yesterday's register
CHART["803"].append(("99309", "09/05/2026", "WESTMINSTER BERTRAND HEALTH CENTER"))                                                  # ... and the visit as it now stands on the chart
s4t2 = s4_fresh({"20261031.hl7": hl7("t3", WO, "", [("99308", "20261008")], NPI) + hl7("t3", WO, "", [("99487", "20261031")], NPI)})
s4o, s4r = s4_run(s4t2, [P_("t3", "t3", [("99308", "20261008")]), P_("t3", "t3", [("99487", "20261031")])], {"t3": "pat803"}); s4x = s4_rows(s4r, "pat803")
check("C1 (challenge review, tie_then_next_batch): yesterday's batch entered the visit the feed sent from two buildings; in today's batch the next visit and the month's CCM still read that day as named under two buildings - 31 / 31 (without the register's tie_lines the chart's one building made them 32 / 32)",
      [x_["dos"] for x_ in s4x] == ["10/08/2026", "10/31/2026"] and s4x[0]["pos_kind"] == ["moved"] and s4x[0]["pos_lines"] == ["31"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
os.remove(s4y)
# W2 (round-5 ops-and-words review; the cross-check of 1478f14, input c): a disagreeing admission date comes from the LAST raw copy of that message
def s4_admit(files, fid, lines):
    m_ = s4_fresh(files); o_, i_ = m_.build(msg(fid, lines), ctx())
    return (i_ or {}).get("admit"), (o_[1] if o_ else ""), i_
s4h1 = hl7("x1", B["h1"], "20261030", [("99232", "20261102")], NPI); s4h2 = hl7("x1", B["h1"], "20261101", [("99232", "20261102")], NP_NPI); s4n = hl7("x1", B["n1"], "20260923", [("99309", "20261103")], NP_NPI)
s4a1 = s4_admit({"a.hl7": s4h1 + s4h2 + s4n}, "x1", [("99232", "20261102")]); s4a2 = s4_admit({"a.hl7": s4n + s4h1 + s4h2}, "x1", [("99232", "20261102")])
check("W2 (cross-check of 1478f14, exact input c): a hospital 99232 of 11/02 sent by the physician (admitted 10/30) and again by the nurse practitioner (admitted 11/01), then a nursing 99309 of 11/03 (admitted 09/23) - the hospital visit takes 11/01, its own last copy's date, in BOTH read orders (1478f14: 09/23, or 11/01 only when the nursing message was read first)",
      s4a1[0] == s4a2[0] == "20261101" and 'hospitalizationfrom="11/01/2026"' in s4a1[1] and 'hospitalizationfrom="11/01/2026"' in s4a2[1] and s4a1[2]["fac"] == s4a2[2]["fac"] == "fac29"
      and s4a1[2].get("msg_fallback") == s4a2[2].get("msg_fallback") == "clinician: the patient's last-read message; admission date: this message's own last copy", (s4a1[0], s4a2[0], s4a1[2].get("msg_fallback")))
s4w = s4_admit({"a.hl7": hl7("tw1", B["h1"], "20261028", [("99232", "20261030")], NPI) + hl7("tw1", B["h1"], "20261027", [("99232", "20261030")], NPI) + hl7("tw1", B["n1"], "20250114", [("99309", "20261105")], NP_NPI)}, "tw1", [("99232", "20261030")])
s4w0 = s4_admit({"a.hl7": hl7("tw1", B["h1"], "20261028", [("99232", "20261030")], NPI) + hl7("tw1", B["n1"], "20250114", [("99309", "20261105")], NP_NPI)}, "tw1", [("99232", "20261030")])
check("W2 (ops-and-words review, exact input): HCA 99232 of 10/30 sent with admission 10/28, then with 10/27, then a Brynwood message admitted 01/14/2025 - the visit takes 10/27/2026 (the corrected copy), never the nursing building's 01/14/2025; the one-copy control keeps 10/28",
      s4w[0] == "20261027" and 'hospitalizationfrom="10/27/2026"' in s4w[1] and s4w0[0] == "20261028" and s4w[2]["fac"] == "fac29" and s4w[2]["prof"] == "prof13", (s4w[0], s4w0[0]))
s4v = [s4_admit({"a.hl7": hl7("p5", B["h1"], "20261018", [("99232", "20261020")], NPI) + hl7("p5", B["h1"], "20261019", [("99232", "20261020")], NPI) + t_}, "p5", [("99232", "20261020")])[0]
       for t_ in (hl7("p5", B["n1"], "20261001", [("99309", "20261102")], NP_NPI), hl7("p5", B["a1"], "20250104", [("99344", "20261102")], NP_NPI), hl7("p5", B["h1"], "20261105", [("99223", "20261105")], NPI),
                  "MSH|^~\\&|feed|" + B["n1"] + "|x|x|20261102||DFT^P03|1|P|2.3\r" + pv1(NP_NPI, "20261001") + "\rPID|1||p5\r" + ft1("99309", "20261102") + "\r")]
check("W2 / C5 (code review's input and its variants): the twice-sent hospital visit keeps 10/19/2026, its own last copy's date, whatever message of the patient is read last (a nursing building, an ALF admitted 01/04/2025, a later hospital stay, a message with PV1 before PID)", s4v == ["20261019"] * 4, s4v)
# a hospital follow-up message with no admission date of its own (integration second reviewer, M3): decided - nothing is taken from another message
s4f = []
for s4ord in (0, 1):
    _f2 = [hl7("s2", B["h1"], "", [("99232", "20261020")], NPI), hl7("s2", B["h1"], "20261018", [("99223", "20261018")], NPI)]
    m_ = s4_fresh({"a.hl7": "".join(_f2 if s4ord == 0 else _f2[::-1])})
    s4f.append((m_.build(msg("s2", [("99232", "20261020")]), ctx())[1]["admit"], m_.build(msg("s2", [("99223", "20261018")]), ctx())[1]["admit"]))
check("second reviewers (integration M3, exact input, both orders): a hospital follow-up message with no admission date of its own is sent without one - never a date from another message of the patient (W2) - and the 99223 keeps its own; the feed inspector step anchors the follow-up on that 99223 (45 days) or holds it for William",
      s4f == [("", "20261018"), ("", "20261018")] and "anchor_99223" in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read(), s4f)
# the cross-check of 1478f14, item a: the raw files are read as UTF-8, as feed_parse_dft_1028.py reads them
s4e = s4_fresh({"e.hl7": hl7("zé9", B["n1"], "", [("99309", "20261102")], NP_NPI)}, default_encoding="latin-1")
check("cross-check (a): on a machine whose default encoding is not UTF-8, a feed patient id with a non-ASCII letter still finds its own message - building and clinician (the parser reads the same file as UTF-8)",
      s4e.msg_own(msg("zé9", [("99309", "20261102")])) == (B["n1"], NP_NPI, "") and "zé9" in s4e.FACOF and 'encoding="utf-8"' in open(HELPER).read() and 'encoding="utf-8"' in open(os.path.join(ROOT, "scripts", "helpers", "feed_parse_dft_1028.py")).read(), sorted(s4e.FACOF))
check("cross-check (b): this self-test names its OWN empty deceased cache - whatever the calling shell exports, the import's date-of-death guard reads this file here", os.environ.get("DECEASED_CACHE") == DECEASED_OWN and DECEASED_OWN.startswith(tmp) and json.load(open(DECEASED_OWN)) == {})
# the second reviewers' two-building patients whose CCM went in at 32 with nothing named (logic M1, message-identity X2)
s4l = s4_fresh({"a.hl7": hl7("q1", B["n1"], "", [("99309", "20261003")], NP_NPI) + hl7("q1", B["n2"], "", [("99487", "20261031"), ("99489", "20261031")], NPI)})
CHART["811"] = [("99309", "09/05/2026", BRY_AMD)]
s4o, s4r = s4_run(s4l, [P_("q1", "q1", [("99309", "20261003")]), P_("q1", "q1", [("99487", "20261031"), ("99489", "20261031")])], {"q1": "pat811"}); s4x = s4_rows(s4r, "pat811")
check("second reviewers (logic M1, exact input): the CCM from Aspire of a resident whose nursing visits are at Brynwood that month stays at the feed's 31 and is listed for William (was 32 / 32 with nothing named); the Brynwood visit itself is still the monthly 32",
      [x_["cpts"] for x_ in s4x] == [["99309"], ["99487", "99489"]] and s4x[0]["pos_lines"] == ["32"] and s4x[1]["pos_lines"] == ["31", "31"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"] * 2, s4_brief(s4x))
s4l2 = s4_fresh({"a.hl7": hl7("q2", B["n2"], "", [("99487", "20261031")], NPI)})
CHART["812"] = [("99309", "09/05/2026", BRY_AMD), ("99309", "10/03/2026", BRY_AMD)]
s4o, s4r = s4_run(s4l2, [P_("q2", "q2", [("99487", "20261031")])], {"q2": "pat812"}); s4x = s4_rows(s4r, "pat812")
check("second reviewers (logic M1, variant X2): both Brynwood visits already on the chart and only the Aspire CCM in the batch - 31, listed for William", s4x and s4x[0]["pos_lines"] == ["31"] and s4x[0]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
s4m = s4_fresh({"a.hl7": hl7("m7x", B["n1"], "", [("99309", "20261005")], NP_NPI) + hl7("m7x", B["n2"], "", [("99487", "20261031"), ("99489", "20261031")], NPI)
                + hl7("m8x", B["a1"], "", [("99344", "20261010")], NP_NPI) + hl7("m8x", B["n2"], "", [("99487", "20261031")], NPI)})
CHART["813"] = [("99309", "09/05/2026", BRY_AMD)]; CHART["814"] = []
s4o, s4r = s4_run(s4m, [P_("m7x", "m7x", [("99309", "20261005")]), P_("m7x", "m7x", [("99487", "20261031"), ("99489", "20261031")]), P_("m8x", "m8x", [("99344", "20261010")]), P_("m8x", "m8x", [("99487", "20261031")])],
                  {"m7x": "pat813", "m8x": "pat814"})
s4x = s4_rows(s4r, "pat813"); s4z = s4_rows(s4r, "pat814")
check("second reviewers (message-identity X2, exact input): M7 - Brynwood visit 10/05, then the physician's Aspire CCM of 10/31: 31 / 31 for William (was 32 / 32); M8 - an assisted-living visit, then an Aspire CCM: 31 (already so since round 5's F2)",
      s4x[1]["pos_lines"] == ["31", "31"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"] * 2 and s4x[0]["pos_lines"] == ["32"] and s4z[1]["pos_lines"] == ["31"] and s4z[1]["pos_kind"] == ["ccm-skilled-month"], (s4_brief(s4x), s4_brief(s4z)))
_ccm2 = [("99309", "09/05/2026", BRY_AMD), ("99309", "10/03/2026", BRY_AMD)]
check("CCM in another building: the pure rule - a CCM entered at Aspire reads the residents' Brynwood visits as another building (31); entered at Brynwood itself it stays the long-term 32; a visit with no building name changes nothing",
      ci.pos_lines([("99487", "10/31/2026")], "31", True, _ccm2, "fac32")[0] == ["31"] and ci.pos_lines([("99487", "10/31/2026")], "31", True, _ccm2, "fac34")[0] == ["32"]
      and ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026")], "fac32")[0] == ["32"] and ci.seen_at_skilled_frequency("10/31/2026", _ccm2, "fac34") is False)
# a dry run writes nothing (challenge review, gap 2, exact shape): a dry run that meets a fault no longer makes the live run of the same stamp drop a visit
s4g = s4_fresh({"a.hl7": hl7("pa", B["n1"], "", [("99309", "20261005")], NP_NPI) + hl7("pa", B["n1"], "", [("99309", "20261104")], NP_NPI) + hl7("pb", B["n2"], "", [("99309", "20261103")], NP_NPI)})
CHART["711"] = [("99309", "10/05/2026", BRY_AMD)]; CHART["712"] = []
S4_GAP2 = [P_("pa", "pa", [("99309", "20261005")]), P_("pa", "pa", [("99309", "20261104")]), P_("pb", "pb", [("99309", "20261103")])]
s4o, s4r = s4_run(s4g, S4_GAP2, {"pa": "pat711", "pb": ["not", "a", "chart"]}, argv=("--dry",))
check("challenge review (gap 2): a dry run that meets a failed message (and skips a visit already in AdvancedMD) writes NO register", s4r is None and "ERR" in s4o and "skip: all lines already in AMD" in s4o, s4o[-300:])
s4o, s4r = s4_run(s4g, S4_GAP2, {"pa": "pat711", "pb": "pat712"})
check("challenge review (gap 2): ... so the live run of the SAME stamp still enters pa's new visit of 11/04 (and pb's) - before, the dry run's register made it count pa as done", [(x_["pid"], x_["dos"]) for x_ in s4r["created"]] == [("pat711", "11/04/2026"), ("pat712", "11/03/2026")], s4r["created"])
s4dc = os.path.join(tmp, "deceased_s4.json"); json.dump({"712": {"dod": "2026-11-" + "01"}}, open(s4dc, "w")); os.environ["DECEASED_CACHE"] = s4dc
try: s4o, s4r = s4_run(s4g, S4_GAP2[2:], {"pb": "pat712"}, argv=("--dry",))
finally: os.environ["DECEASED_CACHE"] = DECEASED_OWN
check("challenge review (gap 2): the dry run's other write - a visit dated after the cached date of death is skipped - writes no register either", s4r is None and "DOS after date of death - not entered" in s4o, s4o[-300:])
# section 12 (William 11/10/2026): an initial nursing-facility visit 99306 is always entered under the physician, every line of it
s4i = s4_fresh({"a.hl7": hl7("i1", B["n2"], "", [("99306", "20261102")], NP_NPI) + hl7("i2", B["n2"], "", [("99306", "20261103"), ("99497", "20261103")], NP_NPI)
                + hl7("i3", B["n2"], "", [("99309", "20261104")], NP_NPI) + hl7("i4", B["n2"], "", [("99497", "20261105")], NP_NPI)
                + hl7("i5", B["n2"], "", [("99306", "20261106")], NPI) + hl7("i6", B["n2"], "", [("99306", "20261107")], "")})
s4b = {k_: s4i.build(msg(k_, l_), ctx()) for k_, l_ in (("i1", [("99306", "20261102")]), ("i2", [("99306", "20261103"), ("99497", "20261103")]), ("i3", [("99309", "20261104")]),
                                                       ("i4", [("99497", "20261105")]), ("i5", [("99306", "20261106")]), ("i6", [("99306", "20261107")]))}
check("12.1: the nurse practitioner's 99306 goes in under the physician (prof13); the register keeps what the message named (prof_feed prof15) and why",
      s4b["i1"][1]["prof"] == "prof13" and s4b["i1"][1].get("prof_feed") == "prof15" and s4b["i1"][1].get("prof_why") == "initial nursing-facility visit: always the physician (William 11/10/2026)"
      and 'profile="prof13"' in s4b["i1"][0][0] and 'profile="prof13"' in s4b["i1"][0][1] and "prof15" not in s4b["i1"][0][0] + s4b["i1"][0][1], s4b["i1"][1])
check("12.1: with its 99497 the WHOLE visit goes in under the physician - one visit, every line, the advance-care-planning line included", s4b["i2"][1]["prof"] == "prof13" and s4b["i2"][1].get("prof_feed") == "prof15" and s4b["i2"][1]["cpts"] == ["99306", "99497"]
      and s4b["i2"][0][1].count("<charge ") == 2 and 'profile="prof15"' not in s4b["i2"][0][1], s4b["i2"][1])
check("12.1 / 12.4: the nurse practitioner's 99309 and a lone 99497 keep her profile; the physician's own 99306 is unchanged and carries no prof_feed",
      (s4b["i3"][1]["prof"], s4b["i4"][1]["prof"], s4b["i5"][1]["prof"]) == ("prof15", "prof15", "prof13") and not any("prof_feed" in s4b[k_][1] or "prof_why" in s4b[k_][1] for k_ in ("i3", "i4", "i5")))
check("12.4: a 99306 whose message names no readable clinician goes in under the physician and is NOT counted as 'clinician not known' (the rule decided it)",
      s4b["i6"][1]["prof"] == "prof13" and s4b["i6"][1]["prof_default"] is False and "prof_feed" not in s4b["i6"][1] and str(s4b["i6"][1].get("prof_why")).startswith("initial nursing-facility visit"), s4b["i6"][1])
s4i.INITIAL_NF = set(); s4nr = {k_: s4i.build(msg(k_, l_), ctx()) for k_, l_ in (("i1", [("99306", "20261102")]), ("i2", [("99306", "20261103"), ("99497", "20261103")]), ("i6", [("99306", "20261107")]))}; s4i.INITIAL_NF = {"99304", "99305", "99306"}
check("12.4: everything else in the request is byte-identical - with the rule switched off the same visits differ only in the profile (the visit's create call and its charge call)",
      all(s4nr[k_][0][j_].replace('profile="prof15"', 'profile="prof13"') == s4b[k_][0][j_] for k_ in ("i1", "i2") for j_ in (0, 1, 2)) and all(s4nr["i6"][0][j_] == s4b["i6"][0][j_] for j_ in (0, 1, 2))
      and s4nr["i1"][1]["prof"] == "prof15" and s4nr["i6"][1]["prof_default"] is True)
_qd, _md = s4i.quality_due, s4i.mvp_due; s4i.quality_due = lambda *a, **k: 0; s4seen = []; s4i.mvp_due = lambda own_ok, prof, year, pos: s4seen.append((own_ok, prof)) or True
s4q = s4i.build(msg("i1", [("99306", "20261102")]), ctx()); s4i.quality_due, s4i.mvp_due = _qd, _md
check("12.3: the option code M0004's once-per-clinician ledger is asked for the profile the visit is ENTERED under (prof13), not the one the feed named", s4seen == [(True, "prof13")] and s4q[1].get("mvp_prof") == "prof13", (s4seen, s4q[1].get("mvp_prof")))
CHART.update({"821": [], "822": [], "823": [], "824": [], "825": [], "826": []})
s4o, s4r = s4_run(s4i, [P_(k_, k_, [(c_, d_.replace("/", "")[4:] + d_.replace("/", "")[:4]) for c_, d_ in l_]) for k_, l_ in (("i1", [("99306", "11/02/2026")]), ("i2", [("99306", "11/03/2026"), ("99497", "11/03/2026")]), ("i3", [("99309", "11/04/2026")]),
                    ("i4", [("99497", "11/05/2026")]), ("i5", [("99306", "11/06/2026")]), ("i6", [("99306", "11/07/2026")]))], {"i1": "pat821", "i2": "pat822", "i3": "pat823", "i4": "pat824", "i5": "pat825", "i6": "pat826"})
check("12.2: one log line per changed visit ('INITIAL VISIT under the physician <chart> <date> - the feed named <profile>'), a counter in DONE, nothing for the others; the addvisit calls carry prof13",
      "INITIAL VISIT under the physician pat821 11/02/2026 - the feed named prof15" in s4o and "INITIAL VISIT under the physician pat822 11/03/2026 - the feed named prof15" in s4o and s4o.count("INITIAL VISIT under the physician") == 2
      and "'initial nursing-facility visit entered under the physician although the feed named another clinician (William 11/10/2026)': 2" in s4o and "clinician id of the feed message is not one of the practice's two" not in s4o
      and sorted(r_["pid"] for r_ in s4r["created"] if r_.get("prof_feed")) == ["pat821", "pat822"] and {r_["pid"]: r_["prof"] for r_ in s4r["created"]} == {"pat821": "prof13", "pat822": "prof13", "pat823": "prof15", "pat824": "prof15", "pat825": "prof13", "pat826": "prof13"}, s4o[-700:])
check("4b2 teardown: nothing of these inputs is left in the registers folder", not any(f_.startswith("feed_import_") for f_ in os.listdir(os.path.join(tmp, "registers"))), os.listdir(os.path.join(tmp, "registers")))
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
def live(parsed, env=None, argv=("--all",), keep_own=False, menv=None, **echo):      # env = QUALITY_CODE, menv = MVP_CODE (None = not set)
    ECHO.update(echo); DETAILS.clear(); REFUSED.clear(); old = os.environ.get("QUALITY_CODE"); mold = os.environ.get("MVP_CODE")
    if env is None: os.environ.pop("QUALITY_CODE", None)
    else: os.environ["QUALITY_CODE"] = env
    if menv is None: os.environ.pop("MVP_CODE", None)
    else: os.environ["MVP_CODE"] = menv
    try: return run_live(parsed, argv=argv, keep_own=keep_own)
    finally:
        if old is None: os.environ.pop("QUALITY_CODE", None)
        else: os.environ["QUALITY_CODE"] = old
        if mold is None: os.environ.pop("MVP_CODE", None)
        else: os.environ["MVP_CODE"] = mold
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
# ---- 4d. the option code M0004 (William 11/10/2026, about M0004 - procedure id pcode692183 in AdvancedMD's list: "use it"): once per clinician per year, with the 1123F line, after proof ----
MP = "pcode692183"
MCHG = r'<charge id=""(?:(?!</charge>).)*proccode="pcode692183"(?:(?!</charge>).)*</charge>'      # the M0004 line as it is sent
def mreset(**kw): ci.MVP.clear(); ci.MVP.update(ci._mvp_fresh()); ci.MVP.update(kw)
PROVEN_Q = dict(confirmed=True, budget=None)                                                       # the 1123F pilot proven (no cap)
def own_msg(fid, lines, npi=NPI, bld=None, dob="1940" + "0215"):      # a made-up feed message whose raw copy names its own building and clinician (msg_own)
    b_ = bld or B["n2"]; ci.MSGOF[ci.msg_key(fid, lines)] = {(b_, npi, "")}; ci.FACOF[fid] = b_; ci.FACS[fid] = {b_}; ci.NPIOF[fid] = npi
    return qmsg(fid, lines, dob)
# 4d.1 when it rides (mvp_due through build())
qreset(**PROVEN_Q); mreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
_ml = re.findall(MCHG, out[1]); _qq = re.findall(QCHG, out[1])
check("M0004 (8.2): after proof a visit of the physician's own message carries 1123F AND the M0004 line - the M0004 line LAST, right after the 1123F line, the same line with M0004's id (same date, place of service, amount, ONE diagnosis, no modifier)",
      pp == [("pcode65119", "32"), (QP, "32"), (MP, "32")] and len(_ml) == 1 and len(_qq) == 1 and _ml[0] == _qq[0].replace(QP, MP) and out[1].index(_qq[0]) + len(_qq[0]) == out[1].index(_ml[0])
      and info["mvp_codes"] == ["M0004"] and info["mvp_prof"] == "prof13" and info["mvp_fee"] == "0.00" and info["mvp_dos"] == "11/02/2026" and info["mvp_pos"] == "32" and 'modcodes=""' in _ml[0] and _ml[0].count("<diagcode ") == 1, (pp, info))
check("M0004 (8.2): the visit's own request is byte for byte the request without the lines (both taken out), and the 1123F-only form is that request with the M0004 line taken out",
      re.sub(QCHG, "", re.sub(MCHG, "", out[1])) == out[2] and QP not in out[2] and MP not in out[2] and re.sub(MCHG, "", out[1]).count("<charge ") == 2 and out[1].rstrip().endswith("</charge></chargelist></visit></ppmdmsg>"), out[1][-400:])
qreset(**dict(PROVEN_Q, off="reference")); mreset(); out0, info0, _p0 = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx([("99309", "10/03/2026")]))
check("M0004 (8.2): ... and the create call and the visit's own register fields are those of the visit with the code switched off", out0[0] == out[0] and out0[1] == out[2] and info0 == {k: v for k, v in info.items() if not k.startswith(("quality_", "mvp_"))}, info0)
qreset(**PROVEN_Q); mreset(); _a = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx()); _c8 = qctx(); _c8["pid"] = "pat8"; ci.QUALITY["verify"]["pat8"] = OKCHK; _b = qbuilt(own_msg("n2b", [("99309", "20261105")]), _c8)
check("M0004 (8.3): once per clinician - a second visit of the SAME clinician in the same run carries the 1123F line but no M0004 line (the first is not decided)", MP in _a[0][1] and MP not in _b[0][1] and QP in _b[0][1] and ("prof13", "2026") in ci.MVP["wait"] and ci.MVP["added"] == ["prof13"], (_b[2], ci.MVP["added"]))
_c7 = qctx(); _c7["pid"] = "pat7"; ci.QUALITY["verify"]["pat7"] = OKCHK; _c = qbuilt(qmsg("m1", [("99309", "20261102")]), _c7)
check("M0004 (8.3, 12.3): ... while the OTHER clinician's visit carries its own M0004 line - the mark is the profile the visit is entered under (prof15)", MP in _c[0][1] and _c[1]["mvp_prof"] == "prof15" and _c[1]["prof"] == "prof15" and sorted(ci.MVP["added"]) == ["prof13", "prof15"], _c[1])
qreset(); mreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx())
check("M0004 (8.2): BEFORE the 1123F pilot is proven no M0004 line rides - the pilot visits carry 1123F only", QP in out[1] and MP not in out[1] and "mvp_codes" not in info, pp)
qreset(**PROVEN_Q); mreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261110")]), qctx())
check("M0004 (8.2): a visit whose clinician comes from the per-patient fallback (no raw message of its own) carries 1123F but NO M0004 line", QP in out[1] and MP not in out[1] and info["msg_own"] is False and "mvp_codes" not in info, info)
qreset(**PROVEN_Q); mreset(); out, info, pp = qbuilt(qmsg("m8", [("99309", "20261104")]), qctx())
check("M0004 (8.2): a visit whose own message names a clinician id the profile table does not have (entered under the physician by default) carries NO M0004 line", QP in out[1] and MP not in out[1] and info["prof_default"] is True and info["msg_own"] is True, info)
for _lbl, _kw, _mkw in (("that clinician's M0004 line of the year is billed (done)", {}, {"done": {("prof13", "2026")}}), ("that clinician's M0004 line is not decided yet", {}, {"wait": {("prof13", "2026")}}),
                        ("M0004 is switched off", {}, {"off": "this run: switched off (MVP_CODE=off)"}), ("the quality code is off", {"off": "x"}, {}), ("the quality code is not proven at the current amount", {"confirmed": False}, {})):
    qreset(**dict(PROVEN_Q, **_kw)); mreset(**_mkw); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx())
    check("M0004 (8.2, 8.3, 8.7): no M0004 line - %s" % _lbl, MP not in out[1] and "mvp_codes" not in info, (pp, info))
qreset(**PROVEN_Q); mreset(done={("prof15", "2026"), ("prof13", "2025")}); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx())
check("M0004 (8.3): ... the other clinician's line, or the physician's line of another year, does not count", MP in out[1], pp)
_yrs = set(ci.QUALITY_YEARS); ci.QUALITY_YEARS.add("2027"); qreset(**PROVEN_Q); mreset(); out, info, pp = qbuilt(own_msg("y7", [("99309", "20270104")]), qctx()); ci.QUALITY_YEARS.clear(); ci.QUALITY_YEARS.update(_yrs)
check("M0004 (8.2): a 2027 date of service gets no M0004 line - M0004 is registered for 2026 only (here the 1123F list is made to cover 2027, so only M0004's own year is tested)", QP in out[1] and MP not in out[1] and info["msg_own"] is True, pp)
qreset(**PROVEN_Q); mreset()
check("M0004 (13.2): the decision itself never lets the M0004 line ride at place of service 21, 22 or 23, and says yes elsewhere when everything else is shown",
      [ci.mvp_due(True, "prof13", "2026", p_) for p_ in ("21", "22", "23", "32", "31", "13")] == [False, False, False, True, True, True])
check("M0004 (8.2): the decision itself - the clinician must be known from its own message, a profile must be given, the year must be one M0004 is registered for",
      [ci.mvp_due(o_, p_, y_, "32") for o_, p_, y_ in ((False, "prof13", "2026"), (None, "prof13", "2026"), (True, "", "2026"), (True, None, "2026"), (True, "prof13", "2027"), (True, "prof13", "2025"))] == [False] * 6)
_on = ci.MVP_ON; ci.MVP_ON = False; _x1 = ci.mvp_due(True, "prof13", "2026", "32"); ci.MVP_ON = _on; ci.QUALITY["confirmed"] = False; _x2 = ci.mvp_due(True, "prof13", "2026", "32"); ci.QUALITY["confirmed"] = True
check("M0004: ... M0004 not on = no line; the 1123F pilot not proven = no line; the constants are the owner's", _x1 is False and _x2 is False and ci.MVP_ON is True and ci.MVP_YEARS == {"2026"} and ci.MVP_CODE == "M0004" and ci.MVP_PCODE == "pcode692183" and ci.MVP_LEFT_OFF_MAX == 2)
qreset(**PROVEN_Q); mreset(); ci.QUALITY["off"] = "x"; _x3 = ci.mvp_due(True, "prof13", "2026", "32"); qreset(**PROVEN_Q)
check("M0004 (8.7): ... the decision itself says no while the quality code is OFF, even with the pilot's proof still recorded", _x3 is False)
qreset(**PROVEN_Q); mreset(); out, info, pp = qbuilt(own_msg("hx", [("99232", "20261031")], bld=B["h1"]), qctx())
check("M0004 (13.2): a hospital visit after proof carries neither line - the request is the visit's own", QP not in out[1] and MP not in out[1] and out[1] == out[2] and "mvp_codes" not in info and pp == [("pcode65089", "21")], (pp, info))
qreset(**PROVEN_Q); mreset(); _md = ci.mvp_due; ci.mvp_due = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom")); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx()); ci.mvp_due = _md
check("M0004: a failure in its decision never touches the visit or the 1123F line (no M0004 line, everything else as without it)", QP in out[1] and MP not in out[1] and "mvp_codes" not in info and re.sub(QCHG, "", out[1]) == out[2] and ci.MVP["wait"] == set(), info)
qreset(**PROVEN_Q); mreset(); out, info, pp = qbuilt(qmsg("n2", [("99309", "20261102")]), qctx()); ci.mvp_undo(info)
check("M0004: a visit built with the M0004 line that was not kept frees that clinician's mark", ci.MVP["wait"] == set() and ci.MVP["added"] == [], (ci.MVP["wait"], ci.MVP["added"]))
# 4d.2 the answer's charges (8.5)
LA = ci.lines_in_answer
check("lines_in_answer (8.5): by procedure ids when the answer names them, wherever they stand; one of them missing = None for it",
      LA([("charge1", "pcode65119", "141.00", "32"), ("charge3", MP, "0.00", "32"), ("charge2", QP, "0.00", "32")], 1, "0.00") == (2, 1) and LA([("charge1", "pcode65119", "141.00", "32"), ("charge2", QP, "0.00", "32")], 1, "0.00") == (1, None)
      and LA([("charge1", "pcode65119", "141.00", "32"), ("charge3", MP, "0.00", "32")], 1, "0.00") == (None, 1))
check("lines_in_answer (8.5): no procedure names - the TWO charges at the lines' amount, the first of them the 1123F line (the order sent); one-cent lines too",
      LA([("charge1", "", "141.00", "32"), ("charge2", "", "0.00", "32"), ("charge3", "", "0.00", "32")], 1, "0.00") == (1, 2) and LA([("charge2", "", "0.01", ""), ("charge1", "", "141.00", ""), ("charge3", "", "0.01", "")], 1, "0.01") == (0, 2))
check("lines_in_answer (8.5): no procedure names and no charge at the lines' amount - the LAST two in the order sent when the answer holds two charges more than the message has codes; otherwise nothing",
      LA([("charge1", "", "", ""), ("charge2", "", "", ""), ("charge3", "", "", "")], 1, "0.00") == (1, 2) and LA([("charge1", "", "1.00", ""), ("charge2", "", "1.00", ""), ("charge3", "", "1.00", "")], 1, "0.00") == (1, 2)
      and LA([("charge1", "", "", ""), ("charge2", "", "", "")], 1, "0.00") == (None, None) and LA([("charge1", "", "", ""), ("charge2", "", "", ""), ("charge3", "", "", ""), ("charge4", "", "", "")], 1, "0.00") == (None, None))
check("lines_in_answer (8.5): ONE charge has the lines' amount (one of the two was not stored - which one is not known): nothing is taken for either line",
      LA([("charge1", "", "141.00", ""), ("charge2", "", "0.00", ""), ("charge3", "", "133.00", "")], 2, "0.00") == (None, None) and LA([("charge1", "", "141.00", ""), ("charge2", "", "0.00", ""), ("charge3", "", "1.00", "")], 1, "0.00") == (None, None))
# 4d.3 which line the words of an edit name (the same test in the import, the inspector step and the insurance check)
_NL = [("Pattern 88001: procedure M0004 is not payable", (False, True)), ("pcode692183 not allowed", (False, True)), ("procedure 1123F - line item charge amount is zero", (True, False)), ("M0004 charge amount is zero", (False, True)),
       ("Charge amount is zero for this procedure", (True, True)), ("Line charge of $0.00 is below the minimum", (True, True)), ("1123F and M0004 are not covered", (True, True)), ("edit on charge 7000012", (False, True)), ("edit on charge 7000011", (True, False)),
       ("Relationship of Subscriber to Patient is invalid", (False, False)), ("zero units", (False, False)), ("charge 17000012 is odd", (False, False)), ("", (False, False)), (None, (False, False))]
check("names_lines (11.6): which no-charge line the words of an edit name - by code, AdvancedMD's id or the charge number; zero-amount words name the line whose code is not named (both when neither is)",
      all(ci.names_lines(w_, "charge7000011", "charge7000012") == r_ for w_, r_ in _NL), [(w_, ci.names_lines(w_, "charge7000011", "charge7000012")) for w_, r_ in _NL if ci.names_lines(w_, "charge7000011", "charge7000012") != r_])
# 4d.4 its own ledger (mvp_state), fed directly with made-up registers: the physician's line MA_ and the nurse practitioner's MB_
def mrow(pid, visit, own, qc, mc, prof="prof13", dos="11/16/2026", **kw): return dict({"pid": pid, "visit": visit, "quality_codes": ["1123F"], "quality_charge": qc, "mvp_codes": ["M0004"], "mvp_charge": mc, "mvp_prof": prof, "mvp_dos": dos,
                                                                                    "quality_dos": dos, "dos": dos, "charges": [own, qc, mc], "quality_fee": "0.00", "mvp_fee": "0.00", "cpts": ["99309"]}, **kw)
def mstate(regs, look=True, **kw):
    DETAILS.clear(); ci.mvp_state(regs, look, **kw); return dict(ci.MVP)
def mnext(stamp, created=(), failed=(), **gate): return (RN(stamp), {"created": list(created), "failed": list(failed), "skipped": [], "mvp_gate": dict(ci.mvp_gate(), **gate)})
MA_ = mrow("pat7101", "vst71", "charge711", "charge712", "charge713"); MB_ = mrow("pat7102", "vst72", "charge721", "charge722", "charge723", prof="prof15")
M1 = (RN("20261116T1240Z"), {"created": [MA_, MB_], "failed": [], "skipped": []})
def mworld(**st):      # every charge of MA_ / MB_ is open unless said otherwise
    BILLS.clear(); PROC.clear(); TEXTOF.clear(); PAYS.clear()
    for c_, pc_ in (("711", "pcode65119"), ("712", QP), ("713", MP), ("721", "pcode65119"), ("722", QP), ("723", MP)): chg(c_, st.get("c" + c_, []), pc_)
mworld(); s = mstate([M1], day=D_(11, 20))
check("M0004 ledger (8.3): two clinicians' lines, nothing billed - both wait (no second M0004 line for either); each line and its visit's own charge was read once; the gate says waiting for both",
      s["wait"] == {("prof13", "2026"), ("prof15", "2026")} and s["done"] == set() and DETAILS == ["713", "711", "723", "721"] and s["off"] == "" and {p_: v_["state"] for p_, v_ in s["clinicians"].items()} == {"prof13": "waiting", "prof15": "waiting"}, (s, DETAILS))
mworld(c713=["11/18/2026"]); s = mstate([M1], day=D_(11, 20))
check("M0004 ledger (8.3): the physician's line is BILLED - he is done for the year; the nurse practitioner still waits", s["done"] == {("prof13", "2026")} and s["wait"] == {("prof15", "2026")} and s["billed_lines"] == ["charge713"] and s["clinicians"]["prof13"]["state"] == "billed" and s["clinicians"]["prof13"]["billed"] == "11/18/2026", s)
mworld(c713={"void": "1"}); s = mstate([M1], day=D_(11, 20))
check("M0004 ledger (8.3): a VOID M0004 line - it may ride again: that clinician is neither done nor waiting, and nothing is switched off (a void line is no reason for OFF)", ("prof13", "2026") not in s["done"] and ("prof13", "2026") not in s["wait"] and s["void_lines"] == ["charge713"] and s["off"] == "" and s["clinicians"]["prof13"]["state"] == "not yet", s)
mworld(c711=["11/18/2026"]); s = mstate([M1], day=D_(11, 20))
check("M0004 ledger (13.1d): the visit billed two days ago without its M0004 line - not decided yet (a line can be billed a day after its visit): the clinician still waits, nothing is left off",
      s["left_off_lines"] == [] and ("prof13", "2026") in s["wait"] and any("not decided before 11/21/2026" in n_ for n_ in s["notes"]), s)
s = mstate([M1], day=D_(11, 21))
check("M0004 ledger (13.1d): three days after - LEFT OFF: listed, that clinician gets it once more (neither done nor waiting), and one left-off line does not switch M0004 off",
      s["left_off_lines"] == ["charge713"] and ("prof13", "2026") not in s["wait"] and ("prof13", "2026") not in s["done"] and s["off"] == "" and s["left_off_on"] == {"charge713": {"on": "11/21/2026", "billed": "11/18/2026"}} and s["clinicians"]["prof13"]["state"] == "left off", s)
G21 = mnext("20261121T1240Z"); MA2 = mrow("pat7103", "vst73", "charge731", "charge732", "charge733"); chg("731", ["11/22/2026"], "pcode65119"); chg("733", [], MP); chg("732", [], QP)
s = mstate([M1, G21, (RN("20261122T1240Z"), {"created": [MA2]})], day=D_(11, 26))
check("M0004 ledger (8.3): the physician's second M0004 line is left off too - TWO left-off lines since the last start: M0004 is OFF until William restarts it, the sentence names the visits",
      sorted(s["left_off_lines"]) == ["charge713", "charge733"] and s["off"].startswith("AdvancedMD left the M0004 line off 2 claims since the option code was last started (visits vst71, vst73)") and s["off_until_reset"] == s["off"], s)
mworld(c711=["11/18/2026"]); mstate([M1], day=D_(11, 21)); G21 = mnext("20261121T1240Z"); chg("713", ["11/25/2026"], MP); s = mstate([M1, G21], day=D_(11, 27))
check("M0004 ledger (13.1b): a left-off M0004 line is read again - billed later, it moves to the billed lines: that clinician is done for the year, and the gate's late row says so",
      s["billed_lines"] == ["charge713"] and s["left_off_lines"] == [] and ("prof13", "2026") in s["done"] and s["late_billed"] == {"charge713": "11/27/2026"} and s["late_rows"] == [["prof13", "pat7101", "vst71", "charge713", "11/21/2026", "", "2026"]], s)
chg("713", [], MP); s = mstate([M1, G21], day=D_(12, 19))
check("M0004 ledger (13.1b): ... read again only until 30 days after its visit was billed", "713" not in DETAILS and s["left_off_lines"] == ["charge713"], (s["left_off_lines"], DETAILS))
mworld(c711=["not a date"]); s = mstate([M1], day=D_(11, 18)); G18 = mnext("20261118T1240Z")
check("M0004 ledger (13.1d): a visit listed as billed whose billed date cannot be read - the gate remembers the day the import first saw it billed and counts from that day", s["left_off_lines"] == [] and s["left_off_seen"] == {"charge713": "11/18/2026"} and ("prof13", "2026") in s["wait"], s)
s = mstate([M1, G18], day=D_(11, 20)); s3 = mstate([M1, G18], day=D_(11, 21))
check("M0004 ledger (13.1d): ... two days later still not decided (the first day seen is kept, not moved to each run's day), three days later left off", s["left_off_lines"] == [] and s["left_off_seen"] == {"charge713": "11/18/2026"} and s3["left_off_lines"] == ["charge713"] and s3["left_off_seen"] == {}, (s, s3))
mworld(); TEXTOF["713"] = "99497"; s = mstate([M1], day=D_(11, 20)); TEXTOF.clear()
check("M0004 ledger (13.4): the charge detail names procedure id pcode692183 with another code text - OFF until William restarts it, the sentence says what AdvancedMD stores, the gate records the text",
      s["off"] == "AdvancedMD stores procedure id pcode692183 as 99497, not M0004 - William looks" and s["wrong_code_text"] == "99497" and s["off_until_reset"] == s["off"], s)
SW = mrow("pat7104", "vst74", "charge741", "charge743", "charge742")       # the row recorded the two no-charge lines the other way round (the answer named no procedures)
BILLS.clear(); PROC.clear(); chg("741", [], "pcode65119"); chg("742", [], QP); chg("743", ["11/18/2026"], MP)
s = mstate([(RN("20261116T1240Z"), {"created": [SW]})], day=D_(11, 20))
check("M0004 ledger (8.5): the charge recorded as the M0004 line shows the 1123F procedure - the first read finds the M0004 line among the visit's other charges, corrects the swap (kept in the gate), and its outcome counts",
      s["swaps"] == {"charge742": "charge743"} and s["billed_lines"] == ["charge743"] and ("prof13", "2026") in s["done"] and any("corrected" in n_ for n_ in s["notes"]), s)
s2 = mstate([(RN("20261116T1240Z"), {"created": [SW]}), mnext("20261120T1240Z")], day=D_(11, 21))
check("M0004 ledger (8.5): ... the correction is carried forward: its outcome is not read again (only its payment lines, for Medicare's answer), and the wrong charge never again", s2["swaps"] == {"charge742": "charge743"} and DETAILS == ["743"] and ("prof13", "2026") in s2["done"], (s2, DETAILS))
OW = mrow("pat7105", "vst75", "charge751", "charge752", "charge751"); OW["charges"] = ["charge751", "charge752", "charge753"]      # the row took the visit's OWN charge for the M0004 line
BILLS.clear(); PROC.clear(); chg("751", [], "pcode65119"); chg("752", [], QP); chg("753", [], MP)
s = mstate([(RN("20261116T1240Z"), {"created": [OW]})], day=D_(11, 20))
check("M0004 ledger (8.5): the row took the visit's own charge for the M0004 line - nothing is decided on that charge: the M0004 line is found among the visit's charges and read instead", s["swaps"] == {"charge751": "charge753"} and ("prof13", "2026") in s["wait"] and s["billed_lines"] == [] and s["void_lines"] == [], s)
MREM = lambda code="M0004", charge="charge713", **e: {"removed": {"20261116T1240Z": [("feed_inspector_20261116T1240Z.json", dict({"visit": "vst71", "pid": "pat7101", "charge": charge, "code": code, "fee": "0.00", "why": "Pattern 88001: procedure M0004 is not payable", "void_ok": True, "released": True, "at": "x"}, **e))]}}
mworld(); s = mstate([M1], files=MREM(), day=D_(11, 20))
check("M0004 ledger (11.6): the inspector step took the M0004 line off a held visit that then went through - void and final, NOT read; M0004 is OFF until William restarts it (no second try)",
      s["void_lines"] == ["charge713"] and "713" not in DETAILS and s["off"].startswith("the routine took the M0004 line off held visit vst71 and the visit went through without it - no second try") and s["off_until_reset"] == s["off"], s)
_RM = (RN("20261116T1240Z"), {"created": [MA_]})
s = state([_RM], files=MREM()); s2 = state([_RM], files={"removed": {"20261116T1240Z": MREM()["removed"]["20261116T1240Z"] + MREM(code="1123F", charge="charge712")["removed"]["20261116T1240Z"]}})
check("M0004 (11.6): an M0004 line taken off with released does NOT count against 1123F (no refusal, the amount stays, the patient is not marked refused); taken off WITH the 1123F line, the 1123F entry counts as one refusal",
      s["fee"] == "0.00" and s["refused"] == set() and "charge713" not in s["void_lines"] and s2["fee"] == "0.01" and ("pat7101", "2026") in s2["refused"] and s2["void_lines"] == ["charge712"], (s, s2))
mworld(); s = mstate([M1], files=MREM(released=False), day=D_(11, 20))
check("M0004 ledger (11.6): ... the visit stayed held anyway (not released) - the line is just void: that clinician may get M0004 again, nothing is switched off", s["void_lines"] == ["charge713"] and s["off"] == "" and ("prof13", "2026") not in s["wait"] and ("prof13", "2026") not in s["done"], s)
s = mstate([M1], files=MREM(void_ok=False, released=False), day=D_(11, 20))
check("M0004 ledger (11.6): ... the void failed - the visit is held WITH its M0004 line: OFF until William restarts it", s["off"].startswith("the Claim Inspector holds visit vst71 and the routine could not take its M0004 line off") and s["void_lines"] == [], s)
s = mstate([M1], files=MREM(charge="charge712"), day=D_(11, 20))
check("M0004 ledger (11.6, 8.5): an M0004 entry whose charge the row recorded as its 1123F line (the two were swapped) is still this row's M0004 line - and the swap is kept", s["void_lines"] == ["charge712"] and s["swaps"] == {"charge713": "charge712"} and "no second try" in s["off"], s)
_HELD = lambda why_: {"held": {"71": [("feed_inspector_20261116T1240Z.json", why_, False)]}}
mworld(); s = mstate([M1], files=_HELD("Pattern 88001: procedure M0004 is not payable"), day=D_(11, 20))
check("M0004 ledger (8.6): a Claim Inspector hold whose words name M0004 on a visit that carries it, with no removal recorded (the line could not be taken off) - M0004 OFF until William restarts it",
      s["off"].startswith("the Claim Inspector holds visit vst71, which carries the M0004 line, for words that name it") and "procedure M0004 is not payable" in s["off"], s)
s = mstate([M1], files=_HELD("Pattern 990001: procedure 1123F - line item charge amount is zero"), day=D_(11, 20)); s2 = mstate([M1], files=_HELD("Charge amount is zero for this procedure"), day=D_(11, 20))
check("M0004 ledger (8.6): ... a hold whose words name only the 1123F line is not M0004's business; words about a zero amount that name no code name both lines - M0004 OFF", s["off"] == "" and "which carries the M0004 line" in s2["off"], (s["off"], s2["off"]))
_RP = (RN("20261116T1240Z"), {"created": [MA_], "quality_gate": {"confirmed": True, "fee": "0.00", "proof": {"visit": "vst2", "charge": "charge22"}}})
s = state([_RP], files=_HELD("Pattern 88001: procedure M0004 is not payable")); s2 = state([_RP], files=_HELD("Pattern 990001: procedure 1123F - charge amount is zero")); s3 = state([_RP], files=_HELD("Pattern 88003: M0004 charge amount is zero"))
check("M0004 (8.6): an edit that names only M0004 switches M0004 off, NOT 1123F - after proof the 1123F ledger does not switch off for it (also when its words speak of a zero amount: that amount is M0004's); an edit that names 1123F still does",
      s["off"] == "" and s["confirmed"] is True and s3["off"] == "" and "the Claim Inspector holds visit vst71, which carries the quality line" in s2["off"], (s["off"], s2["off"], s3["off"]))
s = mstate([M1], files=dict(_HELD("Pattern 88001: procedure M0004 is not payable"), **MREM(released=False)), day=D_(11, 20))
check("M0004 ledger (11.6): a hold that names M0004 on a visit whose M0004 line the routine took off is the visit's own business - no OFF; the line is just void", s["off"] == "" and s["void_lines"] == ["charge713"], s)
s = state([_RM], files={"removed": {"20261116T1240Z": MREM(code="1123F", charge="charge713")["removed"]["20261116T1240Z"]}})
check("M0004 (11.3, 8.5): a 1123F entry whose charge the row recorded as its M0004 line (the two were swapped) is that row's 1123F line - void, and one refusal", s["void_lines"] == ["charge712"] and s["fee"] == "0.01" and ("pat7101", "2026") in s["refused"], s)
mworld(c711=["11/18/2026"]); chg("731", ["11/18/2026"], "pcode65119"); chg("733", [], MP); chg("732", [], QP)
_M2 = (RN("20261116T1240Z"), {"created": [MA_, MA2]}); s = mstate([_M2], day=D_(11, 22)); G22 = mnext("20261122T1240Z"); s2 = mstate([_M2, G22], reset=True, day=D_(11, 23))
check("M0004 ledger (8.3, 8.7): two lines left off - OFF; MVP_CODE=reset starts M0004 again and the left-off lines from before the restart no longer count towards a new OFF",
      s["off"].startswith("AdvancedMD left the M0004 line off 2 claims") and s2["off"] == "" and s2["reset"] is True and sorted(s2["left_off_lines"]) == ["charge713", "charge733"], (s["off"], s2["off"]))
s = mstate([M1], files={"check_holds": {"71": [("feed_verify_20261116T1240Z.json", ["insorder not applied on vst71 (the visit carries the quality line charge712 and the M0004 line charge713: resave FAULT)"])]}}, day=D_(11, 20))
check("M0004 ledger (8.6): the insurance check could not set the order of a visit that carries M0004 - OFF until William restarts it", s["off"].startswith("the insurance check could not set the order of visit vst71, which carries the M0004 line"), s)
mworld(); s = mstate([(RN("20261116T1240Z"), {"created": [dict(MA_, mvp_codes=[], mvp_charge="", mvp_refused="Fault: no", mvp_tried="0.00")]})], day=D_(11, 20))
check("M0004 ledger (8.4): a visit refused with M0004 and taken with the 1123F line only - M0004 is OFF until William restarts it (no second try); the sentence names chart, visit and register",
      s["off"] == "AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only - no second try (chart pat7101, visit vst71, feed_import_20261116T1240Z.json)" and s["lines"] == 0, s)
s = mstate([(RN("20261116T1240Z"), {"created": [dict(MA_, mvp_codes=[], mvp_charge="", mvp_not_stored="0.00")]})], day=D_(11, 20))
check("M0004 ledger: a visit stored without its M0004 line - OFF until William restarts it", s["off"].startswith("AdvancedMD stored a visit without its M0004 line - William looks (chart pat7101"), s)
def _FM(info=None, **kw): return dict({"feed_id": "f1", "pid": "pat7101", "empty_visit": "vst79", "info": dict({"quality_tried": "0.00", "mvp_tried": "0.00", "quality_dos": "11/16/2026", "dos": "11/16/2026", "cpts": ["99309"]}, **(info or {})), "err": "x"}, **kw)
s = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM(stored=[["99309", "11/16/2026"]])]})]); s2 = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM(quality_unknown="0.00")]})])
s3 = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM(stored=[["99309", "11/16/2026"]], info={"mvp_form_refused": True})]})]); s4 = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM()]})])
check("M0004 ledger (8.4): a visit that carried M0004 got a fault or an error and nobody knows what AdvancedMD kept (the chart showed part of it, or a call ended in an error) - OFF; when the 1123F-only form was refused too, M0004 is not blamed; an ordinary failed row says nothing",
      s["off"].startswith("AdvancedMD answered a visit that carried M0004 with a fault or an error and nobody knows what it kept of it - William looks (chart pat7101, visit vst79") and s2["off"] == s["off"] and s3["off"] == "" and s4["off"] == "", (s["off"], s2["off"], s3["off"], s4["off"]))
mworld(); TEXTOF["713"] = "99497"; mstate([M1], day=D_(11, 20)); TEXTOF.clear(); GOFF = mnext("20261120T1240Z")
s = mstate([M1, GOFF], day=D_(11, 21))
check("M0004 ledger: its OFF is carried forward by its gate - the next run is still OFF with the same sentence, and reads nothing for it", s["off"] == "AdvancedMD stores procedure id pcode692183 as 99497, not M0004 - William looks" and s["off_until_reset"] == s["off"], s)
s = mstate([M1, GOFF], reset=True, day=D_(11, 21))
check("M0004 ledger (8.7): MVP_CODE=reset with M0004 OFF - started again: the OFF is gone and the restart recorded; a line that exists still counts for its clinician", s["off"] == "" and s["reset"] is True and any("started again" in n_ for n_ in s["notes"]) and ("prof15", "2026") in s["wait"], s)
s = mstate([M1], reset=True, day=D_(11, 21))
check("M0004 ledger (8.7): MVP_CODE=reset with nothing switched off is ignored, loudly", s["reset"] is False and "NOTHING TO RESTART - MVP_CODE=reset was ignored" in s["loud"], s)
s = mstate([M1, GOFF, (RN("20261121T1240Z"), {"created": [], "quality_gate": {"reset": True, "fee": "0.00"}})], day=D_(11, 22))
check("M0004 (8.7): a restart of the 1123F line (QUALITY_CODE=reset, written in the 1123F gate) does not restart a lasting M0004 OFF", s["off"].startswith("AdvancedMD stores procedure id pcode692183 as 99497"), s["off"])
mworld(c713=["11/12/2026"], c723=["11/12/2026"]); PAYS["713"] = [{"amount": "0.00", "carrierfid": "6085", "date": "11/24/2026", "void": "1"}, {"amount": "0.00", "carrierfid": "6404", "date": "11/24/2026", "void": "0"}]
PAYS["723"] = [{"amount": "0.00", "carrierfid": "6085", "date": "11/25/2026", "void": "0"}]; s = mstate([M1], day=D_(11, 30))
check("M0004 ledger (11.6): Medicare's answer per clinician - a void Medicare payment line or another carrier's is no answer (prof13 waits for it), a live Medicare Part B line is (prof15 recorded)",
      s["answer"] == {"prof15": {"charge": "charge723", "visit": "vst72", "date": "11/25/2026", "amount": "0.00", "register": "feed_import_20261116T1240Z.json"}} and s["answer_wait"].get("prof13", {}).get("days") == 18 and "prof15" not in s["answer_wait"]
      and any("Medicare's remittance shows the M0004 line for prof15" in n_ for n_ in s["notes"]), s)
s2 = mstate([M1, mnext("20261130T1240Z")], day=D_(12, 1)); PAYS.clear()
check("M0004 ledger (11.6): ... the answer is carried forward and that clinician's line is not read for it again", s2["answer"].get("prof15", {}).get("charge") == "charge723" and "723" not in DETAILS and "713" in DETAILS, (s2["answer"], DETAILS))
mworld(); s = mstate([M1], look=False, day=D_(11, 20))
check("M0004 ledger: a dry run reads nothing in AdvancedMD - the undecided lines simply wait", DETAILS == [] and s["wait"] == {("prof13", "2026"), ("prof15", "2026")}, (s, DETAILS))
for odd in ([("a", {"created": "x", "mvp_gate": 7})], [("b", None)], [("c", {"created": [{"mvp_codes": "x", "mvp_charge": 5}, 7, {"mvp_codes": ["M0004"], "mvp_charge": "charge9", "mvp_prof": 5, "charges": "abc"}],
                                                                              "mvp_gate": {"reset": "yes", "billed_lines": "x", "swaps": 5, "answer": [1], "off_until_reset": 3}})], []):
    try: ci.mvp_state(odd, look=True); okm = ci.MVP["off"] == "" and json.dumps(ci.mvp_gate()) != ""
    except Exception: okm = False
    check("M0004 ledger: odd registers (%s) are read without an error, never switch M0004 off, and its gate can still be written" % str(odd)[:40], okm, dict(ci.MVP))
BILLS.clear(); PROC.clear(); TEXTOF.clear(); PAYS.clear(); DETAILS.clear(); mreset()
# 4d.5 through main(): the 1123F pilot proven (an earlier register says so), then visits of both clinicians whose own messages name them
for i in range(10, 20): ci.MATCH[NAME("q%d" % i).upper().strip() + "|" + "19400215"] = {"resolved": "pat4%d" % i}
def charts1(): charts0(); CHART.update({"4%d" % i: [("99309", "10/03/2026")] for i in range(10, 20)})
def mvisit(k, day, npi=NPI):      # made-up patient q<k> (chart pat4<k>) whose raw message names its own building and clinician
    fid = "mv-q%d-%s" % (k, day); ci.MSGOF[ci.msg_key(fid, [("99309", day)])] = {(B["n2"], npi, "")}; ci.FACOF[fid] = B["n2"]; ci.FACS[fid] = {B["n2"]}; ci.NPIOF[fid] = npi
    return {"pid": fid, "name": NAME("q%d" % k), "dob": "1940" + "0215", "file": "f", "FT1": [{"cpt": "99309", "dos": day, "dx": "I10", "units": "1"}]}
DEMOG["plans"] = MEDICARE + OTHER; earlier(); wreg("feed_verify_20261101T0001Z.json", {"pat4%d" % i: vrow() for i in range(10, 20)}); clear_regs(); charts1(); BILLS.clear(); PROC.clear(); mreset()
PRV = dict(RUN1, quality_gate=dict(RUN1["quality_gate"], confirmed=True))      # the three pilot lines of 11/02, proven at $0.00
keep(PRV, "20261111T0100Z"); out, rm1 = live([mvisit(4, "20261116"), mvisit(5, "20261116", NP_NPI), mvisit(6, "20261116"), mvisit(7, "20261116", NP_NPI)])
_mr = [r for r in rm1["created"] if r.get("mvp_codes")]; _ql_ = [r for r in rm1["created"] if r.get("quality_codes")]
check("M0004 through main() (8.2, 8.3): after proof four eligible visits of two clinicians - every one carries 1123F, ONE visit of each clinician carries M0004 (the first of each); its row lists the visit's own charge, then 1123F, then M0004",
      len(_ql_) == 4 and sorted(r["mvp_prof"] for r in _mr) == ["prof13", "prof15"] and [r["pid"] for r in _mr] == ["pat404", "pat405"] and all(r["charges"][-1] == r["mvp_charge"] and r["charges"][-2] == r["quality_charge"] and len(r["charges"]) == 3 and r["fees"] == ["1.00"] for r in _mr),
      [(r["pid"], r.get("mvp_prof"), r["charges"]) for r in rm1["created"]])
check("M0004 through main(): what AdvancedMD stored is read back for the visit's own line as before; the M0004 line's place of service is recorded apart (kept as sent)",
      all(r["pos_stored"] == r["pos_lines"] and r["mvp_pos_stored"] == r["mvp_pos"] and r["quality_pos_stored"] == r["quality_pos"] for r in _mr) and "POS NOT KEPT" not in out, [(r.get("pos_stored"), r.get("mvp_pos_stored")) for r in _mr])
check("M0004 through main(): the register's mvp_gate - both clinicians waiting, added in this run, nothing off; the log line says x2 and both clinicians; M0004 lines are not counted as charge lines",
      rm1["mvp_gate"]["added"] == ["prof13", "prof15"] and {p_: v_["state"] for p_, v_ in rm1["mvp_gate"]["clinicians"].items()} == {"prof13": "waiting", "prof15": "waiting"} and rm1["mvp_gate"]["off"] == "" and rm1["mvp_gate"]["off_until_reset"] == ""
      and "QUALITY M0004: on x2 visit(s), prof13 waiting (added now), prof15 waiting (added now)" in out and "'option code M0004 added': 2" in out and "'charge lines': 4" in out, (rm1["mvp_gate"], [l for l in out.splitlines() if "M0004" in l]))
keep(rm1, "20261116T0100Z"); _m4 = [num(r["mvp_charge"]) for r in _mr]
out, rm2 = live([mvisit(8, "20261117"), mvisit(9, "20261117", NP_NPI)])
check("M0004 through main() (8.3): the next run - both clinicians' M0004 lines are not decided (nothing billed): no second M0004 line for either, the 1123F line goes on as usual; each M0004 line was read",
      [r.get("mvp_codes") for r in rm2["created"]] == [None, None] and len([r for r in rm2["created"] if r.get("quality_codes")]) == 2 and all(c_ in DETAILS for c_ in _m4) and "QUALITY M0004: on x0 visit(s), prof13 waiting, prof15 waiting" in out,
      ([r.get("mvp_codes") for r in rm2["created"]], DETAILS, [l for l in out.splitlines() if "M0004" in l]))
keep(rm2, "20261117T0100Z"); BILLS[_m4[0]] = ["11/18/2026"]; out, rm3 = live([mvisit(10, "20261123"), mvisit(11, "20261123", NP_NPI)])
check("M0004 through main(): the physician's M0004 line is billed - he is done for the year (no second line); the nurse practitioner's still waits", [r.get("mvp_codes") for r in rm3["created"]] == [None, None]
      and rm3["mvp_gate"]["clinicians"]["prof13"]["state"] == "billed" and rm3["mvp_gate"]["clinicians"]["prof15"]["state"] == "waiting", rm3["mvp_gate"])
keep(rm3, "20261123T0100Z"); BILLS[_m4[1]] = {"void": "1"}; out, rm4 = live([mvisit(12, "20261124"), mvisit(13, "20261124", NP_NPI)])
check("M0004 through main(): the nurse practitioner's M0004 line is void - her next visit carries a new one; the physician (done) gets none", [(r["pid"], r.get("mvp_prof")) for r in rm4["created"] if r.get("mvp_codes")] == [("pat413", "prof15")], [(r["pid"], r.get("mvp_codes")) for r in rm4["created"]])
for _lbl, _echo, _ok in (("names procedures", {"proccode": True}, "right"), ("lists the 1123F charge first, names no procedure, carries the amounts", {"fees": True, "qfirst": True}, "right"),
                         ("lists every charge in reverse, names no procedure, carries the amounts", {"fees": True, "reverse": True}, "swapped")):
    clear_regs(); keep(PRV, "20261111T0100Z"); BILLS.clear(); mreset(); out, rx = live([mvisit(14, "20261116")], **_echo); r_ = [r for r in rx["created"] if r.get("mvp_codes")]
    _right = bool(r_) and PROC.get(num(r_[0]["mvp_charge"])) == MP and PROC.get(num(r_[0]["quality_charge"])) == QP; _swap = bool(r_) and PROC.get(num(r_[0]["mvp_charge"])) == QP and PROC.get(num(r_[0]["quality_charge"])) == MP
    check("M0004 through main() (8.5): the answer %s - both no-charge lines are found %s; the row lists the visit's own charge first" % (_lbl, "by procedure / amount" if _ok == "right" else "by their amount, the two the other way round (the first read of the M0004 line in a later run corrects it)"),
          len(r_) == 1 and (_right if _ok == "right" else _swap) and PROC.get(num(r_[0]["charges"][0])) == "pcode65119" and r_[0]["fees"] == (["141.00"] if _echo.get("fees") else ["1.00"]), (r_, PROC))
keep(rx, "20261116T0100Z"); out, ry = live([mvisit(15, "20261117")])
check("M0004 through main() (8.5): ... the next run's first read of the M0004 line finds the 1123F procedure on it, takes the visit's other no-charge charge, and keeps the correction", ry["mvp_gate"]["swaps"] == {r_[0]["mvp_charge"]: r_[0]["quality_charge"]}, ry["mvp_gate"])
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); out, rp = live([mvisit(16, "20261116")], reverse=True); r_ = [r for r in rp["created"] if r.get("mvp_codes")]
check("M0004 through main() (8.5): the answer lists every charge in reverse with no procedure and no line amount - the last two of the answer are taken in the order sent (here the visit's own charge is taken for the M0004 line, the true one stands first)",
      len(r_) == 1 and PROC.get(num(r_[0]["quality_charge"])) == QP and PROC.get(num(r_[0]["mvp_charge"])) == "pcode65119", r_)
_true = next((c_ for c_ in r_[0]["charges"] if PROC.get(num(c_)) == MP), None) if r_ else None
keep(rp, "20261116T0100Z"); out, rq2 = live([mvisit(17, "20261117")])
check("M0004 through main() (8.5): ... the next run's first read finds the M0004 line among the visit's charges and keeps the correction - never a decision on the visit's own charge", rq2["mvp_gate"]["swaps"] == {r_[0]["mvp_charge"]: _true}, rq2["mvp_gate"])
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rr = live([mvisit(14, "20261116"), mvisit(15, "20261116")], refuse_mvp=True)
_rr = rr["created"]; _ref = [r for r in _rr if r.get("mvp_refused")]
_with = [b_ for b_ in POSTS if MP in b_]; _q1 = [b_ for b_ in POSTS if "updvisitwithnewcharges" in b_ and QP in b_ and MP not in b_ and _ref and _ref[0]["visit"] in b_]
check("M0004 refused (8.4): AdvancedMD refuses the visit that carries 1123F + M0004 - after a fresh read of the chart the SAME visit goes in with the 1123F line only, which is accepted; nothing failed, both visits are entered",
      len(_rr) == 2 and rr["failed"] == [] and len(_ref) == 1 and _ref[0]["quality_codes"] == ["1123F"] and bool(_ref[0]["quality_charge"]) and _ref[0]["mvp_codes"] == [] and _ref[0]["mvp_tried"] == "0.00" and len(_ref[0]["charges"]) == 2, (_rr, rr["failed"]))
check("M0004 refused (8.4): ... what goes in the second time is the first request with nothing but the M0004 line taken out, and no further M0004 line is tried in that run (the second visit carries 1123F only)",
      len(_with) == 1 and len(_q1) == 1 and re.sub(MCHG, "", _with[0]) == _q1[0] and _rr[1].get("mvp_codes") is None and len([r for r in _rr if r.get("quality_codes")]) == 2, (len(_with), len(_q1)))
check("M0004 refused (8.4): ... M0004 is OFF until William restarts it - no second try (the register's mvp_gate, the log line); the 1123F line is not blamed (no refusal counted, the patient is not marked refused)",
      rr["mvp_gate"]["off_until_reset"].startswith("AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only - no second try (chart pat414") and "OPTION CODE M0004 REFUSED" in out
      and rr["quality_gate"]["refused_charts"] == [] and rr["quality_gate"]["off"] == "" and "off until William restarts it (one run with MVP_CODE=reset)" in out, (rr["mvp_gate"], rr["quality_gate"]))
keep(rr, "20261116T0100Z"); out, rr2 = live([mvisit(16, "20261117", NP_NPI)])
check("M0004 refused (8.4): ... the next run, no switch: still OFF - the other clinician gets no M0004 line either; the 1123F line as usual", [r.get("mvp_codes") for r in rr2["created"]] == [None] and rr2["created"][0].get("quality_codes") == ["1123F"] and rr2["mvp_gate"]["off_until_reset"] == rr["mvp_gate"]["off_until_reset"], rr2["mvp_gate"])
keep(rr2, "20261117T0100Z"); out, rr3 = live([mvisit(17, "20261118", NP_NPI)], menv="reset")
check("M0004 (8.7): MVP_CODE=reset (William's word) - M0004 starts again: the nurse practitioner's visit carries her M0004 line; the restart is recorded",
      [r.get("mvp_prof") for r in rr3["created"]] == ["prof15"] and rr3["mvp_gate"]["reset"] is True and rr3["mvp_gate"]["off_until_reset"] == "" and rr3["mvp_gate"]["reset_after"] == [0, 0], rr3["mvp_gate"])
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rb = live([mvisit(14, "20261116")], refuse_quality=True); _rb = rb["created"]
check("M0004 refused with the 1123F line only too (8.4): the visit goes in without either line, the refusal counts against 1123F (the patient is marked refused); M0004 is NOT switched off",
      len(_rb) == 1 and bool(_rb[0].get("quality_refused")) and _rb[0].get("mvp_form_refused") is True and _rb[0]["mvp_tried"] == "0.00" and len(_rb[0]["charges"]) == 1 and rb["mvp_gate"]["off_until_reset"] == ""
      and rb["quality_gate"]["refused_charts"] == [["pat414", "2026"]] and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 3, (_rb, rb["mvp_gate"]))
keep(rb, "20261116T0100Z"); ci.PARSED[:] = [mvisit(15, "20261117")]; out, dry = run_dry()
check("M0004 refused with the 1123F line only too: the next run - one refusal after proof changes nothing for 1123F, and the clinician's M0004 line can still ride", ci.QUALITY["fee"] == "0.00" and ci.QUALITY["confirmed"] is True and ci.MVP["off_until_reset"] == "" and dry.get("pat415", [{}])[0].get("mvp_codes") == ["M0004"], (ci.QUALITY["fee"], dry))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rpart = live([mvisit(14, "20261116")], refuse_mvp=True, partial=("414", "99309", "11/16/2026"))
check("M0004 refused and the chart then shows part of the visit (8.4): nothing is tried with the 1123F line only - the visit is left for William as before, and M0004 is OFF until restarted",
      len(rpart["failed"]) == 1 and rpart["failed"][0]["stored"] == [["99309", "11/16/2026"]] and rpart["created"] == [] and rpart["mvp_gate"]["off_until_reset"].startswith("AdvancedMD refused a visit that carried M0004 and the chart did not show it free of that visit")
      and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 1, (rpart["failed"], rpart["mvp_gate"]))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rpm = live([mvisit(14, "20261116")], refuse_mvp=True, partial=("414", "M0004", "11/16/2026"))
check("M0004 refused and the chart then shows only an M0004 line of that date: the visit is NOT sent again in any form (it would carry a stray M0004 line) - left for William, M0004 OFF",
      len(rpm["failed"]) == 1 and rpm["failed"][0]["stored"] == [["M0004", "11/16/2026"]] and rpm["created"] == [] and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 1 and rpm["mvp_gate"]["off_until_reset"] != "", (rpm["failed"], rpm["mvp_gate"]))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rt = live([mvisit(14, "20261116")], refuse_mvp=True, plain_raises=True)
check("M0004 refused, and the visit sent with the 1123F line only ends in an error (8.4): nothing is sent again - a failed row that says nobody knows what AdvancedMD kept; the 1123F code and M0004 are both OFF until William has looked",
      len(rt["failed"]) == 1 and rt["failed"][0].get("quality_unknown") == "0.00" and rt["failed"][0]["info"]["mvp_tried"] == "0.00" and rt["created"] == []
      and "nobody knows whether AdvancedMD kept that visit" in rt["quality_gate"]["off_until_reset"] and rt["mvp_gate"]["off_until_reset"].startswith("AdvancedMD refused a visit that carried M0004, and the same visit sent with the 1123F line only ended in an error"), (rt["failed"], rt["mvp_gate"]))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, ru = live([mvisit(14, "20261116")], line_raises=True)
check("M0004: the call that carries both lines ends in an error - nothing is sent again; the failed row remembers both lines were tried; the 1123F code and M0004 are OFF until William has looked",
      len(ru["failed"]) == 1 and ru["failed"][0].get("quality_unknown") == "0.00" and ru["failed"][0]["info"]["mvp_tried"] == "0.00" and ru["failed"][0]["info"]["mvp_codes"] == []
      and ru["mvp_gate"]["off_until_reset"].startswith("a call that carried M0004 ended in an error"), (ru["failed"], ru["mvp_gate"]))
keep({k_: v_ for k_, v_ in ru.items() if k_ != "mvp_gate"}, "20261116T0100Z"); ci.PARSED[:] = [mvisit(15, "20261117")]; out, dry = run_dry()
check("M0004: ... also from the failed row alone (that run cut off before it wrote its gates)", ci.MVP["off_until_reset"].startswith("AdvancedMD answered a visit that carried M0004 with a fault or an error and nobody knows what it kept of it") and not any(v[0].get("mvp_codes") for v in dry.values()), ci.MVP["off_until_reset"])
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rd = live([mvisit(14, "20261116"), mvisit(15, "20261116", NP_NPI)], drop_mvp=True, proccode=True)
check("M0004: AdvancedMD stores the visit and its 1123F line but not the M0004 line - said at once, M0004 OFF until William restarts it (no further M0004 line in that run); the 1123F line counts as stored",
      rd["created"][0].get("mvp_not_stored") == "0.00" and rd["created"][0]["mvp_codes"] == [] and bool(rd["created"][0]["quality_charge"]) and rd["created"][1].get("mvp_codes") is None
      and rd["mvp_gate"]["off_until_reset"].startswith("AdvancedMD stored a visit without its M0004 line") and rd["quality_gate"]["off"] == "", (rd["created"], rd["mvp_gate"]))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
for _val, _expect in (("off", "switched off (MVP_CODE=off)"), ("OFF ", "switched off (MVP_CODE=off)"), ("stop", "MVP_CODE='stop' is not a value the import knows"), ("0", "MVP_CODE='0' is not a value the import knows")):
    out, rs_ = live([mvisit(14, "20261116")], menv=_val)
    check("M0004 switch MVP_CODE=%r: no M0004 line in that run (the 1123F line as usual), and the log says why" % _val, rs_["created"][0].get("quality_codes") == ["1123F"] and rs_["created"][0].get("mvp_codes") is None and _expect in rs_["mvp_gate"]["off"]
          and rs_["mvp_gate"]["off_until_reset"] == "" and _expect in out, (rs_["mvp_gate"]["off"], [l for l in out.splitlines() if "M0004" in l]))
out, rs_ = live([mvisit(14, "20261116")], menv="reset")
check("M0004 switch MVP_CODE=reset with nothing switched off: ignored, loudly - the M0004 line rides as usual", rs_["created"][0].get("mvp_codes") == ["M0004"] and rs_["mvp_gate"]["reset"] is False and "NOTHING TO RESTART - MVP_CODE=reset was ignored" in out, [l for l in out.splitlines() if "M0004" in l])
out, rs_ = live([mvisit(14, "20261116")], env="off")
check("M0004 (8.7): QUALITY_CODE=off stops M0004 too - neither line in that run; M0004 is not switched off for later runs", rs_["created"][0].get("quality_codes") is None and rs_["created"][0].get("mvp_codes") is None and rs_["mvp_gate"]["off_until_reset"] == "" and "the quality code is off" in rs_["mvp_gate"]["off"], rs_["mvp_gate"])
out, rs_ = live([mvisit(14, "20261116")], env="stop")
check("M0004 (8.7): QUALITY_CODE=stop stops M0004 too - and it is the 1123F code that is OFF until restarted, not M0004", rs_["created"][0].get("mvp_codes") is None and "stopped on William's word" in rs_["quality_gate"]["off_until_reset"] and rs_["mvp_gate"]["off_until_reset"] == "", rs_["mvp_gate"])
open(os.path.join(REGDIR, "feed_import_20261101T0000Z.json"), "w").write("{cut off"); out, rs_ = live([mvisit(14, "20261116")]); rmreg("feed_import_20261101T0000Z.json")
check("M0004 (13.5): an import register of this year that cannot be read - no M0004 line (and no 1123F line) in that run; the M0004 state names the file", rs_["created"][0].get("mvp_codes") is None and "feed_import_20261101T0000Z.json" in rs_["mvp_gate"]["off"] and "cannot be read" in rs_["mvp_gate"]["off"], rs_["mvp_gate"]["off"])
out, rf_ = live([mvisit(14, "20261116"), mvisit(15, "20261116")], fail_create=1)
check("M0004: a visit that could not be created frees its clinician's mark - the next visit of that clinician in the run carries the M0004 line", len(rf_["failed"]) == 1 and [r.get("mvp_prof") for r in rf_["created"]] == ["prof13"], (rf_["failed"], rf_["created"]))
_ms = ci.mvp_state; ci.mvp_state = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom")); out, rs_ = live([mvisit(14, "20261116")]); ci.mvp_state = _ms
check("M0004: its state cannot be read - every visit is entered, the 1123F line as usual, no M0004 line, and the register says so", rs_["created"][0].get("quality_codes") == ["1123F"] and rs_["created"][0].get("mvp_codes") is None and "could not be read (RuntimeError)" in rs_["mvp_gate"]["off"], rs_["mvp_gate"])
_mg_ = ci.mvp_gate; ci.mvp_gate = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom")); out, rs_ = live([mvisit(14, "20261116")]); ci.mvp_gate = _mg_
check("M0004: its gate cannot be written - the register is not lost (every visit and line is in it, with a gate that says so) and the run reaches DONE", rs_["created"][0].get("mvp_codes") == ["M0004"] and "could not be written (RuntimeError)" in rs_["mvp_gate"]["off"] and "DONE" in out, rs_["mvp_gate"])
_mlg = ci.mvp_log; ci.mvp_log = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("boom")); out, rs_ = live([mvisit(14, "20261116")]); ci.mvp_log = _mlg
check("M0004: its log line cannot be built - the run still writes its register and reaches DONE", "QUALITY M0004: this line could not be built" in out and "DONE" in out and isinstance(rs_["mvp_gate"].get("clinicians"), dict), out[-300:])
ci.PARSED[:] = [mvisit(14, "20261116"), mvisit(15, "20261116", NP_NPI)]; out, dry = run_dry()
check("M0004 main --dry: the dry run says which visits WOULD carry it (one per clinician) and writes nothing", "QUALITY M0004: would be on x2 visit(s)" in out and sorted(v[0].get("mvp_prof") for v in dry.values() if v[0].get("mvp_codes")) == ["prof13", "prof15"]
      and not os.path.exists(os.path.join(REGDIR, "feed_import_SELFTEST.json")), [l for l in out.splitlines() if "M0004" in l])
clear_regs(); rmreg(EARLIER, "feed_verify_20261101T0001Z.json"); DEMOG["plans"] = ""; BILLS.clear(); PROC.clear(); DETAILS.clear(); charts0(); qreset(); mreset(); ci.PARSED[:] = BASE

# ---- 5. the mirror keeps these helpers: a workspace copy without the rule never overwrites the repository's ------------------------------
mir = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
for helper in ("claimocity_import.py", "claimocity_report.py", "claimocity_inspector.py", "claimocity_ingest.py", "claimocity_retry_dx.py", "working_denials.py", "claimocity_verify.py", "aging_refresh.py"):
    m = re.search(r'"%s":\s*(?:"([^"]+)"|\'([^\']+)\')' % re.escape(helper), mir); m = m and type("M", (), {"group": lambda self, i, _m=m: _m.group(1) or _m.group(2)})()
    check("mirror.py protects %s with a marker that is in the file" % helper, bool(m) and m.group(1) in open(os.path.join(ROOT, "scripts", "helpers", helper)).read(), m.group(1) if m else "no PROTECTED entry")
insp = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read()
check("inspector: a CCM visit at the hospital location is never moved to HCA REHAB / 31", 'all(x not in HOSP for x in c["cpts"]) and not any(x in ("99487", "99489") for x in c["cpts"])' in insp)
check("inspector: a visit the import flagged (pos_err) is never moved to HCA REHAB either; mirror.py's marker for the inspector is a sentence only the current version has - since 11.6 the version that takes BOTH no-charge lines off (11/10/2026)",
      'not any(x in ("99487", "99489") for x in c["cpts"]) and not c.get("pos_err"):' in insp and "is never moved to HCA REHAB either" in insp and '"claimocity_inspector.py": "the step takes BOTH no-charge lines off"' in mir and "the step takes BOTH no-charge lines off" in insp
      and "THIS STEP TAKES THE LINE OFF BY ITSELF" in insp)
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
check("runbook: the feed step copies the helpers and checks the version line before the ingest", "cp -p claimocity_import.py claimocity_report.py claimocity_inspector.py claimocity_verify.py claimocity_ingest.py claimocity_retry_dx.py claimocity_helpers_current.py feed_parse_dft_1028.py /home/claude/unbilled/" in step and step.index("cp -p claimocity_import.py claimocity_report.py claimocity_inspector.py claimocity_verify.py claimocity_ingest.py claimocity_retry_dx.py claimocity_helpers_current.py feed_parse_dft_1028.py /home/claude/unbilled/") < step.index("must print 1") < step.index("python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run drops --live)"))
check("ingest (C2): the feed helpers are made the repository's copies on EVERY run - right after the stamp line, before the 'nothing new' exit and long before step 5 - by the one function it shares with the retry", "_hl, pos_warn = _helpers_current()" in ingest and ingest.index("print(\"stamp %s | %d new file(s)") < ingest.index("_hl, pos_warn = _helpers_current()") < ingest.index('print("nothing new - done")') < ingest.index('cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py")')
      and "_m.make_current(HERE, REPO_HELPERS, POS_RULE)" in ingest and "_has_rule(" not in ingest)
check("ingest: when some helpers could not be made current the result line names them (the words are the shared function's); the runbook says where that line goes", "FEED HELPERS NOT ALL CURRENT" in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_helpers_current.py")).read() and '+ pos_warn))' in ingest
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
check("digest: CCM lines and visits left at 31 are counted and explained", "CCM lines entered as 32: 2 (and 2 kept at 31 by the back end's exception for that month - see pos_why - not held" in line and "nursing visits 31: 3 (1 of them kept at 31 because the chart shows neither pattern" in line, line)
check("digest: ... it says they go out at 31 unless William acts, and names the charts", "not held: they go out at 31 with the next claim run unless William changes them first" in line and "for William, not held - CCM kept at 31 (pos_kind ccm-skilled-month): pat9 11/02/2026 99487+99489" in r.stdout
      and "for William, not held - visits kept at 31, neither pattern shown (pos_kind extra / between): pat9 11/02/2026 99309" in r.stdout, r.stdout[-900:])
r, line = digest(rows + [reg_row(["99487"], "fac34", "31", ["31"], err="boom"), reg_row(["99487", "99309"], "", "31", ["31", "31"])])
check("digest: a visit the rule could not be applied to, and lines from an unknown building, are named", "POS RULE NOT APPLIED on 1 visit(s) - entered at the feed's place of service" in line and "2 CCM / nursing-visit line(s) came from a building the facility table does not know" in line, line)
check("digest: ... with their chart numbers for the top of the report", "TOP OF THE REPORT - rule not applied, for William before the claim run; a routine changes nothing on these visits: pat9 11/02/2026 99487 (boom)" in r.stdout and "TOP OF THE REPORT - building the facility table does not know: pat9 11/02/2026 99487+99309" in r.stdout, r.stdout[-900:])
r, line = digest(rows + [dict(reg_row(["99309"], "fac32", "31", ["31"], ["moved"]))])
check("digest: visits kept at 31 because the previous visit was in another building are counted apart", "nursing visits 31: 3 (1 of them because the previous nursing visit was in another building)" in line, line)
r, line = digest([dict(x, pos_stored=list(x["pos_lines"])) for x in rows])
check("digest: says when AdvancedMD's own answer shows the place of service as sent", "AdvancedMD's own answer shows the place of service as sent on all 6 visit(s) it echoed." in r.stdout, r.stdout[-600:])
r, line = digest([dict(rows[0], pos_stored=["31", "31"])] + rows[1:])
check("digest: says loudly when AdvancedMD stored another place of service", "TOP OF THE REPORT - ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE on 1 of 1 visit(s) read back:" in r.stdout and "sent ['32', '32'] stored ['31', '31']" in r.stdout, r.stdout[-600:])
r, line = digest(rows)
check("digest (W5 d): when the answer did not echo the place of service it says the run reads ONE 32 line back from the chart, citing the runbook paragraph by its name", "the run reads ONE 32 line back from the chart (runbook, 'EVERY RUN THAT ENTERS A 32 LINE')" in r.stdout and "first batch that enters" not in r.stdout, r.stdout[-600:])
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
check("rulebook (M5, NH-3, M12, M13, M15, 13.2): the exception list and 1123F with modifier 8P entered by a person; no 'does no harm'; who is left out; the exact code list; hospital visits not coded; M0004 now added by the back end (section 8)",
      "registers/quality_exceptions.json" in _qrb and "takes 1123F with modifier 8P - both entered by a person, not by the back end" in _qrb and "does no harm" not in _qrb and "takes no code" not in _qrb
      and "WHO IS LEFT OUT" in _qrb and "Railroad Medicare" in _qrb and "a first visit ever" in _qrb and "99304-99310, 99341, 99342, 99344, 99345, 99347-99350, 99221-99223, 99231-99236, 99202-99205 and 99212-99215" in _qrb
      and "HOSPITAL VISITS ARE NOT CODED IN THIS VERSION" in _qrb and "THE BACK END ADDS M0004" in _qrb and "added by the next step" not in _qrb and "ONE diagnosis" in _qrb and "nurse practitioner" in _qrb)
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
check("lessons: one dated line records the owner's decision on held visits and the rule version (since step 4 a later line follows it: William's initial-visit rule)", sum(1 for l_ in _sl if l_.startswith("- 2026-11-10T1435Z | chat (quality code 1123F, version 2, step 2) | RULE |") and "just deal with it" in l_ and "2026-11-10.6" in l_) == 1)
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
    def post(body, timeout=0):      # fault: "with" = refuses an echo that carries charge11, "with12" = one that carries charge12, "either" = one that carries either, "always" = every echo. An accepted echo voids every charge it leaves out (as AdvancedMD does)
        VQ["sent"].append(body)
        if VQ["fault"] == "always" or (VQ["fault"] == "with" and 'id="charge11"' in body) or (VQ["fault"] == "with12" and 'id="charge12"' in body) or (VQ["fault"] == "either" and re.search(r'id="charge1[12]"', body)):
            return "<r><Fault><description>%s</description></Fault></r>" % VQ.get("text", "Charge amount is zero")
        sent_ = set(re.findall(r'<charge id="charge(\d+)"', body)); VQ["void"] |= {c_ for c_ in VQ["proc"] if c_ not in sent_}
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
def _is_detail(cid):      # charge1011 = IS["qproc"] (the 1123F line), charge1012 = IS["mproc"] (the M0004 line), any other = the visit's own 99309
    cid = re.sub(r"\D", "", str(cid)); pc, fee = IS["qproc"] if cid == "1011" else IS.get("mproc", (MP, "0.00")) if cid == "1012" else ("pcode65119", "141.00")
    return '<r><patient id="pat1"/><visit id="vst101" episode="e1"/><charge id="charge%s" proccode="%s" fee="%s" pos="32" void="%s"/></r>' % (cid, pc, fee, "1" if cid in IS["void"] else "0")
def _is_vc(cid):
    r_ = ET.fromstring(_is_detail("1010")); return r_.find(".//visit"), r_.find(".//patient"), [ET.fromstring(_is_detail(c_)).find(".//charge") for c_ in IS.get("ids", ("1010", "1011")) if c_ not in IS["void"]]
def _is_post(body, timeout=0):
    if "getclaiminspectorcharges" in body:
        return "<r>%s</r>" % "".join('<visit id="vst%s" patientid="pat1">%s</visit>' % (v_, "".join('<error id="%s" number="%s" name="%s"/>' % (e_["id"], e_["number"], e_["text"]) for e_ in es)) for v_, es in IS["listed"].items() if es)
    if "bypassclaimedits" in body: IS["bypassed"].append(re.findall(r'claimedit id="([^"]+)"', body)); return "<r/>"
    if "updvisitwithnewcharges" in body:
        IS["resaved"].append(body)
        if IS["voided"]: IS["listed"]["101"] = list(IS["after"])      # once the line is gone and the visit re-saved, AdvancedMD lists what `after` says
    return "<r/>"
def _is_void(pid, cid):      # void_ok False: every void fails; void_fails = one charge number whose void fails
    IS["voided"].append((pid, cid))
    if not IS["void_ok"] or (IS.get("void_fails") and re.sub(r"\D", "", str(cid)) == IS["void_fails"]): return False, "<Fault><description>the charge cannot be voided</description></Fault>"
    IS["void"].add(re.sub(r"\D", "", str(cid))); return True, "ok"
IS_STAND = {"amd": {"login_cached": lambda *a: None, "msg": lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s">%s</ppmdmsg>' % (action, children), "post": _is_post},
            "resave": {"detail": _is_detail, "visit_charges": _is_vc, "CHG_FIELDS": ["fee", "pos"], "_extins_xml": lambda vis, h: ""}, "txh": {"fetch": lambda pid: ET.Element("r")},
            "dx_primary_fix": {"plan": lambda codes, pc: ("ok", codes), "save_visit_dx": lambda cid, d: ("ok", None), "I10_DCODE": "dcode1"}, "void_tx": {"void_charge": _is_void}}
E_DATA = {"id": "e1", "number": "77002", "text": "Pattern 77002: Claim line requires review before submission"}; E_NAME = {"id": "e2", "number": "88001", "text": "Pattern 88001: Charge amount is zero for procedure 1123F"}
E_ADVQ = {"id": "e3", "number": "35790", "text": "Pattern 35790: procedure 1123F line has a zero charge amount"}; E_ADV = {"id": "e4", "number": "35790", "text": "Pattern 35790: add-on code reminder"}
E_ZERO = {"id": "e5", "number": "35790", "text": "Pattern 35790: Charge amount is zero on a line"}
def is_run(errors, after=(), void_ok=True, proven=False, row=None, qproc=("pcode65441", "0.00"), qvoid=False, mproc=(MP, "0.00"), ids=("1010", "1011"), void_fails=None):
    IS.clear(); IS.update(listed={"101": list(errors)}, after=list(after), void_ok=void_ok, voided=[], resaved=[], bypassed=[], void=({"1011"} if qvoid else set()), qproc=qproc, mproc=mproc, ids=ids, void_fails=void_fails)
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
# ---- 6b. the option code M0004 in the other helpers and the words (8.6, 11.6) ------------------------------------------------------------------------------------
o_, e_, res = vd_run([dict(_vrow, charges=["charge10", "charge11", "charge12"], mvp_codes=["M0004"], mvp_charge="charge12")], {"1": {"dod": _DAY1}})
check("M0004 (8.6): a visit dated after the date of death that carries the 1123F and the M0004 line is voided WHOLE - all three charges", not e_ and sorted(c for _n, c in VD["voided"]) == ["charge10", "charge11", "charge12"] and res and res[0]["result"] == "VOIDED", (e_, res, VD["voided"]))
# the digest's own block for M0004 (claimocity_report.py over made-up registers; it loads no AdvancedMD module)
def mdig(rows, mgate, qgate=None, prev_m=None, insp_=None, ver_=None, stamp="20261111T0100Z"):
    pf = os.path.join(rep_dir, "registers", "feed_import_20261111T0000Z.json"); inf = os.path.join(rep_dir, "registers", "feed_inspector_%s.json" % stamp); vf = os.path.join(rep_dir, "feed_verify_%s.json" % stamp); cf = os.path.join(rep_dir, "registers", "feed_import_%s.json" % stamp)
    for f_, o2_ in ((pf, {"created": [], "quality_gate": dict(G0), "mvp_gate": prev_m} if prev_m is not None else None), (inf, insp_), (vf, ver_)):
        if o2_ is None:
            if os.path.exists(f_): os.remove(f_)
        else: json.dump(o2_, open(f_, "w"))
    json.dump({"created": rows, "skipped": [], "failed": [], "quality_gate": qgate or dict(G0, confirmed=True, proof={"visit": "vst5", "billed": "11/11/2026"}, pilot_cap=None), "mvp_gate": mgate}, open(cf, "w"))
    try:
        r_ = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")], cwd=rep_dir, env=dict(os.environ, FEED_STAMP=stamp), capture_output=True, text=True); return r_, r_.stdout
    finally:
        for f_ in (pf, inf, vf, cf):
            if os.path.exists(f_): os.remove(f_)
_MG0 = {"code": "M0004", "on": True, "off": "", "off_until_reset": "", "reset": False, "reset_after": None, "added": [], "clinicians": {"prof13": {"state": "not yet", "year": "2026"}, "prof15": {"state": "not yet", "year": "2026"}},
        "billed_lines": [], "void_lines": [], "left_off_lines": [], "billed_on": {}, "left_off_on": {}, "left_off_seen": {}, "late_billed": {}, "late_rows": [], "swaps": {}, "wrong_code_text": "", "answer": {}, "answer_wait": {}, "notes": []}
_mrow = dict(qrow, mvp_codes=["M0004"], mvp_charge="charge78", mvp_prof="prof13", mvp_fee="0.00", charges=["charge1", "charge77", "charge78"])
_MW = dict(_MG0, added=["prof13"], clinicians={"prof13": {"state": "waiting", "year": "2026", "visit": "vst1", "charge": "charge78"}, "prof15": {"state": "not yet", "year": "2026"}})
r, o = mdig([_mrow], _MW, prev_m=dict(_MG0))
check("digest (8.6): the option code has its own line - on how many visits, per clinician billed / waiting / not yet; the visit that carries it is named; M0004 lines are not counted as charge lines",
      "Option code M0004 (Quality Care for Patients with Neurological Conditions" in o and "on 1 visit(s) in this batch; prof13 (the physician): waiting; prof15 (the nurse practitioner): not yet; it rides with the next eligible visit of a clinician who has none." in o
      and "M0004 carried by: pat9 vst1 charge78 (prof13)" in o and "1 visits / 1 charge lines created" in o and not any("M0004" in l_ for l_ in _TOP(o)), o[-1500:] + r.stderr[-300:])
_MOFF = dict(_MG0, off="AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only - no second try (chart pat9, visit vst1, feed_import_20261111T0100Z.json)"); _MOFF["off_until_reset"] = _MOFF["off"]
r, o = mdig([dict(qrow, mvp_codes=[], mvp_refused="Fault: no", mvp_tried="0.00")], _MOFF, prev_m=dict(_MG0)); r2_, o2 = mdig([qrow], _MOFF, prev_m=dict(_MOFF))
check("digest (8.4, 8.6): a refused visit with M0004 - at the top: the visit named, entered with the 1123F line only, M0004 OFF until William restarts it; and the OFF itself at the top in the run it began, with MVP_CODE=reset",
      any("AdvancedMD refused 1 visit(s) that carried M0004; each was entered with the 1123F line only: pat9 vst1 (Fault: no)" in l_ for l_ in _TOP(o)) and any("the option code M0004 is OFF until William restarts it: AdvancedMD refused a visit" in l_ and "MVP_CODE=reset" in l_ for l_ in _TOP(o))
      and "OFF until William restarts it (one run with MVP_CODE=reset" in o, _TOP(o))
check("digest (8.6): ... the same M0004 OFF in the next batch is ONE plain line, not the top", not any("M0004" in l_ for l_ in _TOP(o2)) and "the option code M0004 is still OFF (since an earlier run)" in o2, _TOP(o2))
r, o = mdig([qrow], dict(_MG0, off="this run: switched off (MVP_CODE=off)"), prev_m=dict(_MG0))
check("digest (8.7): William's own MVP_CODE=off is a plain line", not any("M0004" in l_ for l_ in _TOP(o)) and "M0004 switched off for this run by William's MVP_CODE=off" in o, o[-600:])
r, o = mdig([qrow], dict(_MG0, off="this run: MVP_CODE='stop' is not a value the import knows (off, reset) - no M0004 line added"), prev_m=dict(_MG0))
check("digest (8.7): an MVP_CODE value the import does not know is at the top, named", any("the option code M0004 is off in this run: this run: MVP_CODE='stop' is not a value the import knows" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = mdig([qrow], dict(_MG0, notes=["NOTHING TO RESTART - MVP_CODE=reset was ignored (M0004 is not switched off; take the switch out of the routine)"]), prev_m=dict(_MG0))
check("digest (8.7): an MVP_CODE=reset that had nothing to restart is at the top", any("NOTHING TO RESTART - MVP_CODE=reset was ignored" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = mdig([dict(qrow, mvp_codes=[], mvp_charge="", mvp_not_stored="0.00")], dict(_MG0, off="x", off_until_reset="x"), prev_m=dict(_MG0, off="x", off_until_reset="x"))
check("digest: a visit stored without its M0004 line is at the top", any("AdvancedMD stored 1 visit(s) WITHOUT the M0004 line that was sent with it" in l_ for l_ in _TOP(o)), _TOP(o))
_MRE = lambda **e: dict({"visit": "1", "pid": "pat9", "charge": "charge78", "code": "M0004", "fee": "0.00", "why": "Pattern 88001: procedure M0004 is not payable", "void_ok": True, "released": True, "at": "x"}, **e)
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE()]))
check("digest (11.6): the M0004 line taken off a held visit that went through - at the top: M0004 OFF until restarted, no second try, it does not count against 1123F; the 1123F block does not report it as its own",
      any("the routine took the M0004 line charge78 off held visit vst1 (pat9; the hold: Pattern 88001: procedure M0004 is not payable) and the visit went through without it: M0004 is OFF until William restarts it (no second try); this does not count against the 1123F line." in l_ for l_ in _TOP(o))
      and not any("took the quality line" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(released=False)])); r2_, o2 = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(void_ok=False, released=False, note="the void failed: Fault")]))
check("digest (11.6): ... the visit still held - at the top, its clinician may get M0004 again; a void that failed - at the top, the visit is held WITH that line, William looks",
      any("but the visit is still held for its own reason" in l_ and "its clinician may get M0004 again" in l_ for l_ in _TOP(o)) and any("the routine could not take the M0004 line off held visit vst1 (pat9: the void failed: Fault)" in l_ for l_ in _TOP(o2)), (_TOP(o), _TOP(o2)))
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), ver_={"pat9": {"decision": "RELEASE", "visits": ["vst1"], "lead": {"code": "FLO02"}, "hold": [], "quality_removed": [_MRE(visit="vst1", why="Fault: charge amount is zero")]}})
check("digest (11.6): an M0004 line the insurance check took off is reported the same way", any("the routine took the M0004 line charge78 off held visit vst1" in l_ for l_ in _TOP(o)), _TOP(o))
_MB = dict(_MG0, clinicians={"prof13": {"state": "billed", "year": "2026", "visit": "vst1", "charge": "charge78", "billed": "11/12/2026"}, "prof15": {"state": "billed", "year": "2026", "visit": "vst2", "charge": "charge88", "billed": "11/13/2026"}},
           answer={"prof13": {"charge": "charge78", "visit": "vst1", "date": "11/25/2026", "amount": "0.00", "register": "x"}})
r, o = mdig([qrow], _MB, prev_m=dict(_MB))
check("digest (11.6): Medicare's answer for M0004 per clinician - shown for prof13, 'not yet' for prof15; a plain line, not the top, that claims no more than the posted line shows",
      "Medicare's remittance shows the M0004 line for prof13 (visit vst1, $0.00 on 11/25/2026)" in o and "not yet for prof15 (its line billed 11/13/2026)" in o and "whether the measure is met shows only in the feedback on the Medicare quality-program site" in o and not any("M0004" in l_ for l_ in _TOP(o)), o[-900:])
_MDEC = dict(_MG0, clinicians={"prof13": {"state": "billed", "year": "2026"}, "prof15": {"state": "not yet", "year": "2026"}}); _MDEC2 = dict(_MDEC, clinicians={"prof13": {"state": "billed", "year": "2026"}, "prof15": {"state": "waiting", "year": "2026"}})
r, o = mdig([qrow], _MDEC, prev_m=dict(_MDEC), stamp="20261201T0100Z"); r2_, o2 = mdig([qrow], _MDEC, prev_m=dict(_MDEC), stamp="20261130T0100Z"); r3_, o3 = mdig([qrow], _MDEC2, prev_m=dict(_MDEC2), stamp="20261215T0100Z")
check("digest (8.6): from December 1 a clinician with no M0004 line billed or waiting is at the top every run - the year ends December 31; not in November; not for a clinician whose line is billed or waiting",
      any("prof15 (the nurse practitioner) has no M0004 line billed or waiting for 2026 - the year ends December 31" in l_ for l_ in _TOP(o)) and not any("prof13" in l_ for l_ in _TOP(o)) and not any("December 31" in l_ for l_ in _TOP(o2)) and not any("December 31" in l_ for l_ in _TOP(o3)), (_TOP(o), _TOP(o2), _TOP(o3)))
r, o = mdig([qrow], dict(_MG0, left_off_lines=["charge78"], late_rows=[["prof15", "pat9", "vst2", "charge88", "11/20/2026", "vst4", "2026"]]), prev_m=dict(_MG0))
check("digest (13.1 for M0004): M0004 lines read as left off - one plain line (listed for William, no routine voids them, that clinician gets it once more); one billed later - its own plain line",
      "1 M0004 line(s) were read as left off their claims" in o and "charge78 - listed for William; no routine voids them. That clinician gets M0004 once more" in o
      and "an M0004 line read as left off on 11/20/2026 was billed later: prof15 counts as done for 2026; prof15 carries two billed M0004 lines (the later one on vst4); nothing to do." in o and not any("M0004" in l_ for l_ in _TOP(o)), o[-900:])
r, o = mdig([rows[4]], _MG0, qgate=dict(G0), prev_m=dict(_MG0))
check("digest: no M0004 line when the quality code is not proven and nothing happened to M0004", "Option code M0004" not in o and r.returncode == 0, o[-400:])
r, o = mdig([rows[4]], "odd"); r2_, o2 = mdig([dict(_mrow, mvp_codes="x", mvp_charge=None)], {"clinicians": 5, "notes": 3, "answer": [1], "left_off_lines": "x", "late_rows": 7, "off": None})
check("digest: odd M0004 values never stop the report", r.returncode == 0 and r2_.returncode == 0 and "could not be built" not in o + o2, (o[-300:], o2[-300:], r2_.stderr[-300:]))
# 11.6: the Claim Inspector step with the M0004 line beside the 1123F line (run INSIDE this process with stand-ins); after proof (M0004 rides only then)
MROW = dict(QROW, charges=["charge1010", "charge1011", "charge1012"], mvp_codes=["M0004"], mvp_charge="charge1012", mvp_fee="0.00", mvp_prof="prof13"); M3 = ("1010", "1011", "1012")
E_MN = {"id": "e6", "number": "88002", "text": "Pattern 88002: procedure M0004 is not payable"}; E_QN = {"id": "e7", "number": "88001", "text": "Pattern 88001: procedure 1123F - line item charge amount is zero"}
E_Z2 = {"id": "e8", "number": "77003", "text": "Pattern 77003: Charge amount is zero for this procedure"}; E_ADVM = {"id": "e9", "number": "35790", "text": "Pattern 35790: procedure M0004 add-on reminder"}
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3)
check("inspector (11.6): an edit that names ONLY M0004 - only the M0004 line is taken off (one void, one entry with code M0004); the 1123F line stays; released",
      _ie == "" and IS["voided"] == [("pat1", "1012")] and len(_ir["quality_removed"]) == 1 and _ir["quality_removed"][0]["code"] == "M0004" and _ir["quality_removed"][0]["charge"] == "charge1012" and _ir["quality_removed"][0]["released"] is True and _ir["held"] == [], (_ie, _ir, IS["voided"]))
_ir, _io, _ie = is_run([E_QN], proven=True, row=MROW, ids=M3)
check("inspector (11.6): an edit that names ONLY 1123F (with its zero amount) - only the 1123F line is taken off; the M0004 line stays", _ie == "" and IS["voided"] == [("pat1", "1011")] and [e_["code"] for e_ in _ir["quality_removed"]] == ["1123F"], (_ie, _ir, IS["voided"]))
_ir, _io, _ie = is_run([E_Z2], proven=True, row=MROW, ids=M3)
check("inspector (11.6): an edit about a zero amount that names neither code - BOTH lines are taken off (two voids, two entries), the visit re-saved once on its own charge",
      _ie == "" and IS["voided"] == [("pat1", "1011"), ("pat1", "1012")] and sorted(e_["code"] for e_ in _ir["quality_removed"]) == ["1123F", "M0004"] and all(e_["released"] is True and e_["void_ok"] is True for e_ in _ir["quality_removed"])
      and len(IS["resaved"]) == 1 and 'id="charge1010"' in IS["resaved"][0] and "charge1011" not in IS["resaved"][0] and "charge1012" not in IS["resaved"][0], (_ie, _ir, IS["voided"]))
_ir, _io, _ie = is_run([E_MN, E_QN], proven=True, row=MROW, ids=M3)
check("inspector (11.6): edits that name both lines - both are taken off", _ie == "" and IS["voided"] == [("pat1", "1011"), ("pat1", "1012")], (_ie, IS["voided"]))
_ir, _io, _ie = is_run([E_DATA], proven=True, row=MROW, ids=M3)
check("inspector (11.6): after proof an edit that names neither line - nothing is voided; held as before, the row says it still carries both lines", _ie == "" and IS["voided"] == [] and _ir["quality_removed"] == [] and _ir["held"][0].get("quality") is True and _ir["held"][0].get("mvp") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_DATA], proven=False, row=MROW, ids=M3)
check("inspector (11.6): before proof any hold takes the lines off - an edit that names neither: BOTH", _ie == "" and IS["voided"] == [("pat1", "1011"), ("pat1", "1012")] and _ir["held"] == [], (_ie, _ir))
_ir, _io, _ie = is_run([E_ADVM], proven=True, row=MROW, ids=M3)
check("inspector (8.6): an ADVISORY whose words name M0004 is never bypassed on a visit that carries it - the M0004 line is taken off instead", _ie == "" and IS["bypassed"] == [] and IS["voided"] == [("pat1", "1012")] and _ir["bypassed"] == [], (_ie, _ir, IS["bypassed"]))
_ir, _io, _ie = is_run([E_MN], proven=True, row=dict(MROW, quality_charge="charge1012", mvp_charge="charge1011"), ids=M3)
check("inspector (11.6, 8.5): the import recorded the two lines the other way round - each is known by its OWN procedure: the M0004 line (charge1012) is the one taken off, and its entry says so", _ie == "" and IS["voided"] == [("pat1", "1012")] and _ir["quality_removed"][0]["code"] == "M0004" and _ir["quality_removed"][0]["charge"] == "charge1012", (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3, mproc=("pcode65119", "141.00"))
check("inspector (11.6): a charge recorded as the M0004 line that shows another procedure and a real amount is NEVER voided: held with its lines, the entry says why", _ie == "" and IS["voided"] == [] and _ir["quality_removed"][0]["void_ok"] is False and "not voided" in _ir["quality_removed"][0]["note"] and _ir["held"][0].get("mvp") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3, mproc=("pcode65119", "0.00"))
check("inspector (11.6): ... also at $0.00 - a charge recorded as the M0004 line is voided only when its own detail shows the M0004 procedure", _ie == "" and IS["voided"] == [] and _ir["quality_removed"][0]["void_ok"] is False, (_ie, _ir))
_ir, _io, _ie = is_run([E_Z2], proven=True, row=MROW, ids=M3, mproc=("pcode65119", "0.00"))
check("inspector (11.6): both lines to come off, and one of them cannot be shown live - NOTHING is voided (not even the line that could be): held with both lines", _ie == "" and IS["voided"] == [] and IS["resaved"] == []
      and [(e_["code"], e_["void_ok"]) for e_ in _ir["quality_removed"]] == [("1123F", False), ("M0004", False)] and _ir["held"][0].get("quality") is True and _ir["held"][0].get("mvp") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_Z2], proven=True, row=MROW, ids=M3, void_fails="1011")
check("inspector (11.6): the first void fails - nothing else is tried (the M0004 line is not voided, no re-save): held WITH both lines, both entries void_ok false (the second says it was not tried)",
      _ie == "" and IS["voided"] == [("pat1", "1011")] and IS["resaved"] == [] and [(e_["code"], e_["void_ok"]) for e_ in _ir["quality_removed"]] == [("1123F", False), ("M0004", False)] and "not tried" in _ir["quality_removed"][1]["note"]
      and _ir["held"][0].get("quality") is True and _ir["held"][0].get("mvp") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3, void_ok=False)
check("inspector (11.6): the held row says names_mvp when the words name the M0004 line", _ie == "" and _ir["held"][0].get("names_mvp") is True and _ir["held"][0].get("mvp") is True and "names_line" not in _ir["held"][0], (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], after=[E_DATA], proven=True, row=MROW, ids=M3)
check("inspector (11.6): the visit is still listed after the M0004 line is gone - held for its own reason; the row says it still carries the 1123F line (not M0004); the entry says released: false",
      _ie == "" and _ir["held"][0].get("quality") is True and "mvp" not in _ir["held"][0] and _ir["quality_removed"][0]["released"] is False, (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], after=[E_ADVQ], proven=True, row=MROW, ids=M3)
check("inspector (11.6, section 7): after ONLY the M0004 line is taken off, an advisory whose words name the 1123F line still on the visit is NOT bypassed - held, the row says its words name that line",
      _ie == "" and IS["bypassed"] == [] and len(_ir["held"]) == 1 and _ir["held"][0].get("quality") is True and _ir["held"][0].get("names_line") is True and _ir["quality_removed"][0]["released"] is False, (_ie, _ir, IS["bypassed"]))
_ir, _io, _ie = is_run([E_QN], after=[E_ADVM], proven=True, row=MROW, ids=M3)
check("inspector (11.6, 8.6): ... and after ONLY the 1123F line is taken off, an advisory whose words name the M0004 line still on the visit is NOT bypassed - held, the row says so",
      _ie == "" and IS["bypassed"] == [] and len(_ir["held"]) == 1 and _ir["held"][0].get("mvp") is True and _ir["held"][0].get("names_mvp") is True and "quality" not in _ir["held"][0] and _ir["quality_removed"][0]["released"] is False, (_ie, _ir, IS["bypassed"]))
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3); json.dump(_ir, open(os.path.join(REGDIR, "feed_inspector_T3.json"), "w")); _F3 = ci.quality_files("T4"); rmreg("feed_inspector_T3.json")
check("inspector -> import (11.6): the M0004 entry the inspector step writes is what the import reads (quality_files: removed, with its code)", [(e_[1]["code"], e_[1]["charge"]) for e_ in (_F3["removed"].get("T3") or [])] == [("M0004", "charge1012")], _F3["removed"])
_ins_ns.update(MVP_CODE="M0004", MVP_PCODE="pcode692183")
check("inspector and import: the same test for which no-charge line the words name (names_lines, every phrase both ways)", all(_ins_ns["names_lines"](w_, "charge7000011", "charge7000012") == ci.names_lines(w_, "charge7000011", "charge7000012") for w_, _r in _NL))
# 11.6: the insurance check with the M0004 line beside the 1123F line (fast_set_insorder, run here with stand-ins)
_mvq = {"visit": "vst1", "pid": "pat1", "charges": ["charge10", "charge11", "charge12"], "quality_charge": "charge11", "quality_codes": ["1123F"], "quality_fee": "0.00", "mvp_charge": "charge12", "mvp_codes": ["M0004"], "mvp_fee": "0.00"}
_P3 = {"10": ("pcode65119", "141.00"), "11": ("pcode65441", "0.00"), "12": (MP, "0.00")}; _P2 = dict(VQ["proc"])
VQ.update(order="1,2", void=set(), sent=[], fault="either", text="Charge amount is zero", proc=_P3); _rm = []; okm1, mm1 = _ns2["fast_set_insorder"](_mvq, "2", _rm)
check("insurance check (11.6): the echo with both no-charge lines is refused with words that name neither code - sent once more without BOTH: accepted, both void, two removal entries (with their codes)",
      okm1 is True and len(VQ["sent"]) == 2 and "charge11" not in VQ["sent"][1] and "charge12" not in VQ["sent"][1] and 'id="charge10"' in VQ["sent"][1] and VQ["void"] == {"11", "12"}
      and sorted((e_["code"], e_["charge"], e_["released"]) for e_ in _rm) == [("1123F", "charge11", True), ("M0004", "charge12", True)], (okm1, mm1, _rm))
VQ.update(order="1,2", void=set(), sent=[], fault="with12", text="procedure M0004 is not payable"); _rm = []; okm2, mm2 = _ns2["fast_set_insorder"](_mvq, "2", _rm)
check("insurance check (11.6): ... words that name only M0004 - sent once more without the M0004 line only; the 1123F line stays", okm2 is True and "charge11" in VQ["sent"][1] and "charge12" not in VQ["sent"][1] and VQ["void"] == {"12"} and [(e_["code"], e_["charge"]) for e_ in _rm] == [("M0004", "charge12")], (okm2, mm2, _rm))
VQ.update(order="1,2", void=set(), sent=[], fault="with", text="procedure 1123F - charge amount is zero"); _rm = []; okm3, mm3 = _ns2["fast_set_insorder"](_mvq, "2", _rm)
check("insurance check (11.6): ... words that name only 1123F - without the 1123F line only; the M0004 line stays", okm3 is True and "charge12" in VQ["sent"][1] and "charge11" not in VQ["sent"][1] and VQ["void"] == {"11"} and [e_["code"] for e_ in _rm] == ["1123F"], (okm3, mm3, _rm))
VQ.update(order="1,2", void=set(), sent=[], fault="always", text="procedure M0004 is not payable"); _rm = []; okm4, mm4 = _ns2["fast_set_insorder"](_mvq, "2", _rm)
check("insurance check (11.6): ... refused again without it - held as before (the line is not the cause), nothing removed", okm4 is False and "a fault again" in mm4 and _rm == [] and len(VQ["sent"]) == 2 and VQ["void"] == set(), (okm4, mm4))
VQ.update(order="1,2", void={"12"}, sent=[], fault=None); _rm = []; okm5, mm5 = _ns2["fast_set_insorder"](_mvq, "2", _rm)
check("insurance check (8.6): a VOID M0004 line never holds the visit - the order is set with the live charges only", okm5 is True and len(VQ["sent"]) == 1 and "charge12" not in VQ["sent"][0] and 'id="charge11"' in VQ["sent"][0], (okm5, mm5))
VQ.update(order="1,2", void=set(), sent=[], fault="always", text="Charge amount is zero"); _rm = []; okm6, mm6 = _ns2["fast_set_insorder"](dict(_mvq, mvp_charge="charge10"), "2", _rm)
check("insurance check (11.6): a row whose M0004 charge names the visit's OWN charge (141.00, another procedure) - the own charge is in every echo; only the real no-charge line is left out", okm6 is False and all('id="charge10"' in s_ for s_ in VQ["sent"]) and len(VQ["sent"]) == 2 and "charge11" not in VQ["sent"][1], (okm6, mm6, VQ["sent"]))
_vns = {"re": re}; exec(_vsrc[_vsrc.index("def names_lines("):], _vns)
check("insurance check and import: the same test for which no-charge line the fault's words name (names_lines, every phrase)", all(_vns["names_lines"](w_, "charge7000011", "charge7000012") == ci.names_lines(w_, "charge7000011", "charge7000012") for w_, _r in _NL))
_vr, _vo, _ve = vf_run(_mvq, "either")
check("insurance check step (11.6): both lines refused, taken out, the echo accepted - RELEASE; the chart's entry records two removals (with their codes) for the import and the fixes say which lines",
      _ve == "" and _vr and _vr["decision"] == "RELEASE" and sorted(e_["code"] for e_ in _vr.get("quality_removed") or []) == ["1123F", "M0004"] and any("the no-charge line(s) 1123F charge11, M0004 charge12 were taken off" in f_ for f_ in _vr["fixes"]), (_ve, _vr))
_vr, _vo, _ve = vf_run(_mvq, "always")
check("insurance check step (8.6): refused with and without the lines - HOLD, and the hold words name both no-charge lines ('insorder not applied' - the words the import switches the codes off on)",
      _ve == "" and _vr and _vr["decision"] == "HOLD" and any(h_.startswith("insorder not applied on vst1 (the visit carries the quality line charge11 and the M0004 line charge12: resave FAULT") for h_ in _vr["hold"]), (_ve, _vr))
VQ.update(proc=_P2, text="Charge amount is zero")
# the words (8, 11.6): the owner's words, the whole rule, the switches; the look-up; the mirror markers
check("rulebook (section 8): the owner's words for M0004 (in the procedure list as pcode692183 'QUAL CARE NEUROLOGIC CND MVP', \"use it\") and the whole rule in plain words - when it rides, its ledger, refusals, held visits, Medicare's answer, December, the switches",
      all(x_ in _qrb for x_ in ('William 11/10/2026, about M0004 - it is in AdvancedMD\'s procedure list as procedure id pcode692183, "QUAL CARE NEUROLOGIC CND MVP": "use it".', "THE BACK END ADDS M0004: ONE no-charge M0004 line per clinician per calendar year",
          "only once the 1123F pilot is proven", "never on a hospital visit", "a second left-off line switches M0004 off", "taken that way, M0004 is OFF - no second try", "does not count against 1123F unless the 1123F line was taken off with it",
          "Medicare's own answer is read per clinician", "the year ends December 31", "MVP_CODE=reset", "MVP_CODE=off", "a restart of 1123F does not restart it")), [x_ for x_ in ("THE BACK END ADDS M0004", "MVP_CODE=reset") if x_ not in _qrb])
check("runbook (section 8): the M0004 paragraph with the owner's words, the switches (off in front of both commands, reset on the ingest only), the December line, and the QUALITY M0004 grep - in the section and in step (f)",
      all(x_ in _qrun.replace("\n", " ") for x_ in ('THE OPTION CODE M0004 - William 11/10/2026: M0004 is in AdvancedMD\'s procedure list (procedure id pcode692183, "QUAL CARE NEUROLOGIC CND MVP") and "use it".', "ONE no-charge M0004 line per clinician per year",
          "`MVP_CODE=off` in front of both commands", "`MVP_CODE=reset` (on the ingest command only)", "the year ends December 31", "grep -h '^QUALITY M0004' logs/claimocity_<stamp>_*.log")) and "grep -h '^QUALITY M0004'" in step[:step.index("## Place of service")]
      and "this version adds 1123F only" not in step)
check("captured calls (section 7, 13.4): M0004 = pcode692183 is the id the feed import uses for its M0004 line, and what is read for that line", "the feed import uses this id for its no-charge M0004 line" in _cc and '`<proccode id="pcode692183" code="M0004"/>`' in _cc and ci.MVP_PCODE == "pcode692183")
check("mirror.py (8.6, 11.6): the inspector's and the insurance check's markers are sentences only the version that knows the M0004 line has", '"claimocity_inspector.py": "the step takes BOTH no-charge lines off"' in mir and '"claimocity_verify.py": "sent once more without BOTH lines"' in mir
      and "sent once more without BOTH lines" in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py")).read())

# ---- 6c. round 6, step 4 (11/10/2026): the feed helpers on every run (C2, W1), the rulebook's merge, reason 58 on the board, the words ---------------
# C2 / W1: the one function the ingest and the retry share (claimocity_helpers_current.make_current) - pure: files in two folders, nothing else
HC_PATH = os.path.join(ROOT, "scripts", "helpers", "claimocity_helpers_current.py"); _hcsrc = open(HC_PATH).read()
check("C2 / W1: the shared helper loads no module that talks to AdvancedMD (os and shutil only)", loads(_hcsrc) == {"os", "shutil"}, loads(_hcsrc))
_hsp = importlib.util.spec_from_file_location("claimocity_helpers_current_t", HC_PATH); HC = importlib.util.module_from_spec(_hsp); _hsp.loader.exec_module(HC)
HC_FILES = {f_: "# %s - the repository's copy\n" % f_ for f_ in HC.FEED_HELPERS}; HC_FILES["claimocity_helpers_current.py"] = _hcsrc
for f_ in HC.RULE_HELPERS: HC_FILES[f_] += ver + "\n"
for f_, m_ in HC.VERSION_LINES.items(): HC_FILES[f_] += m_ + "\n"
HC_OLD = "# an old copy without this rule's version line\n"
def hc_dirs(ws_over=None, repo_drop=(), no_repo=False):
    """(workspace, clone) folders: the clone holds every feed helper; the workspace the same, except ws_over {name: text, or None = missing}."""
    w_ = tempfile.mkdtemp(prefix="posrule_hcw_", dir=tmp); r_ = tempfile.mkdtemp(prefix="posrule_hcr_", dir=tmp)
    for f_, t_ in HC_FILES.items():
        if not no_repo and f_ not in repo_drop: open(os.path.join(r_, f_), "w").write(t_)
        t2 = (ws_over or {}).get(f_, t_)
        if t2 is not None: open(os.path.join(w_, f_), "w").write(t2)
    return w_, (os.path.join(r_, "nowhere") if no_repo else r_)
_same = lambda w_, f_: open(os.path.join(w_, f_)).read() == HC_FILES[f_]
_w, _r = hc_dirs({"claimocity_import.py": HC_OLD}); _l, _wn = HC.make_current(_w, _r, ver)
check("W1 (exact input, helper state): every current helper but an OLD claimocity_import.py in the workspace, the current one in the clone - replaced from the clone before anything runs, said on the console, and nothing to warn about",
      _same(_w, "claimocity_import.py") and _wn == "" and _l == ["FEED HELPERS: claimocity_import.py differed from the repository copy - replaced by it before anything ran"], (_l, _wn))
_w, _r = hc_dirs({"claimocity_report.py": "# report helper of 2075dba\n", "claimocity_inspector.py": "# inspector helper of 2075dba\n"}); _l, _wn = HC.make_current(_w, _r, ver)
check("C2 (exact input G6): a CURRENT import helper with the older report and inspector helpers and a complete clone - both are replaced from the clone on this run (not only when the import helper is old), no warning",
      _same(_w, "claimocity_report.py") and _same(_w, "claimocity_inspector.py") and _wn == "" and "claimocity_report.py, claimocity_inspector.py differed" in _l[0], (_l, _wn))
_w, _r = hc_dirs({"claimocity_report.py": "# report helper of 519062b\n", "claimocity_inspector.py": "# inspector helper of 519062b\n"}, no_repo=True); _l, _wn = HC.make_current(_w, _r, ver)
check("C2 (exact input G7): the same without a clone - nothing can be replaced, and the RESULT warning names both helpers by their missing version lines (the import helper is current: no place-of-service warning)",
      _wn == " | FEED HELPERS NOT ALL CURRENT: claimocity_report.py, claimocity_inspector.py have no version line of this rule and no repository copy was found - this run's digest, insurance check or inspector step may be an older version", _wn)
_w, _r = hc_dirs({"claimocity_import.py": HC_OLD, "claimocity_inspector.py": "# inspector helper of 2075dba\n"}, repo_drop=("claimocity_inspector.py",))
_l1, _w1 = HC.make_current(_w, _r, ver); _l2, _w2 = HC.make_current(_w, _r, ver)
check("C2 (exact input G3 / G4): a clone without claimocity_inspector.py - run 1 replaces the old import helper and names the older inspector; the NEXT run names it again (before, the next run said nothing)",
      _same(_w, "claimocity_import.py") and "FEED HELPERS NOT ALL CURRENT: claimocity_inspector.py has no version line of this rule - " in _w1 and _w2 == _w1 and "PLACE OF SERVICE RULE NOT CURRENT" not in _w2, (_w1, _w2))
open(os.path.join(_r, "claimocity_inspector.py"), "w").write(HC_FILES["claimocity_inspector.py"]); _l3, _w3 = HC.make_current(_w, _r, ver)
check("C2: ... and once the clone holds it, that run replaces it and the warning is gone", _same(_w, "claimocity_inspector.py") and _w3 == "" and "claimocity_inspector.py differed" in _l3[0], (_l3, _w3))
_w, _r = hc_dirs({"claimocity_import.py": None}, no_repo=True); _l, _wn = HC.make_current(_w, _r, ver)
check("W5 (h): no import helper here and no clone - the warning says 'missing, an old copy or an earlier version' and who checks what (for William; a routine changes nothing)",
      _wn.startswith(" | PLACE OF SERVICE RULE NOT CURRENT: claimocity_import.py here is missing, an old copy or an earlier version of the rule and no repository copy was found - for William to check: the place of service") and "a routine changes nothing" in _wn, _wn)
_w, _r = hc_dirs({}); open(os.path.join(_r, "claimocity_import.py"), "w").write("# the clone of an EARLIER rule\n"); open(os.path.join(_r, "claimocity_report.py"), "w").write("# an earlier report\n")
_l, _wn = HC.make_current(_w, _r, ver)
check("a clone of an EARLIER rule (its import helper lacks this version line) never replaces newer workspace copies; they carry their version lines, so nothing is said", _same(_w, "claimocity_report.py") and _same(_w, "claimocity_import.py") and (_l, _wn) == ([], ""), (_l, _wn))
_w, _r = hc_dirs({"claimocity_import.py": HC_OLD, "claimocity_verify.py": "# older\n"}); _c2 = HC.shutil.copy2
HC.shutil.copy2 = lambda a_, b_: (_ for _ in ()).throw(OSError("read-only")) if a_.endswith("claimocity_import.py") else _c2(a_, b_)
try: _l, _wn = HC.make_current(_w, _r, ver)
finally: HC.shutil.copy2 = _c2
check("a helper that cannot be copied is named: the import helper as PLACE OF SERVICE RULE NOT CURRENT ... could not be replaced (OSError); the others that could be copied are replaced",
      "PLACE OF SERVICE RULE NOT CURRENT: claimocity_import.py here is missing, an old copy or an earlier version of the rule and could not be replaced (OSError)" in _wn and _same(_w, "claimocity_verify.py") and "FEED HELPERS NOT ALL CURRENT" not in _wn, (_l, _wn))
_pm = {f_: (m_.group(1) or m_.group(2)) for f_ in HC.VERSION_LINES for m_ in [re.search(r'"%s":\s*(?:"([^"]+)"|\'([^\']+)\')' % re.escape(f_), mir)] if m_}
check("the shared helper's version lines are mirror.py's PROTECTED markers, word for word (so they cannot drift apart), and the drivers pass their own POS_RULE line",
      _pm == HC.VERSION_LINES and HC.RULE_HELPERS == ("claimocity_import.py", "claimocity_ingest.py", "claimocity_retry_dx.py") and set(HC.FEED_HELPERS) == {"claimocity_import.py", "claimocity_report.py", "claimocity_inspector.py", "claimocity_verify.py", "claimocity_ingest.py", "claimocity_retry_dx.py", "feed_parse_dft_1028.py", "claimocity_helpers_current.py"}, (_pm, HC.VERSION_LINES))
# the two drivers themselves, run INSIDE this process over a sandbox workspace and clone: their WS and REPO_HELPERS lines are pointed there, and every
# program they would start (parse, dx, import, verify, inspector, report, recon) is answered by a stand-in that starts nothing
def driver_run(name, w_, r_, argv, on_step):
    src = open(os.path.join(ROOT, "scripts", "helpers", name)).read()
    src = src.replace('WS = "/home/claude/unbilled"', "WS = %r" % w_, 1).replace('REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"', "REPO_HELPERS = %r" % r_, 1)
    _live = [ln_ for ln_ in src.split("\n") if ("/home/claude/unbilled" in ln_ or "/home/claude/effinger-billing-backend" in ln_) and not ln_.lstrip().startswith("#")]
    if _live: raise RuntimeError("the sandbox copy still names a live folder outside a comment - not run: %r" % _live[:2])
    calls_ = []; sub_ = types.ModuleType("subprocess"); sub_.STDOUT = -2; sub_.PIPE = -1
    def _run(cmd, **k):
        calls_.append([os.path.basename(str(x_)) for x_ in cmd]); txt_ = on_step(cmd) or "DONE {}"
        if hasattr(k.get("stdout"), "write"): k["stdout"].write(txt_ + "\n")
        return types.SimpleNamespace(returncode=0, stdout=txt_ if k.get("capture_output") else "", stderr="")
    sub_.run = _run
    old_sub = sys.modules.get("subprocess"); old_cwd = os.getcwd(); old_argv = sys.argv[:]; old_env = dict(os.environ); out_ = io.StringIO(); err_ = ""
    try:
        for k_ in ("FEED_STAMP", "FEED_HL7_DIR", "FEED_DX_CACHE", "FEED_CHART_PREFIX", "QUALITY_CODE", "MVP_CODE"): os.environ.pop(k_, None)      # a routine's environment, not this test's
        sys.modules["subprocess"] = sub_; sys.argv = [os.path.join(w_, name)] + list(argv)
        with contextlib.redirect_stdout(out_):
            try: exec(compile(src, os.path.join(w_, name), "exec"), {"__name__": "__main__", "__file__": os.path.join(w_, name)})
            except SystemExit: pass
            except Exception as e: err_ = "%s: %s" % (type(e).__name__, e)
    finally: sys.modules["subprocess"] = old_sub; os.chdir(old_cwd); sys.argv = old_argv; os.environ.clear(); os.environ.update(old_env)
    return out_.getvalue(), calls_, err_
# W1's exact input: workspace = current helpers except an old claimocity_import.py, clone = current; two earlier batches whose visits waited on code M5117
_w, _r = hc_dirs({"claimocity_import.py": HC_OLD}); os.makedirs(os.path.join(_w, "registers")); _seen_import = []
for _st, _rows in (("20261101T1240Z", [("X2", "99232", "20261031", B["h1"], "20261030", NPI)]), ("20261103T1244Z", [("X2", "99309", "20261102", B["n1"], "", NP_NPI), ("X4", "99487", "20261031", B["n1"], "", NPI)])):
    json.dump({"created": [], "failed": [], "skipped": [{"feed_id": f_, "pid": "pat9102" if f_ == "X2" else "pat9104", "why": "no usable dx for %s" % c_} for f_, c_, *_x in _rows]}, open(os.path.join(_w, "registers", "feed_import_%s.json" % _st), "w"))
    json.dump([{"pid": f_, "name": NAME(f_), "dob": DOBK, "file": "a", "FT1": [{"cpt": c_, "dos": d_, "dx": "M5117", "units": "1"}]} for f_, c_, d_, *_x in _rows], open(os.path.join(_w, "feed_parsed_%s.json" % _st), "w"))
    os.makedirs(os.path.join(_w, "hl7", _st)); open(os.path.join(_w, "hl7", _st, "a.hl7"), "w").write("".join(hl7(f_, b_, a_, [(c_, d_)], n_) for f_, c_, d_, b_, a_, n_ in _rows))
json.dump({"M5117": "dcode77"}, open(os.path.join(_w, "dx_cache_feed.json"), "w")); json.dump({"X2": "pat9102", "X4": "pat9104"}, open(os.path.join(_w, "registers", "claimocity_patient_map.json"), "w"))
_o, _calls, _e = driver_run("claimocity_retry_dx.py", _w, _r, ("--live", "--no-stedi", "--stamp", "2026-11-10T1400Z"),
                           lambda cmd: _seen_import.append(open(os.path.join(_w, "claimocity_import.py")).read()) if str(cmd[1]).endswith("claimocity_import.py") else None)
check("W1 (exact input, the retry driver itself): with the clone beside it, the retry replaces the old import helper BEFORE its import step starts it - the import step ran the clone's copy - and its RESULT line carries no warning",
      _e == "" and _seen_import == [HC_FILES["claimocity_import.py"]] and "RESULT retry 20261110T1400ZR" in _o and "NOT CURRENT" not in _o and [c_[1] for c_ in _calls] == ["claimocity_dx.py", "claimocity_import.py", "claimocity_verify.py", "claimocity_inspector.py", "claimocity_report.py", "claimocity_recon.py"], (_e, _o[-500:], _calls))
_w2, _r2 = hc_dirs({"claimocity_import.py": HC_OLD}, no_repo=True); shutil_ = __import__("shutil")
for _it in ("registers", "hl7", "feed_parsed_20261101T1240Z.json", "feed_parsed_20261103T1244Z.json", "dx_cache_feed.json"):
    (shutil_.copytree if os.path.isdir(os.path.join(_w, _it)) else shutil_.copy)(os.path.join(_w, _it), os.path.join(_w2, _it))
for _f in os.listdir(os.path.join(_w2, "registers")):
    if "R.json" in _f or not _f.startswith(("feed_import_20261101", "feed_import_20261103", "claimocity_patient_map")): os.remove(os.path.join(_w2, "registers", _f))
_o, _calls, _e = driver_run("claimocity_retry_dx.py", _w2, _r2, ("--live", "--no-stedi", "--stamp", "2026-11-10T1400Z"), lambda cmd: None)
check("W1: without a clone the retry still enters the visits (never a hold) and its RESULT line ends with the place-of-service warning, naming who checks what",
      _e == "" and "claimocity_import.py" in [c_[1] for c_ in _calls] and next((l_ for l_ in _o.splitlines() if l_.startswith("RESULT retry")), "").endswith("for William to check: the place of service of every nursing-building line this run entered, and the clinician and building of every visit whose patient has another message in the batch (a routine changes nothing on these visits)"), _o[-400:])
# C2's exact input for the ingest driver: current import helper, report and inspector of 2075dba, complete clone; a batch of invented messages
_w, _r = hc_dirs({"claimocity_report.py": "# report helper of 2075dba\n", "claimocity_inspector.py": "# inspector helper of 2075dba\n"})
os.makedirs(os.path.join(_w, "inbox", "claimocity")); open(os.path.join(_w, "inbox", "claimocity", "20261110a.hl7"), "w").write(hl7("FD4", WO, "", [("99308", "20261105")], NP_NPI) + hl7("FD4", B["h1"], "", [("99308", "20261105")], NPI) + hl7("FG7", "ZZ Other Hospital", "20261028", [("99232", "20261030")], NPI))
os.makedirs(os.path.join(_w, "registers")); json.dump({"FD4": "pat704", "FG7": "pat707"}, open(os.path.join(_w, "registers", "claimocity_patient_map.json"), "w")); _at = {}
def _ingest_step(cmd):
    b_ = os.path.basename(str(cmd[2] if str(cmd[1]) == "-I" else cmd[1]))
    if b_ == "feed_parse_dft_1028.py": json.dump([{"pid": p_, "name": NAME(p_), "dob": DOBK, "file": "20261110", "FT1": [{"cpt": c_, "dos": d_, "dx": "I10", "units": "1"}]} for p_, c_, d_ in (("FD4", "99308", "20261105"), ("FD4", "99308", "20261105"), ("FG7", "99232", "20261030"))], open(os.path.join(_w, str(cmd[-1])), "w"))
    if b_ in ("claimocity_report.py", "claimocity_inspector.py", "claimocity_import.py"): _at[b_] = open(os.path.join(_w, b_)).read()
_o, _calls, _e = driver_run("claimocity_ingest.py", _w, _r, ("--hl7-dir", "inbox/claimocity", "--stamp", "2026-11-10T1239Z", "--live", "--skip-verify"), _ingest_step)
check("C2 (exact input, the ingest driver itself): a current import helper with the older report and inspector helpers and a complete clone - both are replaced before the parse step, so the inspector and report steps run the clone's copies; the RESULT line carries no warning",
      _e == "" and _at.get("claimocity_inspector.py") == HC_FILES["claimocity_inspector.py"] and _at.get("claimocity_report.py") == HC_FILES["claimocity_report.py"] and _at.get("claimocity_import.py") == HC_FILES["claimocity_import.py"]
      and "RESULT stamp 20261110T1239Z: files 1, messages 3" in _o and "NOT ALL CURRENT" not in _o and _o.index("FEED HELPERS: claimocity_report.py, claimocity_inspector.py differed") < _o.index("[parse]"), (_e, _o[-600:]))
_w, _r = hc_dirs({"claimocity_report.py": "# older\n"}); os.makedirs(os.path.join(_w, "inbox", "claimocity")); os.makedirs(os.path.join(_w, "registers"))
_o, _calls, _e = driver_run("claimocity_ingest.py", _w, _r, ("--hl7-dir", "inbox/claimocity", "--stamp", "2026-11-10T1500Z"), lambda cmd: None)
check("C2 / second ops review: on a quiet day (nothing new) the ingest still makes the helpers current before it stops - so the retry of the same routine runs current ones", _e == "" and "nothing new - done" in _o and _same(_w, "claimocity_report.py") and _calls == [], (_e, _o[-300:]))
for _drv in ("claimocity_ingest.py", "claimocity_retry_dx.py"):
    _ds = open(os.path.join(ROOT, "scripts", "helpers", _drv)).read()
    check("%s: the version line stays in the driver (mirror.py's marker), the shared function comes from the copy here or the clone's, and the RESULT line ends with what it could not make current" % _drv,
          ver in _ds and "_m.make_current(HERE, REPO_HELPERS, POS_RULE)" in _ds and '"claimocity_helpers_current.py"), os.path.join(REPO_HELPERS, "claimocity_helpers_current.py"))' in _ds and "+ pos_warn)" in _ds)
check("mirror.py protects the shared helper with a sentence only its current version has", '"claimocity_helpers_current.py": "compared byte for byte with the clone\'s copy"' in mir and "compared byte for byte with the clone's copy" in _hcsrc)
# the rulebook's merge (second ops-and-text reviewer): a bullet rewritten in place REPLACES its old copy instead of coming back beside it
_rmp = os.path.join(ROOT, "tools", "mirror", "rules_merge.py"); _rms = open(_rmp).read()
check("the rulebook's merge driver loads nothing that talks to AdvancedMD (sys and subprocess, for git's own union merge)", loads(_rms) == {"sys", "subprocess"}, loads(_rms))
_rsp = importlib.util.spec_from_file_location("rules_merge_t", _rmp); RMG = importlib.util.module_from_spec(_rsp); _rsp.loader.exec_module(RMG)
_HEAD = "- (11/10/2026, William in chat, STANDING for the charge feed and every billing task) PLACE OF SERVICE IN THE NURSING BUILDINGS (Brynwood, Aspire, Centre Pointe, Westminster Oaks-Bertrand, Oakes Southwood). "
_OLD = _HEAD + "(7) ... a returned line is resubmitted at 31; boards/working_denials.py classes reason 58 as FIX."
_NEW = _HEAD + "(7) ... never resent unchanged; both copies of the denial table class reason 58 as REVIEW."
_INV = "- (11/10/2026, INVENTED for this test) A NEW RULE APPENDED BY ANOTHER SESSION."
_base = "# ehpa rules\n\n- (9/7/2026) an older rule.\n" + _OLD + "\n"
_union = "# ehpa rules\n\n- (9/7/2026) an older rule.\n" + _OLD + "\n" + _INV + "\n" + _NEW + "\n"      # what git's union merge gives (the reviewer's run; build4/out/merge_e2e.json with real git)
_t, _tw = RMG.one_bullet(_union, _base)
check("second reviewers (ops-and-text, exact input): a branch appended one invented rule while this change rewrote the LAST bullet in place - after the union merge ONE place-of-service bullet stands, the new one, and the appended rule is kept",
      _t.count("PLACE OF SERVICE IN THE NURSING BUILDINGS") == 1 and _NEW in _t and _OLD not in _t and _INV in _t and _tw == [], _t)
_t2, _tw2 = RMG.one_bullet("# ehpa rules\n" + _NEW + "\n" + _NEW.replace("REVIEW.", "REVIEW (another session's words).") + "\n", _base)
check("... two DIFFERENT rewrites of the same bullet are never guessed: both stay and the rule is reported (the driver then exits 1 - git stops the merge for a person); the same words twice are one",
      _tw2 == ["PLACE OF SERVICE IN THE NURSING BUILDINGS (Brynwood"] and _t2.count("PLACE OF SERVICE") == 2 and RMG.one_bullet(_NEW + "\n" + _NEW + "\n", _base) == (_NEW + "\n", []))
check("... a merge in which nobody rewrote a bullet is left exactly as git's union made it", RMG.one_bullet(_base + _INV + "\n", _base) == (_base + _INV + "\n", []))
_rules = open(os.path.join(ROOT, "practices", "ehpa", "rules.md")).read()
check("... the driver knows the four rewritten rules (place of service, clinician and building, the quality code with M0004, the initial nursing-facility visit), and each heading stands exactly once in the rulebook",
      len(RMG.REPLACED) == 4 and all(sum(1 for ln_ in _rules.split("\n") if RMG.bullet_of(ln_) == k_) == 1 for k_ in RMG.REPLACED), [(k_, sum(1 for ln_ in _rules.split("\n") if RMG.bullet_of(ln_) == k_)) for k_ in RMG.REPLACED])
_msp = importlib.util.spec_from_file_location("mirror_t", os.path.join(ROOT, "tools", "mirror", "mirror.py")); MIRT = importlib.util.module_from_spec(_msp); _msp.loader.exec_module(MIRT)
_gd = tempfile.mkdtemp(prefix="posrule_gitdir_", dir=tmp); _gcmds = []
MIRT.sh = lambda cmd, check=True, **kw: (_gcmds.append(cmd), types.SimpleNamespace(stdout=_gd + "\n", stderr="", returncode=0))[1]      # git answers with this folder; nothing is started
MIRT.union_rules(); _att1 = open(os.path.join(_gd, "info", "attributes")).read(); MIRT.union_rules(); _att2 = open(os.path.join(_gd, "info", "attributes")).read()
check("mirror.py registers the driver: the union lines stay, the driver's line is the LAST line for rules.md (the later line wins), git's config names rules_merge.py with %O %A %B, and a second call changes nothing",
      [l_ for l_ in _att1.splitlines() if l_.startswith("practices/ehpa/rules.md ")] == ["practices/ehpa/rules.md merge=union", "practices/ehpa/rules.md merge=ehpa-rules"] and _att1 == _att2
      and any("merge.ehpa-rules.driver" in c_ and "rules_merge.py %O %A %B" in c_ for c_ in _gcmds) and "docs/SHARED_LESSONS.md merge=union" in _att1, (_att1, _gcmds[-2:]))
_asp = importlib.util.spec_from_file_location("apply_bundle_t", os.path.join(ROOT, "tools", "mirror", "apply_bundle.py")); ABT = importlib.util.module_from_spec(_asp); _asp.loader.exec_module(ABT)
_gd2 = tempfile.mkdtemp(prefix="posrule_gitdir_", dir=tmp); _acmds = []
ABT.sh = lambda *a, **k: (_acmds.append(list(a)), (0, _gd2 if a[1:3] == ("rev-parse", "--git-dir") else ROOT if a[1:3] == ("rev-parse", "--show-toplevel") else ""))[1]
ABT.union_rules(); _att3 = open(os.path.join(_gd2, "info", "attributes")).read()
check("apply_bundle.py (the routine's GitHub inbox) registers the same driver from the clone's own tools/mirror", _att3.splitlines()[-1] == "practices/ehpa/rules.md merge=ehpa-rules" and any(c_[1:3] == ["config", "merge.ehpa-rules.driver"] and c_[3].endswith("rules_merge.py %O %A %B") for c_ in _acmds), (_att3, _acmds[-2:]))
# reason 58 leads the visit on the Working Denials board (the challenge reviewer's exact input), both copies of the table
_DROWS = [{"pid": p_, "visitid": v_, "patient": "ZZTEST " + v_, "carrier": "MEDICARE", "dos": d_, "cpt": c_, "billed": a_, "carc": k_, "group": "CO", "reason": "", "check": "c1", "amt": a_, "rarc": r_}
          for p_, v_, d_, c_, a_, k_, r_ in (("9001", "v1", "2026-11-02", "99309", 141, "CO58", []), ("9002", "v2", "2026-10-31", "99487", 206, "CO58", []), ("9002", "v2", "2026-10-31", "99489", 109, "CO16", ["M77"]),
                                             ("9003", "v3", "2026-11-02", "99309", 60, "CO45", []), ("9003", "v3", "2026-11-02", "99309", 81, "CO58", []), ("9004", "v4", "2026-11-02", "99309", 141, "CO4", []), ("9004", "v4", "2026-11-02", "99497", 133, "CO58", []),
                                             ("9005", "v5", "2026-11-02", "1123F", 0, "CO58", []), ("9005", "v5", "2026-11-02", "99309", 141, "CO16", []))]
for _wdp in (os.path.join(ROOT, "boards", "working_denials.py"), os.path.join(ROOT, "scripts", "helpers", "working_denials.py")):
    _dd = tempfile.mkdtemp(prefix="posrule_den_", dir=tmp); json.dump(_DROWS, open(os.path.join(_dd, "denials_20261110.json"), "w"))
    _wsp = importlib.util.spec_from_file_location("wd_t_%d" % len(_dd), _wdp); _wdm = importlib.util.module_from_spec(_wsp); _wsp.loader.exec_module(_wdm)
    _oc = os.getcwd(); _oa = sys.argv[:]; os.chdir(_dd); sys.argv = ["working_denials.py"]
    try:
        with contextlib.redirect_stdout(io.StringIO()): _dout = _wdm.main()
    finally: os.chdir(_oc); sys.argv = _oa
    _got = {v_["visitid"]: (v_["dispo"], v_["carc"], v_["codes"]) for v_ in _dout["visits"]}
    check("challenge review (exact input, %s): reason 58 leads its visit whatever else the visit carries - v2 (58 then a FIX-class 16), v4 (a FIX-class 4 then 58), v3 (45 then 58) all read REVIEW / 58 with every code kept; 58 on a reporting line (1123F) does not lead (v5 stays FIX / 16)" % os.path.relpath(_wdp, ROOT),
          _got["v1"][:2] == _got["v2"][:2] == _got["v3"][:2] == _got["v4"][:2] == ("REVIEW", "58") and _got["v2"][2] == ["CO/CO16", "CO/CO58"] and _got["v4"][2] == ["CO/CO4", "CO/CO58"] and _got["v3"][2] == ["CO/CO45", "CO/CO58"]
          and _got["v5"][:2] == ("FIX", "16") and _got["v5"][2] == ["CO/CO16", "CO/CO58"], _got)
_drf = [open(os.path.join(ROOT, d_, "denials_refresh.py")).read() for d_ in (os.path.join("scripts", "helpers"), os.path.join("tools", "button"))]
check("the Refresh-from-AMD step (both copies, identical) rolls visits up the same way: a REVIEW-class 58 leads, and a more actionable line keeps the codes already seen", _drf[0] == _drf[1]
      and 'if norm(r["carc"]) == "58" and dispo == "REVIEW": rank = -1' in _drf[0] and '"codes": (rec["codes"] if rec else set()), "rarc": (rec["rarc"] if rec else set())' in _drf[0])
# the digest's words (C5 / C8 a, W3, W5 d) and its section-12 line
r, line = digest(rows + [dict(reg_row(["99232"], "fac29", "21", ["21"]), msg_own=False, msg_fallback="admission date: this message's own last copy", visit="vst8"),
                         dict(reg_row(["99306", "99497"], "fac32", "31", ["31", "31"], ["initial", "with-visit"]), prof="prof13", prof_feed="prof15", prof_why="initial nursing-facility visit: always the physician (William 11/10/2026)", visit="vst9", pid="pat21")])
check("digest (C5 / C8 a): a visit not matched to one copy of its message says, per chart, where the values its copies did not agree on came from - the admission date of its own last copy",
      "for what its copies do not agree on, the patient's last-read building or clinician and the admission date of the message's own last copy were used (each chart says which)" in r.stdout and "pat9 11/02/2026 99232 (admission date: this message's own last copy)" in r.stdout, r.stdout[-900:])
check("digest (12.2): one plain line - initial visits entered under the physician although the feed named another clinician, with chart and visit, and William's words; not a top-of-report line",
      "- Initial visits entered under the physician although the feed named another clinician: 1 (pat21 vst9). William 11/10/2026: every initial nursing-facility visit is his." in r.stdout and "TOP OF THE REPORT - Initial" not in r.stdout, r.stdout[-900:])
r, line = digest([dict(x_, pos_stored=list(x_["pos_lines"])) for x_ in rows])
check("digest (W5 d): even when AdvancedMD's answer echoed the place of service as sent, a run that entered a 32 line still reads ONE back from the chart (the runbook paragraph by its name)",
      "AdvancedMD's own answer shows the place of service as sent on all 6 visit(s) it echoed. The run still reads ONE 32 line back from the chart (runbook, 'EVERY RUN THAT ENTERS A 32 LINE')." in r.stdout, r.stdout[-600:])
# the audit tool does not list William's initial-visit rule as a visit entered under the wrong clinician
json.dump({"created": [{"visit": "vst11", "pid": "pat11", "prof": "prof13", "prof_feed": "prof15", "prof_why": "initial nursing-facility visit: always the physician (William 11/10/2026)", "fac": "fac32", "cpts": ["99306"], "dos": "11/11/2026", "charges": ["charge11"]}]},
          open(os.path.join(aud, "feed_import_20261111T0000Z.json"), "w"))
json.dump({"stamp": "20261111T0000Z", "rows": [{"v": "vst11", "p": "pat11", "d": "2026-11-11", "c": ["99306"], "prov": "Pamela G. (ARNP)"}]}, open(os.path.join(aud, "feed_recon_20261111T0000Z.json"), "w"))
r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", "feed", "feed_clinician_audit.py"), "--registers", aud], capture_output=True, text=True)
check("audit tool (12.3): an initial nursing-facility visit entered under the physician by William's rule is counted apart and not listed as entered under the wrong clinician; the earlier visit still is",
      r.returncode == 0 and "entered under a different clinician: 1" in r.stdout and "entered under the physician by William's initial-visit rule (11/10/2026, register field prof_why - not a fault, not listed): 1" in r.stdout and "vst11" not in r.stdout, r.stdout[-500:])
# the words: rulebook, runbook, lessons
_step = open(os.path.join(ROOT, "nightly", "claimocity_feed_step.md")).read().replace("\n", " "); _less = open(os.path.join(ROOT, "docs", "SHARED_LESSONS.md")).read()
check("W3: the three places that said 'check ... by hand' say it is for William and a routine changes nothing on the visit (the import's pos_err, the digest's line, rulebook part 3)",
      "check by hand" not in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")).read() and "by hand" not in _rules.split("POS RULE NOT APPLIED, ")[1][:60]
      and "facility, clinician and place of service are for William; a routine changes nothing on this visit" in open(HELPER).read() and "POS RULE NOT APPLIED, for William; a routine changes nothing on this visit." in _rules)
check("C9: rulebook part 6 and the runbook name the visit the import flagged that the Claim Inspector holds at the hospital location beside the CCM one - William says what happens to it",
      "and a visit the import flagged (POS RULE NOT APPLIED) that the Claim Inspector holds at the hospital location (Pattern 4531" in _rules and "a CCM visit or a visit the import flagged (POS RULE NOT APPLIED) that the Claim Inspector holds at the hospital location" in _step and "nor for a visit the import flagged as POS RULE NOT APPLIED" in _step)
check("W6 (1): the bypass loop has an upper bound - at most three passes, then stop and report - in the rulebook, the runbook and the lessons line",
      "at most three passes in all - still listed after the third, stop" in _rules and "at most three passes in all (it clears ONE" in _step and "still listed after the third pass: stop" in _step and "at most three passes; still listed after the third: stop" in _less)
check("W5 / W6: the comma of part 6, the lessons line's exception (part 4), what msg_own false means, what N counts, the second one-liner, every '32' of the read-back, and the CCM exception as part 1 words it",
      "pos_stored in the register), visits that" in _rules and "a wrong building the Claim Inspector flags on a charge that has not gone out yet is still corrected as before - rules.md part 4" in _less
      and "false means the message could not be matched to exactly one raw copy: for whatever its copies do not agree on" in _rules and "(N = the number of charts this run names at the top of the report" in _step
      and "print(' '.join(p for p,n in sorted(c.items()) if n>1))" in _step and "every entry '32' (a CCM visit: ['32', '32'])" in _step and "for any reason except a gap of 15 to 20 days (weekly or more" in _step
      and "the feed inspector step works only on the visits of its own batch, so it corrects none of these older visits" in _rules)
check("C1 / W2 / CCM words: a day the feed sent from two buildings counts as another building (also later), the admission date of the message's own last copy, the CCM of a resident whose visits are in another building - rulebook and runbook",
      "and so does a day the feed itself sent from two buildings" in _rules and "and so does a day the feed itself sent from two buildings - in that batch and in later ones" in _step and "the admission date from the message's OWN last copy - never from another message of the patient" in _rules
      and "when the resident's nursing visits are known to be in ANOTHER building than the CCM's own" in _rules and "known to be in another building than the CCM's own" in _step)
check("12.4: the rulebook carries the initial-visit rule in William's words with its date, the runbook its one paragraph, the lessons one line; the merge, the copy line and both denial tables are said",
      "INITIAL NURSING-FACILITY VISIT UNDER THE PHYSICIAN AND THE GROUP: \"initial visits billed by the nurse practitioner. this is a mistake, all the initial 99306 claims are done by me in the snf and should be under effinger npi and the group npi\"" in _rules
      and "going forward the 99306 should always be billed under effinger npi and group npi as i am the one who is doing the initial hps 99306 and 99497" in _rules and "A 99497 that comes WITHOUT a 99306 keeps the clinician of its own message" in _rules
      and "An initial nursing-facility visit (99306, with its 99497) is entered under the physician's profile whatever clinician the feed names" in _step and "2026-11-10T1700Z | chat (William's orders 11/10) | RULE | William 11/10/2026: \"going forward the 99306" in _less
      and "a bullet rewritten in place REPLACES its old copy instead of coming back beside it (tools/mirror/rules_merge.py" in _rules and "claimocity_helpers_current.py, the one function both call" in _rules
      and "Both copies of the denial table (boards/working_denials.py and scripts/helpers/working_denials.py) class reason 58 as REVIEW" in _rules and "'FEED HELPERS NOT ALL CURRENT' or 'FEED HELPERS NOT CHECKED'" in _step)

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
