# PLAIN ENGLISH (Railroad Medicare re-route, 11/5/2026 run): Medicare answered CO-109 + N105 (RRB beneficiary) on ERA 1053426 for
# two charts; the CMS 271 (Stedi) confirms 'Railroad Retirement Medicare Beneficiary'. Recipe = captured_calls.md 9/23 (pat12182505):
# add RET01 car6080 with the same MBI, end-date FLO02 the day before the first denied DOS, patient order RET01 first, then ONE
# frequency-1 re-route per open visit (freq1_visit.reroute). Register registers/railroad_reroute_<stamp>.json.
import add_ins, ins_update, freq1_visit, amd, json, time, sys
STAMP="2026-11-05T0639Z"; LIVE="--live" in sys.argv
charts={
 '17473431': dict(mbi='[MBI]', flo02=['ins9514885','ins9521007'], enddate='04/20/2026', keep_seq='2',
    visits=[('19439780','23347424'),('19439520','23346997'),('19442341','23350383'),('19448374','23357675'),('19449003','23358564'),('19448819','23358243'),('19452578','23362890'),('19455615','23366963'),('19457097','23368919'),('19458943','23371215')]),
 '17472491': dict(mbi='[MBI]', flo02=['ins9511956'], enddate='09/17/2026', keep_seq='2',
    visits=[('19455917','23367386'),('19455836','23367298'),('19458782','23371002'),('19459023','23371373'),('19460032','23372657')]),
}
reg={'stamp':STAMP,'live':LIVE,'charts':{}}
amd.login_cached()
for pid,c in charts.items():
    rec={'steps':[],'visits':{}}
    if LIVE:
        insid,seq=add_ins.add(pid,'car6080',c['mbi'],'01/01/2026','1','MC')
        rec['steps'].append(('add RET01',insid,seq)); print(pid,'add RET01 ->',insid,seq)
        if not insid or not str(insid).startswith('ins'):
            print(pid,'ADD FAILED - stop this chart'); reg['charts'][pid]=rec; continue
        for f in c['flo02']:
            ok,msg=ins_update.update(pid,f,enddate=c['enddate']); rec['steps'].append(('enddate',f,ok,msg[:200])); print(pid,'enddate',f,ok,msg[:160]); time.sleep(0.5)
        order="%s,%s"%(seq,c['keep_seq'])
        ok,msg=ins_update.update(pid,insid,sequence=order); rec['steps'].append(('order',order,ok,msg[:200])); print(pid,'order',order,ok,msg[:160])
        a,pl=__import__('elig_amd').plans(pid); print(pid,'insorder now',a.get('insorder'))
        rec['insorder']=a.get('insorder')
    else:
        seq='N'; order='N,%s'%c['keep_seq']; print(pid,'DRY: add RET01, enddate',c['flo02'],c['enddate'],'order',order)
    for vid,cid in c['visits']:
        try:
            r=freq1_visit.reroute(vid,cid,order,seq,dry=not LIVE)
        except Exception as e: r='EXC '+str(e)[:200]
        rec['visits'][vid]=r; print(' ',pid,vid,cid,'->',r[:220]); time.sleep(0.4)
    reg['charts'][pid]=rec
json.dump(reg,open('registers/railroad_reroute_%s%s.json'%(STAMP,'' if LIVE else '_dry'),'w'),indent=1)
print('register written')
