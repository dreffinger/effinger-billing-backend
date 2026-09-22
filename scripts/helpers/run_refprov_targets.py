import json, re, time, os, sys, amd, resave
import xml.etree.ElementTree as ET
import fix_referring_provider as frp
pids=json.load(open("/home/claude/unbilled/sweep_targets_2026-09-22.json"))
DONE="/home/claude/unbilled/refprov_done.json"; done=set(json.load(open(DONE))) if os.path.exists(DONE) else set()
t0=time.time(); charts=0; visits=0; rebills=0; money=0.0; checks=0
for pid in pids:
    if pid in done: continue
    if time.time()-t0>225: break
    ref,ins=frp.plans(pid); mp=[p for p in ref if p.get("ismain")=="1"]
    if not mp or mp[0].get("refprov")!="rprov15": done.add(pid); continue
    mp=mp[0]; vis=frp.open_visits_on_plan(pid, mp["id"])
    r=amd.post(amd.msg("addreferralplan","chargeentry",{"nocookie":"1"},f'<refplan id="" patient="pat{pid}" ismain="1" status="stat1" preauthreq="0" sequence="1" refprov="rprov13" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="{mp.get("facility","")}"/>'))
    m=re.search(r'id="(rplan\d+)"',r); newplan=m.group(1) if m else None
    if not newplan or newplan==mp["id"]: frp.L(f"pat{pid}: no new main plan - skip"); done.add(pid); continue
    frp.L(f"pat{pid}: new main {newplan}; {len(vis)} open prof13 visits"); charts+=1
    for vid,cids in vis.items():
        if time.time()-t0>245: break
        v,pat,allc=resave.visit_charges(cids[0]); pre=len(allc); chg=""
        for c in allc:
            at={"id":c.get("id")}
            for fld in resave.CHG_FIELDS:
                if c.get(fld) is not None: at[fld]=c.get(fld)
            chg+="<charge %s/>"%" ".join('%s="%s"'%(k,val) for k,val in at.items())
        va=f'id="{v.get("id")}" date="{v.get("date")}" profile="{v.get("profile")}" insorder="{v.get("insorder")}" refplan="{newplan}" facility="{v.get("facility")}" force="1"'
        rr=amd.post(amd.msg("updvisitwithnewcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":v.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},f"<visit {va}><chargelist>{chg}</chargelist></visit>"))
        if "Fault" in rr: frp.L(f"  v{vid} FAULT {re.sub(chr(10),' ',rr)[:90]}"); continue
        time.sleep(0.4); _,_,post=resave.visit_charges(cids[0]); d=ET.fromstring(resave.detail(cids[0])); v2=d.find(".//visit")
        ok=v2 is not None and v2.get("refplan")==newplan and len(post)==pre
        if not ok: checks+=1; frp.L(f"  v{vid}: ** CHECK ** refplan {v2.get('refplan') if v2 is not None else '?'} charges {pre}->{len(post)}"); continue
        visits+=1; io=(v2.get("insorder") or "").split(","); ms=frp.medicaid_seq(ins); vseq=ms if ms in io else (io[0] if io else None)
        for c in post:
            b=float(c.get("insbalance") or 0)
            if b<=0.005 or not vseq: continue
            amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":re.sub(r"\D","",v.get("id")),"nocookie":"1"},f'<extins txtChargeCode="{c.get("proccode")}" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'))
            code,_=amd.rebill_charge(c.get("id"),vseq)
            if code==204: rebills+=1; money+=b
            else: frp.L(f"  rebill c{c.get('id')} seq {vseq} http {code}")
            time.sleep(0.25)
    else:
        done.add(pid)
    json.dump(sorted(done),open(DONE,"w"))
frp.L(f"batch: charts {charts} visits repointed {visits} rebilled {rebills} ${money:,.2f} checks {checks} | charts done {len(done)}/{len(pids)}")
print(f"batch: charts {charts} visits {visits} rebills {rebills} ${money:,.2f} checks {checks} | done {len(done)}/{len(pids)}")
