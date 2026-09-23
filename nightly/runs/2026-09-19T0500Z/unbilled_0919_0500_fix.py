# PLAIN ENGLISH (Unbilled pass, chat full run 2026-09-19T0500Z): William answered the board 9/19 ~12:30 AM ET.
# (a) Thurlow/Conway/Gorman/Maskell/Frobisher/Fenner: plans added+verified this run -> dx gate, admission date (99223 anchor),
#     full-visit resave insorder=<seq> onhcfa=1 (+preauth VA0061079015 on Conway), release.
# (b) prior-payor rows: release per the 9/8 standing rule (they re-queue when the primary pays).
# HOLDS: Harwick (nothing found - William facesheet), Lisle MSP, Wexford Bill-Ins=No, 11 payment-reason rows.
import amd, resave, dx_primary_fix, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
S="2026-09-19T0500Z"; dry="--dry" in sys.argv
amd.login_cached()
LOG=open("unbilled_0919_0500_fix.log","a")
def L(m): print(m, flush=True); LOG.write(m+"\n"); LOG.flush()
SC=json.load(open("scan_0912/summary_before.json"))
rows={r["id"]:r for r in SC["unbilled"]}
REG={"stamp":S,"dry":dry,"charts":{},"released":[],"held":[]}
REL=[]
def set_admit(vid, code, admit):
    ext=('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" '
         'employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'%(code,admit))
    r=amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":"vst%s"%vid,"nocookie":"1"},ext))
    return "ok" if "Fault" not in r else "FAULT "+re.sub(r"\s+"," ",r[:160])
def resave_full(cid, insorder=None, onhcfa="1", preauth=None):
    vis,pat,allc=resave.visit_charges(cid); chg=""
    for c in allc:
        a={"id":c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f]=c.get(f)
        chg+="<charge %s/>"%" ".join('%s="%s"'%(k,v) for k,v in a.items())
    va=dict(vis.attrib); va["force"]="1"
    if onhcfa: va["onhcfa"]=onhcfa
    if insorder: va["insorder"]=str(insorder)
    if preauth: va["preauth"]=preauth
    if dry: return "DRY resave insorder %s->%s preauth=%s"%(vis.get("insorder"),va.get("insorder"),preauth)
    r=amd.post(amd.msg("updvisitwithnewcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
               "<visit %s><chargelist>%s</chargelist></visit>"%(" ".join('%s="%s"'%(k,v) for k,v in va.items()),chg)))
    time.sleep(0.6)
    if "Fault" in r: return "FAULT "+re.sub(r"\s+"," ",r[:200])
    v2,p2,c2=resave.visit_charges(cid)
    return "ok insorder=%s onhcfa=%s preauth=%s live %d"%(v2.get("insorder"),v2.get("onhcfa"),v2.get("preauth"),len(c2))
def dx_gate(cid):
    vis,pat,allc,m=dx_primary_fix.visit_dx(cid)
    inv={v:k for k,v in m.items()}; inv.setdefault("I10",dx_primary_fix.I10_DCODE)
    new={}; notes=[]
    for c in allc:
        dcodes=(c.get("diagcodes") or "").split(); codes=[m.get(d,d) for d in dcodes]
        act,nc=dx_primary_fix.plan(codes,c.get("proccode"))
        notes.append("%s %s %s->%s"%(c.get("id"),c.get("proccode"),codes,act))
        if act!="ok": new[c.get("id")]=[inv[x] if x in inv else x for x in nc]
    if not new: return "dx ok: "+"; ".join(notes)
    if dry: return "DRY dx: "+"; ".join(notes)
    msg,det=dx_primary_fix.save_visit_dx(cid,new,dry=False)
    return "DX FIX %s -> %s"%("; ".join(notes),msg)
def seq_of(pid,carrier):
    x=amd.post(amd.msg("getdemographic","demographics",{"patientid":"pat%s"%pid,"nocookie":"1"}),timeout=60)
    for p in ET.fromstring(x).iter("insplan"):
        if p.get("carrier")==carrier and not p.get("enddate"): return p.get("sequence")
    return None
CFG={
 "17477776": {"name":"THURLOW,NERYS L","bill":"car41826","admit":"09/14/2026","preauth":None,
              "visits":["19454904","19454910","19454936","19455052"]},
 "17477775": {"name":"CONWAY,SHELBY DOUGAL","bill":"car42025","admit":"09/14/2026","preauth":"VA0061079015",
              "visits":["19454903","19454916","19454951","19455049"]},
 "17477779": {"name":"GORMAN SR,DAVIN J","bill":"car6174","admit":"09/14/2026","preauth":None,
              "visits":["19454907","19454927"]},
 "17477797": {"name":"MASKELL,KIERAN","bill":"car6404","admit":"09/15/2026","preauth":None,
              "visits":["19455025","19455029","19455046"]},
 "17477799": {"name":"FROBISHER,THURLOW","bill":"car6802","admit":"09/16/2026","preauth":None,
              "visits":["19455032","19455058"]},
 "20379":    {"name":"FENNER,MAUDE","bill":"car6085","admit":"09/16/2026","preauth":None,
              "visits":["19455034"]},
}
INPT=("99221","99222","99223","99231","99232","99233","99238","99239")
for pid,cfg in CFG.items():
    rec={"name":cfg["name"],"visits":{}}
    seq=seq_of(pid,cfg["bill"])
    L("--- %s pat%s bill %s seq %s ---"%(cfg["name"],pid,cfg["bill"],seq))
    if not seq: L("  NO open plan -> HOLD"); REG["held"]+=cfg["visits"]; REG["charts"][pid]=rec; continue
    for vid in cfg["visits"]:
        r=rows.get(vid)
        if not r: L("  v%s not on snapshot, skip"%vid); continue
        cid=r["_chgs"][0]["id"]; codes=sorted({c["chgcode"] for c in r["_chgs"]}); vr={}
        try: vr["dx"]=dx_gate(cid); L("  v%s %s"%(vid,vr["dx"][:240]))
        except Exception as ex: vr["dx"]="DX ERR "+str(ex)[:150]; L("  v%s dx ERR %s"%(vid,str(ex)[:150]))
        if any(c in INPT for c in codes):
            for code in codes:
                res=set_admit(vid,code,cfg["admit"]) if not dry else "DRY"
                L("  v%s admit %s %s -> %s"%(vid,code,cfg["admit"],res)); vr["admit_%s"%code]=res; time.sleep(0.3)
        vr["resave"]=resave_full(cid,insorder=seq,preauth=cfg["preauth"]); L("  v%s resave -> %s"%(vid,vr["resave"]))
        if vr["resave"].startswith(("ok","DRY")): REL.append(vid)
        rec["visits"][vid]=vr; time.sleep(0.4)
    REG["charts"][pid]=rec
# (b) prior-payor
pp=[r["id"] for r in SC["unbilled"] if r["_errs"][0].startswith("A payment from the prior payor")]
L("--- prior-payor rows to release: %d ---"%len(pp)); REL+=pp
# holds
REG["held"]+= [r["id"] for r in SC["unbilled"] if r["patientid"]=="17477798"] + ["19455048","19375395"] + [r["id"] for r in SC["unbilled"] if r["_errs"][0].startswith("Payment reason codes")]
REL=list(dict.fromkeys(REL))
L("release %d visits (held %d)"%(len(REL),len(set(REG["held"]))))
if REL and not dry:
    for i in range(0,len(REL),40):
        chunk=REL[i:i+40]
        r=amd.post(amd.msg("hideunbillablevisits","claimsreports",{"hide":"-1","nocookie":"1"},"<visitlist>%s</visitlist>"%"".join('<visit id="%s"/>'%v for v in chunk)),timeout=120)
        ok="Fault" not in r; L("  hide %d -> %s"%(len(chunk),"ok" if ok else "FAULT "+re.sub(r"\s+"," ",r[:200])))
        REG["released"].append({"visits":chunk,"ok":ok}); time.sleep(0.5)
    t=amd.post(amd.msg("getclaimunbillablecharges","claimsreports",{"lowdate":"","highdate":"","carrier":"","provider":"","nocookie":"1"}),timeout=180)
    m=re.search(r'totalcount="([^"]*)"',t); L("Unbilled after: totalcount=%s"%(m.group(1) if m else "?"))
json.dump(REG,open("registers/unbilled_fix_%s%s.json"%(S,"_dry" if dry else ""),"w"),indent=1)
L("DONE")
