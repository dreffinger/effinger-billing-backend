# PLAIN ENGLISH (Medicaid/SMMC: Garland-G -> Effinger, rendering AND referring; William 9/22/2026, full set)
# Decides: For every open Medicaid-type claim in the past year where Garland-G is the rendering (prof15) or the chart's referring
#          provider (rprov15): make Effinger both. A = profile swap prof15->prof13 (AMD voids + recreates the charges on a new visit)
#          with refplan set to an rprov13 main plan in the same resave; B = refplan repoint only (no void). Then freq-1 + rebill the
#          live charges on the sequence of the plan that holds the balance. FCC (FLO99) is the SMMC MMA plan for most of its members (271): keep FCC
#          when the patient has car6113 and no active SMMC plan, to the SMMC plan when one exists, else keep FLO99 and flag.
# Rules it uses: void-trap discipline (visit_charges = every active charge, paginated; recreated count must equal the original);
#          settling gate (a visit with a posted non-void payment is never re-rendered); never a UI step; resumable.
import sys, re, json, os, time, datetime
sys.path[:0]=["/home/claude/effinger-billing-backend/core","/home/claude/effinger-billing-backend/billing/rebill"]
import amd, resave
import xml.etree.ElementTree as ET
import fix_referring_provider as frp
W="/home/claude/unbilled"; STAMP=datetime.date.today().isoformat()
TODAYS=(STAMP,(datetime.date.today()-datetime.timedelta(days=1)).isoformat())   # AMD server clock (ET) can be a day behind the container (UTC)
LOGF=open(os.environ.get("LOGF",f"{W}/medicaid_garland_g_fix_{STAMP}.log"),"a")
def L(m): print(m,flush=True); LOGF.write(m+"\n"); LOGF.flush()
CARMAP=json.load(open(f"{W}/carriers_rich.json")); CODE2CAR={v[0]:k for k,v in CARMAP.items()}
SMMC={"car6194","car6174","car42019","car41991","car41992"}; MCAD="car6113"; FCC="car42008"
tgt=json.load(open(os.environ.get("TGT",f"{W}/medicaid_garland_g_targets_2026-09-22.json")))
DONE=os.environ.get("DONEF",f"{W}/medicaid_garland_g_done.json"); done=set(json.load(open(DONE))) if os.path.exists(DONE) else set()
BUDGET=float(sys.argv[1]) if len(sys.argv)>1 else 230
def carseq(ins, carid):
    for p in ins:
        if p.get("carrier")==carid and not p.get("enddate"): return p.get("sequence")
    for p in ins:
        if p.get("carrier")==carid: return p.get("sequence")
def route(ins, holding_code):
    """sequence to bill: the holding carrier's plan, except FLO99 -> MCAD FFS / SMMC plan when on file"""
    hold=CODE2CAR.get(holding_code)
    if hold==FCC:
        # 9/22 CORRECTION: FL Medicaid's 271 lists FCC as "SMMC MMA Capitated" (the medical plan) for 20 of 22 FCC patients,
        # and FFS denies those claims CO256/N130. FCC stays the payer; never reroute FCC balances off FCC from this runner.
        return carseq(ins,FCC), FCC, "FCC kept (SMMC MMA plan)"
    return carseq(ins,hold), hold, ""
def echo(allc):
    chg=""
    for c in allc:
        at={"id":c.get("id")}
        for fld in resave.CHG_FIELDS:
            if c.get(fld) is not None: at[fld]=c.get(fld)
        chg+="<charge %s/>"%" ".join('%s="%s"'%(k,v) for k,v in at.items())
    return chg
def resave_visit(v,pat,chg,profile,refplan,insorder):
    va=f'id="{v.get("id")}" date="{v.get("date")}" profile="{profile}" insorder="{insorder}" refplan="{refplan}" facility="{v.get("facility")}" force="1"'
    return amd.post(amd.msg("updvisitwithnewcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":v.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},f"<visit {va}><chargelist>{chg}</chargelist></visit>"))
CONS=f"{W}/medicaid_garland_g_consumed.json"; consumed=set(json.load(open(CONS))) if os.path.exists(CONS) else set()
def recreated(pid, origvid, sigs, orig_date=None):
    """active charges created today on a NEW visit matching (proc,fee) of the voided originals"""
    found=[]
    for page in range(1,6):
        th=ET.fromstring(amd.post(amd.msg('gettxhistory','demographics',{'patientid':pid,'filterhistory':'0','pagenumber':str(page),'typefilter':'0','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','profileid':'','getmemo':'false','nocookie':'1'}),timeout=120))
        chs=list(th.iter("charge"))
        for c in chs:
            if c.get("void")=="1" or not any((c.get("createtime") or "").startswith(d) for d in TODAYS): continue
            if c.get("visit")==origvid or not (c.get("visit") or "").isdigit() or int(c.get("visit"))<=int(origvid): continue
            found.append(c)
        if len(chs)<100: break
    # group by new visit; pick the visit whose (proc,fee) multiset matches
    byv={}
    for c in found: byv.setdefault(c.get("visit"),[]).append(c)
    want=sorted(str(fee) for _,fee in sigs)        # fee only: detail says pcode65119, history says 99309 (same charge)
    for nv,cs in sorted(byv.items()):
        if nv in consumed or sorted(str(c.get("fee")) for c in cs)!=want: continue
        if orig_date:                                   # and the recreation carries the original DOS
            dd=ET.fromstring(resave.detail(re.sub(r"\D","",cs[0].get("id")))); vv=dd.find(".//visit")
            if vv is None or vv.get("date")!=orig_date: continue
        consumed.add(nv); json.dump(sorted(consumed),open(CONS,"w")); return nv,cs
    return None,[]
def rebill_live(vidn, cids_procs, seq):
    n=0
    for cid,pc in cids_procs:
        amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":vidn,"nocookie":"1"},f'<extins txtChargeCode="{pc}" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'))
        code,_=amd.rebill_charge(cid,seq); n+= (code==204)
        if code!=204: L(f"      rebill c{cid} seq {seq} http {code}")
        time.sleep(0.25)
    return n
t0=time.time(); stats={"A":0,"B":0,"rebilled":0,"money":0.0,"skip_paid":0,"check":0,"fcc_kept":0}
amd.login_cached()
for pid,parts in tgt.items():
    if time.time()-t0>BUDGET: break
    if all((pid+":"+vid) in done for k in ("A","B") for vid in parts[k]): continue
    ref,ins=frp.plans(pid); main=[p for p in ref if p.get("ismain")=="1"]; newplan=None
    if main and main[0].get("refprov")=="rprov13": newplan=main[0]["id"]
    else:
        r=amd.post(amd.msg("addreferralplan","chargeentry",{"nocookie":"1"},f'<refplan id="" patient="pat{pid}" ismain="1" status="stat1" preauthreq="0" sequence="1" refprov="rprov13" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="{(main[0].get("facility","") if main else "")}"/>'))
        m=re.search(r'id="(rplan\d+)"',r); newplan=m.group(1) if m else None
        if not newplan or (main and newplan==main[0]["id"]): L(f"pat{pid}: no rprov13 main plan - skip chart"); continue
        L(f"pat{pid}: new main plan {newplan} (rprov13)")
    for kind in ("A","B"):
        for vid,chs in parts[kind].items():
            key=pid+":"+vid
            if key in done: continue
            if time.time()-t0>BUDGET+20: break
            cid0=chs[0]["cid"]; hold=chs[0]["car"]
            try: v,pat,allc=resave.visit_charges(cid0)
            except Exception as e: L(f"  v{vid}: read fail {str(e)[:60]}"); continue
            if v is None or not allc:
                d0=ET.fromstring(resave.detail(cid0)); c0=[x for x in d0.iter("charge") if x.get("id")=="charge"+cid0]
                if c0 and c0[0].get("void")=="1" and kind=="A":      # swapped earlier, never rebilled: recover
                    sig=[(c0[0].get("proccode"),c0[0].get("fee"))]; extra=[c for c in chs[1:]]
                    for e in extra:
                        dd=ET.fromstring(resave.detail(e["cid"])); cc=[x for x in dd.iter("charge") if x.get("id")=="charge"+e["cid"]]
                        if cc: sig.append((cc[0].get("proccode"),cc[0].get("fee")))
                    seq,carid,note=route(ins,hold); nv,cs=recreated(pid,vid,sig,v.get("date") if v is not None else None)
                    if nv and seq:
                        n=rebill_live(nv,[(re.sub(r"\D","",c.get("id")),c.get("proccode")) for c in cs],seq); stats["A"]+=1; stats["rebilled"]+=n; stats["money"]+=sum(float(c.get("insbal") or 0) for c in cs)
                        L(f"  A(recovered) v{vid}->{nv} rebilled {n}/{len(cs)} seq {seq} {note}"); done.add(key); json.dump(sorted(done),open(DONE,"w")); continue
                    L(f"  v{vid}: ** CHECK ** original void, recreations not found"); stats["check"]+=1; continue
                L(f"  v{vid}: no live charges - skip"); done.add(key); continue
            seq,carid,note=route(ins,hold)
            if not seq: L(f"  v{vid}: no sequence for {hold} - skip"); done.add(key); continue
            insorder=v.get("insorder") or ""
            if seq not in insorder.split(","): insorder=(seq+","+insorder).strip(",")   # make the target plan billable on this visit
            pre=len(allc); sigs=[(c.get("proccode"),c.get("fee")) for c in allc]; pre_bal=sum(float(c.get("insbalance") or 0) for c in allc)
            if kind=="A":
                if v.get("profile")!="prof15": L(f"  v{vid}: profile {v.get('profile')} already - treat as B"); kind_eff="B"
                else: kind_eff="A"
            else: kind_eff="B"
            if kind_eff=="B" and {p["id"]:p for p in ref}.get(v.get("refplan"),{}).get("refprov")=="rprov13":
                L(f"  v{vid}: referring already Effinger (rprov13) - skip"); done.add(key); continue
            if kind_eff=="A":
                paid=False
                for cx in allc:                               # settling gate across EVERY live charge on the visit
                    dx=ET.fromstring(resave.detail(re.sub(r"\D","",cx.get("id"))))
                    if any(float(p.get("amount") or 0)!=0 and p.get("void")!="1" for p in dx.iter("payment")): paid=True; break
                if paid: L(f"  v{vid}: settling (payment posted) - NOT re-rendered"); stats["skip_paid"]+=1; done.add(key); continue
                rr=resave_visit(v,pat,echo(allc),"prof13",newplan,insorder)
                if "Fault" in rr: L(f"  v{vid}: swap FAULT {re.sub(chr(10),' ',rr)[:90]}"); continue
                time.sleep(0.8); nv,cs=recreated(pid,vid,sigs,v.get("date"))
                if not nv or len(cs)!=pre: L(f"  v{vid}: ** CHECK ** recreated {len(cs)}/{pre} on {nv}"); stats["check"]+=1; continue
                n=rebill_live(nv,[(re.sub(r"\D","",c.get("id")),c.get("proccode")) for c in cs],seq)
                stats["A"]+=1; stats["rebilled"]+=n; stats["money"]+=pre_bal
                L(f"  A v{vid}->{nv} prof13 refplan {newplan} {hold} seq {seq} {note} charges {pre}->{len(cs)} rebilled {n}/{len(cs)} ${pre_bal:.2f}")
            else:
                rr=resave_visit(v,pat,echo(allc),v.get("profile"),newplan,insorder)
                if "Fault" in rr: L(f"  v{vid}: repoint FAULT {re.sub(chr(10),' ',rr)[:90]}"); continue
                time.sleep(0.5); _,_,post=resave.visit_charges(cid0); d2=ET.fromstring(resave.detail(cid0)); v2=d2.find(".//visit")
                if v2 is None or v2.get("refplan")!=newplan or len(post)!=pre: L(f"  v{vid}: ** CHECK ** refplan {v2.get('refplan') if v2 is not None else '?'} charges {pre}->{len(post)}"); stats["check"]+=1; continue
                n=rebill_live(re.sub(r"\D","",v.get("id")),[(re.sub(r"\D","",c.get("id")),c.get("proccode")) for c in post if float(c.get("insbalance") or 0)>0.005],seq)
                stats["B"]+=1; stats["rebilled"]+=n; stats["money"]+=pre_bal
                L(f"  B v{vid} refplan {newplan} {hold} seq {seq} {note} charges {pre} rebilled {n} ${pre_bal:.2f}")
            if "FCC(kept" in note: stats["fcc_kept"]+=1
            done.add(key); json.dump(sorted(done),open(DONE,"w"))
            time.sleep(0.3)
tot=sum(len(parts[k]) for parts in tgt.values() for k in ("A","B"))
L(f"batch: A re-rendered {stats['A']} | B repointed {stats['B']} | charges rebilled {stats['rebilled']} ${stats['money']:,.2f} | settling-skipped {stats['skip_paid']} | CHECK {stats['check']} | FCC kept {stats['fcc_kept']} | visits done {len(done)}/{tot}")
