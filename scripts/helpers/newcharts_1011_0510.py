# PLAIN ENGLISH (Unbilled 'Insurance order is missing' - new Claimocity HCA charts, 1 AM ET 10/11/2026 run 2026-10-11T0510Z;
#   same shape as newcharts_1009_0510.py, driven by this run's Stedi answers in patient_db/<pid>/[name]_[DOB].json)
# Decides, per William's lookup order (patient_db -> AMD 271 -> Stedi -> facesheet -> William), for the charts named below:
#   chart 17478030: Stedi MBI lookup = ORIGINAL MEDICARE Part A/B since 10/1/2023, no Advantage entity, no QMB -> FLO02 (car6085)
#     plan with the MBI (begin = the Part B date, NO group number), AMD free 271 on it, admission 10/07/2026 (the stay's own 99223)
#     on the three visits, full-visit resave insorder <Medicare seq> + onhcfa=1 (charge echo), release from Unbilled.
#   chart 17478031: Stedi MBI lookup = ORIGINAL MEDICARE Part A/B since 7/1/2024 + QMB (FL QMB Plan, COB 7/1/2024) = dual; the
#     Medicaid id is not in the 271 -> FLO02 plan added the same way, visits released Medicare-first; the Florida Medicaid plan waits
#     for the Medicaid id (board row on William's turn; QMB: the coinsurance is never the patient's).
#   chart 17478013: MBI lookup ERR 72 and discovery found nothing -> nothing added, visits stay in Unbilled (board row, facesheet).
#   PRIMARY-DX gate (dx_primary_fix.plan) on every live charge before the resave; the MBI is read from patient_db at run time and never printed.
# Never touches: group numbers, hospitalizationto, payments, any other chart.
#   python3 newcharts_1011_0510.py          # dry
#   python3 newcharts_1011_0510.py --live   # register registers/newcharts_2026-10-11T0510Z.json
import amd, resave, add_ins, elig_amd, dx_primary_fix, json, re, sys, time
import xml.etree.ElementTree as ET
S = "2026-10-11T0510Z"; dry = "--live" not in sys.argv
amd.login_cached()
def L(m): print(m, flush=True)
REG = {"stamp": S, "dry": dry, "charts": {}, "released": []}
CHARTS = {
    "17478030": {"admit": "10/07/2026", "visits": [("19457491", "23369399", "99223"), ("19457457", "23369363", "99232"), ("19457453", "23369359", "99232")]},
    "17478031": {"admit": "10/07/2026", "visits": [("19457492", "23369400", "99223"), ("19457459", "23369365", "99232"), ("19457455", "23369361", "99232")]},
}
def set_admit(vid, code, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit))
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
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return "ok insorder=%s onhcfa=%s hospfrom=%s live %d (was %d)" % (v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, len(c2), len(allc))
def dx_gate(cid):
    vis, pat, allc, m = dx_primary_fix.visit_dx(cid)
    inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dx_primary_fix.I10_DCODE)
    new = {}; notes = []
    for c in allc:
        dcodes = (c.get("diagcodes") or "").split(); codes = [m.get(d, d) for d in dcodes]
        act, nc = dx_primary_fix.plan(codes, c.get("proccode"))
        notes.append("%s %s dx %s -> %s" % (c.get("id"), c.get("proccode"), codes, act))
        if act != "ok": new[c.get("id")] = [inv[x] if x in inv else x for x in nc]
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
def release(vids):
    if not vids: return "nothing"
    if dry: return "DRY release %s" % vids
    xml = amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"', "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids))
    ok = 'success="1"' in xml or '<Error/>' in xml or '<Error />' in xml
    REG["released"] += [{"vid": v, "ok": ok} for v in vids]; return "ok=%s %s" % (ok, re.sub(r"\s+", " ", xml)[:120])
for pid, cfg in CHARTS.items():
    cr = {"steps": []}; REG["charts"][pid] = cr
    j = json.load(open("patient_db/%s/[name]_[DOB].json" % pid)); sub = j.get("subscriber", {}); mbi = sub.get("memberId")
    pb = None
    for b in j.get("benefitsInformation", []):
        if b.get("code") == "1" and (b.get("serviceTypeCodes") or ["30"])[0] in ("30", "48", "49") and b.get("benefitsDateInformation", {}).get("plan"):
            pb = pb or b["benefitsDateInformation"]["plan"]
    pb = pb or "20240101"; begin = "%s/%s/%s" % (pb[4:6], pb[6:8], pb[0:4])
    if not mbi or j.get("errors"):
        cr["steps"].append("no MBI in the Stedi answer - nothing added"); L("%s: no MBI - skip" % pid); continue
    seq, insid = seq_of(pid, "car6085")
    if insid: cr["steps"].append("FLO02 already on the chart %s seq %s" % (insid, seq)); L("%s: FLO02 already %s seq %s" % (pid, insid, seq))
    elif dry: cr["steps"].append("DRY add FLO02 car6085 begin %s MC" % begin); L("%s: DRY add FLO02 begin %s" % (pid, begin)); seq = "1"
    else:
        insid, seq = add_ins.add(pid, "car6085", mbi, begin, "1", "MC"); cr["steps"].append("add_ins FLO02 -> %s seq %s" % (insid, seq)); L("%s: add_ins -> %s seq %s" % (pid, insid, seq))
        if not insid or not str(seq).isdigit(): L("%s: STOP plan not added" % pid); continue
        time.sleep(0.8)
        try:
            e = elig_amd.run_plan(pid, insid); cr["elig"] = (elig_amd.one_line(e) if isinstance(e, dict) else str(e))[:300]; L("%s: 271 %s" % (pid, cr["elig"]))
        except Exception as ex: cr["elig"] = "ERR %s" % str(ex)[:200]; L("%s: 271 ERR" % pid)
    rel = []
    for vid, cid, code in cfg["visits"]:
        vr = {"vid": vid, "cid": cid}
        vr["dx"] = dx_gate(cid); L("  v%s dx: %s" % (vid, vr["dx"][:200]))
        if not dry: vr["admit"] = set_admit(vid, code, cfg["admit"]); time.sleep(0.3)
        else: vr["admit"] = "DRY admit %s" % cfg["admit"]
        vr["resave"] = resave_full(cid, insorder=seq, onhcfa="1"); L("  v%s admit %s resave %s" % (vid, vr["admit"], vr["resave"]))
        cr.setdefault("visits", []).append(vr); rel.append(vid); time.sleep(0.4)
    cr["release"] = release(rel); L("%s: release %s" % (pid, cr["release"]))
json.dump(REG, open("registers/newcharts_%s.json" % S, "w"), indent=1)
L("saved registers/newcharts_%s.json" % S)
