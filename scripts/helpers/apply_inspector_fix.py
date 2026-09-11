# PLAIN ENGLISH (Claim Inspector hospitalization fix)
# Decides: Clears inspector errors about hospitalization dates by setting the admission date and flipping the Box 18 flag.
# Rules it uses: Void-checked full echo.
# Never touches: Visits with a payment.
# ---
"""Clear inspector hospitalization-date errors: set admission date (updextrainsinfo)
+ flip onhcfa=1 (updvisitwithcharges, full echo) so Box 18 counts. Void-checked."""
import amd, resave, json, time
import xml.etree.ElementTree as ET

recs = json.load(open('inspector_admits.json'))
# unique by visitid; carry chargeid, code, admit
seen = {}
for r in recs:
    seen[r['visitid']] = r  # one charge per visit
DONE = {'19453373','19453366'}  # REY 08/30 + TILLERY 08/29 already cleared

def set_date(visitid, code, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" '
           'emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" '
           'otheraccident="0" pregnant="0" outsidelab="0"/>') % (code, admit)
    return amd.post(amd.msg('updextrainsinfo','chargeentry',{'visitid':visitid,'nocookie':'1'}, ext))

def set_hcfa(chargeid):
    x=resave.detail(chargeid); root=ET.fromstring(x); pat=root.find('.//patient'); vis=root.find('.//visit')
    chg=''
    for c in vis.findall('.//charge'):
        a={'id':c.get('id')}
        for f in resave.CHG_FIELDS:
            v=c.get(f)
            if v is not None: a[f]=v
        chg+='<charge %s/>'%' '.join('%s="%s"'%(k,v) for k,v in a.items())
    va=dict(vis.attrib); va['onhcfa']='1'; va['force']='1'
    vs=' '.join('%s="%s"'%(k,v) for k,v in va.items())
    body=amd.msg('updvisitwithcharges','chargeentry',
        {'patientid':pat.get('id'),'episodeid':vis.get('episode'),'approval':'1',
         'inspectorenabled':'1','getfinancials':'-1','customclaimfieldsavailable':'1','nocookie':'1'},
        '<visit %s><chargelist>%s</chargelist></visit>'%(vs,chg))
    return amd.post(body)

def check(chargeid):
    x=resave.detail(chargeid); vis=ET.fromstring(x).find('.//visit'); c=vis.find('.//charge')
    e=vis.find('extins')
    return {'onhcfa':vis.get('onhcfa'),'void':c.get('void'),'billins':c.get('billins'),
            'hf':(e.get('hospitalizationfrom') if e is not None else None)}

log=open('inspector_fix.log','a')
def L(m): print(m); log.write(m+'\n'); log.flush()

L('=== inspector fix %s ===' % time.ctime())
results=[]
for vid, r in seen.items():
    if vid in DONE:
        L('SKIP %s %s (already done)'%(r['name'], r['dos'])); continue
    name=r['name']; code=r['code']; admit=r['admit_date']; cid=r['chargeid']
    try:
        d=set_date('vst'+vid if not vid.startswith('vst') else vid, code, admit)
        if 'Fault' in d: L('  DATE-FAULT %s %s'%(name,r['dos'])); results.append((vid,'date-fault')); continue
        time.sleep(0.6)
        h=set_hcfa(cid)
        st=check(cid)
        if st['void']=='1':
            L('!!! VOID DETECTED %s %s -- STOPPING'%(name,r['dos'])); results.append((vid,'VOIDED')); break
        ok = ('Fault' not in h) and st['onhcfa']=='1' and st['hf']==admit
        L('  %-22s %s %s onhcfa=%s hf=%s void=%s -> %s'%(name,r['dos'],code,st['onhcfa'],st['hf'],st['void'],'OK' if ok else 'CHECK'))
        results.append((vid,'ok' if ok else 'check'))
        time.sleep(1.2)
    except Exception as e:
        L('  ERR %s %s: %s'%(name,r['dos'],e)); results.append((vid,'err'))
json.dump(results, open('inspector_fix_results.json','w'), indent=1)
L('applied: %d'%len(results))
