# PLAIN ENGLISH (2:40 AM ET 10/28 slot, second pass): (A2) the three hospital visits whose admission date is already on the visit
#   still show the stale 'Hospitalization From Date is empty' inspector error - a full-visit resave (every live charge echoed,
#   onhcfa=1, inspectorenabled=1) makes AMD re-inspect them. (B2) pat17476680 v19458871 (99309) + v19458913 (CCM 99487+99489):
#   Z16.12 (resistance to ESBL - secondary-only Z code) in the primary slot -> William's cascade via dx_primary_fix.plan /
#   save_visit_dx (CCM keeps at least two codes). (C2) pat17477225 v19458864: 99309 at POS 21 -> HOLD for William, same as pat25994.
#   No rebill (never claimed). --live writes; default dry. Register registers/act2_2026-10-28T0640Z[_dry].json.
import amd, resave, re, json, sys, time, datetime
import xml.etree.ElementTree as ET
import dx_primary_fix as dpf
DRY = "--live" not in sys.argv; STAMP = "2026-10-28T0640Z"
amd.login_cached(); out = {"stamp": STAMP, "dry": DRY, "steps": [], "hold": [], "done": []}
def L(m): print(m, flush=True); out["steps"].append(m)
A2 = [("17476869", "19458733", "23370953"), ("17478059", "19458794", "23371014"), ("24560", "19458830", "23371055")]
B2 = [("17476680", "19458871", None), ("17476680", "19458913", None)]
C2 = [("17477225", "19458864", None)]
S = json.load(open("scan_2026-10-28T0652Z/summary_post.json"))
CH = {v["vid"]: [c[0] for c in v["chgs"]] for b, vs in S["inspector"].items() for v in vs}
def full_resave(cid, over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    if DRY: return True, "DRY resave visit %s over=%s charges=%d" % (vis.get("id"), over, len(allc))
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    ok = "Fault" not in r and len(c2) == len(allc)
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if "Fault" in r else "saved live=%d/%d onhcfa=%s insorder=%s hospfrom=%s" % (len(c2), len(allc), v2.get("onhcfa"), v2.get("insorder"), ex.get("hospitalizationfrom") if ex is not None else None)
for pid, vid, cid in A2:
    vis, pat, allc = resave.visit_charges(cid); ex = vis.find("extins"); have = ex.get("hospitalizationfrom") if ex is not None else None
    if not have: L("A2 v%s: no admission date on the visit after all - HOLD" % vid); out["hold"].append({"pid": pid, "vid": vid, "why": "admission date missing"}); continue
    ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": vis.get("insorder")}); L("A2 pat%s v%s admission %s re-inspect resave: %s" % (pid, vid, have, msg))
    (out["done"] if ok else out["hold"]).append({"pid": pid, "vid": vid, "action" if ok else "why": ("resave onhcfa=1 with admission %s" % have) if ok else msg}); time.sleep(0.4)
for pid, vid, _ in B2:
    cids = CH.get(vid) or []
    if not cids: L("B2 v%s: no charge id in the scan" % vid); continue
    cid = cids[0]
    if any(s["pays"] for s in dpf.live_state(pid, vid)): L("B2 v%s SKIP - payment posted" % vid); continue
    vis, pat, allc, m = dpf.visit_dx(cid); inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dpf.I10_DCODE)
    plans = {}; acts = set(); after = None
    for c in allc:
        codes = [m.get(d, d) for d in (c.get("diagcodes") or "").split()]; cpt = None
        for pc in ET.fromstring(resave.detail(c.get("id").replace("charge", ""))).iter("proccode"):
            if pc.get("id") == c.get("proccode"): cpt = pc.get("code")
        act, new = dpf.plan(codes, cpt); acts.add(act)
        L("B2 pat%s v%s %s %s dx %s -> %s (%s)" % (pid, vid, c.get("id"), cpt, codes, new, act))
        if act != "ok": plans[c.get("id")] = [inv[x] for x in new]; after = new
    if not plans: out["done"].append({"pid": pid, "vid": vid, "action": "primary dx already acceptable"}); continue
    r, det = dpf.save_visit_dx(cid, plans, dry=DRY); L("  " + r)
    if DRY: continue
    ok = not r.startswith("FAULT") and all(det.get(k, (None, None))[1] == v for k, v in plans.items())
    (out["done"] if ok else out["hold"]).append({"pid": pid, "vid": vid, "action" if ok else "why": ("%s -> %s" % ("/".join(sorted(acts)), after)) if ok else r})
    if ok:
        import os; reg = json.load(open(dpf.REGISTER)) if os.path.exists(dpf.REGISTER) else []
        reg.append({"pid": pid, "vid": vid, "cid": cid, "action": "/".join(sorted(acts)), "dx_after": after, "rebill": "none - unbilled visit, inspector release", "when": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z", "run": STAMP}); json.dump(reg, open(dpf.REGISTER, "w"), indent=1)
    time.sleep(0.4)
for pid, vid, _ in C2:
    cid = (CH.get(vid) or [None])[0]
    if not cid: continue
    vis, pat, allc = resave.visit_charges(cid); x = resave.detail(cid); pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x))
    cp = [pm.get(c.get("proccode"), c.get("proccode")) for c in allc]
    L("C2 pat%s v%s dos %s cpt %s facility %s pos %s insorder %s - 99309 at POS 21: HOLD for William" % (pid, vid, allc[0].get("begindate"), cp, vis.get("facility"), allc[0].get("pos"), vis.get("insorder")))
    out["hold"].append({"pid": pid, "vid": vid, "dos": allc[0].get("begindate"), "cpt": cp, "facility": vis.get("facility"), "pos": allc[0].get("pos"), "why": "99309 at POS 21 (Pattern 4531 + hospitalization date) - POS/CPT decision for William"})
json.dump(out, open("registers/act2_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1, default=str)
L("=== done (dry=%s) done=%d hold=%d ===" % (DRY, len(out["done"]), len(out["hold"])))
