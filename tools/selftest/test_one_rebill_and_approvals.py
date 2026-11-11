#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 10/6/2026) - proves offline, with fakes and NO AdvancedMD traffic, the guarantees William asked to make
#   permanent: ONE rebill per visit (amd.rebill_charge per-visit per-run guard, move_to_ins rebill=False, freq1_visit.reroute), the visit order set
#   without a rebill (resave.set_insorder), the patient order verified and carried by an active plan (ins_update.update), and the
#   approval email/push carrying links to the approval buttons (approval_submit). Run: python3 tools/selftest/test_one_rebill_and_approvals.py
# Never touches: AMD, Gmail, Drive, the page. Writes only to a temp directory.
import os, sys, json, re, tempfile, time, types
import xml.etree.ElementTree as ET
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TMP = tempfile.mkdtemp(prefix="selftest_ws_")
os.environ["BILLING_WORKSPACE"] = TMP
sys.path.insert(0, os.path.join(ROOT, "scripts", "helpers")); sys.path.insert(1, os.path.join(ROOT, "core"))
import amd, resave, freq1_visit, move_to_ins, ins_update, approval_submit
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
import deceased_guard
deceased_guard.check_charge = lambda cid, seq: (True, "DOS after date of death")
c11 = amd.rebill_charge("803", 3)
check("deceased guard still blocks (409) and is not recorded", c11[0] == 409 and "v901:3" not in amd._REBILLED and len(CALLS) == 8, c11)

# ------------------------------------------------------------------ B. resave.set_insorder (no rebill)
def visit(order, n=2):
    v = ET.Element("visit", {"id": "vst900", "episode": "ep1", "insorder": order})
    lst = ET.SubElement(v, "insuranceorderlist")      # 11/10/2026: AdvancedMD builds the visit's insurance-order LIST from its order; set_insorder reads it
    for i, s in enumerate(x for x in order.replace(" ", "").split(",") if x): ET.SubElement(lst, "insuranceorder", {"sequence": s, "ordinal": str(i)})
    p = ET.Element("patient", {"id": "pat77"})
    cs = [ET.Element("charge", {"id": "charge%d" % (500 + k), "proccode": "pcode1", "fee": "100.00", "insbalance": "100.00"}) for k in range(n)]
    return v, p, cs
STATE = {"order": "1,2", "n": 2, "fault": False, "posts": []}
resave.visit_charges = lambda cid: visit(STATE["order"], STATE["n"])
def r_post(body, timeout=180):
    STATE["posts"].append(body)
    if STATE["fault"]: return "<PPMDResults><Error><Fault>boom</Fault></Error></PPMDResults>"
    m = re.search(r'<visit [^>]*insorder="([^"]*)"', body); STATE["order"] = m.group(1); return '<PPMDResults><Results success="1"/></PPMDResults>'
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

# ------------------------------------------------------------------ D. move_to_ins.move rebill flag
move_to_ins.time = types.SimpleNamespace(sleep=lambda s: None)
resave.detail = lambda cid: '<x><visit id="vst900" insorder="%s"/><charge id="charge500" insbalance="100.00" patbalance="0.00"/></x>' % STATE["order"]
REB.clear(); STATE["order"] = "1,2"; m1 = move_to_ins.move("500", "2,1", rebill=False)
check("move(..., rebill=False) never rebills", not REB and "no rebill" in m1, m1)
REB.clear(); m2 = move_to_ins.move("500", "1,2")
check("move(...) default keeps its single rebill (backward compatible)", REB == [("500", 1)], (REB, m2))

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

print("\n%d failure(s)" % len(FAILS) + (": " + ", ".join(FAILS) if FAILS else " - all guarantees hold"))
sys.exit(1 if FAILS else 0)
