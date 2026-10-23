# PLAIN ENGLISH (ehpa Billing Button run 2026-10-23T0424Z - the two board rows William answered 04:20-04:27Z 10/23)
# Decides: nothing new - it does exactly what William wrote on the Insurance Refresh Board, from a LIVE read of each chart first.
#   P: chart 17470713 (row poulter-ellery-gwen-denials) - William 04:20Z: "no AARP plan at all, say so and the 25 coinsurance
#      balances go to the patient statement cycle write off no secondary". The chart's AAR01 plan (seq 4) is already end-dated
#      01/01/2026 (dead), Medicare paid all 25 visits, and the Medicare coinsurance sits as an INSURANCE balance on 19 of them
#      (the other 6 are already on the patient side). Per William: move each open insurance balance to the PATIENT balance
#      (full-visit echo resave - every live charge echoed, insbalance -> patbalance, insportion -> patportion; the proven
#      10/4 shape, act_0310_1004.py step H), NO rebill, then complete the 25 AARP exclusions of claim run 1700302 (hideexclusions).
#      The write-off ("no secondary") follows the patient statement cycle, as on chart 17477183 (10/4) - not posted here.
#   T: chart 17471204 (row tolliver-tracy) - William 04:27Z pasted the Aetna subscriber block: subscriber = the spouse (resp21479706
#      already on the chart), relationship SPOUSE. The AET07 plan ins9510367 carries that subscriber id but relationship SELF
#      (relationship="1" hipaarelationship="18") - the dependent billed as the subscriber, which is the 277 reject
#      'ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DATES OF SERVICE: PATIENT'. Fix: updateinsurance relationship=2 /
#      hipaarelationship=01 (spouse) and strip the group number (William's no-group rule), patient order 2 (the chart's
#      order was blank), then ONE frequency-1 rebill per visit to seq 2 (deceased guard inside amd.rebill_charge) for the
#      three rejected visits of claim run 1700311, then hideexclusions for the three.
# Rules it uses: read the transaction history first (no visit here is rebilled that carries a primary payment except as the
#   named frequency-1 re-send to the plan William named); one rebill per visit per run; --dry prints every write, --live sends.
# Never touches: payments already posted, write-offs, hospitalizationto, group numbers (removes one), other charts.
#   cd /home/claude/unbilled && python3 board_act_1023_0424.py --dry [--only P|T]
#   cd /home/claude/unbilled && python3 board_act_1023_0424.py --live [--only P|T]
import amd, resave, freq1_visit, ins_update, payreasons, re, json, sys, time, datetime
LIVE = "--live" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-10-23T0424Z"
NOW = lambda: datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
amd.login_cached()
out = {"stamp": STAMP, "live": LIVE, "started": NOW(), "P": {}, "T": {}}
def L(m): print(m, flush=True); out.setdefault("log", []).append(m)
def want(k): return ONLY is None or k in ONLY
def first_cid(pid, vid):
    v = payreasons.visit_state(pid, vid)
    live = [c for c in v if float(c.get("fee") or 0) > 0]
    return live[0]["cid"] if live else None, live
def hide(run, items):
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (vv, cl) for vv, cl in items) + "</visitlist>"
    if not LIVE: return "DRY hideexclusions run %s x%d" % (run, len(items))
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:200])
def still_open(run, pid):
    """Re-list the run right before acting (10/14 rule) - only rows still open are worked."""
    r = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": run, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    rows = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<visit [^>]*>', r)]
    return [(x.get("id"), x.get("claimid")) for x in rows if re.sub(r"\D", "", x.get("patientid") or "") == pid]

# ---------------- P. chart 17470713 - coinsurance to the patient statement cycle, complete the 25 AARP exclusions ----------------
if want("P"):
    pid, run = "17470713", "1700302"
    rows = still_open(run, pid); L("P run %s open rows for chart %s: %d" % (run, pid, len(rows)))
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    aarp = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan [^>]*>', d)]
    aarp = [p for p in aarp if p.get("carrier") == "car6600"]
    L("P AAR01 plan: %s" % [(p.get("id"), p.get("begindate"), p.get("enddate")) for p in aarp])
    out["P"] = {"run": run, "visits": [], "moved": 0.0, "already_patient": 0.0}
    done = []
    for vid, claimid in rows:
        cid, live = first_cid(pid, vid)
        if not cid: L("P v%s no live charge - skipped" % vid); continue
        if any(float(c.get("insbalance") or 0) > 0 and (c.get("carrier") or "") != "AAR01" for c in live):
            L("P v%s open insurance balance NOT at AAR01 (%s) - held" % (vid, [c.get("carrier") for c in live])); continue
        vis, pat, allc = resave.visit_charges(cid); chg = ""; moved = 0.0; patside = 0.0
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            ib = float(c.get("insbalance") or 0); patside += float(c.get("patbalance") or 0)
            if ib > 0:
                a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
                a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved += ib
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        rec = {"vid": vid, "claimid": claimid, "cid": cid, "moved": round(moved, 2), "already_patient": round(patside, 2)}
        if moved == 0:
            rec["result"] = "already on the patient side"; done.append((vid, claimid)); out["P"]["visits"].append(rec); out["P"]["already_patient"] += patside
            L("P v%s coinsurance %.2f already on the patient - complete the exclusion" % (vid, patside)); continue
        if not LIVE:
            rec["result"] = "DRY move %.2f to the patient" % moved; done.append((vid, claimid)); out["P"]["visits"].append(rec); out["P"]["moved"] += moved
            L("P v%s DRY move %.2f insurance -> patient (%d charges echoed)" % (vid, moved, len(allc))); continue
        va = dict(vis.attrib); va["force"] = "1"
        r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                             "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
        time.sleep(0.8); x2 = resave.detail(cid)
        st = re.findall(r'id="charge\d+"[^>]*?insbalance="([^"]*)" patbalance="([^"]*)"', x2)
        nlive = len([1 for c in re.findall(r'<charge [^>]*>', x2) if 'void="1"' not in c])
        ok = "Fault" not in r and all(float(i or 0) == 0 for i, p in st)
        rec["result"] = ("moved %.2f to the patient -> %s" % (moved, st)) if ok else ("FAULT " + re.sub(r"\s+", " ", r[:200]) if "Fault" in r else "insurance balance still open after the resave %s" % st)
        L("P v%s %s" % (vid, rec["result"]))
        if ok: done.append((vid, claimid)); out["P"]["moved"] += moved
        out["P"]["visits"].append(rec); time.sleep(0.4)
    out["P"]["moved"] = round(out["P"]["moved"], 2); out["P"]["already_patient"] = round(out["P"]["already_patient"], 2)
    if done: out["P"]["hide"] = hide(run, done); L("P hideexclusions run %s x%d -> %s" % (run, len(done), out["P"]["hide"]))
    L("P SUMMARY: %d visits, %.2f moved to the patient this run, %.2f already there" % (len(out["P"]["visits"]), out["P"]["moved"], out["P"]["already_patient"]))

# ---------------- T. chart 17471204 - spouse subscriber on the Aetna plan, resend the 3 claims of run 1700311 ----------------
if want("T"):
    pid, run, insid = "17471204", "1700311", "ins9510367"
    rows = still_open(run, pid); L("T run %s open rows for chart %s: %d" % (run, pid, len(rows)))
    out["T"] = {"run": run, "visits": []}
    if LIVE:
        ok, msg = ins_update.update(pid, insid, relationship="2", hipaarelationship="01", grpnum="", grpname="")
        out["T"]["plan_edit"] = (ok, msg); L("T plan %s relationship -> spouse, group stripped: %s %s" % (insid, ok, msg[:300]))
        ok2, msg2 = ins_update.update(pid, insid, sequence="2")
        out["T"]["order"] = (ok2, msg2); L("T patient order 2: %s %s" % (ok2, msg2[:300]))
        d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
        p = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan id="%s"[^>]*>' % insid, d)]
        out["T"]["plan_after"] = {k: p[0].get(k) for k in ("relationship", "hipaarelationship", "grpnum", "grpname", "subscriber", "sequence")} if p else None
        L("T plan after: %s | insorder %s" % (out["T"]["plan_after"], re.search(r'<patient [^>]*?insorder="([^"]*)"', d).group(1)))
        if not ok: L("T plan edit failed - no rebill"); rows = []
    else:
        L("T DRY updateinsurance %s relationship=2 hipaarelationship=01 grpnum='' grpname=''; DRY patient order 2" % insid)
    done = []
    for vid, claimid in rows:
        cid, live = first_cid(pid, vid)
        rec = {"vid": vid, "claimid": claimid, "cid": cid, "insbal": sum(float(c.get("insbalance") or 0) for c in live), "pays_nonzero": [p for c in live for p in c.get("pays", []) if float(p.get("amount") or 0) > 0 and p.get("void") != "1"]}
        if rec["pays_nonzero"]:
            rec["result"] = "HELD - a payment is posted on the visit"; L("T v%s %s" % (vid, rec["result"])); out["T"]["visits"].append(rec); continue
        if not LIVE:
            rec["result"] = "DRY reroute order 2 + freq1 rebill seq 2 (insbal %.2f)" % rec["insbal"]; done.append((vid, claimid))
        else:
            res = freq1_visit.reroute(vid, cid, "2", 2); rec["result"] = res[:300]
            if "-> 204" in res and "BLOCKED" not in res and "FAULT" not in res and "NOT rebilled" not in res: done.append((vid, claimid))
        L("T v%s %s" % (vid, rec["result"])); out["T"]["visits"].append(rec); time.sleep(0.5)
    if done: out["T"]["hide"] = hide(run, done); L("T hideexclusions run %s x%d -> %s" % (run, len(done), out["T"]["hide"]))
    L("T SUMMARY: %d visits re-sent to Aetna seq 2" % len(done))
out["ended"] = NOW()
json.dump(out, open("registers/board_act_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1, default=str)
L("DONE %s" % ("LIVE" if LIVE else "DRY"))
