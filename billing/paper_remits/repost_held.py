#!/usr/bin/env python3
# PLAIN ENGLISH (Re-post paper-remit lines the posting engine HELD, after the clinician's decision)
# Decides: nothing on its own. post_paper.py holds a line when the money cannot be applied without a judgement call:
#   (a) the balance is 0 because a coinsurance / crossover residual was already written off before the paper check arrived
#       (WOINS or WOMCAD/WOCAID2ND posted with a $0 COB statement or a Medicaid $0) - the engine only voids a write-off that
#       EQUALS the payment, so a partial payment on a written-off residual is held;
#   (b) the payer paid the same service twice (the original visit's claim on one check, the re-entered visit's claim on another).
#   When William says "post them", this tool carries it out from a spec file:
#   lines[]   - void ONE named premature write-off, then post the payer's money ERA-linked (payreasons.post_line: keeps the CO45/OA23
#               reasons, uses the dismissed check's cached details) with the leftover as the named write-off code in the SAME post,
#               and verify the charge ends at insurance balance 0;
#   unapplied[] - a duplicate payment is posted as ONE unapplied insurance credit on the chart (William's 9/3/2026 overpayment
#               rule: never applied to other claims; the payer nets it on a later remit or asks for a refund).
# Rules it uses: void only the write-off named in the spec (never the primary's contractual); refuse when the EOB payment exceeds the
#   voided write-off; refuse when a live payment from the same payer already carries money on the line; stop a line when the balance
#   after the void is not the voided amount. Every step is logged to a register next to the spec.
# Never touches: paid lines not in the spec, charges, plans, the ERA Center checks (no Post button, no era_clear).
# ---
"""Usage (cd /home/claude/unbilled or set PYTHONPATH to it + billing/paper_remits):
  python3 repost_held.py --spec <spec.json> [--live]
Spec: {"lines": [{"pid": "45210", "vid": "19450674", "cid": "23360625", "checkid": "1052991", "void_writeoff_id": "22480088",
                   "paid": 10.21, "wocode": "WOCAID2ND", "check_number": "01964930", "deposit_date": "2026-09-03",
                   "payment_code": "CHK", "carrier_id": 42008}],
       "unapplied": [{"pid": "20060", "carrier_id": 42008, "check_number": "01971199", "deposit_date": "09/10/2026",
                      "amount": 299.83, "profile": "prof13", "note": "duplicate payment - see register"}]}
Register: <spec dir>/<spec name>_<dry|live>_<stamp>.json"""
import sys, re, json, time, os
sys.path.insert(0, "/home/claude/unbilled")
import amd, txh, void_tx, payreasons
LIVE = "--live" in sys.argv
SPEC = sys.argv[sys.argv.index("--spec") + 1] if "--spec" in sys.argv else sys.exit(__doc__)
S = json.load(open(SPEC))
STAMP = time.strftime("%Y-%m-%dT%H%MZ", time.gmtime())
REGFILE = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "%s_%s_%s.json" % (os.path.splitext(os.path.basename(SPEC))[0], "live" if LIVE else "dry", STAMP))
REG = {"stamp": STAMP, "live": LIVE, "spec": SPEC, "steps": []}
def log(*a): print(*a, flush=True); REG["steps"].append(" ".join(str(x) for x in a))
def f(v): return round(float(str(v or 0).replace(",", "")), 2)
def charge(pid, cid):
    for c in txh.fetch(pid).iter("charge"):
        if c.get("id") == str(cid) and c.get("void") != "1": return c
def state(c):
    wos = [(w.get("id"), w.get("wocode"), f(w.get("amount")), w.get("void")) for w in c.iter("writeoff")]
    pays = [(p.get("id"), p.get("carrier"), f(p.get("amount")), p.get("checknumber"), p.get("void")) for p in c.iter("payment")]
    return f(c.get("fee")), f(c.get("insbal")), f(c.get("patbal")), wos, pays
def carrier_code(carid):
    try:
        cj = json.load(open("/home/claude/unbilled/carriers.json")); v = cj.get("car%s" % carid)
        return v[0] if isinstance(v, (list, tuple)) else (v or "")
    except Exception: return ""
amd.login_cached()
for ln in S.get("lines", []):
    pid, vid, cid, chkid, woid, paid = str(ln["pid"]), str(ln["vid"]), str(ln["cid"]), str(ln["checkid"]), str(ln["void_writeoff_id"]), f(ln["paid"])
    wocode = ln.get("wocode") or "WOCAID2ND"; carid = str(ln.get("carrier_id") or ""); payer = carrier_code(carid)
    c = charge(pid, cid)
    if c is None: log("LINE", cid, "no live charge - SKIP"); continue
    fee, insbal, patbal, wos, pays = state(c)
    w = [x for x in wos if x[0] == woid]
    if not w: log("LINE", cid, "write-off", woid, "not on the charge - SKIP"); continue
    w = w[0]
    if w[3] == "1": log("LINE", cid, "write-off", woid, "already void - SKIP"); continue
    if payer and any(p[1] == payer and abs(p[2]) >= 0.01 and p[4] != "1" for p in pays): log("LINE", cid, "already has a live", payer, "payment - SKIP"); continue
    wo_amt = abs(w[2]); resid = round(wo_amt - paid, 2)
    if resid < 0: log("LINE", cid, "paid", paid, "exceeds the write-off", wo_amt, "- SKIP (review)"); continue
    d = payreasons.details(chkid); v = [x for x in d.get("eracheckdetails", []) if str(x.get("visitid")) == vid]
    if not v: log("LINE", cid, "no cached ERA claim for visit", vid, "on check", chkid, "- SKIP"); continue
    v = v[0]; ch = [x for x in v.get("charges", []) if str(x.get("chargedetailid")) == cid]
    if not ch: log("LINE", cid, "ERA claim has no line for this charge - SKIP"); continue
    ch = ch[0]; chk = dict(payreasons.check_meta(chkid, v))
    chk["paymentnumber"] = ln.get("check_number") or str(chk.get("paymentnumber") or "").split("(")[0]
    chk["depositdate"] = ln.get("deposit_date") or chk.get("depositdate") or ""
    chk["paymentcode"] = ln.get("payment_code") or chk.get("paymentcode") or "CHK"
    if carid: chk["systemcarrierid"] = int(carid)
    log("LINE", pid, vid, cid, "fee", fee, "insbal", insbal, "void", w[1], woid, wo_amt, "-> post", payer or carid, "pay", paid, "+", wocode, resid, "chk", chk["paymentnumber"], chk["depositdate"], "eraclaim", v.get("checkclaimid"))
    if not LIVE: continue
    ok, t = void_tx.void_writeoff(pid, cid, woid); log("   void ->", ok, t[:100])
    if not ok: continue
    time.sleep(0.8)
    fee2, insbal2, patbal2, wos2, pays2 = state(charge(pid, cid))
    if abs(insbal2 - wo_amt) > 0.011: log("   after void insbal", insbal2, "expected", wo_amt, "- STOP this line (review)"); continue
    try: ok, payid, head = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=paid, wo=resid, wocode=wocode)
    except Exception as e: log("   post EXC", repr(e)[:200]); continue
    log("   post ->", ok, payid, head[:100]); time.sleep(0.8)
    fee3, insbal3, patbal3, wos3, pays3 = state(charge(pid, cid))
    log("   verify insbal", insbal3, "patbal", patbal3, "pays", [(p[1], p[2], p[3]) for p in pays3 if p[4] != "1"], "wos", [(x[1], x[2]) for x in wos3 if x[3] != "1"])
for u in S.get("unapplied", []):
    pid, carid, amt = str(u["pid"]), str(u["carrier_id"]), f(u["amount"]); chkno = u.get("check_number", "")
    root = txh.fetch(pid)
    seen = [x.attrib for x in root.iter("payment") if x.get("checknumber") == chkno and abs(f(x.get("amount"))) == amt and x.get("void") != "1" and x.get("actvpaymentid")]
    if seen: log("UNAPPLIED", pid, chkno, amt, "already on the chart:", seen[0].get("id")); continue
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="" amount="%.2f" paycode="PE" woamount="0.00" paymethod="%s" carrierid="car%s" '
           'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist><payment source="2" profile="%s" amount="%.2f" carrier="car%s"/></unappliedpaymentlist><unappliedwriteofflist/><chargelist/></patient></ppmdmsg>'
           % (amd._msgtime(), pid, amt, payreasons.PAYMETHOD.get(u.get("payment_code", "CHK"), "11"), carid, u.get("deposit_date") or time.strftime("%m/%d/%Y"),
              (u.get("note") or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;"), chkno, u.get("profile") or "prof13", amt, carid))
    log("UNAPPLIED credit", amt, "on chart", pid, "carrier car%s check %s ->" % (carid, chkno), "DRY" if not LIVE else "posting")
    if not LIVE: continue
    r = amd.post(xml); ok = 'success="1"' in r and "<Fault" not in r; log("   addpayments unapplied ->", ok, re.sub(r"\s+", " ", r)[:220])
    time.sleep(1.0)
    un = [x.attrib for x in txh.fetch(pid).iter("payment") if x.get("actvpaymentid") and x.get("checknumber") == chkno]
    log("   verify unapplied rows:", json.dumps(un)[:400])
json.dump(REG, open(REGFILE, "w"), indent=1)
print("done", "LIVE" if LIVE else "DRY", REGFILE)
