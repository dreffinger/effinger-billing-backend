# PLAIN ENGLISH (2:40 AM ET 10/28 slot, stabilising loop): the Claimocity feed is delivering a large batch during the run, so one pass
#   is not enough. Up to 3 rounds of: fresh columns_scan -> per inspector visit: (a) Pattern 20389 never-primary first dx -> William's
#   9/14 cascade (dx_primary_fix.plan + save_visit_dx, full echo, no rebill - never claimed); (b) 'Hospitalization From Date empty' on a
#   hospital E/M (99221-99239) -> own 99223 DOS else most recent 99223 within 45 days (gettxhistory), updextrainsinfo hospitalizationfrom
#   only, full resave onhcfa=1; a 99309/99310 at POS 21 (Pattern 4531) is a place-of-service judgement -> HOLD for William; (c) then
#   insp_bypass_advisories with the fresh ids. Stops when a round changes nothing. Register registers/insp_loop_2026-10-28T0640Z.json.
#   Never touches paid visits, hospitalizationto, insurance plans, payments.
import amd, resave, txh, re, json, sys, time, datetime, subprocess, os
import xml.etree.ElementTree as ET
import dx_primary_fix as dpf
STAMP = "2026-10-28T0640Z"; SCAN = "scan_2026-10-28T0652Z"
amd.login_cached(); out = {"stamp": STAMP, "rounds": [], "done": [], "hold": {}, "names": {}}
def L(m): print(m, flush=True)
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
        x = resave.detail(c.get("id").replace("charge", "")); pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    return cpt
def set_date(vid, code, admit):
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
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    ok = "Fault" not in r and len(c2) == len(allc)
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if "Fault" in r else "saved live=%d/%d onhcfa=%s hospfrom=%s" % (len(c2), len(allc), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None)
def dx_fix(pid, vid, cid):
    if any(s["pays"] for s in dpf.live_state(pid, vid)): return "SKIP-PAID"
    vis, pat, allc, m = dpf.visit_dx(cid); inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dpf.I10_DCODE)
    plans = {}; acts = set(); after = None; before = None
    for c in allc:
        codes = [m.get(d, d) for d in (c.get("diagcodes") or "").split()]; cpt = None
        for pc in ET.fromstring(resave.detail(c.get("id").replace("charge", ""))).iter("proccode"):
            if pc.get("id") == c.get("proccode"): cpt = pc.get("code")
        act, new = dpf.plan(codes, cpt); acts.add(act)
        if act != "ok": plans[c.get("id")] = [inv[x] for x in new]; after = new; before = codes
    if not plans: return "OK-already-acceptable"
    r, det = dpf.save_visit_dx(cid, plans, dry=False)
    ok = not r.startswith("FAULT") and all(det.get(k, (None, None))[1] == v for k, v in plans.items())
    if ok:
        reg = json.load(open(dpf.REGISTER)) if os.path.exists(dpf.REGISTER) else []
        reg.append({"pid": pid, "vid": vid, "cid": cid, "action": "/".join(sorted(acts)), "dx_before": before, "dx_after": after, "rebill": "none - unbilled visit, inspector release", "when": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z", "run": STAMP}); json.dump(reg, open(dpf.REGISTER, "w"), indent=1)
    return ("%s %s -> %s" % ("/".join(sorted(acts)), before, after)) if ok else r
seen_hold = set()
for rnd in range(1, 4):
    tag = "loop%d" % rnd
    subprocess.run([sys.executable, "columns_scan.py", tag, SCAN], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    S = json.load(open("%s/summary_%s.json" % (SCAN, tag))); changed = 0; held_now = []
    rows = [v for b, vs in S["inspector"].items() for v in vs]
    L("round %d: inspector rows %d, unbilled %s, exclusions %s" % (rnd, len(rows), S["overview"]["unbillablecount"], S["overview"]["exclusioncount"]))
    for v in rows:
        vid, pid = v["vid"], v["pid"]; errs = [e[1] for e in v["errs"]]; cids = [c[0] for c in v["chgs"]]
        if not errs or not cids: continue
        has20389 = any("Pattern 20389" in e for e in errs); hasHosp = any("Hospitalization From Date" in e for e in errs); has4531 = any("Pattern 4531" in e for e in errs)
        if has20389:
            r = dx_fix(pid, vid, cids[0]); L("  20389 pat%s v%s: %s" % (pid, vid, r)); out["done"].append({"pid": pid, "vid": vid, "what": "dx cascade", "result": r}); changed += 1 if not r.startswith(("SKIP", "OK")) else 0
        if hasHosp:
            vis, pat, allc = resave.visit_charges(cids[0]); cpt = cpts_of(allc); dos = (allc[0].get("begindate") or "").strip()
            ex = vis.find("extins"); have = ex.get("hospitalizationfrom") if ex is not None else None
            hospem = any(str(c).startswith(("99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239")) for c in cpt.values())
            if has4531 or not hospem:
                key = vid
                if key not in seen_hold:
                    seen_hold.add(key); out["names"][pid] = {"name": pat.get("name"), "dob": pat.get("dob")}
                    out["hold"][vid] = {"pid": pid, "dos": dos, "cpt": sorted(set(cpt.values())), "facility": vis.get("facility"), "pos": allc[0].get("pos"), "why": "non-hospital E/M at POS 21 (Pattern 4531 + hospitalization date) - POS/CPT decision for William"}
                    L("  HOLD pat%s v%s %s %s at POS %s facility %s" % (pid, vid, dos, sorted(set(cpt.values())), allc[0].get("pos"), vis.get("facility")))
                continue
            admit = have or (dos if any(str(c).startswith("99223") for c in cpt.values()) else admit_for(pid, dos))
            if not admit:
                out["hold"][vid] = {"pid": pid, "dos": dos, "cpt": sorted(set(cpt.values())), "why": "no 99223 anchor within 45 days"}; out["names"][pid] = {"name": pat.get("name"), "dob": pat.get("dob")}; L("  HOLD pat%s v%s no 99223 anchor" % (pid, vid)); continue
            if not have:
                for p in sorted(set(cpt.values())): L("  admit pat%s v%s %s %s -> %s" % (pid, vid, p, admit, set_date(vid, p, admit)))
            ok, msg = full_resave(cids[0], {"onhcfa": "1", "insorder": vis.get("insorder")}); L("  resave pat%s v%s: %s" % (pid, vid, msg))
            out["done"].append({"pid": pid, "vid": vid, "what": "admission %s" % admit, "result": msg}); changed += 1; time.sleep(0.3)
    time.sleep(3)
    subprocess.run([sys.executable, "columns_scan.py", tag + "b", SCAN], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    bp = subprocess.run([sys.executable, "insp_bypass_advisories.py", "%s/summary_%sb.json" % (SCAN, tag + ""), "--live"], capture_output=True, text=True, timeout=600)
    last = (bp.stdout.strip().splitlines() or [""])[-1]; L("  bypass: " + last)
    m = re.search(r"done=(\d+)", last); nb = int(m.group(1)) if m else 0
    S2 = json.load(open("%s/summary_%sb.json" % (SCAN, tag + "")))
    out["rounds"].append({"round": rnd, "rows": len(rows), "changed": changed, "bypassed": nb, "rows_after": sum(len(vs) for vs in S2["inspector"].values())})
    if changed == 0 and nb == 0: break
json.dump(out, open("registers/insp_loop_%s.json" % STAMP, "w"), indent=1, default=str)
L("=== loop done: rounds %s, holds %d ===" % (out["rounds"], len(out["hold"])))
