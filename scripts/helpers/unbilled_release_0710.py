# PLAIN ENGLISH (Unbilled release, 3am ET 9/15/2026 run): releases the verified 'prior payor' rows (class release-b, plus
# Garrow whose Medicaid payment is 112 days old = window open) with hideunbillablevisits hide=-1 in chunks; for the three
# 2025 Medicare crossover leftovers past the secondary window (Waldron x2, Plessy) posts a contractual WOINS with a dated note
# via manual_post.post (pay 0, wo = open insbal) and then releases them. Register: registers/unbilled_release_<stamp>.json
import amd, re, json, time, sys, manual_post
S="2026-09-15T0710Z"; DRY="--dry" in sys.argv
v=json.load(open("registers/unbilled_verify_%s.json"%S))
rel=[vid for vid,d in v.items() if d["class"]=="release-b" or vid=="19441047"]
wo=[vid for vid,d in v.items() if d["class"]=="hold-a" and vid!="19441047"]
reg={"released":[],"writeoffs":[],"errors":[]}
# write-offs first
for vid in wo:
    d=v[vid]; pid=d["pid"]
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit")==vid and float(a.get("insbal") or 0)>0:
            cid=a["id"]; bal=float(a["insbal"]); car=a.get("carrier") or a.get("lastbilledcarrier")
            note="Contractual - Medicare paid %s, secondary window passed (prior payor rule 9/8) - run %s"%(a.get("datebilled") or a.get("billdate"), S)
            try:
                r=manual_post.post(cid, car, 0.0, bal, "WOINS", checknumber="", depositdate=None, note=note, dry=DRY)
                reg["writeoffs"].append({"vid":vid,"cid":cid,"pid":pid,"carrier":car,"wo":bal,"dos":a.get("dos"),"result":str(r)[:200]})
                print("WO",vid,cid,car,bal,str(r)[:120])
            except Exception as e:
                reg["errors"].append({"vid":vid,"cid":cid,"err":str(e)[:200]}); print("WO ERROR",vid,cid,e)
    rel.append(vid)
# release in chunks
for i in range(0,len(rel),25):
    chunk=rel[i:i+25]
    if DRY: print("DRY release",chunk); continue
    xml=amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"','<visitlist>%s</visitlist>'%"".join('<visit id="%s"/>'%c for c in chunk))
    ok='success="1"' in xml or ('<Error' in xml and '<Error/>' in xml) or '<Error />' in xml
    reg["released"].append({"visits":chunk,"ok":ok,"resp":re.sub(r'\s+',' ',xml)[:200]})
    print("release chunk",len(chunk),"ok" if ok else "??",re.sub(r'\s+',' ',xml)[:160])
json.dump(reg,open("registers/unbilled_release_%s%s.json"%(S,"_dry" if DRY else ""),"w"),indent=1)
print("released",sum(len(c["visits"]) for c in reg["released"]),"writeoffs",len(reg["writeoffs"]),"errors",len(reg["errors"]))
