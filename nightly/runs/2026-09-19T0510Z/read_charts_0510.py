# PLAIN ENGLISH (1am ET 9/19 run 2026-09-19T0510Z): read-only look at the five charts on tonight's Unbilled snapshot / William's board answers
# (pat17477775, pat17477776, pat17477779, pat17477798, pat17477774): insplans, refplans, address, DOB and every open charge. Never touches: AMD writes.
import amd, re, json, sys
amd.login_cached(); out={}
for pid in sys.argv[1:]:
    t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
    pat=dict(re.findall(r'(\w+)="([^"]*)"', (re.search(r'<patient [^>]*>',t) or re.search(r'<patient[^>]*>',t)).group(0)))
    plans=[dict(re.findall(r'(\w+)="([^"]*)"',p)) for p in re.findall(r'<insplan [^>]*>',t)]
    rps=[dict(re.findall(r'(\w+)="([^"]*)"',p)) for p in re.findall(r'<refplan [^>]*>',t)]
    addr=re.search(r'<address [^>]*>',t); addr=dict(re.findall(r'(\w+)="([^"]*)"',addr.group(0))) if addr else {}
    tx=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    chg=[dict(re.findall(r'(\w+)="([^"]*)"',m.group(0))) for m in re.finditer(r'<charge [^>]*/?>',tx)]
    out[pid]={"name":pat.get("name"),"dob":pat.get("dob"),"sex":pat.get("sex"),"ssn_present":bool(pat.get("ssn")),"insorder":pat.get("insorder"),"address":{k:addr.get(k) for k in ("address1","address2","city","state","zip")},
      "plans":[{k:p.get(k) for k in ("id","carrier","subscribernum","sequence","begindate","enddate","mspcode","grpnum","finclasscode")} for p in plans],
      "refplans":[{k:r.get(k) for k in ("id","ismain","preauth","begindate","enddate","status")} for r in rps],
      "charges":[{k:c.get(k) for k in ("id","visit","proccode","dos","carrier","insbal","patbal","paid","insorder","billdate","insbilled","facname","void")} for c in chg]}
    print(pid, json.dumps(out[pid],indent=1))
json.dump(out,open("registers/charts_read_2026-09-19T0510Z.json","w"),indent=1)
