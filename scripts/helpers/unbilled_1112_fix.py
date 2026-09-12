# PLAIN ENGLISH (Unbilled fix, 9/12 7am ET run - the 4 new HCA admits William answered on the board 08:55-09:25 UTC)
# Decides: for each chart, add the plan William gave (facesheet text on the board row / Drive PDF), run AMD's free 271 on it,
#   then resave every visit with insorder=1, the stay's referral plan + auth, hospitalizationfrom (the 99223 date), onhcfa=1
#   (full charge echo), and release the rows from Unbilled with hideunbillablevisits hide=-1.
# Rules it uses: no group numbers; auth = the value before the slash; VA member id = the ICN; out-of-state Blues -> FLORIDA BLUE;
#   an explicit INACTIVE 271 holds the patient (no release); an unanswered 271 does not block a plan William supplied himself.
# Never touches: other patients, existing plans, balances.
import amd, add_ins, resave, era_post, subprocess, re, sys, time, json
import xml.etree.ElementTree as ET
IDS = json.load(open('secrets/run_1112_ids.json'))  # member ids / auths live in secrets/ (workspace + Drive only)
LOG = open("unbilled_1112_fix.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
PATS = [
 {"pid": "17477706", "who": "pat17477706", "car": "car42025", "num": IDS["pats"]["pat17477706"]["num"], "begin": "09/01/2026", "preauth": IDS["pats"]["pat17477706"]["preauth"], "refplan": "rplan18461996", "hosp": "09/08/2026",
  "visits": [("19454317", "23365390"), ("19454284", "23365356"), ("19454270", "23365342")]},
 {"pid": "17477708", "who": "pat17477708", "car": "car6062", "num": IDS["pats"]["pat17477708"]["num"], "begin": "09/01/2026", "preauth": IDS["pats"]["pat17477708"]["preauth"], "refplan": "rplan18461998", "hosp": "09/08/2026",
  "visits": [("19454314", "23365387"), ("19454286", "23365358"), ("19454283", "23365355")]},
 {"pid": "17477709", "who": "pat17477709", "car": "car6062", "num": IDS["pats"]["pat17477709"]["num"], "begin": "09/01/2026", "preauth": IDS["pats"]["pat17477709"]["preauth"], "refplan": "rplan18461999", "hosp": "09/08/2026",
  "visits": [("19454316", "23365389"), ("19454294", "23365367")]},
 {"pid": "17477710", "who": "pat17477710", "car": "car41826", "num": IDS["pats"]["pat17477710"]["num"], "begin": "09/01/2026", "preauth": IDS["pats"]["pat17477710"]["preauth"], "refplan": "rplan18462000", "hosp": "09/09/2026",
  "visits": [("19454313", "23365386")]},
]
def save_visit(cid, insorder, refplan, preauth, hosp, batch):
    vis, pat, allc = resave.visit_charges(cid)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va.update({"force": "1", "insorder": insorder, "refplan": refplan, "onhcfa": "1"})
    if preauth: va["preauth"] = preauth
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch),
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist>%s</visit>" % (vs, chg, resave._extins_xml(vis, hosp))))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:240]), None
    time.sleep(0.8)
    v2, p2, c2 = resave.visit_charges(cid)
    ex = v2.find("extins")
    return "saved live=%d/%d insorder=%s refplan=%s preauth=%s onhcfa=%s hospfrom=%s" % (len(c2), len(allc), v2.get("insorder"), v2.get("refplan"), v2.get("preauth"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None), len(c2) == len(allc)
amd.login_cached()
batch = era_post.batch()
results = {}
for p in PATS:
    L("== %s" % p["who"])
    insid, seq = add_ins.add(p["pid"], p["car"], p["num"], p["begin"])
    L("  addinsurance -> %s seq %s" % (insid, seq))
    if not insid: results[p["who"]] = "ADD FAILED " + str(seq); continue
    time.sleep(0.5)
    el = subprocess.run(["python3", "elig_amd.py", p["pid"]], capture_output=True, text=True, timeout=240)
    eltxt = re.sub(r"\s+", " ", (el.stdout + el.stderr))[:600]
    L("  271: " + eltxt)
    inactive = bool(re.search(r"\bINACTIVE\b", eltxt)) and not re.search(r"\bACTIVE\b", eltxt.replace("INACTIVE", ""))
    if inactive:
        results[p["who"]] = "HELD - 271 INACTIVE: " + eltxt; continue
    ok_all = True; released = []
    for vid, cid in p["visits"]:
        msg, ok = save_visit(cid, "1", p["refplan"], p["preauth"], p["hosp"], batch)
        L("  v%s %s" % (vid, msg)); ok_all = ok_all and bool(ok); time.sleep(0.5)
        if ok: released.append(vid)
    if released:
        r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in released)))
        L("  release %s -> %s" % (released, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200])))
    results[p["who"]] = {"ins": insid, "seq": seq, "elig": eltxt[:300], "released": released, "all_ok": ok_all}
json.dump(results, open("unbilled_1112_results.json", "w"), indent=1)
L(json.dumps({k: (v if isinstance(v, str) else {"ins": v["ins"], "released": v["released"]}) for k, v in results.items()}))
