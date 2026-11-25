#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the place-of-service rule, 11/10/2026)
# Decides: nothing. Loads scripts/helpers/claimocity_import.py with stand-in amd / resave / txh modules in a throwaway folder
#   (no AMD, no network, no patient data - every id, building message and chart here is invented) and proves William's rule:
#     - CCM 99487/99489 is entered as place of service 32 on EVERY line and never at 31 (William 11/25/2026: "make sure they bill with the
#       place of service ltc ... not the skilled snf location of service ... for all ccm charges going forward"): in the five nursing buildings
#       whatever the chart shows (a chart that shows the resident seen at skilled frequency, admitted or readmitted in that calendar month is
#       only LISTED for William - the back end's 31 exception of 11/10 is gone), when the rule fails for the message, and from a building the
#       facility table does not know (the old default 31);
#     - ALF / home CCM keeps 13, hospital lines keep 21, every other line of an unknown building keeps the old default - nothing else changes;
#     - a nursing facility visit is 32 only for the monthly visit (previous nursing visit 21 to 92 days earlier, not a discharge, no
#       hospital visit of ours in between); it is 31 when the resident is seen once or twice a week, for an initial visit, the first
#       nursing visit on the chart, the first visit of a new stay, and whenever the chart shows neither pattern;
#     - 99497 follows the visit line of the same date; modifier 25, fees, dedupe and the hospital admission date are as before;
#     - every visit takes its building, its clinician and its admission date from ITS OWN feed message (a resident's CCM under the
#       physician and the nurse practitioner's visits in one batch each keep their own clinician; a hospital message and a nursing
#       message of one patient each keep their own building); a message the raw files cannot answer falls back to the patient's
#       last-read values and is reported, and so is any failure inside the rule - the import carries on;
#     - a visit an earlier batch could not enter is still read as history; when the batch's own visits cannot be listed no nursing VISIT
#       line is 32 (a CCM line is 32 without that list - William 11/25/2026);
#     - (11/25/2026, the review of the CCM rule) a CCM line that stands at 31 anywhere - in a visit whose rule failed, in a visit with no
#       facility, under whatever kind - is counted by the import and shouted by the digest, which names EVERY chart of its two CCM lists;
#       build() itself moves such a line to 32 once more after the rule, so "never 31" does not rest on the rule's own answer;
#     - (William 11/25/2026: "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to
#       be added") a diagnosis code AdvancedMD's list does not have goes in as I10 in its place - never twice on a line; a line with no
#       code at all is still skipped; without I10 in the list everything is as before; the retry enters the visits that waited on such a
#       code; the digest carries ONE line and writes the email's text to outbox/dx_codes_needed_<stamp>.txt (sections 3b, 6 and 6c);
#     - a feed message with no charge line or no patient id is passed over and counted - it never stops the import step (section 4);
#     - what AdvancedMD stored is read back from its answer and a different place of service is said loudly;
#     - the advance-care-plan quality code 1123F rides, at no charge and once per patient per year, with a visit of a patient 65 or older
#       whose first plan is Medicare Part B and whose last insurance check showed Medicare first - never on a care-management-only message,
#       never twice; a pilot round holds at most three lines and adds none while one of them is not decided; a refused visit is entered
#       again without it. Since 11/12/2026 (William 11/11/2026: "dont stop this dont let it stop make sure this suceeds") the code never
#       switches itself off: where a person, a hold or a refusal showed the line in the way it PROBES (one line a run until one is billed)
#       or PAUSES for one run (a visit stuck held with its line - the inspector step tries it again in every run - or another code text);
#       only William's own QUALITY_CODE=stop lasts; the option code M0004 the same; the digest says the state at its top in every batch
#       (sections 4c, 4d, 6 and the inspector's retry pass here, and the nights of tools/selftest/test_quality_nights.py);
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
check("CCM is 32 on both lines also when the resident had an admission visit that month (William 11/25/2026: every CCM line is 32)", L([("99487", "10/31/2026"), ("99489", "10/31/2026")], "31", True, [("99306", "10/12/2026")]) == ["32", "32"])
check("CCM is 32 also when the resident was seen twice within 14 days that month", L([("99487", "10/31/2026")], "31", True, [("99309", "09/04/2026"), ("99309", "10/06/2026"), ("99309", "10/09/2026")]) == ["32"])
check("CCM is 32 also when the resident came back from the hospital that month", L([("99487", "10/31/2026")], "31", True, HOSP_BETWEEN + [("99309", "10/20/2026")]) == ["32"])
check("CCM is 32 also when one of our hospital visits falls in that month, even with no nursing visit after it", L([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99232", "10/25/2026")]) == ["32"])
check("CCM is 32 when our hospital visits were in ANOTHER month and the month's visit is monthly", L([("99487", "10/31/2026")], "31", True, [("99232", "08/10/2026"), ("99306", "08/14/2026"), ("99309", "09/01/2026"), ("99309", "10/01/2026")]) == ["32"])
check("CCM is 32 also in a month in which the practice saw the resident at home or in an assisted-living facility (out of the building that month) - the chart is listed for William",
      L([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99349", "10/20/2026")]) == ["32"]
      and ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99349", "10/20/2026")])[2] == ["ccm-skilled-month"])
check("CCM is 32 when the home / ALF visit was in ANOTHER month and this month's visit is monthly", L([("99487", "10/31/2026")], "31", True, [("99349", "07/10/2026"), ("99306", "08/01/2026"), ("99309", "09/01/2026"), ("99309", "10/01/2026")]) == ["32"])
check("CCM is 32 also in a month with a discharge visit", L([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99316", "10/12/2026")]) == ["32"])
check("two visit lines on ONE day in a message: any 31 keeps the whole day, and its 99497, at 31", L([("99309", "11/02/2026"), ("99306", "11/02/2026"), ("99497", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["31", "31", "31"] and L([("99497", "11/02/2026"), ("99306", "11/02/2026"), ("99309", "11/02/2026")], "31", True, [("99309", "10/03/2026")]) == ["31", "31", "31"])
check("CCM is 32 also when a visit that month followed one late the month before by 14 days or less", L([("99487", "10/31/2026")], "31", True, [("99309", "08/30/2026"), ("99309", "09/28/2026"), ("99309", "10/02/2026")]) == ["32"])
check("CCM is 32 when the close visits were in ANOTHER month", L([("99487", "10/31/2026")], "31", True, [("99306", "08/03/2026"), ("99309", "08/06/2026"), ("99309", "10/05/2026")]) == ["32"])
check("CCM is 32 when that month's visits are monthly or 15-20 days apart", L([("99487", "10/31/2026")], "31", True, [("99309", "09/01/2026"), ("99309", "10/01/2026"), ("99309", "10/17/2026")]) == ["32"])
_w = ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99306", "10/12/2026")])
check("a CCM line whose chart shows a skilled-looking month is 32, names William, carries no date, and its kind says why it is listed", _w[0] == ["32"] and "William" in _w[1][0] and not re.search(r"\d{1,2}/\d{1,2}/\d{4}", _w[1][0]) and _w[2] == ["ccm-skilled-month"])
# ---- William 11/25/2026: "make sure they bill with the place of service ltc which pays more per prior work not the skilled snf location of service
#      for these charges ... for all ccm charges going forward" - a CCM line is NEVER entered at 31 -----------------------------------------------
_CCM2 = [("99487", "10/31/2026"), ("99489", "10/31/2026")]
_SHOWN = {"an admission visit that month": [("99306", "10/12/2026")], "seen twice within 14 days": [("99309", "09/04/2026"), ("99309", "10/06/2026"), ("99309", "10/09/2026")],
          "back from the hospital": HOSP_BETWEEN + [("99309", "10/20/2026")], "one of our hospital visits that month": [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99232", "10/25/2026")],
          "a home / assisted-living visit that month": [("99309", "09/05/2026"), ("99309", "10/03/2026"), ("99349", "10/20/2026")], "a discharge visit": [("99309", "09/05/2026"), ("99316", "10/12/2026")],
          "the first nursing visit on the chart": [("99309", "10/12/2026")], "a visit after more than 92 days": [("99309", "05/01/2026"), ("99309", "10/12/2026")],
          "the visits in another building": [("99309", "09/05/2026", "BRYNWOOD OPERATIONS LLC"), ("99309", "10/03/2026", "BRYNWOOD OPERATIONS LLC")]}
_r1125 = {k_: ci.pos_lines(_CCM2, "31", True, h_, "fac32") for k_, h_ in _SHOWN.items()}
check("11/25/2026: whatever the chart shows, a nursing-building CCM is 32 on both lines - never the feed's 31 (the back end's exception of 11/10 is gone)",
      all(r_[0] == ["32", "32"] for r_ in _r1125.values()), {k_: r_[0] for k_, r_ in _r1125.items() if r_[0] != ["32", "32"]})
check("11/25/2026: ... and each such chart is still LISTED for William (pos_kind ccm-skilled-month), in words that name him, say 32 and carry no date",
      all(r_[2] == ["ccm-skilled-month"] * 2 and all("William" in w_ and w_.startswith("32 ") and not re.search(r"\d{1,2}/\d{1,2}/\d{4}", w_) for w_ in r_[1]) for r_ in _r1125.values()), {k_: (r_[2], r_[1][0][:60]) for k_, r_ in _r1125.items()})
_u1125 = ci.pos_lines(_CCM2 + [("99309", "10/31/2026"), ("99497", "10/31/2026")], "31", False, ())
check("11/25/2026: a CCM line from a building the facility table does not know (the old default 31) is 32 too; the other lines of that message keep the default",
      _u1125[0] == ["32", "32", "31", "31"] and _u1125[2] == ["ccm-unknown-building"] * 2 + ["", ""] and all("William" in w_ and not re.search(r"\d{1,2}/\d{1,2}/\d{4}", w_) for w_ in _u1125[1][:2]) and _u1125[1][2:] == ["", ""], _u1125)
check("11/25/2026: hospital (21) and ALF / home (13) CCM are not touched", ci.pos_lines(_CCM2, "21", False, ()) == (["21", "21"], ["", ""], ["", ""]) and ci.pos_lines(_CCM2, "13", False, [("99306", "10/12/2026")]) == (["13", "13"], ["", ""], ["", ""]))
_p25, _w25, _k25 = ["31", "31", "31", "13"], ["rule error"] * 4, [""] * 4
check("11/25/2026: ccm_never_31 - where a failed rule leaves every line at the feed's 31, the CCM lines become 32 and no other line is touched",
      ci.ccm_never_31(["99309", "99487", "99489", "99487"], _p25, _w25, _k25) == 2 and _p25 == ["31", "32", "32", "13"] and _k25 == ["", "ccm-forced", "ccm-forced", ""] and _w25[0] == "rule error" and "William" in _w25[1] and _w25[3] == "rule error", (_p25, _w25, _k25))
_CCM_FAMILY = {"99487", "99489", "99490", "99439", "99491", "99437"}
check("11/25/2026: every chronic-care-management code the import can enter is in the rule's CCM set (a code added to the code table without the rule would go out at the feed's 31)",
      {c_ for c_ in ci.PCODE if c_ in _CCM_FAMILY} <= ci.CCM and ci.CCM <= set(ci.PCODE) and ci.CCM <= _CCM_FAMILY, (sorted(ci.CCM), sorted(c_ for c_ in ci.PCODE if c_ in _CCM_FAMILY)))
# 11/25/2026 (review of the CCM rule, finding 5): the digest and the inspector step each keep their OWN copy of the CCM codes - read here from their source text
# (the inspector is never loaded: it talks to AdvancedMD). Each must be the import's set, code for code.
_rep_src = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")).read(); _insp_src = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py")).read()
_ccm_rep = re.search(r"\b_CCM = \{([^}]*)\}", _rep_src); _ccm_insp = re.findall(r'not any\(x in \(([^)]*)\) for x in c\["cpts"\]\)', _insp_src)
_codes = lambda t_: set(re.findall(r'"([0-9A-Z]{5})"', t_))
check("11/25/2026 (review): the digest's own CCM set (claimocity_report.py, _CCM) and the inspector step's CCM codes (its test that keeps a CCM visit from being moved to HCA REHAB at 31) are the import's CCM set, code for code - a CCM code added to the import alone would be moved to 31 after entry, or go uncounted and unshouted in the digest",
      bool(_ccm_rep) and _codes(_ccm_rep.group(1)) == ci.CCM and len(_ccm_insp) == 1 and _codes(_ccm_insp[0]) == ci.CCM, (_ccm_rep and _ccm_rep.group(1), _ccm_insp, sorted(ci.CCM)))
check("... and that guard really reads the codes of such a line: a made-up third CCM code in a line of either shape is read as a third code",
      _codes(re.search(r"\b_CCM = \{([^}]*)\}", '_NFV = {"99304"}; _CCM = {"99487", "99489", "99490"}').group(1)) == ci.CCM | {"99490"}
      and [_codes(t_) for t_ in re.findall(r'not any\(x in \(([^)]*)\) for x in c\["cpts"\]\)', 'all(x not in HOSP for x in c["cpts"]) and not any(x in ("99487", "99489", "99490") for x in c["cpts"]) and not c.get("pos_err"):')] == [ci.CCM | {"99490"}])
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
check("build: a CCM line from an unknown building goes out as 32 (William 11/25/2026: never 31), with no facility, the register keeps the default 31 beside it, and it is not a rule failure",
      [p for _, p in pp] == ["32"] and info["fac"] == "" and info["pos_lines"] == ["32"] and info["pos_feed"] == "31" and info["pos_kind"] == ["ccm-unknown-building"] and info["pos_err"] == "", (pp, info))
check("build (11/25/2026): a message from a building the table does not know carries the feed's OWN building name into the register row (feed_building) - nobody could add the building because its name was in no register and no digest (ten 11/17/2026 visits, charts of one building); a building the table knows carries no such key",
      info.get("feed_building") == B["u1"] and "feed_building" not in built("n1", [("99487", "20261031")])[1] and "feed_building" not in built("a1", [("99487", "20261031")])[1], info)
body, info, pp = built("u1", [("99309", "20261102")])
check("build: a nursing VISIT from an unknown building keeps the old default 31 and no facility", [p for _, p in pp] == ["31"] and info["fac"] == "" and info["pos_lines"] == ["31"] and info["pos_kind"] == [""] and info["pos_err"] == "", (pp, info))
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
check("build: CCM for a resident admitted that month goes out as 32 (William 11/25/2026) and is listed for William", [p for _, p in pp] == ["32"] and info["pos"] == "32" and info["pos_kind"] == ["ccm-skilled-month"] and info["pos_err"] == "", (pp, info))
ci.BATCH_NF_ERR[0] = "selftest: the list was not built"
body, info, pp = built("n1", [("99487", "20261031"), ("99489", "20261031")], live=[("99306", "10/12/2026")])
check("11/25/2026 build: when the batch's own visits could not be listed, a message with no nursing VISIT line needs no pattern - its CCM lines are 32 / 32 and it is not reported as a rule failure",
      [p for _, p in pp] == ["32", "32"] and info["pos_err"] == "" and info["pos_kind"] == ["ccm-skilled-month"] * 2, (pp, info))
body, info, pp = built("n1", [("99309", "20261102"), ("99487", "20261102")], live=[("99309", "10/03/2026")])
check("11/25/2026 build: ... a message WITH a nursing visit line is reported as before - the visit at the feed's 31 - and its CCM line is 32 all the same",
      [p for _, p in pp] == ["31", "32"] and "could not be listed" in info["pos_err"] and info["pos_kind"] == ["", "ccm-forced"] and info["pos_why"][0] == "rule error" and "William" in info["pos_why"][1], (pp, info))
ci.BATCH_NF_ERR[0] = ""
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
check("build: two buildings and a message the raw files cannot answer: the last-read building as before, reported - and its CCM line is 32, never 31 (William 11/25/2026)", [p for _, p in pp] == ["32"] and "2 buildings" in info["pos_err"] and info["pos_lines"] == ["32"] and info["pos_kind"] == ["ccm-forced"] and info["msg_own"] is False, (pp, info))
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
ci.pos_lines = lambda cd, fp, n, h, here=None: (["11"] * len(cd), [""] * len(cd), [""] * len(cd))      # 11/25/2026 (review): the stand-in takes the five arguments build() passes - with four, this check passed on a TypeError and never reached the guard
body, info, pp = built("n2", [("99309", "20261102")], live=[("99309", "10/03/2026")])
check("build: an impossible place of service from the rule is refused by build()'s own guard - the reason reads 'unexpected place of service' (31, reported)", [p for _, p in pp] == ["31"] and info["pos_err"].startswith("unexpected place of service ['11']"), (pp, info))
# 11/25/2026 (review, defence in depth): "a CCM line is never entered at 31" must not rest on the rule's own answer. A stand-in rule that answers 31 for
# a CCM line - under the kind "ccm", as if all were well - is given to build(): the charge that would go to AdvancedMD carries 32 all the same.
_cw = lambda cd: ["32 by rule: CCM in a nursing building" if c_ in ci.CCM else "31 by rule: made up for this test" for c_, _d in cd]
ci.pos_lines = lambda cd, fp, n, h, here=None: (["31"] * len(cd), _cw(cd), ["ccm" if c_ in ci.CCM else "skilled" for c_, _d in cd])
body, info, pp = built("n1", [("99487", "20261031"), ("99489", "20261031")])
check("11/25/2026 build (defence in depth): a rule that answers 31 for a CCM line and calls it 'ccm' - the charge XML still carries pos=\"32\" on both CCM lines and 31 on none; the register says the lines were forced, in William's name, and no rule failure is reported",
      [p for _, p in pp] == ["32", "32"] and (body or "").count(' pos="32" ') == 2 and ' pos="31" ' not in (body or "") and info["pos"] == "32" and info["pos_lines"] == ["32", "32"]
      and info["pos_kind"] == ["ccm-forced", "ccm-forced"] and all("William" in w_ and "never entered at 31" in w_ for w_ in info["pos_why"]) and info["pos_err"] == "" and info["pos_feed"] == "31", (pp, info))
body, info, pp = built("n2", [("99309", "20261102"), ("99487", "20261102"), ("99497", "20261102")], live=[("99309", "10/03/2026")])
check("11/25/2026 build (defence in depth): ... and only the CCM line is touched - the visit line and its 99497 keep the place of service, the reason and the kind the rule gave them",
      [p for _, p in pp] == ["31", "32", "31"] and info["pos_kind"] == ["skilled", "ccm-forced", "skilled"] and info["pos_why"][0] == info["pos_why"][2] == "31 by rule: made up for this test" and info["pos"] == "31", (pp, info))
ci.pos_lines = lambda cd, fp, n, h, here=None: ([fp] * len(cd), [""] * len(cd), [""] * len(cd))
_b13, _i13, _p13 = built("a1", [("99487", "20261031")]); _b21, _i21, _p21 = built("h1", [("99487", "20261031")])
check("11/25/2026 build (defence in depth): ... an ALF / home CCM line (13) and a CCM line from the hospital (21) are not touched by the second look", [p for _, p in _p13 + _p21] == ["13", "21"] and _i13["pos_kind"] == _i21["pos_kind"] == [""], (_p13, _p21))
ci.pos_lines = _realpl
# count_pos (11/25/2026, review): the import's own counters follow the VALUE - a CCM line that stands at 31 is counted as not William's rule under every kind,
# in a visit whose rule failed and in a visit with no facility; the 'CCM 31 xN' of the import's short log line is the sum of that counter
_cnt = lambda info_: (lambda s_: (ci.count_pos(info_, s_), dict(s_))[1])(__import__("collections").Counter())
_K31 = "POS 31 CCM - NOT WILLIAM'S RULE (11/25/2026: every CCM line is 32) - an old copy of the rule ran"
_INFO = lambda cpts, lines, kinds, fac="fac34", err="": {"cpts": cpts, "pos_lines": lines, "pos_kind": kinds, "pos_feed": "31", "fac": fac, "pos_err": err}
_c1 = _cnt(_INFO(["99487", "99489"], ["31", "32"], ["ccm", "ccm"]))
check("count_pos (11/25/2026, review): the VALUE decides, not the label - of two CCM lines called 'ccm', the one at 31 is counted as 'POS 31 CCM - NOT WILLIAM'S RULE' and only the one at 32 as a 32 line",
      _c1.get(_K31) == 1 and _c1.get("POS 32 CCM (nursing building)") == 1 and len(_c1) == 2, _c1)
_c2 = _cnt(_INFO(["99487"], ["31"], ["ccm-skilled-month"]))
check("count_pos: ... the same under the kind 'ccm-skilled-month': a line at 31 is never counted among the 32 lines listed for William", _c2 == {_K31: 1}, _c2)
_c3 = _cnt(_INFO(["99309", "99487"], ["31", "31"], ["", ""], err="boom"))
check("count_pos: ... and in a visit whose rule failed (pos_err) the CCM line at 31 is counted BEFORE the count ends - and that visit is not counted under words that say 'a CCM line at 32'",
      _c3.get(_K31) == 1 and sum(v_ for k_, v_ in _c3.items() if k_.startswith("POS RULE NOT APPLIED")) == 1 and not any("a CCM line at 32" in k_ for k_ in _c3), _c3)
_c4 = _cnt(_INFO(["99487", "99309"], ["31", "31"], ["", ""], fac=""))
check("count_pos: ... and from a building the facility table does not know: the CCM line at 31 is counted as not William's rule, both lines still count as lines of an unknown building, and no counter says 'a CCM line at 32' about that CCM line",
      _c4.get(_K31) == 1 and sum(v_ for k_, v_ in _c4.items() if k_.startswith("POS RULE: building")) == 2 and _c4.get("POS RULE: building not in the facility table - a nursing visit at the default 31, a CCM line at 32") == 1, _c4)
_c5 = _cnt(_INFO(["99309", "99487"], ["31", "32"], ["", "ccm-forced"], err="boom")); _c6 = _cnt(_INFO(["99487", "99309"], ["32", "31"], ["ccm-unknown-building", ""], fac=""))
check("count_pos: what the import enters today is counted as before - a failed rule with its CCM line at 32, and an unknown building with its CCM line at 32, count no CCM line at 31",
      _K31 not in _c5 and _c5.get("POS RULE NOT APPLIED (entered at the feed's place of service; a CCM line at 32)") == 1 and _K31 not in _c6
      and _c6.get("POS RULE: building not in the facility table - a nursing visit at the default 31, a CCM line at 32") == 2, (_c5, _c6))
body, info, pp = built("a1", [("99487", "20261031")], live=[(None, None), ("x",), 7])
check("build: odd rows in the chart history cannot touch an ALF message", [p for _, p in pp] == ["13"] and info["pos_err"] == "", (pp, info))

# ---- 3b. a diagnosis code AdvancedMD's own list does not have: I10 in its place (William 11/25/2026) ---------------------------------------
# "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to be added" (said right after "Add diagnosis
# S82.843D in AMD Master Files change this diagnosis to i10"). The stand-in list of this test knows I10 (dcode1) and E119 (dcode2) and nothing else.
_HSRC = open(HELPER).read()
def dxbuilt(dx, lines=(("99309", "20261102"),), fid="n2"):
    """build() over ONE message whose charge lines carry the diagnosis field dx (one text for every line, or a list with one per line) ->
    (the charge XML or None, the register info or the skip reason, the diagcodes attribute of every charge, the <diagcode> ids of every charge)."""
    dxs = [dx] * len(lines) if isinstance(dx, str) else list(dx)
    m_ = {"pid": fid, "name": "x", "dob": "", "FT1": [{"cpt": c_, "dos": d_, "dx": x_, "units": "1"} for (c_, d_), x_ in zip(lines, dxs)]}
    try: out_, info_ = ci.build(m_, ctx(live=[("99309", "10/03/2026")]))
    except Exception as e: return None, "%s: %s" % (type(e).__name__, e), [], []
    if out_ is None: return None, info_, [], []
    return out_[1], info_, re.findall(r'diagcodes="([^"]*)"', out_[1]), [re.findall(r'<diagcode id="(\d+)"/>', l_) for l_ in re.findall(r"<diagcodelist>(.*?)</diagcodelist>", out_[1])]
def dxold(dx):      # what the import sent for one line BEFORE 11/25/2026: every code the list knows, in the feed's order, at most 12 - a code it does not know was left off
    return " ".join([ci.DX[c_] for c_ in dx.split("^") if ci.DX.get(c_)][:12])
check("William's stand-in code is I10, kept in ONE constant of the import (DX_INSTEAD) with his words beside it, and the helper's PLAIN ENGLISH header states the rule",
      getattr(ci, "DX_INSTEAD", None) == "I10" and re.search(r'^DX_INSTEAD = "I10"\s+#.*for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to be added', _HSRC, re.M) is not None
      and "I10 IN ITS PLACE" in _HSRC.split("\nimport os as _os")[0], getattr(ci, "DX_INSTEAD", None))
_b, _i, _dc, _dl = dxbuilt("S82.843D^E119")
check("dx (William 11/25/2026): a code AdvancedMD's list does not have that stands FIRST on a line goes in as I10, first - the code after it keeps its place; attribute and <diagcode> list agree",
      _dc == ["dcode1 dcode2"] and _dl == [["1", "2"]], (_i, _dc, _dl))
check("dx: ... the register row still names the code AdvancedMD does not know (missing_dx) and says what stands in its place (dx_instead I10)",
      isinstance(_i, dict) and _i.get("missing_dx") == ["S82.843D"] and _i.get("dx_instead") == "I10", _i)
_b, _i, _dc, _dl = dxbuilt("E119^S82.843D")
check("dx: a code the list does not have that stands SECOND goes in as I10 in second place", _dc == ["dcode2 dcode1"] and _dl == [["2", "1"]] and isinstance(_i, dict) and _i.get("dx_instead") == "I10", (_i, _dc))
_r4 = {x_: dxbuilt(x_)[2] for x_ in ("I10^S82.843D", "S82.843D^I10", "E119^S82.843D^I10", "I10^E119^S82.843D", "S82.843D^E119^I10")}
check("dx: I10 never stands twice on a line - when the feed's own I10 is on the line beside a replaced code it stands ONCE, at its first position, and the other codes keep their order",
      _r4 == {"I10^S82.843D": ["dcode1"], "S82.843D^I10": ["dcode1"], "E119^S82.843D^I10": ["dcode2 dcode1"], "I10^E119^S82.843D": ["dcode1 dcode2"], "S82.843D^E119^I10": ["dcode1 dcode2"]}, _r4)
_b, _i, _dc, _dl = dxbuilt("S82.843D^E119^T84.011A^M51.17")
check("dx: two or more replaced codes on one line give I10 once, at the first of their positions - and every one of them is named in missing_dx",
      _dc == ["dcode1 dcode2"] and isinstance(_i, dict) and _i.get("missing_dx") == ["M51.17", "S82.843D", "T84.011A"] and _i.get("dx_instead") == "I10", (_i, _dc))
_b, _i, _dc, _dl = dxbuilt("S82.843D")
check("dx: a line whose ONLY code the list does not have is no longer a reason to skip the visit - it is ENTERED with I10 alone (two 99309 visits waited this way on S82.843D)",
      _b is not None and _dc == ["dcode1"] and _dl == [["1"]] and isinstance(_i, dict) and _i.get("missing_dx") == ["S82.843D"] and _i.get("dx_instead") == "I10" and 'proccode="pcode65119"' in _b, (_i, _dc))
_r7 = {x_: dxbuilt(x_)[:2] for x_ in ("", "^", " ", " ^ ")}
check("dx: a line whose diagnosis field is EMPTY - no code at all - is still skipped as before ('no usable dx for <CPT>'): there is nothing to change to I10",
      all(v_ == (None, "no usable dx for 99309") for v_ in _r7.values()), _r7)
_b, _i, _dc, _dl = dxbuilt(["S82.843D", ""], lines=(("99309", "20261102"), ("99497", "20261102")))
check("dx: ... and ONE such line still skips the whole visit, also when its other line can go in with I10", (_b, _i) == (None, "no usable dx for 99497"), (_b, _i))
_b, _i, _dc, _dl = dxbuilt(["S82.843D^E119", "T84.011A", "E119"], lines=(("99309", "20261102"), ("99497", "20261102"), ("99498", "20261102")))
check("dx: the rule works line by line - each charge line gets I10 where ITS OWN unknown code stood, a line with known codes only is untouched, and the row names every unknown code of the visit once",
      _dc == ["dcode1 dcode2", "dcode1", "dcode2"] and isinstance(_i, dict) and _i.get("missing_dx") == ["S82.843D", "T84.011A"] and _i.get("dx_instead") == "I10", (_i, _dc))
_same = ("I10", "E119", "I10^E119", "E119^I10", "E119^E119", "I10^^E119", "I10^E119^I10")
_brief = lambda r_: (r_[2], r_[1].get("missing_dx"), "dx_instead" in r_[1]) if isinstance(r_[1], dict) else (r_[2], r_[1], None)      # (codes sent per line, the codes named, whether anything stands in a code's place)
_r9 = {x_: _brief(dxbuilt(x_)) for x_ in _same}
check("dx: a line on which no code is replaced is sent EXACTLY as before 11/25/2026 - the same codes in the same order, a code the feed itself repeats included - and its row carries no dx_instead and an empty missing_dx",
      all(v_ == ([dxold(x_)], [], False) for x_, v_ in _r9.items()), _r9)
ci.DX.update({"K%02d" % n_: "dcode%d" % (100 + n_) for n_ in range(14)})
_b, _i, _dc, _dl = dxbuilt("S82.843D^" + "^".join("K%02d" % n_ for n_ in range(14)))
check("dx: the limit of 12 codes on a line stays - I10 in the first place, then the first eleven of the feed's known codes", _dc == [" ".join(["dcode1"] + ["dcode%d" % (100 + n_) for n_ in range(11)])] and len(_dl[0]) == 12, _dc)
for n_ in range(14): del ci.DX["K%02d" % n_]
_b, _i, _dc, _dl = dxbuilt(" E119 ^S82.843D ")
check("dx: a code that arrives with blanks around it is looked up without them, as the cache step and the retry driver already read it - so a code the list HAS is never replaced by I10 (and never asked for in the email) because of a stray blank",
      _dc == ["dcode2 dcode1"] and isinstance(_i, dict) and _i.get("missing_dx") == ["S82.843D"], (_i, _dc))
_dx0 = dict(ci.DX)
for _how, _set in (("I10 itself is not in the list", lambda: ci.DX.pop("I10")), ("the cache holds I10 as 'not in the list' (null)", lambda: ci.DX.__setitem__("I10", None))):
    ci.DX.clear(); ci.DX.update(_dx0); _set()
    _a = _brief(dxbuilt("S82.843D^E119")); _o = dxbuilt("S82.843D"); _t = _brief(dxbuilt("I10^E119"))
    check("dx: when %s EVERYTHING is exactly as before - an unknown code is left off and named, nothing stands in its place (no dx_instead), and a line with no usable code skips the visit" % _how,
          _a == (["dcode2"], ["S82.843D"], False) and _o[:2] == (None, "no usable dx for 99309") and _t == (["dcode2"], ["I10"], False), (_a, _o[:2], _t))
ci.DX.clear(); ci.DX.update(_dx0)
_cd = _cnt(dict(_INFO(["99309"], ["32"], ["monthly"]), dx_instead="I10", missing_dx=["S82.843D"])); _cn = _cnt(_INFO(["99309"], ["32"], ["monthly"]))
check("dx: the import's DONE line counts each visit that went in with I10 in a code's place, in words that name William's order - and counts nothing for a visit with no replaced code",
      [k_ for k_ in _cd if "I10" in k_] == ["diagnosis code not in AdvancedMD's list - visit entered with I10 in its place (William 11/25/2026); the digest names the codes for his email"] and not any("I10" in k_ for k_ in _cn), (_cd, _cn))

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
check("main --dry: when the batch visit list cannot be built it is emptied, said and counted - and the run goes on", "batch visit list not built" in out and "POS RULE: batch visit list not built - nursing visit lines kept at the feed's 31 (CCM lines 32)" in out and ci.BATCH_NF == {} and "DONE" in out, out[-400:])
check("main --dry: ... and then NO nursing VISIT line is 32: each is kept at the feed's 31 and reported - while the CCM message, which needs no pattern, is 32 / 32 and is not reported (William 11/25/2026)",
      all(d["pos_lines"] == ["31"] * len(d["cpts"]) and d["pos_err"] for k in ("pat102", "pat103") for d in dry.get(k, [])) and "not applied x3" in out and dry.get("pat104", [{}])[0].get("pos_lines") == ["13"]
      and [(d["pos_lines"], d["pos_err"], d["pos_kind"]) for d in dry.get("pat101", [])] == [(["32", "32"], "", ["ccm", "ccm"])] and "CCM 32 x2, CCM 31 x0" in out, dry)
ci.BATCH_NF_ERR[0] = ""
_regp = os.path.join(tmp, "registers", "feed_import_SELFTEST.json")
check("main --dry: the broken match row is a failed message - and a dry run that meets one writes NO register (11/10/2026, challenge review: that register made the live run of the same stamp skip whole patients)",
      "ERR ['not', 'a', 'chart']" in out and not os.path.exists(_regp), (os.path.exists(_regp), out[-300:]))
json.dump({"created": [], "skipped": [], "failed": [{"feed_id": "n3", "pid": ["not", "a", "chart"], "lines": [], "err": "odd"}]}, open(_regp, "w"))      # the odd row a failed message used to leave (its chart not a chart number), written here
check("an odd row in a register (its chart not a chart number) is there for the next check", os.path.exists(_regp) and isinstance(json.load(open(_regp))["failed"][0]["pid"], list))
out, dry = run_dry()
check("main --dry: an odd row in an earlier register never switches the rule off for the next run", "batch visit list not built" not in out and dry.get("pat101", [{}])[0].get("pos_lines") == ["32", "32"] and "not applied x0" in out, out[-300:])
os.remove(_regp)
# 11/25/2026 (feed review, finding 6 - older than the CCM change): a parsed message with no charge line, or with no patient id, stopped the WHOLE import step
# (IndexError / KeyError before the per-message guard). The ingest then ended 'STEP FAILED: import', the file was not registered, and every later run stopped
# at the same message. Such a message is passed over and counted; the messages around it go in as if it were not there.
def run_args(argv_):
    """main() with these arguments over ci.PARSED -> (what it printed, its DRY rows per chart, '' or the error that ended it). An error is returned as text: it must show as a failed check, not end this self-test."""
    POSTS.clear(); buf_ = io.StringIO(); _a = sys.argv[:]; sys.argv = ["claimocity_import.py"] + list(argv_); ci.BATCH_NF.clear(); ci.BATCH_NF_ERR[0] = ""; ci._ctx.clear(); err_ = ""
    try:
        with contextlib.redirect_stdout(buf_): ci.main()
    except Exception as e: err_ = "%s: %s" % (type(e).__name__, e)
    finally: sys.argv = _a
    rows_ = {}
    for ln_ in buf_.getvalue().splitlines():
        m_ = re.match(r"DRY (pat\d+) (\{.*\})$", ln_)
        if m_: rows_.setdefault(m_.group(1), []).append(eval(m_.group(2)))      # the helper prints its own dict; this is its own output, no outside data
    return buf_.getvalue(), rows_, err_
_shape = lambda dry_: {k_: [(d_["cpts"], d_["pos_lines"], d_["pos_kind"], d_["pos_err"], d_["fac"], d_["prof"]) for d_ in v_] for k_, v_ in dry_.items()}
_posline = lambda out_: next((l_ for l_ in out_.splitlines() if l_.startswith("POS RULE: CCM")), "")
_base_out, _base_dry, _base_err = run_args(["--dry"])
_NOLINES = {"pid": "n2", "name": NAME("two"), "dob": DOBK, "file": "f", "FT1": [], "IN1": [], "DG1": []}                                # a PID line and no FT1 line
_NOPID = {"file": "f", "FT1": [], "IN1": [], "DG1": []}                                                                               # no PID line at all: no patient id, no name, no date of birth
_NOPID2 = {"file": "f", "FT1": [{"cpt": "99309", "dos": "20261102", "dx": "I10", "units": "1"}], "IN1": [], "DG1": []}                 # ... the same with a charge line
_keep = ci.PARSED[:]; ci.PARSED[:] = [_NOLINES, _NOPID] + _keep[:3] + [_NOPID2] + _keep[3:]
out, dry, _err = run_args(["--dry"])
check("main --dry (11/25/2026, feed review): a feed message with no charge line and two with no patient id do not stop the import step - main() ends with its DONE line and no error",
      _base_err == "" and _err == "" and out.strip().splitlines()[-1:] and out.strip().splitlines()[-1].startswith("DONE "), (_err, out[-300:]))
check("main --dry: ... each is passed over and counted in plain words - 'feed message without a charge line - passed over' once, 'feed message without a patient id - passed over' twice",
      "'feed message without a charge line - passed over': 1" in out and "'feed message without a patient id - passed over': 2" in out, out[-700:])
check("main --dry: ... and the six messages around them reach build exactly as without them - the same visits, places of service, kinds, buildings and clinicians, the same POS RULE line; the batch's visit list is still built",
      sum(len(v_) for v_ in dry.values()) == 6 and _shape(dry) == _shape(_base_dry) and _posline(out) == _posline(_base_out) != "" and "batch visit list not built" not in out and "POS RULE NOT APPLIED" not in out, (_shape(dry), out[-400:]))
check("main --dry: ... and a dry run that meets them still writes no register", not os.path.exists(_regp))
out, dry, _err = run_args(["--dry", "--one", "n1"])
check("main --one <feed patient>: another patient's empty message, and a message of no patient, are simply not this patient's - nothing is counted for them and the one patient's visit is built",
      _err == "" and sorted(dry) == ["pat101"] and "feed message without" not in out, (_err, out[-300:]))
# 11/25/2026 (review, finding 8b): the 'POS CHECK no facility' line - the run copies it to the top of the report - said "at the feed's place of service" also for a CCM line, which is at 32
_U = lambda lines_: {"pid": "u1", "name": NAME("five"), "dob": DOBK, "file": "f", "FT1": [{"cpt": c_, "dos": d_, "dx": "I10", "units": "1"} for c_, d_ in lines_]}
ci.PARSED[:] = [_U([("99309", "20261102")]), _U([("99487", "20261130"), ("99309", "20261130")])]
out, dry, _err = run_args(["--dry"]); ci.PARSED[:] = _keep
_NOFAC = "the message's building is not in the facility table - entered without a facility"
check("main --dry (11/25/2026, review): the 'POS CHECK no facility' line of a CCM visit from a building the table does not know says where its CCM line went in - at 32 - and no longer 'at the feed's place of service'",
      ("POS CHECK no facility pat105 10/31/2026 ['99487'] " + _NOFAC + ": its CCM line(s) at 32 (William 11/25/2026: a CCM line is never 31); for William") in _base_out, [l_ for l_ in _base_out.splitlines() if l_.startswith("POS CHECK no facility")])
check("main --dry: ... a message with a CCM line and a visit line says both - the CCM line at 32, every other line at the feed's place of service - and a visit with no CCM line keeps the old words",
      _err == "" and ("POS CHECK no facility pat105 11/30/2026 ['99487', '99309'] " + _NOFAC + ": its CCM line(s) at 32 (William 11/25/2026: a CCM line is never 31), every other line at the feed's place of service; for William") in out
      and ("POS CHECK no facility pat105 11/02/2026 ['99309'] " + _NOFAC + " at the feed's place of service; for William") in out, (_err, [l_ for l_ in out.splitlines() if l_.startswith("POS CHECK no facility")]))

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
# 11/10/2026 (round 7, section 7): every row records the chart's own order and its open plans when the visit was entered; a visit entered with no
# open plan (AdvancedMD then builds it no insurance-order list) is counted and printed "NO PLAN AT ENTRY". The create shape (insorder "1") stays.
check("live run (round 7): every row records chart_insorder and open_plans_at_entry - a chart with no plan: 0 open plans, each visit printed and counted 'NO PLAN AT ENTRY'",
      all(r_.get("chart_insorder") == "1" and r_.get("open_plans_at_entry") == 0 and r_.get("open_plan_seqs_at_entry") == [] for r_ in reg["created"]) and out.count("NO PLAN AT ENTRY pat") == 5 and "'NO PLAN AT ENTRY': 5" in out
      and sum(1 for b in POSTS if 'action="addvisit"' in b and 'insorder="1"' in b) == 5, (out[-500:], [(r_.get("chart_insorder"), r_.get("open_plans_at_entry")) for r_ in reg["created"]]))
_dm0 = dict(DEMOG); DEMOG.update(order="2", plans=OTHER + MEDICARE.replace('enddate=""', 'enddate="10/01/2026"')); out, reg = run_live(M1); DEMOG.clear(); DEMOG.update(_dm0)
check("live run (round 7): a chart with one open plan (and one ended) - open_plans_at_entry 1, its sequence and the chart's order recorded, nothing printed",
      len(reg["created"]) == 2 and all(r_.get("open_plans_at_entry") == 1 and r_.get("open_plan_seqs_at_entry") == ["2"] and r_.get("chart_insorder") == "2" for r_ in reg["created"]) and "NO PLAN AT ENTRY" not in out, reg["created"])
_pp0 = amd.post; amd.post = lambda body, timeout=0: "<r><Fault>chart not read</Fault></r>" if "getdemographic" in body else _pp0(body, timeout)
try: out, reg = run_live(M1)
finally: amd.post = _pp0
check("live run (round 7): a chart whose plans could not be read records None (unknown - never 0) and is not printed as NO PLAN AT ENTRY",
      len(reg["created"]) == 2 and all(r_.get("open_plans_at_entry") is None and r_.get("chart_insorder") is None for r_ in reg["created"]) and "NO PLAN AT ENTRY" not in out, reg["created"])
out, reg = run_live(M1, flip=True)
last3 = out.strip().splitlines()[-3:]
check("live run: AdvancedMD storing 31 where 32 was sent is said per visit, counted, and shown in a short line within the last three", out.count("POS NOT KEPT") == 2 and any(l.startswith("POS CHECK: stored another POS x2; not own message x0; clinician unknown x0; no facility x0") and len(l) <= 110 for l in last3)
      and any(l.startswith("POS RULE:") for l in last3) and all(r["pos_stored"] != r["pos_lines"] for r in reg["created"]), last3)
out, reg = run_live(M1, none=True)
check("live run: an answer without the place of service claims nothing either way", all(r["pos_stored"] is None for r in reg["created"]) and "POS NOT KEPT" not in out, reg["created"])
out, reg = run_live([P_("m5", "m5", [("99498", "20270121"), ("99309", "20270120")]), P_("m5", "m5", [("99306", "20270121")])])
check("live run: a message with two dates is remembered line by line - the admission visit of the later date is still entered", len(reg["created"]) == 2 and reg["created"][0]["dos_lines"] == ["01/21/2027", "01/20/2027"] and reg["created"][1]["cpts"] == ["99306"] and reg["skipped"] == [], (reg["created"], reg["skipped"]))
# 11/25/2026 (feed review, finding 6): what a LIVE run leaves behind for a message without a charge line / without a patient id
def run_live_safe(parsed, **kw):      # run_live, with a crash of main() returned as text (third value) instead of ending this self-test
    try: return run_live(parsed, **kw) + ("",)
    except Exception as e:
        if os.path.exists(_regp) and not kw.get("keep_own"): os.remove(_regp)
        return "", {"created": [], "skipped": [], "failed": []}, "%s: %s" % (type(e).__name__, e)
_E1 = P_("m1", "m1", [])                                                                # m1's PID line with no FT1 line behind it
out, reg, _err = run_live_safe([_E1, _NOPID, M1[0]], keep_own=True)
check("live run (11/25/2026, feed review): a message without a charge line leaves ONE skipped row with the plain reason where a feed id exists (feed id and chart, no visit line); a message without a patient id leaves no row; the visit behind them is entered",
      _err == "" and [(r_.get("feed_id"), r_.get("pid"), r_.get("why")) for r_ in reg["skipped"]] == [("m1", "pat301", "feed message without a charge line - passed over")] and [r_["cpts"] for r_ in reg["created"]] == [["99309"]] and reg["failed"] == [], (_err, reg["skipped"], out[-300:]))
out, reg, _err = run_live_safe([_E1, _NOPID, M1[0], M1[1]])                              # the SAME stamp started again (its register is still there), now with the resident's CCM message behind
check("live run: ... that row never makes a second start under the same stamp pass over the resident's OTHER messages (a skipped row of a real visit passes over the whole patient): the CCM message behind it is entered by the second start, and the row is not written a second time",
      _err == "" and [tuple(r_["cpts"]) for r_ in reg["created"]] == [("99309",), ("99487", "99489")] and [r_.get("why") for r_ in reg["skipped"]] == ["feed message without a charge line - passed over"], (_err, [r_["cpts"] for r_ in reg["created"]], reg["skipped"], out[-300:]))
if os.path.exists(_regp): os.remove(_regp)
# William 11/25/2026: a diagnosis code AdvancedMD's list does not have - the visit is entered with I10 in its place (section 3b proves build(); this is main() against the stand-in AdvancedMD)
_DXV = dict(P_("n2", "two", [("99309", "20261102")]), FT1=[{"cpt": "99309", "dos": "20261102", "dx": "S82.843D", "units": "1"}])      # the visit of the kind that waited: one line, its only code not in the list
out, reg, _err = run_live_safe([_DXV, P_("n3", "three", [("99306", "20261103")])])
_sent = [b_ for b_ in POSTS if 'action="updvisitwithnewcharges"' in b_ and 'proccode="pcode65119"' in b_]
check("live run (William 11/25/2026): a visit whose only diagnosis code is not in AdvancedMD's list is ENTERED - the charge sent carries I10's id alone - and not skipped; its register row names the code and what stands in its place; the visit beside it carries neither",
      _err == "" and reg["skipped"] == [] and len(_sent) == 1 and 'diagcodes="dcode1"' in _sent[0] and '<diagcodelist><diagcode id="1"/></diagcodelist>' in _sent[0]
      and [(r_["cpts"], r_.get("missing_dx"), r_.get("dx_instead")) for r_ in reg["created"]] == [(["99309"], ["S82.843D"], "I10"), (["99306"], [], None)], (_err, reg["created"], reg["skipped"]))
check("live run: ... and the import's DONE line counts that one visit under William's order", "'diagnosis code not in AdvancedMD's list - visit entered with I10 in its place (William 11/25/2026); the digest names the codes for his email': 1" in out.replace('"', "'"), out[-500:])
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
check("C1 (exact input): the 09/05 visit the feed sent from Westminster AND from Brynwood is entered once, at the feed's 31 and reported; the next visit (10/08, 33 days later) stays at 31 - that day reads as a move, as a day the chart and the feed name under two buildings does - and the October CCM is 32 and LISTED for William (11/25/2026: every CCM line is 32; 1478f14: 32 monthly / 32 CCM, named nowhere)",
      [x_["dos"] for x_ in s4x] == ["09/05/2026", "10/08/2026", "10/31/2026"] and "2 buildings" in s4x[0]["pos_err"] and s4x[0]["pos_lines"] == ["31"]
      and s4x[1]["pos_lines"] == ["31"] and s4x[1]["pos_kind"] == ["moved"] and s4x[2]["pos_lines"] == ["32"] and s4x[2]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
check("C1: the visit's created row keeps every building its copies named (tie_lines), so a later batch still sees that day under two buildings; one-building visits carry none",
      s4x and s4x[0].get("tie_lines") == [["99309", "09/05/2026", B["n1"]], ["99309", "09/05/2026", WO]] and "tie_lines" not in s4x[1] and "tie_lines" not in s4x[2], s4x[0].get("tie_lines"))
check("C1: a message sent from two buildings that is NOT entered (a code the table lacks, a diagnosis AdvancedMD does not know) keeps its visit lines once per building in the register, so a later batch reads that day the same way",
      s4c1.seen_lines(P_("t1", "t1", [("99309", "20260905")])) == [["99309", "09/05/2026", B["n1"]], ["99309", "09/05/2026", WO]] and s4c1.seen_lines(P_("t1", "t1", [("99308", "20261008")])) == [["99308", "10/08/2026", WO]])
check("C1: the batch list carries that day once per building (msg_buildings), and a message sent from one building keeps exactly its own",
      s4c1.msg_buildings(P_("t1", "t1", [("99309", "20260905")])) == [B["n1"], WO] and s4c1.msg_buildings(P_("t1", "t1", [("99308", "20261008")])) == [WO], s4c1.BATCH_NF.get("pat801"))
# C1b: the review's second input - only the last hunk (the visit's OWN day named under two buildings) LISTS the month's CCM for William (until 11/25/2026 it also kept that CCM at 31; since then it is 32 like every CCM line)
s4c1b = s4_fresh({"20261002.hl7": hl7("t2", B["n2"], "", [("99309", "20261002")], NP_NPI) + hl7("t2", WO, "", [("99309", "20261002")], NPI) + hl7("t2", B["n2"], "", [("99487", "20261031")], NPI)})
CHART["802"] = [("99309", "09/03/2026", "ASPIRE AT TALLAHASSEE")]
s4o, s4r = s4_run(s4c1b, [P_("t2", "t2", [("99309", "20261002")]), P_("t2", "t2", [("99309", "20261002")]), P_("t2", "t2", [("99487", "20261031")])], {"t2": "pat802"}); s4x = s4_rows(s4r, "pat802")
check("C1b (exact input): the October CCM of a resident whose 10/02 visit the feed sent from Aspire AND Westminster is LISTED for William - at 32 since 11/25/2026 (1478f14: 32, named nowhere)", [x_["dos"] for x_ in s4x] == ["10/02/2026", "10/31/2026"] and s4x[1]["pos_lines"] == ["32"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
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
check("C1 (challenge review, tie_then_next_batch): yesterday's batch entered the visit the feed sent from two buildings; in today's batch the next visit and the month's CCM still read that day as named under two buildings - the visit stays at 31 (a move) and the CCM is LISTED for William, at 32 like every CCM line since 11/25/2026 (without the register's tie_lines the chart's one building made them 32 monthly / 32 CCM, named nowhere)",
      [x_["dos"] for x_ in s4x] == ["10/08/2026", "10/31/2026"] and s4x[0]["pos_kind"] == ["moved"] and s4x[0]["pos_lines"] == ["31"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"] and s4x[1]["pos_lines"] == ["32"], s4_brief(s4x))
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
check("second reviewers (logic M1, exact input): the CCM from Aspire of a resident whose nursing visits are at Brynwood that month is listed for William (was 32 / 32 with nothing named) - at 32 / 32 since 11/25/2026; the Brynwood visit itself is still the monthly 32",
      [x_["cpts"] for x_ in s4x] == [["99309"], ["99487", "99489"]] and s4x[0]["pos_lines"] == ["32"] and s4x[1]["pos_lines"] == ["32", "32"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"] * 2, s4_brief(s4x))
s4l2 = s4_fresh({"a.hl7": hl7("q2", B["n2"], "", [("99487", "20261031")], NPI)})
CHART["812"] = [("99309", "09/05/2026", BRY_AMD), ("99309", "10/03/2026", BRY_AMD)]
s4o, s4r = s4_run(s4l2, [P_("q2", "q2", [("99487", "20261031")])], {"q2": "pat812"}); s4x = s4_rows(s4r, "pat812")
check("second reviewers (logic M1, variant X2): both Brynwood visits already on the chart and only the Aspire CCM in the batch - listed for William, at 32 since 11/25/2026", s4x and s4x[0]["pos_lines"] == ["32"] and s4x[0]["pos_kind"] == ["ccm-skilled-month"], s4_brief(s4x))
s4m = s4_fresh({"a.hl7": hl7("m7x", B["n1"], "", [("99309", "20261005")], NP_NPI) + hl7("m7x", B["n2"], "", [("99487", "20261031"), ("99489", "20261031")], NPI)
                + hl7("m8x", B["a1"], "", [("99344", "20261010")], NP_NPI) + hl7("m8x", B["n2"], "", [("99487", "20261031")], NPI)})
CHART["813"] = [("99309", "09/05/2026", BRY_AMD)]; CHART["814"] = []
s4o, s4r = s4_run(s4m, [P_("m7x", "m7x", [("99309", "20261005")]), P_("m7x", "m7x", [("99487", "20261031"), ("99489", "20261031")]), P_("m8x", "m8x", [("99344", "20261010")]), P_("m8x", "m8x", [("99487", "20261031")])],
                  {"m7x": "pat813", "m8x": "pat814"})
s4x = s4_rows(s4r, "pat813"); s4z = s4_rows(s4r, "pat814")
check("second reviewers (message-identity X2, exact input): M7 - Brynwood visit 10/05, then the physician's Aspire CCM of 10/31: listed for William (was 32 / 32 with nothing named); M8 - an assisted-living visit, then an Aspire CCM: listed too - both at 32 since 11/25/2026",
      s4x[1]["pos_lines"] == ["32", "32"] and s4x[1]["pos_kind"] == ["ccm-skilled-month"] * 2 and s4x[0]["pos_lines"] == ["32"] and s4z[1]["pos_lines"] == ["32"] and s4z[1]["pos_kind"] == ["ccm-skilled-month"], (s4_brief(s4x), s4_brief(s4z)))
_ccm2 = [("99309", "09/05/2026", BRY_AMD), ("99309", "10/03/2026", BRY_AMD)]
check("CCM in another building: the pure rule - a CCM entered at Aspire reads the residents' Brynwood visits as another building (LISTED - 32 since 11/25/2026); entered at Brynwood itself it is the plain long-term 32; a visit with no building name changes nothing",
      ci.pos_lines([("99487", "10/31/2026")], "31", True, _ccm2, "fac32")[0] == ["32"] and ci.pos_lines([("99487", "10/31/2026")], "31", True, _ccm2, "fac32")[2] == ["ccm-skilled-month"] and ci.seen_at_skilled_frequency("10/31/2026", _ccm2, "fac32") is True
      and ci.pos_lines([("99487", "10/31/2026")], "31", True, _ccm2, "fac34")[0] == ["32"] and ci.pos_lines([("99487", "10/31/2026")], "31", True, _ccm2, "fac34")[2] == ["ccm"]
      and ci.pos_lines([("99487", "10/31/2026")], "31", True, [("99309", "09/05/2026"), ("99309", "10/03/2026")], "fac32")[2] == ["ccm"] and ci.seen_at_skilled_frequency("10/31/2026", _ccm2, "fac34") is False)
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
# ---- CCM and a patient who has passed away - William's word of 11/25/2026: ("run a death check on all ccm charges to make sure there is no date of death prior to billing the ccm charges ...
# verify that no patient dies and a new set of ccm charges go in month after month after the patient has died"). The import's own guard read only the CACHE: a death an
# earlier check had found. A patient who died since had the month's CCM entered; the insurance check after the import then found the death - as a hold that stops nothing
# in AdvancedMD - and the charge went out and was written off later (four charts, August 2026). Medicare is now asked BEFORE a CCM message is entered.
import types as _types
D_BEFORE = "2026-11-" + "10"; D_AFTER = "2026-11-" + "25"      # a date the stand-in Medicare reports, before / after the CCM date of 11/22 - put together at run time: the privacy gate scrubs a date that follows the word in a file it carries, this one included
_DG = _types.ModuleType("deceased_guard"); _DG.calls = []; _DG.deaths = {}; _DG.fail = False
def _dg_load():
    try: return json.load(open(os.environ["DECEASED_CACHE"]))
    except Exception: return {}
def _dg_check(pid, dos, carrier=None, proc=None, allow_lookup=True):      # the real guard's shape: asks Medicare when it may, keeps a death in the cache file, answers (blocked, why)
    _DG.calls.append((pid, dos, carrier, proc, allow_lookup))
    if _DG.fail: raise RuntimeError("the look-up is down")
    if allow_lookup and pid in _DG.deaths:
        c_ = _dg_load(); c_[pid] = {"dod": _DG.deaths[pid], "src": "stand-in Medicare"}; json.dump(c_, open(os.environ["DECEASED_CACHE"], "w"))
    return bool((_dg_load().get(pid) or {}).get("dod")), "stand-in"
_DG._load = _dg_load; _DG.check = _dg_check
_dg_old = sys.modules.get("deceased_guard"); sys.modules["deceased_guard"] = _DG
CHART["721"] = []; CHART["722"] = []; CHART["723"] = []
s4d = s4_fresh({"a.hl7": hl7("pc", B["n1"], "", [("99487", "20261122"), ("99489", "20261122")], NPI) + hl7("pd", B["n1"], "", [("99487", "20261122")], NPI) + hl7("pe", B["n1"], "", [("99309", "20261120")], NP_NPI)})
S4_CCM = [P_("pc", "pc", [("99487", "20261122"), ("99489", "20261122")]), P_("pd", "pd", [("99487", "20261122")]), P_("pe", "pe", [("99309", "20261120")])]
S4_CCM_M = {"pc": "pat721", "pd": "pat722", "pe": "pat723"}
def ccm_death_run(deaths, cache=None, argv=("--all",), fail=False):
    dc_ = os.path.join(tmp, "deceased_ccm.json"); json.dump(cache or {}, open(dc_, "w")); os.environ["DECEASED_CACHE"] = dc_
    _DG.calls[:] = []; _DG.deaths = dict(deaths); _DG.fail = fail
    try: o_, r_ = s4_run(s4d, S4_CCM, S4_CCM_M, argv=argv)
    finally: os.environ["DECEASED_CACHE"] = DECEASED_OWN
    return o_, r_, list(_DG.calls)
try:
    o_, r_, c_ = ccm_death_run({"721": D_BEFORE})
    _sk = [x_ for x_ in (r_ or {}).get("skipped", []) if x_.get("pid") == "pat721"]
    check("CCM death check - William's word of 11/25/2026: a patient who died since the last check - the cache knows nothing - has the month's CCM kept OUT: Medicare is asked BEFORE the entry, the death is before the CCM date, the message is skipped 'never billed' and no CCM charge is created for that chart",
          [x_["pid"] for x_ in (r_ or {}).get("created", [])] == ["pat722", "pat723"] and len(_sk) == 1 and _sk[0]["why"].startswith("DOS after date of death " + D_BEFORE) and "Medicare" in _sk[0]["why"] and "never billed" in _sk[0]["why"]
          and "DOS after date of death - not entered" in o_, (r_, o_[-300:]))
    check("CCM death check: Medicare is asked once per CCM chart, with the CCM date and as a care-management claim, and a chart with no CCM line is not asked by the import (the insurance check after the import asks for it)",
          c_ == [("721", "11/22/2026", None, "99487", True), ("722", "11/22/2026", None, "99487", True)], c_)
    o_, r_, c_ = ccm_death_run({"721": D_AFTER})
    check("CCM death check: a CCM dated ON OR BEFORE the date of death is entered (the month of death is billable up to that day)", [x_["pid"] for x_ in (r_ or {}).get("created", [])] == ["pat721", "pat722", "pat723"], r_)
    o_, r_, c_ = ccm_death_run({}, cache={"721": {"dod": D_BEFORE}})
    check("CCM death check: a death the cache already holds keeps the CCM out with NO new question - every later month the same (a death is never undone)",
          [x_["pid"] for x_ in (r_ or {}).get("created", [])] == ["pat722", "pat723"] and [x_[0] for x_ in c_] == ["722"] and "(deceased cache)" in [x_ for x_ in r_["skipped"] if x_.get("pid") == "pat721"][0]["why"], (r_, c_))
    o_, r_, c_ = ccm_death_run({"721": D_BEFORE}, argv=("--dry",))
    check("CCM death check: a dry run buys nothing - it reads the cache only (the look-up is not allowed) and writes no register", r_ is None and c_ and all(x_[4] is False for x_ in c_), (r_, c_))
    o_, r_, c_ = ccm_death_run({"721": D_BEFORE}, fail=True)
    check("CCM death check: a look-up that fails never keeps a charge out (the guard's own rule: only a date of death blocks) - the CCM is entered, the run says the check could not be made, and the insurance check asks again after the import",
          [x_["pid"] for x_ in (r_ or {}).get("created", [])] == ["pat721", "pat722", "pat723"] and "CCM death check could not be made before the entry" in o_, (r_, o_[-300:]))
finally:
    if _dg_old is None: sys.modules.pop("deceased_guard", None)
    else: sys.modules["deceased_guard"] = _dg_old
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
check("ledger (SM-1): a visit billed without its $0.00 line while ANOTHER $0.00 line of the round is billed - $0.00 is proven; only the line READ as left off is dead - its patient is due again only 30 days after it was called left off "
      "(K12, November 12, 2026 - fix round 1: AdvancedMD may still bill it until then, and once per patient and year holds across a left-off line too); nobody else is touched",
      s["confirmed"] is True and s["fee"] == "0.00" and s["zero_not_billed"] is False and s["left_off_lines"] == ["charge12"] and s["dead_rows"] == [["pat7001", "vst1", "charge12"]] and s["dead"] == {("pat7001", "1123F", "11/10/2026")}
      and s["done"] == {("pat7001", "2026"), ("pat7002", "2026"), ("pat7003", "2026")} and s["proof"]["charge"] == "charge22" and s["left_off_on"] == {"charge12": {"on": "11/20/2026", "billed": "11/11/2026"}}, s)
s_rev = state([(RN("20261111T1240Z"), {"created": [C_, B_, A_]})])
check("ledger (SM-1): ... the same whatever the order of the rows", (s_rev["confirmed"], s_rev["fee"], s_rev["left_off_lines"], s_rev["done"], s_rev["proof"]["charge"]) == (True, "0.00", ["charge12"], s["done"], "charge22"), s_rev)
_NX = nextreg("20261120T1240Z"); RUN_DAY[0] = _dt.date(2026, 12, 19); s29 = state([R1, _NX]); RUN_DAY[0] = _dt.date(2026, 12, 20); s30 = state([R1, _NX]); RUN_DAY[0] = _dt.date(2026, 11, 20)
check("ledger (K12, fix round 1): ... the patient of the left-off line stays not due 29 days after it was called left off, and is due again on the 30th day (as before: a left-off line was never reported); the others still count",
      ("pat7001", "2026") in s29["done"] and ("pat7001", "2026") not in s30["done"] and {("pat7002", "2026"), ("pat7003", "2026")} <= s30["done"] and s30["left_off_lines"] == ["charge12"], (s29["done"], s30["done"]))
world(c11=["11/11/2026"]); s = state([R1])
check("ledger: a visit billed without its $0.00 line and NO line of the round billed - new lines carry one cent and the code PROBES from there: one line a run until one is billed (11/12/2026; before, a new round of three); only that one line is dead "
      "(its patient is due again 30 days after it was called left off - K12, fix round 1), the two lines not decided yet keep counting as reported",
      s["fee"] == "0.01" and s["zero_not_billed"] is True and s["confirmed"] is False and s["wait"] is False and s["budget"] == 1 and s["left_off_lines"] == ["charge12"] and s["dead_rows"] == [["pat7001", "vst1", "charge12"]]
      and s["done"] == {("pat7001", "2026"), ("pat7002", "2026"), ("pat7003", "2026")} and s["round"]["n"] == 2 and s["round"]["fee"] == "0.01" and s["round"]["lines"] == 0 and any("without its $0.00 quality line" in n for n in s["notes"]) and s["off"] == "" and s["off_until_reset"] == ""
      and s["probe"] == "new lines carry $0.01: AdvancedMD left the $0.00 line of visit vst1 off its claim and no $0.00 line of the round is billed - one line a run until one is billed" and (s["probe_kind"], s["probe_since"], s["probe_tries"]) == ("left_off", "feed_import_20261111T1240Z.json", 1), s)
world(c11=["11/11/2026"], c22=BILLED); s3 = state([R1], files={"checks": {"20261111T1240Z": {"pat7002": ("RELEASE", "HUM01")}}})
check("ledger: a visit billed without its $0.00 line while another $0.00 line of the round IS billed, though on a claim that cannot be the proof - the amount does NOT move to one cent (AdvancedMD does send a $0.00 line); the round waits for its third line",
      s3["fee"] == "0.00" and s3["zero_not_billed"] is False and s3["confirmed"] is False and s3["wait"] is True and s3["pending"] == ["vst3"] and s3["left_off_lines"] == ["charge12"] and s3["billed_lines"] == ["charge22"], s3)
world(c11=["11/11/2026"]); state([R1])
world(c11=["11/11/2026"], c22=BILLED); s2 = state([R1, nextreg("20261112T1240Z")])
check("ledger: once at one cent it stays there - a $0.00 line found billed LATER is counted for its patient but changes nothing; the other two are read until decided, and the line read as left off is read again (13.1b: still not billed, so it stays left off)",
      s2["fee"] == "0.01" and s2["confirmed"] is False and s2["billed_lines"] == ["charge22"] and s2["left_off_lines"] == ["charge12"] and DETAILS.count("12") == 1 and "22" in DETAILS and "32" in DETAILS and s2["budget"] == 1 and (s2["probe_kind"], s2["probe_tries"]) == ("left_off", 1)
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
check("ledger: a line is void while its visit's own charge is still live - a person took it off: that patient gets NO line again this year, the charge is kept as taken, and the code STAYS ON (11/12/2026; before, off until a restart). Before proof it probes - one line a run - instead of filling the free place; here the round still waits for its two other lines",
      s["off"] == "" and s["off_until_reset"] == "" and s["probe"] == "1 earlier quality line(s) were taken off their visits (void) while the visits are still there (vst1) - William looks" and s["probe_kind"] == "voided" and s["budget"] == 0 and s["wait"] is True and s["pending"] == ["vst2", "vst3"]
      and s["void_lines"] == ["charge12"] and s["taken_lines"] == ["charge12"] and ("pat7001", "2026") in s["refused"] and ("pat7001", "2026") in s["done"] and ci.quality_gate()["refused_charts"] == [["pat7001", "2026"]]
      and any("a person decided: pat7001 gets no line again this year; the code stays on" in n for n in s["notes"]), s)
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
check("ledger: the replacement lines are voided too - a round never holds more than six lines: the code PROBES ('the pilot's lines keep being voided'), one line a run - it no longer switches itself off (11/12/2026)",
      s["probe"] == "the pilot's lines keep being voided (6 lines in this round, none billed) - William looks" and s["probe_kind"] == "voided" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1 and s["round"]["lines"] == 6 and not any(c_ in DETAILS for c_ in ("12", "22", "32")), (s, DETAILS))
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
check("ledger: an earlier $0.00 line is read later and found taken off its visit by a person while the one-cent round is NOT proven - an OLDER line starts nothing: the code goes on as it stood (probing since the move to one cent, waiting for its one-cent line); that patient gets no line again this year",
      s["off"] == "" and s["off_until_reset"] == "" and (s["probe_kind"], s["probe_tries"]) == ("left_off", 1) and s["budget"] == 0 and s["wait"] is True and s["pending"] == ["vst4"]
      and s["void_lines"] == ["charge22"] and s["taken_lines"] == ["charge22"] and s["fee"] == "0.01" and ("pat7002", "2026") in s["refused"] and ("pat7002", "2026") in s["done"], s)
chg("42", BILLED); chg("41", BILLED, "pcode65119"); s = state([R1, ONEC])                        # the same, but the one-cent line D is billed: one cent is proven in this very run
check("ledger: ... the same $0.00 line found taken off once one cent IS proven - the proven code goes on as it stood; the patient of the line a person took off gets no line again this year (11/12/2026; before, due again)",
      s["off"] == "" and s["confirmed"] is True and s["fee"] == "0.01" and s["budget"] == 10 and s["probe"] == "" and s["void_lines"] == ["charge22"] and s["billed_lines"] == ["charge42"] and ("pat7002", "2026") in s["done"] and ("pat7002", "2026") in s["refused"]
      and any("taken off the visit" in n for n in s["notes"]), s)
world(c12=VOID); chg("42", []); chg("41", [], "pcode65119")                                      # A's $0.00 line was taken off by a person; nobody had read it before William restarted the code
s = state([R1, (RN("20261112T1240Z"), {"created": [qrow("pat7004", "vst4", "charge42", "charge41")], "quality_gate": {"reset": True, "fee": "0.00"}})])
check("ledger: a line from BEFORE William's restart that is read only now and found taken off - an older line starts nothing: the new round waits for its own line; that patient gets no line again this year",
      s["off"] == "" and s["probe"] == "" and s["wait"] is True and s["pending"] == ["vst4"] and s["void_lines"] == ["charge12"] and s["round"]["lines"] == 1 and ("pat7001", "2026") in s["done"] and ("pat7001", "2026") in s["refused"] and any("taken off the visit" in n for n in s["notes"]), s)
# what proves the code: a billed line whose visit was never held and whose own batch's insurance check did not hold the chart or name another payer
world(c12=BILLED)
for _chk, _ok in ((None, True), (OKCHK, True), (("HOLD", ""), False), (("RELEASE", "HUM01"), False), (("RELEASE", ""), False)):
    s = state([R1], files={"checks": {"20261111T1240Z": {"pat7001": _chk}} if _chk else {}})
    check("ledger: a billed line and its own batch's insurance check %s -> %s" % (_chk or "(none of that batch)", "proven" if _ok else "NOT the proof - billed all the same, and the round goes on waiting for the other lines"),
          s["confirmed"] is _ok and s["billed_lines"] == ["charge12"] and (_ok or (s["wait"] is True and s["pending"] == ["vst2", "vst3"] and any("cannot be the proof" in n for n in s["notes"]))), s)
s = state([R1], files={"checks": {"20261109T0000Z": {"pat7001": ("HOLD", "")}}})
check("ledger: ... the check of ANOTHER batch does not matter for the proof", s["confirmed"] is True, s)
world(c12=BILLED, c22=BILLED, c32=BILLED); s = state([R1], files={"checks": {"20261111T1240Z": {p_: ("RELEASE", "HUM01") for p_ in ("pat7001", "pat7002", "pat7003")}}})
check("ledger: the round is full, every line is decided and none can be the proof - the code PROBES, one line a run (otherwise the pilot would stand still for ever without a word); it no longer switches itself off", s["probe"] == "the pilot round is full (3 lines) and none of them can be the proof - William looks" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1 and s["confirmed"] is False, s)
# HELD VISITS (the Medicare reviewer's M1): a visit that carries the line and is held
INS = lambda why, **kw: {"held": {"1": [("feed_inspector_20261111T1240Z.json", why, kw.get("marked", False))]}}
STUCK_ = lambda why, what="the Claim Inspector holds it and the line was not taken off": 'paused this run: visit vst1 (chart pat7001) is held with its quality line - %s (feed_inspector_20261111T1240Z.json: "%s"); no new line while that is so - every run\'s inspector step tries the void and the re-save again' % (what, why)
world(); s = state([R1], files=INS("Relationship of Subscriber to Patient is invalid"))
check("ledger (M1): BEFORE proof any Claim Inspector hold on a visit that carries the line makes that visit STUCK (11/12/2026; before, the code went off until a restart) - PAUSED for this run: no line, the sentence names the visit and quotes the hold, the gate lists the visit for the inspector step's retry pass, and nothing is off until a restart",
      s["off"] == STUCK_("Relationship of Subscriber to Patient is invalid") and s["paused"] == s["off"] and s["off_until_reset"] == "" and s["probe"] == "" and s["budget"] == 0 and ci.quality_gate()["stuck"] == s["stuck"]
      and s["stuck"] == [{"chart": "pat7001", "visit": "vst1", "charge": "charge12", "own": "charge11", "code": "1123F", "fee": "0.00", "with": "", "why": "Relationship of Subscriber to Patient is invalid", "register": "feed_inspector_20261111T1240Z.json",
                          "what": "the Claim Inspector holds it and the line was not taken off", "since": "feed_inspector_20261111T1240Z.json"}], s)
world(c12=BILLED); s = state([R1], files=INS("Pattern 990001: procedure 1123F - line item charge amount is zero"))
check("ledger (M1): a held visit that a person released and that is billed afterwards is NEVER the proof - and until a newer entry says the visit is free it stays listed as stuck (the next inspector step finds it no longer listed)",
      s["confirmed"] is False and s["proof"] is None and s["billed_lines"] == ["charge12"] and s["paused"] == STUCK_("Pattern 990001: procedure 1123F - line item charge amount is zero") and s["budget"] == 0 and any("cannot be the proof" in n for n in s["notes"]), s)
world(c12=BILLED, c22=BILLED); s = state([R1], files=INS("Pattern 990001: procedure 1123F - line item charge amount is zero"))
check("ledger (M1): ... a line of the same round whose visit was never held IS the proof; the stuck visit still pauses this run and no more", s["confirmed"] is True and s["proof"]["charge"] == "charge22" and s["paused"] != "" and s["budget"] == 0 and s["off_until_reset"] == "", s)
PROVEN = (RN("20261112T1240Z"), {"created": [], "quality_gate": {"confirmed": True, "fee": "0.00", "proof": {"visit": "vst2", "charge": "charge22"}}})
world(); s = state([R1, PROVEN], files=INS("Relationship of Subscriber to Patient is invalid"))
check("ledger (M1): AFTER proof a hold whose words do not name the line changes nothing", s["off"] == "" and s["confirmed"] is True and s["budget"] == 10 and s["stuck"] == [], s)
for _w in ("Pattern 990001: procedure 1123F - line item charge amount is zero", "edit on pcode65441", "charge 12 cannot be billed", "Pattern 88001: Charge amount is zero for this procedure"):
    s = state([R1, PROVEN], files=INS(_w))
    check("ledger (M1): AFTER proof a hold whose words name the line (%s) makes the visit STUCK - paused this run, the proof stays, never off until a restart" % _w[:40],
          s["paused"] == STUCK_(_w) and s["off"] == s["paused"] and s["off_until_reset"] == "" and s["confirmed"] is True and s["budget"] == 0 and [i_["visit"] for i_ in s["stuck"]] == ["vst1"], s)
s = state([R1, PROVEN], files=INS("Pattern 24078: something else", marked=True))
check("ledger (M1): ... and so does a hold the inspector step itself marked as naming the line", s["paused"] == STUCK_("Pattern 24078: something else") and s["budget"] == 0 and s["off_until_reset"] == "", s)
s = state([R1, PROVEN], files={"held": {"9": [("feed_inspector_20261111T1240Z.json", "procedure 1123F - zero", False)]}})
check("ledger: a hold on a visit that does not carry the line is not the quality code's business", s["off"] == "" and s["confirmed"] is True, s)
_w = "Pattern 990001: procedure 1123F - line item charge amount is zero"; _old = (RN("20261112T1240Z"), {"created": [], "quality_gate": {"reset": True, "fee": "0.00"}})
world(); s = state([R1, _old], files=INS(_w))
check("ledger (M1): a visit held with its line from BEFORE William's restart is STILL stuck after it (11/12/2026: his reset is no word about that visit, which must still be tried again; before, the hold stopped counting) - the gate lists it, no line is added, the new round holds nothing",
      [i_["visit"] for i_ in s["stuck"]] == ["vst1"] and s["paused"] == STUCK_(_w) and s["budget"] == 0 and s["round"]["lines"] == 0 and s["round"]["n"] == 2 and s["off_until_reset"] == "", s)
_free = {"removed": {"20261113T1240Z": [("feed_inspector_20261113T1240Z.json", {"visit": "vst1", "pid": "pat7001", "charge": "charge12", "code": "1123F", "fee": "0.00", "why": _w, "void_ok": False, "released": True, "listed": False,
                                         "retry_of": "feed_inspector_20261111T1240Z.json", "note": "the visit is no longer listed by the Claim Inspector - nothing done", "at": "x"})]}}
s = state([R1, _old, (RN("20261113T1240Z"), {"created": []})], files=dict(INS(_w), **_free))
check("ledger (M1): ... only a NEWER entry ends a stuck mark: the retry's entry 'no longer listed' frees the visit and counts nothing more (no refusal, the patient is not marked, the line is not called void by it); from there the code probes, one line a run",
      s["stuck"] == [] and s["paused"] == "" and s["off"] == "" and s["probe"] == 'visit vst1 was held with its quality line until the routine could free it (feed_inspector_20261113T1240Z.json: "%s")' % _w and s["probe_kind"] == "stuck" and s["probe_words"] == _w
      and s["budget"] == 1 and s["refused"] == set() and s["void_lines"] == [] and s["fee"] == "0.00", s)
CHK = lambda *words: {"check_holds": {"1": [("feed_verify_20261111T1240Z.json", list(words))]}}
PROVEN0 = (RN("20261110T1240Z"), {"created": [], "quality_gate": {"confirmed": True, "fee": "0.00", "proof": {"visit": "vst0", "charge": "charge02"}}})      # the code was proven BEFORE the batch of A, B, C
for _w in ("insorder not applied on vst1", "vst1 insorder 2: detail read mismatch (1 of 2 charges live)", "vst1 insorder 2: resave FAULT <Fault>x</Fault>", "insorder not applied"):
    _why = 'the insurance check could not set the order of visit vst1, which carries the quality line (feed_verify_20261111T1240Z.json: "%s") - William looks' % _w
    world(); s = state([R1], files=CHK("no active plan: discovery found nothing", _w))
    check("ledger (M1): before proof, the insurance check could not set the order of a visit that carries the line (%s) - that visit is for a person and the code PROBES (11/12/2026; before, off until a restart): the sentence names the visit and quotes the hold; no line while the round's lines are not decided" % _w[:34],
          s["probe"] == _why and (s["probe_kind"], s["probe_since"], s["probe_tries"]) == ("order", "feed_verify_20261111T1240Z.json", 1) and s["off"] == "" and s["off_until_reset"] == "" and s["wait"] is True and s["budget"] == 0, s)
    world(); s = state([PROVEN0, R1], files=CHK("no active plan: discovery found nothing", _w))
    check("ledger (M1): after proof, the insurance check could not set the order of a visit that carries the line (%s) - the proof in place is SET ASIDE there: the lines entered up to that point can no longer be the proof, and the code probes with ONE line" % _w[:34],
          s["probe"] == _why and s["probe_kind"] == "order" and s["confirmed"] is False and s["proof"] is None and s["off"] == "" and s["off_until_reset"] == "" and s["wait"] is False and s["budget"] == 1 and s["round"]["lines"] == 0, s)
world(); s = state([R1, PROVEN], files=CHK("no active plan: discovery found nothing", "insorder not applied on vst1"))
check("ledger (M1): ... a proof recorded AFTER that cause ends the probe - the code is proven and adds ten a run", s["confirmed"] is True and s["probe"] == "" and s["budget"] == 10 and s["off"] == "", s)
world(c12=BILLED); s = state([R1], files=CHK("insorder not applied on vst9", "no active plan: discovery found nothing"))
check("ledger (M1): another insurance-check HOLD on a pilot visit (or one that names another visit) does not switch the code off - but that visit can never be the proof, and the round waits for the others",
      s["off"] == "" and s["confirmed"] is False and s["billed_lines"] == ["charge12"] and s["wait"] is True and s["pending"] == ["vst2", "vst3"], s)
# a PROBE is REMEMBERED by the gate (SM-4), and the switches (SM-8). 11/12/2026: the code never switches itself off - only William's own stop lasts, and only his stop is ended by his reset
world(c12=VOID); s = state([R1]); _why = s["probe"]; LATER = nextreg("20261112T1240Z")
world(c12=VOID, c11=VOID, c22=VOID, c21=VOID, c32=VOID, c31=VOID); s = state([R1, LATER])
check("ledger (SM-4): a probe is carried forward by the gate - the next run still probes with the same sentence although everything now reads void (voiding the lines does not start a new pilot of three): ONE line, the cause counted once, and the patient of the line a person took off still gets none",
      s["probe"] == _why and "taken off their visits" in _why and (s["probe_kind"], s["probe_tries"], s["probe_since"]) == ("voided", 1, "feed_import_20261111T1240Z.json") and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1 and s["reset"] is False
      and s["taken_lines"] == ["charge12"] and ("pat7001", "2026") in s["done"], (s, DETAILS))
s = state([R1, LATER, nextreg("20261113T1240Z"), nextreg("20261114T1240Z")])
check("ledger (SM-4): ... and the run after, and the one after that", s["probe"] == _why and s["probe_tries"] == 1 and s["budget"] == 1 and s["off"] == "", s)
s = state([R1, LATER], reset=True)
check("switch reset while the code PROBES is ignored, loudly (only William's own stop is ended by his reset) - the code goes on probing in its round",
      s["reset"] is False and s["probe"] == _why and s["budget"] == 1 and s["round"]["n"] == 1 and "NOTHING TO RESTART" in s["loud"] and "NOTHING TO RESTART" in ci.quality_log(0, False), s)
s = state([R1, LATER], stop=True); STOP1 = nextreg("20261113T1240Z")
check("switch stop while the code probes: STOPPED on William's word - off_until_reset holds his sentence, and nothing else ever; no line", s["off"] == s["off_until_reset"] and s["off"].startswith("stopped on William's word (QUALITY_CODE=stop)") and s["budget"] == 0, s)
s = state([R1, LATER, STOP1], reset=True)
check("switch reset (William's word) after his stop: a new round at $0.00, the stop is gone, the probe is over, the restart is recorded - the old lines are no longer this round's, but a line that exists still counts once a year",
      s["off"] == "" and s["off_until_reset"] == "" and s["reset"] is True and s["fee"] == "0.00" and s["budget"] == 3 and s["probe"] == "" and s["round"]["lines"] == 0 and s["round"]["n"] == 2 and any("started again" in n for n in s["notes"]) and s["loud"] == "", s)
RESET = nextreg("20261114T1240Z", created=[qrow("pat7004", "vst4", "charge42", "charge41")]); chg("42", []); chg("41", [], "pcode65119")
s = state([R1, LATER, STOP1, RESET])
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
check("switch stop while the code probes keeps what the probe was about in the gate - the stop sentence alone is what is off", s["off"].startswith("stopped on William's word (QUALITY_CODE=stop)") and s["off_until_reset"] == s["off"] and "taken off their visits" in s["probe"], s)
world(); state([R1], stop=True); s = state([R1, nextreg("20261112T1240Z")], stop=True)
check("switch stop when the code is already stopped keeps his sentence and says so", s["off"].startswith("stopped on William's word (QUALITY_CODE=stop)") and s["off_until_reset"] == s["off"] and any("already off" in n for n in s["notes"]), s)
# REFUSALS in a row at one amount (SM-11): before proof ONE is enough, after proof TWO; a stored line clears the count; the refused patient gets no second try that year
REF = lambda pid, fee="0.00", **kw: dict({"pid": pid, "visit": "vst9", "quality_codes": [], "quality_refused": "Fault: no", "quality_refused_fee": fee, "quality_tried": fee, "quality_dos": "11/10/2026", "dos": "11/10/2026", "charges": ["charge91"]}, **kw)
world(); s = state([(RN("20261111T1240Z"), {"created": [REF("pat7009")]})])
check("refusals: BEFORE proof one refused visit at $0.00 moves the amount to one cent, and that move itself begins a probe - one line a run, AdvancedMD's own words kept (11/12/2026; before, a new round of three); the refused patient gets no second try that year",
      s["fee"] == "0.01" and s["off"] == "" and s["budget"] == 1 and s["round"]["n"] == 2 and s["refused"] == {("pat7009", "2026")} and ("pat7009", "2026") in s["done"] and ci.quality_gate()["refused_charts"] == [["pat7009", "2026"]]
      and s["probe"] == "AdvancedMD refused a visit that carried the code at $0.00 (feed_import_20261111T1240Z.json) - new lines carry $0.01, one line a run until one is billed" and (s["probe_kind"], s["probe_words"], s["probe_tries"]) == ("refused", "Fault: no", 1), s)
s = state([(RN("20261111T1240Z"), {"created": [REF("pat7009")]}), (RN("20261112T1240Z"), {"created": [REF("pat7010", "0.01")]})])
check("refusals: refused at one cent too - the code goes on PROBING, one line a run (11/12/2026; before, off until a restart): the newest cause is the sentence, it says where, and the causes are counted",
      s["probe"] == "AdvancedMD refused a visit that carried the code with a one-cent charge too (feed_import_20261112T1240Z.json) - William looks" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1
      and (s["probe_kind"], s["probe_since"], s["probe_tries"]) == ("refused", "feed_import_20261111T1240Z.json", 2) and s["refused"] == {("pat7009", "2026"), ("pat7010", "2026")}, s)
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
check("refusals (SM-11): after proof TWO refused visits in a row with no line stored in between move the amount to one cent - the proof at $0.00 no longer counts and the code probes there, one line a run",
      s["fee"] == "0.01" and s["confirmed"] is False and s["budget"] == 1 and s["off"] == "" and (s["probe_kind"], s["probe_since"], s["probe_tries"]) == ("refused", "feed_import_20261114T1240Z.json", 1), s)
chg("102", []); chg("101", [], "pcode65119")      # a line entered AFTER proof (its register's gate says proven), then the same two refusals
s = state([R1, (RN("20261112T1240Z"), {"created": [qrow("pat7010", "vst10", "charge102", "charge101")], "quality_gate": {"confirmed": True, "fee": "0.00", "billed_lines": ["charge12"]}}),
           (RN("20261113T1240Z"), {"created": [REF("pat7009")]}), (RN("20261114T1240Z"), {"created": [REF("pat7011")]})])
check("ledger: a line entered AFTER proof is never read back - not even when two refusals later move the amount to one cent; only the pilot's own lines that are not decided yet are still read, and a line already decided is not read again",
      s["fee"] == "0.01" and s["confirmed"] is False and "102" not in DETAILS and "101" not in DETAILS and "22" in DETAILS and "32" in DETAILS and "12" not in DETAILS and ("pat7010", "2026") in s["done"], (s, DETAILS))
s = after_proof([REF("pat7009")], [REF("pat7011")], [REF("pat7012", "0.01")])
check("refusals: ... and one refused visit at one cent, before that amount is proven, keeps the code probing - never off", "with a one-cent charge too" in s["probe"] and s["probe_tries"] == 2 and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1, s)
FAILED = lambda **kw: dict({"feed_id": "f1", "pid": "pat7009", "empty_visit": "vst70", "info": {"quality_tried": "0.00", "quality_dos": "11/10/2026", "dos": "11/10/2026", "cpts": ["99309"]}, "err": "x"}, **kw)
# November 12, 2026 - fix round 1 (K11): the inspector step of the same run looks at a visit of a fault run - not held by the Claim Inspector = free (its entry: "listed": false, "fault": true); only then does the next run probe
FREE70 = lambda st="20261111T1240Z", **kw: {"removed": {st: [("feed_inspector_%s.json" % st, dict({"visit": "70", "pid": "pat7009", "charge": "", "code": "1123F", "fee": "0.00", "why": "x", "void_ok": False, "released": True, "listed": False,
                                                                                                   "retry_of": "feed_import_%s.json" % st, "fault": True, "note": "the visit is no longer listed by the Claim Inspector - nothing done", "at": "x"}, **kw))]}}
def step_frees(stamp, failed, since):      # K11: that run's inspector step found each visit of a fault run NOT held by the Claim Inspector - its register says so (the live plays below write it; each play removes it again)
    wreg("feed_inspector_%s.json" % stamp, {"fixed": [], "bypassed": [], "held": [], "laterality": [], "quality_removed": [
        {"visit": num(f_["empty_visit"]), "pid": f_["pid"], "charge": "", "code": "1123F", "fee": "0.00", "why": "x", "void_ok": False, "released": True, "listed": False, "retry_of": since, "fault": True,
         "note": "the visit is no longer listed by the Claim Inspector - nothing done", "at": "x"} for f_ in failed if isinstance(f_, dict) and f_.get("empty_visit")]})
_F70 = (RN("20261111T1240Z"), {"created": [], "failed": [FAILED(stored=[["99309", "11/10/2026"], ["1123F", "11/10/2026"]])]})
world(); s0 = state([_F70]); s = state([_F70], files=FREE70())
check("refusals (SM-5, K11 - fix round 1): a fault although the chart shows the visit - that visit is for a person and its patient gets no second try, AND until the inspector step has looked at it the visit is STUCK: paused (no new line), "
      "listed under 'stuck' with fault true and what the import knows (visit, chart, amount, date - the charge number of its line is not known); the code is not off",
      s0["budget"] == 0 and s0["paused"].startswith("paused this run: visit vst70 (chart pat7009) came from a fault run - AdvancedMD answered a fault but kept the visit - nobody has seen yet whether the Claim Inspector holds it")
      and [(x_["visit"], x_["chart"], x_["charge"], x_["fee"], x_["dos"], x_.get("fault")) for x_ in s0["stuck"]] == [("vst70", "pat7009", "", "0.00", "11/10/2026", True)] and s0["probe_kind"] == "fault" and s0["off_until_reset"] == "" and ("pat7009", "2026") in s0["done"], s0)
check("refusals (SM-5): ... once the step found it not held (listed false), from the next run the code PROBES with one line (11/12/2026; before, off until William had looked); the sentence names the chart, the visit and the register; that patient gets no second try",
      s["probe"] == "AdvancedMD answered a fault but kept the visit - William looks (chart pat7009, visit vst70, feed_import_20261111T1240Z.json)" and s["probe_kind"] == "fault" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1 and ("pat7009", "2026") in s["done"] and s["stuck"] == [], s)
s = state([_F70], files=FREE70(charge="charge701", void_ok=True, released=True, resave_ok=True, listed=None, note=""))
check("refusals (K11): ... the step found it held, took its line off (the charge it found) and the visit went through: free, and that is ONE refusal at its amount ($0.00 before proof moves new lines to one cent) - its patient was marked already",
      s["stuck"] == [] and s["paused"] == "" and s["fee"] == "0.01" and s["probe_kind"] == "claim_check" and "held visit vst70 because of its quality line" in s["probe"] and ("pat7009", "2026") in s["refused"] and s["budget"] == 1, s)
s = state([_F70], files=FREE70(released=False, listed=None, note="no live 1123F line of at most one cent on that visit in the chart's history - nothing voided; a person looks at that visit"))
check("refusals (K11): ... the step found it held and no live 1123F line of that visit to take off: it stays STUCK for a person - paused, no new line meanwhile, the state names the visit and what the step found",
      [(x_["visit"], x_.get("fault"), x_["register"]) for x_ in s["stuck"]] == [("vst70", True, "feed_inspector_20261111T1240Z.json")] and s["budget"] == 0 and s["stuck"][0]["what"].startswith("the Claim Inspector holds it and its line did not come off (no live 1123F line")
      and s["paused"].startswith("paused this run: visit vst70 (chart pat7009) came from a fault"), s)
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(stored=["chart not read: TimeoutError"])]})], files=FREE70())
check("refusals (SM-5): ... and the same when the chart could not be read after the fault (the sentence says that)", s["probe"].startswith("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (chart pat7009") and s["probe_kind"] == "fault" and s["off"] == "" and s["budget"] == 1, s)
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(quality_sent="0.00")]})])
check("refusals (NH-11): a visit refused with the line whose send WITHOUT the line then failed is counted like a refusal by the next run (one cent before proof), and that patient gets no second try (it carries no line: no stuck visit)", s["fee"] == "0.01" and s["off"] == "" and ("pat7009", "2026") in s["done"] and s["stuck"] == [], s)
s0 = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(quality_unknown="0.00")]})]); s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(quality_unknown="0.00")]})], files=FREE70())
check("refusals: a call that carried the line and ended in an error (nobody knows what AdvancedMD kept) - that visit is for a person; stuck until the step has looked (K11), then the code probes",
      s0["budget"] == 0 and [x_.get("fault") for x_ in s0["stuck"]] == [True] and "the call that carried the line ended in an error" in s0["stuck"][0]["what"]
      and s["probe"].startswith("a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (chart pat7009, visit vst70") and s["probe_kind"] == "fault" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1, (s0, s))
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(), FAILED(stored=[]), {"err": "x"}, 7]})])
check("refusals: a visit refused with AND without the line is an ordinary fault - it says nothing about the code (a plain pilot the next run)", s["fee"] == "0.00" and s["off"] == "" and s["budget"] == 3 and s["refused"] == set(), s)
# a restart inside a stamp that already holds rows: what was written before the restart stays in the old round
world(); chg("42", []); chg("41", [], "pcode65119")
SAME = (RN("20261111T1240Z"), {"created": [A_, qrow("pat7004", "vst4", "charge42", "charge41")], "failed": [FAILED(stored=[["99309", "11/10/2026"]])], "quality_gate": {"reset": True, "reset_after": [1, 1], "fee": "0.00"}})
s = state([SAME], files=FREE70())      # (K11: that run's inspector step found the fault visit not held)
check("restart under a stamp that already held rows: the fault and the line from BEFORE the restart do not switch the code off again or sit in the new round - the new round holds only the line entered after it",
      s["off"] == "" and s["wait"] is True and s["pending"] == ["vst4"] and s["round"]["lines"] == 1 and ("pat7001", "2026") in s["done"], s)
s = state([(SAME[0], dict(SAME[1], quality_gate={"reset": True, "fee": "0.00"}))], files=FREE70())
check("restart: ... (without the mark of where the restart happened, the whole register counts as after it - the fault is met in the new round and begins a probe there)", "AdvancedMD answered a fault but kept the visit" in s["probe"] and s["probe_kind"] == "fault" and s["off"] == "", s)
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
# F3 (confirm review): this register's gate comes from the run of 11/21 above, which read the left-off line billed - a later reading wins over an older gate's "left off"
D9 = nextreg("20261115T1240Z", created=[qrow("pat7001", "vst9", "charge92", "charge91", fee="0.01", dos="11/15/2026")]); chg("92", []); chg("91", [], "pcode65119")
s = state([R1, G14, D9], day=D_(11, 21))
check("ledger (13.1b, F3): a line read as left off and found billed by a later run has ONE state, billed - an older gate's 'left off' does not bring it back: not listed as left off, not read again, no dead line, its patient coded",
      s["left_off_lines"] == [] and "charge12" in s["billed_lines"] and "12" not in DETAILS and s["dead_rows"] == [] and ("pat7001", "2026") in s["done"], (s["left_off_lines"], s["billed_lines"], DETAILS))
chg("12", []); state([R1, G14], day=D_(11, 15)); D9 = nextreg("20261115T1240Z", created=[qrow("pat7001", "vst9", "charge92", "charge91", fee="0.01", dos="11/15/2026")]); chg("92", []); chg("91", [], "pcode65119"); chg("12", ["11/20/2026"])
_L0 = ci.QUALITY_LOOKS; ci.QUALITY_LOOKS = 3
try: s = state([R1, G14, D9], day=D_(11, 21)); _d3 = list(DETAILS)
finally: ci.QUALITY_LOOKS = _L0
s6 = state([R1, G14, D9], day=D_(11, 21))
check("ledger (13.1b): ... the re-read comes after everything else and only inside the run's reads - with three reads the one-cent line and the two other $0.00 lines use them up and the left-off line waits for a later run; with six it is read, last",
      s["late_rows"] == [] and s["left_off_lines"] == ["charge12"] and len(_d3) == 6 and "12" not in _d3 and DETAILS[-1] == "12" and s6["late_rows"] == [["pat7001", "vst1", "charge12", "11/14/2026", "", "2026"]], (s["late_rows"], _d3, DETAILS, s6["late_rows"]))
world(c11=["11/11/2026"], c21=VOID, c22=VOID, c31=VOID, c32=VOID); state([R1], day=D_(11, 14)); G14b = nextreg("20261114T1240Z")
D9 = nextreg("20261115T1240Z", created=[qrow("pat7001", "vst9", "charge92", "charge91", fee="0.01", dos="11/15/2026")]); chg("92", []); chg("91", [], "pcode65119"); chg("12", ["11/20/2026"])
s = state([R1, G14b, D9], day=D_(11, 21))
check("ledger (13.1b, F4 - the confirm review's case D5): ... when that patient got a second line meanwhile (its one-cent line of 11/15) that is NOT billed, the late row names no second billed line", s["late_rows"] == [["pat7001", "vst1", "charge12", "11/14/2026", "", "2026"]], s["late_rows"])
chg("92", ["11/16/2026"]); s = state([R1, G14b, D9], day=D_(11, 21)); chg("92", [])
check("ledger (13.1b): ... when that second line IS billed, the late row names it - two billed lines for 2026, nothing to do", s["late_rows"] == [["pat7001", "vst1", "charge12", "11/14/2026", "vst9", "2026"]], s["late_rows"])
chg("12", []); s = state([R1, G14], day=D_(12, 12)); _d12 = list(DETAILS); s15 = state([R1, G14], day=D_(12, 15))
check("ledger (13.1b; K13, fix round 2): ... a left-off line is read again until 30 days after it was CALLED left off (11/14) - the K12 block's own clock: still read on 12/12 (31 days after its visit was billed), no longer on 12/15",
      "12" in _d12 and "12" not in DETAILS and s["left_off_lines"] == ["charge12"] and s15["left_off_lines"] == ["charge12"], (s["left_off_lines"], _d12, DETAILS))
world(c12=BILLED); TEXTOF["12"] = "99497"; s = state([R1]); G_TXT = nextreg("20261112T1240Z")
check("ledger (13.4): the charge detail names procedure id pcode65441 with another code text - NOT the proof: PAUSED for this run (11/12/2026; before, off until a restart) - the sentence says what AdvancedMD shows, the gate records the text and the charge, and no probe starts from it",
      s["confirmed"] is False and s["off"] == "paused this run: AdvancedMD shows procedure id pcode65441 as 99497, not 1123F - no line while that is so; every run reads it again" and s["paused"] == s["off"] and s["wrong_code_text"] == "99497" and s["wrong_code_charge"] == "charge12"
      and s["off_until_reset"] == "" and s["probe"] == "" and s["budget"] == 0, s)
s = state([R1, G_TXT])
check("ledger (13.4): ... the next run reads THAT charge again first and is paused while it still shows the other text", s["paused"].startswith("paused this run: AdvancedMD shows procedure id pcode65441 as 99497") and DETAILS[:1] == ["12"] and s["budget"] == 0 and s["confirmed"] is False and s["off_until_reset"] == "", (s, DETAILS))
TEXTOF.clear(); s = state([R1, G_TXT])
check("ledger (13.4): ... and the first run that reads 1123F there goes on by itself where it stood - here that billed line is the proof; nobody restarts anything", s["paused"] == "" and s["off"] == "" and s["wrong_code_text"] == "" and s["confirmed"] is True and s["proof"]["charge"] == "charge12" and s["budget"] == 10 and s["probe"] == "", s)
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
check("ledger (11.3): a line the inspector step took off a held visit that then went through (released) - void and final, NOT read, NOT 'taken off by a person'; it is ONE refusal: before proof one is enough - at $0.00 new lines carry one cent and the code PROBES there with the claim check's own words kept (11/12/2026; before, a new round of three) - and that patient gets no second try this year",
      s["void_lines"] == ["charge12"] and "12" not in DETAILS and s["off"] == "" and s["fee"] == "0.01" and ("pat7001", "2026") in s["refused"] and ("pat7001", "2026") in s["done"] and s["round"]["n"] == 2 and any("held visit vst1 because of its quality line" in n_ for n_ in s["notes"])
      and (s["probe_kind"], s["probe_words"], s["probe_since"], s["probe_tries"]) == ("claim_check", "Pattern 77002: Claim line requires review", "feed_inspector_20261111T1240Z.json", 1) and s["probe"].endswith(" - new lines carry $0.01, one line a run until one is billed"), s)
_nov11 = {"removed": {"20261111T1240Z": [("feed_inspector_20261111T1240Z.json", {"visit": v_, "pid": p_, "charge": c_, "fee": "0.00", "why": "[Pattern 2049] Per Medicare guidelines the...; Zero dollar CPT", "void_ok": True, "released": True, "at": "x"})
                                         for v_, p_, c_ in (("vst1", "pat7001", "charge12"), ("vst2", "pat7002", "charge22"), ("vst3", "pat7003", "charge32"))]}}
world(); s = state([R1], files=_nov11)
check("ledger (the shape of November 11, 2026): the claim check stopped all three $0.00 pilot lines, the step took them off and the visits went out - the next import puts ONE one-cent line, not three (open point 1, way c: at one cent the code probes from its first line); the three patients get no second try this year; nothing is read",
      s["fee"] == "0.01" and s["budget"] == 1 and s["wait"] is False and s["off"] == "" and s["off_until_reset"] == "" and (s["probe_kind"], s["probe_tries"], s["probe_words"]) == ("claim_check", 1, "[Pattern 2049] Per Medicare guidelines the...; Zero dollar CPT")
      and s["refused"] == {("pat7001", "2026"), ("pat7002", "2026"), ("pat7003", "2026")} and s["void_lines"] == ["charge12", "charge22", "charge32"] and DETAILS == [] and "probing: one line a run until one is seen billed" in ci.quality_log(0, False), (s, DETAILS, ci.quality_log(0, False)))
world(); s = state([R1], files=REM(released=False))
check("ledger (11.3): ... the visit was held anyway (not released) - void and final, nothing counts: the place in the round is free, the patient is due again, the amount stays $0.00",
      s["void_lines"] == ["charge12"] and s["fee"] == "0.00" and s["off"] == "" and ("pat7001", "2026") not in s["done"] and s["round"]["void"] == 1 and s["wait"] is True and "12" not in DETAILS, s)
world(); s = state([R1], files=REM(void_ok=False, released=False, note="the void failed: Fault"))
check("ledger (11.3): ... the void failed - the visit is held WITH its line: it is STUCK - paused this run (no line), listed for the inspector step's retry pass, and the cause is kept for the probing that follows; never off until a restart (11/12/2026)",
      s["paused"] == STUCK_("Pattern 77002: Claim line requires review", "the routine could not take the line off") and s["off"] == s["paused"] and s["off_until_reset"] == "" and s["budget"] == 0 and s["void_lines"] == []
      and [(i_["visit"], i_["what"], i_["register"]) for i_ in s["stuck"]] == [("vst1", "the routine could not take the line off", "feed_inspector_20261111T1240Z.json")]
      and s["probe"] == 'the Claim Inspector holds visit vst1 and the routine could not take its quality line off (feed_inspector_20261111T1240Z.json: "Pattern 77002: Claim line requires review") - William looks' and s["probe_kind"] == "stuck", s)
world(); s = state([R1], files=dict(INS("Pattern 77002: Claim line requires review"), **REM(released=False)))
check("ledger (11.3): a Claim Inspector hold on a visit whose line the routine took off is the visit's own business - no pause and nothing stuck (a visit is stuck only while its line could NOT be taken off)", s["off"] == "" and s["paused"] == "" and s["stuck"] == [] and s["void_lines"] == ["charge12"] and s["wait"] is True, s)
world(); s = state([R1], files=REM(st_="20261111T1240Z", reg_="feed_verify_20261111T1240Z.json"))
check("ledger (11.3): a removal by the insurance check (released, the echo sent once more without the line) counts the same way", s["void_lines"] == ["charge12"] and s["fee"] == "0.01" and ("pat7001", "2026") in s["refused"], s)
world(); s = state([R1], files=REM(released=False, still_named=True, resave_ok=True)); s2 = state([R1], files=REM(released=False, resave_ok=False))
check("ledger (NH2-2): the line is gone but the visit is still listed for the edit about it (the re-save after the void failed, or AdvancedMD did not inspect it again) - NOT the visit's own reason: the visit is STUCK - paused this run, every run's step re-saves it again; the cause's sentence still says one re-save should release it",
      [(i_["visit"], i_["what"]) for i_ in s["stuck"]] == [("vst1", "the line is off, but the visit is still listed for the edit about it")] and s["paused"] == STUCK_("Pattern 77002: Claim line requires review", "the line is off, but the visit is still listed for the edit about it")
      and "still listed for the edit about the line" in s["probe"] and "one re-save of the visit should release it" in s["probe"] and s["probe_kind"] == "stuck" and s["off_until_reset"] == "" and s["void_lines"] == ["charge12"]
      and [i_["visit"] for i_ in s2["stuck"]] == ["vst1"] and s2["budget"] == 0 and s2["off_until_reset"] == "", (s, s2))
_two = {"removed": {"20261112T1240Z": [("feed_inspector_20261112T1240Z.json", {"visit": v_, "pid": p_, "charge": c_, "fee": "0.00", "why": "x", "void_ok": True, "released": True}) for v_, p_, c_ in (("vst1", "pat7001", "charge12"), ("vst2", "pat7002", "charge22"))]}}
world(); s1 = state([R1, PROVEN], files={"removed": {"20261112T1240Z": _two["removed"]["20261112T1240Z"][:1]}}); s2 = state([R1, PROVEN], files=_two)
check("ledger (11.3): after proof ONE line taken off a released visit changes nothing; TWO in a row move new lines to one cent, where the code probes - one line a run",
      s1["fee"] == "0.00" and s1["confirmed"] is True and s1["off"] == "" and s1["probe"] == "" and s2["fee"] == "0.01" and s2["confirmed"] is False and s2["off"] == "" and s2["probe_kind"] == "claim_check" and s2["budget"] == 1, (s1, s2))
# 11/12/2026 - four rules that only the checks below pin (each was broken once in a throwaway copy, and a check had to fail)
world(); s = state([R1, PROVEN, (RN("20261113T1240Z"), {"created": [REF("pat7009")]}), (RN("20261114T1240Z"), {"created": [REF("pat7011")]})], files=CHK("no active plan: discovery found nothing", "insorder not applied on vst1"))
check("ledger (2.3 point 6): a probe that began before the proof has ENDED with it - a cause met later begins a NEW period: its own register in probe_since, counted from one",
      s["fee"] == "0.01" and s["confirmed"] is False and (s["probe_kind"], s["probe_since"], s["probe_tries"]) == ("refused", "feed_import_20261114T1240Z.json", 1), s)
_fq = "AdvancedMD answered a fault but kept the visit - William looks (chart pat7009, visit vst70, feed_import_20261111T1240Z.json)"
s = state([(RN("20261111T1240Z"), {"created": [], "failed": [FAILED(stored=[["99309", "11/10/2026"], ["1123F", "11/10/2026"]])], "quality_gate": {"fee": "0.00", "probe": _fq, "probe_kind": "fault", "probe_since": "feed_import_20261111T1240Z.json", "probe_tries": 1}})], files=FREE70())
check("ledger (2.4): the run that met a fault wrote the cause into its own gate, and the next run reads the same failed row again - the same sentence is the same cause: counted ONCE", s["probe"] == _fq and s["probe_tries"] == 1 and s["probe_kind"] == "fault" and s["budget"] == 1, s)
s = state([(RN("20261112T1240Z"), {"created": [], "quality_gate": {"zero_not_billed": True, "fee": "0.01"}})]); s2 = state([(RN("20261112T1240Z"), {"created": [], "quality_gate": {"fee": "0.01"}})])
check("ledger (open point 1, way c): at one cent with nothing proven the code ALWAYS probes - also when no register shows what moved the amount (a gate written before 11/12/2026, or a register that never arrived): one line a run, never a round of three",
      all(x_["fee"] == "0.01" and x_["budget"] == 1 and x_["probe"] == "new lines carry $0.01 and no one-cent line is seen billed yet - one line a run until one is billed" and x_["probe_tries"] == 1 and x_["off"] == "" for x_ in (s, s2))
      and (s["probe_kind"], s2["probe_kind"]) == ("left_off", "refused"), (s, s2))
world(c12=BILLED); s = state([R1], files={"n620": True, "n620_seen": "11/30/2026"}); _g1 = ci.quality_gate(); s2 = state([R1], files={"n620": True}); s3 = state([R1], files={"n620_seen": "11/30/2026"})
check("ledger (2.4): n620_seen - the date a person wrote into the remittance file is carried in the gate (for the report's 'remark N620 seen on ...'); empty when the file names none, and when the file is not there",
      s["n620"] is True and s["n620_seen"] == "11/30/2026" and _g1["n620_seen"] == "11/30/2026" and s2["n620_seen"] == "" and s3["n620"] is False and s3["n620_seen"] == "", (s["n620_seen"], s2["n620_seen"], s3["n620_seen"]))
open(os.path.join(REGDIR, "quality_n620_seen.json"), "w").write('{"seen": " 11/30/2026 "}'); _f1 = ci.quality_files("x"); open(os.path.join(REGDIR, "quality_n620_seen.json"), "w").write("[1]"); _f2 = ci.quality_files("x"); rmreg("quality_n620_seen.json")
check("remittance file (2.4): what a person wrote as 'seen' is read (spaces trimmed, 40 characters); a file that names no date gives none - and reading it is never a problem file",
      _f1["n620"] is True and _f1["n620_seen"] == "11/30/2026" and _f1["problems"] == [] and _f2["n620"] is True and _f2["n620_seen"] == "" and _f2["problems"] == [], (_f1["n620_seen"], _f1["problems"], _f2["n620_seen"], _f2["problems"]))
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
check("live run 1: the register records where the quality code stands (round 1 at $0.00, three lines entered and not decided, nothing known yet; not probing, not paused, no visit stuck)", reg["quality_gate"] == {"code": "1123F", "fee": "0.00", "confirmed": False, "proof": None, "zero_not_billed": False,
      "off": "", "off_until_reset": "", "wait": False, "pending": [], "pending_since": "", "billed_lines": [], "void_lines": [], "left_off_lines": [], "dead_zero_lines": [], "reset": False, "reset_after": None,
      "round": {"n": 1, "fee": "0.00", "since": "feed_import_SELFTEST.json", "lines": 3, "void": 0, "open": 3}, "budget": 3, "pilot_cap": 3, "n620": False, "history_shows_line": None, "refused_charts": [], "not_renewed": {},
      "billed_on": {}, "code_text_lines": [], "left_off_seen": {}, "left_off_on": {}, "late_billed": {}, "late_rows": [], "wrong_code_text": "", "proof_wait": None, "medicare_answer": None, "medicare_wait": None,
      "quality_skipped_hospital": 0, "unread": [], "unread_prev": [], "probe": "", "probe_kind": "", "probe_since": "", "probe_words": "", "probe_tries": 0, "paused": "", "stuck": [], "open_lines": [], "standing_restart": None,
      "taken_lines": [], "wrong_code_charge": "", "n620_seen": "", "left_off_cent": [], "proof_aside": None, "notes": []}, reg.get("quality_gate"))
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
      and "at most 10 a run (a quality line was seen billed; no Medicare payment line is posted yet on the billed lines the import reads - lines added after proof are not read back)" in qline(out) and "pilot" not in qline(out)
      and "Medicare has not yet shown" not in qline(out), (sorted(got), reg3["quality_gate"], qline(out)))
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
# AdvancedMD bills a visit but leaves its $0.00 line off the claim, and no $0.00 line of the round is billed -> one cent, and there the code PROBES: one line a run until one is billed (11/12/2026; before, a new round of three)
clear_regs(); keep(RUN1, "20261111T0100Z"); BILLS.clear(); BILLS[FIRST[0]] = ["11/11/2026"]
CHART.update({r["pid"][3:]: [("99309", "10/03/2026"), ("99309", "11/02/2026"), ("1123F", "11/02/2026")] for r in qrows})      # the chart history lists the $0.00 lines
out, regz = live(visits("20261109", (1, 2, 3, 4))); qz = qrows_of(regz); gz = regz["quality_gate"]
check("a visit was billed WITHOUT its $0.00 quality line and no $0.00 line is billed -> new lines carry one cent and the code probes; the register says why and lists ONLY the line that was read as left off (SM-1)", gz["fee"] == "0.01" and gz["zero_not_billed"] is True
      and gz["confirmed"] is False and gz["wait"] is False and gz["dead_zero_lines"] == [[qrows[0]["pid"], qrows[0]["visit"], qrows[0]["quality_charge"]]] and gz["left_off_lines"] == [qrows[0]["quality_charge"]]
      and any("without its $0.00 quality line" in n for n in gz["notes"]) and gz["round"]["n"] == 2 and gz["round"]["fee"] == "0.01" and gz["probe_kind"] == "left_off" and gz["off"] == "" and gz["off_until_reset"] == ""
      and "probing: one line a run until one is seen billed" in qline(out) and "pilot" not in qline(out), (gz, qline(out)))
check("... ONE one-cent line in that run, not three: the patient whose $0.00 line was read as left off gets NO line for 30 days after it was called left off (K12, November 12, 2026 - fix round 1: AdvancedMD may still bill that line); "
      "the two patients whose $0.00 lines are not decided yet are not coded a second time; the fourth, who never had one, carries the run's one line",
      [r["pid"] for r in qz] == ["pat404"] and qz[0]["quality_fee"] == "0.01" and gz["round"]["lines"] == 1 and len(regz["created"]) == 4, [r["pid"] for r in qz])
check("... and the one-cent line is what was sent", sum(1 for b_ in POSTS if re.search(r'proccode="pcode65441" cobcode="" pos="\d+" tos="01" units="1" netfee="0" fee="0.01" allowed="0.01"', b_)) == 1 and sum(1 for b_ in POSTS if "pcode65441" in b_) == 1, [b_[-300:] for b_ in POSTS if "pcode65441" in b_])
keep(regz, "20261112T0100Z"); PZ = [num(r["quality_charge"]) for r in qz]; FZ = [num(r["charges"][0]) for r in qz]
out, regz2 = live(visits("20261116", (1, 2, 3, 4)))
check("one cent, nothing billed yet: the probe waits for its ONE line - no new line. The two other $0.00 lines are read until they are decided (every $0.00 line is read in the end), and the line read as left off is read again after them (13.1b), still left off", qrows_of(regz2) == [] and regz2["quality_gate"]["wait"] is True
      and regz2["quality_gate"]["fee"] == "0.01" and len(regz2["quality_gate"]["pending"]) == 1 and regz2["quality_gate"]["pending_since"] == "feed_import_20261112T0100Z.json" and DETAILS.count(PIL[0]) == 1 and PIL[1] in DETAILS and PIL[2] in DETAILS
      and DETAILS.index(PIL[0]) > max(DETAILS.index(PIL[1]), DETAILS.index(PIL[2])) and regz2["quality_gate"]["left_off_lines"] == ["charge" + PIL[0]] and all(c in DETAILS for c in PZ)
      and "probing: waiting for the outcome of 1 earlier line(s) - none added" in qline(out), (regz2["quality_gate"], DETAILS, qline(out)))
keep(regz2, "20261116T0100Z"); BILLS[PZ[0]] = ["11/17/2026"]; BILLS[FIRST[1]] = ["11/17/2026"]; BILLS[PIL[2]] = ["11/17/2026"]      # the one-cent line billed; of the two $0.00 lines one visit went out without its line, the other with it
out, regz3 = live(visits("20261123", (1, 2, 3, 4)))
check("the one-cent line is billed: proven at one cent, the probe is over. The patients of the two $0.00 lines read as left off get no line for 30 days after that (K12, fix round 1: AdvancedMD may still bill them); the $0.00 line read as billed counts for its patient; the patient of the proven line is coded; nobody is coded twice", regz3["quality_gate"]["confirmed"] is True
      and regz3["quality_gate"]["probe"] == "" and regz3["quality_gate"]["fee"] == "0.01" and qrows_of(regz3) == [] and sorted(regz3["quality_gate"]["left_off_lines"]) == sorted([qrows[0]["quality_charge"], qrows[1]["quality_charge"]])
      and qrows[2]["quality_charge"] in regz3["quality_gate"]["billed_lines"] and len(regz3["quality_gate"]["dead_zero_lines"]) == 2, ([r["pid"] for r in qrows_of(regz3)], regz3["quality_gate"]))
clear_regs(); keep(RUN1, "20261111T0100Z"); keep(regz, "20261112T0100Z"); BILLS.clear(); BILLS[FZ[0]] = ["11/13/2026"]
out, regz4 = live(visits("20261116", (4, 5))); gz4 = regz4["quality_gate"]
check("a visit is billed without its ONE-CENT line too: the code goes on PROBING - it no longer switches itself off (11/12/2026). The register says why (AdvancedMD leaves the line off the claim: that needs a setting in AdvancedMD); the left-off line is decided, so this run adds its one line "
      "- not to the patient of the left-off line (K12, fix round 1: no line for him for 30 days, AdvancedMD may still bill it) but to the next eligible visit",
      [r["pid"] for r in qrows_of(regz4)] == ["pat405"] and "without its one-cent quality line too" in gz4["probe"] and gz4["probe_kind"] == "left_off" and gz4["off"] == "" and gz4["off_until_reset"] == "" and len(regz4["created"]) == 2
      and gz4["left_off_cent"] == [qz[0]["visit"]] and "PROBING - AdvancedMD billed visit" in out and "probing: one line a run until one is seen billed" in qline(out) and "off until William restarts it" not in qline(out) and "pilot" not in qline(out), (gz4, out[-300:]))
keep(regz4, "20261116T0100Z"); BILLS.clear(); [BILLS.__setitem__(c, {"void": "1"}) for c in PIL + PZ + [num(r["quality_charge"]) for r in qrows_of(regz4)]]
out, regz5 = live(visits("20261117", (5, 6, 7)))
_lo4 = [num(c) for c in gz4["left_off_lines"]]
check("... (SM-4) the probe is remembered: after somebody has voided the lines the next run does NOT start a new pilot of three by itself - ONE line, still at one cent, still probing; the lines read as left off are read again (13.1b) - found void, they are no longer listed as left off",
      len(qrows_of(regz5)) == 1 and qrows_of(regz5)[0]["quality_fee"] == "0.01" and len(regz5["created"]) == 3 and regz5["quality_gate"]["probe"] != "" and regz5["quality_gate"]["off_until_reset"] == "" and _lo4 and set(_lo4) <= set(DETAILS)
      and regz5["quality_gate"]["left_off_lines"] == [] and set(regz5["quality_gate"]["void_lines"]) >= set("charge" + c for c in _lo4) and "probing: one line a run until one is seen billed" in qline(out), (regz5["quality_gate"], DETAILS, qline(out)))
# somebody takes the pilot's lines off / the whole visits are voided
BILLS.clear(); BILLS[PIL[0]] = {"void": "1"}; BILLS[PIL[1]] = {"void": "1"}; BILLS[PIL[2]] = {"void": "1"}; clear_regs(); keep(RUN1, "20261111T0100Z"); charts0()
out, regv = live(visits("20261109", (4,))); gv = regv["quality_gate"]
check("somebody took the pilot's lines off their visits (void) while the visits are still there: those three patients get no line again this year and the code STAYS ON (11/12/2026; before, off until a restart) - no new pilot of three: it probes, ONE line",
      [r["pid"] for r in qrows_of(regv)] == ["pat404"] and len(regv["created"]) == 1 and gv["off"] == "" and gv["off_until_reset"] == "" and gv["probe"].startswith("3 earlier quality line(s) were taken off their visits") and gv["probe_kind"] == "voided"
      and sum("a person decided" in n for n in gv["notes"]) == 3 and sorted(gv["void_lines"]) == sorted(r["quality_charge"] for r in qrows) and sorted(gv["taken_lines"]) == sorted(r["quality_charge"] for r in qrows)
      and sorted(gv["refused_charts"]) == sorted([r["pid"], "2026"] for r in qrows) and "probing: one line a run until one is seen billed" in qline(out), (gv, qline(out)))
keep(regv, "20261112T0100Z"); out, regv2 = live(visits("20261110", (1, 4)), env="reset")
check("... QUALITY_CODE=reset while the code probes is ignored, loudly (only William's own stop is ended by his reset): no new round, the probe waits for its one line, and the patient whose line a person took off is NOT due again",
      qrows_of(regv2) == [] and len(regv2["created"]) == 2 and regv2["quality_gate"]["reset"] is False and regv2["quality_gate"]["wait"] is True and regv2["quality_gate"]["round"]["n"] == 1 and "NOTHING TO RESTART" in qline(out), (regv2["quality_gate"], qline(out)))
keep(regv2, "20261113T0100Z"); out, regv3 = live(visits("20261114", (5,)), env="stop")
keep(regv3, "20261114T0100Z"); out, regv4 = live(visits("20261115", (1, 5, 6)), env="reset")
check("... after William's own stop, QUALITY_CODE=reset starts the pilot again at $0.00 (a round of up to three); the patient whose line a person took off still gets none this year",
      qrows_of(regv3) == [] and "stopped on William's word" in regv3["quality_gate"]["off_until_reset"] and {r["pid"] for r in qrows_of(regv4)} == {"pat405", "pat406"} and regv4["quality_gate"]["off"] == "" and regv4["quality_gate"]["reset"] is True
      and regv4["quality_gate"]["reset_after"] == [0, 0] and regv4["quality_gate"]["round"]["n"] == 2 and regv4["quality_gate"]["probe"] == "" and regv4["quality_gate"]["budget"] == 3, (regv4["quality_gate"], [r["pid"] for r in qrows_of(regv4)]))
BILLS.clear(); [BILLS.__setitem__(c, {"void": "1"}) for c in PIL + FIRST]; clear_regs(); keep(RUN1, "20261111T0100Z"); charts0()
out, regw = live(visits("20261109", (1, 2, 3, 4)))
check("the pilot's whole visits were voided: no outcome either way - their places are free, the round carries on with three more visits, and those patients are due again", len(qrows_of(regw)) == 3 and regw["quality_gate"]["off"] == "" and regw["quality_gate"]["wait"] is False
      and regw["quality_gate"]["confirmed"] is False and sum("no longer on the chart (void)" in n for n in regw["quality_gate"]["notes"]) == 3 and {r["pid"] for r in qrows_of(regw)} <= {"pat401", "pat402", "pat403", "pat404"}
      and regw["quality_gate"]["round"] == {"n": 1, "fee": "0.00", "since": "feed_import_20261111T0100Z.json", "lines": 6, "void": 3, "open": 3} and regw["quality_gate"]["budget"] == 3, regw["quality_gate"])
keep(regw, "20261112T0100Z"); [BILLS.__setitem__(num(c), {"void": "1"}) for r in qrows_of(regw) for c in r["charges"]]; charts0()
out, regw2 = live(visits("20261113", (5, 6, 7)))
check("... and when the three replacement visits are voided as well, the round has had its six lines: the code PROBES ('the pilot's lines keep being voided') - ONE line a run; it no longer switches itself off", [r["pid"] for r in qrows_of(regw2)] == ["pat405"] and len(regw2["created"]) == 3
      and "the pilot's lines keep being voided" in regw2["quality_gate"]["probe"] and regw2["quality_gate"]["off_until_reset"] == "" and "PROBING - the pilot's lines keep being voided" in qline(out), (regw2["quality_gate"], qline(out)))
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
CHART["412"] = [("99309", "10/03/2026"), ("1123F", "11/02/2026"), ("M0004", "11/02/2026")]; ci._ctx.clear(); DETAILS.clear(); ci.chart_ctx("pat412")
check("chart context (8.6, F1): the M0004 line is never the sample either - the ordinary charge is, although the no-charge lines are newer (its detail may not answer: the next visit would lose its episode and referral plan)", DETAILS == ["1"], DETAILS)
ci._ctx.clear(); DETAILS.clear()
clear_regs()
# F5 (confirm review, attack A2): the run is cut right after the first pilot visit's charge call came back with its line stored, before the register was
# written; then the same command again under the same stamp. The provisional row written before that call tells the second start that a line may exist
# that no row records: that visit is for a person, this stamp has had its try - the second start adds NO line - and from the next run the code probes
# (11/12/2026; before, off until William had looked at that visit). Never a fourth unproven line. The visits themselves still go in.
class _Cut(BaseException): pass
_CUT = {"chart": "", "n": 0}; _post_real = amd.post
def _cut_post(body, timeout=0):
    if "getdemographic" in body: _CUT["chart"] = re.search(r'patientid="pat(\d+)"', body).group(1)
    r_ = _post_real(body, timeout)
    if 'action="updvisitwithnewcharges"' in body and "pcode65441" in body and _CUT["n"] == 0:
        _CUT["n"] = 1; CHART.setdefault(_CUT["chart"], []).extend([("99309", "11/02/2026"), ("1123F", "11/02/2026")]); raise _Cut()
    return r_
earlier(); clear_regs(); charts0(); amd.post = _cut_post
try: live(QB, keep_own=True); _was_cut = False
except _Cut: _was_cut = True
finally: amd.post = _post_real
_creg = os.path.join(REGDIR, "feed_import_SELFTEST.json"); _reg_cut = json.load(open(_creg)) if os.path.exists(_creg) else {}
out, reg_c2 = live(QB)
check("F5 (confirm review A2): a run cut while the first pilot visit's call was out leaves a provisional row; the second start under the same stamp adds NO line (this stamp has had its try, and that visit is for a person) - never four unproven lines; the other visits go in",
      _was_cut is True and [r_.get("provisional") for r_ in _reg_cut.get("failed", [])] == [True] and qrows_of(reg_c2) == [] and "the run was cut while a call that carried the quality line was out" in reg_c2["quality_gate"]["probe"]
      and reg_c2["quality_gate"]["probe_kind"] == "fault" and reg_c2["quality_gate"]["off_until_reset"] == "" and reg_c2["quality_gate"]["budget"] == 0
      and len(reg_c2["created"]) == 4 and any(r_.get("why") == "all lines already in AMD" for r_ in reg_c2["skipped"]), (_was_cut, _reg_cut.get("failed"), reg_c2.get("quality_gate"), [r_.get("pid") for r_ in reg_c2["created"]]))
out, reg_c3 = live(visits("20261103", (2,)))
check("F5: ... and a run that is NOT cut leaves no provisional row behind (the row goes once the answer is recorded)", len(qrows_of(reg_c3)) == 1 and not any(r_.get("provisional") for r_ in reg_c3.get("failed", [])), (qrows_of(reg_c3), reg_c3.get("failed")))
keep(_reg_cut, "20261102T0100Z"); out, reg_c4p = live(visits("20261104", (5,)))
check("F5 (K11, fix round 1): ... the run AFTER the cut pauses - the visit whose call was out may carry the line, and no inspector step has looked at it yet: it is listed under 'stuck' with fault true, no line is added, nothing is off",
      qrows_of(reg_c4p) == [] and [x_.get("fault") for x_ in reg_c4p["quality_gate"]["stuck"]] == [True] and reg_c4p["quality_gate"]["off_until_reset"] == "" and "paused: no line in this run" in qline(out)
      and reg_c4p["quality_gate"]["paused"].startswith("paused this run: visit %s (chart pat401) came from a fault run - the run was cut" % _reg_cut["failed"][0]["empty_visit"]), (reg_c4p["quality_gate"], qline(out)))
keep(reg_c4p, "20261104T0100Z"); step_frees("20261104T0100Z", _reg_cut["failed"], "feed_import_20261102T0100Z.json"); out, reg_c4 = live(visits("20261105", (3, 4))); rmreg("feed_inspector_20261104T0100Z.json")
check("F5: ... and once that run's inspector step found the visit not held, the run after it probes by itself: one line on its first eligible visit, and the sentence says the run was cut - nobody restarts anything", [r_["pid"] for r_ in qrows_of(reg_c4)] == ["pat403"] and len(reg_c4["created"]) == 2
      and "the run was cut while a call that carried the quality line was out" in reg_c4["quality_gate"]["probe"] and reg_c4["quality_gate"]["off_until_reset"] == "" and "probing: one line a run until one is seen billed" in qline(out) and reg_c4["quality_gate"]["stuck"] == [], (reg_c4["quality_gate"], qline(out)))
clear_regs(); charts0()
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
check("refused: ... but the refused patient's own next visit this year carries no line (one try per patient and year); at one cent the code probes, one line a run", lined(dry) == [] and ("pat40%s" % ref[0]["pid"][-1], "2026") in ci.QUALITY["done"] and ci.QUALITY["budget"] == 1 and ci.QUALITY["probe_kind"] == "refused", (dry, ci.QUALITY["done"]))
reg6 = json.loads(json.dumps(reg5)); [r.update(quality_refused_fee="0.01") for r in reg6["created"] if r.get("quality_refused")]
keep(reg6, "20261114T0100Z"); ci.PARSED[:] = visits("20261117", (2,)); out, dry = run_dry()
check("refused at one cent too: the code goes on PROBING - one line a run, and every run says why (11/12/2026; before, off until William said to start again)", ci.QUALITY["off"] == "" and ci.QUALITY["off_until_reset"] == "" and lined(dry) == ["pat402"] and ci.QUALITY["budget"] == 1
      and "PROBING - AdvancedMD refused a visit that carried the code with a one-cent charge too (feed_import_20261114T0100Z.json)" in out and "probing: one line a run until one is seen billed" in qline(out), out[-400:])
out, regr0 = live(visits("20261117", (6,)), env="reset")
check("QUALITY_CODE=reset while the code probes: ignored, loudly - the probe goes on at one cent with its one line", regr0["quality_gate"]["reset"] is False and regr0["quality_gate"]["fee"] == "0.01" and [r["quality_fee"] for r in qrows_of(regr0)] == ["0.01"]
      and "NOTHING TO RESTART" in qline(out), (regr0["quality_gate"], qline(out)))
out, regs0 = live(visits("20261116", (9,)), env="stop"); keep(regs0, "20261116T0100Z")
out, regr = live(visits("20261117", (2,)), env="reset")
check("QUALITY_CODE=reset (William's word) after his own stop: the pilot starts again at $0.00 and the register records the restart", qrows_of(regs0) == [] and regr["quality_gate"]["reset"] is True and regr["quality_gate"]["off"] == "" and regr["quality_gate"]["fee"] == "0.00"
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
check("... (SM-5) that visit is for a person, and from the next run the code PROBES (11/12/2026; before, off until William had looked): the register says so with the chart and the visit, and nothing is off until a restart",
      regq["quality_gate"]["probe"] == "AdvancedMD answered a fault but kept the visit - William looks (chart pat401, visit %s, feed_import_SELFTEST.json)" % f[0]["empty_visit"] and regq["quality_gate"]["probe_kind"] == "fault"
      and regq["quality_gate"]["off_until_reset"] == "" and regq["quality_gate"]["confirmed"] is False and regq["quality_gate"]["refused_charts"] == [["pat401", "2026"]], regq["quality_gate"])
keep(regq, "20261103T0100Z"); charts0(); step_frees("20261103T0100Z", regq["failed"], "feed_import_20261103T0100Z.json"); out, regq3 = live(visits("20261104", (3, 4, 5))); rmreg("feed_inspector_20261103T0100Z.json")      # (K11) that run's step found the visit not held
check("... (SM-5) the next run probes: ONE line on its first eligible visit, no further failed visit, and the log line says what the probe is about", [r["pid"] for r in qrows_of(regq3)] == ["pat403"] and regq3["failed"] == [] and len(regq3["created"]) == 3
      and sum(1 for b_ in POSTS if "pcode65441" in b_) == 1 and "AdvancedMD answered a fault but kept the visit - William looks (chart pat401" in regq3["quality_gate"]["probe"] and regq3["quality_gate"]["off_until_reset"] == ""
      and "PROBING - AdvancedMD answered a fault but kept the visit" in qline(out) and "probing: one line a run until one is seen billed" in qline(out), (regq3["quality_gate"], qline(out)))
keep({k_: v_ for k_, v_ in regq.items() if k_ != "quality_gate"}, "20261103T0100Z"); charts0(); out, regq5 = live(visits("20261104", (3, 4, 5)))
check("... (SM-5) also when that run was cut off before it wrote its gate (and so before its inspector step could look): the failed row alone begins the probe, the sentence names the register it stands in, and the visit is listed as stuck "
      "(K11, fix round 1) - this run pauses until a step has looked at it",
      qrows_of(regq5) == [] and len(regq5["created"]) == 3 and [x_["visit"] for x_ in regq5["quality_gate"]["stuck"]] == [f[0]["empty_visit"]] and regq5["quality_gate"]["budget"] == 0
      and regq5["quality_gate"]["probe"] == "AdvancedMD answered a fault but kept the visit - William looks (chart pat401, visit %s, feed_import_20261103T0100Z.json)" % f[0]["empty_visit"] and regq5["quality_gate"]["probe_tries"] == 1
      and regq5["quality_gate"]["off_until_reset"] == "", regq5["quality_gate"])
clear_regs(); charts0(); _cl = ci.chart_lines_now; _tries = []
def _never(pid): _tries.append(pid); raise RuntimeError("history down")
ci.chart_lines_now = _never; out, regq2 = live(visits("20261102", (1,)), refuse_quality=True); ci.chart_lines_now = _cl
check("refused and the chart cannot be read in three tries: not sent again either - that visit is for a person, and the code probes from the next run", len(regq2["failed"]) == 1 and regq2["created"] == [] and "chart not read" in str(regq2["failed"][0]["stored"]) and len(_tries) == 3
      and regq2["quality_gate"]["probe"].startswith("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (chart pat401") and regq2["quality_gate"]["off_until_reset"] == "", (regq2["failed"], _tries, regq2["quality_gate"]))
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
      and sum(1 for b_ in POSTS if "pcode65441" in b_) == 1 and "ended in an error (TimeoutError)" in regu["quality_gate"]["off"] and "nobody knows whether AdvancedMD kept that visit - William looks (chart pat401" in regu["quality_gate"]["probe"]
      and regu["quality_gate"]["off_until_reset"] == "", (fu, regu["quality_gate"]))
check("... (K11; K17, fix round 2) and THIS run's own gate lists that visit under 'stuck' at once (fault true, the visit, the chart, the amount, nobody has seen it yet), so this run's inspector step already looks at it",
      [(x_.get("fault"), x_.get("visit"), x_.get("chart"), x_.get("fee")) for x_ in regu["quality_gate"].get("stuck") or []] == [(True, fu[0]["empty_visit"], "pat401", "0.00")]
      and regu["quality_gate"]["stuck"][0]["what"].startswith("the call that carried the line ended in an error - nobody has seen yet"), regu["quality_gate"].get("stuck"))
keep(regu, "20261103T0100Z"); ci.PARSED[:] = visits("20261104", (4,)); step_frees("20261103T0100Z", regu["failed"], "feed_import_20261103T0100Z.json"); out, dry = run_dry(); rmreg("feed_inspector_20261103T0100Z.json")      # (K11) that run's step found the visit not held
check("... that visit is for a person, and the next run PROBES with one line (11/12/2026; before, off until William had looked at that visit)", lined(dry) == ["pat404"] and "nobody knows whether AdvancedMD kept that visit" in ci.QUALITY["probe"] and ci.QUALITY["probe_kind"] == "fault"
      and ci.QUALITY["budget"] == 1 and ci.QUALITY["off_until_reset"] == "", ci.QUALITY)
keep({k_: v_ for k_, v_ in regu.items() if k_ != "quality_gate"}, "20261103T0100Z"); out, dry = run_dry()
check("... also from the failed row alone (that run cut off before it wrote its gate, so before its step could look): the probe names the register, and the visit is listed as stuck - no line until a step has looked at it (K11, fix round 1)",
      lined(dry) == [] and "feed_import_20261103T0100Z.json" in ci.QUALITY["probe"] and "chart pat401" in ci.QUALITY["probe"] and ci.QUALITY["off_until_reset"] == "" and [x_.get("fault") for x_ in ci.QUALITY["stuck"]] == [True], ci.QUALITY)
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
check("M0004 ledger (13.1d): three days after - LEFT OFF: listed, that clinician gets it once more - 30 days after it was called left off (K12, November 12, 2026 - fix round 1: it may still be billed until then; not waiting, but no new M0004 line before), and one left-off line does not switch M0004 off",
      s["left_off_lines"] == ["charge713"] and ("prof13", "2026") not in s["wait"] and ("prof13", "2026") in s["done"] and s["off"] == "" and s["left_off_on"] == {"charge713": {"on": "11/21/2026", "billed": "11/18/2026"}} and s["clinicians"]["prof13"]["state"] == "left off", s)
_G21k = mnext("20261121T1240Z"); s29 = mstate([M1, _G21k], day=D_(12, 20)); s30 = mstate([M1, _G21k], day=D_(12, 21))
_sf = mstate([M1], day=D_(11, 21), files={"removed": {"20261116T1240Z": [("feed_inspector_20261116T1240Z.json", {"visit": "75", "pid": "pat7105", "charge": "charge752", "code": "M0004", "void_ok": True, "released": True, "fault": True, "with": "1123F", "why": "x"})]}})
s = mstate([M1], day=D_(11, 21))      # (the state the checks below go on from)
check("M0004 ledger (K11, fix round 1): an M0004 entry about a visit of a fault run (fault true) is the 1123F ledger's business - the M0004 ledger reads nothing from it (no note about a charge no row carries, no probe)",
      not any("passed over" in n_ for n_ in _sf["notes"]) and _sf["probe"] == s["probe"], _sf["notes"])
check("M0004 ledger (K12, fix round 1): ... 29 days after it was called left off that clinician still gets no new M0004 line; on the 30th day he gets it once more, as before",
      ("prof13", "2026") in s29["done"] and ("prof13", "2026") not in s30["done"] and ("prof13", "2026") not in s30["wait"] and s30["left_off_lines"] == ["charge713"], (s29["done"], s30["done"]))
G21 = mnext("20261121T1240Z"); MA2 = mrow("pat7103", "vst73", "charge731", "charge732", "charge733"); chg("731", ["11/22/2026"], "pcode65119"); chg("733", [], MP); chg("732", [], QP)
s = mstate([M1, G21, (RN("20261122T1240Z"), {"created": [MA2]})], day=D_(11, 26))
check("M0004 ledger (8.3): the physician's second M0004 line is left off too - TWO left-off lines since the last start: M0004 PROBES (11/12/2026; before, off until a restart) - the sentence names the visits; no M0004 line while the other clinician's line is not decided",
      sorted(s["left_off_lines"]) == ["charge713", "charge733"] and s["probe"].startswith("AdvancedMD left the M0004 line off 2 claims since the option code was last started (visits vst71, vst73)") and s["off"] == "" and s["off_until_reset"] == ""
      and s["probe_since"] == "feed_import_20261122T1240Z.json" and s["budget"] == 0 and s["wait"] == {("prof15", "2026")}, s)
mworld(c711=["11/18/2026"]); mstate([M1], day=D_(11, 21)); G21 = mnext("20261121T1240Z"); chg("713", ["11/25/2026"], MP); s = mstate([M1, G21], day=D_(11, 27))
check("M0004 ledger (13.1b): a left-off M0004 line is read again - billed later, it moves to the billed lines: that clinician is done for the year, and the gate's late row says so",
      s["billed_lines"] == ["charge713"] and s["left_off_lines"] == [] and ("prof13", "2026") in s["done"] and s["late_billed"] == {"charge713": "11/27/2026"} and s["late_rows"] == [["prof13", "pat7101", "vst71", "charge713", "11/21/2026", "", "2026"]], s)
_s27 = mstate([M1, G21], day=D_(11, 27)); G27 = mnext("20261127T1240Z"); s = mstate([M1, G21, G27], day=D_(11, 28))
check("M0004 ledger (13.1b, F3 - the confirm review's behaviour om): ... the NEXT gate does not list that billed line as left off again (the digest lists left_off_lines as they stand): one state per line, the newest reading",
      s["left_off_lines"] == [] and "charge713" in s["billed_lines"] and ("prof13", "2026") in s["done"], (s["left_off_lines"], s["billed_lines"]))
MA3 = mrow("pat7106", "vst76", "charge761", "charge762", "charge763"); chg("761", [], "pcode65119"); chg("762", [], QP); chg("763", [], MP)
s = mstate([M1, G21, (RN("20261122T1240Z"), {"created": [MA3]})], day=D_(11, 27))
check("M0004 ledger (13.1b, F4): a left-off M0004 line billed later while that clinician's LATER M0004 line is not billed - the late row names no second billed line", s["late_rows"] == [["prof13", "pat7101", "vst71", "charge713", "11/21/2026", "", "2026"]], s["late_rows"])
chg("713", [], MP); s = mstate([M1, G21], day=D_(12, 19)); _d19 = list(DETAILS); s22 = mstate([M1, G21], day=D_(12, 22))
check("M0004 ledger (13.1b; K13, fix round 2): ... read again until 30 days after it was CALLED left off (11/21): still read on 12/19, no longer on 12/22",
      "713" in _d19 and "713" not in DETAILS and s["left_off_lines"] == ["charge713"] and s22["left_off_lines"] == ["charge713"], (s["left_off_lines"], _d19, DETAILS))
mworld(c711=["not a date"]); s = mstate([M1], day=D_(11, 18)); G18 = mnext("20261118T1240Z")
check("M0004 ledger (13.1d): a visit listed as billed whose billed date cannot be read - the gate remembers the day the import first saw it billed and counts from that day", s["left_off_lines"] == [] and s["left_off_seen"] == {"charge713": "11/18/2026"} and ("prof13", "2026") in s["wait"], s)
s = mstate([M1, G18], day=D_(11, 20)); s3 = mstate([M1, G18], day=D_(11, 21))
check("M0004 ledger (13.1d): ... two days later still not decided (the first day seen is kept, not moved to each run's day), three days later left off", s["left_off_lines"] == [] and s["left_off_seen"] == {"charge713": "11/18/2026"} and s3["left_off_lines"] == ["charge713"] and s3["left_off_seen"] == {}, (s, s3))
mworld(); TEXTOF["713"] = "99497"; s = mstate([M1], day=D_(11, 20)); GTXT = mnext("20261120T1240Z")
check("M0004 ledger (13.4): the charge detail names procedure id pcode692183 with another code text - M0004 is PAUSED for this run (11/12/2026; before, off until a restart): the sentence says what AdvancedMD shows, the gate records the text and the charge, and nothing probes",
      s["off"] == "paused this run: AdvancedMD shows procedure id pcode692183 as 99497, not M0004 - no M0004 line while that is so; every run reads it again" and s["paused"] == s["off"] and s["wrong_code_text"] == "99497" and s["wrong_code_charge"] == "charge713"
      and s["off_until_reset"] == "" and s["probe"] == "", s)
s = mstate([M1, GTXT], day=D_(11, 21)); _d = list(DETAILS); TEXTOF.clear(); s2 = mstate([M1, GTXT], day=D_(11, 21))
check("M0004 ledger (13.4): ... the next run reads THAT charge again first and is paused while it still shows the other text; the first run that reads M0004 there goes on by itself where it stood",
      s["paused"] != "" and s["paused"] == s["off"] and _d[:1] == ["713"] and s2["paused"] == "" and s2["off"] == "" and s2["wrong_code_text"] == "" and s2["wait"] == {("prof13", "2026"), ("prof15", "2026")}, (s, _d, s2))
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
check("M0004 ledger (11.6): the inspector step took the M0004 line off a held visit that then went through - void and final, NOT read; M0004 PROBES (11/12/2026; before, off until a restart, no second try): the claim check's own words are kept; no M0004 line while the other clinician's line is not decided",
      s["void_lines"] == ["charge713"] and "713" not in DETAILS and s["probe"] == 'the routine took the M0004 line off held visit vst71 and the visit went through without it (feed_inspector_20261116T1240Z.json: "Pattern 88001: procedure M0004 is not payable")'
      and s["probe_words"] == "Pattern 88001: procedure M0004 is not payable" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 0, s)
_RM = (RN("20261116T1240Z"), {"created": [MA_]})
s = state([_RM], files=MREM()); s2 = state([_RM], files={"removed": {"20261116T1240Z": MREM()["removed"]["20261116T1240Z"] + MREM(code="1123F", charge="charge712")["removed"]["20261116T1240Z"]}})
check("M0004 (11.6): an M0004 line taken off with released does NOT count against 1123F (no refusal, the amount stays, the patient is not marked refused); taken off WITH the 1123F line, the 1123F entry counts as one refusal",
      s["fee"] == "0.00" and s["refused"] == set() and "charge713" not in s["void_lines"] and s2["fee"] == "0.01" and ("pat7101", "2026") in s2["refused"] and s2["void_lines"] == ["charge712"], (s, s2))
mworld(); s = mstate([M1], files=MREM(released=False), day=D_(11, 20))
check("M0004 ledger (11.6): ... the visit stayed held anyway (not released) - the line is just void: that clinician may get M0004 again, nothing is switched off", s["void_lines"] == ["charge713"] and s["off"] == "" and ("prof13", "2026") not in s["wait"] and ("prof13", "2026") not in s["done"], s)
mworld(); s = mstate([M1], files=MREM(**{"with": "1123F"}), day=D_(11, 20))
check("M0004 ledger (NH2-1): an M0004 line taken off only because its 1123F line came off ('with': '1123F', the visit went through) - just void: M0004 is NOT switched off and that clinician may get M0004 again",
      s["void_lines"] == ["charge713"] and s["off"] == "" and ("prof13", "2026") not in s["wait"] and ("prof13", "2026") not in s["done"] and any("came off with its 1123F line" in n_ for n_ in s["notes"]), s)
MSTUCK = lambda what, why="Pattern 88001: procedure M0004 is not payable": 'paused this run: visit vst71 (chart pat7101) is held with its M0004 line - %s (feed_inspector_20261116T1240Z.json: "%s"); no new M0004 line while that is so - every run\'s inspector step tries the void and the re-save again' % (what, why)
mworld(); s = mstate([M1], files=MREM(released=False, still_named=True), day=D_(11, 20))
check("M0004 ledger (NH2-2, 8.6): the M0004 line is gone but the visit is still listed for the edit about it - the visit is STUCK with its M0004 line: M0004 is paused this run, the step re-saves the visit again in every run (one re-save should release it), and M0004 probes afterwards",
      s["paused"] == MSTUCK("the line is off, but the visit is still listed for the edit about it") and s["off"] == s["paused"] and s["off_until_reset"] == "" and [(i_["visit"], i_["code"], i_["charge"]) for i_ in s["stuck"]] == [("vst71", "M0004", "charge713")]
      and "still listed for the edit about the line" in s["probe"], s)
s = mstate([M1], files=MREM(void_ok=False, released=False), day=D_(11, 20))
check("M0004 ledger (11.6): ... the void failed - the visit is held WITH its M0004 line: STUCK - M0004 paused this run, the visit listed in the gate for the inspector step's retry pass; never off until a restart",
      s["paused"] == MSTUCK("the routine could not take the line off") and s["off_until_reset"] == "" and s["void_lines"] == [] and [(i_["visit"], i_["what"]) for i_ in s["stuck"]] == [("vst71", "the routine could not take the line off")] and ci.mvp_gate()["stuck"] == s["stuck"]
      and s["probe"].startswith("the Claim Inspector holds visit vst71 and the routine could not take its M0004 line off"), s)
_mfree = dict(MREM(void_ok=False, released=False)["removed"], **{"20261117T1240Z": [("feed_inspector_20261117T1240Z.json", {"visit": "vst71", "pid": "pat7101", "charge": "charge713", "code": "M0004", "fee": "0.00", "why": "Pattern 88001: procedure M0004 is not payable",
                                                                                     "void_ok": True, "resave_ok": True, "released": True, "retry_of": "feed_inspector_20261116T1240Z.json", "at": "x"})]})
s = mstate([M1, (RN("20261117T1240Z"), {"created": []})], files={"removed": _mfree}, day=D_(11, 20))
check("M0004 ledger (11.6): ... only a NEWER entry ends that stuck mark: the retry pass took the line off and the visit went out - not stuck, not paused; the line is void and M0004 goes on probing",
      s["stuck"] == [] and s["paused"] == "" and s["off"] == "" and s["void_lines"] == ["charge713"] and s["probe"] != "" and s["off_until_reset"] == "" and ("prof13", "2026") not in s["wait"], s)
s = mstate([M1], files=MREM(charge="charge712"), day=D_(11, 20))
check("M0004 ledger (11.6, 8.5): an M0004 entry whose charge the row recorded as its 1123F line (the two were swapped) is still this row's M0004 line - and the swap is kept", s["void_lines"] == ["charge712"] and s["swaps"] == {"charge713": "charge712"}
      and s["probe"].startswith("the routine took the M0004 line off held visit vst71 and the visit went through without it"), s)
_HELD = lambda why_: {"held": {"71": [("feed_inspector_20261116T1240Z.json", why_, False)]}}
mworld(); s = mstate([M1], files=_HELD("Pattern 88001: procedure M0004 is not payable"), day=D_(11, 20))
check("M0004 ledger (8.6): a Claim Inspector hold whose words name M0004 on a visit that carries it, with no removal recorded (the line could not be taken off) - the visit is STUCK with its M0004 line: M0004 paused this run; nothing probes from the held row itself",
      s["paused"] == MSTUCK("the Claim Inspector holds it and the line was not taken off") and s["off"] == s["paused"] and s["off_until_reset"] == "" and s["probe"] == "" and [i_["visit"] for i_ in s["stuck"]] == ["vst71"], s)
s = mstate([M1], files=_HELD("Pattern 990001: procedure 1123F - line item charge amount is zero"), day=D_(11, 20)); s2 = mstate([M1], files=_HELD("Charge amount is zero for this procedure"), day=D_(11, 20))
check("M0004 ledger (8.6): ... a hold whose words name only the 1123F line is not M0004's business; words about a zero amount that name no code name both lines - M0004 paused", s["off"] == "" and s["stuck"] == []
      and s2["paused"] == MSTUCK("the Claim Inspector holds it and the line was not taken off", "Charge amount is zero for this procedure"), (s["off"], s2["off"]))
_RP = (RN("20261116T1240Z"), {"created": [MA_], "quality_gate": {"confirmed": True, "fee": "0.00", "proof": {"visit": "vst2", "charge": "charge22"}}})
s = state([_RP], files=_HELD("Pattern 88001: procedure M0004 is not payable")); s2 = state([_RP], files=_HELD("Pattern 990001: procedure 1123F - charge amount is zero")); s3 = state([_RP], files=_HELD("Pattern 88003: M0004 charge amount is zero"))
check("M0004 (8.6): an edit that names only M0004 pauses M0004, NOT 1123F - after proof the 1123F ledger is not paused for it (also when its words speak of a zero amount: that amount is M0004's); an edit that names 1123F still makes the visit stuck for the 1123F line",
      s["off"] == "" and s["confirmed"] is True and s3["off"] == "" and s2["paused"].startswith("paused this run: visit vst71 (chart pat7101) is held with its quality line - the Claim Inspector holds it and the line was not taken off") and s2["confirmed"] is True, (s["off"], s2["off"], s3["off"]))
s = mstate([M1], files=dict(_HELD("Pattern 88001: procedure M0004 is not payable"), **MREM(released=False)), day=D_(11, 20))
check("M0004 ledger (11.6): a hold that names M0004 on a visit whose M0004 line the routine took off is the visit's own business - no OFF; the line is just void", s["off"] == "" and s["void_lines"] == ["charge713"], s)
s = state([_RM], files={"removed": {"20261116T1240Z": MREM(code="1123F", charge="charge713")["removed"]["20261116T1240Z"]}})
check("M0004 (11.3, 8.5): a 1123F entry whose charge the row recorded as its M0004 line (the two were swapped) is that row's 1123F line - void, and one refusal", s["void_lines"] == ["charge712"] and s["fee"] == "0.01" and ("pat7101", "2026") in s["refused"], s)
mworld(c711=["11/18/2026"]); chg("731", ["11/18/2026"], "pcode65119"); chg("733", [], MP); chg("732", [], QP)
_M2 = (RN("20261116T1240Z"), {"created": [MA_, MA2]}); s = mstate([_M2], day=D_(11, 22)); G22 = mnext("20261122T1240Z"); s2 = mstate([_M2, G22], reset=True, day=D_(11, 23))
check("M0004 ledger (8.3, 8.7): two lines left off - M0004 probes; MVP_CODE=reset has nothing left to restart (M0004 never switches itself off): ignored, loudly - the probe goes on",
      s["probe"].startswith("AdvancedMD left the M0004 line off 2 claims") and s["off"] == "" and s2["off"] == "" and s2["reset"] is False and "NOTHING TO RESTART - MVP_CODE=reset was ignored" in s2["loud"] and s2["probe"] == s["probe"]
      and sorted(s2["left_off_lines"]) == ["charge713", "charge733"] and s2["budget"] == 1, (s, s2))
MA4 = mrow("pat7107", "vst77", "charge771", "charge772", "charge773"); chg("771", ["11/24/2026"], "pcode65119"); chg("772", ["11/24/2026"], QP); chg("773", ["11/24/2026"], MP)
s3 = mstate([_M2, G22, (RN("20261123T1240Z"), {"created": [MA4]})], day=D_(11, 25))
check("M0004 ledger (8.3): ... the probe ends when an M0004 line entered AFTER the newest cause is read billed - from then on each clinician who has none gets one, as before", s3["probe"] == "" and "charge773" in s3["billed_lines"] and ("prof13", "2026") in s3["done"] and s3["budget"] is None, s3)
s = mstate([M1], files={"check_holds": {"71": [("feed_verify_20261116T1240Z.json", ["insorder not applied on vst71 (the visit carries the quality line charge712 and the M0004 line charge713: resave FAULT)"])]}}, day=D_(11, 20))
check("M0004 ledger (8.6): the insurance check could not set the order of a visit that carries M0004 - that visit is for a person, and M0004 probes (11/12/2026; before, off until a restart)", s["probe"].startswith("the insurance check could not set the order of visit vst71, which carries the M0004 line") and s["off"] == "" and s["off_until_reset"] == "", s)
mworld(); s = mstate([(RN("20261116T1240Z"), {"created": [dict(MA_, mvp_codes=[], mvp_charge="", mvp_refused="Fault: no", mvp_tried="0.00")]})], day=D_(11, 20))
check("M0004 ledger (8.4): a visit refused with M0004 and taken with the 1123F line only - M0004 PROBES: one M0004 line a run in all (11/12/2026; before, off until a restart - the sentence has lost its words 'no second try'); it names chart, visit and register and keeps AdvancedMD's own words",
      s["probe"] == "AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only (chart pat7101, visit vst71, feed_import_20261116T1240Z.json)" and s["probe_words"] == "Fault: no" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1 and s["lines"] == 0, s)
s = mstate([(RN("20261116T1240Z"), {"created": [dict(MA_, mvp_codes=[], mvp_charge="", mvp_not_stored="0.00")]})], day=D_(11, 20))
check("M0004 ledger: a visit stored without its M0004 line - M0004 probes", s["probe"].startswith("AdvancedMD stored a visit without its M0004 line - William looks (chart pat7101") and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1, s)
def _FM(info=None, **kw): return dict({"feed_id": "f1", "pid": "pat7101", "empty_visit": "vst79", "info": dict({"quality_tried": "0.00", "mvp_tried": "0.00", "quality_dos": "11/16/2026", "dos": "11/16/2026", "cpts": ["99309"]}, **(info or {})), "err": "x"}, **kw)
s = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM(stored=[["99309", "11/16/2026"]])]})]); s2 = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM(quality_unknown="0.00")]})])
s3 = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM(stored=[["99309", "11/16/2026"]], info={"mvp_form_refused": True})]})]); s4 = mstate([(RN("20261116T1240Z"), {"created": [], "failed": [_FM()]})])
check("M0004 ledger (8.4): a visit that carried M0004 got a fault or an error and nobody knows what AdvancedMD kept (the chart showed part of it, or a call ended in an error) - that visit is for a person and M0004 probes; when the 1123F-only form was refused too, M0004 is not blamed; an ordinary failed row says nothing",
      s["probe"].startswith("AdvancedMD answered a visit that carried M0004 with a fault or an error and nobody knows what it kept of it - William looks (chart pat7101, visit vst79") and s2["probe"] == s["probe"] and s["off"] == "" and s["off_until_reset"] == ""
      and s3["probe"] == "" and s4["probe"] == "" and s3["off"] == "" and s4["off"] == "", (s["probe"], s2["probe"], s3["probe"], s4["probe"]))
_MR = (RN("20261116T1240Z"), {"created": [dict(MA_, mvp_codes=[], mvp_charge="", mvp_refused="Fault: no", mvp_tried="0.00")]})
mworld(); _s0 = mstate([_MR], day=D_(11, 20)); GPRB = mnext("20261120T1240Z"); s = mstate([_MR, GPRB], day=D_(11, 21))
check("M0004 ledger: its probe is carried forward by its gate - the next run still probes with the same sentence: one M0004 line a run in all", s["probe"] == _s0["probe"] and s["probe"] != "" and s["off"] == "" and s["off_until_reset"] == "" and s["budget"] == 1, s)
s = mstate([_MR, GPRB], reset=True, day=D_(11, 21))
check("M0004 ledger (8.7): MVP_CODE=reset while M0004 probes - nothing to restart (M0004 never switches itself off): ignored, loudly; the probe goes on", s["reset"] is False and "NOTHING TO RESTART - MVP_CODE=reset was ignored" in s["loud"] and s["probe"] == _s0["probe"], s)
s = mstate([M1], reset=True, day=D_(11, 21))
check("M0004 ledger (8.7): MVP_CODE=reset with nothing switched off is ignored, loudly", s["reset"] is False and "NOTHING TO RESTART - MVP_CODE=reset was ignored" in s["loud"], s)
s = mstate([_MR, GPRB, (RN("20261121T1240Z"), {"created": [], "quality_gate": {"reset": True, "fee": "0.00"}})], day=D_(11, 22))
check("M0004 (8.7): a restart of the 1123F line (QUALITY_CODE=reset, written in the 1123F gate) changes nothing for M0004 - its probe goes on", s["probe"] == _s0["probe"] and s["off"] == "", s)
_was = "AdvancedMD stores procedure id pcode692183 as 99497, not M0004 - William looks"; GOLD = (RN("20261120T1240Z"), {"created": [], "mvp_gate": {"off": _was, "off_until_reset": _was, "wrong_code_text": "99497"}})
mworld(); s = mstate([M1, GOLD], day=D_(11, 21))
check("M0004 ledger (section 3): an OLDER gate that says 'off until reset' (written before 11/12/2026) is not kept - every such sentence was the code's own: M0004 goes on by itself, probing, and the run right after that gate records the standing restart",
      s["off"] == "" and s["off_until_reset"] == "" and s["probe"] == "the option code M0004 had switched itself off (%s) - William's standing word of November 11, 2026 restarts it" % _was
      and s["standing_restart"] == {"was": _was, "register": "feed_import_20261120T1240Z.json"} and s["wrong_code_text"] == "", s)
s2 = mstate([M1, GOLD, mnext("20261121T1240Z")], day=D_(11, 22))
check("M0004 ledger (section 3): ... every later run finds a gate of this version before it and says nothing more; the probe goes on", s2["standing_restart"] is None and s2["probe"] == s["probe"] and s2["off_until_reset"] == "", s2)
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
def mline(out): return next((l for l in out.splitlines() if l.startswith("QUALITY M0004:")), "")
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
check("M0004 refused (8.4): ... M0004 PROBES from the next run (11/12/2026; before, off until a restart, no second try) - the register's mvp_gate says why and the log line says probing; the 1123F line is not blamed (no refusal counted, the patient is not marked refused)",
      rr["mvp_gate"]["probe"].startswith("AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only (chart pat414") and "no second try" not in rr["mvp_gate"]["probe"] and rr["mvp_gate"]["off_until_reset"] == "" and "OPTION CODE M0004 REFUSED" in out
      and rr["quality_gate"]["refused_charts"] == [] and rr["quality_gate"]["off"] == "" and "off until William restarts it" not in mline(out) and "PROBING - AdvancedMD refused a visit that carried M0004" in mline(out), (rr["mvp_gate"], rr["quality_gate"], mline(out)))
keep(rr, "20261116T0100Z"); out, rr2 = live([mvisit(16, "20261117", NP_NPI), mvisit(17, "20261117")])
check("M0004 refused (8.4): ... the next run, no switch: M0004 probes - ONE M0004 line in all, on the first visit that carries the 1123F line and whose clinician still needs M0004 (here the nurse practitioner's), none on the second (the physician's); the 1123F line as usual",
      [r.get("mvp_prof") for r in rr2["created"]] == ["prof15", None] and all(r.get("quality_codes") == ["1123F"] for r in rr2["created"]) and rr2["mvp_gate"]["probe"] != "" and rr2["mvp_gate"]["off_until_reset"] == ""
      and "probing: one M0004 line a run until one is seen billed" in mline(out), (rr2["mvp_gate"], mline(out)))
keep(rr2, "20261117T0100Z"); out, rr3 = live([mvisit(17, "20261118", NP_NPI), mvisit(18, "20261118")], menv="reset")
check("M0004 (8.7): MVP_CODE=reset has nothing left to restart (M0004 never switches itself off): ignored, loudly - and while the probe's one line is not decided, no M0004 line is added for anybody",
      [r.get("mvp_prof") for r in rr3["created"]] == [None, None] and rr3["mvp_gate"]["reset"] is False and "NOTHING TO RESTART - MVP_CODE=reset was ignored" in out and rr3["mvp_gate"]["off_until_reset"] == "", (rr3["mvp_gate"], mline(out)))
_mp = [num(r["mvp_charge"]) for r in rr2["created"] if r.get("mvp_codes")]; keep(rr3, "20261118T0100Z"); BILLS[_mp[0]] = ["11/19/2026"]; out, rr4 = live([mvisit(10, "20261119"), mvisit(19, "20261119", NP_NPI)])
check("M0004 probe: ... the probe line is billed - the probe is over: each clinician who has none gets one again (the physician now; the nurse practitioner is done for the year)",
      [r.get("mvp_prof") for r in rr4["created"]] == ["prof13", None] and rr4["mvp_gate"]["probe"] == "" and rr4["mvp_gate"]["clinicians"]["prof15"]["state"] == "billed", (rr4["mvp_gate"], mline(out)))
BILLS.clear()
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rb = live([mvisit(14, "20261116")], refuse_quality=True); _rb = rb["created"]
check("M0004 refused with the 1123F line only too (8.4): the visit goes in without either line, the refusal counts against 1123F (the patient is marked refused); M0004 is NOT blamed - it neither probes nor pauses",
      len(_rb) == 1 and bool(_rb[0].get("quality_refused")) and _rb[0].get("mvp_form_refused") is True and _rb[0]["mvp_tried"] == "0.00" and len(_rb[0]["charges"]) == 1 and rb["mvp_gate"]["off_until_reset"] == "" and rb["mvp_gate"]["probe"] == ""
      and rb["quality_gate"]["refused_charts"] == [["pat414", "2026"]] and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 3, (_rb, rb["mvp_gate"]))
keep(rb, "20261116T0100Z"); ci.PARSED[:] = [mvisit(15, "20261117")]; out, dry = run_dry()
check("M0004 refused with the 1123F line only too: the next run - one refusal after proof changes nothing for 1123F, and the clinician's M0004 line can still ride", ci.QUALITY["fee"] == "0.00" and ci.QUALITY["confirmed"] is True and ci.MVP["off_until_reset"] == "" and dry.get("pat415", [{}])[0].get("mvp_codes") == ["M0004"], (ci.QUALITY["fee"], dry))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rpart = live([mvisit(14, "20261116")], refuse_mvp=True, partial=("414", "99309", "11/16/2026"))
check("M0004 refused and the chart then shows part of the visit (8.4): nothing is tried with the 1123F line only - the visit is left for William as before, and M0004 probes from the next run",
      len(rpart["failed"]) == 1 and rpart["failed"][0]["stored"] == [["99309", "11/16/2026"]] and rpart["created"] == [] and rpart["mvp_gate"]["probe"].startswith("AdvancedMD refused a visit that carried M0004 and the chart did not show it free of that visit")
      and rpart["mvp_gate"]["off_until_reset"] == "" and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 1, (rpart["failed"], rpart["mvp_gate"]))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rpm = live([mvisit(14, "20261116")], refuse_mvp=True, partial=("414", "M0004", "11/16/2026"))
check("M0004 refused and the chart then shows only an M0004 line of that date: the visit is NOT sent again in any form (it would carry a stray M0004 line) - left for William; M0004 probes from the next run",
      len(rpm["failed"]) == 1 and rpm["failed"][0]["stored"] == [["M0004", "11/16/2026"]] and rpm["created"] == [] and sum(1 for b_ in POSTS if "updvisitwithnewcharges" in b_) == 1 and rpm["mvp_gate"]["probe"] != "" and rpm["mvp_gate"]["off_until_reset"] == "", (rpm["failed"], rpm["mvp_gate"]))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rt = live([mvisit(14, "20261116")], refuse_mvp=True, plain_raises=True)
check("M0004 refused, and the visit sent with the 1123F line only ends in an error (8.4): nothing is sent again - a failed row that says nobody knows what AdvancedMD kept; that visit is for a person, and both the 1123F code and M0004 probe from the next run (the 1123F proof in place is set aside)",
      len(rt["failed"]) == 1 and rt["failed"][0].get("quality_unknown") == "0.00" and rt["failed"][0]["info"]["mvp_tried"] == "0.00" and rt["created"] == []
      and "nobody knows whether AdvancedMD kept that visit" in rt["quality_gate"]["probe"] and rt["quality_gate"]["off_until_reset"] == "" and rt["quality_gate"]["confirmed"] is False and rt["quality_gate"]["proof_aside"] is not None
      and rt["mvp_gate"]["probe"].startswith("AdvancedMD refused a visit that carried M0004, and the same visit sent with the 1123F line only ended in an error") and rt["mvp_gate"]["off_until_reset"] == "", (rt["failed"], rt["mvp_gate"], rt["quality_gate"]))
check("... (K11; K17, fix round 2) and THIS run's own gate lists that visit under 'stuck' at once (fault true, what the import knows), so this run's inspector step already looks at it",
      [(x_.get("fault"), x_.get("chart"), x_.get("fee")) for x_ in rt["quality_gate"].get("stuck") or []] == [(True, "pat414", "0.00")] and rt["quality_gate"]["stuck"][0]["what"].startswith("the call that carried the line ended in an error"), rt["quality_gate"].get("stuck"))
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, ru = live([mvisit(14, "20261116")], line_raises=True)
check("M0004: the call that carries both lines ends in an error - nothing is sent again; the failed row remembers both lines were tried; that visit is for a person, and the 1123F code and M0004 probe from the next run",
      len(ru["failed"]) == 1 and ru["failed"][0].get("quality_unknown") == "0.00" and ru["failed"][0]["info"]["mvp_tried"] == "0.00" and ru["failed"][0]["info"]["mvp_codes"] == []
      and ru["mvp_gate"]["probe"].startswith("a call that carried M0004 ended in an error") and ru["mvp_gate"]["off_until_reset"] == "" and "nobody knows whether AdvancedMD kept that visit" in ru["quality_gate"]["probe"], (ru["failed"], ru["mvp_gate"]))
keep({k_: v_ for k_, v_ in ru.items() if k_ != "mvp_gate"}, "20261116T0100Z"); ci.PARSED[:] = [mvisit(15, "20261117")]; out, dry = run_dry()
check("M0004: ... also from the failed row alone (that run cut off before it wrote its gates)", ci.MVP["probe"].startswith("AdvancedMD answered a visit that carried M0004 with a fault or an error and nobody knows what it kept of it") and ci.MVP["off_until_reset"] == ""
      and not any(v[0].get("mvp_codes") for v in dry.values()), ci.MVP)
clear_regs(); keep(PRV, "20261111T0100Z"); mreset(); charts1()
out, rd = live([mvisit(14, "20261116"), mvisit(15, "20261116", NP_NPI)], drop_mvp=True, proccode=True)
check("M0004: AdvancedMD stores the visit and its 1123F line but not the M0004 line - said at once, no further M0004 line in that run, and M0004 probes from the next run; the 1123F line counts as stored",
      rd["created"][0].get("mvp_not_stored") == "0.00" and rd["created"][0]["mvp_codes"] == [] and bool(rd["created"][0]["quality_charge"]) and rd["created"][1].get("mvp_codes") is None
      and rd["mvp_gate"]["probe"].startswith("AdvancedMD stored a visit without its M0004 line") and rd["mvp_gate"]["off_until_reset"] == "" and rd["quality_gate"]["off"] == "", (rd["created"], rd["mvp_gate"]))
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
check("inspector: a visit the import flagged (pos_err) is never moved to HCA REHAB either; mirror.py's marker for the inspector is a sentence only the current version has - since 11/12/2026 the version that tries a stuck visit again in every run (before, since 11.6: the one that takes BOTH no-charge lines off), so that an older copy of the step never comes back over the retry pass",
      'not any(x in ("99487", "99489") for x in c["cpts"]) and not c.get("pos_err"):' in insp and "is never moved to HCA REHAB either" in insp
      and '"claimocity_inspector.py": "every run tries the void and the re-save again for a visit stuck with its no-charge line"' in mir and "every run tries the void and the re-save again for a visit stuck with its no-charge line" in insp
      and '"claimocity_inspector.py": "the step takes BOTH no-charge lines off"' not in mir and "the step takes BOTH no-charge lines off" in insp and "THIS STEP TAKES THE LINE OFF BY ITSELF" in insp)
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
check("runbook: the feed step copies the helpers and checks the version line before the ingest", "cp -p claimocity_import.py claimocity_report.py claimocity_inspector.py claimocity_verify.py claimocity_ingest.py claimocity_retry_dx.py claimocity_helpers_current.py feed_parse_dft_1028.py /home/claude/unbilled/" in step and step.index("cp -p claimocity_import.py claimocity_report.py claimocity_inspector.py claimocity_verify.py claimocity_ingest.py claimocity_retry_dx.py claimocity_helpers_current.py feed_parse_dft_1028.py /home/claude/unbilled/") < step.index("must print 1") < step.index("nohup python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live > logs/claimocity_ingest_<run stamp>.log 2>&1 &` (a dry run drops --live)"))
check("runbook (11/25/2026): the ingest is started in the BACKGROUND with its own log and polled until its RESULT line - never as one plain command, which the 600 s limit cuts on a file of 50 or more messages (November's CCM file carries 200 or more)",
      "python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run" not in step and "THEN THE INGEST, IN THE BACKGROUND WITH ITS OWN LOG" in step and "until a line starts with 'RESULT stamp'" in step.replace("\n", " ")
      and "`pgrep -f claimocity_ingest.py` prints nothing when none runs" in step.replace("\n", " ")
      and all("nohup python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live > logs/claimocity_ingest_<run stamp>.log 2>&1 &" in open(os.path.join(ROOT, "nightly", "live", f_)).read() for f_ in ("columns.txt", "billing_button.txt", "feed_daily.txt")))
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
check("digest: a CCM line AT 31 is shouted - it is not William's rule since 11/25/2026 (an older copy of the rule, or a batch from before that day) - and visits left at 31 are counted and explained",
      "CCM lines entered as 32: 2 - AND 2 CCM LINE(S) ENTERED AT 31, which is not William's rule (11/25/2026: every CCM line is 32)" in line and "nursing visits 31: 3 (1 of them kept at 31 because the chart shows neither pattern" in line, line)
check("digest: ... it says they go out at 31 unless they are changed first, and names the charts for the TOP of the report", "not held: they go out at 31 with the next claim run unless they are changed first" in line
      and "  - TOP OF THE REPORT - CCM ENTERED AT 31 (William 11/25/2026: every CCM line is 32) - for William before the claim run; a routine changes nothing on these visits: pat9 11/02/2026 99487+99489" in r.stdout
      and "for William, not held - visits kept at 31, neither pattern shown (pos_kind extra / between): pat9 11/02/2026 99309" in r.stdout, r.stdout[-900:])
r, line = digest(rows + [reg_row(["99487", "99489"], "fac32", "31", ["32", "32"], ["ccm-skilled-month"] * 2), reg_row(["99487"], "fac33", "31", ["32"], ["ccm-skilled-month"])])
check("digest (11/25/2026): CCM lines the chart shows a skilled-looking month for are 32, counted with the others, and LISTED for William by chart - not at the top, nothing held",
      "CCM lines entered as 32: 5 (3 of them listed for William - the chart shows a skilled-looking month, see pos_why - not held and not changed);" in line and "ENTERED AT 31" not in r.stdout
      and "  - for William, not held - CCM entered at 32, the chart shows a skilled-looking month (pos_kind ccm-skilled-month): pat9 11/02/2026 99487+99489; pat9 11/02/2026 99487" in r.stdout, r.stdout[-900:])
# 11/25/2026 (review, findings 1 and 5): the rows as the import writes them SINCE that day - a visit whose rule failed carries its CCM line at 32 (kind ccm-forced), a
# visit from a building the table does not know carries its CCM line at 32 (kind ccm-unknown-building) and its nursing visit at the default 31
_ub = dict(reg_row(["99487", "99309"], "", "31", ["32", "31"], ["ccm-unknown-building", ""]), feed_building="A Building The Table Does Not Know")
_rub, _lub = digest(rows + [_ub, dict(_ub, dos="11/03/2026")])
check("digest (11/25/2026): a building the facility table does not know is NAMED - the feed's own words, once, with how many visits - so that it can be added to the table",
      "  - TOP OF THE REPORT - add to the facility table (claimocity_import.py FAC), the feed's own building name: 'A Building The Table Does Not Know' x2" in _rub.stdout
      and "TOP OF THE REPORT - building the facility table does not know: pat9 11/02/2026 99487+99309" in _rub.stdout, _rub.stdout[-700:])
r, line = digest(rows + [reg_row(["99487"], "fac34", "31", ["32"], ["ccm-forced"], err="boom"), reg_row(["99487", "99309"], "", "31", ["32", "31"], ["ccm-unknown-building", ""])])
check("digest: a visit the rule could not be applied to, and lines from an unknown building, are named - and what the line says about their CCM lines (at 32) is read from the register",
      "POS RULE NOT APPLIED on 1 visit(s) - entered at the feed's place of service (a CCM line among them at 32), see pos_err" in line
      and "2 CCM / nursing-visit line(s) came from a building the facility table does not know - entered with no facility (a nursing visit at the default 31, a CCM line at 32)" in line and "ENTERED AT 31" not in r.stdout, line)
check("digest: ... with their chart numbers for the top of the report", "TOP OF THE REPORT - rule not applied, for William before the claim run; a routine changes nothing on these visits: pat9 11/02/2026 99487 (boom)" in r.stdout and "TOP OF THE REPORT - building the facility table does not know: pat9 11/02/2026 99487+99309" in r.stdout, r.stdout[-900:])
# ... and the rows as a copy of the import from BEFORE 11/25/2026 wrote them (the three old ways to 31): the CCM line at 31 in a visit whose rule failed and in a visit with no
# facility. Both left the digest's loop before any CCM line was looked at, and fixed words then said "a CCM line at 32" about them.
_OLD31 = [dict(reg_row(["99487"], "fac34", "31", ["31"], err="boom"), pid="pat71"), dict(reg_row(["99487", "99309"], "", "31", ["31", "31"]), pid="pat72")]
r, line = digest(rows + _OLD31)
check("digest (11/25/2026, review): a CCM line AT 31 is shouted whatever row it stands in - also in a visit whose rule failed (pos_err) and in a visit with no facility: both are counted as ENTERED AT 31 beside the batch's 32 lines",
      "CCM lines entered as 32: 2 - AND 2 CCM LINE(S) ENTERED AT 31, which is not William's rule (11/25/2026: every CCM line is 32)" in line, line)
check("digest: ... both charts are named for the TOP OF THE REPORT under CCM ENTERED AT 31 - and still under their own headings (rule not applied; unknown building)",
      "  - TOP OF THE REPORT - CCM ENTERED AT 31 (William 11/25/2026: every CCM line is 32) - for William before the claim run; a routine changes nothing on these visits: pat71 11/02/2026 99487; pat72 11/02/2026 99487+99309" in r.stdout
      and "rule not applied, for William before the claim run; a routine changes nothing on these visits: pat71 11/02/2026 99487 (boom)" in r.stdout and "building the facility table does not know: pat72 11/02/2026 99487+99309" in r.stdout, r.stdout[-1200:])
check("digest: ... and the line no longer says 'a CCM line at 32' about a row whose CCM line is at 31 - it points to the CCM ENTERED AT 31 list instead",
      "a CCM line among them at 32" not in line and "a CCM line at 32" not in line and "POS RULE NOT APPLIED on 1 visit(s) - entered at the feed's place of service (a CCM line among them AT 31 - see CCM ENTERED AT 31), see pos_err" in line
      and "entered with no facility (a nursing visit at the default 31, a CCM line AT 31 - see CCM ENTERED AT 31)" in line, line)
r, line = digest(rows + [dict(reg_row(["99487"], "fac37", "13", ["13"], err="2 buildings"), pid="pat73"), dict(reg_row(["99309"], "fac32", "31", ["31"], err="boom"), pid="pat74"), dict(reg_row(["99309"], "", "31", ["31"]), pid="pat75")])
check("digest: ... 'a CCM line at 32' is said only where the register shows one: rule-failed visits whose only CCM line stands at an ALF's 13, and an unknown building with no CCM line, get no such words",
      "POS RULE NOT APPLIED on 2 visit(s) - entered at the feed's place of service, see pos_err" in line and "entered with no facility (a nursing visit at the default 31)" in line and "at 32)" not in line and "ENTERED AT 31" not in r.stdout, line)
r, line = digest(rows + [dict(reg_row(["99487"], "fac29", "21", ["31"], ["ccm"]), pid="pat76")])
check("digest: ... a CCM line at 31 is shouted even in a row whose feed place of service is not 31 (the value is what counts)", "AND 1 CCM LINE(S) ENTERED AT 31" in line and "CCM ENTERED AT 31 (William 11/25/2026: every CCM line is 32) - for William before the claim run; a routine changes nothing on these visits: pat76 11/02/2026 99487" in r.stdout, r.stdout[-700:])
# finding 2: the two CCM lists name EVERY chart - since 11/25/2026 a CCM line of a skilled-looking month goes out at 32 the same day, and the list is William's only cue
_PID = lambda i_: "pat%d" % (7100 + i_)
r, line = digest(rows + [dict(reg_row(["99487"], "fac32", "31", ["32"], ["ccm-skilled-month"]), pid=_PID(i_)) for i_ in range(45)])
_ll = next((l_ for l_ in r.stdout.splitlines() if "for William, not held - CCM entered at 32" in l_), "")
check("digest (11/25/2026, review): the list 'for William, not held - CCM entered at 32, the chart shows a skilled-looking month' names EVERY chart - 45 of 45, with no '(+N more ...)' cut",
      "45 of them listed for William" in line and all(("%s 11/02/2026 99487" % _PID(i_)) in _ll for i_ in range(45)) and " more" not in _ll, _ll[-400:])
r, line = digest(rows + [dict(reg_row(["99487"], "fac32", "31", ["31"], ["ccm"]), pid=_PID(i_)) for i_ in range(45)])
_ll = next((l_ for l_ in r.stdout.splitlines() if "TOP OF THE REPORT - CCM ENTERED AT 31" in l_), "")
check("digest: ... and so does the list 'TOP OF THE REPORT - CCM ENTERED AT 31': 45 of 45 charts, no cut", "AND 45 CCM LINE(S) ENTERED AT 31" in line and all(("%s 11/02/2026 99487" % _PID(i_)) in _ll for i_ in range(45)) and " more" not in _ll, _ll[-400:])
r, line = digest(rows + [dict(reg_row(["99309"], "fac32", "31", ["31"], ["extra"]), pid=_PID(i_)) for i_ in range(45)])
_ll = next((l_ for l_ in r.stdout.splitlines() if "for William, not held - visits kept at 31" in l_), "")
check("digest: ... the other lists keep their cut at 30 charts ('+15 more - see the import register')", ("%s 11/02/2026 99309" % _PID(29)) in _ll and ("%s 11/02/2026 99309" % _PID(30)) not in _ll and _ll.endswith("(+15 more - see the import register)"), _ll[-300:])
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
# William 11/25/2026 ("... change it to i10 and send me an email with the codes needed to be added"): the digest's ONE line about diagnosis codes AdvancedMD's list does
# not have, and the text of the email, which the report writes to outbox/dx_codes_needed_<stamp>.txt - codes, chart numbers and dates of service, never a name
def dxrow(pid, dos, missing, instead=True, **kw):      # a created row of the import register: the codes AdvancedMD does not know and - since 11/25/2026 - what stands in their place
    return dict(reg_row(["99309"], "fac32", "31", ["32"], ["monthly"]), pid=pid, dos=dos, missing_dx=missing, **(dict(dx_instead="I10") if instead else {}), **kw)
def dxdigest(rows_, stamp):      # -> (the run, the digest's line about these codes, the text of the email file - None when the report wrote none)
    f_ = os.path.join(rep_dir, "outbox", "dx_codes_needed_%s.txt" % stamp)
    if os.path.exists(f_): os.remove(f_)
    r_, _l = digest(rows_, stamp=stamp)
    return r_, next((l_ for l_ in r_.stdout.splitlines() if l_.startswith("- Diagnosis codes not in AdvancedMD's list")), ""), (open(f_).read() if os.path.exists(f_) else None)
_DXHEAD = "- Diagnosis codes not in AdvancedMD's list (William 11/25/2026: the visit goes in with I10 in its place; he adds the codes): "
_DXR = [dxrow("pat9101", "10/30/2026", ["S82.843D"]), dxrow("pat9101", "11/12/2026", ["S82.843D"]), dxrow("pat9102", "10/31/2026", ["M51.17", "S82.843D"], name="ZZTEST, PERSON"), dxrow("pat9103", "11/01/2026", [])]
r, _dl, _mail = dxdigest(rows + _DXR, "20261126T0139Z")
check("digest (William 11/25/2026): ONE line names the diagnosis codes AdvancedMD's list does not have - the visits, each code with its number of visits (most visits first), and the file for William's email",
      r.returncode == 0 and _dl == _DXHEAD + "3 visit(s) - S82.843D x3, M51.17 x1 - EMAIL WILLIAM: outbox/dx_codes_needed_20261126T0139Z.txt" and r.stdout.count("Diagnosis codes not in AdvancedMD's list") == 1, (_dl, r.stderr[-300:]))
check("digest: ... the report WRITES that file - the text of the email: first that these codes are not in AdvancedMD's diagnosis list (Master Files > Diagnosis Codes) and need to be added, then one line per code with its visits, chart numbers and dates of service",
      (_mail or "").startswith("These diagnosis codes are not in AdvancedMD's diagnosis list (Master Files > Diagnosis Codes) and need to be added:\n")
      and "\nS82.843D - 3 visit(s): pat9101 10/30/2026; pat9101 11/12/2026; pat9102 10/31/2026\nM51.17 - 1 visit(s): pat9102 10/31/2026\n" in (_mail or ""), _mail)
check("digest: ... and it ends with one sentence: each visit went in with I10 in the code's place on his word of 11/25/2026, later visits use a code once it is in the list, and visits already entered keep I10 unless he says otherwise",
      (_mail or "").rstrip("\n").endswith("\nEach of these visits was entered with I10 in the code's place on your word of 11/25/2026; once a code is in the list, later visits use it; the visits already entered keep I10 unless you say otherwise."), _mail)
check("digest: ... the email's text carries no name (the register row's other fields never reach it) and the digest's own line carries no chart number - codes and counts only",
      _mail is not None and "ZZTEST" not in _mail and "PERSON" not in _mail and "pat9" not in _dl and len((_mail or "").strip().split("\n")) == 6, (_mail, _dl))
r, _dl, _mail = dxdigest(rows + [dxrow("pat9102", "11/12/2026", ["S82.843D"]), dxrow("pat9101", "01/05/2027", ["S82.843D"]), dxrow("pat9101", "12/30/2026", ["S82.843D"]), dxrow("pat9101", "11/12/2026", ["S82.843D"])], "20261126T0150Z")
check("digest: ... in the email's text the visits of a code stand by chart number, then by date of service (a January visit after the December one), whatever order the register holds them in",
      "\nS82.843D - 4 visit(s): pat9101 11/12/2026; pat9101 12/30/2026; pat9101 01/05/2027; pat9102 11/12/2026\n" in (_mail or ""), _mail)
r, _dl, _mail = dxdigest(rows + [dxrow("pat9103", "11/01/2026", [])], "20261126T0200Z")
check("digest: no line and no file when no visit of the batch carries a code AdvancedMD does not know", r.returncode == 0 and _dl == "" and _mail is None and "EMAIL WILLIAM" not in r.stdout, (_dl, _mail))
# a register written by the import of BEFORE 11/25/2026: the code was left off the charge, nothing stood in its place (the row has missing_dx and no dx_instead)
r, _dl, _mail = dxdigest(rows + [dxrow("pat9101", "10/30/2026", ["S82.843D"], instead=False), dxrow("pat9102", "10/31/2026", ["S82.843D", "M51.17"], instead=False)], "20261110T1319Z")
check("digest: a register of an older import (the code was DROPPED, not replaced) is worded truthfully - 'entered without that code (before 11/25/2026)', in the line and in the email's text, and nowhere that I10 was entered",
      _dl == _DXHEAD + "2 visit(s), all entered without that code (before 11/25/2026) - S82.843D x2, M51.17 x1 - EMAIL WILLIAM: outbox/dx_codes_needed_20261110T1319Z.txt"
      and "\nS82.843D - 2 visit(s): entered without that code (before 11/25/2026): pat9101 10/30/2026; pat9102 10/31/2026\n" in (_mail or "") and "was entered with I10" not in (_mail or "") and "entered with I10 in its place" not in (_mail or "")
      and (_mail or "").rstrip("\n").endswith("\nThese visits were entered without that code: it was left off the charge and nothing stands in its place. Since 11/25/2026 a visit goes in with I10 in the code's place on your word; once a code is in the list, later visits use it."), (_dl, _mail))
r, _dl, _mail = dxdigest(rows + [dxrow("pat9101", "10/30/2026", ["S82.843D"], instead=False), dxrow("pat9104", "11/09/2026", ["S82.843D"]), dxrow("pat9105", "11/09/2026", ["T84.011A"])], "20261110T1319Z")
check("digest: ... a register that holds both kinds splits the visits: so many 'entered with I10 in its place' (dx_instead in the row) and so many 'entered without that code (before 11/25/2026)' - per code in the email, with a closing sentence for each kind",
      _dl == _DXHEAD + "3 visit(s), 2 entered with I10 in its place and 1 entered without that code (before 11/25/2026) - S82.843D x2, T84.011A x1 - EMAIL WILLIAM: outbox/dx_codes_needed_20261110T1319Z.txt"
      and "\nS82.843D - 2 visit(s): entered with I10 in its place: pat9104 11/09/2026 - entered without that code (before 11/25/2026): pat9101 10/30/2026\nT84.011A - 1 visit(s): entered with I10 in its place: pat9105 11/09/2026\n" in (_mail or "")
      and "\nThe visits listed as entered with I10 in its place went in with I10 in the code's place on your word of 11/25/2026; once a code is in the list, later visits use it; the visits already entered keep I10 unless you say otherwise. The visits listed as entered without that code went in with their other codes only: nothing stands in the code's place on them." in (_mail or ""), (_dl, _mail))
r, _dl, _mail = dxdigest(rows + [dxrow("pat9101", "11/25/2026", ["S82.843D"], instead=False)], "20261126T0300Z")
check("digest: ... and a batch of 11/25/2026 or later whose row shows the code left off is not called 'before 11/25/2026' - it says that I10 was not put in its place (an older copy of the import ran, or I10 itself is not in AdvancedMD's list)",
      "before 11/25/2026" not in _dl + (_mail or "") and "1 visit(s), all entered without that code (I10 was not put in its place: an older copy of the import ran, or I10 itself is not in AdvancedMD's list) - S82.843D x1 - EMAIL WILLIAM:" in _dl
      and "\nS82.843D - 1 visit(s): entered without that code (I10 was not put in its place: an older copy of the import ran, or I10 itself is not in AdvancedMD's list): pat9101 11/25/2026\n" in (_mail or ""), (_dl, _mail))
r, _dl, _mail = dxdigest(rows + [dxrow("pat9101", "11/26/2026", "S82.843D"), dxrow(None, None, [None, 5, "", "  ", "T84.011A", ["x"]]), dxrow("pat9106", "11/26/2026", {"a": 1}), dict(dxrow("pat9107", "11/26/2026", ["M51.17"]), dx_instead=7)], "20261126T0400Z")
check("digest: odd values in these fields (a text or a dictionary where the list of codes belongs; a number, a blank or a list among the codes; no chart number, no date; a number where I10 belongs) never stop the report - what can be read is still said",
      r.returncode == 0 and "Place of service in the nursing buildings" in r.stdout and "## Next" in r.stdout and "T84.011A x1" in _dl and "M51.17 x1" in _dl and "EMAIL WILLIAM: outbox/dx_codes_needed_20261126T0400Z.txt" in _dl and "? ?" in (_mail or ""), (r.stderr[-300:], _dl, _mail))
_ob = os.path.join(rep_dir, "outbox"); _ob2 = _ob + "_aside"
if os.path.isdir(_ob): os.rename(_ob, _ob2)
open(_ob, "w").write("a file where the folder should be")      # the outbox cannot be made: the report must still run and say so in the line
try: r, _dl, _mail = dxdigest(rows + _DXR, "20261126T0500Z")
finally:
    os.remove(_ob)
    if os.path.isdir(_ob2): os.rename(_ob2, _ob)
check("digest: when the email file cannot be written the report still runs and the line says so - the codes stay in the line and in the import register",
      r.returncode == 0 and _dl.startswith(_DXHEAD + "3 visit(s) - S82.843D x3, M51.17 x1 - EMAIL WILLIAM: the file outbox/dx_codes_needed_20261126T0500Z.txt could not be written (") and "missing_dx of the import register" in _dl and "## Next" in r.stdout, (_dl, r.stderr[-300:]))
_REP = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")).read()
check("the report's PLAIN ENGLISH header says that it writes the email's text and where", "outbox/dx_codes_needed_<STAMP>.txt" in _REP.split("\nimport os as _os")[0] and "no patient name" in _REP.split("\nimport os as _os")[0])

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
# 11/12/2026 (William 11/11/2026: "dont stop this dont let it stop make sure this suceeds"): the state of the code is ONE top line in every batch whose register carries a gate -
# "TOP OF THE REPORT - QUALITY CODE: stopped on William's word / paused this run / probing (one line a run) / going". _TOPQ = those lines, _TOPX = every other top line
_TOP = lambda out_: [l_ for l_ in out_.splitlines() if "TOP OF THE REPORT" in l_]
_TOPQ = lambda out_: [l_ for l_ in _TOP(out_) if "TOP OF THE REPORT - QUALITY CODE:" in l_]
_TOPX = lambda out_: [l_ for l_ in _TOP(out_) if "TOP OF THE REPORT - QUALITY CODE:" not in l_]
r, ql = qdigest([rows[4]], dict(G0, wait=True, pending=["vst5", "vst6"], pending_since="feed_import_20261110T0100Z.json", round={"n": 1, "fee": "0.00", "since": "feed_import_20261110T0100Z.json", "lines": 2, "void": 0, "open": 2}))
check("digest (W-1): a waiting pilot says so - the outcome of its first lines is not decided yet (never 'not billed yet': the visits may be billed, their lines not yet) - names the visits it waits for; its only top line is the state line of every batch: going, first round",
      "PILOT, waiting - no line was added in this run: the outcome of the first line(s) is not decided yet (vst5, vst6) - the lines below say why" in ql and "not billed yet" not in ql
      and _TOP(ql) == ["  - TOP OF THE REPORT - QUALITY CODE: going - first round at $0.00: 2 line(s) entered, none billed yet (at most 3 until one is seen billed), Medicare's answer: not yet."], ql)
r, ql = qdigest([rows[4]], dict(G0, wait=True, pending=["vst5"], pending_since="feed_import_2026-11-07T0100Z.json"))
check("digest (W-1): after three days of waiting the pilot goes to the top of the report - saying the outcome is still not decided, and what that can be; nobody takes a line off by hand (the patient of such a line gets none again this year)",
      "TOP OF THE REPORT - the quality-code pilot has waited 4 days: the outcome of its first line(s) is still not decided (vst5)" in ql and "a line not billed yet although its visit was" in ql and "still not billed" not in ql
      and "nobody takes a line off by hand (the patient of a line taken off by a person gets no line again this year)" in ql and "switches the code off" not in ql, ql)
r, ql = qdigest([qrow], dict(G0, fee="0.01", confirmed=True, proof={"visit": "vst5", "billed": "11/11/2026"}, pilot_cap=None, zero_not_billed=True, dead_zero_lines=[["pat1", "vst2", "charge3"], ["pat4", "vst5", "charge6"]],
                             notes=["visit vst4 was billed 11/10/2026 without its $0.00 quality line - new lines carry $0.01"]))
check("digest: says when every visit carries it, why the amount changed (at the top, in the run it changed), and lists the lines read as left off - for William, no routine voids them (M9)", "line amount $0.01; every eligible visit carries it - a quality line was seen billed to insurance (visit vst5, 11/11/2026)" in ql
      and "without its $0.00 quality line" in r.stdout and "2 quality line(s) were read as left off their claims" in ql and "pat1 vst2 charge3; pat4 vst5 charge6 - listed for William; no routine voids them" in ql
      and "TOP OF THE REPORT - new quality lines now carry ONE CENT" in ql and "voided in AdvancedMD" not in r.stdout and "remark N620" not in r.stdout, ql)
r, ql = qdigest([dict(qrow, quality_codes=[], quality_refused="Fault: no", quality_refused_fee="0.00")], dict(G0, off="this run: AdvancedMD refused a visit that carried the code"))
check("digest: a refusal goes to the top of the report, and the state line says this run was paused by it (no further line in that run) - nothing says OFF", "TOP OF THE REPORT - QUALITY CODE NOT ACCEPTED by AdvancedMD on 1 visit(s); each visit was entered without it: pat9 vst1 (Fault: no)" in r.stdout
      and "  - TOP OF THE REPORT - QUALITY CODE: paused this run - AdvancedMD refused a visit that carried the code." in r.stdout and "the quality code is OFF" not in r.stdout, r.stdout[-700:])
r, ql = qdigest([dict(qrow, quality_codes=[], quality_charge="", quality_not_stored="0.00")], dict(G0, off="this run: AdvancedMD stored a visit without its quality line"))
check("digest: a visit stored without its line goes to the top of the report", "TOP OF THE REPORT - AdvancedMD stored 1 visit(s) WITHOUT the quality line that was sent with it (the visit itself is entered): pat9 vst1" in r.stdout, r.stdout[-500:])
r, ql = qdigest([rows[4]], dict(G0, off="this run: a visit with the code was refused and the chart could not be shown free of it"), failed=[{"feed_id": "n2", "pid": "pat7", "empty_visit": "vst70", "stored": [["99309", "11/02/2026"]], "err": "x", "info": {"quality_tried": "0.00", "cpts": ["99309"]}}])
check("digest: a refused visit that was NOT sent again is named at the top with its codes - check that visit, no routine sends it again (S10, M9)", "TOP OF THE REPORT - 1 visit(s) were refused with the quality line and NOT sent again" in r.stdout
      and "check that visit (for William; no routine sends it again): pat7 ? 99309 (visit vst70; the chart shows [['99309', '11/02/2026']]) - the insurance check did not look at these visits; the Claim Inspector step looks at each of them in every run until it is free (no new line while one is held - November 12, 2026)." in r.stdout
      and "empty visit" not in r.stdout and "by hand" not in r.stdout, r.stdout[-600:])
r, ql = qdigest([rows[4]], dict(G0, reset=True, notes=["the pilot was started again in this run (QUALITY_CODE=reset)"]))
check("digest: a restart of the pilot is said - once (S10: it used to be said twice)", r.stdout.count("the pilot was started again in this run (QUALITY_CODE=reset)") == 1, r.stdout[-400:])
r, ql = qdigest([rows[4], rows[5]], G0)
check("digest (11/12/2026): the state of the code is ONE top line in EVERY batch whose register carries a gate - also when no visit carried the code and nothing happened", r.returncode == 0 and len(_TOP(ql)) == 1 and "QUALITY CODE: going - first round at $0.00" in ql
      and "on 0 visit(s) in this batch" in ql, ql)
r, ql = qdigest([rows[4], rows[5]], None)
check("digest: ... and no quality line at all for a register that carries no gate", r.returncode == 0 and ql == "", ql)
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
STOPS = "stopped on William's word (QUALITY_CODE=stop) - off until he says to start again"; _STOPL = "  - TOP OF THE REPORT - QUALITY CODE: stopped on William's word (QUALITY_CODE=stop) - no line is added until one run with QUALITY_CODE=reset in front of the import's command."
r, o = qdig2([rows[4]], dict(G0, off=STOPS, off_until_reset=STOPS), prev=dict(G0))
check("digest (S10; 11/12/2026): William's own stop is the ONLY lasting off - the state line says it at the top with how to start again; the headline says stopped", _TOP(o) == [_STOPL]
      and "line amount $0.00; stopped on William's word - no line is added until one run with QUALITY_CODE=reset." in o and "PILOT" not in o and "is OFF" not in o, o[-900:])
r, o = qdig2([rows[4]], dict(G0, off=STOPS, off_until_reset=STOPS), prev=dict(G0, off=STOPS, off_until_reset=STOPS))
check("digest (S10): ... the same stop in the next batch: the same ONE line again - every batch says where the code stands", _TOP(o) == [_STOPL], o[-700:])
r, o = qdig2([rows[4]], dict(G0, off="this run: switched off (QUALITY_CODE=off)"), prev=dict(G0))
check("digest (S10): William's own QUALITY_CODE=off - the state line says the run was paused by the switch; nothing else at the top", _TOP(o) == ["  - TOP OF THE REPORT - QUALITY CODE: paused this run - switched off (QUALITY_CODE=off)."], o[-600:])
r, o = qdig2([rows[4]], dict(G0, off="this run: QUALITY_CODE='0ff' is not a value the import knows (off, stop, reset) - no line added"), prev=dict(G0))
check("digest (SM-8, M8): a switch value the import does not know is at the top, named - in the state line", _TOP(o) == ["  - TOP OF THE REPORT - QUALITY CODE: paused this run - QUALITY_CODE='0ff' is not a value the import knows (off, stop, reset) - no line added."], o[-600:])
_UOFF = "this run: the import register feed_import_20261110T0000Z.json cannot be read - the state of the quality code is not known; no line until it is restored from the repository"
r, o = qdig2([rows[4]], dict(G0, off=_UOFF, unread=["feed_import_20261110T0000Z.json"], unread_prev=[]), prev=dict(G0))
check("digest (13.5): the first run that cannot read an import register says so in the state line - paused this run, nothing more at the top",
      _TOP(o) == ["  - TOP OF THE REPORT - QUALITY CODE: paused this run - the import register feed_import_20261110T0000Z.json cannot be read - the state of the quality code is not known; no line until it is restored from the repository."], o[-600:])
r, o = qdig2([rows[4]], dict(G0, off=_UOFF, unread=["feed_import_20261110T0000Z.json"], unread_prev=["feed_import_20261110T0000Z.json"]), prev=dict(G0))
check("digest (13.5): ... from the second run in a row a second top line says what to do - the quality code waits until the register is restored from the repository",
      [l_ for l_ in _TOPX(o) if l_.startswith("  - TOP OF THE REPORT - the import register feed_import_20261110T0000Z.json cannot be read - the quality code waits until it is restored from the repository")] == _TOPX(o) and len(_TOPX(o)) == 1 and len(_TOPQ(o)) == 1, _TOP(o))
r, o = qdig2([rows[4]], dict(G0, notes=["NOTHING TO RESTART - QUALITY_CODE=reset was ignored (the code is not switched off; take the switch out of the routine)"]), prev=dict(G0))
check("digest (SM-8): a reset that had nothing to restart is at the top (a switch left in a routine)", any("NOTHING TO RESTART - QUALITY_CODE=reset was ignored" in l_ for l_ in _TOP(o)), o[-500:])
_CENT = dict(G0, fee="0.01", zero_not_billed=True, notes=["new lines carry $0.01: AdvancedMD left the $0.00 line of visit vst4 off its claim and no $0.00 line of the round is billed"], dead_zero_lines=[["pat4", "vst4", "charge44"]],
             probe="new lines carry $0.01: AdvancedMD left the $0.00 line of visit vst4 off its claim and no $0.00 line of the round is billed - one line a run until one is billed", probe_kind="left_off", probe_since="feed_import_20261111T0000Z.json", probe_tries=1)
r, o = qdig2([rows[4]], _CENT, prev=dict(G0)); r2_, o2 = qdig2([rows[4]], _CENT, prev=dict(G0, fee="0.01"))
check("digest (S10): the switch to one cent is at the top in the run it happened, and says the patients are due again - one line a run until a one-cent line is seen billed (at one cent the code probes); the next batch does not repeat it at the top, and both say probing in the state line",
      any("TOP OF THE REPORT - new quality lines now carry ONE CENT" in l_ and "AdvancedMD left the $0.00 line of visit vst4 off its claim" in l_ and "one line a run until a one-cent line is seen billed (at one cent the code probes)" in l_ for l_ in _TOPX(o)) and _TOPX(o2) == []
      and all(len(_TOPQ(x_)) == 1 and "QUALITY CODE: probing (one line a run) - new lines carry $0.01: AdvancedMD left the $0.00 line of visit vst4 off its claim" in _TOPQ(x_)[0]
              and "AdvancedMD left the $0.00 reporting line off the claim (1 line(s) sit unbilled); new lines carry one cent, which CMS allows." in _TOPQ(x_)[0] for x_ in (o, o2)), (_TOP(o), _TOP(o2)))
r, o = qdig2([rows[4]], dict(G0, wait=True, pending=["vst2"], proof_wait={"since": "11/08/2026", "visit": "vst2", "charge": "charge22", "days": 3}), prev=dict(G0))
check("digest (13.4b): a billed line whose code text nothing shows for three days is at the top", any("the quality line of visit vst2 is billed, but for 3 days neither its charge detail nor the chart's history shows the code text 1123F" in l_ for l_ in _TOP(o)), o[-600:])
_WT = "paused this run: AdvancedMD shows procedure id pcode65441 as 99497, not 1123F - no line while that is so; every run reads it again"
r, o = qdig2([rows[4]], dict(G0, off=_WT, paused=_WT, wrong_code_text="99497", wrong_code_charge="charge12"), prev=dict(G0))
check("digest (13.4a; K2d): AdvancedMD's id read with another code text - the state line says paused this run, that every run reads it again and goes on by itself, and what ends it (the code text in AdvancedMD's procedure list)",
      _TOP(o) == ["  - TOP OF THE REPORT - QUALITY CODE: paused this run - AdvancedMD shows procedure id pcode65441 as 99497, not 1123F. No line is added while that is so; every run reads it again and goes on by itself when it reads 1123F. "
                  "To end it: the code text of that procedure in AdvancedMD's procedure list must be 1123F (a person, or AdvancedMD's support)."] and "paused this run - no line was added (the top line says why)" in o, o[-500:])
_INS = lambda held_, rem_: {"fixed": [], "bypassed": [], "laterality": [], "held": held_, "quality_removed": rem_}
r, o = qdig2([dict(qrow), dict(rows[4], visit="vst7", pid="pat7")], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}, {"visit": "7", "pid": "pat7", "why": "Pattern 24078: else"}], []))
check("digest (section 7): a held visit that still carries the line (the inspector marks it 'quality') is at the top; a held visit without it is not named there",
      any("1 visit(s) that carry the quality line are HELD by the Claim Inspector" in l_ and "pat9 vst1 - Pattern 77002: review" in l_ for l_ in _TOP(o)) and not any("pat7" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review"}], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Pattern 77002: review", "void_ok": True, "released": False, "at": "x"}]))
check("digest (11.5): the line taken off a visit that stays held - at the top: the visit is still held for its own reason, its place in the round is free, the patient is due again; not also named as 'held with the line'",
      any("the routine took the quality line charge77 off held visit vst1 (pat9), but the visit is still held for its own reason" in l_ and "its place in the round is free and the patient is due again" in l_ for l_ in _TOP(o)) and not any("carry the quality line are HELD" in l_ for l_ in _TOP(o)), _TOP(o))
for _fee_, _conf_, _next_ in (("0.00", False, "the next run moves new lines to one cent: one line a run until one is billed"), ("0.01", False, "the code goes on probing: one line a run until one is billed"),
                              ("0.00", True, "after proof one changes nothing; a second in a row moves new lines to one cent"), ("0.01", True, "after proof one changes nothing; a second in a row sets the proof aside and the code probes: one line a run")):
    r, o = qdig2([dict(qrow)], dict(G0, fee=_fee_, confirmed=_conf_), prev=dict(G0), insp_=_INS([], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": _fee_, "why": "Pattern 77002: review", "void_ok": True, "released": True}]))
    check("digest (11.5): the line taken off a held visit that then went through (at $%s, %s) - at the top, with what happens next: %s" % (_fee_, "proven" if _conf_ else "before proof", _next_),
          any(l_.endswith("the routine took the quality line charge77 off held visit vst1 (pat9; the hold: Pattern 77002: review) and the visit went through without it. That is one refusal of the line: " + _next_) for l_ in _TOPX(o))
          and "switches the code off" not in o, _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Pattern 77002: review", "void_ok": False, "released": False, "note": "the void failed: Fault"}]))
check("digest (11.5): a void that failed - at the top: the visit is held WITH its line; no new line while that is so, every run tries the void and the re-save again, and a person can take the line off at any time (11/12/2026; before, 'the code switches off')",
      any("the routine could not take the quality line off held visit vst1 (pat9: the void failed: Fault) - the visit is held WITH its line. No new line is added while that is so; every run tries the void and the re-save again, and a person can take the line off that visit at any time." in l_ for l_ in _TOPX(o))
      and not any("carry the quality line are HELD" in l_ for l_ in _TOP(o)) and "switches the code off" not in o, _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), ver_={"pat9": {"decision": "RELEASE", "visits": ["vst1"], "lead": {"code": "FLO02"}, "hold": [], "quality_removed": [{"visit": "vst1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Fault: zero amount", "void_ok": True, "released": True}]}})
check("digest (11.5): a line the insurance check took off is reported the same way", any("the routine took the quality line charge77 off held visit vst1" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), ver_={"pat9": {"decision": "RELEASE", "visits": ["vst1"], "lead": {"code": "HUM01"}, "hold": []}})
check("digest (NH-3): a quality line whose visit the insurance check moved to another payer - one plain line: that line went to that payer, nothing to do", _TOPX(o) == [] and "pat9 vst1 -> HUM01 - that line went to that payer; nothing to do" in o, o[-600:])
_PRV = dict(G0, confirmed=True, proof={"visit": "vst5", "billed": "11/11/2026"}, pilot_cap=None)
r, o = qdig2([dict(qrow)], dict(_PRV, history_shows_line=False), prev=dict(G0)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, history_shows_line=False), prev=dict(_PRV, history_shows_line=False))
check("digest (SM-7): the chart history that does not list the proven line is at the top once - in the run that found it", any("does NOT list the proven quality line" in l_ for l_ in _TOP(o)) and not any("does NOT list" in l_ for l_ in _TOP(o2)), (_TOP(o), _TOP(o2)))
r, o = qdig2([rows[4]], dict(G0, not_renewed={"2027": 4}), prev=dict(G0))
check("digest (M10): in January, visits of a year the rule was not renewed for - at the top", any("the quality code is not added to 2027 visits until William renews it (4 visit(s) of this batch would otherwise carry it)" in l_ for l_ in _TOP(o)), _TOP(o))
_ANS = {"charge": "charge22", "visit": "vst2", "date": "11/25/2026", "amount": "0.00", "register": "feed_import_20261111T1240Z.json"}
r, o = qdig2([dict(qrow)], dict(_PRV, medicare_answer=_ANS, billed_lines=["charge22"]), prev=dict(_PRV)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, medicare_answer=_ANS, billed_lines=["charge22"]), prev=dict(_PRV, medicare_answer=_ANS))
check("digest (11.4; K5): Medicare's answer when it first arrives - ONCE at the top, before the state line: QUALITY CODE ACCEPTED BY MEDICARE, with what a posted line shows and that the measure is met only by the quality-program site's feedback; the next batch does not repeat it, and the state line carries the answer from then on",
      len(_TOP(o)) == 2 and _TOP(o)[0].startswith("  - TOP OF THE REPORT - QUALITY CODE ACCEPTED BY MEDICARE - Medicare's remittance") and _TOP(o)[1].startswith("  - TOP OF THE REPORT - QUALITY CODE: going - 1 line(s) billed")
      and "  - TOP OF THE REPORT - QUALITY CODE ACCEPTED BY MEDICARE - Medicare's remittance shows the 1123F line on visit vst2, a Medicare payment line of $0.00 posted 11/25/2026: the code reached Medicare on the claim and came back on its remittance; whether the measure is met shows only in the feedback on the Medicare quality-program site. The cap of ten a run is lifted." in o
      and not any("ACCEPTED BY MEDICARE" in l_ for l_ in _TOP(o2)) and all(_TOPQ(x_)[-1] == "  - TOP OF THE REPORT - QUALITY CODE: going - 1 line(s) billed (read in AdvancedMD; lines added after the proof are not read back), Medicare's answer: Medicare's payment line posted 11/25/2026 on visit vst2." for x_ in (o, o2))
      and "no cap" in o and "counted" not in o and "is acceptance" not in o and "Medicare accepted" not in o, (_TOP(o), _TOP(o2)))
r, o = qdig2([dict(qrow)], dict(_PRV, n620=True, n620_seen="11/30/2026"), prev=dict(_PRV)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, n620=True, n620_seen="11/30/2026"), prev=dict(_PRV, n620=True))
check("digest (11.4; K5): ... the same ONCE when a person wrote the remittance file: remark N620 seen, with the date the file names; the state line says 'remark N620 seen on <date>' from then on",
      any(l_ == "  - TOP OF THE REPORT - QUALITY CODE ACCEPTED BY MEDICARE - a person saw remark N620 on a 1123F line of a Medicare remittance (registers/quality_n620_seen.json, seen 11/30/2026): remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; "
                    "whether the measure is met shows only in the feedback on the Medicare quality-program site. The cap of ten a run is lifted." for l_ in _TOP(o))
      and not any("ACCEPTED BY MEDICARE" in l_ for l_ in _TOP(o2)) and all(_TOPQ(x_)[-1].endswith("Medicare's answer: remark N620 seen on 11/30/2026.") for x_ in (o, o2)), (_TOP(o), _TOP(o2)))
r, o = qdig2([dict(qrow)], dict(_PRV, medicare_wait={"lines": 2, "oldest": "11/11/2026", "days": 12}, billed_lines=["charge12", "charge22"]), prev=dict(_PRV)); r2_, o2 = qdig2([dict(qrow)], dict(_PRV, medicare_wait={"lines": 2, "oldest": "10/01/2026", "days": 45}), prev=dict(_PRV))
check("digest (11.4, section 7): from proof until Medicare's answer: one plain sentence (how many lines are billed, since when the oldest waits, the remittance file as the second way) and the state line 'going ... Medicare's answer: not yet'; after 45 days at the top",
      _TOPX(o) == [] and "2 of the pilot's quality lines are read as billed (lines added after proof are not read back); no Medicare payment line is posted on them yet (the oldest billed 11/11/2026, 12 day(s) ago)" in o and "(reason 246, remark N620)" in o and "> registers/quality_n620_seen.json" in o
      and _TOPQ(o) == ["  - TOP OF THE REPORT - QUALITY CODE: going - 2 line(s) billed (read in AdvancedMD; lines added after the proof are not read back), Medicare's answer: not yet."]
      and any(l_.startswith("  - TOP OF THE REPORT - no Medicare payment line is posted on the pilot's billed 1123F lines after 45 days - William looks at one remittance.") for l_ in _TOP(o2)) and "Medicare has not yet shown" not in o + o2 and "Medicare has shown no" not in o2, (o[-500:], _TOP(o2)))
r, o = qdig2([rows[4]], dict(_PRV, late_rows=[["pat7001", "vst1", "charge12", "11/14/2026", "", "2026"], ["pat7002", "vst2", "charge22", "11/14/2026", "vst9", "2026"]]), prev=dict(_PRV))
check("digest (13.1b): a left-off line billed later - one plain line each; with a second line meanwhile: two billed lines for 2026, nothing to do", _TOPX(o) == [] and "a quality line read as left off on 11/14/2026 was billed later: pat7001 counts as coded." in o
      and "a quality line read as left off on 11/14/2026 was billed later: pat7002 counts as coded; pat7002 carries two billed quality lines for 2026 (the later one on vst9); nothing to do." in o, o[-700:])
r, o = qdig2([rows[4]], dict(G0, quality_skipped_hospital=2), prev=dict(G0))
check("digest (13.2): hospital visits left out - one plain line", _TOPX(o) == [] and "2 hospital visit(s) of Medicare patients 65 and older did not get the quality line: hospital visits are not coded in this version (William decides for 2027)." in o, o[-500:])
_DL = [["pat1", "vst2", "charge3"]]
r, o = qdig2([rows[4]], dict(G0, fee="0.01", dead_zero_lines=_DL, off=STOPS, off_until_reset=STOPS), prev=dict(G0, fee="0.01", off=STOPS, off_until_reset=STOPS)); r2_, o2 = qdig2([rows[4]], dict(_PRV, dead_zero_lines=_DL), prev=dict(_PRV))
check("digest (F2, W-1): lines read as left off while William has stopped the code - no promise of a line: no line is added before he restarts it; with the code on, the promise is for a later visit of the SAME year only",
      "Their patients are due again: the code is OFF until William restarts it - no line is added before then; after the restart a later eligible visit of the same year carries the code." in o and "a later eligible visit carries the code." not in o + o2
      and "Their patients are due again: a later eligible visit of the same year carries the code (a line of an earlier year is not replaced by a visit of the new year)." in o2, (o[-600:], o2[-600:]))
r, o = qdig2([rows[4]], dict(_CENT, off=STOPS, off_until_reset=STOPS), prev=dict(G0)); r2_, o2 = qdig2([rows[4]], _CENT, prev=dict(G0))
check("digest (F2): the switch to one cent promises the left-off patients a later visit of the same year - and, while William has stopped the code, only once he restarts it",
      any("they get the code with a later visit of the same year once William restarts the code (it is OFF) - one line a run until a one-cent line is seen billed" in l_ for l_ in _TOPX(o))
      and any("they get the code with a later visit of the same year - one line a run until a one-cent line is seen billed" in l_ for l_ in _TOPX(o2)), (_TOP(o), _TOP(o2)))
r, o = qdig2([dict(qrow)], G0, prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 88001: Charge amount is zero for procedure 1123F"}], [{"visit": "1", "pid": "pat9", "charge": "charge77", "fee": "0.00", "why": "Pattern 88001: Charge amount is zero for procedure 1123F", "void_ok": True, "released": False, "resave_ok": False, "still_named": True, "at": "x"}]))
check("digest (NH2-2): the line taken off, but the visit still listed for the edit about the line (the re-save after the void failed) - at the top it says so, that no new line is added while that is so and that every run re-saves the visit again; never 'held for its own reason', never 'switches the code off'",
      any("the routine took the quality line charge77 off held visit vst1 (pat9), but the visit is still listed for the edit about the line (Pattern 88001: Charge amount is zero for procedure 1123F); the re-save after the void failed - no new line is added while that is so; every run re-saves the visit again (one re-save should release it)." in l_ for l_ in _TOPX(o))
      and not any("still held for its own reason" in l_ for l_ in _TOP(o)) and "switches the code off" not in o, _TOP(o))
r, o = qdig2([rows[4]], dict(G0, off="this run: a visit refused with the code could not be sent without it either (TimeoutError)"), prev=dict(G0), failed=[{"feed_id": "fb1", "pid": "pat9301", "empty_visit": "vst700001", "quality_sent": "0.00", "err": "read timed out", "info": {"dos": "11/02/2026", "cpts": ["99309"], "quality_tried": "0.00"}}])
check("digest (NH2-4, the confirm review's exact input): a visit refused with the line whose send WITHOUT it ended in an error is named at the top - it may not be entered, William checks it, no routine sends it again",
      any("1 visit(s) were refused with the quality line and the send without it ended in an error - such a visit may NOT be entered: William checks it (no routine sends it again): pat9301 11/02/2026 99309 (visit vst700001)" in l_ for l_ in _TOP(o)), _TOP(o))
# 11/12/2026 - THE STATE LINE (K5), said from the gate as the import writes it: probing (with AdvancedMD's own words and what must change), paused (with what THIS run's inspector step did), the standing restart
_PRB = dict(G0, fee="0.01", round={"n": 2, "fee": "0.01", "since": "", "lines": 0, "void": 0, "open": 0}, probe_kind="claim_check", probe_since="feed_inspector_20261111T0100Z.json", probe_words="[Pattern 2049] Per Medicare guidelines the...; Zero dollar CPT", probe_tries=1,
            probe="AdvancedMD held visit vst4 because of its quality line (the routine took the line off and the visit went through) at $0.00 (feed_inspector_20261111T0100Z.json) - new lines carry $0.01, one line a run until one is billed")
r, o = qdig2([dict(qrow, quality_fee="0.01")], _PRB, prev=dict(G0, fee="0.01"))
# November 12, 2026 - fix round 1 (K8): THE FIRST ONE-CENT RUN TELLS THE TRUTH - while the newest cause is the move from $0.00 to one cent (or the one-cent fallback), no one-cent line has been stopped: the $0.00 stop is quoted, ONE one-cent line is tried, and nothing needs changing in AdvancedMD yet
_K8END = ": ONE line of one cent a run is tried until one is billed, and nothing needs changing in AdvancedMD yet - if a one-cent line is stopped or refused too, this line will quote AdvancedMD's words and say what must change."
check("digest (K8, fix round 1): the first one-cent run after the CLAIM CHECK stopped the $0.00 line - ONE top line: AdvancedMD's own words of the $0.00 stop, the move to one cent, that this stop was of the $0.00 line, ONE one-cent line a run, nothing needs changing in AdvancedMD yet "
      "(no 'one of two things must change', no bypass to approve, no count of stops), and this run's probe line; the headline says PROBING",
      _TOP(o) == ['  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - AdvancedMD\'s own words: "[Pattern 2049] Per Medicare guidelines the...; Zero dollar CPT" - ' + _PRB["probe"] + ". That stop was of the $0.00 line, not of a one-cent line" + _K8END
                  + " This run's probe line: visit vst1 (chart pat9)."]
      and "one of two things must change" not in o and "bypass" not in _TOP(o)[0] and "line amount $0.01; PROBING - one line a run until one such line is seen billed to insurance in AdvancedMD." in o and "PILOT" not in o, _TOP(o))
_PRR = dict(_PRB, probe_kind="refused", probe_since="feed_import_20261111T0100Z.json", probe_words="<Fault>the charge amount is not accepted</Fault>", probe="AdvancedMD refused a visit that carried the code at $0.00 (feed_import_20261111T0100Z.json) - new lines carry $0.01, one line a run until one is billed")
r, o = qdig2([dict(qrow, quality_fee="0.01")], _PRR, prev=dict(G0, fee="0.01"))
check("digest (K8): ... the first one-cent run after AdvancedMD's charge entry REFUSED the $0.00 line - the same: the refusal's words, that it was the $0.00 line, nothing needs changing yet (no 'AdvancedMD's charge entry must take procedure 1123F at $0.01')",
      _TOPQ(o) == ['  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - AdvancedMD\'s own words: "<Fault>the charge amount is not accepted</Fault>" - ' + _PRR["probe"] + ". That stop was of the $0.00 line, not of a one-cent line" + _K8END
                   + " This run's probe line: visit vst1 (chart pat9)."] and "must take procedure 1123F" not in o, _TOPQ(o))
_PRF = dict(G0, fee="0.01", probe="new lines carry $0.01 and no one-cent line is seen billed yet - one line a run until one is billed", probe_kind="refused", probe_since="feed_import_20261112T0100Z.json", probe_tries=1)
r, o = qdig2([dict(qrow, quality_fee="0.01")], _PRF, prev=dict(G0, fee="0.01"))
check("digest (K8): ... the one-cent FALLBACK (an older gate at one cent, no register shows what moved it) - no one-cent line has been stopped or refused, nothing needs changing yet; no count of stops (none was seen)",
      _TOPQ(o) == ["  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - " + _PRF["probe"] + ". No one-cent line has been stopped or refused" + _K8END + " This run's probe line: visit vst1 (chart pat9)."] and "stopped 1 time" not in o, _TOPQ(o))
# November 12, 2026 - fix round 2 (K14, review G1): K8's flag no longer overwrites the list of lines that rode on visits the insurance check moved to another payer -
# the K8 digests build their whole quality block, and the "moved to another payer" line still prints while the code probes
_MVV = {"pat9": {"decision": "RELEASE", "visits": ["vst1"], "lead": {"code": "HUM01"}, "hold": []}}; _k14 = []
for _g14 in (_PRB, _PRR, _PRF, dict(_PRB, probe="the code had switched itself off (x) - William's standing word of November 11, 2026 restarts it", probe_kind="standing", probe_words="")):
    for _v14 in (None, _MVV):
        r, o = qdig2([dict(qrow, quality_fee="0.01")], _g14, prev=dict(G0, fee="0.01"), ver_=_v14); _k14.append((o, _v14))
check("digest (K14, fix round 2): no K8 digest says 'could not be built' - the first one-cent run's quality block is built whole (with and without a line on a visit moved to another payer)",
      not any("could not be built" in o_ for o_, _v in _k14) and all("- first lines:" in o_ for o_, _v in _k14), [l_ for o_, _v in _k14 for l_ in o_.splitlines() if "could not be built" in l_][:2])
check("digest (K14, fix round 2): ... and the 'moved to another payer' line still prints while the code probes - after the move to one cent, after a refusal, in the fallback and for another cause",
      all(("1 quality line(s) of this batch rode on visits the insurance check moved to another payer than Medicare: pat9 vst1 -> HUM01" in o_) == (_v is not None) for o_, _v in _k14), [(_v is not None, "moved to another payer" in o_) for o_, _v in _k14])
r, o = qdig2([dict(qrow, quality_fee="0.01")], dict(_PRB, notes=[_PRB["probe"]]), prev=dict(G0))
_l = [l_ for l_ in _TOPX(o) if "new quality lines now carry ONE CENT" in l_]
check("digest (review note F5 with K8 and K12, fix round 1): the run in which new lines move to one cent says the import's note WHOLE, and - the $0.00 line was stopped by the claim check - that those patients get no line again this year (not that they are due again)",
      len(_l) == 1 and _PRB["probe"] in _l[0] and "The patients whose $0.00 line was stopped get no line again this year" in _l[0] and "due again" not in _l[0], _l)
_lon = "new lines carry $0.01: AdvancedMD left the $0.00 line of visit vst4 off its claim and no $0.00 line of the round is billed"
r, o = qdig2([dict(qrow, quality_fee="0.01")], dict(_PRB, probe_kind="left_off", probe=_lon + " - one line a run until one is billed", probe_words="", notes=[_lon]), prev=dict(G0))
_l = [l_ for l_ in _TOPX(o) if "new quality lines now carry ONE CENT" in l_]
check("digest (F5, K12): ... and when a $0.00 line LEFT OFF its claim moved the amount, those patients are due again 30 days after it was called left off (AdvancedMD may still bill it until then)",
      len(_l) == 1 and _lon in _l[0] and "due again 30 days after it was called left off" in _l[0], _l)
_PR1 = dict(_PRB, probe_tries=2, probe="AdvancedMD held visit vst1 because of its quality line (the routine took the line off and the visit went through) with a one-cent charge too (feed_inspector_20261112T0100Z.json) - William looks")
r, o = qdig2([dict(qrow, quality_fee="0.01")], _PR1, prev=dict(_PRB))
check("digest (K8): ... once a ONE-CENT line was stopped by the claim check, the line says what must change in AdvancedMD or which bypass William must approve (no routine bypasses it), with how often and since when",
      _TOPQ(o) == ['  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - AdvancedMD\'s own words: "[Pattern 2049] Per Medicare guidelines the...; Zero dollar CPT" - ' + _PR1["probe"] + " (stopped 2 time(s) since feed_inspector_20261111T0100Z.json). "
                   "To let the line pass, one of two things must change: in AdvancedMD the Claim Inspector edit quoted here is set so that it lets a 1123F line of $0.01 through (a person, or AdvancedMD's support), or William approves a standing bypass of exactly that edit for 1123F lines - "
                   "no routine bypasses it without his word. This run's probe line: visit vst1 (chart pat9)."], _TOPQ(o))
r, o = qdig2([rows[4]], dict(_PRB, wait=True, pending=["vst8"]), prev=dict(_PRB))
check("digest (K5): ... while the probe line of an earlier run is not decided the line says so - no new line in this run", len(_TOP(o)) == 1 and "QUALITY CODE: probing (one line a run) - " in _TOP(o)[0]
      and _TOP(o)[0].endswith(" The probe line of visit vst8 is not decided yet - no new line in this run."), _TOP(o))
_LO = dict(G0, fee="0.01", probe="AdvancedMD billed visit vst9 (11/12/2026) without its one-cent quality line too - William looks", probe_kind="left_off", probe_since="feed_import_20261111T0000Z.json", probe_tries=2, left_off_cent=["vst9", "vst12"])
r, o = qdig2([rows[4]], _LO, prev=dict(_LO))
check("digest (K2b): PROBING after a one-cent line was left off its claim - the top line says AdvancedMD leaves the reporting line off the claim, how many one-cent lines sit unbilled, and that this needs a setting in AdvancedMD (a person or its support)",
      _TOP(o) == ["  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - AdvancedMD billed visit vst9 (11/12/2026) without its one-cent quality line too - William looks (stopped 2 time(s) since feed_import_20261111T0000Z.json). "
                  "AdvancedMD leaves the reporting line off the claim: 2 one-cent line(s) sit unbilled (vst9, vst12). This needs a setting in AdvancedMD - a person or AdvancedMD's support makes it send a line of one cent for procedure 1123F."], _TOP(o))
for _k_, _adv_ in (("refused", "To let the line pass, AdvancedMD's charge entry must take procedure 1123F at $0.01 on a visit - a person asks AdvancedMD's support why it does not."), ("not_stored", "To let the line pass, AdvancedMD's charge entry must take procedure 1123F at $0.01 on a visit - a person asks AdvancedMD's support why it does not."),
                   ("fault", "Nothing to change in AdvancedMD is known; the visit named here is for a person to check, and the first probe line that is billed ends the probing."), ("order", "Nothing to change in AdvancedMD is known; the visit named here is for a person to check, and the first probe line that is billed ends the probing."),
                   ("voided", "Nothing to change in AdvancedMD is known; the first probe line that is billed ends the probing."), ("stuck", "Nothing to change in AdvancedMD is known; the first probe line that is billed ends the probing."), ("standing", "Nothing to change in AdvancedMD is known; the first probe line that is billed ends the probing.")):
    r, o = qdig2([rows[4]], dict(G0, fee="0.01", probe="the cause", probe_kind=_k_, probe_since="feed_import_20261111T0000Z.json", probe_tries=3), prev=dict(G0, fee="0.01"))
    check("digest (K5): probing, a cause of kind %s - the top line ends with the advice of that kind" % _k_, _TOP(o) == ["  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - the cause (stopped 3 time(s) since feed_import_20261111T0000Z.json). " + _adv_], _TOP(o))
_SK = {"chart": "pat9", "visit": "vst1", "charge": "charge77", "own": "charge1", "code": "1123F", "fee": "0.00", "with": "", "why": "Pattern 77002: review", "register": "feed_inspector_20261110T0100Z.json", "what": "the routine could not take the line off", "since": "feed_inspector_20261110T0100Z.json"}
_PS = 'paused this run: visit vst1 (chart pat9) is held with its quality line - the routine could not take the line off (feed_inspector_20261110T0100Z.json: "Pattern 77002: review"); no new line while that is so - every run\'s inspector step tries the void and the re-save again'
_GP = dict(G0, off=_PS, paused=_PS, stuck=[_SK])
_HEAD = '  - TOP OF THE REPORT - QUALITY CODE: paused this run - visit vst1 (chart pat9) is held with its quality line: the routine could not take the line off (feed_inspector_20261110T0100Z.json: "Pattern 77002: review"). No new line was added. '
_RT = lambda **e: dict({"visit": "1", "pid": "pat9", "charge": "charge77", "code": "1123F", "fee": "0.00", "why": "Pattern 77002: review", "void_ok": True, "released": True, "retry_of": "feed_inspector_20261110T0100Z.json", "at": "x"}, **e)
for _lbl_, _ent_, _did_ in (
        ("no new try recorded", None, "This run's inspector step recorded no new try for that visit; the next run tries the void and the re-save again."),
        ("no longer listed", _RT(void_ok=False, listed=False, note="the visit is no longer listed by the Claim Inspector - nothing done"), "This run found the visit free (no longer listed by the Claim Inspector): nothing was done to it, and the next run goes on by itself, probing."),
        ("only advisories remained", _RT(void_ok=False, listed=False, note="only advisories remained - bypassed, nothing voided"), "This run found the visit free (only advisories remained - bypassed): nothing was done to it, and the next run goes on by itself, probing."),
        ("the visit was billed", _RT(void_ok=False, listed=False, note="the visit was billed - nothing done"), "This run found the visit free (the visit was billed): nothing was done to it, and the next run goes on by itself, probing."),
        ("the void failed again", _RT(void_ok=False, released=False, note="the void failed: Fault"), "This run tried again and could not take the line off (the void failed: Fault); every run tries again, and a person can take the line off that visit at any time."),
        ("taken off, re-saved, gone out", _RT(resave_ok=True), "This run took the line off, re-saved the visit and it went out; the next run goes on by itself, probing."),
        ("still listed for the edit", _RT(released=False, resave_ok=True, still_named=True), "This run re-saved the visit again and it is still listed for the edit about the line; every run tries again."),
        ("the re-save failed", _RT(released=False, resave_ok=False, still_named=True), "This run re-saved the visit again and it is still listed for the edit about the line; the re-save failed; every run tries again."),
        ("the listing after the re-save failed", _RT(released=False, resave_ok=True, still_named=True, note="the listing after the re-save failed"), "This run re-saved the visit again, but the listing after it failed, so the visit is not shown free; the next run lists it again."),
        ("held for its own reason", _RT(released=False, resave_ok=True, why="Pattern 24078: else"), "This run took the line off; the visit is still held for its own reason (Pattern 24078: else), which is not this code's; the next run goes on by itself, probing.")):
    r, o = qdig2([rows[4]], _GP, prev=dict(G0), insp_=_INS([], [_ent_] if _ent_ else []))
    check("digest (K5, K2c): PAUSED, a visit stuck held with its line - the top line names the visit, what holds it and what THIS run's inspector step did (%s); the retry's entry is not said a second time" % _lbl_,
          _TOP(o) == [_HEAD + _did_] and "paused this run - no line was added (the top line says why)" in o, _TOP(o))
r, o = qdig2([rows[4]], dict(_GP, stuck=[_SK, dict(_SK, visit="vst5", chart="pat5")]), prev=dict(G0))
check("digest (K2c): ... with a second stuck visit the line says how many more", len(_TOP(o)) == 1 and '(feed_inspector_20261110T0100Z.json: "Pattern 77002: review"); 1 more visit(s) the same way. No new line was added.' in _TOP(o)[0], _TOP(o))
# November 12, 2026 - fix round 1 (K9; specification 2.5): in the digest too the NEWEST entry for a line decides - the same-start corner says ONE top line about the visit
_NOR = lambda e_: {k_: v_ for k_, v_ in e_.items() if k_ != "retry_of"}      # an entry of the step's NORMAL pass (no retry_of)
r, o = qdig2([rows[4]], dict(G0), prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}], [_NOR(_RT(void_ok=False, released=False, note="the void failed: time-out")), _RT(resave_ok=True)]))
check("digest (K9, fix round 1): the same-start corner - the normal pass could not take the line off (a time-out) and the retry pass of the SAME start then took it off and the visit went out: ONE top line about that visit, the newest entry's (it went through), "
      "saying once that the first try did not free it and this run's retry pass did - never also 'held WITH its line'; the held row stays (the import's proof rule reads it) and is still listed in the Claim Inspector pass",
      [l_ for l_ in _TOPX(o) if "vst1" in l_] == ["  - TOP OF THE REPORT - the routine took the quality line charge77 off held visit vst1 (pat9; the hold: Pattern 77002: review) and the visit went through without it - its first try in this run did not free it (the void failed: time-out), then freed by this run's retry pass. "
                                                   "That is one refusal of the line: the next run moves new lines to one cent: one line a run until one is billed"]
      and not any("held WITH its line" in l_ for l_ in _TOP(o)) and "vst1 pat9: Pattern 77002: review" in o, _TOP(o))
r, o = qdig2([rows[4]], dict(G0), prev=dict(G0), insp_=_INS([], [_NOR(_RT(released=False, resave_ok=True, still_named=True)), _RT(void_ok=False, listed=False, note="the visit is no longer listed by the Claim Inspector - nothing done")]))
check("digest (K9): ... and when the first entry said 'still listed for the edit' and the retry of the same start found the visit no longer listed: ONE line says so - never also 'still listed'",
      [l_ for l_ in _TOPX(o) if "vst1" in l_] == ["  - TOP OF THE REPORT - held visit vst1 (pat9): the routine's first try in this run did not free it (still listed for the edit about the line), then freed by this run's retry pass (the visit is no longer listed by the Claim Inspector - nothing done) - nothing more was done to it."], _TOP(o))
r, o = qdig2([rows[4]], dict(G0), prev=dict(G0), insp_=_INS([], [_NOR(_RT(void_ok=False, released=False, note="the void failed: time-out")), _RT(void_ok=False, released=False, note="the void failed: Fault")]))
check("digest (K9): ... when the retry of the same start failed too, the newest entry's own words stand - ONE line, 'held WITH its line', with the newest reason",
      [l_ for l_ in _TOPX(o) if "vst1" in l_] == ["  - TOP OF THE REPORT - the routine could not take the quality line off held visit vst1 (pat9: the void failed: Fault) - the visit is held WITH its line. No new line is added while that is so; every run tries the void and the re-save again, and a person can take the line off that visit at any time."], _TOP(o))
# fix round 1 (K11): PAUSED by a visit of a fault run - the state line says so in its own words
_FS = {"chart": "pat9", "visit": "vst70", "charge": "", "own": "", "code": "1123F", "fee": "0.00", "with": "", "dos": "11/10/2026", "fault": True, "why": "read timed out", "register": "feed_import_20261110T0100Z.json",
       "what": "the call that carried the line ended in an error - nobody has seen yet whether the Claim Inspector holds it", "since": "feed_import_20261110T0100Z.json"}
r, o = qdig2([rows[4]], dict(G0, off="paused this run: visit vst70", paused="paused this run: visit vst70", stuck=[_FS]), prev=dict(G0),
             insp_=_INS([], [dict(_RT(void_ok=False, listed=False, note="the visit is no longer listed by the Claim Inspector - nothing done"), visit="70", charge="", fault=True, retry_of="feed_import_20261110T0100Z.json")]))
check("digest (K11, fix round 1): PAUSED by a visit of a fault run (a fault, an error or a cut run while the call that carried the line was out) - the state line names the visit, says it came from a fault, what the import knows, and what THIS run's inspector step did",
      _TOP(o) == ['  - TOP OF THE REPORT - QUALITY CODE: paused this run - visit vst70 (chart pat9) came from a fault run: the call that carried the line ended in an error - nobody has seen yet whether the Claim Inspector holds it '
                  '(feed_import_20261110T0100Z.json: "read timed out"). No new line was added. This run found the visit free (no longer listed by the Claim Inspector): nothing was done to it, and the next run goes on by itself, probing.'], _TOP(o))
# November 12, 2026 - fix round 2 (K15, K16, K17): what the state line says after a cut or a fault, and of a fault visit held for its own reason
_FO = dict(_FS, own=True, register="feed_inspector_20261110T0100Z.json", what="held for its own reason; no 1123F line is on it - a person fixes the visit", why="Pattern 31001: diagnosis pointer missing")
r, o = qdig2([dict(qrow, quality_fee="0.01")], dict(_PRB, stuck=[_FO]), prev=dict(G0, fee="0.01"))
check("digest (K15, fix round 2): a fault visit held for its own reason (no 1123F line on it) pauses nothing - the ONE state line says the code probes AND names that visit for a person, with why",
      len(_TOPQ(o)) == 1 and _TOPQ(o)[0].startswith("  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run)") and _TOPQ(o)[0].endswith(
          " Visit vst70 (chart pat9) came from a fault run and is held for its own reason, not because of this code: held for its own reason; no 1123F line is on it - a person fixes the visit "
          '(feed_inspector_20261110T0100Z.json: "Pattern 31001: diagnosis pointer missing") - it stays on this report until it is free; it does not pause the code.') and "paused" not in _TOPQ(o)[0], _TOPQ(o))
_SK2 = {"chart": "pat8", "visit": "vst8", "charge": "charge88", "own": "charge80", "code": "1123F", "fee": "0.01", "with": "", "why": "Pattern 77002: review", "register": "feed_inspector_20261110T0100Z.json", "what": "the routine could not take the line off", "since": "feed_inspector_20261110T0100Z.json"}
r, o = qdig2([rows[4]], dict(G0, off="paused this run: visit vst8", paused="paused this run: visit vst8", stuck=[_FO, _SK2]), prev=dict(G0))
check("digest (K15, fix round 2): ... when ANOTHER visit pauses the code, the state line names THAT visit (the one held with its line), not the fault visit held for its own reason - which it names last, as pausing nothing",
      len(_TOPQ(o)) == 1 and _TOPQ(o)[0].startswith("  - TOP OF THE REPORT - QUALITY CODE: paused this run - visit vst8 (chart pat8) is held with its quality line: the routine could not take the line off") and "more visit(s) the same way" not in _TOPQ(o)[0]
      and _TOPQ(o)[0].endswith("it stays on this report until it is free; it does not pause the code."), _TOPQ(o))
r, o = qdig2([rows[4]], dict(G0, off="this run: a visit with the code was refused and the chart could not be shown free of it", stuck=[_FS]), prev=dict(G0),
             insp_=_INS([], [dict(_RT(void_ok=False, released=False, note="its line could not be looked for: the chart's history could not be read (RuntimeError)", looked=False), visit="70", charge="", fault=True, retry_of="feed_import_20261110T0100Z.json")]))
check("digest (K16, fix round 2): the fault run's OWN digest - the generic state line names the fault visit, what the import knows and what THIS run's inspector step found (its newest retry entry): here its line could not be looked for",
      _TOPQ(o) == ['  - TOP OF THE REPORT - QUALITY CODE: paused this run - a visit with the code was refused and the chart could not be shown free of it. Visit vst70 (chart pat9) came from a fault run: the call that carried the line ended in an error - nobody has seen yet whether the Claim Inspector holds it. '
                   "This run's step could not look for its quality line (its line could not be looked for: the chart's history could not be read (RuntimeError)); the next run looks again."], _TOPQ(o))
r, o = qdig2([rows[4]], dict(G0, off="this run: x", stuck=[_FS]), prev=dict(G0), insp_=_INS([], [dict(_RT(void_ok=False, released=False, own_reason=True, note="held for its own reason; no 1123F line is on it - a person fixes the visit"), visit="70", charge="", fault=True, retry_of="feed_import_20261110T0100Z.json")]))
check("digest (K16, fix round 2): ... and when this run's step found NO 1123F line on it: held for its own reason - a person fixes the visit; it does not pause the code (never 'a person can take the line off')",
      len(_TOPQ(o)) == 1 and _TOPQ(o)[0].endswith("This run found it held for its own reason, not because of this code (held for its own reason; no 1123F line is on it - a person fixes the visit) - a person fixes the visit; it does not pause the code.") and "take the line off" not in _TOPQ(o)[0], _TOPQ(o))
_SC = {"chart": "pat9", "visit": "vst1", "charge": "charge77", "own": "charge1", "code": "1123F", "fee": "0.00", "with": "", "why": "Pattern 77002: review", "register": "feed_inspector_20261110T0100Z.json",
       "what": "the routine's last try was cut off before it ended; this run's step looks again", "since": "feed_inspector_20261110T0100Z.json"}
r, o = qdig2([rows[4]], dict(G0, off="paused this run: visit vst1", paused="paused this run: visit vst1", stuck=[_SC]), prev=dict(G0), insp_=_INS([], [_RT(was_void=True)]))
check("digest (K16, fix round 2; review G4 a): after a run cut after the void - the state line says the visit MAY still be held and that the routine's last try was cut off; this run's step found the line off already and re-saved the visit (never 'could not take the line off' nor 'took the line off')",
      _TOPQ(o) == ['  - TOP OF THE REPORT - QUALITY CODE: paused this run - visit vst1 (chart pat9) may still be held with its quality line: the routine\'s last try was cut off before it ended; this run\'s step looks again (feed_inspector_20261110T0100Z.json: "Pattern 77002: review"). '
                   "No new line was added. This run found the line off already, re-saved the visit and it went out; the next run goes on by itself, probing."], _TOPQ(o))
r, o = qdig2([rows[4]], dict(G0), prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}], [_NOR(_RT(void_ok=False, released=False, note="the void failed: time-out")), _RT(void_ok=True, released=True)]))
check("digest (K17, fix round 2; review G5): the Claim Inspector section says that a held visit THIS run's retry pass freed is free - one line, the held row itself stays (and is still counted as written)",
      "  - vst1 pat9: Pattern 77002: review - then freed by this run's retry pass: the visit is free" in r.stdout and "held 1" in r.stdout, r.stdout[-500:])
r, o = qdig2([rows[4]], dict(G0), prev=dict(G0), insp_=_INS([{"visit": "1", "pid": "pat9", "why": "Pattern 77002: review", "quality": True}], [_NOR(_RT(void_ok=False, released=False, note="the void failed: time-out")), _RT(void_ok=False, released=False, note="the void failed: Fault")]))
check("digest (K17, G5): ... a held visit the retry pass did NOT free is listed as held, without that sentence", "  - vst1 pat9: Pattern 77002: review" in r.stdout and "then freed by this run's retry pass: the visit is free" not in r.stdout, r.stdout[-500:])
_SR = {"was": "AdvancedMD billed visit vst9 (11/12/2026) without its one-cent quality line too - William looks", "register": "feed_import_20261111T0000Z.json"}
_GS = dict(G0, fee="0.01", probe="the code had switched itself off (%s) - William's standing word of November 11, 2026 restarts it" % _SR["was"], probe_kind="standing", probe_since="feed_import_20261111T0000Z.json", probe_tries=1)
r, o = qdig2([rows[4]], dict(_GS, standing_restart=_SR), prev=dict(G0, fee="0.01", off=_SR["was"], off_until_reset=_SR["was"])); r2_, o2 = qdig2([rows[4]], _GS, prev=dict(_GS, standing_restart=_SR))
check("digest (section 3): the run that reads an older register's own 'off until reset' says ONCE, before the state line, that William's standing word restarted the code and that no restart by him is needed any more; the state line says probing; the next batch does not repeat it",
      len(_TOP(o)) == 2 and _TOP(o)[0] == '  - TOP OF THE REPORT - QUALITY CODE: restarted on William\'s standing word of November 11, 2026 ("dont stop this dont let it stop make sure this suceeds") - an earlier run had switched it off (%s). No restart by William is needed any more; the code goes on by itself.' % _SR["was"]
      and _TOP(o)[1].startswith("  - TOP OF THE REPORT - QUALITY CODE: probing (one line a run) - the code had switched itself off (") and _TOP(o)[1].endswith("Nothing to change in AdvancedMD is known; the first probe line that is billed ends the probing.")
      and len(_TOP(o2)) == 1 and "restarted on William's standing word" not in o2, (_TOP(o), _TOP(o2)))
r, o = qdig2([rows[4]], G0, prev=dict(G0), failed=[{"feed_id": "n2", "pid": "pat7", "info": {"dos": "11/02/2026", "cpts": ["99309"]}, "err": "x"}])
check("digest (N3): failed visits are counted and named in the Import line (it used to say '0 faults' always)", "1 visit(s) FAILED - not entered or not finished, see the import register's failed rows: pat7 11/02/2026 99309" in o and "0 faults" not in o, o[:600])
_busy = dict(G0, off=STOPS, off_until_reset=STOPS, not_renewed={"2027": 1}, quality_skipped_hospital=1, notes=["NOTHING TO RESTART - QUALITY_CODE=reset was ignored (x)"])
r, o = qdig2([dict(qrow, quality_codes=[], quality_refused="Fault: no", quality_refused_fee="0.00")], _busy, prev=dict(G0), insp_=_INS([], [{"visit": "1", "pid": "pat9", "charge": "charge77", "void_ok": False, "released": False, "note": "x"}]))
check("digest: every line for William starts '  - TOP OF THE REPORT - ' and is one line (a busy batch: five of them, the state line among them)", len(_TOP(o)) == 5 and all(l_.startswith("  - TOP OF THE REPORT - ") for l_ in _TOP(o)), _TOP(o))
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
    _r6, _c6, _p6 = _ag_visit(True, [("CO16", "141.00")], em_paid="0.00", carrier="FLO02", bal="141.00"); _c6[1].update(billdate="11/24/2026", payments=[])      # NH2-6's exact input: the 1123F line billed 11/24, no payment yet
    _d6 = _ag.decide(_r6, _c6, _p6, None)
    check("ageing page (%s, NH2-6): a reporting line billed LATER than the visit (11/24, no payment yet) is not the visit's last send - the visit's own CO-16 of 11/20 still reads CORRECT & RESEND, not WAIT" % _rel, _d6["rec"] == "CORRECT & RESEND" and _d6["carcs"] == "16", _d6)
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
      "&& QUALITY_CODE=off nohup python3 claimocity_ingest.py" in _qrun.replace("\n", " ") and "&& QUALITY_CODE=off python3 claimocity_ingest.py" not in _qrun.replace("\n", " ") and "never between `nohup` and `python3`, where the command does not start" in _qrun.replace("\n", " ") and "`QUALITY_CODE=stop` = OFF until William restarts it" in _qrun.replace("\n", " ") and "NOTHING TO RESTART" in _qrun and "on the ingest command only" in _qrun.replace("\n", " ")
      and "Any other value adds no line and the log names it" in _qrun.replace("\n", " ") and "Hospital visits do not carry\nit in this version" in _qrun)
check("runbook (M8c): the import register is committed right after the import while a pilot round is open - the privacy gate first, then the same git commands as the practice-database register",
      all(x_ in _qrun.replace("\n", " ") for x_ in ("COMMIT THE IMPORT REGISTER while a pilot round is open", "python3 tools/mirror/phi_gate.py /home/claude/unbilled/registers/feed_import_<stamp>.json practices/ehpa/registers/feed_import_<stamp>.json",
          "git add practices/ehpa/registers/feed_import_<stamp>.json", "git pull -q --rebase --autostash origin main && git push origin HEAD:main")) and "--autostash origin main && git push origin HEAD:main" in step[:step.index("## Place of service")])
check("runbook (S6): the step the routines follow (f) names the quality line and its grep", "Then the digest's line 'Quality code 1123F ...'" in step[:step.index("## Place of service")] and "grep -h '^QUALITY 1123F'" in step[:step.index("## Place of service")])
_cc = open(os.path.join(ROOT, "docs", "captured_calls.md")).read(); _sl = open(os.path.join(ROOT, "docs", "SHARED_LESSONS.md")).read().rstrip("\n").split("\n")
check("captured calls (13.4c, section 7): the look-up answers - 1123F = pcode65441 'ACP DISCUSS/DSCN MKR DOCD', 1124F not in the list, M0004 = pcode692183 'QUAL CARE NEUROLOGIC CND MVP' (place of service 11, type of service 01)",
      'procedure id `pcode65441`, name "ACP DISCUSS/DSCN MKR DOCD"' in _cc and "1124F is NOT in the practice's procedure list" in _cc and 'procedure id `pcode692183`, name "QUAL CARE NEUROLOGIC CND MVP", units 1.0, default place of service 11, type of service 01' in _cc and "read 11/10/2026 09:43Z" in _cc)
check("lessons: one dated line records the owner's decision on held visits and the rule version (since step 4 a later line follows it: William's initial-visit rule)", sum(1 for l_ in _sl if l_.startswith("- 2026-11-10T1435Z | chat (quality code 1123F, version 2, step 2) | RULE |") and "just deal with it" in l_ and "2026-11-10.6" in l_) == 1)
# 11/12/2026 (specification 5.1 to 5.3; William 11/11/2026: "dont stop this dont let it stop make sure this suceeds"): the words say what the code does - it never switches itself off
_QR = _qrun.replace("\n", " "); _STEP1 = step.replace("\n", " "); _W1112 = "dont stop this dont let it stop make sure this suceeds"
check("rulebook (5.1, R0-R5): THE CODE NEVER SWITCHES ITSELF OFF with William's sentence and the date it is in force - where the code went off it probes (one new line a run, none while a probe line is not decided, until the proof), it pauses one run at a time, a line taken off by a person costs that patient the year, his own switches stay his, and an older register's own 'off' is a pause that has ended",
      all(x_ in _qrb for x_ in ('THE CODE NEVER SWITCHES ITSELF OFF - William 11/11/2026, about the line "if stopped again the code switches off until the owner restarts it": "%s" (in force since November 12, 2026). No state of the code needs William\'s restart any more.' % _W1112,
          "Where the code used to go off it PROBES: ONE new line a run, on the first eligible visit, at the amount the code stands at, none while an earlier probe line is not decided, until a line is billed to insurance and AdvancedMD shows 1123F for it",
          "It PAUSES one run at a time - every run looks again - while a visit is stuck held with its line, while a visit of a fault run may still carry its line and is not yet seen free of it (November 12, 2026 - fix rounds 1 and 2), and while AdvancedMD shows another code text for pcode65441.", "A line taken off by a person: that patient gets no line again that year (a person decided) and the code stays on.",
          "no routine bypasses an edit for this line", '"QUALITY CODE: probing (one line a run) - ..."', '"QUALITY CODE: paused this run - ..."', '"QUALITY CODE: going - ..."', '"QUALITY CODE ACCEPTED BY MEDICARE"',
          "WILLIAM'S OWN SWITCHES STAY HIS: QUALITY_CODE=stop = off until he restarts it with one run of QUALITY_CODE=reset (honoured only after his stop; a new round at $0.00)",
          'An older register that still says "off until William restarts it" by the code\'s own doing is read as a pause that has ended: his standing word restarts it once, and the report says so.',
          "could set the code back to probing for every setting", "(another code text pauses the code while AdvancedMD shows it: every run reads it again)", "a one-cent line left off does not switch the code off: the code probes (THE CODE NEVER SWITCHES ITSELF OFF, below)",
          "then the visit is stuck, no new line is added in that run - a real claim must never wait because of this code - and every run's inspector step tries the void and the re-save again until the visit is free; the first run that finds no visit stuck goes on by itself, probing.",
          "move new lines to one cent, and at one cent the code probes; a fault while the chart shows the visit (or cannot be read): the visit is not sent again, William enters or checks it, and the code probes from the next run.")),
      [x_ for x_ in ("THE CODE NEVER SWITCHES ITSELF OFF", "It PAUSES one run at a time", "WILLIAM'S OWN SWITCHES STAY HIS") if x_ not in _qrb])
check("rulebook (open points 1 and 11, as built): at one cent the code probes from its first line - one cent never begins with a round of three - and the inspector step also looks at a coded visit of an earlier batch whose line is not decided yet",
      "It probes from its first one-cent line on (the amount only moves to one cent after something stopped a $0.00 line, so one cent never begins with a round of three)" in _qrb
      and "The same step also looks at a coded visit of an earlier batch whose line is not decided yet: when the claim check holds such a visit and no step ever looked at it, its line comes off there, a run late." in _qrb)
check("rulebook (5.1): nothing in the line says any more that the code switches itself off, goes off or waits for William's restart - the phrases of the earlier versions are gone (William's own stop is the one 'off until he restarts it' left)",
      not any(x_ in _qrb for x_ in ("OFF UNTIL WILLIAM RESTARTS IT", "switches the code off until William has looked", "at one cent the code goes off", "the code goes off", "(another code text switches the code off)", "a one-cent line left off switches the code off.",
                                    "switches M0004 off", "switches it off too", "a second left-off line switches M0004 off", "taken that way, M0004 is OFF - no second try", "a restart of 1123F does not restart it", "honoured only while the code is off")),
      [x_ for x_ in ("OFF UNTIL WILLIAM RESTARTS IT", "the code goes off", "switches M0004 off", "honoured only while the code is off") if x_ in _qrb])
check("runbook (5.2, B1-B3): the version check greps the CURRENT rule version (2026-11-25.1 since William's CCM word; .8 and .7 nowhere), and the import register is committed at once also while the code probes or is paused - the probe's memory is that register too",
      ("grep -c '%s'" % ver) in _STEP1 and '2026-11-10.8"' not in step and '2026-11-10.7"' not in step and 'The same when the line says "probing:" or "paused:".' in _STEP1
      and 'The same while the code probes or is paused (the QUALITY line says "probing:" or "paused:"): the probe\'s memory is that register too.' in _QR)
check("runbook (5.2, B4-B7): THE CODE NEVER SWITCHES ITSELF OFF with William's sentence - ONE line 'TOP OF THE REPORT - QUALITY CODE:' in every batch, copied word for word, and what each of its forms means (probing: do nothing by hand, bypass nothing; paused; going; accepted, once; stopped on William's word); the stuck visit and the left-off line in the new words",
      all(x_ in _QR for x_ in ('THE CODE NEVER SWITCHES ITSELF OFF - William 11/11/2026: "%s" (in force since November 12, 2026). No state of the code waits for William. The digest carries ONE line that starts "TOP OF THE REPORT - QUALITY CODE:" in every batch; copy it to the top of the report word for word, every run:' % _W1112,
          '"QUALITY CODE: probing (one line a run) - ..." = something stopped a line', "The import puts ONE line a run on the first eligible visit until one is billed - at one cent from its first line on (the amount only moves to one cent after something stopped a $0.00 line).", "one void and one re-save a run, no visit waits. Do nothing by hand, and bypass nothing.",
          '"QUALITY CODE: paused this run - ..." = no line was added in this run', "The next run looks again by itself.", '"QUALITY CODE: going - ..." = the normal flow', '"QUALITY CODE ACCEPTED BY MEDICARE - ..." = said once, in the first run that sees Medicare\'s answer.',
          '"QUALITY CODE: stopped on William\'s word ..." = only after his own QUALITY_CODE=stop.', '"QUALITY CODE: restarted on William\'s standing word ..." = said once',
          "(while William has stopped it, no line is added before his restart)", "a one-cent line left off does not switch the code off: it probes (THE CODE NEVER SWITCHES ITSELF OFF below), and the digest says at the top that AdvancedMD leaves the line off the claim and how many lines sit unbilled.",
          "then the visit is stuck: no new line is added in that run, and every run's inspector step re-saves it again (one re-save should release it). A void that failed = the visit is held WITH its line: the same - no new line in that run, and every run tries the void and the re-save again. The first run that finds no visit stuck goes on by itself, probing.",
          "at one cent the code probes. If the chart then shows part of the refused visit, or cannot be read, nothing is sent again and the digest names that visit at the top with its date and codes: William enters or checks that visit; no routine sends it again. The code probes from the next run.",
          "new lines carry one cent (one line a run from then on: at one cent the code probes, below)")),
      [x_ for x_ in ("THE CODE NEVER SWITCHES ITSELF OFF - William 11/11/2026", "Do nothing by hand, and bypass nothing.", "The next run looks again by itself.") if x_ not in _QR])
check("runbook (5.2, B8-B10): the M0004 paragraph and both switch paragraphs in the new words - M0004 probes where it went off, QUALITY_CODE=reset works only after William's own stop, MVP_CODE=reset has nothing left to restart",
      all(x_ in _QR for x_ in ("(that M0004 line is just void: nothing follows for M0004, and that clinician may get M0004 again)", "(after a second left-off line M0004 probes: one M0004 line a run in all until one is billed)", "taken that way, M0004 probes.",
          "an M0004 line taken off that way from a visit that then went through makes M0004 probe, and it does not count against the 1123F line.",
          '`QUALITY_CODE=reset` (on the ingest command only) starts a new round at $0.00 after William\'s own stop - only then; while the code probes, is paused or is going it does nothing and the log says "NOTHING TO RESTART" (take it out of the routine).',
          '`MVP_CODE=reset` (on the ingest command only) has nothing left to restart - M0004 never switches itself off any more - and the log says "NOTHING TO RESTART" (take it out of the routine); any other value adds no M0004 line and the log names it. `QUALITY_CODE=off` or `stop` stops M0004 too (it never rides without the 1123F line).',
          "`QUALITY_CODE=stop` = OFF until William restarts it", 'for stop it must say "stopped on William\'s word"')), [x_ for x_ in ("taken that way, M0004 probes.", "has nothing left to restart") if x_ not in _QR])
check("runbook (5.2): nothing in it says any more that the code goes OFF by itself or waits for William's restart (his own stop is the one OFF left); the one-cent round of three is gone with it",
      not any(x_ in _STEP1 for x_ in ("OFF UNTIL WILLIAM RESTARTS IT", "the code goes OFF until William has looked", "at one cent the code goes OFF.", "a one-cent line left off switches the code OFF.", "switches M0004 off", "M0004 is OFF until William restarts it",
                                      "does not restart M0004", "(a new round of 3)", 'after "the quality code is OFF"')), [x_ for x_ in ("OFF UNTIL WILLIAM RESTARTS IT", "switches M0004 off", "(a new round of 3)") if x_ in _STEP1])
check("rulebook and runbook (fix round 1, November 12, 2026): one sentence each says that until the next change a person looks at a visit held after the proof (known gaps B4, B5); and they say what K10 to K12 and K8 made true - the left-off line's patient is due "
      "again only 30 days after it was called left off, the step writes its entry before the void and a void line is a person's decision only without an entry of the routine's, a visit of a fault run is stuck and looked at in every run, the bypass advice comes only after a one-cent stop",
      all(x_ in _qrb for x_ in ("Until the next change a person looks at a visit held after the proof: after the proof the step takes the line off only when the edit's words name it, and it does not go back to a batch whose inspector step failed or was cut.",
                                 "November 12, 2026 - fix round 1: that patient is due again only once the line was called left off 30 days ago or more", "a line found void while its visit is still there is a person's decision only when no entry of the routine's is on record for it",
                                 "A visit of a fault, a time-out or a cut run while the call that carried the line was out is listed as stuck too", "that advice only once a ONE-CENT line was stopped or refused"))
      and all(x_ in _QR for x_ in ("Until the next change a person looks at a visit held AFTER the proof: after the proof the step takes the line off only when the edit's words name it, and it does not go back to a batch whose inspector step failed or was cut.",
                                    "November 12, 2026 - fix round 1: that patient is due again only once the line was called left off 30 days ago or more",
                                    "a line found void while its visit is still there is a person's decision (that patient gets no line again that year) only when no entry of the routine's is on record for it",
                                    "A visit of a fault, a time-out or a cut run while the call that carried the line was out (REFUSED below) is listed as stuck too", "that advice only once a ONE-CENT line was stopped or refused",
                                    'or "paused:" - no line is added in a paused run anyway')),
      [x_ for x_ in ("Until the next change a person looks at a visit held", "called left off 30 days ago or more", "is listed as stuck too") if x_ not in _qrb or x_.lower() not in _QR.lower()])
# November 12, 2026 - fix round 2 (K13, K15, K16, K17 - review notes G2, G4): the sentences of round 2, and the two runbook sentences of round 1 no check proved
_LS = open(os.path.join(ROOT, "docs", "SHARED_LESSONS.md")).read()
check("rulebook, runbook and lessons (fix round 2, November 12, 2026): a left-off line is read again until 30 days after it was CALLED left off (K13); a fault visit pauses the code only while it is held WITH its 1123F line that cannot be taken off - "
      "one held for its own reason stays on the report for William and the code goes on (K15); a cut try is said as cut off (K16); the PAUSES sentence and the lessons line name the fault visit (G4); the runbook's REFUSED and paused sentences (G2)",
      all(x_ in _qrb for x_ in ("it is read again until 30 days after it was called left off (billed after all = it counts; November 12, 2026 - fix round 2", "(still not billed three days after its visit was billed; read again until 30 days after it was called left off)",
                                 "such a visit pauses the code only while it is held WITH its 1123F line and the line cannot be taken off - when the step finds no 1123F line on it, or after the proof the hold's words do not name the line, it is held for its own reason: it stays on the report for William in every run until it is free, its patient stays marked, and the code goes on.",
                                 "a try the step had begun when the run was cut is said as cut off"))
      and all(x_ in _QR for x_ in ("the import reads it again until 30 days after it was called left off (November 12, 2026 - fix round 2;", "such a visit pauses the code only while it is held WITH its 1123F line and the line cannot be taken off",
                                    "\"the routine's last try was cut off before it ended; this run's step looks again\" (never \"could not take the line off\")",
                                    "November 12, 2026 - fix round 1: only once the inspector step has seen that visit free - until then it is stuck (THE HELD VISIT above); fix round 2: a visit the step finds held for its own reason with no 1123F line on it does not hold the probing back",
                                    "a visit of a fault run is not seen free yet (the line says it came from a fault - November 12, 2026; one the step found held for its own reason with no 1123F line on it pauses nothing"))
      and "while a visit of a fault run may still carry its line and is not yet seen free of it (November 12, 2026 - fix rounds 1 and 2: one held for its own reason with no 1123F line on it pauses nothing)" in _LS
      and "until 30 days after the visit was billed" not in _qrb and "until 30 days after the visit was billed" not in _QR and "no such line = it stays for William" not in _qrb and "no such line = it stays for William" not in _QR,
      [x_ for x_ in ("read again until 30 days after it was called left off", "pauses the code only while it is held WITH its 1123F line") if x_ not in _qrb or x_ not in _QR])
check("lessons (5.3): ONE dated line records William's standing word, rule version 2026-11-10.8 and what replaces 'off until William restarts it' - it is the newest line of the file, and the two older lines about the quality code stay as they are",
      sum(1 for l_ in _sl if re.match(r"- 2026-11-12T\d{4}Z \| chat \(quality code 1123F never switches itself off, rule version 2026-11-10\.8\) \| RULE \| ", l_) and _W1112 in l_ and "PROBES" in l_ and "PAUSES" in l_ and "QUALITY CODE ACCEPTED BY MEDICARE" in l_
          and l_.endswith("| practices/ehpa/rules.md (QUALITY CODE 1123F), scripts/helpers/claimocity_import.py (quality_state, mvp_state), claimocity_inspector.py (stuck visits), claimocity_report.py, nightly/claimocity_feed_step.md")) == 1
      and re.match(r"- 2026-11-12T\d{4}Z \| chat \(quality code 1123F never switches itself off", _sl[-1]) is not None and sum(1 for l_ in _sl if l_.startswith("- 2026-11-10T1200Z | ")) >= 1 and sum(1 for l_ in _sl if l_.startswith("- 2026-11-10T1435Z | ")) == 1, _sl[-1][:200])
# the insurance-check step: a void quality line never holds the visit (its function is run here with stand-ins; the rest of that helper is not loaded)
_vsrc = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py")).read(); _vsrc = _vsrc[_vsrc.index("def fast_set_insorder(v, order, removed=None, info=None):"):_vsrc.index("def main():")]
# 11/10/2026 (round 7): AdvancedMD builds a visit's insurance-order LIST from its order - the stand-ins show it, and give every live charge (visit_charges)
_LIST = lambda o_: "<insuranceorderlist>%s</insuranceorderlist>" % "".join('<insuranceorder sequence="%s" ordinal="%d"/>' % (s_, i_) for i_, s_ in enumerate(x_ for x_ in o_.split(",") if x_))
class _RS:
    CHG_FIELDS = ["fee", "pos"]; state = {"order": "1,2", "void": set(), "sent": []}
    @staticmethod
    def detail(cid): return '<r><patient id="pat1"/><visit id="vst1" episode="e1" insorder="%s">%s</visit><charge id="charge%s" fee="1.00" pos="32" void="%s"/></r>' % (_RS.state["order"], _LIST(_RS.state["order"]), cid, "1" if str(cid) in _RS.state["void"] else "0")
    @staticmethod
    def visit_charges(cid):
        r_ = ET.fromstring(_RS.detail(cid)); return r_.find(".//visit"), r_.find(".//patient"), [ET.fromstring(_RS.detail(c_)).find(".//charge") for c_ in ("10", "11") if c_ not in _RS.state["void"]]
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
    def detail(cid):
        if (VQ.get("dfail") or {}).get(str(cid), 0) > 0: VQ["dfail"][str(cid)] -= 1; return "<r><Fault><description>charge not found</description></Fault></r>"      # dfail: that many reads of the charge fail first
        pc, fee = VQ["proc"].get(str(cid), ("pcodeX", "1.00")); return '<r><patient id="pat1"/><visit id="vst1" episode="e1" insorder="%s">%s</visit><charge id="charge%s" fee="%s" pos="32" proccode="%s" void="%s"/></r>' % (VQ["order"], _LIST(VQ["order"]), cid, fee, pc, "1" if str(cid) in VQ["void"] else "0")
    @staticmethod
    def visit_charges(cid):
        r_ = ET.fromstring(_RS2.detail(cid)); return r_.find(".//visit"), r_.find(".//patient"), [ET.fromstring(_RS2.detail(c_)).find(".//charge") for c_ in sorted(VQ["proc"]) if c_ not in VQ["void"]]
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
import time as _tm; _sl0 = _tm.sleep; _tm.sleep = lambda *_a: None
try:
    VQ.update(order="1,2", void=set(), sent=[], fault=None, dfail={"11": 2}); _rm = []; okd1, md1 = _ns2["fast_set_insorder"](_qrow, "2", _rm); _sent1 = list(VQ["sent"])
    VQ.update(order="1,2", void=set(), sent=[], fault=None, dfail={"11": 3}); _rm = []; okd2, md2 = _ns2["fast_set_insorder"](_qrow, "2", _rm)
finally: _tm.sleep = _sl0; VQ["dfail"] = {}
check("insurance check (NH2-3): the quality line's detail fails twice and answers the third time - the visit's own order is still set (a failed read never keeps it from being set at once), both charges echoed",
      okd1 is True and len(_sent1) == 1 and 'id="charge10"' in _sent1[0] and 'id="charge11"' in _sent1[0], (okd1, md1, _sent1))
check("insurance check (NH2-3): ... three failed reads - held as before (nothing is echoed without a line nobody could check), and the message names that line", okd2 is False and "the no-charge line charge11 could not be read in three tries" in md2 and md2.startswith("detail read mismatch"), (okd2, md2))
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
VF_STAND = {"amd": {"login_cached": lambda *a: None, "msg": _AM2.msg, "post": _AM2.post}, "resave": {"detail": _RS2.detail, "CHG_FIELDS": _RS2.CHG_FIELDS, "visit_charges": _RS2.visit_charges},
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
check("insurance check step (section 7): refused with and without the line - HOLD, and the hold says 'insorder not applied' with the quality line named (the words the import starts probing on; the visit itself is for a person)",
      _ve == "" and _vr and _vr["decision"] == "HOLD" and any(h_.startswith("insorder not applied on vst1 (the visit carries the quality line charge11: resave FAULT") for h_ in _vr["hold"]) and not _vr.get("quality_removed"), (_ve, _vr))
_vr, _vo, _ve = vf_run(dict(_qrow, quality_codes=None, quality_charge=None), "always")
check("insurance check step: a visit without the line whose echo is refused - held in words that say what its list shows (round 7, 4.4: it still bills to its old order 2), under order_differs, and the hold says it is a label in this report only (4.6)",
      _ve == "" and _vr and len(_vr["hold"]) == 1 and _vr["hold"][0].startswith("vst1 still bills to its old insurance order 2 (resave FAULT") and _vr["hold"][0].endswith("HELD in this report only - AdvancedMD will still bill this visit to its insurance order at the next claim run unless someone stops it")
      and _vr.get("order_differs") == ["vst1"] and not _vr.get("no_order_list"), (_ve, _vr))
VQ["dfail"] = {"11": 3}; _vr, _vo, _ve = vf_run(_qrow, None); VQ["dfail"] = {}
check("insurance check step (NH2-3): the quality line cannot be read in three tries - HOLD as before (the words the import starts probing on), and FIRST in the hold list a plain sentence: the order was NOT set, the claim goes out under the old order unless William changes it",
      _ve == "" and _vr and _vr["decision"] == "HOLD" and _vr["hold"][0].startswith("the order of vst1 was NOT set because its no-charge quality line could not be read (three tries) - the claim goes out under the old order") and _vr["hold"][0].endswith("unless William changes it")
      and any(h_.startswith("insorder not applied on vst1 (the visit carries the quality line charge11: detail read mismatch") for h_ in _vr["hold"]), (_ve, _vr))
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
        if IS.get("resave_fault"): return "<r><Fault><description>resave not accepted</description></Fault></r>"      # AdvancedMD does not inspect the visit again: it stays listed as it was
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
def is_run(errors, after=(), void_ok=True, proven=False, row=None, qproc=("pcode65441", "0.00"), qvoid=False, mproc=(MP, "0.00"), ids=("1010", "1011"), void_fails=None, resave_fault=False):
    IS.clear(); IS.update(listed={"101": list(errors)}, after=list(after), void_ok=void_ok, voided=[], resaved=[], bypassed=[], void=({"1011"} if qvoid else set()), qproc=qproc, mproc=mproc, ids=ids, void_fails=void_fails, resave_fault=resave_fault)
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
check("inspector (NH2-2): ... that entry says the re-save after the void worked (resave_ok) and does not claim the visit is still listed for the line", _ir["quality_removed"][0].get("resave_ok") is True and "still_named" not in _ir["quality_removed"][0], _ir["quality_removed"])
_ir, _io, _ie = is_run([E_NAME], proven=True, resave_fault=True); _v1, _s1 = list(IS["voided"]), len(IS["resaved"]); _ir2, _io2, _ie2 = is_run([E_NAME], after=[E_NAME], proven=True)
check("inspector (NH2-2): the line is voided but the re-save after the void is refused (the visit stays listed for the edit about the line), or the re-saved visit is still listed for words that name the line - the entry says resave_ok and still_named, so the import does not take it for the visit's own reason",
      _ie == "" and _ir["quality_removed"][0]["void_ok"] is True and _ir["quality_removed"][0].get("resave_ok") is False and _ir["quality_removed"][0].get("still_named") is True and _ir["quality_removed"][0]["released"] is False and len(_ir["held"]) == 1
      and _ie2 == "" and _ir2["quality_removed"][0].get("resave_ok") is True and _ir2["quality_removed"][0].get("still_named") is True and _ir2["quality_removed"][0]["released"] is False, (_ie, _ir, _ie2, _ir2))
check("inspector (2.5; 11/12/2026): ... such a visit of this very start is tried once more by the retry pass of the same start - the line is void already, so nothing is voided again: the visit is re-saved a second time and listed again; the second entry says retry_of this batch's own inspector register, and the visit stands ONCE on the held list",
      _v1 == [("pat1", "1011")] and _s1 == 2 and [(e_["void_ok"], e_.get("resave_ok"), e_.get("still_named"), e_["released"], e_.get("retry_of")) for e_ in _ir["quality_removed"]] == [(True, False, True, False, None), (True, False, True, False, "feed_inspector_T3.json")]
      and len(_ir["held"]) == 1 and len(_ir2["quality_removed"]) == 2 and _ir2["quality_removed"][1].get("retry_of") == "feed_inspector_T3.json" and len(_ir2["held"]) == 1, (_ir, _ir2, _v1, _s1))
_ir, _io, _ie = is_run([E_DATA], void_ok=False)
check("inspector (11.1): ... the void fails - no re-save is sent: the visit is held WITH its line ('quality': true), the entry says void_ok: false; the retry pass of the same start tries the void once more (11/12/2026) and records that try too - still ONE held row",
      _ie == "" and len(_ir["held"]) == 1 and _ir["held"][0].get("quality") is True and IS["resaved"] == [] and IS["voided"] == [("pat1", "1011"), ("pat1", "1011")] and _ir["quality_removed"][0]["void_ok"] is False and "cannot be voided" in _ir["quality_removed"][0]["note"]
      and [(e_["void_ok"], e_.get("retry_of")) for e_ in _ir["quality_removed"]] == [(False, None), (False, "feed_inspector_T3.json")], (_ie, _ir, IS["voided"]))
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
_MPR = dict(_MG0, probe="AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only (chart pat9, visit vst1, feed_import_20261111T0100Z.json)", probe_since="feed_import_20261111T0100Z.json", probe_words="Fault: no")
r, o = mdig([dict(qrow, mvp_codes=[], mvp_refused="Fault: no", mvp_tried="0.00")], dict(_MPR, off="this run: AdvancedMD refused a visit that carried M0004"), prev_m=dict(_MG0)); r2_, o2 = mdig([qrow], _MPR, prev_m=dict(_MPR))
check("digest (8.4, 8.6; D9): a refused visit with M0004 - at the top: the visit named, entered with the 1123F line only, M0004 goes on probing; and the probe itself at the top in the run it began (one M0004 line a run in all; the 1123F line goes on as before) - never 'OFF until William restarts it', never a restart switch",
      any("AdvancedMD refused 1 visit(s) that carried M0004; each was entered with the 1123F line only: pat9 vst1 (Fault: no) - M0004 goes on probing: one M0004 line a run in all until one is billed." in l_ for l_ in _TOP(o))
      and any(l_ == "  - TOP OF THE REPORT - the option code M0004 probes (one M0004 line a run in all until one is billed): AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only (chart pat9, visit vst1, feed_import_20261111T0100Z.json). The 1123F line goes on as before." for l_ in _TOP(o))
      and "probing - one M0004 line a run in all until one is billed." in o and "OFF until William restarts it" not in o and "MVP_CODE=reset" not in o, _TOP(o))
check("digest (8.6; D9): ... the same M0004 probe in the next batch is ONE plain line, not the top", not any("M0004" in l_ for l_ in _TOP(o2)) and "  - the option code M0004 still probes (since an earlier run): AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only" in o2
      and "probing - one M0004 line a run in all until one is billed." in o2, (_TOP(o2), o2[-600:]))
_MPS = "paused this run: AdvancedMD shows procedure id pcode692183 as 99497, not M0004 - no M0004 line while that is so; every run reads it again"
r, o = mdig([qrow], dict(_MG0, off=_MPS, paused=_MPS, wrong_code_text="99497"), prev_m=dict(_MG0)); r2_, o2 = mdig([qrow], dict(_MG0, off=_MPS, paused=_MPS, wrong_code_text="99497"), prev_m=dict(_MG0, off=_MPS, paused=_MPS))
check("digest (D9): an M0004 pause is at the top EVERY run - 'the option code M0004 is paused this run: ...' - and the headline says paused",
      all(any(l_ == "  - TOP OF THE REPORT - the option code M0004 is paused this run: AdvancedMD shows procedure id pcode692183 as 99497, not M0004 - no M0004 line while that is so; every run reads it again." for l_ in _TOP(x_)) and "paused this run - no M0004 line was added." in x_ for x_ in (o, o2)), (_TOP(o), _TOP(o2)))
_MSR = {"was": "AdvancedMD stores procedure id pcode692183 as 99497, not M0004 - William looks", "register": "feed_import_20261111T0000Z.json"}; _MSP = "the option code M0004 had switched itself off (%s) - William's standing word of November 11, 2026 restarts it" % _MSR["was"]
r, o = mdig([qrow], dict(_MG0, probe=_MSP, standing_restart=_MSR), prev_m=dict(_MG0, off=_MSR["was"], off_until_reset=_MSR["was"])); r2_, o2 = mdig([qrow], dict(_MG0, probe=_MSP), prev_m=dict(_MG0, probe=_MSP, standing_restart=_MSR))
check("digest (D9, section 3): M0004's restart on William's standing word is said ONCE at the top - in the run that reads the older register's own 'off until reset'; the next batch does not repeat it",
      any(l_ == "  - TOP OF THE REPORT - the option code M0004: restarted on William's standing word of November 11, 2026 - an earlier run had switched it off (%s)." % _MSR["was"] for l_ in _TOP(o)) and not any("standing word" in l_ for l_ in _TOP(o2)) and "still probes (since an earlier run)" in o2, (_TOP(o), _TOP(o2)))
r, o = mdig([qrow], dict(_MG0, off="this run: switched off (MVP_CODE=off)"), prev_m=dict(_MG0))
check("digest (8.7): William's own MVP_CODE=off is a plain line", not any("M0004" in l_ for l_ in _TOP(o)) and "M0004 switched off for this run by William's MVP_CODE=off" in o, o[-600:])
r, o = mdig([qrow], dict(_MG0, off="this run: MVP_CODE='stop' is not a value the import knows (off, reset) - no M0004 line added"), prev_m=dict(_MG0))
check("digest (8.7): an MVP_CODE value the import does not know is at the top, named", any("the option code M0004 is off in this run: this run: MVP_CODE='stop' is not a value the import knows" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = mdig([qrow], dict(_MG0, notes=["NOTHING TO RESTART - MVP_CODE=reset was ignored (M0004 is not switched off; take the switch out of the routine)"]), prev_m=dict(_MG0))
check("digest (8.7): an MVP_CODE=reset that had nothing to restart is at the top", any("NOTHING TO RESTART - MVP_CODE=reset was ignored" in l_ for l_ in _TOP(o)), _TOP(o))
r, o = mdig([dict(qrow, mvp_codes=[], mvp_charge="", mvp_not_stored="0.00")], dict(_MPR), prev_m=dict(_MPR))
check("digest: a visit stored without its M0004 line is at the top - M0004 goes on probing", any(l_.startswith("  - TOP OF THE REPORT - AdvancedMD stored 1 visit(s) WITHOUT the M0004 line that was sent with it (the visit itself is entered): pat9 vst1 - M0004 goes on probing.") for l_ in _TOP(o)), _TOP(o))
_MRE = lambda **e: dict({"visit": "1", "pid": "pat9", "charge": "charge78", "code": "M0004", "fee": "0.00", "why": "Pattern 88001: procedure M0004 is not payable", "void_ok": True, "released": True, "at": "x"}, **e)
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE()]))
check("digest (11.6; D9): the M0004 line taken off a held visit that went through - at the top: M0004 probes (one M0004 line a run in all until one is billed), and it does not count against 1123F; the 1123F block does not report it as its own",
      any("the routine took the M0004 line charge78 off held visit vst1 (pat9; the hold: Pattern 88001: procedure M0004 is not payable) and the visit went through without it: M0004 probes: one M0004 line a run in all until one is billed; this does not count against the 1123F line." in l_ for l_ in _TOP(o))
      and not any("took the quality line" in l_ for l_ in _TOP(o)) and "OFF until William restarts it" not in o, _TOP(o))
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(released=False)])); r2_, o2 = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(void_ok=False, released=False, note="the void failed: Fault")]))
r3_, o3 = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(released=False, resave_ok=False, still_named=True)]))
check("digest (11.6; D9): ... the visit still held - at the top, its clinician may get M0004 again; a void that failed - at the top: the visit is held WITH that line, no new M0004 line while that is so, every run tries the void and the re-save again; still listed for the edit about the line - every run re-saves the visit again",
      any("but the visit is still held for its own reason" in l_ and "its clinician may get M0004 again" in l_ for l_ in _TOP(o))
      and any("the routine could not take the M0004 line off held visit vst1 (pat9: the void failed: Fault) - the visit is held WITH that line. No new M0004 line is added while that is so; every run tries the void and the re-save again." in l_ for l_ in _TOP(o2))
      and any("the routine took the M0004 line charge78 off held visit vst1 (pat9), but the visit is still listed for the edit about the line (Pattern 88001: procedure M0004 is not payable); the re-save after the void failed - no new M0004 line is added while that is so; every run re-saves the visit again (one re-save should release it)." in l_ for l_ in _TOP(o3))
      and "William looks" not in "".join(_TOP(o2) + _TOP(o3)) and "switches M0004 off" not in o2 + o3, (_TOP(o), _TOP(o2), _TOP(o3)))
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(void_ok=False, listed=False, retry_of="feed_inspector_20261110T0100Z.json", note="the visit is no longer listed by the Claim Inspector - nothing done")]))
check("digest (D9): the step's retry found a visit that was held with its M0004 line free again - one plain line, nothing about M0004 at the top",
      not any("M0004" in l_ for l_ in _TOP(o)) and "  - visit vst1 (pat9), which was held with its M0004 line, is free again (the visit is no longer listed by the Claim Inspector - nothing done) - nothing was done to it; M0004 goes on by itself, probing." in o, (_TOP(o), o[-700:]))
r, o = mdig([_mrow], _MG0, prev_m=dict(_MG0), insp_=_INS([], [_MRE(**{"with": "1123F"})]))
check("digest (NH2-1): an M0004 line that came off only with its 1123F line - one plain line (that clinician may get M0004 again), never 'M0004 is OFF'", "the M0004 line charge78 of visit vst1 (pat9) came off together with its 1123F line (M0004 never rides without it) - that clinician may get M0004 again." in o
      and not any("M0004" in l_ for l_ in _TOP(o)), (o[-700:], _TOP(o)))
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
check("inspector (11.6, NH2-1): an edit that names ONLY 1123F (with its zero amount) - the M0004 line comes off WITH it (M0004 never rides without the 1123F line): two voids, and the M0004 entry says it came off with 1123F",
      _ie == "" and IS["voided"] == [("pat1", "1011"), ("pat1", "1012")] and [(e_["code"], e_.get("with")) for e_ in _ir["quality_removed"]] == [("1123F", None), ("M0004", "1123F")], (_ie, _ir, IS["voided"]))
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
check("inspector (11.6): both lines to come off, and one of them cannot be shown live - NOTHING is voided (not even the line that could be): held with both lines - also in the retry pass's second try of the same start (11/12/2026), which records its two entries beside the first two", _ie == "" and IS["voided"] == [] and IS["resaved"] == []
      and [(e_["code"], e_["void_ok"], bool(e_.get("retry_of"))) for e_ in _ir["quality_removed"]] == [("1123F", False, False), ("M0004", False, False), ("1123F", False, True), ("M0004", False, True)]
      and len(_ir["held"]) == 1 and _ir["held"][0].get("quality") is True and _ir["held"][0].get("mvp") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_Z2], proven=True, row=MROW, ids=M3, void_fails="1011")
check("inspector (11.6): the first void fails - nothing else is tried (the M0004 line is not voided, no re-save): held WITH both lines, both entries void_ok false (the second says it was not tried); the retry pass's second try of the same start ends the same way",
      _ie == "" and IS["voided"] == [("pat1", "1011"), ("pat1", "1011")] and IS["resaved"] == [] and [(e_["code"], e_["void_ok"], bool(e_.get("retry_of"))) for e_ in _ir["quality_removed"]] == [("1123F", False, False), ("M0004", False, False), ("1123F", False, True), ("M0004", False, True)]
      and "not tried" in _ir["quality_removed"][1]["note"] and "not tried" in _ir["quality_removed"][3]["note"] and len(_ir["held"]) == 1 and _ir["held"][0].get("quality") is True and _ir["held"][0].get("mvp") is True, (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3, void_ok=False)
check("inspector (11.6): the held row says names_mvp when the words name the M0004 line", _ie == "" and _ir["held"][0].get("names_mvp") is True and _ir["held"][0].get("mvp") is True and "names_line" not in _ir["held"][0], (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], after=[E_DATA], proven=True, row=MROW, ids=M3)
check("inspector (11.6): the visit is still listed after the M0004 line is gone - held for its own reason; the row says it still carries the 1123F line (not M0004); the entry says released: false",
      _ie == "" and _ir["held"][0].get("quality") is True and "mvp" not in _ir["held"][0] and _ir["quality_removed"][0]["released"] is False, (_ie, _ir))
_ir, _io, _ie = is_run([E_MN], after=[E_ADVQ], proven=True, row=MROW, ids=M3)
check("inspector (11.6, section 7): after ONLY the M0004 line is taken off, an advisory whose words name the 1123F line still on the visit is NOT bypassed - held, the row says its words name that line",
      _ie == "" and IS["bypassed"] == [] and len(_ir["held"]) == 1 and _ir["held"][0].get("quality") is True and _ir["held"][0].get("names_line") is True and _ir["quality_removed"][0]["released"] is False, (_ie, _ir, IS["bypassed"]))
_ir, _io, _ie = is_run([E_QN], after=[E_ADVM], proven=True, row=MROW, ids=M3)
check("inspector (11.6, 8.6, NH2-1): ... an edit that names only 1123F, with an advisory about M0004 listed afterwards - the M0004 line came off with the 1123F line, so no M0004 line is left on the visit: released, nothing held, the M0004 entry is not blamed",
      _ie == "" and IS["voided"] == [("pat1", "1011"), ("pat1", "1012")] and _ir["held"] == [] and all(e_["released"] is True for e_ in _ir["quality_removed"]) and _ir["quality_removed"][1].get("with") == "1123F", (_ie, _ir, IS["bypassed"]))
_ir, _io, _ie = is_run([E_MN], proven=True, row=MROW, ids=M3); json.dump(_ir, open(os.path.join(REGDIR, "feed_inspector_T3.json"), "w")); _F3 = ci.quality_files("T4"); rmreg("feed_inspector_T3.json")
check("inspector -> import (11.6): the M0004 entry the inspector step writes is what the import reads (quality_files: removed, with its code)", [(e_[1]["code"], e_[1]["charge"]) for e_ in (_F3["removed"].get("T3") or [])] == [("M0004", "charge1012")], _F3["removed"])
_ins_ns.update(MVP_CODE="M0004", MVP_PCODE="pcode692183")
check("inspector and import: the same test for which no-charge line the words name (names_lines, every phrase both ways)", all(_ins_ns["names_lines"](w_, "charge7000011", "charge7000012") == ci.names_lines(w_, "charge7000011", "charge7000012") for w_, _r in _NL))
# 11/12/2026 (William 11/11/2026: "dont stop this dont let it stop make sure this suceeds") - THE RETRY PASS of the inspector step (specification 2.5), run INSIDE this process with
# stand-ins, never as a program: the visits the import register's gates list under "stuck" (tried again until free) and under "open_lines" (only looked at), of this batch or an earlier one.
# Visit N has the charges N0 (its own 99309), N1 (the 1123F line) and N2 (the M0004 line); RT says what the stand-in AdvancedMD shows and records what the step did.
RT = {}
QR = lambda r_: (r_ or {}).get("quality_removed") or []; HL = lambda r_: (r_ or {}).get("held") or []      # the step's register as the checks read it (no register = nothing recorded)
def _rt_detail(cid):
    cid = re.sub(r"\D", "", str(cid)); vid = cid[:-1]
    if cid in RT["unread"]: raise RuntimeError("detail read failed")
    pc, fee = RT["proc"].get(cid, ("pcode65119", "141.00")); bill = '<insbilllist><insbill billeddate="11/12/2026"/></insbilllist>' if cid in RT["billed"] else ""
    return '<r><patient id="pat%s"/><visit id="vst%s" episode="e1"/><charge id="charge%s" proccode="%s" fee="%s" pos="32" void="%s">%s</charge></r>' % (vid, vid, cid, pc, fee, "1" if cid in RT["void"] else "0", bill)
def _rt_vc(cid):
    cid = re.sub(r"\D", "", str(cid)); vid = cid[:-1]; ids_ = RT["vc"].get(vid) or [vid + "0"] + sorted(c_ for c_ in RT["proc"] if c_[:-1] == vid and c_ != vid + "0")
    r_ = ET.fromstring(_rt_detail(ids_[0])); return r_.find(".//visit"), r_.find(".//patient"), [ET.fromstring(_rt_detail(c_)).find(".//charge") for c_ in ids_ if c_ not in RT["void"]]
def _rt_post(body, timeout=0):
    if "getclaiminspectorcharges" in body:      # the listing: call number RT["lists"]; a call named in list_fault is answered with a fault
        RT["lists"] += 1
        if RT["lists"] in RT["list_fault"]: return "<r><Fault><description>the listing is not available</description></Fault></r>"
        return "<r>%s</r>" % "".join('<visit id="vst%s" patientid="pat%s">%s</visit>' % (v_, v_, "".join('<error id="%s" number="%s" name="%s"/>' % (e_["id"], e_["number"], e_["text"]) for e_ in es)) for v_, es in RT["listed"].items() if es)
    if "bypassclaimedits" in body: RT["bypassed"].append(re.findall(r'claimedit id="([^"]+)"', body)); return "<r><Fault><description>no</description></Fault></r>" if RT["bypass_fault"] else "<r/>"
    if "updvisitwithnewcharges" in body:
        v_ = re.search(r'<visit [^>]*\bid="vst(\d+)"', body).group(1); RT["resaved"].append(body)
        if v_ in RT["resave_fault"]: return "<r><Fault><description>resave not accepted</description></Fault></r>"      # AdvancedMD does not inspect the visit again: it stays listed as it was
        if v_ in RT["after"]: RT["listed"][v_] = list(RT["after"][v_])      # the visit re-saved: AdvancedMD lists what `after` says for it
    return "<r/>"
def _rt_void(pid, cid):
    cid = re.sub(r"\D", "", str(cid)); RT["voided"].append(cid)
    if cid in RT["void_raises"]: raise RuntimeError("the void call broke")
    if cid in RT["void_fails"] or cid in RT["void_fail_once"]: RT["void_fail_once"].discard(cid); return False, "<Fault><description>the charge cannot be voided</description></Fault>"
    RT["void"].add(cid)
    if cid in RT["void_cuts"]: raise _RTCut("the process is cut off right after the void")      # November 12, 2026 - fix round 1 (K10)
    return True, "ok"
class _RTCut(BaseException): pass      # the step's process is cut off (a killed session): nothing after this moment runs
def _rt_hist(pid):      # fix round 1 (K11): the chart's history as gettxhistory shows it - the code TEXT in proccode - for the charges RT["hist"] lists for that chart
    r_ = ET.Element("r")
    for a_ in RT.get("hist") or []:
        if re.sub(r"\D", "", str(pid)) == re.sub(r"\D", "", a_.get("pid", "")): ET.SubElement(r_, "charge", {k_: v_ for k_, v_ in a_.items() if k_ != "pid"})
    return r_
RT_STAND = {"amd": {"login_cached": lambda *a: None, "msg": lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s">%s</ppmdmsg>' % (action, children), "post": _rt_post},
            "resave": {"detail": _rt_detail, "visit_charges": _rt_vc, "CHG_FIELDS": ["fee", "pos"], "_extins_xml": lambda vis, h: ""}, "txh": {"fetch": _rt_hist},
            "dx_primary_fix": {"plan": lambda codes, pc: ("ok", codes), "save_visit_dx": lambda cid, d: ("ok", None), "I10_DCODE": "dcode1"}, "void_tx": {"void_charge": _rt_void}}
def rt_run(created=(), qgate=None, mgate=None, listed=None, after=None, prev=None, **kw):
    RT.clear(); RT.update(listed={k_: list(v_) for k_, v_ in (listed or {}).items()}, after=dict(after or {}), voided=[], resaved=[], bypassed=[], lists=0, proc=dict(kw.get("proc") or {}), vc=dict(kw.get("vc") or {}), hist=list(kw.get("hist") or []),
                          bypass_fault=bool(kw.get("bypass_fault")), **{k_: set(kw.get(k_) or ()) for k_ in ("void", "billed", "unread", "void_fails", "void_fail_once", "void_raises", "resave_fault", "list_fault", "void_cuts")})
    reg_ = {"created": list(created), "quality_gate": dict({"confirmed": False, "fee": "0.00"}, **(qgate or {}))}
    if mgate is not None: reg_["mvp_gate"] = mgate
    json.dump(reg_, open(os.path.join(isd, "registers", "feed_import_T5.json"), "w")); f_ = os.path.join(isd, "registers", "feed_inspector_T5.json")
    if prev is not None: json.dump(prev, open(f_, "w"))
    elif os.path.exists(f_): os.remove(f_)
    try: o_, e_ = run_inside(os.path.join(ROOT, "scripts", "helpers", "claimocity_inspector.py"), RT_STAND, isd, env={"FEED_STAMP": "T5", "FEED_DX_CACHE": os.path.join(isd, "dx.json")})
    except _RTCut: o_, e_ = "", "cut"      # the process was cut off: what is on disk is all the next run will read
    res = json.load(open(f_)) if os.path.exists(f_) else None      # None = the step wrote no register
    if os.path.exists(f_): os.remove(f_)
    return res, o_, e_
def ROW_(vid, q=True, m=False):      # a row of this batch's import register for visit vid
    r_ = {"visit": "vst%s" % vid, "pid": "pat%s" % vid, "charges": ["charge%s0" % vid] + (["charge%s1" % vid] if q else []) + (["charge%s2" % vid] if m else []), "cpts": ["99309"], "dos": "11/10/2026", "fac": "fac32"}
    if q: r_.update(quality_charge="charge%s1" % vid, quality_codes=["1123F"], quality_fee="0.00")
    if m: r_.update(mvp_charge="charge%s2" % vid, mvp_codes=["M0004"], mvp_fee="0.00", mvp_prof="prof13")
    return r_
def SK(vid, code="1123F", what="the routine could not take the line off", why="Pattern 77002: Claim line requires review before submission", reg="feed_inspector_T4.json", **kw):      # an item of a gate's "stuck" list, as the import writes it
    return dict({"chart": "pat%s" % vid, "visit": "vst%s" % vid, "charge": "charge%s%s" % (vid, "2" if code == "M0004" else "1"), "own": "charge%s0" % vid, "code": code, "fee": "0.00", "with": "", "why": why, "register": reg, "what": what, "since": reg}, **kw)
OL = lambda vid, **kw: {k_: v_ for k_, v_ in SK(vid, why="", reg="feed_import_T4.json", **kw).items() if k_ not in ("what", "since")}      # an item of a gate's "open_lines" list
PR = lambda vid, m=False: dict({"%s1" % vid: (QP, "0.00")}, **({"%s2" % vid: (MP, "0.00")} if m else {}))                                   # what the stand-in stores for the no-charge lines of visit vid
_NOQ = [ROW_(101, q=False)]      # this batch's own visit carries no line and is not listed: the normal pass has nothing to do
_PRV0 = {"fixed": [], "bypassed": [], "held": [], "laterality": []}
_e0 = {"visit": "901", "pid": "pat901", "charge": "charge9011", "code": "1123F", "fee": "0.00", "why": "Pattern 77002: x", "void_ok": True, "released": True, "at": "x"}
_ir, _io, _ie = rt_run(created=_NOQ, listed={"101": [E_DATA]}, prev=dict(_PRV0, quality_removed=[_e0, "odd"]))
check("inspector (2.5, point 1): a second start of the step under one stamp KEEPS what the first start recorded about no-charge lines (until 11/12/2026 those entries were lost with the register the second start wrote anew)",
      _ie == "" and QR(_ir) == [_e0] and len(HL(_ir)) == 1 and RT["voided"] == [], (_ie, _ir))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_DATA]}, after={"201": []}, proc=PR(201))
check("inspector (2.5, K2c): the retry pass reads the visits stuck held with their line from this batch's gates - a visit of an EARLIER batch whose void had failed: the line is voided now, the visit re-saved on its own first charge and listed again - released. The entry says retry_of (the register that first recorded the visit), "
      "and the step's register is written although the normal pass listed no visit of this batch (such a run wrote no register until now)",
      _ie == "" and RT["voided"] == ["2011"] and len(RT["resaved"]) == 1 and 'id="charge2010"' in RT["resaved"][0] and "charge2011" not in RT["resaved"][0] and HL(_ir) == [] and (_ir or {}).get("fixed") == []
      and [{k_: e_.get(k_) for k_ in ("visit", "pid", "charge", "code", "fee", "void_ok", "resave_ok", "released", "retry_of")} for e_ in QR(_ir)]
          == [{"visit": "201", "pid": "pat201", "charge": "charge2011", "code": "1123F", "fee": "0.00", "void_ok": True, "resave_ok": True, "released": True, "retry_of": "feed_inspector_T4.json"}]
      and QR(_ir)[0]["why"].startswith("Pattern 77002") and "still_named" not in QR(_ir)[0] and "listed" not in QR(_ir)[0], (_ie, _ir, RT["voided"], _io[-300:]))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={}, proc=PR(201)); _ir2, _io2, _ie2 = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={}, proc=PR(201), void=("2011",))
check("inspector (2.5 b): a stuck visit that the Claim Inspector no longer lists is FREE - one entry with listed: false, released, retry_of and the note (void_ok = whether the line reads void: no while it is still on the visit, yes when it was voided before); NOTHING is voided or saved",
      _ie == "" and RT["voided"] == [] and RT["resaved"] == [] and HL(_ir) == [] and len(QR(_ir)) == 1
      and {k_: QR(_ir)[0].get(k_) for k_ in ("visit", "charge", "code", "listed", "released", "void_ok", "retry_of", "note")}
          == {"visit": "201", "charge": "charge2011", "code": "1123F", "listed": False, "released": True, "void_ok": False, "retry_of": "feed_inspector_T4.json", "note": "the visit is no longer listed by the Claim Inspector - nothing done"}
      and _ie2 == "" and [(e_["listed"], e_["void_ok"]) for e_ in QR(_ir2)] == [(False, True)], (_ie, _ir, _ir2))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201, what="the line is off, but the visit is still listed for the edit about it", why="Pattern 88001: Charge amount is zero for procedure 1123F")]}, listed={"201": [E_NAME]}, after={"201": []}, proc=PR(201), void=("2011",))
check("inspector (2.5 c, d): a stuck visit whose line is void ALREADY (the re-save after the void had failed) - there is nothing to void, and that is no reason to stop: the visit is re-saved again and listed again - released",
      _ie == "" and RT["voided"] == [] and len(RT["resaved"]) == 1 and [(e_["void_ok"], e_.get("resave_ok"), e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [(True, True, True, "feed_inspector_T4.json")] and HL(_ir) == [], (_ie, _ir))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201, what="the line is off, but the visit is still listed for the edit about it", why="Pattern 88001: Charge amount is zero for procedure 1123F")]}, listed={"201": [E_NAME]}, proc=PR(201), void=("2011",), resave_fault=("201",))
check("inspector (2.5 d, e): ... the re-save is refused again - the entry says resave_ok false and still_named true (not released), and the visit goes on this batch's held list; the next run re-saves it again",
      _ie == "" and len(RT["resaved"]) == 1 and [(e_["void_ok"], e_.get("resave_ok"), e_.get("still_named"), e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [(True, False, True, False, "feed_inspector_T4.json")]
      and [(h_["visit"], h_["pid"]) for h_ in HL(_ir)] == [("201", "pat201")] and "quality" not in HL(_ir)[0], (_ie, _ir))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_DATA]}, proc=PR(201), void_fails=("2011",))
check("inspector (2.5 c): the void fails AGAIN - the entry says void_ok false with the reason, NO re-save is sent, and the visit goes on this batch's held list with its line ('quality': true); the next run tries again",
      _ie == "" and RT["voided"] == ["2011"] and RT["resaved"] == [] and [(e_["void_ok"], e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [(False, False, "feed_inspector_T4.json")] and "the void failed" in QR(_ir)[0]["note"]
      and [(h_["visit"], h_["pid"], h_.get("quality")) for h_ in HL(_ir)] == [("201", "pat201", True)], (_ie, _ir))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_DATA]}, proc={"2011": ("pcode65119", "141.00")})
check("inspector (2.5 c): a recorded charge that does not show itself as the no-charge line (another procedure, a real amount) is NEVER voided by the retry either: one entry with void_ok false and the reason; nothing else is tried for that visit",
      _ie == "" and RT["voided"] == [] and RT["resaved"] == [] and [(e_["void_ok"], e_.get("retry_of")) for e_ in QR(_ir)] == [(False, "feed_inspector_T4.json")] and "not voided" in QR(_ir)[0]["note"], (_ie, _ir))
_ir, _io, _ie = rt_run(created=[ROW_(101)], listed={"101": [E_DATA]}, after={"101": []}, proc=PR(101), void_fail_once=("1011",))
check("inspector (2.5): a visit of THIS very start that the normal pass could not free (its void failed) is tried once more by the retry pass of the same start - here the second void works: the line is off, the visit re-saved and released. Both tries are on record; the second says retry_of this batch's own inspector register",
      _ie == "" and RT["voided"] == ["1011", "1011"] and len(RT["resaved"]) == 1 and [(e_["void_ok"], e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [(False, False, None), (True, True, "feed_inspector_T5.json")] and len(HL(_ir)) == 1, (_ie, _ir))
_e1 = {"visit": "101", "pid": "pat101", "charge": "charge1011", "code": "1123F", "fee": "0.00", "why": "Pattern 77002: x", "void_ok": False, "released": False, "note": "the void failed: x", "at": "x"}
_ir, _io, _ie = rt_run(created=[ROW_(101)], listed={}, proc=PR(101), prev=dict(_PRV0, quality_removed=[_e1]))
check("inspector (2.5): a second start under the same stamp tries the visit the FIRST start could not free (its carried entry says stuck) - here the Claim Inspector no longer lists it: free, recorded beside the first start's entry",
      _ie == "" and [(e_.get("listed"), e_.get("retry_of")) for e_ in QR(_ir)] == [(None, None), (False, "feed_inspector_T5.json")] and RT["voided"] == [] and RT["resaved"] == [], (_ie, _ir))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"confirmed": True}, mgate={"stuck": [SK(201, code="M0004", why="Pattern 88002: procedure M0004 is not payable", **{"with": "charge2011"})]}, listed={"201": [E_MN]}, after={"201": []}, proc=PR(201, m=True))
check("inspector (2.5, 2.6): the same for a visit stuck with its M0004 line (the mvp_gate's list) - only the M0004 line is voided (the 1123F line stays on the visit and in the re-save), the visit re-saved and released; the entry says code M0004 and retry_of",
      _ie == "" and RT["voided"] == ["2012"] and len(RT["resaved"]) == 1 and "charge2011" in RT["resaved"][0] and "charge2012" not in RT["resaved"][0]
      and [(e_["code"], e_["charge"], e_["void_ok"], e_["released"], e_.get("retry_of"), e_.get("with")) for e_ in QR(_ir)] == [("M0004", "charge2012", True, True, "feed_inspector_T4.json", None)], (_ie, _ir, RT["voided"]))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"confirmed": True, "stuck": [SK(201, **{"with": "charge2012"})]}, mgate={"stuck": [SK(201, code="M0004", **{"with": "charge2011"})]}, listed={"201": [E_Z2]}, after={"201": []}, proc=PR(201, m=True))
check("inspector (2.5): a visit stuck with BOTH no-charge lines (named by both gates) - both are voided, ONE re-save on the visit's own charge, one entry per line, each with retry_of",
      _ie == "" and RT["voided"] == ["2011", "2012"] and len(RT["resaved"]) == 1 and [(e_["code"], e_["void_ok"], e_["released"], e_.get("retry_of"), e_.get("with")) for e_ in QR(_ir)]
          == [("1123F", True, True, "feed_inspector_T4.json", None), ("M0004", True, True, "feed_inspector_T4.json", None)], (_ie, _ir, RT["voided"]))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"confirmed": True, "stuck": [SK(201, **{"with": "charge2012"})]}, listed={"201": [E_QN]}, after={"201": []}, proc=PR(201, m=True))
check("inspector (2.5, NH2-1): a visit stuck with its 1123F line that also carries the M0004 line - the M0004 line comes off WITH it (it never rides without the 1123F line), and its entry says so (not M0004's fault)",
      _ie == "" and RT["voided"] == ["2011", "2012"] and [(e_["code"], e_.get("with"), e_["released"]) for e_ in QR(_ir)] == [("1123F", None, True), ("M0004", "1123F", True)], (_ie, _ir, RT["voided"]))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={}, proc=PR(201), list_fault=(2,))
check("inspector (2.5 a): a listing AdvancedMD answers with a fault shows NOTHING - the pass frees nobody on it (read as an empty list it would say 'no visit is listed'): no entry, no register, nothing voided or saved; the next run tries again",
      _ie == "" and _ir is None and RT["voided"] == [] and RT["resaved"] == [] and "the Claim Inspector listing was not answered - 1 visit(s) not looked at" in _io, (_ie, _ir, _io[-300:]))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_DATA]}, after={"201": []}, proc=PR(201), list_fault=(3,))
check("inspector (2.5 e): the listing AFTER the re-save is a fault - the visit is not shown free: the entry says void_ok true, released false, still_named true and 'the listing after the re-save failed'; the next run lists it again",
      _ie == "" and RT["voided"] == ["2011"] and len(RT["resaved"]) == 1 and [(e_["void_ok"], e_.get("resave_ok"), e_["released"], e_.get("still_named"), e_.get("note"), e_.get("retry_of")) for e_ in QR(_ir)]
          == [(True, True, False, True, "the listing after the re-save failed", "feed_inspector_T4.json")], (_ie, _ir))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_ADV]}, proc=PR(201)); _b1 = list(RT["bypassed"]); _ir2, _io2, _ie2 = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_ADV]}, proc=PR(201), bypass_fault=True)
check("inspector (2.5 b2): a stuck visit listed with advisories ONLY - they are bypassed as the step always does and the visit is free: nothing voided, nothing saved (the hold is gone, so the line stays); the entry is the 'free' one with its own note. When the bypass itself is answered with a fault, no entry is written and the next run tries again",
      _ie == "" and _b1 == [["e4"]] and [(e_.get("listed"), e_.get("released"), e_.get("note"), e_.get("retry_of")) for e_ in QR(_ir)] == [(False, True, "only advisories remained - bypassed, nothing voided", "feed_inspector_T4.json")]
      and _ie2 == "" and _ir2 is None and RT["voided"] == [] and RT["resaved"] == [], (_ie, _ir, _b1, _ir2))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_DATA]}, proc=PR(201), billed=("2010",)); _v1, _s1 = list(RT["voided"]), list(RT["resaved"])
_ir2, _io2, _ie2 = rt_run(created=_NOQ, qgate={"stuck": [SK(201)]}, listed={"201": [E_DATA]}, proc=PR(201), unread=("2010",))
check("inspector (2.5 c): a stuck visit still listed with a data error whose own first charge reads BILLED has gone out - a claim that was sent is never changed: nothing voided, nothing saved, and the entry is the 'free' one with the note 'the visit was billed - nothing done'. "
      "When that charge cannot be read, nothing is done and nothing recorded for the visit in this run - the next run tries again",
      _ie == "" and _v1 == [] and _s1 == [] and [(e_.get("listed"), e_.get("released"), e_.get("note")) for e_ in QR(_ir)] == [(False, True, "the visit was billed - nothing done")]
      and _ie2 == "" and _ir2 is None and RT["voided"] == [] and RT["resaved"] == [], (_ie, _ir, _ir2))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": [SK(201), SK(301)]}, listed={"201": [E_DATA], "301": [E_DATA]}, after={"201": [], "301": []}, proc=dict(PR(201), **PR(301)), void_raises=("2011",))
check("inspector (2.5): an error while ONE stuck visit is tried is caught - what was recorded for it stays (its entry, void_ok false) - and the pass goes on with the next visit, which is freed",
      _ie == "" and RT["voided"] == ["2011", "3011"] and [(e_["visit"], e_["void_ok"], e_["released"]) for e_ in QR(_ir)] == [("201", False, False), ("301", True, True)] and "ERR retry 201" in _io, (_ie, _ir, _io[-400:]))
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"stuck": ["odd", {"visit": 5}, {"visit": "vst201", "charge": "charge2011", "chart": 7}, None], "open_lines": "x"}, mgate="odd", listed={"201": [E_DATA]}, proc=PR(201))
check("inspector (2.5): odd items in the gates' lists are passed over - never an error, nothing done, no register", _ie == "" and _ir is None and RT["voided"] == [] and RT["resaved"] == [], (_ie, _ir))
# open point 11 (decided YES): a visit of an EARLIER batch whose line is not decided (the gates' "open_lines") and that no inspector step ever looked at
_ir, _io, _ie = rt_run(created=_NOQ, qgate={"open_lines": [OL(201)]}, listed={"201": [E_DATA]}, after={"201": []}, proc=PR(201))
check("inspector (open point 11): a visit of an EARLIER batch whose line is not decided and that the Claim Inspector lists with a data error - the line comes off by the same sequence (void, re-save on its own charge, list again) and the visit goes out; the entry says retry_of = the import register of the line",
      _ie == "" and RT["voided"] == ["2011"] and len(RT["resaved"]) == 1 and [(e_["visit"], e_["pid"], e_["charge"], e_["void_ok"], e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [("201", "pat201", "charge2011", True, True, "feed_import_T4.json")], (_ie, _ir))
for _lbl_, _kw_ in (("is NOT listed - it simply waits for its claim run", dict(listed={})), ("is listed with advisories only (nothing is bypassed for it either)", dict(listed={"201": [E_ADV]})),
                    ("was billed (a claim that was sent is never changed)", dict(listed={"201": [E_DATA]}, billed=("2010",))), ("is held, after proof, for words that do not name the line (the normal pass's own test)", dict(listed={"201": [E_DATA]}, qgate={"confirmed": True, "open_lines": [OL(201)]})),
                    ("names no own first charge in its item", dict(listed={"201": [E_DATA]}, qgate={"open_lines": [OL(201, own="")]})), ("is listed, but the listing is answered with a fault", dict(listed={"201": [E_DATA]}, list_fault=(2,)))):
    _ir, _io, _ie = rt_run(created=_NOQ, **dict(dict(qgate={"open_lines": [OL(201)]}, proc=PR(201)), **_kw_))
    check("inspector (open point 11): ... such a visit that %s is left alone - nothing voided, nothing saved, nothing bypassed, no entry, no register" % _lbl_, _ie == "" and _ir is None and RT["voided"] == [] and RT["resaved"] == [] and RT["bypassed"] == [], (_ie, _ir, _io[-300:]))
_ir, _io, _ie = rt_run(created=[ROW_(101)], qgate={"open_lines": [OL(101)]}, listed={"101": [E_DATA]}, after={"101": []}, proc=PR(101))
check("inspector (open point 11): this batch's OWN visits are the normal pass's - an open_lines item for one of them adds nothing: one void, one entry, without retry_of", _ie == "" and RT["voided"] == ["1011"] and [(e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [(True, None)], (_ie, _ir))
# the whole circle: the import's gate lists the stuck visit -> the step's retry pass frees it -> the next import reads the entry
world(); state([R1], files=REM(void_ok=False, released=False)); _g = ci.quality_gate()
_ir, _io, _ie = rt_run(created=_NOQ, qgate=_g, listed={"1": [E_DATA]}, after={"1": []}, proc={"12": (QP, "0.00")}, vc={"1": ["11", "12"]})
_fr = {"removed": dict(REM(void_ok=False, released=False)["removed"], **{"20261112T1240Z": [("feed_inspector_20261112T1240Z.json", e_) for e_ in ((_ir or {}).get("quality_removed") or [])]})}
world(); s = state([R1, (RN("20261112T1240Z"), {"created": []})], files=_fr)
check("import -> inspector -> import (K2c, whole circle): the gate the import writes for a visit whose void failed is what the step's retry pass reads (visit, chart, line, own first charge); the pass voids the line and re-saves the visit on its own charge, and the entry it writes is what the next import reads: "
      "the visit is no longer stuck, the code is not paused, the line is void, that patient is not tried again this year, and the code probes at one cent with ONE line - nobody restarted anything",
      _ie == "" and [i_["visit"] for i_ in _g["stuck"]] == ["vst1"] and RT["voided"] == ["12"] and len(RT["resaved"]) == 1 and 'id="charge11"' in RT["resaved"][0] and "charge12" not in RT["resaved"][0]
      and [(e_["visit"], e_["pid"], e_["charge"], e_["void_ok"], e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [("1", "pat7001", "charge12", True, True, "feed_inspector_20261111T1240Z.json")]
      and s["stuck"] == [] and s["paused"] == "" and s["off"] == "" and s["off_until_reset"] == "" and s["void_lines"] == ["charge12"] and ("pat7001", "2026") in s["refused"] and s["fee"] == "0.01" and s["probe_kind"] == "claim_check" and s["probe_tries"] == 2 and s["budget"] == 1, (_ie, _ir, s))
# November 12, 2026 - fix round 1 (the lead's decision K10): THE ROUTINE'S OWN VOID IS NEVER LOST - the step writes its register BEFORE the first void, so a process cut right after the void leaves the entry on disk saying void_ok false
_ir, _io, _ie = rt_run(created=[ROW_(1)], listed={"1": [E_DATA]}, proc={"11": (QP, "0.00")}, void_cuts={"11"})
check("inspector (K10, fix round 1): the normal pass is cut right after the void of a held visit's line - the step's register is already on disk with that entry saying void_ok false (written before the void), so the next import knows the visit is stuck",
      _ie == "cut" and RT["voided"] == ["11"] and RT["resaved"] == [] and [(e_["visit"], e_["charge"], e_["void_ok"], e_["released"]) for e_ in QR(_ir)] == [("1", "charge11", False, False)], (_ie, _ir))
_ir, _io, _ie = rt_run(qgate={"stuck": [SK(5)]}, listed={"5": [E_DATA]}, proc={"51": (QP, "0.00")}, void_cuts={"51"})
check("inspector (K10, fix round 1): the retry pass is cut right after its void - on disk the retry entry says void_ok false and resave_ok false (written before the void), so the visit stays stuck and the next run re-saves it",
      _ie == "cut" and RT["voided"] == ["51"] and [(e_["visit"], e_["void_ok"], e_.get("resave_ok"), e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [("5", False, False, False, "feed_inspector_T4.json")], (_ie, _ir))
_e10 = {"visit": "1", "pid": "pat7001", "charge": "charge12", "code": "1123F", "fee": "0.00", "why": "Pattern 77002: review", "void_ok": False, "released": False, "at": "x"}      # the entry such a cut leaves on disk
world(c12=VOID); s = state([R1], files={"removed": {"20261111T1240Z": [("feed_inspector_20261111T1240Z.json", _e10)]}}); s0 = state([R1])
check("import (K10, fix round 1): the line reads void while its visit is still there, and the routine's own entry (void_ok false - the cut came after the void) is on record - the routine took it off, not a person: the visit is STUCK "
      "(paused, listed for the retry pass), that patient is not marked as a person's decision, the line is not a taken line; WITHOUT any entry of the routine's the same void line is a person's decision, as before (K2f)",
      [x_["visit"] for x_ in s["stuck"]] == ["vst1"] and s["paused"].startswith("paused this run: visit vst1 (chart pat7001) may still be held with its quality line - the routine's last try was cut off before it ended; this run's step looks again") and s["budget"] == 0 and s["taken_lines"] == [] and ("pat7001", "2026") not in s["refused"]
      and any("the routine took it off, not a person" in n_ for n_ in s["notes"]) and not any("a person decided" in n_ for n_ in s["notes"])
      and s0["taken_lines"] == ["charge12"] and ("pat7001", "2026") in s0["refused"] and any("a person decided" in n_ for n_ in s0["notes"]), (s, s0["taken_lines"]))
# November 12, 2026 - fix round 1 (the lead's decision K11): A VISIT OF A FAULT RUN that the Claim Inspector holds is a stuck visit too - the retry pass looks at it in every run
FK = lambda vid, **kw: dict({"chart": "pat%s" % vid, "visit": "vst%s" % vid, "charge": "", "own": "", "code": "1123F", "fee": "0.00", "with": "", "dos": "11/10/2026", "fault": True, "why": "provisional: the call that carries the quality line was sent",
                             "register": "feed_import_T4.json", "what": "the run was cut while the call that carried the line was out - nobody has seen yet whether the Claim Inspector holds it", "since": "feed_import_T4.json"}, **kw)      # a gate's "stuck" item for a visit of a fault run, as the import writes it
HIST6 = [{"pid": "pat6", "id": "charge60", "proccode": "99309", "dos": "11/10/2026", "fee": "141.00", "void": "0"}, {"pid": "pat6", "id": "charge61", "proccode": "1123F", "dos": "11/10/2026", "fee": "0.00", "void": "0"}]
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={"6": [E_DATA]}, after={"6": []}, proc={"61": (QP, "0.00")}, hist=HIST6)
check("inspector (K11, fix round 1): a visit of a fault run (its line's charge number not known) that the Claim Inspector holds with a data error - the step finds its live 1123F line on THAT visit (chart history, then the line's own detail: procedure, at most one cent, this visit), "
      "voids it, re-saves the visit on its own charge, and the visit goes out; the entry says fault true, the charge it found and retry_of; no other charge is touched",
      _ie == "" and RT["voided"] == ["61"] and len(RT["resaved"]) == 1 and 'id="charge60"' in RT["resaved"][0] and "charge61" not in RT["resaved"][0]
      and [(e_["visit"], e_["charge"], e_.get("fault"), e_["void_ok"], e_["released"], e_.get("retry_of")) for e_ in QR(_ir)] == [("6", "charge61", True, True, True, "feed_import_T4.json")], (_ie, _ir, RT["voided"]))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={}, proc={"61": (QP, "0.00")}, hist=HIST6)
check("inspector (K11): ... not listed by the Claim Inspector = free: one entry (listed false, fault true), nothing voided or saved",
      _ie == "" and RT["voided"] == [] and RT["resaved"] == [] and [(e_["visit"], e_.get("listed"), e_.get("fault"), e_["void_ok"]) for e_ in QR(_ir)] == [("6", False, True, False)], (_ie, _ir))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={"6": [E_DATA]}, proc={"61": (QP, "0.00")}, hist=HIST6[:1])
check("inspector (K11; K15, fix round 2): ... held with a data error and no live 1123F line of that visit in the chart's history: nothing is voided - the entry says so (void_ok false, own_reason true: held for its own reason) and the visit stays for a person - it does not pause the code",
      _ie == "" and RT["voided"] == [] and RT["resaved"] == [] and [(e_["visit"], e_.get("fault"), e_["void_ok"], e_.get("own_reason")) for e_ in QR(_ir)] == [("6", True, False, True)]
      and QR(_ir)[0].get("note") == "held for its own reason; no 1123F line is on it - a person fixes the visit", (_ie, _ir))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={"6": [E_DATA]}, proc={"71": (QP, "0.00")}, hist=HIST6[:1] + [{"pid": "pat6", "id": "charge71", "proccode": "1123F", "dos": "11/10/2026", "fee": "0.00", "void": "0"}])
check("inspector (K11): ... never a line of ANOTHER visit: a live 1123F line of the same chart and date whose own detail names another visit is left alone - for a person",
      _ie == "" and RT["voided"] == [] and [(e_.get("fault"), e_["void_ok"]) for e_ in QR(_ir)] == [(True, False)], (_ie, _ir, RT["voided"]))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)], "confirmed": True}, listed={"6": [E_DATA]}, proc={"61": (QP, "0.00")}, hist=HIST6)
check("inspector (K11): ... after the proof, a hold whose words name no no-charge line: the line is left alone (the normal pass's own test) - the entry says so and the visit stays for a person",
      _ie == "" and RT["voided"] == [] and [(e_.get("fault"), e_["void_ok"]) for e_ in QR(_ir)] == [(True, False)] and "after the proof" in QR(_ir)[0].get("note", ""), (_ie, _ir))
# November 12, 2026 - fix round 2 (the lead's decisions K15-K17; William 11/11/2026: "dont stop this dont let it stop make sure this suceeds")
check("inspector (K15, fix round 2): ... that after-proof entry says own_reason true - the visit is held for its own reason, not because of this code (the import does not pause for it)",
      QR(_ir)[0].get("own_reason") is True and QR(_ir)[0].get("note", "").startswith("held for its own reason"), QR(_ir))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={"6": [E_DATA]}, proc={"61": (QP, "0.00")}, hist=HIST6, unread={"61"})
check("inspector (K16, fix round 2): a fault visit held with a data error whose 1123F line cannot be read - nothing is voided, and an entry SAYS so (looked false, void_ok false, the reason) so the state line can say its line could not be looked for",
      _ie == "" and RT["voided"] == [] and [(e_["visit"], e_.get("fault"), e_["void_ok"], e_.get("looked")) for e_ in QR(_ir)] == [("6", True, False, False)]
      and QR(_ir)[0].get("note", "").startswith("its line could not be looked for: charge 61 could not be read"), (_ie, _ir))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={"6": [E_ADV]}, proc={"61": (QP, "0.00")}, hist=HIST6)
check("inspector (K11; K17, fix round 2): a fault visit listed with advisories only - they are bypassed as always, nothing voided, and ONE entry says it is free (listed false, fault true)",
      _ie == "" and RT["voided"] == [] and [(e_["visit"], e_.get("listed"), e_.get("fault"), e_.get("note")) for e_ in QR(_ir)] == [("6", False, True, "only advisories remained - bypassed, nothing voided")], (_ie, _ir))
_ir, _io, _ie = rt_run(qgate={"stuck": [FK(6)]}, listed={"6": [E_DATA]}, after={"6": []}, proc={"61": (QP, "0.00"), "62": (MP, "0.00")}, hist=HIST6)
check("inspector (K11; K17, fix round 2): a fault visit that also carries an M0004 line - the M0004 line comes off with its 1123F line (M0004 never rides without it); two entries, both fault true",
      _ie == "" and sorted(RT["voided"]) == ["61", "62"] and sorted((e_["code"], e_["charge"], e_.get("fault"), e_["void_ok"]) for e_ in QR(_ir)) == [("1123F", "charge61", True, True), ("M0004", "charge62", True, True)], (_ie, _ir, RT["voided"]))
_ir, _io, _ie = rt_run(qgate={"stuck": [SK(5)]}, listed={"5": [E_DATA]}, after={"5": []}, proc={"51": (QP, "0.00")}, void={"51"})
check("inspector (K16, fix round 2): the retry of a stuck visit whose line reads void already (a cut came after the void) - nothing is voided again, the visit is re-saved and goes out; the entry says was_void true (the digest says the line was found off)",
      _ie == "" and RT["voided"] == [] and len(RT["resaved"]) == 1 and [(e_["visit"], e_["void_ok"], e_.get("was_void"), e_["released"]) for e_ in QR(_ir)] == [("5", True, True, True)], (_ie, _ir))
world()
s = state([_F70], files=FREE70(released=False, listed=None, own_reason=True, note="held for its own reason; no 1123F line is on it - a person fixes the visit"))
check("refusals (K15, fix round 2): the step found the fault visit held for its own reason (no 1123F line on it) - it does NOT pause the code: it stays listed under 'stuck' (own true, so every run's step looks again) and its patient stays marked; the code probes on",
      s["paused"] == "" and s["off"] == "" and s["budget"] == 1 and [(x_["visit"], x_.get("fault"), x_.get("own"), x_["what"]) for x_ in s["stuck"]] == [("vst70", True, True, "held for its own reason; no 1123F line is on it - a person fixes the visit")]
      and ("pat7009", "2026") in s["done"] and s["probe_kind"] == "fault", s)
s = state([_F70], files=FREE70(released=False, listed=None, own_reason=True, note="held for its own reason - after the proof its words name no no-charge line, so the line stays; a person fixes the visit"))
check("refusals (K15): ... the same after the proof when the hold's words name no line - no pause, listed for a person", s["paused"] == "" and s["budget"] == 1 and [x_.get("own") for x_ in s["stuck"]] == [True], s)
s = state([_F70], files=FREE70(released=False, listed=None, looked=False, note="its line could not be looked for: the chart's history could not be read (RuntimeError)"))
check("refusals (K16, fix round 2): ... the step could not look for its line - the visit is held and may carry it: paused, and the state says its line could not be looked for",
      s["budget"] == 0 and [(x_["visit"], x_.get("own")) for x_ in s["stuck"]] == [("vst70", False)] and s["stuck"][0]["what"] == "the Claim Inspector holds it and its line could not be looked for: the chart's history could not be read (RuntimeError)"
      and s["paused"].startswith("paused this run: visit vst70 (chart pat7009) came from a fault run - the Claim Inspector holds it and its line could not be looked for"), s)
s = state([_F70], files=FREE70(charge="charge701", released=False, listed=None, note=""))
check("refusals (K16, fix round 2): ... an entry with void_ok false and NO note (written before a void that never reported back) - the state says the routine's last try was cut off and this run's step looks again; paused",
      s["budget"] == 0 and s["stuck"][0]["what"] == "the routine's last try was cut off before it ended; this run's step looks again" and s["stuck"][0]["charge"] == "charge701", s)
s = state([_F70], files=FREE70(charge="charge701", void_ok=True, released=False, listed=None, still_named=True, resave_ok=True, note=""))
check("refusals (K11; K17, fix round 2): ... the line came off but the visit is still listed for the edit about it - it stays STUCK (paused): never read as free while the claim check holds it for the line",
      s["budget"] == 0 and [(x_["visit"], x_["what"]) for x_ in s["stuck"]] == [("vst70", "the line is off, but the visit is still listed for the edit about it")] and s["paused"].startswith("paused this run: visit vst70"), s)
_eC = {"visit": "vst1", "pid": "pat7001", "charge": "charge12", "fee": "0.00", "why": "Pattern 77002: Claim line requires review", "void_ok": False, "released": False, "at": "x"}
_eF = dict(_eC, listed=False, released=True, retry_of="feed_inspector_20261111T1240Z.json", note="the visit is no longer listed by the Claim Inspector - nothing done")
world(); s = state([R1], files={"removed": {"20261111T1240Z": [("feed_inspector_20261111T1240Z.json", _eC)]}})
s2 = state([R1], files={"removed": {"20261111T1240Z": [("feed_inspector_20261111T1240Z.json", _eC), ("feed_inspector_20261112T1240Z.json", _eF)]}})
check("ledger (K16, fix round 2): an entry the step wrote before a void that never reported back (void_ok false, no note) - the visit MAY still be held with its line: paused, and the words say the routine's last try was cut off (never 'could not take the line off')",
      s["budget"] == 0 and [(x_["visit"], x_["what"]) for x_ in s["stuck"]] == [("vst1", "the routine's last try was cut off before it ended; this run's step looks again")]
      and s["paused"].startswith("paused this run: visit vst1 (chart pat7001) may still be held with its quality line - the routine's last try was cut off") and "cut off before it ended" in s["probe"] and "could not take" not in s["probe"], s)
check("ledger (K16, fix round 2): ... once a newer entry says the visit is free, the cause that cut entry began is not left behind: no pause, and the probe no longer says the try was cut off",
      s2["stuck"] == [] and s2["paused"] == "" and "cut off" not in s2["probe"] and s2["probe"].startswith("visit vst1 was held with its quality line until the routine could free it"), s2)
_NXu = (_NX[0], json.loads(json.dumps(_NX[1]))); _NXu[1]["quality_gate"]["left_off_on"] = {"charge12": {"on": "x", "billed": "y"}}
_rd0 = RUN_DAY[0]; world(c11=["11/11/2026"], c22=BILLED); RUN_DAY[0] = _dt.date(2026, 12, 30); s = state([R1, _NXu]); RUN_DAY[0] = _rd0
check("ledger (K12; K17, fix round 2): a left-off line whose dates cannot be read - not shown that 30 days have passed, so its patient gets no second line (once per patient and year)", ("pat7001", "2026") in s["done"], s["done"])
_R1f = (RN("20261111T1240Z"), {"created": [dict(A_, feed_id="f7001"), B_, C_], "failed": [], "skipped": []})
world(c11=["11/11/2026"], c22=BILLED); RUN_DAY[0] = _dt.date(2026, 11, 20); s = state([_R1f]); RUN_DAY[0] = _rd0
check("ledger (K12; K17, fix round 2): ... the block holds by the feed's own patient id too - the same feed patient on a second chart gets no line while the left-off line may still be billed",
      s["left_off_lines"] == ["charge12"] and ("feed:f7001", "2026") in s["done"], s["done"])
BILLS.clear(); PROC.clear(); DETAILS.clear(); qreset()      # the stand-in chart as the checks below expect it
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
check("insurance check (11.6, NH2-1): ... words that name only 1123F - sent once more without BOTH lines (M0004 never rides without the 1123F line); the M0004 entry says it came off with 1123F",
      okm3 is True and "charge12" not in VQ["sent"][1] and "charge11" not in VQ["sent"][1] and VQ["void"] == {"11", "12"} and [(e_["code"], e_.get("with")) for e_ in _rm] == [("1123F", None), ("M0004", "1123F")], (okm3, mm3, _rm))
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
check("rulebook (section 8; 5.1 R6, R7): the owner's words for M0004 (in the procedure list as pcode692183 'QUAL CARE NEUROLOGIC CND MVP', \"use it\") and the whole rule in plain words - when it rides, its ledger, refusals, held visits, Medicare's answer, December, the switches; since 11/12/2026 M0004 never switches itself off either: it probes",
      all(x_ in _qrb for x_ in ('William 11/10/2026, about M0004 - it is in AdvancedMD\'s procedure list as procedure id pcode692183, "QUAL CARE NEUROLOGIC CND MVP": "use it".', "THE BACK END ADDS M0004: ONE no-charge M0004 line per clinician per calendar year",
          "only once the 1123F pilot is proven", "never on a hospital visit", "- after a second left-off line M0004 probes;", "taken that way, M0004 probes;", "does not count against 1123F unless the 1123F line was taken off with it",
          "that M0004 line is just void - nothing follows for M0004, and its clinician may get M0004 again", "(another code text pauses M0004 while AdvancedMD shows it)",
          "an M0004 line taken off a visit that then went through makes M0004 probe and does not count against 1123F unless the 1123F line was taken off with it; a visit stored without its M0004 line or an insurance check unable to set such a visit's order makes it probe too; a void that fails leaves that visit stuck with its M0004 line - no new M0004 line while that is so, and every run tries the void and the re-save again.",
          "M0004 NEVER SWITCHES ITSELF OFF EITHER (William 11/11/2026, as above; in force since November 12, 2026): where it used to go off it probes - ONE M0004 line a run in all, none while an M0004 line is not decided, until an M0004 line is billed; then each clinician who has none gets one as before.",
          "MVP_CODE=reset has nothing left to restart and the log says so", "QUALITY_CODE=off or stop stops M0004 too, since it never rides without the 1123F line",
          "Medicare's own answer is read per clinician", "the year ends December 31", "MVP_CODE=reset", "MVP_CODE=off")), [x_ for x_ in ("THE BACK END ADDS M0004", "MVP_CODE=reset", "M0004 NEVER SWITCHES ITSELF OFF EITHER", "taken that way, M0004 probes;") if x_ not in _qrb])
check("runbook (section 8): the M0004 paragraph with the owner's words, the switches (off in front of both commands, reset on the ingest only), the December line, and the QUALITY M0004 grep - in the section and in step (f)",
      all(x_ in _qrun.replace("\n", " ") for x_ in ('THE OPTION CODE M0004 - William 11/10/2026: M0004 is in AdvancedMD\'s procedure list (procedure id pcode692183, "QUAL CARE NEUROLOGIC CND MVP") and "use it".', "ONE no-charge M0004 line per clinician per year",
          "`MVP_CODE=off` in front of both commands", "`MVP_CODE=reset` (on the ingest command only)", "the year ends December 31", "grep -h '^QUALITY M0004' logs/claimocity_<stamp>_*.log")) and "grep -h '^QUALITY M0004'" in step[:step.index("## Place of service")]
      and "this version adds 1123F only" not in step)
check("captured calls (section 7, 13.4): M0004 = pcode692183 is the id the feed import uses for its M0004 line, and what is read for that line", "the feed import uses this id for its no-charge M0004 line" in _cc and '`<proccode id="pcode692183" code="M0004"/>`' in _cc and ci.MVP_PCODE == "pcode692183")
check("mirror.py (8.6, 11.6; round 7; 11/12/2026): the inspector's marker is a sentence only the version with the retry pass has (it still takes BOTH no-charge lines off); since round 7 (11/10/2026) the insurance check's is a sentence only the list-aware version has - and that version still sends the echo once more without BOTH lines",
      '"claimocity_inspector.py": "every run tries the void and the re-save again for a visit stuck with its no-charge line"' in mir and "the step takes BOTH no-charge lines off" in insp and '"claimocity_verify.py": "the save is skipped only when the visit\'s insurance-order LIST"' in mir
      and "the save is skipped only when the visit's insurance-order LIST" in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py")).read() and "sent once more without BOTH lines" in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_verify.py")).read())

# ---- 6b2. the confirm reviews (11/10/2026 evening): the words of their fixes, and the privacy gate's tree mode ------------------------------------------
_para = step[step.index("CLAIMOCITY FEED INGEST"):step.index("Duplicates: should Gregg's pickup")]      # the paragraph the daily routine is bound to, steps (a) to (f)
check("runbook (W-2): a switch given to a run that imports nothing is lost - the runbook says so, how to see it took (the run's QUALITY line) and to give it again until it does",
      all(x_ in _qrun.replace("\n", " ") for x_ in ("A switch reaches the import only on a run that IMPORTS", "a stop or reset given to such a run is lost", "for stop it must say \"stopped on William's word\"", "give the same switch again on the next run")))
check("runbook (W-6): the commit of the import register while a pilot round is open is INSIDE steps (a) to (f), right after the ingest", "Right after it, when its `QUALITY 1123F` log line says \"pilot:\", commit registers/feed_import_<stamp>.json to main at once" in _para)
check("runbook and rulebook (W-7): William's exception list lives on main, every run copies it over the workspace copy before the ingest (step c), and step (e) carries it",
      "cp -p /home/claude/effinger-billing-backend/practices/ehpa/registers/quality_exceptions.json /home/claude/unbilled/registers/" in _para and "William's quality_exceptions.json -> practices/ehpa/registers/ on main" in _para
      and "WILLIAM'S EXCEPTION LIST (the patients who never get the automatic line - rules.md) lives ON MAIN" in _qrun and "whose home is main (practices/ehpa/registers/quality_exceptions.json" in _qrb)
check("runbook (W-1): the left-off paragraph promises no line while William has stopped the code, and only a visit of the same year", "a later eligible visit of the same year carries the code while the code is on" in _qrun.replace("\n", " ") and "its patient gets the code with a later visit" not in _qrun
      and "(while William has stopped it, no line is added before his restart)" in _qrun.replace("\n", " "))
check("rulebook (W-5): 'NEVER a reason to hold, edit, resend or bypass' is said of a person or a routine acting by hand - the inspector step and the insurance check do their own part (HELD VISITS)",
      "NEVER a reason for a person or a routine to hold, edit, resend or bypass a visit by hand - what the inspector step and the insurance check do with the line on a held visit (HELD VISITS below) is their own, and nothing more." in _qrb and "NEVER a reason to hold, edit, resend or bypass a visit." not in _qrb)
check("lessons (W-4, M3's fifth place): no lesson line says N620 is 'Medicare's acceptance'; the older line says what N620 shows", not any("is Medicare's acceptance" in l_ for l_ in _sl) and any("shows Medicare received a code valid for the year (not that the measure is met" in l_ for l_ in _sl))
check("rulebook and runbook (NH2-1, NH2-2): words that name 1123F alone take BOTH no-charge lines off; a visit still listed for the edit about the line after the void is stuck - no new line in that run, and every run tries again (11/12/2026; before, the code switched off)",
      "and also when it names 1123F alone (M0004 never rides without the 1123F line" in _qrb and "also when the edit names 1123F alone, because M0004 never rides without the 1123F line" in _qrun.replace("\n", " ")
      and "unless it is still listed for the edit about the line" in _qrb and "unless it is still listed for the edit about the line" in _qrun.replace("\n", " "))
_gate = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
if os.path.exists(_gate):      # (a throwaway tree that holds only the files the tests read may lack the gate)
    sys.path.insert(0, os.path.dirname(_gate)); import phi_gate as _pgm; sys.path.pop(0)
    _own = {n_: open(os.path.join(ROOT, "tools", "selftest", n_), encoding="utf-8").read() for n_ in ("test_pos_rule.py", "test_quality_nights.py")}
    check("privacy gate (W-8): its TREE mode (what mirror.py runs before every commit) leaves this self-test and the night simulation unchanged - without a name map, only its own rules", all(_pgm.redact(t_, {}, code=True) == t_ for t_ in _own.values()),
          [n_ for n_, t_ in _own.items() if _pgm.redact(t_, {}, code=True) != t_])
else: print("skip privacy gate (W-8): tools/mirror/phi_gate.py is not in this tree")

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
    if "R.json" in _f or not _f.startswith(tuple("feed_import_" + x for x in ("2026" "1101", "2026" "1103")) + ("claimocity_patient_map",)): os.remove(os.path.join(_w2, "registers", _f))
_o, _calls, _e = driver_run("claimocity_retry_dx.py", _w2, _r2, ("--live", "--no-stedi", "--stamp", "2026-11-10T1400Z"), lambda cmd: None)
check("W1: without a clone the retry still enters the visits (never a hold) and its RESULT line ends with the place-of-service warning, naming who checks what",
      _e == "" and "claimocity_import.py" in [c_[1] for c_ in _calls] and next((l_ for l_ in _o.splitlines() if l_.startswith("RESULT retry")), "").endswith("for William to check: the place of service of every nursing-building line this run entered, and the clinician and building of every visit whose patient has another message in the batch (a routine changes nothing on these visits)"), _o[-400:])
# William 11/25/2026 (the retry of 'no usable dx' skips): the retry driver itself, INSIDE this process over a sandbox workspace and clone as above. Here its import step runs
# the REAL import helper (a fresh copy over the retry's own batch files, with this self-test's stand-in AdvancedMD) and its report step the REAL report helper, so the whole
# road is walked offline: the skip of an earlier batch -> the retry's own readiness rule -> build() puts I10 in the code's place -> the register row -> the digest's line and
# the text of William's email. (The two W1 checks above start the driver over helper texts that carry no code table, which is why they stop at 'nothing to retry'.)
_DXN = [0]
def dx_retry(cache, argv=("--live", "--no-stedi", "--stamp", "2026-11-26T1400Z")):
    """One earlier batch (20261031T1240Z) whose three visits were skipped as 'no usable dx for 99309': Y1 - its only code is not in AdvancedMD's list; Y2 - its charge line carries
    no code at all; Y3 - two lines: the visit's only code is unknown, its 99497 carries a known code beside an unknown one. cache = the diagnosis cache the retry finds.
    -> (what the driver printed, the programs it started, its error, the sandbox workspace)."""
    w_, r_ = hc_dirs({})
    for d_ in (w_, r_): open(os.path.join(d_, "claimocity_import.py"), "w").write(_HSRC)      # the REAL import helper in the workspace and in the clone: the driver reads the code table from its text
    st_ = "20261031T1240Z"; rs_ = "20261126T1400ZR"; os.makedirs(os.path.join(w_, "registers")); os.makedirs(os.path.join(w_, "hl7", st_))
    vis_ = (("Y1", "pat9201", [("99309", "20261030", "S82.843D")]), ("Y2", "pat9202", [("99309", "20261030", "")]), ("Y3", "pat9203", [("99309", "20261030", "M51.17"), ("99497", "20261030", "E11.9^T84.011A")]))
    json.dump({"created": [], "failed": [], "skipped": [{"feed_id": f_, "pid": p_, "why": "no usable dx for 99309"} for f_, p_, _l in vis_]}, open(os.path.join(w_, "registers", "feed_import_%s.json" % st_), "w"))
    json.dump([{"pid": f_, "name": NAME(f_), "dob": DOBK, "file": "a", "FT1": [{"cpt": c_, "dos": d_, "dx": x_, "units": "1"} for c_, d_, x_ in l_]} for f_, _p, l_ in vis_], open(os.path.join(w_, "feed_parsed_%s.json" % st_), "w"))
    open(os.path.join(w_, "hl7", st_, "a.hl7"), "w").write("".join(hl7(f_, B["n1"], "", [(c_, d_) for c_, d_, _x in l_], NPI) for f_, _p, l_ in vis_))
    json.dump(cache, open(os.path.join(w_, "dx_cache_feed.json"), "w")); json.dump({f_: p_ for f_, p_, _l in vis_}, open(os.path.join(w_, "registers", "claimocity_patient_map.json"), "w"))
    def step_(cmd):
        b_ = os.path.basename(str(cmd[1]))
        if b_ == "claimocity_import.py":      # the real import helper, loaded fresh over the retry's own batch files (the driver has written them), against the stand-in AdvancedMD
            e0_ = {k_: os.environ.get(k_) for k_ in ("FEED_STAMP", "FEED_HL7_DIR", "FEED_DX_CACHE")}; os.environ.update(FEED_STAMP=rs_, FEED_HL7_DIR=os.path.join(w_, "hl7", rs_), FEED_DX_CACHE="dx_cache_feed.json"); _DXN[0] += 1
            try: sp_ = importlib.util.spec_from_file_location("claimocity_import_retry_%d" % _DXN[0], HELPER); m_ = importlib.util.module_from_spec(sp_); sp_.loader.exec_module(m_)
            finally:
                for k_, v_ in e0_.items(): os.environ.pop(k_, None) if v_ is None else os.environ.__setitem__(k_, v_)
            if not (m_.amd is amd and m_.resave is resave and m_.txh is txh): raise RuntimeError("the fresh copy did not load the stand-in modules")
            a_ = sys.argv[:]; sys.argv = ["claimocity_import.py"] + [str(x_) for x_ in cmd[2:]]; b2_ = io.StringIO(); sl_ = m_.time.sleep; m_.time.sleep = lambda s: None
            try:
                with contextlib.redirect_stdout(b2_): m_.main()
            finally: sys.argv = a_; m_.time.sleep = sl_
            return b2_.getvalue().strip()
        if b_ == "claimocity_report.py":      # the real report helper, started as a program: it loads nothing that talks to AdvancedMD (section 6 starts it the same way)
            return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "helpers", "claimocity_report.py")], cwd=w_, env=dict(os.environ, FEED_STAMP=rs_), capture_output=True, text=True).stdout.strip()
    POSTS.clear(); ci._ctx.clear()
    o_, calls_, e_ = driver_run("claimocity_retry_dx.py", w_, r_, argv, step_)
    return o_, calls_, e_, w_
_rd = lambda w_, *p_: json.load(open(os.path.join(w_, *p_))) if os.path.exists(os.path.join(w_, *p_)) else None
_txt = lambda w_, *p_: open(os.path.join(w_, *p_)).read() if os.path.exists(os.path.join(w_, *p_)) else ""
_DXC = {"I10": "dcode1", "E11.9": "dcode2", "S82.843D": None}
_o, _calls, _e, _w = dx_retry(_DXC); _RS = "20261126T1400ZR"; _rr = _rd(_w, "registers", "feed_import_%s.json" % _RS) or {"created": [], "skipped": [], "failed": []}
_sent = [re.findall(r'diagcodes="([^"]*)"', b_) for b_ in POSTS if 'action="updvisitwithnewcharges"' in b_]      # per charge call: the diagnosis ids of each of its charges
check("retry (William 11/25/2026, the driver itself with the real import and report helpers, offline): a visit that waited as 'no usable dx' because its only diagnosis code is not in AdvancedMD's list is handed to the import once I10 is in the list - the visit whose charge line carries no code at all still waits",
      _e == "" and [c_[1] for c_ in _calls] == ["claimocity_dx.py", "claimocity_import.py", "claimocity_verify.py", "claimocity_inspector.py", "claimocity_report.py", "claimocity_recon.py"]
      and [m_["pid"] for m_ in (_rd(_w, "feed_parsed_%s.json" % _RS) or [])] == ["Y1", "Y3"], (_e, _calls, _o[-600:]))
check("retry: ... the import enters both visits with I10 where the unknown codes stood - Y1's charge carries I10's id alone, Y3's visit line too and its 99497 the known code first, then I10 - and each register row names its codes and says dx_instead I10",
      _sent == [["dcode1"], ["dcode1", "dcode2 dcode1"]] and [(r_["pid"], r_["cpts"], r_.get("missing_dx"), r_.get("dx_instead")) for r_ in _rr["created"]] == [("pat9201", ["99309"], ["S82.843D"], "I10"), ("pat9203", ["99309", "99497"], ["M51.17", "T84.011A"], "I10")]
      and _rr["skipped"] == [] and _rr["failed"] == [], (_sent, _rr["created"], _rr["skipped"]))
check("retry: ... the driver's own line names the codes for the email - 'retry-dx: 2 visit(s) entered with I10 in place of codes not in AMD's diagnosis list: M51.17, S82.843D, T84.011A' - says which visit still waits and why, and its RESULT line counts two visits created",
      "\nretry-dx: 2 visit(s) entered with I10 in place of codes not in AMD's diagnosis list: M51.17, S82.843D, T84.011A" in _o and "1 still wait: a charge line that carries no diagnosis code at all" in _o
      and "RESULT retry %s: visits created 2, skipped 0, failed 0" % _RS in _o and "| 1 visit(s) still wait: a charge line that carries no diagnosis code at all - for William" in _o, _o[-900:])
_dig = _txt(_w, "feed_digest_%s.md" % _RS); _mail = _txt(_w, "outbox", "dx_codes_needed_%s.txt" % _RS)
check("retry: ... and the retry's own digest carries the line for William's email, with the file the report wrote beside it - each code with its chart number and date of service",
      "- Diagnosis codes not in AdvancedMD's list (William 11/25/2026: the visit goes in with I10 in its place; he adds the codes): 2 visit(s) - M51.17 x1, S82.843D x1, T84.011A x1 - EMAIL WILLIAM: outbox/dx_codes_needed_%s.txt" % _RS in _dig
      and "\nS82.843D - 1 visit(s): pat9201 10/30/2026\n" in _mail and "\nM51.17 - 1 visit(s): pat9203 10/30/2026\n" in _mail and "\nT84.011A - 1 visit(s): pat9203 10/30/2026\n" in _mail and "digest: feed_digest_%s.md" % _RS in _o, (_dig[:900], _mail))
_o, _calls, _e, _w = dx_retry(_DXC, argv=("--no-stedi", "--stamp", "2026-11-26T1400Z"))
check("retry: a DRY retry says what WOULD be entered with I10 and writes nothing - no visit is sent to AdvancedMD and no register is written",
      _e == "" and "\nretry-dx: 2 visit(s) would be entered with I10 in place of codes not in AMD's diagnosis list: M51.17, S82.843D, T84.011A" in _o and "(DRY - nothing written)" in _o
      and not any("addvisit" in b_ or "updvisitwithnewcharges" in b_ for b_ in POSTS) and _rd(_w, "registers", "feed_import_%s.json" % _RS) is None and [c_[1] for c_ in _calls] == ["claimocity_dx.py", "claimocity_import.py"], (_e, _calls, _o[-600:]))
for _how, _c in (("I10 itself is not in the list", {"E11.9": "dcode2", "S82.843D": None}), ("the cache holds I10 as 'not in the list' (null)", {"I10": None, "E11.9": "dcode2", "S82.843D": None})):
    _o, _calls, _e, _w = dx_retry(_c)
    check("retry: when %s everything is as before - no visit is handed to the import, and the driver's old sentence names the codes the visits wait on (William adds them)" % _how,
          _e == "" and [c_[1] for c_ in _calls] == ["claimocity_dx.py"] and "retry-dx: 3 visit(s) still wait on codes not in AMD's diagnosis list: M51.17, S82.843D (valid ICD-10 - William adds them in AMD Master Files > Diagnosis Codes; the next run enters the visits)" in _o
          and not any("addvisit" in b_ for b_ in POSTS) and _rd(_w, "feed_parsed_%s.json" % _RS) is None, (_e, _calls, _o[-500:]))
_RSRC = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_retry_dx.py")).read()
check("retry: its PLAIN ENGLISH header states William's rule of 11/25/2026 and its stand-in code is the import's (one word, two places - they cannot drift apart unseen)",
      "for any diagnosis not in the master file yet change it to i10" in _RSRC.split("\nimport os, sys")[0] and re.search(r'^DX_INSTEAD = "%s"' % ci.DX_INSTEAD, _RSRC, re.M) is not None if hasattr(ci, "DX_INSTEAD") else False)
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
_DROWS = [{"pid": p_, "visitid": v_, "patient": ("ZZ" "TEST ") + v_, "carrier": "MEDICARE", "dos": d_, "cpt": c_, "billed": a_, "carc": k_, "group": "CO", "reason": "", "check": "c1", "amt": a_, "rarc": r_}
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
check("W5 / W6: the comma of part 6, the lessons line's exception (part 4), what msg_own false means, what N counts, the second one-liner, every '32' of the read-back, and what LISTS a CCM line for William as part 1 words it (11/25/2026: listed, no longer kept at 31)",
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
