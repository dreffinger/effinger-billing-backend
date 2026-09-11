# PLAIN ENGLISH (9/7 Unbilled scan) - reads only. For each unbilled visit: DOS, fee, balance, insorder, last claim sent (carrier/date), payments on the visit. Writes unbilled_0907_scan.json.
import amd, resave, txh, re, json, time
amd.login_cached()
vs=json.load(open("unbilled_0907.json")); out=[]; TX={}
for v in vs:
    pid=v["patientid"]; cid=v["charges"][0]["id"]
    try:
        x=resave.detail(cid); vis=re.search(r'<visit [^>]*>',x).group(0); va=dict(re.findall(r'(\w+)="([^"]*)"',vis))
        bills=[dict(re.findall(r'(\w+)="([^"]*)"',b)) for b in re.findall(r'<insbill ([^>]*)/>',x)]
        plans=[dict(re.findall(r'(\w+)="([^"]*)"',b)) for b in re.findall(r'<insplan ([^>]*)/>',x)]
        carr={c[0]:c[1] for c in re.findall(r'<carrier id="(car\d+)" name="([^"]*)"',x)}
        if pid not in TX: TX[pid]=txh.fetch(pid)
        chs=[]
        for c in TX[pid].iter("charge"):
            if c.get("visit")==v["id"] and c.get("void")!="1":
                chs.append({"id":c.get("id"),"proc":c.get("proccode"),"fee":c.get("fee"),"insbal":c.get("insbalance"),"patbal":c.get("patbalance"),"carrier":c.get("carrier"),
                    "pays":[(p.get("date"),p.get("carrier"),p.get("amount"),p.get("checknumber")) for p in c.iter("payment") if p.get("void")!="1"],
                    "wos":[(w.get("date"),w.get("wocode"),w.get("amount")) for w in c.iter("writeoff") if w.get("void")!="1"]})
        out.append({"vid":v["id"],"pid":pid,"pt":v["patientname"],"prov":v["provcode"],"err":v["errors"][0][:40],"dos":v["charges"][0]["dos"].strip(),"insorder":va.get("insorder"),"note":va.get("note"),
            "plans":[(p.get("sequence"),p.get("carrier"),carr.get(p.get("carrier"),""),p.get("begindate"),p.get("enddate")) for p in plans],
            "bills":[(b.get("billeddate"),b.get("carriername")) for b in bills][-3:],"charges":chs})
    except Exception as e: out.append({"vid":v["id"],"pt":v["patientname"],"err":v["errors"][0][:40],"error":str(e)[:100]})
    json.dump(out,open("unbilled_0907_scan.json","w"),indent=1); time.sleep(0.2)
print("done",len(out))
