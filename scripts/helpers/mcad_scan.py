"""One gettxhistory per MCAD patient -> classify EVERY open-list MCAD charge:
   - PAID_RESIDUAL: has posted payment AND insbal>0 AND insbal == fee-paid-wo  -> contractual WOINS target
   - PAID_ZERO: paid, insbal 0 (already resolved; shouldn't be on list, informational)
   - UNPAID_NOPAY: insbal>0, NO posted payment (genuinely unpaid; NOT a write-off)
   - PATIENT_BAL: patbal>0 (do not touch here)
Writes mcad_charge_scan.jsonl (resumable per patient) and mcad_woins_targets.json.
Only straight MCAD car6113 open-list charges are considered."""
import json, os, time, datetime, re
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
    r=sess.post(XURL,data=body,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=45)
    return r.text
def f(x):
    try: return float(x)
    except: return 0.0

rows=json.load(open("medicaid_open.json"))
# open MCAD charge ids and their visits
mcad_charge=set(); pat_of=defaultdict(set)
for r in rows:
    if r["car"]!="car6113": continue
    pid=str(r["patientid"])
    for c in str(r["chargedetailid"]).split(","):
        c=c.strip()
        if c: mcad_charge.add(c); pat_of[pid].add(c)
pats=sorted(pat_of.keys())
print("MCAD patients:", len(pats), "open MCAD charges:", len(mcad_charge), flush=True)

SCAN="mcad_charge_scan.jsonl"
done_pat=set()
if os.path.exists(SCAN):
    for ln in open(SCAN):
        try: done_pat.add(json.loads(ln).get("_pid_done"))
        except: pass
    done_pat.discard(None)
out=open(SCAN,"a")
n=0
for pid in pats:
    if pid in done_pat: continue
    try:
        rt=ET.fromstring(txh(pid))
    except Exception as e:
        out.write(json.dumps({"pid":pid,"err":str(e)[:60]})+"\n"); out.flush(); continue
    want=pat_of[pid]
    for ch in rt.iter("charge"):
        if ch.get("void")=="1": continue
        cidnum=re.sub(r"\D","",ch.get("id") or "")
        if cidnum not in want: continue
        pay=sum(f(p.get("amount")) for p in ch.iter("payment") if p.get("void")!="1")  # negative credits
        wo=sum(f(w.get("amount")) for w in ch.iter("writeoff") if w.get("void")!="1")   # negative
        paidabs=abs(pay); woabs=abs(wo)
        fee=f(ch.get("fee")); ib=f(ch.get("insbal")); pb=f(ch.get("patbal"))
        # residual signature
        leftover = round(fee - paidabs - woabs, 2)
        sig = abs(leftover - ib) < 0.02
        if paidabs>0 and ib>0.005 and sig:
            cls="PAID_RESIDUAL"
        elif paidabs>0 and ib<=0.005:
            cls="PAID_ZERO"
        elif paidabs<=0 and ib>0.005:
            cls="UNPAID_NOPAY"
        elif pb>0.005:
            cls="PATIENT_BAL"
        else:
            cls="OTHER"
        rec={"pid":pid,"vid":ch.get("visit"),"cid":cidnum,"proc":ch.get("proccode"),
             "fee":round(fee,2),"paid":round(paidabs,2),"wo":round(woabs,2),
             "insbal":round(ib,2),"patbal":round(pb,2),"sig":sig,"cls":cls,
             "carrier":ch.get("carrier") or ch.get("facname")}
        out.write(json.dumps(rec)+"\n")
    out.write(json.dumps({"_pid_done":pid})+"\n"); out.flush()
    n+=1
    if n%20==0: print(f"  {n}/{len(pats)} patients", flush=True)
    time.sleep(0.25)
out.close()
open("mcad_scan_DONE","w").write("done\n")
print("SCAN COMPLETE patients processed this run:", n, flush=True)
