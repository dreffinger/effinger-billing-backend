# PLAIN ENGLISH (Chat session 10/4/2026, wave 2 - the board answers William posted 03:02-03:49Z, after the first nine were built)
# Decides: one action per row, from the LIVE chart, as William answered: bellingham WONCS · smythe-bexford / powell voids after the date of death
#   · pignone CAP07 plan + release · reeve admission 09/03/2026 · rodway restore the voided 99487 + Medicare first · rossiter Sunshine
#   secondary · scott new MBI + Medicare-first rebill · screws / slater Medicare + GV · short Florida Blue check · simmonds Medigap check
#   · sikora Medicare card from Pam's email (MBI, first name LORENA) · merriwether BlueOptions id · jarvis duplicate chart made billable
#   · lazenby referral-plan recreate attempt · jacobsen-norcott re-render under Effinger ('mine').
# Never touches: paid charges (a re-render only on unpaid visits), group numbers, the standing holds.
# Usage: cd /home/claude/unbilled && python3 chat_1004_board_act2.py [--dry] [--only item,item]
import amd, resave, freq1_visit, manual_post, move_to_ins, add_ins, ins_update, void_tx, patient_patch, elig_amd, stedi, restore_charge
import re, sys, json, time, datetime, os
import xml.etree.ElementTree as ET
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, out, chart_rows, live, plans, cpt_of, fmt, writeoff, void_charge, set_hosp_date, full_resave, bypass_advisories, release_unbilled, NOTE
DRY = A.DRY; ONLY = A.ONLY
GV = "mcode713"; EFFINGER_RPROV = "rprov13"; EFFINGER_PROF = "prof13"

def seq_of(pl, carrier, prefer_open=True):
    c = [p for p in pl if p.get("carrier") == carrier and (not p.get("enddate") or not prefer_open)]
    return (c[0]["sequence"], c[0]["id"]) if c else (None, None)
def dos_date(s): return datetime.datetime.strptime(s, "%m/%d/%Y").date()
def rebill_visit(item, pid, rows, vid, order, seq):
    """set the visit insorder (full echo) and send frequency 1 on `seq`"""
    key = "%s:%s" % (item, vid)
    if done("rebill", key): return "v%s already rebilled (register)" % vid
    cid = live(rows, vid=vid)[0]["id"]
    if DRY: return "DRY v%s insorder %s freq1 seq %s" % (vid, order, seq)
    r1 = freq1_visit.run(vid, cid, int(seq)); time.sleep(0.4)
    r2 = move_to_ins.move(cid, str(order), rebill_seq=int(seq)); time.sleep(0.4)
    ok = "FAULT" not in str(r1) + str(r2) and "BLOCKED" not in str(r2)
    rec("rebill", key, ok, msg=(str(r1) + " | " + str(r2))[:240]); return "v%s: %s | %s" % (vid, r1, r2)

def item_bellingham():
    """bellingham-amon-17476534: William 03:40Z 'write off (WONCS)' - Florida Blue PR-50/PR-197 on the 5/11-5/13/2026 HCA claims ($731)"""
    pid = "17476534"; rows = chart_rows(pid); res = []
    for r in live(rows):
        if r.get("dos") not in ("05/11/2026", "05/12/2026", "05/13/2026"): continue
        bal = float(r.get("insbal") or 0) + float(r.get("patbal") or 0); res.append("open: " + fmt(r))
        if bal <= 0: continue
        if float(r.get("patbal") or 0) > 0 and not DRY: res.append("   " + str(move_to_ins.move(r["id"])))
        writeoff("bellingham", r["id"], "BCBS", bal, "WONCS", "Florida Blue (BCBS NC BlueCard) PR-50 not medically necessary / PR-197 precert absent on the 5/2026 HCA stay (835 trace 213436603); hospital sheet: auth not required - write off per William 10/3/2026 - %s" % NOTE, chk="ERA213436603")
    for x in res: L("   " + x)
    out("bellingham", lines=res)

def void_after_death(item, pid, dod):
    rows = chart_rows(pid); res = []
    post = [r for r in live(rows) if r.get("dos") and dos_date(r["dos"]) > dod]
    for r in post:
        res.append("after %s: %s pays %s wos %s" % (dod, fmt(r), [(p.get("amount"), p.get("void")) for p in r["pays"]], [(w.get("wocode"), w.get("amount"), w.get("void")) for w in r["wos"]]))
        if [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]: res.append("   live payment - NOT voided"); continue
        void_charge(item, pid, r["id"])
    if not post: res.append("no live charges after %s" % dod)
    for x in res: L("   " + x)
    out(item, lines=res)
def item_smythe_bexford(): void_after_death("smythe_bexford", "17473477", datetime.date(2026, 9, 15))
def item_penhale(): void_after_death("penhale", "17471681", datetime.date(2026, 9, 10))

def item_pignone():
    """pignone-susanna-17477892: HCA sheet (William 03:23Z) CAPITAL HEALTH MCR (policy # on the sheet) -> CAP07 car41826; admission 09/23/2026; release the 2 HCA visits"""
    pid = "17477892"; rows = chart_rows(pid); res = []
    pa, pl = plans(pid); res.append("plans before %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate")) for p in pl], pa.get("insorder")))
    member = os.environ.get("PIGNONE_CHP_ID", "")  # from secrets/run_inputs, never in the repo; name = pa.get("name", ""); last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]
    dob = pa.get("dob", ""); dob8 = dob[6:] + dob[:2] + dob[3:5] if len(dob) == 10 else os.environ.get("PIGNONE_DOB8", "")
    begin = "09/23/2026"
    try:
        j = stedi.elig("95112", first, last.strip(), dob8, member, "20260923"); errs = [(e.get("code"), e.get("description")) for e in j.get("errors") or []]
        pb = (j.get("planDateInformation") or {}).get("planBegin") or (j.get("planInformation") or {}).get("planBegin")
        st = [b.get("name") for b in (j.get("benefitsInformation") or []) if "30" in (b.get("serviceTypeCodes") or [])][:3]
        res.append("Stedi CHP 95112 @9/23/2026: %s errors %s planBegin %s" % (st, errs, pb))
        if pb and re.match(r"\d{8}$", pb): begin = "%s/%s/%s" % (pb[4:6], pb[6:], pb[:4])
    except Exception as e: res.append("Stedi CHP error %s" % e)
    have = [p for p in pl if p.get("subscribernum") == member]
    if have: insid, seq = have[0]["id"], have[0]["sequence"]; res.append("CAP07 already on the chart %s seq %s" % (insid, seq))
    elif DRY: insid, seq = None, "?"; res.append("DRY add CAP07 car41826 %s begin %s" % (member, begin))
    else:
        insid, seq = add_ins.add(pid, "car41826", member, begin); res.append("added car41826 %s begin %s -> %s seq %s" % (member, begin, insid, seq)); rec("addplan", "pignone", bool(insid), insid=insid, seq=seq)
        try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", insid), True); res.append("AMD 271 CAP07: " + elig_amd.one_line(s)[:260])
        except Exception as e: res.append("AMD 271 failed %s" % e)
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    vids = sorted({r["visit"] for r in opens})
    for r in opens: res.append("open: " + fmt(r))
    for vid in vids:
        cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
        cp = {c.get("id"): cpt_of(c.get("id").replace("charge", ""))[0] for c in allc}
        if done("release", "pignone:" + vid): res.append("v%s already set" % vid); continue
        if not DRY:
            for code in sorted(set(cp.values())): set_hosp_date(vid, code, "09/23/2026")
        chg_over = {c.get("id"): {"modcodes": ("mcode7 " + (c.get("modcodes") or "")).strip()} for c in allc if cp[c.get("id")] == "99497" and "mcode7" not in (c.get("modcodes") or "").split()}
        ok, msg = full_resave(cid, over={"insorder": str(seq), "onhcfa": "1"}, chg_over=chg_over); res.append("v%s resave: %s %s" % (vid, ok, msg[:200]))
        if not DRY: rec("release", "pignone:" + vid, ok, msg=msg[:200])
    time.sleep(1.5); res += bypass_advisories(vids)
    if vids: res.append(release_unbilled(vids))
    for x in res: L("   " + x)
    out("pignone", lines=res, visits=vids)

def item_reeve():
    """reeve-cyrilla-17477640: HCA visit history (William 03:24Z): inpatient 09/03-09/27/2026, readmitted 09/29-30. Live chart 10/4: every 99233 is already billed to HUM01 (9/18-10/3) and nothing is held in the inspector - record the admission dates on the row, no resave of billed claims."""
    pid = "17477640"; rows = chart_rows(pid); res = []
    for r in live(rows):
        if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) <= 0: continue
        d = dos_date(r["dos"]); admit = "09/29/2026" if d >= datetime.date(2026, 9, 29) else ("09/03/2026" if datetime.date(2026, 9, 3) <= d <= datetime.date(2026, 9, 27) else None)
        res.append("open: %s -> stay admitted %s" % (fmt(r), admit))
    res += bypass_advisories(sorted({r["visit"] for r in live(rows) if float(r.get("insbal") or 0) > 0}))
    for x in res: L("   " + x)
    out("reeve", lines=res)

def item_rodway():
    """rodway-rosalind-17474541: 'restore' - restore the voided 99487 (23336997) beside the live 99489 (23336998) on v19430630, then Medicare first (chart order 2,1)"""
    pid = "17474541"; res = []; rows = chart_rows(pid)
    lv = live(rows, vid="19430630"); res.append("live on v19430630: %s" % [fmt(r) for r in lv])
    if any(r.get("proccode") == "99487" or cpt_of(r["id"])[0] == "99487" for r in lv): res.append("99487 already live")
    else:
        r = restore_charge.restore("23336997", "23336998", dry=DRY); res.append("restore: %s" % str(r)[:300])
        if not DRY: rec("restore", "rodway", str(r).startswith("OK"), msg=str(r)[:200])
    pa, pl = plans(pid); mseq, mid = seq_of(pl, "car6085"); pseq, _ = seq_of(pl, "car42014" if any(p.get("carrier") == "car42014" for p in pl) else [p for p in pl if p.get("carrier") != "car6085"][0]["carrier"]) if pl else (None, None)
    order = ",".join(x for x in (mseq, pseq) if x); res.append("plans %s -> order %s" % ([(p.get("carrier"), p.get("sequence")) for p in pl], order))
    if mseq:
        rows = chart_rows(pid); res.append(rebill_visit("rodway", pid, rows, "19430630", order, mseq))
    time.sleep(1.5); res += bypass_advisories(["19430630"])
    for x in res: L("   " + x)
    out("rodway", lines=res)

def item_rossiter():
    """rossiter-margery-20729: PCC readmit sheet (William 03:29Z): Medicare A primary (MBI = chart) + 'Medicare A coinsurance from Medicaid' SUNSHINE STATE, Medicaid # (on the sheet) -> SUN01 car6194 seq 2, visits since 9/25 insorder 1,2"""
    pid = "20729"; res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    res.append("plans %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate"), p.get("sequence")) for p in pl], pa.get("insorder")))
    member = os.environ.get("ROSSITER_MEDICAID", "")  # from secrets/run_inputs, never in the repo; have = [p for p in pl if p.get("carrier") == "car6194" and not p.get("enddate")]
    if have: sseq, sid = have[0]["sequence"], have[0]["id"]; res.append("Sunshine already on the chart %s seq %s (%s)" % (sid, sseq, have[0].get("subscribernum")))
    elif DRY: sseq = "?"; res.append("DRY add SUN01 car6194 %s begin 09/25/2026" % member)
    else:
        sid, sseq = add_ins.add(pid, "car6194", member, "09/25/2026"); res.append("added car6194 %s -> %s seq %s" % (member, sid, sseq)); rec("addplan", "rossiter", bool(sid), insid=sid, seq=sseq)
        try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", sid), True); res.append("AMD 271 SUN01: " + elig_amd.one_line(s)[:260])
        except Exception as e: res.append("AMD 271 failed %s" % e)
    mseq, _ = seq_of(pl, "car6085")
    if mseq and sseq != "?":
        if not DRY:
            ok, msg = ins_update.update(pid, [p for p in pl if p.get("carrier") == "car6085"][0]["id"], sequence="%s,%s" % (mseq, sseq)); res.append("patient order %s,%s -> %s %s" % (mseq, sseq, ok, msg[:60]))
        for vid in sorted({r["visit"] for r in live(rows) if dos_date(r["dos"]) >= datetime.date(2026, 9, 25) and float(r.get("insbal") or 0) > 0}):
            cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
            if vis.get("insorder") == "%s,%s" % (mseq, sseq): res.append("v%s already %s" % (vid, vis.get("insorder"))); continue
            ok, msg = full_resave(cid, over={"insorder": "%s,%s" % (mseq, sseq)}); res.append("v%s insorder %s,%s: %s %s" % (vid, mseq, sseq, ok, msg[:120]))
    for x in res: L("   " + x)
    out("rossiter", lines=res)

def item_sayer():
    """sayer-rupert-12180329: TMH active insurance (William 03:30Z): MEDICARE A+B member = the MBI on the sheet (chart MBI was wrong - AMD 271 rejected / CMS ERR 73); BCBS PPO stays second -> fix the id, 271, rebill the open FB visits Medicare first"""
    pid = "12180329"; res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    res.append("plans %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("enddate"), p.get("sequence")) for p in pl], pa.get("insorder")))
    med = [p for p in pl if p.get("carrier") == "car6085"]; new = os.environ.get("SAYER_MBI", "")  # from secrets/run_inputs, never in the repo
    if not med:
        if DRY: res.append("DRY add FLO02 %s" % new); mseq = "?"
        else: mid, mseq = add_ins.add(pid, "car6085", new, "01/01/2025"); res.append("added FLO02 -> %s seq %s" % (mid, mseq)); rec("addplan", "sayer", bool(mid))
    else:
        mid, mseq = med[0]["id"], med[0]["sequence"]
        if med[0].get("subscribernum") != new:
            if DRY: res.append("DRY ins_update %s subscribernum %s -> %s" % (mid, med[0].get("subscribernum"), new))
            else: ok, msg = ins_update.update(pid, mid, subscribernum=new); res.append("MBI %s -> %s: %s %s" % (med[0].get("subscribernum"), new, ok, msg[:60])); rec("mbi", "sayer", ok)
        else: res.append("MBI already %s" % new)
        if not DRY:
            try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", mid), True); res.append("AMD 271 Medicare: " + elig_amd.one_line(s)[:260])
            except Exception as e: res.append("AMD 271 failed %s" % e)
    fbseq, _ = seq_of(pl, "car6062")
    order = ",".join(x for x in (mseq, fbseq) if x and x != "?")
    if mseq != "?" and not DRY and pa.get("insorder") != order and fbseq:
        ok, msg = ins_update.update(pid, mid, sequence=order); res.append("patient order -> %s: %s" % (order, ok))
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens: res.append("open: " + fmt(r))
    if mseq != "?":
        for vid in sorted({r["visit"] for r in opens}):
            res.append(rebill_visit("sayer", pid, rows, vid, order, mseq))
    for x in res: L("   " + x)
    out("sayer", lines=res)

def medicare_gv(item, pid, dos_list, mbi_hint=None):
    """add straight Medicare from the Stedi MBI lookup when the chart has none, put GV on every charge of the listed visits, send frequency 1 to Medicare"""
    res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    res.append("plans %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("enddate"), p.get("sequence")) for p in pl], pa.get("insorder")))
    name = pa.get("name", ""); last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]; dob = pa.get("dob", ""); dob8 = dob[6:] + dob[:2] + dob[3:5] if len(dob) == 10 else ""
    mseq, mid = seq_of(pl, "car6085", prefer_open=False)
    mbi = mbi_hint; dod = None
    try:
        j = stedi.mbi(first, last.strip(), dob8, state="FL", dos=dos_list[0].replace("/", "")[4:] + dos_list[0].replace("/", "")[:4]); sm = stedi.med_summ(j)
        res.append("Stedi MBI lookup: %s" % json.dumps(sm)[:400]); mbi = mbi or sm.get("mbi"); dod = sm.get("death")
    except Exception as e: res.append("Stedi MBI lookup failed %s" % e)
    if not mid:
        if not mbi: res.append("no MBI - cannot add Medicare"); out(item, lines=res); return res
        if DRY: res.append("DRY add FLO02 %s" % mbi); mseq = "?"
        else: mid, mseq = add_ins.add(pid, "car6085", mbi, "01/01/2025"); res.append("added FLO02 %s -> %s seq %s" % (mbi, mid, mseq)); rec("addplan", item, bool(mid))
    if mseq == "?": out(item, lines=res); return res
    for dos in dos_list:
        for vid in sorted({r["visit"] for r in live(rows) if r.get("dos") == dos}):
            if dod and dos_date(dos) > datetime.date.fromisoformat(dod): res.append("v%s %s is after the date of death %s - skipped" % (vid, dos, dod)); continue
            cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
            chg_over = {c.get("id"): {"modcodes": " ".join((c.get("modcodes") or "").split() + [GV])} for c in allc if GV not in (c.get("modcodes") or "").split()}
            if done("gv", "%s:%s" % (item, vid)): res.append("v%s already done" % vid); continue
            ok, msg = full_resave(cid, over={"insorder": str(mseq)}, chg_over=chg_over, action="updvisitwithcharges"); res.append("v%s GV + insorder %s: %s %s" % (vid, mseq, ok, msg[:160]))
            if not DRY and ok:
                r1 = freq1_visit.run(vid, cid, int(mseq)); res.append("   freq1 -> %s" % r1); rec("gv", "%s:%s" % (item, vid), "FAULT" not in str(r1) and "BLOCKED" not in str(r1), msg=str(r1)[:160])
    for x in res: L("   " + x)
    out(item, lines=res); return res
def item_scrivener(): medicare_gv("scrivener", "17477375", ["08/11/2026", "08/12/2026", "08/13/2026"])
def item_slater(): medicare_gv("slater", "12179690", ["02/18/2025", "04/14/2025"])

def item_shortall():
    """shortall-kelvin-17474290: TMH (William 03:31Z) BCBS IN STATE HMO (policy # on the sheet) eff 1/1/2025 - the only payer; check Florida Blue at the DOS, rebill if active, else the 9/14 BCBS rule (patient balance -> WOBAD)"""
    pid = "17474290"; res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    res.append("plans %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate"), p.get("sequence")) for p in pl], pa.get("insorder")))
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens: res.append("open: " + fmt(r))
    if not opens: out("shortall", lines=res); L("\n".join(res)); return
    dos = opens[0]["dos"]; d8 = dos[6:] + dos[:2] + dos[3:5]
    try:
        j = stedi.elig("BCBSF", "KELVIN", "SHORTALL", os.environ.get("SHORTALL_DOB8", ""), os.environ.get("SHORTALL_FB_ID", ""), d8); errs = [(e.get("code"), e.get("description")) for e in j.get("errors") or []]
        st = [(b.get("name"), b.get("planCoverage"), b.get("insuranceTypeCode")) for b in (j.get("benefitsInformation") or []) if "30" in (b.get("serviceTypeCodes") or []) or b.get("code") in ("1", "6")][:4]
        pdi = j.get("planDateInformation") or {}; res.append("Stedi Florida Blue (sheet id) @%s: %s errors %s dates %s" % (dos, st, errs, pdi))
        active = any(b.get("code") == "1" for b in (j.get("benefitsInformation") or []))
    except Exception as e: res.append("Stedi error %s" % e); active = None
    fb = [p for p in pl if p.get("carrier") == "car6062"]
    if active:
        if fb and fb[0].get("subscribernum") != os.environ.get("SHORTALL_FB_ID", "") and not DRY:
            ok, msg = ins_update.update(pid, fb[0]["id"], subscribernum=os.environ.get("SHORTALL_FB_ID", ""), enddate=""); res.append("FB id -> sheet id, end cleared: %s" % ok)
        elif fb and fb[0].get("enddate") and not DRY:
            ok, msg = ins_update.update(pid, fb[0]["id"], enddate=""); res.append("FB end date cleared: %s" % ok)
        if not fb and not DRY: fid, fseq = add_ins.add(pid, "car6062", os.environ.get("SHORTALL_FB_ID", ""), "01/01/2025"); res.append("added FB -> %s seq %s" % (fid, fseq)); fb = [{"id": fid, "sequence": fseq}]
        if fb:
            for vid in sorted({r["visit"] for r in opens}): res.append(rebill_visit("shortall", pid, rows, vid, fb[0]["sequence"], fb[0]["sequence"]))
    else: res.append("Florida Blue not active on the DOS (or lookup failed) - left for the 9/14 BCBS rule; nothing changed")
    for x in res: L("   " + x)
    out("shortall", lines=res)

def item_simmonds():
    """simmonds-dougal-17477260: HCA sheet (William 03:37Z) = the same Medicare + Florida Blue MCR Sup (the chart's seq-2 member id; BLUEMEDICARE SUPPLEMENT F) the 835 called 'not eligible' - check the Medigap at the DOS through Stedi and report"""
    pid = "17477260"; res = []; pa, pl = plans(pid)
    res.append("plans %s" % [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("enddate"), p.get("sequence")) for p in pl])
    try:
        j = stedi.elig("BCBSF", "DOUGAL", "SIMMONDS", os.environ.get("SIMMONDS_DOB8", ""), os.environ.get("SIMMONDS_FB_ID", ""), "20260812"); errs = [(e.get("code"), e.get("description")) for e in j.get("errors") or []]
        st = [(b.get("name"), b.get("planCoverage"), b.get("insuranceTypeCode"), b.get("insuranceType")) for b in (j.get("benefitsInformation") or []) if "30" in (b.get("serviceTypeCodes") or []) or b.get("code") in ("1", "6")][:5]
        res.append("Stedi Florida Blue (chart seq-2 id) @8/12/2026: %s errors %s dates %s payer %s" % (st, errs, j.get("planDateInformation"), (j.get("payer") or {}).get("name")))
    except Exception as e: res.append("Stedi error %s" % e)
    for p in pl:
        if p.get("carrier") == "car6062":
            try: s = elig_amd.run_plan(pid, p["id"].replace("ins", ""), True); res.append("AMD 271 FB %s: %s" % (p.get("subscribernum"), elig_amd.one_line(s)[:260]))
            except Exception as e: res.append("AMD 271 failed %s" % e)
    for x in res: L("   " + x)
    out("simmonds", lines=res)

def item_sikora():
    """sikora-lorena-17474671: Pam's 11/12/2025 admit email (IMG_5814): Medicare card LORENA M SIKORA, MBI from the card, Part A 03/01/2012 B 07/01/2015; Philadelphia American (chart id) = the chart's PHI01; AARP MedicareRx = stand-alone Part D -> straight Medicare first, PHI01 second"""
    pid = "17474671"; res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    MBI = os.environ.get("SIKORA_MBI", "")
    res.append("chart name %s dob %s plans %s insorder %s" % (pa.get("name"), pa.get("dob"), [(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("sequence")) for p in pl], pa.get("insorder")))
    if not MBI: res.append("SIKORA_MBI not supplied"); out("sikora", lines=res); L("\n".join(res)); return
    # Medicare spells the first name LORENA (card) - the chart says LORENA; the 271 name match needs the card's spelling
    try:
        p = patient_patch.get(pid); names = p.get("names") or []; cur = (names[0].get("firstname") if names else None) or p.get("firstname")
        res.append("REST first name: %s" % cur)
        if cur and cur.upper() != "LORENA":
            if DRY: res.append("DRY patch first name -> LORENA")
            else:
                n0 = dict(names[0]); n0["firstname"] = "LORENA"
                code, txt, before = patient_patch.patch(pid, {"names": [n0] + names[1:]}); res.append("PATCH first name LORENA -> %s %s" % (code, txt[:100])); rec("name", "sikora", code in (200, 204))
    except Exception as e: res.append("name patch failed %s" % e)
    med = [p for p in pl if p.get("carrier") == "car6085"]
    if med: mid, mseq = med[0]["id"], med[0]["sequence"]; res.append("Medicare already %s %s" % (mid, med[0].get("subscribernum")))
    elif DRY: mid, mseq = None, "?"; res.append("DRY add FLO02 %s begin 01/01/2025" % MBI)
    else: mid, mseq = add_ins.add(pid, "car6085", MBI, "01/01/2025"); res.append("added FLO02 -> %s seq %s" % (mid, mseq)); rec("addplan", "sikora", bool(mid))
    if mid and not DRY:
        try: s = elig_amd.run_plan(pid, re.sub(r"\D", "", mid), True); res.append("AMD 271 Medicare: " + elig_amd.one_line(s)[:260])
        except Exception as e: res.append("AMD 271 failed %s" % e)
    for p in pl:
        if p.get("carrier") == "car6404" and not p.get("enddate") and not DRY:
            ok, msg = ins_update.update(pid, p["id"], enddate="11/01/2025"); res.append("UHC plan %s (AARP MedicareRx = Part D, not medical) end-dated 11/01/2025: %s" % (p["id"], ok))
    ph = [p for p in pl if p.get("carrier") == "car303238"]; pseq = ph[0]["sequence"] if ph else None
    order = ",".join(x for x in (mseq, pseq) if x and x != "?")
    if mseq != "?" and not DRY and pseq: ok, msg = ins_update.update(pid, mid, sequence=order); res.append("patient order -> %s: %s" % (order, ok))
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens: res.append("open: " + fmt(r))
    if mseq != "?":
        for vid in sorted({r["visit"] for r in opens}): res.append(rebill_visit("sikora", pid, rows, vid, order, mseq))
    for x in res: L("   " + x)
    out("sikora", lines=res)

def item_merriwether():
    """merriwether-paxton-nell-x: 'try the BlueOptions id' - the open Florida Blue visits of 3-4/2026 go under the group plan (ins9519429 seq 2, the BlueOptions id) if they are not there already"""
    pid = "17475906"; res = []; pa, pl = plans(pid); rows = chart_rows(pid)
    res.append("plans %s insorder %s" % ([(p.get("id"), p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate"), p.get("sequence")) for p in pl], pa.get("insorder")))
    opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0 and dos_date(r["dos"]) <= datetime.date(2026, 7, 31)]
    for vid in sorted({r["visit"] for r in opens}):
        cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid); r0 = live(rows, vid=vid)[0]
        res.append("v%s %s insorder %s carrier %s billed %s ins %s" % (vid, r0.get("dos"), vis.get("insorder"), r0.get("carrier"), r0.get("billdate"), r0.get("insbal")))
        if vis.get("insorder", "").startswith("2") and (r0.get("billdate") or "") >= "09/16/2026": res.append("   already under the BlueOptions plan since %s - pending, not re-sent" % r0.get("billdate")); continue
        res.append("   " + rebill_visit("merriwether", pid, rows, vid, "2,1", "2"))
    for x in res: L("   " + x)
    out("merriwether", lines=res)

def item_jarvis():
    """jarvis-marisa-17477842: 'just fix the charts and send the claim that will get paid' - copy the real chart's plans onto the 1921-dated duplicate, fix its DOB, bill the 9/20 CCM"""
    dup, real = "17477842", "17472416"; res = []
    pa_r, pl_r = plans(real); pa_d, pl_d = plans(dup)
    res.append("real %s dob %s insorder %s plans %s" % (pa_r.get("name"), pa_r.get("dob"), pa_r.get("insorder"), [(p.get("carrier"), p.get("subscribernum"), p.get("begindate"), p.get("enddate"), p.get("sequence")) for p in pl_r]))
    res.append("dup  %s dob %s insorder %s plans %s" % (pa_d.get("name"), pa_d.get("dob"), pa_d.get("insorder"), [(p.get("carrier"), p.get("subscribernum"), p.get("sequence")) for p in pl_d]))
    if pa_d.get("dob") != pa_r.get("dob"):
        if DRY: res.append("DRY patch dob %s -> %s" % (pa_d.get("dob"), pa_r.get("dob")))
        else:
            try: code, txt, before = patient_patch.patch(dup, {"dob": pa_r.get("dob")}); res.append("PATCH dob -> %s %s" % (code, txt[:100])); rec("dob", "jarvis", code in (200, 204))
            except Exception as e: res.append("dob patch failed %s" % e)
    order = []
    for p in sorted([p for p in pl_r if not p.get("enddate")], key=lambda p: int(p.get("sequence") or 99)):
        have = [q for q in pl_d if q.get("carrier") == p.get("carrier") and q.get("subscribernum") == p.get("subscribernum")]
        if have: order.append(have[0]["sequence"]); res.append("dup already has %s %s" % (p.get("carrier"), p.get("subscribernum"))); continue
        if DRY: res.append("DRY add %s %s begin %s" % (p.get("carrier"), p.get("subscribernum"), p.get("begindate"))); continue
        iid, seq = add_ins.add(dup, p.get("carrier"), p.get("subscribernum"), p.get("begindate") or "01/01/2025"); res.append("added %s %s -> %s seq %s" % (p.get("carrier"), p.get("subscribernum"), iid, seq)); rec("addplan", "jarvis:" + p.get("carrier"), bool(iid))
        if seq: order.append(seq)
    rows = chart_rows(dup); opens = [r for r in live(rows) if float(r.get("insbal") or 0) + float(r.get("patbal") or 0) > 0]
    for r in opens: res.append("open: " + fmt(r))
    if order and not DRY:
        pa_d, pl_d = plans(dup); first_id = [p for p in pl_d if p.get("sequence") == order[0]][0]["id"]
        ok, msg = ins_update.update(dup, first_id, sequence=",".join(order)); res.append("patient order %s: %s" % (",".join(order), ok))
        for vid in sorted({r["visit"] for r in opens}):
            cid = live(rows, vid=vid)[0]["id"]; ok, msg = full_resave(cid, over={"insorder": ",".join(order)}); res.append("v%s insorder %s: %s %s" % (vid, ",".join(order), ok, msg[:140]))
        res.append(release_unbilled(sorted({r["visit"] for r in opens})))
    for x in res: L("   " + x)
    out("jarvis", lines=res)

def item_lazenby():
    """lazenby-carys-17477777: 'recreate the referral plan' - try the 9/21 addreferralplan shape (ismain=0, refprov=rprov13); if a NEW plan comes back, repoint both HCA visits to it (its preauth is blank)"""
    pid = "17477777"; res = []
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}), timeout=120)
    ref = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*>', d)]
    res.append("referral plans: %s" % [(p.get("id"), p.get("ismain"), p.get("refprov"), p.get("preauth"), p.get("status")) for p in ref])
    main = [p for p in ref if p.get("ismain") == "1"]; clean = [p for p in ref if p.get("ismain") != "1" and not (p.get("preauth") or "").strip()]
    newplan = clean[0]["id"] if clean else None
    if not newplan and not DRY:
        for shape in ('<refplan id="" patient="pat%s" ismain="0" status="stat1" preauthreq="0" sequence="2" refprov="%s" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="%s"/>' % (pid, EFFINGER_RPROV, (main[0].get("facility") if main else "") or ""),
                      '<refplan id="" patient="pat%s" ismain="0" status="stat1" preauthreq="0" sequence="3" refprov="%s" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="fac29"/>' % (pid, EFFINGER_RPROV)):
            r = amd.post(amd.msg("addreferralplan", "chargeentry", {"nocookie": "1"}, shape)); m = re.search(r'id="(rplan\d+)"', r)
            got = m.group(1) if m else None; res.append("addreferralplan -> %s (%s)" % (got, re.sub(r"\s+", " ", r[100:260])))
            if got and (not main or got != main[0]["id"]): newplan = got; break
            time.sleep(0.5)
    if not newplan: res.append("no clean referral plan could be created - the main plan's Pre-Auth # stays (UI)"); out("lazenby", lines=res); L("\n".join(res)); return
    res.append("clean plan %s - repointing the open visits" % newplan)
    rows = chart_rows(pid)
    for vid in sorted({r["visit"] for r in live(rows) if float(r.get("insbal") or 0) > 0}):
        cid = live(rows, vid=vid)[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
        if vis.get("refplan") == newplan: res.append("v%s already on %s" % (vid, newplan)); continue
        ok, msg = full_resave(cid, over={"refplan": newplan}); res.append("v%s refplan -> %s: %s %s" % (vid, newplan, ok, msg[:160]))
        if not DRY: rec("refplan", "lazenby:" + vid, ok)
    d2 = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}), timeout=120)
    res.append("referral plans after: %s" % [(p.get("id"), p.get("ismain"), p.get("refprov"), p.get("preauth")) for p in [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*>', d2)]])
    for x in res: L("   " + x)
    out("lazenby", lines=res)

def item_jacobsen_norcott():
    """jacobsen-norcott-j-denials: William 03:41Z 'mine' - re-create the 6/23/2026 visit under prof13 (Effinger) with an Effinger referral plan, frequency 1 to Sunshine. Unpaid only."""
    pid = "17469007"; res = []; rows = chart_rows(pid); pa, pl = plans(pid)
    tgt = [r for r in live(rows) if r.get("dos") == "06/23/2026" and float(r.get("insbal") or 0) > 0]
    res.append("targets: %s" % [fmt(r) for r in tgt])
    if not tgt: out("jacobsen_norcott", lines=res); L("\n".join(res)); return
    vid = tgt[0]["visit"]; cid = tgt[0]["id"]; vis, pat, allc = resave.visit_charges(cid)
    res.append("visit profile %s refplan %s insorder %s charges %s" % (vis.get("profile"), vis.get("refplan"), vis.get("insorder"), [(c.get("id"), c.get("proccode")) for c in allc]))
    if any(p for c in allc for p in re.findall(r'<payment [^>]*amount="([^"]*)"', resave.detail(c.get("id").replace("charge", ""))) if p not in ("0", "0.00", "")): res.append("payment on the visit - not re-rendered"); out("jacobsen_norcott", lines=res); L("\n".join(res)); return
    sseq, _ = seq_of(pl, "car6194")
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}), timeout=120)
    ref = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*>', d)]
    eff = [p for p in ref if p.get("refprov") == EFFINGER_RPROV]; main = [p for p in ref if p.get("ismain") == "1"]
    res.append("referral plans %s" % [(p.get("id"), p.get("ismain"), p.get("refprov")) for p in ref])
    if vis.get("profile") == EFFINGER_PROF and eff and vis.get("refplan") == eff[0]["id"]: res.append("already Effinger-rendered + Effinger referring"); out("jacobsen_norcott", lines=res); L("\n".join(res)); return
    if DRY: res.append("DRY: addreferralplan refprov=rprov13 (if none) -> resave profile=prof13 refplan=<plan> (AMD voids + recreates the charges) -> find the new charges -> freq1 seq %s" % sseq); out("jacobsen_norcott", lines=res); L("\n".join(res)); return
    newplan = eff[0]["id"] if eff else None
    if not newplan:
        r = amd.post(amd.msg("addreferralplan", "chargeentry", {"nocookie": "1"}, '<refplan id="" patient="pat%s" ismain="0" status="stat1" preauthreq="0" sequence="2" refprov="%s" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="%s"/>' % (pid, EFFINGER_RPROV, vis.get("facility") or "")))
        m = re.search(r'id="(rplan\d+)"', r); newplan = m.group(1) if m else None
        if not newplan or (main and newplan == main[0]["id"]): res.append("could not create an Effinger referral plan (%s) - re-render under prof13 only" % newplan); newplan = None
        else: res.append("Effinger referral plan %s" % newplan)
    before = len(allc); over = {"profile": EFFINGER_PROF}
    if newplan: over["refplan"] = newplan
    ok, msg = full_resave(cid, over=over); res.append("re-render resave: %s %s" % (ok, msg[:200]))
    time.sleep(2); rows2 = chart_rows(pid)
    newc = [r for r in live(rows2) if r.get("dos") == "06/23/2026" and float(r.get("insbal") or 0) > 0]
    res.append("live after: %s" % [fmt(r) for r in newc])
    nv = sorted({r["visit"] for r in newc})
    for v2 in nv:
        c2 = live(rows2, vid=v2)[0]["id"]; vis2, p2, allc2 = resave.visit_charges(c2)
        res.append("v%s profile %s refplan %s charges %d (was %d)" % (v2, vis2.get("profile"), vis2.get("refplan"), len(allc2), before))
        r1 = freq1_visit.run(v2, c2, int(sseq)); res.append("   freq1 seq %s -> %s" % (sseq, r1)); rec("rerender", "jacobsen:" + v2, "FAULT" not in str(r1) and "BLOCKED" not in str(r1), msg=str(r1)[:160])
    for x in res: L("   " + x)
    out("jacobsen_norcott", lines=res)

def secondary_fix(item, pid, mseq="1", sseq="2", dos_from=None):
    """Medicare-paid visits whose residual sits on the PATIENT balance (the supplement never got the claim) -> move back to insurance, visit insorder mseq,sseq, send the secondary (rebill seq sseq)"""
    rows = chart_rows(pid); res = []
    for r in live(rows):
        if float(r.get("patbal") or 0) <= 0: continue
        if dos_from and dos_date(r["dos"]) < dos_from: continue
        if not [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]: res.append("patient balance without a primary payment, left: " + fmt(r)); continue
        res.append("coinsurance on the patient: " + fmt(r))
        if done("secondary", "%s:%s" % (item, r["visit"])): res.append("   already sent"); continue
        if DRY: res.append("   DRY move_to_ins %s,%s rebill seq %s" % (mseq, sseq, sseq)); continue
        m = move_to_ins.move(r["id"], "%s,%s" % (mseq, sseq), rebill_seq=int(sseq)); res.append("   " + str(m)); rec("secondary", "%s:%s" % (item, r["visit"]), "FAULT" not in str(m) and "BLOCKED" not in str(m), msg=str(m)[:160]); time.sleep(0.4)
    for x in res: L("   " + x)
    out(item + "_secondary", lines=res)
def item_sayer_secondary(): secondary_fix("sayer", "12180329", "1", "2")
def item_simmonds_secondary(): secondary_fix("simmonds", "17477260", "1", "2", dos_from=datetime.date(2026, 8, 12))

ITEMS = {"bellingham": item_bellingham, "smythe_bexford": item_smythe_bexford, "penhale": item_penhale, "pignone": item_pignone, "reeve": item_reeve, "rodway": item_rodway,
         "rossiter": item_rossiter, "sayer": item_sayer, "scrivener": item_scrivener, "slater": item_slater, "shortall": item_shortall, "simmonds": item_simmonds, "sikora": item_sikora,
         "merriwether": item_merriwether, "jarvis": item_jarvis, "lazenby": item_lazenby, "jacobsen_norcott": item_jacobsen_norcott, "sayer_secondary": item_sayer_secondary, "simmonds_secondary": item_simmonds_secondary}
if __name__ == "__main__":
    amd.login_cached()
    for name, fn in ITEMS.items():
        if ONLY and name not in ONLY: continue
        L("== %s%s" % (name, " (DRY)" if DRY else ""))
        try: fn()
        except Exception as e:
            import traceback; L("   EXCEPTION %s: %s" % (name, traceback.format_exc()[-700:])); out(name, error=str(e)[:300])
    L("== done wave 2")
