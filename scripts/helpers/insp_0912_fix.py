# PLAIN ENGLISH (9/12 05:20 UTC inspector batch 127692 - 7 visits, all 117065068 hospitalization-from missing)
# Anchors (most recent 99223 on/before DOS within 45 days, via gettxhistory):
#   HOLLIS 08/26/2026, FENNER 09/03/2026, GARCIA 09/08/2026 (his 9/8 visit IS the 99223).
# Write hospitalizationfrom only (NEVER hospitalizationto), then full-visit resave with onhcfa=1, then re-list.
import amd, resave, re, sys, time

amd.login_cached()
LOG = open('insp_0912_fix.log', 'a')
def L(m):
    print(m, flush=True); LOG.write(m + "\n"); LOG.flush()

JOBS = [  # (visitid, chargeid, cpt, hospfrom, tag)
    ('19454267', '23365339', '99233', '08/26/2026', 'HOLLIS 9/10'),
    ('19454296', '23365369', '99233', '08/26/2026', 'HOLLIS 9/9'),
    ('19454280', '23365352', '99233', '09/03/2026', 'FENNER 9/10'),
    ('19454309', '23365382', '99233', '09/03/2026', 'FENNER 9/9'),
    ('19454277', '23365349', '99232', '09/08/2026', 'GARCIA 9/10'),
    ('19454285', '23365357', '99232', '09/08/2026', 'GARCIA 9/9'),
    ('19454315', '23365388', '99223', '09/08/2026', 'GARCIA 9/8'),
]

def extins(vid, cpt, hf):
    ch = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" '
          'payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (cpt, hf))
    r = amd.post(amd.msg('updextrainsinfo', 'chargeentry', {'nocookie': '1', 'visitid': 'vst%s' % vid}, ch))
    return 'ok' if 'Fault' not in r and 'error' not in r.lower()[:200] else r[:250]

def resave_onhcfa(cid):
    vis, pat, allc = resave.visit_charges(cid)
    chg = ''
    for c in allc:
        a = {'id': c.get('id')}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None:
                a[f] = v
        chg += '<charge %s/>' % ' '.join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va['force'] = '1'; va['onhcfa'] = '1'
    r = amd.post(amd.msg('updvisitwithnewcharges', 'chargeentry',
                         {'patientid': pat.get('id'), 'episodeid': vis.get('episode'), 'approval': '1',
                          'inspectorenabled': '1', 'getfinancials': '-1', 'customclaimfieldsavailable': '1',
                          'nocookie': '1'},
                         '<visit %s><chargelist>%s</chargelist></visit>' % (
                             ' '.join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    return 'ok' if 'Fault' not in r else 'FAULT ' + re.sub(r'\s+', ' ', r[:300])

for vid, cid, cpt, hf, tag in JOBS:
    L('EXTINS %s %s -> %s' % (tag, hf, extins(vid, cpt, hf)))
    time.sleep(0.2)
    L('RESAVE %s -> %s' % (tag, resave_onhcfa(cid)))
    time.sleep(0.3)