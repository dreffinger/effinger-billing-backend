import json, re, time, os, sys, amd, resave
import xml.etree.ElementTree as ET
import fix_referring_provider as frp
W="/home/claude/unbilled"; tgt=json.load(open(f"{W}/medicaid_garcia_targets_2026-09-22.json"))
DONE=f"{W}/verify_done.json"; done=set(json.load(open(DONE))) if os.path.exists(DONE) else set()
LOG=open(f"{W}/verify_recreated_2026-09-22.log","a")
def L(m): print(m,flush=True); LOG.write(m+"\n"); LOG.flush()
t0=time.time(); st={"visits":0,"ok":0,"repointed":0,"queued":0,"rebilled":0,"bad_profile":0}
for pid in tgt:
    if pid in done: continue
    if time.time()-t0>240: break
    ref,ins=frp.plans(pid); byid={p["id"]:p for p in ref}; eff=[p for p in ref if p.get("refprov")=="rprov13"]
    if not eff: L(f"pat{pid}: no rprov13 plan on chart - skip"); done.add(pid); continue
    main=[p for p in eff if p.get("ismain")=="1"]; newplan=(main or eff)[0]["id"]
    rec={}
    for page in range(1,6):
        th=ET.fromstring(amd.post(amd.msg('gettxhistory','demographics',{'patientid':pid,'filterhistory':'0','pagenumber':str(page),'typefilter':'0','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','profileid':'','getmemo':'false','nocookie':'1'}),timeout=120))
        chs=list(th.iter("charge"))
        for c in chs:
            ct=c.get("createtime") or ""
            if c.get("void")=="1" or not (ct.startswith("2026-09-21") or ct.startswith("2026-09-22")) or float(c.get("insbal") or 0)<=0.005: continue
            rec.setdefault(c.get("visit"),[]).append(c)
        if len(chs)<100: break
    for vid,cs in rec.items():
        st["visits"]+=1; cid0=re.sub(r"\D","",cs[0].get("id"))
        d=ET.fromstring(resave.detail(cid0)); v=d.find(".//visit")
        prof=v.get("profile"); rp=v.get("refplan"); rprov=byid.get(rp,{}).get("refprov")
        if prof!="prof13": st["bad_profile"]+=1; L(f"  v{vid}: profile {prof} ** not prof13 **")
        if rprov=="rprov13": st["ok"]+=1
        else:
            vv,pat,allc=resave.visit_charges(cid0); pre=len(allc); chg=""
            for c in allc:
                at={"id":c.get("id")}
                for fld in resave.CHG_FIELDS:
                    if c.get(fld) is not None: at[fld]=c.get(fld)
                chg+="<charge %s/>"%" ".join('%s="%s"'%(k,val) for k,val in at.items())
            va=f'id="{vv.get("id")}" date="{vv.get("date")}" profile="{vv.get("profile")}" insorder="{vv.get("insorder")}" refplan="{newplan}" facility="{vv.get("facility")}" force="1"'
            rr=amd.post(amd.msg("updvisitwithnewcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vv.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},f"<visit {va}><chargelist>{chg}</chargelist></visit>"))
            time.sleep(0.4); _,_,post=resave.visit_charges(cid0); d2=ET.fromstring(resave.detail(cid0)); v2=d2.find(".//visit")
            if "Fault" not in rr and v2 is not None and v2.get("refplan")==newplan and len(post)==pre: st["repointed"]+=1; L(f"  v{vid}: refplan {rp}({rprov}) -> {newplan} (rprov13) charges {pre}->{len(post)} OK")
            else: L(f"  v{vid}: ** CHECK ** repoint {rp}->{newplan} charges {pre}->{len(post)}")
        # queue state: a recreated charge starts insbilled=0 (queued); if it was already billed once, make sure it is freq-1 + rebilled
        for c in cs:
            cid=re.sub(r"\D","",c.get("id")); dd=ET.fromstring(resave.detail(cid)); cc=[x for x in dd.iter("charge") if x.get("id")=="charge"+cid][0]
            if cc.get("insbilled")=="0": st["queued"]+=1
            else:
                io=(v.get("insorder") or "").split(","); lb=(cc.get("lastbilledcarrier") or "").strip(); seq=lb if lb in io else (io[0] if io else None)
                if seq:
                    amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":vid,"nocookie":"1"},f'<extins txtChargeCode="{cc.get("proccode")}" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'))
                    code,_=amd.rebill_charge(cid,seq); st["rebilled"]+=(code==204)
            time.sleep(0.15)
    done.add(pid); json.dump(sorted(done),open(DONE,"w"))
L(f"verify: recreated visits {st['visits']} | referring already Effinger {st['ok']} | repointed {st['repointed']} | wrong profile {st['bad_profile']} | charges queued {st['queued']} | re-queued {st['rebilled']} | charts {len(done)}/{len(tgt)}")
