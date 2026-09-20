# PLAIN ENGLISH (AET12 check, 5pm ET 9/20/2026 run (2026-09-20T2110Z)): claim run 1700202 (9/16 evening) rejected the same 59 AET12 claims
# again (PREF0288 TIN + PREF0264). Re-reads gettxhistory for the 15 charts on that run's exclusion list and records each
# AET12 charge's live state (insurance balance, paid, billdate, insbilled). Never touches: AMD writes.
import amd, re, json, time, collections
ex=json.load(open("registers/aet12_excl_1700202_2026-09-17T0710Z.json"))
byvisit={c["visit"] for c in ex}; pids=sorted({c["patientid"] for c in ex})
out=[]; amd.login_cached()
for pid in pids:
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit") in byvisit and a.get("carrier","").startswith("AET12"):
            a2={k:a.get(k) for k in ("id","visit","proccode","dos","carrier","lastbilledcarrier","datebilled","billdate","insbilled","insbal","patbal","paid","insorder","payerinfo","void")}
            a2["patientid"]=pid; out.append(a2)
    time.sleep(0.3)
json.dump(out,open("registers/aet12_verify_2026-09-20T2110Z.json","w"),indent=1)
print(len(out),"AET12 charges on",len(pids),"charts; visits matched",len({c['visit'] for c in out}),"of",len(byvisit))
print("insbilled/billdate:",collections.Counter((c.get("insbilled"),c.get("datebilled") or c.get("billdate")) for c in out).most_common(8))
print("insbal total %.2f  patbal total %.2f  paid total %.2f  zero-bal %d"%(sum(float(c.get("insbal") or 0) for c in out),sum(float(c.get("patbal") or 0) for c in out),sum(float(c.get("paid") or 0) for c in out),sum(1 for c in out if float(c.get("insbal") or 0)==0)))
