import json, os, time, datetime, re, sys
import requests
import xml.etree.ElementTree as ET
from collections import defaultdict
MAX=int(os.environ.get("MAXPAT","15"))
S=json.load(open(".session.json")); WEB=S["web"]; TOK=S["token"]
XURL=WEB+"/xmlrpc/processrequest.aspx"
def mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
def txh(pid):
    body=('<ppmdmsg action="gettxhistory" class="demographics" msgtime="%s" patientid="%s" filterhistory="0" '
          'pagenumber="1" typefilter="0" sortbypayment="false" groupbyvisit="0" sortdescending="1" visitid="0" '
          'profileid="" getmemo="false" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>'%(mt(),pid,TOK))
    r=requests.post(XURL,data=body,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=30)
    return r.text
def f(x):
    try: return float(x)
    except: return 0.0
rows=json.load(open("medicaid_open.json"))
pat_of=defaultdict(set)
for r in rows:
    if r["car"]!="car6113": continue
    for c in str(r["chargedetailid"]).split(","):
        c=c.strip()
        if c: pat_of[str(r["patientid"])].add(c)
pats=sorted(pat_of.keys())
SCAN="mcad_charge_scan.jsonl"
done_pat=set()
if os.path.exists(SCAN):
    for ln in open(SCAN):
        try:
            d=json.loads(ln)
            if d.get("_pid_done"): done_pat.add(d["_pid_done"])
        except: pass
todo=[p for p in pats if p not in done_pat]
out=open(SCAN,"a"); n=0
for pid in todo[:MAX]:
    try: rt=ET.fromstring(txh(pid))
    except Exception as e:
        out.write(json.dumps({"pid":pid,"err":str(e)[:60]})+"\n"); out.write(json.dumps({"_pid_done":pid})+"\n"); out.flush(); n+=1; continue
    want=pat_of[pid]
    for ch in rt.iter("charge"):
        if ch.get("void")=="1": continue
        cidnum=re.sub(r"\D","",ch.get("id") or "")
        if cidnum not in want: continue
        pay=abs(sum(f(p.get("amount")) for p in ch.iter("payment") if p.get("void")!="1"))
        wo=abs(sum(f(w.get("amount")) for w in ch.iter("writeoff") if w.get("void")!="1"))
        fee=f(ch.get("fee")); ib=f(ch.get("insbal")); pb=f(ch.get("patbal"))
        sig=abs(round(fee-pay-wo,2)-ib)<0.02
        if pay>0 and ib>0.005 and sig: cls="PAID_RESIDUAL"
        elif pay>0 and ib<=0.005: cls="PAID_ZERO"
        elif pay<=0 and ib>0.005: cls="UNPAID_NOPAY"
        elif pb>0.005: cls="PATIENT_BAL"
        else: cls="OTHER"
        out.write(json.dumps({"pid":pid,"vid":ch.get("visit"),"cid":cidnum,"proc":ch.get("proccode"),
            "fee":round(fee,2),"paid":round(pay,2),"wo":round(wo,2),"insbal":round(ib,2),"patbal":round(pb,2),
            "sig":sig,"cls":cls,"carrier":ch.get("carrier") or ch.get("facname")})+"\n")
    out.write(json.dumps({"_pid_done":pid})+"\n"); out.flush(); n+=1
    time.sleep(0.2)
out.close()
print("batch done:", n, "remaining after:", len(todo)-n, flush=True)
