# PLAIN ENGLISH (10/6/2026 chat cascade from the 10/5 scan pile - FINAL after the 01:37Z refusal + the 02:00Z review; one letter per chart)
# Decides: Nothing new - applies William's standing rules to the charts the paper pile flagged. Runs only after William approves the card(s).
#  A. Hogarth (chart 17470940): the AARP Medicare-supplement plan ins9510183 sits on carrier UNI20 (UHC commercial) -> carrier AAR01 (car6600, AARP Medigap);
#     the rejected secondary 19455208B (run 1700265 'subscriber id not found') is completed off Exclusions - Medigap secondaries ride the Medicare crossover (9/13 rule).
#  B. Marlow (chart 12232248): Florida Blue plan ins6029665 is dead (AMD 271 AAA 75) -> end date 06/21/2025 (day before the first denied DOS); chart order 2,1
#     (AARP Medicare Advantage first). The 9/20/2026 CCM visit already went to UNI20 on 9/30 - NO rebill. 2025 wrong-payer balances sitting on the PATIENT
#     (no payment on the charge) move back to insurance with no rebill (William 9/3: wrong-payer denials never sit on the statement; the payer decision is his).
#  C. Ulverston (chart 17474493): UHC Dual Complete LPPO (UNI20 seq 3) is the Medicare Advantage plan on the DOS -> chart order 3,2 (MA first, Sunshine Medicaid second);
#     9/30 + 10/1 visits: insorder 3,2 (resave, no rebill) then frequency-1 reset + ONE rebill to seq 3; the unbilled 10/3 visit: insorder 3,2 only.
#  D. Kirkbride (chart 17475338) v19431100: post the Medicare contractual the ERA poster never applied (WOINS 153.50, check 819814877) and chart order 2,1
#     (Medicare first). The dx fix + frequency-7 Florida Blue resend were done by the 01:10Z routine run - not repeated here.
#  E. Carraway (chart 17472143) ins9511482 / F. Elmsley (chart 17473335) ins9513920: the same AARP Medigap carrier fix as A (their 271s read the same way).
# Rules it uses: updateinsurance wipes the chart's patient insurance order (9/21 behaviour) -> the order is read first and re-asserted after every plan edit;
#   a resave that changes nothing is skipped; every rebill is ONE frequency-1 reset + ONE chargerebill (freq1_visit), never move_to_ins's own rebill.
# Never touches: paid lines; Parsons (needs the Medicare card); the Kirkbride Florida Blue secondary (already sent); Marlow's write-off decision.
# Usage: python3 chat_1006_cascade.py [--live] [--only A,B,C,D,E,F]      register: chat_1006_cascade_<live|dry>_<letters>.json (stamp inside)
import sys, re, json, time
sys.path.insert(0, "/home/claude/unbilled")
import amd, resave, ins_update, freq1_visit, manual_post, move_to_ins, txh
LIVE = "--live" in sys.argv
LETTERS = ("A", "B", "C", "D", "E", "F")
ONLY = set(x.strip().upper() for a in sys.argv if a.startswith("--only") for x in (sys.argv[sys.argv.index(a) + 1] if a == "--only" and sys.argv.index(a) + 1 < len(sys.argv) else a.split("=", 1)[-1]).split(",") if x.strip()) or set(LETTERS)
bad = sorted(ONLY - set(LETTERS))
if bad: sys.exit("unknown --only letter(s) %s - valid: %s" % (bad, ",".join(LETTERS)))
def want(letter): return letter in ONLY
STAMP = time.strftime("%Y-%m-%dT%H%MZ", time.gmtime())
REGFILE = "/home/claude/unbilled/chat_1006_cascade_%s_%s.json" % ("live" if LIVE else "dry", "".join(sorted(ONLY)))
REG = {"stamp": STAMP, "live": LIVE, "only": "".join(sorted(ONLY)), "steps": []}
def log(*a): print(*a, flush=True); REG["steps"].append(" ".join(str(x) for x in a))
def chart_order(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', r); seqs = re.findall(r'<insplan [^>]*?sequence="([^"]*)"', r)
    return (m.group(1) if m else ""), seqs
def hide_excl(runid, pairs):
    if not LIVE: return log("DRY hideexclusions", runid, pairs)
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": str(runid), "hide": "-1", "nocookie": "1"},
                 "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in pairs)))
    log("hideexclusions", runid, pairs, re.sub(r"\s+", " ", r)[:160])
def upd(pid, insid, **ch):
    if not LIVE: return log("DRY ins_update", pid, insid, ch)
    ok, msg = ins_update.update(pid, insid, **ch); log("ins_update", pid, insid, ch, ok, str(msg)[:120]); return ok
def plan_edit(pid, insid, want_order, **ch):
    """edit one plan, then re-assert the chart's patient insurance order (updateinsurance wipes it - 9/21 behaviour)"""
    before, seqs = chart_order(pid); log("chart", pid, "order before", repr(before), "plan seqs", seqs)
    upd(pid, insid, **ch)
    order = want_order or before
    if order: upd(pid, insid, sequence=order)
    if LIVE: after, _ = chart_order(pid); log("chart", pid, "order after", repr(after), "(wanted %s)" % order)
def set_insorder(tag, cid, order):
    """visit insorder via a full-visit echo - no rebill; skipped when already there"""
    vis, pat, allc = resave.visit_charges(cid)
    if vis.get("insorder") == order: return log(tag, "visit", vis.get("id"), "insorder already", order, "- resave skipped")
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order
    if not LIVE: return log("DRY", tag, "resave", vis.get("id"), "insorder", vis.get("insorder"), "->", order, "(%d live charges echoed)" % len(allc))
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r: return log(tag, "resave FAULT", cid, re.sub(r"\s+", " ", r[:200]))
    v2, p2, c2 = resave.visit_charges(cid); log(tag, "resave", vis.get("id"), "insorder now", v2.get("insorder"), "%d live (was %d)" % (len(c2), len(allc)))
def freq1(tag, vid, cid, seq):
    if LIVE: log(tag, "freq1", vid, cid, "seq", seq, "->", freq1_visit.run(vid, cid, seq))
    else: log("DRY", tag, "freq1_visit.run(%s, %s, %s)" % (vid, cid, seq))
def patient_balances_to_insurance(tag, pid, year):
    """every charge of <year> with a PATIENT balance and no live payment -> insurance side, no rebill (wrong-payer transfers never sit on the statement)"""
    el = txh.fetch(pid); done = set()
    for c in el.iter("charge"):
        a = c.attrib; cid = a.get("id"); dos = a.get("dos") or ""
        if not dos.strip().endswith(str(year)) or float(a.get("patbal") or 0) <= 0 or cid in done: continue
        if any(p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0 for p in c.iter("payment")): log(tag, "skip", cid, dos, "has a payment"); continue
        done.add(cid)
        if LIVE: log(tag, "move_to_ins", cid, dos, a.get("proccode") or a.get("chgcode"), "$" + a.get("patbal"), "->", move_to_ins.move(cid))
        else: log("DRY", tag, "move_to_ins.move(%s) %s %s $%s ->" % (cid, dos, a.get("proccode") or a.get("chgcode"), a.get("patbal")), move_to_ins.move(cid, dry=True))
amd.login_cached()
try:
    if want("A"):
        plan_edit("17470940", "9510183", None, carrier="car6600")
        hide_excl(1700265, [("19455208", "19455208B")])
    if want("E"): plan_edit("17472143", "9511482", None, carrier="car6600")
    if want("F"): plan_edit("17473335", "9513920", None, carrier="car6600")
    if want("B"):
        plan_edit("12232248", "6029665", "2,1", enddate="06/21/2025")
        patient_balances_to_insurance("marlow", "12232248", 2025)
    if want("C"):
        plan_edit("17474493", "9520723", "3,2", sequence="3,2")
        for vid, cid in (("19456837", "23368495"), ("19456905", "23368613")):
            set_insorder("ulverston", cid, "3,2"); freq1("ulverston", vid, cid, 3)
        set_insorder("ulverston 10/3", "23368705", "3,2")
    if want("D"):
        if LIVE:
            ok, msg = manual_post.post("23337644", "FLO02", 0.0, 153.50, "WOINS", checknumber="819814877", depositdate="09/19/2026", note="Medicare contractual (ERA 819814877 allowed 156.50 paid 125.20) never applied by the ERA poster - posted on William's approval A-2026-10-06T0137Z-D")
            log("kirkbride contractual", ok, str(msg)[:160])
        else: log("DRY manual_post 23337644 FLO02 pay 0 wo 153.50 WOINS chk 819814877 ->", manual_post.post("23337644", "FLO02", 0.0, 153.50, "WOINS", checknumber="819814877", depositdate="09/19/2026", note="dry", dry=True))
        plan_edit("17475338", "9519275", "2,1", sequence="2,1")
except Exception as e:
    import traceback; traceback.print_exc(); log("EXC", repr(e)[:300])
json.dump(REG, open(REGFILE, "w"), indent=1)
print("done", "LIVE" if LIVE else "DRY", REGFILE)
