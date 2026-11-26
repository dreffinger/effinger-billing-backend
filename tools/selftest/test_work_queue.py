#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 11/26/2026 - the work queue: William's answers "Yes, act" on denials and unpaid claims)
# Proves offline, on invented charts and the stand-in AdvancedMD these self-tests use (amd.post answered BY ACTION - gettxhistory,
#   getchargedetaildataicd10, getdemographic read invented rows, addpayments is recorded; the rebill helpers are recorders; no network):
#   T. ONE denial-code table (TABLE in working_denials.py): the board and the aging engine read it; 27/26/200/31/49 are wrong payer, CO-151 the re-date;
#      every code in the repository's denial data has a rule; every old board row kept its meaning.
#   P. the planner's rules, its holds and guards, and no name / birth date / chart number in work_queue.json.
#   A. the actor: dry by default, its skips (paid since the plan, the 30-day wait, watch / FLO99), ONE action per visit, the run cap,
#      the idempotent second start (its own register).
#   W. the write-off code guard and WOINSBANK's Treasury match.
#   R. the recovered block.   X. columns.txt agrees with billing_button.txt: no second rebill after dx_primary_fix.
#   F. the independent review of 11/26/2026 - ONE named check per finding (F1-F11): MATCHED-only Treasury rows, payments by posting date, the
#      crossover secondary, FLO99 on any line, the re-date's partial writes, overlapping runs, the payer's own claim number, step / code tied to
#      the rule, AdvancedMD's fault text kept out of the register, a dry start that buys nothing, the deceased guard before any edit.
# Run: python3 tools/selftest/test_work_queue.py    Never touches: AMD, Drive, the board. Writes only to a temp directory.
import datetime, glob, json, os, re, sys, tempfile, types
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("this self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TMP = tempfile.mkdtemp(prefix="selftest_wq_"); os.chdir(TMP); os.makedirs("registers"); os.makedirs("outbox")
os.environ["BILLING_WORKSPACE"] = TMP
os.environ["DECEASED_CACHE"] = os.path.join(TMP, "registers", "deceased_cache.json")      # the guard's cache in the temp directory, never the repository's
json.dump({"car1": ["FLO02", "Medicare"], "car2": ["BCBS", "Florida Blue"], "car3": ["FLO99", "FCC"], "car4": ["UNI20", "UHC"]}, open("carriers.json", "w"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "helpers")); sys.path.insert(1, os.path.join(ROOT, "core"))
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:300]))
    if not cond: FAILS.append(name)

import working_denials, work_queue as wq, work_queue_act as act
TODAY = datetime.date.today(); D = lambda n: (TODAY - datetime.timedelta(days=n)).isoformat()
WD = working_denials

# ------------------------------------------------------------------ T. the ONE table
_wds = [open(os.path.join(ROOT, d, "working_denials.py")).read() for d in ("boards", os.path.join("scripts", "helpers"))]
check("T1 ONE table: the board's DENIAL_RULES comes from its TABLE, and both copies of working_denials.py are the same file", _wds[0] == _wds[1]
      and WD.DENIAL_RULES == {k: (v[0], v[1]) for k, v in WD.TABLE.items()})
check("T2 27/26/200/31/49 are wrong payer on the board and in the aging family",
      all(WD.DENIAL_RULES[c][0] == "COB" for c in ("27", "26", "200", "31", "49")) and {"27", "26", "200", "31", "49"} <= WD.family("WRONG_PAYER"))
check("T3 CO-151 is the CCM re-date (FIX, family REDATE; aging keeps 151 in its non-covered set for a non-CCM line)",
      WD.DENIAL_RULES["151"][0] == "FIX" and "re-date" in WD.DENIAL_RULES["151"][1] and WD.family("REDATE") == {"151"})
for rel in ("tools/button/aging_refresh.py", "scripts/helpers/aging_refresh.py"):
    t_ = open(os.path.join(ROOT, rel)).read()
    m_ = re.search(r'^INFO_REASONS = \(([^)]*)\)', t_, re.M)
    check("T4 %s takes its code sets from the one table, and its INFO_REASONS (mirror.py's marker) is the table's" % rel,
          "from working_denials import family as _family" in t_ and '_family("WRONG_PAYER")' in t_ and m_ is not None
          and set(re.findall(r'"([0-9A-Z]+)"', m_.group(1))) == set(WD.INFO_REASONS))
old = {"16": "FIX", "B9": "FIX", "58": "REVIEW", "22": "COB", "29": "TIMELY", "204": "REVIEW", "242": "CRED", "1": "PATIENT", "18": "DUPLICATE", "45": "CONTRACTUAL", "246": "INFO"}
check("T5 old rows keep their disposition", all(WD.DENIAL_RULES[k][0] == v for k, v in old.items()))
seen = set()
w = json.load(open(os.path.join(ROOT, "reports", "button", "working_denials_latest.json")))
for v in w.get("visits", []):
    for c in v.get("codes") or []: seen.add(wq.norm(str(c).split("/")[-1]))
for l in wq.era_lines(glob.glob(os.path.join(ROOT, "practices", "ehpa", "registers", "era_denials_*.json"))):
    for ch in l["charges"]: seen |= {c for _, c in ch["carc"]}
missing = sorted(c for c in seen if c and working_denials.triage(c)[0] == "UNCLASSIFIED")
check("T6 every denial code in the repository's data has a rule or REVIEW (%d codes)" % len(seen), not missing, missing)

# ------------------------------------------------------------------ P. the planner
def ev_wd(vid, pid, carc, cpt="99309", carrier="BCBS", dos=D(60), bal=200.0, codes=None):
    return {"pid": pid, "visitid": vid, "carrier": carrier, "dos": dos, "cpt": cpt, "carc": carc, "codes": codes or ["CO/CO" + carc], "status": "OPEN", "open_balance": bal, "amt": bal, "rarc": []}
def ag(vid, pid, rec, rule, payer="FLO02", dos=D(100), bal=50.0, secondary="", sent=D(70), paid_by="", carcs=""):
    return {"visitid": vid, "pid": pid, "rec": rec, "rule": rule, "payer": payer, "dos": dos, "bal": bal, "secondary": secondary, "sent": sent, "paid_by": paid_by, "carcs": carcs, "cpts": "99309", "mods": ""}
inputs = {
 "wd": {"asof": TODAY.isoformat(), "visits": [ev_wd("1", "11", "27"), ev_wd("2", "12", "16"), ev_wd("3", "13", "B9"), ev_wd("4", "14", "B9", cpt="99487", codes=["CO/COB9"]),
                                              ev_wd("5", "15", "29"), ev_wd("6", "16", "16", dos=D(400)), ev_wd("7", "17", "16"), ev_wd("8", "18", "226"), ev_wd("13", "23", "22", carrier="FLO99")]},
 "era": [{"visitid": "2", "pid": "", "carrier": "BCBS", "dos": D(60), "claimstatus": 1, "charges": [{"cpt": "99309", "charge": "70002", "carc": [("CO", "16")], "rarc": ["MA63"]}], "rarc": [], "when": D(5), "icn": "", "file": "x"},
         {"visitid": "6", "pid": "", "carrier": "BCBS", "dos": D(400), "claimstatus": 1, "charges": [{"cpt": "99309", "charge": "70006", "carc": [("CO", "16")], "rarc": ["MA63"]}], "rarc": [], "when": D(5), "icn": "", "file": "x"},
         {"visitid": "9", "pid": "", "carrier": "FLO02", "dos": D(40), "claimstatus": 1, "charges": [{"cpt": "99487", "charge": "70009", "carc": [("CO", "151")], "rarc": []}, {"cpt": "99489", "charge": "70010", "carc": [("CO", "234")], "rarc": []}], "rarc": [], "when": D(3), "icn": "", "file": "x"}],
 "aging": {"asof": TODAY.isoformat(), "rows": [ag("9", "19", "WAIT", "sent 0-30 days ago - inside normal adjudication"),
                                               ag("10", "20", "CORRECT & RESEND", "primary paid - cost-share belongs to the live secondary on the chart: move it there and bill", secondary="BCBS", paid_by="FLO02"),
                                               ag("11", "21", "CORRECT & RESEND", "primary paid - cost-share belongs to the live secondary on the chart: move it there and bill", secondary="HUM01 WEL04", paid_by="FLO02"),
                                               ag("12", "22", "WRITE OFF", "primary unpaid > 12 months from DOS, no adjudication -> WOINS untimely (dated note)", dos=D(400)),
                                               ag("14", "24", "WRITE OFF", "primary paid, no secondary on the chart -> WOCLTREQ cost-share (10/13 rule: nothing stays on the patient)", paid_by="FLO02"),
                                               ag("15", "25", "CORRECT & RESEND", "sent 91-120 days ago, no answer -> verify the plan, fix and resend as original", sent=D(100)),
                                               ag("16", "26", "CORRECT & RESEND", "sent 61-90 days ago, no answer -> claim-status check; no record at the payer = resend as original", payer="BCBS", sent=D(70)),
                                               ag("17", "27", "CORRECT & RESEND", "sent 61-90 days ago, no answer -> claim-status check; no record at the payer = resend as original", sent=D(70)),
                                               ag("18", "28", "CORRECT & RESEND", "sent 91-120 days ago, no answer -> verify the plan, fix and resend as original", sent=D(100)),
                                               ag("19", "29", "WRITE OFF", "primary unpaid > 12 months from DOS, no adjudication -> WOINS untimely (dated note)", dos=D(400)),
                                               ag("20", "30", "CORRECT & RESEND", "sent 91-120 days ago, no answer -> verify the plan, fix and resend as original", sent=D(100)),
                                               ag("21", "31", "WAIT", "sent 31-60 days ago - watch", payer="BCBS", sent=D(80)), ag("22", "32", "WAIT", "sent 31-60 days ago - watch", payer="BCBS")]},
 "ledger": {"21|BCBS": {"vid": "21", "pid": "31", "payer": "BCBS", "answer": "paid", "final": True, "sent": D(80), "dos": D(90)},
            "22|BCBS": {"vid": "22", "pid": "32", "payer": "BCBS", "answer": "not found", "final": False, "sent": D(70), "dos": D(80)}},
 "cs": {"21": {"checks": ["CHK777"], "paid_on": D(20), "paid": 88.0, "icn": "ICN21"}},
 "acted": {"18": {"acted": TODAY - datetime.timedelta(days=10), "card": {}, "tries": 1}}, "rebilled": {}, "watch": {"19"}, "board": {"30"}, "appeals": {}}
q = wq.build(inputs, TODAY); R = {r["visitid"]: r for r in q["rows"]}
expect = {"1": "COB-WRONG-PAYER", "2": "FIX-DX-0914", "3": "FIX-HOSPICE-0920", "4": "WO-CCM-HOSPICE-1015", "5": "OWNER-APPEAL", "6": "OWNER-PAST-12M-1120", "7": "OWNER-CORRECT",
          "8": "OWNER-RECORDS", "9": "FIX-REDATE-1004", "10": "BILL-SECONDARY-1015", "11": "OWNER-TWO-SECONDARIES", "12": "WO-OLD-1102", "13": "HOLD-FLO99-0922",
          "14": "WAIT-COSTSHARE-12M", "15": "RESEND-SILENT-NOROUTE-1015", "16": "STATUS-BY-NEED-1110", "17": "WAIT-SILENT", "18": "WAIT-ACTED-30D", "19": "HOLD-TF-WATCH-1006",
          "20": "HOLD-BOARD", "21": "WO-PAID-NOT-POSTED-1102", "22": "RESEND-NOT-ON-FILE-1110"}
for vid, rule in expect.items():
    check("P1 visit %s -> %s" % (vid, rule), (R.get(vid) or {}).get("rule") == rule, (R.get(vid) or {}).get("rule"))
check("P2 the 11/2 rule names its code (WOINS) and the CCM hospice rule WONCS", R["12"].get("code") == "WOINS" and R["4"].get("code") == "WONCS")
check("P3 the re-date goes to the last day of the DOS month", R["9"].get("redate_to") == wq.last_day_of_month(datetime.date.fromisoformat(D(40))).isoformat())
check("P4 the paid-not-posted row carries the check number and ICN from the claim-status run file", R["21"].get("checks") == ["CHK777"] and R["21"].get("icn") == "ICN21")
check("P5 every row has a rule id, a step, a turn and a due date", all(r.get("rule") in wq.RULES and r.get("step") and r.get("turn") and r.get("due") for r in q["rows"]))
txt = json.dumps(q)
check("P6 no name / birth date / chart-number key in work_queue.json", not re.search(r'"(patient|name|dob|chart|member|subscribernum|mbi)"\s*:', txt))
check("P7 a remit's chart NUMBER is never copied", "HF0000000" not in json.dumps(wq.build({"era": [dict(inputs["era"][0], chart="HF0000000")], "aging": inputs["aging"], "wd": inputs["wd"]}, TODAY)))
check("P8 code_for: only named codes come back", wq.code_for("denied CO-29 timely filing -> WOLATE") == "WOLATE" and wq.code_for("bundled -> contractual write-off") is None)
fu = wq.build(dict(inputs, appeals={"5": D(31), "7": D(3)}), TODAY); F = {r["visitid"]: r for r in fu["rows"]}
check("P9 William's 'sent' starts the 30-day follow-up: due 30 days after the appeal went out", F["5"]["rule"] == "FOLLOWUP-APPEAL-1126" and F["5"]["due"] == TODAY.isoformat()
      and F["7"]["rule"] == "FOLLOWUP-APPEAL-1126" and F["7"]["due"] == (TODAY + datetime.timedelta(days=27)).isoformat(), (F["5"], F["7"]))

# ------------------------------------------------------------------ the stand-in AdvancedMD
import amd
CH = {}      # charge id -> dict(pid, vid, cpt, carrier, dos, insbal, patbal, billdate, pays=[(date, amt) or {date, amt, createtime, carrier, check, icn}], insbills, void)
POSTS = []; CALLS = []
RAISE = set(); FAULTPOST = set(); VOID_FAIL = set(); NEWV = [99000]; SA = {"newcharges_fault": False}      # stand-in switches of the F checks
CARNUM = {"FLO02": "1", "BCBS": "2", "FLO99": "3", "UNI20": "4"}      # carriers.json above: carN -> the payment's carrierfid is N
def charge(cid, pid, vid, carrier="FLO02", cpt="99309", insbal=100.0, patbal=0.0, dos=D(400), billdate=D(200), pays=(), insbills=()):
    CH[cid] = dict(pid=pid, vid=vid, carrier=carrier, cpt=cpt, insbal=insbal, patbal=patbal, dos=dos, billdate=billdate, pays=list(pays), insbills=list(insbills), void="0")
def mdy(iso): y, m, d = iso.split("-"); return "%s/%s/%s" % (m, d, y)
def _pays(c):
    for p in c["pays"]:
        p = p if isinstance(p, dict) else {"date": p[0], "amt": p[1]}
        yield dict({"createtime": p["date"], "carrier": c["carrier"], "check": "", "icn": ""}, **p)
def stand_in(body, timeout=180, **k):
    act_ = re.match(r'<ppmdmsg action="([^"]*)"', body).group(1)
    if act_ == "gettxhistory":
        pid = re.search(r'patientid="(\d+)"', body).group(1); vid = re.search(r'visitid="(\d+)"', body).group(1)
        rows = "".join('<charge id="%s" visit="%s" proccode="%s" carrier="%s" dos="%s" insbal="%.2f" patbal="%.2f" billdate="%s" fee="100.00" void="%s">%s</charge>' % (
            cid, c["vid"], c["cpt"], c["carrier"], mdy(c["dos"]), c["insbal"], c["patbal"], mdy(c["billdate"]) if c["billdate"] else "", c["void"],
            "".join('<payment amount="%.2f" date="%s" createtime="%s 10:00:00 AM" carrier="%s" checknumber="%s" void="0"/>' % (
                p["amt"], mdy(p["date"]), mdy(p["createtime"]), p["carrier"], p["check"]) for p in _pays(c)))
            for cid, c in CH.items() if c["pid"] == pid and (vid == "0" or c["vid"] == vid))
        return "<PPMDResults><Results>%s</Results></PPMDResults>" % rows
    if act_ == "getchargedetaildataicd10":
        cid = re.search(r'chargeid="(\d+)"', body).group(1); c = CH[cid]
        pays = "".join('<payment id="pay%s%d" paymentcode="PE" date="%s" amount="%.2f" checknumber="%s" carrierfid="%s" origrefnum="%s" void="0"/>' % (
            cid, i, mdy(p["date"]), p["amt"], p["check"], CARNUM.get(p["carrier"], ""), p["icn"]) for i, p in enumerate(_pays(c)))
        bills = "".join('<insbill carriername="%s" billeddate="%s" paperedi="%s" claimrun="%s"/>' % (b.get("carrier", ""), mdy(b["date"]), b.get("paperedi", "E"), b.get("run", "1"))
                        for b in c["insbills"])
        return ('<PPMDResults><Results><patient id="pat%s"/><visit id="vst%s" date="%s" profile="prof1" insorder="1,2"/><charge id="charge%s" insbalance="%.2f" insportion="%.2f" '
                'patportion="0.00" patbalance="0.00">%s</charge>%s</Results></PPMDResults>') % (c["pid"], c["vid"], mdy(c["dos"]), cid, c["insbal"], c["insbal"], pays, bills)
    if act_ == "getdemographic":
        return '<PPMDResults><Results><patient id="pat1" name="chart one" dob=""/><respparty id="resp1"/><insplan id="ins1" carrier="car1" sequence="1"/><insplan id="ins2" carrier="car2" sequence="2"/></Results></PPMDResults>'
    if act_ == "addpayments":
        if any("charge%s" % x in body for x in RAISE): raise RuntimeError("the connection dropped")
        if any("charge%s" % x in body for x in FAULTPOST):
            return '<PPMDResults><Error><Fault><detail><description>Patient INVENTED, PERSON 19500101 is locked by another user</description></detail></Fault></Error></PPMDResults>'
        POSTS.append(body); return '<PPMDResults success="1"/>'
    if act_ == "addvisit":
        NEWV[0] += 1; return '<PPMDResults><Results><visit id="vst%d"/></Results></PPMDResults>' % NEWV[0]
    if act_ == "updvisitwithnewcharges":
        if SA["newcharges_fault"]: return '<PPMDResults><Error><Fault><detail><description>invalid diagnosis pointer</description></detail></Fault></Error></PPMDResults>'
        nv = re.search(r'<visit id="vst(\d+)"', body).group(1); pid = re.search(r'patientid="pat(\d+)"', body).group(1)
        for i, (d, pc) in enumerate(re.findall(r'<charge id=""[^>]*begindate="([^"]*)"[^>]*proccode="([^"]*)"', body)):
            m_, d_, y_ = d.split("/"); charge("6%s%d" % (nv, i), pid, nv, cpt=pc.replace("pcode", ""), dos="%s-%s-%s" % (y_, m_, d_), billdate="")
        return '<PPMDResults><Results success="1"/></PPMDResults>'
    raise AssertionError("the stand-in AdvancedMD has no answer for %s" % act_)
amd.post = stand_in; amd.login_cached = lambda psw=None: ("https://web", "tok")
sys.modules.setdefault("era_post", types.ModuleType("era_post"))      # the real one opens a log beside itself in the repository at import
import freq1_visit, move_to_ins, dx_primary_fix, working_denials_act, resave
freq1_visit.run = lambda vid, cid, seq: CALLS.append(("freq1", str(vid), str(seq))) or "freq1 + rebill seq %s -> 204" % seq
freq1_visit.reroute = lambda vid, cid, order, seq=None, dry=False: CALLS.append(("reroute", str(vid), order, dry)) or ("DRY reroute" if dry else "order set | freq1 + rebill seq 1 -> 204")
move_to_ins.move = lambda cid, seq=None, dry=False, rebill_seq=None, rebill=True: CALLS.append(("move", str(cid), seq, dry, rebill)) or ("DRY move" if dry else "moved 0.00")
dx_primary_fix.fix_visit = lambda pid, vid, cid, seq="1", dry=False, bad=None, icn=None: CALLS.append(("dx", str(vid), icn, dry)) or ("DRY v%s move" % vid if dry else "MOVE v%s -> freq7 icn %s + rebill seq 1 -> 204" % (vid, icn))
working_denials_act.act = lambda item, dry: CALLS.append(("hospice", str(item["vid"]), dry)) or ("DRY save" if dry else "freq1 + rebill seq 1 -> 204")
import xml.etree.ElementTree as ET, deceased_guard
def visit_charges(cid):      # the visit of a charge as resave.visit_charges answers: visit (its insurance order), patient, every live charge's detail
    c0 = CH[str(cid)]
    lines = [ET.fromstring('<charge id="charge%s" proccode="pcode%s" diagcodes="dcode1 dcode2" pos="31" tos="01" units="1" fee="%.2f"/>' % (k, c["cpt"], c["insbal"]))
             for k, c in CH.items() if c["vid"] == c0["vid"] and c["void"] != "1"]
    return ET.fromstring('<visit id="vst%s" insorder="1" episode="ep1" profile="prof1" facility="fac1"/>' % c0["vid"]), ET.fromstring('<patient id="pat%s"/>' % c0["pid"]), lines
resave.visit_charges = visit_charges
deceased_guard.check = lambda pid, dos, carrier=None, proc=None, allow_lookup=True: (False, "no death on record")
import void_tx
def _void_charge(pid, cid):
    if str(cid) in VOID_FAIL: return False, "the charge has activity"
    CH[str(cid)]["void"] = "1"; return True, "voided"
void_tx.charge_state = lambda cid: (None, [], []); void_tx.void_charge = _void_charge
AGING_TXT = {"WOINS": "primary unpaid > 12 months from DOS, no adjudication -> WOINS untimely (dated note)",
             "WOCLTREQ": "primary paid > 12 months ago, the secondary's window is closed -> WOCLTREQ"}

def run(rows, *flags):
    json.dump({"planned": D(1) + "T00:00:00Z", "rows": rows}, open("registers/work_queue.json", "w"))
    out = []
    a = act.parse(["--registers", "registers", "--repo", "/nonexistent", "--stamp", "2026-11-26T0900Z"] + list(flags))
    act.Actor(a, out=out.append).run()
    return out
def qrow(vid, pid, rule, **kw):
    r = {"visitid": vid, "pid": pid, "payer": kw.pop("payer", "FLO02"), "dos": D(400), "amount": 100.0, "step": wq.RULES[rule][0], "rule": rule, "turn": wq.RULES[rule][1], "due": TODAY.isoformat()}
    r.update(kw)
    if rule == "WO-OLD-1102" and "aging_rule" not in r and r.get("code") in AGING_TXT: r["aging_rule"] = AGING_TXT[r["code"]]      # as the planner writes it
    return r

# ------------------------------------------------------------------ A. the actor
charge("70101", "101", "801"); charge("70102", "102", "802", pays=[(D(0), 25.0)]); charge("70103", "103", "803")
charge("70104", "104", "804", carrier="FLO99"); charge("70105", "105", "805"); charge("70106", "106", "806", billdate=D(10))
open("registers/rebill_log.jsonl", "w").write(json.dumps({"at": D(5) + "T01:00:00Z", "visit": "805", "charge": "70105", "seq": 1, "status": 204, "by": "x"}) + "\n")
json.dump({"items": [{"id": "w", "visits": [{"vid": "803"}]}]}, open("registers/tf_writeoff_watch.json", "w"))
rows = [qrow("801", "101", "WO-OLD-1102", code="WOINS"), qrow("802", "102", "WO-OLD-1102", code="WOINS"), qrow("803", "103", "WO-OLD-1102", code="WOINS"),
        qrow("804", "104", "WO-OLD-1102", code="WOINS"), qrow("805", "105", "RESEND-NOT-ON-FILE-1110"), qrow("806", "106", "RESEND-NOT-ON-FILE-1110")]
out = run(rows)
check("A1 dry by default: nothing posted, nothing rebilled, the register is the _dry file", not POSTS and not [c for c in CALLS if c[0] == "freq1"] and os.path.exists("registers/work_queue_act_2026-11-26T0900Z_dry.jsonl")
      and not os.path.exists("registers/work_queue_act_2026-11-26T0900Z.jsonl"), (POSTS, CALLS))
out = run(rows, "--live")
check("A2 live: the 11/2 write-off posts WOINS for the live insurance balance", len(POSTS) == 1 and 'code="WOINS"' in POSTS[0] and 'amount="100.00"' in POSTS[0] and "charge70101" in POSTS[0], POSTS)
J = "\n".join(out)
check("A3 skip: a payment came since the plan", "SKIP v802" in J and "payment came since the plan" in J)
check("A4 skip: on the timely-filing watch", "SKIP v803" in J and "timely-filing watch" in J)
check("A5 skip: FLO99 balance", "SKIP v804" in J and "FLO99" in J)
check("A6 skip: re-sent by any helper in the last 30 days (rebill_log) and a recent bill date", "SKIP v805" in J and "SKIP v806" in J and "30-day wait" in J)
reg = [json.loads(l) for l in open("registers/work_queue_act_2026-11-26T0900Z.jsonl")]
check("A7 the register: ids, action, rule id, dollars, result only", len(reg) == 1 and set(reg[0]) <= {"at", "stamp", "visit", "pid", "action", "rule", "dollars", "result", "ok", "live", "code"}
      and reg[0]["rule"] == "WO-OLD-1102" and reg[0]["dollars"] == 100.0, reg)
n_posts = len(POSTS); out = run(rows, "--live")
check("A8 idempotent: a second start the same day acts on nothing (its own register)", len(POSTS) == n_posts and "SKIP v801" in "\n".join(out) and "acted on" in "\n".join(out), out[-1:])
charge("70111", "111", "811", insbal=60.0); charge("70112", "112", "812", insbal=70.0)
POSTS.clear(); CALLS.clear()
out = run([qrow("811", "111", "WO-OLD-1102", code="WOINS"), qrow("811", "111", "RESEND-NOT-ON-FILE-1110")], "--live")
check("A9 one action per visit per run (two rows for one visit -> one action)", len(POSTS) + len([c for c in CALLS if c[0] == "freq1"]) == 1 and "one action per visit" in "\n".join(out), (POSTS, CALLS))
charge("70113", "113", "813"); charge("70114", "114", "814")
POSTS.clear()
out = run([qrow("813", "113", "WO-OLD-1102", code="WOINS"), qrow("814", "114", "WO-OLD-1102", code="WOINS")], "--live", "--max", "1")
check("A10 the run's cap: --max 1 acts once, the rest waits for the next run", len(POSTS) == 1 and "LATER" in "\n".join(out))
charge("70115", "115", "815"); CALLS.clear()
out = run([qrow("815", "115", "COB-WRONG-PAYER")], "--live")
check("A11 wrong payer is listed for the run's RULE C cascade - nothing sent", not CALLS and "CASCADE v815" in "\n".join(out))
out = run([qrow("815", "115", "COB-WRONG-PAYER")], "--live", "--reroute", "815=2,1")
check("A12 --reroute does ONE re-route with the cascade's order", CALLS == [("reroute", "815", "2,1", False)], CALLS)
charge("70116", "116", "816", dos=D(100)); CALLS.clear()
out = run([qrow("816", "116", "FIX-DX-0914", dos=D(100))], "--live")
check("A13 a dx correction with no payer claim number is William's card, never a guess", not CALLS and "CARD v816" in "\n".join(out) and "OWNER-NO-ICN" in "\n".join(out), out)
charge("70117", "117", "817", dos=D(100)); CALLS.clear()
out = run([qrow("817", "117", "FIX-DX-0914", dos=D(100), icn="ICN817")], "--live")
check("A14 with the claim number the dx cascade resends as frequency 7", CALLS == [("dx", "817", "ICN817", False)], CALLS)
charge("70118", "118", "818", dos=D(100), billdate=D(90), pays=[(D(60), 50.0)]); CALLS.clear()      # Medicare paid 60 days ago, nothing billed since
out = run([qrow("818", "118", "BILL-SECONDARY-1015", dos=D(100), secondary="BCBS")], "--live")
check("A15 the secondary: the visit order gains its sequence (move_to_ins, no rebill), then ONE frequency-1 rebill to it",
      CALLS == [("move", "70118", "1,2", False, False), ("freq1", "818", "2")], CALLS)
charge("70119", "119", "819", cpt="99487", dos=D(40), billdate=D(35)); charge("70120", "119", "819", cpt="99489", dos=D(40), billdate=D(35))
out = run([qrow("819", "119", "FIX-REDATE-1004", dos=D(40))])
check("A16 CO-151 on CCM (dry): ONE new visit on the month's last day with both lines, the old lines voided",
      "DRY would re-enter 2 line(s) on %s" % wq.last_day_of_month(datetime.date.fromisoformat(D(40))).strftime("%m/%d/%Y") in "\n".join(out), out)
charge("70131", "131", "831", dos=D(100), billdate=D(90))
os.makedirs("board/items", exist_ok=True); json.dump({"id": "other-131", "amdid": "131", "patient": "chart 131 twin", "dob": "", "status": "done"}, open("board/items/other-131.json", "w"))
out = run([qrow("831", "131", "OWNER-APPEAL", dos=D(100), codes=["CO50"], kind="appeal: CO-50")], "--live", "--board-file", "outbox/board_updates_t.json", "--items-dir", "board")
bf = json.load(open("outbox/board_updates_t.json")); ops = [o for o in bf["ops"] if o["id"] == "denial-131-831"]
check("A17 William's turn: ONE card per visit in the run's board file (status william, twinned by chart, no `updated`), and the APPEAL line",
      len(ops) == 1 and ops[0]["set"]["status"] == "william" and ops[0]["set"].get("twins") == ["other-131"] and "updated" not in json.dumps(bf) and "APPEAL v831" in "\n".join(out), (ops, out[-3:]))
out = run([qrow("831", "131", "OWNER-APPEAL", dos=D(100), codes=["CO50"])], "--live", "--board-file", "outbox/board_updates_t2.json", "--items-dir", "board")
check("A18 the card is not made twice", not os.path.exists("outbox/board_updates_t2.json") and "already on William's turn" in "\n".join(out))

# ------------------------------------------------------------------ W. the write-off guard, WOINSBANK
def refused(*a, **k):
    try: act.guard_writeoff(*a, **k); return False
    except act.Refused: return True
check("W1 a code the rulebook does not name is refused (WOBAD, WOCOUR)", refused("WOBAD", "WO-OLD-1102", "FLO02") and refused("WOCOUR", "WO-OLD-1102", "FLO02"))
check("W2 no rule id, no write-off", refused("WOINS", None, "FLO02") and refused("WOINS", "COB-WRONG-PAYER", "FLO02"))
check("W3 FLO99 is never written off", refused("WOINS", "WO-OLD-1102", "FLO99"))
check("W4 WOINSBANK only with a Treasury match, and a paid-not-posted claim only WOINSBANK", refused("WOINSBANK", "WO-PAID-NOT-POSTED-1102", "BCBS") and refused("WOINS", "WO-PAID-NOT-POSTED-1102", "BCBS", treasury_ok=True)
      and not refused("WOINSBANK", "WO-PAID-NOT-POSTED-1102", "BCBS", treasury_ok=True))
open("deposits_ledger.csv", "w").write("date,amount,descriptor,family,era_check,status\n%s,88.00,Bcbsf,BCBS,0CHK777,matched\n" % D(18))
charge("70121", "121", "821", carrier="BCBS", insbal=88.0, dos=D(90), billdate=D(80)); charge("70122", "122", "822", carrier="BCBS", insbal=40.0, dos=D(90), billdate=D(80))
POSTS.clear()
out = run([qrow("821", "121", "WO-PAID-NOT-POSTED-1102", payer="BCBS", code="WOINSBANK", checks=["CHK777"], paid_on=D(20)),
           qrow("822", "122", "WO-PAID-NOT-POSTED-1102", payer="BCBS", code="WOINSBANK", checks=["CHK999"], paid_on=D(20))], "--live", "--treasury", "deposits_ledger.csv")
check("W5 the check matches a Treasury deposit -> WOINSBANK with that check number", len(POSTS) == 1 and 'code="WOINSBANK"' in POSTS[0] and 'checknumber="CHK777"' in POSTS[0] and "charge70121" in POSTS[0], POSTS)
check("W6 no match -> a LIST line, nothing written", "LIST v822" in "\n".join(out) and not any("charge70122" in p for p in POSTS))
check("W7 Treasury ledger: check numbers compare without leading zeros or punctuation", wq.norm_check("0CHK-777") == wq.norm_check("CHK777"))

# ------------------------------------------------------------------ F. the independent review of 11/26/2026: ONE named check per finding
def lines_of(vid): return [e for e in (json.loads(l) for l in open("registers/work_queue_act_2026-11-26T0900Z.jsonl") if l.strip()) if e["visit"] == vid]
# F1 - the Treasury ledger's status column: only MATCHED counts, in every file
open("ledger_f1.csv", "w").write("date,amount,descriptor,family,era_check,status\n%s,88.00,Bcbsf,BCBS,CHK911,POSSIBLE\n%s,88.00,Bcbsf,BCBS,CHK912,PROBABLE\n" % (D(18), D(18)))
open("ledger_f1b.csv", "w").write("date,amount,descriptor,family,era_check\n%s,88.00,Bcbsf,BCBS,CHK913\n" % D(18))
for i in (1, 2, 3): charge("7910%d" % i, "910%d" % i, "910%d" % i, carrier="BCBS", insbal=88.0, dos=D(90), billdate=D(80))
POSTS.clear()
out = run([qrow("910%d" % i, "910%d" % i, "WO-PAID-NOT-POSTED-1102", payer="BCBS", code="WOINSBANK", checks=["CHK91%d" % i], paid_on=D(20)) for i in (1, 2, 3)],
          "--live", "--treasury", "ledger_f1.csv,ledger_f1b.csv")
J = "\n".join(out)
check("F1 (finding 1) WOINSBANK only on a Treasury row whose status is exactly MATCHED: POSSIBLE, PROBABLE and a row with no status -> LIST, nothing posted",
      not POSTS and all("LIST v910%d" % i in J for i in (1, 2, 3)) and wq.treasury_checks(["ledger_f1.csv", "ledger_f1b.csv"]) == {}, (POSTS, out[-1:]))
# F2 - payments by when they were POSTED (createtime), on the basis day too; the check already posted; the payer that already paid
late = {"date": D(15), "amt": 60.0, "createtime": TODAY.isoformat()}      # a remit POSTED today whose check is dated 15 days ago (before the plan's basis)
charge("79201", "9201", "9201", insbal=40.0, pays=[late])
charge("79202", "9202", "9202", insbal=40.0, dos=D(120), billdate=D(100), pays=[late])
charge("79203", "9203", "9203", carrier="BCBS", insbal=40.0, dos=D(90), billdate=D(80), pays=[{"date": D(20), "amt": 48.0, "createtime": D(12), "check": "CHK920"}])
charge("79204", "9204", "9204", insbal=40.0, dos=D(120), billdate=D(100), pays=[(D(100), 60.0)])      # the payer paid long before the plan
open("ledger_f2.csv", "w").write("date,amount,descriptor,family,era_check,status\n%s,48.00,Bcbsf,BCBS,CHK920,MATCHED\n" % D(19))
POSTS.clear(); CALLS.clear()
out = run([qrow("9201", "9201", "WO-OLD-1102", code="WOINS", basis=D(10)), qrow("9202", "9202", "RESEND-NOT-ON-FILE-1110", dos=D(120), basis=D(10)),
           qrow("9203", "9203", "WO-PAID-NOT-POSTED-1102", payer="BCBS", code="WOINSBANK", checks=["CHK920"], paid_on=D(20), dos=D(90), basis=D(10)),
           qrow("9204", "9204", "RESEND-NOT-ON-FILE-1110", dos=D(120), basis=D(10))], "--live", "--treasury", "ledger_f2.csv")
J = "\n".join(out)
check("F2 (finding 2) 'a payment since the plan' goes by when it was POSTED (posted today, check dated before the plan): WRITE_OFF and RESEND skip; a check already posted "
      "on the visit is never WOINSBANK; no resend to a payer that already paid on the visit",
      not POSTS and not [c for c in CALLS if c[0] == "freq1"] and "SKIP v9201 WO-OLD-1102: a payment came since the plan" in J and "SKIP v9202 RESEND-NOT-ON-FILE-1110: a payment came since the plan" in J
      and "SKIP v9203 WO-PAID-NOT-POSTED-1102: check CHK920 is already posted on the visit" in J and "SKIP v9204 RESEND-NOT-ON-FILE-1110: FLO02 already paid on this visit" in J, (POSTS, CALLS, out))
# F3 - the crossover: the actor reads the claim detail first; the planner sends 'billed on/after the primary paid' to claim status
def ag3(vid, sec, sent, paid):
    return {"visitid": vid, "pid": vid, "rec": "CORRECT & RESEND", "rule": "primary paid - cost-share belongs to the live secondary on the chart: move it there and bill",
            "payer": "FLO02", "dos": D(90), "bal": 40.0, "secondary": sec, "sent": sent, "paid_on": paid, "paid_by": "FLO02", "carcs": "", "cpts": "99309", "mods": ""}
q3 = wq.build({"aging": {"asof": TODAY.isoformat(), "rows": [ag3("9311", "BCBS", D(40), D(45)), ag3("9312", "AAR01", D(65), D(70)), ag3("9313", "BCBS", D(67), D(70)), ag3("9314", "BCBS", D(75), D(70))]}}, TODAY)
R3 = {r["visitid"]: (r["rule"], r.get("payer")) for r in q3["rows"]}
charge("79301", "9301", "9301", insbal=40.0, dos=D(80), billdate=D(70), pays=[(D(45), 110.0)],
       insbills=[{"carrier": "FLORIDA MEDICARE", "date": D(70)}, {"carrier": "FLORIDA BLUE", "date": D(45), "paperedi": "X", "run": "N/A"}])
CALLS.clear()
out = run([qrow("9301", "9301", "BILL-SECONDARY-1015", dos=D(80), secondary="BCBS", amount=40.0)], "--live")
check("F3 (finding 3) a secondary that already holds the claim (an X-marked crossover bill) is never moved or rebilled; the planner never bills a secondary again when the claim "
      "was billed on/after the primary's payment: its answer is awaited 61 days, then its claim status goes to William (one card) - never a second claim",
      not CALLS and "SKIP v9301 BILL-SECONDARY-1015: the secondary already holds the claim" in "\n".join(out)
      and R3 == {"9311": ("WAIT-CROSSOVER-0921", "BCBS"), "9312": ("OWNER-CROSSOVER-SILENT-0921", "AAR01"), "9313": ("OWNER-CROSSOVER-SILENT-0921", "BCBS"), "9314": ("BILL-SECONDARY-1015", "FLO02")},
      (CALLS, out, R3))
# F4 - FLO99 on any line; every write-off line guarded before the first post; a post that breaks off is still recorded
charge("79401", "9401", "9401", insbal=70.0); charge("79402", "9401", "9401", carrier="FLO99", insbal=30.0)
charge("79403", "9403", "9403", insbal=70.0); charge("79404", "9403", "9403", carrier="ZZZ01", insbal=30.0)      # the second line has no carrier code
charge("79405", "9405", "9405", insbal=60.0); charge("79406", "9405", "9405", insbal=40.0); RAISE.add("79406")    # the second post breaks off
POSTS.clear()
out = run([qrow("9401", "9401", "WO-OLD-1102", code="WOINS"), qrow("9403", "9403", "WO-OLD-1102", code="WOINS", payer="ZZZ01"), qrow("9405", "9405", "WO-OLD-1102", code="WOINS")], "--live")
RAISE.clear(); J = "\n".join(out); l4 = lines_of("9405")
check("F4 (finding 4) FLO99 on ANY line holds the visit; every write-off line is guarded before the first post (nothing posted when one line fails); a post that breaks "
      "off midway is still recorded (ok=False)",
      "SKIP v9401 WO-OLD-1102: FLO99 balance on a line" in J and "REFUSED v9403" in J and not any("charge79401" in p or "charge79403" in p for p in POSTS)
      and len(l4) == 1 and l4[0]["ok"] is False and "c79405 WOINS $60.00 ok" in l4[0]["result"] and any("charge79405" in p for p in POSTS), (out, l4))
# F5 - the CO-151 re-date: a partial write is recorded at once and counts as acted; failures void what was written and card William
charge("79501", "9501", "9501", cpt="99487", dos=D(40), billdate=D(35)); SA["newcharges_fault"] = True; n0 = NEWV[0]
out = run([qrow("9501", "9501", "FIX-REDATE-1004", dos=D(40))], "--live"); out2 = run([qrow("9501", "9501", "FIX-REDATE-1004", dos=D(40))], "--live")
SA["newcharges_fault"] = False
charge("79502", "9502", "9502", cpt="99487", dos=D(40), billdate=D(35)); VOID_FAIL.add("79502")
out3 = run([qrow("9502", "9502", "FIX-REDATE-1004", dos=D(40))], "--live")
VOID_FAIL.clear(); l1, l2 = lines_of("9501"), lines_of("9502")
check("F5 (finding 5) the CO-151 re-date records its new visit at once (wrote) and counts it as acted - a second start makes no second new visit; a failed charge step and "
      "an old line that cannot be voided end ok=False with William's card",
      NEWV[0] - n0 == 2 and any(e.get("wrote") and e.get("new_visit") for e in l1) and "SKIP v9501" in "\n".join(out2)
      and [e["ok"] for e in l1 if e["action"] == "REDATE"] == [False, False] and any(e["action"] == "CARD" and e["rule"] == "OWNER-REDATE-1004" for e in l1)
      and [e["ok"] for e in l2 if e["action"] == "REDATE"] == [False, False] and any(e["action"] == "CARD" and e["rule"] == "OWNER-REDATE-1004" and "not voided" in e["result"] for e in l2),
      (out, out2, out3, l1, l2))
# F6 - overlapping runs: the repository's registers merged in right before the live pass; the prompts' lock
os.makedirs("repo_regs", exist_ok=True)
open("repo_regs/work_queue_act_2026-11-26T0215Z.jsonl", "w").write(json.dumps({"at": TODAY.isoformat() + "T02:20:00Z", "stamp": "2026-11-26T0215Z", "visit": "9601", "pid": "9601",
    "action": "RESEND", "rule": "RESEND-NOT-ON-FILE-1110", "dollars": 100.0, "result": "freq1 + rebill seq 1 -> 204", "ok": True, "live": True}) + "\n")
open("repo_regs/rebill_log.jsonl", "w").write(json.dumps({"at": TODAY.isoformat() + "T02:20:00Z", "visit": "9601", "charge": "79601", "seq": 1, "status": 204, "by": "freq1_visit.py"}) + "\n")
m1 = wq.merge_registers("repo_regs", "registers"); m2 = wq.merge_registers("repo_regs", "registers")
charge("79601", "9601", "9601", dos=D(120), billdate=D(100)); CALLS.clear()
out = run([qrow("9601", "9601", "RESEND-NOT-ON-FILE-1110", dos=D(120))], "--live")
prompts = [open(os.path.join(ROOT, "nightly", "live", f)).read() for f in ("billing_button.txt", "columns.txt", "cascade.txt")]
check("F6 (finding 6) overlapping runs: `work_queue.py merge` adds the repository's act-register and rebill_log lines to the workspace (once, nothing removed) so this workspace "
      "skips a visit another run rebilled; the three prompts take the Drive 'work queue RUNNING' lock and pull + merge right before the live pass",
      m1 == (2, 1, 1) and m2 == (0, 0, 0) and not [c for c in CALLS if c[0] == "freq1"] and "SKIP v9601" in "\n".join(out)
      and all("work queue RUNNING" in t and "pull --ff-only" in t and "work_queue.py merge" in t for t in prompts), (m1, m2, out))
# F7 - frequency 7 only with THAT payer's well-formed claim number
charge("79701", "9701", "9701", dos=D(100), billdate=D(90))
charge("79702", "9702", "9702", dos=D(100), billdate=D(90), pays=[{"date": D(70), "amt": 0.0, "carrier": "BCBS", "check": "B77", "icn": "BCBSICN0001"}])
CALLS.clear()
out = run([qrow("9701", "9701", "FIX-DX-0914", dos=D(100), icn="   "), qrow("9702", "9702", "FIX-DX-0914", dos=D(100))], "--live")
import freq7_visit
J = "\n".join(out)
check("F7 (finding 7) frequency 7 only with THAT payer's well-formed claim number: a blank ICN and another payer's ICN -> William's OWNER-NO-ICN card, nothing sent; "
      "freq7_visit.run refuses a blank claim number",
      not [c for c in CALLS if c[0] == "dx"] and "CARD v9701 pat9701 OWNER-NO-ICN" in J and "CARD v9702 pat9702 OWNER-NO-ICN" in J
      and freq7_visit.run("9702", "79702", "1", "   ") == "REFUSED freq7: no payer claim number", (CALLS, out))
# F8 - the step its rule names; the code its rule names
charge("79801", "9801", "9801", dos=D(120), billdate=D(100)); CALLS.clear()
bad = qrow("9801", "9801", "HOLD-AET12-0921", dos=D(120)); bad["step"] = "RESEND"      # a damaged row: the AET12 hold with a RESEND step
out = run([bad], "--live")
check("F8 (finding 8) the action is the step its RULE names (a HOLD row whose step says RESEND is refused) and each write-off code is the one its rule names "
      "(WO-CCM-MEDICAID-0911 is WONCS; WO-OLD-1102 takes the code of its aging rule)",
      not CALLS and "REFUSED v9801 HOLD-AET12-0921: step RESEND does not match its rule" in "\n".join(out)
      and refused("WOINS", "WO-CCM-MEDICAID-0911", "MCAD") and not refused("WONCS", "WO-CCM-MEDICAID-0911", "MCAD")
      and refused("WOCLTREQ", "WO-OLD-1102", "FLO02", aging_rule=AGING_TXT["WOINS"]) and not refused("WOINS", "WO-OLD-1102", "FLO02", aging_rule=AGING_TXT["WOINS"]), (CALLS, out))
# F9 - AdvancedMD's fault text stays out of the register
charge("79901", "9901", "9901"); FAULTPOST.add("79901")
out = run([qrow("9901", "9901", "WO-OLD-1102", code="WOINS")], "--live")
FAULTPOST.clear(); l9 = lines_of("9901"); lp = os.path.join("logs", "work_queue_act_2026-11-26T0900Z.log")
log9 = open(lp).read() if os.path.exists(lp) else ""
check("F9 (finding 9) AdvancedMD's fault text never reaches the register or the report line (cut at FAILED / FAULT); the whole answer is only in the workspace log",
      len(l9) == 1 and l9[0]["result"].endswith("FAILED") and not re.search(r"INVENTED|19500101", json.dumps(l9) + "\n".join(out)) and "INVENTED" in log9, (l9, out[-2:]))
# F10 - a dry start buys nothing outside: no date-of-death look-up, no eligibility
LOOK, ELIG = [], []
deceased_guard.check = lambda pid, dos, carrier=None, proc=None, allow_lookup=True: (LOOK.append(allow_lookup), (False, ""))[1]
import elig_amd
_run_plan = elig_amd.run_plan; elig_amd.run_plan = lambda pid, insid, force=False: ELIG.append(pid) or {"status": "ACTIVE"}
charge("79951", "9951", "9951", dos=D(130), billdate=D(110)); charge("79952", "9952", "9952", cpt="99487", dos=D(40), billdate=D(35))
out = run([qrow("9951", "9951", "RESEND-SILENT-NOROUTE-1015", dos=D(130)), qrow("9952", "9952", "FIX-REDATE-1004", dos=D(40))])      # no --live
elig_amd.run_plan = _run_plan; deceased_guard.check = lambda pid, dos, carrier=None, proc=None, allow_lookup=True: (False, "no death on record")
J = "\n".join(out)
check("F10 (finding 10) a dry start buys no date-of-death look-up (the guard is asked with allow_lookup=False and says 'date of death not checked') and asks no eligibility "
      "(RESEND-SILENT-NOROUTE prints its DRY line before the free checks)",
      LOOK and not any(LOOK) and not ELIG and "DRY free checks" in J and "DRY - date of death not checked" in J, (LOOK, ELIG, out))
# F11 - the deceased guard before any helper edits a visit it will send
deceased_guard.check = lambda pid, dos, carrier=None, proc=None, allow_lookup=True: (str(pid) == "9971", "blocked")
charge("79971", "9971", "9971", dos=D(100), billdate=D(90)); CALLS.clear()
r11 = qrow("9971", "9971", "FIX-HOSPICE-0920", dos=D(100))
out = run([r11], "--live"); out2 = run([r11], "--live")
deceased_guard.check = lambda pid, dos, carrier=None, proc=None, allow_lookup=True: (False, "no death on record")
l11 = lines_of("9971")
q11 = wq.build({"wd": {"asof": TODAY.isoformat(), "visits": [ev_wd("9971", "9971", "B9", carrier="FLO02", dos=D(100))]}, "acted": wq.last_actions(wq.act_lines(["registers"]))}, TODAY)
check("F11 (finding 11) the deceased guard is asked before any helper edits a visit it will send: a block = no edit, a HOLD-DEATH line, the visit on the date-of-death list; "
      "the next start and the planner hold it",
      not CALLS and [e["action"] for e in l11] == ["HOLD-DEATH"] and os.path.exists("outbox/work_queue_death_2026-11-26T0900Z.json")
      and "SKIP v9971 FIX-HOSPICE-0920: held" in "\n".join(out2) and [r["rule"] for r in q11["rows"]] == ["HOLD-DEATH"], (CALLS, l11, out, out2, q11["rows"]))

# ------------------------------------------------------------------ R. the recovered block
mon, sun = wq.week_of(TODAY)
lines = [{"at": (mon - datetime.timedelta(days=3)).isoformat() + "T01:00:00Z", "visit": "1", "pid": "9", "action": "RESEND", "rule": "RESEND-NOT-ON-FILE-1110", "dollars": 150.0, "ok": True, "live": True},
         {"at": mon.isoformat() + "T01:00:00Z", "visit": "2", "pid": "9", "action": "SECONDARY", "rule": "BILL-SECONDARY-1015", "dollars": 40.0, "ok": True, "live": True},
         {"at": mon.isoformat() + "T02:00:00Z", "visit": "3", "pid": "9", "action": "WRITE_OFF", "rule": "WO-OLD-1102", "dollars": 75.5, "ok": True, "live": True, "code": "WOINS"}]
worked = wq.worked_visits(lines)
pays = {"1": [((mon - datetime.timedelta(days=5)).isoformat(), 99.0), (mon.isoformat(), 120.0)], "2": [(mon.isoformat(), 30.0)], "3": [(mon.isoformat(), 10.0)]}
b = wq.recovered_block(worked, pays, lines, TODAY, {"rebills": 507, "visits": 486, "paid_visits": 10, "paid_after": 1234.5})
check("R1 recovered: insurance money posted this week AFTER the queue's action on the claims it worked (a payment before the action and a written-off claim do not count)",
      b["recovered"] == 120.0 and b["claims"] == 1, b)
check("R2 re-sent this week and written off by code", b["resent"] == 40.0 and b["written_off"] == {"WOINS": 75.5}, b)
check("R3 paid_since per worked visit and the baseline in the line", wq.paid_since(pays["1"], worked["1"]["at"]) == 120.0 and "507 rebills" in b["line"] and b["line"].startswith("Recovered this week"), b["line"])
dr = open(os.path.join(ROOT, "tools", "button", "denials_refresh.py")).read()
check("R4 denials_refresh writes paid_since and the recovered block", 'v["paid_since"]' in dr and 'out["recovered"] = _wq.recovered_block' in dr and open(os.path.join(ROOT, "scripts", "helpers", "denials_refresh.py")).read() == dr)

# ------------------------------------------------------------------ X. the prompts agree
cl = open(os.path.join(ROOT, "nightly", "live", "columns.txt")).read().splitlines()[16]
check("X1 columns.txt agrees with billing_button.txt: no freq1_visit.run after dx_primary_fix", "never follow them with freq1_visit.run" in cl and "when the denial is a primary-position diagnosis, then freq1_visit.run" not in cl, cl[:200])
for f in ("billing_button.txt", "columns.txt"):
    t = open(os.path.join(ROOT, "nightly", "live", f)).read()
    check("X2 %s runs the planner, then the actor live" % f, "python3 work_queue.py" in t and "work_queue_act.py --live" in t)

print("\n%d check(s) failed" % len(FAILS) if FAILS else "\nall checks passed")
sys.exit(1 if FAILS else 0)
