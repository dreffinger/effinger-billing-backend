# PLAIN ENGLISH (William 10/7/2026 on board row paper-eob-writeoffs-0923: "fix them as recommended" - the 51 inflated 9/9/2026 Medicare postings)
# Decides: nothing new - applies the 10/5 recommendation on that row and the 10/6 CO-45 lesson: the 9/9/2026 Medicare ERA Post-button
#   payments on four dual charts carry their CO-45 / CO-253 reason codes but NO write-off, so each balance = fee minus paid (inflated by
#   the contractual, $2,906.91 on 51 lines, $3,746.35 open - registers/inflated_medicare_lines_2026-10-07T0510Z.json, read live 05:5xZ).
#   Sections, one per chart (--only A|B|C|D; the approval cards are one per section):
#     A = pat17471688 (34 lines, checks 816705526 + 816846022)   B = pat12232001 (4 lines)
#     C = pat17471172 (3 lines + the 1/31/2024 99497 coinsurance $31.29, charge 22443840: WOLATE write-off under FLO99 - FCC secondary
#         past its timely filing, the row's held item William now closes)                                 D = pat21564 (10 lines)
#   Per line: (1) the check's remit must be in era_details/<checkid>.json - payreasons.details(checkid); a processed / dismissed check
#   answers no claims, so payreasons.restore (reversedismiss) -> details(fresh) -> cache -> payreasons.redismiss (the 9/19 recipe);
#   (2) `python3 era_co45_relink.py <checkid> --live --cid <chargeid>` = VOID the Post-button payment + ERA-linked re-post (addpayments
#   postingmethod=era with the remit's reasons) + WOINS for the CO amounts, PR never written off - verified by a live re-read (a non-void
#   WOINS of the CO amount on the charge); (3) once corrected, the visit is routed as a frequency-1 SECONDARY to the Medicaid plan in force
#   on the DOS (the 10/5 eligibility read): FCC (FLO99) for every chart, Medicaid FFS (MCAD) for pat12232001's pre-11/2025 dates -
#   freq1_visit.reroute(vid, cid, "<medicare seq>,<plan seq>", <plan seq>) = one order write + ONE rebill (William 10/6). A visit with
#   two lines is routed once. Check 815793370 (2 lines, pat21564 9/30/2024) has no ERA id in the dismissed list - HELD and reported.
#   --dry (default): prints the plan from the register + the live plan sequences, sends nothing; --live does it; 3 consecutive faults stop
#   the section. Register registers/fix_inflated_2026-10-07T0510Z_<section>[_dry].json.
# Never touches: PR amounts, insurance plans, charges already carrying WOINS, any charge not in the register.
import amd, payreasons, freq1_visit, precheck, json, sys, os, re, subprocess, time, datetime
DRY = "--live" not in sys.argv
ONLY = sys.argv[sys.argv.index("--only") + 1].upper() if "--only" in sys.argv else "ABCD"
STAMP = "2026-10-07T0510Z"
SEC = {"A": "17471688", "B": "12232001", "C": "17471172", "D": "21564"}
CHECKIDS = {"816705526": "894975", "815638157": "893557", "815915909": "893939", "816846022": "895100", "816005534": "894021",
            "815906990": "893899", "815577106": "893470", "816245550": "894399"}   # payment number -> AMD ERA check id (dismissed list)
MEDICARE, FCC, MCAD = "car6085", "car42008", "car6113"
WO_C = ("22443840", 31.29)   # Thurlow 1/31/2024 99497 coinsurance - WOLATE under FLO99, check ref PAPER1007
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
def cached(checkid):
    d = payreasons.details(checkid)
    if d.get("eracheckdetails"): return True, "cached"
    if DRY: return False, "DRY - would restore / cache / redismiss"
    ok, msg = payreasons.restore(checkid)
    if not ok: return False, "restore failed: " + msg
    d = payreasons.details(checkid, fresh=True); ok2, msg2 = payreasons.redismiss(checkid)
    return bool(d.get("eracheckdetails")), "restored + cached (%d claims), redismiss %s" % (len(d.get("eracheckdetails", [])), ok2)
def corrected(pid, vid, cid, co):
    st = payreasons.visit_state(pid, vid); c = [x for x in st if x["cid"] == cid]
    if not c: return False, None
    w = [x for x in c[0]["wos"] if x["void"] != "1" and x["code"].strip() == "WOINS" and abs(x["amount"] - co) < 0.011]
    return bool(w), c[0]

for sec in ONLY:
    pid = SEC[sec]; mine = [l for l in lines if l["pid"] == pid]; faults = 0
    seqs = plan_seqs(pid); medseq = seqs.get(MEDICARE)
    L("== section %s pat%s: %d lines; live plan seqs medicare %s fcc %s mcad %s" % (sec, pid, len(mine), medseq, seqs.get(FCC), seqs.get(MCAD)))
    routed = set()
    for l in mine:
        vid, cid, co = l["vid"], l["cid"], round((l["co45"] or 0) + (l["co253"] or 0), 2)
        chk = CHECKIDS.get(l["checkno"]); tseq, tname = target_for(pid, l["dos"], seqs)
        tag = "pat%s v%s c%s %s %s open %s co %.2f check %s(era %s) -> %s seq %s" % (pid, vid, cid, l["dos"], l["cpt"], l["insbal"], co, l["checkno"], chk, tname, tseq)
        if not chk: L(tag + " HOLD: no ERA check id for this payment number"); out["hold"].append(dict(l, why="no ERA id")); continue
        if not tseq or not medseq: L(tag + " HOLD: plan sequence missing on the chart"); out["hold"].append(dict(l, why="plan seq missing")); continue
        okc, msgc = cached(chk); L(tag + " | cache: " + msgc)
        if DRY: out["done"].append(dict(l, plan="DRY relink + route %s seq %s" % (tname, tseq))); continue
        if not okc: faults += 1; out["hold"].append(dict(l, why="remit not cached: " + msgc));
        if not okc:
            if faults >= 3: L("3 consecutive faults - stopping section"); break
            continue
        already, live = corrected(pid, vid, cid, co)
        if not already:
            r = subprocess.run(["python3", "era_co45_relink.py", chk, "--live", "--cid", cid], capture_output=True, text=True, timeout=600)
            L("   relink: " + re.sub(r"\s+", " ", (r.stdout or "")[-300:]) + (" ERR " + r.stderr[-200:] if r.returncode else ""))
            time.sleep(1.0); already, live = corrected(pid, vid, cid, co)
        if not already:
            faults += 1; L("   NOT corrected (no WOINS %.2f on the charge after the relink) - not routed" % co); out["hold"].append(dict(l, why="relink did not land"))
            if faults >= 3: L("3 consecutive faults - stopping section"); break
            continue
        faults = 0; L("   corrected: WOINS %.2f on charge %s, live insbal %s patbal %s" % (co, cid, live["insbalance"], live["patbalance"]))
        if vid in routed: out["done"].append(dict(l, result="corrected; visit already routed this run")); continue
        rr = freq1_visit.reroute(vid, cid, "%s,%s" % (medseq, tseq), tseq); routed.add(vid)
        L("   route -> %s seq %s: %s" % (tname, tseq, str(rr)[:160])); out["done"].append(dict(l, result="corrected + routed %s seq %s: %s" % (tname, tseq, str(rr)[:120])))
        time.sleep(0.8)
    if sec == "C":
        import manual_post
        cid, amt = WO_C
        if DRY: L("C write-off: DRY manual_post.post(%s, FLO99, 0, %.2f, WOLATE, PAPER1007, 10/07/2026)" % (cid, amt))
        else:
            r = manual_post.post(cid, "FLO99", 0.0, amt, "WOLATE", "PAPER1007", "10/07/2026", "FCC secondary past timely filing - 1/31/2024 99497 coinsurance, William 10/7/2026 fix as recommended")
            L("C write-off charge %s WOLATE %.2f -> %s" % (cid, amt, str(r)[:160])); out["done"].append({"pid": pid, "cid": cid, "result": "WOLATE %.2f: %s" % (amt, str(r)[:100])})
json.dump(out, open("registers/fix_inflated_%s_%s%s.json" % (STAMP, ONLY, "_dry" if DRY else ""), "w"), indent=1)
L("SUMMARY sections %s done %d hold %d (dry=%s)" % (ONLY, len(out["done"]), len(out["hold"]), DRY))
