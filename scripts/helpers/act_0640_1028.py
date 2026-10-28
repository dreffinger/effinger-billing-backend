# PLAIN ENGLISH (2:40 AM ET 10/28 slot, run 2026-10-28T0640Z - ehpa cloud copy): Claim Inspector holds from the Claimocity
#   batch that landed mid-run (visits 19458733-19458845).
#   A: admission-date holds (Pattern 117065068) on hospital visits (POS 21): admission = the visit's own 99223 DOS, else the most
#      recent 99223 on/before the DOS within 45 days (gettxhistory); updextrainsinfo hospitalizationfrom ONLY (never hospitalizationto);
#      full-visit resave onhcfa=1. Skipped when the date is already on the visit. No anchor = HOLD, reported.
#   B: never-primary first diagnosis (Pattern 20389: Z63.4 secondary-only Z code; W19.XXXA external cause) -> William's 9/14 cascade
#      via dx_primary_fix.plan (delete the code when an acceptable code remains, else move it last, else add I10) + save_visit_dx
#      (full-visit echo). No rebill: these visits have never been claimed - the inspector releases them on its own.
#   C: pat25994 v19458784 / v19458785: 99309 (SNF subsequent) entered at POS 21 / hospital facility (Pattern 4531 + hospitalization
#      date) - the place of service or the CPT is wrong; a judgement call -> HOLD, board row for William. Never bypassed.
#   --dry (default) prints the plan; --live writes. Register registers/act_2026-10-28T0640Z[_dry].json.
import amd, resave, txh, re, json, sys, time, datetime
import xml.etree.ElementTree as ET
import dx_primary_fix as dpf
DRY = "--live" not in sys.argv
STAMP = "2026-10-28T0640Z"
amd.login_cached()
out = {"stamp": STAMP, "dry": DRY, "steps": [], "hold": [], "done": []}
def L(m): print(m, flush=True); out["steps"].append(m)
A_ROWS = [("17476869", "19458733", "23370953"), ("17478059", "19458794", "23371014"), ("24560", "19458830", "23371055")]
B_ROWS = [("17473748", "19458755", "23370975"), ("17472854", "19458776", "23370996")]
C_ROWS = [("25994", "19458784", "23371004"), ("25994", "19458785", "23371005")]

def admit_for(pid, dos):
    d = datetime.datetime.strptime(dos, "%m/%d/%Y").date(); best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or not (c.get("proccode") or "").startswith("99223") or not c.get("dos"): continue
        cd = datetime.datetime.strptime(c.get("dos").strip(), "%m/%d/%Y").date()
        if cd <= d and (d - cd).days <= 45 and (best is None or cd > best): best = cd
    return best.strftime("%m/%d/%Y") if best else None
def cpts_of(allc):
    cpt = {}
    for c in allc:
        x = resave.detail(c.get("id").replace("charge", ""))
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    return cpt
def set_date(vid, code, admit):
    if DRY: return "DRY"
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
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

# ---------------- A ----------------
for pid, vid, cid in A_ROWS:
    vis, pat, allc = resave.visit_charges(cid); cpt = cpts_of(allc)
    dos = (allc[0].get("begindate") or vis.get("date") or "").strip()
    ex = vis.find("extins"); have = ex.get("hospitalizationfrom") if ex is not None else None
    if have and vis.get("onhcfa") == "1":
        L("A pat%s v%s dos %s: admission %s already on the visit, onhcfa=1 - nothing to write" % (pid, vid, dos, have)); out["done"].append({"pid": pid, "vid": vid, "dos": dos, "action": "already set %s" % have}); continue
    own223 = any(str(v).startswith("99223") for v in cpt.values())
    admit = have or (dos if own223 else admit_for(pid, dos))
    L("A pat%s v%s dos %s cpts %s insorder %s onhcfa %s hospfrom-now %r -> admission %s" % (pid, vid, dos, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa"), have, admit))
    if not admit:
        L("  HOLD: no 99223 within 45 days of %s" % dos); out["hold"].append({"pid": pid, "vid": vid, "dos": dos, "why": "no 99223 anchor within 45 days"}); continue
    if not have:
        for p in sorted(set(cpt.values())): L("  updextrainsinfo %s %s -> %s" % (p, admit, set_date(vid, p, admit)))
    ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": vis.get("insorder")}); L("  resave: " + msg)
    (out["done"] if ok else out["hold"]).append({"pid": pid, "vid": vid, "dos": dos, "action" if ok else "why": ("admission %s, onhcfa=1" % admit) if ok else msg})
    time.sleep(0.4)

# ---------------- B ----------------
for pid, vid, cid in B_ROWS:
    st = dpf.live_state(pid, vid)
    if any(s["pays"] for s in st): L("B v%s SKIP - payment posted" % vid); out["hold"].append({"pid": pid, "vid": vid, "why": "payment posted"}); continue
    vis, pat, allc, m = dpf.visit_dx(cid)
    inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dpf.I10_DCODE)
    plans = {}; acts = set(); after = None
    for c in allc:
        dcodes = (c.get("diagcodes") or "").split(); codes = [m.get(d, d) for d in dcodes]
        cpt = None
        for pc in ET.fromstring(resave.detail(c.get("id").replace("charge", ""))).iter("proccode"):
            if pc.get("id") == c.get("proccode"): cpt = pc.get("code")
        act, new = dpf.plan(codes, cpt); acts.add(act)
        L("B pat%s v%s %s %s dx %s -> %s (%s)" % (pid, vid, c.get("id"), cpt, codes, new, act))
        if act != "ok": plans[c.get("id")] = [inv[x] for x in new]; after = new
    if not plans: out["done"].append({"pid": pid, "vid": vid, "action": "primary dx already acceptable"}); continue
    r, det = dpf.save_visit_dx(cid, plans, dry=DRY); L("  " + r)
    if DRY: continue
    ok = not r.startswith("FAULT") and all(det.get(k, (None, None))[1] == v for k, v in plans.items())
    (out["done"] if ok else out["hold"]).append({"pid": pid, "vid": vid, "action" if ok else "why": ("%s -> %s" % ("/".join(sorted(acts)), after)) if ok else r})
    if ok:
        reg = json.load(open(dpf.REGISTER)) if __import__("os").path.exists(dpf.REGISTER) else []
        reg.append({"pid": pid, "vid": vid, "cid": "charge" + cid, "action": "/".join(sorted(acts)), "dx_after": after, "rebill": "none - unbilled visit, inspector release", "when": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z", "run": STAMP})
        json.dump(reg, open(dpf.REGISTER, "w"), indent=1)
    time.sleep(0.4)

# ---------------- C ----------------
for pid, vid, cid in C_ROWS:
    vis, pat, allc = resave.visit_charges(cid); cpt = cpts_of(allc)
    L("C pat%s v%s dos %s cpt %s facility %s pos %s - 99309 at POS 21 / hospital facility: place of service or CPT wrong -> HOLD for William" % (pid, vid, allc[0].get("begindate"), list(cpt.values()), vis.get("facility"), allc[0].get("pos")))
    out["hold"].append({"pid": pid, "vid": vid, "dos": allc[0].get("begindate"), "cpt": list(cpt.values()), "facility": vis.get("facility"), "pos": allc[0].get("pos"), "why": "99309 at POS 21 (Pattern 4531 + hospitalization date) - POS/CPT decision for William"})
json.dump(out, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1, default=str)
L("=== done (dry=%s) done=%d hold=%d ===" % (DRY, len(out["done"]), len(out["hold"])))
