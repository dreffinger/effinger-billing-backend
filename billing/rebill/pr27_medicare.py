# PLAIN ENGLISH (UHC 'coverage terminated' group to Medicare)
# Decides: For the patients UHC dropped (PR27), end UHC on the chart and re-send every open UHC-billed visit Medicare-first with the chart's Medicaid/LTC plan second.
# Rules it uses: Only visits on or after 5/1/2026 (the denial window) - older UHC lines are the unposted-ERA backlog, not a payer change. Skips any chart without an MBI.
# Never touches: Visits with a payment, visits on other carriers. (The 9/6 first run lacked the date filter - that is the Brentwood lesson.)
# ---
"""PR27 group (UHC 'coverage terminated'): Stedi 9/6 confirms UHC inactive + stand-alone Part D active = original Medicare.
Rebill every open UNI20-billed visit Medicare-first with the chart's Medicaid/LTC plan second.  Usage: python3 pr27_medicare.py [pid ...]"""
import amd, txh, resave, move_to_ins, ins_update, re, sys, time, datetime
amd.login_cached()
SEC = ('car6113', 'car6194', 'car42008', 'car42019', 'car6285')   # Medicaid FFS, Sunshine, FCC, Simply, Humana(Medicaid id = 10 digits)
PIDS = {'17471793': None, '17476490': '05/31/2026', '17471174': None, '17472429': None, '17471017': None, '17472849': None, '17473343': None, '17473422': None, '17476094': None}
def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    return re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
for pid in (sys.argv[1:] or list(PIDS)):
    pl = plans(pid); act = [p for p in pl if not p[3]]
    mc = [p for p in act if p[1] == 'car6085']
    if not mc: print(pid, 'NO MEDICARE on chart - skip', flush=True); continue
    ms = mc[0][5]
    sec = [p for p in act if p[1] in SEC and not (p[1] == 'car6285' and not p[4].isdigit())]
    order = ms + (',' + sec[0][5] if sec else '')
    uhc = [p for p in pl if p[1] == 'car6404' and not p[3]]
    for u in uhc:
        end = PIDS.get(pid) or '05/31/2026'
        print(pid, 'end UHC', u[4], end, ins_update.update(pid, u[0], enddate=end)[0], flush=True)
    root = txh.fetch('pat' + pid); byv = {}
    for c in root.iter('charge'):
        a = c.attrib
        if a.get('void') == '1' or float(a.get('insbal') or 0) <= 0 or a.get('carrier') != 'UNI20': continue
        if datetime.datetime.strptime(a['dos'], '%m/%d/%Y').date() < datetime.date(2026, 5, 1): continue   # only the PR27 window; older UNI20 lines are the unposted-ERA backlog
        if any(p.get('void') != '1' and float(p.get('amount') or 0) != 0 for p in c.iter('payment')): continue
        byv.setdefault(a['visit'], (a['id'], a['dos']))
    print(pid, 'order', order, 'visits', len(byv), flush=True)
    for vid, (cid, dos) in sorted(byv.items(), key=lambda kv: kv[1][1][-4:] + kv[1][1]):
        vis, pat, allc = resave.visit_charges(cid); e = vis.find('extins'); base = dict(e.attrib) if e is not None else {}; base.pop('id', None)
        base.update({'resubmissioncode': '1', 'origrefnum': ''})
        for k, val in {'patsignature': '1', 'emergency': '0', 'epsdt': '0', 'payprov': '1', 'employment': '0', 'autoaccident': '0', 'otheraccident': '0', 'pregnant': '0', 'outsidelab': '0'}.items(): base.setdefault(k, val)
        base = resave.clean_extins(base)
        for pc in sorted({c.get('proccode') for c in allc}):
            base['txtChargeCode'] = pc; amd.post(amd.msg('updextrainsinfo', 'chargeentry', {'visitid': str(vid), 'nocookie': '1'}, '<extins %s/>' % ' '.join('%s="%s"' % (k, v) for k, v in base.items())))
        print('  ', vid, dos, move_to_ins.move(cid, order), flush=True); time.sleep(0.5)
print('DONE')
