#!/usr/bin/env python3
# PLAIN ENGLISH (Pam's PCC admission record -> chart 17478318 made claim-ready, 1:39 PM ET 11/11 columns run, fired 18:39Z)
# Decides: nothing new. Pam's admit email of 17:49Z 11/11 (Westminster Oaks SNF, admitted 11/10/2026 from Capital Regional) carries
#   the PCC Clinical Resident Profile: Primary Payer CAPITAL HEALTH PLAN, policy on the sheet, Medicare HIC listed, 'Managed Care
#   coinsurance from private' as the second payer. Stedi 95112 at DOS 11/07/2026 answers Active Coverage, HMO, COMMERCIAL, plan
#   begin 10/01/2018 (the payer echoes the member id with its CHP prefix). The chart's only plan was Cigna DENTAL (the 11/5 feed
#   discovery hit) - four of the six HCA visits (11/05-11/08) went to it and the 11/07 claim bounced (run 1700365).
# Does, in order: add_ins CAP07 with the CHP member id (begin 10/01/2018, no group); end-date the Cigna dental plan 11/02/2026
#   (the day before the first DOS) and re-set the patient order to the new plan (an end-date edit blanks insorder); each of the
#   six visits resaved with the FULL charge echo (void trap) carrying insorder = new seq, onhcfa=1 and its own
#   hospitalizationfrom (11/04/2026 from the feed = the HCA census admission; the 11/03 99223 is the ED/admit-day visit); freq1_visit.run on every visit (originals to CHP); AMD 271 on the new plan.
# Rules it uses: one AMD login (amd.login_cached); member id read from secrets/run_1839_ids.json, never printed; never rebill a
#   visit with a payment (none here - checked live). Never touches: payments, write-offs, other charts, the exclusion row (done after).
# Usage: python3 grantham_1111_1839.py [--live]   register: registers/grantham_2026-11-11T1839Z[_dry].json
import sys, re, json, time, amd, add_ins, ins_update, resave, era_post, freq1_visit, txh
LIVE = "--live" in sys.argv; STAMP = "2026-11-11T1839Z"
PID = "17478318"; DENTAL_INS = "ins9521148"; DENTAL_END = "11/02/2026"
HOSP = None  # keep each visit's own admission date (the feed wrote 11/04/2026 = the HCA census admission)
CAR = "car41826"  # CAP07 CAPITAL HEALTH PLAN (carriers.json)
ids = json.load(open("secrets/run_1839_ids.json"))
out = {"stamp": STAMP, "pid": PID, "live": LIVE, "steps": []}
def step(k, v): out["steps"].append({k: v}); print(k, "->", (str(v)[:300]))
amd.login_cached()
# live charges: visit -> charge ids, refuse any visit carrying a payment
vis = {}
for c in txh.fetch(PID).iter("charge"):
    a = c.attrib
    if a.get("void") in ("1", "true"): continue
    pays = [p for p in c.iter("payment") if p.get("void") not in ("1", "true")]
    vis.setdefault(a["visit"], {"charges": [], "paid": 0})["charges"].append(a["id"])
    vis[a["visit"]]["paid"] += len(pays)
step("visits", {v: d for v, d in vis.items()})
plans = re.findall(r'<insplan [^>]*/?>', amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + PID, "nocookie": "1"})))
step("plans_before", [re.sub(r'subscribernum="[^"]*"', 'subscribernum="<id>"', p)[:120] for p in plans])
if not LIVE:
    step("plan", "DRY: add_ins %s begin %s; end-date %s %s; patient order = new seq; resave %d visits insorder/onhcfa (own hospfrom kept); freq1 each; 271" % (CAR, ids["begindate"], DENTAL_INS, DENTAL_END, len(vis)))
    for vid, d in vis.items():
        v, p, allc = resave.visit_charges(d["charges"][0]); ex = v.find("extins")
        step("visit_%s" % vid, "insorder=%s onhcfa=%s hospfrom=%s live_charges=%d paid=%d" % (v.get("insorder"), v.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, len(allc), d["paid"]))
else:
    insid, seq = add_ins.add(PID, CAR, ids["member"], begindate=ids["begindate"])
    step("add_ins", "ins %s seq %s" % (insid, seq)); time.sleep(0.5)
    r = ins_update.update(PID, DENTAL_INS, enddate=DENTAL_END); step("dental_enddate", str(r)[:160]); time.sleep(0.5)
    r = ins_update.update(PID, insid, sequence=str(seq)); step("patient_order", str(r)[:160]); time.sleep(0.5)
    dem = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + PID, "nocookie": "1"}))
    m = re.search(r'<patient [^>]*insorder="([^"]*)"', dem); step("insorder_readback", m.group(1) if m else None)
    batch = era_post.batch()
    for vid, d in vis.items():
        if d["paid"]: step("visit_%s" % vid, "SKIP has payment"); continue
        cid = d["charges"][0]
        v, p, allc = resave.visit_charges(cid)
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, val) for k, val in a.items())
        va = dict(v.attrib); va.update({"force": "1", "insorder": str(seq), "onhcfa": "1"})
        vs = " ".join('%s="%s"' % (k, val) for k, val in va.items())
        r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
            {"patientid": p.get("id"), "episodeid": v.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch),
             "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
            "<visit %s><chargelist>%s</chargelist>%s</visit>" % (vs, chg, resave._extins_xml(v, (v.find("extins").get("hospitalizationfrom") if v.find("extins") is not None else "") or "11/04/2026"))))
        if "Fault" in r: step("visit_%s" % vid, "FAULT " + re.sub(r"\s+", " ", r[:300])); continue
        time.sleep(0.8)
        v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
        ok = len(c2) == len(allc) and (v2.get("insorder") or "") == str(seq)
        step("visit_%s" % vid, "saved live=%d/%d insorder=%s onhcfa=%s hospfrom=%s %s" % (len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, "OK" if ok else "VERIFY FAILED"))
        if not ok: continue
        try:
            rr = freq1_visit.run(vid, cid, seq); step("rebill_%s" % vid, str(rr)[:160])
        except Exception as e: step("rebill_%s" % vid, "ERR %s" % e)
        time.sleep(0.5)
    try:
        e = amd.check_eligibility(insid.replace("ins", "")); step("amd_271", re.sub(r"\s+", " ", str(e))[:400])
    except Exception as e: step("amd_271", "ERR %s" % e)
json.dump(out, open("registers/grantham_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
