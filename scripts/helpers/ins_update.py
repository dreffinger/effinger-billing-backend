# PLAIN ENGLISH (Update one plan)
# Decides: Nothing on its own. Changes fields on an existing plan - end date, begin date, member number, even the carrier - with AMD's original-value echo.
# Rules it uses: Used to end a dead plan the day before the first denied visit, or to fix a typo'd MBI in place.
# Never touches: Adds or deletes plans; never touches visits.
# ---
"""Update one insplan field set on a patient (works 9/3/2026: action=updateinsurance class=demographics,
insplan id=insNNN with the documented attrs + o_<attr> originals for the concurrency check).
Usage: python3 ins_update.py <patientid> <insplanid> key=value [...]   e.g. enddate=08/03/2026"""
import amd, re, sys
KEYS = "begindate enddate carrier subscriber subscribernum hipaarelationship relationship grpname grpnum copay copaytype coverage payerid mspcode eligibilityid eligibilitystatusid eligibilitychangedat eligibilitycreatedat eligibilityresponsedate finclasscode deductible deductiblemet yearendmonth lifetime sequence".split()
def update(pid, insid, **changes):
    pid = re.sub(r"\D", "", str(pid)); insid = "ins" + re.sub(r"\D", "", str(insid))
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    m = re.search(r'<insplan id="%s"[^>]*>' % insid, r)
    if not m: return False, "insplan not found"
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
    a = {k: attrs.get(k, "") for k in KEYS}; o = {"o_" + k: v for k, v in a.items()}
    a.update(changes); a.update(o)
    xml = '<patient id="pat%s" changed="1"><insplanlist><insplan id="%s" %s><insnote/></insplan></insplanlist></patient>' % (pid, insid, " ".join('%s="%s"' % (k, v) for k, v in a.items()))
    res = amd.post(amd.msg("updateinsurance", "demographics", {"nocookie": "1"}, xml))
    return 'success="1"' in res, re.sub(r"\s+", " ", res[100:300])
if __name__ == "__main__":
    print(update(sys.argv[1], sys.argv[2], **dict(x.split("=", 1) for x in sys.argv[3:])))
