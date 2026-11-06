import amd, json, re
import xml.etree.ElementTree as ET
def X(r): return ET.fromstring(r.encode('latin-1','ignore')) if isinstance(r,str) else ET.fromstring(r)
# Bergstrom lookup
for nm in ('[name]%','DORRINGTON,[first]%'):
    r=amd.call({'class':'lookup','action':'lookuppatient','name':nm})
    for p in X(r).iter('patient'): print(nm, {k:p.attrib.get(k) for k in ('id','name','chart','dob')})
# inspector visit 19459621 charges
r=amd.call({'class':'demographics','action':'gettxhistory','patientid':'17473749','filterhistory':'0','pagenumber':'1','typefilter':'1','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','getmemo':'false'})
for c in X(r).iter('charge'):
    a=c.attrib
    if a.get('visit')=='19459621': print('insp',{k:a.get(k) for k in ('id','visit','proccode','dos','billdate','carrier','insbal','mods','insbilled')})
