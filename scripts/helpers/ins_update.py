# PLAIN ENGLISH (Update one plan)
# Decides: Nothing on its own. Changes fields on an existing plan - end date, begin date, member number, even the carrier - with AMD's original-value echo.
# Rules it uses: Used to end a dead plan the day before the first denied visit, or to fix a typo'd MBI in place. Never echoes the plan's `sequence` attr unless asked - AMD treats it as the PATIENT insurance order (9/14/2026).
# Never touches: Adds or deletes plans; never touches visits.
# ORDER (10/6/2026): sequence="2,1" is sent as its own call through an ACTIVE plan and verified - AMD blanks the order
#   (success="1", insorder="") when it goes through an end-dated plan; a wiped order is put back; never raises after a write.
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

def _norm(o): return (o or "").replace(" ", "")

def _set_order(pid, plans, insid, want):
    """Send the patient order `want` through at most two ACTIVE plans (the plans the order names first, its leading plan first)
    and verify it. Refuses without writing when the order would lead with an end-dated plan (AMD blanks it). -> (ok, msg)"""
    by_seq = {a.get("sequence"): p for p, a in plans.items()}
    seqs = [x for x in want.split(",") if x]
    lead = by_seq.get(seqs[0]) if seqs else None
    if lead is None: return False, "insorder %s: no plan on the chart has sequence %s - nothing written" % (want, seqs[0] if seqs else "?")
    if not _active(plans[lead]): return False, "insorder %s would lead with end-dated plan %s (AMD blanks that) - nothing written" % (want, lead)
    named = [by_seq[x] for x in seqs if x in by_seq]
    cands = []
    for p in ([insid] if insid in named else []) + named + [insid] + list(plans):
        if p in plans and _active(plans[p]) and p not in cands: cands.append(p)
    out = []
    for via in cands[:2]:
        try:
            res = _send(pid, via, plans[via], {"sequence": want})
            m = re.search(r'<patient [^>]*?insorder="([^"]*)"', res); got = m.group(1) if m else None
            if got is None or _norm(got) != want: got = _plans(pid)[2] or ""     # the answer can omit it - trust a re-read
        except Exception as e:
            out.append("insorder %s via %s: call failed (%s) - check the chart" % (want, via, str(e)[:80])); return False, " | ".join(out)
        out.append("insorder %s via %s -> %r" % (want, via, got))
        if 'success="1"' in res and _norm(got) == want: return True, " | ".join(out)
    return False, " | ".join(out)

def update(pid, insid, **changes):
    """Field edits go to `insid`. `sequence` (= the PATIENT's insurance order, e.g. "2,1") goes as its OWN call through an ACTIVE
    plan and is VERIFIED - AMD answers success="1" with insorder="" when the order goes through an end-dated plan (10/6/2026,
    chart 12232248). A field edit that wipes the chart's order (9/21 behaviour) gets the previous order put back. If a requested
    order does not land, the previous one is restored. Never raises after a write: (ok, message), message says what to check."""
    pid = re.sub(r"\D", "", str(pid)); insid = "ins" + re.sub(r"\D", "", str(insid))
    seq = changes.pop("sequence", None)
    try:
        r, plans, before = _plans(pid)
    except Exception as e:
        return False, "getdemographic failed - nothing written (%s)" % str(e)[:100]
    if insid not in plans: return False, "insplan not found"
    if not changes and seq is None: return False, "nothing to change"
    msgs = []
    if changes:
        try:
            res = _send(pid, insid, plans[insid], changes)
        except Exception as e:
            return False, "updateinsurance failed (%s) - check the chart" % str(e)[:100]
        msgs.append(re.sub(r"\s+", " ", res[100:300]))
        if 'success="1"' not in res: return False, msgs[0]
        try:
            r, plans, now = _plans(pid)
        except Exception as e:
            return seq is None, " | ".join(msgs + ["re-read failed - patient order not checked, check the chart"])
        if seq is None:
            if not before or _norm(now) == _norm(before): return True, msgs[0]
            ok2, m2 = _set_order(pid, plans, insid, _norm(before))
            return True, " | ".join(msgs + ["field edit cleared insorder %r - %s" % (before, ("restored: " + m2) if ok2 else ("WARNING not restored, set it: " + m2))])
    want = _norm(seq)
    ok2, m2 = _set_order(pid, plans, insid, want)
    msgs.append(m2)
    if not ok2 and before and _norm(before) != want:
        try:
            _, plans2, now = _plans(pid)
            if _norm(now) != _norm(before):
                ok3, m3 = _set_order(pid, plans2, insid, _norm(before))
                msgs.append("previous insorder %r %s" % (before, "restored" if ok3 else "NOT restored: " + m3))
        except Exception as e:
            msgs.append("re-read failed (%s) - check the chart" % str(e)[:80])
    if not ok2: msgs.append("insorder %s NOT set - check the chart" % want)
    return ok2, " | ".join(msgs)

if __name__ == "__main__":
    print(update(sys.argv[1], sys.argv[2], **dict(x.split("=", 1) for x in sys.argv[3:])))
