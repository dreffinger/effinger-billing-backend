# PLAIN ENGLISH (pat17475906 COB group-plan fix, 1am ET 9/16/2026 run - William's HCA facesheet paste on the board 04:22Z)
# Decides: the chart's only plan is the BlueMedicare PPO (MA) XJPH45679241; CMS and the facesheet say an EMPLOYER-GROUP
#   Florida Blue plan (BLUE OPTIONS PPO, policy [member id], the employer group on the facesheet) was PRIMARY
#   1/1/2025-7/31/2026 (Medicare Secondary Working Aged), which is why the MA plan reversed the 3/29/2026 99232 CO-22/N598.
#   Steps: (1) Stedi BCBSF eligibility on XJBH22972394 at DOS 3/29/2026; (2) add the plan (car6062, NO group number,
#   begin 01/01/2025), end-date it 07/31/2026, set the patient order group-plan first (sequence "2,1"); (3) AMD free 271 on
#   the new plan; (4) every open Florida-Blue charge dated inside 1/1/2025-7/31/2026 (the March + April 2026 HCA stays,
#   $1,459) -> visit insorder = the new sequence (full-visit echo) + frequency-1 rebill. --check = steps 1 only; --add = 1-3;
#   --rebill = 4 (needs the sequence from --add).  Rules: William 9/7 lookup order; 8/31 no group numbers; 9/3 freq-1 for
#   claims that never reached the payer under that policy; void trap = full echo. Never touches: paid charges, payments.
import amd, stedi, add_ins, ins_update, elig_amd, move_to_ins, freq1_visit, txh, json, re, sys, time
PID = "17475906"; MEMBER = "XJBH22972394"; DOS = "20260329"; STAMP = "2026-09-16T0510Z"
mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
rec = {"pid": PID, "stamp": STAMP, "steps": []}
def L(s): print(s, flush=True); rec["steps"].append(s)
amd.login_cached()
# subscriber name / DOB come from the chart at run time (never literals in this file)
_d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
_nm = re.search(r' name="([^"]*)"', _d).group(1); LAST, FIRST = _nm.split(",")[0].strip(), _nm.split(",")[1].strip().split()[0]
_db = re.search(r' dob="([^"]*)"', _d).group(1); _m = re.match(r"(\d\d)/(\d\d)/(\d{4})", _db); DOBYMD = _m.group(3) + _m.group(1) + _m.group(2)
if mode in ("--check", "--add"):
    try:
        import os; os.makedirs("patient_db/%s" % PID, exist_ok=True)
        j = stedi.elig("BCBSF", FIRST, LAST, DOBYMD, MEMBER, DOS)
        json.dump(j, open("patient_db/%s/stedi_elig_BCBSF_%s_%s.json" % (PID, MEMBER, DOS), "w"), indent=1)
        L("Stedi BCBSF %s @%s: %s | errors %s" % (MEMBER, DOS, json.dumps(stedi.med_summ(j))[:500], str(j.get("errors", ""))[:200]))
        act = any(b.get("code") == "1" for b in j.get("benefitsInformation", [])); inact = any(b.get("code") == "6" for b in j.get("benefitsInformation", []))
        rec["stedi"] = "ACTIVE" if act else ("INACTIVE" if inact else "UNKNOWN")
        L("Stedi verdict: %s" % rec["stedi"])
    except Exception as e:
        L("Stedi ERR %s" % repr(e)[:300]); rec["stedi"] = "ERR"
if mode == "--add":
    if rec.get("stedi") not in ("ACTIVE",) and "--force" not in sys.argv:
        L("not ACTIVE on Stedi - stopping before any AMD write (use --force after reading the 271)"); json.dump(rec, open("registers/cob_group_fix_%s.json" % STAMP, "w"), indent=1); sys.exit(0)
    insid, seq = add_ins.add(PID, "car6062", MEMBER, "01/01/2025")
    L("add_ins car6062 %s begin 01/01/2025 -> %s seq %s" % (MEMBER, insid, seq)); rec["insid"] = insid; rec["seq"] = seq
    if not insid: json.dump(rec, open("registers/cob_group_fix_%s.json" % STAMP, "w"), indent=1); sys.exit(1)
    time.sleep(0.6)
    try:
        r = ins_update.update(PID, insid, enddate="07/31/2026"); L("enddate 07/31/2026 -> %s" % str(r)[:160])
    except Exception as e: L("enddate ERR %s" % repr(e)[:200])
    time.sleep(0.6)
    try:
        r = ins_update.update(PID, insid, sequence="%s,1" % seq); L("patient order %s,1 -> %s" % (seq, str(r)[:160]))
    except Exception as e: L("patient order ERR %s" % repr(e)[:200])
    time.sleep(0.6)
    try:
        s = elig_amd.run_plan(PID, insid, force=True); L("AMD 271 on %s: %s" % (insid, elig_amd.one_line(s)[:400] if not isinstance(s, str) else s[:400]))
    except Exception as e: L("AMD 271 ERR %s" % repr(e)[:200])
if mode == "--rebill":
    seq = sys.argv[2]
    vis = []
    for c in txh.fetch(PID).iter("charge"):
        if c.get("void") == "1": continue
        cid = re.sub(r"\D", "", c.get("id") or ""); dos = c.get("dos") or c.get("dateofservice") or ""
        car = c.get("carrier") or c.get("carriercode") or ""
        m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dos); ymd = (m.group(3) + m.group(1) + m.group(2)) if m else ""
        if car == "BCBS" and float(c.get("insbalance") or c.get("insbal") or 0) > 0 and "20250101" <= ymd <= "20260731":
            vis.append((c.get("visitid") or c.get("visit"), cid, dos, c.get("proccode"), c.get("insbalance") or c.get("insbal")))
    seen = set(); vis = [v for v in vis if not (v[0] in seen or seen.add(v[0]))]
    L("open BCBS visits 1/2025-7/2026: %s" % vis)
    for vid, cid, dos, cpt, bal in vis:
        try:
            m = move_to_ins.move(cid, int(seq)); time.sleep(0.6)
            f = freq1_visit.run(vid, cid, int(seq))
            L("v%s c%s %s %s $%s: move %s | freq1 %s" % (vid, cid, dos, cpt, bal, str(m)[:120], str(f)[:80]))
        except Exception as e:
            L("v%s c%s ERROR %s" % (vid, cid, repr(e)[:200]))
        time.sleep(0.6)
json.dump(rec, open("registers/cob_group_fix_%s_%s.json" % (STAMP, mode.strip("-")), "w"), indent=1)
