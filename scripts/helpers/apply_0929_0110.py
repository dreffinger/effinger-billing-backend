# PLAIN ENGLISH (9 PM ET 9/28 slot, run 2026-09-29T0110Z): the run's AMD writes.
#  (1) pat20729: the Brynwood PCC census (Drive 'bht PCC Facesheets', printed 9/28 20:51) names 'Medicare A coinsurance from Medicaid,
#      Medicaid # <census Medicaid id ...004647>, SUNSHINE STATE' - Stedi Centene 68069 answers ACTIVE (Medicaid LTC Dual / SSHP LTC, plan begin 9/1/2026)
#      on that id and ERR 72 on the id read from the JPEG last run. Adds SUN01 (car6194) as the secondary (no group number), sets the
#      patient insurance order Medicare first / Sunshine second, runs AMD's free 271 on the new plan, and resaves her open unpaid
#      Medicare visits with insorder 1,2 (full charge echo) so the coinsurance crosses to Sunshine instead of the patient.
#  (2) Releases the seven Unbilled 'A payment from the prior payor is required' rows (rule b: the claim at the current payer is out and
#      unanswered - v19392347 BCBS secondary billed 9/21, v19441047 MCAD 5/26, v19442414 FLO02 9/5, pat24853 x4 HUM01 9/23).
# Never touches: payments, write-offs, hospitalizationto, the standing holds.
import amd, add_ins, ins_update, resave, era_post, re, json, time, sys
DRY = "--dry" in sys.argv
amd.login_cached(); batch = era_post.batch()
out = {"stamp": "2026-09-29T0110Z", "dry": DRY, "rossiter": {}, "released": [], "resaved": []}
def L(m): print(m, flush=True)
PID = "20729"
d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
have = [p for p in plans if p.get("carrier") == "car6194" and not p.get("enddate")]
if have:
    insid = have[0]["id"]; L("SUN01 already on chart: %s" % have[0]); out["rossiter"]["insid"] = insid
elif DRY:
    L("DRY: would add SUN01 <census Medicaid id ...004647> begin 09/01/2026"); insid = None
else:
    r = add_ins.add(PID, "car6194", open("local/pat20729_medicaid_ids.txt").read().split()[0], begindate="09/01/2026")
    L("add_ins -> %s" % str(r)[:300]); out["rossiter"]["add"] = str(r)[:300]
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    have = [p for p in plans if p.get("carrier") == "car6194" and not p.get("enddate")]
    insid = have[0]["id"] if have else None; out["rossiter"]["insid"] = insid
    L("plans now: %s" % [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("subscribernum")) for p in plans])
if insid and not DRY:
    seq = [p for p in plans if p.get("id") == insid][0].get("sequence")
    out["rossiter"]["seq"] = seq
    try:
        r = ins_update.update(PID, insid, sequence="1,%s" % seq); L("patient insorder 1,%s -> %s" % (seq, str(r)[:200])); out["rossiter"]["order"] = str(r)[:200]
    except Exception as e: L("insorder set failed: %s" % e); out["rossiter"]["order"] = "ERR %s" % e
    try:
        e = amd.check_eligibility(insid.replace("ins", "")); s = re.sub(r"\s+", " ", e)
        st = "ACTIVE" if re.search(r'EB\*1\*', s) else ("INACTIVE" if re.search(r'EB\*6\*', s) else ("REJECTED " + " ".join(re.findall(r'AAA\*[^~]*', s))[:80] if "AAA*" in s else "?"))
        L("AMD 271 SUN01 -> %s" % st); out["rossiter"]["elig271"] = st
    except Exception as ex: L("271 error %s" % ex); out["rossiter"]["elig271"] = "ERR %s" % ex
    # resave open unpaid Medicare visits with insorder 1,<seq>
    t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": PID, "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
    byv = {}
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("void") == "1" or not a.get("dos"): continue
        byv.setdefault(a.get("visit"), []).append(a)
    for vid, chs in byv.items():
        if any(float(c.get("paid") or 0) > 0 for c in chs): continue
        if not any(float(c.get("insbal") or 0) > 0 for c in chs): continue
        if not all(c.get("carrier") in ("FLO02", "", None) for c in chs): continue
        cid = chs[0]["id"]
        try:
            vis, pat, allc = resave.visit_charges(cid)
        except Exception as ex: L("v%s visit_charges failed %s" % (vid, ex)); continue
        if vis.get("insorder") == "1,%s" % seq: L("v%s already 1,%s" % (vid, seq)); continue
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = "1,%s" % seq
        vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
        r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
        time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid)
        ok = "Fault" not in r and len(c2) == len(allc)
        L("v%s resave insorder 1,%s -> %s live %d/%d insorder=%s dos=%s cpts=%s" % (vid, seq, "ok" if ok else re.sub(r"\s+"," ",r[:160]), len(c2), len(allc), v2.get("insorder"), chs[0].get("dos"), [c.get("proccode") for c in chs]))
        out["resaved"].append({"vid": vid, "ok": ok, "live": len(c2), "was": len(allc), "insorder": v2.get("insorder")})
        time.sleep(0.4)
# (2) release the prior-payor rows
REL = ["19392347","19441047","19442414","19453094","19453102","19453106","19453209"]
if DRY: L("DRY: would release %s" % REL)
else:
    x = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in REL)), timeout=120)
    ok = "Fault" not in x; L("hideunbillablevisits x%d -> %s" % (len(REL), "ok" if ok else re.sub(r"\s+"," ",x[:200]))); out["released"] = REL if ok else []; out["release_result"] = re.sub(r"\s+"," ",x[:200])
json.dump(out, open("registers/apply_2026-09-29T0110Z%s.json" % ("_dry" if DRY else ""), "w"), indent=1)
L("DONE")
