# PLAIN ENGLISH (William's Insurance Refresh Board answers of 10/15/2026 03:41-03:55Z, applied by the 1 AM ET run)
# Decides: Nothing on its own - each section is one chart William answered on its board row. --dry (default) reads and
#   plans, --live writes. --only A,B,... runs the named sections only. Register registers/board_1015_0510_<dry|live>.json.
# Sections:
#   A chart 25994 v19455138: 99497 (c23366299) $80.67 open at BCBS after PR-96 non-covered -> WONCS (William: "WONCS").
#   B chart 17477498 v19455608: CCM 99487 (c23366951) $206 on the PATIENT balance after PR-204 -> move back to insurance, WONCS.
#   C chart 20379 v19416099: CCM 99487 (c23319630) at Humana seq 4 - swap I63.9 -> I69.30 (full-visit echo, no rebill),
#     then frequency-7 resend with Humana's claim number (William's words on the row).
#   D chart 48449 v19457091: 99344 -> 99349 (established patient), resend as an ORIGINAL (William: "resend as original") to
#     the payer the AMD 271 names first (Medicare ACTIVE -> Medicare first, Florida Blue second; else Florida Blue).
#   E chart 17471326 v19457089: 99344 -> 99349, resend as an original to Florida Blue seq 1.
#   F chart 17474290 v19419306: 99222 -> 99232 (William: "this should be a 99232"), corrected claim frequency 7 to Florida
#     Blue / Health Options with the payer claim number (Q100001347267463, the number FB adjudicated the 10/6 correction under).
#   G chart 23969: patient insurance order 1,2 (Medicare, Cigna) - one API retry; if AMD keeps 1,3, add a FOURTH plan (Cigna
#     car6687, same member id as ins2246) and point the order at it (William 10/15: "add a fourth insurance ... point to that one").
# Rules it uses: one rebill per visit; recode = full-visit echo (resave.CHG_FIELDS); never a group number; PR amounts stay
#   unless William says WONCS (he did, A and B); never a payment-posted charge recoded (A-F have none except A's paid 99306,
#   which is not touched - only the 99497 line is written off).
# Never touches: other visits, other charges, the 99306 payments on A.
import amd, resave, recode, freq1_visit, freq7_visit, manual_post, move_to_ins, ins_update, add_ins, json, sys, re, time
LIVE = "--live" in sys.argv
ONLY = [a for a in sys.argv if a.startswith("--only")]
ONLY = set(ONLY[0].split("=")[1].split(",")) if ONLY and "=" in ONLY[0] else (set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else set("ABCDEFG"))
STAMP = "2026-10-15T0510Z"
amd.login_cached()
REG = {"stamp": STAMP, "live": LIVE, "sections": {}}
def save(): json.dump(REG, open("registers/board_1015_0510_%s.json" % ("live" if LIVE else "dry"), "w"), indent=1, default=str)
def S(sec, *m):
    line = " ".join(str(x) for x in m); print(sec, line); REG["sections"].setdefault(sec, []).append(line); save()
def charge_state(cid):
    vis, pat, allc = resave.visit_charges(cid)
    me = [c for c in allc if c.get("id") == "charge%s" % cid]
    return vis, pat, allc, (me[0] if me else None)

# ---- A  chart 25994 WONCS 80.67 on c23366299 (insurance balance, BCBS)
if "A" in ONLY:
    try:
        ok, msg = manual_post.post("23366299", "BCBS", 0.0, 80.67, "WONCS", "620268423", "10/14/2026",
                                   "ERA 1053164 Florida Blue PR-96/N130 non-covered 99497 - William 10/15 'WONCS' (run %s)" % STAMP, dry=not LIVE)
        S("A", "c23366299 WONCS 80.67 ->", ok, msg[:200])
    except Exception as e: S("A", "ERROR", str(e)[:200])

# ---- B  chart 17477498: move 206 back to insurance, then WONCS
if "B" in ONLY:
    try:
        r = move_to_ins.move("23366951", None, dry=not LIVE, rebill=False)
        S("B", "c23366951 move_to_ins ->", r[:200])
        if LIVE: time.sleep(1)
        ok, msg = manual_post.post("23366951", "BCBS", 0.0, 206.00, "WONCS", "190596986", "10/14/2026",
                                   "ERA 1053166 Florida Blue PR-204/N130 CCM not a covered benefit - William 10/15 'WONCS' (run %s)" % STAMP, dry=not LIVE)
        S("B", "c23366951 WONCS 206.00 ->", ok, msg[:200])
    except Exception as e: S("B", "ERROR", str(e)[:200])

# ---- C  chart 20379: I63.9 -> I69.30 then freq 7 to Humana seq 4 with claim 820262810497584
if "C" in ONLY:
    try:
        vis, pat, allc, me = charge_state("23319630")
        dx = (me.get("diagcodes") or "").split() if me is not None else []
        S("C", "visit", vis.get("id"), "insorder", vis.get("insorder"), "charges", len(allc), "diagcodes", dx, "paid", me.get("paid") if me is not None else None)
        if "dcode1034545006" not in dx:
            S("C", "I63.9 (dcode1034545006) not on the charge - nothing to swap; freq7 only")
        if not LIVE:
            S("C", "DRY: swap dcode1034545006 -> dcode1034545425 by full-visit echo, then freq7_visit.run(19416099, 23319630, 4, 820262810497584)")
        else:
            if "dcode1034545006" in dx:
                def e(a):
                    d = (a.get("diagcodes") or "").split()
                    if "dcode1034545006" in d: a["diagcodes"] = " ".join("dcode1034545425" if x == "dcode1034545006" else x for x in d); return True
                    return False
                c2, msg = recode._save("23319630", e); S("C", "dx swap ->", msg)
                if c2 is None: raise RuntimeError("swap failed")
                time.sleep(1)
            res = freq7_visit.run("19416099", "23319630", "4", "820262810497584"); S("C", "freq7 ->", res)
    except Exception as e: S("C", "ERROR", str(e)[:200])

# ---- D  chart 48449: 99344 -> 99349, original claim to the right payer
if "D" in ONLY:
    try:
        order = sys.argv[sys.argv.index("--d-order") + 1] if "--d-order" in sys.argv else "2"
        seq = order.split(",")[0]
        vis, pat, allc, me = charge_state("23368913")
        S("D", "visit", vis.get("id"), "insorder", vis.get("insorder"), "proccode", me.get("proccode") if me is not None else None, "paid", me.get("paid") if me is not None else None, "-> order", order, "seq", seq)
        if not LIVE: S("D", "DRY: recode pcode of 99344 -> pcode65142 (99349) with insorder %s in the same echo, then freq1 seq %s" % (order, seq))
        else:
            def e(a):
                if a.get("proccode") == "pcode65142": return False
                if a.get("proccode") and a.get("proccode") != "pcode65142": a["proccode"] = "pcode65142"; return True
                return False
            vis0, pat0, allc0 = resave.visit_charges("23368913"); chg = ""; changed = 0
            for c in allc0:
                a = {"id": c.get("id")}
                for f in resave.CHG_FIELDS:
                    if c.get(f) is not None: a[f] = c.get(f)
                if e(a): changed += 1
                chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
            va = dict(vis0.attrib); va["force"] = "1"; va["insorder"] = order
            r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat0.get("id"), "episodeid": vis0.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
            if "Fault" in r: raise RuntimeError("resave FAULT " + re.sub(r"\s+", " ", r[:200]))
            time.sleep(1)
            vis2, pat2, allc2 = resave.visit_charges("23368913") if any(c.get("id") == "charge23368913" for c in allc0) else (None, None, [])
            S("D", "recode saved: changed", changed, "live now", [(c.get("id"), c.get("proccode")) for c in allc2], "insorder", vis2.get("insorder") if vis2 is not None else "?")
            # the recode may re-create the charge under a new id: find the live charge of the visit
            cid = re.sub(r"\D", "", allc2[0].get("id")) if allc2 else "23368913"
            res = freq1_visit.run("19457091", cid, seq); S("D", "freq1 ->", res)
            if "," in order:
                okp, mp = ins_update.update("48449", "ins6005745", sequence=order); S("D", "patient order %s ->" % order, okp, mp[:200])
    except Exception as e: S("D", "ERROR", str(e)[:200])

# ---- E  chart 17471326: 99344 -> 99349, original to Florida Blue seq 1
if "E" in ONLY:
    try:
        vis, pat, allc, me = charge_state("23368911")
        S("E", "visit", vis.get("id"), "insorder", vis.get("insorder"), "proccode", me.get("proccode") if me is not None else None, "paid", me.get("paid") if me is not None else None)
        if not LIVE: S("E", "DRY: recode.swap_proc(23368911, {pcode of 99344: pcode65142}, 1)")
        else:
            old = me.get("proccode"); res = recode.swap_proc("23368911", {old: "pcode65142"}, "1"); S("E", "swap_proc + freq1 ->", res)
    except Exception as e: S("E", "ERROR", str(e)[:200])

# ---- F  chart 17474290: 99222 -> 99232, freq 7 with the payer claim number
if "F" in ONLY:
    try:
        icn = sys.argv[sys.argv.index("--f-icn") + 1] if "--f-icn" in sys.argv else "Q100001347267463"
        vis, pat, allc, me = charge_state("23324249")
        S("F", "visit", vis.get("id"), "insorder", vis.get("insorder"), "proccode", me.get("proccode") if me is not None else None, "paid", me.get("paid") if me is not None else None, "icn", icn)
        if not LIVE: S("F", "DRY: recode 99222 -> 99232 (pcode lookup from the visit's own detail), then freq7_visit.run(19419306, <cid>, 1, %s)" % icn)
        else:
            old = me.get("proccode")
            # pcode for 99232: taken from the practice's procedure list (pcode65084 is 99223 per the 10/4 register; 99232 = pcode65085 per carriers/procs map)
            x = resave.detail("23369825"); new = re.search(r'proccode="(pcode\d+)"', x).group(1)
            S("F", "pcode for 99232 from charge 23369825 ->", new)
            def e(a):
                if a.get("proccode") == old: a["proccode"] = new; return True
                return False
            c2, msg = recode._save("23324249", e); S("F", "recode ->", msg)
            if c2 is None: raise RuntimeError("recode failed")
            time.sleep(1)
            cid = re.sub(r"\D", "", c2[0].get("id")) if c2 else "23324249"
            res = freq7_visit.run("19419306", cid, "1", icn); S("F", "freq7 ->", res)
    except Exception as e: S("F", "ERROR", str(e)[:200])

# ---- G  chart 23969 patient order
if "G" in ONLY:
    try:
        if not LIVE: S("G", "DRY: ins_update.update(23969, ins2246, sequence='1,2'); if not landed -> add_ins.add(23969, car6687, <ins2246 member id>, 07/22/2022, coverage 2) then sequence 1,<new>")
        else:
            ok, msg = ins_update.update("23969", "ins2246", sequence="1,2"); S("G", "order 1,2 via ins2246 ->", ok, msg[:300])
            if not ok:
                r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat23969", "nocookie": "1"}))
                num = re.search(r'<insplan id="ins2246"[^>]*subscribernum="([^"]*)"', r)
                insid, seqnew = add_ins.add("23969", "car6687", num.group(1), "07/22/2022", "2"); S("G", "fourth plan ->", insid, seqnew)
                if insid:
                    ok2, msg2 = ins_update.update("23969", insid, sequence="1,%s" % seqnew); S("G", "order 1,%s via %s ->" % (seqnew, insid), ok2, msg2[:300])
    except Exception as e: S("G", "ERROR", str(e)[:200])
save(); print("DONE", "live" if LIVE else "dry")
