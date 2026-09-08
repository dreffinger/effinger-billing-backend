# PLAIN ENGLISH (Swap a diagnosis or procedure)
# Decides: Nothing on its own: replaces one diagnosis or procedure code on every live charge of a visit, resets frequency, rebills.
# Rules it uses: Full-visit echo.
# Never touches: Paid visits.
# ---
"""Swap a diagnosis or procedure on every live charge of a visit (full-visit echo), freq-1, rebill.
recode.swap_dx(cid, old_dcode, new_dcode, seq) / recode.swap_proc(cid, {old_pcode:new_pcode}, seq)"""
import amd, resave, re, time, freq1_visit
def _save(cid, edit):
    vis, pat, allc = resave.visit_charges(cid); chg=""; changed=0
    for c in allc:
        a={"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f]=c.get(f)
        if edit(a): changed+=1
        chg+="<charge %s/>" % " ".join('%s="%s"'%(k,v) for k,v in a.items())
    va=dict(vis.attrib); va["force"]="1"
    r=amd.post(amd.msg("updvisitwithcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"'%(k,v) for k,v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r: return None, "FAULT "+re.sub(r"\s+"," ",r[:200])
    v2,p2,c2=resave.visit_charges(cid)
    return c2, "%d charges edited; %d live (was %d)" % (changed, len(c2), len(allc))
def swap_dx(cid, old, new, seq):
    def e(a):
        d=(a.get("diagcodes") or "").split()
        if old in d: a["diagcodes"]=" ".join(new if x==old else x for x in d); return True
        return False
    c2,msg=_save(cid,e)
    if c2 is None: return msg
    vid=re.sub(r"\D","",resave.visit_charges(cid)[0].get("id"))
    return msg+" | "+freq1_visit.run(vid, cid, seq)
def swap_proc(cid, mapping, seq):
    def e(a):
        if a.get("proccode") in mapping: a["proccode"]=mapping[a["proccode"]]; return True
        return False
    c2,msg=_save(cid,e)
    if c2 is None: return msg
    vid=re.sub(r"\D","",resave.visit_charges(cid)[0].get("id"))
    return msg+" | "+freq1_visit.run(vid, cid, seq)
