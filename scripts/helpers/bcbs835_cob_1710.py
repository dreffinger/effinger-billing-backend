# PLAIN ENGLISH (Florida Blue 835 COB denials -> Medicare first, 1pm ET 9/16/2026 run - step 5(d) denial rule + William 9/7 payer order)
# Decides: the five Florida Blue 835s that reached the ERA Center 9/16 (checks 1051680-1051684) carry 121 PR-22/CO-22
#   "another payer is primary" claim lines. For every such visit that STILL has an open Florida-Blue insurance balance:
#   (A) chart already holds a Medicare plan with an MBI -> visit insurance order = the Medicare sequence (full-visit echo via
#       move_to_ins.move), frequency 1 + chargerebill (freq1_visit.run); charts whose plan 1 is Florida Blue also get the
#       patient default order set Medicare first (ins_update sequence "2,1") - the 9/15 cob_fix_1110.py precedent.
#   (B) chart with NO Medicare plan (pat17477062, pat17476106) -> Stedi MBI lookup at the denied DOS; straight Medicare
#       ACTIVE with no Advantage entity -> add FLO02 (car6085) with that MBI, no group number, AMD free 271 on it, then (A).
#       Anything else -> reported for the board, no AMD write.
#   (C) pat23967: the payer's PR-177 'not eligible' on 2 Florida-Blue visits whose 34 sibling visits already sit on the
#       chart's UHC plan (seq 2) -> same seq-2 re-route. pat17473308 PR-27 (BCBS only plan) -> AMD 271 + Stedi MBI +
#       discovery, reported for the board.
# Rules it uses: William 9/7 Medicare-before-supplement; 9/3 every rebill goes out frequency 1; void trap = full echo;
#   8/31 no group numbers. Never touches: paid charges, $0 charges, payments, charts whose lookup is not clean.
import amd, txh, move_to_ins, freq1_visit, ins_update, add_ins, elig_amd, stedi, json, re, sys, time, os
STAMP = "2026-09-16T1710Z"
DRY = "--dry" in sys.argv
amd.login_cached()
MBI = re.compile(r"^[1-9][A-Z][A-Z0-9][0-9][A-Z][A-Z0-9][0-9][A-Z]{2}[0-9]{2}$")
out = []
def L(rec, s): print("  " + s, flush=True); rec["steps"].append(s)
def reroute(rec, pid, seq, visits):
    for vid, cid in visits:
        if DRY: L(rec, "DRY v%s c%s -> seq %s" % (vid, cid, seq)); continue
        try:
            m = move_to_ins.move(cid, seq); time.sleep(0.6)
            f = freq1_visit.run(vid, cid, seq)
            L(rec, "v%s c%s: move %s | freq1 %s" % (vid, cid, str(m)[:120], str(f)[:80]))
        except Exception as e:
            L(rec, "v%s c%s ERROR %s" % (vid, cid, repr(e)[:160]))
        time.sleep(0.6)
def chart(pid):
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    nm = re.search(r' name="([^"]*)"', d).group(1); last, first = nm.split(",")[0].strip(), nm.split(",")[1].strip().split()[0]
    db = re.search(r' dob="([^"]*)"', d).group(1); m = re.match(r"(\d\d)/(\d\d)/(\d{4})", db)
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*>', d)]
    return first, last, (m.group(3) + m.group(1) + m.group(2)) if m else "", plans

# ---------- (A) charts with a Medicare plan already
PLAN_A = [
    ("17471968", 2, [("19420897", "23325994")], True),
    ("17476868", 2, [("19449478", "23359117")], True),
    ("17476438", 2, [("19448820", "23358245"), ("19449004", "23358565")], True),
    ("17473245", 2, [("19453351", "23363895"), ("19448870", "23358345"), ("19448487", "23357790"), ("19447739", "23356967")], True),
    ("25710", 1, [("19432733", "23339381")], False),
    ("12180329", 1, [("19436826", "23343874"), ("19437109", "23344184")], False),
]
for pid, seq, visits, order_fix in PLAN_A:
    rec = {"pid": pid, "kind": "A-cob-medicare-on-chart", "seq": seq, "steps": []}; print("pat%s" % pid, flush=True)
    first, last, dob, plans = chart(pid)
    med = [p for p in plans if p.get("carrier") == "car6085" and p.get("sequence") == str(seq)]
    if not med or not MBI.match(med[0].get("subscribernum") or ""):
        L(rec, "no Medicare plan at seq %s with a valid MBI - skipped (%s)" % (seq, [(p.get("carrier"), p.get("sequence")) for p in plans])); out.append(rec); continue
    L(rec, "Medicare plan %s seq %s ok" % (med[0].get("id"), seq))
    if order_fix and not DRY:
        try:
            r = ins_update.update(pid, med[0]["id"], sequence="%s,1" % seq); L(rec, "patient order %s,1 -> %s" % (seq, str(r)[:100]))
        except Exception as e: L(rec, "patient order ERROR %s" % repr(e)[:120])
        time.sleep(0.5)
    reroute(rec, pid, seq, visits); out.append(rec)

# ---------- (B) charts with no Medicare plan: Stedi MBI lookup first
PLAN_B = [
    ("17477062", "20260709", [("19447692", "23356920"), ("19447726", "23356954")]),
    ("17476106", "20260407", [("19438056", "23345147"), ("19437958", "23345060"), ("19437935", "23345037"), ("19437865", "23344986")]),
    ("17473308", "20251025", [("19421060", "23326320")]),   # PR-27 coverage terminated on Florida Blue; Stedi: Medicare A 4/2025, B 5/2025
]
END_OLD = {"17473308": ("car6062", "10/24/2025")}   # end-date the dead plan the day before the first denied DOS
for pid, dos, visits in PLAN_B:
    rec = {"pid": pid, "kind": "B-cob-no-medicare-plan", "steps": []}; print("pat%s" % pid, flush=True)
    first, last, dob, plans = chart(pid)
    if any(p.get("carrier") == "car6085" for p in plans):
        L(rec, "Medicare plan already on chart - left for the next run to re-route"); out.append(rec); continue
    try:
        j = stedi.mbi(first, last, dob, "FL", dos)
        os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_mbi_%s_%s.json" % (pid, dos, STAMP), "w"), indent=1)
        s = stedi.med_summ(j); L(rec, "Stedi MBI lookup @%s: %s | errors %s" % (dos, json.dumps(s)[:600], str(j.get("errors", ""))[:200]))
    except Exception as e:
        L(rec, "Stedi MBI ERROR %s" % repr(e)[:200]); out.append(rec); continue
    mbi = s.get("mbi")
    active = bool(s.get("partA") or s.get("partB"))
    ma = any(o.get("code") in ("U", "R") and (o.get("type") or "") not in ("OT", "MA", "MB", "QM") and "PRESCRIPTION" not in json.dumps(o).upper() and "PART D" not in json.dumps(o).upper() for o in s.get("other") or [])
    death = bool(s.get("death"))
    L(rec, "verdict: mbi=%s active=%s advantage-entity=%s death=%s" % (mbi, active, ma, death))
    if not (mbi and MBI.match(mbi) and active and not ma and not death):
        L(rec, "not a clean straight-Medicare picture - no AMD write; board row"); out.append(rec); continue
    if DRY: L(rec, "DRY would add FLO02 %s and re-route %s" % (mbi, visits)); out.append(rec); continue
    try:
        pb = s.get("partB") or s.get("partA") or ""; bd = "%s/%s/%s" % (pb[4:6], pb[6:8], pb[:4]) if len(pb) == 8 else "01/01/2025"
        insid, seq = add_ins.add(pid, "car6085", mbi, bd); L(rec, "add_ins car6085 begin %s -> %s seq %s" % (bd, insid, seq))
    except Exception as e:
        L(rec, "add_ins ERROR %s" % repr(e)[:160]); out.append(rec); continue
    if not insid: out.append(rec); continue
    time.sleep(0.6)
    try:
        r = ins_update.update(pid, insid, sequence="%s,1" % seq); L(rec, "patient order %s,1 -> %s" % (seq, str(r)[:100]))
    except Exception as e: L(rec, "patient order ERROR %s" % repr(e)[:120])
    time.sleep(0.6)
    try:
        e2 = elig_amd.run_plan(pid, insid, force=True); L(rec, "AMD 271 on %s: %s" % (insid, (elig_amd.one_line(e2) if not isinstance(e2, str) else e2)[:300]))
    except Exception as e: L(rec, "AMD 271 ERROR %s" % repr(e)[:120])
    if pid in END_OLD:
        car, ed = END_OLD[pid]
        for p in plans:
            if p.get("carrier") == car and not p.get("enddate"):
                try:
                    r = ins_update.update(pid, p["id"], enddate=ed); L(rec, "end-date %s %s %s -> %s" % (p["id"], car, ed, str(r)[:100]))
                except Exception as e: L(rec, "end-date ERROR %s" % repr(e)[:120])
                time.sleep(0.5)
    rec["seq"] = seq; reroute(rec, pid, int(seq), visits); out.append(rec)

# ---------- (C) pat23967 PR-177 -> UHC seq 2 (siblings already there); pat17473308 PR-27 lookups
rec = {"pid": "23967", "kind": "C-pr177-to-uhc-seq2", "seq": 2, "steps": []}; print("pat23967", flush=True)
first, last, dob, plans = chart("23967")
uhc = [p for p in plans if p.get("carrier") == "car6404" and p.get("sequence") == "2"]
if uhc: L(rec, "UHC plan %s seq 2 ok" % uhc[0].get("id")); reroute(rec, "23967", 2, [("19420037", "23325015"), ("19422019", "23327375")])
else: L(rec, "no UHC plan at seq 2 - skipped")
out.append(rec)
json.dump(out, open("registers/bcbs835_cob_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
print("saved registers/bcbs835_cob_%s%s.json" % (STAMP, "_dry" if DRY else ""))
