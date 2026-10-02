# PLAIN ENGLISH (7 AM ET 10/2 slot, run 2026-10-02T1110Z): READ-ONLY pass for the Unbilled column and the admit follow-ups.
# Decides: nothing. (1) lookuppatient for the four pending 9/30 admits (WILBOURNE / THORNEY / TRENT / HARLOW) so a chart created by
#   the Claimocity feed since the last run is noticed. (2) getdemographic on every chart behind an 'Insurance order is missing' row
#   of this run's Unbilled snapshot: plans (carrier, sequence, begin/end), default insorder, address line 1 - so a plan William
#   or a chat session added since the 5 AM run is caught and the visit can be released this run.
# Never touches: AMD writes.
import amd, re, json, sys, time
STAMP = "2026-10-02T1110Z"
amd.login_cached()
out = {"admits": {}, "charts": {}}
for nm in ["WILBOURNE,PATIENT339%", "THORNEY,[first]%", "TRENT,[first]%", "HARLOW,[first]%"]:
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
    pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
    out["admits"][nm] = [{k: p.get(k) for k in ("id", "name", "chart", "dob")} for p in pats]
    print("lookup", nm, [(p.get("id"), p.get("dob")) for p in pats]); time.sleep(0.3)
pids = sys.argv[1:]
for pid in pids:
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    m = re.search(r'<patient [^>]*>', d); attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    addr = re.search(r'<address [^>]*>', d); addr = dict(re.findall(r'(\w+)="([^"]*)"', addr.group(0))) if addr else {}
    out["charts"][pid] = {"insorder": attrs.get("insorder"), "dob": attrs.get("dob"), "addr1": addr.get("address1"),
        "plans": [{k: p.get(k) for k in ("id", "carrier", "sequence", "begindate", "enddate", "finclasscode")} for p in plans]}
    print("pat%s insorder=%s plans=%s addr1=%s" % (pid, attrs.get("insorder"),
          [(p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate")) for p in plans], bool(addr.get("address1"))))
    time.sleep(0.3)
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1)
