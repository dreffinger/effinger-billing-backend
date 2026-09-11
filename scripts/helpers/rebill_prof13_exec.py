"""Freq-1 rebill the confirmed-unpaid prof13 (Effinger-rendered) Medicaid visits.
Each visit is RE-VERIFIED live immediately before rebilling:
  - profile must still be prof13 (Effinger rendering; group = billing NPI)  -> matches William's request
  - must NOT be settling (no posted non-void payment on the visit)          -> William's standing rule
Then: updextrainsinfo resubmissioncode=1 origrefnum="" per proccode, then chargerebill (204).
No profile change, no charge resave -> NO void risk (freq1_visit mechanics).
Writes rebill_prof13.log ; resumable via DONE lines.
"""
import sys, json, os, time, datetime, re
sys.path[:0]=['/home/claude/effinger-billing-backend/core']
import requests
import xml.etree.ElementTree as ET

S=json.load(open("/home/claude/unbilled/.session.json")); WEB=S["web"]; TOK=S["token"]
XURL=WEB+"/xmlrpc/processrequest.aspx"
REST="https://pm-api-103.advancedmd.com/api/claim/chargerebill"
def mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
sess=requests.Session()

def xml_call(action, attrs, children=""):
    a=" ".join('%s="%s"'%(k,v) for k,v in attrs.items())
    body='<ppmdmsg action="%s" %s msgtime="%s"><usercontext>%s</usercontext>%s</ppmdmsg>'%(action,a,mt(),TOK,children)
    r=sess.post(XURL, data=body, headers={"Content-Type":"text/xml"}, cookies={"token":TOK}, timeout=40)
    return r.text

def detail(cid):
    return xml_call("getchargedetaildataicd10", {"class":"demographics","chargeid":str(cid),"nocookie":"1"})

def rebill(cid, seq):
    cidn=int(re.sub(r"\D","",str(cid)))
    r=sess.post(REST, json={"licensekey":"152563","username":"POI0712","chargedetailfid":cidn,
        "sequencenumber":int(seq),"rebillentireclaim":True,"reason":""},
        headers={"Authorization":"Bearer "+TOK}, timeout=60)
    return r.status_code, r.text[:200]

targets=json.load(open("/home/claude/unbilled/rebill_targets_prof13.json"))
LOG="/home/claude/unbilled/rebill_prof13.log"
done=set()
if os.path.exists(LOG):
    for l in open(LOG):
        m=re.match(r"(DONE|SKIP) (\d+)", l)
        if m: done.add(m.group(2))
f=open(LOG,"a")
def L(m): print(m,flush=True); f.write(m+"\n"); f.flush()

DRY = "--dry" in sys.argv
L("=== rebill prof13 unpaid Medicaid %s dry=%s targets=%d ==="%(mt(),DRY,len(targets)))
ok=0; skip=0; fail=0; money=0.0
for t in targets:
    vid=str(t["visitid"])
    if vid in done: continue
    cids=t["cids"]; cid0=str(cids[0])
    # LIVE re-verify
    try:
        x=detail(cid0); rt=ET.fromstring(x)
    except Exception as e:
        L("SKIP %s live-read-fail %s"%(vid,str(e)[:60])); skip+=1; continue
    vis=rt.find(".//visit")
    if vis is None:
        L("SKIP %s no-visit-elem"%vid); skip+=1; continue
    prof=vis.get("profile")
    paid=any(float(p.get("amount") or 0)!=0 and p.get("void")!="1" for p in rt.iter("payment"))
    insorder=vis.get("insorder") or "1"
    seq=insorder.split(",")[0]
    if prof!="prof13":
        L("SKIP %s profile=%s (not prof13) — Garland-G/other, hold"%(vid,prof)); skip+=1; continue
    if paid:
        L("SKIP %s now-settling (payment posted since scan)"%vid); skip+=1; continue
    # active proccodes on the visit (for extins per code) — from live detail (one charge) + siblings
    # freq1: write resubmissioncode on each proccode present, then rebill the primary charge on seq
    # get all live charges' proccodes via the charge detail we have + the other cids
    proccodes=set()
    livecids=[]
    for c in rt.iter("charge"):
        if c.get("void")!="1" and c.get("proccode"):
            proccodes.add(c.get("proccode")); 
            if c.get("id"): livecids.append(re.sub(r"\D","",c.get("id")))
    # the detail call returns only ONE charge; pull the others' proccodes too
    for extra in cids[1:]:
        try:
            xe=ET.fromstring(detail(str(extra)))
            for c in xe.iter("charge"):
                if c.get("void")!="1" and c.get("proccode"): proccodes.add(c.get("proccode"))
        except Exception: pass
    if DRY:
        L("DRY %s prof13 seq=%s codes=%s cids=%s $%.2f"%(vid,seq,sorted(proccodes),cids,t["bal"])); continue
    # write freq-1 extins per proccode
    vidn=re.sub(r"\D","",vis.get("id"))
    faulted=False
    for pc in sorted(proccodes):
        ext='<extins txtChargeCode="%s" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'%pc
        rr=xml_call("updextrainsinfo",{"class":"chargeentry","visitid":vidn,"nocookie":"1"},ext)
        if "Fault" in rr:
            L("  FAULT extins v%s pc%s: %s"%(vid,pc,re.sub(r'\s+',' ',rr)[:120])); faulted=True; break
    if faulted:
        L("SKIP %s extins-fault"%vid); skip+=1; continue
    time.sleep(0.4)
    code,txt=rebill(cid0, seq)
    if code==204:
        L("DONE %s rebilled prof13 seq=%s $%.2f"%(vid,seq,t["bal"])); ok+=1; money+=t["bal"]
    else:
        L("FAIL %s rebill http=%s %s"%(vid,code,txt[:80])); fail+=1
    time.sleep(0.5)
L("=== prof13 rebill done: ok=%d skip=%d fail=%d  $%.2f queued ==="%(ok,skip,fail,money))
