# PLAIN ENGLISH (ALF visits using SNF codes)
# Decides: Nothing - lists unpaid 2025+ charges with 9930x codes at place of service 13 (ALF).
# Rules it uses: Your 9/5 rule: ALF visits use home/residence codes 99341-99350, never SNF codes.
# Never touches: AMD writes - the recode is a separate step.
# ---
"""William 9/5: ALF (POS 13) visits must use home/residence codes 99341-99350, never SNF codes 9930x.
Scan every chart: unpaid 2025+ charges with 9930x -> detail -> POS 13 ? -> list. Output alf_snf_codes.json"""
import amd, txh, resave, json, re, os, time
amd.login_cached()
pids=json.load(open('all_pids.json')); SNF={'99304','99305','99306','99307','99308','99309','99310'}
prog=json.load(open('scan_alf_progress.json')) if os.path.exists('scan_alf_progress.json') else {"done":[],"hits":[]}
done=set(prog['done']); hits=prog['hits']
for i,pid in enumerate(pids):
    if pid in done: continue
    try: h=txh.fetch(pid)
    except Exception as e: print(pid,'ERR',str(e)[:60],flush=True); time.sleep(5); continue
    seenv=set()
    for c in h.iter('charge'):
        a=c.attrib
        if a.get('void')=='1' or (a.get('fee') or '').startswith('-') or (a.get('dos') or '')[-4:]<'2025' or a.get('proccode') not in SNF: continue
        if float(a.get('totbal') or 0)<=0 or a.get('visit') in seenv: continue
        seenv.add(a.get('visit'))
        try:
            x=resave.detail(a.get('id')); pos=re.search(r'pos="([^"]*)"', re.search(r'<charge [^>]*>',x).group(0)).group(1)
        except Exception as e: continue
        if pos=='13': hits.append({"pid":pid,"patient":a.get('patient'),"visit":a.get('visit'),"cid":a.get('id'),"dos":a.get('dos'),"cpt":a.get('proccode'),"fee":a.get('fee'),"bal":a.get('totbal'),"carrier":a.get('carrier'),"fac":a.get('facname')})
    done.add(pid)
    if i%25==0: json.dump({"done":sorted(done),"hits":hits},open('scan_alf_progress.json','w')); print(i,len(hits),flush=True)
json.dump({"done":sorted(done),"hits":hits},open('scan_alf_progress.json','w')); json.dump(hits,open('alf_snf_codes.json','w')); print('=== done',len(hits),flush=True)
