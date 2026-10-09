# PLAIN ENGLISH (Unbilled 'Insurance order is missing' - 1 AM ET 10/9/2026 run 2026-10-09T0510Z; same shape as newcharts_0922_0510.py)
# Decides, per William's lookup order (patient_db -> AMD 271 -> Stedi -> facesheet -> William) already run this slot
#   (secrets/newcharts_stedi_2026-10-09T0510Z.json + secrets/newcharts_1009_0510_cfg.json - names/MBIs/member ids never leave the workspace):
#   three new HCA charts get the plan the cascade found (add_ins, NO group number), AMD free 271 on it, the PRIMARY-DX gate,
#   admission date = the stay's own 99223 (updextrainsinfo hospitalizationfrom ONLY), full-visit resave insorder + onhcfa=1 (charge echo -
#   void trap), address line 1 moved up from line 2, then release from Unbilled. Six new charts the cascade could not insure only get the
#   address line 1 fix (claim readiness; chart 17478018 has no address at all -> the HCA placeholder) and stay in Unbilled (board rows).
#   pat25160: visit insorder "1" (Medicare only - the UHCMA plan ended 11/30/2025, AMD 271 INACTIVE; Medicare ACTIVE) + onhcfa=1, release.
#   pat17476358: patient order 2,3 (Medicare first, Sunshine MMA last; UNI20 ended 5/1/2026 and INACTIVE), three visits insorder 2,3 +
#   onhcfa=1 + admission date from the chart's most recent 99223 within 45 days (none -> inspector hold for William), release.
#   pat17477183: FL Medicaid 77027 INACTIVE at 10/5/2026 (Medicaid Pending not approved) -> the 10/5 visit moved to the patient balance
#   and released (William's PCC note 10/4: bill to patient, then write off no pay).
# Never touches: group numbers, hospitalizationto, payments, any other chart. Usage: python3 newcharts_1009_0510.py [--dry]
import amd, resave, add_ins, elig_amd, addr_line1_fix, dx_primary_fix, ins_update, patient_patch, txh, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
S = "2026-10-09T0510Z"; dry = "--dry" in sys.argv
amd.login_cached()
def L(m): print(m, flush=True)
SC = json.load(open("scan_%s/summary_before.json" % S)); rows = {r["id"]: r for r in SC["unbilled"]}
CFG = json.load(open("secrets/newcharts_1009_0510_cfg.json")); ADDR = json.load(open("secrets/newcharts_1009_0510_addr.json"))
REG = {"stamp": S, "dry": dry, "charts": {}, "released": []}
def set_admit(vid, code, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit))
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, ext))
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:160])
def resave_full(cid, insorder=None, onhcfa="1", to_patient=False):
    vis, pat, allc = resave.visit_charges(cid); chg = ""; moved = 0.0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if to_patient:
            ib = float(c.get("insbalance") or 0)
            if ib > 0:
                a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
                a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved += ib
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if onhcfa: va["onhcfa"] = onhcfa
    if insorder: va["insorder"] = str(insorder)
    if dry: return "DRY resave %d charges insorder %s->%s%s" % (len(allc), vis.get("insorder"), va.get("insorder"), " move %.2f to patient" % moved if to_patient else "")
    r = amd.post(amd.msg("updvisitwithnewcharges" if not to_patient else "updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.6)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return "ok insorder=%s onhcfa=%s hospfrom=%s live %d (was %d) bal %s" % (v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, len(c2), len(allc), [(c.get("insbalance"), c.get("patbalance")) for c in c2])
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
def vids_of(pid): return [r["id"] for r in SC["unbilled"] if r["patientid"] == pid and any("Insurance order" in e for e in r["_errs"])]
REL = []
# ---- A. three charts insured by the cascade ----
for pid, cfg in CFG.items():
    rec = {"added": [], "elig": [], "visits": {}, "addr": None, "why": cfg["why"]}
    L("--- pat%s (%s) ---" % (pid, cfg["why"]))
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
        msg, det = addr_line1_fix.fix(pid, *cfg["addr"], dry=dry); L("  addr: %s %s" % (msg, json.dumps(det)[:160])); rec["addr"] = msg
    except Exception as ex: L("  addr ERR %s" % str(ex)[:150]); rec["addr"] = "ERR " + str(ex)[:150]
    vids = vids_of(pid); seq, insid = seq_of(pid, cfg["bill"])
    if not seq and not dry: L("  NO open %s plan on chart -> HOLD" % cfg["bill"]); rec["hold"] = True; REG["charts"][pid] = rec; continue
    L("  bill seq %s (%s %s) visits %s" % (seq, cfg["bill"], insid, vids))
    for vid in vids:
        r = rows[vid]; cid = r["_chgs"][0]["id"]; codes = sorted({c["chgcode"] for c in r["_chgs"]}); vr = {}
        try: vr["dx"] = dx_gate(cid); L("  v%s %s" % (vid, vr["dx"][:300]))
        except Exception as ex: vr["dx"] = "DX ERR " + str(ex)[:150]; L("  v%s dx gate ERR %s" % (vid, str(ex)[:150]))
        adm = cfg["admit"]
        if adm is None: L("  v%s no admission date (nursing-facility 99306 visit, not a hospital stay)" % vid)
        elif not dry:
            for code in codes: res = set_admit(vid, code, adm); L("  v%s admit %s %s -> %s" % (vid, code, adm, res)); vr["admit_%s" % code] = res; time.sleep(0.3)
        else: L("  DRY v%s admit %s on %s" % (vid, adm, codes))
        vr["resave"] = resave_full(cid, insorder=seq); L("  v%s resave -> %s" % (vid, vr["resave"]))
        if vr["resave"].startswith("ok") or dry: REL.append(vid)
        rec["visits"][vid] = vr; time.sleep(0.4)
    REG["charts"][pid] = rec
# ---- B. six charts without insurance: address line 1 only ----
for pid, a in ADDR.items():
    try:
        if a[0] == "HCA":
            msg = "DRY placeholder" if dry else patient_patch.family_address(pid, "HCA", "", "32308-4486"); L("pat%s addr placeholder HCA -> %s" % (pid, str(msg)[:160]))
        else:
            msg, det = addr_line1_fix.fix(pid, *a, dry=dry); L("pat%s addr: %s %s" % (pid, msg, json.dumps(det)[:120]))
        REG["charts"][pid] = {"addr": str(msg)[:200], "hold": "no coverage found - board row"}
    except Exception as ex: L("pat%s addr ERR %s" % (pid, str(ex)[:150])); REG["charts"][pid] = {"addr": "ERR " + str(ex)[:150], "hold": "no coverage found - board row"}
    time.sleep(0.3)
# ---- C. pat25160: Medicare only ----
pid = "25160"; vid = "19457329"; cid = rows[vid]["_chgs"][0]["id"]
r = resave_full(cid, insorder="1"); L("pat25160 v%s resave insorder 1 -> %s" % (vid, r)); REG["charts"][pid] = {"resave": r}
if r.startswith("ok") or dry: REL.append(vid)
# ---- D. pat17476358: Medicare first, Sunshine last ----
pid = "17476358"; pl = plans(pid); med = [p for p in pl if p.get("carrier") == "car6085"][0]; sun = [p for p in pl if p.get("carrier") == "car6194"][0]
order = "%s,%s" % (med["sequence"], sun["sequence"]); rec = {"order": order, "visits": {}}
L("pat17476358 plans %s -> patient order %s" % ([(p.get("carrier"), p.get("sequence"), p.get("enddate")) for p in pl], order))
if not dry:
    try: L("  ins_update sequence -> %s" % str(ins_update.update(pid, med["id"], sequence=order))[:160])
    except Exception as ex: L("  ins_update ERR %s" % str(ex)[:160])
# admission anchor: most recent 99223 on the chart within 45 days of 10/5/2026
anchor = None
try:
    h = txh.fetch(pid); found = []
    for el in h.iter():
        a = el.attrib
        code = a.get("proccode") or a.get("chgcode") or a.get("cptcode") or a.get("code") or ""
        d = a.get("dos") or a.get("begindate") or a.get("date") or ""
        if "99223" in code and d: found.append(d.strip())
    L("  99223 dates on chart: %s" % found)
    for d in found:
        dd = datetime.datetime.strptime(d[:10], "%m/%d/%Y")
        if 0 <= (datetime.datetime(2026, 10, 5) - dd).days <= 45: anchor = d[:10]
except Exception as ex: L("  txh ERR %s" % str(ex)[:160])
for vid in vids_of(pid):
    cid = rows[vid]["_chgs"][0]["id"]; vr = {}
    if anchor and not dry:
        for code in sorted({c["chgcode"] for c in rows[vid]["_chgs"]}): vr["admit"] = set_admit(vid, code, anchor); L("  v%s admit %s -> %s" % (vid, anchor, vr["admit"]))
    vr["resave"] = resave_full(cid, insorder=order); L("  v%s resave -> %s" % (vid, vr["resave"])); rec["visits"][vid] = vr
    if vr["resave"].startswith("ok") or dry: REL.append(vid)
    time.sleep(0.4)
rec["anchor"] = anchor; REG["charts"][pid] = rec
# ---- E. pat17477183: no coverage after 8/31 -> patient balance ----
pid = "17477183"; vid = "19457365"; cid = rows[vid]["_chgs"][0]["id"]
r = resave_full(cid, insorder=None, onhcfa=None, to_patient=True); L("pat17477183 v%s -> patient balance: %s" % (vid, r)); REG["charts"][pid] = {"to_patient": r}
if r.startswith("ok") or dry: REL.append(vid)
L("release %d visits %s -> %s" % (len(REL), REL, release(REL)))
json.dump(REG, open("registers/newcharts_%s%s.json" % (S, "_dry" if dry else ""), "w"), indent=1)
L("=== done %s" % ("DRY" if dry else "LIVE"))
