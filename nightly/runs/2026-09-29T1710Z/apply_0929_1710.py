# PLAIN ENGLISH (1 PM ET 9/29 slot, run 2026-09-29T1710Z): the CHP -> Medicare payer switch on two charts (pat21483, pat22322).
#  Evidence: CHP (CAP07) posted $0 on EVERY claim since 10/2025 (pat21483) / 3/2026 (pat22322) and AMD transferred the whole charge
#  to the PATIENT balance; CHP's 9/29 ERA says PR-200 'lapse in coverage'; CHP's own 271 answers AAA 75; Stedi's CMS MBI lookup at the
#  oldest DOS and today shows straight Medicare ACTIVE with NO Advantage entity on either chart (MBIs in local_pr200_1710.json - never in the repo).
#  William's rules: wrong-payer denials never stay on the patient balance; add the real plan (no group #), end-date the dead plan the day
#  before the first denied DOS, Medicare first, move the balances back, frequency-1 rebill. Every DOS is inside Medicare's 12-month window.
#  Steps: add FLO02 (car6085) with the MBI, AMD free 271 on it, end-date CAP07, patient order = Medicare, then per open unpaid visit:
#  extins reset to frequency 1, move_to_ins.move(cid, seq, rebill_seq=seq) (full-visit echo, patient balance -> insurance, rebill 204).
# Never touches: payments, write-offs, hospitalizationto, visits with a payment, other charts.
import amd, add_ins, ins_update, move_to_ins, resave, re, json, time, sys
DRY = "--dry" in sys.argv
amd.login_cached()
L = lambda m: print(m, flush=True)
loc = json.load(open("local_pr200_1710.json"))
PLAN = {"21483": {"chp_ins": "ins7357", "chp_end": "10/05/2025"}, "22322": {"chp_ins": "ins499", "chp_end": "03/27/2026"}}
out = {"stamp": "2026-09-29T1710Z", "dry": DRY, "charts": {}}
def elig(insid):
    e = amd.check_eligibility(insid.replace("ins", "")); s = re.sub(r"\s+", " ", e)
    return "ACTIVE" if re.search(r'EB\*1\*', s) else ("INACTIVE" if re.search(r'EB\*6\*', s) else ("REJECTED " + " ".join(re.findall(r'AAA\*[^~]*', s))[:80] if "AAA*" in s else "?"))
def freq1_reset(vid, allc, vis):
    e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
    base.update({"resubmissioncode": "1", "origrefnum": ""})
    for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
    base = resave.clean_extins(base)
    for pc in sorted({c.get("proccode") for c in allc}):
        base["txtChargeCode"] = pc
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, val) for k, val in base.items())))
        if "Fault" in r: return "FAULT extins " + re.sub(r"\s+", " ", r[:160])
    return "ok"
for pid, P in PLAN.items():
    s = loc[pid]["summ"]; mbi = s["mbi"]; pb = s["partB"]; begin = "%s/%s/%s" % (pb[4:6], pb[6:8], pb[0:4])
    C = out["charts"][pid] = {"visits": []}
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    have = [p for p in plans if p.get("carrier") == "car6085" and not p.get("enddate")]
    L("== pat%s plans %s" % (pid, [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("enddate")) for p in plans]))
    if have: insid, seq = have[0]["id"], have[0]["sequence"]; L("FLO02 already on chart %s seq %s" % (insid, seq))
    elif DRY: L("DRY: would add FLO02 car6085 MBI ...%s begin %s" % (mbi[-4:], begin)); insid, seq = None, None
    else:
        insid, seq = add_ins.add(pid, "car6085", mbi, begindate=begin); L("add_ins FLO02 -> %s seq %s" % (insid, seq)); C["add"] = [insid, seq]
        if not insid: L("ADD FAILED - stop this chart"); continue
    C["insid"] = insid; C["seq"] = seq
    if insid and not DRY:
        try: C["elig271"] = elig(insid); L("AMD 271 FLO02 -> %s" % C["elig271"])
        except Exception as ex: C["elig271"] = "ERR %s" % ex; L("271 err %s" % ex)
        ok, msg = ins_update.update(pid, P["chp_ins"], enddate=P["chp_end"]); L("CAP07 %s enddate %s -> %s %s" % (P["chp_ins"], P["chp_end"], ok, msg[:120])); C["chp_end"] = [ok, msg[:120]]
        ok, msg = ins_update.update(pid, insid, sequence=str(seq)); L("patient insorder %s -> %s %s" % (seq, ok, msg[:120])); C["order"] = [ok, msg[:120]]
    # visits
    t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
    byv = {}
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("void") == "1" or not a.get("dos"): continue
        byv.setdefault(a.get("visit"), []).append(a)
    for vid, chs in sorted(byv.items(), key=lambda kv: kv[1][0].get("dos")):
        if any(float(c.get("paid") or 0) > 0 for c in chs): continue
        opn = sum(float(c.get("insbal") or 0) + float(c.get("patbal") or 0) for c in chs)
        if opn <= 0: continue
        if not all(c.get("carrier") == "CAP07" for c in chs): L("v%s carrier %s - skipped" % (vid, [c.get("carrier") for c in chs])); continue
        cid = chs[0]["id"]; row = {"vid": vid, "cid": cid, "dos": chs[0].get("dos"), "cpts": [c.get("proccode") for c in chs], "open": opn, "patbal": sum(float(c.get("patbal") or 0) for c in chs)}
        if DRY: L("DRY v%s %s %s open %.2f patbal %.2f" % (vid, row["dos"], row["cpts"], opn, row["patbal"])); C["visits"].append(row); continue
        try:
            vis, pat, allc = resave.visit_charges(cid); row["freq1"] = freq1_reset(vid, allc, vis)
            row["move"] = move_to_ins.move(cid, str(seq), rebill_seq=seq)
            time.sleep(0.5); v2, p2, c2 = resave.visit_charges(cid); row["live"] = [len(c2), len(allc)]
        except Exception as ex: row["err"] = str(ex)[:200]
        L("v%s %s %s -> freq1 %s | %s | live %s" % (vid, row["dos"], row["cpts"], row.get("freq1"), row.get("move"), row.get("live")))
        C["visits"].append(row); time.sleep(0.4)
    json.dump(out, open("registers/apply_2026-09-29T1710Z%s.json" % ("_dry" if DRY else ""), "w"), indent=1)
L("DONE")
