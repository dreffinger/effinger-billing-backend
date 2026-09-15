# PLAIN ENGLISH (Clack corrected claim, 3am ET 9/15/2026 run - William 9/15 06:52Z 'yes do that'):
# 1) void the 9/9/2026 WOINS $206 (wo22476007) on charge 23340937 (2/26/2026 99487, visit 19434042);
# 2) confirm the $206 is back on the INSURANCE balance (move it back if it landed on the patient);
# 3) change the Florida Blue plan ins9514111 member id XYL991586758 -> X3LM65856326 (the BCBS-of-Michigan MA id
#    Florida Blue echoed); 4) set the visit's extins to frequency 7 with the payer claim number the $0 ERA payment
#    carries (origrefnum H100001346973572) and rebill sequence 1. Stops at the first fault.
# Never touches: any other charge or plan.
import amd, void_tx, ins_update, resave, re, time, json, sys
PID="17473476"; CID="23340937"; VID="19434042"; WOID="22476007"; INS="9514111"; ICN="H100001346973572"
NEWID="X3LM65856326"; OLDID="XYL991586758"; log={}
ch,wos,pays=void_tx.charge_state(CID)
print("before: insbalance",ch.get("insbalance"),"patbalance",ch.get("patbalance"),"wo",[(w["id"],w["amount"],w["void"]) for w in wos],"pay",[(p["id"],p["amount"],p.get("checknumber"),p.get("origrefnum"),p["void"]) for p in pays])
live=[w for w in wos if w["id"]=="wo"+WOID and w["void"]=="0"]
if live:
    ok,msg=void_tx.void_writeoff(PID,CID,WOID); log["void"]=(ok,msg); print("void",ok,msg)
    if not ok: sys.exit("STOP void fault")
    time.sleep(1)
else: print("write-off already void")
ch,wos,pays=void_tx.charge_state(CID)
print("after void: insbalance",ch.get("insbalance"),"patbalance",ch.get("patbalance"))
if float(ch.get("patbalance") or 0)>0:
    import move_to_ins
    r=move_to_ins.move(CID,1,dry=False,rebill_seq=None); log["move"]=str(r)[:200]; print("move",r)
    ch,wos,pays=void_tx.charge_state(CID); print("after move: insbalance",ch.get("insbalance"),"patbalance",ch.get("patbalance"))
if float(ch.get("insbalance") or 0)<206: sys.exit("STOP insurance balance not restored: %s"%ch.get("insbalance"))
# member id
d=amd.post(amd.msg("getdemographic","demographics",{"patientid":PID,"nocookie":"1"}))
cur=re.search(r'<insplan id="ins%s"[^>]*subscribernum="([^"]*)"'%INS,d).group(1)
if cur==OLDID:
    ok,msg=ins_update.update(PID,INS,subscribernum=NEWID); log["insupdate"]=(ok,msg); print("insupdate",ok,msg)
    if not ok: sys.exit("STOP insupdate fault")
else: print("plan member id already",cur)
d=amd.post(amd.msg("getdemographic","demographics",{"patientid":PID,"nocookie":"1"}))
print("readback member id:",re.search(r'<insplan id="ins%s"[^>]*subscribernum="([^"]*)"'%INS,d).group(1))
# frequency 7 + rebill
vis,pat,allc=resave.visit_charges(CID); e=vis.find("extins"); base=dict(e.attrib) if e is not None else {}; base.pop("id",None)
base.update({"resubmissioncode":"7","origrefnum":ICN})
for k,val in {"patsignature":"1","emergency":"0","epsdt":"0","payprov":"1","employment":"0","autoaccident":"0","otheraccident":"0","pregnant":"0","outsidelab":"0"}.items(): base.setdefault(k,val)
base=resave.clean_extins(base)
for pc in sorted({c.get("proccode") for c in allc}):
    base["txtChargeCode"]=pc
    r=amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":VID,"nocookie":"1"},"<extins %s/>"%" ".join('%s="%s"'%(k,v) for k,v in base.items())))
    if "Fault" in r: sys.exit("STOP extins fault "+r[:300])
    print("extins ok",pc,re.sub(r"\s+"," ",r)[100:220])
time.sleep(0.5)
code,_=amd.rebill_charge(CID,1); log["rebill"]=code; print("chargerebill seq 1 ->",code)
x=resave.detail(CID); ex=re.search(r'<extins [^>]*>',x); exa=dict(re.findall(r'(\w+)="([^"]*)"',ex.group(0))) if ex else {}
ch=dict(re.findall(r'(\w+)="([^"]*)"',re.search(r'<charge [^>]*>',x).group(0)))
print("readback: resub",exa.get("resubmissioncode"),"origref",exa.get("origrefnum"),"insbilled",ch.get("insbilled"),"insbalance",ch.get("insbalance"))
log["readback"]={"resub":exa.get("resubmissioncode"),"origref":exa.get("origrefnum"),"insbilled":ch.get("insbilled"),"insbalance":ch.get("insbalance")}
json.dump(log,open("registers/clack_fix_2026-09-15T0710Z.json","w"),indent=1,default=str)
