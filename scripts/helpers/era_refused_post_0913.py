# PLAIN ENGLISH (Post the ERA lines AMD's Post button refused, 9/13/2026 nightly)
# Decides: For each held check's refused visit line, posts the PAYMENT line (never the $0 denial line)
#          per charge: pay = min(allowed, live insurance balance), wo = adjustment capped so pay+wo <= balance.
# Rules it uses: William 9/13 standing rule - post the MAXIMUM AMD accepts, disregard the residual (report only).
#          Skips a charge already carrying a non-void payment with this check number.
# Never touches: denial-only lines, orphan lines with no matching live charge.
"""Usage: python3 era_refused_post_0913.py [--dry]  (JOBS list = the 9/13 held checks; edit per run)"""
import era_post, manual_post, resave, requests, json, sys, os, time
import xml.etree.ElementTree as ET

DRY = "--dry" in sys.argv
JOBS = [
 ('1051131','UNI20','1960189307','19362820'), ('1051131','UNI20','1960189307','19362837'),
 ('1051131','UNI20','1960189307','19362850'), ('1051329','FFVA','3005588619','19377613'),
 ('893458','FLO02','815541694','19388752'),  ('894119','FLO02','816062546','19395416'),
 ('894238','HUM01','149036630241223','19396623'), ('894303','HUM01','149784988250102','19397197'),
 ('894318','HUM01','149867907250104','19397411'), ('894375','HUM01','NO-PAY-202501120003963','19397898'),
 ('894516','HUM01','151507554250131','19398562'), ('894524','HUM01','151711286250202','19398393'),
 ('894572','HUM01','152036314250207','19398821'), ('894579','HUM01','152096809250208','19398821'),
 ('894628','HUM01','NO-PAY-202502150003537','19399477'), ('894912','HUM01','155131976250322','19401309'),
 ('894913','HUM01','155131975250322','19401326'), ('894947','HUM01','155693766250330','19401823'),
 ('895392','HUM01','162733532250707','19407725'), ('1046323','CAP07','4071099','19411100'),
 ('1046323','CAP07','4071099','19411094'), ('1046602','HUM01','166922655250904','19412592'),
 ('1049199','FLO02','819216047','19441645'),
]
os.makedirs('registers', exist_ok=True)
REG = 'registers/era_manual_register.json'
reg = json.load(open(REG)) if os.path.exists(REG) else {}
_cache = {}
def details(checkid):
    if checkid not in _cache:
        _cache[checkid] = requests.get(era_post.API+'/era/checkdetails', headers=era_post.H(),
                                       params={'checkid': checkid}, timeout=120).json()['eracheckdetails']
    return _cache[checkid]
posted = 0.0; wrote = 0.0; lines = 0
for checkid, car, chknum, visitid in JOBS:
    key = '%s:%s' % (checkid, visitid)
    if reg.get(key, {}).get('done'):
        print('SKIP (register)', key); continue
    vs = [v for v in details(checkid) if str(v.get('visitid')) == visitid]
    if not vs:
        print('ORPHAN no visit line', key); continue
    # collect payment lines (allowed > 0) per charge; merge duplicates by summing
    pay_lines = {}
    for v in vs:
        for ch in v.get('charges', []):
            cid = str(ch.get('chargedetailid') or -1)
            if int(ch.get('chargedetailid') or -1) <= 0: continue
            al = float(ch.get('allowedamount') or 0); adj = float(ch.get('adjustmentamount') or 0)
            if al <= 0: continue           # denial line - never post
            p = pay_lines.setdefault(cid, [0.0, 0.0]); p[0] += al; p[1] += adj
    if not pay_lines:
        print('DENIAL-ONLY (cascade handles)', key); continue
    for cid, (al, adj) in pay_lines.items():
        rt = ET.fromstring(resave.detail(cid))
        c = [x for x in rt.iter('charge') if x.get('id') == 'charge'+cid][0]
        if c.get('void') == '1':
            print('VOIDED charge', key, cid); continue
        dup = any(p.get('checknumber') == chknum and p.get('void') != '1' for p in rt.iter('payment'))
        if dup:
            print('ALREADY POSTED (check %s on charge)' % chknum, key, cid); continue
        bal = float(c.get('insbalance') or 0)
        if bal <= 0:
            print('NO BALANCE', key, cid, 'residual $%.2f dropped per rule' % al); continue
        pay = round(min(al, bal), 2)
        wo = round(min(adj, bal - pay), 2)
        note = 'ERA %s manual post (nightly 9/13; Post refused -2147217287/over-apply)' % checkid
        if DRY:
            print('DRY', key, cid, 'pay %.2f wo %.2f bal %.2f (allowed %.2f adj %.2f)' % (pay, wo, bal, al, adj)); continue
        try:
            ok = manual_post.post(cid, car, pay, wo, 'WOINS', checknumber=chknum, note=note)
            ok1 = ok[0] if isinstance(ok, tuple) else ok
            print('POST', key, cid, 'pay %.2f wo %.2f ->' % (pay, wo), ok1)
            if ok1:
                posted += pay; wrote += wo; lines += 1
                reg[key] = {'done': time.strftime('%Y-%m-%d'), 'charge': cid, 'pay': pay, 'wo': wo, 'check': chknum}
        except Exception as e:
            print('FAIL', key, cid, str(e)[:150])
        time.sleep(0.5)
if not DRY:
    json.dump(reg, open(REG, 'w'), indent=1)
print('=== refused-line pass: %d lines posted, $%.2f payments, $%.2f write-offs ===' % (lines, posted, wrote))
