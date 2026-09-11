"""For the classified 'paid'(settling) Medicaid visits, pull CHARGE-LEVEL financials:
paid, writeoff, insbal, patbal — so we can tell whether they're truly resolved (paid+WO, $0 bal)
or have an open insurance balance despite a posted payment.
Uses gettxhistory per patient (cached), reads the charge lines on the open visits."""
import json, os, time, datetime, re, sys
import requests
import xml.etree.ElementTree as ET
from collections import defaultdict
S=json.load(open(".session.json")); WEB=S["web"]; TOK=S["token"]
XURL=WEB+"/xmlrpc/processrequest.aspx"
def mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
sess=requests.Session()
def txh(pid):
    body=('<ppmdmsg action="gettxhistory" class="demographics" msgtime="%s" patientid="%s" filterhistory="0" '
          'pagenumber="1" typefilter="0" sortbypayment="false" groupbyvisit="0" sortdescending="1" visitid="0" '
          'profileid="" getmemo="false" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>'%(mt(),pid,TOK))
    r=sess.post(XURL,data=body,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=40)
    return r.text

# open Medicaid charge rows, indexed
rows=json.load(open("medicaid_open.json"))
open_charge_ids=set()
visit_of_charge={}
for r in rows:
    for c in str(r["chargedetailid"]).split(","):
        c=c.strip()
        if c: open_charge_ids.add(c); visit_of_charge[c]=r["visitid"]

# classified paid visits with a patientid (the 2nd+ classify runs captured patientid)
cls=[]
for ln in open("medicaid_classify.jsonl"):
    try: r=json.loads(ln)
    except: continue
    if r.get("err") or not r.get("paid"): continue
    if not r.get("patientid"): continue
    cls.append(r)
# unique patients among paid visits
pats={}
for r in cls: pats.setdefault(str(r["patientid"]), []).append(r["visitid"])
paidvisits=set(r["visitid"] for r in cls)
print("paid(settling) visits w/ pid:", len(paidvisits), "across", len(pats), "patients", flush=True)

# sample: first 60 patients (enough to characterize)
sample_pids=list(pats.keys())[:60]
OUT=open("paidcheck.jsonl","w")
n=0
for pid in sample_pids:
    try:
        rt=ET.fromstring(txh(pid))
    except Exception as e:
        OUT.write(json.dumps({"pid":pid,"err":str(e)[:60]})+"\n"); continue
    want=set(str(v) for v in pats[pid])
    for ch in rt.iter("charge"):
        if ch.get("void")=="1": continue
        vid=ch.get("visit")
        if vid not in want: continue
        # sum payments and writeoffs on this charge
        pay=sum(float(p.get("amount") or 0) for p in ch.iter("payment") if p.get("void")!="1")
        wo=sum(float(w.get("amount") or 0) for w in ch.iter("writeoff") if w.get("void")!="1")
        rec={"pid":pid,"vid":vid,"cid":ch.get("id"),"proc":ch.get("proccode"),
             "fee":ch.get("fee"),"paid":round(pay,2),"writeoff":round(wo,2),
             "insbal":ch.get("insbal"),"patbal":ch.get("patbal"),
             "carrier":ch.get("carrier") or ch.get("facname"),"payerinfo":ch.get("payerinfo")}
        OUT.write(json.dumps(rec)+"\n"); n+=1
    OUT.flush()
    time.sleep(0.15)
OUT.close()
print("wrote", n, "charge-financial rows for", len(sample_pids), "patients", flush=True)
