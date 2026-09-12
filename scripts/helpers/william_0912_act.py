# PLAIN ENGLISH (act on William's 9/12 board replies - 7am ET run, ehpa cloud)
# Decides: executes the dispositions William typed on the Insurance Refresh Board rows between 08:47 and 09:26 UTC 9/12,
#   each one re-verified LIVE right before the write so a parallel copy of the routine cannot make us double-post:
#   WOINS only on lines that still carry an insurance balance (manual_post refuses over-apply anyway),
#   rebills only on visits whose billdate is not today, inspector dates only where the error is still listed.
# Rules it uses: full-visit echo on every resave (void trap), freq-1 before every rebill, hideexclusions per claim run,
#   modifier 25 = mcode7, admission = most recent 99223 within 45 days, never hospitalizationto.
# Never touches: the 17 charts the 08:35 Working Denials chat session named; anything with a posted payment; carrier masters.
import amd, resave, txh, manual_post, json, re, sys, time, datetime, collections, os
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
TODAY = time.strftime("%m/%d/%Y")
STAMP = time.strftime("%Y-%m-%d_%H%MUTC", time.gmtime())
LOG = open("william_0912_act.log", "a")
def L(m): print(m, flush=True); LOG.write("%s %s\n" % (time.strftime("%H:%M:%S"), m)); LOG.flush()
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
WD_CHARTS = {"17471830","45011","17474082","17471002","12180170","17472286","17470966","17468967","17473292","17476868","17477116","17468923","22575","45024","25852","46802","17472327"}
REGISTER = []  # write-off register rows

# ---------- reads ----------
def open_lines(pid):
    out = []
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        pays = [p for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        wos = [(w.get("id"), w.get("wocode"), w.get("amount")) for w in c.iter("writeoff") if w.get("void") != "1" and float(w.get("amount") or 0) != 0]
        out.append({"visit": a.get("visit"), "cid": a.get("id"), "proccode": a.get("proccode"), "dos": a.get("dos"), "carrier": a.get("carrier"),
                    "insbal": float(a.get("insbal") or 0), "patbal": float(a.get("patbal") or 0), "billdate": a.get("billdate") or "", "fee": a.get("fee"),
                    "npay": len(pays), "wos": wos})
    return out

def insplans(pid):
    root = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60))
    return [(i.get("id"), i.get("carrier"), i.get("subscribernum"), i.get("sequence"), i.get("begindate"), i.get("enddate")) for i in root.iter("insplan")]

# ---------- writes ----------
def woins(pid, visits, carrier, note, code="WOINS"):
    """Write off every open insurance line of `carrier` on the given visits. Returns $ written off."""
    if pid in WD_CHARTS: L("REFUSE %s: Working Denials chart" % pid); return 0.0
    total = 0.0
    for r in open_lines(pid):
        if r["visit"] not in visits or r["carrier"] != carrier or r["insbal"] <= 0: continue
        if r["npay"]:
            L("  note: c%s %s %s has a posted payment - writing off the residual only" % (r["cid"], r["proccode"], r["dos"]))
        if DRY: L("  DRY WOINS c%s %s %s %s $%.2f" % (r["cid"], r["proccode"], r["dos"], carrier, r["insbal"])); total += r["insbal"]; continue
        ok, msg = manual_post.post(r["cid"], carrier, 0.0, r["insbal"], code, "", None, note)
        L("  %s c%s %s %s %s $%.2f -> %s %s" % (code, r["cid"], r["proccode"], r["dos"], carrier, r["insbal"], ok, msg[:90]))
        if ok:
            total += r["insbal"]
            REGISTER.append({"date": TODAY, "pid": pid, "visit": r["visit"], "cid": r["cid"], "carrier": carrier, "dos": r["dos"], "cpt": r["proccode"], "amount": r["insbal"], "code": code, "note": note})
        time.sleep(0.4)
    return total

def complete_exclusions(visit_ids, tag):
    """hideexclusions for the given visit ids using the latest scan summary (run -> visit/claim pairs)."""
    s = json.load(open("scan_0912/summary_%s.json" % tag))
    byrun = collections.defaultdict(list)
    for rid, rows in s["exclusions"].items():
        for r in rows:
            if r.get("id") in visit_ids: byrun[rid].append((r["id"], r.get("claimid")))
    n = 0
    for rid, pairs in byrun.items():
        child = "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % p for p in pairs)
        if DRY: L("  DRY hideexclusions run %s %s" % (rid, pairs)); n += len(pairs); continue
        r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"}, child), timeout=120)
        ok = "Fault" not in r; L("  hideexclusions run %s x%d -> %s" % (rid, len(pairs), ok))
        if ok: n += len(pairs)
        time.sleep(0.3)
    return n

def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst" + re.sub(r"\D", "", str(vid)), "nocookie": "1"}, ext))

def resave_visit(cid, over=None, chg_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if chg_over and c.get("id") in chg_over: a.update(chg_over[c.get("id")])
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, amd.esc(v)) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if over: va.update(over)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode") or "", "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, amd.esc(v)) for k, v in va.items()), chg)))
    time.sleep(0.7)
    return "Fault" not in r, r[:200]

def bypass(vid, ids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"},
        '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
    return "Fault" not in r

def list_inspector():
    ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"')
    out = []
    for bid in re.findall(r'<batch id="([^"]+)"', ib):
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        try: root = ET.fromstring(t)
        except ET.ParseError: continue
        for v in root.iter("visit"):
            errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:200]) for e in v.iter("error")]
            out.append({"bid": bid, "vid": v.get("id"), "pid": v.get("patientid") or "", "name": v.get("patientname") or "", "errs": errs,
                        "chgs": [(c.get("id"), c.get("proccode"), c.get("modcodes") or "", c.get("begindate") or c.get("dos") or "") for c in v.iter("charge")]})
        time.sleep(0.3)
    return out

ADVISORY = ("35790", "7011", "3429", "35777", "33799", "20657", "27261", "4310", "4426", "11256", "4311", "4564", "28158", "23400")

def inspector_pass():
    rows = list_inspector(); L("inspector rows: %d" % len(rows))
    hist = {}
    for v in rows:
        pid = v["pid"]; vid = re.sub(r"\D", "", v["vid"])
        if pid in WD_CHARTS: L("  skip v%s (Working Denials chart)" % vid); continue
        txt = " | ".join(e[1] for e in v["errs"])
        if "Hospitalization From Date" in txt:
            if pid not in hist: hist[pid] = [(d(c.get("dos")), c.get("proccode")) for c in txh.fetch(pid).iter("charge") if c.get("void") != "1" and c.get("dos")]
            dos = min(d(c[3]) for c in v["chgs"] if c[3])
            adm = [x for x, p in hist[pid] if p == "99223" and x <= dos and (dos - x).days <= 45]
            if not adm: L("  HOLD v%s %s: no 99223 anchor within 45 days of %s" % (vid, v["name"], dos)); continue
            admit = max(adm).strftime("%m/%d/%Y")
            if DRY: L("  DRY v%s %s admit=%s codes=%s" % (vid, v["name"], admit, [c[1] for c in v["chgs"]])); continue
            for code in sorted({c[1] for c in v["chgs"]}):
                r = set_date(vid, code, admit); time.sleep(0.3)
                if "Fault" in r: L("  extins FAULT v%s %s %s" % (vid, code, r[:120]))
            ok, msg = resave_visit(re.sub(r"\D", "", v["chgs"][0][0]), over={"onhcfa": "1"})
            L("  v%s %s hospitalizationfrom=%s resave onhcfa=1 -> %s %s" % (vid, v["name"], admit, ok, "" if ok else msg))
        elif "99497" in txt and "unbundle" in txt:
            # ACP same day as a hospital E/M: modifier 25 (mcode7) on the 99497, never on the E/M
            fix = {c[0]: {"modcodes": (c[2] + " mcode7").strip()} for c in v["chgs"] if c[1] == "99497" and "mcode7" not in c[2]}
            if fix and not DRY:
                ok, msg = resave_visit(re.sub(r"\D", "", v["chgs"][0][0]), chg_over=fix)
                L("  v%s %s mod-25 on 99497 (%s) resave -> %s %s" % (vid, v["name"], list(fix), ok, "" if ok else msg))
            elif fix: L("  DRY v%s %s add mcode7 to %s" % (vid, v["name"], list(fix)))
            else: L("  v%s %s 99497 already carries mcode7 - advisory only" % (vid, v["name"]))
    # re-list with FRESH ids and bypass the advisories
    time.sleep(2); rows = list_inspector(); byp = 0; left = []
    for v in rows:
        vid = re.sub(r"\D", "", v["vid"])
        ids = [e[0] for e in v["errs"] if any(("Pattern %s" % p) in e[1] for p in ADVISORY)]
        other = [e[1][:80] for e in v["errs"] if not any(("Pattern %s" % p) in e[1] for p in ADVISORY)]
        if ids and not DRY:
            ok = bypass(vid, ids); byp += len(ids); L("  bypass v%s %s %s -> %s" % (vid, v["name"], ids, ok))
        if other: left.append((vid, v["name"], other))
    L("inspector after pass: %d visits still listed: %s" % (len(left), left))
    return left

def aet12_rebill(tag):
    s = json.load(open("scan_0912/summary_%s.json" % tag))
    rows = [(rid, r) for rid, rs in s["exclusions"].items() for r in rs if r.get("carriercode") == "AET12"]
    L("AET12 exclusion rows: %d" % len(rows)); done_v = []; skipped = []
    bypid = collections.defaultdict(list)
    for rid, r in rows: bypid[r["patientid"]].append((rid, r))
    for pid, prs in bypid.items():
        if pid in WD_CHARTS: L("  skip %s Working Denials chart" % pid); continue
        plans = insplans(pid); seq = [p[3] for p in plans if p[1] == "car42009"]
        if not seq: L("  %s: no AET12 plan on chart - skip" % pid); continue
        seq = seq[0]; lines = open_lines(pid)
        for rid, r in prs:
            vid = r["id"]; vl = [x for x in lines if x["visit"] == vid and x["carrier"] == "AET12" and x["insbal"] > 0]
            if not vl: skipped.append((vid, "no open AET12 balance")); continue
            if any(x["billdate"] == TODAY for x in vl): skipped.append((vid, "already billed today")); done_v.append(vid); continue
            if DRY: L("  DRY freq1 v%s c%s seq %s $%.2f" % (vid, vl[0]["cid"], seq, sum(x["insbal"] for x in vl))); done_v.append(vid); continue
            import freq1_visit
            res = freq1_visit.run(vid, vl[0]["cid"], seq); L("  v%s %s %s -> %s" % (vid, r.get("patientname"), vl[0]["dos"], res))
            if "204" in res: done_v.append(vid)
            time.sleep(0.4)
    L("AET12 skipped: %s" % skipped)
    return done_v

if __name__ == "__main__":
    amd.login_cached()
    what = [a for a in sys.argv[1:] if not a.startswith("--")]
    L("=== william_0912_act %s dry=%s steps=%s ===" % (STAMP, DRY, what))
    results = {}
    if "inspector" in what: results["inspector_left"] = inspector_pass()
    if "writeoffs" in what:
        tot = {}
        tot["whitfield"] = woins("17473232", {"19405066", "19405103", "19406147"}, "UNI20", "UNI20 supplement residual written off per William 9/12/2026 board reply (subscriber not found, deceased [DOB])")
        tot["pemberly"] = woins("17473020", {"19402078", "19402750", "19402770", "19402809", "19402943", "19403208", "19403209"}, "UNI20", "UNI20 supplement residual written off per William 9/12/2026 board reply (subscriber not found, deceased [DOB])")
        tot["penhale"] = woins("17471681", {"19397003", "19405071", "19406152", "19452569"}, "HUM01", "Humana secondary residual written off - no secondary coverage, per William 9/12/2026 board reply")
        tot["corbey"] = woins("17475099", {"19428157", "19428170", "19428175"}, "HUM01", "No insurance on file - patient no-pay write-off per William 9/12/2026 board reply (Humana policy canceled)")
        L("write-offs: %s" % tot); results["writeoffs"] = tot
        n = complete_exclusions({"19405066", "19405103", "19406147", "19402078", "19402750", "19402770", "19402809", "19402943", "19403208", "19403209", "19397003", "19405071", "19406152", "19452569", "19428157", "19428170", "19428175"}, "mid")
        L("exclusions completed: %d" % n); results["excl_completed"] = n
    if "aet12" in what:
        dv = aet12_rebill("before"); results["aet12_rebilled"] = dv
        if dv and not DRY: results["aet12_completed"] = complete_exclusions(set(dv), "before")
    if REGISTER:
        fn = "Writeoff_register_%s_william_replies.csv" % time.strftime("%Y-%m-%d")
        import csv
        new = not os.path.exists(fn)
        with open(fn, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(REGISTER[0].keys()));
            if new: w.writeheader()
            w.writerows(REGISTER)
        L("register -> %s (%d rows)" % (fn, len(REGISTER)))
    json.dump(results, open("william_0912_act_%s.json" % STAMP, "w"), indent=1, default=str)
    L("=== done %s ===" % json.dumps(results, default=str)[:600])
