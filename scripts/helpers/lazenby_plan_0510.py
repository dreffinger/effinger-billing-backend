# PLAIN ENGLISH (1am ET 9/19 run): pat17477777's MAIN referral plan rplan18462071 carries another patient's VA auth (written by a
# 04:45Z chat-session resave that pointed pat17477775's visits at it); a resave with preauth="" does not blank it (proven 05:40Z).
# Captured way out: addreferralplan (blank plan, ismain=0) for pat17477777, then repoint her two visits to it with a full-charge
# resave that sends NO preauth attr - her Florida Blue claims then print no auth. The stale main plan is left for William's UI clear.
# Never touches: other patients, balances.
import amd, resave, era_post, re, time, json
amd.login_cached(); batch=era_post.batch(); LOG=open("lazenby_plan_0510.log","a")
def L(m): print(m,flush=True); LOG.write(m+"\n"); LOG.flush()
r=amd.post(amd.msg("addreferralplan","chargeentry",{"nocookie":"1"},'<refplan id="" patient="pat17477777" ismain="0" status="stat1" preauthreq="0" sequence="2" refprov="rprov13" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility=""/>'))
L("addreferralplan -> "+re.sub(r"\s+"," ",r[:300]))
m=re.search(r'id="(rplan\d+)"',r); new=m.group(1) if m else None
if not new or new=="rplan18462071": L("no new plan id - stop"); raise SystemExit
def refplans(pid):
    t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
    return [(a.get("id"),a.get("ismain"),a.get("preauth")) for a in (dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<refplan [^>]*>',t))]
L("plans now: %s"%refplans("17477777"))
out={"newplan":new}
for vid,cid in (("19454905","23366056"),("19454919","23366071")):
    vis,pat,allc=resave.visit_charges(cid); chg=""
    for c in allc:
        a={"id":c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f]=c.get(f)
        chg+="<charge %s/>"%" ".join('%s="%s"'%(k,v) for k,v in a.items())
    va=dict(vis.attrib); va.pop("preauth",None); va.update({"force":"1","onhcfa":"1","refplan":new})
    ex=vis.find("extins"); hosp=ex.get("hospitalizationfrom") if ex is not None else "09/14/2026"
    rr=amd.post(amd.msg("updvisitwithnewcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1","inspectorenabled":"1","batchid":str(batch),"getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist>%s</visit>"%(" ".join('%s="%s"'%(k,v) for k,v in va.items()),chg,resave._extins_xml(vis,hosp))))
    if "Fault" in rr: L("v%s FAULT %s"%(vid,re.sub(r"\s+"," ",rr[:200]))); continue
    time.sleep(0.8); v2,p2,c2=resave.visit_charges(cid); ex2=v2.find("extins")
    L("v%s saved live=%d/%d insorder=%s refplan=%s onhcfa=%s hospfrom=%s"%(vid,len(c2),len(allc),v2.get("insorder"),v2.get("refplan"),v2.get("onhcfa"),ex2.get("hospitalizationfrom") if ex2 is not None else None)); out[vid]=v2.get("refplan")
L("plans after: %s"%refplans("17477777")); out["plans_after"]=refplans("17477777")
json.dump(out,open("registers/lazenby_plan_2026-09-19T0510Z.json","w"),indent=1)
