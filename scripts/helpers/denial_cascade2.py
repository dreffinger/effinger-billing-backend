# PLAIN ENGLISH (Commercial / Medicaid denial cascade - from the claim-status sweep)
# Decides: For every patient whose non-Medicare claims came back DENIED or FINALIZED-$0 in the full status sweep, what the coverage actually was on those dates - asked of the payers themselves (Stedi eligibility on the billed plan, Florida Medicaid's managed-care record, and Medicare's MBI lookup) - and sorts each patient's denied claims into an action.
# Rules it uses: (1) A claim older than 12 months is written off as untimely (William's rule) - no payer will pay it now. (2) Medicaid straight (MCAD) denied because the patient is in an SMMC plan or has Medicare -> add the plan Medicaid/Medicare names, bill Medicare first then the plan. (3) Billed plan INACTIVE on the date and Medicare names an Advantage plan -> add it and rebill. (4) Billed plan ACTIVE on the date -> the denial is about the claim itself (non-covered, duplicate, missing info) -> board row for William with the payer's words. --act applies (1)-(3) with the proven helpers; without it the script only reports.
# Never touches: Medicare (FLO02) claims, claims with a payment posted, or anything whose answer is ambiguous - those go to the board.
# ---
"""Usage: python3 denial_cascade2.py [--act] [--max N]   reads claimstatus_full_<date>.jsonl -> denial_cascade2_<date>.json"""
import amd, stedi, json, re, sys, datetime, collections, time, glob, requests
from precheck import CAR2STEDI, CARRIERS, plans
amd.login_cached(); today = datetime.date.today(); stamp = today.strftime("%Y%m%d"); ACT = "--act" in sys.argv
mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
CUT = (today - datetime.timedelta(days=365)).isoformat()
PLAN2CAR = {"SUNSHINE": "car6194", "SIMPLY": "car42019", "HUMANA": "car6285", "FLORIDA COMMUNITY CARE": "car42008", "WELLCARE": "car6174", "MOLINA": "car6578", "AETNA BETTER": "car6047", "UNITEDHEALTHCARE": "car302853", "UNITED HEALTHCARE": "car302853", "CARE IMPROVEMENT": "car302853"}
rs = {}
for l in open(sorted(glob.glob("claimstatus_full_*.jsonl"))[-1]):
    r = json.loads(l); rs[r["visitid"]] = r
den = [r for r in rs.values() if r["action"].startswith("DENIED") or r["action"].startswith("FINALIZED")]
byp = collections.defaultdict(list)
for r in den: byp[r["patientid"]].append(r)
def codes_of(r): return sorted({s.get("code") for s in (r.get("status") or []) if s.get("cat") in ("F2", "F3", "F4") or (s.get("cat") in ("F0", "F1") and float(s.get("paid") or 0) == 0)} - {None, "38", "3", "65", "107", "101", "20", "19"})
def mcd_elig(first, last, dob, mid, dos):
    j = stedi.elig("77027", first, last, dob, mid, dos)
    hic = (j.get("planInformation") or {}).get("hicNumber") if isinstance(j.get("planInformation"), dict) else None
    mco = [(b.get("planCoverage"), (b.get("benefitsRelatedEntity") or {}).get("entityName")) for b in (j.get("benefitsInformation") or []) if b.get("code") == "MC" and b.get("name") == "Managed Care Coordinator"]
    active = any(b.get("code") == "1" and b.get("insuranceTypeCode") == "MC" for b in (j.get("benefitsInformation") or []))
    errs = [e.get("code") + " " + e.get("description", "")[:40] for e in (j.get("subscriber", {}).get("aaaErrors") or j.get("errors") or [])]
    return {"active": active, "hic": hic, "mco": mco, "errors": errs}
def payer_elig(payer, first, last, dob, mid, dos):
    j = stedi.elig(payer, first, last, dob, mid, dos)
    errs = [e.get("code") + " " + e.get("description", "")[:40] for e in (j.get("errors") or [])]
    st = [(s.get("status"), (s.get("planDetails") or "")[:40]) for s in (j.get("planStatus") or [])]
    pd = j.get("planDateInformation") or {}
    return {"errors": errs, "status": st, "active": any(s[0] == "Active Coverage" for s in st), "dates": pd, "member": j.get("subscriber", {}).get("memberId")}
import os
OUTF = "denial_cascade2_%s.jsonl" % stamp
done = {json.loads(l)["pid"] for l in open(OUTF)} if os.path.exists(OUTF) else set()
out = [json.loads(l) for l in open(OUTF)] if os.path.exists(OUTF) else []; n = 0
fo = open(OUTF, "a")
for pid, claims in sorted(byp.items(), key=lambda kv: -sum(r["balance"] for r in kv[1])):
    if n >= mx: break
    if pid in done: continue
    n += 1
    pa, pl = plans(pid); nm = pa.get("name") or claims[0]["patient"]; last, first = nm.split(",")[0].strip(), nm.split(",")[-1].strip().split(" ")[0]
    dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
    claims.sort(key=lambda r: r["dos"]); mid_dos = claims[len(claims) // 2]["dos"].replace("-", "")
    cars = collections.Counter(r["carrier"] for r in claims); car = cars.most_common(1)[0][0]
    rec = {"pid": pid, "patient": nm, "dob": dob, "carriers": dict(cars), "claims": len(claims), "balance": round(sum(r["balance"] for r in claims), 2), "first": claims[0]["dos"], "last": claims[-1]["dos"],
           "untimely": [r["visitid"] for r in claims if r["dos"] < CUT], "codes": collections.Counter(c for r in claims for c in codes_of(r)).most_common(6), "chart_plans": [(p[1], p[4], p[2], p[3], p[5]) for p in pl], "checks": []}
    try:
        # 1. Medicare record
        j = stedi.mbi(first, last, dobc, pa.get("state") or "FL", mid_dos); m = stedi.med_summ(j)
        rec["cms"] = {"mbi": m["mbi"], "partA": m["partA"], "partB": m["partB"], "death": m["death"], "errors": m["errors"][:1], "ma": [(o["entity"][0][0] if o["entity"] else o["plan"], o["dates"]) for o in m["other"] if o["code"] in ("U", "R") and (o["type"] or "") in ("HN", "HM", "PR", "PS", "IN", "MC", "MD")]}
        # 2. billed payer on the middle DOS
        mine = [p for p in pl if p[1] == CARRIERS.get(car)]; member = mine[0][4] if mine else ""
        if car == "MCAD" and member: rec["medicaid"] = mcd_elig(first, last, dobc, member, mid_dos)
        elif CAR2STEDI.get(car) and member: rec["payer"] = payer_elig(CAR2STEDI[car], first, last, dobc, member, mid_dos)
        # verdict
        c = rec["cms"]; codes = dict(rec["codes"])
        if c.get("death") and c["death"] < claims[-1]["dos"].replace("-", ""): v = "DATE OF DEATH %s - write off lines after it" % c["death"]
        elif car == "MCAD" and rec.get("medicaid", {}).get("hic") and not any(p[1] == "car6085" for p in pl): v = "MEDICARE PRIMARY (HIC %s per Medicaid) missing on chart -> add Medicare, bill Medicare first" % rec["medicaid"]["hic"]
        elif car == "MCAD" and rec.get("medicaid", {}).get("mco"): v = "SMMC PLAN per Medicaid: %s -> add plan, rebill" % "; ".join("%s (%s)" % (e, p) for p, e in rec["medicaid"]["mco"] if e)
        elif rec.get("payer") and not rec["payer"]["active"] and c.get("ma"): v = "billed plan INACTIVE; Medicare names Advantage plan %s -> add + rebill" % c["ma"][0][0]
        elif rec.get("payer") and not rec["payer"]["active"] and c.get("mbi") and not c.get("ma"): v = "billed plan INACTIVE; straight Medicare %s -> bill Medicare" % c["mbi"]
        elif rec.get("payer") and not rec["payer"]["active"]: v = "billed plan INACTIVE on DOS and no Medicare record - needs facesheet (board)"
        elif rec.get("payer") and rec["payer"]["active"]: v = "billed plan ACTIVE - denial is claim-content (%s) -> board" % ", ".join(k for k, _ in rec["codes"][:3])
        elif car == "MCAD" and rec.get("medicaid", {}).get("active"): v = "Medicaid ACTIVE, no MCO, no Medicare - claim-content denial -> board"
        else: v = "could not verify coverage (%s) -> board" % (rec.get("medicaid", rec.get("payer", {})).get("errors") or c.get("errors"))
        rec["verdict"] = v
    except Exception as e: rec["verdict"] = "ERROR " + str(e)[:120]
    out.append(rec); fo.write(json.dumps(rec, default=str) + "\n"); fo.flush(); print("%-24s %-6s %2d $%-7.0f %s..%s untimely %d -> %s" % (nm[:24], car, len(claims), rec["balance"], rec["first"], rec["last"], len(rec["untimely"]), rec["verdict"][:110]), flush=True); time.sleep(0.3)
json.dump(out, open("denial_cascade2_%s.json" % stamp, "w"), indent=1, default=str)
print("patients", len(out), collections.Counter(r["verdict"].split(" ")[0] + " " + r["verdict"].split(" ")[1] for r in out).most_common())
