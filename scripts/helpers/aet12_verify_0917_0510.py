# PLAIN ENGLISH (AET12 check, 1am ET 9/17/2026 run): the 59 AET12 exclusion rows on claim run 1700201 vanished from the
# exclusion list between the 0310Z run and this one (completed outside the routine). This re-reads gettxhistory for the
# same 15 charts (from the 0310Z register) and records each AET12 charge's live state - insurance balance, paid, billdate,
# insbilled - so the report can say whether they were paid, written off, rebilled or merely completed. Never touches: AMD writes.
import amd, re, json, time, collections
prev=json.load(open("registers/aet12_verify_2026-09-17T0310Z.json"))
byvisit={c["visit"] for c in prev}
pids=sorted({c.get("pid") for c in prev if c.get("pid")}) if any(c.get("pid") for c in prev) else None
if not pids:
    s=json.load(open("/home/claude/effinger-billing-backend/nightly/runs/2026-09-17T0310Z/run_outputs_0917_0310.py")) if False else None
# recover patient ids from the 0310 scan's exclusion rows saved in the repo copy of summary_before if present
import os
pidset=set()
try:
    ex=json.load(open("/home/claude/effinger-billing-backend/practices/ehpa/registers/aet12_verify_2026-09-17T0310Z.json"))
except Exception: ex=prev
for c in ex:
    if c.get("patientid"): pidset.add(c["patientid"])
out=[]; 
amd.login_cached()
if not pidset:
    # fall back: read the charge ids and ask getchargedetaildataicd10? cheaper: gettxhistory needs pid; use the visit->pid map from the 0310 scan xml if the repo kept it
    print("no patient ids in register; charges:",len(prev)); 
for pid in sorted(pidset):
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit") in byvisit:
            a2={k:a.get(k) for k in ("id","visit","proccode","dos","carrier","lastbilledcarrier","datebilled","billdate","insbilled","insbal","patbal","paid","insorder","payerinfo","void")}
            a2["patientid"]=pid; out.append(a2)
    time.sleep(0.3)
json.dump(out,open("registers/aet12_verify_2026-09-17T0510Z.json","w"),indent=1)
print(len(out),"charges on",len(pidset),"charts; visits matched",len({c['visit'] for c in out}),"of",len(byvisit))
print("insbilled/billdate:",collections.Counter((c.get("insbilled"),c.get("datebilled") or c.get("billdate")) for c in out).most_common(8))
print("insbal total %.2f  patbal total %.2f  paid total %.2f"%(sum(float(c.get("insbal") or 0) for c in out),sum(float(c.get("patbal") or 0) for c in out),sum(float(c.get("paid") or 0) for c in out)))
print("carriers:",collections.Counter(c.get("carrier") for c in out))
