import amd, re, json, sys, time
amd.login_cached()
def txh(pid):
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    out=[]
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))); out.append(a)
    return t,out
res={}
for pid in sys.argv[1:]:
    t,ch=txh(pid); res[pid]=ch
    open(f"logs/txh_{pid}_0510.xml","w").write(t)
    print("== pat",pid, len(ch),"charges")
    for a in ch:
        if float(a.get("insbal") or 0)>0 or float(a.get("patbal") or 0)>0:
            print("  ",{k:a.get(k) for k in ("id","visit","proccode","dos","carrier","lastbilledcarrier","datebilled","billdate","insbilled","insbal","patbal","paid","insorder","void","payerinfo","facname")})
    time.sleep(0.3)
json.dump(res,open("logs/txh_0510.json","w"),indent=1)
