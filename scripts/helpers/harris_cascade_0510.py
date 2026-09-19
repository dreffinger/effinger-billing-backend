# PLAIN ENGLISH (1am ET 9/19 run): insurance cascade for the new HCA chart pat17477798 (Unbilled 'Insurance order is missing'):
# Stedi MBI lookup with the chart SSN (read in-script, never printed) then without, Stedi discovery. Saves under patient_db/. Never touches: AMD writes.
import amd, stedi, re, json, os
pid="17477798"; amd.login_cached()
t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
pat=dict(re.findall(r'(\w+)="([^"]*)"',re.search(r'<patient [^>]*>',t).group(0)))
name=pat.get("name",""); last,first=(name.split(",")+[""])[:2]; first=first.split()[0] if first else ""
dob=pat.get("dob",""); m,d,y=dob.split("/"); dob8=y+m+d
ssn=re.sub(r"\D","",pat.get("ssn") or "")
os.makedirs("patient_db/%s"%pid,exist_ok=True); res={}
def show(tag,j):
    s=json.dumps(j)[:1500]; res[tag]=j; print(tag, s.replace(ssn,"SSN") if ssn else s)
try:
    j=stedi.mbi(first,last,dob8,"FL","20260916",ssn or None); show("mbi_ssn",stedi.med_summ(j) if isinstance(j,dict) else j)
except Exception as e: print("mbi_ssn err",str(e)[:200])
try:
    j2=stedi.mbi(first,last,dob8,"FL","20260916"); show("mbi_nossn",stedi.med_summ(j2) if isinstance(j2,dict) else j2)
except Exception as e: print("mbi_nossn err",str(e)[:200])
try:
    j3=stedi.disc(first,last,dob8,"FL","20260916"); show("disc",stedi.disc_summ(j3) if isinstance(j3,dict) else j3)
except Exception as e: print("disc err",str(e)[:200])
json.dump(res,open("patient_db/%s/cascade_2026-09-19T0510Z.json"%pid,"w"),indent=1,default=str)
