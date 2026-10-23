# READ-ONLY: (1) AMD free 271 on chart 17478064's CAP07 plan - read the subscriber id CHP echoes back (NM1*IL segment) to learn the id
# format CHP recognizes; (2) live charge state of ERA 1053267's two visits (fee / paid / patient balance / insurance balance).
import amd, re, json, txh
amd.login_cached()
r=amd.check_eligibility("9520948")
s=r if isinstance(r,str) else json.dumps(r)
m=re.search(r'eligibilitystatus\w*="([^"]*)"',s); print("elig status attr:",m.group(1) if m else None)
for seg in re.findall(r'NM1\*(?:IL|1P|PR)\*[^~]*',s): print("  ",seg[:120])
for seg in re.findall(r'REF\*[^~]{0,60}',s)[:6]: print("  ",seg)
for seg in re.findall(r'AAA\*[^~]*',s)[:4]: print("  ",seg)
for seg in re.findall(r'DTP\*[^~]*',s)[:4]: print("  ",seg)
print("subscriberid attr:",re.findall(r'subscriberid="([^"]*)"',s)[:3])
for v in ["19456177","19456178"]:
    root=txh.fetch_visit("17477844",v)
    for c in root.iter("charge"):
        if c.get("void")=="1" or c.get("visit")!=v: continue
        print("visit",v,"charge",c.get("id"),"cpt",c.get("proccode") or c.get("cpt"),"dos",c.get("dos"),"fee",c.get("fee"),"paid",c.get("paid"),"patbal",c.get("patbal"),"insbal",c.get("insbal"),"carrier",c.get("carrier"),"billdate",c.get("billdate"))
        for p in c.iter("payment"): print("    payment",p.get("id"),"amt",p.get("amount"),"chk",p.get("checknumber") or p.get("refnum"),"void",p.get("void"),"code",p.get("code"))
        for w in c.iter("writeoff"): print("    writeoff",w.get("id"),"amt",w.get("amount"),"code",w.get("code"),"void",w.get("void"))
