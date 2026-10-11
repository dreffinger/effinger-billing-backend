# PLAIN ENGLISH (read-only chart reads, 1 AM ET 10/11 slot = 2026-10-11T0510Z backend billing run)
# Decides: nothing. Reads the charts William's board notes of 03:21-04:26Z name (17472396 hospice GV, 20863 send,
# 17472124 PCC dual, 17470940 + 17477516 99344 recode, 12231996 + 17476337 write-offs, 17475338 card D, 17474258 UHC id,
# 12180329 void, 17477639 self-pay) plus the three new zero-plan Claimocity charts, and writes a register.
# Never touches: AMD writes. No patient names are printed or saved (chart / visit / charge ids only).
import json, re, time, sys
import xml.etree.ElementTree as ET
import amd, txh, payreasons
amd.login_cached()
STAMP = "2026-10-11T0510Z"
out = {"stamp": STAMP, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
def vs(pid, vid):
    return payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, vid))
def brief(ch):
    return {k: ch[k] for k in ("cid","cpt","dos","fee","paid","insbalance","patbalance","carrier")} | {
        "pays": [(p["id"], p["carrier"], p["amount"], p["checkno"], p["date"], p["void"], len(p["reasons"]), p["reasons"][:4]) for p in ch["pays"]],
        "wos": [(w["id"], w["code"], w["amount"], w["date"], w["void"]) for w in ch["wos"]]}
def rawvisit(pid, vid):
    root = txh.fetch_visit(pid, vid); rows = []
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        rows.append({k: c.get(k) for k in ("id","visit","proccode","dos","fee","paid","insbal","patbal","carrier","billdate","insorder","modifiers","mod1","mod2","procmod","status","claimstatus") if c.get(k) is not None})
    return rows
def plans(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}), timeout=120)
    rt = ET.fromstring(r.encode("latin-1", "ignore")) if isinstance(r, str) else ET.fromstring(r)
    res = []
    for p in rt.iter("insplan"):
        res.append({k: p.get(k) for k in p.keys() if not re.search(r"(?i)subscriber|name|ssn|dob|birth|address|phone", k)})
    pat = next(rt.iter("patient"), None)
    order = pat.get("insorder") if pat is not None else None
    return {"patient_insorder": order, "plans": res}
want = {
 "17472396": ["19441616","19442523","19444342","19446223","19447320","19457336"],
 "17472124": ["19445180","19446287","19448899","19449437"],
 "17470940": ["19456320","19455208"],
 "17477516": ["19456319"],
 "12231996": ["19415872"],
 "17476337": ["19440492"],
 "17475338": ["19431100"],
 "17474258": ["19419032","19419622","19420346","19422181"],
 "12180329": ["19436591","19436827"],
 "17477639": ["19455621","19453720"],
 "20863": ["19455936"],
}
for pid, vids in want.items():
    out["plans_"+pid] = plans(pid)
    print("PLANS", pid, json.dumps(out["plans_"+pid]))
    for v in vids:
        try:
            st = [brief(c) for c in vs(pid, v)]
            out[pid+"_"+v] = {"state": st, "raw": rawvisit(pid, v)}
            print("VISIT", pid, v, json.dumps(out[pid+"_"+v]))
        except Exception as e:
            print("VISIT", pid, v, "ERR", repr(e)[:200])
for pid in ("17478013","17478030","17478031"):
    out["plans_"+pid] = plans(pid); print("PLANS", pid, json.dumps(out["plans_"+pid]))
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1)
print("saved registers/reads_%s.json" % STAMP)
