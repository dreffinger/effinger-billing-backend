# PLAIN ENGLISH (Medicare $0-denial cascade)
# Decides: For every patient in the Medicare $0-denial scan (CO24 / COB9 / CO16 / CO22 / CO109), what Medicare's own record says for the denied date of service - Advantage plan, hospice, MBI mismatch, other payer, death - and what to do about it.
# Rules it uses: CO24 = Advantage plan responsible -> add the plan, undo the $0 posting, bill the plan. COB9 = hospice -> Medicare + GV. CO16 = bad ID -> use CMS's MBI. CO109 = Railroad -> written off (no credentialing). CO22 = another payer is primary -> find it. Older than 12 months -> write off.
# Never touches: Anything in --report mode. With --act it only runs the proven helpers (add_ins, ins_update, co24_restore, gv_rebill, rebill_patient_year) on rows whose answer is unambiguous; everything else goes to the board.
# ---
"""Usage: python3 denial_cascade.py [--act]   reads scan_co24.json (+ claimstatus_<date>.json 'FINALIZED $0' rows) -> denial_cascade_<date>.json"""
import amd, stedi, json, re, sys, datetime, collections, time
amd.login_cached(); today = datetime.date.today(); stamp = today.strftime('%Y%m%d'); ACT = '--act' in sys.argv
def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
    return a, pl
hits = json.load(open('scan_co24.json')); by = collections.defaultdict(list)
for h in hits: by[h['pid']].append(h)
out = []
for pid, hs in by.items():
    pa, pl = plans(pid); nm = pa.get('name') or hs[0]['patient']; last, first = nm.split(',')[0].strip(), nm.split(',')[-1].strip().split(' ')[0]
    dob = pa.get('dob', ''); dobc = dob[6:] + dob[:2] + dob[3:5]
    codes = collections.Counter(c for h in hs for c in h['codes']); doss = sorted(datetime.datetime.strptime(h['dos'], '%m/%d/%Y').date() for h in hs)
    mid = doss[len(doss) // 2]; dos = mid.strftime('%Y%m%d')
    rec = {'pid': pid, 'patient': nm, 'dob': dob, 'codes': dict(codes), 'lines': len(hs), 'fee': sum(float(h['fee']) for h in hs), 'first': doss[0].isoformat(), 'last': doss[-1].isoformat(),
           'chart_mbi': next((p[4] for p in pl if p[1] == 'car6085'), ''), 'chart_plans': [(p[1], p[4], p[2], p[3]) for p in pl]}
    try:
        j = stedi.mbi(first, last, dobc, pa.get('state') or 'FL', dos); m = stedi.med_summ(j)
        rec['cms'] = {'mbi': m['mbi'], 'partA': m['partA'], 'partB': m['partB'], 'death': m['death'], 'errors': m['errors'],
                      'ma': [(o['entity'], o['dates'], o['typeName']) for o in m['other'] if o['code'] in ('U', 'R') and (o['type'] or '') in ('HN', 'HM', 'PR', 'PS', 'IN', 'MC', 'MD')],
                      'hospice': [o for o in m['other'] if '45' in json.dumps(o)], 'other': [(o['code'], o['type'], o['entity']) for o in m['other'] if o['code'] in ('U', 'R')]}
        c = rec['cms']
        if c['errors']: rec['verdict'] = 'NOT FOUND on Medicare by name/DOB - retry with chart MBI on CMS direct; else board'
        elif c['death'] and c['death'] < doss[-1].strftime('%Y%m%d'): rec['verdict'] = 'DATE OF DEATH %s - write off lines after it, board' % c['death']
        elif c['ma']: rec['verdict'] = 'ADVANTAGE PLAN on DOS: %s -> add plan, co24_restore, bill it' % '; '.join(e[0] for e in c['ma'][0][0])
        elif 'COB9' in codes and c['hospice']: rec['verdict'] = 'HOSPICE confirmed -> gv_rebill (Medicare + GV)'
        elif 'COB9' in codes: rec['verdict'] = 'COB9 but no hospice benefit in CMS reply for that date - check hospice election dates; gv_rebill likely still right'
        elif 'CO16' in codes and rec['chart_mbi'] and c['mbi'] and rec['chart_mbi'] != c['mbi']: rec['verdict'] = 'MBI MISMATCH chart %s vs CMS %s -> fix + rebill' % (rec['chart_mbi'], c['mbi'])
        elif 'CO16' in codes: rec['verdict'] = 'CO16 with matching MBI - the bad identifier is something else (name/DOB/sex on claim); compare chart vs CMS: %s' % json.dumps(j.get('subscriber', {}).get('address'))
        elif 'CO109' in codes: rec['verdict'] = 'CO109 Railroad Medicare - written off per William (no RR credentialing)'
        elif 'CO22' in codes: rec['verdict'] = 'CO22 other payer primary - CMS shows: %s' % json.dumps(c['other'])[:200]
        else: rec['verdict'] = 'straight Medicare, no MA/hospice - rebill to Medicare as original'
    except Exception as e: rec['verdict'] = 'ERROR ' + str(e)[:120]
    out.append(rec); print('%-24s %-14s %2d $%-7.0f %s -> %s' % (nm[:24], '/'.join(codes), len(hs), rec['fee'], rec['first'], rec['verdict'][:150]), flush=True); time.sleep(0.3)
json.dump(out, open('denial_cascade_%s.json' % stamp, 'w'), indent=1)
