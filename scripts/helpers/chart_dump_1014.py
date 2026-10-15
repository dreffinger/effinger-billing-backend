# PLAIN ENGLISH (chart dump, 10/14/2026 chat pass) - reads only.
# Decides: nothing. For each chart id given, prints the insurance plans (carrier, masked member id, begin/end dates,
# sequence, coverage), the patient insurance order, DOB and sex, so the Unbilled rules can be applied with the facts in hand.
# Never touches: AMD writes.
import amd, re, sys, json
amd.login_cached()
pids = [re.sub(r"\D", "", x) for x in sys.argv[1:]]
out = {}
for pid in pids:
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pat = re.search(r'<patient [^>]*>', r)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', pat.group(0))) if pat else {}
    plans = []
    for tag in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', tag))
        if not a.get("id"): continue
        num = a.get("subscribernum", "")
        plans.append({"id": a["id"], "carrier": a.get("carrier"), "seq": a.get("sequence"), "begin": a.get("begindate"), "end": a.get("enddate"),
                      "coverage": a.get("coverage"), "finclass": a.get("finclasscode"), "member_masked": ("*" * max(0, len(num) - 4)) + num[-4:], "member_len": len(num),
                      "eligstatus": a.get("eligibilitystatusid"), "eligdate": a.get("eligibilityresponsedate")})
    resp = re.search(r'<respparty [^>]*>', r)
    ra = dict(re.findall(r'(\w+)="([^"]*)"', resp.group(0))) if resp else {}
    out[pid] = {"name": pa.get("name"), "dob": pa.get("dob"), "sex": pa.get("sex"), "chart": pa.get("chart"), "insorder": pa.get("insorder"),
                "ssn_present": bool(pa.get("ssn")), "plans": plans, "resp": ra.get("id"), "raw_len": len(r)}
    print(pid, json.dumps(out[pid]))
json.dump(out, open("chart_dump_1014.json", "w"), indent=1)
