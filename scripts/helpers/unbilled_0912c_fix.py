# PLAIN ENGLISH (Unbilled 'Insurance order is missing' fix from William's board notes, 9/12/2026 5am ET run)
# Decides: for each of the four new HCA admits whose facesheet text William pasted into the Insurance Refresh Board
#   row (08:55-09:25 UTC 9/12): (1) add the plan the facesheet names if it is not already on the chart (no group number),
#   (2) fix the address when line 1 is blank (the real street sat in line 2), (3) resave every open visit with the plan's
#   sequence as insorder (+ VA preauth for the VA CCN patient, onhcfa=1), (4) write the admission date (99223 DOS) into
#   extra-insurance info, (5) run AMD's free 271 on the new plan, (6) release the visits from Unbilled.
# Rules it uses: full-visit echo (never a single-charge resave); MA plan = the only plan, primary; VA member id = ICN,
#   auth = the VA-prefixed value before the slash; skip any write whose pre-state already shows the fix (a parallel
#   copy of this routine may have done it minutes earlier).
# Never touches: payments, other patients, existing plans.
import amd, resave, add_ins, patient_patch, elig_amd, txh, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
amd.login_cached()
DRY = "--dry" in sys.argv
LOG = open("unbilled_0912c_fix.log", "a")
def L(m): print(m, flush=True); LOG.write("%s %s\n" % (datetime.datetime.utcnow().strftime("%H:%M:%S"), m)); LOG.flush()

# Member numbers, auths and addresses are PHI: they live in plan_0912c.json in the workspace (never mirrored), keyed by
# patient id with fields tag, car, num, begin, addr [line1, line2, zip, city, state], preauth, admit, src.
import os
PLAN = json.load(open("plan_0912c.json")) if os.path.exists("plan_0912c.json") else {}
for _p in PLAN.values(): _p["addr"] = tuple(_p["addr"])
only = [a for a in sys.argv[1:] if a.isdigit()]
if only: PLAN = {k: v for k, v in PLAN.items() if k in only}

def demog(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<insplan ([^>]*)>', r)]
    return r, plans

def set_admit(vid, vis, codes, admit):
    e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
    for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
    base["hospitalizationfrom"] = admit
    base = resave.clean_extins(base)
    out = []
    for pc in sorted(codes):
        base["txtChargeCode"] = pc
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, val) for k, val in base.items())))
        out.append("fault" if "Fault" in r else "ok")
    return out

def resave_visit(cid, seq, preauth):
    vis, pat, allc = resave.visit_charges(cid)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = str(seq); va["onhcfa"] = "1"
    if preauth: va["preauth"] = preauth
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if DRY: return "DRY resave %s charges insorder=%s preauth=%s" % (len(allc), seq, preauth)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:300])
    return "resaved %d charges" % len(allc)

release = []
summary = {}
for pid, P in PLAN.items():
    L("===== %s (%s) - %s" % (P["tag"], P["car"], P["src"]))
    # 1. plan
    raw, plans = demog(pid)
    have = [p for p in plans if (p.get("subscribernum") or "").upper() == P["num"].upper() and not p.get("enddate")]
    if have:
        insid, seq = have[0]["id"], have[0]["sequence"]; L("plan already on chart: %s seq %s (skip add)" % (insid, seq))
    elif DRY:
        insid, seq = "DRY", "1"; L("DRY would add %s %s" % (P["car"], P["num"]))
    else:
        insid, seq = add_ins.add(pid, P["car"], P["num"], P["begin"])
        L("addinsurance -> %s seq %s" % (insid, seq))
        if not insid: L("ABORT patient: add failed"); continue
    live = [p for p in plans if not p.get("enddate")]
    if len(live) > (0 if not have else 1): L("NOTE other live plans on chart: %s" % [(p.get("id"), p.get("carrier"), p.get("sequence")) for p in live if p is not (have[0] if have else None)])
    # 2. address
    try:
        cur = (patient_patch.get(pid).get("currentaddress") or {})
        if not (cur.get("address1") or "").strip():
            a1, a2, z, city, st = P["addr"]
            if DRY: L("DRY would set address %s" % (P["addr"],))
            else:
                code, txt, after = patient_patch.family_address(pid, a1, a2, z, city, st)
                L("address PATCH %s -> %s" % (code, after))
        else:
            L("address line 1 already set: %s" % cur.get("address1"))
    except Exception as e:
        L("address ERR %s" % str(e)[:200])
    # 3./4. visits
    root = txh.fetch(pid)
    visits = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        if float(c.get("insbal") or c.get("insbalance") or 0) + float(c.get("patbal") or c.get("patbalance") or 0) <= 0: continue
        visits.setdefault(c.get("visit"), []).append(c)
    L("open visits: %s" % {v: [(c.get("id"), c.get("proccode"), c.get("dos")) for c in cs] for v, cs in visits.items()})
    done = []
    for vid, cs in sorted(visits.items()):
        cid = cs[0].get("id")
        codes = {c.get("proccode") for c in cs}
        res = resave_visit(cid, seq, P["preauth"]); L("visit %s %s" % (vid, res))
        if res.startswith("FAULT"): continue
        if not DRY:
            time.sleep(0.6)
            vis, pat, allc = resave.visit_charges(cid)
            L("  admit date -> %s" % set_admit(vid, vis, codes, P["admit"]))
            time.sleep(0.4)
            x = resave.detail(cid); v2 = re.search(r'<visit [^>]*>', x).group(0)
            rb = dict(re.findall(r'(insorder|preauth|onhcfa|refplan)="([^"]*)"', v2))
            hf = re.search(r'hospitalizationfrom="([^"]*)"', x)
            L("  readback %s hospfrom=%s charges_live=%d" % (rb, hf.group(1) if hf else None, len(allc)))
            if rb.get("insorder", "").startswith(str(seq)): done.append(vid)
    # 5. eligibility
    try:
        if not DRY and insid and insid != "DRY":
            s = elig_amd.run_plan(pid, insid.replace("ins", ""), True); L("AMD 271 %s: %s" % (insid, elig_amd.one_line(s)))
    except Exception as e:
        L("elig ERR %s" % str(e)[:200])
    summary[pid] = {"insid": insid, "seq": seq, "visits_fixed": done}
    release += done
# 6. release
if release and not DRY:
    for i in range(0, len(release), 40):
        chunk = release[i:i+40]
        r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in chunk)))
        L("hideunbillablevisits n=%d -> %s" % (len(chunk), "fault " + r[:200] if "Fault" in r else "ok"))
json.dump(summary, open("unbilled_0912c_summary.json", "w"), indent=1)
L("summary %s" % summary)
