# PLAIN ENGLISH (9am ET 9/18/2026 run 2026-09-18T1310Z): re-reads the three new HCA charts whose visits sit in Unbilled
# with 'Insurance order is missing' (pat17477775, pat17477776, pat17477779) and counts their insplans. Never touches: AMD writes.
import amd, re, json
amd.login_cached(); out={}
for pid in ("17477775","17477776","17477779"):
    t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
    plans=re.findall(r'<insplan [^>]*>',t)
    out[pid]={"insplans":len(plans),"carriers":[dict(re.findall(r'(\w+)="([^"]*)"',p)).get("carrier") for p in plans]}
    print(pid,out[pid])
json.dump(out,open("registers/unbilled_verify_2026-09-18T1310Z.json","w"),indent=1)
