# PLAIN ENGLISH (Unbilled 'Insurance order is missing' - two new HCA charts, 1am ET 9/22/2026 run 2026-09-22T0510Z)
# Decides, per William's lookup order (patient_db -> AMD 271 -> Stedi -> facesheet -> William) already run this slot
#   (secrets/newcharts_stedi_2026-09-22T0510Z.json - names/MBIs never leave the workspace):
#   pat17477818: Stedi MBI lookup (SSN) = straight Medicare A/B since 9/1/2015, WellCare stand-alone PDP only, QMB Medicaid COB from
#     3/1/2026 (FL Medicaid 77027 answered AAA 42 'unable to respond' x4 - the Medicaid number is still to come) -> FLO02 seq 1.
#   pat17477819: Stedi MBI lookup (SSN) = Medicare A/B since 5/1/2012 with a HUMANA PPO (CMS code U, COB 1/1/2026 = Medicare Advantage);
#     Stedi Humana 61101 with the MBI answered ACTIVE PPO 'Alcoa' (group Medicare Advantage) member id on file, plan begin 1/1/2026 -> HUM01 seq 1.
#   Per chart: add_ins.add (NO group number), AMD free 271 on the new plan, PRIMARY-DX GATE (dx_primary_fix.plan / save_visit_dx),
#   admission date = the stay's own 99223 (9/18/2026) via updextrainsinfo hospitalizationfrom ONLY, full-visit resave insorder + onhcfa=1
#   (charge echo - void trap), address line 1 moved up from line 2 (Claimocity feed leaves it blank), then release from Unbilled.
# Never touches: group numbers, hospitalizationto, payments, any other chart.
"""Usage: python3 newcharts_0922_0510.py [--dry]"""
import amd, resave, add_ins, elig_amd, addr_line1_fix, dx_primary_fix, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
S = "2026-09-22T0510Z"; dry = "--dry" in sys.argv
amd.login_cached()
def L(m): print(m, flush=True)
SC = json.load(open("scan_0912/summary_before.json")); rows = {r["id"]: r for r in SC["unbilled"]}
CFG = json.load(open("secrets/newcharts_0922_0510_cfg.json"))   # per-chart plan / member number / address config - secrets/, never leaves the workspace
REG = {"stamp": S, "dry": dry, "charts": {}, "released": []}
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
REL = []
for pid, cfg in CFG.items():
    rec = {"added": [], "elig": [], "visits": {}, "addr": None}
    L("--- pat%s ---" % pid)
    for car, num, bd in cfg["add"]:
        s, insid = seq_of(pid, car)
        if s: L("  plan %s already on file seq %s (%s)" % (car, s, insid)); rec["added"].append([car, insid, s, "already"]); continue
        if dry: L("  DRY add %s begin %s" % (car, bd)); continue
        insid, s = add_ins.add(pid, car, num, bd); L("  add %s begin %s -> %s seq %s" % (car, bd, insid, s)); rec["added"].append([car, insid, s, "new"]); time.sleep(0.5)
        if insid and str(insid).startswith("ins"):
            try:
                e = elig_amd.run_plan(pid, insid.replace("ins", ""), True); line = elig_amd.one_line(e)[:300]; L("  AMD 271 %s: %s" % (car, line)); rec["elig"].append([car, line])
            except Exception as ex: L("  AMD 271 ERR %s" % str(ex)[:120]); rec["elig"].append([car, "ERR " + str(ex)[:120]])
    try:
        msg, det = addr_line1_fix.fix(pid, *cfg["addr"], dry=dry); L("  addr: %s %s" % (msg, json.dumps(det)[:200])); rec["addr"] = msg
    except Exception as ex: L("  addr ERR %s" % str(ex)[:150]); rec["addr"] = "ERR " + str(ex)[:150]
    vids = [r["id"] for r in SC["unbilled"] if r["patientid"] == pid and "Insurance order" in r["_errs"][0]]
    seq, insid = seq_of(pid, cfg["bill"])
    if not seq and not dry: L("  NO open %s plan on chart -> HOLD" % cfg["bill"]); rec["hold"] = True; REG["charts"][pid] = rec; continue
    L("  bill seq %s (%s %s)" % (seq, cfg["bill"], insid))
    for vid in vids:
        r = rows[vid]; cid = r["_chgs"][0]["id"]; codes = sorted({c["chgcode"] for c in r["_chgs"]}); vr = {}
        try: vr["dx"] = dx_gate(cid); L("  v%s %s" % (vid, vr["dx"][:300]))
        except Exception as ex: vr["dx"] = "DX ERR " + str(ex)[:150]; L("  v%s dx gate ERR %s" % (vid, str(ex)[:150]))
        adm = cfg["admit"]
        if not dry:
            for code in codes: res = set_admit(vid, code, adm); L("  v%s admit %s %s -> %s" % (vid, code, adm, res)); vr["admit_%s" % code] = res; time.sleep(0.3)
        else: L("  DRY v%s admit %s on %s" % (vid, adm, codes))
        vr["resave"] = resave_full(cid, insorder=seq); L("  v%s resave -> %s" % (vid, vr["resave"]))
        if vr["resave"].startswith("ok") or dry: REL.append(vid)
        rec["visits"][vid] = vr; time.sleep(0.4)
    REG["charts"][pid] = rec
L("release %d visits %s" % (len(REL), REL))
if REL and not dry:
    xml = amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"', "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in REL))
    ok = 'success="1"' in xml or '<Error/>' in xml or '<Error />' in xml
    REG["released"] = [{"vid": v, "ok": ok} for v in REL]; L("release -> ok=%s %s" % (ok, re.sub(r"\s+", " ", xml)[:160]))
json.dump(REG, open("registers/newcharts_%s%s.json" % (S, "_dry" if dry else ""), "w"), indent=1)
L("=== done")
