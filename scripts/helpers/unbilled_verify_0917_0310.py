# PLAIN ENGLISH (Unbilled prior-payor verification, 11pm ET 9/16/2026 run (run 2026-09-17T0310Z)): reads the before-scan, groups the
# 'A payment from the prior payor is required' rows by patient, pulls each patient's gettxhistory ONCE, and for every
# charge on those visits records the carrier last billed, bill date, paid, insbal and whether a real (non-$0) payment
# exists. Classifies each visit: (b) primary sent and unanswered -> release; (a) primary paid long ago -> hold for review.
# Never touches: AMD writes. Output registers/unbilled_verify_<stamp>.json
import amd, re, json, time, datetime
S="2026-09-17T0310Z"
s=json.load(open("scan_0912/summary_before.json"))
rows=[r for r in s["unbilled"] if r["_errs"] and r["_errs"][0].startswith("A payment from the prior")]
bypid={}
for r in rows: bypid.setdefault(r["patientid"],[]).append(r)
out={}; today=datetime.date(2026,9,17)
def pd(x):
    try: return datetime.datetime.strptime(x,"%m/%d/%Y").date()
    except Exception: return None
for pid,rs in bypid.items():
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    vids={r["id"] for r in rs}
    chg=[]
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit") in vids: chg.append(a)
    for r in rs:
        cs=[c for c in chg if c.get("visit")==r["id"]]
        paidsum=sum(float(c.get("paid") or 0) for c in cs)
        bd=[pd(c.get("datebilled") or c.get("billdate") or "") for c in cs]; bd=[b for b in bd if b]
        newest=max(bd) if bd else None
        age=(today-newest).days if newest else None
        cls="release-b" if (paidsum==0 or (age is not None and age<=60)) else "hold-a"
        out[r["id"]]={"pid":pid,"name":r.get("patientname"),"n":len(cs),"paid":paidsum,"newest_bill":str(newest),"age":age,"insbal":sum(float(c.get("insbal") or 0) for c in cs),
                      "carriers":sorted({(c.get("lastbilledcarrier") or c.get("carrier") or "") for c in cs}),"class":cls}
    time.sleep(0.3)
json.dump(out,open("registers/unbilled_verify_%s.json"%S,"w"),indent=1)
import collections
print(collections.Counter(v["class"] for v in out.values()))
for k,v in out.items():
    if v["class"]!="release-b" or v["n"]==0: print(k,v)
print("visits",len(out),"patients",len(bypid))
