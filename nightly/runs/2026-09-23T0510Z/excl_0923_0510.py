# PLAIN ENGLISH (Exclusions pass, 1am ET 9/23/2026 run 2026-09-23T0510Z): three new claim runs (1700227/1700228/1700229, AMD clock
#   9/22 21:06) rejected 125 claim lines - 118 'CH 72 PDTP0303: MISSING RELATED ADMISSION DATE' (hospital visits, facility fac29 / POS 21,
#   whose extins record no longer carries hospitalizationfrom - the secondary claims AMD queued after the 9/22 chat session's ERA-linked
#   payment posts went out without an admission date), 5 charge lines of 2 Florida Blue secondaries 'PREF0283 MISSING PAYER DOC CONTROL NUM'.
# Decides, per visit: (a) every charge already at $0 insurance balance -> complete the exclusion, nothing re-sent; (b) PREF0283 Florida Blue
#   secondaries -> complete per the crossover-wait rule (9/20 lesson: neither freq 7 + ICN nor freq 1 clears it); (c) PDTP0303 -> admission
#   date = the visit's own 99223, else the most recent 99223 on/before the DOS within 45 days (gettxhistory, paged), else an earlier visit
#   of the same stay that already carries the date; written with updextrainsinfo (existing extins attributes echoed + hospitalizationfrom,
#   resubmissioncode 1, no 1900 dates) per CPT, then chargerebill on the sequence the claim was last billed to (the excluded carrier),
#   readback verified, exclusion completed; no anchor -> HOLD (pat17472874's April stay stays on William's board row). No full-visit resave
#   (many of these visits carry posted payments - the void trap); deceased guard runs on every rebill (amd.rebill_charge).
# Never touches: payments, write-offs, insurance plans, hospitalizationto, visits outside the exclusion lists.
"""Usage: python3 excl_0923_0510.py [--dry] [--only vid,vid] [--max N]"""
import amd, resave, deceased_guard, re, time, json, sys, datetime, collections
DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
MAX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
STAMP = "2026-09-23T0510Z"
HOLD_PIDS = {"17472874"}          # Thackeray K: April-2026 stay, no 99223 anchor, William's turn (board row)
amd.login_cached()
rows = json.load(open("excl_rows_0510.json"))
byvisit = collections.OrderedDict()
for r in rows: byvisit.setdefault((r["run"], r["vid"], r["claimid"]), []).append(r)
out = {"stamp": STAMP, "dry": DRY, "fixed": [], "completed_zero": [], "completed_pref0283": [], "held": [], "faults": []}
def L(m): print(m, flush=True)
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
hist = {}
def history(pid):
    if pid in hist: return hist[pid]
    rows_ = []
    for page in (1, 2, 3, 4):
        t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": str(page), "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
        n = 0
        for m in re.finditer(r'<charge [^>]*/?>', t):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))); n += 1
            if a.get("void") == "1" or (a.get("fee") or "").startswith("-") or not a.get("dos"): continue
            rows_.append((d(a["dos"]), a.get("proccode"), a.get("visit"), a.get("id")))
        time.sleep(0.3)
        if n < 50: break
    hist[pid] = rows_; return rows_
def admit_for(pid, dos, own_cpts):
    if "99223" in own_cpts: return dos, "own 99223"
    adm = [x for x, p, v, c in history(pid) if p == "99223" and x <= dos and (dos - x).days <= 45]
    if adm: return max(adm), "most recent 99223 within 45d"
    HOSP = ("99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239", "99291")
    prev = sorted([(x, v, c) for x, p, v, c in history(pid) if p in HOSP and x < dos and (dos - x).days <= 45], reverse=True)
    for x, v, c in prev[:3]:
        try: vv, pp, cc = resave.visit_charges(c.replace("charge", ""))
        except Exception: continue
        ex = vv.find("extins"); hf = ex.get("hospitalizationfrom") if ex is not None else None
        if hf and (dos - d(hf)).days <= 60: return d(hf), "same stay: admission %s already on visit %s (%s)" % (hf, v, x)
    return None, "no 99223 anchor within 45 days and no earlier visit of the stay carries an admission date"
def write_date(vid, vis, cpts, adm):
    e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
    base.update({"resubmissioncode": "1", "origrefnum": "", "hospitalizationfrom": adm})
    for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
    base = resave.clean_extins(base); res = []
    for pc in cpts:
        base["txtChargeCode"] = pc
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in base.items())))
        res.append((pc, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])))
    return res
n = 0
for (run, vid, claimid), rs in byvisit.items():
    if ONLY and vid not in ONLY: continue
    if n >= MAX: break
    n += 1
    pid, car, err = rs[0]["pid"], rs[0]["car"], rs[0]["err"]
    rec = {"run": run, "vid": vid, "claimid": claimid, "pid": pid, "car": car, "err": err[:60], "steps": []}
    def S(m): L("run %s v%s pat%s %s: %s" % (run, vid, pid, car, m)); rec["steps"].append(m)
    try:
        vis, pat, allc = resave.visit_charges(rs[0]["cid"])
    except Exception as e:
        S("visit_charges failed: %s" % e); out["faults"].append(rec); continue
    live = [c for c in allc if c.get("void") != "1"]
    if not live: S("no live charges"); out["held"].append(rec); continue
    cptmap = {}
    for c in live:
        det = resave.detail(c.get("id").replace("charge", ""))
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', det))
        cptmap[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    cpts = sorted(set(cptmap.values()))
    dos = d(live[0].get("begindate") or vis.get("date"))
    bal = sum(float(c.get("insbalance") or 0) for c in live)
    seq = live[0].get("lastbilledcarrier") or (vis.get("insorder") or "1").split(",")[0]
    S("dos %s cpts %s insbal %.2f onhcfa %s insorder %s lastbilledseq %s ex=%s" % (dos, cpts, bal, vis.get("onhcfa"), vis.get("insorder"), seq, (vis.find("extins").get("hospitalizationfrom") if vis.find("extins") is not None else None)))
    if bal <= 0.005:
        S("insurance balance $0 -> complete only"); rec["amount"] = 0; out["completed_zero"].append(rec); continue
    rec["amount"] = round(bal, 2)
    if "PREF0283" in err:
        S("Florida Blue secondary PREF0283 -> complete per the crossover-wait rule, not re-sent"); out["completed_pref0283"].append(rec); continue
    if pid in HOLD_PIDS:
        S("HOLD: chart on the standing hold (no admission anchor, William's turn)"); out["held"].append(rec); continue
    admit, why = admit_for(pid, dos, cpts)
    if not admit: S("HOLD: %s" % why); out["held"].append(rec); continue
    adm = admit.strftime("%m/%d/%Y"); S("admission %s (%s)" % (adm, why)); rec["admission"] = adm
    if DRY: S("DRY: would write hospitalizationfrom %s on %s and rebill seq %s" % (adm, cpts, seq)); out["fixed"].append(rec); continue
    res = write_date(vid, vis, cpts, adm); S("updextrainsinfo %s" % res)
    if any(x[1] != "ok" for x in res): out["faults"].append(rec); continue
    time.sleep(0.5)
    code, msg = amd.rebill_charge(rs[0]["cid"], int(seq)); S("chargerebill seq %s -> %s %s" % (seq, code, (msg or "")[:120]))
    if code != 204: out["faults"].append(rec); continue
    time.sleep(0.5)
    v2, p2, c2 = resave.visit_charges(rs[0]["cid"]); ex2 = v2.find("extins")
    S("readback hospfrom=%s insbilled=%s" % (ex2.get("hospitalizationfrom") if ex2 is not None else None, [c.get("insbilled") for c in c2]))
    if ex2 is None or not ex2.get("hospitalizationfrom"): out["faults"].append(rec); continue
    out["fixed"].append(rec); time.sleep(0.3)
json.dump(out, open("registers/excl_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("SUMMARY: fixed %d, completed_zero %d, completed_pref0283 %d, held %d, faults %d" % (len(out["fixed"]), len(out["completed_zero"]), len(out["completed_pref0283"]), len(out["held"]), len(out["faults"])))
if DRY: sys.exit()
# complete the exclusions (fixed + $0 + PREF0283) per claim run
byrun = collections.defaultdict(list)
for rec in out["fixed"] + out["completed_zero"] + out["completed_pref0283"]: byrun[rec["run"]].append((rec["vid"], rec["claimid"]))
for rid, lst in byrun.items():
    lst = sorted(set(lst))
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in lst)))
    L("hideexclusions run %s x%d -> %s" % (rid, len(lst), "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200]))); time.sleep(0.4)
    out.setdefault("completed_calls", []).append({"run": rid, "n": len(lst), "ok": "Fault" not in r})
json.dump(out, open("registers/excl_%s.json" % STAMP, "w"), indent=1)
L("DONE")
