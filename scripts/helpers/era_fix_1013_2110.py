# PLAIN ENGLISH (ERA follow-up of the 5 PM ET 10/13/2026 slot, run 2026-10-13T2110Z - ehpa cloud copy; shape of era_fix_1012_0910.py)
# Between this run's dry and live passes the Billing Button's live 'columns' run (2026-10-13T2123Z) pressed the ERA Center Post button on
# checks 1053150 (Sunshine 0917897914) and 1053152 (Humana 203043824261013) and dismissed them; this run's era_new_1013_2110.py then found
# their money lines 'already posted' and posted 1053151's six Humana secondary lines itself. The Post button left the known defect on ONE line:
#   A. chart 17477899 v19456243 99232 9/24/2026 (c23367867): Humana paid 70.46, CO-45 39.10 + CO-253 1.44 = 40.54 sit on the PATIENT balance
#      (the remit carried no write-off code, payreasonwoamount 0) -> move_to_ins.move(cid, rebill=False) (balance back to insurance, no rebill)
#      then the write-off-only Payment Entry (captured 10/7/2026: addpayments with an EMPTY <paymentlist/>) WOINS 40.54 under HUM01 with the
#      check number and check date. PR amounts: none.
#   B. chart 17471755 v19455292 99497 7/13/2026 (c23368642, $133 at SUN01 as PRIMARY): Sunshine answered CO-96 / N448 (advance care planning
#      not a benefit) on the frequency-7 corrected claim - the standing non-covered rule -> WONCS 133.00 through the ERA-linked shape
#      (payreasons.post_line pay 0 + wo, the remit's reasonlist rides along). The row walker-lenox-denials already says the run writes it off again.
#   C. Record only (no write): v19455292 c23368640 99309 CO-222/N640 again on the recoded corrected claim -> William (appeal with records or
#      write off); v19452694 c23363074 and v19420291 c23325277 are Sunshine's $0 answers on visits whose live claim is at Medicare (FLO02) - the
#      old plan's answer, Medicare's own answer settles them; v19456055 / v19456053 CO-16 / M56 -> the centene-m56-denials-0920 cluster;
#      1053116 (UHC W0020208 takeback pair) untouched - William's decision.
# Reads first: era_details/1053150.json + era_details/1053152.json, registers/era_checks_before_2026-10-13T2110Z.json, every charge's live
#   state (payreasons.visit_state). --dry (default) prints the plan; --live writes; --only A,B,C limits.
# Never touches: 1053116, PR amounts, insurance plans, charges not named above.
# Register: registers/era_fix_2026-10-13T2110Z[_dry].json + registers/era_manual_register.json (live).
import amd, payreasons, move_to_ins, manual_post, resave, json, sys, time, re
import xml.etree.ElementTree as ET
a = sys.argv[1:]; LIVE = "--live" in a; S = "2026-10-13T2110Z"
ONLY = set(a[a.index("--only") + 1].split(",")) if "--only" in a else {"A", "B", "C"}
def L(m): print(m, flush=True)
amd.login_cached()
_l = json.load(open("registers/era_checks_before_%s.json" % S)); _l = _l.get("checks") if isinstance(_l, dict) else _l
META = {str(c["id"]): c for c in _l}
D50 = {str(v["checkclaimid"]): v for v in json.load(open("era_details/1053150.json"))["eracheckdetails"]}
CHK50 = META["1053150"]; CHK52 = META["1053152"]
def dd(chk): d = str(chk.get("depositdate") or "")[:10]; return "%s/%s/%s" % (d[5:7], d[8:10], d[:4]) if "-" in d else d
out = {"stamp": S, "live": LIVE, "A": [], "B": [], "C": []}; faults = 0
def charge(pid, vid, cid):
    st = payreasons.visit_state(pid, vid); return next((c for c in st if c["cid"] == str(cid)), None)
def wo_only(pid, cid, wo, carrier, checkno, depdate, note):
    """write-off-only Payment Entry (captured 10/7/2026): no <payment> element, so no $0 code-less payment."""
    rt = ET.fromstring(resave.detail(cid)); vis = rt.find(".//visit"); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    bal = float(c.get("insbalance") or 0)
    if wo > bal + 0.005: return False, "over-apply: wo %.2f > insbalance %.2f" % (wo, bal)
    chg = ('<charge id="charge%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s"><paymentlist/>'
           '<writeofflist><writeoff id="" risk="0" amount="%.2f" code="WOINS" status="B"/></writeofflist></charge>'
           % (cid, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", vis.get("profile"), wo))
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="" amount="0.00" paycode="PE" woamount="%.2f" paymethod="9" carrierid="%s" '
           'depositdate="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, wo, manual_post.CAR[carrier], depdate, note, checkno, chg))
    r = amd.post(xml); return ('success="1"' in r and "<Fault" not in r), re.sub(r"\s+", " ", r)[:200]

# ---------------------------------------------------------------- A. CO-45 contractual on the patient balance -> move back + WOINS
A = [("1053152", "17477899", "19456243", "23367867", 40.54)]
if "A" in ONLY:
    for ck, pid, vid, cid, co in A:
        chk = CHK52; chkno = str(chk["paymentnumber"])
        c = charge(pid, vid, cid); r = {"checkid": ck, "pid": pid, "vid": vid, "cid": cid, "co": co}
        if not c: r["outcome"] = "not live"; out["A"].append(r); L("A v%s c%s not live" % (vid, cid)); continue
        r["before"] = {k: c[k] for k in ("fee", "paid", "insbalance", "patbalance", "carrier")}
        if any(w["void"] != "1" and w["code"].strip() == "WOINS" and abs(w["amount"] - co) < 0.011 for w in c["wos"]):
            r["outcome"] = "already corrected"; out["A"].append(r); L("A v%s c%s already corrected" % (vid, cid)); continue
        if not any(p["void"] != "1" and p["checkno"].split("(")[0] == chkno for p in c["pays"]):
            r["outcome"] = "HOLD - no payment with check %s on the charge" % chkno; out["A"].append(r); L("A v%s c%s %s" % (vid, cid, r["outcome"])); continue
        rem = round(c["insbalance"] + c["patbalance"], 2)
        if abs(rem - co) > 0.011: r["outcome"] = "HOLD - remainder %.2f is not the remit contractual %.2f" % (rem, co); out["A"].append(r); L("A v%s c%s %s" % (vid, cid, r["outcome"])); continue
        L("A v%s pat%s c%s %s fee %.2f paid %.2f insbal %.2f patbal %.2f -> move back + WOINS %.2f (check %s %s, %s)" % (vid, pid, cid, c["cpt"], c["fee"], c["paid"], c["insbalance"], c["patbalance"], co, chkno, dd(chk), c["carrier"]))
        if not LIVE: r["outcome"] = "DRY"; out["A"].append(r); continue
        if faults >= 3: r["outcome"] = "not attempted - 3 consecutive faults"; out["A"].append(r); continue
        if c["patbalance"] > 0.005:
            mv = move_to_ins.move(cid, rebill=False); r["move"] = str(mv)[:120]; L("   move back -> %s" % str(mv)[:100])
            if not str(mv).startswith("moved"): faults += 1; r["outcome"] = "FAULT move back"; out["A"].append(r); continue
            time.sleep(0.8)
        ok, resp = wo_only(pid, cid, co, c["carrier"] if c["carrier"] in manual_post.CAR else "HUM01", chkno, dd(chk), "ERA %s CO-45 correction %s" % (ck, S))
        r["post"] = (ok, resp[:160]); faults = 0 if ok else faults + 1; L("   WOINS %.2f -> %s %s" % (co, ok, resp[:100])); time.sleep(0.8)
        c2 = charge(pid, vid, cid) or {}; r["after"] = {k: c2.get(k) for k in ("insbalance", "patbalance", "paid")}; r["outcome"] = "posted" if ok else "FAULT"
        L("   after insbal %s patbal %s" % (c2.get("insbalance"), c2.get("patbalance"))); out["A"].append(r)

# ---------------------------------------------------------------- B. Sunshine CO-96/N448 on the 99497 of a Sunshine-primary visit -> WONCS
B = [("1053150", "15446481", "17471755", "19455292", "23368642", 133.00)]
if "B" in ONLY:
    for ck, claim, pid, vid, cid, wo in B:
        v = D50.get(claim) or next((x for x in D50.values() if str(x["visitid"]) == vid), None)
        ch = next((x for x in (v or {}).get("charges") or [] if str(x["chargedetailid"]) == cid), None)
        c = charge(pid, vid, cid); r = {"checkid": ck, "checkclaimid": claim, "pid": pid, "vid": vid, "cid": cid, "wo": wo, "wocode": "WONCS"}
        if not c or not v or not ch: r["outcome"] = "not live / not on the remit"; out["B"].append(r); L("B v%s c%s %s" % (vid, cid, r["outcome"])); continue
        r["before"] = {k: c[k] for k in ("fee", "paid", "insbalance", "patbalance", "carrier")}
        carcs = [x["reasoncode"] for x in ch.get("carc") or []]
        if c["paid"] > 0.005 or any(p["void"] != "1" for p in c["pays"]): r["outcome"] = "skip - a payment sits on the charge"; out["B"].append(r); L("B v%s c%s %s" % (vid, cid, r["outcome"])); continue
        if any(w["void"] != "1" and w["code"].strip() == "WONCS" for w in c["wos"]): r["outcome"] = "already written off WONCS"; out["B"].append(r); L("B v%s c%s already WONCS" % (vid, cid)); continue
        if c["carrier"] != CHK50["systemcarriercode"]: r["outcome"] = "HOLD - live claim at %s, not the check's %s" % (c["carrier"], CHK50["systemcarriercode"]); out["B"].append(r); L("B v%s c%s %s" % (vid, cid, r["outcome"])); continue
        if not any(x in ("CO96", "96") for x in carcs): r["outcome"] = "HOLD - remit line is not CO-96 (%s)" % carcs; out["B"].append(r); L("B %s" % r["outcome"]); continue
        bal = round(c["insbalance"], 2); wo = round(min(wo, bal), 2)
        if bal <= 0: r["outcome"] = "skip - insurance balance already 0"; out["B"].append(r); L("B v%s c%s bal 0" % (vid, cid)); continue
        L("B v%s pat%s c%s %s %s fee %.2f insbal %.2f %s -> WONCS %.2f ERA-linked under %s" % (vid, pid, cid, c["cpt"], c["dos"], c["fee"], c["insbalance"], "+".join(carcs), wo, CHK50["systemcarriercode"]))
        if not LIVE: r["outcome"] = "DRY"; out["B"].append(r); continue
        if faults >= 3: r["outcome"] = "not attempted - 3 consecutive faults"; out["B"].append(r); continue
        ok, payid, resp = payreasons.post_line(pid, vid, CHK50, v, cid, ch, pay=0.0, wo=wo, wocode="WONCS"); r["post"] = (ok, payid, resp[:160]); L("   post_line pay 0 WONCS %.2f -> %s %s" % (wo, ok, resp[:100]))
        faults = 0 if ok else faults + 1; time.sleep(0.8)
        c2 = charge(pid, vid, cid) or {}; r["after"] = {k: c2.get(k) for k in ("insbalance", "patbalance", "paid")}; r["outcome"] = "posted" if ok else "FAULT"
        L("   after insbal %s patbal %s" % (c2.get("insbalance"), c2.get("patbalance"))); out["B"].append(r)

# ---------------------------------------------------------------- C. record only
if "C" in ONLY:
    out["C"] = [
        {"checkid": "1053150", "pid": "17471755", "vid": "19455292", "cid": "23368640", "outcome": "held - CO-222/N640 (frequency exceeded) again on the 99309 recoded 10/5 and sent frequency 7 with Sunshine's claim number; $141 at SUN01 primary - William: appeal with records or write off (board row walker-lenox-denials, his turn)"},
        {"checkid": "1053150", "pid": "17470802", "vid": "19452694", "cid": "23363074", "outcome": "recorded - Sunshine CO-242/M115 $0 on the 8/20/2026 99497; the live claim is at Medicare (FLO02, re-routed 9/23) - the old plan's answer, Medicare's own answer settles it; 99306 on the visit already at $0"},
        {"checkid": "1053150", "pid": "20670", "vid": "19420291", "cid": "23325277", "outcome": "recorded - Sunshine CO-45/OA-23 $0 on the 10/8/2025 99309; the live claim is at Medicare (FLO02) - the old plan's answer, Medicare's own answer settles it"},
        {"checkid": "1053150", "pid": "17473663", "vid": "19456055", "cid": "23367536", "outcome": "held - Sunshine CO-16/M56 $0 on the 9/22/2026 99309 (secondary, Medicare paid) - centene-m56-denials-0920 cluster (payer identifier), appended to the board row"},
        {"checkid": "1053150", "pid": "17472834", "vid": "19456053", "cid": "23367534", "outcome": "held - Sunshine CO-16/M56 $0 on the 9/22/2026 99309 (secondary, Medicare paid) - centene-m56-denials-0920 cluster (payer identifier), appended to the board row"},
        {"checkid": "1053116", "pid": "22023", "vid": "19395670", "cid": "22468661", "outcome": "held - UHC W0020208 takeback pair, William's decision (unchanged)"},
    ]
    for r in out["C"]: L("C v%s pat%s: %s" % (r["vid"], r["pid"], r["outcome"]))

json.dump(out, open("registers/era_fix_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
if LIVE:
    REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)); when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for sec in ("A", "B"):
        for r in out[sec]:
            if r.get("outcome") in ("posted", "already corrected", "already written off WONCS"):
                reg.append({"checkid": r["checkid"], "checkclaimid": r.get("checkclaimid"), "visitid": r["vid"], "chargedetailid": r["cid"], "outcome": "posted" if r["outcome"] == "posted" else "already-posted", "pay": 0.0, "wo": r.get("co") or r.get("wo"), "wocode": r.get("wocode", "WOINS"), "when": S, "note": "era_fix_%s %s" % (S, sec)})
    json.dump(reg, open(REGF, "w"), indent=1)
L("done: A %s | B %s | C %d recorded" % ([r["outcome"] for r in out["A"]], [r["outcome"] for r in out["B"]], len(out["C"])))
