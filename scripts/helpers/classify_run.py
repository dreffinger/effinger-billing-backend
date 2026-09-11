import amd, resave, json, time, os
import xml.etree.ElementTree as ET
rows=json.load(open("/home/claude/unbilled/medicaid_open.json"))
byvisit={}
for r in rows: byvisit.setdefault((r["car"],r["label"],r["visitid"]), r)
visits=list(byvisit.values())
OUT="/home/claude/unbilled/medicaid_classify.jsonl"
done=set()
if os.path.exists(OUT):
    for ln in open(OUT):
        try: done.add(json.loads(ln)["visitid"])
        except: pass
f=open(OUT,"a")
for v in visits:
    if v["visitid"] in done: continue
    cid=str(v["chargedetailid"]).split(",")[0]
    rec={"car":v["car"],"label":v["label"],"visitid":v["visitid"],"insbalance":v.get("insbalance")}
    try:
        rt=ET.fromstring(resave.detail(cid))
        vis=rt.find(".//visit")
        rec["profile"]=vis.get("profile") if vis is not None else "?"
        rec["paid"]=any(float(x.get("amount") or 0)!=0 and x.get("void")!="1" for x in rt.iter("payment"))
        rec["active_charges"]=len([c for c in rt.iter("charge") if c.get("void")!="1"])
    except Exception as e:
        rec["err"]=str(e)[:80]
    f.write(json.dumps(rec)+"\n"); f.flush()
    time.sleep(0.1)
f.close()
open("/home/claude/unbilled/classify_DONE","w").write("done\n")
