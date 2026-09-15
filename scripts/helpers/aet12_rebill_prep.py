# For each AET12 exclusion visit, find the open AET12 charge(s) + the AET12 sequence.
import amd, resave, json, re, time
import xml.etree.ElementTree as ET
amd.login_cached()
aet = json.load(open("aet12_excl_now.json"))
AET12="car42009"
out=[]; missing=[]
# group visits by patient to reuse demographic seq lookup
by_v={}
for r in aet: by_v[r["visit"]]=r
for vid,r in by_v.items():
    # get visit detail via any charge: use getvisitdetail to list charges, else resave by visit
    # Simplest: pull demographic for insorder/seq of AET12, and gettxhistory for open charges on this visit
    try:
        # find charges on this visit through resave.visit_charges needs a charge id; get one from getclaimexclusion? we only have visit.
        # Use getvisitcharges via chargeentry
        vx = amd.post(amd.msg("getchargedetaildataicd10","chargeentry",{"visitid":vid,"nocookie":"1"}), timeout=60)
        cids = re.findall(r'<charge [^>]*id="charge(\d+)"', vx)
        cids = sorted(set(cids))
        if not cids:
            # fallback: getvisitdetail
            vd = amd.post(amd.msg("getvisitdetail","visit",{"visitid":vid,"nocookie":"1"}), timeout=60)
            cids = sorted(set(re.findall(r'chargedetailid="(\d+)"', vd) + re.findall(r'id="charge(\d+)"', vd)))
    except Exception as e:
        cids=[]
    open_ci=[]; seq=None
    for cid in cids:
        try:
            rt=ET.fromstring(resave.detail(cid))
            c=[x for x in rt.iter("charge") if x.get("id")=="charge"+cid]
            if not c: continue
            c=c[0]
            bal=float(c.get("insbalance") or 0)
            # find AET12 sequence in the plan list
            for ip in rt.iter("insplan"):
                if ip.get("carrier")==AET12: seq=ip.get("sequence")
            if c.get("void")=="1" or bal<=0: continue
            open_ci.append({"cid":cid,"proc":c.get("proccode"),"bal":bal,"lastbilled":c.get("lastbilledcarrier")})
        except Exception as e:
            pass
    if open_ci and seq:
        out.append({"visit":vid,"pid":r["pid"],"name":r["name"],"claimid":r["claimid"],"seq":seq,"charges":open_ci})
    else:
        missing.append({"visit":vid,"name":r["name"],"cids":cids,"seq":seq,"open":len(open_ci)})
    time.sleep(0.2)
json.dump(out, open("aet12_rebill_plan.json","w"), indent=1)
json.dump(missing, open("aet12_rebill_missing.json","w"), indent=1)
print("ready:", len(out), "visits;", sum(len(v["charges"]) for v in out), "charges | missing:", len(missing))
if missing: print("MISSING sample:", missing[:3])
print("bal total: %.2f" % sum(c["bal"] for v in out for c in v["charges"]))
