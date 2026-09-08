# PLAIN ENGLISH (Hospice GV rebill)
# Decides: For a patient's visits Medicare denied as hospice (COB9): undo the $0 posting, add GV, re-send to Medicare.
# Rules it uses: Hospice = straight Medicare + GV, except when hospice was revoked. Only the last 364 days (the Fanguy lesson).
# Never touches: Visits before the window.
# ---
"""Hospice fix (William's rule: hospice -> straight Medicare + GV).  For each of a patient's visits that Medicare denied
COB9 ($0 pay, written off): void the $0 pay + WOINS write-off, add GV (mcode713) to every live charge on the visit
(full visit echo via resave.visit_charges - never single-charge), reset freq 1, rebill to the Medicare sequence.
Usage: gv_rebill.py <pid> <medicare seq> [--dry]"""
import amd, txh, resave, void_tx, move_to_ins, re, sys, time, datetime
import xml.etree.ElementTree as ET
GV="mcode713"
def add_gv(cid):
    vis, pat, allc = resave.visit_charges(cid)
    chg=""; changed=[]
    for c in allc:
        a={"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f]=c.get(f)
        mods=(a.get("modcodes") or "").split()
        if GV not in mods: mods.append(GV); changed.append(c.get("id"))
        a["modcodes"]=" ".join(mods)
        chg+="<charge %s/>" % " ".join('%s="%s"' % (k,v) for k,v in a.items())
    va=dict(vis.attrib); va["force"]="1"
    r=amd.post(amd.msg("updvisitwithcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"'%(k,v) for k,v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r: return "FAULT "+re.sub(r"\s+"," ",r[:200])
    v2,p2,c2=resave.visit_charges(cid)
    return "GV on %d/%d charges (%d live)" % (sum(1 for c in c2 if GV in (c.get("modcodes") or "")), len(c2), len(c2)) + ("" if len(c2)==len(allc) else " !!CHARGE COUNT CHANGED %d->%d" % (len(allc),len(c2)))
def run(pid, seq, dry=False, codes=("COB9","PRB9"), since=datetime.date.today()-datetime.timedelta(days=364)):
    amd.login_cached(); pid=str(pid).replace("pat","")
    h=txh.fetch("pat"+pid); visits={}; out=[]
    for c in h.iter("charge"):
        if c.get("void")=="1" or (c.get("fee") or "").startswith("-") or not c.get("dos"): continue
        if datetime.datetime.strptime(c.get("dos"),"%m/%d/%Y").date()<since: continue
        for p in c.iter("payment"):
            if p.get("void")!="1" and float(p.get("amount") or 0)==0 and any(r.get("code") in codes for r in p.iter("payreason")):
                if dry: out.append("DRY %s %s %s" % (c.get("visit"), c.get("dos"), c.get("proccode"))); continue
                void_tx.void_payment(pid, c.get("id"), p.get("id")); time.sleep(0.4)
                st=void_tx.charge_state(c.get("id"))
                for wo in st[1]:
                    if wo.get("void")!="1" and wo.get("Writeoffcode")=="WOINS": void_tx.void_writeoff(pid, c.get("id"), wo["id"]); time.sleep(0.4)
                st=void_tx.charge_state(c.get("id")); out.append("%s %s %s reversed, insbal %s" % (c.get("visit"), c.get("dos"), c.get("proccode"), st[0].get("insbalance")))
                visits[c.get("visit")]=c.get("id")
    for v,cid in visits.items():
        g=add_gv(cid); out.append("%s %s -> %s" % (v, g, move_to_ins.move(cid, seq) if not g.startswith("FAULT") else "SKIP rebill")); time.sleep(0.5)
    return out
if __name__=="__main__":
    for l in run(sys.argv[1], sys.argv[2], "--dry" in sys.argv): print(l, flush=True)
