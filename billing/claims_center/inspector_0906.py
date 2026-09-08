# PLAIN ENGLISH (9/6 Claim Inspector pass)
# Decides: Clears tonight's 37 inspector holds by rule: hospital admission date = most recent 99223 on/before the visit; Gresham F02.818 -> F03.90; Lowry 99497 gets modifier 25 next to 99223; Enderby second new-patient 99344 -> 99349; add-on/timely/AWV advisories bypassed.
# Rules it uses: William's standing rules from the columns skill. Winslow Jr's sequela-as-primary (S81.801S) is NOT bypassed - it needs a real diagnosis, so it goes to the board.
# Never touches: Paid visits, or any visit not on tonight's inspector list.
# ---
import amd, resave, recode, txh, json, re, time, datetime
import xml.etree.ElementTree as ET
amd.login_cached()
V = json.load(open('inspector_0906.json')); LOG = open('inspector_0906.log', 'a')
def L(m): print(m, flush=True); LOG.write(m + '\n'); LOG.flush()
def admit_for(pid, dos):
    """most recent 99223 on/before dos (same admission), else None"""
    d = datetime.datetime.strptime(dos, '%m/%d/%Y').date(); best = None
    for c in txh.fetch(pid).iter('charge'):
        if c.get('void') == '1' or c.get('proccode') != '99223' or not c.get('dos'): continue
        cd = datetime.datetime.strptime(c.get('dos'), '%m/%d/%Y').date()
        if cd <= d and (d - cd).days <= 45 and (best is None or cd > best): best = cd
    return best.strftime('%m/%d/%Y') if best else None
def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg('updextrainsinfo', 'chargeentry', {'visitid': vid, 'nocookie': '1'}, ext))
def echo_visit(cid, visit_over=None, charge_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ''
    for c in allc:
        a = {'id': c.get('id')}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        if charge_over and c.get('id') == 'charge' + cid: a.update(charge_over)
        chg += '<charge %s/>' % ' '.join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va['force'] = '1'; va.update(visit_over or {})
    r = amd.post(amd.msg('updvisitwithcharges', 'chargeentry', {'patientid': pat.get('id'), 'episodeid': vis.get('episode'), 'approval': '1', 'inspectorenabled': '1', 'getfinancials': '-1', 'customclaimfieldsavailable': '1', 'nocookie': '1'}, '<visit %s><chargelist>%s</chargelist></visit>' % (' '.join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    return 'Fault' not in r
def bypass(vid, errids):
    r = amd.post(amd.msg('bypassclaimedits', 'chargeentry', {'nocookie': '1'}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, ''.join('<claimedit id="%s"/>' % e for e in errids))))
    return 'Fault' not in r
hold = []
for v in V:
    vid = v['vid']; errs = v['errs']; nums = {e[1] for e in errs}
    try:
        if '117065068' in nums:                                   # admission date
            code = v['charges'][0][0]; cid = v['charges'][0][3]; dos = v['charges'][0][4]
            admit = dos if code == '99223' else admit_for(v['pid'], dos)
            if not admit: L('HOLD %s %s no 99223 anchor' % (v['pt'], dos)); hold.append((v, 'no admission anchor')); continue
            r = set_date(vid, code, admit); ok = 'Fault' not in r
            x = resave.detail(cid); on = re.search(r'onhcfa="([^"]*)"', x)
            if on and on.group(1) != '1': ok = echo_visit(cid, {'onhcfa': '1'}) and ok
            else: ok = echo_visit(cid) and ok
            L('ADMIT %-22s %s -> %s %s' % (v['pt'], dos, admit, 'OK' if ok else 'FAULT'))
        if '78080068' in nums and any('F02' in (e[3] or '') or 'F02' in c[2] for e in errs for c in v['charges']):   # Gresham dementia
            cid = v['charges'][0][3]; x = resave.detail(cid); m = re.search(r'<diagcode id="(dcode\d+)" code="F02\.?818"', x) or re.search(r'<diagcode id="(dcode\d+)" code="F02[^"]*"', x)
            if m: L('DX %s F02.x -> F03.90: %s' % (v['pt'], recode.swap_dx(cid, m.group(1), 'dcode1034545095', (v['insorder'] or '1').split(',')[0])))
            else: L('DX %s F02 dcode not found' % v['pt'])
        elif '78080068' in nums:                                  # Winslow Jr S81.801S primary
            L('HOLD %s S81.801S sequela as primary - needs a real dx (board)' % v['pt']); hold.append((v, 'S81.801S listed as primary diagnosis; needs the admitting diagnosis')); continue
        if '85079086' in nums:                                    # Lowry 99497 + 99223 -> 25 on 99497
            cid = [c[3] for c in v['charges'] if c[0] == '99497'][0]
            L('MOD25 %s 99497 -> %s' % (v['pt'], echo_visit(cid, None, {'modcodes': '25'})))
        if '78080084' in nums:                                    # Enderby 99344 established -> 99349
            cid = [c[3] for c in v['charges'] if c[0] == '99344'][0]
            L('RECODE %s 99344->99349: %s' % (v['pt'], recode.swap_proc(cid, {'pcode601053': 'pcode65142'}, (v['insorder'] or '1').split(',')[0])))
        by = [e[0] for e in errs if e[1] in ('68065080', '109084070', '109065087083')]
        if by: L('BYPASS %s %s -> %s' % (v['pt'], [e[1] for e in errs if e[0] in by], bypass(vid, by)))
    except Exception as ex:
        L('ERR %s %s: %s' % (v['pt'], vid, str(ex)[:150]))
    time.sleep(0.5)
json.dump([(h[0]['pt'], h[0]['vid'], h[0]['charges'][0][4], h[1]) for h in hold], open('inspector_hold_0906.json', 'w'))
L('DONE; holds: %s' % [(h[0]['pt'], h[1]) for h in hold])
