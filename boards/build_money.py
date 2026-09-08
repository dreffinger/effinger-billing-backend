# PLAIN ENGLISH (Money Ledger builder)
# Decides: Nothing. Pulls the unpaid list, ERA Center checks, claim runs, tonight's exclusions and the write-off registers into money_data.json and renders money_ledger.html for the Effinger Money Ledger artifact.
# Rules it uses: Outstanding is aged by date of service; FFVA remits belong to BCBS; credentialing-gap payers carry a note.
# Never touches: AMD writes. Read-only.
# ---
"""Usage: python3 build_money.py   (then republish money_ledger.html). Refreshes unpaid_<date>.json, era_checks_<date>.json, claimruns_<date>.json first."""
import amd, era_post, requests, json, re, collections, datetime, glob
amd.login_cached(); today = datetime.date.today(); stamp = today.strftime('%Y%m%d')
unp = requests.post(era_post.API + '/claim/massrebillsearch', headers=era_post.H(), json={}, timeout=120).json(); json.dump(unp, open('unpaid_%s.json' % stamp, 'w'))
cs = era_post.checks(); json.dump(cs, open('era_checks_%s.json' % stamp, 'w'))
r = amd.post(amd.msg('getclaimrunstatus', 'claimsreports', {'nocookie': '1'}), timeout=120)
runs = [dict(re.findall(r'(\w+)="([^"]*)"', cr)) for cr in re.findall(r'<claimrun [^>]*>', r)]
ex = []
for a in runs:
    if int(a.get('totalexclusions') or 0) == 0: continue
    x = amd.post(amd.msg('getclaimexclusioncharges', 'claimsreports', {'nocookie': '1', 'claimrunid': a['id'], 'clearinghouse': '1', 'payer': '1'}), timeout=120)
    for m in re.finditer(r'<visit [^>]*id="(\d+)"[^>]*patientname="([^"]*)"[^>]*carriercode="([^"]*)"', x): ex.append({'vid': m.group(1), 'pt': m.group(2), 'car': m.group(3)})
cars = json.load(open('carriers.json')); name = {v[0]: v[1] for v in cars.values()}
def age(v): return (today - datetime.datetime.fromisoformat(v['dateofservice']).date()).days
B = collections.OrderedDict([('0-30', (0, 30)), ('31-60', (31, 60)), ('61-90', (61, 90)), ('91-180', (91, 180)), ('181-365', (181, 365)), ('over 365', (366, 99999))])
payer = collections.defaultdict(lambda: {'unpaid_n': 0, 'unpaid': 0.0, 'buckets': {k: 0.0 for k in B}, 'era_checks': 0, 'era_paid': 0.0, 'era_unposted': 0.0, 'excl_n': 0, 'excl': 0.0, 'writeoff': 0.0})
for v in unp:
    c = v['carriercode'].strip() or 'NONE'; p = payer[c]; p['unpaid_n'] += 1; p['unpaid'] += v['insbalance']; a = age(v)
    for k, (lo, hi) in B.items():
        if lo <= a <= hi: p['buckets'][k] += v['insbalance']
for c in cs:
    k = c.get('systemcarriercode') or 'OTHER'; p = payer[k]; p['era_checks'] += 1; p['era_paid'] += c.get('paymentamount') or 0; p['era_unposted'] += c.get('unpostedamount') or 0
vamt = {v['visitid']: v['insbalance'] for v in unp}
for r_ in ex:
    k = r_['car'].split()[0]; payer[k]['excl_n'] += 1; payer[k]['excl'] += vamt.get(int(r_['vid']), 0)
wo = []
try:
    import openpyxl
    for f in sorted(glob.glob('Writeoff_register_*.xlsx')):
        ws = openpyxl.load_workbook(f, data_only=True).active; hdr = [str(c.value).lower() if c.value else '' for c in ws[1]]
        ai = [i for i, h in enumerate(hdr) if 'amount' in h or 'write' in h]; ci = [i for i, h in enumerate(hdr) if 'carrier' in h or 'payer' in h]
        for row in ws.iter_rows(min_row=2, values_only=True):
            try: wo.append((str(row[ci[0]] if ci else '') or 'OTHER', float(row[ai[0]])))
            except Exception: pass
except Exception as e: print('writeoff registers:', e)
wo += [('AET07', 513.0), ('FLO02', 630.0), ('MCAD', 232.11)]          # 9/6 manual write-offs not yet in a register
for c, a in wo: payer[c.split()[0]]['writeoff'] += a
cred = {'TRI00': 'TRICARE East - Pam not credentialed (CO185); re-credentialing in progress', 'TRI05': 'TRICARE - carrier file problem (Olson hold)', 'VACCN': 'VA CCN - myVACCN portal registration pending; claims need VA auth numbers', 'RET01': 'Railroad Medicare - not credentialed; written off for now', 'FLO99': 'Florida Community Care - no electronic eligibility; portal only', 'OPT08': 'Optum Network - subscriber not found (Southwick)'}
prev = json.load(open('money_data.json')) if glob.glob('money_data.json') else {}
PAY = json.load(open('payments_by_carrier.json'))['carriers'] if glob.glob('payments_by_carrier.json') else {}   # pay_scan.py: posted payments per carrier
for k, v in PAY.items():
    p = payer[k]; p['paid_12'] = v['paid_12']; p['paid_dos12'] = v['paid_dos12']; p['paid_all'] = v['paid_all']; p['last_paid'] = v['last_paid']; p['n_paid_12'] = v['n_12']; p['dos_year'] = v['dos_year']; p['wo_12'] = v['wo_12']
out = {'asof': (datetime.datetime.utcnow() - datetime.timedelta(hours=4)).strftime('%Y-%m-%d %H:%M ET'), 'runs': {'n_runs': len(runs), 'claims': sum(int(r_['totalsent']) for r_ in runs), 'amount': sum(float(r_['totalamount']) for r_ in runs), 'since': min(r_['date'] for r_ in runs)[:10]},
       'unpaid_total': sum(v['insbalance'] for v in unp), 'unpaid_n': len(unp),
       'era': {'checks': len(cs), 'paid': sum(c.get('paymentamount') or 0 for c in cs), 'unposted': sum(c.get('unpostedamount') or 0 for c in cs)},
       'excl': {'before_n': prev.get('excl', {}).get('after_n', 0), 'before': prev.get('excl', {}).get('after', 0), 'after_n': len(ex), 'after': sum(vamt.get(int(r_['vid']), 0) for r_ in ex)},
       'writeoff_total': sum(a for _, a in wo), 'claimstatus': prev.get('claimstatus', {}),
       'paid': {'posted_12': sum(v['paid_12'] for v in PAY.values()), 'dos_12': sum(v['paid_dos12'] for v in PAY.values()), 'all': sum(v['paid_all'] for v in PAY.values()), 'patients': json.load(open('payments_by_carrier.json'))['patients'] if PAY else 0},
       'payers': [dict(code=k, name=name.get(k, k), **v, note=cred.get(k, '')) for k, v in sorted(payer.items(), key=lambda kv: -kv[1]['unpaid'])],
       'buckets': {k: sum(p['buckets'][k] for p in payer.values()) for k in B}}
json.dump(out, open('money_data.json', 'w'), indent=1)
open('money_ledger.html', 'w').write(open('money_template.html').read().replace('/*__DATA__*/null', json.dumps(out)))
print('money_ledger.html rebuilt: unpaid $%.0f, era $%.0f, excl %d' % (out['unpaid_total'], out['era']['paid'], len(ex)))
