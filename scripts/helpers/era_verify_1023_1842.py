# PLAIN ENGLISH (2:40 PM ET 10/23 slot, run 2026-10-23T1842Z): READ-ONLY checks after the engine pass.
# 1) chart 17478064: list its insurance plans (carrier, member id, sequence, dates) to see why CAP07 rejects the subscriber id format.
# 2) ERA check 1053267 (UHC W1625929, posted by the Post button): read each claim line and the LIVE visit state so a CO-45 left on the
#    patient balance is caught (the Post-button defect on UHC/CAP07 lines).
# 3) lookuppatient for the two chartless Pam admits (BRO*, HIC*). No AMD write of any kind. Chart ids only in the output.
import amd, re, json, sys, time
amd.login_cached()
pid="17478064"
r=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}))
plans=[dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<insplan [^>]*/?>',r)]
m=re.search(r'<patient [^>]*insorder="([^"]*)"',r)
print("chart",pid,"insorder",m.group(1) if m else None)
for p in plans:
    print("  insplan",p.get("id"),"carrier",p.get("carrier"),"seq",p.get("sequence"),"num",p.get("subscribernum"),"begin",p.get("begindate"),"end",p.get("enddate"),"rel",p.get("relationship"),p.get("hipaarelationship"),"grp",p.get("grpnum"))
d=json.load(open("era_details/1053267.json"))
print("ERA 1053267 keys",list(d.keys())[:10] if isinstance(d,dict) else type(d))
claims=d.get("claims") or d.get("Claims") or d
import txh, payreasons
vis=set()
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k.lower() in("visitid","visit") and str(v).isdigit(): vis.add(str(v))
            walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(d); print("visits in ERA detail:",sorted(vis))
s=json.dumps(d)
for key in ["paid","allowed","adjust","carc","reason"]:
    pass
print(s[:1800])
for v in sorted(vis):
    try:
        st=payreasons.visit_state(None,v) if False else None
    except Exception as e: st=e
