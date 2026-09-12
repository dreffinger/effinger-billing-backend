# 9/10 11:05 UTC run - clear the 4 inspector visits per standing rules
import amd, resave, recode, re, time, sys, json
amd.login_cached()
def L(m): print(m, flush=True)
def listbatch(bid):
    t = amd.post(amd.msg("getclaiminspectorcharges","chargeentry",{"batchid":bid}))
    return t
def errids(t, vid, pattern):
    # errors for visit vid matching pattern number in text
    seg = re.search(r'<visit id="%s".*?</visit>' % vid, t, re.S)
    if not seg: return []
    return [m.group(1) for m in re.finditer(r'<error id="(\d+)"[^>]*>(?:(?!</error>).)*?Pattern %s ' % pattern, seg.group(0), re.S)]
def bypass(vid, ids):
    r = amd.post(amd.msg("bypassclaimedits","chargeentry",{"nocookie":"1"},
        '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
    return "Fault" not in r
def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid":vid,"nocookie":"1"},ext))
def resave_visit(cid, over=None):
    vis, pat, allc = resave.visit_charges(cid); chg=""
    for c in allc:
        a={"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f]=c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"'%(k,v) for k,v in a.items())
    va=dict(vis.attrib); va["force"]="1"
    if over: va.update(over)
    r=amd.post(amd.msg("updvisitwithcharges","chargeentry",{"patientid":pat.get("id"),"episodeid":vis.get("episode"),"approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"'%(k,v) for k,v in va.items()), chg)))
    time.sleep(0.8)
    return "Fault" not in r, r[:200]

# --- 1. ROWANTREE vid 19439544 batch 126725: move Z59.00 behind conditions, then bypass 35790
cid = "23347041"
x = resave.detail(cid)
m = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
z = [k for k,v in m.items() if v=="Z59.00"]
L("Rowantree dcode map: %s" % m)
def e(a):
    d=(a.get("diagcodes") or "").split()
    if z and z[0] in d and d[0]==z[0]:
        a["diagcodes"]=" ".join([q for q in d if q!=z[0]]+[z[0]]); return True
    return False
c2,msg = recode._save(cid, e)
L("Rowantree dx reorder: %s" % msg)
time.sleep(1.5)
t = listbatch("126725")
ids = errids(t,"19439544","35790")
L("Rowantree fresh 35790 ids: %s" % ids)
if ids: L("Rowantree bypass -> %s" % bypass("19439544", ids))
time.sleep(1.0)
t = listbatch("126725")
L("Batch 126725 after: %s" % re.sub(r"\s+"," ", re.sub(r"<charge .*?/>","",t))[:600])

# --- 2. FAIRHOLM vid 19454078 batch 127664: hospitalizationfrom = DOS 09/08/2026 (visit IS the 99223)
r = set_date("19454078","99223","09/08/2026")
L("Fairholm set_date fault=%s" % ("Fault" in r))
x = resave.detail("23365048")
on = re.search(r'onhcfa="([^"]*)"', x)
L("Fairholm onhcfa=%s" % (on.group(1) if on else "?"))
over = {"onhcfa":"1"} if (not on or on.group(1)!="1") else None
ok, r2 = resave_visit("23365048", over)
L("Fairholm resave ok=%s" % ok)
time.sleep(1.5)
t = listbatch("127664")
L("Batch 127664 after: %s" % re.sub(r"\s+"," ", re.sub(r"<charge .*?/>","",t))[:600])

# --- 3/4. TATE vids 19420914 (b125500), 19427593 (b125953): bypass add-on advisory (25 already on 99489)
for bid, vid in (("125500","19420914"),("125953","19427593")):
    t = listbatch(bid)
    ids = errids(t, vid, "35790")
    L("Tate %s fresh 35790 ids: %s" % (vid, ids))
    if ids: L("Tate %s bypass -> %s" % (vid, bypass(vid, ids)))
    time.sleep(1.0)
    t = listbatch(bid)
    L("Batch %s after: %s" % (bid, re.sub(r"\s+"," ", re.sub(r"<charge .*?/>","",t))[:500]))
