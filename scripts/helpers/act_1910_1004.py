# PLAIN ENGLISH (3 PM ET 10/4 slot, run 2026-10-04T1910Z): Claim Inspector batch 127868 (7 new rows from the 10/1-10/2 feed).
#   A: admission-date holds (Pattern 117065068) - admission = the visit's own 99223 DOS, else the most recent 99223 on/before the DOS
#      within 45 days (gettxhistory); updextrainsinfo hospitalizationfrom only (never hospitalizationto); full-visit resave onhcfa=1.
#      v19456903 (99223 10/02), v19456904 (99223+99497 09/29), v19456905 (99233 10/01 -> anchor search). No anchor = HOLD, board row.
#   B: Pattern 11256 unspecified laterality (H91.90 on v19456906) -> bypassclaimedits + laterality_flag_log.md.
#   C: Pattern 4310 (99344 new-patient home visit on an established patient) x3 -> standing rule: 99344 -> 99349 (pcode65142) via
#      recode.swap_proc (full-visit resave + freq-1), precedent inspector_0906.py / whitlock_recode_0919_1910.py.
#   D: re-list batch 127868 after the edits and bypass ONLY advisory patterns with the fresh error ids (never missing-data edits).
#   --dry prints every write and sends nothing. Never touches: payments, hospitalizationto, group numbers, the 20 standing holds.
import amd, resave, recode, txh, re, json, sys, time, datetime
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
STAMP = "2026-10-04T1910Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
amd.login_cached()
out = {"stamp": STAMP, "dry": DRY, "steps": [], "hold": [], "done": []}
def L(m): print(m, flush=True); out["steps"].append(m)
ADVISORY = {"35790", "7011", "3429", "35777", "33799", "20657", "27261", "4310", "4426", "11256"}

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
for pid, vid, cid, dos, own223 in (("17471741", "19456903", "23368610", "10/02/2026", True), ("17476868", "19456904", "23368611", "09/29/2026", True), ("17474493", "19456905", "23368613", "10/01/2026", False)):
    vis, pat, allc = resave.visit_charges(cid); cpt = cpts_of(allc)
    admit = dos if own223 else admit_for(pid, dos)
    L("A pat%s v%s cpts %s insorder %s onhcfa %s -> admission %s" % (pid, vid, sorted(set(cpt.values())), vis.get("insorder"), vis.get("onhcfa"), admit))
    if not admit:
        L("  HOLD: no 99223 within 45 days of %s - admission date unknown (William)" % dos); out["hold"].append({"pid": pid, "vid": vid, "dos": dos, "why": "no 99223 anchor within 45 days"}); continue
    for p in sorted(set(cpt.values())): L("  updextrainsinfo %s %s -> %s" % (p, admit, set_date(vid, p, admit)))
    ok, msg = full_resave(cid, {"onhcfa": "1", "insorder": vis.get("insorder")}); L("  resave: " + msg)
    if ok: out["done"].append({"pid": pid, "vid": vid, "action": "admission %s, onhcfa=1" % admit})
    time.sleep(0.4)

# ---------------- B. laterality bypass ----------------
L("B pat17477843 v19456906 Pattern 11256 H91.90 -> bypass %s" % bypass("19456906", ["395699"]))
if not DRY:
    open("laterality_flag_log.md", "a").write("- 10/4 pat17477843 10/01/2026 visit 19456906: H91.90 unspecified laterality - bypassed (no known correction); William to specify\n")
out["done"].append({"pid": "17477843", "vid": "19456906", "action": "11256 H91.90 bypassed + logged"})

# ---------------- C. 99344 -> 99349 on established patients ----------------
for pid, vid, cid in (("17471968", "19456913", "23368621"), ("17474441", "19456916", "23368624"), ("24655", "19456919", "23368627")):
    vis, pat, allc = resave.visit_charges(cid); pc = allc[0].get("proccode"); seq = (vis.get("insorder") or "1").split(",")[0]
    if pc != "pcode601053": L("C pat%s v%s proccode is %s (not 99344/pcode601053) - skipped" % (pid, vid, pc)); continue
    if DRY: L("C pat%s v%s DRY swap_proc pcode601053 -> pcode65142 (99349), freq-1 seq %s" % (pid, vid, seq)); continue
    msg = recode.swap_proc(cid, {"pcode601053": "pcode65142"}, seq); time.sleep(1)
    after = [(c.get("id"), c.get("proccode")) for c in resave.visit_charges(cid)[2]]
    L("C pat%s v%s 99344 -> 99349: %s | after %s" % (pid, vid, msg, after))
    out["done"].append({"pid": pid, "vid": vid, "action": "99344 -> 99349 (Pattern 4310 established patient), freq-1 seq %s" % seq, "result": msg})
    time.sleep(0.5)

# ---------------- D. re-list batch 127868, bypass advisories with fresh ids ----------------
if not DRY:
    time.sleep(3)
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": "127868", "nocookie": "1"}), timeout=120)
    root = ET.fromstring(t); left = []
    for v in root.iter("visit"):
        vid = re.sub(r"\D", "", v.get("id") or "")
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:160]) for e in v.iter("error")]
        adv = [eid for eid, tx in errs if (re.search(r"Pattern (\d+)", tx) and re.search(r"Pattern (\d+)", tx).group(1) in ADVISORY)]
        if adv: L("D v%s bypass advisories %s -> %s" % (vid, [tx[:60] for eid, tx in errs if eid in adv], bypass(vid, adv)))
        rest = [tx for eid, tx in errs if eid not in adv]
        if rest: left.append((vid, v.get("patientid"), rest)); L("D v%s STILL HELD: %s" % (vid, [r[:90] for r in rest]))
    out["left_127868"] = left
json.dump(out, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1, default=str)
L("=== done (dry=%s) ===" % DRY)
