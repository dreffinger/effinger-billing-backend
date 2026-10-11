# PLAIN ENGLISH (contractual correction after AMD's auto-poster took the uploaded UHC / AARP 835s - run 2026-10-11T0510Z)
# Decides: nothing new - the 9/23/2026 standing correction: AMD's ERA posting engine posts a money line WITH the CO-45 (and other
#   CO/OA) reason codes on the payment but WITHOUT the contractual write-off (payreasonwoamount 0), so the charge keeps
#   fee - paid on the insurance balance. For every line in registers/era_recheck_<stamp>.json that the engine posted tonight
#   (now = posted-with-reasons) and that still carries an open insurance balance: wo = the sum of the CO / OA / PI reason amounts
#   on that live payment, capped at the open insurance balance (PR amounts are never written off - AMD moves the PR remainder to
#   the next payer / the patient on its own), posted through the write-off-only Payment Entry shape captured 10/7/2026
#   (addpayments with an EMPTY <paymentlist/> - no $0 code-less payment is born) under the remit's check number and date, code WOINS.
# Never touches: lines with no CO/OA amount, lines whose balance is already the PR share, payments, any other charge.
#   python3 era_wo_fix_1011.py          # dry: lists wo per line
#   python3 era_wo_fix_1011.py --live   # register registers/era_wo_fix_2026-10-11T0510Z.json; stops after 3 consecutive faults
import amd, resave, txh, payreasons, json, re, sys, time
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"
CAR = json.load(open("carriers.json"))
amd.login_cached()
rows = json.load(open("registers/era_recheck_%s.json" % S))
reg = {"stamp": S, "live": LIVE, "lines": []}
faults = 0; tot_wo = 0.0; n = 0
def wo_xml(pid, cid, car, wo, checkno, dd, note):
    rt = ET.fromstring(resave.detail(cid)); vis = rt.find(".//visit")
    c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    bal = float(c.get("insbalance") or 0)
    chg = ('<charge id="charge%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
           '<paymentlist/><writeofflist><writeoff id="" risk="0" amount="%.2f" code="WOINS" status="B"/></writeofflist></charge>'
           % (cid, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", vis.get("profile"), wo))
    return bal, ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="" amount="0.00" paycode="PE" woamount="%.2f" paymethod="9" carrierid="%s" '
           'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, wo, CAR[car], dd, note, checkno, chg))
seen = set()
for r in rows:
    if r["now"] != "posted-with-reasons" or r["insbal"] <= 0.005 or r["cid"] in seen: continue
    seen.add(r["cid"])
    st = payreasons.visit_state(r["pid"], r["vid"], root=txh.fetch_visit(r["pid"], r["vid"]))
    ch = next((x for x in st if x["cid"] == r["cid"]), None)
    if not ch: continue
    pay = next((p for p in ch["pays"] if p["void"] != "1" and p["checkno"].split("(")[0] == r["checkno"] and p["reasons"]), None)
    if not pay: continue
    co = round(sum(a for code, a in pay["reasons"] if not code.upper().startswith("PR")), 2)
    pr = round(sum(a for code, a in pay["reasons"] if code.upper().startswith("PR")), 2)
    wo = round(min(co, ch["insbalance"]), 2)
    rec = {"checkid": r["check"], "checkno": r["checkno"], "pid": r["pid"], "vid": r["vid"], "cid": r["cid"], "cpt": r["cpt"], "paid": pay["amount"], "reasons": pay["reasons"], "co": co, "pr": pr, "insbal": ch["insbalance"], "carrier": pay["carrier"], "wo": wo}
    if wo <= 0.005 or pay["carrier"] not in CAR: rec["outcome"] = "skip - no CO amount / carrier unknown"; reg["lines"].append(rec); print(json.dumps(rec)[:240]); continue
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", pay["date"] or ""); dd = m.group(0) if m else time.strftime("%m/%d/%Y")
    if not LIVE: rec["outcome"] = "DRY WOINS %.2f" % wo
    else:
        if faults >= 3: rec["outcome"] = "stopped after 3 consecutive faults"; reg["lines"].append(rec); continue
        bal, xml = wo_xml(r["pid"], r["cid"], pay["carrier"], wo, pay["checkno"].split("(")[0], dd, "ERA %s contractual correction run %s" % (r["check"], S))
        if wo > bal + 0.005: wo = round(bal, 2); bal, xml = wo_xml(r["pid"], r["cid"], pay["carrier"], wo, pay["checkno"].split("(")[0], dd, "ERA %s contractual correction run %s" % (r["check"], S))
        resp = amd.post(xml); ok = 'success="1"' in resp
        rec["outcome"] = "posted WOINS %.2f" % wo if ok else "FAULT " + re.sub(r"\s+", " ", resp[:200])
        faults = 0 if ok else faults + 1
        if ok: tot_wo += wo; n += 1
        time.sleep(0.5)
    reg["lines"].append(rec); print(json.dumps(rec)[:260], flush=True)
reg["summary"] = {"lines": n, "woins": round(tot_wo, 2), "planned": round(sum(x["wo"] for x in reg["lines"] if x.get("wo", 0) > 0 and "skip" not in x["outcome"]), 2)}
print("SUMMARY", reg["summary"])
json.dump(reg, open("registers/era_wo_fix_%s.json" % S, "w"), indent=1)
