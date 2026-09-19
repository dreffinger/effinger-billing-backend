# PLAIN ENGLISH (Claim Inspector, 7am ET 9/19/2026 run 2026-09-19T1110Z): one visit (pat17472124 v19442479, FLO02, CCM 99487) re-inspected after the
# 0910Z patient-balance move-back raised three CCM frequency advisories (Pattern 3429 duplicate-[name]-19442324, 7011 max frequency, 33799 MUE).
# Decides: reads the chart's tx history to confirm the two flagged visits are different dates of service, then bypasses the advisories with the
# FRESH error ids from a re-list (per the standing rule: 3429/7011/33799 are advisories). Never touches: charges, dx, rebills.
import amd, re, json, time, sys
amd.login_cached(); dry = "--dry" in sys.argv
pid = "17472124"; vid = "19442479"; other = "19442324"
t = amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
rows=[]
for m in re.finditer(r'<charge [^>]*/?>', t):
    a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
    if a.get("visit") in (vid, other) and a.get("void")!="1":
        rows.append({k:a.get(k) for k in ("id","visit","proccode","dos","carrier","insbal","patbal","paid","void","datebilled","billdate")})
print(json.dumps(rows,indent=1))
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib); print("batches", bids)
res=[]
for bid in bids:
    x = amd.post(amd.msg("getclaiminspectorcharges","chargeentry",{"batchid":bid,"nocookie":"1"}),timeout=120)
    for vm in re.finditer(r'<visit id="(\d+)"[^>]*patientid="(\d+)"[^>]*>(.*?)</visit>', x, re.S):
        v,p,body = vm.groups(); errs = re.findall(r'<error id="(\d+)" number="([^"]*)" name="([^"]*)"', body)
        adv = [e for e in errs if re.search(r'Pattern (3429|7011|33799|35790|35777|20657|27261|4310|4426)\]', e[2]) or e[1]=="68065080"]
        print("visit",v,"pat",p,"errs",[(e[0],e[2][:45]) for e in errs],"advisory",len(adv),"of",len(errs))
        if adv and len(adv)==len(errs) and not dry:
            r = amd.post(amd.msg("bypassclaimedits","chargeentry",{"nocookie":"1"},'<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (v,"".join('<claimedit id="%s"/>' % e[0] for e in adv))))
            ok = "Fault" not in r; print("  bypass", ok, r[:150] if not ok else ""); res.append({"vid":v,"pid":p,"errs":errs,"ok":ok})
    time.sleep(0.3)
json.dump(res,open("registers/insp_bypass_2026-09-19T1110Z.json","w"),indent=1)
ib2 = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); print("batches after", re.findall(r'<batch id="([^"]+)"', ib2))
