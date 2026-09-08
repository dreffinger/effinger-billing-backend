# PLAIN ENGLISH (Fairbank GV pass)
# Decides: Fairbank's hospice rebill done separately after the date filter was added.
# Rules it uses: Same as gv_rebill.
# Never touches: 2023 lines (written off as untimely).
# ---
import txh, gv_rebill, move_to_ins, amd, time, datetime
amd.login_cached()
h=txh.fetch('pat22603'); vis={}
for c in h.iter('charge'):
    if c.get('void')=='1' or (c.get('fee') or '').startswith('-'): continue
    d=datetime.datetime.strptime(c.get('dos'),'%m/%d/%Y').date()
    if d>=datetime.date(2025,9,6) and float(c.get('totbal') or 0)>0 and c.get('visit')!='19451612': vis.setdefault(c.get('visit'),(c.get('id'),c.get('dos')))
print(len(vis),'visits', flush=True)
for v,(cid,dos) in sorted(vis.items(), key=lambda kv: kv[1][1][-4:]+kv[1][1]):
    g=gv_rebill.add_gv(cid); print(v,dos,g,'->', move_to_ins.move(cid,'1,2') if not g.startswith('FAULT') else 'SKIP', flush=True); time.sleep(0.5)
print('=== done', flush=True)
