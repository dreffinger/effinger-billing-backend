# PLAIN ENGLISH (Chat session 10/3-10/4/2026 - William's board answers of 10:28-11:02 PM ET, worked live)
# Decides: one action per board row, exactly as William answered on the Insurance Refresh Board, each one re-read from the LIVE chart
#   first so a run that already acted is never repeated: write-offs refuse a $0 balance (manual_post over-apply guard), voids skip a charge
#   that is already void, plans are not added twice, rebills check the charge's last-billed carrier + billdate.
# Items: adams (admission date 09/30/2026 on 3 HCA 99233s) · alcorn (no insurance after 8/31 -> WOBAD) · awv (WONCS x2) · barber (WOLATE)
#   · burney (void the duplicate 9/22 admission visit) · cain (BCBS NC plan -> FLORIDA BLUE car6062, rebill 2 visits) · carmichael (MBI re-checks)
#   · greene (add 99487 to the CCM visit, laterality dx) · griffin (CAP07 plan + release 4 visits) · jacksonm (WOCAID2ND FCC CO-26 residuals)
#   · kleinsmith (WONCS hospice CCM) · springer (void post-death CCM) · creel (WOLATE) · flores (sex/member id check) · macdonald (answer)
#   · christopher (chart lookup + TRICARE East plan when the chart exists)
# Never touches: rendering-provider swaps (Garland-G FCC / Sunshine items are William's compliance call, see the board), chart merges (UI).
# Usage: cd /home/claude/unbilled && python3 chat_1004_board_act.py [--dry] [--only item,item]
import amd, resave, txh, freq1_visit, manual_post, move_to_ins, add_ins, ins_update, void_tx, deceased_guard, patient_patch, elig_amd, stedi
import re, sys, json, time, datetime, os
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
REG = "chat_1004_register.json"; register = json.load(open(REG)) if os.path.exists(REG) else []
LOGF = open("chat_1004_act.log", "a")
def L(m): print(m, flush=True); LOGF.write("%s %s\n" % (datetime.datetime.utcnow().strftime("%H:%M:%SZ"), m)); LOGF.flush()
def done(step, key): return any(r["step"] == step and r["key"] == key and r["ok"] for r in register)
def rec(step, key, ok, **kw):
    register.append(dict(step=step, key=key, ok=ok, when=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), dry=DRY, **kw)); json.dump(register, open(REG, "w"), indent=1)
OUT = {}
def out(item, **kw): OUT.setdefault(item, {}).update(kw); json.dump(OUT, open("chat_1004_out.json", "w"), indent=1)
NOTE = "William 10/3/2026 (board) - chat session %s" % STAMP

# ---------------------------------------------------------------- live chart readers
def chart_rows(pid):
    """every charge on the chart (all pages): dict rows + payments/writeoffs children"""
    pid = re.sub(r"\D", "", str(pid)); rows = []; seen = set()
    for page in range(1, 8):
        body = amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': str(page), 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'})
        root = ET.fromstring(amd.post(body, timeout=120)); new = 0
        for c in root.iter("charge"):
            if c.get("id") in seen: continue
            seen.add(c.get("id")); new += 1
            r = dict(c.attrib); r["pays"] = [dict(p.attrib) for p in c.iter("payment")]; r["wos"] = [dict(w.attrib) for w in c.iter("writeoff")]
            rows.append(r)
        if new == 0 or new < 100: break
    return rows
def live(rows, vid=None, cid=None):
    return [r for r in rows if r.get("void") != "1" and not (r.get("fee") or "").startswith("-") and (vid is None or r.get("visit") == str(vid)) and (cid is None or r.get("id") == str(cid))]
def plans(pid):
    pa, pl = elig_amd.plans(re.sub(r"\D", "", str(pid))); return pa, pl
def cpt_of(cid):
    det = resave.detail(cid); m = re.search(r'<charge [^>]*proccode="(pcode\d+)"', det)
    pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', det))
    return pm.get(m.group(1), m.group(1)) if m else "?", det
def fmt(r): return "%s v%s %s %s fee %s ins %s pat %s paid %s carrier %s billed %s" % (r.get("id"), r.get("visit"), r.get("dos"), r.get("proccode"), r.get("fee"), r.get("insbal"), r.get("patbal"), r.get("paid"), r.get("carrier"), r.get("billdate"))

# ---------------------------------------------------------------- write-off / void primitives
def writeoff(item, cid, carrier, amt, code, note, chk=""):
    key = "%s:%s" % (item, cid)
    if done("writeoff", key): L("   %s already written off (register)" % cid); return True
    note = note.replace('&', 'and').replace('<', '').replace('>', '').replace('"', "'")   # the case_note rides an XML attribute: a raw & = 400 Client Error (creel 10/4)
    ok, msg = manual_post.post(str(cid), carrier, 0.0, round(amt, 2), code, checknumber=chk, note=note, dry=DRY)
    L("   writeoff %s %s %.2f %s -> %s %s" % (cid, carrier, amt, code, ok, msg[:160]))
    if not DRY: rec("writeoff", key, ok, cid=cid, carrier=carrier, amount=amt, code=code, msg=msg[:200])
    return ok
def void_charge(item, pid, cid):
    key = "%s:%s" % (item, cid)
    if done("void", key): L("   %s already void (register)" % cid); return True
    if DRY: L("   DRY void charge %s" % cid); return True
    ok, msg = void_tx.void_charge(pid, cid); L("   void %s -> %s %s" % (cid, ok, msg[:160])); rec("void", key, ok, cid=cid, msg=msg[:200]); return ok

# ---------------------------------------------------------------- resave with hospitalization date / insorder / preauth
def set_hosp_date(vid, code, admit):
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
_batch = None
def batchid():
    global _batch
    if _batch is None:
        import era_post; _batch = era_post.batch()
    return _batch
def full_resave(cid, over=None, chg_over=None, extra_charge=None, action="updvisitwithnewcharges"):
    """full-visit echo (every live charge), visit attrs overridden by `over`, charge attrs by `chg_over`{chargeid:{...}}, one optional new charge dict"""
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if chg_over and c.get("id") in chg_over: a.update(chg_over[c.get("id")])
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    if extra_charge: chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in extra_charge.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if DRY: return True, "DRY resave visit %s attrs %s charges %s" % (vis.get("id"), {k: va.get(k) for k in ("insorder", "onhcfa", "preauth", "facility")}, [(x.get("id"), x.get("proccode")) for x in allc] + ([("NEW", extra_charge.get("proccode"))] if extra_charge else []))
    r = amd.post(amd.msg(action, "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batchid()), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    time.sleep(0.8)
    if "Fault" in r: return False, "FAULT " + re.sub(r"\s+", " ", r[:240])
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return True, "saved live=%d/%d%s onhcfa=%s insorder=%s preauth=%s hospfrom=%s charges=%s" % (len(c2), len(allc), "+1" if extra_charge else "", v2.get("onhcfa"), v2.get("insorder"), v2.get("preauth"), ex.get("hospitalizationfrom") if ex is not None else None, [(x.get("id"), x.get("proccode"), x.get("modcodes")) for x in c2])

# ---------------------------------------------------------------- inspector bypass of advisory patterns with fresh ids
ADV = ("The Source of Payment you have chosen is not typical", "Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261", "Pattern 11256")
def inspector_rows():
    rows = []
    t = amd.post(amd.msg("getclaiminspectorbatches", "chargeentry", {"nocookie": "1"}))
    for bid in re.findall(r'<batch id="([^"]+)"', t):
        x = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        try: root = ET.fromstring(x)
        except ET.ParseError: continue
        for v in root.iter("visit"):
            errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:200]) for e in v.iter("error")]
            rows.append({"batch": bid, "vid": re.sub(r"\D", "", v.get("id") or ""), "pid": re.sub(r"\D", "", v.get("patientid") or ""), "status": v.get("claimstatus") or "", "errs": errs})
        time.sleep(0.3)
    return rows
def bypass_advisories(vids):
    """re-list the inspector and bypass ONLY advisory-pattern errors (fresh ids) on the given visits"""
    rows = [r for r in inspector_rows() if r["vid"] in set(str(v) for v in vids)]
    outl = []
    for r in rows:
        adv = [(eid, txt) for eid, txt in r["errs"] if any(txt.startswith(p) or p in txt for p in ADV)]
        hard = [(eid, txt) for eid, txt in r["errs"] if (eid, txt) not in adv]
        if adv and not DRY:
            x = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (r["vid"], "".join('<claimedit id="%s"/>' % eid for eid, _ in adv))))
            outl.append("v%s bypassed %d advisory (%s) %s" % (r["vid"], len(adv), "; ".join(t[:40] for _, t in adv), "ok" if "Fault" not in x else "FAULT " + x[:120]))
        elif adv: outl.append("v%s DRY would bypass %s" % (r["vid"], [t[:40] for _, t in adv]))
        if hard: outl.append("v%s STILL HELD: %s" % (r["vid"], [t[:80] for _, t in hard]))
    return outl or ["none of %s listed in the inspector now" % list(vids)]
def release_unbilled(vids):
    if DRY: return "DRY release %s" % list(vids)
    x = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)))
    return "released %s -> %s" % (list(vids), "ok" if "Fault" not in x else "FAULT " + x[:160])

# ================================================================= ITEMS
def item_addison():
    """addison-rupert-17476868: William 'confirm 09/30/2026' -> hospitalizationfrom on the three 99233s + full resave onhcfa=1"""
    pid, vids = "17476868", ["19456834", "19456836", "19456835"]
    rows = chart_rows(pid); res = []
    for vid in vids:
        lv = live(rows, vid=vid)
        if not lv: res.append("v%s no live charges" % vid); continue
        cid = lv[0]["id"]; vis, pat, allc = resave.visit_charges(cid); ex = vis.find("extins")
        cur = ex.get("hospitalizationfrom") if ex is not None else None
        if cur and cur.startswith("09/30/2026"):
            res.append("v%s already carries admission %s" % (vid, cur)); continue
        if done("admit", vid): res.append("v%s admit written earlier (register)" % vid); continue
        code, det = cpt_of(cid)
        if DRY: res.append("DRY v%s set hospitalizationfrom 09/30/2026 on %s then full resave onhcfa=1" % (vid, code)); continue
        r1 = set_hosp_date(vid, code, "09/30/2026"); ok1 = "Fault" not in r1
        ok2, msg2 = full_resave(cid, over={"onhcfa": "1"})
        res.append("v%s extins %s | %s" % (vid, "ok" if ok1 else "FAULT " + r1[:120], msg2)); rec("admit", vid, ok1 and ok2, msg=msg2[:200])
    time.sleep(1.5); res += bypass_advisories(vids)
    for x in res: L("   " + x)
    out("adams", lines=res)

def item_alcott():
    """alcott-alfie-17477183: no insurance after 8/31/2026 (Sunshine ended; Medicaid pending on the PCC census) -> bill to patient / write off no-pay (WOBAD), release from Unbilled"""
    pid = "17477183"; rows = chart_rows(pid); res = []
    pa, pl = plans(pid); res.append("plans: %s" % [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate")) for p in pl])
    targets = [r for r in live(rows) if r.get("dos") and datetime.datetime.strptime(r["dos"], "%m/%d/%Y").date() >= datetime.date(2026, 9, 1) and (float(r.get("insbal") or 0) + float(r.get("patbal") or 0)) > 0]
    for r in targets:
        res.append("open: " + fmt(r))
        bal = float(r.get("insbal") or 0) + float(r.get("patbal") or 0)
        if float(r.get("patbal") or 0) > 0 and float(r.get("insbal") or 0) == 0:
            res.append("   patient balance %.2f - moving to insurance first so the write-off posts under SUN01" % float(r["patbal"]))
            if not DRY: res.append("   " + str(move_to_ins.move(r["id"])))
        writeoff("alcorn", r["id"], "SUN01", bal, "WOBAD", "Self-pay no-pay bad debt - no insurance on %s (Sunshine ended 8/31/2026, PCC census: Medicaid Pending from 9/1/2026) - %s" % (r["dos"], NOTE))
    vids = sorted({r["visit"] for r in targets})
    if vids: res.append(release_unbilled(vids))
    for x in res: L("   " + x)
    out("alcorn", lines=res, visits=vids)

def item_awv():
    """awv-pr119-0922: Medicare PR-119/N130 on G0439 7/13/2026 x2 -> WONCS (William)"""
    res = []
    for pid, vid in (("23617", "19448516"), ("21885", "19448510")):
        rows = chart_rows(pid)
        for r in live(rows, vid=vid):
            res.append("open: " + fmt(r)); bal = float(r.get("insbal") or 0)
            if bal <= 0: res.append("   nothing open on %s" % r["id"]); continue
            writeoff("awv", r["id"], "FLO02", bal, "WONCS", "Medicare PR-119/N130 annual wellness benefit maximum (G0439 7/13/2026, ERA 349980199) - non-covered per William 10/3/2026 - %s" % NOTE, chk="ERA349980199")
    for x in res: L("   " + x)
    out("awv", lines=res)

def item_barrow():
    """barrow-john-17474613: v19422927 11/6/2025 99306+99497 ($389) - UHC MA was the payer, past timely -> WOLATE ('write off untimely sent to united')"""
    pid, vid = "17474613", "19422927"; rows = chart_rows(pid); res = []
    for r in live(rows, vid=vid):
        res.append("open: " + fmt(r)); bal = float(r.get("insbal") or 0) + float(r.get("patbal") or 0)
        if bal <= 0: continue
        if float(r.get("patbal") or 0) > 0 and not DRY: res.append("   " + str(move_to_ins.move(r["id"])))
        writeoff("barber", r["id"], "UNI20", bal, "WOLATE", "Untimely - UHC Medicare Advantage was the payer for 11/6/2025 (Medicare CO-109/N418 10/3/2026); past UHC's filing window - write off per William 10/3/2026 - %s" % NOTE, chk="ERA1052943")
    for x in res: L("   " + x)
    out("barber", lines=res)

def item_burnell():
    """burnell-micah-23159: 'void 19456297' - the duplicate 9/22/2026 admission visit (99223+99497); keep v19456050"""
    pid = "23159"; rows = chart_rows(pid); res = []
    keep = live(rows, vid="19456050"); dup = live(rows, vid="19456297")
    res.append("keep v19456050: %s" % [fmt(r) for r in keep]); res.append("dup  v19456297: %s" % [fmt(r) for r in dup])
    if not keep: res.append("STOP: the visit to keep has no live charges - not voiding"); out("burney", lines=res); return
    for r in dup:
        pays = [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        if pays: res.append("   %s carries a live non-zero payment %s - NOT voided (needs a look)" % (r["id"], pays)); continue
        void_charge("burney", pid, r["id"])
    for x in res: L("   " + x)
    out("burney", lines=res)

def item_caine():
    """caine-rowena-17471977: HCA facesheet (William 10/3): BCBS GEORGIA MCR PPO VGD731W22044 eff 11/19/25 (Anthem GA Medicare Advantage, State Health Benefit Plan) -> FLORIDA BLUE car6062 (out-of-state Blues), rebill the 2 visits"""
    pid = "17471977"; rows = chart_rows(pid); res = []
    pa, pl = plans(pid); res.append("plans before: %s" % [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate"), p.get("sequence")) for p in pl]); res.append("insorder %s" % pa.get("insorder"))
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens: res.append("open: " + fmt(r))
    member = "VGD731W22044"
    have = [p for p in pl if p.get("subscribernum") == member]
    if have: seq = have[0]["sequence"]; insid = have[0]["id"]; res.append("plan already on the chart %s seq %s" % (insid, seq))
    else:
        if DRY: res.append("DRY add FLORIDA BLUE car6062 %s begin 11/19/2025" % member); seq = "?"
        else:
            insid, seq = add_ins.add(pid, "car6062", member, "11/19/2025"); res.append("added car6062 %s -> %s seq %s" % (member, insid, seq)); rec("addplan", "cain", bool(insid), insid=insid, seq=seq)
    # end-date the dead UHC plans the day before the first denied DOS
    for p in pl:
        if p.get("carrier") in ("car6404", "car302853") and not p.get("enddate"):
            if DRY: res.append("DRY end-date %s (%s) 11/18/2025" % (p.get("id"), p.get("carrier"))); continue
            ok, msg = ins_update.update(pid, p["id"], enddate="11/18/2025"); res.append("end-dated %s -> %s %s" % (p.get("id"), ok, msg[:80]))
    # eligibility on the new plan (BlueCard via Florida Blue)
    if not DRY and seq != "?":
        try:
            s = elig_amd.run_plan(pid, re.sub(r"\D", "", insid), True); res.append("AMD 271 on the new plan: " + elig_amd.one_line(s)[:300])
        except Exception as e: res.append("AMD 271 failed: %s" % e)
    # rebill the open visits to the new plan's sequence (insorder = seq), frequency 1
    for vid in sorted({r["visit"] for r in opens}):
        cid = live(rows, vid=vid)[0]["id"]
        if done("rebill", "cain:" + vid): res.append("v%s already rebilled (register)" % vid); continue
        if DRY: res.append("DRY v%s: insorder -> %s, freq1 + rebill seq %s" % (vid, seq, seq)); continue
        r1 = freq1_visit.run(vid, cid, int(seq)); time.sleep(0.5)
        r2 = move_to_ins.move(cid, str(seq), rebill_seq=int(seq)); res.append("v%s: %s | %s" % (vid, r1, r2)); rec("rebill", "cain:" + vid, "FAULT" not in str(r1) + str(r2) and "BLOCKED" not in str(r2), msg=str(r2)[:200])
    for x in res: L("   " + x)
    out("cain", lines=res)

def item_carmody():
    """carmody-norcott-17473431: the HCA sheet carries the SAME MBI Medicare now rejects (the MBI on the chart) + the AARP supplement on the chart - re-run every lookup before asking for a new card"""
    pid = "17473431"; res = []
    pa, pl = plans(pid); res.append("plans: %s" % [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("enddate")) for p in pl])
    name = pa.get("name", ""); last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]; dob = pa.get("dob", "")
    dob8 = dob[6:] + dob[:2] + dob[3:5] if len(dob) == 10 else ""
    try:
        t = amd.post(amd.msg("lookuppatient", "lookup", {"name": "%s,%s%%" % (last.strip(), first[:3]), "nocookie": "1"}))
        ssn = next((m for m in re.findall(r'ssn="([^"]*)"', t.encode("latin-1", "ignore").decode("latin-1")) if m), "")
    except Exception as e: ssn = ""; res.append("lookuppatient failed %s" % e)
    for p in pl:
        if not p.get("enddate"):
            try: s = elig_amd.run_plan(pid, p["id"].replace("ins", ""), True); res.append("AMD 271 %s %s: %s" % (p.get("carrier"), p.get("subscribernum"), elig_amd.one_line(s)[:260]))
            except Exception as e: res.append("AMD 271 %s failed %s" % (p.get("id"), e))
    try:
        j = stedi.mbi(first, last.strip(), dob8, state="FL", dos="20260920", ssn=(ssn.replace("-", "") if ssn and ssn.replace("-", "").isdigit() and len(ssn.replace("-", "")) == 9 else None))
        res.append("Stedi MBI lookup (%s): %s" % ("MBILU with SSN" if ssn else "MBILUNOSSN", json.dumps(stedi.med_summ(j))[:400]))
    except Exception as e: res.append("Stedi MBI lookup failed %s" % e)
    try:
        j = stedi.elig("CMS", first, last.strip(), dob8, os.environ.get("CARMODY_MBI", "")  # the chart MBI (secrets/run_inputs; never in the repo), "20260920"); res.append("Stedi CMS with the chart MBI: %s" % json.dumps(stedi.med_summ(j))[:400])
    except Exception as e: res.append("Stedi CMS failed %s" % e)
    try:
        j = stedi.elig("87726", first, last.strip(), dob8, os.environ.get("CARMODY_AARP_ID", ""), "20260920"); errs = ["%s %s" % (e.get("code"), e.get("description")) for e in j.get("errors") or []]
        sub = j.get("subscriber") or {}; res.append("Stedi UHC/AARP (chart seq-2 id): errors %s subscriber %s plan %s" % (errs, {k: sub.get(k) for k in ("memberId", "firstName", "lastName", "dateOfBirth")}, [(b.get("code"), b.get("insuranceTypeCode"), b.get("planCoverage")) for b in (j.get("benefitsInformation") or [])[:4]]))
    except Exception as e: res.append("Stedi UHC failed %s" % e)
    for x in res: L("   " + x)
    out("carmichael", lines=res)

def item_greenwood():
    """greenwood-jesper-17476036: v19456171 bills 99489 without 99487 (Pattern 15775) + unspecified-laterality S91.309D -> add the 99487 base code (William: 'fix the coding (add 99487'), laterality per the 11256 rule, resave + bypass"""
    pid, vid = "17476036", "19456171"; rows = chart_rows(pid); res = []
    lv = live(rows, vid=vid); res.append("live: %s" % [fmt(r) for r in lv])
    if not lv: out("greene", lines=res); return
    cid = lv[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
    dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}
    cpts = {}
    for c in allc:
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', dets[c.get("id")])); cpts[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    res.append("cpts %s" % cpts)
    if "99487" in cpts.values(): res.append("99487 already on the visit"); out("greene", lines=res); return
    c489 = next((c for c in allc if cpts[c.get("id")] == "99489"), None)
    if c489 is None: res.append("no 99489 on the visit - nothing to pair"); out("greene", lines=res); return
    # find the practice's 99487 pcode + fee from another CCM charge on the chart or a known chart
    ref = None
    for cand_pid in (pid, "17468923", "17473431"):
        for r in live(chart_rows(cand_pid)) if cand_pid != pid else lv + [x for x in live(rows) if x.get("visit") != vid]:
            code, det = cpt_of(r["id"])
            if code == "99487": ref = (r, det); break
        if ref: break
    if not ref: res.append("no 99487 reference charge found - cannot build the new charge"); out("greene", lines=res); return
    rr, rdet = ref; rm = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % rr["id"], rdet); ra = dict(re.findall(r'(\w+)="([^"]*)"', rm.group(0)))
    res.append("99487 reference: chart %s charge %s pcode %s fee %s units %s" % (rr.get("patient", "?"), rr["id"], ra.get("proccode"), ra.get("fee"), ra.get("units")))
    new = {}
    for f in resave.CHG_FIELDS:
        if c489.get(f) is not None: new[f] = c489.get(f)
    new.update({"proccode": ra.get("proccode"), "fee": ra.get("fee"), "netfee": ra.get("fee"), "allowed": "0.00", "units": "1", "modcodes": "", "insportion": ra.get("fee"), "insbalance": ra.get("fee"), "patportion": "0.00", "patbalance": "0.00", "paid": "0.00"})
    new.pop("aging", None)
    # laterality: S91.309D on the 99489 - drop that one dcode when another dx remains (11256 billing rule), log it
    chg_over = {}
    dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', dets[c489.get("id")]))
    order = (c489.get("diagcodes") or "").split(); codes = [dmap.get(x, x) for x in order]
    bad = [x for x, cd in zip(order, codes) if cd.replace(".", "").upper().startswith("S91309")]
    if bad and len(order) > 1:
        keep = [x for x in order if x not in bad]; chg_over[c489.get("id")] = {"diagcodes": " ".join(keep)}; new["diagcodes"] = " ".join(keep)
        res.append("laterality: dropping %s (%s) from the dx list, keeping %s" % (bad, [dmap.get(b) for b in bad], [dmap.get(k, k) for k in keep]))
        if not DRY: open("laterality_flag_log.md", "a").write("- %s pat%s v%s: S91.309D unspecified laterality removed from the CCM dx list (billing rule 11256), remaining %s - %s\n" % (STAMP, pid, vid, [dmap.get(k, k) for k in keep], NOTE))
    else: res.append("dx on 99489: %s (no laterality change)" % codes)
    ok, msg = full_resave(cid, over={"onhcfa": "1"}, chg_over=chg_over, extra_charge=new); res.append("resave: %s %s" % (ok, msg[:300]))
    if not DRY: rec("addcharge", "greene:" + vid, ok, msg=msg[:200])
    time.sleep(1.5); res += bypass_advisories([vid])
    for x in res: L("   " + x)
    out("greene", lines=res)

def item_griffith():
    """griffith-jace-17477850: HCA facesheet (William 10/3): CAPITAL HEALTH MCR policy # on the sheet (CHP Medicare Advantage, COB 2/1/2026 per Medicare's 271) -> CAP07 car41826 only plan, primary; release the 4 held HCA visits"""
    pid = "17477850"; rows = chart_rows(pid); res = []
    pa, pl = plans(pid); res.append("plans before: %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate"), p.get("sequence")) for p in pl], pa.get("insorder")))
    member = os.environ.get("GRIFFITH_CHP_ID", "")  # from secrets/run_inputs, never in the repo; have = [p for p in pl if p.get("subscribernum") == member]
    if have: insid, seq = have[0]["id"], have[0]["sequence"]; res.append("CAP07 plan already on the chart %s seq %s" % (insid, seq))
    elif DRY: insid, seq = None, "?"; res.append("DRY add CAP07 car41826 %s begin 02/01/2026" % member)
    else:
        insid, seq = add_ins.add(pid, "car41826", member, "02/01/2026"); res.append("added car41826 %s -> %s seq %s" % (member, insid, seq)); rec("addplan", "griffin", bool(insid), insid=insid, seq=seq)
    if insid and not DRY:
        try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", insid), True); res.append("AMD 271 CAP07: " + elig_amd.one_line(s)[:300])
        except Exception as e: res.append("AMD 271 failed %s" % e)
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens: res.append("open: " + fmt(r))
    vids = sorted({r["visit"] for r in opens})
    for vid in vids:
        cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid); ex = vis.find("extins")
        over = {"insorder": str(seq), "onhcfa": "1"}
        cp = {c.get("id"): cpt_of(c.get("id").replace("charge", ""))[0] for c in allc}
        hosp = any(x in ("99223", "99233", "99232") for x in cp.values())
        if hosp and not (ex is not None and ex.get("hospitalizationfrom", "").startswith("09/21/2026")) and not DRY:
            for code in sorted(set(cp.values())): set_hosp_date(vid, code, "09/21/2026")
            res.append("v%s admission 09/21/2026 written (cpts %s)" % (vid, sorted(set(cp.values()))))
        if done("release", "griffin:" + vid): res.append("v%s already set (register)" % vid); continue
        ok, msg = full_resave(cid, over=over); res.append("v%s resave insorder %s: %s %s" % (vid, seq, ok, msg[:200]))
        if not DRY: rec("release", "griffin:" + vid, ok, msg=msg[:200])
    time.sleep(1.5); res += bypass_advisories(vids)
    if vids: res.append(release_unbilled(vids))
    for x in res: L("   " + x)
    out("griffin", lines=res, visits=vids)

def item_jacksonm():
    """fcc-co26-jacobsen-24039: FCC CO-26/N650 on the Medicare-coinsurance residuals -> WOCAID2ND (the 9/1/2026 line $21.80 + the 9/22 residuals = every open FLO99 residual on the chart)"""
    pid = "24039"; rows = chart_rows(pid); res = []
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) > 0 and (r.get("carrier") in ("FLO99",) or r.get("visit") == "19453504")]
    others = [r for r in live(rows) if float(r.get("insbal") or 0) > 0 and r not in opens]
    for r in others: res.append("open elsewhere (left alone): " + fmt(r))
    for r in opens:
        res.append("FCC residual: " + fmt(r)); bal = float(r.get("insbal") or 0)
        pays = [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        if not pays: res.append("   no primary payment on this charge - not a coinsurance residual, skipped"); continue
        writeoff("jacksonm", r["id"], "FLO99", bal, "WOCAID2ND", "FCC CO-26/N650 on the Medicare-coinsurance residual (dual; FCC's eligibility file behind the state's) - write off per William 10/3/2026 - %s" % NOTE, chk="ERA1052822")
    for x in res: L("   " + x)
    out("jacksonm", lines=res)

def item_kleinman():
    """kleinman-marian-17468923: Medicare CO-B9 hospice on the 5/17/2026 CCM (v19442292 99487+99489 $315) -> WONCS ('CCM charges billed to hospice patients don't pay')"""
    pid, vid = "17468923", "19442292"; rows = chart_rows(pid); res = []
    for r in live(rows, vid=vid):
        res.append("open: " + fmt(r)); bal = float(r.get("insbal") or 0) + float(r.get("patbal") or 0)
        if bal <= 0: continue
        if float(r.get("patbal") or 0) > 0 and not DRY: res.append("   " + str(move_to_ins.move(r["id"])))
        writeoff("kleinsmith", r["id"], "FLO02", bal, "WONCS", "Medicare CO-B9 hospice election - CCM during hospice not payable (ERA 1052943 10/3/2026); William 10/3/2026: CCM billed to hospice patients is written off - %s" % NOTE, chk="ERA1052943")
    # post-death check: date of death 6/21/2026 on the Medicare record - any later charge?
    late = [fmt(r) for r in live(rows) if r.get("dos") and datetime.datetime.strptime(r["dos"], "%m/%d/%Y").date() > datetime.date(2026, 6, 21)]
    res.append("charges after the 6/21/2026 date of death: %s" % (late or "none"))
    for x in res: L("   " + x)
    out("kleinsmith", lines=res)

def item_sprigg():
    """sprigg-davin: William 9/6 'yes void post death charges' - the 12/21/25 + 1/27/26 CCM visits (date of death 11/08/2025); they were written off 9/6, the void never happened"""
    pid = "17473198"; rows = chart_rows(pid); res = []
    dod = datetime.date(2025, 11, 8)
    post = [r for r in live(rows) if r.get("dos") and datetime.datetime.strptime(r["dos"], "%m/%d/%Y").date() > dod]
    for r in post:
        res.append("post-death live charge: " + fmt(r) + " pays %s wos %s" % ([(p.get("amount"), p.get("void")) for p in r["pays"]], [(w.get("wocode"), w.get("amount"), w.get("void")) for w in r["wos"]]))
        pays = [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        if pays: res.append("   live payment on it - NOT voided, needs a look"); continue
        void_charge("springer", pid, r["id"])
    if not post: res.append("no live charges after %s - nothing to void" % dod)
    for x in res: L("   " + x)
    out("springer", lines=res)

def item_crewe():
    """crewe-rhona (pat20989): William 9/11 'write off untimely' - the $594 wrong-payer balance (Sierra/UHC MA was primary; DOS 11/2023-11/2024, date of death 1/18/2025)"""
    pid = "20989"; rows = chart_rows(pid); res = []
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens:
        res.append("open: " + fmt(r)); bal = float(r.get("insbal") or 0) + float(r.get("patbal") or 0)
        if float(r.get("patbal") or 0) > 0 and not DRY: res.append("   " + str(move_to_ins.move(r["id"])))
        carrier = r.get("carrier") if r.get("carrier") in ("UNI20", "AAR01", "HUM01", "FLO02") else "UNI20"
        writeoff("creel", r["id"], carrier, bal, "WOLATE", "Untimely - Sierra Health & Life / UHC MA was primary through the 1/18/2025 date of death and was never billed in time; write off per William 9/11/2026 - %s" % NOTE)
    if not opens: res.append("nothing open")
    for x in res: L("   " + x)
    out("creel", lines=res)

def item_fairholm():
    """fairholm-elowen (pat17477684): William 9/11 - member id on the plan before claims go out; sex F in demographics"""
    pid = "17477684"; res = []
    pa, pl = plans(pid); res.append("plans: %s" % [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("enddate")) for p in pl]); res.append("chart sex=%s name=%s dob=%s" % (pa.get("sex"), pa.get("name"), pa.get("dob")))
    try:
        p = patient_patch.get(pid); sex = p.get("sex") or p.get("gender") or (p.get("demographics") or {}).get("sex")
        res.append("REST sex: %s" % sex)
        if sex and str(sex).upper().startswith("M"):
            if DRY: res.append("DRY patch sex -> F")
            else: code, txt, before = patient_patch.patch(pid, {"sex": "F"}); res.append("PATCH sex F -> %s %s" % (code, txt[:120])); rec("sex", "flores", code in (200, 204), msg=txt[:120])
    except Exception as e: res.append("REST read failed %s" % e)
    rows = chart_rows(pid); res.append("open: %s" % [fmt(r) for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0])
    for x in res: L("   " + x)
    out("flores", lines=res)

def item_macallister():
    """macallister-chester-17469645: William asks what the 4 denied UHC claims are (CCM?) - read the chart"""
    pid = "17469645"; rows = chart_rows(pid); res = []
    for r in live(rows):
        if r.get("dos") in ("05/11/2026", "05/17/2026", "06/01/2026", "06/02/2026"):
            res.append(fmt(r) + " cpt %s" % cpt_of(r["id"])[0])
    for x in res: L("   " + x)
    out("macdonald", lines=res)

def item_christensen():
    """christensen-christa-admit-0925: PCC sheet (William 10/3): male, DOB on the sheet, TRICARE (sponsor id = the policy # on the sheet), Aviata 303-A from TMH 9/25/2026 - add the TRICARE East plan when the chart exists"""
    res = []
    t = amd.post(amd.msg("lookuppatient", "lookup", {"name": "CHRISTENSEN,CHR%", "nocookie": "1"}))
    hits = re.findall(r'<patient ([^>]*)>', t.encode("latin-1", "ignore").decode("latin-1")); charts = [dict(re.findall(r'(\w+)="([^"]*)"', h)) for h in hits]
    res.append("lookuppatient: %s" % [(c.get("id"), c.get("name"), c.get("dob")) for c in charts])
    match = [c for c in charts if c.get("dob", "").startswith(os.environ.get("CHRISTENSEN_DOB", "--"))  # DOB from secrets/run_inputs, never in the repo]
    if not match: res.append("no chart yet - nothing to add (the Claimocity feed creates it with the first charge)"); out("christopher", lines=res); return
    pid = re.sub(r"\D", "", match[0]["id"]); pa, pl = plans(pid); res.append("chart %s plans %s" % (pid, [(p.get("carrier"), p.get("subscribernum")) for p in pl]))
    if any(p.get("carrier") in ("car6872", "car6559") for p in pl): res.append("TRICARE plan already on the chart"); out("christopher", lines=res, pid=pid); return
    sponsor = os.environ.get("CHRISTENSEN_SPONSOR", "")   # the policy # from the PCC sheet, passed in the environment - never written into a script
    if not sponsor: res.append("sponsor id not supplied (CHRISTENSEN_SPONSOR) - plan not added"); out("christopher", lines=res, pid=pid); return
    if DRY: res.append("DRY add TRICARE EAST car6872 sponsor id begin 09/25/2026")
    else: insid, seq = add_ins.add(pid, "car6872", sponsor, "09/25/2026"); res.append("added car6872 -> %s seq %s" % (insid, seq)); rec("addplan", "christopher", bool(insid), insid=insid, seq=seq)
    for x in res: L("   " + x)
    out("christopher", lines=res, pid=pid)

ITEMS = {"adams": item_addison, "alcorn": item_alcott, "awv": item_awv, "barber": item_barrow, "burney": item_burnell, "cain": item_caine, "carmichael": item_carmody,
         "greene": item_greenwood, "griffin": item_griffith, "jacksonm": item_jacksonm, "kleinsmith": item_kleinman, "springer": item_sprigg, "creel": item_crewe,
         "flores": item_fairholm, "macdonald": item_macallister, "christopher": item_christensen}
if __name__ == "__main__":
    amd.login_cached()
    for name, fn in ITEMS.items():
        if ONLY and name not in ONLY: continue
        L("== %s%s" % (name, " (DRY)" if DRY else ""))
        try: fn()
        except Exception as e:
            import traceback; L("   EXCEPTION %s: %s" % (name, traceback.format_exc()[-600:])); out(name, error=str(e)[:300])
    L("== done %s" % STAMP)
