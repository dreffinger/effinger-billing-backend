"""Freq-1 + rebill the 31 recreated (prof13/Effinger) charges from the Garcia->Effinger swap.
Each recreated charge: createtime today, insbal>0, on a new visit id.
Read each new visit's insorder live -> rebill on the Medicaid (car6113) sequence.
NO profile change here (already prof13). NO void risk (freq1 mechanics only)."""
import sys, json, os, time, re
sys.path[:0]=['/home/claude/effinger-billing-backend/core']
import amd, resave
import xml.etree.ElementTree as ET
import json as _j
CAR=_j.load(open("/home/claude/unbilled/carriers.json"))
MCAD=CAR["MCAD"]  # car6113
mcadnum=re.sub(r"\D","",MCAD)

recreated=json.load(open("/home/claude/unbilled/garcia_recreated.json"))

_PLANCACHE={}
def medicaid_seq(pid):
    """Return the SEQUENCE number of the car6113 (Medicaid) plan for this patient, or None.
    We must bill Medicaid's own sequence, NOT insorder[0] (which may be Medicare)."""
    if pid in _PLANCACHE: return _PLANCACHE[pid]
    t=amd.post('<ppmdmsg action="getdemographic" class="demographics" patientid="pat%s" nocookie="1"/>'%pid)
    seq=None; active=[]
    for m in re.finditer(r'<insplan ([^>]*?)/?>', t):
        a=m.group(1)
        g=lambda k: (re.search(k+r'="([^"]*)"',a) or [None,''])[1]
        car=g("carrier"); s=g("sequence"); end=g("enddate")
        if car==MCAD:
            active.append((s,end))
    # prefer a non-end-dated Medicaid plan; else any
    for s,end in active:
        if not end: seq=s; break
    if seq is None and active: seq=active[0][0]
    _PLANCACHE[pid]=seq
    return seq

LOG="/home/claude/unbilled/garcia_rebill_recreated.log"
done=set()
if os.path.exists(LOG):
    for l in open(LOG):
        m=re.match(r"(DONE|SKIP|FAIL) c(\d+)", l)
        if m: done.add(m.group(2))
f=open(LOG,"a")
def L(m): print(m,flush=True); f.write(m+"\n"); f.flush()
DRY="--dry" in sys.argv
amd.login_cached()

# flatten
allc=[]
for pid,news in recreated.items():
    for n in news: allc.append((pid,n))
L("=== rebill recreated Effinger charges %s dry=%s count=%d ==="%(time.ctime(),DRY,len(allc)))
ok=0; skip=0; fail=0; money=0.0
for pid,n in allc:
    cid=str(n["cid"])
    if cid in done: continue
    # read the new charge's visit to get insorder and confirm carrier sequence
    try:
        d=ET.fromstring(resave.detail(cid))
    except Exception as e:
        L("SKIP c%s detail-fail %s"%(cid,str(e)[:60])); skip+=1; continue
    vis=d.find(".//visit")
    if vis is None: L("SKIP c%s no-visit"%cid); skip+=1; continue
    prof=vis.get("profile"); insorder=vis.get("insorder") or "1"
    patel=d.find(".//patient"); pidn=re.sub(r"\D","",patel.get("id")) if patel is not None else pid
    # Bill MEDICAID's own sequence (car6113), never insorder[0] which may be Medicare/UHC.
    seq=medicaid_seq(pidn)
    ch=[c for c in d.iter("charge") if c.get("id")=="charge"+cid]
    ib=float(ch[0].get("insbalance") or 0) if ch else 0
    if prof!="prof13":
        L("SKIP c%s profile=%s not prof13"%(cid,prof)); skip+=1; continue
    if ib<=0.005:
        L("SKIP c%s insbal=0"%cid); skip+=1; continue
    if seq is None:
        L("SKIP c%s pid%s has NO car6113(Medicaid) plan — cannot bill Medicaid"%(cid,pidn)); skip+=1; continue
    proc=ch[0].get("proccode")
    vidn=re.sub(r"\D","",vis.get("id"))
    if DRY:
        L("DRY c%s v%s prof13 proc=%s insorder=%s MEDICAID_seq=%s $%.2f"%(cid,vidn,proc,insorder,seq,ib)); continue
    # freq-1 extins on this proc
    ext=('<extins txtChargeCode="%s" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" '
         'epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'%proc)
    rr=amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":vidn,"nocookie":"1"},ext))
    if "Fault" in rr:
        L("FAIL c%s extins-fault %s"%(cid,re.sub(r'\s+',' ',rr)[:100])); fail+=1; continue
    time.sleep(0.3)
    code,txt=amd.rebill_charge(cid, seq)
    if code==204:
        L("DONE c%s v%s rebilled seq=%s $%.2f"%(cid,vidn,seq,ib)); ok+=1; money+=ib
    else:
        L("FAIL c%s rebill http=%s %s"%(cid,code,txt[:80])); fail+=1
    time.sleep(0.4)
L("=== recreated rebill done: ok=%d skip=%d fail=%d  $%.2f queued ==="%(ok,skip,fail,money))
