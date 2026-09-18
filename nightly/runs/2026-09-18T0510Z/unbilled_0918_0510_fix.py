# PLAIN ENGLISH (Unbilled column pass, 1 AM ET 9/18/2026 slot - ehpa cloud run 2026-09-18T0510Z)
# Decides, per William's standing rules and the lookup cascade already run this run (AMD chart -> Stedi MBI lookup with the
#   chart SSN -> payer eligibility -> discovery; registers/newcharts_stedi*_<stamp>.json):
#   (a) 'Insurance order is missing' charts: add the plan the cascade proved (add_ins.add, NO group numbers), run the free AMD 271
#       on it, PRIMARY-DX GATE (dx_primary_fix.plan / save_visit_dx before anything is approved), write the admission date
#       (updextrainsinfo hospitalizationfrom ONLY, anchor = the stay's 99223), full-visit resave with insorder + onhcfa=1
#       (charge echo - void trap), move a blank address line 1 up from line 2, then release. Charts the cascade could not
#       settle keep their visits in Unbilled (board row on William's turn) - only the address fix is done for them.
#   (c) 'prior payor' rows: primary sent and unanswered (or paid inside the secondary window) -> release (9/8 rule).
# Never touches: the 11 'payment reason codes' rows (HELD per the 9/15 chat rule), the WEXFORD 'Bill Insurance = No' row (William's),
#   group numbers, hospitalizationto, any payment-posted visit.
"""Usage: python3 unbilled_0918_0510_fix.py [--dry] [--only a,c]"""
import amd, resave, add_ins, elig_amd, addr_line1_fix, dx_primary_fix, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
S = "2026-09-18T0510Z"
dry = "--dry" in sys.argv
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["a", "c"]
amd.login_cached()
LOG = open("unbilled_0918_0510_fix.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
SC = json.load(open("scan_0912/summary_before.json"))
rows = {r["id"]: r for r in SC["unbilled"]}
V = json.load(open("registers/unbilled_verify_%s.json" % S))
REG = {"stamp": S, "dry": dry, "charts": {}, "released": [], "held": []}
REL = []
L("=== unbilled fix %s %s dry=%s only=%s ===" % (S, datetime.datetime.utcnow().isoformat(), dry, only))

def set_admit(vid, code, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" '
           'employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit))
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, ext))
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:160])

def resave_full(cid, insorder=None, onhcfa="1"):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if onhcfa: va["onhcfa"] = onhcfa
    if insorder: va["insorder"] = str(insorder)
    if dry: return "DRY resave %d charges insorder %s->%s" % (len(allc), vis.get("insorder"), va.get("insorder"))
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.6)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    v2, p2, c2 = resave.visit_charges(cid)
    return "ok insorder=%s onhcfa=%s live %d (was %d)" % (v2.get("insorder"), v2.get("onhcfa"), len(c2), len(allc))

def dx_gate(cid):
    """William's primary-dx cascade before approval. Returns a result string."""
    vis, pat, allc, m = dx_primary_fix.visit_dx(cid)
    inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dx_primary_fix.I10_DCODE)
    new = {}; notes = []
    for c in allc:
        dcodes = (c.get("diagcodes") or "").split(); codes = [m.get(d, d) for d in dcodes]
        act, nc = dx_primary_fix.plan(codes, c.get("proccode"))
        notes.append("%s %s dx %s -> %s" % (c.get("id"), c.get("proccode"), codes, act))
        if act != "ok":
            new[c.get("id")] = [inv[x] if x in inv else x for x in nc]
    if not new: return "dx ok: " + "; ".join(notes)
    if dry: return "DRY dx fix: " + "; ".join(notes)
    msg, det = dx_primary_fix.save_visit_dx(cid, new, dry=False)
    return "DX FIX %s -> %s" % ("; ".join(notes), msg)

def plans(pid):
    x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60)
    return [dict(i.attrib) for i in ET.fromstring(x).iter("insplan")]
def seq_of(pid, carrier):
    for p in plans(pid):
        if p.get("carrier") == carrier and not p.get("enddate"): return p.get("sequence"), p.get("id")
    return None, None

A = json.load(open("secrets/unbilled_0918_0510_cfg.json"))   # per-chart plan/admission/address config (member numbers) - secrets/, never leaves the workspace
if "a" in only:
    for pid, cfg in A.items():
        rec = {"name": cfg["name"], "added": [], "elig": [], "visits": {}, "addr": None, "hold": False}
        L("--- %s pat%s ---" % (cfg["name"], pid))
        for car, num, bd in cfg["add"]:
            s, insid = seq_of(pid, car)
            if s: L("  plan %s already on file seq %s (%s)" % (car, s, insid)); rec["added"].append([car, insid, s, "already"]); continue
            if dry: L("  DRY add %s begin %s" % (car, bd)); continue
            insid, s = add_ins.add(pid, car, num, bd); L("  add %s begin %s -> %s seq %s" % (car, bd, insid, s)); rec["added"].append([car, insid, s, "new"]); time.sleep(0.5)
            if insid and str(insid).startswith("ins"):
                try:
                    e = elig_amd.run_plan(pid, insid.replace("ins", ""), True); line = elig_amd.one_line(e)[:300]; L("  AMD 271 %s: %s" % (car, line)); rec["elig"].append([car, line])
                except Exception as ex: L("  AMD 271 ERR %s" % str(ex)[:120]); rec["elig"].append([car, "ERR " + str(ex)[:120]])
        if cfg["addr"]:
            try:
                msg, det = addr_line1_fix.fix(pid, *cfg["addr"], dry=dry); L("  addr: %s %s" % (msg, json.dumps(det)[:200])); rec["addr"] = msg
            except Exception as ex: L("  addr ERR %s" % str(ex)[:150]); rec["addr"] = "ERR " + str(ex)[:150]
        vids = [r["id"] for r in SC["unbilled"] if r["patientid"] == pid and "Insurance order" in r["_errs"][0]]
        if not cfg["bill"]:
            L("  cascade found no billable payer -> HOLD %s (board row on William's turn)" % vids); rec["hold"] = True; REG["held"] += vids; REG["charts"][pid] = rec; continue
        seq, insid = seq_of(pid, cfg["bill"])
        if not seq and not dry: L("  NO open %s plan on chart -> HOLD" % cfg["bill"]); rec["hold"] = True; REG["held"] += vids; REG["charts"][pid] = rec; continue
        L("  bill seq %s (%s %s)" % (seq, cfg["bill"], insid))
        for vid in vids:
            r = rows[vid]; cid = r["_chgs"][0]["id"]; codes = sorted({c["chgcode"] for c in r["_chgs"]}); vr = {}
            try: vr["dx"] = dx_gate(cid); L("  v%s %s" % (vid, vr["dx"][:300]))
            except Exception as ex: vr["dx"] = "DX ERR " + str(ex)[:150]; L("  v%s dx gate ERR %s" % (vid, str(ex)[:150]))
            adm = cfg["admit"].get(vid)
            if adm and not dry:
                for code in codes: res = set_admit(vid, code, adm); L("  v%s admit %s %s -> %s" % (vid, code, adm, res)); vr["admit_%s" % code] = res; time.sleep(0.3)
            elif adm: L("  DRY v%s admit %s" % (vid, adm))
            vr["resave"] = resave_full(cid, insorder=seq); L("  v%s resave -> %s" % (vid, vr["resave"]))
            if vr["resave"].startswith("ok") or dry: REL.append(vid)
            rec["visits"][vid] = vr; time.sleep(0.4)
        REG["charts"][pid] = rec

if "c" in only:
    pp = [vid for vid, d in V.items()]   # every verified prior-payor row: release-b, plus Garrow (Medicaid paid 115 days ago = window open)
    L("--- (c) prior-payor rows to release: %d (classes %s) ---" % (len(pp), {k: sum(1 for d in V.values() if d['class'] == k) for k in {d['class'] for d in V.values()}}))
    REL += pp

REL = list(dict.fromkeys(REL))
L("release %d visits" % len(REL))
if REL and not dry:
    for i in range(0, len(REL), 40):
        chunk = REL[i:i + 40]
        r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in chunk)), timeout=120)
        ok = "Fault" not in r; L("  hideunbillablevisits %d -> %s" % (len(chunk), "ok" if ok else "FAULT " + re.sub(r"\s+", " ", r[:200])))
        REG["released"].append({"visits": chunk, "ok": ok}); time.sleep(0.5)
    t = amd.post(amd.msg("getclaimunbillablecharges", "claimsreports", {"lowdate": "", "highdate": "", "carrier": "", "provider": "", "nocookie": "1"}), timeout=180)
    L("Unbilled after: totalcount=%s" % (re.search(r'totalcount="([^"]*)"', t).group(1) if re.search(r'totalcount="([^"]*)"', t) else "?"))
json.dump(REG, open("registers/unbilled_fix_%s%s.json" % (S, "_dry" if dry else ""), "w"), indent=1)
