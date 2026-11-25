#!/usr/bin/env python3
# PLAIN ENGLISH (the payer's claim number for a Humana claim it answered $0, so the corrected claim can go out as frequency 7)
# Decides: nothing. One Stedi claim-status check (276/277, exact date of service, $0.30) per named visit through the same door as the
#   weekly sweep (claim_status_sweep.status); prints and registers the payer's claim number (tradingPartnerClaimNumber) with the status
#   lines. The ERA cache (era_details) carries no ICN, and a $0 denial line is never posted, so this is the only way to get it.
#   Needed 11/25/2026 for the Orwell 99233s (Humana CO-16/M76, William: 'delete all except i10 and resubmit') and the three 99489
#   modifier-25 lines (William: 'yes try that') - the 5(d) rule: a claim the payer adjudicated is corrected with frequency 7 + its ICN.
# Rules it uses: Humana = Stedi payer 61101; the chart's name, birth date and HUM01 member id from getdemographic; the usage log line
#   stedi.py writes. Never touches: AMD writes. Usage: python3 icn_lookup_1125.py <pid>:<vid>:<mm/dd/yyyy>:<amount> [...] [--go]
import amd, stedi, claim_status_sweep, cs_rules, json, os, re, sys, datetime
GO = "--go" in sys.argv; STAMP = "2026-11-25T0721Z"; REG = "registers/icn_lookup_%s.json" % STAMP
reg = json.load(open(REG)) if os.path.exists(REG) else {}
amd.login_cached()
def chart(pid):
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', t).group(0)))
    last, first = (pa.get("name") or ",").split(",", 1); first = first.strip().split(" ")[0]
    dob = datetime.datetime.strptime(pa.get("dob"), "%m/%d/%Y").strftime("%Y%m%d")
    member = None
    for x in re.findall(r'<insplan [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', x))
        if a.get("carrier") == "car6285" and not a.get("enddate"): member = a.get("subscribernum")
    return first.strip(), last.strip(), dob, member
for arg in [a for a in sys.argv[1:] if not a.startswith("--")]:
    pid, vid, dos, amt = arg.split(":")
    first, last, dob, member = chart(pid); d = datetime.datetime.strptime(dos, "%m/%d/%Y").strftime("%Y%m%d")
    print("pat%s v%s %s $%s -> Humana 61101 member %s" % (pid, vid, dos, amt, ("*" * (len(member or "") - 4)) + (member or "")[-4:]))
    if not GO: print("  DRY - would ask"); continue
    code, j = claim_status_sweep.status("61101", first, last, dob, member, d, float(amt), exact=True, pid=pid, who="button %s icn" % STAMP)
    claims = cs_rules.claims_of(j) if j else []
    out = {"http": code, "claims": claims, "errors": cs_rules.errors_of(j) if j else None}
    icn = [c.get("pccn") for c in claims if c.get("pccn")]
    out["icn"] = icn; reg[vid] = out
    print("  http", code, "icn", icn, "| lines", [c.get("lines") for c in claims][:3], "| errors", out["errors"])
    os.makedirs("patient_db/claimstatus_raw", exist_ok=True); json.dump(j, open("patient_db/claimstatus_raw/%s_%s_icn.json" % (vid, STAMP), "w"), indent=1)
json.dump(reg, open(REG, "w"), indent=1)
