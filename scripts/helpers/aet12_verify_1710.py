# PLAIN ENGLISH (AET12 exclusion check, 1pm ET 9/15/2026 run): for the 59 AET12 rows on claim run 1700193, reads each
# chart's gettxhistory once and reports whether the AET12 charge is queued again (insbilled 0 / datebilled newer than the
# run) after the 02:15 ET chat rebill. Never touches: AMD writes.
import amd, re, json, time
s=json.load(open("scan_0912/summary_before.json"))
rows=s["exclusions"]["1700193"]
bypid={}
for r in rows: bypid.setdefault(r["patientid"],[]).append(r)
out=[]
for pid,rs in bypid.items():
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    vids={r["id"] for r in rs}
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit") in vids:
            out.append({k:a.get(k) for k in ("id","visit","proccode","dos","carrier","lastbilledcarrier","datebilled","billdate","insbilled","insbal","paid","insorder","payerinfo")})
    time.sleep(0.3)
json.dump(out,open("registers/aet12_verify_2026-09-15T1710Z.json","w"),indent=1)
print(len(out),"charges on",len(vids and bypid),"charts")
import collections
print(collections.Counter((c.get("insbilled"),c.get("datebilled") or c.get("billdate")) for c in out).most_common(10))
print(sum(float(c.get("insbal") or 0) for c in out))
print(out[:3])
