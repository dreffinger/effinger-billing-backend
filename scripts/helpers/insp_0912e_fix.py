# PLAIN ENGLISH (9/12 19:50 UTC 3pm ET run, inspector batch 127700 - 2 visits, both 117065068 hospitalization-from missing)
# Anchors (most recent 99223 on/before DOS within 45 days, via gettxhistory):
#   SEDGWICK pat17473658 -> 99223 09/08/2026; PELLAM CHARLES E pat17477710 -> 99223 09/09/2026 (both 99232 on 9/10/2026, HCA fac29).
# Write hospitalizationfrom only (NEVER hospitalizationto), then full-visit resave with onhcfa=1, then re-list.
import amd, resave, re, sys, time

amd.login_cached()
LOG = open('insp_0912e_fix.log', 'a')
def L(m):
    print(m, flush=True); LOG.write(m + "\n"); LOG.flush()

JOBS = [  # (visitid, chargeid, cpt, hospfrom, tag)
    ('19454374', '23365454', '99232', '09/08/2026', 'SEDGWICK 9/10'),
    ('19454375', '23365455', '99232', '09/09/2026', 'PELLAM C 9/10'),
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
# re-list the batch and report
time.sleep(1.5)
t = amd.post(amd.msg("getclaiminspectorcharges","chargeentry",{"batchid":"127700","nocookie":"1"}), timeout=120)
L("BATCH 127700 after: " + re.sub(r"\s+"," ", re.sub(r"<charge .*?/>","",t))[:900])
b = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"')
L("BATCHES after: %s" % re.findall(r'<batch id="([^"]+)"', b))
for cid in ("23365454","23365455"):
    x = resave.detail(cid)
    L("VERIFY %s onhcfa=%s extins=%s" % (cid, re.search(r'onhcfa="([^"]*)"', x).group(1), re.findall(r'<extins [^>]*hospitalizationfrom="[^"]*"', x)[:1]))
