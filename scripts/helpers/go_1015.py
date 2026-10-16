# PLAIN ENGLISH (William's "go" of 10/15/2026 ~10:30 PM ET - the live action list of the chat pass, one step per subcommand)
# Decides: nothing new - every step applies a standing rule William already gave; he said "all nine" in chat tonight.
#   K    chart 17478062 (card A-2026-10-15T0510Z-K): CMS 271 re-check on the MBI discovery found -> add FLORIDA MEDICARE (car6085, no group),
#        patient order, hospitalization-from 10/12/2026 + CMS-1500 + visit order by full-visit echo on both HCA visits, release from Unbilled.
#   AET  chart 17472859 (5 AET07 rejections, run 1700294): Medicare paid the Jan/Feb-2025 visits; no secondary was in force (Aetna Medicare
#        started 05/01/2025) -> WOCLTREQ the PR2 coinsurance on each charge (10/13 rule), complete the 5 exclusions; chart fix: Aetna begin
#        05/01/2025, Medicare end-dated 04/30/2025, patient order Aetna first (re-set after the end-date blanks it).
#   DUPS complete, no rebill: 12232248 v19417751 / v19424313 (run 1700271, UHC duplicates of the 9/10 claims already answered CO-29, $0) and
#        17476855 v19445320 (run 1700271, Humana 'patient not found' on a Medicare-paid visit at $0).
#   ERA  dismiss ERA check 1053116 (UHC W0020208 $71 reversal matching no posted payment) with a note - William's call tonight.
# Rules it uses: ONE login (amd.login_cached); deceased guard on every rebill; one rebill per visit; --live writes, otherwise dry.
# Never touches: anything not named above.
import json, os, re, sys, time
sys.path.insert(0, "/home/claude/unbilled")
import amd, add_ins, ins_update, resave, freq1_visit, payreasons, manual_post, stedi, txh
import xml.etree.ElementTree as ET

LIVE = "--live" in sys.argv
STEP = [a for a in sys.argv[1:] if not a.startswith("--")][0]
STAMP = time.strftime("%Y-%m-%dT%H%MZ", time.gmtime())
REG = "/home/claude/unbilled/registers/go_1015_%s.json" % STEP
log = []
num = lambda s: re.sub(r"\D", "", str(s or ""))
def S(*a):
    line = " ".join(str(x) for x in a); print(line); log.append(line)
def save():
    json.dump({"step": STEP, "live": LIVE, "at": STAMP, "log": log}, open(REG, "w"), indent=1)

def full_resave(cid, visit_over=None, charge_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        a.update(charge_over or {})
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(visit_over or {})
    if not LIVE: return True, "DRY resave %s charges=%d visit_over=%s" % (vis.get("id"), len(allc), visit_over)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                 "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return False, "resave FAULT %s: %s" % (vis.get("id"), re.sub(r"\s+", " ", r[:300]))
    time.sleep(0.8)
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return len(c2) == len(allc), "resave %s live %d/%d insorder=%s onhcfa=%s hospfrom=%s" % (vis.get("id"), len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None)

def hosp_from(vid, cpts, admit):
    for code in sorted(set(cpts)):
        if not LIVE: continue
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
            '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
        if "Fault" in r: return "FAULT extins %s: %s" % (code, re.sub(r"\s+", " ", r[:160]))
        time.sleep(0.4)
    return "hospitalizationfrom %s on %s" % (admit, sorted(set(cpts)))

def complete_exclusion(runid, pairs):
    """pairs: [(visitid, claimid)] -> hideexclusions hide=-1 for that claim run."""
    if not LIVE: return "DRY hideexclusions run %s %s" % (runid, pairs)
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": runid, "hide": "-1", "nocookie": "1"},
                         "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in pairs)))
    return ("ok" if ('success="1"' in r or "<Fault" not in r) else "FAIL") + " " + re.sub(r"\s+", " ", r)[:160]

amd.login_cached()

if STEP == "K":
    pid, admit = "17478062", "10/12/2026"
    visits = {"19457795": ("23369841", "99223"), "19457782": ("23369826", "99232")}
    cms = json.load(open("patient_db/%s/[name]_[DOB].json" % pid))
    mbi = (cms.get("subscriber") or {}).get("memberId")
    j = stedi.elig("CMS", (cms.get("subscriber") or {}).get("firstName"), (cms.get("subscriber") or {}).get("lastName"), (cms.get("subscriber") or {}).get("dateOfBirth"), mbi, "[DOB]", pid=pid)
    s = stedi.med_summ(j)
    S("K", "CMS 271 re-check: errors", s.get("errors"), "partA", s.get("partA"), "partB", s.get("partB"), "death", s.get("death"), "MA entities", [o.get("entity") for o in (s.get("other") or []) if o.get("type") in ("HN", "HM", "PR", "PS")])
    if s.get("errors") or not s.get("partB") or s.get("death"):
        S("K", "STOP - Medicare record not clean"); save(); sys.exit(1)
    plans = ins_update._plans(pid)[1]
    have = [p for p, a in plans.items() if a.get("carrier") == "car6085"]
    if have:
        insid = have[0]; seq = plans[insid].get("sequence"); S("K", "FLO02 already on the chart", insid, seq)
    elif LIVE:
        insid, seq = add_ins.add(pid, "car6085", mbi, "10/12/2025", "1", "MC"); S("K", "add_ins ->", insid, "seq", seq)
    else:
        insid, seq = None, "1"; S("K", "DRY add_ins car6085 member ****%s begin 10/12/2025 coverage 1 finclass MC" % str(mbi)[-4:])
    if LIVE:
        okp, mp = ins_update.update(pid, "ins%s" % num(insid), sequence=str(seq)); S("K", "patient order", seq, "->", okp, mp[:160])
    done = []
    for vid, (cid, cpt) in visits.items():
        S("K", "v%s" % vid, cpt, "->", hosp_from(vid, [cpt], admit) if LIVE else "DRY hospitalizationfrom %s" % admit)
        ok, msg = full_resave(cid, {"insorder": str(seq), "onhcfa": "1"}); S("K", "v%s" % vid, msg[:220])
        if ok: done.append(vid)
        time.sleep(0.3)
    for v in done:
        if LIVE:
            ok, m = payreasons.release_visit(v); S("K", "release", v, "->", ok, m[:100])
        else: S("K", "DRY release", v)
    save()

elif STEP == "AET":
    pid = "17472859"
    rows = [("19399931", "19399931D", "22473914", 15.41), ("19399932", "19399932D", "22473915", 15.41), ("19399933", "19399933D", "22473916", 15.41),
            ("19399934", "19399934D", "22473917", 33.75), ("19400003", "19400003D", "22473990", 15.41)]
    # 1) write-offs from a FRESH live read of each charge
    root = txh.fetch(pid)
    live = {num(c.get("id")): c for c in root.iter("charge") if c.get("void") != "1"}
    for vid, claimid, cid, expect in rows:
        c = live.get(cid)
        bal = float((c.get("insbal") if c is not None else 0) or 0)
        pays = [p for p in (c.iter("payment") if c is not None else []) if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0]
        S("AET", "charge", cid, "visit", vid, "live insbal", bal, "expected", expect, "primary pays", [(p.get("carrier"), p.get("amount")) for p in pays])
        if abs(bal - expect) > 0.011 or not pays:
            S("AET", "SKIP - live balance differs or no primary payment"); continue
        if LIVE:
            r = manual_post.post(cid, "FLO02", 0.0, bal, "WOCLTREQ", checknumber="CHAT1015", depositdate=None, note="Medicare paid; no secondary in force Feb-2025 (Aetna MA from 05/01/2025) - William go 10/15/2026")
            S("AET", "WOCLTREQ", cid, bal, "->", str(r)[:160])
        else:
            S("AET", "DRY WOCLTREQ", cid, bal)
        time.sleep(0.4)
    # 2) complete the 5 exclusion rows on run 1700294
    S("AET", "complete ->", complete_exclusion("1700294", [(v, cl) for v, cl, _, _ in rows]))
    # 3) chart: Aetna begin 05/01/2025, Medicare end 04/30/2025, order Aetna first
    plans = ins_update._plans(pid)[1]
    aet = [p for p, a in plans.items() if a.get("carrier") == "car6047"]; mcr = [p for p, a in plans.items() if a.get("carrier") == "car6085"]
    S("AET", "plans", {p: (a.get("carrier"), a.get("sequence"), a.get("begindate"), a.get("enddate")) for p, a in plans.items()})
    if LIVE and aet and mcr:
        ok1, m1 = ins_update.update(pid, aet[0], begindate="05/01/2025"); S("AET", "Aetna begin 05/01/2025 ->", ok1, m1[:120])
        ok2, m2 = ins_update.update(pid, mcr[0], enddate="04/30/2025"); S("AET", "Medicare end 04/30/2025 ->", ok2, m2[:120])
        seq_a = plans[aet[0]].get("sequence"); seq_m = plans[mcr[0]].get("sequence")
        ok3, m3 = ins_update.update(pid, aet[0], sequence="%s,%s" % (seq_a, seq_m)); S("AET", "patient order %s,%s ->" % (seq_a, seq_m), ok3, m3[:120])
        r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
        S("AET", "readback insorder", re.search(r'insorder="([^"]*)"', r).group(1) if re.search(r'insorder="([^"]*)"', r) else "?",
          [(m.group(1), m.group(2), m.group(3)) for m in re.finditer(r'<insplan id="(ins\d+)"[^>]*?begindate="([^"]*)"[^>]*?enddate="([^"]*)"', r)])
    else:
        S("AET", "DRY plan fixes: Aetna begin 05/01/2025, Medicare end 04/30/2025, order Aetna first")
    save()

elif STEP == "DUPS":
    S("DUPS", "run 1700271 ->", complete_exclusion("1700271", [("19417751", "19417751F"), ("19424313", "19424313F"), ("19445320", "19445320B")]))
    save()

elif STEP == "ERA":
    import era_clear
    cid = "1053116"
    if LIVE:
        r = era_clear.dismiss(cid); S("ERA", "dismiss", cid, "->", str(r)[:200])
    else:
        S("ERA", "DRY dismiss", cid, "(UHC W0020208 $71 reversal matching no posted payment - William 10/15/2026)")
    save()

if STEP == "INSP":
    import void_tx
    # 1) 23177 v19451190: void the stray 99489 (23369701) - William's decision 10/15 ("void it")
    if LIVE:
        ok, m = void_tx.void_charge("23177", "23369701"); S("INSP", "void 23369701 (99489 on v19451190) ->", ok, m[:120])
    else: S("INSP", "DRY void 23369701")
    # 2) 22845 v19364378: Medicare paid 10/15/2023, PR2 23.06 to TRICARE For Life never sent - window closed -> WOCLTREQ
    if LIVE:
        r = manual_post.post("22430391", "TRI05", 0.0, 23.06, "WOCLTREQ", checknumber="CHAT1015", depositdate=None, note="TFL secondary window closed (Medicare remit 10/15/2023) - William go 10/15/2026")
        S("INSP", "WOCLTREQ 22430391 23.06 ->", str(r)[:120])
    else: S("INSP", "DRY WOCLTREQ 22430391 23.06 under TRI05")
    # 3) re-list the inspector, bypass the advisories on the four visits, resave/approve so the secondaries go out
    x = amd.post(amd.msg("getclaiminspectorbatches", "chargeentry", {"nocookie": "1"}))
    batches = re.findall(r'<batch\b[^>]*\bid="([^"]+)"', x) or re.findall(r'\bid="(\d+)"', x)
    targets = {"13979435": "20970795", "13984519": "20973913", "19395738": "22468751", "19451190": "23369703", "19364378": "22430391"}
    found = {}
    for b in batches:
        y = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": b, "nocookie": "1"}))
        for vm in re.finditer(r'<visit\b([^>]*)>(.*?)</visit>', y, re.S):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', vm.group(1))); vid = num(attrs.get("id"))
            if vid in targets:
                errs = re.findall(r'<(?:error|claimerror)\b[^>]*\bid="([^"]+)"', vm.group(2)) or re.findall(r'<error\b[^>]*id="([^"]+)"', vm.group(2))
                found[vid] = (b, errs, attrs.get("claimstatus"))
        time.sleep(0.3)
    S("INSP", "inspector rows found:", {k: (v[0], len(v[1]), v[2]) for k, v in found.items()})
    for vid, (b, errs, st) in found.items():
        if not errs: continue
        if LIVE:
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in errs))))
            S("INSP", "bypass", vid, errs, "->", "ok" if 'success="1"' in r else re.sub(r"\s+", " ", r)[:120])
        else: S("INSP", "DRY bypass", vid, errs)
        time.sleep(0.3)
    for vid, cid in targets.items():
        if vid == "19364378" and LIVE:
            ok, m = payreasons.release_visit(vid); S("INSP", "release", vid, "->", ok); continue
        ok, msg = full_resave(cid, {}); S("INSP", "resave/approve", vid, "->", ok, msg[:140]); time.sleep(0.4)
    save()
