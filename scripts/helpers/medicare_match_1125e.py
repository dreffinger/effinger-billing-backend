# PLAIN ENGLISH (three Medicare identity corrections from the sheets and cards William pasted on the board 11/25/2026, 07:49-07:57Z)
# Decides: whether the correction William's document gives is the one Medicare holds - AdvancedMD's free Medicare check (271) must
#   answer ACTIVE (or INACTIVE with a date of death: Medicare then identifies the person - the correction is right, 11/25 lesson) once
#   the chart carries it; anything else and the old value goes back and the card says so.
#   chart 17476865 (card rowantree-[first]-17476865-medicare-match): face sheet + photo ID say the birth date is three years earlier than
#     the chart's; the Medicare card's number already equals the chart's. Patch dob; on ACTIVE ask Medicare (Stedi plain check, $0.30)
#     dated to the open visit's date 09/20/2026 - when it names the Florida Blue BlueMedicare (PPO) plan in force, add BCBS car6062
#     with the card's member number (no group), chart order Florida Blue first / Medicare second, ONE re-route of v19455672 to Florida Blue;
#     when straight Medicare was in force, ONE frequency-1 resend of v19455672 to Medicare.
#   chart 17473460 (card [name]-17473460-medicare-match): Medicare answers 73 (name); the TMH sheet names him with the suffix JR
#     and middle initial P. Patch the billing name's suffix first (JR); if 73 stays, add the middle initial; on ACTIVE resend every
#     unpaid Medicare visit of the chart once (frequency 1, seq 1).
#   chart 17477168 (card [name]-17477168-medicare-match): Medicare answers 73 (name); the HCA sheet names him WHITBY JR, JASPER.
#     Patch suffix JR; on ACTIVE resend the chart's unpaid Medicare visit once.
# Rules it uses: patient_patch.patch = the captured demographics PATCH (read-before-write, originalpatient echoed); elig_amd.run_plan =
#   the free 271; stedi.medicare = the plain Medicare check; add_ins.add (no group number); ins_update.update sequence= (verified);
#   freq1_visit.reroute / freq1_visit.run = ONE rebill per visit (deceased guard inside). A visit with any payment is never re-sent.
# Never touches: paid lines, other fields, other charts. --dry (default) reads and lists. Register registers/medicare_match_2026-11-25T0809Z[_dry].json.
# Usage: NEW_DOB_17476865=<yyyy-mm-ddT00:00:00> BCBS_MEMBER_17476865=<member id> python3 medicare_match_1125e.py [--live] [--only <pid>]
import amd, patient_patch, elig_amd, freq1_visit, stedi, txh, json, sys, copy, os, re, time
LIVE = "--live" in sys.argv; S = "2026-11-25T0809Z"
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
NEW_DOB = os.environ.get("NEW_DOB_17476865", ""); BCBS_MEMBER = os.environ.get("BCBS_MEMBER_17476865", "")
JOBS = [
    {"pid": "17476865", "ins": "ins9518219", "kind": "dob", "new": NEW_DOB, "open_visit": ("19455672", "23367044"), "dos8": "20260920"},
    # 17473460 (read 11/25 08:3xZ): Medicare PAYS this chart under the chart's spelling (payments on 2025-2026 visits up to 11/18/2026);
    #   the open balances are Medicare coinsurance at the Florida Blue secondary and three $0 Medicare answers of 01/2026 - nothing is
    #   re-sent here (resend False): the name fix only makes the eligibility check match.
    {"pid": "17473460", "ins": "ins9514066", "kind": "name", "suffix": "JR", "middle": "P", "resend": False},
    {"pid": "17477168", "ins": "ins9518582", "kind": "name", "suffix": "JR", "middle": "", "resend": True},
]
amd.login_cached(); out = {"stamp": S, "live": LIVE, "jobs": []}
def open_medicare_visits(pid):
    """(visit, charge, dos, cpt, insbal) of every live charge with an open insurance balance at FLO02 and no payment - one entry per charge."""
    rows = []
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        if a.get("carrier") != "FLO02" or float(a.get("insbal") or 0) <= 0: continue
        pays = [p for p in c.iter("payment") if p.get("void") not in ("1", "true") and float(p.get("amount") or 0) != 0]
        if pays: continue
        rows.append((a.get("visit"), a.get("id"), a.get("dos"), a.get("proccode"), a.get("insbal")))
    return rows
def check(pid, ins):
    s = elig_amd.run_plan(pid, ins, force=True); return s, elig_amd.one_line(s)[:240]
for j in JOBS:
    pid = j["pid"]
    if ONLY and pid != ONLY: continue
    rec = {"pid": pid, "kind": j["kind"]}
    p = patient_patch.get(pid); f = patient_patch.flatten(p)
    names = copy.deepcopy(f.get("names") or [])
    opens = open_medicare_visits(pid); rec["open_medicare_charges"] = opens
    tot = sum(float(x[4]) for x in opens)
    print("pat%s dob %s names %s | open Medicare charges %d ($%.2f): %s" % (pid, f.get("dob"), [(n.get("firstname"), n.get("middlename"), n.get("lastname"), n.get("suffix")) for n in names], len(opens), tot, [(x[0], x[2], x[3], x[4]) for x in opens]))
    if j["kind"] == "dob":
        if not NEW_DOB: print("  no NEW_DOB given - skipped"); out["jobs"].append(rec); continue
        changes = {"dob": NEW_DOB}; back = {"dob": f.get("dob")}
    else:
        n2 = copy.deepcopy(names)
        for n in n2: n["suffix"] = j["suffix"]
        changes = {"names": n2}; back = {"names": copy.deepcopy(names)}
    if not LIVE:
        print("  DRY - would patch %s, 271 on %s, keep on ACTIVE / date of death, else restore; then the resend" % (changes if j["kind"] != "names" else "suffix", j["ins"])); out["jobs"].append(rec); continue
    code, txt, _ = patient_patch.patch(pid, changes); rec["patch"] = [code, str(txt)[:160]]; print("  PATCH", code, str(txt)[:160])
    s, line = check(pid, j["ins"]); rec["271"] = line; print("  271:", line)
    if j["kind"] == "name" and s.get("status") != "ACTIVE" and not s.get("date_of_death") and j.get("middle"):
        n3 = copy.deepcopy(patient_patch.flatten(patient_patch.get(pid)).get("names") or [])
        for n in n3: n["middlename"] = j["middle"]
        code, txt, _ = patient_patch.patch(pid, {"names": n3}); rec["patch2"] = [code, str(txt)[:160]]; print("  PATCH middle", code, str(txt)[:160])
        s, line = check(pid, j["ins"]); rec["271b"] = line; print("  271 (with middle):", line)
    dod = s.get("date_of_death")
    if s.get("status") == "ACTIVE" or dod:
        rec["outcome"] = "kept - Medicare ACTIVE" if not dod else "kept - Medicare identifies the chart; INACTIVE, date of death %s" % dod
        if dod:
            import deceased_guard; deceased_guard._put(pid, {"dod": dod, "src": "AMD 271 %s" % S, "at": S}); rec["dod"] = dod
            print("  OUTCOME:", rec["outcome"], "- nothing re-sent; charges after the date go to the void rule"); out["jobs"].append(rec); continue
        if j["kind"] == "dob":
            # Medicare's dated answer for the open visit's date decides the payer
            f2 = patient_patch.flatten(patient_patch.get(pid)); dob8 = (f2.get("dob") or "")[:10].replace("-", "")
            first = names[0].get("firstname"); last = names[0].get("lastname")
            jj = stedi.medicare(first, last, dob8, s.get("subscriber_id") or "[MBI]", j["dos8"], pid=pid, who="billing button 0809Z rowantree card")
            jj = jj[0] if isinstance(jj, tuple) else jj
            summ = stedi.med_summ(jj) if isinstance(jj, dict) else {}
            rec["stedi_dated"] = {k: summ.get(k) for k in ("partA", "partB", "death", "errors", "other")}
            json.dump(jj, open("patient_db/%s/stedi_medicare_%s.json" % (pid, j["dos8"]), "w"))
            ma = [o for o in (summ.get("other") or []) if o.get("code") in ("U", "HM", "HN") or (o.get("type") == "HN")]
            print("  Stedi dated %s: A %s B %s death %s MA %s" % (j["dos8"], summ.get("partA"), summ.get("partB"), summ.get("death"), [(o.get("entity"), o.get("dates")) for o in ma]))
            vid, cid = j["open_visit"]
            if ma and any("BLUE" in str(o.get("entity")).upper() or "FLORIDA" in str(o.get("entity")).upper() for o in ma):
                if not BCBS_MEMBER: rec["outcome"] += " - MA plan named but no BCBS_MEMBER given; nothing re-sent"; print("  no BCBS member id given"); out["jobs"].append(rec); continue
                import add_ins, ins_update
                begin = None
                for o in ma:
                    d = (o.get("dates") or {}); begin = d.get("coordinationOfBenefits") or d.get("plan") or d.get("benefit")
                begin = (begin or "20260101")[:8]; begin_mdy = "%s/%s/%s" % (begin[4:6], begin[6:8], begin[0:4])
                r = add_ins.add(pid, "car6062", BCBS_MEMBER, begin_mdy, "MC") if add_ins.add.__code__.co_argcount >= 5 else add_ins.add(pid, "car6062", BCBS_MEMBER, begin_mdy)
                rec["add_ins"] = str(r)[:200]; print("  add_ins BCBS ->", str(r)[:200])
                m = re.search(r"(ins\d+)", str(r)); newins = m.group(1) if m else None
                t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
                plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', t)]
                bc = [q for q in plans if q.get("carrier") == "car6062"]; seqb = bc[-1].get("sequence") if bc else None
                newins = newins or (bc[-1].get("id") if bc else None)
                r2 = ins_update.update(pid, newins, sequence="%s,1" % seqb); rec["order"] = str(r2)[:200]; print("  chart order %s,1 ->" % seqb, str(r2)[:200])
                s2, line2 = check(pid, newins); rec["271_bcbs"] = line2; print("  271 BCBS:", line2)
                rr = freq1_visit.reroute(vid, cid, "%s,1" % seqb, seqb); rec["reroute"] = str(rr)[:300]; print("  reroute v%s ->" % vid, rr)
            else:
                rr = freq1_visit.run(vid, cid, "1"); rec["resend"] = str(rr)[:200]; print("  resend v%s to Medicare ->" % vid, rr)
        elif not j.get("resend", True):
            rec["resent"] = "nothing - Medicare already pays this chart; open balances are secondary coinsurance / $0 Medicare answers (see the card)"
        else:
            sent = {}
            for vid, cid, dos, cpt, bal in opens:
                if vid in sent: continue
                sent[vid] = str(freq1_visit.run(vid, cid, "1"))[:120]; print("  resend v%s %s ->" % (vid, dos), sent[vid]); time.sleep(0.4)
            rec["resent"] = sent
    else:
        c2, t2, _ = patient_patch.patch(pid, back); rec["outcome"] = "restored - Medicare %s (%s)" % (s.get("status"), line); print("  restored", c2, str(t2)[:100])
    print("  OUTCOME:", rec.get("outcome")); out["jobs"].append(rec)
json.dump(out, open("registers/medicare_match_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
