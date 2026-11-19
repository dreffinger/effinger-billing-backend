# PLAIN ENGLISH (Correct a chart's name or birth date so the payer can match it - 11/19/2026)
# Decides: Nothing. William's facesheet paste on the board gives the patient's name / birth date as the payer holds it
#          (chart 17478221: the birth date was one day off; chart 17478216: the feed misspelled both names and
#          Medicare answered 'invalid name'). This writes exactly the fields given: the patient's birth date and/or billing
#          name through the demographics PATCH (original record echoed), and the same name / birth date on the chart's own
#          responsible party (the subscriber of a self-insured plan) with the proven updaterespparty shape.
# Never touches: address, plans, visits, anything not named on the command line.
# Usage: python3 demo_fix_1119.py <pid> [dob=YYYY-MM-DD] [first=NAME] [last=NAME] [--live]
import amd, patient_patch, re, sys
pid = sys.argv[1]; live = "--live" in sys.argv
ch = dict(x.split("=", 1) for x in sys.argv[2:] if "=" in x)
amd.login_cached()
p = patient_patch.get(pid); f = patient_patch.flatten(p); changes = {}
if "dob" in ch: changes["dob"] = ch["dob"] + "T00:00:00"
if "first" in ch or "last" in ch:
    nm = [dict(n) for n in f.get("names", [])]
    for n in nm:
        if n.get("isbilling"):
            if "first" in ch: n["firstname"] = ch["first"]
            if "last" in ch: n["lastname"] = ch["last"]
    changes["names"] = nm
print("pat%s before: dob %s names %s" % (pid, p.get("dob"), [(n.get("lastname"), n.get("firstname")) for n in p.get("names") or []]))
print("change:", {k: (v if k != "names" else [(n.get("lastname"), n.get("firstname")) for n in v]) for k, v in changes.items()})
rd = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}, ""))
rp = re.search(r'<respparty id="(resp\d+)"[^>]*>', rd); ra = dict(re.findall(r'(\w+)="([^"]*)"', rp.group(0))) if rp else {}
print("responsible party before:", {k: ra.get(k) for k in ("id", "name", "dob", "sex")})
if not live: print("DRY - nothing written"); sys.exit(0)
code, txt, before = patient_patch.patch(pid, changes); print("PATCH", code, txt[:160])
a = patient_patch.get(pid); print("after: dob %s names %s" % (a.get("dob"), [(n.get("lastname"), n.get("firstname")) for n in a.get("names") or []]))
if rp:
    newname = "%s,%s" % (ch.get("last") or (ra.get("name") or ",").split(",")[0], ch.get("first") or (ra.get("name") or ",").split(",")[-1])
    y, m, d = (ch["dob"].split("-") if "dob" in ch else (None, None, None)); newdob = "%s/%s/%s" % (m, d, y) if y else ra.get("dob", "")
    attrs = 'id="%s" changed="1"' % ra["id"]
    if newname != ra.get("name"): attrs += ' name="%s" o_name="%s"' % (newname, ra.get("name", ""))
    if newdob != ra.get("dob"): attrs += ' dob="%s" o_dob="%s"' % (newdob, ra.get("dob", ""))
    if "o_" in attrs:
        rr = amd.post(amd.msg("updaterespparty", "demographics", {"patientid": pid, "nocookie": "1"}, "<respparty %s/>" % attrs))
        print("updaterespparty ->", "ok" if ("Fault" not in rr and 'success="0"' not in rr) else re.sub(r"\s+", " ", rr[:300]))
    rd = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}, ""))
    rp2 = re.search(r'<respparty id="(resp\d+)"[^>]*>', rd); r2 = dict(re.findall(r'(\w+)="([^"]*)"', rp2.group(0))) if rp2 else {}
    print("responsible party after:", {k: r2.get(k) for k in ("id", "name", "dob", "sex")})
