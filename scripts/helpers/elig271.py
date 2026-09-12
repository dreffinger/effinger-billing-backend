"""Parser for AMD checkEligibility PPMDResults XML (XML-ized 271). 9/9/2026."""
import re

def blocks(t):
    idx = [m.start() for m in re.finditer(r'<EligibilityOrBenefitInformation ', t)]
    out = []
    for i, s in enumerate(idx):
        e = idx[i+1] if i+1 < len(idx) else len(t)
        b = t[s:e]
        eb = {}
        head = re.match(r'<EligibilityOrBenefitInformation ([^>]*)/?>', b)
        for k, v in re.findall(r'EB(\d\d)_[A-Za-z]*="([^"]*)"', head.group(1)):
            if v: eb['EB'+k.lstrip('0')] = v
        dtps = re.findall(r'DTP01_DateTimeQualifier="(\d+)" DTP02_[^"]*="[^"]*" DTP03_DateTimePeriod="([^"]*)"', b)
        ents = re.findall(r'NM103_[A-Za-z]*="([^"]{2,})"', b)
        ids = re.findall(r'NM109_[A-Za-z]*="([^"]+)"', b)
        msgs = re.findall(r'MSG01_[A-Za-z]*="([^"]{2,})"', b)
        out.append({'eb': eb, 'dtp': dtps, 'ent': ents, 'entid': ids, 'msg': msgs[:2]})
    return out

def parse(xml):
    out = {'active': False, 'inactive': False, 'ma': [], 'partd': [],
           'aaa': [], 'dod': None, 'subscriberid': None, 'planstart': None,
           'hospice': False, 'blocks': []}
    m = re.search(r'\bsubscriberid="([^"]*)"', xml)
    if m: out['subscriberid'] = m.group(1).strip()
    m = re.search(r'insuranceeffectivestartdate="([^"]*)"', xml)
    if m and m.group(1): out['planstart'] = m.group(1)
    for m in re.finditer(r'<[A-Za-z]*AAA[A-Za-z]* ([^>]*)/?>', xml):
        c = re.search(r'AAA03_[A-Za-z]*="([^"]+)"', m.group(1))
        if c: out['aaa'].append(c.group(1))
    m = re.search(r'DTP01_DateTimeQualifier="442"[^>]*DTP03_DateTimePeriod="(\d+)"', xml)
    if m: out['dod'] = m.group(1)
    for b in blocks(xml):
        eb = b['eb']; code = eb.get('EB1', '')
        stc = eb.get('EB3', ''); ins = eb.get('EB4', '')
        if code == '1':
            out['active'] = True
        if code in ('6', '7', '8'):
            out['inactive'] = True
        if stc == '45' and code in ('1', 'U', 'R'):
            out['hospice'] = True
        if code in ('U', 'R') and b['ent']:
            entry = {'code': code, 'stc': stc, 'instype': ins,
                     'name': b['ent'][0], 'id': (b['entid'] or [''])[0],
                     'dates': b['dtp'][:3]}
            # OT/88 = drug plan; medical types HM/HN/HMO/PR/PS/IN/MA/MB etc.
            if ins == 'OT' or stc == '88':
                out['partd'].append(entry)
            else:
                out['ma'].append(entry)
        if code in ('U', 'R') or eb:
            out['blocks'].append({'EB': code, 'stc': stc[:24], 'ins': ins,
                                  'ent': b['ent'][:1], 'dtp': b['dtp'][:2]})
    return out

def summarize(p):
    bits = []
    if p['aaa']: bits.append('AAA ' + ','.join(p['aaa']))
    if p['dod']: bits.append('DOD ' + p['dod'])
    if p['ma']: bits.append('MA: ' + '; '.join(f"{e['name']} ({e['instype']})" for e in p['ma'][:2]))
    if p['partd']: bits.append('PartD: ' + '; '.join(e['name'] for e in p['partd'][:2]))
    if p['hospice']: bits.append('HOSPICE')
    bits.append('active' if p['active'] and not p['inactive'] else ('INACTIVE' if p['inactive'] else 'no-status'))
    if p['subscriberid']: bits.append('id ' + p['subscriberid'])
    return ' | '.join(bits)