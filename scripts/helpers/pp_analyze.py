# Analyze prior-payor unbilled visits: for each visit, read gettxhistory to find
# the charge's insorder chain + whether primary has a payment/recent claim.
import amd, txh, json, re, time, sys
import xml.etree.ElementTree as ET
amd.login_cached()
pats = json.load(open("prior_payor_pats.json"))
# map visitid -> patient
vis2pat = {}
for pid, d in pats.items():
    for vid in d["visits"]: vis2pat[vid] = (pid, d["name"])

out = []
for pid, d in pats.items():
    root = txh.fetch(pid); time.sleep(0.3)
    # index charges by visit
    byv = {}
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void")=="1": continue
        vid = a.get("visitid") or a.get("visit") or ""
        pays=[]; wos=[]
        for p in c.iter("payment"):
            pays.append({k:p.attrib.get(k) for k in ("amount","date","carrier","paycode","source")})
        for w in c.iter("writeoff"):
            wos.append({k:w.attrib.get(k) for k in ("amount","date","code")})
        byv.setdefault(vid, []).append({"cid":a.get("id"),"proc":a.get("proccode"),"dos":a.get("dos") or a.get("dateofservice"),
            "insbal":a.get("insbalance"),"patbal":a.get("patbalance"),"amount":a.get("amount"),
            "carrier":a.get("carrier") or a.get("carriercode"),"insorder":a.get("insorder") or a.get("insuranceorder"),
            "pays":pays,"wos":wos})
    for vid in d["visits"]:
        chs = byv.get(vid, [])
        out.append({"visit":vid,"pid":pid,"name":d["name"],"charges":chs})
json.dump(out, open("pp_state.json","w"), indent=0)
# Summarize
rel=0; wo=0; unclear=0
for v in out:
    for c in v["charges"]:
        haspay = any(float(p["amount"] or 0)!=0 for p in c["pays"])
        print(v["visit"], v["name"], "| chg", c["cid"], c["proc"], "dos", c["dos"], "insbal", c["insbal"], "patbal", c["patbal"], "insorder", c["insorder"], "| pays", len(c["pays"]), "wos", len(c["wos"]))
