# read-only: plans + open visits of the charts on William's answered rows (ids and carriers only)
import amd, re, json, sys
import xml.etree.ElementTree as ET
amd.login_cached()
cj=json.load(open('carriers.json'))
CAR={v:k for k,v in cj.items()} if all(isinstance(v,str) for v in cj.values()) else {k:v[0] for k,v in cj.items()}
pids=sys.argv[1:]
out={}
for pid in pids:
    r=amd.post(amd.msg("getdemographic","demographics",{"patientid":"pat%s"%pid,"nocookie":"1"}))
    p=re.search(r'<patient [^>]*>',r); a=dict(re.findall(r'(\w+)="([^"]*)"',p.group(0))) if p else {}
    plans=[dict(re.findall(r'(\w+)="([^"]*)"',m)) for m in re.findall(r'<insplan [^>]*>',r)]
    pl=[(x.get('id'),x.get('sequence'),CAR.get(x.get('carrier'),x.get('carrier')),(x.get('subscribernum') or '')[:3]+'..'+(x.get('subscribernum') or '')[-3:],x.get('begindate'),x.get('enddate')) for x in plans]
    print("pat%s dob=%s insorder=%s name=%s"%(pid,a.get('dob'),a.get('insorder'),(a.get('name') or '')[:3]+'..'))
    for x in pl: print("   plan",x)
    # open charges
    rr=amd.post(amd.msg("gettxhistory","demographics",{"patientid":"pat%s"%pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}))
    for c in re.findall(r'<charge [^>]*>',rr):
        d=dict(re.findall(r'(\w+)="([^"]*)"',c))
        if d.get('void')=='1': continue
        if float(d.get('insbal') or 0)==0 and float(d.get('patbal') or 0)==0: continue
        print("   chg %s v%s %s %s insbal=%s patbal=%s paid=%s carrier=%s billdate=%s"%(d.get('id'),d.get('visit') or d.get('visitid'),d.get('dos'),d.get('proccode'),d.get('insbal'),d.get('patbal'),d.get('paid'),d.get('carrier'),d.get('billdate')))
