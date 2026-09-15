import amd, txh, json, re, time, collections
amd.login_cached()
AET12="car42009"
aet = json.load(open("aet12_excl_now.json"))
want_visits = {r["visit"] for r in aet}
by_pid = collections.defaultdict(list)
for r in aet: by_pid[r["pid"]].append(r)

def aet_seq(pid):
    r = amd.post(amd.msg("getdemographic","demographics",{"patientid":"pat%s"%pid,"nocookie":"1"}), timeout=60)
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
    return next((p[5] for p in pl if p[1]==AET12 and not p[3]), None) or next((p[5] for p in pl if p[1]==AET12), None)

out=[]; miss=[]
for pid, rows in by_pid.items():
    seq = aet_seq(pid); time.sleep(0.2)
    # open charges on this patient's exclusion visits, on AET12
    root = txh.fetch(pid); time.sleep(0.2)
    vmap=collections.defaultdict(list)
    for c in root.iter("charge"):
        a=c.attrib
        vid=a.get("visit") or a.get("visitid")
        if vid not in want_visits or a.get("void")=="1": continue
        # need a live open charge; txh insbal attr is 'insbalance' sometimes empty -> keep all non-void on the visit
        vmap[vid].append(a.get("id"))
    for r in rows:
        vid=r["visit"]; cids=sorted(set(vmap.get(vid,[])))
        if seq and cids:
            out.append({"visit":vid,"pid":pid,"name":r["name"],"cid":cids[0],"allcids":cids,"seq":seq})
        else:
            miss.append({"visit":vid,"name":r["name"],"seq":seq,"cids":cids})
json.dump(out, open("aet12_rebill_plan.json","w"), indent=1)
json.dump(miss, open("aet12_rebill_missing.json","w"), indent=1)
print("ready visits:", len(out), "| missing:", len(miss), "| patients:", len(by_pid))
if miss: print("miss sample:", miss[:3])
print("seqs seen:", sorted({v["seq"] for v in out}))
