# PLAIN ENGLISH (ERA follow-up of the 5 AM ET 10/12/2026 slot, run 2026-10-12T0910Z - ehpa cloud copy)
# Two Humana-format 835s were posted through the ERA Center Post button this slot (era_post.py --all-unposted):
#   1053137 HUM01 202832143261011 $226.97 (2 primary lines, chart 17477893) and 1053138 (filed under FLO02, claim carrier Humana)
#   202832142261011 $309.57 (17 claims: 7 posted, 10 left as $0 answers / already-settled lines). AMD put the CO45 / CO253 reasons on
#   each payment but payreasonwoamount 0 (the 9/23 carrier-wide defect), so the contractual sits on the PATIENT balance of six charges.
# Decides, by the standing rules only:
#   A. CO-45 correction (6 lines): move_to_ins.move(cid, rebill=False) (balance back to insurance, no rebill) then the write-off-only
#      Payment Entry (captured 10/7/2026: addpayments with an EMPTY <paymentlist/>, so no $0 code-less payment is born) WOINS = the
#      contractual, under the charge's live carrier, with the check number and the check date. PR amounts: none on these lines.
#   B. CO-185 / N767 $0 answers from Humana Healthy Horizons (the Medicaid MMA secondary) on four Medicare-paid 99309 lines (charts
#      17470899, 20937, 44955, 21915): William's 9/20/2026 rule - the coinsurance residual (16.93) is written off WOINS through the
#      ERA-linked shape (payreasons.post_line pay 0 + wo, the remit's reasonlist rides along: CO185 141.00 = the fee, so the line
#      balances). A residual that sits on the patient side is moved back first (never bill a dual).
#   C. Record only: chart 21915 v19455374 / v19455375 (Humana paid 13.64 / 19.92 on lines already settled WOCAID2ND - $0 open balance,
#      residual disregarded per William 9/13); chart 23969 v19455866 / v19455886 OA-23 $0 (no Humana plan on the chart, Cigna secondary
#      pending - held as on 10/11); chart 17476264 v19455628 CCM OA-23 $0 (no Humana plan on the chart, 28.60 coinsurance on the
#      patient - board row on William's turn); the three OA-23 money lines the Post button settled (v19455372, v19455373, v19455910).
#   D. Chart 20407 v19457356 (99309 10/4/2026, $141 at HUM01 as PRIMARY, Humana answered PI-252 / N4 'primary EOB needed'): AMD's 271
#      says Medicare ACTIVE + QMB and Humana = the Medicaid MMA plan, the chart's default order was Humana alone -> patient order 2,3
#      (ins_update), visit order 2,3 + ONE frequency-1 rebill to Medicare seq 2 (freq1_visit.reroute - William 10/6 one-rebill rule).
# Reads first: era_details/1053137.json + era_details/1053138.json, registers/era_checks_before_2026-10-12T0910Z_list.json, every
#   visit's live charges / payments (payreasons.visit_state). --dry (default) prints the plan; --live writes; --only A,B,C,D limits.
# Never touches: 1053116 (held for William), PR amounts, plans other than chart 20407's order, charges not named above.
# Register: registers/era_fix_2026-10-12T0910Z[_dry].json + registers/era_manual_register.json (live).
import amd, payreasons, move_to_ins, manual_post, resave, ins_update, freq1_visit, json, sys, time, re
import xml.etree.ElementTree as ET
a = sys.argv[1:]; LIVE = "--live" in a; S = "2026-10-12T0910Z"
ONLY = set(a[a.index("--only") + 1].split(",")) if "--only" in a else {"A", "B", "C", "D"}
def L(m): print(m, flush=True)
amd.login_cached()
META = {str(c["id"]): c for c in json.load(open("registers/era_checks_before_%s_list.json" % S))}
D37 = {str(v["checkclaimid"]): v for v in json.load(open("era_details/1053137.json"))["eracheckdetails"]}
D38 = {str(v["checkclaimid"]): v for v in json.load(open("era_details/1053138.json"))["eracheckdetails"]}
CHK37 = META["1053137"]
CHK38 = dict(payreasons.check_meta("1053138")); CHK38["systemcarriercode"] = "HUM01"; CHK38["systemcarrierid"] = 6285   # the claims are Humana's (carrierid 6285) although AMD filed the check under FLO02
def dd(chk): d = str(chk.get("depositdate") or "")[:10]; return "%s/%s/%s" % (d[5:7], d[8:10], d[:4]) if "-" in d else d
out = {"stamp": S, "live": LIVE, "A": [], "B": [], "C": [], "D": []}; faults = 0
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
A = [("1053137", "15446285", "17477893", "19456294", "23367919", 153.49), ("1053137", "15446286", "17477893", "19456229", "23367853", 40.54),
     ("1053138", "15446292", "17477972", "19456879", "23368540", 56.19), ("1053138", "15446293", "17477972", "19456851", "23368512", 56.19),
     ("1053138", "15446294", "17477972", "19456886", "23368547", 56.19), ("1053138", "15446295", "17477972", "19456860", "23368521", 56.19)]
if "A" in ONLY:
    for ck, claim, pid, vid, cid, co in A:
        chk = CHK37 if ck == "1053137" else CHK38; chkno = str(chk["paymentnumber"])
        c = charge(pid, vid, cid); r = {"checkid": ck, "checkclaimid": claim, "pid": pid, "vid": vid, "cid": cid, "co": co}
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
        ok, msg = wo_only(pid, cid, co, c["carrier"], chkno, dd(chk), "ERA %s contractual correction run %s" % (ck, S)); r["post"] = (ok, msg[:160]); L("   WOINS %.2f write-off-only -> %s %s" % (co, ok, msg[:100]))
        faults = 0 if ok else faults + 1; time.sleep(0.8)
        c2 = charge(pid, vid, cid) or {}; r["after"] = {k: c2.get(k) for k in ("insbalance", "patbalance", "paid")}; r["outcome"] = "corrected" if ok else "FAULT"
        L("   after insbal %s patbal %s" % (c2.get("insbalance"), c2.get("patbalance"))); out["A"].append(r)

# ---------------------------------------------------------------- B. CO-185/N767 coinsurance residual -> WOINS, ERA-linked (9/20 rule)
B = [("15446300", "17470899", "19455924", "23367393"), ("15446301", "20937", "19455927", "23367396"), ("15446302", "44955", "19455925", "23367394"), ("15446303", "21915", "19455908", "23367377")]
if "B" in ONLY:
    for claim, pid, vid, cid in B:
        v = D38[claim]; ch = [x for x in v["charges"] if str(x["chargedetailid"]) == cid][0]
        c = charge(pid, vid, cid); r = {"checkid": "1053138", "checkclaimid": claim, "pid": pid, "vid": vid, "cid": cid, "carcs": [x["reasoncode"] for x in ch["carc"]]}
        if not c: r["outcome"] = "not live"; out["B"].append(r); continue
        r["before"] = {k: c[k] for k in ("fee", "paid", "insbalance", "patbalance", "carrier")}
        if any(p["void"] != "1" and p["checkno"].split("(")[0] == str(CHK38["paymentnumber"]) for p in c["pays"]): r["outcome"] = "already-posted"; out["B"].append(r); L("B v%s already posted" % vid); continue
        resid = round(c["insbalance"] + c["patbalance"], 2)
        if resid <= 0: r["outcome"] = "skip - balance already 0"; out["B"].append(r); L("B v%s balance 0" % vid); continue
        L("B v%s pat%s c%s %s fee %.2f paid %.2f insbal %.2f patbal %.2f (%s) -> %sWOINS %.2f ERA-linked under HUM01" % (vid, pid, cid, c["cpt"], c["fee"], c["paid"], c["insbalance"], c["patbalance"], c["carrier"], "move back + " if c["patbalance"] > 0.005 else "", resid))
        r["wo"] = resid
        if not LIVE: r["outcome"] = "DRY"; out["B"].append(r); continue
        if faults >= 3: r["outcome"] = "not attempted - 3 consecutive faults"; out["B"].append(r); continue
        if c["patbalance"] > 0.005:
            mv = move_to_ins.move(cid, rebill=False); r["move"] = str(mv)[:120]; L("   move back -> %s" % str(mv)[:100])
            if not str(mv).startswith("moved"): faults += 1; r["outcome"] = "FAULT move back"; out["B"].append(r); continue
            time.sleep(0.8)
        ok, payid, resp = payreasons.post_line(pid, vid, CHK38, v, cid, ch, pay=0.0, wo=resid, wocode="WOINS"); r["post"] = (ok, payid, resp[:160]); L("   post_line pay 0 WOINS %.2f -> %s %s" % (resid, ok, resp[:100]))
        faults = 0 if ok else faults + 1; time.sleep(0.8)
        c2 = charge(pid, vid, cid) or {}; r["after"] = {k: c2.get(k) for k in ("insbalance", "patbalance", "paid")}; r["outcome"] = "posted" if ok else "FAULT"
        L("   after insbal %s patbal %s" % (c2.get("insbalance"), c2.get("patbalance"))); out["B"].append(r)

# ---------------------------------------------------------------- C. record only
if "C" in ONLY:
    out["C"] = [
        {"checkid": "1053138", "checkclaimid": "15446296", "pid": "21915", "vid": "19455374", "cid": "23366674", "outcome": "residual 13.64 - line already settled WOCAID2ND 13.64 after the Medicaid $0 crossover, open balance 0; Humana's 13.64 disregarded (William 9/13)"},
        {"checkid": "1053138", "checkclaimid": "15446297", "pid": "21915", "vid": "19455375", "cid": "23366676", "outcome": "residual 19.92 - line already settled WOCAID2ND 19.92 after the Medicaid $0 crossover, open balance 0; Humana's 19.92 disregarded (William 9/13)"},
        {"checkid": "1053138", "checkclaimid": "15446298", "pid": "23969", "vid": "19455866", "cid": "23367331", "outcome": "held - OA-23 $0 from Humana Healthy Horizons, no Humana plan on the chart, Cigna secondary claim pending (21.80 coinsurance) - as on 10/11"},
        {"checkid": "1053138", "checkclaimid": "15446299", "pid": "23969", "vid": "19455886", "cid": "23367351", "outcome": "held - OA-23 $0 from Humana Healthy Horizons, no Humana plan on the chart, Cigna secondary claim pending (21.80 coinsurance) - as on 10/11"},
        {"checkid": "1053138", "checkclaimid": "15446287", "pid": "17476264", "vid": "19455628", "cid": "23366984", "outcome": "held - OA-23 $0 from Humana Healthy Horizons on a CCM 99487 Medicare paid 112.09; the chart carries Medicare only and its 271 names no Medicaid/QMB entity; 28.60 coinsurance on the patient - board row on William's turn"},
        {"checkid": "1053138", "checkclaimid": "15446288", "pid": "21021", "vid": "19455372", "cid": "23366670", "outcome": "posted (Post button) 19.92 - balance 0"},
        {"checkid": "1053138", "checkclaimid": "15446291", "pid": "24214", "vid": "19455373", "cid": "23366672", "outcome": "posted (Post button) 19.92 - balance 0"},
        {"checkid": "1053138", "checkclaimid": "15446289", "pid": "45001", "vid": "19455910", "cid": "23367379", "outcome": "posted (Post button) 16.93 - balance 0"},
    ]
    for r in out["C"]: L("C v%s pat%s: %s" % (r["vid"], r["pid"], r["outcome"]))

# ---------------------------------------------------------------- D. chart 20407: Medicare first, one frequency-1 rebill
if "D" in ONLY:
    pid, vid, cid, ins = "20407", "19457356", "23369216", "ins6007551"
    c = charge(pid, vid, cid); r = {"checkid": "1053138", "checkclaimid": "15446290", "pid": pid, "vid": vid, "cid": cid, "before": {k: c[k] for k in ("fee", "paid", "insbalance", "patbalance", "carrier")} if c else None}
    if not c or c["paid"] > 0 or c["insbalance"] <= 0: r["outcome"] = "skip - charge changed (payment or no open balance)"; L("D %s" % r["outcome"])
    elif not LIVE: r["outcome"] = "DRY would set patient order 2,3 + reroute visit 2,3 seq 2 (freq-1 to Medicare)"; L("D v%s pat%s %s %s at %s insbal %.2f -> %s" % (vid, pid, c["cpt"], c["dos"], c["carrier"], c["insbalance"], r["outcome"]))
    else:
        ok, msg = ins_update.update(pid, ins, sequence="2,3"); r["order"] = (ok, str(msg)[:200]); L("D patient order 2,3 -> %s %s" % (ok, str(msg)[:160])); time.sleep(0.8)
        res = freq1_visit.reroute(vid, cid, "2,3", 2); r["reroute"] = str(res)[:240]; L("D reroute -> %s" % str(res)[:200])
        r["outcome"] = "re-routed Medicare first + freq-1 rebill" if ("204" in str(res) and not str(res).startswith("NOT")) else "CHECK - " + str(res)[:120]
    out["D"].append(r)

json.dump(out, open("registers/era_fix_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
if LIVE:
    REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)); when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for sec in ("A", "B", "C", "D"):
        for r in out[sec]:
            reg.append({"checkid": int(r["checkid"]), "checkclaimid": int(r["checkclaimid"]), "visitid": int(r["vid"]), "chargeid": int(r["cid"]), "outcome": ("%s: %s" % (sec, r.get("outcome"))), "when": when, "run": S})
    json.dump(reg, open(REGF, "w"), indent=1)
L("SUMMARY %s: A %s | B %s | C %d recorded | D %s" % ("LIVE" if LIVE else "DRY", [r.get("outcome") for r in out["A"]], [r.get("outcome") for r in out["B"]], len(out["C"]), [r.get("outcome") for r in out["D"]]))
