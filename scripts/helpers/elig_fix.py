# PLAIN ENGLISH (Hospital eligibility refresh)
# Decides: From a pasted TMH 'Active Insurance' block: make Medicare primary with the MBI, the listed plan secondary, end the old denying plan, re-point and rebill the audit visits.
# Rules it uses: Medicare first, supplement/commercial second, no group numbers; only 2025-26 audit visits.
# Never touches: Paid visits.
# ---
"""Hospital-eligibility refresh (William pastes 'Active Insurance' blocks): make Medicare primary with the MBI,
the listed supplement/commercial plan secondary (no group numbers), then re-point + rebill the patient's 2025-26
audit visits Medicare-first.  Usage: python3 elig_fix.py "<name prefix>" <MBI> [<carrier car####> <memberid>] [--end <carrier code to end-date>]"""
import json, amd, re, sys, time, datetime, add_ins, ins_update, move_to_ins
def run(prefix, mbi, sec_car=None, sec_num=None, end_code=None):
    h = json.load(open("audit_pr_transfer.json")); xs = [x for x in h if x["patient"].upper().startswith(prefix.upper())]
    if not xs: return "not in audit"
    pid = xs[0]["patientid"]; out = []
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
    act = [p for p in pl if not p[3]]; out.append("plans %s" % [(p[1], p[4], p[5]) for p in act])
    mc = [p for p in act if p[1] == "car6085"]
    if mbi:
        if not mc: ins, ms = add_ins.add(pid, "car6085", mbi, "09/04/2024"); out.append("Medicare added seq %s" % ms)
        else:
            ms = mc[0][5]
            if mc[0][4] != mbi: out.append("MBI %s->%s %s" % (mc[0][4], mbi, ins_update.update(pid, mc[0][0], subscribernum=mbi)[0]))
    else: ms = None
    order = [ms] if ms else []
    if sec_car:
        sc = [p for p in act if p[1] == sec_car]
        if not sc: ins2, bs = add_ins.add(pid, sec_car, sec_num, "09/04/2024"); out.append("secondary %s added seq %s" % (sec_num, bs))
        else:
            bs = sc[0][5]
            if sc[0][4] != sec_num: out.append("secondary id fix %s" % ins_update.update(pid, sc[0][0], subscribernum=sec_num)[0])
        order.append(bs)
    if end_code:
        CAR = {v[0]: k for k, v in json.load(open("carriers.json")).items()}
        recent = [x for x in xs if x["dos"][-4:] >= "2025"]
        first = min(datetime.datetime.strptime(x["dos"], "%m/%d/%Y") for x in recent) if recent else datetime.datetime.today()
        for p in act:
            if p[1] == CAR.get(end_code): out.append("end %s %s" % (end_code, ins_update.update(pid, p[0], enddate=(first - datetime.timedelta(days=1)).strftime("%m/%d/%Y"))[0]))
    seq = ",".join(order); done = set()
    for x in sorted(xs, key=lambda x: x["dos"][-4:] + x["dos"]):
        if x["visit"] in done or x["dos"][-4:] < "2025": continue
        done.add(x["visit"]); out.append("%s %s -> %s" % (x["dos"], x["cpt"], move_to_ins.move(x["chargeid"], seq))); time.sleep(0.6)
    open("batch_refresh.log", "a").write("== %s pid %s elig_fix 9/4\n   %s\n" % (prefix.upper(), pid, "\n   ".join(out)))
    return "\n".join(out)
if __name__ == "__main__":
    a = sys.argv[1:]; end = a[a.index("--end") + 1] if "--end" in a else None
    a = [x for x in a if x not in ("--end", end)]
    print(run(a[0], a[1] if len(a) > 1 and a[1] != "-" else None, a[2] if len(a) > 2 else None, a[3] if len(a) > 3 else None, end))
