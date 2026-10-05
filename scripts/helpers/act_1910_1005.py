# PLAIN ENGLISH (3 PM ET 10/5 slot, run 2026-10-05T1910Z): Claim Inspector batch 127873 - 13 new HCA rows from the 10/2-10/4 feed,
#   every one held 'Hospitalization From Date in the Extra Info tab is empty' (Pattern 117065068).
#   A: admission = the visit's own 99223 DOS when the visit carries a 99223, else the most recent 99223 on/before the DOS
#      within 45 days on that chart (gettxhistory); updextrainsinfo hospitalizationfrom ONLY (never hospitalizationto);
#      then the full-visit resave (resave.visit_charges echo, every active charge kept) with onhcfa=1.
#      No 99223 anchor within 45 days = HOLD (admission date unknown) - reported, never guessed, board row for William.
#   B: re-list the batch after the edits and bypass ONLY advisory patterns (CCM add-on / frequency, timely, AWV, provider-history,
#      mod-25, laterality 11256 with a laterality_flag_log.md line) with the FRESH error ids; missing-data holds stay.
#   --dry (default) prints every planned write and sends nothing; --live sends them. Register registers/act_2026-10-05T1910Z[_dry].json.
#   Never touches: payments, hospitalizationto, insurance plans, group numbers, the standing holds (batch 127783 Pattern 24078).
import amd, resave, txh, re, json, sys, time, datetime
import xml.etree.ElementTree as ET
DRY = "--live" not in sys.argv
STAMP = "2026-10-05T1910Z"; BATCH = "127873"
amd.login_cached()
out = {"stamp": STAMP, "dry": DRY, "steps": [], "hold": [], "done": []}
def L(m): print(m, flush=True); out["steps"].append(m)
ADVISORY = {"35790", "7011", "3429", "35777", "33799", "20657", "27261", "4310", "4426", "11256"}
ROWS = [("17477557", "19456963", "23368692"), ("17472228", "19456964", "23368693"), ("17476869", "19456965", "23368694"),
        ("17477640", "19456966", "23368695"), ("17472703", "19456967", "23368696"), ("17477899", "19456969", "23368698"),
        ("17474741", "19456970", "23368699"), ("17472553", "19456971", "23368700"), ("20863", "19456972", "23368701"),
        ("17471741", "19456973", "23368702"), ("17471916", "19456974", "23368703"), ("23159", "19456975", "23368704"),
        ("17474493", "19456976", "23368705")]

def admit_for(pid, dos):
    d = datetime.datetime.strptime(dos, "%m/%d/%Y").date(); best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or not (c.get("proccode") or "").startswith("99223") or not c.get("dos"): continue
        cd = datetime.datetime.strptime(c.get("dos").strip(), "%m/%d/%Y").date()
        if cd <= d and (d - cd).days <= 45 and (best is None or cd > best): best = cd
    return best.strftime("%m/%d/%Y") if best else None
def set_date(vid, code, admit):
    if DRY: return "DRY"
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
def cpts_of(allc):
    cpt = {}
    for c in allc:
        x = resave.detail(c.get("id").replace("charge", ""))
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    return cpt
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
def bypass(vid, errids):
    if DRY: return "DRY bypass %s" % errids
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in errids))))
    return "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])

# ---------------- A. admission dates ----------------
for pid, vid, cid in ROWS:
    vis, pat, allc = resave.visit_charges(cid); cpt = cpts_of(allc)
    dos = (allc[0].get("begindate") or vis.get("date") or "").strip()
    ex = vis.find("extins"); have = ex.get("hospitalizationfrom") if ex is not None else None
    own223 = any(str(v).startswith("99223") for v in cpt.values())
    admit = dos if own223 else admit_for(pid, dos)
    L("A pat%s v%s dos %s cpts %s insorder %s onhcfa %s hospfrom-now %r -> admission %s" % (pid, vid, dos, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa"), have, admit))
    if not dos:
        L("  HOLD: no DOS read"); out["hold"].append({"pid": pid, "vid": vid, "why": "no DOS read"}); continue
    if not admit:
        L("  HOLD: no 99223 within 45 days of %s - admission date unknown (William)" % dos); out["hold"].append({"pid": pid, "vid": vid, "dos": dos, "cpts": sorted(set(cpt.values())), "why": "no 99223 anchor within 45 days"}); continue
    for p in sorted(set(cpt.values())): L("  updextrainsinfo %s %s -> %s" % (p, admit, set_date(vid, p, admit)))
    ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": vis.get("insorder")}); L("  resave: " + msg)
    if ok: out["done"].append({"pid": pid, "vid": vid, "dos": dos, "cpts": sorted(set(cpt.values())), "action": "admission %s, onhcfa=1" % admit})
    else: out["hold"].append({"pid": pid, "vid": vid, "dos": dos, "why": "resave " + msg})
    time.sleep(0.4)

# ---------------- B. re-list the batch, bypass advisories with fresh ids ----------------
if not DRY:
    time.sleep(3)
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": BATCH, "nocookie": "1"}), timeout=120)
    root = ET.fromstring(t); left = []
    for v in root.iter("visit"):
        vid = re.sub(r"\D", "", v.get("id") or "")
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:160]) for e in v.iter("error")]
        adv = [eid for eid, tx in errs if (re.search(r"Pattern (\d+)", tx) and re.search(r"Pattern (\d+)", tx).group(1) in ADVISORY)]
        if adv:
            L("B v%s bypass advisories %s -> %s" % (vid, [tx[:70] for eid, tx in errs if eid in adv], bypass(vid, adv)))
            for eid, tx in errs:
                if eid in adv and "11256" in tx:
                    open("laterality_flag_log.md", "a").write("- 10/5 pat%s visit %s: %s - bypassed (no known correction); William to specify\n" % (v.get("patientid"), vid, tx[:120]))
        rest = [tx for eid, tx in errs if eid not in adv]
        if rest: left.append((vid, v.get("patientid"), rest)); L("B v%s STILL HELD: %s" % (vid, [r[:90] for r in rest]))
    out["left_%s" % BATCH] = left
json.dump(out, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1, default=str)
L("=== done (dry=%s) ===" % DRY)
