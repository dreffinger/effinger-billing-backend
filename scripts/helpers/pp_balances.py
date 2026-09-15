import amd, resave, json, time, re
import xml.etree.ElementTree as ET
amd.login_cached()
st = json.load(open("pp_state.json"))
res=[]
for v in st:
    for c in v["charges"]:
        cid=c["cid"]
        try:
            rt = ET.fromstring(resave.detail(cid)); time.sleep(0.15)
            ch = [x for x in rt.iter("charge") if x.get("id")=="charge"+cid]
            if not ch:
                # some builds tag differently
                ch = [x for x in rt.iter("charge")]
            a = ch[0].attrib if ch else {}
            # find insorder chain: list insplan/insurance under charge
            order=[]
            for ip in rt.iter("insplan"):
                order.append((ip.get("sequence") or ip.get("insorder"), ip.get("carrier"), ip.get("payername") or ip.get("carriername")))
            res.append({"visit":v["visit"],"name":v["name"],"cid":cid,"proc":c["proc"],"dos":c["dos"],
                "insbal":a.get("insbalance"),"patbal":a.get("patbalance"),"insportion":a.get("insportion"),
                "carrier":a.get("carrier") or a.get("carrierid"),"npays":len(c["pays"]),"order":order[:4]})
        except Exception as e:
            res.append({"visit":v["visit"],"cid":cid,"err":str(e)[:80]})
json.dump(res, open("pp_balances.json","w"), indent=0)
# summarize
zero=0; pos=0
for r in res:
    ib=r.get("insbal")
    try: ibf=float(ib or 0)
    except: ibf=0
    if ibf>0: pos+=1
    else: zero+=1
print("charges with insbal>0:", pos, " insbal==0:", zero, " total:", len(res))
print("\nsample:")
for r in res[:12]:
    print(r.get("visit"), r.get("name"), r.get("cid"), r.get("proc"), "dos", r.get("dos"), "insbal", r.get("insbal"), "patbal", r.get("patbal"), "npays", r.get("npays"))
