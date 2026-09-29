# PLAIN ENGLISH (9 PM ET 9/28 slot, run 2026-09-29T0110Z): READ-ONLY investigation. Reads the tx history of the seven Unbilled
#   'A payment from the prior payor is required' visits (charge carrier / billdate / balances / payments) so the rule-(b) release
#   decision is made from live data; lookuppatient for the two Aviata admits still without a chart; getdemographic for pat20729
#   (the Brynwood census names a Sunshine secondary) + Stedi Centene 68069 eligibility on the two candidate Medicaid ids.
# Never touches: AMD writes.
import amd, stedi, re, json, time, sys
amd.login_cached()
out = {"prior": {}, "lookup": {}, "ross": {}}
PRIOR = [("19392347","23391"),("19441047","17470743"),("19442414","17473343"),("19453094","24853"),("19453102","24853"),("19453106","24853"),("19453209","24853")]
hist = {}
def txh(pid):
    if pid not in hist:
        hist[pid] = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120); time.sleep(0.3)
    return hist[pid]
for vid, pid in PRIOR:
    t = txh(pid); rows = []
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit") == vid:
            rows.append({k: a.get(k) for k in ("id","proccode","dos","carrier","billdate","insbilled","insbal","patbal","paid","insorder","payerinfo","void","fee")})
    # payments carrying this visit's charge ids
    cids = {r["id"] for r in rows}
    pays = []
    for m in re.finditer(r'<payment [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("charge") in cids or a.get("chargeid") in cids or a.get("visit") == vid:
            pays.append({k: a.get(k) for k in ("id","charge","chargeid","date","amount","carrier","checknumber","paymentcode","void","type")})
    out["prior"][vid] = {"pid": pid, "charges": rows, "payments": pays}
    print("v%s pat%s" % (vid, pid)); [print("   CHG", r) for r in rows]; [print("   PAY", p) for p in pays]
for nm in ("CHRISTOPHER,CHR%", "POWLETTE,SAN%", "ROSSITER,MARG%"):
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
    pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    out["lookup"][nm] = [{k: p.get(k) for k in ("id","name","chart","dob")} for p in pats]
    print("lookup", nm, [(p.get("id"), p.get("name"), p.get("dob")) for p in pats]); time.sleep(0.3)
d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "20729", "nocookie": "1"}), timeout=120)
plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
pa = dict(re.findall(r'(\w+)="([^"]*)"', (re.search(r'<patient [^>]*>', d) or [""])[0] if re.search(r'<patient [^>]*>', d) else ""))
out["ross"]["plans"] = [{k: p.get(k) for k in ("id","carrier","subscribernum","sequence","begindate","enddate","coverage")} for p in plans]
out["ross"]["patient"] = {k: pa.get(k) for k in ("id","name","dob","insorder","respparty")}
print("ROSSITER demographic:", out["ross"]["patient"]); [print("   PLAN", p) for p in out["ross"]["plans"]]
FIRST, LAST, DOB = open("local/pat20729_identity.txt").read().split()   # identity kept out of the mirrored copy
for mid in tuple(open("local/pat20729_medicaid_ids.txt").read().split()):
    try:
        j = stedi.elig("68069", FIRST, LAST, DOB, mid, "20260923")
        st = [(b.get("code"), b.get("name"), b.get("planCoverageDescription") or "", (b.get("insuranceType") or ""), b.get("benefitBegin") or "") for b in (j.get("benefitsInformation") or []) if b.get("code") in ("1","6")][:4]
        errs = [(e.get("code"), e.get("description")) for e in (j.get("errors") or [])]
        pl = j.get("planDateInformation") or {}
        out["ross"][mid] = {"status": st, "errors": errs, "plan": pl, "planStatus": j.get("planStatus")}
        print("STEDI 68069", mid, "->", st, errs, pl, j.get("planStatus"))
    except Exception as e:
        out["ross"][mid] = {"error": str(e)[:200]}; print("STEDI 68069", mid, "ERROR", str(e)[:200])
    time.sleep(0.5)
json.dump(out, open("registers/inv_2026-09-29T0110Z.json", "w"), indent=1)
