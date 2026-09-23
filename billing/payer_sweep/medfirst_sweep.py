#!/usr/bin/env python3
# PLAIN ENGLISH (Medicare-first sweep: wrong-payer denials + unpaid non-Medicare claims)
# Decides: For every patient with unpaid past-year visits sitting at a non-Medicare payer (and the wrong-insurance denials read off the
#          paper EOBs), who the right payer was on those dates: AMD's free 271 on the chart plans (today's status, no cost) + Stedi's
#          Medicare MBI lookup on the date of service (Part A/B dates, any Advantage plan, Part D-only = original Medicare, hospice,
#          date of death) + the live visit history (has Medicare already paid this visit? who was it last billed to?).
#          Then, with --act, for the ORIGINAL-MEDICARE patients: add/fix the Medicare plan (MBI), put it first on the chart, and
#          frequency-1 rebill every past-year visit that was billed to the wrong payer - to Medicare.
# Rules it uses: never rebills a visit that already carries a Medicare payment (that balance is the secondary's); never a visit whose
#          last bill already went to Medicare; never a visit older than 365 days (Medicare timely filing); VA CCN visits are listed,
#          never auto-rebilled (authorized VA care is VA's, not Medicare's); deceased -> list only; an Advantage plan that IS the billed
#          payer -> no action (claim-content); Stedi calls cached per patient+month, AMD 271 cached per plan+day (patient_db/).
# Never touches: payments, write-offs, claims at Medicare, anything on a chart whose Medicare picture is ambiguous.
# ---
"""Usage (from /home/claude/unbilled with the repo helpers on PYTHONPATH):
  python3 medfirst_sweep.py --group cascade|unpaid|both [--tiers 1,2] [--max N] [--pids 1,2] [--act] [--only-verdict ORIGINAL_MEDICARE]
Writes medfirst_<stamp>.jsonl (one record per patient, resume-safe), medfirst_<stamp>.json, and with --act medfirst_register_<stamp>.json."""
import amd, elig_amd, stedi, txh, payreasons, resave, add_ins, ins_update, move_to_ins, freq1_visit
import json, os, sys, re, time, datetime, collections

SCANS = "/home/claude/scans"
TODAY = datetime.date.today(); STAMP = TODAY.strftime("%Y%m%d"); CUT = TODAY - datetime.timedelta(days=365)
CARMAP = json.load(open("carriers.json"))                       # carNNNN -> [code, name]
CODE2CAR = {v[0]: k for k, v in CARMAP.items()}
TIER1 = {"WEL04", "VACCN", "TRI00", "TRI05", "CAP07", "HUM01", "AET07", "UHCMA", "SUN01", "SIM01", "PHI01", "CIG09", "CIG13", "UMR",
         "CHA03", "RET01", "HIG06", "AMB03", "LAN", "MER01", "AAR01", "AET12", "GEO05"}
TIER2 = {"UNI20", "BCBS", "FLO99", "MCAD"}
MA_TYPES = {"HN", "HM", "PR", "PS", "IN"}                        # CMS 271: Advantage / other health plan types (OT + STC 88 = Part D only)
# Advantage payer name -> AMD carrier code family (for "is the Advantage plan the payer we billed?")
MA_FAMILY = [("UNITEDHEALTH", "UNI20"), ("UNITED HEALTH", "UNI20"), ("AARP", "UNI20"), ("PREFERRED CARE", "UNI20"), ("CARE IMPROVEMENT", "UNI20"), ("HUMANA", "HUM01"), ("EMPHESYS", "HUM01"),
             ("AETNA", "AET07"), ("SILVERSCRIPT", "AET07"), ("WELLCARE", "WEL04"), ("SUNSHINE", "SUN01"), ("CENTENE", "SUN01"), ("CAPITAL HEALTH", "CAP07"), ("CHP", "CAP07"),
             ("HEALTHSPRING", "CIG13"), ("CIGNA", "CIG13"), ("SIMPLY", "SIM01"), ("FLORIDA BLUE", "BCBS"), ("BLUE", "BCBS"), ("HIGHMARK", "HIG06"), ("DEVOTED", "DEV"), ("CAREPLUS", "CAR"), ("FREEDOM", "FRE"), ("OPTIMUM", "OPT")]
# CMS 271 legal entities: SilverScript Ins. Co. = Aetna MA-PD contracts, Emphesys Ins. Co. = Humana MA PPO, Care Improvement Plus = UHC MA (Dual Complete), Preferred Care Partners = UHC MA HMO, HealthSpring = Cigna MA
NAME2PID = json.load(open(os.path.join(SCANS, "medfirst_names.json"))) if os.path.exists(os.path.join(SCANS, "medfirst_names.json")) else {}   # paper-EOB names -> chart ids (Drive working copy only, never in git)   # paper-EOB names the OCR could not join (board ids 9/23)
SAME_FAMILY = {"UNI20": {"UNI20", "UHCMA", "AAR01"}, "UHCMA": {"UNI20", "UHCMA"}, "HUM01": {"HUM01"}, "AET07": {"AET07"}, "WEL04": {"WEL04"}, "SUN01": {"SUN01", "WEL04"},
               "CAP07": {"CAP07"}, "CIG13": {"CIG13", "CIG09"}, "SIM01": {"SIM01"}, "BCBS": {"BCBS"}, "HIG06": {"HIG06", "HIG04"}}

def d8(s):   # 'mm/dd/yyyy' or 'yyyy-mm-dd' -> 'yyyymmdd'
    if not s: return ""
    s = s[:10]
    if "/" in s: m, d, y = s.split("/"); return "%s%02d%02d" % (y, int(m), int(d))
    return s.replace("-", "")

def span_covers(span, dos):
    """'yyyymmdd' or 'yyyymmdd-yyyymmdd' covers dos?"""
    if not span or not dos: return False
    a, _, b = span.partition("-")
    return a <= dos and (not b or dos <= b)

def ma_plans(j):
    out = []
    for x in j.get("benefitsInformation") or []:
        if x.get("code") not in ("R", "U"): continue
        if x.get("insuranceTypeCode") not in MA_TYPES: continue
        if (x.get("serviceTypeCodes") or []) == ["88"]: continue          # pharmacy only = Part D plan, not an Advantage plan
        ents = [(e.get("entityIdentifier"), e.get("entityName"), e.get("entityIdentifierValue")) for e in x.get("benefitsRelatedEntities") or []]
        name = next((n for _, n, _ in ents if n), "") or (x.get("planCoverage") or "")
        dates = x.get("benefitsDateInformation") or {}
        out.append({"name": name, "type": x.get("insuranceTypeCode"), "dates": dates.get("benefit") or dates.get("plan") or "", "ids": [v for _, _, v in ents if v]})
    return out

def hospice_flags(j):
    return [x.get("benefitsDateInformation") for x in j.get("benefitsInformation") or [] if (x.get("serviceTypeCodes") or []) == ["45"] and x.get("code") in ("1", "D") and x.get("benefitsRelatedEntities")]

def family_of_name(name):
    u = (name or "").upper()
    for key, fam in MA_FAMILY:
        if key in u: return fam
    return "?"

STEDI_CACHE = os.path.join(SCANS, "medfirst_stedi_cache.json")
_sc = json.load(open(STEDI_CACHE)) if os.path.exists(STEDI_CACHE) else {}
def mbi_lookup(pid, first, last, dobc, state, dos):
    key = "%s|%s" % (pid, dos[:6])
    if key in _sc: return _sc[key]
    j = stedi.mbi(first, last, dobc, state or "FL", dos)
    os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_mbi_%s.json" % (pid, dos), "w"), indent=1)
    m = stedi.med_summ(j)
    rec = {"mbi": m["mbi"], "partA": m["partA"], "partB": m["partB"], "death": m["death"], "errors": m["errors"][:2], "ma": ma_plans(j), "hospice": hospice_flags(j),
           "partd": [ (e.get("entityName") or "") for x in j.get("benefitsInformation") or [] if x.get("code") == "R" and x.get("insuranceTypeCode") == "OT" for e in x.get("benefitsRelatedEntities") or []],
           "elig_date": (j.get("planDateInformation") or {}).get("eligibility"), "stedi_name": m["name"]}
    _sc[key] = rec; json.dump(_sc, open(STEDI_CACHE, "w"), indent=1)
    return rec

VIS_CACHE = os.path.join(SCANS, "medfirst_visit_cache.json")
_vc = json.load(open(VIS_CACHE)) if os.path.exists(VIS_CACHE) else {}
def visit_facts(pid, vid, refresh=False):
    key = "%s|%s" % (pid, vid)
    if key in _vc and not refresh: return _vc[key]
    root = txh.fetch_visit(pid, vid); ch = payreasons.visit_state(pid, vid, root)
    paid_by = sorted({p["carrier"] for c in ch for p in c["pays"] if p["void"] != "1" and p["amount"] > 0})
    zero_by = sorted({p["carrier"] for c in ch for p in c["pays"] if p["void"] != "1" and p["amount"] == 0})
    codes = sorted({r[0] for c in ch for p in c["pays"] if p["void"] != "1" for r in p["reasons"] if r[0]})
    rec = {"cids": [c["cid"] for c in ch], "cpts": [c["cpt"] for c in ch], "dos": ch[0]["dos"] if ch else "", "fee": round(sum(c["fee"] for c in ch), 2),
           "insbal": round(sum(c["insbalance"] for c in ch), 2), "patbal": round(sum(c["patbalance"] for c in ch), 2),
           "last_carrier": sorted({c["carrier"] for c in ch}), "paid_by": paid_by, "zero_by": zero_by, "codes": codes[:8],
           "wos": sorted({w["code"] for c in ch for w in c["wos"] if w["void"] != "1"})}
    _vc[key] = rec; json.dump(_vc, open(VIS_CACHE, "w"), indent=1)
    return rec

def load_groups(args):
    unp = json.load(open(os.path.join(SCANS, "unpaid_2026-09-23.json")))
    by_vid = {str(r["visitid"]): r for r in unp}
    pv = collections.defaultdict(list)
    for r in unp:
        dos = datetime.date.fromisoformat(r["dateofservice"][:10])
        if dos < CUT or r["carriercode"].strip() == "FLO02": continue
        pv[str(r["patientid"])].append({"vid": str(r["visitid"]), "dos": dos.isoformat(), "carrier": r["carriercode"].strip(), "insbal": r["insbalance"], "fee": r["totalvisitamount"], "name": r["patientname"], "source": "unpaid"})
    groups = {}
    if args["group"] in ("cascade", "both"):
        acts = json.load(open(os.path.join(SCANS, "actions.json")))
        for a in acts:
            if "CASCADE" not in (a.get("category") or ""): continue
            vid = (a.get("acct") or "")[:8]; pid = a.get("pid") or (by_vid.get(vid, {}).get("patientid") and str(by_vid[vid]["patientid"])) or NAME2PID.get((a.get("patient") or "").upper())
            if not pid or not pid.isdigit(): groups.setdefault("_unresolved", []).append(a); continue
            pid = str(pid)
            if not any(v["vid"] == vid for v in pv[pid]):
                r = by_vid.get(vid)
                if r: pv[pid].append({"vid": vid, "dos": r["dateofservice"][:10], "carrier": r["carriercode"].strip(), "insbal": r["insbalance"], "fee": r["totalvisitamount"], "name": r["patientname"], "source": "cascade"})
                else: pv[pid].append({"vid": vid, "dos": d8(a.get("dos")) and "%s-%s-%s" % (a["dos"][6:], a["dos"][:2], a["dos"][3:5]), "carrier": "BCBS" if "Blue" in (a.get("payer") or "") else "UNI20", "insbal": 0.0, "fee": 0.0, "name": a.get("patient"), "source": "cascade-notlisted", "remark": a.get("remark")})
            groups.setdefault("cascade", set()).add(pid)
    if args["group"] in ("unpaid", "both"):
        tiers = args["tiers"]; cars = set()
        if "1" in tiers: cars |= TIER1
        if "2" in tiers: cars |= TIER2
        for pid, vs in pv.items():
            if any(v["carrier"] in cars for v in vs): groups.setdefault("unpaid", set()).add(pid)
    return pv, groups, by_vid

def analyze(pid, visits):
    pa, pl = elig_amd.plans(pid)
    name = pa.get("name", "?"); dob = pa.get("dob", ""); dobc = d8(dob)
    last, first = name.split(",")[0].strip(), name.split(",")[-1].strip().split(" ")[0]
    plans = [{"id": p.get("id"), "carrier": p.get("carrier"), "code": CARMAP.get(p.get("carrier"), ["?"])[0], "seq": p.get("sequence"), "begin": p.get("begindate"), "end": p.get("enddate"), "sub": p.get("subscribernum", "")} for p in pl]
    active = [p for p in plans if not p["end"]]
    rec = {"pid": pid, "name": name, "dob": dob, "plans": [{k: (v if k != "sub" else (v[:3] + "…" + v[-2:] if v else "")) for k, v in p.items()} for p in plans],
           "visits": visits, "n": len(visits), "balance": round(sum(v["insbal"] for v in visits), 2), "carriers": dict(collections.Counter(v["carrier"] for v in visits)), "amd271": {}, "checks": []}
    for p in active[:6]:
        try:
            s = elig_amd.run_plan(pid, p["id"].replace("ins", ""))
            rec["amd271"][p["code"]] = {"status": s.get("status"), "partB": s.get("partB"), "others": [(o.get("type"), (o.get("plan") or ""), " ".join((x.get("name") or "") for x in o.get("entities") or [])[:40]) for o in s.get("other_payers") or []][:4], "death": s.get("date_of_death"), "id": (s.get("subscriber") or {}).get("id")}
        except Exception as e: rec["amd271"][p["code"]] = {"status": "ERROR %s" % str(e)[:60]}
    dos_list = sorted(v["dos"] for v in visits if v["dos"]); dos_max = d8(dos_list[-1]) if dos_list else STAMP; dos_min = d8(dos_list[0]) if dos_list else dos_max
    try: cms = mbi_lookup(pid, first, last, dobc, pa.get("state"), dos_max)
    except Exception as e: cms = {"errors": ["EXC %s" % str(e)[:80]]}
    rec["cms"] = cms
    # visit facts
    for v in visits:
        try: v.update(visit_facts(pid, v["vid"]))
        except Exception as e: v["error"] = str(e)[:80]
    # verdict
    med_plan = next((p for p in plans if p["code"] == "FLO02" and not p["end"]), None) or next((p for p in plans if p["code"] == "FLO02"), None)
    mbi = cms.get("mbi"); partB = cms.get("partB") or ""; ma = cms.get("ma") or []
    ma_on_dos = [m for m in ma if not m["dates"] or span_covers(m["dates"], dos_max) or span_covers(m["dates"], dos_min)]
    death = cms.get("death")
    if death and death <= dos_max:
        v = "DECEASED %s" % death
    elif not mbi:
        v = "NO_MEDICARE_RECORD %s" % ("; ".join(cms.get("errors") or [])[:60])
    elif ma_on_dos:
        fam = family_of_name(ma_on_dos[0]["name"]); billed = set(rec["carriers"])
        same = billed <= SAME_FAMILY.get(fam, {fam})
        v = ("MA_SAME_PAYER %s" if same else "MA_SWITCH %s") % (ma_on_dos[0]["name"][:30] + " " + (ma_on_dos[0]["dates"] or ""))
    elif partB and span_covers(partB, dos_max):
        v = "ORIGINAL_MEDICARE"
    elif partB:
        v = "PART_B_NOT_ON_DOS %s" % partB
    else:
        v = "PART_A_ONLY"
    rec["verdict"] = v
    if cms.get("hospice"): rec["hospice"] = cms["hospice"]
    # per-visit plan
    plan = []
    for vt in visits:
        if "error" in vt: plan.append((vt["vid"], "ERROR")); continue
        if v == "ORIGINAL_MEDICARE":
            if "FLO02" in (vt.get("paid_by") or []): a = "SECONDARY_PENDING (Medicare paid)"
            elif vt.get("last_carrier") == ["FLO02"]: a = "AT_MEDICARE_ALREADY"
            elif vt["carrier"] == "VACCN" or "VACCN" in (vt.get("last_carrier") or []): a = "VA_REVIEW (authorized care stays VA's)"
            elif vt.get("insbal", 0) <= 0 and vt.get("patbal", 0) <= 0: a = "NO_BALANCE"
            else: a = "REBILL_TO_MEDICARE"
        elif v.startswith("MA_SWITCH"): a = "REPOINT_TO_MA (%s)" % ma_on_dos[0]["name"][:24]
        elif v.startswith("MA_SAME"): a = "CLAIM_CONTENT (right payer)"
        elif v.startswith("DECEASED"): a = "AFTER_DEATH" if d8(vt["dos"]) > death else "BEFORE_DEATH"
        else: a = "REVIEW"
        plan.append((vt["vid"], a))
    rec["plan"] = plan; rec["counts"] = dict(collections.Counter(a.split(" ")[0] for _, a in plan))
    rec["med_plan"] = med_plan and {"id": med_plan["id"], "seq": med_plan["seq"], "end": med_plan["end"], "mbi_match": (med_plan["sub"] or "").upper() == (mbi or "").upper()}
    return rec

def act(rec, reg, log):
    """ORIGINAL_MEDICARE only: chart fix + freq-1 rebill of REBILL_TO_MEDICARE visits."""
    pid = rec["pid"]; mbi = rec["cms"]["mbi"]; todo = [vid for vid, a in rec["plan"] if a == "REBILL_TO_MEDICARE"]
    if not todo: return "nothing to rebill"
    pa, pl = elig_amd.plans(pid)
    plans = [{"id": p.get("id"), "code": CARMAP.get(p.get("carrier"), ["?"])[0], "seq": p.get("sequence"), "end": p.get("enddate"), "sub": p.get("subscribernum", "")} for p in pl]
    med = next((p for p in plans if p["code"] == "FLO02" and not p["end"]), None)
    steps = []
    if not med:
        ended = next((p for p in plans if p["code"] == "FLO02"), None)
        if ended:
            r = ins_update.update(pid, ended["id"].replace("ins", ""), enddate=""); steps.append(("reopen FLO02 %s" % ended["id"], str(r)[:80])); med = ended
            if (ended["sub"] or "").upper() != mbi.upper():
                r = ins_update.update(pid, ended["id"].replace("ins", ""), subscribernum=mbi); steps.append(("fix MBI", str(r)[:80]))
        else:
            partB = rec["cms"].get("partB") or ""; b = partB.split("-")[0]
            begin = "%s/%s/%s" % (b[4:6], b[6:8], b[:4]) if len(b) == 8 and b >= d8((CUT - datetime.timedelta(days=400)).isoformat()) else None
            insid, seq = add_ins.add(pid, "car6085", mbi, begin); steps.append(("add FLO02", "%s seq %s" % (insid, seq)))
            if not insid: log.write("%s add FLO02 FAILED %s\n" % (pid, seq)); return "add plan failed: %s" % seq
            med = {"id": insid, "seq": str(seq), "sub": mbi}
    elif (med["sub"] or "").upper() != mbi.upper():
        r = ins_update.update(pid, med["id"].replace("ins", ""), subscribernum=mbi); steps.append(("fix MBI on %s" % med["id"], str(r)[:80]))
    pa, pl = elig_amd.plans(pid)
    seqs = [p.get("sequence") for p in pl if not p.get("enddate")]; medseq = next((p.get("sequence") for p in pl if CARMAP.get(p.get("carrier"), ["?"])[0] == "FLO02" and not p.get("enddate")), None)
    if not medseq: return "no active Medicare plan after fix: %s" % steps
    order = ",".join([medseq] + [s for s in seqs if s != medseq])
    if seqs and seqs[0] != medseq:
        r = ins_update.update(pid, next(p.get("id") for p in pl if p.get("sequence") == medseq).replace("ins", ""), sequence=order); steps.append(("chart order %s" % order, str(r)[:80]))
    done = []
    for vid in todo:
        vt = next(v for v in rec["visits"] if v["vid"] == vid); cid = str(vt["cids"][0])
        try:
            r1 = freq1_visit.run(vid, cid, int(medseq)); time.sleep(0.6)
            r2 = move_to_ins.move(cid, order, rebill_seq=int(medseq)); time.sleep(0.6)
            done.append({"vid": vid, "cid": cid, "dos": vt["dos"], "from": vt["carrier"], "insbal": vt.get("insbal"), "patbal": vt.get("patbal"), "freq1": str(r1)[:100], "move": str(r2)[:140]})
        except Exception as e:
            done.append({"vid": vid, "cid": cid, "error": str(e)[:120]})
        log.write("%s %s %s\n" % (pid, vid, json.dumps(done[-1])[:300])); log.flush()
    reg.append({"pid": pid, "name": rec["name"], "mbi_last4": mbi[-4:], "steps": steps, "order": order, "medseq": medseq, "visits": done, "at": datetime.datetime.utcnow().isoformat() + "Z"})
    return "steps %s | rebilled %d" % (steps, sum(1 for d in done if "error" not in d))

def main():
    a = sys.argv[1:]
    args = {"group": a[a.index("--group") + 1] if "--group" in a else "cascade", "tiers": (a[a.index("--tiers") + 1] if "--tiers" in a else "1").split(","),
            "max": int(a[a.index("--max") + 1]) if "--max" in a else 10**9, "pids": set(a[a.index("--pids") + 1].split(",")) if "--pids" in a else None,
            "act": "--act" in a, "only": a[a.index("--only-verdict") + 1] if "--only-verdict" in a else None}
    amd.login_cached()
    pv, groups, by_vid = load_groups(args)
    if "_unresolved" in groups: print("unresolved cascade rows:", [(x.get("patient"), x.get("acct")) for x in groups.pop("_unresolved")])
    pids = set().union(*[s for k, s in groups.items()]) if groups else set()
    if args["pids"]: pids = args["pids"]
    outf = os.path.join(SCANS, "medfirst_%s.jsonl" % STAMP)
    done = {}
    if os.path.exists(outf):
        for l in open(outf): r = json.loads(l); done[r["pid"]] = r
    order = sorted(pids, key=lambda p: -sum(v["insbal"] for v in pv.get(p, [])))
    fo = open(outf, "a"); n = 0
    reg_f = os.path.join(SCANS, "medfirst_register_%s.json" % STAMP); reg = json.load(open(reg_f)) if os.path.exists(reg_f) else []
    log = open(os.path.join(SCANS, "medfirst_act_%s.log" % STAMP), "a")
    for pid in order:
        if n >= args["max"]: break
        if pid in done and not args["act"]: continue
        rec = done.get(pid)
        if rec is None:
            n += 1
            try: rec = analyze(pid, pv.get(pid, []))
            except Exception as e: rec = {"pid": pid, "verdict": "ERROR %s" % str(e)[:120], "visits": pv.get(pid, []), "balance": round(sum(v["insbal"] for v in pv.get(pid, [])), 2), "counts": {}}
            rec["groups"] = [k for k, s in groups.items() if pid in s]
            fo.write(json.dumps(rec, default=str) + "\n"); fo.flush(); done[pid] = rec
            print("%-26s $%-8.2f %-38s %s" % ((rec.get("name") or "?")[:26], rec.get("balance", 0), rec["verdict"][:38], rec.get("counts")), flush=True)
        if args["act"] and rec["verdict"] == "ORIGINAL_MEDICARE" and (not args["only"] or rec["verdict"] == args["only"]) and pid not in {r["pid"] for r in reg}:
            res = act(rec, reg, log); json.dump(reg, open(reg_f, "w"), indent=1); print("   ACT %s -> %s" % (rec["name"][:24], res), flush=True)
    json.dump(list(done.values()), open(os.path.join(SCANS, "medfirst_%s.json" % STAMP), "w"), indent=1, default=str)
    c = collections.Counter(r["verdict"].split(" ")[0] for r in done.values())
    print("patients", len(done), dict(c))
    tot = collections.Counter(); amt = collections.Counter()
    for r in done.values():
        for vid, act_ in r.get("plan", []):
            k = act_.split(" ")[0]; tot[k] += 1; amt[k] += next((v.get("insbal", 0) for v in r["visits"] if v["vid"] == vid), 0)
    print("visits", {k: (tot[k], round(amt[k], 2)) for k in tot})

if __name__ == "__main__": main()
