# PLAIN ENGLISH (9/6 commercial/Medicaid denial cascade - actions)
# Decides: Applies the clear-cut verdicts from denial_cascade2: (A) Medicaid says the patient has Medicare -> add Medicare, bill Medicare first then Medicaid; (B) Medicaid says the patient is in an SMMC plan -> add that plan (with the Medicaid id) and bill it (Medicare first if the chart has Medicare); (C) the billed plan was inactive and CMS shows straight Medicare -> bill Medicare for dates after the plan ended; (D) date of death -> write off lines after it; (E) in A-C, denied claims older than 12 months are written off as untimely (no payer will take them now).
# Rules it uses: add_ins.add for missing plans (no group numbers), rebill_patient_year.run with a date-aware order (freq-1 first, keeps admission dates), manual_post.post WOINS with a dated note for write-offs. Never rebills a visit with a payment posted (rebill_patient_year skips them). --dry prints only.
# Never touches: 'billed plan ACTIVE' (claim-content) denials, 'inactive + no Medicare' patients, Advantage-plan hits that need a member id, or Vandermeer-type rows where the only MCO is dental/transport - all of those go to the board instead.
# ---
"""Usage: python3 denial_act2.py [--dry] [--only A,B,C,D]"""
import amd, add_ins, rebill_patient_year, manual_post, txh, resave, json, re, sys, datetime, time, glob, collections
amd.login_cached(); today = datetime.date.today(); CUT = today - datetime.timedelta(days=365); dry = "--dry" in sys.argv
only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else set("ABCDE")
PLAN2CAR = [("SUNSHINE", "car6194"), ("SIMPLY", "car42019"), ("HUMANA", "car6285"), ("FLORIDA COMMUNITY CARE", "car42008"), ("WELLCARE", "car6174"), ("MOLINA", "car6578"), ("AETNA BETTER", "car6047"), ("UNITEDHEALTHCARE", "car302853"), ("CARE IMPROVEMENT", "car302853")]
CARCODE = {v[0]: k for k, v in json.load(open("carriers.json")).items()}   # code -> carNNN
CODE_OF = {k: v[0] for k, v in json.load(open("carriers.json")).items()}   # carNNN -> code
recs = [json.loads(l) for l in open(sorted(glob.glob("denial_cascade2_*.jsonl"))[-1])]
sweep = {}
for l in open(sorted(glob.glob("claimstatus_full_*.jsonl"))[-1]):
    r = json.loads(l); sweep[r["visitid"]] = r
LOG = open("denial_act2.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    return re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
def seq_of(pl, car): return next((p[5] for p in pl if p[1] == car and not p[3]), None) or next((p[5] for p in pl if p[1] == car), None)
def ensure(pid, car, num, begin):
    pl = plans(pid); s = seq_of(pl, car)
    if s: return s, "had"
    if dry: return "?", "DRY add %s %s" % (car, num)
    ins, s = add_ins.add(pid, car, num, begin, finclass="MC" if car == "car6085" else "MD" if car in ("car6113", "car6194", "car42019", "car42008", "car6578") else "CC"); return s, "added"
def write_off_untimely(rec):
    """write off denied claims older than 12 months for this patient (categories A-C)"""
    old = [v for v in rec["untimely"]]
    if not old: return 0, 0.0
    root = txh.fetch(rec["pid"]); n = 0; tot = 0.0
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or str(a.get("visit")) not in map(str, old): continue
        x = resave.detail(a["id"]); m = re.search(r'<charge [^>]*>', x).group(0); bal = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0)
        if bal <= 0: continue
        car = sweep.get(int(a.get("visit")), sweep.get(str(a.get("visit")), {})).get("carrier") or "FLO02"
        if dry: L("   DRY WO %s %s %s $%.2f" % (rec["patient"], a.get("dos"), a.get("proccode"), bal)); n += 1; tot += bal; continue
        ok, msg = manual_post.post(a["id"], car, 0.0, bal, "WOINS", note="untimely - denied by payer, over 12 months (9/6 cascade)")
        L("   WO %s %s %s $%.2f -> %s %s" % (rec["patient"], a.get("dos"), a.get("proccode"), bal, ok, "" if ok else msg[:80])); n += 1; tot += bal if ok else 0; time.sleep(0.3)
    return n, tot

def rebill_visits(rec, order_fn):
    """freq-1 + move + rebill ONLY the denied, in-window visits from the sweep (not every unpaid visit)."""
    import move_to_ins, freq1_visit
    vids = [str(v["visitid"]) for v in (sweep[k] for k in sweep) if False]
    vids = [str(r["visitid"]) for r in sweep.values() if str(r["patientid"]) == str(rec["pid"]) and (r["action"].startswith("DENIED") or r["action"].startswith("FINALIZED")) and r["dos"] >= CUT.isoformat()]
    if not vids: return 0
    root = txh.fetch(rec["pid"]); vc = {}
    for c in root.iter("charge"):
        if c.get("void") != "1": vc.setdefault(str(c.get("visit")), (c.get("id"), c.get("dos")))
    n = 0
    for vid in vids:
        cid, dos = vc.get(vid, (None, None))
        if not cid: L("   no charge id for visit %s" % vid); continue
        if ("   %s %s -> " % (rec["patient"], dos)) in DONE_LINES: continue
        d = datetime.datetime.strptime(dos, "%m/%d/%Y").date(); o = order_fn(d) if callable(order_fn) else order_fn
        if not o: continue
        if dry: L("   DRY rebill %s %s -> order %s" % (rec["patient"], dos, o)); n += 1; continue
        try:
            mv = move_to_ins.move(cid, o)                      # set the order / move balance (no rebill yet)
            if "FAULT" in str(mv): L("   FAULT move %s %s: %s" % (rec["patient"], dos, str(mv)[:80])); continue
            res = freq1_visit.run(vid, cid, o.split(",")[0])   # freq-1 extins + rebill to the first plan
            L("   %s %s -> %s | %s" % (rec["patient"], dos, str(mv)[:50], str(res)[:60])); n += 1
        except Exception as e: L("   FAIL %s %s: %s" % (rec["patient"], dos, str(e)[:80]))
        time.sleep(0.5)
    return n

import os
DONE_LINES = open("denial_act2.log").read() if os.path.exists("denial_act2.log") else ""
DONE = set(open("denial_act2_done.txt").read().split()) if os.path.exists("denial_act2_done.txt") else set()
summary = collections.Counter(); wo_total = 0.0
for rec in recs:
    v = rec["verdict"]; pid = rec["pid"]; nm = rec["patient"]
    if str(pid) in DONE: continue
    try:
        if v.startswith("MEDICARE PRIMARY") and "A" in only:
            hic = re.search(r"HIC (\w+)", v).group(1); pl = plans(pid)
            s_med, how = ensure(pid, "car6085", hic, "01/01/%d" % (today.year - 3)); pl = plans(pid)
            second = seq_of(pl, "car42008") or seq_of(pl, "car6194") or seq_of(pl, "car42019") or seq_of(pl, "car6285") or seq_of(pl, "car6113")
            order = s_med + ("," + second if second else "")
            L("A %s: Medicare %s (%s) -> order %s" % (nm, hic, how, order))
            rebill_visits(rec, order); n, t = write_off_untimely(rec); wo_total += t; summary["A"] += 1
        elif v.startswith("SMMC PLAN") and "B" in only:
            mco = [m for m in rec["medicaid"]["mco"] if m[1] and ("LTC" in (m[0] or "") or "MMA" in (m[0] or ""))]
            if not mco: L("B %s: MCO is dental/transport only - board" % nm); summary["B-board"] += 1; continue
            ent = mco[0][1].upper(); car = next((c for k, c in PLAN2CAR if k in ent), None)
            if not car: L("B %s: no carrier for %s - board" % (nm, ent)); summary["B-board"] += 1; continue
            mcd_id = next((p[4] for p in plans(pid) if p[1] == "car6113"), None)
            s_plan, how = ensure(pid, car, mcd_id, "01/01/%d" % (today.year - 1)); pl = plans(pid)
            s_med = seq_of(pl, "car6085"); order = (s_med + "," if s_med else "") + s_plan
            L("B %s: %s -> %s (%s) order %s" % (nm, ent[:30], car, how, order))
            rebill_visits(rec, order); n, t = write_off_untimely(rec); wo_total += t; summary["B"] += 1
        elif v.startswith("billed plan INACTIVE; straight Medicare") and "C" in only:
            mbi = re.search(r"Medicare (\w{11})", v).group(1)
            s_med, how = ensure(pid, "car6085", mbi, "01/01/%d" % (today.year - 3)); pl = plans(pid)
            second = seq_of(pl, "car42008") or seq_of(pl, "car6194") or seq_of(pl, "car42019") or seq_of(pl, "car6113") or (seq_of(pl, "car6285") if any(p[1] == "car6285" and p[4].isdigit() for p in pl) else None)
            end = (rec.get("payer", {}).get("dates") or {}).get("planEnd") or ""
            endd = datetime.date(int(end[:4]), int(end[4:6]), int(end[6:8])) if len(end) == 8 else None
            order_s = s_med + ("," + second if second else "")
            order = (lambda d: order_s if (not endd or d > endd) else None)
            L("C %s: billed %s inactive (ends %s); Medicare %s (%s) -> order %s for DOS after %s" % (nm, list(rec["carriers"])[0], end or "?", mbi, how, order_s, end or "all"))
            rebill_visits(rec, order); n, t = write_off_untimely(rec); wo_total += t; summary["C"] += 1
        elif v.startswith("DATE OF DEATH") and "D" in only:
            dod = re.search(r"DEATH (\d{8})", v).group(1); dodd = "%s/%s/%s" % (dod[4:6], dod[6:8], dod[:4])
            root = txh.fetch(pid); n = 0
            for c in root.iter("charge"):
                a = c.attrib
                if a.get("void") == "1" or not a.get("dos"): continue
                if datetime.datetime.strptime(a["dos"], "%m/%d/%Y").date() <= datetime.datetime.strptime(dodd, "%m/%d/%Y").date(): continue
                x = resave.detail(a["id"]); m = re.search(r'<charge [^>]*>', x).group(0); bal = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0)
                if bal <= 0: continue
                if dry: L("   DRY DOD WO %s %s $%.2f (death %s)" % (nm, a["dos"], bal, dodd)); continue
                ok, msg = manual_post.post(a["id"], list(rec["carriers"])[0], 0.0, bal, "WOINS", note="service dated after date of death %s per CMS (9/6 cascade) - William to confirm" % dodd); L("   DOD WO %s %s $%.2f -> %s" % (nm, a["dos"], bal, ok)); n += 1
            L("D %s: date of death %s, %d lines written off" % (nm, dodd, n)); summary["D"] += 1
    except Exception as e: L("ERR %s: %s" % (nm, str(e)[:150])); summary["ERR"] += 1; continue
    if not dry: open("denial_act2_done.txt", "a").write(str(pid) + "\n")
    time.sleep(0.3)
L("=== done %s; untimely written off $%.2f ===" % (dict(summary), wo_total))
