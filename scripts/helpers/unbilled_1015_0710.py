# PLAIN ENGLISH (Unbilled column work of the 2026-10-15T0710Z run - one 'Insurance order is missing' chart)
# Decides: nothing on its own - the coverage comes from the cascade this run: Stedi insurance discovery on 10/15/2026 named
#   HUMANA 'HUM Full Ac Giveback' Medicare PPO, Active Coverage, plan begin 02/01/2024, service date 10/12/2026, for the
#   chart below (its Medicare MBI lookup answered ERR 72 under the chart SSN - the chart SSN or name needs a look, reported).
#   --dry (default) plans, --live writes, --only A runs the named section. Register registers/unbilled_1015_0710_<dry|live>.json.
# Sections:
#   A chart 17478061 (HCA 99223 10/12/2026 v19457793 + 99232 10/13/2026 v19457780, $421, zero plans): add HUMANA car6285
#     (member id read from patient_db/pat17478061/[name]_[DOB].json at run time, begin 02/01/2024, no group, finclass MC),
#     patient order = that plan, admission 10/12/2026 (the 99223's own DOS) by updextrainsinfo hospitalizationfrom ONLY,
#     full-visit resave (every live charge echoed) with insorder <seq> and onhcfa 1, then release both visits from Unbilled.
# Rules it uses: no group numbers; hospitalizationfrom only, never hospitalizationto; full-visit echo on every resave (void trap);
#   one chart, no payment, no write-off, no rebill (the claims leave on the next claim run once released).
# Never touches: payments, write-offs, other charts, other visits.
import amd, resave, add_ins, ins_update, payreasons, txh, json, sys, re, time
LIVE = "--live" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else set("A")
STAMP = "2026-10-15T0710Z"
amd.login_cached()
REG = {"stamp": STAMP, "live": LIVE, "sections": {}}
def save(): json.dump(REG, open("registers/unbilled_1015_0710_%s.json" % ("live" if LIVE else "dry"), "w"), indent=1, default=str)
def S(sec, *m):
    line = " ".join(str(x) for x in m); print(sec, line, flush=True); REG["sections"].setdefault(sec, []).append(line); save()
def num(s): return re.sub(r"\D", "", str(s or ""))
def chart_visits(pid, vids):
    out = {}
    for vid in vids:
        root = txh.fetch_visit(pid, vid)
        cs = [c for c in root.iter("charge") if c.get("void") != "1" and c.get("visit") == str(vid)]
        out[vid] = [(num(c.get("id")), c.get("proccode"), c.get("dos"), c.get("insbal"), c.get("patbal")) for c in cs]
    return out
def hosp_from(vid, cpts, admit):
    for code in sorted(set(cpts)):
        if not LIVE: continue
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
            '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
        if "Fault" in r: return "FAULT extins %s: %s" % (code, re.sub(r"\s+", " ", r[:160]))
        time.sleep(0.4)
    return "hospitalizationfrom %s on %s" % (admit, sorted(set(cpts)))
def full_resave(cid, visit_over=None, charge_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        a.update(charge_over or {})
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(visit_over or {})
    if not LIVE: return True, "DRY resave %s charges=%d visit_over=%s charge_over=%s" % (vis.get("id"), len(allc), visit_over, charge_over)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                 "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return False, "resave FAULT %s: %s" % (vis.get("id"), re.sub(r"\s+", " ", r[:300]))
    time.sleep(0.8)
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    ok = len(c2) == len(allc)
    return ok, "resave %s live %d/%d insorder=%s onhcfa=%s hospfrom=%s" % (vis.get("id"), len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None)
def release(vids):
    if not LIVE: return "DRY release %s" % list(vids)
    out = []
    for v in vids:
        ok, msg = payreasons.release_visit(v); out.append((v, "released" if ok else "FAIL " + msg[:80])); time.sleep(0.3)
    return out
def add_plan(sec, pid, car, member, begin, coverage="1", finclass="CC"):
    if not LIVE: S(sec, "DRY add_ins", pid, car, "member ****%s" % str(member)[-4:], begin, coverage, finclass); return None, "99"
    insid, seq = add_ins.add(pid, car, member, begin, coverage, finclass); S(sec, "add_ins ->", insid, seq); return insid, seq
def bill_hospital(sec, pid, visits, order, admit):
    done = []
    for vid, chs in visits.items():
        cpts = [c[1] for c in chs]
        S(sec, "v%s" % vid, cpts, "->", hosp_from(vid, cpts, admit) if LIVE else "DRY hospitalizationfrom %s" % admit)
        ok, msg = full_resave(chs[0][0], {"insorder": order, "onhcfa": "1"}); S(sec, "v%s" % vid, msg[:220])
        if ok: done.append(vid)
        time.sleep(0.3)
    S(sec, "release ->", release(done))

# ---- A  chart 17478061: Humana Medicare PPO -> HUM01
if "A" in ONLY:
    try:
        pid = "17478061"; vids = ["19457793", "19457780"]
        d = json.load(open("patient_db/pat%s/[name]_[DOB].json" % pid))
        member = next(((it.get("subscriber") or {}).get("memberId") for it in d.get("items") or [] if "HUMANA" in ((it.get("payer") or {}).get("name") or "").upper()), None)
        if not member: raise RuntimeError("no Humana member id in the discovery answer")
        plans = ins_update._plans(pid)[1]
        have = [p for p, a in plans.items() if a.get("carrier") == "car6285"]
        if have: seq = plans[have[0]].get("sequence"); S("A", "HUM01 already on the chart", have, seq)
        else: insid, seq = add_plan("A", pid, "car6285", member, "02/01/2024", "1", "MC")
        if LIVE:
            okp, mp = ins_update.update(pid, "ins%s" % num(insid) if not have else have[0], sequence=str(seq)); S("A", "patient order", seq, "->", okp, mp[:160])
        vis = chart_visits(pid, vids); S("A", "visits", vis)
        bill_hospital("A", pid, vis, str(seq), "10/12/2026")
    except Exception as e: S("A", "ERROR", str(e)[:300])
save()
print("DONE", "live" if LIVE else "dry")
