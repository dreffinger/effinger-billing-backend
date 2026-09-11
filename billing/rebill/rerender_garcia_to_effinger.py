"""Re-render the 30 confirmed-unpaid prof15 (Garcia) Medicaid visits to prof13 (Effinger).
AUTHORIZED by William 9/11/2026 on his explicit representation that these were Dr. Effinger's
own personally-performed visits (resolves the FL-Medicaid no-APRN-incident-to concern).

VOID-TRAP DISCIPLINE:
 - build every resave from resave.visit_charges() (ALL active charges, each by its own detail call)
 - echo every active charge with full CHG_FIELDS; a profile change VOIDS old charges & recreates them
 - record pre-count of active charge lines per visit; post-batch void_scan recounts to prove nothing lost
 - re-verify live: profile still prof15 AND not settling (no posted payment) BEFORE each swap
 - after swap: locate NEW live charges, resubmissioncode=1, rebill on the Medicaid sequence
No FS modifier (these are Effinger's own visits, not split/shared).
Writes garcia_to_effinger.log ; resumable via DONE lines.  --dry to preview.
"""
import sys, json, os, time, re
sys.path[:0]=['/home/claude/effinger-billing-backend/core']
import amd, resave
import xml.etree.ElementTree as ET

EFFINGER="prof13"; GARCIA="prof15"
DRY="--dry" in sys.argv
targets=json.load(open("/home/claude/unbilled/hold_prof15_garcia.json"))
rows=json.load(open("/home/claude/unbilled/medicaid_open.json"))
# map visit -> its charge detail ids (to seed visit_charges)
byvisit={}
for r in rows:
    for c in str(r["chargedetailid"]).split(","):
        c=c.strip()
        if c: byvisit.setdefault(r["visitid"],[]).append(c)

LOG="/home/claude/unbilled/garcia_to_effinger.log"
done=set()
if os.path.exists(LOG):
    for l in open(LOG):
        m=re.match(r"(DONE|SKIP) v(\d+)", l)
        if m: done.add(m.group(2))
f=open(LOG,"a")
def L(m): print(m,flush=True); f.write(m+"\n"); f.flush()

# pre/post active-charge counts per patient for the void scan
prepost="/home/claude/unbilled/garcia_prepost.json"
counts=json.load(open(prepost)) if os.path.exists(prepost) else {}

def active_charges_of_visit(vis_elem_charges):
    return [c for c in vis_elem_charges if c.get("void")!="1"]

L("=== Garcia(prof15)->Effinger(prof13) re-render %s dry=%s targets=%d ==="%(time.ctime(),DRY,len(targets)))
amd.login_cached()
ok=0; skip=0; fail=0; money=0.0
for t in targets:
    vid=str(t["visitid"])
    if vid in done: continue
    cids=byvisit.get(t["visitid"],[])
    if not cids:
        L("SKIP v%s no-charge-ids"%vid); skip+=1; continue
    cid0=str(cids[0])
    # LIVE re-read all active charges + visit
    try:
        vis, pat, charges = resave.visit_charges(cid0)
    except Exception as e:
        L("SKIP v%s visit_charges-fail %s"%(vid,str(e)[:70])); skip+=1; continue
    if vis is None or pat is None:
        L("SKIP v%s no-visit/patient"%vid); skip+=1; continue
    prof=vis.get("profile")
    insorder=vis.get("insorder") or "1"
    seq=insorder.split(",")[0]
    # settling check: pull the charge detail for payments (visit_charges gives charge elems w/o payment children reliably)
    # re-read one detail for payment scan
    paid=False
    try:
        rt=ET.fromstring(resave.detail(cid0))
        paid=any(float(p.get("amount") or 0)!=0 and p.get("void")!="1" for p in rt.iter("payment"))
    except Exception: pass
    if prof!=GARCIA:
        L("SKIP v%s profile=%s (not prof15 — already moved or other)"%(vid,prof)); skip+=1; continue
    if paid:
        L("SKIP v%s now-settling (payment posted since scan)"%vid); skip+=1; continue
    if not charges:
        L("SKIP v%s no-active-charges"%vid); skip+=1; continue
    precount=len(charges)
    # build charge echo
    chg=""
    for c in charges:
        a={"id":c.get("id")}
        for fld in resave.CHG_FIELDS:
            v=c.get(fld)
            if v is not None: a[fld]=v
        chg+="<charge %s/>"%" ".join('%s="%s"'%(k,v) for k,v in a.items())
    # visit attrs: echo identity + insorder/refplan/facility, override profile
    va={"id":vis.get("id"),"date":vis.get("date"),"profile":EFFINGER,
        "insorder":vis.get("insorder"),"refplan":vis.get("refplan"),
        "facility":vis.get("facility"),"force":"1"}
    if vis.get("onhcfa") is not None: va["onhcfa"]=vis.get("onhcfa")
    vs=" ".join('%s="%s"'%(k,v) for k,v in va.items() if v is not None)
    if DRY:
        L("DRY v%s prof15->prof13 seq=%s charges=%d cids=%s $%.2f"%(vid,seq,precount,cids,t["bal"]))
        continue
    body=amd.msg("updvisitwithnewcharges","chargeentry",
        {"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1",
         "inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist></visit>"%(vs,chg))
    r=amd.post(body)
    if "Fault" in r:
        desc=(re.search(r"<description>([^<]*)",r) or [None,r[:120]])[1]
        L("FAIL v%s resave-fault: %s"%(vid,re.sub(r'\s+',' ',desc)[:120])); fail+=1; continue
    time.sleep(0.8)
    # locate NEW live charges (same or new visit id)
    rr=ET.fromstring(r)
    newvis=rr.find(".//visit")
    newvid=(newvis.get("id") if newvis is not None else vis.get("id")) or vis.get("id")
    live=[c for c in rr.iter("charge") if c.get("void")!="1"]
    if not live:
        # re-fetch via visit_charges on the original cid (it will follow to the new charges)
        try:
            _, _, live2 = resave.visit_charges(cid0)
            live=live2
            if live: 
                # get the new visit id from a live charge's detail
                d2=ET.fromstring(resave.detail(re.sub(r"\D","",live[0].get("id"))))
                nv=d2.find(".//visit"); newvid=nv.get("id") if nv is not None else newvid
        except Exception: pass
    postcount=len(live)
    newvid_num=re.sub(r"\D","",newvid)
    # freq-1 + rebill ONLY new charges that carry an open insurance balance.
    # (Echo above preserved every active charge — void-trap safe — but a $0-balance
    #  sibling that was already resolved must NOT be rebilled: pat44976 v19394091.)
    rebilled=0; skipped_zero=0
    for c in live:
        ncid=c.get("id"); ncid_num=re.sub(r"\D","",ncid); pc=c.get("proccode")
        ib=float(c.get("insbalance") or 0)
        if ib<=0.005:
            skipped_zero+=1
            L("   preserve (no rebill) c%s %s insbal=0"%(ncid,pc)); continue
        ext=('<extins txtChargeCode="%s" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" '
             'epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'%pc)
        amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":newvid_num,"nocookie":"1"},ext))
        code,_=amd.rebill_charge(ncid, seq)
        if code==204: rebilled+=1
        else: L("   rebill http=%s on c%s"%(code,ncid))
        time.sleep(0.3)
    counts[vid]={"pre":precount,"post":postcount,"newvid":newvid,"pid":pat.get("id"),"rebilled":rebilled,"preserved":skipped_zero}
    json.dump(counts,open(prepost,"w"))
    flag = "" if postcount==precount else "  ** CHARGE COUNT CHANGED pre=%d post=%d **"%(precount,postcount)
    L("DONE v%s -> %s prof13 seq=%s charges pre=%d post=%d rebilled=%d preserved=%d $%.2f%s"%(vid,newvid,seq,precount,postcount,rebilled,skipped_zero,t["bal"],flag))
    ok+=1; money+=t["bal"]
    time.sleep(0.6)
L("=== Garcia->Effinger done: ok=%d skip=%d fail=%d  $%.2f queued ==="%(ok,skip,fail,money))
