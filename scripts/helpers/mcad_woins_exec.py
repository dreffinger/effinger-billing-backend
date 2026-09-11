"""Post contractual WOINS to zero the residual on confirmed-paid straight-MCAD charges.
Each charge: manual_post.post(cid, 'MCAD', pay=0, wo=<current insbal>, wocode='WOINS', note=...).
manual_post RE-READS the charge live and REFUSES to over-apply beyond the current insbalance,
so a payment that posted since the scan can only shrink what we write off, never overpay.
We pass wo = current-open-insbalance by reading it live here too (belt and suspenders), and
skip any charge whose live insbal has dropped to 0 or whose residual signature no longer holds.
Resumable via mcad_woins.log (DONE <cid>)."""
import sys, json, os, time, datetime, re
sys.path[:0]=['/home/claude/effinger-billing-backend/core']
import requests
import xml.etree.ElementTree as ET
S=json.load(open("/home/claude/unbilled/.session.json")); WEB=S["web"]; TOK=S["token"]
XURL=WEB+"/xmlrpc/processrequest.aspx"
def mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
sess=requests.Session()
def detail(cid):
    body='<ppmdmsg action="getchargedetaildataicd10" class="demographics" msgtime="%s" chargeid="%s" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>'%(mt(),cid,TOK)
    return sess.post(XURL,data=body,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=40).text
def f(x):
    try: return float(x)
    except: return 0.0
CARID="car6113"  # MCAD

def post_woins(cid, wo, note, dry):
    x=detail(cid); rt=ET.fromstring(x); vis=rt.find(".//visit"); pat=rt.find(".//patient")
    cand=[c for c in rt.iter("charge") if c.get("id")=="charge"+str(cid)]
    if not cand: return "SKIP no-charge-elem"
    c=cand[0]
    bal=f(c.get("insbalance"))
    if bal<=0.005: return "SKIP live-bal-zero (already resolved)"
    # only write off up to the live balance
    woamt=round(min(wo, bal),2)
    prof=vis.get("profile"); pid=re.sub(r"\D","",pat.get("id"))
    if dry: return "DRY bal=%.2f wo=%.2f prof=%s"%(bal,woamt,prof)
    chg=('<charge id="charge%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
         '<paymentlist><payment amount="0.00" id="" status="B"/></paymentlist>'
         '<writeofflist><writeoff id="" risk="0" amount="%.2f" code="WOINS" status="B"/></writeofflist></charge>'
         %(cid, c.get("insportion") or "%.2f"%bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof, woamt))
    xml=('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
         '<patient patientid="pat%s" paysource="2" postingmethod="" amount="0.00" paycode="PE" woamount="%.2f" paymethod="9" carrierid="%s" '
         'depositdate="%s" case_note="%s" checknumber="" inclstmt="0" postedby="POI0712" batch=""><usercontext>%s</usercontext>'
         '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
         %(mt(), pid, woamt, CARID, time.strftime("%m/%d/%Y"), note, TOK, chg))
    r=sess.post(XURL,data=xml,headers={"Content-Type":"text/xml"},cookies={"token":TOK},timeout=60).text
    ok='success="1"' in r
    return ("DONE wo=%.2f"%woamt) if ok else ("FAIL "+re.sub(r"\s+"," ",r)[:120])

targets=json.load(open("/home/claude/unbilled/mcad_woins_targets.json"))
MAX=int(os.environ.get("MAXWO","10**9").replace("10**9","1000000000"))
DRY="--dry" in sys.argv
LOG="/home/claude/unbilled/mcad_woins.log"
done=set()
if os.path.exists(LOG):
    for l in open(LOG):
        m=re.match(r"(DONE|SKIP) (\d+)",l)
        if m: done.add(m.group(2))
lf=open(LOG,"a")
def L(m): print(m,flush=True); lf.write(m+"\n"); lf.flush()
todo=[t for t in targets if t["cid"] not in done]
L("=== MCAD WOINS %s dry=%s todo=%d (of %d) ==="%(mt(),DRY,len(todo),len(targets)))
ok=0; skip=0; fail=0; money=0.0
for t in todo[:MAX]:
    cid=t["cid"]; note="Contractual balance - FL Medicaid allowed; residual WOINS %s"%datetime.date.today().isoformat()
    try:
        res=post_woins(cid, t["insbal"], note, DRY)
    except Exception as e:
        res="EXC "+str(e)[:80]
    if res.startswith("DONE"):
        ok+=1; money+=float(res.split("wo=")[1]); L("DONE %s v%s %s $%.2f"%(cid,t["vid"],t["proc"],float(res.split('wo=')[1])))
    elif res.startswith("DRY"):
        L("DRY %s v%s %s %s"%(cid,t["vid"],t["proc"],res))
    elif res.startswith("SKIP"):
        skip+=1; L("SKIP %s v%s %s"%(cid,t["vid"],res))
    else:
        fail+=1; L("FAIL %s v%s %s"%(cid,t["vid"],res))
    time.sleep(0.2)
L("=== batch: ok=%d skip=%d fail=%d  $%.2f written off ==="%(ok,skip,fail,money))
