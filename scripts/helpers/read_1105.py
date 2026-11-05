import amd, json, re, sys
import xml.etree.ElementTree as ET
out={}
# exclusion visits
ex={'17473460':['19435211','19437717','19438563','19439250','19439270','19439707','19439789','19439810','19439883','19441643','19444332','19447394'],
    '17473245':['19445000','19445474','19446131','19446222','19447311','19449458'],'25710':['19432731'],'24750':['19455937']}
import txh
for pid,vids in ex.items():
    r=amd.call({'class':'demographics','action':'gettxhistory','patientid':pid,'filterhistory':'0','pagenumber':'1','typefilter':'1','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','getmemo':'false'})
    root=ET.fromstring(r.encode('latin-1','ignore')) if isinstance(r,str) else ET.fromstring(r)
    rows=[]
    for c in root.iter('charge'):
        a=c.attrib
        if a.get('visit') in vids or a.get('visitid') in vids:
            pays=[(p.attrib.get('amount'),p.attrib.get('carrier'),p.attrib.get('date'),p.attrib.get('checknumber'),p.attrib.get('void')) for p in c.iter('payment')]
            rows.append({k:a.get(k) for k in ('id','visit','proccode','dos','billdate','carrier','insbal','patbal','paid','fee','insbilled','mods','payerinfo')}|{'pays':pays})
    out[pid]=rows
    print(pid, len(rows))
    for x in rows: print('  ',x)
# demographics insplans for the 3 BCBS charts
for pid in ('17473460','17473245','25710'):
    r=amd.call({'class':'demographics','action':'getdemographic','patientid':pid})
    root=ET.fromstring(r.encode('latin-1','ignore')) if isinstance(r,str) else ET.fromstring(r)
    p=root.find('.//patient'); print(pid,'insorder',p.attrib.get('insorder') if p is not None else None)
    for ip in root.iter('insplan'): print('   ',{k:ip.attrib.get(k) for k in ('id','carrier','carriername','sequence','subscribernum','begindate','enddate','coverage')})
json.dump(out,open('scan_2026-11-05T0639Z/excl_txh.json','w'),indent=1,default=str)
