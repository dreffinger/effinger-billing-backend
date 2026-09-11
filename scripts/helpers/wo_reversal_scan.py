# PLAIN ENGLISH (Remit vs write-off scan)
# Decides: Nothing - finds ERA Center remits with money for visits whose charges were written off (no payment ever posted), so the write-off can be reversed and the payer's money posted instead.
# Rules it uses: Read-only. A visit qualifies when the remit line pays > 0, the charge has no non-void payment, and it carries a non-void write-off.
# Never touches: AMD writes. Output wo_reversal_<date>.json.
# ---
import era_post, txh, json, collections, datetime, time, sys
import sys
cs=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'era_checks_0906.json'))
todo=[c for c in cs if (c['unpostedamount'] or 0)>0]
out=[]; seen_pat={}; stats=collections.Counter(); wocodes=collections.Counter(); dates=collections.Counter()
for i,c in enumerate(sorted(todo, key=lambda x:-(x['unpostedamount'] or 0))):
    try: det=era_post.details(c['id'])
    except Exception as e: print('ERR',c['id'],e); continue
    for v in det['eracheckdetails']:
        if (v['paymentamount'] or 0)<=0: continue
        pid=v['patientid']
        if pid not in seen_pat:
            try: seen_pat[pid]={ch.get('id'):ch for ch in txh.fetch('pat%s'%pid).iter('charge') if ch.get('void')!='1'}
            except Exception as e: seen_pat[pid]={}
        chs=[ch for ch in seen_pat[pid].values() if ch.get('visit')==str(v['visitid'])]
        if not chs: stats['no-charge']+=1; continue
        paid=any(p.get('void')!='1' and float(p.get('amount') or 0)!=0 for ch in chs for p in ch.iter('payment'))
        wos=[(ch.get('id'),w.get('id'),w.get('wocode'),w.get('amount'),w.get('date')) for ch in chs for w in ch.iter('writeoff') if w.get('void')!='1']
        bal=sum(float(ch.get('insbal') or 0)+float(ch.get('patbal') or 0) for ch in chs)
        if paid: stats['already-paid']+=1; continue
        if bal>0: stats['open-balance(postable)']+=1; continue
        if not wos: stats['zero-no-wo']+=1; continue
        stats['writeoff-only']+=1
        for w in wos: wocodes[w[2]]+=1; dates[w[4]]+=1
        out.append({'checkid':c['id'],'check':c['paymentnumber'],'carrier':c['systemcarriercode'],'visitid':v['visitid'],'patientid':pid,'patient':v['patientname'],'dos':v['dos'][:10],'era_pay':v['paymentamount'],'writeoffs':wos,'fee':sum(float(ch.get('fee') or 0) for ch in chs)})
    if i%25==0: print(i,len(todo),dict(stats),flush=True); time.sleep(0.2)
json.dump(out,open('wo_reversal_%s.json'%datetime.date.today().strftime('%Y%m%d'),'w'),indent=1)
print('DONE',dict(stats)); print('wocodes',wocodes.most_common(8)); print('dates',dates.most_common(8)); print('visits',len(out),'ERA $%.2f'%sum(o['era_pay'] for o in out))
