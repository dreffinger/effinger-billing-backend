# READ-ONLY: compare chart 17478059's CAP07 id format; live state of the two ERA 1053267 visits; chart lookups for the two Pam admits.
import amd, re, json, time
amd.login_cached()
for pid in ["17478059","17478063"]:
    r=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}))
    for p in [dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<insplan [^>]*/?>',r)]:
        print("chart",pid,"insplan",p.get("id"),"carrier",p.get("carrier"),"seq",p.get("sequence"),"num",p.get("subscribernum"))
import txh, payreasons
for v in ["19456177","19456178"]:
    try:
        t=txh.fetch_visit("17477844",v)
        print("visit",v, json.dumps(t)[:900])
    except Exception as e: print("visit",v,"ERR",e)
for pat in ["[name]%","HICSONMEZ,%"]:
    r=amd.post(amd.msg("lookuppatient","lookup",{"name":pat,"nocookie":"1"}))
    rows=[dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<patient [^>]*/?>',r)]
    print(pat[:3]+"*:",[(p.get("id"),p.get("dob")) for p in rows] or "no chart"); time.sleep(0.3)
