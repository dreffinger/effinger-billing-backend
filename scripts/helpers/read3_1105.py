import amd, json, txh, payreasons, elig_amd
import xml.etree.ElementTree as ET
ex={'17473460':['19435211','19437717','19438563','19439250','19439270','19439707','19439789','19439810','19439883','19441643','19444332','19447394'],
    '17473245':['19445000','19445474','19446131','19446222','19447311','19449458'],'25710':['19432731'],'24750':['19455937']}
out={}
for pid,vids in ex.items():
    root=txh.fetch(pid)
    for vid in vids:
        st=payreasons.visit_state(pid,vid,root)
        if not st:
            st=payreasons.visit_state(pid,vid,txh.fetch_visit(pid,vid))
        out[vid]=st
        for c in st:
            print(pid,vid,c['cid'],c['cpt'],c['dos'],'fee',c['fee'],'paid',c['paid'],'ins',c['insbalance'],'pat',c['patbalance'],'carrier',c['carrier'],'pays',[(p['amount'],p['carrier'],p['date'],p['checkno'],p['void'],p['reasons']) for p in c['pays']],'wos',[(w['amount'],w['code'],w['date']) for w in c['wos']])
    try:
        print(pid,'PLANS',elig_amd.plans(pid))
    except Exception as e: print('plans err',e)
json.dump(out,open('scan_2026-11-05T0639Z/excl_state.json','w'),indent=1)
# Berger + Dorrington
for pid in ('23069','22322'):
    try: print(pid,'PLANS',elig_amd.plans(pid))
    except Exception as e: print('plans err',e)
    root=txh.fetch(pid)
    n=0
    for c in root.iter('charge'):
        a=c.attrib
        if a.get('void')=='1': continue
        n+=1
        if n<=12: print(pid,'CHG',a.get('id'),a.get('dos'),a.get('proccode'),a.get('carrier'),'fee',a.get('fee'),'ins',a.get('insbal'),'pat',a.get('patbal'),'bill',a.get('billdate'),'visit',a.get('visit'))
    print(pid,'charges',n)
# ERA
r=amd.rest_get('/api/era/checks')
try:
    j=json.loads(r) if isinstance(r,str) else r
except Exception: j=r
items=j if isinstance(j,list) else (j.get('items') or j.get('checks') or j)
print('ERA unposted:', len(items) if hasattr(items,'__len__') else items)
if isinstance(items,list):
    for c in items[:30]: print('  ',{k:c.get(k) for k in ('id','checkid','checknumber','payername','payer','checkamount','amount','checkdate','claimcount')})
    json.dump(items,open('scan_2026-11-05T0639Z/era_before.json','w'),indent=1)
