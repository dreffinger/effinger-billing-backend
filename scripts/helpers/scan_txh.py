"""Finish the open-Medicaid scan via per-PATIENT gettxhistory (all pages).
For every charge on medicaid_open.json: live fee / paid / writeoff / insbal / patbal / holder / void,
plus visit-level 'any payment'. Bucket for the WOINS pass. Serial, timeout-bounded, session-recycled."""
import json, time, datetime, re, sys, os
import requests
import xml.etree.ElementTree as ET
from collections import defaultdict

S=json.load(open("/home/claude/unbilled/.session.json")); WEB=S["web"]; TOK=S["token"]
XURL=WEB+"/xmlrpc/processrequest.aspx"
def mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
sess=requests.Session(); ncalls=[0]
def post(body, timeout=35):
    global sess
    ncalls[0]+=1
    if ncalls[0]%60==0: sess=requests.Session()
    for attempt in (1,2):
        try:
            r=sess.post(XURL,data=body,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=timeout)
            return r.text
        except Exception as e:
            sess=requests.Session(); time.sleep(2.5)
            if attempt==2: raise
def txh_page(pid,page):
    body=('<ppmdmsg action="gettxhistory" class="demographics" msgtime="%s" patientid="%s" filterhistory="0" '
          'pagenumber="%s" typefilter="0" sortbypayment="false" groupbyvisit="0" sortdescending="1" visitid="0" '
          'profileid="" getmemo="false" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>'%(mt(),pid,page,TOK))
    return ET.fromstring(post(body))
def plans(pid):
    t=post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>'%(mt(),pid,TOK))
    out=[]
    for m in re.finditer(r'<insplan ([^>]*?)/?>', t):
        a=m.group(1); g=lambda k:(re.search(k+r'="([^"]*)"',a) or [None,''])[1]
        out.append({"carrier":g("carrier"),"seq":g("sequence"),"end":g("enddate")})
    return out

rows=json.load(open("/home/claude/unbilled/medicaid_open.json"))
# open-list charges: cid -> row (car,label,visitid,patientid,dos,insbalance)
open_c={}
for r in rows:
    for c in str(r["chargedetailid"]).split(","):
        c=c.strip()
        if c: open_c[c]={"car":r["car"],"label":r["label"],"visitid":r["visitid"],"pid":str(r["patientid"]),"dos":(r.get("dos") or "")[:10],"list_insbal":r.get("insbalance")}
bypid=defaultdict(list)
for cid,r in open_c.items(): bypid[r["pid"]].append(cid)
pids=sorted(bypid, key=lambda p: -len(bypid[p]))
MAXN=int(sys.argv[sys.argv.index("--max")+1]) if "--max" in sys.argv else 10**9
OUT="/home/claude/unbilled/scan_charges.jsonl"
PLN="/home/claude/unbilled/scan_plans.json"
done=set()
if os.path.exists(OUT):
    for ln in open(OUT):
        try: done.add(json.loads(ln)["pid"])
        except: pass
planmap=json.load(open(PLN)) if os.path.exists(PLN) else {}
f=open(OUT,"a")
SMMC={"car6194","car42019","car6174","car41991","car41992"}
print("patients:",len(pids),"already done:",len(done),flush=True)
t0=time.time(); n=0
for pid in pids:
    if pid in done or pid=="None": continue
    charges={}
    try:
        for page in range(1,8):
            th=txh_page(pid,page)
            chs=list(th.iter("charge"))
            for c in chs:
                cid=re.sub(r"\D","",c.get("id") or "")
                if cid and cid not in charges: charges[cid]=c
            if len(chs)<100: break
            time.sleep(0.15)
    except Exception as e:
        f.write(json.dumps({"pid":pid,"err":str(e)[:80]})+"\n"); f.flush(); continue
    # visit-level paid flag
    vpaid=defaultdict(bool)
    for cid,c in charges.items():
        if c.get("void")=="1": continue
        if any(p.get("void")!="1" and float(p.get("amount") or 0)!=0 for p in c.iter("payment")):
            vpaid[c.get("visit")]=True
    # SMMC plan check (only for patients with SMMC-held rows)
    if any(open_c[cid]["car"] in SMMC for cid in bypid[pid]) and pid not in planmap:
        try: planmap[pid]=plans(pid); time.sleep(0.15)
        except Exception as e: planmap[pid]=[{"err":str(e)[:60]}]
    recs=[]
    for cid in bypid[pid]:
        r=open_c[cid]; c=charges.get(cid)
        rec={"pid":pid,"cid":cid,"car":r["car"],"label":r["label"],"visitid":r["visitid"],"dos":r["dos"]}
        if c is None:
            rec["state"]="NOT-IN-HISTORY"; recs.append(rec); continue
        pays=[(p.get("carrier"),float(p.get("amount") or 0)) for p in c.iter("payment") if p.get("void")!="1"]
        wos=[(w.get("carrier"),float(w.get("amount") or 0),w.get("code")) for w in c.iter("writeoff") if w.get("void")!="1"]
        paid=sum(abs(a) for _,a in pays); wo=sum(abs(a) for _,a,_ in wos)
        rec.update({"void":c.get("void"),"proc":c.get("proccode"),"fee":float(c.get("fee") or 0),"paid":round(paid,2),
                    "wo":round(wo,2),"insbal":float(c.get("insbal") or 0),"patbal":float(c.get("patbal") or 0),
                    "holder":c.get("carrier"),"paycar":sorted(set(k for k,_ in pays if k)),"visit_paid":vpaid.get(c.get("visit"),False),
                    "profile":c.get("profileid")})
        recs.append(rec)
    for rec in recs: f.write(json.dumps(rec)+"\n")
    f.flush(); n+=1
    json.dump(planmap,open(PLN,"w"),indent=1)
    if n>=MAXN: break
    if n%20==0: print(f"  {n} patients ({len(done)+n}/{len(pids)}) {time.time()-t0:.0f}s calls={ncalls[0]}",flush=True)
    time.sleep(0.2)
json.dump(planmap,open(PLN,"w"),indent=1)
if len(done)+n>=len([p for p in pids if p!="None"]): open("/home/claude/unbilled/scan_DONE","w").write("done\n")
print("SCAN COMPLETE patients:",len(done)+n,"calls:",ncalls[0],"secs:",int(time.time()-t0),flush=True)
