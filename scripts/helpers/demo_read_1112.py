# PLAIN ENGLISH (read-only): getdemographic for a list of charts -> secrets/run_0039_ids.json (name, DOB, sex, address, plans) for the
# evening facesheet email and the board cards; nothing written to AMD. Usage: python3 demo_read_1112.py <pid> [<pid> ...]
import sys, re, json, html, amd
out = {}
for pid in sys.argv[1:]:
    x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
    m = re.search(r'<patient [^>]*>', x); a = {}
    if m:
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', x)]
    addr = re.search(r'<address [^>]*>', x); ad = dict(re.findall(r'(\w+)="([^"]*)"', addr.group(0))) if addr else {}
    out[pid] = {"name": html.unescape(a.get("name","")), "dob": a.get("dob",""), "sex": a.get("sex",""), "insorder": a.get("insorder",""),
                "chart": a.get("chart",""), "address": {k: ad.get(k,"") for k in ("address1","city","state","zip")},
                "plans": [{k: p.get(k,"") for k in ("id","carrier","carname","subscribernum","begindate","enddate","sequence")} for p in plans]}
    print(pid, out[pid]["name"], out[pid]["dob"], "plans", len(plans), "insorder", a.get("insorder",""), "chart", a.get("chart",""))
json.dump(out, open("secrets/run_0039_ids.json", "w"), indent=1)
