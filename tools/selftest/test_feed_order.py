#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of round 7, 11/10/2026: no feed visit is left without an insurance order)
# Decides: nothing. Proves, with stand-ins for AdvancedMD and the look-up vendor (no AMD, no network, no patient data - every id here is
#   invented), what the specification's sections 3-6 say:
#     - fast_set_insorder (claimocity_verify.py) and resave.set_insorder read the visit's insurance-order LIST: a visit entered with no plan
#       reads insorder "1" over an EMPTY list - once the plan exists the save IS sent and the list is read back; a visit whose list already
#       equals the order is not saved; a billed visit is never saved; every live charge is echoed (a sibling the register does not list is not
#       voided); a void no-charge quality line never holds the visit; an admission date the save wiped is written back with the import's own
#       call and read again, and when that fails the visit is not confirmed;
#     - the insurance check's loop holds - never releases - such a visit in words that say what its list shows, keeps today's skip of charts the
#       same batch already released, trusts only this version's entries, logs the whole answer, says every hold is a label in the report only;
#       a plan only the paid look-up found is added only when it is a medical plan shown active on every date of service, and nothing is bought
#       when every free check of the chart errored;
#     - the digest puts the visits with no insurance order at the TOP and counts only saves that were sent;
#     - (sections 8 and 9, step 2) feed_order_sweep.py, run INSIDE this process with stand-ins: the read-only listing (TOP lines with the clinician
#       and admission-date problems), the eligibility checks dated to the service date (one per chart, date and plan; capped; no name, birth date
#       or member id written), the clinician moves of the owner's file, the save through set_insorder only for the approved and standing-word
#       visits whose checks all pass, the pilot first, the stop at the first unexpected read-back; the version 2026-11-25.3, the mirror's markers,
#       the owner's approved file unchanged, and the words of the runbook, the rulebook, the lessons and the captured calls.
#   The import's new register fields (section 7) are proved in tools/selftest/test_pos_rule.py, where the import runs with its stand-ins.
#   11/11/2026 (round 8, the echo guard) - section R8: the sweep's own read before its own save (--resave) and its own clinician move
#   (--fix-clinician) - here the REAL resave.visit_charges, lifted out of resave.py's text, over a stand-in transaction history - meeting a
#   failed history page, an empty read and a listed charge that did not come back: nothing is sent for that visit, the run ends DID NOT FINISH
#   as on an error at that read, no row is marked sent and no STOP is left; the order save's own refusal ("visit <id>: nothing sent - ...")
#   is never taken for a save; the insurance check's own save makes the very calls it made before (it does not look at the note yet); the
#   mirror's markers, the rulebook line and the lesson line of that day.
# Run: python3 tools/selftest/test_feed_order.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, io, re, ast, contextlib, time, glob
import xml.etree.ElementTree as ET
# THIS SELF-TEST NEVER REACHES ADVANCEDMD OR ANY OTHER HOST. Every network route is closed here, first: scripts/helpers holds the real amd /
# resave / txh / void_tx modules. Helpers that talk to AdvancedMD are only ever run INSIDE this process with stand-in modules (run_inside), or
# their functions are lifted out of the source text; no helper is started as a program, and no real module is imported.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
AMD_MODULES = ("amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update", "stedi", "elig_amd", "add_ins")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPERS = os.path.join(ROOT, "scripts", "helpers")
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:900]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
_sleep0 = time.sleep; time.sleep = lambda *_a: None      # the helpers wait between calls; nothing to wait for here
HELD = "HELD in this report only - AdvancedMD will still bill this visit to its insurance order at the next claim run unless someone stops it"

# ---- a stand-in AdvancedMD: visits with charges, the insorder attribute, the insurance-order LIST and the admission date --------------------
class SV:
    """One visit as AdvancedMD keeps it. A save (updvisitwithcharges) behaves as the practice's notes say: a charge left out of the echo is voided
    (resave.visit_charges, 9/3/2026); the list is built from the order only when the chart has a plan (builds); wipe = the save wipes the
    admission date (captured_calls 9/22); restore = updextrainsinfo writes it back; fault = 'always' or a charge id whose echo is refused."""
    def __init__(self, vid, charges, attr="1", lst="", admit="", builds=True, wipe=False, restore=True, fault=None, void_after=(), rev=False, raise_after=None):
        self.vid, self.attr, self.lst, self.admit, self.builds, self.wipe, self.restore, self.fault, self.void_after, self.rev = vid, attr, lst, admit, builds, wipe, restore, fault, set(void_after), rev
        self.raise_after = raise_after
        self.ch = {c["id"]: dict(c) for c in charges}; self.saves = []; self.extins = []
    def adm(self, cid):      # admit = one date for the visit, or {CPT: date} = AdvancedMD keeping the date per procedure code (each charge's detail shows its own code's)
        return (self.admit.get(self.ch[cid].get("cpt", "99309")) or "") if isinstance(self.admit, dict) else self.admit
    def detail(self, cid):
        c = self.ch[cid]; seqs = [s for s in self.lst.split(",") if s]
        rows = ['<insuranceorder carrier="car1" sequence="%s" ordinal="%d"/>' % (s, i) for i, s in enumerate(seqs)]
        if self.rev: rows = rows[::-1]      # AdvancedMD can list the entries out of claim order: the ordinal decides
        attrs = dict({"id": cid, "proccode": c.get("pcode", "pcode1"), "fee": c.get("fee", "141.00"), "void": "1" if c.get("void") else "0", "billins": "1", "insbilled": "0", "datebilled": ""}, **c.get("attrs", {}))
        pays = "".join('<payment amount="%s" void="%s"/>' % (p["amount"], p.get("void", "0")) for p in c.get("pays", []))
        kids = ("<paymentlist>%s</paymentlist>" % pays if pays else "") + ("<insbilllist><insbill billeddate=\"x\"/></insbilllist>" if c.get("insbill") else "")
        return ('<r><patient id="pat1"/><visit id="%s" episode="e1" insorder="%s" profile="prof13">%s<insuranceorderlist>%s</insuranceorderlist></visit>'
                '<charge %s>%s</charge><proccodelist><proccode id="%s" code="%s"/></proccodelist></r>') % (
            self.vid, self.attr, '<extins hospitalizationfrom="%s"/>' % self.adm(cid) if self.adm(cid) else "", "".join(rows),
            " ".join('%s="%s"' % kv for kv in attrs.items()), kids, c.get("pcode", "pcode1"), c.get("cpt", "99309"))
    def live(self): return [k for k, c in self.ch.items() if not c.get("void")]
    def post(self, body):
        if "updextrainsinfo" in body:
            self.extins.append(body); m = re.search(r'hospitalizationfrom="([^"]*)"', body); k_ = re.search(r'txtChargeCode="([^"]*)"', body)
            if self.restore and m:
                if isinstance(self.admit, dict): self.admit[k_.group(1) if k_ else "?"] = m.group(1)
                else: self.admit = m.group(1)
                return '<r><extins hospitalizationfrom="%s"/></r>' % m.group(1)
            return "<r/>"
        self.saves.append(body)
        if self.fault == "always" or (self.fault and 'id="%s"' % self.fault in body): return "<r><Fault><description>Charge amount is zero</description></Fault></r>"
        sent = set(re.findall(r'<charge id="(charge\d+)"', body))
        for k in self.ch:
            if k not in sent or k in self.void_after: self.ch[k]["void"] = True
        self.attr = re.search(r'<visit [^>]*insorder="([^"]*)"', body).group(1)
        if self.builds: self.lst = self.attr
        if self.wipe: self.admit = {k_: "" for k_ in self.admit} if isinstance(self.admit, dict) else ""
        if self.raise_after: raise self.raise_after      # the save landed, but its answer never comes back (a time-out)
        return "<r/>"
class World:
    def __init__(self, *visits): self.v = {}; self.posts = []; [self.put(x) for x in visits]
    def put(self, sv): self.v[sv.vid] = sv; return sv
    def owner(self, cid):
        cid = "charge" + re.sub(r"\D", "", str(cid)); return next((x for x in self.v.values() if cid in x.ch), None), cid
    def detail(self, cid):
        sv, cid = self.owner(cid); return sv.detail(cid) if sv else "<r><Fault>charge not found</Fault></r>"
    def visit_charges(self, cid):
        sv, cid = self.owner(cid); r = ET.fromstring(sv.detail(cid))
        return r.find(".//visit"), r.find(".//patient"), [ET.fromstring(sv.detail(k)).find(".//charge") for k in sv.live()]
    def post(self, body, timeout=0):
        self.posts.append(body); m = re.search(r'visitid="(vst\d+)"', body) or re.search(r'<visit id="(vst\d+)"', body)
        return self.v[m.group(1)].post(body) if m and m.group(1) in self.v else "<r/>"
W = [World()]
AM = types.SimpleNamespace(msg=lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s" class="%s" %s>%s</ppmdmsg>' % (action, cls, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children),
                           post=lambda body, timeout=0: W[0].post(body, timeout), login_cached=lambda *a: None)
RS = types.SimpleNamespace(detail=lambda cid: W[0].detail(cid), visit_charges=lambda cid: W[0].visit_charges(cid),
                           CHG_FIELDS=["respparty", "begindate", "enddate", "diagcodes", "modcodes", "aging", "billins", "proccode", "cobcode", "pos", "tos", "units", "netfee", "fee", "allowed", "patportion", "insportion", "patbalance", "insbalance", "finclasscode", "lineitemnote"])
def chg(n, cpt="99309", pcode="pcode65119", fee="141.00", **kw): return dict({"id": "charge%s" % n, "cpt": cpt, "pcode": pcode, "fee": fee}, **kw)

# ---- the two helpers' functions, lifted out of their source text (the modules themselves are never imported) ------------------------------------
VSRC = open(os.path.join(HELPERS, "claimocity_verify.py")).read()
_vs = VSRC[VSRC.index("def fast_set_insorder(v, order, removed=None, info=None):"):VSRC.index("def main():")]
CARS = {"car6085": ["FLO02", "FLORIDA MEDICARE"], "car100": ["CIG09", "CIGNA"], "car300": ["UNI20", "UNITED HEALTHCARE"], "car400": ["TRI05", "TRICARE FOR LIFE"]}
VNS = {"resave": RS, "amd": AM, "re": re, "CARRIERS": CARS, "CODE2CAR": {v_[0]: k_ for k_, v_ in CARS.items()}}; exec(compile(_vs, "claimocity_verify.py", "exec"), VNS)
fast = VNS["fast_set_insorder"]
def lift(path, names):
    tree = ast.parse(open(path).read())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names) or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    return compile(ast.Module(body=keep, type_ignores=[]), path, "exec")
RNS = {"re": re, "ET": ET, "amd": AM, "detail": lambda cid: W[0].detail(cid), "visit_charges": lambda cid: W[0].visit_charges(cid)}
exec(lift(os.path.join(HELPERS, "resave.py"), {"CHG_FIELDS", "HOSP_CODES", "order_list", "billed_reasons", "admit_of", "admit_codes", "admit_back", "restore_admit", "set_insorder"}), RNS)      # core/resave.py must be the same file (next check)
setins = RNS["set_insorder"]
check("both copies of resave.py are the same file (scripts/helpers and core)", open(os.path.join(HELPERS, "resave.py")).read() == open(os.path.join(ROOT, "core", "resave.py")).read())
NEW = {"open_plans_at_entry": 0, "chart_insorder": ""}      # a row the round-7 import wrote (the chart had no plan when the visit was entered)
def row(vid, charges, **kw): return dict({"visit": vid, "pid": "pat1", "charges": charges, "dos": "11/02/2026", "cpts": ["99309"]}, **dict(NEW, **kw))

# ---- 3.1 order_list: plan sequences in ordinal order, joined like the attribute; the two copies agree ------------------------------------------
_shapes = ['<visit insorder="1"><insuranceorderlist/></visit>', '<visit insorder="1"/>', '<visit><insuranceorderlist><insuranceorder sequence="1" ordinal="0"/></insuranceorderlist></visit>',
           '<visit><insuranceorderlist><insuranceorder sequence="2" ordinal="1"/><insuranceorder sequence="4" ordinal="0"/></insuranceorderlist></visit>',
           '<visit><insuranceorderlist><insuranceorder sequence="1" ordinal="0"/><insuranceorder sequence="3" ordinal="1"/><insuranceorder sequence="2" ordinal="2"/></insuranceorderlist></visit>']
_want = ["", "", "1", "4,2", "1,3,2"]
check("3.1 order_list: empty list -> '', one plan -> '1', claim order by ordinal (XML 2/ordinal 1 then 4/ordinal 0 -> '4,2'), three plans", [VNS["order_list"](ET.fromstring(s_)) for s_ in _shapes] == _want, [VNS["order_list"](ET.fromstring(s_)) for s_ in _shapes])
check("3.1 order_list: the insurance check's copy and resave.py's copy give the same answer on every shape", [RNS["order_list"](ET.fromstring(s_)) for s_ in _shapes] == _want)
for _nm in ("billed_reasons", "admit_of"):
    _c = [ET.fromstring(x_) for x_ in ('<charge datebilled="10/28/2026 21:07:13"/>', '<charge insbilled="1"/>', '<charge><insbilllist><insbill/></insbilllist></charge>', '<charge><paymentlist><payment amount="0.00" void="0"/></paymentlist></charge>', '<charge><paymentlist><payment amount="60.74" void="1"/></paymentlist></charge>', '<charge datebilled="" insbilled="0"/>')]
    if _nm == "billed_reasons": check("3.3 billed: a bill date, an insurance bill (flag or row) or a payment that is not void (any amount) - and the two copies agree", [VNS[_nm]([c_]) for c_ in _c] == [["bill date"], ["insurance bill"], ["insurance bill"], ["payment"], [], []] == [RNS[_nm]([c_]) for c_ in _c], [VNS[_nm]([c_]) for c_ in _c])

# ---- 3.2 - 3.6 fast_set_insorder ------------------------------------------------------------------------------------------------------------
# (a) THE STUCK VISIT: entered with no plan, insorder "1", EMPTY list; the plan has landed at sequence 1 (order "1") -> the save IS sent, list read back
W[0] = World(SV("vst11", [chg(111)], attr="1", lst="")); inf = {}
ok, m = fast(row("vst11", ["charge111"]), "1", [], inf); sv = W[0].v["vst11"]
check("3.2/10 stuck visit (attribute 1 over an EMPTY list, plan added): the save IS sent once and the list is read back [1]", ok and len(sv.saves) == 1 and sv.lst == "1" and "list [] -> [1]" in m and inf.get("sent") and inf.get("accepted") and inf.get("list_now") == "1", (ok, m, inf))
# (b) the list already equals the order -> nothing sent
W[0] = World(SV("vst12", [chg(121)], attr="1", lst="1")); ok, m = fast(row("vst12", ["charge121"]), "1", [], {})
check("3.2/10 a visit whose list already equals the order: no save, ok, says 'nothing sent'", ok and W[0].v["vst12"].saves == [] and "nothing sent" in m, (ok, m))
# (b2) the attribute equals the order but the list holds another order -> sent (the attribute alone proves nothing)
W[0] = World(SV("vst13", [chg(131)], attr="1", lst="1,2")); ok, m = fast(row("vst13", ["charge131"]), "1", [], {})
check("3.2 attribute equal but list different (1,2) -> the save is sent and the list reads [1]", ok and len(W[0].v["vst13"].saves) == 1 and "list [1,2] -> [1]" in m, (ok, m))
# (c) a billed visit -> never saved, not ok, words; each kind of bill sign
for _lbl, _c in (("bill date", chg(141, attrs={"datebilled": "10/28/2026 21:07:13", "insbilled": "1"}, insbill=True)), ("insurance bill", chg(141, insbill=True)), ("payment", chg(141, pays=[{"amount": "60.74"}]))):
    W[0] = World(SV("vst14", [_c], attr="1", lst="1")); inf = {}; ok, m = fast(row("vst14", ["charge141"]), "1,2", [], inf)
    check("3.3/10 a billed visit (%s) is never saved: not ok, 'already billed - not saved', nothing posted" % _lbl, not ok and W[0].posts == [] and m.startswith("already billed - not saved") and _lbl in inf.get("billed", []), (ok, m, inf))
W[0] = World(SV("vst15", [chg(151, pays=[{"amount": "60.74", "void": "1"}])], attr="1", lst="")); ok, m = fast(row("vst15", ["charge151"]), "1", [], {})
check("3.3 a VOID payment is not a payment: the never-billed visit is saved", ok and len(W[0].v["vst15"].saves) == 1, (ok, m))
W[0] = World(SV("vst16", [chg(161, attrs={"datebilled": "10/28/2026"})], attr="1", lst="1")); ok, m = fast(row("vst16", ["charge161"]), "1", [], {})
check("3.3 a billed visit whose list already equals the order: nothing to do - ok, nothing sent (no false hold)", ok and W[0].posts == [] and "nothing sent" in m, (ok, m))
# (d) an extra live sibling the register does not list -> echoed, not voided (challenger case 1)
W[0] = World(SV("vst17", [chg(171), chg(172, cpt="99497", pcode="pcode65299", fee="86.00")], attr="1", lst="")); ok, m = fast(row("vst17", ["charge171"]), "1", [], {})
sv = W[0].v["vst17"]
check("3.4/10 an extra live sibling not in the register is echoed, not voided (both ids in the save, both still live)", ok and 'id="charge172"' in sv.saves[0] and 'id="charge171"' in sv.saves[0] and sv.live() == ["charge171", "charge172"] and "also echoed, not in the register: charge172" in m, (ok, m, sv.live()))
# (e) a void no-charge quality line (1123F / M0004) is exempt: not echoed, never holds the visit
for _code, _pc, _key in (("1123F", "pcode65441", "quality_charge"), ("M0004", "pcode692183", "mvp_charge")):
    W[0] = World(SV("vst18", [chg(181), chg(182, cpt=_code, pcode=_pc, fee="0.00", void=True)], attr="1", lst=""))
    r_ = row("vst18", ["charge181", "charge182"], **{_key: "charge182", ("quality_codes" if _key == "quality_charge" else "mvp_codes"): [_code]})
    ok, m = fast(r_, "1", [], {}); sv = W[0].v["vst18"]
    check("3.4/10 a VOID %s line is exempt: the visit is saved with its own charge only and confirmed" % _code, ok and len(sv.saves) == 1 and "charge182" not in sv.saves[0] and sv.lst == "1", (ok, m))
W[0] = World(SV("vst19", [chg(191), chg(192, void=True)], attr="1", lst="")); ok, m = fast(row("vst19", ["charge191", "charge192"]), "1", [], {})
check("3.4 a VOID charge of the visit's own (not a no-charge line) still holds as before: 'detail read mismatch', nothing sent", not ok and "mismatch" in m and W[0].posts == [], (ok, m))
# round 6 kept: the echo with a LIVE quality line refused -> sent once more without it, accepted, line void, removal reported
W[0] = World(SV("vst20", [chg(201), chg(202, cpt="1123F", pcode="pcode65441", fee="0.00")], attr="1", lst="", fault="charge202")); _rm = []
ok, m = fast(row("vst20", ["charge201", "charge202"], quality_charge="charge202", quality_codes=["1123F"], quality_fee="0.00"), "1", _rm, {})
check("3.4 (round 6 kept) a refused echo with the live quality line is sent once more without it: confirmed, the line void, the removal reported", ok and len(W[0].v["vst20"].saves) == 2 and "line is void" in m and len(_rm) == 1 and W[0].v["vst20"].lst == "1", (ok, m, _rm))
# (f) the save wipes the admission date -> written back with the import's own call (per hospital code) and read again
W[0] = World(SV("vst21", [chg(211, cpt="99223", pcode="pcode65101"), chg(212, cpt="99497", pcode="pcode65299")], attr="1", lst="", admit="10/27/2026", wipe=True))
inf = {}; ok, m = fast(row("vst21", ["charge211", "charge212"], cpts=["99223", "99497"]), "1", [], inf); sv = W[0].v["vst21"]
_shape = ('<extins txtChargeCode="99223" hospitalizationfrom="10/27/2026" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
          'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>')
check("3.5/10 an admission date wiped by the save is written back with the import's exact updextrainsinfo shape (per hospital code only) and read again: ok",
      ok and len(sv.extins) == 1 and _shape in sv.extins[0] and 'action="updextrainsinfo" class="chargeentry"' in sv.extins[0] and 'visitid="vst21"' in sv.extins[0] and sv.admit == "10/27/2026"
      and "admission date 10/27/2026 was lost on save and written back (99223)" in m and not inf.get("admit_lost"), (ok, m, sv.extins))
_frag = ("'<extins txtChargeCode=\"%s\" hospitalizationfrom=\"%s\" patsignature=\"1\" emergency=\"0\" epsdt=\"0\" payprov=\"1\" employment=\"0\" '",
         "'autoaccident=\"0\" otheraccident=\"0\" pregnant=\"0\" outsidelab=\"0\"/>'", 'amd.msg("updextrainsinfo", "chargeentry", {"visitid": ')
_srcs = {n_: open(os.path.join(HELPERS, n_)).read() for n_ in ("claimocity_import.py", "claimocity_verify.py", "resave.py")}
check("3.5 ... and that shape is the import's own: the same template and call in claimocity_import.py, claimocity_verify.py and resave.py", all(f_ in s_ for f_ in _frag for s_ in _srcs.values()), {n_: [f_ in s_ for f_ in _frag] for n_, s_ in _srcs.items()})
# (g) restoring fails -> not ok: "admission date lost on save" (the loop holds it)
W[0] = World(SV("vst22", [chg(221, cpt="99232", pcode="pcode65102")], attr="1", lst="", admit="10/27/2026", wipe=True, restore=False)); inf = {}
ok, m = fast(row("vst22", ["charge221"], cpts=["99232"]), "1", [], inf)
check("3.5/10 the write-back does not take: not ok, 'admission date lost on save', info.admit_lost", not ok and "admission date lost on save (was 10/27/2026, now none" in m and inf.get("admit_lost"), (ok, m))
W[0] = World(SV("vst23", [chg(231)], attr="1", lst="", admit="10/27/2026", wipe=True)); ok, m = fast(row("vst23", ["charge231"]), "1", [], {})
check("3.5 a wiped admission date on a visit with no hospital code cannot be written back: not ok, said", not ok and "no hospital code" in m and W[0].v["vst23"].extins == [], (ok, m))
W[0] = World(SV("vst24", [chg(241, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/27/2026")); ok, m = fast(row("vst24", ["charge241"], cpts=["99223"]), "1", [], {})
check("3.5 an admission date the save keeps: nothing is written", ok and W[0].v["vst24"].extins == [] and "admission" not in m, (ok, m))
# (h) AdvancedMD accepts the save but builds no list -> not ok (investigator case 2)
W[0] = World(SV("vst25", [chg(251)], attr="1", lst="", builds=False)); inf = {}; ok, m = fast(row("vst25", ["charge251"]), "1", [], inf)
check("3.6 the save is accepted but the list stays EMPTY: not ok, 'NOT AS ASKED', the list read back is ''", not ok and "NOT AS ASKED" in m and inf.get("list_now") == "" and inf.get("accepted"), (ok, m))
# (i) a real re-order 1,2 -> 1 (investigator case 4); (j) a sibling voided by the save (investigator case 5); (k) claim order 4,2 (case 6)
W[0] = World(SV("vst26", [chg(261)], attr="1,2", lst="1,2")); ok, m = fast(row("vst26", ["charge261"]), "1", [], {})
check("3.6 a real change 1,2 -> 1: sent once, 'list [1,2] -> [1]'", ok and len(W[0].v["vst26"].saves) == 1 and "list [1,2] -> [1]" in m, (ok, m))
W[0] = World(SV("vst27", [chg(271), chg(272)], attr="1", lst="", void_after={"charge272"})); ok, m = fast(row("vst27", ["charge271", "charge272"]), "1", [], {})
check("3.6 a sibling voided by the save is caught: not ok, 'no longer live: charge272'", not ok and "no longer live: charge272" in m and "1 of 2 echoed charges live" in m, (ok, m))
W[0] = World(SV("vst28", [chg(281)], attr="1", lst="", rev=True)); ok, m = fast(row("vst28", ["charge281"]), "4,2", [], {})
check("3.6 a two-plan order keeps its claim order (ordinal), not numeric order: [4,2]", ok and "-> [4,2]" in m, (ok, m))
# (l) a visit the import entered BEFORE this change (no open_plans_at_entry) with an EMPTY list is not saved here (spec 4.2: old stuck visits -> the sweep)
W[0] = World(SV("vst29", [chg(291)], attr="1", lst="")); inf = {}
ok, m = fast({"visit": "vst29", "pid": "pat1", "charges": ["charge291"], "dos": "10/20/2026", "cpts": ["99309"]}, "1", [], inf)
check("4.2 an old row (entered before 11/10/2026) with an EMPTY list is never saved by the insurance check - only by feed_order_sweep.py with the owner's file", not ok and W[0].posts == [] and inf.get("old_row") and "feed_order_sweep.py --resave" in m, (ok, m))
W[0] = World(SV("vst30", [chg(301)], attr="2", lst="2")); ok, m = fast({"visit": "vst30", "pid": "pat1", "charges": ["charge301"], "dos": "10/20/2026", "cpts": ["99309"]}, "1", [], {})
check("4.2 ... an old row whose list is NOT empty is set as before (it would bill to its old order otherwise)", ok and len(W[0].v["vst30"].saves) == 1, (ok, m))
# the challenger's four hazards (c8_test_proposed.py), on the built function: none of them happens now
W[0] = World(SV("vst31", [chg(311), chg(312)], attr="1", lst="", admit="10/21/2026", wipe=True)); ok, m = fast(row("vst31", ["charge311"]), "1", [], {})
check("challenger c8 (1)+(2): an extra live charge is not voided, and a wiped admission date is never answered 'ok'", W[0].v["vst31"].live() == ["charge311", "charge312"] and not (ok and W[0].v["vst31"].admit == ""), (ok, m))
W[0] = World(SV("vst32", [chg(321), chg(329, cpt="1123F", pcode="pcode65441", fee="0.00", void=True)], attr="1", lst="")); ok, m = fast(row("vst32", ["charge321", "charge329"], quality_charge="charge329", quality_codes=["1123F"]), "1", [], {})
check("challenger c8 (3): a void quality line kept in the register no longer makes the check not ok", ok and len(W[0].v["vst32"].saves) == 1, (ok, m))
W[0] = World(SV("vst33", [chg(331, attrs={"insbilled": "1", "datebilled": "10/29/2026"})], attr="1", lst="1")); ok, m = fast(row("vst33", ["charge331"]), "1,2", [], {})
check("challenger c8 (4): a billed visit re-checked after its lead changed is NOT re-saved", W[0].v["vst33"].saves == [] and not ok, (ok, m))

# ---- 5. resave.set_insorder: the same rules for every caller (freq1_visit.reroute, hand-fix helpers) ----------------------------------------------
W[0] = World(SV("vst41", [chg(411)], attr="1", lst="")); ok, m = setins("411", "1")
check("5 set_insorder: stuck visit (attribute 1, EMPTY list) -> saved, list read back [1] (it was 'already 1 - resave skipped' before)", ok and len(W[0].v["vst41"].saves) == 1 and "list [] -> [1]" in m, (ok, m))
W[0] = World(SV("vst42", [chg(421)], attr="1,2", lst="1,2")); ok, m = setins("421", "1,2")
check("5 set_insorder: list already equal -> skipped, nothing posted", ok and W[0].posts == [] and "resave skipped" in m, (ok, m))
W[0] = World(SV("vst43", [chg(431, attrs={"datebilled": "10/28/2026"}, insbill=True)], attr="1", lst="1")); ok, m = setins("431", "2,1")
check("5 set_insorder: a billed visit is never saved - not ok, 'already billed - not saved'", not ok and W[0].posts == [] and "already billed - not saved" in m, (ok, m))
try: ok, m = setins("431", "2,1", allow_billed=True)
except TypeError as e_: ok, m = False, "set_insorder takes no allow_billed: %s" % e_
check("5 CORRECTION (A) set_insorder(..., allow_billed=True) - the re-route helpers' word - saves the billed visit, with the full echo and the read-back", ok and len(W[0].v["vst43"].saves) == 1 and "list [1] -> [2,1]" in m, (ok, m))
check("5 CORRECTION (A) the keyword is allow_billed and it is False unless a caller says so (every other caller keeps the billed guard)", "def set_insorder(chargeid, order, dry=False, allow_billed=False):" in open(os.path.join(HELPERS, "resave.py")).read() and "billed_ok" not in open(os.path.join(HELPERS, "resave.py")).read())
W[0] = World(SV("vst44", [chg(441), chg(442, cpt="99497", pcode="pcode65299")], attr="1", lst="")); ok, m = setins("441", "1")
check("5 set_insorder: every live charge is echoed (visit_charges) and read back live", ok and W[0].v["vst44"].saves[0].count("<charge ") == 2 and W[0].v["vst44"].live() == ["charge441", "charge442"], (ok, m))
W[0] = World(SV("vst45", [chg(451, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/27/2026", wipe=True)); ok, m = setins("451", "1")
check("5 set_insorder: a wiped admission date is written back with the import's call and read again", ok and len(W[0].v["vst45"].extins) == 1 and _shape.replace("99223", "99223") in W[0].v["vst45"].extins[0] and W[0].v["vst45"].admit == "10/27/2026", (ok, m))
W[0] = World(SV("vst46", [chg(461, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/27/2026", wipe=True, restore=False)); ok, m = setins("461", "1")
check("5 set_insorder: the write-back does not take -> not ok, 'admission date lost on save' (a reroute then never rebills)", not ok and "admission date lost on save" in m, (ok, m))
W[0] = World(SV("vst47", [chg(471)], attr="1", lst="", builds=False)); ok, m = setins("471", "1")
check("5 set_insorder: accepted but the list stays empty -> not ok", not ok and "NOT as asked" in m, (ok, m))
W[0] = World(SV("vst48", [chg(481), chg(482)], attr="1", lst="", void_after={"charge482"})); ok, m = setins("481", "1")
check("5 set_insorder: a charge voided by the save -> not ok, named", not ok and "no longer live: charge482" in m, (ok, m))
W[0] = World(SV("vst49", [chg(491)], attr="1", lst="", fault="always")); ok, m = setins("491", "1")
check("5 set_insorder: a Fault -> not ok, 'resave FAULT'", not ok and "resave FAULT" in m, (ok, m))
W[0] = World(SV("vst50", [chg(501)], attr="1", lst="")); ok, m = setins("501", "3,2", dry=True)
check("5 set_insorder: dry -> nothing posted, the list named", ok and W[0].posts == [] and "DRY" in m and "list []" in m, (ok, m))
_fq = open(os.path.join(HELPERS, "freq1_visit.py")).read(); _fqc = open(os.path.join(ROOT, "core", "freq1_visit.py")).read(); _msp = open(os.path.join(HELPERS, "unbilled_msp_1109_0639.py")).read()
check("5 CORRECTION (A) freq1_visit.reroute (both copies, the same file) and the MSP Unbilled fix pass allow_billed=True - they re-route an ALREADY-BILLED visit after a wrong-payer denial",
      "ok, msg = resave.set_insorder(cid, order, dry=dry, allow_billed=True)" in _fq and _fq == _fqc and "resave.set_insorder(cid, order, dry=not LIVE, allow_billed=True)" in _msp)
_cl = [(f_, l_.strip()) for f_ in glob.glob(os.path.join(HELPERS, "*.py")) + glob.glob(os.path.join(ROOT, "core", "*.py")) for l_ in open(f_, errors="replace").read().splitlines() if "set_insorder(" in l_ and "allow_billed=True" in l_ and "def set_insorder" not in l_]
check("5 CORRECTION (A) ... and no other helper passes allow_billed=True (the insurance check, the sweep and the hand helpers keep the guard)", sorted({os.path.basename(f_) for f_, _l in _cl}) == ["freq1_visit.py", "unbilled_msp_1109_0639.py"], _cl)
# the re-route of a billed, denied visit end to end (NH7-2 / R7-REPLAY-3 / OPS-3: freq1_visit.reroute lifted out of its source, the stand-in AdvancedMD, set_insorder of resave.py)
_rbill = []
FQNS = {"resave": types.SimpleNamespace(set_insorder=setins, visit_charges=lambda cid: W[0].visit_charges(cid), clean_extins=lambda a: a), "time": time, "amd": types.SimpleNamespace(
        msg=AM.msg, post=lambda body, timeout=0: W[0].post(body, timeout), rebill_charge=lambda cid, seq, visitid=None: (_rbill.append((cid, seq)), ("200", "rebilled"))[1])}
exec(lift(os.path.join(HELPERS, "freq1_visit.py"), {"run", "reroute"}), FQNS)
W[0] = World(SV("vst601", [chg(6011, attrs={"datebilled": "10/28/2026 21:07:13", "insbilled": "1"}, insbill=True)], attr="1", lst="1"))
_rr = FQNS["reroute"]("vst601", "6011", "2")
check("5 CORRECTION (A) freq1_visit.reroute on a visit billed to sequence 1 whose denial names sequence 2: the order is saved [2] (full echo, read back) and ONE frequency-1 rebill goes to sequence 2 - not 'NOT rebilled ... already billed'",
      not _rr.startswith("NOT rebilled") and W[0].v["vst601"].lst == "2" and len(W[0].v["vst601"].saves) == 1 and _rbill == [("6011", 2)], (_rr, _rbill))
W[0] = World(SV("vst602", [chg(6021, attrs={"datebilled": "10/28/2026 21:07:13", "insbilled": "1"}, insbill=True)], attr="1", lst="1")); ok, m = setins("6021", "2")
check("5 CORRECTION (A) the same billed visit through set_insorder WITHOUT the re-route's word (the insurance check, the sweep, a hand helper): never saved", not ok and W[0].posts == [] and "already billed - not saved" in m, (ok, m))

# ---- the three confirmation reviews (round 7 fix round): the admission date per hospital code, an answer that never comes back -----------------
def _try(f, *a):
    try: return f(*a)
    except Exception as e_: return False, "RAISED %s: %s" % (type(e_).__name__, e_)
# NH7-4: AdvancedMD keeps the admission date per procedure code (one updextrainsinfo per CPT): 99497 + 99223, the date on the 99223 only
W[0] = World(SV("vst53", [chg(531, cpt="99497", pcode="pcode65299"), chg(532, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit={"99223": "10/10/2026"}, wipe=True)); inf = {}
ok, m = _try(fast, row("vst53", ["charge531", "charge532"], cpts=["99497", "99223"]), "1", [], inf); sv = W[0].v["vst53"]
check("NH7-4 fast_set_insorder, per-code store, the 99497 first in the register: the 99223's admission date the save wiped is seen, written back for 99223 and read again (it was missed and the visit confirmed)",
      ok and sv.admit == {"99223": "10/10/2026"} and len(sv.extins) == 1 and 'txtChargeCode="99223"' in sv.extins[0] and "was lost on save and written back (99223)" in m, (ok, m, sv.admit))
W[0] = World(SV("vst54", [chg(541, cpt="99497", pcode="pcode65299"), chg(542, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit={"99223": "10/10/2026"}))
ok, m = _try(fast, row("vst54", ["charge542", "charge541"], cpts=["99223", "99497"]), "1", [], {})
check("NH7-4 fast_set_insorder, per-code store, the 99223 first in the register and the date kept by the save: no false 'admission date lost on save' (the read-back went through the 99497's detail)",
      ok and "admission date" not in m and W[0].v["vst54"].extins == [], (ok, m))
W[0] = World(SV("vst55", [chg(551, cpt="99497", pcode="pcode65299"), chg(552, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit={"99223": "10/10/2026"}, wipe=True)); ok, m = _try(setins, "551", "1")
check("NH7-4 set_insorder, per-code store, the 99497 first: the 99223's wiped date is written back and read again", ok and W[0].v["vst55"].admit == {"99223": "10/10/2026"} and "written back (99223)" in m, (ok, m, W[0].v["vst55"].admit))
# NH7-3: the save lands, then its answer never comes back (a time-out) - on a hospital visit whose admission date the save wiped
W[0] = World(SV("vst56", [chg(561, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/10/2026", wipe=True, raise_after=TimeoutError("read timed out"))); inf = {}
ok, m = _try(fast, row("vst56", ["charge561"], cpts=["99223"]), "1", [], inf)
check("NH7-3 fast_set_insorder: the save lands and its answer times out - not raised: the visit is read again, the wiped admission date written back (the import's call), not ok, with what the visit reads now",
      not ok and m.startswith("error after the save was sent: the answer to the save never came back (TimeoutError") and W[0].v["vst56"].admit == "10/10/2026" and len(W[0].v["vst56"].extins) == 1 and inf.get("list_now") == "1", (ok, m, inf))
W[0] = World(SV("vst57", [chg(571, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/10/2026", wipe=True, raise_after=TimeoutError("read timed out"))); ok, m = _try(setins, "571", "1")
check("NH7-3 set_insorder: the same - not raised (the sweep no longer crashes), the date written back, not ok", not ok and "the answer to the save never came back" in m and m.startswith("resave ") and W[0].v["vst57"].admit == "10/10/2026", (ok, m))
# (B) the 11/10 clarification: a Medicare Advantage plan WITH drug coverage is a MEDICAL plan; only a stand-alone drug plan is skipped
_drv = VNS["disc_refusal"]; _itb = lambda payer, plan="": {"payer": payer, "plan": plan, "status": "Active Coverage", "member": "X1", "dates": {"planBegin": "20260101"}}
check("B / R7-REPLAY-4 / OPS-6 the insurance check's look-up rule: an Advantage plan with drug coverage may be added ('Medicare Advantage Prescription Drug', an HMO with Part D, an MA-PD PPO with a pharmacy row)",
      _drv(_itb("UNITEDHEALTHCARE"), {"benefitsInformation": [{"code": "1", "planCoverage": "Medicare Advantage Prescription Drug"}]}, "UNI20", ["20261012", "20261020"]) == ""
      and _drv(_itb("HUMANA", "HUMANA GOLD PLUS HMO - MEDICARE ADVANTAGE PRESCRIPTION DRUG"), {}, None, ["20261012"]) == ""
      and _drv(_itb("UNITED HEALTHCARE", "AARP MEDICARE ADVANTAGE HMO WITH PART D"), {}, "UNI20", ["20261012"]) == ""
      and _drv(_itb("AETNA", "MA-PD PPO"), {"benefitsInformation": [{"code": "1", "planCoverage": "PHARMACY"}]}, None, ["20261012"]) == "",
      [_drv(_itb("UNITEDHEALTHCARE"), {"benefitsInformation": [{"code": "1", "planCoverage": "Medicare Advantage Prescription Drug"}]}, "UNI20", ["20261012"])])
check("B ... and a STAND-ALONE drug plan is still skipped ('Prescription Drug Plan', Part D, a PDP - no Advantage / HMO / PPO / medical word); a 'Dental HMO' is still dental",
      all(_drv(_itb(p_, q_), {}, None, ["20261012"]) for p_, q_ in (("HUMANA", "Humana Walmart Value Rx Plan (PDP)"), ("WELLCARE", "Prescription Drug Plan"), ("SILVERSCRIPT", "Medicare Part D"), ("CIGNA", "Cigna Dental HMO")))
      and "dental" in _drv(_itb("CIGNA", "Cigna Dental HMO"), {}, None, ["20261012"]))

# ---- 4.4 / 4.6 the hold words (order_hold) -------------------------------------------------------------------------------------------------------
oh = VNS["order_hold"]
l1, k1 = oh("vst1", "1", "x", {"list_now": ""})
l2, k2 = oh("vst1", "1", "y", {"list_now": "1,2", "sent": True})
l3, k3 = oh("vst1", "1,2", "z", {"list_now": "1", "billed": ["bill date"]})
l4, k4 = oh("vst1", "1", "e", {"list_now": None})
l5, k5 = oh("vst1", "1", "admission date lost on save", {"list_now": "1", "sent": True, "admit_lost": True})
l6, k6 = oh("vst1", "1", "q", {"list_now": "", "accepted": True, "sent": True})
check("4.4/10 an EMPTY list -> 'NO CLAIM CAN BE MADE on <visit>: its insurance order is empty', under no_order_list", l1.startswith("NO CLAIM CAN BE MADE on vst1: its insurance order is empty") and k1 == "no_order_list", l1)
check("4.4/10 a list that differs -> '<visit> still bills to its old insurance order <list>', under order_differs", l2.startswith("vst1 still bills to its old insurance order 1,2") and k2 == "order_differs", l2)
check("4.4/10 billed -> 'already billed - its order was not changed', under order_differs", l3.startswith("vst1 already billed - its order was not changed") and k3 == "order_differs", l3)
check("4.4 a list that could not be read -> said, under order_unread; the order right but the admission date lost -> save_problem", "could not be read" in l4 and k4 == "order_unread" and k5 == "save_problem" and "admission date lost on save" in l5, (l4, l5))
check("4.4 an empty list after an accepted save says the save was sent and no list was built (look before anything is sent again)", "the save was sent and AdvancedMD still built no list" in l6, l6)
check("4.6 every hold line says HOLD stops nothing in AdvancedMD - except a NO CLAIM line, where AdvancedMD makes no claim (it says that instead)",
      all(l_.endswith(HELD) for l_ in (l2, l3, l4, l5)) and HELD not in l1 and l1.endswith("AdvancedMD makes no claim for this visit until it is saved again with its plan in place"), (l1, l2))
lq, kq = oh("vst1", "1", "resave FAULT x", {"list_now": "2"}, lambda w: " (the visit carries the quality line charge9: %s)" % w[:120])
check("4.4 a visit with the quality line keeps the import's words in front ('insorder not applied on <visit> (the visit carries ...)')", lq.startswith("insorder not applied on vst1 (the visit carries the quality line charge9: resave FAULT x) - vst1 still bills to its old insurance order 2"), lq)
_trig = re.compile(r"no active plan|no ACTIVE plan|discovery found \[|CMS reports MA/other primary|Medicaid 271 names SMMC MMA plan")
check("4.4 none of the new words carries a phrase the hand step claimocity_fixholds.py acts on", not any(_trig.search(l_) for l_ in (l1, l2, l3, l4, l5, l6, lq, HELD)))

# ---- 4.7 / 4.8 the look-up rules, as functions --------------------------------------------------------------------------------------------------
dr = VNS["disc_refusal"]
_it = lambda payer, plan="", dates=None: {"payer": payer, "plan": plan, "status": "Active Coverage", "member": "X1", "dates": dates or {}}
_D = ["20261012", "20261020"]
check("4.7 a dental plan by payer name is refused", "dental" in dr(_it("CIGNA Dental Health, Inc.", "Dental HMO"), {}, "CIG09", _D))
check("4.8 THE 11/9 GAP: dental only in a SECOND benefit row's plan text (the summary's plan text and the payer name say nothing) is refused",
      "dental" in dr(_it("CIGNA", ""), {"benefitsInformation": [{"code": "1", "planCoverage": ""}, {"code": "1", "planCoverage": "HM Dental HMO"}]}, "CIG09", _D))
check("4.7 vision, life, drug-only (PDP / Part D / pharmacy) plans are refused", all(dr(_it(p_, q_), {}, None, _D) for p_, q_ in (("EYEMED", ""), ("MetLife", ""), ("HUMANA", "Medicare Part D PDP"), ("OptumRx", ""), ("X", "Pharmacy only"))))
check("4.7 TRICARE FOR LIFE is a medical plan (not refused for the word LIFE)", dr(_it("TRICARE FOR LIFE", "TFL", {"planBegin": "20250101"}), {}, None, _D) == "")
check("4.7 a medical plan whose own dates cover every date of service may be added", dr(_it("UNITED HEALTHCARE", "AARP Medicare Advantage", {"planBegin": "20260101"}), {}, "UNI20", _D) == "")
check("4.7 a plan that begins after the earliest date of service is refused ('not active on 10/12/2026')", dr(_it("UNITED HEALTHCARE", "MA", {"planBegin": "20261015"}), {}, "UNI20", _D).startswith("not active on 10/12/2026"))
check("4.7 a plan that ends before the latest date of service is refused (range in a benefit row)", dr(_it("UNITED HEALTHCARE", "MA"), {"benefitsInformation": [{"benefitsDateInformation": {"plan": "20260301-20261015"}}]}, "UNI20", _D).startswith("not active on 10/20/2026"))
check("4.7 no plan begin date and visits on two dates: not shown active on the earlier date - refused; one date only: allowed (the look-up is dated to it)",
      dr(_it("UNITED HEALTHCARE", "MA"), {}, "UNI20", _D) != "" and dr(_it("UNITED HEALTHCARE", "MA"), {}, "UNI20", ["20261020"]) == "")
_bd = {"planBegin": "1940" + "0215", "planEnd": "1940" + "0215"}      # a placeholder row whose plan dates are the patient's birth date
_w = VNS["disc_words"](_it("SOME PAYER", "x", _bd), {}) + " " + dr(_it("SOME PAYER", "x", _bd), {}, None, _D)
check("4.7 the words for William never print a plan date (a placeholder row can carry the birth date there)", "1940" not in _w and "02/15" not in _w, _w)
check("4.7 dates of service as YYYYMMDD", [VNS["ymd"](x_) for x_ in ("11/02/2026", "1/5/2026", "2026-11-02", "", "x")] == ["20261102", "20260105", "20261102", "", ""])

# ---- 4. the insurance check's loop, run INSIDE this process with stand-in modules -------------------------------------------------------------
def loads(src):
    out_ = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out_.add(n)
    return out_
def run_inside(path, standins, cwd, env=None, argv=()):
    """Run a helper INSIDE this process: its AMD modules are the stand-ins given here (refuses when one is missing), put in sys.modules for the run."""
    src = open(path).read(); missing = sorted((loads(src) & set(AMD_MODULES)) - set(standins))
    if missing: raise RuntimeError("no stand-in for %s - the helper is not run" % missing)
    old_mod = {k: sys.modules.get(k) for k in standins}; old_cwd = os.getcwd(); old_env = dict(os.environ); old_argv = list(sys.argv); out = io.StringIO(); err = ""
    try:
        for k, v in standins.items():
            m_ = types.ModuleType(k); m_.STAND_IN = True
            for n, f in v.items(): setattr(m_, n, f)
            sys.modules[k] = m_
        os.chdir(cwd); os.environ.update(env or {}); sys.argv = [path] + list(argv)
        with contextlib.redirect_stdout(out):
            try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit: pass
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally:
        os.chdir(old_cwd); sys.argv = old_argv
        for k in list(os.environ):
            if k not in old_env: del os.environ[k]
        os.environ.update(old_env)
        for k, v in old_mod.items():
            if v is None: sys.modules.pop(k, None)
            else: sys.modules[k] = v
    return out.getvalue(), err
WS = tempfile.mkdtemp(prefix="feedorder_"); os.makedirs(os.path.join(WS, "registers"))
json.dump(CARS, open(os.path.join(WS, "carriers_rich.json"), "w")); json.dump([{"pid": "f1", "name": "x", "dob": "", "IN1": []}], open(os.path.join(WS, "feed_parsed_T7.json"), "w"))
CH = {}       # chart number -> {"insorder", "plans": [...], "status": {plan id: status}}
DISC = {"calls": [], "answer": {"items": []}}; ADDED = []
_ssrc = ast.parse(open(os.path.join(HELPERS, "stedi.py")).read()); _sns = {}
exec(compile(ast.Module(body=[n for n in _ssrc.body if isinstance(n, ast.FunctionDef) and n.name == "disc_summ"], type_ignores=[]), "stedi.py", "exec"), _sns)      # the vendor client's own summary (a pure function; the module is not imported)
def _plans(num): c = CH[num]; return {"insorder": c["insorder"], "deceased": ""}, [dict(p) for p in c["plans"]]
def _run_plan(num, p):
    s = CH[num]["status"].get("ins" + p, "UNKNOWN")
    if s == "RAISE": raise RuntimeError("271 timed out")
    return {"status": s, "other_payers": []}
def _add(num, car, member): ADDED.append((num, car)); CH[num]["plans"].append({"id": "ins9", "carrier": car, "sequence": "1", "enddate": ""}); return "ins9", "1"
def _disc(first, last, dob, state="FL", dos=None): DISC["calls"].append(dos); return DISC["answer"]
STAND = {"amd": {"login_cached": lambda *a: None, "msg": AM.msg, "post": AM.post}, "resave": {"detail": RS.detail, "visit_charges": RS.visit_charges, "CHG_FIELDS": RS.CHG_FIELDS},
         "elig_amd": {"plans": _plans, "run_plan": _run_plan, "one_line": lambda s: s.get("status")}, "deceased_guard": {"check": lambda *a, **k: (False, ""), "record": lambda *a, **k: None, "_iso": lambda x: x},
         "stedi": {"disc": _disc, "disc_summ": _sns["disc_summ"]}, "add_ins": {"add": _add}, "ins_update": {"_set_order": lambda num, plans, insid, seq: (True, "chart order set")}}
MEDICARE = {"id": "ins1", "carrier": "car6085", "sequence": "1", "enddate": ""}
def verify(rows, charts, prev=None, stedi=False):
    """One insurance-check run over the given import rows; returns (records, output, error)."""
    CH.clear(); CH.update(charts); json.dump({"created": rows}, open(os.path.join(WS, "registers", "feed_import_T7.json"), "w"))
    vf = os.path.join(WS, "feed_verify_T7.json")
    if os.path.exists(vf): os.remove(vf)
    if prev is not None: json.dump(prev, open(vf, "w"))
    o_, e_ = run_inside(os.path.join(HELPERS, "claimocity_verify.py"), STAND, WS, env={"FEED_STAMP": "T7", "DECEASED_CACHE": os.path.join(WS, "dc.json")}, argv=() if stedi else ("--no-stedi",))
    return (json.load(open(vf)) if os.path.exists(vf) else {}), o_, e_
def frow(pid, vid, charges, dos="11/02/2026", **kw): return dict({"feed_id": "f1", "pid": pid, "visit": vid, "charges": charges, "fees": ["141.00"], "dos": dos, "cpts": ["99309"]}, **dict(NEW, **kw))
# 4.1 THE STUCK VISIT END TO END: chart default "1" = the order "1" (the old shortcut sent nothing) - the save is sent, the list read back, RELEASE
W[0] = World(SV("vst701", [chg(7011)], attr="1", lst=""))
R, o, e = verify([frow("pat701", "vst701", ["charge7011"])], {"701": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
r = R.get("pat701") or {}
check("4.1/10 a no-plan visit whose plan landed (chart default 1 = order 1): the save IS sent, the list read back, RELEASE, record version 4", e == "" and r.get("decision") == "RELEASE" and r.get("v") == 4 and len(W[0].v["vst701"].saves) == 1 and W[0].v["vst701"].lst == "1", (e, r))
check("4.3 the fix line carries the whole answer (never just 'ok'), and the save is counted under 'saved'", any(f_.startswith("vst701 insorder 1: insorder 1 -> 1, list [] -> [1]") for f_ in r.get("fixes", [])) and r.get("saved") == ["vst701"], r.get("fixes"))
# 4.2 skip of charts the SAME batch already released - version 3 and version 4 records alike; a held chart is checked again; old 'applied' entries not trusted
for _v in (3, 4):
    W[0] = World(SV("vst702", [chg(7021)], attr="1", lst=""))
    R, o, e = verify([frow("pat702", "vst702", ["charge7021"])], {"702": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}}, prev={"pat702": {"v": _v, "decision": "RELEASE", "visits": ["vst702"], "applied": {"vst702": "1"}}})
    check("4.2 a chart an earlier run of this batch RELEASED (record version %d) is not checked again - nothing read, nothing saved" % _v, e == "" and W[0].posts == [] and R["pat702"].get("v") == _v, (e, R.get("pat702")))
W[0] = World(SV("vst703", [chg(7031)], attr="1", lst=""))
R, o, e = verify([frow("pat703", "vst703", ["charge7031"])], {"703": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}}, prev={"pat703": {"v": 3, "decision": "HOLD", "visits": ["vst703"], "applied": {"vst703": "1"}}})
check("4.2 a HELD chart is checked again, and its version-3 'applied' entry is not trusted (it trusted the attribute): the visit's list is read and saved", e == "" and len(W[0].v["vst703"].saves) == 1 and R["pat703"]["decision"] == "RELEASE", (e, R.get("pat703")))
W[0] = World(SV("vst704", [chg(7041)], attr="1", lst=""))
R, o, e = verify([frow("pat704", "vst704", ["charge7041"])], {"704": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}}, prev={"pat704": {"v": 4, "decision": "HOLD", "visits": ["vst704"], "applied": {"vst704": "1"}}})
check("4.2 ... a version-4 'applied' entry IS trusted (this version read the list): no save", e == "" and W[0].v["vst704"].saves == [], (e, R.get("pat704")))
# 4.4 holds in the loop: billed / list differs / empty after the save / old row; every line with the 4.6 words
W[0] = World(SV("vst705", [chg(7051, attrs={"datebilled": "11/03/2026", "insbilled": "1"})], attr="2", lst="2"), SV("vst706", [chg(7061)], attr="2", lst="2", fault="always"),
             SV("vst707", [chg(7071)], attr="1", lst="", builds=False))
R, o, e = verify([frow("pat705", "vst705", ["charge7051"]), frow("pat705", "vst706", ["charge7061"]), frow("pat705", "vst707", ["charge7071"])], {"705": {"insorder": "2", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
r = R.get("pat705") or {}; H = r.get("hold", [])
check("4.4/10 the loop HOLDS - never releases - a chart with an unconfirmed visit", e == "" and r.get("decision") == "HOLD", (e, r))
check("4.4/10 a billed visit is never saved, held 'already billed - its order was not changed'", W[0].v["vst705"].saves == [] and any(h_.startswith("vst705 already billed - its order was not changed") for h_ in H), H)
check("4.4/10 a list that differs (save refused) -> 'vst706 still bills to its old insurance order 2'", any(h_.startswith("vst706 still bills to its old insurance order 2") for h_ in H), H)
check("4.4/10 an empty list after the save -> 'NO CLAIM CAN BE MADE on vst707: its insurance order is empty'", any(h_.startswith("NO CLAIM CAN BE MADE on vst707: its insurance order is empty") for h_ in H), H)
check("4.4 the visits are recorded under no_order_list / order_differs", r.get("no_order_list") == ["vst707"] and sorted(r.get("order_differs") or []) == ["vst705", "vst706"], r)
check("4.6 every hold line says HOLD is a label in this report only (a NO CLAIM line says AdvancedMD makes no claim)", all(h_.endswith(HELD) or h_.endswith("until it is saved again with its plan in place") for h_ in H) and len(H) == 3, H)
check("4.6 the log line of the chart says it too", "HELD in this report only" in o, o[-300:])
W[0] = World(SV("vst708", [chg(7081)], attr="1", lst=""))
R, o, e = verify([dict(frow("pat708", "vst708", ["charge7081"]), **{"open_plans_at_entry": None})], {"708": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
check("4.2 a row whose import could not read the chart (open_plans_at_entry None) is a round-7 row: its stuck visit IS saved", W[0].v["vst708"].lst == "1" and R["pat708"]["decision"] == "RELEASE", R.get("pat708"))
W[0] = World(SV("vst709", [chg(7091)], attr="1", lst=""))
_old = {k_: v_ for k_, v_ in frow("pat709", "vst709", ["charge7091"]).items() if k_ not in NEW}
R, o, e = verify([_old], {"709": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
check("4.2 an OLD batch's stuck visit (row without the round-7 fields) is never saved by a re-run: HELD, NO CLAIM, named for the sweep", W[0].v["vst709"].saves == [] and R["pat709"]["decision"] == "HOLD" and R["pat709"].get("no_order_list") == ["vst709"]
      and any("feed_order_sweep.py --resave" in h_ for h_ in R["pat709"]["hold"]), R.get("pat709"))
W[0] = World(); R, o, e = verify([frow("pat710", "vst710", [])], {"710": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
check("4.4 a visit with no charge id recorded can no longer pass silently: HOLD, order_unread", R["pat710"]["decision"] == "HOLD" and R["pat710"].get("order_unread") == ["vst710"], R.get("pat710"))
# 4.5 a chart held with no open plan gets its line
W[0] = World(SV("vst711", [chg(7111)], attr="1", lst=""))
R, o, e = verify([frow("pat711", "vst711", ["charge7111"])], {"711": {"insorder": "", "plans": [], "status": {}}})
NOCLAIM = "HELD in this report only - AdvancedMD makes no claim for this visit until it is saved again with its plan in place"
check("4.5 a chart held with no open plan: 'each visit of this chart must be saved again after a plan is added'", R["pat711"]["decision"] == "HOLD" and any(h_.startswith("no open plan on this chart: each visit of this chart must be saved again after a plan is added (vst711)") for h_ in R["pat711"]["hold"]), R.get("pat711"))
check("OPS-9/R7-REPLAY-N1 a chart with no plan whose visits were entered with no plan: EVERY hold line ends with the NO CLAIM words (their insurance order is empty) - never 'AdvancedMD will still bill this visit'",
      R["pat711"]["hold"] and all(h_.endswith(NOCLAIM) and HELD not in h_ for h_ in R["pat711"]["hold"]), R["pat711"]["hold"])
W[0] = World(SV("vst719", [chg(7191)], attr="1", lst="1"))
_ended = {"id": "ins7", "carrier": "car6085", "sequence": "1", "enddate": "10/01/2026"}
R, o, e = verify([dict(frow("pat719", "vst719", ["charge7191"]), open_plans_at_entry=1, chart_insorder="1")], {"719": {"insorder": "1", "plans": [_ended], "status": {}}})
check("OPS-9 ... but a chart whose only plan has ended, with a visit entered while the plan was open (its insurance order is not empty): the lines still say AdvancedMD will bill it", R["pat719"]["hold"] and all(h_.endswith(HELD) for h_ in R["pat719"]["hold"]), R["pat719"]["hold"])
# NH7-5: a lost admission date is remembered - a second run of the same batch does not RELEASE the visit while the date is still gone
W[0] = World(SV("vst720", [chg(7201, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/10/2026", wipe=True, restore=False))
R1, o, e = verify([frow("pat720", "vst720", ["charge7201"], cpts=["99223"])], {"720": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
R2, o, e = verify([frow("pat720", "vst720", ["charge7201"], cpts=["99223"])], {"720": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}}, prev=R1)
check("NH7-5 run 1: the save wipes the admission date and the write-back is refused - HOLD 'admission date lost on save', and the record remembers the date", R1["pat720"]["decision"] == "HOLD" and (R1["pat720"].get("admit_lost") or {}).get("vst720") == {"99223": "10/10/2026"}, R1.get("pat720"))
check("NH7-5 run 2 of the same batch: the list now reads right, but the date is still gone - still HELD (save_problem), never RELEASED; nothing is sent again",
      R2["pat720"]["decision"] == "HOLD" and R2["pat720"].get("save_problem") == ["vst720"] and any("admission date was lost on an earlier save" in h_ for h_ in R2["pat720"]["hold"]) and len(W[0].v["vst720"].saves) == 1, R2.get("pat720"))
W[0].v["vst720"].admit = "10/10/2026"
R3, o, e = verify([frow("pat720", "vst720", ["charge7201"], cpts=["99223"])], {"720": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}}, prev=R2)
check("NH7-5 run 3, after a person wrote the date back: RELEASE, and the memory is gone", R3["pat720"]["decision"] == "RELEASE" and not R3["pat720"].get("admit_lost"), R3.get("pat720"))
# OPS-4: SAVE NOT AS ASKED on one visit of a chart (the admission date lost): the chart's other visits are not saved - William looks first
W[0] = World(SV("vst721", [chg(7211, cpt="99223", pcode="pcode65101")], attr="1", lst="", admit="10/10/2026", wipe=True, restore=False), SV("vst722", [chg(7221)], attr="1", lst=""))
R, o, e = verify([frow("pat721", "vst721", ["charge7211"], cpts=["99223"]), frow("pat721", "vst722", ["charge7221"], dos="11/03/2026")], {"721": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "ACTIVE"}}})
check("OPS-4 after a save that lost the admission date, the chart's next visit is NOT saved: held 'the rest of this chart waits for William' (order_unread)", W[0].v["vst722"].saves == [] and R["pat721"].get("order_unread") == ["vst722"]
      and any(h_.startswith("the insurance order of vst722 was not read or saved: the save of vst721 on this chart did not read back as asked") for h_ in R["pat721"]["hold"]), R.get("pat721"))
# 4.8 free check down: every free check of a chart with plans errored -> nothing bought
W[0] = World(SV("vst712", [chg(7121)], attr="1", lst="1")); DISC["calls"].clear()
R, o, e = verify([frow("pat712", "vst712", ["charge7121"])], {"712": {"insorder": "1", "plans": [MEDICARE, {"id": "ins2", "carrier": "car300", "sequence": "2", "enddate": ""}], "status": {"ins1": "PARSE", "ins2": "RAISE"}}}, stedi=True)
check("4.8 every free check errored: no paid look-up is bought, HOLD 'free check down - not checked tonight'", DISC["calls"] == [] and R["pat712"]["decision"] == "HOLD" and any(h_.startswith("free check down - not checked tonight") for h_ in R["pat712"]["hold"]), (DISC["calls"], R.get("pat712")))
check("4.8 ... worded so the hand step claimocity_fixholds.py buys nothing either (no 'no active plan')", not any(_trig.search(h_) for h_ in R["pat712"]["hold"]), R["pat712"]["hold"])
W[0] = World(SV("vst713", [chg(7131)], attr="1", lst="")); DISC["calls"].clear(); DISC["answer"] = {"items": []}
R, o, e = verify([frow("pat713", "vst713", ["charge7131"])], {"713": {"insorder": "1", "plans": [MEDICARE], "status": {"ins1": "INACTIVE"}}}, stedi=True)
check("4.8 one free check answered (INACTIVE): the look-up is bought, dated to the chart's latest date of service", DISC["calls"] == ["20261102"], DISC["calls"])
# 4.7 a plan only the look-up found: a dental answer is not added; a medical plan active on every date is added and the visits saved
def _ans(payer, plan, dates=None, rows=None): return {"items": [{"payer": {"name": payer}, "payerId": "1", "subscriber": {"memberId": "X1"}, "planDateInformation": dates or {}, "benefitsInformation": rows or [{"code": "1", "name": "Active Coverage", "planCoverage": plan}]}]}
W[0] = World(SV("vst714", [chg(7141)], attr="1", lst="")); ADDED.clear(); DISC["calls"].clear(); DISC["answer"] = _ans("CIGNA Dental Health, Inc.", "Dental HMO", {"planBegin": "20260101"})
R, o, e = verify([frow("pat714", "vst714", ["charge7141"])], {"714": {"insorder": "", "plans": [], "status": {}}}, stedi=True)
check("4.7 a dental plan only the look-up found is NOT added; the chart is held for William with the answer's words", ADDED == [] and R["pat714"]["decision"] == "HOLD" and any("the look-up's answer was not added - for William: CIGNA Dental Health, Inc. 'Dental HMO' Active Coverage" in h_ for h_ in R["pat714"]["hold"]), R.get("pat714"))
check("4.7 ... worded without 'discovery found [' (the hand step would buy the look-up again and add it)", not any("discovery found [" in h_ for h_ in R["pat714"]["hold"]), R["pat714"]["hold"])
W[0] = World(SV("vst715", [chg(7151)], attr="1", lst="")); ADDED.clear(); DISC["answer"] = _ans("UNITED HEALTHCARE", "AARP Medicare Advantage", {"planBegin": "20261015"})
R, o, e = verify([frow("pat715", "vst715", ["charge7151"], dos="10/12/2026"), frow("pat715", "vst716", ["charge7161"], dos="10/20/2026")], {"715": {"insorder": "", "plans": [], "status": {}}}, stedi=True)
check("4.7 a medical plan the answer does not show active on every date of service (begins after 10/12) is NOT added", ADDED == [] and any("not active on 10/12/2026" in h_ for h_ in R["pat715"]["hold"]), R.get("pat715"))
W[0] = World(SV("vst717", [chg(7171)], attr="1", lst="")); ADDED.clear(); DISC["answer"] = _ans("UNITED HEALTHCARE", "AARP Medicare Advantage", {"planBegin": "20260101"})
R, o, e = verify([frow("pat717", "vst717", ["charge7171"])], {"717": {"insorder": "", "plans": [], "status": {}}}, stedi=True)
check("4.7 a medical plan active on every date of service IS added, and the visit is then saved and its list read back - RELEASE", ADDED == [("717", "car300")] and R["pat717"]["decision"] == "RELEASE" and W[0].v["vst717"].lst == "1", (ADDED, R.get("pat717")))
W[0] = World(SV("vst718", [chg(7181)], attr="1", lst="")); ADDED.clear(); DISC["answer"] = _ans("UNITEDHEALTHCARE", "Medicare Advantage Prescription Drug", {"planBegin": "20260101"})
R, o, e = verify([frow("pat718", "vst718", ["charge7181"])], {"718": {"insorder": "", "plans": [], "status": {}}}, stedi=True)
check("B (R7-REPLAY-4's exact input) the look-up answers a Medicare Advantage plan WITH drug coverage on a chart with no plan: the plan IS added and the visit saved - RELEASE (it was refused as 'drug-only')",
      ADDED == [("718", "car300")] and R["pat718"]["decision"] == "RELEASE" and W[0].v["vst718"].lst == "1", (ADDED, R.get("pat718")))
W[0] = World(SV("vst719x", [chg(7192)], attr="1", lst="")); ADDED.clear(); DISC["answer"] = _ans("HUMANA", "Humana Walmart Value Rx Plan (PDP)", {"planBegin": "20260101"})
R, o, e = verify([frow("pat7192", "vst719x", ["charge7192"])], {"7192": {"insorder": "", "plans": [], "status": {}}}, stedi=True)
check("B ... a stand-alone drug plan (PDP) is still not added: held for William with the answer's words", ADDED == [] and R["pat7192"]["decision"] == "HOLD" and any("stand-alone drug plan" in h_ for h_ in R["pat7192"]["hold"]), R.get("pat7192"))

# ---- 6. the digest (claimocity_report.py, run INSIDE this process: it loads no AdvancedMD module) -----------------------------------------------
RSRC = open(os.path.join(HELPERS, "claimocity_report.py")).read()
check("6 the digest helper loads none of the modules that talk to AdvancedMD", not (loads(RSRC) & set(AMD_MODULES)), loads(RSRC))
DG = tempfile.mkdtemp(prefix="feedorder_digest_"); os.makedirs(os.path.join(DG, "registers"))
_rows = [{"feed_id": "f%d" % i, "pid": "pat8%d" % i, "visit": "vst8%d" % i, "charges": ["charge8%d1" % i], "fees": ["141.00"], "cpts": ["99309"], "dos": "11/02/2026"} for i in range(1, 5)]
json.dump({"created": _rows, "skipped": [], "failed": []}, open(os.path.join(DG, "registers", "feed_import_T8.json"), "w"))
json.dump({"pat81": {"v": 4, "decision": "HOLD", "visits": ["vst81"], "no_order_list": ["vst81"], "hold": ["NO CLAIM CAN BE MADE on vst81: its insurance order is empty - x"], "fixes": ["vst81 insorder 1: insorder 1 -> 1, list [] -> [] - NOT AS ASKED"]},
           "pat82": {"v": 4, "decision": "HOLD", "visits": ["vst82"], "hold": ["no ACTIVE plan on the chart (Stedi off) - " + NOCLAIM, "no open plan on this chart: each visit of this chart must be saved again after a plan is added (vst82) - " + NOCLAIM], "fixes": []},
           "pat85": {"v": 4, "decision": "HOLD", "visits": ["vst85"], "order_differs": ["vst85"], "hold": ["vst85 still bills to its old insurance order 2 (x) - " + HELD], "fixes": []},
           "pat83": {"v": 4, "decision": "RELEASE", "visits": ["vst83"], "saved": ["vst83"], "insorder": "1", "applied": {"vst83": "1"}, "fixes": ["vst83 insorder 1: insorder 1 -> 1, list [] -> [1]"], "hold": [], "lead": {"code": "FLO02"}},
           "pat84": {"v": 4, "decision": "RELEASE", "visits": ["vst84"], "insorder": "1", "applied": {"vst84": "2"}, "fixes": ["vst84 insorder 2: already 2, list [2] - nothing sent"], "hold": [], "lead": {"code": "FLO02"}}},
          open(os.path.join(DG, "feed_verify_T8.json"), "w"))
o, e = run_inside(os.path.join(HELPERS, "claimocity_report.py"), {}, DG, env={"FEED_STAMP": "T8"})
_top = [l_ for l_ in o.splitlines() if l_.startswith("  - TOP OF THE REPORT - ")]
check("6/10 the digest's TOP line, word for word: '  - TOP OF THE REPORT - NO CLAIM CAN BE MADE: 1 visit(s) on 1 chart(s) have no insurance order: pat81 vst81'", e == "" and "  - TOP OF THE REPORT - NO CLAIM CAN BE MADE: 1 visit(s) on 1 chart(s) have no insurance order: pat81 vst81" in _top, (e, _top, o[-600:]))
check("6/10 ... and a TOP line for the chart held with no plan", any(l_.startswith("  - TOP OF THE REPORT - 1 chart(s) held with NO plan:") and "pat82 (vst82)" in l_ for l_ in _top), _top)
check("6 'orders changed' counts only saves actually sent and accepted (1 - the visit whose order already matched is not a change)", "- Visit insurance orders changed (saves sent and accepted by AdvancedMD): 1;" in o, [l_ for l_ in o.splitlines() if "orders changed" in l_])
check("4.6/6 the digest says a HOLD is a label in this report only (said once at the end of a chart's line)", "- Holds (William) - " + HELD in o and any(l_.startswith("  - pat85: vst85 still bills") and l_.endswith(HELD) and l_.count(HELD) == 1 for l_ in o.splitlines()), o[-800:])
check("OPS-9 the digest's line for a chart with no plan ends ONCE with the NO CLAIM words and never says AdvancedMD will still bill it", any(l_.startswith("  - pat82: no ACTIVE plan") and l_.endswith(NOCLAIM) and l_.count(NOCLAIM) == 1 and HELD not in l_ for l_ in o.splitlines()), [l_ for l_ in o.splitlines() if "pat82:" in l_])
json.dump({"pat81": {"v": 3, "decision": "RELEASE", "visits": ["vst81"], "insorder": "", "applied": {"vst81": "1"}, "fixes": ["vst81 insorder 1: ok"], "hold": [], "lead": {"code": "FLO02"}}}, open(os.path.join(DG, "feed_verify_T8.json"), "w"))
o, e = run_inside(os.path.join(HELPERS, "claimocity_report.py"), {}, DG, env={"FEED_STAMP": "T8"})
check("6 an older (version 3) check whose order differed from an empty chart order is NOT counted as a change (nothing says a save was sent)", e == "" and "orders changed (saves sent and accepted by AdvancedMD): 0;" in o and "TOP OF THE REPORT - NO CLAIM" not in o, (e, o[-400:]))

# ---- 8. feed_order_sweep.py: the daily listing, the dated checks, the clinician moves and the owner-approved save (run INSIDE this process) ---------
import glob, datetime
SWP = os.path.join(HELPERS, "feed_order_sweep.py"); SSRC = open(SWP).read()
check("8 the sweep loads exactly the modules this self-test stands in for (amd, resave, stedi, deceased_guard)", loads(SSRC) & set(AMD_MODULES) == {"amd", "resave", "stedi", "deceased_guard"}, loads(SSRC) & set(AMD_MODULES))
check("8.3 the sweep never resets a chart's default order, adds or ends a plan, or rebills: none of those helpers or calls is in it",
      not (loads(SSRC) & {"ins_update", "add_ins", "move_to_ins", "freq1_visit", "elig_amd"}) and not re.search(r'_set_order\(|"addinsurance"|"chargerebill"|rebill_charge\(|"updinsurance"', SSRC))
check("8.2 an insurance order is saved only through resave.set_insorder (step 1's list-aware save) - the sweep sends no updvisitwithcharges of its own", "resave.set_insorder(" in SSRC and "updvisitwithcharges" not in SSRC)
check("8.5 the price and the caps: $0.30 a check, 120 checks and $40 a run", "PRICE, CAP_CHECKS, CAP_DOLLARS = 0.30, 120, 40.0" in SSRC)
MIR = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read(); HCS = open(os.path.join(HELPERS, "claimocity_helpers_current.py")).read()
_mk = {"resave.py": "set_insorder never sends a save when the visit's charges could not all be read", "claimocity_verify.py": "A NAME THAT IS ALIKE BUT NOT THE SAME IS HELD LIKE ANY OTHER NAME", "feed_order_sweep.py": "THE ADMISSION DATE IS SET BY THE STANDING RULE, NOT HELD FOR WILLIAM"}      # 11/25/2026: the sentence only the version that sets the admission date by the standing rule has. 11/26/2026 (identity rule .5): the insurance check's marker is the sentence only the version that holds a relative under an alike name has
_mk7 = ('"resave.py": "set_insorder reads the visit\'s insurance-order LIST"', "\"feed_order_sweep.py\": 'STANDING = \"standing word, William 11/10/2026\"'")      # the round-7 entries of mirror.py's table: gone since 11/11/2026
check("mirror.py protects resave.py and the sweep with sentences only their round-8 versions (11/11/2026, the echo guard) have, and the insurance check with one only its version after the second review of 11/25/2026 has (a number in common proves the chart) - it still asks the paid look-up with the chart's own birth date; it still carries round 7's list rule (a copy from before never comes back over them - the round-7 sentences of resave.py and the sweep are no longer the markers); the shared helper names the same sentence for the insurance check",
      all(('"%s": "%s"' % (f_, m_) in MIR or "\"%s\": '%s'" % (f_, m_) in MIR) and m_ in open(os.path.join(HELPERS, f_)).read() for f_, m_ in _mk.items()) and not any(x_ in MIR for x_ in _mk7)
      and '"claimocity_verify.py": "A NAME THAT IS ALIKE BUT NOT THE SAME IS HELD LIKE ANY OTHER NAME"' in HCS and "the paid look-up is asked with the CHART's own name and birth date" in open(os.path.join(HELPERS, "claimocity_verify.py")).read() and "the save is skipped only when the visit's insurance-order LIST" in open(os.path.join(HELPERS, "claimocity_verify.py")).read() and "def set_insorder" not in MIR, {f_: m_ in open(os.path.join(HELPERS, f_)).read() for f_, m_ in _mk.items()})      # 11/25/2026: the insurance check's marker moved on to the sentence only the version that asks with the chart's own birth date has - round 7's list sentence is still in the step
_vc = {p_: open(os.path.join(ROOT, p_)).read() for p_ in ("scripts/helpers/claimocity_import.py", "scripts/helpers/claimocity_ingest.py", "scripts/helpers/claimocity_retry_dx.py", "scripts/helpers/claimocity_report.py", "scripts/helpers/claimocity_helpers_current.py", "tools/mirror/mirror.py", "nightly/claimocity_feed_step.md")}
check("the rule version is 2026-11-25.5 in every place that carries it (import, ingest, retry, report, the shared helper, the mirror's markers, the runbook's grep) and 2026-11-10.8 / .7 / .6 in none of them (11/25/2026, William: every CCM line is 32 - never the skilled-nursing 31; .3 the same day: inpatient rehab at 61 and the chart's own birth date; .4 the fixes after the independent verification of that work; .5 the second round of those fixes)",
      all('VERSION = "2026-11-25.5"' in s_ and not any(('POS_%s_VERSION = "2026-11-25.%d"' % (w_, n_)) in s_ for w_ in ("RULE", "REPORT") for n_ in (3, 4)) and '"2026-11-10.8"' not in s_ and '"2026-11-10.7"' not in s_ and '"2026-11-10.6"' not in s_ for s_ in _vc.values()) and MIR.count('POS_RULE_VERSION = "2026-11-25.5"') == 3
      and "grep -c 'POS_RULE_VERSION = \"2026-11-25.5\"' /home/claude/unbilled/claimocity_import.py" in _vc["nightly/claimocity_feed_step.md"], [p_ for p_, s_ in _vc.items() if 'VERSION = "2026-11-25.5"' not in s_ or '"2026-11-10.8"' in s_])
_apf = os.path.join(ROOT, "practices", "ehpa", "registers", "feed_order_approved.json")
check("8.8 the owner's approved file is in the repository unchanged (the very bytes of 11/10/2026): 84 visits, his answers, no 'william' visit left after his second answer",
      __import__("hashlib").sha256(open(_apf, "rb").read()).hexdigest() == "cb96a8d0ee76af6e4ffc20dba1efe051e5baa71bf38f6e7e4ff668e4ddbee3dc" and len(json.load(open(_apf))["visits"]) == 84
      and "yes to all your recommendations" in open(_apf).read() and not [v_ for v_ in json.load(open(_apf))["visits"].values() if v_.get("decision") == "william"])
BD8 = "1940" + "0215"; BDS = "02/15/" + "1940"      # an invented birth date, written in two pieces (the privacy gate's rule for test dates)
CARS9 = dict(CARS, car500=["DEN01", "CIGNA DENTAL"], car600=["ZZZ01", "SOME PLAN"], car700=["CAP07", "CAPITAL HEALTH"], car800=["BAN07", "BANKERS LIFE AND CASUALTY"])
class SW(SV):
    """A visit for the sweep: its own clinician profile, and the clinician move (updvisitwithnewcharges with another profile) as rebill_under_effinger.py
    describes it - AdvancedMD voids the echoed charges and creates them again under the new profile (keep_old: the old ones stay live = duplicates;
    move_builds: that full save builds the list; move_fault: refused)."""
    def __init__(self, vid, charges, prof="prof13", keep_old=False, move_builds=True, move_fault=False, move_list=None, **kw):
        SV.__init__(self, vid, charges, **kw); self.prof, self.keep_old, self.move_builds, self.move_fault, self.moves = prof, keep_old, move_builds, move_fault, []
        self.move_list = move_list      # the list the move builds when it is NOT the insorder sent (an unexpected read-back)
    def detail(self, cid): return SV.detail(self, cid).replace('profile="prof13"', 'profile="%s"' % self.prof)
    def post(self, body):
        m = re.search(r'<visit [^>]*profile="([^"]*)"', body)
        if 'action="updvisitwithnewcharges"' in body and m and m.group(1) != self.prof:
            self.moves.append(body)
            if self.move_fault: return "<r><Fault><description>refused in this test</description></Fault></r>"
            new = []
            for k in [k for k, c in self.ch.items() if not c.get("void") and 'id="%s"' % k in body]:
                self.ch[k + "9"] = dict(self.ch[k], id=k + "9"); new.append(k + "9")
                if not self.keep_old: self.ch[k]["void"] = True
            self.prof = m.group(1); a_ = re.search(r'<visit [^>]*insorder="([^"]*)"', body); self.attr = a_.group(1) if a_ else self.attr      # the move is a full save: it keeps the insorder it is sent
            if self.move_builds and self.builds: self.lst = self.attr if self.move_list is None else self.move_list
            if self.wipe: self.admit = ""
            return '<r><visit id="%s" profile="%s"><chargelist>%s</chargelist></visit></r>' % (self.vid, self.prof, "".join('<charge id="%s" void="0"/>' % n for n in new))
        return SV.post(self, body)
class SWorld(World):
    """The visits, and each chart's plans for getdemographic (the patient's name and birth date are invented)."""
    def __init__(self, charts, *visits): World.__init__(self, *visits); self.charts = charts
    def post(self, body, timeout=0):
        if 'action="getdemographic"' not in body: return World.post(self, body, timeout)
        self.posts.append(body); c = self.charts.get(re.search(r'patientid="pat(\d+)"', body).group(1))
        if c is None: return "<r><Fault><description>no such chart</description></Fault></r>"
        return '<r><patient id="pat1" name="TESTER, ALPHA" %s="%s"/>%s</r>' % ("dob", BDS, "".join('<insplan id="%s" carrier="%s" begindate="%s" enddate="%s" subscribernum="%s" sequence="%s"/>' % (
            p["id"], p["car"], p.get("begin", "01/01/2026"), p.get("end", ""), p.get("member", "M1"), p["seq"]) for p in c))
DREADS = []; ELIG = {"calls": [], "ans": {}}; DGB = set()
SRS = {k_: RNS[k_] for k_ in ("CHG_FIELDS", "HOSP_CODES", "order_list", "billed_reasons", "admit_of", "admit_codes", "admit_back", "restore_admit", "set_insorder") if k_ in RNS}      # step 1's own functions, run against the stand-in
SRS.update(detail=lambda cid: (DREADS.append(re.sub(r"\D", "", str(cid))), W[0].detail(cid))[1], visit_charges=lambda cid: W[0].visit_charges(cid))
SRS["READ_NOTE"] = ""      # 11/11/2026 (round 8): resave.py's note beside visit_charges's answer - the sweep does not start with a resave.py that has none (section R8); this stand-in's visit_charges never writes it
def _elig(payer, first, last, b8, member, dos, stc=("30",), pid=None):
    ELIG["calls"].append({"payer": payer, "first": first, "last": last, "b": b8, "member": member, "dos": dos, "pid": pid})
    return ELIG["ans"].get((payer, member, dos), {"errors": [{"code": "T1", "description": "no answer in this test"}]})
DGR = {}; DGC = []      # 11/25/2026 (D1): chart -> the error the stand-in guard raises for it; every question that guard got, with the cache file the environment named at that moment
def _dg_standin(pid, dos, carrier=None, proc=None, allow_lookup=True):
    DGC.append((pid, dos, carrier, proc, allow_lookup, os.environ.get("DECEASED_CACHE")))
    if pid in DGR: raise DGR[pid]
    return (True, "the deceased guard blocks it (test)") if pid in DGB else (False, "")
SSTAND = {"amd": STAND["amd"], "resave": SRS, "stedi": {"elig": _elig}, "deceased_guard": {"check": _dg_standin}}
SWD = [None]; NOW = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None); DOC, NPL = "Dr. Effinger (DO)", "Pamela G."; APPF = "registers/feed_order_approved.json"
def ws9(rows, recon=None, verify=None, approved=None, seed=()):
    """A fresh workspace for the sweep: the import register (batch T9), the feed's clinicians, the insurance check's record, the approved file, earlier registers."""
    d = tempfile.mkdtemp(prefix="feedorder_sweep_"); os.makedirs(os.path.join(d, "registers")); SWD[0] = d; ELIG["calls"].clear(); DREADS.clear(); DGB.clear(); DGR.clear(); del DGC[:]
    json.dump(CARS9, open(os.path.join(d, "carriers_rich.json"), "w")); json.dump({"created": rows}, open(os.path.join(d, "registers", "feed_import_T9.json"), "w"))
    json.dump({"rows": [{"v": v_, "prov": p_} for v_, p_ in (recon or {}).items()]}, open(os.path.join(d, "registers", "feed_recon_T9.json"), "w"))
    if verify is not None: json.dump(verify, open(os.path.join(d, "registers", "feed_verify_T9.json"), "w"))
    if approved is not None: json.dump({"what": "test", "approved_by": "the owner (test)", "answers": ["yes (test)"], "visits": approved}, open(os.path.join(d, "registers", "feed_order_approved.json"), "w"))
    for name, j_ in seed: json.dump(j_, open(os.path.join(d, "registers", name), "w"))
def sweep(*argv):
    se = io.StringIO()
    with contextlib.redirect_stderr(se): o_, e_ = run_inside(SWP, SSTAND, SWD[0], argv=argv)
    return o_ + se.getvalue(), e_
def sreg(kind): return [json.load(open(f_)) for f_ in sorted(glob.glob(os.path.join(SWD[0], "registers", "feed_order_%s_*.json" % kind)))]
def srow(vid, pid, dos, cpts, charges, days_ago=1, **kw): return dict({"feed_id": "f9", "pid": pid, "visit": vid, "charges": charges, "fees": ["141.00"] * len(charges), "at": (NOW - datetime.timedelta(days=days_ago)).isoformat(), "dos": dos, "cpts": cpts, "prof": "prof13", "admit": ""}, **kw)
def age(dos): return (NOW.date() - datetime.date(int(dos[6:]), int(dos[:2]), int(dos[3:5]))).days
def tops(o_): return [l_ for l_ in o_.splitlines() if l_.startswith("TOP OF THE REPORT - NO CLAIM CAN BE MADE: ")]
def top(o_, vid): return next((l_ for l_ in tops(o_) if re.match(r"TOP OF THE REPORT - NO CLAIM CAN BE MADE: \S+ %s\b" % vid, l_)), "")
def med(pid, member, *more): return [{"id": "ins%s" % pid, "car": "car6085", "seq": "1", "member": member}] + list(more)
PARTB = lambda: {"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "MEDICARE PART B"}], "benefitsInformation": [{"code": "1", "insuranceTypeCode": "MB", "benefitsDateInformation": {"plan": "20200101-"}}]}
PILOT_DONE = ("feed_order_resave_20261101T000000Z.json", {"rows": [{"visit": "vst1", "sent": True, "ok": True}]})
MOVE_DONE = ("feed_order_fixclin_20261101T000000Z.json", {"moves": [{"visit": "vst1", "sent": True, "ok": True}]})
# 8.1 THE LISTING (read only)
W[0] = SWorld({"901": med("901", "M901"), "902": [{"id": "ins902", "car": "car300", "seq": "1"}], "903": [{"id": "ins903", "car": "car100", "seq": "1"}], "904": med("904", "M904"), "905": med("905", "M905"), "906": [], "907": med("907", "M907")},
    SW("vst9011", [chg(90111)]), SW("vst9012", [chg(90121, cpt="99306", pcode="pcode65306"), chg(90122, cpt="99497", pcode="pcode65299")]),
    SW("vst9013", [chg(90131, cpt="99223", pcode="pcode65101")], admit="10/28/2026"), SW("vst9015", [chg(90151, cpt="99232", pcode="pcode65102")], admit="10/27/2026"),
    SW("vst9016", [chg(90161, cpt="99232", pcode="pcode65102", attrs={"datebilled": "11/01/2026"})], lst="1", admit="10/28/2026"), SW("vst9017", [chg(90171, cpt="99232", pcode="pcode65102")]),
    SW("vst9018", [chg(90181, attrs={"insbilled": "1"})], lst="1"), SW("vst9019", [chg(90191)], lst="1"), SW("vst9020", [chg(90201, attrs={"billins": "0"})], attr=""),
    SW("vst9021", [chg(90211)]), SW("vst9022", [chg(90221), chg(90222, cpt="1123F", pcode="pcode65441", fee="0.00", void=True)]),
    SW("vst9023", [chg(90231, attrs={"datebilled": "11/02/2026"}), chg(90232, attrs={"datebilled": "11/02/2026"})], lst="1"), SW("vst9024", [chg(90241), chg(90242, cpt="99497", pcode="pcode65299", void=True)]))
ws9([srow("vst9011", "pat901", "10/12/2026", ["99344"], ["charge90111"]), srow("vst9012", "pat901", "10/14/2026", ["99306", "99497"], ["charge90121", "charge90122"]),
     srow("vst9013", "pat902", "10/27/2026", ["99223"], ["charge90131"], admit="20261028"),
     srow("vst9015", "pat903", "10/30/2026", ["99232"], ["charge90151"], admit="20261027"), srow("vst9016", "pat903", "10/31/2026", ["99232"], ["charge90161"], admit="20261028"),
     srow("vst9017", "pat904", "11/01/2026", ["99232"], ["charge90171"], admit="20261101"), srow("vst9018", "pat905", "11/02/2026", ["99309"], ["charge90181"]),
     srow("vst9019", "pat905", "11/03/2026", ["99309"], ["charge90191"]), srow("vst9020", "pat906", "11/03/2026", ["99309"], ["charge90201"]),
     srow("vst9021", "pat907", "09/25/2026", ["99309"], ["charge90211"], days_ago=40), srow("vst9022", "pat901", "11/04/2026", ["99309", "1123F"], ["charge90221", "charge90222"], quality_charge="charge90222", quality_codes=["1123F"]),
     srow("vst9023", "pat905", "11/02/2026", ["99309", "99497"], ["charge90231", "charge90232"]), srow("vst9024", "pat901", "11/05/2026", ["99309", "99497"], ["charge90241", "charge90242"])],
    recon={"vst9011": NPL, "vst9012": NPL, "vst9013": DOC, "vst9015": DOC, "vst9017": DOC, "vst9022": DOC, "vst9024": DOC})
o, e = sweep()
check("8.1/10 the listing: one TOP line per never-billed visit with an EMPTY insurance order - chart, visit, service date, age, payer", e == "" and len(tops(o)) == 8
      and top(o, "vst9011").startswith("TOP OF THE REPORT - NO CLAIM CAN BE MADE: pat901 vst9011 service date 10/12/2026 (%d days old), payer FLO02 seq 1: its insurance order is empty" % age("10/12/2026")), (e, tops(o)))
check("8.1 a billed visit, a visit whose list is filled (it waits for the claim run) and a self-pay visit are not listed", not any(top(o, v_) for v_ in ("vst9016", "vst9018", "vst9019", "vst9020", "vst9023")), tops(o))
check("R7-REPLAY-5 a stuck visit entered 40 days ago (service date 09/25/2026) is STILL listed - the window is the service date's timely-filing year, not 30 days from entry", top(o, "vst9021") != "", tops(o))
check("8.1/8.4/10 a clinician mismatch is listed: entered under the physician, the feed names the nurse practitioner", "clinician: entered under the physician (prof13) - the feed names the nurse practitioner (prof15)" in top(o, "vst9011"), top(o, "vst9011"))
check("8.4 an initial nursing-facility visit (99306 + 99497) under the physician is not a mismatch, and the line SHOWS the feed's clinician for William",
      "clinician: entered under" not in top(o, "vst9012") and "an initial nursing-facility visit: the physician's by William's rule - the feed names the nurse practitioner (prof15): William confirms who saw the patient" in top(o, "vst9012"), top(o, "vst9012"))
check("8.1/10 admission dates in the listing (11/25/2026: set by the standing rule, not held): a 99223 whose date is the day after its own becomes its own date; two dates in one stay are said and hold nothing; a hospital visit with no date on a chart with no initial hospital visit is still for a person",
      "its admission date 10/28/2026 becomes 10/27/2026 - the date of the chart's most recent initial hospital visit on or before it (William 11/19/2026); written with the save" in top(o, "vst9013") and "is after its service date" not in top(o, "vst9013")
      and "two admission dates in one stay: vst9015 10/27/2026, vst9016 10/28/2026 - not held for it (William 11/19/2026)" in top(o, "vst9015")
      and "a hospital visit with no admission date" in top(o, "vst9017") and "admission" not in top(o, "vst9011"), (top(o, "vst9013"), top(o, "vst9015"), top(o, "vst9017")))
check("8.1 a void no-charge quality line (1123F) the import entered does not count against the visit", top(o, "vst9022") != "" and "read void" not in top(o, "vst9022"), top(o, "vst9022"))
check("8.1 (investigator's case) a charge of the visit's own that now reads void is listed - a person reads it; the save refuses it", "charge(s) the import entered now read void: charge90242" in top(o, "vst9024"), top(o, "vst9024"))
check("8.1 one charge detail per charge the import entered - and a billed visit stops at its first billed charge", "90121" in DREADS and "90122" in DREADS and "90231" in DREADS and "90232" not in DREADS and "90211" in DREADS, DREADS)
check("8.1 the listing is read only: no save, no admission-date write, no vendor call - only charge details and one chart read per chart with such a visit",
      not any(re.search(r'action="(updvisit|updextrainsinfo|addinsurance)', p_) for p_ in W[0].posts) and ELIG["calls"] == [] and not any(sv_.saves or sv_.extins for sv_ in W[0].v.values())
      and len(W[0].posts) == len(set(W[0].posts)) == 5, [p_[:90] for p_ in W[0].posts])
_r1 = sreg("sweep")
check("8.1 its register lists the billed visits (never read again) and carries no name or birth date", len(_r1) == 1 and set(_r1[0].get("billed") or []) == {"vst9016", "vst9018", "vst9023"}
      and not re.search("TESTER|ALPHA|%s|%s" % (BD8, re.escape(BDS)), json.dumps(_r1)), _r1[0].get("billed") if _r1 else _r1)
DREADS.clear(); o2, e2 = sweep()
check("8.1 the next run does not read a visit an earlier sweep saw billed", e2 == "" and "billed before 3" in o2 and not set(DREADS) & {"90161", "90181", "90231"} and len(sreg("sweep")) == 2, ([l_ for l_ in o2.splitlines() if l_.startswith("Feed order sweep")], DREADS))
# 8.5 + 8.2 THE OWNER'S APPROVED VISITS: dated checks, then the save (the pilot first)
FL1 = [{"carrier": "FLO02", "seq": "1"}]
APB = {"vst9101": {"decision": "send_if_active_on_dos", "order": "1", "plans_in_force_today": FL1}, "vst9102": {"decision": "send_if_active_on_dos", "order": "1", "plans_in_force_today": FL1},
       "vst9103": {"decision": "send", "order": "1", "evidence": "face sheet (test)", "plans_in_force_today": [{"carrier": "CAP07", "seq": "1"}]},
       "vst9104": {"decision": "send_if_active_on_dos", "order": "1", "plans_in_force_today": [{"carrier": "UNI20", "seq": "1"}]},
       "vst9106": {"decision": "william", "order": "1"}, "vst9107": {"decision": "send_if_active_on_dos", "order": "1", "plans_in_force_today": FL1}}
W[0] = SWorld({"911": med("911", "M911"), "912": [{"id": "ins912", "car": "car700", "seq": "1", "member": "M912"}], "913": [{"id": "ins913", "car": "car300", "seq": "1", "member": "M913"}],
               "914": med("914", "M914"), "915": med("915", "M915"), "916": med("916", "M916")},
    *[SW("vst910%d" % i_, [chg(91000 + i_ * 10 + 1, attrs={"patbalance": "20.00"} if i_ == 7 else {})]) for i_ in range(1, 8)])
ws9([srow("vst9101", "pat911", "10/15/2026", ["99309"], ["charge91011"]), srow("vst9102", "pat911", "10/15/2026", ["99309"], ["charge91021"]), srow("vst9103", "pat912", "10/16/2026", ["99309"], ["charge91031"]),
     srow("vst9104", "pat913", "10/17/2026", ["99309"], ["charge91041"]), srow("vst9105", "pat914", "10/18/2026", ["99309"], ["charge91051"], open_plans_at_entry=1, chart_insorder="1"),
     srow("vst9106", "pat915", "10/19/2026", ["99309"], ["charge91061"]), srow("vst9107", "pat916", "10/20/2026", ["99309"], ["charge91071"])],
    recon={"vst910%d" % i_: DOC for i_ in range(1, 8)}, approved=APB)
ELIG["ans"] = {("CMS", "M911", "20261015"): PARTB(), ("87726", "M913", "20261017"): {"planStatus": [{"statusCode": "6", "status": "Inactive"}]}}
o, e = sweep("--coverage", "--approved", APPF)
check("8.5 --coverage without --live buys nothing and says what it would buy (one check per chart and date: vst9101 and vst9102 share one)", e == "" and ELIG["calls"] == [] and "2 eligibility check(s) dated to the service date would be bought (dry run - nothing bought) - $0.60" in o
      and "would check vst9101 10/15/2026 FLO02 seq 1" in o and "would check vst9104 10/17/2026 UNI20 seq 1" in o and sreg("coverage") == [], (e, o[-700:]))
o, e = sweep("--coverage", "--approved", APPF, "--live")
_cv = sreg("coverage"); _ans = (_cv[0].get("answers") if _cv else []) or []
check("8.5/10 --coverage --live: ONE check dated to the service date per chart and date - Medicare through the CMS route with the chart's Medicare number, the other plan with its member id",
      e == "" and sorted((c_["payer"], c_["member"], c_["dos"], c_["pid"], c_["first"], c_["last"], c_["b"]) for c_ in ELIG["calls"]) == [("87726", "M913", "20261017", "913", "ALPHA", "TESTER", BD8), ("CMS", "M911", "20261015", "911", "ALPHA", "TESTER", BD8)], (e, ELIG["calls"]))
check("8.5 no check for a visit the file sends on its evidence, a visit kept for William, a visit outside the file, or a visit that fails another check (a balance on the patient)", not [c_ for c_ in ELIG["calls"] if c_["member"] in ("M912", "M914", "M915", "M916")], ELIG["calls"])
check("8.5 the register: visit, chart, date of service, payer, yes / no with the answer's words - never a name, a birth date or a member id; the count and the cost are said",
      sorted((a_["visit"], a_["dos"], a_["code"], a_["active"]) for a_ in _ans) == [("vst9101", "10/15/2026", "FLO02", "yes"), ("vst9104", "10/17/2026", "UNI20", "no")] and _cv[0].get("checks") == 2 and _cv[0].get("cost") == 0.6
      and not re.search("TESTER|ALPHA|M911|M913|%s|%s" % (BD8, re.escape(BDS)), json.dumps(_cv)) and "2 eligibility check(s) dated to the service date bought - $0.60 at $0.30 a check (cap 120 checks / $40 a run); active on the date 1, not active 1, error 0" in o, (_ans, o[-500:]))
check("8.5 a plan the dated check does not show active is listed for William (never saved)", "FEED ORDER COVERAGE - for William: pat913 vst9104 service date 10/17/2026, UNI20 seq 1: no - Inactive" in o, o[-400:])
ELIG["calls"].clear(); o, e = sweep("--coverage", "--approved", APPF, "--live")
check("8.5 an answered check is never bought again", e == "" and ELIG["calls"] == [] and len(sreg("coverage")) == 1, ELIG["calls"])
o, e = sweep("--resave", "--approved", APPF, "--live"); _rs = sreg("resave")
sv1 = W[0].v["vst9101"]
check("8.2/10 PILOT: the first live run saves ONE visit (the oldest that passes every check) through set_insorder - the full echo with insorder 1 - and reads the list back [1]",
      e == "" and len(sv1.saves) == 1 and 'action="updvisitwithcharges"' in sv1.saves[0] and 'insorder="1"' in sv1.saves[0] and sv1.lst == "1" and all(W[0].v[v_].saves == [] for v_ in ("vst9102", "vst9103", "vst9104", "vst9105", "vst9106", "vst9107"))
      and "FEED ORDER SAVE: pat911 vst9101 10/15/2026 (the owner's approved file (send_if_active_on_dos)): saved - insurance order [1], admission date none, clinician prof13 read back as asked" in o, (e, o[-900:]))
_rows = {r_["visit"]: r_ for r_ in (_rs[0]["rows"] if _rs else [])}
check("8.2 one register row per visit: saved and read back, waiting for the pilot, refused with its words", _rows.get("vst9101", {}).get("ok") is True and _rows.get("vst9101", {}).get("list_after") == "1" and "pilot" in _rows.get("vst9102", {}).get("waits", "")
      and "pilot" in _rows.get("vst9103", {}).get("waits", "") and "the check dated to 10/17/2026 answered: Inactive" in _rows.get("vst9104", {}).get("refused", ""), _rows)
check("8.1/8.2 the TOP lines come last and say what this run did: the visit saved and read back has none any more; a visit not saved carries the reason",
      not top(o, "vst9101") and top(o, "vst9104").endswith("| this run: for William: the check dated to 10/17/2026 answered: Inactive") and top(o, "vst9102").endswith("| this run: the pilot saves ONE visit whose clinician was never changed and reads it back first - the next run does the rest")
      and o.index("FEED ORDER SAVE: pat911 vst9101") < o.index("TOP OF THE REPORT - NO CLAIM CAN BE MADE: pat911 vst9102"), [l_[-140:] for l_ in tops(o)])
check("8.2/10 --resave refuses a visit not in the approved file, never touches a visit kept for William, and refuses a visit that fails a check (a balance on the patient)",
      _rows.get("vst9105", {}).get("refused") == "not in the owner's approved file - never saved by --resave --approved" and "kept for William" in _rows.get("vst9106", {}).get("kept", "") and "$20.00 sits on the patient" in _rows.get("vst9107", {}).get("refused", ""), _rows)
o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.2 after the pilot read back as asked, the next run saves the rest that pass (the file's own evidence counts for a 'send' visit) - and the saved one is no longer listed",
      e == "" and len(W[0].v["vst9102"].saves) == 1 and len(W[0].v["vst9103"].saves) == 1 and W[0].v["vst9103"].lst == "1" and len(sv1.saves) == 1 and not top(o, "vst9101") and all(W[0].v[v_].saves == [] for v_ in ("vst9104", "vst9105", "vst9106", "vst9107")), (e, o[-600:]))
# the first unexpected read-back stops the run, and every later run, until a person writes "cleared" into that row
W[0] = SWorld({"921": med("921", "M921")}, SW("vst9201", [chg(92011)], builds=False), SW("vst9202", [chg(92021)]))
_send = {"decision": "send", "order": "1", "evidence": "face sheet (test)", "plans_in_force_today": FL1}
ws9([srow("vst9201", "pat921", "10/12/2026", ["99309"], ["charge92011"]), srow("vst9202", "pat921", "10/13/2026", ["99309"], ["charge92021"])], recon={"vst9201": DOC, "vst9202": DOC},
    approved={"vst9201": _send, "vst9202": _send}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.2/10 STOP at the first unexpected read-back: the save is sent, AdvancedMD builds no list - the run stops there, the next visit is not saved, the top of the report says so",
      e == "" and len(W[0].v["vst9201"].saves) == 1 and W[0].v["vst9202"].saves == [] and "TOP OF THE REPORT - FEED ORDER SWEEP STOPPED at pat921 vst9201: the save did not read back as asked" in o, (e, o[-600:]))
o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.2 ... and every later run sends nothing while that row is not cleared", e == "" and len(W[0].v["vst9201"].saves) == 1 and W[0].v["vst9202"].saves == [] and "TOP OF THE REPORT - FEED ORDER SWEEP STOPPED: an earlier save or move did not read back as asked: vst9201" in o
      and "an earlier save or move did not read back as asked - nothing is saved" in o, o[-600:])
_f = sorted(glob.glob(os.path.join(SWD[0], "registers", "feed_order_resave_*.json")))[-1]; _j = json.load(open(_f))
for r_ in _j["rows"]:
    if r_.get("unexpected"): r_["cleared"] = "a person, after looking at the visit (test)"
json.dump(_j, open(_f, "w")); W[0].v["vst9201"].builds = True
o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.2 once a person has written 'cleared' into that row, the saves go on", e == "" and W[0].v["vst9201"].lst == "1" and len(W[0].v["vst9202"].saves) == 1 and W[0].v["vst9202"].lst == "1", o[-500:])
# 8.7 THE CLINICIAN MOVES (William 11/10/2026, Q4)
_mv = dict(_send, clinician="prof15")
W[0] = SWorld({"931": med("931", "M931"), "932": med("932", "M932"), "933": med("933", "M933")},
    SW("vst9301", [chg(93011)], move_builds=False), SW("vst9302", [chg(93021, cpt="99306", pcode="pcode65306"), chg(93022, cpt="99497", pcode="pcode65299")]),
    SW("vst9303", [chg(93031)]), SW("vst9304", [chg(93041, cpt="99232", pcode="pcode65102")], admit="10/15/2026", wipe=True, move_builds=False))
ws9([srow("vst9301", "pat931", "10/12/2026", ["99309"], ["charge93011"]), srow("vst9302", "pat931", "10/14/2026", ["99306", "99497"], ["charge93021", "charge93022"]),
     srow("vst9303", "pat932", "10/15/2026", ["99309"], ["charge93031"]), srow("vst9304", "pat933", "10/16/2026", ["99232"], ["charge93041"], admit="20261015")],
    recon={v_: NPL for v_ in ("vst9301", "vst9302", "vst9303", "vst9304")},
    approved={"vst9301": _mv, "vst9302": _mv, "vst9303": dict(_mv, decision="send_if_active_on_dos", evidence=""), "vst9304": _mv})
o, e = sweep("--fix-clinician", "--approved", APPF, "--live")
check("9/8.7 the remedy order: no clinician move before the first save of this helper (the pilot, a visit whose clinician matches) has read back as asked",
      e == "" and not any(sv_.moves for sv_ in W[0].v.values()) and "FEED ORDER CLINICIAN - waits: pat931 vst9301 10/12/2026 - the clinician moves wait until the first save of this helper (the pilot) has read back as asked" in o, o[-600:])
json.dump(PILOT_DONE[1], open(os.path.join(SWD[0], "registers", PILOT_DONE[0]), "w"))      # the pilot save has read back as asked
o, e = sweep("--fix-clinician", "--approved", APPF, "--live"); s1 = W[0].v["vst9301"]
_call = ['action="updvisitwithnewcharges" class="chargeentry"', 'approval="1"', 'inspectorenabled="1"', 'getfinancials="-1"', 'customclaimfieldsavailable="1"', 'nocookie="1"', 'profile="prof15"', 'force="1"', '<charge id="charge93011"']
check("8.7 PILOT: the first live run moves ONE visit to the nurse practitioner with rebill_under_effinger.py's call - updvisitwithnewcharges, profile prof15, force 1, every live charge echoed",
      e == "" and len(s1.moves) == 1 and all(x_ in s1.moves[0] for x_ in _call) and s1.prof == "prof15" and s1.live() == ["charge930119"] and W[0].v["vst9304"].moves == [], (e, s1.moves[:1], o[-700:]))
_fx = {m_["visit"]: m_ for m_ in (sreg("fixclin")[0]["moves"] if sreg("fixclin") else [])}
check("8.7 read back and recorded: old -> new charge ids and visit id, the profile, the list", _fx.get("vst9301", {}).get("ok") is True and _fx["vst9301"].get("old_charges") == ["charge93011"] and _fx["vst9301"].get("new_charges") == ["charge930119"]
      and _fx["vst9301"].get("new_visit") == "vst9301" and _fx["vst9301"].get("profile_now") == "prof15" and _fx["vst9301"].get("list_now") == "", _fx.get("vst9301"))
check("8.4/8.7 an initial nursing-facility visit is never moved off the physician, even when the file asks; a visit without proof of coverage on its date is not moved either",
      W[0].v["vst9302"].moves == [] and W[0].v["vst9303"].moves == [] and "an initial nursing-facility visit stays under the physician (William 11/10/2026)" in o and "FEED ORDER CLINICIAN - not moved: pat932 vst9303" in o, o[-900:])
check("8.7 a clinician move sets no insurance order (no updvisitwithcharges)", not any(sv_.saves for sv_ in W[0].v.values()), [len(sv_.saves) for sv_ in W[0].v.values()])
o, e = sweep("--fix-clinician", "--approved", APPF, "--live"); s4 = W[0].v["vst9304"]
check("8.7 the next run moves the rest; an admission date the move wiped is written back with the import's own call and read again",
      e == "" and len(s4.moves) == 1 and len(s4.extins) == 1 and _shape.replace("99223", "99232").replace("10/27/2026", "10/15/2026") in s4.extins[0] and s4.admit == "10/15/2026"
      and "admission date 10/15/2026 was lost on the move and written back (99232)" in json.dumps(sreg("fixclin")), (e, s4.extins, o[-600:]))
check("8.7 the listing then reads the moved visit's NEW charges and expects the nurse practitioner (no clinician line)", top(o, "vst9301") != "" and "clinician:" not in top(o, "vst9301") and "930119" in DREADS, top(o, "vst9301"))
o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.7/8.2 the moved visit then goes through the save like the others - its clinician check now expects prof15 - and is read back", e == "" and len(s1.saves) == 1 and 'id="charge930119"' in s1.saves[0] and s1.lst == "1"
      and "FEED ORDER SAVE: pat931 vst9301 10/12/2026 (the owner's approved file (send)): saved - insurance order [1], admission date none, clinician prof15 read back as asked" in o, (e, o[-600:]))
check("8.7/8.2 a visit the file moves to the nurse practitioner is never saved while it is still under another clinician (here an initial visit, which stays under the physician: William decides)",
      W[0].v["vst9302"].saves == [] and "for William: the owner's approved file moves this visit to the nurse practitioner (prof15) first, but an initial nursing-facility visit stays under the physician (William 11/10/2026) - it is still under the physician (prof13)" in o, o[-700:])
check("OPS-5 a visit that waits for the clinician move says who acts: 'waits for the clinician move to the nurse practitioner (prof15) - a chat session runs --fix-clinician' (on its TOP line, after '| this run:' too) - never 'moved ... first' while it is not",
      "waits for the clinician move to the nurse practitioner (prof15) - a chat session runs --fix-clinician" in top(o, "vst9303") and "moved to the nurse practitioner (prof15) first" not in o, top(o, "vst9303"))
W[0] = SWorld({"941": med("941", "M941")}, SW("vst9311", [chg(93111)], keep_old=True, move_builds=False), SW("vst9312", [chg(93121)], move_builds=False))
ws9([srow("vst9311", "pat941", "10/12/2026", ["99309"], ["charge93111"]), srow("vst9312", "pat941", "10/13/2026", ["99309"], ["charge93121"])], recon={"vst9311": NPL, "vst9312": NPL},
    approved={"vst9311": _mv, "vst9312": _mv}, seed=[MOVE_DONE, PILOT_DONE])
o, e = sweep("--fix-clinician", "--approved", APPF, "--live")
check("8.7 a move that leaves the old charges live beside the new ones is an unexpected read-back: the run stops, the next visit is not moved", e == "" and W[0].v["vst9312"].moves == []
      and "TOP OF THE REPORT - FEED ORDER SWEEP STOPPED at pat941 vst9311: old charge(s) still live beside the new ones: charge93111" in o, o[-600:])
o, e = sweep("--resave", "--fix-clinician", "--approved", APPF, "--live")
check("8.7 ... and nothing is moved or saved after it until that row is cleared", e == "" and W[0].v["vst9312"].moves == [] and not any(sv_.saves for sv_ in W[0].v.values()) and "nothing is moved" in o and "nothing is saved" in o, o[-500:])
W[0] = SWorld({"942": med("942", "M942")}, SW("vst9321", [chg(93211)], prof="prof15"), SW("vst9322", [chg(93221)]))
ws9([srow("vst9321", "pat942", "10/12/2026", ["99309"], ["charge93211"]), srow("vst9322", "pat942", "10/13/2026", ["99309"], ["charge93221"])], recon={"vst9321": NPL, "vst9322": DOC},
    approved={"vst9321": _mv, "vst9322": _send}, seed=[("feed_order_fixclin_20261101T000000Z.json", {"moves": [{"visit": "vst9321", "sent": True, "ok": True, "new_visit": "vst9321", "new_charges": ["charge93211"]}]})])
o, e = sweep("--resave", "--approved", APPF, "--live")
check("9 the pilot save is a visit whose clinician was never changed: the older, moved visit waits; the next run saves it", e == "" and W[0].v["vst9321"].saves == [] and len(W[0].v["vst9322"].saves) == 1
      and "FEED ORDER SAVE - waits: pat942 vst9321 10/12/2026 - the pilot saves ONE visit whose clinician was never changed" in o, o[-600:])
o, e = sweep("--resave", "--approved", APPF, "--live")
check("9 ... and after the pilot read back as asked, the moved visit is saved (under the nurse practitioner, as the file asks)", e == "" and len(W[0].v["vst9321"].saves) == 1 and W[0].v["vst9321"].lst == "1", o[-400:])
# 8.6 THE STANDING WORD (William 11/10/2026, Q5)
W[0] = SWorld({"951": med("951", "M951"), "952": med("952", "M952", {"id": "ins9522", "car": "car300", "seq": "2", "member": "U952"}), "953": med("953", "M953", {"id": "ins9532", "car": "car500", "seq": "2", "member": "D953"}),
               "954": med("954", "M954"), "955": med("955", "M955"), "956": med("956", "M956")}, *[SW("vst940%d" % i_, [chg(94000 + i_ * 10 + 1)]) for i_ in range(1, 7)])
_np = dict(open_plans_at_entry=0, chart_insorder="")
ws9([srow("vst9401", "pat951", "10/20/2026", ["99309"], ["charge94011"], **_np), srow("vst9402", "pat952", "10/21/2026", ["99309"], ["charge94021"], **_np), srow("vst9403", "pat953", "10/22/2026", ["99309"], ["charge94031"], **_np),
     srow("vst9404", "pat954", "10/23/2026", ["99309"], ["charge94041"], open_plans_at_entry=1, chart_insorder="1"), srow("vst9405", "pat955", "10/24/2026", ["99309"], ["charge94051"]),
     srow("vst9406", "pat956", "10/25/2026", ["99309"], ["charge94061"], **_np)],
    recon={"vst940%d" % i_: DOC for i_ in range(1, 7)}, verify={"pat955": {"v": 3, "plans": [], "insorder": ""}}, approved={"vst9406": _send}, seed=[PILOT_DONE])
ELIG["ans"] = {("CMS", m_, d_): PARTB() for m_, d_ in (("M951", "20261020"), ("M953", "20261022"), ("M955", "20261024"))}
o, e = sweep("--coverage", "--live")
check("8.5/8.6 the dated checks also cover the standing word's visits: no plan at entry (the import's record, or the insurance check's record for an older batch), exactly one open MEDICAL plan now (a dental plan does not count)",
      e == "" and sorted(c_["member"] for c_ in ELIG["calls"]) == ["M951", "M953", "M955"], (e, ELIG["calls"], o[-500:]))
check("8.6 the listing says who decides the others: two open medical plans, or a plan at entry -> William", "for William: the chart has 2 open medical plans now - exactly one is needed" in top(o, "vst9402") and "for William: it had an open plan when it was entered" in top(o, "vst9404")
      and "standing word: saved once every check passes" in top(o, "vst9401") and "the owner's approved file: send" in top(o, "vst9406"), [top(o, v_) for v_ in ("vst9402", "vst9404")])
o, e = sweep("--resave", "--standing", "--live"); _rs = sreg("resave")
check("8.6 --resave --standing --live saves WITHOUT an approved file exactly the standing-word visits, each after every check (dated proof included); the register says 'standing word, William 11/10/2026'",
      e == "" and [len(W[0].v["vst940%d" % i_].saves) for i_ in range(1, 7)] == [1, 0, 1, 0, 1, 0] and all(W[0].v[v_].lst == "1" for v_ in ("vst9401", "vst9403", "vst9405"))
      and sorted(r_["visit"] for r_ in _rs[-1]["rows"] if r_.get("mode") == "standing word, William 11/10/2026" and r_.get("ok")) == ["vst9401", "vst9403", "vst9405"], (e, o[-700:]))
check("8.6 a visit the owner's approved file names is never saved by the standing word (the file decides it)", W[0].v["vst9406"].saves == [], o[-300:])
# the two-plan chart: the ONE plan the dated checks show active on the date decides the order; both active -> William
_two = [{"carrier": "UNI20", "seq": "1"}, {"carrier": "FLO02", "seq": "2"}]; _ob = {"decision": "order_by_dated_check", "order_candidates": ["1", "2"], "plans_in_force_today": _two}
W[0] = SWorld({"961": [{"id": "ins9611", "car": "car300", "seq": "1", "member": "U961"}, {"id": "ins9612", "car": "car6085", "seq": "2", "member": "M961"}],
               "962": [{"id": "ins9621", "car": "car300", "seq": "1", "member": "U962"}, {"id": "ins9622", "car": "car6085", "seq": "2", "member": "M962"}]}, SW("vst9501", [chg(95011)]), SW("vst9502", [chg(95021)]))
ws9([srow("vst9501", "pat961", "10/15/2026", ["99309"], ["charge95011"]), srow("vst9502", "pat962", "10/16/2026", ["99309"], ["charge95021"])], recon={"vst9501": DOC, "vst9502": DOC},
    approved={"vst9501": _ob, "vst9502": _ob}, seed=[PILOT_DONE])
ELIG["ans"] = {("87726", "U961", "20261015"): {"planStatus": [{"statusCode": "6", "status": "Inactive"}]}, ("CMS", "M961", "20261015"): PARTB(),
               ("87726", "U962", "20261016"): {"planStatus": [{"statusCode": "1", "status": "Active Coverage"}]}, ("CMS", "M962", "20261016"): PARTB()}
o, e = sweep("--coverage", "--approved", APPF, "--live"); o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.5 the two-plan chart: a check of each plan dated to the service date; the one shown active (Medicare, sequence 2) is the order - saved, list [2]",
      e == "" and len(ELIG["calls"]) == 4 and len(W[0].v["vst9501"].saves) == 1 and 'insorder="2"' in W[0].v["vst9501"].saves[0] and W[0].v["vst9501"].lst == "2", (e, o[-500:]))
check("8.5 both plans active on the date -> William decides, nothing saved", W[0].v["vst9502"].saves == [] and "both plans answer active on 10/16/2026 - William decides the order" in o, o[-400:])
# the other checks of a save, one at a time: the deceased guard, the plan the file names, AdvancedMD's plan dates, the admission date, a billed sibling
W[0] = SWorld({"971": med("971", "M971"), "972": med("972", "M972"), "973": [{"id": "ins973", "car": "car6085", "seq": "1", "member": "M973", "begin": "10/30/2026"}], "974": med("974", "M974"), "975": med("975", "M975"),
               "976": med("976", "M976"), "977": med("977", "M977"), "978": med("978", "M978")},
    SW("vst9701", [chg(97011)]), SW("vst9702", [chg(97021)]), SW("vst9703", [chg(97031)]), SW("vst9704", [chg(97041, cpt="99232", pcode="pcode65102")], admit="10/29/2026"),
    SW("vst9705", [chg(97051), chg(97052, cpt="99497", pcode="pcode65299", pays=[{"amount": "12.00"}])]), SW("vst9706", [chg(97061)]), SW("vst9707", [chg(97071)]), SW("vst9708", [chg(97081), chg(97082, cpt="99497", pcode="pcode65299", void=True)]))
ws9([srow("vst970%d" % i_, "pat97%d" % i_, "10/2%d/2026" % i_, ["99232"] if i_ == 4 else ["99309"], ["charge970%d1" % i_] + (["charge97082"] if i_ == 8 else [])) for i_ in range(1, 9)], recon=dict({"vst970%d" % i_: DOC for i_ in range(1, 9)}, vst9706=NPL),
    approved={"vst9701": _send, "vst9702": dict(_send, plans_in_force_today=[{"carrier": "UNI20", "seq": "1"}]), "vst9703": _send, "vst9704": _send, "vst9705": _send, "vst9706": _send,
              "vst9707": dict(_send, order="2", plans_in_force_today=[]), "vst9708": _send}, seed=[PILOT_DONE])
DGB.add("971"); o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.2 the deceased guard blocks a save", e == "" and W[0].v["vst9701"].saves == [] and "the deceased guard blocks it (test)" in o, o[-900:])
check("8.2 a plan at the lead sequence that is not the carrier the owner's file names: not saved (never a claim to another payer than he approved)", W[0].v["vst9702"].saves == [] and "the plan at sequence 1 is FLO02 now - the approved file names UNI20" in o, o[-900:])
check("8.2 AdvancedMD's plan begins after the date of service: not saved", W[0].v["vst9703"].saves == [] and "AdvancedMD's plan at sequence 1 begins 10/30/2026, after the service date" in o, o[-900:])
check("8.2 an admission date that is not sane (after the date of service) on a follow-up visit of a chart with no initial hospital visit of ours: not saved (11/25/2026: an initial visit in that state gets its own date - the NEW ADMISSION checks below)", W[0].v["vst9704"].saves == [] and "for William: its admission date 10/29/2026 is after its service date 10/24/2026" in o, o[-900:])
check("8.2 a payment on a charge the import register does not list (read just now through every live charge): never saved", W[0].v["vst9705"].saves == [] and "billed, paid or a balance on the patient on one of its 2 live charges" in o, o[-500:])
check("8.2/8.4 the entered clinician must be the one the feed names: the nurse practitioner's visit under the physician is not saved", W[0].v["vst9706"].saves == [] and "entered under the physician (prof13), but the feed names the nurse practitioner (prof15)" in o, o[-900:])
check("8.2 exactly one open plan at the lead sequence: an order whose plan the chart does not have is not saved", W[0].v["vst9707"].saves == [] and "0 open plan(s) at sequence 2 - exactly one is needed" in o, o[-900:])
check("8.2 a charge the import entered that now reads void (not a no-charge line): not saved - a person reads the visit first", W[0].v["vst9708"].saves == [] and "charge(s) the import entered now read void: charge97082" in o, o[-600:])
# 11/25/2026 (the independent check of the death check's second round, its new finding 1 - a regression). Since that day the guard RAISES when a death is on record for a
# chart and nobody can name its day (DayLost), and any guard call can end in an error of another kind (the chart could not be read, a time-out). The sweep let the error
# out of its deceased check: the run ended 'DID NOT FINISH' at the first such visit and the visits of OTHER charts behind it were never saved - in every run, until
# somebody named the day. Now the error is caught PER VISIT: that one visit is refused in fixed words - the error by its kind, never by its own words (they can name a
# patient) - in the sweep's own way of refusing a visit, and the sweep goes on with the next visit.
class DayLost(RuntimeError): pass      # the guard's own error for such a chart: the sweep knows an error by the name of its kind only
SECRET_WORDS = "ZZSECRET-WORDS-OF-THE-ERROR"      # what the error itself says - never printed, never written
UNCHECKED = "for William: the date of death could not be checked (%s) - nothing is sent for this visit on this run"
def lost_world(world=None):
    W[0] = (world or SWorld)({"661": med("661", "M661"), "662": med("662", "M662"), "663": med("663", "M663")}, SW("vst6601", [chg(66011)]), SW("vst6602", [chg(66021)]), SW("vst6603", [chg(66031)]))
    ws9([srow("vst6601", "pat661", "10/12/2026", ["99309"], ["charge66011"]), srow("vst6602", "pat662", "10/13/2026", ["99309"], ["charge66021"]), srow("vst6603", "pat663", "10/14/2026", ["99309"], ["charge66031"])],
        recon={"vst6601": DOC, "vst6602": DOC, "vst6603": DOC}, approved={"vst6601": _send, "vst6602": _send, "vst6603": _send}, seed=[PILOT_DONE])
def saves66(): return [len(W[0].v[v_].saves) for v_ in ("vst6601", "vst6602", "vst6603")]
_dc0 = os.environ.pop("DECEASED_CACHE", None)      # the runs below start with NO cache named by the environment: what the guard is asked under shows whether the sweep names one itself
try:
    lost_world(); o, e = sweep("--resave", "--approved", APPF, "--live")
    check("D1 control: three approved stuck visits of three charts and a guard that raises for none - all three are saved", e == "" and saves66() == [1, 1, 1] and len(DGC) == 3, (e, saves66(), o[-500:]))
    check("s01 the sweep names no cache file of its own (the line os.environ.setdefault('DECEASED_CACHE', ...) of before must not come back - the guard keeps ONE cache): its guard is asked with the environment as the run has it, and no such line is in its code",
          len(DGC) == 3 and all(c_[5] is None for c_ in DGC) and not re.search(r"environ\.setdefault\(\s*[\"']DECEASED_CACHE", SSRC) and "deceased_cache_local" not in "\n".join(l_.split("#")[0] for l_ in SSRC.splitlines()), [c_[5] for c_ in DGC])
    lost_world(); DGR["662"] = DayLost(SECRET_WORDS); o, e = sweep("--resave", "--approved", APPF, "--live"); _r6 = {r_["visit"]: r_ for j_ in sreg("resave") for r_ in j_.get("rows") or []}
    check("D1 the guard raises DayLost for the SECOND visit's chart (a death on record whose day nobody can name): that ONE visit is not saved, and the visits of the other charts - the one before it AND the one behind it - are saved; the run finishes",
          e == "" and saves66() == [1, 0, 1] and "FEED ORDER SWEEP DID NOT FINISH" not in o and "Feed order saves: 2 saved and read back, 1 not saved" in o and (sreg("sweep") or [{}])[-1].get("finished") is True, (e, saves66(), o[-900:]))
    check("D1 ... the visit is refused the sweep's own way - 'FEED ORDER SAVE - not saved', its register row says refused and not sent, its TOP line says what this run did - in fixed words that name the error by its KIND; the error's own words are nowhere",
          "FEED ORDER SAVE - not saved: pat662 vst6602 10/13/2026 (the owner's approved file (send)) - " + UNCHECKED % "DayLost" in o and _r6.get("vst6602", {}).get("refused") == UNCHECKED % "DayLost" and _r6["vst6602"].get("sent") is False
          and top(o, "vst6602").endswith("| this run: " + UNCHECKED % "DayLost") and SECRET_WORDS not in o and SECRET_WORDS not in json.dumps(sreg("resave") + sreg("sweep")), (o[-900:], _r6.get("vst6602")))
    o, e = sweep("--resave", "--approved", APPF, "--live"); _s2 = saves66(); DGR.clear(); o2, e2 = sweep("--resave", "--approved", APPF, "--live")
    check("D1 ... the next run asks again and refuses that visit again (nothing else is sent twice); once the guard answers, the visit is saved",
          e == "" and _s2 == [1, 0, 1] and "FEED ORDER SAVE - not saved: pat662 vst6602" in o and e2 == "" and saves66() == [1, 1, 1] and "FEED ORDER SAVE: pat662 vst6602 10/13/2026" in o2, (e, _s2, e2, saves66(), o2[-500:]))
    lost_world(); DGR["661"] = TimeoutError(SECRET_WORDS); o, e = sweep("--resave", "--approved", APPF, "--live")
    check("D1 an error of ANOTHER kind (a time-out) for the FIRST visit's chart: the same - that visit is refused by the error's kind and the two visits behind it are saved (0 of 3 were saved before)",
          e == "" and saves66() == [0, 1, 1] and "FEED ORDER SWEEP DID NOT FINISH" not in o and "FEED ORDER SAVE - not saved: pat661 vst6601 10/12/2026 (the owner's approved file (send)) - " + UNCHECKED % "TimeoutError" in o and SECRET_WORDS not in o, (e, saves66(), o[-900:]))
    lost_world(); DGR["662"] = DayLost(SECRET_WORDS); o, e = sweep("--resave", "--approved", APPF)
    check("D1 a DRY run the same: the guard is asked from its cache only, the visit it raises for is 'not saved' in the same words, the other two 'would be saved' - and nothing is sent",
          e == "" and saves66() == [0, 0, 0] and [c_[4] for c_ in DGC] == [False] * 3 and o.count("FEED ORDER SAVE (dry run): would save ") == 2 and "FEED ORDER SAVE - not saved: pat662 vst6602 10/13/2026 (the owner's approved file (send)) - " + UNCHECKED % "DayLost" in o, (e, saves66(), DGC, o[-900:]))
    W[0] = SWorld({"664": med("664", "M664"), "665": med("665", "M665")}, SW("vst6604", [chg(66041)], move_builds=False), SW("vst6605", [chg(66051)], move_builds=False))
    ws9([srow("vst6604", "pat664", "10/12/2026", ["99309"], ["charge66041"]), srow("vst6605", "pat665", "10/13/2026", ["99309"], ["charge66051"])], recon={"vst6604": NPL, "vst6605": NPL},
        approved={"vst6604": _mv, "vst6605": _mv}, seed=[MOVE_DONE, PILOT_DONE])
    DGR["664"] = DayLost(SECRET_WORDS); o, e = sweep("--fix-clinician", "--approved", APPF, "--live"); _m6 = {m_["visit"]: m_ for j_ in sreg("fixclin") for m_ in j_.get("moves") or []}
    check("D1 the clinician moves the same: the guard raises for the first visit's chart - that visit is NOT moved ('FEED ORDER CLINICIAN - not moved', refused and not sent in its row, the error by its kind) and the visit of the other chart behind it IS moved",
          e == "" and W[0].v["vst6604"].moves == [] and len(W[0].v["vst6605"].moves) == 1 and "FEED ORDER SWEEP DID NOT FINISH" not in o
          and "FEED ORDER CLINICIAN - not moved: pat664 vst6604 10/12/2026 - " + UNCHECKED % "DayLost" in o and _m6.get("vst6604", {}).get("refused") == UNCHECKED % "DayLost" and _m6["vst6604"].get("sent") is False and SECRET_WORDS not in o + json.dumps(sreg("fixclin")),
          (e, [len(W[0].v[v_].moves) for v_ in ("vst6604", "vst6605")], o[-900:]))
    # ... and with the REAL guard (scripts/helpers/deceased_guard.py - a copy loaded from the sandbox folder, so every module it loads beside itself is a stand-in of this
    # self-test or is not there; the network is shut either way): its cache holds the privacy gate's placeholder for the second chart, and nobody can name the day
    class SWorldG(SWorld):      # the real guard asks for a chart by its digits (patientid="662"); the stand-in world reads pat662
        def post(self, body, timeout=0): return SWorld.post(self, re.sub(r'patientid="(\d+)"', r'patientid="pat\1"', body), timeout)
    import importlib.util as _ilu
    lost_world(SWorldG); _gp = os.path.join(SWD[0], "deceased_guard.py"); open(_gp, "w").write(open(os.path.join(HELPERS, "deceased_guard.py")).read())
    json.dump({"662": {"dod": "[" + "DOB" + "]", "checked": (NOW - datetime.timedelta(days=30)).strftime("%Y-%m-%d"), "src": "x"}}, open(os.path.join(SWD[0], "registers", "deceased_cache.json"), "w"))
    _path0 = list(sys.path); _gsp = _ilu.spec_from_file_location("deceased_guard_real_d1", _gp); _g = _ilu.module_from_spec(_gsp); _gsp.loader.exec_module(_g); _old = SSTAND["deceased_guard"]; SSTAND["deceased_guard"] = {"check": _g.check}
    try: o, e = sweep("--resave", "--approved", APPF, "--live")
    finally: SSTAND["deceased_guard"] = _old; sys.path[:] = _path0
    check("D1 with the REAL guard: a chart whose cache entry is the placeholder (a death on record, its day not readable here) and nobody names the day - the guard raises its own DayLost, that visit is refused in the fixed words, and the visits of the two other charts are saved (the checker's own case: 1 of 3, then the run stopped)",
          e == "" and _g.CACHE == os.path.join(SWD[0], "registers", "deceased_cache.json") and saves66() == [1, 0, 1] and "FEED ORDER SWEEP DID NOT FINISH" not in o
          and "FEED ORDER SAVE - not saved: pat662 vst6602 10/13/2026 (the owner's approved file (send)) - " + UNCHECKED % "DayLost" in o and not any(m_ in sys.modules for m_ in ("medicare_store", "elig_amd")), (e, getattr(_g, "CACHE", None), saves66(), o[-900:]))
finally:
    if _dc0 is not None: os.environ["DECEASED_CACHE"] = _dc0
# the cap: 121 visits on one chart, each its own date -> 120 checks bought ($36.00), one waits for the next run
W[0] = SWorld({"981": med("981", "M981")}, *[SW("vst98%03d" % i_, [chg(980000 + i_)]) for i_ in range(121)])
_d0 = datetime.date(2026, 6, 1)
ws9([srow("vst98%03d" % i_, "pat981", (_d0 + datetime.timedelta(days=i_)).strftime("%m/%d/%Y"), ["99309"], ["charge%d" % (980000 + i_)], **_np) for i_ in range(121)], recon={"vst98%03d" % i_: DOC for i_ in range(121)}, approved={})
o, e = sweep("--coverage", "--live")
check("8.5 the cap: 120 checks a run ($36.00 - under the $40 cap), the rest wait for the next run", e == "" and len(ELIG["calls"]) == 120 and "120 eligibility check(s) dated to the service date bought - $36.00" in o and "1 wait for the next run (cap reached)" in o, (e, len(ELIG["calls"]), o[-300:]))
# vendor answers: errors are asked at most twice; a carrier the vendor cannot check buys nothing; a plan date equal to the birth date is neither used nor written
W[0] = SWorld({"991": med("991", "M991"), "992": [{"id": "ins992", "car": "car600", "seq": "1", "member": "M992"}], "993": med("993", "M993")}, SW("vst9901", [chg(99011)]), SW("vst9902", [chg(99021)]), SW("vst9903", [chg(99031)]))
ws9([srow("vst9901", "pat991", "10/20/2026", ["99309"], ["charge99011"], **_np), srow("vst9902", "pat992", "10/21/2026", ["99309"], ["charge99021"], **_np), srow("vst9903", "pat993", "10/22/2026", ["99309"], ["charge99031"], **_np)],
    recon={"vst9901": DOC, "vst9902": DOC, "vst9903": DOC}, seed=[PILOT_DONE], approved={})
ELIG["ans"] = {("CMS", "M993", "20261022"): dict(PARTB(), planDateInformation={"planBegin": BD8, "planEnd": BD8})}
for _i in range(3): o, e = sweep("--coverage", "--live")
check("8.5 an error answer is asked again once, never a third time; a carrier the vendor has no route for buys nothing and is not tried again", e == "" and [c_["member"] for c_ in ELIG["calls"]].count("M991") == 2 and "M992" not in [c_["member"] for c_ in ELIG["calls"]]
      and "the vendor has no eligibility route for ZZZ01 - nothing was bought" in json.dumps(sreg("coverage")), [c_["member"] for c_ in ELIG["calls"]])
_c3 = [a_ for j_ in sreg("coverage") for a_ in j_.get("answers") or [] if a_.get("visit") == "vst9903"]
check("8.5 a plan date equal to the birth date is a placeholder: the answer still counts (active on the date), and that date is written nowhere", len(_c3) == 1 and _c3[0]["active"] == "yes" and not re.search("%s|%s" % (BD8, re.escape(BDS)), json.dumps(sreg("coverage")) + o), _c3)
o, e = sweep("--resave", "--standing", "--live")
check("8.5/8.6 an error is never proof: that visit is not saved; the one with a dated active answer is", W[0].v["vst9901"].saves == [] and W[0].v["vst9902"].saves == [] and len(W[0].v["vst9903"].saves) == 1, o[-600:])
# the answer itself (verdict), lifted out of the sweep's source text
SVN = {"re": re}; exec(lift(SWP, {"d8", "mdy", "verdict", "ACTIVE", "MA_TYPES", "NOT_MEDICAL", "LIMITED", "DRUG_ONLY", "MEDICAL_TOO", "CARRIER_NOT_MEDICAL", "not_medical"}), SVN); vd = SVN["verdict"]
check("8.5 verdict: an active answer that limits the coverage (Florida Medicaid's family-planning class) or names a dental / drug-only plan is not proof -> no (William)",
      vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "FP | Limited to family planning services"}]}, "20261015", False)[0] == "no"
      and vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "Dental PPO"}]}, "20261015", False)[0] == "no"
      and vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "TRICARE FOR LIFE"}]}, "20261015", False)[0] == "yes")
check("8.5 verdict: active status -> yes; inactive -> no; an error -> error; active and inactive mixed -> error (William)",
      [vd(x_, "20261015", False)[0] for x_ in ({"planStatus": [{"statusCode": "1"}]}, {"planStatus": [{"statusCode": "6"}]}, {"errors": [{"code": "62", "description": "x"}]}, {"planStatus": [{"statusCode": "1"}, {"statusCode": "6"}]}, {})] == ["yes", "no", "error", "error", "error"])
check("8.5 verdict: the plan's own dates that do not cover the date of service -> no", vd({"planStatus": [{"statusCode": "1"}], "planDateInformation": {"planBegin": "20261020"}}, "20261015", False)[0] == "no"
      and vd({"planStatus": [{"statusCode": "1"}], "planDateInformation": {"plan": "20260101-20261001"}}, "20261015", False)[0] == "no" and vd({"planStatus": [{"statusCode": "1"}], "planDateInformation": {"plan": "20260101-20261231"}}, "20261015", False)[0] == "yes")
_ma = dict(PARTB(), benefitsInformation=PARTB()["benefitsInformation"] + [{"code": "R", "insuranceTypeCode": "HN", "benefitsRelatedEntities": [{"entityName": "SOME ADVANTAGE PLAN"}]}])
check("8.5 verdict (Medicare): Part B active on the date -> yes; a Medicare Advantage plan named for the date -> no (its name said); no Part B -> no; a Part D entry (type OT) is not a payer",
      vd(PARTB(), "20261015", True)[0] == "yes" and vd(_ma, "20261015", True)[:2] == ("no", "Medicare names another primary payer on 10/15/2026: SOME ADVANTAGE PLAN")
      and vd({"planStatus": [{"statusCode": "1"}], "benefitsInformation": [{"code": "1", "insuranceTypeCode": "MA"}]}, "20261015", True)[0] == "no"
      and vd(dict(PARTB(), benefitsInformation=PARTB()["benefitsInformation"] + [{"code": "R", "insuranceTypeCode": "OT"}]), "20261015", True)[0] == "yes")
check("B / R7-REPLAY-4 / OPS-6 the sweep's dated proof: an active answer naming a Medicare Advantage plan WITH drug coverage is proof (yes); a stand-alone drug plan is not (no)",
      vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "UHC MEDICARE ADVANTAGE PRESCRIPTION DRUG (MAPD) HMO"}]}, "20261015", False)[0] == "yes"
      and vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "AARP MEDICARE ADVANTAGE PRESCRIPTION DRUG (HMO)"}]}, "20261015", False)[0] == "yes"
      and vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "HUMANA WALMART VALUE RX PLAN (PDP)"}]}, "20261015", False)[0] == "no"
      and vd({"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "Prescription Drug Plan"}]}, "20261015", False)[0] == "no")
# NH7-1 (blocker): the clinician move carries the CHECKED order - the two-plan chart shaped like the owner's vst19459210 / vst19459257 (UHC seq 1 not active, Medicare seq 2 active)
_obm = dict(_ob, clinician="prof15")
W[0] = SWorld({"963": [{"id": "ins9631", "car": "car300", "seq": "1", "member": "U963"}, {"id": "ins9632", "car": "car6085", "seq": "2", "member": "M963"}],
               "964": [{"id": "ins9641", "car": "car300", "seq": "1", "member": "U964"}, {"id": "ins9642", "car": "car6085", "seq": "2", "member": "M964"}]},
              SW("vst9601", [chg(96011)]), SW("vst9602", [chg(96021)], move_list="1"))
ws9([srow("vst9601", "pat963", "10/15/2026", ["99309"], ["charge96011"]), srow("vst9602", "pat964", "10/16/2026", ["99309"], ["charge96021"])], recon={"vst9601": NPL, "vst9602": NPL},
    approved={"vst9601": _obm, "vst9602": _obm}, seed=[PILOT_DONE, MOVE_DONE])
ELIG["ans"] = {("87726", "U963", "20261015"): {"planStatus": [{"statusCode": "6", "status": "Inactive"}]}, ("CMS", "M963", "20261015"): PARTB(),
               ("87726", "U964", "20261016"): {"planStatus": [{"statusCode": "6", "status": "Inactive"}]}, ("CMS", "M964", "20261016"): PARTB()}
o, e = sweep("--coverage", "--approved", APPF, "--live"); o, e = sweep("--fix-clinician", "--resave", "--approved", APPF, "--live"); s61 = W[0].v["vst9601"]; s62 = W[0].v["vst9602"]
check("NH7-1 the move of a two-plan visit (order 2 by the dated checks, attribute 1) carries insorder 2 - never the old attribute 1 - and the list it builds reads [2]: billable as approved, no TOP line any more",
      e == "" and len(s61.moves) == 1 and 'insorder="2"' in s61.moves[0] and s61.lst == "2" and not top(o, "vst9601") and s61.saves == [], (e, s61.moves[:1], s61.lst, o[-500:]))
check("NH7-1 a move that builds ANOTHER list than the checked order ([1], the plan the dated check showed not active) is an unexpected read-back: the run stops and says so at the top",
      len(s62.moves) == 1 and 'insorder="2"' in s62.moves[0] and s62.lst == "1" and "TOP OF THE REPORT - FEED ORDER SWEEP STOPPED at pat964 vst9602: the move built insurance order [1], not the checked order [2]" in o, (s62.lst, o[-700:]))
_f = sorted(glob.glob(os.path.join(SWD[0], "registers", "feed_order_fixclin_*.json")))[-1]; _j = json.load(open(_f))
for r_ in _j["moves"]:
    if r_.get("unexpected"): r_["cleared"] = "a person, after looking at the visit (test)"
json.dump(_j, open(_f, "w"))
o, e = sweep("--resave", "--approved", APPF, "--live")
check("NH7-1 once a person cleared that stop, the moved visit on the wrong order is listed ('NOT THE CHECKED INSURANCE ORDER ... reads [1], the checked order is [2]') and the save sets [2] - it is never left to bill the inactive plan",
      e == "" and len(s62.saves) == 1 and 'insorder="2"' in s62.saves[0] and s62.lst == "2" and "1 moved visit(s) on another insurance order than the checked one" in o and "FEED ORDER SAVE: pat964 vst9602" in o, (e, s62.lst, o[-700:]))
# NH7-3 / OPS-2: the save lands, its answer never comes back; a run cut off from outside; a visit saved earlier whose admission date is gone since
W[0] = SWorld({"965": med("965", "M965"), "966": med("966", "M966")}, SW("vst9651", [chg(96511, cpt="99223", pcode="pcode65101")], admit="10/14/2026", wipe=True, raise_after=TimeoutError("read timed out")), SW("vst9652", [chg(96521)]))
ws9([srow("vst9651", "pat965", "10/14/2026", ["99223"], ["charge96511"], admit="20261014"), srow("vst9652", "pat966", "10/15/2026", ["99309"], ["charge96521"])], recon={"vst9651": DOC, "vst9652": DOC},
    approved={"vst9651": _send, "vst9652": _send}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live"); _rs = sreg("resave")
check("NH7-3 a hospital visit's save lands but its answer never comes back: the sweep does not crash - it reads the visit again, writes the wiped admission date back, records the row as unexpected and stops (the next visit is not saved)",
      e == "" and W[0].v["vst9651"].admit == "10/14/2026" and W[0].v["vst9652"].saves == [] and "TOP OF THE REPORT - FEED ORDER SWEEP STOPPED at pat965 vst9651" in o
      and any(r_.get("visit") == "vst9651" and r_.get("unexpected") and r_.get("sent") for j_ in _rs for r_ in j_.get("rows") or []), (e, o[-700:]))
class SWR(SW):      # after its save, every read of this visit times out (the sweep's own read-back fails, not only set_insorder's)
    def detail(self, cid):
        if self.saves: raise TimeoutError("read timed out (test)")
        return SW.detail(self, cid)
W[0] = SWorld({"962": med("962", "M962"), "966": med("966", "M966")}, SWR("vst9621", [chg(96211)]), SW("vst9622", [chg(96221)]))
ws9([srow("vst9621", "pat962", "10/14/2026", ["99309"], ["charge96211"]), srow("vst9622", "pat966", "10/15/2026", ["99309"], ["charge96221"])], recon={"vst9621": DOC, "vst9622": DOC},
    approved={"vst9621": _send, "vst9622": _send}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live"); _rs = sreg("resave")
check("NH7-3 the sweep's own read-back fails after the save landed: caught - the row says what failed (not only that the run ended), the run stops, the next visit is not saved",
      e == "" and W[0].v["vst9622"].saves == [] and any(r_.get("visit") == "vst9621" and str(r_.get("unexpected") or "").startswith("the save or its read-back failed (TimeoutError") for j_ in _rs for r_ in j_.get("rows") or []), (e, [r_ for j_ in _rs for r_ in j_.get("rows") or []][-2:]))
W[0] = SWorld({"967": med("967", "M967"), "968": med("968", "M968")}, SW("vst9671", [chg(96711)], raise_after=SystemExit("stopped from outside (test)")), SW("vst9672", [chg(96721)]))
ws9([srow("vst9671", "pat967", "10/14/2026", ["99309"], ["charge96711"]), srow("vst9672", "pat968", "10/15/2026", ["99309"], ["charge96721"])], recon={"vst9671": DOC, "vst9672": DOC},
    approved={"vst9671": _send, "vst9672": _send}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live"); _rs = sreg("resave"); _sw = sreg("sweep")
check("OPS-2 a run cut off from outside right after a save landed: that save's row was written BEFORE the save and still says unexpected, the sweep's register is written, the top of the report says the run did not finish, and the TOP lines are still printed",
      any(r_.get("visit") == "vst9671" and r_.get("unexpected") for j_ in _rs for r_ in j_.get("rows") or []) and len(_sw) == 1 and _sw[0].get("finished") is False
      and "TOP OF THE REPORT - FEED ORDER SWEEP DID NOT FINISH: it was stopped from outside" in o and top(o, "vst9672") != "", o[-800:])
check("OPS-8 the sweep names every register it wrote (its own stamp) - the routine commits every one", any(l_.startswith("registers written this run - commit every one: ") and "feed_order_resave_" in l_ and "feed_order_sweep_" in l_ for l_ in o.splitlines()), o[-300:])
o, e = sweep("--resave", "--approved", APPF, "--live")
check("OPS-2 ... and the next run STOPS on that row: nothing more is saved until a person has looked at the visit", W[0].v["vst9672"].saves == [] and "TOP OF THE REPORT - FEED ORDER SWEEP STOPPED: an earlier save or move did not read back as asked: vst9671" in o, o[-500:])
class SWX(SW):      # its charge detail is answered by the run being stopped from outside (a time limit while the listing runs)
    def detail(self, cid): raise SystemExit("stopped from outside (test)")
W[0] = SWorld({"978": med("978", "M978")}, SW("vst9781", [chg(97811, attrs={"datebilled": "10/20/2026", "insbilled": "1"})], lst="1"), SWX("vst9782", [chg(97821)]))
ws9([srow("vst9781", "pat978", "10/12/2026", ["99309"], ["charge97811"]), srow("vst9782", "pat978", "10/13/2026", ["99309"], ["charge97821"])], recon={"vst9781": DOC, "vst9782": DOC}, approved={})
o, e = sweep(); _sw = sreg("sweep")
check("OPS-2 a run stopped from outside while it lists: one TOP line says so, and the visits it saw billed are kept in its register (the next run does not read them again)",
      "TOP OF THE REPORT - FEED ORDER SWEEP DID NOT FINISH: it was stopped from outside while listing" in o and len(_sw) == 1 and _sw[0].get("billed") == ["vst9781"], (o[-400:], _sw))
W[0] = SWorld({"969": med("969", "M969")}, SW("vst9691", [chg(96911, cpt="99223", pcode="pcode65101")], lst="1", admit=""))
ws9([srow("vst9691", "pat969", "10/14/2026", ["99223"], ["charge96911"], admit="20261014")], recon={"vst9691": DOC}, approved={"vst9691": _send},
    seed=[("feed_order_resave_20261102T000000Z.json", {"rows": [{"visit": "vst9691", "sent": True, "ok": True, "admit_before": "10/14/2026", "list_after": "1"}]})])
o, e = sweep()
check("OPS-2/NH7-3 a visit an earlier run saved (its list filled, not billed yet) is read again until it bills: its admission date, gone since that save, gets a TOP line for a person",
      e == "" and "TOP OF THE REPORT - FEED ORDER SWEEP - ADMISSION DATE LOST: pat969 vst9691 service date 10/14/2026: its admission date read 10/14/2026 before this helper's save" in o, o[-600:])
# R7-REPLAY-2: two admission dates ONE day apart in one stay (the reviewer's exact shape) - both listed with it, neither saved; NH7-4 in the listing: 99497 first, the date on the 99223
W[0] = SWorld({"970": med("970", "M970"), "974": med("974", "M974"), "977": med("977", "M977"), "978": med("978", "M978")}, SW("vst9801", [chg(98011, cpt="99223", pcode="pcode65101")], admit="10/27/2026"), SW("vst9802", [chg(98021, cpt="99232", pcode="pcode65102")], admit="10/28/2026"),
              SW("vst9803", [chg(98031, cpt="99232", pcode="pcode65102", attrs={"datebilled": "11/02/2026", "insbilled": "1"})], lst="1", admit="10/28/2026"),
              SW("vst9804", [chg(98041, cpt="99497", pcode="pcode65299"), chg(98042, cpt="99223", pcode="pcode65101")], admit={"99223": "10/20/2026"}),
              SW("vst9805", [chg(98051, cpt="99223", pcode="pcode65101")], admit="10/20/2026"), SW("vst9806", [chg(98061, cpt="99232", pcode="pcode65102")], admit="10/25/2026"),
              SW("vst9807", [chg(98071, cpt="99232", pcode="pcode65102")], admit="10/29/2026"))      # chart 978: a follow-up whose only date lies AFTER it, and no initial hospital visit of ours on the chart
ws9([srow("vst9807", "pat978", "10/27/2026", ["99232"], ["charge98071"], admit="20261029"),
     srow("vst9801", "pat970", "10/27/2026", ["99223"], ["charge98011"], admit="20261027"), srow("vst9802", "pat970", "10/28/2026", ["99232"], ["charge98021"], admit="20261028"),
     srow("vst9803", "pat970", "11/01/2026", ["99232"], ["charge98031"], admit="20261028"), srow("vst9804", "pat974", "10/20/2026", ["99497", "99223"], ["charge98041", "charge98042"], admit="20261020"),
     srow("vst9805", "pat977", "10/27/2026", ["99223"], ["charge98051"], admit="20261020"), srow("vst9806", "pat977", "10/28/2026", ["99232"], ["charge98061"], admit="20261025")],
    recon={v_: DOC for v_ in ("vst9801", "vst9802", "vst9803", "vst9804", "vst9805", "vst9806", "vst9807")}, approved={"vst9801": _send, "vst9802": _send, "vst9807": _send}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live")
check("R7-REPLAY-2 (CHANGED 11/25/2026 - William settled it on 11/19: the rule's date, and send) two different admission dates within 3 days on one chart (the 99223 of 10/27 with 10/27, its follow-up with 10/28): both are named on the TOP lines, NEITHER is held - the 99223 is saved as it is, the follow-up's date is written 10/27 first and then it is saved",
      e == "" and top(o, "vst9801") == "" and top(o, "vst9802") == ""      # a visit this run saved and read back gets no TOP line
      and len(W[0].v["vst9801"].saves) == 1 and len(W[0].v["vst9802"].saves) == 1 and W[0].v["vst9802"].admit == "10/27/2026" and W[0].v["vst9801"].admit == "10/27/2026"
      and "for William: two admission dates in one stay" not in o, (top(o, "vst9801")[-400:], top(o, "vst9802")[-400:], W[0].v["vst9802"].admit, len(W[0].v["vst9801"].saves), len(W[0].v["vst9802"].saves)))
_rs = [r_ for g_ in sreg("resave") for r_ in g_.get("rows") or [] if r_.get("visit") == "vst9802"]
check("R7-REPLAY-2 ... the save's row says what was written: admit_write 10/27/2026, the date it read before, and the admission date read back after the save is the rule's",
      len(_rs) == 1 and _rs[0].get("admit_write") == "10/27/2026" and "it read 10/28/2026" in str(_rs[0].get("admit_before")) and _rs[0].get("admit_after") == "10/27/2026" and _rs[0].get("ok") is True, _rs)
check("8.1 (the builders' rule kept) two admission dates 5 days apart, both on or before both service dates, are still 'two admission dates in one stay'", "two admission dates in one stay: vst9805 10/20/2026, vst9806 10/25/2026" in top(o, "vst9805"), top(o, "vst9805"))
check("NH7-4 the listing reads each hospital code's admission date from its own charge: a 99497 + 99223 visit whose date sits on the 99223 is not 'a hospital visit with no admission date'", top(o, "vst9804") != "" and "no admission date" not in top(o, "vst9804"), top(o, "vst9804"))
check("OPS-5 a check only a person can clear says so: 'for William: ...' (here the one admission-date hold that remains - a follow-up whose only date lies after it, on a chart with no initial hospital visit of ours)",
      "FEED ORDER SAVE - not saved: pat978 vst9807 10/27/2026 (the owner's approved file (send)) - for William: its admission date 10/29/2026 is after its service date 10/27/2026" in o and W[0].v["vst9807"].saves == [], o[-900:])
# NEW ADMISSION - THE ADMISSION DATE IS SET BY THE STANDING RULE, NOT HELD (William 11/19/2026: "there will be some 99223 admission dates after follow up dates which will be
# valid"; 11/25/2026: "i now follow patients after dc from the inpatient hospital and admit them to inpatient rehab so code into the billing runs that that block is no longer
# valid to block a 99223 after a series of inpatient visits"). The shapes are the ones the feed really sends (the independent review of 11/25 replayed the import registers):
# the follow-ups of a stay carry a date a day LATER than their 99223; a second 99223 carries the FIRST stay's date; a 99223 carries the day after its own date; the follow-ups
# of a rehab stay arrive BEFORE its 99223 and carry the feed's later date.
_NA = ("vst9811", "vst9812", "vst9813", "vst9814", "vst9821", "vst9822", "vst9823", "vst9831", "vst9832", "vst9841", "vst9842")
W[0] = SWorld({"981": med("981", "M981"), "982": med("982", "M982"), "983": med("983", "M983"), "984": med("984", "M984")},
              # chart 981 - hospital 99223 10/20 (date 10/20) + follow-up 10/21 (date 10/20); rehab 99223 10/22 (date 10/22) + follow-up 10/23 carrying 10/23, a day late
              SW("vst9811", [chg(98111, cpt="99223", pcode="pcode65101")], admit="10/20/2026"), SW("vst9812", [chg(98121, cpt="99232", pcode="pcode65102")], admit="10/20/2026"),
              SW("vst9813", [chg(98131, cpt="99223", pcode="pcode65101")], admit="10/22/2026"), SW("vst9814", [chg(98141, cpt="99232", pcode="pcode65102")], admit="10/23/2026"),
              # chart 982 - the second 99223 (10/23, two days after the first stay's last visit) carries the FIRST stay's date 10/20; its follow-up 10/24 carries 10/20 too
              SW("vst9821", [chg(98211, cpt="99223", pcode="pcode65101")], admit="10/20/2026"), SW("vst9822", [chg(98221, cpt="99223", pcode="pcode65101")], admit="10/20/2026"),
              SW("vst9823", [chg(98231, cpt="99232", pcode="pcode65102")], admit="10/20/2026"),
              # chart 983 - a 99223 of 10/19 whose date reads 10/20, the day AFTER it; its follow-up of 10/20 carries 10/20
              SW("vst9831", [chg(98311, cpt="99223", pcode="pcode65101")], admit="10/20/2026"), SW("vst9832", [chg(98321, cpt="99232", pcode="pcode65102")], admit="10/20/2026"),
              # chart 984 - hospital 99223 10/06; a rehab follow-up of 10/15 that carries 10/14 arrives BEFORE the rehab stay's own 99223: the feed's later date stands
              SW("vst9841", [chg(98411, cpt="99223", pcode="pcode65101")], admit="10/06/2026"), SW("vst9842", [chg(98421, cpt="99233", pcode="pcode65103")], admit="10/14/2026"))
ws9([srow("vst9811", "pat981", "10/20/2026", ["99223"], ["charge98111"], admit="20261020"), srow("vst9812", "pat981", "10/21/2026", ["99232"], ["charge98121"], admit="20261020"),
     srow("vst9813", "pat981", "10/22/2026", ["99223"], ["charge98131"], admit="20261022"), srow("vst9814", "pat981", "10/23/2026", ["99232"], ["charge98141"], admit="20261023"),
     srow("vst9821", "pat982", "10/20/2026", ["99223"], ["charge98211"], admit="20261020"), srow("vst9822", "pat982", "10/23/2026", ["99223"], ["charge98221"], admit="20261020"),
     srow("vst9823", "pat982", "10/24/2026", ["99232"], ["charge98231"], admit="20261020"),
     srow("vst9831", "pat983", "10/19/2026", ["99223"], ["charge98311"], admit="20261020"), srow("vst9832", "pat983", "10/20/2026", ["99232"], ["charge98321"], admit="20261020"),
     srow("vst9841", "pat984", "10/06/2026", ["99223"], ["charge98411"], admit="20261006"), srow("vst9842", "pat984", "10/15/2026", ["99233"], ["charge98421"], admit="20261014")],
    recon={v_: DOC for v_ in _NA}, approved={v_: _send for v_ in _NA}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live")
_adm_now = {v_: W[0].v[v_].admit for v_ in _NA}; _saved = {v_: len(W[0].v[v_].saves) for v_ in _NA}
check("NEW ADMISSION (William 11/25/2026) no visit of these four charts is kept for William for its admission date - all eleven are saved", e == "" and all(n_ == 1 for n_ in _saved.values()) and "for William: two admission dates" not in o and "is after its service date" not in o, (e, _saved, o[-600:]))
check("NEW ADMISSION a hospital stay then a rehab stay with its own 99223: each stay keeps its own date; the rehab follow-up that carried a date a day late gets the rehab 99223's date, written before its save",
      [_adm_now[v_] for v_ in ("vst9811", "vst9812", "vst9813", "vst9814")] == ["10/20/2026", "10/20/2026", "10/22/2026", "10/22/2026"] and top(o, "vst9814") == "", ([_adm_now[v_] for v_ in ("vst9811", "vst9812", "vst9813", "vst9814")], top(o, "vst9814")[-300:]))
check("NEW ADMISSION a second 99223 that carries the FIRST stay's date gets its own date, and the follow-up after it gets that date too - the first stay's 99223 is untouched",
      [_adm_now[v_] for v_ in ("vst9821", "vst9822", "vst9823")] == ["10/20/2026", "10/23/2026", "10/23/2026"], [_adm_now[v_] for v_ in ("vst9821", "vst9822", "vst9823")])
check("NEW ADMISSION a 99223 whose date reads the day AFTER its own date gets its own date, and its follow-up - whose date is then one day after it - the same",
      [_adm_now[v_] for v_ in ("vst9831", "vst9832")] == ["10/19/2026", "10/19/2026"], [_adm_now[v_] for v_ in ("vst9831", "vst9832")])
check("NEW ADMISSION a rehab follow-up that arrives before the rehab stay's own 99223 KEEPS the feed's later date (10/14, eight days after the hospital 99223) - it is not pulled back to the hospital admission",
      [_adm_now[v_] for v_ in ("vst9841", "vst9842")] == ["10/06/2026", "10/14/2026"] and "becomes" not in top(o, "vst9842"), ([_adm_now[v_] for v_ in ("vst9841", "vst9842")], top(o, "vst9842")[-300:]))
_rs = {r_.get("visit"): r_ for g_ in sreg("resave") for r_ in g_.get("rows") or []}
check("NEW ADMISSION every save that wrote a date says so in its row (admit_write) and read the rule's date back after the save; a save that wrote none carries no such field",
      {v_: _rs[v_].get("admit_write") for v_ in _NA if _rs[v_].get("admit_write")} == {"vst9814": "10/22/2026", "vst9822": "10/23/2026", "vst9823": "10/23/2026", "vst9831": "10/19/2026", "vst9832": "10/19/2026"}
      and all(_rs[v_].get("ok") is True and _rs[v_].get("admit_after") == _adm_now[v_] for v_ in _NA), {v_: (_rs[v_].get("admit_write"), _rs[v_].get("admit_after"), _rs[v_].get("ok")) for v_ in _NA})
# ... a date that cannot be written: the order is NOT saved, nothing else is sent, and it is no STOP - the next run writes it again
W[0] = SWorld({"985": med("985", "M985")}, SW("vst9851", [chg(98511, cpt="99223", pcode="pcode65101")], admit="10/20/2026", restore=False))
ws9([srow("vst9851", "pat985", "10/19/2026", ["99223"], ["charge98511"], admit="20261020")], recon={"vst9851": DOC}, approved={"vst9851": _send}, seed=[PILOT_DONE])
o, e = sweep("--resave", "--approved", APPF, "--live")
check("NEW ADMISSION the rule's date cannot be written (AdvancedMD keeps the old one): the order is NOT saved, the line says why, no STOP is raised - the next run tries again",
      e == "" and W[0].v["vst9851"].saves == [] and "FEED ORDER SAVE - not saved: pat985 vst9851 10/19/2026 (the owner's approved file (send)) - its admission date could not be set to 10/19/2026 before the save (AdvancedMD refused it for 99223) - not saved, the next run tries again" in o and W[0].v["vst9851"].admit == "10/20/2026"
      and "FEED ORDER SWEEP STOPPED" not in o, (e, len(W[0].v["vst9851"].saves), o[-700:]))
o, e = sweep("--resave", "--approved", APPF)
check("NEW ADMISSION a dry run writes nothing and says which date the save would write first", e == "" and W[0].v["vst9851"].saves == [] and W[0].v["vst9851"].admit == "10/20/2026"
      and "FEED ORDER SAVE (dry run): would save pat985 vst9851 10/19/2026 insurance order 1 (the owner's approved file (send)) - its admission date 10/20/2026 -> 10/19/2026 first (the standing rule)" in o, o[-500:])
# ... the same rule on the sweep's own function, taken from its source (no AdvancedMD, no files): (visit, service date, admission date[, codes]) per visit of the chart
_asrc = SSRC[SSRC.index("def d8(x):"):SSRC.index("def jload(path):")] + SSRC[SSRC.index("def days_apart(a8, b8):"):SSRC.index("def approved(path):")]
_ans = {"re": re, "datetime": datetime, "resave": types.SimpleNamespace(HOSP_CODES=set(SRS["HOSP_CODES"]))}; exec(_asrc, _ans); _adm = _ans["admission"]
_I, _F = ["99223"], ["99232"]
check("NEW ADMISSION (the function) the date is right: nothing kept, nothing written - the 99223 on its own date, a follow-up carrying its 99223's date, a chart with no initial visit whose date is not after the visit",
      _adm("v1", "20261020", "20261020", _I, [("v1", "20261020", "20261020", _I)]) == ([], [], "") and _adm("v2", "20261021", "20261020", _F, [("v1", "20261020", "20261020", _I), ("v2", "20261021", "20261020", _F)]) == ([], [], "")
      and _adm("v2", "20261021", "20261019", _F, [("v2", "20261021", "20261019", _F)]) == ([], [], ""))
check("NEW ADMISSION (the function) the rule's date is written when the date is empty, after the service date, before the most recent initial visit, or the day after it - 99221, 99222 and 99223 alike",
      all(_adm("v2", "20261021", f_, _F, [("v1", "20261020", "20261020", [c_]), ("v2", "20261021", f_, _F)])[2] == "20261020" for f_ in ("", "20261022", "20261015", "20261021") for c_ in ("99221", "99222", "99223"))
      and _adm("v2", "20261021", "20261022", _F, [("v1", "20261020", "20261020", _I), ("v2", "20261021", "20261022", _F)])[0] == [])
check("NEW ADMISSION (the function) the feed's date stands when it is two or more days after the most recent initial visit and not after the service date (a later admission whose own initial visit is not on the chart yet)",
      _adm("v2", "20261015", "20261014", _F, [("v1", "20261006", "20261006", _I), ("v2", "20261015", "20261014", _F)]) == ([], [], "")
      and (lambda r_: r_[0] == [] and r_[2] == "")(_adm("v2", "20261015", "20261008", _F, [("v1", "20261006", "20261006", _I), ("v2", "20261015", "20261008", _F)])))
check("NEW ADMISSION (the function) an initial visit more than 45 days back anchors nothing: the feed's date stands; and the visit's OWN codes (the argument) make it an initial visit also when the chart list carries no codes",
      _adm("v2", "20261215", "20261210", _F, [("v1", "20261020", "20261020", _I), ("v2", "20261215", "20261210", _F)]) == ([], [], "")
      and _adm("v2", "20261022", "20261023", ["99497", "99223"], [("v1", "20261021", "20261020"), ("v2", "20261022", "20261023")])[2] == "20261022")
check("NEW ADMISSION (the function) the ONE hold that remains: a hospital visit for which no date can be named - no date at all, or only a date after the visit - on a chart with no initial hospital visit of ours in the 45 days before",
      _adm("v2", "20261021", "", _F, [("v2", "20261021", "", _F)]) == (["a hospital visit with no admission date"], [], "")
      and _adm("v2", "20261021", "20261022", _F, [("v2", "20261021", "20261022", _F)]) == (["its admission date 10/22/2026 is after its service date 10/21/2026"], [], ""))
check("NEW ADMISSION (the function) 'two admission dates in one stay' is said for the report and never keeps a visit; a visit with no hospital code is judged as before (only a date after its service date keeps it)",
      (lambda r_: r_[0] == [] and r_[1] == ["two admission dates in one stay: v1 10/27/2026, v2 10/28/2026 - not held for it (William 11/19/2026)"] and r_[2] == "")(_adm("v1", "20261030", "20261027", _F, [("v1", "20261030", "20261027", _F), ("v2", "20261031", "20261028", _F)]))
      and _adm("v9", "20261021", "20261022", ["99309"], [("v9", "20261021", "20261022", ["99309"])]) == (["its admission date 10/22/2026 is after its service date 10/21/2026"], [], "")
      and _adm("v9", "20261021", "", ["99309"], [("v1", "20261020", "20261020", _I), ("v9", "20261021", "", ["99309"])]) == ([], [], ""))
# R7-REPLAY-5 (the reviewer's exact input): a no-plan visit entered 31 days ago, its chart's first plan landed, the dated check active, not in the owner's file -> listed and saved by the standing word
W[0] = SWorld({"975": [{"id": "ins975", "car": "car300", "seq": "1", "member": "U975"}]}, SW("vst9751", [chg(97511)]), SW("vst9752", [chg(97521)]))
ws9([srow("vst9751", "pat975", "10/08/2026", ["99309"], ["charge97511"], days_ago=31, open_plans_at_entry=0, chart_insorder=""),
     srow("vst9752", "pat975", "10/01/2025", ["99309"], ["charge97521"], days_ago=400, open_plans_at_entry=0, chart_insorder="")], recon={"vst9751": DOC, "vst9752": DOC}, approved={}, seed=[PILOT_DONE])
ELIG["ans"] = {("87726", "U975", "20261008"): {"planStatus": [{"statusCode": "1", "status": "Active Coverage", "planDetails": "UHC MEDICARE ADVANTAGE (HMO)"}]}}
o, e = sweep("--coverage", "--resave", "--standing", "--live")
check("R7-REPLAY-5 a no-plan visit entered 31 days ago whose plan landed later is still listed and saved by the standing word (it went silent on day 31)", e == "" and len(W[0].v["vst9751"].saves) == 1 and W[0].v["vst9751"].lst == "1", (e, o[-600:]))
check("R7-REPLAY-5 ... a visit whose service date is older than the timely-filing year is not read", "97521" not in DREADS and W[0].v["vst9752"].saves == [], DREADS)
# OPS-7: Medicare + a Medigap carrier named '... LIFE ...' is TWO medical plans - the standing word does not save the visit with Medicare alone
W[0] = SWorld({"976": med("976", "M976", {"id": "ins9762", "car": "car800", "seq": "2", "member": "B976"})}, SW("vst9761", [chg(97611)]))
ws9([srow("vst9761", "pat976", "10/20/2026", ["99309"], ["charge97611"], open_plans_at_entry=0, chart_insorder="")], recon={"vst9761": DOC}, approved={}, seed=[PILOT_DONE])
ELIG["ans"] = {("CMS", "M976", "20261020"): PARTB()}
o, e = sweep("--coverage", "--resave", "--standing", "--live")
check("OPS-7 a chart with Medicare and a Bankers Life Medigap plan has 2 open medical plans: nothing bought, nothing saved (never Medicare alone with the secondary dropped) - listed for William",
      e == "" and W[0].v["vst9761"].saves == [] and ELIG["calls"] == [] and "for William: the chart has 2 open medical plans now - exactly one is needed" in top(o, "vst9761"), (e, top(o, "vst9761")))
# what the sweep refuses to start
W[0] = SWorld({"911": med("911", "M911")}, SW("vst9101", [chg(91011)])); ws9([srow("vst9101", "pat911", "10/15/2026", ["99309"], ["charge91011"])], recon={"vst9101": DOC})
o, e = sweep("--resave", "--live")
check("8.2 --resave without --approved <file> or --standing does nothing", e == "" and "--resave needs --approved <file>" in o and DREADS == [] and W[0].posts == [], o[-300:])
with open(os.path.join(SWD[0], "registers", "feed_order_approved.json"), "w") as _fh: _fh.write("{not json")
o, e = sweep("--resave", "--approved", APPF, "--live")
check("8.8 an approved file that cannot be read: nothing is bought, moved or saved - the listing still runs, read only, and the top of the report says why",
      "TOP OF THE REPORT - FEED ORDER SWEEP: the owner's approved file registers/feed_order_approved.json could not be read" in o and W[0].v["vst9101"].saves == [] and ELIG["calls"] == []
      and not any(re.search(r'action="(updvisit|updextrainsinfo)', p_) for p_ in W[0].posts) and top(o, "vst9101") != "", o[-600:])
# OPS-1 / R7-REPLAY-1 / NH7-N1: the approved file MISSING (the runbook used to say "drop --approved") - the standing word must not save the owner's visits without his file
W[0] = SWorld({"912": med("912", "M912"), "913": med("913", "M913")}, SW("vst9111", [chg(91111)]), SW("vst9112", [chg(91121)]))
ws9([srow("vst9111", "pat912", "10/20/2026", ["99309"], ["charge91111"], open_plans_at_entry=0, chart_insorder=""), srow("vst9112", "pat913", "10/21/2026", ["99309"], ["charge91121"])],
    recon={"vst9111": DOC, "vst9112": DOC}, verify={"pat913": {"v": 3, "plans": [], "insorder": ""}}, seed=[PILOT_DONE])
ELIG["ans"] = {("CMS", "M912", "20261020"): PARTB(), ("CMS", "M913", "20261021"): PARTB()}
for _i in range(2): o, e = sweep("--coverage", "--resave", "--standing", "--live")
check("OPS-1/R7-REPLAY-1 the approved file is missing: the runbook's call buys NOTHING and saves NOTHING - not the round-7 standing-word visit, not an old batch's stuck visit - and the top of the report says the file must be restored",
      e == "" and ELIG["calls"] == [] and W[0].v["vst9111"].saves == [] and W[0].v["vst9112"].saves == [] and len(sreg("resave")) == 1 and sreg("coverage") == []
      and "TOP OF THE REPORT - FEED ORDER SWEEP: the owner's approved file registers/feed_order_approved.json is not in this folder - nothing was bought, moved or saved this run, the standing word included" in o, (e, ELIG["calls"], [l_ for l_ in o.splitlines() if "approved file" in l_][:2]))
check("OPS-1 ... the listing still runs (read only): both stuck visits have their TOP line", top(o, "vst9111") != "" and top(o, "vst9112") != "", tops(o))
json.dump({"vst9111": "1", "vst9112": "1"}, open(os.path.join(SWD[0], "registers", "feed_order_approved.json"), "w"))
o, e = sweep("--coverage", "--resave", "--standing", "--approved", APPF, "--live")
check("OPS-13 a file that does not carry the owner's recorded word (a bare visit -> order list, no approved_by / answers) is not his approved file: nothing bought, moved or saved",
      e == "" and ELIG["calls"] == [] and W[0].v["vst9111"].saves == [] and W[0].v["vst9112"].saves == [] and "does not carry the owner's recorded word (approved_by and answers)" in o, o[-500:])
_old_rs = SSTAND["resave"]; SSTAND["resave"] = {k_: v_ for k_, v_ in SRS.items() if k_ != "billed_reasons"}; DREADS.clear()
try: o, e = sweep()
finally: SSTAND["resave"] = _old_rs
check("8.2 a workspace resave.py older than round 7 (no list-aware save): the sweep does not run at all and says so at the top", "TOP OF THE REPORT - FEED ORDER SWEEP DID NOT RUN: resave.py in this folder is older than 11/10/2026 (no billed_reasons)" in o and DREADS == [], o[-300:])
# ---- R8. (11/11/2026, round 8 - the echo guard) nothing is sent when AdvancedMD did not return all of a visit's charges ----------------------------
# Until here a stand-in listed a visit's live charges. In this section the REAL resave.visit_charges runs under the sweep, under the order save and
# under the insurance check's own save: it is lifted out of resave.py's text with the other functions, all into ONE namespace (as in the real
# module), and the stand-in AdvancedMD answers each charge's own detail and the chart's transaction history (gettxhistory, 100 charge rows a page).
import hashlib
class HW(SWorld):
    """SWorld plus the two calls the real visit_charges makes. gettxhistory lists `pad` charge rows of another visit first, then every charge of
    every visit of this world (its visit, its void flag, its fee); a good page carries the empty <Error /> of a good answer and memos with the
    letters "Fault". fault = the history CALLS (the first is 1) answered with a Fault; timeout = history calls that never answer; hide = charges
    the history does not list."""
    def __init__(self, charts, *visits, pad=0): SWorld.__init__(self, charts, *visits); self.pad, self.fault, self.timeout, self.hide, self.hcalls = pad, set(), set(), set(), 0
    def rows(self):
        return ['<charge id="%d" visit="555" void="0" fee="50.00" memo="No Fault of the payer"/>' % (700000 + k) for k in range(self.pad)] + [
            '<charge id="%s" visit="%s" void="%d" fee="%s"/>' % (k[6:], re.sub(r"\D", "", sv.vid), bool(c.get("void")), c.get("fee", "141.00")) for sv in self.v.values() for k, c in sv.ch.items() if k not in self.hide]
    def post(self, body, timeout=0):
        if 'action="gettxhistory"' in body:
            self.posts.append(body); self.hcalls += 1; page = int(re.search(r'pagenumber="(\d+)"', body).group(1))
            if self.hcalls in self.timeout: raise TimeoutError("read timed out (test)")
            if self.hcalls in self.fault: return "<PPMDResults><Error><Fault><detail><description>Server Error (test)</description></detail></Fault></Error></PPMDResults>"
            return "<PPMDResults><Results>%s</Results><Error /></PPMDResults>" % "".join(self.rows()[(page - 1) * 100:page * 100])
        if 'action="getchargedetaildataicd10"' in body: self.posts.append(body); return self.detail(re.search(r'chargeid="(\d+)"', body).group(1))
        return SWorld.post(self, body, timeout)
RNS8 = {"re": re, "ET": ET, "amd": AM}
exec(lift(os.path.join(HELPERS, "resave.py"), {"detail", "READ_NOTE", "_fault_text", "visit_charges", "CHG_FIELDS", "HOSP_CODES", "order_list", "billed_reasons", "admit_of", "admit_codes", "admit_back", "restore_admit", "set_insorder"}), RNS8)
def _vc8(cid):      # resave.py is ONE module in real life: the note visit_charges writes is the note the sweep reads. Here the lifted functions live in RNS8 and the sweep sees a stand-in module, so the note is handed over to that module
    out = RNS8["visit_charges"](cid)
    if "READ_NOTE" in RNS8 and "resave" in sys.modules: sys.modules["resave"].READ_NOTE = RNS8["READ_NOTE"]
    return out
SRS8 = {k_: RNS8[k_] for k_ in ("READ_NOTE", "detail", "CHG_FIELDS", "HOSP_CODES", "order_list", "billed_reasons", "admit_of", "admit_codes", "admit_back", "restore_admit", "set_insorder") if k_ in RNS8}; SRS8["visit_charges"] = _vc8
SSTAND8 = dict(SSTAND, resave=SRS8)
def sweep8(*argv):      # the sweep over the real history read; also the exit code it ended with (None = it ran to its end)
    se = io.StringIO(); codes = []; _exit = sys.exit; sys.exit = lambda c=0: (codes.append(c), _exit(c))[1]
    try:
        with contextlib.redirect_stderr(se): o_, e_ = run_inside(SWP, SSTAND8, SWD[0], argv=argv)
    finally: sys.exit = _exit
    return o_ + se.getvalue(), e_, (codes[-1] if codes else None)
def dnf(o_): return next((l_ for l_ in o_.splitlines() if l_.startswith("TOP OF THE REPORT - FEED ORDER SWEEP DID NOT FINISH: ")), "")
def rows8(kind, *vids): return [r_ for j_ in sreg(kind) for r_ in (j_.get("rows") or j_.get("moves") or []) if r_.get("visit") in vids]
def calls8():      # every call of a scenario, in the order it came, in a few words
    out_ = []
    for b_ in W[0].posts:
        a_ = re.search(r'action="([^"]*)"', b_).group(1)
        out_.append("history %s" % re.search(r'pagenumber="(\d+)"', b_).group(1) if a_ == "gettxhistory" else "detail %s" % re.search(r'chargeid="(\d+)"', b_).group(1) if a_ == "getchargedetaildataicd10"
                    else "save %s insorder=%s" % (",".join(re.findall(r'<charge id="charge(\d+)"', b_)) or "NO CHARGE", re.search(r'<visit [^>]*insorder="([^"]*)"', b_).group(1)) if a_ == "updvisitwithcharges" else a_)
    return out_
def sum8(): return hashlib.sha256("\n".join(W[0].posts).encode()).hexdigest()[:16]      # the bodies of those calls, word for word and in order, as one short fingerprint
STOPTAIL = "a save or move it had begun is marked unexpected there (a STOP until a person has looked at that visit)"
SIB = dict(cpt="99497", pcode="pcode65299", fee="86.00")      # the visit's second charge
# the sweep's OWN read before its OWN save (--resave) and its OWN clinician move (--fix-clinician)
for _ph, _kind, _what, _ap, _who in (("--resave", "resave", "save", _send, DOC), ("--fix-clinician", "fixclin", "clinician move", _mv, NPL)):
    for _case, _knob, _two, _pad, _words in (
            ("a FAULT PAGE in the chart's history (the listed charge is read; a sibling the import register does not list is on the page that failed - only resave.py's note can tell)", "fault", False, 99, "1 live charge(s) came back and the read was not complete"),
            ("an EMPTY READ (the history lists none of the visit's charges, and nothing failed)", "hide_all", False, 0, "no live charge came back"),
            ("a LISTED CHARGE THAT IS MISSING (the history lists one of the two charges this run's listing read)", "hide_one", True, 0, "charge80012, which this run's listing read for the visit, did not come back among the 1 live charge(s) read"),
            ("an ERROR at that read (a time-out): what the sweep has always done there - here for comparison", "timeout", False, 0, "")):
        W[0] = HW({"801": med("801", "M801"), "802": med("802", "M802")}, SW("vst8001", [chg(80011), chg(80012, **SIB)]), SW("vst8002", [chg(80021)]), pad=_pad)
        ws9([srow("vst8001", "pat801", "10/12/2026", ["99309", "99497"] if _two else ["99309"], ["charge80011", "charge80012"] if _two else ["charge80011"]), srow("vst8002", "pat802", "10/13/2026", ["99309"], ["charge80021"])],
            recon={"vst8001": _who, "vst8002": _who}, approved={"vst8001": _ap, "vst8002": _ap}, seed=[PILOT_DONE, MOVE_DONE])
        setattr(W[0], *{"fault": ("fault", {2}), "hide_all": ("hide", {"charge80011", "charge80012"}), "hide_one": ("hide", {"charge80012"}), "timeout": ("timeout", {1})}[_knob])
        o, e, code = sweep8(_ph, "--approved", APPF, "--live"); A, B = W[0].v["vst8001"], W[0].v["vst8002"]; line = dnf(o); r0 = rows8(_kind, "vst8001", "vst8002")
        nothing = not (A.saves or A.moves or A.extins or B.saves or B.moves or B.extins)
        if _knob == "timeout":
            check("R8 %s meets %s: nothing is sent, 'FEED ORDER SWEEP DID NOT FINISH: TimeoutError: ...', exit 2, no row for the visit" % (_ph, _case),
                  e == "" and code == 2 and nothing and r0 == [] and line.startswith("TOP OF THE REPORT - FEED ORDER SWEEP DID NOT FINISH: TimeoutError: read timed out (test) - what it did is in the registers named below; " + STOPTAIL)
                  and (sreg("sweep") or [{}])[-1].get("finished") is False, (e, code, line, r0))
        else:
            check("R8 %s meets %s: NOTHING is sent for that visit and the run ends the same way - 'FEED ORDER SWEEP DID NOT FINISH: nothing was sent for ... - AdvancedMD did not return all of this visit's charges before the %s: ...', exit 2, the next visit not touched" % (_ph, _case, _what),
                  e == "" and code == 2 and nothing and line.startswith("TOP OF THE REPORT - FEED ORDER SWEEP DID NOT FINISH: nothing was sent for pat801 vst8001 (service date 10/12/2026) - AdvancedMD did not return all of this visit's charges before the %s: %s. A full-visit save that leaves a live charge out voids that charge. No row was written for the visit and no STOP is left: leave it as it is and run the same command again later" % (_what, _words))
                  and STOPTAIL not in line and ("gettxhistory page 2 for visit vst8001 of chart pat1 answered a Fault" in line) == (_knob == "fault") and line.endswith(" - what it did is in the registers named below") and (sreg("sweep") or [{}])[-1].get("finished") is False, (e, code, line))
        W[0].fault, W[0].timeout, W[0].hide = set(), set(), set(); o2, e2, code2 = sweep8(_ph, "--approved", APPF, "--live"); _body = (A.saves or A.moves or [""])[0]
        check("R8 ... no row was written for that visit (none marked sent) and no STOP is left: the same command, run again once AdvancedMD answers in full, %s both visits - both charges of the first one in its echo - with nothing for a person to clear" % ("saves" if _ph == "--resave" else "moves"),
              r0 == [] and e2 == "" and code2 is None and "FEED ORDER SWEEP STOPPED" not in o2 and "DID NOT FINISH" not in o2 and 'id="charge80011"' in _body and 'id="charge80012"' in _body
              and ((len(A.saves) == 1 and A.lst == "1" and len(B.saves) == 1 and not A.moves) if _ph == "--resave" else (len(A.moves) == 1 and A.prof == "prof15" and len(B.moves) == 1 and not A.saves)), (r0, e2, code2, o2[-400:]))
# the sweep sets the note to "" itself before each of its two reads: a stand-in for visit_charges never touches it (sections 8.x use one), and a note left in the module by an earlier read must not refuse a good one
_old_rs = SSTAND["resave"]; SSTAND["resave"] = dict(SRS, READ_NOTE="a note left by an earlier read (test)")
try:
    for _ph, _ap, _who in (("--resave", _send, DOC), ("--fix-clinician", _mv, NPL)):
        W[0] = SWorld({"801": med("801", "M801")}, SW("vst8001", [chg(80011)])); ws9([srow("vst8001", "pat801", "10/12/2026", ["99309"], ["charge80011"])], recon={"vst8001": _who}, approved={"vst8001": _ap}, seed=[PILOT_DONE, MOVE_DONE])
        o, e = sweep(_ph, "--approved", APPF, "--live"); A = W[0].v["vst8001"]
        check("R8 %s with a stand-in for visit_charges that never touches the note, and a stale note left in the module: the sweep sets the note to '' itself before its read - the visit is %s, nothing is refused" % (_ph, "saved" if _ph == "--resave" else "moved"),
              e == "" and "DID NOT FINISH" not in o and ((len(A.saves) == 1 and A.lst == "1") if _ph == "--resave" else (len(A.moves) == 1 and A.prof == "prof15")), (e, o[-400:]))
finally: SSTAND["resave"] = _old_rs
# the answer of the order save: set_insorder's own guard, on its own read, inside the sweep (no pilot save has been made yet in this workspace)
W[0] = HW({"801": med("801", "M801"), "802": med("802", "M802")}, SW("vst8001", [chg(80011), chg(80012, **SIB)]), SW("vst8002", [chg(80021)]))
ws9([srow("vst8001", "pat801", "10/12/2026", ["99309"], ["charge80011"]), srow("vst8002", "pat802", "10/13/2026", ["99309"], ["charge80021"])], recon={"vst8001": DOC, "vst8002": DOC}, approved={"vst8001": _send, "vst8002": _send})
W[0].fault = {2}      # the sweep's own read (history call 1) is complete; the order save's own read (call 2) meets a failed page
o, e, code = sweep8("--resave", "--approved", APPF, "--live"); A, B = W[0].v["vst8001"], W[0].v["vst8002"]; line = dnf(o); r0 = rows8("resave", "vst8001")
check("R8 the order save refuses inside the sweep (the sweep's own read was complete; set_insorder's read met a failed page): its answer 'visit vst8001: nothing sent - ...' is not taken for a save - nothing went out, the visit's row is NOT marked sent, carries no 'unexpected' (so it is no STOP) and says that nothing was sent; the run ends DID NOT FINISH, exit 2",
      e == "" and code == 2 and not (A.saves or A.extins or B.saves) and len(r0) == 1 and r0[0].get("sent") is False and r0[0].get("ok") is False and "unexpected" not in r0[0] and str(r0[0].get("words")).startswith("visit vst8001: nothing sent - AdvancedMD did not return all of this visit's charges")
      and str(r0[0].get("refused")).startswith("nothing was sent - the order save answered: visit vst8001: nothing sent - ") and STOPTAIL not in line and "FEED ORDER SWEEP STOPPED" not in o
      and line.startswith("TOP OF THE REPORT - FEED ORDER SWEEP DID NOT FINISH: nothing was sent for pat801 vst8001 (service date 10/12/2026) - the order save could not read all of this visit's charges and sent nothing. The visit's row says so and is not a STOP: leave the visit as it is and run the same command again later - the order save answered: visit vst8001: nothing sent - ")
      and "| this run: nothing was sent - the order save answered: visit vst8001: nothing sent - " in top(o, "vst8001"), (e, code, r0, line))
W[0].fault = set(); o2, e2, code2 = sweep8("--resave", "--approved", APPF, "--live")
check("R8 ... and the next run goes on as if that visit had never been tried: no STOP, and the refused row did not count as the pilot save - this run is still the pilot: it saves that ONE visit (both its charges echoed) and the other waits",
      e2 == "" and code2 is None and "FEED ORDER SWEEP STOPPED" not in o2 and len(A.saves) == 1 and A.lst == "1" and 'id="charge80012"' in (A.saves or [""])[0] and B.saves == [] and "FEED ORDER SAVE - waits: pat802 vst8002 10/13/2026 - the pilot saves ONE visit" in o2, (e2, code2, o2[-500:]))
# the sweep does not start with a resave.py from before round 8
_old_rs = SSTAND["resave"]; SSTAND["resave"] = {k_: v_ for k_, v_ in SRS.items() if k_ != "READ_NOTE"}; DREADS.clear(); _p0 = len(W[0].posts)
try: o, e = sweep("--resave", "--approved", APPF, "--live")
finally: SSTAND["resave"] = _old_rs
check("R8 a workspace resave.py from before round 8 (it leaves no note when a visit's charges were not all read): the sweep does not run at all and says so at the top - the same line and the same remedy as for a copy from before round 7",
      "TOP OF THE REPORT - FEED ORDER SWEEP DID NOT RUN: resave.py in this folder is older than 11/11/2026 (no READ_NOTE" in o and "copy the repository's scripts/helpers/resave.py here and run again" in o and DREADS == [] and len(W[0].posts) == _p0, o[-300:])
# the insurance check's own save (claimocity_verify.fast_set_insorder) does not look at the note - a known, older gap that round 8 leaves as it was.
# Over the REAL history read it makes, on a good read and on a failed one, the very calls it made before this round: each fingerprint below was
# taken from the helpers of the live branch as it stood before round 8 (this same file, the same answers), and the helpers of this tree give the same.
RSV8 = types.SimpleNamespace(detail=RNS8["detail"], CHG_FIELDS=RNS8["CHG_FIELDS"], READ_NOTE="")      # the resave module as the insurance check sees it: the real history read, and the note where the real module keeps it
def _vc8v(cid): out = RNS8["visit_charges"](cid); RSV8.READ_NOTE = RNS8.get("READ_NOTE", ""); return out
RSV8.visit_charges = _vc8v
VNS8 = {"resave": RSV8, "amd": AM, "re": re, "CARRIERS": CARS, "CODE2CAR": {v_[0]: k_ for k_, v_ in CARS.items()}}
exec(compile(_vs, "claimocity_verify.py", "exec"), VNS8); fast8 = VNS8["fast_set_insorder"]
def w81(pad=0, **knob): W[0] = HW({}, SV("vst8101", [chg(81011), chg(81012, **SIB)], attr="1", lst=""), pad=pad); [setattr(W[0], k_, v_) for k_, v_ in knob.items()]
w81(); _a = _try(fast8, row("vst8101", ["charge81011"]), "1", [], {})
check("R8 UNCHANGED in round 8 - the insurance check's own save on a good read: the sibling the register does not list is echoed in ONE save and read back - the answer and the calls of before this round, word for word",
      _a == (True, "insorder 1 -> 1, list [] -> [1], 2 of 2 echoed charges live (also echoed, not in the register: charge81012)") and sum8() == "397b65b3ac41b14e"
      and calls8() == ["detail 81011", "detail 81011", "history 1", "detail 81011", "detail 81012", "detail 81011", "detail 81012", "save 81011,81012 insorder=1", "detail 81011", "history 1", "detail 81011", "detail 81012"] and W[0].v["vst8101"].live() == ["charge81011", "charge81012"], (_a, calls8(), sum8()))
w81(fault={1}); _a = _try(fast8, row("vst8101", ["charge81011"]), "1", [], {})
check("R8 UNCHANGED in round 8 - the insurance check's own save, a Fault on the first history page: its own guard holds the visit ('detail read mismatch ... not among the visit's 0 live charges'), nothing sent - the answer and the calls of before this round, word for word",
      _a == (False, "detail read mismatch (register charge(s) charge81011 not among the visit's 0 live charges)") and calls8() == ["detail 81011", "detail 81011", "history 1"] and sum8() == "46b65262491445ed" and W[0].v["vst8101"].saves == [], (_a, calls8(), sum8()))
w81(pad=99, fault={2}); _a = _try(fast8, row("vst8101", ["charge81011"]), "1", [], {})
check("R8 UNCHANGED in round 8 (the known, older gap - NOT closed here) - the insurance check's own save, a Fault on page 2 of the history: the register's charge is read, the sibling on the failed page is not - it still saves the ONE charge it read (the stand-in voids the sibling left out) - the answer and the calls of before this round, word for word",
      _a == (True, "insorder 1 -> 1, list [] -> [1], 1 of 1 echoed charges live") and sum8() == "8fb38fbd4e02f462"
      and calls8() == ["detail 81011", "detail 81011", "history 1", "history 2", "detail 81011", "detail 81011", "save 81011 insorder=1", "detail 81011", "history 1", "history 2", "detail 81011"] and W[0].v["vst8101"].live() == ["charge81011"], (_a, calls8(), sum8()))
# nobody else reads the note, and the two helpers say in their own words what is refused and what is still open
_rn = sorted(os.path.relpath(f_, ROOT) for f_ in glob.glob(os.path.join(HELPERS, "*.py")) + glob.glob(os.path.join(ROOT, "core", "*.py")) if "READ_NOTE" in open(f_, errors="replace").read())
check("R8 only resave.py (both copies) and the sweep know the note: no other helper under scripts/helpers or core reads READ_NOTE - every other caller of visit_charges gets its answer exactly as before",
      _rn == ["core/resave.py", "scripts/helpers/feed_order_sweep.py", "scripts/helpers/resave.py"], _rn)
_rsrc = open(os.path.join(HELPERS, "resave.py")).read(); _ssrc8 = open(SWP).read()
check("R8 resave.py and the sweep say, dated 11/11/2026, what is refused ('nothing sent') and that every OTHER helper that calls visit_charges still saves what it read - a known, older gap; the refusal never begins with the word the sweep reads as 'a save went out'",
      all("11/11/2026 (round 8" in x_ and "nothing sent - " in x_ and re.search(r"KNOWN, OLDER GAP|known, older gap", x_) and "do not look at that note yet" in x_.replace("does not", "do not") for x_ in (_rsrc, _ssrc8))
      and 'return False, "visit %s: nothing sent - ' in _rsrc and 'm.startswith("resave ")' in _ssrc8 and 're.match(r"visit \\S+: nothing sent - ", m)' in _ssrc8, [("11/11/2026 (round 8" in x_, "nothing sent - " in x_) for x_ in (_rsrc, _ssrc8)])
# ---- 9. the words: the runbook's step and section, the rulebook, the lessons, the captured calls -----------------------------------------------------
_stp = open(os.path.join(ROOT, "nightly", "claimocity_feed_step.md")).read(); _stpn = _stp.replace("\n", " "); _rl = open(os.path.join(ROOT, "practices", "ehpa", "rules.md")).read()
_ls = open(os.path.join(ROOT, "docs", "SHARED_LESSONS.md")).read(); _cc = open(os.path.join(ROOT, "docs", "captured_calls.md")).read()
_c2 = _stp[_stp.index("(c2) FEED VISITS WITH AN EMPTY INSURANCE ORDER"):_stp.index("(d) Every chart the digest lists")]
check("9 runbook: step (c2) runs the sweep right after the insurance check - the repository's resave.py first, then the listing, the dated checks and the saves (approved file and standing word) in one call; its TOP lines go to the top and its registers are committed",
      _stp.index("(c) FIRST the place-of-service precondition") < _stp.index("(c2) FEED VISITS") < _stp.index("(d) Every chart") and "cp -p feed_order_sweep.py resave.py /home/claude/unbilled/" in _c2
      and "python3 feed_order_sweep.py --coverage --resave --standing --approved registers/feed_order_approved.json --live" in _c2 and "--fix-clinician" not in _c2
      and "'TOP OF THE REPORT' go to the top of the report word for word" in _c2 and "feed_order_fixclin_<stamp>.json" in _c2 and "feed_order_coverage_<stamp>.json" in _c2)
check("9 runbook section: the TOP lines and what the routine does, how William approves visits (the file only after his word, never by a routine), the remedy order (oldest first, one pilot whose clinician matches, read back, then the rest), the moves by a chat session",
      all(x_ in _stpn for x_ in ("## Feed visits with an empty insurance order", "written only after his word, by a chat session or by him - never by a routine",
                                 "THE REMEDY ORDER: oldest date of service first. The first live run saves ONE visit whose clinician matches - the pilot - and reads it back; the next run does the rest",
                                 "are run by a chat session, not by a routine", "A routine never writes \"cleared\"", "HOLD in the insurance check's report is a label only")), [x_ for x_ in ("## Feed visits", "never by a routine", "THE REMEDY ORDER", "chat session, not by a routine") if x_ not in _stpn])
# 11/11/2026: the lesson line and the captured-calls section are COUNTED, not pinned to the end of their files - every routine run appends to both
check("9 rulebook and lessons: one dated line each, with the cause; captured calls: one new section on the list-aware read-back",
      _rl.count("FEED VISITS WITH AN EMPTY INSURANCE ORDER") == 1 and "(11/10/2026, William in chat, STANDING for the charge feed) FEED VISITS WITH AN EMPTY INSURANCE ORDER. The cause:" in _rl
      and _ls.count("| chat (round 7, feed visits with no insurance order) | TRAP |") == 1 and any(l_.startswith("- 2026-11-10T1915Z | chat (round 7") for l_ in _ls.split("\n"))
      and sum(1 for s_ in _cc.split("\n## ") if s_.startswith("2026-11-10T1915Z - a visit's insurance-order LIST, read back")) == 1 and "the 10/28 advice above (skip the save when the chart default already equals the target) is withdrawn" in _cc)
# 11/11/2026 (round 8): the two new lines are COUNTED too, wherever they stand in their files - routines append to both
_rl8 = next((l_ for l_ in _rl.split("\n") if "NO SAVE WHEN A VISIT'S CHARGES COULD NOT ALL BE READ" in l_), ""); _ls8 = next((l_ for l_ in _ls.split("\n") if "| chat (round 8, the echo guard) | TRAP |" in l_), "")
check("R8 rulebook: ONE dated line on the echo guard, after round 7's line on feed visits with an empty insurance order - the order save and the sweep never send a save when AdvancedMD did not return all of a visit's charges, and what a routine or a billing session does on 'nothing sent' / 'DID NOT FINISH' for that reason: it leaves the visit as it is, reports the line, runs the same command again later, never in a loop",
      _rl.count("NO SAVE WHEN A VISIT'S CHARGES COULD NOT ALL BE READ") == 1 and _rl8.startswith("- (11/11/2026, ") and _rl.index("FEED VISITS WITH AN EMPTY INSURANCE ORDER") < _rl.index("NO SAVE WHEN A VISIT'S CHARGES COULD NOT ALL BE READ")
      and all(x_ in _rl8 for x_ in ("resave.set_insorder", "feed_order_sweep.py --resave and --fix-clinician", "never send a save when AdvancedMD did not return all of a visit's charges", '"visit <id>: nothing sent - ..."', '"NOT rebilled"',
                                    "FEED ORDER SWEEP DID NOT FINISH: nothing was sent for", "leaves no STOP", "it leaves the visit as it is (no save by another helper, no rebill), reports the line, and runs the same command again later", "it never retries in a loop", "A KNOWN, OLDER GAP")),
      [x_ for x_ in ("leaves the visit as it is", "runs the same command again later", "never retries in a loop") if x_ not in _rl8] or _rl8[:200])
check("R8 lessons: ONE dated TRAP line - a failed history read looks like 'no more charges', a save that leaves a live charge out voids it, which helpers are guarded now and that the others are not yet",
      _ls.count("| chat (round 8, the echo guard) | TRAP |") == 1 and _ls8.startswith("- 2026-11-11T") and all(x_ in _ls8 for x_ in ('A failed history read looks like "no more charges"', "A full-visit save that leaves a live charge out voids it",
                                    "GUARDED since 11/11/2026: resave.set_insorder", "feed_order_sweep.py (--resave, --fix-clinician)", "NOT GUARDED YET: every other helper that calls visit_charges", "move_to_ins.move", "freq1_visit.run", "claimocity_verify.fast_set_insorder", "never in a loop")), _ls8[:300])
# the three confirmation reviews: the words a routine follows
check("OPS-1/R7-REPLAY-1 runbook (c2): the owner's approved file is copied from the repository every run, and the call never drops --approved (no 'drop --approved' fallback - the sweep lists only and says so)",
      "cp -p ../../practices/ehpa/registers/feed_order_approved.json /home/claude/unbilled/registers/" in _c2 and "drop --approved" not in _stp and "the call never changes when the approved file is missing" in _c2)
check("OPS-2 runbook (c2): the sweep runs in the background under nohup with its own log, one at a time, read to its 'register: ' line - not one plain call under the 600 s cap",
      "nohup python3 feed_order_sweep.py --coverage --resave --standing --approved registers/feed_order_approved.json --live > logs/feed_order_sweep_<run stamp>.log 2>&1 &" in _c2 and "ONE plain call" not in _c2
      and "pgrep -f feed_order_sweep.py" in _c2 and "until its last line starts with 'register: '" in _c2)
check("OPS-8 runbook (c2): <stamp> is the sweep's OWN stamp, every register its 'registers written this run' line names is committed, and the resave register holds the pilot and every STOP",
      "'registers written this run - commit every one: ...'" in _c2 and "the sweep's OWN stamp" in _c2 and "the resave register holds the pilot and every STOP" in _c2)
check("OPS-11 runbook (c2) runs EVERY run, also one that imported nothing new; the daily feed prompt (B5) and the billing button's FEED line name step (c2)",
      "also a run that imported nothing new" in _c2 and "then the runbook's step (c2) - the feed order sweep (`feed_order_sweep.py`" in open(os.path.join(ROOT, "nightly", "live", "feed_daily.txt")).read()
      and "then the runbook's step (c2), the feed order sweep (`feed_order_sweep.py`" in open(os.path.join(ROOT, "nightly", "live", "billing_button.txt")).read())
check("OPS-4 runbook: every top-of-report line the change can print has its meaning and action (the digest's six and the sweep's), and step (f) lifts every digest TOP line to the top word for word",
      all(x_ in re.sub(r"\s+", " ", _stp) for x_ in ("chart(s) held with NO plan", "OLD INSURANCE ORDER", "INSURANCE ORDER NOT READ", "SAVE NOT AS ASKED", "the insurance-order lines could not be built", "NOT THE CHECKED INSURANCE ORDER",
                                 "ADMISSION DATE LOST", "FEED ORDER SWEEP DID NOT FINISH", "the owner's approved file ... - nothing was bought, moved or saved"))
      and "Every line of the digest that starts '  - TOP OF THE REPORT - ' - those of the insurance check's section 'Cascade insurance check' included" in _stp)
check("OPS-5 runbook: '| this run:', 'for William:' and 'waits for the clinician move ... a chat session runs --fix-clinician' are explained (who acts on a visit that only a person can move on)",
      "after '| this run:' what this" in _stpn and "words that start 'for William:'" in _stpn and "waits for the clinician move to the nurse practitioner (prof15) - a chat session runs --fix-clinician' = only a chat" in _stpn)
check("A/B words: captured calls, rulebook and lessons say the re-route helpers pass allow_billed=True and a Medicare Advantage plan with drug coverage is medical; no sentence says the re-route is refused",
      "set_insorder(..., allow_billed=True)" in _cc and "Medicare Advantage plan with drug coverage" in _cc and "allow_billed=True" in _rl and "a Medicare Advantage plan with drug coverage is a medical plan" in _rl
      and "only the re-route of a billed visit after a wrong-payer denial passes allow_billed=True" in _ls and "billed_ok" not in _cc + _rl + _ls)
_own = open(os.path.abspath(__file__)).read()
check("OPS-10 no invented member id here is 5 characters or more: the privacy gate's tree mode (mirror.py sync) would rewrite it and break this test", not re.findall(r'"(?:member|subscribernum|memberid|member_id)"\s*:\s*"[A-Za-z0-9][A-Za-z0-9\-]{4,}"', _own))

# ---- INGEST-1 (11/25/2026, independent review): a second LIVE start under the SAME stamp is refused before anything is touched --------------
# The import resumes a stamp's register and then passes over every message of a patient that register lists as skipped - also one the first
# start never reached (reproduced by the review: a CCM 99487 in no row, the file registered, the charge never entered). The driver is run here
# for real, with only its workspace folder pointed at a throw-away one.
import subprocess as _sp, shutil as _sh
def _ingest_at(tmp, stamp, live=True, register=True):
    src = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_ingest.py")).read()
    assert src.count('WS = "/home/claude/unbilled"') == 1
    open(os.path.join(tmp, "claimocity_ingest.py"), "w").write(src.replace('WS = "/home/claude/unbilled"', "WS = %r" % tmp))
    os.makedirs(os.path.join(tmp, "inbox"), exist_ok=True); os.makedirs(os.path.join(tmp, "registers"), exist_ok=True)
    open(os.path.join(tmp, "inbox", "20261125.hl7"), "w").write("MSH|^~\\&|X\r")
    if register: json.dump({"created": [], "skipped": [{"feed_id": "F1", "pid": "pat1", "why": "all lines already in AMD"}], "failed": []}, open(os.path.join(tmp, "registers", "feed_import_%s.json" % stamp), "w"))
    return _sp.run([sys.executable, os.path.join(tmp, "claimocity_ingest.py"), "--hl7-dir", os.path.join(tmp, "inbox"), "--stamp", stamp] + (["--live"] if live else []), capture_output=True, text=True)
_t1 = tempfile.mkdtemp(prefix="ingest_same_stamp_"); _r1 = _ingest_at(_t1, "20261125T1239Z")
check("INGEST-1 a second live start under a stamp that already has an import register is refused: 'STEP FAILED: stamp ... already has an import register', exit 2, a NEW stamp named - and no step ran (no parse, no log of a step)",
      _r1.returncode == 2 and "STEP FAILED: stamp 20261125T1239Z already has an import register" in _r1.stdout and "NEW stamp" in _r1.stdout
      and not glob.glob(os.path.join(_t1, "logs", "claimocity_*")) and not glob.glob(os.path.join(_t1, "feed_parsed_*")), (_r1.returncode, _r1.stdout[-400:], _r1.stderr[-300:]))
_run1 = (json.load(open(os.path.join(_t1, "registers", "claimocity_ingest.json"))).get("runs") or [{}])[-1] if os.path.exists(os.path.join(_t1, "registers", "claimocity_ingest.json")) else {}
check("INGEST-1 the refused start is on record (exit 2) and the file is NOT registered - the start under the new stamp reads it again", _run1.get("exit") == 2 and not json.load(open(os.path.join(_t1, "registers", "claimocity_ingest.json"))).get("files"), _run1)
_t2 = tempfile.mkdtemp(prefix="ingest_same_stamp_"); _r2 = _ingest_at(_t2, "20261125T1239Z", register=False)
check("INGEST-1 a first start under a stamp is not refused (it goes on to its first step)", "already has an import register" not in _r2.stdout and bool(glob.glob(os.path.join(_t2, "logs", "claimocity_20261125T1239Z_parse.log"))), (_r2.returncode, _r2.stdout[-300:], _r2.stderr[-200:]))
_t3 = tempfile.mkdtemp(prefix="ingest_same_stamp_"); _r3 = _ingest_at(_t3, "20261125T1239Z", live=False)
check("INGEST-1 a dry look under the same stamp is not refused (it writes nothing)", "already has an import register" not in _r3.stdout, (_r3.returncode, _r3.stdout[-300:]))
for _t in (_t1, _t2, _t3): _sh.rmtree(_t, ignore_errors=True)
check("INGEST-1 the driver's header no longer promises that a re-run inside a batch is a no-op", "make a re-run a no-op" not in open(os.path.join(ROOT, "scripts", "helpers", "claimocity_ingest.py")).read())

time.sleep = _sleep0
print("\n" + ("all checks passed" if not FAILS else "%d check(s) FAILED: %s" % (len(FAILS), "; ".join(FAILS))))
sys.exit(1 if FAILS else 0)
