"""One gettxhistory per patient over the past-year unpaid universe. For every open-list charge:
fee/allowed/paid/wo/insbal/patbal/carrier(holding balance)/payerinfo. Derives:
  contractual_gap = fee - allowed - wo  (contractual not yet written off; safe WOINS candidate)
  coins_gap       = allowed - paid - wo_beyond_contractual (coinsurance-shaped; secondary/patient decision)
Bounded per process (MAXPAT); resumable via _pid_done markers."""
import json, os, time, datetime, re
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
    return requests.post(XURL,data=body,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=30).text
def f(x):
    try: return float(x)
    except: return None
rows=json.load(open("allpayer_unpaid_1yr.json"))
pat_charges=defaultdict(dict)  # pid -> cid -> (lastbilled carriercode, visitid, dos, profile)
for r in rows:
    pid=str(r["patientid"])
    for c in str(r.get("chargedetailids") or "").split(","):
        c=c.strip()
        if c: pat_charges[pid][c]=(r.get("carriercode"),str(r["visitid"]),(r.get("dateofservice") or "")[:10],r.get("providerprofilecode"))
pats=sorted(pat_charges)
SCAN="allpayer_charge_scan.jsonl"; done=set()
if os.path.exists(SCAN):
    for ln in open(SCAN):
        try:
            d=json.loads(ln)
            if d.get("_pid_done"): done.add(d["_pid_done"])
        except: pass
todo=[p for p in pats if p not in done]
out=open(SCAN,"a"); n=0
for pid in todo[:MAX]:
    try: rt=ET.fromstring(txh(pid))
    except Exception as e:
        out.write(json.dumps({"pid":pid,"err":str(e)[:60]})+"\n"); out.write(json.dumps({"_pid_done":pid})+"\n"); out.flush(); n+=1; continue
    want=pat_charges[pid]
    for ch in rt.iter("charge"):
        if ch.get("void")=="1": continue
        cid=re.sub(r"\D","",ch.get("id") or "")
        if cid not in want: continue
        lb,vid,dos,prof=want[cid]
        pay=abs(sum(f(p.get("amount")) or 0 for p in ch.iter("payment") if p.get("void")!="1"))
        wo=abs(sum(f(w.get("amount")) or 0 for w in ch.iter("writeoff") if w.get("void")!="1"))
        fee=f(ch.get("fee")) or 0; allowed=f(ch.get("allowed")); ib=f(ch.get("insbal")) or 0; pb=f(ch.get("patbal")) or 0
        sig=abs(round(fee-pay-wo,2)-ib)<0.02
        if pay>0 and ib>0.005: cls="PAID_RESIDUAL" if sig else "PAID_OPEN_NOSIG"
        elif pay>0 and ib<=0.005: cls="PAID_ZERO"
        elif pay<=0 and ib>0.005: cls="UNPAID_NOPAY"
        elif pb>0.005: cls="PATIENT_BAL"
        else: cls="OTHER"
        rec={"pid":pid,"vid":vid,"cid":cid,"dos":dos,"prof":prof,"lastbilled":lb,
             "holder":ch.get("carrier") or "","payerinfo":(ch.get("payerinfo") or "")[:30],
             "proc":ch.get("proccode"),"fee":round(fee,2),"allowed":allowed,"paid":round(pay,2),"wo":round(wo,2),
             "insbal":round(ib,2),"patbal":round(pb,2),"sig":sig,"cls":cls}
        if allowed is not None and allowed>0:
            rec["contractual_gap"]=round(max(0.0,fee-allowed-wo),2)   # un-posted contractual
            rec["coins_gap"]=round(max(0.0,ib-rec["contractual_gap"]),2)  # what's left after contractual
        out.write(json.dumps(rec)+"\n")
    out.write(json.dumps({"_pid_done":pid})+"\n"); out.flush(); n+=1
    time.sleep(0.2)
out.close()
print("batch:",n,"patients | remaining:",len(todo)-n,flush=True)
