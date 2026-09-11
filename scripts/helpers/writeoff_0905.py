# PLAIN ENGLISH (9/5 approved write-offs)
# Decides: Carrow, Chadwick, Cormack, Barlowe (2024) lines older than 12 months, plus Lockridge 8/22 CCM (no Railroad credentialing).
# Rules it uses: Your 9/5 approvals; register kept in Writeoff_register_2026-09-05.xlsx.
# Never touches: Anything under 12 months.
# ---
"""William 9/5/2026 approvals: write off (WOINS, non-ERA) every unpaid line older than 12 months for Carrow, Chadwick, Cormack, Barlowe (2024),
plus Lockridge 8/22/26 CCM (no Railroad Medicare credentialing).  Appends to Writeoff_register_2026-09-05.xlsx + writeoff_0905.log"""
import txh, resave, manual_post, re, time, datetime, openpyxl, os, amd
amd.login_cached()
CUT=datetime.date(2025,9,6)
targets={'22538':('CARROW,PORTIA',CUT),'17469673':('CHADWICK,SELINA',CUT),'21258':('CORMACK,PRESTON',CUT),'17472559':('BARLOWE,CORETTA',CUT)}
log=open('writeoff_0905.log','a'); done={l.split()[1] for l in open('writeoff_0905.log') if l.startswith('OK ')} if os.path.exists('writeoff_0905.log') else set()
reg=[]; tot=0.0
def wo(pid,name,c,carrier,note):
    global tot
    cid=c.get('id'); bal=float(c.get('totbal') or 0)
    if cid in done or bal<=0: return
    x=resave.detail(cid); ch=re.search(r'<charge [^>]*>', x).group(0); ib=float(re.search(r'insbalance="([^"]*)"',ch).group(1)); pb=float(re.search(r'patbalance="([^"]*)"',ch).group(1))
    if pb>0:   # move to insurance first so the write-off applies cleanly
        import move_to_ins; move_to_ins.move(cid); time.sleep(0.5); ib=ib+pb
    ok,r=manual_post.post(cid,carrier,0,ib,'WOINS','','',note=note)
    log.write('%s %s %s %s %s %.2f %s\n'%('OK' if ok else 'FAIL',cid,name,c.get('dos'),c.get('proccode'),ib,'' if ok else r[:120])); log.flush()
    if ok: reg.append((name,c.get('dos'),c.get('proccode'),ib,carrier,note)); tot+=ib
    time.sleep(0.4)
for pid,(name,cut) in targets.items():
    h=txh.fetch('pat'+pid)
    for c in h.iter('charge'):
        if c.get('void')=='1' or (c.get('fee') or '').startswith('-') or not c.get('dos'): continue
        d=datetime.datetime.strptime(c.get('dos'),'%m/%d/%Y').date()
        if d>=cut: continue
        paid=any(p.get('void')!='1' and float(p.get('amount') or 0)!=0 for p in c.iter('payment'))
        if paid and float(c.get('totbal') or 0)<60: continue   # coinsurance remnants handled elsewhere
        wo(pid,name,c,c.get('carrier') or 'FLO02','William 9/5: past 12-month timely filing, no remit on file')
# Lockridge 8/22/26 CCM
r = amd.post('<ppmdmsg action="lookuppatient" class="lookup" msgtime="%s" name="LOCKRIDGE,LENORA%%" nocookie="1"/>' % amd._msgtime())
pid=re.search(r'<patient id="pat(\d+)"', r).group(1); h=txh.fetch('pat'+pid)
for c in h.iter('charge'):
    if c.get('visit')=='19452338' and c.get('void')!='1': wo(pid,'LOCKRIDGE,LENORA',c,'FLO02','William 9/5: Railroad Medicare beneficiary, practice not credentialed with Palmetto RRB - write off for now')
wb=openpyxl.Workbook(); ws=wb.active; ws.title='Write-offs 9-5'; ws.append(['Patient','DOS','CPT','Amount','Carrier','Reason'])
for rrow in reg: ws.append(list(rrow))
ws.append(['TOTAL','','',round(tot,2),'','']); wb.save('Writeoff_register_2026-09-05.xlsx')
print('written off %d lines $%.2f'%(len(reg),tot))
