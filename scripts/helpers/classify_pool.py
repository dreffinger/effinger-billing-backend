import json, time, os, datetime, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET

S=json.load(open("/home/claude/unbilled/.session.json")); WEB=S["web"]; TOK=S["token"]
URL=WEB+"/xmlrpc/processrequest.aspx"
def mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
sess=requests.Session()
def classify(v):
    cid=str(v["chargedetailid"]).split(",")[0]
    rec={"car":v["car"],"label":v["label"],"visitid":v["visitid"],"patientid":v.get("patientid"),"insbalance":v.get("insbalance")}
    body='<ppmdmsg action="getchargedetaildataicd10" class="demographics" msgtime="%s" chargeid="%s" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>' % (mt(), cid, TOK)
    try:
        r=sess.post(URL, data=body, headers={"Content-Type":"text/xml"}, cookies={"token":TOK}, timeout=20)
        rt=ET.fromstring(r.text); vis=rt.find(".//visit")
        rec["profile"]=vis.get("profile") if vis is not None else "?"
        rec["insorder"]=vis.get("insorder") if vis is not None else "?"
        rec["paid"]=any(float(p.get("amount") or 0)!=0 and p.get("void")!="1" for p in rt.iter("payment"))
        rec["active_charges"]=len([c for c in rt.iter("charge") if c.get("void")!="1"])
    except Exception as e:
        rec["err"]=str(e)[:80]
    return rec

rows=json.load(open("/home/claude/unbilled/medicaid_open.json"))
byv={}
for r in rows: byv.setdefault(r["visitid"],r)
done=set()
OUT="/home/claude/unbilled/medicaid_classify.jsonl"
for ln in open(OUT):
    try: done.add(json.loads(ln)["visitid"])
    except: pass
todo=[v for v in byv.values() if v["visitid"] not in done]
print("todo", len(todo), "done", len(done), flush=True)
f=open(OUT,"a"); n=0; e=0
with ThreadPoolExecutor(max_workers=5) as ex:
    futs={ex.submit(classify,v):v for v in todo}
    for fut in as_completed(futs):
        try: rec=fut.result(timeout=30)
        except Exception as ex2:
            v=futs[fut]; rec={"visitid":v["visitid"],"car":v["car"],"label":v["label"],"err":"future-timeout"}
        f.write(json.dumps(rec)+"\n"); f.flush(); n+=1
        if "err" in rec: e+=1
        if n%150==0: print(f"  {n}/{len(todo)} err={e}", flush=True)
f.close()
open("/home/claude/unbilled/classify_DONE","w").write("done\n")
print("COMPLETE new",n,"err",e,"total",len(done)+n, flush=True)
