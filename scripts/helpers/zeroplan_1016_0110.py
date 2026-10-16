# PLAIN ENGLISH (zero-plan chart re-read, 9 PM ET 10/15/2026 run 2026-10-16T0110Z) - READ ONLY.
# Decides: nothing. For each Unbilled 'Insurance order is missing' chart it reads getdemographic and prints how many
#   insurance plans the chart carries now (plan ids + carrier ids only - no names, no member numbers), so the run knows
#   whether William or a chat session added a plan since the last slot. No AMD write of any kind.
import amd, re, sys, json
amd.login_cached()
out = {}
for pid in sys.argv[1:]:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
    plans = re.findall(r'<insplan [^>]*>', r)
    rows = []
    for p in plans:
        a = dict(re.findall(r'(\w+)="([^"]*)"', p))
        rows.append((a.get("id"), a.get("carrier"), a.get("begindate"), a.get("enddate"), a.get("sequence")))
    io = re.search(r'<patient [^>]*insorder="([^"]*)"', r)
    out[pid] = {"plans": rows, "insorder": io.group(1) if io else None}
    print(pid, "plans:", len(rows), rows, "insorder:", out[pid]["insorder"])
json.dump(out, open("registers/zeroplan_2026-10-16T0110Z.json", "w"), indent=1)
