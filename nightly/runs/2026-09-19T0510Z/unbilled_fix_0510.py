# PLAIN ENGLISH (Unbilled fixes, 1am ET 9/19/2026 run 2026-09-19T0510Z)
# Decides: (1) pat17477777's main referral plan rplan18462071 carries pat17477775's VA auth (a 04:45Z chat-session resave pointed
#   pat17477775's 9/16 + 9/17 visits at it) -> blank that plan's preauth by resaving one of pat17477777's own visits with preauth="".
#   (2) Repoint pat17477775's visits 19454951 + 19455049 to his own plan rplan18462069 with the facesheet auth (12 bytes), hosp 09/14/2026.
#   (3) pat17477779: visits insorder "1,2" (WellCare MA first, Georgia Medicaid second) + the HCA auth from the facesheet on his own plan.
#   (4) pat17477774: MSP code 43 (disabled, large-group plan primary) on the Medicare seq-2 plan, then release visit 19455048 from Unbilled.
#   (5) pat17477773: MSP code 12 (working aged) on the Medicare seq-2 plan (same clearinghouse rule, before the row appears).
#   (6) pat17477798: address line 1 from line 2 (new HCA chart). Every resave = full charge echo (void trap); readback after each write.
# Never touches: balances, other plans, other patients' visits. Auth values come from inbox/facesheets/*.txt (workspace only).
import amd, resave, era_post, ins_update, addr_line1_fix, re, json, time
LOG=open("unbilled_fix_0510.log","a")
def L(m): print(m,flush=True); LOG.write(m+"\n"); LOG.flush()
AUTH_CONWAY="VA0061079015"; AUTH_GORMAN="26244WMC0225"
amd.login_cached(); batch=era_post.batch(); R={}
def save_visit(cid, updates, hosp):
    vis,pat,allc=resave.visit_charges(cid)
    chg=""
    for c in allc:
        a={"id":c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f]=c.get(f)
        chg+="<charge %s/>"%" ".join('%s="%s"'%(k,v) for k,v in a.items())
    va=dict(vis.attrib); va.update({"force":"1","onhcfa":"1"}); va.update(updates)
    vs=" ".join('%s="%s"'%(k,v) for k,v in va.items())
    ex=vis.find("extins"); hosp=hosp or (ex.get("hospitalizationfrom") if ex is not None else None)
    r=amd.post(amd.msg("updvisitwithnewcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1","inspectorenabled":"1","batchid":str(batch),"getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist>%s</visit>"%(vs,chg,resave._extins_xml(vis,hosp))))
    if "Fault" in r: return "FAULT "+re.sub(r"\s+"," ",r[:240]), False
    time.sleep(0.8); v2,p2,c2=resave.visit_charges(cid); ex2=v2.find("extins")
    return "saved live=%d/%d insorder=%s refplan=%s preauth=%s onhcfa=%s hospfrom=%s"%(len(c2),len(allc),v2.get("insorder"),v2.get("refplan"),v2.get("preauth"),v2.get("onhcfa"),ex2.get("hospitalizationfrom") if ex2 is not None else None), len(c2)==len(allc)
def refplans(pid):
    t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
    return [(a.get("id"),a.get("preauth")) for a in (dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<refplan [^>]*>',t))]
def charges(pid):
    tx=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    return [dict(re.findall(r'(\w+)="([^"]*)"',m.group(0))) for m in re.finditer(r'<charge [^>]*/?>',tx)]
# (1) pat17477777 - blank the foreign auth on her plan
L("== (1) pat17477777 rplan18462071 before: %s"%refplans("17477777"))
lz=[c for c in charges("17477777") if c.get("void")=="0"]; L("   charges: %s"%[(c["id"],c["visit"],c["proccode"],c["dos"]) for c in lz])
if lz:
    m,ok=save_visit(lz[0]["id"],{"refplan":"rplan18462071","preauth":""},None); L("   resave v%s: %s"%(lz[0]["visit"],m))
L("   rplan18462071 after: %s"%refplans("17477777")); R["laz"]=refplans("17477777")
# (2) pat17477775 - repoint 9/16 + 9/17 to his own plan with the auth
for vid,cid in (("19454951","23366102"),("19455049","23366201")):
    m,ok=save_visit(cid,{"refplan":"rplan18462069","preauth":AUTH_CONWAY,"insorder":"1"},"09/14/2026"); L("== (2) pat17477775 v%s: %s"%(vid,m)); R["conway_"+vid]=m
L("   pat17477775 refplans: %s | pat17477777 refplans: %s"%(refplans("17477775"),refplans("17477777")))
# (3) pat17477779 - insorder 1,2 + auth on his own plan
for vid,cid in (("19454907","23366058"),("19454927","23366079")):
    m,ok=save_visit(cid,{"refplan":"rplan18462073","preauth":AUTH_GORMAN,"insorder":"1,2"},"09/14/2026"); L("== (3) pat17477779 v%s: %s"%(vid,m)); R["gorman_"+vid]=m
L("   pat17477779 refplans: %s"%refplans("17477779"))
# (4) pat17477774 MSP 43 + release; (5) pat17477773 MSP 12
for pid,ins,code in (("17477774","ins9519462","43"),("17477773","ins9519460","12")):
    ok,msg=ins_update.update(pid,ins,mspcode=code); L("== MSP %s -> %s on %s: %s %s"%(code,ins,pid,ok,msg)); R["msp_"+pid]=(ok,msg)
    t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
    L("   readback mspcode=%s"%(re.search(r'<insplan id="%s"[^>]*mspcode="([^"]*)"'%ins,t) or [None,None])[1] if re.search(r'<insplan id="%s"[^>]*mspcode="([^"]*)"'%ins,t) else "   readback: attr not found")
if R["msp_17477774"][0]:
    r=amd.post(amd.msg("hideunbillablevisits","claimsreports",{"hide":"-1","nocookie":"1"},'<visitlist><visit id="19455048"/></visitlist>')); L("   release 19455048 -> %s"%("ok" if "Fault" not in r else re.sub(r"\s+"," ",r[:200]))); R["release_lisle"]="Fault" not in r
# (6) pat17477798 address line 1
try:
    m,info=addr_line1_fix.fix("17477798","[address]","TALLAHASSEE","FL","32303"); L("== (6) pat17477798 address: %s %s"%(m,json.dumps(info))); R["harwick_addr"]=m
except Exception as e: L("== (6) address error %s"%str(e)[:200])
json.dump(R,open("registers/unbilled_fix_2026-09-19T0510Z.json","w"),indent=1)
