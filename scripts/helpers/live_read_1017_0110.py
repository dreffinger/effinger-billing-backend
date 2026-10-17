# PLAIN ENGLISH (live chart read, 9 PM ET 10/16/2026 run 2026-10-17T0110Z) - READ ONLY.
# Decides: nothing. For each chart id it reads getdemographic and prints the insurance plans (plan id, carrier id,
#   begin/end dates, sequence, and only the SHAPE of the member id - length + pattern class, never the value) and the
#   patient insorder, so the run can see whether a plan was added since the last slot and whether a VA plan carries an
#   ICN-shaped id or an SSN-shaped one. No AMD write of any kind. Writes registers/live_read_<stamp>.json (ids only).
import amd, re, sys, json
STAMP = "2026-10-17T0110Z"; amd.login_cached(); out = {}
def shape(s):
    s = s or ""
    if re.fullmatch(r"\d{10}V\d{6}", s): return "ICN(10V6)"
    if re.fullmatch(r"\d{9}", s): return "9digits(SSN-shaped)"
    if re.fullmatch(r"\d+", s): return "%ddigits" % len(s)
    if re.fullmatch(r"[0-9][A-Z0-9]{10}", s): return "MBI-shaped"
    return "mixed len %d" % len(s)
for pid in sys.argv[1:]:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
    rows = []
    for p in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', p))
        rows.append({"ins": a.get("id"), "carrier": a.get("carrier"), "begin": a.get("begindate"), "end": a.get("enddate"),
                     "seq": a.get("sequence"), "idshape": shape(a.get("subscribernum")), "coverage": a.get("coverage")})
    io = re.search(r'<patient [^>]*insorder="([^"]*)"', r)
    out[pid] = {"plans": rows, "insorder": io.group(1) if io else None}
    print(pid, "insorder:", out[pid]["insorder"], "plans:", rows)
json.dump(out, open("registers/live_read_%s.json" % STAMP, "w"), indent=1)
