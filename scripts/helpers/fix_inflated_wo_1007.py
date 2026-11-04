# PLAIN ENGLISH (William 10/7/2026 "Go apply" / "finish all billing tasks now" - cards A-2026-10-07T0510Z-C..F, the 51 inflated 9/9/2026 Medicare postings)
# Decides: nothing new - same decision as fix_inflated_1007.py (the card scripts), different proven mechanics, because the 9/9/2026 remits
#   are PROCESSED checks: GET /api/era/checkdetails answers no claims for them, no era_details cache of them exists anywhere (workspace,
#   Drive, main), and the dismissed entry 894975 that the 0510Z run mapped payment 816705526 to is a 2-claim leftover of another chart. So
#   the void + ERA-linked re-post (era_co45_relink) cannot run. The live Post-button payments already carry balanced CO45 / PR2 / CO253
#   reasons (|paid| + reasons = fee on every line); the only defect is the missing WOINS. Correction per line, every call a captured shape:
#     1. manual_post.post(cid, "FLO02", 0, CO45+CO253, "WOINS", checknumber=<payment number>, depositdate=<pay date>)  (9/29 fix shape)
#     2. the $0 code-less payment that addpayments adds beside the write-off is VOIDED (void_tx.void_payment) - the 10/5 recipe: on chart
#        17471688 charge 23365741 the 9/29 WOINS 57.71 is live, its $0 payment 24656994 void, |paid| + reasons = fee, visit routed FLO99,
#        and the Unbilled column is empty today (01:31Z read) - so the WOINS survives the void and the secondary claim builds its CAS.
#     3. verify live: non-void WOINS = CO, no non-void code-less payment, payreasons.balanced() True, insbal + patbal = PR
#     4. once per visit: freq1_visit.reroute(vid, cid, "<medicare seq>,<plan seq>", <plan seq>) = order write + ONE freq-1 rebill (10/6 rule)
#   Section C adds the 1/31/2024 99497 coinsurance $31.29 WOLATE under FLO99 (charge 22443840) the same way (manual_post + void the $0 line).
#   Register: registers/inflated_medicare_lines_2026-10-07T0510Z.json (rebuilt 08:23Z by scan_inflated_1007.py: 51 lines, $3,746.35 open,
#   $2,906.91 CO - identical to the 0510Z run's numbers). Check 815793370 (2 lines, pat21564 9/30/2024) stays HELD like the card says.
#   --dry (default) prints the plan and sends nothing; --live does it; --first-only stops after the first corrected line; 3 consecutive
#   faults stop the section. Output registers/fix_inflated_wo_2026-10-07T0510Z_<sections>[_dry].json.
# Never touches: PR amounts, payments with reasons (never voided), plans, charges already carrying a WOINS, charges not in the register.
import amd, payreasons, freq1_visit, precheck, manual_post, void_tx, move_to_ins, json, sys, time, datetime
DRY = "--live" not in sys.argv; FIRST = "--first-only" in sys.argv
ONLY = sys.argv[sys.argv.index("--only") + 1].upper() if "--only" in sys.argv else "ABCD"
STAMP = "2026-10-07T0510Z"
SEC = {"A": "17471688", "B": "12232001", "C": "17471172", "D": "21564"}
CARD = {"A": "A-2026-10-07T0510Z-C", "B": "A-2026-10-07T0510Z-D", "C": "A-2026-10-07T0510Z-E", "D": "A-2026-10-07T0510Z-F"}
ERAID = {"816705526": "894975", "815638157": "893557", "815915909": "893939", "816846022": "895100", "816005534": "894021",
         "815906990": "893899", "815577106": "893470", "816245550": "894399"}   # payment number -> ERA id (card list); 815793370 has none -> HOLD
MEDICARE, FCC, MCAD = "car6085", "car42008", "car6113"
WO_C = ("22443840", 31.29)
amd.login_cached()
lines = json.load(open("registers/inflated_medicare_lines_%s.json" % STAMP))
out = {"stamp": STAMP, "dry": DRY, "sections": ONLY, "steps": [], "done": [], "hold": []}
def L(m): print(m, flush=True); out["steps"].append(m)

def plan_seqs(pid):
    _, pl = precheck.plans(pid); seqs = {}
    for insid, car, beg, end, num, seq in pl:
        if end.strip(): continue
        seqs.setdefault(car, seq)
    return seqs
def target_for(pid, dos, seqs):
    if pid == "12232001" and datetime.datetime.strptime(dos, "%m/%d/%Y").date() < datetime.date(2025, 11, 1): return seqs.get(MCAD), "MCAD"
    return seqs.get(FCC), "FLO99"
def state(pid, vid, cid):
    st = payreasons.visit_state(pid, vid); c = [x for x in st if x["cid"] == cid]
    return (c[0] if c else None), st
def woins_live(c, co, code="WOINS"):
    return [w for w in c["wos"] if w["void"] != "1" and w["code"].strip() == code and abs(w["amount"] - co) < 0.011]
def codeless_live(c):
    return [p for p in c["pays"] if p["void"] != "1" and not p["reasons"]]

def correct(pid, vid, cid, co, checkno, paydate, carrier="FLO02", code="WOINS", note=""):
    """manual_post WOINS, void the $0 code-less payment it adds, verify. Returns (ok, message)."""
    c, st = state(pid, vid, cid)
    if not c: return False, "charge not live"
    if woins_live(c, co, code): return True, "already corrected"
    stale = codeless_live(c)
    if stale: return False, "a non-void code-less payment already sits on the charge (%s) - review first" % [(p["id"], p["amount"]) for p in stale]
    if DRY: return True, "DRY manual_post %s 0 + %s %.2f chk %s dd %s, then void the $0 line" % (carrier, code, co, checkno, paydate)
    ok, msg = manual_post.post(cid, carrier, 0.0, co, code, checknumber=checkno, depositdate=paydate, note=note)
    L("   manual_post %s %.2f -> %s %s" % (code, co, ok, msg[:120]))
    if not ok: return False, "manual_post fault: " + msg[:160]
    time.sleep(1.0); c, st = state(pid, vid, cid)
    if not woins_live(c, co, code): return False, "write-off did not land"
    for p in codeless_live(c):
        okv, msgv = void_tx.void_payment(pid, cid, p["id"]); L("   void $0 code-less payment %s -> %s %s" % (p["id"], okv, str(msgv)[:100]))
        if not okv: return False, "void of the $0 payment %s failed: %s" % (p["id"], str(msgv)[:120])
    time.sleep(1.0); c, st = state(pid, vid, cid)
    good = bool(woins_live(c, co, code)) and not codeless_live(c) and payreasons.balanced(st)
    return good, "verified: WOINS %.2f live, code-less %d, balanced %s, insbal %.2f patbal %.2f" % (co, len(codeless_live(c)), payreasons.balanced(st), c["insbalance"], c["patbalance"])

stop = False
for sec in ONLY:
    pid = SEC[sec]; mine = [l for l in lines if l["pid"] == pid]; faults = 0
    seqs = plan_seqs(pid); medseq = seqs.get(MEDICARE)
    L("== section %s pat%s card %s: %d lines; live plan seqs medicare %s fcc %s mcad %s" % (sec, pid, CARD[sec], len(mine), medseq, seqs.get(FCC), seqs.get(MCAD)))
    routed = set()
    try:   # a visit this helper already rebilled today (an earlier, timed-out pass) is routed ONCE - the 10/6 one-rebill rule across runs
        for ln in open("registers/rebill_log.jsonl"):
            e = json.loads(ln)
            if e.get("by") == "fix_inflated_wo_1007.py" and 200 <= int(e.get("status", 0)) < 300 and str(e.get("at", ""))[:10] == "2026-10-07": routed.add(str(e["visit"]))
    except FileNotFoundError: pass
    if routed: L("   %d visit(s) already routed today by an earlier pass - not rebilled again" % len(routed))
    for l in mine:
        vid, cid, co = l["vid"], l["cid"], round((l["co45"] or 0) + (l["co253"] or 0), 2)
        era = ERAID.get(l["checkno"]) or ("n/a" if "--include-no-era" in sys.argv else None)   # the write-off recipe needs no remit: the live payment carries the reasons (William's card F covers all 10 lines)
        tseq, tname = target_for(pid, l["dos"], seqs)
        tag = "pat%s v%s c%s %s %s open %s co %.2f check %s(era %s) -> %s seq %s" % (pid, vid, cid, l["dos"], l["cpt"], l["insbal"], co, l["checkno"], era, tname, tseq)
        if not era: L(tag + " HOLD: no ERA check id for this payment number"); out["hold"].append(dict(l, why="no ERA id")); continue
        if not tseq or not medseq: L(tag + " HOLD: plan sequence missing on the chart"); out["hold"].append(dict(l, why="plan seq missing")); continue
        ok, msg = correct(pid, vid, cid, co, l["checkno"], l.get("paydate") or "09/09/2026",
                          note="9/9/2026 Medicare ERA %s contractual CO45+CO253 - card %s, William 10/7/2026" % (era, CARD[sec]))
        L(tag + " | " + msg)
        if DRY: out["done"].append(dict(l, plan="DRY WOINS %.2f + route %s seq %s" % (co, tname, tseq))); continue
        if not ok:
            faults += 1; out["hold"].append(dict(l, why=msg))
            if faults >= 3: L("3 consecutive faults - stopping section"); break
            continue
        faults = 0
        c, st = state(pid, vid, cid)
        if c and c["patbalance"] > 0.005:
            # AMD moves the PR2 to the PATIENT side when the write-off lands (9/29 lesson); a dual is never billed - back to insurance, no rebill
            mv = move_to_ins.move(cid, rebill=False); L("   move_to_ins (patient %.2f -> insurance, no rebill) -> %s" % (c["patbalance"], str(mv)[:120])); time.sleep(0.8)
        if vid in routed: out["done"].append(dict(l, result="corrected; visit already routed this run"))
        else:
            rr = freq1_visit.reroute(vid, cid, "%s,%s" % (medseq, tseq), tseq); routed.add(vid)
            L("   route -> %s seq %s: %s" % (tname, tseq, str(rr)[:160])); out["done"].append(dict(l, result="corrected + routed %s seq %s: %s" % (tname, tseq, str(rr)[:120])))
            time.sleep(0.8)
        if FIRST: L("--first-only: stopping after the first corrected line"); stop = True; break
    if sec == "C" and not stop:
        cid, amt = WO_C
        # the charge's visit id is read live (the register only lists the 9/9 lines)
        import txh
        root = txh.fetch(pid); vid_c = next((payreasons.num(x.get("visit")) for x in root.iter("charge") if payreasons.num(x.get("id")) == cid), None)
        ok, msg = correct(pid, vid_c, cid, amt, "PAPER1007", "10/07/2026", carrier="FLO99", code="WOLATE",
                          note="FCC secondary past timely filing - 1/31/2024 99497 coinsurance, William 10/7/2026 fix as recommended (card %s)" % CARD[sec])
        L("C write-off charge %s v%s WOLATE %.2f | %s" % (cid, vid_c, amt, msg)); out["done" if ok else "hold"].append({"pid": pid, "vid": vid_c, "cid": cid, "result": "WOLATE %.2f: %s" % (amt, msg)})
    if stop: break
json.dump(out, open("registers/fix_inflated_wo_%s_%s%s.json" % (STAMP, ONLY, "_dry" if DRY else ("_first" if FIRST else "")), "w"), indent=1)
L("SUMMARY sections %s done %d hold %d (dry=%s)" % (ONLY, len(out["done"]), len(out["hold"]), DRY))
