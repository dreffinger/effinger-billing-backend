# PLAIN ENGLISH (Add an insurance plan)
# Decides: Nothing on its own. Adds one plan (carrier + member number + begin date) to a chart and returns its sequence number.
# Rules it uses: No group numbers or group names, ever. Default begin date is one year back so old visits can bill to it.
# Never touches: Existing plans, visits, balances.
# ---
"""Add an insurance plan (addinsurance class=api; William's rule: NO grpnum/grpname; begindate one year back by default).
Usage: python3 add_ins.py <patientid> <carrierid car####> <subscribernum> [begindate mm/dd/yyyy] [coverage 1]"""
import amd, re, sys, datetime
def add(pid, carrier, subnum, begindate=None, coverage="1", finclass="CC"):
    pid = re.sub(r"\D", "", str(pid))
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    resp = re.search(r'<respparty id="(resp\d+)"', r).group(1)
    if not begindate:
        d = datetime.date.today(); begindate = "%02d/%02d/%d" % (d.month, d.day, d.year - 1)
    xml = ('<patient id="pat%s" changed="1"><insplanlist><insplan id="" begindate="%s" enddate="" carrier="%s" subscriber="%s" subscribernum="%s" '
           'hipaarelationship="18" relationship="1" grpname="" grpnum="" copay="0.00" copaytype="$" coverage="%s" payerid="" mspcode="" eligibilityid="" '
           'eligibilitystatusid="" eligibilitychangedat="" eligibilitycreatedat="" eligibilityresponsedate="" finclasscode="%s" deductible="0.00" '
           'deductiblemet="0.00" yearendmonth="1" lifetime="0.00"><insnote/></insplan></insplanlist></patient>') % (pid, begindate, carrier, resp, subnum, coverage, finclass)
    res = amd.post(amd.msg("addinsurance", "demographics", {"nocookie": "1"}, xml))
    m = re.search(r'<patient id="(ins\d+)" sequence="(\d+)"', res)
    return (m.group(1), m.group(2)) if m else (None, re.sub(r"\s+", " ", res[100:400]))
if __name__ == "__main__":
    a = sys.argv[1:]; print(add(a[0], a[1], a[2], a[3] if len(a) > 3 else None, a[4] if len(a) > 4 else "1"))
