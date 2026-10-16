# PLAIN ENGLISH (chart plan read, 9 AM ET 10/16/2026 run 2026-10-16T1310Z) - READ ONLY.
# Decides: nothing. getdemographic for each chart id given; prints every insplan's id, carrier, sequence, begin/end dates,
#   subscriber number and the patient insorder, so a cascade answer can be compared with what the chart already holds. No AMD write.
import amd, re, sys
amd.login_cached()
for pid in sys.argv[1:]:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
    io = re.search(r'<patient [^>]*insorder="([^"]*)"', r)
    print(pid, "insorder", io.group(1) if io else None)
    for p in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', p))
        print("   ", a.get("id"), a.get("carrier"), "seq", a.get("sequence"), a.get("begindate"), "-", a.get("enddate"), "sub", a.get("subscribernum"), "cov", a.get("coverage"), "fin", a.get("finclasscode") or a.get("finclass"))
