"""AMD write/read helpers rebuilt 9/8/2026 from the registry + Postman shapes."""
import re, amd

def plans(pid):
    t = amd.call(f'action="getdemographic" class="demographics" patientid="pat{pid}" nocookie="1"')
    out = []
    for m in re.finditer(r'<insplan ([^>]*?)/?>', t):
        a = m.group(1)
        g = lambda k: (re.search(k + r'="([^"]*)"', a) or [None, ''])[1] if re.search(k + r'="([^"]*)"', a) else ''
        out.append({'id': g('\\bid'), 'carrier': g('carrier'), 'carriercode': g('carriercode'),
                    'carriername': g('carriername'), 'seq': g('sequence'), 'num': g('subscribernum'),
                    'begin': g('begindate'), 'end': g('enddate'), 'coverage': g('coverage')})
    resp = re.search(r'respparty="(resp\d+)"', t) or re.search(r'<respparty id="(resp\d+)"', t)
    dob = re.search(r'\bdob="([^"]*)"', t)
    name = re.search(r'\bname="([^"]*)"', t)
    return out, (resp.group(1) if resp else None), (dob.group(1) if dob else ''), (name.group(1) if name else ''), t

def txh(pid):
    t = amd.call(f'action="gettxhistory" class="demographics" patientid="{pid}" filterhistory="0" pagenumber="1" typefilter="1" sortbypayment="0" groupbyvisit="0" sortdescending="1" profileid="" getmemo="0" nocookie="1"')
    out = []
    for m in re.finditer(r'<charge ([^>]*?)/?>', t):
        a = m.group(1)
        def g(k, d=''):
            mm = re.search(r'\b' + k + r'="([^"]*)"', a)
            return mm.group(1) if mm else d
        if not g('proccode'): continue
        out.append({'id': g('id'), 'visit': g('visit'), 'proc': g('proccode'),
                    'begindate': g('begindate') or g('date'), 'fee': g('fee'), 'paid': g('paid'),
                    'insbal': g('insbal'), 'patbal': g('patbal'), 'carrier': g('carrier'),
                    'payerinfo': g('payerinfo'), 'billdate': g('billdate'), 'descr': g('description')[:30],
                    'raw': a})
    return out, t

def add_plan(pid, car, num, begindate, resp, coverage='1'):
    """addinsurance - Postman shape, NEVER a group number. Returns (insid, sequence, raw)."""
    child = (f'<patient id="pat{pid}" changed="1"><insplanlist>'
             f'<insplan id="" begindate="{begindate}" enddate="" carrier="{car}" subscriber="{resp}" '
             f'subscribernum="{amd.esc(num)}" hipaarelationship="18" relationship="1" grpname="" grpnum="" '
             f'copay="0.00" copaytype="$" coverage="{coverage}" payerid="" mspcode="" eligibilityid="" '
             f'eligibilitystatusid="" eligibilitychangedat="" eligibilitycreatedat="" eligibilityresponsedate="" '
             f'deductible="0.00" deductiblemet="0.00" yearendmonth="1" lifetime="0.00"><insnote></insnote>'
             f'</insplan></insplanlist></patient>')
    t = amd.call('action="addinsurance" class="demographics" nocookie="1"', child)
    ins = re.search(r'<insplan id="(ins\d+)"[^>]*sequence="(\d+)"', t)
    if not ins:
        ins = re.search(r'id="(ins\d+)"', t)
        seq = re.search(r'sequence="(\d+)"', t)
        return (ins.group(1) if ins else None), (seq.group(1) if seq else None), t
    return ins.group(1), ins.group(2), t

def upd_plan(pid, insid, field, new, old):
    child = (f'<patient id="pat{pid}" changed="1"><insplanlist>'
             f'<insplan id="{insid}" {field}="{amd.esc(new)}" o_{field}="{amd.esc(old)}"/>'
             f'</insplanlist></patient>')
    t = amd.call('action="updateinsurance" class="demographics" nocookie="1"', child)
    return ('Fault' not in t), t

def freq1(chargeid, visitid, seq):
    """Reset resubmission to original then queue rebill to plan sequence seq."""
    cid = str(chargeid).lstrip('charge')
    t = amd.call(f'action="updextrainsinfo" class="chargeentry" visitid="vst{str(visitid).lstrip("vst")}" nocookie="1"',
                 '<extins resubmissioncode="1" origrefnum=""/>')
    st = amd.rebill_charge(cid, seq)
    return st, t

# Full-echo visit resave for insorder/payer switches (void-trap safe):
# fetch EVERY active charge's detail by CHARGE id, echo CHG_KEYS + visit attrs, set insorder, force=1.
CHG_KEYS = ['respparty','begindate','enddate','diagcodes','modcodes','finclasscode','aging','billins',
            'proccode','cobcode','pos','tos','units','netfee','fee','allowed','patportion','insportion',
            'patbalance','insbalance']
VIS_KEYS = ['seq','date','isappt','profile','episode','insorder','note','forcepaper','facility',
            'refplan','onhcfa','acceptassign','referenceid']

def detail(cid):
    t = amd.call(f'action="getchargedetaildataicd10" class="demographics" chargeid="{cid}" nocookie="1"')
    attrs = lambda s: dict(re.findall(r'([a-zA-Z0-9_]+)="([^"]*)"', s))
    return attrs(re.search(r'<visit ([^>]*)>', t).group(1)), attrs(re.search(r'<charge ([^>]*?)/?>', t).group(1))

def resave_visit(pid, charge_ids, insorder):
    """charge_ids must be ALL active charges of the visit (void trap)."""
    vats = None; chxml = []
    for cid in charge_ids:
        v, c = detail(cid)
        if c.get('void') == '1': continue
        if vats is None: vats = v
        parts = [f'id="{c["id"].replace("charge","")}"'] + [f'{k}="{amd.esc(c.get(k,""))}"' for k in CHG_KEYS]
        chxml.append('<charge ' + ' '.join(parts) + '/>')
    vparts = [f'id="{vats["id"]}"'] + [f'{k}="{amd.esc(insorder if k=="insorder" else vats.get(k,""))}"' for k in VIS_KEYS] + ['force="1"']
    t = amd.call(f'action="updvisitwithcharges" class="chargeentry" patientid="pat{pid}" '
                 f'episodeid="{vats.get("episode","")}" approval="1" inspectorenabled="1" '
                 f'getfinancials="-1" customclaimfieldsavailable="1" nocookie="1"',
                 f'<visit {" ".join(vparts)}><chargelist>{"".join(chxml)}</chargelist></visit>')
    f = re.search(r'<description>([^<]*)</description>', t)
    return (f.group(1)[:150] if f else None), t
