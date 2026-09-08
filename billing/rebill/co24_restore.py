# PLAIN ENGLISH (Undo a CO24 posting and rebill the MA plan)
# Decides: For Medicare $0 CO24 postings: void the $0 payment and its write-off, then bill the visit to the Advantage plan.
# Rules it uses: CO24 means an Advantage plan is responsible. Date window optional.
# Never touches: Non-CO24 postings.
# ---
"""Undo ERA-posted Medicare CO24 ($0 pay + WOINS write-off) on a patient's charges and rebill those visits to the MA plan.
Usage: co24_restore.py <pid> <seq> [<first dos mm/dd/yyyy> <last dos>]   (CO24 = Medicare says an Advantage plan is responsible)"""
import txh, void_tx, amd, move_to_ins, time, sys, datetime
def run(pid, seq, first=None, last=None, dry=False, codes=('CO24',)):
    amd.login_cached(); pid=str(pid).replace('pat','')
    h=txh.fetch('pat'+pid); P=lambda s: datetime.datetime.strptime(s,'%m/%d/%Y').date()
    lo=P(first) if first else datetime.date(1900,1,1); hi=P(last) if last else datetime.date(2100,1,1)
    visits={}; out=[]
    for c in h.iter('charge'):
        if c.get('void')=='1' or (c.get('fee') or '').startswith('-') or not c.get('dos'): continue
        d=P(c.get('dos'))
        if d<lo or d>hi: continue
        for p in c.iter('payment'):
            if p.get('void')!='1' and float(p.get('amount') or 0)==0 and any(r.get('code') in codes for r in p.iter('payreason')):
                if dry: out.append("DRY %s %s %s pay %s" % (c.get('visit'), c.get('dos'), c.get('proccode'), p.get('id'))); continue
                ok,_=void_tx.void_payment(pid, c.get('id'), p.get('id')); time.sleep(0.4)
                st=void_tx.charge_state(c.get('id'))
                for wo in st[1]:
                    if wo.get('void')!='1' and wo.get('Writeoffcode')=='WOINS': void_tx.void_writeoff(pid, c.get('id'), wo['id']); time.sleep(0.4)
                st=void_tx.charge_state(c.get('id'))
                out.append("%s %s %s pay-void %s insbal %s" % (c.get('visit'), c.get('dos'), c.get('proccode'), ok, st[0].get('insbalance')))
                visits[c.get('visit')]=c.get('id')
    for v,cid in visits.items():
        out.append("%s -> %s" % (v, move_to_ins.move(cid, seq))); time.sleep(0.5)
    return out
if __name__=='__main__':
    a=sys.argv[1:]; dry='--dry' in a; a=[x for x in a if x!='--dry']
    for l in run(a[0], a[1], a[2] if len(a)>2 else None, a[3] if len(a)>3 else None, dry): print(l, flush=True)
