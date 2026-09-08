# PLAIN ENGLISH (Blank insurance effective-date scan)
# Decides: Which active insurance plans on recently-seen patients have NO effective (begin) date - the Sorrells oversight William spotted 9/6. Plans without a begin date can be sent as primary when they should not be, and eligibility checks cannot date them.
# Rules it uses: Reads the unpaid list for patients seen in the last 90 days, pulls each chart once, lists open plans with begindate="". Report only; fixing is a separate decision (date = first DOS billed to that plan is the usual answer).
# Never touches: Any chart.
# ---
import amd, re, json, sys, time, datetime
amd.login_cached(); cut = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
import glob; unp = json.load(open(sorted(glob.glob('unpaid_*.json'))[-1]))
pids = sorted({v['patientid'] for v in unp if v['dateofservice'] >= cut}); blank = []
for pid in pids:
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    nm = re.search(r'<patient [^>]*name="([^"]*)"', r); nm = nm.group(1) if nm else str(pid)
    for m in re.finditer(r'<insplan [^>]*>', r):
        d = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if not d.get('begindate') and not d.get('enddate'): blank.append({'pid': pid, 'patient': nm, 'ins': d.get('id'), 'carrier': d.get('carrier'), 'num': d.get('subscribernum'), 'seq': d.get('sequence'), 'created': d.get('eligibilitycreatedat')}); print(blank[-1], flush=True)
    time.sleep(0.1)
json.dump(blank, open('blank_begindate_%s.json' % datetime.date.today().strftime('%Y%m%d'), 'w'), indent=1)
print('scanned %d patients, %d open plans with no effective date' % (len(pids), len(blank)))
