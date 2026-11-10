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
#     - the digest puts the visits with no insurance order at the TOP and counts only saves that were sent.
#   The import's new register fields (section 7) are proved in tools/selftest/test_pos_rule.py, where the import runs with its stand-ins.
# Run: python3 tools/selftest/test_feed_order.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, io, re, ast, contextlib, time
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
    def __init__(self, vid, charges, attr="1", lst="", admit="", builds=True, wipe=False, restore=True, fault=None, void_after=(), rev=False):
        self.vid, self.attr, self.lst, self.admit, self.builds, self.wipe, self.restore, self.fault, self.void_after, self.rev = vid, attr, lst, admit, builds, wipe, restore, fault, set(void_after), rev
        self.ch = {c["id"]: dict(c) for c in charges}; self.saves = []; self.extins = []
    def detail(self, cid):
        c = self.ch[cid]; seqs = [s for s in self.lst.split(",") if s]
        rows = ['<insuranceorder carrier="car1" sequence="%s" ordinal="%d"/>' % (s, i) for i, s in enumerate(seqs)]
        if self.rev: rows = rows[::-1]      # AdvancedMD can list the entries out of claim order: the ordinal decides
        attrs = dict({"id": cid, "proccode": c.get("pcode", "pcode1"), "fee": c.get("fee", "141.00"), "void": "1" if c.get("void") else "0", "billins": "1", "insbilled": "0", "datebilled": ""}, **c.get("attrs", {}))
        pays = "".join('<payment amount="%s" void="%s"/>' % (p["amount"], p.get("void", "0")) for p in c.get("pays", []))
        kids = ("<paymentlist>%s</paymentlist>" % pays if pays else "") + ("<insbilllist><insbill billeddate=\"x\"/></insbilllist>" if c.get("insbill") else "")
        return ('<r><patient id="pat1"/><visit id="%s" episode="e1" insorder="%s" profile="prof13">%s<insuranceorderlist>%s</insuranceorderlist></visit>'
                '<charge %s>%s</charge><proccodelist><proccode id="%s" code="%s"/></proccodelist></r>') % (
            self.vid, self.attr, '<extins hospitalizationfrom="%s"/>' % self.admit if self.admit else "", "".join(rows),
            " ".join('%s="%s"' % kv for kv in attrs.items()), kids, c.get("pcode", "pcode1"), c.get("cpt", "99309"))
    def live(self): return [k for k, c in self.ch.items() if not c.get("void")]
    def post(self, body):
        if "updextrainsinfo" in body:
            self.extins.append(body); m = re.search(r'hospitalizationfrom="([^"]*)"', body)
            if self.restore and m: self.admit = m.group(1); return '<r><extins hospitalizationfrom="%s"/></r>' % m.group(1)
            return "<r/>"
        self.saves.append(body)
        if self.fault == "always" or (self.fault and 'id="%s"' % self.fault in body): return "<r><Fault><description>Charge amount is zero</description></Fault></r>"
        sent = set(re.findall(r'<charge id="(charge\d+)"', body))
        for k in self.ch:
            if k not in sent or k in self.void_after: self.ch[k]["void"] = True
        self.attr = re.search(r'<visit [^>]*insorder="([^"]*)"', body).group(1)
        if self.builds: self.lst = self.attr
        if self.wipe: self.admit = ""
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
exec(lift(os.path.join(HELPERS, "resave.py"), {"CHG_FIELDS", "HOSP_CODES", "order_list", "billed_reasons", "admit_of", "restore_admit", "set_insorder"}), RNS)      # core/resave.py must be the same file (next check)
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
ok, m = setins("431", "2,1", billed_ok=True)
check("5 set_insorder: billed_ok=True (a person's deliberate choice) saves it", ok and len(W[0].v["vst43"].saves) == 1, (ok, m))
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
_fq = open(os.path.join(HELPERS, "freq1_visit.py")).read()
check("5 freq1_visit.reroute still calls set_insorder without billed_ok (it inherits the billed guard, as the specification says)", "ok, msg = resave.set_insorder(cid, order, dry=dry)" in _fq and "billed_ok" not in _fq)

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
check("4.5 a chart held with no open plan: 'each visit of this chart must be saved again after a plan is added' (with the 4.6 words)", R["pat711"]["decision"] == "HOLD" and any(h_.startswith("no open plan on this chart: each visit of this chart must be saved again after a plan is added (vst711)") and h_.endswith(HELD) for h_ in R["pat711"]["hold"]), R.get("pat711"))
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

# ---- 6. the digest (claimocity_report.py, run INSIDE this process: it loads no AdvancedMD module) -----------------------------------------------
RSRC = open(os.path.join(HELPERS, "claimocity_report.py")).read()
check("6 the digest helper loads none of the modules that talk to AdvancedMD", not (loads(RSRC) & set(AMD_MODULES)), loads(RSRC))
DG = tempfile.mkdtemp(prefix="feedorder_digest_"); os.makedirs(os.path.join(DG, "registers"))
_rows = [{"feed_id": "f%d" % i, "pid": "pat8%d" % i, "visit": "vst8%d" % i, "charges": ["charge8%d1" % i], "fees": ["141.00"], "cpts": ["99309"], "dos": "11/02/2026"} for i in range(1, 5)]
json.dump({"created": _rows, "skipped": [], "failed": []}, open(os.path.join(DG, "registers", "feed_import_T8.json"), "w"))
json.dump({"pat81": {"v": 4, "decision": "HOLD", "visits": ["vst81"], "no_order_list": ["vst81"], "hold": ["NO CLAIM CAN BE MADE on vst81: its insurance order is empty - x"], "fixes": ["vst81 insorder 1: insorder 1 -> 1, list [] -> [] - NOT AS ASKED"]},
           "pat82": {"v": 4, "decision": "HOLD", "visits": ["vst82"], "hold": ["no open plan on this chart: each visit of this chart must be saved again after a plan is added (vst82) - " + HELD], "fixes": []},
           "pat83": {"v": 4, "decision": "RELEASE", "visits": ["vst83"], "saved": ["vst83"], "insorder": "1", "applied": {"vst83": "1"}, "fixes": ["vst83 insorder 1: insorder 1 -> 1, list [] -> [1]"], "hold": [], "lead": {"code": "FLO02"}},
           "pat84": {"v": 4, "decision": "RELEASE", "visits": ["vst84"], "insorder": "1", "applied": {"vst84": "2"}, "fixes": ["vst84 insorder 2: already 2, list [2] - nothing sent"], "hold": [], "lead": {"code": "FLO02"}}},
          open(os.path.join(DG, "feed_verify_T8.json"), "w"))
o, e = run_inside(os.path.join(HELPERS, "claimocity_report.py"), {}, DG, env={"FEED_STAMP": "T8"})
_top = [l_ for l_ in o.splitlines() if l_.startswith("  - TOP OF THE REPORT - ")]
check("6/10 the digest's TOP line, word for word: '  - TOP OF THE REPORT - NO CLAIM CAN BE MADE: 1 visit(s) on 1 chart(s) have no insurance order: pat81 vst81'", e == "" and "  - TOP OF THE REPORT - NO CLAIM CAN BE MADE: 1 visit(s) on 1 chart(s) have no insurance order: pat81 vst81" in _top, (e, _top, o[-600:]))
check("6/10 ... and a TOP line for the chart held with no plan", any(l_.startswith("  - TOP OF THE REPORT - 1 chart(s) held with NO plan:") and "pat82 (vst82)" in l_ for l_ in _top), _top)
check("6 'orders changed' counts only saves actually sent and accepted (1 - the visit whose order already matched is not a change)", "- Visit insurance orders changed (saves sent and accepted by AdvancedMD): 1;" in o, [l_ for l_ in o.splitlines() if "orders changed" in l_])
check("4.6/6 the digest says a HOLD is a label in this report only", "- Holds (William) - " + HELD in o and any(l_.startswith("  - pat82: no open plan on this chart") and l_.endswith(HELD) and l_.count(HELD) == 1 for l_ in o.splitlines()), o[-800:])
json.dump({"pat81": {"v": 3, "decision": "RELEASE", "visits": ["vst81"], "insorder": "", "applied": {"vst81": "1"}, "fixes": ["vst81 insorder 1: ok"], "hold": [], "lead": {"code": "FLO02"}}}, open(os.path.join(DG, "feed_verify_T8.json"), "w"))
o, e = run_inside(os.path.join(HELPERS, "claimocity_report.py"), {}, DG, env={"FEED_STAMP": "T8"})
check("6 an older (version 3) check whose order differed from an empty chart order is NOT counted as a change (nothing says a save was sent)", e == "" and "orders changed (saves sent and accepted by AdvancedMD): 0;" in o and "TOP OF THE REPORT - NO CLAIM" not in o, (e, o[-400:]))

time.sleep = _sleep0
print("\n" + ("all checks passed" if not FAILS else "%d check(s) FAILED: %s" % (len(FAILS), "; ".join(FAILS))))
sys.exit(1 if FAILS else 0)
