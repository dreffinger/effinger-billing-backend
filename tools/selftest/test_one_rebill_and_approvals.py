#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 10/6/2026) - proves offline, with fakes and NO AdvancedMD traffic, the guarantees William asked to make
#   permanent: ONE rebill per visit (amd.rebill_charge per-visit per-run guard, move_to_ins rebill=False, freq1_visit.reroute), the visit order set
#   without a rebill (resave.set_insorder), the patient order verified and carried by an active plan (ins_update.update), and the
#   approval email/push carrying links to the approval buttons (approval_submit). Run: python3 tools/selftest/test_one_rebill_and_approvals.py
# Never touches: AMD, Gmail, Drive, the page. Writes only to a temp directory.
# 11/11/2026 - RUN THIS TEST BEFORE A DELIVERY. It runs the REAL code of the billing modules (amd, resave, freq1_visit, move_to_ins,
#   ins_update, approval_submit) with its own stand-ins where that code would call AdvancedMD. Until 11/13/2026 it imported the modules
#   themselves, so the delivery sessions' guarded test runner refused it and it was NOT run with the other self-tests (11/13/2026 below).
#   On November 11, 2026 it stood RED on the live branch: the change to resave.py of rule
#   version 2026-11-10.7 (never-billed feed visits) had been delivered without running it - set_insorder had started to READ each charge's
#   detail, and this file's stand-in still took every call for a save and crashed. Run it before delivering ANY change to amd.py,
#   resave.py, freq1_visit.py, move_to_ins.py, ins_update.py, approval_submit.py or deceased_guard.py - offline as the header above says, or in a sandbox
#   with no network (deceased_guard stands in here: what is proved is amd.rebill_charge's answer to it).
#   Since that day it also proves, on the real modules, what that rule version added (sections B2 and C2): set_insorder reads the visit's
#   insurance-order LIST, refuses a visit already billed unless the caller passes allow_billed=True (freq1_visit.reroute does), echoes
#   every live charge and looks for each again, and puts back an admission date the save wiped - or says "admission date lost on save".
#   11/11/2026 (round 8, the echo guard) - section H runs the REAL resave.visit_charges (sections B-D replace it) on an invented chart history
#   and proves: a history page that fails, a history longer than the pages read and a live charge missing from its own detail are NOTED beside
#   an answer that is otherwise exactly what it was; set_insorder and freq1_visit.reroute then send NOTHING ("visit ...: nothing sent", "NOT
#   rebilled") - also when no live charge was read or the asked charge is not among them, also for a dry run - and a read-back that could not
#   read all the charges is not trusted. move_to_ins.move and freq1_visit.run do NOT look at that note yet (a known, older gap): section H
#   pins the very calls they make on a failed read, so that this round is seen to change nothing in them.
# 11/13/2026 - THE OWNER'S RULE FOR TESTS: never start a helper from scripts/helpers or core as a program in a test and never import the real
#   amd, resave, txh or void_tx modules there (they talk to the practice's live billing system); tests load helpers with stand-in modules and
#   the network shut. So this file no longer puts scripts/helpers or core on the path and imports none of the billing modules: every function
#   it proves is LIFTED out of its module's text (lift and sandbox below, which list the names - of amd.py only the one-rebill guard and the
#   message builder, never its login, post or REST calls) into a sandbox module that stands where the module would, whose amd / resave /
#   requests / deceased_guard are this file's own sandboxes and stand-ins. An import of a billing module, of `requests` or of any module of
#   the checkout is refused (a lifted function that reached for the real thing fails here, it never reaches it), and every network route is
#   closed. The checks are the same, word for word, and so is their number.
import os, sys, json, re, tempfile, time, types, ast, datetime, importlib.abc, importlib.machinery
import html as _html
import xml.etree.ElementTree as ET
import socket as _socket      # 11/11/2026: no network route is open in this process - a call no stand-in answers fails here, it never reaches a host
def _no_network(*a, **k): raise RuntimeError("this self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPERS = os.path.join(ROOT, "scripts", "helpers")
TMP = tempfile.mkdtemp(prefix="selftest_ws_")
os.environ["BILLING_WORKSPACE"] = TMP
LIVE = {"amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update", "approval_submit", "requests", "stedi", "elig_amd", "add_ins", "era_post", "medicare_store"}
class _Refuse(importlib.abc.MetaPathFinder):      # 11/13/2026: what is not a stand-in or a sandbox of this file is never imported
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in LIVE: raise ImportError("refused: %s is a live-system module - only this file's stand-ins and sandboxes are used here" % name)
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is not None and spec.origin and os.path.abspath(spec.origin).startswith(ROOT + os.sep):
            raise ImportError("refused: %s would be loaded from the checkout (%s)" % (name, spec.origin))
        return None
sys.meta_path.insert(0, _Refuse())
def lift(path, names):
    """The top-level functions and assignments of `path` named in `names` - nothing else of the file: no import, no other function, no
    `if __name__` block - compiled under the file's own name (a traceback points at its lines). A name the file no longer has stops the
    test here, by its name."""
    tree = ast.parse(open(path).read(), path)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names) or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    got = {n.name for n in keep if isinstance(n, ast.FunctionDef)} | {t.id for n in keep if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    if set(names) - got: raise RuntimeError("%s has no %s - the code under test is not lifted" % (os.path.basename(path), sorted(set(names) - got)))
    return compile(ast.Module(body=keep, type_ignores=[]), path, "exec")
def sandbox(name, file, names, **env):
    """A module that stands where the billing module `name` would: first `env` - what its own imports give it (the standard library, and
    this file's sandboxes and stand-ins for the billing modules) - then the code lifted out of scripts/helpers/<file>. It is never put in
    sys.modules: the test hands it on by hand, so nothing else can import it."""
    m = types.ModuleType(name); m.__file__ = os.path.join(HELPERS, file); m.UNDER_TEST = True; m.__dict__.update(env)
    exec(lift(m.__file__, names), m.__dict__)
    return m
def standin(name, **attrs):
    m = types.ModuleType(name); m.STAND_IN = True
    for k, v in attrs.items(): setattr(m, k, v)
    return m
def unanswered(what):      # a stand-in's answer until a section gives it its own: every call is refused, so nothing goes anywhere
    def refuse_call(*a, **k): raise RuntimeError("the stand-in %s has no answer for this call yet - nothing leaves this test" % what)
    return refuse_call
deceased_guard = standin("deceased_guard", check_charge=unanswered("deceased_guard.check_charge")); sys.modules["deceased_guard"] = deceased_guard      # amd.rebill_charge imports it by name
amd = sandbox("amd", "amd.py", ("OFFICE", "USER", "_msgtime", "msg", "WS_DIR", "REBILL_LOG", "_REBILLED", "_visit_of", "_rebill_log", "rebill_charge"),
              re=re, os=os, json=json, sys=sys, time=time, datetime=datetime, ET=ET, post=unanswered("amd.post"), login_cached=unanswered("amd.login_cached"),
              requests=standin("requests", post=unanswered("requests.post"), get=unanswered("requests.get")))
resave = sandbox("resave", "resave.py", ("detail", "CHG_FIELDS", "READ_NOTE", "_fault_text", "visit_charges", "DATE_ATTRS", "clean_extins", "order_list", "billed_reasons",
                                         "HOSP_CODES", "admit_of", "admit_codes", "restore_admit", "admit_back", "set_insorder"), amd=amd, re=re, sys=sys, ET=ET)
freq1_visit = sandbox("freq1_visit", "freq1_visit.py", ("run", "reroute"), amd=amd, resave=resave, sys=sys, time=time)
move_to_ins = sandbox("move_to_ins", "move_to_ins.py", ("move",), amd=amd, resave=resave, re=re, sys=sys, time=time, ET=ET)
ins_update = sandbox("ins_update", "ins_update.py", ("KEYS", "_plans", "_active", "_send", "_norm", "_set_order", "update"), amd=amd, re=re, sys=sys, datetime=datetime)
approval_submit = sandbox("approval_submit", "approval_submit.py", ("PAGE", "CASCADE", "SSN", "MBI", "IDWORD", "IDWORD2", "DOB", "VAICN", "NAMEFIELD", "LASTFIRST", "ADDINS", "now",
                                                                   "privacy_hit", "repo_safe", "build_items", "collisions", "register", "email", "total_dollars", "card_link",
                                                                   "push_text", "title", "html_email"),
                          json=json, os=os, re=re, sys=sys, datetime=datetime, html=_html)      # it never talks to AdvancedMD; lifted all the same - without its git and gate steps
if (LIVE & set(sys.modules)) != {"deceased_guard"}: raise RuntimeError("a live module is loaded in this process (%s) - the test does not run" % sorted(LIVE & set(sys.modules)))
REAL_VISIT_CHARGES, REAL_DETAIL = resave.visit_charges, resave.detail      # 11/11/2026 (round 8): the REAL history read and charge detail (lifted out of resave.py), kept for section H (sections B-D put stand-ins in their place)
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond: FAILS.append(name)

# ------------------------------------------------------------------ A. amd.rebill_charge: one rebill per VISIT per run
class Resp:
    def __init__(self, code): self.status_code = code; self.text = ""
CALLS = []; NEXT = []
def fake_post(url, json=None, headers=None, timeout=None):
    CALLS.append(json); return Resp(NEXT.pop(0) if NEXT else 204)
amd.requests = types.SimpleNamespace(post=fake_post)
amd.login_cached = lambda psw=None: ("https://web", "tok")
VISIT_OF = {"801": "900", "802": "900", "803": "901"}
def detail_post(body, timeout=180):
    m = re.search(r'chargeid="(\d+)"', body)
    if not m or m.group(1) not in VISIT_OF: raise RuntimeError("detail unreadable")
    return '<PPMDResults><Results><visit id="vst%s" episode="1"/><patient id="pat5"/></Results></PPMDResults>' % VISIT_OF[m.group(1)]
amd.post = detail_post
check("audit log path follows BILLING_WORKSPACE", amd.REBILL_LOG.startswith(TMP), amd.REBILL_LOG)
c1 = amd.rebill_charge("charge801", 1, dod_guard=False)
c2 = amd.rebill_charge("802", 1, dod_guard=False)
check("first rebill of a visit is sent (204)", c1[0] == 204 and len(CALLS) == 1 and not c1[1].startswith("SKIPPED"), c1)
check("second charge of the SAME visit, same seq, same run -> 204 SKIPPED, nothing sent", c2[0] == 204 and c2[1].startswith("SKIPPED") and len(CALLS) == 1, c2)
c3 = amd.rebill_charge("801", 2, dod_guard=False)
check("same visit, another sequence -> sent", c3[0] == 204 and len(CALLS) == 2, c3)
c4 = amd.rebill_charge("801", 1, dod_guard=False, allow_repeat=True)
check("allow_repeat forces a second rebill", c4[0] == 204 and len(CALLS) == 3 and not c4[1].startswith("SKIPPED"), c4)
c5 = amd.rebill_charge("803", 1, dod_guard=False)
check("a different visit is sent", c5[0] == 204 and len(CALLS) == 4, c5)
NEXT[:] = [500]; c6 = amd.rebill_charge("x77", 1, dod_guard=False, visitid="950"); c7 = amd.rebill_charge("x77", 1, dod_guard=False, visitid="950")
check("a 500 is not recorded - the next rebill of that visit is sent", c6[0] == 500 and c7[0] == 204 and len(CALLS) == 6, (c6, c7))
c8 = amd.rebill_charge("999", 1, dod_guard=False); c9 = amd.rebill_charge("999", 1, dod_guard=False)
check("unreadable visit falls back to the charge id (fail-open, still one per charge)", c8[0] == 204 and c9[1].startswith("SKIPPED") and len(CALLS) == 7, (c8, c9))
amd._REBILLED.clear()                                   # a NEW script run (process) starts with an empty guard
c10 = amd.rebill_charge("801", 1, dod_guard=False)
check("a LATER run is never blocked (corrected rebill after a claim-run rejection goes out)", c10[0] == 204 and len(CALLS) == 8 and not c10[1].startswith("SKIPPED"), c10)
log = [json.loads(l) for l in open(amd.REBILL_LOG)]
check("every sent 2xx rebill is in the audit log (7), skips and 500s are not", len(log) == 7 and all(e["status"] == 204 for e in log), len(log))
deceased_guard.check_charge = lambda cid, seq: (True, "DOS after date of death")      # the guard's stand-in (top of the file): amd.rebill_charge imports it by name
c11 = amd.rebill_charge("803", 3)
check("deceased guard still blocks (409) and is not recorded", c11[0] == 409 and "v901:3" not in amd._REBILLED and len(CALLS) == 8, c11)

# ------------------------------------------------------------------ B. resave.set_insorder (no rebill)
# 11/11/2026: the stand-in AdvancedMD of sections B-D is ONE invented visit (vst900 of chart pat77, charges charge500..) kept in STATE, and it
#   answers BY ACTION, the way the real system does (shapes: docs/captured_calls.md, and the reviewed stand-in of tools/selftest/test_feed_order.py):
#     getchargedetaildataicd10 -> a READ, the detail of THAT charge: the patient, the visit (insorder, extins with the admission date of that
#                                 charge's procedure code, the insurance-order LIST), the charge with its bill signs, the procedure list (id -> code);
#     updvisitwithcharges      -> the SAVE: the new order lands and the list follows it; a live charge left out of the echo is voided;
#     updextrainsinfo          -> the admission date written for that procedure code (with a resubmissioncode: section C's frequency reset);
#     any other action         -> AssertionError that names it. Until 11/11/2026 every call was taken for a save, and the first READ crashed here.
#   STATE["posts"] holds the SAVES only, so "nothing posted" still means "no save was sent"; the reads, the admission-date writes and the
#   frequency resets are counted on their own (STATE["reads"], ["admits"], ["resets"]; STATE["log"] = all four kinds in the order they came).
_sleep = time.sleep; time.sleep = lambda *a: None      # set_insorder waits 0.8 s after every save - nothing to wait for here (put back after section D)
PROC = {"99309": "pcode1", "99223": "pcode2", "99497": "pcode3"}      # the stand-in's procedure list: code -> procedure id (a charge carries the id; its detail maps it back)
STATE = {}; UNANSWERED = []
def fresh(**kw):      # the visit as a check needs it. Default: never billed, two 99309 charges, order 1,2 with its list, no admission date, nothing counted
    STATE.clear(); STATE.update(order="1,2", lst=None, n=2, fault=False, cpt={}, bill={}, admit={}, void=set(), lands=True, builds=True, wipe=False, restore=True, gone=(), grow=0,
                                noanswer=None, readfail=0, vcfail=0, ext={}, resetfault=False, posts=[], reads=[], admits=[], resets=[], log=[]); STATE.update(kw)
fresh()
def cids(): return ["charge%d" % (500 + k) for k in range(STATE["n"])]
def later(mark, what): return mark in STATE["log"] and any(x.startswith(what) for x in STATE["log"][STATE["log"].index(mark) + 1:])      # did a `what...` come after `mark`?
def charge(cid):      # one charge as its OWN detail shows it; STATE["bill"][cid] = (attributes, child rows) = its bill signs
    a, kids = STATE["bill"].get(cid, ({}, ""))
    c = ET.fromstring('<charge id="%s" proccode="%s" fee="100.00" insbalance="100.00" void="%d" insbilled="0" datebilled="">%s</charge>' % (cid, PROC[STATE["cpt"].get(cid, "99309")], cid in STATE["void"], kids))
    c.attrib.update(a); return c
def visit(order, n=2, cid="charge500"):
    v = ET.Element("visit", {"id": "vst900", "episode": "ep1", "insorder": order})
    adm = STATE["admit"].get(STATE["cpt"].get(cid, "99309"), "")      # AdvancedMD keeps the admission date per procedure code: a charge's detail shows its own code's
    ET.SubElement(v, "extins", dict(dict({"id": "ext900"}, **STATE["ext"]), **({"hospitalizationfrom": adm} if adm else {})))      # ext = what the extra-info row already carries (a corrected claim: resubmissioncode 7 + the payer's reference number)
    lst = ET.SubElement(v, "insuranceorderlist")      # 11/10/2026: AdvancedMD builds the visit's insurance-order LIST from its order; set_insorder reads it
    for i, s in enumerate(x for x in (order if STATE["lst"] is None else STATE["lst"]).replace(" ", "").split(",") if x): ET.SubElement(lst, "insuranceorder", {"sequence": s, "ordinal": str(i)})
    p = ET.Element("patient", {"id": "pat77"})
    cs = [charge(c) for c in ("charge%d" % (500 + k) for k in range(n)) if c not in STATE["void"]]
    return v, p, cs
def live_charges(cid):      # the stand-in of resave.visit_charges; vcfail = how many of ITS reads after the save get no answer
    if STATE["vcfail"] and "save" in STATE["log"]: STATE["vcfail"] -= 1; raise TimeoutError("read timed out")
    return visit(STATE["order"], STATE["n"], "charge" + re.sub(r"\D", "", str(cid)))
resave.visit_charges = live_charges
def refuse(what, body):
    UNANSWERED.append(what); raise AssertionError("the stand-in AdvancedMD of sections B-D has no answer for %s: %s" % (what, body[:200]))
def r_post(body, timeout=180):
    m = re.match(r'<ppmdmsg action="([^"]*)"', body); act = m.group(1) if m else "?"
    if act == "getchargedetaildataicd10":      # a READ - never counted as a save
        m = re.search(r' chargeid="(\d+)"', body); cid = "charge" + (m.group(1) if m else "?")
        if cid not in cids(): refuse("action getchargedetaildataicd10 for a charge the visit does not have", body)
        if STATE["readfail"] and "save" in STATE["log"]: STATE["readfail"] -= 1; raise TimeoutError("read timed out")      # readfail = how many reads AFTER the save get no answer
        STATE["reads"].append(cid); STATE["log"].append("read " + cid); v, p, _cs = visit(STATE["order"], STATE["n"], cid); c = charge(cid)
        return '<PPMDResults><Results>%s%s%s<proccodelist><proccode id="%s" code="%s"/></proccodelist></Results></PPMDResults>' % (
            ET.tostring(p, encoding="unicode"), ET.tostring(v, encoding="unicode"), ET.tostring(c, encoding="unicode"), c.get("proccode"), STATE["cpt"].get(cid, "99309"))
    if act == "updextrainsinfo":      # the admission date written for ONE procedure code - or, with a resubmissioncode, the frequency reset of freq1_visit.run
        m = re.search(r'<extins ([^>]*)/>', body)
        if not m or not re.search(r' visitid="(vst)?900"', body): refuse("action updextrainsinfo without an extins row for visit 900", body)
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1))); code = a.get("txtChargeCode", "")
        if "resubmissioncode" in a:
            STATE["resets"].append(body); STATE["log"].append("reset " + code)
            if STATE["resetfault"]: return "<PPMDResults><Error><Fault>boom</Fault></Error></PPMDResults>"
            return '<PPMDResults><Results><extins id="ext900" resubmissioncode="%s" origrefnum="%s"/></Results></PPMDResults>' % (a["resubmissioncode"], a.get("origrefnum", ""))
        STATE["admits"].append(body); STATE["log"].append("admit " + code)
        if STATE["restore"] is True and a.get("hospitalizationfrom"): STATE["admit"][code] = a["hospitalizationfrom"]      # kept for THAT code, exactly as it was sent
        return '<PPMDResults><Results><extins id="ext900" hospitalizationfrom="%s" hospitalizationto=""/></Results></PPMDResults>' % (a.get("hospitalizationfrom", "") if STATE["restore"] == "says" else STATE["admit"].get(code, ""))      # restore "says" = answered with the date, not kept
    if act == "updvisitwithcharges":      # the SAVE
        STATE["posts"].append(body); STATE["log"].append("save")
        if STATE["fault"]: return "<PPMDResults><Error><Fault>boom</Fault></Error></PPMDResults>"
        m = re.search(r'<visit [^>]*insorder="([^"]*)"', body)
        if not m: refuse("action updvisitwithcharges without a visit insorder", body)
        echoed = re.findall(r'<charge id="(charge\d+)"', body)
        STATE["void"] |= {c for c in cids() if c not in echoed} | set(STATE["gone"])      # a live charge left out of the echo is voided (learned 9/3/2026); gone = voided although it was echoed
        was = STATE["order"] if STATE["lst"] is None else STATE["lst"]
        if STATE["lands"]: STATE["order"] = m.group(1); STATE["lst"] = None if STATE["builds"] else was      # the list follows the new order - unless the chart has no plan to build it from (lands False: accepted, and nothing changed)
        STATE["n"] += STATE["grow"]      # grow = a charge that was not there before the save
        if STATE["wipe"]: STATE["admit"] = dict.fromkeys(STATE["admit"], "" if STATE["wipe"] is True else STATE["wipe"])      # a save can wipe the admission date (docs/captured_calls.md, 9/22/2026)
        if STATE["noanswer"]: raise STATE["noanswer"]      # the save landed, its answer never comes back
        return '<PPMDResults><Results success="1"/></PPMDResults>'
    refuse("action %r" % act, body)
amd.post = r_post
REB = []; amd_rebill_orig = amd.rebill_charge
amd.rebill_charge = lambda cid, seq, **k: (REB.append((cid, seq)) or (204, ""))
ok, msg = resave.set_insorder("500", "1,2"); check("same order -> skipped, nothing posted", ok and not STATE["posts"], msg)
ok, msg = resave.set_insorder("500", "3,2", dry=True); check("dry -> nothing posted", ok and not STATE["posts"] and "DRY" in msg, msg)
ok, msg = resave.set_insorder("500", "3, 2")
body = STATE["posts"][-1]
check("live -> one updvisitwithcharges, every charge echoed, force=1, no rebill",
      ok and len(STATE["posts"]) == 1 and body.count("<charge ") == 2 and 'force="1"' in body and 'insorder="3,2"' in body and not REB, msg)
STATE["fault"] = True; ok, msg = resave.set_insorder("500", "1"); STATE["fault"] = False
check("Fault -> ok False", not ok and "FAULT" in msg, msg)

# ---- B2 (11/11/2026). What rule version 2026-11-10.7 added to set_insorder, proved on the REAL resave.py - each check fails when its rule is broken.
ADM = "10/27/2026"
HOSP = lambda: dict(cpt={"charge500": "99497", "charge501": "99223"}, admit={"99223": ADM})      # a 99497 (the charge named) and a 99223: the admission date is the 99223's, and only its own detail shows it
SHAPE = ('<extins txtChargeCode="99223" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
         'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % ADM      # the import's own call for the admission date (claimocity_import.py)
BILLED = ({"datebilled": "10/28/2026 21:07:13", "insbilled": "1"},      # billed, and answered with a $0.00 line: a bill date, the flag, a bill row, a payment
          '<insbilllist><insbill billeddate="10/28/2026"/></insbilllist><paymentlist><payment amount="0.00" void="0"/></paymentlist>')
def setord(*a, **k):      # resave.set_insorder - a raise becomes an answer the check shows, so one broken guarantee cannot hide the checks after it
    try: return resave.set_insorder(*a, **k)
    except Exception as e: return None, "RAISED %s: %s" % (type(e).__name__, e)
def route(*a, **k):      # freq1_visit.reroute, the same way (section C2)
    try: return freq1_visit.reroute(*a, **k)
    except Exception as e: return "RAISED %s: %s" % (type(e).__name__, e)
fresh()
try: amd.post(amd.msg("gettxhistory", "demographics", {"patientid": "pat77"})); _r = "answered"
except Exception as e: _r = "%s: %s" % (type(e).__name__, e)
check("the stand-in refuses an action it has no answer for, by its name, and never counts it as a save",
      _r.startswith("AssertionError") and "'gettxhistory'" in _r and not STATE["posts"] and UNANSWERED == ["action 'gettxhistory'"], (_r, UNANSWERED)); UNANSWERED.clear()
# a dry run reads and never writes
fresh(**HOSP(), wipe=True); ok, msg = setord("500", "3,2", dry=True)
check("dry: the visit is only READ (each live charge's own detail) - no save, no admission-date write; the order, the list and the date stay as they were",
      ok and "DRY" in msg and "list [1,2]" in msg and sorted(set(STATE["reads"])) == ["charge500", "charge501"] and not STATE["posts"] and not STATE["admits"]
      and STATE["order"] == "1,2" and STATE["admit"] == {"99223": ADM}, (msg, STATE["log"]))
# the insurance-order LIST decides, not the attribute; and the save is only as good as what is read back
fresh(order="1", lst=""); ok, msg = setord("500", "1")
check("the attribute already reads the order but the insurance-order LIST is EMPTY (a feed visit entered while its chart had no plan) -> NOT skipped: saved once, the message carries the list before and after",
      ok and len(STATE["posts"]) == 1 and 'insorder="1"' in STATE["posts"][0] and "list [] -> [1]" in msg and "skipped" not in msg, msg)
fresh(order="1", lst="1,2"); ok, msg = setord("500", "1")
check("the attribute reads the order but the list holds ANOTHER order -> saved, list [1,2] -> [1] (the attribute alone proves nothing)", ok and len(STATE["posts"]) == 1 and "list [1,2] -> [1]" in msg, msg)
fresh(order="1", lst="", builds=False); ok, msg = setord("500", "1")
check("the save is accepted but AdvancedMD builds NO list -> NOT ok: list [] -> [], 'NOT as asked'", ok is False and len(STATE["posts"]) == 1 and "list [] -> []" in msg and "NOT as asked" in msg, msg)
fresh(order="1", lands=False); ok, msg = setord("500", "2")
check("the save is accepted but the order does not land -> NOT ok: read back as it was, 'NOT as asked'", ok is False and len(STATE["posts"]) == 1 and "insorder 1 -> 1, list [1] -> [1]" in msg and "NOT as asked" in msg, msg)
# a visit already billed is never saved - unless the caller passes allow_billed=True
for _what, _word, _sign in (("a bill date", "bill date", ({"datebilled": "10/28/2026 21:07:13"}, "")), ("the insurance-bill flag", "insurance bill", ({"insbilled": "1"}, "")),
                            ("an insurance-bill row", "insurance bill", ({}, '<insbilllist><insbill billeddate="10/28/2026"/></insbilllist>')),
                            ("a payment that is not void, even of $0.00", "payment", ({}, '<paymentlist><payment amount="0.00" void="0"/></paymentlist>'))):
    fresh(order="1", bill={"charge501": _sign}); ok, msg = setord("500", "2,1")
    check("a visit already billed (%s on one of its live charges) is REFUSED: 'already billed - not saved', nothing sent" % _what,
          ok is False and "already billed - not saved (%s on a live charge" % _word in msg and not STATE["posts"] and not STATE["admits"] and STATE["order"] == "1", msg)
fresh(order="1", bill={"charge501": ({}, '<paymentlist><payment amount="60.74" void="1"/></paymentlist>')}); ok, msg = setord("500", "2,1")
check("a VOID payment is not a bill sign: that visit is saved", ok and len(STATE["posts"]) == 1 and "list [1] -> [2,1]" in msg, msg)
fresh(order="1", bill={"charge500": BILLED, "charge501": BILLED}); ok, msg = setord("500", "2,1", allow_billed=True)
check("the billed visit WITH allow_billed=True (the two re-route helpers' word) IS saved: one save, every charge echoed, read back",
      ok and len(STATE["posts"]) == 1 and STATE["posts"][0].count("<charge ") == 2 and "list [1] -> [2,1]" in msg and "already billed" not in msg, msg)
fresh(bill={"charge500": BILLED, "charge501": BILLED}); ok, msg = setord("500", "1,2")
check("a billed visit whose attribute AND list already read the order: nothing to do - ok, skipped, nothing sent (no false refusal)", ok and "resave skipped" in msg and not STATE["posts"], msg)
# the admission date of a hospital code, read from that code's own charge detail before the save and after it
fresh(order="1", **HOSP()); ok, msg = setord("500", "2,1")
check("a hospital code's admission date that the save KEEPS: ok, nothing written, not a word about it",
      ok and len(STATE["posts"]) == 1 and not STATE["admits"] and "admission" not in msg and STATE["admit"] == {"99223": ADM}, (msg, STATE["log"]))
fresh(order="1", **HOSP(), wipe=True); ok, msg = setord("500", "2,1")
check("a hospital code's admission date that the save WIPES: written back with updextrainsinfo for THAT code (the import's own call, visit vst900) and read again - ok, and the message says it was written back",
      ok and len(STATE["admits"]) == 1 and SHAPE in STATE["admits"][0] and 'action="updextrainsinfo" class="chargeentry"' in STATE["admits"][0] and 'visitid="vst900"' in STATE["admits"][0]
      and STATE["admit"] == {"99223": ADM} and "admission date %s was lost on save and written back (99223)" % ADM in msg and later("admit 99223", "read charge501"), (msg, STATE["log"]))
fresh(order="1", **HOSP(), wipe=True, restore=False); ok, msg = setord("500", "2,1")
check("a hospital code's admission date that the save wipes and that CANNOT be written back: NOT ok, 'admission date lost on save' (was the date, now none), after one try",
      ok is False and "admission date lost on save (was %s, now none" % ADM in msg and len(STATE["admits"]) == 1 and "NOT as asked" in msg, (msg, STATE["log"]))
fresh(order="1", admit={"99309": ADM}, wipe=True); ok, msg = setord("500", "2,1")
check("a visit with NO hospital code whose one admission date the save wipes: there is no code to write it back for - NOT ok, said",
      ok is False and "admission date lost on save (was %s, now none; written back for no hospital code)" % ADM in msg and not STATE["admits"], (msg, STATE["log"]))
# every live charge is echoed, and each is looked for again by its id
fresh(order="1", n=3); ok, msg = setord("501", "2")
check("every live charge of the visit is echoed in the save - three of three, whichever charge was named - and all are live after it",
      ok and len(STATE["posts"]) == 1 and re.findall(r'<charge id="(charge\d+)"', STATE["posts"][0]) == ["charge500", "charge501", "charge502"] and not STATE["void"] and "3 live charges (was 3)" in msg, (msg, sorted(STATE["void"])))
fresh(order="1", gone=("charge501",)); ok, msg = setord("500", "2")
check("a charge that is NO LONGER LIVE after the save -> NOT ok, named", ok is False and "no longer live: charge501" in msg and "NOT as asked" in msg, msg)
fresh(order="1", grow=1); ok, msg = setord("500", "2")
check("a charge that is NEW after the save -> NOT ok, named", ok is False and "new: charge502" in msg and "NOT as asked" in msg, msg)
fresh(order="1", gone=("charge501",), grow=1); ok, msg = setord("500", "2")
check("one charge gone and one new - the same COUNT as before - is NOT ok either: every echoed charge is looked for by its id", ok is False and "no longer live: charge501" in msg and "new: charge502" in msg, msg)
# an error after the save was sent is never raised: the visit is read again and the answer is NOT ok
fresh(order="1", **HOSP(), wipe=True, noanswer=TimeoutError("read timed out")); ok, msg = setord("500", "2,1")
check("the save lands but its answer never comes back: NOT raised - the visit is read again, the wiped admission date written back, NOT ok, with what the visit reads now",
      ok is False and "the answer to the save never came back (TimeoutError" in msg and "list [1] -> [2,1]" in msg and STATE["admit"] == {"99223": ADM} and len(STATE["admits"]) == 1 and "NOT as asked" in msg, (msg, STATE["log"]))
fresh(order="1", **HOSP(), readfail=1); ok, msg = setord("500", "2,1")
check("a read after the save gets no answer: NOT raised - the visit is read again, NOT ok, with what it reads now",
      ok is False and "the read-back after the save failed (TimeoutError" in msg and "read again: insorder 2,1, list [1] -> [2,1]" in msg and "NOT as asked" in msg, (msg, STATE["log"]))
fresh(order="1", **HOSP(), readfail=99); ok, msg = setord("500", "2,1")
check("no read after the save gets an answer: NOT raised - NOT ok, 'look at it in AdvancedMD before anything else is sent'",
      ok is False and "the visit could not be read again (TimeoutError)" in msg and "look at it in AdvancedMD before anything else is sent" in msg, (msg, STATE["log"]))
# ---- B3 (proposed by the independent check, 11/11/2026). Until 11/10 every call of set_insorder was a save, so "nothing posted" meant NOTHING
#      was sent. Since rule version .7 the helper also reads and writes admission dates: these checks say again that nothing of ANY kind goes out.
def sent(): return [x for x in STATE["log"] if not x.startswith("read ")]      # everything that is not a read: saves, admission-date writes, frequency resets
fresh(); ok, msg = setord("500", "1,2")
check("skipped: once the visit is read NOTHING more goes to AdvancedMD - no charge detail, no save, no admission-date write, no frequency reset", ok and "resave skipped" in msg and not STATE["log"], (msg, STATE["log"]))
fresh(**HOSP(), wipe=True); ok, msg = setord("500", "3,2", dry=True)
check("dry: every call is a READ - nothing of any other kind is sent", ok and "DRY" in msg and STATE["log"] and not sent(), (msg, STATE["log"]))
fresh(order="1", bill={"charge500": BILLED, "charge501": BILLED}); ok, msg = setord("500", "2,1")
check("a billed visit is refused with NOTHING sent - no save, no admission-date write, no frequency reset", ok is False and "already billed - not saved" in msg and not sent(), (msg, STATE["log"]))
fresh(order="1", bill={"charge501": BILLED}); ok, msg = setord("500", "2,1", dry=True)
check("a DRY run on a billed visit says what the live run would do: refused, not 'DRY resave'", ok is False and "already billed - not saved" in msg and "DRY" not in msg and not sent(), msg)
fresh(order="1"); ok, msg = setord("500", "2")
check("a plain save sends ONE save and nothing else, each live charge echoed AS READ (its procedure, fee and balance) and the visit with its own attributes",
      ok and sent() == ["save"] and '<visit id="vst900" episode="ep1" insorder="2" force="1"><chargelist><charge id="charge500" proccode="pcode1" fee="100.00" insbalance="100.00"/><charge id="charge501" proccode="pcode1" fee="100.00" insbalance="100.00"/></chargelist></visit>' in STATE["posts"][0], (msg, STATE["posts"]))
fresh(order="2", lst="1"); ok, msg = setord("500", "1")
check("the LIST already reads the order but the attribute does NOT -> NOT skipped: saved once (the list alone proves nothing either)",
      ok and len(STATE["posts"]) == 1 and "insorder 2 -> 1, list [1] -> [1]" in msg and "skipped" not in msg, msg)
fresh(order="1", lst="2", lands=False); ok, msg = setord("500", "2")
check("the save is accepted, the list reads the order but the ATTRIBUTE does not -> NOT ok", ok is False and len(STATE["posts"]) == 1 and "insorder 1 -> 1, list [2] -> [2]" in msg and "NOT as asked" in msg, msg)
for _k in ("charge500", "charge501", "charge502"):
    fresh(order="1", n=3, bill={_k: ({"datebilled": "10/28/2026 21:07:13"}, "")}); ok, msg = setord("501", "2,1")
    check("a bill sign on ANY live charge refuses the visit (on %s of three; charge501 was named)" % _k, ok is False and "already billed - not saved (bill date on a live charge" in msg and not sent(), msg)
fresh(order="1", **HOSP(), wipe=True, restore="says"); ok, msg = setord("500", "2,1")
check("the write-back is ANSWERED with the date but the visit still reads none: the read after it decides - NOT ok, 'admission date lost on save'",
      ok is False and "admission date lost on save (was %s, now none" % ADM in msg and len(STATE["admits"]) == 1 and "NOT as asked" in msg, (msg, STATE["log"]))
fresh(order="1", **HOSP(), wipe=True, restore=False); ok, msg = setord("500", "2,1")
check("a write-back that is refused is named with its code: 'refused for 99223'", ok is False and "written back for 99223, refused for 99223" in msg, msg)
fresh(order="1", **HOSP(), wipe="11/01/2026"); ok, msg = setord("500", "2,1")
check("a hospital code's admission date that the save CHANGES (not wipes) is written back too", ok and len(STATE["admits"]) == 1 and SHAPE in STATE["admits"][0] and STATE["admit"] == {"99223": ADM} and "written back (99223)" in msg, (msg, STATE["log"]))
fresh(order="1", vcfail=1); ok, msg = setord("500", "2,1")
check("the FIRST read after the save (the visit's live charges) gets no answer: NOT raised - the visit is read again, NOT ok, with what it reads now",
      ok is False and "the read-back after the save failed (TimeoutError" in msg and "read again: insorder 2,1, list [1] -> [2,1]" in msg and "NOT as asked" in msg, msg)
fresh()      # section C starts from the visit as it was

# ------------------------------------------------------------------ C. freq1_visit.reroute
RUNS = []; f_run = freq1_visit.run
freq1_visit.run = lambda vid, cid, seq: (RUNS.append((vid, cid, seq)) or "freq1 + rebill seq %s -> 204" % seq)
freq1_visit.time = types.SimpleNamespace(sleep=lambda s: None)
STATE["order"] = "1,2"; r = freq1_visit.reroute("900", "500", "3,2")
check("reroute = order then ONE freq-1 rebill to the first plan", RUNS == [("900", "500", 3)] and "rebill seq 3" in r, r)
RUNS.clear(); STATE["fault"] = True; r = freq1_visit.reroute("900", "500", "1"); STATE["fault"] = False
check("reroute does NOT rebill when the order step fails", not RUNS and r.startswith("NOT rebilled"), r)
RUNS.clear(); STATE["order"] = "1,2"; r = freq1_visit.reroute("900", "500", "2,1", dry=True)
check("reroute dry -> no rebill", not RUNS and "DRY" in r, r)

# ---- C2 (11/11/2026). The real nightly case: the visit is ALREADY BILLED (a wrong-payer denial), and reroute passes allow_billed=True.
s_run = freq1_visit.run      # the recorder set above (RUNS); f_run is the real frequency-1 reset + rebill
def billed(**kw): fresh(bill={"charge500": BILLED, "charge501": BILLED}, **kw); RUNS.clear(); REB.clear()
billed(); r = route("900", "500", "3,2")
check("reroute on an ALREADY-BILLED visit (the nightly re-route after a wrong-payer denial): the order IS saved, then ONE freq-1 rebill to the first plan of the new order",
      RUNS == [("900", "500", 3)] and len(STATE["posts"]) == 1 and 'insorder="3,2"' in STATE["posts"][0] and "list [1,2] -> [3,2]" in r and "rebill seq 3" in r and not r.startswith("NOT rebilled"), r)
billed(); r = route("900", "500", "3,2", dry=True)
check("reroute dry on an already-billed visit: said, nothing saved, no rebill", not RUNS and "DRY resave" in r and "DRY freq1 + rebill seq 3" in r and not STATE["posts"], r)
billed(); _real = resave.set_insorder
resave.set_insorder = lambda cid, order, dry=False, allow_billed=False: _real(cid, order, dry=dry)      # the order step asked WITHOUT the re-route's word: the billed guard refuses it
r = route("900", "500", "3,2"); resave.set_insorder = _real
check("reroute does NOT rebill when the order step is REFUSED (the billed guard - asked here without the re-route's word): 'NOT rebilled', nothing sent",
      not RUNS and r.startswith("NOT rebilled") and "already billed - not saved" in r and not STATE["posts"] and STATE["order"] == "1,2", r)
billed(fault=True); r = route("900", "500", "3,2")
check("reroute on an already-billed visit does NOT rebill when the save FAILS (a Fault): one save tried, 'NOT rebilled'", not RUNS and r.startswith("NOT rebilled") and "resave FAULT" in r and len(STATE["posts"]) == 1, r)
billed(cpt={"charge500": "99223"}, admit={"99223": ADM}, wipe=True, restore=False); r = route("900", "500", "3,2")
check("reroute on an already-billed HOSPITAL visit does NOT rebill when the save wiped the admission date and it cannot be written back", not RUNS and r.startswith("NOT rebilled") and "admission date lost on save" in r, r)
billed(cpt={"charge500": "99223"}, admit={"99223": ADM}, wipe=True); r = route("900", "500", "3,2")
check("reroute on an already-billed HOSPITAL visit rebills ONCE when the wiped admission date was written back", RUNS == [("900", "500", 3)] and "written back (99223)" in r and STATE["admit"] == {"99223": ADM}, r)
freq1_visit.run = f_run      # ONCE with the REAL freq1_visit.run under reroute (amd.rebill_charge is still section B's recorder REB)
billed(); r = route("900", "500", "3,2"); freq1_visit.run = s_run
check("the whole re-route of an already-billed visit on the real helpers: ONE save, then the frequency reset (resubmissioncode 1, no payer reference number), then exactly ONE rebill - to sequence 3",
      REB == [("500", 3)] and len(STATE["posts"]) == 1 and len(STATE["resets"]) == 1 and 'resubmissioncode="1"' in STATE["resets"][0] and 'origrefnum=""' in STATE["resets"][0]
      and later("save", "reset ") and r.endswith("| freq1 + rebill seq 3 -> 204"), (r, REB, STATE["log"]))
# ---- C3 (proposed by the independent check, 11/11/2026): the REAL freq1_visit.run under reroute, on a visit whose extra-info row is a corrected claim
_reb0 = amd.rebill_charge
def _reb1(cid, seq, **k): REB.append((cid, seq)); STATE["log"].append("rebill %s" % seq); return 204, ""      # the same recorder, and it writes its place into the log
amd.rebill_charge = _reb1; freq1_visit.run = f_run
billed(cpt={"charge500": "99497"}, ext={"resubmissioncode": "7", "origrefnum": "ICN900"}); r = route("900", "500", "3,2")
check("the real reset + rebill after the order: ONE save, then a reset for EACH procedure of the visit - frequency 1, the payer's reference number BLANKED (it read 7 / ICN900) - and only then the ONE rebill",
      [x.split()[0] for x in sent()] == ["save", "reset", "reset", "rebill"] and all('resubmissioncode="1"' in b and 'origrefnum=""' in b and "ICN900" not in b for b in STATE["resets"]) and REB == [("500", 3)], (r, STATE["log"]))
billed(resetfault=True); r = route("900", "500", "3,2")
check("the frequency reset answers a Fault: NO rebill, and it is said", REB == [] and "FAULT extins" in r and [x.split()[0] for x in sent()] == ["save", "reset"], (r, STATE["log"]))
amd.rebill_charge = _reb0; freq1_visit.run = s_run
billed(); r = route("900", "500", "3,2", seq=2)
check("reroute rebills to the sequence the caller names (2), not to the first plan of the order", RUNS == [("900", "500", 2)] and "rebill seq 2" in r, r)
fresh(); RUNS.clear(); REB.clear()      # section D starts from the visit as it was

# ------------------------------------------------------------------ D. move_to_ins.move rebill flag
move_to_ins.time = types.SimpleNamespace(sleep=lambda s: None)
resave.detail = lambda cid: '<x><visit id="vst900" insorder="%s"/><charge id="charge500" insbalance="100.00" patbalance="0.00"/></x>' % STATE["order"]
REB.clear(); STATE["order"] = "1,2"; m1 = move_to_ins.move("500", "2,1", rebill=False)
check("move(..., rebill=False) never rebills", not REB and "no rebill" in m1, m1)
REB.clear(); m2 = move_to_ins.move("500", "1,2")
check("move(...) default keeps its single rebill (backward compatible)", REB == [("500", 1)], (REB, m2))
check("the stand-in AdvancedMD of sections B-D had an answer for every call the helpers made (no action it does not know)", not UNANSWERED, UNANSWERED)
time.sleep = _sleep

# ------------------------------------------------------------------ E. ins_update.update order carried by an ACTIVE plan + verified + restored
amd.rebill_charge = amd_rebill_orig
CH = {"insorder": "1,2", "plans": {"ins10": {"sequence": "1", "enddate": "06/21/2025", "carrier": "car1"},
                                   "ins20": {"sequence": "2", "enddate": "", "carrier": "car2"}}, "sent": [], "blank_via": set(), "boom": False}
def demo():
    if CH["boom"] and CH["sent"]: raise RuntimeError("read timeout")
    pl = "".join('<insplan id="%s" sequence="%s" enddate="%s" carrier="%s"/>' % (k, v["sequence"], v["enddate"], v["carrier"]) for k, v in CH["plans"].items())
    return '<PPMDResults><Results><patient id="pat5" insorder="%s"/>%s</Results></PPMDResults>' % (CH["insorder"], pl)
def i_post(body, timeout=180):
    if 'action="getdemographic"' in body: return demo()
    m = re.search(r'<insplan id="(ins\d+)" ([^>]*)>', body); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
    CH["sent"].append((m.group(1), a))
    if "sequence" in a:
        ended = CH["plans"][m.group(1)]["enddate"] != "" or m.group(1) in CH["blank_via"]
        CH["insorder"] = "" if ended else a["sequence"]
    else:
        CH["insorder"] = ""                                    # 9/21 behaviour: a plain field edit wipes the order
        for k in ("enddate", "carrier"):
            if k in a: CH["plans"][m.group(1)][k] = a[k]
    return '<?xml version="1.0"?><PPMDResults s="x" lst="y"><Results success="1"><patient insorder="%s" /></Results><Error /></PPMDResults>' % CH["insorder"]
def reset(order, end10="", blank=()):
    CH["sent"].clear(); CH["insorder"] = order; CH["plans"]["ins10"]["enddate"] = end10; CH["blank_via"] = set(blank); CH["boom"] = False
amd.post = i_post; amd._msgtime = lambda: "10/6/2026 3:30:00 AM"
reset("1,2", end10="06/21/2025")
ok, msg = ins_update.update("5", "ins10", sequence="2,1")        # the 10/6 chart-12232248 case: ins10 = the end-dated plan
check("order asked via an END-DATED plan is carried by the active plan and lands (one call)", ok and CH["insorder"] == "2,1" and [x[0] for x in CH["sent"]] == ["ins20"], (msg, CH["sent"]))
reset("1,2")
ok, msg = ins_update.update("5", "10", enddate="06/21/2025", sequence="2,1")
check("field edit + order = two calls; the field call carries NO sequence; order lands",
      ok and len(CH["sent"]) == 2 and "sequence" not in CH["sent"][0][1] and CH["sent"][0][0] == "ins10" and CH["sent"][1][0] == "ins20" and CH["insorder"] == "2,1", (msg, CH["sent"]))
reset("1,2", blank={"ins10"})
ok, msg = ins_update.update("5", "10", sequence="2,1")
check("a blank answer is re-sent ONCE through another active plan", ok and [x[0] for x in CH["sent"]] == ["ins10", "ins20"] and CH["insorder"] == "2,1", (msg, CH["sent"]))
reset("1,2", blank={"ins10", "ins20"})
ok, msg = ins_update.update("5", "10", sequence="2,1")
check("order that never lands: 2 tries, previous order restore attempted, reported NOT set", not ok and len(CH["sent"]) == 4 and "NOT set" in msg and "previous insorder" in msg, (msg, CH["sent"]))
reset("2,1")
ok, msg = ins_update.update("5", "20", carrier="car9")
check("a field edit that wipes the order gets the previous order put back", ok and CH["insorder"] == "2,1" and "restored" in msg and len(CH["sent"]) == 2 and "sequence" not in CH["sent"][0][1], (msg, CH["sent"]))
reset("1,2")
ok, msg = ins_update.update("5", "10", enddate="06/21/2025")
check("end-dating the LEADING plan: order not restored through it (would blank) - WARNING, field edit ok", ok and "WARNING" in msg and len(CH["sent"]) == 1, (msg, CH["sent"]))
reset("2,1", end10="06/21/2025")
ok, msg = ins_update.update("5", "20", sequence="1,2")
check("an order led by an end-dated plan is refused WITHOUT writing", not ok and not CH["sent"] and "end-dated" in msg, (msg, CH["sent"]))
reset("2,1"); CH["boom"] = True
try:
    ok, msg = ins_update.update("5", "10", enddate="06/21/2025", sequence="2,1"); raised = False
except Exception as e:
    raised = True; msg = repr(e)
check("a failed re-read after a write returns (ok, msg) instead of raising", not raised and "check the chart" in msg, msg)
reset("1,2")
ok, msg = ins_update.update("5", "99", sequence="1")
check("unknown plan -> insplan not found", not ok and msg == "insplan not found", msg)
ok, msg = ins_update.update("5", "10")
check("nothing to change -> no write", not ok and msg == "nothing to change" and not CH["sent"], msg)

# ------------------------------------------------------------------ F. approval email + push carry the links
items = approval_submit.build_items([{"letter": "A", "command": "cd /home/claude/unbilled && python3 x.py --live --only A", "reason": "classifier <refused>",
                                       "what": "chart 17470940 AARP carrier fix & exclusion", "dollars": "$21.80", "ui": "Patient > Insurance"},
                                      {"letter": "B", "command": "python3 x.py --live --only B", "reason": "r", "what": "chart 12232248", "dollars": "$1,656.00", "ui": ""}],
                                     "2026-10-06T0330Z", TMP)
h = approval_submit.html_email(items, "2026-10-06T0330Z", "APPROVAL NEEDED - test")
check("html: page button + one Review & Approve button per card", h.count("Review &amp; Approve") == 2 and approval_submit.PAGE + '"' in h
      and all(approval_submit.PAGE + "#" + i["id"] in h for i in items), h[:300])
check("html escapes item text", "&lt;refused&gt;" in h and "<refused>" not in h)
p2 = approval_submit.push_text(items, "2026-10-06T0330Z"); p1 = approval_submit.push_text(items[:1], "2026-10-06T0330Z")
check("push (several) <= 199 chars and ends with the page link", len(p2) <= 199 and p2.endswith(approval_submit.PAGE), p2)
check("push (one) ends with that card's link", len(p1) <= 199 and p1.endswith(approval_submit.PAGE + "#" + items[0]["id"]), p1)
long = [dict(items[0], id="A-2026-10-06T0330Z-%s" % ("X" * 60), dollars="$1")]
pl = approval_submit.push_text(long, "2026-10-06T0330Z")
check("push never exceeds 199 even with a long id", len(pl) <= 199 and pl.endswith(approval_submit.PAGE) or pl.endswith(long[0]["id"]), (len(pl), pl))
check("privacy gate still catches an SSN", approval_submit.privacy_hit("pt " + "123-45-" + "6789") == "SSN pattern")

# ------------------------------------------------------------------ G. approval_submit review fixes
for t, want in [('subscribernum="' + "1234" + '56789"', True), ('Member ID: XEH' + "1234" + "56789", True), ('"memberId": "VMYH' + '12345678"', True), ("DOB 01/02/" + "1940", True),
                ("ICN " + "1234567890V" + "123456", True), ('"last' + 'Name": "Doe"', True), ("chart 17470940 visit 19455208 99233 $160", False),
                ("'SUBSCRIBER ID NOT FOUND' + 'MEMBER PICK REJECT' on 19455208B", False)]:
    check("privacy gate %s: %s" % ("catches" if want else "passes", t[:40]), bool(approval_submit.privacy_hit(t)) == want, approval_submit.privacy_hit(t))
ef = os.path.join(TMP, "dry_register.json"); open(ef, "w").write('{"member' + 'Id": "VMYH' + '12345678", "first' + 'Name": "Ann"}')
it = approval_submit.build_items([{"letter": "C", "command": "python3 y.py --live --only C", "reason": "r", "what": "VANTABLE, " + "OTTO (chart 12232248) six visits",
                                   "dollars": "$1", "ui": "", "evidence": "dry run: 6 visits to UNI20", "evidence_file": ef}], "2026-10-06T0430Z", TMP)
check("evidence file is referenced by path, never copied", it[0]["evidence"] == "dry run: 6 visits to UNI20" and "VMYH" not in json.dumps(it), it[0]["evidence"])
reg = os.path.join(TMP, "reg", "approvals_pending.json")
approval_submit.register(reg, it, False, scrub=True)
check("repo copy of the register carries no chart name", "VANTABLE" not in open(reg).read() and "[name] (chart 12232248)" in open(reg).read())
clash = [dict(it[0], cmd="python3 other.py --live")]
check("same id with a different command = collision", approval_submit.collisions(reg, clash) == [it[0]["id"]] and approval_submit.collisions(reg, it) == [])
subj, body = approval_submit.email(items, "2026-10-06T0330Z", "nightly cascade")
check("subject is found by the hourly sync's search and names the run kind", subj.startswith("mandatory approval writes - 2 new to approve (nightly cascade"), subj)
check("no email-reply approval channel is offered", "APPROVED <id>" not in body and "APPROVED &lt;id&gt;" not in approval_submit.html_email(items, "x", subj), body[:200])

check("gate catches a member number inside an add_ins command", approval_submit.privacy_hit("cd /home/claude/unbilled && python3 add_ins.py 17477638 car6404 912345678") is not None)
check("repo copy also scrubs AMD's no-space LAST,FIRST form and the command", approval_submit.repo_safe("XANTHER," + "OTTO pat17477638 via x.py --only A") == "[name] pat17477638 via x.py --only A")

# ------------------------------------------------------------------ H. (11/11/2026, round 8) the echo guard: no save when the visit's charges could not all be read
# Sections B-D put a stand-in in the place of resave.visit_charges; here the REAL one runs (and the real resave.detail) on an invented chart
# history. gettxhistory answers pages of 100 charge rows, newest first: `before` rows of ANOTHER visit of the chart, this visit's charges (a
# void one keeps its row, void="1"), one row of this visit with a negative fee (a reversal - never a live charge), then `after` more rows of
# the other visit. Every good page carries the empty <Error /> that every good AdvancedMD answer carries, and a memo with the letters "Fault".
#   fault_pages = the pages answered with a Fault on every read; fault_calls = the history CALLS of the scenario (the first is 1) answered
#   with one; nodetail = charges whose OWN detail answer does not hold them. The charge details, the save, the admission-date write and the
#   frequency reset are answered by section B's stand-in (r_post). HCALLS = every call of the scenario in the order it came; HBOD = the
#   bodies, word for word (hsum = their fingerprint).
import hashlib
HIST = {}; HCALLS = []; HBOD = []; HREB = []
def hreal(**h):      # a new scenario: its knobs, and nothing counted yet
    HIST.clear(); HIST.update(before=0, after=0, fault_pages=(), fault_calls=(), nodetail=(), words="Server Error", asked=0); HIST.update(h); del HCALLS[:]; del HBOD[:]; del HREB[:]
def h_rows():
    other = ['<charge id="%d" visit="555" void="0" fee="50.00" memo="Faulty meter - Default plan"/>' % (700000 + k) for k in range(HIST["before"] + HIST["after"])]
    mine = ['<charge id="%s" visit="900" void="%d" fee="100.00"/>' % (c[6:], c in STATE["void"]) for c in cids()] + ['<charge id="499" visit="900" void="0" fee="-100.00"/>']
    return other[:HIST["before"]] + mine + other[HIST["before"]:]
def h_post(body, timeout=180):
    m = re.match(r'<ppmdmsg action="([^"]*)"', body); act = m.group(1) if m else "?"; HBOD.append(body)
    if act == "gettxhistory":
        page = int(re.search(r' pagenumber="(\d+)"', body).group(1)); HIST["asked"] += 1; HCALLS.append("history %d" % page)
        if page in HIST["fault_pages"] or HIST["asked"] in HIST["fault_calls"]:
            return "<PPMDResults><Error><Fault><detail><code>500</code><description>%s</description></detail></Fault></Error></PPMDResults>" % HIST["words"]
        return '<PPMDResults><Results><patient id="pat77"><chargelist>%s</chargelist></patient></Results><Error /></PPMDResults>' % "".join(h_rows()[(page - 1) * 100:page * 100])
    if act == "getchargedetaildataicd10":
        cid = re.search(r' chargeid="(\d+)"', body).group(1); HCALLS.append("detail " + cid)
        if "charge" + cid in HIST["nodetail"]: return "<PPMDResults><Fault>charge not found</Fault></PPMDResults>"      # the other shape of a Fault: not under <Error>
        return r_post(body, timeout)
    if act == "updvisitwithcharges": HCALLS.append("save %s insorder=%s" % (",".join(re.findall(r'<charge id="(charge\d+)"', body)) or "NO CHARGE", (re.search(r'<visit [^>]*insorder="([^"]*)"', body) or [None, "?"])[1]))
    elif act == "updextrainsinfo": HCALLS.append("%s %s" % ("reset" if "resubmissioncode" in body else "admit", (re.search(r'txtChargeCode="([^"]*)"', body) or [None, "?"])[1]))
    else: HCALLS.append(act)
    return r_post(body, timeout)
def h_rebill(cid, seq, **k): HREB.append((cid, seq)); HCALLS.append("rebill %s %s" % (cid, seq)); HBOD.append("rebill %s %s %s" % (cid, seq, sorted(k.items()))); return 204, ""
def hsum(): return hashlib.sha256("\n".join(HBOD).encode()).hexdigest()[:16]
def hnote(): return getattr(resave, "READ_NOTE", "(this resave.py keeps no READ_NOTE)")
def hvc(cid="500"):      # the real visit_charges: (visit id, chart id, the ids of the live charges it returns) - or, in words, what it raised
    try: v, p, cs = resave.visit_charges(cid); return v.get("id"), p.get("id"), [c.get("id") for c in cs]
    except Exception as e: return "RAISED %s: %s" % (type(e).__name__, e)
def hdo(f, *a):      # another helper over the real read - a raise becomes an answer the check shows
    try: return f(*a)
    except Exception as e: return "RAISED %s: %s" % (type(e).__name__, e)
_keep = (amd.post, amd.rebill_charge, amd._msgtime, resave.visit_charges, resave.detail, freq1_visit.run, time.sleep)
amd.post = h_post; amd.rebill_charge = h_rebill; amd._msgtime = lambda: "T"; resave.visit_charges = REAL_VISIT_CHARGES; resave.detail = REAL_DETAIL; freq1_visit.run = f_run; time.sleep = lambda *a: None
NOTHING = "visit vst900: nothing sent - "; VOIDS = "A full-visit save that leaves a live charge out voids that charge: read the visit again before anything is sent"
READ1 = ["detail 500", "history 1"]; READ2 = ["detail 500", "history 1", "history 2", "detail 500"]      # the calls of ONE read of the visit: a Fault on page 1; 99 other rows first and a Fault on page 2
# a good read: the answer is what it always was, and there is nothing to note
fresh(order="1", n=4, void={"charge503"}); hreal(before=3, after=2); got = hvc("501")
check("H the REAL visit_charges on a good read - three live charges among another visit's rows, a void charge and a reversal; the page carries the empty <Error /> of a good answer and memos with the letters 'Fault': the visit, the chart and exactly the three live charges, each from its own detail - the answer and the calls of before round 8",
      got == ("vst900", "pat77", ["charge500", "charge501", "charge502"]) and HCALLS == ["detail 501", "history 1", "detail 500", "detail 501", "detail 502"] and hsum() == "b186023af5f12b43", (got, HCALLS, hsum()))
check("H ... and READ_NOTE stays empty: there is nothing to say about a good read (the letters 'Fault' in a memo and the empty <Error /> are not a fault)", hnote() == "", hnote())
fresh(order="1", n=4, void={"charge503"}); hreal(before=3, after=2); ok, msg = setord("501", "2")
check("H set_insorder over the real history read, a good read: saved once, the three live charges echoed and read back - ok",
      ok is True and sent() == ["save"] and re.findall(r'<charge id="(charge\d+)"', STATE["posts"][0]) == ["charge500", "charge501", "charge502"] and "3 live charges (was 3)" in msg and hnote() == "", (msg, HCALLS))
# a. a history page answered with a Fault - the first page
LONG = "The transaction history of this chart could not be read at this time. " * 3      # 213 characters: the note keeps the first 120 of the fault's words
fresh(order="1"); hreal(fault_pages={1}, words=LONG); got = hvc()
check("H a Fault on the FIRST history page: the answer is what it was before round 8 - the visit, the chart and NO charge (the failed page is taken for 'no more charges') after ONE history call, and nothing is raised",
      got == ("vst900", "pat77", []) and HCALLS == READ1 and hsum() == "9ac1587ee9a113dc", (got, HCALLS, hsum()))
_n = hnote(); _fw = " ".join(("500 " + LONG).split())[:120]
check("H ... and READ_NOTE says why the charges may not all have been read: the call and the page first (gettxhistory page 1), the visit and the chart, and the first 120 characters of the fault's own words last",
      _n.startswith("gettxhistory page 1 for visit vst900 of chart pat77 answered a Fault") and _n.endswith(": " + _fw) and len(_fw) == 120 and LONG.strip() not in _n, _n)
fresh(order="1"); hreal(fault_pages={1}); ok, msg = setord("500", "2")
check("H set_insorder, a Fault on the first history page: NOT ok, 'visit vst900: nothing sent - ...' - it says AdvancedMD did not return all the charges, that a save which leaves a live charge out voids it, to read the visit again, the fault's words last - and NOTHING went out: no save, no further read (before round 8: a save with an EMPTY charge list, answered ok, '0 live charges (was 0)')",
      ok is False and msg.startswith(NOTHING + "AdvancedMD did not return all of this visit's charges (0 live charge(s) read). " + VOIDS) and msg.endswith("answered a Fault, so the chart's charges were not all listed: 500 Server Error")
      and not msg.startswith("resave") and not sent() and HCALLS == READ1 and not STATE["void"], (msg, HCALLS))
fresh(order="1"); hreal(fault_pages={1}); ok, msg = setord("500", "2", dry=True)
check("H ... the same for a DRY run: NOT ok, 'nothing sent' - never 'DRY resave ... (0 live charges echoed)'", ok is False and msg.startswith(NOTHING) and "DRY" not in msg and not sent() and HCALLS == READ1, (msg, HCALLS))
billed(order="1"); hreal(fault_pages={1}); r = route("900", "500", "2")
check("H ... and through freq1_visit.reroute on an already-billed visit (the real frequency reset and rebill stand behind it): 'NOT rebilled - visit order step failed: visit vst900: nothing sent - ...' - no save, no frequency reset, no rebill (before round 8: the empty save, then the rebill)",
      r.startswith("NOT rebilled - visit order step failed: " + NOTHING) and not sent() and not HREB and HCALLS == READ1, (r, HCALLS))
_ft = getattr(resave, "_fault_text", lambda root: "(this resave.py has no _fault_text)"); _x = ET.fromstring
_shapes = ("<r><Error><Fault><detail>Server   Error</detail></Fault></Error></r>", "<r><Fault>charge not found</Fault></r>", "<Fault>down</Fault>", '<r xmlns:s="urn:x"><s:Fault>soap fault</s:Fault></r>', "<r><Fault/></r>",
           '<r><Results><charge memo="Fault line"/><facility label="Default - Faulty meter">No Fault found</facility></Results><Error /></r>', "<r><Error /></r>")
check("H the Fault test looks for an ELEMENT named Fault anywhere in the answer - under <Error>, at the top, as the answer itself, with a namespace - and never for the letters: a memo, a label or a text that holds 'Fault', and the empty <Error /> of a good answer, are no fault",
      [_ft(_x(a_)) for a_ in _shapes] == ["Server Error", "charge not found", "down", "soap fault", "no words in it", None, None], [_ft(_x(a_)) for a_ in _shapes])
# a. the SECOND page of a two-page history: the asked charge is read, its siblings are not - only the note can tell
fresh(order="1", n=3); hreal(before=99, fault_pages={2}); got = hvc()
check("H a Fault on the SECOND page of a two-page history (charge500 is the last row of page 1, its two siblings are on page 2): the answer of before round 8 - charge500 ALONE, the siblings missing without a word",
      got == ("vst900", "pat77", ["charge500"]) and HCALLS == READ2 and hsum() == "e0bf5e78192bcfda", (got, HCALLS, hsum()))
check("H ... and READ_NOTE names page 2", hnote().startswith("gettxhistory page 2 for visit vst900 of chart pat77 answered a Fault") and hnote().endswith(": 500 Server Error"), hnote())
fresh(order="1", n=3); hreal(before=99, fault_pages={2}); ok, msg = setord("500", "2")
check("H set_insorder, the Fault on page 2: the asked charge WAS read and the list is not empty - only the note tells - NOT ok, nothing sent, nothing more read, and the two siblings stay live (before round 8 the save left them out, and AdvancedMD voids a charge left out)",
      ok is False and msg.startswith(NOTHING + "AdvancedMD did not return all of this visit's charges (1 live charge(s) read). " + VOIDS + " (insorder 1, list [1], asked 2) - gettxhistory page 2 ") and not sent() and not STATE["void"] and HCALLS == READ2, (msg, HCALLS))
fresh(order="1", n=3); hreal(before=99, fault_pages={2}); ok, msg = setord("500", "2", dry=True)
check("H ... the same for a DRY run", ok is False and msg.startswith(NOTHING) and "DRY" not in msg and not sent() and HCALLS == READ2, (msg, HCALLS))
billed(order="1", n=3); hreal(before=99, fault_pages={2}); r = route("900", "500", "2")
check("H ... and through freq1_visit.reroute: 'NOT rebilled', no save, no frequency reset, no rebill", r.startswith("NOT rebilled - visit order step failed: " + NOTHING) and not sent() and not HREB and HCALLS == READ2, (r, HCALLS))
fresh(order="1", n=3, bill={"charge500": BILLED}); hreal(before=99, fault_pages={2}); ok, msg = setord("500", "2")
check("H the guard comes BEFORE the billed guard: a billed visit whose charges were not all read answers 'nothing sent', not 'already billed - not saved' (bill signs read from an incomplete list prove nothing)",
      ok is False and msg.startswith(NOTHING) and "already billed" not in msg and not sent() and HCALLS == READ2, (msg, HCALLS))
# b. the page cap: page 7 still full
fresh(order="1"); hreal(before=700); got = hvc()
check("H the page cap - 700 newer charge rows of another visit come before this visit's: the answer of before round 8 (NO charge, after seven full pages)",
      got == ("vst900", "pat77", []) and HCALLS == ["detail 500"] + ["history %d" % p_ for p_ in range(1, 8)] and hsum() == "915025a49320f905", (got, HCALLS, hsum()))
check("H ... and READ_NOTE says page 7 was still full: the history is longer than the 700 charge rows read", hnote().startswith("gettxhistory page 7 for visit vst900 of chart pat77 was still full") and "longer than the 700 charge rows" in hnote(), hnote())
fresh(order="1"); hreal(before=697); ok, msg = setord("500", "2")      # 697 other rows + this visit's two charges + its reversal row = exactly 700 rows: both charges are read, on a page 7 that is full
check("H set_insorder at the cap - exactly 700 rows, both charges of the visit read on page 7: the page is full, so more rows may follow - NOT ok, nothing sent (only the note tells)",
      ok is False and msg.startswith(NOTHING + "AdvancedMD did not return all of this visit's charges (2 live charge(s) read). ") and "gettxhistory page 7 for visit vst900 of chart pat77 was still full" in msg and not sent() and not STATE["void"], (msg, HCALLS[-3:]))
fresh(order="1"); hreal(before=696); ok, msg = setord("500", "2")      # one row fewer: page 7 is not full - the whole history was read
check("H ... one row fewer (699 rows, page 7 not full): the whole history was read - saved as before, ok, no note", ok is True and sent() == ["save"] and "2 live charges (was 2)" in msg and hnote() == "", (msg, hnote()))
# c. a live charge that is not in its own detail answer
fresh(order="1"); hreal(nodetail={"charge501"}); got = hvc()
check("H a charge the history lists as live whose OWN detail answer does not hold it (a Fault, not under <Error>): the answer of before round 8 - that charge is left out without a word",
      got == ("vst900", "pat77", ["charge500"]) and HCALLS == ["detail 500", "history 1", "detail 500", "detail 501"] and hsum() == "2b0e0327d21f885c", (got, HCALLS, hsum()))
check("H ... and READ_NOTE names the call and the charge, the fault's words last", hnote() == "getchargedetaildataicd10 of charge 501 for visit vst900 of chart pat77 did not return that charge, which the history lists as live: charge not found", hnote())
fresh(order="1"); hreal(nodetail={"charge501"}); ok, msg = setord("500", "2")
check("H set_insorder, a live charge missing from its own detail answer: NOT ok, nothing sent - charge501 stays live (before round 8 it was left out of the save)",
      ok is False and msg.startswith(NOTHING + "AdvancedMD did not return all of this visit's charges (1 live charge(s) read). ") and "getchargedetaildataicd10 of charge 501" in msg and not sent() and not STATE["void"], (msg, HCALLS))
fresh(order="1", n=3); hreal(before=98, fault_pages={2}, nodetail={"charge501"}); got = hvc()      # two reasons in one read: page 2 fails (noted first), then charge501 - read on page 1 - is missing from its own detail
check("H two reasons in one read: the note keeps the FIRST one (the failed page), and the answer is still what it was before round 8", got == ("vst900", "pat77", ["charge500"]) and hnote().startswith("gettxhistory page 2 for visit vst900 of chart pat77 answered a Fault"), (got, hnote()))
# no live charge read, and the asked charge not among the live charges read - a complete read, no note: the list itself tells
fresh(order="1", void={"charge500", "charge501"}); hreal(); got = hvc(); _n = hnote(); hreal(); ok, msg = setord("500", "2")
check("H every charge of the visit is void (a complete read: no note): NOT ok, 'nothing sent - no live charge of this visit was read' - no save with an EMPTY charge list (before round 8 that save went out and was answered ok)",
      got == ("vst900", "pat77", []) and _n == "" and ok is False and msg.startswith(NOTHING + "no live charge of this visit was read (0 read). " + VOIDS) and not sent() and HCALLS == READ1, (got, _n, msg, HCALLS))
fresh(order="1", n=3, void={"charge500"}); hreal(); ok, msg = setord("500", "2")
check("H the charge asked for is void while its two siblings are live (a complete read: no note): NOT ok, 'nothing sent - charge 500, the one asked for, is not among the 2 live charge(s) read' (move_to_ins.move's own guard, now here too)",
      ok is False and msg.startswith(NOTHING + "charge 500, the one asked for, is not among the 2 live charge(s) read (501,502). " + VOIDS) and not sent() and hnote() == "", (msg, HCALLS))
# the skip answer is unchanged - chosen: a visit already right is "skipped", note or no note (it is decided from the asked charge's own detail, and nothing is sent on that path)
fresh(order="2"); hreal(fault_pages={1}); ok, msg = setord("500", "2")
check("H the skip is unchanged: a visit ALREADY as asked (attribute and list) is still 'skipped' when the history could not be read - ok, the words of before round 8, nothing sent",
      ok is True and msg == "visit vst900 insorder already 2, list [2] - resave skipped" and not sent() and HCALLS == READ1, (msg, HCALLS))
# after the save: a read-back that could not read all the charges is not trusted
fresh(order="1"); hreal(fault_calls={2}); ok, msg = setord("500", "2")      # the first read is good, the save lands, the read-back's history page fails, the read after it is good
check("H the READ-BACK after the save cannot read all the visit's charges: it is not trusted - NOT ok through 'read again', with what the visit reads now",
      ok is False and sent() == ["save"] and msg.startswith("resave vst900: the read-back after the save could not read all the visit's charges (gettxhistory page 1 for visit vst900 of chart pat77 answered a Fault")
      and " - read again: insorder 2, list [1] -> [2], 2 live charges (was 2)" in msg and msg.endswith(" - NOT as asked") and HIST["asked"] == 3, (msg, HCALLS))
fresh(order="1"); hreal(fault_calls={2, 3}); ok, msg = setord("500", "2")
check("H ... and when the read after it is not complete either: 'the visit could not be read again ... look at it in AdvancedMD before anything else is sent' - the last answer of a read-back that fails",
      ok is False and sent() == ["save"] and ", and the visit could not be read again (not all of its charges came back: gettxhistory page 1 " in msg and msg.endswith(" - look at it in AdvancedMD before anything else is sent - NOT as asked") and HIST["asked"] == 3, (msg, HCALLS))
fresh(order="1", **HOSP(), wipe=True); hreal(fault_calls={2}); ok, msg = setord("500", "2,1")
check("H ... a hospital code's admission date the save wiped is still written back on that 'read again' path", ok is False and STATE["admit"] == {"99223": ADM} and len(STATE["admits"]) == 1 and "written back (99223)" in msg and "NOT as asked" in msg, (msg, STATE["log"]))
# the note never goes stale, and a stand-in that never touches it keeps working
fresh(order="1"); hreal(fault_pages={1}); hvc(); _n1 = hnote(); HIST["fault_pages"] = (); got = hvc()
check("H the note is set anew by every call of visit_charges: a failed read followed by a good one leaves no stale note", _n1 != "" and got == ("vst900", "pat77", ["charge500", "charge501"]) and hnote() == "", (_n1, got, hnote()))
fresh(order="1"); hreal(fault_pages={1}); hvc(); _n1 = hnote()      # a failed REAL read leaves its note ...
resave.visit_charges = live_charges; ok, msg = setord("500", "2"); resave.visit_charges = REAL_VISIT_CHARGES      # ... then a stand-in that never touches the note (sections B-D's own) takes the real one's place
check("H a stand-in for visit_charges that never touches the note keeps working: set_insorder sets the note to '' itself before it reads - saved, ok (a stale note would have refused it)", _n1 != "" and ok is True and sent() == ["save"], (msg, _n1))
# move_to_ins.move and freq1_visit.run do not look at the note - a known, older gap that round 8 leaves as it was. On a good read and on a failed
# one they make the very calls, word for word, that they made before this round: each fingerprint below was taken from the helpers of the live
# branch as it stood before round 8 (this same file, the same answers), and the helpers of this tree give the same.
fresh(order="1"); hreal(); _m = hdo(move_to_ins.move, "500", "2")
check("H UNCHANGED in round 8 - move_to_ins.move on a good read: both charges echoed in ONE save, read back, ONE rebill - the calls of before this round, word for word",
      _m == "moved 0.00 -> {'insbalance': '100.00', 'insorder': '2'} rebill seq 2 (sent to 2) -> 204" and HCALLS == ["detail 500", "history 1", "detail 500", "detail 501", "save charge500,charge501 insorder=2", "detail 500", "rebill 500 2"] and hsum() == "da5df0b7128ee6d7", (_m, HCALLS, hsum()))
fresh(order="1"); hreal(fault_pages={1}); _m = hdo(move_to_ins.move, "500", "2")
check("H UNCHANGED in round 8 - move_to_ins.move, a Fault on the first history page: its own guard answers 'charge not live on visit' - two calls, nothing sent, nothing raised",
      _m == "charge not live on visit" and HCALLS == READ1 and hsum() == "9ac1587ee9a113dc" and not sent(), (_m, HCALLS, hsum()))
fresh(order="1"); hreal(before=99, fault_pages={2}); _m = hdo(move_to_ins.move, "500", "2")
check("H UNCHANGED in round 8 (the known, older gap - NOT closed here) - move_to_ins.move, a Fault on page 2: it still saves the ONE charge it read (the stand-in voids the sibling left out) and rebills - the calls of before this round, word for word",
      _m == "moved 0.00 -> {'insbalance': '100.00', 'insorder': '2'} rebill seq 2 (sent to 2) -> 204" and HCALLS == READ2 + ["save charge500 insorder=2", "detail 500", "rebill 500 2"] and hsum() == "fcf0dbcf40e717f3" and STATE["void"] == {"charge501"}, (_m, HCALLS, hsum()))
fresh(order="1", cpt={"charge501": "99223"}); hreal(); _f = hdo(f_run, "900", "500", 2)
check("H UNCHANGED in round 8 - freq1_visit.run on a good read: a frequency reset for each of the visit's two procedures, then ONE rebill - the calls of before this round, word for word",
      _f == "freq1 + rebill seq 2 -> 204" and HCALLS == ["detail 500", "history 1", "detail 500", "detail 501", "reset pcode1", "reset pcode2", "rebill 500 2"] and hsum() == "02b425450e5f457b", (_f, HCALLS, hsum()))
fresh(order="1", cpt={"charge501": "99223"}); hreal(fault_pages={1}); _f = hdo(f_run, "900", "500", 2)
check("H UNCHANGED in round 8 (the known, older gap - NOT closed here) - freq1_visit.run, a Fault on the first history page: NO frequency reset, and the rebill still goes out - the calls of before this round, word for word",
      _f == "freq1 + rebill seq 2 -> 204" and HCALLS == READ1 + ["rebill 500 2"] and hsum() == "2af86ab9d0f80f57", (_f, HCALLS, hsum()))
fresh(order="1", cpt={"charge501": "99223"}); hreal(before=99, fault_pages={2}); _f = hdo(f_run, "900", "500", 2)
check("H UNCHANGED in round 8 (the known, older gap - NOT closed here) - freq1_visit.run, a Fault on page 2: the frequency reset goes out for the ONE procedure it read, then the rebill - the calls of before this round, word for word",
      _f == "freq1 + rebill seq 2 -> 204" and HCALLS == READ2 + ["reset pcode1", "rebill 500 2"] and hsum() == "85f36e10b6d90cbf", (_f, HCALLS, hsum()))
check("H the stand-in AdvancedMD of section H had an answer for every call the helpers made (no action it does not know)", not UNANSWERED, UNANSWERED)
amd.post, amd.rebill_charge, amd._msgtime, resave.visit_charges, resave.detail, freq1_visit.run, time.sleep = _keep

print("\n%d failure(s)" % len(FAILS) + (": " + ", ".join(FAILS) if FAILS else " - all guarantees hold"))
sys.exit(1 if FAILS else 0)
