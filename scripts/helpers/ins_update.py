# PLAIN ENGLISH (Update one plan)
# Decides: Nothing on its own. Changes fields on an existing plan - end date, begin date, member number, even the carrier - with AMD's original-value echo.
# Rules it uses: Used to end a dead plan the day before the first denied visit, or to fix a typo'd MBI in place. Never echoes the plan's `sequence` attr unless asked - AMD treats it as the PATIENT insurance order (9/14/2026).
# Never touches: Adds or deletes plans; never touches visits.
# ORDER (10/6/2026): sequence="2,1" is sent as its own call through an ACTIVE plan and verified - AMD blanks the order
#   (success="1", insorder="") when it goes through an end-dated plan; one re-send through another active plan.
# ---
"""Update one insplan field set on a patient (works 9/3/2026: action=updateinsurance class=demographics,
insplan id=insNNN with the documented attrs + o_<attr> originals for the concurrency check).
Usage: python3 ins_update.py <patientid> <insplanid> key=value [...]   e.g. enddate=08/03/2026"""
import amd, re, sys, datetime
KEYS = "begindate enddate carrier subscriber subscribernum hipaarelationship relationship grpname grpnum copay copaytype coverage payerid mspcode eligibilityid eligibilitystatusid eligibilitychangedat eligibilitycreatedat eligibilityresponsedate finclasscode deductible deductiblemet yearendmonth lifetime sequence".split()
def _plans(pid):
    """(raw getdemographic, {insplan id: attrs}, patient insorder)"""
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    plans = {}
    for tag in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', tag))
        if a.get("id"): plans[a["id"]] = a
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', r)
    return r, plans, (m.group(1) if m else None)

def _active(attrs):
    """True when the plan has no end date or one that is not in the past."""
    e = (attrs.get("enddate") or "").strip()
    if not e: return True
    try:
        return datetime.datetime.strptime(e, "%m/%d/%Y").date() >= datetime.date.today()
    except ValueError:
        return True

def _send(pid, insid, attrs, changes):
    a = {k: attrs.get(k, "") for k in KEYS}; o = {"o_" + k: v for k, v in a.items()}
    # 9/14/2026 (Tillotson): AMD reads the echoed `sequence` attr as the PATIENT's insurance ORDER - echoing a plan's own
    # sequence ("4") on a begin-date edit silently reset insorder "4,3" -> "4". So `sequence` goes out ONLY when the
    # caller passes it on purpose (sequence="2,1" = set the patient order Medicare-first); plain field edits never send it.
    if "sequence" not in changes:
        a.pop("sequence", None); o.pop("o_sequence", None)
    a.update(changes); a.update(o)
    xml = '<patient id="pat%s" changed="1"><insplanlist><insplan id="%s" %s><insnote/></insplan></insplanlist></patient>' % (pid, insid, " ".join('%s="%s"' % (k, v) for k, v in a.items()))
    return amd.post(amd.msg("updateinsurance", "demographics", {"nocookie": "1"}, xml))

def update(pid, insid, **changes):
    """Field edits go to `insid`. A `sequence` (= the PATIENT's insurance order, e.g. "2,1") goes as its OWN call through an
    ACTIVE plan - `insid` when it is active, else the first active plan on the chart - and is VERIFIED: AMD answers
    success="1" with insorder="" when the order is sent through an end-dated plan (10/6/2026, chart 12232248). On a
    mismatch it is re-read once and, if still wrong, re-sent ONCE through another active plan. Returns (ok, message)."""
    pid = re.sub(r"\D", "", str(pid)); insid = "ins" + re.sub(r"\D", "", str(insid))
    seq = changes.pop("sequence", None)
    r, plans, _ = _plans(pid)
    if insid not in plans: return False, "insplan not found"
    msgs = []; ok = True
    if changes:
        res = _send(pid, insid, plans[insid], changes)
        ok = 'success="1"' in res; msgs.append(re.sub(r"\s+", " ", res[100:300]))
        if seq is None or not ok: return ok, msgs[0]
        r, plans, _ = _plans(pid)                                   # fresh originals for the order call
    elif seq is None:
        return False, "nothing to change"
    want = str(seq).replace(" ", "")
    order = [insid] if _active(plans[insid]) else []
    order += [p for p, a in plans.items() if p != insid and _active(a)]
    if not order: return False, " | ".join(msgs + ["no active plan on the chart to carry insorder %s" % want])
    for n, via in enumerate(order[:2]):
        res = _send(pid, via, plans[via], {"sequence": want})
        m = re.search(r'<patient [^>]*?insorder="([^"]*)"', res)
        got = m.group(1) if m else None
        if got is None or got.replace(" ", "") != want:
            got = (_plans(pid)[2] or "")                            # the response can omit it - trust a re-read
        landed = 'success="1"' in res and got.replace(" ", "") == want
        msgs.append("insorder %s via %s%s -> %s" % (want, via, "" if via == insid else " (active plan)", repr(got)))
        if landed: return ok, " | ".join(msgs)
        if n == 0 and len(order) > 1: msgs.append("insorder did not land - re-sending once through another active plan")
    return False, " | ".join(msgs + ["insorder NOT set - check the chart"])
if __name__ == "__main__":
    print(update(sys.argv[1], sys.argv[2], **dict(x.split("=", 1) for x in sys.argv[3:])))
