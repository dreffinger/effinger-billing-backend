import sys
sys.path[:0] = ['/home/claude/effinger-billing-backend/core']
import json, time, os, threading, queue
import xml.etree.ElementTree as ET
import requests, re, datetime

# --- minimal direct caller with a HARD timeout (no 4x SSL retry storm) ---
S=json.load(open("/home/claude/unbilled/.session.json"))
WEB=S["web"]; TOK=S["token"]
URL=WEB+"/xmlrpc/processrequest.aspx"
def msgtime():
    return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
def detail(cid):
    body='<ppmdmsg action="getchargedetaildataicd10" class="demographics" msgtime="%s" chargeid="%s" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>' % (msgtime(), cid, TOK)
    r=requests.post(URL, data=body, headers={"Content-Type":"text/xml"}, cookies={"token":TOK}, timeout=25)
    return r.text

rows=json.load(open("/home/claude/unbilled/medicaid_open.json"))
byvisit={}
for r in rows: byvisit.setdefault(r["visitid"], r)
visits=list(byvisit.values())
OUT="/home/claude/unbilled/medicaid_classify.jsonl"
done=set()
if os.path.exists(OUT):
    for ln in open(OUT):
        try: done.add(json.loads(ln)["visitid"])
        except: pass
todo=[v for v in visits if v["visitid"] not in done]
print("todo:", len(todo), "already done:", len(done), flush=True)

q=queue.Queue()
for v in todo: q.put(v)
lock=threading.Lock()
f=open(OUT,"a")
cnt=[0]; errcnt=[0]
def worker():
    while True:
        try: v=q.get_nowait()
        except queue.Empty: return
        cid=str(v["chargedetailid"]).split(",")[0]
        rec={"car":v["car"],"label":v["label"],"visitid":v["visitid"],"patientid":v.get("patientid"),"insbalance":v.get("insbalance")}
        try:
            x=detail(cid)
            rt=ET.fromstring(x)
            vis=rt.find(".//visit")
            rec["profile"]=vis.get("profile") if vis is not None else "?"
            rec["insorder"]=vis.get("insorder") if vis is not None else "?"
            rec["paid"]=any(float(p.get("amount") or 0)!=0 and p.get("void")!="1" for p in rt.iter("payment"))
            rec["active_charges"]=len([c for c in rt.iter("charge") if c.get("void")!="1"])
        except Exception as e:
            rec["err"]=str(e)[:80]
        with lock:
            f.write(json.dumps(rec)+"\n"); f.flush()
            cnt[0]+=1
            if "err" in rec: errcnt[0]+=1
            if cnt[0]%100==0: print(f"  {cnt[0]}/{len(todo)} (err {errcnt[0]})", flush=True)
        q.task_done()

NTH=6
ts=[threading.Thread(target=worker) for _ in range(NTH)]
for t in ts: t.start()
for t in ts: t.join()
f.close()
open("/home/claude/unbilled/classify_DONE","w").write("done %d\n" % (len(done)+cnt[0]))
print("DONE. new:", cnt[0], "errors:", errcnt[0], "total:", len(done)+cnt[0], flush=True)
