# PLAIN ENGLISH (exclusion-row live read, 7 AM ET 10/16/2026 run 2026-10-16T1110Z): READ-ONLY.
# Decides: nothing. For each "<patientid>:<visitid>" argument it reads the visit's live transaction history
#   (gettxhistory via txh.fetch_visit) and the chart's insurance plans (getdemographic) and prints, per charge:
#   CPT, DOS, fee, insurance balance, patient balance, last-billed carrier, bill date, and every payment / write-off
#   row (carrier, amount, check number, date). Plans print as plan id + carrier id + sequence + begin/end dates only.
#   Writes registers/excl_reads_<stamp>.json (ids and amounts only - no names, no member numbers). No AMD write.
# Usage: python3 excl_reads_1016_1110.py 23456:19367114 17475638:19443047
import amd, txh, re, json, sys
STAMP = "2026-10-16T1110Z"
amd.login_cached()
out = {"stamp": STAMP, "visits": []}
for arg in sys.argv[1:]:
    pid, vid = arg.split(":")
    rec = {"pid": pid, "vid": vid, "charges": [], "plans": []}
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
    for p in re.findall(r'<insplan [^>]*>', d):
        a = dict(re.findall(r'(\w+)="([^"]*)"', p))
        rec["plans"].append({k: a.get(k) for k in ("id", "carrier", "sequence", "begindate", "enddate", "coverage")})
    m = re.search(r'<patient [^>]*insorder="([^"]*)"', d)
    rec["patient_insorder"] = m.group(1) if m else None
    root = txh.fetch_visit(pid, vid)
    for ch in root.iter("charge"):
        a = ch.attrib
        c = {k: a.get(k) for k in ("id", "proccode", "dos", "fee", "insbal", "patbal", "paid", "carrier", "billdate", "insbilled", "void", "modifiers")}
        c["payments"] = []
        for p in ch.iter("payment"):
            b = p.attrib
            c["payments"].append({k: b.get(k) for k in ("id", "amount", "carrier", "date", "checknumber", "type", "code", "void", "origrefnum")})
        rec["charges"].append(c)
    out["visits"].append(rec)
    print("chart %s visit %s  patient insorder=%s  plans=%s" % (pid, vid, rec["patient_insorder"], rec["plans"]))
    for c in rec["charges"]:
        print("   charge %(id)s %(proccode)s %(dos)s fee=%(fee)s insbal=%(insbal)s patbal=%(patbal)s paid=%(paid)s carrier=%(carrier)s billdate=%(billdate)s void=%(void)s" % c)
        for p in c["payments"]:
            print("      pay %(id)s amt=%(amount)s carrier=%(carrier)s date=%(date)s chk=%(checknumber)s type=%(type)s code=%(code)s void=%(void)s" % p)
json.dump(out, open("registers/excl_reads_%s.json" % STAMP, "w"), indent=1)
