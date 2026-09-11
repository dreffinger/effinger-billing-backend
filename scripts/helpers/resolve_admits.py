# PLAIN ENGLISH (Work out admission dates)
# Decides: Nothing - builds the mapping of subsequent-care visits to their admitting 99223 date.
# Rules it uses: Most recent 99223 on or before the DOS.
# Never touches: AMD - read-only.
# ---
"""Resolve hospital admission dates for inspector records using gettxhistory.
Admission date for a subsequent-care charge = DOS of the MOST RECENT 99223
(initial hospital care) on or before that charge's DOS (William's rule 9/1).
Read-only: builds a mapping, mutates nothing."""
import amd, json, re, time
import xml.etree.ElementTree as ET
from datetime import datetime

def hist(pid):
    body = amd.msg('gettxhistory','demographics',{
      'patientid':str(pid),'filterhistory':'0','pagenumber':'1','typefilter':'1',
      'sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0',
      'profileid':'','getmemo':'false','nocookie':'1'})
    return amd.post(body)

def parse_charges(xml):
    root = ET.fromstring(xml)
    out=[]
    for c in root.findall('.//charge'):
        out.append({'proccode':c.get('proccode'),'dos':c.get('dos'),
                    'visit':c.get('visit'),'pos':c.get('pos'),
                    'desc':c.get('description'),'id':c.get('id')})
    return out

def d(s):
    return datetime.strptime(s,'%m/%d/%Y') if s else None

cats=json.load(open('inspector_cats.json'))
recs=cats['inpatient']+cats.get('posflag',[])
pids=sorted(set(r['pid'] for r in recs))
print('unique patients:',len(pids))

hists={}
for pid in pids:
    try:
        x=hist(pid); hists[pid]=parse_charges(x)
        n99223=[c for c in hists[pid] if c['proccode']=='99223']
        print(pid, 'charges',len(hists[pid]), '99223s:', [c['dos'] for c in n99223])
    except Exception as e:
        print(pid,'ERR',e); hists[pid]=[]
    time.sleep(0.5)

json.dump(hists, open('patient_histories.json','w'), indent=1)

# resolve admission per record
resolved=[]
for r in recs:
    pid=r['pid']; visdos=d(r['dos'])
    admits=[c['dos'] for c in hists.get(pid,[]) if c['proccode']=='99223' and d(c['dos']) and d(c['dos'])<=visdos]
    admit=max(admits, key=d) if admits else None
    resolved.append({**r, 'admit_date':admit,
                     'all_99223':[c['dos'] for c in hists.get(pid,[]) if c['proccode']=='99223']})
json.dump(resolved, open('inspector_admits.json','w'), indent=1)
print('\n=== RESOLVED ===')
for r in resolved:
    print('%-22s DOS %s  code %s  -> admit %s' % (r['name'], r['dos'], r['code'], r['admit_date'] or 'NONE'))
