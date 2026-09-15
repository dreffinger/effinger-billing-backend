import resave, json, time, re
import xml.etree.ElementTree as ET
from datetime import date, datetime
st = json.load(open("pp_state.json"))
today = date(2026,9,15)
rows=[]
for v in st:
    for c in v["charges"]:
        cid=c["cid"]
        try:
            rt = ET.fromstring(resave.detail(cid)); time.sleep(0.12)
            ch=[x for x in rt.iter("charge") if x.get("id")=="charge"+cid]
            if not ch: continue
            a=ch[0].attrib
            insbal=float(a.get("insbalance") or 0)
            lastbilled=a.get("lastbilledcarrier")
            datebilled=a.get("datebilled") or ""
            realpays=[]; zeropays=[]
            for p in ch[0].iter("payment"):
                amt=float(p.attrib.get("amount") or 0); dt=p.attrib.get("date") or ""
                (realpays if amt!=0 else zeropays).append((amt,dt))
            # decision
            has_real = len(realpays)>0
            # newest posting date (real or zero)
            alldts=[d for _,d in realpays+zeropays if d]
            def pd(s):
                try: return datetime.strptime(s,"%m/%d/%Y").date()
                except: return None
            newest = max([pd(d) for d in alldts if pd(d)], default=None)
            age = (today-newest).days if newest else None
            rows.append({"visit":v["visit"],"name":v["name"],"cid":cid,"proc":c["proc"],"dos":c["dos"],
                "insbal":insbal,"lastbilled":lastbilled,"datebilled":datebilled[:10],
                "realpays":realpays,"nzero":len(zeropays),"newest":str(newest) if newest else "","age":age,"has_real":has_real})
        except Exception as e:
            rows.append({"visit":v["visit"],"cid":cid,"err":str(e)[:60]})
json.dump(rows, open("pp_decide.json","w"), indent=0)
# classify: release vs writeoff-candidate
rel=[]; wo=[]; rev=[]
for r in rows:
    if "err" in r: rev.append(r); continue
    if r["insbal"]<=0: continue
    if not r["has_real"]:
        rel.append(r)          # no real primary payment -> case (b) release
    else:
        # real primary paid; full-ish balance still open -> secondary not collected
        # window from primary remit: use newest real pay date
        rp = max((datetime.strptime(d,"%m/%d/%Y").date() for _,d in r["realpays"] if _!=0 and d), default=None)
        wdays = (today-rp).days if rp else None
        r["primary_remit"]=str(rp) if rp else ""; r["window_days"]=wdays
        if wdays is not None and wdays>120:
            wo.append(r)
        else:
            rel.append(r)      # window still open -> release, secondary can still be billed
print("RELEASE:", len(rel), " WRITEOFF-CANDIDATE:", len(wo), " REVIEW/ERR:", len(rev))
print("\nWRITEOFF CANDIDATES (real primary pay >120d, balance open):")
for r in wo:
    print("  ", r["name"], r["visit"], r["cid"], r["proc"], "dos",r["dos"], "insbal",r["insbal"], "primary_remit",r.get("primary_remit"),"window",r.get("window_days"))
json.dump({"release":[r["visit"] for r in rel],"writeoff":wo}, open("pp_plan.json","w"), indent=1)
# distinct visits to release
relv = sorted(set(r["visit"] for r in rel))
print("\ndistinct visits to release:", len(relv))
