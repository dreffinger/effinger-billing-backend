# PLAIN ENGLISH (Medicaid payment scan)
# Decides: Nothing - lists what Medicaid paid vs denied.
# Rules it uses: Read-only.
# Never touches: AMD writes.
# ---
import amd, json, time, random, sys
import xml.etree.ElementTree as ET
u=json.load(open('unpaid_20260902b.json'))
done=json.load(open('mcad_patient_payments.json'))
pids=sorted({r['patientid'] for r in u} - {int(k) for k in done})
random.seed(7); random.shuffle(pids)
N=int(sys.argv[1]) if len(sys.argv)>1 else 200
for i,pid in enumerate(pids[:N]):
    body = amd.msg('gettxhistory','demographics',{'patientid':str(pid),'filterhistory':'0','pagenumber':'1','typefilter':'0','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','profileid':'','getmemo':'false','nocookie':'1'})
    try:
        r=amd.post(body,timeout=90); root=ET.fromstring(r)
        done[str(pid)]=[p.attrib for p in root.iter('payment')]
    except Exception as e:
        print(pid,'ERR',e, flush=True); time.sleep(10)
    if i%25==0:
        json.dump(done,open('mcad_patient_payments.json','w')); print('progress',i, flush=True)
    time.sleep(1.2)
json.dump(done,open('mcad_patient_payments.json','w')); print('done',len(done))
