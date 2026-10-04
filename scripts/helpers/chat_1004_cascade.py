# PLAIN ENGLISH (Chat session 10/4/2026 - the insurance cascade on the Unbilled 'Insurance order is missing' charts William asked to be worked)
# Decides, per chart with no billable plan: (1) plans already on the chart -> AMD's free 271; an ACTIVE plan is the payer; (2) Stedi MBI lookup
#   (with the chart SSN when lookuppatient has one): straight Medicare -> FLO02 added; a Medicare Advantage entity on the record -> the MA
#   member id is needed (discovery tries to return it; otherwise the row goes to William); (3) not a Medicare beneficiary -> Stedi discovery
#   -> a found commercial/Medicaid plan is added when its payer maps to an AMD carrier; (4) nothing -> the row stays on William's turn.
#   Then every open visit gets the plan's sequence as its insurance order (full-visit echo) and is released from Unbilled; a blank address
#   line 1 gets the street from line 2 or the SNF/ALF/HCA placeholder (William's rule).
# Specials tonight: Whitlow (known self-pay, trust invoice) -> patient balance + release; Whitfield + Vance (William: void anything dated after
#   the date of death / delete the duplicate CCM lines); Osgood duplicate chart -> plans copied from the real chart (the Jarvis recipe).
# Never touches: paid charges, group numbers.  Usage: cd /home/claude/unbilled && python3 chat_1004_cascade.py [--dry] [--only pid,pid]
import amd, resave, add_ins, ins_update, elig_amd, stedi, patient_patch, addr_line1_fix, freq1_visit, void_tx
import re, sys, json, time, datetime, os
import xml.etree.ElementTree as ET
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, out, chart_rows, live, plans, fmt, full_resave, release_unbilled, void_charge, NOTE, DRY, ONLY
PAYER_CAR = {"HUMANA": "car6285", "UNITEDHEALTHCARE DUAL": "car302853", "UNITED HEALTHCARE": "car6404", "UNITEDHEALTHCARE": "car6404", "UHC": "car6404", "AETNA": "car6047", "CAPITAL HEALTH": "car41826",
             "FLORIDA BLUE": "car6062", "BLUE CROSS": "car6062", "BCBS": "car6062", "SUNSHINE": "car6194", "AMBETTER": "car6802", "SIMPLY": "car42019", "WELLCARE": "car6174", "FLORIDA COMMUNITY CARE": "car42008",
             "MEDICAID": "car6113", "CHLIC": "car6687", "CIGNA HEALTHSPRING": "car42014", "CIGNA": "car6687", "TRICARE": "car6872", "AARP": "car6600"}
FAC_PLACE = {"fac29": "HCA", "fac30": "HCA", "fac67": "HCA"}
def car_for(name):
    n = (name or "").upper()
    for k, v in PAYER_CAR.items():
        if k in n: return v
    return None
def ssn_of(name):
    try:
        last, first = (name.split(",") + [""])[:2]
        t = amd.post(amd.msg("lookuppatient", "lookup", {"name": "%s,%s%%" % (last.strip(), first.strip()[:3]), "nocookie": "1"}))
        t = t.encode("latin-1", "ignore").decode("latin-1")
        for m in re.finditer(r'<patient [^>]*>', t):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
            s = (a.get("ssn") or "").replace("-", "")
            if len(s) == 9 and s.isdigit() and s != "000000000": return s
    except Exception: pass
    return None
def set_order_release(pid, rows, seq, extra_over=None):
    res = []; vids = sorted({r["visit"] for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0})
    for vid in vids:
        cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
        if vis.get("insorder") == str(seq) and not extra_over: res.append("v%s already insorder %s" % (vid, seq)); continue
        over = {"insorder": str(seq)}; over.update(extra_over or {})
        ok, msg = full_resave(cid, over=over); res.append("v%s insorder %s: %s %s" % (vid, seq, ok, msg[:140]))
    if vids: res.append(release_unbilled(vids))
    return res
def fix_address(pid, rows):
    try:
        p = patient_patch.get(pid); a = p.get("currentaddress") or {}
        if (a.get("address1") or "").strip(): return "address ok: %s" % a.get("address1")
        fac = ""
        for r in live(rows):
            try: fac = resave.visit_charges(r["id"])[0].get("facility") or ""; break
            except Exception: pass
        street = (a.get("address2") or "").strip() or FAC_PLACE.get(fac, "SNF" if fac in ("fac34", "fac32", "fac33", "fac1350", "fac31", "fac35", "fac66", "fac1351", "fac58") else "ALF")
        if DRY: return "DRY address line 1 -> %s" % street
        r = addr_line1_fix.fix(pid, street, a.get("city") or "TALLAHASSEE", a.get("state") or "FL", a.get("zipcode") or "32308-4486")
        return "address line 1 -> %s: %s" % (street, str(r)[:120])
    except Exception as e: return "address check failed %s" % e
def cascade(pid):
    res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    name = pa.get("name", ""); dob = pa.get("dob", ""); dob8 = dob[6:] + dob[:2] + dob[3:5] if len(dob) == 10 else ""
    last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    res.append("%s dob %s plans %s insorder %s | open %s" % (name, dob, [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("enddate")) for p in pl], pa.get("insorder"), [fmt(r) for r in opens]))
    if not opens: res.append("nothing open"); return res, None
    dos = opens[0]["dos"]; dos8 = dos[6:] + dos[:2] + dos[3:5]
    # 1. plans on the chart
    for p in pl:
        if p.get("enddate"): continue
        try: s = elig_amd.run_plan(pid, p["id"].replace("ins", ""), True); line = elig_amd.one_line(s); res.append("AMD 271 %s %s: %s" % (p.get("carrier"), p.get("subscribernum"), line[:200]))
        except Exception as e: res.append("271 failed %s" % e); continue
        if s.get("status") == "ACTIVE" and not s.get("date_of_death"):
            res += set_order_release(pid, rows, p["sequence"]); res.append(fix_address(pid, rows)); return res, ("plan", p["sequence"])
    # 2. Medicare record
    ssn = ssn_of(name); sm = None
    try:
        j = stedi.mbi(first, last, dob8, state="FL", dos=dos8, ssn=ssn); sm = stedi.med_summ(j); res.append("Stedi MBI lookup (%s): %s" % ("with SSN" if ssn else "name/DOB/FL", json.dumps(sm)[:420]))
    except Exception as e: res.append("Stedi MBI lookup failed %s" % e)
    if sm and sm.get("mbi") and not sm.get("errors"):
        if sm.get("death") and sm["death"] < dos8: res.append("DATE OF DEATH %s before the DOS - nothing billed, William's call" % sm["death"]); return res, ("deceased", sm["death"])
        def is_pd(o): return (o.get("type") or "") == "OT" or any(re.search(r"PRESCRIPTION|PDP|\bRX\b|DRUG", (e[0] or "").upper()) for e in o.get("entity") or [])
        ma = [o for o in sm.get("other") or [] if o.get("code") in ("U", "R") and (o.get("type") or "") in ("HM", "HN", "PS", "PR", "MC") and not is_pd(o) and any(e[0] for e in o.get("entity") or [])]
        hospice = [o for o in sm.get("other") or [] if "45" in str(o)]
        if ma:
            ent = [e for o in ma for e in (o.get("entity") or []) if e[0]]; res.append("Medicare Advantage on the record: %s dates %s" % (ent, [o.get("dates") for o in ma]))
            car = car_for(ent[0][0] if ent else "")
            fam = {"car6194": {"car6194", "car6174"}, "car6174": {"car6194", "car6174"}}.get(car, {car})
            if car == "car6194": car = "car6174"   # a Medicare Advantage entity named Sunshine = Wellcare by Allwell -> the WellCare MA carrier, never the Medicaid one
            # discovery may return the MA member id
            try:
                dj = stedi.disc(first, last, dob8, "FL", dos8); items = dj.get("items") or []
                res.append("discovery: coveragesFound %s %s" % (dj.get("coveragesFound"), [((i.get("payer") or {}).get("name"), (i.get("subscriber") or {}).get("memberId"), (i.get("planDateInformation") or {})) for i in items][:4]))
                hit = next((i for i in items if (i.get("subscriber") or {}).get("memberId") and car_for((i.get("payer") or {}).get("name")) in fam), None)
                if hit and car:
                    mid = hit["subscriber"]["memberId"]; begin = ((hit.get("planDateInformation") or {}).get("planBegin") or "")
                    bd = "%s/%s/%s" % (begin[4:6], begin[6:], begin[:4]) if re.match(r"\d{8}$", begin) else "01/01/2025"
                    if DRY: res.append("DRY add %s %s begin %s" % (car, mid, bd)); return res, ("dry", car)
                    iid, seq = add_ins.add(pid, car, mid, bd); res.append("added %s %s -> %s seq %s" % (car, mid, iid, seq)); rec("addplan", "cascade:" + pid, bool(iid))
                    res += set_order_release(pid, rows, seq); res.append(fix_address(pid, rows)); return res, ("plan", seq)
            except Exception as e: res.append("discovery failed %s" % e)
            return res, ("ma-id-needed", ent)
        # straight Medicare
        if DRY: res.append("DRY add FLO02 %s" % sm["mbi"]); return res, ("dry", "car6085")
        iid, seq = add_ins.add(pid, "car6085", sm["mbi"], "01/01/2025"); res.append("added FLO02 %s -> %s seq %s" % (sm["mbi"], iid, seq)); rec("addplan", "cascade:" + pid, bool(iid))
        try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", iid), True); res.append("AMD 271 FLO02: " + elig_amd.one_line(s)[:200])
        except Exception as e: res.append("271 failed %s" % e)
        res += set_order_release(pid, rows, seq); res.append(fix_address(pid, rows)); return res, ("plan", seq)
    # 3. not Medicare -> discovery
    try:
        dj = stedi.disc(first, last, dob8, "FL", dos8); items = dj.get("items") or []
        res.append("discovery: coveragesFound %s %s" % (dj.get("coveragesFound"), [((i.get("payer") or {}).get("name"), (i.get("subscriber") or {}).get("memberId"), (i.get("planDateInformation") or {}), [b.get("name") for b in (i.get("benefitsInformation") or [])[:2]]) for i in items][:4]))
        for i in items:
            payer = (i.get("payer") or {}).get("name"); mid = (i.get("subscriber") or {}).get("memberId"); car = car_for(payer)
            active = any(b.get("code") == "1" for b in (i.get("benefitsInformation") or [])) or "Active" in json.dumps(i)
            if car and mid and active:
                begin = ((i.get("planDateInformation") or {}).get("planBegin") or ""); bd = "%s/%s/%s" % (begin[4:6], begin[6:], begin[:4]) if re.match(r"\d{8}$", begin) else "01/01/2025"
                if DRY: res.append("DRY add %s %s (%s) begin %s" % (car, mid, payer, bd)); return res, ("dry", car)
                iid, seq = add_ins.add(pid, car, mid, bd); res.append("added %s %s (%s) -> %s seq %s" % (car, mid, payer, iid, seq)); rec("addplan", "cascade:" + pid, bool(iid))
                try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", iid), True); res.append("AMD 271: " + elig_amd.one_line(s)[:200])
                except Exception as e: res.append("271 failed %s" % e)
                res += set_order_release(pid, rows, seq); res.append(fix_address(pid, rows)); return res, ("plan", seq)
    except Exception as e: res.append("discovery failed %s" % e)
    return res, ("human", "facesheet / card needed")

def copy_plans(dup, real):
    """the Jarvis recipe: plans from the real chart onto the duplicate, DOB aligned, visits ordered and released"""
    res = []; pa_r, pl_r = plans(real); pa_d, pl_d = plans(dup); rows = chart_rows(dup)
    res.append("real %s dob %s insorder %s plans %s | dup %s dob %s plans %s" % (pa_r.get("name"), pa_r.get("dob"), pa_r.get("insorder"), [(p.get("carrier"), p.get("subscribernum"), p.get("sequence"), p.get("enddate")) for p in pl_r], pa_d.get("name"), pa_d.get("dob"), [(p.get("carrier"), p.get("subscribernum")) for p in pl_d]))
    order = []
    for s in (pa_r.get("insorder") or "").split(","):
        p = next((q for q in pl_r if q.get("sequence") == s.strip() and not q.get("enddate")), None)
        if not p: continue
        have = [q for q in pl_d if q.get("carrier") == p.get("carrier") and q.get("subscribernum") == p.get("subscribernum")]
        if have: order.append(have[0]["sequence"]); continue
        if DRY: res.append("DRY add %s %s" % (p.get("carrier"), p.get("subscribernum"))); continue
        iid, seq = add_ins.add(dup, p.get("carrier"), p.get("subscribernum"), p.get("begindate") or "01/01/2025"); res.append("added %s %s -> %s seq %s" % (p.get("carrier"), p.get("subscribernum"), iid, seq))
        if seq: order.append(seq)
    if order and not DRY:
        pa_d, pl_d = plans(dup); fid = [p for p in pl_d if p.get("sequence") == order[0]][0]["id"]
        ok, msg = ins_update.update(dup, fid, sequence=",".join(order)); res.append("patient order %s: %s" % (",".join(order), ok))
        res += set_order_release(dup, rows, ",".join(order))
    return res

def prim():
    """pat17476358: Medicare ACTIVE (QMB) seq 2 + Sunshine Medicaid seq 3 - order 2,3; May-2026 coinsurance sitting on the patient goes to Sunshine (crossover); Oct visits released Medicare first"""
    pid = "17476358"; rows = chart_rows(pid); res = []; import move_to_ins
    for r in live(rows):
        if float(r.get("patbal") or 0) > 0 and [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]:
            res.append("coinsurance on the patient: " + fmt(r))
            if DRY: continue
            m = move_to_ins.move(r["id"], "2,3", rebill_seq=3); res.append("   " + str(m)[:160]); time.sleep(0.4)
    new = sorted({r["visit"] for r in live(rows) if not r.get("billdate") and float(r.get("insbal") or 0) > 0})
    for vid in new:
        cid = live(rows, vid=vid)[0]["id"]; ok, msg = full_resave(cid, over={"insorder": "2,3", "onhcfa": "1"}); res.append("v%s insorder 2,3: %s %s" % (vid, ok, msg[:120]))
    if new: res.append(release_unbilled(new))
    res.append(fix_address(pid, rows)); return res
def smythe_myra():
    """pat17477933 carries the 01/01/1900 placeholder DOB (Pruitt pattern) - find the real SMYTHE,MYRA chart and copy its plans"""
    res = []; t = amd.post(amd.msg("lookuppatient", "lookup", {"name": "SMYTHE,MYRA%", "nocookie": "1"})).encode("latin-1", "ignore").decode("latin-1")
    charts = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<patient [^>]*>', t)]
    res.append("lookuppatient SMYTHE,MYRA%%: %s" % [(c.get("id"), c.get("name"), c.get("dob")) for c in charts])
    real = [c for c in charts if re.sub(r"\D", "", c.get("id", "")) != "17477933" and not c.get("dob", "").startswith("01/01/1900")]
    if not real: res.append("no other SMYTHE,MYRA chart - facesheet needed"); return res
    rid = re.sub(r"\D", "", real[0]["id"]); pa, pl = plans(rid); res.append("real chart %s dob %s plans %s" % (rid, pa.get("dob"), [(p.get("carrier"), p.get("subscribernum"), p.get("enddate")) for p in pl]))
    if not [p for p in pl if not p.get("enddate")]: res.append("the real chart has no active plan either - cascade it next"); return res
    res += copy_plans("17477933", rid)
    if not DRY:
        try:
            p = patient_patch.get("17477933"); orig = patient_patch.flatten(p); import copy, requests
            upd = copy.deepcopy(orig); upd["dob"] = (patient_patch.get(rid).get("dob") or ""); upd["updateaccounttype"] = False
            a = patient_patch.get(rid).get("currentaddress") or {}
            new = {"address1": a.get("address1") or "SNF", "address2": a.get("address2") or "", "zipcode": a.get("zipcode") or "32308-4486", "city": a.get("city") or "TALLAHASSEE", "state": a.get("state") or "FL", "countrycode": "USA"}
            upd.update(new)
            for n in upd.get("names", []): n.setdefault("prefixSuffix", {"prefix": n.get("prefix") or "", "suffix": n.get("suffix") or ""})
            body = {"updatedpatient": upd, "originalpatient": orig, "updateaccounttype": False, "familyupdate": {"capturepreviousaddress": False, "responsiblepartyid": orig["responsiblepartyfid"], "patientids": [0], "homephone": orig.get("homephone") or "", "newaddress": new}, "deleteappointments": False}
            web, tok = amd.login_cached(); r = requests.patch(patient_patch.H % "17477933", json=body, timeout=60, headers={"Authorization": "Bearer " + tok, "Accept": patient_patch.ACC, "Content-Type": "application/json", "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"})
            res.append("DOB patch -> %s %s" % (r.status_code, r.text[:80]))
        except Exception as e: res.append("DOB patch failed %s" % e)
    return res
def probes():
    res = []
    for label, payer, first, last, dob8, mid, dos in (("zippay Aetna 60054 W299825621", "60054", "EVIE", "ZANE", "19430707", "W299825621", "20260930"), ("will CHP 95112 by name/DOB", "95112", "CATHLEEN", "WILLOUGHBY", "19570627", None, "20260922"), ("zippay CHP 95112 by name/DOB", "95112", "EVIE", "ZANE", "19430707", None, "20260930")):
        try:
            body = {"tradingPartnerServiceId": payer, "provider": stedi.PROV, "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob8}, "encounter": {"dateOfService": dos, "serviceTypeCodes": ["30"]}}
            if mid: body["subscriber"]["memberId"] = mid
            j = stedi._post(stedi.API + "/change/medicalnetwork/eligibility/v3", body); sub = j.get("subscriber") or {}
            res.append("%s: errors %s member %s plan %s dates %s" % (label, [(e.get("code"), e.get("description")) for e in j.get("errors") or []], sub.get("memberId"), [(b.get("name"), b.get("insuranceTypeCode"), b.get("planCoverage")) for b in (j.get("benefitsInformation") or [])[:4]], j.get("planDateInformation")))
        except Exception as e: res.append("%s: failed %s" % (label, str(e)[:120]))
    return res

def main():
    amd.login_cached()
    if not ONLY or "probes" in ONLY:
        L("== probes"); [L("   " + x) for x in probes()]
    if not ONLY or "17476358" in ONLY:
        L("== prim 17476358"); r = prim(); [L("   " + x) for x in r]; out("prim", lines=r)
    if not ONLY or "17477933" in ONLY:
        L("== smith myrtle 17477933"); r = smythe_myra(); [L("   " + x) for x in r]; out("smythe_myra", lines=r)
    plan = {"17477971": "MACFARLANE,PAULINA", "17477972": "HERRIOT,SONNIE", "17477973": "ZANE,EVIE", "17477974": "TISDALE,MICAH", "17477975": "SINGER,MICAH", "17477898": "WILLOUGHBY,CATHLEEN"}
    for pid, nm in plan.items():
        if ONLY and pid not in ONLY: continue
        L("== cascade pat%s %s%s" % (pid, nm, " (DRY)" if DRY else ""))
        try:
            res, verdict = cascade(pid)
            for x in res: L("   " + x)
            L("   VERDICT %s" % (verdict,)); out("cascade:" + pid, lines=res, verdict=verdict)
        except Exception as e:
            import traceback; L("   EXCEPTION %s" % traceback.format_exc()[-500:]); out("cascade:" + pid, error=str(e)[:200])
    if not ONLY or "17477870" in ONLY:
        L("== osborn duplicate chart 17477870 <- 17470849")
        try: res = copy_plans("17477870", "17470849"); [L("   " + x) for x in res]; out("osborn", lines=res)
        except Exception as e: L("   EXCEPTION %s" % e)
    if not ONLY or "17477639" in ONLY:
        L("== whitson 17477639 self-pay (trust invoice) -> patient balance + release")
        rows = chart_rows("17477639"); res = []
        for r in live(rows):
            if float(r.get("insbal") or 0) <= 0: continue
            vis, pat, allc = resave.visit_charges(r["id"]); chg = ""
            for c in allc:
                a = {"id": c.get("id")}
                for f in resave.CHG_FIELDS:
                    if c.get(f) is not None: a[f] = c.get(f)
                ib = float(c.get("insbalance") or 0)
                if ib > 0: a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"; a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"
                chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
            if DRY: res.append("DRY v%s -> patient balance" % r["visit"]); continue
            va = dict(vis.attrib); va["force"] = "1"
            x = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
            res.append("v%s -> patient balance: %s" % (r["visit"], "ok" if "Fault" not in x else "FAULT " + x[:120])); time.sleep(0.6)
        if not DRY: res.append(release_unbilled(sorted({r["visit"] for r in live(rows)})))
        [L("   " + x) for x in res]; out("whitson", lines=res)
    if not ONLY or "17473232" in ONLY:
        L("== whitehouse 17473232 - CCM 9/20/2026 after the 06/02/2026 date of death -> void (William 10/4: void anything dated after the date of death)")
        rows = chart_rows("17473232"); res = []
        for r in live(rows):
            if datetime.datetime.strptime(r["dos"], "%m/%d/%Y").date() > datetime.date(2026, 6, 2) and float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0:
                res.append("post-death: " + fmt(r)); void_charge("whitehouse", "17473232", r["id"])
        [L("   " + x) for x in res]; out("whitehouse", lines=res)
    if not ONLY or "17477208" in ONLY:
        L("== vaughn 17477208 - v19455940 duplicates v19455939 (same 9/20/2026 CCM, lines doubled) -> void the duplicate visit's lines")
        rows = chart_rows("17477208"); res = []
        keep = live(rows, vid="19455939"); dup = live(rows, vid="19455940")
        res.append("keep v19455939 %s | dup v19455940 %s" % ([fmt(r) for r in keep], [fmt(r) for r in dup]))
        if keep and dup:
            for r in dup:
                if [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]: res.append("payment on %s - left" % r["id"]); continue
                void_charge("vaughn", "17477208", r["id"])
        [L("   " + x) for x in res]; out("vaughn", lines=res)
    L("== cascade done")
if __name__ == "__main__": main()
